#!/usr/bin/env python
'''
   Plotting functions for Larch, wrapping the mplot plotting
   widgets which use matplotlib

Exposed functions here are
   plot:  display 2D line plot to an enhanced,
            configurable Plot Frame
   oplot: overplot a 2D line plot on an existing Plot Frame
   imshow: display a false-color map from array data on
           a configurable Image Display Frame.
'''

import time
import os
import sys
import wx

from wxmplot import PlotFrame, ImageFrame, StackedPlotFrame

import larch
from ..xrf import isLarchMCAGroup
from ..larchlib import ensuremod
from ..site_config import usr_larchdir

from .xrfdisplay import XRFDisplayFrame

mpl_dir = os.path.join(usr_larchdir, 'matplotlib')
os.environ['MPLCONFIGDIR'] = mpl_dir
if not os.path.exists(mpl_dir):
    try:
        os.makedirs(mpl_dir)
    except:
        pass

from matplotlib.axes import Axes
HIST_DOC = Axes.hist.__doc__

IMG_DISPLAYS = {}
PLOT_DISPLAYS = {}
FITPLOT_DISPLAYS = {}
XRF_DISPLAYS = {}

_larch_name = '_plotter'

__DOC__ = '''
General Plotting and Image Display Functions

The functions here include (but are not limited to):

function         description
------------     ------------------------------
plot             2D (x, y) plotting, with many, many options
plot_text        add text to a 2D plot
plot_marker      add a marker to a 2D plot
plot_arrow       add an arrow to a 2D plot

imshow           image display (false-color intensity image)

xrf_plot         browsable display for XRF spectra
'''

MAX_WINDOWS = 20
MAX_CURSHIST = 25

class XRFDisplay(XRFDisplayFrame):
    def __init__(self, wxparent=None, window=1, _larch=None,
                 size=(725, 425), **kws):
        XRFDisplayFrame.__init__(self, parent=wxparent, size=size,
                                 _larch=_larch,
                                 exit_callback=self.onExit, **kws)
        self.Show()
        self.Raise()
        self.panel.cursor_callback = self.onCursor
        self.window = int(window)
        self._larch = _larch
        self._xylims = {}
        self.symname = '%s.xrf%i' % (_larch_name, self.window)
        symtable = ensuremod(self._larch, _larch_name)

        if symtable is not None:
            symtable.set_symbol(self.symname, self)
        if window not in XRF_DISPLAYS:
            XRF_DISPLAYS[window] = self

    def onExit(self, o, **kw):
        try:
            symtable = self._larch.symtable
            if symtable.has_group(_larch_name):
                symtable.del_symbol(self.symname)
        except:
            pass
        if self.window in XRF_DISPLAYS:
            XRF_DISPLAYS.pop(self.window)

        self.Destroy()

    def onCursor(self, x=None, y=None, **kw):
        symtable = ensuremod(self._larch, _larch_name)
        if symtable is None:
            return
        symtable.set_symbol('%s_xrf_x'  % self.symname, x)
        symtable.set_symbol('%s_xrf_y'  % self.symname, y)

