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

from wx.lib.agw.floatspin import FloatSpin, EVT_FLOATSPIN

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check,
                     GridPanel, CEN, RCEN, LCEN, Font)

from larch.utils import index_of
from larch.wxlib import BitmapButton, FloatCtrl
from larch_plugins.wx.icons import get_icon
from larch_plugins.xasgui.xas_dialogs import EnergyUnitsDialog
from larch_plugins.xasgui.taskpanel import TaskPanel

from larch_plugins.xafs.xafsutils import guess_energy_units
from larch_plugins.xafs.xafsplots import plotlabels

np.seterr(all='ignore')

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, zorder=3,
                  marker='None', markersize=4)
PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)


PlotOne_Choices = OrderedDict((('chi(k)', 'k'),
                               ('chi(k) + Window', 'k+win'),
                               ('|chi(R)|', 'rmag'),
                               ('Re[chi(R)]', 'rreal'),
                               ('|chi(R)| + Re[chi(R)]', 'rmagreal')))

PlotSel_Choices = OrderedDict((('chi(k)', 'k'),
                               ('|chi(R)|', 'rmag'),
                               ('Re[chi(R)]', 'rreal')))

FTWINDOWS = ('Kaiser-Bessel', 'Hanning', 'Gaussian', 'Sine', 'Parzen', 'Welch')

KWLIST = ('0', '1', '2', '3', '4', '5')
CLAMPLIST = ('0', '1', '2', '5', '10', '20', '50', '100')

