#!/usr/bin/env python
"""
HDF5 Browser:  borrowd from PyCrust's Filling module
  by rPatrick K. O'Brien <pobrien@orbtech.com>
"""

import sys
import glob
import wx
import numpy
import wx.html as html
import types
import time
import h5py
import locale
import inspect
from functools import partial
from pathlib import Path
import larch

from wxutils  import Button, pack, get_color, register_darkdetect, MenuItem
from pyshortcuts import uname, fix_filename, get_cwd

VERSION = '0.1'

COMMONTYPES = (int, float, complex, str, bool, dict, list, tuple, numpy.ndarray)

FILE_WILDCARD = 'HDF5/Zarr files(*.hdf5;*.h5;*.zarr)|*.hdf5;*.h5;*.zarr|All files (*.*)|*.*'


FONTSIZE = 10
FONTSIZE_FW = 10
if uname == 'win':
    FONTSIZE = 11
    FONTSIZE_FW = 12
    locale.setlocale(locale.LC_ALL, 'C')
elif uname == 'darwin':
    FONTSIZE = 11
    FONTSIZE_FW = 12

def fontsize(fixed_width=False):
    """return best default fontsize"""
    font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
    if uname not in ('win', 'darwin'):
        font = font.Smaller()
    elif fixed_width:
        font = font.Larger()
    return int(font.GetFractionalPointSize())

def Font(size, serif=False, fixed_width=False):
    """define a font by size and serif/ non-serif
    f = Font(10, serif=True)
    """
    family = wx.DEFAULT
    if not serif:
        family = wx.SWISS
    if fixed_width:
        family = wx.MODERN
    return wx.Font(size, family, wx.NORMAL, wx.BOLD, 0, "")

def get_font(larger=0, smaller=0, serif=False, fixed_width=False):
    "return a font"
    fnt = Font(fontsize(fixed_width=fixed_width),
               serif=serif, fixed_width=fixed_width)
    for i in range(larger):
        fnt = fnt.Larger()
    for i in range(smaller):
        fnt = fnt.Smaller()
    return fnt


def call_signature(obj):
    """try to get call signature for callable object"""
    fname = obj.__name__

    if isinstance(obj, partial):
        obj = obj.func

    argspec = None
    argspec = inspect.getfullargspec(obj)
    keywords = argspec.varkw

    fargs = []
    ioff = len(argspec.args) - len(argspec.defaults)
    for iarg, arg in enumerate(argspec.args):
        if iarg < ioff:
            fargs.append(arg)
        else:
            fargs.append(f"{arg}={repr(argspec.defaults[iarg-ioff])}")
    if keywords is not None:
        fargs.append(f"**{keywords}")

    out = f"{fname}({', '.join(fargs)})"
    maxlen = 71
    if len(out) > maxlen:
        o  = []
        while len(out) > maxlen:
            ecomm = maxlen - out[maxlen-1::-1].find(',')
            o.append(out[:ecomm])
            out = " "*(len(fname)+1) + out[ecomm:].strip()
        if len(out)  > 0:
            o.append(out)
        out = '\n'.join(o)
    return out