class PlotDisplay(PlotFrame):
    def __init__(self, wxparent=None, window=1, _larch=None, size=None, **kws):
        PlotFrame.__init__(self, parent=None, size=size,
                           output_title='plot2d',
                           exit_callback=self.onExit, **kws)

        self.Show()
        self.Raise()
        self.panel.cursor_callback = self.onCursor
        self.panel.cursor_mode = 'zoom'
        self.window = int(window)
        self._larch = _larch
        self._xylims = {}
        self.cursor_hist = []
        self.symname = '%s.plot%i' % (_larch_name, self.window)
        symtable = ensuremod(self._larch, _larch_name)
        self.panel.canvas.figure.set_facecolor('#FDFDFB')

        if symtable is not None:
            symtable.set_symbol(self.symname, self)
            if not hasattr(symtable, '%s.cursor_maxhistory' % _larch_name):
                symtable.set_symbol('%s.cursor_maxhistory' % _larch_name, MAX_CURSHIST)

        if window not in PLOT_DISPLAYS:
            PLOT_DISPLAYS[window] = self

    def onExit(self, o, **kw):
        try:
            symtable = self._larch.symtable
            if symtable.has_group(_larch_name):
                symtable.del_symbol(self.symname)
        except:
            pass
        if self.window in PLOT_DISPLAYS:
            PLOT_DISPLAYS.pop(self.window)

        self.Destroy()

    def onCursor(self, x=None, y=None, **kw):
        symtable = ensuremod(self._larch, _larch_name)
        if symtable is None:
            return
        hmax = getattr(symtable, '%s.cursor_maxhistory' % _larch_name, MAX_CURSHIST)
        symtable.set_symbol('%s_x'  % self.symname, x)
        symtable.set_symbol('%s_y'  % self.symname, y)
        self.cursor_hist.insert(0, (x, y, time.time()))
        if len(self.cursor_hist) > hmax:
            self.cursor_hist = self.cursor_hist[:hmax]
        symtable.set_symbol('%s_cursor_hist' % self.symname, self.cursor_hist)


class StackedPlotDisplay(StackedPlotFrame):
    def __init__(self, wxparent=None, window=1, _larch=None,  size=None, **kws):
        StackedPlotFrame.__init__(self, parent=None,
                                  exit_callback=self.onExit, **kws)

        self.Show()
        self.Raise()
        self.panel.cursor_callback = self.onCursor
        self.panel.cursor_mode = 'zoom'
        self.window = int(window)
        self._larch = _larch
        self._xylims = {}
        self.cursor_hist = []
        self.symname = '%s.fitplot%i' % (_larch_name, self.window)
        symtable = ensuremod(self._larch, _larch_name)
        self.panel.canvas.figure.set_facecolor('#FDFDFB')
        self.panel_bot.canvas.figure.set_facecolor('#FDFDFB')

        if symtable is not None:
            symtable.set_symbol(self.symname, self)
            if not hasattr(symtable, '%s.cursor_maxhistory' % _larch_name):
                symtable.set_symbol('%s.cursor_maxhistory' % _larch_name, MAX_CURSHIST)

        if window not in FITPLOT_DISPLAYS:
            FITPLOT_DISPLAYS[window] = self

    def onExit(self, o, **kw):
        try:
            symtable = self._larch.symtable
            if symtable.has_group(_larch_name):
                symtable.del_symbol(self.symname)
        except:
            pass
        if self.window in FITPLOT_DISPLAYS:
            FITPLOT_DISPLAYS.pop(self.window)

        self.Destroy()

    def onCursor(self, x=None, y=None, **kw):
        symtable = ensuremod(self._larch, _larch_name)
        if symtable is None:
            return
        hmax = getattr(symtable, '%s.cursor_maxhistory' % _larch_name, MAX_CURSHIST)
        symtable.set_symbol('%s_x'  % self.symname, x)
        symtable.set_symbol('%s_y'  % self.symname, y)
        self.cursor_hist.insert(0, (x, y, time.time()))
        if len(self.cursor_hist) > hmax:
            self.cursor_hist = self.cursor_hist[:hmax]
        symtable.set_symbol('%s_cursor_hist' % self.symname, self.cursor_hist)

