import time
import numpy as np
np.seterr(all='ignore')

from functools import partial
from collections import OrderedDict
import json

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as flat_nb

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check,
                     MenuItem, GUIColors, GridPanel, CEN, RCEN, LCEN,
                     FRAMESTYLE, Font, FileSave)

import lmfit.models as lm_models
from lmfit import Parameter, Parameters

from larch import Group
from larch.utils.jsonutils import encode4js, decode4js

from larch.wxlib import (ReportFrame, BitmapButton, ParameterWidgets,
                         FloatCtrl, SetTip)

from larch.fitting import fit_report
from larch_plugins.std import group2dict
from larch_plugins.math import index_of
from larch_plugins.wx.icons import get_icon
from larch_plugins.wx.parameter import ParameterPanel

LCEN = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
CEN |=  wx.ALL

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_NO_NAV_BUTTONS

StepChoices = ('<Add Step Model>', 'Linear', 'Arctan', 'ErrorFunction',
               'Logistic')

PeakChoices = ('<Add Peak Model>', 'Gaussian', 'Lorentzian', 'Voigt',
               'PseudoVoigt', 'Pearson7', 'StudentsT', 'SkewedGaussian',
               'Moffat', 'BreitWigner', 'Donaich', 'Lognormal')

ModelChoices = ('<Add Other Model>', 'Constant', 'Linear', 'Quadratic',
               'Exponential', 'PowerLaw', 'Rectangle', 'DampedOscillator')

FITCONF_WILDCARDS = 'Fit Configs (*.fitconf)|*.fitconf|All files (*.*)|*.*'

class AllParamsPanel(wx.Panel):
    """Panel containing simple list of all Parameters"""
    def __init__(self, parent=None, controller=None, **kws):
        wx.Panel.__init__(self, parent, -1, **kws)
        self.parent = parent
        self.parameters = OrderedDict()

    def addParameter(self, param):
        """add a parameter"""
        print( "add parameter ", param)

    def delParameter(self, param):
        """delete a parameter"""
        print( "del parameter ", param)


