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
from pathlib import Path

from pyshortcuts import uname, fix_filename
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

FONTSIZE = 8
FONTSIZE_FW = 8
if uname == 'win':
    FONTSIZE = 10
    FONTSIZE_FW = 11
    locale.setlocale(locale.LC_ALL, 'C')
elif uname == 'darwin':
    FONTSIZE = 11
    FONTSIZE_FW = 12

def fontsize(fixed_width=False):
    """return best default fontsize"""
    font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
    if uname not in ('win', 'darwin'):
        font = font.Smaller()
    elif fixed_width:
        font = font.Larger()
    return int(font.GetFractionalPointSize())


def Font(size, serif=False, fixed_width=False):
    """define a font by size and serif/ non-serif
    f = Font(10, serif=True)
    """
    family = wx.DEFAULT
    if not serif:
        family = wx.SWISS
    if fixed_width:
        family = wx.MODERN
    return wx.Font(size, family, wx.NORMAL, wx.BOLD, 0, "")

def get_font(larger=0, smaller=0, serif=False, fixed_width=False):
    "return a font"
    fnt = Font(fontsize(fixed_width=fixed_width),
               serif=serif, fixed_width=fixed_width)
    for i in range(larger):
        fnt = fnt.Larger()
    for i in range(smaller):
        fnt = fnt.Smaller()
    return fnt


def DarwinHLine(parent, size=(700, 3)):
    """Horizontal line for MacOS
    h = HLine(parent, size=(700, 3)
    """
    msize = (size[0], int(size[1]*0.75))
    line = wx.Panel(parent, size=msize)
    line.SetBackgroundColour((196,196,196))
    return line

DARK_THEME = False
try:
    import darkdetect
    DARK_THEME = darkdetect.isDark()
except ImportError:
    DARK_THEME = False

def nullfunc(*args, **kws):
    pass

_larch_builtins = {'_sys.wx': dict(gcd=nullfunc,
                                   databrowser=nullfunc,
                                   fileprompt=nullfunc,
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

if HAS_WXPYTHON:
    from wxutils import (set_sizer, pack, SetTip, HLine, Check,
                         MenuItem, Popup, RIGHT, LEFT, CEN , LTEXT,
                         FRAMESTYLE, hms, DateTimeCtrl, Button,
                         TextCtrl, ToggleButton, BitmapButton, Choice,
                         YesNo, SimpleText, LabeledTextCtrl,
                         HyperText, get_icon, OkCancel,
                         SavedParameterDialog, GridPanel, RowPanel,
                         make_steps, set_float, FloatCtrl,
                         EditableListBox,
                         FileDropTarget, NumericCombo, FloatSpin,
                         FileOpen, FileSave, SelectWorkdir,
                         FloatSpinWithPin, flatnotebook,
                         PeriodicTablePanel, gcd, ExceptionPopup,
                         show_wxsizes, panel_pack)

    from .filechecklist import FileCheckList
    from .wxcolors import COLORS, GUIColors, GUI_COLORS, set_color
    from . import larchframe
    from . import larchfilling
    from . import readlinetextctrl

    from .larchframe import LarchFrame, LarchPanel
    from .columnframe import ColumnDataFileFrame, EditColumnFrame
    from .hdf5_browser import HDF5DataFileFrame
    from .athena_importer import AthenaImporter
    from .specfile_importer import SpecfileImporter
    from .xas_importer import XasImporter
    from .reportframe import ReportFrame, DictFrame, DataTableGrid, CSVFrame
    from .gui_utils import (databrowser, fileprompt, LarchWxApp, wx_update)
    from .larch_updater import LarchUpdaterDialog
    from .parameter import ParameterWidgets, ParameterPanel


    from .feff_browser import FeffResultsFrame, FeffResultsPanel
    from .cif_browser import CIFFrame
    from .structure2feff_browser import Structure2FeffFrame

    _larch_builtins = {'_sys.wx': dict(gcd=gcd,
                                       databrowser=databrowser,
                                       fileprompt=fileprompt,
                                       wx_update=wx_update)}

    from .plotter import (plot, oplot, newplot, plot_text, fileplot,
                          plot_marker, plot_arrow, plot_setlimits,
                          plot_axvline, plot_axhline, scatterplot,
                          hist, update_trace, save_plot, save_image,
                          get_display, close_displays, get_cursor,
                          last_cursor_pos, imshow, contour, xrf_plot,
                          xrf_oplot, fitplot, redraw_plot,
                          get_zoomlimits, set_zoomlimits,
                          save_plot_config, get_plot_config,
                          get_panel_plot_config, set_panel_plot_config,
                          get_zorders, get_markercolors, set_plotwindow_title)

    if uname == 'darwin':
        HLine = DarwinHLine

    _larch_builtins['_plotter'] = dict(plot=plot, oplot=oplot,
                                       newplot=newplot, plot_text=plot_text,
                                       plot_marker=plot_marker,
                                       plot_arrow=plot_arrow,
                                       plot_setlimits=plot_setlimits,
                                       plot_axvline=plot_axvline,
                                       plot_axhline=plot_axhline,
                                       scatterplot=scatterplot, hist=hist,
                                       update_trace=update_trace,
                                       save_plot=save_plot,
                                       save_image=save_image,
                                       save_plot_config=save_plot_config,
                                       get_plot_config=get_plot_config,
                                       get_display=get_display,
                                       close_all_displays=close_displays,
                                       get_cursor=get_cursor,
                                       last_cursor_pos=last_cursor_pos,
                                       imshow=imshow, contour=contour,
                                       xrf_plot=xrf_plot,
                                       xrf_oplot=xrf_oplot,
                                       fit_plot=fitplot,
                                       fileplot=fileplot,
                                       redraw_plot=redraw_plot)



    def _larch_init(_larch):
        """add ScanFrameViewer to _sys.gui_apps """
        if _larch is None:
            return
        _sys = _larch.symtable._sys
        if not hasattr(_sys, 'gui_apps'):
            _sys.gui_apps = {}
        # _sys.gui_apps['xrfviewer'] = ('XRF Spectrum Viewer', XRFDisplayFrame)
        from larch.plot import wxmplot_xafsplots as xafsplots
        print("INIT WXLIB PLOTTER")
        _larch_builtins['_xafs'] = dict(redraw=xafsplots.redraw,
                                    plotlabels=xafsplots.plotlabels,
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
                                    plot_pca_fit=xafsplots.plot_pca_fit,
                                    plot_curvefit=xafsplots.plot_curvefit,
                                    )


    #############################
    ## Hack System and Startfile on Windows totry to track down
    ## weird error of starting other applications, like Mail
    if uname == 'win':
        from os import system as os_system
        from os import startfile as os_startfile

        def my_system(command):
            print(f"#@-> os.system: {command}")
            return os_system(command)

        def my_startfile(filepath, operation=None):
            print(f"#@-> os.startfile: {filepath}, {operation}")
            try:
                if operation is None:
                    return os_startfile(filepath)
                else:
                    return os_startfile(filepath, operation)
            except WindowsError:
                print(f"#@-> os.startfile failed: {filepath}, {operation}")

        os.system = my_system
        os.startfile = my_startfile
    #############################
