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

from wxutils import (SimpleText, EditableListBox, Font, FloatCtrl,
                     pack, Popup, Button, get_icon, Check, MenuItem,
                     Choice, FileOpen, FileSave, fix_filename, HLine,
                     GridPanel, CEN, LEFT, RIGHT)

from larch import use_plugin_path

# use_plugin_path('xray')
use_plugin_path('wx')
from periodictable import PeriodicTablePanel
from xrfdisplay import XRFDisplayFrame

from xrfdisplay_utils import CalibrationFrame

use_plugin_path('std')
from debugtime import DebugTimer

use_plugin_path('epics')
from xrf_detectors import Epics_MultiXMAP, Epics_Xspress3

class DetectorSelectDialog(wx.Dialog):
    """Connect to an Epics MCA detector
    Can be either XIA xMAP  or Quantum XSPress3
    """
    msg = '''Select XIA xMAP or Quantum XSPress3 MultiElement MCA detector'''
    amp_types = ('xspress3', 'xmap')
    det_types = ('ME-4', 'other')
    def_prefix = '13QX4:'   # SDD1:'
    def_nelem  =  4

    def __init__(self, parent=None, prefix=None, det_type='ME-4',
                 amp_type='xmap', nmca=4,
                 title='Select Epics MCA Detector'):
        if prefix is None: prefix = self.def_prefix
        if amp_type not in self.amp_types:
            amp_type = self.amp_types[0]
        if det_type not in self.det_types:
            det_type = self.det_types[0]
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        self.SetBackgroundColour((240, 240, 230))
        if parent is not None:
            self.SetFont(parent.GetFont())

        self.amptype = Choice(self, size=(120, -1),choices=self.amp_types)
        self.amptype.SetStringSelection(amp_type)

        self.dettype = Choice(self,size=(120, -1), choices=self.det_types)
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

        hline = wx.StaticLine(self, size=(225, 3), style=wx.LI_HORIZONTAL)
        sty = LEFT|wx.ALIGN_CENTER_VERTICAL
        sizer = wx.GridBagSizer(5, 2)
        def txt(label):
            return SimpleText(self, label, size=(120, -1), style=LEFT)

        sizer.Add(txt('Detector Type'), (0, 0), (1, 1), sty, 2)
        sizer.Add(txt('Electronics'),   (1, 0), (1, 1), sty, 2)
        sizer.Add(txt('Epics Prefix'),  (2, 0), (1, 1), sty, 2)
        sizer.Add(txt('# Elements'),    (3, 0), (1, 1), sty, 2)
        sizer.Add(self.dettype,         (0, 1), (1, 1), sty, 2)
        sizer.Add(self.amptype,         (1, 1), (1, 1), sty, 2)
        sizer.Add(self.prefix,          (2, 1), (1, 1), sty, 2)
        sizer.Add(self.nelem,           (3, 1), (1, 1), sty, 2)

        sizer.Add(hline,                (4, 0), (1, 2), sty, 2)
        sizer.Add(btnsizer,             (5, 0), (1, 2), sty, 2)
        self.SetSizer(sizer)
        sizer.Fit(self)


