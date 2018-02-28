#!/usr/bin/env python
"""
XANES Data Viewer and Analysis Tool
"""

from functools import partial
from collections import OrderedDict

import numpy as np
import time
import wx

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check,
                     GridPanel, CEN, RCEN, LCEN, Font)

from larch.utils import index_of
from larch.wxlib import BitmapButton, FloatCtrl
from larch_plugins.wx.icons import get_icon

is_wxPhoenix = 'phoenix' in wx.PlatformInfo
np.seterr(all='ignore')

FILE_WILDCARDS = "Data Files(*.0*,*.dat,*.xdi,*.prj)|*.0*;*.dat;*.xdi;*.prj|All files (*.*)|*.*"

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, zorder=3,
                  marker='None', markersize=4)
PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)

SMOOTH_OPS = ('None', 'Boxcar', 'Savitzky-Golay', 'Convolution')
CONV_OPS = ('Lorenztian', 'Gaussian')
DECONV_OPS = ('None', 'Lorenztian', 'Gaussian')

XASOPChoices = OrderedDict((('Raw Data', 'raw'),
                            ('Normalized', 'norm'),
                            ('Derivative', 'deriv'),
                            ('Normalized + Derivative', 'norm+deriv'),
                            ('Pre-edge subtracted', 'preedge'),
                            ('Raw Data + Pre-edge/Post-edge', 'prelines'),
                            ('Deconvolved + Normalized',   'deconv')))

                            # ('Pre-edge Peaks + Baseline', 'prepeaks+base'),
                            # ('Pre-edge Peaks, isolated', 'prepeaks'))

