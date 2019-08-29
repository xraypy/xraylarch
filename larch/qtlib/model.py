#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This module provides a class to implement a tree model for
spectroscopy data.
"""
from __future__ import absolute_import, division
from silx.gui import qt

from .items import TreeItem, RootItem


class HeaderSection(object):

    def __init__(self, name, roles, delegate=None, removable=False):
        self.name = name
        self.roles = roles
        self.delegate = delegate
        self.removable = removable


class Header(list):

    def data(self, section, role=qt.Qt.DisplayRole):
        if role == qt.Qt.DisplayRole:
            try:
                return self[section].name
            except IndexError:
                return None

    def setData(self, section, value, role):
        if role == qt.Qt.EditRole:
            if value is None:
                try:
                    del self[section]
                    return True
                except IndexError:
                    return False
            else:
                try:
                    self[section] = value
                except IndexError:
                    self.append(value)
                return True
        return False

    def attrNameData(self, section, role):
        try:
            return self[section].roles[role]
        except (IndexError, KeyError):
            return None

    def attrNameSetData(self, section, role):
        if role == qt.Qt.EditRole:
            try:
                return self[section].roles[qt.Qt.DisplayRole]
            except (IndexError, KeyError):
                return None

    def flags(self, section):
        try:
            roles = self[section].roles
        except IndexError:
            return None

        if qt.Qt.EditRole in roles:
            return qt.Qt.ItemIsEditable
        return None

    def delegate(self, section):
        try:
            return self[section].delegate
        except IndexError:
            return None


class TreeModel(qt.QAbstractItemModel):

    def __init__(self, parent=None):
        super(TreeModel, self).__init__(parent=parent)
        self.rootItem = RootItem()
        self.header = Header()
        section = 0
        orientation = qt.Qt.Horizontal
        value = HeaderSection(
            name='Name', roles={
                qt.Qt.DisplayRole: 'name', qt.Qt.EditRole: 'name'})
        self.setHeaderData(section, orientation, value)

    def index(self, row, column, parent):
        """Return the index of the item in the model specified by the
        row, column, and parent index.
        """
        # If the item has no parent it is the root item. Otherwise, get
        # the parent item from the parent index.
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = self.itemFromIndex(parent)

        # Get the child at the position specified by the row.
        childItem = parentItem.child(row)

        # If the child item exists, create an index for it.
        if childItem is not None:
            return self.createIndex(row, column, childItem)
        else:
            return qt.QModelIndex()

    def parent(self, index):
        """Return the index of the parent for a child index."""
        # Use the index of the child to get the child item.
        childItem = self.itemFromIndex(index)
        # Call the parent() method of the child to get the parent item.
        parentItem = childItem.parent()

        # If the parent item is not the root item, create an index for it.
        if parentItem == self.rootItem:
            return qt.QModelIndex()
        else:
            return self.createIndex(parentItem.childPosition(), 0, parentItem)

    def rowCount(self, parent=qt.QModelIndex()):
        item = self.itemFromIndex(parent)
        return item.childCount()

    def columnCount(self, parent=qt.QModelIndex()):
        return len(self.header)

    def data(self, index, role=qt.Qt.DisplayRole):
        item = self.itemFromIndex(index)
        section = index.column()
        name = self.header.attrNameData(section, role)
        return item.data(section, name, role)

    def setData(self, index, value, role=qt.Qt.EditRole):
        item = self.itemFromIndex(index)
        section = index.column()
        name = self.header.attrNameSetData(section, role)
        if item.setData(section, name, value, role):
            self.dataChanged.emit(index, index)
            return True
        return False

    def itemFromIndex(self, index):
        if index.isValid():
            return index.internalPointer()
        else:
            return self.rootItem

    def indexFromItem(self, item):
        if item == self.rootItem:
            return qt.QModelIndex()
        else:
            return self.createIndex(item.childPosition(), 0, item)

    def flags(self, index):
        section = index.column()
        item = self.itemFromIndex(index)
        flags = self.header.flags(section)
        name = self.header.attrNameData(section, qt.Qt.DisplayRole)
        data = item.data(section, name, qt.Qt.DisplayRole)
        if flags is not None and data is not None:
            return flags | item.flags(section)
        else:
            return item.flags(section)

    def headerData(self, section, orientation, role):
        if orientation == qt.Qt.Horizontal:
            return self.header.data(section, role)

    def setHeaderData(self, section, orientation, value, role=qt.Qt.EditRole):
        if orientation == qt.Qt.Horizontal:
            if self.header.setData(section, value, role):
                self.headerDataChanged.emit(orientation, section, section)
                return True
        return False

    def insertRows(self, row, count, parent=qt.QModelIndex()):
        parentItem = self.itemFromIndex(parent)
        topLeft = self.index(row, 0, parent)
        bottomRight = self.index(row + count - 1, 0, parent)

        self.beginInsertRows(parent, row, row + count - 1)
        result = parentItem.insertRows(row, count)
        self.endInsertRows()

        self.dataChanged.emit(topLeft, bottomRight)

        return result

    def removeRows(self, row, count, parent=qt.QModelIndex()):
        parentItem = self.itemFromIndex(parent)
        topLeft = self.index(row, 0, parent)
        bottomRight = self.index(row + count - 1, 0, parent)

        self.beginRemoveRows(parent, row, row + count - 1)
        result = parentItem.removeRows(row, count)
        self.endRemoveRows()

        self.dataChanged.emit(topLeft, bottomRight)

        return result

    def insertRow(self, row, item):
        """Inserts a row at row containing item."""
        parentItem = item.parentItem
        parent = self.indexFromItem(parentItem)

        self.beginInsertRows(parent, row, row)
        parentItem.childItems.insert(row, item)
        self.endInsertRows()

        index = self.index(row, 0, parent)
        self.dataChanged.emit(index, index)

        return True

    def appendRow(self, item):
        parentItem = item.parentItem
        self.insertRow(parentItem.childCount(), item)

    def visitModel(self, parent=qt.QModelIndex(), columns=False):
        for row in range(self.rowCount(parent)):
            if columns:
                for column in range(self.columnCount(parent)):
                    index = self.index(row, column, parent)
                    yield index
            else:
                index = self.index(row, 0, parent)
                yield index

            index = self.index(row, 0, parent)
            for index in self.visitModel(index, columns):
                yield index

    def setModelData(self, data, parent=qt.QModelIndex()):
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = self.itemFromIndex(parent)

        for name in data:
            item = TreeItem(name=name, parentItem=parentItem)
            self.appendRow(item)
            if data is not None and isinstance(data[name], dict):
                index = self.indexFromItem(item)
                self.setModelData(data=data[name], parent=index)
