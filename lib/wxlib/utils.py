import wx
from collections import OrderedDict

is_wxPhoenix = 'phoenix' in wx.PlatformInfo

def SetTip(wid, msg):
    "set tooltip message"
    wid.SetToolTip(wx.ToolTip(msg))

def BitmapButton(parent, bmp, action=None, tooltip=None,
                 size=(20, 20), **kws):
    b = wx.BitmapButton(parent, -1, bmp, size=size, **kws)
    if action is not None:
        parent.Bind(wx.EVT_BUTTON, action, b)
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

        self.SetBackgroundColour(wx.Colour(248, 248, 235))
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
