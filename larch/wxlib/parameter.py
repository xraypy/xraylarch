#!/usr/bin/env python
"""
General-Purpose Parameter widget
  shows Float TextCtrl for value, Choice fixed/variable/constrained
  and icon button to bring up dialog for full settings,
  including max/min value and constraint expression
"""

import numpy as np
import ast
import wx
from wx.lib.embeddedimage import PyEmbeddedImage

from wxutils import (GridPanel, Choice, FloatCtrl,
                     LEFT, pack, HLine, SetTip)

from lmfit import Parameter
from larch import Group
from larch.larchlib import Empty

PAR_FIX = 'fix'
PAR_VAR = 'vary'
PAR_CON = 'constrain'
VARY_CHOICES = (PAR_VAR, PAR_FIX, PAR_CON)


BOUNDS_custom = 'custom'
BOUNDS_none   = 'unbound'
BOUNDS_pos    = 'positive'
BOUNDS_neg    = 'negative'
BOUNDS_CHOICES = (BOUNDS_none, BOUNDS_pos, BOUNDS_neg, BOUNDS_custom)

PAR_WIDS = ('name', 'value',  'minval', 'maxval',
            'vary', 'expr', 'stderr', 'bounds')

infoicon = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACzElEQVR42m2TW0gUURjHv3Nm"
    "b+6ut028lOaldm0RL2gGxWamSWHWi4JhPRjokyhCYWA9lfRQD0FUBJbdCBEEUzFILFjxQaxQ"
    "Wi+prXfXXV11J2zXXXdmOjPO7no78zAcvu//+/7nO+dDcMD6Ob14OiwisnDItpk0aXOi5XWX"
    "ecm68qW5Irtvby7aualq/q49k6FrlEulOQ4Pi4ALxLa8DFjsG/0zc9bKDzezhvcByt8PntRr"
    "Y7vlCmk4QmhXkGNZAIyBI0CXy7MxNW8vaizVG/05RQ9aNOmGHJNCIT3Mi3m9T3xcjSAvXgXG"
    "eSeM0SyBcOBxe1cnRn6ntVTlWoS86s6ZxwqV/DYWxXjHwc7HKcFwVA0dEzQMLbuBJS5YAnG7"
    "PK+eXo6vRNk36qisa1VWhHEEFsU+F5gkRisR8O1Y2eSE6tsAQmZZ5/i39ghUUN+UEpmZM8xX"
    "x0QtAMiXGEJBoS4MUmKCYWCOhre/1gMAlhNcOBfMBpR3911+cPKpHgoToQBAEKmkIDZUDqlR"
    "QXBBdwg6Ru3QOrImNFGA8ADSV2ZtsQQZ6prOKpIye4XqGPntKyQYGku0oJRJoLb9D8zT7j0A"
    "sqGtV1FaeUOUKq1gCRM1Eo/BX8FFXTjcyk+EcdsG1LRNCkIQ7YsQjlkwnRD6ndlgHGARzg44"
    "QPC8VA/pcWHw5OsU2Bwu6Jv+Kwh9DhDHTgzeO5csAPR1n4pZiboViQCVnALjHQNQ5PG0/ViA"
    "7jE79E85eP/bEAKgwFsx+vDSa/+NJ9R2fuQQVcY3QCbF8Kg0FWjXFrzpnYXZVacoBuGPgOly"
    "mrquLPe85PwATX61TKbNbeIAXxeeMto1JiCqSRO87cySqWyl475z3zDxS51bU0yFHqmnNAkZ"
    "/MX65Mz6rHlz9PMzxm5+4V2b2zpwGgMziiQoSBODQ6KPEa2EpS0WzuWwkMg/fjB3pv4HvQJH"
    "bUDKnS4AAAAASUVORK5CYII=")


