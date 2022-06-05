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
from copy import deepcopy
from functools import partial

from lmfit.printfuncs import gformat
from larch import Group
from larch.math import index_of
from larch.wxlib import (BitmapButton, TextCtrl, FloatCtrl, get_icon,
                         SimpleText, pack, Button, HLine, Choice, Check,
                         NumericCombo, CEN, LEFT, Font, FileSave, FileOpen,
                         DataTableGrid, Popup)
from larch.io import save_groups, read_groups, read_csv
from larch.utils.strutils import fix_varname
from larch.utils import get_cwd

from .taskpanel import TaskPanel
from .config import Linear_ArrayChoices, Regress_Choices

CSV_WILDCARDS = "CSV Files(*.csv,*.dat)|*.csv*;*.dat|All files (*.*)|*.*"
MODEL_WILDCARDS = "Regression Model Files(*.regmod,*.dat)|*.regmod*;*.dat|All files (*.*)|*.*"

Plot_Choices = ['Mean Spectrum + Active Energies',
                'Spectra Stack',
                'Predicted External Varliable']

MAX_ROWS = 1000

def make_steps(max=1, decades=8):
    steps = [1.0]
    for i in range(6):
        steps.extend([(j*10**(-(1+i))) for j in (5, 2, 1)])
    return steps

