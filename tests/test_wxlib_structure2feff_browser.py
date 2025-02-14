#!/usr/bin/env python
"""Test larch.wxlib.structure2feff_browser"""

import pytest
from pathlib import Path
from larch.wxlib.structure2feff_browser import Structure2FeffViewer

toppath = Path(__file__).parent.parent
structpath = toppath / "examples" / "structuredata" / "struct2xas"


def test_structure2feff():
    struct_file = structpath / "GaBr_single_frame.xyz"
    viewer = Structure2FeffViewer()
    frame = viewer.GetTopWindow()
    frame.onImportStructure(path=struct_file.as_posix())
    frame.onGetFeff()
    frame.onRunFeff()
    # viewer.MainLoop()


if __name__ == "__main__":
    test_structure2feff()
