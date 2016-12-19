#!/usr/bin/env python
"""
Code for floating point controls
"""

from functools import partial
import wx

HAS_NUMPY = False
try:
    import numpy
    HAS_NUMPY = True
except ImportError:
    pass

def make_steps(prec=3, tmin=0, tmax=10, base=10, steps=(1, 2, 5)):
    """make a list of 'steps' to use for a numeric ComboBox
    returns a list of floats, such as
        [0.01, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00, 2.00...]
    """
    steplist = []
    power = -prec
    step = tmin
    while True:
        decade = base**power
        for step in (j*decade for j in steps):
            if step > 0.99*tmin and step <= tmax and step not in steplist:
                steplist.append(step)
        if step >= tmax:
            break
        power += 1
    return steplist

def set_float(val, default=0):
    """ utility to set a floating value,
    useful for converting from strings """
    out = None
    if not val in (None, ''):
        try:
            out = float(val)
        except ValueError:
            return None
        if HAS_NUMPY:
            if numpy.isnan(out):
                out = default
        else:
            if not(out > 0) and not(out<0) and not(out==0):
                out = default
    return out

class FloatCtrl(wx.TextCtrl):
    """ Numerical Float Control::
    wx.TextCtrl that allows only numerical input

    takes a precision argument
    and optional upper / lower bounds
    options:
     action             callback on Enter (or lose focus)
     act_on_losefocus   boolean (default False) to act on lose focus events
     action_kws         keyword args for action

    """
    def __init__(self, parent, value='', minval=None, maxval=None,
                 precision=3, bell_on_invalid = True,
                 act_on_losefocus=False, gformat=False,
                 action=None, action_kws=None, **kws):

        self.__digits = '0123456789.-e'
        self.__prec   = precision
        if precision is None:
            self.__prec = 0
        self.format   = '%%.%if' % self.__prec
        self.gformat  = gformat
        if gformat:
            self.__prec = max(8, self.__prec)
            self.format = '%%.%ig' % self.__prec

        self.is_valid = True
        self.__val = set_float(value)
        self.__max = set_float(maxval)
        self.__min = set_float(minval)
        self.__bound_val = None
        self.__mark = None
        self.__action = None

        self.fgcol_valid   = "Black"
        self.bgcol_valid   = "White"
        self.fgcol_invalid = "Red"
        self.bgcol_invalid = (254, 254, 80)
        self.bell_on_invalid = bell_on_invalid
        self.act_on_losefocus = act_on_losefocus

        # set up action
        if action_kws is None:
            action_kws = {}
        self.SetAction(action, **action_kws)

        this_sty =  wx.TE_PROCESS_ENTER|wx.TE_RIGHT
        if 'style' in kws:
            this_sty = this_sty | kws['style']
        kws['style'] = this_sty

        wx.TextCtrl.__init__(self, parent, wx.ID_ANY, **kws)

        self.__CheckValid(self.__val)
        self.SetValue(self.__val)

        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_TEXT, self.OnText)

        self.Bind(wx.EVT_SET_FOCUS,  self.OnSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.__GetMark()

    def SetAction(self, action, **kws):
        "set callback action"
        if hasattr(action,'__call__'):
            self.__action = partial(action, **kws)

    def SetPrecision(self, prec=0, gformat=None):
        "set precision"
        self.__prec = prec
        if gformat is not None:
            self.gformat = gformat
        if self.gformat:
            self.__prec = max(8, self.__prec)
            self.format = '%%.%ig' % self.__prec
        else:
            self.format = '%%.%if' % prec

    def __GetMark(self):
        " keep track of cursor position within text"
        try:
            self.__mark = min(wx.TextCtrl.GetSelection(self)[0],
                              len(wx.TextCtrl.GetValue(self).strip()))
        except:
            self.__mark = 0

    def __SetMark(self, mark=None):
        "set mark for later"
        if mark is None:
            mark = self.__mark
        self.SetSelection(mark, mark)

    def SetValue(self, value=None, act=True):
        " main method to set value "
        if value is None:
            value = wx.TextCtrl.GetValue(self).strip()
        self.__CheckValid(value)
        self.__GetMark()
        if value is not None:
            wx.TextCtrl.SetValue(self, self.format % set_float(value))

        if self.is_valid and hasattr(self.__action, '__call__') and act:
            self.__action(value=self.__val)
        elif not self.is_valid and self.bell_on_invalid:
            wx.Bell()

        self.__SetMark()

    def OnKillFocus(self, event):
        "focus lost"
        self.__GetMark()
        if self.act_on_losefocus and hasattr(self.__action, '__call__'):
            self.__action(value=self.__val)
        event.Skip()

    def OnSetFocus(self, event):
        "focus gained - resume editing from last mark point"
        self.__SetMark()
        event.Skip()

    def OnChar(self, event):
        """ on Character event"""
        key   = event.GetKeyCode()
        entry = wx.TextCtrl.GetValue(self).strip()
        pos   = wx.TextCtrl.GetSelection(self)[0]
        # really, the order here is important:
        # 1. return sends to ValidateEntry
        if key == wx.WXK_RETURN:
            if not self.is_valid:
                wx.TextCtrl.SetValue(self, self.format % set_float(self.__bound_val))
            else:
                self.SetValue(entry)
            return

        # 2. other non-text characters are passed without change
        if (key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255):
            event.Skip()
            return

        # 3. check for multiple '.' and out of place '-' signs and ignore these
        #    note that chr(key) will now work due to return at #2
        ckey = chr(key)
        if ((ckey == '.' and (self.__prec == 0 or '.' in entry)) or
            (ckey != '-' and pos == 0 and entry.startswith('-'))):
            return
        if 'e' in entry:
            if ckey == 'e':
                return
            ind_e = entry.index('e')
            if (ckey == '-' and pos not in (0, ind_e+1)):
                return
        elif (ckey == '-' and '-' in entry):
            return
        # allow 'inf' and '-inf', but very restricted
        if ckey in ('i', 'n', 'f'):
            has_num = any([x in entry for x in self.__digits[:11]])
            if ((ckey in entry) or has_num or
                entry not in ('', '-', '-i', 'i', '-n', 'n', '-f', 'f',
                              '-in', 'in', '-if', 'if',
                             '-nf', 'nf', '-inf', 'inf')):
                return
        elif (ckey != '-' and ckey in self.__digits and
              any([x in ('i', 'n', 'f') for x in entry])):
            return

        # 4. allow digits or +/-inf but not other characters
        if ckey in self.__digits or ckey in ('i', 'n', 'f'):
            event.Skip()

    def OnText(self, event=None):
        "text event"
        try:
            if event.GetString() != '':
                self.__CheckValid(event.GetString())
        except:
            pass
        event.Skip()

    def GetValue(self):
        if self.__prec > 0:
            return set_float("%%.%ig" % (self.__prec) % (self.__val))
        else:
            return int(self.__val)

    def GetMin(self):
        "return min value"
        return self.__min

    def GetMax(self):
        "return max value"
        return self.__max

    def SetMin(self, val):
        "set min value"
        self.__min = set_float(val)

    def SetMax(self, val):
        "set max value"
        self.__max = set_float(val)

    def __CheckValid(self, value):
        "check for validity of value"
        val = self.__val
        self.is_valid = True
        try:
            val = set_float(value)
            if self.__min is not None and (val < self.__min):
                self.is_valid = False
                val = self.__min
            if self.__max is not None and (val > self.__max):
                self.is_valid = False
                val = self.__max
        except:
            self.is_valid = False
        self.__bound_val = self.__val = val
        fgcol, bgcol = self.fgcol_valid, self.bgcol_valid
        if not self.is_valid:
            fgcol, bgcol = self.fgcol_invalid, self.bgcol_invalid

        self.SetForegroundColour(fgcol)
        self.SetBackgroundColour(bgcol)
        self.Refresh()

class NumericCombo(wx.ComboBox):
    """
    Numeric Combo: ComboBox with numeric-only choices
    """
    def __init__(self, parent, choices, precision=3,
                 init=0, width=80):

        self.fmt = "%%.%if" % precision
        self.choices  = choices
        schoices = [self.fmt % i for i in self.choices]
        wx.ComboBox.__init__(self, parent, -1, '', (-1, -1), (width, -1),
                             schoices, wx.CB_DROPDOWN|wx.TE_PROCESS_ENTER)

        init = min(init, len(self.choices))
        self.SetStringSelection(schoices[init])
        self.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)

    def OnEnter(self, event=None):
        "text enter event handler"
        thisval = float(event.GetString())

        if thisval not in self.choices:
            self.choices.append(thisval)
            self.choices.sort()

        self.Clear()
        self.AppendItems([self.fmt % i for i in self.choices])
        self.SetSelection(self.choices.index(thisval))