class FillingTree(wx.TreeCtrl):
    """FillingTree based on TreeCtrl."""
    __label__ = 'Data'

    def __init__(self, parent, rootObject=None, rootLabel=None, size=wx.DefaultSize,
                 pos=wx.DefaultPosition, style=wx.TR_DEFAULT_STYLE):

        """Create FillingTree instance."""
        wx.TreeCtrl.__init__(self, parent, size=size, style=style)
        self.item = None
        self.root = None
        self.rootLabel = rootLabel
        self.setRootObject(rootObject)

    def setRootObject(self, rootObject=None):
        self.rootObject = rootObject
        if self.rootObject is None:
            return
        if self.rootLabel is None:
            self.rootLabel = self.__label__

        self.item = self.root = self.AddRoot(self.rootLabel, -1, -1,  self.rootObject)

        self.SetItemHasChildren(self.root,  self.objHasChildren(self.rootObject))
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnItemActivated, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnItemExpanding, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnItemCollapsed, id=self.GetId())
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnSelChanged, id=self.GetId() )

    def push(self, command=None, more=None):
        """Receiver for Interpreter.push signal."""
        self.display()

    def OnItemExpanding(self, event=None):
        """Add children to the item."""
        try:
            item = event.GetItem()
        except:
            item = self.item
        if self.IsExpanded(item):
            return
        # print("OnItemExpanding ", self.item)
        self.addChildren(item)
        self.SelectItem(item)

    def OnItemCollapsed(self, event):
        """Remove all children from the item."""
        item = event.GetItem()

    def OnSelChanged(self, event):
        """Display information about the item."""
        if hasattr(event, 'GetItem'):
            self.item = event.GetItem()
        self.display()

    def OnItemActivated(self, event):
        """Launch a DirFrame."""
        item = event.GetItem()
        text = self.getFullName(item)
        obj = self.GetItemData(item)

    def objHasChildren(self, obj):
        """Return true if object has children."""
        children = self.objGetChildren(obj)
        if isinstance(children, dict):
            return len(children) > 0
        else:
            return False

    def objGetChildren(self, obj):
        """Return dictionary with attributes or contents of object."""
        otype = type(obj)
        d = {}
        self.ntop = 0
        if (obj is None or obj is False or obj is True):
            return d
        elif isinstance(obj, COMMONTYPES):
            d = obj
        elif isinstance(obj, larch.Group):
            d = obj._members()
        elif isinstance(obj, h5py.Group):
            d = {key: val for key, val in obj.items()}
        elif isinstance(obj, h5py.Dataset):
            d = obj
        elif isinstance(obj, (list, tuple)):
            for n in range(len(obj)):
                key = '[' + str(n) + ']'
                d[key] = obj[n]
        elif (not isinstance(obj, wx.Object)
              and not hasattr(obj, '__call__')):
            d = self.GetAttr(obj)
        return d

    def GetAttr(self, obj):
        out = {}
        for key in dir(obj):
            if not (key.startswith('__') and key.endswith('__')):
                try:
                    out[key] = getattr(obj, key)
                except:
                    out[key] = key
        return out

    def addChildren(self, item):
        self.DeleteChildren(item)
        obj = self.GetItemData(item)
        children = self.objGetChildren(obj)
        if not children:
            return
        try:
            keys = children.keys()
        except:
            return
        # keys.sort(lambda x, y: cmp(str(x).lower(), str(y).lower()))
        for key in sorted(keys):
            itemtext = str(key)
            # Show string dictionary items with single quotes, except
            # for the first level of items, if they represent a
            # namespace.
            if isinstance(obj, dict) and isinstance(key, str):
                itemtext = repr(key)
            child  = children[key]
            branch = self.AppendItem(parent=item, text=itemtext, data=child)
            self.SetItemHasChildren(branch, self.objHasChildren(child))

    def display(self):
        item = self.item
        if not item:
            return
        obj = self.GetItemData(item)
        print(" Display item: " , item, obj)
        if self.IsExpanded(item):
            self.addChildren(item)
        self.setText('')

        if wx.Platform == '__WXMSW__':
            if obj is None: # Windows bug fix.
                return
        self.SetItemHasChildren(item, self.objHasChildren(obj))
        otype = type(obj)
        text = []
        fullname = self.getFullName(item)
        if fullname is not None:
            text.append(f"{fullname}")

        if obj == self.rootObject:
            text = ['Data']

        elif isinstance(obj, COMMONTYPES):
            text.append(f'Type: {otype.__name__}')
            text.append(f'Value = {repr(obj)}')

        elif isinstance(obj, h5py.File):
            text.append(f'HDF5 File  : {obj.filename}')
            text.append(f'members    : {list(obj.keys())}')
            text.append(f'attributes : {dict(obj.attrs)}')
        elif isinstance(obj, h5py.Group):
            text.append(f'HDF5 Group : {obj.name}')
            text.append(f'members    : {list(obj.keys())}')
            text.append(f'attributes : {dict(obj.attrs)}')
        elif isinstance(obj, h5py.Dataset):
            text.append(f'HDF5 Dataset : {obj.name}')
            text.append(f'shape, dtype : {obj.shape}, {obj.dtype}')
            text.append(f'attributes   : {dict(obj.attrs)}')

        elif hasattr(obj, '__call__'):
            text.append(f'Function: {obj}')
            try:
                text.append(f"\n{call_signature(obj)}")
            except:
                pass
            try:
                doclines = obj.__doc__.strip().split('\n')
            except:
                doclines = ['No documentation found']
            indent = 0
            for dline in doclines:
                if len(dline.strip()) > 0:
                    indent = dline.index(dline.strip())
                    break
            for d in doclines:
                text.append(d[indent:])
        else:
            text.append(f'Type  : {otype}')
            text.append(f'Value : {repr(obj)}')
        text.append('')
        self.setText('\n'.join(text))

    def getFullName(self, item, part=''):
        """Return a syntactically proper name for item."""
        try:
            name = self.GetItemText(item)
        except:
            return None

        parent = None
        obj = None
        if item != self.root:
            parent = self.GetItemParent(item)
            obj = self.GetItemData(item)
        # Apply dictionary syntax to dictionary items, except the root
        # and first level children of a namepace.
        if ((isinstance(obj, dict) or hasattr(obj, 'keys')) and
            ((item != self.root and parent != self.root))):
            name = f'{name}'
        if len(part) > 0:
             name = f'{name}/{part}'
        # Repeat for everything but the root item
        # and first level children of a namespace.
        if (item != self.root and parent != self.root):
            name = self.getFullName(parent, part=name)
        return name

    def setText(self, text):
        """Display information about the current selection."""
        print( text)

    def setStatusText(self, text):
        """Display status information."""
        print(f"Status: {text}")

