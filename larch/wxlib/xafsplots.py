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
from numpy import gradient, ndarray, diff, where, arange, argmin
from matplotlib.ticker import FuncFormatter

from larch import Group
from larch.math import (index_of, index_nearest, interp)
from larch.xafs import cauchy_wavelet, etok, ktoe

try:
    import wx
    HAS_WXPYTHON = True
except ImportError:
    HAS_WXPYTHON = False

if HAS_WXPYTHON:
    from .plotter import (_getDisplay, _plot, _oplot, _newplot, _fitplot,
                          _plot_text, _plot_marker, _plot_arrow,
                          _plot_axvline, _plot_axhline, _imshow)
else:
    def nullfunc(*args, **kws): pass

    _getDisplay = _plot = _oplot = _newplot = nullfunc
    _fitplot = _plot_text = _plot_marker = nullfunc
    _plot_arrow = _plot_axvline = _plot_axhline = nullfunc



LineColors = ('#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd',
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf')

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
    return ylab[0].format(kweight+1)
#enddef

plotlabels = Group(k       = r'$k \rm\,(\AA^{-1})$',
                   r       = r'$R \rm\,(\AA)$',
                   energy  = r'$E\rm\,(eV)$',
                   ewithk  = r'$E\rm\,(eV)$' + '\n' + r'$[k \rm\,(\AA^{-1})]$',
                   mu      = r'$\mu(E)$',
                   norm    = r'normalized $\mu(E)$',
                   flat    = r'flattened $\mu(E)$',
                   deconv  = r'deconvolved $\mu(E)$',
                   dmude   = r'$d\mu(E)/dE$',
                   dnormde = r'$d\mu_{\rm norm}(E)/dE$',
                   d2mude  = r'$d^2\mu(E)/dE^2$',
                   d2normde= r'$d^2\mu_{\rm norm}(E)/dE^2$',
                   chie    = r'$\chi(E)$',
                   chiew   = r'$E^{{{0:g}}}\chi(E) \rm\,(eV^{{{0:g}}})$',
                   chikw   = r'$k^{{{0:g}}}\chi(k) \rm\,(\AA^{{-{0:g}}})$',
                   chir    = r'$\chi(R) \rm\,(\AA^{{-{0:g}}})$',
                   chirmag = r'$|\chi(R)| \rm\,(\AA^{{-{0:g}}})$',
                   chirre  = r'${{\rm Re}}[\chi(R)] \rm\,(\AA^{{-{0:g}}})$',
                   chirim  = r'${{\rm Im}}[\chi(R)] \rm\,(\AA^{{-{0:g}}})$',
                   chirpha = r'${{\rm Phase}}[\chi(R)] \rm\,(\AA^{{-{0:g}}})$',
                   e0color = '#B2B282',
                   chirlab = chirlab)

def _get_title(dgroup, title=None):
    """get best title for group"""
    if title is not None:
        return title
    #endif
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
            return t
        #endif
        if data_group is not None:
            t = getattr(data_group, attr, None)
            if t is not None:
                return t
            #endif
        #endif
    #endfor

    return repr(dgroup)
#enddef

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
    if emax is not None:
        if not (emax > dat_emin and emax < dat_emax):
            if emax+e0 > dat_emin and emax+e0 < dat_emax:
                emax += e0
    return emin, emax
#enddef

def redraw(win=1, xmin=None, xmax=None, ymin=None, ymax=None,
           show_legend=True, stacked=False, _larch=None):
    disp = _getDisplay(win=win, stacked=stacked, _larch=_larch)
    if disp is None:
        return
    panel = disp.panel
    panel.conf.show_legend = show_legend
    if (xmin is not None or xmax is not None or
        ymin is not None or ymax is not None):
        panel.set_xylims((xmin, xmax, ymin, ymax))
    else:
        panel.unzoom_all()
    if show_legend:  # note: draw_legend *will* redraw the canvas
        panel.conf.draw_legend()
    else:
        panel.canvas.draw()
    #endif
#enddef


def plot_mu(dgroup, show_norm=False, show_deriv=False,
            show_pre=False, show_post=False, show_e0=False, with_deriv=False,
            emin=None, emax=None, label='mu', new=True, delay_draw=False,
            offset=0, title=None, win=1, _larch=None):
    """
    plot_mu(dgroup, norm=False, deriv=False, show_pre=False, show_post=False,
             show_e0=False, show_deriv=False, emin=None, emax=None, label=None,
             new=True, win=1)

    Plot mu(E) for an XAFS data group in various forms

    Arguments
    ----------
     dgroup     group of XAFS data after pre_edge() results (see Note 1)
     show_norm  bool whether to show normalized data [False]
     show_deriv bool whether to show derivative of XAFS data [False]
     show_pre   bool whether to show pre-edge curve [False]
     show_post  bool whether to show post-edge curve [False]
     show_e0    bool whether to show E0 [False]
     with_deriv bool whether to show deriv together with mu [False]
     emin       min energy to show, absolute or relative to E0 [None, start of data]
     emax       max energy to show, absolute or relative to E0 [None, end of data]
     label      string for label [None:  'mu', `dmu/dE', or 'mu norm']
     title      string for plot title [None, may use filename if available]
     new        bool whether to start a new plot [True]
     delay_draw bool whether to delay draw until more traces are added [False]
     offset      vertical offset to use for y-array [0]
     win        integer plot window to use [1]

    Notes
    -----
     1. The input data group must have the following attributes:
         energy, mu, norm, e0, pre_edge, edge_step
    """
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
        label = 'mu'
    #endif
    if show_deriv:
        mu = gradient(mu)/gradient(dgroup.energy)
        ylabel = plotlabels.dmude
        dlabel = '%s (deriv)' % label
    elif show_norm:
        mu = dgroup.norm
        ylabel = "%s (norm)" % ylabel
        dlabel = "%s (norm)" % label
    #endif
    emin, emax = _get_erange(dgroup, emin, emax)

    title = _get_title(dgroup, title=title)

    opts = dict(win=win, show_legend=True, linewidth=3,
                title=title, xmin=emin, xmax=emax,
                delay_draw=True, _larch=_larch)

    _plot(dgroup.energy, mu+offset, xlabel=plotlabels.energy, ylabel=ylabel,
          label=label, zorder=20, new=new, **opts)

    if with_deriv:
        dmu = gradient(mu)/gradient(dgroup.energy)
        _plot(dgroup.energy, dmu+offset, ylabel=plotlabels.dmude,
              label='%s (deriv)' % label, zorder=18, side='right', **opts)
    #endif
    if (not show_norm and not show_deriv):
        if show_pre:
            _plot(dgroup.energy, dgroup.pre_edge+offset, label='pre_edge',
                  zorder=18, **opts)
        #endif
        if show_post:
            _plot(dgroup.energy, dgroup.post_edge+offset, label='post_edge',
                  zorder=18, **opts)
            if show_pre:
                i = index_of(dgroup.energy, dgroup.e0)
                ypre = dgroup.pre_edge[i]
                ypost = dgroup.post_edge[i]
                _plot_arrow(dgroup.e0, ypre, dgroup.e0+offset, ypost,
                            color=plotlabels.e0color, width=0.25,
                            head_width=0, zorder=3, win=win, _larch=_larch)
            #endif
        #endif
    #endif
    if show_e0:
        _plot_axvline(dgroup.e0, zorder=2, size=3,
                      label='E0', color=plotlabels.e0color, win=win,
                      _larch=_larch)
        disp = _getDisplay(win=win, _larch=_larch)
        if disp is not None:
            disp.panel.conf.draw_legend()
    redraw(win=win, xmin=emin, xmax=emax, _larch=_larch)
#enddef

def plot_bkg(dgroup, norm=True, emin=None, emax=None, show_e0=False,
             label=None, title=None, new=True, delay_draw=False, offset=0,
             win=1, _larch=None):
    """
    plot_bkg(dgroup, norm=True, emin=None, emax=None, show_e0=False, label=None, new=True, win=1):

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
     new         bool whether to start a new plot [True]
     delay_draw  bool whether to delay draw until more traces are added [False]
     offset      vertical offset to use for y-array [0]
     win         integer plot window to use [1]

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

    bkg = dgroup.bkg
    ylabel = plotlabels.mu
    if label is None:
        label = 'mu'
    #endif
    emin, emax = _get_erange(dgroup, emin, emax)
    if norm:
        mu  = dgroup.norm
        bkg = (dgroup.bkg - dgroup.pre_edge) / dgroup.edge_step
        ylabel = "%s (norm)" % ylabel
        label = "%s (norm)" % label
    #endif
    title = _get_title(dgroup, title=title)
    opts = dict(win=win, show_legend=True, linewidth=3,
                delay_draw=True, _larch=_larch)
    _plot(dgroup.energy, mu+offset, xlabel=plotlabels.energy, ylabel=ylabel,
         title=title, label=label, zorder=20, new=new, xmin=emin, xmax=emax,
         **opts)
    ymin, ymax = None, None
    disp = _getDisplay(win=win, _larch=_larch)
    if disp is not  None:
        xylims = disp.panel.get_viewlimits()
        ymin, ymax = xylims[2], xylims[3]
    _plot(dgroup.energy, bkg+offset, zorder=18, label='bkg', **opts)

    if show_e0:
        _plot_axvline(dgroup.e0, zorder=2, size=3, label='E0',
                      color=plotlabels.e0color, win=win, _larch=_larch)
        if disp is not None:
            disp.panel.conf.draw_legend()
    #endif
    redraw(win=win, xmin=emin, xmax=emax, ymin=ymin, ymax=ymax, _larch=_larch)
#enddef

def plot_chie(dgroup, emin=-5, emax=None, label=None, title=None,
              eweight=0, show_k=True, new=True, delay_draw=False,
              offset=0, win=1, _larch=None):
    """
    plot_chie(dgroup, emin=None, emax=None, label=None, new=True, win=1):

    Plot chi(E) for XAFS data group

    Arguments
    ----------
     dgroup      group of XAFS data after autobk() results (see Note 1)
     emin        min energy to show, absolute or relative to E0 [-25]
     emax        max energy to show, absolute or relative to E0 [None, end of data]
     label       string for label [``None``: 'mu']
     title       string for plot title [None, may use filename if available]
     new         bool whether to start a new plot [True]
     eweight     energy weightingn for energies>e0  [0]
     show_k      bool whether to show k values   [True]
     delay_draw  bool whether to delay draw until more traces are added [False]
     offset      vertical offset to use for y-array [0]
     win         integer plot window to use [1]

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
        ylabel = plotlabels.chiew.format(eweight)

    xlabel = plotlabels.ewithk if show_k else plotlabels.energy

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
            s = '\n[%.1f]' % (etok(ex))
        return r"%1.4g%s" % (x, s)

    _plot(dgroup.energy-e0, chie+offset, xlabel=xlabel, ylabel=ylabel,
          title=title, label=label, zorder=20, new=new, xmin=emin,
          xmax=emax, win=win, show_legend=True, delay_draw=delay_draw,
          linewidth=3, _larch=_larch)

    if show_k:
        disp = _getDisplay(win=win, _larch=_larch)
        axes = disp.panel.axes
        axes.xaxis.set_major_formatter(FuncFormatter(ek_formatter))

    if not delay_draw:
        redraw(win=win, xmin=emin, xmax=emax, _larch=_larch)

#enddef

def plot_chik(dgroup, kweight=None, kmax=None, show_window=True,
              scale_window=True, label=None, title=None, new=True,
              delay_draw=False, offset=0, win=1, _larch=None):
    """
    plot_chik(dgroup, kweight=None, kmax=None, show_window=True, label=None,
              new=True, win=1)

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
     new          bool whether to start a new plot [True]
     delay_draw   bool whether to delay draw until more traces are added [False]
     offset       vertical offset to use for y-array [0]
     win          integer plot window to use [1]

    Notes
    -----
     1. The input data group must have the following attributes:
         k, chi, kwin, filename
    """
    if kweight is None:
        kweight = 0
        xft = getattr(dgroup, 'xftf_details', None)
        if xft is not None:
            kweight = xft.call_args.get('kweight', 0)
        #endif
    #endif

    chi = dgroup.chi * dgroup.k ** kweight
    opts = dict(win=win, show_legend=True, delay_draw=True, linewidth=3,
                _larch=_larch)
    if label is None:
        label = 'chi'
    #endif
    if new:
        title = _get_title(dgroup, title=title)
    _plot(dgroup.k, chi+offset, xlabel=plotlabels.k,
         ylabel=plotlabels.chikw.format(kweight), title=title,
         label=label, zorder=20, new=new, xmax=kmax, **opts)

    if show_window and hasattr(dgroup, 'kwin'):
        kwin = dgroup.kwin
        if scale_window:
            kwin = kwin*max(abs(chi))
        _plot(dgroup.k, kwin+offset, zorder=12, label='window',  **opts)
    #endif
    redraw(win=win, xmax=kmax, _larch=_larch)
#enddef

def plot_chir(dgroup, show_mag=True, show_real=False, show_imag=False,
              show_window=False, rmax=None, label=None, title=None,
              new=True, delay_draw=False, offset=0, win=1, _larch=None):
    """
    plot_chir(dgroup, show_mag=True, show_real=False, show_imag=False,
              rmax=None, label=None, new=True, win=1)

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
     new          bool whether to start a new plot [True]
     delay_draw   bool whether to delay draw until more traces are added [False]
     offset       vertical offset to use for y-array [0]
     win          integer plot window to use [1]

    Notes
    -----
     1. The input data group must have the following attributes:
         r, chir_mag, chir_im, chir_re, kweight, filename
    """

    try:
        kweight = dgroup.xftf_details.call_args['kweight']
    except:
        kweight = 0

    if new:
        title = _get_title(dgroup, title=title)

    opts = dict(win=win, show_legend=True, linewidth=3, title=title,
                zorder=20, xmax=rmax, xlabel=plotlabels.r, new=new,
                delay_draw=True, _larch=_larch)

    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)
    opts['ylabel'] = ylabel

    if label is None:
        label = 'chir'
    #endif
    if show_mag:
        _plot(dgroup.r, dgroup.chir_mag+offset, label='%s (mag)' % label, **opts)
        opts['new'] = False
    #endif
    if show_real:
        _plot(dgroup.r, dgroup.chir_re+offset, label='%s (real)' % label, **opts)
        opts['new'] = False
    #endif
    if show_imag:
        _plot(dgroup.r, dgroup.chir_im+offset, label='%s (imag)' % label, **opts)
    #endif
    if show_window and hasattr(dgroup, 'rwin'):
        rwin = dgroup.rwin * max(dgroup.chir_mag)
        opts['zorder'] = 15
        _plot(dgroup.r, rwin+offset, label='window',  **opts)
    #endif

    if show_mag or show_real or show_imag or show_window:
        redraw(win=win, xmax=rmax, _larch=_larch)
    #endif
