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
import wx.dataview as dv
import wx.lib.colourselect  as csel

try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception


import numpy as np
import matplotlib
from matplotlib.ticker import LogFormatter, FuncFormatter

from wxmplot import PlotPanel

from wxutils import (SimpleText, EditableListBox, Font, pack, Popup,
                     get_icon, SetTip, Button, Check, MenuItem, Choice,
                     FileOpen, FileSave, fix_filename, HLine, GridPanel,
                     CEN, LEFT, RIGHT)

from ..math import index_of
from ..utils import bytes2str, debugtime
from ..io import GSEMCA_File
from ..site_config import icondir
from ..interpreter import Interpreter

from .gui_utils import LarchWxApp
from .larchframe import LarchFrame
from .periodictable import PeriodicTablePanel

from .xrfdisplay_utils import (XRFCalibrationFrame, ColorsFrame,
                               XrayLinesFrame, XRFDisplayConfig, XRFGROUP,
                               MAKE_XRFGROUP_CMD, next_mcaname)

from .xrfdisplay_fitpeaks import FitSpectraFrame

FILE_WILDCARDS = "MCA File (*.mca)|*.mca|All files (*.*)|*.*"
FILE_ALREADY_READ = """The File
   '%s'
has already been read.
"""

ICON_FILE = 'ptable.ico'

read_mcafile = "# {group:s}.{name:s} = read_gsemca('{filename:s}')"

def txt(panel, label, size=75, colour=None, font=None, style=None):
    if style is None:
        style = wx.ALIGN_LEFT|wx.ALL|wx.GROW
    if colour is None:
        colour = wx.Colour(0, 0, 50)
    this = SimpleText(panel, label, size=(size, -1),
                      colour=colour, style=style)
    if font is not None: this.SetFont(font)
    return this

def lin(panel, len=30, wid=2, style=wx.LI_HORIZONTAL):
    return wx.StaticLine(panel, size=(len, wid), style=style)