class ParameterWidgets(object):
    """a set of related widgets for a lmfit Parameter

    param = Parameter(value=11.22, vary=True, min=0, name='x1')
    wid   = ParameterPanel(parent_wid, param)
    """
    def __init__(self, parent, param,  name_size=None, prefix=None,
                 expr_size=120, stderr_size=120, float_size=80,
                 minmax_size=60, widgets=PAR_WIDS):

        self.parent = parent
        self.param = param
        self.widgets = []
        self._saved_expr = ''
        if (prefix is not None and
            not self.param.name.startswith(prefix)):
            self.param.name = "%s%s" %(prefix, self.param.name)

        for attr in PAR_WIDS:
            setattr(self, attr, None)

        # set vary_choice from param attributes
        vary_choice = PAR_VAR
        value = None
        if param.expr not in (None, 'None', ''):
            vary_choice = PAR_CON
            try:
                value = param.value
            except:
                value = -np.Inf

        else:
            value = param.value
            vary_choice = PAR_VAR if param.vary else PAR_FIX

        if 'name' in widgets:
            name = param.name
            if name in (None, 'None', ''):
                name = ''
            if name_size is None:
                name_size = min(50, len(param.name)*10)
            self.name = wx.StaticText(parent, label=name,
                                      size=(name_size, -1))
            self.widgets.append(self.name)
        if 'value' in widgets:
            self.value = FloatCtrl(parent, value=value,
                                   minval=param.min,
                                   maxval=param.max,
                                   action=self.onValue,
                                   act_on_losefocus=True,
                                   gformat=True,
                                   size=(float_size, -1))
            self.widgets.append(self.value)

        if 'minval' in widgets:
            minval = param.min
            if minval in (None, 'None', -np.inf):
                minval = -np.inf
            self.minval = FloatCtrl(parent, value=minval,
                                    gformat=True,
                                    size=(minmax_size, -1),
                                    act_on_losefocus=True,
                                    action=self.onMinval)
            self.widgets.append(self.minval)
            self.minval.Enable(vary_choice==PAR_VAR)

        if 'maxval' in widgets:
            maxval = param.max
            if maxval in (None, 'None', np.inf):
                maxval = np.inf
            self.maxval = FloatCtrl(parent, value=maxval,
                                    gformat=True,
                                    size=(minmax_size, -1),
                                    act_on_losefocus=True,
                                    action=self.onMaxval)
            self.widgets.append(self.maxval)
            self.maxval.Enable(vary_choice==PAR_VAR)

        if 'vary' in widgets:
            self.vary = Choice(parent, size=(90, -1),
                               choices=VARY_CHOICES,
                               action=self.onVaryChoice)
            self.widgets.append(self.vary)
            self.vary.SetStringSelection(vary_choice)

        if 'expr' in widgets:
            expr = param.expr
            if expr in (None, 'None', ''):
                expr = ''
            self._saved_expr = expr
            self.expr = wx.TextCtrl(parent, -1, value=expr,
                                    size=(expr_size, -1),
                                    style=wx.TE_PROCESS_ENTER)
            self.widgets.append(self.expr)
            self.expr.Enable(vary_choice==PAR_CON)
            self.expr.Bind(wx.EVT_TEXT_ENTER, self.onExpr)
            self.expr.Bind(wx.EVT_KILL_FOCUS, self.onExpr)
            SetTip(self.expr, 'Enter constraint expression')

            if param.expr not in (None, 'None', ''):
                try:
                    ast.parse(param.expr)
                    bgcol, fgcol = 'white', 'black'
                except SyntaxError:
                    bgcol, fgcol = 'white', '#AA0000'

                self.expr.SetForegroundColour(fgcol)
                self.expr.SetBackgroundColour(bgcol)


        if 'stderr' in widgets:
            stderr = param.stderr
            if stderr in (None, 'None', ''):
                stderr = ''
            self.stderr = wx.StaticText(parent, label=stderr,
                                        size=(stderr_size, -1))
            self.widgets.append(self.expr)

        if 'minval' in widgets or 'maxval' in widgets:
            minval = param.min
            maxval = param.max
            bounds_choice = BOUNDS_custom
            if minval in (None, 'None', -np.inf) and maxval in (None, 'None', np.inf):
                bounds_choice = BOUNDS_none
            elif minval == 0:
                bounds_choice = BOUNDS_pos
            elif maxval == 0:
                bounds_choice = BOUNDS_neg

            self.bounds = Choice(parent, size=(90, -1),
                                 choices=BOUNDS_CHOICES,
                                 action=self.onBOUNDSChoice)
            self.widgets.append(self.bounds)
            self.bounds.SetStringSelection(bounds_choice)

    def onBOUNDSChoice(self, evt=None):
        bounds = str(self.bounds.GetStringSelection().lower())
        if bounds == BOUNDS_custom:
            pass
        elif bounds == BOUNDS_none:
            self.minval.SetValue(-np.inf)
            self.maxval.SetValue(np.inf)

        elif bounds == BOUNDS_pos:
            self.minval.SetValue(0)
            if float(self.maxval.GetValue()) == 0:
                self.maxval.SetValue(np.inf)
        elif bounds == BOUNDS_neg:
            self.maxval.SetValue(0)
            if float(self.minval.GetValue()) == 0:
                self.minval.SetValue(-np.inf)

    def onValue(self, evt=None, value=None):
        if value is not None:
            self.param.value = value

    def onExpr(self, evt=None, value=None):
        if value is None:
            value = self.expr.GetValue()
            # if hasattr(evt, 'GetString'):
            #     value = evt.GetString()
        try:
            ast.parse(value)
            self.param.expr = value
            bgcol, fgcol = 'white', 'black'
        except SyntaxError:
            bgcol, fgcol = 'white', '#AA0000'

        self.expr.SetForegroundColour(fgcol)
        self.expr.SetBackgroundColour(bgcol)


    def onMinval(self, evt=None, value=None):
        if value in (None, 'None', ''):
            value = -np.inf
        if self.value is not None:
            v = self.value.GetValue()
            self.value.SetMin(value)
            self.value.SetValue(v)
            self.param.min = value
        if self.bounds is not None:
            if value == 0:
                self.bounds.SetStringSelection(BOUNDS_pos)
            elif value == -np.inf:
                if self.maxval.GetValue() == np.inf:
                    self.bounds.SetStringSelection(BOUNDS_none)
            else:
                self.bounds.SetStringSelection(BOUNDS_custom)

    def onMaxval(self, evt=None, value=None):
        if value in (None, 'None', ''):
            value = np.inf
        if self.value is not None:
            v = self.value.GetValue()
            self.value.SetMax( value)
            self.value.SetValue(v)
            self.param.max = value

        if self.bounds is not None:
            if value == 0:
                self.bounds.SetStringSelection(BOUNDS_neg)
            elif value == np.inf:
                if self.minval.GetValue() == -np.inf:
                    self.bounds.SetStringSelection(BOUNDS_none)
            else:
                self.bounds.SetStringSelection(BOUNDS_custom)


    def onVaryChoice(self, evt=None):
        if self.vary is None:
            return

        vary = str(self.vary.GetStringSelection().lower())
        self.param.vary = (vary==PAR_VAR)
        if ((vary == PAR_VAR or vary == PAR_FIX) and
            self.param.expr not in (None, 'None', '')):
            self._saved_expr = self.param.expr
            self.param.expr = ''
        elif (vary == PAR_CON and self.param.expr in (None, 'None', '')):
            self.param.expr = self._saved_expr

        if self.value is not None:
            self.value.Enable(vary!=PAR_CON)
        if self.expr is not None:
            self.expr.Enable(vary==PAR_CON)
        if self.minval is not None:
            self.minval.Enable(vary!=PAR_FIX)
        if self.maxval is not None:
            self.maxval.Enable(vary!=PAR_FIX)
        if self.bounds is not None:
            self.bounds.Enable(vary!=PAR_FIX)


