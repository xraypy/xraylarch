#!/usr/bin/env python
"""
utilities for XRF display
"""
import copy
from functools import partial

import wx
import wx.lib.colourselect  as csel

from wxutils import (SimpleText, FloatCtrl, Choice, Font, pack, Button,
                     Check, HLine, GridPanel, CEN, LEFT, RIGHT)

from wxmplot.colors import hexcolor

import larch

larch.use_plugin_path('xrf')

from xrf_bgr import xrf_background
from xrf_calib import xrf_calib_fitrois, xrf_calib_compute, xrf_calib_apply

class CalibrationFrame(wx.Frame):
    def __init__(self, parent, mca, larch=None, size=(500, 300)):
        self.mca = mca
        self.larch = larch
        wx.Frame.__init__(self, parent, -1, 'Calibrate MCA',
                          size=size, style=wx.DEFAULT_FRAME_STYLE)

        self.SetFont(Font(8))
        panel = GridPanel(self)
        self.calib_updated = False
        panel.AddText("Calibrate MCA Energy (Energies in eV)",
                      colour='#880000', dcol=7)
        panel.AddText("ROI", newrow=True)
        panel.AddText("Predicted")
        panel.AddText("Current Energies", dcol=3, style=CEN)
        panel.AddText("Refined Energies", dcol=3, style=CEN)
        panel.AddText("Use?")

        panel.AddText("Name", newrow=True)
        panel.AddText("Energy")
        panel.AddText("Center")
        panel.AddText("Difference")
        panel.AddText("FWHM")
        panel.AddText("Center")
        panel.AddText("Difference")
        panel.AddText("FWHM")

        panel.Add(HLine(panel, size=(900, 3)),  dcol=9, newrow=True)
        self.wids = []

        # find ROI peak positions
        xrf_calib_fitrois(mca, _larch=self.larch)

        for roi in self.mca.rois:
            eknown, ecen, fwhm, amp, fit = mca.init_calib[roi.name]
            diff = ecen - eknown
            name = ('   ' + roi.name+' '*10)[:10]
            opts = {'style': CEN, 'size':(100, -1)}
            w_name = SimpleText(panel, name,   **opts)
            w_pred = SimpleText(panel, "% .1f" % (1000*eknown), **opts)
            w_ccen = SimpleText(panel, "% .1f" % (1000*ecen),   **opts)
            w_cdif = SimpleText(panel, "% .1f" % (1000*diff),   **opts)
            w_cwid = SimpleText(panel, "% .1f" % (1000*fwhm),   **opts)
            w_ncen = SimpleText(panel, "-----",         **opts)
            w_ndif = SimpleText(panel, "-----",         **opts)
            w_nwid = SimpleText(panel, "-----",         **opts)
            w_use  = Check(panel)

            panel.Add(w_name, style=LEFT, newrow=True)
            panel.AddMany((w_pred, w_ccen, w_cdif, w_cwid,
                           w_ncen, w_ndif, w_nwid, w_use))

            self.wids.append((roi.name, eknown, ecen, w_ncen, w_ndif, w_nwid, w_use))

        panel.Add(HLine(panel, size=(900, 3)),  dcol=9, newrow=True)
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

        panel.Add(Button(panel, 'Compute Calibration',
                         size=(160, -1), action=self.onCalibrate),
                  dcol=2, newrow=True)

        panel.Add(Button(panel, 'Use New Calibration',
                         size=(160, -1), action=self.onUseCalib),
                  dcol=2, style=RIGHT)

        panel.Add(Button(panel, 'Done',
                         size=(160, -1), action=self.onClose),
                  dcol=2, style=RIGHT)

        panel.pack()
        self.SetSize((950, 450))
        self.Show()
        self.Raise()

    def onCalibrate(self, event=None):
        x, y = [], []
        mca = self.mca
        # save old calib
        old_calib  =  mca.offset, mca.slope
        init_calib =  copy.deepcopy(mca.init_calib)
        for roiname, eknown, ecen, w_ncen, w_ndif, w_nwid, w_use in self.wids:
            if not w_use.IsChecked():
                mca.init_calib.pop(roiname)

        xrf_calib_compute(mca, apply=True, _larch=self.larch)
        offset, slope = mca.new_calib
        self.calib_updated = True
        self.new_offset.SetValue("% .3f" % (1000*offset))
        self.new_slope.SetValue("% .3f" % (1000*slope))

        # find ROI peak positions using this new calibration
        xrf_calib_fitrois(mca, _larch=self.larch)
        for roi in self.mca.rois:
            eknown, ecen, fwhm, amp, fit = mca.init_calib[roi.name]
            diff  = ecen - eknown
            for roiname, eknown, ocen, w_ncen, w_ndif, w_nwid, w_use in self.wids:
                if roiname == roi.name:
                    w_ncen.SetLabel("%.1f" % (1000*ecen))
                    w_ndif.SetLabel("% .1f" % (1000*diff))
                    w_nwid.SetLabel("%.1f" % (1000*fwhm))
                    break

        # restore calibration to old values until new values are accepted
        xrf_calib_apply(mca, offset=old_calib[0], slope=old_calib[1],
                        _larch=self.larch)
        mca.init_calib = init_calib

        tsize = self.GetSize()
        self.SetSize((tsize[0]+1, tsize[1]))
        self.SetSize((tsize[0], tsize[1]))

    def onUseCalib(self, event=None):
        mca = self.mca
        if hasattr(mca, 'new_calib'):
            xrf_calib_apply(mca, _larch=self.larch)
        self.Destroy()

    def onClose(self, event=None):
        self.Destroy()


