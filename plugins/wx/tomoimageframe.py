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
from wxmplot.baseframe  import BaseFrame
from wxmplot import ImageFrame, PlotFrame, PlotPanel, StackedPlotFrame
from wxmplot.imagepanel import ImagePanel

from wxmplot.imageframe import ColorMapPanel, AutoContrastDialog
from wxmplot.imageconf import ColorMap_List, Interp_List
from wxmplot.colors import rgb2hex, register_custom_colormaps
from wxmplot.utils import LabelEntry, MenuItem, pack

from wxutils import (SimpleText, TextCtrl, Button, Popup, Choice, pack)

from functools import partial

HAS_IMAGE = False
try:
    from PIL import Image
    HAS_IMAGE = True
except ImportError:
    pass

COLORMAPS = ('blue', 'red', 'green', 'magenta', 'cyan', 'yellow')

CURSOR_MENULABELS = {'zoom':  ('Zoom to Rectangle\tCtrl+B',
                               'Left-Drag to zoom to rectangular box'),
                     'lasso': ('Select Points for XRF/XRD Spectra\tCtrl+N',
                               'Left-Drag to select points freehand'),
                     'prof':  ('Select Line Profile\tCtrl+K',
                               'Left-Drag to select like for profile')}

class TomographyFrame(BaseFrame):
### COPY OF ImageMatrixFrame(BaseFrame)
    """
    wx.Frame, with 3 ImagePanels and correlation plot for 2 map arrays
    """
    def __init__(self, parent=None, size=(1500,600),
                 cursor_callback=None, lasso_callback=None,
                 cursor_labels=None, save_callback=None,
                 title='Tomography Plot', **kws):

        self.sel_mask = None
        self.xdata = None
        self.ydata = None
        self.cursor_callback = cursor_callback
        BaseFrame.__init__(self, parent=parent,
                           title=title, size=size, **kws)

        self.title = title
        self.cmap_panels= {}
        sbar = self.CreateStatusBar(2, wx.CAPTION)
        sfont = sbar.GetFont()
        sfont.SetWeight(wx.BOLD)
        sfont.SetPointSize(10)
        sbar.SetFont(sfont)

        self.SetStatusWidths([-2, -1])
        self.SetStatusText('', 0)

        self.bgcol = rgb2hex(self.GetBackgroundColour()[:3])
        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(225)

        conf_panel = wx.Panel(splitter)
        main_panel = wx.Panel(splitter)

        self.config_panel = conf_panel

        img_opts = dict(size=(600, 600),
                        zoom_callback=self.on_imagezoom)
        self.img1_panel = ImagePanel(main_panel, **img_opts)
        self.img2_panel = ImagePanel(main_panel, **img_opts)

        self.imgpanels = [self.img1_panel,
                          self.img2_panel]

        lsty = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND

        ir = 0
        self.wids = {}
        self.cmap_panels = [None, None]
        csizer = wx.BoxSizer(wx.VERTICAL)
        for i, imgpanel in enumerate((self.img1_panel, self.img2_panel)):
            self.cmap_panels[i] =  ColorMapPanel(conf_panel, imgpanel,
                                                 title='Map %i: ' % (i+1),
                                                 color=0,
                                                 default='gray', #COLORMAPS[i],
                                                 colormap_list=ColorMap_List, #COLORMAPS,
                                                 cmap_callback=partial(self.onColorMap, index=i))

            csizer.Add(self.cmap_panels[i], 0, lsty, 2)
            csizer.Add(wx.StaticLine(conf_panel, size=(200, 2),
                                    style=wx.LI_HORIZONTAL), 0, lsty, 2)

        cust = self.CustomConfig(conf_panel)
        if cust is not None:
            sizer.Add(cust, 0, lsty, 1)
        pack(conf_panel, csizer)

        for name, panel in (('map1',    self.img1_panel),
                            ('map2',    self.img2_panel)):

            panel.report_leftdown = partial(self.report_leftdown, name=name)
            panel.messenger = self.write_message

        #sizer = wx.GridSizer(2, 1, 2, 2)
        sizer = wx.GridSizer(1, 2, 2, 2)
        print 'what size to make this...? also, which orientation?'
        lsty |= wx.GROW|wx.ALL|wx.EXPAND|wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
        sizer.Add(self.img1_panel, 1, lsty, 2)
        sizer.Add(self.img2_panel, 1, lsty, 2)

        pack(main_panel, sizer)
        splitter.SplitVertically(conf_panel, main_panel, 1)

        self.BuildMenu()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)
        pack(self, sizer)

    def CustomConfig(self, parent):
        """
        override to add custom config panel items to bottom of config panel
        """
        pass

    def onColorMap(self, name=None, index=None):
        colors = color_complements(name)
        opanel = self.cmap_panels[0]
        if index == 0:
            opanel = self.cmap_panels[1]

        c1 = opanel.cmap_choice.GetStringSelection()
        opanel.cmap_choice.Clear()
        for c in colors:
            opanel.cmap_choice.Append(c)
        if c1 in colors:
            opanel.cmap_choice.SetStringSelection(c1)
        else:
            opanel.cmap_choice.SetStringSelection(colors[0])
            opanel.set_colormap(name=colors[0])
            opanel.imgpanel.redraw()


    def unzoom(self, event=None):
        self.xzoom = slice(0, self.map1.shape[1]+1)
        self.yzoom = slice(0, self.map1.shape[0]+1)

        for p in self.imgpanels:
            p.unzoom_all()

    def BuildMenu(self):
        # file menu
        mfile = self.Build_FileMenu()

        mview =  wx.Menu()

        MenuItem(self, mview, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range",
                 self.unzoom)

        mcont =  wx.Menu()
        MenuItem(self, mcont, 'Toggle Contrast Enhancement\tCtrl+E',
                 'Toggle contrast between auto-scale and full-scale',
                 self.onEnhanceContrast, kind=wx.ITEM_CHECK)

        MenuItem(self, mcont, 'Set Auto-Contrast Level',
                 'Set auto-contrast scale',
                 self.onContrastConfig)


        # smoothing
        msmoo = wx.Menu()
        for itype in Interp_List:
            wid = wx.NewId()
            msmoo.AppendRadioItem(wid, itype, itype)
            self.Bind(wx.EVT_MENU, partial(self.onInterp, name=itype), id=wid)

        mbar = wx.MenuBar()
        mbar.Append(mfile, 'File')
        mbar.Append(mview, 'Image')
        mbar.Append(mcont, 'Contrast')
        mbar.Append(msmoo, 'Smoothing')

        self.SetMenuBar(mbar)
        self.Bind(wx.EVT_CLOSE,self.onExit)


    def save_figure(self, event=None):
        if not HAS_IMAGE:
            return

        file_choices = "PNG (*.png)|*.png|SVG (*.svg)|*.svg|PDF (*.pdf)|*.pdf"
        ofile = "%s.png" % self.title
        dlg = wx.FileDialog(self, message='Save Figure as...',
                            defaultDir = os.getcwd(),
                            defaultFile=ofile,
                            wildcard=file_choices,
                            style=wx.FD_SAVE|wx.FD_CHANGE_DIR)

        if dlg.ShowModal() != wx.ID_OK:
            return

        path = dlg.GetPath()
        img = self.make_composite_image()
        img.save(path)
        self.write_message('Saved plot to %s' % path)

    def make_composite_image(self):
        h, w = 0, 0
        def GetImage(panel):
            wximg = panel.canvas.bitmap.ConvertToImage()
            w, h = wximg.GetWidth(), wximg.GetHeight()
            img = Image.new( 'RGB', (w, h))
            img.frombytes(bytes(wximg.GetData()))
            return img, w, h

        img1, w1, h1 = GetImage(self.img1_panel)
        img2, w2, h2 = GetImage(self.img2_panel)

        w = (w1 + w2 ) / 2
        h = (h1 + h2 ) / 2

        img = Image.new('RGB', (2*w+2, 2*h+2))
        img.paste(img1, (0,   0))
        img.paste(img2, (1+w, 1+h))
        return img

    def Copy_to_Clipboard(self, event=None):
        img = self.make_composite_image()
        bmp_obj = wx.BitmapDataObject()
        bmp_obj.SetBitmap(image2wxbitmap(img))

        if not wx.TheClipboard.IsOpened():
            open_success = wx.TheClipboard.Open()
            if open_success:
                wx.TheClipboard.SetData(bmp_obj)
                wx.TheClipboard.Close()
                wx.TheClipboard.Flush()

    def PrintSetup(self, event=None):
        dlg = wx.MessageDialog(self, "Printing not Available",
                               "Save Image or Copy to Clipboard",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def PrintPreview(self, event=None):
        dlg = wx.MessageDialog(self, "Printing not Available",
                               "Save Image or Copy to Clipboard",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def Print(self, event=None):
        dlg = wx.MessageDialog(self, "Printing not Available",
                               "Save Image or Copy to Clipboard",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onInterp(self, event=None, name=None):
        if name not in Interp_List:
            name = Interp_List[0]
        for ipanel in self.imgpanels:
            ipanel.conf.interp = name
            ipanel.redraw()

    def onExit(self, event=None):
        self.Destroy()

    def onEnhanceContrast(self, event=None):
        """change image contrast, using scikit-image exposure routines"""
        for ipanel in self.imgpanels:
            ipanel.conf.auto_contrast = event.IsChecked()
            ipanel.redraw()
        self.set_contrast_levels()


    def onContrastConfig(self, event=None):
        dlg = AutoContrastDialog(parent=self, conf=self.img1_panel.conf)
        dlg.CenterOnScreen()
        val = dlg.ShowModal()
        if val == wx.ID_OK:
            for ipanel in self.imgpanels:
                ipanel.conf.auto_contrast_level = self.img1_panel.conf.auto_contrast_level
        dlg.Destroy()
        self.set_contrast_levels()

    def report_leftdown(self,event=None, name=''):
        if event is None:
            return
        if event.xdata is None or event.ydata is None:
            return
        ix, iy = int(round(event.xdata)), int(round(event.ydata))
        if (ix >= 0 and ix < self.map1.shape[1] and
            iy >= 0 and iy < self.map1.shape[0]):
            pos = ''
            if self.xdata is not None:
                pos = ' %s=%.4g,' % (self.xlabel, self.xdata[ix])
            if self.ydata is not None:
                pos = '%s %s=%.4g,' % (pos, self.ylabel, self.ydata[iy])

            d1, d2 = (self.map1[iy, ix], self.map2[iy, ix])
            msg = "Pixel [%i, %i],%s %s=%.4g, %s=%.4g" % (ix, iy, pos,
                                                          self.name1, d1,
                                                          self.name2, d2)
            self.write_message(msg, panel=0)

            if callable(self.cursor_callback):
                self.cursor_callback(x=event.xdata, y=event.ydata)

    def on_imagezoom(self, event=None, wid=0, limits=None):
        if wid in [w.GetId() for w in self.imgpanels]:
            lims = [int(x) for x in limits]
            for ipanel in self.imgpanels:
                ax = ipanel.fig.axes[0]
                axlims = {ax: lims}
                ipanel.conf.zoom_lims.append(axlims)
                ipanel.set_viewlimits()

        m1 = self.map1[lims[2]:lims[3], lims[0]:lims[1]]
        m2 = self.map2[lims[2]:lims[3], lims[0]:lims[1]]
        self.xzoom = slice(lims[0], lims[1])
        self.yzoom = slice(lims[2], lims[3])

    def display(self, map1, map2, title=None, name1='Sinogram', name2='Tomograph',
                xlabel='x', ylabel='y', x=None, y=None):
        
        print 'shape',np.shape(map1),np.shape(map2)
        self.map1 = map1
        self.map2 = map2
        self.name1 = name1
        self.name2 = name2
        self.xdata = x
        self.ydata = y
        self.xlabel = xlabel
        self.ylabel = ylabel
        
#         for comp in self.config_panel.Children:
#             comp.Destroy()
        
        self.map1 = np.array(self.map1)
        if len(self.map1.shape) == 3:
            ishape = self.map1.shape
            # make sure 3d image is shaped (NY, NX, 3)
            if ishape[2] != 3:
                if ishape[0] == 3:
                    self.map1 = self.map1.swapaxes(0, 1).swapaxes(1, 2)
                elif ishape[1] == 3:
                    self.map1 = self.map1.swapaxes(1, 2)
            #self.config_mode = 'rgb'
            self.img1_panel.conf.tricolor_mode = 'rgb'
            #self.Build_ConfigPanel()
        #else:
        #    #self.config_mode = 'int'
        #    #self.Build_ConfigPanel()

        self.map2 = np.array(self.map2)
        if len(self.map2.shape) == 3:
            ishape = self.map2.shape
            # make sure 3d image is shaped (NY, NX, 3)
            if ishape[2] != 3:
                if ishape[0] == 3:
                    self.map2 = self.map2.swapaxes(0, 1).swapaxes(1, 2)
                elif ishape[1] == 3:
                    self.map2 = self.map2.swapaxes(1, 2)
            #self.config_mode = 'rgb'
            self.img2_panel.conf.tricolor_mode = 'rgb'
            #self.Build_ConfigPanel()
        #else:
        #    #self.config_mode = 'int'
        #    #self.Build_ConfigPanel()

        print 'shape',np.shape(self.map1),np.shape(self.map2)
            
        self.xzoom = slice(0, map1.shape[1]+1)
        self.yzoom = slice(0, map1.shape[0]+1)

        self.img1_panel.display(map1, x=x, y=y)
        self.img2_panel.display(map2, x=x, y=y)

        self.cmap_panels[0].title.SetLabel(name1)
        self.cmap_panels[1].title.SetLabel(name2)

        self.set_contrast_levels()

    def set_contrast_levels(self):
        """enhance contrast levels, or use full data range
        according to value of self.panel.conf.auto_contrast
        """
        for cmap_panel, img_panel in zip((self.cmap_panels[0], self.cmap_panels[1]),
                                         (self.img1_panel, self.img2_panel)):
            conf = img_panel.conf
            img  = img_panel.conf.data
            enhance = conf.auto_contrast
            clevel = conf.auto_contrast_level
            jmin = imin = img.min()
            jmax = imax = img.max()
            cmap_panel.imin_val.SetValue('%.4g' % imin)
            cmap_panel.imax_val.SetValue('%.4g' % imax)
            if enhance:
                jmin, jmax = np.percentile(img, [clevel, 100.0-clevel])

            conf.int_lo[0]  = imin
            conf.int_hi[0]  = imax
            conf.cmap_lo[0] = xlo = (jmin-imin)*conf.cmap_range/(imax-imin)
            conf.cmap_hi[0] = xhi = (jmax-imin)*conf.cmap_range/(imax-imin)

            cmap_panel.cmap_hi.SetValue(xhi)
            cmap_panel.cmap_lo.SetValue(xlo)
            cmap_panel.islider_range.SetLabel('Shown: [ %.4g :  %.4g ]' % (jmin, jmax))
            cmap_panel.redraw_cmap()
            img_panel.redraw()

