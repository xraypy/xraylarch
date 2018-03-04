import time
import os
import numpy as np
np.seterr(all='ignore')

from functools import partial
from collections import OrderedDict
import json

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as flat_nb

import wx.dataview as dv

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check,
                     MenuItem, GUIColors, GridPanel, CEN, RCEN, LCEN,
                     FRAMESTYLE, Font, FileSave, FileOpen)

from lmfit import Parameter, Parameters, fit_report
try:
    from lmfit.model import save_modelresult, load_modelresult
    HAS_MODELSAVE = True
except ImportError:
    HAS_MODELSAVE = False

import lmfit.models as lm_models
from lmfit.printfuncs import gformat, CORREL_HEAD

from larch import Group, site_config
from larch.utils import index_of
from larch.utils.jsonutils import encode4js, decode4js

from larch.wxlib import (ReportFrame, BitmapButton, ParameterWidgets,
                         FloatCtrl, SetTip)

from larch_plugins.std import group2dict
from larch_plugins.io.export_modelresult import export_modelresult
from larch_plugins.wx.icons import get_icon
from larch_plugins.wx.parameter import ParameterPanel

LCEN = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
CEN |=  wx.ALL

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_NO_NAV_BUTTONS

ModelChoices = {'other': ('<General Models>', 'Constant', 'Linear',
                          'Quadratic', 'Exponential', 'PowerLaw'
                          'Linear Step', 'Arctan Step',
                          'ErrorFunction Step', 'Logistic Step', 'Rectangle'),
                'peaks': ('<Peak Models>', 'Gaussian', 'Lorentzian',
                          'Voigt', 'PseudoVoigt', 'DampedHarmonicOscillator',
                          'Pearson7', 'StudentsT', 'SkewedGaussian',
                          'Moffat', 'BreitWigner', 'Donaich', 'Lognormal'),
                }

Array_Choices = OrderedDict((('Raw Data', 'mu'),
                             ('Normalized', 'norm'),
                             ('Flattened', 'flat'),
                             ('Deconvolved', 'deconv'),
                             ('Derivative', 'dmude')))

PlotChoices = OrderedDict((('Data + Baseline', 'bkg'),
                           ('Data + Fit', 'fit')))


FitMethods = ("Levenberg-Marquardt", "Nelder-Mead", "Powell")

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, zorder=3,
                  marker='None', markersize=4)


def default_prepeaks_config():
    return dict(mask_elo=-10, mask_ehi=-5,
                fit_emin=-40, fit_emax=0,
                yarray='norm')

MIN_CORREL = 0.0010

