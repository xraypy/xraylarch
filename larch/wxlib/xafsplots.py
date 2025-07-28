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

from pathlib import Path
from numpy import ndarray, diff, where, arange, argmin
from matplotlib.ticker import FuncFormatter

from larch import Group
from larch.math import index_of
from larch.xafs import cauchy_wavelet, etok

try:
    import wx
    HAS_WXPYTHON = True
except ImportError:
    HAS_WXPYTHON = False

if HAS_WXPYTHON:
    from .plotter import (get_display, _plot, _oplot,  _fitplot,
                         _plot_marker, _plot_axvline, _imshow)
else:
    get_display = _plot = _oplot = None
    _fitplot = _plot_marker = _plot_axvline = None

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
    if show_mag:
        ylab.append(plotlabels.chirmag)
    if show_real:
        ylab.append(plotlabels.chirre)
    if show_imag:
        ylab.append(plotlabels.chirim)
    if len(ylab) > 1:
        ylab = [plotlabels.chir]
    return ylab[0].format(kweight+1)
#enddef

plotlabels = Group(k       = r'$k \rm\,(\AA^{-1})$',
                   r       = r'$R \rm\,(\AA)$',
                   energy  = r'$E\rm\,(eV)$',
                   en_e0   = r'$E-E_{0}\rm\,(eV)$',
                   en_e0val = r'$E-E_0 \rm\,(eV)\rm\,\,\,  [E_0={0:.2f}]$',
                   ewithk  = r'$E\rm\,(eV)$' + '\n' + r'$[k \rm\,(\AA^{-1})]$',
                   i0      = r'$I_0(E)$',
                   mu      = r'$\mu(E)$',
                   norm    = r'normalized $\mu(E)$',
                   flat    = r'flattened $\mu(E)$',
                   deconv  = r'deconvolved $\mu(E)$',
                   dmude   = r'$d\mu_{\rm norm}(E)/dE$',
                   d2mude  = r'$d^2\mu_{\rm norm}(E)/dE^2$',
                   chie    = r'$\chi(E)$',
                   chie0   = r'$\chi(E)$',
                   chie1   = r'$E\chi(E) \rm\, (eV)$',
                   chiew   = r'$E^{{{0:g}}}\chi(E) \rm\,(eV^{{{0:g}}})$',
                   chikw   = r'$k^{{{0:g}}}\chi(k) \rm\,(\AA^{{-{0:g}}})$',
                   chi0    = r'$\chi(k)$',
                   chi1    = r'$k\chi(k) \rm\,(\AA^{-1})$',
                   chi2    = r'$k^2\chi(k) \rm\,(\AA^{-2})$',
                   chi3    = r'$k^3\chi(k) \rm\,(\AA^{-3})$',
                   chir    = r'$\chi(R) \rm\,(\AA^{{-{0:g}}})$',
                   chirmag = r'$|\chi(R)| \rm\,(\AA^{{-{0:g}}})$',
                   chirre  = r'${{\rm Re}}[\chi(R)] \rm\,(\AA^{{-{0:g}}})$',
                   chirim  = r'${{\rm Im}}[\chi(R)] \rm\,(\AA^{{-{0:g}}})$',
                   chirpha = r'${{\rm Phase}}[\chi(R)] \rm\,(\AA^{{-{0:g}}})$',
                   e0color = '#B2B282',
                   chirlab = chirlab,
                   x = r'$x$',
                   y = r'$y$',
                   xdat = r'$x$',
                   ydat = r'$y$',
                   xplot = r'$x$',
                   yplot= r'$y$',
                   ynorm = r'scaled $y$',
                   xshift = r'shifted $x$',
                   dydx = r'$dy/dx$',
                   d2ydx = r'$d^2y/dx^2$',
                       )

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
                t = '/'.join(Path(t).absolute().parts[-2:])
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


