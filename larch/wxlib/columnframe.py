#!/usr/bin/env python
"""

"""
import os
import re
from copy import deepcopy

import numpy as np
np.seterr(all='ignore')

from functools import partial

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb
from wxmplot import PlotPanel

from wxutils import (SimpleText, FloatCtrl, GUIColors, Button, Choice,
                     TextCtrl, pack, Popup, Check, MenuItem, CEN, RIGHT, LEFT,
                     FRAMESTYLE, HLine, Font)

import larch
from larch import Group
from larch.xafs.xafsutils import guess_energy_units
from larch.utils.strutils import fix_varname, fix_filename, file2groupname
from larch.io import look_for_nans,  guess_filereader, is_specfile, sum_fluor_channels
from larch.utils.physical_constants import PLANCK_HC, DEG2RAD

from . import FONTSIZE

CEN |=  wx.ALL
FNB_STYLE = fnb.FNB_NO_X_BUTTON|fnb.FNB_SMART_TABS
FNB_STYLE |= fnb.FNB_NO_NAV_BUTTONS|fnb.FNB_NODRAG

YPRE_OPS = ('', 'log(', '-log(', '-')
ARR_OPS = ('+', '-', '*', '/')

YERR_OPS = ('Constant', 'Sqrt(Y)', 'Array')
CONV_OPS  = ('Lorenztian', 'Gaussian')

DATATYPES = ('raw', 'xas')
ENUNITS_TYPES = ('eV', 'keV', 'degrees', 'not energy')


MULTICHANNEL_TITLE = """
  Build Arrays for MultiChannel Fluorescence Data:
  To allow for many dead-time-correction mehtods, Spectra for each Channe are built as:
        ROI_Corrected = ROI * ICR /(OCR * LTIME)

  Select the Number of Fluorescence Channels, the Step (usually 1) between columns for
  ROI 1, 2, ..., NChans.  Set Bad Channels as a list of Channel numbers (start at 1).

  Select columns for ROI (raw counts) and correction factors ICR, OCR, and LTIME for Channel 1.
"""
ROI_STEP_TOOLTIP =  """number of columns between ROI columns -- typically 1 if the columns are like
   ROI_Ch1 ROI_Ch2 ROI_Ch3 ... ICR_Ch1 ICR_Ch2 ICR_Ch3 ... OCR_Ch1 OCR_Ch2 OCR_Ch3 ...

but set to 3 if the columns are arranged as
   ROI_Ch1 ICR_Ch1 OCR_Ch1 ROI_Ch2 ICR_Ch2 OCR_Ch2 ROI_Ch3 ICR_Ch3 OCR_Ch3 ...
"""