class ParameterDialog(wx.Dialog):
    """Dialog (modal, that is, block) for Parameter Configuration"""
    def __init__(self, parent, param, precision=4, vary=None, **kws):
        self.param = param
        title = "  Parameter:  %s  " % (param.name)
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)
        panel = GridPanel(self)
        self.SetFont(parent.GetFont())

        if vary is None:
            vary = 0
            if param.vary:
                vary = 1
            elif param.expr is not None:
                vary = 2

        minval, maxval = param.min, param.max
        stderr, expr   = param.stderr, param.expr
        sminval = "%s" % minval
        smaxval = "%s" % maxval
        if minval in (None, 'None', -np.inf): minval = -np.inf
        if maxval in (None, 'None',  np.inf): maxval = np.inf
        if stderr is None: stderr = ''
        if expr is None:   expr = ''

        self.wids = Empty()
        self.wids.vary = Choice(panel, choices=VARY_CHOICES,
                                action=self.onVaryChoice, size=(110, -1))
        self.wids.vary.SetSelection(vary)

        self.wids.val  = FloatCtrl(panel, value=param.value, size=(100, -1),
                                   precision=precision,
                                   minval=minval, maxval=maxval)
        self.wids.min  = FloatCtrl(panel, value=minval, size=(100, -1))
        self.wids.max  = FloatCtrl(panel, value=maxval, size=(100, -1))
        self.wids.expr = wx.TextCtrl(panel, value=expr, size=(300, -1))
        self.wids.err  = wx.StaticText(panel, label="%s" % stderr)

        SetTip(self.wids.expr, "Mathematical expression to calcutate value")

        btnsizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        ok_btn.SetDefault()
        btnsizer.AddButton(ok_btn)
        btnsizer.AddButton(wx.Button(panel, wx.ID_CANCEL))
        btnsizer.Realize()

        panel.AddText(' Name:',       style=LEFT)
        panel.AddText(param.name,     style=LEFT)
        panel.AddText(' Type:',       style=LEFT)
        panel.Add(self.wids.vary,     style=LEFT)
        panel.AddText(' Value:',      style=LEFT, newrow=True)
        panel.Add(self.wids.val,      style=LEFT)
        panel.AddText(' Std Error:',  style=LEFT)
        panel.Add(self.wids.err,      style=LEFT)
        panel.AddText(' Min Value:',  style=LEFT, newrow=True)
        panel.Add(self.wids.min,      style=LEFT)
        panel.AddText(' Max Value:',  style=LEFT)
        panel.Add(self.wids.max,      style=LEFT)
        panel.AddText(' Constraint:', style=LEFT, newrow=True)
        panel.Add(self.wids.expr,     style=LEFT, dcol=3)

        panel.Add(HLine(panel, size=(375, 2)), dcol=4, newrow=True)
        panel.Add(btnsizer,  dcol=4, newrow=True, style=LEFT)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 0, 0, 25)
        self.onVaryChoice()
        pack(self, sizer)
        bsize = self.GetBestSize()
        self.SetSize((bsize[0]+10, bsize[1]+10))

    def onVaryChoice(self, evt=None):

        vary = self.wids.vary.GetStringSelection()
        if vary == PAR_CON:
            self.wids.val.Disable()
            self.wids.expr.Enable()
        else:
            self.wids.val.Enable()
            self.wids.expr.Disable()