class FitResultFrame(wx.Frame):
    def __init__(self, parent=None, peakframe=None, datagroup=None, **kws):

        wx.Frame.__init__(self, None, -1, title='Fit Results',
                          style=FRAMESTYLE, size=(600, 675), **kws)
        self.parent = parent
        self.peakframe = peakframe
        self.datagroup = datagroup
        self.build()
        self.show()

    def build(self):
        sizer = wx.GridBagSizer(10, 5)
        sizer.SetVGap(2)
        sizer.SetHGap(2)

        panel = scrolled.ScrolledPanel(self)
        self.SetMinSize((600, 450))
        self.colors = GUIColors()

        # title row
        self.wids = wids = {}
        title = SimpleText(panel, 'Fit Results',  font=Font(12),
                           colour=self.colors.title, style=LCEN)

        wids['data_title'] = SimpleText(panel, '< > ',  font=Font(12),
                                             colour=self.colors.title, style=LCEN)

        wids['hist_tag'] = SimpleText(panel, 'Fit #1',  font=Font(12),
                                      colour=self.colors.title, style=LCEN)

        wids['hist_info'] = SimpleText(panel, ' ___ ',  font=Font(12),
                                       colour=self.colors.title, style=LCEN)

        sizer.Add(title,              (0, 0), (1, 2), LCEN)
        sizer.Add(wids['data_title'], (0, 2), (1, 2), LCEN)
        sizer.Add(wids['hist_tag'],   (0, 4), (1, 1), LCEN)
        sizer.Add(wids['hist_info'],  (0, 5), (1, 1), LCEN)

        irow = 1
        wids['model_desc'] = SimpleText(panel, '<Model>',  font=Font(12))
        sizer.Add(wids['model_desc'],  (irow, 0), (1, 5), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(400, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Fit Statistics]]',  font=Font(12),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title, (irow, 0), (1, 4), LCEN)

        for label, attr in (('Fit method', 'method'),
                            ('# Fit Evaluations', 'nfev'),
                            ('# Data Points', 'ndata'),
                            ('# Fit Variables', 'nvarys'),
                            ('# Free Points', 'nfree'),
                            ('Chi-square', 'chisqr'),
                            ('Reduced Chi-square', 'redchi'),
                            ('Akaike Info Criteria', 'aic'),
                            ('Bayesian Info Criteria', 'bic')):
            irow += 1
            wids[attr] = SimpleText(panel, '?')
            sizer.Add(SimpleText(panel, " %s = " % label),  (irow, 0), (1, 1), LCEN)
            sizer.Add(wids[attr],                           (irow, 1), (1, 1), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(400, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Variables]]',  font=Font(12),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title, (irow, 0), (1, 1), LCEN)

        self.wids['copy_params'] = Button(panel, 'Update Model with Best Fit Values',
                                          size=(250, -1), action=self.onCopyParams)

        sizer.Add(self.wids['copy_params'], (irow, 1), (1, 3), LCEN)

        dvstyle = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES
        pview = self.wids['params'] = dv.DataViewListCtrl(panel, style=dvstyle)
        self.wids['paramsdata'] = []
        pview.AppendTextColumn('Parameter',         width=150)
        pview.AppendTextColumn('Best-Fit Value',    width=100)
        pview.AppendTextColumn('Standard Error',    width=100)
        pview.AppendTextColumn('Info ',             width=275)

        for col in (0, 1, 2, 3):
            this = pview.Columns[col]
            isort, align = True, wx.ALIGN_LEFT
            if col in (1, 2):
                isort, align = False, wx.ALIGN_RIGHT
            this.Sortable = isort
            this.Alignment = this.Renderer.Alignment = align

        pview.SetMinSize((650, 200))
        pview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectParameter)

        irow += 1
        sizer.Add(pview, (irow, 0), (1, 5), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(400, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Correlations]]',  font=Font(12),
                           colour=self.colors.title, style=LCEN)

        self.wids['all_correl'] = Button(panel, 'Show All',
                                          size=(100, -1), action=self.onAllCorrel)

        self.wids['min_correl'] = FloatCtrl(panel, value=MIN_CORREL,
                                            minval=0, size=(60, -1), gformat=True)

        ctitle = SimpleText(panel, 'minimum correlation: ')
        sizer.Add(title,  (irow, 0), (1, 1), LCEN)
        sizer.Add(ctitle, (irow, 1), (1, 1), LCEN)
        sizer.Add(self.wids['min_correl'], (irow, 2), (1, 1), LCEN)
        sizer.Add(self.wids['all_correl'], (irow, 3), (1, 1), LCEN)

        irow += 1

        cview = self.wids['correl'] = dv.DataViewListCtrl(panel, style=dvstyle)

        cview.AppendTextColumn('Parameter 1',    width=150)
        cview.AppendTextColumn('Parameter 2',    width=150)
        cview.AppendTextColumn('Correlation',    width=100)

        for col in (0, 1, 2):
            this = cview.Columns[col]
            isort, align = True, wx.ALIGN_LEFT
            if col == 1:
                isort = False
            if col == 2:
                align = wx.ALIGN_RIGHT
            this.Sortable = isort
            this.Alignment = this.Renderer.Alignment = align
        cview.SetMinSize((450, 200))

        irow += 1
        sizer.Add(cview, (irow, 0), (1, 5), LCEN)
        irow += 1
        sizer.Add(HLine(panel, size=(400, 3)), (irow, 0), (1, 5), LCEN)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def onSelectParameter(self, evt=None):
        if self.wids['params'] is None:
            return
        if not self.wids['params'].HasSelection():
            return
        item = self.wids['params'].GetSelectedRow()
        pname = self.wids['paramsdata'][item]

        cormin= self.wids['min_correl'].GetValue()
        self.wids['correl'].DeleteAllItems()

        fit_history = getattr(self.datagroup, 'fit_history', [])
        result = fit_history[-1]
        this = result.params[pname]
        if this.correl is not None:
            sort_correl = sorted(this.correl.items(), key=lambda it: abs(it[1]))
            for name, corval in reversed(sort_correl):
                if abs(corval) > cormin:
                    self.wids['correl'].AppendItem((pname, name, "% .4f" % corval))

    def onAllCorrel(self, evt=None):
        fit_history = getattr(self.datagroup, 'fit_history', [])
        params = fit_history[-1].params
        parnames = list(params.keys())

        cormin= self.wids['min_correl'].GetValue()
        correls = {}
        for i, name in enumerate(parnames):
            par = params[name]
            if not par.vary:
                continue
            if hasattr(par, 'correl') and par.correl is not None:
                # print(par, par.correl)
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
        fit_history = getattr(self.datagroup, 'fit_history', [])
        self.peakframe.update_start_values(fit_history[-1])

    def show(self, datagroup=None):
        if datagroup is not None:
            self.datagroup = datagroup

        fit_history = getattr(self.datagroup, 'fit_history', [])
        if len(fit_history) < 1:
            print("No fit reults to show for datagroup ", self.datagroup)
        result = fit_history[-1]
        wids = self.wids
        wids['method'].SetLabel(result.method)
        wids['ndata'].SetLabel("%d" % result.ndata)
        wids['nvarys'].SetLabel("%d" % result.nvarys)
        wids['nfree'].SetLabel("%d" % result.nfree)
        wids['nfev'].SetLabel("%d" % result.nfev)
        wids['redchi'].SetLabel("%f" % result.redchi)
        wids['chisqr'].SetLabel("%f" % result.chisqr)
        wids['aic'].SetLabel("%f" % result.aic)
        wids['bic'].SetLabel("%f" % result.bic)
        wids['hist_info'].SetLabel("%d" % len(fit_history))
        wids['hist_tag'].SetLabel("Latest Fit") #

        wids['data_title'].SetLabel(self.datagroup.filename)

        wids['model_desc'].SetLabel(result.model_repr)
        wids['params'].DeleteAllItems()
        wids['paramsdata'] = []
        for i, param in enumerate(result.params.values()):
            pname = param.name
            try:
                val = gformat(param.value)
            except (TypeError, ValueError):
                val = ' ??? '

            serr = ' N/A '
            if param.stderr is not None:
                serr = gformat(param.stderr, length=9)

            extra = ' '
            if param.expr is not None:
                extra = ' = %s ' % param.expr
            elif param.init_value is not None:
                extra = ' (init=% .7g)' % param.init_value
            elif not param.vary:
                extra = ' (fixed)'

            wids['params'].AppendItem((pname, val, serr, extra))
            wids['paramsdata'].append(pname)

        self.Refresh()