class EXAFSPanel(TaskPanel):
    """EXAFS Panel"""
    title = 'EXAFS panel'
    configname = 'exafs_config'

    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller, **kws)
        self.skip_process = False

    def build_display(self):
        self.SetFont(Font(10))
        titleopts = dict(font=Font(11), colour='#AA0000')

        panel = self.panel

        self.plotone_op = Choice(panel, choices=list(PlotOne_Choices.keys()),
                                 action=self.onPlotOne, size=(200, -1))
        self.plotsel_op = Choice(panel, choices=list(PlotSel_Choices.keys()),
                                 action=self.onPlotSel, size=(200, -1))

        self.plot_kweight = Choice(panel, choices=KWLIST,
                                   action=self.onPlotOne, size=(100, -1))

        self.kwindow = Choice(panel, choices=list(FTWINDOWS),
                               action=self.on_fft, size=(100, -1))

        self.plotone_op.SetSelection(0)
        self.plotsel_op.SetSelection(0)

        plot_one = Button(panel, 'Plot This Group', size=(150, -1),
                          action=self.onPlotOne)

        plot_sel = Button(panel, 'Plot Selected Groups', size=(150, -1),
                          action=self.onPlotSel)

        saveconf = Button(panel, 'Save as Default Settings', size=(200, -1),
                          action=self.onSaveConfigBtn)

        def CopyBtn(name):
            return Button(panel, 'Copy', size=(50, -1),
                          action=partial(self.onCopyParam, name))

        wids = self.wids
        btns = self.btns

        opts = dict(size=(90, -1), digits=2, increment=0.1)
        wids['e0'] = FloatSpin(panel, -1, **opts)

        opts['size'] = (90, -1)
        wids['rbkg'] = FloatSpin(panel, -1, value=1.0,
                                 min_val=0, max_val=25, **opts)
        wids['bkg_kmin'] = FloatSpin(panel, -1, value=0,
                                 min_val=0, max_val=125, **opts)

        wids['bkg_kmax'] = FloatSpin(panel, -1, min_val=0, max_val=125, **opts)

        wids['fft_kmin'] = FloatSpin(panel, -1, value=0,
                                 min_val=0, max_val=125, **opts)

        wids['fft_kmax'] = FloatSpin(panel, -1, min_val=0, max_val=125, **opts)

        wids['fft_dk'] = FloatSpin(panel, -1, value=3,
                                 min_val=0, max_val=125, **opts)

        opts['increment'] = opts['digits'] = 1
        wids['bkg_kweight'] = FloatSpin(panel, -1, value=1,
                                 min_val=0, max_val=8, **opts)

        wids['fft_kweight'] = FloatSpin(panel, -1, value=1,
                                 min_val=0, max_val=8, **opts)

        for name in ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax', 'bkg_kweight'):
            wids[name].Bind(EVT_FLOATSPIN, self.on_autobk)

        for name in ('fft_kmin', 'fft_kmax', 'fft_dk', 'fft_kweight'):
            wids[name].Bind(EVT_FLOATSPIN, self.on_fft)

        for name in ('bkg_kmin', 'bkg_kmax', 'fft_kmin', 'fft_kmax'):
            bb = BitmapButton(panel, get_icon('plus'),
                              action=partial(self.onSelPoint, opt=name),
                              tooltip='use last point selected from plot')
            btns[name] = bb
        opts = dict(choices=CLAMPLIST, size=(70, -1), action=self.on_autobk)
        wids['bkg_clamplo'] = Choice(panel, **opts)
        wids['bkg_clamphi'] = Choice(panel, **opts)


        panel.Add(SimpleText(panel, ' EXAFS Processing', **titleopts), dcol=5)

        panel.Add(SimpleText(panel, ' Copy to Selected Groups?'), style=RCEN, dcol=3)


        panel.Add(plot_sel, newrow=True)
        panel.Add(self.plotsel_op, dcol=6)

        panel.Add(plot_one, newrow=True)
        panel.Add(self.plotone_op, dcol=5)
        panel.Add(CopyBtn('plotone_op'), style=RCEN)

        panel.Add(SimpleText(panel, 'K weight for plot: '), newrow=True)
        panel.Add(self.plot_kweight, dcol=4)

        panel.Add(HLine(panel, size=(250, 2)), dcol=7, newrow=True)

        panel.Add(SimpleText(panel, ' Background subtraction',
                             **titleopts), dcol=6, newrow=True)

        panel.Add(SimpleText(panel, 'E0: '), dcol=2, newrow=True)
        panel.Add(wids['e0'], dcol=4)
        panel.Add(CopyBtn('e0'), style=RCEN)


        panel.Add(SimpleText(panel, 'R_bkg: '), dcol=2, newrow=True)
        panel.Add(wids['rbkg'], dcol=4)
        panel.Add(CopyBtn('rbkg'), style=RCEN)

        panel.Add(SimpleText(panel, 'K weight (for background): '), dcol=2, newrow=True)
        panel.Add(wids['bkg_kweight'], dcol=4)
        panel.Add(CopyBtn('bkg_kweight'), style=RCEN)


        panel.Add(SimpleText(panel, 'K range: '), newrow=True)
        panel.Add(btns['bkg_kmin'])
        panel.Add(wids['bkg_kmin'])

        panel.Add(SimpleText(panel, ' : '))
        panel.Add(btns['bkg_kmax'])
        panel.Add(wids['bkg_kmax'])
        panel.Add(CopyBtn('bkg_krange'), style=RCEN)


        panel.Add(SimpleText(panel, 'Clamps Low k: '), dcol=2, newrow=True)
        panel.Add( wids['bkg_clamplo'])
        panel.Add(SimpleText(panel, 'high k: '), dcol=2)
        panel.Add( wids['bkg_clamphi'])
        panel.Add(CopyBtn('bkg_clamps'), style=RCEN)

        panel.Add(HLine(panel, size=(250, 2)), dcol=7, newrow=True)

        panel.Add(SimpleText(panel, ' Fourier transform',
                             **titleopts), dcol=6, newrow=True)


        panel.Add(SimpleText(panel, 'K range: '), newrow=True)
        panel.Add(btns['fft_kmin'])
        panel.Add(wids['fft_kmin'])

        panel.Add(SimpleText(panel, ' : '))
        panel.Add(btns['fft_kmax'])
        panel.Add(wids['fft_kmax'])
        panel.Add(CopyBtn('fft_krange'), style=RCEN)

        panel.Add(SimpleText(panel, 'K weight : '), dcol=2, newrow=True)
        panel.Add(wids['fft_kweight'], dcol=4)
        panel.Add(CopyBtn('fft_kweight'), style=RCEN)

        panel.Add(SimpleText(panel, 'K window : '), dcol=2, newrow=True)
        panel.Add(self.kwindow)
        panel.Add(SimpleText(panel, ' dk : '), dcol=2)
        panel.Add(wids['fft_dk'])
        panel.Add(CopyBtn('fft_kwin'), style=RCEN)

        panel.Add(HLine(panel, size=(250, 2)), dcol=7, newrow=True)

        panel.Add(saveconf, dcol=4, newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(panel, 1, LCEN, 3)
        pack(self, sizer)

    def on_autobk(self, event=None):
        print("do autobk")

    def on_fft(self, event=None):
        print("do fft")

    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)
        self.skip_process = True
        print("EXAFS Panel Fill Form")



