#!/usr/bin/env python
"""
Epics XRF Display App
"""

import sys
import os
# import epics

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

class Empty(): pass

class EpicsXRFDisplayFrame(XRFDisplayFrame):
    _about = """Epics XRF Spectra Display
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, detector=None, parent=None,
                 size=(725, 550),
                 title='Epics XRF Display',
                 output_title='XRF', **kws):
        if detector is None:
            print 'need to prompt for detector'
            detector = Empty()
        self.det = detector
        self.det.nmcas = 4
        self.det_fore = -1
        self.det_back = -1
        XRFDisplayFrame.__init__(self, parent=parent,
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

        # det button panel
        btnpanel = wx.Panel(pane)
        btnsizer = wx.GridBagSizer(2, 2)
        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL
        for i in range(1, 5):
            b =  Button(btnpanel, '%i' % i, size=(30, 30),
                        action=partial(self.onSelectDet, index=i))
            self.wids['det%i' % i] = b
            btnsizer.Add(b, (0, i), (1, 1), style, 1)
        pack(btnpanel, btnsizer)

        psizer.Add(btnpanel, 0, style, 1)

        x = self.wids['det_as_bkg'] = Check(pane, label='as bkg',
                                            default=False)
        psizer.Add(x, 0, style, 1)

        b =  Button(pane, 'Start', size=(60, 40),
                    action=partial(self.onCount))

        psizer.Add(b, 0, style, 1)
        pack(pane, psizer)
        return pane

    def onSelectDet(self, event=None, index=-1, **kws):
        print 'on Select Det ', index, self.wids['det_as_bkg'].IsChecked()
        isbkg = self.wids['det_as_bkg'].IsChecked()
        if isbkg:
            self.det_back = index
        else:
            self.det_fore = index
        for i in range(1, 5):
            dname = 'det%i' % i
            col = (220, 220, 220)
            if i == self.det_fore:
                col = (120, 120, 240)
            elif i == self.det_back:
                col = (120, 240, 120)
            print dname, col
            self.wids[dname].SetBackgroundColour(col)
        self.Refresh()

    def onConnectEpics(self, event=None, **kws):
        print 'on Connect Epics'

    def onCount(self, event=None, **kws):
        print 'on Count'

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
