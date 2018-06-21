#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import six
import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv

import numpy as np

from functools import partial
from collections import OrderedDict

import lmfit
from lmfit.printfuncs import gformat, fit_report

from larch import Group
from larch.utils import index_of

from larch.wxlib import (BitmapButton, FloatCtrl, FloatSpin, ToggleButton,
                         GridPanel, get_icon, SimpleText, pack, Button,
                         HLine, Choice, Check, CEN, RCEN, LCEN, Font,
                         MenuItem, FRAMESTYLE, GUIColors, FileSave)

from larch_plugins.xasgui.taskpanel import TaskPanel
from larch_plugins.io.columnfile import write_ascii

np.seterr(all='ignore')

# plot options:
norm   = six.u('Normalized \u03bC(E)')
dmude  = six.u('d\u03bC(E)/dE')
chik   = six.u('\u03c7(k)')
noplot = '<no plot>'
noname = '<none>'

FitSpace_Choices = [norm, dmude, chik]
Plot_Choices = ['Data + Sum', 'Data + Sum + Components']

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

defaults = dict(e0=0, elo=-25, ehi=75, fitspace=norm, all_combos=True,
                sum_to_one=True, show_e0=True, show_fitrange=True)

MAX_COMPONENTS = 10

def make_lcfplot(dgroup, form, nfit=0):
    """make larch plot commands to plot LCF fit from form"""
    form['nfit'] = nfit
    form['label'] = label = 'Fit #%2.2d' % (nfit+1)
    form['plotopt'] = 'show_norm=True'
    if form['arrayname'] == 'dmude':
        form['plotopt'] = 'show_deriv=True'

    erange = form['ehi'] - form['elo']
    form['pemin'] = 10*int( (form['elo'] - 5 - erange/4.0) / 10.0)
    form['pemax'] = 10*int( (form['ehi'] + 5 + erange/4.0) / 10.0)


    cmds = ["""plot_mu({group:s}, {plotopt:s}, delay_draw=True, label='data',
    emin={pemin:.1f}, emax={pemax:.1f}, title='{filename:s}, {label:s}')"""]

    if hasattr(dgroup, 'lcf_result'):
        with_comps = "Components" in form['plotchoice']
        delay = 'delay_draw=True' if with_comps else 'delay_draw=False'
        xarr = "{group:s}.lcf_result[{nfit:d}].xdata"
        yfit = "{group:s}.lcf_result[{nfit:d}].yfit"
        ycmp = "{group:s}.lcf_result[{nfit:d}].ycomps"
        cmds.append("plot(%s, %s, label='%s', zorder=30, %s)" % (xarr, yfit, label, delay))
        ncomps = len(dgroup.lcf_result[nfit].ycomps)
        if with_comps:
            for i, key in enumerate(dgroup.lcf_result[nfit].ycomps):
                delay = 'delay_draw=False' if i==(ncomps-1) else 'delay_draw=True'
                cmds.append("plot(%s, %s['%s'], label='%s', %s)" % (xarr, ycmp, key, key, delay))

    if form['show_e0']:
        cmds.append("plot_axvline({e0:1f}, color='#DDDDCC', zorder=-10)")
    if form['show_fitrange']:
        cmds.append("plot_axvline({elo_abs:1f}, color='#EECCCC', zorder=-10)")
        cmds.append("plot_axvline({ehi_abs:1f}, color='#EECCCC', zorder=-10)")

    script = "\n".join(cmds)
    return script.format(**form)