def _get_erange(dgroup, emin=None, emax=None, e0=None):
    """get absolute emin/emax for data range, allowing using
    values relative to e0.
    """
    dat_emin = float(min(dgroup.energy)) - 25
    dat_emax = float(max(dgroup.energy)) + 25
    if e0 is None or e0 < dat_emin or e0 > dat_emax:
        e0 = getattr(dgroup, 'e0', 0.0)
    if emin is not None:
        emin = max(emin+e0, dat_emin)
    if emax is not None:
        emax = min(emax+e0, dat_emax)
    return emin, emax
#enddef

def redraw(win=1, xmin=None, xmax=None, ymin=None, ymax=None,
           dymin=None, dymax=None,
           show_legend=True, stacked=False, _larch=None):
    disp = get_display(win=win, stacked=stacked, _larch=_larch)
    if disp is None:
        return
    panel = disp.panel
    panel.conf.show_legend = show_legend
    if (xmin is not None or xmax is not None or
        ymin is not None or ymax is not None):
        panel.set_xylims((xmin, xmax, ymin, ymax))
        if stacked:
            disp.panel_bot.set_xylims((xmin, xmax, dymin, dymax))
    panel.unzoom_all()
    panel.reset_formats()
    if stacked:
        disp.panel_bot.unzoom_all()
        disp.panel_bot.reset_formats()
    if show_legend:  # note: draw_legend *will* redraw the canvas
        panel.conf.draw_legend()
    else:
        panel.canvas.draw()
        if stacked:
            disp.panel_bot.canvas.draw()

    #endif
#enddef