class XASNormPanel(wx.Panel):
    """XAS normalization Panel"""
    def __init__(self, parent, controller=None, reporter=None, **kws):
        wx.Panel.__init__(self, parent, -1, **kws)

        self.controller = controller
        self.reporter = reporter
        self.needs_update = False
        self.unzoom_on_update = True
        self.proc_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onProcessTimer, self.proc_timer)
        self.proc_timer.Start(100)
        self.build_display()

    def edit_config(self, event=None):
        """edit config"""
        pass

    def fill(self, dgroup):
        opts = self.controller.get_proc_opts(dgroup)
        self.eshift.SetValue(opts['eshift'])

        self.smooth_op.SetStringSelection(opts['smooth_op'])
        self.smooth_conv.SetStringSelection(opts['smooth_conv'])
        self.smooth_c0.SetValue(opts['smooth_c0'])
        self.smooth_c1.SetValue(opts['smooth_c1'])
        self.smooth_sig.SetValue(opts['smooth_sig'])

        if dgroup.datatype == 'xas':
            self.xas_op.SetStringSelection(opts['xas_op'])
            self.xas_e0.SetValue(opts['e0'])
            self.xas_step.SetValue(opts['edge_step'])
            self.xas_pre1.SetValue(opts['pre1'])
            self.xas_pre2.SetValue(opts['pre2'])
            self.xas_nor1.SetValue(opts['norm1'])
            self.xas_nor2.SetValue(opts['norm2'])
            self.xas_vict.SetSelection(opts['nvict'])
            self.xas_nnor.SetSelection(opts['nnorm'])
            self.xas_showe0.SetValue(opts['show_e0'])
            self.xas_autoe0.SetValue(opts['auto_e0'])
            self.xas_autostep.SetValue(opts['auto_step'])
            self.deconv_form.SetStringSelection(opts['deconv_form'])
            self.deconv_ewid.SetValue(opts['deconv_ewid'])

            # self.xas_ppeak_elo.SetValue(opts['ppeak_elo'])
            # self.xas_ppeak_ehi.SetValue(opts['ppeak_ehi'])
            # self.xas_ppeak_emin.SetValue(opts['ppeak_emin'])
            # self.xas_ppeak_emax.SetValue(opts['ppeak_emax'])
            # if len(getattr(dgroup, 'centroid_msg', '')) > 3:
            #    self.xas_ppeak_centroid.SetLabel(dgroup.centroid_msg)


    def build_display(self):
        self.SetFont(Font(10))
        titleopts = dict(font=Font(11), colour='#AA0000')

        gopts = dict(ncols=4, nrows=4, pad=2, itemstyle=LCEN)
        xas = self.xaspanel = GridPanel(self, **gopts)
        gen = self.genpanel = GridPanel(self, **gopts)
        self.btns = {}
        #gen
        opts = dict(action=self.UpdatePlot)

        self.eshift = FloatCtrl(gen, value=0.0, precision=3, gformat=True,
                                size=(65, -1), **opts)
        self.deconv_ewid = FloatCtrl(xas, value=0.5, precision=3,
                                     minval=0, gformat=True, size=(65, -1), **opts)

        self.deconv_form = Choice(xas, choices=DECONV_OPS, size=(100, -1), **opts)

        opts = dict(action=self.onSmoothChoice, size=(30, -1))
        sm_row1 = wx.Panel(gen)
        sm_row2 = wx.Panel(gen)
        sm_siz1 = wx.BoxSizer(wx.HORIZONTAL)
        sm_siz2 = wx.BoxSizer(wx.HORIZONTAL)

        self.smooth_c0 = FloatCtrl(sm_row1, value=2, precision=0, minval=1, **opts)
        self.smooth_c1 = FloatCtrl(sm_row1, value=1, precision=0, minval=1, **opts)
        self.smooth_msg = SimpleText(sm_row1, label='         ', size=(205, -1))
        opts['size'] = (65, -1)
        self.smooth_sig = FloatCtrl(sm_row2, value=1, gformat=True, **opts)

        opts['size'] = (120, -1)
        self.smooth_op = Choice(sm_row1, choices=SMOOTH_OPS, **opts)
        self.smooth_op.SetSelection(0)

        opts['size'] = (100, -1)
        self.smooth_conv = Choice(sm_row2, choices=CONV_OPS, **opts)

        self.smooth_c0.Disable()
        self.smooth_c1.Disable()
        self.smooth_sig.Disable()
        self.smooth_conv.SetSelection(0)
        self.smooth_conv.Disable()


        sm_siz1.Add(self.smooth_op, 0, LCEN, 1)
        sm_siz1.Add(SimpleText(sm_row1, ' n= '), 0, LCEN, 1)
        sm_siz1.Add(self.smooth_c0, 0, LCEN, 1)
        sm_siz1.Add(SimpleText(sm_row1, ' order= '), 0, LCEN, 1)
        sm_siz1.Add(self.smooth_c1, 0, LCEN, 1)
        sm_siz1.Add(self.smooth_msg, 0, LCEN, 1)

        sm_siz2.Add(SimpleText(sm_row2, ' form= '), 0, LCEN, 1)
        sm_siz2.Add(self.smooth_conv, 0, LCEN, 1)
        sm_siz2.Add(SimpleText(sm_row2, ' sigma= '), 0, LCEN, 1)
        sm_siz2.Add(self.smooth_sig, 0, LCEN, 1)
        pack(sm_row1, sm_siz1)
        pack(sm_row2, sm_siz2)

        gen.Add(SimpleText(gen, ' Data Pre-Processing', **titleopts), dcol=8)
        gen.Add(SimpleText(gen, ' Energy shift:'), newrow=True)
        gen.Add(self.eshift, dcol=2)

        gen.Add(SimpleText(gen, ' Smoothing:'), newrow=True)
        gen.Add(sm_row1, dcol=8)
        gen.Add(sm_row2, icol=1, dcol=7, newrow=True)

        gen.pack()

        #xas
        opts = {'action': partial(self.UpdatePlot, setval=True)}
        e0opts_panel = wx.Panel(xas)
        self.xas_autoe0 = Check(e0opts_panel, default=True, label='auto?', **opts)
        self.xas_showe0 = Check(e0opts_panel, default=True, label='show?', **opts)
        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(self.xas_autoe0, 0, LCEN, 4)
        sx.Add(self.xas_showe0, 0, LCEN, 4)
        pack(e0opts_panel, sx)

        self.xas_autostep = Check(xas, default=True, label='auto?', **opts)
        # self.xas_show_ppcen = Check(xas, default=False, label='show?', **opts)
        # self.xas_show_ppfit = Check(xas, default=False, label='show?', **opts)
        # self.xas_show_ppdat = Check(xas, default=False, label='show?', **opts)
        opts = {'action': partial(self.UpdatePlot, setval=False, unzoom=True),
                'size': (250, -1)}
        self.xas_op = Choice(xas, choices=list(XASOPChoices.keys()), **opts)

        self.xas_op.SetStringSelection('Normalized')

        for name in ('e0', 'pre1', 'pre2', 'nor1', 'nor2'):
            # 'ppeak_elo', 'ppeak_emin', 'ppeak_emax', 'ppeak_ehi'):
            bb = BitmapButton(xas, get_icon('plus'),
                              action=partial(self.on_selpoint, opt=name),
                              tooltip='use last point selected from plot')
            self.btns[name] = bb

        opts = {'size': (65, -1), 'gformat': True}


        self.xas_e0 = FloatCtrl(xas, value=0, action=self.onSet_XASE0, **opts)
        self.xas_step = FloatCtrl(xas, value=0, action=self.onSet_XASStep, **opts)

        opts['precision'] = 1
        opts['action'] = partial(self.UpdatePlot, setval=True)
        self.xas_pre1 = FloatCtrl(xas, value=-np.inf, **opts)
        self.xas_pre2 = FloatCtrl(xas, value=-30, **opts)
        self.xas_nor1 = FloatCtrl(xas, value=50, **opts)
        self.xas_nor2 = FloatCtrl(xas, value=np.inf, **opts)

        # self.xas_ppeak_emin = FloatCtrl(xas, value=-31, **opts)
        # self.xas_ppeak_elo = FloatCtrl(xas, value=-15, **opts)
        # self.xas_ppeak_ehi = FloatCtrl(xas, value=-6, **opts)
        # self.xas_ppeak_emax = FloatCtrl(xas, value=-2, **opts)
        # self.xas_ppeak_fit = Button(xas, 'Fit Pre edge Baseline', size=(175, 30),
        #                             action=self.onPreedgeBaseline)
        # self.xas_ppeak_centroid = SimpleText(xas, label='         ', size=(200, -1))

        opts = {'size': (50, -1),
                'choices': ('0', '1', '2', '3'),
                'action': partial(self.UpdatePlot, setval=True)}
        self.xas_vict = Choice(xas, **opts)
        self.xas_nnor = Choice(xas, **opts)
        self.xas_vict.SetSelection(1)
        self.xas_nnor.SetSelection(1)

        def CopyBtn(name):
            return Button(xas, 'Copy', size=(50, 30),
                          action=partial(self.onCopyParam, name))

        xas.Add(SimpleText(xas, ' XAS Data Processing', **titleopts), dcol=6)
        xas.Add(SimpleText(xas, ' Copy to Selected Groups?'), style=RCEN, dcol=3)
        xas.Add(SimpleText(xas, 'Arrays to Plot: '), newrow=True)
        xas.Add(self.xas_op, dcol=6)
        xas.Add((10, 10))
        xas.Add(CopyBtn('xas_op'), style=RCEN)

        xas.Add(SimpleText(xas, 'E0 : '), newrow=True)
        xas.Add(self.btns['e0'])
        xas.Add(self.xas_e0)
        xas.Add(e0opts_panel, dcol=4)
        xas.Add((10, 1))
        xas.Add(CopyBtn('xas_e0'), style=RCEN)

        xas.Add(SimpleText(xas, 'Edge Step: '), newrow=True)
        xas.Add((10, 1))
        xas.Add(self.xas_step)
        xas.Add(self.xas_autostep, dcol=3)
        xas.Add((10, 1))
        xas.Add((10, 1))
        xas.Add(CopyBtn('xas_step'), style=RCEN)

        xas.Add(SimpleText(xas, 'Pre-edge range: '), newrow=True)
        xas.Add(self.btns['pre1'])
        xas.Add(self.xas_pre1)
        xas.Add(SimpleText(xas, ':'))
        xas.Add(self.btns['pre2'])
        xas.Add(self.xas_pre2)
        xas.Add(SimpleText(xas, 'Victoreen:'))
        xas.Add(self.xas_vict)
        xas.Add(CopyBtn('xas_pre'), style=RCEN)

        xas.Add(SimpleText(xas, 'Normalization range: '), newrow=True)
        xas.Add(self.btns['nor1'])
        xas.Add(self.xas_nor1)
        xas.Add(SimpleText(xas, ':'))
        xas.Add(self.btns['nor2'])
        xas.Add(self.xas_nor2)
        xas.Add(SimpleText(xas, 'PolyOrder:'))
        xas.Add(self.xas_nnor)
        xas.Add(CopyBtn('xas_norm'), style=RCEN)


        xas.Add(SimpleText(xas, ' Deconvolution:'), newrow=True)
        xas.Add(self.deconv_form, dcol=4)
        xas.Add(SimpleText(xas, ' E width:'), dcol=1)
        xas.Add(self.deconv_ewid,  dcol=2)

        xas.Add((10, 1), newrow=True)
        xas.Add(HLine(xas, size=(250, 2)), dcol=7, style=CEN)

