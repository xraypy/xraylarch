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
from xdifile import XDIFile
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
        self.SetSize((775, 600))
        self.SetFont(Font(9))

        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ["Initializing....", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

    def createMainPanel(self):
        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(175)

        self.filelist  = wx.ListBox(splitter)
        self.filelist.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.filelist.Bind(wx.EVT_LISTBOX, self.ShowFile)

        self.detailspanel = self.createDetailsPanel(splitter)

        splitter.SplitVertically(self.filelist, self.detailspanel, 1)
        wx.CallAfter(self.init_larch)

    def createDetailsPanel(self, parent):
        mainpanel = wx.Panel(parent)
        mainsizer = wx.BoxSizer(wx.VERTICAL)

        panel = wx.Panel(mainpanel)
        sizer = wx.GridBagSizer(8, 10)
        self.title = SimpleText(panel, 'initializing...')
        ir = 0
        sizer.Add(self.title, (ir, 0), (1, 8), CEN, 2)
        # x-axis

        self.x_choice = add_choice(panel, choices=[],          size=(120, -1))
        self.x_op     = add_choice(panel, choices=('', 'log'), size=(75, -1))

        ir += 1
        sizer.Add(SimpleText(panel, 'X='), (ir, 0), (1, 1), CEN, 0)
        sizer.Add(self.x_op,               (ir, 1), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, '('),  (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.x_choice,           (ir, 3), (1, 1), RCEN, 0)
        sizer.Add(SimpleText(panel, ')'),  (ir, 4), (1, 1), CEN, 0)

        self.y_op1  = [0,0]
        self.y_op2  = [0,0]
        self.y_op3  = [0,0]
        self.y_arr1 = [0,0]
        self.y_arr2 = [0,0]
        self.y_arr3 = [0,0]

        for i in range(2):
            label = 'Y%i=' % (i+1)
            self.y_op1[i] = add_choice(panel, size=(75, -1),
                                       choices=('', 'log', '-log', 'deriv', '-deriv',
                                                'deriv(log', 'deriv(-log'))
            self.y_op2[i] = add_choice(panel, choices=('+', '-', '*', '/'), size=(50, -1))
            self.y_op3[i] = add_choice(panel, choices=('+', '-', '*', '/'), size=(50, -1))
            self.y_arr1[i] = add_choice(panel, choices=[], size=(120, -1))
            self.y_arr2[i] = add_choice(panel, choices=[], size=(120, -1))
            self.y_arr3[i] = add_choice(panel, choices=[], size=(120, -1))

            self.y_op1[i].SetSelection(0)
            self.y_op2[i].SetSelection(3)
            self.y_op3[i].SetSelection(3)

            ir += 1
            sizer.Add(SimpleText(panel, label), (ir,  0), (1, 1), CEN, 0)
            sizer.Add(self.y_op1[i],            (ir,  1), (1, 1), CEN, 0)
            sizer.Add(SimpleText(panel, '[('),  (ir,  2), (1, 1), CEN, 0)
            sizer.Add(self.y_arr1[i],           (ir,  3), (1, 1), CEN, 0)
            sizer.Add(self.y_op2[i],            (ir,  4), (1, 1), CEN, 0)
            sizer.Add(self.y_arr2[i],           (ir,  5), (1, 1), CEN, 0)
            sizer.Add(SimpleText(panel, ')'),   (ir,  6), (1, 1), CEN, 0)
            sizer.Add(self.y_op3[i],            (ir,  7), (1, 1), CEN, 0)
            sizer.Add(self.y_arr3[i],           (ir,  8), (1, 1), CEN, 0)
            sizer.Add(SimpleText(panel, ']'),   (ir,  9), (1, 1), LCEN, 0)

        self.plot_btn  = add_button(panel, "New Plot", action=self.onPlot)
        self.oplot_btn = add_button(panel, "OverPlot", action=self.onOPlot)

        ir += 1
        sizer.Add(self.plot_btn,   (ir, 0), (1, 2), CEN, 2)
        sizer.Add(self.oplot_btn,  (ir, 2), (1, 2), CEN, 2)

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

        gname = self.groupname
        lgroup = getattr(self.larch.symtable, gname)

        xfmt = "%s._x1_ = %s(%s)"
        yfmt = "%s._y1_ = %s((%s %s %s) %s (%s))"
        xop = self.x_op.GetStringSelection()

        xlabel = x
        xunits = lgroup.array_units[ix]
        if xunits != '':
            xlabel = '%s (%s)' % (xlabel, xunits)

        for i in range(2):
            pass # print 'IY SIDE = ', i

        op1 = self.y_op1[0].GetStringSelection()
        op2 = self.y_op2[0].GetStringSelection()
        op3 = self.y_op3[0].GetStringSelection()

        y1 = l1 = self.y_arr1[0].GetStringSelection()
        y2 = l2 = self.y_arr2[0].GetStringSelection()
        y3 = l3 = self.y_arr3[0].GetStringSelection()
        if y1 not in ('0', '1'):  y1 = "%s.%s" % (gname, y1)
        if y2 not in ('0', '1'):  y2 = "%s.%s" % (gname, y2)
        if y3 not in ('0', '1'):  y3 = "%s.%s" % (gname, y3)
        if x not in ('0', '1'):  x = "%s.%s" % (gname, x)
        self.larch(xfmt % (gname, xop, x))
        self.larch(yfmt % (gname, op1, y1, op2, y2, op3, y3))

        path, fname = os.path.split(lgroup.filename)
        label = "%s: %s((%s%s%s)%s%s)" % (lgroup.filename, op1, l1, op2, l2, op3, l3)

        self.plotpanel.plot(lgroup._x1_, lgroup._y1_, label=label)

        old = """
        if xop == 'log': x = "log(%s)" % x

        ylabel = "[%s%s%s]%s%s" % (y1_1, y1_op2, y2_1, y1_op3, y3_1)

        if y2_1 == '1' and yop2 in ('*', '/') or y2 == '0' and yop2 in ('+', '-'):
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
        """

    def ShowFile(self, evt=None, filename=None, **kws):
        if filename is None and evt is not None:
            filename = evt.GetString()

        key = filename
        if filename in self.filemap:
            key = self.filemap[filename]
        if not hasattr(self.datagroups, key):
            print 'cannot find key ', key
            return
        data = getattr(self.datagroups, key)
        self.groupname = key

        xcols = data.array_labels[:]
        ycols = data.array_labels[:] + ['1', '0']
        ncols = len(xcols)
        self.title.SetLabel(data.filename)
        self.x_choice.SetItems(xcols)
        self.x_choice.SetSelection(0)
        for i in range(2):
            self.y_arr1[i].SetItems(ycols)
            self.y_arr2[i].SetItems(ycols)
            self.y_arr3[i].SetItems(ycols)
            self.y_arr1[i].SetSelection(ncols)
            self.y_arr2[i].SetSelection(ncols)
            self.y_arr3[i].SetSelection(ncols)
        self.y_arr1[0].SetSelection(1)

    def createMenus(self):
        ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        #
        fmenu = wx.Menu()
        pmenu = wx.Menu()
        add_menu(self, fmenu, "&Open Scan File\tCtrl+O",
                 "Read Scan File",  self.onReadScan)

        fmenu.AppendSeparator()
        add_menu(self, fmenu, "&Copy\tCtrl+C",
                 "Copy Figure to Clipboard", ppnl.canvas.Copy_to_Clipboard)
        add_menu(self, fmenu, "&Save\tCtrl+S", "Save Figure", self.save_figure)
        add_menu(self, fmenu, "&Print\tCtrl+P", "Print Figure", ppnl.Print)
        add_menu(self, fmenu, "Page Setup", "Print Page Setup", ppnl.PrintSetup)
        add_menu(self, fmenu, "Preview", "Print Preview", ppnl.PrintPreview)

        fmenu.AppendSeparator()
        add_menu(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)

        add_menu(self, pmenu, "Configure\tCtrl+K",
                 "Configure Plot", ppnl.configure)
        add_menu(self, pmenu, "Unzoom\tCtrl+Z", "Unzoom Plot", ppnl.unzoom)
        pmenu.AppendSeparator()
        add_menu(self, pmenu, "Toggle Legend\tCtrl+L",
                 "Toggle Legend on Plot", ppnl.toggle_legend)
        add_menu(self, pmenu, "Toggle Grid\tCtrl+G",
                 "Toggle Grid on Plot", ppnl.toggle_grid)


        self.menubar.Append(fmenu, "&File")
        self.menubar.Append(pmenu, "Plot Options")
        self.SetMenuBar(self.menubar)

    def save_figure(self,event=None, transparent=False, dpi=600):
        """ save figure image to file"""
        if self.plotpanel is not None:
            self.plotpanel.save_figure(event=event,
                                   transparent=transparent, dpi=dpi)

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
        dlg = wx.FileDialog(self, message="Load Epics Scan Data File",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS, style=wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            path = path.replace('\\', '/')
            if path in self.filemap:
                if wx.ID_YES != popup(self, "Re-read file '%s'?" % path,
                                      'Re-read file?'):
                    return

            gname = randname(n=5)
            if hasattr(self.datagroups, gname):
                time.sleep(0.005)
                gname = randname(n=6)
            parent, fname = os.path.split(path)
            self.larch("%s = read_xdi('%s')" % (gname, path))
            self.larch("%s.path  = '%s'"     % (gname, path))
            self.filelist.Append(fname)
            self.filemap[fname] = gname
            print 'Larch:: ', gname, path, fname
            self.ShowFile(filename=fname)

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
