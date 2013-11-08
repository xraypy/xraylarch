#!/usr/bin/python
"""
subclass of wxmplot.ImageFrame specific for Map Viewer -- adds custom menus
"""

import os
import time
from threading import Thread

from functools import partial
import wx
from wx._core import PyDeadObjectError
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg

import larch

larch.use_plugin_path('std')
from debugtime import DebugTimer

larch.use_plugin_path('wx')

from wxmplot import ImageFrame, PlotFrame
from wxmplot.imagepanel import ImagePanel
from wxmplot.imageconf import ColorMap_List, Interp_List
from wxmplot.colors import rgb2hex

HAS_SKIMAGE = False
try:
    import skimage
    from skimage import exposure
    HAS_SKIMAGE = True

except ImportError:
    pass

CURSOR_MENULABELS = {'zoom':  ('Zoom to Rectangle\tCtrl+B',
                               'Left-Drag to zoom to rectangular box'),
                     'lasso': ('Select Points for XRF Spectra\tCtrl+X',
                               'Left-Drag to select points freehand'),
                     'prof':  ('Select Line Profile\tCtrl+K',
                               'Left-Drag to select like for profile')}

class MapImageFrame(ImageFrame):
    """
    MatPlotlib Image Display on a wx.Frame, using ImagePanel
    """

    def __init__(self, parent=None, size=None,
                 lasso_callback=None, mode='intensity',
                 show_xsections=False, cursor_labels=None,
                 output_title='Image',   **kws):

        dbt = DebugTimer()
        self.det = None
        self.xrmfile = None
        self.map = None
        ImageFrame.__init__(self, parent=parent, size=size,
                            lasso_callback=lasso_callback,
                            cursor_labels=cursor_labels, mode=mode,
                            output_title=output_title, **kws)
        self.panel.add_cursor_mode('prof', motion = self.prof_motion,
                                   leftdown = self.prof_leftdown,
                                   leftup   = self.prof_leftup)
        self.panel.report_leftdown = self.report_leftdown
        self.panel.report_motion   = self.report_motion

        self.prof_plotter = None
        self.zoom_ini =  None
        self.lastpoint = [None, None]
        self.rbbox = None

    def display(self, map, det=None, xrmfile=None, **kws):
        # print 'DISPLAY ', kws.keys()
        self.det = det
        self.xrmfile = xrmfile
        self.map = map
        ImageFrame.display(self, map, **kws)
        if 'x' in kws:
            self.panel.xdata = kws['x']

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
        zdc.BeginDrawing()

        # erase previous box
        if self.rbbox is not None:
            zdc.DrawLine(*self.rbbox)
        self.rbbox = (xmin, ymin, xmax, ymax)
        zdc.DrawLine(*self.rbbox)
        zdc.EndDrawing()

    def prof_leftdown(self, event=None):
        self.report_leftdown(event=event)
        if event.inaxes:
            self.lastpoint = [None, None]
            self.zoom_ini = [event.x, event.y, event.xdata, event.ydata]

    def prof_leftup(self, event=None):
        if self.rbbox is not None:
            zdc = wx.ClientDC(self.panel.canvas)
            zdc.SetLogicalFunction(wx.XOR)
            zdc.SetBrush(wx.TRANSPARENT_BRUSH)
            zdc.SetPen(wx.Pen('White', 2, wx.SOLID))
            zdc.ResetBoundingBox()
            zdc.BeginDrawing()
            zdc.DrawLine(*self.rbbox)
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

            except AttributeError, PyDeadObjectError:
                self.prof_plotter = None

        if self.prof_plotter is None:
            self.prof_plotter = PlotFrame(self, title='Profile')
            self.prof_plotter.panel.report_leftdown = self.prof_report_coords

        xlabel, y2label = 'Pixel (x)',  'Pixel (y)'

        if dy > dx:
            x, y = y, x
            xlabel, y2label = y2label, xlabel
        self.prof_plotter.panel.clear() # reset_config()
        self.prof_plotter.plot(x, z, xlabel=xlabel, show_legend=True,
                               xmin=min(x)-3, xmax=max(x)+3, zorder=10,
                               ylabel='counts', label='counts',
                               linewidth=2, marker='+', color='blue')
        self.prof_plotter.oplot(x, y, y2label=y2label, label=y2label,
                                side='right', show_legend=True, zorder=5,
                                color='#771111', linewidth=1, marker='+',
                                markersize=3)
        self.prof_plotter.panel.unzoom_all()
        self.prof_plotter.Show()
        self.zoom_ini = None

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

        this_point = 0, 0, 0, 0, 0
        for ix, iy in self.prof_dat[1]:
            if (int(x) == ix and not self.prof_dat[0] or
                int(x) == iy and self.prof_dat[0]):
                this_point = (ix, iy,
                              self.panel.xdata[ix],
                              self.panel.ydata[iy],
                              self.panel.conf.data[iy, ix])

        msg = "Pixel [%i, %i], X, Y = [%.4f, %.4f], Intensity= %g" % this_point
        write(msg,  panel=0)

    def onCursorMode(self, event=None):
        self.panel.cursor_mode = 'zoom'
        if 1 == event.GetInt():
            self.panel.cursor_mode = 'lasso'
        elif 2 == event.GetInt():
            self.panel.cursor_mode = 'prof'

    def enhance_constrast(self, level):
        map = self.map
        if level == 1:  # 'Stretch Contrast'
            # Contrast stretching
            p02 = np.percentile(map,  2)
            p98 = np.percentile(map, 98)
            map = exposure.rescale_intensity(map, in_range=(p02, p98))
        elif level == 2: #     'Histogram Equalization',
            map = exposure.equalize_hist(map.astype('int'))
        self.cmap = map

    def report_leftdown(self, event=None):
        if event is None:
            return
        if event.xdata is None or event.ydata is None:
            return

        ix, iy = round(event.xdata), round(event.ydata)
        conf = self.panel.conf
        if conf.flip_ud:  iy = conf.data.shape[0] - iy
        if conf.flip_lr:  ix = conf.data.shape[1] - ix
        # print 'LeftDown ', conf.data.shape
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
            pos = ', '.join(labs)
            vals =', '.join(['%.4g' % v for v in vals])
            pos = '%s = [%s]' % (pos, vals)
            dval = conf.data[iy, ix]
            if len(pan.data_shape) == 3:
                dval = "%.4g, %.4g, %.4g" % tuple(dval)
            else:
                dval = "%.4g" % dval
            msg = "Pixel [%i, %i], %s, Intensity=%s " % (ix, iy, pos, dval)
        self.panel.write_message(msg, panel=0)

    def report_motion(self, event=None):
        return

    def onContrastMode(self, event=None):
        contrast =  event.GetInt()
        if not HAS_SKIMAGE:
            return
        if self.map is None:
            self.map = self.panel.conf.data

        map = self.map
        if contrast > 0:
            self.cmap = None
            _thread = Thread(target=self.enhance_constrast, args=(contrast,))
            _thread.start()
            while self.cmap is None:
                time.sleep(0.1)
                try:
                    wx.Yield()
                except:
                    pass
            _thread.join()
            map = self.cmap
        ImageFrame.display(self, map)
        self.cmap = None

    def onLasso(self, data=None, selected=None, mask=None, **kws):
        if hasattr(self.lasso_callback , '__call__'):
            self.lasso_callback(data=data, selected=selected, mask=mask,
                                det=self.det, xrmfile=self.xrmfile, **kws)

    def CustomConfig(self, panel, sizer, irow):
        """config panel for left-hand-side of frame"""
        conf = self.panel.conf
        lpanel = panel
        lsizer = sizer
        labstyle = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND

        zoom_mode = wx.RadioBox(panel, -1, "Cursor Mode:",
                                wx.DefaultPosition, wx.DefaultSize,
                                ('Zoom to Rectangle',
                                 'Pick Area for XRF Spectrum',
                                 'Show Line Profile'),
                                1, wx.RA_SPECIFY_COLS)
        zoom_mode.Bind(wx.EVT_RADIOBOX, self.onCursorMode)
        sizer.Add(zoom_mode,  (irow, 0), (1, 4), labstyle, 3)

