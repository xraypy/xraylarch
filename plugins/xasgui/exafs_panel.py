#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import wx
import numpy as np

from functools import partial
from collections import OrderedDict

from wx.lib.agw.floatspin import FloatSpin, EVT_FLOATSPIN

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check,
                     GridPanel, CEN, RCEN, LCEN, Font)

from larch.utils import index_of
from larch.wxlib import BitmapButton, FloatCtrl
from larch_plugins.wx.icons import get_icon
from larch_plugins.xasgui.xas_dialogs import EnergyUnitsDialog
from larch_plugins.xasgui.taskpanel import TaskPanel

from larch_plugins.xafs.xafsutils import etok, ktoe
from larch_plugins.xafs.xafsplots import plotlabels

np.seterr(all='ignore')

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, zorder=3,
                  marker='None', markersize=4)
PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=2,
                  side='right', marker='None', markersize=4)


PlotOne_Choices = ('mu(E) + bkg(E)', 'chi(k)', 'chi(k) + Window',
                   '|chi(R)|', 'Re[chi(R)]', '|chi(R)| + Re[chi(R)]')

PlotSel_Choices = ('chi(k)', '|chi(R)|', 'Re[chi(R)]')

FTWINDOWS = ('Kaiser-Bessel', 'Hanning', 'Gaussian', 'Sine', 'Parzen', 'Welch')
KWLIST = ('0', '1', '2', '3', '4')
CLAMPLIST = ('0', '1', '2', '5', '10', '20', '50', '100', '200', '500', '1000')

autobk_cmd = """autobk({group:s}, rbkg={rbkg: .3f}, e0={e0: .4f},
      kmin={bkg_kmin: .3f}, kmax={bkg_kmax: .3f}, kweight={bkg_kweight: .1f},
      clamp_lo={bkg_clamplo: .1f}, clamp_hi={bkg_clamphi: .1f})"""

xftf_cmd = """xftf({group:s}, kmin={fft_kmin: .3f}, kmax={fft_kmax: .3f},
      kweight={fft_kweight: .3f}, dk={fft_dk: .3f}, window={kwindow:s})"""


def default_exafs_config():
    return dict(e0=0, rbkg=1, bkg_kmin=0, bkg_kmax=None, bkg_clamplo=2,
                bkg_clamphi=5, bkg_kweight=1, fft_kmin=2, fft_kmax=None,
                fft_kwindow='Kaiser-Bessel', fft_dk=4, fft_kweight=2,
                plot_kweight=2, plotone_op='chi(k)', plotsel_op='chi(k)')


