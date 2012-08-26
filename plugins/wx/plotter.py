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
import thread
import wx
import wx.lib.newevent

import larch
from wxmplot import PlotFrame, ImageFrame

mpl_dir = os.path.join(larch.site_config.usr_larchdir, 'matplotlib')
os.environ['MPLCONFIGDIR'] = mpl_dir
if not os.path.exists(mpl_dir):
    try:
        os.makedirs(mpl_dir)
    except:
        pass


here = os.path.join(larch.site_config.sys_larchdir, 'plugins', 'wx')
sys.path.insert(0, here)

# now we can reliably import other wx modules...
from gui_utils import ensuremod


IMG_DISPLAYS = {}
PLOT_DISPLAYS = {}
MODNAME = '_plotter'
MAX_WINDOWS = 16

class PlotDisplay(PlotFrame):
    def __init__(self, wxparent=None, window=1, _larch=None, **kws):
        PlotFrame.__init__(self, parent=wxparent,
                           output_title='plot2d',
                           exit_callback=self.onExit, **kws)
        self.Show()
        self.Raise()
        self.panel.cursor_callback = self.onCursor
        self.window = int(window)
        self._larch = _larch
        self._xylims = {}
        self.symname = '%s.plot%i' % (MODNAME, self.window)
        symtable = ensuremod(self._larch, MODNAME)

        if symtable is not None:
            symtable.set_symbol(self.symname, self)
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
        symtable.set_symbol('%s_x'  % self.symname, x)
        symtable.set_symbol('%s_y'  % self.symname, y)

class ImageDisplay(ImageFrame):
    def __init__(self, wxparent=None, window=1, _larch=None, **kws):
        ImageFrame.__init__(self, parent=wxparent,
                                  exit_callback=self.onExit, **kws)
        self.Show()
        self.Raise()
        self.cursor_pos = []
        self.panel.cursor_callback = self.onCursor
        self.window = int(window)
        self.symname = '%s.img%i' % (MODNAME, self.window)
        self._larch = _larch
        symtable = ensuremod(self._larch, MODNAME)
        if symtable is not None:
            symtable.set_symbol(self.symname, self)
        if self.window not in IMG_DISPLAYS:
            IMG_DISPLAYS[self.window] = self

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

    def onCursor(self,x=None, y=None, ix=None, iy=None,
                 val=None, **kw):
        symtable = ensuremod(self._larch, MODNAME)
        if symtable is None:
            return
        set = symtable.set_symbol
        if x is not None:   set('%s_x' % self.symname, x)
        if y is not None:   set('%s_y' % self.symname, y)
        if ix is not None:  set('%s_ix' % self.symname, ix)
        if iy is not None:  set('%s_iy' % self.symname, iy)
        if val is not None: set('%s_val' % self.symname, val)

def _getDisplay(win=1, _larch=None, wxparent=None, image=False):
    """make a plotter"""
    # global PLOT_DISPLAYS, IMG_DISPlAYS
    if _larch is None:
        #print("Could not find larch?")
        return
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
    if win in display_dict:
        display = display_dict[win]
    else:
        display = _larch.symtable.get_symbol(symname, create=True)
    if display is None:
        display = creator(window=win, wxparent=wxparent, _larch=_larch)
        _larch.symtable.set_symbol(symname, display)
    if display is not None:
        display.SetTitle(title)
    return display

def _plot(x,y, win=1, new=False, _larch=None, wxparent=None,
          force_draw=True, side='left', **kws):
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
        marker:  symbol to draw at eac point ('+', 'o', 'x', 'square', etc)
        markersize: integer size of marker

        drawstyle: style for joining line segments

        dy: array for error bars in y (must be same size as y!)
        yaxis='left'??
        use_dates

    See Also: oplot, newplot
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(msg='No Plotter defined')
    plotter.Raise()
    if new:
        plotter.plot(x, y, side=side, **kws)
    else:
        plotter.oplot(x, y, side=side, **kws)
    if force_draw:
        update(_larch=_larch)


