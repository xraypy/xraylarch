"""
wx utils
"""
import os
import array
import fpformat
from string import maketrans

import wx
import wx.lib.masked as masked
from wx.lib.embeddedimage import PyEmbeddedImage
import numpy as np

def pack(window, sizer):
    "simple wxPython Pack"
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

def addtoMenu(parent, menu, label, longtext, action=None):
    "add label-with-action to menu"
    wid = wx.NewId()
    menu.Append(wid, label, longtext)
    if hasattr(action, '__call__'):
        wx.EVT_MENU(parent, wid, action)

def add_choice(panel, choices, default=0, action=None, **kws):
    "add simple button with bound action"
    c = wx.Choice(panel, -1,  choices=choices, **kws)
    c.Select(default)
    c.Bind(wx.EVT_CHOICE, action)
    return c

def add_checkbox(panel, label, check=True, action=None, **kws):
    "add simple checkbox with bound action"
    c = wx.CheckBox(panel, -1,  label=label, **kws)
    c.SetValue({True:1, False:0}[check])
    c.Bind(wx.EVT_CHECKBOX, action)
    return c

def set_choices(choicebox, choices):
    index = 0
    try:
        current = choicebox.GetStringSelection()
        if current in choices:
            index = choices.index(current)
    except:
        pass
    choicebox.Clear()
    choicebox.AppendItems(choices)
    choicebox.SetStringSelection(choices[index])

def popup(parent, message, title, style=None):
    """generic popup message dialog, returns
    output of MessageDialog.ShowModal()
    """
    if style is None:
        style = wx.OK|wx.ICON_INFORMATION
    dlg = wx.MessageDialog(parent, message, title, style)
    ret = dlg.ShowModal()
    dlg.Destroy()
    if style == wx.YES_NO:
        ret = (ret == wx.ID_YES)
    return ret

def empty_bitmap(width, height, value=255):
    "return empty wx.BitMap"
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

