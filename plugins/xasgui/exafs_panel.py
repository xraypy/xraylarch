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

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check,
                      CEN, RCEN, LCEN, Font)

from larch.utils import index_of
from larch.wxlib import BitmapButton, FloatCtrl, FloatSpin, ToggleButton
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

units_list = ('eV', u'1/\u212B')
PlotChoices = {'e': ('\u03BC(E) + \u03BC0(E)', '\u03A7(E)'),
               'k': ('\u03A7(k)', '\u03A7(k) + Window'),
               'r': ('|\u03A7(R)|', 'Re[\u03A7(R)]', '|\u03A7(R)| + Re[\u03A7(R)]')}

FTWINDOWS = ('Kaiser-Bessel', 'Hanning', 'Gaussian', 'Sine', 'Parzen', 'Welch')

CLAMPLIST = ('0', '1', '2', '5', '10', '20', '50', '100', '200', '500', '1000',
             '2000', '5000', '10000')

autobk_cmd = """autobk({group:s}, rbkg={rbkg: .3f}, e0={e0: .4f},
      kmin={bkg_kmin: .3f}, kmax={bkg_kmax: .3f}, kweight={bkg_kweight: .1f},
      clamp_lo={bkg_clamplo: .1f}, clamp_hi={bkg_clamphi: .1f})"""

xftf_cmd = """xftf({group:s}, kmin={fft_kmin: .3f}, kmax={fft_kmax: .3f},
      kweight={fft_kweight: .3f}, dk={fft_dk: .3f}, window='{fft_kwindow:s}')"""


def default_exafs_config():
    opts = dict(e0=0, rbkg=1, bkg_kmin=0, bkg_kmax=None, bkg_clamplo=2,
                bkg_clamphi=5, bkg_kweight=1, fft_kmin=2, fft_kmax=None,
                fft_dk=4, fft_kweight=2, fft_kwindow='Kaiser-Bessel',
                plot_kweight=2)
    for space in ('e', 'k', 'r'):
        opts['plotopts_%s' % space] = PlotChoices[space][0]
        opts['plotone_%s' % space] = False
        opts['plotsel_%s' % space] = False

    opts['plotone_k'] = True
    return opts

## plotone_op='chi(k)', plotsel_op='chi(k)')