def _update_trace(x, y, trace=1, win=1, _larch=None, wxparent=None,
                 side='left', redraw=False, **kws):
    """update a plot trace with new data, avoiding complete redraw"""
    plotter = _getDisplay(wxparent=wxparent, win=win, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(msg='No Plotter defined')
    plotter.Raise()
    trace -= 1 # wxmplot counts traces from 0

    plotter.panel.update_line(trace, x, y, draw=True, side=side)
    update(_larch)

def update(_larch=None, **kws):
    _larch.symtable.set_symbol('_sys.wx.force_wxupdate', True)
    try:
        _larch.symtable.get_symbol('_sys.wx.ping')(timeout=0.002)
    except:
        pass


def _oplot(x, y, win=1, _larch=None, wxparent=None, **kws):
    """oplot(x, y[, win=1[, options]])

    Plot 2-D trace of x, y arrays in a Plot Frame, over-plotting any
    plot currently in the Plot Frame.

    This is equivalent to
    plot(x, y[, win=1[, new=False[, options]]])

    See Also: plot, newplot
    """
    _plot(x, y, win=win, new=False, _larch=_larch, wxparent=wxparent, **kws)

def _newplot(x, y, win=1, _larch=None, wxparent=None, **kws):
    """newplot(x, y[, win=1[, options]])

    Plot 2-D trace of x, y arrays in a Plot Frame, clearing any
    plot currently in the Plot Frame.

    This is equivalent to
    plot(x, y[, win=1[, new=True[, options]]])

    See Also: plot, oplot
    """
    _plot(x, y, win=win, new=True, _larch=_larch, wxparent=wxparent, **kws)

def _plot_text(text, x, y, win=1, side='left',
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
    plotter = _getDisplay(wxparent=wxparent, win=win, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(msg='No Plotter defined')
    plotter.Raise()

    plotter.add_text(text, x, y, side=side,
                     rotation=rotation, ha=ha, va=va, **kws)

def _plot_arrow(x1, y1, x2, y2, win=1, side='left',
                shape='full', fg='black', wdith=0.01,
                head_width=0.1, overhang=0,
               _larch=None, wxparent=None,  **kws):

    """plot_arrow(x1, y1, x2, y2, win=1, options)

    draw arrow from x1, y1 to x2, y2.

    Parameters:
    --------------
        x1: starting x coordinate
        y1: starting y coordinate
        x2: endnig x coordinate
        y2: ending y coordinate
        side: which axis to use ('left' or 'right') for coordinates.
        shape:  arrow head shape ('full', 'left', 'right')
        fg:     arrow fill color ('black')
        width:  width of arrow line (in points. default=0.01)
        head_width:  width of arrow head (in points. default=0.1)
        overhang:    amount the arrow is swept back (in points. default=0)


    See Also: plot, oplot, plot_text
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(msg='No Plotter defined')
    plotter.Raise()

    plotter.add_text(text, x, y, side=side,
                     rotation=rotation, ha=ha, va=va, **kws)


def _getcursor(win=1, timeout=30, _larch=None, wxparent=None, **kws):
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
    plotter = _getDisplay(wxparent=wxparent, win=win, _larch=_larch)
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
        update(_larch)
        if symtable.get_symbol(sentinal):
            break
    symtable.del_symbol(sentinal)
    symtable.clear_callbacks(xsym)
    return (symtable.get_symbol(xsym), symtable.get_symbol(ysym))


def _scatterplot(x,y, win=1, _larch=None, wxparent=None,
          force_draw=True,  **kws):
    """scatterplot(x, y[, win=1], options])

    Plot x, y values as a scatterplot.  Parameters are very similar to
    those of plot()

    See Also: plot, newplot
    """
    plotter = _getDisplay(wxparent=wxparent, win=win, _larch=_larch)
    if plotter is None:
        _larch.raise_exception(msg='No Plotter defined')
    plotter.Raise()
    plotter.scatterplot(x, y, **kws)
    if force_draw:
        update(_larch=_larch)



def _imshow(map, x=None, y=None, colormap=None, win=1, _larch=None,
            wxparent=None, **kws):
    """imshow(map[, options])

    Display an image for a 2-D array, as a map

    map: 2-dimensional array for map
    """
    img = _getDisplay(wxparent=wxparent, win=win, _larch=_larch, image=True)
    if img is not None:
        img.display(map, x=x, y=y, colormap=colormap, **kws)

def _saveplot(fname, dpi=300, format=None, win=1, _larch=None, wxparent=None,
              facecolor='w', edgecolor='w', quality=75, image=False, **kws):
    """formats: png (default), svg, pdf, jpeg, tiff"""
    if format is None:
        pref, suffix = os.path.splitext(fname)
        if suffix is not None:
            if suffix.startswith('.'):
                suffix = suffix[1:]
            format = suffix
    if format is None: format = 'png'
    format = format.lower()
    canvas = _getDisplay(wxparent=wxparent, win=win,
                         _larch=_larch, image=image).panel.canvas

    if format in ('jpeg', 'jpg'):
        canvas.print_jpeg(fname, quality=quality, **kws)
    elif format in ('tiff', 'tif'):
        canvas.print_tiff(fname, **kws)
    elif format in ('png', 'svg', 'pdf', 'emf', 'eps'):
        canvas.print_figure(fname, dpi=dpi, format=format,
                            facecolor=facecolor, edgecolor=edgecolor, **kws)
    else:
        print 'unsupported image format: ', format

def _saveimg(fname, _larch=None, **kws):
    """save image from image display"""
    kws.update({'image':True})
    _saveplot(fname, _larch=_larch, **kws)

def registerLarchPlugin():
    return (MODNAME, {'plot':_plot,
                      'oplot':_oplot,
                      'newplot':_newplot,
                      'plot_text': _plot_text,
                      'plot_arrow': _plot_arrow,
                      'scatterplot': _scatterplot,
                      'update_trace': _update_trace,
                      'save_plot': _saveplot,
                      'save_image': _saveimg,
                      'get_display':_getDisplay,
                      'get_cursor': _getcursor,
                      'imshow':_imshow} )
