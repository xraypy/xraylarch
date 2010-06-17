#!/usr/bin/python
"""
Plot Configuration of (simplified) properties for Matplotlib Lines.  In matplotlib,
a line is a series of x,y points, which are to be connected into a single trace.

Here, we'll call the thing drawn on the screen a 'trace', and the configuration
here is for trace properties:
    color        color of trace (a color name or hex code such as #FF00FF)
    style        trace style: one of ('solid', 'dashed', 'dotted', 'dash-dot')
    width        trace width
    marker       marker symbol for each point (see list below)
    markersize   size of marker
    markercolor  color for marker (defaults to same as trace color
    label        label used for trace


A matplotlib Line2D can have many more properties than this: these are not set here.

Valid marker names are:
   'no symbol', '+', 'o','x', '^','v','>','<','|','_',
   'square','diamond','thin diamond', 'hexagon','pentagon',
   'tripod 1','tripod 2'

"""

from matplotlib.font_manager import FontProperties
from matplotlib import rcParams
import colors

# use ordered dictionary to control order displayed in GUI dropdown lists
from odict import odict

StyleMap  = odict()
MarkerMap = odict()

for k,v in (('solid','-'), ('dashed','--'), ('dotted',':'), ('dash-dot','-.')):
    StyleMap[k]=v

for k,v in (('no symbol','None'), ('square','s'), ('+','+'),
            ('o','o'), ('x','x'), ('diamond','D'), ('thin diamond','d'),
            ('^','^'), ('v','v'), ('>','>'), ('<','<'), ('|','|'),('_','_'),
            ('hexagon','h'), ('pentagon','p'),
            ('tripod 1','1'), ('tripod 2','2')):
    MarkerMap[k] = v


class LineProperties:
    """ abstraction for Line2D properties, closely related to a
    MatPlotlib Line2D.  used to set internal line properties, and
    to  make the matplotlib calls to set the Line2D properties
    """

    def __init__(self,color='black',style='solid',linewidth=2,
                 marker='no symbol',markersize=6,markercolor=None,label=''):
        self.color      = color
        self.style      = style
        self.linewidth  = linewidth
        self.marker     = marker
        self.markersize = markersize
        self.markercolor= markercolor
        self.label      = label

    def update(self, line=None):
        """ set a matplotlib Line2D to have the current properties"""
        if line:
            markercolor = self.markercolor
            if markercolor is None: markercolor=self.color
            # self.set_markeredgecolor(markercolor, line=line)
            # self.set_markerfacecolor(markercolor, line=line)
            
            self.set_label(self.label, line=line)
            self.set_color(self.color, line=line)
            self.set_style(self.style, line=line)
            self.set_marker(self.marker,line=line)
            self.set_markersize(self.markersize, line=line)
            self.set_linewidth(self.linewidth, line=line)

    def set_color(self, color,line=None):
        self.color = color
        c = colors.hexcolor(color)
        def _setc(aline, col):
            aline.set_color(col)                    
            
        if line:
            for lx in line:
                if isinstance(lx, (list, tuple)):
                    for sublx in lx:
                        _setc(sublx, c)
                else:
                    _setc(lx, c)
                    
    def set_label(self, label,line=None):
        self.label = label
        if line:
            line[0].set_label(self.label)

    def set_style(self,style,line=None):
        sty = 'solid'
        if style in StyleMap:
            sty = style
        elif style in StyleMap.values():
            for k,v in StyleMap.items():
                if v == style:  sty = k
        self.style = sty
        if line:
            line[0].set_linestyle(StyleMap[sty])

    def set_marker(self,marker,line=None):
        sym = 'no symbol'
        if marker in MarkerMap:
            sym = marker
        elif marker in MarkerMap.values():
            for k,v in MarkerMap.items():
                if v == marker:  sym = k
        self.marker = sym
        if line:
            line[0].set_marker(MarkerMap[sym])
            
    def set_markersize(self,markersize,line=None):
        self.markersize=markersize
        if line:
            line[0].set_markersize(self.markersize/2.0)

    def set_linewidth(self,linewidth,line=None):
        self.linewidth=linewidth
        if line:
            for l in line:
                try:
                    l.set_linewidth(self.linewidth/2.0)
                except:
                    pass
                 
