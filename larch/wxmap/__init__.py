from ..wxlib import (gui_utils, ParameterPanel, PeriodicTablePanel,
                     _newplot, _plot, XRFDisplayFrame)

from .gse_dtcorrect import DTViewer, dtcorrect
from .mapviewer import MapViewer, mapviewer


_larch_builtins = {'_plotter': {'dtcorrect_viewer': dtcorrect,
                                'map_viewer': mapviewer}}

# def initializeLarchPlugin(_larch=None):
#     """add MapFrameViewer to _sys.gui_apps """
#     if _larch is not None:
#         _sys = _larch.symtable._sys
#         if not hasattr(_sys, 'gui_apps'):
#             _sys.gui_apps = {}
#         _sys.gui_apps['mapviewer'] = ('XRF Map Viewer', MapViewerFrame)
