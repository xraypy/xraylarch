import time
import sys
from pathlib import Path
import numpy as np
np.seterr(all='ignore')

from functools import partial
import json
import time
import traceback
from copy import deepcopy

import wx
import wx.lib.scrolledpanel as scrolled

import wx.dataview as dv

from lmfit import Parameter
import lmfit.models as lm_models
from pyshortcuts import uname, gformat, fix_varname

from larch import Group, site_config
from larch.utils import mkdir
from larch.math import index_of
from larch.io.export_modelresult import export_modelresult
from larch.io import save_groups, read_groups

from larch.wxlib import (ReportFrame, BitmapButton, FloatCtrl,
                         FloatSpin, SetTip, GridPanel, get_icon,
                         SimpleText, pack, Button, HLine, Choice,
                         Check, MenuItem, GUI_COLORS, set_color, CEN,
                         RIGHT, LEFT, FRAMESTYLE, Font, FONTSIZE,
                         FONTSIZE_FW, FileSave, FileOpen,
                         flatnotebook, Popup, EditableListBox,
                         ExceptionPopup, set_plotwindow_title)

from larch.wxlib.parameter import ParameterWidgets
from larch.wxlib.plotter import last_cursor_pos
from larch.wxlib.xafsplots import extend_plotrange
from .taskpanel import TaskPanel
from .config import PrePeak_ArrayChoices, PlotWindowChoices

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

ModelChoices = {'other': ('<General Models>', 'Constant', 'Linear',
                          'Quadratic', 'Exponential', 'PowerLaw',
                          'Linear Step', 'Arctan Step',
                          'ErrorFunction Step', 'Logisic Step', 'Rectangle'),
                'peaks': ('<Peak Models>', 'Gaussian', 'Lorentzian',
                          'Voigt', 'PseudoVoigt', 'DampedHarmonicOscillator',
                          'Pearson7', 'StudentsT', 'SkewedGaussian',
                          'Moffat', 'BreitWigner', 'Doniach', 'Lognormal'),
                }


# map of lmfit function name to Model Class
ModelFuncs = {'constant': 'ConstantModel',
              'linear': 'LinearModel',
              'quadratic': 'QuadraticModel',
              'polynomial': 'PolynomialModel',
              'gaussian': 'GaussianModel',
              'lorentzian': 'LorentzianModel',
              'voigt': 'VoigtModel',
              'pvoigt': 'PseudoVoigtModel',
              'moffat': 'MoffatModel',
              'pearson7': 'Pearson7Model',
              'students_t': 'StudentsTModel',
              'breit_wigner': 'BreitWignerModel',
              'lognormal': 'LognormalModel',
              'damped_oscillator': 'DampedOscillatorModel',
              'dho': 'DampedHarmonicOscillatorModel',
              'expgaussian': 'ExponentialGaussianModel',
              'skewed_gaussian': 'SkewedGaussianModel',
              'doniach': 'DoniachModel',
              'powerlaw': 'PowerLawModel',
              'exponential': 'ExponentialModel',
              'step': 'StepModel',
              'rectangle': 'RectangleModel'}

ModelAbbrevs = {'Constant': 'const',
               'Linear': 'line',
               'Quadratic': 'quad',
               'Exponential': 'exp',
               'PowerLaw': 'pow',
               'Linear Step': 'line_step',
               'Arctan Step': 'atan_step',
               'ErrorFunction Step': 'erf_step',
               'Logistic Step': 'logi_step',
               'Rectangle': 'rect',
               'Gaussian': 'gauss',
               'Lorentzian': 'loren',
               'Voigt': 'voigt',
               'PseudoVoigt': 'pvoigt',
               'DampedHarmonicOscillator': 'dho',
               'Pearson7': 'pear7',
               'StudentsT': 'studt',
               'SkewedGaussian': 'sgauss',
               'Moffat': 'moffat',
               'BreitWigner': 'breit',
               'Doniach': 'doniach',
               'Lognormal': 'lognorm'}

BaselineFuncs = ['No Baseline',
                 'Constant+Lorentzian',
                 'Linear+Lorentzian',
                 'Constant+Gaussian',
                 'Linear+Gaussian',
                 'Constant+Voigt',
                 'Linear+Voigt',
                 'Constant+ArcTan Step',
                 'Constant+ErrorFunction Step',
                 'Quadratic', 'Linear']


PLOT_BASELINE = 'Data+Baseline'
PLOT_FIT      = 'Data+Fit'
PLOT_INIT     = 'Data+Init Fit'
PLOT_RESID    = 'Data+Residual'
PlotChoices = [PLOT_BASELINE, PLOT_FIT, PLOT_RESID]

FitMethods = ("Levenberg-Marquardt", "Nelder-Mead", "Powell")
ModelWcards = "Fit Models(*.modl)|*.modl|All files (*.*)|*.*"
DataWcards = "Data Files(*.dat)|*.dat|All files (*.*)|*.*"


MIN_CORREL = 0.10

COMMANDS = {}
COMMANDS['prepfit'] = """# prepare fit
{group}.prepeaks.user_options = {user_opts:s}
{group}.prepeaks.init_fit = peakmodel.eval(peakpars, x={group}.prepeaks.energy)
{group}.prepeaks.init_ycomps = peakmodel.eval_components(params=peakpars, x={group}.prepeaks.energy)
{group}.prepeaks.peakmodel = {{'model': deepcopy(peakmodel), 'params': deepcopy(peakpars)}}
if not hasattr({group}.prepeaks, 'fit_history'): {group}.prepeaks.fit_history = []
"""

COMMANDS['prepeaks_setup'] = """# setup prepeaks
if not hasattr({group}, 'energy'): {group:s}.energy = 1.0*{group:s}.xplot
{group:s}.xplot = 1.0*{group:s}.energy
{group:s}.yplot = 1.0*{group:s}.{array_name:s}
prepeaks_setup(energy={group:s}, arrayname='{array_name:s}', elo={elo:.3f}, ehi={ehi:.3f},
               emin={emin:.3f}, emax={emax:.3f})
"""

COMMANDS['set_yerr_const'] = "{group}.prepeaks.norm_std = {group}.yerr*ones(len({group}.prepeaks.norm))"
COMMANDS['set_yerr_array'] = """
{group}.prepeaks.norm_std = 1.0*{group}.yerr[{imin:d}:{imax:d}]
yerr_min = 1.e-9*{group}.prepeaks.yplot.mean()
{group}.prepeaks.norm_std[where({group}.yerr < yerr_min)] = yerr_min
"""

