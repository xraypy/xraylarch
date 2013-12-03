#!/usr/bin/env python
"""

"""
import os
import time
import shutil
import numpy as np
from random import randrange
from functools import partial
from datetime import timedelta

import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection
from wx._core import PyDeadObjectError

import epics
from epics.wx import DelayedEpicsCallback, EpicsFunction

from larch import Interpreter, use_plugin_path, isParameter
from larch.larchlib import read_workdir, save_workdir
from larch.fitting import fit_report

use_plugin_path('math')
from fitpeak import fit_peak

use_plugin_path('io')
from gse_escan import gsescan_group
from xdi import read_xdi

use_plugin_path('xafs')
from pre_edge import find_e0, pre_edge

from wxmplot import PlotFrame, PlotPanel

from wxutils import (SimpleText, FloatCtrl, pack, Button,
                     Choice,  Check, MenuItem,
                     CEN, RCEN, LCEN, FRAMESTYLE, Font)

CEN |=  wx.ALL
FILE_WILDCARDS = "Scan Data Files(*.0*,*.dat,*.xdi)|*.0*;*.dat;*.xdi|All files (*.*)|*.*"
FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS


PRE_OPS = ('', 'log', '-log', 'deriv', '-deriv', 'deriv(log', 'deriv(-log')
ARR_OPS = ('+', '-', '*', '/')

SCANGROUP = '_scan'
def randname(n=6):
    "return random string of n (default 6) lowercase letters"
    return ''.join([chr(randrange(26)+97) for i in range(n)])

