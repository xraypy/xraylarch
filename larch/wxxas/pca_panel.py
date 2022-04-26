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
from larch.utils import get_cwd
from larch.wxlib import (BitmapButton, FloatCtrl, get_icon, SimpleText,
                         pack, Button, HLine, Choice, Check, CEN, RIGHT,
                         LEFT, Font, FileSave, FileOpen, DataTableGrid)

from .taskpanel import TaskPanel, autoset_fs_increment
from larch.math.lincombo_fitting import get_arrays

np.seterr(all='ignore')

# plot options:
norm   = 'Normalized \u03bC(E)'
flatmu = 'Flattened \u03bC(E)'
rawmu  = 'Raw \u03bC(E)'
dmude  = 'd\u03bC(E)/dE'
chik   = '\u03c7(k)'
noplot = '<no plot>'
noname = '<none>'


DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES


FITSPACES = {norm:'norm', flatmu:'flat', dmude:'dmude', chik:'chik',
             rawmu:'mu'}

FitSpace_Choices = list(FITSPACES.keys())

Plot_Choices = ['PCA Components',
                'Data + Fit',
                'Data + Fit + Components']

# max number of *reported* PCA weights after fit
MAX_COMPS = 30

class PCAPanel(TaskPanel):
    """PCA Panel"""

    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='pca_config',
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


        add_text = self.add_text

        opts = dict(digits=2, increment=1.0)
        defaults = self.get_defaultconfig()
        w_xmin = self.add_floatspin('xmin', value=defaults['xmin'], **opts)
        w_xmax = self.add_floatspin('xmax', value=defaults['xmax'], **opts)

        w_wmin = self.add_floatspin('weight_min', digits=4,
                                    value=defaults['weight_min'],
                                    increment=0.0005, with_pin=False,
                                    min_val=0,  max_val=0.5,
                                    action=self.onSet_WeightMin)

        self.wids['weight_auto'] = Check(panel, default=True, label='auto?')

        w_mcomps = self.add_floatspin('max_components', digits=0,
                                      value=defaults['max_components'],
                                      increment=1, with_pin=False, min_val=0)

        wids['build_model'] = Button(panel, 'Build Model With Selected Groups',
                                     size=(250, -1),  action=self.onBuildPCAModel)

        wids['plot_model'] = Button(panel, 'Plot Components and Statistics',
                                    size=(250, -1),  action=self.onPlotPCAModel)

        wids['fit_group'] = Button(panel, 'Test Current Group with Model', size=(250, -1),
                                   action=self.onFitGroup)
        wids['fit_selected'] = Button(panel, 'Test Selected Groups with Model', size=(250, -1),
                                   action=self.onFitSelected)

        wids['save_model'] = Button(panel, 'Save PCA Model', size=(125, -1),
                                    action=self.onSavePCAModel)
        wids['load_model'] = Button(panel, 'Load PCA Model', size=(125, -1),
                                    action=self.onLoadPCAModel)

        wids['fit_group'].Disable()
        wids['fit_selected'].Disable()
        wids['load_model'].Enable()
        wids['save_model'].Disable()

        collabels = [' Variance ', ' IND value ', 'IND/IND_Best']
        colsizes = [90, 90, 90]
        coltypes = ['float:12,6', 'float:12,6', 'float:12,5']
        coldefs  = [0.0, 0.0, 1.0]

        wids['pca_table'] = DataTableGrid(panel, nrows=MAX_COMPS,
                                          collabels=collabels,
                                          datatypes=coltypes,
                                          defaults=coldefs,
                                          colsizes=colsizes, rowlabelsize=60)

        wids['pca_table'].SetMinSize((425, 150))
        wids['pca_table'].EnableEditing(False)


        collabels = [' Group ', ' Chi-square ', ' Scale ']
        colsizes = [200, 80, 80]
        coltypes = ['string', 'string', 'string']
        coldefs  = [' ', '0.0', '1.0']
        for i in range(MAX_COMPS):
            collabels.append(f'Comp {i+1:d}')
            colsizes.append(80)
            coltypes.append('string')
            coldefs.append('0.0')

        wids['fit_table'] = DataTableGrid(panel, nrows=50,
                                          collabels=collabels,
                                          datatypes=coltypes,
                                          defaults=coldefs,
                                          colsizes=colsizes, rowlabelsize=60)

        wids['fit_table'].SetMinSize((625, 200))
        wids['fit_table'].EnableEditing(False)


        wids['status'] = SimpleText(panel, ' ')

        panel.Add(SimpleText(panel, 'Principal Component Analysis',
                             size=(350, -1), **self.titleopts), style=LEFT, dcol=4)

        add_text('Array to Use: ', newrow=True)
        panel.Add(wids['fitspace'], dcol=2)
        add_text('Energy Range: ', newrow=True)
        panel.Add(w_xmin)
        add_text(' : ', newrow=False)
        panel.Add(w_xmax)
        # panel.Add(wids['show_fitrange'])

        panel.Add(wids['load_model'], dcol=1, newrow=True)
        panel.Add(wids['save_model'], dcol=1)

        panel.Add(wids['build_model'], dcol=3, newrow=True)
        panel.Add(wids['plot_model'],  dcol=2)


        add_text('Min Weight: ')
        panel.Add(w_wmin)
        panel.Add(wids['weight_auto'], dcol=2)
        panel.Add(wids['pca_table'], dcol=6, newrow=True)

        add_text('Status: ')
        panel.Add(wids['status'], dcol=6)


        panel.Add(HLine(panel, size=(550, 2)), dcol=5, newrow=True)

        add_text('Use this PCA Model : ', dcol=1, newrow=True)
        add_text('Max Components:', dcol=1, newrow=False)
        panel.Add(w_mcomps, dcol=2)

        panel.Add(wids['fit_group'], dcol=3, newrow=True)
        panel.Add(wids['fit_selected'], dcol=3, newrow=False)

        panel.Add(wids['fit_table'], dcol=6, newrow=True)


        panel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((10, 10), 0, LEFT, 3)
        sizer.Add(panel, 1, LEFT, 3)
        pack(self, sizer)
        self.skip_process = False

    def onSet_WeightMin(self, evt=None, value=None):
        "handle setting edge step"
        wmin = self.wids['weight_min'].GetValue()
        self.wids['weight_auto'].SetValue(0)
        self.update_config({'weight_min': wmin})
        # autoset_fs_increment(self.wids['weight_min'], wmin)

    def fill_form(self, dgroup):
        opts = self.get_config(dgroup)
        self.dgroup = dgroup
        if isinstance(dgroup, Group):
            d_emin = min(dgroup.energy)
            d_emax = max(dgroup.energy)
            xmin, xmax = opts['xmin'], opts['xmax']
            if xmin < d_emin or xmin > d_emax or abs(xmin-dgroup.e0) > 500:
                opts['xmin'] = -40 + int(dgroup.e0/10.0)*10
            if xmax < d_emin or xmax > d_emax or abs(xmax-dgroup.e0) > 500:
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
                  'max_components', 'fitspace')

        out = {a: conf[a] for a in attrs}
        for checked in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            self.update_config(out, dgroup=dgroup)


    def plot_pca_weights(self, win=2):
        if self.result is None or self.skip_plotting:
            return
        self.larch_eval(f"plot_pca_weights(pca_result, win={win:d})")

    def plot_pca_components(self, win=1):
        if self.result is None or self.skip_plotting:
            return
        self.larch_eval(f"plot_pca_components(pca_result, win={win:d})")

    def plot_pca_fit(self, win=1):
        if self.result is None or self.skip_plotting:
            return
        dgroup = self.controller.get_group()
        if hasattr(dgroup, 'pca_result'):
            self.larch_eval(f"plot_pca_fit({dgroup.groupname:s}, with_components=True, win={win:d})")

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

    def onFitSelected(self, event=None):
        form = self.read_form()
        if self.result is None:
            print("need result first!")
        ncomps = int(form['max_components'])

        selected_groups = self.controller.filelist.GetCheckedStrings()
        groups = [self.controller.file_groups[cn] for cn in selected_groups]
        grid_data = []
        fnames = []
        for gname in groups:
            grp = self.controller.get_group(gname)
            if not hasattr(grp, 'norm'):
                self.xasmain.process_normalization(grp)
            cmd = f"pca_fit({gname:s}, pca_result, ncomps={ncomps:d})"
            self.larch_eval(cmd)
            grp.journal.add('pca_fit', cmd)

            _data = [grp.filename,
                     gformat(grp.pca_result.chi_square),
                     gformat(grp.pca_result.data_scale)]
            _data.extend([gformat(w) for w in grp.pca_result.weights])
            grid_data.append(_data)
            fnames.append(grp.filename)

        for row in self.wids['fit_table'].table.data:
            if len(row) < 2 or row[0] not in fnames:
                grid_data.append(row)

        self.wids['fit_table'].table.data = grid_data
        self.wids['fit_table'].table.View.Refresh()

        self.plot_pca_fit()


    def onFitGroup(self, event=None):
        form = self.read_form()
        if self.result is None:
            print("need result first!")
        ncomps = int(form['max_components'])
        gname = form['groupname']
        cmd = f"pca_fit({gname:s}, pca_result, ncomps={ncomps:d})"
        self.larch_eval(cmd)

        dgroup = self.controller.get_group()
        dgroup.journal.add('pca_fit', cmd)

        thisrow = [dgroup.filename,
                   gformat(dgroup.pca_result.chi_square),
                   gformat(dgroup.pca_result.data_scale)]
        wts = [gformat(w) for w in dgroup.pca_result.weights]
        thisrow.extend(wts)
        grid_data = [thisrow]
        for row in self.wids['fit_table'].table.data:
            if len(row) < 2 or row[0] != dgroup.filename:
                grid_data.append(row)


        self.wids['fit_table'].table.data = grid_data
        self.wids['fit_table'].table.View.Refresh()

        self.plot_pca_fit()

    def onBuildPCAModel(self, event=None):
        self.wids['status'].SetLabel(" training model...")
        form = self.read_form()
        selected_groups = self.controller.filelist.GetCheckedStrings()
        groups = [self.controller.file_groups[cn] for cn in selected_groups]
        for gname in groups:
            grp = self.controller.get_group(gname)
            if not hasattr(grp, 'norm'):
                self.xasmain.process_normalization(grp)

        groups = ', '.join(groups)
        opts = dict(groups=groups, arr='norm', xmin=form['xmin'], xmax=form['xmax'])

        opts['arr'] = FITSPACES.get(form['fitspace'], 'norm')
        cmd = "pca_result = pca_train([{groups}], arrayname='{arr}', xmin={xmin:.2f}, xmax={xmax:.2f})"

        self.larch_eval(cmd.format(**opts))
        self.use_model('pca_result')

    def use_model(self, modelname='pca_result'):
        form = self.read_form()
        r = self.result = self.larch_get(modelname)
        ncomps = len(r.components)
        wmin = form['weight_min']
        if self.wids['weight_auto'].GetValue():
            nsig = int(r.nsig)
            wmin = r.variances[nsig-1]
            if nsig <= len(r.variances):
                wmin = (r.variances[nsig] + r.variances[nsig-1])/2.0
            self.wids['weight_min'].SetValue(wmin)
        else:
            nsig = len(np.where(r.variances > wmin)[0])


        status = " Model built, %d of %d components have weight > %.4f"
        self.wids['status'].SetLabel(status %  (nsig, ncomps, wmin))
        self.wids['max_components'].SetValue(nsig+1)

        for b in ('fit_group', 'fit_selected', 'save_model'):
            self.wids[b].Enable()

        grid_data = []
        ind = [i for i in r.ind]
        ind.extend([0,0,0])
        ind_best = ind[nsig]
        for i, var in enumerate(r.variances):
            grid_data.append([var, ind[i+1], ind[i+1]/ind_best])
        self.wids['pca_table'].table.data = grid_data
        self.wids['pca_table'].table.View.Refresh()
        self.wids['fit_table'].table.data = []
        self.wids['fit_table'].table.Clear()
        self.wids['fit_table'].table.View.Refresh()

        self.plot_pca_components()
        self.plot_pca_weights()

    def onPlotPCAModel(self, event=None):
        self.plot_pca_components()
        self.plot_pca_weights()

    def onSavePCAModel(self, event=None):
        form = self.read_form()
        if self.result is None:
            print("need result first!")
            retrun
        wildcard = 'Larch PCA Model (*.pcamod)|*.pcamod|All files (*.*)|*.*'
        fname = time.strftime('%Y%b%d_%H%M.pcamod')
        path = FileSave(self, message='Save PCA Model',
                        wildcard=wildcard,
                        default_file=fname)
        if path is not None:
            self.larch.eval(f"save_pca_model(pca_result, '{path:s}')")
            self.write_message("Saved PCA Model to '%s'" % path, 0)

    def onLoadPCAModel(self, event=None):
        form = self.read_form()
        wildcard = 'Larch PCA Model (*.pcamod)|*.pcamod|All files (*.*)|*.*'
        path = FileOpen(self, message="Read PCA Model",
                        wildcard=wildcard, default_file='a.pcamod')
        if path is None:
            return

        if hasattr(self.larch.symtable, 'pca_result'):
            self.larch.eval("old_pca_result = copy_group(pca_result)")

        self.larch.eval(f"pca_result = read_pca_model('{path:s}')")
        self.write_message("Read PCA Model from '%s'" % path, 0)
        self.use_model()