class XRFDisplayFrame(wx.Frame):
    _about = """XRF Spectral Viewer
  Matt Newville <newville @ cars.uchicago.edu>
  """
    main_title = 'XRF Display'
    def __init__(self, _larch=None, parent=None, filename=None,
                 size=(725, 450), axissize=None, axisbg=None,
                 title='XRF Display', exit_callback=None,
                 output_title='XRF', **kws):

        if size is None: size = (725, 450)
        wx.Frame.__init__(self, parent=parent,
                          title=title, size=size,  **kws)
        self.conf = XRFDisplayConfig()
        self.subframes = {}
        self.data = None
        self.title = title
        self.plotframe = None
        self.wids = {}
        self.larch = _larch
        if isinstance(self.larch, Interpreter):  # called from shell
            self.larch_buffer = None
        else:
            self.larch_buffer = parent
            if not isinstance(parent, LarchFrame):
                self.larch_buffer = LarchFrame(_larch=self.larch,
                                               is_standalone=False, with_raise=False)
                self.subframes['larchframe'] = self.larch_buffer
            self.larch = self.larch_buffer.larchshell
        self.init_larch()

        self.exit_callback = exit_callback
        self.roi_patch = None
        self.selected_roi = None
        self.roilist_sel  = None
        self.selected_elem = None
        self.mca = None
        self.mca2 = None
        self.xdata = np.arange(2048)*0.01
        self.ydata = np.ones(2048)*1.e-4
        self.x2data = None
        self.y2data = None
        self.rois_shown = False
        self.mca_index = 0
        self.major_markers = []
        self.minor_markers = []
        self.hold_markers = []

        self.hold_lines = None
        self.saved_lines = None
        self.energy_for_zoom = None
        self.xview_range = None
        self.show_yaxis = False
        self.xmarker_left = None
        self.xmarker_right = None

        self.highlight_xrayline = None
        self.highlight_xrayline = None
        self.cursor_markers = [None, None]
        self.ylog_scale = True
        self.SetTitle("%s: %s " % (self.main_title, title))

        self._menus = []
        self.createMainPanel()
        self.createMenus()
        self.SetFont(Font(9, serif=True))
        self.statusbar = self.CreateStatusBar(4)
        self.statusbar.SetStatusWidths([-5, -3, -3, -4])
        statusbar_fields = ["XRF Display", " ", " ", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)
        if filename is not None:
            self.add_mca(GSEMCA_File(filename), filename=filename, plot=True)


    def ignoreEvent(self, event=None):
        pass

    def on_cursor(self, event=None, side='left'):
        if event is None:
            return
        x, y  = event.xdata, event.ydata
        if len(self.panel.fig.axes) > 1:
            try:
                x, y = self.panel.axes.transData.inverted().transform((event.x, event.y))
            except:
                pass
        ix = x
        if self.mca is not None:
            try:
                ix = index_of(self.mca.energy, x)
            except TypeError:
                pass

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
        self.draw()

    def clear_lines(self, evt=None):
        "remove all Line Markers"
        for m in self.major_markers + self.minor_markers + self.hold_markers:
            try:
                m.remove()
            except:
                pass
        if self.highlight_xrayline is not None:
            try:
                self.highlight_xrayline.remove()
            except:
                pass

        self.highlight_xrayline = None
        self.major_markers = []
        self.minor_markers = []
        self.hold_markers = []
        self.draw()

    def draw(self):
        try:
            self.panel.canvas.draw()
        except:
            pass

    def clear_markers(self, evt=None):
        "remove all Cursor Markers"
        for m in self.cursor_markers:
            if m is not None:
                m.remove()
        self.cursor_markers = [None, None]
        self.xmarker_left  = None
        self.xmarker_right = None
        self.draw()

    def clear_background(self, evt=None):
        "remove XRF background"
        self.mca2 = None
        self.plotmca(self.mca)

    def update_status(self):
        fmt = "{:s}:{:}, E={:.3f}, Cts={:,.0f}".format
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
            self.cursor_markers[idx] = axes.axvline(x, y1, y2, linewidth=2.5,
                                                    color=self.conf.marker_color)

        if self.xmarker_left is not None:
            ix = self.xmarker_left
            x, y = self.xdata[ix],  self.ydata[ix]
            draw_ymarker_range(0, x, y)
            self.write_message(fmt("L", ix, x, y), panel=1)
        if self.xmarker_right is not None:
            ix = self.xmarker_right
            x, y = self.xdata[ix],  self.ydata[ix]
            draw_ymarker_range(1, x, y)
            self.write_message(fmt("R", ix, x, y), panel=2)

        if self.mca is None:
            return

        if (self.xmarker_left is not None and
            self.xmarker_right is not None):
            self.ShowROIStatus(self.xmarker_left,
                               self.xmarker_right,
                               name='', panel=3)

        if self.selected_roi is not None:
            roi = self.selected_roi
            left, right = roi.left, roi.right
            self.ShowROIStatus(left, right, name=roi.name, panel=0)
            self.ShowROIPatch(left, right)

    def createPlotPanel(self):
        """mca plot window"""
        pan = PlotPanel(self, fontsize=7, axisbg='#FFFFFF',
                        with_data_process=False,
                        output_title='test.xrf',
                        messenger=self.write_message)
        pan.SetSize((650, 350))
        
        pan.conf.grid_color='#E5E5C0'
        pan.conf.show_grid = False
        pan.conf.canvas.figure.set_facecolor('#FCFCFE')
        pan.conf.labelfont.set_size(6)
        pan.conf.labelfont.set_size(6)
        pan.onRightDown= partial(self.on_cursor, side='right')
        pan.add_cursor_mode('zoom',  motion = self.ignoreEvent,
                            leftup   = self.ignoreEvent,
                            leftdown = self.on_cursor,
                            rightdown = partial(self.on_cursor, side='right'))
        return pan

    def createControlPanel(self):
        ctrlpanel = wx.Panel(self, name='Ctrl Panel')

        ptable = PeriodicTablePanel(ctrlpanel, onselect=self.onShowLines,
                                    tooltip_msg='Select Element for KLM Lines',
                                    fontsize=10)
        self.wids['ptable'] = ptable

        labstyle = wx.ALIGN_LEFT|wx.EXPAND
        ctrlstyle = wx.ALIGN_LEFT
        txtstyle=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE|wx.TE_PROCESS_ENTER
        Font9  = Font(9)
        Font10 = Font(10)
        Font11 = Font(11)
        #
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
            ssizer.Add(self.wids[wname],  0, wx.EXPAND|wx.ALL)

        self.wids['holdbtn'] = wx.ToggleButton(arrowpanel, -1, 'Hold   ',
                                               size=(85, -1))
        self.wids['holdbtn'].Bind(wx.EVT_TOGGLEBUTTON, self.onToggleHold)
        self.wids['kseries'] = Check(arrowpanel, ' K ', action=self.onKLM)
        self.wids['lseries'] = Check(arrowpanel, ' L ', action=self.onKLM)
        self.wids['mseries'] = Check(arrowpanel, ' M ', action=self.onKLM)

        ssizer.Add(self.wids['holdbtn'],    0, wx.EXPAND|wx.ALL, 2)
        ssizer.Add(self.wids['kseries'],    0, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['lseries'],    0, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['mseries'],    0, wx.EXPAND|wx.ALL, 0)
        pack(arrowpanel, ssizer)

        # roi section...
        rsizer = wx.GridBagSizer(4, 6)
        roipanel = wx.Panel(ctrlpanel, name='ROI Panel')
        self.wids['roilist'] = wx.ListBox(roipanel, size=(140, 150))
        self.wids['roilist'].Bind(wx.EVT_LISTBOX, self.onROI)
        self.wids['roilist'].SetMinSize((140, 150))
        self.wids['roiname'] = wx.TextCtrl(roipanel, -1, '', size=(150, -1))

        #
        roibtns= wx.Panel(roipanel, name='ROIButtons')
        zsizer = wx.BoxSizer(wx.HORIZONTAL)
        z1 = Button(roibtns, 'Add',    size=(70, 30), action=self.onNewROI)
        z2 = Button(roibtns, 'Delete', size=(70, 30), action=self.onConfirmDelROI)
        z3 = Button(roibtns, 'Rename', size=(70, 30), action=self.onRenameROI)

        zsizer.Add(z1,    0, wx.EXPAND|wx.ALL, 0)
        zsizer.Add(z2,    0, wx.EXPAND|wx.ALL, 0)
        zsizer.Add(z3,    0, wx.EXPAND|wx.ALL, 0)
        pack(roibtns, zsizer)

        rt1 = txt(roipanel, ' Channels:', size=80, font=Font10)
        rt2 = txt(roipanel, ' Energy:',   size=80, font=Font10)
        rt3 = txt(roipanel, ' Cen, Wid:',  size=80, font=Font10)
        m = ''
        self.wids['roi_msg1'] = txt(roipanel, m, size=135, font=Font10)
        self.wids['roi_msg2'] = txt(roipanel, m, size=135, font=Font10)
        self.wids['roi_msg3'] = txt(roipanel, m, size=135, font=Font10)

        rsizer.Add(txt(roipanel, ' Regions of Interest:', size=125, font=Font11),
                   (0, 0), (1, 3), labstyle)
        rsizer.Add(self.wids['roiname'],    (1, 0), (1, 3), labstyle)
        rsizer.Add(roibtns,                 (2, 0), (1, 3), labstyle)
        rsizer.Add(rt1,                     (3, 0), (1, 1), LEFT)
        rsizer.Add(rt2,                     (4, 0), (1, 1), LEFT)
        rsizer.Add(rt3,                     (5, 0), (1, 1), LEFT)
        rsizer.Add(self.wids['roi_msg1'],   (3, 1), (1, 2), labstyle)
        rsizer.Add(self.wids['roi_msg2'],   (4, 1), (1, 2), labstyle)
        rsizer.Add(self.wids['roi_msg3'],   (5, 1), (1, 2), labstyle)
        rsizer.Add(self.wids['roilist'],    (0, 3), (6, 1),
                   wx.EXPAND|wx.ALL|wx.ALIGN_RIGHT)
        rsizer.SetHGap(1)

        pack(roipanel, rsizer)
        # end roi section

        # y scale
        yscalepanel = wx.Panel(ctrlpanel, name='YScalePanel')
        ysizer = wx.BoxSizer(wx.HORIZONTAL)
        ytitle = txt(yscalepanel, ' Y Axis:', font=Font10, size=80)
        yspace = txt(yscalepanel, ' ', font=Font10, size=20)
        ylog   = Choice(yscalepanel, size=(80, 30), choices=['log', 'linear'],
                      action=self.onLogLinear)
        yaxis  = Check(yscalepanel, ' Show Y Scale ', action=self.onYAxis,
                      default=False)
        self.wids['show_yaxis'] = yaxis
        ysizer.Add(ytitle,  0, wx.ALL, 0)
        ysizer.Add(ylog,    0, wx.EXPAND|wx.ALL, 0)
        ysizer.Add(yspace,  0, wx.EXPAND|wx.ALL, 0)
        ysizer.Add(yaxis,   0, wx.EXPAND|wx.ALL, 0)
        pack(yscalepanel, ysizer)

        # zoom buttons
        zoompanel = wx.Panel(ctrlpanel, name='ZoomPanel')
        zsizer = wx.BoxSizer(wx.HORIZONTAL)
        z1 = Button(zoompanel, 'Zoom In',   size=(80, 30), action=self.onZoomIn)
        z2 = Button(zoompanel, 'Zoom Out',  size=(80, 30), action=self.onZoomOut)
        p1 = Button(zoompanel, 'Pan Lo',    size=(75, 30), action=self.onPanLo)
        p2 = Button(zoompanel, 'Pan Hi',    size=(75, 30), action=self.onPanHi)

        zsizer.Add(p1,      0, wx.EXPAND|wx.ALL, 0)
        zsizer.Add(p2,      0, wx.EXPAND|wx.ALL, 0)
        zsizer.Add(z1,      0, wx.EXPAND|wx.ALL, 0)
        zsizer.Add(z2,      0, wx.EXPAND|wx.ALL, 0)
        pack(zoompanel, zsizer)

        self.wids['xray_lines'] = None

        dvstyle = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES
        xlines = dv.DataViewListCtrl(ctrlpanel, style=dvstyle)
        self.wids['xray_lines'] = xlines
        xlines.AppendTextColumn(' Line ',         width=60)
        xlines.AppendTextColumn(' Energy(keV) ',  width=110)
        xlines.AppendTextColumn(' Strength ',     width=85)
        xlines.AppendTextColumn(' Levels ',       width=75)
        for col in (0, 1, 2, 3):
            this = xlines.Columns[col]
            this.Sortable = True
            align = RIGHT
            if col in (0, 3):
                align = wx.ALIGN_LEFT
            this.Alignment = this.Renderer.Alignment = align

        xlines.SetMinSize((300, 240))
        xlines.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED,
                    self.onSelectXrayLine)
        store = xlines.GetStore()

        # main layout
        # may have to adjust comparison....

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(roipanel,            0, labstyle)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)
        sizer.Add(yscalepanel,         0, wx.EXPAND|wx.ALL)
        sizer.Add(zoompanel,           0, wx.EXPAND|wx.ALL)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)
        sizer.Add(ptable,              0, wx.EXPAND|wx.ALL, 4)
        sizer.Add(arrowpanel,          0, labstyle)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)

        if self.wids['xray_lines'] is not None:
            sizer.Add(xlines,  0, wx.GROW|wx.ALL|wx.EXPAND)

        pack(ctrlpanel, sizer)
        return ctrlpanel

    def createMainPanel(self):
        ctrlpanel = self.createControlPanel()
        plotpanel = self.panel = self.createPlotPanel()
        plotpanel.yformatter = self._formaty

        tx, ty = self.wids['ptable'].GetBestVirtualSize()
        cx, cy = ctrlpanel.GetBestVirtualSize()
        px, py = plotpanel.GetBestVirtualSize() # (650, 350)
        self.SetSize((max(cx, tx)+px, 25+max(cy, py)))

        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(ctrlpanel, 0, style, 3)
        sizer.Add(plotpanel, 1, style, 2)

        self.SetMinSize((450, 150))
        pack(self, sizer)
        self.set_roilist(mca=None)

    def init_larch(self):
        symtab = self.larch.symtable
        if not symtab.has_symbol('_sys.wx.wxapp'):
            symtab.set_symbol('_sys.wx.wxapp', wx.GetApp())
        if not symtab.has_symbol('_sys.wx.parent'):
            symtab.set_symbol('_sys.wx.parent', self)

        if not symtab.has_group(XRFGROUP):
            self.larch.eval(MAKE_XRFGROUP_CMD)

        fico = os.path.join(icondir, ICON_FILE)
        try:
            self.SetIcon(wx.Icon(fico, wx.BITMAP_TYPE_ICO))
        except:
            pass

    def add_mca(self, mca, filename=None, label=None, as_mca2=False, plot=True):
        if as_mca2:
            self.mca2 = mca
        else:
            self.mca2 = self.mca
            self.mca = mca

        xrfgroup = self.larch.symtable.get_group(XRFGROUP)
        mcaname = next_mcaname(self.larch)
        if filename is not None:
            self.larch.eval(read_mcafile.format(group=XRFGROUP,
                                                name=mcaname,
                                                filename=filename))
            if label is None:
                label = filename
        if label is None and mca.filename is not None:
            label = mca.filename
        if label is None:
            label = mcaname
        self.mca.label = label
        # push mca to mca2, save id of this mca
        setattr(xrfgroup, '_mca2', getattr(xrfgroup, '_mca', ''))
        setattr(xrfgroup, '_mca', mcaname)
        setattr(xrfgroup, mcaname, mca)
        if plot:
            self.plotmca(self.mca)
            if as_mca2:
                self.plotmca(self.mca, as_mca2=True)

    def _getlims(self):
        emin, emax = self.panel.axes.get_xlim()
        erange = emax-emin
        emid   = (emax+emin)/2.0
        if self.energy_for_zoom is not None:
            emid = self.energy_for_zoom
        dmin, dmax = emin, emax
        drange = erange
        if self.mca is not None:
            dmin, dmax = self.mca.energy.min(), self.mca.energy.max()
        return (emid, erange, dmin, dmax)

    def _set_xview(self, e1, e2, keep_zoom=False):
        if not keep_zoom:
            self.energy_for_zoom = (e1+e2)/2.0
        self.panel.axes.set_xlim((e1, e2))
        self.xview_range = [e1, e2]
        self.draw()

    def onPanLo(self, event=None):
        emid, erange, dmin, dmax = self._getlims()
        e1 = max(dmin, emid-0.9*erange)
        e2 = min(dmax, e1 + erange)
        self._set_xview(e1, e2)

    def onPanHi(self, event=None):
        emid, erange, dmin, dmax = self._getlims()
        e2 = min(dmax, emid+0.9*erange)
        e1 = max(dmin, e2-erange)
        self._set_xview(e1, e2)

    def onZoomIn(self, event=None):
        emid, erange, dmin, dmax = self._getlims()
        e1 = max(dmin, emid-erange/3.0)
        e2 = min(dmax, emid+erange/3.0)
        self._set_xview(e1, e2, keep_zoom=True)

    def onZoomOut(self, event=None):
        emid, erange, dmin, dmax = self._getlims()
        e1 = max(dmin, emid-1.25*erange)
        e2 = min(dmax, emid+1.25*erange)
        self._set_xview(e1, e2)

    def unzoom_all(self, event=None):
        emid, erange, dmin, dmax = self._getlims()
        self._set_xview(dmin, dmax)
        self.xview_range = None

    def toggle_grid(self, event=None):
        self.panel.toggle_grid()

    def set_roilist(self, mca=None):
        """ Add Roi names to roilist"""
        self.wids['roilist'].Clear()
        if mca is not None:
            for roi in mca.rois:
                name = bytes2str(roi.name.strip())
                if len(name) > 0:
                    self.wids['roilist'].Append(roi.name)

    def clear_roihighlight(self, event=None):
        self.selected_roi = None
        try:
            self.roi_patch.remove()
        except:
            pass
        self.roi_patch = None
        self.wids['roiname'].SetValue('')
        self.draw()

    def get_roiname(self):
        roiname = self.wids['roiname'].GetValue()
        if len(roiname) < 1:
            roiname = 'ROI 1'
            names = [str(r.name.lower()) for r in self.mca.rois]
            if str(roiname.lower()) in names:
                ix = 1
                while str(roiname.lower()) in names:
                    roiname = "ROI %i" % (ix)
                    ix += 1
        return roiname

    def onNewROI(self, event=None):
        if (self.xmarker_left is None or
            self.xmarker_right is None or self.mca is None):
            return
        roiname = self.get_roiname()

        names = [str(r.name.lower()) for r in self.mca.rois]
        if str(roiname.lower()) in names:
            msg = "Overwrite Definition of ROI {:s}?".format(roiname)
            if (wx.ID_YES != Popup(self, msg, 'Overwrite ROI?', style=wx.YES_NO)):
                return False

        left, right  = self.xmarker_left, self.xmarker_right
        if left > right:
            left, right = right, left
        self.mca.add_roi(name=roiname, left=left, right=right, sort=True)
        self.set_roilist(mca=self.mca)
        for roi in self.mca.rois:
            if roi.name.lower()==roiname:
                selected_roi = roi
        self.plot(self.xdata, self.ydata)
        self.onROI(label=roiname)
        if self.selected_elem is not None:
            self.onShowLines(elem=self.selected_elem)
        return True

    def onConfirmDelROI(self, event=None):
        roiname = self.wids['roiname'].GetValue()
        msg = "Delete ROI {:s}?".format(roiname)
        if (wx.ID_YES == Popup(self, msg,   'Delete ROI?', style=wx.YES_NO)):
            self.onDelROI()

    def onRenameROI(self, event=None):
        roiname = self.get_roiname()

        if self.roilist_sel is not None:
            names = self.wids['roilist'].GetStrings()
            names[self.roilist_sel] = roiname
            self.wids['roilist'].Clear()
            for sname in names:
                self.wids['roilist'].Append(sname)
            self.wids['roilist'].SetSelection(self.roilist_sel)

    def onDelROI(self):
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

    def ShowROIStatus(self, left, right, name='', panel=0):
        if left > right:
            return
        sum = self.ydata[left:right].sum()
        dt = self.mca.real_time
        nmsg, cmsg, rmsg = '', '', ''
        if len(name) > 0:
            nmsg = " %s" % name
        cmsg = " Cts={:10,.0f}".format(sum)
        if dt is not None and dt > 1.e-9:
            rmsg = " CPS={:10,.1f}".format(sum/dt)
        self.write_message("%s%s%s" % (nmsg, cmsg, rmsg), panel=panel)

    def ShowROIPatch(self, left, right):
        """show colored XRF Patch:
        Note: ROIs larger than half the energy are not colored"""
        # xnpts = 1.0/len(self.mca.energy)
        # if xnpts*(right - left) > 0.5:
        #    return

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
        self.roi_patch = self.panel.axes.fill_between(e, r, zorder=-20,
                                           color=self.conf.roi_fillcolor)

    def onROI(self, event=None, label=None):
        if label is None and event is not None:
            label = event.GetString()
            self.roilist_sel = event.GetSelection()

        self.wids['roiname'].SetValue(label)
        name, left, right= None, -1, -1
        label = bytes2str(label.lower().strip())

        self.selected_roi = None
        if self.mca is not None:
            for roi in self.mca.rois:
                if bytes2str(roi.name.lower())==label:
                    left, right, name = roi.left, roi.right, roi.name
                    elo  = self.mca.energy[left]
                    ehi  = self.mca.energy[right]
                    self.selected_roi = roi
                    break
        if name is None or right == -1:
            return

        self.ShowROIStatus(left, right, name=name)
        self.ShowROIPatch(left, right)

        roi_msg1 = '[{:}:{:}]'.format(left, right)
        roi_msg2 = '[{:6.3f}:{:6.3f}]'.format(elo, ehi)
        roi_msg3 = '{:6.3f}, {:6.3f}'.format((elo+ehi)/2., (ehi - elo))

        self.energy_for_zoom = (elo+ehi)/2.0

        self.wids['roi_msg1'].SetLabel(roi_msg1)
        self.wids['roi_msg2'].SetLabel(roi_msg2)
        self.wids['roi_msg3'].SetLabel(roi_msg3)

        self.draw()
        self.panel.Refresh()

    def onSaveROIs(self, event=None):
        pass

    def onRestoreROIs(self, event=None):
        pass

    def createCustomMenus(self):
        return

    def createBaseMenus(self):
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "&Read MCA Spectra File\tCtrl+O",
                 "Read GSECARS MCA File",  self.onReadMCAFile)

        MenuItem(self, fmenu, "&Save MCA File\tCtrl+S",
                 "Save GSECARS MCA File",  self.onSaveMCAFile)
        MenuItem(self, fmenu, "&Save ASCII Column File\tCtrl+A",
                 "Save Column File",  self.onSaveColumnFile)

        fmenu.AppendSeparator()
        # MenuItem(self, fmenu, "Save ROIs to File",
        #         "Save ROIs to File",  self.onSaveROIs)
        # MenuItem(self, fmenu, "Restore ROIs File",
        #         "Read ROIs from File",  self.onRestoreROIs)
        # fmenu.AppendSeparator()
        MenuItem(self, fmenu, 'Show Larch Buffer\tCtrl+L',
                 'Show Larch Programming Buffer',
                 self.onShowLarchBuffer)
        MenuItem(self, fmenu,  "Save Plot\tCtrl+I",
                 "Save PNG Image of Plot", self.onSavePNG)
        MenuItem(self, fmenu, "&Copy Plot\tCtrl+C",
                 "Copy Plot Image to Clipboard",
                 self.onCopyImage)
        MenuItem(self, fmenu, 'Page Setup...', 'Printer Setup', self.onPageSetup)
        MenuItem(self, fmenu, 'Print Preview...', 'Print Preview', self.onPrintPreview)
        MenuItem(self, fmenu, "&Print\tCtrl+P", "Print Plot", self.onPrint)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)

        omenu = wx.Menu()
        MenuItem(self, omenu, "Configure Colors",
                 "Configure Colors", self.config_colors)
        MenuItem(self, omenu, "Configure X-ray Lines",
                 "Configure which X-ray Lines are shown", self.config_xraylines)
        MenuItem(self, omenu, "Configure Plot\tCtrl+K",
                 "Configure Plot Colors, etc", self.panel.configure)
        MenuItem(self, omenu, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range", self.unzoom_all)
        MenuItem(self, omenu, "Toggle Grid\tCtrl+G",
                 "Toggle Grid Display", self.toggle_grid)
        MenuItem(self, omenu,  "Toggle Plot legend",
                 "Toggle Plot Legend", self.onToggleLegend)
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
        MenuItem(self, omenu, "Swap MCA and Background MCA",
                 "Swap Foreground and Background MCAs", self.swap_mcas)
        MenuItem(self, omenu, "Close Background MCA",
                 "Close Background MCA", self.close_bkg_mca)

        amenu = wx.Menu()
        MenuItem(self, amenu, "Show Pileup Prediction",
                 "Show Pileup Prediction", kind=wx.ITEM_CHECK,
                 checked=False, action=self.onPileupPrediction)
        MenuItem(self, amenu, "Show Escape Prediction",
                 "Show Escape Prediction", kind=wx.ITEM_CHECK,
                 checked=False, action=self.onEscapePrediction)
        MenuItem(self, amenu, "&Calibrate Energy\tCtrl+E",
                 "Calibrate Energy",  self.onCalibrateEnergy)
        MenuItem(self, amenu, "Fit Spectrum\tCtrl+F",
                 "Fit Spectrum for Elemental Contributiosn",
                 self.onFitSpectrum)
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
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def onShowLarchBuffer(self, evt=None):
        if self.larch_buffer is not None:
            self.larch_buffer.Show()
            self.larch_buffer.Raise()

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

    def onClose(self, event=None):
        try:
            if callable(self.exit_callback):
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

        if hasattr(self.larch.symtable, '_plotter'):
            wx.CallAfter(self.larch.symtable._plotter.close_all_displays)

        for name, wid in self.subframes.items():
            if hasattr(wid, 'Destroy'):
                wx.CallAfter(wid.Destroy)
        self.Destroy()

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

    def onToggleLegend(self, event=None):
        self.panel.conf.show_legend = not self.panel.conf.show_legend
        self.panel.conf.draw_legend()

    def onKLM(self, event=None):
        """selected K, L, or M Markers"""
        if self.selected_elem is not None:
            self.onShowLines(elem = self.selected_elem)

    def onToggleHold(self, event=None):
        if event.IsChecked():
            self.wids['holdbtn'].SetLabel("Hide %s" % self.selected_elem)
            self.hold_lines = self.saved_lines[:]
        else:
            self.wids['holdbtn'].SetLabel("Hold %s" % self.selected_elem)
            self.hold_lines = None
            for m in self.hold_markers:
                try:
                    m.remove()
                except:
                    pass
            self.hold_markers = []
            self.draw()

    def onSelectXrayLine(self, evt=None):
        if self.wids['xray_lines'] is None:
            return
        if not self.wids['xray_lines'].HasSelection():
            return
        item = self.wids['xray_lines'].GetSelectedRow()
        en = self.wids['xray_linesdata'][item]

        if self.highlight_xrayline is not None:
            self.highlight_xrayline.remove()

        self.energy_for_zoom = en
        self.highlight_xrayline = self.panel.axes.axvline(en,
                             color=self.conf.emph_elinecolor,
                             linewidth=2.5, zorder=-15)
        self.draw()

    def onShowLines(self, event=None, elem=None):
        if elem is None:
            elem  = event.GetString()

        vline = self.panel.axes.axvline
        elines = self.larch.symtable._xray.xray_lines(elem)

        self.selected_elem = elem
        self.clear_lines()
        self.energy_for_zoom = None
        xlines = self.wids['xray_lines']
        if xlines is not None:
            xlines.DeleteAllItems()
        self.wids['xray_linesdata'] = []
        minors, majors = [], []
        conf = self.conf
        line_data = {}
        for line in (conf.K_major+conf.K_minor+conf.L_major+
                     conf.L_minor+conf.M_major):
            line_data[line] = line, -1, 0, '', ''
            if line in elines:
                dat = elines[line]
                line_data[line] = line, dat[0], dat[1], dat[2], dat[3]

        if self.wids['kseries'].IsChecked():
            majors.extend([line_data[l] for l in conf.K_major])
            minors.extend([line_data[l] for l in conf.K_minor])
        if self.wids['lseries'].IsChecked():
            majors.extend([line_data[l] for l in conf.L_major])
            minors.extend([line_data[l] for l in conf.L_minor])
        if self.wids['mseries'].IsChecked():
            majors.extend([line_data[l] for l in conf.M_major])

        self.saved_lines = majors[:] + minors[:]
        erange = [max(conf.e_min, self.xdata.min()),
                  min(conf.e_max, self.xdata.max())]

        view_mid, view_range, d1, d2 = self._getlims()
        view_emin = view_mid - view_range/2.0
        view_emax = view_mid + view_range/2.0
        for label, eev, frac, ilevel, flevel in majors:
            e = float(eev) * 0.001
            # print( 'Major ', label, eev, e, frac, ilevel, flevel)
            if (e >= erange[0] and e <= erange[1]):
                l = vline(e, color= self.conf.major_elinecolor,
                          linewidth=1.50, zorder=-5)
                l.set_label(label)
                dat = (label, "%.4f" % e, "%.4f" % frac,
                       "%s->%s" % (ilevel, flevel))
                self.wids['xray_linesdata'].append(e)
                if xlines is not None:
                    xlines.AppendItem(dat)

                self.major_markers.append(l)
                if (self.energy_for_zoom is None and
                    e > view_emin and e < view_emax):
                    self.energy_for_zoom = e

        for label, eev, frac, ilevel, flevel in minors:
            e = float(eev) * 0.001
            if (e >= erange[0] and e <= erange[1]):
                l = vline(e, color= self.conf.minor_elinecolor,
                          linewidth=1.25, zorder=-7)
                l.set_label(label)

                # dat = (label, "%.4f" % e, "%.4f" % frac,
                #       "%s->%s" % (ilevel, flevel))
                dat = (label,  "%.4f" % e, "%.4f" % frac,
                       "%s->%s" % (ilevel, flevel))

                self.wids['xray_linesdata'].append(e)
                if xlines is not None:
                    xlines.AppendItem(dat)
                self.minor_markers.append(l)

        if not self.wids['holdbtn'].GetValue():
            self.wids['holdbtn'].SetLabel("Hold %s" % elem)
        elif self.hold_lines is not None:
            for label, eev, frac, ilevel, flevel in self.hold_lines:
                e = float(eev) * 0.001
                if (e >= erange[0] and e <= erange[1]):
                    l = vline(e, color=self.conf.hold_elinecolor,
                              linewidth=1.5, zorder=-20, dashes=(3, 3))
                    l.set_label(label)
                    self.hold_markers.append(l)

        if xlines is not None:
            xlines.Refresh()

        edge_en = {}
        for edge in ('K', 'M5', 'L3', 'L2', 'L1'):
            edge_en[edge] = None
            xex = self.larch.symtable._xray.xray_edge(elem, edge)
            if xex is not None:
                en = xex[0]*0.001
                if en > erange[0] and en < erange[1]:
                    edge_en[edge] = en
        out = ''
        for key in ('M5', 'K'):
            if edge_en[key] is not None:
                out = "%s=%.3f" % (key, edge_en[key])
        if len(out) > 1:
            self.wids['ptable'].set_subtitle(out, index=0)
        s, v, out = [], [], ''
        for key in ('L3', 'L2', 'L1'):
            if edge_en[key] is not None:
                s.append(key)
                v.append("%.3f" % edge_en[key])
        if len(s) > 0:
            out = "%s=%s" %(', '.join(s), ', '.join(v))
        self.wids['ptable'].set_subtitle(out, index=1)

        self.draw()

    def onPileupPrediction(self, event=None):
        if event.IsChecked():
            self.mca.predict_pileup()
            self.oplot(self.mca.energy, self.mca.pileup,
                       color=self.conf.pileup_color, label='pileup prediction')
        else:
            self.plotmca(self.mca)

    def onEscapePrediction(self, event=None):
        if event.IsChecked():
            self.mca.predict_escape()
            self.oplot(self.mca.energy, self.mca.escape,
                       color=self.conf.escape_color, label='escape prediction')
        else:
            self.plotmca(self.mca)


    def onYAxis(self, event=None):
        self.show_yaxis = self.wids['show_yaxis'].IsChecked()
        ax = self.panel.axes
        ax.yaxis.set_major_formatter(FuncFormatter(self._formaty))
        ax.get_yaxis().set_visible(self.show_yaxis)
        ax.spines['right'].set_visible(False)
        ax.yaxis.set_ticks_position('left')
        self.draw()

    def _formaty(self, val, index=0, **kws):
        try:
            decade = int(np.log10(val))
        except:
            decade = 0
        scale = 10**decade
        out = "%.1fe%i" % (val/scale, decade)
        if abs(decade) < 1.9:
            out = "%.1f" % val
        elif abs(decade) < 3.9:
            out = "%.0f" % val
        return out

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

    def plotmca(self, mca, title=None, set_title=True, as_mca2=False,
                fullrange=False, init=False, **kws):
        if as_mca2:
            self.mca2 = mca
            kws['new'] = False
        else:
            self.mca = mca
            self.panel.conf.show_grid = False
        xview_range = self.panel.axes.get_xlim()

        if init or xview_range == (0.0, 1.0):
            self.xview_range = (min(self.mca.energy), max(self.mca.energy))
        else:
            self.xview_range = xview_range

        atitles = []
        if self.mca is not None:
            if getattr(self.mca, 'title', None) is not None:
                atitles.append(bytes2str(self.mca.title))
            if getattr(self.mca, 'filename', None) is not None:
                atitles.append(" File={:s}".format(self.mca.filename))
            if getattr(self.mca, 'npixels', None) is not None:
                atitles.append(" {:.0f} Pixels".format(self.mca.npixels))
            if getattr(self.mca, 'real_time', None) is not None:
                try:
                    rtime_str = " RealTime={:.2f} sec".format(self.mca.real_time)
                except ValueError:
                    rtime_str = " RealTime= %s sec".format(str(self.mca.real_time))
                atitles.append(rtime_str)

            try:
                self.plot(self.mca.energy, self.mca.counts,
                          mca=self.mca, **kws)
            except ValueError:
                pass
        if as_mca2:
            if getattr(self.mca2, 'title', None) is not None:
                atitles.append(" BG={:s}".format(self.mca2.title))
            elif getattr(self.mca2, 'filename', None) is not None:
                atitles.append(" BG_File={:s}".format(self.mca2.filename))
            if getattr(self.mca, 'real_time', None) is not None:
                atitles.append(" BG_RealTime={:.2f} sec".format(self.mca2.real_time))

            self.oplot(self.mca2.energy, self.mca2.counts,
                       mca=self.mca2, **kws)
        if title is None:
            title = ' '.join(atitles)
        if set_title:
            self.SetTitle(title)

    def plot(self, x, y=None, mca=None, init=False, with_rois=True, **kws):
        if mca is not None:
            self.mca = mca
        mca = self.mca
        panel = self.panel

        panel.yformatter = self._formaty
        panel.axes.get_yaxis().set_visible(False)
        kwargs = {'xmin': 0,
                  'linewidth': 2.5,
                  'delay_draw': True,
                  'grid': panel.conf.show_grid,
                  'ylog_scale': self.ylog_scale,
                  'xlabel': 'E (keV)',
                  'axes_style': 'bottom',
                  'color': self.conf.spectra_color}
        kwargs.update(kws)

        self.xdata = 1.0*x[:]
        self.ydata = 1.0*y[:]
        ydat = 1.0*y[:] + 1.e-9
        kwargs['ymax'] = max(ydat)*1.25
        kwargs['ymin'] = 0.9
        kwargs['xmax'] = max(self.xdata)
        kwargs['xmin'] = min(self.xdata)
        if self.xview_range is not None:
            kwargs['xmin'] = self.xview_range[0]
            kwargs['xmax'] = self.xview_range[1]

        panel.plot(x, ydat, label='spectrum',  **kwargs)
        if with_rois and mca is not None:
            if not self.rois_shown:
                self.set_roilist(mca=mca)
            yroi = -1.0*np.ones(len(y))
            max_width = 0.5*len(self.mca.energy) # suppress very large ROIs
            for r in mca.rois:
                if ((r.left, r.right) in ((0, 0), (-1, -1)) or
                    (r.right - r.left) > max_width):
                    continue
                yroi[r.left:r.right] = y[r.left:r.right]
            yroi = np.ma.masked_less(yroi, 0)
            if yroi.max() > 0:
                kwargs['color'] = self.conf.roi_color
                panel.oplot(x, yroi, label='rois', **kwargs)
        yscale = {False:'linear', True:'log'}[self.ylog_scale]
        panel.set_viewlimits()
        panel.set_logscale(yscale=yscale)
        panel.axes.get_yaxis().set_visible(self.show_yaxis)
        panel.cursor_mode = 'zoom'
        self.draw()
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
        xnpts = 1.0/len(energy)
        nrois = len(mca.rois)
        if not is_mca2 and with_rois and nrois > 0:
            yroi = -1*np.ones(len(counts))
            for r in mca.rois:
                if xnpts*(r.right - r.left) > 0.5:
                    continue
                yroi[r.left:r.right] = counts[r.left:r.right]
            yroi = np.ma.masked_less(yroi, 0)
            self.panel.update_line(1, mca.energy, yroi, draw=False,
                                   update_limits=False)

        self.panel.update_line(ix, mca.energy, counts,
                               draw=False, update_limits=False)

        max_counts = max_counts2 = max(self.mca.counts)
        try:
            max_counts2 = max(self.mca2.counts)
        except:
            pass

        self.panel.axes.set_ylim(0.9, 1.25*max(max_counts, max_counts2))
        if mca == self.mca:
            self.ydata = 1.0*counts[:]
        self.update_status()
        if draw: self.draw()

    def oplot(self, x, y, color='darkgreen', label='spectrum2',
              mca=None, zorder=-2, **kws):
        if mca is not None:
            self.mca2 = mca

        self.x2data = 1.0*x[:]
        self.y2data = 1.0*y[:]
        if hasattr(self, 'ydata'):
            ymax = max(max(self.ydata), max(y))*1.25
        else:
            ymax = max(y)*1.25

        kws.update({'zorder': zorder, 'label': label,
                    'ymax' : ymax, 'axes_style': 'bottom',
                    'ylog_scale': self.ylog_scale})
        self.panel.oplot(self.x2data, self.y2data, color=color, **kws)

    def swap_mcas(self, event=None):
        if self.mca2 is None:
            return
        self.mca, self.mca2 = self.mca2, self.mca
        xrfgroup = self.larch.symtable.get_group(XRFGROUP)
        _mca = getattr(xrfgroup, '_mca', '')
        _mca2 = getattr(xrfgroup, '_mca2', '')
        setattr(xrfgroup, '_mca2', _mca)
        setattr(xrfgroup, '_mca', _mca2)

        self.plotmca(self.mca)
        self.plotmca(self.mca2, as_mca2=True)

    def close_bkg_mca(self, event=None):
        self.mca2 = None
        xrfgroup = self.larch.symtable.get_group(XRFGROUP)
        setattr(xrfgroup, '_mca2', '')
        self.plotmca(self.mca)

    def onReadMCAFile(self, event=None):
        dlg = wx.FileDialog(self, message="Open MCA File for reading",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style = wx.FD_OPEN|wx.FD_CHANGE_DIR)

        filename = None
        if dlg.ShowModal() == wx.ID_OK:
            filename = os.path.abspath(dlg.GetPath())
        dlg.Destroy()

        if filename is None:
            return
        if self.mca is not None:
            self.mca2 = copy.deepcopy(self.mca)

        self.add_mca(GSEMCA_File(filename), filename=filename)

    def onSaveMCAFile(self, event=None, **kws):
        deffile = ''
        if getattr(self.mca, 'sourcefile', None) is not None:
            deffile = "%s%s" % (deffile, self.mca.sourcefile)
        elif getattr(self.mca, 'filename', None) is not None:
            deffile = "%s%s" % (deffile, self.mca.filename)
        if getattr(self.mca, 'areaname', None) is not None:
            deffile = "%s_%s" % (deffile, self.mca.areaname)
        if deffile == '':
            deffile ='test'
        if not deffile.endswith('.mca'):
            deffile = deffile + '.mca'

        _, deffile = os.path.split(deffile)
        deffile = fix_filename(str(deffile))
        outfile = FileSave(self, "Save MCA File",
                           default_file=deffile,
                           wildcard=FILE_WILDCARDS)
        if outfile is not None:
            self.mca.save_mcafile(outfile)

    def onSaveColumnFile(self, event=None, **kws):
        deffile = ''
        if getattr(self.mca, 'sourcefile', None) is not None:
            deffile = "%s%s" % (deffile, self.mca.sourcefile)
        elif getattr(self.mca, 'filename', None) is not None:
            deffile = "%s%s" % (deffile, self.mca.filename)

        if getattr(self.mca, 'areaname', None) is not None:
            deffile = "%s_%s" % (deffile, self.mca.areaname)
        if deffile == '':
            deffile ='test'
        if not deffile.endswith('.dat'):
            deffile = deffile + '.dat'

        _, deffile = os.path.split(deffile)
        deffile = fix_filename(str(deffile))
        ASCII_WILDCARDS = "Data File (*.dat)|*.dat|All files (*.*)|*.*"
        outfile = FileSave(self, "Save ASCII File for MCA Data",
                           default_file=deffile,
                           wildcard=ASCII_WILDCARDS)
        if outfile is not None:
            self.mca.save_ascii(outfile)

    def onCalibrateEnergy(self, event=None, **kws):
        try:
            self.win_calib.Raise()
        except:
            self.win_calib = XRFCalibrationFrame(self, mca=self.mca,
                                                 callback=self.onCalibrationChange)

    def onCalibrationChange(self, mca):
        """update whenn mca changed calibration"""
        self.plotmca(mca)

    def onFitSpectrum(self, event=None, **kws):
        try:
            self.win_fit.Raise()
        except:
            self.win_fit = FitSpectraFrame(self)

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def onAbout(self, event=None):
        dlg = wx.MessageDialog(self,
                               """XRF Spectral Viewer
                               Matt Newville <newville @ cars.uchicago.edu>
                               """,
                               "About XRF Viewer",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onReadFile(self, event=None):
        dlg = wx.FileDialog(self, message="Read MCA File",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.FD_OPEN)
        path, re1ad = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
            if path in self.filemap:
                read = (wx.ID_YES == Popup(self, "Re-read file '%s'?" % path,
                                           'Re-read file?', style=wx.YES_NO))
        dlg.Destroy()

        if read:
            try:
                parent, fname = os.path.split(path)
            except:
                return

class XRFApp(LarchWxApp):
    def __init__(self, filename=None, **kws):
        self.filename = filename
        LarchWxApp.__init__(self, **kws)

    def createApp(self):
        frame = XRFDisplayFrame(filename=self.filename)
        frame.Show()
        self.SetTopWindow(frame)
        return True
