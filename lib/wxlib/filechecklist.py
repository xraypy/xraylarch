import wx
from collections import OrderedDict

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
            for title, action in (("Move up", None),
                                  ("Move down", None),
                                  ("Move to Top", None),
                                  ("Move to Bottom", None),
                                  ("Remove from List", None),
                                  ("--sep--", None),
                                  ("Select All",        self.select_all),
                                  ("Select All above",  self.select_allabove),
                                  ("Select All below",  self.select_allbelow),
                                  ("Select None",       self.select_none),
                                  ("Select None above", self.select_noneabove),
                                  ("Select None below", self.select_nonebelow)):
                self.rclick_actions[title] = action
                self.Bind(wx.EVT_MENU, self.onRightEvent)

    def onRightClick(self, evt=None):
        menu = wx.Menu()
        self.rclick_wids = {}
        for label, action in self.rclick_actions.items():
            if label == '--sep--':
                menu.AppendSeparator()
            else:
                wid = menu.Append(-1, label)
                self.rclick_wids[wid.Id] = (label, action)
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
        this  = names[idx]
        do_relist = False

        label, action = self.rclick_wids[event.GetId()]
        if label == "Move up" and idx > 0:
            names.pop(idx)
            names.insert(idx-1, this)
            do_relist = True
        elif label == "Move down" and idx < len(names):
            names.pop(idx)
            names.insert(idx+1, this)
            do_relist = True
        elif label == "Move to Top":
            names.pop(idx)
            names.insert(0, this)
            do_relist = True
        elif label == "Move to Bottom":
            names.pop(idx)
            names.append(this)
            do_relist = True
        elif label == "Remove from List":
            names.pop(idx)
            if self.remove_action is not None:
                self.remove_action(this)
            do_relist = True
        elif action is not None:
            action(event=event)

        if do_relist:
            self.Clear()
            for name in names:
                self.Append(name)

    def select_all(self, event=None):
        self.SetCheckedStrings(self.GetStrings())

    def select_none(self, event=None):
        self.SetCheckedStrings([])

    def select_allabove(self, event=None, name=None):
        self._alter_list(select=True, reverse=False)

    def select_allbelow(self, event=None, name=None):
        self._alter_list(select=True, reverse=True)

    def select_noneabove(self, event=None):
        self._alter_list(select=False, reverse=False)

    def select_nonebelow(self, event=None):
        self._alter_list(select=False, reverse=True)

    def _alter_list(self, select=True, reverse=False):
        all = list(self.GetStrings())
        if reverse:
            all.reverse()

        this = self.GetStringSelection()
        slist = list(self.GetCheckedStrings())
        for name in all:
            if select and name not in slist:
                slist.append(name)
            elif not select and name in slist:
                slist.remove(name)
            if name == this:
                break
        self.SetCheckedStrings(slist)