#         xas.Add(SimpleText(xas, 'Pre-edge Peak Baseline Removal: '),
#                 dcol=6, newrow=True)
#         xas.Add(self.xas_ppeak_fit, dcol=3, style=RCEN)
#         xas.Add(SimpleText(xas, 'Pre-edge Peak range: '), newrow=True)
#
#         xas.Add(self.btns['ppeak_elo'])
#         xas.Add(self.xas_ppeak_elo)
#         xas.Add(SimpleText(xas, ':'))
#         xas.Add(self.btns['ppeak_ehi'])
#         xas.Add(self.xas_ppeak_ehi)
#         xas.Add(self.xas_show_ppdat, dcol=2)
#         xas.Add(CopyBtn('xas_ppeak_dat'), style=RCEN)
#
#         xas.Add(SimpleText(xas, 'Pre-edge Fit range: '), newrow=True)
#         xas.Add(self.btns['ppeak_emin'])
#         xas.Add(self.xas_ppeak_emin)
#         xas.Add(SimpleText(xas, ':'))
#         xas.Add(self.btns['ppeak_emax'])
#         xas.Add(self.xas_ppeak_emax)
#         xas.Add(self.xas_show_ppfit, dcol=2)
#         xas.Add(CopyBtn('xas_ppeak_fit'), style=RCEN)
#         xas.Add(SimpleText(xas, 'Pre-edge Centroid: '), newrow=True)
#         xas.Add(self.xas_ppeak_centroid, dcol=5)
#         xas.Add(self.xas_show_ppcen, dcol=2)

        xas.pack()

        saveconf = Button(self, 'Save as Default Settings', size=(200, 30),
                          action=self.onSaveConfigBtn)

        hxline = HLine(self, size=(550, 2))

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.AddMany([((10, 10), 0, LCEN, 10), (gen,      0, LCEN, 10),
                       ((10, 10), 0, LCEN, 10), (hxline,   0, LCEN, 10),
                       ((10, 10), 0, LCEN, 10), (xas,      0, LCEN, 10),
                       ((10, 10), 0, LCEN, 10), (saveconf, 0, LCEN, 10),
                       ])

        xas.Disable()

        pack(self, sizer)

    def onPreedgeBaseline(self, evt=None):
        pass
