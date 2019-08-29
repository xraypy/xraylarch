#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qt delegates
============
"""
from __future__ import absolute_import, division
from silx.gui import qt


class ComboBoxDelegate(qt.QStyledItemDelegate):

    def __init__(self, parent=None):
        super(ComboBoxDelegate, self).__init__(parent=parent)

    def createEditor(self, parent, option, index):
        editor = qt.QComboBox(parent)
        editor.setMinimumHeight(25)
        editor.currentIndexChanged.connect(self.commitDataAndClose)
        return editor

    def setEditorData(self, editor, index):
        model = index.model()
        values = model.data(index, qt.Qt.EditRole)
        currentText = model.data(index, qt.Qt.DisplayRole)
        editor.blockSignals(True)
        editor.addItems(values)
        editor.setCurrentText(currentText)
        editor.blockSignals(False)

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        model.setData(index, value, qt.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def commitDataAndClose(self):
        editor = self.sender()
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)


if __name__ == '__main__':
    pass