COMMANDS['dofit'] = """# do fit
peakresult = prepeaks_fit({group}, peakmodel, peakpars)
peakresult.user_options = {user_opts:s}
"""

def get_model_abbrev(modelname):
    if modelname in ModelAbbrevs:
        return ModelAbbrevs[modelname]
    return fix_varname(modelname).lower()

def get_xlims(x, xmin, xmax):
    xeps = min(np.diff(x))/ 5.
    i1 = index_of(x, xmin + xeps)
    i2 = index_of(x, xmax + xeps) + 1
    return i1, i2

class PrePeakFitResultFrame(wx.Frame):
    config_sect = 'prepeak'
    def __init__(self, parent=None, peakframe=None, datagroup=None, **kws):
        wx.Frame.__init__(self, None, -1, title='Pre-edge Peak Fit Results',
                          style=FRAMESTYLE, size=(950, 700), **kws)
        self.peakframe = peakframe

        if datagroup is not None:
            self.datagroup = datagroup
            # prepeaks = getattr(datagroup, 'prepeaks', None)
            # self.peakfit_history = getattr(prepeaks, 'fit_history', [])
        self.parent = parent
        self.datasets = {}
        self.form = {}
        self.larch_eval = self.peakframe.larch_eval
        self.nfit = 0
        self.createMenus()
        self.build()

        if datagroup is None:
            symtab = self.peakframe.larch.symtable
            xasgroups = getattr(symtab, '_xasgroups', None)
            if xasgroups is not None:
                for dname, dgroup in xasgroups.items():
                    dgroup = getattr(symtab, dgroup, None)
                    ppeak = getattr(dgroup, 'prepeaks', None)
                    hist =  getattr(ppeak, 'fit_history', None)
                    if hist is not None:
                        self.add_results(dgroup, show=True)


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

        self.filelist = EditableListBox(splitter, self.ShowDataSet,
                                        size=(250, -1))
        set_color(self.filelist, 'list_fg', bg='list_bg')

        panel = scrolled.ScrolledPanel(splitter)

        panel.SetMinSize((775, 575))
        self.font_fixedwidth = wx.Font(FONTSIZE_FW, wx.MODERN, wx.NORMAL, wx.BOLD)

        # title row
        self.wids = wids = {}
        title = SimpleText(panel, 'Fit Results', font=Font(FONTSIZE+2),
                           colour=GUI_COLORS.title, style=LEFT)

        wids['data_title'] = SimpleText(panel, '< > ', font=Font(FONTSIZE+2),
                                        minsize=(350, -1),
                                        colour=GUI_COLORS.title, style=LEFT)

        opts = dict(default=False, size=(200, -1), action=self.onPlot)
        ppanel = wx.Panel(panel)
        wids['plot_bline'] = Check(ppanel, label='Plot baseline-subtracted?', **opts)
        wids['plot_resid'] = Check(ppanel, label='Plot with residual?', **opts)
        wids['plot_win']   = Choice(ppanel, size=(60, -1), choices=PlotWindowChoices,
                                    action=self.onPlot)
        wids['plot_win'].SetStringSelection('1')

        psizer = wx.BoxSizer(wx.HORIZONTAL)
        psizer.Add( wids['plot_bline'], 0, 5)
        psizer.Add( wids['plot_resid'], 0, 5)
        psizer.Add(SimpleText(ppanel, 'Plot Window:'), 0, 5)
        psizer.Add( wids['plot_win'], 0, 5)

        pack(ppanel, psizer)

        wids['load_model'] = Button(panel, 'Load this Model for Fitting',
                                    size=(250, -1), action=self.onLoadModel)

        wids['plot_choice'] = Button(panel, 'Plot This Fit',
                                     size=(125, -1), action=self.onPlot)

        wids['fit_label'] = wx.TextCtrl(panel, -1, ' ', size=(175, -1))
        wids['set_label'] = Button(panel, 'Update Label', size=(150, -1),
                                   action=self.onUpdateLabel)
        wids['del_fit'] = Button(panel, 'Remove from Fit History', size=(200, -1),
                                 action=self.onRemoveFromHistory)



        irow = 0
        sizer.Add(title,              (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['data_title'], (irow, 1), (1, 3), LEFT)

        irow += 1
        wids['model_desc'] = SimpleText(panel, '<Model>', font=Font(FONTSIZE+1),
                                        size=(750, 50), style=LEFT)
        sizer.Add(wids['model_desc'],  (irow, 0), (1, 6), LEFT)

        irow += 1
        sizer.Add(wids['load_model'],(irow, 0), (1, 2), LEFT)

        irow += 1
        sizer.Add(wids['plot_choice'],(irow, 0), (1, 1), LEFT)
        sizer.Add(ppanel, (irow, 1), (1, 4), LEFT)


        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LEFT)

        irow += 1
        sizer.Add(SimpleText(panel, 'Fit Label:', style=LEFT), (irow, 0), (1, 1), LEFT)
        sizer.Add(wids['fit_label'], (irow, 1), (1, 1), LEFT)
        sizer.Add(wids['set_label'], (irow, 2), (1, 1), LEFT)
        sizer.Add(wids['del_fit'], (irow, 3), (1, 2), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Fit Statistics]]',  font=Font(FONTSIZE+2),
                           colour=GUI_COLORS.title, style=LEFT)
        subtitle = SimpleText(panel, ' (most recent fit is at the top)',
                              font=Font(FONTSIZE+1),  style=LEFT)

        sizer.Add(title, (irow, 0), (1, 1), LEFT)
        sizer.Add(subtitle, (irow, 1), (1, 1), LEFT)

        sview = self.wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)

        sview.SetFont(self.font_fixedwidth)

        xw = (170, 75, 75, 110, 115, 115, 100)
        if uname=='darwin':
            xw = (150, 70, 70, 90, 95, 95, 95)


        sview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectFit)
        sview.AppendTextColumn('Label',  width=xw[0])
        sview.AppendTextColumn('Ndata', width=xw[1])
        sview.AppendTextColumn('Nvary', width=xw[2])
        sview.AppendTextColumn('\u03c7\u00B2', width=xw[3])
        sview.AppendTextColumn('reduced \u03c7\u00B2', width=xw[4])
        sview.AppendTextColumn('Akaike Info', width=xw[5])
        sview.AppendTextColumn('R^2', width=xw[6])

        for col in range(sview.ColumnCount):
            this = sview.Columns[col]
            this.Sortable = True
            this.Alignment = wx.ALIGN_RIGHT if col > 0 else wx.ALIGN_LEFT
            this.Renderer.Alignment = this.Alignment

        sview.SetMinSize((775, 150))

        irow += 1
        sizer.Add(sview, (irow, 0), (1, 5), LEFT)

        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Variables]]',  font=Font(FONTSIZE+2),
                           colour=GUI_COLORS.title, style=LEFT)
        sizer.Add(title, (irow, 0), (1, 1), LEFT)

        self.wids['use_model'] = Button(panel, 'Use Model in Pre-Edge Peaks',
                                          size=(250, -1), action=self.onCopyModel)
        self.wids['copy_params'] = Button(panel, 'Update Model with best-fit values',
                                          size=(250, -1), action=self.onCopyParams)

        sizer.Add(self.wids['use_model'], (irow, 1), (1, 2), LEFT)
        sizer.Add(self.wids['copy_params'], (irow, 3), (1, 2), LEFT)

        pview = self.wids['params'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        pview.SetFont(self.font_fixedwidth)
        self.wids['paramsdata'] = []

        xw = (180, 140, 150, 250)
        if uname=='darwin':
            xw = (180, 110, 110, 250)
        pview.AppendTextColumn('Parameter',  width=xw[0])
        pview.AppendTextColumn('Best Value', width=xw[1])
        pview.AppendTextColumn('1-\u03c3 Uncertainty', width=xw[2])
        pview.AppendTextColumn('Initial value or constraint expression',     width=xw[3])

        for col in range(4):
            this = pview.Columns[col]
            this.Sortable = False
            this.Alignment = wx.ALIGN_RIGHT if col in (1, 2) else wx.ALIGN_LEFT
            this.Renderer.Alignment = this.Alignment

        pview.SetMinSize((775, 200))
        pview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectParameter)

        irow += 1
        sizer.Add(pview, (irow, 0), (1, 5), LEFT)

        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LEFT)

        irow += 1
        title = SimpleText(panel, '[[Correlations]]',  font=Font(FONTSIZE+2),
                           colour=GUI_COLORS.title, style=LEFT)

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
        cview.SetFont(self.font_fixedwidth)


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
        cview.SetMinSize((475, 150))

        irow += 1
        sizer.Add(cview, (irow, 0), (1, 5), LEFT)

        pack(panel, sizer)
        panel.SetupScrolling()

        splitter.SplitVertically(self.filelist, panel, 1)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def onUpdateLabel(self, event=None):
        result = self.get_fitresult()
        item = self.wids['stats'].GetSelectedRow()
        result.label = self.wids['fit_label'].GetValue()
        self.show_results()

    def onRemoveFromHistory(self, event=None):
        result = self.get_fitresult()
        if wx.ID_YES != Popup(self,
                              f"Remove fit '{result.label}' from history?\nThis cannot be undone.",
                              "Remove fit?", style=wx.YES_NO):
                return

        self.datagroup.prepeaks.fit_history.pop(self.nfit)
        self.nfit = 0
        self.show_results()


    def onSaveAllStats(self, evt=None):
        "Save Parameters and Statistics to CSV"
        # get first dataset to extract fit parameter names
        fnames = self.filelist.GetItems()
        if len(fnames) == 0:
            return

        deffile = "PrePeaksResults.csv"
        wcards  = 'CVS Files (*.csv)|*.csv|All files (*.*)|*.*'
        path = FileSave(self, 'Save Parameter and Statistics for Pre-edge Peak Fits',
                        default_file=deffile, wildcard=wcards)
        if path is None:
            return

        if Path(path).exists() and uname != 'darwin':  # darwin prompts in FileSave!
            if wx.ID_YES != Popup(self,
                                  "Overwrite existing Statistics File?",
                                  "Overwrite existing file?", style=wx.YES_NO):
                return


        out = ['# Pre-edge Peak Fit Report %s' % time.ctime(),
               '# For ful details, each fit must be saved individually',
               '#--------------------']


        param_names = []
        for name, dgroup in self.datasets.items():
            if not hasattr(dgroup, 'prepeaks'):
                continue
            for pkfit in getattr(dgroup.prepeaks, 'fit_history', []):
                try:
                    xparams = pkfit.result.params.keys()
                except Expcetion:
                    xparams = []
                for pname in reversed(xparams):
                    if pname not in param_names:
                        param_names.append(pname)

        labels = [('Data Set' + ' '*25)[:25], 'Group name', 'Fit Label',
                 'n_data', 'n_varys', 'chi-square',
                 'reduced_chi-square', 'akaike_info', 'bayesian_info',
                 'R^2']

        for pname in param_names:
            labels.append(pname)
            labels.append(pname+'_stderr')
        out.append('# %s' % (', '.join(labels)))
        for name, dgroup in self.datasets.items():
            # print(name, dgroup, hasattr(dgroup, 'prepeaks'))
            if not hasattr(dgroup, 'prepeaks'):
                continue
            i = 0
            for pkfit in getattr(dgroup.prepeaks, 'fit_history', []):
                i += 1
                try:
                    xparams = pkfit.result.params.keys()
                except Expcetion:
                    print('   no params')
                    continue

                result = pkfit.result
                label = getattr(pkfit, 'label', f'fit #{i}')
                dat = [dgroup.filename, dgroup.groupname, label,
                        f'{result.ndata}', f'{result.nvarys}']
                for attr in ('chisqr', 'redchi', 'aic', 'bic', 'rsquared'):
                    dat.append(gformat(getattr(result, attr), 11))
                for pname in param_names:
                    val = stderr = 'unused'
                    if pname in result.params:
                        par = result.params[pname]
                        val = gformat(par.value, 11)
                        stderr = 'nan'
                        if par.stderr is not None:
                            stderr = gformat(par.stderr, 11)
                    dat.append(val)
                    dat.append(stderr)
                out.append(', '.join(dat))
        out.append('')

        with open(path, 'w', encoding=sys.getdefaultencoding()) as fh:
            fh.write('\n'.join(out))

    def onSaveFitResult(self, event=None):
        deffile = self.datagroup.filename.replace('.', '_') + 'peak.modl'
        sfile = FileSave(self, 'Save Fit Model', default_file=deffile,
                           wildcard=ModelWcards)
        if sfile is not None:
            pkfit = self.get_fitresult()
            save_groups(sfile, ['#peakfit 1.0', pkfit])

    def onExportFitResult(self, event=None):
        dgroup = self.datagroup
        deffile = dgroup.filename.replace('.', '_') + '.xdi'
        wcards = 'All files (*.*)|*.*'

        outfile = FileSave(self, 'Export Fit Result', default_file=deffile)

        if outfile is not None:
            pkfit = self.get_fitresult()
            result = pkfit.result
            export_modelresult(result, filename=outfile,
                               label=pkfit.label,
                               datafile=dgroup.filename,
                               xdata=pkfit.energy, ydata=pkfit.norm,
                               yerr=pkfit.norm_std)


    def get_fitresult(self, nfit=None):
        if nfit is None:
            nfit = self.nfit
        self.peakfit_history = getattr(self.datagroup.prepeaks, 'fit_history', [])
        self.nfit = max(0, nfit)
        if self.nfit > len(self.peakfit_history):
            self.nfit = 0
        if len(self.peakfit_history) > 0:
            return self.peakfit_history[self.nfit]

    def onPlot(self, event=None):
        """Modified onPlot method for PrePeakFitResultFrame with auto-scaling"""
        show_resid = self.wids['plot_resid'].IsChecked()
        sub_bline = self.wids['plot_bline'].IsChecked()
        win = int(self.wids['plot_win'].GetStringSelection())

        self.peakframe.controller.set_datatask_name(self.peakframe.title)

        cmd = "plot_prepeaks_fit(%s, nfit=%i, show_residual=%s, subtract_baseline=%s, win=%d)"
        cmd = cmd % (self.datagroup.groupname, self.nfit, show_resid, sub_bline, win)
        self.peakframe.larch_eval(cmd)
        self.peakframe.controller.set_focus(topwin=self)

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
        this = result.result.params[pname]
        if this.correl is not None:
            sort_correl = sorted(this.correl.items(), key=lambda it: abs(it[1]))
            for name, corval in reversed(sort_correl):
                if abs(corval) > cormin:
                    self.wids['correl'].AppendItem((pname, name, "% .4f" % corval))

    def onAllCorrel(self, evt=None):
        result = self.get_fitresult()
        params = result.result.params
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

    def onLoadModel(self, event=None):
        self.peakframe.use_modelresult(modelresult=self.get_fitresult(),
                                       ddgroup=self.datagroup)

    def onCopyModel(self, evt=None):
        dataset = evt.GetString()
        group = self.datasets.get(evt.GetString(), None)
        result = self.get_fitresult()
        self.peakframe.use_modelresult(modelresult=result, dgroup=group)

    def onCopyParams(self, evt=None):
        result = self.get_fitresult()
        self.peakframe.update_start_values(result.result.params)

    def ShowDataSet(self, evt=None):
        dataset = evt.GetString()
        group = self.datasets.get(evt.GetString(), None)
        if group is not None:
            self.show_results(datagroup=group, show_plot=True)

    def add_results(self, dgroup, form=None, larch_eval=None, show=True):
        name = dgroup.filename
        if name not in self.filelist.GetItems():
            self.filelist.Append(name)
        self.datasets[name] = dgroup
        if show:
            self.show_results(datagroup=dgroup, form=form, larch_eval=larch_eval)

    def show_results(self, datagroup=None, form=None, show_plot=False, larch_eval=None):
        """Modified show_results method with auto-scaling"""
        if datagroup is not None:
            self.datagroup = datagroup
        if larch_eval is not None:
            self.larch_eval = larch_eval

        datagroup = self.datagroup
        self.peakfit_history = getattr(self.datagroup.prepeaks, 'fit_history', [])
        # cur = self.get_fitresult()
        wids = self.wids
        wids['stats'].DeleteAllItems()
        for i, res in enumerate(self.peakfit_history):
            args = [res.label]
            for attr in ('ndata', 'nvarys', 'chisqr', 'redchi',
                        'aic', 'rsquared'):
                val = getattr(res.result, attr)
                if isinstance(val, int):
                    val = '%d' % val
                elif attr == 'rsquared':
                    val = f"{val:.5f}"
                else:
                    val = gformat(val, 10)
                args.append(val)
            wids['stats'].AppendItem(tuple(args))
        wids['data_title'].SetLabel(self.datagroup.filename)
        self.show_fitresult(nfit=0)

        if show_plot:
            show_resid = self.wids['plot_resid'].IsChecked()
            sub_bline = self.wids['plot_bline'].IsChecked()
            win = int(self.wids['plot_win'].GetStringSelection())

            cmd = "plot_prepeaks_fit(%s, nfit=0, show_residual=%s, subtract_baseline=%s, win=%d)"
            cmd = cmd % (datagroup.groupname, show_resid, sub_bline, win)

            self.peakframe.larch_eval(cmd)
            # self.set_prepeak_plot_limits(dgroup=datagroup, win=win, nfit=0)
            self.peakframe.controller.set_focus(topwin=self)

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
        try:
            wids['fit_label'].SetValue(result.label)
            wids['data_title'].SetLabel(self.datagroup.filename)
            wids['model_desc'].SetLabel(self.get_model_desc(result.result.model))
            valid_result = True
        except:
            valid_result = False

        wids['params'].DeleteAllItems()
        wids['paramsdata'] = []
        if valid_result:
            for param in reversed(result.result.params.values()):
                pname = param.name
                try:
                    val = gformat(param.value, 9)
                except (TypeError, ValueError):
                    val = ' ??? '
                serr = ' N/A '
                if param.stderr is not None:
                    serr = gformat(param.stderr, 8)
                extra = ' '
                if param.expr is not None:
                    extra = '= %s ' % param.expr
                elif not param.vary:
                    extra = f'(fixed to {gformat(param.init_value, 9)}'
                elif param.init_value is not None:
                    extra = gformat(param.init_value, 9)

                wids['params'].AppendItem((pname, val, serr, extra))
                wids['paramsdata'].append(pname)
        self.Refresh()