class FillingText(wx.TextCtrl):
    """FillingText based on StyledTextCtrl."""

    name = 'Filling Text'

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, bcol=None,
                 style=wx.TE_MULTILINE|wx.TE_RICH|wx.TE_READONLY):
        """Create FillingText instance."""

        wx.TextCtrl.__init__(self, parent, id, style=style)
        self.CanCopy()
        self.SetFont(get_font(fixed_width=True))

    def push(self, command, more):
        """Receiver for Interpreter.push signal."""
        self.Refresh()

    def SetText(self, *args, **kwds):
        # self.SetReadOnly(False)
        self.Clear()
        self.SetInsertionPoint(0)
        self.WriteText(*args)
        self.ShowPosition(0)


class Filling(wx.SplitterWindow):
    """Filling based on wxSplitterWindow."""
    name = 'Filling'

    def __init__(self, parent, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.SP_3D|wx.SP_LIVE_UPDATE,
                 name='Filling Window', rootObject=None,
                 rootLabel=None, bgcol=None, fgcol=None):
        """Create a Filling instance."""

        wx.SplitterWindow.__init__(self, parent, -1, pos, size, style, name)
        self.tree = FillingTree(parent=self, rootObject=rootObject,
                                rootLabel=rootLabel)

        self.text = FillingText(parent=self)
        fgcol = get_color('text')
        bgcol = get_color('text_bg')
        self.tree.SetBackgroundColour(bgcol)
        self.tree.SetForegroundColour(fgcol)
        self.text.SetBackgroundColour(bgcol)
        self.text.SetForegroundColour(fgcol)

        self.SplitVertically(self.tree, self.text, 200)
        self.SetMinimumPaneSize(100)
        register_darkdetect(self.onDarkMode)
        # Override the filling so that descriptions go to FillingText.
        self.tree.setText = self.text.SetText

        # Display the root item.
        if self.tree.root is not None:
            self.tree.SelectItem(self.tree.root)
            self.tree.display()

    def onDarkMode(self, is_dark=None):
        fgcol = get_color('text', dark=is_dark)
        bgcol = get_color('text_bg', dark=is_dark)
        self.tree.SetBackgroundColour(bgcol)
        self.tree.SetForegroundColour(fgcol)
        self.text.SetBackgroundColour(bgcol)
        self.text.SetForegroundColour(fgcol)
        wx.CallAfter(self.Refresh)


    def SetRootObject(self, rootObject=None):
        self.tree.setRootObject(rootObject)
        if self.tree.root is not None:
            self.tree.SelectItem(self.tree.root)
            self.tree.display()

    def OnChanged(self, event):
        pass

    def onRefresh(self, evt=None):
        """ refesh data tree, preserving current selection"""
        root = self.tree.GetRootItem()
        this = self.tree.GetFocusedItem()
        parents = [self.tree.GetItemText(this)]
        while True:
            try:
                this = self.tree.GetItemParent(this)
                if this == root:
                    break
                parents.append(self.tree.GetItemText(this))
            except:
                break
        self.tree.Collapse(root)
        self.tree.Expand(root)
        node = root

        while len(parents) > 0:
            name = parents.pop()
            node = self.get_node_by_name(node, name)
            if node is not None:
                self.tree.Expand(node)

        try:
            self.tree.Expand(node)
            self.tree.SelectItem(node)
        except:
            pass

    def get_node_by_name(self, node, name):
        if node is None:
            node = self.tree.GetRootItem()
        item, cookie = self.tree.GetFirstChild(node)
        if item.IsOk() and self.tree.GetItemText(item) == name:
            return item

        nodecount = self.tree.GetChildrenCount(node)
        while nodecount > 1:
            nodecount -= 1
            item, cookie = self.tree.GetNextChild(node, cookie)
            if not item.IsOk() or self.tree.GetItemText(item) == name:
                return item

    def ShowNode(self, name):
        """show node by name"""
        root = self.tree.GetRootItem()
        self.tree.Collapse(root)
        self.tree.Expand(root)
        node = root
        parts = name.split('.')
        parts.reverse()
        while len(parts) > 0:
            name = parts.pop()
            node = self.get_node_by_name(node, name)
            if node is not None:
                self.tree.Expand(node)

        try:
            self.tree.Expand(node)
            self.tree.SelectItem(node)
        except:
            pass

    def LoadSettings(self, config):
        pos = config.ReadInt('Sash/FillingPos', 200)
        wx.FutureCall(250, self.SetSashPosition, pos)
        zoom = config.ReadInt('View/Zoom/Filling', -99)
        if zoom != -99:
            self.text.SetZoom(zoom)

    def SaveSettings(self, config):
        config.WriteInt('Sash/FillingPos', self.GetSashPosition())
        config.WriteInt('View/Zoom/Filling', self.text.GetZoom())


