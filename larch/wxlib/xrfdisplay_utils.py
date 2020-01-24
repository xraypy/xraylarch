#!/usr/bin/env python
"""
utilities for XRF display
"""
import copy
from functools import partial
from collections import OrderedDict
import time
import numpy as np

import wx
import wx.lib.colourselect  as csel
import wx.lib.scrolledpanel as scrolled
from wxutils import (SimpleText, FloatCtrl, Choice, Font, pack, Button,
                     Check, HyperText, HLine, GridPanel, CEN, LEFT, RIGHT)

from wxmplot.colors import hexcolor
from xraydb import xray_line
from ..xrf import (xrf_calib_fitrois, xrf_calib_init_roi,
                   xrf_calib_compute, xrf_calib_apply)

# Group used to hold MCA data
XRFGROUP   = '_xrfdata'
MAKE_XRFGROUP_CMD = "%s = group(__doc__='MCA/XRF data groups', _mca='', _mca2='')" % XRFGROUP
XRFRESULTS_GROUP   = '_xrfresults'
MAKE_XRFRESULTS_GROUP = "_xrfresults = []"

def mcaname(i):
    return "mca{:03d}".format(i)

def next_mcaname(_larch):
    xrfgroup = _larch.symtable.get_group(XRFGROUP)
    i, exists = 1, True
    name = "mca{:03d}".format(i)
    while hasattr(xrfgroup, name):
        i += 1
        name = "mca{:03d}".format(i)
    return name


