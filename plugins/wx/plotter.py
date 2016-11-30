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

if not hasattr(sys, 'frozen'):
    try:
        import wxversion
        wxversion.ensureMinimal('2.8')
    except:
        pass

import wx
import wx.lib.newevent

from wxmplot import PlotFrame, ImageFrame

import larch

from larch_plugins.wx.gui_utils import ensuremod
from larch_plugins.wx.xrfdisplay import XRFDisplayFrame
from larch_plugins.xrf import isLarchMCAGroup

mpl_dir = os.path.join(larch.site_config.usr_larchdir, 'matplotlib')
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
XRF_DISPLAYS = {}
MODNAME = '_plotter'

MODDOC = '''
General Plotting and Image Display Functions

The functions here include (but are not limited too):

function         descrption
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
        self.symname = '%s.xrf%i' % (MODNAME, self.window)
        symtable = ensuremod(self._larch, MODNAME)

        if symtable is not None:
            symtable.set_symbol(self.symname, self)
        if window not in XRF_DISPLAYS:
            XRF_DISPLAYS[window] = self

    def onExit(self, o, **kw):
        try:
            symtable = self._larch.symtable
            if symtable.has_group(MODNAME):
                symtable.del_symbol(self.symname)
        except:
            pass
        if self.window in XRF_DISPLAYS:
            XRF_DISPLAYS.pop(self.window)

        self.Destroy()

    def onCursor(self, x=None, y=None, **kw):
        symtable = ensuremod(self._larch, MODNAME)
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
        self.symname = '%s.plot%i' % (MODNAME, self.window)
        symtable = ensuremod(self._larch, MODNAME)

        if symtable is not None:
            symtable.set_symbol(self.symname, self)
            if not hasattr(symtable, '%s.cursor_maxhistory' % MODNAME):
                symtable.set_symbol('%s.cursor_maxhistory' % MODNAME, MAX_CURSHIST)

        if window not in PLOT_DISPLAYS:
            PLOT_DISPLAYS[window] = self

    def onExit(self, o, **kw):
        try:
            symtable = self._larch.symtable
            if symtable.has_group(MODNAME):
                symtable.del_symbol(self.symname)
        except:
            pass
        if self.window in PLOT_DISPLAYS:
            PLOT_DISPLAYS.pop(self.window)

        self.Destroy()

    def onCursor(self, x=None, y=None, **kw):
        symtable = ensuremod(self._larch, MODNAME)
        if symtable is None:
            return
        hmax = getattr(symtable, '%s.cursor_maxhistory' % MODNAME, MAX_CURSHIST)
        symtable.set_symbol('%s_x'  % self.symname, x)
        symtable.set_symbol('%s_y'  % self.symname, y)
        self.cursor_hist.insert(0, (x, y))
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
        self.symname = '%s.img%i' % (MODNAME, self.window)
        self._larch = _larch
        symtable = ensuremod(self._larch, MODNAME)
        if symtable is not None:
            symtable.set_symbol(self.symname, self)
        if self.window not in IMG_DISPLAYS:
            IMG_DISPLAYS[self.window] = self

    def onContour(self, levels=None, **kws):
        symtable = ensuremod(self._larch, MODNAME)
        if symtable is not None and levels is not None:
            symtable.set_symbol('%s_contour_levels'  % self.symname, levels)

    def onExit(self, o, **kw):
        try:
            symtable = self._larch.symtable
            symtable.has_group(MODNAME), self.symname
            if symtable.has_group(MODNAME):
                symtable.del_symbol(self.symname)
        except:
            pass
        if self.window in IMG_DISPLAYS:
            IMG_DISPLAYS.pop(self.window)
        self.Destroy()

    def onCursor(self,x=None, y=None, ix=None, iy=None, val=None, **kw):
        symtable = ensuremod(self._larch, MODNAME)
        if symtable is None:
            return
        set = symtable.set_symbol
        if x is not None:   set('%s_x' % self.symname, x)
        if y is not None:   set('%s_y' % self.symname, y)
        if ix is not None:  set('%s_ix' % self.symname, ix)
        if iy is not None:  set('%s_iy' % self.symname, iy)
        if val is not None: set('%s_val' % self.symname, val)

@larch.ValidateLarchPlugin
def _getDisplay(win=1, _larch=None, wxparent=None, size=None,
                wintitle=None, xrf=False, image=False):
    """make a plotter"""
    # global PLOT_DISPLAYS, IMG_DISPlAYS
    if getattr(_larch.symtable._sys.wx, 'wxapp', None) is None:
        return None
    win = max(1, min(MAX_WINDOWS, int(abs(win))))
    title   = 'Plot Window %i' % win
    symname = '%s.plot%i' % (MODNAME, win)
    creator = PlotDisplay
    display_dict = PLOT_DISPLAYS
    if image:
        creator = ImageDisplay
        display_dict = IMG_DISPLAYS
        title   = 'Image Window %i' % win
        symname = '%s.img%i' % (MODNAME, win)
    elif xrf:
        creator = XRFDisplay
        display_dict = XRF_DISPLAYS
        title   = 'XRF Display Window %i' % win
        symname = '%s.xrf%i' % (MODNAME, win)

    if win in display_dict:
        display = display_dict[win]
    else:
        display = _larch.symtable.get_symbol(symname, create=True)
    if display is None:
        display = creator(window=win, wxparent=wxparent, size=size, _larch=_larch)
        if wintitle is not None:
            title = wintitle
        display.SetTitle(title)

    _larch.symtable.set_symbol(symname, display)
    return display

@larch.ValidateLarchPlugin
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
        _larch.raise_exception(None, msg='No Plotter defined')
    plotter.Raise()
    if x is None:
        return
    if isLarchMCAGroup(x):
        mca = x
        y = x.counts
        x = x.energy

    if as_mca2:
        new = False
        if isLarchMCAGroup(mca):
            plotter.plotmca(mca, as_mca2=True, new=False, **kws)
        elif y is not None:
            plotter.oplot(x, y, mca=mca, as_mca2=True, **kws)
    elif new:
        if isLarchMCAGroup(mca):
            plotter.plotmca(mca, **kws)
        elif y is not None:
            plotter.plot(x, y, mca=mca, **kws)
    else:
        plotter.oplot(x, y, mca=mca, **kws)

@larch.ValidateLarchPlugin
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

@larch.ValidateLarchPlugin
def _plot(x,y, win=1, new=False, _larch=None, wxparent=None, size=None,
          force_draw=True, side='left', wintitle=None, **kws):
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
                          wintitle=wintitle,  _larch=_larch)
    if plotter is None:
        _larch.raise_exception(None, msg='No Plotter defined')
    plotter.Raise()
    if new:
        plotter.plot(x, y, side=side, **kws)
    else:
        plotter.oplot(x, y, side=side, **kws)
    if force_draw:
        wx_update(_larch=_larch)

@larch.ValidateLarchPlugin
def _update_trace(x, y, trace=1, win=1, _larch=None, wxparent=None,
                 side='left', redraw=False, **kws):
    """update a plot trace with new data, avoiding complete redraw"""
    plotter = _getDisplay(wxparent=wxparent, win=win, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(None, msg='No Plotter defined')
    plotter.Raise()
    trace -= 1 # wxmplot counts traces from 0

    plotter.panel.update_line(trace, x, y, draw=True, side=side)
    wx_update(_larch=_larch)

@larch.ValidateLarchPlugin
def wx_update(_larch=None, **kws):
    _larch.symtable.set_symbol('_sys.wx.force_wxupdate', True)
    try:
        _larch.symtable.get_symbol('_sys.wx.ping')(timeout=0.002)
    except:
        pass


@larch.ValidateLarchPlugin
def _oplot(x, y, win=1, _larch=None, wxparent=None,  size=None, **kws):
    """oplot(x, y[, win=1[, options]])

    Plot 2-D trace of x, y arrays in a Plot Frame, over-plotting any
    plot currently in the Plot Frame.

    This is equivalent to
    plot(x, y[, win=1[, new=False[, options]]])

    See Also: plot, newplot
    """
    _plot(x, y, win=win, size=size, new=False, _larch=_larch, wxparent=wxparent, **kws)



@larch.ValidateLarchPlugin
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

@larch.ValidateLarchPlugin
def _plot_text(text, x, y, win=1, side='left', size=None,
               rotation=None, ha='left', va='center',
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
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(None, msg='No Plotter defined')
    plotter.Raise()

    plotter.add_text(text, x, y, side=side,
                     rotation=rotation, ha=ha, va=va, **kws)

@larch.ValidateLarchPlugin
def _plot_arrow(x1, y1, x2, y2, win=1, side='left',
                shape='full', color='black',
                width=0.02, head_width=0.20,
               _larch=None, wxparent=None,  size=None, **kws):

    """plot_arrow(x1, y1, x2, y2, win=1, options)

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
        width:  width of arrow line (in points. default=0.02)
        head_width:  width of arrow head (in points. default=0.20)
        overhang:    amount the arrow is swept back (in points. default=0)
        win:  window to draw too

    See Also: plot, oplot, plot_text
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(None, msg='No Plotter defined')
    plotter.Raise()
    kwargs = {'length_includes_head': True}
    plotter.add_arrow(x1, y1, x2, y2, side=side, shape=shape,
                      color=color, width=width, head_width=head_width, **kws)

@larch.ValidateLarchPlugin
def _plot_marker(x, y, marker='o', size=4, color='black',
               _larch=None, wxparent=None,  win=1, **kws):

    """plot_marker(x, y, marker='o', size=4, color='black')

    draw a marker at x, y

    Parameters:
    --------------
        x:      x coordinate
        y:      y coordinate
        marker: symbol to draw at each point ('+', 'o', 'x', 'square', etc)
        size:   symbol size
        color:  color ('black')

    See Also: plot, oplot, plot_text
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=None, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(None, msg='No Plotter defined')
    plotter.Raise()
    kwds = {'label': 'marker'}
    kwds.update(kws)
    plotter.oplot([x], [y], marker=marker, markersize=size,
                 color=color, _larch=_larch, wxparent=wxparent,  **kwds)

@larch.ValidateLarchPlugin
def _plot_axhline(y, xmin=0, xmax=1, win=1, size=None,
                  wxparent=None, _larch=None, **kws):
    """plot_axhline(y, xmin=None, ymin=None, **kws)

    plot a horizontal line spanning the plot axes
    Parameters:
    --------------
        y:      y position of line
        xmin:   starting x fraction (window units -- not user units!)
        xmax:   ending x fraction (window units -- not user units!)
    See Also: plot, oplot, plot_arrow
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(None, msg='No Plotter defined')
    plotter.Raise()

    plotter.panel.axes.axhline(y, xmin=xmin, xmax=xmax, **kws)
    plotter.panel.canvas.draw()

@larch.ValidateLarchPlugin
def _plot_axvline(x, ymin=0, ymax=1, win=1, size=None,
                  wxparent=None, _larch=None, **kws):
    """plot_axvline(y, xmin=None, ymin=None, **kws)

    plot a vertical line spanning the plot axes
    Parameters:
    --------------
        x:      x position of line
        ymin:   starting y fraction (window units -- not user units!)
        ymax:   ending y fraction (window units -- not user units!)
    See Also: plot, oplot, plot_arrow
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(None, msg='No Plotter defined')
    plotter.Raise()

    plotter.panel.axes.axvline(x, ymin=ymin, ymax=ymax, **kws)
    plotter.panel.canvas.draw()

@larch.ValidateLarchPlugin
def _getcursor(win=1, timeout=30, _larch=None, wxparent=None, size=None, **kws):
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
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch)
    symtable = ensuremod(_larch, MODNAME)
    sentinal = '%s.plot%i_cursorflag' % (MODNAME, win)
    xsym = '%s.plot%i_x' % (MODNAME, win)
    ysym = '%s.plot%i_y' % (MODNAME, win)

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


@larch.ValidateLarchPlugin
def _scatterplot(x,y, win=1, _larch=None, wxparent=None, size=None,
          force_draw=True,  **kws):
    """scatterplot(x, y[, win=1], options])

    Plot x, y values as a scatterplot.  Parameters are very similar to
    those of plot()

    See Also: plot, newplot
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(None, msg='No Plotter defined')
    plotter.Raise()
    plotter.scatterplot(x, y, **kws)
    if force_draw:
        wx_update(_larch=_larch)

@larch.ValidateLarchPlugin
def _hist(x, bins=10, win=1, new=False,
           _larch=None, wxparent=None, size=None, force_draw=True,  *args, **kws):

    plotter = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(None, msg='No Plotter defined')
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


@larch.ValidateLarchPlugin
def _imshow(map, x=None, y=None, colormap=None, win=1, _larch=None,
            wxparent=None, size=None, **kws):
    """imshow(map[, options])

    Display an 2-D array of intensities as a false-color map

    map: 2-dimensional array for map
    """
    img = _getDisplay(wxparent=wxparent, win=win, size=size, _larch=_larch, image=True)
    if img is not None:
        img.display(map, x=x, y=y, colormap=colormap, **kws)

@larch.ValidateLarchPlugin
def _contour(map, x=None, y=None, **kws):
    """contour(map[, options])

    Display an 2-D array of intensities as a contour plot

    map: 2-dimensional array for map
    """
    kws.update(dict(style='contour'))
    _imshow(map, x=x, y=y, **kws)

@larch.ValidateLarchPlugin
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

@larch.ValidateLarchPlugin
def _saveimg(fname, _larch=None, **kws):
    """save image from image display"""
    kws.update({'image':True})
    _saveplot(fname, _larch=_larch, **kws)

@larch.ValidateLarchPlugin
def _closeDisplays(_larch=None, **kws):
    names = PLOT_DISPLAYS.keys()
    for name in names:
        win = PLOT_DISPLAYS.pop(name)
        win.Destroy()
    names = IMG_DISPLAYS.keys()
    for name in names:
        win = IMG_DISPLAYS.pop(name)
        win.Destroy()


def initializeLarchPlugin(_larch=None):
    """initialize plotter"""
    cmds = ['plot', 'oplot', 'newplot', 'imshow', 'contour']
    if _larch is not None:
        _larch.symtable._sys.valid_commands.extend(cmds)
        mod = getattr(_larch.symtable, MODNAME)
        mod.__doc__ = MODDOC

def registerLarchPlugin():
    return (MODNAME, {'plot':_plot,
                      'oplot':_oplot,
                      'newplot':_newplot,
                      'plot_text': _plot_text,
                      'plot_marker': _plot_marker,
                      'plot_arrow': _plot_arrow,
                      'plot_axvline':  _plot_axvline,
                      'plot_axhline':  _plot_axhline,
                      'scatterplot': _scatterplot,
                      'hist': _hist,
                      'update_trace': _update_trace,
                      'save_plot': _saveplot,
                      'save_image': _saveimg,
                      'get_display':_getDisplay,
                      'close_all_displays':_closeDisplays,
                      'get_cursor': _getcursor,
                      'imshow':_imshow,
                      'contour':_contour,
                      'xrf_plot': _xrf_plot,
                      'xrf_oplot': _xrf_oplot,
                      })
