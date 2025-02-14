#!/usr/bin/env python
"""Test larch.wxlib.cif_browser"""

import sys, os
import pytest
from pathlib import Path
from larch.wxlib.cif_browser import CIFViewer

toppath = Path(__file__).parent.parent
structpath = toppath / "examples" / "structuredata" / "struct2xas"


@pytest.mark.skipif(os.name == "nt" and sys.version_info < (3,10), reason="fails for windows and python3.9")
def test_cif2feff():
    cif_file = structpath / "ZnO_mp-2133.cif"
    viewer = CIFViewer(with_feff=True)
    frame = viewer.GetTopWindow()
    frame.onImportCIF(path=cif_file.as_posix())
    frame.onGetFeff()
    frame.onRunFeff()
    # viewer.MainLoop()


if __name__ == "__main__":
    test_cif2feff()