class EditableListBox(wx.ListBox):
    """
    A ListBox with pop-up menu to arrange order of
    items and remove items from list
    supply select_action for EVT_LISTBOX selection action
    """
    def __init__(self, parent, select_action, right_click=True,
                 remove_action=None, **kws):
        wx.ListBox.__init__(self, parent, **kws)

        self.SetBackgroundColour(wx.Colour(248, 248, 235))
        self.Bind(wx.EVT_LISTBOX,  select_action)
        self.remove_action = remove_action
        if right_click:
            self.Bind(wx.EVT_RIGHT_DOWN, self.onRightClick)
            for item in ('popup_up1', 'popup_dn1',
                         'popup_upall', 'popup_dnall', 'popup_remove'):
                setattr(self, item,  wx.NewId())
                self.Bind(wx.EVT_MENU, self.onRightEvent, id=getattr(self, item))

    def onRightClick(self, evt=None):
        menu = wx.Menu()
        menu.Append(self.popup_up1,    "Move up")
        menu.Append(self.popup_dn1,    "Move down")
        menu.Append(self.popup_upall,  "Move to top")
        menu.Append(self.popup_dnall,  "Move to bottom")
        menu.Append(self.popup_remove, "Remove from list")
        self.PopupMenu(menu)
        menu.Destroy()

    def onRightEvent(self, event=None):
        idx = self.GetSelection()
        if idx < 0: # no item selected
            return
        wid   = event.GetId()
        names = self.GetItems()
        this  = names.pop(idx)
        if wid == self.popup_up1 and idx > 0:
            names.insert(idx-1, this)
        elif wid == self.popup_dn1 and idx < len(names):
            names.insert(idx+1, this)
        elif wid == self.popup_upall:
            names.insert(0, this)
        elif wid == self.popup_dnall:
            names.append(this)
        elif wid == self.popup_remove and self.remove_action is not None:
            self.remove_action(this)

        self.Clear()
        for name in names:
            self.Append(name)

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
                 style=None, **kws):
        if style is None:
            style = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
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
    def  __init__(self, parent, label, action=None, style=None,
                  colour=(50, 50, 180), **kws):
        self.action = action
        wx.StaticText.__init__(self, parent, -1, label=label, style=style, **kws)
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
    """Combined date/time control
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



def set_float(val):
    """ utility to set a floating value,
    useful for converting from strings """
    out = None
    if not val in (None, ''):
        try:
            out = float(val)
        except ValueError:
            return None
        if np.isnan(out):
            out = default
    return out

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

class LabelEntry(wx.TextCtrl):
    """
    simple extension of TextCtrl.  Typical usage:
       entry = LabelEntry(self, -1, value='22', color='black',
                          labeltext='X = ',labelbgcolor='green',
                          style=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE)
       row   = wx.BoxSizer(wx.HORIZONTAL)
       row.Add(entry.label, 1,wx.ALIGN_LEFT|wx.EXPAND)
       row.Add(entry,    1,wx.ALIGN_LEFT|wx.EXPAND)

    """
    def __init__(self,parent, value, size=-1,
                 font=None, action=None,
                 bgcolor=None, color=None, style=None,
                 labeltext=None, labelsize=-1,
                 labelcolor=None, labelbgcolor=None):

        if style is None:
            style=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE|wx.TE_PROCESS_ENTER
        if action is None:
            action = self.GetValue
        self.action = action

        if labeltext is not None:
            self.label = wx.StaticText(parent, -1, labeltext,
                                       size = (labelsize,-1),
                                       style = style)
            if labelcolor:
                self.label.SetForegroundColour(labelcolor)
            if labelbgcolor:
                self.label.SetBackgroundColour(labelbgcolor)
            if font is not None:
                self.label.SetFont(font)

        try:
            value = str(value)
        except:
            value = ' '

        wx.TextCtrl.__init__(self, parent, -1, value,
                             size=(size,-1),style=style)

        self.Bind(wx.EVT_TEXT_ENTER, self.__act)
        self.Bind(wx.EVT_KILL_FOCUS, self.__act)
        if font is not None:
            self.SetFont(font)
        if color:
            self.SetForegroundColour(color)
        if bgcolor:
            self.SetBackgroundColour(bgcolor)

    def __act(self,event=None):
        self.action(event=event)
        val = self.GetValue()
        event.Skip()
        return val


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
        value = set_float(value)
        if value is not None:
            wx.TextCtrl.SetValue(self, self.format % value)

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

_BMPS = {"leftarrow": """iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAIAAABvFaqvAAAACXBIWXMAAAxMAAAMTAEAiU+qAAAACXZwQWcAAAAYAAAAGAB4TKWmAAAB3UlEQVQ4y6VVO27bUBCc/YiFgcBllDZXsK+U3gewxI9dJQjgs9iNG3eukhOkD0DGCAzIQGBZfLubgpIiyw7JIFM+koOZnTdLWlooIQJ7IMAczBgEEVJAhSAE0LNnHa2MYNm+z3ihJQIIWIqrq4fl0tcng0ytxS7co209Ik5Ovh8ff3MPs3CPfrQWvKfFHap0dvbj4qI+OBCiIS0b8HOWEEFZNvN5zaxjOQAQdMtiFqqU501V1Vmmq1Vy34xscEQBBf1xVBRNVdUi2n3c+RIZJpoQFIFAiFBVNWVZq4rZWkPbxmLhT09OBOqdlgXoaeXZhIqiKctaRN1j62UyocNDjkAEengikGVEEXF+3sxm+yw7N2QYqiR3Pz98+ninKu6vFWUcsmxMl8ZBvn75LIKbmwd5PZ5R1gDoqo3T02lK+MuwZeSwlYXcoyimzMjzLn4ww8yOjt5cX78fGb+CQCAzzOdT97UuZpit49+tUZ81BIjBjJSiKKYR6C43NuUwAxH625ti0zUiiJBZlOWUGUXRMFMXacfST0S7sonATGbI82lVvXNP/xD+VtEOF1KK2ezt/X26vf01pvpr7G3Ibkl2e/LycvH4aN3J4Iak1kPppdK185FIAbUA4X9/Rxb4DQ6meRDp8UWOAAAAJXRFWHRjcmVhdGUtZGF0ZQAyMDEwLTExLTEyVDExOjM0OjQ1LTA2OjAwXhFyIAAAACV0RVh0bW9kaWZ5LWRhdGUAMjAxMC0xMS0xMlQxMDo0Nzo0MS0wNjowMOp1VwIAAAAddEVYdFNvZnR3YXJlAEdQTCBHaG9zdHNjcmlwdCA4LjcxAz9oNAAAAABJRU5ErkJggg==""",
"rightarrow": """iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAIAAABvFaqvAAAACXBIWXMAAAxMAAAMTAEAiU+qAAAACXZwQWcAAAAYAAAAGAB4TKWmAAABxklEQVQ4y61VS04bQRSs1/0MiDUoM/fgEBwlyooDWPOxL8BZ4BJsoyiLbLKKZEhWThaYmX6vshgDNgZPR6RWLc1Tqaq6+o2sjCogMQp3xIDdQREkQqMgCiDjRHhk2Z3l88e3MYhdrfz6+rclgq/JJ9Ab98OdZnTn2dm3i4sfJPve3bdmemPIsLQO4vg4Xl4u5vM7VXF/qStkpfM0HbSqFm17GyPcucml5EhKfAzFHe48ONCmWbijbYuUGKOIAIBOxsyJbB1IxKiz2UIETVOYIQRAoHe/LO51R5LE4WHoewJwpztUY9suQkBVFe4ERIria9dRZA8RRCCC5dIHrkFdCGKW6rpsmqLrKaqfU8roNfCiiU9c83k5nRZydPTl4cFzaHZ7KIIYYeYfP53m9mgUmtJ2H/7RWkpra3pyou8Mezotup5y+zNlXv/5+febmz8xRnfEiJSsbcvh+h2iH05jZgqTiQAIQQCklOq6rKqhkAJAe4eOKBravL41EZilqiqbZuOJOHTwn4MQEIJ0nTVNWdeF2fNDQ85i24R7ms0GFoQgWwr+12LLIiJ5f29XV8uB4gXLQCS9U7N321vLPxFqhOC9vyMj/gJsaMELYgNmYQAAACV0RVh0Y3JlYXRlLWRhdGUAMjAxMC0xMS0xMlQxMTozNDo0NS0wNjowMF4RciAAAAAldEVYdG1vZGlmeS1kYXRlADIwMTAtMTEtMTJUMTA6NDc6MzYtMDY6MDAlF2CVAAAAHXRFWHRTb2Z0d2FyZQBHUEwgR2hvc3RzY3JpcHQgOC43MQM/aDQAAAAASUVORK5CYII=""",
"uparrow": """iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAIAAABvFaqvAAAACXBIWXMAAAxMAAAMTAEAiU+qAAAACXZwQWcAAAAYAAAAGAB4TKWmAAAB3klEQVQ4y+2VMW7bQBBF/3CHkhrFCFwlKV2l9gF8Al8k6dy5IkEV7twld1GlE1gG3aRymVAuXBiGERq7Mz8FEUoiBQRIm/yKnP3zwJmd5UprVAGJPQlAmHGay6fP3wF8/fLhNTIE6Zb2vIJEIDrHcqcZSS6qBrgFbhdVQ9KMfsgfnYh2gJKSkyzLBliHUIdQA+uybEim5GNWtBHInTE6yaLoKHcitUgdwh2wLoqGZIxD1hDkzpQ4oAA1MGSltFfjHmhQkWrdU3qW6uEaozHrOk/CjCFIUWzKsglBzYZbScIMIWhZNkWxCUHM2HsyCEiIQFUWi4eq2kwmKoIsw1hZBhFMJlpVm8XiQVWkGx2BRGMQxMjLyx/X1w2gO3MSRijbmbR0cfHu6up9nosR6g5VLJfPq9XL2dlbd5AIAa+vvLn5GeO2vDyX09P5dCpm6D55tXpZLp/Pz9+4QaJRM7Stz2Z7xTw9+cnJt8fHJCIASB4f6/39x6OjPVuXmBzavc9mmfu2qSJoWx83u219Ps86Q5/YPehu8m5Tu74OzlQXd98u9YnamwaSceh3UOSA/9Am/5X+g/5pkEL+4BheMAclUCNk1y2gIw9wQFVCkDzPAMToqtIdx+SQbPuzEYERvwBwYMALE1tK0wAAACV0RVh0Y3JlYXRlLWRhdGUAMjAxMC0xMS0xMlQxMTozNDo0NS0wNjowMF4RciAAAAAldEVYdG1vZGlmeS1kYXRlADIwMTAtMTEtMTJUMTA6NDc6MzEtMDY6MDDgsF4bAAAAHXRFWHRTb2Z0d2FyZQBHUEwgR2hvc3RzY3JpcHQgOC43MQM/aDQAAAAASUVORK5CYII=""",
"downarrow": """iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAIAAABvFaqvAAAACXBIWXMAAAxMAAAMTAEAiU+qAAAACXZwQWcAAAAYAAAAGAB4TKWmAAAB4UlEQVQ4y+2Vv3LTQBDGv72TYleuPDiBB6BheI40eRHo0qWQ5NhFunTwMnkHZ+yhoaEDAePKQ2HrbvejOFuOZTOhh280o9H++d3tanWStTITkNhKQEPu8XOpb998Xi5jnjsAIdhwmC0+vX4x9EEhDtiliCASmRd4AQSt6ADAATFSlaqWzDEmDzIH6aQArgX/SSIQeSYGhHsu5G/1H/RPg7J045OxJCEC8sSkJmPHk8Y1ax/M9iAzmHUTTtrdrqQtaL22fv+gzH7fdb4MEfT7zh02o03MzACHh4dfVfV9MPBpQe+x2XC1MkB268tqZZeXX3o9UYUInMNqpbe351dXAzNIUHpBCLy5+XZ/XwPZ/oCAP+qStvsD4vX1xd3dyzwXJSQY/a5h0+mPsqzPztK+qNrFeA8RcQ5No5PJRVGMUu80HSMiIBEji2JUludNE1Nfj5UKb5pYludFMYqR6RWDQFAmmTFGIzke18Asy+Yic2B/icyzbA7MxuOaZIxmts0Nyj1oxyLJqqqBmfeLliUy934BzKoqUdhSToASKwTrsDqUEOwp5TTouEbv596frugQdGRNLFWSnE5q4BF4nE5qkqq0U/HBKN3fUTslhCp7ubx7/xXAxw+vNoHeS3J1Jj4SvwHUp92N41HPcAAAACV0RVh0Y3JlYXRlLWRhdGUAMjAxMC0xMS0xMlQxMTozNDo0NS0wNjowMF4RciAAAAAldEVYdG1vZGlmeS1kYXRlADIwMTAtMTEtMTJUMTA6NDc6NDUtMDY6MDAeOnMRAAAAHXRFWHRTb2Z0d2FyZQBHUEwgR2hvc3RzY3JpcHQgOC43MQM/aDQAAAAASUVORK5CYII=""",

}

def get_icon(name):
    if name in _BMPS:
        val = _BMPS[name]
        return  wx.BitmapFromImage(PyEmbeddedImage(val).GetImage())
    return None
