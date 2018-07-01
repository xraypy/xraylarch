#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import six

import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv

import numpy as np

from functools import partial
from collections import OrderedDict


from larch.utils import index_of
from larch.wxlib import (BitmapButton, FloatCtrl, get_icon, SimpleText,
                         pack, Button, HLine, Choice, Check, CEN, RCEN,
                         LCEN, Font)

from larch_plugins.xasgui.taskpanel import TaskPanel


np.seterr(all='ignore')

# plot options:
norm   = six.u('Normalized \u03bC(E)')
dmude  = six.u('d\u03bC(E)/dE')
chik   = six.u('\u03c7(k)')
noplot = '<no plot>'
noname = '<none>'


FitSpace_Choices = [norm, dmude, chik]
Plot_Choices = ['PCA Components', 'Component Weights',
              'Data + Fit + Compononents']

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

defaults = dict(e0=0, elo=-25, ehi=75, fitspace=norm, threshold=1.e-5,
                show_e0=True, show_fitrange=True)

MAX_COMPONENTS = 40

class PCAPanel(TaskPanel):
    """PCA Panel"""

    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='pca_config',
                           title='Principal Component Analysis',
                           **kws)

    def process(self, dgroup, **kws):
        """ handle PCA processing"""
        if self.skip_process:
            return
        form = self.read_form()


    def build_display(self):
        titleopts = dict(font=Font(12), colour='#AA0000')
        panel = self.panel
        wids = self.wids
        self.skip_process = True

        wids['fitspace'] = Choice(panel, choices=FitSpace_Choices, size=(175, -1))
        wids['fitspace'].SetStringSelection(norm)
        wids['plotchoice'] = Choice(panel, choices=Plot_Choices,
                                  size=(175, -1), action=self.onPlot)
        wids['plotchoice'].SetSelection(0)

        add_text = self.add_text

        opts = dict(digits=2, increment=1.0)

        wids['xmin'] = self.add_floatspin('xmin', value=-30, **opts)
        wids['xmax'] = self.add_floatspin('xmax', value=75, **opts)

        wids['weight_min'] = self.add_floatspin('weight_min', value=0.010, digits=3,
                                                increment=0.001, with_pin=False)

        wids['build_model'] = Button(panel, 'Use Selected Groups to Build PCA Model',
                                     size=(250, -1),  action=self.onBuildPCAModel)

        wids['fit_group'] = Button(panel, 'Test Current Group with PCA Model', size=(250, -1),
                                   action=self.onFitGroup)

        wids['save_model'] = Button(panel, 'Save PCA Model', size=(250, -1),
                                    action=self.onSavePCAModel)

        wids['fit_group'].Disable()
        wids['save_model'].Disable()

        opts = dict(default=True, size=(75, -1), action=self.onPlot)

        wids['show_fitrange'] = Check(panel, label='show?', **opts)

        wids['status'] = SimpleText(panel, ' ')

        panel.Add(SimpleText(panel, ' Principal Component Analysis', **titleopts), dcol=4)

        add_text('Array to Use: ', newrow=True)
        panel.Add(wids['fitspace'], dcol=3)

        add_text('Plot : ', newrow=True)
        panel.Add(wids['plotchoice'], dcol=3)

        add_text('Fit Range: ')
        panel.Add(wids['xmin'])
        add_text(' : ', newrow=False)
        panel.Add(wids['xmax'])
        panel.Add(wids['show_fitrange'])

        add_text('Min Weight: ')
        panel.Add(wids['weight_min'])

        add_text('Status: ')
        panel.Add(wids['status'], dcol=4)

        panel.Add(HLine(panel, size=(500, 2)), dcol=5, newrow=True)

        panel.Add(wids['build_model'], dcol=4, newrow=True)
        panel.Add(wids['fit_group'], dcol=4, newrow=True)

        panel.Add(HLine(panel, size=(400, 2)), dcol=5, newrow=True)
        panel.Add(wids['save_model'], dcol=4, newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LCEN, 3)
        pack(self, sizer)
        self.skip_process = False

    def onPlot(self, event=None):
        print("on Plot!")

    def onFitGroup(self, event=None):
        print("on fit group!")

    def onBuildPCAModel(self, event=None):
        print("on build!")
        self.wids['status'].SetLabel(" training model...")

    def onSavePCAModel(self, event=None):
        print("on save model!")
