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

from lmfit import Parameter, Parameters, fit_report
try:
    from lmfit.model import (save_modelresult, load_modelresult,
                             save_model, load_model)

    HAS_MODELSAVE = True
except ImportError:
    HAS_MODELSAVE = False

import lmfit.models as lm_models
from lmfit.printfuncs import gformat, CORREL_HEAD

from larch import Group, site_config
from larch.utils import index_of
from larch.utils.jsonutils import encode4js, decode4js

from larch.wxlib import (ReportFrame, BitmapButton, ParameterWidgets,
                         FloatCtrl, FloatSpin, SetTip, GridPanel, get_icon,
                         SimpleText, pack, Button, HLine, Choice, Check,
                         MenuItem, GUIColors, CEN, RCEN, LCEN, FRAMESTYLE,
                         Font, FileSave, FileOpen)

from larch_plugins.std import group2dict
from larch_plugins.io.export_modelresult import export_modelresult
from larch_plugins.wx.parameter import ParameterPanel
from larch_plugins.wx.plotter import last_cursor_pos
from larch_plugins.xasgui.taskpanel import TaskPanel

LCEN = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
CEN |=  wx.ALL

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_NO_NAV_BUTTONS
DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

ModelChoices = {'other': ('<General Models>', 'Constant', 'Linear',
                          'Quadratic', 'Exponential', 'PowerLaw'
                          'Linear Step', 'Arctan Step',
                          'ErrorFunction Step', 'Logistic Step', 'Rectangle'),
                'peaks': ('<Peak Models>', 'Gaussian', 'Lorentzian',
                          'Voigt', 'PseudoVoigt', 'DampedHarmonicOscillator',
                          'Pearson7', 'StudentsT', 'SkewedGaussian',
                          'Moffat', 'BreitWigner', 'Donaich', 'Lognormal'),
                }

# map of lmfit function name to Model Class
ModelFuncs = {'constant': 'ConstantModel',
              'linear': 'LinearModel',
              'parabolic': 'QuadraticModel',
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
              'donaich': 'DonaichModel',
              'powerlaw': 'PowerLawModel',
              'exponential': 'ExponentialModel',
              'step': 'StepModel',
              'rectangle': 'RectangleModel'}

Array_Choices = OrderedDict(((u'Raw \u03BC(E)', 'mu'),
                             (u'Normalized \u03BC(E)', 'norm'),
                             (u'Deconvolved \u03BC(E)', 'deconv'),
                             (u'Derivative \u03BC(E)', 'dmude')))

PLOT_BASELINE = 'Data+Baseline'
PLOT_FIT      = 'Data+Fit'
PLOT_RESID    = 'Data+Residual'
PlotChoices = [PLOT_BASELINE, PLOT_FIT, PLOT_RESID]

FitMethods = ("Levenberg-Marquardt", "Nelder-Mead", "Powell")
ModelWcards = 'Fit Models(*.modl)|*.modl|All files (*.*)|*.*'

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, marker='None', markersize=4)

PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)

MIN_CORREL = 0.0010

COMMANDS = {}
COMMANDS['prepfit'] = """
peakdat = group()
peakdat.xdat = {group:s}.xdat[{imin:d}:{imax:d}]
peakdat.ydat = {group:s}.ydat[{imin:d}:{imax:d}]
peakdat.init_fit = peakmodel.eval(peakpars, x={group:s}.xdat[{imin:d}:{imax:d}])
peakdat.init_ycomps = peakmodel.eval_components(params=peakpars, x={group:s}.xdat[{imin:d}:{imax:d}])
if not hasattr({group:s}, 'peakfit_history'): {group:s}.peakfit_history = []"""

COMMANDS['set_yerr_const'] = "peakdat.yerr = {group:s}.yerr*ones(len(peakdat.xdat))"
COMMANDS['set_yerr_array'] = """peakdat.yerr = 1.0*{group:s}.yerr[{imin:d}:{imax:d}]
yerr_min = 1.e-9*peakdat.ydat.mean()
peakdat.yerr[where({group:s}.yerr < yerr_min)] = yerr_min"""

COMMANDS['dofit'] = """
peakresult = peakmodel.fit(peakdat.ydat, params=peakpars, x=peakdat.xdat, weights=1.0/peakdat.yerr)
peakresult.xdat = peakdat.xdat[:]
peakresult.ydat = peakdat.ydat[:]
peakresult.yerr = peakdat.yerr[:]
peakresult.init_fit = peakdat.init_fit[:]
peakresult.init_ycomps = peakdat.init_ycomps
peakresult.ycomps = peakmodel.eval_components(params=peakresult.params, x=peakdat.xdat)
peakresult.user_options = {user_opts:s}
{group:s}.peakfit_history.insert(0, peakresult)"""


