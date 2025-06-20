import time
import sys
from pathlib import Path
import numpy as np
np.seterr(all='ignore')

from functools import partial
import json

import wx
import wx.lib.scrolledpanel as scrolled

import wx.dataview as dv

from pyshortcuts import uname, gformat, fix_varname

from larch import Group, site_config
from larch.utils import mkdir
from larch.math import index_of
from lmfit import Parameter

from larch.math.fitmodels import (ConstantModel, LinearModel,
            QuadraticModel, PolynomialModel, SplineModel, SineModel,
            GaussianModel, Gaussian2dModel, LorentzianModel,
            SplitLorentzianModel, VoigtModel, PseudoVoigtModel,
            MoffatModel, Pearson4Model, Pearson7Model, StudentsTModel,
            BreitWignerModel, LognormalModel, DampedOscillatorModel,
            DampedHarmonicOscillatorModel,
            DampedHarmonicOscillatorModel, ExponentialGaussianModel,
            SkewedGaussianModel, SkewedVoigtModel,
            ThermalDistributionModel, DoniachModel, PowerLawModel,
            ExponentialModel, LinearStepModel, AtanStepModel,
            ErfStepModel, LogiStepModel, LinearRectangleModel,
            AtanRectangleModel, ErfRectangleModel, LogiRectangleModel,
            ExpressionModel)


# import lmfit.models as lm_models
from larch.io.export_modelresult import export_modelresult
from larch.io import save_groups, read_groups

from larch.wxlib import (ReportFrame, BitmapButton, FloatCtrl,
                         FloatSpin, SetTip, GridPanel, get_icon,
                         SimpleText, pack, Button, HLine, Choice,
                         Check, MenuItem, GUI_COLORS, set_color, CEN,
                         RIGHT, LEFT, FRAMESTYLE, Font, FONTSIZE,
                         FONTSIZE_FW, FileSave, FileOpen,
                         flatnotebook, Popup, EditableListBox,
                         ExceptionPopup)

from larch.wxlib.parameter import ParameterWidgets
from larch.wxlib.plotter import last_cursor_pos
from .taskpanel import TaskPanel
from .config import (CurveFit_ArrayChoices, PlotWindowChoices,
                     XRANGE_CHOICES, YERR_CHOICES)

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

MODELS = {'Constant': Group(model=ConstantModel, abbrev='const', type='other'),
          'Linear': Group(model=LinearModel, abbrev='line', type='other'),
          'Quadratic': Group(model=QuadraticModel, abbrev='quad', type='other'),
          'Polynomial': Group(model=PolynomialModel, abbrev='poly', type='other'),
          'Power Law': Group(model=PowerLawModel, abbrev='powerlaw', type='other'),
          'Exponential': Group(model=ExponentialModel, abbrev='expon', type='other'),
          'Sine':Group(model=SineModel, abbrev='sine', type='other'),
          'Gaussian': Group(model=GaussianModel, abbrev='gauss', type='peak'),
          'Lorentzian': Group(model=LorentzianModel, abbrev='loren', type='peak'),
          'Voigt': Group(model=VoigtModel, abbrev='voigt', type='peak'),
          'PseudoVoigt': Group(model=PseudoVoigtModel, abbrev='pvoigt', type='peak'),
          'Moffat': Group(model=MoffatModel, abbrev='moffat', type='peak'),
          'Pearson4': Group(model=Pearson4Model, abbrev='pearson4', type='peak'),
          'Pearson7': Group(model=Pearson7Model, abbrev='pearson7', type='peak'),
          'Students T': Group(model=StudentsTModel, abbrev='studentst', type='peak'),
          'Breit Wigner': Group(model=BreitWignerModel, abbrev='breit', type='peak'),
          'Lognormal': Group(model=LognormalModel, abbrev='lognorm', type='peak'),
          'Damped Harmonic Oscillator': Group(model=DampedHarmonicOscillatorModel,
                                          abbrev='dho', type='peak'),
          'Split Lorentzian': Group(model=SplitLorentzianModel,
                                        abbrev='splitloren', type='peak'),
          'Exponential Gaussian': Group(model=ExponentialGaussianModel,
                                        abbrev='expgauss', type='peak'),
          'Skewed Gaussian': Group(model=SkewedGaussianModel, abbrev='skewgauss', type='peak'),
          'Skewed Voigt': Group(model=SkewedVoigtModel, abbrev='skewvoigt',
                                    type='peak'),
          'Doniach': Group(model=DoniachModel, abbrev='doniach', type='peak'),

          'Linear Step': Group(model=LinearStepModel, abbrev='steplin', type='step'),
          'Arctan Step': Group(model=AtanStepModel, abbrev='stepatan', type='step'),
          'Erf Step': Group(model=ErfStepModel, abbrev='steperf', type='step'),
          'Logistic Step': Group(model=LogiStepModel, abbrev='steplog', type='step'),
          'Linear Rectangle': Group(model=LinearRectangleModel,
                                   abbrev='rectlin', type='step'),
          'Arctan Rectangle': Group(model=AtanRectangleModel,
                                          abbrev='rectatan', type='step'),
          'Erf Rectangle': Group(model=ErfRectangleModel, abbrev='recterf', type='step'),
          'Logistic Rectangle': Group(model=LogiRectangleModel, abbrev='rectlog', type='step'),
          'Spline': Group(model=SplineModel, abbrev='spline', type='special'),
          'Gaussian2d': Group(model=Gaussian2dModel, abbrev='gauss2d', type='special'),
}

# 'User Expression': Group(model=ExpressionModel, abbrev='Expression', type='special'),

MODEL_ALIASES =  {'powerlaw': 'Power Law',
                  'pseudovoigt': 'PseudoVoigt',
                  'dho': 'Damped Harmonic Oscillator',
                  'expgaussian': 'Exponential Gaussian',
                  'atan_step': 'Arctan Step',
                  'logi_step': 'Logistic Step',
                  'atan_rectangle': 'Arctan Rectangle',
                  'logi_rectangle': 'Logistic Rectangle'}

ModelChoices = {'other': ['<General Models>'],  'peaks': ['<Peak Models>']}

for name, dat in MODELS.items():
    if dat.type == 'peak':
        ModelChoices['peaks'].append(name)
    elif dat.type in ('other', 'step'):
        ModelChoices['other'].append(name)


BaselineFuncs = ['No Baseline', 'Constant', 'Linear', 'Quadratic']


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
COMMANDS['curvefit_params'] = """
if not hasattr(_main, 'curvefit_params'): curvefit_params = Parameters()
"""

COMMANDS['curvefit_prep'] = """# prepare curve-fit
if not hasattr(_main, 'curvefit_params'): curvefit_params = Parameters()
if not hasattr({group}, 'curvefit'): {group}.curvefit = group(__name__='curvefit result')
if not hasattr({group}.curvefit, 'fit_history'): {group}.curvefit.fit_history = []
{group}.curvefit.user_options = {user_opts:s}
{group}.curvefit.init_fit = curvefit_model.eval(curvefit_params, x={group}.curvefit.xdat)
{group}.curvefit.init_ycomps = curvefit_model.eval_components(params=curvefit_params, x={group}.curvefit.xdat)
"""

COMMANDS['curvefit_setup'] = """# setup curve-fit
if not hasattr({group}, 'xdat'): {group:s}.xdat = 1.0*{group}.xplot
{group:s}.xplot = 1.0*{group:s}.xdat
{group:s}.yplot = 1.0*{group:s}.{array_name:s}
curvefit_setup({group:s},y={group}.{array_name}, xmin={xmin}, xmax={xmax})
"""