class ScanViewerFrame(wx.Frame):
    _about = """Scan 2D Plotter
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, _larch=None, **kws):
            
        wx.Frame.__init__(self, None, -1, style=FRAMESTYLE)
        self.filemap = {}
        title = "ASCII Column Data File Viewer"
        self.larch = None
        self.plotframe = None

        self.SetTitle(title)
        self.SetSize((850, 650))
        self.SetFont(Font(9))

        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ["Initializing....", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)
        read_workdir('scanviewer.dat')

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
        sizer = wx.GridBagSizer(8, 7)

        self.title = SimpleText(panel, 'initializing...')
        ir = 0
        sizer.Add(self.title, (ir, 0), (1, 6), LCEN, 2)
        # x-axis

        self.xarr = Choice(panel, choices=[],
                               action=self.onYchoice,  size=(120, -1))
        self.xop  = Choice(panel, choices=('', 'log'),
                               action=self.onYchoice, size=(75, -1))

        ir += 1
        sizer.Add(SimpleText(panel, 'X = '), (ir, 0), (1, 1), CEN, 0)
        sizer.Add(self.xop,                  (ir, 1), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, '('),    (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.xarr,                 (ir, 3), (1, 1), RCEN, 0)
        sizer.Add(SimpleText(panel, ')'),    (ir, 4), (1, 1), CEN, 0)

        self.yops = []
        self.yarr = []
        
        opts= {'choices':[], 'size':(120, -1), 'action':self.onYchoice}
        for i in range(3):
            self.yarr.append(Choice(panel, **opts))


        for opts, sel, siz in ((PRE_OPS, 0, 75),
                               (ARR_OPS, 3, 50), (ARR_OPS, 3, 50)):
            w1 = Choice(panel, choices=opts, action=self.onYchoice,
                            size=(siz, -1))
            w1.SetSelection(sel)
            self.yops.append(w1)

        ir += 1            
        label = 'Y = ' 
        sizer.Add(SimpleText(panel, label), (ir, 0), (1, 1), CEN, 0)
        sizer.Add(self.yops[0],             (ir, 1), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, '[('),  (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.yarr[0],             (ir, 3), (1, 1), CEN, 0)
        sizer.Add(self.yops[1],             (ir, 4), (1, 1), CEN, 0)
        sizer.Add(self.yarr[1],             (ir, 5), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, ')'),   (ir, 6), (1, 1), LCEN, 0)
        ir += 1
        sizer.Add(self.yops[2],             (ir, 4), (1, 1), CEN, 0)
        sizer.Add(self.yarr[2],             (ir, 5), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, ']'),   (ir, 6), (1, 1), LCEN, 0)

        ir += 1
        self.dtcorr   = Check(panel, default=True, label='correct deadtime?')
        sizer.Add(self.dtcorr,  (ir,   0), (1, 3), LCEN, 0)

        pack(panel, sizer)

        self.nb = flat_nb.FlatNotebook(mainpanel, -1, agwStyle=FNB_STYLE)

        self.nb.SetTabAreaColour(wx.Colour(248,248,240))
        self.nb.SetActiveTabColour(wx.Colour(254,254,195))

        self.nb.SetNonActiveTabTextColour(wx.Colour(40,40,180))
        self.nb.SetActiveTabTextColour(wx.Colour(80,0,0))
 
        self.xas_panel = self.CreateXASPanel(self.nb) # mainpanel)
        self.fit_panel = self.CreateFitPanel(self.nb) # mainpanel)

        self.nb.AddPage(self.fit_panel, ' General Analysis ', True)
        self.nb.AddPage(self.xas_panel, ' XAS Processing ',   True)
        mainsizer.Add(panel,   0, LCEN|wx.EXPAND, 2)

        mainsizer.Add(self.nb, 1, LCEN|wx.EXPAND, 2)

        btnbox   = wx.Panel(mainpanel)
        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        for ttl, opt in (('New Plot',   'new'),
                         ('Plot (left axis)',  'left'),
                         ('Plot (right axis)', 'right')):
            
            btnsizer.Add(Button(btnbox, ttl, size=(130, -1),
                                action=partial(self.onPlot, opt=opt)), LCEN, 1)

        pack(btnbox, btnsizer)
        mainsizer.Add(btnbox, 1, LCEN, 2)

        pack(mainpanel, mainsizer)

        return mainpanel

    def CreateFitPanel(self, parent):
        p = panel = wx.Panel(parent)
        self.fit_model   = Choice(panel, size=(100, -1),
                                      choices=('Gaussian', 'Lorentzian',
                                               'Voigt', 'Linear', 'Quadratic',
                                               'Step', 'Rectangle',
                                               'Exponential'))
        self.fit_bkg = Choice(panel, size=(100, -1),
                                  choices=('None', 'constant', 'linear', 'quadtratic'))
        self.fit_step = Choice(panel, size=(100, -1),
                                  choices=('linear', 'error function', 'arctan'))

        self.fit_report = wx.StaticText(panel, -1, "", (180, 200))
        sizer = wx.GridBagSizer(10, 4)
        sizer.Add(SimpleText(p, 'Fit Model: '),           (0, 0), (1, 1), LCEN)
        sizer.Add(self.fit_model,                         (0, 1), (1, 1), LCEN)

        sizer.Add(SimpleText(p, 'Background: '),          (1, 0), (1, 1), LCEN)
        sizer.Add(self.fit_bkg,                           (1, 1), (1, 1), LCEN)

        sizer.Add(SimpleText(p, 'Step Function Form: '),  (2, 0), (1, 1), LCEN)
        sizer.Add(self.fit_step,                          (2, 1), (1, 1), LCEN)
        sizer.Add(Button(panel, 'Show Fit', size=(100, -1),
                             action=self.onFitPeak),       (3, 0), (1, 1), LCEN)
        sizer.Add(self.fit_report,                         (0, 2), (4, 2), LCEN, 3)
        pack(panel, sizer)
        return panel

    def CreateXASPanel(self, parent):
        p = panel = wx.Panel(parent)
        self.xas_autoe0   = Check(panel, default=True, label='auto?')
        self.xas_autostep = Check(panel, default=True, label='auto?')
        self.xas_op       = Choice(panel, size=(95, -1),
                                       choices=('Raw Data', 'Pre-edged',
                                                'Normalized', 'Flattened'))
        self.xas_e0   = FloatCtrl(panel, value  = 0, precision=3, size=(95, -1))
        self.xas_step = FloatCtrl(panel, value  = 0, precision=3, size=(95, -1))
        self.xas_pre1 = FloatCtrl(panel, value=-200, precision=1, size=(95, -1))
        self.xas_pre2 = FloatCtrl(panel, value= -30, precision=1, size=(95, -1))
        self.xas_nor1 = FloatCtrl(panel, value=  30, precision=1, size=(95, -1))
        self.xas_nor2 = FloatCtrl(panel, value= 300, precision=1, size=(95, -1))
        self.xas_vict = Choice(panel, size=(50, -1), choices=('0', '1', '2', '3'))
        self.xas_nnor = Choice(panel, size=(50, -1), choices=('0', '1', '2', '3'))
        self.xas_vict.SetSelection(1)
        self.xas_nnor.SetSelection(2)
        sizer = wx.GridBagSizer(10, 4)

        sizer.Add(SimpleText(p, 'Plot XAS as: '),         (0, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'E0 : '),                 (1, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Edge Step: '),           (2, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Pre-edge range: '),      (3, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Normalization range: '), (4, 0), (1, 1), LCEN)

        sizer.Add(self.xas_op,                 (0, 1), (1, 1), LCEN)
        sizer.Add(self.xas_e0,                 (1, 1), (1, 1), LCEN)
        sizer.Add(self.xas_step,               (2, 1), (1, 1), LCEN)
        sizer.Add(self.xas_pre1,               (3, 1), (1, 1), LCEN)
        sizer.Add(SimpleText(p, ':'),          (3, 2), (1, 1), LCEN)
        sizer.Add(self.xas_pre2,               (3, 3), (1, 1), LCEN)
        sizer.Add(self.xas_nor1,               (4, 1), (1, 1), LCEN)
        sizer.Add(SimpleText(p, ':'),          (4, 2), (1, 1), LCEN)
        sizer.Add(self.xas_nor2,               (4, 3), (1, 1), LCEN)

        sizer.Add(self.xas_autoe0,             (1, 2), (1, 2), LCEN)
        sizer.Add(self.xas_autostep,           (2, 2), (1, 2), LCEN)

        sizer.Add(SimpleText(p, 'Victoreen:'), (3, 4), (1, 1), LCEN)
        sizer.Add(self.xas_vict,               (3, 5), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'PolyOrder:'), (4, 4), (1, 1), LCEN)
        sizer.Add(self.xas_nnor,               (4, 5), (1, 1), LCEN)

        pack(panel, sizer)
        return panel

    def onFitPeak(self, evt=None):
        gname = self.groupname
        if self.dtcorr.IsChecked():
            print( 'fit needs to dt correct!')

        dtext = []
        model = self.fit_model.GetStringSelection().lower()
        dtext.append('Fit Model: %s' % model)
        bkg =  self.fit_bkg.GetStringSelection()
        if bkg == 'None':
            bkg = None
        if bkg is None:
            dtext.append('No Background')
        else:
            dtext.append('Background: %s' % bkg)

        step = self.fit_step.GetStringSelection().lower()
        if model in ('step', 'rectangle'):
            dtext.append('Step form: %s' % step)
        lgroup =  getattr(self.larch.symtable, gname)
        x = lgroup._x1_
        y = lgroup._y1_
        pgroup = fit_peak(x, y, model, background=bkg, step=step,
                          _larch=self.larch)
        text = fit_report(pgroup.params, _larch=self.larch)
        dtext.append('Parameters: ')
        for pname in dir(pgroup.params):
            par = getattr(pgroup.params, pname)
            if isParameter(par):
                ptxt = "    %s= %.4f" % (par.name, par.value)
                if (hasattr(par, 'stderr') and par.stderr is not None):
                    ptxt = "%s(%.4f)" % (ptxt, par.stderr)
                dtext.append(ptxt)

        dtext = '\n'.join(dtext)
        # plotframe = self.get_plotwindow()
        # plotframe.oplot(x, pgroup.fit, label='fit (%s)' % model)
        text = fit_report(pgroup.params, _larch=self.larch)
        self.fit_report.SetLabel(dtext)

    def xas_process(self, gname, plotopts):
        """ process (pre-edge/normalize) XAS data from XAS form, overwriting
        larch group '_y1_' attribute to be plotted
        """
        print( 'Process XAS ', gname)
        out = self.xas_op.GetStringSelection().lower() # raw, pre, norm, flat
        if out.startswith('raw'):
            return plotopts

        preopts = {'group': gname, 'e0': None, 'step': None}

        lgroup = getattr(self.larch.symtable, gname)

        dtcorr = self.dtcorr.IsChecked()

        if not self.xas_autoe0.IsChecked():
            xmin, xmax = min(lgroup._x1_),  max(lgroup._x1_)
            e0 = self.xas_e0.GetValue()
            if e0 < xmax and e0 > xmin:
                preopts['e0'] = e0

        if not self.xas_autostep.IsChecked():
            preopts['step'] = self.xas_step.GetValue()

        preopts['pre1']  = self.xas_pre1.GetValue()
        preopts['pre2']  = self.xas_pre2.GetValue()
        preopts['norm1'] = self.xas_nor1.GetValue()
        preopts['norm2'] = self.xas_nor2.GetValue()

        preopts['nvict'] = self.xas_vict.GetSelection()
        preopts['nnorm'] = self.xas_nnor.GetSelection()

        preopts = ", ".join(["%s=%s" %(k, v) for k,v in preopts.items()])
        preedge_cmd = "pre_edge(%s._x1_, %s._y1_, %s)" % (gname, gname, preopts)

        self.larch(preedge_cmd)

        self.xas_e0.SetValue(lgroup.e0)
        self.xas_step.SetValue(lgroup.edge_step)

        if out.startswith('pre'):
            self.larch('%s._y1_ = %s.norm * %s.edge_step' % (gname, gname, gname))
        elif out.startswith('norm'):
            self.larch('%s._y1_ = %s.norm' % (gname, gname))
        elif out.startswith('flat'):
            self.larch('%s._y1_ = %s.flat' % (gname, gname))

        return plotopts

    def init_larch(self):
        t0 = time.time()
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

    def onYchoice(self, evt=None, side='left'):
        self.onPlot()

    def onPlot(self, evt=None, opt='new', npts=None):
        # 'new', 'New Window'),
        # 'left', 'Left Axis'),
        # 'right', 'Right Axis')):
        # 'update',  from scan

        optwords = opt.split()
        print 'onPlot ', opt, npts

        try:
            self.plotframe.Show()
        except: #  wx.PyDeadObjectError
            self.plotframe = PlotFrame(self, size=(650, 400))
            self.plotframe.Show()
            self.plotpanel = self.plotframe.panel            
        

        dtcorr = self.dtcorr.IsChecked()

        side = 'left'
        update = False
        plotcmd = self.plotpanel.plot
        if opt in ('left', 'right'):
            side = opt
            plotcmd = self.plotpanel.oplot
        elif optwords[0] == 'update'  and npts > 4:
            plotcmd = self.plotpanel.update_line
            update = True

        popts = {'side': side}

        ix = self.xarr.GetSelection()
        x  = self.xarr.GetStringSelection()

        print( ' X -> ' ,  ix, x)
        try:
            gname = self.groupname
            lgroup = getattr(self.larch.symtable, gname)
        except:
            gname = SCANGROUP
            lgroup = getattr(self.larch.symtable, gname)

        print( ' ==> ', ix, x, gname)
        xfmt = "%s._x1_ = %s(%s)"
        yfmt = "%s._y1_ = %s((%s %s %s) %s (%s))"
        xop = self.xop.GetStringSelection()
        
        print( ' L Group ', lgroup)

        xlabel = x
        try:
            xunits = lgroup.array_units[ix]
        except:
            xunits = ''
        if xop != '':
            xlabel = "%s(%s)" % (xop, xlabel)
        if xunits != '':
            xlabel = '%s (%s)' % (xlabel, xunits)
        popts['xlabel'] = xlabel

        op1 = self.yops[0].GetStringSelection()
        op2 = self.yops[1].GetStringSelection()
        op3 = self.yops[2].GetStringSelection()

        y1 = self.yarr[0].GetStringSelection()
        y2 = self.yarr[1].GetStringSelection()
        y3 = self.yarr[2].GetStringSelection()

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

        if y1 in ('0', '1'):  
            y1 = int(yl1)
        else:
            y1 = lgroup.get_data(y1, correct=dtcorr)
        if y2 in ('0', '1'):  
            y2 = int(y2)
        else:
            y2 = lgroup.get_data(y2, correct=dtcorr)
        if y3 in ('0', '1'):  
            y3 = int(y3)
        else:
            y3 = lgroup.get_data(y3, correct=dtcorr)
        if x not in ('0', '1'): 
            x = lgroup.get_data(x)

        setattr(lgroup, '_x',   x)
        setattr(lgroup, '_y1', y1)
        setattr(lgroup, '_y2', y2)
        setattr(lgroup, '_y3', y3)
        
        print ("%s._y1_ = %s((%s._y1 %s %s._y2) %s %s._y3)"  %
               (gname, op1, gname, op2, gname, op3, gname))

        self.larch("%s._xplot_ = %s(%s._x)" % (gname, xop, gname))
        self.larch("%s._yplot_ = %s((%s._y1 %s %s._y2) %s %s._y3)"  %
                   (gname, op1, gname, op2, gname, op3, gname))

        try:
            npts = min(len(lgroup._xplot_), len(lgroup._yplot_))
        except AttributeError:
            print( 'npts borked ')
            return
                
        lgroup._xplot_ = np.array( lgroup._xplot_[:npts])
        lgroup._yplot_ = np.array( lgroup._yplot_[:npts])
       

        path, fname = os.path.split(lgroup.filename)
        popts['label'] = "%s: %s" % (fname, ylabel)
        if side == 'right':
            popts['y2label'] = ylabel
        else:
            popts['ylabel'] = ylabel

        if plotcmd == self.plotpanel.plot:
            popts['title'] = fname

        # XAFS Processing!
        # if (self.nb.GetCurrentPage() == self.xas_panel):
        #     popts = self.xas_process(gname, popts)

        if update:
            self.plotpanel.set_xlabel(popts['xlabel'])
            self.plotpanel.set_ylabel(popts['ylabel'])
            
            plotcmd(0, lgroup._xplot_, lgroup._yplot_, draw=True,
                        update_limits=True) # ((npts < 5) or (npts % 5 == 0)))
            
            self.plotpanel.set_xylims((
                min(lgroup._xplot_), max(lgroup._xplot_),
                min(lgroup._yplot_), max(lgroup._yplot_)))
                                      
        else:
            plotcmd(lgroup._xplot_, lgroup._yplot_, **popts)
            self.plotpanel.canvas.draw()
            
    def ShowFile(self, evt=None, filename=None, **kws):
        if filename is None and evt is not None:
            filename = evt.GetString()
        key = filename
        if filename in self.filemap:
            key = self.filemap[filename]
        print ' KEY ', filename, key
        print hasattr(self.datagroups, key)
        if key == SCANGROUP:
            #array_labels = [fix_filename(s.name) for s in self.scandb.get_scandata()]
            title = filename
        elif hasattr(self.datagroups, key):
            data = getattr(self.datagroups, key)
            title = data.filename
            if hasattr(data, 'array_labels'):
                array_labels = data.array_labels[:]
            elif hasattr(data, 'column_labels'):
                array_labels = data.column_labels[:]
            else:
                array_labels = []
                for attr in dir(data):
                    if isinstance(getattr(data, attr), np.ndarray):
                        array_labels.append(attr)
                        

        self.groupname = key
        xcols  = array_labels[:]
        ycols  = array_labels[:]
        y2cols = array_labels[:] + ['1.0', '0.0', '']
        ncols  = len(xcols)
        self.title.SetLabel(title)

        _xarr = self.xarr.GetStringSelection()
        if len(_xarr) < 1:
            _xarr = xcols[0]

        _yarr = [[], [], []]
        for j in range(3):
            _yarr[j] = self.yarr[j].GetStringSelection()
            
        self.xarr.SetItems(xcols)
        self.xarr.SetStringSelection(_xarr)
        for j in range(3):
            if j == 0:
                self.yarr[j].SetItems(ycols)                
            else:
                self.yarr[j].SetItems(y2cols)
            self.yarr[j].SetStringSelection(_yarr[j])

        inb = 0
        for colname in xcols:
            if 'energ' in colname.lower():
                inb = 1
        self.nb.SetSelection(inb)

    def createMenus(self):
        # ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        #
        fmenu = wx.Menu()
        pmenu = wx.Menu()
        MenuItem(self, fmenu, "&Open Data File\tCtrl+O",
                 "Read Scan File",  self.onReadScan)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)

        self.menubar.Append(fmenu, "&File")

        # fmenu.AppendSeparator()
        # MenuItem(self, fmenu, "&Copy\tCtrl+C",
        #          "Copy Figure to Clipboard", self.onClipboard)
        # MenuItem(self, fmenu, "&Save\tCtrl+S", "Save Figure", self.onSaveFig)
        # MenuItem(self, fmenu, "&Print\tCtrl+P", "Print Figure", self.onPrint)
        # MenuItem(self, fmenu, "Page Setup", "Print Page Setup", self.onPrintSetup)
        # MenuItem(self, fmenu, "Preview", "Print Preview", self.onPrintPreview)
        #

        # MenuItem(self, pmenu, "Configure\tCtrl+K",
        #         "Configure Plot", self.onConfigurePlot)
        #MenuItem(self, pmenu, "Unzoom\tCtrl+Z", "Unzoom Plot", self.onUnzoom)
        ##pmenu.AppendSeparator()
        #MenuItem(self, pmenu, "Toggle Legend\tCtrl+L",
        #         "Toggle Legend on Plot", self.onToggleLegend)
        #MenuItem(self, pmenu, "Toggle Grid\tCtrl+G",
        #         "Toggle Grid on Plot", self.onToggleGrid)
        # self.menubar.Append(pmenu, "Plot Options")
        self.SetMenuBar(self.menubar)


    def onAbout(self,evt):
        dlg = wx.MessageDialog(self, self._about,"About Epics StepScan",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,evt):
        save_workdir('scanviewer.dat')
        try:
            self.plotframe.Destroy()
        except:
            pass
        for nam in dir(self.larch.symtable._sys.wx):
            obj = getattr(self.larch.symtable._sys.wx, nam)
            del obj

        self.Destroy()

    def onReadScan(self, evt=None):
        dlg = wx.FileDialog(self, message="Load Column Data File",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS, style=wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            path = path.replace('\\', '/')
            if path in self.filemap:
                if wx.ID_YES != popup(self, "Re-read file '%s'?" % path,
                                      'Re-read file?'):
                    return

            gname = 's001'
            count, maxcount = 1, 999
            while hasattr(self.datagroups, gname) and count < maxcount:
                count += 1
                gname = 's%3.3i' % count
            
            if hasattr(self.datagroups, gname):
                gname = randname()
                
            parent, fname = os.path.split(path)
            fh = open(path, 'r')
            line1 = fh.readline().lower()
            fh.close()
            if 'epics scan' in line1:
                self.larch("%s = read_gsescan('%s')" % (gname, path))
            elif 'xdi' in line1:
                self.larch("%s = read_xdi('%s')" % (gname, path))
            else:
                self.larch("%s = read_ascii('%s')" % (gname, path))
                
            self.larch("%s.path  = '%s'"     % (gname, path))
            self.filelist.Append(fname)
            self.filemap[fname] = gname

            self.ShowFile(filename=fname)

        dlg.Destroy()

class ScanViewer(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, **kws):
        wx.App.__init__(self, **kws)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = ScanViewerFrame()
        frame.Show()
        self.SetTopWindow(frame)

    def OnInit(self):
        self.createApp()
        return True

if __name__ == "__main__":
    ScanViewer().MainLoop()

