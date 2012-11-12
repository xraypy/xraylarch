#!/usr/bin/env python
"""
GUI for reading and displaying plots of column data from StepScanData objects,
as read from disk files written by stepscan.

Principle features:
   simple list of files read
   frame for plot a file, with math on columns
To Do:
   all

"""
import os
import time
import shutil

from datetime import timedelta

import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection

import epics
from epics.wx import DelayedEpicsCallback, EpicsFunction

from .gui_utils import SimpleText, FloatCtrl, Closure
from .gui_utils import pack, add_button, add_menu, add_choice, add_menu

from ..datafile import StepScanData

from ..ordereddict import OrderedDict

ALL_CEN =  wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL
FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

FILE_WILDCARDS = "Scan Data Files(*.0*)|*.0*|Data Files(*.dat)|*.dat|All files (*.*)|*.*"

class PlotterFrame(wx.Frame):
    _about = """StepScan Plotter
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, conffile=None,  **kwds):


        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, None, -1, size=(600, 500),  **kwds)

        self.datafiles = {}
        self.filemap = {}
        self.Font16=wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font14=wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font12=wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font11=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        self.SetTitle("Step Scan Viewer")
        self.SetSize((700, 575))
        self.SetFont(self.Font11)

        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ["Messages", "Status"]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

    def createMainPanel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(175)

        self.filelist  = wx.ListBox(splitter)
        self.filelist.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.filelist.Bind(wx.EVT_LISTBOX, self.ShowFile)

        self.detailspanel = self.createDetailsPanel(splitter)

        splitter.SplitVertically(self.filelist, self.detailspanel, 1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)
        wx.CallAfter(self.init_larch)
        pack(self, sizer)

    def createDetailsPanel(self, parent):
        panel = wx.Panel(parent)
        sizer = wx.GridBagSizer(8, 5)
        title = SimpleText(panel, 'select arrays')
        sizer.Add(title, (0, 0), (1, 5), ALL_CEN, 2)
        pack(panel, sizer)
        return panel

    def init_larch(self):
        t0 = time.time()
        import larch
        self._larch = larch.Interpreter()
        print 'initialized larch in %.3f sec' % (time.time()-t0)

    def ShowFile(self, evt=None, filename=None, **kws):
        print 'show file details on rhs'
        print evt
        key = None
        if filename in self.filemap:
            key = self.filemap[filename]
        if filename in self.datafiles:
            key = filename
        print filename, key
        dfile = self.datafiles[key]
        print dfile

    def createMenus(self):
        self.menubar = wx.MenuBar()
        # file
        fmenu = wx.Menu()
        add_menu(self, fmenu, "&Open Scan File\tCtrl+O",
                 "Read Scan File",  self.onReadScan)

        fmenu.AppendSeparator()
        add_menu(self, fmenu, "&Quit\tCtrl+Q",
                  "Quit program", self.onClose)

        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)

    def onAbout(self,evt):
        dlg = wx.MessageDialog(self, self._about,"About Epics StepScan",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,evt):
        self.Destroy()

    def onReadScan(self, evt=None):
        dlg = wx.FileDialog(self, message="Load EpicsScan Settings",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if path in self.datafiles:
                print 'should ask for re-read?'
            try:
                dfile = StepScanData(path)
            except IOError:
                print 'should popup ioerror'
            if dfile._valid:
                p, fname = os.path.split(path)
                self.datafiles[path] = StepScanData(path)
                self.filelist.Append(fname)
                self.filemap[fname] = path
                self.ShowFile(filename=fname)
            else:
                print 'should popup invalid file message'
            print 'file read success: ', path
        dlg.Destroy()

class ViewerApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, config=None, dbname=None, **kws):
        self.config  = config
        self.dbname  = dbname
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        frame = PlotterFrame() #
        frame.Show()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    ViewerApp().MainLoop()
