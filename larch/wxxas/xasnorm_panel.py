#!/usr/bin/env python
"""
XANES Normalization panel
"""
import os
import time
import wx
import numpy as np

from functools import partial

from lmfit.printfuncs import gformat
from larch.math import index_of
from larch.xray import guess_edge, atomic_number
from larch.xafs.xafsutils import guess_energy_units

from larch.wxlib import (BitmapButton, FloatCtrl, FloatSpin, get_icon,
                         SimpleText, pack, Button, HLine, Choice, Check,
                         GridPanel, CEN, RCEN, LCEN, plotlabels)

from larch.wxlib.plotter import last_cursor_pos
from .xas_dialogs import EnergyUnitsDialog
from .taskpanel import TaskPanel, autoset_fs_increment

np.seterr(all='ignore')

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, zorder=3,
                  marker='None', markersize=4)
PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)

PlotOne_Choices = {'Raw \u03BC(E)': 'mu',
                   'Normalized \u03BC(E)': 'norm',
                   '\u03BC(E) + Pre-/Post-edge': 'prelines',
                   'Flattened \u03BC(E)': 'flat',
                   '\u03BC(E) + MBACK tabulated \u03BC(E)': 'mback_norm',
                   'MBACK- + Poly-Normalized \u03BC(E)': 'mback_poly',
                   # 'Area- + Poly-Normalized \u03BC(E)': 'area_norm',
                   'd\u03BC(E)/dE': 'dmude',
                   'Raw \u03BC(E) + d\u03BC(E)/dE': 'mu+dmude',
                   'Normalized \u03BC(E) + d\u03BC(E)/dE': 'norm+dnormde'}

PlotSel_Choices = {'Raw \u03BC(E)': 'mu',
                   'Normalized \u03BC(E)': 'norm',
                   'Flattened \u03BC(E)': 'flat',
                   'd\u03BC(E)/dE (raw)': 'dmude',
                   'd\u03BC(E)/dE (normalized)': 'dnormde'}

PlotOne_Choices_nonxas = {'Raw Data': 'mu',
                          'Derivative': 'dmude',
                          'Data + Derivative': 'norm+dmude'}

PlotSel_Choices_nonxas = {'Raw Data': 'mu', 'Derivative': 'dmude'}

defaults = dict(e0=0, edge_step=None, auto_step=True, auto_e0=True,
                show_e0=True, pre1=-200, pre2=-30, norm1=100, norm2=-10,
                norm_method='polynomial', edge='K', atsym='?',
                nvict=0, nnorm=1,
                plotone_op='Normalized \u03BC(E)',
                plotsel_op='Normalized \u03BC(E)')