class XRFCalibrationFrame(wx.Frame):
    def __init__(self, parent, mca, size=(-1, -1), callback=None):
        self.mca = mca
        self.callback = callback
        wx.Frame.__init__(self, parent, -1, 'Calibrate MCA',
                          size=size, style=wx.DEFAULT_FRAME_STYLE)

        opanel = scrolled.ScrolledPanel(self)
        osizer = wx.BoxSizer(wx.VERTICAL)
        panel = GridPanel(opanel)
        self.calib_updated = False
        panel.AddText("Calibrate MCA Energy (Energies in eV)",
                      colour='#880000', dcol=7)
        panel.AddText("ROI", newrow=True, style=CEN)
        panel.AddText("Predicted", style=CEN)
        panel.AddText("Peaks with Current Calibration", dcol=3, style=CEN)
        panel.AddText("Peaks with Refined Calibration", dcol=3, style=CEN)

        panel.AddText("Name", newrow=True, style=CEN)
        panel.AddText("Energy", style=CEN)
        panel.AddText("Center", style=CEN)
        panel.AddText("Difference", style=CEN)
        panel.AddText("FWHM", style=CEN)
        panel.AddText("Center", style=CEN)
        panel.AddText("Difference", style=CEN)
        panel.AddText("FWHM", style=CEN)
        panel.AddText("Use? ", style=CEN)

        panel.Add(HLine(panel, size=(700, 3)),  dcol=9, newrow=True)
        self.wids = []

        # find ROI peak positions
        self.init_wids = {}
        for roi in self.mca.rois:
            eknown, ecen, fwhm = 1, 1, 1

            words = roi.name.split()
            elem = words[0].title()
            family = 'ka'
            if len(words) > 1:
                family = words[1]
            try:
                eknown = xray_line(elem, family).energy/1000.0
            except (AttributeError, ValueError):
                eknown = 0.0001
            mid = (roi.right + roi.left)/2
            wid = (roi.right - roi.left)/2
            ecen = mid * mca.slope + mca.offset
            fwhm = 2.354820 * wid * mca.slope

            diff = ecen - eknown
            name = ('   ' + roi.name+' '*10)[:10]
            opts = {'style': CEN, 'size':(75, -1)}
            w_name = SimpleText(panel, name,   **opts)
            w_pred = SimpleText(panel, "% .1f" % (1000*eknown), **opts)
            w_ccen = SimpleText(panel, "% .1f" % (1000*ecen),   **opts)
            w_cdif = SimpleText(panel, "% .1f" % (1000*diff),   **opts)
            w_cwid = SimpleText(panel, "% .1f" % (1000*fwhm),   **opts)
            w_ncen = SimpleText(panel, "-----",         **opts)
            w_ndif = SimpleText(panel, "-----",         **opts)
            w_nwid = SimpleText(panel, "-----",         **opts)
            w_use  = Check(panel, label='', size=(40, -1), default=0)
            panel.Add(w_name, style=LEFT, newrow=True)
            panel.AddMany((w_pred, w_ccen, w_cdif, w_cwid,
                           w_ncen, w_ndif, w_nwid, w_use))
            self.init_wids[roi.name] = [False, w_pred, w_ccen, w_cdif, w_cwid, w_use]
            self.wids.append((roi.name, eknown, ecen, w_ncen, w_ndif, w_nwid, w_use))

        panel.Add(HLine(panel, size=(700, 3)),  dcol=9, newrow=True)
        offset = 1000.0*self.mca.offset
        slope  = 1000.0*self.mca.slope
        panel.AddText("Current Calibration:",   dcol=2, newrow=True)
        panel.AddText("offset(eV):")
        panel.AddText("%.3f" % (offset), dcol=1, style=RIGHT)
        panel.AddText("slope(eV/chan):")
        panel.AddText("%.3f" % (slope),  dcol=1, style=RIGHT)

        panel.AddText("Refined Calibration:", dcol=2, newrow=True)
        self.new_offset = FloatCtrl(panel, value=offset, precision=3,
                                   size=(80, -1))
        self.new_slope = FloatCtrl(panel, value=slope,  precision=3,
                                   size=(80, -1))
        panel.AddText("offset(eV):")
        panel.Add(self.new_offset,    dcol=1, style=RIGHT)
        panel.AddText("slope(eV/chan):")
        panel.Add(self.new_slope,     dcol=1, style=RIGHT)

        self.calib_btn = Button(panel, 'Compute Calibration',
                                size=(175, -1), action=self.onCalibrate)
        self.calib_btn.Disable()
        panel.Add(self.calib_btn, dcol=3, newrow=True)
        panel.Add(Button(panel, 'Use New Calibration',
                         size=(175, -1), action=self.onUseCalib),
                  dcol=3, style=RIGHT)
        panel.Add(Button(panel, 'Done',
                         size=(125, -1), action=self.onClose),
                  dcol=2, style=RIGHT)
        panel.pack()
        a = panel.GetBestSize()
        self.SetSize((a[0]+25, a[1]+50))
        osizer.Add(panel)
        pack(opanel, osizer)
        opanel.SetupScrolling()
        self.Show()
        self.Raise()
        self.init_proc = False
        self.init_t0 = time.time()
        self.init_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onInitTimer, self.init_timer)
        self.init_timer.Start(2)

    def onInitTimer(self, evt=None):
        """initial calibration"""
        if self.init_proc:
            # print("skipping in init_proc...")
            return
        nextroi = None
        if time.time() - self.init_t0 > 20:
            self.init_timer.Stop()
            self.init_proc = False
            self.calib_btn.Enable()
        for roiname, wids in self.init_wids.items():
            if not wids[0]:
                nextroi = roiname
                break

        if nextroi is None:
            self.init_timer.Stop()
            self.init_proc = False
            self.calib_btn.Enable()
        else:
            self.init_proc = True
            xrf_calib_init_roi(self.mca, roiname)
            s, w_pred, w_ccen, w_cdif, w_cwid, w_use = self.init_wids[roiname]
            if roiname in self.mca.init_calib:
                eknown, ecen, fwhm, amp, fit = self.mca.init_calib[roiname]

                diff = ecen - eknown
                opts = {'style': CEN, 'size':(75, -1)}
                w_pred.SetLabel("% .1f" % (1000*eknown))
                w_ccen.SetLabel("% .1f" % (1000*ecen))
                w_cdif.SetLabel("% .1f" % (1000*diff))
                w_cwid.SetLabel("% .1f" % (1000*fwhm))
                if fwhm > 0.001 and fwhm < 2.00 and fit is not None:
                    w_use.SetValue(1)

            self.init_wids[roiname][0] = True
            self.init_proc = False


    def onCalibrate(self, event=None):
        x, y = [], []
        mca = self.mca
        # save old calib
        old_calib  =  mca.offset, mca.slope
        init_calib =  copy.deepcopy(mca.init_calib)
        for roiname, eknown, ecen, w_ncen, w_ndif, w_nwid, w_use in self.wids:
            if not w_use.IsChecked():
                mca.init_calib.pop(roiname)
            w_ncen.SetLabel("-----")
            w_ndif.SetLabel("-----")
            w_nwid.SetLabel("-----")


        xrf_calib_compute(mca, apply=True)
        offset, slope = mca.new_calib
        self.calib_updated = True
        self.new_offset.SetValue("% .3f" % (1000*offset))
        self.new_slope.SetValue("% .3f" % (1000*slope))

        # find ROI peak positions using this new calibration
        xrf_calib_fitrois(mca)
        for roi in self.mca.rois:
            try:
                eknown, ecen, fwhm, amp, fit = mca.init_calib[roi.name]
            except:
                continue
            diff  = ecen - eknown
            for roiname, eknown, ocen, w_ncen, w_ndif, w_nwid, w_use in self.wids:
                if roiname == roi.name and w_use.IsChecked():
                    w_ncen.SetLabel("%.1f" % (1000*ecen))
                    w_ndif.SetLabel("% .1f" % (1000*diff))
                    w_nwid.SetLabel("%.1f" % (1000*fwhm))
                    break


        # restore calibration to old values until new values are accepted
        xrf_calib_apply(mca, offset=old_calib[0], slope=old_calib[1])
        mca.init_calib = init_calib

        tsize = self.GetSize()
        self.SetSize((tsize[0]+1, tsize[1]))
        self.SetSize((tsize[0], tsize[1]))

    def onUseCalib(self, event=None):
        mca = self.mca
        offset = 0.001*float(self.new_offset.GetValue())
        slope  = 0.001*float(self.new_slope.GetValue())
        mca.new_calib = offset, slope
        xrf_calib_apply(mca, offset=offset, slope=slope)
        if callable(self.callback):
            self.callback(mca)
        self.Destroy()

    def onClose(self, event=None):
        self.Destroy()


