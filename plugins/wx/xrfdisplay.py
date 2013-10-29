#!/usr/bin/env python
"""
GUI Frame for XRF display, reading larch MCA group

"""
import sys
import os
import time
import copy
from functools import partial

import wx
import wx.lib.mixins.inspection
import wx.lib.scrolledpanel as scrolled
from wx._core import PyDeadObjectError
import wx.lib.colourselect  as csel

import numpy as np
import matplotlib
from wxmplot import PlotPanel
from wxmplot.colors import hexcolor

from larch import Group, Parameter, isParameter, use_plugin_path

use_plugin_path('math')
use_plugin_path('xrf')
use_plugin_path('xray')
use_plugin_path('wx')

from mathutils import index_of

from wxutils import (SimpleText, EditableListBox, FloatCtrl, Font,
                     pack, Popup, Button, get_icon, Check, MenuItem,
                     Choice, FileOpen, FileSave, fix_filename, HLine,
                     GridPanel, CEN, LEFT, RIGHT)

from periodictable import PeriodicTablePanel

from gsemca_file import GSEMCA_File, gsemca_group
from xrf_bgr import xrf_background
from xrf_calib import xrf_calib_fitrois, xrf_calib_compute, xrf_calib_apply

ALL_CEN =  wx.ALL|CEN
ALL_LEFT =  wx.ALL|LEFT
ALL_RIGHT =  wx.ALL|RIGHT

FILE_WILDCARDS = "MCA File (*.mca)|*.mca|All files (*.*)|*.*"

FILE_ALREADY_READ = """The File
   '%s'
has already been read.
"""


def txt(panel, label, size=75, colour=None,  style=None):
    if style is None:
        style = wx.ALIGN_LEFT|wx.ALL|wx.GROW
    if colour is None:
        colour = wx.Colour(0, 0, 50)
    return SimpleText(panel, label, size=(size, -1),
                      colour=colour, style=style)

def lin(panel, len=30, wid=2, style=wx.LI_HORIZONTAL):
    return wx.StaticLine(panel, size=(len, wid), style=style)

class Menu_IDs:
    def __init__(self):
        self.EXIT   = wx.NewId()
        self.SAVE   = wx.NewId()
        self.CONFIG = wx.NewId()
        self.UNZOOM = wx.NewId()
        self.HELP   = wx.NewId()
        self.ABOUT  = wx.NewId()
        self.PRINT  = wx.NewId()
        self.PSETUP = wx.NewId()
        self.PREVIEW= wx.NewId()
        self.CLIPB  = wx.NewId()
        self.SELECT_COLOR = wx.NewId()
        self.SELECT_SMOOTH= wx.NewId()
        self.TOGGLE_LEGEND = wx.NewId()
        self.TOGGLE_GRID = wx.NewId()

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
            eknown, ecen, fwhm, amp = mca.init_calib[roi.name]

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
        panel.AddText("Current Calibration:",   dcol=2, newrow=True)
        panel.AddText("offset(eV):")
        panel.AddText("%.2f" % (1000*self.mca.offset), dcol=2)
        panel.AddText("slope(eV/chan):")
        panel.AddText("%.2f" % (1000*self.mca.slope),  dcol=2)

        panel.AddText("Refined Calibration:", dcol=2, newrow=True)
        self.new_offset = wx.TextCtrl(panel, -1, value="--", size=(80, -1))
        self.new_slope  = wx.TextCtrl(panel, -1, value="--", size=(80, -1))
        panel.AddText("offset(eV):")
        panel.Add(self.new_offset,    dcol=2)
        panel.AddText("slope(eV/chan):")
        panel.Add(self.new_slope,     dcol=2)

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
        self.new_offset.SetValue("% .2f" % (1000*offset))
        self.new_slope.SetValue("% .2f" % (1000*slope))

        # find ROI peak positions using this new calibration
        xrf_calib_fitrois(mca, _larch=self.larch)
        for roi in self.mca.rois:
            eknown, ecen, fwhm, amp = mca.init_calib[roi.name]
            diff  = ecen - eknown
            for roiname, eknown, ecen, w_ncen, w_ndif, w_nwid, w_use in self.wids:
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