def plot_mu(dgroup, show_norm=False, show_flat=False,
            show_deriv=False, show_e0=False, show_pre=False,
            show_post=False, with_deriv=False, with_deriv2=False,
            with_i0=False, with_norm=False, with_mback=False,
            emin=None, emax=None, marker_energies=None,
            markerstyle='marker', label=None, new=True,
            delay_draw=False, offset=0, en_offset=0, title=None,
            win=1, _larch=None):
    """
    plot_mu(dgroup, norm=False, deriv=False, show_pre=False, show_post=False,
             show_e0=False, show_deriv=False, emin=None, emax=None, label=None,
             new=True, win=1)

    Plot mu(E) for an XAFS data group in various forms

    Arguments
    ----------
     dgroup        group of XAFS data after pre_edge() results (see Note 1)
     show_norm     bool whether to show normalized data [False]
     show_flat     bool whether to show flattened, normalized data [False]
     show_deriv    bool whether to show derivative of normalized data [False]
     show_pre      bool whether to show pre-edge curve [False]
     show_post     bool whether to show post-edge curve [False]
     show_e0       bool whether to show E0 [False]
     with_i0       bool whether to show I0 together with mu [False]
     with_deriv    bool whether to show deriv (dmu/de) together with mu [False]
     with_deriv2   bool whether to show 2nd deriv together with mu [False]
     with_norm     bool whether to show normalized data with mu [False]
     with_mback    bool whether to show MBACK tabulated background with mu [False]
     emin          min energy to show, absolute or relative to E0 [None, start of data]
     emax          max energy to show, absolute or relative to E0 [None, end of data]
     marker_energies list of energies (relative to e0!) to show markers [None]
     markerstyle   how to show e0, pre/post ranges  ['vline', 'marker']
     label         string for label [None:  'mu', `dmu/dE', or 'mu norm']
     title         string for plot title [None, may use filename if available]
     new           bool whether to start a new plot [True]
     delay_draw    bool whether to delay draw until more traces are added [False]
     offset        vertical offset to *add* to the y-array [0]
     en_offset     energy offset to *subtract* from for x-array [0]
     win           integer plot window to use [1]

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

    mode = 'raw'
    ylabel = plotlabels.mu
    if label is None:
        label = getattr(dgroup, 'filename', 'mu')

    if show_deriv:
        mode = 'deriv'
        mu = dgroup.dmude
    elif show_norm:
        mode  = 'norm'
        mu = dgroup.norm
    elif show_flat:
        mode = 'flat'
        mu = dgroup.flat
    if mode != 'raw':
        ylabel = f"{ylabel} ({mode})"

    if en_offset in (None, 0):
        emin, emax = _get_erange(dgroup, emin, emax, e0=en_offset)

    title = _get_title(dgroup, title=title)

    opts = dict(win=win, show_legend=True, linewidth=3,
                title=title, xmin=emin, xmax=emax, zorder=20,
                delay_draw=True, _larch=_larch)

    _plot(dgroup.energy-en_offset, mu+offset, xlabel=plotlabels.energy, ylabel=ylabel,
          label=label, new=new, **opts)

    if show_pre and mode=='raw':
        _plot(dgroup.energy-en_offset, dgroup.pre_edge+offset, label='pre_edge',
                 **opts)

    if show_post and mode in ('raw', 'norm'):
        post = dgroup.post_edge*1.0
        if mode=='norm':
            post = (post - dgroup.pre_edge) / dgroup.edge_step
        _plot(dgroup.energy-en_offset, post+offset, label='post_edge', **opts)

    yaxes = 1
    if with_i0:
        i0 = getattr(dgroup, 'i0', None)
        if i0 is not None:
            yaxes += 1
            opts['yaxes'] = yaxes
            opts['label'] = f'{label} (I_0)'
            opts[f'y{yaxes}label'] = plotlabels.i0
            _plot(dgroup.energy-en_offset, i0+offset, **opts)

    if with_deriv:
        dmu = dgroup.dmude
        yaxes += 1
        opts['yaxes'] = yaxes
        opts['label'] = f'{label} (deriv)'
        opts[f'y{yaxes}label'] = plotlabels.dmude
        _plot(dgroup.energy-en_offset, dmu+offset, **opts)

    if with_deriv2:
        dmu2 = dgroup.d2mude
        yaxes += 1
        opts['yaxes'] = yaxes
        opts['label'] = f'{label} (2nd deriv)'
        opts[f'y{yaxes}label'] = plotlabels.d2mude
        _plot(dgroup.energy-en_offset, dmu2+offset, **opts)

    if with_norm and mode!='norm':
        yaxes += 1
        opts['yaxes'] = yaxes
        opts['label'] = f'{label} (norm)'
        opts[f'y{yaxes}label'] = plotlabels.norm
        _plot(dgroup.energy-en_offset, dgroup.norm+offset, **opts)

    if with_mback:
        mback = getattr(dgroup, 'mback_mu', None)
        if mback is not None:
            opts['label'] = f'{label} (MBACK mu)'
            if mode in ('norm', 'flat'):
                mback = (mback - dgroup.pre_edge)/dgroup.edge_step
                opts['label'] = f'{label} (MBACK mu, norm)'
            _plot(dgroup.energy-en_offset, mback+offset, **opts)

    marker_popts = {'marker': 'o', 'markersize': 5, 'label': '_nolegend_',
                    'markerfacecolor': '#888', 'markeredgecolor': '#A00'}
    disp = get_display(win=win, _larch=_larch)
    axes = disp.panel.axes
    if show_e0:
        if 'vli'in markerstyle.lower():
            _plot_axvline(dgroup.e0-en_offset, zorder=2, size=3, win=win,
                          label='__nolegend__',color=plotlabels.e0color,
                          _larch=_larch)
        else:
            ie0 = index_of(dgroup.energy, dgroup.e0)
            axes.plot([dgroup.e0-en_offset], [mu[ie0]+offset], **marker_popts)

    if marker_energies is None:
        marker_energies = []
    for _mark_en in marker_energies:
        ex = dgroup.e0 + _mark_en
        if 'vli'in markerstyle.lower():
            _plot_axvline(ex-en_offset, zorder=2, size=3, win=win,
                          label='__nolegend__',color=plotlabels.e0color,
                          _larch=_larch)
        else:
            ix = index_of(dgroup.energy, ex)
            axes.plot([ex-en_offset], [mu[ix]+offset], **marker_popts)
    redraw(win=win, xmin=emin, xmax=emax, _larch=_larch)

def plot_bkg(dgroup, norm=True, emin=None, emax=None, show_e0=False, show_ek0=False,
             label=None, title=None, new=True, delay_draw=False, offset=0, en_offset=0,
             win=1, _larch=None):
    """
    plot_bkg(dgroup, norm=True, emin=None, emax=None, show_e0=False, label=None, new=True, win=1):

    Plot mu(E) and background mu0(E) for XAFS data group

    Arguments
    ----------
     dgroup      group of XAFS data after autobk() results (see Note 1)
     norm        bool whether to show normalized data [True]
     emin        min energy to show, absolute or relative to E0 [None, start of data]
     emax        max energy to show, absolute or relative to E0 [None, end of data]
     show_e0     bool whether to show E0 [False]
     show_ek0    bool whether to show EK0 [False]
     label       string for label [``None``: 'mu']
     title       string for plot titlte [None, may use filename if available]
     new         bool whether to start a new plot [True]
     delay_draw  bool whether to delay draw until more traces are added [False]
     offset      vertical offset to *add* to the y-array [0]
     en_offset   energy offset to *subtract* from for x-array [0]
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
    _plot(dgroup.energy-en_offset, mu+offset, xlabel=plotlabels.energy, ylabel=ylabel,
         title=title, label=label, zorder=20, new=new, xmin=emin, xmax=emax,
         **opts)
    ymin, ymax = None, None
    disp = get_display(win=win, _larch=_larch)
    if disp is not  None:
        xylims = disp.panel.get_viewlimits()
        ymin, ymax = xylims[2], xylims[3]
    _plot(dgroup.energy-en_offset, bkg+offset, zorder=18, label='bkg', **opts)

    e0val = None
    if show_e0 and hasattr(dgroup, 'e0'):
        e0val = dgroup.e0
    elif show_ek0 and hasattr(dgroup, 'ek0'):
        e0val = dgroup.ek0

    if e0val is not None:
        ie0 = index_of(dgroup.energy, e0val)
        ee0 = dgroup.energy[ie0] - en_offset
        me0 = mu[ie0] + offset
        disp.panel.axes.plot([ee0], [me0], marker='o',
                             markersize=5, label='_nolegend_',
                             markerfacecolor='#808080',
                             markeredgecolor='#A03030')

        if disp is not None:
            disp.panel.conf.draw_legend()
    #endif
    redraw(win=win, xmin=emin, xmax=emax, _larch=_larch)
