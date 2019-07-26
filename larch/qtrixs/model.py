#!/usr/bin/env python
# coding: utf-8
"""
RIXS data model
"""
from larch.qtlib.model import TreeModel


class RixsTreeModel(TreeModel):
    """TreeModel customized for RIXS"""

    def __init__(self, parent=None):

        super(RixsTreeModel, self).__init__(parent=parent)


if __name__ == '__main__':
    pass
