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

from larch.math import index_of

from larch.wxlib import (BitmapButton, FloatCtrl, FloatSpin, ToggleButton,
                         get_icon, SimpleText, pack, Button, HLine, Choice,
                         Check, CEN, RCEN, LCEN, Font)

from larch.xafs.xafsutils import etok, ktoe
from larch.xafs.xafsplots import plotlabels

from .xas_dialogs import EnergyUnitsDialog
from .taskpanel import TaskPanel

np.seterr(all='ignore')

# plot options:
mu_bkg  = '\u03bC(E) + \u03bc0(E)'
chie    = '\u03c7(E)'
chik    = '\u03c7(k)'
chikwin = '\u03c7(k) + Window(k)'
chirmag = '|\u03c7(R)|'
chirre  = 'Re[\u03c7(R)]'
chirmr  = '|\u03c7(R)| + Re[\u03c7(R)]'
noplot  = '<no plot>'

PlotOne_Choices = [mu_bkg, chie, chik, chikwin, chirmag, chirre, chirmr]
PlotAlt_Choices = [noplot] + PlotOne_Choices
PlotSel_Choices = [chie, chik, chirmag, chirre]


PlotCmds = {mu_bkg:  "plot_bkg({group:s}",
            chie:    "plot_chie({group:s}",
            chik:    "plot_chik({group:s}, show_window=False, kweight={plot_kweight:.0f}",
            chikwin: "plot_chik({group:s}, show_window=True, kweight={plot_kweight:.0f}",
            chirmag: "plot_chir({group:s}, show_mag=True, show_real=False",
            chirre:  "plot_chir({group:s}, show_mag=False, show_real=True",
            chirmr:  "plot_chir({group:s}, show_mag=True, show_real=True",
            noplot: None}

FTWINDOWS = ('Kaiser-Bessel', 'Hanning', 'Gaussian', 'Sine', 'Parzen', 'Welch')

CLAMPLIST = ('0', '1', '2', '5', '10', '20', '50', '100', '200', '500', '1000',
             '2000', '5000', '10000')

autobk_cmd = """autobk({group:s}, rbkg={rbkg: .3f}, e0={e0: .4f},
      kmin={bkg_kmin: .3f}, kmax={bkg_kmax: .3f}, kweight={bkg_kweight: .1f},
      clamp_lo={bkg_clamplo: .1f}, clamp_hi={bkg_clamphi: .1f})"""

xftf_cmd = """xftf({group:s}, kmin={fft_kmin: .3f}, kmax={fft_kmax: .3f},
      kweight={fft_kweight: .3f}, dk={fft_dk: .3f}, window='{fft_kwindow:s}')"""


defaults = dict(e0=0, rbkg=1, bkg_kmin=0, bkg_kmax=None, bkg_clamplo=2,
                bkg_clamphi=50, bkg_kweight=1, fft_kmin=2, fft_kmax=None,
                fft_dk=4, fft_kweight=2, fft_kwindow='Kaiser-Bessel')

