#!/usr/bin/env python
"""Test larch.wxlib.structure2feff_browser"""

import pytest
from pathlib import Path
import wx
from larch.wxlib.structure2feff_browser import Structure2FeffViewer

toppath = Path(__file__).parent.parent
structpath = toppath / "examples" / "structuredata" / "struct2xas"


def test_structure2feff():
    struct_file = structpath / "GaBr_single_frame.xyz"
    viewer = Structure2FeffViewer()
    frame = viewer.GetTopWindow()
    exit_timer = wx.Timer(frame)
    frame.Bind(wx.EVT_TIMER, frame.onClose, exit_timer)
    frame.onImportStructure(path=struct_file.as_posix())
    frame.onGetFeff()
    exit_timer.Start(15000)
    frame.onRunFeff()


if __name__ == "__main__":
    test_structure2feff()
