#!/usr/bin/python
##
## MPlot PlotPanel: a wx.Panel for 2D line plotting, using matplotlib
##

import sys
import time
import os
import wx
import matplotlib
import matplotlib.cm as colormap
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg

from ImageConfig  import ImageConfig,   ImageConfigFrame
from basepanel import BasePanel

class ImagePanel(BasePanel):
    """
    MatPlotlib Image as a wx.Panel, suitable for embedding
    in any wx.Frame.   This does provide a right-click popup
    menu for configuration, zooming, saving an image of the
    figure, and Ctrl-C for copy-image-to-clipboard.

    For more features, see PlotFrame, which embeds a PlotPanel
    and also provides, a Menu, StatusBar, and Printing support.
    """

    def __init__(self, parent, messenger=None, show_config_popup=True,
                 size=(5.00,4.50), dpi=96, **kwds):

        matplotlib.rc('lines', linewidth=2)
        BasePanel.__init__(self, parent,
                           messenger=messenger,
                           show_config_popup=show_config_popup)

        self.conf = ImageConfig()
        self.win_config = None
        self.cursor_callback = None
        self.figsize = size
        self.dpi     = dpi

    def display(self,data,x=None,y=None,**kw):
        """
        display (that is, create a new image display on the current frame
        """
        self.axes.cla()
        self.conf.ntraces  = 0
        self.conf.data = data[:] # .transpose()
        d = self.conf.data * 1.0 / self.conf.data.max()
        self.data_range = [0,d.shape[0], 0, d.shape[1]]
        if x is not None: self.data_range[:1] = [min(x),max(x)]
        if y is not None: self.data_range[2:] = [min(y),max(y)]

        print 'Hello ', d.shape, self.data_range

        self.conf.image = self.axes.imshow(d,cmap=colormap.gray,
                                           interpolation='nearest', origin='lower')
        self.axes.set_axis_off()
        
    def set_xylims(self, xyrange,autoscale=True):
        """ update xy limits of a plot"""
        xmin,xmax,ymin,ymax = xyrange
        if autoscale:
            xmin,xmax,ymin,ymax = self.data_range
            
        if abs(xmax-xmin) < 1.90:
            xmin  = 0.5*(xmax+xmin) - 1
            xmax = 0.5*(xmax+xmin) + 1

        if abs(ymax-ymin) < 1.90:
            ymin =  0.5*(ymax+xmin) - 1
            ymax = 0.5*(ymax+xmin) + 1

        self.axes.set_xlim((xmin,xmax),emit=True)
        self.axes.set_ylim((ymin,ymax),emit=True)
        self.axes.update_datalim(((xmin,ymin),(xmax,ymax)))
        if autoscale:
            self.axes.set_xbound(self.axes.xaxis.get_major_locator().view_limits(xmin,xmax))
            self.axes.set_ybound(self.axes.yaxis.get_major_locator().view_limits(ymin,ymax))            

    def clear(self):
        """ clear plot """
        self.axes.cla()
        self.conf.title  = ''

    def unzoom_all(self,event=None):
        """ zoom out full data range """
        self.zoom_lims = [None]
        self.unzoom(event,set_bounds=False)
        

       
    def unzoom(self,event=None,set_bounds=True):
        """ zoom out 1 level, or to full data range """
        lims = None
        if len(self.zoom_lims) > 1:
            self.zoom_lims.pop()
            lims = self.zoom_lims[-1]
        print 'UNZOOM lims: ', lims, self.data_range
        print 'Current X ', self.axes.get_xlim() 
        print 'Current Y ', self.axes.get_ylim()       
        if lims is None: # auto scale
            self.zoom_lims = [None]
            ymin,ymax, xmin,xmax   = self.data_range
            self.axes.set_xlim((xmin,xmax),emit=True)
            self.axes.set_ylim((ymin,ymax),emit=True)
            if set_bounds:
                print 'Setting Bounds ' 
                self.axes.update_datalim(((xmin,ymin),(xmax,ymax)))
                self.axes.set_xbound(self.axes.xaxis.get_major_locator().view_limits(xmin,xmax))
                self.axes.set_ybound(self.axes.yaxis.get_major_locator().view_limits(ymin,ymax))            
        else:
            self.axes.set_ylim(lims[:2])
            self.axes.set_xlim(lims[2:])
        self.old_zoomdc = (None,(0,0),(0,0))
        txt = ''
        if len(self.zoom_lims)>1:
            txt = 'zoom level %i' % (len(self.zoom_lims))
        self.write_message(txt)
        self.canvas.draw()

    def configure(self,event=None):
        try:
            self.win_config.Raise()
        except:
            self.win_config = ImageConfigFrame(conf=self.conf)

    ####
    ## create GUI 
    ####
    def BuildPanel(self, **kwds):
        """ builds basic GUI panel and popup menu"""
        wx.Panel.__init__(self, self.parent, -1, **kwds)

        self.fig   = Figure(self.figsize,dpi=self.dpi)
        self.axes  = self.fig.add_axes([0.08,0.08,0.90,0.90],
                                       axisbg='#FEFEFE')
                                      
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.fig.set_facecolor('#FBFBF8')
        
        self.conf.axes  = self.axes
        self.conf.fig   = self.fig
        self.conf.canvas= self.canvas

        self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))

        # This way of adding to sizer allows resizing
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 2, wx.LEFT|wx.TOP|wx.BOTTOM|wx.EXPAND,0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        self.Fit()
        self.addCanvasEvents()

    ####
    ## GUI events, overriding BasePanel components
    ####
    def reportMotion(self,event=None):
        pass
    
    def reportLeftDown(self,event=None):
        if event == None: return        
        ix, iy = round(event.xdata), round(event.ydata)

        if (ix > -1 and ix < self.conf.data.shape[1] and
            iy > -1 and iy < self.conf.data.shape[0]):
            msg = "Pixel[%i, %i], Intensity=%.4g " %(ix,iy,
                                                     self.conf.data[iy,ix])
            self.write_message(msg, panel=0)
            if hasattr(self.cursor_callback , '__call__'):
                x, y = None, None
                val = self.conf.data[iy,ix]
                self.cursor_callback(ix=ix, iy=iy, val=val)
                

    def zoom_OK(self, start,stop):
        """ returns whether a requested zoom is acceptable: rejects zooms that are too small"""
        print 'zoom ok ', start, stop, self.data_range
        xmax = self.data_range[1]
        ymax = self.data_range[3]
        return  ((start[0] > 0    or stop[0] > 0) and
                 (start[1] > 0    or stop[1] > 0) and
                 (start[0] < xmax or stop[0] < xmax) and
                 (start[1] < ymax or stop[1] < ymax) and
                 (abs(start[0] - stop[0]) > 1.25) and
                 (abs(start[1] - stop[1]) > 1.25))
