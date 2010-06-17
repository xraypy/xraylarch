#/usr/bin/python
# Name:      MPlot.py
# Purpose:   Provide user-configurable 2D plotting module, using wxPython
#            and matplotlib.
# Author:    Matthew Newville
# Copyright: Matthew Newville, The University of Chicago, 2004
# Licence:   Python license
# Created:   12/09/2004
#-----------------------------------------------------------------------------

"""
MPlot:  Plotting Tools based on matplotlib and wxPython.

Principle objects: 

    PlotPanel:   2D Plotting Panel
    PlotFrame  wx.Frame containing PlotPanel

    ImagePanel:    Image display Panel
    ImageFrame   wx.Frame containing ImagePanel


  PlotPanel is a wxPython plotting component, that can be included in
     other applications to provide a simple way to plot 2D data.
     PlotPanel provides capabilities for the user to:
     1. show X,Y coordinates (left-click)
     2. zoom in on a particular region of the plot (left-drag)
     3. customize titles, labels, legend, color, linestyle, marker,
        and whether a grid is shown.  A separate window is used to
        set these attributes.
     4. save plot images as PNGs, copy to system clipboard, or print.

  PlotPanel is a wxPython Panel, and can be included as such into other
  wx components.
  
  PlotFrame is a wxPython Frame (that is, a toplevel GUI window) that
  contains PlotPanel, dropdown menus from Save, Configure, Help, and so on,
  and a statusbar for messages and display of X,Y coordinates.

MPlot.PlotPanel and PlotFrame plot data in 1D Numeric (or numarray) arrays,
and provides these basic methods:
   plot(x,y):  start a new plot, and plot data x,y
      optional arguments (all keyword/value types):
          color='Blue'    for any X11 color name, (rgb) tuple, or '#RRGGBB'
          style='solid'   'solid,'dashed','dotted','dot-dash'
          linewidth=2     integer 0 (no line) to 10
          marker='None'   any of a wide range of marker symbols
          markersize=6    integer 0 to 30
          xlabel=' '      label for X Axis (MPlot text)    
          ylabel=' '      label for Y Axis (MPlot text)    
          title=' '       title for top of PlotFrame (MPlot text)    
          grid=True       boolean for whether to show grid.

   oplot(x,y):  plot data x,y, on same plot as current data
      optional arguments (all keyword/value types):
          color='Blue'    for any X11 color name, (rgb) tuple, or '#RRGGBB'
          style='solid'   'solid,'dashed','dotted','dot-dash'
          linewidth=2     integer 0 (no line) to 10
          marker='None'   any of a wide range of marker symbols
          markersize=6    integer 0 to 30

   clear():  clear plot
   save_figure():  bring up file dialog for saving image of figure
    
"""

__version__  = '0.9.1'
__date__     = '10-May-2010'

from .plotframe import PlotFrame
from .plotpanel import PlotPanel
from .imagepanel import ImagePanel
from .imageframe import ImageFrame
from .multiframe import MultiPlotFrame
from .plotapp  import PlotApp