class XRFBackgroundFrame(wx.Frame):
    def __init__(self, parent, mca, larch=None, size=(350, -1)):
        self.mca = mca
        self.larch = larch
        self.parent = parent
        wx.Frame.__init__(self, parent, -1, 'Fit Background',
                          size=size, style=wx.DEFAULT_FRAME_STYLE)

        self.SetFont(Font(8))
        panel = GridPanel(self)

        panel.AddText("Background Parameters", colour='#880000', dcol=3)
        width = getattr(self.mca, 'bgr_width', 2.5)
        compr = getattr(self.mca, 'bgr_compress', 2)
        expon = getattr(self.mca, 'bgr_exponent', 2.5)        
        self.wid_width = FloatCtrl(panel, value=width, minval=0, maxval=10, 
                                   precision=1)
        self.wid_compress = FloatCtrl(panel, value=compr, minval=0, maxval=8, 
                                   precision=0)
        self.wid_exponent = FloatCtrl(panel, value=expon, minval=1, maxval=8, 
                                   precision=0)
        
        panel.AddText("Energy Width: ", newrow=True, style=LEFT)
        panel.Add(self.wid_width, style=LEFT)
        panel.AddText(" (keV) ", style=LEFT)
        panel.AddText("Exponent: ", newrow=True, style=LEFT)
        panel.Add(self.wid_exponent, style=LEFT)
        panel.AddText(" (even numbers) ", style=LEFT)
        panel.AddText("Compression: ", newrow=True, style=LEFT)
        panel.Add(self.wid_compress, style=LEFT)
        panel.AddText(" (even numbers) ", style=LEFT)

        panel.Add(HLine(panel, size=(300, 3)),  dcol=4, newrow=True)

        panel.Add(Button(panel, 'Update Background',
                         size=(150, -1), action=self.onCalc),
                         dcol=3, newrow=True, style=LEFT)
        panel.Add(Button(panel, 'Done',
                         size=(80, -1), action=self.onClose),
                         dcol=1, newrow=True, style=LEFT)
        panel.pack()
        self.Show()
        self.Raise()

    def onCalc(self, event=None):
        width = self.wid_width.GetValue()
        compress = self.wid_compress.GetValue()
        exponent = self.wid_exponent.GetValue()
        xrf_background(energy=self.mca.energy, counts=self.mca.counts,
                       group=self.mca, width=width, compress=compress, 
                       exponent=exponent, _larch=self.larch)
        self.mca.bgr_width = width
        self.mca.bgr_compress = compress
        self.mca.bgr_exponent = exponent
        self.parent.plotmca(self.mca)
        self.parent.oplot(self.mca.energy, self.mca.bgr, color='black',
                          label='background')
        
    def onClose(self, event=None):
        self.Destroy()


class SettingsFrame(wx.Frame):
    """settings frame for XRFDisplay"""
    k1lines = ['Ka1', 'Ka2', 'Kb1']
    k2lines = ['Kb2', 'Kb3']
    l1lines = ['La1', 'Lb1', 'Lb3', 'Lb4']
    l2lines = ['La2', 'Ll',  'Ln', 'Lg2', 'Lg3', 'Lg1', 'Lb2,15']
    mlines  = ['Ma', 'Mb', 'Mg', 'Mz']

    def __init__(self, parent, conf, size=(600, 450), **kws):
        self.parent = parent
        kws['style'] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, parent, -1, size=size,
                          title='XRF Display Settings', **kws)
        labstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM|wx.EXPAND
        leftstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM
        rlabstyle = wx.ALIGN_RIGHT|wx.RIGHT|wx.TOP|wx.EXPAND
        txtstyle=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE|wx.TE_PROCESS_ENTER

        self.conf  = conf
        panel = wx.Panel(self)
        sizer = wx.GridBagSizer(10, 10)

        emin = FloatCtrl(panel, value=self.parent.conf.e_min,
                         minval=0, maxval=1000, precision=2,
                         action=self.onErange, action_kws={'is_max':False})
        emax = FloatCtrl(panel, value=self.parent.conf.e_max,
                         minval=0, maxval=1000, precision=2,
                         action=self.onErange, action_kws={'is_max':True})

        def add_color(panel, name):
            cval = hexcolor(getattr(self.conf, name))
            c = csel.ColourSelect(panel,  -1, "", cval, size=(40, 25))
            c.Bind(csel.EVT_COLOURSELECT, partial(self.onColor, item=name))
            return c

        ir = 0
        sizer.Add(txt(panel, '  XRF Display Settings ', size=275),
                  (ir, 0), (1, 5), labstyle|wx.ALIGN_CENTER)
        ir += 1
        sizer.Add(lin(panel, 575),   (ir, 0), (1, 4), labstyle)

        ir += 1
        sizer.Add(txt(panel, 'Spectra Color:', size=140),
                  (ir, 0), (1, 1), labstyle)
        sizer.Add(add_color(panel, 'spectra_color'),  (ir, 1), (1, 1), labstyle)

        sizer.Add(txt(panel, 'ROI Spectra Color:', size=140),
                  (ir, 2), (1, 1), labstyle)
        sizer.Add(add_color(panel, 'roi_color'),  (ir, 3), (1, 1), leftstyle)

        ir += 1
        sizer.Add(txt(panel, 'ROI Fill Color:', size=140),
                  (ir, 0), (1, 1), labstyle)
        sizer.Add(add_color(panel, 'roi_fillcolor'), (ir, 1), (1, 1), labstyle)

        sizer.Add(txt(panel, 'Marker Color:', size=140),
                  (ir, 2), (1, 1), labstyle)
        sizer.Add(add_color(panel, 'marker_color'),  (ir, 3), (1, 1), leftstyle)

        ir += 1
        sizer.Add(txt(panel, 'Major Line Color:', size=140),
                  (ir, 0), (1, 1), labstyle)
        sizer.Add(add_color(panel, 'major_elinecolor'),  (ir, 1), (1, 1), labstyle)
        sizer.Add(txt(panel, 'Minor Line Color:', size=140),
                  (ir, 2), (1, 1), labstyle)
        sizer.Add(add_color(panel, 'minor_elinecolor'), (ir, 3), (1, 1), leftstyle)

        ir += 1
        sizer.Add(lin(panel, 375),   (ir, 0), (1, 4), labstyle)

        def eline_panel(all_lines, checked, action):
            p = wx.Panel(panel)
            s = wx.BoxSizer(wx.HORIZONTAL)
            for i in all_lines:
                s.Add(Check(p, '%s ' % i,
                                   default = i in checked,
                                   action=partial(action, label=i)),
                      wx.EXPAND|wx.ALL, 0)
            pack(p, s)
            return p
        k1panel = eline_panel(self.k1lines, conf.K_major, self.onKMajor)
        k2panel = eline_panel(self.k2lines, conf.K_minor, self.onKMinor)
        l1panel = eline_panel(self.l1lines, conf.L_major, self.onLMajor)
        l2panel = eline_panel(self.l2lines, conf.L_minor, self.onLMinor)
        m1panel = eline_panel(self.mlines, conf.M_major, self.onMMajor)

        ir += 1
        sizer.Add(txt(panel, 'Major K Lines:', size=140),
                  (ir, 0), (1, 1), labstyle)
        sizer.Add(k1panel, (ir, 1), (1, 2), leftstyle, 1)

        ir += 1
        sizer.Add(txt(panel, 'Minor K Lines:', size=140),
                  (ir, 0), (1, 1), labstyle)
        sizer.Add(k2panel, (ir, 1), (1, 2), leftstyle)

        ir += 1
        sizer.Add(txt(panel, 'Major L Lines:', size=140),
                  (ir, 0), (1, 1), labstyle)
        sizer.Add(l1panel, (ir, 1), (1, 2), leftstyle)
        ir += 1
        sizer.Add(txt(panel, 'Minor L Lines:', size=140),
                  (ir, 0), (1, 1), labstyle)
        sizer.Add(l2panel, (ir, 1), (1, 3), leftstyle)

        ir += 1
        sizer.Add(txt(panel, 'Major M Lines:', size=140),
                  (ir, 0), (1, 1), labstyle)
        sizer.Add(m1panel, (ir, 1), (1, 2), leftstyle)

        ir += 1
        sizer.Add(txt(panel, 'Energy Min/Max (keV): ', size=140),
                  (ir, 0), (1, 1), labstyle)
        sizer.Add(emin, (ir, 1), (1, 2), leftstyle)
        sizer.Add(emax, (ir, 3), (1, 2), leftstyle)

        ir += 1
        sizer.Add(lin(panel, 375),   (ir, 0), (1, 4), labstyle)

        ir += 1
        sizer.Add(Button(panel, 'Done', size=(80, -1),
                         action=self.onDone),  (ir, 0), (1, 1), leftstyle)

        pack(panel, sizer)
        self.Show()
        self.Raise()

    def onColor(self, event=None, item=None):
        color = hexcolor(event.GetValue())
        setattr(self.conf, item, color)
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
    major_elinecolor = '#DAD8CA'
    minor_elinecolor = '#F4DAC0'
    marker_color     = '#77BB99'
    roi_fillcolor    = '#F8F0BA'
    roi_color        = '#AA0000'
    spectra_color    = '#0000AA'

    K_major = ['Ka1', 'Ka2', 'Kb1']
    K_minor = ['Kb3', 'Kb2']
    K_minor = []
    L_major = ['La1', 'Lb1', 'Lb3', 'Lb4']
    L_minor = ['Ln', 'Ll', 'Lb2,15', 'Lg2', 'Lg3', 'Lg1', 'La2']
    L_minor = []

    M_major = ['Ma', 'Mb', 'Mg', 'Mz']
    e_min   = 0.50
    e_max   = 30.0

