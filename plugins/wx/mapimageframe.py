#!/usr/bin/python
"""
subclass of wxmplot.ImageFrame specific for Map Viewer -- adds custom menus
"""
import os
import wx
import numpy
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg

from wxutils import Closure, LabelEntry

from wxmplot import ImageFrame
from wxmplot.imagepanel import ImagePanel
from wxmplot.imageconf import ColorMap_List, Interp_List
from wxmplot.colors import rgb2hex


CURSOR_MENULABELS = {'zoom':  ('Zoom to Rectangle\tCtrl+B',
                               'Left-Drag to zoom to rectangular box'),
                     'lasso': ('Select Points\tCtrl+X',
                               'Left-Drag to select points freehand'),
                     'prof':  ('Select Line Profile\tCtrl+K',
                               'Left-Drag to select like for profile')}

class MapImageFrame(ImageFrame):
    """
    MatPlotlib Image Display ons a wx.Frame, using ImagePanel
    """

    def __init__(self, parent=None, size=None,
                 config_on_frame=True, lasso_callback=None,
                 show_xsections=False, cursor_labels=None,
                 output_title='Image',   **kws):

        ImageFrame.__init__(self, parent=parent, size=size,
                            config_on_frame=config_on_frame,
                            lasso_callback=lasso_callback,
                            cursor_labels=cursor_labels,
                            output_title=output_title, **kws)

    def display(self, img, title=None, colormap=None, style='image', **kw):
        """plot after clearing current plot """
        if title is not None:
            self.SetTitle(title)
        if self.config_on_frame:
            if len(img.shape) == 3:
                for comp in self.config_panel.Children:
                    comp.Disable()
            else:
                for comp in self.config_panel.Children:
                    comp.Enable()
        self.panel.display(img, style=style, **kw)
        self.panel.conf.title = title
        if colormap is not None:
            self.set_colormap(name=colormap)
        contour_value = 0
        if style == 'contour':
            contour_value = 1
        if self.config_on_frame:
            self.contour_toggle.SetValue(contour_value)
        self.panel.redraw()


    def BuildMenu(self):
        mids = self.menuIDs
        m0 = wx.Menu()
        mids.EXPORT = wx.NewId()
        m0.Append(mids.SAVE,   "&Save Image\tCtrl+S",  "Save PNG Image of Plot")
        m0.Append(mids.CLIPB,  "&Copy Image\tCtrl+C",  "Copy Image to Clipboard")
        m0.Append(mids.EXPORT, "Export Data",   "Export to ASCII file")
        m0.AppendSeparator()
        m0.Append(mids.PSETUP, 'Page Setup...', 'Printer Setup')
        m0.Append(mids.PREVIEW, 'Print Preview...', 'Print Preview')
        m0.Append(mids.PRINT, "&Print\tCtrl+P", "Print Plot")
        m0.AppendSeparator()
        m0.Append(mids.EXIT, "E&xit\tCtrl+Q", "Exit the 2D Plot Window")

        self.top_menus['File'] = m0

        mhelp = wx.Menu()
        mhelp.Append(mids.HELP, "Quick Reference",  "Quick Reference for WXMPlot")
        mhelp.Append(mids.ABOUT, "About", "About WXMPlot")
        self.top_menus['Help'] = mhelp

        mbar = wx.MenuBar()

        mbar.Append(self.top_menus['File'], "File")
        for m in self.user_menus:
            title,menu = m
            mbar.Append(menu, title)
        mbar.Append(self.top_menus['Help'], "&Help")


        self.SetMenuBar(mbar)
        self.Bind(wx.EVT_MENU, self.onHelp,            id=mids.HELP)
        self.Bind(wx.EVT_MENU, self.onAbout,           id=mids.ABOUT)
        self.Bind(wx.EVT_MENU, self.onExit ,           id=mids.EXIT)
        self.Bind(wx.EVT_CLOSE,self.onExit)

    def BuildCustomMenus(self):
        "build menus"
        mids = self.menuIDs
        mids.SAVE_CMAP = wx.NewId()
        mids.LOG_SCALE = wx.NewId()
        mids.FLIP_H    = wx.NewId()
        mids.FLIP_V    = wx.NewId()
        mids.FLIP_O    = wx.NewId()
        mids.ROT_CW    = wx.NewId()
        mids.CUR_ZOOM  = wx.NewId()
        mids.CUR_LASSO = wx.NewId()
        mids.CUR_PROF  = wx.NewId()
        m = wx.Menu()
        m.Append(mids.UNZOOM, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range")
        m.Append(mids.SAVE_CMAP, "Save Image of Colormap")
        m.AppendSeparator()
        m.Append(mids.LOG_SCALE, "Log Scale Intensity\tCtrl+L", "", wx.ITEM_CHECK)
        m.Append(mids.ROT_CW, 'Rotate clockwise\tCtrl+R', '')
        m.Append(mids.FLIP_V, 'Flip Top/Bottom\tCtrl+T', '')
        m.Append(mids.FLIP_H, 'Flip Left/Right\tCtrl+F', '')
        # m.Append(mids.FLIP_O, 'Flip to Original', '')
        m.AppendSeparator()
        m.Append(wx.NewId(), 'Cursor Modes : ',
                 'Action taken on with Left-Click and Left-Drag')

        clabs = self.cursor_menulabels
        m.AppendRadioItem(mids.CUR_ZOOM,  clabs['zoom'][0],  clabs['zoom'][1])
        m.AppendRadioItem(mids.CUR_LASSO, clabs['lasso'][0], clabs['lasso'][1])
        m.AppendRadioItem(mids.CUR_PROF,  clabs['prof'][0],  clabs['prof'][1])
        m.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.onFlip,       id=mids.FLIP_H)
        self.Bind(wx.EVT_MENU, self.onFlip,       id=mids.FLIP_V)
        self.Bind(wx.EVT_MENU, self.onFlip,       id=mids.FLIP_O)
        self.Bind(wx.EVT_MENU, self.onFlip,       id=mids.ROT_CW)
        self.Bind(wx.EVT_MENU, self.onCursorMode, id=mids.CUR_ZOOM)
        self.Bind(wx.EVT_MENU, self.onCursorMode, id=mids.CUR_PROF)
        self.Bind(wx.EVT_MENU, self.onCursorMode, id=mids.CUR_LASSO)

        sm = wx.Menu()
        for itype in Interp_List:
            wid = wx.NewId()
            sm.AppendRadioItem(wid, itype, itype)
            self.Bind(wx.EVT_MENU, Closure(self.onInterp, name=itype), id=wid)
        self.user_menus  = [('&Options', m), ('Smoothing', sm)]


    def onCursorMode(self, event=None):
        wid = event.GetId()
        self.panel.cursor_mode = 'zoom'
        if wid == self.menuIDs.CUR_PROF:
            self.panel.cursor_mode = 'profile'
        elif wid == self.menuIDs.CUR_LASSO:
            self.panel.cursor_mode = 'lasso'

    def onLasso(self, data=None, selected=None, mask=None, **kws):
        if hasattr(self.lasso_callback , '__call__'):
            self.lasso_callback(data=data, selected=selected, mask=mask, **kws)


    def redraw_cmap(self):
        conf = self.panel.conf
        if not hasattr(conf, 'image'): return
        # conf.image.set_cmap(conf.cmap)
        self.cmap_image.set_cmap(conf.cmap)

        lo = conf.cmap_lo
        hi = conf.cmap_hi
        cmax = 1.0 * conf.cmap_range
        wid = numpy.ones(cmax/4)
        self.cmap_data[:lo, :] = 0
        self.cmap_data[lo:hi] = numpy.outer(numpy.linspace(0., 1., hi-lo), wid)
        self.cmap_data[hi:, :] = 1
        self.cmap_image.set_data(self.cmap_data)
        self.cmap_canvas.draw()