class ParameterPanel(wx.Panel):
    """wx.Panel for a Larch Parameter

    param = Parameter(value=11.22, vary=True, min=0, name='x1')
    wid   = ParameterPanel(parent_wid, param)
    """
    def __init__(self, parent, param, size=(80, -1), show_name=False, precision=4, **kws):
        self.param = param
        self.precision = precision
        wx.Panel.__init__(self, parent, -1)
        self.wids = Empty()

        self.wids.val = FloatCtrl(self, value=param.value,
                                  minval=param.min, maxval=param.max,
                                  precision=precision, size=size)

        self.wids.name = None
        self.wids.edit = wx.Button(self, label='edit', size=(45, 25))
        self.wids.edit.Bind(wx.EVT_BUTTON, self.onConfigure)
        SetTip(self.wids.edit, "Configure Parameter")

        self.wids.vary = Choice(self, choices=VARY_CHOICES,
                                action=self.onVaryChoice, size=(80, -1))

        vary_choice = 0
        if param.vary:
            vary_choice = 1
        elif param.expr is not None:
            vary_choice = 2
        self.wids.vary.SetSelection(vary_choice)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        CLEFT = LEFT|wx.ALL
        if show_name:
            self.wids.name = wx.StaticText(self,
                                           label="%s: " %  param.name,
                                           size=(len(param.name)*8, -1))
            sizer.Add(self.wids.name,  0, CLEFT)

        sizer.Add(self.wids.val,   0, CLEFT)
        sizer.Add(self.wids.vary,  0, CLEFT)
        sizer.Add(self.wids.edit,  0, CLEFT)
        pack(self, sizer)

    def onVaryChoice(self, evt=None):
        vary = self.wids.vary.GetStringSelection() # evt.GetString()
        self.param.vary = (vary == PAR_VAR)
        if vary == PAR_CON:
            self.wids.val.Disable()
        else:
            self.wids.val.Enable()

    def onConfigure(self, evt=None):
        self.param.value = self.wids.val.GetValue()
        vary = self.wids.vary.GetSelection()
        dlg = ParameterDialog(self, self.param, vary=vary,
                              precision=self.precision)
        dlg.Raise()
        if dlg.ShowModal() == wx.ID_OK:
            self.param.max   = float(dlg.wids.max.GetValue())
            self.param.min   = float(dlg.wids.min.GetValue())
            self.param.value = float(dlg.wids.val.GetValue())
            self.wids.val.SetMax(self.param.max)
            self.wids.val.SetMin(self.param.min)

            self.wids.val.SetValue(self.param.value)

            var = dlg.wids.vary.GetSelection()
            self.wids.vary.SetSelection(var)
            self.param.vary = False
            if var == 1:
                self.param.vary = True
            elif var == 2:
                self.param.expr= dlg.wids.expr.GetValue()
            self.param._getval()
        dlg.Destroy()

