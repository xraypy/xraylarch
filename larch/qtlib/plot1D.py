#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Custom version of SILX Plot1D
=============================

This class is based on:

- https://github.com/mretegan/crispy/blob/master/crispy/gui/widgets/plotwidget.py
- https://github.com/silx-kit/silx/blob/master/examples/plotCurveLegendWidget.py

"""
from __future__ import absolute_import, division, unicode_literals
import functools
from silx.gui import qt
from silx.gui.plot import PlotWindow
from silx.gui.plot.tools.CurveLegendsWidget import CurveLegendsWidget
from silx.gui.widgets.BoxLayoutDockWidget import BoxLayoutDockWidget


class CustomCurveLegendsWidget(CurveLegendsWidget):
    """Extension of CurveLegendWidget.

    .. note:: Taken from SILX examples -> plotCurveLegendWidget

    This widget adds:
    - Set a curve as active with a left click its the legend
    - Adds a context menu with content specific to the hovered legend
    :param QWidget parent: See QWidget
    """

    def __init__(self, parent=None):
        super(CustomCurveLegendsWidget, self).__init__(parent)

        # Activate/Deactivate curve with left click on the legend widget
        self.sigCurveClicked.connect(self._switchCurveActive)

        # Add a custom context menu
        self.setContextMenuPolicy(qt.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)

    def _switchCurveActive(self, curve):
        """Set a curve as active.
        This is called from the context menu and when a legend is clicked.
        :param silx.gui.plot.items.Curve curve:
        """
        plot = curve.getPlot()
        plot.setActiveCurve(
            curve.getLegend() if curve != plot.getActiveCurve() else None)

    def _switchCurveVisibility(self, curve):
        """Toggle the visibility of a curve
        :param silx.gui.plot.items.Curve curve:
        """
        curve.setVisible(not curve.isVisible())

    def _switchCurveYAxis(self, curve):
        """Change the Y axis a curve is attached to.
        :param silx.gui.plot.items.Curve curve:
        """
        yaxis = curve.getYAxis()
        curve.setYAxis('left' if yaxis == 'right' else 'right')

    def _copyCurve(self, curve, plot):
        """Copy curve"""
        data = curve.getData()
        legend = curve.getLegend() + '*'
        plot.addCurve(data[0], data[1], legend=legend)

    def _clearPlot(self, plot):
        """Clear plot"""
        plot.clear()

    def _contextMenu(self, pos):
        """Create a show the context menu.
        :param QPoint pos: Position in this widget
        """
        curve = self.curveAt(pos)  # Retrieve curve from hovered legend
        if curve is not None:
            menu = qt.QMenu()  # Create the menu

            # Add an action to activate the curve
            activeCurve = curve.getPlot().getActiveCurve()
            menu.addAction('Unselect' if curve == activeCurve else 'Select',
                           functools.partial(self._switchCurveActive, curve))

            # Add an action to show/hide the curve
            menu.addAction('Hide' if curve.isVisible() else 'Show',
                           functools.partial(self._switchCurveVisibility, curve))

            # Add an action to store a copy of the curve
            plot = curve.getPlot()
            menu.addAction('Copy', functools.partial(self._copyCurve, curve, plot))

            # Add an action to switch the Y axis of a curve
            yaxis = 'right' if curve.getYAxis() == 'left' else 'left'
            menu.addAction('Map to %s' % yaxis,
                           functools.partial(self._switchCurveYAxis, curve))

            menu.addSeparator()

            # Add an action to clear the plot
            plot = curve.getPlot()
            menu.addAction('Clear plot', functools.partial(self._clearPlot, plot))

            globalPosition = self.mapToGlobal(pos)
            menu.exec_(globalPosition)


class Plot1D(PlotWindow):
    """Custom PlotWindow instance targeted to 1D curves"""

    def __init__(self, parent=None, backend=None, title='Plot1D'):
        """Constructor"""
        super(Plot1D, self).__init__(parent=parent, backend=backend,
                                     resetzoom=True, autoScale=True,
                                     logScale=True, grid=False,
                                     curveStyle=True, colormap=False,
                                     aspectRatio=False, yInverted=False,
                                     copy=True, save=True, print_=True,
                                     control=False, position=True, roi=False,
                                     mask=False, fit=True)
        self._index = None
        self._title = title
        self.setWindowTitle(self._title)

        # Active curve behaviour
        # TODO: https://github.com/silx-kit/silx/blob/5035be343dc37ef60eab114c139016ebd9832d96/silx/gui/plot/test/testPlotWidget.py#L636
        self.setActiveCurveHandling(True)

        self.setDataMargins(0, 0, 0.05, 0.05)

        # Create a MyCurveLegendWidget associated to the plot
        self.legendsWidget = CustomCurveLegendsWidget()
        self.legendsWidget.setPlotWidget(self)

        # Add the CurveLegendsWidget as a dock widget to the plot
        self.dock = BoxLayoutDockWidget()
        self.dock.setWindowTitle('Legend (right click for menu)')
        self.dock.setWidget(self.legendsWidget)
        self.addDockWidget(qt.Qt.RightDockWidgetArea, self.dock)

        # Show the plot and run the QApplication
        self.setAttribute(qt.Qt.WA_DeleteOnClose)

    def index(self):
        if self._index is None:
            self._index = 0
        return self._index

    def setIndex(self, value):
        self._index = value
        if self._index is not None:
            self.setWindowTitle('{0}: {1}'.format(self._index, self._title))

    def reset(self):
        self.clear()
        self.setGraphTitle()
        self.setGraphXLabel('X')
        # self.setGraphXLimits(0, 100)
        self.setGraphYLabel('Y')
        # self.setGraphYLimits(0, 100)


def main():
    """Run a Qt app with the widget"""
    app = qt.QApplication([])
    widget = Plot1D()
    widget.show()
    app.exec_()


if __name__ == '__main__':
    main()
