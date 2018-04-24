import time
import os
import numpy as np
np.seterr(all='ignore')

from functools import partial
from collections import OrderedDict

import wx
import wx.lib.agw.flatnotebook as flat_nb

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check,
                     MenuItem, GUIColors, GridPanel, CEN, RCEN, LCEN,
                     FRAMESTYLE, Font, FileSave, FileOpen)

from larch import Group
from larch.wxlib import (BitmapButton, FloatCtrl, SetTip)
from larch_plugins.std import group2dict


LCEN = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
CEN |=  wx.ALL

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_NO_NAV_BUTTONS

FONTSIZE = 10

class TaskPanel(wx.Panel):
    """generic panel for main tasks.
    meant to be subclassed
    """
    def __init__(self, parent, controller, configname='task_config',
                 title='Generic Panel', **kws):
        wx.Panel.__init__(self, parent, -1, size=(550, 625), **kws)
        self.parent = parent
        self.controller = controller
        self.larch = controller.larch
        self.title = title
        self.configname = configname

        self.wids = {}
        self.SetFont(Font(FONTSIZE))

        self.panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LCEN)
        self.skip_process = True
        self.build_display()
        self.skip_process = False


    def onPanelExposed(self, **kws):
        # called when notebook is selected
        fname = self.controller.filelist.GetStringSelection()
        if fname in self.controller.file_groups:
            gname = self.controller.file_groups[fname]
            dgroup = self.controller.get_group(gname)
            self.fill_form(dgroup=dgroup)
            self.process(dgroup=dgroup)

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

    def set_defaultconfig(self, config):
        """set the default configuration for this session"""
        conf = self.controller.larch.symtable._sys.xas_viewer
        setattr(conf, self.configname, {key:val for key, val in config.items()})

    def get_defaultconfig(self):
        """get the default configuration for this session"""
        conf = self.controller.larch.symtable._sys.xas_viewer
        getattr(conf, self.configname, {})

    def get_config(self, dgroup=None):
        """get processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()

        conf = getattr(dgroup, self.configname, self.get_defaultconfig())

        return self.customize_config(conf, dgroup=dgroup)

    def customize_config(self, config, dgroup=None):
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

    def process(self, dgroup=None, **kws):
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

    def onSelPoint(self, evt=None, opt='__'):
        xval = None
        try:
            xval = self.larch.symtable._plotter.plot1_x
        except:
            return

        if opt in self.wids:
            self.wids[opt].SetValue(xval)
