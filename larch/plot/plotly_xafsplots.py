#!/usr/bin/env python
"""
Plotting macros for XAFS data sets and fits

 Function          Description of what is plotted
 ---------------- -----------------------------------------------------
  plot_mu()        mu(E) for XAFS data group in various forms
  plot_bkg()       mu(E) and background mu0(E) for XAFS data group
  plot_chik()      chi(k) for XAFS data group
  plot_chie()      chi(E) for XAFS data group
  plot_chir()      chi(R) for XAFS data group
  plot_chifit()    chi(k) and chi(R) for fit to feffit dataset
  plot_path_k()    chi(k) for a single path of a feffit dataset
  plot_path_r()    chi(R) for a single path of a feffit dataset
  plot_paths_k()   chi(k) for model and all paths of a feffit dataset
  plot_paths_r()   chi(R) for model and all paths of a feffit dataset
  plot_diffkk()    plots from DIFFKK
 ---------------- -----------------------------------------------------
"""

import os
import numpy as np
import time
import logging
from copy import deepcopy

from larch import Group
from larch.math import index_of
from larch.xafs import cauchy_wavelet, etok

def nullfunc(*args, **kws):
    pass

get_display = _plot = _oplot = _newplot = _fitplot = _plot_text = nullfunc

HAS_PLOTLY = True
try:
    import plotly
except ImportError:
    HAS_PLOTLY = False

if HAS_PLOTLY:
    import plotly.graph_objs as pgo
    from  plotly.subplots import make_subplots

