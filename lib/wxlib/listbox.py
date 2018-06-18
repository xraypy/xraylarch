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

    def onRightClick(self, evt=None):
        menu = wx.Menu()
        self.pmenu_labels = {}
        for menulabel in ('Move up', 'Move down', 'Move to top',
                          'Move to bottom', 'Remove from list'):
            item = menu.Append(-1, menulabel)
            self.pmenu_labels[item.Id] = menulabel
            self.Bind(wx.EVT_MENU, self.onRightEvent, item)
        self.PopupMenu(menu)
        menu.Destroy()

    def onRightEvent(self, event=None):
        idx = self.GetSelection()
        mlabel = self.pmenu_labels.get(event.GetId(), None)
        if idx < 0 or mlabel is None:
            return

        names = self.GetItems()
        this  = names.pop(idx)

        if mlabel == 'Move up' and idx > 0:
            names.insert(idx-1, this)
        elif mlabel == 'Move down' and idx < len(names):
            names.insert(idx+1, this)
        elif mlabel == 'Move to top':
            names.insert(0, this)
        elif mlabel == 'Move to bottom':
            names.append(this)
        elif mlabel == 'Remove from list' and self.remove_action is not None:
            self.remove_action(this)

        self.Clear()
        for name in names:
            self.Append(name)
