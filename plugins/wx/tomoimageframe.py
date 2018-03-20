#!/usr/bin/python
'''
subclass of wxmplot.ImageFrame specific for Map Viewer -- adds custom menus
'''

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
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled

is_wxPhoenix = 'phoenix' in wx.PlatformInfo

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg

import wxmplot
from wxmplot.baseframe  import BaseFrame
from wxmplot import ImageFrame, PlotFrame, PlotPanel, StackedPlotFrame
from wxmplot.imagepanel import ImagePanel

from wxmplot.imageframe import ColorMapPanel, AutoContrastDialog
from wxmplot.imageconf import ColorMap_List, Interp_List
from wxmplot.colors import rgb2hex, register_custom_colormaps
from wxmplot.utils import LabelEntry, MenuItem, pack

from wxutils import (SimpleText, TextCtrl, Button, Popup, Choice, pack)

import larch
from larch_plugins.wx.mapimageframe import get_wxmplot_version

from functools import partial

HAS_IMAGE = False
try:
    from PIL import Image
    HAS_IMAGE = True
except ImportError:
    pass

COLORMAPS = ('blue', 'red', 'green', 'magenta', 'cyan', 'yellow')
RGB_COLORS = ('red', 'green', 'blue')

CURSOR_MENULABELS = {'zoom':  ('Zoom to Rectangle\tCtrl+B',
                               'Left-Drag to zoom to rectangular box'),
                     'lasso': ('Select Points for XRM Spectra\tCtrl+N',
                               'Left-Drag to select points freehand'),
                     'prof':  ('Select Line Profile\tCtrl+K',
                               'Left-Drag to select like for profile')}

class TomoFrameClass(object):

    def __init__(self,label=None,map=None,panel=None):

        self.label  = label
        self.map    = map
        self.panel  = panel

