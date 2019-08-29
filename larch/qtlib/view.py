#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This module provides base classes to implement models for
spectroscopy data.
"""
from __future__ import absolute_import, division
import os

from silx.gui import qt
import silx.io

from .items import (ExperimentItem,
                    GroupItem,
                    FileItem,
                    ScanItem)

from larch.utils.logging import getLogger
_logger = getLogger('larch.qtlib.view')


class HorizontalHeaderView(qt.QHeaderView):

    def __init__(self, parent=None):
        super(HorizontalHeaderView, self).__init__(qt.Qt.Horizontal, parent)

        # Some properties
        self.setStretchLastSection(True)
        # self.setSectionsMovable(True)

        # Context menu
        self.setContextMenuPolicy(qt.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

    def showContextMenu(self, position):
        menu = qt.QMenu('Horizontal Header View Menu', self)

        section = self.logicalIndexAt(position)

        action = qt.QAction('Add', self, triggered=self.append)
        menu.addAction(action)

        action = qt.QAction('Remove', self,
                            triggered=lambda: self.remove(section))
        menu.addAction(action)

        menu.exec_(self.mapToGlobal(position))

    def append(self):
        pass

    def remove(self, section):
        model = self.model()
        if not model.header[section].removable:
            _logger.info('The selected column cannot be removed')
            return
        model.setHeaderData(section, orientation=qt.Qt.Horizontal, value=None)
        view = self.parent()
        view.setItemsDelegates()


class TreeView(qt.QTreeView):

    def __init__(self, parent=None):
        super(TreeView, self).__init__(parent)

        # Header
        headerView = HorizontalHeaderView()
        self.setHeader(headerView)

        # Context menu
        self.setContextMenuPolicy(qt.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        # Selection mode
        self.setSelectionMode(qt.QAbstractItemView.ExtendedSelection)

    def setModel(self, model):
        super(TreeView, self).setModel(model)
        self.setItemsDelegates()

    def setItemsDelegates(self):
        if self.model() is None:
            return

        header = self.model().header
        for i, _ in enumerate(header):
            delegate = header.delegate(i)
            if delegate is not None:
                self.setItemDelegateForColumn(i, delegate(parent=self))

    def showContextMenu(self, position):
        menu = qt.QMenu('Tree View Menu', self)

        action = qt.QAction(
            'Add Experiment', self, triggered=self.addExperiment)
        menu.addAction(action)

        # Get the index under the cursor.
        index = self.indexAt(position)
        item = self.model().itemFromIndex(index)

        if isinstance(item, ExperimentItem) or isinstance(item, GroupItem):
            action = qt.QAction('Add Group', self, triggered=self.addGroup)
            menu.addAction(action)

            action = qt.QAction('Load Files', self, triggered=self.loadFiles)
            menu.addAction(action)

        # If there are selected indexes, they can be removed or checked.
        if self.selectedIndexes():
            menu.addSeparator()
            action = qt.QAction(
                'Toggle Selected', self, triggered=self.toggleSelected)
            menu.addAction(action)
            action = qt.QAction(
                'Remove Selected', self, triggered=self.removeSelected)
            menu.addAction(action)

        if isinstance(item, ScanItem) and index.column() > 0:
            menu.addSeparator()
            action = qt.QAction(
                'Copy Value to Selected', self,
                triggered=lambda: self.copyValueToSelected(index))
            menu.addAction(action)

            action = qt.QAction(
                'Copy Value to Toggled', self,
                triggered=lambda: self.copyValueToToggled(index))
            menu.addAction(action)

        menu.exec_(self.mapToGlobal(position))

    def loadFiles(self):
        paths, _ = qt.QFileDialog.getOpenFileNames(
            self, 'Select Files to Load', os.getcwd(),
            'Data Files (*.spec *.hdf5);; All Files (*)')

        if not paths:
            return

        parent = self.selectionModel().selectedRows().pop()
        parentItem = self.model().itemFromIndex(parent)
        for path in paths:
            self.addFile(path, parentItem)

    def addExperiment(self, name=None):
        rootItem = self.model().rootItem
        row = rootItem.childCount()
        if name is None or not name:
            name = 'Experiment{}'.format(row)
        item = ExperimentItem(name=name, parentItem=rootItem)
        self.model().appendRow(item)
        return item

    def addGroup(self, name=None, parentItem=None):
        """Add a generic GroupItem at a given parentItem"""
        # Add the file to the last added item.
        if parentItem is None:
            parent = self.selectionModel().selectedRows().pop()
            parentItem = self.model().itemFromIndex(parent)
        row = parentItem.childCount()

        if name is None or not name:
            name = 'Group{}'.format(row)

        item = GroupItem(name, parentItem)
        self.model().appendRow(item)

    def addFile(self, path=None, parentItem=None):
        if path is None:
            return

        # Add the file to the last added experiment item.
        if parentItem is None:
            parentItem = self.model().rootItem.lastChild()

        try:
            data = silx.io.open(path)
        except OSError as e:
            _logger.warning(e)
            return

        # Create a tree item for the file and add it to the experiment item.
        name, _ = os.path.splitext(os.path.basename(path))
        item = FileItem(name, parentItem)
        self.model().appendRow(item)

        # Create a tree item for each scan. The parent item is now the
        # previous file item.
        # TODO: Make this more "intelligent" by using the command to
        # set better defaults for x, signal, etc.
        parentItem = item
        for scan in data:
            item = ScanItem(name=scan, parentItem=parentItem, data=data[scan])
            self.model().appendRow(item)

    def selectedItems(self):
        indexes = self.selectionModel().selectedRows()
        items = [self.model().itemFromIndex(index) for index in indexes]
        return items

    def scanItems(self):
        for index in self.model().visitModel():
            item = self.model().itemFromIndex(index)
            if isinstance(item, ScanItem):
                yield item

    def toggleSelected(self):
        for item in self.selectedItems():
            index = self.model().indexFromItem(item)
            try:
                if item.isChecked:
                    self.model().setData(
                        index, qt.Qt.Unchecked, qt.Qt.CheckStateRole)
                else:
                    self.model().setData(
                        index, qt.Qt.Checked, qt.Qt.CheckStateRole)
            except AttributeError:
                pass

    def removeSelected(self):
        items = self.selectedItems()
        parentItems = dict()
        for item in items:
            parentItem = item.parentItem
            remove = True
            while parentItem is not self.model().rootItem:
                if parentItem in items:
                    remove = False
                    break
                parentItem = parentItem.parentItem
            # If an ancestors is selected for removal, pass the item.
            if not remove:
                continue

            # Get the parent item for the current item.
            parentItem = item.parentItem
            if parentItem not in parentItems:
                parentItems[parentItem] = list()
            # Create a list with the positions of the children that are
            # going to be removed.
            parentItems[parentItem].append(item.childPosition())

        # Remove the rows from the parent.
        for parentItem in parentItems:
            rows = parentItems[parentItem]
            parent = self.model().indexFromItem(parentItem)
            for row in reversed(sorted(rows)):
                self.model().removeRow(row, parent)

    def copyValueToToggled(self, indexAt):
        """Copy the value under the cursor to the toggled items."""
        indexes = self.model().visitModel(columns=True)
        for index in indexes:
            item = self.model().itemFromIndex(index)
            if not item.isChecked or index == indexAt:
                continue
            elif index.column() == indexAt.column():
                value = self.model().data(indexAt)
                self.model().setData(index, value)

    def copyValueToSelected(self, indexAt):
        """Copy the value under the cursor to the selected indexes."""
        indexes = self.selectionModel().selectedIndexes()
        for index in indexes:
            if index == indexAt:
                continue
            elif index.column() == indexAt.column():
                value = self.model().data(indexAt)
                self.model().setData(index, value)
