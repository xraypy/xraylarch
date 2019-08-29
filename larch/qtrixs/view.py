#!/usr/bin/env python
# coding: utf-8
"""
RIXS data view
"""
import os
from silx.gui import qt

from larch.qtlib.view import TreeView

from .rixsdata import RixsData
from .items import RixsItem


class RixsTreeView(TreeView):

    def __init__(self, parent=None):
        super(RixsTreeView, self).__init__(parent)

    def loadFiles(self):
        paths, _ = qt.QFileDialog.getOpenFileNames(
            self, 'Select Files to Load', os.getcwd(),
            'RixsData Files (*rixs.h5)')

        if not paths:
            return

        parent = self.selectionModel().selectedRows().pop()
        parentItem = self.model().itemFromIndex(parent)
        for path in paths:
            self.addFile(path, parentItem)

    def addFile(self, path=None, parentItem=None):
        if path is None:
            return

        # Add the file to the last added experiment item.
        if parentItem is None:
            parentItem = self.model().rootItem.lastChild()

        try:
            rdata = RixsData()
            rdata.load_from_h5(path)
        except Exception:
            return

        # Create a tree item for the file and add it to the experiment item.
        item = RixsItem(rdata.sample_name, parentItem, data=rdata)
        self.model().appendRow(item)

    def rixsItems(self):
        for index in self.model().visitModel():
            item = self.model().itemFromIndex(index)
            if isinstance(item, RixsItem):
                yield item


class RixsListView(qt.QListView):
    """Simple List View used in larch.qtrixs.plotrixs.RixsMainWindow"""

    def __init__(self, parent=None):
        super(RixsListView, self).__init__(parent)


if __name__ == '__main__':
    pass
