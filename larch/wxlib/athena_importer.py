#!/usr/bin/env python
"""
Athena Project Importer
"""
import os
import numpy as np
np.seterr(all='ignore')

import wx

import larch
from larch import Group
from larch.io import fix_varname, read_athena

from wxutils import (SimpleText, Button, Choice, GUIColors,
                     FileCheckList, FileDropTarget, pack,
                     Check, MenuItem, SetTip, Popup, CEN,
                     LEFT, FRAMESTYLE, Font)

from wxmplot import PlotPanel

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

        self.select_imported = sel_imp
        self.grouplist = FileCheckList(leftpanel, select_action=self.onShowGroup)

        tsizer = wx.GridBagSizer(2, 2)
        tsizer.Add(sel_all, (0, 0), (1, 1), LEFT, 0)
        tsizer.Add(sel_none,  (0, 1), (1, 1), LEFT, 0)
        tsizer.Add(sel_imp,  (1, 0), (1, 2), LEFT, 0)

        pack(ltop, tsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ltop, 0, LEFT|wx.GROW, 1)
        sizer.Add(self.grouplist, 1, LEFT|wx.GROW|wx.ALL, 1)
        pack(leftpanel, sizer)

        # right hand side
        rightpanel = wx.Panel(splitter)

        self.SetTitle("Reading Athena Project '%s'" % self.filename)
        self.title = SimpleText(rightpanel, self.filename, font=Font(13),
                                colour=self.colors.title, style=LEFT)

        self.plotpanel = PlotPanel(rightpanel, messenger=self.plot_messages)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.title, 0, LEFT, 2)
        sizer.Add(self.plotpanel, 0, LEFT, 2)
        pack(rightpanel, sizer)

        splitter.SplitVertically(leftpanel, rightpanel, 1)

        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = [self.filename, ""]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        self.a_project = read_athena(self.filename, do_bkg=False, do_fft=False,
                                     _larch=_larch)
        self.allgroups = {}
        for sname, item in self.a_project._athena_groups.items():
            try:
                self.allgroups[item.label] = sname
                self.grouplist.Append(item.label)
            except:
                print(' ? ', sname, item.label, item)
        self.Show()
        self.Raise()

    def plot_messages(self, msg, panel=1):
        self.SetStatusText(msg, panel)

    def onOK(self, event=None):
        """generate script to import groups"""
        namelist = [self.allgroups[n] for n in self.grouplist.GetCheckedStrings()]
        if len(namelist) == 0:

            cancel = Popup(self, """No data groups selected.
        Cancel import from this project?""", 'Cancel Import?',
                           style=wx.YES_NO)
            if wx.ID_YES == cancel:
                self.Destroy()
            else:
                return

        if self.read_ok_cb is not None:
            self.read_ok_cb(self.filename, namelist)
        self.Destroy()

    def onCancel(self, event=None):
        self.Destroy()

    def onSelAll(self, event=None):
        self.grouplist.SetCheckedStrings(list(self.allgroups.keys()))

    def onSelNone(self, event=None):
        self.grouplist.SetCheckedStrings([])

    def onShowGroup(self, event=None):
        """column selections changed calc xdat and ydat"""
        label = event.GetString()
        gname = self.allgroups[label]
        grp = getattr(self.a_project, gname)
        if hasattr(grp, 'energy') and hasattr(grp, 'mu'):
            self.plotpanel.plot(grp.energy, grp.mu,
                                xlabel='Energy', ylabel='mu',title=label)

        glist = list(self.grouplist.GetCheckedStrings())
        if label not in glist:
            glist.append(label)
        self.grouplist.SetCheckedStrings(glist)
