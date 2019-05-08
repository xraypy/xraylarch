import time
import os
import numpy as np
np.seterr(all='ignore')

from functools import partial
from collections import OrderedDict
import json

import wx
import wx.lib.scrolledpanel as scrolled

import wx.dataview as dv

from lmfit import Parameter
try:
    from lmfit.model import (save_modelresult, load_modelresult,
                             save_model, load_model)
    HAS_MODELSAVE = True
except ImportError:
    HAS_MODELSAVE = False

import lmfit.models as lm_models
from lmfit.printfuncs import gformat, CORREL_HEAD

from larch import Group, site_config
from larch.math import index_of
from larch.utils.jsonutils import encode4js, decode4js
from larch.io.export_modelresult import export_modelresult

from larch.wxlib import (ReportFrame, BitmapButton, FloatCtrl, FloatSpin,
                         SetTip, GridPanel, get_icon, SimpleText, pack,
                         Button, HLine, Choice, Check, MenuItem, GUIColors,
                         CEN, RCEN, LCEN, FRAMESTYLE, Font, FONTSIZE,
                         FileSave, FileOpen, flatnotebook)

from larch.wxlib.parameter import ParameterWidgets
from larch.wxlib.plotter import last_cursor_pos
from .taskpanel import TaskPanel

LCEN = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
CEN |=  wx.ALL

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

Array_Choices = {'Raw \u03BC(E)': 'mu',
                 'Normalized \u03BC(E)': 'norm',
                 'Deconvolved \u03BC(E)': 'deconv',
                 'Derivative \u03BC(E)': 'dmude'}

PLOT_BASELINE = 'Data+Baseline'
PLOT_FIT      = 'Data+Fit'
PLOT_INIT     = 'Data+Init Fit'
PLOT_RESID    = 'Data+Residual'
PlotChoices = [PLOT_BASELINE, PLOT_FIT, PLOT_RESID]

FitMethods = ("Levenberg-Marquardt", "Nelder-Mead", "Powell")
ModelWcards = "Fit Models(*.modl)|*.modl|All files (*.*)|*.*"

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, marker='None', markersize=4)

PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)

MIN_CORREL = 0.10

COMMANDS = {}
COMMANDS['prepfit'] = """# prepare fit
{group}.prepeaks.user_options = {user_opts:s}
{group}.prepeaks.init_fit = peakmodel.eval(peakpars, x={group}.prepeaks.energy)
{group}.prepeaks.init_ycomps = peakmodel.eval_components(params=peakpars, x={group}.prepeaks.energy)
if not hasattr({group}.prepeaks, 'fit_history'): {group}.prepeaks.fit_history = []
"""

COMMANDS['prepeaks_setup'] = """# setup prepeaks
{group:s}.xdat = 1.0*{group:s}.energy
{group:s}.ydat = 1.0*{group:s}.{array_name:s}
prepeaks_setup(energy={group:s}.energy, norm={group:s}.ydat, group={group:s},
               elo={elo:.3f}, ehi={ehi:.3f}, emin={emin:.3f}, emax={emax:.3f})
"""

COMMANDS['set_yerr_const'] = "{group}.prepeaks.norm_std = {group}.yerr*ones(len({group}.prepeaks.norm))"
COMMANDS['set_yerr_array'] = """
{group}.prepeaks.norm_std = 1.0*{group}.yerr[{imin:d}:{imax:d}]
yerr_min = 1.e-9*{group}.prepeaks.ydat.mean()
{group}.prepeaks.norm_std[where({group}.yerr < yerr_min)] = yerr_min
"""

COMMANDS['dofit'] = """# do fit
peakresult = peakmodel.fit({group}.prepeaks.norm, params=peakpars, x={group}.prepeaks.energy, weights=1.0/{group}.prepeaks.norm_std)
peakresult.energy   = {group}.prepeaks.energy[:]
peakresult.norm     = {group}.prepeaks.norm[:]
peakresult.norm_std = {group}.prepeaks.norm_std[:]
peakresult.ycomps   = peakmodel.eval_components(params=peakresult.params, x={group}.prepeaks.energy)
peakresult.init_fit = {group}.prepeaks.init_fit[:]
peakresult.init_ycomps = peakmodel.eval_components(params=peakpars, x={group}.prepeaks.energy)
peakresult.user_options = {user_opts:s}
{group}.prepeaks.fit_history.insert(0, peakresult)"""

defaults = dict(e=None, elo=-10, ehi=-5, emin=-40, emax=0, yarray='norm')


