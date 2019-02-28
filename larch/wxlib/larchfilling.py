#!/usr/bin/env python
"""
Larch Filling:  stolen and hacked from PyCrust's Filling module

Filling is the gui tree control through which a user can navigate
the local namespace or any object."""

from __future__ import print_function

__author__ = "Patrick K. O'Brien <pobrien@orbtech.com>"
__cvsid__ = "$Id: filling.py 37633 2006-02-18 21:40:57Z RD $"
__revision__ = "$Revision: 37633 $"

import sys
import wx
import numpy
import wx.html as html
import types

from wx.py import dispatcher
from wx.py import editwindow

import inspect
from functools import partial

from wx.py import introspect
from larch.symboltable import SymbolTable, Group
from larch.larchlib import Procedure
from wxutils  import Button, pack, is_wxPhoenix


VERSION = '0.9.5(Larch)'

COMMONTYPES = (int, float, complex, str, bool, dict, list, tuple, numpy.ndarray)

H5TYPES = ()
try:
    import h5py
    H5TYPES = (h5py.File, h5py.Group, h5py.Dataset)
except ImportError:
    pass

TYPE_HELPS = {}
for t in COMMONTYPES:
    TYPE_HELPS[t] = 'help on %s' % t

IGNORE_TYPE = []
DOCTYPES = ('BuiltinFunctionType', 'BuiltinMethodType', 'ClassType',
            'FunctionType', 'GeneratorType', 'InstanceType',
            'LambdaType', 'MethodType', 'ModuleType',
            'UnboundMethodType', 'method-wrapper')

def rst2html(text):
    return "<br>".join(text.split('\n'))


