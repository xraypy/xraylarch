#!/usr/bin/env python
"""

"""
import re
from copy import deepcopy

import numpy as np
np.seterr(all='ignore')
from pathlib import Path
from functools import partial

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb
from wxmplot import PlotPanel

from wxutils import (SimpleText, FloatCtrl, FloatSpin, GUIColors, Button, Choice,
                     TextCtrl, pack, Popup, Check, MenuItem, CEN, RIGHT, LEFT,
                     FRAMESTYLE, HLine, Font)

import larch
from larch import Group
from larch.xafs.xafsutils import guess_energy_units
from larch.utils.strutils import fix_varname, fix_filename, file2groupname
from larch.io import look_for_nans,  guess_filereader, is_specfile, sum_fluor_channels
from larch.utils.physical_constants import PLANCK_HC, DEG2RAD
from larch.utils import gformat
from larch.math import safe_log
from . import FONTSIZE

CEN |=  wx.ALL
FNB_STYLE = fnb.FNB_NO_X_BUTTON|fnb.FNB_SMART_TABS
FNB_STYLE |= fnb.FNB_NO_NAV_BUTTONS|fnb.FNB_NODRAG

YPRE_OPS = ('', 'log(', '-log(', '-')
ARR_OPS = ('+', '-', '*', '/')

YERR_OPS = ('Constant', 'Sqrt(Y)', 'Array')
CONV_OPS  = ('Lorenztian', 'Gaussian')

DATATYPES = ('xydata', 'xas')
ENUNITS_TYPES = ('eV', 'keV', 'degrees', 'not energy')


MULTICHANNEL_TITLE = """ Sum MultiChannel Fluorescence Data, with Dead-Time Corrections:
  To allow for many Dead-Time-Correction methods, each Channel is built as:
        ROI_Corrected = ROI * ICR /(OCR * LTIME)

  Set the Number of Channels, the Step (usually 1) between columns for
  ROI 1, 2, ..., NChans, and any Bad Channels: a list of Channel numbers (start at 1).

  Select columns for ROI (counts) and correction factors ICR, OCR, and LTIME for Channel 1.

"""

ROI_STEP_TOOLTIP =  """number of columns between ROI columns -- typically 1 if the columns are like
   ROI_Ch1 ROI_Ch2 ROI_Ch3 ... ICR_Ch1 ICR_Ch2 ICR_Ch3 ... OCR_Ch1 OCR_Ch2 OCR_Ch3 ...

but set to 3 if the columns are arranged as
   ROI_Ch1 ICR_Ch1 OCR_Ch1 ROI_Ch2 ICR_Ch2 OCR_Ch2 ROI_Ch3 ICR_Ch3 OCR_Ch3 ...
"""
MAXCHANS=2000

