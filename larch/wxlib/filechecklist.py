import wx
from pyshortcuts import uname

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
        alt = "ctrl+alt" if uname == "darwin" else "alt"
        aname = "Ctrl+Alt" if uname == "darwin" else "Alt"


        core_actions = [("Select All\tCtrl+A",         self.select_all, "ctrl+A"),
                        ("Select All above\tCtrl+Shift+Up",   self.select_allabove, "ctrl+shift+up"),
                        ("Select All below\tCtrl+Shift+Down",   self.select_allbelow, "ctrl+shift+down"),
                        ("Select None\tCtrl+D",        self.select_none, "ctrl+D"),
                        ("Select None above\tCtrl+Shift+Left",  self.select_noneabove,  "ctrl+shift+left"),
                        ("Select None below\tCtrl+Shift+Right",  self.select_nonebelow, "ctrl+shift+right"),
                        ("--sep--", None, None),
                        (f"Move up\t{aname}+Up",           self.move_up, f"{alt}+up"),
                        (f"Move down\t{aname}+Down",         self.move_down, f"{alt}+down"),
                        (f"Move to Top\t{aname}+Left",       self.move_to_top, f"{alt}+left"),
                        (f"Move to Bottom\t{aname}+Right",    self.move_to_bottom, f"{alt}+right")]
        if with_remove_from_list:
            core_actions.append((f"Remove from List.. Alt+Delete", self.remove_from_list, f"{alt}+delete"))

        click_actions =  []
        if pre_actions is not None:
            click_actions.extend(pre_actions)
            click_actions.append(("--sep--", None, None))
        click_actions.extend(core_actions)
        if post_actions is not None:
            click_actions.append(("--sep--", None, None))
            click_actions.extend(post_actions)

        self.key_bindings = {}
        isep = 0
        if right_click:
            self.Bind(wx.EVT_RIGHT_DOWN, self.onRightClick)
            for dat in click_actions:
                keybind = None
                title = dat[0]
                if title.startswith("--sep"):
                    isep += 1
                    title = f"{title}_{isep}"
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

        keymap = {wx.WXK_LEFT: 'left', wx.WXK_RIGHT: 'right',
                  wx.WXK_UP: 'up',  wx.WXK_DOWN: 'down',
                  wx.WXK_DELETE: 'delete', wx.WXK_F1: 'f1',
                  wx.WXK_F2: 'f2', wx.WXK_F3: 'f3', wx.WXK_F4: 'f4',
                  wx.WXK_ADD: 'add', wx.WXK_SUBTRACT: 'sub',
                  wx.WXK_MULTIPLY: 'mul', wx.WXK_DIVIDE: 'div'}

        key = keymap.get(thiskey, chr(thiskey))

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
                mname = 'cmd' if uname == 'darwin' else 'ctrl'
                mname = 'ctrl'
                key = f'{mname}+{key}'
            elif mod == 16 and uname == 'darwin':
                key = f'rawctrl+{key}'

        action = self.key_bindings.get(key, None)
        # print("Event ", key, evt.HasAnyModifiers(), evt.GetModifiers(), 'alt : ', evt.AltDown() )
        # print(f"   checklist key_event:  {key=}, {action=}")
        if action is not None:
            action()

    def check_event(self, evt=None):
        index = evt.GetSelection()
        label = self.GetString(index)

    def onRightClick(self, evt=None):
        menu = wx.Menu()
        self.rclick_wids = {}
        for label, action in self.rclick_actions.items():
            if label.startswith('--sep--'):
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
        checked = list(self.GetCheckedStrings())
        self.Clear()
        for name in names:
            self.Append(name)
        self.SetCheckedStrings(checked)

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
        slist = list(self.GetCheckedStrings())
        if idx > 0:
            names.pop(idx)
            names.insert(idx-1, this)
            self.refresh(names)
        self.SetStringSelection(this)

    def move_down(self, event=None):
        idx, names, this =  self._get_current()
        if idx > -1 and idx < len(names):
            names.pop(idx)
            names.insert(idx+1, this)
            self.refresh(names)
        self.SetStringSelection(this)

    def move_to_top(self, event=None):
        idx, names, this =  self._get_current()
        if idx > -1:
            names.pop(idx)
            names.insert(0, this)
            self.refresh(names)
        self.SetStringSelection(this)

    def move_to_bottom(self, event=None):
        idx, names, this =  self._get_current()
        if idx > -1:
            names.pop(idx)
            names.append(this)
            self.refresh(names)
        self.SetStringSelection(this)

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