defaults = dict(e=None, elo=-10, ehi=-5, emin=-40, emax=0, yarray='norm')

class FitResultFrame(wx.Frame):
    config_sect = 'prepeak'
    def __init__(self, parent=None, peakframe=None, datagroup=None, **kws):

        wx.Frame.__init__(self, None, -1, title='Fit Results',
                          style=FRAMESTYLE, size=(625, 750), **kws)
        self.parent = parent
        self.peakframe = peakframe
        self.datagroup = datagroup
        self.peakfit_history = getattr(datagroup, 'peakfit_history', [])
        self.nfit = 0
        self.build()

    def build(self):
        sizer = wx.GridBagSizer(10, 5)
        sizer.SetVGap(5)
        sizer.SetHGap(5)

        panel = scrolled.ScrolledPanel(self)
        self.SetMinSize((700, 450))
        self.colors = GUIColors()

        # title row
        self.wids = wids = {}
        title = SimpleText(panel, 'Fit Results',  font=Font(12),
                           colour=self.colors.title, style=LCEN)

        wids['data_title'] = SimpleText(panel, '< > ',  font=Font(12),
                                             colour=self.colors.title, style=LCEN)

        wids['hist_info'] = SimpleText(panel, ' ___ ',  font=Font(12),
                                       colour=self.colors.title, style=LCEN)

        wids['hist_hint'] = SimpleText(panel, '  (Fit #01 is most recent)',
                                       font=Font(12), colour=self.colors.title,
                                       style=LCEN)

        opts = dict(default=False, size=(200, -1), action=self.onPlot)
        self.plot_sub_bline = Check(panel, label='Subtract Baseline?', **opts)
        self.plot_choice = Choice(panel, size=(150, -1),  choices=PlotChoices,
                                  action=self.onPlot)

        irow = 0
        sizer.Add(title,              (irow, 0), (1, 2), LCEN)
        sizer.Add(wids['data_title'], (irow, 2), (1, 2), LCEN)

        irow += 1
        sizer.Add(wids['hist_info'],  (irow, 0), (1, 2), LCEN)
        sizer.Add(wids['hist_hint'],  (irow, 2), (1, 2), LCEN)

        irow += 1
        wids['model_desc'] = SimpleText(panel, '<Model>',  font=Font(11),
                                        size=(700, 50), style=LCEN)
        sizer.Add(wids['model_desc'],  (irow, 0), (1, 6), LCEN)

        irow += 1
        sizer.Add(SimpleText(panel, 'Plot: '), (irow, 0), (1, 1), LCEN)
        sizer.Add(self.plot_choice,            (irow, 1), (1, 1), LCEN)
        sizer.Add(self.plot_sub_bline,         (irow, 2), (1, 1), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(625, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Fit Statistics]]',  font=Font(12),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title, (irow, 0), (1, 4), LCEN)

        sview = self.wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        sview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectFit)
        sview.AppendTextColumn(' Fit #',  width=50)
        sview.AppendTextColumn(' N_data', width=50)
        sview.AppendTextColumn(' N_vary', width=50)
        sview.AppendTextColumn(' N_eval', width=60)
        sview.AppendTextColumn(u' \u03c7\u00B2', width=110)
        sview.AppendTextColumn(u' \u03c7\u00B2_reduced', width=110)
        sview.AppendTextColumn(' Akaike Info', width=110)
        sview.AppendTextColumn(' Bayesian Info', width=110)

        for col in range(sview.ColumnCount):
            this = sview.Columns[col]
            isort, align = True, wx.ALIGN_RIGHT
            if col == 0:
                align = wx.ALIGN_CENTER
            this.Sortable = isort
            this.Alignment = this.Renderer.Alignment = align
        sview.SetMinSize((675, 125))

        irow += 1
        sizer.Add(sview, (irow, 0), (1, 5), LCEN)

