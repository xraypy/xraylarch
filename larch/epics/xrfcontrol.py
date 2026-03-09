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
import wx.lib.agw.flatnotebook as flat_nb
import wx.dataview as dv

import numpy as np
import matplotlib

from pyshortcuts import fix_filename
from wxmplot import PlotPanel
from wxutils import (SimpleText, EditableListBox, Font, FloatCtrl,
                     pack, Popup, Button, get_icon, Check, MenuItem,
                     Choice, FileOpen, FileSave, HLine, flatnotebook,
                     GridPanel, CEN, LEFT, RIGHT)

import larch
from larch.site_config import icondir
from larch.wxlib import PeriodicTablePanel, LarchWxApp, get_color
from larch.wxlib.xrfdisplay import (XRFDisplayFrame, XRFCalibrationFrame,
                                    FILE_WILDCARDS)
from larch.utils import get_cwd


ROI_WILDCARD = 'Data files (*.dat)|*.dat|ROI files (*.roi)|*.roi|All files (*.*)|*.*'
try:
    from epics import caget, caput, get_pv
    from epics.wx import EpicsFunction
    from .xrf_detectors import Epics_MultiXMAP, Epics_Xspress3, Epics_KetekMCA
except:
    caget = get_pv = Epics_MultiXMAP = Epics_Xspress3 = Epics_KetekMCA = None

if caget is not None:  # is pyepics imported?
    from epics.wx import (PVText, PVTextCtrl, PVFloatCtrl,
                          PVEnumButtons, PVEnumChoice)

def warning_color(val, warn, error):
    tcolor = wx.Colour(get_color('texP'))
    if val > warn:
        tcolor = wx.Colour(140, 60, 10, 255)
    if val > error:
        tcolor = wx.Colour(get_color('text_invalid'))
    return tcolor

class DetectorSelectDialog(wx.Dialog):
    """Connect to an Epics MCA detector
    Can be either XIA xMAP  or Quantum XSPress3
    """
    msg = '''Select XIA xMAP or Quantum XSPress3 MultiElement MCA detector'''
    det_types = ('SXD-7', 'ME-7', 'ME-4', 'Ketek', 'MCA', 'other')
    ioc_types = ('Xspress3.1', 'xMAP', 'Xspress3.0', 'MCA')
    def_prefix = '13QX7:'   # SDD1:'
    def_nelem  =  4

    def __init__(self, parent=None, prefix=None, det_type='ME-4',
                 ioc_type='Xspress3', nmca=4,
                 title='Select Epics MCA Detector'):
        if prefix is None:
            prefix = self.def_prefix
        if det_type not in self.det_types:
            det_type = self.det_types[0]

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        self.SetBackgroundColour(get_color('info_bg'))
        self.SetFont(Font(9))
        if parent is not None:
            self.SetFont(parent.GetFont())

        self.ioctype = Choice(self,size=(120, -1), choices=self.ioc_types)
        self.ioctype.SetStringSelection(ioc_type)

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
        sty = LEFT
        sizer = wx.GridBagSizer(5, 2)
        def txt(label):
            return SimpleText(self, label, size=(120, -1), style=LEFT)

        sizer.Add(txt('  Detector Type'),  (0, 0), (1, 1), sty, 2)
        sizer.Add(txt('  Uses Xspress3?'), (1, 0), (1, 1), sty, 2)
        sizer.Add(txt('  Epics Prefix'),  (2, 0), (1, 1), sty, 2)
        sizer.Add(txt('  # Elements'),    (3, 0), (1, 1), sty, 2)
        sizer.Add(self.dettype,         (0, 1), (1, 1), sty, 2)
        sizer.Add(self.ioctype,         (1, 1), (1, 1), sty, 2)
        sizer.Add(self.prefix,          (2, 1), (1, 1), sty, 2)
        sizer.Add(self.nelem,           (3, 1), (1, 1), sty, 2)

        sizer.Add(hline,                (4, 0), (1, 2), sty, 2)
        sizer.Add(btnsizer,             (5, 0), (1, 2), sty, 2)
        self.SetSizer(sizer)
        sizer.Fit(self)