LineColors = ('#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd',
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf')
LineStyles = ('solid', 'dashed', 'dotted')
NCOLORS = len(LineColors)
NSTYLES = len(LineStyles)

FIGSTYLE = dict(width=650, height=500,
                showlegend=True, hovermode='closest',
                legend=dict(borderwidth=0.5, bgcolor='#F2F2F2'),
                 # orientation='v') #, x=0.1, y=1.15)# , yanchor='top'),
                plot_bgcolor='#FDFDFF',
                xaxis=dict(showgrid=True, gridcolor='#D8D8D8',
                           color='#004', zerolinecolor='#DDD'),
                yaxis=dict(showgrid=True, gridcolor='#D8D8D8',
                           color='#004', zerolinecolor='#DDD')
                )

def set_label_weight(label, w):
    return label.replace('_w_', '{0:g}'.format(w))

# common XAFS plot labels
def chirlab(kweight, show_mag=True, show_real=False, show_imag=False):
    """generate chi(R) label for a kweight

    Arguments
    ----------
     kweight      k-weight to use (required)
     show_mag     bool whether to plot |chi(R)| [True]
     show_real    bool whether to plot Re[chi(R)] [False]
     show_imag    bool whether to plot Im[chi(R)] [False]
    """
    ylab = []
    if show_mag:  ylab.append(plotlabels.chirmag)
    if show_real: ylab.append(plotlabels.chirre)
    if show_imag: ylab.append(plotlabels.chirim)
    if len(ylab) > 1:  ylab = [plotlabels.chir]
    return set_label_weight(ylab[0], kweight+1)
#enddef

# note:
#  to make life easier for MathJax/Plotly/IPython
#  we have just replaced "\AA" with "\unicode{x212B}"
plotlabels = Group(k       = r'$k \rm\,(\unicode{x212B}^{-1})$',
                   r       = r'$R \rm\,(\unicode{x212B})$',
                   energy  = r'$E\rm\,(eV)$',
                   ewithk  = r'$E\rm\,(eV)$' + '\n' + r'$[k \rm\,(\unicode{x212B}^{-1})]$',
                   mu      = r'$\mu(E)$',
                   norm    = r'normalized $\mu(E)$',
                   flat    = r'flattened $\mu(E)$',
                   deconv  = r'deconvolved $\mu(E)$',
                   dmude   = r'$d\mu_{\rm norm}(E)/dE$',
                   d2mude  = r'$d^2\mu_{\rm norm}(E)/dE^2$',
                   chie    = r'$\chi(E)$',
                   chie0   = r'$\chi(E)$',
                   chie1   = r'$E\chi(E) \rm\, (eV)$',
                   chiew   = r'$E^{{_w_}\chi(E) \rm\,(eV^{_w_})$',
                   chikw   = r'$k^{{_w_}}\chi(k) \rm\,(\unicode{x212B}^{{-_w_}})$',
                   chi0    = r'$\chi(k)$',
                   chi1    = r'$k\chi(k) \rm\,(\unicode{x212B}^{-1})$',
                   chi2    = r'$k^2\chi(k) \rm\,(\unicode{x212B}^{-2})$',
                   chi3    = r'$k^3\chi(k) \rm\,(\unicode{x212B}^{-3})$',
                   chir    = r'$\chi(R) \rm\,(\unicode{x212B}^{{-_w_}})$',
                   chirmag = r'$|\chi(R)| \rm\,(\unicode{x212B}^{{-_w_}})$',
                   chirre  = r'${{\rm Re}}[\chi(R)] \rm\,(\unicode{x212B}^{{-_w_}})$',
                   chirim  = r'${{\rm Im}}[\chi(R)] \rm\,(\unicode{x212B}^{{-_w_}})$',
                   chirpha = r'${{\rm Phase}}[\chi(R)] \rm\,(\unicode{x212B}^{{-_w_}})$',
                   e0color = '#B2B282',
                   chirlab = chirlab)


def safetitle(t):
    if "'" in t:
        t = t.replace("'", "\\'")
    return t

def _get_title(dgroup, title=None):
    """get best title for group"""
    if title is not None:
        return safetitle(title)
    data_group = getattr(dgroup, 'data', None)

    for attr in ('title', 'plot_title', 'filename', 'name', '__name__'):
        t = getattr(dgroup, attr, None)
        if t is not None:
            if attr == 'filename':
                folder, file = os.path.split(t)
                if folder == '':
                    t = file
                else:
                    top, folder = os.path.split(folder)
                    t = '/'.join((folder, file))
            return safetitle(t)
        if data_group is not None:
            t = getattr(data_group, attr, None)
            if t is not None:
                return t
    return safetitle(repr(dgroup))


def _get_kweight(dgroup, kweight=None):
    if kweight is not None:
        return kweight
    callargs = getattr(dgroup, 'callargs', None)
    ftargs = getattr(callargs, 'xftf', {'kweight':0})
    return ftargs['kweight']

def _get_erange(dgroup, emin=None, emax=None):
    """get absolute emin/emax for data range, allowing using
    values relative to e0.
    """
    dat_emin, dat_emax = min(dgroup.energy)-100, max(dgroup.energy)+100
    e0 = getattr(dgroup, 'e0', 0.0)
    if emin is not None:
        if not (emin > dat_emin and emin < dat_emax):
            if emin+e0 > dat_emin and emin+e0 < dat_emax:
                emin += e0
    else:
        emin = dat_emin
    if emax is not None:
        if not (emax > dat_emin and emax < dat_emax):
            if emax+e0 > dat_emin and emax+e0 < dat_emax:
                emax += e0
    else:
        emax = dat_emax
    return emin, emax

def extend_plotrange(x, y, xmin=None, xmax=None, extend=0.10):
    """return plot limits to extend a plot range for x, y pairs"""
    xeps = min(np.diff(x)) / 5.
    if xmin is None:
        xmin = min(x)
    if xmax is None:
        xmax = max(x)

    xmin = max(min(x), xmin-5)
    xmax = min(max(x), xmax+5)

    i0 = index_of(x, xmin + xeps)
    i1 = index_of(x, xmax + xeps) + 1

    xspan = x[i0:i1]
    xrange = max(xspan) - min(xspan)
    yspan = y[i0:i1]
    yrange = max(yspan) - min(yspan)

    return  (min(xspan) - extend * xrange,
             max(xspan) + extend * xrange,
             min(yspan) - extend * yrange,
             max(yspan) + extend * yrange)


def redraw(win=1, xmin=None, xmax=None, ymin=None, ymax=None,
           dymin=None, dymax=None,
           show_legend=True, stacked=False):
    pass


class PlotlyFigure:
    """wrapping of Plotly Figure
    """
    def __init__(self, two_yaxis=False, style=None):
        self.two_yaxis = two_yaxis
        self.style = deepcopy(FIGSTYLE)
        if style is not None:
            self.style.update(style)
        if self.two_yaxis:
            self.fig = make_subplots(specs=[[{"secondary_y": True}]])
        else:
            self.fig = pgo.FigureWidget()

        self.traces = []

    def clear(self):
        self.traces = []

    def add_plot(self, x, y, label=None, color=None, linewidth=3,
                 style='solid', marker=None, side='left'):
        itrace = len(self.traces)

        if label is None:
            label = "trace %d" % (1+itrace)
        if color is None:
            color = LineColors[itrace % NCOLORS]
        if style is None:
            style = LineStyles[ int(itrace*1.0 / NCOLORS) % NSTYLES]

        trace_opts = {}
        if self.two_yaxis:
            trace_opts['secondary_y'] = (side.lower().startswith('r'))

        lineopts = dict(color=color, width=linewidth)
        trace = pgo.Scatter(x=x, y=y, name=label, line=lineopts)

        self.traces.append(trace)

        self.fig.add_trace(trace, **trace_opts)

    def add_vline(self, *args, **kws):
        self.fig.add_vline(*args, **kws)

    def set_xrange(self, xmin, xmax):
        self.fig.update_xaxes(range=[xmin, xmax])

    def set_yrange(self, ymin, ymax):
        self.fig.update_yaxes(range=[ymin, ymax])

    def set_ylog(self, ylog=True):
        ytype = 'log' if ylog else 'linear'
        self.fig.update_yaxes(type=ytype)

    def set_style(self, **kws):
        self.style.update(**kws)
        self.fig.update_layout(**self.style)

    def show(self, title=None, xlabel=None, ylabel=None,
            xmin=None, xmax=None, ymin=None, ymax=None, show=True):
        self.set_style(title=title, xaxis_title=xlabel, yaxis_title=ylabel)
        if xmin is not None or xmax is not None:
            self.set_xrange(xmin, xmax)
        if ymin is not None or ymax is not None:
            self.set_yrange(ymin, ymax)
        if show:
            self.fig.show()
        return self

def plot(xdata, ydata, dy=None, fig=None, label=None, xlabel=None,
         ylabel=None, y2label=None, title=None, side='left', ylog_scale=None,
         xlog_scale=None, grid=None, xmin=None, xmax=None, ymin=None,
         ymax=None, color=None, style='solid', alpha=None, fill=False,
         drawstyle=None, linewidth=2, marker=None, markersize=None,
         show_legend=None, bgcolor=None, framecolor=None, gridcolor=None,
         textcolor=None, labelfontsize=None, titlefontsize=None,
         legendfontsize=None, fullbox=None, axes_style=None, zorder=None, show=True):
    """emulate wxmplot plot() function, probably incompletely"""

    if fig is None:
        fig = PlotlyFigure(two_yaxis=(side=='right'))

    fig.add_plot(xdata, ydata, label=label, color=color, linewidth=linewidth,
                 style=style, marker=marker, side=side)

    return fig.show(title=title, xlabel=xlabel, ylabel=ylabel,
                    xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, show=show)


def multi_plot(plotsets):
    """plot multiple traces with an array of dictionaries emulating
    multiplot calls to plot:

    instead of

    >>>  plot(x1, y1, label='thing1', color='blue')
    >>>  plot(x2, y2, label='thing2', color='red')

    you can do

    >>> multi_plot([dict(xdata=x1, ydata=y1, label='thing1', color='blue'),
                    dict(xdata=x2, ydata=y2, label='thing2', color='red')])

    """
    two_axis = False
    for pset in plotsets[:]:
        side = pset.get('side', None)
        if side == 'right':
            two_axis = True


    fig = PlotlyFigure(two_yaxis=two_axis)
    fig.clear()

    sopts = dict(title=None, xlabel=None, ylabel=None)
    ropts = dict(xmin=None, xmax=None, ymin=None, ymax=None)

    for pset in plotsets[:]:
        xdata = pset['xdata']
        ydata = pset['ydata']
        popts = dict(label=None, color=None, side='left', style=None,
                    linewidth=3, marker=None)
        for w in ('label', 'color', 'style', 'linewidth', 'marker', 'side'):
            if w in pset:
                popts[w] = pset[w]
        for w in ('title', 'xlabel', 'ylabel'):
            if w in pset:
                sopts[w] = pset[w]

        for w in ('xmin', 'xmax', 'ymin', 'ymax'):
            if w in pset:
                ropts[w] = pset[w]

        fig.add_plot(xdata, ydata, **popts)

    sopts['xaxis_title'] = sopts.pop('xlabel')
    sopts['yaxis_title'] = sopts.pop('ylabel')
    fig.style.update(sopts)
    return fig.show(**ropts)

def plot_mu(dgroup, show_norm=False, show_flat=False, show_deriv=False,
            show_pre=False, show_post=False, show_e0=False, with_deriv=False,
            emin=None, emax=None, label='mu', offset=0, title=None, fig=None, show=True):
    """
    plot_mu(dgroup, norm=False, deriv=False, show_pre=False, show_post=False,
            show_e0=False, show_deriv=False, emin=None, emax=None, label=None,
            show=True, fig=None)

    Plot mu(E) for an XAFS data group in various forms

    Arplguments
    ----------
     dgroup     group of XAFS data after pre_edge() results (see Note 1)
     show_norm  bool whether to show normalized data [False]
     show_flat  bool whether to show flattened, normalized data [False]
     show_deriv bool whether to show derivative of normalized data [False]
     show_pre   bool whether to show pre-edge curve [False]
     show_post  bool whether to show post-edge curve [False]
     show_e0    bool whether to show E0 [False]
     with_deriv bool whether to show deriv (dmu/de) together with mu [False]
     emin       min energy to show, absolute or relative to E0 [None, start of data]
     emax       max energy to show, absolute or relative to E0 [None, end of data]
     label      string for label [None:  'mu', `dmu/dE', or 'mu norm']
     title      string for plot title [None, may use filename if available]
     offset     vertical offset to use for y-array [0]
     show       display the PlotlyFig now [True]
     fig        PlotlyFig to reuse [None]

    Notes
    -----
     1. The input data group must have the following attributes:
         energy, mu, norm, e0, pre_edge, edge_step
    """
    if not HAS_PLOTLY:
        logging.getLogger().error('Need plotply installed')
        return

    if hasattr(dgroup, 'mu'):
        mu = dgroup.mu
    elif  hasattr(dgroup, 'mutrans'):
        mu = dgroup.mutrans
    elif  hasattr(dgroup, 'mufluor'):
        mu = dgroup.mufluor
    else:
        raise ValueError("XAFS data group has no array for mu")
    #endif
    ylabel = plotlabels.mu
    if label is None:
        label = getattr(dgroup, 'filename', 'mu')
    #endif
    if show_deriv:
        mu = dgroup.dmude
        ylabel = f"{ylabel} (deriv)"
        dlabel = plotlabels.dmude
    elif show_norm:
        mu = dgroup.norm
        ylabel = f"{ylabel} (norm)"
        dlabel = plotlabels.norm
    #endif
    elif show_flat:
        mu = dgroup.flat
        ylabel = f"{ylabel} (flat)"
        dlabel = plotlabels.flat
    #endif
    emin, emax = _get_erange(dgroup, emin, emax)
    title = _get_title(dgroup, title=title)

    if fig is None:
        fig = PlotlyFigure(two_yaxis=with_deriv)
    fig.add_plot(dgroup.energy, mu+offset, label=label)

    if with_deriv:
        fig.add_plot(dgroup.energy, dgroup.dmude+offset, label=f"{ylabel} (deriv)", side='right')
        fig.fig.update_yaxis(title_text=plotlabels.dmude, secondary_y=True)
    else:
        if not show_norm and show_pre:
            fig.add_plot(dgroup.energy, dgroup.pre_edge+offset, label='pre_edge')
        if not show_norm and show_post:
            fig.add_plot(dgroup.energy, dgroup.post_edge+offset, label='post_edge')

    if show_e0:
        fig.add_vline(x=dgroup.e0, line_width=2, line_dash="dash", line_color="#AAC")

    return fig.show(title=title, xlabel=plotlabels.energy, ylabel=ylabel,
                        xmin=emin, xmax=emax, show=show)


def plot_bkg(dgroup, norm=True, emin=None, emax=None, show_e0=False,
             label=None, title=None, offset=0):
    """
    plot_bkg(dgroup, norm=True, emin=None, emax=None, show_e0=False, label=None, new=True)

    Plot mu(E) and background mu0(E) for XAFS data group

    Arguments
    ----------
     dgroup      group of XAFS data after autobk() results (see Note 1)
     norm        bool whether to show normalized data [True]
     emin       min energy to show, absolute or relative to E0 [None, start of data]
     emax       max energy to show, absolute or relative to E0 [None, end of data]
     show_e0     bool whether to show E0 [False]
     label       string for label [``None``: 'mu']
     title       string for plot titlte [None, may use filename if available]
     offset      vertical offset to use for y-array [0]

    Notes
    -----
     1. The input data group must have the following attributes:
         energy, mu, bkg, norm, e0, pre_edge, edge_step, filename
    """
    if hasattr(dgroup, 'mu'):
        mu = dgroup.mu
    elif  hasattr(dgroup, 'mutrans'):
        mu = dgroup.mutrans
    else:
        raise ValueError("XAFS data group has no array for mu")

    bkg = dgroup.bkg
    ylabel = plotlabels.mu
    if label is None:
        label = 'mu'

    emin, emax = _get_erange(dgroup, emin, emax)
    if norm:
        mu  = dgroup.norm
        bkg = (dgroup.bkg - dgroup.pre_edge) / dgroup.edge_step
        ylabel = f"{ylabel} (norm)"
        label = f"{ylabel} (norm)"
    #endif
    title = _get_title(dgroup, title=title)

    fig = PlotlyFigure(two_yaxis=False)
    fig.add_plot(dgroup.energy, mu+offset, label=label)
    fig.add_plot(dgroup.energy, bkg+offset, label='bkg')

    if show_e0:
        fig.add_vline(x=dgroup.e0, line_width=2, line_dash="dash", line_color="#AAC")

    return fig.show(title=title, xlabel=plotlabels.energy, ylabel=ylabel, xmin=emin, xmax=emax)


def plot_chie(dgroup, emin=-5, emax=None, label=None, title=None,
              eweight=0, offset=0, how_k=False, fig=None, show=True):
    """
    plot_chie(dgroup, emin=None, emax=None, label=None, new=True, fig=None):

    Plot chi(E) for XAFS data group

    Arguments
    ----------
     dgroup      group of XAFS data after autobk() results (see Note 1)
     emin        min energy to show, absolute or relative to E0 [-25]
     emax        max energy to show, absolute or relative to E0 [None, end of data]
     label       string for label [``None``: 'mu']
     title       string for plot title [None, may use filename if available]
     eweight     energy weightingn for energisdef es>e0  [0]
     offset      vertical offset to use for y-array [0]
     show        display the PlotlyFig now [True]
     fig         PlotlyFigure to re-use [None]

    Notes
    -----
     1. The input data group must have the following attributes:
         energy, mu, bkg, norm, e0, pre_edge, edge_step, filename
    """
    if hasattr(dgroup, 'mu'):
        mu = dgroup.mu
    elif  hasattr(dgroup, 'mutrans'):
        mu = dgroup.mutrans
    else:
        raise ValueError("XAFS data group has no array for mu")
    #endif
    e0   = dgroup.e0
    chie = (mu - dgroup.bkg)
    ylabel = plotlabels.chie
    if abs(eweight) > 1.e-2:
        chie *= (dgroup.energy-e0)**(eweight)
        ylabel = set_label_weight(plotlabels.chiew, eweight)
    xlabel = plotlabels.energy

    emin, emax = _get_erange(dgroup, emin, emax)
    if emin is not None:
        emin = emin - e0
    if emax is not None:
        emax = emax - e0

    title = _get_title(dgroup, title=title)
    def ek_formatter(x, pos):
        ex = float(x)
        if ex < 0:
            s = ''
        else:
            s = f"\n[{etok(ex):.2f}]"
        return r"%1.4g%s" % (x, s)

    if fig is None:
        fig = PlotlyFigure(two_yaxis=False)
    fig.add_plot(dgroup.energy-e0, chie+offset, label=label)
    return fig.show(title=title, xlabel=xlabel, ylabel=ylabel, xmin=emin, xmax=emax, show=show)

def plot_chik(dgroup, kweight=None, kmax=None, show_window=True,
              scale_window=True, label=None, title=None, offset=0, show=True, fig=None):
    """
    plot_chik(dgroup, kweight=None, kmax=None, show_window=True, label=None,
              fig=None)

    Plot k-weighted chi(k) for XAFS data group

    Arguments
    ----------
     dgroup       group of XAFS data after autobk() results (see Note 1)
     kweight      k-weighting for plot [read from last xftf(), or 0]
     kmax         max k to show [None, end of data]
     show_window  bool whether to also plot k-window [True]
     scale_window bool whether to scale k-window to max |chi(k)| [True]
     label        string for label [``None`` to use 'chi']
     title        string for plot title [None, may use filename if available]
     offset       vertical offset to use for y-array [0]
     show         display the PlotlyFig now [True]
     fig          PlotlyFigure to re-use [None]

    Notes
    -----
     1. The input data group must have the following attributes:
         k, chi, kwin, filename
    """
    kweight = _get_kweight(dgroup, kweight)
    chi = dgroup.chi * dgroup.k ** kweight

    if label is None:
        label = 'chi'

    title = _get_title(dgroup, title=title)

    if fig is None:
        fig = PlotlyFigure(two_yaxis=False)
    fig.add_plot(dgroup.k, chi+offset, label=label)

    if show_window and hasattr(dgroup, 'kwin'):
        kwin = dgroup.kwin
        if scale_window:
            kwin = kwin*max(abs(chi))
        fig.add_plot(dgroup.k, kwin+offset, label='window')

    return fig.show(title=title, xlabel=plotlabels.k, xmin=0, xmax=kmax,
                    ylabel=set_label_weight(plotlabels.chikw, kweight),
                        show=show)

def plot_chir(dgroup, show_mag=True, show_real=False, show_imag=False,
              show_window=False, rmax=None, label=None, title=None,
              offset=0, show=True, fig=None):
    """
    plot_chir(dgroup, show_mag=True, show_real=False, show_imag=False,
              rmax=None, label=None, fig=None)

    Plot chi(R) for XAFS data group

    Arguments
    ----------
     dgroup       group of XAFS data after xftf() results (see Note 1)
     show_mag     bool whether to plot |chi(R)| [True]
     show_real    bool whether to plot Re[chi(R)] [False]
     show_imag    bool whether to plot Im[chi(R)] [False]
     show_window  bool whether to R-windw for back FT (will be scaled) [False]
     label        string for label [``None`` to use 'chir']
     title        string for plot title [None, may use filename if available]
     rmax         max R to show [None, end of data]
     offset       vertical offset to use for y-array [0]
     show         display the PlotlyFig now [True]
     fig          PlotlyFigure to re-use [None]

    Notes
    -----
     1. The input data group must have the following attributes:
         r, chir_mag, chir_im, chir_re, kweight, filename
    """
    kweight = _get_kweight(dgroup, None)

    title = _get_title(dgroup, title=title)

    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)

    if not hasattr(dgroup, 'r'):
        print("group does not have chi(R) data")
        return
    #endif
    if label is None:
        label = 'chir'

    if fig is None:
        fig = PlotlyFigure(two_yaxis=False)
    if show_mag:
        fig.add_plot(dgroup.r, dgroup.chir_mag+offset, label=f'{label} (mag)')
    if show_real:
        fig.add_plot(dgroup.r, dgroup.chir_re+offset, label=f'{label} (real)')

    if show_imag:
        fig.add_plot(dgroup.r, dgroup.chir_im+offset, label=f'{label} (imag)')

    if show_window and hasattr(dgroup, 'rwin'):
        rwin = dgroup.rwin * max(dgroup.chir_mag)
        fig.add_plot(dgroup.r, rwin+offset, label='window')

    return fig.show(title=title, xlabel=plotlabels.r, ylabel=ylabel, xmax=rmax, show=show)