#         widlist = (self.xas_e0, self.xas_step, self.xas_pre1,
#                    self.xas_pre2, self.xas_nor1, self.xas_nor2,
#                    self.xas_vict, self.xas_nnor, self.xas_showe0,
#                    self.xas_autoe0, self.xas_autostep,
#                    self.deconv_form, self.deconv_ewid)
#
#         if dgroup.datatype == 'xas':
#             for k in widlist:
#                 k.Enable()
#
#             self.plotone_op.SetChoices(list(PlotOne_Choices.keys()))
#             self.plotsel_op.SetChoices(list(PlotSel_Choices.keys()))
#
#             self.plotone_op.SetStringSelection(opts['plotone_op'])
#             self.plotsel_op.SetStringSelection(opts['plotsel_op'])
#             self.xas_e0.SetValue(opts['e0'])
#             self.xas_step.SetValue(opts['edge_step'])
#             self.xas_pre1.SetValue(opts['pre1'])
#             self.xas_pre2.SetValue(opts['pre2'])
#             self.xas_nor1.SetValue(opts['norm1'])
#             self.xas_nor2.SetValue(opts['norm2'])
#             self.xas_vict.SetSelection(opts['nvict'])
#             self.xas_nnor.SetSelection(opts['nnorm'])
#             self.xas_showe0.SetValue(opts['show_e0'])
#             self.xas_autoe0.SetValue(opts['auto_e0'])
#             self.xas_autostep.SetValue(opts['auto_step'])
#             self.deconv_form.SetStringSelection(opts['deconv_form'])
#             self.deconv_ewid.SetValue(opts['deconv_ewid'])
#         else:
#             self.plotone_op.SetChoices(list(PlotOne_Choices_nonxas.keys()))
#             self.plotsel_op.SetChoices(list(PlotSel_Choices_nonxas.keys()))
#             self.plotone_op.SetStringSelection('Raw Data')
#             self.plotsel_op.SetStringSelection('Raw Data')
#             for k in widlist:
#                 k.Disable()
#
#         self.skip_process = False
#         self.process(dgroup)

    def read_form(self):
        "read for, returning dict of values"
        form_opts = {}
        return form_opts

    def onPlotOne(self, evt=None):
        self.plot(self.controller.get_group())

    def onPlotSel(self, evt=None):
        newplot = True
        pass

    def onSaveConfigBtn(self, evt=None):
        conf = self.controller.larch.symtable._sys.xas_viewer
        opts = {}
        opts.update(getattr(conf, 'exafs', {}))
        opts.update(self.read_form())
        conf.xas_norm = opts

    def onCopyParam(self, name=None, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())
        opts = {}


    def process(self, dgroup, **kws):
        """ handle process of XAS data
        """
        if self.skip_process:
            return
        self.skip_process = True
        form = self.read_form()

    def get_plot_arrays(self, dgroup):
        form = self.read_form()


    def plot(self, dgroup, title=None, plot_yarrays=None, delay_draw=False,
             new=True, zoom_out=True, with_extras=True, **kws):

        print("plot")
