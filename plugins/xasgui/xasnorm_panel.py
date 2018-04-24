#!/usr/bin/env python
"""
XANES Normalization panel
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
from larch.wxlib import BitmapButton, FloatCtrl, FloatSpin
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

PlotOne_Choices = OrderedDict(((u'Raw \u03BC(E)', 'mu'),
                               (u'Normalized \u03BC(E)', 'norm'),
                               (u'd\u03BC(E)/dE', 'dmude'),
                               (u'Normalized \u03BC(E) + d\u03BC(E)/dE', 'norm+deriv'),
                               (u'Flattened \u03BC(E)', 'flat'),
                               (u'\u03BC(E) + Pre-/Post-edge', 'prelines')))

PlotSel_Choices = OrderedDict(((u'Raw \u03BC(E)', 'mu'),
                               (u'Normalized \u03BC(E)', 'norm'),
                               (u'Flattened \u03BC(E)', 'flat'),
                               (u'd\u03BC(E)/dE (normalized)', 'dnormde')))

PlotOne_Choices_nonxas = OrderedDict((('Raw Data', 'mu'),
                                      ('Derivative', 'dmude'),
                                      ('Data + Derivative', 'norm+deriv')))

PlotSel_Choices_nonxas = OrderedDict((('Raw Data', 'mu'),
                                      ('Derivative', 'dmude')))


def default_xasnorm_config():
    return dict(e0=0, edge_step=None, pre1=-200, pre2=-25, nnorm=2, norm1=25,
                norm2=-10, nvict=1, auto_step=True, auto_e0=True, show_e0=True,
                plotone_op='Normalized \u03BC(E)',
                plotsel_op='Normalized \u03BC(E)')


class XASNormPanel(TaskPanel):
    """XAS normalization Panel"""
    def __init__(self, parent, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='xasnorm_config', **kws)

    def build_display(self):
        titleopts = dict(font=Font(12), colour='#AA0000')

        xas = self.panel
        self.wids = {}

        self.plotone_op = Choice(xas, choices=list(PlotOne_Choices.keys()),
                                 action=self.onPlotOne, size=(175, -1))
        self.plotsel_op = Choice(xas, choices=list(PlotSel_Choices.keys()),
                                 action=self.onPlotSel, size=(175, -1))

        self.plotone_op.SetSelection(1)
        self.plotsel_op.SetSelection(1)

        plot_one = Button(xas, 'Plot This Group', size=(150, -1),
                          action=self.onPlotOne)

        plot_sel = Button(xas, 'Plot Selected Groups', size=(150, -1),
                          action=self.onPlotSel)


        def FloatSpinWithPin(name, value, **kws):
            s = wx.BoxSizer(wx.HORIZONTAL)
            self.wids[name] = FloatSpin(xas, value=value, **kws)
            bb = BitmapButton(xas, get_icon('pin'), size=(25, 25),
                              action=partial(self.onSelPoint, opt=name),
                              tooltip='use last point selected from plot')
            s.Add(self.wids[name])
            s.Add(bb)
            return s

        opts = dict(action=self.onReprocess)

        e0opts_panel = wx.Panel(xas)
        self.wids['autoe0'] = Check(e0opts_panel, default=True, label='auto?', **opts)
        self.wids['showe0'] = Check(e0opts_panel, default=True, label='show?', **opts)
        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(self.wids['autoe0'], 0, LCEN, 4)
        sx.Add(self.wids['showe0'], 0, LCEN, 4)
        pack(e0opts_panel, sx)

        self.wids['autostep'] = Check(xas, default=True, label='auto?', **opts)


        opts['size'] = (50, -1)
        self.wids['vict'] = Choice(xas, choices=('0', '1', '2', '3'), **opts)
        self.wids['nnor'] = Choice(xas, choices=('0', '1', '2', '3'), **opts)
        self.wids['vict'].SetSelection(1)
        self.wids['nnor'].SetSelection(1)

        opts.update({'size': (100, -1), 'digits': 2, 'increment': 5.0})

        xas_pre1 = FloatSpinWithPin('pre1', value=-1000, **opts)
        xas_pre2 = FloatSpinWithPin('pre2', value=-30, **opts)
        xas_nor1 = FloatSpinWithPin('nor1', value=50, **opts)
        xas_nor2 = FloatSpinWithPin('nor2', value=5000, **opts)

        opts = {'digits': 2, 'increment': 0.1, 'value': 0}
        xas_e0   = FloatSpinWithPin('e0', action=self.onSet_XASE0, **opts)
        self.wids['step'] = FloatSpin(xas, action=self.onSet_XASStep, **opts)

        saveconf = Button(xas, 'Save as Default Settings', size=(200, -1),
                          action=self.onSaveConfigBtn)

        def CopyBtn(name):
            return Button(xas, 'Copy', size=(50, -1),
                          action=partial(self.onCopyParam, name))

        def add_text(text, dcol=1, newrow=True):
            xas.Add(SimpleText(xas, text), dcol=dcol, newrow=newrow)



        xas.Add(SimpleText(xas, ' XAS Pre-edge subtraction and Normalization',
                           **titleopts), dcol=4)
        xas.Add(SimpleText(xas, 'Copy to Selected Groups?'), style=RCEN, dcol=3)

        xas.Add(plot_sel, newrow=True)
        xas.Add(self.plotsel_op, dcol=6)

        xas.Add(plot_one, newrow=True)
        xas.Add(self.plotone_op, dcol=4)
        xas.Add((10, 10))
        xas.Add(CopyBtn('plotone_op'), style=RCEN)

        add_text('E0 : ')
        xas.Add(xas_e0)
        xas.Add(e0opts_panel, dcol=3)
        xas.Add((10, 1))
        xas.Add(CopyBtn('xas_e0'), style=RCEN)

        add_text('Edge Step: ')
        xas.Add(self.wids['step'])
        xas.Add(self.wids['autostep'], dcol=3)
        xas.Add((10, 1))
        xas.Add(CopyBtn('xas_step'), style=RCEN)

        add_text('Pre-edge range: ')
        xas.Add(xas_pre1)
        add_text(' : ', newrow=False)
        xas.Add(xas_pre2)
        xas.Add(SimpleText(xas, 'Victoreen:'))
        xas.Add(self.wids['vict'])
        xas.Add(CopyBtn('xas_pre'), style=RCEN)

        add_text('Normalization range: ')
        xas.Add(xas_nor1)
        add_text(' : ', newrow=False)
        xas.Add(xas_nor2)
        xas.Add(SimpleText(xas, 'Poly Order:'))
        xas.Add(self.wids['nnor'])
        xas.Add(CopyBtn('xas_norm'), style=RCEN)

        xas.Add(saveconf, dcol=6, newrow=True)
        xas.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((5, 5), 0, LCEN, 3)
        sizer.Add(HLine(self, size=(550, 2)), 0, LCEN, 3)
        sizer.Add(xas, 0, LCEN, 3)
        sizer.Add((5, 5), 0, LCEN, 3)
        sizer.Add(HLine(self, size=(550, 2)), 0, LCEN, 3)
        pack(self, sizer)


    def customize_config(self, config, dgroup=None):
        if config is None:
            config = {}
        if 'e0' not in config:
            config.update(default_xasnorm_config())
        if dgroup is not None:
            dgroup.xasnorm_config = config
        return config

    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)
        self.skip_process = True


        if dgroup.datatype == 'xas':
            for k in self.wids.values():
                k.Enable()

            self.plotone_op.SetChoices(list(PlotOne_Choices.keys()))
            self.plotsel_op.SetChoices(list(PlotSel_Choices.keys()))

            self.plotone_op.SetStringSelection(opts['plotone_op'])
            self.plotsel_op.SetStringSelection(opts['plotsel_op'])
            self.wids['e0'].SetValue(opts['e0'])
            edge_step = opts.get('edge_step', None)
            if edge_step is None:
                edge_step = 1.0

            ndigits = int(2 - round(np.log10(abs(edge_step))))
            self.wids['step'].SetDigits(ndigits+1)
            self.wids['step'].SetIncrement(0.2*10**(-ndigits))
            self.wids['step'].SetValue(edge_step)

            self.wids['pre1'].SetValue(opts['pre1'])
            self.wids['pre2'].SetValue(opts['pre2'])
            self.wids['nor1'].SetValue(opts['norm1'])
            self.wids['nor2'].SetValue(opts['norm2'])
            self.wids['vict'].SetSelection(opts['nvict'])
            self.wids['nnor'].SetSelection(opts['nnorm'])
            self.wids['showe0'].SetValue(opts['show_e0'])
            self.wids['autoe0'].SetValue(opts['auto_e0'])
            self.wids['autostep'].SetValue(opts['auto_step'])
        else:
            self.plotone_op.SetChoices(list(PlotOne_Choices_nonxas.keys()))
            self.plotsel_op.SetChoices(list(PlotSel_Choices_nonxas.keys()))
            self.plotone_op.SetStringSelection('Raw Data')
            self.plotsel_op.SetStringSelection('Raw Data')
            for k in self.wids.values():
                k.Disable()

        self.skip_process = False
        self.process(dgroup=dgroup)

    def read_form(self):
        "read form, return dict of values"
        form_opts = {}
        form_opts['e0'] = self.wids['e0'].GetValue()
        form_opts['edge_step'] = self.wids['step'].GetValue()
        form_opts['pre1'] = self.wids['pre1'].GetValue()
        form_opts['pre2'] = self.wids['pre2'].GetValue()
        form_opts['norm1'] = self.wids['nor1'].GetValue()
        form_opts['norm2'] = self.wids['nor2'].GetValue()
        form_opts['nnorm'] = int(self.wids['nnor'].GetSelection())
        form_opts['nvict'] = int(self.wids['vict'].GetSelection())

        form_opts['plotone_op'] = self.plotone_op.GetStringSelection()
        form_opts['plotsel_op'] = self.plotsel_op.GetStringSelection()

        form_opts['show_e0'] = self.wids['showe0'].IsChecked()
        form_opts['auto_e0'] = self.wids['autoe0'].IsChecked()
        form_opts['auto_step'] = self.wids['autostep'].IsChecked()

        return form_opts

    def onPlotOne(self, evt=None):
        self.plot(self.controller.get_group())

    def onPlotSel(self, evt=None):
        newplot = True
        group_ids = self.controller.filelist.GetCheckedStrings()
        if len(group_ids) < 1:
            return
        last_id = group_ids[-1]

        yarray_name = PlotSel_Choices[self.plotsel_op.GetStringSelection()]
        ylabel = getattr(plotlabels, yarray_name)

        for checked in group_ids:
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            plot_yarrays = [(yarray_name, PLOTOPTS_1, dgroup.filename)]
            if dgroup is not None:
                dgroup.plot_extras = []
                self.plot(dgroup, title='', new=newplot, multi=True,
                          plot_yarrays=plot_yarrays, show_legend=True,
                          with_extras=False,  delay_draw=(last_id != checked))
                newplot = False
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

        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group:
                grp.xasnorm_config.update(opts)
                self.fill_form(grp)
                self.process(dgroup=grp)

    def onSet_XASE0(self, evt=None, value=None):
        "handle setting e0"
        self.wids['autoe0'].SetValue(0)
        self.onReprocess()

    def onSet_XASStep(self, evt=None, value=None):
        "handle setting edge step"
        self.wids['autostep'].SetValue(0)
        self.onReprocess()

    def onReprocess(self, evt=None, value=None, **kws):
        "handle request reprocess"
        if self.skip_process:
            return
        try:
            dgroup = self.controller.get_group()
        except TypeError:
            return
        self.process(dgroup=dgroup)
        self.plot(dgroup)

    def onSelPoint(self, evt=None, opt='e0'):
        "on point selected by cursor"
        xval, _ = self.controller.get_cursor()
        if xval is None:
            return

        e0 = self.wids['e0'].GetValue()
        if opt == 'e0':
            self.wids['e0'].SetValue(xval)
            self.wids['autoe0'].SetValue(0)
        elif opt in ('pre1', 'pre2', 'nor1', 'nor2'):
            self.wids[opt].SetValue(xval-e0)
        else:
            print(" unknown selection point ", opt)

    def make_dnormde(self, dgroup):
        form = dict(group=dgroup.groupname)
        self.larch_eval("{group:s}.dnormde={group:s}.dmude/{group:s}.edge_step".format(**form))

    def process(self, dgroup=None, **kws):
        """ handle process (pre-edge/normalize) of XAS data from XAS form
        """
        if self.skip_process:
            return

        if dgroup is None:
            dgroup = self.controller.get_group()

        self.skip_process = True

        if not hasattr(dgroup, 'xasnorm_config'):
            dgroup.xasnorm_config = default_xasnorm_config()

        dgroup.custom_plotopts = {}
        # print("XAS norm process ", dgroup.datatype)

        if dgroup.datatype != 'xas':
            self.skip_process = False
            dgroup.mu = dgroup.ydat * 1.0
            return

        en_units = getattr(dgroup, 'energy_units', None)
        if en_units is None:
            en_units = 'eV'
            units = guess_energy_units(dgroup.energy)

            if units != 'eV':
                dlg = EnergyUnitsDialog(self.parent, units, dgroup.energy)
                res = dlg.GetResponse()
                dlg.Destroy()
                if res.ok:
                    en_units = res.units
                    dgroup.xdat = dgroup.energy = res.energy
            dgroup.energy_units = en_units

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
        self.make_dnormde(dgroup)

        if form['auto_e0']:
            self.wids['e0'].SetValue(dgroup.e0) # , act=False)
        if form['auto_step']:
            self.wids['step'].SetValue(dgroup.edge_step) # , act=False)

        self.wids['pre1'].SetValue(dgroup.pre_edge_details.pre1)
        self.wids['pre2'].SetValue(dgroup.pre_edge_details.pre2)
        self.wids['nor1'].SetValue(dgroup.pre_edge_details.norm1)
        self.wids['nor2'].SetValue(dgroup.pre_edge_details.norm2)

        for attr in ('e0', 'edge_step'):
            dgroup.xasnorm_config[attr] = getattr(dgroup, attr)

        for attr in ('pre1', 'pre2', 'nnorm', 'norm1', 'norm2'):
            dgroup.xasnorm_config[attr] = getattr(dgroup.pre_edge_details, attr)

        self.skip_process = False

    def get_plot_arrays(self, dgroup):
        form = self.read_form()

        lab = plotlabels.norm
        dgroup.plot_y2label = None
        dgroup.plot_xlabel = plotlabels.energy
        dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab)]

        if dgroup.datatype != 'xas':
            pchoice = PlotOne_Choices_nonxas[self.plotone_op.GetStringSelection()]
            dgroup.plot_xlabel = 'x'
            dgroup.plot_ylabel = 'y'
            dgroup.plot_yarrays = [('ydat', PLOTOPTS_1, 'ydat')]
            dgroup.dmude = np.gradient(dgroup.ydat)/np.gradient(dgroup.xdat)
            if pchoice == 'dmude':
                dgroup.plot_ylabel = 'dy/dx'
                dgroup.plot_yarrays = [('dmude', PLOTOPTS_1, 'dy/dx')]
            elif pchoice == 'norm+deriv':
                lab = plotlabels.norm
                dgroup.plot_y2label = 'dy/dx'
                dgroup.plot_yarrays = [('ydat', PLOTOPTS_1, 'y'),
                                       ('dmude', PLOTOPTS_D, 'dy/dx')]
            return

        pchoice = PlotOne_Choices[self.plotone_op.GetStringSelection()]
        if pchoice in ('mu', 'norm', 'flat', 'dmude'):
            lab = getattr(plotlabels, pchoice)
            dgroup.plot_yarrays = [(pchoice, PLOTOPTS_1, lab)]

        elif pchoice == 'prelines':
            dgroup.plot_yarrays = [('mu', PLOTOPTS_1, plotlabels.mu),
                                   ('pre_edge', PLOTOPTS_2, 'pre edge'),
                                   ('post_edge', PLOTOPTS_2, 'post edge')]
        elif pchoice == 'preedge':
            dgroup.pre_edge_sub = dgroup.norm * dgroup.edge_step
            dgroup.plot_yarrays = [('pre_edge_sub', PLOTOPTS_1,
                                    r'pre-edge subtracted $\mu$')]
            lab = r'pre-edge subtracted $\mu$'

        elif pchoice == 'norm+deriv':
            lab = plotlabels.norm
            lab2 = plotlabels.dmude
            dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab),
                                   ('dmude', PLOTOPTS_D, lab2)]
            dgroup.plot_y2label = lab2


        dgroup.plot_ylabel = lab
        y4e0 = dgroup.ydat = getattr(dgroup, dgroup.plot_yarrays[0][0], dgroup.mu)
        dgroup.plot_extras = []
        if form['show_e0']:
            ie0 = index_of(dgroup.energy, dgroup.e0)
            dgroup.plot_extras.append(('marker', dgroup.e0, y4e0[ie0], {}))

    def plot(self, dgroup, title=None, plot_yarrays=None, delay_draw=False,
             multi=False, new=True, zoom_out=True, with_extras=True, **kws):

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
            self.process(dgroup=dgroup)

        if plot_yarrays is None and hasattr(dgroup, 'plot_yarrays'):
            plot_yarrays = dgroup.plot_yarrays

        popts = kws
        path, fname = os.path.split(dgroup.filename)
        if 'label' not in popts:
            popts['label'] = dgroup.plot_ylabel


        zoom_out = (zoom_out or min(dgroup.xdat) >= viewlims[1] or
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

        if multi:
            yarray_name = PlotSel_Choices[self.plotsel_op.GetStringSelection()]
            popts['ylabel'] = getattr(plotlabels, yarray_name)

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
            # print("plot:: ", i, popts['delay_draw'], plotcmd, popts)
            if yaname == 'dnormde' and not hasattr(dgroup, yaname):
                self.make_dnormde(dgroup)

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