def plot_chiq(dgroup, kweight=None, kmin=0, kmax=None, show_chik=False, label=None,
              title=None, offset=0, show_window=False, scale_window=True,
              show=True, fig=None):
    """
    plot_chiq(dgroup, kweight=None, kmax=None, show_chik=False, label=None,
              new=True, win=1)

    Plot Fourier filtered chi(k), optionally with k-weighted chi(k) for XAFS data group

    Arguments
    ----------
     dgroup       group of XAFS data after autobk() results (see Note 1)
     kweight      k-weighting for plot [read from last xftf(), or 0]
     kmax         max k to show [None, end of data]
     show_chik    bool whether to also plot k-weighted chi(k) [False]
     show_window  bool whether to also plot FT k-window [False]
     scale_window bool whether to scale FT k-window to max |chi(q)| [True]
     label        string for label [``None`` to use 'chi']
     title        string for plot title [None, may use filename if available]
     offset       vertical offset to use for y-array [0]
     show         display the PlotlyFig now [True]
     fig          PlotlyFigure to re-use [None]

    Notes
    -----
     1. The input data group must have the following attributes:
         k, chi, kwin, filename
    """
    kweight = _get_kweight(dgroup, kweight)
    nk = len(dgroup.k)
    chiq = dgroup.chiq_re[:nk]

    if label is None:
        label = 'chi(q) (filtered)'

    title = _get_title(dgroup, title=title)
    if fig is None:
        fig = PlotlyFigure(two_yaxis=False)
    fig.add_plot(dgroup.k, chiq+offset, label=label)
    if kmax is None:
        kmax = max(dgroup.k)

    if show_chik:
        chik = dgroup.chi * dgroup.k ** kweight
        fig.add_plot(dgroup.k, chik+offset, label='chi(k) (unfiltered)')

    if show_window and hasattr(dgroup, 'kwin'):
        kwin = dgroup.kwin
        if scale_window:
            kwin = kwin*max(abs(chiq))
        fig.add_plot(dgroup.k, kwin+offset, label='window')

    ylabel = set_label_weight(plotlabels.chikw, kweight)
    return fig.show(title=title, xlabel=plotlabels.k,
                    ylabel=ylabel, xmin=kmin, xmax=kmax, show=show)



