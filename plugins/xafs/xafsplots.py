#!/usr/bin/env python
"""
Plotting macros for XAFS data sets and fits

 Function          Description of what is plotted
 ---------------- -----------------------------------------------------
  plot_mu()        mu(E) for XAFS data group in various forms
  plot_bkg()       mu(E) and background mu0(E) for XAFS data group
  plot_chik()      chi(k) for XAFS data group
  plot_chir()      chi(R) for XAFS data group
  plot_chifit()    chi(k) and chi(R) for fit to feffit dataset
  plot_path_k()    chi(k) for a single path of a feffit dataset
  plot_path_r()    chi(R) for a single path of a feffit dataset
  plot_paths_k()   chi(k) for model and all paths of a feffit dataset
  plot_paths_r()   chi(R) for model and all paths of a feffit dataset
 ---------------- -----------------------------------------------------
"""

from numpy import gradient, ndarray
from larch import Group, ValidateLarchPlugin
from larch.utils import (index_of, index_nearest)

from larch_plugins.wx.plotter import (_getDisplay, _plot, _oplot, _newplot,
                                      _plot_text, _plot_marker,
                                      _plot_arrow, _plot_axvline,
                                      _plot_axhline)

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
                   mu      = r'$\mu(E)$',
                   dmude   = r'$d\mu(E)/dE$',
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

