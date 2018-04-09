import time
import os
import numpy as np
np.seterr(all='ignore')

from functools import partial
from collections import OrderedDict
import json

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as flat_nb

import wx.dataview as dv

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check,
                     MenuItem, GUIColors, GridPanel, CEN, RCEN, LCEN,
                     FRAMESTYLE, Font, FileSave, FileOpen)

from larch import Group, site_config
from larch.utils import index_of

from larch.wxlib import (BitmapButton, FloatCtrl, SetTip)

from larch_plugins.std import group2dict
from larch_plugins.wx.icons import get_icon


LCEN = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
CEN |=  wx.ALL

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_NO_NAV_BUTTONS

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, marker='None', markersize=4)

PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)

class TaskPanel(wx.Panel):
    """generic panel for main tasks.
    meant to be subclassed

    """
    title = 'generic panel'
    configname = 'generic_config'

    def __init__(self, parent, controller, **kws):

        wx.Panel.__init__(self, parent, -1, size=(550, 625), **kws)
        self.parent = parent
        self.controller = controller
        self.larch = controller.larch
        self.wids = {}
        self.panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LCEN)


    def onPanelExposed(self, **kws):
        # called when notebook is selected
        fname = self.controller.filelist.GetStringSelection()
        if fname in self.controller.file_groups:
            gname = self.controller.file_groups[fname]
            dgroup = self.controller.get_group(gname)
            self.fill_form(dgroup)


    def larch_eval(self, cmd):
        """eval"""
        self.controller.larch.eval(cmd)

    def build_display(self):
        """build display"""

        titleopts = dict(font=Font(11), colour='#AA0000')
        self.panel.Add(SimpleText(self.panel, self.title, **titleopts),
                       dcol=7)
        self.panel.Add(SimpleText(self.panel, ' coming soon....'),
                       dcol=7, newrow=True)
        self.panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.panel, 1, wx.LEFT|wx.CENTER, 3)
        pack(self, sizer)


    def get_config(self, dgroup=None):
        """get processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()

        conf = getattr(dgroup, self.configname, {})

        return self.customize_config(conf)

    def customize_config(self, config):
        """override to customize getting the panels config"""
        return config

    def fill_form(self, dat):
        if isinstance(dat, Group):
            dat = group2dict(dat)

        for name, wid in self.wids.items():
            if isinstance(wid, FloatCtrl) and name in dat:
                wid.SetValue(dat[name])

    def read_form(self):
        "read for, returning dict of values"
        dgroup = self.controller.get_group()
        form_opts = {'groupname': dgroup.groupname}
        for name, wid in self.wids.items():
            if isinstance(wid, FloatCtrl):
                form_opts[name] = wid.GetValue()
        return form_opts

    def process(self, dgroup, **kws):
        """override to handle data process step"""
        if self.skip_process:
            return
        self.skip_process = True
        form = self.read_form()

    def onPlot(self, evt=None):
        pass

    def onPlotOne(self, evt=None):
        pass

    def onPlotSel(self, evt=None):
        pass

    def onSelPoint(self, evt=None, opt='xmin'):
        xval = None
        try:
            xval = self.larch.symtable._plotter.plot1_x
        except:
            return

        if opt in self.wids:
            self.wids[opts].SetValue(xval)