def plot_chifit(dataset, kmin=0, kmax=None, kweight=None, rmax=None,
                show_mag=True, show_real=False, show_imag=False,
                show_bkg=False, use_rebkg=False, title=None, offset=0):
    """
    plot_chifit(dataset, kmin=0, kmax=None, rmax=None,
                show_mag=True, show_real=False, show_imag=False)

    Plot k-weighted chi(k) and chi(R) for fit to feffit dataset

    Arguments
    ----------
     dataset      feffit dataset, after running feffit()
     kmin         min k to show [0]
     kmax         max k to show [None, end of data]
     kweight      kweight to show [None, taken from dataset]
     rmax         max R to show [None, end of data]
     show_mag     bool whether to plot |chidr(R)| [True]
     show_real    bool whether to plot Re[chi(R)] [False]
     show_imag    bool whether to plot Im[chi(R)] [False]
     title        string for plot title [None, may use filename if available]
     offset       vertical offset to use for y-array [0]


    """
    if kweight is None:
        kweight = dataset.transform.kweight
    #endif
    if isinstance(kweight, (list, tuple, np.ndarray)):
        kweight=kweight[0]

    title = _get_title(dataset, title=title)

    mod = dataset.model
    dat = dataset.data
    if use_rebkg and hasattr(dataset, 'data_rebkg'):
        dat = dataset.data_rebkg
        title += ' (refined bkg)'

    data_chik  = dat.chi * dat.k**kweight
    model_chik = mod.chi * mod.k**kweight

    # k-weighted chi(k) in first plot window
    fig = PlotlyFigure(two_yaxis=False)
    fig.add_plot(dat.k, data_chik+offset, label='data')
    fig.add_plot(mod.k, model_chik+offset, label='fit')

    ylabel = set_label_weight(plotlabels.chikw, kweight)
    fig.show(title=title, xlabel=plotlabels.k,
                  ylabel=ylabel, xmin=kmin, xmax=kmax)

    #  chi(R) in first plot window
    rfig = PlotlyFigure(two_yaxis=False)

    if show_mag:
        rfig.add_plot(dat.r, dat.chir_mag+offset, label='|data|')
        rfig.add_plot(mod.r, mod.chir_mag+offset, label='|fit|')

    if show_real:
        rfig.add_plot(dat.r, dat.chir_re+offset, label='Re[data]')
        rfig.add_plot(mod.r, mod.chir_re+offset, label='Re[fit]')
    if show_imag:
        rfig.add_plot(dat.r, dat.chir_im+offset, label='Im[data]')
        rfig.add_plot(mod.r, mod.chir_im+offset, label='Im[fit]')

    ylabel = chirlab(kweight, show_mag=show_mag, show_real=show_real, show_imag=show_imag)
    rfig.show(title=title, xlabel=plotlabels.r, ylabel=ylabel, xmin=0, xmax=rmax)
    return fig, rfig