#enddef

def plot_chie(dgroup, emin=-5, emax=None, label=None, title=None,
              eweight=0, show_k=True, new=True, delay_draw=False,
              offset=0, show_ek0=False, win=1, _larch=None):
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
     eweight     energy weightingn for energisdef es>e0  [0]
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
    chie = mu - dgroup.bkg
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
            s = '\n[%.2f]' % (etok(ex))
        return r"%1.4g%s" % (x, s)

    _plot(dgroup.energy-e0, chie+offset, xlabel=xlabel, ylabel=ylabel,
          title=title, label=label, zorder=20, new=new, xmin=emin,
          xmax=emax, win=win, show_legend=True, delay_draw=delay_draw,
          linewidth=3, _larch=_larch)

    if show_k:
        disp = get_display(win=win, _larch=_larch)
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
    kweight = _get_kweight(dgroup, kweight)

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
            kwin *= max(abs(chi))
        _plot(dgroup.k, kwin+offset, zorder=12, label='window',  **opts)
    #endif
    redraw(win=win, xmax=kmax, _larch=_larch)
#enddef

def plot_chir(dgroup, show_mag=True, show_real=False, show_imag=False,
              show_window=False, scale_window=True, rmax=None, label=None, title=None,
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
     scale_window bool whether to scale k-window to max |chi(R)| [True]
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
    kweight = _get_kweight(dgroup, None)

    if new:
        title = _get_title(dgroup, title=title)

    opts = dict(win=win, show_legend=True, linewidth=3, title=title,
                zorder=20, xmax=rmax, xlabel=plotlabels.r, new=new,
                delay_draw=True, _larch=_larch)

    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)
    opts['ylabel'] = ylabel
    if not hasattr(dgroup, 'r'):
        print("group does not have chi(R) data")
        return
    #endif
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
        rwin = dgroup.rwin
        if scale_window:
            rwin *= max(dgroup.chir_mag)
        opts['zorder'] = 15
        _plot(dgroup.r, rwin+offset, label='window',  **opts)
    #endif

    if show_mag or show_real or show_imag or show_window:
        redraw(win=win, xmax=rmax, _larch=_larch)
    #endif