class ResultFrame(wx.Frame):
    def __init__(self, parent=None,  **kws):

        wx.Frame.__init__(self, None, -1, title='Linear Combination Results',
                          style=FRAMESTYLE, size=(675, 700), **kws)
        self.parent = parent
        self.datagroup = None
        self.form = None
        self.larch_eval = None
        self.current_fit = 0
        self.createMenus()
        self.build()

    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        m = {}

        MenuItem(self, fmenu, "Save This Fit And Components",
                 "Save Fit and Compoents to Data File",  self.onSaveFit)

        MenuItem(self, fmenu, "Save Statistics for Best N Fits",
                 "Save Statistics and Weights for Best N Fits",  self.onSaveStats)

        MenuItem(self, fmenu, "Save Data and Best N Fits",
                 "Save Data and Best N Fits",  self.onSaveMultiFits)

        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)

    def build(self):
        sizer = wx.GridBagSizer(10, 5)
        sizer.SetVGap(5)
        sizer.SetHGap(5)

        panel = scrolled.ScrolledPanel(self)
        self.SetMinSize((650, 600))
        self.colors = GUIColors()

        # title row
        self.wids = wids = {}
        title = SimpleText(panel, 'Linear Combination Results',  font=Font(12),
                           colour=self.colors.title, style=LCEN)

        wids['plot_one'] = Button(panel, 'Plot This Fit', size=(125, -1),
                                  action=self.onPlotOne)
        wids['plot_sel'] = Button(panel, 'Plot N Best Fits', size=(125, -1),
                                  action=self.onPlotSel)

        wids['plot_ntitle'] = SimpleText(panel, 'N fits to plot: ')

        wids['plot_nchoice'] = Choice(panel, size=(60, -1),
                                      choices=['%d' % i for i in range(1, 21)])
        wids['plot_nchoice'].SetStringSelection('5')

        wids['data_title'] = SimpleText(panel, '<--> ',  font=Font(12),
                                        colour=self.colors.title, style=LCEN)
        wids['nfits_title'] = SimpleText(panel, 'showing 5 best fits')

        copts = dict(size=(125, 30), default=True, action=self.onPlotOne)
        wids['show_e0'] = Check(panel, label='show E0?', **copts)
        wids['show_fitrange'] = Check(panel, label='show fit range?', **copts)

        irow = 0
        sizer.Add(title,              (irow, 0), (1, 1), LCEN)
        sizer.Add(wids['data_title'], (irow, 1), (1, 2), LCEN)

        irow += 1
        sizer.Add(wids['nfits_title'],     (irow, 0), (1, 1), LCEN)


        irow += 1
        self.wids['paramstitle'] = SimpleText(panel, '[[Parameters]]',  font=Font(12),
                                              colour=self.colors.title, style=LCEN)
        sizer.Add(self.wids['paramstitle'], (irow, 0), (1, 1), LCEN)


        pview = self.wids['params'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        pview.SetMinSize((475, 200))
        pview.AppendTextColumn(' Parameter ', width=230)
        pview.AppendTextColumn(' Best-Fit Value', width=120)
        pview.AppendTextColumn(' Standard Error ', width=120)
        for col in range(3):
            this = pview.Columns[col]
            isort, align = True, wx.ALIGN_RIGHT
            if col == 0:
                align = wx.ALIGN_LEFT
            this.Sortable = isort
            this.Alignment = this.Renderer.Alignment = align


        irow += 1
        sizer.Add(self.wids['params'],       (irow,   0), (5, 1), LCEN)
        sizer.Add(self.wids['plot_one'],     (irow,   1), (1, 2), LCEN)
        sizer.Add(self.wids['plot_sel'],     (irow+1, 1), (1, 2), LCEN)
        sizer.Add(self.wids['plot_ntitle'],  (irow+2, 1), (1, 1), LCEN)
        sizer.Add(self.wids['plot_nchoice'], (irow+2, 2), (1, 1), LCEN)
        sizer.Add(self.wids['show_e0'],      (irow+3, 1), (1, 2), LCEN)
        sizer.Add(self.wids['show_fitrange'],(irow+4, 1), (1, 2), LCEN)

        irow += 5
        sizer.Add(HLine(panel, size=(675, 3)), (irow, 0), (1, 4), LCEN)

        sview = self.wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        sview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectFitStat)
        sview.AppendTextColumn(' Fit #', width=50)
        sview.AppendTextColumn(' N_vary', width=50)
        sview.AppendTextColumn(' N_eval', width=60)
        sview.AppendTextColumn(six.u(' \u03c7\u00B2'), width=110)
        sview.AppendTextColumn(six.u(' \u03c7\u00B2_reduced'), width=110)
        sview.AppendTextColumn(' Akaike Info', width=110)
        sview.AppendTextColumn(' Bayesian Info', width=110)

        for col in range(sview.ColumnCount):
            this = sview.Columns[col]
            isort, align = True, wx.ALIGN_RIGHT
            if col == 0:
                align = wx.ALIGN_CENTER
            this.Sortable = isort
            this.Alignment = this.Renderer.Alignment = align

        sview.SetMinSize((675, 175))

        irow += 1
        title = SimpleText(panel, '[[Fit Statistics]]',  font=Font(12),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title, (irow, 0), (1, 4), LCEN)

        irow += 1
        sizer.Add(sview, (irow, 0), (1, 4), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(675, 3)), (irow, 0), (1, 4), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Weights]]',  font=Font(12),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title, (irow, 0), (1, 4), LCEN)
        self.wids['weightspanel'] = ppan = wx.Panel(self)

        p1 = SimpleText(ppan, ' < Weights > ')
        os = wx.BoxSizer(wx.VERTICAL)
        os.Add(p1, 1, 3)
        pack(ppan, os)
        ppan.SetMinSize((675, 175))

        irow += 1
        sizer.Add(ppan, (irow, 0), (1, 4), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(675, 3)), (irow, 0), (1, 4), LCEN)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        # self.SetSize((725, 750))
        self.Show()
        self.Raise()

    def show_results(self, datagroup=None, form=None, larch_eval=None):
        if datagroup is not None:
            self.datagroup = datagroup
        if form is not None:
            self.form = form
        if larch_eval is not None:
            self.larch_eval = larch_eval

        lcf_history = getattr(self.datagroup, 'lcf_history', [])

        wids = self.wids
        wids['data_title'].SetLabel(self.datagroup.filename)
        wids['show_e0'].SetValue(form['show_e0'])
        wids['show_fitrange'].SetValue(form['show_fitrange'])

        wids['stats'].DeleteAllItems()
        results = self.datagroup.lcf_result[:20]
        self.nresults = len(results)
        wids['nfits_title'].SetLabel('showing %i best results' % self.nresults)

        for i, res in enumerate(results):
            args = ['%2.2d' % (i+1)]
            for attr in ('nvarys', 'nfev', 'chisqr', 'redchi', 'aic', 'bic'):
                val = getattr(res.result, attr)
                if isinstance(val, int):
                    val = '%d' % val
                else:
                    val = gformat(val, 11)
                args.append(val)
            wids['stats'].AppendItem(tuple(args))

        wpan = self.wids['weightspanel']
        wpan.DestroyChildren()

        wview = self.wids['weights'] = dv.DataViewListCtrl(wpan, style=DVSTYLE)
        wview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectFitParam)
        wview.AppendTextColumn(' Fit #', width=50)

        for i, cname in enumerate(form['comp_names']):
            wview.AppendTextColumn(cname, width=100)
        wview.AppendTextColumn('Total', width=100)

        for col in range(len(form['comp_names'])+2):
            this = wview.Columns[col]
            isort, align = True, wx.ALIGN_RIGHT
            if col == 0:
                align = wx.ALIGN_CENTER
            this.Sortable = isort
            this.Alignment = this.Renderer.Alignment = align

        for i, res in enumerate(results):
            args = ['%2.2d' % (i+1)]
            for cname in form['comp_names'] + ['total']:
                val = '--'
                if cname in res.params:
                    val = "%.4f" % res.params[cname].value
                args.append(val)
            wview.AppendItem(tuple(args))

        os = wx.BoxSizer(wx.VERTICAL)
        os.Add(wview, 1, wx.GROW|wx.ALL)
        pack(wpan, os)

        wview.SetMinSize((675, 200))
        s1, s2 = self.GetSize()
        if s2 % 2 == 0:
            s2 = s2 + 1
        else:
            s2 = s2 - 1
        self.SetSize((s1, s2))
        self.show_fitresult(0)
        self.Refresh()

    def onSelectFitParam(self, evt=None):
        if self.wids['weights'] is None:
            return
        item = self.wids['weights'].GetSelectedRow()
        self.show_fitresult(item)

    def onSelectFitStat(self, evt=None):
        if self.wids['stats'] is None:
            return
        item = self.wids['stats'].GetSelectedRow()
        self.show_fitresult(item)

    def show_fitresult(self, n):
        fit_result = self.datagroup.lcf_result[n]
        self.current_fit = n
        wids = self.wids
        wids['nfits_title'].SetLabel('Showing Fit # %2.2d of %i Best Fits' % (n+1, self.nresults))
        wids['paramstitle'].SetLabel('[[Parameters for Fit # %2.2d]]' % (n+1))

        wids['params'].DeleteAllItems()

        for pname, par in fit_result.params.items():
            args = [pname, gformat(par.value, 11), '--']
            if par.stderr is not None:
                args[2] = gformat(par.stderr, 11)
            self.wids['params'].AppendItem(tuple(args))

    def onPlotOne(self, evt=None):
        if self.form is None or self.larch_eval is None:
            return

        for attr in ('show_e0', 'show_fitrange'):
            self.form[attr] = self.wids[attr].GetValue()

        self.larch_eval(make_lcfplot(self.datagroup,
                                     self.form, nfit=self.current_fit))

    def onPlotSel(self, evt=None):
        if self.form is None or self.larch_eval is None:
            return
        for attr in ('show_e0', 'show_fitrange'):
            self.form[attr] = self.wids[attr].GetValue()
        form = self.form
        dgroup = self.datagroup

        form['plotopt'] = 'show_norm=True'
        if form['arrayname'] == 'dmude':
            form['plotopt'] = 'show_deriv=True'

        erange = form['ehi'] - form['elo']
        form['pemin'] = 10*int( (form['elo'] - 5 - erange/4.0) / 10.0)
        form['pemax'] = 10*int( (form['ehi'] + 5 + erange/4.0) / 10.0)

        cmds = ["""plot_mu({group:s}, {plotopt:s}, delay_draw=True, label='data',
        emin={pemin:.1f}, emax={pemax:.1f}, title='{filename:s}')"""]

        nfits = int(self.wids['plot_nchoice'].GetStringSelection())
        for i in range(nfits):
            delay = 'delay_draw=True' if i<nfits-1 else 'delay_draw=False'
            xarr = "{group:s}.lcf_result[%i].xdata" % i
            yfit = "{group:s}.lcf_result[%i].yfit" % i
            lab = 'Fit #%2.2d' % (i+1)
            cmds.append("plot(%s, %s, label='%s', zorder=30, %s)" % (xarr, yfit, lab, delay))

        if form['show_e0']:
            cmds.append("plot_axvline({e0:1f}, color='#DDDDCC', zorder=-10)")
        if form['show_fitrange']:
            cmds.append("plot_axvline({elo_abs:1f}, color='#EECCCC', zorder=-10)")
            cmds.append("plot_axvline({ehi_abs:1f}, color='#EECCCC', zorder=-10)")

        script = "\n".join(cmds)
        self.larch_eval(script.format(**form))

    def onSaveFit(self, evt=None):
        "Save Fit and Compoents to Data File"
        nfit = self.current_fit
        dgroup = self.datagroup
        nfits = int(self.wids['plot_nchoice'].GetStringSelection())

        deffile = "%s_LinearFit%i.dat" % (dgroup.filename, nfit+1)
        wcards  = 'Data Files (*.dat)|*.dat|All files (*.*)|*.*'
        path = FileSave(self, 'Save Fit and Components to File',
                        default_file=deffile, wildcard=wcards)
        if path is None:
            return

        form  = self.form
        label = [' energy         ',
                 ' data           ',
                 ' best_fit       ']
        result = dgroup.lcf_result[nfit]

        header = ['Larch Linear Fit Result for Fit: #%2.2d' % (nfit+1),
                  'Dataset filename: %s ' % dgroup.filename,
                  'Larch group: %s ' % dgroup.groupname,
                  'Array name: %s' %  form['arrayname'],
                  'E0:  %f '  % form['e0'],
                  'Energy fit range: [%f, %f]' % (form['elo'], form['ehi']),
                  'Components: ']
        for key, val in result.weights.items():
            header.append('  %s: %f' % (key, val))

        report = fit_report(result.result).split('\n')
        header.extend(report)

        out = [result.xdata, result.ydata, result.yfit]
        for compname, compdata in result.ycomps.items():
            label.append(' %s' % (compname + ' '*(max(1, 15-len(compname)))))
            out.append(compdata)

        label = ' '.join(label)
        _larch = self.parent.controller.larch
        write_ascii(path, header=header, label=label, _larch=_larch, *out)


    def onSaveStats(self, evt=None):
        "Save Statistics and Weights for Best N Fits"
        dgroup = self.datagroup
        nfits = int(self.wids['plot_nchoice'].GetStringSelection())
        results = dgroup.lcf_result[:nfits]
        nresults = len(results)
        deffile = "%s_LinearStats%i.dat" % (dgroup.filename, nresults)
        wcards  = 'Data Files (*.dat)|*.dat|All files (*.*)|*.*'

        path = FileSave(self, 'Save Statistics and Weights for Best N Fits',
                        default_file=deffile, wildcard=wcards)
        if path is None:
            return
        form = self.form

        header = ['Larch Linear Fit Statistics for %2.2d best results' % (nresults),
                  'Dataset filename: %s ' % dgroup.filename,
                  'Larch group: %s ' % dgroup.groupname,
                  'Array name: %s' %  form['arrayname'],
                  'E0:  %f '  % form['e0'],
                  'Energy fit range: [%f, %f]' % (form['elo'], form['ehi']),
                  'N_Data: %d' % len(results[0].xdata)]

        label = ['fit #', 'n_varys', 'n_eval', 'chi2',
                  'chi2_reduced', 'akaike_info', 'bayesian_info']
        label.extend(form['comp_names'])
        label.append('Total')
        for i in range(len(label)):
            if len(label[i]) < 13:
                label[i] = (" %s                " % label[i])[:13]
        label = ' '.join(label)

        out = []
        for i, res in enumerate(results):
            dat = [(i+1)]
            for attr in ('nvarys', 'nfev', 'chisqr', 'redchi', 'aic', 'bic'):
                dat.append(getattr(res.result, attr))
            for cname in form['comp_names'] + ['total']:
                val = 0.0
                if cname in res.params:
                    val = res.params[cname].value
                dat.append(val)
            out.append(dat)

        out = np.array(out).transpose()
        _larch = self.parent.controller.larch
        write_ascii(path, header=header, label=label, _larch=_larch, *out)

    def onSaveMultiFits(self, evt=None):
        "Save Data and Best N Fits"
        dgroup = self.datagroup
        nfits = int(self.wids['plot_nchoice'].GetStringSelection())
        results = dgroup.lcf_result[:nfits]
        nresults = len(results)

        deffile = "%s_LinearFits%i.dat" % (dgroup.filename, nresults)
        wcards  = 'Data Files (*.dat)|*.dat|All files (*.*)|*.*'

        path = FileSave(self, 'Save Best N Fits',
                        default_file=deffile, wildcard=wcards)
        if path is None:
            return
        form = self.form
        header = ['Larch Linear Arrays for %2.2d best results' % (nresults),
                  'Dataset filename: %s ' % dgroup.filename,
                  'Larch group: %s ' % dgroup.groupname,
                  'Array name: %s' %  form['arrayname'],
                  'E0:  %f '  % form['e0'],
                  'Energy fit range: [%f, %f]' % (form['elo'], form['ehi'])]

        label = [' energy         ',  ' data           ']
        label.extend([' fit_%2.2d         ' % i for i in range(nresults)])
        label = ' '.join(label)

        out = [results[0].xdata, results[0].ydata]
        for i, res in enumerate(results):
            out.append(results[i].yfit)

        _larch = self.parent.controller.larch
        write_ascii(path, header=header, label=label, _larch=_larch, *out)


