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


from wxutils import (SimpleText, EditableListBox, Font, FloatCtrl,
                     pack, Popup, Button, get_icon, Check, MenuItem,
                     Choice, FileOpen, FileSave, fix_filename, HLine,
                     GridPanel, CEN, LEFT, RIGHT)

from periodictable import PeriodicTablePanel

from xrfdisplay import XRFDisplayFrame

class Empty(): pass

class DetectorSelecttDialog(wx.Dialog):
    """Connect to an Epics MCA detector 
    Can be either XIA xMAP  or Quantum XSPress3
    """
    msg = '''Select XIA xMAP or Quantum XSPress3 MultiElement MCA detector'''
    det_types = ('xmap', 'xspress3')
    def_prefix =  '13SDD1:'
    def_nelem  =  4
    def __init__(self, parent=None, prefix=None, dettype='xmap',
                 title='Select Epics MCA Detector'):

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        self.SetBackgroundColour((240, 240, 230))
        if parent is not None:
            self.SetFont(parent.GetFont())

        self.dettype = Choice(self,  size=(120, -1),
                              choices=self.det_types)

        self.prefix = wx.TextCtrl(self, -1, self.def_prefix, size=(120, -1))
        self.nelem = FloatCtrl(self, value=4, precision=0, minval=1,
                               size=(120, -1))


        btnsizer = wx.StdDialogButtonSizer()
        
        if wx.Platform != "__WXMSW__":
            btn = wx.ContextHelpButton(self)
            btnsizer.AddButton(btn)
        
        btn = wx.Button(self, wx.ID_OK)
        btn.SetHelpText("Use this detector")
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sty = LEFT|wx.ALIGN_CENTER_VERTICAL
        sizer = wx.GridBagSizer(5, 2)
        sizer.Add(SimpleText(self, 'MCA Type', size=(100, -1)), 
                  (0, 0), (1, 1), sty, 2)

        sizer.Add(SimpleText(self, 'Epics Prefix', size=(100, -1)), 
                  (1, 0), (1, 1), sty, 2)

        sizer.Add(SimpleText(self, '# Elements', size=(100, -1)), 
                  (2, 0), (1, 1), sty, 2)

        sizer.Add(self.dettype,
                  (0, 1), (1, 1), sty, 2)

        sizer.Add(self.prefix,
                  (1, 1), (1, 1), sty, 2)
        
        sizer.Add(self.nelem,
                  (2, 1), (1, 1), sty, 2)
        
        sizer.Add(wx.StaticLine(self, size=(225, 3), style=wx.LI_HORIZONTAL),
                  (3, 0), (1, 2), sty, 2)

        sizer.Add(btnsizer,
                  (4, 0), (1, 2), sty, 2)
        
        self.SetSizer(sizer)
        sizer.Fit(self)


class EpicsXRFDisplayFrame(XRFDisplayFrame):
    _about = """Epics XRF Spectra Display
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, parent=None, _larch=None, det_prefix=None, det_class=None,
                 size=(725, 550),  title='Epics XRF Display',
                 output_title='XRF', **kws):
        self.det_prefix = det_prefix
        self.det_class  = det_class
        self.nmcas = 4
        if det_prefix is None or det_class is None:
            self.prompt_for_detector()

        self.connect_to_detector(self)

        self.det_fore = -1
        self.det_back = -1
        XRFDisplayFrame.__init__(self, parent=parent, _larch=_larch,
                                 title=title, size=size, **kws)

    def prompt_for_detector(self):
        dlg = DetectorSelectDialog()
        dlg.Raise()
        if dlg.ShowModal() == wx.ID_OK:
            self.det_prefix = dlg.prefix.GetValue()
            self.det_class  = dlg.dettype.GetStringSelection()
            self.nmcas      = dlg.nelem.GetValue()
            dlg.Destroy()

    def connect_to_detector(self):
        print 'Prompt and got ', self.nmcas, self.det_prefix, self.det_class
        
        
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
            if index == self.det_fore:
                self.det_fore = -1
        else:
            self.det_fore = index
            if index == self.det_back:
                self.det_back = -1

        for i in range(1, 5):
            dname = 'det%i' % i
            col = (220, 220, 220)
            if i == self.det_fore:
                col = (20, 80, 200)
            elif i == self.det_back:
                col = (80, 200, 20)
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