def call_signature(obj):
    """try to get call signature for callable object"""
    fname = obj.__name__

    # print("CALL SIG1: ", obj,  getattr(obj, '__module__', '<>'))
    # print(dir(obj))
    if isinstance(obj, partial):
        obj = obj.func

    argspec = None
    if hasattr(obj, '_larchfunc_'):
        obj = obj._larchfunc_

    argspec = inspect.getfullargspec(obj)
    keywords = argspec.varkw

    fargs = []
    ioff = len(argspec.args) - len(argspec.defaults)
    for iarg, arg in enumerate(argspec.args):
        if arg == '_larch':
            continue
        if iarg < ioff:
            fargs.append(arg)
        else:
            fargs.append("%s=%s" % (arg, repr(argspec.defaults[iarg-ioff])))
    if keywords is not None:
        fargs.append("**%s" % keywords)

    out = "%s(%s)" % (fname, ', '.join(fargs))
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

    name = 'Larch Filling Tree'
    revision = __revision__

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.TR_DEFAULT_STYLE,
                 rootObject=None, rootLabel=None, rootIsNamespace=False,
                 static=False):
        """Create FillingTree instance."""
        wx.TreeCtrl.__init__(self, parent, id, pos, size, style)
        self.rootIsNamespace = rootIsNamespace
        self.rootLabel = rootLabel
        self.static = static
        self.item = None
        self.root = None
        if is_wxPhoenix:
            self.GetPyData = self.GetItemData

        self.setRootObject(rootObject)

    def setRootObject(self, rootObject=None):
        self.rootObject = rootObject
        if self.rootObject is None:
            return
        if not self.rootLabel:
            self.rootLabel = 'Larch Data'

        rootData = rootObject
        if not is_wxPhoenix:
            rootData = wx.TreeItemData(rootData)
        self.item = self.root = self.AddRoot(self.rootLabel, -1, -1,  rootData)

        self.SetItemHasChildren(self.root,  self.objHasChildren(self.rootObject))
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnItemExpanding, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnItemCollapsed, id=self.GetId())
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, id=self.GetId())
        # self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnItemActivated, id=self.GetId())
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnSelChanged, id=self.GetId() )
        if not self.static:
            dispatcher.connect(receiver=self.push, signal='Interpreter.push')

    def push(self, command, more):
        """Receiver for Interpreter.push signal."""
        self.display()

    def OnItemExpanding(self, event):
        """Add children to the item."""
        item = event.GetItem()
        if self.IsExpanded(item):
            return
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
        obj = self.GetPyData(item)
        frame = FillingFrame(parent=self, size=(500, 500),
                             rootObject=obj,
                             rootLabel=text, rootIsNamespace=False)
        frame.Show()

    def objHasChildren(self, obj):
        """Return true if object has children."""
        children = self.objGetChildren(obj)
        if isinstance(children, dict):
            return len(children) > 1
        else:
            return False

    def objGetChildren(self, obj):
        """Return dictionary with attributes or contents of object."""
        otype = type(obj)
        d = {}
        if (obj is None or obj is False or obj is True):
            return d
        self.ntop = 0
        if isinstance(obj, SymbolTable) or isinstance(obj, Group):
            d = obj._members()
        if isinstance(obj, COMMONTYPES):
            d = obj
        elif isinstance(obj, h5py.Group):
            try:
                for key, val in obj.items():
                    d[key] = val
            except (AttributeError, ValueError):
                pass
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
            if not ((key.startswith('__') and key.endswith('__')) or
                    key.startswith('_SymbolTable') or
                    key == '_main'):
                a = getattr(obj, key)
                out[key] = a
        return out

    def addChildren(self, item):
        self.DeleteChildren(item)
        obj = self.GetPyData(item)
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
            if (isinstance(obj, dict) and isinstance(key, str) and
                (item != self.root or
                 (item == self.root and not self.rootIsNamespace))):
                itemtext = repr(key)
            child = data = children[key]
            if not is_wxPhoenix:
                data = wx.TreeItemData(child)
            branch = self.AppendItem(parent=item, text=itemtext, data=data)
            self.SetItemHasChildren(branch, self.objHasChildren(child))

    def display(self):
        item = self.item
        if not item:
            return

        obj = self.GetPyData(item)
        # print("Display: ", item, obj, isinstance(obj, Procedure),

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
            text.append("%s\n" % fullname)

        needs_doc = False
        if isinstance(obj, COMMONTYPES):
            text.append('Type: %s' % otype.__name__)
            text.append('Value = %s' % repr(obj))

        elif isinstance(obj, Group):
            text.append('Group: %s ' % obj.__name__)
            gdoc = getattr(obj, '__doc__', None)
            if gdoc is None: gdoc = Group.__doc__
            text.append(gdoc)
        elif hasattr(obj, '__call__'):
            text.append('Function: %s' % obj)
            try:
                text.append("\n%s" % call_signature(obj))
            except:
                pass
            needs_doc = True
        else:
            text.append('Type: %s' % str(otype))
            text.append('Value = %s' % repr(obj))
        text.append('\n')
        if needs_doc:
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
        text.append('\n')
        self.setText('\n'.join(text))

    def getFullName(self, item, part=''):
        """Return a syntactically proper name for item."""
        try:
            name = self.GetItemText(item)
        except:
            return None

        # return 'Could not get item name: %s' % repr(item)
        parent = None
        obj = None
        if item != self.root:
            parent = self.GetItemParent(item)
            obj = self.GetPyData(item)
        # Apply dictionary syntax to dictionary items, except the root
        # and first level children of a namepace.
        if ((isinstance(obj, dict) or hasattr(obj, 'keys')) and
            ((item != self.root and parent != self.root) or
             (parent == self.root and not self.rootIsNamespace))):
            name = '[' + name + ']'
        # Apply dot syntax to multipart names.
        if part:
            if part[0] == '[':
                name += part
            else:
                name += '.' + part
        # Repeat for everything but the root item
        # and first level children of a namespace.
        if (item != self.root and parent != self.root) \
        or (parent == self.root and not self.rootIsNamespace):
            name = self.getFullName(parent, part=name)
        return name

    def setText(self, text):
        """Display information about the current selection."""

        # This method will likely be replaced by the enclosing app to
        # do something more interesting, like write to a text control.
        print( text)

    def setStatusText(self, text):
        """Display status information."""

        # This method will likely be replaced by the enclosing app to
        # do something more interesting, like write to a status bar.
        print( text)


