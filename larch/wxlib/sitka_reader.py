#!/usr/bin/env python
"""
reader for extracting data from HDF5 Files with Sitka Spruce
"""
from copy import deepcopy

import numpy as np
np.seterr(all='ignore')
from pathlib import Path
from functools import partial

import wx


from wxutils import (SimpleText, FloatCtrl, FloatSpin, Button, get_color,
                     Choice, TextCtrl, pack, Popup, Check, MenuItem, CEN,
                     RIGHT, LEFT, FRAMESTYLE, flatnotebook, HLine, Font, GridPanel)
from pyshortcuts import fix_filename, fix_varname, gformat

from sitka_spruce import SitkaFrame

from larch import Group
from larch.interpreter import Interpreter
from larch.xafs.xafsutils import guess_energy_units
from larch.utils.strutils import file2groupname
from larch.io import look_for_nans, guess_filereader, is_specfile, sum_fluor_channels
from larch.utils.physical_constants import PLANCK_HC, DEG2RAD
from larch.math import safe_log

from . import FONTSIZE

CEN |=  wx.ALL
YPRE_OPS = ('', 'log(', '-log(', '-')
ARR_OPS = ('+', '-', '*', '/')

YERR_OPS = ('Constant', 'Sqrt(Y)', 'Array')
CONV_OPS  = ('Lorenztian', 'Gaussian')

DATATYPES = ('xydata', 'xas')
XAS_MODE_TYPES = ('unknown', 'transmission', 'fluorescence', 'herfd', 'calculation')

ENUNITS_TYPES = ('eV', 'keV', 'degrees', 'not energy')


MIN_NPTS = 4
MAX_NPTS = 128000


class SitkaReaderFrame(wx.Frame) :
    """Read data from HDF5/Zarr File"""
    def __init__(self, parent, filename=None, sitka=None, read_ok_cb=None):

        wx.Frame.__init__(self, parent, size=(650, 325),
                          title='Read Arrays from HDF5 / Zarr Files',
                          style=FRAMESTYLE)

        self.parent = parent
        self.filename = filename
        self.read_ok_cb = read_ok_cb
        if sitka is None:
            print("Creating SitkaFrame in Reader")
            sitka = SitkaFrame()
        self.sitka = sitka

        if filename is not None:
            sitka.onDroppedFiles([filename])
        wids = self.wids = {}
        self.subframes = {}

        panel = self.panel = GridPanel(self, ncols=5, nrows=10, pad=2, itemstyle=LEFT)


        def padd_text(text, dcol=1, size=(140, -1), newrow=True):
            panel.Add(SimpleText(panel, text, size=size, style=LEFT),
                      dcol=dcol, newrow=newrow)

        wids['data_type'] = Choice(panel, choices=DATATYPES, size=(150, -1),
                                   action=self.onXSelect)

        wids['xas_mode'] = Choice(panel, choices=XAS_MODE_TYPES, size=(150, -1))
        wids['en_units'] = Choice(panel, choices=ENUNITS_TYPES, size=(150, -1),
                                  action=self.onEnUnitsSelect)
        wids['monod_val'] = FloatCtrl(panel, value=3.1355316, precision=7, size=(75, -1))
        wids['monod_val'].Disable()

        yarr_labels = self.yarr_labels = ['1.0', '']
        xarr_labels = self.xarr_labels = ['<index>']

        wids['xarr']  = Choice(panel, choices=xarr_labels, action=self.onXSelect, size=(150, -1))
        wids['yarr1'] = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        wids['yarr2'] = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        wids['dyarr'] = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        wids['dyarr'].Disable()

        wids['ypop'] = Choice(panel, choices=YPRE_OPS, action=self.onUpdate, size=(100, -1))
        wids['yop']  = Choice(panel, choices=ARR_OPS, action=self.onUpdate, size=(100, -1))
        wids['yop'].SetStringSelection('/')

        wids['dyop'] = Choice(panel, choices=YERR_OPS, action=self.onYerrChoice, size=(100, -1))
        wids['dyop'].SetStringSelection('Constant')

        wids['dyval'] = FloatCtrl(panel, value=1, precision=4, size=(75, -1))


        wids['filename'] = wx.TextCtrl(panel, value='from_sitka', size=(200, -1))
        wids['groupname'] = wx.TextCtrl(panel, value='sitka1', size=(200, -1))


        wids['update_arrays'] = Button(panel, "Update Array Choices", size=(200, -1),
                                       action=self.onArrayChoices)
        wids['ok'] = Button(panel, "OK", size=(150, -1), action=self.onOK)

        opts = {'size': (600, -1), 'dcol': 6}

        padd_text(' Use Sitka to Browse Files and Save Arrays ', newrow=False,  **opts)
        padd_text(' Then Use "Update Arrays" to update the array choices here ', **opts)
        padd_text(' NOT WORKING YET!!', **opts)

        panel.Add(wids['update_arrays'], dcol=3, newrow=True)

        padd_text('Data Type: ')
        panel.Add(wids['data_type'], dcol=2)
        padd_text('XAS Mode: ', newrow=False)
        panel.Add(wids['xas_mode'], dcol=2)
        padd_text('X array: ')
        panel.Add(wids['xarr'], dcol=2)
        padd_text('X units: ', newrow=False)
        panel.Add(wids['en_units'], dcol=2)
        panel.Add((5, 5), dcol=3, newrow=True)
        padd_text('Mono dspacing (A)', newrow=False)
        panel.Add(wids['monod_val'], style=wx.ALIGN_RIGHT)
        padd_text('Y array: ')
        panel.Add(wids['ypop'])
        panel.Add(wids['yarr1'])
        panel.Add(wids['yop'])
        panel.Add(wids['yarr2'])

        padd_text('Y uncertainty: ')
        panel.Add(wids['dyop'])
        panel.Add(wids['dyarr'])
        padd_text(' value: ', newrow=False)
        panel.Add(wids['dyval'])

        panel.Add((5,5), newrow=True)
        padd_text('Display Name = ')
        panel.Add(wids['filename'], dcol=3)
        padd_text('Group Name = ', newrow=True)
        panel.Add(wids['groupname'], dcol=3)

        panel.Add(wids['ok'], dcol=2, newrow=True)

        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, 0, LEFT|wx.GROW, 4)
        pack(self, sizer)
        self.Show()
        self.Raise()

    def onOK(self, event=None):
        """ build arrays according to selection """
        print("on OK")

    def onXSelect(self, event=None):
        print('on x select')

        xname = self.wids['xarr'].GetStringSelection()
        xdat = self.sitka.data.arrays[xname]
        print(xname, len(xdat))

        arrays = []
        for name, arr in self.sitka.data.arrays.items():
            if len(arr.shape) == 1 and len(arr) == len(xdat):
                arrays.append(name)

        ychoices = arrays[:]
        ychoices.extend(['1.0', '0.0'])
        self.wids['yarr1'].SetChoices(ychoices)
        self.wids['yarr2'].SetChoices(ychoices)
        self.wids['dyarr'].SetChoices(ychoices)

        if 'ener' in xname.lower():
            self.wids['data_type'].SetSelection(1)
        else:
            self.wids['data_type'].SetSelection(0)

        self.wids['monod_val'].Disable()
        if self.wids['data_type'].GetStringSelection().strip().lower() == 'xydata':
            self.wids['en_units'].SetSelection(4)
        else:
            eguess = guess_energy_units(xdat)
            if eguess.startswith('keV'):
                self.wids['en_units'].SetSelection(1)
            elif eguess.startswith('deg'):
                self.wids['en_units'].SetSelection(2)
                self.wids['monod_val'].Enable()
            else:
                self.wids['en_units'].SetSelection(0)


    def onUpdate(self, event=None):
        print('on update')

    def onYerrChoice(self, event=None):
        print('on Yerr Choice')

    def onArrayChoices(self, event=None):
        print('on Array Choices')
        arrays_1d = []
        for name, arr in self.sitka.data.arrays.items():
            if (len(arr.shape) == 1 and
                len(arr) > MIN_NPTS and
                len(arr) < MAX_NPTS ):
                arrays_1d.append(name)

        print(arrays_1d)
        xchoices = ['<index>']
        xchoices.extend(arrays_1d)
        self.wids['xarr'].SetChoices(xchoices)

        ychoices = arrays_1d[:]
        ychoices.extend(['1.0', '0.0'])
        self.wids['yarr1'].SetChoices(ychoices)
        self.wids['yarr2'].SetChoices(ychoices)
        self.wids['dyarr'].SetChoices(ychoices)

    def onEnUnitsSelect(self, evt=None):
        print("on En Units")