def get_xlims(x, xmin, xmax):
    xeps = min(np.diff(x))/ 5.
    i1 = index_of(x, xmin + xeps)
    i2 = index_of(x, xmax + xeps) + 1
    return i1, i2

class FitResultFrame(wx.Frame):
    config_sect = 'prepeak'
    def __init__(self, parent=None, peakframe=None, datagroup=None, **kws):

        wx.Frame.__init__(self, None, -1, title='Fit Results',
                          style=FRAMESTYLE, size=(625, 750), **kws)
        self.peakframe = peakframe
        self.datagroup = datagroup
        self.peakfit_history = getattr(datagroup.prepeaks, 'fit_history', [])
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
        title = SimpleText(panel, 'Fit Results', font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LCEN)

        wids['data_title'] = SimpleText(panel, '< > ', font=Font(FONTSIZE+2),
                                             colour=self.colors.title, style=LCEN)

        wids['hist_info'] = SimpleText(panel, ' ___ ', font=Font(FONTSIZE+2),
                                       colour=self.colors.title, style=LCEN)

        wids['hist_hint'] = SimpleText(panel, '  (Fit #01 is most recent)',
                                       font=Font(FONTSIZE+2), colour=self.colors.title,
                                       style=LCEN)

        opts = dict(default=False, size=(200, -1), action=self.onPlot)
        wids['plot_bline'] = Check(panel, label='Plot baseline-subtracted?', **opts)
        wids['plot_resid'] = Check(panel, label='Plot with residual?', **opts)
        self.plot_choice = Button(panel, 'Plot Selected Fit',
                                  size=(175, -1), action=self.onPlot)


        self.save_result = Button(panel, 'Save Selected Model',
                                  size=(175, -1), action=self.onSaveFitResult)
        SetTip(self.save_result, 'save model and result to be loaded later')

        self.export_fit  = Button(panel, 'Export Fit',
                                  size=(175, -1), action=self.onExportFitResult)
        SetTip(self.export_fit, 'save arrays and results to text file')

        irow = 0
        sizer.Add(title,              (irow, 0), (1, 2), LCEN)
        sizer.Add(wids['data_title'], (irow, 2), (1, 2), LCEN)

        irow += 1
        sizer.Add(wids['hist_info'],  (irow, 0), (1, 2), LCEN)
        sizer.Add(wids['hist_hint'],  (irow, 2), (1, 2), LCEN)

        irow += 1
        wids['model_desc'] = SimpleText(panel, '<Model>', font=Font(FONTSIZE+1),
                                        size=(700, 50), style=LCEN)
        sizer.Add(wids['model_desc'],  (irow, 0), (1, 6), LCEN)

        irow += 1
        sizer.Add(self.save_result, (irow, 0), (1, 1), LCEN)
        sizer.Add(self.export_fit,  (irow, 1), (1, 2), LCEN)

        irow += 1
        # sizer.Add(SimpleText(panel, 'Plot: '), (irow, 0), (1, 1), LCEN)
        sizer.Add(self.plot_choice,   (irow, 0), (1, 2), LCEN)
        sizer.Add(wids['plot_bline'], (irow, 2), (1, 1), LCEN)
        sizer.Add(wids['plot_resid'], (irow, 3), (1, 1), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Fit Statistics]]',  font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title, (irow, 0), (1, 4), LCEN)

        sview = self.wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        sview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectFit)
        sview.AppendTextColumn(' Fit #',  width=50)
        sview.AppendTextColumn(' N_data', width=50)
        sview.AppendTextColumn(' N_vary', width=50)
        sview.AppendTextColumn(' N_eval', width=60)
        sview.AppendTextColumn(' \u03c7\u00B2', width=110)
        sview.AppendTextColumn(' \u03c7\u00B2_reduced', width=110)
        sview.AppendTextColumn(' Akaike Info', width=110)
        sview.AppendTextColumn(' Bayesian Info', width=110)

        for col in range(sview.ColumnCount):
            this = sview.Columns[col]
            isort, align = True, wx.ALIGN_RIGHT
            if col == 0:
                align = wx.ALIGN_CENTER
            this.Sortable = isort
            this.Alignment = this.Renderer.Alignment = align
        sview.SetMinSize((700, 125))

        irow += 1
        sizer.Add(sview, (irow, 0), (1, 5), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Variables]]',  font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title, (irow, 0), (1, 1), LCEN)

        self.wids['copy_params'] = Button(panel, 'Update Model with these values',
                                          size=(250, -1), action=self.onCopyParams)

        sizer.Add(self.wids['copy_params'], (irow, 1), (1, 3), LCEN)

        pview = self.wids['params'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        self.wids['paramsdata'] = []
        pview.AppendTextColumn('Parameter',         width=150)
        pview.AppendTextColumn('Best-Fit Value',    width=125)
        pview.AppendTextColumn('Standard Error',    width=125)
        pview.AppendTextColumn('Info ',             width=275)

        for col in range(4):
            this = pview.Columns[col]
            align = wx.ALIGN_LEFT
            if col in (1, 2):
                align = wx.ALIGN_RIGHT
            this.Sortable = False
            this.Alignment = this.Renderer.Alignment = align

        pview.SetMinSize((700, 200))
        pview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectParameter)

        irow += 1
        sizer.Add(pview, (irow, 0), (1, 5), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(650, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Correlations]]',  font=Font(FONTSIZE+2),
                           colour=self.colors.title, style=LCEN)

        self.wids['all_correl'] = Button(panel, 'Show All',
                                          size=(100, -1), action=self.onAllCorrel)

        self.wids['min_correl'] = FloatSpin(panel, value=MIN_CORREL,
                                            min_val=0, size=(100, -1),
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
        self.peakfit_history = getattr(self.datagroup.prepeaks, 'fit_history', [])
        self.nfit = max(0, nfit)
        if self.nfit > len(self.peakfit_history):
            self.nfit = 0
        return self.peakfit_history[self.nfit]

    def onPlot(self, event=None):
        show_resid = self.wids['plot_resid'].IsChecked()
        sub_bline = self.wids['plot_bline'].IsChecked()
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
                pref, suff = word.split(', ', 1)
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
        for param in reversed(result.params.values()):
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
            elif not param.vary:
                extra = ' (fixed)'
            elif param.init_value is not None:
                extra = ' (init=%s)' % gformat(param.init_value, 11)

            wids['params'].AppendItem((pname, val, serr, extra))
            wids['paramsdata'].append(pname)
        self.Refresh()


class PrePeakPanel(TaskPanel):
    def __init__(self, parent=None, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='prepeaks_config',
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
            self.fill_form(dgroup)
        except:
            pass # print(" Cannot Fill prepeak panel from group ")

    def build_display(self):
        self.mod_nb = flatnotebook(self, {})
        pan = self.panel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LCEN)

        self.wids = {}

        fsopts = dict(digits=2, increment=0.1, with_pin=True)
        ppeak_e0   = self.add_floatspin('ppeak_e0', value=0, **fsopts)
        ppeak_elo  = self.add_floatspin('ppeak_elo', value=-15, **fsopts)
        ppeak_ehi  = self.add_floatspin('ppeak_ehi', value=-5, **fsopts)
        ppeak_emin = self.add_floatspin('ppeak_emin', value=-30, **fsopts)
        ppeak_emax = self.add_floatspin('ppeak_emax', value=0, **fsopts)

        self.fitbline_btn  = Button(pan,'Fit Baseline', action=self.onFitBaseline,
                                    size=(125, -1))
        self.plotmodel_btn = Button(pan, 'Plot Model',
                                   action=self.onPlotModel,  size=(125, -1))
        self.fitmodel_btn = Button(pan, 'Fit Model',
                                   action=self.onFitModel,  size=(125, -1))
        self.loadmodel_btn = Button(pan, 'Load Model',
                                    action=self.onLoadFitResult,  size=(125, -1))
        self.fitmodel_btn.Disable()

        self.array_choice = Choice(pan, size=(175, -1),
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

        def add_text(text, dcol=1, newrow=True):
            pan.Add(SimpleText(pan, text), dcol=dcol, newrow=newrow)

        pan.Add(SimpleText(pan, ' Pre-edge Peak Fitting',
                           **self.titleopts), dcol=5)
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
        SetTip(t, 'Range used as mask for background')

        pan.Add(t, newrow=True)
        pan.Add(ppeak_elo)
        add_text(' : ', newrow=False)
        pan.Add(ppeak_ehi)
        pan.Add(self.show_peakrange)


        # pan.Add(self.fitsel_btn)

        add_text( 'Peak Centroid: ')
        pan.Add(self.msg_centroid, dcol=3)
        pan.Add(self.show_centroid, dcol=1)
        pan.Add(self.loadmodel_btn)

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
        sizer.Add((10, 10), 0, LCEN, 3)
        sizer.Add(pan, 0, LCEN, 3)
        sizer.Add((10, 10), 0, LCEN, 3)
        sizer.Add(HLine(self, size=(550, 2)), 0, LCEN, 3)
        sizer.Add((10, 10), 0, LCEN, 3)
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
        elif isinstance(dat, dict):
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

    def read_form(self):
        "read for, returning dict of values"
        dgroup = self.controller.get_group()
        array_desc = self.array_choice.GetStringSelection()
        form_opts = {'gname': dgroup.groupname,
                     'filename': dgroup.filename,
                     'array_desc': array_desc.lower(),
                     'array_name': Array_Choices[array_desc],
                     'baseline_form': 'lorentzian',
                     'bkg_components': []}

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

        if 'bpeak_' not in self.fit_components:
            self.addModel(model='Lorentzian', prefix='bpeak_', isbkg=True)
        if 'bline_' not in self.fit_components:
            self.addModel(model='Linear', prefix='bline_', isbkg=True)

        for prefix in ('bpeak_', 'bline_'):
            cmp = self.fit_components[prefix]
            # cmp.bkgbox.SetValue(1)
            self.fill_model_params(prefix, dgroup.prepeaks.fit_details.params)

        self.fill_form(dgroup)
        self.fitmodel_btn.Enable()
        # self.fitallmodel_btn.Enable()

        i1, i2 = self.get_xranges(dgroup.energy)
        dgroup.yfit = dgroup.xfit = 0.0*dgroup.energy[i1:i2]

        # self.plot_choice.SetStringSelection(PLOT_BASELINE)
        self.onPlot(baseline_only=True)

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
        g = self.build_fitmodel(dgroup)
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

        panel = GridPanel(self.mod_nb, ncols=2, nrows=5, pad=1, itemstyle=CEN)

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
        pick2btn = Button(panel, 'Pick Values from Plotted Data', size=(200, -1),
                          action=partial(self.onPick2Points, prefix=prefix))

        # SetTip(mname,  'Label for the model component')
        SetTip(usebox,   'Use this component in fit?')
        SetTip(bkgbox,   'Label this component as "background" when plotting?')
        SetTip(delbtn,   'Delete this model component')
        SetTip(pick2btn, 'Select X range on Plot to Guess Initial Values')

        panel.Add(SLabel(label, size=(275, -1), colour='#0000AA'),
                  dcol=4,  style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(usebox, dcol=2)
        panel.Add(bkgbox, dcol=1, style=RCEN)

        panel.Add(pick2btn, dcol=2, style=wx.ALIGN_LEFT, newrow=True)
        panel.Add(pick2msg, dcol=3, style=wx.ALIGN_RIGHT)
        panel.Add(delbtn, dcol=2, style=wx.ALIGN_RIGHT)

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

        self.mod_nb.AddPage(panel, title, True)
        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))
        self.fitmodel_btn.Enable()


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


    def onLoadFitResult(self, event=None):
        dlg = wx.FileDialog(self, message="Load Saved File Model",
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
        opts = self.read_form()


        opts['group'] = opts['gname']
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
        self.build_fitmodel(dgroup)

    def onFitModel(self, event=None):
        dgroup = self.controller.get_group()
        if dgroup is None:
            return
        self.build_fitmodel(dgroup)
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
        if getattr(dgroup, 'yerr', 1.0)  == 1.0:
            if hasattr(dgroup, 'norm_std'):
                cmds.append("{group}.yerr = {group}.norm_std")
                yerr_type = 'set_yerr_array'
            elif hasattr(dgroup, 'mu_std'):
                cmds.append("{group}.yerr = {group}.mu_std/(1.e-15+{group}.edge_step)")
                yerr_type = 'set_yerr_array'
            else:
                cmds.append("{group}.yerr = 1")
        else:
            if isinstance(dgroup.yerr, np.ndarray):
                yerr_type = 'set_yerr_array'


        cmds.extend([COMMANDS[yerr_type], COMMANDS['dofit']])

        cmd = '\n'.join(cmds)
        self.larch_eval(cmd.format(group=dgroup.groupname,
                                   imin=imin, imax=imax,
                                   user_opts=repr(opts)))

        self.autosave_modelresult(self.larch_get("peakresult"))

        self.onPlot()
        self.show_subframe('prepeak_result_frame', FitResultFrame,
                                  datagroup=dgroup, peakframe=self)
        self.subframes['prepeak_result_frame'].show_results()

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
                print("Warning: cannot create XAS_Viewer user folder")
                return
        if not HAS_MODELSAVE:
            print("Warning: cannot save model results: upgrade lmfit")
            return
        if fname is None:
            fname = 'autosave.fitmodel'
        save_modelresult(result, os.path.join(confdir, fname))