#         opts = {'elo':  self.xas_ppeak_elo.GetValue(),
#                 'ehi':  self.xas_ppeak_ehi.GetValue(),
#                 'emin': self.xas_ppeak_emin.GetValue(),
#                 'emax': self.xas_ppeak_emax.GetValue()}
#
#         self.xas_op.SetStringSelection('Pre-edge Peaks + Baseline')
#
#         gname = self.controller.groupname
#         dgroup = self.controller.get_group(gname)
#         self.controller.xas_preedge_baseline(dgroup, opts=opts)
#         self.xas_ppeak_centroid.SetLabel(dgroup.centroid_msg)
#         self.process(gname)

    def onSaveConfigBtn(self, evt=None):
        conf = self.controller.larch.symtable._sys.xas_viewer

        data_proc = {}
        data_proc.update(getattr(conf, 'data_proc', {}))

        data_proc['eshift'] = self.eshift.GetValue()
        data_proc['smooth_op'] = str(self.smooth_op.GetStringSelection())
        data_proc['smooth_c0'] = int(self.smooth_c0.GetValue())
        data_proc['smooth_c1'] = int(self.smooth_c1.GetValue())
        data_proc['smooth_sig'] = float(self.smooth_sig.GetValue())
        data_proc['smooth_conv'] = str(self.smooth_conv.GetStringSelection())

        conf.data_proc = data_proc

        if self.xaspanel.Enabled:
            xas_proc = {}
            xas_proc.update(getattr(conf, 'xas_proc', {}))

            xas_proc['auto_e0'] = True
            xas_proc['auto_step'] = True

            xas_proc['pre1'] = self.xas_pre1.GetValue()
            xas_proc['pre2'] = self.xas_pre2.GetValue()
            xas_proc['norm1'] = self.xas_nor1.GetValue()
            xas_proc['norm2'] = self.xas_nor2.GetValue()

            xas_proc['show_e0'] = self.xas_showe0.IsChecked()
            xas_proc['nnorm'] = int(self.xas_nnor.GetSelection())
            xas_proc['nvict'] = int(self.xas_vict.GetSelection())
            xas_proc['xas_op'] = str(self.xas_op.GetStringSelection())

            # xas_proc['ppeak_elo'] = self.xas_ppeak_elo.GetValue()
            # xas_proc['ppeak_ehi'] = self.xas_ppeak_ehi.GetValue()
            # xas_proc['ppeak_emin'] = self.xas_ppeak_emin.GetValue()
            # xas_proc['ppeak_emax'] = self.xas_ppeak_emax.GetValue()
            conf.xas_proc = xas_proc

    def onCopyParam(self, name=None, evt=None):
        proc_opts = self.controller.group.proc_opts
        opts = {}
        name = str(name)
        if name == 'xas_op':
            opts['xas_op'] = proc_opts['xas_op']
        elif name == 'xas_e0':
            opts['e0'] = proc_opts['e0']
            opts['show_e0'] = proc_opts['show_e0']
            opts['auto_e0'] = False
        elif name == 'xas_step':
            opts['edge_step'] = proc_opts['edge_step']
            opts['auto_step'] = False
        elif name == 'xas_pre':
            opts['nvict'] = proc_opts['nvict']
            opts['pre1'] = proc_opts['pre1']
            opts['pre2'] = proc_opts['pre2']
        elif name == 'xas_norm':
            opts['nnorm'] = proc_opts['nnorm']
            opts['norm1'] = proc_opts['norm1']
            opts['norm2'] = proc_opts['norm2']