class EXAFSPanel(TaskPanel):
    """EXAFS Panel"""
    title = 'EXAFS panel'
    configname = 'exafs_config'

    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller, **kws)
        self.skip_process = False
        self.last_process_pars = None

    def build_display(self):
        self.SetFont(Font(10))
        titleopts = dict(font=Font(11), colour='#AA0000')

        panel = self.panel
        wids = self.wids
        btns = self.btns
        self.skip_process = True

        wids['plotone_op'] = Choice(panel, choices=PlotOne_Choices,
                                    action=self.onPlotOne, size=(200, -1))
        wids['plotsel_op'] = Choice(panel, choices=PlotSel_Choices,
                                    action=self.onPlotSel, size=(200, -1))

        wids['plot_kweight'] = Choice(panel, choices=KWLIST,
                                      action=self.onPlotOne, size=(100, -1))


        wids['plotone_op'].SetSelection(0)
        wids['plotsel_op'].SetSelection(0)

        plot_one = Button(panel, 'Plot This Group', size=(150, -1),
                          action=self.onPlotOne)

        plot_sel = Button(panel, 'Plot Selected Groups', size=(150, -1),
                          action=self.onPlotSel)

        saveconf = Button(panel, 'Save as Default Settings', size=(200, -1),
                          action=self.onSaveConfigBtn)

        def CopyBtn(name):
            return Button(panel, 'Copy', size=(50, -1),
                          action=partial(self.onCopyParam, name))

        opts = dict(size=(90, -1), digits=2, increment=0.1)
        wids['e0'] = FloatSpin(panel, -1, **opts)

        opts['size'] = (90, -1)
        wids['rbkg'] = FloatSpin(panel, -1, value=1.0,
                                 min_val=0, max_val=25, **opts)
        wids['bkg_kmin'] = FloatSpin(panel, -1, value=0,
                                 min_val=0, max_val=125, **opts)

        wids['bkg_kmax'] = FloatSpin(panel, -1, min_val=0, max_val=125, **opts)

        wids['fft_kmin'] = FloatSpin(panel, -1, value=0,
                                 min_val=0, max_val=125, **opts)

        wids['fft_kmax'] = FloatSpin(panel, -1, min_val=0, max_val=125, **opts)

        wids['fft_dk'] = FloatSpin(panel, -1, value=3,
                                 min_val=0, max_val=125, **opts)

        opts['increment'] = opts['digits'] = 1
        wids['bkg_kweight'] = FloatSpin(panel, -1, value=1,
                                 min_val=0, max_val=8, **opts)

        wids['fft_kweight'] = FloatSpin(panel, -1, value=1,
                                 min_val=0, max_val=8, **opts)

        for name in ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax', 'bkg_kweight'):
            wids[name].Bind(EVT_FLOATSPIN, self.process)

        for name in ('fft_kmin', 'fft_kmax', 'fft_dk', 'fft_kweight'):
            wids[name].Bind(EVT_FLOATSPIN, self.process)

        for name in ('bkg_kmin', 'bkg_kmax', 'fft_kmin', 'fft_kmax'):
            bb = BitmapButton(panel, get_icon('plus'),
                              action=partial(self.onSelPoint, opt=name),
                              tooltip='use last point selected from plot')
            btns[name] = bb
        opts = dict(choices=CLAMPLIST, size=(70, -1), action=self.process)
        wids['bkg_clamplo'] = Choice(panel, **opts)
        wids['bkg_clamphi'] = Choice(panel, **opts)
        wids['kwindow'] = Choice(panel, choices=list(FTWINDOWS),
                                 action=self.process, size=(100, -1))

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        panel.Add(SimpleText(panel, ' EXAFS Processing', **titleopts), dcol=5)

        panel.Add(SimpleText(panel, ' Copy to Selected Groups?'), style=RCEN, dcol=3)


        panel.Add(plot_sel, newrow=True)
        panel.Add(wids['plotsel_op'], dcol=6)

        panel.Add(plot_one, newrow=True)
        panel.Add(wids['plotone_op'], dcol=5)
        panel.Add(CopyBtn('plotone_op'), style=RCEN)

        add_text('K weight for plot: ', newrow=True)
        panel.Add(wids['plot_kweight'], dcol=4)

        panel.Add(HLine(panel, size=(250, 2)), dcol=7, newrow=True)

        panel.Add(SimpleText(panel, ' Background subtraction',
                             **titleopts), dcol=6, newrow=True)

        add_text('E0: ', dcol=2, newrow=True)
        panel.Add(wids['e0'], dcol=4)
        panel.Add(CopyBtn('e0'), style=RCEN)


        add_text('R_bkg: ', dcol=2, newrow=True)
        panel.Add(wids['rbkg'], dcol=4)
        panel.Add(CopyBtn('rbkg'), style=RCEN)

        add_text('K weight (for bkg): ', dcol=2, newrow=True)
        panel.Add(wids['bkg_kweight'], dcol=4)
        panel.Add(CopyBtn('bkg_kweight'), style=RCEN)


        add_text('K range: ')
        panel.Add(btns['bkg_kmin'])
        panel.Add(wids['bkg_kmin'])

        add_text(' : ', newrow=False)
        panel.Add(btns['bkg_kmax'])
        panel.Add(wids['bkg_kmax'])
        panel.Add(CopyBtn('bkg_krange'), style=RCEN)


        add_text('Clamps Low k: ', dcol=2, newrow=True)
        panel.Add( wids['bkg_clamplo'])
        panel.Add(SimpleText(panel, 'high k: '), dcol=2)
        panel.Add( wids['bkg_clamphi'])
        panel.Add(CopyBtn('bkg_clamps'), style=RCEN)

        panel.Add(HLine(panel, size=(250, 2)), dcol=7, newrow=True)

        panel.Add(SimpleText(panel, ' Fourier transform',
                             **titleopts), dcol=6, newrow=True)


        panel.Add(SimpleText(panel, 'K range: '), newrow=True)
        panel.Add(btns['fft_kmin'])
        panel.Add(wids['fft_kmin'])

        panel.Add(SimpleText(panel, ' : '))
        panel.Add(btns['fft_kmax'])
        panel.Add(wids['fft_kmax'])
        panel.Add(CopyBtn('fft_krange'), style=RCEN)

        panel.Add(SimpleText(panel, 'K weight : '), dcol=2, newrow=True)
        panel.Add(wids['fft_kweight'], dcol=4)
        panel.Add(CopyBtn('fft_kweight'), style=RCEN)

        panel.Add(SimpleText(panel, 'K window : '), dcol=2, newrow=True)
        panel.Add(wids['kwindow'])
        panel.Add(SimpleText(panel, ' dk : '), dcol=2)
        panel.Add(wids['fft_dk'])
        panel.Add(CopyBtn('fft_kwin'), style=RCEN)

        panel.Add(HLine(panel, size=(250, 2)), dcol=7, newrow=True)

        panel.Add(saveconf, dcol=4, newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(panel, 1, LCEN, 3)
        pack(self, sizer)
        self.skip_process = False


    def customize_config(self, config, dgroup=None):
        if 'e0' not in config:
            config.update(default_exafs_config())
        if dgroup is not None:
            dgroup.xasnorm_config = config
        return config

    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)
        self.dgroup = dgroup
        self.skip_process = True
        wids = self.wids
        self.skip_process = True
        for attr in ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                     'bkg_kweight', 'fft_kmin', 'fft_kmax',
                     'fft_kweight', 'fft_dk'):
            val = getattr(dgroup, attr, None)

            if val is None:
                val = opts.get(attr, -1)
                if 'kmax' in attr:
                    val = 0.25 + etok(max(dgroup.energy) - dgroup.e0)
            wids[attr].SetValue(val)

        for attr in ('bkg_clamplo', 'bkg_clamphi', 'plot_kweight'):
            wids[attr].SetStringSelection("%d" % opts.get(attr, 0))

        for attr in ('kwindow', 'plotone_op', 'plotsel_op'):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])

        self.skip_process = False
        self.process()

    def read_form(self):
        "read form, return dict of values"
        self.dgroup = self.controller.get_group()
        form_opts = {'group': self.dgroup.groupname}

        wids = self.wids
        for attr in ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                     'bkg_kweight', 'fft_kmin', 'fft_kmax',
                     'fft_kweight', 'fft_dk'):
            form_opts[attr] = wids[attr].GetValue()

        for attr in ('bkg_clamplo', 'bkg_clamphi', 'plot_kweight'):
            form_opts[attr] = int(wids[attr].GetStringSelection())

        for attr in ('kwindow', 'plotone_op', 'plotsel_op'):
            form_opts[attr] = wids[attr].GetStringSelection()

        return form_opts


    def onSaveConfigBtn(self, evt=None):
        conf = self.controller.larch.symtable._sys.xas_viewer
        opts = {}
        opts.update(getattr(conf, 'exafs', {}))
        opts.update(self.read_form())
        conf.xas_norm = opts

    def onCopyParam(self, name=None, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())
        opts = {}

    def process(self, event=None):
        """ handle process of XAS data
        """
        if self.skip_process:
            return

        self.skip_process = True
        form = self.read_form()

        tpars = [int(form[attr]*100) for attr in
                 ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                  'bkg_kweight', 'bkg_clamplo', 'bkg_clamphi',
                  'fft_kmin', 'fft_kmax', 'fft_kweight', 'fft_dk')]
        tpars.append(form['kwindow'])

        if tpars != self.last_process_pars:
            self.controller.larch.eval(autobk_cmd.format(**form))
            self.controller.larch.eval(xftf_cmd.format(**form))
            self.onPlotOne()

        self.last_process_pars = tpars
        self.skip_process = False

    def get_plot_arrays(self, dgroup):
        form = self.read_form()

    def onPlotOne(self, evt=None):
        form = self.read_form()
        plotchoice = form['plotone_op'].lower()
        form['title'] = self.dgroup.filename
        cmd = None
        if plotchoice.startswith('mu'):
            cmd = "plot_bkg({group:s}"
        elif plotchoice.startswith('chi(k)'):
            cmd = "plot_chik({group:s}, kweight={plot_kweight: d}"
            if 'window' in plotchoice.lower():
                cmd = cmd + ', show_window=True'
            else:
                cmd = cmd + ', show_window=False'

        elif 'chi(r)' in plotchoice:
            cmd = "plot_chir({group:s}"
            if plotchoice.startswith('|'):
                cmd = cmd  + ', show_mag=True'
            if 're[' in plotchoice:
                cmd = cmd  + ', show_real=True'

        if cmd is not None:
            cmd = cmd + ', title="{title:s}")'
            self.controller.larch.eval(cmd.format(**form))

    def onPlotSel(self, evt=None):
        newplot = True
        pass

    def plot(self, dgroup, title=None, plot_yarrays=None, delay_draw=False,
             new=True, zoom_out=True, with_extras=True, **kws):

        print("plot ", dgroup)