class ImageDisplay(ImageFrame):
    def __init__(self, wxparent=None, window=1, _larch=None, size=None, **kws):
        ImageFrame.__init__(self, parent=None, size=size,
                                  exit_callback=self.onExit, **kws)
        self.Show()
        self.Raise()
        self.cursor_pos = []
        self.panel.cursor_callback = self.onCursor
        self.panel.contour_callback = self.onContour
        self.window = int(window)
        self.symname = '%s.img%i' % (_larch_name, self.window)
        self._larch = _larch
        symtable = ensuremod(self._larch, _larch_name)
        if symtable is not None:
            symtable.set_symbol(self.symname, self)
        if self.window not in IMG_DISPLAYS:
            IMG_DISPLAYS[self.window] = self

    def onContour(self, levels=None, **kws):
        symtable = ensuremod(self._larch, _larch_name)
        if symtable is not None and levels is not None:
            symtable.set_symbol('%s_contour_levels'  % self.symname, levels)

    def onExit(self, o, **kw):
        try:
            symtable = self._larch.symtable
            symtable.has_group(_larch_name), self.symname
            if symtable.has_group(_larch_name):
                symtable.del_symbol(self.symname)
        except:
            pass
        if self.window in IMG_DISPLAYS:
            IMG_DISPLAYS.pop(self.window)
        self.Destroy()

    def onCursor(self,x=None, y=None, ix=None, iy=None, val=None, **kw):
        symtable = ensuremod(self._larch, _larch_name)
        if symtable is None:
            return
        set = symtable.set_symbol
        if x is not None:   set('%s_x' % self.symname, x)
        if y is not None:   set('%s_y' % self.symname, y)
        if ix is not None:  set('%s_ix' % self.symname, ix)
        if iy is not None:  set('%s_iy' % self.symname, iy)
        if val is not None: set('%s_val' % self.symname, val)

def _getDisplay(win=1, _larch=None, wxparent=None, size=None,
                wintitle=None, xrf=False, image=False, stacked=False):
    """make a plotter"""
    # global PLOT_DISPLAYS, IMG_DISPlAYS
    if  hasattr(_larch, 'symtable'):
        if (getattr(_larch.symtable._sys.wx, 'wxapp', None) is None or
            getattr(_larch.symtable._plotter, 'no_plotting', False)):
            return None
    win = max(1, min(MAX_WINDOWS, int(abs(win))))
    title   = 'Plot Window %i' % win
    symname = '%s.plot%i' % (_larch_name, win)
    creator = PlotDisplay
    display_dict = PLOT_DISPLAYS
    if image:
        creator = ImageDisplay
        display_dict = IMG_DISPLAYS
        title   = 'Image Window %i' % win
        symname = '%s.img%i' % (_larch_name, win)
    elif xrf:
        creator = XRFDisplay
        display_dict = XRF_DISPLAYS
        title   = 'XRF Display Window %i' % win
        symname = '%s.xrf%i' % (_larch_name, win)
    elif stacked:
        creator = StackedPlotDisplay
        display_dict = FITPLOT_DISPLAYS
        title   = 'Fit Plot Window %i' % win
        symname = '%s.fitplot%i' % (_larch_name, win)

    if wintitle is not None:
        title = wintitle

    def _get_disp(symname, creator, win, ddict, wxparent, size, _larch):
        display = None
        if win in ddict:
            display = ddict[win]
            try:
                s = display.GetSize()
            except RuntimeError:  # window has been deleted
                ddict.pop(win)
                display = None

        if display is None and hasattr(_larch, 'symtable'):
            display = _larch.symtable.get_symbol(symname, create=True)
            if display is not None:
                try:
                    s = display.GetSize()
                except RuntimeError:  # window has been deleted
                    display = None
            
        if display is None:
            display = creator(window=win, wxparent=wxparent,
                              size=size, _larch=_larch)
        ddict[win] = display
        return display

    display = _get_disp(symname, creator, win, display_dict, wxparent,
                        size, _larch)
    try:
        display.SetTitle(title)
    except:
        display_dict.pop(win)
        display = _get_disp(symname, creator, win, display_dict, wxparent,
                            size, _larch)
        display.SetTitle(title) 
    if  hasattr(_larch, 'symtable'):
        _larch.symtable.set_symbol(symname, display)
    return display

