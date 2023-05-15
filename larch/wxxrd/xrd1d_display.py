#!/usr/bin/env pythonw
'''
GUI for displaying 1D XRD images

'''
import os
from os.path import expanduser

import numpy as np
import sys
import time
import re
import math

from threading import Thread
from functools import partial

import wx
import wx.lib.scrolledpanel as scrolled
from wxmplot import PlotPanel

import larch
from larch.larchlib import read_workdir, save_workdir
from larch.utils import nativepath, get_cwd
from larch.xray import XrayBackground
from larch.xrd import (cifDB, SearchCIFdb, QSTEP, QMIN, QMAX, CATEGORIES,
                       match_database, d_from_q,twth_from_q,q_from_twth,
                       d_from_twth,twth_from_d,q_from_d, lambda_from_E,
                       E_from_lambda,calc_broadening,
                       instrumental_fit_uvw,peaklocater,peakfitter,
                       xrd1d, peakfinder_methods,SPACEGROUPS, create_xrdcif,
                       save1D)


from larch.wxlib import (ReportFrame, BitmapButton, FloatCtrl, FloatSpin,
                         SetTip, GridPanel, get_icon, SimpleText, pack,
                         Button, HLine, Choice, Check, MenuItem, COLORS,
                         set_color, CEN, RIGHT, LEFT, FRAMESTYLE, Font,
                         FONTSIZE, FONTSIZE_FW, FileSave, FileOpen,
                         flatnotebook, Popup, FileCheckList,
                         EditableListBox, ExceptionPopup)

XYWcards = "XY Data File(*.xy)|*.xy|All files (*.*)|*.*"
PlotWindowChoices = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

X_SCALES = [u'q (\u212B\u207B\u00B9)', u'2\u03B8 (\u00B0)', u'd (\u212B)']
Y_SCALES = ['linear', 'log']

PLOT_CHOICES = ['Data', 'Data + Background',
                'Background-subtracted', 'Difference Pattern']

SCALE_METHODS = ['Max Intensity', 'Mean Intensity',
                 'Max Background Intensity',
                 'Mean Background Intensity']

def calc_bgr(data):
    bgr = data*1.00
    xb = XrayBackground(bgr, width=10, compress=5, exponent=2, slope=1.)
    bgr[:len(xb.bgr)] = xb.bgr
    print("CALC BGR !! ", type(bgr), bgr.mean())
    return bgr