class LinearComboPanel(TaskPanel):
    """Liear Combination Panel"""
    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='lincombo_config',
                           config=defaults, **kws)

    def process(self, dgroup, **kws):
        """ handle linear combo processing"""
        if self.skip_process:
            return
        return self.read_form()

    def build_display(self):
        titleopts = dict(font=Font(12), colour='#AA0000')
        panel = self.panel
        wids = self.wids
        self.skip_process = True

        wids['fitspace'] = Choice(panel, choices=FitSpace_Choices,
                                  size=(175, -1))
        wids['fitspace'].SetStringSelection(norm)
        wids['plotchoice'] = Choice(panel, choices=Plot_Choices,
                                  size=(175, -1), action=self.onPlot)
        wids['plotchoice'].SetSelection(1)

        add_text = self.add_text

        opts = dict(digits=2, increment=1.0, relative_e0=True)

        e0_wids = self.add_floatspin('e0', value=0, **opts)
        elo_wids = self.add_floatspin('elo', value=-20, **opts)
        ehi_wids = self.add_floatspin('ehi', value=30, **opts)

        wids['fit_group'] = Button(panel, 'Fit this Group', size=(150, -1),
                                   action=self.onFitOne)
        wids['fit_selected'] = Button(panel, 'Fit Selected Groups', size=(150, -1),
                                      action=self.onFitAll)

        wids['add_selected'] = Button(panel, 'Use Selected Groups as Components', size=(250, -1),
                                      action=self.onUseSelected)

        wids['saveconf'] = Button(panel, 'Save as Default Settings', size=(200, -1),
                                  action=self.onSaveConfigBtn)

        opts = dict(default=True, size=(75, -1), action=self.onPlotOne)

        wids['show_e0']       = Check(panel, label='show?', **opts)
        wids['show_fitrange'] = Check(panel, label='show?', **opts)

        wids['sum_to_one'] = Check(panel, label='Weights Must Sum to 1?', default=True)
        wids['all_combos'] = Check(panel, label='Fit All Combinations?', default=True)

        panel.Add(SimpleText(panel, ' Linear Combination Analysis', **titleopts), dcol=4)
        add_text('Run Fit', newrow=False)

        add_text('Array to Fit: ', newrow=True)
        panel.Add(wids['fitspace'], dcol=3)
        panel.Add(wids['fit_group'])

        add_text('Plot : ', newrow=True)
        panel.Add(wids['plotchoice'], dcol=3)
        panel.Add(wids['fit_selected'])

        add_text('E0: ')
        panel.Add(e0_wids, dcol=3)
        panel.Add(wids['show_e0'])

        add_text('Fit Energy Range: ')
        panel.Add(elo_wids)
        add_text(' : ', newrow=False)
        panel.Add(ehi_wids)
        panel.Add(wids['show_fitrange'])

        panel.Add(wids['sum_to_one'], dcol=2, newrow=True)
        panel.Add(wids['all_combos'], dcol=3)

        panel.Add(HLine(panel, size=(500, 2)), dcol=5, newrow=True)

        add_text('Components: ')
        panel.Add(wids['add_selected'], dcol=4)

        groupnames = [noname] + list(self.controller.file_groups.keys())
        sgrid = GridPanel(panel, nrows=6)

        sgrid.Add(SimpleText(sgrid, "#"))
        sgrid.Add(SimpleText(sgrid, "Group"))
        sgrid.Add(SimpleText(sgrid, "Initial Weight"))
        sgrid.Add(SimpleText(sgrid, "Min Weight"))
        sgrid.Add(SimpleText(sgrid, "Max Weight"))

        fopts = dict(minval=-10, maxval=20, precision=4, size=(75, -1))
        for i in range(1, 1+MAX_COMPONENTS):
            si = ("comp", "_%2.2d" % i)
            sgrid.Add(SimpleText(sgrid, "%2i" % i), newrow=True)
            wids['%schoice%s' % si] = Choice(sgrid, choices=groupnames, size=(200, -1),
                                           action=partial(self.onComponent, comp=i))
            wids['%sval%s' % si] = FloatCtrl(sgrid, value=0, **fopts)
            wids['%smin%s' % si] = FloatCtrl(sgrid, value=0, **fopts)
            wids['%smax%s' % si] = FloatCtrl(sgrid, value=1, **fopts)
            for cname in ('choice', 'val', 'min', 'max'):
                sgrid.Add(wids[("%%s%s%%s" % cname) % si])
        sgrid.pack()
        panel.Add(sgrid, dcol=5, newrow=True)
        panel.Add(HLine(panel, size=(400, 2)), dcol=5, newrow=True)
        panel.Add(wids['saveconf'], dcol=4, newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LCEN, 3)
        pack(self, sizer)
        self.skip_process = False

    def onComponent(self, evt=None, comp=None):
        if comp is None or evt is None:
            return

        comps = []
        for wname, wid in self.wids.items():
            if wname.startswith('compchoice'):
                pref, n = wname.split('_')
                if wid.GetSelection() > 0:
                    comps.append((int(n), wid.GetStringSelection()))
                else:
                    self.wids["compval_%s" % n].SetValue(0)

        cnames = set([elem[1] for elem in comps])
        if len(cnames) < len(comps):
            comps.remove((comp, evt.GetString()))
            self.wids["compchoice_%2.2d" % comp].SetSelection(0)

        weight = 1.0 / len(comps)

        for n, cname in comps:
            self.wids["compval_%2.2d" % n].SetValue(weight)


    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)
        self.dgroup = dgroup
        if isinstance(dgroup, Group):
            d_emin = min(dgroup.energy)
            d_emax = max(dgroup.energy)
            if opts['e0'] < d_emin or opts['e0'] > d_emax:
                opts['e0'] = dgroup.e0

        self.skip_process = True
        wids = self.wids
        for attr in ('e0', 'elo', 'ehi'):
            val = opts.get(attr, None)
            if val is not None:
                wids[attr].SetValue(val)

        for attr in ('all_combos', 'sum_to_one', 'show_e0', 'show_fitrange'):
            wids[attr].SetValue(opts.get(attr, True))

        for attr in ('fitspace',):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])

        groupnames = [noname] + list(self.controller.file_groups.keys())
        for wname, wid in wids.items():
            if wname.startswith('compchoice'):
                cur = wid.GetStringSelection()
                wid.Clear()
                wid.AppendItems(groupnames)
                if cur in groupnames:
                    wid.SetStringSelection(cur)
                else:
                    wid.SetSelection(0)
            elif wname.startswith('comp'):
                wid.SetValue(opts.get(wname, wid.GetValue()))
        self.skip_process = False

    def read_form(self, dgroup=None):
        "read form, return dict of values"
        self.skip_process = True
        if dgroup is None:
            dgroup = self.controller.get_group()
        self.dgroup = dgroup
        opts = {'group': dgroup.groupname, 'filename':dgroup.filename}
        wids = self.wids
        for attr in ('e0', 'elo', 'ehi'):
            opts[attr] = wids[attr].GetValue()

        for attr in ('fitspace', 'plotchoice'):
            opts[attr] = wids[attr].GetStringSelection()
        for attr in ('all_combos', 'sum_to_one', 'show_e0', 'show_fitrange'):
            opts[attr] = wids[attr].GetValue()

        for attr, wid in wids.items():
            if attr.startswith('compchoice'):
                opts[attr] = wid.GetStringSelection()
            elif attr.startswith('comp'):
                opts[attr] = wid.GetValue()

        comps, cnames, wval, wmin, wmax = [], [], [], [], []
        for i in range(MAX_COMPONENTS):
            scomp = "_%2.2d" % (i+1)
            cname = opts['compchoice%s' % scomp]
            if cname != noname:
                wval.append(str(opts['compval%s' % scomp]))
                wmin.append(str(opts['compmin%s' % scomp]))
                wmax.append(str(opts['compmax%s' % scomp]))
                comps.append(self.controller.file_groups[cname])
                cnames.append(cname)
        opts['comp_names'] = cnames
        opts['comps']   = ', '.join(comps)
        opts['weights'] = ', '.join(wval)
        opts['minvals'] = ', '.join(wmin)
        opts['maxvals'] = ', '.join(wmax)
        opts['elo_abs'] = float(opts['elo']) + float(opts['e0'])
        opts['ehi_abs'] = float(opts['ehi']) + float(opts['e0'])
        opts['func'] = 'lincombo_fit'
        if opts['all_combos']:
            opts['func'] = 'lincombo_fitall'

        opts['arrayname'] = 'norm'
        if opts['fitspace'] == dmude:
            opts['arrayname'] = 'dmude'

        self.skip_process = False
        return opts

    def onSaveConfigBtn(self, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())
        self.set_defaultconfig(conf)

    def onUseSelected(self, event=None):
        """ use selected groups as standards"""
        self.skip_process = True
        selected_groups = self.controller.filelist.GetCheckedStrings()
        if len(selected_groups) == 0:
            return
        if len(selected_groups) >= MAX_COMPONENTS:
            selected_groups = selected_groups[:MAX_COMPONENTS]
        weight = 1.0/len(selected_groups)

        for i in range(MAX_COMPONENTS):
            si = "_%2.2d" % (i+1)
            self.wids['compchoice%s' % si].SetStringSelection(noname)
            self.wids['compval%s' % si].SetValue(0.0)

        for i, sel in enumerate(selected_groups):
            si = "_%2.2d" % (i+1)
            self.wids['compchoice%s' % si].SetStringSelection(sel)
            self.wids['compval%s' % si].SetValue(weight)
        self.skip_process = False


    def do_fit(self, groupname, form):
        """run lincombo fit for a group"""
        form['gname'] = groupname
        script = """# do LCF for {gname:s}
result = {func:s}({gname:s}, [{comps:s}],
            xmin={elo_abs:.4f}, xmax={ehi_abs:.4f}, sum_to_one={sum_to_one}, arrayname='{arrayname:s}',
            weights=[{weights:s}],
            minvals=[{minvals:s}],
            maxvals=[{maxvals:s}])
"""
        if form['all_combos']:
            script = "%s\n{gname:s}.lcf_result = result\n" % script
        else:
            script = "%s\n{gname:s}.lcf_result = [result]\n" % script

        self.larch_eval(script.format(**form))

        dgroup = self.controller.get_group(groupname)
        self.parent.show_subframe('lcf_result',  ResultFrame)


        self.parent.subframes['lcf_result'].show_results(datagroup=dgroup,
                                                         form=form,
                                                         larch_eval=self.larch_eval)
        self.plot(dgroup=dgroup)

    def onFitOne(self, event=None):
        """ handle process events"""
        if self.skip_process:
            return

        self.skip_process = True
        form = self.read_form()
        self.do_fit(form['group'], form)
        self.skip_process = False

    def onFitAll(self, event=None):
        """ handle process events"""
        if self.skip_process:
            return
        self.skip_process = True
        form = self.read_form()
        for sel in self.controller.filelist.GetCheckedStrings():
            gname = self.controller.file_groups[sel]
            self.do_fit(gname, form)
        self.skip_process = False

    def plot(self, dgroup=None):
        self.onPlot(dgroup=dgroup)

    def onPlot(self, evt=None, dgroup=None):
        if dgroup is None:
            dgroup = self.controller.get_group()
        form = self.read_form(dgroup=dgroup)
        script = make_lcfplot(dgroup, form, nfit=0)
        self.larch_eval(script)