def _xrf_plot(x=None, y=None, mca=None, win=1, new=True, as_mca2=False, _larch=None,
              wxparent=None, size=None, side='left', force_draw=True, wintitle=None,
              **kws):
    """xrf_plot(energy, data[, win=1], options])

    Show XRF trace of energy, data

    Parameters:
    --------------
        energy :  array of energies
        counts :  array of counts
        mca:      Group counting MCA data (rois, etc)
        as_mca2:  use mca as background MCA

        win: index of Plot Frame (0, 1, etc).  May create a new Plot Frame.
        new: flag (True/False, default False) for whether to start a new plot.
        color: color for trace (name such as 'red', or '#RRGGBB' hex string)
        style: trace linestyle (one of 'solid', 'dashed', 'dotted', 'dot-dash')
        linewidth:  integer width of line
        marker:  symbol to draw at each point ('+', 'o', 'x', 'square', etc)
        markersize: integer size of marker

    See Also: xrf_oplot, plot
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size,
                          _larch=_larch, wintitle=wintitle, xrf=True)
    if plotter is None:
        return
    plotter.Raise()
    if x is None:
        return

    if isLarchMCAGroup(x):
        mca = x
        y = x.counts
        x = x.energy

    if as_mca2:
        if isLarchMCAGroup(mca):
            plotter.add_mca(mca, as_mca2=True, plot=False)
            plotter.plotmca(mca, as_mca2=True, **kws)
        elif y is not None:
            plotter.oplot(x, y, mca=mca, as_mca2=True, **kws)
    elif new:
        if isLarchMCAGroup(mca):
            plotter.add_mca(mca, plot=False)
            plotter.plotmca(mca, **kws)
        elif y is not None:
            plotter.plot(x, y, mca=mca, **kws)
    elif y is not None:
        if isLarchMCAGroup(mca):
            plotter.add_mca(mca, plot=False)
        plotter.oplot(x, y, mca=mca, **kws)


def _xrf_oplot(x=None, y=None, mca=None, win=1, _larch=None, **kws):
    """xrf_oplot(energy, data[, win=1], options])

    Overplot a second  XRF trace of energy, data

    Parameters:
    --------------
        energy :  array of energies
        counts :  array of counts
        mca:      Group counting MCA data (rois, etc)

        win: index of Plot Frame (0, 1, etc).  May create a new Plot Frame.
        color: color for trace (name such as 'red', or '#RRGGBB' hex string)
        style: trace linestyle (one of 'solid', 'dashed', 'dotted', 'dot-dash')

    See Also: xrf_plot
    """
    _xrf_plot(x=x, y=y, mca=mca, win=win, _larch=_larch, new=False, **kws)

def _plot(x,y, win=1, new=False, _larch=None, wxparent=None, size=None,
          xrf=False, stacked=False, force_draw=True, side='left', wintitle=None, **kws):
    """plot(x, y[, win=1], options])

    Plot 2-D trace of x, y arrays in a Plot Frame, clearing any plot currently in the Plot Frame.

    Parameters:
    --------------
        x :  array of ordinate values
        y :  array of abscissa values (x and y must be same size!)

        win: index of Plot Frame (0, 1, etc).  May create a new Plot Frame.
        new: flag (True/False, default False) for whether to start a new plot.
        force_draw: flag (True/False, default Tree) for whether force a draw.
                    This will take a little extra time, and is not needed when
                    typing at the command-line, but is needed for plots to update
                    from inside scripts.
        label: label for trace
        title:  title for Plot
        xlabel: x-axis label
        ylabel: y-axis label
        ylog_scale: whether to show y-axis as log-scale (True or False)
        grid: whether to draw background grid (True or False)

        color: color for trace (name such as 'red', or '#RRGGBB' hex string)
        style: trace linestyle (one of 'solid', 'dashed', 'dotted', 'dot-dash')
        linewidth:  integer width of line
        marker:  symbol to draw at each point ('+', 'o', 'x', 'square', etc)
        markersize: integer size of marker

        drawstyle: style for joining line segments

        dy: array for error bars in y (must be same size as y!)
        yaxis='left'??
        use_dates

    See Also: oplot, newplot
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size,
                          xrf=xrf, stacked=stacked,
                          wintitle=wintitle,  _larch=_larch)
    if plotter is None:
        return
    plotter.Raise()
    if new:
        plotter.plot(x, y, side=side, **kws)
    else:
        plotter.oplot(x, y, side=side, **kws)
    if force_draw:
        wx_update(_larch=_larch)

