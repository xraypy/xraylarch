#!/usr/bin/env python
"""
Athena Project Importer
"""
import os
import numpy as np
np.seterr(all='ignore')

import wx
from wxmplot import PlotPanel

from wxutils import (SimpleText, pack, Button, Choice, Check, MenuItem,
                     GUIColors, CEN, RCEN, LCEN, FRAMESTYLE, Font)

import larch
from larch import Group
from larch_plugins.io import fix_varname, read_athena
from larch.wxlib import (FileCheckList, SetTip)

CEN |=  wx.ALL

class AthenaImporter(wx.Frame) :
    """Import Athena File"""
    def __init__(self, parent, filename=None, read_ok_cb=None,
                 size=(725, 450), _larch=None):
        self.parent = parent
        self.filename = filename
        self.larch = _larch
        self.read_ok_cb = read_ok_cb

        self.colors = GUIColors()

        wx.Frame.__init__(self, parent, -1,   size=size, style=FRAMESTYLE)
        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(200)

        leftpanel = wx.Panel(splitter)
        ltop = wx.Panel(leftpanel)

        sel_none = Button(ltop, 'Select None', size=(100, 30), action=self.onSelNone)
        sel_all  = Button(ltop, 'Select All', size=(100, 30), action=self.onSelAll)
        sel_imp  = Button(ltop, 'Import Selected Groups', size=(200, 30), action=self.onOK)

        self.grouplist = FileCheckList(leftpanel, select_action=self.onShowGroup)
        self.grouplist.SetBackgroundColour(wx.Colour(255, 255, 255))

        tsizer = wx.GridBagSizer(2, 2)
        tsizer.Add(sel_all, (0, 0), (1, 1), LCEN, 0)
        tsizer.Add(sel_none,  (0, 1), (1, 1), LCEN, 0)
        tsizer.Add(sel_imp,  (1, 0), (1, 2), LCEN, 0)

        pack(ltop, tsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ltop, 0, LCEN|wx.GROW, 1)
        sizer.Add(self.grouplist, 1, LCEN|wx.GROW|wx.ALL, 1)
        pack(leftpanel, sizer)

        # right hand side
        rightpanel = wx.Panel(splitter)

        self.SetTitle("Reading Athena Project '%s'" % self.filename)
        self.title = SimpleText(rightpanel, self.filename, font=Font(13),
                                colour=self.colors.title, style=LCEN)

        self.plotpanel = PlotPanel(rightpanel, messenger=self.plot_messages)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.title, 0, LCEN, 2)
        sizer.Add(self.plotpanel, 0, LCEN, 2)
        pack(rightpanel, sizer)

        splitter.SplitVertically(leftpanel, rightpanel, 1)

        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = [self.filename, ""]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        self.all = read_athena(filename, do_bkg=False, do_fft=False, _larch=_larch)
        for item in dir(self.all):
            self.grouplist.Append(item)

        self.Show()
        self.Raise()

    def plot_messages(self, msg, panel=1):
        self.SetStatusText(msg, panel)

    def onOK(self, event=None):
        """ import groups """
        for name in self.grouplist.GetCheckedStrings():
            rawgroup = getattr(self.all, name)
            npts = len(rawgroup.energy)
            outgroup = Group(datatype='xas',
                            path="%s::%s" %(self.filename, name),
                            filename=name,
                            groupname = fix_varname(name),
                            raw=rawgroup,
                            xdat=rawgroup.energy,
                            ydat=rawgroup.mu,
                            y=rawgroup.mu,
                            yerr=1.0,
                            npts=npts, _index=1.0*np.arange(npts),
                            plot_xlabel='Energy (eV)',
                            plot_ylabel='mu')

            self.read_ok_cb(outgroup, array_sel=None, overwrite=True)

        self.Destroy()

    def onCancel(self, event=None):
        self.Destroy()

    def onSelAll(self, event=None):
        self.grouplist.SetCheckedStrings(dir(self.all))

    def onSelNone(self, event=None):
        self.grouplist.SetCheckedStrings([])

    def onShowGroup(self, event=None):
        """column selections changed calc xdat and ydat"""
        gname = event.GetString()
        grp = getattr(self.all, gname)
        if hasattr(grp, 'energy') and hasattr(grp, 'mu'):
            self.plotpanel.plot(grp.energy, grp.mu,
                                xlabel='Energy', ylabel='mu',title=gname)
