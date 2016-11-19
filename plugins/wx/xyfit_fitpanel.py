import time
import numpy as np
np.seterr(all='ignore')

from functools import partial

import wx
import wx.lib.scrolledpanel as scrolled

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check,
                     MenuItem, GUIColors, GridPanel, CEN, RCEN, LCEN,
                     FRAMESTYLE, Font)

import lmfit.models as lm_models
from lmfit import Parameter, Parameters

from larch import Group

from larch.wxlib import (ReportFrame, BitmapButton, ParameterWidgets,
                         FloatCtrl, SetTip)

from larch.fitting import fit_report
from larch_plugins.std import group2dict
from larch_plugins.math import index_of
from larch_plugins.wx.icons import get_icon
from larch_plugins.wx.parameter import ParameterDialog, ParameterPanel

LCEN = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
CEN |=  wx.ALL

StepChoices = ('<Add Step Model>', 'Linear', 'Arctan', 'ErrorFunction',
               'Logistic')

PeakChoices = ('<Add Peak Model>', 'Gaussian', 'Lorentzian', 'Voigt',
               'PseudoVoigt', 'Pearson7', 'StudentsT', 'SkewedGaussian',
               'Moffat', 'BreitWigner', 'Donaich', 'Lognormal')

ModelChoices = ('<Add Other Model>', 'Constant', 'Linear', 'Quadratic',
               'Exponential', 'PowerLaw', 'Rectangle', 'DampedOscillator')