def _redraw_plot(win=1, xrf=False, stacked=False, size=None, wintitle=None,
                 _larch=None, wxparent=None):
    """redraw_plot(win=1)

    redraw a plot window, especially convenient to force setting limits after
    multiple plot()s with delay_draw=True
    """

    plotter = _getDisplay(wxparent=wxparent, win=win, size=size,
                          xrf=xrf, stacked=stacked,
                          wintitle=wintitle,  _larch=_larch)
    plotter.panel.unzoom_all()


def _update_trace(x, y, trace=1, win=1, _larch=None, wxparent=None,
                 side='left', redraw=False, **kws):
    """update a plot trace with new data, avoiding complete redraw"""
    plotter = _getDisplay(wxparent=wxparent, win=win, _larch=_larch)
    if plotter is None:
        return
    plotter.Raise()
    trace -= 1 # wxmplot counts traces from 0

    plotter.panel.update_line(trace, x, y, draw=True, side=side)
    wx_update(_larch=_larch)

def wx_update(_larch=None, **kws):
    if  hasattr(_larch, 'symtable'):
        _larch.symtable.set_symbol('_sys.wx.force_wxupdate', True)
    try:
        _larch.symtable.get_symbol('_sys.wx.ping')(timeout=0.002)
    except:
        pass

def _plot_setlimits(xmin=None, xmax=None, ymin=None, ymax=None, win=1, wxparent=None,
                    _larch=None):
    """set plot view limits for plot in window `win`"""
    plotter = _getDisplay(wxparent=wxparent, win=win, _larch=_larch)
    if plotter is None:
        return
    plotter.panel.set_xylims((xmin, xmax, ymin, ymax))

def _oplot(x, y, win=1, _larch=None, wxparent=None, xrf=False, stacked=False,
           size=None, **kws):
    """oplot(x, y[, win=1[, options]])

    Plot 2-D trace of x, y arrays in a Plot Frame, over-plotting any
    plot currently in the Plot Frame.

    This is equivalent to
    plot(x, y[, win=1[, new=False[, options]]])

    See Also: plot, newplot
    """
    kws['new'] = False
    _plot(x, y, win=win, size=size, xrf=xrf, stacked=stacked,
          wxparent=wxparent, _larch=_larch, **kws)

def _newplot(x, y, win=1, _larch=None, wxparent=None,  size=None, wintitle=None,
             **kws):
    """newplot(x, y[, win=1[, options]])

    Plot 2-D trace of x, y arrays in a Plot Frame, clearing any
    plot currently in the Plot Frame.

    This is equivalent to
    plot(x, y[, win=1[, new=True[, options]]])

    See Also: plot, oplot
    """
    _plot(x, y, win=win, size=size, new=True, _larch=_larch,
          wxparent=wxparent, wintitle=wintitle, **kws)