class XRFDisplayFrame(wx.Frame):
    _about = """XRF Spectral Viewer
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, _larch=None, parent=None, gsexrmfile=None,
                 size=(725, 450), axissize=None, axisbg=None,
                 title='XRF Display', exit_callback=None,
                 output_title='XRF', **kws):


        # kws["style"] = wx.DEFAULT_FRAME_STYLE|wx
        wx.Frame.__init__(self, parent=parent,
                          title=title, size=size,
                          **kws)
        self.conf = XRFDisplayConfig()
        self.subframes = {}
        self.data = None
        self.gsexrmfile = gsexrmfile
        self.title = title
        self.plotframe = None
        self.larch = _larch
        self.exit_callback = exit_callback
        self.roi_patch = None
        self.selected_roi = None
        self.selected_elem = None
        self.mca  = None
        self.mca2 = None
        self.rois_shown = False
        self.major_markers = []
        self.minor_markers = []
        self.energy_for_zoom = None
        self.zoom_lims = []
        self.last_rightdown = None
        self.last_leftdown = None
        self.cursor_markers = [None, None]
        self.ylog_scale = True
        self.win_title = title
        self.SetTitle(title)

        self.createMainPanel()
        self.createMenus()
        self.SetFont(Font(9))
        self.statusbar = self.CreateStatusBar(3)
        self.statusbar.SetStatusWidths([-3, -1, -1])
        statusbar_fields = ["XRF Display", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

    def ignoreEvent(self, event=None):
        pass

    def on_leftdown(self, event=None):
        if event is None:
            return
        x, y  = event.xdata, event.ydata
        if len(self.panel.fig.get_axes()) > 1:
            try:
                x, y = self.panel.axes.transData.inverted().transform((event.x, event.y))
            except:
                pass
        if self.mca is not None:
            ix = index_of(self.mca.energy, x)
            x = self.mca.energy[ix]
            y = self.mca.counts[ix]
        self.last_leftdown = x
        self.energy_for_zoom = x
        self.draw_marker(x, y, 0, 'Left:')

    def clear_lines(self, evt=None):
        "remove all Line Markers"
        for m in self.major_markers + self.minor_markers:
            try:
                m.remove()
            except:
                pass
        self.major_markers = []
        self.minor_markers = []
        self.panel.canvas.draw()
        
    def clear_markers(self, evt=None):
        "remove all Cursor Markers"        
        for m in self.cursor_markers:
            if m is not None:
                m.remove()
        self.cursor_markers = [None, None]
        self.panel.canvas.draw()
        
    def draw_marker(self, x, y, idx, title):
        arrow = self.panel.axes.arrow
        if self.cursor_markers[idx] is not None:
            try:
                self.cursor_markers[idx].remove()
            except:
                pass
        ymin, ymax = self.panel.axes.get_ylim()
        dy = int(max((ymax-ymin)*0.10,  min(ymax*0.99, 3*y)) - y)
        try:
            self.cursor_markers[idx] = arrow(x, y, 0, dy, shape='full',
                                             width=0.015, head_width=0.0,
                                             length_includes_head=True,
                                             head_starts_at_zero=True,
                                             color=self.conf.marker_color)
            self.panel.canvas.draw()
            self.write_message("%s E=%.3f keV, Counts=%g" % (title, x, y), panel=1+idx)
        except:
            pass
    def on_rightdown(self, event=None):
        if event is None:
            return
        x, y  = event.xdata, event.ydata
        if len(self.panel.fig.get_axes()) > 1:
            try:
                x, y = self.panel.axes.transData.inverted().transform((event.x, event.y))
            except:
                pass
        if self.mca is not None:
            ix = index_of(self.mca.energy, x)
            x = self.mca.energy[ix]
            y = self.mca.counts[ix]
        self.last_rightdown = x
        self.draw_marker(x, y, 1, 'Right:')

    def createMainPanel(self):
        self.wids = {}
        ctrlpanel = wx.Panel(self)
        ptable = PeriodicTablePanel(ctrlpanel,  onselect=self.onShowLines,
                                    tooltip_msg='Select Element for KLM Lines')

        plotpanel = self.panel = PlotPanel(self, fontsize=7,
                                           axisbg='#FDFDFA',
                                           axissize=[0.01, 0.11, 0.98, 0.87],
                                           # axissize=[0.12, 0.12, 0.86, 0.86],
                                           output_title='test.xrf',
                                           messenger=self.write_message)
        self.panel.conf.labelfont.set_size(7)
        self.panel.onRightDown= self.on_rightdown
        self.panel.add_cursor_mode('zoom',  motion = self.ignoreEvent,
                                   leftup   = self.ignoreEvent,
                                   leftdown = self.on_leftdown,
                                   rightdown = self.on_rightdown)

        sizer = wx.GridBagSizer(11, 5)
        labstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM|wx.EXPAND
        ctrlstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM
        rlabstyle = wx.ALIGN_RIGHT|wx.RIGHT|wx.TOP|wx.EXPAND
        txtstyle=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE|wx.TE_PROCESS_ENTER

        self.wids['ylog'] = Choice(ctrlpanel, size=(80, -1),
                                       choices=['log', 'linear'],
                                       action=self.onLogLinear)
        self.wids['zoom_in'] = Button(ctrlpanel, 'Zoom In',
                                          size=(80, -1),
                                          action=self.onZoomIn)
        self.wids['zoom_out'] = Button(ctrlpanel, 'Zoom out',
                                          size=(80, -1),
                                          action=self.onZoomOut)

        spanel = wx.Panel(ctrlpanel)
        ssizer = wx.BoxSizer(wx.HORIZONTAL)
        for wname, dname in (('uparrow', 'up'),
                             ('leftarrow', 'left'),
                             ('rightarrow', 'right'),
                             ('downarrow', 'down')):
            self.wids[wname] = wx.BitmapButton(spanel, -1,
                                               get_icon(wname),
                                               style=wx.NO_BORDER)
            self.wids[wname].Bind(wx.EVT_BUTTON,
                                 partial(ptable.onKey, name=dname))

            ssizer.Add(self.wids[wname],  0, wx.EXPAND|wx.ALL, 2)

        self.wids['kseries'] = Check(spanel, ' K ',
                                            action=self.onSeriesSelect)
        self.wids['lseries'] = Check(spanel, ' L ',
                                            action=self.onSeriesSelect)
        self.wids['mseries'] = Check(spanel, ' M ',
                                            action=self.onSeriesSelect)

        ssizer.Add(txt(spanel, '  '),       1, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['kseries'],    0, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['lseries'],    0, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['mseries'],    0, wx.EXPAND|wx.ALL, 0)
        pack(spanel, ssizer)

        self.wids['roilist'] = EditableListBox(ctrlpanel, self.onROI,
                                               right_click=False,
                                               size=(80, 120))

        self.wids['roiname'] = wx.TextCtrl(ctrlpanel, -1, '', size=(140, -1))


        self.wids['newroi'] = Button(ctrlpanel, 'Add', size=(75, -1),
                                         action=self.onNewROI)
        self.wids['delroi'] = Button(ctrlpanel, 'Delete', size=(75, -1),
                                         action=self.onDelROI)

        self.wids['counts_tot'] = txt(ctrlpanel, ' Total: ', size=140)
        self.wids['counts_net'] = txt(ctrlpanel, ' Net:  ', size=140)
        self.wids['roi_message'] = txt(ctrlpanel, '  ', size=280)

        ir = 0
        sizer.Add(ptable,  (ir, 1), (1, 4), wx.ALIGN_RIGHT|wx.EXPAND)

        ir += 1
        sizer.Add(spanel, (ir, 1), (1, 4), labstyle)

        ir += 1
        sizer.Add(lin(ctrlpanel, 195),   (ir, 1), (1, 4), labstyle)

        # roi section...
        ir += 1
        sizer.Add(txt(ctrlpanel, ' Regions of Interest:', size=140),
                  (ir, 1), (1, 2), labstyle)
        sizer.Add(self.wids['roilist'],     (ir, 3), (5, 2), labstyle)

        sizer.Add(self.wids['roiname'],  (ir+1, 1), (1, 2), labstyle)

        sizer.Add(self.wids['newroi'],   (ir+2, 1), (1, 1), wx.ALIGN_CENTER)
        sizer.Add(self.wids['delroi'],   (ir+2, 2), (1, 1), wx.ALIGN_CENTER)

        sizer.Add(self.wids['counts_tot'], (ir+3, 1), (1, 2), LEFT)
        sizer.Add(self.wids['counts_net'], (ir+4, 1), (1, 2), LEFT)

        ir += 5
        sizer.Add(self.wids['roi_message'],        (ir, 1), (1, 5), ctrlstyle)
        ir += 1
        sizer.Add(lin(ctrlpanel, 195),         (ir, 1), (1, 4), labstyle)

        ir += 2
        sizer.Add(txt(ctrlpanel, ' Energy Scale:'),  (ir, 1), (1, 2), labstyle)
        sizer.Add(self.wids['zoom_in'],              (ir, 3), (1, 1), ctrlstyle)
        sizer.Add(self.wids['zoom_out'],             (ir, 4), (1, 1), ctrlstyle)
        ir += 1
        sizer.Add(txt(ctrlpanel, ' Counts Scale:'),  (ir, 1), (1, 2), labstyle)
        sizer.Add(self.wids['ylog'],                 (ir, 4), (1, 2), ctrlstyle)

        ir += 1
        sizer.Add(lin(ctrlpanel, 195),   (ir, 1), (1, 4), labstyle)

        sizer.SetHGap(1)
        sizer.SetVGap(1)
        ctrlpanel.SetSizer(sizer)
        sizer.Fit(ctrlpanel)

        tx, ty = ptable.GetBestSize()
        cx, cy = ctrlpanel.GetBestSize()
        px, py = plotpanel.GetBestSize()

        self.SetSize((max(cx, tx)+px, 25+max(cy, py)))

        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL
        msizer = wx.BoxSizer(wx.HORIZONTAL)
        msizer.Add(ctrlpanel, 0, style, 1)
        msizer.Add(self.panel,     1, style, 1)
        pack(self, msizer)
        self.set_roilist(mca=None)

    def onZoomIn(self, event=None):
        emin, emax = self.panel.axes.get_xlim()
        self.zoom_lims.append((emin, emax))
        erange = emax-emin
        emid   = (emax+emin)/2.0
        dmin, dmax = emin, emax

        if self.mca is not None:
            dmin, dmax = self.mca.energy.min(), self.mca.energy.max()
        if self.energy_for_zoom is not None:
            emid = self.energy_for_zoom
        espan = erange/3.0
        e1 = max(dmin, emid-espan)
        e2 = min(dmax, emid+espan)
        self.panel.axes.set_xlim((e1, e2))
        self.panel.canvas.draw()

    def unzoom_all(self, event=None):
        self.zoom_lims = []
        self.onZoomOut()

    def onZoomOut(self, event=None):
        e1, e2 = None, None
        if len(self.zoom_lims) > 0:
            e1, e2 = self.zoom_lims.pop()
        elif self.mca is not None:
            e1, e2 = self.mca.energy.min(), self.mca.energy.max()
        if e1 is not None:
            self.panel.axes.set_xlim((e1, e2))
            self.panel.canvas.draw()

    def set_roilist(self, mca=None):
        """ Add Roi names to roilist"""
        self.wids['roilist'].Clear()
        if mca is not None:
            for roi in mca.rois:
                self.wids['roilist'].Append(roi.name)

    def clear_roihighlight(self, event=None):
        self.selected_roi = None
        try:
            self.roi_patch.remove()
        except:
            pass
        self.roi_patch = None
        self.wids['roiname'].SetValue('')
        self.panel.canvas.draw()

    def onNewROI(self, event=None):
        label = self.wids['roiname'].GetValue()
        if (self.last_leftdown is None or
            self.last_rightdown is None or
            self.mca is None):
            return
        found = False
        for roi in self.mca.rois:
            if roi.name.lower()==label:
                found = True
        left  = index_of(self.mca.energy, self.last_leftdown)
        right = index_of(self.mca.energy, self.last_rightdown)
        if left > right:
            left, right = right, left
        self.mca.add_roi(name=label, left=left, right=right, sort=True)
        self.set_roilist(mca=self.mca)
        for roi in self.mca.rois:
            if roi.name.lower()==label:
                selected_roi = roi
        self.plot(self.xdata, self.ydata)
        self.onROI(label=label)
        if self.selected_elem is not None:
            self.onShowLines(elem=self.selected_elem)

    def onDelROI(self, event=None):
        roiname = self.wids['roiname'].GetValue()
        rdat = []
        if self.mca is None:
            return
        for i in range(len(self.mca.rois)):
            roi = self.mca.rois.pop(0)
            if roi.name.lower() != roiname.lower():
                rdat.append((roi.name, roi.left, roi.right))

        for name, left, right in rdat:
            self.mca.add_roi(name=name, left=left, right=right, sort=False)
        self.mca.rois.sort()
        self.set_roilist(mca=self.mca)
        self.wids['roiname'].SetValue('')
        try:
            self.roi_patch.remove()
        except:
            pass

        self.plot(self.xdata, self.ydata)
        if self.selected_elem is not None:
            self.onShowLines(elem=self.selected_elem)

    def onROI(self, event=None, label=None):
        if label is None and event is not None:
            label = event.GetString()
        self.wids['roiname'].SetValue(label)
        msg = "Counts for ROI  %s: " % label
        name, left, right= None, -1, -1
        counts_tot, counts_net = '', ''
        label = label.lower().strip()
        self.selected_roi = None
        if self.mca is not None:
            for roi in self.mca.rois:
                if roi.name.lower()==label:
                    name = roi.name
                    left = roi.left
                    right= roi.right
                    ctot = roi.get_counts(self.mca.counts)
                    cnet = roi.get_counts(self.mca.counts, net=True)
                    counts_tot = " Total: %i" % ctot
                    counts_net = " Net: %i" % cnet
                    msg = "%s  Total: %i, Net: %i" % (msg, ctot, cnet)
                    self.selected_roi = roi
                    break
        if name is None or right == -1:
            return

        try:
            self.roi_patch.remove()
        except:
            pass

        e = np.zeros(right-left+2)
        r = np.ones(right-left+2)
        e[1:-1] = self.mca.energy[left:right]
        r[1:-1] = self.mca.counts[left:right]
        e[0]    = e[1]
        e[-1]   = e[-2]
        roi_message = ' Energy Center=%.3f, Width=%.3f keV' % (
                               (e[0]+e[-1])/2., e[-1] - e[0])
        fill = self.panel.axes.fill_between
        self.roi_patch  = fill(e, r, color=self.conf.roi_fillcolor, zorder=-10)
        self.energy_for_zoom = self.mca.energy[(left+right)/2]

        self.wids['counts_tot'].SetLabel(counts_tot)
        self.wids['counts_net'].SetLabel(counts_net)
        self.wids['roi_message'].SetLabel(roi_message)
        self.write_message(msg, panel=0)
        self.panel.canvas.draw()
        self.panel.Refresh()
        # if self.gsexrmfile is not None:
            # print 'Add ROI: ', self.gsexrmfile

    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "&Read MCA Spectra File\tCtrl+O",
                 "Read GSECARS MCA File",  self.onReadMCAFile)
        # MenuItem(self, fmenu, "&Read XRM Map File\tCtrl+F",
        #          "Read GSECARS XRM MAp File",  self.onReadGSEXRMFile)
        # MenuItem(self, fmenu, "&Open Epics MCA\tCtrl+E",
        #         "Read Epics MCA",  self.onOpenEpicsMCA)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "&Save MCA File\tCtrl+S",
                 "Save GSECARS MCA File",  self.onSaveMCAFile)
        MenuItem(self, fmenu, "&Save ASCII Column File\tCtrl+A",
                 "Save Column File",  self.onSaveColumnFile)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu,  "&Save\tCtrl+S",
                 "Save PNG Image of Plot", self.onSavePNG)
        MenuItem(self, fmenu, "&Copy\tCtrl+C",
                 "Copy Plot Image to Clipboard",
                 self.onCopyImage)
        MenuItem(self, fmenu, 'Page Setup...', 'Printer Setup', self.onPageSetup)
        MenuItem(self, fmenu, 'Print Preview...', 'Print Preview', self.onPrintPreview)
        MenuItem(self, fmenu, "&Print\tCtrl+P", "Print Plot", self.onPrint)


        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "&Quit\tCtrl+Q",
                  "Quit program", self.onExit)

        omenu = wx.Menu()
        MenuItem(self, omenu, "Colors and Line Selection",
                 "Configure Colors and Settings", self.configure)
        MenuItem(self, omenu, "Hide X-ray Lines",
                 "Hide all X-ray Lines", self.clear_lines)
        MenuItem(self, omenu, "Hide selected ROI ",
                 "Hide selected ROI", self.clear_roihighlight)
        MenuItem(self, omenu, "Hide Markers ",
                 "Hide cursor markers", self.clear_markers)

        omenu.AppendSeparator()
        MenuItem(self, omenu, "Configure Plot\tCtrl+K",
                 "Configure Plot Colors, etc", self.panel.configure)
        MenuItem(self, omenu, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range", self.unzoom_all)
        omenu.AppendSeparator()
        MenuItem(self, omenu, "Swap MCAs",
                 "Swap Fore and Back MCAs", self.swap_mcas)
        MenuItem(self, omenu, "Close Background MCA",
                 "Close Background MCA", self.close_bkg_mca)

        amenu = wx.Menu()
        MenuItem(self, amenu, "&Calibrate Energy\tCtrl+E",
                 "Calibrate Energy",  self.onCalibrateEnergy)
        MenuItem(self, amenu, "Fit background\tCtrl+B",
                 "Fit smooth background",  self.onFitBgr)
        MenuItem(self, amenu, "Fit Peaks",
                 "Fit Peaks in spectra",  self.onFitPeaks)        

        self.menubar.Append(fmenu, "&File")
        self.menubar.Append(omenu, "&Options")
        self.menubar.Append(amenu, "&Analysis")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE, self.onExit)

    def onSavePNG(self, event=None):
        if self.panel is not None:
            self.panel.save_figure(event=event)

    def onCopyImage(self, event=None):
        if self.panel is not None:
            self.panel.canvas.Copy_to_Clipboard(event=event)
    def onPageSetup(self, event=None):
        if self.panel is not None:
            self.panel.PrintSetup(event=event)

    def onPrintPreview(self, event=None):
        if self.panel is not None:
            self.panel.PrintPreview(event=event)

    def onPrint(self, event=None):
        if self.panel is not None:
            self.panel.Print(event=event)

    def onExit(self, event=None):
        try:
            if hasattr(self.exit_callback, '__call__'):
                self.exit_callback()
        except:
            pass
        try:
            if self.panel is not None:
                self.panel.win_config.Close(True)
            if self.panel is not None:
                self.panel.win_config.Destroy()
        except:
            pass

        try:
            self.Destroy()
        except:
            pass

    def configure(self, event=None):
        """show configuration frame"""
        try:
            self.win_config.Raise()
        except:
            self.win_config = SettingsFrame(parent=self, conf=self.conf)


    def onSeriesSelect(self, event=None):
        if self.selected_elem is not None:
            self.onShowLines(elem = self.selected_elem)

    def onShowLines(self, event=None, elem=None):
        if elem is None:
            elem  = event.GetString()
        try:
            vline = self.panel.axes.axvline
            elines = self.larch.symtable._xray.xray_lines(elem)
        except:
            return
        self.selected_elem = elem
        self.clear_lines()

        self.energy_for_zoom = None
        miss = [-1, '']
        minors, majors = [], []
        conf = self.conf
        if self.wids['kseries'].IsChecked():
            majors.extend([(l, elines.get(l, miss)[0]) for l in conf.K_major])
            minors.extend([(l, elines.get(l, miss)[0]) for l in conf.K_minor])
        if self.wids['lseries'].IsChecked():
            majors.extend([(l, elines.get(l, miss)[0]) for l in conf.L_major])
            minors.extend([(l, elines.get(l, miss)[0]) for l in conf.L_minor])
        if self.wids['mseries'].IsChecked():
            majors.extend([(l, elines.get(l, miss)[0]) for l in conf.M_major])

        erange = [max(0, self.xdata.min()), self.xdata.max()]
        for label, eev in minors:
            e = float(eev) * 0.001
            if (e > erange[0] and e < erange[1] and
                e >= conf.e_min and e <= conf.e_max):
                l = vline(e, color= self.conf.minor_elinecolor,
                          linewidth=0.75, zorder=-6)
                l.set_label(label)
                self.minor_markers.append(l)

        for label, eev in majors:
            e = float(eev) * 0.001
            if (e > erange[0] and e < erange[1] and
                e >= conf.e_min and e <= conf.e_max):
                l = vline(e, color= self.conf.major_elinecolor,
                          linewidth=1.75, zorder=-4)
                l.set_label(label)
                self.major_markers.append(l)
                if self.energy_for_zoom is None:
                    self.energy_for_zoom = e

        self.panel.canvas.draw()

    def onLogLinear(self, event=None):
        self.ylog_scale = 'log' == event.GetString()
        roiname = None
        if self.selected_roi is not None:
            roiname = self.selected_roi.name
        self.plot(self.xdata, self.ydata)
        if self.selected_elem is not None:
            self.onShowLines(elem=self.selected_elem)
        if roiname is not None:
            self.onROI(label=roiname)

    def plotmca(self, mca, show_mca2=True, **kws):
        self.mca = mca
        self.plot(mca.energy, mca.counts, mca=mca, **kws)
        title = self.win_title
        if hasattr(mca, 'filename'):
            title = "%s: %s"% (title, mca.filename)
        if show_mca2 and self.mca2 is not None:
            self.oplot(self.mca2.energy, self.mca2.counts)
            mca2name = 'MCA2'
            if hasattr(self.mca2, 'filename'):
                mca2name = self.mca2.filename
            title = "%s (fore), %s (back)"% (title, mca2name)
        self.SetTitle(title)
        
    def plot(self, x, y=None, mca=None,  **kws):
        if mca is not None:
            self.mca = mca
        mca = self.mca
        panel = self.panel
        panel.canvas.Freeze()
        kwargs = {'grid': False, 'xmin': 0,
                  'ylog_scale': self.ylog_scale,
                  'xlabel': 'E (keV)',
                  'axes_style': 'bottom',
                  'color': self.conf.spectra_color}
        kwargs.update(kws)

        self.xdata = 1.0*x[:]
        self.ydata = 1.0*y[:]
        yroi = None
        ydat = 1.0*y[:]
        kwargs['ymax'] = max(ydat)*1.25
        kwargs['ymin'] = 1
        if mca is not None:
            if not self.rois_shown:
                self.set_roilist(mca=mca)
            yroi = -1*np.ones(len(y))
            for r in mca.rois:
                yroi[r.left:r.right] = y[r.left:r.right]
                ydat[r.left+1:r.right-1] = -1
            yroi = np.ma.masked_less(yroi, 0)
            ydat = np.ma.masked_less(ydat, 0)

        panel.plot(x, ydat, label='spectra',  **kwargs)
        if yroi is not None:
            kwargs['color'] = self.conf.roi_color
            panel.oplot(x, yroi, label='roi', **kwargs)

        panel.axes.get_yaxis().set_visible(False)
        if len(self.zoom_lims) > 0:
            x1, x2 = self.zoom_lims[-1]
            panel.axes.set_xlim(x1, x2)
        else:
            panel.unzoom_all()
        panel.cursor_mode = 'zoom'
        panel.canvas.draw()
        panel.canvas.Thaw()
        panel.canvas.Refresh()

    def oplot(self, x, y, color='darkgreen', **kws):
        ymax = max( max(self.ydata), max(y))*1.25
        kws.update({'zorder': -5, 'label': 'spectra2',
                    'ymax' : ymax, 'axes_style': 'bottom',
                    'ylog_scale': True})

        self.panel.oplot(x, 1.0*y[:], color=color, **kws)

    def swap_mcas(self, event=None):
        if self.mca2 is None:
            return
            
        self.mca, self.mca2 = self.mca2, self.mca
        self.plotmca(self.mca, show_mca2=True)


    def close_bkg_mca(self, event=None):
        self.mca2 = None
        self.plotmca(self.mca, show_mca2=False)

    def onReadMCAFile(self, event=None):
        dlg = wx.FileDialog(self, message="Open MCA File for reading",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style = wx.OPEN|wx.CHANGE_DIR)

        fnew= None
        if dlg.ShowModal() == wx.ID_OK:
            fnew = os.path.abspath(dlg.GetPath())
        dlg.Destroy()

        if fnew is None:
            return
        self.mca2 = None
        if self.mca is not None:
            self.mca2 = copy.deepcopy(self.mca)

        self.mca = gsemca_group(fnew, _larch=self.larch)
        self.plotmca(self.mca, show_mca2=True)

    def onReadGSEXRMFile(self, event=None, **kws):
        print '  onReadGSEXRMFile   '
        pass

    def onOpenEpicsMCA(self, event=None, **kws):
        print '  onOpenEpicsMCA   '
        pass

    def onSaveMCAFile(self, event=None, **kws):
        deffile = ''
        if hasattr(self.mca, 'sourcefile'):
            deffile = "%s%s" % (deffile, getattr(self.mca, 'sourcefile'))
        if hasattr(self.mca, 'areaname'):
            deffile = "%s%s" % (deffile, getattr(self.mca, 'areaname'))
        if deffile == '':
            deffile ='test'
        if not deffile.endswith('.mca'):
            deffile = deffile + '.mca'

        deffile = fix_filename(str(deffile))

        outfile = FileSave(self, "Save MCA File",
                           default_file=deffile,
                           wildcard=FILE_WILDCARDS)

        if outfile is not None:
            self.mca.save_mcafile(outfile)

    def onSaveColumnFile(self, event=None, **kws):
        print '  onSaveColumnFile   '
        pass

    def onCalibrateEnergy(self, event=None, **kws):
        try:
            self.win_calib.Raise()
        except:
            self.win_calib = CalibrationFrame(self, mca=self.mca,
                                              larch=self.larch)

    def onFitBgr(self, event=None, **kws):
        try:
            self.win_bgr.Raise()
        except:
            self.win_bgr = XRFBackgroundFrame(self, mca=self.mca,
                                              larch=self.larch)

        
    def onFitPeaks(self, event=None, **kws):
        print '  onFit Peaks   '
        pass
    
    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def onAbout(self,event):
        dlg = wx.MessageDialog(self, self._about,"About XRF Viewer",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,event):
        self.Destroy()

    def onReadFile(self, event=None):
        dlg = wx.FileDialog(self, message="Read MCA File",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.OPEN)
        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
            if path in self.filemap:
                read = Popup(self, "Re-read file '%s'?" % path, 'Re-read file?',
                             style=wx.YES_NO)
        dlg.Destroy()

        if read:
            try:
                parent, fname = os.path.split(path)
                # xrmfile = GSEXRM_MapFile(fname)
            except:
                # Popup(self, NOT_GSEXRM_FILE % fname,
                # "Not a Map file!")
                return


class XRFApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, **kws):
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        frame = XRFDisplayFrame() #
        frame.Show()
        self.SetTopWindow(frame)
        self.ShowInspectionTool()
        return True

if __name__ == "__main__":
    XRFApp().MainLoop()