class DeadtimeCorrectionFrame(wx.Frame):
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

        self.SetFont(Font(FONTSIZE))
        sizer = wx.GridBagSizer(2, 2)
        panel = scrolled.ScrolledPanel(self)

        self.SetMinSize((650, 450))
        self.yarr_labels = [s for s in self.parent.yarr_labels]
        wids = self.wids = {}

        multi_title = wx.StaticText(panel, label=MULTICHANNEL_TITLE, size=(650, 150))
        multi_title.SetFont(Font(FONTSIZE-1))
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

        wids['nchans']  = FloatCtrl(panel, value=self.config.get('nchans', 4),
                                    precision=0, maxval=MAXCHANS, minval=1, size=(50, -1),
                                    action=self.on_nchans)
        wids['bad_chans'] = TextCtrl(panel, value='', size=(175, -1), action=self.read_form)
        bad_chans = self.config.get('bad_chans', [])
        if len(bad_chans) > 0:
            wids['bad_chans'].SetValue(', '.join(['%d' % c for c in bad_chans]))
        wids['bad_chans'].SetToolTip("List Channels to skip, separated by commas or spaces")
        wids['step']    = FloatCtrl(panel, value=self.config.get('step', 1), precision=0,
                                    maxval=MAXCHANS, minval=1, size=(50, -1), action=self.read_form)
        wids['step'].SetToolTip(ROI_STEP_TOOLTIP)

        wids['plot_chan'] = FloatSpin(panel, value=self.config.get('plot_chan', 1),
                                      digits=0, increment=1, max_val=MAXCHANS, min_val=1, size=(50, -1),
                                      action=self.onPlotThis)

        wids['plot_this'] = Button(panel, 'Plot ROI + Correction For Channel', action=self.onPlotThis)
        wids['plot_all'] = Button(panel, 'Plot All Channels', action=self.onPlotEach)
        wids['plot_sum'] = Button(panel, 'Plot Sum of Channels',   action=self.onPlotSum)
        wids['save_btn'] = Button(panel, 'Use this Sum of Channels',  action=self.onOK_DTC)

        def tlabel(t):
            return SimpleText(panel, label=t)

        sizer.Add(multi_title,       (0, 0), (2, 5), LEFT, 3)
        ir = 2
        sizer.Add(HLine(panel, size=(650, 2)), (ir, 0), (1, 5), LEFT, 3)

        ir += 1
        sizer.Add(tlabel(' Number of Channels:'),   (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['nchans'],                   (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(tlabel(' Step between Channels:'), (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(wids['step'],                     (ir, 3), (1, 1), LEFT, 3)

        ir += 1
        sizer.Add(tlabel(' Bad Channels :'),   (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['bad_chans'],           (ir, 1), (1, 2), LEFT, 3)

        ir += 1
        sizer.Add(HLine(panel, size=(650, 2)), (ir, 0), (1, 5), LEFT, 3)

        ir += 1
        sizer.Add(tlabel(' Signal '),  (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(tlabel(' Array for Channel #1 '),  (ir, 1), (1, 1), LEFT, 3)
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
        sizer.Add(HLine(panel, size=(650, 2)), (ir, 0), (1, 5), LEFT, 3)

        ir += 1
        sizer.Add(wids['plot_this'],   (ir, 0), (1, 2), LEFT, 3)
        sizer.Add(tlabel(' Channel:'), (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(wids['plot_chan'],   (ir, 3), (1, 1), LEFT, 3)

        ir += 1
        sizer.Add(HLine(panel, size=(650, 2)), (ir, 0), (1, 5), LEFT, 3)
        ir += 1
        sizer.Add(wids['plot_all'],  (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['plot_sum'],  (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(wids['save_btn'],  (ir, 2), (1, 2), LEFT, 3)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def get_en_i0(self):
        en = self.group.xplot
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

    def onOK_DTC(self, event=None):
        self.read_form()
        if callable(self.on_ok):
            self.on_ok(self.config)
        self.Destroy()

    def onPlotSum(self, event=None):
        self.read_form()
        en, i0 = self.get_en_i0()
        label, sum = sum_fluor_channels(self.group, self.config['roi'],
                                        icr=self.config['icr'],
                                        ocr=self.config['ocr'],
                                        ltime=self.config['ltime'],
                                        add_data=False)
        if sum is not None:
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

    def on_nchans(self, event=None, value=None, **kws):
        try:
            nchans = self.wids['nchans'].GetValue()
            pchan = self.wids['plot_chan'].GetValue()
            self.wids['plot_chan'].SetMax(nchans)
            self.wids['plot_chan'].SetValue(pchan)
        except:
            pass

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

        self.config['bad_chans'] = bad_channels
        self.config['plot_chan'] = pchan
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
                        nchan = chans[i]
                        if nchan < len(self.group.array_labels):
                            labs.append(self.group.array_labels[nchan])
                wids[f"{s}_txt"].SetLabel(', '.join(labs))
                self.config[s] = chans


class MultiColumnFrame(wx.Frame) :
    """Select Multiple Columns for import, optional i0 channel"""
    def __init__(self, parent, group, config=None, on_ok=None):
        self.parent = parent
        self.group = group

        self.on_ok = on_ok
        wx.Frame.__init__(self, None, -1, 'Import Multiple Columns from a file',
                          style=wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.config = {'channels': [], 'i0': '1.0'}
        if config is not None:
            self.config.update(config)

        self.SetFont(Font(FONTSIZE))
        sizer = wx.GridBagSizer(2, 2)
        panel = scrolled.ScrolledPanel(self)

        self.SetMinSize((475, 350))
        self.yarr_labels = [s for s in self.parent.yarr_labels]
        wids = self.wids = {}

        wids['i0'] = Choice(panel, choices=self.yarr_labels, size=(200, -1))
        wids['i0'].SetToolTip("All Channels will be divided by the I0 array")

        wids['i0'].SetStringSelection(self.parent.yarr2.GetStringSelection())

        bpanel = wx.Panel(panel)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)

        bsizer.Add(Button(bpanel, ' Select All ', action=self.onSelAll))
        bsizer.Add(Button(bpanel, ' Select None ', action=self.onSelNone))
        bsizer.Add(Button(bpanel, ' Plot Selected ', action=self.onPlotSel))
        bsizer.Add(Button(bpanel, ' Import Selected Columns ', action=self.onOK_Multi))
        pack(bpanel, bsizer)

        ir = 0
        sizer.Add(bpanel,  (ir, 0), (1, 5), LEFT, 3)
        ir += 1
        sizer.Add(HLine(panel, size=(450, 2)),  (ir, 0), (1, 5), LEFT, 3)

        ir += 1
        sizer.Add(SimpleText(panel, label=' I0 Array: '), (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['i0'],                        (ir, 1), (1, 3), LEFT, 3)

        ir += 1
        sizer.Add(SimpleText(panel, label=' Array Name'),  (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(SimpleText(panel, label=' Select '),   (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(SimpleText(panel, label=' Plot'),       (ir, 2), (1, 1), LEFT, 3)

        array_labels = getattr(group, 'array_labels', self.yarr_labels)
        nlabels = len(array_labels)
        narrays, npts = group.data.shape
        for i in range(narrays):
            if i < nlabels:
                name = array_labels[i]
            else:
                name = f'unnamed_column{i+1}'
            self.wids[f'use_{i}'] = chuse = Check(panel, label='', default=(i in self.config['channels']))
            slabel = SimpleText(panel, label=f' {name}  ')
            bplot  = Button(panel, 'Plot', action=partial(self.onPlot, index=i))

            ir += 1
            sizer.Add(slabel, (ir, 0), (1, 1), LEFT, 3)
            sizer.Add(chuse,  (ir, 1), (1, 1), LEFT, 3)
            sizer.Add(bplot,  (ir, 2), (1, 1), LEFT, 3)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()


    def onSelAll(self, event=None, *kws):
        for wname, wid in self.wids.items():
            if wname.startswith('use_'):
                wid.SetValue(1)

    def onSelNone(self, event=None, *kws):
        for wname, wid in self.wids.items():
            if wname.startswith('use_'):
                wid.SetValue(0)

    def onPlotSel(self, event=None):
        group = self.group
        self.config['i0']  = self.wids['i0'].GetSelection()
        channels = []
        x = self.group.xplot
        popts = dict(marker=None, markersize=0, linewidth=2.5,
                     ylabel='selected arrays', show_legend=True,
                     xlabel=self.group.plot_xlabel, delay_draw=True)
        first = True
        for wname, wid in self.wids.items():
            if wname.startswith('use_') and wid.IsChecked():
                chan = int(wname.replace('use_', ''))
                y = self.group.data[chan, :]
                try:
                    label = self.group.array_labels[chan]
                except:
                    label = f'column {chan+1}'
                plot = self.parent.plotpanel.oplot
                if first:
                    first = False
                    plot = self.parent.plotpanel.plot
                plot(x, y, label=label, **popts)
        self.parent.plotpanel.draw()


    def onPlot(self, event=None, index=None):
        if index is not None:
            x = self.group.xplot
            y = self.group.data[index, :]
            try:
                label = self.group.array_labels[index]
            except:
                label = f'column {index+1}'

            popts = dict(marker=None, markersize=0, linewidth=2.5,
                         ylabel=label, xlabel=self.group.plot_xlabel, label=label)
            self.parent.plotpanel.plot(x, y, **popts)

    def onOK_Multi(self, evt=None):
        group = self.group
        self.config['i0']  = self.wids['i0'].GetSelection()
        channels = []
        for wname, wid in self.wids.items():
            if wname.startswith('use_') and wid.IsChecked():
                chan = int(wname.replace('use_', ''))
                channels.append(chan)

        self.config['channels']  = channels
        if callable(self.on_ok):
            self.on_ok(self.config)
        self.Destroy()


class EditColumnFrame(wx.Frame) :
    """Edit Column Labels for a larch grouop"""
    def __init__(self, parent, group, on_ok=None):
        self.parent = parent
        self.group = group
        self.on_ok = on_ok
        wx.Frame.__init__(self, None, -1, 'Edit Array Names',
                          style=wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.SetFont(Font(FONTSIZE))
        sizer = wx.GridBagSizer(2, 2)
        panel = scrolled.ScrolledPanel(self)

        self.SetMinSize((700, 450))

        self.wids = {}
        ir = 0
        sizer.Add(Button(panel, 'Apply Changes', size=(200, -1),
                         action=self.onOK_Edit),
                  (0, 1), (1, 2), LEFT, 3)
        sizer.Add(Button(panel, 'Use Column Number', size=(200, -1),
                         action=self.onColNumber),
                  (0, 3), (1, 2), LEFT, 3)
        sizer.Add(HLine(panel, size=(550, 2)),
                  (1, 1), (1, 5), LEFT, 3)

        cind = SimpleText(panel, label='Column')
        cold = SimpleText(panel, label=' Current Name')
        cnew = SimpleText(panel, label=' Enter New Name')
        cret = SimpleText(panel, label=' Result   ')
        cinfo = SimpleText(panel, label=' Data Range')
        cplot = SimpleText(panel, label=' Plot')

        ir = 2
        sizer.Add(cind,  (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(cold,  (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(cnew,  (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(cret,  (ir, 3), (1, 1), LEFT, 3)
        sizer.Add(cinfo, (ir, 4), (1, 1), LEFT, 3)
        sizer.Add(cplot, (ir, 5), (1, 1), LEFT, 3)

        nlabels = len(group.array_labels)
        narrays, npts = group.data.shape
        for i in range(narrays):
            if i < nlabels:
                name = group.array_labels[i]
            else:
                name = f'unnamed_column{i+1}'
            ir += 1
            cind = SimpleText(panel, label=f' {i+1} ')
            cold = SimpleText(panel, label=f' {name} ')
            cret = SimpleText(panel, label=fix_varname(name))
            cnew = wx.TextCtrl(panel, value=name, size=(150, -1),
                               style=wx.TE_PROCESS_ENTER)

            cnew.Bind(wx.EVT_TEXT_ENTER, partial(self.update, index=i))
            cnew.Bind(wx.EVT_KILL_FOCUS, partial(self.update, index=i))

            arr = group.data[i,:]
            info_str = f" [{gformat(arr.min(),length=9)}:{gformat(arr.max(), length=9)}] "
            cinfo = SimpleText(panel, label=info_str)
            cplot = Button(panel, 'Plot', action=partial(self.onPlot, index=i))


            self.wids[f"{i}"] = cnew
            self.wids[f"ret_{i}"] = cret

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
            x = self.group.index
            y = self.group.data[index, :]
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
        newval = fix_varname(self.wids[f"{index}"].GetValue())
        self.wids[f"ret_{index}"].SetLabel(newval)

    def update_char(self, evt=None, index=-1):
        if evt.GetKeyCode() == wx.WXK_RETURN:
            self.update(evt=evt, index=index)
        # evt.Skip()

    def onOK_Edit(self, evt=None):
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
    def __init__(self, parent, filename=None, groupname=None, config=None,
                 read_ok_cb=None, edit_groupname=True, _larch=None):
        self.parent = parent
        self._larch = _larch
        self.path = filename

        group = self.read_column_file(self.path)
        # print("COLUMN FILE Read ", self.path, getattr(group, 'datatype', 'unknown'))
        self.subframes = {}
        self.workgroup  = Group(raw=group)
        for attr in ('path', 'filename', 'groupname', 'datatype',
                     'array_labels', 'data'):
            setattr(self.workgroup, attr, getattr(group, attr, None))

        self.array_labels = [l.lower() for l in group.array_labels]

        has_energy = False
        en_units = 'unknown'
        for arrlab in self.array_labels[:5]:
            arrlab  = arrlab.lower()
            if arrlab.startswith('en') or 'ener' in arrlab:
                en_units = 'eV'
                has_energy = True

        # print("C : ", has_energy, self.workgroup.datatype, config)

        if self.workgroup.datatype in (None, 'unknown'):
            self.workgroup.datatype = 'xas' if has_energy else 'xydata'

        en_units = 'eV' if self.workgroup.datatype == 'xas' else 'unknown'

        self.read_ok_cb = read_ok_cb
        self.config = dict(xarr=None, yarr1=None, yarr2=None, yop='/',
                           ypop='', monod=3.1355316, en_units=en_units,
                           yerr_op='constant', yerr_val=1, yerr_arr=None,
                           yrpop='', yrop='/', yref1='', yref2='',
                           has_yref=False, dtc_config={}, multicol_config={})
        if config is not None:
            if 'datatype' in config:
                config.pop('datatype')
            self.config.update(config)

        if self.config['yarr2'] is None and 'i0' in self.array_labels:
            self.config['yarr2'] = 'i0'

        if self.config['yarr1'] is None:
            if 'itrans' in self.array_labels:
                self.config['yarr1'] = 'itrans'
            elif 'i1' in self.array_labels:
                self.config['yarr1'] = 'i1'

        if self.config['yref1'] is None:
            if 'iref' in self.array_labels:
                self.config['yref1'] = 'iref'
            elif 'irefer' in self.array_labels:
                self.config['yref1'] = 'irefer'
            elif 'i2' in self.array_labels:
                self.config['yref1'] = 'i2'

        if self.config['yref2'] is None and 'i1' in self.array_labels:
            self.config['yref2'] = 'i1'

        use_trans = self.config.get('is_trans', False) or 'log' in self.config['ypop']

        message = "Data Columns for %s" % group.filename
        wx.Frame.__init__(self, None, -1,
                          'Build Arrays from Data Columns for %s' % group.filename,
                          style=FRAMESTYLE)

        x0, y0 = parent.GetPosition()
        self.SetPosition((x0+60, y0+60))

        self.SetFont(Font(FONTSIZE))
        panel = wx.Panel(self)
        self.SetMinSize((725, 700))
        self.colors = GUIColors()

        def subtitle(s, fontsize=12, colour=wx.Colour(10, 10, 180)):
            return SimpleText(panel, s, font=Font(fontsize),
                           colour=colour, style=LEFT)

        # title row
        title = subtitle(message, colour=self.colors.title)

        yarr_labels = self.yarr_labels = self.array_labels + ['1.0', '']
        xarr_labels = self.xarr_labels = self.array_labels + ['_index']

        self.xarr   = Choice(panel, choices=xarr_labels, action=self.onXSelect, size=(150, -1))
        self.yarr1  = Choice(panel, choices= self.array_labels, action=self.onUpdate, size=(150, -1))
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

        self.is_trans = Check(panel, label='is transmission data?',
                              default=use_trans, action=self.onTransCheck)

        self.yerr_val = FloatCtrl(panel, value=1, precision=4, size=(75, -1))
        self.monod_val  = FloatCtrl(panel, value=3.1355316, precision=7, size=(75, -1))

        xlab = SimpleText(panel, ' X array = ')
        ylab = SimpleText(panel, ' Y array = ')
        units_lab = SimpleText(panel, '  Units of X array:  ')
        yerr_lab = SimpleText(panel, ' Y uncertainty = ')
        dtype_lab = SimpleText(panel, ' Data Type: ')
        monod_lab = SimpleText(panel, ' Mono D spacing (Ang): ')
        yerrval_lab = SimpleText(panel, ' Value:')
        self.info_message = subtitle('    ', colour=wx.Colour(100, 10, 10))

        # yref
        self.has_yref = Check(panel, label='data file includes energy reference data',
                              default=self.config['has_yref'],
                              action=self.onYrefCheck)
        refylab = SimpleText(panel, ' Refer array = ')
        self.yref1 = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        self.yref2 = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        self.yrpop = Choice(panel, choices=YPRE_OPS, action=self.onUpdate, size=(100, -1))
        self.yrop =  Choice(panel, choices=ARR_OPS, action=self.onUpdate, size=(100, -1))

        self.ysuf = SimpleText(panel, '')
        # print("COL FILE READER set ypop to ", use_trans, self.config['ypop'])
        self.ypop.SetStringSelection(self.config['ypop'])
        self.yop.SetStringSelection(self.config['yop'])
        self.yrpop.SetStringSelection(self.config['yrpop'])
        self.yrop.SetStringSelection(self.config['yrop'])
        self.monod_val.SetValue(self.config['monod'])
        self.monod_val.SetAction(self.onUpdate)
        self.monod_val.Enable(self.config['en_units'].startswith('deg'))
        self.en_units.SetStringSelection(self.config['en_units'])
        self.yerr_op.SetStringSelection(self.config['yerr_op'])
        self.yerr_val.SetValue(self.config['yerr_val'])
        if '(' in self.config['ypop']:
            self.ysuf.SetLabel(')')


        ixsel, iysel = 0, 1
        iy2sel = iyesel = iyr1sel = iyr2sel = len(yarr_labels)-1
        if self.config['xarr'] in xarr_labels:
            ixsel = xarr_labels.index(self.config['xarr'])
        if self.config['yarr1'] in self.array_labels:
            iysel = self.array_labels.index(self.config['yarr1'])
        if self.config['yarr2'] in yarr_labels:
            iy2sel = yarr_labels.index(self.config['yarr2'])
        if self.config['yerr_arr'] in yarr_labels:
            iyesel = yarr_labels.index(self.config['yerr_arr'])
        if self.config['yref1'] in self.array_labels:
            iyr1sel = self.array_labels.index(self.config['yref1'])
        if self.config['yref2'] in self.array_labels:
            iyr2sel = self.array_labels.index(self.config['yref2'])

        self.xarr.SetSelection(ixsel)
        self.yarr1.SetSelection(iysel)
        self.yarr2.SetSelection(iy2sel)
        self.yerr_arr.SetSelection(iyesel)
        self.yref1.SetSelection(iyr1sel)
        self.yref2.SetSelection(iyr2sel)

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

        self.onTransCheck(is_trans=use_trans)
        self.onYrefCheck(has_yref=self.config['has_yref'])


        bpanel = wx.Panel(panel)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        _ok    = Button(bpanel, 'OK', action=self.onOK)
        _cancel = Button(bpanel, 'Cancel', action=self.onCancel)
        _edit   = Button(bpanel, 'Edit Array Names', action=self.onEditNames)
        self.multi_sel = Button(bpanel, 'Select Multilple Columns',  action=self.onMultiColumn)
        self.multi_clear = Button(bpanel, 'Clear Multiple Columns',  action=self.onClearMultiColumn)
        self.multi_clear.Disable()
        _edit.SetToolTip('Change the current Column Names')

        self.multi_sel.SetToolTip('Select Multiple Columns to import as separate groups')
        self.multi_clear.SetToolTip('Clear Multiple Column Selection')
        bsizer.Add(_ok)
        bsizer.Add(_cancel)
        bsizer.Add(_edit)
        bsizer.Add(self.multi_sel)
        bsizer.Add(self.multi_clear)
        _ok.SetDefault()
        pack(bpanel, bsizer)

        self.dtc_button  = Button(panel, 'Sum and Correct Fluoresence Data', action=self.onDTC)
        self.dtc_button.SetToolTip('Select channels and do deadtime-corrections for multi-element fluorescence data')

        sizer = wx.GridBagSizer(2, 2)
        sizer.Add(title,     (0, 0), (1, 7), LEFT, 5)

        ir = 1
        sizer.Add(subtitle(' X [Energy] Array:'),   (ir, 0), (1, 2), LEFT, 0)
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
        sizer.Add(subtitle(' Y [\u03BC(E)] Array:'), (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.is_trans,                     (ir, 1), (1, 2), LEFT, 0)
        sizer.Add(self.dtc_button,                   (ir, 3), (1, 2), RIGHT, 0)
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

        ir += 1
        sizer.Add(self.info_message,                  (ir, 0), (1, 5), LEFT, 1)

        ir += 2
        sizer.Add(subtitle(' Reference [\u03BC_ref(E)] Array: '),
                  (ir, 0), (1, 2), LEFT, 0)
        sizer.Add(self.has_yref,   (ir, 2), (1, 3), LEFT, 0)

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
        ftext.SetFont(Font(FONTSIZE))

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
        dtc_conf = self.config.get('dtc_config', {})
        if len(dtc_conf) > 0:
            self.onDTC_OK(dtc_conf, update=False)

        self.Show()
        self.Raise()
        self.onUpdate()

    def onDTC(self, event=None):
        self.show_subframe('dtc_conf', DeadtimeCorrectionFrame,
                           config=self.config['dtc_config'],
                           group=self.workgroup,
                           on_ok=self.onDTC_OK)

    def onDTC_OK(self, config, update=True, **kws):
        label, sum = sum_fluor_channels(self.workgroup, config['roi'],
                                        icr=config['icr'],
                                        ocr=config['ocr'],
                                        ltime=config['ltime'],
                                        add_data=False)
        if sum is None:
            return
        self.info_message.SetLabel(f"Added array '{label}' with summed and corrected fluorecence data")
        self.workgroup.array_labels.append(label)
        self.set_array_labels(self.workgroup.array_labels)
        npts = len(sum)
        new = np.append(self.workgroup.raw.data, sum.reshape(1, npts), axis=0)
        self.workgroup.raw.data = new[()]
        self.workgroup.data = new[()]
        self.yarr1.SetStringSelection(label)
        self.config['dtc_config'] = config
        if update:
            self.onUpdate()

    def onClearMultiColumn(self, event=None):
        self.config['multicol_config'] = {}
        self.info_message.SetLabel(f" cleared reading of multiple columns")
        self.multi_clear.Disable()
        self.yarr1.Enable()
        self.ypop.Enable()
        self.yop.Enable()
        self.onUpdate()


    def onMultiColumn(self, event=None):
        self.show_subframe('multicol', MultiColumnFrame,
                           config=self.config['multicol_config'],
                           group=self.workgroup,
                           on_ok=self.onMultiColumn_OK)


    def onMultiColumn_OK(self, config, update=True, **kws):
        chans = config.get('channels', [])
        if len(chans) == 0:
            self.config['multicol_config'] = {}
        else:
            self.config['multicol_config'] = config
            self.yarr1.SetSelection(chans[0])
            self.yarr2.SetSelection(config['i0'])
            self.ypop.SetStringSelection('')
            self.yarr1.Disable()
            self.ypop.Disable()
            self.yop.Disable()
            y2 = self.yarr2.GetStringSelection()
            msg = f"  Will import {len(config['channels'])} Y arrays, divided by '{y2}'"
            self.info_message.SetLabel(msg)
            self.multi_clear.Enable()
        if update:
            self.onUpdate()


    def read_column_file(self, path):
        """read column file, generally as initial read"""
        path = Path(path).absolute()
        filename = path.name
        path = path.as_posix()
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
        self.read_form()
        cout = create_arrays(self.workgroup, **self.config)
        self.config.update(cout)
        conf = self.config
        if self.ypop.Enabled:  #not using multicolumn mode
            conf['multicol_config'] = {'channels': [], 'i0': conf['iy2']}

        self.expressions = conf['expressions']
        filename = conf['filename']
        groupname = conf['groupname']

        conf['array_labels'] = self.workgroup.array_labels

        # generate script to pass back to calling program:
        labstr = ', '.join(self.array_labels)
        buff = [f"{{group}} = {self.reader}('{{path}}', labels='{labstr}')",
                "{group}.path = '{path}'",
                "{group}.is_frozen = False",
                "{group}.energy_ref = '{group}'"]

        dtc_conf = conf.get('dtc_config', {})
        if len(dtc_conf) > 0:
            sumcmd = "sum_fluor_channels({{group}}, {roi}, icr={icr}, ocr={ocr}, ltime={ltime})"
            buff.append(sumcmd.format(**dtc_conf))

        buff.append("{group}.datatype = '%s'" % (conf['datatype']))

        for attr in ('plot_xlabel', 'plot_ylabel'):
            val = getattr(self.workgroup, attr)
            buff.append("{group}.%s = '%s'" % (attr, val))

        xexpr = self.expressions['xplot']
        en_units = conf['en_units']
        if en_units.startswith('deg'):
            monod = conf['monod']
            buff.append(f"monod = {monod:.9f}")
            buff.append(f"{{group}}.xplot = PLANCK_HC/(2*monod*sin(DEG2RAD*({xexpr:s})))")
        elif en_units.startswith('keV'):
            buff.append(f"{{group}}.xplot = 1000.0*{xexpr:s}")
        else:
            buff.append(f"{{group}}.xplot = {xexpr:s}")

        for aname in ('yplot', 'yerr'):
            expr = self.expressions[aname]
            buff.append(f"{{group}}.{aname} = {expr}")


        dtype = getattr(self.workgroup, 'datatype', 'xytype')
        if dtype == 'xas':
            if self.reader == 'read_gsescan':
                buff.append("{group}.xplot = {group}.x")
            buff.append("{group}.energy = {group}.xplot[:]")
            buff.append("{group}.mu = {group}.yplot[:]")
            buff.append("sort_xafs({group}, overwrite=True, fix_repeats=True)")
        elif dtype == 'xydata':
            buff.append("{group}.x = {group}.xplot[:]")
            buff.append("{group}.y = {group}.yplot[:]")
            buff.append("{group}.scale = (ptp({group}.yplot)+1.e-15)")
            buff.append("{group}.xshift = 0.0")

        array_desc = dict(xplot=self.workgroup.plot_xlabel,
                          yplot=self.workgroup.plot_ylabel,
                          yerr=self.expressions['yerr'])

        reffile = refgroup = None
        if conf['has_yref']:
            reffile = conf['reffile']
            refgroup = conf['refgroup']
            refexpr = self.expressions['yref']
            array_desc['yref'] = getattr(self.workgroup, 'yrlabel', 'reference')

            buff.append("# reference group")
            buff.append("{refgroup} = deepcopy({group})")
            buff.append(f"{{refgroup}}.yplot = {{refgroup}}.mu = {refexpr}")
            buff.append(f"{{refgroup}}.plot_ylabel = '{self.workgroup.yrlabel}'")
            buff.append("{refgroup}.energy_ref = {group}.energy_ref = '{refgroup}'")
            buff.append("# end reference group")

        script = "\n".join(buff)
        conf['array_desc'] = array_desc

        if self.read_ok_cb is not None:
            self.read_ok_cb(script, self.path, conf)

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
        # self.onUpdate()

    def onTransCheck(self, evt=None, is_trans=False):
        if evt is not None:
            is_trans = evt.IsChecked()
        if is_trans:
            self.ypop.SetStringSelection('-log(')
        else:
            self.ypop.SetStringSelection('')
        try:
            self.onUpdate()
        except:
            pass

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
        ncol, npts = self.workgroup.data.shape
        if xname.startswith('_index') or ix >= ncol:
            workgroup.xplot = 1.0*np.arange(npts)
        else:
            workgroup.xplot = 1.0*self.workgroup.data[ix, :]
        self.onUpdate()

        self.monod_val.Disable()
        if self.datatype.GetStringSelection().strip().lower() == 'xydata':
            self.en_units.SetSelection(4)
        else:
            eguess = guess_energy_units(workgroup.xplot)
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
        workgroup = self.workgroup
        try:
            ncol, npts = workgroup.data.shape
        except (AttributeError,  ValueError):
            return

        if xname.startswith('_index') or ix >= ncol:
            workgroup.xplot = 1.0*np.arange(npts)
        else:
            workgroup.xplot = 1.0*self.workgroup.data[ix, :]
        if self.datatype.GetStringSelection().strip().lower() != 'xydata':
            eguess =  guess_energy_units(workgroup.xplot)
            if eguess.startswith('eV'):
                self.en_units.SetStringSelection('eV')
            elif eguess.startswith('keV'):
                self.en_units.SetStringSelection('keV')

    def read_form(self, **kws):
        """return form configuration"""
        datatype = self.datatype.GetStringSelection().strip().lower()
        if self.workgroup.datatype == 'xydata' and datatype == 'xas':
            self.workgroup.datatype = 'xas'
            eguess = guess_energy_units(self.workgroup.xplot)
            if eguess.startswith('keV'):
                self.en_units.SetSelection(1)
            elif eguess.startswith('deg'):
                self.en_units.SetSelection(2)
                self.monod_val.Enable()
            else:
                self.en_units.SetSelection(0)
        if datatype == 'xydata':
            self.en_units.SetStringSelection('not energy')

        ypop = self.ypop.GetStringSelection().strip()
        self.is_trans.SetValue('log' in ypop)


        conf = {'datatype': datatype,
                'ix':  self.xarr.GetSelection(),
                'xarr': self.xarr.GetStringSelection(),
                'en_units': self.en_units.GetStringSelection(),
                'monod': float(self.monod_val.GetValue()),
                'yarr1': self.yarr1.GetStringSelection().strip(),
                'yarr2': self.yarr2.GetStringSelection().strip(),
                'iy1': self.yarr1.GetSelection(),
                'iy2': self.yarr2.GetSelection(),
                'yop': self.yop.GetStringSelection().strip(),
                'ypop': ypop,
                'iyerr': self.yerr_arr.GetSelection(),
                'yerr_arr': self.yerr_arr.GetStringSelection(),
                'yerr_op': self.yerr_op.GetStringSelection().lower(),
                'yerr_val': self.yerr_val.GetValue(),
                'has_yref': self.has_yref.IsChecked(),
                'yref1': self.yref1.GetStringSelection().strip(),
                'yref2': self.yref2.GetStringSelection().strip(),
                'iry1': self.yref1.GetSelection(),
                'iry2': self.yref2.GetSelection(),
                'yrpop': self.yrpop.GetStringSelection().strip(),
                'yrop': self.yop.GetStringSelection().strip(),
                'filename': self.wid_filename.GetValue(),
                'groupname': fix_varname(self.wid_groupname.GetValue()),
                'reffile': self.wid_reffilename.GetValue(),
                'refgroup': fix_varname(self.wid_refgroupname.GetValue()),
                }
        self.config.update(conf)
        return conf

    def onUpdate(self, evt=None, **kws):
        """column selections changed calc xplot and yplot"""
        workgroup = self.workgroup
        try:
            ncol, npts = self.workgroup.data.shape
        except:
            return

        conf = self.read_form()
        cout = create_arrays(workgroup, **conf)
        self.expressions = cout.pop('expressions')
        conf.update(cout)

        if energy_may_need_rebinning(workgroup):
            self.info_message.SetLabel("Warning: XAS data may need to be rebinned!")

        fname = Path(workgroup.filename).name
        popts = dict(marker='o', markersize=4, linewidth=1.5, title=fname,
                     xlabel=workgroup.plot_xlabel,
                     ylabel=workgroup.plot_ylabel,
                     label=workgroup.plot_ylabel)

        self.plotpanel.plot(workgroup.xplot, workgroup.yplot, **popts)
        if conf['has_yref']:
            yrlabel = getattr(workgroup, 'plot_yrlabel', 'reference')
            self.plotpanel.oplot(workgroup.xplot, workgroup.yref,
                                 y2label=yrlabel,
                                 linewidth=2.0, color='#E08070',
                                 label=yrlabel, zorder=-40, side='right')

        for i in range(self.nb.GetPageCount()):
            if 'plot' in self.nb.GetPageText(i).lower():
                self.nb.SetSelection(i)

    def plot_messages(self, msg, panel=1):
        self.statusbar.SetStatusText(msg, panel)


def create_arrays(dgroup, datatype='xas', ix=0, xarr='energy', en_units='eV',
                  monod=3.1355316, yarr1=None, yarr2=None, iy1=2, iy2=1, yop='/',
                  ypop='', iyerr=5, yerr_arr=None, yerr_op='constant', yerr_val=1.0,
                  has_yref=False, yref1=None, yref2=None, iry1=3, iry2=2,
                  yrpop='', yrop='/', **kws):
    """
    build arrays and values for datagroup based on configuration as from ColumnFile
    """
    ncol, npts = dgroup.data.shape
    exprs = dict(xplot=None, yplot=None, yerr=None, yref=None)

    if not hasattr(dgroup, 'index'):
        dgroup.index = 1.0*np.arange(npts)

    if xarr.startswith('_index') or ix >= ncol:
        dgroup.xplot = 1.0*np.arange(npts)
        xarr = '_index'
        exprs['xplot'] = 'arange({npts})'
    else:
        dgroup.xplot = 1.0*dgroup.data[ix, :]
        exprs['xplot'] = '{group}.data[{ix}, : ]'

    xlabel = xarr
    monod = float(monod)
    if en_units.startswith('deg'):
        dgroup.xplot = PLANCK_HC/(2*monod*np.sin(DEG2RAD*dgroup.xplot))
        xlabel = xarr + ' (eV)'
    elif en_units.startswith('keV'):
        dgroup.xplot *= 1000.0
        xlabel = xarr + ' (eV)'

    def pre_op(opstr, arr):
        if opstr == '-':
            return '', opstr, -arr
        suf = ''
        if opstr in ('-log(', 'log('):
            suf = ')'
            arr = safe_log(arr)
            if opstr.startswith('-'): arr = -arr
            arr[np.where(np.isnan(arr))] = 0
        return suf, opstr, arr

    if yarr1 is None:
        yarr1 = dgroup.array_labels[iy1]

    if yarr2 is None:
        yarr2 = dgroup.array_labels[iy2]

    ylabel = yarr1
    if len(yarr2) == 0:
        yarr2 = '1.0'
    else:
        ylabel = f"{ylabel}{yop}{yarr2}"

    if yarr1 == '0.0':
        ydarr1 = np.zeros(npts)*1.0
        yexpr1 = f'np.zeros(npts)'
    elif len(yarr1) == 0 or yarr1 == '1.0' or iy1 >= ncol:
        ydarr1 = np.ones(npts)*1.0
        yexpr1 = f'np.ones({npts})'
    else:
        ydarr1 = dgroup.data[iy1, :]
        yexpr1 = '{group}.data[{iy1}, : ]'

    dgroup.yplot = ydarr1
    exprs['yplot'] = yexpr1

    if yarr2 == '0.0':
        ydarr2 = np.zeros(npts)*1.0
        yexpr2 = '0.0'
    elif len(yarr2) == 0 or yarr2 == '1.0' or iy2 >= ncol:
        ydarr2 = np.ones(npts)*1.0
        yexpr2 = '1.0'
    else:
        ydarr2 = dgroup.data[iy2, :]
        yexpr2 = '{group}.data[{iy2}, : ]'

    if yop in ('+', '-', '*', '/'):
        exprs['yplot'] = f"{yexpr1}{yop}{yexpr2}"
        if yop == '+':
            dgroup.yplot = ydarr1 + ydarr2
        elif yop == '-':
            dgroup.yplot = ydarr1 - ydarr2
        elif yop == '*':
            dgroup.yplot = ydarr1 * ydarr2
        elif yop == '/':
            dgroup.yplot = ydarr1 / ydarr2

    ysuf, ypop, dgroup.yplot = pre_op(ypop, dgroup.yplot)
    ypopx = ypop.replace('log', 'safe_log')
    exprs['yplot'] = f"{ypopx}{exprs['yplot']}{ysuf}"
    ylabel = f"{ypop}{ylabel}{ysuf}"

    # error
    exprs['yerr'] = '1'
    if yerr_op.startswith('const'):
        yderr = yerr_val
        exprs['yerr'] = f"{yerr_val}"
    elif yerr_op.startswith('array'):
        yderr = dgroup.data[iyerr, :]
        exprs['yerr'] = '{group}.data[{iyerr}, :]'
    elif yerr_op.startswith('sqrt'):
        yderr = np.sqrt(dgroup.yplot)
        exprs['yerr'] = 'sqrt({group}.yplot)'

    # reference
    yrlabel = None
    if has_yref:
        yrlabel = yref1
        if len(yref2) == 0:
            yref2 = '1.0'
        else:
            yrlabel = f"{yrlabel}{yrop}{yref2}"

        if yref1 == '0.0':
            ydrarr1 = np.zeros(npts)*1.0
            yrexpr1 = 'zeros({npts})'
        elif len(yref1) == 0 or yref1 == '1.0' or iry1 >= ncol:
            ydrarr1 = np.ones(npts)*1.0
            yrexpr1 = 'ones({npts})'
        else:
            ydrarr1 = dgroup.data[iry1, :]
            yrexpr1 = '{group}.data[{iry1}, : ]'

        dgroup.yref = ydrarr1
        exprs['yref'] = yrexpr1

        if yref2 == '0.0':
            ydrarr2 = np.zeros(npts)*1.0
            ydrexpr2 = '0.0'
        elif len(yref2) == 0 or yref2 == '1.0' or iry2 >= ncol:
            ydrarr2 = np.ones(npts)*1.0
            yrexpr2 = '1.0'
        else:
            ydrarr2 = dgroup.data[iry2, :]
            yrexpr2 = '{group}.data[{iry2}, : ]'

        if yrop in ('+', '-', '*', '/'):
            exprs['yref'] = f'{yrexpr1} {yop} {yrexpr2}'
            if yrop == '+':
                dgroup.yref = ydrarr1 + ydrarr2
            elif yrop == '-':
                dgroup.yref = ydrarr1 - ydrarr2
            elif yrop == '*':
                dgroup.yref = ydrarr1 * ydarr2
            elif yrop == '/':
                dgroup.yref = ydrarr1 / ydrarr2

        yrsuf, yprop, dgroup.yref = pre_op(yrpop, dgroup.yref)
        yrpopx = yrpop.replace('log', 'safe_log')
        exprs['yref'] = f"{yrpopx}{exprs['yref']}{yrsuf}"
        yrlabel = f'{yrpop} {yrlabel} {yrsuf}'
        dgroup.yrlabel = yrlabel


    try:
        npts = min(len(dgroup.xplot), len(dgroup.yplot))
    except AttributeError:
        return
    except ValueError:
        return

    en = dgroup.xplot
    dgroup.datatype    = datatype
    dgroup.npts        = npts
    dgroup.plot_xlabel = xlabel
    dgroup.plot_ylabel = ylabel
    dgroup.xplot       = np.array(dgroup.xplot[:npts])
    dgroup.yplot       = np.array(dgroup.yplot[:npts])
    dgroup.y           = dgroup.yplot
    dgroup.yerr        = yderr
    if isinstance(yderr, np.ndarray):
        dgroup.yerr    = np.array(yderr[:npts])
    if yrlabel is not None:
        dgroup.plot_yrlabel = yrlabel

    if dgroup.datatype == 'xas':
        dgroup.energy = dgroup.xplot
        dgroup.mu     = dgroup.yplot

    return dict(xarr=xarr, ypop=ypop, yop=yop, yarr1=yarr1, yarr2=yarr2,
                monod=monod, en_units=en_units, yerr_op=yerr_op,
                yerr_val=yerr_val, yerr_arr=yerr_arr, yrpop=yrpop, yrop=yrop,
                yref1=yref1, yref2=yref2, has_yref=has_yref,
                expressions=exprs)

def energy_may_need_rebinning(workgroup):
    "test if energy may need rebinning"
    if getattr(workgroup, 'datatype', '?') != 'xas':
        return False
    en = getattr(workgroup, 'xplot', [-8.0e12])
    if len(en) < 2:
        return False
    if not isinstance(en, np.ndarray):
        en = np.array(en)
    if len(en) > 2000 or any(np.diff(en))< 0:
        return True
    if (len(en) > 200 and (max(en) - min(en)) > 350 and
        np.diff(en[:-100]).mean() < 1.0):
        return True