def plot_path_k(dataset, ipath=0, kmin=0, kmax=None, offset=0, label=None, fig=None):
    """
    plot_path_k(dataset, ipath, kmin=0, kmax=None, offset=0, label=None)

    Plot k-weighted chi(k) for a single Path of a feffit dataset

    Arguments
    ----------
     dataset      feffit dataset, after running feffit()
     ipath        index of path, starting count at 0 [0]
     kmin         min k to show [0]
     kmax         max k to show [None, end of data]
     offset       vertical offset to use for plot [0]
     label        path label ['path %d' % ipath]
     fig          PlotlyFigure for reuse
    """
    kweight = dataset.transform.kweight
    path = dataset.pathlist[ipath]
    if label is None:
        label = 'path %i' % (1+ipath)
    title = _get_title(dataset, title=title)

    chi_kw = offset + path.chi * path.k**kweight
    if fig is None:
        fig = PlotlyFigure(two_yaxis=False)
    fig.add_plot(path.k, chi_kw, label=label)
    return fig.set_style(title=title,  xlabel=plotlabels.k,
                        yabel=set_label_weight(plotlabels.chikw, kweight),
                        xmin=kmin, xmax=kmax)

def plot_path_r(dataset, ipath, rmax=None, offset=0, label=None,
                show_mag=True, show_real=False, show_imag=True, fig=None):
    """
    plot_path_r(dataset, ipath,rmax=None, offset=0, label=None,
                show_mag=True, show_real=False, show_imag=True, fig=None)

    Plot chi(R) for a single Path of a feffit dataset

    Arguments
    ----------
     dataset      feffit dataset, after running feffit()
     ipath        index of path, starting count at 0 [0]
     rmax         max R to show [None, end of data]
     offset       vertical offset to use for plot [0]
     label        path label ['path %d' % ipath]
     show_mag     bool whether to plot |chi(R)| [True]
     show_real    bool whether to plot Re[chi(R)] [False]
     show_imag    bool whether to plot Im[chi(R)] [False]
     fig          PlotlyFigure for reuse
    """
    path = dataset.pathlist[ipath]
    if label is None:
        label = 'path %i' % (1+ipath)

    title = _get_title(dataset, title=title)
    kweight =dataset.transform.kweight
    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)

    if fig is None:
        fig = PlotlyFigure(two_yaxis=False)
    if show_mag:
        fig.add_plot(path.r,  offset+path.chir_mag, label=f'|{label}|')

    if show_real:
        fig.add_plot(path.r,  offset+path.chir_re, label=f'Re[{label}|')

    if show_imag:
        fig.add_plot(path.r,  offset+path.chir_im, label=f'Im[{label}|')

    return fig.show(title=title,  xlabel=plotlabels.r, ylabel=chirlab(kweight),
                    xmax=rmax)


