import wx
from collections import OrderedDict

is_wxPhoenix = 'phoenix' in wx.PlatformInfo

def SetTip(wid, msg):
    "set tooltip message"
    wid.SetToolTip(wx.ToolTip(msg))

def BitmapButton(parent, bmp, action=None, tooltip=None, size=(20, 20), **kws):
    b = wx.BitmapButton(parent, id=-1, bitmap=bmp, size=size, **kws)
    if action is not None:
        parent.Bind(wx.EVT_BUTTON, action, b)
    if tooltip is not None:
        if is_wxPhoenix:
            b.SetToolTip(tooltip)
        else:
            b.SetToolTipString(tooltip)
    return b

def ToggleButton(parent, label, action=None, tooltip=None,
                 size=(25, 25), **kws):
    b = wx.ToggleButton(parent, -1, label, size=size, **kws)
    if action is not None:
        b.Bind(wx.EVT_TOGGLEBUTTON, action)
    if tooltip is not None:
        if is_wxPhoenix:
            b.SetToolTip(tooltip)
        else:
            b.SetToolTipString(tooltip)
    return b


class FileDropTarget(wx.FileDropTarget):
    def __init__(self, main):
        wx.FileDropTarget.__init__(self)
        self.main = main

    def OnDropFiles(self, x, y, filenames):
        for file in filenames:
            if hasattr(self.main, 'onRead'):
                self.main.onRead(file)

class FileCheckList(wx.CheckListBox):
    """
    A ListBox with pop-up menu to arrange order of
    items and remove items from list
    supply select_action for EVT_LISTBOX selection action

    """
    right_click_actions = ("Move up",
                           "Move down",
                           "Move to Top",
                           "Move to Bottom",
                           "Remove from List")

    def __init__(self, parent, main=None, select_action=None,
                 right_click=True, remove_action=None,
                 custom_actions=None, **kws):

        wx.CheckListBox.__init__(self, parent, **kws)

        self.SetDropTarget(FileDropTarget(main))

        self.SetBackgroundColour((250, 250, 250, 255))
        self.SetForegroundColour((5, 5, 85, 255))
        if select_action is not None:
            self.Bind(wx.EVT_LISTBOX,  select_action)
        self.remove_action = remove_action
        self.rclick_actions = OrderedDict()
        if right_click:
            self.Bind(wx.EVT_RIGHT_DOWN, self.onRightClick)
            for title in self.right_click_actions:
                wid = wx.NewId()
                self.rclick_actions[wid] = (title, None)
                self.Bind(wx.EVT_MENU, self.onRightEvent, id=wid)

        if custom_actions is not None:
            for title, action in custom_actions:
                wid = wx.NewId()
                self.rclick_actions[wid] = (title, action)
                self.Bind(wx.EVT_MENU, self.onRightEvent, id=wid)

    def onRightClick(self, evt=None):
        menu = wx.Menu()
        for wid, val in self.rclick_actions.items():
            menu.Append(wid, val[0])

        self.PopupMenu(menu)
        menu.Destroy()

    def rename_item(self, old, new):
        names = self.GetItems()
        if old not in names:
            return
        i = names.index(old)
        names[i] = new
        self.Clear()
        for name in names:
            self.Append(name)

    def onRightEvent(self, event=None):
        idx = self.GetSelection()
        if idx < 0: # no item selected
            return
        names = self.GetItems()
        this  = names[idx] # .pop(idx)

        label, action = self.rclick_actions[event.GetId()]
        if label == "Move up" and idx > 0:
            names.pop(idx)
            names.insert(idx-1, this)
        elif label == "Move down" and idx < len(names):
            names.pop(idx)
            names.insert(idx+1, this)
        elif label == "Move to Top":
            names.pop(idx)
            names.insert(0, this)
        elif label == "Move to Bottom":
            names.pop(idx)
            names.append(this)
        elif label == "Remove from List":
            names.pop(idx)
            if self.remove_action is not None:
                self.remove_action(this)
        elif action is not None:
            action(this)

        self.Clear()
        for name in names:
            self.Append(name)

class GridPanel(wx.Panel):
    """A simple panel with a GridBagSizer"""

    def __init__(self, parent, nrows=10, ncols=10, pad=2, gap=5,
                 itemstyle = wx.ALIGN_CENTER, **kws):
        wx.Panel.__init__(self, parent, **kws)
        self.sizer = wx.GridBagSizer(nrows, ncols)
        self.sizer.SetVGap(gap)
        self.sizer.SetHGap(gap)

        self.irow = 0
        self.icol = 0
        self.itemstyle = itemstyle
        self.pad=pad

    def Add(self, item, irow=None, icol=None, drow=1, dcol=1, style=None,
            newrow=False, pad=None, **kws):
        """add item with default values for col, row, and size"""
        # print 'Sizer Add ', style, self.itemstyle, LEFT, item
        if newrow:
            self.NewRow()
        if style is None:
            style = self.itemstyle
        if irow is None:
            irow = self.irow
        if pad is None:
            pad = self.pad
        if icol is None:
            icol = self.icol
        self.sizer.Add(item, (irow, icol), (drow, dcol), style, pad, **kws)
        self.icol = self.icol + dcol

    def AddMany(self, items, newrow=False, **kws):
        """add items"""
        if newrow: self.NewRow()
        for item in items:
            self.Add(item, **kws)

    def AddManyText(self, items, newrow=False, **kws):
        """add items"""
        if newrow: self.NewRow()
        for item in items:
            self.AddText(item, **kws)

    def NewRow(self):
        "advance row, set col # = 0"
        self.irow += 1
        self.icol = 0

    def AddText(self, label, newrow=False, dcol=1, style=None, **kws):
        """add a Simple StaticText item"""
        if style is None:
            style = LCEN
        self.Add(SimpleText(self, label, style=style, **kws),
                 dcol=dcol, style=style, newrow=newrow)

    def pack(self):
        tsize = self.GetSize()
        msize = self.GetMinSize()

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)
        nsize = (10*int(1.1*(max(msize[0], tsize[0])/10)),
                 10*int(1.1*(max(msize[1], tsize[1])/10.)))
        self.SetSize(nsize)
