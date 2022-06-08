#!/usr/bin/env python
"""
wx widgets for Larch
"""
__DOC__ = '''
WxPython functions for larch

function         description
------------     ------------------------------
gcd              graphical change directory - launch browser to select working folder
fileprompt       launch file browser to select files.

'''

import locale

from pyshortcuts import platform
import os
import sys
HAS_WXPYTHON = False
try:
    import wx
    HAS_WXPYTHON = True
except (ImportError, AttributeError):
    HAS_WXPYTHON = False

_larch_name = '_sys.wx'
_larch_builtins = {}

FONTSIZE = 9
FONTSIZE_FW = 9
if platform == 'win':
    FONTSIZE = 10
    FONTSIZE_FW = 9
    locale.setlocale(locale.LC_ALL, 'C')

if platform == 'darwin':
    FONTSIZE = 12
    FONTSIZE_FW = 12

if HAS_WXPYTHON:
    try:
        import wxutils
        import wxmplot
    except:
        from ..apps import install_extras
        from ..site_config import extras_wxgraph
        install_extras(extras_wxgraph)


    from . import larchframe
    from . import larchfilling
    from . import readlinetextctrl

    from wxutils import (set_sizer, pack, SetTip, Font, HLine, Check,
                         MenuItem, Popup, RIGHT, LEFT, CEN , LTEXT,
                         FRAMESTYLE, hms, DateTimeCtrl, Button, TextCtrl,
                         ToggleButton, BitmapButton, Choice, YesNo,
                         SimpleText, LabeledTextCtrl, HyperText, get_icon,
                         OkCancel, FileOpen, FileSave, SelectWorkdir,
                         fix_filename, SavedParameterDialog, GridPanel,
                         RowPanel, make_steps, set_float, FloatCtrl,
                         EditableListBox)

    from .colors import COLORS, GUIColors, set_color
    from .filechecklist import FileCheckList, FileDropTarget

    from .floats import NumericCombo, FloatSpin, FloatSpinWithPin

    from .notebooks import flatnotebook

    from .larchframe import LarchFrame, LarchPanel
    from .columnframe import ColumnDataFileFrame, EditColumnFrame
    from .athena_importer import AthenaImporter
    from .specfile_importer import SpecfileImporter
    from .reportframe import ReportFrame, DictFrame, DataTableGrid
    from .gui_utils import gcd, databrowser, fileprompt, wx_update, LarchWxApp

    from .larch_updater import LarchUpdaterDialog
    from .parameter import ParameterWidgets, ParameterPanel
    from .periodictable import PeriodicTablePanel
    from .feff_browser import FeffResultsFrame, FeffResultsPanel

    from .cif_browser import CIFFrame


    _larch_builtins = {'_sys.wx': dict(gcd=gcd,
                                       databrowser=databrowser,
                                       filepromspt=fileprompt,
                                       wx_update=wx_update)}

    from .plotter import (_plot, _oplot, _newplot, _plot_text,
                          _plot_marker, _plot_arrow, _plot_setlimits,
                          _plot_axvline, _plot_axhline, _scatterplot,
                          _hist, _update_trace, _saveplot, _saveimg,
                          _getDisplay, _closeDisplays, _getcursor,
                          last_cursor_pos, _imshow, _contour, _xrf_plot,
                          _xrf_oplot, _fitplot, _redraw_plot)

    from .xrfdisplay import  XRFDisplayFrame

    from . import xafsplots
    from .xafsplots import plotlabels

    _larch_builtins['_plotter'] = dict(plot=_plot, oplot=_oplot,
                                       newplot=_newplot, plot_text=_plot_text,
                                       plot_marker=_plot_marker,
                                       plot_arrow=_plot_arrow,
                                       plot_setlimits=_plot_setlimits,
                                       plot_axvline=_plot_axvline,
                                       plot_axhline=_plot_axhline,
                                       scatterplot=_scatterplot, hist=_hist,
                                       update_trace=_update_trace,
                                       save_plot=_saveplot,
                                       save_image=_saveimg,
                                       get_display=_getDisplay,
                                       close_all_displays=_closeDisplays,
                                       get_cursor=_getcursor,
                                       last_cursor_pos=last_cursor_pos,
                                       imshow=_imshow, contour=_contour,
                                       xrf_plot=_xrf_plot,
                                       xrf_oplot=_xrf_oplot,
                                       fit_plot=_fitplot,
                                       redraw_plot=_redraw_plot)

    _larch_builtins['_xafs'] = dict(redraw=xafsplots.redraw,
                                    plot_mu=xafsplots.plot_mu,
                                    plot_bkg=xafsplots.plot_bkg,
                                    plot_chie=xafsplots.plot_chie,
                                    plot_chik=xafsplots.plot_chik,
                                    plot_chir=xafsplots.plot_chir,
                                    plot_chiq=xafsplots.plot_chiq,
                                    plot_wavelet=xafsplots.plot_wavelet,
                                    plot_chifit=xafsplots.plot_chifit,
                                    plot_path_k=xafsplots.plot_path_k,
                                    plot_path_r=xafsplots.plot_path_r,
                                    plot_paths_k=xafsplots.plot_paths_k,
                                    plot_paths_r=xafsplots.plot_paths_r,
                                    plot_feffdat=xafsplots.plot_feffdat,
                                    plot_diffkk=xafsplots.plot_diffkk,
                                    plot_prepeaks_fit=xafsplots.plot_prepeaks_fit,
                                    plot_prepeaks_baseline=xafsplots.plot_prepeaks_baseline,
                                    plot_pca_components=xafsplots.plot_pca_components,
                                    plot_pca_weights=xafsplots.plot_pca_weights,
                                    plot_pca_fit=xafsplots.plot_pca_fit)


    def _larch_init(_larch):
        """add ScanFrameViewer to _sys.gui_apps """
        if _larch is None:
            return
        _sys = _larch.symtable._sys
        if not hasattr(_sys, 'gui_apps'):
            _sys.gui_apps = {}
        _sys.gui_apps['xrfviewer'] = ('XRF Spectrum Viewer', XRFDisplayFrame)

else:
    def nullfunc(*args, **kws):
        pass

    _larch_builtins = {'_sys.wx': dict(gcd=nullfunc,
                                       databrowser=nullfunc,
                                       filepromspt=nullfunc,
                                       wx_update=nullfunc)}

    _larch_builtins['_plotter'] = dict(plot=nullfunc,
                                       oplot=nullfunc,
                                       newplot=nullfunc,
                                       plot_text=nullfunc,
                                       plot_marker=nullfunc,
                                       plot_arrow=nullfunc,
                                       plot_setlimits=nullfunc,
                                       plot_axvline=nullfunc,
                                       plot_axhline=nullfunc,
                                       scatterplot=nullfunc,
                                       hist=nullfunc,
                                       update_trace=nullfunc,
                                       save_plot=nullfunc,
                                       save_image=nullfunc,
                                       get_display=nullfunc,
                                       close_all_displays=nullfunc,
                                       get_cursor=nullfunc,
                                       last_cursor_pos=nullfunc,
                                       imshow=nullfunc,
                                       contour=nullfunc,
                                       xrf_plot=nullfunc,
                                       xrf_oplot=nullfunc,
                                       fit_plot=nullfunc)