class PrePeakPanel(wx.Panel):
    def __init__(self, parent=None, controller=None, **kws):

        wx.Panel.__init__(self, parent, -1, size=(550, 625), **kws)
        self.parent = parent
        self.controller = controller
        self.larch = controller.larch
        self.fit_components = OrderedDict()
        self.fit_model = None
        self.fit_params = None
        self.user_added_params = None
        self.summary = None
        self.sizer = wx.GridBagSizer(10, 6)
        self.build_display()
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
            # print(" Fill prepeak panel from group ", fname, gname, dgroup)
            self.fill_form(dgroup)
        except:
            pass # print(" Cannot Fill prepeak panel from group ")

    def larch_eval(self, cmd):
        """eval"""
        self.controller.larch.eval(cmd)

    def build_display(self):
        self.mod_nb = flat_nb.FlatNotebook(self, -1, agwStyle=FNB_STYLE)
        self.mod_nb.SetTabAreaColour(wx.Colour(250,250,250))
        self.mod_nb.SetActiveTabColour(wx.Colour(254,254,195))

        self.mod_nb.SetNonActiveTabTextColour(wx.Colour(10,10,128))
        self.mod_nb.SetActiveTabTextColour(wx.Colour(128,0,0))
        self.mod_nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onNBChanged)

        pan = self.panel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LCEN)

        self.btns = {}
        for name in ('ppeak_e0', 'ppeak_elo', 'ppeak_emin', 'ppeak_emax', 'ppeak_ehi'):
            bb = BitmapButton(pan, get_icon('plus'),
                              action=partial(self.on_selpoint, opt=name),
                              tooltip='use last point selected from plot')
            self.btns[name] = bb

        opts = dict(size=(65, -1), gformat=True, precision=1)

        self.ppeak_e0   = FloatCtrl(pan, value=0, **opts)
        self.ppeak_emin = FloatCtrl(pan, value=-30, **opts)
        self.ppeak_emax = FloatCtrl(pan, value=0, **opts)
        self.ppeak_elo = FloatCtrl(pan, value=-15, **opts)
        self.ppeak_ehi = FloatCtrl(pan, value=-5, **opts)

        fitbkg_btn = Button(pan, 'Fit Baseline', size=(125, -1),
                            action=self.onFitBaseline)
        fitmodel_btn = Button(pan, 'Fit Full Model', size=(125, -1), action=self.onRunFit)
        savefit_btn  = Button(pan, 'Save Fit', size=(125, -1), action=self.onSaveFitResult)
        plotbkg_btn = Button(pan, 'Plot Baseline', size=(125, -1), action=self.onPlotBaseline)
        plotfit_btn = Button(pan, 'Plot Fit', size=(125, -1), action=self.onShowModel)

        savefit_btn.Disable()
        fitmodel_btn.Disable()
        plotfit_btn.Disable()

        self.savefit_btn = savefit_btn
        self.fitmodel_btn = fitmodel_btn
        self.plotfit_btn = plotfit_btn

        self.array_choice = Choice(pan, size=(125, -1),
                                   choices=list(Array_Choices.keys()))
        self.array_choice.SetSelection(1)

        models_peaks = Choice(pan, size=(150, -1),
                              choices=ModelChoices['peaks'],
                              action=self.addModel)

        models_other = Choice(pan, size=(150, -1),
                              choices=ModelChoices['other'],
                              action=self.addModel)

        self.message = SimpleText(pan, ' fit baseline, then add peaks or other models ')

        opts = dict(default=True, size=(150, -1))
        self.show_comps = Check(pan, label='Plot Components?', **opts)
        self.show_subbkg = Check(pan, label='Subtract Baseline?', **opts)

        self.show_peakrange = Check(pan, label='show?', **opts)

        self.show_fitrange = Check(pan, label='show?', **opts)
        self.show_e0 = Check(pan, label='show?', **opts)

        titleopts = dict(font=Font(11), colour='#AA0000')
        pan.Add(SimpleText(pan, ' Pre-edge Peak Fitting', **titleopts), dcol=6)

        pan.Add(SimpleText(pan, 'Array to fit: '), newrow=True)
        pan.Add(self.array_choice, dcol=5)

        pan.Add(SimpleText(pan, 'E0: '), newrow=True)
        pan.Add(self.btns['ppeak_e0'])
        pan.Add(self.ppeak_e0)
        pan.Add(self.show_e0, dcol=5)

        pan.Add(SimpleText(pan, 'Fit Energy Range: '), newrow=True)
        pan.Add(self.btns['ppeak_emin'])
        pan.Add(self.ppeak_emin)
        pan.Add(SimpleText(pan, ':'))
        pan.Add(self.btns['ppeak_emax'])
        pan.Add(self.ppeak_emax)
        pan.Add(self.show_fitrange, dcol=2)

        t = SimpleText(pan, 'Pre-edge Peak Range: ')
        t.SetToolTip('Range used as mask for background')

        pan.Add(t, newrow=True)
        pan.Add(self.btns['ppeak_elo'])
        pan.Add(self.ppeak_elo)
        pan.Add(SimpleText(pan, ':'))
        pan.Add(self.btns['ppeak_ehi'])
        pan.Add(self.ppeak_ehi)
        pan.Add(self.show_peakrange, dcol=2)

        ts = wx.BoxSizer(wx.HORIZONTAL)
        ts.Add(fitbkg_btn, 0)
        ts.Add(fitmodel_btn, 0)
        ts.Add(savefit_btn, 0)

        pan.Add(ts, dcol=8, newrow=True)

        ts = wx.BoxSizer(wx.HORIZONTAL)
        ts.Add(plotbkg_btn, 0)
        ts.Add(plotfit_btn, 0)
        ts.Add(self.show_comps, 0)
        ts.Add(self.show_subbkg, 0)
        pan.Add(ts, dcol=8, newrow=True)

        ts = wx.BoxSizer(wx.HORIZONTAL)
        ts.Add(models_peaks)
        ts.Add(models_other)
        pan.Add(SimpleText(pan, ' Add Function: '), newrow=True)
        pan.Add(ts, dcol=7)

        pan.Add(self.message, dcol=8, newrow=True)

        pan.pack()


        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((5,5), 0, LCEN, 3)
        sizer.Add(HLine(self, size=(550, 2)), 0, LCEN, 3)
        sizer.Add(pan,   0, LCEN, 3)
        sizer.Add((5,5), 0, LCEN, 3)
        sizer.Add(HLine(self, size=(550, 2)), 0, LCEN, 3)
        sizer.Add((5,5), 0, LCEN, 3)
        sizer.Add(self.mod_nb,  1, LCEN|wx.GROW, 10)

        pack(self, sizer)

    def get_config(self, dgroup=None):
        """get processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()

        conf = getattr(dgroup, 'prepeak_config', {})
        if 'e0' not in conf:
            conf = default_prepeak_config()
        if not hasattr(dgroup, 'prepeaks'):
            dgroup.prepeaks = Group()
        dgroup.prepeaks.config = conf
        return conf

    def fill_form(self, dgroup):
        self.ppeak_e0.SetValue(dgroup.e0)
        if hasattr(dgroup, 'prepeaks'):
            self.ppeak_emin.SetValue(dgroup.prepeaks.emin)
            self.ppeak_emax.SetValue(dgroup.prepeaks.emax)
            self.ppeak_elo.SetValue(dgroup.prepeaks.elo)
            self.ppeak_ehi.SetValue(dgroup.prepeaks.ehi)

    def read_form(self):
        "read for, returning dict of values"
        dgroup = self.controller.get_group()
        array_desc = self.array_choice.GetStringSelection()
        form_opts = {'gname': dgroup.groupname,
                     'group': dgroup,
                     'array_desc': array_desc.lower(),
                     'array_name': Array_Choices[array_desc],
                     'baseline_form': 'lorentzian'}

        form_opts['e0'] = self.ppeak_e0.GetValue()
        form_opts['emin'] = self.ppeak_emin.GetValue()
        form_opts['emax'] = self.ppeak_emax.GetValue()
        form_opts['elo'] = self.ppeak_elo.GetValue()
        form_opts['ehi'] = self.ppeak_ehi.GetValue()
        form_opts['show_centroid'] = True
        form_opts['show_comp'] = self.show_comps.IsChecked()
        form_opts['show_subbkg'] = self.show_subbkg.IsChecked()
        form_opts['show_peakrange'] = self.show_peakrange.IsChecked()
        form_opts['show_fitrange'] = self.show_fitrange.IsChecked()
        form_opts['show_e0'] = self.show_e0.IsChecked()

        return form_opts


    def onFitBaseline(self, evt=None):
        opts = self.read_form()

        cmd = """{gname:s}.ydat = 1.0*{gname:s}.{array_name:s}