class TestFrame(wx.Frame):
    def __init__(self, parent=None, size=(-1, -1)):
        wx.Frame.__init__(self, parent, -1, 'Parameter Panel Test',
                          size=size, style=wx.DEFAULT_FRAME_STYLE)
        panel = GridPanel(self)

        param1 = Parameter(value=99.0, vary=True, min=0,            name='peak1_amplitude')
        param2 = Parameter(value=110.2, vary=True, min=100, max=120, name='peak1_center')
        param3 = Parameter(value=1.23, vary=True, min=0.5, max=2.0, name='peak1_sigma')

        panel.Add(ParameterPanel(panel, param1, show_name=True), style=LEFT)
        # panel.NewRow()
        panel.Add(ParameterPanel(panel, param2, show_name=True), style=LEFT)
        panel.Add(ParameterPanel(panel, param3, show_name=True), style=LEFT)
        panel.pack()
        self.createMenus()

        self.SetSize((700, 200))
        self.Show()
        self.Raise()

    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        im = fmenu.Append(wid, "Show Widget Frame\tCtrl+I", "")
        sellf.Bind(wx.EVT_MENU, self.onShowInspection, im.Id)
        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE, self.onExit)

    def onShowInspection(self, evt=None):
        wx.GetApp().ShowInspectionTool()

    def onExit(self, evt=None):
        self.Destroy()
