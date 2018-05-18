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

import lmfit
from larch import Group
from larch.utils import index_of

from larch.wxlib import (BitmapButton, FloatCtrl, FloatSpin, ToggleButton,
                         GridPanel, get_icon, SimpleText, pack, Button,
                         HLine, Choice, Check, CEN, RCEN, LCEN, Font)

from larch_plugins.xasgui.taskpanel import TaskPanel

np.seterr(all='ignore')


# plot options:
norm   = u'Normalized \u03bC(E)'
dmude  = u'd\u03bC(E)/dE'
chik   = u'\u03c7(k)'
noplot = '<no plot>'
noname = '<none>'

FitSpace_Choices = [norm, dmude, chik]
Plot_Choices = ['Data + Sum', 'Data + Sum + Components']

PlotCmds = {norm: "plot_mu({group:, norm=True}",
            chik: "plot_chik({group:s}, show_window=False, kweight={plot_kweight:.0f}",
            noplot: None}


defaults = dict(e0=0, elo=-25, ehi=75, fitspace=norm, all_combos=False,
                sum_to_one=True, show_e0=True, show_fitrange=True)

MAX_COMPONENTS = 10

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


        wids['plotchoice'] = Choice(panel, choices=Plot_Choices,
                                  size=(175, -1), action=self.onPlot)
        wids['plotchoice'].SetSelection(1)

        add_text = self.add_text

        opts = dict(digits=2, increment=1.0)

        e0_wids = self.add_floatspin('e0', value=0, **opts)
        elo_wids = self.add_floatspin('elo', value=-20, **opts)
        ehi_wids = self.add_floatspin('ehi', value=30, **opts)

        wids['fit_group'] = Button(panel, 'Fit this Group', size=(150, -1),
                                   action=self.onFitOne)
        wids['fit_selected'] = Button(panel, 'Fit Selected Groups', size=(150, -1),
                                      action=self.onFitAll)

        wids['add_selected'] = Button(panel, 'Use Selected Groups as Components', size=(250, -1),
                                      action=self.onUseSelected)

        wids['saveconf'] = Button(panel, 'Save as Default Settings', size=(200, -1),
                                  action=self.onSaveConfigBtn)

        opts = dict(default=True, size=(75, -1), action=self.onPlotOne)

        wids['show_e0']       = Check(panel, label='show?', **opts)
        wids['show_fitrange'] = Check(panel, label='show?', **opts)

        wids['sum_to_one'] = Check(panel, label='Weights Must Sum to 1?', default=True)
        wids['all_combos'] = Check(panel, label='Fit All Combinations?', default=False)

        panel.Add(SimpleText(panel, ' Linear Combination Analysis', **titleopts), dcol=5)
        add_text('Run Fit', newrow=False)

        add_text('Array to Fit: ', newrow=True)
        panel.Add(wids['fitspace'], dcol=4)
        panel.Add(wids['fit_group'])

        add_text('Plot : ', newrow=True)
        panel.Add(wids['plotchoice'], dcol=4)
        panel.Add(wids['fit_selected'])

        add_text('E0: ')
        panel.Add(e0_wids, dcol=3)
        panel.Add(wids['show_e0'])


        add_text('Fit Energy Range: ')
        panel.Add(elo_wids)
        add_text(' : ', newrow=False)
        panel.Add(ehi_wids)
        panel.Add(wids['show_fitrange'])

        panel.Add(wids['sum_to_one'], dcol=2, newrow=True)
        panel.Add(wids['all_combos'], dcol=3)

        panel.Add(HLine(panel, size=(400, 2)), dcol=5, newrow=True)

        add_text('Components: ')
        panel.Add(wids['add_selected'], dcol=4)

        groupnames = [noname] + list(self.controller.file_groups.keys())
        sgrid = GridPanel(panel, nrows=6)

        sgrid.Add(SimpleText(sgrid, "#"))
        sgrid.Add(SimpleText(sgrid, "Group"))
        sgrid.Add(SimpleText(sgrid, "Weight"))
        sgrid.Add(SimpleText(sgrid, "Min Weight"))
        sgrid.Add(SimpleText(sgrid, "Max Weight"))

        fopts = dict(minval=-10, maxval=20, precision=4, size=(60, -1))
        for i in range(1, 1+MAX_COMPONENTS):
            si = ("comp", "_%2.2i" % i)
            sgrid.Add(SimpleText(sgrid, "%2i" % i), newrow=True)
            wids['%schoice%s' % si] = Choice(sgrid, choices=groupnames, size=(200, -1),
                                           action=partial(self.onComponent, comp=i))
            wids['%sval%s' % si] = FloatCtrl(sgrid, value=0, **fopts)
            wids['%smin%s' % si] = FloatCtrl(sgrid, value=0, **fopts)
            wids['%smax%s' % si] = FloatCtrl(sgrid, value=1, **fopts)
            for cname in ('choice', 'val', 'min', 'max'):
                sgrid.Add(wids[("%%s%s%%s" % cname) % si])
        sgrid.pack()
        panel.Add(sgrid, dcol=5, newrow=True)
        panel.Add(HLine(panel, size=(400, 2)), dcol=5, newrow=True)
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
        if isinstance(dgroup, Group):
            d_emin = min(dgroup.energy)
            d_emax = max(dgroup.energy)
            if opts['e0'] < d_emin or opts['e0'] > d_emax:
                opts['e0'] = dgroup.e0

        self.skip_process = True
        wids = self.wids
        for attr in ('e0', 'elo', 'ehi'):
            val = opts.get(attr, None)
            if val is not None:
                wids[attr].SetValue(val)

        for attr in ('all_combos', 'sum_to_one', 'show_e0', 'show_fitrange'):
            wids[attr].SetValue(opts.get(attr, True))

        for attr in ('fitspace',):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])

        groupnames = [noname] + list(self.controller.file_groups.keys())
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
                wid.SetValue(opts.get(wname, wid.GetValue()))
        self.skip_process = False

    def read_form(self, dgroup=None):
        "read form, return dict of values"
        self.skip_process = True
        if dgroup is None:
            dgroup = self.controller.get_group()
        self.dgroup = dgroup
        opts = {'group': dgroup.groupname, 'filename':dgroup.filename}
        wids = self.wids
        for attr in ('e0', 'elo', 'ehi'):
            opts[attr] = wids[attr].GetValue()

        for attr in ('fitspace', 'plotchoice'):
            opts[attr] = wids[attr].GetStringSelection()

        for attr in ('all_combos', 'sum_to_one', 'show_e0', 'show_fitrange'):
            opts[attr] = wids[attr].GetValue()

        for attr, wid in wids.items():
            if attr.startswith('compchoice'):
                opts[attr] = wid.GetStringSelection()
            elif attr.startswith('comp'):
                opts[attr] = wid.GetValue()

        comps, wval, wmin, wmax = [], [], [], []
        for i in range(MAX_COMPONENTS):
            scomp = "_%2.2i" % (i+1)
            cname = opts['compchoice%s' % scomp]
            if cname != noname:
                wval.append(str(opts['compval%s' % scomp]))
                wmin.append(str(opts['compmin%s' % scomp]))
                wmax.append(str(opts['compmax%s' % scomp]))
                comps.append(self.controller.file_groups[cname])
        opts['comps']   = ', '.join(comps)
        opts['weights'] = ', '.join(wval)
        opts['minvals'] = ', '.join(wmin)
        opts['maxvals'] = ', '.join(wmax)
        opts['elo_abs'] = float(opts['elo']) + float(opts['e0'])
        opts['ehi_abs'] = float(opts['ehi']) + float(opts['e0'])
        opts['func'] = 'lincombo_fit'
        if opts['all_combos']:
            opts['func'] = 'lincombo_fitall'
        opts['arrayname'] = 'norm'
        if opts['fitspace'] == dmude:
            opts['arrayname'] = 'dmude'

        self.skip_process = False
        return opts

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
        if len(selected_groups) >= MAX_COMPONENTS:
            selected_groups = selected_groups[:MAX_COMPONENTS]
        weight = 1.0/len(selected_groups)

        for i in range(MAX_COMPONENTS):
            si = "_%2.2i" % (i+1)
            self.wids['compchoice%s' % si].SetStringSelection(noname)
            self.wids['compval%s' % si].SetValue(0.0)

        for i, sel in enumerate(selected_groups):
            si = "_%2.2i" % (i+1)
            self.wids['compchoice%s' % si].SetStringSelection(sel)
            self.wids['compval%s' % si].SetValue(weight)
        self.skip_process = False


    def do_fit(self, groupname, form):
        """run lincombo fit for a group"""
        form['gname'] = groupname
        script = """
lcf_result = {func:s}({gname:s}, [{comps:s}], xmin={elo_abs:.4f}, xmax={ehi_abs:.4f}, sum_to_one={sum_to_one},
          weights=[{weights:s}], minvals=[{minvals:s}], maxvals=[{maxvals:s}])
{gname:s}.lcf_result = lcf_result
"""
        self.controller.larch.eval(script.format(**form))

        dgroup = self.controller.get_group(groupname)
        print(lmfit.fit_report(dgroup.lcf_result.result))
        print(dgroup.lcf_result.weights)

        self.plot(dgroup=dgroup)

    def onFitOne(self, event=None):
        """ handle process events"""
        if self.skip_process:
            return

        self.skip_process = True
        form = self.read_form()
        self.do_fit(form['group'], form)
        self.skip_process = False

    def onFitAll(self, event=None):
        """ handle process events"""
        if self.skip_process:
            return

        self.skip_process = True
        form = self.read_form()
        for sel in self.controller.filelist.GetCheckedStrings():
            gname = self.controller.file_groups[sel]
            self.do_fit(gname, form)
        self.skip_process = False

    def plot(self, dgroup=None):
        self.onPlot(dgroup=dgroup)

    def onPlot(self, evt=None, dgroup=None):
        if dgroup is None:
            dgroup = self.controller.get_group()

        form = self.read_form(dgroup=dgroup)
        form['plotopt'] = 'show_norm=True'
        if form['arrayname'] == 'dmude':
            form['plotopt'] = 'show_deriv=True'

        erange = form['ehi'] - form['elo']
        form['pemin'] = 10*int( (form['elo'] - 5 - erange/4.0) / 10.0)
        form['pemax'] = 10*int( (form['ehi'] + 5 + erange/4.0) / 10.0)

        cmds = ["""plot_mu({group:s}, {plotopt:s}, delay_draw=True, label='data',
        emin={pemin:.1f}, emax={pemax:.1f}, title='{filename:s}')"""]

        if hasattr(dgroup, 'lcf_result'):
            with_comps = "Components" in form['plotchoice']
            delay = 'delay_draw=True' if with_comps else 'delay_draw=False'
            xarr = "{group:s}.lcf_result.xdata"
            yfit = "{group:s}.lcf_result.yfit"
            ycmp = "{group:s}.lcf_result.ycomps"
            cmds.append("plot(%s, %s, label='fit', zorder=30, %s)" % (xarr, yfit, delay))
            ncomps = len(dgroup.lcf_result.ycomps)
            if with_comps:
                for i, key in enumerate(dgroup.lcf_result.ycomps):
                    delay = 'delay_draw=False' if i==(ncomps-1) else 'delay_draw=True'
                    cmds.append("plot(%s, %s['%s'], label='%s', %s)" % (xarr, ycmp, key, key, delay))

        if form['show_e0']:
            cmds.append("plot_axvline({e0:1f}, color='#DDDDCC', zorder=-10)")
        if form['show_fitrange']:
            cmds.append("plot_axvline({elo_abs:1f}, color='#EECCCC', zorder=-10)")
            cmds.append("plot_axvline({ehi_abs:1f}, color='#EECCCC', zorder=-10)")

        script = "\n".join(cmds)
        self.controller.larch.eval(script.format(**form))
