#!/usr/bin/env python
"""
Viewer App for ASCII Column Data
"""
import os
import larch
from larch_plugins.wx import ScanViewer

os.chdir(larch.site_config.home_dir)
ScanViewer().run()