class ColorsFrame(wx.Frame):
    """settings frame for XRFDisplay"""
    def __init__(self, parent, size=(400, 300), **kws):
        self.parent = parent
        conf = parent.conf
        kws['style'] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, parent, -1, size=size,
                          title='XRF Color Settings', **kws)

        panel = GridPanel(self)
        panel.SetFont(Font(11))
        def add_color(panel, name):
            cval = hexcolor(getattr(conf, name))
            c = csel.ColourSelect(panel,  -1, "", cval, size=(35, 25))
            c.Bind(csel.EVT_COLOURSELECT, partial(self.onColor, item=name))
            return c

        def scolor(txt, attr, **kws):
            panel.AddText(txt, size=(130, -1), style=LEFT, font=Font(11), **kws)
            panel.Add(add_color(panel, attr),  style=LEFT)

        panel.AddText('    XRF Display Colors', dcol=4, colour='#880000')
        panel.Add(HLine(panel, size=(400, 3)),  dcol=4, newrow=True)
        scolor(' Main Spectra:',        'spectra_color', newrow=True)
        scolor(' Background Spectra:',      'spectra2_color')
        scolor(' ROIs:',                'roi_color',     newrow=True)
        scolor(' ROI Fill:',            'roi_fillcolor')
        scolor(' Cursor:',              'marker_color',  newrow=True)
        scolor(' XRF Background:',      'bgr_color')
        scolor(' Major X-ray Lines:',   'major_elinecolor', newrow=True)
        scolor(' Minor X-ray Lines:',   'minor_elinecolor')
        scolor(' Selected X-ray Line:', 'emph_elinecolor', newrow=True)
        scolor(' Held  X-ray Lines:',   'hold_elinecolor')
        scolor(' Pileup Prediction:',   'pileup_color', newrow=True)
        scolor(' Escape Prediction:',   'escape_color')

        panel.Add(HLine(panel, size=(400, 3)),  dcol=4, newrow=True)
        panel.Add(Button(panel, 'Done', size=(80, -1), action=self.onDone),
                  dcol=2, newrow=True)

        panel.pack()
        self.SetMinSize(panel.GetBestSize())
        self.Show()
        self.Raise()

    def onColor(self, event=None, item=None):
        color = hexcolor(event.GetValue())
        setattr(self.parent.conf, item, color)
        if item == 'spectra_color':
            self.parent.panel.conf.set_trace_color(color, trace=0)
        elif item == 'roi_color':
            self.parent.panel.conf.set_trace_color(color, trace=1)
        elif item == 'marker_color':
            for lmark in self.parent.cursor_markers:
                if lmark is not None:
                    lmark.set_color(color)

        elif item == 'roi_fillcolor' and self.parent.roi_patch is not None:
            self.parent.roi_patch.set_color(color)
        elif item == 'major_elinecolor':
            for l in self.parent.major_markers:
                l.set_color(color)
        elif item == 'minor_elinecolor':
            for l in self.parent.minor_markers:
                l.set_color(color)
        elif item == 'hold_elinecolor':
            for l in self.parent.hold_markers:
                l.set_color(color)

        self.parent.panel.canvas.draw()
        self.parent.panel.Refresh()

    def onDone(self, event=None):
        self.Destroy()