class XASNormPanel(TaskPanel):
    """XAS normalization Panel"""
    def __init__(self, parent, controller=None, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='xasnorm_config',
                           config=defaults, **kws)

    def build_display(self):
        panel = self.panel
        self.wids = {}

        self.plotone_op = Choice(panel, choices=list(PlotOne_Choices.keys()),
                                 action=self.onPlotOne, size=(225, -1))
        self.plotsel_op = Choice(panel, choices=list(PlotSel_Choices.keys()),
                                 action=self.onPlotSel, size=(225, -1))

        self.plotone_op.SetSelection(1)
        self.plotsel_op.SetSelection(1)

        plot_one = Button(panel, 'Plot This Group', size=(175, -1),
                          action=self.onPlotOne)

        plot_sel = Button(panel, 'Plot Selected Groups', size=(175, -1),
                          action=self.onPlotSel)

        e0panel = wx.Panel(panel)
        self.wids['auto_e0'] = Check(e0panel, default=True, label='auto?',
                                    action=self.onSet_XASE0)
        self.wids['showe0'] = Check(e0panel, default=True, label='show?',
                                    action=self.onSet_XASE0)
        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(self.wids['auto_e0'], 0, LCEN, 4)
        sx.Add(self.wids['showe0'], 0, LCEN, 4)
        pack(e0panel, sx)


        self.wids['auto_step'] = Check(panel, default=True, label='auto?',
                                      action=self.onNormMethod)

        self.wids['nvict'] = Choice(panel, choices=('0', '1', '2', '3'),
                                    size=(60, -1), action=self.onNormMethod,
                                    default=0)
        self.wids['nnorm'] = Choice(panel, choices=('constant', 'linear',
                                                    'quadratic', 'cubic'),
                                    size=(100, -1), action=self.onNormMethod,
                                    default=1)

        opts = {'size': (100, -1), 'digits': 2, 'increment': 5.0,
                'action': self.onSet_Ranges}

        xas_pre1 = self.add_floatspin('pre1', value=defaults['pre1'], **opts)
        xas_pre2 = self.add_floatspin('pre2', value=defaults['pre2'], **opts)
        xas_norm1 = self.add_floatspin('norm1', value=defaults['norm1'], **opts)
        xas_norm2 = self.add_floatspin('norm2', value=defaults['norm2'], **opts)

        opts = {'digits': 3, 'increment': 0.1, 'value': 0}
        plot_voff = self.add_floatspin('plot_voff',  with_pin=False,
                                       action=self.onVoffset, **opts)


        xas_e0   = self.add_floatspin('e0', action=self.onSet_XASE0Val, **opts)
        xas_step = self.add_floatspin('step', action=self.onSet_XASStep,
                                      with_pin=False, **opts)

        self.wids['norm_method'] = Choice(panel, choices=('polynomial', 'mback'), # , 'area'),
                                          size=(120, -1), action=self.onNormMethod)
        self.wids['norm_method'].SetSelection(0)
        atsyms = ['?'] + self.larch.symtable._xray._xraydb.atomic_symbols
        edges = ('K', 'L3', 'L2', 'L1', 'M5')

        self.wids['atsym'] = Choice(panel, choices=atsyms, size=(75, -1))
        self.wids['edge'] = Choice(panel, choices=edges, size=(60, -1))

        self.wids['is_frozen'] = Check(panel, default=False, label='Freeze Group',
                                       action=self.onFreezeGroup)

        saveconf = Button(panel, 'Save as Default Settings', size=(200, -1),
                          action=self.onSaveConfigBtn)

        def CopyBtn(name):
            return Button(panel, 'Copy', size=(60, -1),
                          action=partial(self.onCopyParam, name))

        add_text = self.add_text
        HLINEWID = 600
        panel.Add(SimpleText(panel, ' XAS Pre-edge subtraction and Normalization',
                             **self.titleopts), dcol=7)

        panel.Add(plot_sel, newrow=True)
        panel.Add(self.plotsel_op, dcol=3)
        panel.Add(SimpleText(panel, '  Vertical offset:'), style=RCEN)
        panel.Add(plot_voff, style=RCEN)

        panel.Add((5, 5), dcol=3, newrow=True)
        panel.Add(SimpleText(panel, 'Copy to Selected Groups:'),
                  style=RCEN, dcol=3)
        panel.Add(plot_one, newrow=True)
        panel.Add(self.plotone_op, dcol=4)
        panel.Add(CopyBtn('plotone_op'), dcol=1, style=RCEN)

        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=6, newrow=True)

        add_text('Element and Edge: ', newrow=True)
        panel.Add(self.wids['atsym'])
        panel.Add(self.wids['edge'], dcol=3)
        panel.Add(CopyBtn('atsym'), dcol=1, style=RCEN)

        add_text('E0 : ')
        panel.Add(xas_e0)
        panel.Add(e0panel, dcol=3)
        panel.Add(CopyBtn('xas_e0'), dcol=1, style=RCEN)

        add_text('Edge Step: ')
        panel.Add(xas_step)
        panel.Add(self.wids['auto_step'], dcol=2)
        panel.Add(CopyBtn('xas_step'), dcol=2, style=RCEN)

        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=6, newrow=True)

        add_text('Pre-edge range: ')
        panel.Add(xas_pre1)
        add_text(' : ', newrow=False)
        panel.Add(xas_pre2, dcol=2)
        panel.Add(CopyBtn('xas_pre'), dcol=1, style=RCEN)

        panel.Add(SimpleText(panel, 'Victoreen order:'), newrow=True)
        panel.Add(self.wids['nvict'], dcol=3)

        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=6, newrow=True)

        add_text('Normalization method: ')
        panel.Add(self.wids['norm_method'], dcol=4)
        panel.Add(CopyBtn('xas_norm'), dcol=1, style=RCEN)

        add_text('Normalization range: ')
        panel.Add(xas_norm1)
        add_text(' : ', newrow=False)
        panel.Add(xas_norm2, dcol=2)
        panel.Add(SimpleText(panel, 'Polynomial Type:'), newrow=True)
        panel.Add(self.wids['nnorm'], dcol=2)

        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=6, newrow=True)
        panel.Add((5, 5), newrow=True)
        panel.Add(self.wids['is_frozen'], newrow=True)
        panel.Add(saveconf, dcol=4)

        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(HLINEWID, 3)), dcol=6, newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((5, 5), 0, LCEN, 3)
        sizer.Add(panel, 0, LCEN, 3)
        sizer.Add((5, 5), 0, LCEN, 3)

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
                for attr in ('e0', 'pre1', 'pre2', 'norm1', 'norm2', 'nnorm'):
                    conf[attr]   = getattr(dgroup.bkg_params, attr, conf[attr])
                conf['auto_step'] = (float(getattr(dgroup.bkg_params, 'fixstep', 0.0))< 0.5)
                conf['edge_step'] = getattr(dgroup.bkg_params, 'step', conf['edge_step'])

        if conf['edge_step'] is None:
            conf['edge_step'] = getattr(dgroup, 'edge_step', conf['edge_step'])
        conf['atsym'] = getattr(dgroup, 'atsym', conf['atsym'])
        conf['edge'] = getattr(dgroup,'edge', conf['edge'])
        if hasattr(dgroup, 'e0') and conf['atsym'] == '?':
            atsym, edge = guess_edge(dgroup.e0, _larch=self.larch)
            conf['atsym'] = atsym
            conf['edge'] = edge

        if hasattr(dgroup, 'mback_params'):
            conf['atsym'] = getattr(dgroup.mback_params, 'atsym', conf['atsym'])
            conf['edge'] = getattr(dgroup.mback_params, 'edge', conf['edge'])

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

            if hasattr(dgroup, 'e0') and opts['atsym'] == '?':
                atsym, edge = guess_edge(dgroup.e0, _larch=self.larch)
                opts['atsym'] = atsym
                opts['edge'] = edge

            self.wids['step'].SetValue(edge_step)
            autoset_fs_increment(self.wids['step'], edge_step)

            self.wids['pre1'].SetValue(opts['pre1'])
            self.wids['pre2'].SetValue(opts['pre2'])
            self.wids['norm1'].SetValue(opts['norm1'])
            self.wids['norm2'].SetValue(opts['norm2'])
            self.wids['nvict'].SetSelection(opts['nvict'])
            self.wids['nnorm'].SetSelection(opts['nnorm'])
            self.wids['showe0'].SetValue(opts['show_e0'])
            self.wids['auto_e0'].SetValue(opts['auto_e0'])
            self.wids['auto_step'].SetValue(opts['auto_step'])
            self.wids['edge'].SetStringSelection(opts['edge'].title())
            self.wids['atsym'].SetStringSelection(opts['atsym'].title())
            self.wids['norm_method'].SetStringSelection(opts['norm_method'].lower())
        else:
            self.plotone_op.SetChoices(list(PlotOne_Choices_nonxas.keys()))
            self.plotsel_op.SetChoices(list(PlotSel_Choices_nonxas.keys()))
            self.plotone_op.SetStringSelection('Raw Data')
            self.plotsel_op.SetStringSelection('Raw Data')
            for k in self.wids.values():
                k.Disable()

        frozen = opts.get('is_frozen', False)
        if hasattr(dgroup, 'is_frozen'):
            frozen = dgroup.is_frozen

        self.wids['is_frozen'].SetValue(frozen)
        self._set_frozen(frozen)
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
        form_opts['norm1'] = self.wids['norm1'].GetValue()
        form_opts['norm2'] = self.wids['norm2'].GetValue()
        form_opts['nnorm'] = int(self.wids['nnorm'].GetSelection())
        form_opts['nvict'] = int(self.wids['nvict'].GetSelection())

        form_opts['plotone_op'] = self.plotone_op.GetStringSelection()
        form_opts['plotsel_op'] = self.plotsel_op.GetStringSelection()
        form_opts['plot_voff'] = self.wids['plot_voff'].GetValue()
        form_opts['show_e0'] = self.wids['showe0'].IsChecked()
        form_opts['auto_e0'] = self.wids['auto_e0'].IsChecked()
        form_opts['auto_step'] = self.wids['auto_step'].IsChecked()

        form_opts['norm_method'] = self.wids['norm_method'].GetStringSelection().lower()
        form_opts['edge'] = self.wids['edge'].GetStringSelection().title()
        form_opts['atsym'] = self.wids['atsym'].GetStringSelection().title()
        return form_opts

    def onNormMethod(self, evt=None):
        method = self.wids['norm_method'].GetStringSelection().lower()
        self.update_config({'norm_method': method})
        if method.startswith('mback'):
            dgroup = self.controller.get_group()
            cur_elem = self.wids['atsym'].GetStringSelection()
            if hasattr(dgroup, 'e0') and cur_elem == 'H':
                atsym, edge = guess_edge(dgroup.e0, _larch=self.larch)
                self.wids['edge'].SetStringSelection(edge)
                self.wids['atsym'].SetStringSelection(atsym)
                self.update_config({'edge': edge, 'atsym': atsym})
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)

    def _set_frozen(self, frozen):
        try:
            dgroup = self.controller.get_group()
            dgroup.is_frozen = frozen
        except:
            pass
        for wattr in ('e0', 'step', 'pre1', 'pre2', 'norm1', 'norm2',
                      'nvict', 'nnorm', 'showe0', 'auto_e0', 'auto_step',
                      'norm_method', 'edge', 'atsym'):

            self.wids[wattr].Enable(not frozen)

    def onFreezeGroup(self, evt=None):
        self._set_frozen(evt.IsChecked())

    def onPlotOne(self, evt=None):
        self.plot(self.controller.get_group())

    def onVoffset(self, evt=None):
        time.sleep(0.01)
        wx.CallAfter(self.onPlotSel)

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

        if yarray_name == 'norm':
            norm_method = self.wids['norm_method'].GetStringSelection().lower()
            if norm_method.startswith('mback'):
                yarray_name = 'norm_mback'
                ylabel = "%s (MBACK)" % ylabel
            elif  norm_method.startswith('area'):
                yarray_name = 'norm_area'
                ylabel = "%s (Area)" % ylabel
        voff = self.wids['plot_voff'].GetValue()
        for ix, checked in enumerate(group_ids):
            yoff = ix * voff
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            plot_yarrays = [(yarray_name, PLOTOPTS_1, dgroup.filename)]
            if dgroup is not None:
                dgroup.plot_extras = []
                self.plot(dgroup, title='', new=newplot, multi=True,
                          yoff=yoff, plot_yarrays=plot_yarrays,
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
        elif name == 'atsym':
            copy_attrs('atsym', 'edge')
        elif name == 'xas_norm':
            copy_attrs('norm_method', 'nnorm', 'norm1', 'norm2')

        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group and not grp.is_frozen:
                self.update_config(opts, dgroup=grp)
                self.fill_form(grp)
                self.process(grp, noskip=True)

    def onSet_XASE0(self, evt=None, value=None):
        "handle setting auto e0 / show e0"
        auto_e0  = self.wids['auto_e0'].GetValue()
        self.update_config({'e0': self.wids['e0'].GetValue(),
                           'auto_e0':self.wids['auto_e0'].GetValue()})
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)

    def onSet_XASE0Val(self, evt=None, value=None):
        "handle setting e0"
        self.wids['auto_e0'].SetValue(0)
        self.update_config({'e0': self.wids['e0'].GetValue(),
                            'auto_e0':self.wids['auto_e0'].GetValue()})
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)

    def onSet_XASStep(self, evt=None, value=None):
        "handle setting edge step"
        edge_step = self.wids['step'].GetValue()
        self.wids['auto_step'].SetValue(0)
        self.update_config({'edge_step': edge_step, 'auto_step': False})
        autoset_fs_increment(self.wids['step'], edge_step)
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)

    def onSet_Ranges(self, evt=None, **kws):
        conf = {}
        for attr in ('pre1', 'pre2', 'norm1', 'norm2'):
            conf[attr] = self.wids[attr].GetValue()
        self.update_config(conf)
        time.sleep(0.01)
        wx.CallAfter(self.onReprocess)

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
            self.wids['auto_e0'].SetValue(0)
        elif opt in ('pre1', 'pre2', 'norm1', 'norm2'):
            self.wids[opt].SetValue(_x-e0)
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
        if not hasattr(dgroup, self.configname):
            return
        form = self.read_form()
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
        __conf = self.get_config(dgroup)
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

        norm_method = form['norm_method'].lower()
        form['normmeth'] = 'poly'
        if force_mback or norm_method.startswith('mback'):
            form['normmeth'] = 'mback'
            copts = [dgroup.groupname]
            copts.append("z=%d" % atomic_number(form['atsym']))
            copts.append("edge='%s'" % form['edge'])
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

        if norm_method.startswith('area'):
            form['normmeth'] = 'area'
            expr = """{group:s}.norm = 1.0*{group:s}.norm_{normmeth:s}
{group:s}.edge_step = 1.0*{group:s}.edge_step_{normmeth:s}"""
            self.larch_eval(expr.format(**form))


        self.make_dnormde(dgroup)

        if form['auto_e0']:
            self.wids['e0'].SetValue(dgroup.e0)
        if form['auto_step']:
            self.wids['step'].SetValue(dgroup.edge_step)
            autoset_fs_increment(self.wids['step'], dgroup.edge_step)

        self.wids['pre1'].SetValue(dgroup.pre_edge_details.pre1)
        self.wids['pre2'].SetValue(dgroup.pre_edge_details.pre2)
        self.wids['norm1'].SetValue(dgroup.pre_edge_details.norm1)
        self.wids['norm2'].SetValue(dgroup.pre_edge_details.norm2)

        self.wids['atsym'].SetStringSelection(dgroup.atsym)
        self.wids['edge'].SetStringSelection(dgroup.edge)

        conf = {}

        for attr in ('e0', 'edge_step'):
            conf[attr] = getattr(dgroup, attr)
        for attr in ('pre1', 'pre2', 'nnorm', 'norm1', 'norm2'):
            conf[attr] = getattr(dgroup.pre_edge_details, attr)

        if hasattr(dgroup, 'mback_params'): # from mback
            conf['atsym'] = getattr(dgroup.mback_params, 'atsym')
            conf['edge'] = getattr(dgroup.mback_params, 'edge')
        self.update_config(conf, dgroup=dgroup)
        wx.CallAfter(self.unset_skip_process)

    def get_plot_arrays(self, dgroup):
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
            self.process(dgroup=dgroup, noskip=True)

        y4e0 = dgroup.ydat = getattr(dgroup, dgroup.plot_yarrays[0][0], dgroup.mu)
        dgroup.plot_extras = []

        if self.wids['showe0'].IsChecked():
            ie0 = index_of(dgroup.energy, dgroup.e0)
            dgroup.plot_extras.append(('marker', dgroup.e0, y4e0[ie0], {}))

    def plot(self, dgroup, title=None, plot_yarrays=None, yoff=0,
             delay_draw=False, multi=False, new=True, zoom_out=True,
             with_extras=True, **kws):

        if self.skip_plotting:
            return
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
        self.get_plot_arrays(dgroup)

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
                print(" -- need norm_mback ! " )
                self.process(dgroup=dgroup, noskip=True, force_mback=True)

            plotcmd(dgroup.xdat, getattr(dgroup, yaname)+yoff, **popts)
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
