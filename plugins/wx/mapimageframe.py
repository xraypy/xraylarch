#!/usr/bin/python
"""
subclass of wxmplot.ImageFrame specific for Map Viewer -- adds custom menus
"""

import os
import time
from threading import Thread
import socket

from functools import partial
import wx
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception

is_wxPhoenix = 'phoenix' in wx.PlatformInfo

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg

import wxmplot
from wxmplot import ImageFrame, PlotFrame, PlotPanel
from wxmplot.imagepanel import ImagePanel

from wxmplot.imageconf import ColorMap_List, Interp_List
from wxmplot.colors import rgb2hex, register_custom_colormaps

from wxutils import (SimpleText, TextCtrl, Button, Popup, Choice, pack)

def get_wxmplot_version():
    wmv = [int(w) for w in wxmplot.__version__ .split('.')]
    return  wmv[0]*1.0 + wmv[1]*0.1 + wmv[2]*0.001


CURSOR_MENULABELS = {'zoom':  ('Zoom to Rectangle\tCtrl+B',
                               'Left-Drag to zoom to rectangular box'),
                     'lasso': ('Select Points for XRF Spectra\tCtrl+N',
                               'Left-Drag to select points freehand'),
                     'prof':  ('Select Line Profile\tCtrl+K',
                               'Left-Drag to select like for profile')}


