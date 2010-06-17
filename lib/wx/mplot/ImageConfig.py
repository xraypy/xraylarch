import wx
import os
import numpy

import matplotlib.cm as colormap
from matplotlib.font_manager import FontProperties
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg

from LabelEntry import LabelEntry

ColorMap_List = ('gray', 'jet', 'hsv', 'Reds', 'Greens', 'Blues', 'hot',
                 'cool', 'copper', 'spring', 'summer', 'autumn', 'winter', 
                 'Spectral', 'Accent', 'Set1', 'Set2', 'Set3')

Interp_List = ('nearest', 'bilinear', 'bicubic', 'spline16', 'spline36',
               'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom',
               'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos')

class ImageConfig:
    def __init__(self, axes=None, fig=None, canvas=None):
        self.axes   = axes
        self.fig  = fig
        self.canvas  = canvas
        self.cmap  = colormap.gray
        self.cmap_reverse = False
        self.interp = 'nearest'
        self.title   = 'map'
        self.log_scale = False
        self.cmap_lo = 0
        self.cmap_hi = self.cmap_range = 100
        # self.zoombrush = wx.Brush('#141430',  wx.SOLID)
        self.zoombrush = wx.Brush('#040410',  wx.SOLID)
        self.zoompen   = wx.Pen('#101090',  3, wx.SOLID)

        f0 =  FontProperties()
        self.titlefont = f0.copy()
        self.titlefont.set_size(14)

    def relabel(self):
        " re draw labels (title, x,y labels)"
        self.axes.set_title(self.title,
                            fontproperties=self.titlefont)

    def set_zoombrush(self,color, style):
        self.zoombrush = wx.Brush(color, style)

    def set_zoompen(self,color, style):
        self.zoompen = wx.Pen(color, 3, style)