def _plot_text(text, x, y, win=1, side='left', size=None,
               stacked=False, xrf=False, rotation=None, ha='left', va='center',
               _larch=None, wxparent=None,  **kws):
    """plot_text(text, x, y, win=1, options)

    add text at x, y coordinates of a plot

    Parameters:
    --------------
        text:  text to draw
        x:     x position of text
        y:     y position of text
        win:   index of Plot Frame (0, 1, etc).  May create a new Plot Frame.
        side:  which axis to use ('left' or 'right') for coordinates.
        rotation:  text rotation. angle in degrees or 'vertical' or 'horizontal'
        ha:    horizontal alignment ('left', 'center', 'right')
        va:    vertical alignment ('top', 'center', 'bottom', 'baseline')

    See Also: plot, oplot, plot_arrow
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, xrf=xrf,
                          stacked=stacked, _larch=_larch)
    if plotter is None:
        return
    plotter.Raise()

    plotter.add_text(text, x, y, side=side,
                     rotation=rotation, ha=ha, va=va, **kws)

def _plot_arrow(x1, y1, x2, y2, win=1, side='left',
                shape='full', color='black',
                width=0.00, head_width=0.05, head_length=0.25,
               _larch=None, wxparent=None, stacked=False, xrf=False,
                size=None, **kws):

    """plot_arrow(x1, y1, x2, y2, win=1, **kws)

    draw arrow from x1, y1 to x2, y2.

    Parameters:
    --------------
        x1: starting x coordinate
        y1: starting y coordinate
        x2: ending x coordinate
        y2: ending y coordinate
        side: which axis to use ('left' or 'right') for coordinates.
        shape:  arrow head shape ('full', 'left', 'right')
        color:  arrow color ('black')
        width:  width of arrow line (in points. default=0.0)
        head_width:  width of arrow head (in points. default=0.05)
        head_length:  length of arrow head (in points. default=0.25)
        overhang:    amount the arrow is swept back (in points. default=0)
        win:  window to draw too

    See Also: plot, oplot, plot_text
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, xrf=xrf,
                          stacked=stacked, _larch=_larch)
    if plotter is None:
        return
    plotter.Raise()
    plotter.add_arrow(x1, y1, x2, y2, side=side, shape=shape,
                      color=color, width=width, head_length=head_length,
                      head_width=head_width, **kws)

def _plot_marker(x, y, marker='o', size=4, color='black', label='_nolegend_',
               _larch=None, wxparent=None, win=1, xrf=False, stacked=False, **kws):

    """plot_marker(x, y, marker='o', size=4, color='black')

    draw a marker at x, y

    Parameters:
    -----------
        x:      x coordinate
        y:      y coordinate
        marker: symbol to draw at each point ('+', 'o', 'x', 'square', etc) ['o']
        size:   symbol size [4]
        color:  color  ['black']

    See Also: plot, oplot, plot_text
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=None, xrf=xrf,
                          stacked=stacked, _larch=_larch)
    if plotter is None:
        return
    plotter.Raise()
    plotter.oplot([x], [y], marker=marker, markersize=size, label=label,
                 color=color, _larch=_larch, wxparent=wxparent,  **kws)

def _plot_axhline(y, xmin=0, xmax=1, win=1, wxparent=None, xrf=False,
                  stacked=False, size=None, delay_draw=False, _larch=None, **kws):
    """plot_axhline(y, xmin=None, ymin=None, **kws)

    plot a horizontal line spanning the plot axes
    Parameters:
    --------------
        y:      y position of line
        xmin:   starting x fraction (window units -- not user units!)
        xmax:   ending x fraction (window units -- not user units!)
    See Also: plot, oplot, plot_arrow
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, xrf=xrf,
                          stacked=stacked, _larch=_larch)
    if plotter is None:
        return
    plotter.Raise()
    if 'label' not in kws:
        kws['label'] = '_nolegend_'
    plotter.panel.axes.axhline(y, xmin=xmin, xmax=xmax, **kws)
    if delay_draw:
        plotter.panel.canvas.draw()

