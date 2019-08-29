#!/usr/bin/env python
# coding: utf-8
"""
RIXS items
"""
from silx.gui import qt
from larch.qtlib.items import TreeItem


class RixsItem(TreeItem):
    """Qt item for adding RixsData to the application and handling plots interaction"""

    def __init__(self, name=None, parentItem=None, isChecked=False, data=None):

        super(RixsItem, self).__init__(name, parentItem, isChecked)
        self._plotWindows = None
        self._currentPlotWindow = None
        self._data = data

    def data(self, column, name, role):
        if role == qt.Qt.CheckStateRole:
            if column == 0:
                if self.isChecked:
                    return qt.Qt.Checked
                else:
                    return qt.Qt.Unchecked
        return super(RixsItem, self).data(column, name, role)

    def setData(self, column, name, value, role):
        if role == qt.Qt.CheckStateRole:
            if value == qt.Qt.Checked:
                self.isChecked = True
            else:
                self.isChecked = False
            return True
        return super(RixsItem, self).setData(column, name, value, role)

    def flags(self, column):
        flags = super(RixsItem, self).flags(column)
        if column == 0:
            return flags | qt.Qt.ItemIsUserCheckable
        else:
            return flags

    @property
    def currentPlotWindowIndex(self):
        if self.currentPlotWindow is not None:
            return str(self.currentPlotWindow.index())
        else:
            return None

    @currentPlotWindowIndex.setter
    def currentPlotWindowIndex(self, value):
        try:
            self._currentPlotWindowIndex = int(value)
        except ValueError:
            self.currentPlotWindow = None
        else:
            self.currentPlotWindow = self.plotWindows[self._currentPlotWindowIndex] # noqa

    @property
    def currentPlotWindow(self):
        if self._currentPlotWindow is None:
            if self.plotWindows:
                self._currentPlotWindow = self.plotWindows[0]
        else:
            if self._currentPlotWindow not in self.plotWindows:
                if self.plotWindows:
                    self._currentPlotWindow = self.plotWindows[0]
                else:
                    self._currentPlotWindow = None
        return self._currentPlotWindow

    @currentPlotWindow.setter
    def currentPlotWindow(self, value):
        self._currentPlotWindow = value

    @property
    def plotWindowsIndexes(self):
        indexes = list()
        if self.plotWindows is not None:
            for index, _ in enumerate(self.plotWindows):
                indexes.append(str(index))
        return indexes

    @property
    def plotWindows(self):
        return self._plotWindows

    @plotWindows.setter
    def plotWindows(self, value):
        self._plotWindows = value

    def _plot_rixs(self, plotWindow):
        """Plot rixs full plane"""
        plotWindow.addImage(self._data.rixs_map,
                            x=self._data.ene_in,
                            y=self._data.ene_out,
                            title=self._data.sample_name,
                            xlabel=self._data.ene_in_label,
                            ylabel=self._data.ene_out_label)

    def _plot_rixs_et(self, plotWindow):
        """Plot rixs_et full plane"""
        plotWindow.addImage(self._data.rixs_et_map,
                            x=self._data.ene_in,
                            y=self._data.ene_et,
                            title=self._data.sample_name,
                            xlabel=self._data.ene_in_label,
                            ylabel=self._data.ene_et_label)

    def _plot_rixs_crop(self, plotWindow):
        """Plot rixs_et crop_area plane"""
        _title = f"{self._data.sample_name} [CROP: {self._data._crop_area}]"
        plotWindow.addImage(self._data.rixs_map_crop,
                            x=self._data.ene_in_crop,
                            y=self._data.ene_out_crop,
                            title=_title,
                            xlabel=self._data.ene_in_label,
                            ylabel=self._data.ene_out_label)

    def _plot_rixs_et_crop(self, plotWindow):
        """Plot rixs_et crop_area plane"""
        _title = f"{self._data.sample_name} [CROP: {self._data._crop_area}]"
        plotWindow.addImage(self._data.rixs_et_map_crop,
                            x=self._data.ene_in_crop,
                            y=self._data.ene_et_crop,
                            title=_title,
                            xlabel=self._data.ene_in_label,
                            ylabel=self._data.ene_et_label)

    def plot(self, crop=False, rixs_et=False, nlevels=50):
        """Data plotter"""
        plotter = self.currentPlotWindow()
        if plotter is None:
            return
        plotter.reset()
        if type(crop) is tuple:
            self._data.crop(crop)
        if crop:
            if rixs_et:
                self._plot_rixs_et_crop(plotter)
            else:
                self._plot_rixs_crop(plotter)
        else:
            if rixs_et:
                self._plot_rixs_et(plotter)
            else:
                self._plot_rixs_et(plotter)
        plotter.addContours(nlevels)
        plotter.show()