#enddef

def plot_chiq(dgroup, kweight=None, kmax=None, show_chik=False, label=None,
              title=None, new=True, delay_draw=False, offset=0, win=1,
              show_window=False, scale_window=True, _larch=None):
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
     new          bool whether to start a new plot [True]
     delay_draw   bool whether to delay draw until more traces are added [False]
     offset       vertical offset to use for y-array [0]
     win          integer plot window to use [1]

    Notes
    -----
     1. The input data group must have the following attributes:
         k, chi, kwin, filename
    """
    kweight = _get_kweight(dgroup, kweight)
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
    if show_window and hasattr(dgroup, 'kwin'):
        kwin = dgroup.kwin
        if scale_window:
            kwin = kwin*max(abs(chiq))
        _plot(dgroup.k, kwin+offset, zorder=12, label='window',  **opts)
    #endif

    redraw(win=win, xmax=kmax, _larch=_larch)
#enddef


def plot_wavelet(dgroup, show_mag=True, show_real=False, show_imag=False,
                 rmax=None, kmax=None, kweight=None, title=None, win=1,
                 _larch=None, **kws):
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
    kweight = _get_kweight(dgroup, kweight)
    cauchy_wavelet(dgroup, kweight=kweight, rmax_out=rmax)
    title = _get_title(dgroup, title=title)

    opts = dict(win=win, title=title, x=dgroup.k, y=dgroup.wcauchy_r, xmax=kmax,
                ymax=rmax, xlabel=plotlabels.k, ylabel=plotlabels.r,
                show_axis=True, _larch=_larch)
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
                show_bkg=False, use_rebkg=False, title=None, new=True,
                delay_draw=False, offset=0, win=1, _larch=None):

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
     show_bkg     bool whether to plot feffit-refined background [False]
     use_rebkg    bool whether to plot data with feffit-refined background [False]
     title        string for plot title [None, may use filename if available]
     new          bool whether to start a new plot [True]
     delay_draw   bool whether to delay draw until more traces are added [False]
     offset       vertical offset to use for y-array [0]
     win          integer plot window to use [1]

    """
    if kweight is None:
        kweight = dataset.transform.kweight
    #endif
    if isinstance(kweight, (list, tuple, ndarray)):
        kweight=kweight[0]

    title = _get_title(dataset, title=title)

    mod = dataset.model
    dat = dataset.data
    if use_rebkg and hasattr(dataset, 'data_rebkg'):
        dat = dataset.data_rebkg
        title += ' (refined bkg)'

    data_chik  = dat.chi * dat.k**kweight
    model_chik = mod.chi * mod.k**kweight

    opts=dict(labelfontsize=10, legendfontsize=10, linewidth=3,
              show_legend=True, delay_draw=True, win=win, title=title,
              _larch=_larch)

    # k-weighted chi(k) in first plot window
    _plot(dat.k, data_chik+offset, xmin=kmin, xmax=kmax,
          xlabel=plotlabels.k, ylabel=plotlabels.chikw.format(kweight),
          label='data', new=new, **opts)
    _plot(mod.k, model_chik+offset, label='fit',  **opts)

    if show_bkg and hasattr(dat, 'bkgk'):
        _plot(dat.k, dat.bkgk*dat.k**kweight,
              label='refined bkg', **opts)
    #endif

    redraw(win=win, xmin=kmin, xmax=kmax, _larch=_larch)

    # show chi(R) in next plot window
    opts['win'] = win = win+1
    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)

    opts.update(dict(xlabel=plotlabels.r, ylabel=ylabel,
                     xmax=rmax, new=True, show_legend=True))

    if show_mag:
        _plot(dat.r, dat.chir_mag+offset, label='|data|', **opts)
        opts['new'] = False
        _plot(mod.r, mod.chir_mag+offset,  label='|fit|', **opts)
    #endif
    if show_real:
        _plot(dat.r, dat.chir_re+offset, label='Re[data]', **opts)
        opts['new'] = False
        _plot(mod.r, mod.chir_re+offset, label='Re[fit]',  **opts)
    #endif
    if show_imag:
        _plot(dat.r, dat.chir_im+offset, label='Im[data]', **opts)
        opts['new'] = False
        _plot(mod.r, mod.chir_im+offset, label='Im[fit]',  **opts)
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
    if label is None:
        label = 'path %i' % (1+ipath)

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

    yplot = getattr(dgroup, 'yplot', getattr(dgroup, 'ydat', None))
    xplot = getattr(dgroup, 'xplot', getattr(dgroup, 'x', None))

    px0, px1, py0, py1 = extend_plotrange(xplot, yplot,
                                          xmin=ppeak.emin, xmax=ppeak.emax)

    title = "pre_edge baseline\n %s" % dgroup.filename

    popts = dict(xmin=px0, xmax=px1, ymin=py0, ymax=py1, title=title,
                 xlabel='Energy (eV)', ylabel='mu (normalized)', delay_draw=True,
                 show_legend=True, style='solid', linewidth=3,
                 label='data', new=True,
                 marker='None', markersize=4, win=win, _larch=_larch)
    popts.update(kws)

    if subtract_baseline:
        xplot = ppeak.energy
        yplot = ppeak.baseline
        popts['label'] = 'baseline subtracted peaks'
        _plot(xplot, yplot, **popts)
    else:
        _plot(xplot, yplot, **popts)
        popts['new'] = False
        popts['label'] = 'baseline'
        _oplot(ppeak.energy, ppeak.baseline, **popts)

    popts = dict(win=win, _larch=_larch, delay_draw=True,
                 label='_nolegend_')

    if show_fitrange:
        for x in (ppeak.emin, ppeak.emax):
            _plot_axvline(x, color='#888888', **popts)
            _plot_axvline(ppeak.centroid, color='#EECCCC', **popts)

    if show_peakrange:
        for x in (ppeak.elo, ppeak.ehi):
            _plot_axvline(x, color='#DDDDDD', **popts)
            y = yplot[index_of(xplot, x)]
            _plot_marker(x, y, color='#DDDDDD', marker='o', size=5, **popts)

    redraw(win=win, xmin=px0, xmax=px1, ymin=py0, ymax=py1,
           show_legend=True, _larch=_larch)