class PlotConfig:
    """ MPlot Configuration for 2D Plots... holder class for most configuration data """
    def __init__(self):
        self.axes   = None
        self.canvas = None
        self.fig    = None
        self.zoom_x = 0
        self.zoom_y = 0
        self.zoom_init = (0,1)
        
        self.title  = ' '
        self.xlabel = ' '
        self.ylabel = ' '
        self.styles      = StyleMap.keys()
        self.symbols     = MarkerMap.keys()
        self.legend_locs = ['upper right' , 'upper left', 'upper center',
                            'lower right',  'lower left', 'lower center',
                            'center left',  'center right', 'right', 'center']
        self.legend_onaxis_choices =  ['on plot', 'off plot']

        self.legend_loc    =  'upper right'
        self.legend_onaxis =  'on plot'
        self.mpl_legend  = None
        self.show_grid   = True
        self.show_legend = False
        self.show_legend_frame = True

        f0 =  FontProperties()
        self.labelfont = f0.copy()
        self.titlefont = f0.copy()
        self.labelfont.set_size(12)
        self.titlefont.set_size(14)

        self.grid_color = '#E0E0E0'
        # preload some traces
        #                   color  style linewidth marker markersize
        self.ntrace = 0
        self.lines  = [None]*30
        self.traces = []
        self._init_trace(20,None, 'black'    ,'dotted',2,'o', 8)
        self._init_trace( 0,None, 'blue',     'solid', 2,None,8)
        self._init_trace( 1,None, 'red',      'solid', 2,None,8)
        self._init_trace( 2,None, 'black',    'solid', 2,None,8)
        self._init_trace( 3,None, 'magenta',  'solid', 2,None,8)
        self._init_trace( 4,None, 'darkgreen','solid', 2,None,8)
        self._init_trace( 5,None, 'maroon'   ,'solid', 2,None,8)
        self._init_trace( 6,None, 'blue',     'dashed',2,None,8)
        self._init_trace( 7,None, 'red',      'dashed',2,None,8)
        self._init_trace( 8,None, 'black',    'dashed',2,None,8)
        self._init_trace( 9,None, 'magenta',  'dashed',2,None,8)
        self._init_trace(10,None, 'darkgreen','dashed',2,None,8)
        self._init_trace(11,None, 'maroon'   ,'dashed',2,None,8)
        self._init_trace(12,None, 'blue',     'dotted',2,None,8)
        self._init_trace(13,None, 'red',      'dotted',2,None,8)
        self._init_trace(14,None, 'black',    'dotted',2,None,8)
        self._init_trace(15,None, 'magenta',  'dotted',2,None,8)
        self._init_trace(16,None, 'darkgreen','dotted',2,None,8)
        self._init_trace(17,None, 'maroon'   ,'dotted',2,None,8)
        self._init_trace(18,None, 'blue'     ,'solid',1,'+',8)
        self._init_trace(19,None, 'red'      ,'solid',1,'+',8)
        
    def _init_trace(self,n,label,color,style,
                  linewidth,marker,markersize):
        """ used for building set of traces"""
        while n >= len(self.traces): self.traces.append(LineProperties())
        line = self.traces[n]
        if label == None:label = "trace %i" % (n+1)
        line.label = label
        if color     != None: line.color = color
        if style     != None: line.style = style
        if linewidth != None: line.linewidth = linewidth
        if marker    != None: line.marker = marker
        if markersize!= None: line.markersize = markersize
        self.traces[n] = line


    def __mpline(self,trace):
        n = max(0,int(trace))
        while n >= len(self.traces): self.traces.append(LineProperties())
        try:
            return self.lines[n]        
        except:
            return None

    def relabel(self):
        " re draw labels (title, x,y labels)"
        n = self.labelfont.get_size()
        n = self.labelfont.get_size()
                
        self.axes.set_xlabel(self.xlabel,
                             fontproperties=self.labelfont)
        self.axes.set_ylabel(self.ylabel,
                             fontproperties=self.labelfont)
        self.axes.set_title(self.title,
                            fontproperties=self.titlefont)
        rcParams['xtick.labelsize']=  n-1
        rcParams['ytick.labelsize']=  n-1

    def refresh_trace(self,trace=None):
        if trace is None: trace = self.ntrace
        self.traces[trace].update(self.__mpline(trace))
        
    def set_trace_color(self,color,trace=None):
        if trace is None: trace = self.ntrace
        self.traces[trace].set_color(color,line=self.__mpline(trace))
        
    def set_trace_label(self,label,trace=None):
        if trace is None: trace = self.ntrace
        self.traces[trace].set_label(label,line=self.__mpline(trace))

    def set_trace_style(self,style,trace=None):
        if trace is None: trace = self.ntrace
        self.traces[trace].set_style(style,line=self.__mpline(trace))

    def set_trace_marker(self,marker,trace=None):
        if trace is None: trace = self.ntrace
        self.traces[trace].set_marker(marker,line=self.__mpline(trace))

    def set_trace_markersize(self,markersize,trace=None):
        if trace is None: trace = self.ntrace
        self.traces[trace].set_markersize(markersize,line=self.__mpline(trace))

    def set_trace_linewidth(self,linewidth,trace=None):
        if trace is None: trace = self.ntrace
        self.traces[trace].set_linewidth(linewidth,line=self.__mpline(trace))

    def get_mpl_line(self,trace=None):
        if trace is None: trace = self.ntrace        
        return self.__mpline(trace)[0]