COMMANDS['set_yerr_const'] = "{group}.curvefit.y_std = {group}.yerr*ones(len({group}.curvefit.ydat))"
COMMANDS['set_yerr_array'] = """
{group}.curvefit.y_std = 1.0*{group}.yerr[{imin:d}:{imax:d}]
yerr_min = 1.e-9*{group}.curvefit.ydat.mean()
{group}.curvefit.y_std[where({group}.yerr < yerr_min)] = yerr_min
"""

COMMANDS['do_curvefit'] = """# do curvefit
curvefit_result = curvefit_run({group}, curvefit_model, curvefit_params)
curvefit_result.user_options = {user_opts:s}
"""

def get_xlims(x, xmin=None, xmax=None):
    xeps = min(np.diff(x))/ 5.
    i1, i2 = 0, len(x) + 1
    if xmin is not None:
        i1 = index_of(x, xmin + xeps)
    if xmax is not None:
        i2 = index_of(x, xmax + xeps) + 1
    return i1, i2

class CurveFitResultFrame(wx.Frame):
    config_sect = 'curvefit'
    def __init__(self, parent=None, fit_frame=None, datagroup=None, **kws):
        wx.Frame.__init__(self, None, -1, title='Curve Fit Results',
                          style=FRAMESTYLE, size=(950, 700), **kws)
        self.fit_frame = fit_frame

        if datagroup is not None:
            self.datagroup = datagroup
        self.parent = parent
        self.datasets = {}
        self.form = {}
        self.larch_eval = self.fit_frame.larch_eval
        self.nfit = 0
        self.createMenus()
        self.build()

        if datagroup is None:
            symtab = self.fit_frame.larch.symtable
            xasgroups = getattr(symtab, '_xasgroups', None)
            if xasgroups is not None:
                for dname, dgroup in xasgroups.items():
                    dgroup = getattr(symtab, dgroup, None)
                    curvefit = getattr(dgroup, 'curvefit', None)
                    hist =  getattr(curvefit, 'fit_history', None)
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

        self.wids['copy_params'] = Button(panel, 'Update Model with these values',
                                          size=(250, -1), action=self.onCopyParams)

        sizer.Add(self.wids['copy_params'], (irow, 1), (1, 3), LEFT)

        pview = self.wids['params'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        pview.SetFont(self.font_fixedwidth)
        self.wids['paramsdata'] = []

        xw = (180, 140, 150, 250)
        if uname=='darwin':
            xw = (180, 110, 110, 250)
        pview.AppendTextColumn('Parameter',  width=xw[0])
        pview.AppendTextColumn('Best Value', width=xw[1])
        pview.AppendTextColumn('1-\u03c3 Uncertainty', width=xw[2])
        pview.AppendTextColumn('Info ',     width=xw[3])

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
        ret = Popup(self,
                    f"Remove fit '{result.label}' from history?\nThis cannot be undone.",
                   "Remove fit?", style=wx.YES_NO)
        if ret == wx.ID_YES:
            self.datagroup.curvefit.fit_history.pop(self.nfit)
            self.nfit = 0
            self.show_results()

    def onSaveAllStats(self, evt=None):
        "Save Parameters and Statistics to CSV"
        # get first dataset to extract fit parameter names
        fnames = self.filelist.GetItems()
        if len(fnames) == 0:
            return

        deffile = "CurveFitResults.csv"
        wcards  = 'CVS Files (*.csv)|*.csv|All files (*.*)|*.*'
        path = FileSave(self, 'Save Parameter and Statistics for Curve Fits',
                        default_file=deffile, wildcard=wcards)
        if path is None:
            return
        if Path(path).exists() and uname != 'darwin':  # darwin prompts in FileSave!
            if wx.ID_YES != Popup(self,
                                  "Overwrite existing Statistics File?",
                                  "Overwrite existing file?", style=wx.YES_NO):
                return

        curvefit_tmpl = self.datasets[fnames[0]].curvefit
        res0 = curvefit_tmpl.fit_history[0].result
        param_names = list(reversed(res0.params.keys()))
        user_opts = curvefit_tmpl.user_options
        model_desc = self.get_model_desc(res0.model).replace('\n', ' ')
        out = ['# Curve Fit Report %s' % time.ctime(),
               '# Fitted Array name: %s' %  user_opts['array_name'],
               '# Model form: %s' % model_desc,
               '# Baseline form: %s' % user_opts.get('baseline_form', 'No baseline'),
               '# Energy fit range: [%f, %f]' % (user_opts['xmin'], user_opts['xmax']),
               '#--------------------']

        labels = [('Data Set' + ' '*25)[:25], 'Group name', 'n_data',
                 'n_varys', 'chi-square', 'reduced_chi-square',
                 'akaike_info', 'bayesian_info', 'R^2']

        for pname in param_names:
            labels.append(pname)
            labels.append(pname+'_stderr')
        out.append('# %s' % (', '.join(labels)))
        for name, dgroup in self.datasets.items():
            if not hasattr(dgroup, 'curvefit'):
                continue
            try:
                cvfit = dgroup.curvefit.fit_history[0]
            except:
                continue
            result = cvfit.result
            label = dgroup.filename
            if len(label) < 25:
                label = (label + ' '*25)[:25]
            dat = [label, dgroup.groupname,
                   '%d' % result.ndata, '%d' % result.nvarys]
            for attr in ('chisqr', 'redchi', 'aic', 'bic', 'rsquared'):
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

        with open(path, 'w', encoding=sys.getdefaultencoding()) as fh:
            fh.write('\n'.join(out))

    def onSaveFitResult(self, event=None):
        deffile = self.datagroup.filename.replace('.', '_') + 'fit.modl'
        sfile = FileSave(self, 'Save Fit Model', default_file=deffile,
                           wildcard=ModelWcards)
        if sfile is not None:
            save_groups(sfile, ['#curvefit 1.0', self.get_fitresult()])

    def onExportFitResult(self, event=None):
        dgroup = self.datagroup
        deffile = dgroup.filename.replace('.', '_') + '.xdi'
        wcards = 'All files (*.*)|*.*'

        outfile = FileSave(self, 'Export Fit Result', default_file=deffile)

        cvfit = self.get_fitresult()
        result = cvfit.result
        if outfile is not None:
            i1, i2 = get_xlims(dgroup.xplot,
                               cvfit.user_options['xmin'],
                               cvfit.user_options['xmax'])
            x = dgroup.xplot[i1:i2]
            y = dgroup.yplot[i1:i2]
            yerr = None
            if hasattr(dgroup, 'y_std'):
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
        self.fit_history = getattr(self.datagroup.curvefit, 'fit_history', [])
        self.nfit = max(0, nfit)
        if self.nfit > len(self.fit_history):
            self.nfit = 0
        if len(self.fit_history) > 0:
            return self.fit_history[self.nfit]

    def onPlot(self, event=None):
        show_resid = self.wids['plot_resid'].IsChecked()
        sub_bline = self.wids['plot_bline'].IsChecked()
        win  = int(self.wids['plot_win'].GetStringSelection())
        cmd = "plot_curvefit(%s, nfit=%i, show_residual=%s, subtract_baseline=%s, win=%d)"
        cmd = cmd % (self.datagroup.groupname, self.nfit, show_resid, sub_bline, win)
        self.fit_frame.larch_eval(cmd)
        self.fit_frame.controller.set_focus(topwin=self)

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
        self.fit_frame.use_modelresult(self.get_fitresult())

    def onCopyParams(self, evt=None):
        result = self.get_fitresult()
        self.fit_frame.update_start_values(result.result.params)

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
        if datagroup is not None:
            self.datagroup = datagroup
        if larch_eval is not None:
            self.larch_eval = larch_eval

        datagroup = self.datagroup
        self.curvefit_history = getattr(self.datagroup.curvefit, 'fit_history', [])
        # cur = self.get_fitresult()
        wids = self.wids
        wids['stats'].DeleteAllItems()
        for i, res in enumerate(self.curvefit_history):
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
            show_resid= self.wids['plot_resid'].IsChecked()
            sub_bline = self.wids['plot_bline'].IsChecked()
            cmd = "plot_curvefit(%s, nfit=0, show_residual=%s, subtract_baseline=%s)"
            cmd = cmd % (datagroup.groupname, show_resid, sub_bline)

            self.fit_frame.larch_eval(cmd)
            self.fit_frame.controller.set_focus(topwin=self)

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


class ParametersModel(dv.DataViewIndexListModel):
    def __init__(self, params, selected=None):
        dv.DataViewIndexListModel.__init__(self, 0)
        self.data = []
        if selected is None:
            selected = []
        self.selected = selected

        self.params = params
        self.read_data()

    def set_data(self, params, selected=None):
        self.params = params
        if selected is not None:
            self.selected = selected
        self.read_data()

    def read_data(self):
        self.data = []
        if self.params is None:
            self.data.append(['Parameter Name', False, 'vary', '0.0'])
        else:
            for pname, par in self.params.items():
                ptype = 'vary'
                if not par.vary:
                    ptype = 'fixed'
                try:
                    value = str(par.value)
                except:
                    value = 'INVALID  '
                if par.expr is not None:
                    ptype = 'constraint'
                    value = f"{value} := {par.expr}"
                sel = pname in self.selected
                self.data.append([pname, sel, ptype, value])
        self.Reset(len(self.data))

    def select_all(self, value=True):
        self.selected = []
        for irow, row in enumerate(self.data):
            self.SetValueByRow(value, irow, 1)
            if value:
                self.selected.append(row[0])

    def select_none(self):
        self.select_all(value=False)

    def GetColumnType(self, col):
        return "bool" if col == 2 else "string"

    def GetValueByRow(self, row, col):
        return self.data[row][col]

    def SetValueByRow(self, value, row, col):
        self.data[row][col] = value
        return True

    def GetColumnCount(self):
        return len(self.data[0])

    def GetCount(self):
        return len(self.data)

    def GetAttrByRow(self, row, col, attr):
        """set row/col attributes (color, etc)"""
        ptype = self.data[row][2]
        if ptype == 'vary':
            attr.SetColour(GUI_COLORS.text)
        elif ptype == 'fixed':
            attr.SetColour(GUI_COLORS.title_blue)
        else:
            attr.SetColour(GUI_COLORS.title_red)
        return True

class EditParamsFrame(wx.Frame):
    """ edit parameters"""
    def __init__(self, parent=None, curvefit_panel=None, params=None):
        wx.Frame.__init__(self, None, -1, 'Edit CurveFit Parameters',
                          style=FRAMESTYLE, size=(550, 325))

        self.parent = parent
        self.curvefit_panel = curvefit_panel
        self.params = params
        spanel = scrolled.ScrolledPanel(self, size=(500, 275))
        spanel.SetBackgroundColour(GUI_COLORS.text_bg)

        self.font_fixedwidth = wx.Font(FONTSIZE_FW, wx.MODERN, wx.NORMAL, wx.BOLD)

        self.dvc = dv.DataViewCtrl(spanel, style=DVSTYLE)
        self.dvc.SetFont(self.font_fixedwidth)
        self.SetMinSize((500, 250))

        self.model = ParametersModel(params)
        self.dvc.AssociateModel(self.model)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.dvc, 1, LEFT|wx.ALL|wx.GROW)
        pack(spanel, sizer)

        spanel.SetupScrolling()

        toppan = GridPanel(self, ncols=4, pad=1, itemstyle=LEFT)

        bkws = dict(size=(200, -1))
        toppan.Add(Button(toppan, "Select All",    action=self.onSelAll, size=(175, -1)))
        toppan.Add(Button(toppan, "Select None",             action=self.onSelNone, size=(175, -1)))
        toppan.Add(Button(toppan, "Select Unused Variables", action=self.onSelUnused, size=(200, -1)))
        toppan.Add(Button(toppan, "Remove Selected",   action=self.onRemove, size=(175,-1)), newrow=True)
        toppan.Add(Button(toppan, "Force Refresh",     action=self.onRefresh, size=(200, -1)))
        npan = wx.Panel(toppan)
        nsiz = wx.BoxSizer(wx.HORIZONTAL)

        self.par_name = wx.TextCtrl(npan, -1, value='par_name', size=(125, -1),
                                    style=wx.TE_PROCESS_ENTER)
        self.par_expr = wx.TextCtrl(npan, -1, value='<expression or value>', size=(250, -1),
                                    style=wx.TE_PROCESS_ENTER)
        nsiz.Add(SimpleText(npan, "Add Parameter:"), 0)
        nsiz.Add(self.par_name, 0)
        nsiz.Add(self.par_expr, 1, wx.GROW|wx.ALL)
        nsiz.Add(Button(npan, label='Add', action=self.onAddParam), 0)
        pack(npan, nsiz)

        toppan.Add(npan, dcol=4, newrow=True)
        toppan.Add(HLine(toppan, size=(500, 2)), dcol=5, newrow=True)
        toppan.pack()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(toppan, 0, wx.GROW|wx.ALL, 1)
        mainsizer.Add(spanel, 1, wx.GROW|wx.ALL, 1)
        pack(self, mainsizer)

        columns = [('Parameter',   150, 'text'),
                   ('Select',       75, 'bool'),
                   ('Type',         75, 'text'),
                   ('Value',       200, 'text')]

        for icol, dat in enumerate(columns):
             label, width, dtype = dat
             method = self.dvc.AppendTextColumn
             mode = dv.DATAVIEW_CELL_EDITABLE
             if dtype == 'bool':
                 method = self.dvc.AppendToggleColumn
                 mode = dv.DATAVIEW_CELL_ACTIVATABLE
             method(label, icol, width=width, mode=mode)
             c = self.dvc.Columns[icol]
             c.Alignment = c.Renderer.Alignment = wx.ALIGN_LEFT
             c.SetSortable(False)

        self.dvc.EnsureVisible(self.model.GetItem(0))
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.Show()
        self.Raise()
        wx.CallAfter(self.onSelUnused)

    def onSelAll(self, event=None):
        self.model.select_all()
        self.model.read_data()

    def onSelNone(self, event=None):
        self.model.select_none()
        self.model.read_data()

    def onSelUnused(self, event=None):
        curr_syms = self.curvefit_panel.get_used_params()
        unused = []
        for pname, par in self.params.items():
            if pname not in curr_syms: #  and par.vary:
                unused.append(pname)
        self.model.set_data(self.params, selected=unused)

    def onRemove(self, event=None):
        out = []
        for pname, sel, ptype, val in self.model.data:
            if sel:
                out.append(pname)
        nout = len(out)

        msg = f"Remove {nout:d} Parameters? \n This is not easy to undo!"
        dlg = wx.MessageDialog(self, msg, 'Warning', wx.YES | wx.NO )
        if (wx.ID_YES == dlg.ShowModal()):
            for pname, sel, ptype, val in self.model.data:
                if sel:
                    out.append(pname)
                    if name in params:
                        params.pop(name)

            self.model.set_data(self.params)
            self.model.read_data()
            self.curvefit_panel.get_pathpage('parameters').Rebuild()
        dlg.Destroy()

    def onAddParam(self, event=None):
        par_name = self.par_name.GetValue()
        par_expr = self.par_expr.GetValue()

        try:
            val = float(par_expr)
            ptype = 'vary'
        except:
            val = par_expr
            ptype = 'expr'

        if ptype == 'vary':
            cmd = f"curvefit_params.Add({par_name}, value={val}, vary=True)"
        else:
            cmd = f"curvefit_params.Add({par_name}, expr='{val}')"

        if not self.curvefit_panel.larch_has_symbol('curvefit_params'):
            self.curvefit_panel.larch_eval(COMMANDS['curvefit_params'])
        self.curvefit_panel.larch_eval(cmd)
        self.onRefresh()

    def onRefresh(self, event=None):
        if not self.curvefit_panel.larch_has_symbol('curvefit_params'):
            self.curvefit_panel.larch_eval(COMMANDS['curvefit_params'])

        self.params = self.curvefit_panel.larch_get('curvefit_params')
        self.model.set_data(self.params)
        self.model.read_data()
        self.curvefit_panel.get_pathpage('parameters').Rebuild()

    def onClose(self, event=None):
        self.Destroy()