class TomographyFrame(BaseFrame):
### COPY OF ImageFrame(BaseFrame) with portions of ImageMatrixFrame(BaseFrame)
    '''
    MatPlotlib Image Display ons a wx.Frame, using ImagePanel
    '''

    help_msg =  '''Quick help:

Left-Click:   to display X,Y coordinates and Intensity
Left-Drag:    to zoom in on region
Right-Click:  display popup menu with choices:
               Zoom out 1 level
               Zoom all the way out
               --------------------
               Rotate Image
               Save Image

Keyboard Shortcuts:   (For Mac OSX, replace 'Ctrl' with 'Apple')
  Saving Images:
     Ctrl-S:     Save image to file
     Ctrl-C:     Copy image to clipboard
     Ctrl-P:     Print Image

  Zooming:
     Ctrl-Z:     Zoom all the way out

  Rotating/Flipping:
     Ctrl-R:     Rotate Clockwise
     Ctrl-T:     Flip Top/Bottom
     Ctrl-F:     Flip Left/Right

  Image Enhancement:
     Ctrl-L:     Log-Scale Intensity
     Ctrl-E:     Enhance Contrast


'''


    def __init__(self, parent=None, size=None, mode='intensity',
                 lasso_callback=None, 
                 output_title='Tomography Display Frame', subtitles=None,
                 user_menus=None, **kws):

        if size is None: size = (1500, 600)
        self.lasso_callback = lasso_callback
        self.user_menus = user_menus
        self.cursor_menulabels =  {}
        self.cursor_menulabels.update(CURSOR_MENULABELS)

        self.title = output_title

        self.det = None
        self.xrmfile = None
        self.wxmplot_version = get_wxmplot_version()

        BaseFrame.__init__(self, parent=parent,
                           title  = output_title,
                           output_title=output_title,
                           size=size, **kws)

        self.cmap_panels = {}

        self.subtitles = {}
        self.config_mode = None
        if subtitles is not None:
            self.subtitles = subtitles
        sbar_widths = [-2, -1, -1]
        sbar = self.CreateStatusBar(len(sbar_widths), wx.CAPTION)
        sfont = sbar.GetFont()
        sfont.SetWeight(wx.BOLD)
        sfont.SetPointSize(10)
        sbar.SetFont(sfont)
        self.SetStatusWidths(sbar_widths)

        self.optional_menus = []

        self.bgcol = rgb2hex(self.GetBackgroundColour()[:3])

        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(225)

        self.config_panel = wx.Panel(splitter)
        self.main_panel   = wx.Panel(splitter)
        
        img_opts = dict(size = (700, 525),
                        dpi  = 100,
                        data_callback  = self.onDataChange,
                        lasso_callback = self.onLasso,
                        output_title   = self.output_title)
        
        self.tomo_frame = [TomoFrameClass(panel=ImagePanel(self.main_panel, **img_opts),
                                          label='Sinogram'),
                           TomoFrameClass(panel=ImagePanel(self.main_panel, **img_opts),
                                          label='Tomograph')]

        for iframe in self.tomo_frame:
            iframe.panel.nstatusbar = sbar.GetFieldsCount()

        self.BuildMenu()

        self.SetBackgroundColour('#F8F8F4')

        self.imin_val = {}
        self.imax_val = {}
        self.islider_range = {}

        self.config_mode = 'int'
        if mode.lower().startswith('rgb'):
            self.config_mode = 'rgb'

        self.Build_ConfigPanel()

        for iframe in self.tomo_frame:
            kwargs = {'frame':iframe}
            iframe.panel.add_cursor_mode('prof', 
                                         motion   = partial(self.prof_motion,   **kwargs),
                                         leftdown = partial(self.prof_leftdown, **kwargs),
                                         leftup   = partial(self.prof_leftup,   **kwargs))
            iframe.panel.report_leftdown = partial(self.report_leftdown, **kwargs)
            iframe.panel.messenger = self.write_message


        self.prof_plotter = None
        self.zoom_ini =  None
        self.lastpoint = [None, None]
        self.this_point = None
        self.rbbox = None


        lsty = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND
        gsizer = wx.GridSizer(1, 2, 2, 2)
        lsty |= wx.GROW|wx.ALL|wx.EXPAND|wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
        gsizer.Add(self.tomo_frame[0].panel, 1, lsty, 2)
        gsizer.Add(self.tomo_frame[1].panel, 1, lsty, 2)

        pack(self.main_panel, gsizer)
        splitter.SplitVertically(self.config_panel, self.main_panel, 1)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)
        pack(self, mainsizer)


    def display(self, map1, map2, title=None, colormap=None, style='image',
                subtitles=None, name1='Sinogram', name2='Tomograph',
                xlabel='x', ylabel='y', rotlabel='theta',
                x=None, y=None, rot=None,
                **kws):

        '''plot after clearing current plot
        '''
        
        map1 = np.array(map1)
        map2 = np.array(map2)
        
        if len(map1.shape) != len(map2.shape):
            return

        self.tomo_frame[0].label, self.tomo_frame[1].label = name1, name2
        self.xdata,  self.ydata,  self.rotdata  = x,      y,      rot
        self.xlabel, self.ylabel, self.rotlabel = xlabel, ylabel, rotlabel

        if title is not None:
            self.SetTitle(title)
        if subtitles is not None:
            self.subtitles = subtitles
        cmode = self.config_mode.lower()[:3]



        # make sure 3d image is shaped (NY, NX, 3)
        if len(map1.shape) == 3:
            ishape = map1.shape
            if ishape[2] != 3:
                if ishape[0] == 3:
                    map1 = map1.swapaxes(0, 1).swapaxes(1, 2)
                elif ishape[1] == 3:
                    map1 = map1.swapaxes(1, 2)
        if len(map2.shape) == 3:
            ishape = map2.shape
            if ishape[2] != 3:
                if ishape[0] == 3:
                    map2 = map2.swapaxes(0, 1).swapaxes(1, 2)
                elif ishape[1] == 3:
                    map2 = map2.swapaxes(1, 2)

        self.xzoom = self.yzoom = slice(0, map1.shape[1]+1)
        self.rotzoom  = slice(0, map1.shape[0]+1)

        ## sets config_mode to single or tri color and builds panel accordingly
        if len(map1.shape) == 3 and len(map2.shape) == 3:
            if cmode != 'rgb':
                for comp in self.config_panel.Children:
                    comp.Destroy()
                self.config_mode = 'rgb'
                self.tomo_frame[0].panel.conf.tricolor_mode = 'rgb'
                self.Build_ConfigPanel()
        else: ##if len(map1.shape) == 2 and len(map2.shape) == 2:
            if cmode != 'int':
                for comp in self.config_panel.Children:
                    comp.Destroy()
                self.config_mode = 'int'
                self.Build_ConfigPanel()

        for map,iframe in zip([map1,map2],self.tomo_frame):
            iframe.map = map
            iframe.panel.display(iframe.map, style=style, **kws)
            iframe.panel.conf.title = iframe.label

        if colormap is not None and self.config_mode == 'int':
            self.cmap_panels[0].set_colormap(name=colormap)

        if subtitles is not None:
            if isinstance(subtitles, dict):
                self.set_subtitles(**subtitles)
            elif self.config_mode == 'int':
                self.set_subtitles(red=subtitles)

        contour_value = 0
        if style == 'contour':
            contour_value = 1
        self.set_contrast_levels()

        for iframe in self.tomo_frame:
            iframe.panel.redraw()

        self.config_panel.Refresh()
        self.SendSizeEvent()
        wx.CallAfter(self.EnableMenus)

    def prof_motion(self, event=None, frame=None):
        if not event.inaxes or self.zoom_ini is None:
            return
        try:
            xmax, ymax  = event.x, event.y
        except:
            return
        if frame is None:
            frame = self.tomo_frame[0]

        xmin, ymin, xd, yd = self.zoom_ini
        if event.xdata is not None:
            self.lastpoint[0] = event.xdata
        if event.ydata is not None:
            self.lastpoint[1] = event.ydata

        yoff = frame.panel.canvas.figure.bbox.height
        ymin, ymax = yoff - ymin, yoff - ymax

        zdc = wx.ClientDC(frame.panel.canvas)
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

    def prof_leftdown(self, event=None, frame=None):
        if frame is None:
            frame = self.tomo_frame[0]
        self.report_leftdown(event=event,frame=frame)
        if event.inaxes: #  and len(self.map.shape) == 2:
            self.lastpoint = [None, None]
            self.zoom_ini = [event.x, event.y, event.xdata, event.ydata]

    def prof_leftup(self, event=None, frame=None):
        # print("Profile Left up ", self.map.shape, self.rbbox)
        if frame is None:
            frame = self.tomo_frame[0]

        if self.rbbox is not None:
            zdc = wx.ClientDC(frame.panel.canvas)
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
            z.append(frame.panel.conf.data[iy, ix])
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

            self.prof_plotter.plot(x, z, color='blue', title=self.title.split(':')[-1], #title=self.title, 
                                   zorder=20, xmin=min(x)-3, xmax=max(x)+3,
                                   ylabel='counts', label='counts', **opts)

        try:
            self.prof_plotter.oplot(x, y, y2label=y2label, label=y2label,
                                  zorder=3, side='right', color='black', **opts)
        except:
            pass

        self.prof_plotter.panel.unzoom_all()
        self.prof_plotter.Show()
        self.zoom_ini = None

        self.zoom_mode.SetSelection(0)
        frame.panel.cursor_mode = 'zoom'

    def prof_report_coords(self, event=None, frame=None):
        """override report leftdown for profile plotter"""
        if event is None:
            return
        ex, ey = event.x, event.y
        msg = ''
        if frame is None:
            frame = self.tomo_frame[0]

        plotpanel = self.prof_plotter.panel
        axes  = plotpanel.fig.properties()['axes'][0]
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
                              frame.panel.xdata[ix],
                              frame.panel.ydata[iy],
                              frame.panel.conf.data[iy, ix])

        msg = "Pixel [%i, %i], X, OME = [%.4f mm, %.4f deg], Intensity= %g" % _point
        write(msg,  panel=0)

    def report_leftdown(self,event=None, frame=None):
        if event is None:
            return
        if event.xdata is None or event.ydata is None:
            return
        if frame is None:
            frame = self.tomo_frame[0]
        
        ix, iy = int(round(event.xdata)), int(round(event.ydata))

        if (ix >= 0 and ix < frame.map.shape[1] and
            iy >= 0 and iy < frame.map.shape[0]):
            pos = ''
            if self.xdata is not None:
                pos = ' %s=%.4g,' % (self.xlabel, self.xdata[ix])
            if self.ydata is not None:
                pos = '%s %s=%.4g,' % (pos, self.ylabel, self.ydata[iy])

            if len(frame.map.shape) > 2:
                msg = 'Pixel [%i, %i],%s %s=(%.4g, %.4g, %.4g)' % (ix, iy, pos,
                                                  frame.label,        frame.map[iy,ix,0],
                                                  frame.map[iy,ix,1], frame.map[iy,ix,2])
            else:
                msg = 'Pixel [%i, %i],%s %s=%.4g' % (ix, iy, pos,
                                                     frame.label, frame.map[iy, ix])
            self.write_message(msg, panel=0)

            #if callable(self.cursor_callback):
            #    self.cursor_callback(x=event.xdata, y=event.ydata)

    def set_subtitles(self, red=None, green=None, blue=None, **kws):
        if self.config_mode.startswith('int') and red is not None:
            self.cmap_panels[0].title.SetLabel(red)

        if self.config_mode.startswith('rgb') and red is not None:
            self.cmap_panels[0].title.SetLabel(red)

        if self.config_mode.startswith('rgb') and green is not None:
            self.cmap_panels[1].title.SetLabel(green)

        if self.config_mode.startswith('rgb') and blue is not None:
            self.cmap_panels[2].title.SetLabel(blue)


    def EnableMenus(self, evt=None):
        is_3color = len(self.tomo_frame[0].panel.conf.data.shape) > 2
        for menu, on_3color in self.optional_menus:
            menu.Enable(is_3color==on_3color)

    def unzoom_all(self):
        self.tomo_frame[0].panel.unzoom()
        self.tomo_frame[1].panel.unzoom()
    
    def BuildMenu(self):
        # file menu
        mfile = self.Build_FileMenu(extras=(('Save Image of Colormap',
                                     'Save Image of Colormap',
                                      self.onCMapSave),))

        # options menu
        mview = self.view_menu = wx.Menu()
        MenuItem(self, mview, 'Zoom Out\tCtrl+Z',
                 'Zoom out to full data range',
                 self.unzoom_all)

        m = MenuItem(self, mview, 'Toggle Background Color (Black/White)\tCtrl+W',
                     'Toggle background color for 3-color images',
                     self.onTriColorBG, kind=wx.ITEM_CHECK)

        self.optional_menus.append((m, True))

        mview.AppendSeparator()
        MenuItem(self, mview, 'Rotate clockwise\tCtrl+R', '',
                 partial(self.onFlip, mode='rot_cw'))
        MenuItem(self, mview,  'Flip Top/Bottom\tCtrl+T', '',
                 partial(self.onFlip, mode='flip_ud'))
        MenuItem(self, mview,  'Flip Left/Right\tCtrl+F', '',
                 partial(self.onFlip, mode='flip_lr'))

        mview.AppendSeparator()
        MenuItem(self, mview, 'Projet Horizontally\tCtrl+X', '',
                 partial(self.onProject, mode='x'))
        MenuItem(self, mview, 'Projet Vertically\tCtrl+Y', '',
                 partial(self.onProject, mode='y'))

        mview.AppendSeparator()
        m = MenuItem(self, mview, 'As Contour', 'Shown as contour map',
                     self.onContourToggle, kind=wx.ITEM_CHECK)
        m.Check(False)
        self.optional_menus.append((m, False))

        m = MenuItem(self, mview, 'Configure Contours', 'Configure Contours',
                     self.onContourConfig)
        self.optional_menus.append((m, False))

        # intensity contrast
        mint =self.intensity_menu = wx.Menu()