class ColorsFrame(wx.Frame):
    """settings frame for XRFDisplay"""
    def __init__(self, parent, size=(500, 250), **kws):
        self.parent = parent
        conf = parent.conf
        kws['style'] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, parent, -1, size=size,
                          title='XRF Color Settings', **kws)

        panel = GridPanel(self)
        def add_color(panel, name):
            cval = hexcolor(getattr(conf, name))
            c = csel.ColourSelect(panel,  -1, "", cval, size=(35, 25))
            c.Bind(csel.EVT_COLOURSELECT, partial(self.onColor, item=name))
            return c

        SX = 180
        panel.AddText(' XRF Display Colors', dcol=4, colour='#880000')

        panel.Add(HLine(panel, size=(400, 3)),  dcol=4, newrow=True)
        panel.AddText('Spectra Color:', size=(SX, -1), style=LEFT, newrow=True)
        panel.Add(add_color(panel, 'spectra_color'),  style=LEFT)
        panel.AddText('ROI Spectra Color:', size=(SX, -1), style=LEFT)
        panel.Add(add_color(panel, 'roi_color'),  style=LEFT)

        panel.AddText('Cursor Color:', size=(SX, -1), style=LEFT, newrow=True)
        panel.Add(add_color(panel, 'marker_color'),  style=LEFT)
        panel.AddText('ROI Fill Color:', size=(SX, -1), style=LEFT)
        panel.Add(add_color(panel, 'roi_fillcolor'),  style=LEFT)

        panel.AddText('Major Line Color:', size=(SX, -1), style=LEFT, newrow=True)
        panel.Add(add_color(panel, 'major_elinecolor'),   style=LEFT)
        panel.AddText('Minor Line Color:', size=(SX, -1), style=LEFT)
        panel.Add(add_color(panel, 'minor_elinecolor'),   style=LEFT)

        panel.AddText('Spectra 2 Color:', size=(SX, -1), style=LEFT, newrow=True)
        panel.Add(add_color(panel, 'spectra2_color'),    style=LEFT)
        panel.AddText('XRF Background Color:', size=(SX, -1), style=LEFT)
        panel.Add(add_color(panel, 'bgr_color'),          style=LEFT)

        panel.Add(HLine(panel, size=(400, 3)),  dcol=4, newrow=True)
        panel.Add(Button(panel, 'Done', size=(80, -1), action=self.onDone),
                  dcol=2, newrow=True)
        panel.pack()
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

    def __init__(self, parent, size=(525, 350), **kws):
        self.parent = parent
        conf  = parent.conf
        kws['style'] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, parent, -1, size=size,
                          title='XRF Line Selection', **kws)
        panel = GridPanel(self)

        def add_elines(panel, lines, checked, action):
            for i in lines:
                panel.Add(Check(panel, '%s ' % i, default = i in checked,
                                action=partial(action, label=i)), style=LEFT)

        labopts = {'size': (150, -1), 'newrow': True, 'style': LEFT}

        panel.AddText(' X-ray Emission Lines', dcol=5, colour='#880000')
        panel.Add(HLine(panel, size=(475, 3)),  dcol=5, newrow=True)

        panel.AddText('Major K Lines:', **labopts)
        add_elines(panel, self.k1lines, conf.K_major, self.onKMajor)

        panel.AddText('Minor K Lines:', **labopts)
        add_elines(panel, self.k2lines, conf.K_minor, self.onKMinor)

        panel.AddText('Major L Lines:', **labopts)
        add_elines(panel, self.l1lines, conf.L_major, self.onLMajor)

        panel.AddText('Minor L Lines:', **labopts)
        add_elines(panel, self.l2lines, conf.L_minor, self.onLMinor)

        panel.AddText(' ', **labopts)
        add_elines(panel, self.l3lines, conf.L_minor, self.onLMinor)

        panel.AddText('Major M Lines:', **labopts)
        add_elines(panel, self.mlines,  conf.M_major, self.onMMajor)

        panel.AddText('Min Energy (keV): ', **labopts)
        panel.Add(FloatCtrl(panel, value=conf.e_min,
                            minval=0, maxval=1000, precision=2,
                            action=self.onErange, action_kws={'is_max':False}),
                  dcol=3, style=LEFT)

        panel.AddText('Max Energy (keV): ', **labopts)
        panel.Add(FloatCtrl(panel, value=conf.e_max,
                            minval=0, maxval=1000, precision=2,
                            action=self.onErange, action_kws={'is_max':True}),
                  dcol=3, style=LEFT)

        panel.Add(HLine(panel, size=(475, 3)),  dcol=5, newrow=True)
        panel.Add(Button(panel, 'Done', size=(80, -1), action=self.onDone),
                  newrow=True, style=LEFT)
        panel.pack()
        self.Show()
        self.Raise()

    def onKMajor(self, event=None, label=None):
        self.onLine(label, event.IsChecked(), self.parent.conf.K_major)

    def onKMinor(self, event=None, label=None):
        self.onLine(label, event.IsChecked(), self.parent.conf.K_minor)

    def onLMajor(self, event=None, label=None):
        self.onLine(label, event.IsChecked(), self.parent.conf.L_major)

    def onLMinor(self, event=None, label=None):
        self.onLine(label, event.IsChecked(), self.parent.conf.L_minor)

    def onMMajor(self, event=None, label=None):
        self.onLine(label, event.IsChecked(), self.parent.conf.M_major)

    def onErange(self, event=None, value=None, is_max=True):
        if is_max:
            self.parent.conf.e_max = float(value)
        else:
            self.parent.conf.e_min = float(value)

    def onLine(self, label, checked, plist):
        if label in plist and not checked:
            plist.remove(label)
        elif label not in plist and checked:
            plist.append(label)
        if self.parent.selected_elem is not None:
            self.parent.onShowLines(elem=self.parent.selected_elem)

    def onDone(self, event=None):
        self.Destroy()

class XRFDisplayConfig:
    highlight_elinecolor = '#880000'
    major_elinecolor = '#DAD8CA'    
    minor_elinecolor = '#F4DAC0'
    marker_color     = '#77BB99'
    roi_fillcolor    = '#F8F0BA'
    roi_color        = '#AA0000'
    spectra_color    = '#0000AA'
    spectra2_color   = '#00DD00'
    bgr_color        = '#000000'

    K_major = ['Ka1', 'Ka2', 'Kb1']
    K_minor = ['Kb3', 'Kb2']
    K_minor = []
    L_major = ['La1', 'Lb1', 'Lb3', 'Lb4']
    L_minor = ['Ln', 'Ll', 'Lb2,15', 'Lg2', 'Lg3', 'Lg1', 'La2']
    L_minor = []
    M_major = ['Ma', 'Mb', 'Mg', 'Mz']
    e_min   = 1.25
    e_max   = 30.0