pre_edge_baseline(energy={gname:s}.energy, norm={gname:s}.ydat, group={gname:s},
form='{baseline_form:s}', with_line=True,
elo={elo:.3f}, ehi={ehi:.3f}, emin={emin:.3f}, emax={emax:.3f})
"""
        self.larch_eval(cmd.format(**opts))

        dgroup = opts['group']
        ppeaks = dgroup.prepeaks
        dgroup.centroid_msg = "%.4f +/- %.4f eV" % (ppeaks.centroid,
                                                    ppeaks.delta_centroid)

        self.message.SetLabel(dgroup.centroid_msg)

        if 'bkg_' not in self.fit_components:
            self.addModel(model='Lorentzian', prefix='bkg_')
            self.addModel(model='Linear', prefix='l_')

        for prefix in ('bkg_', 'l_'):
            bkg = self.fit_components[prefix]
            bkg.bkgbox.SetValue(1)
            self.fill_model_params(dgroup, prefix, dgroup.prepeaks.fit_details)

        self.fill_form(dgroup)
        self.fitmodel_btn.Enable()
        self.plotfit_btn.Enable()

        self.onPlotBaseline()

    def fill_model_params(self, dgroup, prefix, fit_details):
        comp = self.fit_components[prefix]
        parwids = comp.parwids
        for pname, par in fit_details.params.items():
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
                    wids.expr.SetValue(par.expr)
                    varstr = 'constrain'
                if wids.vary is not None:
                    wids.vary.SetStringSelection(varstr)

    def onPlotBaseline(self, evt=None):
        opts = self.read_form()
        dgroup = self.controller.get_group()
        opts = self.read_form()
        ppeaks = dgroup.prepeaks
        i0 = index_of(dgroup.energy, ppeaks.energy[0])
        i1 = index_of(dgroup.energy, ppeaks.energy[-1]) + 1

        baseline = dgroup.ydat*1.0
        baseline[i0:i1] = ppeaks.baseline

        jmin, jmax = max(0, i0-2), i1+3
        ydat = dgroup.ydat[jmin:jmax]
        yrange = max(ydat) - min(ydat)

        array_desc = self.array_choice.GetStringSelection()

        plotopts = {'xmin': dgroup.energy[jmin],
                    'xmax': dgroup.energy[jmax],
                    'ymax': max(ydat) + 0.05 * yrange,
                    'ymin': min(ydat) - 0.05 * yrange,
                    'title': 'Pre-edge baseline: %s' % opts['gname'],
                    'xlabel': 'Energy (eV)',
                    'ylabel': '%s $\mu$' % opts['array_desc'],
                    'label': '%s $\mu$' % opts['array_desc']}

        plot_extras = []
        if opts['show_fitrange']:
            popts = {'color': '#DDDDCC'}
            emin = opts['emin']
            emax = opts['emax']
            imin = index_of(dgroup.xdat, emin)
            imax = index_of(dgroup.xdat, emax)

            plot_extras.append(('vline', emin, None, popts))
            plot_extras.append(('vline', emax, None, popts))

        if opts['show_peakrange']:
            popts = {'marker': '+', 'markersize': 6}
            elo = opts['elo']
            ehi = opts['ehi']
            ilo = index_of(dgroup.xdat, elo)
            ihi = index_of(dgroup.xdat, ehi)

            plot_extras.append(('marker', elo, dgroup.ydat[ilo], popts))
            plot_extras.append(('marker', ehi, dgroup.ydat[ihi], popts))

        if opts['show_centroid']:
            popts = {'color': '#EECCCC'}
            ecen = getattr(dgroup.prepeaks, 'centroid', -1)
            if ecen > min(dgroup.energy):
                plot_extras.append(('vline', ecen, None,  popts))


        ppanel = self.controller.get_display().panel
        plotopts.update(PLOTOPTS_1)
        ppanel.plot(dgroup.energy, dgroup.ydat, delay_draw=True, **plotopts)

        plotopts.update(PLOTOPTS_2)
        plotopts['label'] = 'baseline'

        ppanel.oplot(dgroup.energy, baseline, **plotopts)

        axes = ppanel.axes
        for etype, x, y, opts in plot_extras:
            # print(" plot extra ", etype, x, y, opts)
            if etype == 'marker':
                popts = {'marker': 'o', 'markersize': 4,
                         'label': '_nolegend_',
                         'markerfacecolor': 'red',
                         'markeredgecolor': '#884444'}
                popts.update(opts)
                axes.plot([x], [y], **popts)
            elif etype == 'vline':
                popts = {'ymin': 0, 'ymax': 1.0, 'color': '#888888'}
                popts.update(opts)
                axes.axvline(x, **popts)
        ppanel.canvas.draw()



    def onNBChanged(self, event=None):
        idx = self.mod_nb.GetSelection()

    def addModel(self, event=None, model=None, prefix=None):
        if model is None and event is not None:
            model = event.GetString()
        if model is None or model.startswith('<'):
            return

        if prefix is None:
            p = model[0].lower()
            curmodels = ["%s%i_" % (p, i+1) for i in range(1+len(self.fit_components))]
            for comp in self.fit_components:
                if comp in curmodels:
                    curmodels.remove(comp)

            prefix = curmodels[0]

        label = "%s(prefix='%s')" % (model, prefix)
        title = "%s: %s " % (prefix[:-1], model)
        mclass_kws = {'prefix': prefix}
        if 'step' in model.lower():
            form = model.lower().replace('step', '').strip()

            if form.startswith('err'): form = 'erf'
            label = "Step(form='%s', prefix='%s')" % (form, prefix)
            title = "%s: Step %s" % (prefix[:-1], form[:3])
            mclass = lm_models.StepModel
            mclass_kws['form'] = form
            minst = mclass(form=form, prefix=prefix)
        else:
            mclass = getattr(lm_models, model+'Model')
            minst = mclass(prefix=prefix)

        panel = GridPanel(self.mod_nb, ncols=1, nrows=1, pad=1, itemstyle=CEN)

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label,
                               size=size, style=wx.ALIGN_LEFT, **kws)
        usebox = Check(panel, default=True, label='Use in Fit?', size=(100, -1))
        bkgbox = Check(panel, default=False, label='Is Baseline?', size=(125, -1))

        delbtn = Button(panel, 'Delete Component', size=(125, -1),
                        action=partial(self.onDeleteComponent, prefix=prefix))

        pick2msg = SimpleText(panel, "    ", size=(125, -1))
        pick2btn = Button(panel, 'Pick Values from Data', size=(150, -1),
                          action=partial(self.onPick2Points, prefix=prefix))

        # SetTip(mname,  'Label for the model component')
        SetTip(usebox,   'Use this component in fit?')
        SetTip(bkgbox,   'Label this component as "background" when plotting?')
        SetTip(delbtn,   'Delete this model component')
        SetTip(pick2btn, 'Select X range on Plot to Guess Initial Values')

        panel.Add(SLabel(label, size=(275, -1), colour='#0000AA'),
                  dcol=3,  style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(usebox, dcol=1)
        panel.Add(bkgbox, dcol=2, style=LCEN)
        panel.Add(delbtn, dcol=1, style=wx.ALIGN_LEFT)

        panel.Add(pick2btn, dcol=2, style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(pick2msg, dcol=2, style=wx.ALIGN_RIGHT)

        # panel.Add((10, 10), newrow=True)
        # panel.Add(HLine(panel, size=(150,  3)), dcol=4, style=wx.ALIGN_CENTER)

        panel.Add(SLabel("Parameter "), style=wx.ALIGN_LEFT,  newrow=True)
        panel.AddMany((SLabel(" Value"), SLabel(" Type"), SLabel(' Bounds'),
                       SLabel("  Min", size=(60, -1)),
                       SLabel("  Max", size=(60, -1)),  SLabel(" Expression")))

        parwids = OrderedDict()
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

            pwids = ParameterWidgets(panel, par, name_size=100, expr_size=125,
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

                pwids = ParameterWidgets(panel, par, name_size=100, expr_size=225,
                                         float_size=80, prefix=prefix,
                                         widgets=('name', 'value', 'expr'))
                parwids[par.name] = pwids
                panel.Add(pwids.name, newrow=True)
                panel.Add(pwids.value)
                panel.Add(pwids.expr, dcol=4, style=wx.ALIGN_RIGHT)
                pwids.value.Disable()


        # panel.Add(delbtn, dcol=2)
        # panel.Add(HLine(panel, size=(250, 3)), dcol=3, style=wx.ALIGN_CENTER)

        fgroup = Group(prefix=prefix, title=title, mclass=mclass,
                       mclass_kws=mclass_kws, usebox=usebox, panel=panel,
                       parwids=parwids, float_size=65, expr_size=150,
                       pick2_msg=pick2msg, bkgbox=bkgbox)


        self.fit_components[prefix] = fgroup
        panel.pack()

        self.mod_nb.AddPage(panel, title, True)
        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))

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

        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))

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
            plotframe = self.controller.get_display(stacked=False)
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
            if name in parwids:
                parwids[name].value.SetValue(param.value)

        dgroup._tmp = mod.eval(guesses, x=dgroup.xdat)
        plotframe = self.controller.get_display(stacked=False)
        plotframe.cursor_hist = []
        plotframe.oplot(dgroup.xdat, dgroup._tmp)
        self.pick2erase_panel = plotframe.panel

        self.pick2erase_timer.Start(5000)


    def onPick2Points(self, evt=None, prefix=None):
        fgroup = self.fit_components.get(prefix, None)
        if fgroup is None:
            return

        plotframe = self.controller.get_display(stacked=False)
        plotframe.Raise()

        plotframe.cursor_hist = []
        fgroup.npts = 0
        self.pick2_group = fgroup

        if fgroup.pick2_msg is not None:
            fgroup.pick2_msg.SetLabel("0/2")

        self.pick2_t0 = time.time()
        self.pick2_timer.Start(250)

    def onSaveFitResult(self, event=None):
        dgroup = self.controller.get_group()
        deffile = dgroup.filename.replace('.', '_') + '.fitresult'
        wcards = 'Fit Results(*.fitresult)|*.fitresult|All files (*.*)|*.*'

        outfile = FileSave(self, 'Save Fit Result',
                           default_file=deffile,
                           wildcard=wcards)

        if outfile is not None:
            try:
                save_modelresult(dgroup.fit_history[-1], outfile)
            except IOError:
                print('could not write %s' % outfile)

    def onLoadFitResult(self, event=None):

        wcards = 'Fit Results(*.fitresult)|*.fitresult|All files (*.*)|*.*'

        mfile = FileOpen(self, 'Load Fit Result',
                         default_file='', wildcard=wcards)
        model = None

        if mfile is not None:
            try:
                model = load_modelresult(mfile)
            except IOError:
                print('could not read model result %s' % mfile)
                return
        if model is None:
            return
        print(" Loading Model (work in progress) ", model)

    def onExportFitResult(self, event=None):
        dgroup = self.controller.get_group()
        deffile = dgroup.filename.replace('.', '_') + '_result.xdi'
        wcards = 'All files (*.*)|*.*'

        outfile = FileSave(self, 'Export Fit Result',
                           default_file=deffile, wildcard=wcards)

        if outfile is not None:
            i1, i2, xv1, xv2 = self.get_xranges(dgroup.xdat)
            x = dgroup.xdat[slice(i1, i2)]
            y = dgroup.ydat[slice(i1, i2)]
            yerr = None
            if hasattr(dgroup, 'yerr'):
                yerr = dgroup.yerr
                if not isinstance(yerr, np.ndarray):
                    yerr = yerr * np.ones(len(y))
                else:
                    yerr = yerr[slice(i1, i2)]

            export_modelresult(dgroup.fit_history[-1],
                               filename=outfile,
                               datafile=dgroup.filename,
                               ydata=y, yerr=yerr, x=x)


    def on_selpoint(self, evt=None, opt='xmin'):
        xval = None
        try:
            xval = self.larch.symtable._plotter.plot1_x
        except:
            return
        wid = getattr(self, opt, None)
        if wid is not None:
            wid.SetValue(xval)

    def get_xranges(self, x):
        opts = self.read_form()
        _xmin = opts['emin']
        _xmax = opts['emax']

        xmin, xmax = min(x), max(x)
        i1, i2 = 0, len(x)
        if _xmin > min(x):
            i1 = index_of(x, _xmin)
            xmin = x[i1]
        if _xmax < max(x):
            i2 = index_of(x, _xmax) + 1
            xmax = x[i2]
        xv1 = max(min(x), xmin - (xmax-xmin)/5.0)
        xv2 = min(max(x), xmax + (xmax-xmin)/5.0)
        return i1, i2, xv1, xv2

    def build_fitmodel(self):
        """ use fit components to build model"""
        dgroup = self.controller.get_group()
        fullmodel = None
        params = Parameters()
        self.summary = {'components': [], 'options': {}}
        for comp in self.fit_components.values():
            if comp.usebox is not None and comp.usebox.IsChecked():
                for parwids in comp.parwids.values():
                    params.add(parwids.param)
                self.summary['components'].append((comp.mclass.__name__, comp.mclass_kws))
                thismodel = comp.mclass(**comp.mclass_kws)
                if fullmodel is None:
                   fullmodel = thismodel
                else:
                    fullmodel += thismodel

        self.fit_model = fullmodel
        self.fit_params = params

        if dgroup is not None:
            i1, i2, xv1, xv2 = self.get_xranges(dgroup.xdat)
            xsel = dgroup.xdat[slice(i1, i2)]
            dgroup.xfit = xsel
            dgroup.yfit = self.fit_model.eval(self.fit_params, x=xsel)
            dgroup.ycomps = self.fit_model.eval_components(params=self.fit_params,
                                                           x=xsel)
        return dgroup

    def onShowModel(self, event=None):
        dgroup = self.build_fitmodel()
        if dgroup is not None:
            with_components = (self.show_comps.IsChecked() and
                               len(dgroup.ycomps) > 1)

            self.plot_fitmodel(dgroup, show_resid=False,
                               with_components=with_components)

    def plot_fitmodel(self, dgroup, show_resid=False, with_components=None):
        if dgroup is None:
            return
        i1, i2, xv1, xv2 = self.get_xranges(dgroup.xdat)
        ysel = dgroup.ydat[slice(i1, i2)]

        plotframe = self.controller.get_display(stacked=True)
        plotframe.plot(dgroup.xfit, ysel, new=True, panel='top',
                       xmin=xv1, xmax=xv2, label='data',
                       xlabel=dgroup.plot_xlabel, ylabel=dgroup.plot_ylabel,
                       title='Fit: %s' % dgroup.filename )

        plotframe.oplot(dgroup.xfit, dgroup.yfit, label='fit')

        plotframe.plot(dgroup.xfit, ysel-dgroup.yfit, grid=False,
                       marker='o', markersize=4, linewidth=1, panel='bot')

        if with_components is None:
            with_components = (self.show_comps.IsChecked() and
                               len(dgroup.ycomps) > 1)
        if with_components:
            for label, _y in dgroup.ycomps.items():
                plotframe.oplot(dgroup.xfit, _y, label=label,
                                style='short dashed')

        line_opts = dict(color='#AAAAAA', label='_nolegend_',
                    linewidth=1, zorder=-5)
        plotframe.panel_bot.axes.axhline(0, **line_opts)
        axvline = plotframe.panel.axes.axvline
        if i1 > 0:
            axvline(dgroup.xdat[i1], **line_opts)

        if i2 < len(dgroup.xdat):
            axvline(dgroup.xdat[i2-1], **line_opts)

        plotframe.panel.canvas.draw()


    def onRunFit(self, event=None):
        dgroup = self.build_fitmodel()
        if dgroup is None:
            return
        i1, i2, xv1, xv2 = self.get_xranges(dgroup.xdat)
        dgroup.xfit = dgroup.xdat[slice(i1, i2)]
        ysel = dgroup.ydat[slice(i1, i2)]
        weights = np.ones(len(ysel))

        if hasattr(dgroup, 'yerr'):
            yerr = dgroup.yerr
            if not isinstance(yerr, np.ndarray):
                yerr = yerr * np.ones(len(ysel))
            else:
                yerr = yerr[slice(i1, i2)]
            yerr_min = 1.e-9*ysel.mean()
            yerr[np.where(yerr < yerr_min)] = yerr_min
            weights = 1.0/yerr

        result = self.fit_model.fit(ysel, params=self.fit_params,
                                    x=dgroup.xfit, weights=weights,
                                    method='leastsq')
        self.summary['xmin'] = xv1
        self.summary['xmax'] = xv2
        for attr in ('aic', 'bic', 'chisqr', 'redchi', 'ci_out', 'covar',
                     'flatchain', 'success', 'nan_policy', 'nfev', 'ndata',
                     'nfree', 'nvarys', 'init_values'):
            self.summary[attr] = getattr(result, attr)
        self.summary['params'] = result.params


        dgroup.yfit = result.best_fit
        dgroup.ycomps = self.fit_model.eval_components(params=result.params,
                                                       x=dgroup.xfit)


        with_components = (self.show_comps.IsChecked() and len(dgroup.ycomps) > 1)

        self.plot_fitmodel(dgroup, show_resid=True, with_components=with_components)

        result.model_repr = self.fit_model._reprstring(long=True)

        self.autosave_modelresult(result)
        if not hasattr(dgroup, 'fit_history'):
            dgroup.fit_history = []
        dgroup.fit_history.append(result)


        self.parent.show_subframe('result_frame', FitResultFrame,
                                  datagroup=dgroup, peakframe=self)

        # self.update_start_values(result)
        self.savefit_btn.Enable()

        for m in self.parent.afterfit_menus:
            self.parent.menuitems[m].Enable(True)

    def update_start_values(self, result):
        """fill parameters with best fit values"""
        allparwids = {}
        for comp in self.fit_components.values():
            if comp.usebox is not None and comp.usebox.IsChecked():
                for name, parwids in comp.parwids.items():
                    allparwids[name] = parwids

        for pname, par in result.params.items():
            if pname in allparwids:
                allparwids[pname].value.SetValue(par.value)

    def autosave_modelresult(self, result, fname=None):
        """autosave model result to user larch folder"""
        xasguidir = os.path.join(site_config.usr_larchdir, 'xasgui')
        if not os.path.exists(xasguidir):
            try:
                os.makedirs(xasguidir)
            except OSError:
                print("Warning: cannot create XAS GUI user folder")
                return
        if not HAS_MODELSAVE:
            print("Warning: cannot save model results: upgrade lmfit")
            return
        if fname is None:
            fname = 'autosave.fitresult'
        fname = os.path.join(xasguidir, fname)
        save_modelresult(result, fname)