#         elif name == 'xas_ppeak_dat':
#             opts['ppeak_elo'] = proc_opts['ppeak_elo']
#             opts['ppeak_ehi'] = proc_opts['ppeak_ehi']
#         elif name == 'xas_ppeak_fit':
#             opts['ppeak_emin'] = proc_opts['ppeak_emin']
#             opts['ppeak_emax'] = proc_opts['ppeak_emax']

        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group:
                grp.proc_opts.update(opts)
                self.fill(grp)
                self.process(grp.groupname)

    def onSmoothChoice(self, evt=None, value=1):
        try:
            choice = self.smooth_op.GetStringSelection().lower()
            conv = self.smooth_conv.GetStringSelection()
            self.smooth_c0.Disable()
            self.smooth_c1.Disable()
            self.smooth_conv.Disable()
            self.smooth_sig.Disable()
            self.smooth_msg.SetLabel('')
            self.smooth_c0.SetMin(1)
            self.smooth_c0.odd_only = False
            if choice.startswith('box'):
                self.smooth_c0.Enable()
            elif choice.startswith('savi'):
                self.smooth_c0.Enable()
                self.smooth_c1.Enable()
                self.smooth_c0.Enable()
                self.smooth_c0.odd_only = True

                c0 = int(self.smooth_c0.GetValue())
                c1 = int(self.smooth_c1.GetValue())
                x0 = max(c1+1, c0)
                if x0 % 2 == 0:
                    x0 += 1
                self.smooth_c0.SetMin(c1+1)
                if c0 != x0:
                    self.smooth_c0.SetValue(x0)
                self.smooth_msg.SetLabel('n must odd and  > order+1')

            elif choice.startswith('conv'):
                self.smooth_conv.Enable()
                self.smooth_sig.Enable()
            self.needs_update = True
        except AttributeError:
            pass

    def onSet_XASE0(self, evt=None, value=None):
        self.xas_autoe0.SetValue(0)
        self.needs_update = True
        self.unzoom_on_update = False

    def onSet_XASStep(self, evt=None, value=None):
        self.xas_autostep.SetValue(0)
        self.needs_update = True
        self.unzoom_on_update = False

    def onProcessTimer(self, evt=None):
        if self.needs_update and self.controller.groupname is not None:
            self.process(self.controller.groupname)
            self.controller.plot_group(groupname=self.controller.groupname,
                                       new=True, unzoom=self.unzoom_on_update)
            self.needs_update = False

    def UpdatePlot(self, evt=None, unzoom=True, setval=True, value=None, **kws):
        if not setval:
            self.unzoom_on_update = unzoom
        self.needs_update = True

    def on_selpoint(self, evt=None, opt='e0'):
        xval, yval = self.controller.get_cursor()
        if xval is None:
            return

        e0 = self.xas_e0.GetValue()
        if opt == 'e0':
            self.xas_e0.SetValue(xval)
            self.xas_autoe0.SetValue(0)
        elif opt == 'pre1':
            self.xas_pre1.SetValue(xval-e0)
        elif opt == 'pre2':
            self.xas_pre2.SetValue(xval-e0)
        elif opt == 'nor1':
            self.xas_nor1.SetValue(xval-e0)
        elif opt == 'nor2':
            self.xas_nor2.SetValue(xval-e0)
        # elif opt == 'ppeak_elo':
        #    self.xas_ppeak_elo.SetValue(xval-e0)
        # elif opt == 'ppeak_ehi':
        #    self.xas_ppeak_ehi.SetValue(xval-e0)
        # elif opt == 'ppeak_emin':
        #     self.xas_ppeak_emin.SetValue(xval-e0)
        # elif opt == 'ppeak_emax':
        #     self.xas_ppeak_emax.SetValue(xval-e0)
        elif opt == 'eshift':
            self.eshift.SetValue(xval)
        elif opt == 'yshift':
            self.yshift.SetValue(yval)
        else:
            print(" unknown selection point ", opt)

    def process(self, gname, **kws):
        """ handle process (pre-edge/normalize) XAS data from XAS form, overwriting
        larch group 'x' and 'y' attributes to be plotted
        """
        self.needs_update = False
        dgroup = self.controller.get_group(gname)
        proc_opts = {}
        save_unzoom = self.unzoom_on_update
        dgroup.custom_plotopts = {}
        proc_opts['eshift'] = self.eshift.GetValue()
        proc_opts['smooth_op'] = self.smooth_op.GetStringSelection()
        proc_opts['smooth_c0'] = int(self.smooth_c0.GetValue())
        proc_opts['smooth_c1'] = int(self.smooth_c1.GetValue())
        proc_opts['smooth_sig'] = float(self.smooth_sig.GetValue())
        proc_opts['smooth_conv'] = self.smooth_conv.GetStringSelection()
        proc_opts['deconv_form'] = self.deconv_form.GetStringSelection()
        proc_opts['deconv_ewid'] = self.deconv_ewid.GetValue()

        self.xaspanel.Enable(dgroup.datatype.startswith('xas'))

        if dgroup.datatype.startswith('xas'):
            proc_opts['datatype'] = 'xas'
            proc_opts['e0'] = self.xas_e0.GetValue()
            proc_opts['edge_step'] = self.xas_step.GetValue()
            proc_opts['pre1'] = self.xas_pre1.GetValue()
            proc_opts['pre2'] = self.xas_pre2.GetValue()
            proc_opts['norm1'] = self.xas_nor1.GetValue()
            proc_opts['norm2'] = self.xas_nor2.GetValue()

            proc_opts['auto_e0'] = self.xas_autoe0.IsChecked()
            proc_opts['show_e0'] = self.xas_showe0.IsChecked()
            proc_opts['auto_step'] = self.xas_autostep.IsChecked()
            proc_opts['nnorm'] = int(self.xas_nnor.GetSelection())
            proc_opts['nvict'] = int(self.xas_vict.GetSelection())
            proc_opts['xas_op'] = self.xas_op.GetStringSelection()

            # proc_opts['ppeak_elo'] = self.xas_ppeak_elo.GetValue()
            # proc_opts['ppeak_ehi'] = self.xas_ppeak_ehi.GetValue()
            # proc_opts['ppeak_emin'] = self.xas_ppeak_emin.GetValue()
            # proc_opts['ppeak_emax'] = self.xas_ppeak_emax.GetValue()

        self.controller.process(dgroup, proc_opts=proc_opts)

        if dgroup.datatype.startswith('xas'):
            if self.xas_autoe0.IsChecked():
                self.xas_e0.SetValue(dgroup.proc_opts['e0'], act=False)
            if self.xas_autostep.IsChecked():
                self.xas_step.SetValue(dgroup.proc_opts['edge_step'], act=False)

            self.xas_pre1.SetValue(dgroup.proc_opts['pre1'])
            self.xas_pre2.SetValue(dgroup.proc_opts['pre2'])
            self.xas_nor1.SetValue(dgroup.proc_opts['norm1'])
            self.xas_nor2.SetValue(dgroup.proc_opts['norm2'])

            dgroup.orig_ylabel = dgroup.plot_ylabel
            dgroup.plot_ylabel = r'$\mu$'
            dgroup.plot_y2label = None
            dgroup.plot_xlabel = r'$E \,\mathrm{(eV)}$'
            dgroup.plot_yarrays = [(dgroup.mu, PLOTOPTS_1, dgroup.plot_ylabel)]

            dgroup.ydat = dgroup.mu

            pchoice = XASOPChoices[self.xas_op.GetStringSelection()]

            if pchoice == 'prelines':
                dgroup.plot_yarrays = [(dgroup.mu, PLOTOPTS_1, r'$\mu$'),
                                       (dgroup.pre_edge, PLOTOPTS_2, 'pre edge'),
                                       (dgroup.post_edge, PLOTOPTS_2, 'post edge')]
                dgroup.ydat = dgroup.mu
            elif pchoice == 'preedge':
                dgroup.pre_edge_sub = dgroup.norm * dgroup.edge_step
                dgroup.plot_yarrays = [(dgroup.pre_edge_sub, PLOTOPTS_1,
                                        r'pre-edge subtracted $\mu$')]
                dgroup.ydat = dgroup.pre_edge_sub
                dgroup.plot_ylabel = r'pre-edge subtracted $\mu$'
            elif pchoice == 'norm+deriv':
                dgroup.plot_yarrays = [(dgroup.norm, PLOTOPTS_1, r'normalized $\mu$'),
                                       (dgroup.dmude, PLOTOPTS_D, r'$d\mu/dE$')]
                dgroup.plot_ylabel = r'normalized $\mu$'
                dgroup.plot_y2label = r'$d\mu/dE$'
                dgroup.ydat = dgroup.norm

            elif pchoice == 'norm':
                dgroup.plot_yarrays = [(dgroup.norm, PLOTOPTS_1, r'normalized $\mu$')]
                dgroup.plot_ylabel = r'normalized $\mu$'
                dgroup.ydat = dgroup.norm

            elif pchoice == 'deriv':
                dgroup.plot_yarrays = [(dgroup.dmude, PLOTOPTS_1, r'$d\mu/dE$')]
                dgroup.plot_ylabel = r'$d\mu/dE$'
                dgroup.ydat = dgroup.dmude

            if pchoice == 'deconv' and hasattr(dgroup, 'deconv'):
                dgroup.plot_yarrays = [(dgroup.deconv, PLOTOPTS_1, r'deconvolved'),
                                       (dgroup.norm, PLOTOPTS_1, r'normalized $\mu$')]
                dgroup.plot_ylabel = r'deconvolved and normalized $\mu$'
                dgroup.ydat = dgroup.deconv

            y4e0 = dgroup.ydat

