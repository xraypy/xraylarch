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
from wx._core import PyDeadObjectError

import epics
from epics.wx import DelayedEpicsCallback, EpicsFunction

from wxmplot import PlotFrame
from xdifile import XDIFile
from ..datafile import StepScanData
from .gui_utils import (SimpleText, FloatCtrl, Closure, pack, add_button,
                        add_menu, add_choice, add_menu, check,
                        CEN, RCEN, LCEN, FRAMESTYLE, Font)

CEN |=  wx.ALL
FILE_WILDCARDS = "Scan Data Files(*.0*,*.dat,*.xdi)|*.0*;*.dat;*.xdi|All files (*.*)|*.*"
FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

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
        self.plotters = []

        self.SetTitle("Step Scan Data File Viewer")
        self.SetSize((700, 450))
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
        panel = wx.Panel(parent)
        sizer = wx.GridBagSizer(8, 7)

        self.title = SimpleText(panel, 'initializing...')
        ir = 0
        sizer.Add(self.title, (ir, 0), (1, 6), LCEN, 2)
        # x-axis

        self.x_choice = add_choice(panel, choices=[],          size=(120, -1))
        self.x_op     = add_choice(panel, choices=('', 'log'), size=(75, -1))

        ir += 1
        sizer.Add(SimpleText(panel, 'X = '), (ir, 0), (1, 1), CEN, 0)
        sizer.Add(self.x_op,               (ir, 1), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, '('),  (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.x_choice,           (ir, 3), (1, 1), RCEN, 0)
        sizer.Add(SimpleText(panel, ')'),  (ir, 4), (1, 1), CEN, 0)

        self.yop1  = add_choice(panel, size=(75, -1),
                                 choices=('', 'log', '-log', 'deriv', '-deriv',
                                            'deriv(log', 'deriv(-log'))
        self.yop2  = add_choice(panel, choices=('+', '-', '*', '/'), size=(50, -1))
        self.yop3  = add_choice(panel, choices=('+', '-', '*', '/'), size=(50, -1))
        self.yarr1 = add_choice(panel, choices=[], size=(120, -1))
        self.yarr2 = add_choice(panel, choices=[], size=(120, -1))
        self.yarr3 = add_choice(panel, choices=[], size=(120, -1))

        self.yop1.SetSelection(0)
        self.yop2.SetSelection(3)
        self.yop3.SetSelection(3)

        ir += 1
        sizer.Add(SimpleText(panel, 'Y = '), (ir,  0), (1, 1), CEN, 0)
        sizer.Add(self.yop1,                 (ir,  1), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, '[('),   (ir,  2), (1, 1), CEN, 0)
        sizer.Add(self.yarr1,                (ir,  3), (1, 1), CEN, 0)
        sizer.Add(self.yop2,                 (ir,  4), (1, 1), CEN, 0)
        sizer.Add(self.yarr2,                (ir,  5), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, ')'),    (ir,  6), (1, 1), LCEN, 0)
        ir += 1
        sizer.Add(self.yop3,                 (ir,  4), (1, 1), CEN, 0)
        sizer.Add(self.yarr3,                (ir,  5), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, ']'),    (ir,  6), (1, 1), LCEN, 0)


        ir += 1
        sizer.Add(SimpleText(panel, ' New Plot: '),  (ir,  0), (1, 2), LCEN, 0)
        sizer.Add(SimpleText(panel, ' Over Plot: '), (ir+1,  0), (1, 2), LCEN, 0)

        for jr, ic, opt, ttl in ((0, 2, 'win new', 'New Window'),
                                 (0, 4, 'win old',  'Old Window'),
                                 (1, 2, 'over left', 'Left Axis'),
                                 (1, 4, 'over right', 'Right Axis')):
            sizer.Add(add_button(panel, ttl, size=(100, -1),
                                 action=Closure(self.onPlot, opt=opt)),
                      (ir+jr, ic), (1, 2), LCEN, 2)

        ir += 2

        self.nb = flat_nb.FlatNotebook(panel, wx.ID_ANY, agwStyle=FNB_STYLE)
        # self.nb.SetBackgroundColour(self.GetBackgroundColour())

        self.xas_panel = self.CreateXASPanel(panel)
        self.fit_panel = self.CreateFitPanel(panel)

        self.nb.AddPage(self.fit_panel, 'General Analysis', True)
        self.nb.AddPage(self.xas_panel, 'XAS Processing', True)

        sizer.Add(self.nb,  (ir,  0), (1, 7), CEN|wx.GROW|wx.ALL, 0)

        pack(panel, sizer)
        return panel

    def onFit(self, evt=None):
        print 'fit!'

    def CreateFitPanel(self, parent):
        p = panel = wx.Panel(parent)
        self.fit_dtcorr  = check(panel, default=True)
        self.fit_btn     = add_button(panel, 'Fit Data', size=(100, -1),
                                 action=self.onFit)

        self.fit_dobkg   = check(panel, default=True)
        self.fit_model   = add_choice(panel, size=(160, -1),
                                      choices=('Linear', 'Quadratic',
                                               'Gaussian', 'Lorentzian',
                                               'Voigt', 'Step', 'Rectangle',
                                               'Exponential'))
        self.fit_bkg = add_choice(panel, size=(160, -1),
                                  choices=('constant', 'linear', 'quadtratic'))
        self.fit_step = add_choice(panel, size=(160, -1),
                                  choices=('linear', 'error function', 'arctan'))

        sizer = wx.GridBagSizer(10, 4)

        sizer.Add(SimpleText(p, 'Correct DeadTime?: '),   (0, 0), (1, 1), LCEN)
        sizer.Add(self.fit_dtcorr,                        (0, 1), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Fit Model: '),           (1, 0), (1, 1), LCEN)
        sizer.Add(self.fit_model,                         (1, 1), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Add Background?: '),     (2, 0), (1, 1), LCEN)
        sizer.Add(self.fit_dobkg,                         (2, 1), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Background Form: '),     (3, 0), (1, 1), LCEN)
        sizer.Add(self.fit_bkg,                           (3, 1), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Step Function Form: '),  (4, 0), (1, 1), LCEN)
        sizer.Add(self.fit_step,                          (4, 1), (1, 1), LCEN)
        sizer.Add(self.fit_btn,  (5, 0), (1, 1), LCEN)

        pack(panel, sizer)
        return panel

    def CreateXASPanel(self, parent):
        p = panel = wx.Panel(parent)
        self.xas_dtcorr   = check(panel, default=True)
        self.xas_autoe0   = check(panel, default=True)
        self.xas_autostep = check(panel, default=True)
        self.xas_autoe0.SetLabel('auto?')
        self.xas_autostep.SetLabel('auto?')
        self.xas_op       = add_choice(panel, size=(120, -1),
                                       choices=('Raw Data', 'Normalized', 'Flattened'))
        self.xas_e0   = FloatCtrl(panel, value  = 0, precision=3, size=(120, -1))
        self.xas_step = FloatCtrl(panel, value  = 0, precision=3, size=(120, -1))
        self.xas_pre1 = FloatCtrl(panel, value=-100, precision=1, size=(120, -1))
        self.xas_pre2 = FloatCtrl(panel, value= -30, precision=1, size=(120, -1))
        self.xas_nor1 = FloatCtrl(panel, value= 100, precision=1, size=(120, -1))
        self.xas_nor2 = FloatCtrl(panel, value= 300, precision=1, size=(120, -1))
        self.xas_prev = add_choice(panel, size=(90, -1), choices=('0', '1', '2', '3'))
        self.xas_nnor = add_choice(panel, size=(90, -1), choices=('0', '1', '2', '3'))
        self.xas_nnor.SetSelection(2)
        sizer = wx.GridBagSizer(10, 4)
        ir = 0
        sizer.Add(SimpleText(p, 'Correct DeadTime?: '),   (0, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Plot XAS as: '),         (1, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'E0 : '),                 (2, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Edge Step: '),           (3, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Pre-edge range: '),      (4, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Normalization range: '), (5, 0), (1, 1), LCEN)

        sizer.Add(self.xas_dtcorr,             (0, 1), (1, 1), LCEN)
        sizer.Add(self.xas_op,                 (1, 1), (1, 1), LCEN)
        sizer.Add(self.xas_e0,                 (2, 1), (1, 1), LCEN)
        sizer.Add(self.xas_step,               (3, 1), (1, 1), LCEN)
        sizer.Add(self.xas_pre1,               (4, 1), (1, 1), LCEN)
        sizer.Add(self.xas_pre2,               (4, 3), (1, 1), LCEN)
        sizer.Add(self.xas_nor1,               (5, 1), (1, 1), LCEN)
        sizer.Add(self.xas_nor2,               (5, 3), (1, 1), LCEN)
        sizer.Add(SimpleText(p, ':'),          (4, 2), (1, 1), LCEN)
        sizer.Add(SimpleText(p, ':'),          (5, 2), (1, 1), LCEN)

        sizer.Add(self.xas_autoe0,             (2, 3), (1, 2), LCEN)
        sizer.Add(self.xas_autostep,           (3, 3), (1, 2), LCEN)

        sizer.Add(SimpleText(p, 'Pre-edge Victoreen Power: '), (6, 0), (1, 2), LCEN)
        sizer.Add(self.xas_prev,  (6, 2), (1, 2), LCEN)
        sizer.Add(SimpleText(p, 'Normalization Polynomial Order: '), (7, 0), (1, 2), LCEN)
        sizer.Add(self.xas_nnor,   (7, 2), (1, 2), LCEN)

        pack(panel, sizer)
        return panel

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

    def get_plotwindow(self, new=False, **kws):
        pframe = None
        if not new:
            while pframe is None:
                try:
                    pframe = self.plotters.pop()
                    pframe.Show()
                    pframe.Raise()
                except IndexError:
                    pframe = None
                    break
                except PyDeadObjectError:
                    pframe = None

        if pframe is None:
            pframe = PlotFrame()
            pframe.Show()
            pframe.Raise()

        self.plotters.append(pframe)

        return pframe

    def onPlot(self, evt=None, opt='over right'):
        # 'win new', 'New Window'),
        # 'win old',  'Old Window'),
        # 'over left', 'Left Axis'),
        # 'over right', 'Right Axis')):
        print 'on Plot nb = ', self.nb.GetCurrentPage() == self.xas_panel
        optwords = opt.split()
        plotframe = self.get_plotwindow(new=('new' in optwords[1]))
        plotcmd = plotframe.plot

        optwords = opt.split()
        side = 'left'
        if optwords[0] == 'over':
            side = optwords[1]
            plotcmd = plotframe.oplot

        popts = {'side': side}

        ix = self.x_choice.GetSelection()
        x  = self.x_choice.GetStringSelection()

        gname = self.groupname
        lgroup = getattr(self.larch.symtable, gname)

        xfmt = "%s._x1_ = %s(%s)"
        yfmt = "%s._y1_ = %s((%s %s %s) %s (%s))"
        xop = self.x_op.GetStringSelection()

        xlabel = x
        xunits = lgroup.array_units[ix]
        if xop != '':
            xlabel = "%s(%s)" % (xop, xlabel)
        if xunits != '':
            xlabel = '%s (%s)' % (xlabel, xunits)
        popts['xlabel'] = xlabel

        op1 = self.yop1.GetStringSelection()
        op2 = self.yop2.GetStringSelection()
        op3 = self.yop3.GetStringSelection()

        y1 = self.yarr1.GetStringSelection()
        y2 = self.yarr2.GetStringSelection()
        y3 = self.yarr3.GetStringSelection()

        ylabel = y1

        if y2 == '':
            y2, op2 = '1', '*'
        else:
            ylabel = "%s%s%s" % (ylabel, op2, y2)
        if y3 == '':
            y3, op3 = '1', '*'
        else:
            ylabel = "(%s)%s%s" % (ylabel, op3, y3)

        if op1 != '':
            ylabel = "%s(%s)" % (op1, ylabel)

        if y1 not in ('0', '1'):  y1 = "%s.%s" % (gname, y1)
        if y2 not in ('0', '1'):  y2 = "%s.%s" % (gname, y2)
        if y3 not in ('0', '1'):  y3 = "%s.%s" % (gname, y3)
        if x not in ('0', '1'):    x = "%s.%s" % (gname, x)

        self.larch(xfmt % (gname, xop, x))
        self.larch(yfmt % (gname, op1, y1, op2, y2, op3, y3))

        path, fname = os.path.split(lgroup.filename)
        popts['label'] = "%s: %s" % (lgroup.filename, ylabel)
        if side == 'right':
            popts['y2label'] = ylabel
        else:
            popts['ylabel'] = ylabel

        if plotcmd == plotframe.plot:
            popts['title'] = fname

        plotcmd(lgroup._x1_, lgroup._y1_, **popts)


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
        ycols = data.array_labels[:]
        y2cols = data.array_labels[:] + ['1.0', '0.0', '']
        ncols = len(xcols)
        self.title.SetLabel(data.filename)
        self.x_choice.SetItems(xcols)
        self.x_choice.SetSelection(0)
        self.yarr1.SetItems(ycols)
        self.yarr1.SetSelection(1)

        self.yarr2.SetItems(y2cols)
        self.yarr3.SetItems(y2cols)
        self.yarr2.SetSelection(len(y2cols))
        self.yarr3.SetSelection(len(y2cols))

    def createMenus(self):
        # ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        #
        fmenu = wx.Menu()
        pmenu = wx.Menu()
        add_menu(self, fmenu, "&Open Scan File\tCtrl+O",
                 "Read Scan File",  self.onReadScan)

        fmenu.AppendSeparator()
        add_menu(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)

        self.menubar.Append(fmenu, "&File")

        # fmenu.AppendSeparator()
        # add_menu(self, fmenu, "&Copy\tCtrl+C",
        #          "Copy Figure to Clipboard", self.onClipboard)
        # add_menu(self, fmenu, "&Save\tCtrl+S", "Save Figure", self.onSaveFig)
        # add_menu(self, fmenu, "&Print\tCtrl+P", "Print Figure", self.onPrint)
        # add_menu(self, fmenu, "Page Setup", "Print Page Setup", self.onPrintSetup)
        # add_menu(self, fmenu, "Preview", "Print Preview", self.onPrintPreview)
        #

        # add_menu(self, pmenu, "Configure\tCtrl+K",
        #         "Configure Plot", self.onConfigurePlot)
        #add_menu(self, pmenu, "Unzoom\tCtrl+Z", "Unzoom Plot", self.onUnzoom)
        ##pmenu.AppendSeparator()
        #add_menu(self, pmenu, "Toggle Legend\tCtrl+L",
        #         "Toggle Legend on Plot", self.onToggleLegend)
        #add_menu(self, pmenu, "Toggle Grid\tCtrl+G",
        #         "Toggle Grid on Plot", self.onToggleGrid)
        # self.menubar.Append(pmenu, "Plot Options")
        self.SetMenuBar(self.menubar)

    def get_plotpanel(self):

        pass

    def onConfigurePlot(self, evt=None):
        ppnl = self.get_plotpanel()
        if ppnl is not None:
            ppnl.configure()

    def onUnzoom(self, evt=None):
        ppnl = self.get_plotpanel()
        if ppnl is not None:
            ppnl.unzoom()

    def onToggleLegend(self, evt=None):
        ppnl = self.get_plotpanel()
        if ppnl is not None:
            ppnl.toggle_legend()

    def onToggleGrid(self, evt=None):
        ppnl = self.get_plotpanel()
        if ppnl is not None:
            ppnl.toggle_grid()

    def onPrint(self, evt=None):
        ppnl = self.get_plotpanel()
        if ppnl is not None:
            ppnl.Print()

    def onPrintSetup(self, evt=None):
        ppnl = self.get_plotpanel()
        if ppnl is not None:
            ppnl.PrintSetup()

    def onPrintPreview(self, evt=None):
        ppnl = self.get_plotpanel()
        if ppnl is not None:
            ppnl.PrintPreview()



    def onClipboard(self, evt=None):
        ppnl = self.get_plotpanel()
        if ppnl is not None:
            ppnl.canvas.Copy_to_Clipboard()

    def onSaveFig(self,event=None, transparent=False, dpi=600):
        """ save figure image to file"""
        ppnl = self.get_plotpanel()
        if ppnl is not None:
            ppnl.save_figure(event=event,
                             transparent=transparent, dpi=dpi)

    def onAbout(self,evt):
        dlg = wx.MessageDialog(self, self._about,"About Epics StepScan",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,evt):
        for obj in self.plotters:
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
