#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DataGroup: generic tree-like container for data objects
==========================================================

This module implements a tree-like model for storing data in Larch.

The model is composed of a RootDataGroup at the top of the tree, which contains
zero or more ChildDataGroup objects. Each ChildDataGroup object contains zero or
more additional ChildDataGroup objects, allowing for an arbitrarily deep tree
structure.

The model is designed to be used as functional programming with the larch
library, that is, a Larch function takes a datagroup as input and returns it
after execution.

"""

from dataclasses import dataclass
from typing import List
import numpy as np
from silx.io import commonh5
from larch import Group


@dataclass
class DataGroup(Group):
    name: str
    children: List[DataGroup]


@dataclass
class RootDataGroup(DataGroup):
    pass


@dataclass
class ChildDataGroup(DataGroup):
    parent: DataGroup = None

    def __post_init__(self):
        if self.parent:
            self.parent.children.append(self)


@dataclass
class XYGroup(ChildDataGroup):
    x: np.ndarray
    y: np.ndarray


@dataclass
class XASGroup(ChildDataGroup):
    mode: str

    @property
    def energy(self) -> np.ndarray:
        return self.x

    @property
    def mu(self) -> np.ndarray:
        return self.y


def test_datagroups():
    """Test example for :mod:`larch.datagroups`"""
    t = RootDataGroup()
    t._logger.info("Data model example: 't' is the root instance")
    t.add_group("Z9entry1", cls=EntryGroup)
    t.add_group("A0entry2")
    t["Z9entry1"].add_group("ZZsubentry1")
    t["Z9entry1"].add_group("ZAsubentry2")
    t["A0entry2"].add_group("AAsubentry1")
    t["A0entry2"].add_group("AZsubentry2")
    t["A0entry2/AZsubentry2"].add_group("Bsubsubentry1")
    t["A0entry2/AZsubentry2"].add_group("Dsubsubentry2")
    t["A0entry2/AZsubentry2"].add_group("Asubsubentry3")

    #: +dataset
    x = np.arange(10)
    t["Z9entry1"].add_dataset("x", x)
    t["Z9entry1/ZZsubentry1"].add_dataset("x", x)

    t._logger.info("print(t):\n%s", t)

    if write:
        import tempfile
        #: +write to file
        ft = tempfile.mkstemp(prefix="test_", suffix=".h5")
        t.write_to_h5(ft)

    if view:
        from silx import sx

        sx.enable_gui()
        # from silx.app.view.Viewer import Viewer
        # v = Viewer()
        # v.appendFile(ft)
        # v.setMinimumSize(1280, 800)
        # v.show()
        from sloth.gui.hdf5.view import TreeViewWidget

        v = TreeViewWidget()
        # v.model().appendFile(t._fname_out)
        v.model().insertH5pyObject(t)
        v.show()
        input("Press ENTER to close the view window...")

    return t


if __name__ == "__main__":
    pass