class Xspress3ControlFrame(wx.Frame):
    def __init__(self, parent=None, prefix='No IOC', nmca=4, size=(750, 550)):

        title=f" Xspress3 Epics Control: '{prefix}', {nmca} elements"
        self.parent = parent
        self.prefix = prefix
        self.nmca = nmca

        wx.Frame.__init__(self, parent=parent, size=size, title=title)

        pan = self.panel = GridPanel(self)

        pan.Add(SimpleText(pan, title, size=(450, -1),style=LEFT), dcol=4, style=LEFT)

        bpan = wx.Panel(pan)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        for label, action in (('Start', self.onStart),
                              ('Stop', self.parent.onStop),
                              ('Erase', self.parent.onErase),
                              ('Continuous', partial(self.onStart,
                                                     dtime=0.25, nframes=16000))):
            bsizer.Add(Button(bpan, label, size=(100, -1), action=action))
        pack(bpan, bsizer)

        pan.Add(bpan, newrow=True, dcol=4, style=LEFT)

        for label, name, newrow in ((' Connection Status: ', 'det1:CONNECTED', True),
                                    (' Status Message: ',  'det1:StatusMessage_RBV', True),
                                   (' Detector State: ', 'det1:DetectorState_RBV', False)):
            ctrl = PVText(pan, f'{prefix}{name}', size=(125, -1))
            pan.Add(SimpleText(pan, label, style=LEFT), dcol=1,  style=LEFT, newrow=newrow)
            pan.Add(ctrl, dcol=1, style=LEFT)

        for label, ctrl, rbv, label2, spv in ((' # Frames: ', 'det1:NumImages', 'det1:NumImages',
                                               ' Array Counter: ',  'det1:ArrayCounter_RBV'),
                                              (' Dwell Time:',  'det1:AcquireTime', 'det1:AcquireTime_RBV',
                                               ' Frame Rate (Hz): ', 'det1:ArrayRate_RBV')):
            wctrl = PVFloatCtrl(pan, f'{prefix}{ctrl}', size=(100, -1))
            wrbv  = PVText(pan, f'{prefix}{rbv}', size=(100, -1))
            wspv  = PVText(pan, f'{prefix}{spv}', size=(100, -1))
            pan.Add(SimpleText(pan, label, style=LEFT), dcol=1,  style=LEFT, newrow=True)
            pan.Add(wctrl, dcol=1, style=LEFT)
            pan.Add(wrbv,  dcol=1, style=LEFT)
            pan.Add(SimpleText(pan, label2, style=LEFT), dcol=1,  style=LEFT)
            pan.Add(wspv,  dcol=1, style=LEFT)

        for label, ctrl, rbv in ((' Trigger Mode: ', 'det1:TriggerMode', 'det1:TriggerMode_RBV'),
                                        ):
            wctrl = PVEnumChoice(pan, f'{prefix}{ctrl}', size=(175, -1))
            wrbv  = PVText(pan, f'{prefix}{rbv}', size=(100, -1))
            pan.Add(SimpleText(pan, label, style=LEFT), dcol=1,  style=LEFT, newrow=True)
            pan.Add(wctrl, dcol=2, style=LEFT)
            pan.Add(wrbv,  dcol=1, style=LEFT)

        for label, ctrl in ((' Erase on Start? ', 'det1:EraseOnStart'),):
            pvname = f'{prefix}{ctrl}'
            wctrl = PVEnumButtons(pan, get_pv(pvname), size=(175, -1))
            pan.Add(SimpleText(pan, label, style=LEFT), dcol=1,  style=LEFT, newrow=True)
            pan.Add(wctrl, dcol=2, style=LEFT)

        pan.Add((25, 25),  newrow=True)

        self.nb = flatnotebook(pan, {'HDF5 FileSaver': self.hdf5_panel,
                                     'SCA Values': self.sca_panel},
                               size=(750, 550))

        self.nb.SetFont(self.GetFont())
        pan.Add(self.nb, dcol=7, newrow=True)
        self.panel.pack()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.panel, 1, wx.LEFT|wx.CENTER|wx.GROW)
        pack(self, sizer)
        self.Show()
        self.Raise()

    def hdf5_panel(self, parent):
        "HDF5 File Saver panel"
        pan = GridPanel(self)
        prefix = self.prefix

        bpan = wx.Panel(pan)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        for label, action in (('Start Capture ', self.onStartCapture),
                              ('Stop Capture ', self.onStopCapture)):
            bsizer.Add(Button(bpan, label, size=(150, -1), action=action))
        pack(bpan, bsizer)
        pan.Add(bpan, newrow=True, dcol=3, style=LEFT)
        pan.Add(PVText(pan, f'{prefix}HDF1:Capture_RBV', size=(125, -1)), dcol=2, style=LEFT)

        for label, name, wid, newrow, form in (('File Path: ',   'HDF1:FilePath', 475, True, 'textctrl'),
                                               ('File Name: ', 'HDF1:FileName', 475, True, 'textctrl'),
                                               ('Template: ', 'HDF1:FileTemplate', 175, True, 'textctrl'),
                                               ('Number: ',  'HDF1:FileNumber', 100, False, 'textctrl'),
                                               ('Compression: ',  'HDF1:Compression', 175, True, 'choice'),
                                               ('Zlib Level: ',  'HDF1:ZLevel', 100, False, 'textctrl'),
                                               ('Last File: ',  'HDF1:FullFileName_RBV', 800, True, 'statictext'),
                                               ):

            if form == 'choice':
                ctrl = PVEnumChoice(pan, f'{prefix}{name}', size=(wid, -1))
            elif form == 'statictext':
                ctrl = PVText(pan, f'{prefix}{name}', size=(wid, -1))
            else:
                ctrl = PVTextCtrl(pan, f'{prefix}{name}', size=(wid, -1))
            pan.Add(SimpleText(pan, f' {label}', size=(125, -1), style=LEFT), dcol=1,  style=LEFT, newrow=newrow)
            dcol = 1
            if wid > 350:
                dcol = 4
            elif wid > 200:
                dcol = 2
            pan.Add(ctrl, dcol=dcol, style=LEFT)
        pan.pack()
        return pan

    def sca_panel(self, parent):
        "SCA panel"
        pan = GridPanel(self)
        prefix = self.prefix
        nmca = self.nmca
        cols = {'Clock Ticks': 'SCA:0:Value_RBV',
                'Reset Ticks': 'SCA:1:Value_RBV',
                'All Events':  'SCA:3:Value_RBV',
                'DT Factor':   'SCA:9:Value_RBV',
                '%Deadtime':  'SCA:10:Value_RBV'}

        pan.Add(SimpleText(pan, ' Channel', size=(100, -1), style=LEFT), dcol=1, style=LEFT)
        for cname in cols:
            pan.Add(SimpleText(pan, cname, size=(130, -1), style=LEFT), dcol=1, style=LEFT)

        pan.Add(HLine(pan, size=(750, -1)), dcol=6, newrow=True)

        for i in range(1, self.nmca+1):
            pan.Add(SimpleText(pan, f' MCA {i}', size=(100, -1), style=LEFT), dcol=1, style=LEFT, newrow=True)
            for label, pvname in cols.items():
                pan.Add(PVText(pan, f'{prefix}C{i}{pvname}', size=(130, -1), style=LEFT),  dcol=1, style=LEFT)

        pan.pack()
        return pan


    def onStart(self, event=None, dtime=None, nframes=None, **kws):
        if dtime is not None:
            self.parent.det.set_dwelltime(dtime=dtime, nframes=nframes)
        self.parent.det.start()

    @EpicsFunction
    def onStartCapture(self, event=None):
        caput(f'{self.prefix}HDF1:Capture', 1)

    @EpicsFunction
    def onStopCapture(self, event=None):
        caput(f'{self.prefix}HDF1:Capture', 0)