class PrePeakPanel(TaskPanel):
    def __init__(self, parent=None, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller, panel='prepeaks', **kws)
        self.fit_components = {}
        self.user_added_params = None

        self.pick2_timer = wx.Timer(self)
        self.pick2_group = None
        self.Bind(wx.EVT_TIMER, self.onPick2Timer, self.pick2_timer)
        self.pick2_t0 = 0.
        self.pick2_timeout = 15.

        self.pick2erase_timer = wx.Timer(self)
        self.pick2erase_panel = None
        self.Bind(wx.EVT_TIMER, self.onPick2EraseTimer, self.pick2erase_timer)

    def onPanelExposed(self, **kws):
        # called when notebook is selected
        try:
            fname = self.controller.filelist.GetStringSelection()
            gname = self.controller.file_groups[fname]
            dgroup = self.controller.get_group(gname)
            self.ensure_xas_processed(dgroup)
            self.fill_form(dgroup, newgroup=True)
        except Exception:
            pass

    def onModelPanelExposed(self, event=None, **kws):
        pass

    def build_display(self):
        pan = self.panel # = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LEFT)

        self.wids = {}

        fsopts = dict(digits=2, increment=0.25, min_val=-999999,
                      max_val=999999, size=(125, -1), with_pin=True,
                      action=self.set_config)

        ppeak_elo  = self.add_floatspin('ppeak_elo',  value=-13, **fsopts)
        ppeak_ehi  = self.add_floatspin('ppeak_ehi',  value=-3, **fsopts)
        ppeak_emin = self.add_floatspin('ppeak_emin', value=-20, **fsopts)
        ppeak_emax = self.add_floatspin('ppeak_emax', value=0, **fsopts)

        self.loadresults_btn = Button(pan, 'Load Fit Result',
                                      action=self.onLoadFitResult, size=(165, -1))
        self.showresults_btn = Button(pan, 'Show Fit Results',
                                      action=self.onShowResults, size=(165, -1))
        self.showresults_btn.Disable()

        self.fitbline_btn  = Button(pan,'Fit Baseline', action=self.onFitBaseline,
                                    size=(165, -1))

        self.plotmodel_btn = Button(pan,
                                    'Plot Current Model',
                                    action=self.onPlotModel,  size=(165, -1))
        self.fitmodel_btn = Button(pan, 'Fit Current Group',
                                   action=self.onFitModel,  size=(165, -1))
        self.fitmodel_btn.Disable()
        self.fitselected_btn = Button(pan, 'Fit Selected Groups',
                                      action=self.onFitSelected,  size=(165, -1))
        self.fitselected_btn.Disable()
        self.fitmodel_btn.Disable()

        self.array_choice = Choice(pan, size=(200, -1),
                                   choices=list(PrePeak_ArrayChoices.keys()))
        self.array_choice.SetSelection(0)

        self.bline_choice = Choice(pan, size=(200, -1),
                                   choices=BaselineFuncs)
        self.bline_choice.SetSelection(2)

        models_peaks = Choice(pan, size=(200, -1),
                              choices=ModelChoices['peaks'],
                              action=self.addModel)

        models_other = Choice(pan, size=(200, -1),
                              choices=ModelChoices['other'],
                              action=self.addModel)

        self.models_peaks = models_peaks
        self.models_other = models_other


        self.message = SimpleText(pan,
                                 'first fit baseline, then add peaks to fit model.')

        opts = dict(default=True, size=(75, -1), action=self.onPlot)
        self.show_peakrange = Check(pan, label='show?', **opts)
        self.show_fitrange  = Check(pan, label='show?', **opts)
        self.use_baseline = Check(pan, label='Fit Baseline before main peaks?',
                                  default=True,  size=(300, -1),
                                  action=self.onEnableBaseline)

        opts = dict(default=False, size=(200, -1), action=self.onPlot)

        def add_text(text, dcol=1, newrow=True):
            pan.Add(SimpleText(pan, text), dcol=dcol, newrow=newrow)

        pan.Add(SimpleText(pan, 'Pre-edge Peak Fitting',
                           size=(350, -1), **self.titleopts), style=LEFT, dcol=5)
        pan.Add(self.loadresults_btn)

        add_text('Array to fit: ')
        pan.Add(self.array_choice, dcol=3)
        pan.Add((5,5))
        pan.Add(self.showresults_btn)


        add_text('Fit X/Energy Range: ')
        pan.Add(ppeak_emin)
        add_text(' : ', newrow=False)
        pan.Add(ppeak_emax)
        pan.Add(self.show_fitrange)

        pan.Add(HLine(pan, size=(600, 2)), dcol=6, newrow=True)

        pan.Add(SimpleText(pan, 'Fit Baseline: '), newrow=True)
        pan.Add(self.use_baseline, dcol=4)
        pan.Add(SimpleText(pan, 'Baseline Form: '), newrow=True)
        t = SimpleText(pan, 'Baseline Skip Range: ')
        SetTip(t, 'Range skipped over for baseline fit')
        pan.Add(self.bline_choice, dcol=3)
        pan.Add((10, 10))
        pan.Add(self.fitbline_btn)

        pan.Add(t, newrow=True)
        pan.Add(ppeak_elo)
        add_text(' : ', newrow=False)
        pan.Add(ppeak_ehi)

        pan.Add(self.show_peakrange)
        pan.Add(HLine(pan, size=(600, 2)), dcol=6, newrow=True)

        #  add model
        ts = wx.BoxSizer(wx.HORIZONTAL)
        ts.Add(models_peaks)
        ts.Add(models_other)

        pan.Add(SimpleText(pan, 'Add Component: '), newrow=True)
        pan.Add(ts, dcol=4)
        pan.Add(self.plotmodel_btn)

        pan.Add(SimpleText(pan, 'Fit Model to Current Group : '), dcol=5, newrow=True)
        pan.Add(self.fitmodel_btn)

        pan.Add(SimpleText(pan, 'Messages: '), newrow=True)
        pan.Add(self.message, dcol=4)
        pan.Add(self.fitselected_btn)

        pan.Add(HLine(pan, size=(600, 2)), dcol=6, newrow=True)
        pan.pack()

        self.mod_nb = flatnotebook(self, {}, on_change=self.onModelPanelExposed)
        self.mod_nb_init = True
        dummy_panel = wx.Panel(self.mod_nb)

        self.mod_nb.AddPage(dummy_panel, 'Empty Model', True)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((5, 5), 0, LEFT, 3)
        sizer.Add(pan, 0, LEFT, 3)
        sizer.Add((5, 5), 0, LEFT, 3)
        sizer.Add(self.mod_nb,  1, LEFT|wx.GROW, 5)

        pack(self, sizer)


    def onEnableBaseline(self, event=None, **kws):
        use_baseline = self.use_baseline.IsChecked()
        self.bline_choice.Enable(use_baseline)
        self.fitbline_btn.Enable(use_baseline)
        self.show_peakrange.Enable(use_baseline)
        self.wids['ppeak_elo'].Enable(use_baseline)
        self.wids['ppeak_ehi'].Enable(use_baseline)
        message = 'First Fit Baseline, then add model to fit spectra'
        if not use_baseline:
            message = 'Ignoring "Baseline" -- build model to fit spectra'
        self.message.SetLabel(message)

    def get_config(self, dgroup=None):
        """get processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()
        conf = getattr(dgroup, 'prepeak_config', {})
        if 'e0' not in conf:
            conf = self.get_defaultconfig()
            conf['e0'] = getattr(dgroup, 'e0', -1)

        dgroup.prepeak_config = conf
        if not hasattr(dgroup, 'prepeaks'):
            dgroup.prepeaks = Group()
        return conf

    def set_config(self, event=None):
        dgroup = self.controller.get_group()
        conf = getattr(dgroup, 'prepeak_config', {})
        fopts = self.read_form()
        for attr in ('elo', 'ehi', 'emin', 'emax'):
            conf[attr]  = fopts[attr]
        dgroup.prepeak_config = conf

    def fill_form(self, dgroup, newgroup=False):
        # print("prepeak.fill_form ", dgroup, type(dgroup))
        if isinstance(dgroup, Group):
            if not hasattr(dgroup, 'norm'):
                self.parent.process_normalization(dgroup)
            conf = getattr(dgroup, 'prepeak_config', {})
            for attr in ('elo', 'ehi', 'emin', 'emax'):
                if attr in conf:
                    self.wids[f'ppeak_{attr}'].SetValue(conf[attr])

        elif isinstance(dgroup, dict):
            self.wids['ppeak_emin'].SetValue(dgroup['emin'])
            self.wids['ppeak_emax'].SetValue(dgroup['emax'])
            self.wids['ppeak_elo'].SetValue(dgroup['elo'])
            self.wids['ppeak_ehi'].SetValue(dgroup['ehi'])

            self.array_choice.SetStringSelection(dgroup['array_desc'])
            self.bline_choice.SetStringSelection(dgroup['baseline_form'])

            self.show_fitrange.Enable(dgroup['show_fitrange'])
            self.show_peakrange.Enable(dgroup['show_peakrange'])

        if newgroup and isinstance(dgroup, Group):
            modelresult = None
            prepeaks = getattr(dgroup, 'prepeaks', None)
            if prepeaks is None:
                modelresult = getattr(self.larch.symtable, 'peakresult', None)
                # print("use result from global peakresult ", modelresult)
            else:
                peakmodel = getattr(prepeaks, 'peakmodel', None)
                user_opts = getattr(prepeaks, 'user_options', None)
                if peakmodel is None:
                    modelresult = getattr(prepeaks, 'fit_history', [None])[0]
                    # print("use modelresult from history ", modelresult)

            if modelresult is not None or peakmodel is not None:
                self.showresults_btn.Enable()
                # print("-> use model_result ", modelresult, peakmodel, dgroup)
                self.use_modelresult(modelresult=modelresult, dgroup=dgroup,
                                    peakmodel=peakmodel, user_opts=user_opts)


    def read_form(self):
        "read for, returning dict of values"
        dgroup = self.controller.get_group()
        array_desc = self.array_choice.GetStringSelection()
        bline_form = self.bline_choice.GetStringSelection()
        form_opts = {'gname': dgroup.groupname,
                     'filename': dgroup.filename,
                     'array_desc': array_desc.lower(),
                     'array_name': PrePeak_ArrayChoices[array_desc],
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

    def onFitBaseline(self, evt=None):
        """Modified onFitBaseline with plot scaling fix"""
        opts = self.read_form()
        bline_form  = opts.get('baseline_form', 'no baseline')
        if bline_form.startswith('no base'):
            return
        bline_form = bline_form.replace('arctan step', 'atan_step').replace('errorfunction step', 'erf_step')
        opts['bline_form'] = bline_form

        cmd = """{gname:s}.yplot = 1.0*{gname:s}.{array_name:s}
    pre_edge_baseline(energy={gname:s}.energy, norm={gname:s}.yplot,
                    group={gname:s}, form='{bline_form:s}',
                    elo={elo:.3f}, ehi={ehi:.3f}, emin={emin:.3f}, emax={emax:.3f})"""
        self.larch_eval(cmd.format(**opts))

        dgroup = self.controller.get_group()
        ppeaks = dgroup.prepeaks
        dgroup.centroid_msg = "%.4f +/- %.4f eV" % (ppeaks.centroid,
                                                    ppeaks.delta_centroid)

        self.message.SetLabel("Centroid= %s" % dgroup.centroid_msg)

        if '+' in bline_form:
            bforms = [f.lower() for f in bline_form.split('+')]
        else:
            bforms = [bline_form.lower(), '']

        poly_model = peak_model = None
        for bform in bforms:
            if bform.startswith('line'):
                poly_model = 'Linear'
            elif bform.startswith('const'):
                poly_model = 'Constant'
            if bform.startswith('quad'):
                poly_model = 'Quadratic'
            elif bform.startswith('loren'):
                peak_model = 'Lorentzian'
            elif bform.startswith('guass'):
                peak_model = 'Gaussian'
            elif bform.startswith('voigt'):
                peak_model = 'Voigt'
            elif bform.startswith('atan_step'):
                peak_model = 'atan_step'
            elif bform.startswith('erf_step'):
                peak_model = 'erf_step'

        if peak_model is not None:
            if 'bpeak_' in self.fit_components:
                self.onDeleteComponent(prefix='bpeak_')
            self.addModel(model=peak_model, prefix='bpeak_', isbkg=True)

        if poly_model is not None:
            if 'bpoly_' in self.fit_components:
                self.onDeleteComponent(prefix='bpoly_')
            self.addModel(model=poly_model, prefix='bpoly_', isbkg=True)

        for prefix in ('bpeak_', 'bpoly_'):
            if prefix in self.fit_components:
                cmp = self.fit_components[prefix]
                self.fill_model_params(prefix, dgroup.prepeaks.fit_details.params)

        self.fill_form(dgroup)
        self.fitmodel_btn.Enable()
        self.fitselected_btn.Enable()

        i1, i2 = self.get_xranges(dgroup.energy)
        dgroup.yfit = dgroup.xfit = 0.0*dgroup.energy[i1:i2]

        # Plot with proper scaling
        self.onPlot(baseline_only=True)


    def onSaveBaseline(self, evt=None):
        opts = self.read_form()

        dgroup = self.controller.get_group()
        ppeaks = dgroup.prepeaks

        deffile = dgroup.filename.replace('.', '_') + '_baseline.dat'
        sfile = FileSave(self, 'Save Pre-edge Peak Baseline', default_file=deffile,
                         wildcard=DataWcards)
        if sfile is None:
            return
        opts['savefile'] = sfile
        opts['centroid'] = ppeaks.centroid
        opts['delta_centroid'] = ppeaks.delta_centroid

        cmd = """# save baseline script:
header = ['baseline data from "{filename:s}"',
          'baseline form = "{baseline_form:s}"',
          'baseline fit range emin = {emin:.3f}',
          'baseline fit range emax = {emax:.3f}',
          'baseline peak range elo = {elo:.3f}',
          'baseline peak range ehi = {ehi:.3f}',
          'prepeak centroid energy = {centroid:.3f} +/- {delta_centroid:.3f} eV']
i0 = index_of({gname:s}.energy, {gname:s}.prepeaks.energy[0])
i1 = index_of({gname:s}.energy, {gname:s}.prepeaks.energy[-1])
{gname:s}.prepeaks.full_baseline = {gname:s}.norm*1.0
{gname:s}.prepeaks.full_baseline[i0:i1+1] = {gname:s}.prepeaks.baseline

write_ascii('{savefile:s}', {gname:s}.energy, {gname:s}.norm, {gname:s}.prepeaks.full_baseline,
             header=header, label='energy           norm            baseline')
             """
        self.larch_eval(cmd.format(**opts))


    def fill_model_params(self, prefix, params):
        comp = self.fit_components[prefix]
        parwids = comp.parwids
        for pname, par in params.items():
            pname = prefix + pname
            if pname in parwids:
                wids = parwids[pname]
                wids.value.SetValue(par.value)
                if wids.minval is not None:
                    wids.minval.SetValue(par.min)
                if wids.maxval is not None:
                    wids.maxval.SetValue(par.max)
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
        """Modified onPlot method with proper absolute energy scaling"""
        opts = self.read_form()
        dgroup = self.controller.get_group()
        opts['group'] = opts['gname']

        self.controller.set_datatask_name(self.title)

        # Run the prepeaks setup first
        self.larch_eval(COMMANDS['prepeaks_setup'].format(**opts))

        ppeaks_opts = dict(array=opts['array_name'], elo=opts['elo'],
                        ehi=opts['ehi'], emin=opts['emin'],
                        emax=opts['emax'])
        dgroup.journal.add_ifnew('prepeaks_setup', ppeaks_opts)

        # Do the plotting
        cmd = "plot_prepeaks_fit"
        args = ['{gname}']
        if baseline_only:
            cmd = "plot_prepeaks_baseline"
        else:
            args.append("show_init=%s" % (show_init))
        cmd = "%s(%s)" % (cmd, ', '.join(args))
        self.larch_eval(cmd.format(**opts))
        self.controller.set_focus()

    def addModel(self, event=None, model=None, prefix=None, isbkg=False, opts=None):
        if model is None and event is not None:
            model = event.GetString()
        if model is None or model.startswith('<'):
            return

        self.models_peaks.SetSelection(0)
        self.models_other.SetSelection(0)

        mod_abbrev = get_model_abbrev(model)

        opts = self.read_form()
        dgroup = self.controller.get_group()
        has_data = getattr(dgroup, 'yplot', None) is not None
        is_peakmodel = model in ModelChoices['peaks']

        if prefix is None:
            curmodels = ["%s%i_" % (mod_abbrev, i+1) for i in range(1+len(self.fit_components))]
            for comp in self.fit_components:
                if comp in curmodels:
                    curmodels.remove(comp)

            prefix = curmodels[0]

        label = "%s(prefix='%s')" % (model, prefix)
        title = "%s: %s " % (prefix[:-1], model)
        title = prefix[:-1]
        mclass_kws = {'prefix': prefix}
        if 'step' in mod_abbrev:
            form = prefix.split('_')[0]
            for sname, fullname in (('lin', 'linear'), ('atan', 'arctan'),
                                    ('err', 'erf'), ('logi', 'logistic')):
                if form.startswith(sname):
                    form = fullname
            if form not in ('linear', 'erf', 'arctan', 'logistic'):
                if opts is None:
                    opts = {'form': 'linear'}
                form = opts.get('form', 'linear')

            label = "Step(form='%s', prefix='%s')" % (form, prefix)
            title = "%s: Step %s" % (prefix[:-1], form[:3])
            mclass = lm_models.StepModel
            mclass_kws['form'] = form
            minst = mclass(form=form, prefix=prefix,
                           independent_vars=['x', 'form'])
        else:
            if model in ModelFuncs:
                mclass = getattr(lm_models, ModelFuncs[model])
            else:
                mclass = getattr(lm_models, model+'Model')

            minst = mclass(prefix=prefix)

        panel = GridPanel(self.mod_nb, ncols=2, nrows=5, pad=1, itemstyle=CEN)
        panel.SetFont(Font(FONTSIZE))

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

        panel.Add(SLabel(label, size=(275, -1), colour=GUI_COLORS.title_blue),
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

        if has_data:
            xdata = getattr(dgroup, 'xplot', np.arange(2))
            ydata = getattr(dgroup, 'yplot', np.arange(2))

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
            value = 0.0
            if is_peakmodel and 'sigma' in pname:
                value = 1.0
                if has_data:
                    value = max(0.5, 0.1*(opts['ehi'] - opts['elo']))
            elif is_peakmodel and 'center' in pname:
                value = 1.0
                if has_data:
                    value = int((opts['ehi'] + opts['elo'])/2.0)
            elif is_peakmodel and 'ampl' in pname:
                value = 1.0
                if has_data:
                    value = np.ptp(ydata)
            if 'value' in hints:
                value = hints['value']

            par = Parameter(name=pname, value=value, vary=True)
            if 'min' in hints:
                par.min = hints['min']
            if 'max' in hints:
                par.max = hints['max']
            if 'expr' in hints:
                par.expr = hints['expr']

            pwids = ParameterWidgets(panel, par, name_size=110,
                                     expr_size=200,
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
                pwids = ParameterWidgets(panel, par, name_size=110,
                                         expr_size=400,
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
        if self.mod_nb_init:
            self.mod_nb.DeletePage(0)
            self.mod_nb_init = False

        self.mod_nb.AddPage(panel, title, True)
        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))
        self.fitmodel_btn.Enable()
        self.fitselected_btn.Enable()


    def onDeleteComponent(self, evt=None, prefix=None):
        fgroup = self.fit_components.get(prefix, None)
        if fgroup is None:
            return

        for i in range(self.mod_nb.GetPageCount()):
            if fgroup.title == self.mod_nb.GetPageText(i):
                self.mod_nb.DeletePage(i)

        for attr in dir(fgroup):
            setattr(fgroup, attr, None)

        self.fit_components.pop(prefix)
        if len(self.fit_components) < 1:
            self.fitmodel_btn.Disable()
            self.fitselected_btn.Enable()

    def onPick2EraseTimer(self, evt=None):
        """erases line trace showing automated 'Pick 2' guess """
        self.pick2erase_timer.Stop()
        panel = self.pick2erase_panel
        ntrace = panel.conf.ntrace - 1
        trace = panel.conf.get_mpl_line(ntrace)

        panel.conf.get_mpl_line(ntrace).set_data(np.array([]), np.array([]))
        panel.conf.ntrace = ntrace
        panel.draw()

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
        i0 = index_of(dgroup.xplot, xmin)
        i1 = index_of(dgroup.xplot, xmax)
        x, y = dgroup.xplot[i0:i1+1], dgroup.yplot[i0:i1+1]

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

        dgroup._tmp = mod.eval(guesses, x=dgroup.xplot)
        plotframe = self.controller.get_display(win=1)

        plotframe.cursor_hist = []
        plotframe.oplot(dgroup.xplot, dgroup._tmp)
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
        rfile = FileOpen(self, "Load Saved Pre-edge Model",
                         wildcard=ModelWcards)
        if rfile is None:
            return

        self.larch_eval(f"# peakmodel = read_groups('{rfile}')[1]")
        dat = read_groups(str(rfile))
        if len(dat) != 2 or not dat[0].startswith('#peakfit'):
            Popup(self, f" '{rfile}' is not a valid Peak Model file",
                  "Invalid file")

        self.use_modelresult(modelresult=dat[1])

    def use_modelresult(self, modelresult=None, peakmodel=None, user_opts=None, dgroup=None):
        for prefix in list(self.fit_components.keys()):
            self.onDeleteComponent(prefix=prefix)

        if modelresult is not None:
            params = modelresult.result.params
            model = modelresult.result.model
            user_opts = modelresult.user_options
        elif peakmodel is not None and user_opts is not None:
            model = peakmodel['model']
            params = peakmodel['params']

        if dgroup is None:
            dgroup = self.controller.get_group()
        if not hasattr(dgroup, 'prepeaks'):
            dgroup.prepeaks = Group()

        dgroup.prepeaks.user_options = {k: v for k, v in user_opts.items()}
        dgroup.prepeaks.peakmodel = {'model': deepcopy(model), 'params': deepcopy(params)}

        bkg_comps = user_opts['bkg_components']
        for comp in model.components:
            self.addModel(model=comp.func.__name__,
                          prefix=comp.prefix, isbkg=(comp.prefix in bkg_comps),
                          opts=comp.opts)

        for comp in model.components:
            parwids = self.fit_components[comp.prefix].parwids
            for pname, par in params.items():
                if pname in parwids:
                    wids = parwids[pname]
                    wids.value.SetValue(par.init_value)
                    varstr = 'vary' if par.vary else 'fix'
                    if par.expr is not None:
                        varstr = 'constrain'
                    if wids.vary is not None:
                        wids.vary.SetStringSelection(varstr)
                    if wids.minval is not None:
                        wids.minval.SetValue(par.min)
                    if wids.maxval is not None:
                        wids.maxval.SetValue(par.max)

        # print("use modelresult -- > fill form ", user_opts)
        self.fill_form(user_opts)


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
        # print(f"Build Fit Model {groupname=}")
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

        ppeaks_opts = dict(array=opts['array_name'], elo=opts['elo'],
                           ehi=opts['ehi'], emin=opts['emin'],
                           emax=opts['emax'])
        dgroup.journal.add_ifnew('prepeaks_setup', ppeaks_opts)

        bkg_comps = []
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
                if comp.bkgbox.IsChecked():
                    bkg_comps.append(comp.mclass_kws.get('prefix', ''))
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
                self.parent.process_normalization(dgroup)
            self.build_fitmodel(gname)
            opts['group'] = opts['gname']
            self.larch_eval(COMMANDS['prepeaks_setup'].format(**opts))

            ppeaks_opts = dict(array=opts['array_name'], elo=opts['elo'],
                               ehi=opts['ehi'], emin=opts['emin'],
                               emax=opts['emax'])
            dgroup.journal.add_ifnew('prepeaks_setup', ppeaks_opts)
            ppeaks = dgroup.prepeaks

            # add bkg_component to saved user options
            bkg_comps = []
            for label, comp in self.fit_components.items():
                if comp.bkgbox.IsChecked():
                    bkg_comps.append(label)

            opts['bkg_components'] = bkg_comps
            imin, imax = self.get_xranges(dgroup.xplot)
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

            pkfit = self.larch_get("peakresult")
            jnl = {'label': pkfit.label, 'var_names': pkfit.result.var_names,
                   'model': repr(pkfit.result.model)}
            jnl.update(pkfit.user_options)
            dgroup.journal.add('peakfit', jnl)
            if igroup == 0:
                self.autosave_modelresult(pkfit)

            self.subframes['prepeak_result'].add_results(dgroup, form=opts,
                                                         larch_eval=self.larch_eval,
                                                         show=igroup==ngroups-1)

    def onFitModel(self, event=None):
        """Modified onFitModel with plot scaling fix"""
        dgroup = self.controller.get_group()
        if dgroup is None:
            return
        self.build_fitmodel(dgroup.groupname)
        opts = self.read_form()

        dgroup = self.controller.get_group()
        opts['group'] = opts['gname']
        self.larch_eval(COMMANDS['prepeaks_setup'].format(**opts))

        ppeaks_opts = dict(array=opts['array_name'], elo=opts['elo'],
                        ehi=opts['ehi'], emin=opts['emin'],
                        emax=opts['emax'])
        dgroup.journal.add_ifnew('prepeaks_setup', ppeaks_opts)

        ppeaks = dgroup.prepeaks

        # add bkg_component to saved user options
        bkg_comps = []
        for label, comp in self.fit_components.items():
            if comp.bkgbox.IsChecked():
                bkg_comps.append(label)
        opts['bkg_components'] = bkg_comps

        imin, imax = self.get_xranges(dgroup.xplot)

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

        # journal about peakresult
        pkfit = self.larch_get("peakresult")
        jnl = {'label': pkfit.label, 'var_names': pkfit.result.var_names,
            'model': repr(pkfit.result.model)}
        jnl.update(pkfit.user_options)
        dgroup.journal.add('peakfit', jnl)

        self.autosave_modelresult(pkfit)

        # Plot the results with proper scaling
        self.onPlot()

        self.showresults_btn.Enable()

        self.show_subframe('prepeak_result', PrePeakFitResultFrame, peakframe=self)
        self.subframes['prepeak_result'].add_results(dgroup, form=opts,
                                                    larch_eval=self.larch_eval)

    def onShowResults(self, event=None):
        self.show_subframe('prepeak_result', PrePeakFitResultFrame,
                           peakframe=self)


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
        confdir = self.controller.larix_folder
        if fname is None:
            fname = 'autosave_peakfile.modl'
        save_groups(Path(confdir, fname).as_posix(), ['#peakfit 1.0', result])
