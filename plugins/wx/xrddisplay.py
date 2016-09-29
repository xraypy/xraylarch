#!/usr/bin/env python
"""
GUI Frame for XRD display

"""

import sys
import os
import time
import copy
from functools import partial
from threading import Thread
import socket

from functools import partial
import wx
import wx.lib.mixins.inspection
import wx.lib.scrolledpanel as scrolled
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception
import wx.lib.colourselect  as csel

is_wxPhoenix = 'phoenix' in wx.PlatformInfo

import math
import numpy as np
from scipy import constants
import matplotlib
from matplotlib.ticker import LogFormatter, FuncFormatter
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg

from wxmplot import ImageFrame, PlotFrame
from wxmplot.imagepanel import ImagePanel
from wxmplot.imageconf import ColorMap_List, Interp_List
from wxmplot.colors import rgb2hex

from wxutils import (SimpleText, TextCtrl, Button, Popup)


HAS_PLOT = False
try:
    from wxmplot import PlotPanel
    HAS_PLOT = True
except ImportError:
    pass
HAS_DV = False
try:
    import wx.dataview as dv
    HAS_DV = True
except:
    pass

#import larch
from larch import Interpreter, site_config
from wxutils import (SimpleText, EditableListBox, Font,
                     pack, Popup, Button, get_icon, Check, MenuItem,
                     Choice, FileOpen, FileSave, fix_filename, HLine,
                     GridPanel, CEN, LEFT, RIGHT)

from larch_plugins.math import index_of
from larch_plugins.xrd import calc_q_to_d,calc_q_to_2th,calc_d_to_q,calc_2th_to_q
from larch_plugins.xrd import struc_from_cif,calc_all_F,XRDSearchGUI

import matplotlib as plt

FILE_ALREADY_READ = """    The File
       '%s'
    has already been read.
    """

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

## keep menu options same for now
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

