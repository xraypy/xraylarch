#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import copy
import wx
import numpy as np

from functools import partial

from larch.math import index_of
from larch.wxlib import (BitmapButton, FloatCtrl, FloatSpin, ToggleButton,
                         get_icon, SimpleText, pack, Button, HLine, Choice,
                         TextCtrl, plotlabels, Check, CEN, RIGHT, LEFT)

from larch.xafs.xafsutils import etok, ktoe, FT_WINDOWS
from larch.xafs.pre_edge import find_e0

from .xas_dialogs import EnergyUnitsDialog
from .taskpanel import TaskPanel, update_confval
from .config import ATHENA_CLAMPNAMES, PlotWindowChoices

np.seterr(all='ignore')

# plot options:
mu_bkg  = '\u03bC(E) + \u03bc0(E)'
chie    = '\u03c7(E)'
chik    = '\u03c7(k)'
chikwin = '\u03c7(k) + Window(k)'
chirmag = '|\u03c7(R)|'
chirre  = 'Re[\u03c7(R)]'
chirmr  = '|\u03c7(R)| + Re[\u03c7(R)]'
wavelet = 'EXAFS wavelet'
chir_w  = '\u03c7(R) + Window(R)'
chiq    = 'Filtered \u03c7(k)'
chikq   = '\u03c7(k) + Filtered \u03c7(k)'
noplot  = '<no plot>'

PlotOne_Choices = [mu_bkg, chie, chik, chikwin, chirmag, chirre, chirmr, wavelet,
                   chir_w, chiq, chikq]
PlotAlt_Choices = [noplot] + PlotOne_Choices
PlotSel_Choices = [chie, chik, chirmag, chirre, chiq]


PlotCmds = {mu_bkg:  "plot_bkg({group:s}, show_ek0={show_ek0}",
            chie:    "plot_chie({group:s}",
            chik:    "plot_chik({group:s}, show_window=False, kweight={plot_kweight:.0f}",
            chikwin: "plot_chik({group:s}, show_window=True, kweight={plot_kweight:.0f}",
            chirmag: "plot_chir({group:s}, show_mag=True, show_real=False, rmax={plot_rmax:.1f}",
            chirre:  "plot_chir({group:s}, show_mag=False, show_real=True, rmax={plot_rmax:.1f}",
            chirmr:  "plot_chir({group:s}, show_mag=True, show_real=True, rmax={plot_rmax:.1f}",
            chir_w:  "plot_chir({group:s}, show_mag=True, show_real=True, show_window=True, rmax={plot_rmax:.1f}",
            chiq:    "plot_chiq({group:s}, show_chik=False",
            chikq:   "plot_chiq({group:s}, show_chik=True",
            wavelet: "plot_wavelet({group:s}, rmax={plot_rmax:.1f}",
            noplot: None}


CLAMPLIST = ('0', '1', '2', '5', '10', '20', '50', '100', '200', '500', '1000',
             '2000', '5000', '10000')

autobk_cmd = """autobk({group:s}, rbkg={rbkg: .3f}, ek0={ek0: .4f},
      kmin={bkg_kmin: .3f}, kmax={bkg_kmax: .3f}, kweight={bkg_kweight: .1f},
      clamp_lo={bkg_clamplo: .1f}, clamp_hi={bkg_clamphi: .1f})"""

xftf_cmd = """xftf({group:s}, kmin={fft_kmin: .3f}, kmax={fft_kmax: .3f}, dk={fft_dk: .3f},
      kweight={fft_kweight: .3f}, window='{fft_kwindow:s}', rmax_out={fft_rmaxout:.3f})"""

xftr_cmd = """xftr({group:s}, rmin={fft_rmin: .3f}, rmax={fft_rmax: .3f},
      dr={fft_dr: .3f}, window='{fft_rwindow:s}')"""