#enddef

def plot_chiq(dgroup, kweight=None, kmax=None, show_chik=False, label=None,
              title=None, new=True, delay_draw=False, offset=0, win=1,
              _larch=None):
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
     label        string for label [``None`` to use 'chi']
     title        string for plot title [None, may use filename if available]
     new          bool whether to start a new plot [True]
     delay_draw   bool whether to delay draw until more traces are added [False]
     offset       vertical offset to use for y-array [0]
     win          integer plot window to use [1]

    Notes
    -----
     1. The input data group must have the following attributes:
         k, chi, kwin, filename
    """
    if kweight is None:
        kweight = 0
        xft = getattr(dgroup, 'xftf_details', None)
        if xft is not None:
            kweight = xft.call_args.get('kweight', 0)
        #endif
    #endif
    nk = len(dgroup.k)
    chiq = dgroup.chiq_re[:nk]
    opts = dict(win=win, show_legend=True, delay_draw=True, linewidth=3, _larch=_larch)
    if label is None:
        label = 'chi(q) (filtered)'
    #endif
    if new:
        title = _get_title(dgroup, title=title)

    _plot(dgroup.k, chiq+offset, xlabel=plotlabels.k,
         ylabel=plotlabels.chikw.format(kweight), title=title,
         label=label, zorder=20, new=new, xmax=kmax, **opts)

    if show_chik:
        chik = dgroup.chi * dgroup.k ** kweight
        _plot(dgroup.k, chik+offset, zorder=16, label='chi(k)',  **opts)
    #endif
    redraw(win=win, xmax=kmax, _larch=_larch)
#enddef


def plot_wavelet(dgroup, show_mag=True, show_real=False, show_imag=False,
                 rmax=None, kmax=None, kweight=None, title=None, win=1, _larch=None):
    """
    plot_wavelet(dgroup, show_mag=True, show_real=False, show_imag=False,
              rmax=None, kmax=None, kweight=None, title=None, win=1)

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
     win          integer image window to use [1]

    Notes
    -----
     The wavelet will be performed
    """
    if kweight is None:
        kweight = dgroup.xftf_details.call_args['kweight']

    title = _get_title(dgroup, title=title)

    opts = dict(win=win, title=title, x=dgroup.k, y=dgroup.r, xmax=kmax,
                ymax=rmax, xlabel=plotlabels.k, ylabel=plotlabels.r,
                show_axis=True, _larch=_larch)

    cauchy_wavelet(dgroup, kweight=kweight)
    if show_mag:
        _imshow(dgroup.wcauchy_mag, **opts)
    elif show_real:
        _imshow(dgroup.wcauchy_real, **opts)
    elif show_imag:
        _imshow(dgroup.wcauchy_imag, **opts)
    #endif
#enddef

def plot_chifit(dataset, kmin=0, kmax=None, kweight=None, rmax=None,
                show_mag=True, show_real=False, show_imag=False,
                title=None, new=True, delay_draw=False, offset=0, win=1,
                _larch=None):
    """
    plot_chifit(dataset, kmin=0, kmax=None, rmax=None,
                show_mag=True, show_real=False, show_imag=False,
                new=True, win=1)

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
     new          bool whether to start a new plot [True]
     delay_draw   bool whether to delay draw until more traces are added [False]
     offset       vertical offset to use for y-array [0]
     win          integer plot window to use [1]

    """
    if kweight is None:
        kweight = dataset.transform.kweight
    #endif
    if isinstance(kweight, (list, tuple, ndarray)): kweight=kweight[0]

    data_chik  = dataset.data.chi * dataset.data.k**kweight
    model_chik = dataset.model.chi * dataset.model.k**kweight

    title = _get_title(dataset, title=title)

    opts=dict(labelfontsize=10, legendfontsize=10, linewidth=3,
              show_legend=True, delay_draw=True, win=win, title=title,
              _larch=_larch)

    # k-weighted chi(k) in first plot window
    _plot(dataset.data.k, data_chik+offset, xmin=kmin, xmax=kmax,
            xlabel=plotlabels.k, ylabel=plotlabels.chikw.format(kweight),
            label='data', new=new, **opts)
    _plot(dataset.model.k, model_chik+offset, label='fit',  **opts)
    redraw(win=win, xmin=kmin, xmax=kmax, _larch=_larch)

    # show chi(R) in next plot window
    opts['win'] = win = win+1
    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)

    opts.update(dict(xlabel=plotlabels.r, ylabel=ylabel,
                     xmax=rmax, new=True, show_legend=True))

    if show_mag:
        _plot(dataset.data.r,  dataset.data.chir_mag+offset,
             label='|data|', **opts)
        opts['new'] = False
        _plot(dataset.model.r, dataset.model.chir_mag+offset,
              label='|fit|', **opts)
    #endif
    if show_real:
        _plot(dataset.data.r, dataset.data.chir_re+offset, label='Re[data]', **opts)
        opts['new'] = False
        _plot(dataset.model.r, dataset.model.chir_re+offset, label='Re[fit]',  **opts)
    #endif
    if show_imag:
        _plot(dataset.data.r, dataset.data.chir_im+offset, label='Im[data]', **opts)
        opts['new'] = False
        _plot(dataset.model.r, dataset.model.chir_im+offset, label='Im[fit]',  **opts)
    #endif
    if show_mag or show_real or show_imag:
        redraw(win=opts['win'], xmax=opts['xmax'], _larch=_larch)
    #endif
#enddef

def plot_path_k(dataset, ipath=0, kmin=0, kmax=None, offset=0, label=None,
                new=False, delay_draw=False, win=1, _larch=None, **kws):
    """
    plot_path_k(dataset, ipath, kmin=0, kmax=None, offset=0,
               label=None, new=False, win=1, **kws)

    Plot k-weighted chi(k) for a single Path of a feffit dataset

    Arguments
    ----------
     dataset      feffit dataset, after running feffit()
     ipath        index of path, starting count at 0 [0]
     kmin         min k to show [0]
     kmax         max k to show [None, end of data]
     offset       vertical offset to use for plot [0]
     label        path label ['path %d' % ipath]
     new          bool whether to start a new plot [True]
     delay_draw   bool whether to delay draw until more traces are added [False]
     win          integer plot window to use [1]
     kws          additional keyword arguments are passed to plot()
    """
    kweight = dataset.transform.kweight
    path = dataset.pathlist[ipath]
    if label is None: label = 'path %i' % (1+ipath)

    chi_kw = offset + path.chi * path.k**kweight

    _plot(path.k, chi_kw, label=label, xmin=kmin, xmax=kmax,
         xlabel=plotlabels.k, ylabel=plotlabels.chikw.format(kweight),
         win=win, new=new, delay_draw=delay_draw, _larch=_larch, **kws)
    if delay_draw:
        redraw(win=win, xmin=kmin, xmax=kmax, _larch=_larch)
#enddef

def plot_path_r(dataset, ipath, rmax=None, offset=0, label=None,
                show_mag=True, show_real=False, show_imag=True,
                new=False, delay_draw=False, win=1, _larch=None,
                **kws):
    """
    plot_path_r(dataset, ipath,rmax=None, offset=0, label=None,
                show_mag=True, show_real=False, show_imag=True,
                new=False, win=1, **kws)

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
     new          bool whether to start a new plot [True]
     delay_draw   bool whether to delay draw until more traces are added [False]
     win          integer plot window to use [1]
     kws          additional keyword arguments are passed to plot()
    """
    path = dataset.pathlist[ipath]
    if label is None:
        label = 'path %i' % (1+ipath)
    #endif
    kweight =dataset.transform.kweight
    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)

    opts = dict(xlabel=plotlabels.r, ylabel=ylabel, xmax=rmax, new=new,
                delay_draw=True, _larch=_larch)

    opts.update(kws)
    if show_mag:
        _plot(path.r,  offset+path.chir_mag, label=label, **opts)
        opts['new'] = False
    #endif
    if show_real:
        _plot(path.r,  offset+path.chir_re, label=label, **opts)
        opts['new'] = False
    #endif
    if show_imag:
        _plot(path.r,  offset+path.chir_im, label=label, **opts)
        opts['new'] = False
    #endif
    redraw(win=win, xmax=rmax, _larch=_larch)
#enddef

def plot_paths_k(dataset, offset=-1, kmin=0, kmax=None, title=None,
                 new=True, delay_draw=False, win=1, _larch=None, **kws):

    """
    plot_paths_k(dataset, offset=-1, kmin=0, kmax=None, new=True, win=1, **kws):

    Plot k-weighted chi(k) for model and all paths of a feffit dataset

    Arguments
    ----------
     dataset      feffit dataset, after running feffit()
     kmin         min k to show [0]
     kmax         max k to show [None, end of data]
     offset       vertical offset to use for paths for plot [-1]
     new          bool whether to start a new plot [True]
     title        string for plot title [None, may use filename if available]
     win          integer plot window to use [1]
     delay_draw   bool whether to delay draw until more traces are added [False]
     kws          additional keyword arguments are passed to plot()
    """
    # make k-weighted chi(k)
    kweight = dataset.transform.kweight
    model = dataset.model

    model_chi_kw = model.chi * model.k**kweight

    title = _get_title(dataset, title=title)

    _plot(model.k, model_chi_kw, title=title, label='sum', new=new,
          xlabel=plotlabels.r, ylabel=plotlabels.chikw.format(kweight),
          xmin=kmin, xmax=kmax, win=win, delay_draw=True,_larch=_larch,
          **kws)

    for ipath in range(len(dataset.pathlist)):
        plot_path_k(dataset, ipath, offset=(ipath+1)*offset,
                    kmin=kmin, kmax=kmax, new=False, delay_draw=True,
                    win=win, _larch=_larch)
    #endfor
    redraw(win=win, xmin=kmin, xmax=kmax, _larch=_larch)
#enddef

def plot_paths_r(dataset, offset=-0.25, rmax=None, show_mag=True,
                 show_real=False, show_imag=False, title=None, new=True,
                 win=1, delay_draw=False, _larch=None, **kws):
    """
    plot_paths_r(dataset, offset=-0.5, rmax=None, show_mag=True, show_real=False,
                 show_imag=False, new=True, win=1, **kws):

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
     new          bool whether to start a new plot [True]
     delay_draw   bool whether to delay draw until more traces are added [False]
     win          integer plot window to use [1]
     kws          additional keyword arguments are passed to plot()
    """
    kweight = dataset.transform.kweight
    model = dataset.model

    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)
    title = _get_title(dataset, title=title)
    opts = dict(xlabel=plotlabels.r, ylabel=ylabel, xmax=rmax, new=new,
                delay_draw=True, title=title, _larch=_larch)
    opts.update(kws)
    if show_mag:
        _plot(model.r,  model.chir_mag, label='|sum|', **opts)
        opts['new'] = False
    #endif
    if show_real:
        _plot(model.r,  model.chir_re, label='Re[sum]', **opts)
        opts['new'] = False
    #endif
    if show_imag:
        _plot(model.r,  model.chir_im, label='Im[sum]', **opts)
        opts['new'] = False
    #endif

    for ipath in range(len(dataset.pathlist)):
        plot_path_r(dataset, ipath, offset=(ipath+1)*offset,
                    show_mag=show_mag, show_real=show_real,
                    show_imag=show_imag, **opts)
    #endfor
    redraw(win=win, xmax=rmax,_larch=_larch)
#enddef


def extend_plotrange(x, y, xmin=None, xmax=None, extend=0.10):
    """return plot limits to extend a plot range for x, y pairs"""
    xeps = min(diff(x)) / 5.
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

def plot_prepeaks_baseline(dgroup, subtract_baseline=False, show_fitrange=True,
                           show_peakrange=True, win=1, _larch=None, **kws):
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

    popts = dict(xmin=px0, xmax=px1, ymin=py0, ymax=py1, title=title,
                 xlabel='Energy (eV)', ylabel='mu (normalized)', delay_draw=True,
                 show_legend=True, style='solid', linewidth=3,
                 label='data', new=True,
                 marker='None', markersize=4, win=win, _larch=_larch)
    popts.update(kws)

    ydat = dgroup.ydat
    xdat = dgroup.xdat
    if subtract_baseline:
        xdat = ppeak.energy
        ydat = ppeak.baseline
        popts['label'] = 'baseline subtracted peaks'
        _plot(xdat, ydat, **popts)
    else:
        _plot(xdat, ydat, **popts)
        popts['new'] = False
        popts['label'] = 'baseline'
        _oplot(ppeak.energy, ppeak.baseline, **popts)

    popts = dict(win=win, _larch=_larch, delay_draw=True,
                 label='_nolegend_')

    if show_fitrange:
        for x in (ppeak.emin, ppeak.emax):
            _plot_axvline(x, color='#DDDDCC', **popts)
            _plot_axvline(ppeak.centroid, color='#EECCCC', **popts)

    if show_peakrange:
        for x in (ppeak.elo, ppeak.ehi):
            y = ydat[index_of(xdat, x)]
            _plot_marker(x, y, color='#222255', marker='o', size=8, **popts)

    redraw(win=win, xmin=px0, xmax=px1, ymin=py0, ymax=py1,
           show_legend=True, _larch=_larch)
#enddef

def plot_prepeaks_fit(dgroup, nfit=0, show_init=False, subtract_baseline=False,
                      show_residual=False, win=1, _larch=None):
    """plot pre-edge peak fit, as from XAS Viewer

    dgroup must have a 'peakfit_history' attribute
    """
    if not hasattr(dgroup, 'prepeaks'):
        raise ValueError('Group needs prepeaks')
    #endif
    if show_init:
        result = dgroup.prepeaks
    else:
        result = getattr(dgroup.prepeaks, 'fit_history', None)
        if nfit > len(result):
            nfit = 0
        result = result[nfit]
    #endif

    if result is None:
        raise ValueError('Group needs prepeaks.fit_history or init_fit')
    #endif

    opts = result.user_options
    xeps = min(diff(dgroup.xdat)) / 5.
    xdat = 1.0*result.energy
    ydat = 1.0*result.norm

    xdat_full = 1.0*dgroup.xdat
    ydat_full = 1.0*dgroup.ydat

    if show_init:
        yfit   = 1.0*result.init_fit
        ycomps = None
        ylabel = 'model'
    else:
        yfit   = 1.0*result.best_fit
        ycomps = result.ycomps
        ylabel = 'best fit'

    baseline = 0.*ydat
    if ycomps is not None:
        for label, ycomp in ycomps.items():
            if label in opts['bkg_components']:
                baseline += ycomp

    plotopts = dict(title='%s:\npre-edge peak' % dgroup.filename,
                    xlabel='Energy (eV)', ylabel=opts['array_desc'],
                    delay_draw=True, show_legend=True, style='solid',
                    linewidth=3, marker='None', markersize=4)

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
    popts = {'win': win, '_larch': _larch}
    plotopts.update(popts)
    if show_residual:
        popts['stacked'] = True
        _fitplot(xdat, ydat, yfit, label='data', label2=ylabel, **plotopts)
    else:
        _plot(xdat_full, ydat_full, new=True, label='data',
              color=LineColors[0], **plotopts)
        _oplot(xdat, yfit, label=ylabel, color=LineColors[1], **plotopts)
        ncolor = 1

    if ycomps is not None:
        ncomps = len(ycomps)
        if not subtract_baseline:
            ncolor += 1
            _oplot(xdat, baseline, label='baseline', delay_draw=True,
                   style='short dashed', marker='None', markersize=5,
                   color=LineColors[ncolor], **popts)

        for icomp, label in enumerate(ycomps):
            ycomp = ycomps[label]
            if label in opts['bkg_components']:
                continue
            ncolor =  (ncolor+1) % 10
            _oplot(xdat, ycomp, label=label, delay_draw=(icomp != ncomps-1),
                   style='short dashed', marker='None', markersize=5,
                   color=LineColors[ncolor], **popts)

    if opts.get('show_fitrange', False):
        for attr in ('emin', 'emax'):
            _plot_axvline(opts[attr], ymin=0, ymax=1,
                          delay_draw=False, color='#DDDDCC',
                          label='_nolegend_', **popts)

    if opts.get('show_centroid', False):
        pcen = getattr(dgroup.prepeaks, 'centroid', None)
        if hasattr(result, 'params'):
            pcen = result.params.get('fit_centroid', None)
            if pcen is not None:
                pcen = pcen.value
        if pcen is not None:
            _plot_axvline(pcen, delay_draw=False, ymin=0, ymax=1,
                          color='#EECCCC', label='_nolegend_', **popts)

    redraw(win=win, xmin=dx0, xmax=dx1, ymin=min(dy0, fy0),
           ymax=max(dy1, fy1), show_legend=True, _larch=_larch)

def _pca_ncomps(result, min_weight=0, ncomps=None):
    if ncomps is None:
        if min_weight > 1.e-12:
            ncomps = where(result.variances < min_weight)[0][0]
        else:
            ncomps = argmin(result.ind)
    return ncomps - 1


def plot_pca_components(result, min_weight=0, ncomps=None, win=1, _larch=None, **kws):
    """Plot components from PCA result

    result must be output of `pca_train`
    """
    title = "PCA components"
    popts = dict(xmin=result.xmin, xmax=result.xmax, title=title,
                 xlabel=plotlabels.energy, ylabel=plotlabels.norm,
                 delay_draw=True, show_legend=True, style='solid',
                 linewidth=3, new=True, marker='None', markersize=4,
                 win=win, _larch=_larch)

    popts.update(kws)
    ncomps = _pca_ncomps(result, min_weight=min_weight, ncomps=ncomps)

    _plot(result.x, result.mean, label='Mean', **popts)
    for i, comp in enumerate(result.components[:ncomps+1]):
        label = 'Comp# %d (%.4f)' % (i+1, result.variances[i])
        _oplot(result.x, comp, label=label, **popts)

    redraw(win=win, show_legend=True, _larch=_larch)

def plot_pca_weights(result, min_weight=0, ncomps=None, win=1, _larch=None, **kws):
    """Plot component weights from PCA result (aka SCREE plot)

    result must be output of `pca_train`
    """
    max_comps = len(result.components)

    title = "PCA Variances (SCREE) and Indicator Values"

    popts = dict(title=title, xlabel='Component #', zorder=10,
                 xmax=max_comps+1.5, xmin=0.25, ymax=1, ylabel='variance',
                 style='solid', ylog_scale=True, show_legend=True,
                 linewidth=1, new=True, marker='o', win=win, _larch=_larch)

    popts.update(kws)

    ncomps = _pca_ncomps(result, min_weight=min_weight, ncomps=ncomps)

    x = 1 + arange(ncomps)
    y = result.variances[:ncomps]
    _plot(x, y, label='significant', **popts)

    xe = 1 + arange(ncomps-1, max_comps)
    ye = result.variances[ncomps-1:ncomps+max_comps]

    popts.update(dict(new=False, zorder=5, style='short dashed',
                      color='#B34050', ymin=2.e-3*result.variances[ncomps]))
    _plot(xe, ye, label='not significant', **popts)

    xi = 1 + arange(len(result.ind)-2)

    _plot(xi, result.ind[1:len(xi)+1], zorder=15, y2label='Indicator Value',
          label='IND', style='solid', win=win, show_legend=True,
          linewidth=1, marker='o', side='right', _larch=_larch)



def plot_pca_fit(dgroup, win=1, with_components=False, _larch=None, **kws):
    """Plot data and fit result from pca_fit, which rom PCA result

    result must be output of `pca_fit`
    """

    title = "PCA fit: %s" % (dgroup.filename)
    result = dgroup.pca_result
    model = result.pca_model

    popts = dict(xmin=model.xmin, xmax=model.xmax, title=title,
                 xlabel=plotlabels.energy, ylabel=plotlabels.norm,
                 delay_draw=True, show_legend=True, style='solid',
                 linewidth=3, new=True, marker='None', markersize=4,
                 stacked=True, win=win, _larch=_larch)
    popts.update(kws)
    _fitplot(result.x, result.ydat, result.yfit,
             label='data', label2='PCA fit', **popts)

    disp = _getDisplay(win=win, stacked=True, _larch=_larch)
    if with_components and disp is not None:
        disp.panel.oplot(result.x, model.mean, label='mean')
        for n in range(len(result.weights)):
            cval = model.components[n]*result.weights[n]
            disp.panel.oplot(result.x, cval, label='Comp #%d' % (n+1))
    redraw(win=win, show_legend=True, stacked=True, _larch=_larch)

def plot_diffkk(dgroup, emin=None, emax=None, new=True, label=None,
                title=None, delay_draw=False, offset=0, win=1, _larch=None):
    """
    plot_diffkk(dgroup, norm=True, emin=None, emax=None, show_e0=False, label=None, new=True, win=1):

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
     new         bool whether to start a new plot [True]
     delay_draw  bool whether to delay draw until more traces are added [False]
     offset      vertical offset to use for y-array [0]
     win         integer plot window to use [1]

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

    opts = dict(win=win, show_legend=True, linewidth=3,
                delay_draw=True, _larch=_larch)

    _plot(dgroup.energy, f2, xlabel=plotlabels.energy, ylabel=ylabel,
          title=title, label=labels['f2'], zorder=20, new=new, xmin=emin, xmax=emax,
          **opts)
    zorder = 15
    for attr in ('fpp', 'f1', 'fp'):
        yval = getattr(dgroup, attr)
        if yval is not None:
            _plot(dgroup.energy, yval, zorder=zorder, label=labels[attr], **opts)
            zorder = zorder - 3

    redraw(win=win, xmin=emin, xmax=emax, _larch=_larch)
