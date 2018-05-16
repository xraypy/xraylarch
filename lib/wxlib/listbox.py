import wx

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