class EXAFSPanel(TaskPanel):
    """EXAFS Panel"""
    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller, panel='exafs', **kws)

        self.skip_process = False
        self.last_plot = 'one'
        self.last_process_bkg = {}
        self.last_process_fft = {}
        self.last_process_time = time.time() - 5000

    def build_display(self):
        panel = self.panel
        wids = self.wids
        self.skip_process = True

        wids['plotone_op'] = Choice(panel, choices=PlotOne_Choices,
                                    action=self.onPlotOne, size=(175, -1))
        wids['plotalt_op'] = Choice(panel, choices=PlotAlt_Choices,
                                    action=self.onPlotOne, size=(175, -1))
        wids['plotsel_op'] = Choice(panel, choices=PlotSel_Choices,
                                    action=self.onPlotSel, size=(175, -1))

        wids['plotone_op'].SetStringSelection(chik)
        wids['plotsel_op'].SetStringSelection(chik)
        wids['plotalt_op'].SetStringSelection(noplot)

        plot_one = Button(panel, 'Plot Current Group', size=(175, -1),
                          action=self.onPlotOne)

        plot_sel = Button(panel, 'Plot Selected Groups', size=(175, -1),
                          action=self.onPlotSel)

        ## saveconf = Button(panel, 'Save as Default Settings', size=(200, -1),
        #                  action=self.onSaveConfigBtn)

        wids['plot_voffset'] = FloatSpin(panel, value=0, digits=2, increment=0.25,
                                         action=self.onProcess)
        wids['plot_kweight'] = FloatSpin(panel, value=2, digits=1, increment=1,
                                         action=self.onProcess,
                                         min_val=0, max_val=5)
        wids['plot_kweight_alt'] = FloatSpin(panel, value=2, digits=1, increment=1,
                                             action=self.onProcess,
                                             min_val=0, max_val=5)

        wids['plot_rmax'] = FloatSpin(panel, value=8, digits=1, increment=0.5,
                                             action=self.onProcess,
                                             min_val=2, max_val=20)
        wids['plot_win']  = Choice(panel, size=(60, -1), choices=PlotWindowChoices,
                                   action=self.onProcess)
        wids['plot_win'].SetStringSelection('2')

        ek0_panel = wx.Panel(panel)
        opts = dict(digits=2, increment=0.1, min_val=0, action=self.onProcess)
        wids['ek0'] = FloatSpin(ek0_panel, **opts)
        wids['show_ek0'] = Check(ek0_panel, default=True, label='show?',
                                 action=self.onShowEk0)
        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(self.wids['ek0'], 0, LEFT, 4)
        sx.Add(self.wids['show_ek0'], 0, LEFT, 4)
        pack(ek0_panel, sx)

        wids['push_e0'] = Button(panel, 'Use as Normalization E0', size=(190, -1),
                                 action=self.onPushE0)
        wids['push_e0'].SetToolTip('Use this value for E0 in the Normalization Tab')


        #
        wids['plotopt_name'] = TextCtrl(panel, 'kspace, kw=2', size=(150, -1),
                                        action=self.onPlotOptSave,
                                        act_on_losefocus=False)
        wids['plotopt_name'].SetToolTip('Name this set of Plot Choices')

        self.plotopt_saves = {'kspace, kw=2': {'plotone_op': chik, 'plotsel_op': chik,
                                          'plotalt_op': noplot, 'plot_voffset': 0.0,
                                          'plot_kweight': 2, 'plot_kweight_alt': 2,
                                          'plot_rmax': 8}}

        wids['plotopt_sel']  = Choice(panel, size=(150, -1),
                                      choices=list(self.plotopt_saves.keys()),
                                      action=self.onPlotOptSel)


        opts['max_val'] = 6
        opts['action'] = self.onRbkg
        wids['rbkg'] = FloatSpin(panel, value=1.0, **opts)

        opts['action'] = self.onProcess
        opts['max_val'] = 125
        bkg_kmin = self.add_floatspin('bkg_kmin', value=0, with_pin=True, **opts)
        bkg_kmax = self.add_floatspin('bkg_kmax', value=20, with_pin=True, **opts)
        fft_kmin = self.add_floatspin('fft_kmin', value=0, with_pin=True, **opts)
        fft_kmax = self.add_floatspin('fft_kmax', value=20, with_pin=True, **opts)

        wids['fft_dk'] = FloatSpin(panel, value=3,  **opts)

        opts.update({'increment': 0.1, 'digits': 2, 'max_val': 20})
        fft_rmin = self.add_floatspin('fft_rmin', value=1, with_pin=True, **opts)
        fft_rmax = self.add_floatspin('fft_rmax', value=6, with_pin=True, **opts)

        wids['fft_dr'] = FloatSpin(panel, value=0.5,  **opts)
        wids['fft_rmaxout'] = FloatSpin(panel, value=12, min_val=2,
                                        increment=0.5, digits=1, max_val=20)

        opts.update({'increment': 1, 'digits': 1, 'max_val': 5})
        wids['bkg_kweight'] = FloatSpin(panel, value=2, **opts)
        wids['fft_kweight'] = FloatSpin(panel, value=2, **opts)

        opts = dict(choices=CLAMPLIST, size=(80, -1), action=self.onProcess)
        wids['bkg_clamplo'] = Choice(panel, **opts)
        wids['bkg_clamphi'] = Choice(panel, **opts)

        wids['fft_kwindow'] = Choice(panel, choices=list(FT_WINDOWS),
                                     action=self.onProcess, size=(125, -1))


        wids['fft_rwindow'] = Choice(panel, choices=list(FT_WINDOWS),
                                     action=self.onProcess, size=(125, -1))
        wids['fft_rwindow'].SetStringSelection('Hanning')


        self.wids['is_frozen'] = Check(panel, default=False, label='Freeze Group',
                                       action=self.onFreezeGroup)

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        def CopyBtn(name):
            return Button(panel, 'Copy', size=(60, -1),
                          action=partial(self.onCopyParam, name))
        copy_all = Button(panel, 'Copy All Parameters', size=(175, -1),
                          action=partial(self.onCopyParam, 'all'))


        panel.Add(SimpleText(panel, 'EXAFS Data Reduction and Fourier Transforms',
                             size=(350, -1),  **self.titleopts), style=LEFT, dcol=6)

        panel.Add(plot_sel, newrow=True)
        panel.Add(self.wids['plotsel_op'], dcol=2)

        add_text('Vertical offset: ', newrow=False)
        panel.Add(wids['plot_voffset'],  style=RIGHT)

        panel.Add(plot_one, newrow=True)
        panel.Add(self.wids['plotone_op'], dcol=2)

        add_text('Plot k weight: ', newrow=False)
        panel.Add(wids['plot_kweight'], style=RIGHT)

        add_text('Add Second Plot: ', newrow=True)
        panel.Add(self.wids['plotalt_op'], dcol=2)
        add_text('Plot2 k weight: ', newrow=False)
        panel.Add(wids['plot_kweight_alt'], style=RIGHT)
        add_text('Window for Second Plot: ', newrow=True)
        panel.Add(self.wids['plot_win'], dcol=2)
        add_text('Plot R max: ', newrow=False)
        panel.Add(wids['plot_rmax'], style=RIGHT)

        add_text('Save Plot Options as: ', newrow=True)
        panel.Add(self.wids['plotopt_name'], dcol=2)

        add_text('Use Saved Plot Options: ', dcol=1, newrow=False)
        panel.Add(self.wids['plotopt_sel'], dcol=1)


        panel.Add(HLine(panel, size=(500, 3)), dcol=6, newrow=True)

        panel.Add(SimpleText(panel, ' Background subtraction', size=(200, -1),
                             **self.titleopts), dcol=2, style=LEFT, newrow=True)
        panel.Add(SimpleText(panel, 'Copy To Selected Groups:'),
                  style=RIGHT, dcol=3)


        add_text('E k=0: ')
        panel.Add(ek0_panel, dcol=2)
        panel.Add(wids['push_e0'], dcol=1)
        panel.Add(CopyBtn('ek0'), style=RIGHT)

        add_text('R bkg: ')
        panel.Add(wids['rbkg'])
        panel.Add((10, 10), dcol=2)
        panel.Add(CopyBtn('rbkg'), style=RIGHT)

        add_text('k min: ')
        panel.Add(bkg_kmin)
        panel.Add(SimpleText(panel, 'k max:'), style=LEFT)
        panel.Add(bkg_kmax)
        panel.Add(CopyBtn('bkg_krange'), style=RIGHT)

        add_text('kweight: ', newrow=True)
        panel.Add(wids['bkg_kweight'])
        panel.Add((10, 10), dcol=2)
        panel.Add(CopyBtn('bkg_kweight'), style=RIGHT)

        add_text('Clamps Low E: ', newrow=True)
        panel.Add( wids['bkg_clamplo'])
        add_text('high E: ',  newrow=False)
        panel.Add( wids['bkg_clamphi'])
        panel.Add(CopyBtn('bkg_clamp'), style=RIGHT)

        panel.Add(HLine(panel, size=(500, 3)), dcol=6, newrow=True)

        panel.Add(SimpleText(panel, ' Fourier transform (k->R) ', size=(275, -1),
                             **self.titleopts), dcol=2, style=LEFT, newrow=True)
        panel.Add(SimpleText(panel, 'Copy To Selected Groups:'),
                  style=RIGHT, dcol=3)

        panel.Add(SimpleText(panel, 'k min: '), newrow=True)
        panel.Add(fft_kmin)
        panel.Add(SimpleText(panel, 'k max:'), style=LEFT)
        panel.Add(fft_kmax)
        panel.Add(CopyBtn('fft_krange'), style=RIGHT)

        panel.Add(SimpleText(panel, 'k weight : '), newrow=True)
        panel.Add(wids['fft_kweight'])
        panel.Add((10, 10), dcol=2)
        panel.Add(CopyBtn('fft_kweight'), style=RIGHT)

        panel.Add(SimpleText(panel, 'k window : '), newrow=True)
        panel.Add(wids['fft_kwindow'])
        panel.Add(SimpleText(panel, 'dk : '))
        panel.Add(wids['fft_dk'])
        panel.Add(CopyBtn('fft_kwindow'), style=RIGHT)

        panel.Add(SimpleText(panel, 'R max output: '), newrow=True)
        panel.Add(wids['fft_rmaxout'])
        panel.Add((10, 10), dcol=2)
        panel.Add(CopyBtn('fft_rmaxout'), style=RIGHT)

        panel.Add(HLine(panel, size=(500, 3)), dcol=6, newrow=True)

        panel.Add(SimpleText(panel, ' Back Fourier transform (R->q) ', size=(275, -1),
                             **self.titleopts), dcol=2, style=LEFT, newrow=True)
        panel.Add(SimpleText(panel, 'Copy To Selected Groups:'),
                  style=RIGHT, dcol=3)

        panel.Add(SimpleText(panel, 'R min: '), newrow=True)
        panel.Add(fft_rmin)

        panel.Add(SimpleText(panel, 'R max:'), style=LEFT)
        panel.Add(fft_rmax)
        panel.Add(CopyBtn('fft_rrange'), style=RIGHT)

        panel.Add(SimpleText(panel, 'R window : '), newrow=True)
        panel.Add(wids['fft_rwindow'])
        panel.Add(SimpleText(panel, 'dR : '))
        panel.Add(wids['fft_dr'])

        panel.Add(CopyBtn('fft_rwindow'), style=RIGHT)
        panel.Add((10, 10), newrow=True)
        panel.Add(self.wids['is_frozen'], dcol=1, newrow=True)
        panel.Add(copy_all, dcol=5, style=RIGHT)

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((10, 10), 0, LEFT, 3)
        sizer.Add(panel, 1, LEFT, 3)
        pack(self, sizer)
        self.skip_process = False

    def get_config(self, dgroup=None):
        """get and set processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()
        if dgroup is None:
            return self.get_defaultconfig()

        conf = getattr(dgroup.config, self.configname,
                       self.get_defaultconfig())

        # update config from callargs - last call arguments
        callargs = getattr(dgroup, 'callargs', None)
        if callargs is not None:
            bkg_callargs = getattr(callargs, 'autobk', None)
            if bkg_callargs is not None:
                for attr in ('rbkg', 'ek0'):
                    update_confval(conf, bkg_callargs, attr)
                for attr in ('kmin', 'kmax', 'kweight'):
                    update_confval(conf, bkg_callargs, attr, pref='bkg_')
                conf['bkg_clamplo'] = bkg_callargs.get('clamp_lo', 1)
                conf['bkg_clamphi'] = bkg_callargs.get('clamp_hi', 20)

            ftf_callargs = getattr(callargs, 'xftf', None)
            if ftf_callargs is not None:
                conf['fft_kwindow'] = ftf_callargs.get('window', 'Hanning')
                conf['fft_rmaxout'] = ftf_callargs.get('rmax_out', 12)
                for attr in ('kmin', 'kmax', 'dk', 'kweight'):
                    update_confval(conf, ftf_callargs, attr, pref='fft_')

            ftr_callargs = getattr(callargs, 'xftr', None)
            if ftr_callargs is not None:
                conf['fft_rwindow'] = ftr_callargs.get('window', 'Hanning')
                for attr in ('rmin', 'rmax', 'dr'):
                    update_confval(conf, ftr_callargs, attr, pref='fft_')

        ek0 = getattr(dgroup, 'ek0', conf.get('ek0', None))
        if ek0 is None:
            nconf = getattr(dgroup.config, 'xasnorm', {'e0': None})
            ek0 = nconf.get('e0',  getattr(dgroup, 'e0', None))
            if ek0 is None:
                ek0 = min(dgroup.energy)

        if getattr(dgroup, 'ek0', None) is None:
            dgroup.ek0 = ek0

        kmax = etok(max(dgroup.energy) - ek0)

        bkg_kmax = conf.get('bkg_kmax', -1)
        if bkg_kmax < 0 or bkg_kmax > kmax:
            conf['bkg_kmax'] = 0.25*int(kmax*4.0 + 1.0)

        fft_kmax = conf.get('fft_kmax', -1)
        if fft_kmax < 0 or fft_kmax > kmax:
            conf['fft_kmax'] = 0.25*int(kmax*4.0 - 1.0)

        fft_rmin = conf.get('fft_rmin', -1)
        if fft_rmin:
            conf['fft_rmin'] = conf['rbkg']

        setattr(dgroup.config, self.configname, conf)
        return conf

    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)
        self.dgroup = dgroup
        if not (hasattr(dgroup, 'norm') and hasattr(dgroup, 'e0')):
            self.parent.process_normalization(dgroup)

        self.skip_process = True
        wids = self.wids
        ek0 = getattr(dgroup, 'ek0', None)
        if ek0 is None:
            ek0 = dgroup.ek0 = getattr(dgroup, 'e0', None)
        if ek0 is None:
            ek0 = dgroup.ek0 = dgroup.e0 = find_e0(dgroup)
        if ek0 is None:
            print("cannot determine E0 for this group")
            return

        rbkg = getattr(dgroup, 'rbkg', None)
        if rbkg is None:
            rkbg = dgroup.rbkg = opts.get('rbkg', 1.0)

        for attr in ('ek0', 'rbkg'):
            wids[attr].SetValue(getattr(dgroup, attr))

        for attr in ('bkg_kmin', 'bkg_kmax', 'bkg_kweight', 'fft_kmin',
                     'fft_kmax', 'fft_kweight', 'fft_dk', 'fft_rmaxout',
                     ):
            try:
                wids[attr].SetValue(float(opts.get(attr)))
            except:
                pass
        for attr in ('fft_kwindow',):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])


        for attr in ('bkg_clamplo', 'bkg_clamphi'):
            val = opts.get(attr, 0)
            try:
                val = float(val)
            except:
                if isinstance(val, str):
                    val = ATHENA_CLAMPNAMES.get(val.lower(), 0)
            try:
                wids[attr].SetStringSelection("%d" % int(val))
            except:
                pass

        frozen = opts.get('is_frozen', False)
        if hasattr(dgroup, 'is_frozen'):
            frozen = dgroup.is_frozen

        self.wids['is_frozen'].SetValue(frozen)
        self._set_frozen(frozen)

        self.skip_process = False

    def read_form(self, dgroup=None, as_copy=False):
        "read form, return dict of values"
        skip_save = self.skip_process
        self.skip_process = True
        if dgroup is None:
            dgroup = self.controller.get_group()
        self.dgroup = dgroup

        conf = self.get_config()
        if dgroup is not None:
            conf['group'] = dgroup.groupname

        wids = self.wids
        for attr in ('ek0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                     'bkg_kweight', 'fft_kmin', 'fft_kmax',
                     'fft_kweight', 'fft_dk',  'fft_rmaxout',
                     'fft_rmin', 'fft_rmax', 'fft_dr',
                     'plot_kweight', 'plot_rmax',
                     'plot_kweight_alt', 'plot_voffset'):
            conf[attr] = wids[attr].GetValue()

        for attr in ('bkg_clamplo', 'bkg_clamphi', 'plot_win'):
            conf[attr] = int(wids[attr].GetStringSelection())

        for attr in ('fft_kwindow', 'fft_rwindow', 'plotone_op',
                     'plotsel_op', 'plotalt_op'):
            conf[attr] = wids[attr].GetStringSelection()
        conf['show_ek0'] = wids['show_ek0'].IsChecked()

        time.sleep(0.001)
        self.skip_process = skip_save
        if as_copy:
            conf = copy.deepcopy(conf)
        if dgroup is not None:
            setattr(dgroup.config, self.configname, conf)
        return conf

    def onSaveConfigBtn(self, evt=None):
        self.set_defaultconfig(self.read_form())

    def onShowEk0(self, evt=None):
        print("show ek0 ", evt)


    def onPushE0(self, evt=None):
        conf = self.read_form()
        dgroup = self.controller.get_group()
        if dgroup is not None:
            nconf = getattr(dgroup.config, 'xasnorm', {'e0': None})
            nconf['auto_e0'] = False
            nconf['e0'] = dgroup.e0 = conf['ek0']

    def onCopyParam(self, name=None, evt=None):
        conf = self.read_form()
        opts = {}
        def copy_attrs(*args):
            return {a: conf[a] for a in args}
        name = str(name)
        set_ek0 = set_rbkg = False
        if name == 'all':
            opts = copy_attrs( 'ek0', 'rbkg', 'bkg_kweight', 'fft_kweight',
                               'bkg_kmin', 'bkg_kmax', 'bkg_clamplo',
                               'bkg_clamphi', 'fft_kmin', 'fft_kmax',
                               'fft_kwindow', 'fft_dk', 'fft_rmin',
                               'fft_rmax', 'fft_rmaxout', 'fft_rwindow',
                               'fft_dr')
            set_ek0 = True
            set_rbkg = True

        elif name in ('ek0', 'rbkg', 'bkg_kweight', 'fft_kweight'):
            opts = copy_attrs(name)
            if name == 'ek0':
                set_ek0 = True
            elif name == 'rbkg':
                set_rbkg = True
        elif name == 'bkg_krange':
            opts = copy_attrs('bkg_kmin', 'bkg_kmax')
        elif name == 'bkg_clamp':
            opts = copy_attrs('bkg_clamplo', 'bkg_clamphi')
        elif name == 'fft_krange':
            opts = copy_attrs('fft_kmin', 'fft_kmax')
        elif name == 'fft_kwindow':
            opts = copy_attrs('fft_kwindow', 'fft_dk')
        elif name == 'fft_rrange':
            opts = copy_attrs('fft_rmin', 'fft_rmax')
        elif name == 'fft_rmaxout':
            opts = copy_attrs('fft_rmaxout',)
        elif name == 'fft_rwindow':
            opts = copy_attrs('fft_rwindow', 'fft_dr')

        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            grp = self.controller.get_group(groupname)
            if grp != self.controller.group and not grp.is_frozen:
                self.update_config(opts, dgroup=grp)
                if set_ek0:
                    grp.ek0 = opts['ek0']
                if set_rbkg:
                    grp.rbkg = opts['rbkg']
                self.process(dgroup=grp, read_form=False)


    def _set_frozen(self, frozen):
        try:
            dgroup = self.controller.get_group()
            dgroup.is_frozen = frozen
        except:
            pass

        for attr in ('ek0', 'rbkg', 'bkg_kmin', 'bkg_kmax', 'bkg_kweight',
                     'fft_kmin', 'fft_kmax', 'fft_kweight', 'fft_dk',
                     'fft_rmin', 'fft_rmax', 'fft_dr',
                     'bkg_clamplo', 'bkg_clamphi', 'fft_kwindow'):
            self.wids[attr].Enable(not frozen)

    def onFreezeGroup(self, evt=None):
        self._set_frozen(evt.IsChecked())


    def onRbkg(self, event=None):
        self.wids['fft_rmin'].SetValue(self.wids['rbkg'].GetValue())
        self.onProcess(event=event)

    def onProcess(self, event=None):
        """ handle process events"""
        if self.skip_process or ((time.time() - self.last_process_time) < 0.5):
            return
        self.last_process_time = time.time()
        self.skip_process = True
        self.process(dgroup=self.dgroup, read_form=True)
        self.skip_process = False
        plotter = self.onPlotSel if self.last_plot=='selected' else self.onPlotOne
        wx.CallAfter(plotter)

    def process(self, dgroup=None, read_form=True, force=False, **kws):
        conf = {}
        if dgroup is not None:
            self.dgroup = dgroup
            conf = getattr(dgroup.config, self.configname, None)
            if conf is None:
                conf = self.get_config(dgroup=dgroup)
            if 'ek0' not in conf:
                conf['ek0']  = conf.get('e0', getattr(dgroup, 'e0', -1))

        if read_form:
            conf.update(self.read_form())

        conf.update(kws)
        if dgroup is None or 'fft_kwindow' not in conf:
            return

        conf['group'] = dgroup.groupname

        try:
            txt = autobk_cmd.format(**conf)
        except:
            conf.update(self.read_form())
            txt = autobk_cmd.format(**conf)

        bkgpars = []
        for attr in ('ek0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                     'bkg_kweight', 'bkg_clamplo', 'bkg_clamphi'):
            val = conf.get(attr, 0.0)
            if val is None:
                val = -1.0
            bkgpars.append("%.3f" % val)
        bkgpars = ':'.join(bkgpars)
        lastpars = self.last_process_bkg.get(self.dgroup.groupname, '')
        if force or (bkgpars != lastpars):
            self.larch_eval(autobk_cmd.format(**conf))
            self.last_process_bkg[self.dgroup.groupname] = bkgpars
            self.last_process_fft[self.dgroup.groupname] = ''

        fftpars = [conf['fft_kwindow'], conf['fft_rwindow']]
        for attr in ('fft_kmin', 'fft_kmax', 'fft_kweight', 'fft_dk',
                     'fft_rmin', 'fft_rmax', 'fft_dr', 'fft_rmaxout'):
            fftpars.append("%.3f" % conf.get(attr, 0.0))
        fftpars = ':'.join(fftpars)
        if fftpars != self.last_process_fft.get(self.dgroup.groupname, ''):
            self.larch_eval(xftf_cmd.format(**conf))
            self.larch_eval(xftr_cmd.format(**conf))
            self.last_process_fft[self.dgroup.groupname] = fftpars

        setattr(dgroup.config, self.configname, conf)

    def plot(self, dgroup=None):
        if self.skip_plotting:
            return
        self.onPlotOne(dgroup=dgroup)


    def onPlotOptSave(self, name=None, event=None):
        data = {}
        if name is None or len(name) < 1:
            name = f"view {len(self.plotopt_saves)+1}"

        name = name.strip()
        for attr in ('plot_voffset', 'plot_kweight',
                     'plot_kweight_alt', 'plot_rmax'):
            data[attr] = self.wids[attr].GetValue()

        for attr in ('plotone_op', 'plotsel_op', 'plotalt_op'):
            data[attr] = self.wids[attr].GetStringSelection()
        self.plotopt_saves[name] = data

        choices = list(reversed(self.plotopt_saves.keys()))
        self.wids['plotopt_sel'].SetChoices(choices)
        self.wids['plotopt_sel'].SetSelection(0)


    def onPlotOptSel(self, event=None):
        name =  event.GetString()
        data = self.plotopt_saves.get(name, None)
        if data is not None:
            for attr in ('plot_voffset', 'plot_kweight',
                         'plot_kweight_alt', 'plot_rmax'):
                self.wids[attr].SetValue(data[attr])

            for attr in ('plotone_op', 'plotsel_op', 'plotalt_op'):
                self.wids[attr].SetStringSelection(data[attr])

            self.plot()


    def onPlotOne(self, evt=None, dgroup=None):
        if self.skip_plotting:
            return
        conf = self.read_form(as_copy=True)
        if dgroup is not None:
            self.dgroup = dgroup
            conf['group'] = dgroup.groupname
        self.process(dgroup=self.dgroup)
        conf['title'] = '"%s"' % self.dgroup.filename

        # print(" onPlotOne ", conf['plotone_op'])
        cmd = PlotCmds[conf['plotone_op']] + ", win=1, title={title:s})"
        # 2nd plot
        cmd2 =  PlotCmds[conf['plotalt_op']]
        if cmd2 is not None:
            cmd2 = cmd2.replace('plot_kweight', 'plot_kweight_alt')
            cmd2 = cmd2 + ", win={plot_win:d}, title={title:s})"
            cmd = "%s\n%s" % (cmd, cmd2)
            self.controller.get_display(win=2)

        # print(" onPlotOne ",   cmd.format(**conf))
        self.larch_eval(cmd.format(**conf))
        self.last_plot = 'one'

        self.controller.set_focus()


    def onPlotSel(self, evt=None):
        if self.skip_plotting:
            return
        group_ids = self.controller.filelist.GetCheckedStrings()
        if len(group_ids) < 1:
            return

        conf = self.read_form(as_copy=True)
        bcmd = PlotCmds[conf['plotsel_op']]
        conf['new'] = 'True'
        conf.pop('ek0') # don't copy ek0 to all groups
        offset = conf['plot_voffset']
        for i, checked in enumerate(group_ids):
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            if dgroup is not None:
                conf['group'] = dgroup.groupname
                conf['label'] = dgroup.filename
                conf['offset'] = offset * i
                if not hasattr(dgroup, 'chir_mag'):
                    self.process(dgroup=dgroup, force=True, read_form=False, **conf)

                extra = """, offset={offset:.3f}, win=1, delay_draw=True,
    label='{label:s}', new={new:s})"""
                cmd = "%s%s" % (bcmd, extra)
                self.larch_eval(cmd.format(**conf))
                conf['new'] = 'False'

        self.larch_eval("redraw(win=1, show_legend=True)")
        self.last_plot = 'selected'

        self.controller.set_focus()
