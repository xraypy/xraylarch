#!/usr/bin/env python
"""
XANES Normalization panel
"""
import time
import wx
from copy import deepcopy
import numpy as np

from functools import partial
from xraydb import guess_edge, atomic_number

from larch.utils import gformat, path_split
from larch.math import index_of
from larch.xafs.xafsutils import guess_energy_units
from larch.xafs.pre_edge import find_e0

from larch.wxlib import (BitmapButton, FloatCtrl, FloatSpin, get_icon,
                         SimpleText, pack, Button, HLine, Choice, Check,
                         GridPanel, CEN, RIGHT, LEFT, plotlabels,
                         get_zoomlimits, set_zoomlimits)

from larch.utils.strutils import fix_varname, fix_filename, file2groupname

from larch.utils.physical_constants import ATOM_NAMES
from larch.wxlib.plotter import last_cursor_pos
from .xas_dialogs import EnergyUnitsDialog
from .taskpanel import TaskPanel, autoset_fs_increment, update_confval
from .config import (make_array_choice, EDGES, ATSYMS,
                     NNORM_CHOICES, NNORM_STRINGS, NORM_METHODS)

np.seterr(all='ignore')

PLOTOPTS_1 = dict(style='solid', marker='None')
PLOTOPTS_2 = dict(style='short dashed', zorder=3, marker='None')
PLOTOPTS_D = dict(style='solid', zorder=2, side='right', marker='None')

PlotOne_Choices = make_array_choice(['mu','norm', 'flat', 'prelines',
                                     'norm+flat', 'mback_norm', 'mback_poly',
                                     'i0', 'norm+i0', 'dmude', 'norm+dmude',
                                     'd2mude', 'norm+d2mude'])


PlotSel_Choices = make_array_choice(['mu', 'norm', 'flat', 'dmude', 'd2mude'])

Plot_EnergyRanges = {'full E range': None,
                     'E0 -20:+80eV':  (-20, 80),
                     'E0 -30:+120eV': (-30, 120),
                     'E0 -50:+250eV': (-50, 250),
                     'E0 -100:+500eV': (-100, 500)}



FSIZE = 120
FSIZEBIG = 175

def get_auto_nnorm(norm1, norm2):
    "autoamatically set nnorm from range"
    nrange = abs(norm2 - norm1)
    nnorm = 2
    if nrange < 300:   nnorm = 1
    if nrange < 30:    nnorm = 0
    return nnorm