class MultiChannelFrame(wx.Frame):
    """Manage MultiChannel Fluorescence Data"""
    def __init__(self, parent, group, config=None, on_ok=None):
        self.parent = parent
        self.group = group
        self.config = {'bad_chans': [], 'plot_chan': 1, 'nchans': 4, 'step': 1,
                       'roi': '1.0', 'icr': '1.0', 'ocr': '1.0',
                       'ltime': '1.0', 'i0': '1.0'}
                       # 'out_choice': 'summed spectrum',
        if config is not None:
            self.config.update(config)
        self.arrays = {}
        self.on_ok = on_ok
        wx.Frame.__init__(self, None, -1, 'MultiChannel Fluorescence Data',
                          style=wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.SetFont(Font(10))
        sizer = wx.GridBagSizer(2, 2)
        panel = scrolled.ScrolledPanel(self)

        self.SetMinSize((650, 425))

        self.yarr_labels = [s for s in self.parent.yarr_labels]

        wids = self.wids = {}

        multi_title = wx.StaticText(panel, label=MULTICHANNEL_TITLE, size=(500, 110))

        # wids['out_choice'] = wx.RadioBox(panel, -1, '',   wx.DefaultPosition, wx.DefaultSize,
        # ['summed spectrum', 'per-channel spectra', 'both sum and per-channel'],
        #                                  3, wx.RA_SPECIFY_COLS)
        # wids['out_choice'].SetStringSelection(self.config['out_choice'])
        # wids['out_choice'].Bind(wx.EVT_RADIOBOX, self.read_form)
        for s in ('roi', 'icr', 'ocr', 'ltime'):
            wids[s] = Choice(panel, choices=self.yarr_labels, action=self.read_form, size=(150, -1))
            sel = self.config.get(s, '1.0')
            if sel == '1.0':
                wids[s].SetStringSelection(sel)
            else:
                wids[s].SetSelection(sel[0])
            wids[f'{s}_txt'] = SimpleText(panel, label='<list of column labels>', size=(275, -1))

        wids['i0'] = Choice(panel, choices=self.yarr_labels, action=self.read_form, size=(150, -1))
        wids['i0'].SetToolTip("All Channels will be divided by the I0 array")

        wids['i0'].SetStringSelection(self.parent.yarr2.GetStringSelection())
        wids['roi'].SetStringSelection(self.parent.yarr1.GetStringSelection())

        wids['nchans']  = FloatCtrl(panel, value=self.config.get('nchans', 4),
                                    precision=0, maxval=2000, minval=1, size=(50, -1),
                                    action=self.read_form)
        wids['bad_chans'] = TextCtrl(panel, value='', size=(175, -1), action=self.read_form)
        if len(self.config.get('bad_chans', [])) > 0:
               wids['bad_chans'].SetValue(', '.join(['%d' % c for c in bad_chans]))
        wids['bad_chans'].SetToolTip("List Channels to skip, separated by commas or spaces")
        wids['step']    = FloatCtrl(panel, value=self.config.get('step', 1), precision=0,
                                    maxval=2000, minval=1, size=(50, -1), action=self.read_form)
        wids['step'].SetToolTip(ROI_STEP_TOOLTIP)

        wids['plot_chan'] = FloatCtrl(panel, value=self.config.get('plot_chan', 1),
                                      precision=0, maxval=2000, minval=1, size=(50, -1))

        wids['save_btn'] = Button(panel, 'Use this Sum of Channels',  action=self.onOK)
        wids['plot_sum'] = Button(panel, 'Plot Sum of Channels',   action=self.onPlotSum)
        wids['plot_all'] = Button(panel, 'Plot Each Channel', action=self.onPlotEach)
        wids['plot_this'] = Button(panel, 'Plot ROI and DeadTime Correction For Channel', action=self.onPlotThis)

        def tlabel(t):
            return SimpleText(panel, label=t)

        sizer.Add(multi_title,       (0, 0), (2, 5), LEFT, 3)
        ir = 2
        sizer.Add(HLine(panel, size=(550, 3)), (ir, 0), (1, 5), LEFT, 3)

        ir += 1
        sizer.Add(tlabel(' Number of Channels:'),   (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['nchans'],                   (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(tlabel(' Step between Channels:'), (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(wids['step'],                     (ir, 3), (1, 1), LEFT, 3)

        ir += 1
        sizer.Add(tlabel(' Bad Channels :'),   (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['bad_chans'],           (ir, 1), (1, 2), LEFT, 3)

        ir += 1
        sizer.Add(HLine(panel, size=(550, 3)), (ir, 0), (1, 5), LEFT, 3)

        ir += 1
        sizer.Add(tlabel(' Signal '),  (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(tlabel(' Array for Chan #1 '),  (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(tlabel(' Array Labels used for all Channels '),  (ir, 2), (1, 3), LEFT, 3)

        for s in ('roi', 'icr', 'ocr', 'ltime'):
            ir += 1
            sizer.Add(tlabel(f' {s.upper()} #1 : '), (ir, 0), (1, 1), LEFT, 3)
            sizer.Add(wids[s],               (ir, 1), (1, 1), LEFT, 3)
            sizer.Add(wids[f'{s}_txt'],      (ir, 2), (1, 3), LEFT, 3)

        ir += 1
        sizer.Add(tlabel(' I0 : '),  (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['i0'],        (ir, 1), (1, 1), LEFT, 3)

        ir += 1
        sizer.Add(HLine(panel, size=(550, 3)), (ir, 0), (1, 5), LEFT, 3)

        ir += 1
        sizer.Add(wids['plot_sum'],  (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['plot_all'],  (ir, 1), (1, 3), LEFT, 3)

        ir += 1
        sizer.Add(wids['plot_this'], (ir, 0), (1, 2), LEFT, 3)
        sizer.Add(tlabel(' Channel:'),  (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(wids['plot_chan'],     (ir, 3), (1, 1), LEFT, 3)
        ir += 1
        sizer.Add(HLine(panel, size=(550, 2)), (ir, 0), (1, 5), LEFT, 3)
        ir += 1
        sizer.Add(wids['save_btn'],   (ir, 0), (1, 3), LEFT, 3)
        # sizer.Add(wids['out_choice'], (ir, 1), (1, 3), LEFT, 3)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def make_sum(self):
        return sum_fluor_channels(self.group, self.config['roi'],
                                  icr=self.config['icr'],
                                  ocr=self.config['ocr'],
                                  ltime=self.config['ltime'],
                                  add_data=False)

    def get_en_i0(self):
        en = self.group.xdat
        i0 = 1.0
        if self.config['i0'] != '1.0':
            i0 = self.group.data[self.config['i0'], :]
        return en, i0

    def read_arrays(self, pchan):
        def get_array(name, pchan, default=1.0):
            out = default
            if self.config[name] != '1.0':
                ix = self.config[name][pchan-1]
                if ix > 0:
                    out = self.group.data[ix, :]
            return out
        roi = get_array('roi', pchan, default=None)
        icr = get_array('icr', pchan)
        ocr = get_array('ocr', pchan)
        ltime = get_array('ltime', pchan)
        return roi, icr*ocr/ltime

    def onOK(self, event=None):
        self.read_form()
        label, sum = self.make_sum()
        npts = len(sum)
        self.group.array_labels.append(label)
        new = np.append(self.group.raw.data, sum.reshape(1, npts), axis=0)
        self.group.raw.data = new
        if callable(self.on_ok):
            self.on_ok(label, self.config)
        self.Destroy()

    def onPlotSum(self, event=None):
        self.read_form()
        en, i0 = self.get_en_i0()
        label, sum = self.make_sum()
        popts = dict(marker=None, markersize=0, linewidth=2.5,
                     show_legend=True, ylabel=label, label=label,
                     xlabel='Energy (eV)')
        self.parent.plotpanel.plot(en, sum/i0, new=True, **popts)

    def onPlotEach(self, event=None):
        self.read_form()
        new = True
        en, i0 = self.get_en_i0()
        popts = dict(marker=None, markersize=0, linewidth=2.5,
                     show_legend=True,  xlabel='Energy (eV)',
                     ylabel=f'Corrected Channels')

        nused = 0
        for pchan in range(1, self.config['nchans']+1):
            roi, dtc = self.read_arrays(pchan)
            if roi is not None:
                popts['label'] = f'Chan{pchan} Corrected'
                if new:
                    self.parent.plotpanel.plot(en, roi*dtc/i0, new=True, **popts)
                    new = False
                else:
                    self.parent.plotpanel.oplot(en, roi*dtc/i0, **popts)

    def onPlotThis(self, event=None):
        self.read_form()
        en, i0 = self.get_en_i0()
        pchan = self.config['plot_chan']
        roi, dtc = self.read_arrays(pchan)
        if roi is None:
            return
        ylabel = self.wids['roi'].GetStringSelection()
        popts = dict(marker=None, markersize=0, linewidth=2.5, show_legend=True,
                     ylabel=f'Chan{pchan}', xlabel='Energy (eV)',
                     label=f'Chan{pchan} Raw')

        self.parent.plotpanel.plot(en, roi/i0, new=True, **popts)
        popts['label'] = f'Chan{pchan} Corrected'
        self.parent.plotpanel.oplot(en, roi*dtc/i0, **popts)

    def read_form(self, event=None, value=None, **kws):
        try:
            wids = self.wids
            nchans = int(wids['nchans'].GetValue())
            step = int(wids['step'].GetValue())
            badchans = wids['bad_chans'].GetValue().replace(',', ' ').strip()
        except:
            return

        bad_channels = []
        if len(badchans) > 0:
            try:
                bad_channels = [int(s) for s in badchans.split()]
                wids['bad_chans'].SetBackgroundColour('#FFFFFF')
            except:
                bad_channels = []
                wids['bad_chans'].SetBackgroundColour('#F0B03080')

        pchan = int(wids['plot_chan'].GetValue())
        if pchan <= nchans:
            wids['plot_chan'].SetBackgroundColour('#FFFFFF')
            self.config['plot_chan'] = pchan
        else:
            wids['plot_chan'].SetBackgroundColour('#F0B03080')
            self.config['plot_chan'] = 1

        # self.config['out_choice'] = wids['out_choice'].GetStringSelection()
        self.config['bad_chans'] = bad_channels
        self.config['nchans'] = nchans
        self.config['step'] = step
        self.config['i0'] = wids['i0'].GetSelection()
        if wids['i0'].GetStringSelection() in ('1.0', ''):
            self.config['i0'] = '1.0'

        for s in ('roi', 'icr', 'ocr', 'ltime'):
            lab = wids[s].GetStringSelection()
            ilab = wids[s].GetSelection()
            if lab in ('1.0', ''):
                wids[f"{s}_txt"].SetLabel(lab)
                wids[f"{s}_txt"].SetToolTip(lab)
                self.config[s] = '1.0'
            else:
                chans = [ilab + i*step for i in range(nchans)]
                labs = []
                for i in range(nchans):
                    if (i+1) in bad_channels:
                        chans[i] = -1
                    else:
                        labs.append(self.group.array_labels[chans[i]])
                wids[f"{s}_txt"].SetLabel(', '.join(labs))
                self.config[s] = chans

class EditColumnFrame(wx.Frame) :
    """Edit Column Labels for a larch grouop"""
    def __init__(self, parent, group, on_ok=None):
        self.parent = parent
        self.group = group
        self.on_ok = on_ok
        wx.Frame.__init__(self, None, -1, 'Edit Array Names',
                          style=wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.SetFont(Font(10))
        sizer = wx.GridBagSizer(2, 2)
        panel = scrolled.ScrolledPanel(self)

        self.SetMinSize((675, 450))

        self.wids = {}
        ir = 0
        sizer.Add(Button(panel, 'Apply Changes', size=(200, -1),
                         action=self.onOK),
                  (0, 1), (1, 2), LEFT, 3)
        sizer.Add(Button(panel, 'Use Column Number', size=(200, -1),
                         action=self.onColNumber),
                  (0, 3), (1, 2), LEFT, 3)
        sizer.Add(HLine(panel, size=(550, 2)),
                  (1, 1), (1, 5), LEFT, 3)

        cind = SimpleText(panel, label='Column')
        cold = SimpleText(panel, label='Current Name')
        cnew = SimpleText(panel, label='Enter New Name')
        cret = SimpleText(panel, label='  Result   ', size=(150, -1))
        cinfo = SimpleText(panel, label='   Data Range')
        cplot = SimpleText(panel, label='   Plot')

        ir = 2
        sizer.Add(cind,  (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(cold,  (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(cnew,  (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(cret,  (ir, 3), (1, 1), LEFT, 3)
        sizer.Add(cinfo, (ir, 4), (1, 1), LEFT, 3)
        sizer.Add(cplot, (ir, 5), (1, 1), LEFT, 3)

        for i, name in enumerate(group.array_labels):
            ir += 1
            cind = SimpleText(panel, label='  %i ' % (i+1))
            cold = SimpleText(panel, label=' %s ' % name)
            cret = SimpleText(panel, label=fix_varname(name), size=(150, -1))
            cnew = wx.TextCtrl(panel, value=name, size=(150, -1),
                               style=wx.TE_PROCESS_ENTER)

            cnew.Bind(wx.EVT_TEXT_ENTER, partial(self.update, index=i))
            cnew.Bind(wx.EVT_KILL_FOCUS, partial(self.update, index=i))

            arr = group.data[i,:]
            info_str = " [ %8g : %8g ] " % (arr.min(), arr.max())
            cinfo = SimpleText(panel, label=info_str)
            cplot = Button(panel, 'Plot', action=partial(self.onPlot, index=i))


            self.wids["%d" % i] = cnew
            self.wids["ret_%d" % i] = cret

            sizer.Add(cind,  (ir, 0), (1, 1), LEFT, 3)
            sizer.Add(cold,  (ir, 1), (1, 1), LEFT, 3)
            sizer.Add(cnew,  (ir, 2), (1, 1), LEFT, 3)
            sizer.Add(cret,  (ir, 3), (1, 1), LEFT, 3)
            sizer.Add(cinfo, (ir, 4), (1, 1), LEFT, 3)
            sizer.Add(cplot, (ir, 5), (1, 1), LEFT, 3)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def onPlot(self, event=None, index=None):
        if index is not None:
            x = self.parent.workgroup.index
            y = self.parent.workgroup.data[index, :]
            label = self.wids["ret_%i" % index].GetLabel()
            popts = dict(marker='o', markersize=4, linewidth=1.5,
                         ylabel=label, xlabel='data point', label=label)
            self.parent.plotpanel.plot(x, y, **popts)

    def onColNumber(self, evt=None, index=-1):
        for name, wid in self.wids.items():
            val = name
            if name.startswith('ret_'):
                val = name[4:]
                setter = wid.SetLabel
            else:
                setter = wid.SetValue
            setter("col%d" % (int(val) +1))

    def update(self, evt=None, index=-1):
        newval = fix_varname(self.wids["%d" % index].GetValue())
        self.wids["ret_%i" % index].SetLabel(newval)

    def update_char(self, evt=None, index=-1):
        if evt.GetKeyCode() == wx.WXK_RETURN:
            self.update(evt=evt, index=index)
        # evt.Skip()

    def onOK(self, evt=None):
        group = self.group
        array_labels = []
        for i in range(len(self.group.array_labels)):
            newname = self.wids["ret_%i" % i].GetLabel()
            array_labels.append(newname)

        if callable(self.on_ok):
            self.on_ok(array_labels)
        self.Destroy()

class ColumnDataFileFrame(wx.Frame) :
    """Column Data File, select columns"""
    def __init__(self, parent, filename=None, groupname=None,
                 last_array_sel=None, read_ok_cb=None, extra_sums=None,
                 edit_groupname=True, _larch=None):
        self.parent = parent
        self._larch = _larch
        self.path = filename
        if extra_sums is None:
            extra_sums = {}
        self.extra_sums = extra_sums

        group = self.initgroup = self.read_column_file(self.path)

        self.subframes = {}
        self.workgroup  = Group(raw=group)
        for attr in ('path', 'filename', 'groupname', 'datatype',
                     'array_labels', 'data'):
            setattr(self.workgroup, attr, getattr(group, attr, None))

        arr_labels = [l.lower() for l in self.initgroup.array_labels]
        self.orig_labels = arr_labels[:]

        if self.workgroup.datatype is None:
            self.workgroup.datatype = 'raw'
            en_units = 'not energy'
            for arrlab in arr_labels[:4]:
                if 'ener' in arrlab.lower():
                    en_units = 'eV'
                    self.workgroup.datatype = 'xas'

        self.read_ok_cb = read_ok_cb
        self.array_sel = dict(xarr=None, yarr1=None, yarr2=None, yop='/',
                              ypop='', monod=3.1355316, en_units=en_units,
                              yerror='constant', yerr_val=1, yerr_arr=None,
                              yrpop='', yrop='/', yref1='', yref2='',
                              has_yref=False, multicolumn_config={})
        if last_array_sel is not None:
            self.array_sel.update(last_array_sel)

        if self.array_sel['yarr2'] is None and 'i0' in arr_labels:
            self.array_sel['yarr2'] = 'i0'

        if self.array_sel['yarr1'] is None:
            if 'itrans' in arr_labels:
                self.array_sel['yarr1'] = 'itrans'
            elif 'i1' in arr_labels:
                self.array_sel['yarr1'] = 'i1'

        if self.array_sel['yref1'] is None:
            if 'iref' in arr_labels:
                self.array_sel['yref1'] = 'iref'
            elif 'irefer' in arr_labels:
                self.array_sel['yref1'] = 'irefer'
            elif 'i2' in arr_labels:
                self.array_sel['yref1'] = 'i2'

        if self.array_sel['yref2'] is None and 'i1' in arr_labels:
            self.array_sel['yref2'] = 'i1'

        message = "Data Columns for %s" % group.filename
        wx.Frame.__init__(self, None, -1,
                          'Build Arrays from Data Columns for %s' % group.filename,
                          style=FRAMESTYLE)

        x0, y0 = parent.GetPosition()
        self.SetPosition((x0+60, y0+60))

        self.SetFont(Font(FONTSIZE))
        panel = wx.Panel(self)
        self.SetMinSize((600, 700))
        self.colors = GUIColors()

        def subtitle(s, fontsize=12, colour=wx.Colour(10, 10, 180)):
            return SimpleText(panel, s, font=Font(fontsize),
                           colour=colour, style=LEFT)

        # title row
        title = subtitle(message, colour=self.colors.title)

        yarr_labels = self.yarr_labels = arr_labels + ['1.0', '']
        xarr_labels = self.xarr_labels = arr_labels + ['_index']

        self.xarr   = Choice(panel, choices=xarr_labels, action=self.onXSelect, size=(150, -1))
        self.yarr1  = Choice(panel, choices= arr_labels, action=self.onUpdate, size=(150, -1))
        self.yarr2  = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        self.yerr_arr = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        self.yerr_arr.Disable()

        self.datatype = Choice(panel, choices=DATATYPES, action=self.onUpdate, size=(150, -1))
        self.datatype.SetStringSelection(self.workgroup.datatype)

        self.en_units = Choice(panel, choices=ENUNITS_TYPES,
                               action=self.onEnUnitsSelect, size=(150, -1))

        self.ypop = Choice(panel, choices=YPRE_OPS, action=self.onUpdate, size=(100, -1))
        self.yop =  Choice(panel, choices=ARR_OPS, action=self.onUpdate, size=(100, -1))
        self.yerr_op = Choice(panel, choices=YERR_OPS, action=self.onYerrChoice, size=(100, -1))
        self.yerr_op.SetSelection(0)

        self.yerr_val = FloatCtrl(panel, value=1, precision=4, size=(75, -1))
        self.monod_val  = FloatCtrl(panel, value=3.1355316, precision=7, size=(75, -1))

        xlab = SimpleText(panel, ' X array = ')
        ylab = SimpleText(panel, ' Y array = ')
        units_lab = SimpleText(panel, '  Units of X array:  ')
        yerr_lab = SimpleText(panel, ' Y uncertainty = ')
        dtype_lab = SimpleText(panel, ' Data Type: ')
        monod_lab = SimpleText(panel, ' Mono D spacing (Ang): ')
        yerrval_lab = SimpleText(panel, ' Value:')

        # yref
        self.has_yref = Check(panel, label='data file includes energy reference data',
                              default=self.array_sel['has_yref'],
                              action=self.onYrefCheck)
        refylab = SimpleText(panel, ' Refer array = ')
        self.yref1 = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        self.yref2 = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        self.yrpop = Choice(panel, choices=YPRE_OPS, action=self.onUpdate, size=(100, -1))
        self.yrop =  Choice(panel, choices=ARR_OPS, action=self.onUpdate, size=(100, -1))

        self.ysuf = SimpleText(panel, '')
        self.message = subtitle(' ', colour=wx.Colour(0, 0, 0))


        self.ypop.SetStringSelection(self.array_sel['ypop'])
        self.yop.SetStringSelection(self.array_sel['yop'])
        self.yrpop.SetStringSelection(self.array_sel['yrpop'])
        self.yrop.SetStringSelection(self.array_sel['yrop'])
        self.monod_val.SetValue(self.array_sel['monod'])
        self.monod_val.SetAction(self.onUpdate)
        self.monod_val.Enable(self.array_sel['en_units'].startswith('deg'))
        self.en_units.SetStringSelection(self.array_sel['en_units'])
        self.yerr_op.SetStringSelection(self.array_sel['yerror'])
        self.yerr_val.SetValue(self.array_sel['yerr_val'])
        if '(' in self.array_sel['ypop']:
            self.ysuf.SetLabel(')')

        ixsel, iysel = 0, 1
        iy2sel = iyesel = iyr1sel = iyr2sel = len(yarr_labels)-1
        if self.array_sel['xarr'] in xarr_labels:
            ixsel = xarr_labels.index(self.array_sel['xarr'])
        if self.array_sel['yarr1'] in arr_labels:
            iysel = arr_labels.index(self.array_sel['yarr1'])
        if self.array_sel['yarr2'] in yarr_labels:
            iy2sel = yarr_labels.index(self.array_sel['yarr2'])
        if self.array_sel['yerr_arr'] in yarr_labels:
            iyesel = yarr_labels.index(self.array_sel['yerr_arr'])
        if self.array_sel['yref1'] in arr_labels:
            iyr1sel = arr_labels.index(self.array_sel['yref1'])
        if self.array_sel['yref2'] in arr_labels:
            iyr2sel = arr_labels.index(self.array_sel['yref2'])

        self.xarr.SetSelection(ixsel)
        self.yarr1.SetSelection(iysel)
        self.yarr2.SetSelection(iy2sel)
        self.yerr_arr.SetSelection(iyesel)
        self.yref1.SetSelection(iyr1sel)
        self.yref2.SetSelection(iyr2sel)

        self.wid_multicol = wx.RadioBox(panel, -1, '', wx.DefaultPosition, wx.DefaultSize,
                                        ['use single data columns', 'add multi-column fluorescence'], 2,
                                        wx.RA_SPECIFY_COLS)
        self.wid_multicol.Bind(wx.EVT_RADIOBOX, self.onUseMultiColumn)
        is_multicol = len(self.array_sel.get('multicolumn_config', {})) > 0
        self.wid_multicol.SetSelection(1 if is_multicol else 0)

        self.wid_filename = wx.TextCtrl(panel, value=fix_filename(group.filename),
                                         size=(250, -1))
        self.wid_groupname = wx.TextCtrl(panel, value=group.groupname,
                                         size=(150, -1))
        if not edit_groupname:
            self.wid_groupname.Disable()
        self.wid_reffilename = wx.TextCtrl(panel, value=fix_filename(group.filename + '_ref'),
                                         size=(250, -1))
        self.wid_refgroupname = wx.TextCtrl(panel, value=group.groupname + '_ref',
                                         size=(150, -1))

        self.onYrefCheck(has_yref=self.array_sel['has_yref'])

        bpanel = wx.Panel(panel)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        _ok    = Button(bpanel, 'OK', action=self.onOK)
        _cancel = Button(bpanel, 'Cancel', action=self.onCancel)
        _edit   = Button(bpanel, 'Edit Array Names', action=self.onEditNames)
        bsizer.Add(_ok)
        bsizer.Add(_cancel)
        bsizer.Add(_edit)
        _ok.SetDefault()
        pack(bpanel, bsizer)

        sizer = wx.GridBagSizer(2, 2)
        sizer.Add(title,     (0, 0), (1, 7), LEFT, 5)

        ir = 1
        sizer.Add(subtitle(' X [ Energy ] Array:'),   (ir, 0), (1, 2), LEFT, 0)
        sizer.Add(dtype_lab,       (ir, 3), (1, 1), RIGHT, 0)
        sizer.Add(self.datatype,   (ir, 4), (1, 2), LEFT, 0)

        ir += 1
        sizer.Add(xlab,      (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.xarr, (ir, 1), (1, 2), LEFT, 0)
        sizer.Add(units_lab,     (ir, 3), (1, 1), RIGHT, 0)
        sizer.Add(self.en_units,  (ir, 4), (1, 2), LEFT, 0)

        ir += 1
        sizer.Add(monod_lab,     (ir, 2), (1, 2), RIGHT, 0)
        sizer.Add(self.monod_val,(ir, 4), (1, 1), LEFT, 0)

        ir += 1
        sizer.Add(subtitle(' Y [ \u03BC(E) ] Array:'),   (ir, 0), (1, 2), LEFT, 0)
        sizer.Add(self.wid_multicol, (ir, 2), (1, 3), LEFT, 1)
        ir += 1
        sizer.Add(ylab,       (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.ypop,  (ir, 1), (1, 1), LEFT, 0)
        sizer.Add(self.yarr1, (ir, 2), (1, 1), LEFT, 0)
        sizer.Add(self.yop,   (ir, 3), (1, 1), RIGHT, 0)
        sizer.Add(self.yarr2, (ir, 4), (1, 1), LEFT, 0)
        sizer.Add(self.ysuf,  (ir, 5), (1, 1), LEFT, 0)


        ir += 1
        sizer.Add(yerr_lab,      (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.yerr_op,  (ir, 1), (1, 1), LEFT, 0)
        sizer.Add(self.yerr_arr, (ir, 2), (1, 1), LEFT, 0)
        sizer.Add(yerrval_lab,   (ir, 3), (1, 1), RIGHT, 0)
        sizer.Add(self.yerr_val, (ir, 4), (1, 2), LEFT, 0)

        ir += 1
        sizer.Add(SimpleText(panel, ' Display Name:'), (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.wid_filename,                  (ir, 1), (1, 2), LEFT, 0)
        sizer.Add(SimpleText(panel, ' Group Name:'),   (ir, 3), (1, 1), RIGHT, 0)
        sizer.Add(self.wid_groupname,                 (ir, 4), (1, 2), LEFT, 0)

        ir += 2
        sizer.Add(subtitle(' Reference [ \u03BC_ref(E) ] Array: '),
                  (ir, 0), (1, 2), LEFT, 0)
        sizer.Add(self.has_yref,   (ir, 2), (1, 2), LEFT, 0)

        ir += 1
        sizer.Add(refylab,    (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.yrpop, (ir, 1), (1, 1), LEFT, 0)
        sizer.Add(self.yref1, (ir, 2), (1, 1), LEFT, 0)
        sizer.Add(self.yrop,  (ir, 3), (1, 1), RIGHT, 0)
        sizer.Add(self.yref2, (ir, 4), (1, 2), LEFT, 0)

        ir += 1
        sizer.Add(SimpleText(panel, ' Reference Name:'), (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.wid_reffilename,               (ir, 1), (1, 2), LEFT, 0)
        sizer.Add(SimpleText(panel, ' Group Name:'),   (ir, 3), (1, 1), RIGHT, 0)
        sizer.Add(self.wid_refgroupname,              (ir, 4), (1, 2), LEFT, 0)
        ir +=1
        sizer.Add(self.message,                     (ir, 1), (1, 4), LEFT, 0)


        ir += 1
        sizer.Add(bpanel,     (ir, 0), (1, 5), LEFT, 3)

        pack(panel, sizer)

        self.nb = fnb.FlatNotebook(self, -1, agwStyle=FNB_STYLE)
        self.nb.SetTabAreaColour(wx.Colour(248,248,240))
        self.nb.SetActiveTabColour(wx.Colour(254,254,195))
        self.nb.SetNonActiveTabTextColour(wx.Colour(40,40,180))
        self.nb.SetActiveTabTextColour(wx.Colour(80,0,0))

        self.plotpanel = PlotPanel(self, messenger=self.plot_messages)
        try:
            plotopts = self._larch.symtable._sys.wx.plotopts
            self.plotpanel.conf.set_theme(plotopts['theme'])
            self.plotpanel.conf.enable_grid(plotopts['show_grid'])
        except:
            pass


        self.plotpanel.SetMinSize((200, 200))
        textpanel = wx.Panel(self)
        ftext = wx.TextCtrl(textpanel, style=wx.TE_MULTILINE|wx.TE_READONLY,
                               size=(400, 250))

        ftext.SetValue(group.text)
        ftext.SetFont(Font(11))

        textsizer = wx.BoxSizer(wx.VERTICAL)
        textsizer.Add(ftext, 1, LEFT|wx.GROW, 1)
        pack(textpanel, textsizer)

        self.nb.AddPage(textpanel, ' Text of Data File ', True)
        self.nb.AddPage(self.plotpanel, ' Plot of Selected Arrays ', True)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 0, wx.GROW|wx.ALL, 2)
        mainsizer.Add(self.nb, 1, LEFT|wx.GROW,   2)
        pack(self, mainsizer)

        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-1, -1])
        statusbar_fields = [group.filename, ""]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        self.set_energy_units()
        self.Show()
        self.Raise()
        self.onUpdate()

    def onUseMultiColumn(self, event=None):
        if 'multi' in self.wid_multicol.GetStringSelection().lower():
            self.show_subframe('multicol', MultiChannelFrame,
                               group=self.workgroup,
                               on_ok=self.set_multichannel_info)

    def read_column_file(self, path):
        """read column file, generally as initial read"""
        parent, filename = os.path.split(path)
        reader, text = guess_filereader(path, return_text=True)

        if reader == 'read_specfile':
            if not is_specfile(path, require_multiple_scans=True):
                reader = 'read_ascii'

        if reader in ('read_xdi', 'read_gsexdi'):
            # first check for Nans and Infs
            nan_result = look_for_nans(path)
            if 'read error' in nan_result.message:
                title = "Cannot read %s" % path
                message = "Error reading %s\n%s" %(path, nan_result.message)
                r = Popup(self.parent, message, title)
                return None
            if 'no data' in nan_result.message:
                title = "No data in %s" % path
                message = "No data found in file %s" % path
                r = Popup(self.parent, message, title)
                return None

            if ('has nans' in nan_result.message or
                'has infs' in nan_result.message):
                reader = 'read_ascii'

        tmpname = '_tmpfile_'
        read_cmd = "%s = %s('%s')" % (tmpname, reader, path)
        self.reader = reader
        _larch = self._larch

        if (not isinstance(_larch, larch.Interpreter) and
            hasattr(_larch, '_larch')):
            _larch = _larch._larch
        try:
            _larch.eval(read_cmd, add_history=True)
        except:
            pass
        if len(_larch.error) > 0 and reader in ('read_xdi', 'read_gsexdi'):
            read_cmd = "%s = %s('%s')" % (tmpname, 'read_ascii', path)
            try:
                _larch.eval(read_cmd, add_history=True)
            except:
                pass
            if len(_larch.error) == 0:
                self.reader = 'read_ascii'

        if len(_larch.error) > 0:
            msg = ["Error trying to read '%s':" % path, ""]
            for err in _larch.error:
                exc_name, errmsg = err.get_error()
                msg.append(errmsg)

            title = "Cannot read %s" % path
            r = Popup(self.parent, "\n".join(msg), title)
            return None
        group = deepcopy(_larch.symtable.get_symbol(tmpname))
        _larch.symtable.del_symbol(tmpname)

        group.text = text
        group.path = path
        group.filename = filename
        group.groupname = file2groupname(filename,
                                         symtable=self._larch.symtable)
        return group

    def show_subframe(self, name, frameclass, **opts):
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except:
                pass
        if not shown:
            self.subframes[name] = frameclass(self, **opts)
            self.subframes[name].Show()
            self.subframes[name].Raise()

    def set_multichannel_info(self, label, config=None, **kws):
        new_labels = self.workgroup.array_labels
        self.set_array_labels(new_labels)
        self.yarr1.SetStringSelection(label)
        self.yarr1.SetStringSelection(label)
        self.array_sel['multicolumn_config'] = config
        self.onUpdate()

    def onEditNames(self, evt=None):
        self.show_subframe('editcol', EditColumnFrame,
                           group=self.workgroup,
                           on_ok=self.set_array_labels)

    def set_array_labels(self, arr_labels):
        self.workgroup.array_labels = arr_labels
        yarr_labels = self.yarr_labels = arr_labels + ['1.0', '']
        xarr_labels = self.xarr_labels = arr_labels + ['_index']
        def update(wid, choices):
            curstr = wid.GetStringSelection()
            curind = wid.GetSelection()
            wid.SetChoices(choices)
            if curstr in choices:
                wid.SetStringSelection(curstr)
            else:
                wid.SetSelection(curind)
        update(self.xarr,  xarr_labels)
        update(self.yarr1, yarr_labels)
        update(self.yarr2, yarr_labels)
        update(self.yerr_arr, yarr_labels)
        self.onUpdate()

    def onOK(self, event=None):
        """ build arrays according to selection """
        user_filename = self.wid_filename.GetValue()
        groupname = fix_varname(self.wid_groupname.GetValue())

        en_units = self.en_units.GetStringSelection()
        monod    = float(self.monod_val.GetValue())
        xarr     = self.xarr.GetStringSelection()
        yarr1    = self.yarr1.GetStringSelection()
        yarr2    = self.yarr2.GetStringSelection()
        ypop     = self.ypop.GetStringSelection()
        yop      = self.yop.GetStringSelection()
        yerr_op  = self.yerr_op.GetStringSelection()
        yerr_arr = self.yerr_arr.GetStringSelection()
        yerr_idx = self.yerr_arr.GetSelection()
        yerr_val = self.yerr_val.GetValue()
        yerr_expr = '1'
        if yerr_op.startswith('const'):
            yerr_expr = "%f" % self.yerr_val.GetValue()
        elif yerr_op.startswith('array'):
            yerr_expr = '%%s.data[%i, :]' % self.yerr_arr.GetSelection()
        elif yerr_op.startswith('sqrt'):
            yerr_expr = 'sqrt(%s.ydat)'
        self.expressions['yerr'] = yerr_expr

        # generate script to pass back to calling program:
        read_cmd = "%s('{path}', labels='%s')" % (self.reader,
                                                  ', '.join(self.orig_labels))
        buff = ["{group} = %s" % read_cmd,
                "{group}.path = '{path}'",
                "{group}.is_frozen = False"]

        fconf = self.array_sel.get('multicolumn_config', {})
        if len(fconf) > 0:
            sumcmd = "sum_fluor_channels({{group}}, {roi}, icr={icr}, ocr={ocr}, ltime={ltime})"
            buff.append(sumcmd.format(**fconf))

        for label, selection in self.extra_sums.items():
            buff.append("{group}.array_labels.append('%s')" % label)
            buff.append("_tmparr = {group}.data[%s, :].sum(axis=0)" % repr(selection))
            buff.append("_tmpn   = len(_tmparr)")
            buff.append("{group}.data = append({group}.data, _tmparr.reshape(1, _tmpn), axis=0)")
            buff.append("del _tmparr, _tmpn")

        for attr in ('datatype', 'plot_xlabel', 'plot_ylabel'):
            val = getattr(self.workgroup, attr)
            buff.append("{group}.%s = '%s'" % (attr, val))

        expr = self.expressions['xdat'].replace('%s', '{group:s}')
        if en_units.startswith('deg'):
            buff.append(f"monod = {monod:.9f}")
            buff.append(f"{{group}}.xdat = PLANCK_HC/(2*monod*sin(DEG2RAD*({expr:s})))")
        elif en_units.startswith('keV'):
            buff.append(f"{{group}}.xdat = 1000.0*{expr:s}")
        else:
            buff.append(f"{{group}}.xdat = {expr:s}")

        for aname in ('ydat', 'yerr'):
            expr = self.expressions[aname].replace('%s', '{group:s}')
            buff.append("{group}.%s = %s" % (aname, expr))

        if getattr(self.workgroup, 'datatype', 'raw') == 'xas':
            if self.reader == 'read_gsescan':
                buff.append("{group}.xdat = {group}.x")
            buff.append("{group}.energy = {group}.xdat")
            buff.append("{group}.mu = {group}.ydat")
            buff.append("sort_xafs({group}, overwrite=True, fix_repeats=True)")
        else:
            buff.append("{group}.scale = 1./({group}.ydat.ptp()+1.e-16)")



        array_desc = {}
        array_desc['xdat'] = self.workgroup.plot_xlabel
        array_desc['ydat'] = self.workgroup.plot_ylabel
        array_desc['yerr'] = self.expressions['yerr'].replace('%s', '{group:s}')

        ref_filename = None
        ref_groupname = None
        if self.has_yref.IsChecked():
            yrname1 = self.yref1.GetStringSelection().strip()
            yrname2 = self.yref2.GetStringSelection().strip()
            iry1    = self.yref1.GetSelection()
            iry2    = self.yref2.GetSelection()
            yrpop   = self.yrpop.GetStringSelection().strip()
            yrop    = self.yop.GetStringSelection().strip()

            ref_filename = self.wid_reffilename.GetValue()
            ref_groupname = fix_varname(self.wid_refgroupname.GetValue())

            buff.append("# reference group")
            buff.append("{refgroup} = %s" % read_cmd)
            buff.append("{refgroup}.path = '{path}'")
            buff.append("{refgroup}.is_frozen = False")
            buff.append("{refgroup}.datatype = 'xas'")
            buff.append("{refgroup}.plot_xlabel = 'energy'")
            buff.append("{refgroup}.plot_ylabel = '%s'" % self.workgroup.yrlabel)
            buff.append("{refgroup}.xdat =1.0*{group}.xdat")
            buff.append("{refgroup}.energy = {refgroup}.xdat")

            refexpr = self.expressions['yref'].replace('%s', '{group:s}')
            array_desc['yref'] = self.workgroup.yrlabel

            buff.append("{group}.energy_ref = '%s'" % (ref_groupname))
            buff.append("{refgroup}.energy_ref = '%s'" % (ref_groupname))
            buff.append("{refgroup}.ydat =  %s" % refexpr)
            buff.append("{refgroup}.mu = {refgroup}.ydat")
            buff.append("sort_xafs({refgroup}, overwrite=True, fix_repeats=True)")
            buff.append("# end reference group")
        else:
            buff.append("{group}.energy_ref = '%s'" % (groupname))


        script = "\n".join(buff)

        self.array_sel['xarr'] = xarr
        self.array_sel['yarr1'] = yarr1
        self.array_sel['yarr2'] = yarr2
        self.array_sel['yop'] = yop
        self.array_sel['ypop'] = ypop
        self.array_sel['yerror'] = yerr_op
        self.array_sel['yerr_val'] = yerr_val
        self.array_sel['yerr_arr'] = yerr_arr
        self.array_sel['monod'] = monod
        self.array_sel['en_units'] = en_units

        if self.read_ok_cb is not None:
            self.read_ok_cb(script, self.path, groupname=groupname,
                            filename=user_filename,
                            ref_groupname=ref_groupname,
                            ref_filename=ref_filename,
                            array_desc=array_desc,
                            extra_sums=self.extra_sums,
                            array_sel=self.array_sel)

        for f in self.subframes.values():
            try:
                f.Destroy()
            except:
                pass
        self.Destroy()

    def onCancel(self, event=None):
        self.workgroup.import_ok = False
        for f in self.subframes.values():
            try:
                f.Destroy()
            except:
                pass
        self.Destroy()

    def onYerrChoice(self, evt=None):
        yerr_choice = evt.GetString()
        self.yerr_arr.Disable()
        self.yerr_val.Disable()
        if 'const' in yerr_choice.lower():
            self.yerr_val.Enable()
        elif 'array' in yerr_choice.lower():
            self.yerr_arr.Enable()
        self.onUpdate()

    def onYrefCheck(self, evt=None, has_yref=False):
        if evt is not None:
            has_yref = evt.IsChecked()
        self.yref1.Enable(has_yref)
        self.yref2.Enable(has_yref)
        self.yrpop.Enable(has_yref)
        self.yrop.Enable(has_yref)
        self.wid_reffilename.Enable(has_yref)
        self.wid_refgroupname.Enable(has_yref)


    def onXSelect(self, evt=None):
        ix  = self.xarr.GetSelection()
        xname = self.xarr.GetStringSelection()

        workgroup = self.workgroup
        rdata = self.initgroup.data
        ncol, npts = rdata.shape
        if xname.startswith('_index') or ix >= ncol:
            workgroup.xdat = 1.0*np.arange(npts)
        else:
            workgroup.xdat = 1.0*rdata[ix, :]
        self.onUpdate()

        self.monod_val.Disable()
        if self.datatype.GetStringSelection().strip().lower() == 'raw':
            self.en_units.SetSelection(4)
        else:
            eguess = guess_energy_units(workgroup.xdat)
            if eguess.startswith('keV'):
                self.en_units.SetSelection(1)
            elif eguess.startswith('deg'):
                self.en_units.SetSelection(2)
                self.monod_val.Enable()
            else:
                self.en_units.SetSelection(0)

    def onEnUnitsSelect(self, evt=None):
        self.monod_val.Enable(self.en_units.GetStringSelection().startswith('deg'))
        self.onUpdate()

    def set_energy_units(self):
        ix  = self.xarr.GetSelection()
        xname = self.xarr.GetStringSelection()
        rdata = self.initgroup.data
        ncol, npts = rdata.shape
        workgroup = self.workgroup
        if xname.startswith('_index') or ix >= ncol:
            workgroup.xdat = 1.0*np.arange(npts)
        else:
            workgroup.xdat = 1.0*rdata[ix, :]
        if self.datatype.GetStringSelection().strip().lower() != 'raw':
            eguess =  guess_energy_units(workgroup.xdat)
            if eguess.startswith('eV'):
                self.en_units.SetStringSelection('eV')
            elif eguess.startswith('keV'):
                self.en_units.SetStringSelection('keV')

    def onUpdate(self, evt=None, **kws):
        """column selections changed calc xdat and ydat"""
        rawgroup = self.initgroup
        workgroup = self.workgroup
        rdata = self.initgroup.data

        ix  = self.xarr.GetSelection()
        xname = self.xarr.GetStringSelection()

        exprs = dict(xdat=None, ydat=None, yerr=None, yref=None)

        try:
            ncol, npts = rdata.shape
        except:
            return

        workgroup.index = 1.0*np.arange(npts)
        if xname.startswith('_index') or ix >= ncol:
            workgroup.xdat = 1.0*np.arange(npts)
            xname = '_index'
            exprs['xdat'] = 'arange(%i)' % npts
        else:
            workgroup.xdat = 1.0*rdata[ix, :]
            exprs['xdat'] = '%%s.data[%i, : ]' % ix

        workgroup.datatype = self.datatype.GetStringSelection().strip().lower()
        if workgroup.datatype == 'raw':
            self.en_units.SetStringSelection('not energy')

        xlabel = xname
        en_units = self.en_units.GetStringSelection()
        monod = float(self.monod_val.GetValue())
        if en_units.startswith('deg'):
            workgroup.xdat = PLANCK_HC/(2*monod*np.sin(DEG2RAD*workgroup.xdat))
            xlabel = xname + ' (eV)'
        elif en_units.startswith('keV'):
            workgroup.xdat *= 1000.0
            xlabel = xname + ' (eV)'


        def pre_op(opwid, arr):
            opstr = opwid.GetStringSelection().strip()
            if opstr == '-':
                return '', opstr, -arr
            suf = ''
            if opstr in ('-log(', 'log('):
                suf = ')'
                if opstr == 'log(':
                    arr = np.log(arr)
                elif opstr == '-log(':
                    arr = -np.log(arr)
                arr[np.where(np.isnan(arr))] = 0
            return suf, opstr, arr

        yname1  = self.yarr1.GetStringSelection().strip()
        yname2  = self.yarr2.GetStringSelection().strip()
        iy1    = self.yarr1.GetSelection()
        iy2    = self.yarr2.GetSelection()
        yop = self.yop.GetStringSelection().strip()

        ylabel = yname1
        if len(yname2) == 0:
            yname2 = '1.0'
        else:
            ylabel = "%s%s%s" % (ylabel, yop, yname2)

        if yname1 == '0.0':
            yarr1 = np.zeros(npts)*1.0
            yexpr1 = 'zeros(%i)' % npts
        elif len(yname1) == 0 or yname1 == '1.0' or iy1 >= ncol:
            yarr1 = np.ones(npts)*1.0
            yexpr1 = 'ones(%i)' % npts
        else:
            yarr1 = rdata[iy1, :]
            yexpr1 = '%%s.data[%i, : ]' % iy1

        if yname2 == '0.0':
            yarr2 = np.zeros(npts)*1.0
            yexpr2 = '0.0'
        elif len(yname2) == 0 or yname2 == '1.0' or iy2 >= ncol:
            yarr2 = np.ones(npts)*1.0
            yexpr2 = '1.0'
        else:
            yarr2 = rdata[iy2, :]
            yexpr2 = '%%s.data[%i, : ]' % iy2

        workgroup.ydat = yarr1

        exprs['ydat'] = yexpr1
        if yop in ('+', '-', '*', '/'):
            exprs['ydat'] = "%s %s %s" % (yexpr1, yop, yexpr2)
            if yop == '+':
                workgroup.ydat = yarr1.__add__(yarr2)
            elif yop == '-':
                workgroup.ydat = yarr1.__sub__(yarr2)
            elif yop == '*':
                workgroup.ydat = yarr1.__mul__(yarr2)
            elif yop == '/':
                workgroup.ydat = yarr1.__truediv__(yarr2)

        ysuf, ypop, workgroup.ydat = pre_op(self.ypop, workgroup.ydat)
        self.ysuf.SetLabel(ysuf)
        exprs['ydat'] = '%s%s%s' % (ypop, exprs['ydat'], ysuf)
        ylabel = '%s%s%s' % (ypop, ylabel,ysuf)

        # error
        yerr_arr = self.yerr_arr.GetStringSelection()
        yerr_op = self.yerr_op.GetStringSelection().lower()
        exprs['yerr'] = '1'
        yerr_val = self.yerr_val.GetValue()
        if yerr_op.startswith('const'):
            yerr = yerr_val
            exprs['yerr'] = '%f' % yerr_val
        elif yerr_op.startswith('array'):
            iyerr = self.yerr_arr.GetSelection()
            yerr = rdata[iyerr, :]
            exprs['yerr'] = '%%s.data[%i, :]' % iyerr
        elif yerr_op.startswith('sqrt'):
            yerr = np.sqrt(workgroup.ydat)
            exprs['yerr'] = 'sqrt(%s.ydat)'

        # ref
        has_yref = self.has_yref.IsChecked()
        yrname1  = self.yref1.GetStringSelection().strip()
        yrname2  = self.yref2.GetStringSelection().strip()
        iry1    = self.yref1.GetSelection()
        iry2    = self.yref2.GetSelection()
        yrpop  = self.yrpop.GetStringSelection().strip()
        yrop   = self.yop.GetStringSelection().strip()
        yrlabel = ''
        if has_yref:
            yrlabel = yrname1
            if len(yrname2) == 0:
                yrname2 = '1.0'
            else:
                yrlabel = "%s%s%s" % (yrlabel, yrop, yrname2)

            if yrname1 == '0.0':
                yrarr1 = np.zeros(npts)*1.0
                yrexpr1 = 'zeros(%i)' % npts
            elif len(yrname1) == 0 or yrname1 == '1.0' or iry1 >= ncol:
                yrarr1 = np.ones(npts)*1.0
                yrexpr1 = 'ones(%i)' % npts
            else:
                yrarr1 = rdata[iry1, :]
                yrexpr1 = '%%s.data[%i, : ]' % iry1

            if yrname2 == '0.0':
                yrarr2 = np.zeros(npts)*1.0
                yrexpr2 = '0.0'
            elif len(yrname2) == 0 or yrname2 == '1.0' or iry2 >= ncol:
                yrarr2 = np.ones(npts)*1.0
                yrexpr2 = '1.0'
            else:
                yrarr2 = rdata[iry2, :]
                yrexpr2 = '%%s.data[%i, : ]' % iry2

            workgroup.yref = yrarr1
            exprs['yref'] = yrexpr1
            if yrop in ('+', '-', '*', '/'):
                exprs['yref'] = "%s %s %s" % (yrexpr1, yop, yrexpr2)
                if yrop == '+':
                    workgroup.yref = yrarr1.__add__(yrarr2)
                elif yrop == '-':
                    workgroup.yref = yrarr1.__sub__(yrarr2)
                elif yrop == '*':
                    workgroup.yref = yrarr1.__mul__(yarr2)
                elif yrop == '/':
                    workgroup.yref = yrarr1.__truediv__(yrarr2)

            yrsuf, yprop, workgroup.yref = pre_op(self.yrpop, workgroup.yref)
            exprs['yref'] = '%s%s%s' % (yrpop, exprs['yref'], yrsuf)
            yrlabel = '%s%s%s' % (yrpop, yrlabel, yrsuf)
            workgroup.yrlabel = yrlabel

        self.expressions = exprs

        self.array_sel.update(dict(xarr=xname, ypop=ypop, yop=yop,
                                   yarr1=yname1, yarr2=yname2, monod=monod,
                                   en_units=en_units, yerror=yerr_op,
                                   yerr_val=yerr_val, yerr_arr=yerr_arr,
                                   yrpop=yrpop, yrop=yrop, yref1=yrname1,
                                   yref2=yrname2, has_yref=has_yref))

        try:
            npts = min(len(workgroup.xdat), len(workgroup.ydat))
        except AttributeError:
            return
        except ValueError:
            return

        en = workgroup.xdat
        if ((workgroup.datatype == 'xas') and
            ((len(en) > 1000 or any(np.diff(en) < 0) or
              ((max(en)-min(en)) > 350 and
               (np.diff(en[:100]).mean() < 1.0))))):
            self.message.SetLabel("Warning: XAS data may need to be rebinned!")
        else:
            self.message.SetLabel("")

        workgroup.filename    = rawgroup.filename
        workgroup.npts        = npts
        workgroup.plot_xlabel = xlabel
        workgroup.plot_ylabel = ylabel
        workgroup.plot_yrlabel = yrlabel
        workgroup.xdat        = np.array(workgroup.xdat[:npts])
        workgroup.ydat        = np.array(workgroup.ydat[:npts])
        workgroup.y           = workgroup.ydat
        workgroup.yerr        = yerr
        if isinstance(yerr, np.ndarray):
            workgroup.yerr    = np.array(yerr[:npts])

        if workgroup.datatype == 'xas':
            workgroup.energy = workgroup.xdat
            workgroup.mu     = workgroup.ydat

        path, fname = os.path.split(workgroup.filename)
        popts = dict(marker='o', markersize=4, linewidth=1.5,
                     title=fname, ylabel=ylabel, xlabel=xlabel,
                     label=ylabel)

        self.plotpanel.plot(workgroup.xdat, workgroup.ydat, **popts)
        if has_yref:
            self.plotpanel.oplot(workgroup.xdat, workgroup.yref,
                                 y2label=yrlabel,
                                 linewidth=2.0, color='#E08070',
                                 label=yrlabel, zorder=-40, side='right')


        for i in range(self.nb.GetPageCount()):
            if 'plot' in self.nb.GetPageText(i).lower():
                self.nb.SetSelection(i)

    def plot_messages(self, msg, panel=1):
        self.statusbar.SetStatusText(msg, panel)
