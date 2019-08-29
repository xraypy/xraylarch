#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Plot RIXS data
==============
"""
from silx.gui import qt
from silx.gui.plot.actions import PlotAction
from silx.gui.plot.tools.roi import RegionOfInterestManager
from silx.gui.plot.tools.roi import RegionOfInterestTableWidget
# from silx.gui.plot.items.roi import RectangleROI
from silx.gui.plot.items import LineMixIn, SymbolMixIn
from larch.utils.logging import getLogger
from larch.qtlib.plotarea import PlotArea, MdiSubWindow
from larch.qtlib.plot1D import Plot1D
from larch.qtlib.plot2D import Plot2D
from .profiletoolbar import (_DEFAULT_OVERLAY_COLORS, RixsProfileToolBar)
from .view import RixsListView
from .model import RixsListModel

_logger = getLogger("larch.qtrixs.plotrixs")


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
        raise NotImplementedError

    def rotateImage(self):
        """"""
        return


class RixsPlot2D(Plot2D):
    """RIXS equivalent of Plot2D"""

    def __init__(self, parent=None, backend=None, logger=None,
                 profileWindow=None, overlayColors=None, title="RixsPlot2D"):
        """Constructor"""
        super(RixsPlot2D, self).__init__(parent=parent, backend=backend, title=title)

        self._title = title
        self._logger = logger or _logger
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

    def __init__(self, parent=None, profileWindow=None, overlayColors=None,
                 logger=None):
        super(RixsPlotArea, self).__init__(parent=parent)

        self._logger = logger or _logger
        self._overlayColors = overlayColors or _DEFAULT_OVERLAY_COLORS
        self._profileWindow = profileWindow or self._addProfileWindow()
        self.addRixsPlot2D()
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

    def __init__(self, parent=None, logger=None):

        super(RixsMainWindow, self).__init__(parent=parent)

        self._logger = logger or _logger

        if parent is not None:
            #: behave as a widget
            self.setWindowFlags(qt.Qt.Widget)
        else:
            #: main window
            self.setWindowTitle('RIXS_VIEW')

        self.setGeometry(0, 0, 1280, 960)

        #: Model (= simple RixsData container)
        self._model = RixsListModel()

        #: View (= simply show list of loaded data)
        self._view = RixsListView(parent=self)
        self._view.setModel(self._model)

        #: View dock widget
        self._dockDataWidget = qt.QDockWidget(parent=self)
        self._dockDataWidget.setObjectName('Data View')
        self._dockDataWidget.setWidget(self._view)
        self.addDockWidget(qt.Qt.LeftDockWidgetArea, self._dockDataWidget)

        #: Plot Area
        self._plotArea = RixsPlotArea(self)
        self.setCentralWidget(self._plotArea)
        self.setMinimumSize(600, 600)

        #: TODO Tab widget containing Cursors Infos dock widgets
        # self._tabCurInfos = qt.QTabWidget(parent=self)
        # self._tabCurInfos.setLayoutDirection(qt.Qt.LeftToRight)
        # self._tabCurInfos.setDocumentMode(False)
        # self._tabCurInfos.setTabsClosable(False)
        # self._tabCurInfos.setMovable(False)
        # self._dockCurInfos = qt.QDockWidget('Plot Cursors Infos', self)
        # self.addDockWidget(qt.Qt.BottomDockWidgetArea, self._dockCurInfos)
        # self._dockCurInfos.setWidget(self._tabCurInfos)

    def _plot_rixs(self, rd, pw):
        """Plot rixs full plane"""
        pw.addImage(rd.rixs_map, x=rd.ene_in, y=rd.ene_out,
                    title=rd.sample_name,
                    xlabel=rd.ene_in_label,
                    ylabel=rd.ene_out_label)

    def _plot_rixs_et(self, rd, pw):
        """Plot rixs_et full plane"""
        pw.addImage(rd.rixs_et_map, x=rd.ene_in, y=rd.ene_et,
                    title=rd.sample_name,
                    xlabel=rd.ene_in_label,
                    ylabel=rd.ene_et_label)

    def _plot_rixs_crop(self, rd, pw):
        """Plot rixs_et crop_area plane"""
        _title = f"{rd.sample_name} [CROP: {rd._crop_area}]"
        pw.addImage(rd.rixs_map_crop, x=rd.ene_in_crop, y=rd.ene_out_crop,
                    title=_title,
                    xlabel=rd.ene_in_label,
                    ylabel=rd.ene_out_label)

    def _plot_rixs_et_crop(self, rd, pw):
        """Plot rixs_et crop_area plane"""
        _title = f"{rd.sample_name} [CROP: {rd._crop_area}]"
        pw.addImage(rd.rixs_et_map_crop,
                    x=rd.ene_in_crop,
                    y=rd.ene_et_crop,
                    title=_title,
                    xlabel=rd.ene_in_label,
                    ylabel=rd.ene_et_label)

    def plot(self, dataIndex, plotIndex,
             crop=False, rixs_et=False,
             nlevels=50):
        """Plot given data index to given plot"""
        rd = self.getData(dataIndex)
        pw = self.getPlotWindow(plotIndex)
        if rd is None or pw is None:
            return
        pw.reset()
        if type(crop) is tuple:
            rd.crop(crop)
        if crop:
            if rixs_et:
                self._plot_rixs_et_crop(rd, pw)
            else:
                self._plot_rixs_crop(rd, pw)
        else:
            if rixs_et:
                self._plot_rixs_et(rd, pw)
            else:
                self._plot_rixs(rd, pw)
        pw.addContours(nlevels)

    def getData(self, index):
        try:
            return self._model._data[index]
        except IndexError:
            self._logger.error("data index is wrong")
            self._logger.info("use 'addData' to add new data to the list")
            return None

    def getPlotWindow(self, index):
        try:
            return self._plotArea.getPlotWindow(index)
        except IndexError:
            self._plotArea.addRixsPlot2D()
            self._logger.warning("plot index wrong -> created a new RixsPlot2D")
            return self._plotArea.getPlotWindow(-1)

    def addData(self, data):
        """Append RixsData object to the model"""
        self._model.appendRow(data)

    def addRixsDOIDockWidget(self, plotIndex):
        plot = self.getPlotWindow(plotIndex)
        _roiDock = RixsROIDockWidget(plot, parent=self)
        self.addDockWidget(qt.Qt.BottomDockWidgetArea, _roiDock)

    def getPlotArea(self):
        return self._plotArea

    def getProfileWindow(self):
        return self.getPlotArea().getProfileWindow()


if __name__ == '__main__':
    pass
