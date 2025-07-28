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
from larch.wxlib import (FloatCtrl, FloatSpin, GridPanel,
                         SimpleText, pack, Button, HLine, Choice,
                         TextCtrl, plotlabels, Check, CEN, RIGHT, LEFT)


from larch.xafs.xafsutils import etok, ktoe, FT_WINDOWS
from larch.xafs.pre_edge import find_e0

from .xas_dialogs import EnergyUnitsDialog
from .taskpanel import TaskPanel, update_confval
from .config import ATHENA_CLAMPNAMES, Plot_EnergyRanges

np.seterr(all='ignore')

# plot options:
norm_bkg = '\u03bC(E) + \u03bc0(E) (norm)'
mu_bkg   = '\u03bC(E) + \u03bc0(E) (raw)'
chie    = '\u03c7(E)'
chik    = '\u03c7(k)'
chiq    = 'Filtered \u03c7(k)'
chikq   = '\u03c7(k) + Filtered \u03c7(k)'

chirmag = '|\u03c7(R)|'
chirre  = 'Re[\u03c7(R)]'
chirmr  = '|\u03c7(R)| + Re[\u03c7(R)]'
wavelet = 'EXAFS wavelet'

PlotE_Choices = [norm_bkg, mu_bkg, chie]
PlotK_Choices = [chik, chikq, chiq]
PlotR_Choices = [chirmag, chirre, chirmr, wavelet]
PlotWindowChoices = ['No 2nd Plot', '2', '3', '4', '5']

PLOT_SPACES = ['E', 'k', 'R']

PlotCmds = {mu_bkg:  "plot_bkg({group:s}, norm=False, ",
            norm_bkg:  "plot_bkg({group:s}, norm=True, ",
            chie:    "plot_chie({group:s}, ",
            chik:    "plot_chik({group:s}, ",
            chirmag: "plot_chir({group:s}, show_mag=True, show_real=False, ",
            chirre:  "plot_chir({group:s}, show_mag=False, show_real=True, ",
            chirmr:  "plot_chir({group:s}, show_mag=True, show_real=True, ",
            chiq:    "plot_chiq({group:s}, show_chik=False, ",
            chikq:   "plot_chiq({group:s}, show_chik=True, ",
            wavelet: "plot_wavelet({group:s}, "
}


CLAMPLIST = ('0', '1', '2', '5', '10', '20', '50', '100', '200', '500', '1000',
             '2000', '5000', '10000')

autobk_cmd = """autobk({group:s}, rbkg={rbkg: .3f}, ek0={ek0: .4f},
      kmin={bkg_kmin: .3f}, kmax={bkg_kmax: .3f}, kweight={bkg_kweight: .1f},
      clamp_lo={bkg_clamplo: .1f}, clamp_hi={bkg_clamphi: .1f})"""

xftf_cmd = """xftf({group:s}, kmin={fft_kmin: .3f}, kmax={fft_kmax: .3f}, dk={fft_dk: .3f},
      kweight={fft_kweight: .3f}, window='{fft_kwindow:s}', rmax_out={fft_rmaxout:.3f})"""

xftr_cmd = """xftr({group:s}, rmin={fft_rmin: .3f}, rmax={fft_rmax: .3f},
      dr={fft_dr: .3f}, window='{fft_rwindow:s}')"""


NAMED_PLOTOPTS = {'default': {'plot1_space': 'k',
                              'plot2_space': 'R',
                              'plot_voffset': 0.0,
                              'plot_kweight': 2,
                              'plot_rmax': 8.0,
                              'plot2_win': 'No 2nd Plot',
                              'plot_echoice': 'norm+bkg',
                              'plot_erange': 'full E Range',
                              'plot_kchoice': 'chik',
                              'plot_rchoice': 'mag_chir',
                              'plot_show_kwin': True,
                              'plot_show_rwin': False}
                              }

_cnf = copy.deepcopy(NAMED_PLOTOPTS['default'])
_cnf['plot2_win'] = '2'
_cnf['plot1_space'] = 'k'
_cnf['plot2_space'] = 'R'
NAMED_PLOTOPTS['k and R space'] = _cnf