#         for label, attr in (('Fit method', 'method'),
#                             ('# Fit Evaluations', 'nfev'),
#                             ('# Data Points', 'ndata'),
#                             ('# Fit Variables', 'nvarys'),
#                             ('# Free Points', 'nfree'),
#                             ('Chi-square', 'chisqr'),
#                             ('Reduced Chi-square', 'redchi'),
#                             ('Akaike Info Criteria', 'aic'),
#                             ('Bayesian Info Criteria', 'bic')):
#             irow += 1
#             wids[attr] = SimpleText(panel, '?')
#             sizer.Add(SimpleText(panel, " %s = " % label),  (irow, 0), (1, 1), LCEN)
#             sizer.Add(wids[attr],                           (irow, 1), (1, 1), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(625, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Variables]]',  font=Font(12),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title, (irow, 0), (1, 1), LCEN)

        self.wids['copy_params'] = Button(panel, 'Update Model with these values',
                                          size=(250, -1), action=self.onCopyParams)

        sizer.Add(self.wids['copy_params'], (irow, 1), (1, 3), LCEN)

        pview = self.wids['params'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
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

        pview.SetMinSize((675, 200))
        pview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectParameter)

        irow += 1
        sizer.Add(pview, (irow, 0), (1, 5), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(625, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Correlations]]',  font=Font(12),
                           colour=self.colors.title, style=LCEN)

        self.wids['all_correl'] = Button(panel, 'Show All',
                                          size=(100, -1), action=self.onAllCorrel)

        self.wids['min_correl'] = FloatSpin(panel, value=MIN_CORREL,
                                            min_val=0, size=(60, -1),
                                            digits=3, increment=0.1)

        ctitle = SimpleText(panel, 'minimum correlation: ')
        sizer.Add(title,  (irow, 0), (1, 1), LCEN)
        sizer.Add(ctitle, (irow, 1), (1, 1), LCEN)
        sizer.Add(self.wids['min_correl'], (irow, 2), (1, 1), LCEN)
        sizer.Add(self.wids['all_correl'], (irow, 3), (1, 1), LCEN)

        irow += 1

        cview = self.wids['correl'] = dv.DataViewListCtrl(panel, style=DVSTYLE)

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

    def get_fitresult(self, nfit=0):
        if len(self.peakfit_history) < 1:
            pfhist = getattr(self.datagroup, 'peakfit_history', [])
            self.peakfit_history = pfhist
        self.nfit = max(0, nfit)
        if self.nfit > len(self.peakfit_history):
            self.nfit = 0
        return self.peakfit_history[self.nfit]

    def onPlot(self, event=None):
        self.peakframe.onPlot()

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

    def show_results(self):
        cur = self.get_fitresult()
        wids = self.wids
        wids['stats'].DeleteAllItems()
        for i, res in enumerate(self.peakfit_history):
            args = ['%2.2d' % (i+1)]
            for attr in ('ndata', 'nvarys', 'nfev', 'chisqr', 'redchi', 'aic', 'bic'):
                val = getattr(res.result, attr)
                if isinstance(val, int):
                    val = '%d' % val
                else:
                    val = gformat(val, 11)
                args.append(val)
            wids['stats'].AppendItem(tuple(args))
        wids['data_title'].SetLabel(self.datagroup.filename)
        self.show_fitresult(nfit=0)

    def show_fitresult(self, nfit=0, datagroup=None):
        if datagroup is not None:
            self.datagroup = datagroup

        result = self.get_fitresult(nfit=nfit)
        wids = self.wids
        wids['data_title'].SetLabel(self.datagroup.filename)
        wids['hist_info'].SetLabel("Fit #%2.2d of %d" % (nfit+1, len(self.peakfit_history)))

        parts = []
        model_repr = result.model._reprstring(long=True)
        for word in model_repr.split('Model('):
            if ',' in word:
                pref, suff = word.split(', ')
                parts.append( ("%sModel(%s" % (pref.title(), suff) ))
            else:
                parts.append(word)
        desc = ''.join(parts)
        parts = []
        tlen = 90
        while len(desc) >= tlen:
            i = desc[tlen-1:].find('+')
            if i < 0:
                break
            parts.append(desc[:tlen+i])
            desc = desc[tlen+i:]
        parts.append(desc)
        wids['model_desc'].SetLabel('\n'.join(parts))


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
                serr = gformat(param.stderr, 10)
            extra = ' '
            if param.expr is not None:
                extra = ' = %s ' % param.expr
            elif param.init_value is not None:
                extra = ' (init=%s)' % gformat(param.init_value, 11)
            elif not param.vary:
                extra = ' (fixed)'

            wids['params'].AppendItem((pname, val, serr, extra))
            wids['paramsdata'].append(pname)
        self.Refresh()


