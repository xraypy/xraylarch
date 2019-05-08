#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv

import numpy as np

from functools import partial
from collections import OrderedDict

from lmfit.printfuncs import gformat

from larch import Group
from larch.math import index_of
from larch.wxlib import (BitmapButton, FloatCtrl, get_icon, SimpleText,
                         pack, Button, HLine, Choice, Check, CEN, RCEN,
                         LCEN, Font)

from .taskpanel import TaskPanel, autoset_fs_increment, DataTableGrid
from larch.math.lincombo_fitting import get_arrays

np.seterr(all='ignore')

# plot options:
norm   = 'Normalized \u03bC(E)'
dmude  = 'd\u03bC(E)/dE'
chik   = '\u03c7(k)'
noplot = '<no plot>'
noname = '<none>'

DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

FitSpace_Choices = [norm, dmude, chik]
Plot_Choices = ['PCA Components', 'Component Weights', 'Data + Fit',
                'Data + Fit + Components']

defaults = dict(xmin=-5.e5, xmax=5.e5, fitspace=norm, weight_min=0.002,
                weight_auto=True, max_components=50)

# max number of *reported* PCA weights after fit
MAX_ROWS = 50

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
        panel = self.panel
        wids = self.wids
        self.skip_process = True

        wids['fitspace'] = Choice(panel, choices=FitSpace_Choices, size=(175, -1))
        wids['fitspace'].SetStringSelection(norm)
        wids['plotchoice'] = Choice(panel, choices=Plot_Choices,
                                  size=(175, -1), action=self.onPlot)
        wids['plotchoice'].SetSelection(0)

        add_text = self.add_text

        opts = dict(digits=2, increment=1.0)

        w_xmin = self.add_floatspin('xmin', value=defaults['xmin'], **opts)
        w_xmax = self.add_floatspin('xmax', value=defaults['xmax'], **opts)

        w_wmin = self.add_floatspin('weight_min', digits=4,
                                    value=defaults['weight_min'],
                                    increment=0.001, with_pin=False,
                                    min_val=0,  max_val=0.5,
                                    action=self.onSet_WeightMin)

        autoset_fs_increment(self.wids['weight_min'], defaults['weight_min'])


        self.wids['weight_auto'] = Check(panel, default=True, label='auto?')


        w_mcomps = self.add_floatspin('max_components', digits=0,
                                    value=defaults['max_components'],
                                    increment=1, with_pin=False, min_val=0)

        b_build_model = Button(panel, 'Build Model With Selected Groups',
                                     size=(275, -1),  action=self.onBuildPCAModel)

        wids['fit_group'] = Button(panel, 'Test Current Group with Model', size=(225, -1),
                                   action=self.onFitGroup)

        wids['save_model'] = Button(panel, 'Save PCA Model', size=(150, -1),
                                    action=self.onSavePCAModel)
        wids['load_model'] = Button(panel, 'Load PCA Model', size=(150, -1),
                                    action=self.onLoadPCAModel)

        wids['fit_group'].Disable()
        wids['load_model'].Disable()
        wids['save_model'].Disable()

        collabels = [' Variance ', ' IND value ', ' IND / IND_Best',
                     ' Factor Weight' ]

        colsizes = [100, 100, 100, 200]
        coltypes = ['float:12,6', 'float:12,6', 'float:12,5', 'string']
        coldefs  = [0.0, 0.0, 1.0, '0.0']

        wids['table'] = DataTableGrid(panel, nrows=MAX_ROWS,
                                      collabels=collabels,
                                      datatypes=coltypes,
                                      defaults=coldefs,
                                      colsizes=colsizes, rowlabelsize=60)

        wids['table'].SetMinSize((625, 175))
        wids['table'].EnableEditing(False)
#
#         sview = self.wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
#         sview.AppendTextColumn(' Component',    width=75)
#         sview.AppendTextColumn(' Weight',       width=100)
#         sview.AppendTextColumn(' Significant?', width=75)
#
#         for col in range(sview.ColumnCount):
#             this = sview.Columns[col]
#             align = wx.ALIGN_LEFT if col == 0 else wx.ALIGN_RIGHT
#             this.Sortable = False
#             this.Alignment = this.Renderer.Alignment = align
#         sview.SetMinSize((275, 250))

        wids['status'] = SimpleText(panel, ' ')
        rfont = self.GetFont()
        rfont.SetPointSize(rfont.GetPointSize()+1)

        wids['fit_chi2'] = SimpleText(panel, '0.000', font=rfont)
        wids['fit_dscale'] = SimpleText(panel, '1.000', font=rfont)

        panel.Add(SimpleText(panel, ' Principal Component Analysis',
                             **self.titleopts), dcol=4)

        add_text('Array to Use: ', newrow=True)
        panel.Add(wids['fitspace'], dcol=2)
        panel.Add(wids['load_model'], dcol=2)

        add_text('Plot : ', newrow=True)
        panel.Add(wids['plotchoice'], dcol=2)

        panel.Add(wids['save_model'], dcol=2)

        add_text('Fit Energy Range: ')
        panel.Add(w_xmin)
        add_text(' : ', newrow=False)
        panel.Add(w_xmax)
        #panel.Add(wids['show_fitrange'])

        add_text('Min Weight: ')
        panel.Add(w_wmin)
        panel.Add(wids['weight_auto'])
        add_text('Max Components:', dcol=1, newrow=True)
        panel.Add(w_mcomps)

        panel.Add(Button(panel, 'Copy To Selected Groups', size=(200, -1),
                         action=partial(self.onCopyParam, 'pca')),
                  dcol=2)

        add_text('Status: ')
        panel.Add(wids['status'], dcol=3)

        panel.Add(HLine(panel, size=(550, 2)), dcol=5, newrow=True)

        panel.Add(b_build_model, dcol=5, newrow=True)

        panel.Add(wids['table'], dcol=5, newrow=True)
        panel.Add(wids['fit_group'], dcol=3, newrow=True)

        add_text('chi-square: ')
        panel.Add(wids['fit_chi2'])
        add_text('scale factor: ')
        panel.Add(wids['fit_dscale'])

