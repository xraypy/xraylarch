#!/usr/bin/python
##
## MPlot PlotPanel: a wx.Panel for 2D line plotting, using matplotlib
##

import sys
import time
import os
import wx
import matplotlib

from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.dates import AutoDateFormatter, AutoDateLocator

from PlotConfig import PlotConfig
from PlotConfigFrame import PlotConfigFrame

from basepanel import BasePanel

class PlotPanel(BasePanel):
    """
    MatPlotlib 2D plot as a wx.Panel, suitable for embedding
    in any wx.Frame.   This does provide a right-click popup
    menu for configuration, zooming, saving an image of the
    figure, and Ctrl-C for copy-image-to-clipboard.

    For more features, see PlotFrame, which embeds a PlotPanel
    and also provides, a Menu, StatusBar, and Printing support.
    """
    def __init__(self, parent, messenger=None,
                 size=(6.00,3.70), dpi=96, **kwds):

        BasePanel.__init__(self, parent,  messenger=messenger)

        matplotlib.rc('axes', axisbelow=True)
        matplotlib.rc('lines', linewidth=2)
        matplotlib.rc('xtick',  labelsize=11, color='k')
        matplotlib.rc('ytick',  labelsize=11, color='k')
        matplotlib.rc('grid',  linewidth=0.5, linestyle='-')

        self.conf = PlotConfig()

        self.win_config = None
        self.cursor_callback = None
        self.parent    = parent
        self.figsize = size
        self.dpi     = dpi

    def plot(self,xdata,ydata, label=None, dy=None,
             color=None,  style =None, linewidth=None,
             marker=None,   markersize=None,   drawstyle=None,
             use_dates=False, ylog_scale=False, grid=None,
             title=None,  xlabel=None, ylabel=None,  **kw):
        """
        plot (that is, create a newplot: clear, then oplot)
        """

        self.axes.cla()
        self.conf.ntrace  = 0
        self.data_range   = [min(xdata),max(xdata),
                             min(ydata),max(ydata)]
        if xlabel is not None:   self.set_xlabel(xlabel)
        if ylabel is not None:   self.set_ylabel(ylabel)            
        if title  is not None:   self.set_title(title)
        if use_dates !=None: self.use_dates  = use_dates
        if ylog_scale !=None: self.ylog_scale = ylog_scale

        if grid: self.conf.show_grid = grid
        
        return self.oplot(xdata,ydata,label=label,
                          color=color,style=style,
                          drawstyle=drawstyle,
                          linewidth=linewidth,dy=dy,
                          marker=marker, markersize=markersize,  **kw)
        
    def oplot(self,xdata,ydata, label=None,color=None,style=None,
              linewidth=None,marker=None,markersize=None,
              drawstyle=None, dy=None,
              autoscale=True, refresh=True, yaxis='left', **kw):
        """ basic plot method, overplotting any existing plot """
        # set y scale to log/linear
        yscale = 'linear'
        if (self.ylog_scale and min(ydata) > 0):  yscale = 'log'
        self.axes.set_yscale(yscale, basey=10)

        if dy is None:
            _lines = self.axes.plot(xdata,ydata,drawstyle=drawstyle)
        else:
            _lines = self.axes.errorbar(xdata,ydata,yerr=dy)
        
        self.data_range    = [min((self.data_range[0],min(xdata))),
                              max((self.data_range[1],max(xdata))),
                              min((self.data_range[2],min(ydata))),
                              max((self.data_range[3],max(ydata)))]

        cnf  = self.conf
        n    = cnf.ntrace
        
        if label == None:   label = 'trace %i' % (n+1)
        cnf.set_trace_label(label)
        cnf.lines[n] = _lines
        
        if color:            cnf.set_trace_color(color)
        if style:            cnf.set_trace_style(style)
        if marker:           cnf.set_trace_marker(marker)
        if linewidth!=None:  cnf.set_trace_linewidth(linewidth)        
        if markersize!=None: cnf.set_trace_markersize(markersize)
        
        self.axes.yaxis.set_major_formatter(FuncFormatter(self.yformatter))
        self.axes.xaxis.set_major_formatter(FuncFormatter(self.xformatter))            

        xa = self.axes.xaxis
        if refresh:
            cnf.refresh_trace(n)
            cnf.relabel()

        if autoscale:
            self.axes.autoscale_view()
            self.zoom_lims = [None]
        if self.conf.show_grid:
            # I'm sure there's a better way...
            for i in self.axes.get_xgridlines()+self.axes.get_ygridlines():
                i.set_color(self.conf.grid_color)
            self.axes.grid(True)
        
        self.canvas.draw()
        cnf.ntrace = cnf.ntrace + 1
        return _lines

    def set_xylims(self, xyrange,autoscale=True, scalex=True, scaley=True):
        """ update xy limits of a plot, as used with .update_line() """
        xmin,xmax,ymin,ymax = xyrange
        if autoscale:
            if scalex:
                xmin, xmax= self.data_range[0], self.data_range[1]
            if scaley:
                ymin, ymax= self.data_range[2], self.data_range[3]
            
        self.axes.set_xlim((xmin,xmax),emit=True)
        self.axes.set_ylim((ymin,ymax),emit=True)
        self.axes.update_datalim(((xmin,ymin),(xmax,ymax)))
        if autoscale:
            if scalex:
                self.axes.set_xbound(self.axes.xaxis.get_major_locator().view_limits(xmin,xmax))
            if scaley:
                self.axes.set_ybound(self.axes.yaxis.get_major_locator().view_limits(ymin,ymax))            
            
    def clear(self):
        """ clear plot """
        self.axes.cla()
        self.conf.ntrace = 0
        self.conf.xlabel = ''
        self.conf.ylabel = ''
        self.conf.title  = ''
  
    def unzoom_all(self,event=None):
        """ zoom out full data range """
        self.zoom_lims = [None]
        self.unzoom(event)
        
    def unzoom(self,event=None):
        """ zoom out 1 level, or to full data range """
        lims = None
        if len(self.zoom_lims) > 1:
            self.zoom_lims.pop()
            lims = self.zoom_lims[-1]

        if lims is None: # auto scale
            self.zoom_lims = [None]
            xmin,xmax,ymin,ymax = self.data_range
            self.axes.set_xlim((xmin,xmax),emit=True)
            self.axes.set_ylim((ymin,ymax),emit=True)
            self.axes.update_datalim(((xmin,ymin),(xmax,ymax)))
            self.axes.set_xbound(self.axes.xaxis.get_major_locator().view_limits(xmin,xmax))
            self.axes.set_ybound(self.axes.yaxis.get_major_locator().view_limits(ymin,ymax))            

        else:
            self.axes.set_xlim(lims[:2])
            self.axes.set_ylim(lims[2:])
        
        self.old_zoomdc = (None,(0,0),(0,0))
        txt = ''
        if len(self.zoom_lims)>1:
            txt = 'zoom level %i' % (len(self.zoom_lims))
        self.write_message(txt)
        self.canvas.draw()
        
    def set_ylabel(self,s):
        "set plot ylabel"
        self.conf.ylabel = s
        self.conf.relabel()

    def configure(self,event=None):
        try:
            self.win_config.Raise()
        except:
            self.win_config = PlotConfigFrame(self.conf)

    ####
    ## create GUI 
    ####
    def BuildPanel(self, **kwds):
        """ builds basic GUI panel and popup menu"""

        wx.Panel.__init__(self, self.parent, -1, **kwds)

        self.fig   = Figure(self.figsize,dpi=self.dpi)

        self.axes  = self.fig.add_axes([0.12,0.12,0.80,0.80],
                                       axisbg='#FFFFFA')

        self.canvas = FigureCanvas(self, -1, self.fig)
        self.printer.canvas = self.canvas

        self.set_bg()

        self.conf.axes  = self.axes
        self.conf.fig   = self.fig
        self.conf.canvas= self.canvas
        self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))

        # overwrite ScalarFormatter from ticker.py here:
        self.axes.yaxis.set_major_formatter(FuncFormatter(self.yformatter))
        self.axes.xaxis.set_major_formatter(FuncFormatter(self.xformatter))

        # This way of adding to sizer allows resizing
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 2, wx.LEFT|wx.TOP|wx.BOTTOM|wx.EXPAND,0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        self.Fit()

        # define zoom box properties
        self.conf.zoombrush = wx.Brush('#080830',  wx.SOLID)
        self.conf.zoompen   = wx.Pen('#707070', 2, wx.SOLID) # SOLID)

        self.addCanvasEvents()

    def update_line(self,trace,xdata,ydata):
        """ update a single trace, for faster redraw """
        x = self.conf.get_mpl_line(trace)
        x.set_data(xdata,ydata)
        self.data_range = [min(self.data_range[0],xdata.min()),
                           max(self.data_range[1],xdata.max()),
                           min(self.data_range[2],ydata.min()),
                           max(self.data_range[3],ydata.max())]

        # this defeats zooming, which gets ugly in this fast-mode anyway.
        self.cursor_mode = 'cursor'
        self.canvas.draw()

    ####
    ## GUI events
    ####
    def reportLeftDown(self,event=None):
        if event == None: return        
        fmt = "X,Y= %s, %s" % (self._xfmt, self._yfmt)
        self.write_message(fmt % (event.xdata,event.ydata), panel=0)
        if hasattr(self.cursor_callback , '__call__'):
            self.cursor_callback(x=event.xdata, y=event.ydata)
        
