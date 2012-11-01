#!/usr/bin/env python
# epics/wx/utils.py
"""
This is a collection of general purpose utility functions and classes,
especially useful for wx functionality
"""
import wx
import wx.lib.masked as masked

import os
import array
from string import maketrans

import fpformat

HAS_NUMPY = False
try:
    import numpy
    HAS_NUMPY = True
except ImportError:
    pass

# some common abbrevs for wx ALIGNMENT styles
RIGHT = wx.ALIGN_RIGHT
LEFT  = wx.ALIGN_LEFT
CEN   = wx.ALIGN_CENTER
LCEN  = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT
RCEN  = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT
CCEN  = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER
LTEXT = wx.ST_NO_AUTORESIZE|wx.ALIGN_CENTER


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

def set_sizer(panel, sizer=None, style=wx.VERTICAL, fit=False):
    """ utility for setting wx Sizer  """
    if sizer is None:
        sizer = wx.BoxSizer(style)
    panel.SetAutoLayout(1)
    panel.SetSizer(sizer)
    if fit:
        sizer.Fit(panel)

def set_float(val):
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

def pack(window, sizer):
    "simple wxPython pack function"
    window.SetSizer(sizer)
    sizer.Fit(window)

def add_button(parent, label, size=(-1, -1), action=None):
    "add simple button with bound action"
    thisb = wx.Button(parent, label=label, size=size)
    if hasattr(action, '__call__'):
        parent.Bind(wx.EVT_BUTTON, action, thisb)
    return thisb

def add_menu(parent, menu, label='', text='', action=None):
    "add submenu"
    wid = wx.NewId()
    menu.Append(wid, label, text)
    if hasattr(action, '__call__'):
        wx.EVT_MENU(parent, wid, action)

def popup(parent, message, title, style=None):
    """
    generic popup message dialog, returns
    output of MessageDialog.ShowModal()
    """
    if style is None:
        style = wx.OK|wx.ICON_INFORMATION
    dlg = wx.MessageDialog(parent, message, title, style)
    ret = dlg.ShowModal()
    dlg.Destroy()
    return ret

def empty_bitmap(width, height, value=255):
    """return empty wx.BitMap"""
    data = array.array('B', [value]*3*width*height)
    return wx.BitmapFromBuffer(width, height, data)

def fix_filename(fname):
    """
    fix string to be a 'good' filename. This may be a more
    restrictive than the OS, but avoids nasty cases.
    """
    bchars = ' <>:"\'\\\t\r\n/|?*!%$'
    out = fname.translate(maketrans(bchars, '_'*len(bchars)))
    if out[0] in '-,;[]{}()~`@#':
        out = '_%s' % out
    return out


def FileOpen(parent, message, default_dir=None,
             default_file=None, multiple=False,
             wildcard=None):
    """File Open dialog wrapper.
    returns full path on OK or None on Cancel
    """
    out = None
    if default_dir is None:
        default_dir = os.getcwd()
    if wildcard is None:
        wildcard = 'All files (*.*)|*.*'

    style = wx.OPEN|wx.CHANGE_DIR
    if multiple:
        style = style|wx.MULTIPLE
    dlg = wx.FileDialog(parent, message=message,
                        defaultFile=default_file,
                        defaultDir=default_dir,
                        wildcard=wildcard,
                        style=style)

    out = None
    if dlg.ShowModal() == wx.ID_OK:
        out = os.path.abspath(dlg.GetPath())
    dlg.Destroy()
    return out

def FileSave(parent, message, default_file=None,
             default_dir=None,   wildcard=None):
    "File Save dialog"
    out = None
    if wildcard is None:
        wildcard = 'All files (*.*)|*.*'

    if default_dir is None:
        default_dir = os.getcwd()

    dlg = wx.FileDialog(parent, message=message,
                        defaultFile=default_file,
                        wildcard=wildcard,
                        style=wx.SAVE|wx.CHANGE_DIR)
    if dlg.ShowModal() == wx.ID_OK:
        out = os.path.abspath(dlg.GetPath())
    dlg.Destroy()
    return out


def SelectWorkdir(parent,  message='Select Working Folder...'):
    "prompt for and change into a working directory "
    dlg = wx.DirDialog(parent, message,
                       style=wx.DD_DEFAULT_STYLE|wx.DD_CHANGE_DIR)

    path = os.path.abspath(os.curdir)
    dlg.SetPath(path)
    if  dlg.ShowModal() == wx.ID_CANCEL:
        return None
    path = os.path.abspath(dlg.GetPath())
    dlg.Destroy()
    os.chdir(path)
    return path