@ValidateLarchPlugin
def plot_mu(dgroup, show_norm=False, show_deriv=False,
            show_pre=False, show_post=False, show_e0=False, with_deriv=False,
            emin=None, emax=None, label='mu', new=True, title=None, win=1,
            _larch=None):
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
     emin       min energy to show, relative to E0 [None, start of data]
     emax       max energy to show, relative to E0 [None, end of data]
     label      string for label [None:  'mu', `dmu/dE', or 'mu norm']
     title      string for plot titlel [None, may use filename if available]
     new        bool whether to start a new plot [True]
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
    xmin, xmax = None, None
    if emin is not None: xmin = dgroup.e0 + emin
    if emax is not None: xmax = dgroup.e0 + emax

    title = _get_title(dgroup, title=title)

    opts = dict(win=win, show_legend=True, linewidth=3,
                title=title, xmin=xmin, xmax=xmax, _larch=_larch)

    _plot(dgroup.energy, mu, xlabel=plotlabels.energy, ylabel=ylabel,
          label=label, zorder=20, new=new, **opts)

    if with_deriv:
        dmu = gradient(mu)/gradient(dgroup.energy)
        _plot(dgroup.energy, dmu, ylabel=plotlabels.dmude,
              label='%s (deriv)' % label, zorder=18, side='right', **opts)
    #endif

    if (not show_norm and not show_deriv):
        if show_pre:
            _plot(dgroup.energy, dgroup.pre_edge, label='pre_edge',
                  zorder=18, **opts)
        #endif
        if show_post:
            _plot(dgroup.energy, dgroup.post_edge, label='post_edge',
                  zorder=18, **opts)
            if show_pre:
                i = index_of(dgroup.energy, dgroup.e0)
                ypre = dgroup.pre_edge[i]
                ypost = dgroup.post_edge[i]
                _plot_arrow(dgroup.e0, ypre, dgroup.e0, ypost,
                            color=plotlabels.e0color, width=0.25,
                            head_width=0, zorder=3, win=win, _larch=_larch)
            #endif
        #endif
    #endif
    if show_e0:
        _plot_axvline(dgroup.e0, zorder=2, size=3,
                      label='E0', color=plotlabels.e0color, win=win,
                      _larch=_larch)
        _getDisplay(win=win, _larch=_larch).panel.conf.draw_legend()
    #endif
#enddef

@ValidateLarchPlugin
def plot_bkg(dgroup, norm=True, emin=None, emax=None, show_e0=False,
             label=None, title=None, new=True, win=1, _larch=None):
    """
    plot_bkg(dgroup, norm=True, emin=None, emax=None, show_e0=False, label=None, new=True, win=1):

    Plot mu(E) and background mu0(E) for XAFS data group

    Arguments
    ----------
     dgroup   group of XAFS data after autobk() results (see Note 1)
     norm     bool whether to show normalized data [True]
     emin     min energy to show, relative to E0 [None, start of data]
     emax     max energy to show, relative to E0 [None, end of data]
     show_e0  bool whether to show E0 [False]
     label    string for label [``None``: 'mu']
     title    string for plot titlel [None, may use filename if available]
     new      bool whether to start a new plot [True]
     win      integer plot window to use [1]

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
    xmin, xmax = None, None
    if emin is not None: xmin = dgroup.e0 + emin
    if emax is not None: xmax = dgroup.e0 + emax
    if norm:
        mu  = dgroup.norm
        bkg = (dgroup.bkg - dgroup.pre_edge) / dgroup.edge_step
        ylabel = "%s (norm)" % ylabel
        label = "%s (norm)" % label
    #endif
    title = _get_title(dgroup, title=title)

    opts = dict(win=win, show_legend=True, linewidth=3, _larch=_larch)
    _plot(dgroup.energy, mu, xlabel=plotlabels.energy, ylabel=ylabel,
         title=title, label=label, zorder=20, new=new, xmin=xmin, xmax=xmax,
         **opts)
    _plot(dgroup.energy, bkg, zorder=18, label='bkg', **opts)
    if show_e0:
        _plot_axvline(dgroup.e0, zorder=2, size=3, label='E0',
                      color=plotlabels.e0color, win=win, _larch=_larch)
        _getDisplay(win=win, _larch=_larch).panel.conf.draw_legend()
    #endif
#enddef


@ValidateLarchPlugin
def plot_chik(dgroup, kweight=None, kmax=None, show_window=True,
              label=None, title=None, new=True, win=1, _larch=None):
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
     label        string for label [``None`` to use 'chi']
     title        string for plot titlel [None, may use filename if available]
     new          bool whether to start a new plot [True]
     win          integer plot window to use [1]

    Notes
    -----
     1. The input data group must have the following attributes:
         k, chi, kwin, filename
    """
    if kweight is None and hasattr(group, 'xftf_details'):
        kweight = dgroup.xftf_details.call_args['kweight']
    #endif
    if kweight is None: kweight = 0

    chi = dgroup.chi * dgroup.k ** kweight
    opts = dict(win=win, show_legend=True, linewidth=3, _larch=_larch)
    if label is None:
        label = 'chi'
    #endif
    title = _get_title(dgroup, title=title)
    _plot(dgroup.k, chi, xlabel=plotlabels.k,
         ylabel=plotlabels.chikw.format(kweight), title=title,
         label=label, zorder=20, new=new, xmax=kmax, **opts)

    if show_window and hasattr(dgroup, 'kwin'):
        _plot(dgroup.k, dgroup.kwin, zorder=12, label='window', **opts)
    #endif
#enddef


@ValidateLarchPlugin
def plot_chir(dgroup, show_mag=True, show_real=False, show_imag=False,
              rmax=None, label=None, title=None, new=True, win=1, _larch=None):
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
     label        string for label [``None`` to use 'chir']
     title        string for plot titlel [None, may use filename if available]
     rmax         max R to show [None, end of data]
     new          bool whether to start a new plot [True]
     win          integer plot window to use [1]

    Notes
    -----
     1. The input data group must have the following attributes:
         r, chir_mag, chir_im, chir_re, kweight, filename
    """

    kweight = dgroup.xftf_details.call_args['kweight']
    title = _get_title(dgroup, title=title)
    opts = dict(win=win, show_legend=True, linewidth=3,
                title=title, zorder=20, xmax=rmax,
                xlabel=plotlabels.r, new=new, _larch=_larch)

    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)
    opts['ylabel'] = ylabel

    if label is None:
        label = 'chir'
    #endif
    if show_mag:
        _plot(dgroup.r, dgroup.chir_mag, label='%s (mag)' % label, **opts)
        opts['new'] = False
    #endif
    if show_real:
        _plot(dgroup.r, dgroup.chir_re, label='%s (real)' % label, **opts)
        opts['new'] = False
    #endif
    if show_imag:
        _plot(dgroup.r, dgroup.chir_im, label='%s (imag)' % label, **opts)
    #endif
#enddef

@ValidateLarchPlugin
def plot_chifit(dataset, kmin=0, kmax=None, kweight=None, rmax=None,
                show_mag=True, show_real=False, show_imag=False,
                title=None, new=True, win=1, _larch=None):
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
     title        string for plot titlel [None, may use filename if available]
     new          bool whether to start a new plot [True]
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
              show_legend=True, win=win, title=title, _larch=_larch)

    # k-weighted chi(k) in first plot window
    _plot(dataset.data.k, data_chik, xmin=kmin, xmax=kmax,
            xlabel=plotlabels.k, ylabel=plotlabels.chikw.format(kweight),
            label='data', new=new, **opts)
    _plot(dataset.model.k, model_chik, label='fit',  **opts)

    # show chi(R) in next plot window
    opts['win'] = win+1

    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)
    opts.update({'xlabel': plotlabels.r, 'ylabel': ylabel,
                 'xmax': rmax, 'new': new})

    if show_mag:
        _plot(dataset.data.r,  dataset.data.chir_mag,
             label='|data|', **opts)
        opts['new'] = False
        _plot(dataset.model.r, dataset.model.chir_mag,
             label='|fit|',  **opts)
    #endif
    if show_real:
        _plot(dataset.data.r, dataset.data.chir_re, label='Re[data]', **opts)
        opts['new'] = False
        _plot(dataset.model.r, dataset.model.chir_re, label='Re[fit]',  **opts)
    #endif
    if show_imag:
        plot(dataset.data.r, dataset.data.chir_im, label='Im[data]', **opts)
        opts['new'] = False
        plot(dataset.model.r, dataset.model.chir_im, label='Im[fit]',  **opts)
    #endif
#enddef

@ValidateLarchPlugin
def plot_path_k(dataset, ipath=0, kmin=0, kmax=None, offset=0, label=None,
                new=False, win=1, _larch=None, **kws):
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
     win          integer plot window to use [1]
     kws          additional keyword arguments are passed to plot()
    """
    kweight = dataset.transform.kweight
    path = dataset.pathlist[ipath]
    if label is None: label = 'path %i' % (ipath)

    chi_kw = offset + path.chi * path.k**kweight

    _plot(path.k, chi_kw, label=label, xmin=kmin, xmax=kmax,
         xlabel=plotlabels.k, ylabel=plotlabels.chikw.format(kweight),
         win=win, new=new, _larch=_larch, **kws)
#enddef

@ValidateLarchPlugin
def plot_path_r(dataset, ipath, rmax=None, offset=0, label=None,
                show_mag=True, show_real=False, show_imag=True,
                new=False, win=1, _larch=None, **kws):
    """
    plot_path_r(dataset, ipath,rmax=None, offset=0, label=None,
                show_mag=True, show_real=False, show_imag=True,
                new=False, win=1, **kws)

    Plot chi(R) for a single Path of a feffit dataset

    Arguments
    ----------
     dataset      feffit dataset, after running feffit()
     ipath        index of path, starting count at 0 [0]
     kmax         max k to show [None, end of data]
     offset       vertical offset to use for plot [0]
     label        path label ['path %d' % ipath]
     show_mag     bool whether to plot |chi(R)| [True]
     show_real    bool whether to plot Re[chi(R)] [False]
     show_imag    bool whether to plot Im[chi(R)] [False]
     new          bool whether to start a new plot [True]
     win          integer plot window to use [1]
     kws          additional keyword arguments are passed to plot()
    """
    path = dataset.pathlist[ipath]
    if label is None:
        label = 'path %i' % (ipath)
    #endif
    kweight =dataset.transform.kweight
    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)

    opts.update({'xlabel': plotlabels.r, 'ylabel': ylabel,
                 'xmax': rmax, 'new': new, '_larch': _larch})
    opts.update(kws)
    if show_mag:
        _plot(path.r,  offest+path.chir_mag, label=label, **opts)
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
#enddef

@ValidateLarchPlugin
def plot_paths_k(dataset, offset=-1, kmin=0, kmax=None,
                 title=None, new=True, win=1, _larch=None, **kws):
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
     title        string for plot titlel [None, may use filename if available]
     win          integer plot window to use [1]
     kws          additional keyword arguments are passed to plot()
    """
    # make k-weighted chi(k)
    kweight = dataset.transform.kweight
    model = dataset.model

    model_chi_kw = model.chi * model.k**kweight

    title = _get_title(dataset, title=title)
    _plot(model.k, model_chi_kw, title=title, label='sum', new=new,
          xlabel=plotlabels.r, ylabel=plotlabels.chikw.format(kweight),
          xmin=xmin, xmax=kmax, win=win, _larch=_larch, **kws)

    for ipath in range(len(dataset.pathlist)):
        plot_path_k(dataset, ipath, offset=(ipath+1)*offset,
                    kmin=kmin, kmax=kmax, new=False, win=win, _larch=_larch)
    #endfor
#enddef

@ValidateLarchPlugin
def plot_paths_r(dataset, offset=-0.5, rmax=None, show_mag=True,
                 show_real=False, show_imag=False, title=None, new=True,
                 win=1, _larch=None, **kws):
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
     title        string for plot titlel [None, may use filename if available]
     new          bool whether to start a new plot [True]
     win          integer plot window to use [1]
     kws          additional keyword arguments are passed to plot()
    """
    kweight = dataset.transform.kweight
    model = dataset.model

    ylabel = plotlabels.chirlab(kweight, show_mag=show_mag,
                                show_real=show_real, show_imag=show_imag)
    title = _get_title(dataset, title=title)
    opts.update({'xlabel': plotlabels.r, 'ylabel': ylabel,
                 'xmax': rmax, 'new': new, 'title': title,
                 '_larch': _larch})
    opts.update(kws)
    if show_mag:
        _plot(path.r,  model.chir_mag, label=label, **opts)
        opts['new'] = False
    #endif
    if show_real:
        _plot(path.r,  model.chir_re, label=label, **opts)
        opts['new'] = False
    #endif
    if show_imag:
        _plot(path.r,  model.chir_im, label=label, **opts)
        opts['new'] = False
    #endif

    for ipath in range(len(dataset.pathlist)):
        plot_path_r(dataset, ipath, offset=(ipath+1)*offset,
                    show_mag=show_mag, show_real=show_real,
                    show_imag=show_imag, **opts)
    #endfor
#enddef


def initializeLarchPlugin(_larch=None):
    """initialize _xafs"""
    if _larch is None:
        return
    _larch.symtable._xafs.plotlabels  = plotlabels

def registerLarchPlugin():
    return ('_xafs', {'plot_mu':plot_mu,
                      'plot_bkg':plot_bkg,
                      'plot_chik': plot_chik,
                      'plot_chir': plot_chir,
                      'plot_chifit': plot_chifit,
                      'plot_path_k': plot_path_k,
                      'plot_path_r': plot_path_r,
                      'plot_paths_k': plot_paths_k,
                      'plot_paths_r': plot_paths_r,
                      })
