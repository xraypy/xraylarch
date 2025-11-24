#!/usr/bin/env python

"""
Standard plots for Larch
------------------------

This module is independent of the Wx GUI. It allows a number of plotting libraries
to be used, and is intended for use in standalone scripts and Jupyter notebooks.

Currenly supported plotting libraries include:
     wxmplot - this is the library used in Larix, but it can be used in standalone scripts,
               without needing Larix. It requires "write access" to your screen, so cannot
               be for cloud-hosted notebooks.
     plotly  - this uses the Plotly library, dessigned for drawing in a web browwer.
     bokeh   - this uses the Bokeh library, dessigned for drawing in a web browwer.
"""
from pathlib import Path
import numpy as np
from larch import Group
from larch.math import index_of, index_nearest, interp1d

LineColors = ('#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd',
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf')


plotlabels_wx = Group(k    = r'$k \rm\,(\AA^{-1})$',
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
                   chiew   = r'$E^{_w_}\chi(E) \rm\,(eV^{_w_})$',
                   chikw   = r'$k^{_w_}\chi(k) \rm\,(\AA^{-_w_})$',
                   chi0    = r'$\chi(k)$',
                   chi1    = r'$k\chi(k) \rm\,(\AA^{-1})$',
                   chi2    = r'$k^2\chi(k) \rm\,(\AA^{-2})$',
                   chi3    = r'$k^3\chi(k) \rm\,(\AA^{-3})$',
                   chir    = r'$\chi(R) \rm\,(\AA^{-_w_})$',
                   chirmag = r'$|\chi(R)| \rm\,(\AA^{-_w_})$',
                   chirre  = r'${{\rm Re}}[\chi(R)] \rm\,(\AA^{-_w_})$',
                   chirim  = r'${{\rm Im}}[\chi(R)] \rm\,(\AA^{-_w_}})$',
                   chirpha = r'${{\rm Phase}}[\chi(R)] \rm\,(\AA^{-_w_})$',
                   e0color = '#B2B282',
                   x = r'$x$',
                   y = r'$y$',
                   xdat = r'$x$',
                   ydat = r'$y$',
                   xplot = r'$x$',
                   yplot= r'$y$',
                   ynorm = r'scaled $y$',
                   xshift = r'shifted $x$',
                   dydx = r'$dy/dx$',
                   d2ydx = r'$d^2y/dx^2$')


# to make life easier for MathJax/Plotly/Bokeh/IPython
# we have replace "\AA" with "\unicode{x212B}"
plotlabels_web = Group(k   = r'$$k \rm\,(\unicode{x212B}^{-1})$$',
                   r       = r'$$R \rm\,(\unicode{x212B})$$',
                   energy  = r'$$E\rm\,(eV)$$',
                   en_e0   = r'$E-E_{0}\rm\,(eV)$',
                   en_e0val = r'$E-E_0 \rm\,(eV)\rm\,\,\,  [E_0={0:.2f}]$',
                   ewithk  = r'$$E\rm\,(eV)$$' + '\n' + r'$$[k \rm\,(\unicode{x212B}^{-1})]$$',
                   mu      = r'$$\mu(E)$$',
                   norm    = r'normalized $$\mu(E)$$',
                   flat    = r'flattened $$\mu(E)$$',
                   deconv  = r'deconvolved $$\mu(E)$$',
                   dmude   = r'$$d\mu_{\rm norm}(E)/dE$$',
                   d2mude  = r'$$d^2\mu_{\rm norm}(E)/dE^2$$',
                   chie    = r'$$\chi(E)$$',
                   chie0   = r'$$\chi(E)$$',
                   chie1   = r'$$E\chi(E) \rm\, (eV)$$',
                   chiew   = r'$$E^{{_w_}\chi(E) \rm\,(eV^{_w_})$$',
                   chikw   = r'$$k^{{_w_}}\chi(k) \rm\,(\unicode{x212B}^{{-_w_}})$$',
                   chi0    = r'$$\chi(k)$$',
                   chi1    = r'$$k\chi(k) \rm\,(\unicode{x212B}^{-1})$$',
                   chi2    = r'$$k^2\chi(k) \rm\,(\unicode{x212B}^{-2})$$',
                   chi3    = r'$$k^3\chi(k) \rm\,(\unicode{x212B}^{-3})$$',
                   chir    = r'$$\chi(R) \rm\,(\unicode{x212B}^{{-_w_}})$$',
                   chirmag = r'$$|\chi(R)| \rm\,(\unicode{x212B}^{{-_w_}})$$',
                   chirre  = r'$${{\rm Re}}[\chi(R)] \rm\,(\unicode{x212B}^{{-_w_}})$$',
                   chirim  = r'$${{\rm Im}}[\chi(R)] \rm\,(\unicode{x212B}^{{-_w_}})$$',
                   chirpha = r'$${{\rm Phase}}[\chi(R)] \rm\,(\unicode{x212B}^{{-_w_}})$$',
                   e0color = '#B2B282',
                   x = r'$x$',
                   y = r'$y$',
                   xdat = r'$x$',
                   ydat = r'$y$',
                   xplot = r'$x$',
                   yplot= r'$y$',
                   ynorm = r'scaled $y$',
                   xshift = r'shifted $x$',
                   dydx = r'$dy/dx$',
                   d2ydx = r'$d^2y/dx^2$')


# functions common to many XAFS plots

def safetitle(t):
    if "'" in t:
        t = t.replace("'", "\\'")
    return t

def get_title(dgroup, title=None):
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


def get_kweight(dgroup, kweight=None):
    "get the kweight used for a group"
    if kweight is not None:
        return kweight
    callargs = getattr(dgroup, 'callargs', None)
    ftargs = getattr(callargs, 'xftf', {'kweight':0})
    return ftargs['kweight']

def set_label_weight(label, w):
    return label.replace('_w_', f'{w:g}')

def chir_label(labels, kweight, show_mag=True, show_real=False, show_imag=False):
    """generate chi(R) label for a kweight

    Arguments
    ----------
     labels       plotlabels group (required)
     kweight      k-weight to use (required)
     show_mag     bool whether to plot |chi(R)| [True]
     show_real    bool whether to plot Re[chi(R)] [False]
     show_imag    bool whether to plot Im[chi(R)] [False]
    """
    ylab = []
    if show_mag:
        ylab.append(set_label_weight(labels.chirmag, kweight))
    if show_real:
        ylab.append(set_label_weight(labels.chirre, kweight))
    if show_imag:
        ylab.append(set_label_weight(labels.chirim, kweight))
    if len(ylab) > 1:  # if multiple selected, use the generic chi(r)
        ylab = [set_label_weight(labels.chir, kweight)]
    return ylab[0]


def get_erange(dgroup, emin=None, emax=None, e0=None):
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

def extend_plotrange(x, y, xmin=None, xmax=None, extend=0.10):
    """return plot limits to extend a plot range for x, y pairs"""
    xeps = min(np.diff(x)) / 5.
    if xmin is None:  xmin = min(x)
    xmin = max(min(x), xmin)

    if xmax is None:  xmax = max(x)
    xmax = min(max(x), xmax)
    i0 = index_of(x, xmin + xeps)
    i1 = index_nearest(x, xmax + xeps) + 1

    xspan = x[i0:i1]
    xrange = max(xspan) - min(xspan)
    yspan = y[i0:i1]
    yrange = max(yspan) - min(yspan)
    return  (min(xspan) - extend * xrange,
             max(xspan) + extend * xrange,
             min(yspan) - extend * yrange,
             max(yspan) + extend * yrange)


from . import plotly_xafsplots
from . import bokeh_xafsplots
from . import wxmplot_xafsplots
