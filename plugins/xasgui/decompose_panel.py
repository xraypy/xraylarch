#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import six

import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv

import numpy as np

from functools import partial
from collections import OrderedDict

from lmfit.printfuncs import gformat

from larch import Group
from larch.utils import index_of
from larch.wxlib import (BitmapButton, FloatCtrl, get_icon, SimpleText,
                         pack, Button, HLine, Choice, Check, CEN, RCEN,
                         LCEN, Font)

from larch_plugins.xasgui.taskpanel import TaskPanel
from larch_plugins.math.lincombo_fitting import get_arrays

np.seterr(all='ignore')

# plot options:
norm   = six.u('Normalized \u03bC(E)')
dmude  = six.u('d\u03bC(E)/dE')
chik   = six.u('\u03c7(k)')
noplot = '<no plot>'
noname = '<none>'

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

FitSpace_Choices = [norm, dmude, chik]
Plot_Choices = ['PCA Components', 'Component Weights',
                'Data + Fit + Compononents']

defaults = dict(e0=0, xmin=-30, xmax=70, fitspace=norm, weight_min=0.005,
                max_components=500) # , show_e0=True, show_fitrange=True)

class PCAPanel(TaskPanel):
    """PCA Panel"""

    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='pca_config',
                           config=defaults,
                           title='Principal Component Analysis',
                           **kws)
        self.result = None

    def process(self, dgroup, **kws):
        """ handle PCA processing"""
        if self.skip_process:
            return
        form = self.read_form()

    def build_display(self):
        titleopts = dict(font=Font(12), colour='#AA0000')
        panel = self.panel
        wids = self.wids
        self.skip_process = True

        wids['fitspace'] = Choice(panel, choices=FitSpace_Choices, size=(175, -1))
        wids['fitspace'].SetStringSelection(norm)
        wids['plotchoice'] = Choice(panel, choices=Plot_Choices,
                                  size=(175, -1), action=self.onPlot)
        wids['plotchoice'].SetSelection(0)

        add_text = self.add_text

        opts = dict(digits=2, increment=1.0, relative_e0=True)

        w_e0   = self.add_floatspin('e0', value=0, **opts)
        w_xmin = self.add_floatspin('xmin', value=defaults['xmin'], **opts)
        w_xmax = self.add_floatspin('xmax', value=defaults['xmax'], **opts)

        w_wmin = self.add_floatspin('weight_min', digits=4,
                                    value=defaults['weight_min'],
                                    increment=0.001, with_pin=False,
                                    min_val=0, max_val=0.5)

        w_mcomps = self.add_floatspin('max_components', digits=0,
                                    value=defaults['max_components'],
                                    increment=1, with_pin=False, min_val=0)

        b_build_model = Button(panel, 'Build Model With Selected Groups',
                                     size=(225, -1),  action=self.onBuildPCAModel)

        wids['fit_group'] = Button(panel, 'Test Current Group with Model', size=(225, -1),
                                   action=self.onFitGroup)

        wids['save_model'] = Button(panel, 'Save PCA Model', size=(150, -1),
                                    action=self.onSavePCAModel)
        wids['load_model'] = Button(panel, 'Load PCA Model', size=(150, -1),
                                    action=self.onLoadPCAModel)

        wids['fit_group'].Disable()
        wids['load_model'].Disable()
        wids['save_model'].Disable()

        sview = self.wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        sview.AppendTextColumn(' Component',    width=75)
        sview.AppendTextColumn(' Weight',       width=100)
        sview.AppendTextColumn(' Significant?', width=75)

        for col in range(sview.ColumnCount):
            this = sview.Columns[col]
            align = wx.ALIGN_LEFT if col == 0 else wx.ALIGN_RIGHT
            this.Sortable = False
            this.Alignment = this.Renderer.Alignment = align
        sview.SetMinSize((275, 250))

        wids['status'] = SimpleText(panel, ' ')

        wids['fit_chi2'] = SimpleText(panel, '--')


        panel.Add(SimpleText(panel, ' Principal Component Analysis', **titleopts), dcol=4)

        add_text('Array to Use: ', newrow=True)
        panel.Add(wids['fitspace'], dcol=2)
        panel.Add(wids['load_model'], dcol=2)

        add_text('Plot : ', newrow=True)
        panel.Add(wids['plotchoice'], dcol=2)

        panel.Add(wids['save_model'], dcol=2)

        add_text('E0: ')
        panel.Add(w_e0, dcol=3)
        # panel.Add(wids['show_e0'])

        add_text('Fit Range: ')
        panel.Add(w_xmin)
        add_text(' : ', newrow=False)
        panel.Add(w_xmax)
        #panel.Add(wids['show_fitrange'])

        add_text('Minimum Weight: ')
        panel.Add(w_wmin)
        add_text('Max Components:', dcol=1, newrow=True)
        panel.Add(w_mcomps)

        add_text('Status: ')
        panel.Add(wids['status'], dcol=3)

        panel.Add(HLine(panel, size=(550, 2)), dcol=5, newrow=True)

        panel.Add(b_build_model, dcol=3, newrow=True)
        panel.Add(wids['fit_group'], dcol=3)

        panel.Add(wids['stats'], dcol=3, drow=4, newrow=True)
        panel.Add(SimpleText(panel, 'chi-square = '))
        panel.Add(wids['fit_chi2'])
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((10, 10), 0, LCEN, 3)
        sizer.Add(panel, 1, LCEN, 3)
        pack(self, sizer)
        self.skip_process = False

    def fill_form(self, dgroup):
        opts = self.get_config(dgroup)
        self.dgroup = dgroup
        if isinstance(dgroup, Group):
            d_emin = min(dgroup.energy)
            d_emax = max(dgroup.energy)
            if opts['e0'] < d_emin or opts['e0'] > d_emax:
                opts['e0'] = dgroup.e0

        self.skip_process = True
        wids = self.wids
        e0 = None
        for attr in ('e0', 'xmin', 'xmax', 'weight_min'):
            val = opts.get(attr, None)
            if attr == 'e0':
                e0 = val
            if val is not None:
                if attr in ('xmin', 'xmax') and e0 is not None:
                    val += e0
                wids[attr].SetValue(val)

