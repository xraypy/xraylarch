#!/usr/bin/python
##
## MPlot PlotFrame: a wx.Frame for 2D line plotting, using matplotlib
##

from plotpanel import PlotPanel
from baseframe import BaseFrame

class PlotFrame(BaseFrame):
    """
    MatPlotlib 2D plot as a wx.Frame, using PlotPanel
    """
    def __init__(self, parent=None, size=(700,450), exit_callback=None, **kwds):
        self.exit_callback = exit_callback
        self.title  = '2D Plot Frame'
        self.panel = PlotPanel(self, parent)
        BaseFrame.__init__(self,parent=parent, panel=self.panel, size=size)
        self.BuildFrame(size=size, **kwds)
        
    def plot(self,x,y,**kw):
        """plot after clearing current plot """        
        self.panel.plot(x,y,**kw)
        
    def oplot(self,x,y,**kw):
        """generic plotting method, overplotting any existing plot """
        self.panel.oplot(x,y,**kw)

    def update_line(self,t,x,y,**kw):
        """overwrite data for trace t """
        self.panel.update_line(t,x,y,**kw)
