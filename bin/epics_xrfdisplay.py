#!/usr/bin/env python
"""
Epics XRF Display App 
"""

import sys
import os
import epics

import time
import copy
from functools import partial

import wx
import wx.lib.mixins.inspection
import wx.lib.scrolledpanel as scrolled
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception
    
import wx.lib.colourselect  as csel
import numpy as np
import matplotlib
from wxmplot import PlotPanel

HAS_DV = False
try:
    import wx.dataview as dv
    HAS_DV = True
except:
    pass

from larch import Interpreter, use_plugin_path

use_plugin_path('math')
from mathutils import index_of

use_plugin_path('xrf')
use_plugin_path('xray')
use_plugin_path('wx')


from wxutils import (SimpleText, EditableListBox, Font,
                     pack, Popup, Button, get_icon, Check, MenuItem,
                     Choice, FileOpen, FileSave, fix_filename, HLine,
                     GridPanel, CEN, LEFT, RIGHT)

from periodictable import PeriodicTablePanel


from xrfdisplay import XRFDisplayFrame


class EpicsXRFDisplayFrame(XRFDisplayFrame):
    _about = """Epics XRF Spectra Display
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, _larch=None, parent=None, mca=None, 
                 size=(725, 550), 
                 title='Epics XRF Display', 
                 output_title='XRF', **kws):
        XRFDisplayFrame.__init__(self, _larch=_larch, parent=parent,
                                 title=title, size=size, **kws)

    def createCustomMenus(self, fmenu):
        MenuItem(self, fmenu, "Connect Epics Detector\tCtrl+D",
                 "Connect to MCA or XSPress3 Detector", 
                 self.onConnectEpics)
        fmenu.AppendSeparator()


    def createMainPanel(self):
        print 'Epics create Main'
        epicspanel = self.creatEpicsPanel()
        ctrlpanel = self.createControlPanel()
        plotpanel = self.panel = self.createPlotPanel()

        tx, ty = self.wids['ptable'].GetBestSize()
        cx, cy = ctrlpanel.GetBestSize()
        px, py = plotpanel.GetBestSize()

        self.SetSize((max(cx, tx)+px, 25+max(cy, py)))

        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL

        bpanel = wx.Panel(self)

        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.Add(ctrlpanel, 0, style, 1)
        bsizer.Add(plotpanel, 1, style, 1)
        pack(bpanel, bsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(epicspanel, 0, style, 1)
        sizer.Add(bsizer,     1, style, 1)
        pack(self, sizer)

        wx.CallAfter(self.init_larch)
        self.set_roilist(mca=None)

    def creatEpicsPanel(self):
        pane = wx.Panel(self)
        psizer = wx.BoxSizer(wx.HORIZONTAL)
        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL
        for i in range(1, 5):
            b =  Button(pane, '%i' % i, size=(50, 50),
                        action=partial(self.onSelectDet, index=i))
            self.wids['det%i' % i] = b
            psizer.Add(b, 0, style, 1)
        pack(pane, psizer)        
        return pane

    def onSelectDet(self, event=None, index=-1, **kws):
        print 'on Select Det ', index

    def onConnectEpics(self, event=None, **kws):
        print 'on Connect Epics'


class EpicsXRFApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, **kws):
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        frame = EpicsXRFDisplayFrame() #
        frame.Show()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    EpicsXRFApp().MainLoop()