#
#         ## add weights report: slightly tricky layout
#         ## working with GridBagSizer under gridpanel...
#         icol = panel.icol - 2
#         irow = panel.irow
#         pstyle, ppad = panel.itemstyle, panel.pad
#
#         panel.sizer.Add(SimpleText(panel, 'data scalefactor = '),
#                         (irow+1, icol), (1, 1), pstyle, ppad)
#         panel.sizer.Add(wids['fit_dscale'],
#                         (irow+1, icol+1), (1, 1), pstyle, ppad)
#         irow +=1
#         for i in range(1, NWTS+1):
#             wids['fit_wt%d' % i] = SimpleText(panel, '--', font=rfont)
#             panel.sizer.Add(SimpleText(panel, 'weight_%d ='%i, font=rfont),
#                             (irow+i, icol), (1, 1), pstyle, ppad)
#             panel.sizer.Add(wids['fit_wt%d'%i],
#                             (irow+i, icol+1), (1, 1), pstyle, ppad)
#
        panel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((10, 10), 0, LCEN, 3)
        sizer.Add(panel, 1, LCEN, 3)
        pack(self, sizer)
        self.skip_process = False

    def onSet_WeightMin(self, evt=None, value=None):
        "handle setting edge step"
        wmin = self.wids['weight_min'].GetValue()
        self.wids['weight_auto'].SetValue(0)
        self.update_config({'weight_min': wmin})
        autoset_fs_increment(self.wids['weight_min'], wmin)

    def fill_form(self, dgroup):
        opts = self.get_config(dgroup)
        self.dgroup = dgroup
        if isinstance(dgroup, Group):
            d_emin = min(dgroup.energy)
            d_emax = max(dgroup.energy)
            if opts['xmin'] < d_emin:
                opts['xmin'] = -40 + int(dgroup.e0/10.0)*10
            if opts['xmax'] > d_emax:
                opts['xmax'] =  110 + int(dgroup.e0/10.0)*10

        self.skip_process = True
        wids = self.wids
        for attr in ('xmin', 'xmax', 'weight_min'):
            val = opts.get(attr, None)
            if val is not None:
                wids[attr].SetValue(val)

        for attr in ('fitspace',):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])

        self.skip_process = False

    def onCopyParam(self, name=None, evt=None):
        conf = self.get_config()
        conf.update(self.read_form())
        attrs =  ('xmin', 'xmax', 'weight_min',
                  'max_components', 'fitspace', 'plotchoice')

        out = {a: conf[a] for a in attrs}
        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            self.update_config(out, dgroup=dgroup)


    def plot_pca_weights(self, win=2):
        if self.result is None or self.skip_plotting:
            return
        form = self.read_form()
        cmd = "plot_pca_weights(pca_result, ncomps=%d, min_weight=%.3f, win=%d)"
        max_comps = form['max_components']
        min_weight = form['weight_min']
        self.larch_eval(cmd % (max_comps, min_weight, win))

    def plot_pca_components(self, win=1):
        if self.result is None or self.skip_plotting:
            return
        form = self.read_form()
        cmd = "plot_pca_components(pca_result, ncomps=%d, min_weight=%.3f, win=%d)"
        max_comps = form['max_components']
        min_weight = form['weight_min']
        self.larch_eval(cmd % (max_comps, min_weight, win))

    def plot_pca_fit(self, win=1):
        if self.result is None or self.skip_plotting:
            return
        form = self.read_form()
        with_comps = repr('components' in form['plotchoice'].lower())
        dgroup = self.controller.get_group()
        if hasattr(dgroup, 'pca_result'):
            a = (dgroup.groupname, win, with_comps)
            self.larch_eval("plot_pca_fit(%s, win=%d, with_components=%s)" % a)

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
        self.wids['fit_chi2'].SetLabel(gformat(dgroup.pca_result.chi_square))
        self.wids['fit_dscale'].SetLabel(gformat(dgroup.pca_result.data_scale))

        grid_data = self.wids['table'].table.data
        for g in grid_data: g[3] = '-'

        for i, wt in enumerate(dgroup.pca_result.weights):
            grid_data[i][3] = gformat(wt)

        self.wids['table'].table.data = grid_data
        self.wids['table'].table.View.Refresh()
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
        if self.wids['weight_auto'].GetValue():
            nsig = r.nsig
            wmin = r.variances[nsig-1]
            self.wids['weight_min'].SetValue(wmin)
        else:
            nsig = np.where(r.variances < wmin)[0][0] - 1


        status = " Model built, %d of %d components have weight > %.4f"
        self.wids['status'].SetLabel(status %  (nsig, ncomps, wmin))
        self.wids['max_components'].SetValue(nsig+1)

        for b in ('fit_group',):
            self.wids[b].Enable()

        grid_data = []
        ind = [i for i in r.ind]
        ind.extend([0,0,0])
        ind_best = ind[r.nsig]
        for i, var in enumerate(r.variances):
            grid_data.append([var, ind[i+1], ind[i+1]/ind_best,  '0.0'])
        self.wids['table'].table.data = grid_data
        self.wids['table'].table.View.Refresh()

        self.plot_pca_components()
        self.plot_pca_weights()

    def onSavePCAModel(self, event=None):
        form = self.read_form()
        print("SAVE model: form: ", form)

    def onLoadPCAModel(self, event=None):
        form = self.read_form()
