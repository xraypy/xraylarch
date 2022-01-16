#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import wx
import wx.grid as wxgrid
import numpy as np
import pickle
import base64

from functools import partial

from lmfit.printfuncs import gformat
from larch import Group
from larch.math import index_of
from larch.wxlib import (BitmapButton, TextCtrl, FloatCtrl, get_icon,
                         SimpleText, pack, Button, HLine, Choice, Check,
                         NumericCombo, CEN, LEFT, Font, FileSave, FileOpen)
from larch.io import read_csv
from larch.utils.strutils import fix_varname

from .taskpanel import TaskPanel, DataTableGrid

# plot options:
norm   = 'Normalized \u03bC(E)'
dmude  = 'd\u03bC(E)/dE'
chik   = '\u03c7(k)'
noplot = '<no plot>'
noname = '<none>'

CSV_WILDCARDS = "CSV Files(*.csv,*.dat)|*.csv*;*.dat|All files (*.*)|*.*"
MODEL_WILDCARDS = "Regression Model Files(*.regmod,*.dat)|*.regmod*;*.dat|All files (*.*)|*.*"

FitSpace_Choices = [norm, dmude, chik]
Plot_Choices = ['Mean Spectrum + Active Energies',
                'Spectra Stack',
                'Predicted External Varliable']

Regress_Choices = ['Partial Least Squares', 'LassoLars']

defaults = dict(fitspace=norm, varname='valence', xmin=-5.e5, xmax=5.e5,
                scale=True, cv_folds=None, cv_repeats=3, fit_intercept=True,
                use_lars=True, alpha=0.01)

MAX_ROWS = 1000

def make_steps(max=1, decades=8):
    steps = [1.0]
    for i in range(6):
        steps.extend([(j*10**(-(1+i))) for j in (5, 2, 1)])
    return steps