class HDF5_Frame(wx.Frame):
    """Frame containing the namespace tree component."""
    name = 'HDF5 Data Tree'

    def __init__(self, parent=None, id=-1, title='HDF5 Data Tree',
                 pos=wx.DefaultPosition, size=(600, 400),
                 style=wx.DEFAULT_FRAME_STYLE, rootObject=None,
                 rootLabel=None):
        """Create HDF5_Frame instance."""
        wx.Frame.__init__(self, parent, id, title, pos, size, style)

        self.filling = Filling(parent=self,
                               rootObject=rootObject,
                               rootLabel=rootLabel)

        self.data = self.filling.tree.rootObject
        self.set_fontsize(12)
        self.CreateStatusBar()
        self.SetStatusText('Welcome to HDF5 Browser')
        self.BuildMenus()
        # Override so that status messages go to the status bar.
        self.filling.tree.setStatusText = self.SetStatusText

    def Raise(self):
        self.SetStatusText("Ready", 0)
        self.Refresh()
        wx.Frame.Raise(self)

    def BuildMenus(self):
        menuBar = wx.MenuBar()
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "&Read Data File\tCtrl+O",
                 "Read Data File", self.onReadData)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, 'Show wxPython Inspector\tCtrl+I',
                 'Debug wxPython App', self.onWxInspect)

        self.Bind(wx.EVT_CLOSE,  self.onExit)
        MenuItem(self, fmenu, 'E&xit', 'Exit', self.onExit)
        menuBar.Append(fmenu, '&File')

        fsmenu = wx.Menu()
        self.fontsizes = {}
        for fsize in (10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 24):
            m = MenuItem(self, fsmenu,  f"{fsize}", f"{fsize}",
                         self.onSelectFont, kind=wx.ITEM_RADIO)
            self.fontsizes[m.GetId()] = fsize
            if fsize == self.fontsize:
                m.Check()

        menuBar.Append(fsmenu, 'Font Size')

        #hmenu = wx.Menu()
        #MenuItem(self, hmenu, '&About',
        #         'Information about this program',  self.onAbout)
        #menuBar.Append(hmenu, '&Help')
        self.SetMenuBar(menuBar)

    def onSelectFont(self, event=None, fsize=None):
        if fsize is None:
            fsize = self.fontsizes.get(event.GetId(), self.fontsize)
        self.set_fontsize(fsize)

    def set_fontsize(self, fsize):
        self.fontsize = self.PointSize = fsize
        def set_fsize(obj, fsize):
            fn = obj.GetFont()
            f1, f2 = fn.PixelSize
            fn.SetPixelSize(wx.Size(int((f1*fsize/f2)), fsize))
            obj.SetFont(fn)

        set_fsize(self, fsize)

        set_fsize(self.filling.tree,  fsize)
        set_fsize(self.filling.text, fsize)

    def onWxInspect(self, event=None):
        wx.GetApp().ShowInspectionTool()

    def show_subframe(self, event=None, name=None, creator=None, **opts):
        if name is None or creator is None:
            return
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except:
                del self.subframes[name]
        if not shown:
            self.subframes[name] = creator(parent=self, **opts)
            self.subframes[name].Show()

    def onReadData(self, event=None):
        dlg = wx.FileDialog(self, message='Open Data File',
                            defaultDir=get_cwd(),
                            wildcard=FILE_WILDCARD,
                            style=wx.FD_OPEN|wx.FD_CHANGE_DIR)
        path = None
        if dlg.ShowModal() == wx.ID_OK:
            path = Path(dlg.GetPath()).absolute()
        dlg.Destroy()

        if path is None:
            return

        fname = path.name
        if fname in self.data:
            dlg = wx.MessageDialog(None, f'File {fname} already exists... re-read?', 'Question',
                                   wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            ret = dlg.ShowModal()
            if ret == wx.ID_NO:
                return

        try:
            self.data[fname] = h5py.File(fname, 'r')
        except Exception:
            pass
        self.filling.tree.display()
        self.filling.ShowNode(fname)

    def onChangeDir(self, event=None):
        dlg = wx.DirDialog(None, 'Choose a Working Directory',
                           defaultPath = get_cwd(),
                           style = wx.DD_DEFAULT_STYLE)

        if dlg.ShowModal() == wx.ID_OK:
            os.chdir(dlg.GetPath())
        dlg.Destroy()
        return get_cwd()

    def onAbout(self, event=None):
        about_msg =  """HDF5 Viewer"""
        dlg = wx.MessageDialog(self, about_msg,
                               "About HDF5 Viewer", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()


    def onExit(self, event=None):
        dlg = wx.MessageDialog(None, 'Really Quit?', 'Question',
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        ret = dlg.ShowModal()

        if ret == wx.ID_YES:
            try:
                for a in self.GetChildren():
                    a.Destroy()
            except:
                pass
            self.Destroy()
        else:
            try:
                event.Veto()
            except:
                pass

class HDF5_App(wx.App):
    "simple app to wrap HDF5_Frame"
    def __init__(self, with_inspect=False, dtree=None, **kws):
        self.with_inspect = with_inspect
        self.dtree = dtree
        wx.App.__init__(self, **kws)

    def createApp(self):
        self.frame = HDF5_Frame(rootObject=self.dtree)
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True

    def OnInit(self):
        self.createApp()
        if self.with_inspect:
            self.ShowInspectionTool()
        return True

    def InitLocale(self):
        """over-ride wxPython default initial locale"""
        lang, enc = locale.getdefaultlocale()
        self._initial_locale = wx.Locale(lang, lang[:2], lang)
        locale.setlocale(locale.LC_ALL, lang)

    def set_datatree(self, dtree):
        self.frame.rootObject = self.dtree = dtree

    def run(self):
        self.MainLoop()

if __name__ == '__main__':
    files = {}
    for fname in sorted(glob.glob('*.h5')):
        try:
            obj = h5py.File(fname)
            files[fname] = obj
        except Exception:
            pass
        if len(files) > 2:
            break


    app = HDF5_App(dtree=files)
    app.MainLoop()