class RegressionPanel(TaskPanel):
    """Regression Panel"""
    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller, panel='regression', **kws)
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

        wids['fitspace'] = Choice(panel, choices=list(Linear_ArrayChoices.keys()),
                                  action=self.onFitSpace, size=(175, -1))
        wids['fitspace'].SetSelection(0)
        # wids['plotchoice'] = Choice(panel, choices=Plot_Choices,
        #                           size=(250, -1), action=self.onPlot)

        wids['method'] = Choice(panel, choices=Regress_Choices, size=(250, -1),
                                action=self.onRegressMethod)
        wids['method'].SetSelection(1)
        add_text = self.add_text

        opts = dict(digits=2, increment=1.0)
        defaults = self.get_defaultconfig()

        self.make_fit_xspace_widgets(elo=defaults['elo_rel'], ehi=defaults['ehi_rel'])

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
                     'Predicted Value', 'Training?']
        colsizes = [250, 100, 100, 100]
        coltypes = ['str', 'float:12,4', 'float:12,4', 'str']
        coldefs  = ['', 0.0, 0.0, '']

        wids['table'] = DataTableGrid(panel, nrows=MAX_ROWS,
                                      collabels=collabels,
                                      datatypes=coltypes,
                                      defaults=coldefs,
                                      colsizes=colsizes)

        wids['table'].SetMinSize((675, 225))

        wids['use_selected'] = Button(panel, 'Use Selected Groups',
                                      size=(150, -1),  action=self.onFillTable)

        panel.Add(SimpleText(panel, 'Feature Regression, Model Selection',
                             size=(350, -1), **self.titleopts), style=LEFT, dcol=4)

        add_text('Array to Use: ', newrow=True)
        panel.Add(wids['fitspace'], dcol=4)

        panel.Add(wids['fitspace_label'], newrow=True)
        panel.Add(self.elo_wids)
        add_text(' : ', newrow=False)
        panel.Add(self.ehi_wids, dcol=3)
        add_text('Regression Method:')
        panel.Add(wids['method'], dcol=4)
        add_text('PLS # components: ')
        panel.Add(w_ncomps)
        panel.Add(wids['auto_scale_pls'], dcol=2)
        add_text('Lasso Alpha: ')
        panel.Add(wids['alpha'])
        panel.Add(wids['auto_alpha'], dcol=2)
        panel.Add(wids['fit_intercept'])

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
        self.onRegressMethod()
        self.skip_process = False

    def onRegressMethod(self, evt=None):
        meth = self.wids['method'].GetStringSelection()
        use_lasso = meth.lower().startswith('lasso')
        self.wids['alpha'].Enable(use_lasso)
        self.wids['auto_alpha'].Enable(use_lasso)
        self.wids['fit_intercept'].Enable(use_lasso)
        self.wids['auto_scale_pls'].Enable(not use_lasso)
        self.wids['ncomps'].Enable(not use_lasso)

    def onFitSpace(self, evt=None):
        fitspace = self.wids['fitspace'].GetStringSelection()
        self.update_config(dict(fitspace=fitspace))
        arrname = Linear_ArrayChoices.get(fitspace, 'norm')
        self.update_fit_xspace(arrname)
        self.plot()


    def fill_form(self, dgroup=None, opts=None):
        conf = deepcopy(self.get_config(dgroup=dgroup, with_erange=True))
        if opts is None:
            opts = {}
        conf.update(opts)
        self.dgroup = dgroup
        self.skip_process = True
        wids = self.wids

        for attr in ('fitspace','method'):
            if attr in conf:
                wids[attr].SetStringSelection(conf[attr])

        for attr in ('elo', 'ehi', 'alpha', 'varname', 'cv_folds', 'cv_repeats'):
            val = conf.get(attr, None)
            if val is not None:
                if attr == 'alpha':
                    if val < 0:
                        val = 0.001
                        conf['auto_alpha'] = True
                    val = '%.6g' % val
                if attr in wids:
                    wids[attr].SetValue(val)

        use_lasso = conf['method'].lower().startswith('lasso')

        for attr in ('auto_alpha', 'fit_intercept','auto_scale_pls'):
            val = conf.get(attr, True)
            if attr == 'auto_scale_pls':
                val = val and not use_lasso
            else:
                val = val and use_lasso
            wids[attr].SetValue(val)
        self.onRegressMethod()

        self.skip_process = False

    def read_form(self):
        dgroup = self.controller.get_group()
        form = {'groupname': getattr(dgroup, 'groupname', 'No Group')}

        for k in ('fitspace', 'method'):
            form[k] = self.wids[k].GetStringSelection()

        for k in ('elo', 'ehi', 'alpha', 'cv_folds',
                  'cv_repeats', 'ncomps', 'varname'):
            form[k] = self.wids[k].GetValue()

        form['alpha'] = float(form['alpha'])
        if form['alpha'] < 0:
            form['alpha'] = 1.e-3

        for k in ('auto_scale_pls', 'auto_alpha',  'fit_intercept'):
            form[k] = self.wids[k].IsChecked()

        mname = form['method'].lower()
        form['use_lars'] = 'lars' in mname
        form['funcname'] = 'pls'
        if mname.startswith('lasso'):
            form['funcname'] = 'lasso'
            if form['auto_alpha']:
                form['alpha'] = None

        return form


    def onFillTable(self, event=None):
        selected_groups = self.controller.filelist.GetCheckedStrings()
        varname = fix_varname(self.wids['varname'].GetValue())
        predname = varname + '_predicted'
        grid_data = []
        for fname in self.controller.filelist.GetCheckedStrings():
            gname = self.controller.file_groups[fname]
            grp = self.controller.get_group(gname)
            grid_data.append([fname, getattr(grp, varname, 0.0),
                              getattr(grp, predname, 0.0), 'Yes'])

        self.wids['table'].table.data = grid_data
        self.wids['table'].table.View.Refresh()

    def onTrainModel(self, event=None):
        form = self.read_form()
        varname = form['varname']
        predname = varname + '_predicted'

        grid_data = self.wids['table'].table.data
        groups = []
        for fname, yval, pval, istrain in grid_data:
            gname = self.controller.file_groups[fname]
            grp = self.controller.get_group(gname)
            setattr(grp, varname, yval)
            setattr(grp, predname, pval)
            groups.append(gname)

        cmds = ['# train linear regression model',
               'training_groups = [%s]' % ', '.join(groups)]

        copts = ["varname='%s'" % varname, "xmin=%.4f" % form['elo'],
                 "xmax=%.4f" % form['ehi']]

        arrname = Linear_ArrayChoices.get(form['fitspace'], 'norm')
        copts.append("arrayname='%s'" % arrname)

        if form['method'].lower().startswith('lasso'):
            if form['auto_alpha']:
                copts.append('alpha=None')
            else:
                copts.append('alpha=%.6g' % form['alpha'])
            copts.append('use_lars=%s' % repr('lars' in form['method'].lower()))
            copts.append('fit_intercept=%s' % repr(form['fit_intercept']))
        else:
            copts.append('ncomps=%d' % form['ncomps'])
            copts.append('scale=%s' % repr(form['auto_scale_pls']))

        callargs = ', '.join(copts)

        cmds.append("reg_model = %s_train(training_groups, %s)" %
                    (form['funcname'], callargs))

        self.larch_eval('\n'.join(cmds))
        reg_model = self.larch_get('reg_model')
        reg_model.form = form
        self.use_regmodel(reg_model)

    def use_regmodel(self, reg_model):
        if reg_model is None:
            return
        opts = self.read_form()

        if hasattr(reg_model, 'form'):
            opts.update(reg_model.form)

        self.write_message('Regression Model trained: %s' % opts['method'])
        rmse_cv = reg_model.rmse_cv
        if rmse_cv is not None:
            rmse_cv = "%.4f" % rmse_cv
        stat = "RMSE_CV = %s, RMSE = %.4f" % (rmse_cv, reg_model.rmse)
        self.wids['stat1'].SetLabel(stat)
        if opts['funcname'].startswith('lasso'):
            stat = "Alpha = %.4f, %d active components"
            self.wids['stat2'].SetLabel(stat % (reg_model.alpha,
                                                len(reg_model.active)))

            if opts['auto_alpha']:
                self.wids['alpha'].add_choice(reg_model.alpha)

        else:
            self.wids['stat2'].SetLabel('- - - ')
        training_groups = reg_model.groupnames
        ntrain = len(training_groups)
        grid_data = self.wids['table'].table.data
        grid_new = []
        for i in range(ntrain): # min(ntrain, len(grid_data))):
            fname = training_groups[i]
            istrain = 'Yes' if fname in training_groups else 'No'
            grid_new.append( [fname, reg_model.ydat[i], reg_model.ypred[i], istrain])
        self.wids['table'].table.data = grid_new
        self.wids['table'].table.View.Refresh()

        if reg_model.cv_folds not in (0, None):
            self.wids['cv_folds'].SetValue(reg_model.cv_folds)
        if reg_model.cv_repeats not in (0, None):
            self.wids['cv_repeats'].SetValue(reg_model.cv_repeats)

        self.wids['save_model'].Enable()
        self.wids['fit_group'].Enable()

        wx.CallAfter(self.onPlotModel, model=reg_model)

    def onPanelExposed(self, **kws):
        # called when notebook is selected
        try:
            fname = self.controller.filelist.GetStringSelection()
            gname = self.controller.file_groups[fname]
            dgroup = self.controller.get_group(gname)
            if not hasattr(dgroup, 'norm'):
                self.xasmain.process_normalization(dgroup)
            self.fill_form(dgroup)
        except:
            pass # print(" Cannot Fill prepeak panel from group ")

        reg_model = getattr(self.larch.symtable, 'reg_model', None)
        if reg_model is not None:
            self.use_regmodel(reg_model)


    def onPredictGroups(self, event=None):
        opts = self.read_form()
        varname = opts['varname'] + '_predicted'

        reg_model = self.larch_get('reg_model')
        training_groups = reg_model.groupnames

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
                                                         opts['funcname'], gname)
            self.larch_eval(cmd)
            val = self.larch_get('%s.%s' % (gname, varname))
            if fname in gent:
                grid_data[gent[fname]][2] = val
            else:
                istrain = 'Yes' if fname in training_groups else 'No'
                grid_data.append([fname, extval, val, istrain])
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
                            defaultDir=get_cwd(),
                            defaultFile=self.save_modelfile,
                            wildcard=MODEL_WILDCARDS,
                            style=wx.FD_SAVE)
        fname = None
        if dlg.ShowModal() == wx.ID_OK:
            fname = dlg.GetPath()
        dlg.Destroy()
        if fname is None:
            return
        save_groups(fname, ['#regression model 1.0', reg_model])
        self.write_message('Wrote Regression Model to %s ' % fname)

    def onLoadModel(self, event=None):
        dlg = wx.FileDialog(self, message="Load Regression Model",
                            defaultDir=get_cwd(),
                            wildcard=MODEL_WILDCARDS, style=wx.FD_OPEN)

        fname = None
        if dlg.ShowModal() == wx.ID_OK:
            fname = dlg.GetPath()
        dlg.Destroy()
        if fname is None:
            return
        dat = read_groups(fname)
        if len(dat) != 2 or not dat[0].startswith('#regression model'):
            Popup(self, f" '{rfile}' is not a valid Regression model file",
                  "Invalid file")

        reg_model = dat[1]
        self.controller.symtable.reg_model = reg_model

        self.write_message('Read Regression Model from %s ' % fname)
        self.wids['fit_group'].Enable()

        self.use_regmodel(reg_model)

    def onLoadCSV(self, event=None):
        dlg = wx.FileDialog(self, message="Load CSV Data File",
                            defaultDir=get_cwd(),
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
        opts.update(model.form)

        ppanel = self.controller.get_display(win=1).panel
        viewlims = ppanel.get_viewlimits()
        plotcmd = ppanel.plot

        d_ave = model.spectra.mean(axis=0)
        d_std = model.spectra.std(axis=0)
        ymin, ymax = (d_ave-d_std).min(), (d_ave+d_std).max()

        if opts['funcname'].startswith('lasso'):
            active = [int(i) for i in model.active]
            active_coefs = (model.coefs[active])
            active_coefs = active_coefs/max(abs(active_coefs))
            ymin = min(active_coefs.min(), ymin)
            ymax = max(active_coefs.max(), ymax)

        else:
            ymin = min(model.coefs.min(), ymin)
            ymax = max(model.coefs.max(), ymax)

        ymin = ymin - 0.02*(ymax-ymin)
        ymax = ymax + 0.02*(ymax-ymin)


        title = '%s Regression results' % (opts['method'])

        ppanel.plot(model.x, d_ave, win=1, title=title,
                    label='mean spectra', xlabel='Energy (eV)',
                    ylabel=opts['fitspace'], show_legend=True,
                    ymin=ymin, ymax=ymax)
        ppanel.axes.fill_between(model.x, d_ave-d_std, d_ave+d_std,
                                 color='#1f77b433')
        if opts['funcname'].startswith('lasso'):
            ppanel.axes.bar(model.x[active], active_coefs,
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
                    labelxsxfontsize=7, markersize=6, marker='o',
                    linewidth=0, show_legend=True, new=False)

        ppanel.axes.barh(indices, diff[sx], 0.5, color='#9f9f9f88')
        ppanel.axes.set_yticks(indices)
        ppanel.axes.set_yticklabels([model.groupnames[o] for o in sx])
        ppanel.conf.auto_margins = False
        ppanel.conf.set_margins(left=0.35, right=0.05, bottom=0.15, top=0.1)
        ppanel.canvas.draw()


    def onCopyParam(self, name=None, evt=None):
        conf = self.get_config()