#         self.array_labels = [l.lower() for l in group.array_labels]
#
#         has_energy = False
#         en_units = 'unknown'
#         for arrlab in self.array_labels[:5]:
#             arrlab  = arrlab.lower()
#             if arrlab == 'e' or arrlab.startswith('en') or 'energ' in arrlab:
#                 en_units = 'eV'
#                 has_energy = True
#
#         if self.workgroup.datatype in (None, 'unknown'):
#             self.workgroup.datatype = 'xas' if has_energy else 'xydata'
#
#
#         datatype = config.pop('datatype', None)
#         if datatype is not None:
#             self.workgroup.datatype = datatype
#
#         en_units = 'eV' if self.workgroup.datatype == 'xas' else 'unknown'
#
#         self.read_ok_cb = read_ok_cb
#
#         ncol, npts = self.workgroup.data.shape
#         self.config = dict(xarr=None, yarr1=None, yarr2=None, yop='/',
#                            ypop='', monod=3.1355316, en_units=en_units,
#                            yerr_op='constant', yerr_val=1, yerr_arr=None,
#                            yrpop='', yrop='/', yref1='', yref2='',
#                            has_yref=False, dtc_config={}, multicol_config={},
#                            datattype=self.workgroup.datatype, npts=npts)
#         if config is not None:
#             self.config.update(config)
#
#         if self.config['yarr2'] is None and 'i0' in self.array_labels:
#             self.config['yarr2'] = 'i0'
#
#         if self.config['yarr1'] is None:
#             if 'itrans' in self.array_labels:
#                 self.config['yarr1'] = 'itrans'
#             elif 'i1' in self.array_labels:
#                 self.config['yarr1'] = 'i1'
#
#         if self.config['yref1'] is None:
#             if 'iref' in self.array_labels:
#                 self.config['yref1'] = 'iref'
#             elif 'irefer' in self.array_labels:
#                 self.config['yref1'] = 'irefer'
#             elif 'i2' in self.array_labels:
#                 self.config['yref1'] = 'i2'
#
#         if self.config['yref2'] is None and 'i1' in self.array_labels:
#             self.config['yref2'] = 'i1'
#
#         # use_trans = self.config.get('xasmode', 'unknown') == 'transmission' or 'log' in self.config['ypop']
#
#         message = f"Data Columns (blue) for {group.filename}"
#         wx.Frame.__init__(self, None, -1,
#                           f'Build Arrays from Data Columns for {group.filename}',
#                           style=FRAMESTYLE)
#
#         x0, y0 = parent.GetPosition()
#         self.SetPosition((x0+60, y0+60))
#
#         self.SetFont(Font(FONTSIZE))
#         panel = wx.Panel(self)
#         self.SetMinSize((725, 700))
#
#         def subtitle(s, fontsize=12, colorname='title_blue'):
#             return SimpleText(panel, s, font=Font(fontsize),  colour=colorname, style=LEFT)
#
#         # title row
#         title = subtitle(message, colorname='title_blue')
#
#         yarr_labels = self.yarr_labels = self.array_labels + ['1.0', '']
#         xarr_labels = self.xarr_labels = self.array_labels + ['_index']
#
#         self.xarr   = Choice(panel, choices=xarr_labels, action=self.onXSelect, size=(150, -1))
#         self.yarr1  = Choice(panel, choices= self.array_labels, action=self.onUpdate, size=(150, -1))
#         self.yarr2  = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
#         self.yerr_arr = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
#         self.yerr_arr.Disable()
#
#         self.datatype = Choice(panel, choices=DATATYPES, action=self.onUpdate, size=(150, -1))
#         self.datatype.SetStringSelection(self.workgroup.datatype)
#
#         self.xasmode = Choice(panel, choices=XAS_MODE_TYPES, action=self.onUpdate, size=(150, -1))
#         wmode = getattr(self.workgroup, 'xasmode', 'unknown')
#         self.xasmode.SetStringSelection(wmode)
#         self.xasmode.Enable(self.workgroup.datatype=='xas')
#
#         self.en_units = Choice(panel, choices=ENUNITS_TYPES,
#                                action=self.onEnUnitsSelect, size=(150, -1))
#
#         self.ypop = Choice(panel, choices=YPRE_OPS, action=self.onUpdate, size=(100, -1))
#         self.yop =  Choice(panel, choices=ARR_OPS, action=self.onUpdate, size=(100, -1))
#         self.yerr_op = Choice(panel, choices=YERR_OPS, action=self.onYerrChoice, size=(100, -1))
#         self.yerr_op.SetSelection(0)
#
#         self.yerr_val = FloatCtrl(panel, value=1, precision=4, size=(75, -1))
#         self.monod_val  = FloatCtrl(panel, value=3.1355316, precision=7, size=(75, -1))
#
#         xlab = SimpleText(panel, ' X array = ')
#         ylab = SimpleText(panel, ' Y array = ')
#         units_lab = SimpleText(panel, 'Units of X array: ')
#         yerr_lab = SimpleText(panel, ' Y uncertainty = ')
#         dtype_lab = SimpleText(panel, ' Data Type: ')
#         monod_lab = SimpleText(panel, ' Mono D spacing (Ang): ')
#         yerrval_lab = SimpleText(panel, ' Value:')
#
#         # yref
#         self.has_yref = Check(panel, label='data file includes energy reference data',
#                               default=self.config['has_yref'],
#                               action=self.onYrefCheck)
#         refylab = SimpleText(panel, ' Refer array = ')
#         self.yref1 = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
#         self.yref2 = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
#         self.yrpop = Choice(panel, choices=YPRE_OPS, action=self.onUpdate, size=(100, -1))
#         self.yrop =  Choice(panel, choices=ARR_OPS, action=self.onUpdate, size=(100, -1))
#
#         self.ysuf = SimpleText(panel, '')
#         # print("COL FILE READER set ypop to ", use_trans, self.config['ypop'])
#         self.ypop.SetStringSelection(self.config['ypop'])
#         self.yop.SetStringSelection(self.config['yop'])
#         self.yrpop.SetStringSelection(self.config['yrpop'])
#         self.yrop.SetStringSelection(self.config['yrop'])
#         self.monod_val.SetValue(self.config['monod'])
#         self.monod_val.SetAction(self.onUpdate)
#         self.monod_val.Enable(self.config['en_units'].startswith('deg'))
#         self.en_units.SetStringSelection(self.config['en_units'])
#         self.yerr_op.SetStringSelection(self.config['yerr_op'])
#         self.yerr_val.SetValue(self.config['yerr_val'])
#         if '(' in self.config['ypop']:
#             self.ysuf.SetLabel(')')
#
#
#         ixsel, iysel = 0, 1
#         iy2sel = iyesel = iyr1sel = iyr2sel = len(yarr_labels)-1
#         if self.config['xarr'] in xarr_labels:
#             ixsel = xarr_labels.index(self.config['xarr'])
#         if self.config['yarr1'] in self.array_labels:
#             iysel = self.array_labels.index(self.config['yarr1'])
#         if self.config['yarr2'] in yarr_labels:
#             iy2sel = yarr_labels.index(self.config['yarr2'])
#         if self.config['yerr_arr'] in yarr_labels:
#             iyesel = yarr_labels.index(self.config['yerr_arr'])
#         if self.config['yref1'] in self.array_labels:
#             iyr1sel = self.array_labels.index(self.config['yref1'])
#         if self.config['yref2'] in self.array_labels:
#             iyr2sel = self.array_labels.index(self.config['yref2'])
#
#         self.xarr.SetSelection(ixsel)
#         self.yarr1.SetSelection(iysel)
#         self.yarr2.SetSelection(iy2sel)
#         self.yerr_arr.SetSelection(iyesel)
#         self.yref1.SetSelection(iyr1sel)
#         self.yref2.SetSelection(iyr2sel)
#
#         self.wid_filename = wx.TextCtrl(panel, value=fix_filename(group.filename),
#                                          size=(250, -1))
#         self.wid_groupname = wx.TextCtrl(panel, value=group.groupname,
#                                          size=(150, -1))
#         if not edit_groupname:
#             self.wid_groupname.Disable()
#         self.wid_reffilename = wx.TextCtrl(panel, value=fix_filename(group.filename + '_ref'),
#                                          size=(250, -1))
#         self.wid_refgroupname = wx.TextCtrl(panel, value=group.groupname + '_ref',
#                                          size=(150, -1))
#
#         # self.onTransCheck(is_trans=use_trans)
#         self.onYrefCheck(has_yref=self.config['has_yref'])
#
#
#         bpanel = wx.Panel(panel)
#         bsizer = wx.BoxSizer(wx.HORIZONTAL)
#         _ok    = Button(bpanel, 'OK', action=self.onOK)
#         _cancel = Button(bpanel, 'Cancel', action=self.onCancel)
#         _edit   = Button(bpanel, 'Edit Array Names', action=self.onEditNames)
#         self.multi_sel = Button(bpanel, 'Select Multilple Columns',  action=self.onMultiColumn)
#         self.multi_clear = Button(bpanel, 'Clear Multiple Columns',  action=self.onClearMultiColumn)
#         self.dtc_button  = Button(bpanel, 'Sum and Correct Fluoresence Data', action=self.onDTC)
#
#         self.multi_clear.Disable()
#         _edit.SetToolTip('Change the current Column Names')
#         self.multi_sel.SetToolTip('Select Multiple Columns to import as separate groups')
#         self.multi_clear.SetToolTip('Clear Multiple Column Selection')
#
#         self.dtc_button.SetToolTip('Select channels and do deadtime-corrections for multi-element fluorescence data')
#
#         bsizer.Add(_ok)
#         bsizer.Add(_cancel)
#         bsizer.Add(_edit)
#         bsizer.Add(self.dtc_button)
#         bsizer.Add(self.multi_sel)
#         bsizer.Add(self.multi_clear)
#
#         _ok.SetDefault()
#         pack(bpanel, bsizer)
#
#
#         sizer = wx.GridBagSizer(2, 2)
#         sizer.Add(title,     (0, 0), (1, 7), LEFT, 5)
#
#         ir = 1
#         sizer.Add(dtype_lab,       (ir, 0), (1, 1), LEFT, 0)
#         sizer.Add(self.datatype,   (ir, 1), (1, 1), LEFT, 0)
#         sizer.Add(SimpleText(panel, 'XAS Mode:'), (ir, 2), (1, 1), LEFT, 0)
#         sizer.Add(self.xasmode,     (ir, 3), (1, 2), LEFT, 0)
#
#         ir += 1
#         sizer.Add(xlab,           (ir, 0), (1, 1), LEFT, 0)
#         sizer.Add(self.xarr,      (ir, 1), (1, 1), LEFT, 0)
#         sizer.Add(units_lab,      (ir, 2), (1, 1), LEFT, 0)
#         sizer.Add(self.en_units,  (ir, 3), (1, 1), LEFT, 0)
#         ir += 1
#         sizer.Add(monod_lab,      (ir, 2), (1, 1), LEFT, 0)
#         sizer.Add(self.monod_val, (ir, 3), (1, 1), LEFT, 0)
#
#         ir += 1
#         sizer.Add(ylab,       (ir, 0), (1, 1), LEFT, 0)
#         sizer.Add(self.ypop,  (ir, 1), (1, 1), LEFT, 0)
#         sizer.Add(self.yarr1, (ir, 2), (1, 1), LEFT, 0)
#         sizer.Add(self.yop,   (ir, 3), (1, 1), RIGHT, 0)
#         sizer.Add(self.yarr2, (ir, 4), (1, 1), LEFT, 0)
#         sizer.Add(self.ysuf,  (ir, 5), (1, 1), LEFT, 0)
#
#
#         ir += 1
#         sizer.Add(yerr_lab,      (ir, 0), (1, 1), LEFT, 0)
#         sizer.Add(self.yerr_op,  (ir, 1), (1, 1), LEFT, 0)
#         sizer.Add(self.yerr_arr, (ir, 2), (1, 1), LEFT, 0)
#         sizer.Add(yerrval_lab,   (ir, 3), (1, 1), RIGHT, 0)
#         sizer.Add(self.yerr_val, (ir, 4), (1, 2), LEFT, 0)
#
#         ir += 1
#         sizer.Add(SimpleText(panel, ' Display Name:'), (ir, 0), (1, 1), LEFT, 0)
#         sizer.Add(self.wid_filename,                  (ir, 1), (1, 2), LEFT, 0)
#         ir += 1
#         sizer.Add(SimpleText(panel, ' Group Name:'),   (ir, 0), (1, 1), LEFT, 0)
#         sizer.Add(self.wid_groupname,                 (ir, 1), (1, 2), LEFT, 0)
#
#         ir += 1
#         sizer.Add(subtitle(' Reference [\u03BC_ref(E)] Array: '),
#                   (ir, 0), (1, 2), LEFT, 0)
#         sizer.Add(self.has_yref,   (ir, 2), (1, 3), LEFT, 0)
#
#         ir += 1
#         sizer.Add(refylab,    (ir, 0), (1, 1), LEFT, 0)
#         sizer.Add(self.yrpop, (ir, 1), (1, 1), LEFT, 0)
#         sizer.Add(self.yref1, (ir, 2), (1, 1), LEFT, 0)
#         sizer.Add(self.yrop,  (ir, 3), (1, 1), RIGHT, 0)
#         sizer.Add(self.yref2, (ir, 4), (1, 2), LEFT, 0)
#
#
#         ir += 1
#         sizer.Add(SimpleText(panel, ' Reference Name:'), (ir, 0), (1, 1), LEFT, 0)
#         sizer.Add(self.wid_reffilename,               (ir, 1), (1, 2), LEFT, 0)
#         sizer.Add(SimpleText(panel, ' Group Name:'),   (ir, 3), (1, 1), RIGHT, 0)
#         sizer.Add(self.wid_refgroupname,              (ir, 4), (1, 2), LEFT, 0)
#
#         ir +=1
#         sizer.Add(bpanel,     (ir, 0), (1, 5), LEFT, 3)
#
#         pack(panel, sizer)
#
#         self.nb = flatnotebook(self, {}, style=FNB_STYLE)
#         self.plotpanel = PlotPanel(self, messenger=self.set_message)
#         from .plotter import get_plot_config
#         self.plotpanel.set_config(**get_plot_config())
#         self.plotpanel.SetMinSize((250, 250))
#         textpanel = wx.Panel(self)
#         ftext = wx.TextCtrl(textpanel, style=wx.TE_MULTILINE|wx.TE_READONLY,
#                                size=(370, 275))
#
#         ftext.SetValue(group.text)
#         ftext.SetFont(Font(FONTSIZE))
#
#         textsizer = wx.BoxSizer(wx.VERTICAL)
#         textsizer.Add(ftext, 1, LEFT|wx.GROW, 1)
#         pack(textpanel, textsizer)
#
#         self.nb.AddPage(textpanel, ' Text of Data File ', True)
#         self.nb.AddPage(self.plotpanel, ' Plot of Selected Arrays ', True)
#
#         mainsizer = wx.BoxSizer(wx.VERTICAL)
#         mainsizer.Add(panel, 0, wx.GROW|wx.ALL, 2)
#         mainsizer.Add(self.nb, 1, LEFT|wx.GROW,   2)
#         pack(self, mainsizer)
#
#         self.statusbar = self.CreateStatusBar(2, 0)
#         self.statusbar.SetStatusWidths([-1, -1])
#         statusbar_fields = [group.filename, ""]
#         for i in range(len(statusbar_fields)):
#             self.statusbar.SetStatusText(statusbar_fields[i], i)
#
#         self.set_energy_units()
#         dtc_conf = self.config.get('dtc_config', {})
#         if len(dtc_conf) > 0:
#             self.onDTC_OK(dtc_conf, update=False)
#

