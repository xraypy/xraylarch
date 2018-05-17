#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import wx
import wx.lib.scrolledpanel as scrolled

import numpy as np

from functools import partial
from collections import OrderedDict

from wxutils import (SimpleText, pack, Button, HLine, Choice, Check, CEN,
                     RCEN, LCEN, Font)

from larch.utils import index_of
from larch.wxlib import (BitmapButton, FloatCtrl, FloatSpin, ToggleButton,
                         GridPanel, get_icon)
from larch_plugins.xasgui.taskpanel import TaskPanel

np.seterr(all='ignore')


# plot options:
norm    = u'Normalized \u03bC(E)'
dmude   = u'd\u03bC(E)/dE'
chik    = u'\u03c7(k)'
noplot  = '<no plot>'

FitSpace_Choices = [norm, dmude, chik]

PlotCmds = {norm: "plot_mu({group:, norm=True}",
            chik: "plot_chik({group:s}, show_window=False, kweight={plot_kweight:.0f}",
            noplot: None}


defaults = dict(e0=0, elo=-20, ehi=30, fitspace=norm, all_combos=True,
                sum_to_one=True, show_e0=True, show_fitrange=True)

MAX_STANDARDS = 10

class LinearComboPanel(TaskPanel):
    """Liear Combination Panel"""
    def __init__(self, parent, controller, **kws):

        TaskPanel.__init__(self, parent, controller,
                           configname='lincombo_config',
                           config=defaults, **kws)

    def process(self, dgroup, **kws):
        """ handle linear combo processing"""
        if self.skip_process:
            return
        return self.read_form()

    def larch_eval(self, cmd):
        """eval"""
        self.controller.larch.eval(cmd)

    def build_display(self):
        titleopts = dict(font=Font(12), colour='#AA0000')
        panel = self.panel
        wids = self.wids
        self.skip_process = True

        wids['fitspace'] = Choice(panel, choices=FitSpace_Choices,
                                  size=(175, -1))
        wids['fitspace'].SetStringSelection(norm)

        add_text = self.add_text

        opts = dict(digits=2, increment=0.1, action=self.onFitOne)

        e0_wids = self.add_floatspin('e0', value=0, **opts)
        elo_wids = self.add_floatspin('elo', value=-20, **opts)
        ehi_wids = self.add_floatspin('ehi', value=30, **opts)

        wids['fit_group'] = Button(panel, 'Fit this Group', size=(150, -1),
                                   action=self.onFitOne)
        wids['fit_selected'] = Button(panel, 'Fit Selected Groups', size=(150, -1),
                                      action=self.onFitAll)

        wids['add_selected'] = Button(panel, 'Use Selected Groups', size=(200, -1),
                                      action=self.onUseSelected)

        wids['saveconf'] = Button(panel, 'Save as Default Settings', size=(200, -1),
                                  action=self.onSaveConfigBtn)

        opts = dict(default=True, size=(75, -1), action=self.onPlotOne)

        wids['show_e0']       = Check(panel, label='show?', **opts)
        wids['show_fitrange'] = Check(panel, label='show?', **opts)

        wids['sum_to_one'] = Check(panel, label='Weights Must Sum to 1?', default=True)
        wids['all_combos'] = Check(panel, label='Fit All Combinations?', default=True)

        panel.Add(SimpleText(panel, ' Linear Combination Analysis', **titleopts), dcol=5)
        add_text('Run Fit', newrow=False)

        add_text('Array to Fit: ', newrow=True)
        panel.Add(wids['fitspace'], dcol=4)
        panel.Add(wids['fit_group'])

        add_text('E0: ')
        panel.Add(e0_wids, dcol=3)
        panel.Add(wids['show_e0'])
        panel.Add(wids['fit_selected'])


        add_text('Fit Energy Range: ')
        panel.Add(elo_wids)
        add_text(' : ', newrow=False)
        panel.Add(ehi_wids)
        panel.Add(wids['show_fitrange'])

        panel.Add(wids['sum_to_one'], dcol=2, newrow=True)
        panel.Add(wids['all_combos'], dcol=3)

        panel.Add(HLine(panel, size=(500, 3)), dcol=6, newrow=True)

        add_text('Standards: ')
        panel.Add(wids['add_selected'], dcol=4)

        groupnames = ['<none>'] + list(self.controller.file_groups.keys())
        sgrid = GridPanel(panel, nrows=6)

        sgrid.Add(SimpleText(sgrid, "#"))
        sgrid.Add(SimpleText(sgrid, "Group"))
        sgrid.Add(SimpleText(sgrid, "Weight"))
        sgrid.Add(SimpleText(sgrid, "Min"))
        sgrid.Add(SimpleText(sgrid, "Max"))
        sgrid.Add(SimpleText(sgrid, "Use?"))

        fopts = dict(minval=-10, maxval=20, precision=4, size=(60, -1))
        for i in range(1, 1+MAX_STANDARDS):
            si = ("comp", "_%2.2i" % i)
            sgrid.Add(SimpleText(sgrid, "%2i" % i), newrow=True)
            wids['%schoice%s' % si] = Choice(sgrid, choices=groupnames, size=(200, -1),
                                           action=partial(self.onComponent, comp=i))
            wids['%sval%s' % si] = FloatCtrl(sgrid, value=0, **fopts)
            wids['%smin%s' % si] = FloatCtrl(sgrid, value=0, **fopts)
            wids['%smax%s' % si] = FloatCtrl(sgrid, value=1, **fopts)
            wids['%suse%s' % si] = Check(sgrid, label='', default=False)
            for cname in ('choice', 'val', 'min', 'max', 'use'):
                sgrid.Add(wids[("%%s%s%%s" % cname) % si])
        sgrid.pack()
        panel.Add(sgrid, dcol=7, newrow=True)
        panel.Add(wids['saveconf'], dcol=4, newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LCEN, 3)
        pack(self, sizer)
        self.skip_process = False

    def onComponent(self, evt=None, comp=None):
        if comp is None or evt is None:
            return

        comps = []
        for wname, wid in self.wids.items():
            if wname.startswith('compchoice'):
                pref, n = wname.split('_')
                if wid.GetSelection() > 0:
                    comps.append((int(n), wid.GetStringSelection()))
                else:
                    self.wids["compval_%s" % n].SetValue(0)

        cnames = set([elem[1] for elem in comps])
        if len(cnames) < len(comps):
            comps.remove((comp, evt.GetString()))
            self.wids["compchoice_%2.2i" % comp].SetSelection(0)

        weight = 1.0 / len(comps)

        for n, cname in comps:
            self.wids["compval_%2.2i" % n].SetValue(weight)


    def fill_form(self, dgroup):
        """fill in form from a data group"""
        opts = self.get_config(dgroup)

        self.dgroup = dgroup
        self.skip_process = True
        wids = self.wids
        for attr in ('e0', 'elo', 'ehi'):
            val = getattr(opts, attr, None)
            if val is not None:
                wids[attr].SetValue(val)

        for attr in ('all_combos', 'sum_to_one', 'show_e0', 'show_fitrange'):
            wids[attr].Enable(getattr(opts, attr, False))

        for attr in ('fitspace',):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])

        groupnames = ['<none>'] + list(self.controller.file_groups.keys())
        for wname, wid in wids.items():
            if wname.startswith('compchoice'):
                cur = wid.GetStringSelection()
                wid.Clear()
                wid.AppendItems(groupnames)
                if cur in groupnames:
                    wid.SetStringSelection(cur)
                else:
                    wid.SetSelection(0)
            elif wname.startswith('comp'):
                wid.SetValue(getattr(opts, wname, wid.GetValue()))
        self.skip_process = False

    def read_form(self, dgroup=None):
        "read form, return dict of values"
        self.skip_process = True
        if dgroup is None:
            dgroup = self.controller.get_group()
        self.dgroup = dgroup
        form_opts = {'group': dgroup.groupname}
        wids = self.wids
        for attr in ('e0', 'elo', 'ehi'):
            form_opts[attr] = wids[attr].GetValue()

        for attr in ('fitspace',):
            form_opts[attr] = wids[attr].GetStringSelection()

        for attr in ('all_combos', 'sum_to_one', 'show_e0', 'show_fitrange'):
            form_opts[attr] = wids[attr].Enabled

        for attr, wid in wids.items():
            if attr.startswith('compchoice'):
                form_opts[attr] = wid.GetStringSelection()
            elif attr.startswith('compuse'):
                form_opts[attr] = wid.IsChecked()
            elif attr.startswith('comp'):
                form_opts[attr] = wid.GetValue()

        self.skip_process = False
        return form_opts

    def onSaveConfigBtn(self, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())
        self.set_defaultconfig(conf)

    def onUseSelected(self, event=None):
        """ use selected groups as standards"""
        self.skip_process = True
        selected_groups = self.controller.filelist.GetCheckedStrings()
        if len(selected_groups) == 0:
            return
        if len(selected_groups) > MAX_STANDARDS:
            selected_groups = selected_groups[:MAX_STANDARDS]
        weight = 1.0/len(selected_groups)
        for attr, wid in self.wids.items():
            if attr.startswith('compuse'):
                wid.SetValue(False)
        for i, sel in enumerate(selected_groups):
            si = "_%2.2i" % (i+1)
            self.wids['compchoice%s' % si].SetStringSelection(sel)
            self.wids['compval%s' % si].SetValue(weight)
            self.wids['compuse%s' % si].SetValue(True)

        self.skip_process = False

    def onFitOne(self, event=None):
        """ handle process events"""
        print("onFitOne ", event, self.skip_process)
        if self.skip_process:
            return

        self.skip_process = True
        form = self.read_form()

        print(" FORM ", form)

        self.plot()
        self.skip_process = False

    def onFitAll(self, event=None):
        """ handle process events"""
        print("onFitAll ", event, self.skip_process)
        if self.skip_process:
            return

        self.skip_process = True
        form = self.read_form()

        print(" FORM ", form)

        self.plot()
        self.skip_process = False

    def plot(self, dgroup=None):
        self.onPlotOne(dgroup=dgroup)
