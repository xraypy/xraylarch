#!/usr/bin/env python
"""
GUI Frame for XRF display, reading larch MCA group

"""
import sys
import time
import copy
from collections import namedtuple
from functools import partial
from pathlib import Path
import wx
import wx.lib.mixins.inspection
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv
import wx.lib.colourselect  as csel

import numpy as np
import matplotlib
from matplotlib.ticker import LogFormatter, FuncFormatter

from pyshortcuts import uname, bytes2str, get_cwd, fix_filename

from wxmplot import PlotPanel
from . import (SimpleText, FileCheckList, Font, pack, Popup,
               set_color, get_icon, get_font,
               SetTip, Button, Check, MenuItem, Choice,
               FileOpen, FileSave, HLine, GridPanel,
               CEN, LEFT, RIGHT, PeriodicTablePanel,
               FONTSIZE, FONTSIZE_FW, OkCancel)

from ..math import index_of
from ..io import GSEMCA_File
from ..site_config import icondir
from ..interpreter import Interpreter

from .gui_utils import LarchWxApp
from .larchframe import LarchFrame
# from .periodictable import PeriodicTablePanel

from .xrfdisplay_utils import (XRFCalibrationFrame,
                               XrayLinesFrame,
                               ColorsFrame,
                               XRFLines,
                               XRFDisplayColors_Light,
                               XRFDisplayColors_Dark,
                               XRFGROUP, XRF_FILES, MAKE_XRFGROUPS,
                               next_mcaname)

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

def fit_dialog_window(dialog, panel):
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, LEFT, 5)
    pack(dialog, sizer)
    dialog.Fit()
    w0, h0 = dialog.GetSize()
    w1, h1 = dialog.GetBestSize()
    dialog.SetSize((max(w0, w1)+25, max(h0, h1)+25))

