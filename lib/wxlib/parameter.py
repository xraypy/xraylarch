#!/usr/bin/env python
"""
ParameterWidgets to create selected widgets for a Parameter
"""

import numpy as np
import ast
import wx
from wx.lib.embeddedimage import PyEmbeddedImage

from wxutils import Choice, pack, HLine, GridPanel, LEFT
from .floats import FloatCtrl
from .utils import SetTip

from larch import Parameter, Group
from larch.larchlib import Empty

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


PAR_FIX = 'fix'
PAR_VAR = 'vary'
PAR_CON = 'constrain'
VARY_CHOICES = (PAR_VAR, PAR_FIX, PAR_CON)
PAR_WIDS = ('name', 'value',  'minval', 'maxval', 'vary', 'expr', 'stderr')
class ParameterWidgets(object):
    """a set of related widgets for a lmfit Parameter

    param = Parameter(value=11.22, vary=True, min=0, name='x1')
    wid   = ParameterPanel(parent_wid, param)
    """
    def __init__(self, parent, param,  name_size=None, prefix=None,
                 expr_size=120, stderr_size=120, float_size=80,
                 widgets=PAR_WIDS):

        self.parent = parent
        self.param = param
        self._saved_expr = ''
        if (prefix is not None and
            not self.param.name.startswith(prefix)):
            self.param.name = "%s%s" %(prefix, self.param.name)

        for attr in PAR_WIDS:
            setattr(self, attr, None)

        # set vary_choice from param attributes
        vary_choice = PAR_VAR
        if param.expr not in (None, 'None', ''):
            vary_choice = PAR_CON
        elif not param.vary:
            vary_choice = PAR_FIX

        if 'name' in widgets:
            name = param.name
            if name in (None, 'None', ''):
                name = ''
            if name_size is None:
                name_size = min(50, len(param.name)*10)
            self.name = wx.StaticText(parent, label=name,
                                      size=(name_size, -1))

        if 'value' in widgets:
            self.value = FloatCtrl(parent, value=param.value,
                                   minval=param.min,
                                   maxval=param.max,
                                   action=self.onValue,
                                   act_on_losefocus=True,
                                   gformat=True,
                                   size=(float_size, -1))

        if 'minval' in widgets:
            minval = param.min
            if minval in (None, 'None', -np.inf):
                minval = -np.inf
            self.minval = FloatCtrl(parent, value=minval,
                                    gformat=True,
                                    size=(float_size, -1),
                                    act_on_losefocus=True,
                                    action=self.onMinval)
            self.minval.Enable(vary_choice==PAR_VAR)

        if 'maxval' in widgets:
            maxval = param.max
            if maxval in (None, 'None', np.inf):
                maxval = np.inf
            self.maxval = FloatCtrl(parent, value=maxval,
                                    gformat=True,
                                    size=(float_size, -1),
                                    act_on_losefocus=True,
                                    action=self.onMaxval)
            self.maxval.Enable(vary_choice==PAR_VAR)

        if 'vary' in widgets:
            self.vary = Choice(parent, size=(90, -1),
                               choices=VARY_CHOICES,
                               action=self.onVaryChoice)
            self.vary.SetStringSelection(vary_choice)

        if 'expr' in widgets:
            expr = param.expr
            if expr in (None, 'None', ''):
                expr = ''
            self._saved_expr = expr
            self.expr = wx.TextCtrl(parent, -1, value=expr,
                                      size=(expr_size, -1))
            self.expr.Enable(vary_choice==PAR_CON)
            self.expr.Bind(wx.EVT_CHAR, self.onExprChar)
            self.expr.Bind(wx.EVT_KILL_FOCUS, self.onExprKillFocus)
            SetTip(self.expr, 'Enter constraint expression')

        if 'stderr' in widgets:
            stderr = param.stderr
            if stderr in (None, 'None', ''):
                stderr = ''
            self.stderr = wx.StaticText(parent, label=stderr,
                                        size=(stderr_size, -1))

    def onValue(self, evt=None, value=None):
        if value is not None:
            self.param.value = value

    def onExprChar(self, evt=None):
        key = evt.GetKeyCode()
        if key == wx.WXK_RETURN:
            self.onExpr(value=self.expr.GetValue())
        evt.Skip()

    def onExprKillFocus(self, evt=None):
        self.onExpr(value=self.expr.GetValue())
        evt.Skip()

    def onExpr(self, evt=None, value=None):
        if value is None and evt is not None:
            value = evt.GetString()
        try:
            ast.parse(value)
            self.param.expr = value
            bgcol, fgcol = 'white', 'black'
        except SyntaxError:
            bgcol, fgcol = 'red', 'yellow'

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

    def onMaxval(self, evt=None, value=None):
        # print "onMaxval " , value, self.value, self.value
        if value in (None, 'None', ''):
            value = np.inf
        if self.value is not None:
            v = self.value.GetValue()
            self.value.SetMax( value)
            self.value.SetValue(v)
            self.param.max = value

    def onVaryChoice(self, evt=None):
        if self.vary is None:
            return
        vary = str(evt.GetString().lower())
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
            self.minval.Enable(vary==PAR_VAR)
        if self.maxval is not None:
            self.maxval.Enable(vary==PAR_VAR)
