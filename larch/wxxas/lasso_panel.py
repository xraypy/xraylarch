#!/usr/bin/env python
"""
Linear Combination panel
"""
import os
import time
import wx
import wx.grid as wxgrid
import numpy as np

from functools import partial
from collections import OrderedDict

from larch.math import index_of

from larch.wxlib import (BitmapButton, TextCtrl, FloatCtrl, get_icon,
                         SimpleText, pack, Button, HLine, Choice, Check,
                         CEN, RCEN, LCEN, Font)

from .taskpanel import TaskPanel

# plot options:
norm   = 'Normalized \u03bC(E)'
dmude  = 'd\u03bC(E)/dE'
chik   = '\u03c7(k)'
noplot = '<no plot>'
noname = '<none>'

FitSpace_Choices = [norm, dmude, chik]
Plot_Choices = ['Mean Spectrum + Active Energies', 'Spectra Stack',
                'Predicted External Varliable']

defaults = dict(fitspace=norm, fit_intercept=True, alpha=0.01,
                varname='valence',
                xmin=-5.e5, xmax=5.e5)


class ExtVarDataTable(wxgrid.GridTableBase):
    def __init__(self):
        wxgrid.GridTableBase.__init__(self)
        self.colLabels = [' File /Group Name      ',   'External Variable']
        self.dataTypes = [wxgrid.GRID_VALUE_STRING,
                          wxgrid.GRID_VALUE_FLOAT+ ':12,4']

        self.data = []
        for i in range(500):
            self.data.append([' ', 0.00])

    def GetNumberRows(self):
        return len(self.data) + 1

    def GetNumberCols(self):
        return len(self.data[0])

    def IsEmptyCell(self, row, col):
        try:
            return not self.data[row][col]
        except IndexError:
            return True

    def GetValue(self, row, col):
        try:
            return self.data[row][col]
        except IndexError:
            return ''

    def SetValue(self, row, col, value):
        def innerSetValue(row, col, value):
            try:
                self.data[row][col] = value
            except IndexError:
                # add a new row
                self.data.append(['', 0.00] * self.GetNumberCols())
                innerSetValue(row, col, value)

                # tell the grid we've added a row
                self.GetView().ProcessTableMessage(
                    wxgrid.GridTableMessage(self,
                       wxgrid.GRIDTABLE_NOTIFY_ROWS_APPENDED, 1))

        innerSetValue(row, col, value)

    def GetColLabelValue(self, col):
        return self.colLabels[col]

    def GetTypeName(self, row, col):
        return self.dataTypes[col]

    def CanGetValueAs(self, row, col, typeName):
        return (typeName == self.dataTypes[col].split(':')[0])

    def CanSetValueAs(self, row, col, typeName):
        return self.CanGetValueAs(row, col, typeName)

class ExtVarTableGrid(wxgrid.Grid):
    def __init__(self, parent):
        wxgrid.Grid.__init__(self, parent, -1)

        self.table = ExtVarDataTable()
        self.SetTable(self.table, True)

        self.SetRowLabelSize(0)
        self.SetMargins(0,0)
        self.AutoSizeColumns(False)
        self.SetColSize(0, 375)
        self.SetColSize(1, 100)

        self.Bind(wxgrid.EVT_GRID_CELL_LEFT_DCLICK, self.OnLeftDClick)

    def OnLeftDClick(self, evt):
        if self.CanEnableCellControl():
            self.EnableCellEditControl()