class FillingText(editwindow.EditWindow):
    """FillingText based on StyledTextCtrl."""

    name = 'Filling Text'
    revision = __revision__

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.CLIP_CHILDREN,
                 static=False):
        """Create FillingText instance."""
        editwindow.EditWindow.__init__(self, parent, id, pos, size, style)
        # Configure various defaults and user preferences.
        self.SetReadOnly(True)
        self.SetWrapMode(True)
        self.SetMarginWidth(1, 0)
        if not static:
            dispatcher.connect(receiver=self.push, signal='Interpreter.push')

    def push(self, command, more):
        """Receiver for Interpreter.push signal."""
        self.Refresh()

    def SetText(self, *args, **kwds):
        # print("Text Set Text ", args)
        self.SetReadOnly(False)
        editwindow.EditWindow.SetText(self, *args, **kwds)
        self.SetReadOnly(True)


class FillingRST(html.HtmlWindow):
    """FillingText based on Rest doc string!"""

    name = 'Filling Restructured Text'

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.NO_FULL_REPAINT_ON_RESIZE,
                 static=False):
        """Create FillingRST instance."""
        html.HtmlWindow.__init__(self, parent, id, style=wx.NO_FULL_REPAINT_ON_RESIZE)

        # Configure various defaults and user preferences.
        if not static:
            dispatcher.connect(receiver=self.push, signal='Interpreter.push')

    def push(self, command, more):
        """Receiver for Interpreter.push signal."""
        pass

    def SetText(self, text='', **kwds):
        # html = ['<html><body>',rst2html(text), '</body></html>']
        self.SetPage(rst2html(text))



class Filling(wx.SplitterWindow):
    """Filling based on wxSplitterWindow."""

    name = 'Filling'
    revision = __revision__

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.SP_3D|wx.SP_LIVE_UPDATE,
                 name='Filling Window', rootObject=None,
                 rootLabel=None, rootIsNamespace=False, static=False):
        """Create a Filling instance."""
        wx.SplitterWindow.__init__(self, parent, id, pos, size, style, name)
        self.tree = FillingTree(parent=self, rootObject=rootObject,
                                rootLabel=rootLabel,
                                rootIsNamespace=rootIsNamespace,
                                static=static)

        self.text = FillingText(parent=self, static=static)
        self.SplitVertically(self.tree, self.text, 200)
        self.SetMinimumPaneSize(100)

        # Override the filling so that descriptions go to FillingText.
        self.tree.setText = self.text.SetText

        # Display the root item.
        if self.tree.root is not None:
            self.tree.SelectItem(self.tree.root)
            self.tree.display()

        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnChanged)

    def SetRootObject(self, rootObject=None):
        self.tree.setRootObject(rootObject)
        if self.tree.root is not None:
            self.tree.SelectItem(self.tree.root)
            wx.CallAfter(self.tree.display)

    def OnChanged(self, event):
        #this is important: do not evaluate this event=>
        # otherwise, splitterwindow behaves strange
        #event.Skip()
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


class FillingFrame(wx.Frame):
    """Frame containing the namespace tree component."""
    name = 'Filling Frame'
    revision = __revision__
    def __init__(self, parent=None, id=-1, title='Larch Data Tree',
                 pos=wx.DefaultPosition, size=(600, 400),
                 style=wx.DEFAULT_FRAME_STYLE, rootObject=None,
                 rootLabel=None, rootIsNamespace=False, static=False):
        """Create FillingFrame instance."""
        wx.Frame.__init__(self, parent, id, title, pos, size, style)
        intro = 'Larch Data Tree'
        self.CreateStatusBar()
        self.SetStatusText(intro)
        self.filling = Filling(parent=self,
                               rootObject=rootObject,
                               rootLabel=rootLabel,
                               rootIsNamespace=rootIsNamespace,
                               static=static)
        # Override so that status messages go to the status bar.
        self.filling.tree.setStatusText = self.SetStatusText


class App(wx.App):
    """PyFilling standalone application."""
    def OnInit(self):
        wx.InitAllImageHandlers()
        self.fillingFrame = FillingFrame()
        self.fillingFrame.Show(True)
        self.SetTopWindow(self.fillingFrame)
        return True
