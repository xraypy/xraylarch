import time
import os
import numpy as np
np.seterr(all='ignore')

from functools import partial
import json

import wx
import wx.lib.scrolledpanel as scrolled

import wx.dataview as dv

from lmfit import Parameter
from lmfit.model import (save_modelresult, load_modelresult,
                             save_model, load_model)

import lmfit.models as lm_models
from lmfit.printfuncs import gformat, CORREL_HEAD

from larch import Group, site_config
from larch.math import index_of
from larch.utils.jsonutils import encode4js, decode4js
from larch.io.export_modelresult import export_modelresult

from larch.wxlib import (ReportFrame, BitmapButton, FloatCtrl, FloatSpin,
                         SetTip, GridPanel, get_icon, SimpleText, pack,
                         Button, HLine, Choice, Check, MenuItem, GUIColors,
                         CEN, RIGHT, LEFT, FRAMESTYLE, Font, FONTSIZE,
                         FileSave, FileOpen, flatnotebook,
                         EditableListBox)

from larch.wxlib.parameter import ParameterWidgets
from larch.wxlib.plotter import last_cursor_pos
from .taskpanel import TaskPanel

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

KWeight_Choices = {'1': 1, '2': 2, '3': 3,
                   '2 and 3': (2, 3),
                   '1, 2, and 3':   (2, 1, 3)}
FitSpace_Choices = {'k space': 'k', 'R space': 'R', 'wavelet': 'w'}
FTWINDOWS = ('Kaiser-Bessel', 'Hanning', 'Gaussian', 'Sine', 'Parzen', 'Welch')

ScriptWcards = "Fit Models(*.lar)|*.lar|All files (*.*)|*.*"
PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, marker='None', markersize=4)

PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)

MIN_CORREL = 0.10

COMMANDS = {}
COMMANDS['feffit_params'] = """# make feffit parameters"""
COMMANDS['feffit_trans'] = """# setup feffit transform"""
COMMANDS['dofit'] = """# do fit"""

defaults = dict(e=None, elo=-10, ehi=-5, emin=-40, emax=0, yarray='norm')

def get_xlims(x, xmin, xmax):
    xeps = min(np.diff(x))/ 5.
    i1 = index_of(x, xmin + xeps)
    i2 = index_of(x, xmax + xeps) + 1
    return i1, i2

class FeffPathPanel(wx.Panel):
    """Feff Path """

    def __init__(self, parent=None, feffdat_file=None, dirname=None,
                 fullpath=None, absorber=None, edge=None, reff=None,
                 degen=None, geom=None, npath=1, title='', user_label='',
                 _larch=None, xasmain=None, **kws):

        self.parent = parent
        self.title = title
        self.xasmain = xasmain
        wx.Panel.__init__(self, parent, -1, size=(550, 450))
        panel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LEFT)
        
        self.feffdat_file = feffdat_file
        self.fullpath = fullpath

        reff = float(reff)
        degen = float(degen)
        self.geom = geom
        self._larch = _larch

        self.wids = wids = {}
        delr = 'delr' if npath == 1 else f'delr_{npath:d}'
        sigma2  = 'sigma2' if npath == 1 else f'sigma2_{npath:d}'
        
        wids['label']  = wx.TextCtrl(panel, -1, user_label, size=(250, -1))
        wids['amp']    = wx.TextCtrl(panel, -1, f'{degen:.1f} * S02', size=(250, -1))
        wids['e0']     = wx.TextCtrl(panel, -1, 'e0',   size=(250, -1))
        wids['delr']   = wx.TextCtrl(panel, -1, delr,   size=(250, -1))
        wids['sigma2'] = wx.TextCtrl(panel, -1, sigma2, size=(250, -1))
        wids['c3']     = wx.TextCtrl(panel, -1, '',     size=(250, -1))
        wids['amp_val']    = SimpleText(panel,  '', size=(150, -1))
        wids['e0_val']     = SimpleText(panel,  '', size=(150, -1))
        wids['delr_val']   = SimpleText(panel,  '', size=(150, -1))
        wids['sigma2_val'] = SimpleText(panel,  '', size=(150, -1))
        wids['c3_val']     = SimpleText(panel,  '', size=(150, -1))

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label,
                               size=size, style=wx.ALIGN_LEFT, **kws)
        wids['use'] = Check(panel, default=True, label='Use in Fit?', size=(100, -1))        
        wids['del'] = Button(panel, 'Remove This Path', size=(150, -1),
                             action=self.onRemovePath)

        title1 = f'{dirname:s}: {feffdat_file:s}  {absorber:s} {edge:s} edge'
        title2 = f'Reff={reff:.4f},  Degen={degen:.1f}   {geom:s}'

        panel.Add(SLabel(title1, size=(275, -1), colour='#0000AA'),
                  dcol=2,  style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(wids['use'])
        panel.Add(wids['del'])
        panel.Add(SLabel(title2, size=(375, -1)),
                  dcol=3, style=wx.ALIGN_LEFT, newrow=True)

        panel.AddMany((SLabel('Label'),     wids['label']),                  newrow=True)
        panel.AddMany((SLabel('Amplitude'), wids['amp'],    wids['amp_val']), newrow=True)
        panel.AddMany((SLabel('E0 '),       wids['e0'],     wids['e0_val']),  newrow=True)
        panel.AddMany((SLabel('Delta R'),   wids['delr'],   wids['delr_val']), newrow=True)
        panel.AddMany((SLabel('sigma2'),    wids['sigma2'], wids['sigma2_val']), newrow=True)
        panel.AddMany((SLabel('C3'),        wids['c3'],     wids['c3_val']),   newrow=True)
        panel.pack()
        sizer= wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LEFT|wx.GROW|wx.ALL, 2)
        pack(self, sizer)
        

    def onRemovePath(self, event=None):
        print(' remove path ', self.fullpath, self.title, self.xasmain)
        