class ImageConfigFrame(wx.Frame):
    def __init__(self,conf=None,cmap=None,interp=None,**kw):
        self.conf   = conf
        self.cmap   = cmap or conf.cmap or colormap.jet
        self.interp = interp or conf.interp or 'bilinear'
        self.axes   = conf.axes
        self.canvas = conf.canvas
        self.DrawPanel()

    def DrawPanel(self):
        style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL 
        wx.Frame.__init__(self, None,-1, 'Configure Images', style=style)
        wx.Frame.SetBackgroundColour(self,"#F8F8F0")
        
        panel = wx.Panel(self, -1)
        panel.SetBackgroundColour( "#F8F8F0")

        Font = wx.Font(13,wx.SWISS,wx.NORMAL,wx.NORMAL,False)
        panel.SetFont(Font)

        sizer  = wx.GridBagSizer(6,6)
        labstyle= wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        label = wx.StaticText(panel, -1, 'ImagePanel Configuration',
                              style=labstyle)
        label.SetFont(Font)
        
        sizer.Add(label,(0,0),(1,5),  labstyle,2)

        self.wid_title = LabelEntry(panel, self.conf.title,
                                    size=400,
                                    labeltext='Title: ',
                                    action = self.onTitle)

        sizer.Add(self.wid_title.label, (1,0), (1,1), labstyle,5)
        sizer.Add(self.wid_title,        (1,1), (1,5), labstyle,5)
        #
        row = 2
        interp_choice =  wx.Choice(panel, -1, choices=Interp_List, size=(130,-1))
        interp_choice.Bind(wx.EVT_CHOICE,  self.onInterp)
        
        interp_choice.SetStringSelection(self.conf.interp)

        sizer.Add(wx.StaticText(panel,label='Smoothing'), (row,0), (1,1), labstyle,3)
        sizer.Add(interp_choice,   (row,1), (1,4), labstyle,3)        
        #
        row = row+1
        cmap_choice =  wx.Choice(panel, -1, choices=ColorMap_List, size=(130,-1))
        cmap_choice.Bind(wx.EVT_CHOICE,  self.onCMap)
        cmap_name = self.cmap.name
        if cmap_name.endswith('_r'): cmap_name = cmap_name[:-2]
        cmap_choice.SetStringSelection(cmap_name)

        cmap_toggle = wx.CheckBox(panel,-1, 'Reverse', (-1,-1),(-1,-1))
        cmap_toggle.Bind(wx.EVT_CHECKBOX,self.onCMapReverse)
        cmap_toggle.SetValue(self.conf.cmap_reverse)

        sizer.Add(wx.StaticText(panel,label='Color Map'), (row,0), (1,1), labstyle,3)
        sizer.Add(cmap_choice,   (row,1), (1,3), labstyle,3)
        sizer.Add(cmap_toggle,   (row,4), (1,2), labstyle,3)

        row = row+1
        cmax = self.conf.cmap_range
        self.cmap_data   = numpy.outer(numpy.ones(cmax/8),
                                       numpy.arange(0,cmax,1.0)/(1.0*cmax))
        self.cmap_fig     = Figure( (3.85, 0.5), dpi=96)
        self.cmap_axes  = self.cmap_fig.add_axes([0.01,0.01,0.98,0.98])
        self.cmap_axes.set_axis_off()
        self.cmap_canvas = FigureCanvasWxAgg(panel, -1, self.cmap_fig)
        self.cmap_fig.set_facecolor('#FBFBF8')
        self.cmap_image = self.cmap_axes.imshow(self.cmap_data,
                                                cmap=self.cmap, interpolation='bilinear')

        sizer.Add(self.cmap_canvas,   (row,1), (1,5), labstyle,3)

        self.cmap_lo_val = wx.Slider(panel, -1, self.conf.cmap_lo,0,self.conf.cmap_range,
                                     size=(375, -1), style=wx.SL_HORIZONTAL)
        self.cmap_hi_val = wx.Slider(panel, -1, self.conf.cmap_hi,0,self.conf.cmap_range,
                                     size=(375,-1), style=wx.SL_HORIZONTAL)

        self.cmap_lo_val.Bind(wx.EVT_SCROLL,  self.onStretchLow)
        self.cmap_hi_val.Bind(wx.EVT_SCROLL,  self.onStretchHigh)

        row = row+1
        sizer.Add(wx.StaticText(panel,label='Stretch Bottom'), (row,0), (1,1), labstyle,3)
        sizer.Add(self.cmap_lo_val, (row,1), (1,5), labstyle,3)

        row = row+1
        sizer.Add(wx.StaticText(panel,label='Stretch Top'), (row,0), (1,1), labstyle,3)
        sizer.Add(self.cmap_hi_val, (row,1), (1,5), labstyle,3)

        row = row+1
        cmap_save = wx.Button(panel, -1, 'Save Colormap Image')
        cmap_save.Bind(wx.EVT_BUTTON, self.onCMapSave)
        sizer.Add(cmap_save,   (row,0), (1,3), labstyle,3)        

        
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        a = wx.ALIGN_LEFT|wx.LEFT|wx.TOP|wx.BOTTOM|wx.EXPAND
        mainsizer.Add(sizer,0, a, 5)

        panel.SetAutoLayout(True)
        panel.SetSizer(mainsizer)
        mainsizer.Fit(panel)

        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(panel,   0, a, 5)
        self.SetAutoLayout(True)
        self.SetSizer(s)
        s.Fit(self)
        self.Show()
        self.Raise()

    def onCMapSave(self,event=None):
        file_choices = "PNG (*.png)|*.png"
        ofile = 'Colormap.png'
       
        dlg = wx.FileDialog(self, message='Save Plot Figure as...',
                            defaultDir = os.getcwd(),
                            defaultFile=ofile,
                            wildcard=file_choices,
                            style=wx.SAVE|wx.CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.cmap_canvas.print_figure(path,dpi=300)
        
    def onInterp(self,event=None):
        self.conf.interp =  event.GetString()
        self.conf.image.set_interpolation(self.conf.interp)
        self.canvas.draw()
        
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
        self.cmap_lo_val.SetValue(lo)
        self.cmap_hi_val.SetValue(hi)
        self.conf.cmap_lo = lo
        self.conf.cmap_hi = hi
        self.cmap_data[:,:lo] =0
        self.cmap_data[:,hi:] =1
        self.cmap_data[:,lo:hi] =  1.0*numpy.arange(hi-lo)/(hi-lo)
        self.cmap_image.set_data(self.cmap_data)
        self.cmap_canvas.draw()
        cmax = 1.0*self.conf.cmap_range
        img = cmax * self.conf.data/(1.0*self.conf.data.max())
        self.conf.image.set_data(numpy.clip((cmax*(img-lo)/(hi-lo+1.e-5)), 0, int(cmax-1))/cmax)
        self.canvas.draw()
        
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
        self.canvas.draw()
        self.cmap_canvas.draw()        

    def onTitle(self, event,argu=''):
        s = ''
        if (wx.EVT_TEXT_ENTER.evtType[0] == event.GetEventType()):
            s = str(event.GetString()).strip()        
        elif (wx.EVT_KILL_FOCUS.evtType[0] == event.GetEventType()):
            self.conf.title = self.wid_title.GetValue().strip()

        self.conf.relabel()
        self.canvas.draw()
