#!/usr/bin/env python
"""
XANES Normalization panel
"""
import time
import wx
from copy import deepcopy
import numpy as np

from functools import partial
from xraydb import guess_edge, atomic_number, xray_edge
from pyshortcuts import gformat
from larch import Group
from larch.utils import file2groupname
from larch.xafs.xafsutils import guess_energy_units
from larch.xafs.pre_edge import find_e0

from larch.wxlib import (FloatSpin, SimpleText, pack, Button, HLine,
                         Choice, Check, RIGHT, LEFT, plotlabels)

from .xas_dialogs import EnergyUnitsDialog
from .taskpanel import TaskPanel, autoset_fs_increment
from .config import (make_array_choice, EDGES, ATSYMS, PREEDGE_FORMS,
                     NNORM_CHOICES, NNORM_STRINGS, NORM_METHODS,
                     Plot_EnergyRanges)

np.seterr(all='ignore')

PLOTOPTS_1 = dict(style='solid', marker='None')
PLOTOPTS_2 = dict(style='short dashed', zorder=3, marker='None')
PLOTOPTS_D = dict(style='solid', zorder=2, side='right', marker='None')

Plot_Choices1 = make_array_choice(['mu','norm', 'flat', 'dmude'])
Plot_Choices2 = make_array_choice(['noplot', 'prelines',
                                   'dmude', 'd2mude', 'i0',
                                   'mback_mu', 'norm'])

Plot_EnergyOffsets = ['0 (absolute energy)',
                      'E0 for Group',
                      'Nominal E0 (element/edge)']

FSIZE = 120
FSIZEBIG = 175

def get_auto_nnorm(norm1, norm2):
    "autoamatically set nnorm from range"
    nrange = abs(norm2 - norm1)
    nnorm = 2
    if nrange < 300:
        nnorm = 1
    if nrange < 30:
        nnorm = 0
    return nnorm