class RenameDialog(wx.Dialog):
    """dialog for renaming group"""
    def __init__(self, parent, oldname,  **kws):
        title = "Rename Group %s" % (oldname)
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)
        self.SetFont(get_font())
        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LEFT)
        self.newname   = wx.TextCtrl(panel, -1, oldname,  size=(250, -1))

        panel.Add(SimpleText(panel, 'Old Name : '), newrow=True)
        panel.Add(SimpleText(panel, oldname))
        panel.Add(SimpleText(panel, 'New Name : '), newrow=True)
        panel.Add(self.newname)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()
        fit_dialog_window(self, panel)


    def GetResponse(self, newname=None):
        self.Raise()
        response = namedtuple('RenameResponse', ('ok', 'newname'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            newname = self.newname.GetValue()
            ok = True
        return response(ok, newname)


class XRFDataBrowser(wx.Frame):
    """ frame for browsing XRF data in larch buffer
    """
    def __init__(self, parent, larch, size=(500, 250), **kws):
        self.parent = parent
        self.larch = larch
        if size is None:
            size = (500, 250)

        wx.Frame.__init__(self, parent=parent, size=size,
                        title='XRF Datasets', **kws)

        panel = wx.Panel(self)
        top = wx.Panel(panel)
        mid = wx.Panel(panel)

        def Btn(p, msg, x, act):
            b = Button(p, msg, size=(x, 30),  action=act)
            b.SetFont(get_font())
            return b

        sel_none = Btn(top, 'Select None',   125, self.onSelNone)
        sel_all  = Btn(top, 'Select All',    125, self.onSelAll)
        plot_one = Btn(mid, 'Plot One',      125, self.onPlotOne)
        plot_sel = Btn(mid, 'Plot Selected', 250, self.onPlotSelected)

        file_actions = [("Copy Group\tCtrl+Shift+C", self.onCopyGroup, "ctrl+shift+C"),
                        ("Rename Group\tCtrl+N", self.onRenameGroup, "ctrl+N"),
                        ("Remove Group\tCtrl+X", self.onRemoveGroup, "ctrl+X"),
                        ("Remove Selected Groups\tCtrl+Delete", self.onRemoveGroups, "ctrl+delete"),
                        ("--sep--", None, None),
                        ]

        self.current_file = None
        self.file_groups = {}
        self.filelist = FileCheckList(panel, main=self,
                                      pre_actions=file_actions,
                                      select_action=self.onSelectOne,
                                      remove_action=self.onRemoveGroup,
                                      with_remove_from_list=False)

        set_color(self.filelist, 'list_fg', bg='list_bg')
        wx.CallAfter(self.update_grouplist)

        tsizer = wx.BoxSizer(wx.HORIZONTAL)
        tsizer.Add(sel_all, 1, LEFT|wx.GROW, 1)
        tsizer.Add(sel_none, 1, LEFT|wx.GROW, 1)
        pack(top, tsizer)

        psizer = wx.BoxSizer(wx.HORIZONTAL)
        psizer.Add(plot_one, 1, LEFT|wx.GROW, 1)
        psizer.Add(plot_sel, 1, LEFT|wx.GROW, 1)
        pack(mid, psizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(top, 0, LEFT|wx.GROW, 1)
        sizer.Add(mid, 0, LEFT|wx.GROW|wx.ALL, 2)
        sizer.Add(self.filelist, 1, LEFT|wx.GROW|wx.ALL, 2)
        pack(panel, sizer)
        self.SetSize((500, 250))
        self.Show()
        self.Raise()

    def update_grouplist(self, event=None, full=False):
        if full:
            self.file_groups = {}
            self.filelist.Clear()
        for key, val in self.parent.xrf_files.items():
            if key not in self.file_groups:
                self.file_groups[key] = val
                try:
                    self.filelist.Append(key)
                except Exception:
                    pass
        self.Refresh()

    def onSelNone(self, event=None):
        self.filelist.select_none()

    def onSelAll(self, event=None):
        self.filelist.select_all()

    def onSelectOne(self, event=None):
        self.current_file = str(event.GetString())

    def onPlotOne(self, event=None):
        if self.current_file is not None:
            mca = self.parent.get_mca(self.current_file)
            self.parent.plotted_groups = []
            if mca is not None:
                self.parent.plotmca(mca, newplot=True)

    def onPlotSelected(self, event=None):
        filenames = self.filelist.GetCheckedStrings()
        ix = 0
        self.parent.plotted_groups = []
        for ix, fname in enumerate(filenames):
            mca = self.parent.get_mca(fname)
            if mca is not None:
                self.parent.plotmca(mca, newplot=(ix==0))

    def onCopyGroup(self, event=None):
        fname = self.current_filename
        if fname is None:
            fname = self.filelist.GetStringSelection()

        mca = xrf_files[fname]
        newname = fname + '_copy'
        self.parent.xrf_files[newname] = deepcopy(mca)
        self.update_grouplist()


    def onRenameGroup(self, event=None):
        fname = self.current_file
        if fname is None:
            fname = self.filelist.GetStringSelection()

        dlg = RenameDialog(self, fname)
        res = dlg.GetResponse()
        dlg.Destroy()

        if res.ok:
            mca = self.parent.xrf_files.pop(fname)
            selected = []
            for checked in self.filelist.GetCheckedStrings():
                selected.append(str(checked))
            if self.current_file in selected:
                selected.remove(self.current_file)
                selected.append(res.newname)

            self.parent.xrf_files[res.newname] = mca
            self.update_grouplist(full=True)


    def onRemoveGroup(self, event=None):
        fname = self.current_filename
        if fname is None:
            fname = self.filelist.GetStringSelection()

        self.parent.xrf_files.pop(fname)
        self.update_grouplist(full=True)

    def onRemoveGroups(self, event=None):
        filenames = self.filelist.GetCheckedStrings()

        for fname in enumerate(filenames):
            self.parent.xrf_files.pop(fname)
        self.update_grouplist(full=True)


class XRFDisplayFrame(wx.Frame):
    _about = """XRF Spectral Viewer
  Matt Newville <newville@cars.uchicago.edu>
  """
    main_title = 'XRF Display'

    def __init__(self, parent=None, filename=None, size=(725, 450),
                 axissize=None, axisbg=None, title='XRF Display',
                 exit_callback=None, output_title='XRF', roi_callback=None,
                 _larch=None, **kws):

        if size is None:
            size = (725, 450)
        wx.Frame.__init__(self, parent=parent,
                          title=title, size=size,  **kws)
        self.colors = XRFDisplayColors_Light()
        self.subframes = {}
        self.data = None
        self.title = title
        self.roi_callback = roi_callback
        self.plotframe = None
        self.wids = {}
        if isinstance(_larch, LarchFrame):  # called with existing LarchFrame
            self.larch_buffer = _larch
            self.larch_owner = False
        elif isinstance(_larch, Interpreter):     # called from shell
            self.larch_buffer = LarchFrame(_larch=_larch,
                   is_standalone=False, with_raise=False)
            self.larch_owner = False
        else:  # (includes  _larch is None)  called from Python
            self.larch_buffer = LarchFrame(with_raise=False)
            self.larch_owner = True

        self.subframes['larch_buffer'] = self.larch_buffer
        self.larch = self.larch_buffer.larchshell
        self.init_larch()

        self.exit_callback = exit_callback
        self.roi_patch = None
        self.selected_roi = None
        self.roilist_sel  = None
        self.selected_elem = None
        self.mca = None
        self.mcabkg = None
        self.xdat = np.arange(4096)*0.01
        self.ydat = np.ones(4096)*0.01
        self.plotted_groups = []
        self.ymin = 0.9
        self.show_cps = False
        self.show_pileup = False
        self.show_escape = False
        self.show_yaxis = True
        self.ylog_scale = True
        self.show_grid = False

        self.major_markers = []
        self.minor_markers = []
        self.hold_markers = []

        self.hold_lines = None
        self.saved_lines = None
        self.energy_for_zoom = None
        self.xview_range = None
        self.xmarker_left = None
        self.xmarker_right = None

        self.highlight_xrayline = None
        self.cursor_markers = [None, None]
        self.SetTitle("%s: %s " % (self.main_title, title))

        self._menus = []
        self.createMainPanel()
        self.createMenus()
        self.SetFont(get_font())
        self.statusbar = self.CreateStatusBar(4)
        self.statusbar.SetStatusWidths([-5, -3, -3, -4])
        statusbar_fields = ["XRF Display", " ", " ", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        try:
            fico = Path(icondir, ICON_FILE).as_posix()
            self.SetIcon(wx.Icon(fico, wx.BITMAP_TYPE_ICO))
        except:
            pass

        if filename is not None:
            if isinstance(filename, Path):
                filename = Path(filename).absolute().as_posix()
            self.add_mca(GSEMCA_File(filename), filename=filename, plot=True)

    def on_cursor(self, event=None, side='left'):
        if event is None:
            return
        x, y  = event.xdata, event.ydata
        if len(self.plotpanel.fig.axes) > 1:
            try:
                x, y = self.plotpanel.axes.transData.inverted().transform((event.x, event.y))
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

        if side == 'left' and ix is not None:
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


    def clear_markers(self, evt=None):
        "remove all Cursor Markers"
        for m in self.cursor_markers:
            if m is not None:
                m.remove()
        self.cursor_markers = [None, None]
        self.xmarker_left  = None
        self.xmarker_right = None
        self.draw()

    def draw(self):
        try:
            self.plotpanel.canvas.draw()
        except:
            pass

    def update_status(self):
        fmt = "{:s}:{:}, E={:.3f}, Cts={:,.0f}".format
        if (self.xmarker_left is None and
            self.xmarker_right is None and
            self.selected_roi is None):
            return

        log = np.log10
        axes= self.plotpanel.axes
        def draw_ymarker_range(idx, x, y):
            ymin, ymax = self.plotpanel.axes.get_ylim()
            y1 = (y-ymin)/(ymax-ymin+0.0002)
            if y < 1.0: y = 1.0
            if  self.ylog_scale:
                y1 = (log(y)-log(ymin))/(log(ymax)-log(ymin)+2.e-9)
                if y1 < 0.0: y1 = 0.0
            y2 = min(y1+0.25, y1*0.1 + 0.001)
            if self.cursor_markers[idx] is not None:
                try:
                    self.cursor_markers[idx].remove()
                except:
                    pass
            self.cursor_markers[idx] = axes.axvline(x, y1, y2, linewidth=2.5,
                                                    label='_nolegend_',
                                                    color=self.colors.marker_color)

        if self.xmarker_left is not None:
            ix = self.xmarker_left
            x, y = self.xdat[ix],  self.ydat[ix]
            draw_ymarker_range(0, x, y)
            self.write_message(fmt("L", ix, x, y), panel=1)
        if self.xmarker_right is not None:
            ix = self.xmarker_right
            x, y = self.xdat[ix],  self.ydat[ix]
            draw_ymarker_range(1, x, y)
            self.write_message(fmt("R", ix, x, y), panel=2)

        if self.mca is None:
            return

        if self.selected_roi is not None:
            roi = self.selected_roi
            left, right = roi.left, roi.right
            self.ShowROIStatus(left, right, name=roi.name, panel=0)
            self.ShowROIPatch(left, right)

        elif (self.xmarker_left is not None and self.xmarker_right is not None):
            self.ShowROIStatus(self.xmarker_left, self.xmarker_right,
                               name='unnamed', panel=3)


    def onLeftUp(self, event=None):
        """ left button up"""
        if event is None:
            return
        x, y  = event.xdata, event.ydata
        if len(self.plotpanel.fig.axes) > 1:
            try:
                x, y = self.plotpanel.axes.transData.inverted().transform((event.x, event.y))
            except:
                pass
        ix = x
        if self.mca is not None:
            try:
                ix = index_of(self.mca.energy, x)
            except TypeError:
                pass
        if ix is not None:
            ezoom = self.mca.energy[ix]
            self.energy_for_zoom = (ezoom + self.energy_for_zoom)/2.0

        self.plotpanel.cursor_mode_action('leftup', event=event)
        self.plotpanel.canvas.draw_idle()
        self.plotpanel.canvas.draw()
        self.plotpanel.ForwardEvent(event=event.guiEvent)


    def createControlPanel(self):
        ctrlpanel = wx.Panel(self, name='Ctrl Panel')
        ptable_fontsize = 11 if uname=='darwin' else 9
        ptable = PeriodicTablePanel(ctrlpanel, onselect=self.onShowLines,
                                    tooltip_msg='Select Element for KLM Lines',
                                    fontsize=ptable_fontsize, size=(360, 180))
        self.wids['ptable'] = ptable
        self.font_fixedwidth = wx.Font(FONTSIZE_FW, wx.MODERN, wx.NORMAL, wx.NORMAL)

        labstyle = wx.ALIGN_LEFT|wx.EXPAND
        ctrlstyle = wx.ALIGN_LEFT
        txtstyle=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE|wx.TE_PROCESS_ENTER
        Font10 = Font(10)
        Font11 = Font(11)
        Font12 = Font(12)
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
                                               size=(100, 30))
        self.wids['holdbtn'].Bind(wx.EVT_TOGGLEBUTTON, self.onToggleHold)

        ssizer.Add(self.wids['holdbtn'],    0, wx.EXPAND|wx.ALL, 2)
        pack(arrowpanel, ssizer)

        # zoom
        zpanel = wx.Panel(ctrlpanel)
        zsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.wids['zoom_in'] = Button(zpanel, 'Zoom In',   size=(100, 30),
                                        action=self.onZoomIn)
        self.wids['zoom_out'] = Button(zpanel, 'Zoom Out',   size=(100, 30),
                                        action=self.onZoomOut)

        zsizer.Add(self.wids['zoom_in'],    0, wx.EXPAND|wx.ALL, 2)
        zsizer.Add(self.wids['zoom_out'],    0, wx.EXPAND|wx.ALL, 2)

        pack(zpanel, zsizer)

        # Lines selection
        linespanel = wx.Panel(ctrlpanel)
        lsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.wids['kmajor'] = Check(linespanel, ' K major', default=True, action=self.onKLM)
        self.wids['kminor'] = Check(linespanel, ' K minor', default=False, action=self.onKLM)
        self.wids['lmajor'] = Check(linespanel, ' L major', default=True, action=self.onKLM)
        self.wids['lminor'] = Check(linespanel, ' L minor', default=False, action=self.onKLM)
        self.wids['mmajor'] = Check(linespanel, ' M lines', default=False, action=self.onKLM)

        lsizer.Add(self.wids['kmajor'],    0, wx.EXPAND|wx.ALL, 0)
        lsizer.Add(self.wids['kminor'],    0, wx.EXPAND|wx.ALL, 0)
        lsizer.Add(self.wids['lmajor'],    0, wx.EXPAND|wx.ALL, 0)
        lsizer.Add(self.wids['lminor'],    0, wx.EXPAND|wx.ALL, 0)
        lsizer.Add(self.wids['mmajor'],    0, wx.EXPAND|wx.ALL, 0)
        pack(linespanel, lsizer)

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

        rt1 = txt(roipanel, ' Channels:', size=80, font=Font11)
        rt2 = txt(roipanel, ' Energy:',   size=80, font=Font11)
        rt3 = txt(roipanel, ' Cen, Wid:',  size=80, font=Font11)
        m = ''
        self.wids['roi_msg1'] = txt(roipanel, m, size=135, font=Font11)
        self.wids['roi_msg2'] = txt(roipanel, m, size=135, font=Font11)
        self.wids['roi_msg3'] = txt(roipanel, m, size=135, font=Font11)

        rsizer.Add(txt(roipanel, ' Regions of Interest:', size=125, font=Font12),
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

        self.wids['xray_lines'] = None

        dvstyle = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES
        xlines = dv.DataViewListCtrl(ctrlpanel, style=dvstyle)
        xlines.SetFont(self.font_fixedwidth)
        self.wids['xray_lines'] = xlines

        xw = (55, 105, 90, 95)
        if uname == 'darwin':
            xw = (55, 80, 65, 120)
        elif uname == 'win':
            xw = (55, 120, 90, 90)
        xlines.AppendTextColumn('Line',         width=xw[0])
        xlines.AppendTextColumn('Energy(keV)',  width=xw[1])
        xlines.AppendTextColumn('Strength',     width=xw[2])
        xlines.AppendTextColumn('Levels',       width=xw[3])
        for col in (0, 1, 2, 3):
            this = xlines.Columns[col]
            this.Sortable = False
            align = RIGHT
            if col in (0, 3):
                align = wx.ALIGN_LEFT
            this.Alignment = this.Renderer.Alignment = align

        xlines.SetMinSize((300, 240))
        xlines.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectXrayLine)
        store = xlines.GetStore()

        # main layout
        # may have to adjust comparison....

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(roipanel,            0, labstyle)
        sizer.Add((5, 5),              0, wx.EXPAND|wx.ALL)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)
        sizer.Add(zpanel,              0, labstyle)
        sizer.Add(ptable,              0, wx.EXPAND|wx.ALL, 4)
        sizer.Add(arrowpanel,          0, labstyle)
        sizer.Add(linespanel,          0, labstyle)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)

        if self.wids['xray_lines'] is not None:
            sizer.Add(xlines,  0, wx.GROW|wx.ALL|wx.EXPAND)

        pack(ctrlpanel, sizer)
        return ctrlpanel

    def createMainPanel(self):
        ctrlpanel = self.createControlPanel()
        rpanel = self.createPlotPanel()

        tx, ty = self.wids['ptable'].GetBestVirtualSize()
        cx, cy = ctrlpanel.GetBestVirtualSize()
        px, py = self.plotpanel.GetBestVirtualSize()

        self.SetSize((max(cx, tx)+px, 25+max(cy, py)))

        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(ctrlpanel, 0, style, 3)
        sizer.Add(rpanel, 1, style, 2)

        self.SetMinSize((450, 150))
        pack(self, sizer)
        self.set_roilist(mca=None)

    def createPlotPanel(self):
        rpanel = wx.Panel(self)
        top = wx.Panel(rpanel)
        tsiz = wx.BoxSizer(wx.HORIZONTAL)

        self.wids['show_cps']   = Check(top, 'Counts/Sec', default=self.show_cps, action=self.onShowCPS)
        self.wids['show_ylog']   = Check(top, 'Y LogScale', default=self.ylog_scale, action=self.onLogLinear)
        self.wids['show_yaxis']  = Check(top, 'Y Axis', default=self.show_yaxis, action=self.onYAxis)
        self.wids['show_grid']   = Check(top, 'Grid ', default=self.show_grid, action=self.onShowGrid)
        self.wids['show_legend'] = Check(top, 'Legend', default=False, action=self.onShowLegend)

        tsiz.Add(SimpleText(top, 'Show: '), 0, wx.EXPAND|wx.ALL, 0)
        tsiz.Add(self.wids['show_cps'],    0, wx.EXPAND|wx.ALL, 0)
        tsiz.Add(self.wids['show_ylog'],   0, wx.EXPAND|wx.ALL, 0)
        tsiz.Add(self.wids['show_yaxis'],  0, wx.EXPAND|wx.ALL, 0)
        tsiz.Add(self.wids['show_legend'], 0, wx.EXPAND|wx.ALL, 0)
        tsiz.Add(self.wids['show_grid'],   0, wx.EXPAND|wx.ALL, 0)
        pack(top, tsiz)

        pan = self.plotpanel = PlotPanel(rpanel, fontsize=9, axisbg='#FFFFFF',
                                         with_data_process=False,
                                         output_title='test.xrf',
                                         messenger=self.write_message)
        rsiz = wx.BoxSizer(wx.VERTICAL)
        rsiz.Add(top,   0, wx.EXPAND|wx.ALL, 1)
        rsiz.Add(pan,   1, wx.EXPAND|wx.ALL, 1)
        pack(rpanel, rsiz)

        pan.SetSize((650, 350))

        pan.conf.grid_color='#E5E5C0'
        pan.conf.show_grid = self.show_grid
        pan.yformatter = self._formaty

        pan.axes.yaxis.set_major_formatter(FuncFormatter(self._formaty))
        pan.axes.yaxis.set_visible(self.show_yaxis)
        pan.axes.spines['right'].set_visible(False)
        pan.axes.yaxis.set_ticks_position('left')

        pan.conf.canvas.figure.set_facecolor('#FCFCFE')
        pan.conf.labelfont.set_size(9)
        pan.onRightDown =   partial(self.on_cursor, side='right')
        pan.report_leftdown = partial(self.on_cursor, side='left')
        pan.onLeftUp = self.onLeftUp

        return rpanel


    def init_larch(self):
        symtab = self.larch.symtable
        if not symtab.has_symbol('_sys.wx.wxapp'):
            symtab.set_symbol('_sys.wx.wxapp', wx.GetApp())
        if not symtab.has_symbol('_sys.wx.parent'):
            symtab.set_symbol('_sys.wx.parent', self)

        if not symtab.has_group(XRFGROUP):
            self.larch.eval(MAKE_XRFGROUPS)
        self.xrf_files = self.larch.symtable.get_symbol(XRF_FILES)


    def add_mca(self, mca, filename=None, label=None, plot=True):
        self.mca = mca
        xrfgroup = self.larch.symtable.get_group(XRFGROUP)
        mcaname = next_mcaname(self.larch)

        if filename is not None:
            if isinstance(filename, Path):
                filename = Path(filename).absolute().as_posix()
            readcomment = read_mcafile.format(group=XRFGROUP,
                                              name=mcaname,
                                              filename=filename)
            self.larch.eval(readcomment)
            if label is None:
                label = Path(filename).absolute().name
        if label is None and hasattr(mca, 'filename'):
            label = Path(mca.filename).absolute().name
        if label is None:
            label = mcaname

        self.mca.label = label
        real_time = getattr(self.mca, 'real_time', 1.0)
        try:
            real_time = float(real_time)
        except:
            real_time = 1.0

        mca.real_time = max(real_time, 1.e-6)

        setattr(xrfgroup, mcaname, mca)
        setattr(xrfgroup, 'mca', mcaname)

        self.larch.eval(f"{XRFGROUP}.mca = '{mcaname}'")
        self.larch.eval(f"{XRF_FILES}['{label}'] = {XRFGROUP}.{mcaname}")

        self.xrf_files[label] = self.mca
        if plot:
            self.plotmca(self.mca)

        if 'xrf_browser' in self.subframes:
            browser = self.subframes['xrf_browser']
            browser.update_grouplist()

    def _getlims(self):
        emin, emax = self.plotpanel.axes.get_xlim()
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
        self.plotpanel.axes.set_xlim((e1, e2))
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
        i1 = index_of(self.mca.energy, e1)
        if i1 > 0 : ii = i1 -1
        i2 = index_of(self.mca.energy, e2) + 1

        ymin, ymax = self.plotpanel.axes.get_ylim()
        dmax = float(max(self.mca.counts[i1:i2]) * 1.5)
        dmin = float(min(self.mca.counts[i1:i2]) * 0.5)
        if self.show_cps:
            dmax /= self.mca.real_time
            dmin /= self.mca.real_time
        if dmin < 1: dmin = 1
        self._set_xview(e1, e2)
        self.plotpanel.axes.set_ylim((min(dmin, ymin), max(dmax, ymax)), emit=True)

    def unzoom_all(self, event=None):
        self.plotpanel.unzoom_all()

    def onShowCPS(self, event=None):
        use_cps = event.IsChecked()
        rtime = max(1.e-5, self.mca.real_time)
        self.ymin = 0.9/rtime if use_cps else 0.9
        if use_cps != self.show_cps:
            self.show_cps = use_cps
            self.replot()

    def onShowGrid(self, event=None):
        self.show_grid = event.IsChecked()
        self.plotpanel.conf.enable_grid(event.IsChecked())
        self.plotpanel.conf.show_grid = event.IsChecked()

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
        self.plot(self.xdat, self.ydat)
        self.onROI(label=roiname)
        if self.selected_elem is not None:
            self.onShowLines(elem=self.selected_elem)
        if self.roi_callback is not None:
            xrange = [self.mca.energy[left], self.mca.energy[right]]
            self.roi_callback(roiname, xrange=xrange, action='add', units='keV', roitype='XRF')
        return True

    def onConfirmDelROI(self, event=None):
        roiname = self.wids['roiname'].GetValue()
        msg = "Delete ROI {:s}?".format(roiname)
        if (wx.ID_YES == Popup(self, msg,   'Delete ROI?', style=wx.YES_NO)):
            self.onDelROI()
            if self.roi_callback is not None:
                self.roi_callback(roiname, action='delete', roitype='XRF')

    def onRenameROI(self, event=None):
        roiname = self.get_roiname()

        if self.roilist_sel is not None:
            names = self.wids['roilist'].GetStrings()
            names[self.roilist_sel] = roiname
            self.wids['roilist'].Clear()
            for sname in names:
                self.wids['roilist'].Append(sname)
            self.wids['roilist'].SetSelection(self.roilist_sel)

        try:
            self.mca.rois[self.roilist_sel].name = roiname
        except:
            pass


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

        self.plot(self.xdat, self.ydat)
        if self.selected_elem is not None:
            self.onShowLines(elem=self.selected_elem)

    def ShowROIStatus(self, left, right, name='', panel=0):
        if left > right:
            return
        sum = self.ydat[left:right].sum()
        dt = self.mca.real_time
        if self.show_cps:
            sum *= self.mca.real_time

        msg = f"[ {name}  |  Counts={sum:10,.0f} | CPS={(sum/dt):10,.2f} Hz ]"
        self.write_message(msg, panel=panel)

    def ShowROIPatch(self, left, right):
        """show colored XRF Patch:
        Note: ROIs larger than half the energy are not colored"""

        try:
            self.roi_patch.remove()
        except:
            pass

        e = np.zeros(right-left+2)
        r = np.ones(right-left+2)
        e[1:-1] = self.mca.energy[left:right]
        r[1:-1] = self.mca.counts[left:right]
        if self.show_cps:
            r /= self.mca.real_time

        e[0]  = e[1]
        e[-1] = e[-2]
        self.roi_patch = self.plotpanel.axes.fill_between(e, r, zorder=-20,
                                                    label='',
                                           color=self.colors.roi_fillcolor)

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
        self.plotpanel.Refresh()

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

        MenuItem(self, fmenu, 'Show XRF Dataset Browser\tCtrl+B',
                 'Show List of XRF Spectra ',
                 self.onShowXRFBrowser)

        MenuItem(self, fmenu, 'Show Larch Buffer\tCtrl+M',
                 'Show Larch Data/Programming Buffer',
                 self.onShowLarchBuffer)
        fmenu.AppendSeparator()

        MenuItem(self, fmenu, "&Save MCA File\tCtrl+S",
                 "Save GSECARS MCA File",  self.onSaveMCAFile)
        MenuItem(self, fmenu, "&Save ASCII Column File",
                 "Save Column File",  self.onSaveColumnFile)

        MenuItem(self, fmenu,  "Save Plot\tCtrl+I",
                 "Save PNG Image of Plot", self.onSavePNG)
        MenuItem(self, fmenu, "&Copy Plot\tCtrl+C",
                 "Copy Plot Image to Clipboard",
                 self.onCopyImage)
        MenuItem(self, fmenu, 'Page Setup...', 'Printer Setup', self.onPageSetup)
        MenuItem(self, fmenu, 'Print Preview...', 'Print Preview', self.onPrintPreview)
        MenuItem(self, fmenu, "&Print\tCtrl+P", "Print Plot", self.onPrint)

        MenuItem(self, fmenu, "&Inspect \tCtrl+J",
                 " wx inspection tool ",  self.showInspectionTool)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)

        omenu = wx.Menu()
        MenuItem(self, omenu, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range", self.unzoom_all)

        MenuItem(self, omenu, "Configure Plot\tCtrl+K",
                 "Configure Plot Colors, etc", self.plotpanel.configure)

        omenu.AppendSeparator()
        MenuItem(self, omenu, "Hide X-ray Lines",
                 "Hide all X-ray Lines", self.clear_lines)
        MenuItem(self, omenu, "Hide selected ROI ",
                 "Hide selected ROI", self.clear_roihighlight)
        MenuItem(self, omenu, "Hide Markers ",
                "Hide cursor markers", self.clear_markers)


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
                       (omenu, '&Display'),
                       (amenu, '&Analysis')]

    def createMenus(self):
        self.menubar = wx.MenuBar()
        self.createBaseMenus()
        self.createCustomMenus()
        for menu, title in self._menus:
            self.menubar.Append(menu, title)
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE, self.onClose)


    def show_subframe(self, name, frameclass, **opts):
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except Exception:
                del self.subframes[name]
        if not shown:
            self.subframes[name] = frameclass(**opts)
            self.subframes[name].Show()

    def onShowLarchBuffer(self, evt=None):
        f2 = get_font(larger=2)
        self.show_subframe('larch_buffer', LarchFrame)
        self.subframes['larch_buffer'].set_fontsize(f2.GetPointSize())
        self.subframes['larch_buffer'].Show()

    def onShowXRFBrowser(self, evt=None):
        self.show_subframe('xrf_browser', XRFDataBrowser,
                               parent=self, larch=self.larch)

    def onSavePNG(self, event=None):
        if self.plotpanel is not None:
            self.plotpanel.save_figure(event=event)

    def onCopyImage(self, event=None):
        if self.plotpanel is not None:
            self.plotpanel.canvas.Copy_to_Clipboard(event=event)

    def onPageSetup(self, event=None):
        if self.plotpanel is not None:
            self.plotpanel.PrintSetup(event=event)

    def onPrintPreview(self, event=None):
        if self.plotpanel is not None:
            self.plotpanel.PrintPreview(event=event)

    def onPrint(self, event=None):
        if self.plotpanel is not None:
            self.plotpanel.Print(event=event)

    def onClose(self, event=None):
        try:
            if callable(self.exit_callback):
                self.exit_callback()
        except:
            pass

        for name, wid in self.subframes.items():
            if name == 'larch_buffer' and not self.larch_owner:
                continue
            elif hasattr(wid, 'Destroy'):
                try:
                    wid.Destroy()
                except:
                    pass
        if hasattr(self.larch.symtable, '_plotter'):
            wx.CallAfter(self.larch.symtable._plotter.close_all_displays)
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

    def onShowLegend(self, event=None):
        self.plotpanel.conf.show_legend = event.IsChecked()
        self.plotpanel.conf.draw_legend()

    def onKLM(self, event=None):
        """selected K, L, or M Markers"""
        if self.selected_elem is not None:
            self.onShowLines(elem=self.selected_elem)

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
        en, label = self.wids['xray_linesdata'][item]

        dlabel = f'{self.selected_elem} {label}'

        newh = self.displayed_lines.get(dlabel, None)
        if newh is None:
            return
        if self.highlight_xrayline is not None:
            h = self.highlight_xrayline
            try:
                elem, lab = h.get_label().split(' ')
            except:
                lab = None
            col = self.colors.major_elinecolor
            if lab in XRFLines.K_minor+XRFLines.L_minor:
                col = self.colors.minor_elinecolor
            h.set_color(col)
            h.set_linewidth(1.5)
            h.set_zorder(-5)
        newh.set_color(self.colors.emph_elinecolor)
        newh.set_linewidth(2.0)
        newh.set_zorder(-10)
        self.highlight_xrayline = newh
        self.energy_for_zoom = en
        if self.plotpanel.conf.show_legend:
            self.plotpanel.toggle_legend()
            self.plotpanel.toggle_legend()
        self.draw()

    def onShowLines(self, event=None, elem=None):
        if elem is None:
            elem  = event.GetString()

        vline = self.plotpanel.axes.axvline
        elines = self.larch.symtable._xray.xray_lines(elem)

        self.selected_elem = elem
        self.clear_lines()
        self.energy_for_zoom = None
        xlines = self.wids['xray_lines']
        if xlines is not None:
            xlines.DeleteAllItems()
        self.wids['xray_linesdata'] = []
        minors, majors = [], []
        lines = XRFLines
        line_data = {}
        for line in (lines.K_major+lines.K_minor+lines.L_major+
                     lines.L_minor+lines.M_major):
            line_data[line] = line, -1, 0, '', ''
            if line in elines:
                dat = elines[line]
                line_data[line] = line, dat[0], dat[1], dat[2], dat[3]

        if self.wids['kmajor'].IsChecked():
            majors.extend([line_data[l] for l in lines.K_major])
        if self.wids['kminor'].IsChecked():
            minors.extend([line_data[l] for l in lines.K_minor])
        if self.wids['lmajor'].IsChecked():
            majors.extend([line_data[l] for l in lines.L_major])
        if self.wids['lminor'].IsChecked():
            minors.extend([line_data[l] for l in lines.L_minor])
        if self.wids['mmajor'].IsChecked():
            majors.extend([line_data[l] for l in lines.M_major])

        self.saved_lines = majors[:] + minors[:]
        erange = [max(lines.e_min, self.xdat.min()),
                  min(lines.e_max, self.xdat.max())]
        self.displayed_lines = {}
        view_mid, view_range, d1, d2 = self._getlims()
        view_emin = view_mid - view_range/2.0
        view_emax = view_mid + view_range/2.0
        for label, eev, frac, ilevel, flevel in majors:
            e = float(eev) * 0.001
            if (e >= erange[0] and e <= erange[1]):
                l = vline(e, color= self.colors.major_elinecolor,
                          linewidth=1.50, zorder=-5)
                dlabel = f'{elem} {label}'
                l.set_label(dlabel)
                self.displayed_lines[dlabel] = l
                dat = (label, "%.4f" % e, "%.4f" % frac,
                       "%s->%s" % (ilevel, flevel))
                self.wids['xray_linesdata'].append((e, label))
                if xlines is not None:
                    xlines.AppendItem(dat)

                self.major_markers.append(l)
                if (self.energy_for_zoom is None and
                    e > view_emin and e < view_emax):
                    self.energy_for_zoom = e

        for label, eev, frac, ilevel, flevel in minors:
            e = float(eev) * 0.001
            if (e >= erange[0] and e <= erange[1]):
                l = vline(e, color= self.colors.minor_elinecolor,
                          linewidth=1.25, zorder=-7, label='')
                dlabel = f'{elem} {label}'
                l.set_label(dlabel)
                self.displayed_lines[dlabel] = l
                dat = (label,  "%.4f" % e, "%.4f" % frac,
                       "%s->%s" % (ilevel, flevel))

                self.wids['xray_linesdata'].append((e, label))
                if xlines is not None:
                    xlines.AppendItem(dat)
                self.minor_markers.append(l)

        if not self.wids['holdbtn'].GetValue():
            self.wids['holdbtn'].SetLabel("Hold %s" % elem)
        elif self.hold_lines is not None:
            for label, eev, frac, ilevel, flevel in self.hold_lines:
                e = float(eev) * 0.001
                if (e >= erange[0] and e <= erange[1]):
                    l = vline(e, color=self.colors.hold_elinecolor,
                              linewidth=1.5, zorder=-20, dashes=(3, 3), label='')
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

        if self.plotpanel.conf.show_legend:
            self.plotpanel.toggle_legend()
            self.plotpanel.toggle_legend()
        self.draw()

    def onPileupPrediction(self, event=None):
        val = event.IsChecked()
        if val != self.show_pileup:
            self.show_pileup = val
            self.replot()

    def onEscapePrediction(self, event=None):
        val = event.IsChecked()
        if val != self.show_escape:
            self.show_escape = val
            self.replot()

    def onYAxis(self, event=None):
        if event is not None:
            self.show_yaxis = event.IsChecked()

        ax = self.plotpanel.axes
        ax.yaxis.set_major_formatter(FuncFormatter(self._formaty))
        ax.yaxis.set_visible(self.show_yaxis)
        ax.spines['right'].set_visible(False)
        ax.yaxis.set_ticks_position('left')
        self.draw()

    def _formaty(self, val, index=0, **kws):
        try:
            decade = int(np.log10(val))
        except:
            decade = 0
        scale = 10**decade
        out = outx = f"%.1fe%i" % (val/scale, decade)
        if decade < -1.5:
            out = f"{val:.2f}"
        elif decade < -0.5:
            out = f"{val:.1f}"
        elif decade < 0.5:
            out = f"{val:.0f}"
        elif abs(decade) < 5:
            out = f"{val:.0f}"
        return out

    def replot(self, event=None):
        for ix, gname in enumerate(self.plotted_groups):
            self.plotmca(self.xrf_files[gname], newplot=(ix==0))

    def onLogLinear(self, event=None):
        self.ylog_scale = event.IsChecked()
        roiname = None
        if self.selected_roi is not None:
            roiname = self.selected_roi.name
        self.plot(self.xdat, self.ydat)
        if self.selected_elem is not None:
            self.onShowLines(elem=self.selected_elem)
        if roiname is not None:
            self.onROI(label=roiname)
        for gname in self.plotted_groups[1:]:
            mca = self.xrf_files[gname]
            self.oplot(mca.energy, mca.counts, label=mca.label)

    def plotmca(self, mca, title=None, set_title=True, newplot=True,
                fullrange=False,  **kws):
        if newplot:
            kws['new'] = True
            self.mca = mca
            self.plotted_groups = [mca.label]
        else:
            self.plotted_groups.append(mca.label)

        label = kws.pop('label', None)
        if label is None:
            label = getattr(mca, 'label', 'unknkown')

        self.xview_range = self.plotpanel.axes.get_xlim()
        if self.xview_range == (0.0, 1.0):
            self.xview_range = (min(mca.energy), max(mca.energy))


        yval = mca.counts[:]
        if self.show_cps:
            yval = yval/float(mca.real_time)

        atitles = []
        if newplot:
            if getattr(mca, 'title', None) is not None:
                atitles.append(bytes2str(mca.title))
            if getattr(mca, 'filename', None) is not None:
                atitles.append(f" File={mca.filename}")
            if getattr(mca, 'npixels', None) is not None:
                atitles.append(f" {mca.npixels} Pixels")
            if getattr(mca, 'real_time', None) is not None:
                try:
                    rtime_str = f" RealTime={mca.real_time:.3f} sec"
                except ValueError:
                    rtime_str = f" RealTime={mca.real_time} sec"
                atitles.append(rtime_str)

            try:
                self.plot(mca.energy, yval, label=label, **kws)
            except ValueError:
                pass
        else:
            try:
                self.oplot(mca.energy, yval, label=label, **kws)
            except ValueError:
                pass

        if newplot:
            if len(atitles) > 0:
                self.SetTitle(' '.join(atitles))

            if self.show_pileup:
                self.mca.predict_pileup()
                pileup = self.mca.pileup[:]
                if self.show_cps:
                    pileup /= self.mca.real_time
                self.oplot(self.mca.energy, pileup,
                        color=self.colors.pileup_color, label='pileup prediction')

            if self.show_escape:
                self.mca.predict_escape()
                escape = self.mca.escape[:]
                if self.show_cps:
                    escape /= self.mca.real_time
                self.oplot(self.mca.energy, escape,
                       color=self.colors.escape_color, label='escape prediction')



    def plot(self, x, y=None, mca=None, with_rois=True, label=None, **kws):
        if mca is not None:
            self.mca = mca
        mca = self.mca
        panel = self.plotpanel

        kwargs = {'xmin': 0,
                  'show_grid': self.show_grid,
                  'zorder': 100,
                  'linewidth': 2.5,
                  'delay_draw': True,
                  'ylog_scale': self.ylog_scale,
                  'xlabel': 'E (keV)',
                  'axes_style': 'bottom',
                  'color': self.colors.spectra_color}
        if self.show_yaxis:
            kwargs['ylabel'] = 'Counts/sec (Hz)' if self.show_cps else 'Counts'
        kwargs.update(kws)

        self.xdat = 1.0*x[:]
        self.ydat = 1.0*y[:]
        self.ydat[np.where(self.ydat<1.e-9)] = 1.e-9

        kwargs['ymax'] = max(self.ydat)*1.25
        self.ymax = kwargs['ymax']
        kwargs['ymin'] = self.ymin
        kwargs['xmax'] = max(self.xdat)
        kwargs['xmin'] = min(self.xdat)
        if self.xview_range is not None:
            kwargs['xmin'] = self.xview_range[0]
            kwargs['xmax'] = self.xview_range[1]

        if label is None:
            label = getattr(self.mca, 'label', 'spectrum')
        kwargs['label'] = label
        panel.plot(self.xdat, self.ydat, **kwargs)
        if with_rois and mca is not None:
            self.set_roilist(mca=mca)
            yroi = -1.0*np.ones(len(y))
            max_width = 0.5*len(self.mca.energy) # suppress very large ROIs
            for r in mca.rois:
                if ((r.left, r.right) in ((0, 0), (-1, -1)) or
                    (r.right - r.left) > max_width):
                    continue
                yroi[r.left:r.right] = y[r.left:r.right]
            yroi = np.ma.masked_less(yroi, 0)
            xroi = 1.0*x[:]
            xroi[yroi< 0.0] = np.nan
            if yroi.max() > 0:
                kwargs['color'] = self.colors.roi_color
                kwargs['label'] = 'rois'
                kwargs['zorder'] = 110
                panel.oplot(xroi, yroi, **kwargs)


        yscale = {False:'linear', True:'log'}[self.ylog_scale]
        panel.set_viewlimits()
        panel.set_viewlimits()
        panel.cursor_mode = 'zoom'
        panel.conf.enable_grid(self.show_grid)

        self.onYAxis()

        # panel.canvas.Refresh()

    def get_mca(self, name):
        """get MCA from filename in the xrf_files"""
        return self.xrf_files.get(name, None)

    def update_mca(self, counts, mcalabel=None, energy=None,
                   with_rois=True, draw=True):
        """update counts for an mca, and update plot"""
        self.show_cps = False
        mca, index = None, 0
        if mcalabel in self.plotted_groups:
            mca = self.xrf_files.get(mcalabel, None)
            index = self.plotted_groups.index(mcalabel)

        elif mcaname is not None:
            xrfgroup = self.larch.symtable.get_group(XRFGROUP)
            mca = getattr(xrfgroup, xrfgroup.mca, None)
            mcalabel = xrfgroup.mca

        if mca is None:
            mca = self.mca
            index = 0

        mca.counts = 1.0*counts[:]

        if energy is None:
            energy = 1.0*mca.energy[:]
        else:
            mca.energy = 1.0*energy[:]

        nrois = len(mca.rois)
        roi_index_offset = 0
        if index == 0 and with_rois and nrois > 0:
            xnpts = 1.0/len(energy)
            yroi = -1*np.ones(len(counts))
            for r in mca.rois:
                if xnpts*(r.right - r.left) > 0.5:
                    continue
                yroi[r.left:r.right] = counts[r.left:r.right]
            yroi = np.ma.masked_less(yroi, 0)
            self.plotpanel.update_line(1, mca.energy, yroi, draw=False,
                                   update_limits=False)
            roi_index_offset = 1
        if index > 1 and roi_index_offset > 0:
            index = index + roi_index_offset
        self.plotpanel.update_line(index, energy, counts, draw=False,
                               update_limits=False)
        if index == 0:
            self.max_counts = max(counts)
        else:
            try:
                self.max_counts = max(self.max_counts, max(counts))
            except:
                pass

        self.plotpanel.axes.set_ylim(self.ymin, 1.25*self.max_counts)
        self.update_status()
        if draw:
            self.draw()

    def oplot(self, x, y, color=None, label=None, **kws):
        xdat = 1.0*x[:]
        ydat = 1.0*y[:]
        ymax = max(ydat)*1.25
        if hasattr(self, 'ymax'):
            self.ymax = max(self.ymax, max(ydat))*1.25

        kws.update({'label': label, 'ymax': self.ymax,
                    'ymin': self.ymin, 'axes_style': 'bottom',
                    'ylog_scale': self.ylog_scale})
        self.plotpanel.oplot(xdat, ydat, **kws)

    def onReadMCAFile(self, event=None):
        dlg = wx.FileDialog(self, message="Open MCA File for reading",
                            defaultDir=get_cwd(),
                            wildcard=FILE_WILDCARDS,
                            style = wx.FD_OPEN|wx.FD_CHANGE_DIR)

        filename = None
        if dlg.ShowModal() == wx.ID_OK:
            filename = Path(dlg.GetPath()).absolute().as_posix()
        dlg.Destroy()

        if filename is None:
            return

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

        deffile = fix_filename(Path(deffile).name)
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

        deffile = fix_filename(Path(deffile).name)
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

    def showInspectionTool(self, event=None):
        app = wx.GetApp()
        app.ShowInspectionTool()

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
                            defaultDir=get_cwd(),
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
        return path


class XRFApp(LarchWxApp):
    def __init__(self, filename=None, **kws):
        self.filename = filename
        LarchWxApp.__init__(self, **kws)

    def createApp(self):
        frame = XRFDisplayFrame(filename=self.filename)
        frame.Show()
        self.SetTopWindow(frame)
        return True