class XRD1DBrowserFrame(wx.Frame):
    """browse 1D XRD patterns"""
    def __init__(self, parent=None, _larch=None, **kws):
        wx.Frame.__init__(self, None, -1, title='1D XRD Browser',
                          style=FRAMESTYLE, size=(600, 600), **kws)
        self.parent = parent
        self.larch = _larch
        self.current_label = None
        self.datasets = {}
        self.form = {}
        self.createMenus()
        self.build()

    def createMenus(self):
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "Read XY File",
                 "Read XRD 1D data from XY FIle",
                 self.onReadXY)

        MenuItem(self, fmenu, "Save XY File",
                 "Save XRD 1D data to XY FIle",
                 self.onSaveXY)

        menubar = wx.MenuBar()
        menubar.Append(fmenu, "&File")
        self.SetMenuBar(menubar)

    def onReadXY(self, event=None):
        print('read xy ')
        deffile = 'some.xy'
        sfile = FileOpen(self, 'Read XY Data',
                         default_file=deffile,
                         wildcard=XYWcards)
        if sfile is not None:
            print(' would read ', sfile)

    def onSaveXY(self, event=None):
        print('save xy ')
        deffile = 'some.xy'
        # self.datagroup.filename.replace('.', '_') + 'peak.modl'
        sfile = FileSave(self, 'Save XY Data',
                         default_file=deffile)
        if sfile is not None:
            print(' would save ', sfile)

    def build(self):
        sizer = wx.GridBagSizer(3, 3)
        sizer.SetVGap(3)
        sizer.SetHGap(3)

        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(220)

        # left side: list of XRD 1D patterns
        lpanel = wx.Panel(splitter)
        lpanel.SetMinSize((275, 350))

        rpanel = scrolled.ScrolledPanel(splitter)
        rpanel.SetSize((600, 650))
        rpanel.SetMinSize((350, 350))

        ltop = wx.Panel(lpanel)

        def Btn(msg, x, act):
            b = Button(ltop, msg, size=(x, 30),  action=act)
            b.SetFont(Font(FONTSIZE))
            return b

        sel_none = Btn('Select None', 130, self.onSelNone)
        sel_all  = Btn('Select All', 130, self.onSelAll)

        self.filelist = FileCheckList(lpanel, main=self,
                                      select_action=self.show_dataset,
                                      remove_action=self.remove_dataset)
        set_color(self.filelist, 'list_fg', bg='list_bg')

        tsizer = wx.BoxSizer(wx.HORIZONTAL)
        tsizer.Add(sel_all, 1, LEFT|wx.GROW, 1)
        tsizer.Add(sel_none, 1, LEFT|wx.GROW, 1)
        pack(ltop, tsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ltop, 0, LEFT|wx.GROW, 1)
        sizer.Add(self.filelist, 1, LEFT|wx.GROW|wx.ALL, 1)
        pack(lpanel, sizer)

        # right side: parameters controlling display
        panel = GridPanel(rpanel, ncols=6, nrows=10, pad=3, itemstyle=LEFT)
        panel.sizer.SetVGap(3)
        panel.sizer.SetHGap(3)

        self.font_fixedwidth = wx.Font(FONTSIZE_FW, wx.MODERN, wx.NORMAL, wx.BOLD)

        # title row
        self.wids = wids = {}
        title = SimpleText(panel, '1D XRD Data Display', font=Font(FONTSIZE+2),
                           colour=COLORS['title'], style=LEFT)

        self.last_plot_type = 'one'
        self.plotone = Button(panel, 'Plot Current ', size=(125, -1),
                              action=self.onPlotOne)
        self.plotsel = Button(panel, 'Plot Selected ', size=(125, -1),
                              action=self.onPlotSel)
        wids['plotone'] = Choice(panel, choices=PLOT_CHOICES, default=0,
                                 action=self.onPlotOne, size=(200, -1))
        wids['plotsel'] = Choice(panel, choices=PLOT_CHOICES, default=0,
                                 action=self.onPlotSel, size=(200, -1))
        wids['xscale'] = Choice(panel, choices=X_SCALES, default=0,
                                 action=self.onPlotEither, size=(100, -1))

        opts = dict(default=False, size=(200, -1), action=self.onPlotEither)
        wids['plot_win']  = Choice(panel, size=(100, -1), choices=PlotWindowChoices,
                                   action=self.onPlotEither)
        wids['plot_win'].SetStringSelection('1')

        wids['scale'] = FloatCtrl(panel, value=1.0, size=(150, -1), precision=2,
                                  action=self.set_scale)
        wids['auto_scale'] = Check(panel, default=True, label='auto?',
                                   action=self.auto_scale)
        wids['scale_method'] = Choice(panel, choices=SCALE_METHODS,
                                      size=(250, -1), action=self.auto_scale, default=0)


        pwin_lab = wx.StaticText(panel, label=' Plot Window: ')
        xscale_lab = wx.StaticText(panel, label=' X scale: ')

        panel.Add(title, style=LEFT, dcol=5)
        panel.Add(self.plotsel, newrow=True)
        panel.Add(wids['plotsel'])
        panel.Add(xscale_lab)
        panel.Add(wids['xscale'])

        panel.Add(self.plotone, newrow=True)
        panel.Add(wids['plotone'])
        panel.Add(pwin_lab)
        panel.Add(wids['plot_win'])

        panel.Add((5, 5))
        panel.Add(HLine(panel, size=(550, 3)), dcol=5, newrow=True)
        panel.Add((5, 5))

        panel.Add(wx.StaticText(panel, label=' Scaling Factor: '), style=LEFT, newrow=True)
        panel.Add(wids['scale'])
        panel.Add(wids['auto_scale'])
        panel.Add(wx.StaticText(panel, label=' Scaling Method: '), style=LEFT, newrow=True)
        panel.Add(wids['scale_method'], dcol=2)

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((5, 5), 0, LEFT, 3)
        sizer.Add(panel, 0, LEFT, 3)
        sizer.Add((5, 5), 0, LEFT, 3)
        pack(rpanel, sizer)

        rpanel.SetupScrolling()

        splitter.SplitVertically(lpanel, rpanel, 1)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)
        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def onSelNone(self, event=None):
        self.filelist.select_none()

    def onSelAll(self, event=None):
        self.filelist.select_all()

    def show_dataset(self, event=None, label=None):
        print('show xd1d ', event, label)
        if label is None and event is not None:
            label = str(event.GetString())
        if label not in self.datasets:
            print('dataset not found ', label)

        self.current_label = label
        dset = self.datasets[label]
        print("Show dataset ", label, dir(dset))
        if not hasattr(dset, 'scale'):
            dset.scale = dset.I.max()
            dset.auto_scale = True
            dset.scale_method = SCALE_METHODS[0]
            dset.bgkd = calc_bgr(dset.I)

        self.wids['scale'].SetValue(dset.scale)
        self.wids['auto_scale'].SetValue(dset.auto_scale)
        self.wids['scale_method'].SetStringSelection(dset.scale_method)
        self.onPlotOne(label=label)

    def set_scale(self, event=None, value=-1.0):
        label = self.current_label
        if label not in self.datasets:
            print('dataset not found ', label)
            return
        if value < 0:
            value = self.wids['scale'].GetValue()
        self.datasets[label].scale = value # self.wids['scale'].GetValue()

    def auto_scale(self, event=None):
        label = self.current_label
        if label not in self.datasets:
            print('dataset not found ', label)
            return
        dset = self.datasets[label]
        dset.auto_scale = self.wids['auto_scale'].IsChecked()
        self.wids['scale_method'].Enable(dset.auto_scale)

        if dset.auto_scale:
            meth = dset.scale_method = self.wids['scale_method'].GetStringSelection().lower()
            use_back = 'background' in meth
            if use_back:
                dset.bkgd = calc_bgr(dset.I)

            scale =  -1
            if meth.lower().startswith('mean'):
                if use_back:
                    scale = dset.bkgd.mean()
                else:
                    scale = dset.I.mean()
            elif meth.lower().startswith('max'):
                if use_back:
                    scale = dset.bkgd.max()
                else:
                    scale = dset.I.max()
            if scale > 0:
                self.wids['scale'].SetValue(scale)

    def remove_dataset(self, event=None):
        print('remove dataset ', event.GetString())

    def get_display(self, win=1, stacked=False):
        wintitle='XRD Plot Window %i' % win
        opts = dict(wintitle=wintitle, stacked=stacked, win=win, linewidth=3)
        return self.larch.symtable._plotter.get_display(**opts)

    def onPlotOne(self, event=None, label=None):
        print('plot one ', label)
        if label is None:
            label = self.current_label
        if label not in self.datasets:
            return
        dset = self.datasets[label]
        self.last_plot_type = 'one'
        win    = int(self.wids['plot_win'].GetStringSelection())
        xscale = self.wids['xscale'].GetSelection()
        xlabel = self.wids['xscale'].GetStringSelection()
        xdat = dset.q
        if xscale == 2:
           xdat = dset.D
        elif xscale == 1:
            xdat = dset.twth
        ytype = self.wids['plotone'].GetStringSelection().lower()
        print("PLOT ONE ", ytype)

        if ytype.startswith('data'):
            ydat = 1.0*dset.I/dset.scale
            ylabel = 'Scaled Intensity'
        elif ytype.startswith('background-sub'):
            ydat = 1.0*(dset.I-dset.bkgd)/dset.scale
            ylabel = 'Scaled (Intensity - Background)'

        pframe = self.get_display(win=win)
        pframe.plot(xdat, ydat, xlabel=xlabel, ylabel=ylabel,
                    label=dset.label, show_legend=True)
        if ytype.startswith('data') and 'background' in ytype:
            y2dat = 1.0*dset.bkgd/dset.scale
            ylabel = 'Scaled Intensity with Background'
            pframe.oplot(xdat, y2dat, xlabel=xlabel, ylabel=ylabel,
                         label='background', show_legend=True)

        wx.CallAfter(self.SetFocus)

    def onPlotSel(self, event=None):
        labels = self.filelist.GetCheckedStrings()
        if len(labels) < 1:
            return
        self.last_plot_type = 'multi'
        last_id = group_ids[-1]

    def onPlotEither(self, evt=None):
        if self.last_plot_type == 'multi':
            self.onPlotSel(event=event)
        else:
            self.onPlotOne(event=event)


    def add_data(self, dataset, label=None,  **kws):
        print("add dataset ", dataset, label)
        if label is None:
            label = 'XRD pattern'
        self.filelist.Append(label)
        self.datasets[label] = dataset
        self.show_dataset(label=label)
