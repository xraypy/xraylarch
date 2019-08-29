#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module provides classes to implement model items for spectroscopy data.
"""
from __future__ import absolute_import, division
import weakref

from silx.gui import qt
from silx.utils.weakref import WeakList

from larch.utils.logging import getLogger
_logger = getLogger('larch.qtlib.items')

__authors__ = ['Marius Retegan', 'Mauro Rovezzi']


class Signal(object):
    """Base class for signal objects."""

    def __init__(self):
        self._slots = WeakList()

    def connect(self, slot):
        """Register a slot.

        Adding an already registered slot has no effect.

        :param callable slot: The function or method to register.
        """
        if slot not in self._slots:
            self._slots.append(slot)
        else:
            _logger.warning('Ignoring addition of an already registered slot')

    def disconnect(self, slot):
        """Remove a previously registered slot.

        :param callable slot: The function or method to unregister.
        """
        try:
            self._slots.remove(slot)
        except ValueError:
            _logger.warning('Trying to remove a slot that is not registered')

    def emit(self, *args, **kwargs):
        """Notify all registered slots with the given parameters.

        Slots are called directly in this method.
        Slots are called in the order they were registered.
        """
        for slot in self._slots:
            slot(*args, **kwargs)


class TreeItem(object):

    def __init__(self, name=None, parentItem=None, isChecked=False):
        """Base class for items of the tree model.

        Use a weak reference for the parent item to avoid circular
        references, i.e. if the parent is destroyed, the child will only
        have a week reference to it, so the garbage collector will remove
        the parent object from memory.

        Using a weakref.proxy object for the parent makes the parentItem
        unhashable, which causes problem if they are used as dictionary keys.

        :param name: Name of the tree item, defaults to None
        :param parentItem: Parent of the tree item, defaults to None
        """
        self.name = name
        self._parentItem = None if parentItem is None else weakref.ref(parentItem)  # noqa
        self.isChecked = isChecked

        self.childItems = list()
        self.itemChanged = Signal()

    @property
    def parentItem(self):
        return self._parentItem() if self._parentItem is not None else None

    def child(self, row):
        try:
            return self.childItems[row]
        except KeyError:
            return None

    def data(self, column, name, role):
        if name is None:
            return None

        try:
            return getattr(self, name)
        except AttributeError:
            return None

    def setData(self, column, name, value, role):
        if name is None:
            return False

        try:
            setattr(self, name, value)
            return True
        except AttributeError:
            return False

    def parent(self):
        return self.parentItem

    def childPosition(self):
        if self.parentItem is not None:
            return self.parentItem.childItems.index(self)
        else:
            # The root item has no parent; for this item, we return zero
            # to be consistent with the other items.
            return 0

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return len(self.name)

    def lastChild(self):
        return self.childItems[-1]

    def insertRows(self, row, count):
        for i in range(count):
            name = 'TreeItem{}'.format(self.childCount())
            item = TreeItem(name=name, parentItem=self)
            self.childItems.insert(row, item)
            _logger.debug('Inserted {}'.format(name))
        return True

    def removeRows(self, row, count):
        try:
            childItem = self.childItems[row]
        except IndexError:
            return False

        for i in range(count):
            self.childItems.pop(row)

        _logger.debug('Removed {}'.format(childItem.name))
        return True

    def flags(self, column):
        return qt.Qt.ItemIsEnabled | qt.Qt.ItemIsSelectable

    @property
    def legend(self):
        tokens = list()
        tokens.append(self.name)

        parentItem = self.parentItem
        while parentItem is not None:
            if parentItem.name is not None:
                tokens.append(parentItem.name)
            parentItem = parentItem.parentItem

        tokens.reverse()
        return '/'.join(tokens)


class RootItem(TreeItem):
    """Root item of the TreeModel (not visible in the view)"""

    def __init__(self, name=None, parentItem=None):
        super(RootItem, self).__init__(name, parentItem)


class ExperimentItem(TreeItem):
    """Experiment as generic data container
    (appearing at root level in the view)

    Root
    +---> Experiment

    """

    def __init__(self, name=None, parentItem=None):
        super(ExperimentItem, self).__init__(name, parentItem)


class GroupItem(TreeItem):
    """Group item is equivalent to data group in HDF5"""

    def __init__(self, name=None, parentItem=None):
        super(GroupItem, self).__init__(name, parentItem)


class DatasetItem(TreeItem):
    """Dataset item is equivalent of dataset in HDF5"""

    def __init__(self, name=None, parentItem=None):
        super(DatasetItem, self).__init__(name, parentItem)


class FileItem(GroupItem):
    """Equivalent to h5py.File -> datagroup"""

    def __init__(self, name=None, parentItem=None):
        super(FileItem, self).__init__(name, parentItem)


class ScanItem(DatasetItem):
    """Dataset representing a 1D scan

    TODO: needs refactoring
    """

    def __init__(self, name=None, parentItem=None, isChecked=False, data=None):
        super(ScanItem, self).__init__(name, parentItem, isChecked)
        self._xLabel = None
        self._signalLabel = None
        self._monitorLabel = None
        self._plotWindows = None
        self._currentPlotWindow = None

        self.scanData = data

    def data(self, column, name, role):
        if role == qt.Qt.CheckStateRole:
            if column == 0:
                if self.isChecked:
                    return qt.Qt.Checked
                else:
                    return qt.Qt.Unchecked
        return super(ScanItem, self).data(column, name, role)

    def setData(self, column, name, value, role):
        if role == qt.Qt.CheckStateRole:
            if value == qt.Qt.Checked:
                self.isChecked = True
            else:
                self.isChecked = False
            return True
        return super(ScanItem, self).setData(column, name, value, role)

    def flags(self, column):
        flags = super(ScanItem, self).flags(column)
        if column == 0:
            return flags | qt.Qt.ItemIsUserCheckable
        else:
            return flags

    @property
    def xLabel(self):
        if self._xLabel is None:
            self._xLabel = list(self.counters)[0]
        return self._xLabel

    @xLabel.setter
    def xLabel(self, value):
        self._xLabel = value

    @property
    def signalLabel(self):
        if self._signalLabel is None:
            self._signalLabel = list(self.counters)[1]
        return self._signalLabel

    @signalLabel.setter
    def signalLabel(self, value):
        self._signalLabel = value

    @property
    def monitorLabel(self):
        if self._monitorLabel is None:
            self._monitorLabel = list(self.counters)[2]
        return self._monitorLabel

    @monitorLabel.setter
    def monitorLabel(self, value):
        self._monitorLabel = value

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

    @property
    def counters(self):
        return self.scanData['measurement']

    @property
    def command(self):
        return str(self.scanData['title'].value)

    @property
    def x(self):
        try:
            return self.counters[self.xLabel].value
        except KeyError:
            return None

    @property
    def signal(self):
        try:
            return self.counters[self.signalLabel].value
        except KeyError:
            return None

    @property
    def monitor(self):
        try:
            return self.counters[self.monitorLabel].value
        except KeyError:
            return None

    def plot(self):
        if self.x is None or self.signal is None:
            return

        x = self.x
        signal = self.signal
        legend = self.legend

        if 0 not in self.monitor:
            try:
                signal = signal / self.monitor
            except (TypeError, ValueError):
                pass

        if not self.currentPlotWindow.getItems():
            resetzoom = True
        else:
            resetzoom = False
        self.currentPlotWindow.addCurve(x, signal, legend=legend,
                                        resetzoom=resetzoom)
        self.currentPlotWindow.setGraphYLabel('Signal / Monitor')
