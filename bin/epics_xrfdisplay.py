#!/usr/bin/env python
"""
Epics XRF Display App
"""

import sys
import os

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

import epics
from epics.devices.mca import MCA, MultiXMAP
from epics.wx import EpicsFunction, DelayedEpicsCallback


class Empty(): pass

class DetectorSelectDialog(wx.Dialog):
    """Connect to an Epics MCA detector 
    Can be either XIA xMAP  or Quantum XSPress3
    """
    msg = '''Select XIA xMAP or Quantum XSPress3 MultiElement MCA detector'''
    det_types = ('xmap', 'xspress3')
    def_prefix =  '13SDD1:'
    def_nelem  =  4
    def __init__(self, parent=None, prefix=None, det_type='xmap', nmca=4,
                 title='Select Epics MCA Detector'):
        if prefix is None: prefix = self.def_prefix
        if det_type not in self.det_types:
            det_type = self.det_types[0]
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        self.SetBackgroundColour((240, 240, 230))
        if parent is not None:
            self.SetFont(parent.GetFont())

        self.dettype = Choice(self,  size=(120, -1),
                              choices=self.det_types)
        self.dettype.SetStringSelection(det_type)

        self.prefix = wx.TextCtrl(self, -1, prefix, size=(120, -1))
        self.nelem = FloatCtrl(self, value=nmca, precision=0, minval=1,
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

class Epics_MultiMCA(object):
    """base multi-MCA detector, to be subclassed for Xspress3

    Needs the following methods / members

    mcas    list of MCA objects

    connect()
    set_dwelltime(dtime=0)
    start()
    stop()
    erase()
    add_roi(roiname, lo, hi)
    del_roi(roiname)
    clear_rois()
    save_ascii(filename)
    get_energy(mca=1)
    get_array(mca=1)
    """
    def __init__(self, prefix=None, nmca=4, **kws):
        self.nmca = nmca
        self.prefix = prefix
        self.mcas = []
        self.energies = []
        self.connected = False
        if self.prefix is not None:
            self.connect()

    @EpicsFunction
    def connect(self):
        self._xmap = MultiXMAP(self.prefix, nmca=self.nmca)
        time.sleep(0.001)
        self.mcas = self._xmap.mcas
        self.connected = True
        self._xmap.SpectraMode()
        self.rois = self._xmap.mcas[0].get_rois()

    def set_dwelltime(self, dtime=0):
        print 'dwelltime ', dtime
        if dtime <= 0:
            self._xmap.PresetMode = 0
        else:
            self._xmap.PresetMode = 1
            self._xmap.PresetReal = dtime
    
    def start(self):
        return self._xmap.start()

    def stop(self):
        return self._xmap.stop()

    def erase(self):
        self._xmap.EraseAll = 1

    def get_array(self, mca=1):
        return self._xmap.mcas[mca-1].get('VAL')

    def get_energy(self, mca=1):
        return self._xmap.mcas[mca-1].get_energy()

    def clear_rois(self):
        for mca in self._xmap.mcas:
            mca.clear_rois()
        self.rois = self._xmap.mcas[0].get_rois()

    def del_roi(self, roiname):
        for mca in self._xmap.mcas:
            mca.del_roi(roiname)
        self.rois = self._xmap.mcas[0].get_rois()

    def add_roi(self, roiname, lo=-1, hi=-1):
        calib = self._xmap.mcas[0].get_calib()
        for mca in self._xmap.mcas:
            mca.add_roi(roiname, lo=lo, hi=hi, calib=calib)
        self.rois = self._xmap.mcas[0].get_rois()

    def restore_rois(self, roifile):
        self._xmap.restore_rois(roifile)
        self.rois = self._xmap.mcas[0].get_rois()

    def save_rois(self, roifile):
        buff = self._xmap.roi_calib_info()
        with open(roifile, 'w') as fout:
            fout.write("%s\n" % "\n".join(buff))


class EpicsXRFDisplayFrame(XRFDisplayFrame):
    _about = """Epics XRF Spectra Display
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, parent=None, _larch=None, prefix=None, det_type='xmap',
                 nmca=4, size=(725, 580),  title='Epics XRF Display',
                 output_title='XRF', **kws):

        if prefix is None:
            prefix, det_type, nmca  = self.prompt_for_detector(prefix=prefix, 
                                                                det_type=det_type, 
                                                                nmca=nmca)
        self.connect_to_detector(prefix=prefix, det_type=det_type, nmca=nmca)
        self.det_fore = -1
        self.det_back = -1
        XRFDisplayFrame.__init__(self, parent=parent, _larch=_larch,
                                 title=title, size=size, **kws)

    def prompt_for_detector(self, prefix=None, det_type='xmap', nmca=4):
        dlg = DetectorSelectDialog(prefix=prefix, det_type=det_type, nmca=nmca)
        dlg.Raise()
        if dlg.ShowModal() == wx.ID_OK:
            dpref = dlg.prefix.GetValue()
            dtype = dlg.dettype.GetStringSelection()
            nmca = dlg.nelem.GetValue()
            dlg.Destroy()
        return dpref, dtype, nmca

    def connect_to_detector(self, prefix=None, det_type='xmap', nmca=4):
        if det_type.lower().startswith('xmap'):
            self.det = Epics_MultiMCA(prefix=prefix, nmca=nmca)
            print self.det
        elif det_type.lower().startswith('xsp'):
            print ' connect to xspress3 ' # self.det = Xspress3Detector()
        wx.CallAfter(self.show_mca, 1)
        
    def show_mca(self, mca=1, mca2=-1):
        energy = self.det.get_energy(mca=mca)
        counts = self.det.get_array(mca=mca)
        if mca2 is not None and mca2 > 1:
            print 'Show MCA2 too!'
        print 'show mca ', energy, counts
        self.plot(energy, counts)

    def createCustomMenus(self, fmenu):
        MenuItem(self, fmenu, "Connect Epics Detector\tCtrl+D",
                 "Connect to MCA or XSPress3 Detector",
                 self.onConnectEpics)
        fmenu.AppendSeparator()

    def createMainPanel(self):
        epicspanel = self.createEpicsPanel()
        ctrlpanel  = self.createControlPanel()
        plotpanel  = self.panel = self.createPlotPanel()
        self.panel.SetName('plotpanel')
        tx, ty = self.wids['ptable'].GetBestSize()
        cx, cy = ctrlpanel.GetBestSize()
        px, py = plotpanel.GetBestSize()

        self.SetSize((max(cx, tx)+px, 85+max(cy, py)))

        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL


        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.Add(ctrlpanel, 0, style, 1)
        bsizer.Add(plotpanel, 1, style, 1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(epicspanel, 0, style, 1)
        sizer.Add(bsizer,     1, style, 1)
        pack(self, sizer)

        self.set_roilist(mca=None)
        
    def createEpicsPanel(self):
        pane = wx.Panel(self, name='boo')
        psizer = wx.BoxSizer(wx.HORIZONTAL)

        # det button panel
        btnpanel = wx.Panel(pane, name='foo')
        # print dir(btnpanel)
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
                col = (50, 50, 250)
            elif i == self.det_back:
                col = (80, 200, 20)
            self.wids[dname].SetBackgroundColour(col)
        self.show_mca(mca=self.det_fore, mca2=self.det_back)

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
        print '... frame ', frame
        frame.Show()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    EpicsXRFApp().MainLoop()