#enddef

def plot_feffdat(feffpath, with_phase=True, title=None,
                 new=True, delay_draw=False, win=1, _larch=None):
    """
    plot_feffdat(feffpath, with_phase=True, title=None, new=True, win=1):

    Plot Feff's magnitude and phase as a function of k for a FeffPath

    Arguments
    ----------
     feffpath    feff path as read by feffpath()
     with_pase   whether to plot phase(k) as well as magnitude [True]
     title       string for plot title [None, may use filename if available]
     new         bool whether to start a new plot [True]
     delay_draw  bool whether to delay draw until more traces are added [False]
     win         integer plot window to use [1]

    Notes
    -----
     1. The input data group must have the following attributes:
         energy, mu, bkg, norm, e0, pre_edge, edge_step, filename
    """
    if hasattr(feffpath, '_feffdat'):
        fdat = feffpath._feffdat
    else:
        raise ValueError("must pass in a Feff path as from feffpath()")
    #endif

    _plot(fdat.k, fdat.mag_feff, xlabel=plotlabels.k,
          ylabel='|F(k)|', title=title, label='magnitude', zorder=20,
          new=new, win=win, show_legend=True,
          delay_draw=delay_draw, linewidth=3, _larch=_larch)

    if with_phase:
        _plot(fdat.k, fdat.pha_feff, xlabel=plotlabels.k,
              y2label='Phase(k)', title=title, label='phase', side='right',
              zorder=10, new=False, win=win, show_legend=True,
              delay_draw=delay_draw, linewidth=3, _larch=_larch)
    #endif

    if delay_draw:
        redraw(win=win, xmin=emin, xmax=emax, _larch=_larch)
#enddef