class RegressionPanel(TaskPanel):
    """Regression Panel"""
    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller,
                           configname='regression_config', config=defaults,
                           title='Regression and Feature Selection', **kws)
        self.result = None
        self.save_csvfile   = 'RegressionData.csv'
        self.save_modelfile = 'Model.regmod'

    def process(self, dgroup, **kws):
        """ handle processing"""
        if self.skip_process:
            return
        self.skip_process = True
        form = self.read_form()

    def build_display(self):
        panel = self.panel
        wids = self.wids
        self.skip_process = True

        wids['fitspace'] = Choice(panel, choices=FitSpace_Choices, size=(250, -1))
        wids['fitspace'].SetStringSelection(norm)
        # wids['plotchoice'] = Choice(panel, choices=Plot_Choices,
        #                           size=(250, -1), action=self.onPlot)

        wids['method'] = Choice(panel, choices=Regress_Choices, size=(250, -1),
                                action=self.onRegressMethod)

        add_text = self.add_text

        opts = dict(digits=2, increment=1.0)

        w_xmin = self.add_floatspin('xmin', value=defaults['xmin'], **opts)
        w_xmax = self.add_floatspin('xmax', value=defaults['xmax'], **opts)
        wids['alpha'] =  NumericCombo(panel, make_steps(), fmt='%.6g',
                                      default_val=0.01, width=100)

        wids['auto_scale_pls'] = Check(panel, default=True, label='auto scale?')
        wids['auto_alpha'] = Check(panel, default=False, label='auto alpha?')

        wids['fit_intercept'] = Check(panel, default=True, label='fit intercept?')

        wids['save_csv'] = Button(panel, 'Save CSV File', size=(150, -1),
                                    action=self.onSaveCSV)
        wids['load_csv'] = Button(panel, 'Load CSV File', size=(150, -1),
                                    action=self.onLoadCSV)

        wids['save_model'] = Button(panel, 'Save Model', size=(150, -1),
                                    action=self.onSaveModel)
        wids['save_model'].Disable()

        wids['load_model'] = Button(panel, 'Load Model', size=(150, -1),
                                    action=self.onLoadModel)


        wids['train_model'] = Button(panel, 'Train Model From These Data',
                                     size=(275, -1),  action=self.onTrainModel)

        wids['fit_group'] = Button(panel, 'Predict Variable for Selected Groups',
                                   size=(275, -1), action=self.onPredictGroups)
        wids['fit_group'].Disable()


        w_cvfolds = self.add_floatspin('cv_folds', digits=0, with_pin=False,
                                       value=0, increment=1, min_val=-1)

        w_cvreps  = self.add_floatspin('cv_repeats', digits=0, with_pin=False,
                                       value=0, increment=1, min_val=-1)

        w_ncomps  = self.add_floatspin('ncomps', digits=0, with_pin=False,
                                       value=3, increment=1, min_val=1)

        wids['varname'] = wx.TextCtrl(panel, -1, 'valence', size=(150, -1))
        wids['stat1'] =  SimpleText(panel, ' - - - ')
        wids['stat2'] =  SimpleText(panel, ' - - - ')


        collabels = [' File /Group Name ', 'External Value',
                     'Predicted Value']
        colsizes = [300, 120, 120]
        coltypes = ['str', 'float:12,4', 'float:12,4']
        coldefs  = ['', 0.0, 0.0]

        wids['table'] = DataTableGrid(panel, nrows=MAX_ROWS,
                                      collabels=collabels,
                                      datatypes=coltypes,
                                      defaults=coldefs,
                                      colsizes=colsizes)

        wids['table'].SetMinSize((650, 225))

        wids['use_selected'] = Button(panel, 'Use Selected Groups',
                                      size=(150, -1),  action=self.onFillTable)

        panel.Add(SimpleText(panel, 'Feature Regression, Model Selection',
                             size=(350, -1), **self.titleopts), style=LEFT, dcol=4)

        add_text('Array to Use: ', newrow=True)
        panel.Add(wids['fitspace'], dcol=4)

        # add_text('Plot : ', newrow=True)
        # panel.Add(wids['plotchoice'], dcol=3)
        add_text('Fit Energy Range: ')
        panel.Add(w_xmin)
        add_text(' : ', newrow=False)
        panel.Add(w_xmax, dcol=3)
        add_text('Regression Method:')
        panel.Add(wids['method'], dcol=4)
        add_text('PLS # components: ')
        panel.Add(w_ncomps)
        panel.Add(wids['auto_scale_pls'], dcol=2)
        add_text('Lasso Alpha: ')
        panel.Add(wids['alpha'])
        panel.Add(wids['auto_alpha'], dcol=2)
        panel.Add(wids['fit_intercept'])
        wids['alpha'].Disable()
        wids['auto_alpha'].Disable()
        wids['fit_intercept'].Disable()

        add_text('Cross Validation: ')
        add_text(' # folds, # repeats: ', newrow=False)
        panel.Add(w_cvfolds, dcol=2)
        panel.Add(w_cvreps)

        panel.Add(HLine(panel, size=(600, 2)), dcol=6, newrow=True)

        add_text('Build Model: ', newrow=True)
        panel.Add(wids['use_selected'],   dcol=2)
        add_text('Attribute Name: ', newrow=False)
        panel.Add(wids['varname'], dcol=4)

        add_text('Read/Save Data: ', newrow=True)
        panel.Add(wids['load_csv'], dcol=3)
        panel.Add(wids['save_csv'], dcol=2)

        panel.Add(wids['table'], newrow=True, dcol=5) # , drow=3)

        panel.Add(HLine(panel, size=(550, 2)), dcol=5, newrow=True)
        panel.Add((5, 5), newrow=True)
        add_text('Train Model : ')
        panel.Add(wids['train_model'], dcol=3)
        panel.Add(wids['load_model'])

        add_text('Use This Model : ')
        panel.Add(wids['fit_group'], dcol=3)
        panel.Add(wids['save_model'])
        add_text('Fit Statistics : ')
        panel.Add(wids['stat1'], dcol=4)
        panel.Add((5, 5), newrow=True)
        panel.Add(wids['stat2'], dcol=4)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((10, 10), 0, LEFT, 3)
        sizer.Add(panel, 1, LEFT, 3)
        pack(self, sizer)
        self.skip_process = False

    def onRegressMethod(self, evt=None):
        meth = self.wids['method'].GetStringSelection()
        use_lasso = meth.lower().startswith('lasso')
        self.wids['alpha'].Enable(use_lasso)
        self.wids['auto_alpha'].Enable(use_lasso)
        self.wids['fit_intercept'].Enable(use_lasso)
        self.wids['fit_intercept'].Enable(use_lasso)
        self.wids['auto_scale_pls'].Enable(not use_lasso)
        self.wids['ncomps'].Enable(not use_lasso)


    def fill_form(self, dgroup):
        opts = self.get_config(dgroup)
        self.dgroup = dgroup
        if isinstance(dgroup, Group):
            if not hasattr(dgroup, 'norm'):
                self.xasmain.process_normalization(dgroup)
            d_emin = min(dgroup.energy)
            d_emax = max(dgroup.energy)
            if opts['xmin'] < d_emin:
                opts['xmin'] = -40 + int(dgroup.e0/10.0)*10
            if opts['xmax'] > d_emax:
                opts['xmax'] =  110 + int(dgroup.e0/10.0)*10

        self.skip_process = True
        wids = self.wids
        for attr in ('xmin', 'xmax', 'alpha'):
            val = opts.get(attr, None)
            if val is not None:
                if attr == 'alpha':
                    val = "%.6g" % val
                wids[attr].SetValue(val)

        for attr in ('fitspace',):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])

        self.skip_process = False

    def onFillTable(self, event=None):
        selected_groups = self.controller.filelist.GetCheckedStrings()
        varname = fix_varname(self.wids['varname'].GetValue())
        predname = varname + '_predicted'
        grid_data = []
        for fname in self.controller.filelist.GetCheckedStrings():
            gname = self.controller.file_groups[fname]
            grp = self.controller.get_group(gname)
            grid_data.append([fname, getattr(grp, varname, 0.0),
                              getattr(grp, predname, 0.0)])

        self.wids['table'].table.data = grid_data
        self.wids['table'].table.View.Refresh()

    def onTrainModel(self, event=None):
        opts = self.read_form()
        varname = opts['varname']
        predname = varname + '_predicted'

        grid_data = self.wids['table'].table.data
        groups = []
        for fname, yval, pval in grid_data:
            gname = self.controller.file_groups[fname]
            grp = self.controller.get_group(gname)
            setattr(grp, varname, yval)
            setattr(grp, predname, pval)
            groups.append(gname)

        cmds = ['# train linear regression model',
               'training_groups = [%s]' % ', '.join(groups)]

        copts = ["varname='%s'" % varname,
                 "xmin=%.4f" % opts['xmin'],
                 "xmax=%.4f" % opts['xmax']]

        arrname = 'norm'
        if opts['fitspace'] == dmude:
            arrname = 'dmude'
        elif opts['fitspace'] == chik:
            arrname = 'chi'
        copts.append("arrayname='%s'" % arrname)

        self.method = 'pls'
        if opts['method'].lower().startswith('lasso'):
            self.method = 'lasso'
            if opts['auto_alpha']:
                copts.append('alpha=None')
            else:
                copts.append('alpha=%s' % opts['alpha'])
            copts.append('use_lars=%s' % repr('lars' in opts['method'].lower()))
            copts.append('fit_intercept=%s' % repr(opts['fit_intercept']))
        else:
            copts.append('ncomps=%d' % opts['ncomps'])
            copts.append('scale=%s' % repr(opts['auto_scale_pls']))

        copts = ', '.join(copts)
        cmds.append("reg_model = %s_train(training_groups, %s)" %
                    (self.method, copts))
        self.larch_eval('\n'.join(cmds))
        reg_model = self.larch_get('reg_model')
        if reg_model is not None:
            self.write_message('Regression Model trained: %s' % opts['method'])
            rmse_cv = reg_model.rmse_cv
            if rmse_cv is not None:
                rmse_cv = "%.4f" % rmse_cv
            stat = "RMSE_CV = %s, RMSE = %.4f" % (rmse_cv, reg_model.rmse)
            self.wids['stat1'].SetLabel(stat)
            if self.method == 'lasso':
                stat = "Alpha = %.4f, %d active components"
                self.wids['stat2'].SetLabel(stat % (reg_model.alpha,
                                                    len(reg_model.active)))

                if opts['auto_alpha']:
                    self.wids['alpha'].add_choice(reg_model.alpha)

            else:
                self.wids['stat2'].SetLabel('- - - ')

            for i, row in enumerate(grid_data):
                grid_data[i] = [row[0], row[1], reg_model.ypred[i]]
            self.wids['table'].table.data = grid_data
            self.wids['table'].table.View.Refresh()

            if reg_model.cv_folds not in (0, None):
                self.wids['cv_folds'].SetValue(reg_model.cv_folds)
            if reg_model.cv_repeats not in (0, None):
                self.wids['cv_repeats'].SetValue(reg_model.cv_repeats)

            self.wids['save_model'].Enable()
            self.wids['fit_group'].Enable()

            wx.CallAfter(self.onPlotModel, model=reg_model)

    def onPredictGroups(self, event=None):
        opts = self.read_form()
        varname = opts['varname'] + '_predicted'

        grid_data = self.wids['table'].table.data
        gent = {}
        if len(grid_data[0][0].strip()) == 0:
            grid_data = []
        else:
            for i, row in enumerate(grid_data):
                gent[row[0]] = i

        for fname in self.controller.filelist.GetCheckedStrings():
            gname = self.controller.file_groups[fname]
            grp   = self.controller.get_group(gname)
            extval = getattr(grp, opts['varname'], 0)
            cmd = "%s.%s = %s_predict(%s, reg_model)" % (gname, varname,
                                                         self.method, gname)
            self.larch_eval(cmd)
            val = self.larch_get('%s.%s' % (gname, varname))
            if fname in gent:
                grid_data[gent[fname]][2] = val
            else:
                grid_data.append([fname, extval, val])
            self.wids['table'].table.data = grid_data
            self.wids['table'].table.View.Refresh()

    def onSaveModel(self, event=None):
        try:
            reg_model = self.larch_get('reg_model')
        except:
            reg_model = None
        if reg_model is None:
            self.write_message('Cannot Save Regression Model')
            return

        dlg = wx.FileDialog(self, message="Save Regression Model",
                            defaultDir=os.getcwd(),
                            defaultFile=self.save_modelfile,
                            wildcard=MODEL_WILDCARDS,
                            style=wx.FD_SAVE)
        fname = None
        if dlg.ShowModal() == wx.ID_OK:
            fname = dlg.GetPath()
        dlg.Destroy()
        if fname is None:
            return
        self.save_modelfile = os.path.split(fname)[1]
        text = str(base64.b64encode(pickle.dumps(reg_model)), 'utf-8')
        with open(fname, 'w') as fh:
            fh.write("%s\n" % text)
        fh.flush()
        fh.close()
        self.write_message('Wrote Regression Model to %s ' % fname)

    def onLoadModel(self, event=None):
        dlg = wx.FileDialog(self, message="Load Regression Model",
                            defaultDir=os.getcwd(),
                            wildcard=MODEL_WILDCARDS, style=wx.FD_OPEN)

        fname = None
        if dlg.ShowModal() == wx.ID_OK:
            fname = dlg.GetPath()
        dlg.Destroy()
        if fname is None:
            return
        self.save_modelfile = os.path.split(fname)[1]
        with open(fname, 'rb') as fh:
            text = fh.read().decode('utf-8')

        reg_model = pickle.loads(base64.b64decode(bytes(text, 'utf-8')))
        self.controller.symtable.reg_model = reg_model
        self.write_message('Read Regression Model from %s ' % fname)
        self.wids['fit_group'].Enable()


    def onLoadCSV(self, event=None):
        dlg = wx.FileDialog(self, message="Load CSV Data File",
                            defaultDir=os.getcwd(),
                            wildcard=CSV_WILDCARDS, style=wx.FD_OPEN)

        fname = None
        if dlg.ShowModal() == wx.ID_OK:
            fname = dlg.GetPath()
        dlg.Destroy()
        if fname is None:
            return

        self.save_csvfile = os.path.split(fname)[1]
        varname = fix_varname(self.wids['varname'].GetValue())
        csvgroup = read_csv(fname)
        script = []
        grid_data = []
        for sname, yval in zip(csvgroup.col_01, csvgroup.col_02):
            if sname.startswith('#'):
                continue
            if sname in self.controller.file_groups:
                gname = self.controller.file_groups[sname]
                script.append('%s.%s = %f' % (gname, varname, yval))
                grid_data.append([sname, yval, 0])

        self.larch_eval('\n'.join(script))
        self.wids['table'].table.data = grid_data
        self.wids['table'].table.View.Refresh()
        self.write_message('Read CSV File %s ' % fname)

    def onSaveCSV(self, event=None):
        wildcard = 'CSV file (*.csv)|*.csv|All files (*.*)|*.*'
        fname = FileSave(self, message='Save CSV Data File',
                         wildcard=wildcard,
                         default_file=self.save_csvfile)
        if fname is None:
            return
        self.save_csvfile = os.path.split(fname)[1]
        buff = []
        for  row in self.wids['table'].table.data:
            buff.append("%s, %s, %s" % (row[0], gformat(row[1]), gformat(row[2])))
        buff.append('')
        with open(fname, 'w') as fh:
            fh.write('\n'.join(buff))
        self.write_message('Wrote CSV File %s ' % fname)

    def onPlotModel(self, event=None, model=None):
        opts = self.read_form()
        if model is None:
            return

        ppanel = self.controller.get_display(win=1).panel
        viewlims = ppanel.get_viewlimits()
        plotcmd = ppanel.plot

        d_ave = model.spectra.mean(axis=0)
        d_std = model.spectra.std(axis=0)
        ymin, ymax = (d_ave-d_std).min(), (d_ave+d_std).max()
        if self.method == 'lasso':
            active_coefs = (model.coefs[model.active])
            active_coefs = active_coefs/max(abs(active_coefs))
            ymin = min(active_coefs.min(), ymin)
            ymax = max(active_coefs.max(), ymax)

        else:
            ymin = min(model.coefs.min(), ymin)
            ymax = max(model.coefs.max(), ymax)

        ymin = ymin - 0.02*(ymax-ymin)
        ymax = ymax + 0.02*(ymax-ymin)


        title = '%s Regression results' % (self.method.upper())

        ppanel.plot(model.x, d_ave, win=1, title=title,
                    label='mean spectra', xlabel='Energy (eV)',
                    ylabel=opts['fitspace'], show_legend=True,
                    ymin=ymin, ymax=ymax)
        ppanel.axes.fill_between(model.x, d_ave-d_std, d_ave+d_std,
                                 color='#1f77b433')
        if self.method == 'lasso':
            ppanel.axes.bar(model.x[model.active], active_coefs,
                            1.0, color='#9f9f9f88',
                            label='coefficients')
        else:
            _, ncomps = model.coefs.shape
            for i in range(ncomps):
                ppanel.oplot(model.x, model.coefs[:, i], label='coef %d' % (i+1))

        ppanel.canvas.draw()

        ngoups = len(model.groupnames)
        indices = np.arange(len(model.groupnames))
        diff = model.ydat - model.ypred
        sx = np.argsort(model.ydat)

        ppanel = self.controller.get_display(win=2).panel

        ppanel.plot(model.ydat[sx], indices, xlabel='valence',
                    label='experimental', linewidth=0, marker='o',
                    markersize=8, win=2, new=True, title=title)

        ppanel.oplot(model.ypred[sx], indices, label='predicted',
                    labelfontsize=7, markersize=6, marker='o',
                    linewidth=0, show_legend=True, new=False)

        ppanel.axes.barh(indices, diff[sx], 0.5, color='#9f9f9f88')
        ppanel.axes.set_yticks(indices)
        ppanel.axes.set_yticklabels([model.groupnames[o] for o in sx])
        ppanel.conf.auto_margins = False
        ppanel.conf.set_margins(left=0.35, right=0.05, bottom=0.15, top=0.1)
        ppanel.canvas.draw()


    def onCopyParam(self, name=None, evt=None):
        print("on Copy Param")
        conf = self.get_config()