def plot_prepeaks_fit(dgroup, nfit=0, show_init=False, subtract_baseline=False,
                      show_residual=False, win=1, _larch=None):
    """plot pre-edge peak fit, as from XAS Viewer

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
    xplot = 1.0*pkfit.energy
    yplot = 1.0*pkfit.norm

    xplot_full = 1.0*dgroup.xplot
    yplot_full = 1.0*dgroup.yplot

    if show_init:
        yfit   = pkfit.init_fit
        ycomps = None #  pkfit.init_ycomps
        ylabel = 'model'
    else:
        yfit   = 1.0*result.best_fit
        ycomps = pkfit.ycomps
        ylabel = 'best fit'

    baseline = 0.*yplot
    if ycomps is not None:
        for label, ycomp in ycomps.items():
            if label in opts['bkg_components']:
                baseline += ycomp

    plotopts = dict(title='%s:\npre-edge peak' % dgroup.filename,
                    xlabel='Energy (eV)', ylabel=opts['array_desc'],
                    delay_draw=True, show_legend=True, style='solid',
                    linewidth=3, marker='None', markersize=4)

    if subtract_baseline:
        yplot -= baseline
        yfit -= baseline
        yplot_full = 1.0*yplot
        xplot_full = 1.0*xplot
        plotopts['ylabel'] = '%s-baseline' % plotopts['ylabel']

    dx0, dx1, dy0, dy1 = extend_plotrange(xplot_full, yplot_full,
                                          xmin=opts['emin'], xmax=opts['emax'])
    _1, _2, fy0, fy1 = extend_plotrange(xplot, yfit,
                                          xmin=opts['emin'], xmax=opts['emax'])

    ncolor = 0
    popts = {'win': win, '_larch': _larch}
    plotopts.update(popts)
    dymin = dymax = None
    if show_residual:
        popts['stacked'] = True
        _fitplot(xplot, yplot, yfit, label='data', label2=ylabel, **plotopts)
        dy = yfit - yplot
        dymax, dymin = dy.max(), dy.min()
        dymax += 0.05 * (dymax - dymin)
        dymin -= 0.05 * (dymax - dymin)
    else:
        _plot(xplot_full, yplot_full, new=True, label='data',
              color=LineColors[0], **plotopts)
        _oplot(xplot, yfit, label=ylabel, color=LineColors[1], **plotopts)
        ncolor = 1

    if ycomps is not None:
        ncomps = len(ycomps)
        if not subtract_baseline:
            ncolor += 1
            _oplot(xplot, baseline, label='baseline', delay_draw=True,
                   style='short dashed', marker='None', markersize=5,
                   color=LineColors[ncolor], **popts)

        for icomp, label in enumerate(ycomps):
            ycomp = ycomps[label]
            if label in opts['bkg_components']:
                continue
            ncolor =  (ncolor+1) % 10
            _oplot(xplot, ycomp, label=label, delay_draw=(icomp != ncomps-1),
                   style='short dashed', marker='None', markersize=5,
                   color=LineColors[ncolor], **popts)

    if opts.get('show_fitrange', False):
        for attr in ('emin', 'emax'):
            _plot_axvline(opts[attr], ymin=0, ymax=1,
                          delay_draw=False, color='#888888',
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

    redraw(xmin=dx0, xmax=dx1, ymin=min(dy0, fy0),
           ymax=max(dy1, fy1), dymin=dymin, dymax=dymax, show_legend=True, **popts)

def _pca_ncomps(result, min_weight=0, ncomps=None):
    if ncomps is None:
        if min_weight > 1.e-12:
            ncomps = where(result.variances < min_weight)[0][0]
        else:
            ncomps = argmin(result.ind)
    return ncomps


def plot_pca_components(result, min_variance=1.e-5, win=1, _larch=None, **kws):
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


    _plot(result.x, result.mean, label='Mean', **popts)
    for i, comp in enumerate(result.components):
        if result.variances[i] > min_variance:
            label = 'Comp# %d (%.4f)' % (i+1, result.variances[i])
            _oplot(result.x, comp, label=label, **popts)

    redraw(win=win, show_legend=True, _larch=_larch)

def plot_pca_weights(result, win=1, _larch=None, **kws):
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

    ncomps = max(1, int(result.nsig))
    x = 1 + arange(ncomps)
    y = result.variances[:ncomps]
    _plot(x, y, label='significant', **popts)

    xe = 1 + arange(ncomps-1, max_comps)
    ye = result.variances[ncomps-1:ncomps+max_comps]

    popts.update(dict(new=False, zorder=5, style='short dashed',
                      color='#B34050', ymin=2e-3*result.variances[ncomps-1]))
    _plot(xe, ye, label='not significant', **popts)

    xi = 1 + arange(len(result.ind)-1)

    _plot(xi, result.ind[1:], zorder=15, y2label='Indicator Value',
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
    yplot = getattr(result, 'yplot', getattr(result, 'ydat', None))
    if yplot is None:
        raise ValueError('cannot find y data for PCA plot')

    _fitplot(result.x, yplot, result.yfit,
             label='data', label2='PCA fit', **popts)

    disp = get_display(win=win, stacked=True, _larch=_larch)
    if with_components and disp is not None:
        disp.panel.oplot(result.x, model.mean, label='mean')
        for n in range(len(result.weights)):
            cval = model.components[n]*result.weights[n]
            disp.panel.oplot(result.x, cval, label='Comp #%d' % (n+1))
    redraw(win=win, show_legend=True, stacked=True, _larch=_larch)

def plot_diffkk(dgroup, emin=None, emax=None, new=True, label=None,
                title=None, delay_draw=False, offset=0, win=1, _larch=None):
    """
    plot_diffkk(dgroup, norm=True, emin=None, emax=None, show_e0=False,
               label=None, new=True, win=1):

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
        redraw(win=win, _larch=_larch)