class EXAFSPanel(TaskPanel):
    """EXAFS Panel"""
    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='exafs_config', **kws)
        self.skip_process = False
        self.last_process_pars = None

    def build_display(self):
        self.SetFont(Font(10))
        titleopts = dict(font=Font(11), colour='#AA0000')

        panel = self.panel
        wids = self.wids
        btns = self.btns
        self.skip_process = True

        saveconf = Button(panel, 'Save as Default Settings', size=(200, -1),
                          action=self.onSaveConfigBtn)

        def CopyBtn(name):
            return Button(panel, 'Copy', size=(50, -1),
                          action=partial(self.onCopyParam, name))


        for space, label in (('e', 'Energy'), ('k', 'K space'),
                             ('r', 'R space')): # , ('w', 'Wavelet')):
            cname = 'plotopts_%s' % space
            oname = 'plotone_%s' % space
            sname = 'plotsel_%s' % space

            actone = partial(self.onPlot, selected=False)
            actsel = partial(self.onPlot, selected=True)

            if space in PlotChoices:
                wids[cname] = Choice(panel, choices=PlotChoices[space],
                                     size=(100, -1), action=actone)
            wids[oname] = ToggleButton(panel, label, size=(100, -1), action=actone)
            wids[sname] = ToggleButton(panel, label, size=(100, -1), action=actsel)
            # if space != 'w':

        wids['plot_kweight'] = FloatSpin(panel, value=2,
                                         action=self.onPlot, size=(90, -1),
                                         min_val=0, max_val=4, digits=0,
                                         increment=1)


        opts = dict(size=(90, -1), digits=2, increment=0.1,
                    action=self.process)
        wids['e0'] = FloatSpin(panel, **opts)

        wids['rbkg'] = FloatSpin(panel, value=1.0,
                                 min_val=0, max_val=25, **opts)
        wids['bkg_kmin'] = FloatSpin(panel,  value=0,
                                     min_val=0, max_val=125, **opts)

        wids['bkg_kmax'] = FloatSpin(panel, min_val=0, max_val=125, **opts)

        wids['fft_kmin'] = FloatSpin(panel, value=0,
                                     min_val=0, max_val=125, **opts)

        wids['fft_kmax'] = FloatSpin(panel, min_val=0, max_val=125, **opts)

        wids['fft_dk'] = FloatSpin(panel, value=3,
                                   min_val=0, max_val=125, **opts)

        opts['increment'] = opts['digits'] = 1
        wids['bkg_kweight'] = FloatSpin(panel, value=1,
                                        min_val=0, max_val=8, **opts)

        wids['fft_kweight'] = FloatSpin(panel, value=1,
                                        min_val=0, max_val=8, **opts)

        for name in ('bkg_kmin', 'bkg_kmax', 'fft_kmin', 'fft_kmax'):
            bb = BitmapButton(panel, get_icon('plus'),
                              action=partial(self.onSelPoint, opt=name),
                              tooltip='use last point selected from plot')
            btns[name] = bb
        opts = dict(choices=CLAMPLIST, size=(70, -1), action=self.process)
        wids['bkg_clamplo'] = Choice(panel, **opts)
        wids['bkg_clamphi'] = Choice(panel, **opts)

        wids['fft_kwindow'] = Choice(panel, choices=list(FTWINDOWS),
                                     action=self.process, size=(100, -1))

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        plotsel_buttons = wx.BoxSizer(wx.HORIZONTAL)
        plotsel_buttons.Add(wids['plotsel_e'])
        plotsel_buttons.Add(wids['plotsel_k'])
        plotsel_buttons.Add(wids['plotsel_r'])

        plotone_buttons = wx.BoxSizer(wx.HORIZONTAL)
        plotone_buttons.Add(wids['plotone_e'])
        plotone_buttons.Add(wids['plotone_k'])
        plotone_buttons.Add(wids['plotone_r'])

        panel.Add(SimpleText(panel, ' EXAFS Processing', **titleopts), dcol=5)

        add_text('Plot Selected Groups: ', dcol=2, newrow=True)
        panel.Add(plotsel_buttons, dcol=5)


        add_text('Plot This Group: ', dcol=2, newrow=True)
        panel.Add(plotone_buttons, dcol=5)


        add_text('Plot Options: ', dcol=2, newrow=True)
        popts = wx.BoxSizer(wx.HORIZONTAL)
        popts.Add(wids['plotopts_e'])
        popts.Add(wids['plotopts_k'])
        popts.Add(wids['plotopts_r'])
        panel.Add(popts, dcol=5)

        add_text('K weight for plot: ', dcol=2)
        panel.Add(wids['plot_kweight'])


        panel.Add(HLine(panel, size=(250, 2)), dcol=7, newrow=True)

        panel.Add(SimpleText(panel, ' Background subtraction',
                             **titleopts), dcol=4, newrow=True)
        panel.Add(SimpleText(panel, ' Copy to Selected Groups?'),
                  style=RCEN, dcol=3)


        add_text('E0: ', dcol=2, newrow=True)
        panel.Add(wids['e0'], dcol=4)
        panel.Add(CopyBtn('e0'), style=RCEN)

        add_text('R_bkg: ', dcol=2, newrow=True)
        panel.Add(wids['rbkg'], dcol=1)

        add_text('K weight: ', dcol=2, newrow=False)
        panel.Add(wids['bkg_kweight'], dcol=1)
        panel.Add(CopyBtn('rbkg'), style=RCEN)


        add_text('K range: ')
        panel.Add(btns['bkg_kmin'], style=RCEN)
        panel.Add(wids['bkg_kmin'])

        add_text(' : ', dcol=1, newrow=False)
        panel.Add(btns['bkg_kmax'], style=RCEN)
        panel.Add(wids['bkg_kmax'])
        panel.Add(CopyBtn('bkg_krange'), style=RCEN)


        add_text('Clamps Low E: ', dcol=2, newrow=True)
        panel.Add( wids['bkg_clamplo'])
        add_text('high E: ', dcol=2, newrow=False)
        panel.Add( wids['bkg_clamphi'])
        panel.Add(CopyBtn('bkg_clamps'), style=RCEN)

        panel.Add(HLine(panel, size=(250, 2)), dcol=7, newrow=True)

        panel.Add(SimpleText(panel, ' Fourier transform',
                             **titleopts), dcol=6, newrow=True)


        panel.Add(SimpleText(panel, 'K range: '), newrow=True)
        panel.Add(btns['fft_kmin'], style=RCEN)
        panel.Add(wids['fft_kmin'])

        panel.Add(SimpleText(panel, ' : '))
        panel.Add(btns['fft_kmax'], style=RCEN)
        panel.Add(wids['fft_kmax'])
        panel.Add(CopyBtn('fft_krange'), style=RCEN)

        panel.Add(SimpleText(panel, 'K weight : '), dcol=2, newrow=True)
        panel.Add(wids['fft_kweight'], dcol=4)
        panel.Add(CopyBtn('fft_kweight'), style=RCEN)

        panel.Add(SimpleText(panel, 'K window : '), dcol=2, newrow=True)
        panel.Add(wids['fft_kwindow'])
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
            dgroup.exafs_config = config
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
                     'fft_kweight', 'fft_dk', 'plot_kweight'):
            val = getattr(dgroup, attr, None)
            if val is None:
                val = opts.get(attr, -1)
                if attr == 'bkg_kmax':
                    val = 0.25 + etok(max(dgroup.energy) - dgroup.e0)
                elif attr == 'fft_kmax':
                    val = -1.0 + etok(max(dgroup.energy) - dgroup.e0)
            wids[attr].SetValue(val)

        for attr in ('bkg_clamplo', 'bkg_clamphi'):
            wids[attr].SetStringSelection("%d" % opts.get(attr, 0))
        for attr in ('fft_kwindow', 'plotopts_e', 'plotopts_k', 'plotopts_r'):
            wids[attr].SetStringSelection(opts[attr])

        for space in ('e', 'k', 'r'): # , 'w'):
            cname = 'plotopts_%s' % space
            oname = 'plotone_%s' % space
            sname = 'plotsel_%s' % space
            wids[oname].SetValue(opts[oname])
            wids[cname].SetStringSelection(opts[cname])
            wids[sname].SetValue(opts[sname])
        self.skip_process = False
        self.process()

    def read_form(self):
        "read form, return dict of values"
        self.dgroup = self.controller.get_group()
        form_opts = {'group': self.dgroup.groupname}

        wids = self.wids
        for attr in ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                     'bkg_kweight', 'fft_kmin', 'fft_kmax',
                     'fft_kweight', 'fft_dk', 'plot_kweight'):
            form_opts[attr] = wids[attr].GetValue()

        for attr in ('bkg_clamplo', 'bkg_clamphi'):
            form_opts[attr] = int(wids[attr].GetStringSelection())

        for attr in ('fft_kwindow', 'plotopts_e', 'plotopts_k', 'plotopts_r'):
            form_opts[attr] = wids[attr].GetStringSelection()

        for space in ('e', 'k', 'r'): # , 'w'):
            cname = 'plotopts_%s' % space
            oname = 'plotone_%s' % space
            sname = 'plotsel_%s' % space
            form_opts[oname] = wids[oname].GetValue()
            form_opts[cname] = wids[cname].GetStringSelection()
            form_opts[sname] = wids[sname].GetValue()

            # if space != 'w':

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
        tpars.append(form['fft_kwindow'])

        if tpars != self.last_process_pars:
            self.controller.larch.eval(autobk_cmd.format(**form))
            self.controller.larch.eval(xftf_cmd.format(**form))
            self.onPlot()

        self.last_process_pars = tpars
        self.skip_process = False

    def get_plot_arrays(self, dgroup):
        form = self.read_form()

    def onPlot(self, evt=None, selected=False):
        form = self.read_form()
        # print("form : ", form)

        form['title'] = '"%s"' % self.dgroup.filename

        if selected:
            print("PLOT SELECTED")


        if form['plotone_e']:
            form['win'] =  1
            if '\u03A7' in form['plotopts_e'].lower():
                print(" plot chi(e)")
            else:
                cmd = "plot_bkg({group:s}"
                cmd = cmd + ", win={win:d}, title={title:s})"
                self.controller.larch.eval(cmd.format(**form))

        if form['plotone_k']:
            form['win'] =  2
            show_win = 'window' in form['plotopts_k'].lower()
            form['show_win'] = 'True' if show_win else 'False'
            cmd = "plot_chik({group:s}, kweight={plot_kweight:.1f}, show_window={show_win:s}"
            cmd = cmd + ", win={win:d}, title={title:s})"
            self.controller.larch.eval(cmd.format(**form))

        if form['plotone_r']:
            form['win'] = 3
            show_mag = '|' in form['plotopts_r'].lower()
            show_re  = 're[' in form['plotopts_r'].lower()
            form['show_mag'] = 'True' if show_mag else 'False'
            form['show_re'] = 'True' if  show_re else 'False'
            cmd = "plot_chir({group:s}, show_mag={show_mag:s}, show_real={show_re:s}"
            cmd = cmd + ", win={win:d}, title={title:s})"
            self.controller.larch.eval(cmd.format(**form))


    def onPlotSel(self, evt=None):
        newplot = True
        pass
