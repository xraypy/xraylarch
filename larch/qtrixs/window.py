#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Application window of RIXS GUI
==============================
"""
from silx.gui import qt

from larch.utils.logging import getLogger
from larch.qtlib.console import InternalIPyKernel
from larch.qtlib.model import HeaderSection
from larch.qtlib.delegates import ComboBoxDelegate

from .plotrixs import RixsPlotArea
from .view import RixsTreeView as RixsView
from .model import RixsTreeModel as RixsModel
from .items import RixsItem


class RixsAppWindow(qt.QMainWindow):
    """MainWindow may also behave as widget"""

    def __init__(self, parent=None, with_ipykernel=True, logger=None):
        """Constructor"""

        self._logger = logger or getLogger('RixsAppWindow')

        super(RixsAppWindow, self).__init__(parent=parent)

        if parent is not None:
            #: behave as a widget
            self.setWindowFlags(qt.Qt.Widget)
        else:
            #: main window
            self.setWindowTitle('RIXS_VIEW')

            # TODO: Add icon to the application
            #ico = qt.QIcon(os.path.join(_resourcesPath, "logo",
            #                            "xraysloth_logo_04.svg"))
            #self.setWindowIcon(ico)

        #: IPython kernel status
        self._with_ipykernel = with_ipykernel

        #: Model/view
        self._model = RixsModel()
        self._view = RixsView(parent=self)
        self._view.setModel(self._model)

        # Add additional sections to the header.
        values = [
            HeaderSection(name='Plot',
                          roles={qt.Qt.DisplayRole: 'currentPlotWindowIndex',
                                 qt.Qt.EditRole: 'plotWindowsIndexes'
                                 },
                          delegate=ComboBoxDelegate),
            ]

        for value in values:
            section = len(self._model.header)
            orientation = qt.Qt.Horizontal
            self._model.setHeaderData(section, orientation, value)

        # Add (empty) menu bar -> contents added later
        self._menuBar = qt.QMenuBar()
        self.setMenuBar(self._menuBar)
        self._initAppMenu()

        #: Plot Area
        self._plotArea = RixsPlotArea(self)
        self.setCentralWidget(self._plotArea)

        #: TreeView dock widget
        self._dockDataWidget = qt.QDockWidget(parent=self)
        self._dockDataWidget.setObjectName('Data View')
        self._dockDataWidget.setWidget(self._view)
        self.addDockWidget(qt.Qt.LeftDockWidgetArea, self._dockDataWidget)

        #: Plots update
        self._model.dataChanged.connect(self.updatePlot)
        self._plotArea.changed.connect(self.updateModel)

        #: Console
        if self._with_ipykernel:
            # Initialize internal ipykernel
            self._ipykernel = InternalIPyKernel()
            self._ipykernel.init_kernel(backend='qt')
            self._ipykernel.add_to_namespace('view', self._view)
            self._ipykernel.add_to_namespace('model', self._model)
            self._ipykernel.add_to_namespace('plot', self._plotArea)

            # Add IPython console at menu
            self._initConsoleMenu()
        else:
            self._ipykernel = None

    def updateModel(self):
        plotWindows = self._plotArea.plotWindows()
        for item in self._view.rixsItems():
            item.plotWindows = plotWindows
            if len(plotWindows) == 0:
                index = self._model.indexFromItem(item)
                self._model.dataChanged.emit(index, index)

    def updatePlot(self, *args):
        topLeft, bottomRight, _ = args

        topLeftItem = self._model.itemFromIndex(topLeft)
        bottomRightItem = self._model.itemFromIndex(bottomRight)

        if topLeftItem is not bottomRightItem:
            self._logger.error('The indices do not point to the same item in the model')
            return

        item = topLeftItem
        plotWindows = self._plotArea.plotWindows()

        if item.isChecked:
            if len(plotWindows) == 0:
                self._logger.info('There are no plot widgets available')
                return

        for plotWindow in plotWindows:
            plotWindow.remove(item.legend)
            if not plotWindow.getItems():
                plotWindow.reset()
            else:
                plotWindow.statusBar().clearMessage()

        rixsItems = self._view.rixsItems()
        if item.isChecked:
            if item in list(rixsItems) and isinstance(item, RixsItem):
                item.plot()

    def showEvent(self, event):
        self.loadSettings()
        super(RixsAppWindow, self).showEvent(event)

    def closeEvent(self, event):
        self.saveSettings()
        super(RixsAppWindow, self).closeEvent(event)

    def loadSettings(self):
        """TODO"""
        pass

    def saveSettings(self):
        """TODO"""
        pass

    # Populate the menu bar with common actions and shortcuts
    def _addMenuAction(self, menu, action, deferShortcut=False):
        """Add action to menu as well as self so that when the menu bar is
        invisible, its actions are still available. If deferShortcut
        is True, set the shortcut context to widget-only, where it
        will avoid conflict with shortcuts already bound to the
        widgets themselves.
        """
        menu.addAction(action)
        self.addAction(action)

        if deferShortcut:
            action.setShortcutContext(qt.Qt.WidgetShortcut)
        else:
            action.setShortcutContext(qt.Qt.ApplicationShortcut)

    def _initAppMenu(self):
        """Add application menu"""
        self._menuApp = self._menuBar.addMenu("Application")
        self._closeAppAction = qt.QAction("&Quit", self, shortcut="Ctrl+Q",
                                          triggered=self.onClose)
        self._addMenuAction(self._menuApp, self._closeAppAction)

    def _initConsoleMenu(self):
        self._menuConsole = self._menuBar.addMenu("Console")

        self._newConsoleAction = qt.QAction("&New Qt Console",
                                            self, shortcut="Ctrl+K",
                                            triggered=self._ipykernel.new_qt_console)
        self._addMenuAction(self._menuConsole, self._newConsoleAction)

    def onClose(self):
        if self._ipykernel is not None:
            self._ipykernel.cleanup_consoles()
        self.closeEvent(quit())


def main():
    from silx import sx
    sx.enable_gui()
    rx = RixsAppWindow()
    rx.show()
    input("Press ENTER to close the window...")


if __name__ == '__main__':
    main()