class Closure:
    """A very simple callback class to emulate a closure (reference to
    a function with arguments) in python.

    This class holds a user-defined function to be executed when the
    class is invoked as a function.  This is useful in many situations,
    especially for 'callbacks' where lambda's are quite enough.
    Many Tkinter 'actions' can use such callbacks.

    >>>def my_action(x=None):
    ...    print('my action: x = ', x)
    >>>c = Closure(my_action,x=1)
    ..... sometime later ...
    >>>c()
     my action: x = 1
    >>>c(x=2)
     my action: x = 2

    based on Command class from J. Grayson's Tkinter book.
    """
    def __init__(self, func=None, *args, **kws):
        self.func  = func
        self.kws   = kws
        self.args  = args

    def __call__(self,  *args, **kws):
        self.kws.update(kws)
        if hasattr(self.func, '__call__'):
            self.args = args
            return self.func(*self.args, **self.kws)


class FloatCtrl(wx.TextCtrl):
    """ Numerical Float Control::
    a wx.TextCtrl that allows only numerical input, can take a precision argument
    and optional upper / lower bounds
    Options:

    """
    def __init__(self, parent, value='', minval=None, maxval=None,
                 precision=3, bell_on_invalid = True,
                 act_on_losefocus=False,
                 action=None, action_kw=None, **kws):

        self.__digits = '0123456789.-'
        self.__prec   = precision
        if precision is None:
            self.__prec = 0
        self.format   = '%%.%if' % self.__prec
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
        if action_kw is None:
            action_kw = {}
        self.SetAction(action, **action_kw)

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
            self.__action = Closure(action, **kws)

    def SetPrecision(self, prec=0):
        "set precision"
        self.__prec = prec
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
        pos   = wx.TextCtrl.GetSelection(self)
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

        has_minus = '-' in entry
        ckey = chr(key)
        if ((ckey == '.' and (self.__prec == 0 or '.' in entry) ) or
            (ckey == '-' and (has_minus or  pos[0] != 0)) or
            (ckey != '-' and  has_minus and pos[0] == 0)):
            return
        # 4. allow digits, but not other characters
        if chr(key) in self.__digits:
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
            return set_float(fpformat.fix(self.__val, self.__prec))
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

class SimpleText(wx.StaticText):
    "simple static text wrapper"
    def __init__(self, parent, label, minsize=None,
                 font=None, colour=None, bgcolour=None,
                 style=wx.ALIGN_CENTRE,  **kws):

        wx.StaticText.__init__(self, parent, -1,
                               label=label, style=style, **kws)

        if minsize is not None:
            self.SetMinSize(minsize)
        if font is not None:
            self.SetFont(font)
        if colour is not None:
            self.SetForegroundColour(colour)
        if bgcolour is not None:
            self.SetBackgroundColour(colour)

class HyperText(wx.StaticText):
    """HyperText is a simple extension of wx.StaticText that

       1. adds an underscore to the lable to appear to be a hyperlink
       2. performs the supplied action on Left-Up button events
    """
    def  __init__(self, parent, label, action=None, colour=(50, 50, 180)):
        self.action = action
        wx.StaticText.__init__(self, parent, -1, label=label)
        font  = self.GetFont() # .Bold()
        font.SetUnderlined(True)
        self.SetFont(font)
        self.SetForegroundColour(colour)
        self.Bind(wx.EVT_LEFT_UP, self.OnSelect)

    def OnSelect(self, evt=None):
        "Left-Up Event Handler"
        if self.action is not None:
            self.action(evt=evt, label=self.GetLabel())
        evt.Skip()

class DateTimeCtrl(object):
    """
    Simple Combined date/time control
    """
    def __init__(self, parent, name='datetimectrl', use_now=False):
        self.name = name
        panel = self.panel = wx.Panel(parent)
        bgcol = wx.Colour(250, 250, 250)

        datestyle = wx.DP_DROPDOWN|wx.DP_SHOWCENTURY|wx.DP_ALLOWNONE

        self.datectrl = wx.DatePickerCtrl(panel, size=(120, -1),
                                          style=datestyle)
        self.timectrl = masked.TimeCtrl(panel, -1, name=name,
                                        limited=False,
                                        fmt24hr=True, oob_color=bgcol)
        timerheight = self.timectrl.GetSize().height
        spinner = wx.SpinButton(panel, -1, wx.DefaultPosition,
                                (-1, timerheight), wx.SP_VERTICAL )
        self.timectrl.BindSpinButton(spinner)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.datectrl, 0, wx.ALIGN_CENTER)
        sizer.Add(self.timectrl, 0, wx.ALIGN_CENTER)
        sizer.Add(spinner, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT)
        panel.SetSizer(sizer)
        sizer.Fit(panel)
        if use_now:
            self.timectrl.SetValue(wx.DateTime_Now())