def plot_paths_k(dataset, offset=-1, kmin=0, kmax=None, title=None, fig=None):
    """
    plot_paths_k(dataset, offset=-1, kmin=0, kmax=None, fig=None)

    Plot k-weighted chi(k) for model and all paths of a feffit dataset

    Arguments
    ----------
     dataset      feffit dataset, after running feffit()
     kmin         min k to show [0]
     kmax         max k to show [None, end of data]
     offset       vertical offset to use for paths for plot [-1]
     title        string for plot title [None, may use filename if available]
     fig          PlotlyFigure for reuse
    """
    # make k-weighted chi(k)
    kweight = dataset.transform.kweight
    model = dataset.model

    model_chi_kw = model.chi * model.k**kweight

    title = _get_title(dataset, title=title)
    if fig is None:
        fig = PlotlyFigure(two_yaxis=False)
    fig.add_plot(model.k, model_chi_kw, label='sum')

    for ipath in range(len(dataset.pathlist)):
        path = dataset.pathlist[ipath]
        label = 'path %i' % (1+ipath)
        chi_kw = offset*(1+ipath) + path.chi * path.k**kweight
        fig.add_plot(path.k, chi_kw, label=label)

    return fig.show(title=title,  xlabel=plotlabels.k,
                    ylabel=set_label_weight(plotlabels.chikw, kweight),
                    xmin=kmin, xmax=kmax)

def plot_paths_r(dataset, offset=-0.25, rmax=None, show_mag=True,
                 show_real=False, show_imag=False, title=None, fig=None):
    """
    plot_paths_r(dataset, offset=-0.5, rmax=None, show_mag=True, show_real=False,
                 show_imag=False)

    Plot chi(R) for model and all paths of a feffit dataset

    Arguments
    ----------
     dataset      feffit dataset, after running feffit()
     offset       vertical offset to use for paths for plot [-0.5]
     rmax         max R to show [None, end of data]
     show_mag     bool whether to plot |chi(R)| [True]
     show_real    bool whether to plot Re[chi(R)] [False]
     show_imag    bool whether to plot Im[chi(R)] [False]
     title        string for plot title [None, may use filename if available]
     fig          PlotlyFigure for reuse
    """
    kweight = dataset.transform.kweight
    model = dataset.model

    title = _get_title(dataset, title=title)
    if fig is None:
        fig = PlotlyFigure(two_yaxis=False)

    if show_mag:
        fig.add_plot(model.r, model.chir_mag, label='|sum|')

    if show_real:
        fig.add_plot(model.r, model.chir_re, label='Re[sum]')

    if show_imag:
        fig.add_plot(model.r, model.chir_re, label='Im[sum]')

    for ipath in range(len(dataset.pathlist)):
        path = dataset.pathlist[ipath]
        label = 'path %i' % (1+ipath)
        off = (ipath+1)*offset
        if show_mag:
            fig.add_plot(path.r, off+path.chir_mag, label=f'|{label}|')

        if show_real:
            fig.add_plot(path.r, off+path.chir_re, label=f'Re[{label}]')

        if show_imag:
            fig.add_plot(path.r, off+path.chir_im, label=f'Im[{label}]')

    return fig.show(title=title, xlabel=plotlabels.r,
                    ylabel=chirlab(kweight), xmax=rmax)

def plot_prepeaks_baseline(dgroup, subtract_baseline=False, show_fitrange=True,
                           show_peakrange=True):
    """Plot pre-edge peak baseline fit, as from `pre_edge_baseline` or XAS Viewer

    dgroup must have a 'prepeaks' attribute
    """
    if not hasattr(dgroup, 'prepeaks'):
        raise ValueError('Group needs prepeaks')
    #endif
    ppeak = dgroup.prepeaks

    px0, px1, py0, py1 = extend_plotrange(dgroup.xdat, dgroup.ydat,
                                          xmin=ppeak.emin, xmax=ppeak.emax)

    title = "pre_edge baseline\n %s" % dgroup.filename

    fig = PlotlyFigure(two_yaxis=False)

    ydat = dgroup.ydat
    xdat = dgroup.xdat
    if subtract_baseline:
        fig.add_plot(ppeak.energy, ppeak.baseline, label='baseline subtracted peaks')
    else:
        fig.add_plot(ppeak.energy, ppeak.baseline, label='baseline')
        fig.add_plot(xdat, ydat, label='data')

    if show_fitrange:
        for x in (ppeak.emin, ppeak.emax):
            fig.add_vline(x=x, line_width=2, line_dash="dash", line_color="#DDDDCC")
            fig.add_vline(x=ppeak.centroid, line_width=2, line_dash="dash", line_color="#EECCCC")

    if show_peakrange:
        for x in (ppeak.elo, ppeak.ehi):
            y = ydat[index_of(xdat, x)]
            fig.add_plot([x], [y], marker='o', marker_size=7)

    return fig.show(title=title, xlabel=plotlabels.energy, ylabel='mu (normalized)',
                    xmin=px0, xmax=px1, ymin=py0, ymax=py1)


