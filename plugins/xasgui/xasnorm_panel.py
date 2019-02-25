#!/usr/bin/env python
"""
XANES Normalization panel
"""
import os
import time
import wx
import six
import numpy as np

from functools import partial
from collections import OrderedDict
from lmfit.printfuncs import gformat
from larch.utils import index_of

from larch.wxlib import (BitmapButton, FloatCtrl, FloatSpin, get_icon,
                         SimpleText, pack, Button, HLine, Choice, Check,
                         GridPanel, CEN, RCEN, LCEN, Font)

from larch_plugins.wx.plotter import last_cursor_pos
from larch_plugins.xasgui.xas_dialogs import EnergyUnitsDialog
from larch_plugins.xasgui.taskpanel import TaskPanel

from larch_plugins.xafs.xafsutils import guess_energy_units
from larch_plugins.xafs.xafsplots import plotlabels
from larch_plugins.xray import guess_edge, atomic_number
np.seterr(all='ignore')

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, zorder=3,
                  marker='None', markersize=4)
PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)

PlotOne_Choices = OrderedDict(((six.u('Raw \u03BC(E)'), 'mu'),
                               (six.u('Normalized \u03BC(E)'), 'norm'),
                               (six.u('d\u03BC(E)/dE'), 'dmude'),
                               (six.u('Raw \u03BC(E) + d\u03BC(E)/dE'), 'mu+dmude'),
                               (six.u('Normalized \u03BC(E) + d\u03BC(E)/dE'), 'norm+dnormde'),
                               (six.u('Flattened \u03BC(E)'), 'flat'),
                               (six.u('\u03BC(E) + Pre-/Post-edge'), 'prelines'),
                               (six.u('\u03BC(E) + MBACK tabulated \u03BC(E)'), 'mback_norm'),
                               (six.u('MBACK v. Poly Normalized \u03BC(E)'), 'mback_poly'),
                              ))

PlotSel_Choices = OrderedDict(((six.u('Raw \u03BC(E)'), 'mu'),
                               (six.u('Normalized \u03BC(E)'), 'norm'),
                               (six.u('Flattened \u03BC(E)'), 'flat'),
                               (six.u('d\u03BC(E)/dE (raw)'), 'dmude'),
                               (six.u('d\u03BC(E)/dE (normalized)'), 'dnormde')))

PlotOne_Choices_nonxas = OrderedDict((('Raw Data', 'mu'),
                                      ('Derivative', 'dmude'),
                                      ('Data + Derivative', 'norm+dmude')))

PlotSel_Choices_nonxas = OrderedDict((('Raw Data', 'mu'),
                                      ('Derivative', 'dmude')))

defaults = dict(e0=0, edge_step=None, auto_step=True, auto_e0=True,
                show_e0=True, pre1=-200, pre2=-30, norm1=100, norm2=-10,
                norm_method='polynomial', mback_edge='K', mback_elem='H',
                nvict=1, nnorm=1,
                plotone_op='Normalized \u03BC(E)',
                plotsel_op='Normalized \u03BC(E)')