def _plot_axvline(x, ymin=0, ymax=1, win=1, wxparent=None, xrf=False,
                  stacked=False, size=None, delay_draw=False, _larch=None, **kws):
    """plot_axvline(y, xmin=None, ymin=None, **kws)

    plot a vertical line spanning the plot axes
    Parameters:
    --------------
        x:      x position of line
        ymin:   starting y fraction (window units -- not user units!)
        ymax:   ending y fraction (window units -- not user units!)
    See Also: plot, oplot, plot_arrow
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, xrf=xrf,
                          stacked=stacked, _larch=_larch)
    if plotter is None:
        return
    plotter.Raise()
    if 'label' not in kws:
        kws['label'] = '_nolegend_'
    plotter.panel.axes.axvline(x, ymin=ymin, ymax=ymax, **kws)
    if not delay_draw:
        plotter.panel.canvas.draw()

def _getcursor(win=1, timeout=30, _larch=None, wxparent=None, size=None,
               xrf=False, stacked=False, **kws):
    """get_cursor(win=1, timeout=30)

    waits (up to timeout) for cursor click in selected plot window, and
    returns x, y position of cursor.  On timeout, returns the last known
    cursor position, or (None, None)

    Note that _plotter.plotWIN_x and _plotter.plotWIN_y will be updated,
    with each cursor click, and so can be used to read the last cursor
    position without blocking.

    For a more consistent programmatic approach, this routine can be called
    with timeout <= 0 to read the most recently clicked cursor position.
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, xrf=xrf,
                          stacked=stacked, _larch=_larch)
    if plotter is None:
        return
    symtable = ensuremod(_larch, _larch_name)
    sentinal = '%s.plot%i_cursorflag' % (_larch_name, win)
    xsym = '%s.plot%i_x' % (_larch_name, win)
    ysym = '%s.plot%i_y' % (_larch_name, win)

    xval = symtable.get_symbol(xsym, create=True)
    yval = symtable.get_symbol(ysym, create=True)
    symtable.set_symbol(sentinal, False)

    def onChange(symbolname=None, **kws):
        symtable.set_symbol(kws['sentinal'], True)

    symtable.add_callback(xsym, onChange, kws={'sentinal': sentinal})

    t0 = time.time()
    while time.time() - t0 < timeout:
        wx_update(_larch=_larch)
        if symtable.get_symbol(sentinal):
            break
    symtable.del_symbol(sentinal)
    symtable.clear_callbacks(xsym)
    return (symtable.get_symbol(xsym), symtable.get_symbol(ysym))

def last_cursor_pos(win=None, _larch=None):
    """return most recent cursor position -- 'last click on plot'

    By default, this returns the last postion for all plot windows.
    If win is not `None`, the last position for that window will be returned

    Arguments
    ---------
    win  (int or None) index of window to get cursor position [None, all windows]

    Returns
    -------
    x, y coordinates of most recent cursor click, in user units
    """
    if  hasattr(_larch, 'symtable'):
        plotter = _larch.symtable._plotter
    else:
        return None, None
    histories = []
    for attr in dir(plotter):
        if attr.endswith('_cursor_hist'):
            histories.append(attr)

    if win is not None:
        tmp = []
        for attr in histories:
            if attr.startswith('plot%d_' % win):
                tmp.append(attr)
        histories = tmp
    _x, _y, _t = None, None, 0
    for hist in histories:
        for px, py, pt in getattr(plotter, hist, [None, None, -1]):
            if pt > _t and px is not None:
                _x, _y, _t = px, py, pt
    return _x, _y