#         for attr in ('show_e0', 'show_fitrange'):
#             wids[attr].SetValue(opts.get(attr, True))

        for attr in ('fitspace',):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])

        self.skip_process = False

    def plot_pca_weights(self, win=2):
        if self.result is None or self.skip_plotting:
            return
        form = self.read_form()
        cmd = "plot_pca_weights(pca_result, max_components=%d, min_weight=%.3f, win=%d)"
        max_comps = form['max_components']
        min_weight = form['weight_min']
        self.larch_eval(cmd % (max_comps, min_weight, win))

    def plot_pca_components(self, win=1):
        if self.result is None or self.skip_plotting:
            return
        form = self.read_form()
        cmd = "plot_pca_components(pca_result, max_components=%d, min_weight=%.3f, win=%d)"
        max_comps = form['max_components']
        min_weight = form['weight_min']
        self.larch_eval(cmd % (max_comps, min_weight, win))

    def plot_pca_fit(self, win=1):
        if self.result is None or self.skip_plotting:
            return
        form = self.read_form()
        dgroup = self.controller.get_group()
        if hasattr(dgroup, 'pca_result'):
            self.larch_eval("plot_pca_fit(%s)" % dgroup.groupname)

    def onPlot(self, event=None):
        form = self.read_form()
        if self.skip_plotting:
            return
        pchoice = form['plotchoice'].lower()
        if pchoice.startswith('pca'):
            self.plot_pca_components()
        elif pchoice.startswith('component w'):
            self.plot_pca_weights()
        else:
            self.plot_pca_fit()

    def onFitGroup(self, event=None):
        form = self.read_form()
        if self.result is None:
            print("need result first!")
        ncomps = int(form['max_components'])
        gname = form['groupname']
        cmd = "pca_fit(%s, pca_result, ncomps=%d)" % (gname, ncomps)
        self.larch_eval(cmd)
        dgroup = self.controller.get_group()
        pca_chisquare = dgroup.pca_result.chi_square
        self.wids['fit_chi2'].SetLabel(gformat(pca_chisquare))
        self.plot_pca_fit()


    def onBuildPCAModel(self, event=None):
        self.wids['status'].SetLabel(" training model...")
        form = self.read_form()
        selected_groups = self.controller.filelist.GetCheckedStrings()
        groups = [self.controller.file_groups[cn] for cn in selected_groups]
        for gname in groups:
            grp = self.controller.get_group(gname)
            if not hasattr(grp, 'norm'):
                self.parent.nb_panels[0].process(grp)

        groups = ', '.join(groups)
        opts = dict(groups=groups, arr='norm', xmin=form['xmin'], xmax=form['xmax'])
        cmd = "pca_result = pca_train([{groups}], arrayname='{arr}', xmin={xmin:.2f}, xmax={xmax:.2f})"

        self.larch_eval(cmd.format(**opts))
        r = self.result = self.larch_get('pca_result')
        ncomps = len(r.components)
        wmin = form['weight_min']
        nsig = len(np.where(r.variances > wmin)[0])

        status = " PCA model built, %d components, %d with weight > %.3f"
        self.wids['status'].SetLabel(status %  (ncomps, nsig, wmin))
        self.wids['max_components'].SetValue(min(ncomps, 1+nsig))

        for b in ('fit_group',): # , 'save_model'):
            self.wids[b].Enable()

        self.wids['stats'].DeleteAllItems()
        for i, val in enumerate(r.variances):
            sig = {True: 'Yes', False: 'No'}[val > wmin]
            self.wids['stats'].AppendItem((' #%d' % (i+1), gformat(val), sig))

        self.plot_pca_components()
        self.plot_pca_weights()

    def onSavePCAModel(self, event=None):
        form = self.read_form()
        print("SAVE model: form: ", form)

    def onLoadPCAModel(self, event=None):
        form = self.read_form()
