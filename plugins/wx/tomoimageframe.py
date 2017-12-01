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
                     'lasso': ('Select Points for XRF/XRD Spectra\tCtrl+N',
                               'Left-Drag to select points freehand'),
                     'prof':  ('Select Line Profile\tCtrl+K',
                               'Left-Drag to select like for profile')}

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
                 lasso_callback=True, move_callback=None, save_callback=None,
                 show_xsections=False, cursor_labels=None,
                 output_title='Image', subtitles=None,
                 user_menus=None, **kws):

        if size is None: size = (1500, 600)
        self.lasso_callback = lasso_callback
        self.user_menus = user_menus
        self.cursor_menulabels =  {}
        self.cursor_menulabels.update(CURSOR_MENULABELS)
        if cursor_labels is not None:
            self.cursor_menulabels.update(cursor_labels)
            
        self.img_label = ['Sinogram', 'Tomograph']


        self.det = None
        self.xrmfile = None
        self.map = None
        self.move_callback = move_callback
        self.save_callback = save_callback
        self.wxmplot_version = get_wxmplot_version()

        BaseFrame.__init__(self, parent=parent,
                           title  = 'Image Display Frame',
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

        self.config_panel = wx.Panel(splitter) ## wx.Panel(self) 
        self.main_panel   = wx.Panel(splitter) ## wx.Panel(self) 
        
        img_opts = dict(data_callback=self.onDataChange,
                        size=(700, 525), dpi=100,
                        lasso_callback=self.onLasso,
                        output_title=self.output_title)
        self.img_panel = [ImagePanel(self.main_panel, **img_opts),
                          ImagePanel(self.main_panel, **img_opts)]
        

        for ipanel in self.img_panel:
            ipanel.nstatusbar = sbar.GetFieldsCount()

        self.BuildMenu()

        self.SetBackgroundColour('#F8F8F4')

        self.imin_val = {}
        self.imax_val = {}
        self.islider_range = {}

        self.config_mode = 'int'
        if mode.lower().startswith('rgb'):
            self.config_mode = 'rgb'

        self.Build_ConfigPanel()

        for ilabel, ipanel in zip(self.img_label,self.img_panel):
            ipanel.report_leftdown = partial(self.report_leftdown, name=ilabel)
            ipanel.messenger = self.write_message

        lsty = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND
        gsizer = wx.GridSizer(1, 2, 2, 2)
        lsty |= wx.GROW|wx.ALL|wx.EXPAND|wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
        gsizer.Add(self.img_panel[0], 1, lsty, 2)
        gsizer.Add(self.img_panel[1], 1, lsty, 2)

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

        self.name1, self.name2 = name1, name2
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
                self.img_panel[0].conf.tricolor_mode = 'rgb'
                self.Build_ConfigPanel()
        else: ##if len(map1.shape) == 2 and len(map2.shape) == 2:
            if cmode != 'int':
                for comp in self.config_panel.Children:
                    comp.Destroy()
                self.config_mode = 'int'
                self.Build_ConfigPanel()

               
        self.map1,self.map2 = map1,map2

        self.img_panel[0].display(map1, style=style, **kws)
        self.img_panel[1].display(map2, style=style, **kws)

        self.img_panel[0].conf.title = name1
        self.img_panel[1].conf.title = name2

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

        self.img_panel[0].redraw()
        self.img_panel[1].redraw()

        self.config_panel.Refresh()
        self.SendSizeEvent()
        wx.CallAfter(self.EnableMenus)

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
            msg = 'Pixel [%i, %i],%s %s=%.4g, %s=%.4g' % (ix, iy, pos,
                                                          self.name1, d1,
                                                          self.name2, d2)
            self.write_message(msg, panel=0)

            if callable(self.cursor_callback):
                self.cursor_callback(x=event.xdata, y=event.ydata)

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
        is_3color = len(self.img_panel[0].conf.data.shape) > 2
        for menu, on_3color in self.optional_menus:
            menu.Enable(is_3color==on_3color)

    def unzoom_all(self):
        self.img_panel[0].unzoom()
        self.img_panel[1].unzoom()
    
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
        MenuItem(self, mint,  'Log Scale Intensity\tCtrl+L',
                 'use logarithm to set intensity scale',
                 self.onLogScale, kind=wx.ITEM_CHECK)

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
        for ipanel in self.img_panel:
            ipanel.conf.interp = name
            ipanel.redraw()

    def onCursorMode(self, event=None, mode='zoom'):

        choice = self.zoom_mode.GetString(self.zoom_mode.GetSelection())
        for ipanel in self.img_panel:
            ipanel.cursor_mode = mode
            if event is not None:
                if choice.startswith('Pick Area'):
                    ipanel.cursor_mode = 'lasso'
                elif choice.startswith('Show Line'):
                    ipanel.cursor_mode = 'prof'

    def onProject(self, event=None, mode='y'):

        wid = event.GetId()
        if mode=='x':
            x = self.img_panel[0].ydata
            y = self.img_panel[0].conf.data.sum(axis=1)
            x = self.img_panel[1].ydata
            y = self.img_panel[1].conf.data.sum(axis=1)
            axname = 'horizontal'
            if x is None:
                x = np.arange(y.shape[0])

        else:
            x = self.img_panel[0].xdata
            y = self.img_panel[0].conf.data.sum(axis=0)
            x = self.img_panel[1].xdata
            y = self.img_panel[1].conf.data.sum(axis=0)
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

        for ipanel in self.img_panel:
            conf = ipanel.conf
            if mode == 'flip_lr':
                conf.flip_lr = not conf.flip_lr
            elif mode == 'flip_ud':
                conf.flip_ud = not conf.flip_ud
            elif mode == 'flip_orig':
                conf.flip_lr, conf.flip_ud = False, False
            elif mode == 'rot_cw':
                conf.rot = True
            ipanel.unzoom_all()

    def Build_ConfigPanel(self):
        '''config panel for left-hand-side of frame: RGB Maps'''

# #         FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS
# # 
# #         bsizer = wx.BoxSizer(wx.VERTICAL)
# #         nb = flat_nb.FlatNotebook(self, wx.ID_ANY, agwStyle=FNB_STYLE)
# #         
# #         lsty = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND
# # 
# #         icol = 0
# #         if self.config_mode == 'rgb':
# #             for ilabel, ipanel in zip(self.img_label,self.img_panel):
# #                 csizer = wx.BoxSizer(wx.VERTICAL)
# #                 for i,col in enumerate(RGB_COLORS):
# #                     self.cmap_panels[icol] =  ColorMapPanel(self.config_panel,
# #                                                             ipanel,
# #                                                             title='%s - %s: ' % (ilabel,col.title()),
# #                                                             color=i,
# #                                                             default=col,
# #                                                             colormap_list=None)
# # 
# #                     csizer.Add(self.cmap_panels[icol], 0, lsty, 2)
# #                     csizer.Add(wx.StaticLine(self.config_panel, size=(100, 2),
# #                                             style=wx.LI_HORIZONTAL), 0, lsty, 2)
# #                     icol += 1
# # #                 nb.AddPage(csizer, ilabel)
# # 
# # 
# #         else:
# #             for ilabel, ipanel in zip(self.img_label,self.img_panel):
# #                 csizer = wx.BoxSizer(wx.VERTICAL)
# #                 self.cmap_panels[icol] =  ColorMapPanel(self.config_panel,
# #                                                         ipanel,
# #                                                         title='%s: ' % ilabel,
# #                                                         default='gray',
# #                                                         colormap_list=ColorMap_List)
# # 
# #                 csizer.Add(self.cmap_panels[icol],  0, lsty, 1)
# #                 csizer.Add(wx.StaticLine(self.config_panel, size=(100, 2),
# #                                         style=wx.LI_HORIZONTAL), 0, lsty, 2)
# #                 icol += 1
# # #                 nb.AddPage(csizer, ilabel)
# # 
# #         bsizer.Add(nb, 0, lsty, 1)
# #         cust = self.CustomConfig(self.config_panel, None, 0)
# #         if cust is not None:
# #             bsizer.Add(cust, 0, lsty, 1)
# #         pack(self.config_panel, bsizer)
        
        csizer = wx.BoxSizer(wx.VERTICAL)
        lsty = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND

        icol = 0
        if self.config_mode == 'rgb':
            for ilabel, ipanel in zip(self.img_label,self.img_panel):
                for i,col in enumerate(RGB_COLORS):
                    self.cmap_panels[icol] =  ColorMapPanel(self.config_panel,
                                                            ipanel,
                                                            title='%s - %s: ' % (ilabel,col.title()),
                                                            color=i,
                                                            default=col,
                                                            colormap_list=None)

                    csizer.Add(self.cmap_panels[icol], 0, lsty, 2)
                    csizer.Add(wx.StaticLine(self.config_panel, size=(100, 2),
                                            style=wx.LI_HORIZONTAL), 0, lsty, 2)
                    icol += 1


        else:
            for ilabel, ipanel in zip(self.img_label,self.img_panel):
                self.cmap_panels[icol] =  ColorMapPanel(self.config_panel,
                                                        ipanel,
                                                        title='%s: ' % ilabel,
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
                         'Pick Area for XRF/XRD Spectra',
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
            self.zoom_mode = wx.RadioBox(panel, -1, 'Cursor Mode:',
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



    def onContrastConfig(self, event=None):
        
        for ipanel in self.img_panel:
            dlg = AutoContrastDialog(parent=self, conf=ipanel.conf)
            dlg.CenterOnScreen()
            val = dlg.ShowModal()
            if val == wx.ID_OK:
                pass
            dlg.Destroy()


    def onContourConfig(self, event=None):

        for icol,ipanel in enumerate(self.img_panel):
            conf = ipanel.conf
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

            ipanel.axes.cla()
            ipanel.display(conf.data, x=ipanel.xdata, y = ipanel.ydata,
                          xlabel=ipanel.xlab, ylabel=ipanel.ylab,
                          contour_labels=conf.contour_labels,
                          nlevels=conf.ncontour_levels, style='contour')
            ipanel.redraw()

    def onContourToggle(self, event=None):

        for icol,ipanel in enumerate(self.img_panel):
            if len(ipanel.conf.data.shape) > 2:
                return
            conf  = ipanel.conf
            conf.style = 'image'
            if event.IsChecked():
                conf.style = 'contour'
            nlevels = int(conf.ncontour_levels)
            if self.config_mode == 'int':
                self.cmap_panels[0].set_colormap()
            ipanel.axes.cla()
            ipanel.display(conf.data, x=ipanel.xdata, y = ipanel.ydata,
                          nlevels=nlevels, contour_labels=conf.contour_labels,
                          xlabel=ipanel.xlab, ylabel=ipanel.ylab,
                          style=conf.style)
            ipanel.redraw()

    def onTriColorBG(self, event=None):
        bgcol = {True:'white', False:'black'}[event.IsChecked()]

        icol = 0
        for ipanel in self.img_panel:
            conf = ipanel.conf
            if bgcol == conf.tricolor_bg:
                return

            conf.tricolor_bg = bgcol
            cmaps = colors = RGB_COLORS
            if bgcol.startswith('wh'):
                cmaps = ('Reds', 'Greens', 'Blues')

            for i in range(3):
                self.cmap_panels[icol].set_colormap(name=cmaps[i])
                icol += 1

            ipanel.redraw()

    def onLasso(self, data=None, selected=None, mask=None, **kws):
        if hasattr(self.lasso_callback , '__call__'):
            self.lasso_callback(data=data, selected=selected, mask=mask, **kws)

    def onDataChange(self, data, x=None, y=None, col='int', **kw):

        icol = 0
        for ipanel in self.img_panel:
            conf = ipanel.conf
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
        for ipanel in self.img_panel: self.ipanel.conf.auto_contrast = event.IsChecked()
        self.set_contrast_levels()
        for ipanel in self.img_panel: ipanel.redraw()

    def set_contrast_levels(self):
        '''enhance contrast levels, or use full data range
        according to value of panel.conf.auto_contrast
        '''

        icol = 0
        for ipanel in self.img_panel:
            conf = ipanel.conf
            img  = ipanel.conf.data
            enhance = conf.auto_contrast
            clevel = conf.auto_contrast_level
            if len(img.shape) == 2: # intensity map
                jmin = imin = img.min()
                jmax = imax = img.max()
                self.cmap_panels[icol].imin_val.SetValue('%.4g' % imin)
                self.cmap_panels[icol].imax_val.SetValue('%.4g' % imax)
                if enhance:
                    jmin, jmax = np.percentile(img, [clevel, 100.0-clevel])
                if imax == imin:
                    imax = imin + 0.5
                conf.cmap_lo[icol] = xlo = (jmin-imin)*conf.cmap_range/(imax-imin)
                conf.cmap_hi[icol] = xhi = (jmax-imin)*conf.cmap_range/(imax-imin)

                # print('Set contrast level =', conf.cmap_hi, conf.cmap_range)

                self.cmap_panels[icol].cmap_hi.SetValue(xhi)
                self.cmap_panels[icol].cmap_lo.SetValue(xlo)
                self.cmap_panels[icol].islider_range.SetLabel('Shown: [ %.4g :  %.4g ]' % (jmin, jmax))
                self.cmap_panels[icol].redraw_cmap()
                icol += 1

            if len(img.shape) == 3: # rgb map
                for ix in range(3):
                    jmin = imin = img[:,:,ix].min()
                    jmax = imax = img[:,:,ix].max()
                    self.cmap_panels[icol].imin_val.SetValue('%.4g' % imin)
                    self.cmap_panels[icol].imax_val.SetValue('%.4g' % imax)
                    if enhance:
                        jmin, jmax = np.percentile(img[:,:,ix], [1, 99])
                    if imax == imin:
                        imax = imin + 0.5
                    conf.cmap_lo[ix] = xlo = (jmin-imin)*conf.cmap_range/(imax-imin)
                    conf.cmap_hi[ix] = xhi = (jmax-imin)*conf.cmap_range/(imax-imin)
                    self.cmap_panels[icol].cmap_hi.SetValue(xhi)
                    self.cmap_panels[icol].cmap_lo.SetValue(xlo)

                    self.cmap_panels[icol].islider_range.SetLabel('Shown: [ %.4g :  %.4g ]' % (jmin, jmax))
                    self.cmap_panels[icol].redraw_cmap()
                    icol += 1

    def onLogScale(self, event=None):
        
        for ipanel in self.img_panel:
            ipanel.conf.log_scale = not ipanel.conf.log_scale
            ipanel.redraw()

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
        for ipanel in self.img_panel:
            if ipanel is not None:
                ipanel.save_figure(event=event, transparent=transparent, dpi=dpi)