_cnf = copy.deepcopy(NAMED_PLOTOPTS['default'])
_cnf['plot2_win'] = '2'
_cnf['plot1_space'] = 'E'
_cnf['plot2_space'] = 'R'
_cnf['plot_erange'] = 'E0 -50:+250eV'

NAMED_PLOTOPTS['E and R space'] = _cnf


class EXAFSPanel(TaskPanel):
    """EXAFS Panel"""
    def __init__(self, parent, controller, **kws):

        self.plot_conf = {}
        self.plot_opts = {}
        for key, value in NAMED_PLOTOPTS.items():
            self.plot_opts[key] = value
        self.plot_opts.update(controller.load_exafsplot_config())

        TaskPanel.__init__(self, parent, controller, panel='exafs', **kws)

        self.skip_process = False
        self.last_plot = 'one'
        self.last_process_bkg = {}
        self.last_process_fft = {}
        self.last_process_time = time.time() - 5000


    def build_display(self):
        wids = self.wids
        self.skip_process = True
        defaults = self.get_defaultconfig()
        ppanel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)
        wids['plot_one'] = Button(ppanel, 'Plot Current Group', size=(175, -1),
                              action=self.onPlotOne)

        wids['plot_sel'] = Button(ppanel, 'Plot Selected Groups', size=(175, -1),
                              action=self.onPlotSel)

        wids['plot_voffset'] = FloatSpin(ppanel, value=0, digits=2, increment=0.25,
                                         action=self.onPlot, size=(125, -1))

        wids['plot_kweight'] = FloatSpin(ppanel, value=2, digits=1, increment=1,
                                         action=self.onPlot, size=(90, -1),
                                         min_val=0, max_val=5)

        wids['plot_rmax'] = FloatSpin(ppanel, value=8, digits=1, increment=0.5,
                                      action=self.onPlot, size=(90, -1),
                                      min_val=2, max_val=25)

        wids['plot2_win']  = Choice(ppanel, size=(125, -1), choices=PlotWindowChoices,
                                   action=self.onPlot)
        wids['plot2_win'].SetSelection(0)

        wids['plot_opt']  = Choice(ppanel,  choices=list(self.plot_opts),
                                    size=(175, -1), action=self.onPlotOptSel)

        wids['plot_opt'].SetToolTip('Reuse Saved Plot Choices')

        wids['plot_opt_save'] = TextCtrl(ppanel, value='', size=(175, -1),
                                             action=self.onPlotOptSave)

        wids['plot_echoice'] = Choice(ppanel, choices=PlotE_Choices,
                                      action=self.onPlot, size=(175, -1))
        wids['plot_erange'] = Choice(ppanel, choices=list(Plot_EnergyRanges),
                                         action=self.onPlot,
                                         size=(125, -1))

        wids['plot_kchoice'] = Choice(ppanel, choices=PlotK_Choices,
                                      action=self.onPlot, size=(175, -1))

        wids['plot_rchoice'] = Choice(ppanel, choices=PlotR_Choices,
                                      action=self.onPlot, size=(175, -1))

        for t in (1, 2):
            wids[f'plot{t}_space'] = pan = wx.Panel(ppanel)
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            style = wx.RB_GROUP
            for s in ('E', 'k', 'R'):
                rb = wx.RadioButton(pan, -1, f' {s} ', style=style)
                style = 0
                rb.Bind(wx.EVT_RADIOBUTTON, partial(self.onRadButton, space=t))
                wids[f'plot{t}_rb_{s.lower()}'] = rb
                sizer.Add(rb)
            pack(pan, sizer)

        wids['plot1_rb_k'].SetValue(1)
        wids['plot2_rb_r'].SetValue(1)
        self.plot1_space = 'k'
        self.plot2_space = 'R'

        wids['plot_show_kwin'] = Check(ppanel, default=False, label='show k->R Window',
                                           action=self.onPlot)
        wids['plot_show_rwin'] = Check(ppanel, default=False, label='show R->q Window',
                                            action=self.onPlot)

        wids['plot_on_choose'] = Check(ppanel, default=defaults.get('auto_plot', True),
                                label='Auto-Plot when choosing Current Group?')


        def padd_text(text, dcol=1, newrow=True):
            ppanel.Add(SimpleText(ppanel, text), dcol=dcol, newrow=newrow)

        ppanel.Add(SimpleText(ppanel, 'EXAFS Data Reduction and Fourier Transforms',
                             size=(450, -1),  **self.titleopts), style=LEFT, dcol=6)

        ppanel.Add(wids['plot_one'], newrow=True)
        ppanel.Add(wids['plot_sel'])
        ppanel.Add(wids['plot_on_choose'], dcol=3)

        padd_text('Main Plot: ', newrow=True)
        ppanel.Add(self.wids['plot1_space'])
        padd_text('Vertical offset: ', newrow=False)
        ppanel.Add(wids['plot_voffset'], dcol=2)

        padd_text('Second Plot: ', newrow=True)
        ppanel.Add(self.wids['plot2_space'])
        padd_text('2nd Window: ', newrow=False)
        ppanel.Add(self.wids['plot2_win'], dcol=2)

        padd_text('Energy : ', newrow=True)
        ppanel.Add(wids['plot_echoice'])
        padd_text('Energy Range: ', newrow=False)
        ppanel.Add(wids['plot_erange'], dcol=2)


        padd_text('k: ', newrow=True)
        ppanel.Add(wids['plot_kchoice'])
        padd_text('K weight: ', newrow=False)
        ppanel.Add(wids['plot_kweight'])
        ppanel.Add(wids['plot_show_kwin'])

        padd_text('R: ', newrow=True)
        ppanel.Add(wids['plot_rchoice'])
        padd_text('R Max: ', newrow=False)
        ppanel.Add(wids['plot_rmax'])
        ppanel.Add(wids['plot_show_rwin'])

        padd_text('Use Saved Plot Options: ', newrow=True)
        ppanel.Add(wids['plot_opt'])
        padd_text('Save Options: ', newrow=False)
        ppanel.Add(wids['plot_opt_save'], dcol=2)
        ppanel.pack()

        ####
        panel = self.panel

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        ek0_panel = wx.Panel(panel)
        opts = dict(digits=2, increment=0.1, min_val=0, action=self.onProcess)
        wids['ek0'] = FloatSpin(ek0_panel, **opts)
        wids['show_ek0'] = Check(ek0_panel, default=True, label='show?',
                                 action=self.onShowEk0)
        wids['push_e0'] = Button(ek0_panel, 'Use as Normalization E0', size=(225, -1),
                                 action=self.onPushE0)
        wids['push_e0'].SetToolTip('Use this value for E0 in the Normalization Tab')

        sx = wx.BoxSizer(wx.HORIZONTAL)
        sx.Add(self.wids['ek0'], 0, LEFT, 4)
        sx.Add(self.wids['show_ek0'], 0, LEFT, 4)
        sx.Add(self.wids['push_e0'], 0, LEFT, 4)
        pack(ek0_panel, sx)

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
                                        increment=0.5, digits=1, max_val=20,
                                        action=self.onProcess)

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

        def CopyBtn(name):
            return Button(panel, 'Copy', size=(60, -1),
                          action=partial(self.onCopyParam, name))
        copy_all = Button(panel, 'Copy All Parameters', size=(175, -1),
                          action=partial(self.onCopyParam, 'all'))

        panel.Add((10, 10))
        panel.Add(HLine(panel, size=(600, 3)), dcol=8, newrow=True)

        panel.Add(SimpleText(panel, ' Background subtraction', size=(200, -1),
                             **self.titleopts), dcol=2, style=LEFT, newrow=True)
        panel.Add(SimpleText(panel, 'Copy To Selected Groups:'),
                  style=RIGHT, dcol=3)


        add_text('E k=0: ')
        panel.Add(ek0_panel, dcol=3)
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

        panel.Add(HLine(panel, size=(600,3)), dcol=8, newrow=True)

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

        panel.Add(HLine(panel, size=(600, 3)), dcol=8, newrow=True)

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
        sizer.Add((5, 5), 0, LEFT, 1)
        sizer.Add(ppanel, 0, LEFT, 1)
        sizer.Add(panel, 0, LEFT, 1)
        pack(self, sizer)
        self.skip_process = False

    def onRadButton(self, event=None, space='unknown'):
        label = event.GetEventObject().GetLabel()
        if space == 1:
            self.plot1_space = label.strip().lower()
        elif space == 2:
            self.plot2_space = label.strip().lower()
        self.onPlot()

    def get_config(self, dgroup=None):
        """get and processing configuration for a group (but not from form)"""
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

        for attr in ('bkg_kmin', 'bkg_kmax', 'bkg_kweight',
                    'bkg_clamplo', 'bkg_clamphi', 'fft_kmin',
                    'fft_kmax', 'fft_kweight', 'fft_dk', 'fft_kwindow',
                    'fft_rmin', 'fft_rmax', 'fft_dr', 'fft_rmaxout',
                    'fft_rwindow'):
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

    def read_form(self):
        "read form, return dict of values"
        self.skip_process = True
        conf = self.get_config()
        wids = self.wids
        for attr in ('ek0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                     'bkg_kweight', 'fft_kmin', 'fft_kmax',
                     'fft_kweight', 'fft_dk',  'fft_rmaxout',
                     'fft_rmin', 'fft_rmax', 'fft_dr'):
            conf[attr] = wids[attr].GetValue()

        for attr in ('bkg_clamplo', 'bkg_clamphi', 'fft_kwindow',
                     'fft_rwindow'):
            try:
                val = wids[attr].GetStringSelection()
                if 'clamp' in attr:
                    val = int(val)
                conf[attr] = val
            except:
                print("failed to read exafs attr ", attr)

        time.sleep(0.001)
        self.skip_process = False
        dgroup = self.controller.get_group()
        setattr(dgroup.config, self.configname, conf)
        return conf

    def read_plot_conf(self):
        "read plot choices from form, return dict of values"
        pconf = {}
        wids = self.wids
        for attr in ('plot_voffset', 'plot_kweight', 'plot_rmax'):
            pconf[attr] = wids[attr].GetValue()

        for attr in ('plot2_win', 'plot_echoice', 'plot_erange',
                    'plot_kchoice', 'plot_rchoice'):
            pconf[attr] = wids[attr].GetStringSelection()

        for attr in ('show_ek0', 'plot_show_kwin', 'plot_show_rwin'):
            pconf[attr] = wids[attr].IsChecked()

        pconf['plot1_space'] = self.plot1_space
        pconf['plot2_space'] = self.plot2_space
        self.plot_conf = pconf

    def onSaveConfigBtn(self, evt=None):
        self.set_defaultconfig(self.read_form())

    def onShowEk0(self, evt=None):
        plotter = self.onPlotSel if self.last_plot=='selected' else self.onPlotOne
        wx.CallAfter(plotter)

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
            frozen = getattr(grp, 'is_frozen', False)
            if grp != self.controller.group and not frozen:
                self.update_config(opts, dgroup=grp)
                if set_ek0:
                    grp.ek0 = opts['ek0']
                if set_rbkg:
                    grp.rbkg = opts['rbkg']
                self.process(dgroup=grp, force=True)

    def _set_frozen(self, frozen):
        try:
            dgroup = self.controller.get_group()
            dgroup.is_frozen = frozen
        except:
            pass

        for attr in ('ek0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                     'bkg_kweight', 'bkg_clamplo', 'bkg_clamphi',
                     'fft_kmin', 'fft_kmax', 'fft_kweight', 'fft_dk',
                     'fft_kwindow', 'fft_rmin', 'fft_rmax', 'fft_dr',
                     'fft_rmaxout', 'fft_rwindow'):
            self.wids[attr].Enable(not frozen)

    def onFreezeGroup(self, evt=None):
        self._set_frozen(evt.IsChecked())


    def onRbkg(self, event=None):
        fft_rmin = self.wids['fft_rmin'].GetValue()
        rbkg = self.wids['rbkg'].GetValue()
        self.wids['fft_rmin'].SetValue(max(rbkg, fft_rmin))
        self.onProcess(event=event)

    def onProcess(self, event=None):
        """ handle process events"""
        if self.skip_process or ((time.time() - self.last_process_time) < 0.5):
            return
        self.last_process_time = time.time()
        self.skip_process = True
        self.dgroup = self.controller.get_group()

        conf = getattr(self.dgroup.config, self.configname, None)
        if conf is None:
            conf = self.get_config(dgroup=dgroup)
        if 'ek0' not in conf:
            conf['ek0']  = conf.get('e0', getattr(dgroup, 'e0', -1))

        self.read_form()
        self.process(dgroup=self.dgroup)
        self.skip_process = False
        plotter = self.onPlotSel if self.last_plot=='selected' else self.onPlotOne
        wx.CallAfter(plotter)

    def process(self, dgroup, force=False, **kws):
        conf = {}
        if dgroup is None:
            dgroup = self.controller.get_group()
        if dgroup is None:
            return

        conf = getattr(dgroup.config, self.configname, None)
        if conf is None:
            conf = self.get_config(dgroup=dgroup)
        if 'ek0' not in conf:
            conf['ek0']  = conf.get('e0', getattr(dgroup, 'e0', -1))

        gname = conf.get('group', None)
        if gname is None:
            gname = conf['group'] = dgroup.groupname

        bkgpars = []
        for attr in ('ek0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                     'bkg_kweight', 'bkg_clamplo', 'bkg_clamphi'):
            val = conf.get(attr, 0.0)
            if val is None:
                val = -1.0
            bkgpars.append("%.4f" % val)
        bkgpars = ':'.join(bkgpars)
        lastpars = self.last_process_bkg.get(gname, '')
        if (force or (bkgpars != lastpars) or
              (getattr(dgroup, 'chi', None) is None)):
            self.larch_eval(autobk_cmd.format(**conf))
            self.last_process_bkg[gname] = bkgpars
            self.last_process_fft[gname] = None

        fftpars = [conf['fft_kwindow'], conf['fft_rwindow']]
        for attr in ('fft_kmin', 'fft_kmax', 'fft_kweight', 'fft_dk',
                     'fft_rmin', 'fft_rmax', 'fft_dr', 'fft_rmaxout'):
            fftpars.append("%.4f" % conf.get(attr, 0.0))
        fftpars = ':'.join(fftpars)
        lastpars = self.last_process_fft.get(gname, '')
        # print(f"process  {dgroup=}, fft: {fftpars != lastpars}, {fftpars=}")
        if (force or (fftpars != lastpars) or
             (getattr(dgroup, 'chir_mag', None) is None)):
            self.larch_eval(xftf_cmd.format(**conf))
            self.larch_eval(xftr_cmd.format(**conf))
            self.last_process_fft[gname] = fftpars

    def onPlotOptSave(self, value, event=None):
        name = value.strip()
        if len(name) < 1:
            return
        wids = self.wids
        data = {}
        data['plot1_space'] = self.plot1_space
        data['plot2_space'] = self.plot2_space
        for attr in ('plot_voffset', 'plot_kweight', 'plot_rmax'):
            data[attr] = wids[attr].GetValue()

        for attr in ('plot2_win', 'plot_echoice', 'plot_erange',
                     'plot_kchoice', 'plot_rchoice'):
            data[attr] = wids[attr].GetStringSelection()

        for attr in ('plot_show_kwin', 'plot_show_rwin'):
            data[attr] = wids[attr].IsChecked()

        self.plot_opts[name] = data
        wids['plot_opt'].Clear()
        wids['plot_opt'].SetChoices(list(self.plot_opts))
        wids['plot_opt'].SetStringSelection(name)
        wids['plot_opt_save'].SetValue('')
        self.controller.save_exafsplot_config(self.plot_opts)

    def onPlotOptSel(self, event=None):
        name =  event.GetString()
        data = NAMED_PLOTOPTS['default']
        data.update(self.plot_opts.get(name, {}))
        wids = self.wids
        for t in (1, 2):
            sval = data[f'plot{t}_space'].lower()
            if t == 1:
                self.plot1_space = sval
            else:
                self.plot2_space = sval
            for s in ('e', 'k', 'r'):
                wids[f'plot{t}_rb_{s}'].SetValue(s==sval)

        for attr in ('plot_voffset', 'plot_kweight', 'plot_rmax'):
            wids[attr].SetValue(float(data[attr]))

        for attr in ('plot2_win', 'plot_echoice', 'plot_erange',
                     'plot_kchoice', 'plot_rchoice'):
            wids[attr].SetStringSelection(data[attr])

        for attr in ('plot_show_kwin', 'plot_show_rwin'):
            wids[attr].SetValue(data[attr])

        wx.CallAfter(self.onPlot)

    def onPlot(self, event=None, dgroup=None):
        plotter = self.onPlotSel if self.last_plot=='selected' else self.onPlotOne
        plotter()

    def plot(self, **kws):
        """for compat"""
        self.onPlot(**kws)

    def onPlotOne(self, evt=None):
        dgroup = self.controller.get_group()
        if getattr(dgroup, 'chir_mag', None) is None:
            self.process(dgroup=dgroup, force=True)

        self.read_plot_conf()
        # print("PlotOne ", self.plot_conf)
        self.larch_eval(self._get_plotcmd(dgroup, space=1))

        if self.plot_conf['plot2_win'] in ('2', '3', '4', '5'):
            self.larch_eval(self._get_plotcmd(dgroup, space=2))

        self.last_plot = 'one'
        self.controller.set_focus()

    def _get_plotcmd(self, dgroup, space=1, delay_draw=False, new=True,
                    offset=None, label=None, title=None):

        conf = self.plot_conf
        if space == 1:
            space_label = conf['plot1_space'].lower()
            win = '1'
        elif space == 2:
            space_label = conf['plot2_space'].lower()
            win = conf['plot2_win']

        if title is None:
            title = f"'{dgroup.filename}'"

        opts = {'win': win, 'title': title, 'new': new,
                'delay_draw': delay_draw}

        if label is not None:
            opts['label'] = label
        if offset is not None:
            opts['offset'] = offset
        if space_label == 'e':
            cmd = PlotCmds[conf['plot_echoice']]
            opts['show_ek0'] = conf['show_ek0']
            erange = Plot_EnergyRanges[conf['plot_erange']]
            if erange is not None:
                opts['emin'] = erange[0]
                opts['emax'] = erange[1]
        elif space_label == 'k':
            cmd = PlotCmds[conf['plot_kchoice']]
            opts['show_window'] = conf['plot_show_kwin']
            opts['scale_window'] = False
            opts['kweight'] = conf['plot_kweight']
        elif space_label == 'r':
            cmd = PlotCmds[conf['plot_rchoice']]
            opts['show_window'] = conf['plot_show_rwin']
            opts['scale_window'] = False
            opts['rmax'] = conf['plot_rmax']

        opts = [f"{key}={val}" for key, val in opts.items()]
        cmd = cmd + ', '.join(opts) + ')'
        cmd = cmd.format(group=dgroup.groupname)
        # print("Get Plot Command: ", cmd)
        return cmd


    def onPlotSel(self, evt=None):
        group_ids = self.controller.filelist.GetCheckedStrings()
        if len(group_ids) < 1:
            return

        self.read_plot_conf()
        conf = self.plot_conf
        offset = float(conf['plot_voffset'])
        cmds = []
        title = f"'{len(group_ids)} Groups'"
        for i, checked in enumerate(group_ids):
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            if dgroup is None:
                continue
            self.process(dgroup=dgroup)
            cmds.append(self._get_plotcmd(dgroup, space=1,
                                       delay_draw=True, new=(i==0),
                                       offset=i*offset,
                                       label=f"'{dgroup.filename}'",
                                       title=title))

            if conf['plot2_win'] in ('1', '2', '3', '4', '5'):
                cmds.append(self._get_plotcmd(dgroup, space=2,
                                       delay_draw=True, new=(i==0),
                                       offset=i*offset,
                                       label=f"'{dgroup.filename}'",
                                       title=title))


        cmds.append("redraw(win=1, show_legend=True)")
        if conf['plot2_win'] in ('1', '2', '3', '4', '5'):
            cmds.append("redraw(win=2, show_legend=True)")
        self.larch_eval('\n'.join(cmds))
        self.last_plot = 'selected'
        self.controller.set_focus()