class XrayLinesFrame(wx.Frame):
    """settings frame for XRFDisplay"""

    k1lines = ['Ka1', 'Ka2', 'Kb1']
    k2lines = ['Kb2', 'Kb3']
    l1lines = ['La1', 'Lb1', 'Lb3', 'Lb4']
    l2lines = ['La2', 'Ll', 'Ln', 'Lb2,15']
    l3lines = ['Lg1', 'Lg2', 'Lg3']
    mlines  = ['Ma', 'Mb', 'Mg', 'Mz']

    def __init__(self, parent, size=(475, 325), **kws):
        self.parent = parent
        conf  = parent.conf
        kws['style'] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, parent, -1, size=size,
                          title='XRF Line Selection', **kws)
        panel = GridPanel(self)
        self.checkbox = {}
        def add_elines(panel, lines, checked):
            for i in lines:
                cb = Check(panel, '%s ' % i, default = i in checked,
                           action=partial(self.onLine, label=i, lines=checked))
                self.checkbox[i] = cb
                panel.Add(cb, style=LEFT)

        hopts = {'size': (125, -1), 'bgcolour': (250, 250, 200)}
        labopts = {'newrow': True, 'style': LEFT}
        self.linedata = {'Major K Lines:': self.k1lines,
                         'Minor K Lines:': self.k2lines,
                         'Major L Lines:': self.l1lines,
                         'Minor L Lines:': self.l2lines+self.l3lines,
                         'Major M Lines:': self.mlines}
        panel.AddText(' Select X-ray Emission Lines', dcol=4, colour='#880000')
        panel.Add(HLine(panel, size=(450, 3)),  dcol=5, newrow=True)

        panel.Add(HyperText(panel, 'Major K Lines:',
                            action=partial(self.ToggleLines, lines=conf.K_major),
                            **hopts), **labopts)
        add_elines(panel, self.k1lines, conf.K_major)

        panel.Add(HyperText(panel, 'Minor K Lines:',
                            action=partial(self.ToggleLines, lines=conf.K_minor),
                            **hopts), **labopts)
        add_elines(panel, self.k2lines, conf.K_minor)

        panel.Add(HyperText(panel, 'Major L Lines:',
                            action=partial(self.ToggleLines, lines=conf.L_major),
                            **hopts), **labopts)
        add_elines(panel, self.l1lines, conf.L_major)

        panel.Add(HyperText(panel, 'Minor L Lines:',
                            action=partial(self.ToggleLines, lines=conf.L_minor),
                            **hopts), **labopts)
        add_elines(panel, self.l2lines, conf.L_minor)

        panel.AddText(' ', **labopts)
        add_elines(panel, self.l3lines, conf.L_minor)

        panel.Add(HyperText(panel, 'Major M Lines:',
                            action=partial(self.ToggleLines, lines=conf.M_major),
                            **hopts), **labopts)
        add_elines(panel, self.mlines,  conf.M_major)

        panel.AddText('Energy Range (keV): ', **labopts)
        fopts = {'minval':0, 'maxval':1000, 'precision':2, 'size':(75, -1)}
        panel.Add(FloatCtrl(panel, value=conf.e_min,
                            action=partial(self.onErange, is_max=False),
                            **fopts),  dcol=2, style=LEFT)

        panel.AddText(' : ')
        panel.Add(FloatCtrl(panel, value=conf.e_max,
                            action=partial(self.onErange, is_max=True),
                            **fopts), dcol=2, style=LEFT)

        panel.Add(HLine(panel, size=(450, 3)),  dcol=5, newrow=True)
        panel.Add(Button(panel, 'Done', size=(80, -1), action=self.onDone),
                  newrow=True, style=LEFT)
        panel.pack()
        self.Show()
        self.Raise()

    def ToggleLines(self, label=None, event=None, lines=None, **kws):
        if not event.leftIsDown:
            self.parent.Freeze()
            for line in self.linedata.get(label, []):
                check = not self.checkbox[line].IsChecked()
                self.checkbox[line].SetValue({True: 1, False:0}[check])
                self.onLine(checked=check, label=line, lines=lines)
            self.parent.Thaw()

    def onLine(self, event=None, checked=None, label=None, lines=None):
        if checked is None:
            try:
                checked =event.IsChecked()
            except:
                pass
        if checked is None: checked = False
        if lines is None:
            lines = []

        if label in lines and not checked:
            lines.remove(label)
        elif label not in lines and checked:
            lines.append(label)
        if self.parent.selected_elem is not None:
            self.parent.onShowLines(elem=self.parent.selected_elem)

    def onErange(self, event=None, value=None, is_max=True):
        if value is None:   return

        val = float(value)
        if is_max:
            self.parent.conf.e_max = val
        else:
            self.parent.conf.e_min = val
        if self.parent.selected_elem is not None:
            self.parent.onShowLines(elem=self.parent.selected_elem)


    def onDone(self, event=None):
        self.Destroy()

