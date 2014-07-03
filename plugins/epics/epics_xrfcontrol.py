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
from mca import MCA
from roi import ROI
use_plugin_path('xray')
use_plugin_path('wx')
use_plugin_path('std')
from debugtime import DebugTimer

from wxutils import (SimpleText, EditableListBox, Font, FloatCtrl,
                     pack, Popup, Button, get_icon, Check, MenuItem,
                     Choice, FileOpen, FileSave, fix_filename, HLine,
                     GridPanel, CEN, LEFT, RIGHT)

from periodictable import PeriodicTablePanel
from xrfdisplay import XRFDisplayFrame

import epics
from epics.devices.mca import  MultiXMAP
from epics.wx import EpicsFunction, DelayedEpicsCallback

class Empty(): pass

class DetectorSelectDialog(wx.Dialog):
    """Connect to an Epics MCA detector 
    Can be either XIA xMAP  or Quantum XSPress3
    """
    msg = '''Select XIA xMAP or Quantum XSPress3 MultiElement MCA detector'''
    det_types = ('xmap', 'xspress3')
    def_prefix =  '13GEXMAP:'
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

        sizer.Add(self.dettype, (0, 1), (1, 1), sty, 2)
        sizer.Add(self.prefix, (1, 1), (1, 1), sty, 2)
        sizer.Add(self.nelem,  (2, 1), (1, 1), sty, 2)
       
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
        self.elapsed_real = None
        self.needs_refresh = False
        if self.prefix is not None:
            self.connect()

    @EpicsFunction
    def connect(self):
        self._xmap = MultiXMAP(self.prefix, nmca=self.nmca)
        self._xmap.PV('ElapsedReal', callback=self.onRealTime)
        self._xmap.PV('DeadTime')
        time.sleep(0.001)
        self.mcas = self._xmap.mcas
        self.connected = True
        self._xmap.SpectraMode()
        self.rois = self._xmap.mcas[0].get_rois()

    @EpicsFunction
    def connect_displays(self, status=None, elapsed=None, deadtime=None):
        pvs = self._xmap._pvs
        if elapsed is not None:
            self.elapsed_textwidget = elapsed
        for wid, attr in ((status, 'Acquiring'),(deadtime, 'DeadTime')):
            if wid is not None:
                pvs[attr].add_callback(partial(self.update_widget, wid=wid))
                
    @DelayedEpicsCallback
    def update_widget(self, pvname, char_value=None,  wid=None, **kws):
        if wid is not None:
            wid.SetLabel(char_value)

    @DelayedEpicsCallback
    def onRealTime(self, pvname, value=None, **kws):
        self.elapsed_real = value
        self.needs_refresh = True
        if self.elapsed_textwidget is not None:
            self.elapsed_textwidget.SetLabel("  %8.2f" % value)
            
            
    def set_dwelltime(self, dtime=0):
        if dtime <= 1.e-3:
            self._xmap.PresetMode = 0
        else:
            self._xmap.PresetMode = 1
            self._xmap.PresetReal = dtime
    
    def start(self):
        return self._xmap.start()

    def stop(self):
        return self._xmap.stop()

    def erase(self):
        self._xmap.put('EraseAll', 1)

    def get_array(self, mca=1):
        return 1.0*self._xmap.mcas[mca-1].get('VAL')

    def get_energy(self, mca=1):
        return self._xmap.mcas[mca-1].get_energy()

    def get_mca(self, mca=1):
        """return an MCA object """
        emca = self._xmap.mcas[mca-1]
        emca.get_rois()
        thismca = MCA(counts=1.0*emca.VAL, offset=emca.CALO, slope=emca.CALS)
        thismca.energy = emca.get_energy()
        thismca.counts += 1.0 
        thismca.rois = []
        for eroi in emca.rois:
            thismca.rois.append(ROI(name=eroi.name, address=eroi.address,
                                    left=eroi.left, right=eroi.right))
        return thismca
    
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


        self.det_type = det_type
        self.nmca = nmca
        self.det_fore = 1
        self.det_back = 0
        
        self.onConnectEpics(event=None, prefix=prefix)

        XRFDisplayFrame.__init__(self, parent=parent, _larch=_larch,
                                 title=title, size=size, **kws)


    def onConnectEpics(self, event=None, prefix=None, **kws):
        if prefix is None:
            res  = self.prompt_for_detector(prefix=prefix, 
                                            det_type=self.det_type, 
                                            nmca=self.nmca)
            self.prefix, self.det_type, self.nmca = res
        self.det_fore = 1
        self.det_back = 0
        self.clear_mcas()
        self.connect_to_detector(prefix=self.prefix,
                                 det_type=self.det_type, nmca=self.nmca)

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
        elif det_type.lower().startswith('xsp'):
            print ' connect to xspress3 ' # self.det = Xspress3Detector()
        
    def show_mca(self):
        self.needs_newplot = False
        if self.mca is None or self.needs_newplot:
            self.mca = self.det.get_mca(mca=self.det_fore)
        
        self.plotmca(self.mca, set_title=False)
        title = "Foreground: MCA{:d}".format(self.det_fore)
        if self.det_back  > 0:
            if self.mca2 is None:
                self.mca2 = self.det.get_mca(mca=self.det_back)

            e2 = self.det.get_energy(mca=self.det_back)
            c2 = self.det.get_array(mca=self.det_back)
            title = "{:s}  Background: MCA{:d}".format(title, self.det_back)
            try:
                self.oplot(e2, c2)
            except ValueError:
                pass
        self.SetTitle(title)
        self.needs_newplot = False


    def onSaveROIs(self, event=None, **kws):
        wildcard = ' ROI files (*.roi)|*.roi|All files (*.*)|*.*'        
        dlg = wx.FileDialog(self, message="Save ROI File",
                            defaultDir=os.getcwd(),
                            wildcard=wildcard,
                            style = wx.SAVE|wx.CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            roifile = dlg.GetPath()
        
        self.det.save_rois(roifile)
    
    def onRestoreROIs(self, event=None, **kws):
        wildcard = ' ROI files (*.roi)|*.roi|All files (*.*)|*.*'        
        dlg = wx.FileDialog(self, message="Read ROI File",
                            defaultDir=os.getcwd(),
                            wildcard=wildcard,
                            style = wx.OPEN|wx.CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            roifile = dlg.GetPath()        
            self.det.restore_rois(roifile)
            self.set_roilist(mca=self.mca)

    def createCustomMenus(self):
        menu = wx.Menu()
        MenuItem(self, menu, "Connect to Detector\tCtrl+D",
                 "Connect to MCA or XSPress3 Detector",
                 self.onConnectEpics)
        menu.AppendSeparator()
        self._menus.insert(1, (menu, 'Detector'))

    def createMainPanel(self):
        epicspanel = self.createEpicsPanel()
        ctrlpanel  = self.createControlPanel()
        plotpanel  = self.panel = self.createPlotPanel()
        self.panel.SetName('plotpanel')
        tx, ty = self.wids['ptable'].GetBestSize()
        cx, cy = ctrlpanel.GetBestSize()
        px, py = plotpanel.GetBestSize()

        self.SetSize((950, 625))
        self.SetMinSize((450, 350))

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
        pane = wx.Panel(self, name='epics panel')
        psizer = wx.BoxSizer(wx.HORIZONTAL)

        # det button panel
        btnpanel = wx.Panel(pane, name='foo')

        btnsizer = wx.GridBagSizer(2, 2)
        style  = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        tstyle = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        rstyle = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
        bkg_choices = ['None']
        
        psizer.Add(SimpleText(pane, ' MCAs: '),  0, tstyle, 1)
        for i in range(1, self.nmca+1):
            bkg_choices.append("%i" % i)
            b =  Button(btnpanel, '%i' % i, size=(25, 25),
                        action=partial(self.onSelectDet, index=i))
            self.wids['det%i' % i] = b
            btnsizer.Add(b, (0, i), (1, 1), style, 1)
        pack(btnpanel, btnsizer)

        psizer.Add(btnpanel, 0, style, 1)
        
        self.wids['det_status'] = SimpleText(pane, ' ', size=(60, -1))
        self.wids['elapsed']    = SimpleText(pane, ' ', size=(70, -1),
                                             style=rstyle)
        self.wids['deadtime']   = SimpleText(pane, ' ', size=(70, -1),
                                             style=rstyle)
        
        self.wids['bkg_det'] = Choice(pane, size=(60, -1),
                                      choices=bkg_choices,
                                      action=self.onSelectDet)

        self.wids['dwelltime'] = FloatCtrl(pane, value=0.0, precision=1, minval=0,
                                       size=(55, -1),act_on_losefocus=True,
                                       action=self.onSetDwelltime)

        b0 =  Button(pane, 'Continuous', size=(75, 25), action=partial(self.onStart, dtime=0))        
        b1 =  Button(pane, 'Start',      size=(75, 25), action=self.onStart)
        b2 =  Button(pane, 'Stop',       size=(75, 25), action=self.onStop)
        b3 =  Button(pane, 'Erase',      size=(75, 25), action=self.onErase)

        psizer.Add(SimpleText(pane, '  Background:  '), 0, tstyle, 1)
        psizer.Add(self.wids['bkg_det'],            0, style, 1)

        psizer.Add(SimpleText(pane, '  Time (s): '), 0, tstyle, 1)
        psizer.Add(self.wids['dwelltime'],             0, tstyle, 2)
        psizer.Add(self.wids['elapsed'],           0, tstyle, 2)
        
        # psizer.Add(SimpleText(pane, ' Status:'),  0, tstyle, 1)
        psizer.Add(self.wids['det_status'],         0, tstyle, 2)

        psizer.Add(b0, 0, style, 1)
        psizer.Add(b1, 0, style, 1)
        psizer.Add(b2, 0, style, 1)
        psizer.Add(b3, 0, style, 1)
        
        psizer.Add(SimpleText(pane, '   % Deadtime: '), 0, tstyle, 2)        
        psizer.Add(self.wids['deadtime'],               0, tstyle, 2)

        pack(pane, psizer)
        # pane.SetMinSize((500, 53))
        

        self.det.connect_displays(status=self.wids['det_status'],
                                  elapsed=self.wids['elapsed'],
                                  deadtime=self.wids['deadtime'])

        wx.CallAfter(self.onSelectDet, index=1)

        self.mca_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer, self.mca_timer)
        self.mca_timer.Start(100)
        return pane

    def onTimer(self, event=None):
        if self.mca is None or self.needs_newplot:
            self.show_mca()
        # self.elapsed_real = self.det.elapsed_real
        self.mca.real_time = self.det.elapsed_real

        if self.det.needs_refresh:
            if self.det_back > 0:
                if self.mca2 is None:
                    self.mca2 = self.det.get_mca(mca=self.det_back)

                energy = self.det.get_energy(mca=self.det_back)
                counts = self.det.get_array(mca=self.det_back)
                try:
                    self.update_mca(counts, energy=energy, is_mca2=True, draw=False)
                except ValueError:
                    pass

            if self.mca is None:
                self.mca = self.det.get_mca(mca=self.det_fore)

            energy = self.det.get_energy(mca=self.det_fore)
            counts = self.det.get_array(mca=self.det_fore)*1.0
            
            self.update_mca(counts, energy=energy)

            self.det.needs_refresh = False
        
    def onSelectBkgDet(self, event=None, **kws):
        self.mca2 = None
        self.det_back = self.wids['bkg_det'].GetSelection()
        self.onSelectDet(index=self.det_fore)
        
    def onSelectDet(self, event=None, index=0, **kws):
        if index > 0: 
            self.det_fore = index

        self.det_back = self.wids['bkg_det'].GetSelection()
        if self.det_fore  == self.det_back:
            self.det_back = 0

        for i in range(1, self.nmca+1):
            dname = 'det%i' % i
            bcol = (220, 220, 220)
            fcol = (0, 0, 0)
            if i == self.det_fore:
                bcol = (60, 50, 245)
                fcol = (240, 230, 100)
            if i == self.det_back:
                bcol = (80, 200, 20)
            self.wids[dname].SetBackgroundColour(bcol)
            self.wids[dname].SetForegroundColour(fcol)
        self.clear_mcas()
        self.show_mca()
        self.Refresh()

    def swap_mcas(self, event=None):
        if self.mca2 is None:
            return
        self.mca, self.mca2 = self.mca2, self.mca
        fore, back = self.det_fore, self.det_back
        self.wids['bkg_det'].SetSelection(fore)
        self.onSelectDet(index=back)


    def clear_background(self, evt=None):
        "remove XRF background"
        self.mca2 = None
        self.det_back = 0
        self.wids['bkg_det'].SetSelection(0)
        self.onSelectDet()

    def onSetDwelltime(self, event=None, **kws):
        if 'dwelltime' in self.wids:
            self.det.set_dwelltime(dtime=self.wids['dwelltime'].GetValue())

    def clear_mcas(self):
        self.mca = self.mca2 = None
        self.needs_newplot = True
        
    def onStart(self, event=None, dtime=None, **kws):
        if dtime is not None:
            self.wids['dwelltime'].SetValue("%.1f" % dtime)            
            self.det.set_dwelltime(dtime=dtime)
        else:
            self.det.set_dwelltime(dtime=self.wids['dwelltime'].GetValue())
        self.det.start()

    def onStop(self, event=None, **kws):
        self.det.stop()
        
    def onErase(self, event=None, **kws):
        self.needs_newplot = True
        self.det.erase()

    def onDelROI(self, event=None):
        roiname = self.wids['roiname'].GetValue()        
        XRFDisplayFrame.onDelROI(self)
        self.det.del_roi(roiname)

    def onNewROI(self, event=None):
        nam = self.wids['roiname'].GetValue()
        confirmed = XRFDisplayFrame.onNewROI(self)
        if confirmed:
            self.det.add_roi(nam, lo=self.xmarker_left, hi=self.xmarker_right)
        
        
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