class CurveFitParamsPanel(wx.Panel):
    def __init__(self, parent=None, curvefit_panel=None, **kws):
        wx.Panel.__init__(self, parent, -1, size=(550, 250))
        self.curvefit_panel = curvefit_panel
        #
        if not self.curvefit_panel.larch_has_symbol('curvefit_params'):
            self.curvefit_panel.larch_eval(COMMANDS['curvefit_params'])
        params = self.curvefit_panel.larch_get('curvefit_params')

        self.parwids = {}
        self.SetFont(Font(FONTSIZE))
        spanel = scrolled.ScrolledPanel(self)
        spanel.SetSize((250, 250))
        spanel.SetMinSize((50, 50))
        panel = self.panel = GridPanel(spanel, ncols=8, nrows=30, pad=1, itemstyle=LEFT)
        panel.SetFont(Font(FONTSIZE))

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label, size=size, style=wx.ALIGN_LEFT, **kws)

        panel.Add(SLabel("CurveFit Parameters ", colour=GUI_COLORS.title_blue, size=(200, -1)), dcol=2)
        panel.Add(Button(panel, 'Edit Parameters', action=self.onEditParams),  dcol=2)
        panel.Add(Button(panel, 'Force Refresh', action=self.Rebuild),         dcol=3)

        panel.Add(SLabel("Parameter "), style=wx.ALIGN_LEFT,  newrow=True)
        panel.AddMany((SLabel(" Value"), SLabel(" Type"), SLabel(' Bounds'),
                       SLabel("  Min", size=(60, -1)),
                       SLabel("  Max", size=(60, -1)),
                       SLabel(" Expression")))

        self.update()
        panel.pack()
        ssizer = wx.BoxSizer(wx.VERTICAL)
        ssizer.Add(panel, 1,  wx.GROW|wx.ALL, 2)
        pack(spanel, ssizer)

        spanel.SetupScrolling()
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(spanel, 1, wx.GROW|wx.ALL, 2)
        pack(self, mainsizer)

    def Rebuild(self, event=None):
        for pname, parwid in self.parwids.items():
            for x in parwid.widgets:
                x.Destroy()
        self.panel.irow = 1
        self.parwids = {}
        self.update()

    def set_init_values(self, params):
        for pname, par in params.items():
            if pname in self.parwids and par.vary:
                stderr = getattr(par, 'stderr', 0.001)
                try:
                    prec = max(1, min(8, round(2-math.log10(stderr))))
                except:
                    prec = 5
                self.parwids[pname].value.SetValue(("%%.%.df" % prec) % par.value)

    def update(self):
        if not self.curvefit_panel.larch_has_symbol('curvefit_params'):
            self.curvefit_panel.larch_eval(COMMANDS['curvefit_params'])
        params = self.curvefit_panel.larch_get('curvefit_params')
        for pname, par in params.items():
            if pname not in self.parwids:
                pwids = ParameterWidgets(self.panel, par, name_size=120,
                                         expr_size=200,   float_size=85,
                                         with_skip=False,
                                         widgets=('name', 'value','minval', 'maxval',
                                                  'vary', 'expr'))

                self.parwids[pname] = pwids
                self.panel.Add(pwids.name, newrow=True)
                self.panel.AddMany((pwids.value, pwids.vary, pwids.bounds,
                                    pwids.minval, pwids.maxval, pwids.expr))
                self.panel.pack()

            pwids = self.parwids[pname]
            varstr = 'vary' if par.vary else 'fix'
            if par.expr is not None:
                varstr = 'constrain'
                pwids.expr.SetValue(par.expr)
            pwids.vary.SetStringSelection(varstr)
            pwids.value.SetValue(par.value)
            pwids.minval.SetValue(par.min)
            pwids.maxval.SetValue(par.max)
            pwids.onVaryChoice()
        self.panel.Update()

    def onEditParams(self, event=None):
        params = self.curvefit_panel.larch_get('curvefit_params')
        self.curvefit_panel.show_subframe('edit_params',
                                          EditParamsFrame,
                                          params=params,
                                          curvefit_panel=self.curvefit_panel)

    def RemoveParams(self, event=None, name=None):
        if name is None:
            return
        params = self.curvefit_panel.larch_get('curvefit_params')
        if name in params:
            params.pop(name)
        if name in self.parwids:
            pwids = self.parwids.pop(name)
            pwids.name.Destroy()
            pwids.value.Destroy()
            pwids.vary.Destroy()
            pwids.bounds.Destroy()
            pwids.minval.Destroy()
            pwids.maxval.Destroy()
            pwids.expr.Destroy()
            pwids.remover.Destroy()

    def generate_params(self, event=None):
        s = []
        s.append("curvefit_params = Parameters()")
        for name, pwids in self.parwids.items():
            param = pwids.param
            args = [f'{param.value}']
            minval = pwids.minval.GetValue()
            if np.isfinite(minval):
                args.append(f'min={minval}')
            maxval = pwids.maxval.GetValue()
            if np.isfinite(maxval):
                args.append(f'max={maxval}')

            varstr = pwids.vary.GetStringSelection()
            if param.expr is not None and varstr == 'constrain':
                args.append(f"expr='{param.expr}'")
            elif varstr == 'vary':
                args.append(f'vary=True')
            else:
                args.append(f'vary=False')
            args = ', '.join(args)
            cmd = f'curvefit_params.add(d{name}, {args})'
            s.append(cmd)
        return s

    def onPanelExposed(self, event=None):
        self.update()

    def onPanelHidden(self, event=None):
        try:
            self.update_components()
        except:
            pass

    def update_components(self):
        """ updates the component parameter widgets"""
        params = self.curvefit_panel.larch_get('curvefit_params')
        fitcomps = self.curvefit_panel.fit_components
        for pname, pwids in self.parwids.items():
            pexpr = pwids.expr.GetValue()
            if pexpr is None:
                pexpr = ''
            varstr = pwids.vary.GetStringSelection()
            for comp in fitcomps.values():
                for cname, cwids in comp.parwids.items():
                    if cname == pname:
                        cwids.expr.SetValue(pexpr)
                        cwids.value.SetValue(pwids.value.GetValue())
                        cwids.minval.SetValue(pwids.minval.GetValue())
                        cwids.maxval.SetValue(pwids.maxval.GetValue())
                        cwids.vary.SetStringSelection(varstr)