#         self.onUpdate()
#
#     def onDTC(self, event=None):
#         self.show_subframe('dtc_conf', DeadtimeCorrectionFrame,
#                            config=self.config['dtc_config'],
#                            group=self.workgroup,
#                            on_ok=self.onDTC_OK)
#
#     def onDTC_OK(self, config, update=True, **kws):
#
#         label, sum = sum_fluor_channels(self.workgroup, config['roi'],
#                                         icr=config['icr'],
#                                         ocr=config['ocr'],
#                                         ltime=config['ltime'],
#                                         add_data=False)
#         if sum is None:
#             return
#         self.set_message(f"Added array '{label}' with summed and corrected fluorecence data")
#         self.workgroup.array_labels.append(label)
#         self.set_array_labels(self.workgroup.array_labels)
#         npts = len(sum)
#         new = np.append(self.workgroup.raw.data, sum.reshape(1, npts), axis=0)
#         self.workgroup.raw.data = new[()]
#         self.workgroup.data = new[()]
#         self.yarr1.SetStringSelection(label)
#         self.config['dtc_config'] = config
#         if update:
#             self.onUpdate()
#
#     def onClearMultiColumn(self, event=None):
#         self.config['multicol_config'] = {}
#         self.set_message(f" cleared reading of multiple columns")
#         self.multi_clear.Disable()
#         self.yarr1.Enable()
#         self.ypop.Enable()
#         self.yop.Enable()
#         self.onUpdate()
#
#
#     def onMultiColumn(self, event=None):
#         self.show_subframe('multicol', MultiColumnFrame,
#                            config=self.config['multicol_config'],
#                            group=self.workgroup,
#                            on_ok=self.onMultiColumn_OK)
#
#
#     def onMultiColumn_OK(self, config, update=True, **kws):
#         chans = config.get('channels', [])
#         if len(chans) == 0:
#             self.config['multicol_config'] = {}
#         else:
#             self.config['multicol_config'] = config
#             self.yarr1.SetSelection(chans[0])
#             self.yarr2.SetSelection(config['i0'])
#             self.ypop.SetStringSelection('')
#             self.yarr1.Disable()
#             self.ypop.Disable()
#             self.yop.Disable()
#             y2 = self.yarr2.GetStringSelection()
#             msg = f"  Will import {len(config['channels'])} Y arrays, divided by '{y2}'"
#             self.set_message(msg)
#             self.multi_clear.Enable()
#         if update:
#             self.onUpdate()
#
#     def read_column_file(self, path):
#         """read column file, generally as initial read"""
#         path = Path(path).absolute()
#         filename = path.name
#         path = path.as_posix()
#         reader, text = guess_filereader(path, return_text=True)
#         if reader == 'read_specfile':
#             if not is_specfile(path, require_multiple_scans=True):
#                 reader = 'read_ascii'
#
#         if reader in ('read_xdi', 'read_gsexdi'):
#             # first check for Nans and Infs
#             nan_result = look_for_nans(path)
#             if 'read error' in nan_result.message:
#                 title = "Cannot read %s" % path
#                 message = "Error reading %s\n%s" %(path, nan_result.message)
#                 r = Popup(self.parent, message, title)
#                 return None
#             if 'no data' in nan_result.message:
#                 title = "No data in %s" % path
#                 message = "No data found in file %s" % path
#                 r = Popup(self.parent, message, title)
#                 return None
#
#             if ('has nans' in nan_result.message or
#                 'has infs' in nan_result.message):
#                 reader = 'read_ascii'
#
#         tmpname = '_tmpfile_'
#         read_cmd = "%s = %s('%s')" % (tmpname, reader, path)
#         self.reader = reader
#
#         _larch = self._larch
#         if (not isinstance(_larch, Interpreter) and
#             hasattr(_larch, '_larch')):
#             _larch = _larch._larch
#         try:
#             _larch.eval(read_cmd, add_history=True)
#         except:
#             pass
#         if len(_larch.error) > 0 and reader in ('read_xdi', 'read_gsexdi'):
#             read_cmd = "%s = %s('%s')" % (tmpname, 'read_ascii', path)
#             try:
#                 _larch.eval(read_cmd, add_history=True)
#             except:
#                 pass
#             if len(_larch.error) == 0:
#                 self.reader = 'read_ascii'
#
#         if len(_larch.error) > 0:
#             msg = ["Error trying to read '%s':" % path, ""]
#             for err in _larch.error:
#                 exc_name, errmsg = err.get_error()
#                 msg.append(errmsg)
#
#             title = "Cannot read %s" % path
#             r = Popup(self.parent, "\n".join(msg), title)
#             return None
#         group = deepcopy(_larch.symtable.get_symbol(tmpname))
#         _larch.symtable.del_symbol(tmpname)
#
#         group.text = text
#         group.path = path
#         group.filename = filename
#         group.groupname = file2groupname(filename,
#                                          symtable=self._larch.symtable)
#         return group
#
#     def show_subframe(self, name, frameclass, **opts):
#         shown = False
#         if name in self.subframes:
#             try:
#                 self.subframes[name].Raise()
#                 shown = True
#             except:
#                 pass
#         if not shown:
#             self.subframes[name] = frameclass(self, **opts)
#             self.subframes[name].Show()
#             self.subframes[name].Raise()
#
#
#     def onEditNames(self, evt=None):
#         self.show_subframe('editcol', EditColumnFrame,
#                            group=self.workgroup,
#                            on_ok=self.set_array_labels)
#
#     def set_array_labels(self, arr_labels):
#         self.workgroup.array_labels = arr_labels
#         yarr_labels = self.yarr_labels = arr_labels + ['1.0', '']
#         xarr_labels = self.xarr_labels = arr_labels + ['_index']
#         def update(wid, choices):
#             curstr = wid.GetStringSelection()
#             curind = wid.GetSelection()
#             wid.SetChoices(choices)
#             if curstr in choices:
#                 wid.SetStringSelection(curstr)
#             else:
#                 wid.SetSelection(curind)
#         update(self.xarr,  xarr_labels)
#         update(self.yarr1, yarr_labels)
#         update(self.yarr2, yarr_labels)
#         update(self.yerr_arr, yarr_labels)
#         self.onUpdate()
#
#     def onOK(self, event=None):
#         """ build arrays according to selection """
#         self.read_form()
#         cout = create_arrays(self.workgroup, **self.config)
#         self.config.update(cout)
#         conf = self.config
#         if self.ypop.Enabled:  #not using multicolumn mode
#             conf['multicol_config'] = {'channels': [], 'i0': conf['iy2']}
#
#         self.expressions = conf['expressions']
#         filename = conf['filename']
#         groupname = conf['groupname']
#         datatype  = conf['datatype']
#         xasmode = conf['xasmode']
#
#         conf['array_labels'] = self.workgroup.array_labels
#
#         # generate script to pass back to calling program:
#         labstr = ', '.join(self.array_labels)
#         buff = [f"{{group}} = {self.reader}('{{path}}', labels='{labstr}')",
#                 "{group}.path = '{path}'",
#                 "{group}.is_frozen = False",
#                 "{group}.energy_ref = '{group}'"]
#
#         dtc_conf = conf.get('dtc_config', {})
#         if len(dtc_conf) > 0:
#             sumcmd = "sum_fluor_channels({{group}}, {roi}, icr={icr}, ocr={ocr}, ltime={ltime})"
#             buff.append(sumcmd.format(**dtc_conf))
#
#         buff.append("{group}.datatype = '%s'" % (datatype))
#
#         for attr in ('plot_xlabel', 'plot_ylabel'):
#             val = getattr(self.workgroup, attr)
#             buff.append("{group}.%s = '%s'" % (attr, val))
#
#         xexpr = self.expressions['xplot']
#         en_units = conf['en_units']
#         if en_units.startswith('deg'):
#             monod = conf['monod']
#             buff.append(f"monod = {monod:.9f}")
#             buff.append(f"{{group}}.xplot = PLANCK_HC/(2*monod*sin(DEG2RAD*({xexpr:s})))")
#         elif en_units.startswith('keV'):
#             buff.append(f"{{group}}.xplot = 1000.0*{xexpr:s}")
#         else:
#             buff.append(f"{{group}}.xplot = {xexpr:s}")
#
#         for aname in ('yplot', 'yerr'):
#             expr = self.expressions[aname]
#             buff.append(f"{{group}}.{aname} = {expr}")
#
#
#         dtype = getattr(self.workgroup, 'datatype', 'xytype')
#         if dtype == 'xas':
#             if self.reader == 'read_gsescan':
#                 buff.append("{group}.xplot = {group}.x")
#             buff.append("{group}.energy = {group}.xplot[:]")
#             buff.append("{group}.mu = {group}.yplot[:]")
#             buff.append("{group}.xasmode = '%s'" % (xasmode))
#             buff.append("sort_xafs({group}, overwrite=True, fix_repeats=True)")
#         elif dtype == 'xydata':
#             buff.append("{group}.xdat = {group}.xplot[:]")
#             buff.append("{group}.ydat = {group}.yplot[:]")
#             buff.append("{group}.scale = (ptp({group}.yplot)+1.e-15)")
#             buff.append("{group}.xshift = 0.0")
#
#         array_desc = dict(xplot=self.workgroup.plot_xlabel,
#                           yplot=self.workgroup.plot_ylabel,
#                           yerr=self.expressions['yerr'])
#
#         reffile = refgroup = None
#         if conf['has_yref']:
#             reffile = conf['reffile']
#             refgroup = conf['refgroup']
#             refexpr = self.expressions['yref']
#             array_desc['yref'] = getattr(self.workgroup, 'yrlabel', 'reference')
#
#             buff.append("# reference group")
#             buff.append("{refgroup} = deepcopy({group})")
#             buff.append(f"{{refgroup}}.yplot = {{refgroup}}.mu = {refexpr}")
#             buff.append(f"{{refgroup}}.plot_ylabel = '{self.workgroup.yrlabel}'")
#             buff.append("{refgroup}.energy_ref = {group}.energy_ref = '{refgroup}'")
#             buff.append("# end reference group")
#
#         script = "\n".join(buff)
#         conf['array_desc'] = array_desc
#
#         if self.read_ok_cb is not None:
#             self.read_ok_cb(script, self.path, conf)
#
#         for f in self.subframes.values():
#             try:
#                 f.Destroy()
#             except:
#                 pass
#         self.Destroy()
#
#     def onCancel(self, event=None):
#         self.workgroup.import_ok = False
#         for f in self.subframes.values():
#             try:
#                 f.Destroy()
#             except:
#                 pass
#         self.Destroy()
#
#     def onYerrChoice(self, evt=None):
#         yerr_choice = evt.GetString()
#         self.yerr_arr.Disable()
#         self.yerr_val.Disable()
#         if 'const' in yerr_choice.lower():
#             self.yerr_val.Enable()
#         elif 'array' in yerr_choice.lower():
#             self.yerr_arr.Enable()
#         # self.onUpdate()
#
#     def onXASMode(self, evt=None):
#         xasmode = self.xasmode.GetStringSelction()
#         if xasmode == 'transmission':
#             self.ypop.SetStringSelection('-log(')
#         else:
#             self.ypop.SetStringSelection('')
#         try:
#             self.onUpdate()
#         except:
#             pass
#
#
#     def onTransCheck(self, evt=None, is_trans=False):
#         if evt is not None:
#             is_trans = evt.IsChecked()
#         if is_trans:
#             self.ypop.SetStringSelection('-log(')
#         else:
#             self.ypop.SetStringSelection('')
#         try:
#             self.onUpdate()
#         except:
#             pass
#
#     def onYrefCheck(self, evt=None, has_yref=False):
#         if evt is not None:
#             has_yref = evt.IsChecked()
#         self.yref1.Enable(has_yref)
#         self.yref2.Enable(has_yref)
#         self.yrpop.Enable(has_yref)
#         self.yrop.Enable(has_yref)
#         self.wid_reffilename.Enable(has_yref)
#         self.wid_refgroupname.Enable(has_yref)
#
#
#     def onXSelect(self, evt=None):
#         ix  = self.xarr.GetSelection()
#         xname = self.xarr.GetStringSelection()
#
#         workgroup = self.workgroup
#         ncol, npts = self.workgroup.data.shape
#         if xname.startswith('_index') or ix >= ncol:
#             workgroup.xplot = 1.0*np.arange(npts)
#         else:
#             workgroup.xplot = 1.0*self.workgroup.data[ix, :]
#         self.onUpdate()
#
#         self.monod_val.Disable()
#         if self.datatype.GetStringSelection().strip().lower() == 'xydata':
#             self.en_units.SetSelection(4)
#         else:
#             eguess = guess_energy_units(workgroup.xplot)
#             if eguess.startswith('keV'):
#                 self.en_units.SetSelection(1)
#             elif eguess.startswith('deg'):
#                 self.en_units.SetSelection(2)
#                 self.monod_val.Enable()
#             else:
#                 self.en_units.SetSelection(0)
#
#     def onEnUnitsSelect(self, evt=None):
#         self.monod_val.Enable(self.en_units.GetStringSelection().startswith('deg'))
#         self.onUpdate()
#
#     def set_energy_units(self):
#         ix  = self.xarr.GetSelection()
#         xname = self.xarr.GetStringSelection()
#         workgroup = self.workgroup
#         try:
#             ncol, npts = workgroup.data.shape
#         except (AttributeError,  ValueError):
#             return
#
#         if xname.startswith('_index') or ix >= ncol:
#             workgroup.xplot = 1.0*np.arange(npts)
#         else:
#             workgroup.xplot = 1.0*self.workgroup.data[ix, :]
#         if self.datatype.GetStringSelection().strip().lower() != 'xydata':
#             eguess =  guess_energy_units(workgroup.xplot)
#             if eguess.startswith('eV'):
#                 self.en_units.SetStringSelection('eV')
#             elif eguess.startswith('keV'):
#                 self.en_units.SetStringSelection('keV')
#
#     def read_form(self, **kws):
#         """return form configuration"""
#         datatype = self.datatype.GetStringSelection().strip().lower()
#         if self.workgroup.datatype == 'xydata' and datatype == 'xas':
#             self.workgroup.datatype = 'xas'
#             eguess = guess_energy_units(self.workgroup.xplot)
#             if eguess.startswith('keV'):
#                 self.en_units.SetSelection(1)
#             elif eguess.startswith('deg'):
#                 self.en_units.SetSelection(2)
#                 self.monod_val.Enable()
#             else:
#                 self.en_units.SetSelection(0)
#         if datatype == 'xydata':
#             self.en_units.SetStringSelection('not energy')
#
#         ypop = self.ypop.GetStringSelection().strip()
#
#         if 'log' in ypop:
#             self.xasmode.SetStringSelection('transmission')
#
#
#         conf = {'datatype': datatype,
#                 'xasmode': self.xasmode.GetStringSelection(),
#                 'ix':  self.xarr.GetSelection(),
#                 'xarr': self.xarr.GetStringSelection(),
#                 'en_units': self.en_units.GetStringSelection(),
#                 'monod': float(self.monod_val.GetValue()),
#                 'yarr1': self.yarr1.GetStringSelection().strip(),
#                 'yarr2': self.yarr2.GetStringSelection().strip(),
#                 'iy1': self.yarr1.GetSelection(),
#                 'iy2': self.yarr2.GetSelection(),
#                 'yop': self.yop.GetStringSelection().strip(),
#                 'ypop': ypop,
#                 'iyerr': self.yerr_arr.GetSelection(),
#                 'yerr_arr': self.yerr_arr.GetStringSelection(),
#                 'yerr_op': self.yerr_op.GetStringSelection().lower(),
#                 'yerr_val': self.yerr_val.GetValue(),
#                 'has_yref': self.has_yref.IsChecked(),
#                 'yref1': self.yref1.GetStringSelection().strip(),
#                 'yref2': self.yref2.GetStringSelection().strip(),
#                 'iry1': self.yref1.GetSelection(),
#                 'iry2': self.yref2.GetSelection(),
#                 'yrpop': self.yrpop.GetStringSelection().strip(),
#                 'yrop': self.yop.GetStringSelection().strip(),
#                 'filename': self.wid_filename.GetValue(),
#                 'groupname': fix_varname(self.wid_groupname.GetValue()),
#                 'reffile': self.wid_reffilename.GetValue(),
#                 'refgroup': fix_varname(self.wid_refgroupname.GetValue()),
#                 }
#         self.config.update(conf)
#         return conf
#
#     def onUpdate(self, evt=None, **kws):
#         """column selections changed calc xplot and yplot"""
#         workgroup = self.workgroup
#         try:
#             ncol, npts = self.workgroup.data.shape
#         except:
#             return
#
#         conf = self.read_form()
#         cout = create_arrays(workgroup, **conf)
#         self.expressions = cout.pop('expressions')
#         conf.update(cout)
#
#         self.xasmode.Enable(conf['datatype']=='xas')
#
#         if energy_may_need_rebinning(workgroup):
#             self.set_message("Warning: XAS data may need to be rebinned!")
#
#         fname = Path(workgroup.filename).name
#         popts = dict(marker='o', title=fname,
#                      xlabel=workgroup.plot_xlabel,
#                      ylabel=workgroup.plot_ylabel,
#                      label=workgroup.plot_ylabel)
#
#         self.plotpanel.plot(workgroup.xplot, workgroup.yplot, **popts)
#         if conf['has_yref']:
#             yrlabel = getattr(workgroup, 'plot_yrlabel', 'reference')
#             self.plotpanel.oplot(workgroup.xplot, workgroup.yref,
#                                  y2label=yrlabel,
#                                  label=yrlabel, zorder=-10, side='right')
#
#         for i in range(self.nb.GetPageCount()):
#             if 'plot' in self.nb.GetPageText(i).lower():
#                 self.nb.SetSelection(i)
#
#     def set_message(self, msg, panel=1):
#         self.statusbar.SetStatusText(msg, panel)
#
#
# def create_arrays(dgroup, datatype='xas', ix=0, xarr='energy', en_units='eV',
#                   monod=3.1355316, yarr1=None, yarr2=None, iy1=2, iy2=1, yop='/',
#                   ypop='', iyerr=5, yerr_arr=None, yerr_op='constant', yerr_val=1.0,
#                   has_yref=False, yref1=None, yref2=None, iry1=3, iry2=2,
#                   yrpop='', yrop='/', **kws):
#     """
#     build arrays and values for datagroup based on configuration as from ColumnFile
#     """
#     ncol, npts = dgroup.data.shape
#     exprs = dict(xplot=None, yplot=None, yerr=None, yref=None)
#
#     if not hasattr(dgroup, 'index'):
#         dgroup.index = 1.0*np.arange(npts)
#
#     if xarr.startswith('_index') or ix >= ncol:
#         dgroup.xplot = 1.0*np.arange(npts)
#         xarr = '_index'
#         exprs['xplot'] = 'arange({npts})'
#     else:
#         dgroup.xplot = 1.0*dgroup.data[ix, :]
#         exprs['xplot'] = '{group}.data[{ix}, : ]'
#
#     xlabel = xarr
#     monod = float(monod)
#     if en_units.startswith('deg'):
#         dgroup.xplot = PLANCK_HC/(2*monod*np.sin(DEG2RAD*dgroup.xplot))
#         xlabel = xarr + ' (eV)'
#     elif en_units.startswith('keV'):
#         dgroup.xplot *= 1000.0
#         xlabel = xarr + ' (eV)'
#
#     def pre_op(opstr, arr):
#         if opstr == '-':
#             return '', opstr, -arr
#         suf = ''
#         if opstr in ('-log(', 'log('):
#             suf = ')'
#             arr = safe_log(arr)
#             if opstr.startswith('-'): arr = -arr
#             arr[np.where(np.isnan(arr))] = 0
#         return suf, opstr, arr
#
#     if yarr1 is None:
#         yarr1 = dgroup.array_labels[iy1]
#
#     if yarr2 is None:
#         yarr2 = dgroup.array_labels[iy2]
#
#     ylabel = yarr1
#     if len(yarr2) == 0:
#         yarr2 = '1.0'
#     else:
#         ylabel = f"{ylabel}{yop}{yarr2}"
#
#     if yarr1 == '0.0':
#         ydarr1 = np.zeros(npts)*1.0
#         yexpr1 = f'np.zeros(npts)'
#     elif len(yarr1) == 0 or yarr1 == '1.0' or iy1 >= ncol:
#         ydarr1 = np.ones(npts)*1.0
#         yexpr1 = f'np.ones({npts})'
#     else:
#         ydarr1 = dgroup.data[iy1, :]
#         yexpr1 = '{group}.data[{iy1}, : ]'
#
#     dgroup.yplot = ydarr1
#     exprs['yplot'] = yexpr1
#
#     if yarr2 == '0.0':
#         ydarr2 = np.zeros(npts)*1.0
#         yexpr2 = '0.0'
#     elif len(yarr2) == 0 or yarr2 == '1.0' or iy2 >= ncol:
#         ydarr2 = np.ones(npts)*1.0
#         yexpr2 = '1.0'
#     else:
#         ydarr2 = dgroup.data[iy2, :]
#         yexpr2 = '{group}.data[{iy2}, : ]'
#
#     if yop in ('+', '-', '*', '/'):
#         exprs['yplot'] = f"{yexpr1}{yop}{yexpr2}"
#         if yop == '+':
#             dgroup.yplot = ydarr1 + ydarr2
#         elif yop == '-':
#             dgroup.yplot = ydarr1 - ydarr2
#         elif yop == '*':
#             dgroup.yplot = ydarr1 * ydarr2
#         elif yop == '/':
#             dgroup.yplot = ydarr1 / ydarr2
#
#     ysuf, ypop, dgroup.yplot = pre_op(ypop, dgroup.yplot)
#     ypopx = ypop.replace('log', 'safe_log')
#     exprs['yplot'] = f"{ypopx}{exprs['yplot']}{ysuf}"
#     ylabel = f"{ypop}{ylabel}{ysuf}"
#
#     # error
#     exprs['yerr'] = '1'
#     if yerr_op.startswith('const'):
#         yderr = yerr_val
#         exprs['yerr'] = f"{yerr_val}"
#     elif yerr_op.startswith('array'):
#         yderr = dgroup.data[iyerr, :]
#         exprs['yerr'] = '{group}.data[{iyerr}, :]'
#     elif yerr_op.startswith('sqrt'):
#         yderr = np.sqrt(dgroup.yplot)
#         exprs['yerr'] = 'sqrt({group}.yplot)'
#
#     # reference
#     yrlabel = None
#     if has_yref:
#         yrlabel = yref1
#         if len(yref2) == 0:
#             yref2 = '1.0'
#         else:
#             yrlabel = f"{yrlabel}{yrop}{yref2}"
#
#         if yref1 == '0.0':
#             ydrarr1 = np.zeros(npts)*1.0
#             yrexpr1 = 'zeros({npts})'
#         elif len(yref1) == 0 or yref1 == '1.0' or iry1 >= ncol:
#             ydrarr1 = np.ones(npts)*1.0
#             yrexpr1 = 'ones({npts})'
#         else:
#             ydrarr1 = dgroup.data[iry1, :]
#             yrexpr1 = '{group}.data[{iry1}, : ]'
#
#         dgroup.yref = ydrarr1
#         exprs['yref'] = yrexpr1
#
#         if yref2 == '0.0':
#             ydrarr2 = np.zeros(npts)*1.0
#             ydrexpr2 = '0.0'
#         elif len(yref2) == 0 or yref2 == '1.0' or iry2 >= ncol:
#             ydrarr2 = np.ones(npts)*1.0
#             yrexpr2 = '1.0'
#         else:
#             ydrarr2 = dgroup.data[iry2, :]
#             yrexpr2 = '{group}.data[{iry2}, : ]'
#
#         if yrop in ('+', '-', '*', '/'):
#             exprs['yref'] = f'{yrexpr1} {yop} {yrexpr2}'
#             if yrop == '+':
#                 dgroup.yref = ydrarr1 + ydrarr2
#             elif yrop == '-':
#                 dgroup.yref = ydrarr1 - ydrarr2
#             elif yrop == '*':
#                 dgroup.yref = ydrarr1 * ydarr2
#             elif yrop == '/':
#                 dgroup.yref = ydrarr1 / ydrarr2
#
#         yrsuf, yprop, dgroup.yref = pre_op(yrpop, dgroup.yref)
#         yrpopx = yrpop.replace('log', 'safe_log')
#         exprs['yref'] = f"{yrpopx}{exprs['yref']}{yrsuf}"
#         yrlabel = f'{yrpop} {yrlabel} {yrsuf}'
#         dgroup.yrlabel = yrlabel
#
#
#     try:
#         npts = min(len(dgroup.xplot), len(dgroup.yplot))
#     except AttributeError:
#         return
#     except ValueError:
#         return
#
#     en = dgroup.xplot
#     dgroup.datatype    = datatype
#     dgroup.npts        = npts
#     dgroup.plot_xlabel = xlabel
#     dgroup.plot_ylabel = ylabel
#     dgroup.xplot       = np.array(dgroup.xplot[:npts])
#     dgroup.yplot       = np.array(dgroup.yplot[:npts])
#     dgroup.ydat        = dgroup.yplot
#     dgroup.yerr        = yderr
#     if isinstance(yderr, np.ndarray):
#         dgroup.yerr    = np.array(yderr[:npts])
#     if yrlabel is not None:
#         dgroup.plot_yrlabel = yrlabel
#
#     if dgroup.datatype == 'xas':
#         dgroup.energy = dgroup.xplot
#         dgroup.mu     = dgroup.yplot
#
#     return dict(xarr=xarr, ypop=ypop, yop=yop, yarr1=yarr1, yarr2=yarr2,
#                 monod=monod, en_units=en_units, yerr_op=yerr_op,
#                 yerr_val=yerr_val, yerr_arr=yerr_arr, yrpop=yrpop, yrop=yrop,
#                 yref1=yref1, yref2=yref2, has_yref=has_yref,
#                 expressions=exprs)
#
# def energy_may_need_rebinning(workgroup):
#     "test if energy may need rebinning"
#     if getattr(workgroup, 'datatype', '?') != 'xas':
#         return False
#     en = getattr(workgroup, 'xplot', [-8.0e12])
#     if len(en) < 2:
#         return False
#     if not isinstance(en, np.ndarray):
#         en = np.array(en)
#     if len(en) > 2000 or any(np.diff(en))< 0:
#         return True
#     if (len(en) > 200 and (max(en) - min(en)) > 350 and
#         np.diff(en[:-100]).mean() < 1.0):
#         return True
