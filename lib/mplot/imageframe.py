#!/usr/bin/python
##
## MPlot PlotFrame: a wx.Frame for 2D line plotting, using matplotlib
##
import os
import wx
import numpy
import matplotlib.cm as colormap
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg

from .imagepanel import ImagePanel
from .baseframe import BaseFrame
from colors import rgb2hex
ColorMap_List = ('gray', 'jet', 'hsv', 'Reds', 'Greens', 'Blues', 'hot',
                 'cool', 'copper', 'spring', 'summer', 'autumn', 'winter',
                 'Spectral', 'Accent', 'Set1', 'Set2', 'Set3')

Interp_List = ('nearest', 'bilinear', 'bicubic', 'spline16', 'spline36',
               'hanning', 'hamming', 'hermite', 'kaiser', 'quadric',
               'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc',
               'lanczos')   

class ImageFrame(BaseFrame):
    """
    MatPlotlib Image Display ons a wx.Frame, using ImagePanel
    """
    def __init__(self, parent=None, size=(550,450),
                 exit_callback=None, config_on_frame=True,
                 **kwds):
        self.exit_callback = exit_callback
        self.title  = 'Image Display Frame(Larch)'
        self.size = size
        self.config_on_frame = config_on_frame
        show_config_popup = not config_on_frame

        self.img_panel = ImagePanel(self, parent,
                                show_config_popup=show_config_popup)
        self.conf = self.img_panel.conf
        BaseFrame.__init__(self, parent=parent,
                           panel=self.img_panel, size=size)
        self.BuildFrame(size=size, **kwds)
        
    def display(self,img,**kw):
        """plot after clearing current plot """        
        self.img_panel.display(img,**kw)
      
    def BuildCustomMenus(self):
        mids = self.menuIDs
        mids.SAVE_CMAP = wx.NewId()
        m = wx.Menu()
        m.Append(mids.UNZOOM, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range")
        m.AppendSeparator()        
        m.Append(mids.SAVE_CMAP, "Save Colormap Image")

        self.user_menus  = [('&Options',m)]

    def BindCustomMenus(self):
        mids = self.menuIDs        
        self.Bind(wx.EVT_MENU, self.onCMapSave, id=mids.SAVE_CMAP)

    def BuildFrame(self, size=(550,450), **kwds):
        kwds['style'] = wx.DEFAULT_FRAME_STYLE
        kwds['size']  = size
        wx.Frame.__init__(self, self.parent, title=self.title, **kwds)

        sbar = self.CreateStatusBar(2,wx.CAPTION|wx.THICK_FRAME)
        sfont = sbar.GetFont()
        sfont.SetWeight(wx.BOLD)
        sfont.SetPointSize(10)
        sbar.SetFont(sfont)

        self.SetStatusWidths([-3,-1])
        self.SetStatusText('',0)

        self.BuildCustomMenus()
        self.BuildMenu()
        mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        if self.config_on_frame:
            lpanel = self.BuildConfigPanel()
            mainsizer.Add(lpanel, 0,
                          wx.LEFT|wx.ALIGN_LEFT|wx.TOP|wx.ALIGN_TOP|wx.EXPAND)

        if self.img_panel is not None:
            self.img_panel.BuildPanel()
            self.img_panel.messenger = self.write_message
            mainsizer.Add(self.img_panel, 1, wx.EXPAND)
            self.img_panel.fig.set_facecolor(self.bgcol)

            self.BindMenuToPanel()
            self.BindCustomMenus()
            
        self.SetAutoLayout(True)
        self.SetSizer(mainsizer)
        self.Fit()
            
    def BuildConfigPanel(self):
        """config panel for left-hand-side of frame"""
        lpanel = wx.Panel(self)
        lsizer = wx.GridBagSizer(7,4)

        labstyle = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.EXPAND
        imgstyle = labstyle|wx.EXPAND

        interp_choice =  wx.Choice(lpanel, choices=Interp_List)
        interp_choice.Bind(wx.EVT_CHOICE,  self.onInterp)
        
        interp_choice.SetStringSelection(self.conf.interp)
        s = wx.StaticText(lpanel,label=' Smoothing:')
        s.SetForegroundColour('Blue')
        lsizer.Add(s,               (0,0), (1,3), labstyle, 5)
        lsizer.Add(interp_choice,   (1,0), (1,3), labstyle, 2)

        s = wx.StaticText(lpanel, label=' Color Table:')
        s.SetForegroundColour('Blue')
        lsizer.Add(s, (2,0), (1,3), labstyle, 5)

        cmap_choice =  wx.Choice(lpanel, choices=ColorMap_List)
        cmap_choice.Bind(wx.EVT_CHOICE,  self.onCMap)
        cmap_name = self.conf.cmap.name
        if cmap_name.endswith('_r'): cmap_name = cmap_name[:-2]
        cmap_choice.SetStringSelection(cmap_name)

        cmap_toggle = wx.CheckBox(lpanel,label='Reverse Table',
                                  size=(140,-1))
        cmap_toggle.Bind(wx.EVT_CHECKBOX,self.onCMapReverse)
        cmap_toggle.SetValue(self.conf.cmap_reverse)

        # log_toggle = wx.CheckBox(lpanel,-1, 'Log Scale', (-1,-1),(-1,-1))
        # log_toggle.Bind(wx.EVT_CHECKBOX,self.onLogScale)
        # log_toggle.SetValue(self.conf.log_scale)

        ##
        cmax = self.conf.cmap_range
        self.cmap_data   = numpy.outer(numpy.linspace(0,1,cmax),
                                       numpy.ones(cmax/8))

        self.cmap_fig   = Figure((0.350, 1.75), dpi=100)
        self.cmap_axes  = self.cmap_fig.add_axes([0,0,1,1])
        self.cmap_axes.set_axis_off()
        
        self.cmap_canvas = FigureCanvasWxAgg(lpanel, -1,
                                             figure=self.cmap_fig)

        self.bgcol = rgb2hex(lpanel.GetBackgroundColour()[:3])
        self.cmap_fig.set_facecolor(self.bgcol)

        self.cmap_image = self.cmap_axes.imshow(self.cmap_data,
                                                cmap=self.conf.cmap,
                                                interpolation='bilinear')

        self.cmap_axes.set_ylim((0,cmax),emit=True)
        
        self.cmap_lo_val = wx.Slider(lpanel, -1,
                                     self.conf.cmap_lo,0,
                                     self.conf.cmap_range,
                                     size=(-1,200),
                                     style=wx.SL_INVERSE|wx.SL_VERTICAL)

        self.cmap_hi_val = wx.Slider(lpanel, -1,
                                     self.conf.cmap_hi,0,
                                     self.conf.cmap_range,
                                     size=(-1,200),
                                     style=wx.SL_INVERSE|wx.SL_VERTICAL)

        self.cmap_lo_val.Bind(wx.EVT_SCROLL,  self.onStretchLow)
        self.cmap_hi_val.Bind(wx.EVT_SCROLL,  self.onStretchHigh)


        lsizer.Add(cmap_choice,      (3,0), (1,4), labstyle, 2)
        lsizer.Add(cmap_toggle,      (4,0), (1,4), labstyle, 5)
        lsizer.Add(self.cmap_lo_val, (5,0), (1,1), labstyle, 5)
        lsizer.Add(self.cmap_canvas, (5,1), (1,2), wx.ALIGN_CENTER|labstyle)
        lsizer.Add(self.cmap_hi_val, (5,3), (1,1), labstyle, 5)
        # lsizer.Add(log_toggle,       (6,0), (1,4), labstyle)

        lpanel.SetSizer(lsizer)
        lpanel.Fit()
        return lpanel

    def onInterp(self,event=None):
        self.conf.interp =  event.GetString()
        self.conf.image.set_interpolation(self.conf.interp)
        self.conf.canvas.draw()

    def onCMap(self,event=None):
        self.update_cmap(event.GetString())

    def onCMapReverse(self,event=None):
        self.conf.cmap_reverse = event.IsChecked()
        cmap_name = self.conf.cmap.name
        if  cmap_name.endswith('_r'): cmap_name = cmap_name[:-2]
        self.update_cmap(cmap_name)
        
    def update_cmap(self, cmap_name):
        if  self.conf.cmap_reverse:  cmap_name = cmap_name + '_r'
        self.conf.cmap = getattr(colormap, cmap_name)
        
        self.conf.image.set_cmap(self.conf.cmap)
        self.cmap_image.set_cmap(self.conf.cmap)        
        self.conf.canvas.draw()
        self.cmap_canvas.draw()        
        
    def onStretchLow(self,event=None):
        lo =  event.GetInt()
        hi = self.cmap_hi_val.GetValue()
        self.StretchCMap(lo,hi)
        
    def onStretchHigh(self,event=None):
        hi = event.GetInt()
        lo = self.cmap_lo_val.GetValue()
        
        self.StretchCMap(lo,hi)
        
    def StretchCMap(self,low, high):
        lo,hi = min(low,high), max(low,high)
        if (hi-lo)<2:
            hi= min(hi+1,self.conf.cmap_range)
            lo= max(lo,0)

        self.cmap_lo_val.SetValue(lo)
        self.cmap_hi_val.SetValue(hi)
        self.conf.cmap_lo = lo
        self.conf.cmap_hi = hi
        self.UpdateImages()

    def UpdateImages(self):
        lo = self.conf.cmap_lo
        hi = self.conf.cmap_hi
        cmax = 1.0 * self.conf.cmap_range

        wid=numpy.ones(cmax/8)

        # color table altered into a set of 3 linear segments: 
        # Intensity = 0.0:0.1  between 0 and lo
        # Intensity = 0.1:0.9  between lo and hi
        # Intensity = 0.9:1.0  between hi and cmap_range (highest value)
        # self.cmap_data[:lo,:] = numpy.outer(numpy.linspace(0.0,0.1,lo),wid)
        # self.cmap_data[lo:hi] = numpy.outer(numpy.linspace(0.1,0.9,hi-lo),wid)
        # self.cmap_data[hi:,:] = numpy.outer(numpy.linspace(0.9,1.0,cmax-hi),wid)
        # ex = self.cmap_data[:,0]
        # print ex, len(ex), lo, hi
        
        self.cmap_data[:lo,:] = 0  
        self.cmap_data[lo:hi] = numpy.outer(numpy.linspace(0.0,1.0,hi-lo),wid)
        self.cmap_data[hi:,:] = 1

        img = cmax * self.conf.data/(1.0*self.conf.data.max())
        img = numpy.clip((cmax*(img-lo)/(hi-lo+1.e-5)),0, int(cmax-1))/cmax

        cmap_fill_val = 1.0/(hi-lo)
        if self.conf.log_scale:
            imin = img[numpy.where(img>0)].min()
            img = numpy.log(abs(img)+imin/5.0)
            img = (img-img.min()) / abs(img.max()-img.min())

            cmimg = numpy.log(self.cmap_data+cmap_fill_val/5.0)
            cmimg = (cmimg-cmimg.min()) / abs(cmimg.max()-cmimg.min())
            self.cmap_data = cmimg
            
        cmap_max = self.cmap_data.max()

        self.cmap_image.set_data(self.cmap_data)

        self.cmap_canvas.draw()
        self.conf.image.set_data(img)
        self.conf.canvas.draw()

    def onLogScale(self,event=None):
        self.conf.log_scale = event.IsChecked()
        self.UpdateImages()
        
    def onCMapSave(self,event=None):
        """save color table image"""
        file_choices = "PNG (*.png)|*.png"
        ofile = 'Colormap.png'
       
        dlg = wx.FileDialog(self, message='Save Colormap as...',
                            defaultDir = os.getcwd(),
                            defaultFile=ofile,
                            wildcard=file_choices,
                            style=wx.SAVE|wx.CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.cmap_canvas.print_figure(path,dpi=300)