class FeffitResultFrame(wx.Frame):
    config_sect = 'feffit'
    def __init__(self, parent=None, peakframe=None, datagroup=None, **kws):
        wx.Frame.__init__(self, None, -1, title='Feffit Results',
                          style=FRAMESTYLE, size=(900, 700), **kws)
        self.peakframe = peakframe
        self.datagroup = datagroup
        feffit = getattr(datagroup, 'feffit', None)
        self.fit_history = getattr(feffit, 'fit_history', [])
        self.parent = parent
        self.datasets = {}
        self.form = {}
        self.larch_eval = None
        self.nfit = 0
        self.createMenus()
        self.build()

    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        m = {}
        MenuItem(self, fmenu, "Save Model for Current Group",
                 "Save Model and Result to be loaded later",
                 self.onSaveFitResult)

        MenuItem(self, fmenu, "Save Fit and Components for Current Fit",
                 "Save Arrays and Results to Text File",
                 self.onExportFitResult)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "Save Parameters and Statistics for All Fitted Groups",
                 "Save CSV File of Parameters and Statistics for All Fitted Groups",
                 self.onSaveAllStats)
        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)

    def build(self):
        sizer = wx.GridBagSizer(3, 3)
        sizer.SetVGap(3)
        sizer.SetHGap(3)

        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(200)

        self.datalistbox = EditableListBox(splitter, self.ShowDataSet,
                                           size=(250, -1))
        panel = scrolled.ScrolledPanel(splitter)

        panel.SetMinSize((775, 575))
        self.colors = GUIColors()

        # title row
        self.wids = wids = {}
        title = SimpleText(panel, 'Feffit Results', font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LEFT)

        wids['data_title'] = SimpleText(panel, '< > ', font=Font(FONTSIZE+2),
                                        minsize=(350, -1),
                                        colour=self.colors.title, style=LEFT)

        opts = dict(default=False, size=(200, -1), action=self.onPlot)
        wids['plot_rspace'] = Check(panel, label='Plot R-space', **opts)
        wids['plot_kspace'] = Check(panel, label='Plot k-space', **opts)
        self.plot_choice = Button(panel, 'Plot This Fit',
                                  size=(125, -1), action=self.onPlot)

        irow = 0
        sizer.Add(title,              (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['data_title'], (irow, 1), (1, 3), LEFT)

        irow += 1
        wids['model_desc'] = SimpleText(panel, '<Model>', font=Font(FONTSIZE+1),
                                        size=(750, 50), style=LEFT)
        sizer.Add(wids['model_desc'],  (irow, 0), (1, 6), LEFT)

        irow += 1
        # sizer.Add(SimpleText(panel, 'Plot: '), (irow, 0), (1, 1), LEFT)
        sizer.Add(self.plot_choice,   (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['plot_kspace'], (irow, 1), (1, 2), LEFT)
        sizer.Add(wids['plot_rspace'], (irow, 3), (1, 1), LEFT)

        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Fit Statistics]]',  font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LEFT)
        subtitle = SimpleText(panel, '  (Fit #01 is most recent)',
                              font=Font(FONTSIZE+1),  style=LEFT)

        sizer.Add(title, (irow, 0), (1, 1), LEFT)
        sizer.Add(subtitle, (irow, 1), (1, 1), LEFT)

        sview = self.wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        sview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectFit)
        sview.AppendTextColumn(' Fit#',  width=75)
        sview.AppendTextColumn(' N_data', width=75)
        sview.AppendTextColumn(' N_vary', width=75)
        sview.AppendTextColumn('\u03c7\u00B2', width=110)
        sview.AppendTextColumn('reduced \u03c7\u00B2', width=110)
        sview.AppendTextColumn('Akaike Info', width=110)
        sview.AppendTextColumn('Bayesian Info', width=110)

        for col in range(sview.ColumnCount):
            this = sview.Columns[col]
            this.Sortable = True
            this.Alignment = wx.ALIGN_RIGHT if col > 0 else wx.ALIGN_LEFT
            this.Renderer.Alignment = this.Alignment

        sview.SetMinSize((700, 125))

        irow += 1
        sizer.Add(sview, (irow, 0), (1, 5), LEFT)

        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Variables]]',  font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LEFT)
        sizer.Add(title, (irow, 0), (1, 1), LEFT)

        self.wids['copy_params'] = Button(panel, 'Update Model with these values',
                                          size=(250, -1), action=self.onCopyParams)

        sizer.Add(self.wids['copy_params'], (irow, 1), (1, 3), LEFT)

        pview = self.wids['params'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        self.wids['paramsdata'] = []
        pview.AppendTextColumn('Parameter',         width=150)
        pview.AppendTextColumn('Best-Fit Value',    width=125)
        pview.AppendTextColumn('Standard Error',    width=125)
        pview.AppendTextColumn('Info ',             width=300)

        for col in range(4):
            this = pview.Columns[col]
            this.Sortable = False
            this.Alignment = wx.ALIGN_RIGHT if col in (1, 2) else wx.ALIGN_LEFT
            this.Renderer.Alignment = this.Alignment

        pview.SetMinSize((700, 200))
        pview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectParameter)

        irow += 1
        sizer.Add(pview, (irow, 0), (1, 5), LEFT)

        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Correlations]]',  font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LEFT)

        self.wids['all_correl'] = Button(panel, 'Show All',
                                          size=(100, -1), action=self.onAllCorrel)

        self.wids['min_correl'] = FloatSpin(panel, value=MIN_CORREL,
                                            min_val=0, size=(100, -1),
                                            digits=3, increment=0.1)

        ctitle = SimpleText(panel, 'minimum correlation: ')
        sizer.Add(title,  (irow, 0), (1, 1), LEFT)
        sizer.Add(ctitle, (irow, 1), (1, 1), LEFT)
        sizer.Add(self.wids['min_correl'], (irow, 2), (1, 1), LEFT)
        sizer.Add(self.wids['all_correl'], (irow, 3), (1, 1), LEFT)

        cview = self.wids['correl'] = dv.DataViewListCtrl(panel, style=DVSTYLE)

        cview.AppendTextColumn('Parameter 1',    width=150)
        cview.AppendTextColumn('Parameter 2',    width=150)
        cview.AppendTextColumn('Correlation',    width=150)

        for col in (0, 1, 2):
            this = cview.Columns[col]
            this.Sortable = False
            align = wx.ALIGN_LEFT
            if col == 2:
                align = wx.ALIGN_RIGHT
            this.Alignment = this.Renderer.Alignment = align
        cview.SetMinSize((475, 200))

        irow += 1
        sizer.Add(cview, (irow, 0), (1, 5), LEFT)

        pack(panel, sizer)
        panel.SetupScrolling()

        splitter.SplitVertically(self.datalistbox, panel, 1)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)

        pack(self, mainsizer)
        self.Show()
        self.Raise()


    def onSaveAllStats(self, evt=None):
        "Save Parameters and Statistics to CSV"
        # get first dataset to extract fit parameter names
        fnames = self.datalistbox.GetItems()
        if len(fnames) == 0:
            return

        deffile = "FeffitResults.csv"
        wcards  = 'CVS Files (*.csv)|*.csv|All files (*.*)|*.*'
        path = FileSave(self, 'Save Parameter and Statistics for Feff Fits',
                        default_file=deffile, wildcard=wcards)
        if path is None:
            return
        if os.path.exists(path):
            if wx.ID_YES != Popup(self,
                                  "Overwrite existing Statistics File?",
                                  "Overwrite existing file?", style=wx.YES_NO):
                return

        ppeaks_tmpl = self.datasets[fnames[0]].prepeaks
        param_names = list(reversed(ppeaks_tmpl.fit_history[0].params.keys()))
        user_opts = ppeaks_tmpl.user_options
        model_desc = self.get_model_desc(ppeaks_tmpl.fit_history[0].model).replace('\n', ' ')
        out = ['# Feffit Report %s' % time.ctime(),
               '# Fitted Array name: %s' %  user_opts['array_name'],
               '# Model form: %s' % model_desc,
               '# Baseline form: %s' % user_opts['baseline_form'],
               '# Energy fit range: [%f, %f]' % (user_opts['emin'], user_opts['emax']),
               '#--------------------']

        labels = [('Data Set' + ' '*25)[:25], 'Group name', 'n_data',
                 'n_varys', 'chi-square', 'reduced_chi-square',
                 'akaike_info', 'bayesian_info']

        for pname in param_names:
            labels.append(pname)
            labels.append(pname+'_stderr')
        out.append('# %s' % (', '.join(labels)))
        for name, dgroup in self.datasets.items():
            result = dgroup.prepeaks.fit_history[0]
            label = dgroup.filename
            if len(label) < 25:
                label = (label + ' '*25)[:25]
            dat = [label, dgroup.groupname,
                   '%d' % result.ndata, '%d' % result.nvarys]
            for attr in ('chisqr', 'redchi', 'aic', 'bic'):
                dat.append(gformat(getattr(result, attr), 11))
            for pname in param_names:
                val = stderr = 0
                if pname in result.params:
                    par = result.params[pname]
                    dat.append(gformat(par.value, 11))
                    stderr = gformat(par.stderr, 11) if par.stderr is not None else 'nan'
                    dat.append(stderr)
            out.append(', '.join(dat))
        out.append('')

        with open(path, 'w') as fh:
            fh.write('\n'.join(out))


    def onSaveFitResult(self, event=None):
        deffile = self.datagroup.filename.replace('.', '_') + 'peak.modl'
        sfile = FileSave(self, 'Save Fit Model', default_file=deffile,
                           wildcard=ModelWcards)
        if sfile is not None:
            result = self.get_fitresult()
            save_modelresult(result, sfile)

    def onExportFitResult(self, event=None):
        dgroup = self.datagroup
        deffile = dgroup.filename.replace('.', '_') + '.xdi'
        wcards = 'All files (*.*)|*.*'

        outfile = FileSave(self, 'Export Fit Result', default_file=deffile)

        result = self.get_fitresult()
        if outfile is not None:
            i1, i2 = get_xlims(dgroup.xdat,
                               result.user_options['emin'],
                               result.user_options['emax'])
            x = dgroup.xdat[i1:i2]
            y = dgroup.ydat[i1:i2]
            yerr = None
            if hasattr(dgroup, 'yerr'):
                yerr = 1.0*dgroup.yerr
                if not isinstance(yerr, np.ndarray):
                    yerr = yerr * np.ones(len(y))
                else:
                    yerr = yerr[i1:i2]

            export_modelresult(result, filename=outfile,
                               datafile=dgroup.filename, ydata=y,
                               yerr=yerr, x=x)


    def get_fitresult(self, nfit=None):
        if nfit is None:
            nfit = self.nfit
        self.fit_history = getattr(self.datagroup.feffit, 'fit_history', [])
        self.nfit = max(0, nfit)
        if self.nfit > len(self.fit_history):
            self.nfit = 0
        return self.fit_history[self.nfit]

    def onPlot(self, event=None):
        show_resid = self.wids['plot_kspace'].IsChecked()
        sub_bline = self.wids['plot_rspace'].IsChecked()
        cmd = "plot_prepeaks_fit(%s, nfit=%i, show_residual=%s, subtract_baseline=%s)"
        cmd = cmd % (self.datagroup.groupname, self.nfit, show_resid, sub_bline)

        self.peakframe.larch_eval(cmd)

    def onSelectFit(self, evt=None):
        if self.wids['stats'] is None:
            return
        item = self.wids['stats'].GetSelectedRow()
        if item > -1:
            self.show_fitresult(nfit=item)

    def onSelectParameter(self, evt=None):
        if self.wids['params'] is None:
            return
        if not self.wids['params'].HasSelection():
            return
        item = self.wids['params'].GetSelectedRow()
        pname = self.wids['paramsdata'][item]

        cormin= self.wids['min_correl'].GetValue()
        self.wids['correl'].DeleteAllItems()

        result = self.get_fitresult()
        this = result.params[pname]
        if this.correl is not None:
            sort_correl = sorted(this.correl.items(), key=lambda it: abs(it[1]))
            for name, corval in reversed(sort_correl):
                if abs(corval) > cormin:
                    self.wids['correl'].AppendItem((pname, name, "% .4f" % corval))

    def onAllCorrel(self, evt=None):
        result = self.get_fitresult()
        params = result.params
        parnames = list(params.keys())

        cormin= self.wids['min_correl'].GetValue()
        correls = {}
        for i, name in enumerate(parnames):
            par = params[name]
            if not par.vary:
                continue
            if hasattr(par, 'correl') and par.correl is not None:
                for name2 in parnames[i+1:]:
                    if (name != name2 and name2 in par.correl and
                            abs(par.correl[name2]) > cormin):
                        correls["%s$$%s" % (name, name2)] = par.correl[name2]

        sort_correl = sorted(correls.items(), key=lambda it: abs(it[1]))
        sort_correl.reverse()

        self.wids['correl'].DeleteAllItems()

        for namepair, corval in sort_correl:
            name1, name2 = namepair.split('$$')
            self.wids['correl'].AppendItem((name1, name2, "% .4f" % corval))

    def onCopyParams(self, evt=None):
        result = self.get_fitresult()
        self.peakframe.update_start_values(result.params)

    def ShowDataSet(self, evt=None):
        dataset = evt.GetString()
        group = self.datasets.get(evt.GetString(), None)
        if group is not None:
            self.show_results(datagroup=group)

    def add_results(self, dgroup, form=None, larch_eval=None, show=True):
        name = dgroup.filename
        if name not in self.datalistbox.GetItems():
            self.datalistbox.Append(name)
        self.datasets[name] = dgroup
        if show:
            self.show_results(datagroup=dgroup, form=form, larch_eval=larch_eval)

    def show_results(self, datagroup=None, form=None, larch_eval=None):
        if datagroup is not None:
            self.datagroup = datagroup
        if larch_eval is not None:
            self.larch_eval = larch_eval

        datagroup = self.datagroup
        self.peakfit_history = getattr(self.datagroup.prepeaks, 'fit_history', [])

        cur = self.get_fitresult()
        wids = self.wids
        wids['stats'].DeleteAllItems()
        for i, res in enumerate(self.peakfit_history):
            args = ['%2.2d' % (i+1)]
            for attr in ('ndata', 'nvarys', 'chisqr', 'redchi', 'aic', 'bic'):
                val = getattr(res.result, attr)
                if isinstance(val, int):
                    val = '%d' % val
                else:
                    val = gformat(val, 10)
                args.append(val)
            wids['stats'].AppendItem(tuple(args))
        wids['data_title'].SetLabel(self.datagroup.filename)
        self.show_fitresult(nfit=0)

    def get_model_desc(self, model):
        model_repr = model._reprstring(long=True)
        for word in ('Model(', ',', '(', ')', '+'):
            model_repr = model_repr.replace(word, ' ')
        words = []
        mname, imodel = '', 0
        for word in model_repr.split():
            if word.startswith('prefix'):
                words.append("%sModel(%s)" % (mname.title(), word))
            else:
                mname = word
                if imodel > 0:
                    delim = '+' if imodel % 2 == 1 else '+\n'
                    words.append(delim)
                imodel += 1
        return ''.join(words)


    def show_fitresult(self, nfit=0, datagroup=None):
        if datagroup is not None:
            self.datagroup = datagroup

        result = self.get_fitresult(nfit=nfit)
        wids = self.wids
        wids['data_title'].SetLabel(self.datagroup.filename)
        wids['model_desc'].SetLabel(self.get_model_desc(result.model))
        wids['params'].DeleteAllItems()
        wids['paramsdata'] = []
        for param in reversed(result.params.values()):
            pname = param.name
            try:
                val = gformat(param.value, 10)
            except (TypeError, ValueError):
                val = ' ??? '
            serr = ' N/A '
            if param.stderr is not None:
                serr = gformat(param.stderr, 10)
            extra = ' '
            if param.expr is not None:
                extra = '= %s ' % param.expr
            elif not param.vary:
                extra = '(fixed)'
            elif param.init_value is not None:
                extra = '(init=%s)' % gformat(param.init_value, 10)

            wids['params'].AppendItem((pname, val, serr, extra))
            wids['paramsdata'].append(pname)
        self.Refresh()


