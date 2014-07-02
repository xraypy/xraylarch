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
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception
    
import wx.lib.colourselect  as csel
import numpy as np
import matplotlib
from wxmplot import PlotPanel

HAS_DV = False
try:
    import wx.dataview as dv
    HAS_DV = True
except:
    pass

from larch import Interpreter, use_plugin_path

use_plugin_path('math')
from mathutils import index_of

use_plugin_path('xrf')
use_plugin_path('xray')
use_plugin_path('wx')


from wxutils import (SimpleText, EditableListBox, Font,
                     pack, Popup, Button, get_icon, Check, MenuItem,
                     Choice, FileOpen, FileSave, fix_filename, HLine,
                     GridPanel, CEN, LEFT, RIGHT)

from periodictable import PeriodicTablePanel

from xrfdisplay_utils import (CalibrationFrame, ColorsFrame,
                              XrayLinesFrame, XRFDisplayConfig)

from xrfdisplay_fitpeaks import FitSpectraFrame

from gsemca_file import GSEMCA_File, gsemca_group

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
        self.wids = {}
        self.larch = _larch
        if self.larch is None:
            self.init_larch()
        self._mcagroup = self.larch.symtable.new_group('_mcas')
        self.exit_callback = exit_callback
        self.roi_patch = None
        self.selected_roi = None
        self.selected_elem = None
        self.mca = None
        self.mca2 = None
        self.xdata = np.arange(2048)*0.015
        self.ydata = np.ones(2048)*1.e-4
        self.x2data = None
        self.y2data = None
        self.rois_shown = False
        self.major_markers = []
        self.minor_markers = []
        self.energy_for_zoom = None
        self.zoom_lims = []

        self.xmarker_left = None
        self.xmarker_right = None

        self.highlight_xrayline = None        
        self.highlight_xrayline = None
        self.cursor_markers = [None, None]
        self.ylog_scale = True
        self.win_title = title
        self.SetTitle(title)

        self._menus = []
        
        self.createMainPanel()
        self.createMenus()
        self.SetFont(Font(9))
        self.statusbar = self.CreateStatusBar(4)
        self.statusbar.SetStatusWidths([-1, -1, -1, -1])
        statusbar_fields = ["XRF Display", " ", " ", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

    def ignoreEvent(self, event=None):
        pass

    def on_cursor(self, event=None, side='left'):
        if event is None:
            return
        x, y  = event.xdata, event.ydata
        if len(self.panel.fig.get_axes()) > 1:
            try:
                x, y = self.panel.axes.transData.inverted().transform((event.x, event.y))
            except:
                pass
        ix = x
        if self.mca is not None:
            ix = index_of(self.mca.energy, x)

        if side == 'right':
            self.xmarker_right = ix
        elif side == 'left':        
            self.xmarker_left = ix
            
        if self.xmarker_left is not None and self.xmarker_right is not None:
            ix1, ix2 = self.xmarker_left, self.xmarker_right
            self.xmarker_left  = min(ix1, ix2)
            self.xmarker_right = max(ix1, ix2)

        if side == 'left':
            self.energy_for_zoom = self.mca.energy[ix]
        self.update_status()
        self.panel.canvas.draw()
        
    def clear_lines(self, evt=None):
        "remove all Line Markers"
        for m in self.major_markers + self.minor_markers:
            try:
                m.remove()
            except:
                pass
        if self.highlight_xrayline is not None:
            self.highlight_xrayline.remove()

        self.highlight_xrayline = None
        self.major_markers = []
        self.minor_markers = []
        self.panel.canvas.draw()

    def clear_markers(self, evt=None):
        "remove all Cursor Markers"
        for m in self.cursor_markers:
            if m is not None:
                m.remove()
        self.cursor_markers = [None, None]
        self.xmarker_left  = None
        self.xmarker_right = None
        self.panel.canvas.draw()

    def clear_background(self, evt=None):
        "remove XRF background"
        self.mca2 = None
        self.plotmca(self.mca)

    def update_status(self):
        fmt = "%s: Chan=%i [%6.3f keV] Counts=%g"
        if (self.xmarker_left is None and
            self.xmarker_right is None and
            self.selected_roi is None):
            return

        log = np.log10
        axes= self.panel.axes
        def draw_ymarker_range(idx, x, y):
            ymin, ymax = self.panel.axes.get_ylim()
            y1 = (y-ymin)/(ymax-ymin+0.0002)
            if y < 1.0: y = 1.0
            if  self.ylog_scale:
                y1 = (log(y)-log(ymin))/(log(ymax)-log(ymin)+2.e-9)
                if y1 < 0.0: y1 = 0.0
            y2 = min(y1+0.25, y1*0.1 + 0.9)
            if self.cursor_markers[idx] is not None:
                try:
                    self.cursor_markers[idx].remove()
                except:
                    pass
            self.cursor_markers[idx] = axes.axvline(x, y1, y2, linewidth=2.0, 
                                                    color=self.conf.marker_color)
        
        if self.xmarker_left is not None:
            ix = self.xmarker_left
            x, y = self.xdata[ix],  self.ydata[ix]
            draw_ymarker_range(0, x, y)
            self.write_message(fmt % ("L", ix, x, y), panel=1)
        if self.xmarker_right is not None:
            ix = self.xmarker_right
            x, y = self.xdata[ix],  self.ydata[ix]
            draw_ymarker_range(1, x, y)
            self.write_message(fmt % ("R", ix, x, y), panel=2)

        if self.mca is None:
            return
        
        if (self.xmarker_left is not None and
            self.xmarker_right is not None):
            sum = 0.0
            if self.xmarker_left < self.xmarker_right:
                sum = self.ydata[self.xmarker_left:self.xmarker_right].sum()
            dt = self.mca.real_time
            if dt is None or dt < 0:  dt = 1.0
            self.write_message("Counts=%10i  CPS=%8.1f"%(sum, sum/dt), panel=3)

        if self.selected_roi is not None:
            roi = self.selected_roi
            left, right = roi.left, roi.right
            self.ShowROIStatus(roi)

            try:
                self.roi_patch.remove()
            except:
                pass

            e = np.zeros(right-left+2)
            r = np.ones(right-left+2)
            e[1:-1] = self.mca.energy[left:right]
            r[1:-1] = self.mca.counts[left:right]
            e[0]  = e[1]
            e[-1] = e[-2]
            self.roi_patch  = axes.fill_between(e, r, zorder=-10,
                                                color=self.conf.roi_fillcolor)


    def createPlotPanel(self):
        """mca plot window"""
        pan = PlotPanel(self, fontsize=7,
                        axisbg='#FDFDFA',
                        axissize=[0.01, 0.11, 0.98, 0.87],
                        output_title='test.xrf',
                        messenger=self.write_message)

        pan.conf.labelfont.set_size(7)
        pan.onRightDown= partial(self.on_cursor, side='right')
        pan.add_cursor_mode('zoom',  motion = self.ignoreEvent,
                            leftup   = self.ignoreEvent,
                            leftdown = self.on_cursor, 
                            rightdown = partial(self.on_cursor, side='right'))
        return pan


    def createControlPanel(self):
        ctrlpanel = wx.Panel(self, name='Ctrl Panel')

        ptable = PeriodicTablePanel(ctrlpanel,  onselect=self.onShowLines,
                                    tooltip_msg='Select Element for KLM Lines')

        self.wids['ptable'] = ptable

        sizer = wx.GridBagSizer(15, 5)
        labstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM|wx.EXPAND
        ctrlstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM

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

        arrowpanel = wx.Panel(ctrlpanel)
        ssizer = wx.BoxSizer(wx.HORIZONTAL)
        for wname, dname in (('uparrow', 'up'),
                             ('leftarrow', 'left'),
                             ('rightarrow', 'right'),
                             ('downarrow', 'down')):
            self.wids[wname] = wx.BitmapButton(arrowpanel, -1,
                                               get_icon(wname),
                                               style=wx.NO_BORDER)
            self.wids[wname].Bind(wx.EVT_BUTTON,
                                 partial(ptable.onKey, name=dname))

            ssizer.Add(self.wids[wname],  0, wx.EXPAND|wx.ALL, 2)

        self.wids['kseries'] = Check(arrowpanel, ' K ', action=self.onKLM)
        self.wids['lseries'] = Check(arrowpanel, ' L ', action=self.onKLM)
        self.wids['mseries'] = Check(arrowpanel, ' M ', action=self.onKLM)

        ssizer.Add(txt(arrowpanel, '  '),   1, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['kseries'],    0, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['lseries'],    0, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['mseries'],    0, wx.EXPAND|wx.ALL, 0)
        pack(arrowpanel, ssizer)

        self.wids['roilist'] = EditableListBox(ctrlpanel, self.onROI,
                                               right_click=False,
                                               size=(80, 125))

        self.wids['roiname'] = wx.TextCtrl(ctrlpanel, -1, '', size=(140, -1))


        self.wids['newroi'] = Button(ctrlpanel, 'Add', size=(75, -1),
                                         action=self.onNewROI)
        self.wids['delroi'] = Button(ctrlpanel, 'Delete', size=(75, -1),
                                         action=self.onDelROI)

        rtitle1  = txt(ctrlpanel, ' Bins: ')
        rtitle2  = txt(ctrlpanel, ' Energy: ')
        rtitle3  = txt(ctrlpanel, ' Cen/Wid: ')
        self.wids['roi_msg1'] = txt(ctrlpanel, '  ', size=100)
        self.wids['roi_msg2'] = txt(ctrlpanel, '  ', size=100)
        self.wids['roi_msg3'] = txt(ctrlpanel, '  ', size=100)

        ir = 0
        sizer.Add(ptable,  (ir, 0), (1, 4), wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL, 5)

        ir += 1
        sizer.Add(arrowpanel, (ir, 0), (1, 4), labstyle)

        ir += 1
        sizer.Add(lin(ctrlpanel, 195),   (ir, 0), (1, 4), labstyle)

        # roi section...
        ir += 1
        sizer.Add(txt(ctrlpanel, ' Regions of Interest:', size=140),
                  (ir, 0), (1, 2), labstyle)
        sizer.Add(self.wids['roilist'],    (ir, 2), (6, 2), labstyle)

        sizer.Add(self.wids['roiname'],    (ir+1, 0), (1, 2), labstyle)
        sizer.Add(self.wids['newroi'],     (ir+2, 0), (1, 1), wx.ALIGN_CENTER)
        sizer.Add(self.wids['delroi'],     (ir+2, 1), (1, 1), wx.ALIGN_CENTER)
        sizer.Add(rtitle1,                 (ir+3, 0), (1, 1), LEFT)
        sizer.Add(rtitle2,                 (ir+4, 0), (1, 1), LEFT)
        sizer.Add(rtitle3,                 (ir+5, 0), (1, 1), LEFT)

        sizer.Add(self.wids['roi_msg1'],   (ir+3, 1), (1, 1), LEFT)
        sizer.Add(self.wids['roi_msg2'],   (ir+4, 1), (1, 1), LEFT)
        sizer.Add(self.wids['roi_msg3'],   (ir+5, 1), (1, 1), LEFT)

        ir += 6
        sizer.Add(lin(ctrlpanel, 195),       (ir, 0), (1, 4), labstyle)

        ir += 1
        sizer.Add(txt(ctrlpanel, ' Energy Scale:'),  (ir, 0), (1, 2), labstyle)
        sizer.Add(self.wids['zoom_in'],              (ir, 2), (1, 1), ctrlstyle)
        sizer.Add(self.wids['zoom_out'],             (ir, 3), (1, 1), ctrlstyle)
        ir += 1
        sizer.Add(txt(ctrlpanel, ' Counts Scale:'),  (ir, 0), (1, 2), labstyle)
        sizer.Add(self.wids['ylog'],                 (ir, 3), (1, 2), ctrlstyle)

        ir += 1
        sizer.Add(lin(ctrlpanel, 195),   (ir, 0), (1, 4), labstyle)

        self.wids['xray_lines'] = None
        if HAS_DV:
            dvstyle = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES
            xlines = dv.DataViewListCtrl(ctrlpanel, style=dvstyle)
            self.wids['xray_lines'] = xlines
            xlines.AppendTextColumn('Line ',        width=45)
            xlines.AppendTextColumn('Energy (keV)', width=85)
            xlines.AppendTextColumn('Strength',     width=85)
            xlines.AppendTextColumn('Init Level',   width=75)
            for col in (0, 1, 2, 3):
                xlines.Columns[col].Sortable = True
                align = RIGHT
                if col in (0, 3): align = wx.ALIGN_CENTER
                xlines.Columns[col].Renderer.Alignment = align
                xlines.Columns[col].Alignment = RIGHT

            xlines.SetMinSize((300, 200))
            xlines.SetMaxSize((320, 400))
            xlines.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectXrayLine)

            ir += 1
            sizer.Add(xlines,  (ir, 0), (8, 4), wx.GROW|wx.ALL|wx.EXPAND) 

        sizer.SetHGap(1)
        sizer.SetVGap(1)
        ctrlpanel.SetSizer(sizer)
        sizer.Fit(ctrlpanel)
        return ctrlpanel

    def createMainPanel(self):
        ctrlpanel = self.createControlPanel()
        plotpanel = self.panel = self.createPlotPanel()

        tx, ty = self.wids['ptable'].GetBestSize()
        cx, cy = ctrlpanel.GetBestSize()
        px, py = plotpanel.GetBestSize()

        self.SetSize((max(cx, tx)+px, 25+max(cy, py)))

        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(ctrlpanel, 0, style, 3)
        sizer.Add(plotpanel, 1, style, 2)

        pack(self, sizer)
        wx.CallAfter(self.init_larch)
        self.set_roilist(mca=None)

    def init_larch(self):
        if self.larch is None:
            self.larch = Interpreter()
        symtab = self.larch.symtable
        if not symtab.has_symbol('_sys.wx.wxapp'):
            symtab.set_symbol('_sys.wx.wxapp', wx.GetApp())
        if not symtab.has_symbol('_sys.wx.parent'):
            symtab.set_symbol('_sys.wx.parent', self)

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
        if (self.xmarker_left is None or 
            self.xmarker_right is None or self.mca is None):
            return
        label = self.wids['roiname'].GetValue()
        found = False
        for roi in self.mca.rois:
            if roi.name.lower()==label:
                found = True
        left  = self.xmarker_left
        right = self.xmarker_right
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

    def ShowROIStatus(self, roi=None):
        dt = self.mca.real_time
        if roi is None or self.mca is None:
            return 
        counts = roi.get_counts(self.mca.counts)
        if dt is None or dt < 0:
            fmt = " %s : Counts=%10i"
            msg = fmt % (roi.name, counts)
        else:
            fmt = " %s : Counts=%10i  CPS=%8.1f"
            msg = fmt % (roi.name, counts, counts/dt)
        self.write_message(msg, panel=0)            
        
    def onROI(self, event=None, label=None):
        if label is None and event is not None:
            label = event.GetString()
        self.wids['roiname'].SetValue(label)
        name, left, right= None, -1, -1
        label = label.lower().strip()
        self.selected_roi = None
        fmt = "%s : Counts= %i"
        if self.mca is not None:
            for roi in self.mca.rois:
                if roi.name.lower()==label:
                    left, right, name = roi.left, roi.right, roi.name
                    elo  = self.mca.energy[left]
                    ehi  = self.mca.energy[right]
                    self.selected_roi = roi
                    break
        if name is None or right == -1:
            return

        self.ShowROIStatus(roi)
        
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
        roi_msg1 = '[%6i: %6i]' % (left, right)
        roi_msg2 = '[%6.3f: %6.3f]' % (elo, ehi)
        roi_msg3 = ' %6.3f/ %6.3f ' % ((elo+ehi)/2., (ehi - elo))
        
        fill = self.panel.axes.fill_between
        self.roi_patch  = fill(e, r, color=self.conf.roi_fillcolor, zorder=-10)
        self.energy_for_zoom = (elo+ehi)/2.0

        self.wids['roi_msg1'].SetLabel(roi_msg1)
        self.wids['roi_msg2'].SetLabel(roi_msg2)
        self.wids['roi_msg3'].SetLabel(roi_msg3)

        self.panel.canvas.draw()
        self.panel.Refresh()

    def onSaveROIs(self):
        pass
    
    def onRestoreROIs(self):
        pass
    
    def createCustomMenus(self):
        return

    def createBaseMenus(self):
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "&Read MCA Spectra File\tCtrl+O",
                 "Read GSECARS MCA File",  self.onReadMCAFile)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "&Save MCA File\tCtrl+S",
                 "Save GSECARS MCA File",  self.onSaveMCAFile)
        MenuItem(self, fmenu, "&Save ASCII Column File\tCtrl+A",
                 "Save Column File",  self.onSaveColumnFile)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "Save ROIs to File",
                 "Save ROIs to File",  self.onSaveROIs)
        MenuItem(self, fmenu, "Read ROIs File",
                 "Read ROIs from File",  self.onRestoreROIs)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu,  "&Save Plot\tCtrl+I",
                 "Save PNG Image of Plot", self.onSavePNG)
        MenuItem(self, fmenu, "&Copy Plot\tCtrl+C",
                 "Copy Plot Image to Clipboard",
                 self.onCopyImage)
        MenuItem(self, fmenu, 'Page Setup...', 'Printer Setup', self.onPageSetup)
        MenuItem(self, fmenu, 'Print Preview...', 'Print Preview', self.onPrintPreview)
        MenuItem(self, fmenu, "&Print\tCtrl+P", "Print Plot", self.onPrint)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "&Quit\tCtrl+Q",
                  "Quit program", self.onExit)

        omenu = wx.Menu()
        MenuItem(self, omenu, "Configure Colors",
                 "Configure Colors", self.config_colors)
        MenuItem(self, omenu, "Configure X-ray Lines",
                 "Configure which X-ray Lines are shown", self.config_xraylines)

        omenu.AppendSeparator()
        MenuItem(self, omenu, "Hide X-ray Lines",
                 "Hide all X-ray Lines", self.clear_lines)
        MenuItem(self, omenu, "Hide selected ROI ",
                 "Hide selected ROI", self.clear_roihighlight)
        MenuItem(self, omenu, "Hide Markers ",
                 "Hide cursor markers", self.clear_markers)
        MenuItem(self, omenu, "Hide XRF Background ",
                 "Hide cursor markers", self.clear_background)

        omenu.AppendSeparator()
        MenuItem(self, omenu, "Configure Plot\tCtrl+K",
                 "Configure Plot Colors, etc", self.panel.configure)
        MenuItem(self, omenu, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range", self.unzoom_all)
        omenu.AppendSeparator()
        MenuItem(self, omenu, "Swap MCA and Background MCA",
                 "Swap Foreground and Background MCAs", self.swap_mcas)
        MenuItem(self, omenu, "Close Background MCA",
                 "Close Background MCA", self.close_bkg_mca)

        amenu = wx.Menu()
        MenuItem(self, amenu, "&Calibrate Energy\tCtrl+E",
                 "Calibrate Energy",  self.onCalibrateEnergy)
        MenuItem(self, amenu, "Fit Peaks\tCtrl+F",
                 "Fit Peaks in spectra",  self.onFitPeaks)
        self._menus = [(fmenu, '&File'),
                       (omenu, '&Options'),
                       (amenu, '&Analysis')]
        
    def createMenus(self):
        self.menubar = wx.MenuBar()
        self.createBaseMenus()
        self.createCustomMenus()
        for menu, title in self._menus:
            self.menubar.Append(menu, title)
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

    def config_colors(self, event=None):
        """show configuration frame"""
        try:
            self.win_config.Raise()
        except:
            self.win_config = ColorsFrame(parent=self)

    def config_xraylines(self, event=None):
        """show configuration frame"""
        try:
            self.win_config.Raise()
        except:
            self.win_config = XrayLinesFrame(parent=self)

    def onKLM(self, event=None):
        """selected K, L, or M Markers"""
        if self.selected_elem is not None:
            self.onShowLines(elem = self.selected_elem)

    def onSelectXrayLine(self, evt=None):
        if self.wids['xray_lines'] is None:
            return
        if not self.wids['xray_lines'].HasSelection():
            return
        item = self.wids['xray_lines'].GetSelection().GetID()
        en = self.wids['xray_linesdata'][item]

        if self.highlight_xrayline is not None:
            self.highlight_xrayline.remove()

        self.energy_for_zoom = en
        self.highlight_xrayline = self.panel.axes.axvline(en,
                             color=self.conf.emph_elinecolor,
                             linewidth=2.5, zorder=-20)
        self.panel.canvas.draw()


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
        xlines = self.wids['xray_lines']
        if xlines is not None:
            xlines.DeleteAllItems()
        self.wids['xray_linesdata'] = [0]
        minors, majors = [], []
        conf = self.conf
        line_data = {}
        for line in (conf.K_major+conf.K_minor+conf.L_major+
                     conf.L_minor+conf.M_major):
            line_data[line] = line, -1, 0, ''
            if line in elines:
                dat = elines[line]
                line_data[line] = line, dat[0], dat[1], dat[2]

        if self.wids['kseries'].IsChecked():
            majors.extend([line_data[l] for l in conf.K_major])
            minors.extend([line_data[l] for l in conf.K_minor])
        if self.wids['lseries'].IsChecked():
            majors.extend([line_data[l] for l in conf.L_major])
            minors.extend([line_data[l] for l in conf.L_minor])
        if self.wids['mseries'].IsChecked():
            majors.extend([line_data[l] for l in conf.M_major])

        erange = [max(conf.e_min, self.xdata.min()),
                  min(conf.e_max, self.xdata.max())]
        for label, eev, frac, ilevel in majors:
            e = float(eev) * 0.001
            if (e >= erange[0] and e <= erange[1]):
                l = vline(e, color= self.conf.major_elinecolor,
                          linewidth=1.50, zorder=-4)
                l.set_label(label)
                dat = (label, "%.4f" % e, "%.4f" % frac, ilevel)
                self.wids['xray_linesdata'].append(e)
                if xlines is not None:
                    xlines.AppendItem(dat)

                self.major_markers.append(l)
                if self.energy_for_zoom is None:
                    self.energy_for_zoom = e

        for label, eev, frac, ilevel in minors:
            e = float(eev) * 0.001
            if (e >= erange[0] and e <= erange[1]):
                l = vline(e, color= self.conf.minor_elinecolor,
                          linewidth=1.25, zorder=-6)
                l.set_label(label)
                dat = (label, "%.4f" % e, "%.4f" % frac, ilevel)
                self.wids['xray_linesdata'].append(e)
                if xlines is not None:
                    xlines.AppendItem(dat)
                self.minor_markers.append(l)



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
        if self.y2data is not None:
            self.oplot(self.x2data, self.y2data)

    def plotmca(self, mca, title=None, as_mca2=False, **kws):
        if as_mca2:
            self.mca2 = mca
        else:
            self.mca = mca
        user_title = title
        
        # print 'PLOT MCA ', self.mca, self.mca2
        if self.mca is not None:
            if hasattr(self.mca, 'title'):
                title = self.mca.title
            elif hasattr(self.mca, 'filename'):
                title = "%s: %s"% (title, self.mca.filename)
            try:
                self.plot(self.mca.energy, self.mca.counts,
                          mca=self.mca, **kws)
            except ValueError:
                pass
        if as_mca2:
            if hasattr(self.mca2, 'title'):
                title = "%s / bg=%s" % (title, self.mca2.title)
            elif  hasattr(self.mca2, 'filename'):
                title = "%s / bg=%s"% (title, self.mca2.filename)

            self.oplot(self.mca2.energy, self.mca2.counts,
                       mca=self.mca2, **kws)
        if user_title is not None:
            title = user_title
        if title is None:
            title = self.win_title
        self.SetTitle(title)

       
    def plot(self, x, y=None, mca=None, **kws):
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
        ydat = 1.0*y[:] + 1.e-9
        kwargs['ymax'] = max(ydat)*1.25
        kwargs['ymin'] = 0.90

        if mca is not None:
            if not self.rois_shown:
                self.set_roilist(mca=mca)
            yroi = -1*np.ones(len(y))
            for r in mca.rois:
                yroi[r.left:r.right] = y[r.left:r.right]
                ydat[r.left+1:r.right-1] = -1
            yroi = np.ma.masked_less(yroi, 0)
            ydat = np.ma.masked_less(ydat, 0)

        if ydat.max() > 0:
            panel.plot(x, ydat, label='spectra',  **kwargs)
        if yroi is not None and yroi.max() > 0:
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

    def update_mca(self, counts, energy=None, with_rois=True,
                   is_mca2=False, draw=True):
        """update counts (and optionally energy) for mca, and update plot"""
        mca = self.mca
        ix = 0
        if is_mca2:
            mca = self.mca2
            ix = 2
        mca.counts = counts[:] 

        if energy is not None:
            mca.energy = energy[:]
        nrois = len(mca.rois)
        if not is_mca2 and with_rois and nrois > 0:
            yroi = -1*np.ones(len(counts))
            for r in mca.rois:
                yroi[r.left:r.right] = counts[r.left:r.right]
            self.panel.update_line(1, mca.energy, yroi, draw=False,
                                   update_limits=False)

        self.panel.update_line(ix, mca.energy, counts, 
                               draw=False, update_limits=False)

        max_counts = max_counts2 = max(self.mca.counts)
        try:
            max_counts2 = max(self.mca2.counts)
        except:
            pass
        
        self.panel.axes.set_ylim(1, 1.25*max(max_counts, max_counts2))
        if mca == self.mca:
            self.ydata = 1.0*counts[:]
        self.update_status()
        if draw:
            try:
                self.panel.canvas.draw()
            except:
                pass

    def oplot(self, x, y, color='darkgreen', mca=None, zorder=-5, **kws):
        if mca is not None:
            self.mca2 = mca

        self.x2data = 1.0*x[:]
        self.y2data = 1.0*y[:]
        if hasattr(self, 'ydata'):
            ymax = max(max(self.ydata), max(y))*1.25
        else:
            ymax = max(y)*1.25

        kws.update({'zorder': zorder, 'label': 'spectra2',
                    'ymax' : ymax,
                    'axes_style': 'bottom',
                    'ylog_scale': self.ylog_scale,
                    'grid': False})
        self.panel.oplot(self.x2data, self.y2data, color=color, **kws)

    def swap_mcas(self, event=None):
        if self.mca2 is None:
            return
        self.mca, self.mca2 = self.mca2, self.mca
        self.plotmca(self.mca)
        self.plotmca(self.mca2, as_mca2=True)

    def close_bkg_mca(self, event=None):
        self.mca2 = None
        self.plotmca(self.mca)

            
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

        setattr(self._mcagroup, 'mca1', self.mca)
        setattr(self._mcagroup, 'mca2', self.mca2)
        self.plotmca(self.mca, show_mca2=True)

    def onReadGSEXRMFile(self, event=None, **kws):
        print( '  onReadGSEXRMFile   ')
        pass

    def onOpenEpicsMCA(self, event=None, **kws):
        print( '  onOpenEpicsMCA   ')
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
        print( '  onSaveColumnFile   ')
        pass

    def onCalibrateEnergy(self, event=None, **kws):
        try:
            self.win_calib.Raise()
        except:
            self.win_calib = CalibrationFrame(self, mca=self.mca,
                                              larch=self.larch)

    def onFitPeaks(self, event=None, **kws):
        try:
            self.win_fit.Raise()
        except:
            self.win_fit = FitSpectraFrame(self)

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
        path, re1ad = None, False
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
        return True

if __name__ == "__main__":
    XRFApp().MainLoop()