class MapImageFrame(ImageFrame):
    """
    MatPlotlib Image Display on a wx.Frame, using ImagePanel
    """

    def __init__(self, parent=None, size=(750, 675), mode='intensity',
                 lasso_callback=None, move_callback=None, save_callback=None,
                 show_xsections=False, cursor_labels=None,
                 output_title='Image',   **kws):

        # instdb=None,  inst_name=None,

        self.det = None
        self.xrmfile = None
        self.map = None
        self.move_callback = move_callback
        self.save_callback = save_callback
        self.wxmplot_version = get_wxmplot_version()


        ImageFrame.__init__(self, parent=parent, size=size,
                            lasso_callback=lasso_callback,
                            cursor_labels=cursor_labels, mode=mode,
                            output_title=output_title, **kws)

        self.panel.add_cursor_mode('prof', motion = self.prof_motion,
                                   leftdown = self.prof_leftdown,
                                   leftup   = self.prof_leftup)
        self.panel.report_leftdown = self.report_leftdown
        self.panel.report_motion   = self.report_motion

        w, h = self.GetSize()
        w = min(w, 750)
        h = min(h, 675)
        self.SetSize((w, h))

        self.prof_plotter = None
        self.zoom_ini =  None
        self.lastpoint = [None, None]
        self.this_point = None
        self.rbbox = None

    def display(self, map, det=None, xrmfile=None, xoff=0, yoff=0, **kws):
        self.xoff = xoff
        self.yoff = yoff
        self.det = det
        self.xrmfile = xrmfile
        self.map = map
        self.title = ''
        if 'title' in kws:
            self.title = kws['title']
        ImageFrame.display(self, map, **kws)
        if 'x' in kws:
            self.panel.xdata = kws['x']
        if 'y' in kws:
            self.panel.ydata = kws['y']
        if self.panel.conf.auto_contrast:
            self.set_contrast_levels()

        if self.wxmplot_version > 0.921:
            sd = kws.get('subtitles', {})
            if sd is None:
                return
            t_red = sd.get('red', None)
            t_green = sd.get('green', None)
            t_blue = sd.get('blue', None)
            if t_red is not None:
                self.cmap_panels[0].title.SetLabel(t_red)
            if t_green is not None:
                self.cmap_panels[1].title.SetLabel(t_green)
            if t_blue is not None:
                self.cmap_panels[2].title.SetLabel(t_blue)

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
        if event.inaxes: #  and len(self.map.shape) == 2:
            self.lastpoint = [None, None]
            self.zoom_ini = [event.x, event.y, event.xdata, event.ydata]

    def prof_leftup(self, event=None):
        # print("Profile Left up ", self.map.shape, self.rbbox)
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
            z.append(self.panel.conf.data[iy, ix])
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

        x = np.array(x)
        y = np.array(y)
        z = np.array(z)
        if dy > dx:
            x, y = y, x
            xlabel, y2label = y2label, xlabel
        self.prof_plotter.panel.clear()

        if len(self.title) < 1:
            self.title = os.path.split(self.xrmfile.filename)[1]

        opts = dict(linewidth=2, marker='+', markersize=3,
                    show_legend=True, xlabel=xlabel)

        if isinstance(z[0], np.ndarray) and len(z[0]) == 3: # color plot
            rlab = self.subtitles['red']
            glab = self.subtitles['green']
            blab = self.subtitles['blue']
            self.prof_plotter.plot(x, z[:, 0], title=self.title, color='red',
                                   zorder=20, xmin=min(x)-3, xmax=max(x)+3,
                                   ylabel='counts', label=rlab, **opts)
            self.prof_plotter.oplot(x, z[:, 1], title=self.title, color='darkgreen',
                                   zorder=20, xmin=min(x)-3, xmax=max(x)+3,
                                   ylabel='counts', label=glab, **opts)
            self.prof_plotter.oplot(x, z[:, 2], title=self.title, color='blue',
                                   zorder=20, xmin=min(x)-3, xmax=max(x)+3,
                                   ylabel='counts', label=blab, **opts)

        else:

            self.prof_plotter.plot(x, z, title=self.title, color='blue',
                                   zorder=20, xmin=min(x)-3, xmax=max(x)+3,
                                   ylabel='counts', label='counts', **opts)

        self.prof_plotter.oplot(x, y, y2label=y2label, label=y2label,
                              zorder=3, side='right', color='black', **opts)

        self.prof_plotter.panel.unzoom_all()
        self.prof_plotter.Show()
        self.zoom_ini = None

        self.zoom_mode.SetSelection(0)
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

        _point = 0, 0, 0, 0, 0
        for ix, iy in self.prof_dat[1]:
            if (int(x) == ix and not self.prof_dat[0] or
                int(x) == iy and self.prof_dat[0]):
                _point = (ix, iy,
                              self.panel.xdata[ix],
                              self.panel.ydata[iy],
                              self.panel.conf.data[iy, ix])

        msg = "Pixel [%i, %i], X, Y = [%.4f, %.4f], Intensity= %g" % _point
        write(msg,  panel=0)

    def onCursorMode(self, event=None, mode='zoom'):
        self.panel.cursor_mode = mode
        if event is not None:
            if 1 == event.GetInt():
                self.panel.cursor_mode = 'lasso'
            elif 2 == event.GetInt():
                self.panel.cursor_mode = 'prof'

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
            pos = ', '.join(labs)
            vals =', '.join(['%.4g' % v for v in vals])
            pos = '%s = [%s]' % (pos, vals)
            dval = conf.data[iy, ix]
            if len(pan.data_shape) == 3:
                dval = "%.4g, %.4g, %.4g" % tuple(dval)
            else:
                dval = "%.4g" % dval
            if pan.xdata is not None and pan.ydata is not None:
                self.this_point = (ix, iy)

            msg = "Pixel [%i, %i], %s, Intensity=%s " % (ix, iy, pos, dval)
        self.panel.write_message(msg, panel=0)

    def report_motion(self, event=None):
        return

    def onLasso(self, data=None, selected=None, mask=None, **kws):
        if hasattr(self.lasso_callback , '__call__'):

            self.lasso_callback(data=data, selected=selected, mask=mask,
                                xoff=self.xoff, yoff=self.yoff,
                                det=self.det, xrmfile=self.xrmfile, **kws)

        self.zoom_mode.SetSelection(0)
        self.panel.cursor_mode = 'zoom'

    def CustomConfig(self, panel, sizer=None, irow=0):
        """config panel for left-hand-side of frame"""

        labstyle = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND
        zoom_opts = ('Zoom to Rectangle',
                     'Pick Area for XRF Spectrum',
                     'Show Line Profile')

        if self.wxmplot_version > 0.921:
            cpanel = wx.Panel(panel)
            if sizer is None:
                sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(SimpleText(cpanel, label='Cursor Modes', style=labstyle), 0, labstyle, 3)
            self.zoom_mode = wx.RadioBox(cpanel, -1, "",
                                         wx.DefaultPosition, wx.DefaultSize,
                                         zoom_opts, 1, wx.RA_SPECIFY_COLS)
            self.zoom_mode.Bind(wx.EVT_RADIOBOX, self.onCursorMode)

            sizer.Add(self.zoom_mode, 1, labstyle, 4)

            if self.save_callback is not None:
                sizer.Add(SimpleText(cpanel, label='Save Position:', style=labstyle), 0, labstyle, 3)
                self.pos_name = wx.TextCtrl(cpanel, -1, '',  size=(155, -1),
                                            style=wx.TE_PROCESS_ENTER)
                self.pos_name.Bind(wx.EVT_TEXT_ENTER, self.onSavePixel)
                sizer.Add(self.pos_name, 0, labstyle, 3)

            pack(cpanel, sizer)
            return cpanel
        else:  # support older versions of wxmplot, will be able to deprecate
            conf = self.panel.conf
            lpanel = panel
            lsizer = sizer
            self.zoom_mode = wx.RadioBox(panel, -1, "Cursor Mode:",
                                         wx.DefaultPosition, wx.DefaultSize,
                                         zoom_opts, 1, wx.RA_SPECIFY_COLS)
            self.zoom_mode.Bind(wx.EVT_RADIOBOX, self.onCursorMode)
            sizer.Add(self.zoom_mode,  (irow, 0), (1, 4), labstyle, 3)
            if self.save_callback is not None:
                self.pos_name = wx.TextCtrl(panel, -1, '',  size=(175, -1),
                                            style=wx.TE_PROCESS_ENTER)
                self.pos_name.Bind(wx.EVT_TEXT_ENTER, self.onSavePixel)
                label   = SimpleText(panel, label='Save Position:',
                                     size=(-1, -1))
                sizer.Add(label,         (irow+1, 0), (1, 2), labstyle, 3)
                sizer.Add(self.pos_name, (irow+1, 2), (1, 2), labstyle, 3)

            # if self.move_callback is not None:
            #    mbutton = Button(panel, 'Move to Position', size=(100, -1),
            #                     action=self.onMoveToPixel)
            #    irow  = irow + 2
            #    sizer.Add(mbutton,       (irow+1, 0), (1, 2), labstyle, 3)

    def onMoveToPixel(self, event=None):
        pass
        # if self.this_point is not None and self.move_callback is not None:
        #    p1 = float(self.panel.xdata[self.this_point[0]])
        #    p2 = float(self.panel.ydata[self.this_point[1]])
        #    self.move_callback(p1, p2)

    def onSavePixel(self, event=None):
        if self.this_point is not None and self.save_callback is not None:
            name  = str(event.GetString().strip())
            # name  = str(self.pos_name.GetValue().strip())
            ix, iy = self.this_point
            x = float(self.panel.xdata[int(ix)])
            y = float(self.panel.ydata[int(iy)])
            self.save_callback(name, ix, iy, x=x, y=y,
                               title=self.title, datafile=self.xrmfile)

CorrelatedMapFrame = None
if get_wxmplot_version() > 0.922:

    class CorrelatedMapFrame(wxmplot.ImageMatrixFrame):
        """
        wx.Frame, with 3 ImagePanels and correlation plot for 2 map arrays
        """
        def __init__(self, parent=None, xrmfile=None,
                     title='CorrelatedMaps',  **kws):

            self.xrmfile = xrmfile
            wxmplot.ImageMatrixFrame.__init__(self, parent, size=(900, 625),
                                              title=title, **kws)

        def CustomConfig(self, parent):
            pass # print("no custom config yet")
