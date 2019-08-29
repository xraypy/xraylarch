#!/usr/bin/env python
# coding: utf-8
"""
RIXS data model
"""
from silx.gui import qt
from larch.qtlib.model import TreeModel


class RixsTreeModel(TreeModel):
    """TreeModel customized for RIXS"""

    def __init__(self, parent=None):

        super(RixsTreeModel, self).__init__(parent=parent)


class RixsListModel(qt.QAbstractListModel):
    """Simple ListModel used in larch.qtrixs.plotrixs.RixsMainWindow"""

    def __init__(self, *args, data=None, **kwargs):
        """Constructor"""

        super(RixsListModel, self).__init__(*args, **kwargs)
        self._data = data or []

    def data(self, index, role):
        if role == qt.Qt.DisplayRole:
            row = index.row()
            rd = self._data[row]
            _name = "{0}: {1}".format(row, rd.sample_name)
            return _name

    def rowCount(self, index):
        return len(self._data)

    def appendRow(self, rxobj):
        self._data.append(rxobj)
        self.layoutChanged.emit()


if __name__ == '__main__':
    pass