class XYFitPanel(wx.Panel):
    def __init__(self, parent=None, controller=None, **kws):

        wx.Panel.__init__(self, parent, -1, size=(550, 500), **kws)
        self.parent = parent
        self.controller = controller
        self.larch = controller.larch
        self.fit_components = OrderedDict()
        self.fit_model = None
        self.fit_params = None
        self.summary = None
        self.sizer = wx.GridBagSizer(10, 6)
        self.build_display()
        self.pick2_timer = wx.Timer(self)
        self.pick2_group = None
        self.Bind(wx.EVT_TIMER, self.onPick2Timer, self.pick2_timer)
        self.pick2_t0 = 0.
        self.pick2_timeout = 15.

    def build_display(self):

        self.mod_nb = flat_nb.FlatNotebook(self, -1, agwStyle=FNB_STYLE)
        self.mod_nb.SetTabAreaColour(wx.Colour(250,250,250))
        self.mod_nb.SetActiveTabColour(wx.Colour(254,254,195))

        self.mod_nb.SetNonActiveTabTextColour(wx.Colour(10,10,128))
        self.mod_nb.SetActiveTabTextColour(wx.Colour(128,0,0))

        self.param_panel = AllParamsPanel(self, controller=self.controller)
        self.mod_nb.AddPage(self.param_panel, 'Parameters', True)

        range_row = wx.Panel(self)
        rsizer = wx.BoxSizer(wx.HORIZONTAL)

        xmin_sel = BitmapButton(range_row, get_icon('plus'),
                                action=partial(self.on_selpoint, opt='xmin'),
                                tooltip='use last point selected from plot')
        xmax_sel = BitmapButton(range_row, get_icon('plus'),
                                action=partial(self.on_selpoint, opt='xmax'),
                                tooltip='use last point selected from plot')

        opts = {'size': (70, -1), 'gformat': True}
        self.xmin = FloatCtrl(range_row, value=-np.inf, **opts)
        self.xmax = FloatCtrl(range_row, value=np.inf, **opts)

        rsizer.Add(SimpleText(range_row, 'Fit Range X=[ '), 0, LCEN, 3)
        rsizer.Add(xmin_sel, 0, LCEN, 3)
        rsizer.Add(self.xmin, 0, LCEN, 3)
        rsizer.Add(SimpleText(range_row, ' : '), 0, LCEN, 3)
        rsizer.Add(xmax_sel, 0, LCEN, 3)
        rsizer.Add(self.xmax, 0, LCEN, 3)
        rsizer.Add(SimpleText(range_row, ' ]  '), 0, LCEN, 3)
        rsizer.Add(Button(range_row, 'Use Full Data Range', size=(150, -1),
                          action=self.onResetRange), 0, LCEN, 3)

        pack(range_row, rsizer)

        action_row = wx.Panel(self)
        rsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.plot_comps = Check(action_row, label='Plot Components?',
                                default=True, size=(150, -1))

        rsizer.Add(Button(action_row, 'Run Fit',
                          size=(100, -1), action=self.onRunFit), 0, RCEN, 3)
        rsizer.Add(Button(action_row, 'Save Fit',
                         size=(100, -1), action=self.onSaveFit), 0, LCEN, 3)

        rsizer.Add(Button(action_row, 'Plot Current Model',
                          size=(150, -1), action=self.onShowModel), 0, LCEN, 3)
        rsizer.Add(self.plot_comps, 0, LCEN, 3)

        pack(action_row, rsizer)

        models_row = wx.Panel(self)
        rsizer = wx.BoxSizer(wx.HORIZONTAL)

        rsizer.Add(SimpleText(models_row, ' Add Model: '), 0, LCEN, 3)
        rsizer.Add(Choice(models_row, size=(150, -1), choices=PeakChoices,
                          action=self.addModel), 0, LCEN, 3)
        rsizer.Add(Choice(models_row, size=(150, -1), choices=StepChoices,
                         action=partial(self.addModel, is_step=True)), 0, LCEN, 3)
        rsizer.Add(Choice(models_row, size=(150, -1), choices=ModelChoices,
                          action=self.addModel), 0, LCEN, 3)

        pack(models_row, rsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddMany([(range_row, 0, LCEN,  4), ((9, 9), 0, LCEN, 4),
                       (models_row, 0, LCEN, 4), ((9, 9), 0, LCEN, 4),
                       (action_row, 0, LCEN, 4), ((9, 9), 0, LCEN, 4),
                       (HLine(self, size=(550, 3)), 0, LCEN, 4),
                       ((10,10), 0, LCEN, 2),
                       (self.mod_nb,  1, LCEN|wx.GROW, 10)])

        pack(self, sizer)


    def addModel(self, event=None, model=None, is_step=False):
        if model is None and event is not None:
            model = event.GetString()
        if model is None or model.startswith('<'):
            return

        curmodels = ["p%i_" % (i+1) for i in range(1+len(self.fit_components))]
        for comp in self.fit_components:
            if comp in curmodels:
                curmodels.remove(comp)

        prefix = curmodels[0]

        label = "%s(prefix='%s')" % (model, prefix)
        title = "%s: %s" % (prefix[:-1], (model+' '*4)[:5])
        mclass_kws = {'prefix': prefix}
        if is_step:
            form = model.lower()
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

        def SLabel(label, size=(75, -1), **kws):
            return  SimpleText(panel, label,
                               size=size, style=wx.ALIGN_LEFT, **kws)
        usebox = Check(panel, default=True, label='Use?', size=(75, -1))
        delbtn = Button(panel, 'Delete Model', size=(120, -1),
                        action=partial(self.onDeleteComponent, prefix=prefix))
        pick2msg = SimpleText(panel, "    ", size=(75, -1))
        pick2btn = Button(panel, 'Pick Data Range', size=(125, -1),
                          action=partial(self.onPick2Points, prefix=prefix))

        # SetTip(mname,  'Label for the model component')
        SetTip(usebox, 'Use this component in fit?')
        SetTip(delbtn, 'Delete this model component')
        SetTip(pick2btn, 'Select X range on Plot to Guess Initial Values')

        panel.Add(HLine(panel, size=(520, 3)), style=wx.ALIGN_CENTER, dcol=6)

        panel.Add(SLabel(label, size=(200, -1), colour='#0000AA'),
                  dcol=3,  newrow=True)
        panel.AddMany((usebox, pick2msg, pick2btn))

        panel.Add(SLabel("Parameter"),   newrow=True)
        panel.AddMany((SLabel("Value"), SLabel("Type"), SLabel("Min"),
                       SLabel("Max"), SLabel("Expression")))

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

            pwids = ParameterWidgets(panel, par, name_size=80, expr_size=150,
                                     float_size=70, prefix=prefix,
                                     widgets=('name', 'value',  'minval',
                                              'maxval', 'vary', 'expr'))
            parwids[par.name] = pwids
            panel.Add(pwids.name, newrow=True)
            panel.AddMany((pwids.value, pwids.vary, pwids.minval,
                           pwids.maxval, pwids.expr))

        for sname, hint in minst.param_hints.items():
            pname = "%s%s" % (prefix, sname)
            if 'expr' in hint and pname not in parnames:
                par = Parameter(name=pname, value=0, expr=hint['expr'])

                pwids = ParameterWidgets(panel, par, name_size=80, expr_size=275,
                                         float_size=70, prefix=prefix,
                                         widgets=('name', 'value', 'vary', 'expr'))
                parwids[par.name] = pwids
                panel.Add(pwids.name, newrow=True)
                panel.AddMany((pwids.value, pwids.vary))
                panel.Add(pwids.expr, dcol=3, style=wx.ALIGN_RIGHT)
                pwids.value.Disable()
                pwids.vary.Disable()

        panel.Add(HLine(panel, size=(90,  3)), style=wx.ALIGN_CENTER, newrow=True)
        panel.Add(delbtn, dcol=2)
        panel.Add(HLine(panel, size=(250, 3)), dcol=3, style=wx.ALIGN_CENTER)

        fgroup = Group(prefix=prefix, title=title, mclass=mclass,
                       mclass_kws=mclass_kws, usebox=usebox, panel=panel,
                       parwids=parwids, float_size=65, expr_size=150,
                       pick2_msg=pick2msg)

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

    def onPick2Timer(self, evt=None):
        try:
            curhist = self.larch.symtable._plotter.plot1.cursor_hist[:]
        except:
            return
        if (time.time() - self.pick2_t0) > self.pick2_timeout:
            msg = self.pick2_group.pick2_msg.SetLabel(" ")
            self.larch.symtable._plotter.plot1.cursor_hist = []
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
        x, y = dgroup.x, dgroup.y
        i0 = index_of(dgroup.x, xmin)
        i1 = index_of(dgroup.x, xmax)
        x, y = dgroup.x[i0:i1+1], dgroup.y[i0:i1+1]

        mod = self.pick2_group.mclass(prefix=self.pick2_group.prefix)
        parwids = self.pick2_group.parwids
        try:
            guesses = mod.guess(y, x=x)
        except:
            return

        for name, param in guesses.items():
            if name in parwids:
                parwids[name].value.SetValue(param.value)

        dgroup._tmp = mod.eval(guesses, x=dgroup.x)
        self.larch.symtable._plotter.plot1.oplot(dgroup.x, dgroup._tmp)
        self.larch.symtable._plotter.plot1.cursor_hist = []

    def onPick2Points(self, evt=None, prefix=None):
        fgroup = self.fit_components.get(prefix, None)
        if fgroup is None:
                return
        self.larch.symtable._plotter.plot1.cursor_hist = []
        fgroup.npts = len(self.larch.symtable._plotter.plot1.cursor_hist)
        self.pick2_group = fgroup

        if fgroup.pick2_msg is not None:
            fgroup.pick2_msg.SetLabel("0/2")

        self.pick2_t0 = time.time()
        self.pick2_timer.Start(250)

    def onSaveFit(self, event=None):
        dgroup = self.get_datagroup()
        deffile = dgroup.filename.replace('.', '_') + '.fitconf'
        outfile = FileSave(self, 'Save Fit Configuration and Results',
                           default_file=deffile,
                           wildcard=FITCONF_WILDCARDS)

        if outfile is None:
            return

        buff = ['#XYFit Config version 1']
        buff.append(json.dumps(encode4js(self.summary),
                               encoding='UTF-8',default=str))
        buff.append('')
        try:
            fout = open(outfile, 'w')
            fout.write('\n'.join(buff))
            fout.close()
        except IOError:
            print('could not write %s' % outfile)

    def onResetRange(self, event=None):
        dgroup = self.get_datagroup()
        self.xmin.SetValue(min(dgroup.x))
        self.xmax.SetValue(max(dgroup.x))

    def on_selpoint(self, evt=None, opt='xmin'):
        xval = None
        try:
            xval = self.larch.symtable._plotter.plot1_x
        except:
            xval = None
        if xval is not None:
            if opt == 'xmin':
                self.xmin.SetValue(xval)
            elif opt == 'xmax':
                self.xmax.SetValue(xval)

    def get_datagroup(self):
        dgroup = None
        if self.controller.groupname is not None:
            try:
                dgroup = getattr(self.larch.symtable,
                                 self.controller.groupname)
            except:
                pass
        return dgroup

    def get_xranges(self, x):
        xmin, xmax = min(x), max(x)
        i1, i2 = 0, len(x)
        _xmin = self.xmin.GetValue()
        _xmax = self.xmax.GetValue()
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
        dgroup = self.get_datagroup()
        model = None
        params = Parameters()
        self.summary = {'components': [], 'options': {}}
        for comp in self.fit_components.values():
            if comp.usebox is not None and comp.usebox.IsChecked():
                for parwids in comp.parwids.values():
                    params.add(parwids.param)
                self.summary['components'].append((comp.mclass.__name__, comp.mclass_kws))
                thismodel = comp.mclass(**comp.mclass_kws)
                if model is None:
                    model = thismodel
                else:
                    model += thismodel
        self.fit_model = model
        self.fit_params = params

        self.plot1 = self.larch.symtable._plotter.plot1
        if dgroup is not None:
            i1, i2, xv1, xv2 = self.get_xranges(dgroup.x)
            xsel = dgroup.x[slice(i1, i2)]
            dgroup.xfit = xsel
            dgroup.yfit = self.fit_model.eval(self.fit_params, x=xsel)
            dgroup.ycomps = self.fit_model.eval_components(params=self.fit_params,
                                                           x=xsel)
        return dgroup

    def onShowModel(self, event=None):
        dgroup = self.build_fitmodel()
        if dgroup is not None:
            with_components = (self.plot_comps.IsChecked() and
                               len(dgroup.ycomps) > 1)

            self.plot_fitmodel(dgroup, show_resid=False,
                               with_components=with_components)

    def plot_fitmodel(self, dgroup, show_resid=False, with_components=None):
        if dgroup is None:
            return
        i1, i2, xv1, xv2 = self.get_xranges(dgroup.x)
        self.controller.plot_group(self.controller.groupname, new=True,
                             xmin=xv1, xmax=xv2, label='data')

        self.plot1.oplot(dgroup.xfit, dgroup.yfit, label='fit')
        if with_components is None:
            with_components = (self.plot_comps.IsChecked() and
                               len(dgroup.ycomps) > 1)
        if with_components:
            for label, _y in dgroup.ycomps.items():
                self.plot1.oplot(dgroup.xfit, _y, label=label)

        _plotter = self.larch.symtable._plotter
        _plotter.plot_axvline(dgroup.x[i1], color='#999999')
        _plotter.plot_axvline(dgroup.x[i2-1], color='#999999')


    def onRunFit(self, event=None):
        dgroup = self.build_fitmodel()
        if dgroup is None:
            return
        i1, i2, xv1, xv2 = self.get_xranges(dgroup.x)
        dgroup.xfit = dgroup.x[slice(i1, i2)]
        ysel = dgroup.y[slice(i1, i2)]
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
        self.summary['report'] = result.fit_report()

        dgroup.fit_history = []
        dgroup.fit_history.append(self.summary)

        dgroup.yfit = result.best_fit
        dgroup.ycomps = self.fit_model.eval_components(params=result.params,
                                                       x=dgroup.xfit)
        self.plot_fitmodel(dgroup, show_resid=True, with_components=False)

        self.controller.show_report(result.fit_report())

        # fill parameters with best fit values
        allparwids = {}
        for comp in self.fit_components.values():
            if comp.usebox is not None and comp.usebox.IsChecked():
                for name, parwids in comp.parwids.items():
                    allparwids[name] = parwids

        for pname, par in result.params.items():
            if pname in allparwids:
                allparwids[pname].value.SetValue(par.value)