class PrePeakPanel(TaskPanel):
    def __init__(self, parent=None, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='prepreaks_config',
                           config=defaults, **kws)

        self.fit_components = OrderedDict()
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
            # print(" Fill prepeak panel from group ", fname, gname, dgroup)
            self.fill_form(dgroup)
        except:
            pass # print(" Cannot Fill prepeak panel from group ")

    def build_display(self):
        self.mod_nb = flat_nb.FlatNotebook(self, -1, agwStyle=FNB_STYLE)
        self.mod_nb.SetTabAreaColour(wx.Colour(250,250,250))
        self.mod_nb.SetActiveTabColour(wx.Colour(254,254,195))

        self.mod_nb.SetNonActiveTabTextColour(wx.Colour(10,10,128))
        self.mod_nb.SetActiveTabTextColour(wx.Colour(128,0,0))
        self.mod_nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onNBChanged)

        pan = self.panel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LCEN)

        self.wids = {}

        def FloatSpinWithPin(name, value, **kws):
            s = wx.BoxSizer(wx.HORIZONTAL)
            self.wids[name] = FloatSpin(pan, value=value, **kws)
            bb = BitmapButton(pan, get_icon('pin'), size=(25, 25),
                              action=partial(self.onSelPoint, opt=name),
                              tooltip='use last point selected from plot')
            s.Add(self.wids[name])
            s.Add(bb)
            return s

        opts = dict(digits=2, increment=0.1)
        ppeak_e0   = FloatSpinWithPin('ppeak_e0', value=0, **opts)
        ppeak_elo  = FloatSpinWithPin('ppeak_elo', value=-15, **opts)
        ppeak_ehi  = FloatSpinWithPin('ppeak_ehi', value=-5, **opts)
        ppeak_emin = FloatSpinWithPin('ppeak_emin', value=-30, **opts)
        ppeak_emax = FloatSpinWithPin('ppeak_emax', value=0, **opts)

        self.fitbline_btn  = Button(pan,'Fit Baseline', action=self.onFitBaseline,
                                    size=(150, -1))
        self.plotmodel_btn = Button(pan, 'Plot Model',
                                   action=self.onPlotModel,  size=(150, -1))
        self.fitmodel_btn = Button(pan, 'Fit Model',
                                   action=self.onFitModel,  size=(150, -1))
        # self.fitsel_btn = Button(pan, 'Fit Selected Groups',
        #                          action=self.onFitSelected,  size=(150, 25))
        self.fitmodel_btn.Disable()
        # self.fitsel_btn.Disable()

        self.array_choice = Choice(pan, size=(150, -1),
                                   choices=list(Array_Choices.keys()))
        self.array_choice.SetSelection(1)

        models_peaks = Choice(pan, size=(150, -1),
                              choices=ModelChoices['peaks'],
                              action=self.addModel)

        models_other = Choice(pan, size=(150, -1),
                              choices=ModelChoices['other'],
                              action=self.addModel)

        self.models_peaks = models_peaks
        self.models_other = models_other


        self.message = SimpleText(pan,
                                 'first fit baseline, then add peaks to fit model.')

        self.msg_centroid = SimpleText(pan, '----')

        opts = dict(default=True, size=(75, -1), action=self.onPlot)
        self.show_centroid  = Check(pan, label='show?', **opts)
        self.show_peakrange = Check(pan, label='show?', **opts)
        self.show_fitrange  = Check(pan, label='show?', **opts)
        self.show_e0        = Check(pan, label='show?', **opts)

        opts = dict(default=False, size=(200, -1), action=self.onPlot)
        # self.plot_sub_bline = Check(pan, label='Subtract Baseline?', **opts)
        # self.plot_choice = Choice(pan, size=(150, -1),  choices=PlotChoices,
        #                                   action=self.onPlot)

        def add_text(text, dcol=1, newrow=True):
            pan.Add(SimpleText(pan, text), dcol=dcol, newrow=newrow)

        titleopts = dict(font=Font(12), colour='#AA0000')
        pan.Add(SimpleText(pan, ' Pre-edge Peak Fitting', **titleopts), dcol=5)
        add_text(' Run Fit:', newrow=False)

        add_text('Array to fit: ')
        pan.Add(self.array_choice, dcol=3)
        pan.Add((10, 10))
        pan.Add(self.fitbline_btn)

        add_text('E0: ')
        pan.Add(ppeak_e0)
        pan.Add((10, 10), dcol=2)
        pan.Add(self.show_e0)
        pan.Add(self.plotmodel_btn)


        add_text('Fit Energy Range: ')
        pan.Add(ppeak_emin)
        add_text(' : ', newrow=False)
        pan.Add(ppeak_emax)
        pan.Add(self.show_fitrange)
        pan.Add(self.fitmodel_btn)

        t = SimpleText(pan, 'Pre-edge Peak Range: ')
        t.SetToolTip('Range used as mask for background')

        pan.Add(t, newrow=True)
        pan.Add(ppeak_elo)
        add_text(' : ', newrow=False)
        pan.Add(ppeak_ehi)
        pan.Add(self.show_peakrange)
        # pan.Add(self.fitsel_btn)

        add_text( 'Peak Centroid: ')
        pan.Add(self.msg_centroid, dcol=3)
        pan.Add(self.show_centroid, dcol=1)

        #  plot buttons
        # ts = wx.BoxSizer(wx.HORIZONTAL)
        # ts.Add(self.plot_choice)
        # ts.Add(self.plot_sub_bline)

        # pan.Add(SimpleText(pan, 'Plot: '), newrow=True)
        # pan.Add(ts, dcol=7)

        #  add model
        ts = wx.BoxSizer(wx.HORIZONTAL)
        ts.Add(models_peaks)
        ts.Add(models_other)

        pan.Add(SimpleText(pan, 'Add Component: '), newrow=True)
        pan.Add(ts, dcol=7)

        pan.Add(SimpleText(pan, 'Messages: '), newrow=True)
        pan.Add(self.message, dcol=7)

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
            conf = defaults
            conf['e0'] = getattr(dgroup, 'e0', -1)

        dgroup.prepeak_config = conf
        if not hasattr(dgroup, 'prepeaks'):
            dgroup.prepeaks = Group()

        return conf

    def fill_form(self, dat):
        if isinstance(dat, Group):
            self.wids['ppeak_e0'].SetValue(dat.e0)
            if hasattr(dat, 'prepeaks'):
                self.wids['ppeak_emin'].SetValue(dat.prepeaks.emin)
                self.wids['ppeak_emax'].SetValue(dat.prepeaks.emax)
                self.wids['ppeak_elo'].SetValue(dat.prepeaks.elo)
                self.wids['ppeak_ehi'].SetValue(dat.prepeaks.ehi)

        elif instance(dat, dict):
            self.wids['ppeak_e0'].SetValue(dat['e0'])
            self.wids['ppeak_emin'].SetValue(dat['emin'])
            self.wids['ppeak_emax'].SetValue(dat['emax'])
            self.wids['ppeak_elo'].SetValue(dat['elo'])
            self.wids['ppeak_ehi'].SetValue(dat['ehi'])

            self.array_choice.SetStringSelection(dat['array_desc'])
            self.show_e0.Enable(dat['show_e0'])
            self.show_centroid.Enable(dat['show_centroid'])
            self.show_fitrange.Enable(dat['show_fitrange'])
            self.show_peakrange.Enable(dat['show_peakrange'])
            # self.plot_sub_bline.Enable(dat['plot_sub_bline'])

    def read_form(self):
        "read for, returning dict of values"
        dgroup = self.controller.get_group()
        array_desc = self.array_choice.GetStringSelection()
        form_opts = {'gname': dgroup.groupname,
                     'filename': dgroup.filename,
                     'array_desc': array_desc.lower(),
                     'array_name': Array_Choices[array_desc],
                     'baseline_form': 'lorentzian'}

        form_opts['e0'] = self.wids['ppeak_e0'].GetValue()
        form_opts['emin'] = self.wids['ppeak_emin'].GetValue()
        form_opts['emax'] = self.wids['ppeak_emax'].GetValue()
        form_opts['elo'] = self.wids['ppeak_elo'].GetValue()
        form_opts['ehi'] = self.wids['ppeak_ehi'].GetValue()
        form_opts['plot_sub_bline'] = False # self.plot_sub_bline.IsChecked()
        form_opts['show_centroid'] = self.show_centroid.IsChecked()
        form_opts['show_peakrange'] = self.show_peakrange.IsChecked()
        form_opts['show_fitrange'] = self.show_fitrange.IsChecked()
        form_opts['show_e0'] = self.show_e0.IsChecked()
        return form_opts

    def onFitBaseline(self, evt=None):
        opts = self.read_form()
        cmd = """{gname:s}.ydat = 1.0*{gname:s}.{array_name:s}
pre_edge_baseline(energy={gname:s}.energy, norm={gname:s}.ydat, group={gname:s}, form='{baseline_form:s}',
                  with_line=True, elo={elo:.3f}, ehi={ehi:.3f}, emin={emin:.3f}, emax={emax:.3f})"""
        self.larch_eval(cmd.format(**opts))

        dgroup = self.controller.get_group()
        ppeaks = dgroup.prepeaks
        dgroup.centroid_msg = "%.4f +/- %.4f eV" % (ppeaks.centroid,
                                                    ppeaks.delta_centroid)

        self.msg_centroid.SetLabel(dgroup.centroid_msg)

        if 'bp_' not in self.fit_components:
            self.addModel(model='Lorentzian', prefix='bp_', isbkg=True)
        if 'bl_' not in self.fit_components:
            self.addModel(model='Linear', prefix='bl_', isbkg=True)

        for prefix in ('bp_', 'bl_'):
            cmp = self.fit_components[prefix]
            # cmp.bkgbox.SetValue(1)
            self.fill_model_params(prefix, dgroup.prepeaks.fit_details.params)

        self.fill_form(dgroup)
        self.fitmodel_btn.Enable()
        # self.fitallmodel_btn.Enable()

        i1, i2 = self.get_xranges(dgroup.energy)
        dgroup.yfit = dgroup.xfit = 0.0*dgroup.energy[i1:i2]

        # self.plot_choice.SetStringSelection(PLOT_BASELINE)
        self.onPlot(choice=PLOT_BASELINE)

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
        g = self.build_fitmodel(dgroup)
        self.onPlot(choice=PLOT_FIT)

    def onPlot(self, evt=None, choice=PLOT_FIT):
        plot_choice = choice # self.plot_choice.GetStringSelection()

        opts = self.read_form()
        dgroup = self.controller.get_group()
        gname = dgroup.groupname
        if choice == PLOT_BASELINE:
            cmd = ["newplot({group:s}.xdat, {group:s}.ydat)",
                   "plot({group:s}.prepeaks.energy, {group:s}.prepeaks.baseline)"]
            cmd = '\n'.join(cmd)
        else:
            cmd = "plot_prepeak({group:s})"
        self.larch_eval(cmd.format(group=gname))


            #         ppanel.plot(xdat, ydat, **plotopts)