#         MenuItem(self, mint,  'Log Scale Intensity\tCtrl+L',
#                  'use logarithm to set intensity scale',
#                  self.onLogScale, kind=wx.ITEM_CHECK)

        MenuItem(self, mint, 'Toggle Contrast Enhancement\tCtrl+E',
                 'Toggle contrast between auto-scale and full-scale',
                 self.onEnhanceContrast, kind=wx.ITEM_CHECK)


        MenuItem(self, mint, 'Set Auto-Contrast Level',
                 'Set auto-contrast scale',
                 self.onContrastConfig)

        # smoothing
        msmoo = wx.Menu()
        for itype in Interp_List:
            wid = wx.NewId()
            msmoo.AppendRadioItem(wid, itype, itype)
            self.Bind(wx.EVT_MENU, partial(self.onInterp, name=itype), id=wid)

        # help
        mhelp = wx.Menu()
        MenuItem(self, mhelp, 'Quick Reference',
                 'Quick Reference for WXMPlot', self.onHelp)
        MenuItem(self, mhelp, 'About', 'About WXMPlot', self.onAbout)

        # add all sub-menus, including user-added
        submenus = [('File', mfile),
                    ('Image', mview),
                    ('Contrast', mint),
                    ('Smoothing', msmoo)]
        if self.user_menus is not None:
            submenus.extend(self.user_menus)
        submenus.append(('&Help', mhelp))

        mbar = wx.MenuBar()
        for title, menu in submenus:
            mbar.Append(menu, title)

        self.SetMenuBar(mbar)
        self.Bind(wx.EVT_CLOSE,self.onExit)

    def onInterp(self, evt=None, name=None):

        if name not in Interp_List:
            name = Interp_List[0]
        for iframe in self.tomo_frame:
            iframe.panel.conf.interp = name
            iframe.panel.redraw()

    def onCursorMode(self, event=None, mode='zoom'):

        choice = self.zoom_mode.GetString(self.zoom_mode.GetSelection())
        for iframe in self.tomo_frame:
            iframe.panel.cursor_mode = mode
            if event is not None:
                if choice.startswith('Pick Area'):
                    iframe.panel.cursor_mode = 'lasso'
                elif choice.startswith('Show Line'):
                    iframe.panel.cursor_mode = 'prof'

    def onProject(self, event=None, mode='y'):

        wid = event.GetId()
        if mode=='x':
            x = self.tomo_frame[0].panel.ydata
            y = self.tomo_frame[0].panel.conf.data.sum(axis=1)
            x = self.tomo_frame[1].panel.ydata
            y = self.tomo_frame[1].panel.conf.data.sum(axis=1)
            axname = 'horizontal'
            if x is None:
                x = np.arange(y.shape[0])

        else:
            x = self.tomo_frame[0].panel.xdata
            y = self.tomo_frame[0].panel.conf.data.sum(axis=0)
            x = self.tomo_frame[1].panel.xdata
            y = self.tomo_frame[1].panel.conf.data.sum(axis=0)
            if x is None:
                x = np.arange(y.shape[0])

            axname = 'vertical'
        title = '%s: sum along %s axis' % (self.GetTitle(), axname)

        pf = PlotFrame(title=title, parent=self, size=(500, 250))
        colors = RGB_COLORS
        if len(y.shape) == 2 and y.shape[1] == 3:
            pf.plot(x, y[:,0], color=colors[0])
            pf.oplot(x, y[:,1], color=colors[1])
            pf.oplot(x, y[:,2], color=colors[2])
        else:
            pf.plot(x, y)
        pf.Raise()
        pf.Show()

    def onFlip(self, event=None, mode=None):

        for iframe in self.tomo_frame:
            conf = iframe.panel.conf
            if mode == 'flip_lr':
                conf.flip_lr = not conf.flip_lr
            elif mode == 'flip_ud':
                conf.flip_ud = not conf.flip_ud
            elif mode == 'flip_orig':
                conf.flip_lr, conf.flip_ud = False, False
            elif mode == 'rot_cw':
                conf.rot = True
            iframe.panel.unzoom_all()

    def Build_ConfigPanel(self):
        '''config panel for left-hand-side of frame: RGB Maps'''
        
        csizer = wx.BoxSizer(wx.VERTICAL)
        lsty = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND

        icol = 0
        if self.config_mode == 'rgb':
            for iframe in self.tomo_frame:
                for ic,col in enumerate(RGB_COLORS):
                    self.cmap_panels[icol] =  ColorMapPanel(self.config_panel,
                                                            iframe.panel,
                                                            title='%s - %s: ' % (iframe.label,col.title()),
                                                            color=ic,
                                                            default=col,
                                                            colormap_list=None)

                    csizer.Add(self.cmap_panels[icol], 0, lsty, 2)
                    csizer.Add(wx.StaticLine(self.config_panel, size=(100, 2),
                                            style=wx.LI_HORIZONTAL), 0, lsty, 2)
                    icol += 1


        else:
            for iframe in self.tomo_frame:
                self.cmap_panels[icol] =  ColorMapPanel(self.config_panel,
                                                        iframe.panel,
                                                        title='%s: ' % iframe.label,
                                                        default='gray',
                                                        colormap_list=ColorMap_List)

                csizer.Add(self.cmap_panels[icol],  0, lsty, 1)
                csizer.Add(wx.StaticLine(self.config_panel, size=(100, 2),
                                        style=wx.LI_HORIZONTAL), 0, lsty, 2)
                icol += 1

        cust = self.CustomConfig(self.config_panel, None, 0)
        if cust is not None:
            csizer.Add(cust, 0, lsty, 1)
        pack(self.config_panel, csizer)

    def clear_highlight_area(self):
    
        for iframe in self.tomo_frame:
            for area in iframe.panel.conf.highlight_areas:
                for w in area.collections + area.labelTexts:
                    w.remove()

            iframe.panel.conf.highlight_areas = []
            iframe.panel.redraw()


    def add_highlight_area(self, mask0, label=None, col=0):
        """add a highlighted area -- outline an arbitrarily shape --
        as if drawn from a Lasso event.

        This takes a mask, which should be a boolean array of the
        same shape as the image.
        """
        
        panel = None

        for iframe in self.tomo_frame:
            imap_size = iframe.map.shape[:2]
            for imask in (mask0,np.swapaxes(mask0,0,1)):
               if imap_size == imask.shape:
                  panel = iframe.panel
                  mask = imask

        if panel is not None:
            patch = mask * np.ones(mask.shape) * 0.9
            cmap = panel.conf.cmap[col]
            area = panel.axes.contour(patch, cmap=cmap, levels=[0, 1])
            panel.conf.highlight_areas.append(area)
            col = None
            if hasattr(cmap, '_lut'):
                rgb  = [int(i*240)^255 for i in cmap._lut[0][:3]]
                col  = '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])

            if label is not None:
                def fmt(*args, **kws): return label
                panel.axes.clabel(area, fontsize=9, fmt=fmt,
                                 colors=col, rightside_up=True)

            if col is not None:
                for l in area.collections:
                    l.set_color(col)

            panel.canvas.draw()

    def CustomConfig(self, panel, sizer=None, irow=0):
        '''
        override to add custom config panel items
        to bottom of config panel
        '''

        labstyle = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND
        
        if self.lasso_callback is None:
            zoom_opts = ('Zoom to Rectangle',
                         'Show Line Profile')
        else:
            zoom_opts = ('Zoom to Rectangle',
                         'Pick Area for XRM Spectra',
                         'Show Line Profile')
                         
        if self.wxmplot_version > 0.921:
            cpanel = wx.Panel(panel)
            if sizer is None:
                sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(SimpleText(cpanel, label='Cursor Modes', style=labstyle), 0, labstyle, 3)
            self.zoom_mode = wx.RadioBox(cpanel, -1, '',
                                         wx.DefaultPosition, wx.DefaultSize,
                                         zoom_opts, 1, wx.RA_SPECIFY_COLS)
            self.zoom_mode.Bind(wx.EVT_RADIOBOX, self.onCursorMode)

            sizer.Add(self.zoom_mode, 1, labstyle, 4)

            pack(cpanel, sizer)
            return cpanel
        else:  # support older versions of wxmplot, will be able to deprecate
            conf = self.tomo_frame[0].panel.conf # self.panel.conf
            lpanel = panel
            lsizer = sizer
            self.zoom_mode = wx.RadioBox(panel, -1, 'Cursor Mode:',
                                         wx.DefaultPosition, wx.DefaultSize,
                                         zoom_opts, 1, wx.RA_SPECIFY_COLS)
            self.zoom_mode.Bind(wx.EVT_RADIOBOX, self.onCursorMode)
            sizer.Add(self.zoom_mode,  (irow, 0), (1, 4), labstyle, 3)

    def onContrastConfig(self, event=None):
        
        for iframe in self.tomo_frame:
            dlg = AutoContrastDialog(parent=self, conf=iframe.panel.conf)
            dlg.CenterOnScreen()
            val = dlg.ShowModal()
            if val == wx.ID_OK:
                pass
            dlg.Destroy()


    def onContourConfig(self, event=None):

        for icol,iframe in enumerate(self.tomo_frame):
            conf = iframe.panel.conf
            dlg = ContourDialog(parent=self, conf=conf)
            dlg.CenterOnScreen()
            val = dlg.ShowModal()
            if val == wx.ID_OK:
                pass
            dlg.Destroy()
            if conf.style != 'contour':
                return

            if self.config_mode == 'int':
                self.cmap_panels[icol].set_colormap()

            iframe.panel.axes.cla()
            iframe.panel.display(conf.data, x=iframe.panel.xdata, y = iframe.panel.ydata,
                          xlabel=iframe.panel.xlab, ylabel=iframe.panel.ylab,
                          contour_labels=conf.contour_labels,
                          nlevels=conf.ncontour_levels, style='contour')
            iframe.panel.redraw()

    def onContourToggle(self, event=None):

        for icol,iframe in enumerate(self.tomo_frame):
            if len(iframe.panel.conf.data.shape) > 2:
                return
            conf  = iframe.panel.conf
            conf.style = 'image'
            if event.IsChecked():
                conf.style = 'contour'
            nlevels = int(conf.ncontour_levels)
            if self.config_mode == 'int':
                self.cmap_panels[0].set_colormap()
            iframe.panel.axes.cla()
            iframe.panel.display(conf.data, x=iframe.panel.xdata, y = iframe.panel.ydata,
                          nlevels=nlevels, contour_labels=conf.contour_labels,
                          xlabel=iframe.panel.xlab, ylabel=iframe.panel.ylab,
                          style=conf.style)
            iframe.panel.redraw()

    def onTriColorBG(self, event=None):
        bgcol = {True:'white', False:'black'}[event.IsChecked()]

        icol = 0
        for iframe in self.tomo_frame:
            conf = iframe.panel.conf
            if bgcol == conf.tricolor_bg:
                return

            conf.tricolor_bg = bgcol
            cmaps = colors = RGB_COLORS
            if bgcol.startswith('wh'):
                cmaps = ('Reds', 'Greens', 'Blues')

            for i in range(3):
                self.cmap_panels[icol].set_colormap(name=cmaps[i])
                icol += 1

            iframe.panel.redraw()

    def onLasso(self, data=None, selected=None, mask=None, **kws):

        ## orients mask correctly to match with raw data shape
        ## mkak 2018.01.24
        mask = np.swapaxes(mask,0,1)
        
        if hasattr(self.lasso_callback , '__call__'):
            self.lasso_callback(data=data, selected=selected, mask=mask, **kws)

    def onDataChange(self, data, x=None, y=None, col='int', **kw):

        icol = 0
        for iframe in self.tomo_frame:
            conf = iframe.panel.conf
            if len(data.shape) == 2: # intensity map
                imin, imax = data.min(), data.max()
                conf.int_lo[0] = imin
                conf.int_hi[0] = imax
                cpan = self.cmap_panels[0]

                cpan.cmap_lo.SetValue(imin)
                cpan.cmap_hi.SetValue(imax)

                cpan.imin_val.SetValue('%.4g' % imin)
                cpan.imax_val.SetValue('%.4g' % imax)
                cpan.imin_val.Enable()
                cpan.imax_val.Enable()
            else:
                for ix in range(3):
                    imin, imax = data[:,:,ix].min(), data[:,:,ix].max()
                    conf.int_lo[ix] = imin
                    conf.int_hi[ix] = imax
                    self.cmap_panels[icol].imin_val.SetValue('%.4g' % imin)
                    self.cmap_panels[icol].imax_val.SetValue('%.4g' % imax)
                    self.cmap_panels[icol].imin_val.Enable()
                    self.cmap_panels[icol].imax_val.Enable()
                    icol += 1

    def onEnhanceContrast(self, event=None):
        '''change image contrast, using scikit-image exposure routines'''
        
        for iframe in self.tomo_frame:
            iframe.panel.conf.auto_contrast = event.IsChecked()
        self.set_contrast_levels()
        for iframe in self.tomo_frame:
            iframe.panel.redraw()

    def set_contrast_levels(self):
        '''enhance contrast levels, or use full data range
        according to value of iframe.panel.conf.auto_contrast
        '''

        def set_panel_contrast(icol,conf,ix=-1):

            if ix < 0:
                ix = icol
                img  = conf.data
            else:
                img = conf.data[:,:,ix]

            jmin = imin = img.min()
            jmax = imax = img.max()

            self.cmap_panels[icol].imin_val.SetValue('%.4g' % imin)
            self.cmap_panels[icol].imax_val.SetValue('%.4g' % imax)
            conf.int_lo[ix] = imin
            conf.int_hi[ix] = imax

            if conf.auto_contrast:
                jmin, jmax = np.percentile(img, [      conf.auto_contrast_level,
                                                 100.0-conf.auto_contrast_level])
            if imax == imin:
                imax = imin + 0.5
            conf.cmap_lo[ix] = xlo = (jmin-imin)*conf.cmap_range/(imax-imin)
            conf.cmap_hi[ix] = xhi = (jmax-imin)*conf.cmap_range/(imax-imin)
            self.cmap_panels[icol].cmap_hi.SetValue(xhi)
            self.cmap_panels[icol].cmap_lo.SetValue(xlo)
            
            str = 'Shown: [ %.4g :  %.4g ]' % (jmin, jmax)
            self.cmap_panels[icol].islider_range.SetLabel(str)
            self.cmap_panels[icol].redraw_cmap()

        icol = 0
        for iframe in self.tomo_frame:
            conf = iframe.panel.conf
            if len(conf.data.shape) == 2: # intensity map
                set_panel_contrast(icol,conf)
                icol += 1
            elif len(conf.data.shape) == 3: # rgb map
                for ix in range(3):
                    set_panel_contrast(icol,conf,ix=ix)
                    icol += 1
            iframe.panel.redraw()

    def onLogScale(self, event=None):
        
        for iframe in self.tomo_frame:
            iframe.panel.conf.log_scale = not iframe.panel.conf.log_scale
            iframe.panel.redraw()

    def onCMapSave(self, event=None, col='int'):
        '''save color table image'''
        file_choices = 'PNG (*.png)|*.png'
        ofile = 'Colormap.png'

        dlg = wx.FileDialog(self, message='Save Colormap as...',
                            defaultDir=os.getcwd(),
                            defaultFile=ofile,
                            wildcard=file_choices,
                            style=wx.FD_SAVE|wx.FD_CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            self.cmap_panels[0].cmap_canvas.print_figure(dlg.GetPath(), dpi=600)

    def save_figure(self,event=None, transparent=True, dpi=600):
        ''' save figure image to file'''
        for iframe in self.tomo_frame:
            if iframe.panel is not None:
                iframe.panel.save_figure(event=event, transparent=transparent, dpi=dpi)