class XYFitPanel(wx.Panel):
    def __init__(self, parent=None, main=None, **kws):

        wx.Panel.__init__(self, parent, -1, size=(550, 500), **kws)
        self.parent = parent
        self.main  = main
        self.fit_components = []
        self.fit_model = None
        self.fit_params = None
        self.sizer = wx.GridBagSizer(10, 6)
        self.build_display()
        self.pick2_timer = wx.Timer(self)
        self.pick2_group = None
        self.Bind(wx.EVT_TIMER, self.onPick2Timer, self.pick2_timer)
        self.pick2_t0 = 0.
        self.pick2_timeout = 15.

    def build_display(self):

        self.modelpanel = scrolled.ScrolledPanel(self, style=wx.GROW|wx.TAB_TRAVERSAL)
        self.modelsizer = wx.BoxSizer(wx.VERTICAL)

        pack(self.modelpanel, self.modelsizer)
        self.modelpanel.SetupScrolling()
        self.modelpanel.SetAutoLayout(1)

        row1 = wx.Panel(self)
        rsizer = wx.BoxSizer(wx.HORIZONTAL)

        xmin_sel = BitmapButton(row1, get_icon('plus'),
                                action=partial(self.on_selpoint, opt='xmin'),
                                tooltip='use last point selected from plot')
        xmax_sel = BitmapButton(row1, get_icon('plus'),
                                action=partial(self.on_selpoint, opt='xmax'),
                                tooltip='use last point selected from plot')

        opts = {'size': (70, -1), 'gformat': True}
        self.xmin = FloatCtrl(row1, value=-np.inf, **opts)
        self.xmax = FloatCtrl(row1, value=np.inf, **opts)

        rsizer.Add(SimpleText(row1, 'Fit Range: [ '), 0, LCEN, 3)
        rsizer.Add(xmin_sel, 0, LCEN, 3)
        rsizer.Add(self.xmin, 0, LCEN, 3)
        rsizer.Add(SimpleText(row1, ' : '), 0, LCEN, 3)
        rsizer.Add(xmax_sel, 0, LCEN, 3)
        rsizer.Add(self.xmax, 0, LCEN, 3)
        rsizer.Add(SimpleText(row1, ' ]  '), 0, LCEN, 3)
        rsizer.Add(Button(row1, 'Use Full Range', size=(120, -1),
                          action=self.onResetRange), 0, LCEN, 3)

        pack(row1, rsizer)

        row2 = wx.Panel(self)
        rsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.plot_comps = Check(row2, label='Plot Components?',
                                default=True, size=(140, -1))

        rsizer.Add(Button(row2, 'Plot Model',
                          size=(100, -1), action=self.onShowModel), 0, LCEN, 3)
        rsizer.Add(self.plot_comps, 0, LCEN, 3)
        rsizer.Add(Button(row2, 'Save Fit',
                         size=(100, -1), action=self.onSaveFit), 0, LCEN, 3)
        rsizer.Add(Button(row2, 'Run Fit',
                          size=(150, -1), action=self.onRunFit), 0, RCEN, 3)
        pack(row2, rsizer)

        row3 = wx.Panel(self)
        rsizer = wx.BoxSizer(wx.HORIZONTAL)

        rsizer.Add(SimpleText(row3, ' Add Model: '), 0, LCEN, 3)
        rsizer.Add(Choice(row3, size=(150, -1), choices=PeakChoices,
                          action=self.addModel), 0, LCEN, 3)
        rsizer.Add(Choice(row3, size=(150, -1), choices=StepChoices,
                         action=partial(self.addModel, is_step=True)), 0, LCEN, 3)
        rsizer.Add(Choice(row3, size=(150, -1), choices=ModelChoices,
                          action=self.addModel), 0, LCEN, 3)

        pack(row3, rsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddMany([(row1, 0, LCEN, 5),
                       (row2, 0, LCEN, 5),
                       (row3, 0, LCEN, 5),
                       ((5,5), 0, LCEN, 0),
                       (HLine(self, size=(550, 2)), 0, LCEN, 10),
                       ((5,5), 0, LCEN, 0),
                       (self.modelpanel,  1, LCEN|wx.GROW, 10)])

        pack(self, sizer)


    def addModel(self, event=None, model=None, is_step=False):
        if model is None and event is not None:
            model = event.GetString()
        if model is None or model.startswith('<'):
            return

        icomp = len(self.fit_components)
        prefix = "p%i_" % (icomp + 1)

        title = "%s(" % model
        mclass_kws = {'prefix': prefix}
        if is_step:
            form = model.lower()
            if form.startswith('err'): form = 'erf'
            title = "Step(form='%s', " % form
            mclass = lm_models.StepModel
            mclass_kws['form'] = form
            minst = mclass(form=form)
        else:
            mclass = getattr(lm_models, model+'Model')
            minst = mclass()

        fgroup = Group(icomp=icomp, prefix=prefix,
                       mclass=mclass, mclass_kws=mclass_kws)
        panel = GridPanel(self.modelpanel, ncols=1, nrows=1,
                          pad=1, itemstyle=CEN)

        def SLabel(label, size=(80, -1), **kws):
            return  SimpleText(panel, label,
                               size=size, style=wx.ALIGN_LEFT, **kws)
        mname  = wx.TextCtrl(panel, -1, prefix, size=(80, -1))
        usebox = Check(panel, default=True, label='Use?', size=(90, -1))
        delbtn = Button(panel, 'Delete', size=(80, -1),
                        action=partial(self.onDeleteComponent, comp=icomp))
        pick2msg = SimpleText(panel, "    ", size=(80, -1))
        pick2btn = Button(panel, 'Pick Range', size=(80, -1),
                          action=partial(self.onPick2Points, comp=icomp))

        SetTip(mname,  'Label for the model component')
        SetTip(usebox, 'Use this component in fit?')
        SetTip(delbtn, 'Delete this model component')
        SetTip(pick2btn, 'Select X range on Plot to Guess Initial Values')

        panel.Add(HLine(panel, size=(90, 3)), style=wx.ALIGN_CENTER)
        panel.Add(SLabel(" %sprefix='%s')" % (title, prefix), size=(250, -1),
                         colour='#0000AA'), dcol=4)
        panel.Add(HLine(panel, size=(120, 3)), style=wx.ALIGN_CENTER)
        panel.Add(SLabel("Label:"),  newrow=True)
        panel.AddMany((mname, usebox, pick2btn, pick2msg, delbtn))

        panel.Add(SLabel("Parameter"),   newrow=True)
        panel.AddMany((SLabel("Value"), SLabel("Type"), SLabel("Min"),
                       SLabel("Max"), SLabel("Expression")))

        parwids = {}
        for pname in sorted(minst.param_names):
            par = Parameter(name=pname, value=0, vary=True)
            if 'sigma' in pname:
                par.min = 0.0
            pwids = ParameterWidgets(panel, par, name_size=80,
                                     float_size=80, prefix=prefix,
                                     widgets=('name', 'value',  'minval',
                                              'maxval', 'vary', 'expr'))
            parwids[par.name] = pwids
            panel.Add(pwids.name, newrow=True)
            panel.AddMany((pwids.value, pwids.vary, pwids.minval,
                           pwids.maxval, pwids.expr))

        panel.Add(HLine(panel, size=(90,  3)), style=wx.ALIGN_CENTER, newrow=True)
        panel.Add(HLine(panel, size=(325, 3)), dcol=4, style=wx.ALIGN_CENTER)
        panel.Add(HLine(panel, size=(120, 3)), style=wx.ALIGN_CENTER)

        fgroup = Group(icomp=icomp, prefix=prefix,
                       mclass=mclass, mclass_kws=mclass_kws,
                       usebox=usebox, panel=panel, parwids=parwids,
                       pick2_msg=pick2msg)

        self.fit_components.append(fgroup)
        panel.pack()

        self.modelsizer.Add(panel, 0, LCEN|wx.GROW, 2)
        pack(self.modelpanel, self.modelsizer)
        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))

    def onDeleteComponent(self, evt=None, comp=-1):
        if comp > -1:
            fgroup = self.fit_components[comp]
            if fgroup.icomp == comp and fgroup.panel is not None:
                fgroup.panel.Destroy()
                for attr in dir(fgroup):
                    setattr(fgroup, attr, None)

        sx,sy = self.GetSize()
        self.SetSize((sx, sy+1))
        self.SetSize((sx, sy))

    def onPick2Timer(self, evt=None):
        try:
            curhist = self.main.larch.symtable._plotter.plot1.cursor_hist[:]
        except:
            return
        if (time.time() - self.pick2_t0) > self.pick2_timeout:
            msg = self.pick2_group.pick2_msg.SetLabel(" ")
            self.main.larch.symtable._plotter.plot1.cursor_hist = []
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

        dgroup = getattr(self.main.larch.symtable, self.main.groupname)
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
        self.main.larch.symtable._plotter.plot1.oplot(dgroup.x, dgroup._tmp)
        self.main.larch.symtable._plotter.plot1.cursor_hist = []

    def onPick2Points(self, evt=None, comp=-1):
        if comp > -1:
            fgroup = self.fit_components[comp]
            if fgroup.icomp != comp or fgroup.panel is None:
                return
        self.main.larch.symtable._plotter.plot1.cursor_hist = []
        fgroup.npts = len(self.main.larch.symtable._plotter.plot1.cursor_hist)
        self.pick2_group = fgroup

        if fgroup.pick2_msg is not None:
            fgroup.pick2_msg.SetLabel("0/2")

        self.pick2_t0 = time.time()
        self.pick2_timer.Start(250)

    def onSaveFit(self, event=None):
        print "Save Fit : ", self.fit_model, self.fit_components

        if (self.fit_model is None and
            len(self.fit_components) > 0):
            self.build_fitmodel()
        print self.fit_model
        print self.fit_params.dumps()

    def onResetRange(self, event=None):
        dgroup = self.get_datagroup()
        self.xmin.SetValue(min(dgroup.x))
        self.xmax.SetValue(max(dgroup.x))

    def on_selpoint(self, evt=None, opt='xmin'):
        xval = None
        try:
            xval = self.main.larch.symtable._plotter.plot1_x
        except:
            xval = None
        if xval is not None:
            if opt == 'xmin':
                self.xmin.SetValue(xval)
            elif opt == 'xmax':
                self.xmax.SetValue(xval)

    def get_datagroup(self):
        dgroup = None
        if self.main.groupname is not None:
            try:
                dgroup = getattr(self.main.larch.symtable,
                                      self.main.groupname)
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
        for comp in self.fit_components:
            if comp.usebox is not None and comp.usebox.IsChecked():
                for parwids in comp.parwids.values():
                    params.add(parwids.param)
                thismodel = comp.mclass(**comp.mclass_kws)
                if model is None:
                    model = thismodel
                else:
                    model += thismodel
        self.fit_model = model
        self.fit_params = params

        self.plot1 = self.main.larch.symtable._plotter.plot1
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
        self.main.plot_group(self.main.groupname, new=True,
                             xmin=xv1, xmax=xv2, label='data')

        self.plot1.oplot(dgroup.xfit, dgroup.yfit, label='fit')
        if with_components is None:
            with_components = (self.plot_comps.IsChecked() and
                               len(dgroup.ycomps) > 1)
        if with_components:
            for label, _y in dgroup.ycomps.items():
                self.plot1.oplot(dgroup.xfit, _y, label=label)

        _plotter = self.main.larch.symtable._plotter
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

        dgroup.yfit = result.best_fit
        dgroup.ycomps = self.fit_model.eval_components(params=result.params,
                                                       x=dgroup.xfit)
        self.plot_fitmodel(dgroup, show_resid=True, with_components=False)

        self.main.show_report(result.fit_report())

        # fill parameters with best fit values
        allparwids = {}
        for comp in self.fit_components:
            if comp.usebox is not None and comp.usebox.IsChecked():
                for name, parwids in comp.parwids.items():
                    allparwids[name] = parwids

        for pname, par in result.params.items():
            if pname in allparwids:
                allparwids[pname].value.SetValue(par.value)
