from .taskpanel  import TaskPanel, FONTSIZE
from .xasnorm_panel import XASNormPanel
from .prepeak_panel import PrePeakPanel
from .lincombo_panel import LinearComboPanel
from .pca_panel import PCAPanel
from .regress_panel import RegressionPanel
from .exafs_panel import EXAFSPanel

from .xas_dialogs import (MergeDialog, RenameDialog, RemoveDialog,
                          DeglitchDialog, RebinDataDialog,
                          EnergyCalibrateDialog, SmoothDataDialog,
                          DeconvolutionDialog, OverAbsorptionDialog,
                          QuitDialog, ExportCSVDialog)

from .xasgui import XASFrame, XASViewer


# def initializeLarchPlugin(_larch=None):
#     """add XAS Frame to _sys.gui_apps """
#     if _larch is not None:
#         _sys = _larch.symtable._sys
#         if not hasattr(_sys, 'gui_apps'):
#             _sys.gui_apps = {}
#         _sys.gui_apps['xas_viewer'] = ('XAS Viewer', XASFrame)