class EpicsXRFDisplayFrame(XRFDisplayFrame):
    _about = """Epics XRF Spectra Display
  Matt Newville <newville @ cars.uchicago.edu>
  """
    me4_layout = ((0, 0), (1, 0), (1, 1), (0, 1))

    def __init__(self, parent=None, _larch=None, prefix='13QX4:',
                 det_type='ME-4',  amp_type='xspress3',
                 nmca=4, size=(725, 580),  title='Epics XRF Display',
                 output_title='XRF', **kws):

        self.det_type = det_type
        self.amp_type = amp_type
        self.nmca = nmca
        self.det_fore = 1
        self.det_back = 0

        self.onConnectEpics(event=None, prefix=prefix)

        XRFDisplayFrame.__init__(self, parent=parent, _larch=_larch,
                                 title=title, size=size, **kws)

    def onConnectEpics(self, event=None, prefix=None, **kws):
        if prefix is None:
            res  = self.prompt_for_detector(prefix=prefix,
                                            amp_type=self.amp_type,
                                            nmca=self.nmca)
            self.prefix, self.det_type, self.amp_type, self.nmca = res
        else:
            self.prefix = prefix
        self.det_fore = 1
        self.det_back = 0
        self.clear_mcas()
        self.connect_to_detector(prefix=self.prefix, amp_type=self.amp_type,
                                 det_type=self.det_type, nmca=self.nmca)


    def onSaveMCAFile(self, event=None, **kws):
        tmp = '''
        print 'SaveMCA File'
        deffile = ''
        if hasattr(self.mca, 'sourcefile'):
            deffile = "%s%s" % (deffile, getattr(self.mca, 'sourcefile'))
        if hasattr(self.mca, 'areaname'):
            deffile = "%s%s" % (deffile, getattr(self.mca, 'areaname'))
        if deffile == '':
            deffile ='test'
        if not deffile.endswith('.mca'):
            deffile = deffile + '.mca'
        '''

        deffile = 'save.mca' # fix_filename(str(deffile))
        outfile = FileSave(self, "Save MCA File",
                           default_file=deffile,
                           wildcard=FILE_WILDCARDS)

        if outfile is not None:
            print 'Would write ', outfile,  self.det
            self.mca.save_mcafile(outfile)

    def onSaveColumnFile(self, event=None, **kws):
        print( '  EPICS-XRFDisplay onSaveColumnFile not yet implemented  ')
        pass

    def prompt_for_detector(self, prefix=None, amp_type='xspress3', nmca=4):
        dlg = DetectorSelectDialog(prefix=prefix, amp_type=amp_type, nmca=nmca)
        dlg.Raise()
        if dlg.ShowModal() == wx.ID_OK:
            dpref = dlg.prefix.GetValue()
            atype = dlg.amptype.GetStringSelection()
            dtype = dlg.dettype.GetStringSelection()
            nmca = dlg.nelem.GetValue()
            dlg.Destroy()
        return dpref, dtype, atype, nmca

    def connect_to_detector(self, prefix=None, amp_type='xmap',
                            det_type=None, nmca=4):
        self.det = None
        if amp_type.lower().startswith('xmap'):
            self.det = Epics_MultiXMAP(prefix=prefix, nmca=nmca)
        elif amp_type.lower().startswith('xsp'):
            self.det = Epics_Xspress3(prefix=prefix, nmca=nmca)
            self.det.connect()
            time.sleep(0.5)
            self.det.get_mca(mca=1)
            self.needs_newplot=True

    def show_mca(self, init=False):
        self.needs_newplot = False
        if self.mca is None or self.needs_newplot:
            self.mca = self.det.get_mca(mca=self.det_fore)

        self.plotmca(self.mca, set_title=False, init=init)
        title = "Foreground: MCA{:d}".format(self.det_fore)
        if self.det_back  > 0:
            if self.mca2 is None:
                self.mca2 = self.det.get_mca(mca=self.det_back)

            c2 = self.det.get_array(mca=self.det_back)
            e2 = self.det.get_energy(mca=self.det_back)
            title = "{:s}  Background: MCA{:d}".format(title, self.det_back)
            try:
                self.oplot(e2, c2)
            except ValueError:
                pass

        roiname = self.wids['roiname'].GetValue()

        if roiname in self.wids['roilist'].GetStrings():
            i = self.wids['roilist'].GetStrings().index(roiname)
            self.wids['roilist'].EnsureVisible(i)
            self.onROI(label=roiname)

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
            self.show_mca()
            self.onSelectDet(event=None, index=0)

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
        hline = wx.StaticLine(self, size=(425, 2), style=wx.LI_HORIZONTAL|style)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(epicspanel, 0, style, 1)
        sizer.Add(hline,      0, style, 1)
        sizer.Add(bsizer,     1, style, 1)
        pack(self, sizer)

        self.set_roilist(mca=None)

    def createEpicsPanel(self):
        pane = wx.Panel(self, name='epics panel')
        psizer = wx.GridBagSizer(4, 12) # wx.BoxSizer(wx.HORIZONTAL)

        btnpanel = wx.Panel(pane, name='foo')

        nmca = self.nmca

        if self.det_type.lower().startswith('me-4') and nmca<5:
            btnsizer = wx.GridBagSizer(2, 2)
        else:
            btnsizer = wx.GridBagSizer(int((nmca+3.0)/4.0), 4)

        style  = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        rstyle = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
        bkg_choices = ['None']

        psizer.Add(SimpleText(pane, ' MCAs: '),  (0, 0), (1, 1), style, 1)
        for i in range(1, 1+nmca):
            bkg_choices.append("%i" % i)
            b =  Button(btnpanel, '%i' % i, size=(30, 25),
                        action=partial(self.onSelectDet, index=i))
            self.wids['det%i' % i] = b
            loc = divmod(i-1, 4)
            if self.det_type.lower().startswith('me-4') and nmca<5:
                loc = self.me4_layout[i-1]
            btnsizer.Add(b,  loc, (1, 1), style, 1)
        pack(btnpanel, btnsizer)
        nrows = 1 + loc[0]

        if self.det_type.lower().startswith('me-4') and nmca<5:
            nrows = 2

        psizer.Add(btnpanel, (0, 1), (nrows, 1), style, 1)

        self.wids['det_status'] = SimpleText(pane, ' ', size=(120, -1), style=style)
        self.wids['deadtime']   = SimpleText(pane, ' ', size=(120, -1), style=style)

        self.wids['bkg_det'] = Choice(pane, size=(75, -1), choices=bkg_choices,
                                      action=self.onSelectDet)

        self.wids['dwelltime'] = FloatCtrl(pane, value=0.0, precision=1, minval=0,
                                           size=(80, -1), act_on_losefocus=True,
                                           action=self.onSetDwelltime)
        self.wids['elapsed']   = SimpleText(pane, ' ', size=(80, -1),  style=rstyle)

        b0 =  Button(pane, 'Continuous', size=(90, 25), action=partial(self.onStart, 
                                                                       dtime=0))  
        b1 =  Button(pane, 'Start',      size=(90, 25), action=self.onStart)
        b2 =  Button(pane, 'Stop',       size=(90, 25), action=self.onStop)
        b3 =  Button(pane, 'Erase',      size=(90, 25), action=self.onErase)

        psizer.Add(SimpleText(pane, 'Background MCA: '), (0, 2), (1, 1), style, 1)
        psizer.Add(self.wids['bkg_det'],                 (1, 2), (1, 1), style, 1)

        psizer.Add(SimpleText(pane, 'Preset Time (s):'),  (0, 3), (1, 1),  style, 1)
        psizer.Add(SimpleText(pane, 'Elapsed Time (s):'), (1, 3), (1, 1),  style, 1)
        psizer.Add(self.wids['dwelltime'],                (0, 4), (1, 1),  style, 1)
        psizer.Add(self.wids['elapsed'],                  (1, 4), (1, 1),  style, 1)

        psizer.Add(b0, (0, 5), (1, 1), style, 1)
        psizer.Add(b1, (0, 6), (1, 1), style, 1)
        psizer.Add(b2, (1, 5), (1, 1), style, 1)
        psizer.Add(b3, (1, 6), (1, 1), style, 1)

        psizer.Add(SimpleText(pane, 'Status:'),      (0, 7), (1, 1), style, 1)
        psizer.Add(self.wids['det_status'],          (0, 8), (1, 1), style, 1)
        psizer.Add(SimpleText(pane, '% Deadtime: '), (1, 7), (1, 1), style, 1)
        psizer.Add(self.wids['deadtime'],            (1, 8), (1, 1), style, 1)

        pack(pane, psizer)
        # pane.SetMinSize((500, 53))
        self.det.connect_displays(status=self.wids['det_status'],
                                  elapsed=self.wids['elapsed'],
                                  deadtime=self.wids['deadtime'])

        wx.CallAfter(self.onSelectDet, index=1, init=True)
        self.timer_counter = 0
        self.mca_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.UpdateData, self.mca_timer)
        self.mca_timer.Start(100)
        return pane

    # def update_mca(self, counts, **kws):
    #    self.det.needs_refresh = False
                   
    def UpdateData(self, event=None, force=False):
        self.timer_counter += 1
        if self.mca is None or self.needs_newplot:
            self.show_mca()
        # self.elapsed_real = self.det.elapsed_real
        self.mca.real_time = self.det.elapsed_real

        if force or self.det.needs_refresh:
            self.det.needs_refresh = False
            if self.det_back > 0:
                if self.mca2 is None:
                    self.mca2 = self.det.get_mca(mca=self.det_back)

                counts = self.det.get_array(mca=self.det_back)
                energy = self.det.get_energy(mca=self.det_back)
                try:
                    self.update_mca(counts, energy=energy, is_mca2=True, draw=False)
                except ValueError:
                    pass

            if self.mca is None:
                self.mca = self.det.get_mca(mca=self.det_fore)

            counts = self.det.get_array(mca=self.det_fore)*1.0
            energy = self.det.get_energy(mca=self.det_fore)
            if max(counts) < 1.0:
                counts    = 1e-4*np.ones(len(counts))
                counts[0] = 2.0
            self.update_mca(counts, energy=energy)

    def onSelectBkgDet(self, event=None, **kws):
        self.mca2 = None
        self.det_back = self.wids['bkg_det'].GetSelection()
        if self.det_back == self.det_fore:
            self.det_back = 0
        if self.det_back != 0:
            title = "Foreground: MCA{:d}".format(self.det_fore)
            if self.mca2 is None:
                self.mca2 = self.det.get_mca(mca=self.det_back, with_rois=False)
                c = self.mca2.counts
                e = self.mca2.energy
            else:
                c = self.det.get_array(mca=self.det_back)
                e = self.det.get_energy(mca=self.det_back)
            title = "{:s}  Background: MCA{:d}".format(title, self.det_back)
            try:
                self.oplot(e, c)
                self.SetTitle(title)
            except ValueError:
                pass
        self.needs_newplot = False

    def onSelectDet(self, event=None, index=0, init=False, **kws):
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
        self.show_mca(init=init)
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
        self.det.needs_refresh = True
        time.sleep(0.125)
        self.UpdateData(event=None, force=True)

    def onErase(self, event=None, **kws):
        self.needs_newplot = True
        self.det.erase()

    def onDelROI(self, event=None):
        roiname = self.wids['roiname'].GetValue()
        errmsg = None
        if self.roilist_sel is None:
            errmsg = 'No ROI selected to delete.'
        if errmsg is not None:
            return Popup(self, errmsg, 'Cannot Delete ROI')

        self.det.del_roi(roiname)
        XRFDisplayFrame.onDelROI(self)

    def onNewROI(self, event=None):
        roiname = self.wids['roiname'].GetValue()
        errmsg = None
        if self.xmarker_left is None or self.xmarker_right is None:
            errmsg = 'Must select right and left markers to define ROI'
        elif roiname in self.wids['roilist'].GetStrings():
            errmsg = '%s is already in ROI list - use a unique name.' % roiname
        if errmsg is not None:
            return Popup(self, errmsg, 'Cannot Define ROI')

        confirmed = XRFDisplayFrame.onNewROI(self)
        if confirmed:
            print 'NEW ROI ' , self.det, roiname, self.xmarker_left, self.xmarker_right
            self.det.add_roi(roiname, lo=self.xmarker_left, 
                             hi=self.xmarker_right)

    def onRenameROI(self, event=None):
        roiname = self.wids['roiname'].GetValue()
        errmsg = None
        if roiname in self.wids['roilist'].GetStrings():
            errmsg = '%s is already in ROI list - use a unique name.' % roiname
        elif self.roilist_sel is None:
            errmsg = 'No ROI selected to rename.'
        if errmsg is not None:
            return Popup(self, errmsg, 'Cannot Rename ROI')

        if self.roilist_sel < len(self.det.mcas[0].rois):
            self.det.rename_roi(self.roilist_sel, roiname)
            names = self.wids['roilist'].GetStrings()
            names[self.roilist_sel] = roiname
            self.wids['roilist'].Clear()
            for sname in names:
                self.wids['roilist'].Append(sname)
            self.wids['roilist'].SetSelection(self.roilist_sel)

    def onCalibrateEnergy(self, event=None, **kws):
        try:
            self.win_calib.Raise()
        except:
            self.win_calib = CalibrationFrame(self, mca=self.mca,
                                              larch=self.larch,
                                              callback=self.onSetCalib)

    def onSetCalib(self, offset, slope, mca=None):
        print 'XRFControl Set Energy Calibratione' , offset, slope, mca

    def onClose(self, event=None):
        self.onStop()
        XRFDisplayFrame.onClose(self)        

    def onExit(self, event=None):
        self.onStop()
        XRFDisplayFrame.onExit(self)        

class EpicsXRFApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, **kws):
        self.kws = kws
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        frame = EpicsXRFDisplayFrame(**self.kws) #
        frame.Show()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    # e = EpicsXRFApp(prefix='QX4:', det_type='ME-4',
    #                amp_type='xspress3', nmca=4)
   
    EpicsXRFApp().MainLoop()