class XRD2D_DisplayFrame(ImageFrame):
    """
    MatPlotlib Image Display on a wx.Frame, using ImagePanel
    """

    def __init__(self, _larch=None, parent=None, size=None, mode='intensity',
                 move_callback=None, save_callback=None,
                 show_xsections=False, cursor_labels=None,
                 output_title='Image',   **kws):

        self.xrmfile = None
        self.map = None
        self.move_callback = move_callback
        self.save_callback = save_callback

        self.larch = _larch
        if self.larch is None:
            self.init_larch()
            
        ImageFrame.__init__(self, parent=parent, size=size,
                            cursor_labels=cursor_labels, mode=mode,
                            output_title=output_title, **kws)

        self.panel.cursor_mode = 'zoom'
        self.panel.xaxis = 'q'
        self.panel.report_leftdown = self.report_leftdown
        self.panel.report_motion   = self.report_motion


        self.prof_plotter = None
        self.zoom_ini =  None
        self.lastpoint = [None, None]
        self.this_point = None
        self.rbbox = None

    def display(self, map, xrmfile=None, ai=None, mask=None, **kws):
        self.xrmfile = xrmfile
        self.map = map
        self.title = ''
        if 'title' in kws:
            self.title = kws['title']
        ImageFrame.display(self, map, **kws)

        if self.panel.conf.auto_contrast:
            self.set_contrast_levels()
        self.ai = ai
        self.mask = mask
        if np.shape(self.mask) == np.shape(map):
            self.masked_map = map * (np.ones(np.shape(self.mask))-mask.value)
        
        self.panel.xdata = np.arange(map.shape[0])
        self.panel.ydata = np.arange(map.shape[0])

    def init_larch(self):
        if self.larch is None:
            self.larch = Interpreter()

    def prof_motion(self, event=None):
        if not event.inaxes or self.zoom_ini is None:
            return
        try:
            xmax, ymax  = event.x, event.y
        except:
            return

        xmin, ymin, xd, yd = self.zoom_ini
        if event.xdata is not None:
            self.lastpoint[0] = event.xdata
        if event.ydata is not None:
            self.lastpoint[1] = event.ydata

        yoff = self.panel.canvas.figure.bbox.height
        ymin, ymax = yoff - ymin, yoff - ymax

        zdc = wx.ClientDC(self.panel.canvas)
        zdc.SetLogicalFunction(wx.XOR)
        zdc.SetBrush(wx.TRANSPARENT_BRUSH)
        zdc.SetPen(wx.Pen('White', 2, wx.SOLID))
        zdc.ResetBoundingBox()
        if not is_wxPhoenix:
            zdc.BeginDrawing()


        # erase previous box
        if self.rbbox is not None:
            zdc.DrawLine(*self.rbbox)
        self.rbbox = (xmin, ymin, xmax, ymax)
        zdc.DrawLine(*self.rbbox)
        if not is_wxPhoenix:
            zdc.EndDrawing()

    def prof_leftdown(self, event=None):
        self.report_leftdown(event=event)
        if event.inaxes and len(self.map.shape) == 2:
            self.lastpoint = [None, None]
            self.zoom_ini = [event.x, event.y, event.xdata, event.ydata]

    def prof_leftup(self, event=None):
        if len(self.map.shape) != 2:
            return
        if self.rbbox is not None:
            zdc = wx.ClientDC(self.panel.canvas)
            zdc.SetLogicalFunction(wx.XOR)
            zdc.SetBrush(wx.TRANSPARENT_BRUSH)
            zdc.SetPen(wx.Pen('White', 2, wx.SOLID))
            zdc.ResetBoundingBox()
            if not is_wxPhoenix:
                zdc.BeginDrawing()
            zdc.DrawLine(*self.rbbox)
            if not is_wxPhoenix:
                zdc.EndDrawing()

            self.rbbox = None

        if self.zoom_ini is None or self.lastpoint[0] is None:
            return

        x0 = int(self.zoom_ini[2])
        x1 = int(self.lastpoint[0])
        y0 = int(self.zoom_ini[3])
        y1 = int(self.lastpoint[1])
        dx, dy = abs(x1-x0), abs(y1-y0)

        self.lastpoint, self.zoom_ini = [None, None], None
        if dx < 2 and dy < 2:
            self.zoom_ini = None
            return

        outdat = []

        if dy > dx:
            _y0 = min(int(y0), int(y1+0.5))
            _y1 = max(int(y0), int(y1+0.5))

            for iy in range(_y0, _y1):
                ix = int(x0 + (iy-int(y0))*(x1-x0)/(y1-y0))
                outdat.append((ix, iy))
        else:
            _x0 = min(int(x0), int(x1+0.5))
            _x1 = max(int(x0), int(x1+0.5))
            for ix in range(_x0, _x1):
                iy = int(y0 + (ix-int(x0))*(y1-y0)/(x1-x0))
                outdat.append((ix, iy))
        x, y, z = [], [], []

        for ix, iy in outdat:
            x.append(ix)
            y.append(iy)
            z.append(self.panel.conf.data[iy,ix])
        self.prof_dat = dy>dx, outdat

        if self.prof_plotter is not None:
            try:
                self.prof_plotter.Raise()
                self.prof_plotter.clear()

            except (AttributeError, PyDeadObjectError):
                self.prof_plotter = None

        if self.prof_plotter is None:
            self.prof_plotter = PlotFrame(self, title='Profile')
            self.prof_plotter.panel.report_leftdown = self.prof_report_coords

        xlabel, y2label = 'Pixel (x)',  'Pixel (y)'

        if dy > dx:
            x, y = y, x
            xlabel, y2label = y2label, xlabel
        self.prof_plotter.panel.clear() # reset_config()

        if len(self.title) < 1:
            self.title = os.path.split(self.xrmfile.filename)[1]

        opts = dict(linewidth=2, marker='+', markersize=3,
                    show_legend=True, xlabel=xlabel)
        self.prof_plotter.plot(x, z, title=self.title, color='blue',
                               zorder=20, xmin=min(x)-3, xmax=max(x)+3,
                               ylabel='counts', label='counts', **opts)

        self.prof_plotter.oplot(x, y, y2label=y2label, label=y2label,
                              zorder=3, side='right', color='#771111', **opts)

        self.prof_plotter.panel.unzoom_all()
        self.prof_plotter.Show()
        self.zoom_ini = None

        self.panel.cursor_mode = 'zoom'

    def prof_report_coords(self, event=None):
        """override report leftdown for profile plotter"""
        if event is None:
            return
        ex, ey = event.x, event.y
        msg = ''
        plotpanel = self.prof_plotter.panel
        axes  = plotpanel.fig.get_axes()[0]
        write = plotpanel.write_message
        try:
            x, y = axes.transData.inverted().transform((ex, ey))
        except:
            x, y = event.xdata, event.ydata

        if x is None or y is None:
            return

        
        if self.ai is None:
            _point = 0, 0, 0
            for ix, iy in self.prof_dat[1]:
                if (int(x) == ix and not self.prof_dat[0] or
                    int(x) == iy and self.prof_dat[0]):
                    _point = (ix, iy,
                                  self.panel.conf.data[iy, ix])
                msg = "Pixel [%i, %i], Intensity= %g" % _point
        else:
            ai = self.ai
            xcenter = ai._poni2/ai.detector.pixel2        ## units pixels
            ycenter = ai._poni1/ai.detector.pixel1        ## units pixels
            _point = 0, 0, 0, 0, 0
            for ix, iy in self.prof_dat[1]:
                if (int(x) == ix and not self.prof_dat[0] or
                    int(x) == iy and self.prof_dat[0]):
                    x_pix = ix - xcenter                      ## units pixels
                    y_pix = iy - ycenter                      ## units pixels
                    x_m = x_pix * ai.detector.pixel2          ## units m
                    y_m = y_pix * ai.detector.pixel1          ## units m
                    twth = np.arctan2(math.sqrt(x_m**2 + y_m**2),ai._dist)  ## radians
                    twth = np.degrees(twth)                                 ## units degrees
                    eta  = np.arctan2(y_m,x_m)                              ## units radians
                    eta  = np.degrees(eta)                                  ## units degrees
                    _point = (ix, iy, twth, eta, self.panel.conf.data[iy, ix])
            msg = 'Pixel [%i, %i], 2TH=%.2f, ETA=%.1f, Intensity= %g' % _point
        write(msg,  panel=0)

    def report_leftdown(self, event=None):
        if event is None:
            return
        if event.xdata is None or event.ydata is None:
            return

        ix, iy = int(round(event.xdata)), int(round(event.ydata))
        conf = self.panel.conf
        if conf.flip_ud:  iy = conf.data.shape[0] - iy
        if conf.flip_lr:  ix = conf.data.shape[1] - ix

        self.this_point = None
        msg = ''
        if (ix >= 0 and ix < conf.data.shape[1] and
            iy >= 0 and iy < conf.data.shape[0]):
            pos = ''
            pan = self.panel
            labs, vals = [], []
            if pan.xdata is not None:
                labs.append(pan.xlab)
                vals.append(pan.xdata[ix])
            if pan.ydata is not None:
                labs.append(pan.ylab)
                vals.append(pan.ydata[iy])
            dval = conf.data[iy, ix]
            if len(pan.data_shape) == 3:
                dval = "%.4g, %.4g, %.4g" % tuple(dval)
            else:
                dval = "%.4g" % dval
            if pan.xdata is not None and pan.ydata is not None:
                self.this_point = (ix, iy)

            if self.ai is None:
                msg = "Pixel [%i, %i], Intensity=%s " % (ix, iy, dval)
            else:
                ai = self.ai
                xcenter = ai._poni2/ai.detector.pixel2        ## units pixels
                ycenter = ai._poni1/ai.detector.pixel1        ## units pixels
                x_pix = ix - xcenter                          ## units pixels
                y_pix = iy - ycenter                          ## units pixels
                x_m = x_pix * ai.detector.pixel2                        ## units m
                y_m = y_pix * ai.detector.pixel1                        ## units m
                twth = np.arctan2(math.sqrt(x_m**2 + y_m**2),ai._dist)  ## radians
                twth = np.degrees(twth)                                 ## units degrees
                eta  = np.arctan2(y_m,x_m)                              ## units radians
                eta  = np.degrees(eta)                                  ## units degrees
                msg = 'Pixel [%i, %i], 2TH=%.2f deg., ETA=%.1f deg., Intensity= %s' % (ix, 
                                      iy, twth, eta, dval)
        self.panel.write_message(msg, panel=0)

    def report_motion(self, event=None):
        return

    def CustomConfig(self, panel, sizer, irow):
        """config panel for left-hand-side of frame"""
        conf = self.panel.conf
        lpanel = panel
        lsizer = sizer
        labstyle = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND

        self.MskCkBx = wx.CheckBox(panel, label='Apply mask?')
        self.MskCkBx.Bind(wx.EVT_CHECKBOX, self.onApplyMask)
        sizer.Add(self.MskCkBx, (irow+1,0), (1,4), labstyle, 3)

        self.LoadBtn = wx.Button(panel, label='Load New Mask')
        self.LoadBtn.Bind(wx.EVT_BUTTON, self.onLoadMask)
        sizer.Add(self.LoadBtn, (irow+2,0), (1,4), labstyle, 3)

        self.ReCalc1D = wx.Button(panel, label='Replot 1DXRD')
        self.ReCalc1D.Bind(wx.EVT_BUTTON, self.onReplot1DXRD)
        sizer.Add(self.ReCalc1D, (irow+3,0), (1,4), labstyle, 3)

    def onApplyMask(self, event):
        '''
        Applies mask to 2DXRD map
        mkak 2016.09.29
        '''
        if event.GetEventObject().GetValue():
            if self.masked_map is None:
                print('Mask file not defined.')
                
                question = 'No mask found in map file. Would you like to load a new file now?'
                caption = 'Load mask file?'
                dlg = wx.MessageDialog(self, question, caption, wx.YES_NO | wx.ICON_QUESTION)
                print 'answer:', dlg.ShowModal() # == wx.ID_YES
                read = dlg.ShowModal()
                dlg.Destroy()
                if read == wx.ID_YES:
                    self.onLoadMask()

                self.MskCkBx.SetValue(False)
            else:
                ImageFrame.display(self, self.masked_map)

        else:
            ImageFrame.display(self, self.map)        
       
    def onLoadMask(self, evt=None):

        wildcards = 'pyFAI mask (*.edf)|*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD mask file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        edffile, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            edffile = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:

            print('Reading mask file: %s' % edffile)
            try:
                import fabio
                self.mask = fabio.open(edffile).data
                self.masked_map = self.map * (np.ones(np.shape(self.mask))-self.mask)
                self.MskCkBx.SetValue(True)
                ImageFrame.display(self, self.masked_map)
            except:
                print('File must be .edf format; user must have fabio installed.')
            
            ## Can this be called here?
            #readEDFfile(self,name='mask',keyword='maskfile')
            #add_calibration()

    def onReplot1DXRD(self, evt=None):

        print('How do I do this?')