def plot_prepeaks_fit(dgroup, nfit=0, show_init=False, subtract_baseline=False,
                      show_residual=False):
    """plot pre-edge peak fit, as from Larix

    dgroup must have a 'peakfit_history' attribute
    """
    if not hasattr(dgroup, 'prepeaks'):
        raise ValueError('Group needs prepeaks')
    #endif
    if show_init:
        result = pkfit = dgroup.prepeaks
    else:
        hist = getattr(dgroup.prepeaks, 'fit_history', None)
        if nfit > len(hist):
            nfit = 0
        pkfit = hist[nfit]
        result = pkfit.result
    #endif

    if pkfit is None:
        raise ValueError('Group needs prepeaks.fit_history or init_fit')
    #endif

    opts = pkfit.user_options
    xeps = min(np.diff(dgroup.xdat)) / 5.
    xdat = 1.0*pkfit.energy
    ydat = 1.0*pkfit.norm

    xdat_full = 1.0*dgroup.xdat
    ydat_full = 1.0*dgroup.ydat

    if show_init:
        yfit   = pkfit.init_fit
        ycomps = None #  pkfit.init_ycomps
        ylabel = 'model'
    else:
        yfit   = 1.0*result.best_fit
        ycomps = pkfit.ycomps
        ylabel = 'best fit'

    baseline = 0.*ydat
    if ycomps is not None:
        for label, ycomp in ycomps.items():
            if label in opts['bkg_components']:
                baseline += ycomp

    fig = PlotlyFigure(two_yaxis=False)
    title ='%s:\npre-edge peak' % dgroup.filename



    if subtract_baseline:
        ydat -= baseline
        yfit -= baseline
        ydat_full = 1.0*ydat
        xdat_full = 1.0*xdat
        plotopts['ylabel'] = '%s-baseline' % plotopts['ylabel']

    dx0, dx1, dy0, dy1 = extend_plotrange(xdat_full, ydat_full,
                                          xmin=opts['emin'], xmax=opts['emax'])
    fx0, fx1, fy0, fy1 = extend_plotrange(xdat, yfit,
                                          xmin=opts['emin'], xmax=opts['emax'])

    ncolor = 0
    popts = {}
    plotopts.update(popts)
    dymin = dymax = None

    fig.add_plot(xdat, ydat, label='data')
    fig.add_plot(xday, yfit, label='fit')

    if show_residual:
        dfig = PlotlyFigure()
        dfig.add_plot(xdat, yfit-ydat, label='fit-data')
        dy = yfit - ydat
        dymax, dymin = dy.max(), dy.min()
        dymax += 0.05 * (dymax - dymin)
        dymin -= 0.05 * (dymax - dymin)

    if ycomps is not None:
        ncomps = len(ycomps)
        if not subtract_baseline:
            fig.add_plot(xdat, baseline, label='baseline')
        for icomp, label in enumerate(ycomps):
            ycomp = ycomps[label]
            if label in opts['bkg_components']:
                continue
            fig.add_plot(xdat, ycomp, label=label)

    if opts.get('show_fitrange', False):
        for attr in ('emin', 'emax'):
            fig.add_vline(opts[attr], line_width=2, line_dash="dash", line_color="#DDDDCC")

    if opts.get('show_centroid', False):
        pcen = getattr(dgroup.prepeaks, 'centroid', None)
        if hasattr(result, 'params'):
            pcen = result.params.get('fit_centroid', None)
            if pcen is not None:
                pcen = pcen.value
        if pcen is not None:
            fig.add_vlinee(pcen, color='#EECCCC')

    fig.show(title=title, xlabel=plotlabels.energy, ylabel=opts['array_desc'])
    dfig.show(title=tile, ylabel='fit-data', ymin=dymin, ymax=dymax)
    return fig, dfig


def _pca_ncomps(result, min_weight=0, ncomps=None):
    if ncomps is None:
        if min_weight > 1.e-12:
            ncomps = np.where(result.variances < min_weight)[0][0]
        else:
            ncomps = np.argmin(result.ind)
    return ncomps


def plot_pca_components(result, min_weight=0, ncomps=None, min_variance=1.e-5):
    """Plot components from PCA result

    result must be output of `pca_train`
    """
    title = "PCA components"

    ncomps = int(result.nsig)
    fig = PlotlyFigure(two_yaxis=False)
    fig.add_plot(result.x, result.mean, label='Mean')
    for i, comp in enumerate(result.components):
        if result.variances[i] > min_variance:
            label = 'Comp# %d (%.4f)' % (i+1, result.variances[i])
            fig.add_plot(result.x, comp, label=label)

    return fig.show(title=title, xlabel=plotlabels.energy, ylabel=plotlabels.norm,
                 xmin=result.xmin, xmax=result.xmax)

def plot_pca_weights(result, min_weight=0, ncomps=None):
    """Plot component weights from PCA result (aka SCREE plot)

    result must be output of `pca_train`
    """
    max_comps = len(result.components)-1

    title = "PCA Variances (SCREE) and Indicator Values"
    fig = PlotlyFigure(two_yaxis=True)

    ncomps = max(1, int(result.nsig))

    x0, x1, y0, y1 = extend_plotrange(result.variances, result.variances)
    y0 = max(1.e-6, min(result.variances[:-1]))
    x = 1+np.arange(ncomps)
    y = result.variances[:ncomps]
    fig.add_plot(x, y, label='significant', style='solid', marker='o')

    xe = 1 + np.arange(ncomps-1, max_comps)
    ye = result.variances[ncomps-1:ncomps+max_comps]

    fig.add_plot(xe, ye, label='not significant', style='dashed', marker='o')
    fig.set_ylog()
    yi = result.ind[1:]
    xi = 1 + np.arange(len(yi))

    x0, x1, yimin, yimax = extend_plotrange(xi, yi)

    fig.add_plot(xi, result.ind[1:], label='Indicator Value',
                    style='solid', side='right')
    fig.fig.update_yaxes(title_text='Indicator', secondary_y=True)
    return fig.show(title=title, xlabel='Component #', ylabel='variance')


