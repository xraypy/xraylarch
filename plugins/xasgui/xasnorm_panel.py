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

PlotOne_Choices = OrderedDict((('Raw Data', 'mu'),
                               ('Normalized', 'norm'),
                               ('Derivative', 'dmude'),
                               ('Normalized + Derivative', 'norm+deriv'),
                               ('Flattened', 'flat'),
                               ('Pre-edge subtracted', 'preedge'),
                               ('Raw Data + Pre-edge/Post-edge', 'prelines'),
                               ('Deconvolved + Normalized',   'deconv+norm'),
                               ('Deconvolved',   'deconv')
                               ))

PlotSel_Choices = OrderedDict((('Raw Data', 'mu'),
                               ('Normalized', 'norm'),
                               ('Flattened', 'flat'),
                               ('Derivative', 'dmude')))


PlotLabels = {'mu': r'$\mu(E)',
              'norm': r'normalized $\mu(E)$',
              'flat': r'flattened $\mu(E)$',
              'deconv': r'deconvolved $\mu(E)$',
              'dmude': r'$d\mu/dE$'}

class XASNormPanel(wx.Panel):
    """XAS normalization Panel"""
    def __init__(self, parent, controller=None, reporter=None, **kws):
        wx.Panel.__init__(self, parent, -1, **kws)

        self.controller = controller
        self.reporter = reporter
        self.needs_update = False
        self.zoom_out_on_update = True
        self.proc_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onProcessTimer, self.proc_timer)
        self.proc_timer.Start(100)
        self.build_display()

    def edit_config(self, event=None):
        """edit config"""
        pass

    def fill(self, dgroup):
        opts = self.controller.get_proc_opts(dgroup)
        self.plotone_op.SetStringSelection(opts['plotone_op'])
        self.plotsel_op.SetStringSelection(opts['plotsel_op'])
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

    def build_display(self):
        self.SetFont(Font(10))
        titleopts = dict(font=Font(11), colour='#AA0000')

        xas = self.xaspanel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LCEN)
        self.btns = {}

        opts = dict(action=self.UpdatePlot)
        self.deconv_ewid = FloatCtrl(xas, value=0.5, precision=3,
                                     minval=0, gformat=True, size=(65, -1), **opts)

        self.deconv_form = Choice(xas, choices=DECONV_OPS, size=(100, -1), **opts)

        opts = {'action': partial(self.UpdatePlot, setval=True)}
        e0opts_panel = wx.Panel(xas)
        self.xas_autoe0 = Check(e0opts_panel, default=True, label='auto?', **opts)
        self.xas_showe0 = Check(e0opts_panel, default=True, label='show?', **opts)
        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(self.xas_autoe0, 0, LCEN, 4)
        sx.Add(self.xas_showe0, 0, LCEN, 4)
        pack(e0opts_panel, sx)

        self.xas_autostep = Check(xas, default=True, label='auto?', **opts)

        self.plotone_op = Choice(xas, choices=list(PlotOne_Choices.keys()),
                                 action=partial(self.UpdatePlot, setval=False, zoom_out=True),
                                 size=(200, -1))
        self.plotsel_op = Choice(xas, choices=list(PlotSel_Choices.keys()),
                                 action=self.onPlotSel, size=(200, -1))

        self.plotone_op.SetStringSelection('Normalized')
        self.plotsel_op.SetStringSelection('Normalized')

        for name in ('e0', 'pre1', 'pre2', 'nor1', 'nor2'):
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

        plot_sel = Button(xas, 'Plot Selected Groups', size=(150, 30),
                          action=self.onPlotSel)

        plot_one = Button(xas, 'Plot This Group', size=(150, 30),
                          action=self.onPlotOne)

        opts = {'size': (50, -1), 'choices': ('0', '1', '2', '3'),
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

        xas.Add(plot_sel, newrow=True)
        xas.Add(self.plotsel_op, dcol=6)

        xas.Add(plot_one, newrow=True)
        xas.Add(self.plotone_op, dcol=6)
        xas.Add((10, 10))
        xas.Add(CopyBtn('plotone_op'), style=RCEN)

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
        xas.pack()

        saveconf = Button(self, 'Save as Default Settings', size=(200, 30),
                          action=self.onSaveConfigBtn)

        hxline = HLine(self, size=(550, 2))

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.AddMany([((10, 10), 0, LCEN, 10), (hxline,   0, LCEN, 10),
                       ((10, 10), 0, LCEN, 10), (xas,      0, LCEN, 10),
                       ((10, 10), 0, LCEN, 10), (saveconf, 0, LCEN, 10),
                       ])

        pack(self, sizer)


    def onPlotOne(self, evt=None, groupname=None):
        if groupname is None:
            groupname = self.controller.groupname

        dgroup = self.controller.get_group(groupname)
        if dgroup is not None:
            self.controller.plot_group(groupname=groupname, new=True)

    def onPlotSel(self, evt=None):
        newplot = True
        group_ids = self.controller.filelist.GetCheckedStrings()
        if len(group_ids) < 1:
            return
        last_id = group_ids[-1]

        yarray_name  = PlotSel_Choices[self.plotsel_op.GetStringSelection()]
        ylabel = PlotLabels[yarray_name]

        for checked in group_ids:
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            plot_yarrays = [(yarray_name, PLOTOPTS_1, dgroup.filename)]
            dgroup.plot_ylabel = ylabel
            if dgroup is not None:
                dgroup.plot_extras = []
                self.controller.plot_group(groupname=groupname,
                                           title='',
                                           new=newplot,
                                           plot_yarrays=plot_yarrays,
                                           show_legend=True,
                                           delay_draw=(last_id!=checked))
                newplot=False



    def onSaveConfigBtn(self, evt=None):
        conf = self.controller.larch.symtable._sys.xas_viewer

        data_proc = {}
        data_proc.update(getattr(conf, 'data_proc', {}))

        data_proc['auto_e0'] = True
        data_proc['auto_step'] = True

        data_proc['pre1'] = self.xas_pre1.GetValue()
        data_proc['pre2'] = self.xas_pre2.GetValue()
        data_proc['norm1'] = self.xas_nor1.GetValue()
        data_proc['norm2'] = self.xas_nor2.GetValue()

        data_proc['show_e0'] = self.xas_showe0.IsChecked()
        data_proc['nnorm'] = int(self.xas_nnor.GetSelection())
        data_proc['nvict'] = int(self.xas_vict.GetSelection())
        data_proc['plotone_op'] = str(self.plotone_op.GetStringSelection())
        data_proc['plotsel_op'] = str(self.plotsel_op.GetStringSelection())


    def onCopyParam(self, name=None, evt=None):
        proc_opts = self.controller.group.proc_opts
        opts = {}
        name = str(name)
        if name == 'plotone_op':
            opts['plotone_op'] = proc_opts['plotone_op']
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


        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group:
                grp.proc_opts.update(opts)
                self.fill(grp)
                self.process(grp.groupname)

    def onSet_XASE0(self, evt=None, value=None):
        self.xas_autoe0.SetValue(0)
        self.needs_update = True
        self.zoom_out_on_update = False

    def onSet_XASStep(self, evt=None, value=None):
        self.xas_autostep.SetValue(0)
        self.needs_update = True
        self.zoom_out_on_update = False

    def onProcessTimer(self, evt=None):
        if self.needs_update and self.controller.groupname is not None:
            self.process(self.controller.groupname)
            self.controller.plot_group(groupname=self.controller.groupname,
                                       new=True, zoom_out=self.zoom_out_on_update)
            self.needs_update = False

    def UpdatePlot(self, evt=None, zoom_out=True, setval=True, value=None, **kws):
        if not setval:
            self.zoom_out_on_update = zoom_out
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
        else:
            print(" unknown selection point ", opt)

    def process(self, gname, **kws):
        """ handle process (pre-edge/normalize) XAS data from XAS form, overwriting
        larch group 'x' and 'y' attributes to be plotted
        """
        self.needs_update = False
        dgroup = self.controller.get_group(gname)
        proc_opts = {}
        save_zoom_out = self.zoom_out_on_update
        dgroup.custom_plotopts = {}

        proc_opts['deconv_form'] = self.deconv_form.GetStringSelection()
        proc_opts['deconv_ewid'] = self.deconv_ewid.GetValue()
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
        proc_opts['plotone_op'] = self.plotone_op.GetStringSelection()
        proc_opts['plotsel_op'] = self.plotsel_op.GetStringSelection()

        self.controller.process(dgroup, proc_opts=proc_opts)

        if self.xas_autoe0.IsChecked():
            self.xas_e0.SetValue(dgroup.proc_opts['e0'], act=False)
        if self.xas_autostep.IsChecked():
            self.xas_step.SetValue(dgroup.proc_opts['edge_step'], act=False)

        self.xas_pre1.SetValue(dgroup.proc_opts['pre1'])
        self.xas_pre2.SetValue(dgroup.proc_opts['pre2'])
        self.xas_nor1.SetValue(dgroup.proc_opts['norm1'])
        self.xas_nor2.SetValue(dgroup.proc_opts['norm2'])

        #
        lab = PlotLabels['norm']
        dgroup.plot_y2label = None
        dgroup.plot_xlabel = r'$E \,\mathrm{(eV)}$'
        dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab)]

        pchoice  = PlotOne_Choices[self.plotone_op.GetStringSelection()]

        if pchoice in ('mu', 'norm', 'flat', 'dmude'):
            lab = PlotLabels[pchoice]
            dgroup.plot_yarrays = [(pchoice, PLOTOPTS_1, lab)]

        elif pchoice == 'prelines':
            dgroup.plot_yarrays = [('mu', PLOTOPTS_1, lab),
                                   ('pre_edge', PLOTOPTS_2, 'pre edge'),
                                   ('post_edge', PLOTOPTS_2, 'post edge')]
        elif pchoice == 'preedge':
            dgroup.pre_edge_sub = dgroup.norm * dgroup.edge_step
            dgroup.plot_yarrays = [('pre_edge_sub', PLOTOPTS_1,
                                    r'pre-edge subtracted $\mu$')]
            lab = r'pre-edge subtracted $\mu$'

        elif pchoice == 'norm+deriv':
            lab = PlotLabels['norm']
            lab2 = PlotLabels['dmude']
            dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab),
                                   ('dmude', PLOTOPTS_D, lab2)]
            dgroup.plot_y2label = lab2

        elif pchoice == 'deconv' and hasattr(dgroup, 'deconv'):
            lab = PlotLabels['deconv']
            dgroup.plot_yarrays = [('deconv', PLOTOPTS_1, lab)]

        elif pchoice == 'deconv+norm' and hasattr(dgroup, 'deconv'):
            lab1 = PlotLabels['norm']
            lab2 = PlotLabels['deconv']
            dgroup.plot_yarrays = [('deconv', PLOTOPTS_1, lab2),
                                   ('norm', PLOTOPTS_1, lab1)]
            lab = lab1 + lab2

        dgroup.plot_ylabel = lab
        y4e0 = dgroup.ydat = getattr(dgroup, dgroup.plot_yarrays[0][0], dgroup.mu)
        dgroup.plot_extras = []
        if self.xas_showe0.IsChecked():
            ie0 = index_of(dgroup.energy, dgroup.e0)
            dgroup.plot_extras.append(('marker', dgroup.e0, y4e0[ie0], {}))

        self.zoom_out_on_update = save_zoom_out