class EXAFSPanel(TaskPanel):
    """EXAFS Panel"""
    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='exafs_config',
                           config=defaults, **kws)
        self.skip_process = False
        self.last_plot = 'one'

    def build_display(self):
        titleopts = dict(font=Font(12), colour='#AA0000')
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

        plot_one = Button(panel, 'Plot This Group', size=(175, -1),
                          action=self.onPlotOne)

        plot_sel = Button(panel, 'Plot Selected Groups', size=(175, -1),
                          action=self.onPlotSel)


        saveconf = Button(panel, 'Save as Default Settings', size=(200, -1),
                          action=self.onSaveConfigBtn)

        def xxxFSWithPinPanel(name, value, **kws):
            s = wx.BoxSizer(wx.HORIZONTAL)
            self.wids[name] = FloatSpin(panel, value=value, **kws)
            bb = BitmapButton(panel, get_icon('pin'), size=(25, 25),
                              action=partial(self.onSelPoint, opt=name),
                              tooltip='use last point selected from plot')
            s.Add(self.wids[name])
            s.Add(bb)
            return s

        wids['plot_voffset'] = FloatSpin(panel, value=0, digits=2, increment=0.25,
                                         action=self.onProcess)
        wids['plot_kweight'] = FloatSpin(panel, value=2, digits=1, increment=1,
                                         action=self.onProcess, min_val=0, max_val=5)
        wids['plot_kweight_alt'] = FloatSpin(panel, value=2, digits=1, increment=1,
                                             action=self.onProcess,  min_val=0, max_val=5)

        opts = dict(digits=2, increment=0.1, min_val=0, action=self.onProcess)
        wids['e0'] = FloatSpin(panel, **opts)

        opts['max_val'] = 5
        wids['rbkg'] = FloatSpin(panel, value=1.0, **opts)

        opts['max_val'] = 125
        bkg_kmin = self.add_floatspin('bkg_kmin', value=0, with_pin=True, **opts)
        bkg_kmax = self.add_floatspin('bkg_kmax', value=20, with_pin=True, **opts)
        fft_kmin = self.add_floatspin('fft_kmin', value=0, with_pin=True, **opts)
        fft_kmax = self.add_floatspin('fft_kmax', value=20, with_pin=True, **opts)

        wids['fft_dk'] = FloatSpin(panel, value=3,  **opts)

        opts.update({'increment': 1, 'digits': 1, 'max_val': 5})
        wids['bkg_kweight'] = FloatSpin(panel, value=1, **opts)

        wids['fft_kweight'] = FloatSpin(panel, value=1, **opts)

        opts = dict(choices=CLAMPLIST, size=(80, -1), action=self.onProcess)
        wids['bkg_clamplo'] = Choice(panel, **opts)
        wids['bkg_clamphi'] = Choice(panel, **opts)

        wids['fft_kwindow'] = Choice(panel, choices=list(FTWINDOWS),
                                     action=self.onProcess, size=(150, -1))

        self.wids['is_frozen'] = Check(panel, default=False, label='Freeze Group',
                                       action=self.onFreezeGroup)

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        panel.Add(SimpleText(panel, ' EXAFS Processing', **titleopts), dcol=5)

        panel.Add(plot_sel, newrow=True)
        panel.Add(self.wids['plotsel_op'], dcol=2)

        add_text('Vertical offset: ', newrow=False)
        panel.Add(wids['plot_voffset'], dcol=2)

        panel.Add(plot_one, newrow=True)
        panel.Add(self.wids['plotone_op'], dcol=2)

        add_text('Plot k weight: ', newrow=False)
        panel.Add(wids['plot_kweight'])

        add_text('Add Second Plot: ', newrow=True)
        panel.Add(self.wids['plotalt_op'], dcol=2)
        add_text('Plot2 k weight: ', newrow=False)
        panel.Add(wids['plot_kweight_alt'])


        panel.Add(HLine(panel, size=(500, 3)), dcol=6, newrow=True)

        panel.Add(SimpleText(panel, ' Background subtraction',
                             **titleopts), dcol=1, newrow=True)

        panel.Add(Button(panel, 'Copy To Selected Groups', size=(225, -1),
                         action=partial(self.onCopyParam, 'bkg')),
                  dcol=3)

        add_text('R bkg: ')
        panel.Add(wids['rbkg'])

        add_text('E0: ', newrow=False)
        panel.Add(wids['e0'])

        add_text('k min: ')
        panel.Add(bkg_kmin)
        add_text('k max:',newrow=False)
        panel.Add(bkg_kmax)

        add_text('kweight: ', newrow=True)
        panel.Add(wids['bkg_kweight'], dcol=1)

        add_text('Clamps Low E: ', newrow=True)
        panel.Add( wids['bkg_clamplo'])
        add_text('high E: ',  newrow=False)
        panel.Add( wids['bkg_clamphi'])

        panel.Add(HLine(panel, size=(500, 3)), dcol=6, newrow=True)

        panel.Add(SimpleText(panel, ' Fourier transform',
                             **titleopts), dcol=1, newrow=True)

        panel.Add(Button(panel, 'Copy to Selected Groups', size=(225, -1),
                         action=partial(self.onCopyParam, 'fft')),
                  dcol=3)

        panel.Add(SimpleText(panel, 'k min: '), newrow=True)
        panel.Add(fft_kmin)

        panel.Add(SimpleText(panel, 'k max:'))
        panel.Add(fft_kmax)

        panel.Add(SimpleText(panel, 'k weight : '), newrow=True)
        panel.Add(wids['fft_kweight'])

        panel.Add(SimpleText(panel, 'K window : '), newrow=True)
        panel.Add(wids['fft_kwindow'])
        panel.Add(SimpleText(panel, ' dk : '))
        panel.Add(wids['fft_dk'])

        panel.Add((10, 10), newrow=True)
        panel.Add(self.wids['is_frozen'], dcol=1, newrow=True)
        panel.Add(saveconf, dcol=4)
        panel.Add((10, 10), newrow=True)
        panel.Add(HLine(self, size=(500, 3)), dcol=8, newrow=True)

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((10, 10), 0, LCEN, 3)
        sizer.Add(panel, 1, LCEN, 3)
        pack(self, sizer)
        self.skip_process = False

    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)
        self.dgroup = dgroup
        self.skip_process = True
        wids = self.wids
        for attr in ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                     'bkg_kweight', 'fft_kmin', 'fft_kmax',
                     'fft_kweight', 'fft_dk'):
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

        for attr in ('fft_kwindow', 'plotone_op', 'plotsel_op', 'plotalt_op'):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])


        frozen = opts.get('is_frozen', False)
        if hasattr(dgroup, 'is_frozen'):
            frozen = dgroup.is_frozen

        self.wids['is_frozen'].SetValue(frozen)
        self._set_frozen(frozen)

        self.skip_process = False

    def read_form(self, dgroup=None):
        "read form, return dict of values"
        skip_save = self.skip_process
        self.skip_process = True

        if dgroup is None:
            dgroup = self.controller.get_group()
        self.dgroup = dgroup
        if dgroup is None:
            return {}
        form_opts = {'group': dgroup.groupname}

        wids = self.wids
        for attr in ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                     'bkg_kweight', 'fft_kmin', 'fft_kmax',
                     'fft_kweight', 'fft_dk', 'plot_kweight',
                     'plot_kweight_alt', 'plot_voffset'):
            form_opts[attr] = wids[attr].GetValue()

        for attr in ('bkg_clamplo', 'bkg_clamphi'):
            form_opts[attr] = int(wids[attr].GetStringSelection())

        for attr in ('fft_kwindow', 'plotone_op', 'plotsel_op', 'plotalt_op'):
            form_opts[attr] = wids[attr].GetStringSelection()
        time.sleep(0.001)
        self.skip_process = skip_save
        return form_opts

    def onSaveConfigBtn(self, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())
        self.set_defaultconfig(conf)

    def onCopyParam(self, name=None, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())

        attrs =  ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                  'bkg_kweight', 'bkg_clamplo', 'bkg_clamphi')

        if name.startswith('fft'):
            attrs = ('fft_kmin', 'fft_kmax',
                     'fft_kweight', 'fft_dk', 'fft_kwindow')

        out = {a: conf[a] for a in attrs}

        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            if not dgroup.is_frozen:
                self.update_config(out, dgroup=dgroup)

    def _set_frozen(self, frozen):
        try:
            dgroup = self.controller.get_group()
            dgroup.is_frozen = frozen
        except:
            pass

        for attr in ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax', 'bkg_kweight',
                     'fft_kmin', 'fft_kmax', 'fft_kweight', 'fft_dk',
                     'bkg_clamplo', 'bkg_clamphi', 'fft_kwindow'):
            self.wids[attr].Enable(not frozen)

    def onFreezeGroup(self, evt=None):
        self._set_frozen(evt.IsChecked())


    def onProcess(self, event=None):
        """ handle process events"""
        if self.skip_process:
            return
        self.skip_process = True

        form = self.read_form()
        self.process(dgroup=self.dgroup, opts=form)
        self.skip_process = False

        plotter = self.onPlotOne
        if self.last_plot == 'selected':
            plotter = self.onPlotSel
        wx.CallAfter(partial(plotter, form=form))

    def process(self, dgroup=None, opts=None, fast_process=False, **kws):
        if opts is None:
            opts = self.read_form()
        if dgroup is not None:
            self.dgroup = dgroup
            opts['group'] = dgroup.groupname

        opts.update(kws)
        pars = [int(opts.get(attr, 0)*1000) for attr in
                ('e0', 'rbkg', 'bkg_kmin', 'bkg_kmax',
                 'bkg_kweight', 'bkg_clamplo', 'bkg_clamphi',
                 'fft_kmin', 'fft_kmax', 'fft_kweight', 'fft_dk')]
        if not 'fft_kwindow' in opts:
            return

        pars.append(opts['fft_kwindow'])

        lpars = getattr(dgroup, 'exafs_formvals', False)

        if pars != lpars and not fast_process:
            self.larch_eval(autobk_cmd.format(**opts))
            self.larch_eval(xftf_cmd.format(**opts))
            dgroup.exafs_formvals = pars
            self.update_config(opts, dgroup=dgroup)

    def plot(self, dgroup=None):
        if self.skip_plotting:
            return
        self.onPlotOne(dgroup=dgroup)

    def onPlotOne(self, evt=None, form=None, dgroup=None):
        if self.skip_plotting:
            return
        if form is None:
            form = self.read_form()
        if len(form) == 0:
            return
        if dgroup is not None:
            self.dgroup = dgroup
            form['group'] = dgroup.groupname
        form['title'] = '"%s"' % self.dgroup.filename

        cmd = PlotCmds[form['plotone_op']] + ", win=1, title={title:s})"
        # 2nd plot
        cmd2 =  PlotCmds[form['plotalt_op']]
        if cmd2 is not None:
            cmd2 = cmd2.replace('plot_kweight', 'plot_kweight_alt')
            cmd2 = cmd2 + ", win=2, title={title:s})"
            cmd = "%s\n%s" % (cmd, cmd2)
            self.controller.get_display(win=2)

        self.larch_eval(cmd.format(**form))
        self.last_plot = 'one'
        self.parent.SetFocus()
        if evt is not None:
            evt.Skip()

    def onPlotSel(self, evt=None, form=None):
        if self.skip_plotting:
            return
        group_ids = self.controller.filelist.GetCheckedStrings()
        if len(group_ids) < 1:
            return
        if form is None:
            form = self.read_form()

        bcmd = PlotCmds[form['plotsel_op']]
        form['new'] = 'True'
        offset = form['plot_voffset']
        for i, checked in enumerate(group_ids):
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            if dgroup is not None:
                form['group'] = dgroup.groupname
                form['label'] = dgroup.filename
                form['offset'] = offset * i
                if not (hasattr(dgroup, 'chir_mag') and hasattr(dgroup, 'r')):
                    self.process(dgroup=dgroup, opts=form)

                extra = """, offset={offset:.3f}, win=1, delay_draw=True,
    label='{label:s}', new={new:s})"""
                cmd = "%s%s" % (bcmd, extra)
                self.larch_eval(cmd.format(**form))
                form['new'] = 'False'

        self.larch_eval("redraw(win=1, show_legend=True)")
        self.last_plot = 'selected'
        self.parent.SetFocus()
        if evt is not None:
            evt.Skip()
