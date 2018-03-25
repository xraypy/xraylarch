#!/usr/bin/env python
"""
XANES Data Viewer and Analysis Tool
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
from larch.wxlib import BitmapButton, FloatCtrl
from larch_plugins.wx.icons import get_icon

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


PlotOne_Choices_nonxas = OrderedDict((('Raw Data', 'mu'),
                                      ('Derivative', 'dmude'),
                                      ('Data + Derivative', 'norm+deriv')))

PlotSel_Choices_nonxas = OrderedDict((('Raw Data', 'mu'),
                                      ('Derivative', 'dmude')))


def default_xasnorm_config():
    return dict(e0=0, edge_step=None, pre1=-200, pre2=-25, nnorm=2, norm1=25,
                norm2=-10, nvict=1, auto_step=True, auto_e0=True,
                show_e0=True, plotone_op='Normalized',
                plotsel_op='Normalized', deconv_form='none',
                deconv_ewid=0.5)


class XASNormPanel(wx.Panel):
    """XAS normalization Panel"""
    def __init__(self, parent, controller=None, reporter=None, **kws):
        wx.Panel.__init__(self, parent, -1, **kws)

        self.controller = controller
        self.reporter = reporter
        self.skip_process = False
        self.build_display()

    def onPanelExposed(self, **kws):
        # called when notebook is selected
        try:
            fname = self.controller.filelist.GetStringSelection()
            gname = self.controller.file_groups[fname]
            dgroup = self.controller.get_group(gname)
            self.fill_form(dgroup)
        except:
            pass

    def larch_eval(self, cmd):
        """eval"""
        self.controller.larch.eval(cmd)

    def build_display(self):
        self.SetFont(Font(10))
        titleopts = dict(font=Font(11), colour='#AA0000')

        xas = self.xaspanel = GridPanel(self, ncols=4, nrows=4, pad=2, itemstyle=LCEN)

        self.plotone_op = Choice(xas, choices=list(PlotOne_Choices.keys()),
                                 action=self.onPlotOne, size=(200, -1))
        self.plotsel_op = Choice(xas, choices=list(PlotSel_Choices.keys()),
                                 action=self.onPlotSel, size=(200, -1))

        self.plotone_op.SetStringSelection('Normalized')
        self.plotsel_op.SetStringSelection('Normalized')

        plot_one = Button(xas, 'Plot This Group', size=(150, -1),
                         action=self.onPlotOne)

        plot_sel = Button(xas, 'Plot Selected Groups', size=(150, -1),
                         action=self.onPlotSel)

        self.btns = {}

        opts = dict(action=self.onReprocess)

        self.deconv_ewid = FloatCtrl(xas, value=0.5, precision=2,
                                     minval=0, size=(50, -1), **opts)

        self.deconv_form = Choice(xas, choices=DECONV_OPS, size=(100, -1), **opts)

        e0opts_panel = wx.Panel(xas)
        self.xas_autoe0 = Check(e0opts_panel, default=True, label='auto?', **opts)
        self.xas_showe0 = Check(e0opts_panel, default=True, label='show?', **opts)
        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(self.xas_autoe0, 0, LCEN, 4)
        sx.Add(self.xas_showe0, 0, LCEN, 4)
        pack(e0opts_panel, sx)

        self.xas_autostep = Check(xas, default=True, label='auto?', **opts)


        for name in ('e0', 'pre1', 'pre2', 'nor1', 'nor2'):
            bb = BitmapButton(xas, get_icon('plus'),
                              action=partial(self.on_selpoint, opt=name),
                              tooltip='use last point selected from plot')
            self.btns[name] = bb

        opts['size'] = (50, -1)
        self.xas_vict = Choice(xas, choices=('0', '1', '2', '3'), **opts)
        self.xas_nnor = Choice(xas, choices=('0', '1', '2', '3'), **opts)
        self.xas_vict.SetSelection(1)
        self.xas_nnor.SetSelection(1)

        opts.update({'size': (75, -1), 'precision': 1})

        self.xas_pre1 = FloatCtrl(xas, value=-np.inf, **opts)
        self.xas_pre2 = FloatCtrl(xas, value=-30, **opts)
        self.xas_nor1 = FloatCtrl(xas, value=50,   **opts)
        self.xas_nor2 = FloatCtrl(xas, value=np.inf, **opts)

        opts = {'size': (75, -1), 'gformat': True}
        self.xas_e0 = FloatCtrl(xas, value=0, action=self.onSet_XASE0, **opts)
        self.xas_step = FloatCtrl(xas, value=0, action=self.onSet_XASStep, **opts)


        saveconf = Button(xas, 'Save as Default Settings', size=(200, -1),
                          action=self.onSaveConfigBtn)

        def CopyBtn(name):
            return Button(xas, 'Copy', size=(50, -1),
                          action=partial(self.onCopyParam, name))

        xas.Add(SimpleText(xas, ' XAS Pre-edge subtraction and Normalization',
                           **titleopts), dcol=6)
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
        xas.Add(SimpleText(xas, 'Poly Order:'))
        xas.Add(self.xas_nnor)
        xas.Add(CopyBtn('xas_norm'), style=RCEN)

        xas.Add(SimpleText(xas, ' Deconvolution:'), newrow=True)
        xas.Add(self.deconv_form, dcol=5)
        xas.Add(SimpleText(xas, 'Energy width:'))
        xas.Add(self.deconv_ewid)
        xas.Add(CopyBtn('deconv'), style=RCEN)

        xas.Add(saveconf, dcol=6, newrow=True)
        xas.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((5,5), 0, LCEN, 3)
        sizer.Add(HLine(self, size=(550, 2)), 0, LCEN, 3)
        sizer.Add(xas,   0, LCEN, 3)
        sizer.Add((5,5), 0, LCEN, 3)
        sizer.Add(HLine(self, size=(550, 2)), 0, LCEN, 3)
        pack(self, sizer)


    def get_config(self, dgroup=None):
        """get processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()

        conf = getattr(dgroup, 'xasnorm_config', {})
        if 'e0' not in conf:
            conf = default_xasnorm_config()
        dgroup.xasnorm_config = conf
        return conf

    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)
        self.skip_process = True

        widlist = (self.xas_e0, self.xas_step, self.xas_pre1,
                   self.xas_pre2, self.xas_nor1, self.xas_nor2,
                   self.xas_vict, self.xas_nnor, self.xas_showe0,
                   self.xas_autoe0, self.xas_autostep,
                   self.deconv_form, self.deconv_ewid)

        if dgroup.datatype == 'xas':
            for k in widlist:
                k.Enable()

            self.plotone_op.SetChoices(list(PlotOne_Choices.keys()))
            self.plotsel_op.SetChoices(list(PlotSel_Choices.keys()))

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
        else:
            self.plotone_op.SetChoices(list(PlotOne_Choices_nonxas.keys()))
            self.plotsel_op.SetChoices(list(PlotSel_Choices_nonxas.keys()))
            self.plotone_op.SetStringSelection('Raw Data')
            self.plotsel_op.SetStringSelection('Raw Data')
            for k in widlist:
                k.Disable()

        self.skip_process = False
        self.process(dgroup)

    def read_form(self):
        "read for, returning dict of values"
        form_opts = {}
        form_opts['e0'] = self.xas_e0.GetValue()
        form_opts['edge_step'] = self.xas_step.GetValue()
        form_opts['pre1'] = self.xas_pre1.GetValue()
        form_opts['pre2'] = self.xas_pre2.GetValue()
        form_opts['norm1'] = self.xas_nor1.GetValue()
        form_opts['norm2'] = self.xas_nor2.GetValue()
        form_opts['nnorm'] = int(self.xas_nnor.GetSelection())
        form_opts['nvict'] = int(self.xas_vict.GetSelection())

        form_opts['plotone_op'] = self.plotone_op.GetStringSelection()
        form_opts['plotsel_op'] = self.plotsel_op.GetStringSelection()

        form_opts['show_e0'] = self.xas_showe0.IsChecked()
        form_opts['auto_e0'] = self.xas_autoe0.IsChecked()
        form_opts['auto_step'] = self.xas_autostep.IsChecked()

        form_opts['deconv_form'] = self.deconv_form.GetStringSelection()
        form_opts['deconv_ewid'] = self.deconv_ewid.GetValue()
        return form_opts

    def onPlotOne(self, evt=None):
        self.plot(self.controller.get_group())

    def onPlotSel(self, evt=None):
        newplot = True
        group_ids = self.controller.filelist.GetCheckedStrings()
        if len(group_ids) < 1:
            return
        last_id = group_ids[-1]

        yarray_name  = PlotSel_Choices[self.plotsel_op.GetStringSelection()]
        ylabel = PlotLabels[yarray_name]

        # print("Plot Sel:: ", group_ids)
        for checked in group_ids:
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            plot_yarrays = [(yarray_name, PLOTOPTS_1, dgroup.filename)]
            dgroup.plot_ylabel = ylabel
            if dgroup is not None:
                dgroup.plot_extras = []
                # print(" PlotSel -> plot ", checked, (last_id!=checked) )
                self.plot(dgroup, title='', new=newplot,
                          plot_yarrays=plot_yarrays,
                          show_legend=True, with_extras=False,
                          delay_draw=(last_id!=checked))
                newplot=False
        self.controller.get_display(stacked=False).panel.canvas.draw()

    def onSaveConfigBtn(self, evt=None):
        conf = self.controller.larch.symtable._sys.xas_viewer
        opts = {}
        opts.update(getattr(conf, 'xas_norm', {}))
        opts.update(self.read_form())
        conf.xas_norm = opts

    def onCopyParam(self, name=None, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())
        opts = {}
        name = str(name)
        def copy_attrs(*args):
            for a in args:
                opts[a] = conf[a]

        if name == 'plotone_op':
            copy_attrs('plotone_op')
        elif name == 'xas_e0':
            copy_attrs('e0', 'show_e0')
            opts['auto_e0'] = False
        elif name == 'xas_step':
            copy_attrs('edge_step')
            opts['auto_step'] = False
        elif name == 'xas_pre':
            copy_attrs('pre1', 'pre2', 'nvict')
        elif name == 'xas_norm':
            copy_attrs('nnorm', 'norm1', 'norm2')
        elif name == 'deconv':
            copy_attrs('deconv_form', 'deconv_ewid')

        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group:
                grp.xasnorm_config.update(opts)
                self.fill_form(grp)
                self.process(grp)

    def onSet_XASE0(self, evt=None, value=None):
        self.xas_autoe0.SetValue(0)
        self.onReprocess()

    def onSet_XASStep(self, evt=None, value=None):
        self.xas_autostep.SetValue(0)
        self.onReprocess()

    def onReprocess(self, evt=None, value=None, **kws):
        if self.skip_process:
            return
        try:
            dgroup = self.controller.get_group()
        except TypeError:
            return
        self.process(dgroup)
        self.plot(dgroup)

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

    def process(self, dgroup, **kws):
        """ handle process (pre-edge/normalize, deconvolve) of XAS data from XAS form
        """
        if self.skip_process:
            return
        self.skip_process = True

        dgroup.custom_plotopts = {}
        # print("XAS norm process ", dgroup.datatype)

        if dgroup.datatype != 'xas':
            self.skip_process = False
            dgroup.mu = dgroup.ydat * 1.0
            return

        form = self.read_form()
        e0 = form['e0']
        edge_step = form['edge_step']

        form['group'] = dgroup.groupname

        copts = [dgroup.groupname]
        if not form['auto_e0']:
            if e0 < max(dgroup.energy) and e0 > min(dgroup.energy):
                copts.append("e0=%.4f" % float(e0))

        if not form['auto_step']:
            copts.append("step=%.4f" % float(edge_step))

        for attr in ('pre1', 'pre2', 'nvict', 'nnorm', 'norm1', 'norm2'):
            copts.append("%s=%.2f" % (attr, form[attr]))


        self.larch_eval("pre_edge(%s)" % (', '.join(copts)))

        if form['auto_e0']:
            self.xas_e0.SetValue(dgroup.e0, act=False)
        if form['auto_step']:
            self.xas_step.SetValue(dgroup.edge_step, act=False)

        self.xas_pre1.SetValue(dgroup.pre_edge_details.pre1)
        self.xas_pre2.SetValue(dgroup.pre_edge_details.pre2)
        self.xas_nor1.SetValue(dgroup.pre_edge_details.norm1)
        self.xas_nor2.SetValue(dgroup.pre_edge_details.norm2)

        # deconvolution
        deconv_form = form['deconv_form'].lower()
        deconv_ewid = float(form['deconv_ewid'])
        if not deconv_form.startswith('none') and deconv_ewid > 1.e-3:
            dopts = [dgroup.groupname,
                     "form='%s'" % (deconv_form),
                     "esigma=%.4f" % (deconv_ewid)]
            self.larch_eval("xas_deconvolve(%s)" % (', '.join(dopts)))


        for attr in ('e0', 'edge_step'):
            dgroup.xasnorm_config[attr] = getattr(dgroup, attr)

        for attr in ('pre1', 'pre2',  'nnorm', 'norm1', 'norm2'):
            dgroup.xasnorm_config[attr] = getattr(dgroup.pre_edge_details, attr)

        self.skip_process = False

    def get_plot_arrays(self, dgroup):
        form = self.read_form()

        lab = PlotLabels['norm']
        dgroup.plot_y2label = None
        dgroup.plot_xlabel = r'$E \,\mathrm{(eV)}$'
        dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab)]

        if dgroup.datatype != 'xas':
            pchoice  = PlotOne_Choices_nonxas[self.plotone_op.GetStringSelection()]
            dgroup.plot_xlabel = 'x'
            dgroup.plot_ylabel = 'y'
            dgroup.plot_yarrays = [('ydat', PLOTOPTS_1, 'ydat')]
            dgroup.dmude = np.gradient(dgroup.ydat)/np.gradient(dgroup.xdat)
            if pchoice  == 'dmude':
                dgroup.plot_ylabel = 'dy/dx'
                dgroup.plot_yarrays = [('dmude', PLOTOPTS_1, 'dy/dx')]
            elif pchoice == 'norm+deriv':
                lab = PlotLabels['norm']
                dgroup.plot_y2label = 'dy/dx'
                dgroup.plot_yarrays = [('ydat', PLOTOPTS_1, 'y'),
                                       ('dmude', PLOTOPTS_D, 'dy/dx')]
            return

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
            lab = lab1 + ' + ' + lab2

        dgroup.plot_ylabel = lab
        y4e0 = dgroup.ydat = getattr(dgroup, dgroup.plot_yarrays[0][0], dgroup.mu)
        dgroup.plot_extras = []
        if form['show_e0']:
            ie0 = index_of(dgroup.energy, dgroup.e0)
            dgroup.plot_extras.append(('marker', dgroup.e0, y4e0[ie0], {}))

    def plot(self, dgroup, title=None, plot_yarrays=None, delay_draw=False,
             new=True, zoom_out=True, with_extras=True, **kws):

        self.get_plot_arrays(dgroup)
        ppanel = self.controller.get_display(stacked=False).panel
        viewlims = ppanel.get_viewlimits()
        plotcmd = ppanel.oplot
        if new:
            plotcmd = ppanel.plot

        groupname = dgroup.groupname

        if not hasattr(dgroup, 'xdat'):
            print("Cannot plot group ", groupname)

        if ((getattr(dgroup, 'plot_yarrays', None) is None or
             getattr(dgroup, 'energy', None) is None or
             getattr(dgroup, 'mu', None) is None)):
            self.process(dgroup)

        if plot_yarrays is None and hasattr(dgroup, 'plot_yarrays'):
            plot_yarrays = dgroup.plot_yarrays

        popts = kws
        path, fname = os.path.split(dgroup.filename)
        if not 'label' in popts:
            popts['label'] = dgroup.plot_ylabel
        zoom_out = (zoom_out or
                  min(dgroup.xdat) >= viewlims[1] or
                  max(dgroup.xdat) <= viewlims[0] or
                  min(dgroup.ydat) >= viewlims[3] or
                  max(dgroup.ydat) <= viewlims[2])

        if not zoom_out:
            popts['xmin'] = viewlims[0]
            popts['xmax'] = viewlims[1]
            popts['ymin'] = viewlims[2]
            popts['ymax'] = viewlims[3]

        popts['xlabel'] = dgroup.plot_xlabel
        popts['ylabel'] = dgroup.plot_ylabel
        if getattr(dgroup, 'plot_y2label', None) is not None:
            popts['y2label'] = dgroup.plot_y2label

        plot_extras = None
        if new:
            if title is None:
                title = fname
            plot_extras = getattr(dgroup, 'plot_extras', None)

        popts['title'] = title
        popts['delay_draw'] = delay_draw
        if hasattr(dgroup, 'custom_plotopts'):
            popts.update(dgroup.custom_plotopts)

        narr = len(plot_yarrays) - 1
        for i, pydat in enumerate(plot_yarrays):
            yaname, yopts, yalabel = pydat
            popts.update(yopts)
            if yalabel is not None:
                popts['label'] = yalabel

            popts['delay_draw'] = delay_draw or (i != narr)
            # print("plot:: ", i, popts['delay_draw'], plotcmd)
            # print(popts)
            plotcmd(dgroup.xdat, getattr(dgroup, yaname), **popts)
            plotcmd = ppanel.oplot

        if with_extras and plot_extras is not None:
            axes = ppanel.axes
            for etype, x, y, opts in plot_extras:
                if etype == 'marker':
                    xpopts = {'marker': 'o', 'markersize': 4,
                              'label': '_nolegend_',
                              'markerfacecolor': 'red',
                              'markeredgecolor': '#884444'}
                    xpopts.update(opts)
                    axes.plot([x], [y], **xpopts)
                elif etype == 'vline':
                    xpopts = {'ymin': 0, 'ymax': 1.0,
                              'label': '_nolegend_',
                              'color': '#888888'}
                    xpopts.update(opts)
                    axes.axvline(x, **xpopts)
        if not popts['delay_draw']:
            ppanel.canvas.draw()