class XASNormPanel(TaskPanel):
    """XAS normalization Panel"""
    def __init__(self, parent, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller, panel='xasnorm', **kws)

    def build_display(self):
        defaults = self.get_defaultconfig()
        panel = self.panel
        self.wids = wids = {}
        self.last_plot_type = 'one'

        trow = wx.Panel(panel)

        opts = {'size': (190, -1)}
        wids['plot_sel'] = Button(trow, 'Plot Selected Groups',
                                  action=self.onPlotSel, **opts)
        wids['plot_one'] = Button(trow, 'Plot Current Group',
                                  action=self.onPlotOne, **opts)

        opts['action'] = self.onPlotEither
        opts['default'] = 1
        wids['plot_choice1'] = Choice(trow, choices=list(Plot_Choices1), **opts)

        opts['default'] = 0
        wids['plot_choice2'] = Choice(trow, choices=list(Plot_Choices2), **opts)
        wids['plot_enoff'] = Choice(trow, choices=Plot_EnergyOffsets, **opts)
        opts['size'] = (150, -1)
        wids['plot_erange'] = Choice(trow, choices=list(Plot_EnergyRanges), **opts)

        opts = {'digits': 2, 'increment': 0.05, 'value': 0, 'size': (FSIZE, -1)}
        plot_voff = self.add_floatspin('plot_voff', with_pin=False,
                                               parent=trow,
                                               action=self.onPlotSel,
                                               max_val=10000, min_val=-10000,
                                               **opts)

        erange_lab = wx.StaticText(parent=trow, label=' Energy Range:', size=(150, -1))
        voff_lab = wx.StaticText(parent=trow, label=' Y Offset:', size=(150, -1))

        enoff_lab = wx.StaticText(parent=trow, label=' Energy Offset:', size=(175, -1))
        plot1_lab = wx.StaticText(parent=trow, label=' Main Plot Array:', size=(175, -1))
        plot2_lab = wx.StaticText(parent=trow, label=' With [Current Group]:', size=(175, -1))

        self.wids['plot_on_choose'] = Check(trow, default=defaults.get('auto_plot', True),
                                label='Auto-Plot when choosing Current Group?')

        tsizer = wx.GridBagSizer(3, 3)
        tsizer.Add(wids['plot_one'],     (0, 0), (1, 1), LEFT, 2)
        tsizer.Add(wids['plot_sel'],     (0, 1), (1, 1), LEFT, 2)
        tsizer.Add(wids['plot_on_choose'], (0, 2), (1, 2), LEFT, 2)

        tsizer.Add(plot1_lab,            (1, 0), (1, 1), LEFT, 2)
        tsizer.Add(wids['plot_choice1'], (1, 1), (1, 1), LEFT, 2)
        tsizer.Add(erange_lab,           (1, 2), (1, 1), RIGHT, 2)
        tsizer.Add(wids['plot_erange'],  (1, 3), (1, 1), RIGHT, 2)
        tsizer.Add(plot2_lab,            (2, 0), (1, 1), LEFT, 2)
        tsizer.Add(wids['plot_choice2'], (2, 1), (1, 1), LEFT, 2)
        tsizer.Add(enoff_lab,            (3, 0), (1, 1), LEFT, 2)
        tsizer.Add(wids['plot_enoff'],   (3, 1), (1, 1), LEFT, 2)
        tsizer.Add(voff_lab,             (3, 2), (1, 1), RIGHT, 2)
        tsizer.Add(plot_voff,            (3, 3), (1, 1), RIGHT, 2)

        pack(trow, tsizer)

        # atom row
        atpanel = wx.Panel(panel)
        opts = {'size': (100, -1), 'action': self.onAtSymEdge}
        self.wids['atsym']  = Choice(atpanel, choices=ATSYMS, **opts)
        self.wids['edge']   = Choice(atpanel, choices=EDGES, **opts)
        self.wids['e0_nominal']  = SimpleText(atpanel, label='nominal E0=       ',
                                                     size=(175, -1))

        sat = wx.BoxSizer(wx.HORIZONTAL)
        sat.Add(self.wids['atsym'], 0, LEFT, 4)
        sat.Add(self.wids['edge'], 0, LEFT, 4)
        sat.Add(self.wids['e0_nominal'], 0, LEFT, 4)
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
                                       action=self.onAuto_XASStep)
        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(xas_step, 0, LEFT, 4)
        sx.Add(self.wids['auto_step'], 0, LEFT, 4)
        pack(step_panel, sx)

        # step rows
        nnorm_panel = wx.Panel(panel)
        self.wids['nnorm'] = Choice(nnorm_panel, choices=list(NNORM_CHOICES),
                                    size=(150, -1), action=self.onNormMethod,
                                    default=2)
        self.wids['auto_nnorm'] = Check(nnorm_panel, default=True, label='auto?',
                                    action=self.onAuto_NNORM)

        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(self.wids['nnorm'], 0, LEFT, 4)
        sx.Add(self.wids['auto_nnorm'], 0, LEFT, 4)
        pack(nnorm_panel, sx)

        self.wids['energy_ref'] = Choice(panel, choices=['None'],
                                         action=self.onEnergyRef, size=(325, -1))

        self.wids['nvict'] = Choice(panel, choices=('0', '1', '2', '3'),
                                    size=(150, -1), action=self.onNormMethod,
                                    default=0)
        self.wids['npre'] = Choice(panel, choices=list(PREEDGE_FORMS),
                                          size=(150, -1), action=self.onNormMethod)
        self.wids['npre'].SetSelection(1)


        opts = {'size': (FSIZE, -1), 'digits': 2, 'increment': 5.0,
                'action': self.onSet_Ranges,
                'min_val':-99000, 'max_val':99000}

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

        compare_norms = Button(panel, 'Compare Normalization Methods', size=(225, -1),
                          action=self.onCompareNorm)

        def CopyBtn(name):
            return Button(panel, 'Copy', size=(60, -1),
                          action=partial(self.onCopyParam, name))

        copy_all = Button(panel, 'Copy All Parameters', size=(175, -1),
                          action=partial(self.onCopyParam, 'all'))

        add_text = self.add_text
        HLINEWID = 700
        panel.Add(SimpleText(panel, 'XAS Pre-edge subtraction and Normalization',
                             size=(650, -1), **self.titleopts), style=LEFT, dcol=4)
        panel.Add(trow, dcol=5, newrow=True)

        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=4, newrow=True)
        add_text('XAS Data:')
        # panel.Add(use_auto, dcol=1)
        panel.Add(SimpleText(panel, 'Copy to Selected Groups:'), style=RIGHT, dcol=3)

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

        add_text('Pre-edge Type:')
        panel.Add(self.wids['npre'], dcol=2)
        add_text('Victoreen order:')
        panel.Add(self.wids['nvict'], dcol=2)

        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=4, newrow=True)

        add_text('Normalization : ')
        panel.Add(self.wids['norm_method'], dcol=1)
        panel.Add(compare_norms)
        panel.Add(CopyBtn('xas_norm'), dcol=1, style=RIGHT)

        add_text('Norm Energy range: ')
        panel.Add(nor_panel, dcol=2)
        add_text('Polynomial Type:')
        panel.Add(nnorm_panel, dcol=2)

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

        conf = deepcopy(self.controller.config[self.configname])
        if hasattr(dgroup, 'config'):
            conf.update(getattr(dgroup.config, self.configname, {}))
        else:
            dgroup.config = Group()
            setattr(dgroup.config, self.configname, {})

        if conf.get('edge_step', None) is None:
            conf['edge_step'] = getattr(dgroup, 'edge_step', 1)

        conf['atsym'] = getattr(dgroup, 'atsym', '?')
        conf['edge'] = getattr(dgroup,'edge', 'K')
        if hasattr(dgroup, 'e0') and conf['atsym'] == '?':
            atsym, edge = guess_edge(dgroup.e0)
            dgroup.atsym = conf['atsym'] = atsym
            dgroup.edge =  conf['edge'] = edge

        try:
            conf['e0_nominal'] = e0_nom = xray_edge(conf['atsym'] , conf['edge']).energy
            self.wids['e0_nominal'].SetLabel(f'nominal E0={e0_nom:.2f} eV')
        except:
            conf['e0_nominal'] = -1

        fname = getattr(dgroup, 'filename', None)
        if fname is None:
            fname = getattr(dgroup, 'groupname', None)
            if fname is None:
                fname = file2groupname('unknown_group',
                                        symtable=self._larch.symtable)

        conf['energy_ref'] = getattr(dgroup, 'energy_ref', fname)

        if conf['energy_ref'] in (None, 'None'):
            conf['energy_ref'] = fname

        conf['energy_shift'] = getattr(dgroup,'energy_shift', conf['energy_shift'])
        setattr(dgroup.config, self.configname, conf)
        return conf

    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)
        self.skip_process = True
        if self.is_xasgroup(dgroup):
            groupnames = list(self.controller.file_groups.keys())
            self.wids['energy_ref'].SetChoices(groupnames)
            eref = opts.get('energy_ref', 'no_energy_ref')

            for key, val in self.controller.file_groups.items():
                if eref in (val, key):
                    self.wids['energy_ref'].SetStringSelection(key)

            self.wids['e0'].SetValue(opts.get('e0', -1))
            edge_step = opts.get('edge_step', 1.0)
            if opts['atsym'] == '?' and hasattr(dgroup, 'atsym'):
                self.set_atom_edge(dgroup.atsym, getattr(dgroup, 'edge', 'K'))

            self.wids['step'].SetValue(edge_step)
            autoset_fs_increment(self.wids['step'], edge_step)
            for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
                val = opts.get(attr, None)
                if val is not None:
                    self.wids[attr].SetValue(val)
            self.set_nnorm_widget(opts.get('nnorm'))

            xasmode = getattr(dgroup, 'xasmode', 'unknown')
            if xasmode.startswith('calc'):
                opts['npre'] = 0
            self.wids['energy_shift'].SetValue(opts['energy_shift'])
            self.wids['nvict'].SetStringSelection("%d" % opts['nvict'])
            self.wids['npre'].SetSelection(opts['npre'])
            self.wids['show_e0'].SetValue(opts['show_e0'])
            self.wids['auto_e0'].SetValue(opts['auto_e0'])
            self.wids['auto_nnorm'].SetValue(opts.get('auto_nnorm', 0))
            self.wids['auto_step'].SetValue(opts['auto_step'])

            self.wids['edge'].SetStringSelection(opts['edge'].title())
            self.wids['atsym'].SetStringSelection(opts['atsym'].title())

            self.wids['e0_nominal'].SetLabel(f"nominal E0={opts['e0_nominal']:.2f} eV")

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
        self.skip_process = False

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
        self.update_config({'nnorm': nnorm})

    def unset_skip_process(self):
        self.skip_process = False

    def read_form(self):
        "read form, return dict of values"
        form_opts = {}
        form_opts['e0'] = self.wids['e0'].GetValue()
        form_opts['edge_step'] = self.wids['step'].GetValue()
        for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
            val = self.wids[attr].GetValue()
            if val == 0:
                val = None
            form_opts[attr] = val
        form_opts['energy_shift'] = self.wids['energy_shift'].GetValue()

        form_opts['nnorm'] = NNORM_CHOICES.get(self.wids['nnorm'].GetStringSelection(), 1)
        form_opts['nvict'] = int(self.wids['nvict'].GetStringSelection())
        form_opts['npre']  = PREEDGE_FORMS.get(self.wids['npre'].GetStringSelection(), 1)
        form_opts['plot_choice1'] = self.wids['plot_choice1'].GetStringSelection()
        form_opts['plot_choice2'] = self.wids['plot_choice2'].GetStringSelection()
        form_opts['plot_voff'] = self.wids['plot_voff'].GetValue()
        for ch in ('show_e0', 'show_pre', 'show_norm', 'auto_e0',
                   'auto_step', 'auto_nnorm'):
            form_opts[ch] = self.wids[ch].IsChecked()

        form_opts['norm_method'] = self.wids['norm_method'].GetStringSelection().lower()
        form_opts['edge'] = self.wids['edge'].GetStringSelection().title()
        form_opts['atsym'] = self.wids['atsym'].GetStringSelection().title()
        form_opts['energy_ref'] = self.wids['energy_ref'].GetStringSelection()
        return form_opts

    def onAtSymEdge(self, event=None):
        self.set_atom_edge(self.wids['atsym'].GetStringSelection().title(),
                           self.wids['edge'].GetStringSelection().title())

    def set_atom_edge(self, atsym, edge):
        "set atom symbol and edge, aiming for consistency"
        dgroup = self.controller.get_group()
        if dgroup is None:
            return
        if atsym == '?' and getattr(dgroup, 'e0', None) is not None:
            atsym, edge = guess_edge(dgroup.e0)

        dgroup.atsym = atsym
        dgroup.edge = edge

        self.update_config({'atsym': atsym, 'edge': edge}, dgroup=dgroup)
        try:
            e0_nom = xray_edge(atsym , edge).energy
            self.update_config({'e0_nominal': e0_nom}, dgroup=dgroup)
            self.wids['e0_nominal'].SetLabel(f'nominal E0={e0_nom:.2f} eV')
        except:
            pass
        if hasattr(dgroup, 'mback_params'):
            dgroup.mback_params.atsym = atsym
            dgroup.mback_params.edge = edge
        # print("End of Set Atom ", atsym, edge)

    def onNormMethod(self, evt=None):
        method = self.wids['norm_method'].GetStringSelection().lower()
        dgroup = self.controller.get_group()
        nnorm  = NNORM_CHOICES.get(self.wids['nnorm'].GetStringSelection(), 1)
        if nnorm is None:
            nnorm = get_auto_nnorm(self.wids['norm1'].GetValue(),
                                   self.wids['norm2'].GetValue())

        npre_sel = self.wids['npre'].GetStringSelection()
        npre = 0 if npre_sel.lower().startswith('con') else 1
        nvict = int(self.wids['nvict'].GetStringSelection())
        self.update_config({'norm_method': method, 'nnorm': nnorm,
                            'nvict': nvict, 'npre': npre},
                            dgroup=dgroup)
        if method.startswith('mback'):
            cur_elem = self.wids['atsym'].GetStringSelection()
            if hasattr(dgroup, 'e0') and cur_elem in ('H', '?'):
                atsym, edge = guess_edge(dgroup.e0)
                self.wids['edge'].SetStringSelection(edge)
                self.wids['atsym'].SetStringSelection(atsym)
        self.onReprocess()

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
        dgroup.energy_ref = eref = self.wids['energy_ref'].GetStringSelection()
        self.update_config({'energy_ref': eref}, dgroup=dgroup)


    def onAuto_NNORM(self, evt=None):
        if evt.IsChecked():
            nnorm = get_auto_nnorm(self.wids['norm1'].GetValue(),
                                   self.wids['norm2'].GetValue())
            self.set_nnorm_widget(nnorm)
            self.wids['auto_nnorm'].SetValue(0)
            time.sleep(0.001)
            self.onReprocess()

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
        self.wids['npre'].SetSelection(1)
        for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
            self.wids[attr].SetValue(defaults[attr])
        self.onReprocess()

    def onCompareNorm(self, evt=None):
        dgroup = self.controller.get_group()
        groupname = dgroup.groupname
        self.ensure_xas_processed(dgroup, force_mback=True)
        title = f'{dgroup.filename}'

        self.larch_eval(f"""plot({groupname}.energy, {groupname}.norm_poly,
   new=True, delay_draw=True, label='norm (poly)', linewidth=3, show_legend=True,
   {title=},  xlabel=r'{plotlabels.energy}', ylabel=r'{plotlabels.norm}')
plot({groupname}.energy, {groupname}.norm_mback, label='norm (MBACK)',
      linewidth=3, new=False, delay_draw=False)""")

        self.controller.set_focus()

    def onCopyParam(self, name=None, evt=None):
        conf = self.get_config()
        dgroup = self.controller.get_group()
        self.update_config(conf)
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
            if grp != dgroup and not getattr(grp, 'is_frozen', False):
                self.update_config(opts, dgroup=grp)
                for key, val in opts.items():
                    if hasattr(grp, key):
                        setattr(grp, key, val)
                self.process(grp, force=True)

    def onAuto_XASE0(self, evt=None):
        if evt.IsChecked():
            dgroup = self.controller.get_group()
            find_e0(dgroup)
            self.update_config({'e0': dgroup.e0})
            self.onReprocess()

    def onAuto_XASStep(self, evt=None):
        dgroup = self.controller.get_group()
        if dgroup is None:
            return
        if evt.IsChecked():
            self.process(dgroup=dgroup)
            self.update_config({'edge_step': dgroup.edge_step})


    def onSet_XASE0(self, evt=None, value=None):
        "handle setting auto e0 / show e0"
        self.update_config({'e0': self.wids['e0'].GetValue(),
                           'auto_e0':self.wids['auto_e0'].GetValue()})
        self.onReprocess()

    def onSet_XASE0Val(self, evt=None, value=None):
        "handle setting e0"
        self.wids['auto_e0'].SetValue(0)
        self.update_config({'e0': self.wids['e0'].GetValue(),
                            'auto_e0':self.wids['auto_e0'].GetValue()})
        self.onReprocess()

    def onSet_EnergyShift(self, evt=None, value=None):
        conf = self.get_config()
        dgroup = self.controller.get_group()
        eshift = self.wids['energy_shift'].GetValue()
        dgroup.energy_shift = conf['energy_shift'] = eshift
        if conf['auto_energy_shift']:
            _eref = getattr(dgroup, 'energy_ref', '<;no eref;>')
            _gname = dgroup.groupname
            self.stale_groups = []
            for fname, gname in self.controller.file_groups.items():
                this = self.controller.get_group(gname)
                if _gname != gname and _eref == getattr(this, 'energy_ref', None):
                    this.energy_shift = this.config.xasnorm['energy_shift'] = eshift
                    self.stale_groups.append(this)

        self.onReprocess()

    def onSet_XASStep(self, evt=None, value=None):
        "handle setting edge step"
        edge_step = self.wids['step'].GetValue()
        if edge_step < 0:
            self.wids['step'].SetValue(abs(edge_step))
        self.wids['auto_step'].SetValue(0)
        self.onReprocess()
        time.sleep(0.01)

        self.update_config({'edge_step': abs(edge_step), 'auto_step': False})
        autoset_fs_increment(self.wids['step'], abs(edge_step))


    def onSet_Ranges(self, evt=None, **kws):
        conf = {}
        for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
            conf[attr] = self.wids[attr].GetValue()
        self.update_config(conf)
        self.onReprocess()

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
        self.onReprocess()

    def onReprocess(self, evt=None, value=None, **kws):
        "handle request reprocess"
        if self.skip_process:
            return
        try:
            dgroup = self.controller.get_group()
        except TypeError:
            return
        if dgroup is None:
            return
        if not hasattr(dgroup.config, self.configname):
            return
        self.process(dgroup=dgroup)
        if self.stale_groups is not None:
            for g in self.stale_groups:
                self.process(dgroup=g, force=True)
            self.stale_groups = None
        self.onPlotEither(process=False)

    # def process(self, dgroup=None, force_mback=False, force=False, use_form=True, **kws):
    def process(self, dgroup=None, force_mback=False, force=False):
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
                dgroup.energy = res.energy*1.0
                dgroup.xplot = dgroup.energy*1.0
        dgroup.energy_units = en_units

        if not hasattr(dgroup, 'e0'):
            e0 = find_e0(dgroup)
        if form['atsym'] == '?':
            self.set_atom_edge('?', '?')

        cmds = []
        # test whether the energy shift is 0 or is different from the current energy shift:
        ediff = 1e15  # just a huge energy step/shift
        eshift_current = getattr(dgroup, 'energy_shift', ediff)
        eshift = form.get('energy_shift', ediff)
        e1 = getattr(dgroup, 'energy', [ediff])
        e2 = getattr(dgroup, 'energy_orig', None)
        gname = dgroup.groupname


        if (not isinstance(e2, np.ndarray) or (len(e1) != len(e2))):
            cmds.append("{group:s}.energy_orig = {group:s}.energy[:]")

        if (isinstance(e1, np.ndarray) and isinstance(e2, np.ndarray) and
            len(e1) == len(e2)):
            ediff = (e1-e2).min()

        if abs(eshift-ediff) > 1.e-5 or abs(eshift-eshift_current) > 1.e-5:
            if abs(eshift) > 1e15:
                eshift = 0.0
            cmds.extend(["{group:s}.energy_shift = {eshift:.4f}",
                         "{group:s}.energy = {group:s}.xplot = {group:s}.energy_orig + {group:s}.energy_shift"])

        if len(cmds) > 0:
            self.larch_eval(('\n'.join(cmds)).format(group=gname, eshift=eshift))

        e0 = form['e0']
        edge_step = form['edge_step']
        copts = [gname]
        if not form['auto_e0']:
            if e0 < max(dgroup.energy) and e0 > min(dgroup.energy):
                copts.append("e0=%.4f" % float(e0))

        if not form['auto_step']:
            copts.append("step=%s" % gformat(float(edge_step)))

        xasmode = getattr(dgroup, 'xasmode', 'unknown')
        if xasmode.startswith('calc'):
            copts.append('iscalc=True')
        for attr in ('pre1', 'pre2', 'nvict', 'npre', 'nnorm', 'norm1', 'norm2'):
            val = form[attr]
            if val is None or val == 'auto':
                val = 'None'
            elif attr in ('nvict', 'nnorm', 'npre'):
                if val in NNORM_CHOICES:
                    val = NNORM_CHOICES[val]
                val = int(val)
                if attr == 'npre' and xasmode.startswith('calc'):
                    val=0
            else:
                val = f"{float(val):.2f}"
            copts.append(f"{attr}={val}")

        self.larch_eval("pre_edge(%s) " % (', '.join(copts)))
        self.larch_eval("{group:s}.norm_poly = 1.0*{group:s}.norm".format(**form))
        if not hasattr(dgroup, 'e0'):
            self.skip_process = False
            dgroup.mu = dgroup.yplot * 1.0
            return

        norm_method = form['norm_method'].lower()
        form['normmeth'] = 'poly'

        dgroup.journal.add_ifnew('normalization_method', norm_method)
        if ((not xasmode.startswith('calc')) and
            (force_mback or norm_method.startswith('mback'))):
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
                # print("AUTO STEP  ..")
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
            # conf['atsym'] = atsym
            # conf['edge'] = edge
        try:
            self.wids['atsym'].SetStringSelection(dgroup.atsym)
            self.wids['edge'].SetStringSelection(dgroup.edge)
        except:
            pass

        for attr in ('e0', 'edge_step'):
            conf[attr] = getattr(dgroup, attr)

        if not hasattr(dgroup, 'pre_edge_details'):
            dgroup.pre_edge_details = Group(nnorm=None)
        self.set_nnorm_widget(getattr(dgroup.pre_edge_details,
                                      'nnorm', None))
        for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
            conf[attr] = val = getattr(dgroup.pre_edge_details, attr, None)
            if val is not None:
                self.wids[attr].SetValue(val)

        self.update_config(conf, dgroup=dgroup)

        self.skip_process = False

    def get_plot_energy_offset(self, dgroup):
        selection = self.wids['plot_enoff'].GetSelection()
        en_off = 0.0
        if selection == 1 and hasattr(dgroup, 'e0'):
            en_off = dgroup.e0
        elif selection == 2:
            form = self.read_form()
            atsym = getattr(dgroup, 'atsym', form['atsym'])
            edge = getattr(dgroup, 'edge', form['edge'])
            try:
                en_off = xray_edge(atsym, edge).energy
            except:
                pass
        return en_off

    def ensure_xas_processed(self, dgroup, force_mback=False):
        req_attrs = ['e0', 'mu', 'dmude', 'norm', 'pre_edge']
        if force_mback:
            req_attrs.extend(['norm_mback', 'mback_mu'])
        if not all([hasattr(dgroup, attr) for attr in req_attrs]):
            # print("Ensure XAS Process for mback:  ", dgroup, force_mback)
            self.process(dgroup, force=True, force_mback=force_mback)

    def plot(self, dgroup=None, **kws):
        if dgroup is None:
            self.onPlotEither(**kws)
        else:
            self.onPlotOne(dgroup=dgroup, **kws)

    def onPlotEither(self, evt=None, process=True, **kws):
        plt = self.onPlotSel if self.last_plot_type=='multi' else self.onPlotOne
        plt(process=process, **kws)

    def onPlotOne(self, evt=None, dgroup=None, process=True, **kws):
        if self.skip_plotting:
            return
        self.last_plot_type = 'one'

        if dgroup is None:
            dgroup = self.controller.get_group()

        groupname = getattr(dgroup, 'groupname', None)
        if groupname is None:
            return

        plot1 = Plot_Choices1[self.wids['plot_choice1'].GetStringSelection()]
        show_norm = (plot1 == 'norm')
        show_flat = (plot1 == 'flat')
        show_deriv = (plot1 == 'dmude')

        plot2 = Plot_Choices2[self.wids['plot_choice2'].GetStringSelection()]
        show_pre  = (plot2 == 'prelines')
        show_post = (plot2 == 'prelines')
        with_i0   = (plot2 == 'i0')
        with_deriv = (plot2 == 'dmude')
        with_deriv2 = (plot2 == 'd2mude')
        with_norm = (plot2 == 'norm')
        with_mback = (plot2 == 'mback_mu')
        if with_mback and not hasattr(dgroup, 'mback_mu'):
            self.ensure_xas_processed(dgroup, force_mback=True)

        show_e0 = self.wids['show_e0'].IsChecked()

        marker_energies = []
        if self.wids['show_pre'].IsChecked():
            marker_energies.append(self.wids['pre1'].GetValue())
            marker_energies.append(self.wids['pre2'].GetValue())
        if self.wids['show_norm'].IsChecked():
            marker_energies.append(self.wids['norm1'].GetValue())
            marker_energies.append(self.wids['norm2'].GetValue())

        title = f'{dgroup.filename}'

        erange = Plot_EnergyRanges[self.wids['plot_erange'].GetStringSelection()]
        self.controller.set_plot_erange(erange)
        emin = emax = None
        if erange is not None:
            emin, emax = erange

        en_offset = self.get_plot_energy_offset(dgroup)

        self.larch_eval(f"""plot_mu({groupname}, {show_norm=}, {show_flat=}, {show_deriv=},
    {show_e0=}, {show_pre=}, {show_post=}, {with_deriv=}, {with_deriv2=},
    {with_i0=}, {with_norm=}, {with_mback=}, {title=},
    {emin=}, {emax=}, {marker_energies=}, {en_offset=})""")

        self.controller.set_focus()

    def onPlotSel(self, evt=None, process=None, **kws):
        self.last_plot_type = 'multi'
        group_ids = self.controller.filelist.GetCheckedStrings()
        if len(group_ids) < 1:
            return
        last_id = group_ids[-1]

        groupname = self.controller.file_groups[str(last_id)]
        dgroup = self.controller.get_group(groupname)

        title = self.wids['plot_choice1'].GetStringSelection()
        plot1 = Plot_Choices1[title]
        show_norm = (plot1 == 'norm')
        show_flat = (plot1 == 'flat')
        show_deriv = (plot1 == 'dmude')

        erange = Plot_EnergyRanges[self.wids['plot_erange'].GetStringSelection()]
        self.controller.set_plot_erange(erange)
        emin = emax = None
        if erange is not None:
            emin, emax = erange

        en_offset = self.get_plot_energy_offset(dgroup)

        cmds = []
        new = True
        for gid in group_ids:
            delay_draw = gid !=  last_id
            groupname = self.controller.file_groups[str(gid)]
            dgroup = self.controller.get_group(groupname)
            en_offset = self.get_plot_energy_offset(dgroup)
            # print(f"{gid=}, {groupname=}, {delay_draw=}, {en_offset=}")
            cmds.append(f"""plot_mu({groupname}, {show_norm=}, {show_flat=}, {show_deriv=},
            {title=}, {emin=}, {emax=}, {en_offset=}, {new=}, {delay_draw=}, label='{gid}')""")
            new = False

        self.larch.eval( '\n'.join(cmds) )
        self.controller.set_focus()
