#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Plot RIXS data
==============
"""
from itertools import cycle
from silx.gui import qt
from silx.gui.plot.Profile import ProfileToolBar
from silx.gui.plot.actions import PlotAction

from silx.gui.plot.tools.roi import RegionOfInterestManager
from silx.gui.plot.tools.roi import RegionOfInterestTableWidget
# from silx.gui.plot.items.roi import RectangleROI
from silx.gui.plot.items import LineMixIn, SymbolMixIn


from larch.qtlib.plotarea import PlotArea, MdiSubWindow
from larch.qtlib.plot1D import Plot1D
from larch.qtlib.plot2D import Plot2D

from larch.utils.logging import getLogger

_DEFAULT_OVERLAY_COLORS = cycle(['#1F77B4', '#AEC7E8', '#FF7F0E', '#FFBB78',
                                 '#2CA02C', '#98DF8A', '#D62728', '#FF9896',
                                 '#9467BD', '#C5B0D5', '#8C564B', '#C49C94',
                                 '#E377C2', '#F7B6D2', '#7F7F7F', '#C7C7C7',
                                 '#BCBD22', '#DBDB8D', '#17BECF', '#9EDAE5'])

__authors__ = ['Mauro Rovezzi']


class RixsROIManager(RegionOfInterestManager):

    def __init__(self, plot, color='pink'):
        super(RixsROIManager, self).__init__(plot)
        self.setColor(color)
        self.sigRoiAdded.connect(self.updateAddedRegionOfInterest)

    def updateAddedRegionOfInterest(self, roi):
        """Called for each added region of interest: set the name"""
        if roi.getLabel() == '':
            roi.setLabel('%d' % len(self.getRois()))
        if isinstance(roi, LineMixIn):
            roi.setLineWidth(2)
            roi.setLineStyle('--')
        if isinstance(roi, SymbolMixIn):
            roi.setSymbol('+')
            roi.setSymbolSize(3)


class RixsROIDockWidget(qt.QDockWidget):

    def __init__(self, plot, parent=None):

        assert isinstance(plot, RixsPlot2D), "'plot' should be an instance of RixsPlot2D"
        _title = f"Plot {plot._index} : cursors infos"
        super(RixsROIDockWidget, self).__init__(_title, parent=parent)

        self._roiManager = RixsROIManager(plot)

        #: Create the table widget displaying infos
        self._roiTable = RegionOfInterestTableWidget()
        self._roiTable.setRegionOfInterestManager(self._roiManager)

        #: Create a toolbar containing buttons for all ROI 'drawing' modes
        self._roiToolbar = qt.QToolBar()
        self._roiToolbar.setIconSize(qt.QSize(16, 16))

        for roiClass in self._roiManager.getSupportedRoiClasses():
            # Create a tool button and associate it with the QAction of each
            # mode
            action = self._roiManager.getInteractionModeAction(roiClass)
            self._roiToolbar.addAction(action)

        # Add the region of interest table and the buttons to a dock widget
        self._widget = qt.QWidget()
        self._layout = qt.QVBoxLayout()
        self._widget.setLayout(self._layout)
        self._layout.addWidget(self._roiToolbar)
        self._layout.addWidget(self._roiTable)

        self.setWidget(self._widget)
        self.visibilityChanged.connect(self.roiDockVisibilityChanged)

    def roiDockVisibilityChanged(self, visible):
        """Handle change of visibility of the roi dock widget

        If dock becomes hidden, ROI interaction is stopped.
        """
        if not visible:
            self._roiManager.stop()


class RixsRotateAction(PlotAction):
    """QAction rotating a Rixs plane

    :param plot: :class:`.PlotWidget` instance on which to operate
    :param parent: See :class:`QAction`
    """

    def __init__(self, plot, parent=None):
        PlotAction.__init__(self,
                            plot,
                            icon='compare-align-auto',
                            text='Rixs_et',
                            tooltip='Rotate RIXS plane to energy transfer',
                            triggered=self.rotateImage,
                            parent=parent)

    def rotateImage(self):
        """"""
        return


class RixsProfileToolBar(ProfileToolBar):
    """RIXS-adapted Profile (=Cuts) toolbar"""

    def __init__(self, parent=None, plot=None, profileWindow=None, overlayColors=None,
                 title='RIXS profile'):
        """Constructor"""
        super(RixsProfileToolBar, self).__init__(parent=parent, plot=plot,
                                                 profileWindow=profileWindow, title=title)

        self._overlayColors = overlayColors or _DEFAULT_OVERLAY_COLORS

    def _getNewColor(self):
        return next(self._overlayColors)

    def updateProfile(self):
        """Update the displayed profile and profile ROI.
        This uses the current active image of the plot and the current ROI.
        """
        image = self.plot.getActiveImage()
        if image is None:
            return

        self._overlayColor = self._getNewColor()

        self._createProfile(currentData=image.getData(copy=False),
                            origin=image.getOrigin(), scale=image.getScale(),
                            colormap=None, z=image.getZValue(),
                            method=self.getProfileMethod())


class RixsPlot2D(Plot2D):
    """RIXS equivalent of Plot2D"""

    def __init__(self, parent=None, backend=None, logger=None,
                 profileWindow=None, overlayColors=None, title="RixsPlot2D"):
        """Constructor"""
        super(RixsPlot2D, self).__init__(parent=parent, backend=backend, title=title)

        self._title = title
        self._logger = logger or getLogger("RixsPlot2D")
        self._profileWindow = profileWindow or Plot1D(title="Profiles")
        self._overlayColors = overlayColors or _DEFAULT_OVERLAY_COLORS

        #: cleaning toolbar
        self.getMaskAction().setVisible(False)
        self.getYAxisInvertedAction().setVisible(False)
        self.getKeepDataAspectRatioAction().setVisible(False)
        self.getColorBarAction().setVisible(False)

        # Change default profile toolbar
        self.removeToolBar(self.profile)
        self.profile = RixsProfileToolBar(plot=self,
                                          profileWindow=self._profileWindow,
                                          overlayColors=self._overlayColors)
        self.addToolBar(self.profile)
        self.setKeepDataAspectRatio(True)
        self.getDefaultColormap().setName('YlOrBr')


class RixsPlotArea(PlotArea):
    """RIXS equivalent of PlotArea"""

    def __init__(self, parent=None, profileWindow=None, overlayColors=None):
        super(RixsPlotArea, self).__init__(parent=parent)

        self._overlayColors = overlayColors or _DEFAULT_OVERLAY_COLORS
        self._profileWindow = profileWindow or self._addProfileWindow()
        self.setMinimumSize(300, 300)
        self.setWindowTitle('RixsPlotArea')

    def showContextMenu(self, position):
        menu = qt.QMenu('RixsPlotArea Menu', self)

        action = qt.QAction('Add RixsPlot2D Window', self,
                            triggered=self.addRixsPlot2D)
        menu.addAction(action)

        menu.addSeparator()

        action = qt.QAction('Cascade Windows', self,
                            triggered=self.cascadeSubWindows)
        menu.addAction(action)

        action = qt.QAction('Tile Windows', self,
                            triggered=self.tileSubWindows)
        menu.addAction(action)

        menu.exec_(self.mapToGlobal(position))

    def _addProfileWindow(self):
        """Add a ProfileWindow in the mdi Area"""
        subWindow = MdiSubWindow(parent=self)
        plotWindow = Plot1D(parent=subWindow, title='Profiles')
        plotWindow.setIndex(len(self.plotWindows()))
        subWindow.setWidget(plotWindow)
        subWindow.show()
        self.changed.emit()
        return plotWindow

    def addRixsPlot2D(self, profileWindow=None):
        """Add a RixPlot2D window in the mdi Area"""
        subWindow = MdiSubWindow(parent=self)
        profileWindow = profileWindow or self._profileWindow
        plotWindow = RixsPlot2D(parent=subWindow,
                                profileWindow=profileWindow,
                                overlayColors=self._overlayColors)
        plotWindow.setIndex(len(self.plotWindows()))
        subWindow.setWidget(plotWindow)
        subWindow.show()
        self.changed.emit()
        return plotWindow

    def getProfileWindow(self):
        return self._profileWindow


class RixsMainWindow(qt.QMainWindow):

    def __init__(self, parent=None):

        super(RixsMainWindow, self).__init__(parent=parent)

        if parent is not None:
            #: behave as a widget
            self.setWindowFlags(qt.Qt.Widget)
        else:
            #: main window
            self.setWindowTitle('RIXS_VIEW')

        #: Plot Area
        self._plotArea = RixsPlotArea(self)
        self.setCentralWidget(self._plotArea)
        self.setMinimumSize(600, 600)

    def addRixsDOIDockWidget(self, plot):
        self._roiDock = RixsROIDockWidget(plot, parent=self)
        self.addDockWidget(qt.Qt.LeftDockWidgetArea, self._roiDock)

    def getPlotArea(self):
        return self._plotArea

    def getProfileWindow(self):
        return self.getPlotArea().getProfileWindow()

if __name__ == '__main__':
    pass