class CurveFitPanel(TaskPanel):
    def __init__(self, parent=None, controller=None, **kws):
        self.fit_components = {}
        self.params_panel = None
        TaskPanel.__init__(self, parent, controller, panel='curvefit', **kws)
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
            self.fill_form(dgroup)
        except:
            pass # print(" Cannot Fill curvefit panel from group ")

        cvfit = getattr(self.larch.symtable, 'curvefit_result', None)
        if cvfit is not None:
            self.showresults_btn.Enable()
            self.use_modelresult(cvfit)

    def onModelPanelExposed(self, event=None, **kws):
        if self.mod_nb is None:
            return
        oldpage = self.mod_nb.GetPage(event.GetOldSelection())
        newpage = self.mod_nb.GetPage(event.GetSelection())
        def noop():
            pass

        getattr(oldpage, 'onPanelHidden', noop)()
        getattr(newpage, 'onPanelExposed', noop)()

#         if callable(on_hide):
#             on_hide()
#
#         # self.build_fitmodel()
#
#         if callable(on_expose):
#             on_expose()

    def build_display(self):
        pan = self.panel # = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LEFT)

        self.wids = {}

        # xrange row
        xrpanel = wx.Panel(pan)
        xrsizer = wx.BoxSizer(wx.HORIZONTAL)
        fsopts = dict(parent=xrpanel, digits=2, increment=1,
                      size=(125, -1), with_pin=True)

        curvefit_xmin  = self.add_floatspin('curvefit_xmin',  value=-1, **fsopts)
        curvefit_xmax  = self.add_floatspin('curvefit_xmax',  value=+1, **fsopts)

        self.xrange_choice = Choice(xrpanel, size=(150, -1),
                                   choices=XRANGE_CHOICES,
                                   action=self.onXrangeChoice)

        self.wids['show_fitrange']  = Check(xrpanel, label='show?', default=True,
                                           size=(75, -1),  action=self.onPlot)

        xrsizer.Add(self.xrange_choice, 0)
        xrsizer.Add(SimpleText(xrpanel, ' X min:'), 0)
        xrsizer.Add(curvefit_xmin, 0)
        xrsizer.Add(SimpleText(xrpanel, ' X max: '), 0)
        xrsizer.Add(curvefit_xmax, 0)
        xrsizer.Add(self.wids['show_fitrange'], 0)
        pack(xrpanel, xrsizer)

        self.wids['curvefit_xmin'].Disable()
        self.wids['curvefit_xmax'].Disable()
        self.xrange_choice.SetSelection(0)

        # yerror row
        yerrpanel = wx.Panel(pan)
        yerrsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.wids['yerr_choice'] = Choice(yerrpanel, choices=YERR_CHOICES, default=0,
                                          action=self.onYerrChoice, size=(150, -1))
        self.wids['yerr_array'] = Choice(yerrpanel, choices=['-'],
                                           action=self.onYerrChoice, size=(225, -1))
        self.wids['yerr_array'].Disable()
        self.wids['yerr_value'] = FloatCtrl(yerrpanel, value=1.0, minval=0, precision=5, size=(75, -1))

        yerrsizer.Add(self.wids['yerr_choice'], 0)
        yerrsizer.Add(SimpleText(yerrpanel, ' Value: '), 0)
        yerrsizer.Add(self.wids['yerr_value'], 0)
        yerrsizer.Add(SimpleText(yerrpanel, 'Array Name: '), 0)
        yerrsizer.Add(self.wids['yerr_array'], 0)

        pack(yerrpanel, yerrsizer)

        self.loadresults_btn = Button(pan, 'Load Fit Result',
                                      action=self.onLoadFitResult, size=(175, -1))
        self.showresults_btn = Button(pan, 'Show Fit Results',
                                      action=self.onShowResults, size=(175, -1))
        self.showresults_btn.Disable()

        self.plotmodel_btn = Button(pan,
                                    'Plot Current Model',
                                    action=self.onPlotModel,  size=(175, -1))
        self.fitmodel_btn = Button(pan, 'Fit Current Group',
                                   action=self.onFitModel,  size=(175, -1))
        self.fitmodel_btn.Disable()
        self.fitselected_btn = Button(pan, 'Fit Selected Groups',
                                      action=self.onFitSelected,  size=(175, -1))
        self.fitselected_btn.Disable()
        self.fitmodel_btn.Disable()

        self.array_choice = Choice(pan, size=(150, -1),
                                   choices=list(CurveFit_ArrayChoices.keys()))
        self.array_choice.SetSelection(0)

        models_peaks = Choice(pan, size=(200, -1),
                              choices=ModelChoices['peaks'],
                              action=self.addModel)

        models_other = Choice(pan, size=(200, -1),
                              choices=ModelChoices['other'],
                              action=self.addModel)

        self.models_peaks = models_peaks
        self.models_other = models_other
        self.message = SimpleText(pan, '')


        opts = dict(default=False, size=(200, -1), action=self.onPlot)

        def add_text(text, dcol=1, newrow=True):
            pan.Add(SimpleText(pan, text), dcol=dcol, newrow=newrow)

        pan.Add(SimpleText(pan, 'Curve-Fitting',
                           size=(350, -1), **self.titleopts), style=LEFT, dcol=5)

        add_text(' Y Array to fit: ')
        pan.Add(self.array_choice, dcol=3)

        add_text(' Y uncertainty: ')
        pan.Add(yerrpanel, dcol=5)

        add_text( ' X range: ')
        pan.Add(xrpanel, dcol=5)

        pan.Add((10, 10), newrow=True)
        pan.Add(self.loadresults_btn)
        pan.Add(self.showresults_btn)

        pan.Add(HLine(pan, size=(600, 2)), dcol=6, newrow=True)

        #  add model
        ts = wx.BoxSizer(wx.HORIZONTAL)
        ts.Add(models_peaks)
        ts.Add(models_other)

        pan.Add(SimpleText(pan, 'Add Component: '), newrow=True)
        pan.Add(ts, dcol=4)
        pan.Add(self.plotmodel_btn)


        pan.Add(SimpleText(pan, 'Messages: '), newrow=True)
        pan.Add(self.message, dcol=4)
        pan.Add(self.fitmodel_btn)
        pan.Add(SimpleText(pan, '  '), dcol=5, newrow=True)
        pan.Add(self.fitselected_btn)

        pan.Add(HLine(pan, size=(600, 2)), dcol=6, newrow=True)
        pan.pack()

        self.mod_nb = flatnotebook(self, {}, on_change=self.onModelPanelExposed)

        self.params_panel = CurveFitParamsPanel(parent=self.mod_nb,
                                              curvefit_panel=self)

        self.mod_nb.AddPage(self.params_panel, 'Parameters', True)
        self.mod_nb

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((5, 5), 0, LEFT, 3)
        sizer.Add(pan, 0, LEFT, 3)
        sizer.Add((5, 5), 0, LEFT, 3)
        sizer.Add(self.mod_nb,  1, LEFT|wx.GROW, 5)

        pack(self, sizer)

    def get_config(self, dgroup=None):
        """get processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()

        conf = getattr(dgroup, 'curvefit_config', {})
        if 'e0' not in conf:
            conf = self.get_defaultconfig()
            conf['e0'] = getattr(dgroup, 'e0', -1)

        dgroup.curvefit_config = conf
        if not hasattr(dgroup, 'curvefit'):
            dgroup.curvefit = Group()

        return conf

    def onYerrChoice(self, event=None):
        yerr_type = self.wids['yerr_choice'].GetSelection() # Constant, Sqrt, Array
        self.wids['yerr_array'].Enable(yerr_type==2)
        self.wids['yerr_value'].Enable(yerr_type==0)
        if yerr_type == 2:
            dgroup = self.controller.get_group()
            xarr = getattr(dgroup, 'x', None)
            if xarr is None:
                return
            npts = len(xarr)

            cur_list = self.wids['yerr_array'].GetStrings()
            cur_sel = self.wids['yerr_array'].GetStringSelection()

            arrlist  = []
            needs_update = False
            for attr in dir(dgroup):
                obj = getattr(dgroup, attr, None)
                if isinstance(obj, np.ndarray) and len(obj) == npts:
                    if attr not in ('x', 'y'):
                        arrlist.append(attr)
                        if attr not in cur_list:
                            needs_update = True
            if needs_update:
                self.wids['yerr_array'].Clear()
                self.wids['yerr_array'].SetChoices(arrlist)
                try:
                    self.wids['yerr_array'].SetStringSelection(cur_sel)
                except:
                    pass

    def onXrangeChoice(self, evt=None):
        sel = self.xrange_choice.GetSelection()
        self.wids['curvefit_xmin'].Enable(sel==1)
        self.wids['curvefit_xmax'].Enable(sel==1)
        if sel == 1:
            dgroup = self.controller.get_group()
            xmin = dgroup.xdat.min()
            xmax = dgroup.xdat.max()
            self.wids['curvefit_xmin'].SetValue(xmin)
            self.wids['curvefit_xmax'].SetValue(xmax)

    def fill_form(self, dat):
        if isinstance(dat, Group):
            xmin  = dat.xdat.xmin()
            xmax  = dat.xdat.xmax()

            if hasattr(dat, 'curvefit'):
                xmin = dat.curvefit.xmin
                xmax = dat.curvefit.xmax

            self.wids['curvefit_xmin'].SetValue(xmin)
            self.wids['curvefit_xmax'].SetValue(xmax)
        elif isinstance(dat, dict):
            self.wids['curvefit_xmin'].SetValue(dat['xmin'])
            self.wids['curvefit_xmax'].SetValue(dat['xmax'])


        self.array_choice.SetStringSelection(dat['array_desc'])
        self.wids['show_fitrange'].Enable(dat['show_fitrange'])

    def read_form(self):
        "read for, returning dict of values"
        dgroup = self.controller.get_group()

        array_desc = self.array_choice.GetStringSelection()
        form_opts = {'gname': dgroup.groupname,
                     'filename': dgroup.filename,
                     'array_desc': array_desc.lower(),
                     'array_name': CurveFit_ArrayChoices[array_desc],
                     'bkg_components': []}
        xrange_sel = self.xrange_choice.GetSelection()
        if xrange_sel == 0:
            form_opts['xmin'] = dgroup.xdat.min()
            form_opts['xmax'] = dgroup.xdat.max()
        else:
            form_opts['xmin'] = self.wids['curvefit_xmin'].GetValue()
            form_opts['xmax'] = self.wids['curvefit_xmax'].GetValue()
        form_opts['show_fitrange'] = self.wids['show_fitrange'].IsChecked()
        return form_opts

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
        opts = self.read_form()
        dgroup = self.controller.get_group()
        opts['group'] = opts['gname']
        self.larch_eval(COMMANDS['curvefit_setup'].format(**opts))

        curvefit_opts = dict(array=opts['array_name'], xmin=opts['xmin'],
                            xmax=opts['xmax'])
        dgroup.journal.add_ifnew('curvefit_setup', curvefit_opts)

        cmd = "plot_curvefit"
        args = ['{gname}', "show_init=%s" % (show_init)]
        cmd = "%s(%s)" % (cmd, ', '.join(args))
        self.larch_eval(cmd.format(**opts))
        self.controller.set_focus()

    def addModel(self, event=None, model=None, prefix=None, isbkg=False, opts=None):
        if model is None and event is not None:
            model = event.GetString()
        if model is None or model.startswith('<'):
            return

        if not self.larch_has_symbol('curvefit_params'):
            self.larch_eval(COMMANDS['curvefit_params'])
        params = self.larch_get('curvefit_params')

        self.models_peaks.SetSelection(0)
        self.models_other.SetSelection(0)

        mpanel = ModelComponentPanel(self, model)
        self.fit_components[mpanel.prefix] = mpanel
        self.mod_nb.AddPage(mpanel, mpanel.title, True)
        self.fitmodel_btn.Enable()
        self.fitselected_btn.Enable()


    def onDeleteComponent(self, evt=None, prefix=None):
        fcomp = self.fit_components.get(prefix, None)
        if fcomp is None:
            return

        for i in range(self.mod_nb.GetPageCount()):
            if fcomp.title == self.mod_nb.GetPageText(i):
                self.mod_nb.DeletePage(i)

        for attr in dir(fcomp):
            if attr is not None:
                try:
                    setattr(fcomp, attr, None)
                except:
                    pass

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
            msg = self.pick2msg.SetLabel(" ")
            plotframe.cursor_hist = []
            self.pick2_timer.Stop()
            return

        if len(curhist) < 2:
            self.pick2msg.SetLabel("%i/2" % (len(curhist)))
            return

        self.pick2msg.SetLabel("done.")
        self.pick2_timer.Stop()

        # guess param values
        xcur = (curhist[0][0], curhist[1][0])
        xmin, xmax = min(xcur), max(xcur)

        dgroup = getattr(self.larch.symtable, self.controller.groupname)
        i0 = max(0, index_of(dgroup.xplot, xmin) - 2)
        i1 = min(len(dgroup.xplot), index_of(dgroup.xplot, xmax) + 2)
        x, y = dgroup.xplot[i0:i1+1], dgroup.yplot[i0:i1+1]

        mod = self.comp_panel.mclass(prefix=self.comp_panel.prefix)
        parwids = self.comp_panel.parwids
        try:
            guesses = mod.guess(y, x=x)
        except:
            return

        c_params = self.larch_get('curvefit_params')
        for name, param in guesses.items():
#             if 'amplitude' in name:
#                 param.value *= 1.5
#             elif 'sigma' in name:
#                 param.value *= 0.75
            if name in parwids:
                parwids[name].value.SetValue(param.value)
            c_params[name] = param

        dgroup._tmp = mod.eval(guesses, x=dgroup.xplot)
        plotframe = self.controller.get_display(win=1)
        plotframe.panel.conf.set_theme()

        plotframe.cursor_hist = []
        plotframe.oplot(dgroup.xplot, dgroup._tmp)
        self.pick2erase_panel = plotframe.panel
        self.pick2erase_timer.Start(60000)


    def onPick2Points(self, evt=None, prefix=None):
        cpanel = self.fit_components.get(prefix, None)
        if cpanel is None:
            return

        plotframe = self.controller.get_display(win=1)
        plotframe.Raise()

        plotframe.cursor_hist = []
        self.pick2msg = cpanel.pick2msg
        self.comp_panel = cpanel
        self.pick2_npts = 0

        if self.pick2msg is not None:
            self.pick2msg.SetLabel("0/2")

        self.pick2_t0 = time.time()
        self.pick2_timer.Start(1000)


    def onLoadFitResult(self, event=None):
        rfile = FileOpen(self, "Load Saved Pre-edge Model",
                         wildcard=ModelWcards)
        if rfile is None:
            return

        self.larch_eval(f"# curvefit_model = read_groups('{rfile}')[1]")
        dat = read_groups(str(rfile))
        if len(dat) != 2 or not dat[0].startswith('#curvefit'):
            Popup(self, f" '{rfile}' is not a valid Curvefit Model file",
                  "Invalid file")

        self.use_modelresult(dat[1])

    def use_modelresult(self, cvfit):
        for prefix in list(self.fit_components.keys()):
            self.onDeleteComponent(prefix=prefix)

        result = cvfit.result
        bkg_comps = cvfit.user_options['bkg_components']

        for comp in result.model.components:
            isbkg = comp.prefix in bkg_comps
            # print("USE MODEL ", comp, comp.func, comp.prefix, comp.opts)
            self.addModel(model=comp.func.__name__,
                          prefix=comp.prefix, isbkg=isbkg,
                          opts=comp.opts)

        for comp in result.model.components:
            parwids = self.fit_components[comp.prefix].parwids
            for pname, par in result.params.items():
                if pname in parwids:
                    wids = parwids[pname]
                    wids.value.SetValue(result.init_values.get(pname, par.value))
                    varstr = 'vary' if par.vary else 'fix'
                    if par.expr is not None:   varstr = 'constrain'
                    if wids.vary is not None:  wids.vary.SetStringSelection(varstr)
                    if wids.minval is not None: wids.minval.SetValue(par.min)
                    if wids.maxval is not None: wids.maxval.SetValue(par.max)

        self.fill_form(cvfit.user_options)

    def get_xranges(self, x):
        opts = self.read_form()
        dgroup = self.controller.get_group()
        dx = min(np.diff(dgroup.xdat)) / 5.

        i1 = index_of(x, opts['xmin'] + dx)
        i2 = index_of(x, opts['xmax'] + dx) + 1
        return i1, i2

    def set_yerror(self):
        """set yerr array based on Panel selections"""
        dgroup = self.controller.get_group()
        if dgroup is None:
            return 1.0
        gname  = dgroup.groupname
        yerr_type = self.wids['yerr_choice'].GetSelection() # Constant, Sqrt, Array
        cmd = None

        # Need IMIN / IMAX
        if yerr_type == 0: # constant
            val = self.wids['yerr_value'].GetValue()
            cmd = f"{gname}.y_std = {val}*ones(len({gname}.curvefit.ydat))"
        elif yerr_type == 1: # sqrt
            cmd = f"{gname}.y_std = sqrt(abs({gname}.ydat))"
        elif yerr_type == 2: # array name
            yarrname = self.wids['yerr_array'].GetStringSelection()
            if yename != 'yerr':
                cmd = f"{gname}.yerr = {gname}.{yarrname}*1.0"
        if cmd is not None:
            self.larch_eval(cmd)

    def build_fitmodel(self, groupname=None):
        """ use fit components to build model"""
        comps = []
        cmds = ["# setup curve-fit parameters", "curvefit_params = Parameters()"]
        modcmds = ["## define curve-fit model"]
        modop = " ="
        opts = self.read_form()
        if groupname is None:
            groupname = opts['gname']

        opts['group'] = groupname
        dgroup = self.controller.get_group(groupname)
        self.larch_eval(COMMANDS['curvefit_setup'].format(**opts))
        self.set_yerror()

        cur_mod_panel = self.mod_nb.GetCurrentPage()
        if cur_mod_panel == self.params_panel:
            self.params_panel.update_components()

        curvefit_opts = dict(array=opts['array_name'],
                         xmin=opts['xmin'], xmax=opts['xmax'])
        dgroup.journal.add_ifnew('curvefit_setup', curvefit_opts)

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

                    cmds.append("curvefit_params.add(%s)" % (', '.join(pargs)))
                    if this.name.endswith('_center'):
                        _cen = this.name
                    elif parwids.param.name.endswith('_amplitude'):
                        _amp = this.name
                mname = comp.mclass.__name__
                modcmds.append(f"curvefit_model {modop} {mname}(prefix='{comp.prefix}')")
                modop = "+="
                if not comp.bkgbox.IsChecked() and _cen is not None and _amp is not None:
                    comps.append((_amp, _cen))

        cmds.extend(modcmds)
        cmds.append(COMMANDS['curvefit_prep'].format(group=dgroup.groupname,
                                               user_opts=repr(opts)))

        self.larch_eval("\n".join(cmds))

    def onFitSelected(self, event=None):
        opts = self.read_form()

        selected_groups = self.controller.filelist.GetCheckedStrings()
        groups = [self.controller.file_groups[cn] for cn in selected_groups]
        ngroups = len(groups)
        for igroup, gname in enumerate(groups):
            dgroup = self.controller.get_group(gname)
            # print("Fitting group ", gname)
            self.build_fitmodel(gname)

            opts['group'] = opts['gname']
            self.larch_eval(COMMANDS['curvefit_setup'].format(**opts))

            curvefit_opts = dict(array=opts['array_name'], xmin=opts['xmin'],
                               xmax=opts['xmax'])
            dgroup.journal.add_ifnew('curvefit_setup', curvefit_opts)
            curvefit = dgroup.curvefit

            # add bkg_component to saved user options
            bkg_comps = []
            for label, comp in self.fit_components.items():
                if comp.bkgbox.IsChecked():
                    bkg_comps.append(label)
            opts['bkg_components'] = bkg_comps

            imin, imax = self.get_xranges(dgroup.xplot)
            cmds = [f"## do curvefit for group {gname} / {dgroup.filename}"]

            cmds.extend([COMMANDS['do_curvefit']])
            cmd = '\n'.join(cmds)
            self.larch_eval(cmd.format(group=dgroup.groupname,
                                       imin=imin, imax=imax,
                                       user_opts=repr(opts)))

            cvfit = self.larch_get("curvefit_result")
            jnl = {'label': cvfit.label, 'var_names': cvfit.result.var_names,
                   'model': repr(cvfit.result.model)}
            jnl.update(cvfit.user_options)
            dgroup.journal.add('curvefit', jnl)
            if igroup == 0:
                self.autosave_modelresult(cvfit)
            self.showresults_btn.Enable()
            # print("Did fit for grouop ", dgroup, opts)
            self.subframes['curvefit_result'].add_results(dgroup, form=opts,
                                                         larch_eval=self.larch_eval)

    def onFitModel(self, event=None):
        dgroup = self.controller.get_group()
        if dgroup is None:
            return
        self.build_fitmodel(dgroup.groupname)
        opts = self.read_form()

        dgroup = self.controller.get_group()
        opts['group'] = opts['gname']
        self.larch_eval(COMMANDS['curvefit_setup'].format(**opts))

        curvefit_opts = dict(array=opts['array_name'], xmin=opts['xmin'],
                             xmax=opts['xmax'])
        dgroup.journal.add_ifnew('curvefit_setup', curvefit_opts)
        curvefit = dgroup.curvefit

        # add bkg_component to saved user options
        bkg_comps = []
        for label, comp in self.fit_components.items():
            if comp.bkgbox.IsChecked():
                bkg_comps.append(label)
        opts['bkg_components'] = bkg_comps

        imin, imax = self.get_xranges(dgroup.xplot)
        self.set_yerror()
        cmds = ["## do curve fit: "]
        cmds.extend([COMMANDS['do_curvefit']])
        cmd = '\n'.join(cmds)
        self.larch_eval(cmd.format(group=dgroup.groupname, imin=imin, imax=imax,
                                  user_opts=repr(opts)))

        # journal about curvefit_result
        cvfit = self.larch_get("curvefit_result")
        jnl = {'label': cvfit.label, 'var_names': cvfit.result.var_names,
               'model': repr(cvfit.result.model)}
        jnl.update(cvfit.user_options)
        dgroup.journal.add('curvefit', jnl)

        self.autosave_modelresult(cvfit)
        self.onPlot()
        self.showresults_btn.Enable()

        self.show_subframe('curvefit_result', CurveFitResultFrame, fit_frame=self)
        self.subframes['curvefit_result'].add_results(dgroup, form=opts,
                                                      larch_eval=self.larch_eval)

    def onShowResults(self, event=None):
        self.show_subframe('curvefit_result', CurveFitResultFrame, fit_frame=self)


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
            fname = 'autosave_fit.modl'
        save_groups(Path(confdir, fname).as_posix(), ['#curvefit 1.0', result])


class ModelComponentPanel(GridPanel):
    def __init__(self, parent, modelname, prefix=None, isbkg=False,
                ncols=7, nrows=6, pad=1):
        GridPanel.__init__(self, parent, ncols=ncols, nrows=nrows, pad=pad, itemstyle=CEN)

        fit_comps = parent.fit_components

        if modelname not in MODELS:
            mname_alt = modelname.replace('_', ' ').replace('-', ' ').title()
            if mname_alt in MODELS:
                modelname = mname_alt
            elif modelname.lower() in MODEL_ALIASES:
                modelname = MODEL_ALIASES[modelname.lower()]

        modgroup = MODELS[modelname]
        # print('add Model : ', modelname, modgroup)
        if prefix is None:
            curmodels = [f"{modgroup.abbrev}{i+1}_" for i in range(1+len(fit_comps))]
            # print("Current Models ", curmodels, fit_comps.keys())
            for comp in fit_comps:
                if comp in curmodels:
                    curmodels.remove(comp)
            prefix = curmodels[0]

        self.parent = parent
        self.prefix = prefix

        self.title = prefix[:-1]
        self.isbkg = isbkg
        self.label = f"{modelname}(prefix='{prefix}')"
        self.mclass = modgroup.model

        self.build()

    def build(self):
        self.SetFont(Font(FONTSIZE))
        parent = self.parent
        prefix = self.prefix


        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(self, label, size=size, style=LEFT, **kws)
        usebox = Check(self, default=True, label='Use in Fit?', size=(125, -1))
        bkgbox = Check(self, default=self.isbkg, label='Is Baseline?', size=(125, -1))

        delbtn = Button(self, 'Delete This Component', size=(200, -1),
                        action=partial(parent.onDeleteComponent, prefix=prefix))

        pick2msg = SimpleText(self, "    ", size=(125, -1))
        pick2btn = Button(self, 'Pick Values from Plot', size=(200, -1),
                          action=partial(parent.onPick2Points, prefix=prefix))

        # SetTip(mname,  'Label for the model component')
        SetTip(usebox,   'Use this component in fit?')
        SetTip(bkgbox,   'Label this component as "background" when plotting?')
        SetTip(delbtn,   'Delete this model component')
        SetTip(pick2btn, 'Select X range on Plot to Guess Initial Values')

        self.Add(SLabel(self.label, size=(275, -1), colour=GUI_COLORS.title_blue),
                  dcol=4,  style=wx.ALIGN_LEFT, newrow=True)
        self.Add(usebox, dcol=2)
        self.Add(bkgbox, dcol=1, style=RIGHT)

        self.Add(pick2btn, dcol=2, style=wx.ALIGN_LEFT, newrow=True)
        self.Add(pick2msg, dcol=3, style=wx.ALIGN_RIGHT)
        self.Add(delbtn, dcol=2, style=wx.ALIGN_RIGHT)

        self.Add(SLabel("Parameter "), style=wx.ALIGN_LEFT,  newrow=True)
        self.AddMany((SLabel(" Value"), SLabel(" Type"), SLabel(' Bounds'),
                       SLabel("  Min", size=(60, -1)),
                       SLabel("  Max", size=(60, -1)),  SLabel(" Expression")))

        parwids = {}
        model = self.mclass(prefix=prefix)
        parnames = sorted(model.param_names)
        for hint in model.param_hints:
            pname = "%s%s" % (prefix, hint)
            if pname not in parnames:
                parnames.append(pname)

        c_params = self.parent.larch_get('curvefit_params')
        for pname in parnames:
            sname = pname[len(prefix):]
            hints = model.param_hints.get(sname, {})

            par = Parameter(name=pname, value=0, vary=True)
            if 'min' in hints:
                par.min = hints['min']
            if 'max' in hints:
                par.max = hints['max']
            if 'value' in hints:
                par.value = hints['value']
            if 'expr' in hints:
                par.expr = hints['expr']

            pwids = ParameterWidgets(self, par, name_size=110,
                                     expr_size=200,
                                     float_size=80, prefix=prefix,
                                     widgets=('name', 'value',  'minval',
                                              'maxval', 'vary', 'expr'))
            parwids[par.name] = pwids
            self.Add(pwids.name, newrow=True)

            self.AddMany((pwids.value, pwids.vary, pwids.bounds,
                           pwids.minval, pwids.maxval, pwids.expr))
            c_params[pname] = par

        for sname, hint in model.param_hints.items():
            pname = "%s%s" % (prefix, sname)
            if 'expr' in hint and pname not in parnames:
                par = Parameter(name=pname, value=0, expr=hint['expr'])
                pwids = ParameterWidgets(self, par, name_size=110,
                                         expr_size=400,
                                         float_size=80, prefix=prefix,
                                         widgets=('name', 'value', 'expr'))
                parwids[par.name] = pwids
                self.Add(pwids.name, newrow=True)
                self.Add(pwids.value)
                self.Add(pwids.expr, dcol=5, style=wx.ALIGN_RIGHT)
                pwids.value.Disable()
                # c_params[pname] = par
        self.parwids = parwids
        self.pick2msg = pick2msg
        self.bkgbox = bkgbox
        self.usebox = usebox

        self.pack()

        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))

    def onPanelExposed(self, event=None):
        "set widget values from params"
        params = self.parent.larch_get('curvefit_params')
        for pname, par in params.items():
            if pname in self.parwids:
                pwids = self.parwids[pname]
                varstr = 'vary' if par.vary else 'fix'
                if par.expr is not None:
                    varstr = 'constrain'
                    pwids.expr.SetValue(par.expr)
                pwids.vary.SetStringSelection(varstr)
                pwids.value.SetValue(par.value)
                pwids.minval.SetValue(par.min)
                pwids.maxval.SetValue(par.max)
                pwids.onVaryChoice()

    def onPanelHidden(self, event=None):
        "set params from widget values"
        params = self.parent.larch_get('curvefit_params')
        for pname, pwids in self.parwids.items():
            par = params.get(pname, None)
            if par is None:
                continue
            varstr = pwids.vary.GetStringSelection()
            par.vary = (varstr == 'vary')
            par.min = pwids.minval.GetValue()
            par.max = pwids.maxval.GetValue()
            if varstr.startswith('cons'):
                par.expr = pwids.expr.GetValue()
            else:
                par.value = pwids.value.GetValue()