#         if plot_choice == PLOT_BASELINE:
#             if not opts['plot_sub_bline']:
#                 ppanel.oplot(dgroup.prepeaks.energy,
#                              dgroup.prepeaks.baseline,
#                              label='baseline', **PLOTOPTS_2)

#         ppeaks = getattr(dgroup, 'prepeaks', None)
#         if ppeaks is None:
#             return
#
#         i1, i2 = self.get_xranges(dgroup.xdat)
#         # i2 = len(ppeaks.baseline) + i1
#
#         if len(dgroup.yfit) > len(ppeaks.baseline):
#             i2 = i1 + len(ppeaks.baseline)
#         # print(" Indexes: ", i1, i2, i2-i1, len(dgroup.yfit), len(ppeaks.baseline))
#
#         xdat = 1.0*dgroup.energy
#         ydat = 1.0*dgroup.ydat
#         yfit = 1.0*dgroup.ydat
#         baseline = 1.0*dgroup.ydat
#         yfit[i1:i2] = dgroup.yfit[:i2-i1]
#         baseline[i1:i2] = ppeaks.baseline[:i2-i1]
#
#         if opts['plot_sub_bline']:
#             ydat = ydat - baseline
#             if plot_choice in (PLOT_FIT, PLOT_RESID):
#                 yfit = yfit - baseline
#         if plot_choice == PLOT_RESID:
#             resid = ydat - yfit
#
#         _xs = dgroup.energy[i1:i2]
#         xrange = max(_xs) - min(_xs)
#         pxmin = min(_xs) - 0.05 * xrange
#         pxmax = max(_xs) + 0.05 * xrange
#
#         jmin = index_of(dgroup.energy, pxmin)
#         jmax = index_of(dgroup.energy, pxmax) + 1
#
#         _ys = ydat[jmin:jmax]
#         yrange = max(_ys) - min(_ys)
#         pymin = min(_ys) - 0.05 * yrange
#         pymax = max(_ys) + 0.05 * yrange
#
#         title = ' pre-edge fit'
#         if plot_choice == PLOT_BASELINE:
#             title = ' pre-edge baseline'
#             if opts['plot_sub_bline']:
#                 title = ' pre-edge peaks'
#
#         array_desc = self.array_choice.GetStringSelection()
#
#         plotopts = {'xmin': pxmin, 'xmax': pxmax,
#                     'ymin': pymin, 'ymax': pymax,
#                     'title': '%s:\n%s' % (opts['filename'], title),
#                     'xlabel': 'Energy (eV)',
#                     'ylabel': opts['array_desc'],
#                     'label': opts['array_desc'],
#                     'delay_draw': True,
#                     'show_legend': True}
#
#         plot_extras = []
#         if opts['show_fitrange']:
#             popts = {'color': '#DDDDCC'}
#             emin = opts['emin']
#             emax = opts['emax']
#             imin = index_of(dgroup.energy, emin)
#             imax = index_of(dgroup.energy, emax)
#
#             plot_extras.append(('vline', emin, None, popts))
#             plot_extras.append(('vline', emax, None, popts))
#
#         if opts['show_peakrange']:
#             popts = {'marker': '+', 'markersize': 6}
#             elo = opts['elo']
#             ehi = opts['ehi']
#             ilo = index_of(dgroup.xdat, elo)
#             ihi = index_of(dgroup.xdat, ehi)
#
#             plot_extras.append(('marker', elo, ydat[ilo], popts))
#             plot_extras.append(('marker', ehi, ydat[ihi], popts))
#
#         if opts['show_centroid']:
#             popts = {'color': '#EECCCC'}
#             ecen = getattr(dgroup.prepeaks, 'centroid', -1)
#             if ecen > min(dgroup.energy):
#                 plot_extras.append(('vline', ecen, None,  popts))
#
#         if plot_choice == PLOT_RESID:
#             pframe = self.controller.get_display(win=2, stacked=True)
#         else:
#             pframe = self.controller.get_display(win=1)
#
#         ppanel = pframe.panel
#         axes = ppanel.axes
#
#         plotopts.update(PLOTOPTS_1)
#
#         ppanel.plot(xdat, ydat, **plotopts)
#         if plot_choice == PLOT_BASELINE:
#             if not opts['plot_sub_bline']:
#                 ppanel.oplot(dgroup.prepeaks.energy,
#                              dgroup.prepeaks.baseline,
#                              label='baseline', **PLOTOPTS_2)
#
#         elif plot_choice in (PLOT_FIT, PLOT_RESID):
#             ppanel.oplot(dgroup.energy, yfit,
#                          label='fit', **PLOTOPTS_1)
#
#             if hasattr(dgroup, 'ycomps'):
#                 ncomp = len(dgroup.ycomps)
#                 icomp = 0
#                 for label, ycomp in dgroup.ycomps.items():
#                     icomp +=1
#                     fcomp = self.fit_components[label]
#                     if not (fcomp.bkgbox.IsChecked() and opts['plot_sub_bline']):
#                         ppanel.oplot(dgroup.xfit, ycomp, label=label,
#                                      delay_draw=(icomp!=ncomp), style='short dashed')
#
#             if plot_choice == PLOT_RESID:
#                 _ys = resid
#                 yrange = max(_ys) - min(_ys)
#                 plotopts['ymin'] = min(_ys) - 0.05 * yrange
#                 plotopts['ymax'] = max(_ys) + 0.05 * yrange
#                 plotopts['delay_draw'] = False
#                 plotopts['ylabel'] = 'data-fit'
#                 plotopts['label'] = '_nolegend_'
#
#                 pframe.plot(dgroup.energy, resid, panel='bot', **plotopts)
#                 pframe.Show()
#                 # print(" RESIDUAL PLOT  margins: ")
#                 # print(" top : ", pframe.panel.conf.margins)
#                 # print(" bot : ", pframe.panel_bot.conf.margins)
#
#         for etype, x, y, opts in plot_extras:
#             if etype == 'marker':
#                 popts = {'marker': 'o', 'markersize': 4,
#                          'label': '_nolegend_',
#                          'markerfacecolor': 'red',
#                          'markeredgecolor': '#884444'}
#                 popts.update(opts)
#                 axes.plot([x], [y], **popts)
#             elif etype == 'vline':
#                 popts = {'ymin': 0, 'ymax': 1.0, 'color': '#888888'}
#                 popts.update(opts)
#                 axes.axvline(x, **popts)
#         ppanel.canvas.draw()

    def onNBChanged(self, event=None):
        idx = self.mod_nb.GetSelection()

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

            if form.startswith('err'): form = 'erf'
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

        panel = GridPanel(self.mod_nb, ncols=2, nrows=5, pad=2, itemstyle=CEN)

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label,
                               size=size, style=wx.ALIGN_LEFT, **kws)
        usebox = Check(panel, default=True, label='Use in Fit?', size=(100, -1))
        bkgbox = Check(panel, default=False, label='Is Baseline?', size=(125, -1))
        if isbkg:
            bkgbox.SetValue(1)

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

        # sx,sy = self.GetSize()
        # self.SetSize((sx, sy+1))
        # self.SetSize((sx, sy))

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
        plotframe = self.controller.get_display(win=1)
        plotframe.cursor_hist = []
        plotframe.oplot(dgroup.xdat, dgroup._tmp)
        self.pick2erase_panel = plotframe.panel

        self.pick2erase_timer.Start(5000)


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
        self.pick2_timer.Start(250)


    def onSaveFitResult(self, event=None):
        dgroup = self.controller.get_group()
        deffile = dgroup.filename.replace('.', '_') + '.modl'

        outfile = FileSave(self, 'Save Fit Result',
                           default_file=deffile,
                           wildcard=ModelWcards)

        if outfile is not None:
            try:
                self.save_fit_result(self.get_fitresult(), outfile)
            except IOError:
                print('could not write %s' % outfile)

    def onLoadFitResult(self, event=None):
        mfile = FileOpen(self, 'Load Fit Result',
                         default_file='', wildcard=ModelWcards)
        if mfile is not None:
            self.load_modelresult(mfile)

    def save_fit_result(self, fitresult, outfile):
        """saves a customized ModelResult"""
        save_modelresult(fitresult, outfile)

    def load_modelresult(self, inpfile):
        """read a customized ModelResult"""
        result = load_modelresult(inpfile)

        for prefix in list(self.fit_components.keys()):
            self.onDeleteComponent(self, prefix=prefix)

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

        self.fill_form(result.user_options)
        return result

    def onExportFitResult(self, event=None):
        dgroup = self.controller.get_group()
        deffile = dgroup.filename.replace('.', '_') + '_result.xdi'
        wcards = 'All files (*.*)|*.*'

        outfile = FileSave(self, 'Export Fit Result',
                           default_file=deffile, wildcard=wcards)

        if outfile is not None:
            i1, i2 = self.get_xranges(dgroup.xdat)
            x = dgroup.xdat[i1:i2]
            y = dgroup.ydat[i1:i2]
            yerr = None
            if hasattr(dgroup, 'yerr'):
                yerr = 1.0*dgroup.yerr
                if not isinstance(yerr, np.ndarray):
                    yerr = yerr * np.ones(len(y))
                else:
                    yerr = yerr[i1:i2]

            export_modelresult(self.get_fitresult(),
                               filename=outfile,
                               datafile=dgroup.filename,
                               ydata=y, yerr=yerr, x=x)


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

    def build_fitmodel(self, dgroup):
        """ use fit components to build model"""
        # self.summary = {'components': [], 'options': {}}
        peaks = []
        cmds = ["## set up pre-edge peak parameters", "peakpars = Parameters()"]
        modcmds = ["## define pre-edge peak model"]
        modop = " ="
        for comp in self.fit_components.values():
            _cen, _amp = None, None
            if comp.usebox is not None and comp.usebox.IsChecked():
                for parwids in comp.parwids.values():
                    this = parwids.param
                    if this.expr is not None:
                        pargs = "expr='%s'" % (this.expr)
                    else:
                        pargs = "value=%f, min=%f, max=%f" % (this.value,
                                                              this.min, this.max)
                    cmds.append("peakpars.add('%s', %s)" % (this.name, pargs))
                    if this.name.endswith('_center'):
                        _cen = this.name
                    elif parwids.param.name.endswith('_amplitude'):
                        _amp = this.name

                modcmds.append("peakmodel %s %s(prefix='%s')" % (modop, comp.mclass.__name__,
                                                                 comp.mclass_kws['prefix']))
                modop = "+="
                if not comp.bkgbox.IsChecked() and _cen is not None and _amp is not None:
                    peaks.append((_amp, _cen))

        if len(peaks) > 0:
            denom = '+'.join([p[0] for p in peaks])
            numer = '+'.join(["%s*%s "% p for p in peaks])
            cmds.append("peakpars.add('fit_centroid', expr='(%s)/(%s)')" % (numer, denom))

        cmds.extend(modcmds)

        imin, imax = self.get_xranges(dgroup.xdat)
        cmds.append(COMMANDS['prepfit'].format(group=dgroup.groupname, imin=imin, imax=imax))

        self.larch_eval("\n".join(cmds))

    def onFitSelected(self, event=None):
        dgroup = self.controller.get_group()
        self.build_fitmodel(dgroup)
        opts = self.read_form()
        # print("fitting selected groups in progress")

    def onFitModel(self, event=None):
        dgroup = self.controller.get_group()
        if dgroup is None:
            return
        self.build_fitmodel(dgroup)
        opts = self.read_form()
        # add bkg_component to saved user options
        bkg_comps = []
        for label, comp in self.fit_components.items():
            if comp.bkgbox.IsChecked():
                bkg_comps.append(label)
        opts['bkg_components'] = bkg_comps

        imin, imax = self.get_xranges(dgroup.xdat)

        if not hasattr(dgroup, 'yerr'):
            dgroup.yerr = 1.0

        yerr_type = 'set_yerr_const'
        if  isinstance(dgroup.yerr, np.ndarray):
            yerr_type = 'set_yerr_array'

        cmds = ["## do peak fit: ",
                COMMANDS[yerr_type],
                COMMANDS['dofit']]

        cmd = '\n'.join(cmds)
        self.larch_eval(cmd.format(group=dgroup.groupname,
                                   imin=imin, imax=imax,
                                   user_opts=repr(opts)))

        self.autosave_modelresult(self.larch_get("peakresult"))

        self.onPlot()
        self.parent.show_subframe('prepeak_result_frame', FitResultFrame,
                                  datagroup=dgroup, peakframe=self)
        self.parent.subframes['prepeak_result_frame'].show_results()

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
        confdir = os.path.join(site_config.usr_larchdir, 'xas_viewer')
        if not os.path.exists(confdir):
            try:
                os.makedirs(confdir)
            except OSError:
                print("Warning: cannot create XAS GUI user folder")
                return
        if not HAS_MODELSAVE:
            print("Warning: cannot save model results: upgrade lmfit")
            return
        if fname is None:
            fname = 'autosave.fitresult'
        self.save_fit_result(result, os.path.join(confdir, fname))