class XRFDisplayConfig:
    emph_elinecolor  = '#444444'
    major_elinecolor = '#DAD8CA'
    minor_elinecolor = '#F4DAC0'
    hold_elinecolor  = '#CAC8DA'
    marker_color     = '#77BB99'
    roi_fillcolor    = '#F8F0BA'
    roi_color        = '#d62728'
    spectra_color    = '#1f77b4'
    spectra2_color   = '#2ca02c'
    bgr_color        = '#ff7f0e'
    fit_color        = '#d62728'
    pileup_color     = '#555555'
    escape_color     = '#F07030'

    K_major = ['Ka1', 'Ka2', 'Kb1']
    K_minor = ['Kb3', 'Kb2']
    K_minor = []
    L_major = ['La1', 'Lb1', 'Lb3', 'Lb4']
    L_minor = ['Ln', 'Ll', 'Lb2,15', 'Lg2', 'Lg3', 'Lg1', 'La2']
    L_minor = []
    M_major = ['Ma', 'Mb', 'Mg', 'Mz']
    e_min   = 1.00
    e_max   = 30.0


class ROI_Averager():
    """ROI averager (over a fixed number of event samples)
       to give a rolling average of 'recent ROI values'

       roi_buff = ROI_Averager('13SDD1:mca1.R12',  nsamples=11)
       while True:
            print( roi_buff.average())

       typically, the ROIs update at a fixed 10 Hz, so 11 samples
       gives the ROI intensity integrated over the previous second

       using a ring buffer using numpy arrays
    """
    def __init__(self, nsamples=11):
        self.clear(nsamples = nsamples)

    def clear(self, nsamples=11):
        self.nsamples = nsamples
        self.index = -1
        self.lastval = 0
        self.toffset = time.time()
        self.data  =  np.zeros(self.nsamples, dtype=np.float32)
        self.times = -np.ones(self.nsamples, dtype=np.float32)

    def append(self, value):
        "adds value to ring buffer"
        idx = self.index = (self.index + 1) % self.data.size
        self.data[idx] = max(0, value - self.lastval)
        self.lastval  = value
        dt = time.time() - self.toffset
        # avoid first time point
        if (idx == 0 and max(self.times) < 0):
            dt = 0
        self.times[idx] =  dt

    def update(self, value):
        self.append(value)

    def get_mean(self):
        valid = np.where(self.times > 0)[0]
        return self.data[valid].mean()

    def get_cps(self):
        valid = np.where(self.times > 0)[0]
        if len(valid) < 1 or  self.times[valid].ptp() < 0.5:
            return 0
        return self.data[valid].sum() / self.times[valid].ptp()