class EpicsXRFDisplayFrame(XRFDisplayFrame):
    _about = """Epics XRF Spectra Display
  Matt Newville <newville @ cars.uchicago.edu>
  """
    me4_layout = ((0, 0), (1, 0), (1, 1), (0, 1))
    main_title = 'Epics XRF Control'

    def __init__(self, parent=None, _larch=None, prefix=None,
                 det_type='ME-4', ioc_type='Xspress3', nmca=4,
                 size=(1100, 850), environ_file=None,
                 incident_energy_pvname=None, incident_energy_units='eV',
                 title='Epics XRF Display', output_title='XRF', **kws):

        self.det_type = det_type
        self.ioc_type = ioc_type
        self.prefix = prefix
        self.nmca = nmca
        self.det_main = 1
        self.det = None
        self.win_xps3 = None
        self.incident_energy_kev = None
        self.incident_energy_pvname = incident_energy_pvname
        self.incident_energy_units = incident_energy_units
        self.environ = []
        if environ_file is not None:
            self.read_environfile(environ_file)

        self.icon_file = os.path.join(icondir, 'ptable.ico')

        XRFDisplayFrame.__init__(self, parent=parent, _larch=_larch,
                                 title=title, size=size, **kws)

        self.onConnectEpics(event=None, prefix=prefix)

    def read_environfile(self, filename):
        """read environmnet file"""
        if os.path.exists(filename):
            textlines = []
            try:
                with open(filename, 'r') as fh:
                    textlines = fh.readlines()
            except IOError:
                return
            self.environ = []
            for line in textlines:
                line = line[:-1].replace('\t', ' ')
                pvname, desc = line.split(None, 1)
                desc = desc.strip()
                self.environ.append((pvname, desc))


    def onXspress3Control(self, event=None):
        if self.ioc_type != 'Xspress3' or caget is None:
            return
        try:
            self.win_xsp3.Raise()
        except:
            self.win_xsp3 = Xspress3ControlFrame(parent=self,
                                                 prefix=self.prefix,
                                                 nmca=self.nmca)



    def onConnectEpics(self, event=None, prefix=None, **kws):
        if prefix is None:
            res  = self.prompt_for_detector(prefix=prefix,
                                            ioc_type=self.ioc_type,
                                            nmca=self.nmca)
            self.prefix, self.det_type, self.ioc_type, self.nmca = res
        else:
            self.prefix = prefix
        self.det_main = 1
        self.connect_to_detector(prefix=self.prefix, ioc_type=self.ioc_type,
                                 det_type=self.det_type, nmca=self.nmca)
        if get_pv is not None and self.incident_energy_pvname is not None:
            self.incident_energy_pv = get_pv(self.incident_energy_pvname,
                                             callback=self.onIncidentEnergy)

    def onIncidentEnergy(self, pvname, value=None, **kws):
        self.incident_energy_kev = value
        if self.incident_energy_units == 'eV':
            self.incident_energy_kev /= 1000.0
        self.det.needs_refresh = True

    def onSaveMCAFile(self, event=None, **kws):
        tmp = '''
        # print('SaveMCA File')
        deffile = ''
        if hasattr(self.mca, 'sourcefile'):
            deffile = "%s%s" % (deffile, getattr(self.mca, 'sourcefile'))
        if hasattr(self.mca, 'areanae'):
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

        env = []
        if len(self.environ) > 0:
            for pvname, desc in self.environ:
                val  = caget(pvname, as_string=True)
                env.append((pvname, val, desc))

        if outfile is not None:
            self.det.save_mcafile(outfile, environ=env)

    def onSaveColumnFile(self, event=None, **kws):
        print( '  EPICS-XRFDisplay onSaveColumnFile not yet implemented  ')
        pass

    def prompt_for_detector(self, prefix=None, ioc_type='Xspress3',  nmca=4):
        dlg = DetectorSelectDialog(prefix=prefix, ioc_type=ioc_type, nmca=nmca)
        dlg.Raise()
        if dlg.ShowModal() == wx.ID_OK:
            dpref = dlg.prefix.GetValue()
            atype = dlg.ioctype.GetStringSelection()
            dtype = dlg.dettype.GetStringSelection()
            nmca = dlg.nelem.GetValue()
            dlg.Destroy()
        return dpref, dtype, atype, nmca

    def connect_to_detector(self, prefix=None, ioc_type='Xspress3',
                            det_type=None, nmca=4):
        self.det = None
        ioc_type = ioc_type.lower()
        if ioc_type.startswith('xspress3'):
            version = 2
            if 'old' in ioc_type:
                version = 1
            self.det = Epics_Xspress3(prefix=prefix, nmca=nmca, version=version)
            self.det.connect()
            time.sleep(0.1)
            self.det.get_mca(mca=1)
            self.needs_newplot=True
        elif ioc_type.startswith('ketek') or ioc_type.startswith('mca'):
            self.det = Epics_KetekMCA(prefix=prefix)
            self.det_type = 'mca'
            self.needs_newplot=True
        else:
            self.det = Epics_MultiXMAP(prefix=prefix, nmca=nmca)
        time.sleep(0.05)
        if self.det is not None:
            self.det.connect_displays(status=self.wids['det_status'],
                                      elapsed=self.wids['elapsed'])

        for imca in range(1, nmca+1):
            self.add_mca(self.det.get_mca(mca=imca), label=f'MCA{imca}', plot=False)


    def show_mca(self, init=False):
        self.needs_newplot = False
        if self.mca is None or self.needs_newplot:
            self.mca = self.det.get_mca(mca=self.det_main)
            self.mca.label = f"MCA{self.det_main}"
            self.mca.real_time = self.det.elapsed_real
            if self.incident_energy_kev is not None:
                self.mca.incident_energy = self.incident_energy_kev

        self.plotmca(self.mca, set_title=False, init=init)
        title = self.mca.label

        bkg_det = self.wids['bkg_det'].GetStringSelection()
        if bkg_det == 'All':
            title = f"{title} with all {self.nmca} detectors"
            for imca in range(1, self.nmca+1):
                label = f"MCA{imca}"
                if label != self.mca.label:
                    thismca = self.xrf_files[label]
                    thismca.counts = self.det.get_array(mca=imca)
                    thismca.energy = self.det.get_energy(mca=imca)
                    thismca.real_time = self.det.elapsed_real
                    c = thismca.counts[:]
                    if self.show_cps:
                        c /= thismca.real_time
                    self.oplot(thismca.energy, c, label=label)
        elif bkg_det != 'None':
            label = bkg_det
            if label != self.mca.label:
                thismca = self.xrf_files.get(label, None)
                imca = int(label.replace('MCA', ''))
                if thismca is not None:
                    thismca.counts = self.det.get_array(mca=imca)
                    thismca.energy = self.det.get_energy(mca=imca)
                    thismca.real_time = self.det.elapsed_real
                    c = thismca.counts[:]
                    if self.show_cps:
                        c /= thismca.real_time
                    self.oplot(thismca.energy, c, label=label)
                    title = f"{title} background: {label}"
        roiname = self.get_roiname()

        if roiname in self.wids['roilist'].GetStrings():
            i = self.wids['roilist'].GetStrings().index(roiname)
            self.wids['roilist'].EnsureVisible(i)
            self.onROI(label=roiname)
        dtime = self.det.get_deadtime(mca=self.det_main)
        if dtime is not None:
            self.wids['deadtime'].SetLabel(f"{dtime:.1f}")
        self.wids['deadtime'].SetForegroundColour(warning_color(dtime, 25, 50))
        self.SetTitle(f"{self.main_title}: {title}")
        self.needs_newplot = False

    def onSaveROIs(self, event=None, **kws):
        dlg = wx.FileDialog(self, message="Save ROI File",
                            defaultDir=get_cwd(),
                            wildcard=ROI_WILDCARD,
                            style = wx.FD_SAVE|wx.FD_CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            roifile = dlg.GetPath()

        self.det.save_rois(roifile)

    def onRestoreROIs(self, event=None, **kws):
        dlg = wx.FileDialog(self, message="Read ROI File",
                            defaultDir=get_cwd(),
                            wildcard=ROI_WILDCARD,
                            style = wx.FD_OPEN|wx.FD_CHANGE_DIR)

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
        MenuItem(self, menu, "Xspress3 Control",
                 "more Xspress3 Detector",
                 self.onXspress3Control)
        menu.AppendSeparator()
        self._menus.insert(1, (menu, 'Detector'))

    def createMainPanel(self):
        epicspanel = self.createEpicsPanel()
        ctrlpanel  = self.createControlPanel()
        rpanel = self.createPlotPanel()

        tx, ty = self.wids['ptable'].GetBestSize()
        cx, cy = ctrlpanel.GetBestSize()
        px, py = self.plotpanel.GetBestSize()

        self.SetSize((950, 625))
        self.SetMinSize((450, 350))

        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL

        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.Add(ctrlpanel, 0, style, 1)
        bsizer.Add(rpanel, 1, style, 1)
        hline = wx.StaticLine(self, size=(425, 2), style=wx.LI_HORIZONTAL|style)


        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(epicspanel, 0, style, 1)
        sizer.Add(hline,      0, style, 1)
        sizer.Add(bsizer,     1, style, 1)
        pack(self, sizer)

        try:
            self.SetIcon(wx.Icon(self.icon_file, wx.BITMAP_TYPE_ICO))
        except:
            pass
        self.set_roilist(mca=None)

    def create_detbuttons(self, pane):
        btnpanel = wx.Panel(pane, name='buttons')
        btnsizer = wx.GridBagSizer(1, 1)
        btns = {}
        sx = 36
        sy = int(sx/2)
        dtype = self.det_type.lower().replace('-', '').replace(' ', '').replace('_', '')
        if dtype == 'mca':
            self.nmca = 1
            btnsizer.Add((sx, sy),  (0, 0), (2, 2), wx.ALIGN_LEFT, 1)
            return btnsizer

        for i in range(1, self.nmca+1):
            b = Button(btnpanel, f'{i}', size=(sx, sx),
                       action=partial(self.onSelectDet, index=i))
            b.SetFont(Font(9))
            self.wids['det%i' % i] = b
            btns[i] = b

        if dtype.startswith('sxd7') and self.nmca == 7:
            btnsizer.Add((sx, sy), (0, 0), (1, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[6],  (1, 0), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[7],  (3, 0), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add((sx, sy), (5, 0), (1, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[5],  (0, 2), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[4],  (2, 2), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[1],  (4, 2), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add((sx, sy), (0, 4), (1, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[3],  (1, 4), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[2],  (3, 4), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add((sx, sy), (5, 4), (1, 2), wx.ALIGN_LEFT, 1)
        elif dtype.startswith('me7') and self.nmca == 7:
            btnsizer.Add((sx, sy), (0, 0), (1, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[7],  (1, 0), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[6],  (3, 0), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add((sx, sy), (5, 0), (1, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[2],  (0, 2), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[1],  (2, 2), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[5],  (4, 2), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add((sx, sy), (0, 4), (1, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[3],  (1, 4), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[4],  (3, 4), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add((sx, sy), (5, 4), (1, 2), wx.ALIGN_LEFT, 1)
        elif dtype.startswith('me4') and self.nmca == 4:
            btnsizer.Add(btns[1],  (0, 0), (1, 1), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[2],  (1, 0), (1, 1), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[3],  (1, 1), (1, 1), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[4],  (0, 1), (1, 1), wx.ALIGN_LEFT, 1)
        else:
            NPERROW = 4
            icol, irow = 0, 0
            for nmca  in range(1, self.nmca+1):
                btnsizer.Add(btns[nmca],  (irow, icol), (1, 1), wx.ALIGN_LEFT, 1)
                icol += 1
                if icol > NPERROW-1:
                    icol = 0
                    irow += 1

        pack(btnpanel, btnsizer)
        return btnpanel

    def createEpicsPanel(self):
        pane = wx.Panel(self, name='epics panel')
        style  = wx.ALIGN_LEFT
        rstyle = wx.ALIGN_RIGHT

        det_btnpanel = self.create_detbuttons(pane)

        bkg_choices = ['None', 'All'] + [f"MCA{i+1}" for i in range(self.nmca)]

        self.wids['det_status'] = SimpleText(pane, ' ', size=(120, -1), style=style)
        self.wids['deadtime']   = SimpleText(pane, ' ', size=(120, -1), style=style)

        if self.nmca > 1:
            self.wids['bkg_det'] = Choice(pane, size=(125, -1), choices=bkg_choices,
                                          action=self.onSelectDet)

        self.wids['dwelltime'] = FloatCtrl(pane, value=0.0, precision=3, minval=0,
                                           size=(80, -1), act_on_losefocus=True,
                                           action=self.onSetDwelltime)
        self.wids['elapsed'] = SimpleText(pane, ' ', size=(80, -1),  style=style)

        self.wids['mca_sum'] = Choice(pane, size=(125, -1),
                                      choices=['Single', 'Accumulate'],
                                      action=self.onMcaSumChoice,
                                      default=1 )

        roipanel = wx.Panel(pane)
        roisizer = wx.GridBagSizer(3, 3)
        rlabel = SimpleText(roipanel, 'Count Rates (Hz)',  style=LEFT, size=(150, -1))
        tlabel = SimpleText(roipanel, 'Output Count Rate',  style=LEFT, size=(150, -1))
        self.wids['roi_name'] = SimpleText(roipanel, '[ROI]', style=LEFT, size=(150, -1))

        roisizer.Add(rlabel,                 (0, 0), (1, 1), LEFT, 1)
        roisizer.Add(tlabel,                 (1, 0), (1, 1), LEFT, 1)
        roisizer.Add(self.wids['roi_name'],  (2, 0), (1, 1), LEFT, 1)

        opts = {'style': RIGHT, 'size': (100, -1)}
        for i in range(1, self.nmca+1):
            l = SimpleText(roipanel, f'MCA {i}', **opts)
            self.wids[f'ocr{i}'] = o = SimpleText(roipanel, ' ', **opts)
            self.wids[f'roi{i}'] = r = SimpleText(roipanel, ' ', **opts)
            o.SetBackgroundColour(get_color('info_bg'))
            r.SetBackgroundColour(get_color('info_bg'))

            roisizer.Add(l,  (0, i), (1, 1), style, 1)
            roisizer.Add(o,  (1, i), (1, 1), style, 1)
            roisizer.Add(r,  (2, i), (1, 1), style, 1)
        pack(roipanel, roisizer)

        b1 =  Button(pane, 'Start',      size=(90, -1), action=self.onStart)
        b2 =  Button(pane, 'Stop',       size=(90, -1), action=self.onStop)
        b3 =  Button(pane, 'Erase',      size=(90, -1), action=self.onErase)
        b4 =  Button(pane, 'Continuous', size=(90, -1), action=partial(self.onStart,
                                                    dtime=0.25, nframes=16000))

        sum_lab = SimpleText(pane, 'Accumulate Mode:',   size=(150, -1))
        if self.nmca > 1:
            bkg_lab = SimpleText(pane, 'Background MCA:',   size=(150, -1))
        pre_lab = SimpleText(pane, 'Dwell Time (s):',   size=(125, -1))
        ela_lab = SimpleText(pane, 'Elapsed Time (s):', size=(125, -1))
        sta_lab = SimpleText(pane, 'Status :',          size=(100, -1))
        dea_lab = SimpleText(pane, '% Deadtime:',       size=(100, -1))

        psizer = wx.GridBagSizer(3, 3)
        psizer.Add(SimpleText(pane, ' MCAs: '),  (0, 0), (1, 1), style, 1)
        psizer.Add(det_btnpanel,           (0, 1), (3, 1), style, 1)
        if self.nmca > 1:
            psizer.Add(bkg_lab,                (0, 2), (1, 1), style, 1)
            psizer.Add(self.wids['bkg_det'],   (0, 3), (1, 1), style, 1)
        psizer.Add(sum_lab,                (1, 2), (1, 1), style, 1)
        psizer.Add(self.wids['mca_sum'],   (1, 3), (1, 1), style, 1)
        psizer.Add(pre_lab,                (0, 4), (1, 1),  style, 1)
        psizer.Add(ela_lab,                (1, 4), (1, 1),  style, 1)
        psizer.Add(self.wids['dwelltime'], (0, 5), (1, 1),  style, 1)
        psizer.Add(self.wids['elapsed'],   (1, 5), (1, 1),  style, 1)

        psizer.Add(b1, (0, 6), (1, 1), style, 1)
        psizer.Add(b4, (0, 7), (1, 1), style, 1)
        psizer.Add(b2, (1, 6), (1, 1), style, 1)
        psizer.Add(b3, (1, 7), (1, 1), style, 1)

        psizer.Add(sta_lab,                  (0, 8), (1, 1), style, 1)
        psizer.Add(self.wids['det_status'],  (0, 9), (1, 1), style, 1)
        psizer.Add(dea_lab,                  (1, 8), (1, 1), style, 1)
        psizer.Add(self.wids['deadtime'],    (1, 9), (1, 1), style, 1)
        psizer.Add(roipanel,                 (2, 2), (1, 8), style, 1)

        pack(pane, psizer)
        # pane.SetMinSize((500, 53))
        if self.det is not None:
            self.det.connect_displays(status=self.wids['det_status'],
                                      elapsed=self.wids['elapsed'])

        wx.CallAfter(self.onSelectDet, index=1, init=True)
        self.timer_counter = 0
        self.mca_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.UpdateData, self.mca_timer)
        self.mca_timer.Start(250)
        return pane

    def UpdateData(self, event=None, force=False):
        self.timer_counter += 1
        if self.mca is None or self.needs_newplot:
            self.show_mca()

        if force or self.det.needs_refresh:
            self.det.needs_refresh = False
            if self.mca is None:
                self.mca = self.det.get_mca(mca=self.det_main)

            dtime = self.det.get_deadtime(mca=self.det_main)
            if dtime is not None:
                self.wids['deadtime'].SetLabel(f"{dtime:.1f}")
            self.wids['deadtime'].SetForegroundColour(warning_color(dtime, 25, 50))
            self.mca.counts = self.det.get_array(mca=self.det_main)*1.0
            self.mca.energy = self.det.get_energy(mca=self.det_main)
            self.mca.real_time = self.det.elapsed_real
            self.mca.incident_energy = self.incident_energy_kev
            if max(self.mca.counts) < 1.0:
                self.mca.counts    = 1e-4*np.ones(len(self.mca.energy))
                self.mca.counts[0] = 2.0
            self.update_mca(self.mca.counts, energy=self.mca.energy, mcalabel=self.mca.label)

    def ShowROIStatus(self, left, right, name='', panel=0):
        if left > right:
            return
        try:
            ftime, nframes = self.det.get_frametime()
        except:
            ftime   = self.det.frametime
            nframes = self.det.nframes
        self.det.elapsed_real = nframes * ftime

        rfmt = "mca{}: {:8,.0f}"

        mca_counts = self.det.mcas[self.det_main-1].get('VAL')
        sum =  mca_counts[left:right].sum()
        thissum = 0
        thisrate = 0

        if name in (None, ''):
            name = 'selected'
        else:
            lname = name.lower()
            for nmca in range(1, self.nmca+1):
                counts = self.det.mcas[nmca-1].get('VAL')
                total = counts.sum()/ftime
                sum = counts[left:right].sum()
                rate = sum/ftime
                self.wids[f'ocr{nmca}'].SetLabel(f'{total:,.0f}')
                self.wids[f'ocr{nmca}'].SetForegroundColour(warning_color(total, 1.25e6, 2.5e6))

                self.wids[f'roi{nmca}'].SetLabel(f'{rate:,.0f}')
                self.wids[f'roi{nmca}'].SetForegroundColour(warning_color(rate, 4.0e5, 8.0e5))
                if self.det_main == nmca:
                    thissum, thisrate = sum, rate
        mfmt = " {:s}: Cts={:10,.0f} :{:10,.1f} Hz"
        self.write_message(mfmt.format(name, thissum, thisrate), panel=panel)
        cname = self.wids['roi_name'].GetLabel().strip()
        if name != cname:
            self.wids['roi_name'].SetLabel(name)

    def onSelectDet(self, event=None, index=0, init=False, **kws):
        if index > 0:
            self.det_main = index

        if self.nmca > 1:
            self.det_back = self.wids['bkg_det'].GetSelection()


        for i in range(1, self.nmca+1):
            dname = 'det%i' % i
            fcol, bcol = 'text', 'info_bg'
            if i == self.det_main:
                fcol, bcol = 'title_blue', 'text_bg'
            if dname in self.wids:
                self.wids[dname].SetBackgroundColour(get_color(bcol))
                self.wids[dname].SetForegroundColour(get_color(fcol))
        self.clear_mcas()
        self.show_mca(init=init)
        self.Refresh()

    def onMcaSumChoice(self, event=None):
        wid = self.wids['mca_sum']
        self.det.set_usesum('accum' in wid.GetStringSelection().lower())

    def onSetDwelltime(self, event=None, **kws):
        if 'dwelltime' in self.wids:
            dtime = self.wids['dwelltime'].GetValue()
            self.det.set_dwelltime(dtime=float(dtime))

    def clear_mcas(self):
        self.mca = None
        # self.x2data = self.y2data = None
        self.needs_newplot = True

    def onStart(self, event=None, dtime=None, nframes=None, **kws):
        if dtime is not None:
            self.wids['dwelltime'].SetValue("%.1f" % dtime)
            self.det.set_dwelltime(dtime=dtime, nframes=nframes)
        else:
            self.det.set_dwelltime(dtime=self.wids['dwelltime'].GetValue(),
                                   nframes=nframes)
        self.det.start()

    def onStop(self, event=None, **kws):
        self.det.stop()
        self.det.needs_refresh = True
        time.sleep(0.05)
        self.UpdateData(event=None, force=True)

    def onErase(self, event=None, **kws):
        self.needs_newplot = True
        self.det.erase()

    def onDelROI(self, event=None):
        roiname = self.get_roiname()
        errmsg = None
        t0 = time.time()
        if self.roilist_sel is None:
            errmsg = 'No ROI selected to delete.'
        if errmsg is not None:
            return Popup(self, errmsg, 'Cannot Delete ROI')

        self.det.del_roi(roiname)
        XRFDisplayFrame.onDelROI(self)


    def onNewROI(self, event=None):
        roiname = self.get_roiname()
        errmsg = None
        if self.xmarker_left is None or self.xmarker_right is None:
            errmsg = 'Must select right and left markers to define ROI'
        elif roiname in self.wids['roilist'].GetStrings():
            errmsg = '%s is already in ROI list - use a unique name.' % roiname
        if errmsg is not None:
            return Popup(self, errmsg, 'Cannot Define ROI')

        confirmed = XRFDisplayFrame.onNewROI(self)
        if confirmed:
            self.det.add_roi(roiname, lo=self.xmarker_left,
                             hi=self.xmarker_right)

    def onRenameROI(self, event=None):
        roiname = self.get_roiname()
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
            self.win_calib = XRFCalibrationFrame(self, mca=self.mca,
                                              larch=self.larch,
                                              callback=self.onSetCalib)

    def onSetCalib(self, offset, slope, mca=None):
        print('XRFControl Set Energy Calibratione' , offset, slope, mca)

    def onClose(self, event=None):
        XRFDisplayFrame.onClose(self)

    def onExit(self, event=None):
        XRFDisplayFrame.onExit(self)

class EpicsXRFApp(LarchWxApp):
    def __init__(self, _larch=None, prefix=None,
                 det_type='ME-4', ioc_type='Xspress3', nmca=4,
                 size=(1100, 800), environ_file=None,
                 incident_energy_pvname=None, incident_energy_units='eV',
                 title='Epics XRF Display', output_title='XRF', **kws):
        self.prefix = prefix
        self.det_type = det_type
        self.ioc_type = ioc_type
        self.nmca = nmca
        self.size = size
        self.environ_file = environ_file
        self.incident_energy_pvname = incident_energy_pvname
        self.incident_energy_units = incident_energy_units
        self.title = title
        self.output_title = output_title
        LarchWxApp.__init__(self, _larch=_larch, **kws)

    def createApp(self):
        frame = EpicsXRFDisplayFrame(prefix=self.prefix,
                                     det_type=self.det_type,
                                     ioc_type=self.ioc_type,
                                     nmca=self.nmca,
                                     size=self.size,
                                     incident_energy_pvname=self.incident_energy_pvname,
                                     incident_energy_units=self.incident_energy_units,
                                     environ_file=self.environ_file,
                                     title=self.title,
                                     output_title=self.output_title,
                                     _larch=self._larch)
        frame.Show()
        frame.Raise()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    EpicsXRFApp().MainLoop()