#             elif pchoice == 'prepeaks+base' and hasattr(dgroup, 'prepeaks'):
#                 ppeaks = dgroup.prepeaks
#                 i0 = index_of(dgroup.energy, ppeaks.energy[0])
#                 i1 = index_of(dgroup.energy, ppeaks.energy[-1]) + 1
#                 dgroup.prepeaks_baseline = dgroup.norm*1.0
#                 dgroup.prepeaks_baseline[i0:i1] = ppeaks.baseline
#
#                 dgroup.plot_yarrays = [(dgroup.norm, PLOTOPTS_1,
#                                         r'normalized $\mu$'),
#                                        (dgroup.prepeaks_baseline, PLOTOPTS_2,
#                                         'pre-edge peaks baseline')]
#
#                 jmin, jmax = max(0, i0-2), i1+3
#                 dgroup.custom_plotopts = {'xmin':dgroup.energy[jmin],
#                                           'xmax':dgroup.energy[jmax],
#                                           'ymax':max(dgroup.norm[jmin:jmax])*1.05}
#                 dgroup.y = y4e0 = dgroup.norm
#                 dgroup.plot_ylabel = r'normalized $\mu$'
#
#             elif pchoice == 'prepeaks' and hasattr(dgroup, 'prepeaks'):
#                 ppeaks = dgroup.prepeaks
#                 i0 = index_of(dgroup.energy, ppeaks.energy[0])
#                 i1 = index_of(dgroup.energy, ppeaks.energy[-1]) + 1
#                 dgroup.prepeaks_baseline = dgroup.norm*1.0
#                 dgroup.prepeaks_baseline[i0:i1] = ppeaks.baseline
#                 dgroup.prepeaks_norm = dgroup.norm - dgroup.prepeaks_baseline
#
#                 dgroup.plot_yarrays = [(dgroup.prepeaks_norm, PLOTOPTS_1,
#                                         'normalized pre-edge peaks')]
#                 dgroup.y = y4e0 = dgroup.prepeaks_norm
#                 dgroup.plot_ylabel = r'normalized $\mu$'
#                 jmin, jmax = max(0, i0-2), i1+3
#                 dgroup.custom_plotopts = {'xmin':dgroup.energy[jmin],
#                                           'xmax':dgroup.energy[jmax],
#                                           'ymax':max(dgroup.y[jmin:jmax])*1.05}
#
            dgroup.plot_extras = []
            if self.xas_showe0.IsChecked():
                ie0 = index_of(dgroup.energy, dgroup.e0)
                dgroup.plot_extras.append(('marker', dgroup.e0, y4e0[ie0], {}))

