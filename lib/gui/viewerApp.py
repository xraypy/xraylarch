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

CEN = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
RIGHT = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
ALL_CEN =  wx.ALL|CEN


FILE_WILDCARDS = "Scan Data Files(*.0*)|*.0*|Data Files(*.dat)|*.dat|All files (*.*)|*.*"

class PlotterFrame(wx.Frame):
    _about = """StepScan Plotter
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, conffile=None,  **kwds):


        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, None, -1, size=(600, 500),  **kwds)

        self.data = None
        self.datafiles = {}
        self.filemap = {}
        self.Font16=wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font14=wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font12=wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font11=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        self.SetTitle("Step Scan Viewer")
        self.SetSize((750, 775))
        self.SetFont(self.Font11)

        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-4, -1])
        statusbar_fields = ["Initializing....", " "]
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
        sizer = wx.GridBagSizer(8, 15)
        self.filename = SimpleText(panel, 'initializing...')
        ir = 0
        sizer.Add(self.filename, (ir, 0), (1, 12), ALL_CEN, 2)
        # x-axis

        self.x_choice = add_choice(panel, choices=[], size=(130, -1))
        self.x_ops    = add_choice(panel, choices=('', 'log'), size=(120, -1))
        # self.xchoice.SetItems(list of choices)
        # self.xchoice.SetStringSelection(default string)

        ir += 1
        sizer.Add(SimpleText(panel, 'X = '), (ir, 1), (1, 1), ALL_CEN, 0)
        sizer.Add(self.x_ops,                (ir, 2), (1, 1), ALL_CEN, 0)
        sizer.Add(self.x_choice,             (ir, 4), (1, 1), RIGHT, 0)

        self.y_ops1    = add_choice(panel, size=(120, -1),
                                    choices=('', 'log', '-log', 'deriv', '-deriv',
                                             'deriv(log', 'deriv(-log'))

        self.y1_choice = add_choice(panel, choices=[], size=(130, -1))
        self.y_ops2    = add_choice(panel, choices=('+', '-', '*', '/'), size=(50, -1))
        self.y2_choice = add_choice(panel, choices=[], size=(130, -1))
        self.y_ops3    = add_choice(panel, choices=('+', '-', '*', '/'), size=(50, -1))
        self.y3_choice = add_choice(panel, choices=[], size=(130, -1))
        self.y_ops1.SetSelection(0)
        self.y_ops2.SetSelection(2)
        self.y_ops3.SetSelection(3)

        ir += 1
        sizer.Add(SimpleText(panel, 'Y = '), (ir,  1), (1, 1), ALL_CEN, 0)
        sizer.Add(self.y_ops1,               (ir,  2), (1, 1), ALL_CEN, 0)
        sizer.Add(SimpleText(panel, '( ('),  (ir,  3), (1, 1), ALL_CEN, 0)
        sizer.Add(self.y1_choice,            (ir,  4), (1, 1), ALL_CEN, 0)
        sizer.Add(self.y_ops2,               (ir,  5), (1, 1), ALL_CEN, 0)
        sizer.Add(self.y2_choice,            (ir,  6), (1, 1), ALL_CEN, 0)
        sizer.Add(SimpleText(panel, ') '),   (ir,  7), (1, 1), ALL_CEN, 0)
        sizer.Add(self.y_ops3,               (ir,  8), (1, 1), ALL_CEN, 0)
        sizer.Add(self.y3_choice,            (ir,  9), (1, 1), ALL_CEN, 0)
        sizer.Add(SimpleText(panel, ')'),    (ir, 10), (1, 1), ALL_CEN, 0)

        self.plot_btn  = add_button(panel, "New Plot", action=self.onPlot)
        self.oplot_btn = add_button(panel, "OverPlot", action=self.onOPlot)

        ir += 1
        sizer.Add(self.plot_btn,   (ir, 1), (1, 3), ALL_CEN, 2)
        sizer.Add(self.oplot_btn,  (ir, 4), (1, 3), ALL_CEN, 2)

        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(675, 3), style=wx.LI_HORIZONTAL),
                  (ir, 1), (1, 10), wx.ALIGN_CENTER)
        ir += 1
        sizer.Add(SimpleText(panel, 'Should add fitting options'),
                  (ir, 1), (1, 10), wx.ALIGN_CENTER)

        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(675, 3), style=wx.LI_HORIZONTAL),
                  (ir, 1), (1, 10), wx.ALIGN_CENTER)

        pack(panel, sizer)
        return panel

    def init_larch(self):
        t0 = time.time()
        import larch
        self._larch = larch.Interpreter()
        print 'initialized larch in %.3f sec' % (time.time()-t0)
        self.SetStatusText('ready')
        self.filename.SetLabel('')

    def onPlot(self, evt):    self.do_plot()

    def onOPlot(self, evt):   self.do_plot(overplot=True)

    def do_plot(self, overplot=False):
        print ' Plot ', overplot
        print self.x_choice.GetSelection()
        if self.data is None:
            self.SetStatus( 'cannot plot - no valid data')

    def ShowFile(self, evt=None, filename=None, **kws):
        print 'show file details on rhs', evt, filename
        if filename is None and hasattr(evt, 'GetStringSelection'):
            filename = evt.GetStringSelection()

        key = filename
        if filename in self.filemap:
            key = self.filemap[filename]
        if filename in self.datafiles:
            key = filename

        self.data = self.datafiles[key]

        xcols, ycols = [], ['1']
        for i, k in  enumerate(self.data.column_keys):
            if k.startswith('p'):
                xcols.append(self.data.column_names[i])
            elif k.startswith('d'):
                ycols.append(self.data.column_names[i])
        ycols.extend(xcols)

        self.filename.SetLabel(key)
        self.x_choice.SetItems(xcols)
        self.x_choice.SetSelection(0)
        self.y1_choice.SetItems(ycols)
        self.y1_choice.SetSelection(3)
        self.y2_choice.SetItems(ycols)
        self.y1_choice.SetSelection(4)
        self.y3_choice.SetItems(ycols)
        self.y1_choice.SetSelection(2)

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
