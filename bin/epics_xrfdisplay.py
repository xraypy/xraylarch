#!/usr/bin/env python
"""
GSECARS Epics XRF Display App 
"""
import larch
larch.use_plugin_path('epics')

from xrfcontrol import EpicsXRFApp
EpicsXRFApp().MainLoop()