#             if self.xas_show_ppfit.IsChecked():
#                 popts = {'color': '#DDDDCC'}
#                 emin = dgroup.e0 + self.xas_ppeak_emin.GetValue()
#                 emax = dgroup.e0 + self.xas_ppeak_emax.GetValue()
#                 imin = index_of(dgroup.energy, emin)
#                 imax = index_of(dgroup.energy, emax)
#
#                 dgroup.plot_extras.append(('vline', emin, y4e0[imin], popts))
#                 dgroup.plot_extras.append(('vline', emax, y4e0[imax], popts))
#
#             if self.xas_show_ppdat.IsChecked():
#                 popts = {'marker': '+', 'markersize': 6}
#                 elo = dgroup.e0 + self.xas_ppeak_elo.GetValue()
#                 ehi = dgroup.e0 + self.xas_ppeak_ehi.GetValue()
#                 ilo = index_of(dgroup.energy, elo)
#                 ihi = index_of(dgroup.energy, ehi)
#
#                 dgroup.plot_extras.append(('marker', elo, y4e0[ilo], popts))
#                 dgroup.plot_extras.append(('marker', ehi, y4e0[ihi], popts))
#
#             if self.xas_show_ppcen.IsChecked() and hasattr(dgroup, 'prepeaks'):
#                 popts = {'color': '#EECCCC'}
#                 ecen = getattr(dgroup.prepeaks, 'centroid', -1)
#                 if ecen > min(dgroup.energy):
#                     dgroup.plot_extras.append(('vline', ecen, None, popts))

        self.unzoom_on_update = save_unzoom
