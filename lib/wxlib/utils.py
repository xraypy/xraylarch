import wx

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
    def __init__(self, parent, main=None,
                 select_action=None,
                 right_click=True,
                 remove_action=None, **kws):
        wx.CheckListBox.__init__(self, parent, **kws)

        self.SetDropTarget(FileDropTarget(main))

        self.SetBackgroundColour(wx.Colour(248, 248, 235))
        if select_action is not None:
            self.Bind(wx.EVT_LISTBOX,  select_action)
        self.remove_action = remove_action
        if right_click:
            self.Bind(wx.EVT_RIGHT_DOWN, self.onRightClick)
            for item in ('popup_up1', 'popup_dn1',
                         'popup_upall', 'popup_dnall', 'popup_remove'):
                setattr(self, item,  wx.NewId())
                self.Bind(wx.EVT_MENU, self.onRightEvent,
                          id=getattr(self, item))

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