class XASNormPanel(TaskPanel):
    """XAS normalization Panel"""
    def __init__(self, parent, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='xasnorm_config',
                           config=defaults, **kws)

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

        opts = dict(action=self.onReprocess)

        e0opts_panel = wx.Panel(xas)
        self.wids['autoe0'] = Check(e0opts_panel, default=True, label='auto?', **opts)
        self.wids['showe0'] = Check(e0opts_panel, default=True, label='show?', **opts)
        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(self.wids['autoe0'], 0, LCEN, 4)
        sx.Add(self.wids['showe0'], 0, LCEN, 4)
        pack(e0opts_panel, sx)

        self.wids['autostep'] = Check(xas, default=True, label='auto?', **opts)


        opts['size'] = (60, -1)
        self.wids['vict'] = Choice(xas, choices=('0', '1', '2', '3'), **opts)
        self.wids['nnor'] = Choice(xas, choices=('0', '1', '2', '3'), **opts)
        self.wids['vict'].SetSelection(1)
        self.wids['nnor'].SetSelection(1)

        opts.update({'size': (100, -1), 'digits': 2, 'increment': 5.0,
                     'action': self.onSet_Ranges})

        xas_pre1 = self.add_floatspin('pre1', value=defaults['pre1'], **opts)
        xas_pre2 = self.add_floatspin('pre2', value=defaults['pre2'], **opts)
        xas_nor1 = self.add_floatspin('nor1', value=defaults['norm1'], **opts)
        xas_nor2 = self.add_floatspin('nor2', value=defaults['norm2'], **opts)

        opts = {'digits': 3, 'increment': 0.1, 'value': 0}
        xas_e0   = self.add_floatspin('e0', action=self.onSet_XASE0, **opts)
        xas_step = self.add_floatspin('step', action=self.onSet_XASStep,
                                      with_pin=False, **opts)

        self.wids['norm_method'] = Choice(xas, choices=('polynomial', 'mback'),
                                          size=(120, -1), action=self.onNormMethod)
        self.wids['norm_method'].SetSelection(0)
        atsyms = self.larch.symtable._xray._xraydb.atomic_symbols
        mback_edges = ('K', 'L3', 'L2', 'L1', 'M5')

        self.wids['mback_elem'] = Choice(xas, choices=atsyms, size=(75, -1))
        self.wids['mback_edge'] = Choice(xas, choices=mback_edges, size=(60, -1))

        saveconf = Button(xas, 'Save as Default Settings', size=(200, -1),
                          action=self.onSaveConfigBtn)

        def CopyBtn(name):
            return Button(xas, 'Copy', size=(50, -1),
                          action=partial(self.onCopyParam, name))

        add_text = self.add_text

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
        xas.Add(xas_step)
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
        xas.Add(CopyBtn('xas_normpoly'), style=RCEN)

        add_text('Normalization method: ')
        xas.Add(self.wids['norm_method'], dcol=5)
        xas.Add(CopyBtn('norm_method'))

        add_text('    mback options: ')
        add_text('      Element : ', newrow=False, dcol=2)
        xas.Add(self.wids['mback_elem'])
        add_text(' Edge : ', newrow=False)
        xas.Add(self.wids['mback_edge'])
        xas.Add(CopyBtn('xas_mback'), style=RCEN)

        xas.Add(saveconf, dcol=6, newrow=True)
        xas.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((10, 10), 0, LCEN, 3)
        sizer.Add(xas, 0, LCEN, 3)
        sizer.Add((10, 10), 0, LCEN, 3)
        sizer.Add(HLine(self, size=(600, 2)), 0, LCEN, 3)
        pack(self, sizer)

    def get_config(self, dgroup=None):
        """custom get_config to possibly inherit from Athena settings"""
        if dgroup is None:
            dgroup = self.controller.get_group()
        if dgroup is None:
            return self.get_defaultconfig()

        if hasattr(dgroup, self.configname):
            conf = getattr(dgroup, self.configname)
        else:
            conf = self.get_defaultconfig()
            if hasattr(dgroup, 'bkg_params'): # from Athena
                conf['e0']   = getattr(dgroup.bkg_params, 'e0', conf['e0'])
                conf['pre1'] = getattr(dgroup.bkg_params, 'pre1', conf['pre1'])
                conf['pre2'] = getattr(dgroup.bkg_params, 'pre2', conf['pre2'])
                conf['norm1'] = getattr(dgroup.bkg_params, 'nor1', conf['norm1'])
                conf['norm2'] = getattr(dgroup.bkg_params, 'nor2', conf['norm2'])
                conf['nnorm'] = getattr(dgroup.bkg_params, 'nnor', conf['nnorm'])
                conf['nvict'] = getattr(dgroup.bkg_params, 'nvic', conf['nvict'])
                conf['autostep'] = (float(getattr(dgroup.bkg_params, 'fixstep', 0.0))< 0.5)
            if hasattr(dgroup, 'mback_params'): # from mback
                conf['mback_elem'] = getattr(dgroup.mback_params, 'atsym', conf['mback_elem'])
                conf['mback_edge'] = getattr(dgroup.mback_params, 'edge', conf['mback_edge'])

        setattr(dgroup, self.configname, conf)
        return conf

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
            self.wids['step'].SetIncrement(2.0*10**(-ndigits))
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
            self.wids['mback_edge'].SetStringSelection(opts['mback_edge'].title())
            self.wids['mback_elem'].SetStringSelection(opts['mback_elem'].title())
            self.wids['norm_method'].SetStringSelection(opts['norm_method'].lower())

        else:
            self.plotone_op.SetChoices(list(PlotOne_Choices_nonxas.keys()))
            self.plotsel_op.SetChoices(list(PlotSel_Choices_nonxas.keys()))
            self.plotone_op.SetStringSelection('Raw Data')
            self.plotsel_op.SetStringSelection('Raw Data')
            for k in self.wids.values():
                k.Disable()

        wx.CallAfter(self.unset_skip_process)

    def unset_skip_process(self):
        self.skip_process = False

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

        form_opts['norm_method'] = self.wids['norm_method'].GetStringSelection().lower()
        form_opts['mback_edge'] = self.wids['mback_edge'].GetStringSelection().title()
        form_opts['mback_elem'] = self.wids['mback_elem'].GetStringSelection().title()

        return form_opts

    def onNormMethod(self, evt=None):
        method = self.wids['norm_method'].GetStringSelection().lower()
        if method.startswith('mback'):
            dgroup = self.controller.get_group()
            cur_elem = self.wids['mback_elem'].GetStringSelection()
            if hasattr(dgroup, 'e0') and cur_elem == 'H':
                atsym, edge = guess_edge(dgroup.e0, _larch=self.larch)
                self.wids['mback_edge'].SetStringSelection(edge)
                self.wids['mback_elem'].SetStringSelection(atsym)

        self.onReprocess()

    def onPlotOne(self, evt=None):
        self.plot(self.controller.get_group())

    def onPlotSel(self, evt=None):
        newplot = True
        group_ids = self.controller.filelist.GetCheckedStrings()
        if len(group_ids) < 1:
            return
        last_id = group_ids[-1]

        groupname = self.controller.file_groups[str(last_id)]
        dgroup = self.controller.get_group(groupname)

        plot_choices = PlotSel_Choices
        if dgroup.datatype != 'xas':
            plot_choices = PlotSel_Choices_nonxas

        ytitle = self.plotsel_op.GetStringSelection()
        yarray_name = plot_choices[ytitle]
        ylabel = getattr(plotlabels, yarray_name, ytitle)

        for checked in group_ids:
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            plot_yarrays = [(yarray_name, PLOTOPTS_1, dgroup.filename)]
            if dgroup is not None:
                dgroup.plot_extras = []
                self.plot(dgroup, title='', new=newplot, multi=True,
                          plot_yarrays=plot_yarrays,
                          with_extras=False,  delay_draw=True)
                newplot = False
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.conf.show_legend=True
        ppanel.conf.draw_legend()

    def onSaveConfigBtn(self, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())
        self.set_defaultconfig(conf)

    def onCopyParam(self, name=None, evt=None):
        conf = self.get_config()
        form = self.read_form()
        conf.update(form)
        dgroup = self.controller.get_group()
        self.update_config(conf)
        self.fill_form(dgroup)
        opts = {}
        name = str(name)
        def copy_attrs(*args):
            for a in args:
                opts[a] = conf[a]
        if name == 'plotone_op':
            copy_attrs('plotone_op')
        elif name == 'xas_e0':
            copy_attrs('e0', 'show_e0', 'auto_e0')
        elif name == 'xas_step':
            copy_attrs('edge_step', 'auto_step')
        elif name == 'xas_pre':
            copy_attrs('pre1', 'pre2', 'nvict')
        elif name == 'xas_normpoly':
            copy_attrs('nnorm', 'norm1', 'norm2')
        elif name == 'xas_mback':
            copy_attrs('mback_elem', 'mback_edge')
        elif name == 'norm_method':
            copy_attrs('norm_method')

        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group:
                self.update_config(opts, dgroup=grp)
                self.fill_form(grp)
                self.process(grp, noskip=True)

    def onSet_XASE0(self, evt=None, value=None):
        "handle setting e0"
        self.wids['autoe0'].SetValue(0)
        self.update_config({'e0': self.wids['e0'].GetValue(),
                           'auto_e0': False})

        self.onReprocess()

    def onSet_XASStep(self, evt=None, value=None):
        "handle setting edge step"
        self.wids['autostep'].SetValue(0)
        self.update_config({'edge_step': self.wids['step'].GetValue(),
                            'auto_step': False})
        self.onReprocess()

    def onSet_Ranges(self, evt=None, **kws):
        conf = {}
        for attr in ('pre1', 'pre2', 'nor1', 'nor2'):
            conf[attr] = self.wids[attr].GetValue()
        self.update_config(conf)
        self.onReprocess()

    def onSelPoint(self, evt=None, opt='__', relative_e0=True, win=None):
        """
        get last selected point from a specified plot window
        and fill in the value for the widget defined by `opt`.

        by default it finds the latest cursor position from the
        cursor history of the first 20 plot windows.
        """
        if opt not in self.wids:
            return None

        _x, _y = last_cursor_pos(win=win, _larch=self.larch)
        if _x is None:
            return

        e0 = self.wids['e0'].GetValue()
        if opt == 'e0':
            self.wids['e0'].SetValue(_x)
            self.wids['autoe0'].SetValue(0)
        elif opt in ('pre1', 'pre2', 'nor1', 'nor2'):
            self.wids[opt].SetValue(_x-e0)
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

    def make_dnormde(self, dgroup):
        form = dict(group=dgroup.groupname)
        self.larch_eval("{group:s}.dnormde={group:s}.dmude/{group:s}.edge_step".format(**form))

    def process(self, dgroup=None, force_mback=False, noskip=False, **kws):
        """ handle process (pre-edge/normalize) of XAS data from XAS form
        """
        if self.skip_process and not noskip:
            return
        if dgroup is None:
            dgroup = self.controller.get_group()
        if dgroup is None:
            return

        self.skip_process = True
        self.get_config(dgroup)
        dgroup.custom_plotopts = {}

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
            copts.append("step=%s" % gformat(float(edge_step)))

        for attr in ('pre1', 'pre2', 'nvict', 'nnorm', 'norm1', 'norm2'):
            copts.append("%s=%.2f" % (attr, form[attr]))

        self.larch_eval("pre_edge(%s)" % (', '.join(copts)))

        self.larch_eval("{group:s}.norm_poly = 1.0*{group:s}.norm".format(**form))

        use_mback = form['norm_method'].lower().startswith('mback')
        form['normmeth'] = 'poly'
        if use_mback:
            form['normmeth'] = 'mback'

        if force_mback or use_mback:
            copts = [dgroup.groupname]
            copts.append("z=%d" % atomic_number(form['mback_elem']))
            copts.append("edge='%s'" % form['mback_edge'])
            for attr in ('pre1', 'pre2', 'nvict', 'nnorm', 'norm1', 'norm2'):
                copts.append("%s=%.2f" % (attr, form[attr]))

            self.larch_eval("mback_norm(%s)" % (', '.join(copts)))

            if form['auto_step']:
                norm_expr = """{group:s}.norm = 1.0*{group:s}.norm_{normmeth:s}
{group:s}.edge_step = 1.0*{group:s}.edge_step_{normmeth:s}"""
                self.larch_eval(norm_expr.format(**form))
            else:
                norm_expr = """{group:s}.norm = 1.0*{group:s}.norm_{normmeth:s}
{group:s}.norm *= {group:s}.edge_step_{normmeth:s}/{edge_step:.8f}"""
                self.larch_eval(norm_expr.format(**form))

        self.make_dnormde(dgroup)

        if form['auto_e0']:
            self.wids['e0'].SetValue(dgroup.e0)
        if form['auto_step']:
            self.wids['step'].SetValue(dgroup.edge_step)
            ndigits = int(2 - round(np.log10(abs(edge_step))))
            self.wids['step'].SetDigits(ndigits+1)
            self.wids['step'].SetIncrement(2.0*10**(-ndigits))


        self.wids['pre1'].SetValue(dgroup.pre_edge_details.pre1)
        self.wids['pre2'].SetValue(dgroup.pre_edge_details.pre2)
        self.wids['nor1'].SetValue(dgroup.pre_edge_details.norm1)
        self.wids['nor2'].SetValue(dgroup.pre_edge_details.norm2)

        conf = {}
        for attr in ('e0', 'edge_step'):
            conf[attr] = getattr(dgroup, attr)
        for attr in ('pre1', 'pre2', 'nnorm', 'norm1', 'norm2'):
            conf[attr] = getattr(dgroup.pre_edge_details, attr)

        if hasattr(dgroup, 'mback_params'): # from mback
            conf['mback_elem'] = getattr(dgroup.mback_params, 'atsym', 'H')
            conf['mback_edge'] = getattr(dgroup.mback_params, 'edge', 'K')
        else:
            conf['mback_elem'] = 'H'
            conf['mback_edge'] = 'K'
        self.update_config(conf, dgroup=dgroup)
        wx.CallAfter(self.unset_skip_process)

    def get_plot_arrays(self, dgroup):
        form = self.read_form()

        lab = plotlabels.norm
        if dgroup is None:
            return

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
            elif pchoice == 'norm+dnormde':
                lab = plotlabels.norm
                dgroup.plot_y2label = 'dy/dx'
                dgroup.plot_yarrays = [('ydat', PLOTOPTS_1, 'y'),
                                       ('dnormde', PLOTOPTS_D, 'dy/dx')]
            return

        req_attrs = ['e0', 'norm', 'dmude', 'pre_edge']

        pchoice = PlotOne_Choices[self.plotone_op.GetStringSelection()]
        if pchoice in ('mu', 'norm', 'flat', 'dmude'):
            lab = getattr(plotlabels, pchoice)
            dgroup.plot_yarrays = [(pchoice, PLOTOPTS_1, lab)]

        elif pchoice == 'prelines':
            dgroup.plot_yarrays = [('mu', PLOTOPTS_1, plotlabels.mu),
                                   ('pre_edge', PLOTOPTS_2, 'pre edge'),
                                   ('post_edge', PLOTOPTS_2, 'post edge')]
        elif pchoice == 'preedge':
            lab = r'pre-edge subtracted $\mu$'
            dgroup.pre_edge_sub = dgroup.norm * dgroup.edge_step
            dgroup.plot_yarrays = [('pre_edge_sub', PLOTOPTS_1, lab)]

        elif pchoice == 'mu+dmude':
            lab = plotlabels.mu
            lab2 = plotlabels.dmude
            dgroup.plot_yarrays = [('mu', PLOTOPTS_1, lab),
                                   ('dmude', PLOTOPTS_D, lab2)]
            dgroup.plot_y2label = lab2

        elif pchoice == 'norm+dnormde':
            lab = plotlabels.norm
            lab2 = plotlabels.dmude + ' (normalized)'
            dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab),
                                   ('dnormde', PLOTOPTS_D, lab2)]
            dgroup.plot_y2label = lab2

        elif pchoice == 'mback_norm':
            req_attrs.append('mback_norm')
            lab = r'$\mu$'
            if not hasattr(dgroup, 'mback_mu'):
                self.process(dgroup=dgroup)
            dgroup.plot_yarrays = [('mu', PLOTOPTS_1, lab),
                                   ('mback_mu', PLOTOPTS_2, r'tabulated $\mu(E)$')]

        elif pchoice == 'mback_poly':
            req_attrs.append('mback_norm')
            lab = plotlabels.norm
            if not hasattr(dgroup, 'mback_mu'):
                self.process(dgroup=dgroup)
            dgroup.plot_yarrays = [('norm_mback', PLOTOPTS_1, 'mback'),
                                   ('norm_poly', PLOTOPTS_2, 'polynomial')]

        dgroup.plot_ylabel = lab
        y4e0 = dgroup.ydat = getattr(dgroup, dgroup.plot_yarrays[0][0], dgroup.mu)
        dgroup.plot_extras = []

        needs_proc = False
        force_mback = False
        for attr in req_attrs:
            needs_proc = needs_proc or (not hasattr(dgroup, attr))
            force_mback = force_mback or attr.startswith('mback')

        if needs_proc:
            self.process(dgroup=dgroup, force_mback=force_mback, noskip=True)

        if form['show_e0']:
            ie0 = index_of(dgroup.energy, dgroup.e0)
            dgroup.plot_extras.append(('marker', dgroup.e0, y4e0[ie0], {}))

    def plot(self, dgroup, title=None, plot_yarrays=None, delay_draw=False,
             multi=False, new=True, zoom_out=True, with_extras=True, **kws):
        if self.skip_plotting:
            return
        self.get_plot_arrays(dgroup)
        ppanel = self.controller.get_display(stacked=False).panel
        viewlims = ppanel.get_viewlimits()
        plotcmd = ppanel.oplot
        if new:
            plotcmd = ppanel.plot

        groupname = getattr(dgroup, 'groupname', None)
        if groupname is None:
            return

        if not hasattr(dgroup, 'xdat'):
            print("Cannot plot group ", groupname)

        if ((getattr(dgroup, 'plot_yarrays', None) is None or
             getattr(dgroup, 'energy', None) is None or
             getattr(dgroup, 'mu', None) is None or
             getattr(dgroup, 'e0', None) is None or
             getattr(dgroup, 'dmude', None) is None or
             getattr(dgroup, 'norm', None) is None)):
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

        plot_choices = PlotSel_Choices
        if dgroup.datatype != 'xas':
            plot_choices = PlotSel_Choices_nonxas

        if multi:
            ylabel = self.plotsel_op.GetStringSelection()
            yarray_name = plot_choices[ylabel]
            if dgroup.datatype == 'xas':
                ylabel = getattr(plotlabels, yarray_name, ylabel)
            popts['ylabel'] = ylabel

        plot_extras = None
        if new:
            if title is None:
                title = fname
            plot_extras = getattr(dgroup, 'plot_extras', None)

        popts['title'] = title
        popts['delay_draw'] = delay_draw
        if hasattr(dgroup, 'custom_plotopts'):
            popts.update(dgroup.custom_plotopts)

        popts['show_legend'] = len(plot_yarrays) > 1
        narr = len(plot_yarrays) - 1
        for i, pydat in enumerate(plot_yarrays):
            yaname, yopts, yalabel = pydat
            popts.update(yopts)
            if yalabel is not None:
                popts['label'] = yalabel

            popts['delay_draw'] = delay_draw or (i != narr)
            if yaname == 'dnormde' and not hasattr(dgroup, yaname):
                self.make_dnormde(dgroup)
            if yaname == 'norm_mback' and not hasattr(dgroup, yaname):
                self.process(force_mback=True, noskip=True)

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