class FeffitPanel(TaskPanel):
    def __init__(self, parent=None, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='fefft_config',
                           title='Feff Fitting of EXAFS Paths',
                           config=defaults, **kws)
        self.paths_data = {}
        
    def onPanelExposed(self, **kws):
        # called when notebook is selected
        try:
            fname = self.controller.filelist.GetStringSelection()
            gname = self.controller.file_groups[fname]
            dgroup = self.controller.get_group(gname)
            if not hasattr(dgroup, 'chi'):
                self.xasmain.process_exafs(dgroup)
            self.fill_form(dgroup)
        except:
            pass # print(" Cannot Fill prepeak panel from group ")

    def build_display(self):
        self.paths_nb = flatnotebook(self, {})
        pan = self.panel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LEFT)

        self.wids = wids = {}

        fsopts = dict(digits=2, increment=0.1, with_pin=True)

        ffit_kmin = self.add_floatspin('ffit_kmin',  value=2, **fsopts)
        ffit_kmax = self.add_floatspin('ffit_kmax',  value=17, **fsopts)
        ffit_dk   = self.add_floatspin('ffit_dk',    value=4, **fsopts)
        ffit_rmin = self.add_floatspin('ffit_rmin',  value=1, **fsopts)
        ffit_rmax = self.add_floatspin('ffit_rmax',  value=5, **fsopts)
                
        wids['ffit_kweight'] = Choice(pan, size=(125, -1),
                                     choices=list(KWeight_Choices.keys()))
        wids['ffit_kweight'].SetSelection(1)

        wids['ffit_kwindow'] = Choice(pan, choices=list(FTWINDOWS), size=(125, -1))

        wids['ffit_fitspace'] = Choice(pan, choices=list(FitSpace_Choices.keys()),
                                       size=(125, -1))

        self.plotmodel_btn = Button(pan,'Plot Current Model',
                                    action=self.onPlotModel,  size=(125, -1))
        self.fitmodel_btn = Button(pan, 'Fit Current Group',
                                   action=self.onFitModel,  size=(125, -1))
        self.fitmodel_btn.Disable()
        
        self.fitselected_btn = Button(pan, 'Fit Selected Groups',
                                   action=self.onFitSelected,  size=(125, -1))
        self.fitselected_btn.Disable()
        self.fitmodel_btn.Disable()

        def add_text(text, dcol=1, newrow=True):
            pan.Add(SimpleText(pan, text), dcol=dcol, newrow=newrow)

        pan.Add(SimpleText(pan, 'Feff Fitting',
                           size=(350, -1), **self.titleopts), style=LEFT, dcol=4, newrow=True)

        add_text('Fitting Space: ')
        pan.Add(wids['ffit_fitspace'])

        add_text('k weightings: ', newrow=False)
        pan.Add(wids['ffit_kweight'])

        add_text('k min: ')
        pan.Add(ffit_kmin)
        add_text(' k max: ', newrow=False)
        pan.Add(ffit_kmax)

        add_text('k Window: ')
        pan.Add(wids['ffit_kwindow'])
        add_text('dk: ', newrow=False)
        pan.Add(ffit_dk)

        add_text('R min: ')
        pan.Add(ffit_rmin)
        add_text('R max: ', newrow=False)
        pan.Add(ffit_rmax)

        pan.Add(HLine(pan, size=(600, 2)), dcol=6, newrow=True)

        pan.Add(self.plotmodel_btn, dcol=2, newrow=True)
        pan.Add(self.fitmodel_btn, dcol=2, newrow=True)

        pan.Add(self.fitselected_btn)
        pan.Add((5, 5), newrow=True)
        
        pan.Add(HLine(self, size=(600, 2)), dcol=6, newrow=True)
        pan.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(pan, 0, LEFT, 3)
        sizer.Add((10, 10), 0, LEFT, 3)
        sizer.Add(self.paths_nb,  1, LEFT|wx.GROW, 5)

        pack(self, sizer)

    def get_config(self, dgroup=None):
        """get processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()

        conf = getattr(dgroup, 'feffit_config', {})
        if 'kmin' not in conf:
            conf = defaults

        dgroup.feffit_config = conf
        if not hasattr(dgroup, 'feffit'):
            dgroup.feffit = Group()

        return conf

    def fill_form(self, dat):
        print("Fill Form ", dat, type(dat))
        if isinstance(dat, Group):
            if not hasattr(dat, 'chi'):
                self.xasmain.process_exafs(dat)
            if hasattr(dat, 'feffit'):
                self.wids['ffit_kmin'].SetValue(dat.feffit.kmin)
                self.wids['ffit_kmax'].SetValue(dat.feffit.kmax)
                self.wids['ffit_rmin'].SetValue(dat.feffit.rmin)
                self.wids['ffit_rmax'].SetValue(dat.feffit.rmax)
                self.wids['ffit_dk'].SetValue(dat.feffit.dk)
        elif isinstance(dat, dict):
            # self.wids['ppeak_e0'].SetValue(dat['e0'])
            self.wids['ppeak_emin'].SetValue(dat['emin'])
            self.wids['ppeak_emax'].SetValue(dat['emax'])
            self.wids['ppeak_elo'].SetValue(dat['elo'])
            self.wids['ppeak_ehi'].SetValue(dat['ehi'])

    def read_form(self):
        "read for, returning dict of values"
        dgroup = self.controller.get_group()
        array_desc = self.array_choice.GetStringSelection()
        bline_form = self.bline_choice.GetStringSelection()
        form_opts = {'gname': dgroup.groupname,
                     'filename': dgroup.filename,
                     'array_desc': array_desc.lower(),
                     'array_name': Array_Choices[array_desc],
                     'baseline_form': bline_form.lower(),
                     'bkg_components': []}

        # form_opts['e0'] = self.wids['ppeak_e0'].GetValue()
        form_opts['emin'] = self.wids['ppeak_emin'].GetValue()
        form_opts['emax'] = self.wids['ppeak_emax'].GetValue()
        form_opts['elo'] = self.wids['ppeak_elo'].GetValue()
        form_opts['ehi'] = self.wids['ppeak_ehi'].GetValue()
        form_opts['plot_sub_bline'] = False # self.plot_sub_bline.IsChecked()
        # form_opts['show_centroid'] = self.show_centroid.IsChecked()
        form_opts['show_peakrange'] = self.show_peakrange.IsChecked()
        form_opts['show_fitrange'] = self.show_fitrange.IsChecked()
        return form_opts


    def fill_model_params(self, prefix, params):
        comp = self.fit_components[prefix]
        parwids = comp.parwids
        for pname, par in params.items():
            pname = prefix + pname
            if pname in parwids:
                wids = parwids[pname]
                if wids.minval is not None:
                    wids.minval.SetValue(par.min)
                if wids.maxval is not None:
                    wids.maxval.SetValue(par.max)
                wids.value.SetValue(par.value)
                varstr = 'vary' if par.vary else 'fix'
                if par.expr is not None:
                    varstr = 'constrain'
                if wids.vary is not None:
                    wids.vary.SetStringSelection(varstr)

    def onPlotModel(self, evt=None):
        dgroup = self.controller.get_group()
        g = self.build_fitmodel(dgroup.groupname)
        self.onPlot(show_init=True)

    def onPlot(self, evt=None, baseline_only=False, show_init=False):
        opts = self.read_form()
        dgroup = self.controller.get_group()
        opts['group'] = opts['gname']
        self.larch_eval(COMMANDS['prepeaks_setup'].format(**opts))

        cmd = "plot_prepeaks_fit"
        args = ['{gname}']
        if baseline_only:
            cmd = "plot_prepeaks_baseline"
        else:
            args.append("show_init=%s" % (show_init))
        cmd = "%s(%s)" % (cmd, ', '.join(args))
        self.larch_eval(cmd.format(**opts))

    def add_path(self, feffdat_file,  feffresult):
        pathinfo = None
        folder, fp_file = os.path.split(feffdat_file)
        folder, dirname = os.path.split(folder)
        for path in feffresult.paths:
            if path.filename == fp_file:
                pathinfo = path
                break
        atoms = [s.strip() for s in pathinfo.geom.split('>')]
        atoms.pop()
        atoms[0] = atoms[0].replace('[', '').replace(']', '')
        title = '>'.join(atoms)
        i = 0
        while title in self.paths_data:
            i +=1
            title = ('>'.join(atoms)) + '_%d' % i

        self.paths_data[title] = (feffdat_file, feffresult.folder,
                                  feffresult.absorber, feffresult.edge,
                                  pathinfo)
        user_label = f'{title:s}, Reff={pathinfo.reff:.4f}'
        pathpanel = FeffPathPanel(parent=self.paths_nb, title=title,
                                  npath=len(self.paths_data),
                                  user_label=user_label,
                                  feffdat_file=fp_file, dirname=dirname,
                                  fullpath=feffdat_file,
                                  absorber=feffresult.absorber,
                                  edge=feffresult.edge, reff=pathinfo.reff,
                                  degen=pathinfo.degeneracy,
                                  geom=pathinfo.geom, _larch=self.larch,
                                  xasmain=self.xasmain)

        self.paths_nb.AddPage(pathpanel, f' {title:s} ', True)
        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))
        
    def onRemovePath(self, label='__', event=None):
        print('--- remove path ', label)
              
    def addModel(self, event=None, model=None, prefix=None, isbkg=False):
        if model is None and event is not None:
            model = event.GetString()
        if model is None or model.startswith('<'):
            return

        self.models_peaks.SetSelection(0)
        self.models_other.SetSelection(0)

        if prefix is None:
            p = model[:5].lower()
            curmodels = ["%s%i_" % (p, i+1) for i in range(1+len(self.fit_components))]
            for comp in self.fit_components:
                if comp in curmodels:
                    curmodels.remove(comp)

            prefix = curmodels[0]

        label = "%s(prefix='%s')" % (model, prefix)
        title = "%s: %s " % (prefix[:-1], model)
        title = prefix[:-1]
        mclass_kws = {'prefix': prefix}
        if 'step' in model.lower():
            form = model.lower().replace('step', '').strip()
            if form.startswith('err'):
                form = 'erf'
            label = "Step(form='%s', prefix='%s')" % (form, prefix)
            title = "%s: Step %s" % (prefix[:-1], form[:3])
            mclass = lm_models.StepModel
            mclass_kws['form'] = form
            minst = mclass(form=form, prefix=prefix)
        else:
            if model in ModelFuncs:
                mclass = getattr(lm_models, ModelFuncs[model])
            else:
                mclass = getattr(lm_models, model+'Model')

            minst = mclass(prefix=prefix)

        panel = GridPanel(self.paths_nb, ncols=2, nrows=5, pad=1, itemstyle=CEN)

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label,
                               size=size, style=wx.ALIGN_LEFT, **kws)
        usebox = Check(panel, default=True, label='Use in Fit?', size=(100, -1))
        bkgbox = Check(panel, default=False, label='Is Baseline?', size=(125, -1))
        if isbkg:
            bkgbox.SetValue(1)

        delbtn = Button(panel, 'Delete This Component', size=(200, -1),
                        action=partial(self.onDeleteComponent, prefix=prefix))

        pick2msg = SimpleText(panel, "    ", size=(125, -1))
        pick2btn = Button(panel, 'Pick Values from Plot', size=(200, -1),
                          action=partial(self.onPick2Points, prefix=prefix))

        # SetTip(mname,  'Label for the model component')
        SetTip(usebox,   'Use this component in fit?')
        SetTip(bkgbox,   'Label this component as "background" when plotting?')
        SetTip(delbtn,   'Delete this model component')
        SetTip(pick2btn, 'Select X range on Plot to Guess Initial Values')

        panel.Add(SLabel(label, size=(275, -1), colour='#0000AA'),
                  dcol=4,  style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(usebox, dcol=2)
        panel.Add(bkgbox, dcol=1, style=RIGHT)

        panel.Add(pick2btn, dcol=2, style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(pick2msg, dcol=3, style=wx.ALIGN_RIGHT)
        panel.Add(delbtn, dcol=2, style=wx.ALIGN_RIGHT)

        panel.Add(SLabel("Parameter "), style=wx.ALIGN_LEFT,  newrow=True)
        panel.AddMany((SLabel(" Value"), SLabel(" Type"), SLabel(' Bounds'),
                       SLabel("  Min", size=(60, -1)),
                       SLabel("  Max", size=(60, -1)),  SLabel(" Expression")))

        parwids = {}
        parnames = sorted(minst.param_names)

        for a in minst._func_allargs:
            pname = "%s%s" % (prefix, a)
            if (pname not in parnames and
                a in minst.param_hints and
                a not in minst.independent_vars):
                parnames.append(pname)

        for pname in parnames:
            sname = pname[len(prefix):]
            hints = minst.param_hints.get(sname, {})

            par = Parameter(name=pname, value=0, vary=True)
            if 'min' in hints:
                par.min = hints['min']
            if 'max' in hints:
                par.max = hints['max']
            if 'value' in hints:
                par.value = hints['value']
            if 'expr' in hints:
                par.expr = hints['expr']

            pwids = ParameterWidgets(panel, par, name_size=100, expr_size=150,
                                     float_size=80, prefix=prefix,
                                     widgets=('name', 'value',  'minval',
                                              'maxval', 'vary', 'expr'))
            parwids[par.name] = pwids
            panel.Add(pwids.name, newrow=True)

            panel.AddMany((pwids.value, pwids.vary, pwids.bounds,
                           pwids.minval, pwids.maxval, pwids.expr))

        for sname, hint in minst.param_hints.items():
            pname = "%s%s" % (prefix, sname)
            if 'expr' in hint and pname not in parnames:
                par = Parameter(name=pname, value=0, expr=hint['expr'])
                pwids = ParameterWidgets(panel, par, name_size=100, expr_size=400,
                                         float_size=80, prefix=prefix,
                                         widgets=('name', 'value', 'expr'))
                parwids[par.name] = pwids
                panel.Add(pwids.name, newrow=True)
                panel.Add(pwids.value)
                panel.Add(pwids.expr, dcol=5, style=wx.ALIGN_RIGHT)
                pwids.value.Disable()

        fgroup = Group(prefix=prefix, title=title, mclass=mclass,
                       mclass_kws=mclass_kws, usebox=usebox, panel=panel,
                       parwids=parwids, float_size=65, expr_size=150,
                       pick2_msg=pick2msg, bkgbox=bkgbox)


        self.fit_components[prefix] = fgroup
        panel.pack()

        self.paths_nb.AddPage(panel, title, True)
        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))
        self.fitmodel_btn.Enable()
        self.fitselected_btn.Enable()


    def onDeleteComponent(self, evt=None, prefix=None):
        fgroup = self.fit_components.get(prefix, None)
        if fgroup is None:
            return

        for i in range(self.paths_nb.GetPageCount()):
            if fgroup.title == self.paths_nb.GetPageText(i):
                self.paths_nb.DeletePage(i)

        for attr in dir(fgroup):
            setattr(fgroup, attr, None)

        self.fit_components.pop(prefix)
        if len(self.fit_components) < 1:
            self.fitmodel_btn.Disable()
            self.fitselected_btn.Enable()


    def onPick2Timer(self, evt=None):
        """checks for 'Pick 2' events, and initiates 'Pick 2' guess
        for a model from the selected data range
        """
        try:
            plotframe = self.controller.get_display(win=1)
            curhist = plotframe.cursor_hist[:]
            plotframe.Raise()
        except:
            return

        if (time.time() - self.pick2_t0) > self.pick2_timeout:
            msg = self.pick2_group.pick2_msg.SetLabel(" ")
            plotframe.cursor_hist = []
            self.pick2_timer.Stop()
            return

        if len(curhist) < 2:
            self.pick2_group.pick2_msg.SetLabel("%i/2" % (len(curhist)))
            return

        self.pick2_group.pick2_msg.SetLabel("done.")
        self.pick2_timer.Stop()

        # guess param values
        xcur = (curhist[0][0], curhist[1][0])
        xmin, xmax = min(xcur), max(xcur)

        dgroup = getattr(self.larch.symtable, self.controller.groupname)
        x, y = dgroup.xdat, dgroup.ydat
        i0 = index_of(dgroup.xdat, xmin)
        i1 = index_of(dgroup.xdat, xmax)
        x, y = dgroup.xdat[i0:i1+1], dgroup.ydat[i0:i1+1]

        mod = self.pick2_group.mclass(prefix=self.pick2_group.prefix)
        parwids = self.pick2_group.parwids
        try:
            guesses = mod.guess(y, x=x)
        except:
            return
        for name, param in guesses.items():
            if 'amplitude' in name:
                param.value *= 1.5
            elif 'sigma' in name:
                param.value *= 0.75
            if name in parwids:
                parwids[name].value.SetValue(param.value)

        dgroup._tmp = mod.eval(guesses, x=dgroup.xdat)
        plotframe = self.controller.get_display(win=1)
        plotframe.cursor_hist = []
        plotframe.oplot(dgroup.xdat, dgroup._tmp)
        self.pick2erase_panel = plotframe.panel

        self.pick2erase_timer.Start(60000)


    def onPick2Points(self, evt=None, prefix=None):
        fgroup = self.fit_components.get(prefix, None)
        if fgroup is None:
            return

        plotframe = self.controller.get_display(win=1)
        plotframe.Raise()

        plotframe.cursor_hist = []
        fgroup.npts = 0
        self.pick2_group = fgroup

        if fgroup.pick2_msg is not None:
            fgroup.pick2_msg.SetLabel("0/2")

        self.pick2_t0 = time.time()
        self.pick2_timer.Start(1000)


    def onLoadFitResult(self, event=None):
        dlg = wx.FileDialog(self, message="Load Saved Pre-edge Model",
                            wildcard=ModelWcards, style=wx.FD_OPEN)
        rfile = None
        if dlg.ShowModal() == wx.ID_OK:
            rfile = dlg.GetPath()
        dlg.Destroy()

        if rfile is None:
            return

        self.larch_eval("# peakmodel = lm_load_modelresult('%s')" %rfile)

        result = load_modelresult(str(rfile))
        for prefix in list(self.fit_components.keys()):
            self.onDeleteComponent(prefix=prefix)

        for comp in result.model.components:
            isbkg = comp.prefix in result.user_options['bkg_components']
            self.addModel(model=comp.func.__name__,
                          prefix=comp.prefix, isbkg=isbkg)

        for comp in result.model.components:
            parwids = self.fit_components[comp.prefix].parwids
            for pname, par in result.params.items():
                if pname in parwids:
                    wids = parwids[pname]
                    if wids.minval is not None:
                        wids.minval.SetValue(par.min)
                    if wids.maxval is not None:
                        wids.maxval.SetValue(par.max)
                    val = result.init_values.get(pname, par.value)
                    wids.value.SetValue(val)
                    varstr = 'vary' if par.vary else 'fix'
                    if par.expr is not None:
                        varstr = 'constrain'
                    if wids.vary is not None:
                        wids.vary.SetStringSelection(varstr)

        self.fill_form(result.user_options)


    def onSelPoint(self, evt=None, opt='__', relative_e0=False, win=None):
        """
        get last selected point from a specified plot window
        and fill in the value for the widget defined by `opt`.

        by default it finds the latest cursor position from the
        cursor history of the first 20 plot windows.
        """
        if opt not in self.wids:
            return None

        _x, _y = last_cursor_pos(win=win, _larch=self.larch)

        if _x is not None:
            if relative_e0 and 'e0' in self.wids:
                _x -= self.wids['e0'].GetValue()
            self.wids[opt].SetValue(_x)

    def get_xranges(self, x):
        opts = self.read_form()
        dgroup = self.controller.get_group()
        en_eps = min(np.diff(dgroup.energy)) / 5.

        i1 = index_of(x, opts['emin'] + en_eps)
        i2 = index_of(x, opts['emax'] + en_eps) + 1
        return i1, i2

    def build_fitmodel(self, groupname=None):
        """ use fit components to build model"""
        # self.summary = {'components': [], 'options': {}}
        peaks = []
        cmds = ["## set up pre-edge peak parameters", "peakpars = Parameters()"]
        modcmds = ["## define pre-edge peak model"]
        modop = " ="
        opts = self.read_form()
        if groupname is None:
            groupname = opts['gname']

        opts['group'] = groupname
        dgroup = self.controller.get_group(groupname)
        self.larch_eval(COMMANDS['prepeaks_setup'].format(**opts))

        for comp in self.fit_components.values():
            _cen, _amp = None, None
            if comp.usebox is not None and comp.usebox.IsChecked():
                for parwids in comp.parwids.values():
                    this = parwids.param
                    pargs = ["'%s'" % this.name, 'value=%f' % (this.value),
                             'min=%f' % (this.min), 'max=%f' % (this.max)]
                    if this.expr is not None:
                        pargs.append("expr='%s'" % (this.expr))
                    elif not this.vary:
                        pargs.pop()
                        pargs.pop()
                        pargs.append("vary=False")

                    cmds.append("peakpars.add(%s)" % (', '.join(pargs)))
                    if this.name.endswith('_center'):
                        _cen = this.name
                    elif parwids.param.name.endswith('_amplitude'):
                        _amp = this.name
                compargs = ["%s='%s'" % (k,v) for k,v in comp.mclass_kws.items()]
                modcmds.append("peakmodel %s %s(%s)" % (modop, comp.mclass.__name__,
                                                        ', '.join(compargs)))

                modop = "+="
                if not comp.bkgbox.IsChecked() and _cen is not None and _amp is not None:
                    peaks.append((_amp, _cen))

        if len(peaks) > 0:
            denom = '+'.join([p[0] for p in peaks])
            numer = '+'.join(["%s*%s "% p for p in peaks])
            cmds.append("peakpars.add('fit_centroid', expr='(%s)/(%s)')" % (numer, denom))

        cmds.extend(modcmds)
        cmds.append(COMMANDS['prepfit'].format(group=dgroup.groupname,
                                               user_opts=repr(opts)))

        self.larch_eval("\n".join(cmds))

    def onFitSelected(self, event=None):
        dgroup = self.controller.get_group()
        if dgroup is None:
            return

        opts = self.read_form()

        self.show_subframe('prepeak_result', PrePeakFitResultFrame,
                           datagroup=dgroup, peakframe=self)

        selected_groups = self.controller.filelist.GetCheckedStrings()
        groups = [self.controller.file_groups[cn] for cn in selected_groups]
        ngroups = len(groups)
        for igroup, gname in enumerate(groups):
            dgroup = self.controller.get_group(gname)
            if not hasattr(dgroup, 'norm'):
                self.xasmain.process_normalization(dgroup)
            self.build_fitmodel(gname)
            opts['group'] = opts['gname']
            self.larch_eval(COMMANDS['prepeaks_setup'].format(**opts))
            ppeaks = dgroup.prepeaks

            # add bkg_component to saved user options
            bkg_comps = []
            for label, comp in self.fit_components.items():
                if comp.bkgbox.IsChecked():
                    bkg_comps.append(label)
            opts['bkg_components'] = bkg_comps
            imin, imax = self.get_xranges(dgroup.xdat)
            cmds = ["## do peak fit for group %s / %s " % (gname, dgroup.filename) ]

            yerr_type = 'set_yerr_const'
            yerr = getattr(dgroup, 'yerr', None)
            if yerr is None:
                if hasattr(dgroup, 'norm_std'):
                    cmds.append("{group}.yerr = {group}.norm_std")
                    yerr_type = 'set_yerr_array'
                elif hasattr(dgroup, 'mu_std'):
                    cmds.append("{group}.yerr = {group}.mu_std/(1.e-15+{group}.edge_step)")
                    yerr_type = 'set_yerr_array'
                else:
                    cmds.append("{group}.yerr = 1")
            elif isinstance(dgroup.yerr, np.ndarray):
                    yerr_type = 'set_yerr_array'

            cmds.extend([COMMANDS[yerr_type], COMMANDS['dofit']])
            cmd = '\n'.join(cmds)
            self.larch_eval(cmd.format(group=dgroup.groupname,
                                       imin=imin, imax=imax,
                                       user_opts=repr(opts)))

            self.autosave_modelresult(self.larch_get("peakresult"))
            self.subframes['prepeak_result'].add_results(dgroup, form=opts,
                                                         larch_eval=self.larch_eval,
                                                         show=igroup==ngroups-1)


    def onFitModel(self, event=None):
        dgroup = self.controller.get_group()
        if dgroup is None:
            return
        self.build_fitmodel(dgroup.groupname)
        opts = self.read_form()

        dgroup = self.controller.get_group()
        opts['group'] = opts['gname']
        self.larch_eval(COMMANDS['prepeaks_setup'].format(**opts))

        ppeaks = dgroup.prepeaks

        # add bkg_component to saved user options
        bkg_comps = []
        for label, comp in self.fit_components.items():
            if comp.bkgbox.IsChecked():
                bkg_comps.append(label)
        opts['bkg_components'] = bkg_comps

        imin, imax = self.get_xranges(dgroup.xdat)

        cmds = ["## do peak fit: "]

        yerr_type = 'set_yerr_const'
        yerr = getattr(dgroup, 'yerr', None)
        if yerr is None:
            if hasattr(dgroup, 'norm_std'):
                cmds.append("{group}.yerr = {group}.norm_std")
                yerr_type = 'set_yerr_array'
            elif hasattr(dgroup, 'mu_std'):
                cmds.append("{group}.yerr = {group}.mu_std/(1.e-15+{group}.edge_step)")
                yerr_type = 'set_yerr_array'
            else:
                cmds.append("{group}.yerr = 1")
        elif isinstance(dgroup.yerr, np.ndarray):
                yerr_type = 'set_yerr_array'


        cmds.extend([COMMANDS[yerr_type], COMMANDS['dofit']])

        cmd = '\n'.join(cmds)
        self.larch_eval(cmd.format(group=dgroup.groupname,
                                   imin=imin, imax=imax,
                                   user_opts=repr(opts)))

        self.autosave_modelresult(self.larch_get("peakresult"))

        self.onPlot()
        self.show_subframe('prepeak_result', PrePeakFitResultFrame,
                                  datagroup=dgroup, peakframe=self)
        self.subframes['prepeak_result'].add_results(dgroup, form=opts,
                                                     larch_eval=self.larch_eval)

    def update_start_values(self, params):
        """fill parameters with best fit values"""
        allparwids = {}
        for comp in self.fit_components.values():
            if comp.usebox is not None and comp.usebox.IsChecked():
                for name, parwids in comp.parwids.items():
                    allparwids[name] = parwids

        for pname, par in params.items():
            if pname in allparwids:
                allparwids[pname].value.SetValue(par.value)

    def autosave_modelresult(self, result, fname=None):
        """autosave model result to user larch folder"""
        confdir = os.path.join(site_config.user_larchdir, 'xas_viewer')
        if not os.path.exists(confdir):
            try:
                os.makedirs(confdir)
            except OSError:
                print("Warning: cannot create XAS_Viewer user folder")
                return
        if fname is None:
            fname = 'autosave.fitmodel'
        save_modelresult(result, os.path.join(confdir, fname))
