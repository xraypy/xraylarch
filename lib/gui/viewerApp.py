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
from random import randrange

from datetime import timedelta

import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection

import epics
from epics.wx import DelayedEpicsCallback, EpicsFunction

from wxmplot import PlotPanel

from ..datafile import StepScanData
from .gui_utils import (SimpleText, FloatCtrl, Closure, pack, add_button,
                        add_menu, add_choice, add_menu,
                        CEN, RCEN, LCEN, FRAMESTYLE, Font)

CEN |=  wx.ALL
FILE_WILDCARDS = "Scan Data Files(*.0*)|*.0*|Data Files(*.dat)|*.dat|All files (*.*)|*.*"

def randname(n=6):
    "return random string of n (default 6) lowercase letters"
    return ''.join([chr(randrange(26)+97) for i in range(n)])

class PlotterFrame(wx.Frame):
    _about = """StepScan Plotter
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, conffile=None,  **kwds):


        kwds["style"] = FRAMESTYLE
        wx.Frame.__init__(self, None, -1, **kwds)

        self.data = None
        self.filemap = {}
        self.larch = None

        self.SetTitle("Step Scan Data File Viewer")
        self.SetSize((775, 525))
        self.SetFont(Font(9))

        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
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
        mainpanel = wx.Panel(parent)
        mainsizer = wx.BoxSizer(wx.VERTICAL)

        panel = wx.Panel(mainpanel)
        sizer = wx.GridBagSizer(8, 10)
        self.title = SimpleText(panel, 'initializing...')
        ir = 0
        sizer.Add(self.title, (ir, 0), (1, 8), CEN, 2)
        # x-axis

        self.x_choice = add_choice(panel, choices=[],          size=(100, -1))
        self.x_op     = add_choice(panel, choices=('', 'log'), size=(60, -1))
        # self.xchoice.SetItems(list of choices)
        # self.xchoice.SetStringSelection(default string)

        ir += 1
        sizer.Add(SimpleText(panel, 'X='), (ir, 1), (1, 1), CEN, 0)
        sizer.Add(self.x_op,               (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.x_choice,           (ir, 4), (1, 1), RCEN, 0)

        self.y_op1     = add_choice(panel, size=(60, -1),
                                    choices=('', 'log', '-log', 'deriv', '-deriv',
                                             'deriv(log', 'deriv(-log'))

        self.y1_choice = add_choice(panel, choices=[], size=(100, -1))
        self.y_op2     = add_choice(panel, choices=('+', '-', '*', '/'), size=(50, -1))
        self.y2_choice = add_choice(panel, choices=[], size=(100, -1))
        self.y_op3     = add_choice(panel, choices=('+', '-', '*', '/'), size=(50, -1))
        self.y3_choice = add_choice(panel, choices=[], size=(100, -1))
        self.y_op1.SetSelection(0)
        self.y_op2.SetSelection(2)
        self.y_op3.SetSelection(3)

        ir += 1
        sizer.Add(SimpleText(panel, 'Y='),  (ir,  1), (1, 1), CEN, 0)
        sizer.Add(self.y_op1,               (ir,  2), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, '(['),  (ir,  3), (1, 1), CEN, 0)
        sizer.Add(self.y1_choice,           (ir,  4), (1, 1), CEN, 0)
        sizer.Add(self.y_op2,               (ir,  5), (1, 1), CEN, 0)
        sizer.Add(self.y2_choice,           (ir,  6), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, ']'),   (ir,  7), (1, 1), CEN, 0)
        sizer.Add(self.y_op3,               (ir,  8), (1, 1), CEN, 0)
        sizer.Add(self.y3_choice,           (ir,  9), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, ')'),   (ir, 10), (1, 1), LCEN, 0)

        self.plot_btn  = add_button(panel, "New Plot", action=self.onPlot)
        self.oplot_btn = add_button(panel, "OverPlot", action=self.onOPlot)

        ir += 1
        sizer.Add(self.plot_btn,   (ir, 1), (1, 3), CEN, 2)
        sizer.Add(self.oplot_btn,  (ir, 4), (1, 3), CEN, 2)

#         ir += 1
#         sizer.Add(SimpleText(panel, 'Should add fitting options'),
#                   (ir, 1), (1, 10), wx.ALIGN_CENTER)
#
        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(675, 3), style=wx.LI_HORIZONTAL),
                  (ir, 1), (1, 10), wx.ALIGN_CENTER)
        pack(panel, sizer)

        self.plotpanel = PlotPanel(mainpanel, size=(500, 670))
        self.plotpanel.BuildPanel()

        # self.plotpanel.SetBackgroundColour(bgcol)
        self.plotpanel.messenger = self.write_message

        bgcol = panel.GetBackgroundColour()
        bgcol = (bgcol[0]/255., bgcol[1]/255., bgcol[2]/255.)
        self.plotpanel.canvas.figure.set_facecolor(bgcol)

        mainsizer.Add(panel, 0, 1)
        mainsizer.Add(self.plotpanel, 1, wx.GROW|wx.ALL, 1)
        pack(mainpanel, mainsizer)
        return mainpanel

    def init_larch(self):
        t0 = time.time()
        from larch import Interpreter
        from larch.wxlib import inputhook
        self.larch = Interpreter()
        self.larch.symtable.set_symbol('_sys.wx.wxapp', wx.GetApp())
        self.larch.symtable.set_symbol('_sys.wx.parent', self)
        self.SetStatusText('ready')
        self.datagroups = self.larch.symtable
        self.title.SetLabel('')

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def onPlot(self, evt):    self.do_plot(newplot=True)

    def onOPlot(self, evt):   self.do_plot(newplot=False)

    def do_plot(self, newplot=False):

        ix = self.x_choice.GetSelection()
        x  = self.x_choice.GetStringSelection()
        if self.data is None and ix > -1:
            self.SetStatusText( 'cannot plot - no valid data')
        xop = self.x_op.GetStringSelection()
        yop1 = self.y_op1.GetStringSelection()
        yop2 = self.y_op2.GetStringSelection()
        yop3 = self.y_op3.GetStringSelection()

        y1 = self.y1_choice.GetStringSelection()
        y2 = self.y2_choice.GetStringSelection()
        y3 = self.y3_choice.GetStringSelection()
        if y1 == '': y1 = '1'
        if y2 == '': y2 = '1'
        if y3 == '': y3 = '1'

        gname = self.groupname
        lgroup = getattr(self.larch.symtable, gname)

        xlabel_ = xlabel = x
        xunits = lgroup.column_units[ix]
        if xunits != '':
            xlabel = '%s (%s)' % (xlabel, xunits)

        x = "%s.get_data('%s')" % (gname, x)

        if xop == 'log': x = "log(%s)" % x

        ylabel = "[%s%s%s]%s%s" % (y1, yop2, y2, yop3, y3)
        if y2 == '1' and yop2 in ('*', '/') or y2 == '0' and yop2 in ('+', '-'):
            ylabel = "(%s%s%s" % (y1, yop3, y3)
            if y3 == '1' and yop3 in ('*', '/') or y3 == '0' and yop3 in ('+', '-'):
                ylabel = "%s" % (y1)
        elif y3 == '1' and yop3 in ('*', '/') or y3 == '0' and yop3 in ('+', '-'):
            ylabel = "%s%s%s" % (y1, yop2, y2)
        if yop1 != '':
            yoplab = yop1.replace('deriv', 'd')
            ylabel = '%s(%s)' % (yoplab, ylabel)
            if '(' in yop1: ylabel = "%s)" % ylabel

        y1 = y1 if y1 in ('0, 1') else "%s.get_data('%s')" % (gname, y1)
        y2 = y2 if y2 in ('0, 1') else "%s.get_data('%s')" % (gname, y2)
        y3 = y3 if y3 in ('0, 1') else "%s.get_data('%s')" % (gname, y3)

        y = "%s((%s %s %s) %s (%s))" % (yop1, y1, yop2, y2, yop3, y3)
        if '(' in yop1: y = "%s)" % y
        if 'deriv' in yop1:
            y = "%s/deriv(%s)" % (y, x)
            ylabel = '%s/d(%s)' % (ylabel, xlabel_)

        fmt = "plot(%s, %s, label='%s', xlabel='%s', ylabel='%s', new=%s)"
        cmd = fmt % (x, y, self.data.fname, xlabel, ylabel, repr(newplot))
        self.larch(cmd)

    def ShowFile(self, evt=None, filename=None, **kws):
        if filename is None and evt is not None:
            filename = evt.GetString()

        key = filename
        if filename in self.filemap:
            key = self.filemap[filename]
        if not hasattr(self.datagroups, key):
            print 'cannot find key ', key
            return
        self.data = getattr(self.datagroups, key)
        self.groupname = key

        xcols, ycols = [], ['0', '1']
        for i, k in  enumerate(self.data.column_keys):
            if k.startswith('p'):
                xcols.append(self.data.column_names[i])
            elif k.startswith('d'):
                ycols.append(self.data.column_names[i])
        ycols.extend(xcols)

        self.title.SetLabel(self.data.filename)
        self.x_choice.SetItems(xcols)
        self.x_choice.SetSelection(0)
        self.y1_choice.SetItems(ycols)
        self.y1_choice.SetSelection(3)
        self.y2_choice.SetItems(ycols)
        self.y2_choice.SetSelection(1)
        self.y3_choice.SetItems(ycols)
        self.y3_choice.SetSelection(1)

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
        for nam in dir(self.larch.symtable._plotter):
            obj = getattr(self.larch.symtable._plotter, nam)
            try:
                obj.Destroy()
            except:
                pass
        for nam in dir(self.larch.symtable._sys.wx):
            obj = getattr(self.larch.symtable._sys.wx, nam)
            del obj

        self.Destroy()

    def onReadScan(self, evt=None):
        dlg = wx.FileDialog(self, message="Load EpicsScan Settings",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            path = path.replace('\\', '/')
            if path in self.filemap:
                re_read = popup(self, "Re-read file '%s'?" % path, 'Re-read file?')
                print 'read again ', re_read
            try:
                dfile = StepScanData(path)
            except IOError:
                print 'should popup ioerror'
            if dfile._valid and self.larch is not None:
                p, fname = os.path.split(path)
                #path = os.path.join(p, fname)
                #print path

                gname = randname(n=5)
                if hasattr(self.datagroups, gname):
                    time.sleep(0.005)
                    gname = randname(n=6)
                print 'Larch:: ', gname, path
                self.larch("%s = read_stepscan('%s')" % (gname, path))
                self.larch("%s.fname = '%s'" % (gname, fname))
                self.filelist.Append(fname)
                self.filemap[fname] = gname
                self.ShowFile(filename=fname)
            else:
                print 'should popup invalid file message'
            print 'file read success: ', path
        dlg.Destroy()

class ViewerApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, dbname=None, **kws):
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
