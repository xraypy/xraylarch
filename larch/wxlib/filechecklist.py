import wx

class FileDropTarget(wx.FileDropTarget):
    def __init__(self, main):
        wx.FileDropTarget.__init__(self)
        self.reader = getattr(main, 'onRead', None)

    def OnDropFiles(self, x, y, filenames):
        if self.reader is not None:
            for file in filenames:
                self.reader(file)
        return (self.reader is not None)

class FileCheckList(wx.CheckListBox):
    """
    A ListBox with pop-up menu to arrange order of
    items and remove items from list
    supply select_action for EVT_LISTBOX selection action
    """
    def __init__(self, parent, main=None, select_action=None,
                 right_click=True, remove_action=None,
                 pre_actions=None, post_actions=None,
                 custom_key_bindings={}, with_remove_from_list=True,  **kws):

        wx.CheckListBox.__init__(self, parent, **kws)
        self.SetDropTarget(FileDropTarget(main))

        if select_action is not None:
            self.Bind(wx.EVT_LISTBOX,  select_action)
        self.Bind(wx.EVT_CHECKLISTBOX, self.check_event)
        self.Bind(wx.EVT_KEY_DOWN, self.key_event)

        self.remove_action = remove_action
        self.rclick_actions = {}

        core_actions = [("Select All",         self.select_all, "ctrl+A"),
                        ("Select All above",   self.select_allabove, "ctrl+shift+up"),
                        ("Select All below",   self.select_allbelow, "ctrl+shift+down"),
                        ("Select None",        self.select_none, "ctrl+D"),
                        ("Select None above",  self.select_noneabove,  "ctrl+shift+left"),
                        ("Select None below",  self.select_nonebelow, "ctrl+shift+right"),
                        ("--sep--", None, None),
                        ("Move up",           self.move_up, "cmd+up"),
                        ("Move down",         self.move_down, "cmd+down"),
                        ("Move to Top",       self.move_to_top, "cmd+left"),
                        ("Move to Bottom",    self.move_to_bottom, "cmd+right")]
        if with_remove_from_list:
            core_actions.append(("--sep--", None, None))
            core_actions.append(("Remove from List", self.remove_from_list, "alt-+del"))

        click_actions =  []
        if pre_actions is not None:
            click_actions.extend(pre_actions)
            click_actions.append(("--sep--", None, None))
        click_actions.extend(core_actions)
        if post_actions is not None:
            click_actions.append(("--sep--", None, None))

            click_actions.extend(post_actions)
        click_actions.append(("--sep--", None, None))
        self.key_bindings = {}
        if right_click:
            self.Bind(wx.EVT_RIGHT_DOWN, self.onRightClick)
            for dat in click_actions:
                keybind = None
                title = dat[0]
                action = dat[1]
                if len(dat) == 3:
                    keybind = dat[2]
                if title in custom_key_bindings:
                    keybind = custom_key_bindings[title]
                if keybind is not None:
                    self.key_bindings[keybind] = action
                self.rclick_actions[title] = action
                self.Bind(wx.EVT_MENU, self.onRightEvent)

    def key_event(self, evt=None):
        thiskey = evt.GetKeyCode()
        arrows = {wx.WXK_LEFT: 'left', wx.WXK_RIGHT: 'right',
                  wx.WXK_UP: 'up',  wx.WXK_DOWN: 'down'}
        key = arrows.get(thiskey, chr(thiskey))
        if evt.HasAnyModifiers():
            mod = evt.GetModifiers()
            if evt.AltDown():
                key = f'alt+{key}'
                mod -= 1
            if evt.ShiftDown():
                key = f'shift+{key}'
                mod -= 4
            if evt.MetaDown():
                key = f'meta+{key}'

            if mod == 2:
                key = f'cmd+{key}'
            elif mod == 16:
                key = f'ctrl+{key}'

        action = self.key_bindings.get(key, None)
        if action is not None:
            action()

    def check_event(self, evt=None):
        index = evt.GetSelection()
        label = self.GetString(index)

    def onRightClick(self, evt=None):
        menu = wx.Menu()
        self.rclick_wids = {}
        for label, action in self.rclick_actions.items():
            if label == '--sep--':
                menu.AppendSeparator()
            else:
                wid = menu.Append(-1, label)
                self.rclick_wids[wid.Id] = action
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
        action = self.rclick_wids[event.GetId()]
        if action is not None:
            action(event=event)


    def refresh(self, names):
        self.Clear()
        for name in names:
            self.Append(name)

    def _get_current(self):
        idx, names = self.GetSelection(), self.GetItems()
        return idx, names, names[idx]

    def remove_from_list(self, event=None):
        idx, names, this =  self._get_current()
        if idx > -1:
            names.pop(idx)
            if self.remove_action is not None:
                self.remove_action(this)
            self.refresh(names)

    def move_up(self, event=None):
        idx, names, this =  self._get_current()
        if idx > 0:
            names.pop(idx)
            names.insert(idx-1, this)
            self.refresh(names)

    def move_down(self, event=None):
        idx, names, this =  self._get_current()
        if idx > -1 and idx < len(names):
            names.pop(idx)
            names.insert(idx+1, this)
            self.refresh(names)

    def move_to_top(self, event=None):
        idx, names, this =  self._get_current()
        if idx > -1:
            names.pop(idx)
            names.insert(0, this)
            self.refresh(names)

    def move_to_bottom(self, event=None):
        idx, names, this =  self._get_current()
        if idx > -1:
            names.pop(idx)
            names.append(this)
            self.refresh(names)

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