class XRD1D_DisplayFrame(wx.Frame):
    _about = """XRD Viewer
  Margaret Koker <koker @ cars.uchicago.edu>
  """
    main_title = 'XRD Display'
    def __init__(self, _larch=None, parent=None, xrd_file=None,
                 size=(725, 450), axissize=None, axisbg=None,
                 title='XRD Display', exit_callback=None,
                 output_title='XRD', **kws):

        if size is None: size = (725, 450)
        wx.Frame.__init__(self, parent=parent,
                          title=title, size=size,  **kws)
                          
        self.marker_color = '#77BB99'
        self.spectra_color = '#0000AA'

        self.subframes = {}
        self.data = None
        self.title = title
        self.plotframe = None
        self.wids = {}
        self.larch = _larch
        if self.larch is None:
            self.init_larch()
        self._xrdgroup = self.larch.symtable.new_group('_xrds')
        self.exit_callback = exit_callback
        self.selected_elem = None
        self.xrd = None
        self.xrd2 = None
        self.xdata = np.arange(2048)*0.015
        self.ydata = np.ones(2048)*1.e-4
        self.x2data = None
        self.y2data = None
        self.major_markers = []
        self.minor_markers = []
        self.hold_markers = []
        self.xunit = 'q'
        self.xlabel = None

        self.hold_lines = None
        self.saved_lines = None
        self.x_for_zoom = None
        self.xview_range = None
        self.show_yaxis = True
        self.xmarker_left = None
        self.xmarker_right = None

        self.highlight_xrayline = None
        self.highlight_xrayline = None
        self.cursor_markers = [None, None]
        self.ylog_scale = False
        self.SetTitle("%s: %s " % (self.main_title, title))

        self._menus = []
        self.createMainPanel()
        self.createMenus()
        self.SetFont(Font(9, serif=True))
        self.statusbar = self.CreateStatusBar(4)
        self.statusbar.SetStatusWidths([-5, -3, -3, -4])
        statusbar_fields = ["XRD Display", " ", " ", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)
        if xrd_file is not None:
            self.xrd = gsexrd_group(xrd_file, _larch=self.larch)
            self._xrdgroup.xrd1 = self.xrd
            self._xrdgroup.xrd2 = None
            self.plot1Dxrd(self.xrd, show_xrd2=False)

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
        if self.xrd is not None:
            if self.xunit == '2th':
                q = calc_2th_to_q(x,self.xrd.wavelength*1e10)
            elif self.xunit == 'd':
                q = calc_d_to_q(x)
            else:
                q = x
            ix = index_of(self.xrd.data1D[0], q)

        if side == 'right':
            self.xmarker_right = ix
        elif side == 'left':
            self.xmarker_left = ix
        self.eventx = x
        self.eventy = y

        if self.xmarker_left is not None and self.xmarker_right is not None:
            ix1, ix2 = self.xmarker_left, self.xmarker_right
            self.xmarker_left  = min(ix1, ix2)
            self.xmarker_right = max(ix1, ix2)

        if side == 'left':
            self.x_for_zoom = np.array(self.xrd.data1D)[0,ix]
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
        "remove XRD background"
        self.xrd2 = None
        self.plot1Dxrd(self.xrd)

    def update_status(self):
        fmt = "{:s}: {:s}={:.3f} {:s}, Cts={:,.0f}".format
        if (self.xmarker_left is None and self.xmarker_right is None):
            return

        log = np.log10
        axes= self.panel.axes
        def draw_ymarker_range(idx, x, y):
            ymin, ymax = self.panel.axes.get_ylim()
            y1 = min(1.0,ymin)
            if self.ylog_scale:
                y1 = log(y1)
                y2 = (log(y)-log(ymin))/(log(ymax)-log(ymin)+2.e-9)
            else:
                y2 = (y-ymin)/(ymax-ymin+0.0002)
            if self.cursor_markers[idx] is not None:
                try:
                    self.cursor_markers[idx].remove()
                except:
                    pass
            self.cursor_markers[idx] = axes.axvline(x, y1, y2, linewidth=2.0,
                                                    color=self.marker_color)

        def correct_units(ix):
            
            if self.xunit == '2th':
                 xlbl = self.xunit
                 xunt = 'deg'
                 x = calc_q_to_2th(self.xdata[ix],self.xrd.wavelength*1e10)
            elif self.xunit == 'd':
                 xlbl = self.xunit
                 xunt = 'A'
                 x = calc_q_to_d(self.xdata[ix])
            else:
                 xlbl = 'q'
                 xunt = '1/A'
                 x = self.xdata[ix]
            y = self.ydata[ix]
                 
            return x,y,xlbl,xunt

        if self.xmarker_left is not None:

            ix = self.xmarker_left
            x,y,xlbl,xunt = correct_units(ix)

            draw_ymarker_range(0, x, y)
            self.write_message(fmt("L", xlbl, x, xunt, y), panel=1)

        if self.xmarker_right is not None:
            ix = self.xmarker_right
            x,y,xlbl,xunt = correct_units(ix)

            draw_ymarker_range(1, x, y)
            self.write_message(fmt("R", xlbl, x, xunt, y), panel=2)

        if self.xrd is None:
            return



    def createPlotPanel(self):
        """xrd plot window"""
        pan = PlotPanel(self, fontsize=7,
                        axisbg='#FEFEFE',
                        output_title='test.xrd',
                        messenger=self.write_message)
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

        searchpanel = self.createSearchPanel()

        labstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM|wx.EXPAND
        ctrlstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM
        txtstyle=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE|wx.TE_PROCESS_ENTER
        Font9  = Font(9)
        Font10 = Font(10)
        Font11 = Font(11)

        plttitle = txt(ctrlpanel, 'Plot Parameters', font=Font10, size=200)
        
        # y scale
        yscalepanel = wx.Panel(ctrlpanel, name='YScalePanel')
        ysizer = wx.BoxSizer(wx.HORIZONTAL)
        ytitle = txt(yscalepanel, ' Y Axis:', font=Font10, size=80)
        yspace = txt(yscalepanel, ' ', font=Font10, size=20)
        ylog   = Choice(yscalepanel, size=(80, 30), choices=['linear', 'log'],
                      action=self.onLogLinear)
        yaxis  = Check(yscalepanel, ' Show Y Scale ', action=self.onYAxis,
                      default=True)

        self.wids['show_yaxis'] = yaxis
        ysizer.Add(ytitle,  0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
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

        # x scale
        xscalepanel = wx.Panel(ctrlpanel, name='XScalePanel')
        xsizer = wx.BoxSizer(wx.HORIZONTAL)
        xtitle = txt(xscalepanel, ' X Axis:', font=Font10, size=80)
        xspace = txt(xscalepanel, ' ', font=Font10, size=20)

        self.xaxis = wx.RadioBox(xscalepanel, -1, '',wx.DefaultPosition, wx.DefaultSize,
                                     ('q','2th','d'),
                                     1, wx.RA_SPECIFY_ROWS)
        self.xaxis.Bind(wx.EVT_RADIOBOX, self.onXaxis)

        xsizer.Add(xtitle,     0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        xsizer.Add(xspace,     0, wx.EXPAND|wx.ALL, 0)
        xsizer.Add(self.xaxis, 0, wx.EXPAND|wx.ALL, 0)
        pack(xscalepanel, xsizer)
        
###########################
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(plttitle, 0, wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)
        sizer.Add(yscalepanel,         0, wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)
        sizer.Add(xscalepanel,         0, wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)
        sizer.Add(zoompanel,           0, wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)
        sizer.Add(lin(ctrlpanel, 195), 0, labstyle)
        sizer.Add(searchpanel,         0, wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL)

        pack(ctrlpanel, sizer)
        return ctrlpanel

    def createSearchPanel(self):
        searchpanel = wx.Panel(self, name='Search Panel')

        labstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM|wx.EXPAND
        ctrlstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM
        txtstyle=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE|wx.TE_PROCESS_ENTER
        Font9  = Font(9)
        Font10 = Font(10)
        Font11 = Font(11)

        plttitle = txt(searchpanel, 'XRD Reference Data', font=Font11, size=200)

        # Load buttons
        loadpanel = wx.Panel(searchpanel, name='LoadPanel')
        lsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        l1 = Button(loadpanel, 'Search Database', size=(120, 30), action=self.onSearchDB)
        l2 = Button(loadpanel, 'Load CIF',  size=(120, 30), action=self.onLoadCIF)

        lsizer.Add(l1,      0, wx.EXPAND|wx.ALL, 0)
        lsizer.Add(l2,      0, wx.EXPAND|wx.ALL, 0)
        pack(loadpanel, lsizer)
# 
#         # x scale
#         xscalepanel = wx.Panel(searchpanel, name='XScalePanel')
#         xsizer = wx.BoxSizer(wx.HORIZONTAL)
#         xtitle = txt(xscalepanel, ' X Axis:', font=Font10, size=80)
#         xspace = txt(xscalepanel, ' ', font=Font10, size=20)
# 
#         self.xaxis = wx.RadioBox(xscalepanel, -1, '',wx.DefaultPosition, wx.DefaultSize,
#                                      ('q','2th','d'),
#                                      1, wx.RA_SPECIFY_ROWS)
#         self.xaxis.Bind(wx.EVT_RADIOBOX, self.onXaxis)
# 
#         xsizer.Add(xtitle,     0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
#         xsizer.Add(xspace,     0, wx.EXPAND|wx.ALL, 0)
#         xsizer.Add(self.xaxis, 0, wx.EXPAND|wx.ALL, 0)
#         pack(xscalepanel, xsizer)
        
###########################
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(plttitle, 0, wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL)
        sizer.Add(lin(searchpanel, 195), 0, labstyle)
#         sizer.Add(xscalepanel,         0, wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL)
#         sizer.Add(lin(searchpanel, 195), 0, labstyle)
#         sizer.Add(lin(searchpanel, 195), 0, labstyle)
        sizer.Add(loadpanel,           0, wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL)
        sizer.Add(lin(searchpanel, 195), 0, labstyle)
        sizer.Add(lin(searchpanel, 195), 0, labstyle)

        pack(searchpanel, sizer)
        return searchpanel


    def onXaxis(self, event=None):

        q,I = self.xrd.data1D

        if event is not None:
            if 0 == event.GetInt():
                ## q in units 1/A
                self.xunit = 'q'
                self.xlabel = 'q (1/A)'
                x = q
            elif 1 == event.GetInt():
                ## d in units A
                self.xunit = '2th'
                self.xlabel = r'$2\Theta$'+r' $(^\circ)$'
                x = calc_q_to_2th(q,self.xrd.wavelength*1e10)
            elif 2 == event.GetInt():
                ## d in units A
                self.xunit = 'd'
                self.xlabel = 'd (A)'
                x = calc_q_to_d(q)
        
        self.plot1d([x,I])

        if self.xrd2 is not None:
            self.oplot1D([x,I])

    def createMainPanel(self):
        ctrlpanel = self.createControlPanel()
        plotpanel = self.panel = self.createPlotPanel()
        plotpanel.yformatter = self._formaty

        ##tx, ty = self.wids['ptable'].GetBestSize()
        cx, cy = ctrlpanel.GetBestSize()
        px, py = plotpanel.GetBestSize()

        self.SetSize((cx+px, 25+max(cy, py)))

        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
       
        sizer.Add(ctrlpanel,   0, style, 3)
        sizer.Add(plotpanel,   1, style, 2)

        self.SetMinSize((450, 150))
        pack(self, sizer)
        wx.CallAfter(self.init_larch)

    def init_larch(self):
        if self.larch is None:
            self.larch = Interpreter()

    def _get1Dlims(self):
        xmin, xmax = self.panel.axes.get_xlim()
        xrange = xmax-xmin
        xmid   = (xmax+xmin)/2.0
        if self.x_for_zoom is not None:
            xmid = self.x_for_zoom
        return (xmid, xrange, xmin, xmax)
        
    def abs_limits(self):
        if self.xrd is not None:
            xmin, xmax = self.xrd.data1D[0].min(), self.xrd.data1D[0].max()
            if self.xunit == '2th':
                xmin = calc_q_to_2th(xmin,self.xrd.wavelength*1e10)
                xmax = calc_q_to_2th(xmax,self.xrd.wavelength*1e10)
            elif self.xunit == 'd':
                xmax = calc_q_to_d(xmin)
                xmin = calc_q_to_d(xmax)
                if xmax > 5:
                    xmax = 5.0    
        return xmin,xmax
    
    def _set_xview(self, x1, x2, keep_zoom=False, pan=False):

        xmin,xmax = self.abs_limits()
        xrange = x2-x1
        x1 = max(xmin,x1)
        x2 = min(xmax,x2)

        if pan:
            if x2 == xmax:
                x1 = x2-xrange
            elif x1 == xmin:
                x2 = x1+xrange
        if not keep_zoom:
            self.x_for_zoom = (x1+x2)/2.0
        self.panel.axes.set_xlim((x1, x2))
        self.xview_range = [x1, x2]
        self.draw()

    def onPanLo(self, event=None):
        xmid, xrange, xmin, xmax = self._get1Dlims()
        x1 = xmin-0.9*xrange
        x2 = x1 + xrange
        self._set_xview(x1, x2, pan=True)

    def onPanHi(self, event=None):
        xmid, xrange, xmin, xmax = self._get1Dlims()
        x2 = xmax+0.9*xrange
        x1 = x2 - xrange
        self._set_xview(x1, x2, pan=True)
        
    def onZoomIn(self, event=None):
        xmid, xrange, xmin, xmax = self._get1Dlims()
        x1 = max(xmin, xmid-xrange/3.0)
        x2 = min(xmax, xmid+xrange/3.0)
        self._set_xview(x1, x2, keep_zoom=True)
                
    def onZoomOut(self, event=None):
        xmid, xrange, xmin, xmax = self._get1Dlims()
        x1 = min(xmin, xmid-1.25*xrange)
        x2 = max(xmax, xmid+1.25*xrange)
        self._set_xview(x1, x2)
        
    def unzoom_all(self, event=None):

        xmid, xrange, xmin, xmax = self._get1Dlims()
        
        self._set_xview(xmin, xmax)
        self.xview_range = None

    def toggle_grid(self, event=None):
        self.panel.toggle_grid()

    def onLoadCIF(self, event=None):
       
        wildcards = 'CIF file (*.cif)|*.cif|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose CIF file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            cry_strc = struc_from_cif(path)

            if cry_strc:
                hc = constants.value(u'Planck constant in eV s') * \
                         constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m
                energy = hc/(self.xrd.wavelength) ## units: keV
                q,F = calc_all_F(cry_strc,energy,maxhkl=10,qmax=5)

                #self.plot1Dxrd(xrddata, show_xrd2=True)

    def onSearchDB(self, event=None):

        XRDSearchGUI()

    def createCustomMenus(self):
        return

    def createBaseMenus(self):
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "&Read XRD File\tCtrl+O",
                 "Read GSECARS XRD File",  self.onReadXRDFile)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "&Save XRD File\tCtrl+S",
                 "Save GSECARS XRD File",  self.onSaveXRDFile)
        
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
        MenuItem(self, omenu, "Configure Plot\tCtrl+K",
                 "Configure Plot Colors, etc", self.panel.configure)
        MenuItem(self, omenu, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range", self.unzoom_all)
        MenuItem(self, omenu, "Toggle Grid\tCtrl+G",
                 "Toggle Grid Display", self.toggle_grid)
        omenu.AppendSeparator()
        MenuItem(self, omenu, "Hide Markers ",
                 "Hide cursor markers", self.clear_markers)
        MenuItem(self, omenu, "Hide XRD Background ",
                 "Hide cursor markers", self.clear_background)

        omenu.AppendSeparator()
        MenuItem(self, omenu, "Swap Fore and Background plots",
                 "Swap Foreground and Background XRD plots", self.swap_lines)
        MenuItem(self, omenu, "Close Background XRD plot",
                 "Close Background XRD plot", self.close_bkg_xrd)

        amenu = wx.Menu()
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

        self.plot1d(self.xrd.data1D)

        if self.xrd2 is not None:
            self.oplot1D(self.xrd2.data1D)

    def plot1Dxrd(self, xrd, title=None, set_title=True, as_xrd2=False,
                unit = 'q', fullrange=False, init=False, **kws):
        if as_xrd2:
            self.xrd2 = xrd
            kws['new'] = False
            self.x2data = xrd.data1D[0]
            self.y2data = xrd.data1D[1]
        else:
            self.xrd = xrd
            self.panel.conf.show_grid = False
            self.xdata = xrd.data1D[0]
            self.ydata = xrd.data1D[1]

        self.xunit = unit        
        if self.xunit == '2th':
            self.xlabel = r'$2\Theta$'+r' $(^\circ)$'
        elif self.xunit == 'd':
            self.xlabel = 'd (A)'
        else:
            self.xunit = 'q'
            self.xlabel = 'q (1/A)'

        if init:
            self.xview_range = (min(self.xrd.data1D[0]), max(self.xrd.data1D[0]))
        else:
            self.xview_range = self.panel.axes.get_xlim()
            #self.xview_range = self.panel.axes.get_axes().get_xlim()

        atitles = []
        if self.xrd is not None:
            if hasattr(self.xrd, 'title'):
                atitles.append(self.xrd.title)
            if hasattr(self.xrd, 'filename'):
                atitles.append(" File={:s}".format(self.xrd.filename))
            if hasattr(self.xrd, 'npixels'):
                atitles.append(" ({:.0f} Pixels)".format(self.xrd.npixels))
            if hasattr(self.xrd, 'real_time'):
                try:
                    rtime_str = " RealTime={:.2f} sec".format(self.xrd.real_time)
                except ValueError:
                    rtime_str = " RealTime= %s sec".format(str(self.xrd.real_time))
                atitles.append(rtime_str)

            try:
                self.plot1d(self.xrd.data1D, **kws)
            except ValueError:
                pass
        if as_xrd2:
            if hasattr(self.xrd2, 'title'):
                atitles.append(" BG={:s}".format(self.xrd2.title))
            elif  hasattr(self.xrd2, 'filename'):
                atitles.append(" BG_File={:s}".format(self.xrd2.filename))
            if hasattr(self.xrd, 'real_time'):
                atitles.append(" BG_RealTime={:.2f} sec".format(self.xrd2.real_time))

            self.oplot1D(self.xrd2.data1D,
                       xrd=self.xrd2, **kws)
        if title is None:
            title =' '.join(atitles)
        if set_title:
            self.SetTitle(title)

    def plot1d(self, xrd_spectra, init=False, **kws):

        panel = self.panel
        panel.canvas.Freeze()
        panel.yformatter = self._formaty
        panel.axes.get_yaxis().set_visible(False)
        kwargs = {'xmin': 0,
                  'grid': panel.conf.show_grid,
                  'ylog_scale': self.ylog_scale,
                  'xlabel': self.xlabel,
                  'ylabel': 'intensity (counts)',
                  'axes_style': 'bottom',
                  'color': self.spectra_color}
        kwargs.update(kws)

        panel.plot(xrd_spectra[0], xrd_spectra[1], label='spectra',  **kwargs)

        ## Working on background calculation
        ## mkak 2016.09.28
        #pfit = np.polyfit(xrd_spectra[0],xrd_spectra[1],1)
        #yfit = np.polyval(pfit,xrd_spectra[0])
        #panel.plot(xrd_spectra[0], xrd_spectra[1]-yfit, label='no bkg')
        #panel.plot(xrd_spectra[0], yfit, color='blue', label='bkg')
        ### calculation works, but plotting here wipes previous plots - only shows last

        self.unzoom_all()

        panel.axes.get_yaxis().set_visible(self.show_yaxis)
        panel.cursor_mode = 'zoom'

        a, b, c, d = self._get1Dlims()
        self.panel.axes.set_xlim((c, d))
        self.draw()

        panel.canvas.Thaw()
        panel.canvas.Refresh()


    def update_1Dxrd(self, data1D, draw=True):
        """update xrd frame on plot"""
        xrd = self.xrd

        xrd.data1D = data1D[:]

        self.panel.update_line(ix, xrd.data2, draw=False, update_limits=False)

        max_intensity = max_intensity2 = max(self.xrd.data1d[1,])
        try:
            max_intensity2 = max(self.xrd2.data1d[1,])
        except:
            pass

        self.panel.axes.set_ylim(0.9, 1.25*max(max_intensity, max_intensity2))
        if xrd == self.xrd:
            self.ydata = 1.0*data1d[1,:]
        self.update_status()
        if draw: self.draw()

    ## Not using this routine. mkak 2016.09.28
    def oplot1D(self, xrd_spectra, color='darkgreen', label='spectra2',
              xrd=None, zorder=-2, **kws):
        if xrd is not None:
            self.xrd2 = xrd

        if hasattr(self, 'xrd2') and hasattr(self, 'xrd'):
            ymax = max(max(self.xrd.data1D), max(self.xrd2.data1D))*1.25
        else:
            ymax = max(xrd_spectra[1])

        kws.update({'zorder': zorder, 'label': label,
                    'ymax' : ymax, 'axes_style': 'bottom',
                    'ylog_scale': self.ylog_scale})
        self.panel.oplot(xrd_spectra[0], xrd_spectra[1], color=color, **kws)

    def swap_lines(self, event=None):
        if self.xrd2 is None:
            return
        self.xrd, self.xrd2 = self.xrd2, self.xrd
        self.plot1Dxrd(self.xrd)
        self.plot1Dxrd(self.xrd2, as_xrd2=True)

    def close_bkg_xrd(self, event=None):
        self.xrd2 = None
        self.plot1Dxrd(self.xrd)

    def onReadXRDFile(self, event=None):
        dlg = wx.FileDialog(self, message="Open XRD File for reading",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style = wx.FD_OPEN|wx.FD_CHANGE_DIR)

        fnew= None
        if dlg.ShowModal() == wx.ID_OK:
            fnew = os.path.abspath(dlg.GetPath())
        dlg.Destroy()

        if fnew is None:
            return
        self.xrd2 = None
        if self.xrd is not None:
            self.xrd2 = copy.deepcopy(self.xrd)

        self.xrd = gsexrd_group(fnew, _larch=self.larch)

        setattr(self._xrdgroup, 'xrd1', self.xrd)
        setattr(self._xrdgroup, 'xrd2', self.xrd2)
        self.plot1Dxrd(self.xrd, show_xrd2=True)

    def onReadGSEXRDFile(self, event=None, **kws):
        print( '  onReadGSEXRDFile   ')
        pass

    def onOpenEpicsXRD(self, event=None, **kws):
        print( '  onOpenEpicsXRD   ')
        pass

    def onSaveXRDFile(self, event=None, **kws):
        deffile = ''
        if hasattr(self.xrd, 'sourcefile'):
            deffile = "%s%s" % (deffile, getattr(self.xrd, 'sourcefile'))
        if hasattr(self.xrd, 'areaname'):
            deffile = "%s%s" % (deffile, getattr(self.xrd, 'areaname'))
        if deffile == '':
            deffile ='test'
        if not deffile.endswith('.xrd'):
            deffile = deffile + '.xrd'

        deffile = fix_filename(str(deffile))
        outfile = FileSave(self, "Save XRD File",
                           default_file=deffile,
                           wildcard=FILE_WILDCARDS)

        if outfile is not None:
            self.xrd.save_xrdfile(outfile)

# ## Not ready to incorporate peak fitting, yet...
# ## mkak 2016.07.25
#     def onFitPeaks(self, event=None, **kws):
#         print('This function is not yet implemented...')
#         #try:
#         #    self.win_fit.Raise()
#         #except:
#         #    self.win_fit = FitSpectraFrame(self)

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def onAbout(self, event=None):
        dlg = wx.MessageDialog(self,
                               """XRD Pattern Viewer
                               Margaret Koker <koker @ cars.uchicago.edu>
                               """,
                               "About XRD Viewer",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,event):
        self.Destroy()

    def onReadFile(self, event=None):
        dlg = wx.FileDialog(self, message="Read XRD File",
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

class XRDApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, xrd_file=None, **kws):
        self.xrd_file = xrd_file
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        frame = XRD1D_DisplayFrame(xrd_file=self.xrd_file) #
        frame.Show()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    XRDApp().MainLoop()