class XASNormPanel(TaskPanel):
    """XAS normalization Panel"""
    def __init__(self, parent, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller, panel='xasnorm', **kws)

    def build_display(self):
        panel = self.panel
        self.wids = {}
        self.last_plot_type = 'one'

        trow = wx.Panel(panel)
        plot_sel = Button(trow, 'Plot Selected Groups', size=(175, -1),
                          action=self.onPlotSel)
        plot_one = Button(trow, 'Plot Current Group', size=(175, -1),
                          action=self.onPlotOne)

        self.plotsel_op = Choice(trow, choices=list(PlotSel_Choices.keys()),
                                 action=self.onPlotSel, size=(300, -1))
        self.plotone_op = Choice(trow, choices=list(PlotOne_Choices.keys()),
                                 action=self.onPlotOne, size=(300, -1))

        self.plot_erange = Choice(trow, choices=list(Plot_EnergyRanges.keys()),
                                 action=self.onPlotEither, size=(175, -1))

        opts = {'digits': 2, 'increment': 0.05, 'value': 0, 'size': (FSIZE, -1)}
        plot_voff = self.add_floatspin('plot_voff', with_pin=False,
                                       parent=trow,
                                       action=self.onVoffset,
                                       max_val=10000, min_val=-10000,
                                       **opts)

        vysize, vxsize = plot_sel.GetBestSize()
        voff_lab = wx.StaticText(parent=trow, label='  Y Offset:', size=(80, vxsize),
                                 style=wx.RIGHT|wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE)

        self.plot_erange.SetSelection(0)
        self.plotone_op.SetSelection(1)
        self.plotsel_op.SetSelection(1)

        tsizer = wx.GridBagSizer(3, 3)
        tsizer.Add(plot_sel,        (0, 0), (1, 1), LEFT, 2)
        tsizer.Add(self.plotsel_op, (0, 1), (1, 1), LEFT, 2)
        tsizer.Add(voff_lab,        (0, 2), (1, 1), RIGHT, 2)
        tsizer.Add(plot_voff,       (0, 3), (1, 1), RIGHT, 2)
        tsizer.Add(plot_one,       (1, 0), (1, 1), LEFT, 2)
        tsizer.Add(self.plotone_op, (1, 1), (1, 1), LEFT, 2)
        tsizer.Add(self.plot_erange, (1, 2), (1, 2), RIGHT, 2)

        pack(trow, tsizer)

        # atom row
        atpanel = wx.Panel(panel)
        self.wids['atsym']  = Choice(atpanel, choices=ATSYMS, size=(100, -1))
        self.wids['edge']   = Choice(atpanel, choices=EDGES, size=(100, -1))
        sat = wx.BoxSizer(wx.HORIZONTAL)
        sat.Add(self.wids['atsym'], 0, LEFT, 4)
        sat.Add(self.wids['edge'], 0, LEFT, 4)
        pack(atpanel, sat)

        # e0 row
        e0_panel = wx.Panel(panel)
        xas_e0   = self.add_floatspin('e0', action=self.onSet_XASE0Val,
                                      min_val=-1000, max_val=1e7, digits=3,
                                      increment=0.05, value=0, size=(FSIZEBIG, -1),
                                      parent=e0_panel)

        self.wids['auto_e0'] = Check(e0_panel, default=True, label='auto?',
                                    action=self.onAuto_XASE0)
        self.wids['show_e0'] = Check(e0_panel, default=True, label='show?',
                                     action=self.onSet_XASE0)

        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(xas_e0, 0, LEFT, 4)
        sx.Add(self.wids['auto_e0'], 0, LEFT, 4)
        sx.Add(self.wids['show_e0'], 0, LEFT, 4)
        pack(e0_panel, sx)

        # step row
        step_panel = wx.Panel(panel)
        xas_step = self.add_floatspin('step', action=self.onSet_XASStep, with_pin=False,
                                      min_val=-1000.0, max_val=1e7, digits=4, increment=0.05,
                                      value=0.1, size=(FSIZEBIG, -1), parent=step_panel)
        self.wids['auto_step'] = Check(step_panel, default=True, label='auto?',
                                       action=self.onNormMethod)
        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(xas_step, 0, LEFT, 4)
        sx.Add(self.wids['auto_step'], 0, LEFT, 4)
        pack(step_panel, sx)

        # step rows
        nnorm_panel = wx.Panel(panel)
        self.wids['nnorm'] = Choice(nnorm_panel, choices=list(NNORM_CHOICES.keys()),
                                    size=(150, -1), action=self.onNNormChoice,
                                    default=2)
        self.wids['auto_nnorm'] = Check(nnorm_panel, default=True, label='auto?',
                                    action=self.onAuto_NNORM)

        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(self.wids['nnorm'], 0, LEFT, 4)
        sx.Add(self.wids['auto_nnorm'], 0, LEFT, 4)
        pack(nnorm_panel, sx)

        self.wids['energy_ref'] = Choice(panel, choices=['None'],
                                         action=self.onEnergyRef, size=(300, -1))

        self.wids['nvict'] = Choice(panel, choices=('0', '1', '2', '3'),
                                    size=(100, -1), action=self.onNormMethod,
                                    default=0)


        opts = {'size': (FSIZE, -1), 'digits': 2, 'increment': 5.0, 'action': self.onSet_Ranges,
                'min_val':-99000, 'max_val':99000}
        defaults = self.get_defaultconfig()

        pre_panel = wx.Panel(panel)
        xas_pre1 = self.add_floatspin('pre1', value=defaults['pre1'], parent=pre_panel, **opts)
        xas_pre2 = self.add_floatspin('pre2', value=defaults['pre2'], parent=pre_panel, **opts)
        self.wids['show_pre'] = Check(pre_panel, default=False, label='show?',
                                      action=self.onSet_XASE0)

        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(xas_pre1, 0, LEFT, 4)
        sx.Add(SimpleText(pre_panel, ' : '), 0, LEFT, 4)
        sx.Add(xas_pre2, 0, LEFT, 4)
        sx.Add(self.wids['show_pre'], 0, LEFT, 4)
        pack(pre_panel, sx)

        nor_panel = wx.Panel(panel)
        xas_norm1 = self.add_floatspin('norm1', value=defaults['norm1'], parent=nor_panel, **opts)
        xas_norm2 = self.add_floatspin('norm2', value=defaults['norm2'], parent=nor_panel, **opts)

        self.wids['show_norm'] = Check(nor_panel, default=False, label='show?',
                                       action=self.onSet_XASE0)
        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(xas_norm1, 0, LEFT, 4)
        sx.Add(SimpleText(nor_panel, ' : '), 0, LEFT, 4)
        sx.Add(xas_norm2, 0, LEFT, 4)
        sx.Add(self.wids['show_norm'], 0, LEFT, 4)
        pack(nor_panel, sx)


        opts = {'digits': 3, 'increment': 0.05, 'value': 0, 'size': (FSIZEBIG, -1)}

        opts.update({'value': 1.0, 'digits': 3})

        self.wids['norm_method'] = Choice(panel, choices=NORM_METHODS,
                                          size=(150, -1), action=self.onNormMethod)
        self.wids['norm_method'].SetSelection(0)
        self.wids['energy_shift'] = FloatSpin(panel, value=0, digits=3, increment=0.05,
                                              min_val=-99000, max_val=99000,
                                              action=self.onSet_EnergyShift,
                                              size=(FSIZEBIG, -1))


        self.wids['is_frozen'] = Check(panel, default=False, label='Freeze Group',
                                       action=self.onFreezeGroup)

        use_auto = Button(panel, 'Use Default Settings', size=(200, -1),
                          action=self.onResetNorm)

        def CopyBtn(name):
            return Button(panel, 'Copy', size=(60, -1),
                          action=partial(self.onCopyParam, name))

        copy_all = Button(panel, 'Copy All Parameters', size=(200, -1),
                          action=partial(self.onCopyParam, 'all'))

        add_text = self.add_text
        HLINEWID = 700
        panel.Add(SimpleText(panel, 'XAS Pre-edge subtraction and Normalization',
                             size=(650, -1), **self.titleopts), style=LEFT, dcol=4)
        panel.Add(trow, dcol=4, newrow=True)

        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=4, newrow=True)
        add_text('XAS Data:')
        panel.Add(use_auto, dcol=1)
        panel.Add(SimpleText(panel, 'Copy to Selected Groups:'), style=RIGHT, dcol=2)

        add_text('Element and Edge: ', newrow=True)
        panel.Add(atpanel, dcol=2)
        panel.Add(CopyBtn('atsym'), dcol=1, style=RIGHT)

        add_text('Energy Reference : ')
        panel.Add(self.wids['energy_ref'], dcol=2)
        panel.Add(CopyBtn('energy_ref'), dcol=1, style=RIGHT)

        add_text('Energy Shift : ')
        panel.Add(self.wids['energy_shift'], dcol=2)
        panel.Add(CopyBtn('energy_shift'), dcol=1, style=RIGHT)

        add_text('E0 : ')
        panel.Add(e0_panel, dcol=2)
        panel.Add(CopyBtn('xas_e0'), dcol=1, style=RIGHT)

        add_text('Edge Step: ')
        panel.Add(step_panel, dcol=2)
        panel.Add(CopyBtn('xas_step'), dcol=1, style=RIGHT)

        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=4, newrow=True)

        add_text('Pre-edge range: ')
        panel.Add(pre_panel, dcol=2)
        panel.Add(CopyBtn('xas_pre'), dcol=1, style=RIGHT)

        panel.Add(SimpleText(panel, 'Victoreen order:'), newrow=True)
        panel.Add(self.wids['nvict'], dcol=2)

        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=4, newrow=True)

        add_text('Normalization : ')
        panel.Add(self.wids['norm_method'], dcol=2)
        panel.Add(CopyBtn('xas_norm'), dcol=1, style=RIGHT)

        add_text('Norm Energy range: ')
        panel.Add(nor_panel, dcol=2)
        panel.Add(SimpleText(panel, 'Polynomial Type:'), newrow=True)
        panel.Add(nnorm_panel, dcol=3)

        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=4, newrow=True)
        panel.Add(self.wids['is_frozen'], newrow=True)
        panel.Add(copy_all, dcol=3, style=RIGHT)

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((5, 5), 0, LEFT, 3)
        sizer.Add(panel, 0, LEFT, 3)
        sizer.Add((5, 5), 0, LEFT, 3)
        pack(self, sizer)

    def get_config(self, dgroup=None):
        """custom get_config to possibly inherit from Athena settings"""
        if dgroup is None:
            dgroup = self.controller.get_group()
        if dgroup is None:
            return self.get_defaultconfig()
        self.read_form()


        defconf = self.get_defaultconfig()
        conf = getattr(dgroup.config, self.configname, defconf)

        for k, v in defconf.items():
            if k not in conf:
                conf[k] = v
        if conf.get('edge_step', None) is None:
            conf['edge_step'] = getattr(dgroup, 'edge_step', 1)

        atsym = '?'
        if hasattr(dgroup, 'element'):
            elem = getattr(dgroup, 'element', '?')
            try:
                z = int(elem)
                atsym = ATSYMS[z]
            except:
                pass
            if elem in ATSYMS[1:]:
                atsym = elem
            else:
                try:
                    if elem.lower() in ATOM_NAMES:
                        z = 1 + ATOM_NAMES.index(eleme.lower())
                        atsym = ATSYMS[z]
                except:
                    pass

        conf['atsym'] = atsym
        if atsym == '?':
            conf['atsym'] = getattr(dgroup, 'atsym', atsym)
        conf['edge'] = getattr(dgroup,'edge', conf['edge'])

        xeref = getattr(dgroup, 'energy_ref', '')
        fname = getattr(dgroup, 'filename', None)
        if fname is None:
            fname = getattr(dgroup, 'groupname', None)
            if fname is None:
                fname =file2groupname('unknown_group',
                                      symtable=self._larch.symtable)

        conf['energy_ref'] = getattr(dgroup, 'energy_ref', fname)

        if conf['energy_ref'] in (None, 'None'):
            conf['energy_ref'] = fname


        conf['energy_shift'] = getattr(dgroup,'energy_shift', conf['energy_shift'])

        if hasattr(dgroup, 'e0') and conf['atsym'] == '?':
            atsym, edge = guess_edge(dgroup.e0)
            conf['atsym'] = atsym
            conf['edge'] = edge


        if hasattr(dgroup, 'mback_params'):
            conf['atsym'] = getattr(dgroup.mback_params, 'atsym', conf['atsym'])
            conf['edge'] = getattr(dgroup.mback_params, 'edge', conf['edge'])

        setattr(dgroup.config, self.configname, conf)
        return conf

    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)
        self.skip_process = True
        if self.is_xasgroup(dgroup):
            if self.plotone_op.GetCount() != len(PlotOne_Choices.keys()):
                self.plotone_op.SetChoices(list(PlotOne_Choices.keys()))
                self.plotone_op.SetSelection(1)
            if self.plotsel_op.GetCount() != len(PlotSel_Choices.keys()):
                self.plotsel_op.SetChoices(list(PlotSel_Choices.keys()))
                self.plotsel_op.SetSelection(1)

            groupnames = list(self.controller.file_groups.keys())
            self.wids['energy_ref'].SetChoices(groupnames)
            eref = opts.get('energy_ref', 'no_energy_ref')

            for key, val in self.controller.file_groups.items():
                if eref in (val, key):
                    self.wids['energy_ref'].SetStringSelection(key)

            self.wids['e0'].SetValue(opts.get('e0', -1))
            edge_step = opts.get('edge_step', 1.0)

            if hasattr(dgroup, 'e0') and opts['atsym'] == '?':
                atsym, edge = guess_edge(dgroup.e0)
                opts['atsym'] = atsym
                opts['edge'] = edge

            self.wids['step'].SetValue(edge_step)
            autoset_fs_increment(self.wids['step'], edge_step)
            for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
                val = opts.get(attr, None)
                if val is not None:
                    self.wids[attr].SetValue(val)
            self.set_nnorm_widget(opts.get('nnorm'))

            self.wids['energy_shift'].SetValue(opts['energy_shift'])
            self.wids['nvict'].SetStringSelection("%d" % opts['nvict'])
            self.wids['show_e0'].SetValue(opts['show_e0'])
            self.wids['auto_e0'].SetValue(opts['auto_e0'])
            self.wids['auto_nnorm'].SetValue(opts.get('auto_nnorm', 0))
            self.wids['auto_step'].SetValue(opts['auto_step'])

            self.wids['edge'].SetStringSelection(opts['edge'].title())
            self.wids['atsym'].SetStringSelection(opts['atsym'].title())
            self.wids['norm_method'].SetStringSelection(opts['norm_method'].lower())
            for attr in ('pre1', 'pre2', 'norm1', 'norm2', 'nnorm', 'edge',
                         'atsym', 'step', 'norm_method'):
                self.wids[attr].Enable()
            self.wids['show_pre'].SetValue(opts['show_pre'])
            self.wids['show_norm'].SetValue(opts['show_norm'])


        frozen = opts.get('is_frozen', False)
        frozen = getattr(dgroup, 'is_frozen', frozen)

        self.wids['is_frozen'].SetValue(frozen)
        self._set_frozen(frozen)
        wx.CallAfter(self.unset_skip_process)

    def set_nnorm_widget(self, nnorm=None):
        conf = self.get_config()
        nnorm_default = get_auto_nnorm(conf['norm1'], conf['norm2'])
        if nnorm in (None, 'auto'):
            nnorm = nnorm_default
        elif nnorm in NNORM_CHOICES:
            nnorm = int(NNORM_CHOICES[nnorm])
        nnorm_str = NNORM_STRINGS.get(nnorm, None)
        if nnorm_str is None:
            nnorm_str = NNORM_STRINGS.get(nnorm_default, '1')
        self.wids['nnorm'].SetStringSelection(nnorm_str)
        self.wids['auto_nnorm'].SetValue(0)

    def unset_skip_process(self):
        self.skip_process = False

    def read_form(self):
        "read form, return dict of values"
        form_opts = {}
        form_opts['e0'] = self.wids['e0'].GetValue()
        form_opts['edge_step'] = self.wids['step'].GetValue()
        for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
            val = self.wids[attr].GetValue()
            if val == 0: val = None
            form_opts[attr] = val

        form_opts['energy_shift'] = self.wids['energy_shift'].GetValue()

        form_opts['nnorm'] = NNORM_CHOICES.get(self.wids['nnorm'].GetStringSelection(), 1)
        form_opts['nvict'] = int(self.wids['nvict'].GetStringSelection())
        form_opts['plotone_op'] = self.plotone_op.GetStringSelection()
        form_opts['plotsel_op'] = self.plotsel_op.GetStringSelection()
        form_opts['plot_voff'] = self.wids['plot_voff'].GetValue()
        for ch in ('show_e0', 'show_pre', 'show_norm', 'auto_e0',
                   'auto_step', 'auto_nnorm'):
            form_opts[ch] = self.wids[ch].IsChecked()

        form_opts['norm_method'] = self.wids['norm_method'].GetStringSelection().lower()
        form_opts['edge'] = self.wids['edge'].GetStringSelection().title()
        form_opts['atsym'] = self.wids['atsym'].GetStringSelection().title()
        form_opts['energy_ref'] = self.wids['energy_ref'].GetStringSelection()
        return form_opts

    def onNNormChoice(self, evt=None):
        auto_nnorm  = self.wids['auto_nnorm'].SetValue(0)
        self.onNormMethod()

    def onNormMethod(self, evt=None):
        method = self.wids['norm_method'].GetStringSelection().lower()
        auto_nnorm  = self.wids['auto_nnorm'].GetValue()

        nnorm  = NNORM_CHOICES.get(self.wids['nnorm'].GetStringSelection(), 1)
        if nnorm is None:
            nnorm = get_auto_nnorm(self.wids['norm1'].GetValue(),
                                   self.wids['norm2'].GetValue())

        nvict = int(self.wids['nvict'].GetStringSelection())
        self.update_config({'norm_method': method, 'nnorm': nnorm, 'nvict': nvict})
        if method.startswith('mback'):
            dgroup = self.controller.get_group()
            cur_elem = self.wids['atsym'].GetStringSelection()
            if hasattr(dgroup, 'e0') and cur_elem == 'H':
                atsym, edge = guess_edge(dgroup.e0)
                self.wids['edge'].SetStringSelection(edge)
                self.wids['atsym'].SetStringSelection(atsym)
                self.update_config({'edge': edge, 'atsym': atsym})
        time.sleep(0.002)
        wx.CallAfter(self.onReprocess)

    def _set_frozen(self, frozen):
        try:
            dgroup = self.controller.get_group()
            dgroup.is_frozen = frozen
        except:
            pass

        for wattr in ('e0', 'step', 'pre1', 'pre2', 'norm1', 'norm2', 'nvict',
                      'nnorm', 'show_e0', 'auto_e0', 'auto_step', 'auto_nnorm',
                      'norm_method', 'edge', 'atsym', 'show_pre', 'show_norm'):
            self.wids[wattr].Enable(not frozen)

    def onFreezeGroup(self, evt=None):
        self._set_frozen(evt.IsChecked())

    def onEnergyRef(self, evt=None):
        dgroup = self.controller.get_group()
        eref = self.wids['energy_ref'].GetStringSelection()
        gname = self.controller.file_groups[eref]
        dgroup.config.xasnorm['energy_ref'] = eref
        dgroup.energy_ref = eref
        self.update_config({'energy_ref': eref}, dgroup=dgroup)

    def onPlotEither(self, evt=None):
        if self.last_plot_type == 'multi':
            self.onPlotSel(evt=evt)
        else:
            self.onPlotOne(evt=evt)

    def onPlotOne(self, evt=None):
        self.last_plot_type = 'one'
        self.plot(self.controller.get_group())
        wx.CallAfter(self.controller.set_focus)

    def onVoffset(self, evt=None):
        time.sleep(0.002)
        wx.CallAfter(self.onPlotSel)

    def onPlotSel(self, evt=None):
        newplot = True
        self.last_plot_type = 'multi'
        group_ids = self.controller.filelist.GetCheckedStrings()
        if len(group_ids) < 1:
            return
        last_id = group_ids[-1]

        groupname = self.controller.file_groups[str(last_id)]
        dgroup = self.controller.get_group(groupname)

        plot_choices = PlotSel_Choices

        erange = Plot_EnergyRanges[self.plot_erange.GetStringSelection()]
        self.controller.set_plot_erange(erange)

        ytitle = self.plotsel_op.GetStringSelection()
        yarray_name = plot_choices.get(ytitle, 'norm')
        ylabel = getattr(plotlabels, yarray_name, ytitle)
        xlabel = getattr(dgroup, 'plot_xlabel', getattr(plotlabels, 'energy'))

        if yarray_name == 'norm':
            norm_method = self.wids['norm_method'].GetStringSelection().lower()
            if norm_method.startswith('mback'):
                yarray_name = 'norm_mback'
                ylabel = "%s (MBACK)" % ylabel
            elif  norm_method.startswith('area'):
                yarray_name = 'norm_area'
                ylabel = "%s (Area)" % ylabel

        voff = self.wids['plot_voff'].GetValue()
        plot_traces = []
        newplot = True
        plotopts = self.controller.get_plot_conf()
        popts = {'style': 'solid', 'marker': None}
        popts['linewidth'] = plotopts.pop('linewidth')
        popts['marksize'] = plotopts.pop('markersize')
        popts['grid'] = plotopts.pop('show_grid')
        popts['fullbox'] = plotopts.pop('show_fullbox')

        for ix, checked in enumerate(group_ids):
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            if dgroup is None:
                continue
            self.ensure_xas_processed(dgroup, force_mback =('mback' in yarray_name))

            if erange is not None and hasattr(dgroup, 'e0') and 'xmin' not in popts:
                popts['xmin'] = dgroup.e0 + erange[0]
                popts['xmax'] = dgroup.e0 + erange[1]

            trace = {'xdata': dgroup.xplot,
                     'ydata': getattr(dgroup, yarray_name) + ix*voff,
                     'label': dgroup.filename, 'new': newplot}
            trace.update(popts)
            plot_traces.append(trace)
            newplot = False

        ppanel = self.controller.get_display(stacked=False).panel
        zoom_limits = get_zoomlimits(ppanel, dgroup)

        nplot_traces = len(ppanel.conf.traces)
        nplot_request = len(plot_traces)
        if nplot_request > nplot_traces:
            linecolors = ppanel.conf.linecolors
            ncols = len(linecolors)
            for i in range(nplot_traces, nplot_request+5):
                ppanel.conf.init_trace(i,  linecolors[i%ncols], 'dashed')

        #

        ppanel.plot_many(plot_traces, xlabel=plotlabels.energy, ylabel=ylabel,
                         zoom_limits=zoom_limits, show_legend=True)
        set_zoomlimits(ppanel, zoom_limits) or ppanel.unzoom_all()
        ppanel.canvas.draw()

        wx.CallAfter(self.controller.set_focus)

    def onAuto_NNORM(self, evt=None):
        if evt.IsChecked():
            nnorm = get_auto_nnorm(self.wids['norm1'].GetValue(),
                                   self.wids['norm2'].GetValue())
            self.set_nnorm_widget(nnorm)
            self.wids['auto_nnorm'].SetValue(0)
            time.sleep(0.001)
            wx.CallAfter(self.onReprocess)

    def onResetNorm(self, evt=None):
        auto_nnorm = self.wids['auto_nnorm'].GetValue()
        if auto_nnorm:
            nnorm = get_auto_nnorm(self.wids['norm1'].GetValue(),
                                   self.wids['norm2'].GetValue())
            self.set_nnorm_widget(nnorm)

        defaults = self.get_defaultconfig()

        self.wids['auto_step'].SetValue(1)
        self.wids['auto_e0'].SetValue(1)
        self.wids['auto_e0'].SetValue(1)
        self.wids['nvict'].SetSelection(0)
        for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
            self.wids[attr].SetValue(defaults[attr])
        self.onReprocess()

    def onCopyAuto(self, evt=None):
        opts = dict(pre1=0, pre2=0, nvict=0, norm1=0, norm2=0,
                    norm_method='polynomial', nnorm=2, auto_e0=1,
                    auto_step=1)
        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group and not getattr(grp, 'is_frozen', False):
                self.update_config(opts, dgroup=grp)
                self.fill_form(grp)
                self.process(grp, force=True)


    def onSaveConfigBtn(self, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())
        # self.set_defaultconfig(conf)

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
        if name == 'all':
            copy_attrs('e0', 'show_e0', 'auto_e0', 'edge_step',
                       'auto_step', 'energy_shift', 'pre1', 'pre2',
                       'nvict', 'atsym', 'edge', 'norm_method', 'nnorm',
                       'norm1', 'norm2', 'energy_ref')
        elif name == 'xas_e0':
            copy_attrs('e0', 'show_e0', 'auto_e0')
        elif name == 'xas_step':
            copy_attrs('edge_step', 'auto_step')
        elif name == 'energy_shift':
            copy_attrs('energy_shift')
        elif name == 'xas_pre':
            copy_attrs('pre1', 'pre2', 'nvict', 'show_pre')
        elif name == 'atsym':
            copy_attrs('atsym', 'edge')
        elif name == 'xas_norm':
            copy_attrs('norm_method', 'nnorm', 'norm1', 'norm2', 'show_norm')
        elif name == 'energy_ref':
            copy_attrs('energy_ref')
        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group and not getattr(grp, 'is_frozen', False):
                self.update_config(opts, dgroup=grp)
                for key, val in opts.items():
                    if hasattr(grp, key):
                        setattr(grp, key, val)
                self.fill_form(grp)
                self.process(grp, force=True)

    def onAuto_XASE0(self, evt=None):
        if evt.IsChecked():
            dgroup = self.controller.get_group()
            find_e0(dgroup)
            self.update_config({'e0': dgroup.e0})
            time.sleep(0.002)
            wx.CallAfter(self.onReprocess)

    def onSet_XASE0(self, evt=None, value=None):
        "handle setting auto e0 / show e0"
        auto_e0  = self.wids['auto_e0'].GetValue()
        self.update_config({'e0': self.wids['e0'].GetValue(),
                           'auto_e0':self.wids['auto_e0'].GetValue()})
        time.sleep(0.002)
        wx.CallAfter(self.onReprocess)

    def onSet_XASE0Val(self, evt=None, value=None):
        "handle setting e0"
        self.wids['auto_e0'].SetValue(0)
        self.update_config({'e0': self.wids['e0'].GetValue(),
                            'auto_e0':self.wids['auto_e0'].GetValue()})
        time.sleep(0.002)
        wx.CallAfter(self.onReprocess)

    def onSet_EnergyShift(self, evt=None, value=None):
        conf = self.get_config()
        if conf['auto_energy_shift']:
            eshift = self.wids['energy_shift'].GetValue()
            dgroup = self.controller.get_group()
            _eref = getattr(dgroup, 'energy_ref', '<;no eref;>')
            _gname = dgroup.groupname
            self.stale_groups = []
            for fname, gname in self.controller.file_groups.items():
                this = self.controller.get_group(gname)
                if _gname != gname and _eref == getattr(this, 'energy_ref', None):
                    this.energy_shift = this.config.xasnorm['energy_shift'] = eshift
                    self.stale_groups.append(this)

        wx.CallAfter(self.onReprocess)

    def onSet_XASStep(self, evt=None, value=None):
        "handle setting edge step"
        edge_step = self.wids['step'].GetValue()
        if edge_step < 0:
            self.wids['step'].SetValue(abs(edge_step))
        self.wids['auto_step'].SetValue(0)
        self.update_config({'edge_step': abs(edge_step), 'auto_step': False})
        autoset_fs_increment(self.wids['step'], abs(edge_step))
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)


    def onSet_Ranges(self, evt=None, **kws):
        conf = {}
        for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
            conf[attr] = self.wids[attr].GetValue()
        self.update_config(conf)
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)

    def pin_callback(self, opt='__', xsel=None, relative_e0=True, **kws):
        """
        get last selected point from a specified plot window
        and fill in the value for the widget defined by `opt`.

        by default it finds the latest cursor position from the
        cursor history of the first 20 plot windows.
        """
        if xsel is None or opt not in self.wids:
            return

        e0 = self.wids['e0'].GetValue()
        if opt == 'e0':
            self.wids['e0'].SetValue(xsel)
            self.wids['auto_e0'].SetValue(0)
        elif opt in ('pre1', 'pre2', 'norm1', 'norm2'):
            self.wids[opt].SetValue(xsel-e0)
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)

    def onReprocess(self, evt=None, value=None, **kws):
        "handle request reprocess"
        if self.skip_process:
            return
        try:
            dgroup = self.controller.get_group()
        except TypeError:
            return
        if not hasattr(dgroup.config, self.configname):
            return
        form = self.read_form()
        self.process(dgroup=dgroup)
        if self.stale_groups is not None:
            for g in self.stale_groups:
                self.process(dgroup=g, force=True)
            self.stale_groups = None
        self.onPlotEither()


    def process(self, dgroup=None, force_mback=False, force=False, use_form=True, **kws):
        """ handle process (pre-edge/normalize) of XAS data from XAS form
        """
        if self.skip_process and not force:
            return
        if dgroup is None:
            dgroup = self.controller.get_group()
        if dgroup is None:
            return

        self.skip_process = True
        conf = self.get_config(dgroup)
        form = self.read_form()
        if not use_form:
            form.update(self.get_defaultconfig())

        form['group'] = dgroup.groupname
        groupnames = list(self.controller.file_groups.keys())
        self.wids['energy_ref'].SetChoices(groupnames)
        eref_sel = self.wids['energy_ref'].GetStringSelection()
        for key, val in self.controller.file_groups.items():
            if eref_sel in (val, key):
                self.wids['energy_ref'].SetStringSelection(key)


        en_units = getattr(dgroup, 'energy_units', None)
        if en_units is None:
            en_units = guess_energy_units(dgroup.energy)

        if en_units != 'eV':
            mono_dspace = getattr(dgroup, 'mono_dspace', 1)
            dlg = EnergyUnitsDialog(self.parent, dgroup.energy,
                                    unitname=en_units,
                                    dspace=mono_dspace)
            res = dlg.GetResponse()
            dlg.Destroy()
            if res.ok:
                en_units = res.units
                dgroup.mono_dspace = res.dspace
                dgroup.xplot = dgroup.energy = res.energy
        dgroup.energy_units = en_units

        if not hasattr(dgroup, 'e0'):
            e0 = find_e0(dgroup)
            if form['atsym'] == '?' and conf.get('atsym', '?') != '?':
                form['atsym'] = conf['atsym']
                form['edge'] = conf.get('edge', 'K')

        if form['atsym'] == '?':
            form['atsym'], form['edge'] = guess_edge(dgroup.e0)
        dgroup.atsym = form['atsym']
        dgroup.edge = form['edge']


        cmds = []
        # test whether the energy shift is 0 or is different from the current energy shift:
        ediff = 8.42e14  # just a huge energy step/shift
        eshift_current = getattr(dgroup, 'energy_shift', ediff)
        eshift = form.get('energy_shift', ediff)
        e1 = getattr(dgroup, 'energy', [ediff])
        e2 = getattr(dgroup, 'energy_orig', None)

        if (not isinstance(e2, np.ndarray) or (len(e1) != len(e2))):
            cmds.append("{group:s}.energy_orig = {group:s}.energy[:]")

        if (isinstance(e1, np.ndarray) and isinstance(e2, np.ndarray) and
            len(e1) == len(e2)):
            ediff = (e1-e2).min()

        if abs(eshift-ediff) > 1.e-5 or abs(eshift-eshift_current) > 1.e-5:
            if abs(eshift) > 1e15: eshift = 0.0
            cmds.extend(["{group:s}.energy_shift = {eshift:.4f}",
                         "{group:s}.energy = {group:s}.xplot = {group:s}.energy_orig + {group:s}.energy_shift"])

        if len(cmds) > 0:
            self.larch_eval(('\n'.join(cmds)).format(group=dgroup.groupname, eshift=eshift))

        e0 = form['e0']
        edge_step = form['edge_step']

        copts = [dgroup.groupname]
        if not form['auto_e0']:
            if e0 < max(dgroup.energy) and e0 > min(dgroup.energy):
                copts.append("e0=%.4f" % float(e0))

        if not form['auto_step']:
            copts.append("step=%s" % gformat(float(edge_step)))

        for attr in ('pre1', 'pre2', 'nvict', 'nnorm', 'norm1', 'norm2'):
            val = form[attr]
            if val is None or val == 'auto':
                val = 'None'
            elif attr in ('nvict', 'nnorm'):
                if val in NNORM_CHOICES:
                    val = NNORM_CHOICES[val]
                val = int(val)
            else:
                val = f"{float(val):.2f}"
            copts.append(f"{attr}={val}")
        # print("process PreEdge ", copts)
        self.larch_eval("pre_edge(%s)" % (', '.join(copts)))
        self.larch_eval("{group:s}.norm_poly = 1.0*{group:s}.norm".format(**form))
        if not hasattr(dgroup, 'e0'):
            self.skip_process = False
            dgroup.mu = dgroup.yplot * 1.0
            opts = {'group': dgroup.groupname}
            return

        norm_method = form['norm_method'].lower()
        form['normmeth'] = 'poly'

        dgroup.journal.add_ifnew('normalization_method', norm_method)

        if force_mback or norm_method.startswith('mback'):
            form['normmeth'] = 'mback'
            copts = [dgroup.groupname]
            copts.append("z=%d" % atomic_number(form['atsym']))
            copts.append("edge='%s'" % form['edge'])
            for attr in ('pre1', 'pre2', 'nvict', 'nnorm', 'norm1', 'norm2'):
                val = form[attr]
                if val is None or val == 'auto':
                    val = 'None'
                elif attr in ('nvict', 'nnorm'):
                    if val in NNORM_CHOICES:
                        val = NNORM_CHOICES[val]
                    val = int(val)
                else:
                    val = f"{float(val):.2f}"
                copts.append(f"{attr}={val}")
            self.larch_eval("mback_norm(%s)" % (', '.join(copts)))

            if form['auto_step']:
                norm_expr = """{group:s}.norm = 1.0*{group:s}.norm_{normmeth:s}
{group:s}.edge_step = 1.0*{group:s}.edge_step_{normmeth:s}"""
                self.larch_eval(norm_expr.format(**form))
            else:
                norm_expr = """{group:s}.norm = 1.0*{group:s}.norm_{normmeth:s}
{group:s}.norm *= {group:s}.edge_step_{normmeth:s}/{edge_step:.8f}"""
                self.larch_eval(norm_expr.format(**form))

        if norm_method.startswith('area'):
            form['normmeth'] = 'area'
            expr = """{group:s}.norm = 1.0*{group:s}.norm_{normmeth:s}
{group:s}.edge_step = 1.0*{group:s}.edge_step_{normmeth:s}"""
            self.larch_eval(expr.format(**form))


        if form['auto_e0'] and hasattr(dgroup, 'e0'):
            self.wids['e0'].SetValue(dgroup.e0)
        if form['auto_step'] and hasattr(dgroup, 'edge_step'):
            self.wids['step'].SetValue(dgroup.edge_step)
            autoset_fs_increment(self.wids['step'], dgroup.edge_step)

        if hasattr(dgroup, 'e0') and (conf.get('atsym', '?') == '?'):
            atsym, edge = guess_edge(dgroup.e0)
            conf['atsym'] = dgroup.atsym = atsym
            conf['edge'] = dgroup.edge = edge
        self.wids['atsym'].SetStringSelection(dgroup.atsym)
        self.wids['edge'].SetStringSelection(dgroup.edge)

        self.set_nnorm_widget(dgroup.pre_edge_details.nnorm)
        for attr in ('e0', 'edge_step'):
            conf[attr] = getattr(dgroup, attr)
        for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
            conf[attr] = val = getattr(dgroup.pre_edge_details, attr, None)
            if val is not None:
                self.wids[attr].SetValue(val)

        if hasattr(dgroup, 'mback_params'): # from mback
            conf['atsym'] = getattr(dgroup.mback_params, 'atsym')
            conf['edge'] = getattr(dgroup.mback_params, 'edge')
        self.update_config(conf, dgroup=dgroup)
        # print("process updated conf  ", dgroup, conf)
        wx.CallAfter(self.unset_skip_process)


    def get_plot_arrays(self, dgroup):
        lab = plotlabels.norm
        if dgroup is None:
            return

        dgroup.plot_y2label = None
        dgroup.plot_xlabel = plotlabels.energy
        dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab)]

        req_attrs = ['e0', 'norm', 'dmude', 'd2mude', 'pre_edge']

        pchoice = PlotOne_Choices.get(self.plotone_op.GetStringSelection(), 'norm')

        if pchoice in ('mu', 'norm', 'i0', 'flat', 'dmude', 'd2mude'):
            lab = getattr(plotlabels, pchoice)
            dgroup.plot_yarrays = [(pchoice, PLOTOPTS_1, lab)]

        elif pchoice == 'prelines':
            lab = plotlabels.mu
            dgroup.plot_yarrays = [('mu', PLOTOPTS_1, plotlabels.mu),
                                   ('pre_edge', PLOTOPTS_2, 'pre edge'),
                                   ('post_edge', PLOTOPTS_2, 'post edge')]

        elif pchoice == 'norm+d2mude':
            lab = plotlabels.norm
            dgroup.plot_y2label = lab2 = plotlabels.d2mude
            dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab),
                                   ('d2mude', PLOTOPTS_D, lab2)]

        elif pchoice == 'norm+dmude':
            lab = plotlabels.norm
            dgroup.plot_y2label = lab2 = plotlabels.dmude
            dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab),
                                   ('dmude', PLOTOPTS_D, lab2)]
        elif pchoice == 'norm+i0':
            lab = plotlabels.norm
            dgroup.plot_y2label = lab2 = plotlabels.i0
            dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab),
                                   ('i0', PLOTOPTS_D, lab2)]
        elif pchoice == 'norm+flat':
            lab = plotlabels.norm
            dgroup.plot_y2label = lab2 = plotlabels.flat
            dgroup.plot_yarrays = [('norm', PLOTOPTS_1, lab),
                                   ('flat', PLOTOPTS_D, lab2)]
        elif pchoice == 'mback_norm':
            req_attrs.append('mback_norm')
            lab = plotlabels.mu
            if not hasattr(dgroup, 'mback_mu'):
                self.process(dgroup=dgroup, force_mback=True)
            dgroup.plot_yarrays = [('mu', PLOTOPTS_1, lab),
                                   ('mback_mu', PLOTOPTS_2, r'tabulated $\mu(E)$')]

        elif pchoice == 'mback_poly':
            req_attrs.append('mback_norm')
            lab = plotlabels.norm
            if not hasattr(dgroup, 'mback_mu'):
                self.process(dgroup=dgroup, force_mback=True)
            dgroup.plot_yarrays = [('norm_mback', PLOTOPTS_1, 'mback'),
                                   ('norm_poly', PLOTOPTS_2, 'polynomial')]

        elif pchoice == 'area_norm':
            dgroup.plot_yarrays = [('norm_area', PLOTOPTS_1, 'area'),
                                   ('norm_poly', PLOTOPTS_2, 'polynomial')]

        dgroup.plot_ylabel = lab
        needs_proc = False
        for attr in req_attrs:
            needs_proc = needs_proc or (not hasattr(dgroup, attr))

        if needs_proc:
            self.process(dgroup=dgroup, force=True)

        y4e0 = dgroup.yplot = getattr(dgroup, dgroup.plot_yarrays[0][0], dgroup.mu)
        dgroup.plot_extras = []

        popts = {'marker': 'o', 'markersize': 5,
                 'label': '_nolegend_',
                 'markerfacecolor': '#888',
                 'markeredgecolor': '#A00'}

        if self.wids['show_e0'].IsChecked():
            ie0 = index_of(dgroup.energy, dgroup.e0)
            dgroup.plot_extras.append(('marker', dgroup.e0, y4e0[ie0], popts))

        if self.wids['show_pre'].IsChecked() or self.wids['show_norm'].IsChecked():
            popts['markersize'] = 4
            wids = []
            if self.wids['show_pre'].IsChecked():  wids.extend(['pre1', 'pre2'])
            if self.wids['show_norm'].IsChecked():  wids.extend(['norm1', 'norm2'])
            for wid in wids:
                val = self.wids[wid].GetValue()
                ival = min(len(y4e0)-1, index_of(dgroup.energy, dgroup.e0 + val))
                dgroup.plot_extras.append(('marker', dgroup.e0+val, y4e0[ival], popts))

    def plot(self, dgroup, title=None, plot_yarrays=None, yoff=0,
             delay_draw=True, multi=False, new=True, with_extras=True, **kws):

        if self.skip_plotting:
            return
        ppanel = self.controller.get_display(stacked=False).panel

        plotcmd = ppanel.oplot
        if new:
            plotcmd = ppanel.plot

        erange = Plot_EnergyRanges[self.plot_erange.GetStringSelection()]
        self.controller.set_plot_erange(erange)

        groupname = getattr(dgroup, 'groupname', None)
        if groupname is None:
            return

        self.ensure_xas_processed(dgroup, force_mback=True)
        self.get_plot_arrays(dgroup)

        if plot_yarrays is None and hasattr(dgroup, 'plot_yarrays'):
            plot_yarrays = dgroup.plot_yarrays

        popts = self.controller.get_plot_conf()
        popts.update(kws)
        popts['grid'] = popts.pop('show_grid')
        popts['fullbox'] = popts.pop('show_fullbox')

        path, fname = path_split(dgroup.filename)
        if 'label' not in popts:
            popts['label'] = dgroup.plot_ylabel

        zoom_limits = get_zoomlimits(ppanel, dgroup)

        if erange is not None and hasattr(dgroup, 'e0'):
            popts['xmin'] = dgroup.e0 + erange[0]
            popts['xmax'] = dgroup.e0 + erange[1]

        popts['xlabel'] = dgroup.plot_xlabel
        popts['ylabel'] = dgroup.plot_ylabel
        if getattr(dgroup, 'plot_y2label', None) is not None:
            popts['y2label'] = dgroup.plot_y2label

        plot_choices = PlotSel_Choices
        if multi:
            ylabel = self.plotsel_op.GetStringSelection()
            yarray_name = plot_choices.get(ylabel, 'norm')

            if self.is_xasgroup(dgroup):
                ylabel = getattr(plotlabels, yarray_name, ylabel)
            popts['ylabel'] = ylabel

        plot_extras = None
        if new:
            if title is None:
                title = fname
            plot_extras = getattr(dgroup, 'plot_extras', None)

        popts['title'] = title
        popts['show_legend'] = len(plot_yarrays) > 1
        narr = len(plot_yarrays) - 1

        _linewidth = popts['linewidth']
        for i, pydat in enumerate(plot_yarrays):
            yaname, yopts, yalabel = pydat
            popts.update(yopts)
            if yalabel is not None:
                popts['label'] = yalabel
            linewidht = _linewidth
            if 'linewidth' in popts:
                linewidth = popts.pop('linewidth')
            popts['delay_draw'] = delay_draw
            if yaname == 'norm_mback' and not hasattr(dgroup, yaname):
                self.process(dgroup=dgroup, force=True, force_mback=True)
            if yaname == 'i0' and not hasattr(dgroup, yaname):
                dgroup.i0 = np.ones(len(dgroup.xplot))
            plotcmd(dgroup.xplot, getattr(dgroup, yaname)+yoff, linewidth=linewidth, **popts)
            plotcmd = ppanel.oplot

        if with_extras and plot_extras is not None:
            axes = ppanel.axes
            for etype, x, y, opts in plot_extras:
                if etype == 'marker':
                    xpopts = {'marker': 'o', 'markersize': 5,
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

        # set_zoomlimits(ppanel, zoom_limits)
        ppanel.reset_formats()
        set_zoomlimits(ppanel, zoom_limits)
        ppanel.conf.unzoom(full=True, delay_draw=False)