class LASSOPanel(TaskPanel):
    """LASSO Panel"""
    def __init__(self, parent, controller, **kws):
        TaskPanel.__init__(self, parent, controller, configname='lasso_config',
                           title='LASSO, Linear Feature Selection', **kws)
        self.result = None

    def process(self, dgroup, **kws):
        """ handle LASSO processing"""
        if self.skip_process:
            return
        self.skip_process = True
        form = self.read_form()

    def build_display(self):
        titleopts = dict(font=Font(12), colour='#AA0000')
        panel = self.panel
        wids = self.wids
        self.skip_process = True

        wids['fitspace'] = Choice(panel, choices=FitSpace_Choices, size=(250, -1))
        wids['fitspace'].SetStringSelection(norm)
        wids['plotchoice'] = Choice(panel, choices=Plot_Choices,
                                  size=(250, -1), action=self.onPlot)

        add_text = self.add_text

        opts = dict(digits=2, increment=1.0)

        wids['xmin'] = self.add_floatspin('xmin', value=defaults['xmin'], **opts)
        wids['xmax'] = self.add_floatspin('xmax', value=defaults['xmax'], **opts)

        wids['alpha'] = self.add_floatspin('alpha', digits=5,
                                           value=defaults['alpha'],
                                           increment=0.0002, with_pin=False,
                                           min_val=0, max_val=1.0)

        wids['auto_alpha'] = Check(panel, default=False, label='auto?')

        wids['fit_intercept'] = Check(panel, default=True, label='fit intercept?')

        wids['save_csv'] = Button(panel, 'Save CSV Data', size=(200, -1),
                                    action=self.onSaveCSV)
        wids['load_csv'] = Button(panel, 'Load CSV Data', size=(200, -1),
                                    action=self.onLoadCSV)

        wids['train_model'] = Button(panel, 'Train Model With Selected Groups',
                                     size=(275, -1),  action=self.onTrainLassoModel)

        wids['fit_group'] = Button(panel, 'Predict Variable for Current Group', size=(275, -1),
                                   action=self.onPredictGroup)

        wids['save_model'] = Button(panel, 'Save Lasso Model', size=(200, -1),
                                    action=self.onSaveLassoModel)
        wids['load_model'] = Button(panel, 'Load Lasso Model', size=(200, -1),
                                    action=self.onLoadLassoModel)

        wids['copy_params'] = Button(panel, 'Copy To Selected Groups', size=(200, -1),
                                     action=partial(self.onCopyParam, 'lasso'))
        wids['fit_group'].Disable()
        wids['save_model'].Disable()


        wids['attr_name'] = wx.TextCtrl(panel, -1, 'valence', size=(150, -1))

        wids['table'] = ExtVarTableGrid(panel)
        wids['table'].SetMinSize((475, 150))

        # sview = self.wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        # sview.AppendTextColumn(' Group',    width=75)
        # sview.AppendTextColumn(' External Variable',   width=100)
        # sview.SetMinSize((275, 250))

        # wids['status'] = SimpleText(panel, ' ')
        # rfont = self.GetFont()
        # rfont.SetPointSize(rfont.GetPointSize()+1)

        add_text('Array to Use: ', newrow=True)
        panel.Add(wids['fitspace'], dcol=3)
        panel.Add(wids['load_model'])

        add_text('Plot : ', newrow=True)
        panel.Add(wids['plotchoice'], dcol=3)
        panel.Add(wids['save_model'])

        add_text('Fit Energy Range: ')
        panel.Add(wids['xmin'])
        add_text(' : ', newrow=False)
        panel.Add(wids['xmax'])

        add_text('Alpha: ')
        panel.Add(wids['alpha'])
        panel.Add(wids['auto_alpha'])
        panel.Add(wids['fit_intercept'])

        add_text('Attribute : ')
        panel.Add(wids['attr_name'], dcol=2)

        panel.Add(wids['copy_params'], dcol=2)

        panel.Add(wids['load_csv'], newrow=True, dcol=2)
        panel.Add(wids['save_csv'], newrow=False, dcol=2)

        panel.Add(wids['table'], newrow=True, dcol=5)

        panel.Add(HLine(panel, size=(550, 2)), dcol=5, newrow=True)

        panel.Add(wids['train_model'], dcol=3, newrow=True)
        panel.Add(wids['fit_group'], dcol=3)

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
        for attr in ('xmin', 'xmax', 'alpha'):
            val = opts.get(attr, None)
            if val is not None:
                wids[attr].SetValue(val)

        for attr in ('fitspace',):
            if attr in opts:
                wids[attr].SetStringSelection(opts[attr])

        self.skip_process = False

    def onTrainLassoModel(self, event=None):
        print("train")

    def onPredictGroup(self, event=None):
        print("predict")

    def onSaveLassoModel(self, event=None):
        print("save model")

    def onLoadLassoModel(self, event=None):
        print("load model")

    def onLoadCSV(self, event=None):
        print("load csv")

    def onSaveCSV(self, event=None):
        print("save csv")

    def onPlot(self, event=None):
        print("on Plot")

    def onCopyParam(self, name=None, evt=None):
        print("on Copy Param")
        conf = self.get_config()