def plot_pca_fit(dgroup, with_components=True):
    """Plot data and fit result from pca_fit, which rom PCA result

    result must be output of `pca_fit`
    """
    title = "PCA fit: %s" % (dgroup.filename)
    result = dgroup.pca_result
    model = result.pca_model

    fig = PlotlyFigure(two_yaxis=False)
    fig.add_plot(result.x, result.ydat, label='data')
    fig.add_plot(result.x, result.yfit, label='fit')
    if with_components:
        fig.add_plot(result.x, model.mean, label='mean')
        for n in range(len(result.weights)):
            cval = model.components[n]*result.weights[n]
            fig.add_plot(result.x, cval, label='Comp #%d' % (n+1))

    fig.show(title=title, xmin=model.xmin, xmax=model.xmax,
             xlabel=plotlabels.energy, ylabel=plotlabels.norm)

    dfig = PlotlyFigure(two_yaxis=False)
    dfig.add_plot(result.x, result.yfit-result.ydat, label='fit-data')
    dfig.show(title=title, xmin=model.xmin, xmax=model.xmax,
             xlabel=plotlabels.energy, ylabel='fit-data')
    return fig, dfig

def plot_diffkk(dgroup, emin=None, emax=None, new=True, label=None,
                title=None, offset=0):
    """
    plot_diffkk(dgroup, norm=True, emin=None, emax=None, show_e0=False, label=None):

    Plot mu(E) and background mu0(E) for XAFS data group

    Arguments
    ----------
     dgroup      group of XAFS data after autobk() results (see Note 1)
     norm        bool whether to show normalized data [True]
     emin       min energy to show, absolute or relative to E0 [None, start of data]
     emax       max energy to show, absolute or relative to E0 [None, end of data]
     show_e0     bool whether to show E0 [False]
     label       string for label [``None``: 'mu']
     title       string for plot title [None, may use filename if available]
     offset      vertical offset to use for y-array [0]

    Notes
    -----
     1. The input data group must have the following attributes:
         energy, mu, bkg, norm, e0, pre_edge, edge_step, filename
    """
    if hasattr(dgroup, 'f2'):
        f2 = dgroup.f2
    else:
        raise ValueError("Data group has no array for f2")
    #endif
    ylabel = r'$f \rm\,\, (e^{-})$ '
    emin, emax = _get_erange(dgroup, emin, emax)
    title = _get_title(dgroup, title=title)

    labels = {'f2': r"$f_2(E)$", 'fpp': r"$f''(E)$", 'fp': r"$f'(E)$", 'f1': r"$f_1(E)$"}

    fig = PlotlyFigure(two_yaxis=False)
    fig.add_plot(dgroup.energy, f2, label=labels['f2'])

    for attr in ('fpp', 'f1', 'fp'):
        yval = getattr(dgroup, attr)
        if yval is not None:
            fig.add_plot(dgroup.energy, yval, label=labels[attr])

    return fig.show(title=title, xlabel=plotlabels.energy, yaxis_label=ylabel,
             xmin=emin, xmax=emax)


def plot_feffdat(feffpath, with_phase=True, title=None, fig=None):
    """
    plot_feffdat(feffpath, with_phase=True, title=None)

    Plot Feff's magnitude and phase as a function of k for a FeffPath

    Arguments
    ----------
     feffpath    feff path as read by feffpath()
     with_pase   whether to plot phase(k) as well as magnitude [True]
     title       string for plot title [None, may use filename if available]

    Notes
    -----
     1. The input data group must have the following attributes:
         energy, mu, bkg, norm, e0, pre_edge, edge_step, filename
    """
    if hasattr(feffpath, '_feffdat'):
        fdat = feffpath._feffdat
    else:
        raise ValueError("must pass in a Feff path as from feffpath()")

    if fig is None:
        fig = PlotlyFigure(two_yaxis=True)
    fig.add_plot(result.x, result.ydat, label='data')


    fig.add_plot(fdat.k, fdat.mag_feff, label='magnitude')
    # xlabel=plotlabels.k,
    # ylabel='|F(k)|', title=title,

    if with_phase:
        fig.add_plot(fdat.k, fdat.pha_feff, label='phase')
        fig.fig.update_yaxis(title_text='Phase(k)', secondary_y=True)
    return fig.show(title=title, xlabel=plotlabels.k, ylabel='|F(k)|')

#enddef

def plot_wavelet(dgroup, show_mag=True, show_real=False, show_imag=False,
                 rmax=None, kmax=None, kweight=None, title=None):
    """
    plot_wavelet(dgroup, show_mag=True, show_real=False, show_imag=False,
              rmax=None, kmax=None, kweight=None, title=None)

    Plot wavelet for XAFS data group

    Arguments
    ----------
     dgroup       group of XAFS data after xftf() results (see Note 1)
     show_mag     bool whether to plot wavelet magnitude [True]
     show_real    bool whether to plot real part of wavelet [False]
     show_imag    bool whether to plot imaginary part of wavelet [False]
     title        string for plot title [None, may use filename if available]
     rmax         max R to show [None, end of data]
     kmax         max k to show [None, end of data]
     kweight      k-weight to use to construct wavelet [None, take from group]

    Notes
    -----
     The wavelet will be performed
    """
    print("Image display not yet available with larch+plotly")
    kweight = _get_kweight(dgroup, kweight)
    cauchy_wavelet(dgroup, kweight=kweight, rmax_out=rmax)
    title = _get_title(dgroup, title=title)

    opts = dict(title=title, x=dgroup.k, y=dgroup.wcauchy_r, xmax=kmax,
                ymax=rmax, xlabel=plotlabels.k, ylabel=plotlabels.r,
                show_axis=True)
    if show_mag:
        _imshow(dgroup.wcauchy_mag, **opts)
    elif show_real:
        _imshow(dgroup.wcauchy_real, **opts)
    elif show_imag:
        _imshow(dgroup.wcauchy_imag, **opts)
    #endif
#enddef
