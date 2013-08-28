import wx
import epics

from lib.gui import ScanFrame, ScanApp

epics.ca.initialize_libca()
ScanApp().MainLoop()