#enddef

def plot_curvefit(dgroup, nfit=0, show_init=False, subtract_baseline=False,
                      show_residual=False, win=1, _larch=None):
    """plot curvefit fit
    dgroup must have a 'curvefit_history' attribute
    """
    if not hasattr(dgroup, 'curvefit'):
        raise ValueError('Group needs curvefit group')
    #endif

    result = fit = dgroup.curvefit
    if not show_init:
        hist = getattr(dgroup.curvefit, 'fit_history', [])
        if len(hist) > 0:
            if nfit > len(hist):
                nfit = 0
            fit = hist[nfit]
            result = fit.result

    if fit is None:
        raise ValueError('Group needs curvefit.fit_history or init_fit')

    # print(f"Plot Curvefit {show_init=}")
    opts = fit.user_options
    xplot = getattr(fit, 'xdat', getattr(fit, 'x', None))
    yplot = getattr(fit, 'ydat', getattr(fit, 'y', None))
    if xplot is None or yplot is None:
        raise ValueError('Cannot get x or y data for fit')
    xplot = xplot*1.0
    yplot = yplot*1.0
    xplot_full = 1.0*xplot
    yplot_full = 1.0*yplot

    if show_init:
        yfit   = fit.init_fit
        ycomps = None #  pkfit.init_ycomps
        ylabel = 'model'
    else:
        yfit   = 1.0*result.best_fit
        ycomps = fit.ycomps
        ylabel = 'best fit'

    baseline = 0.*yplot
    if ycomps is not None:
        for label, ycomp in ycomps.items():
            if label in opts['bkg_components']:
                baseline += ycomp

    plotopts = dict(title='%s:\ncurvefit' % dgroup.filename,
                    xlabel='x', ylabel=opts['array_desc'],
                    delay_draw=True, show_legend=True, style='solid',
                    linewidth=3, marker='None', markersize=4)

    if subtract_baseline:
        yplot-= baseline
        yfit -= baseline
        plotopts['ylabel'] = '%s-baseline' % plotopts['ylabel']

    dx0, dx1, dy0, dy1 = extend_plotrange(xplot_full, yplot_full,
                                          xmin=opts['xmin'], xmax=opts['xmax'])
    _1, _2, fy0, fy1 = extend_plotrange(xplot, yfit,
                                          xmin=opts['xmin'], xmax=opts['xmax'])

    ncolor = 0
    popts = {'win': win, '_larch': _larch}
    plotopts.update(popts)
    dymin = dymax = None
    if show_residual:
        popts['stacked'] = True
        _fitplot(xplot, yplot, yfit, label='data', label2=ylabel, **plotopts)
        dy = yfit - yplot
        dymax, dymin = dy.max(), dy.min()
        dymax += 0.05 * (dymax - dymin)
        dymin -= 0.05 * (dymax - dymin)
    else:
        _plot(xplot_full, yplot_full, new=True, label='data',
              color=LineColors[0], **plotopts)
        _oplot(xplot, yfit, label=ylabel, color=LineColors[1], **plotopts)
        ncolor = 1

    if ycomps is not None:
        ncomps = len(ycomps)
        if not subtract_baseline:
            ncolor += 1
            _oplot(xplot, baseline, label='baseline', delay_draw=True,
                   style='short dashed', marker='None', markersize=5,
                   color=LineColors[ncolor], **popts)

        for icomp, label in enumerate(ycomps):
            ycomp = ycomps[label]
            if label in opts['bkg_components']:
                continue
            ncolor =  (ncolor+1) % 10
            _oplot(xplot, ycomp, label=label, delay_draw=(icomp != ncomps-1),
                   style='short dashed', marker='None', markersize=5,
                   color=LineColors[ncolor], **popts)

    if opts.get('show_fitrange', False):
        for attr in ('xmin', 'xmax'):
            _plot_axvline(opts[attr], ymin=0, ymax=1,
                          delay_draw=False, color='#888888',
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

    redraw(xmin=dx0, xmax=dx1, ymin=min(dy0, fy0),
           ymax=max(dy1, fy1), dymin=dymin, dymax=dymax, show_legend=True, **popts)