def _scatterplot(x,y, win=1, _larch=None, wxparent=None, size=None,
          force_draw=True,  **kws):
    """scatterplot(x, y[, win=1], options])

    Plot x, y values as a scatterplot.  Parameters are very similar to
    those of plot()

    See Also: plot, newplot
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch)
    if plotter is None:
        return
    plotter.Raise()
    plotter.scatterplot(x, y, **kws)
    if force_draw:
        wx_update(_larch=_larch)


def _fitplot(x, y, y2=None, panel='top', label=None, label2=None, win=1,
             _larch=None, wxparent=None, size=None, **kws):
    """fit_plot(x, y, y2=None, win=1, options)

    Plot x, y values in the top of a StackedPlot. If y2 is not None, then x, y2 values
    will also be plotted in the top frame, and the residual (y-y2) in the bottom panel.

    By default, arrays will be plotted in the top panel, and you must
    specify `panel='bot'` to plot an array in the bottom panel.

    Parameters are the same as for plot() and oplot()

    See Also: plot, newplot
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size,
                          stacked=True, _larch=_larch)
    if plotter is None:
        return
    plotter.Raise()
    plotter.plot(x, y, panel='top', label=label, **kws)
    if y2 is not None:
        kws.update({'label': label2})
        plotter.oplot(x, y2, panel='top', **kws)
        plotter.plot(x, y2-y, panel='bot')
        plotter.panel.conf.set_margins(top=0.15, bottom=0.01,
                                       left=0.15, right=0.05)
        plotter.panel_bot.conf.set_margins(top=0.01, bottom=0.35,
                                           left=0.15, right=0.05)


def _hist(x, bins=10, win=1, new=False,
           _larch=None, wxparent=None, size=None, force_draw=True,  *args, **kws):

    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch)
    if plotter is None:
        return
    plotter.Raise()
    if new:
        plotter.panel.axes.clear()

    out = plotter.panel.axes.hist(x, bins=bins, **kws)
    plotter.panel.canvas.draw()
    if force_draw:
        wx_update(_larch=_larch)
    return out


_hist.__doc__ = """
    hist(x, bins, win=1, options)

  %s
""" % (HIST_DOC)


def _imshow(map, x=None, y=None, colormap=None, win=1, _larch=None,
            wxparent=None, size=None, **kws):
    """imshow(map[, options])

    Display an 2-D array of intensities as a false-color map

    map: 2-dimensional array for map
    """
    img = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch, image=True)
    if img is not None:
        img.display(map, x=x, y=y, colormap=colormap, **kws)

def _contour(map, x=None, y=None, _larch=None, **kws):
    """contour(map[, options])

    Display an 2-D array of intensities as a contour plot

    map: 2-dimensional array for map
    """
    kws.update(dict(style='contour'))
    _imshow(map, x=x, y=y, _larch=_larch, **kws)

def _saveplot(fname, dpi=300, format=None, win=1, _larch=None, wxparent=None,
              size=None, facecolor='w', edgecolor='w', quality=90,
              image=False, **kws):
    """formats: png (default), svg, pdf, jpeg, tiff"""
    thisdir = os.path.abspath(os.curdir)
    if format is None:
        pref, suffix = os.path.splitext(fname)
        if suffix is not None:
            if suffix.startswith('.'):
                suffix = suffix[1:]
            format = suffix
    if format is None: format = 'png'
    format = format.lower()
    canvas = _getDisplay(wxparent=wxparent, win=win, size=size,
                         _larch=_larch, image=image).panel.canvas
    if canvas is None:
        return
    if format in ('jpeg', 'jpg'):
        canvas.print_jpeg(fname, quality=quality, **kws)
    elif format in ('tiff', 'tif'):
        canvas.print_tiff(fname, **kws)
    elif format in ('png', 'svg', 'pdf', 'emf', 'eps'):
        canvas.print_figure(fname, dpi=dpi, format=format,
                            facecolor=facecolor, edgecolor=edgecolor, **kws)
    else:
        print('unsupported image format: ', format)
    os.chdir(thisdir)

def _saveimg(fname, _larch=None, **kws):
    """save image from image display"""
    kws.update({'image':True})
    _saveplot(fname, _larch=_larch, **kws)

def _closeDisplays(_larch=None, **kws):
    for display in (PLOT_DISPLAYS, IMG_DISPLAYS,
                    FITPLOT_DISPLAYS, XRF_DISPLAYS):
        for win in display.values():
            win.Destroy()
