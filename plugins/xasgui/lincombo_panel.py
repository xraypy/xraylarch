#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import wx
import numpy as np

from functools import partial
from collections import OrderedDict

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check,
                     GridPanel, CEN, RCEN, LCEN, Font)

from larch.utils import index_of
from larch.wxlib import BitmapButton, FloatCtrl, FloatSpin, ToggleButton
from larch_plugins.wx.icons import get_icon
from larch_plugins.xasgui.taskpanel import TaskPanel

np.seterr(all='ignore')


# plot options:
norm    = u'Normalized \u03bC(E)'
dmude   = u'd\u03bC(E)/dE'
chik    = u'\u03c7(k)'
noplot  = '<no plot>'

FitSpace_Choices = [norm, dmude, chik]

PlotCmds = {norm:   "plot_mu({group:, norm=True}",
            chik:    "plot_chik({group:s}, show_window=False, kweight={plot_kweight:.0f}",
            noplot: None}


defaults = dict(e0=0, elow=-20, ehi=30, fitspace=norm, sum_to_one=True)

class LinearComboPanel(TaskPanel):
    """Liear Combination Panel"""
    def __init__(self, parent, controller, **kws):

        TaskPanel.__init__(self, parent, controller,
                           configname='lincombo_config',
                           config=defaults, **kws)

    def process(self, dgroup, **kws):
        """ handle linear combo processing"""
        if self.skip_process:
            return
        self.skip_process = True
        form = self.read_form()

    def larch_eval(self, cmd):
        """eval"""
        self.controller.larch.eval(cmd)

    def build_display(self):

        titleopts = dict(font=Font(12), colour='#AA0000')
        panel = self.panel
        wids = self.wids
        self.skip_process = True

        wids['fitspace'] = Choice(panel, choices=FitSpace_Choices,
                                   size=(175, -1))

        wids['fitspace'].SetStringSelection(norm)

        def FloatSpinWithPin(name, value, **kws):
            s = wx.BoxSizer(wx.HORIZONTAL)
            self.wids[name] = FloatSpin(panel, value=value, **kws)
            bb = BitmapButton(panel, get_icon('pin'), size=(25, 25),
                              action=partial(self.onSelPoint, opt=name),
                              tooltip='use last point selected from plot')
            s.Add(wids[name])
            s.Add(bb)
            return s


        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        opts = dict(digits=2, increment=0.1, min_val=0, action=self.onProcess)

        wids['e0']  = FloatSpin(panel, **opts)
        wids['elo'] = FloatSpin(panel, **opts)
        wids['ehi'] = FloatSpin(panel, **opts)


        wids['dofit'] = Button(panel, 'Do Fit', size=(200, -1),
                               action=self.onProcess)
        wids['saveconf'] = Button(panel, 'Save as Default Settings', size=(200, -1),
                                  action=self.onSaveConfigBtn)


        panel.Add(SimpleText(panel, ' Linear Combination Analysis', **titleopts), dcol=5)

        panel.Add(wids['dofit'], newrow=True)
        panel.Add(wids['fitspace'], dcol=2)

        add_text('E0: ')
        panel.Add(wids['e0'])

        add_text('Fit Energy Range: ')
        panel.Add(wids['elo'])
        add_text(' : ', newrow=False)
        panel.Add(wids['ehi'])

        panel.Add(wids['saveconf'], dcol=4, newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LCEN, 3)
        pack(self, sizer)
        self.skip_process = False

    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)

        self.dgroup = dgroup
        self.skip_process = True
        wids = self.wids
        for attr in ('e0', 'elo', 'ehi'):
            val = getattr(dgroup, attr, None)
            if val is None:
                val = opts.get(attr, -1)
            wids[attr].SetValue(val)

        for attr in ('fitspace',):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])

        self.skip_process = False
        self.process(dgroup=dgroup)

    def read_form(self, dgroup=None):
        "read form, return dict of values"
        self.skip_process = True
        if dgroup is None:
            dgroup = self.controller.get_group()
        self.dgroup = dgroup
        form_opts = {'group': dgroup.groupname}

        wids = self.wids
        for attr in ('e0', 'elo', 'ehi'):
            form_opts[attr] = wids[attr].GetValue()

        for attr in ('fitspace',):
            form_opts[attr] = wids[attr].GetStringSelection()

        self.skip_process = False
        return form_opts

    def onSaveConfigBtn(self, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())
        self.set_defaultconfig(conf)

    def onProcess(self, event=None):
        """ handle process events"""
        if self.skip_process:
            return

        self.skip_process = True
        form = self.read_form()
        self.process(dgroup=self.dgroup, opts=form)
        self.plot()

        self.skip_process = False

    def plot(self, dgroup=None):
        self.onPlotOne(dgroup=dgroup)
