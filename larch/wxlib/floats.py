import sys
import wx
from wx.lib.agw import floatspin as fspin

is_gtk3  = 'gtk3' in wx.PlatformInfo

from wxutils.icons import get_icon

def FloatSpin(parent, value=0, action=None, tooltip=None,
                 size=(100, -1), digits=1, increment=1, **kws):
    """FloatSpin with action and tooltip"""
    if value is None:
        value = 0
    if is_gtk3:
        size = (size[0]+30, size[1])

    # need to work this out better for GTK3 - lots of small
    # differences with GTK2, but this one is the biggest headache.
    # SpinCtrlDouble is like FloatSpin, but with every option
    # having a slightly different name...
    if is_gtk3 and False:
        maxval = kws.pop('max_val', None)
        minval = kws.pop('min_val', None)
        fmt = "%%%df" % digits
        fs = wx.SpinCtrlDouble(parent, -1, value=fmt % value,
                               size=(size[0]+25, size[1]),
                               inc=increment, **kws)
        fs = wx.SpinCtrlDouble(parent, -1, value=fmt % value,
                               size=(size[0]+25, size[1]),
                               inc=increment, **kws)
        fs.SetDigits(digits)
        if minval is not None:
            fs.SetMin(minval)
        if maxval is not None:
            fs.SetMax(maxval)

        if action is not None:
            fs.Bind(wx.EVT_SPINCTRLDOUBLE, action)

    else:
        fs = fspin.FloatSpin(parent, -1, size=size, value=value,
                             digits=digits, increment=increment, **kws)

        if action is not None:
            fs.Bind(fspin.EVT_FLOATSPIN, action)
    if tooltip is not None:
        fs.SetToolTip(tooltip)
    return fs

def FloatSpinWithPin(parent, value=0, pin_action=None,
                     tooltip='use last point selected from plot', **kws):
    """create a FloatSpin with Pin button with action"""
    fspin = FloatSpin(parent, value=value, **kws)
    bmbtn = wx.BitmapButton(parent, id=-1, bitmap=get_icon('pin'),
                            size=(25, 25))
    if pin_action is not None:
        parent.Bind(wx.EVT_BUTTON, pin_action, bmbtn)
    bmbtn.SetToolTip(tooltip)
    return fspin, bmbtn

class NumericCombo(wx.ComboBox):
    """
    Numeric Combo: ComboBox with numeric-only choices
    """
    def __init__(self, parent, choices, precision=3, fmt=None,
                 init=0, default_val=None, width=80):

        self.fmt = fmt
        if fmt is None:
            self.fmt = "%%.%if" % precision

        self.choices  = choices
        schoices = [self.fmt % i for i in self.choices]
        wx.ComboBox.__init__(self, parent, -1, '', (-1, -1), (width, -1),
                             schoices, wx.CB_DROPDOWN|wx.TE_PROCESS_ENTER)

        init = min(init, len(self.choices))
        if default_val is not None:
            if default_val in schoices:
                self.SetStringSelection(default_val)
            else:
                self.add_choice(default_val, select=True)
        else:
            self.SetStringSelection(schoices[init])
        self.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)

    def OnEnter(self, event=None):
        self.add_choice(float(event.GetString()))

    def add_choice(self, val, select=True):
        if val not in self.choices:
            self.choices.append(val)
            self.choices.sort()
        self.choices.reverse()
        self.Clear()
        self.AppendItems([self.fmt % x for x in self.choices])
        if select:
            self.SetSelection(self.choices.index(val))
