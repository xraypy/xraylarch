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

HAS_PLOT = False
try:
    from wxmplot import PlotPanel
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

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


import larch
from larch.site_config import icondir
from larch.wxlib import PeriodicTablePanel, LarchWxApp
from larch.wxlib.xrfdisplay import (XRFDisplayFrame, XRFCalibrationFrame,
                                    FILE_WILDCARDS)

ROI_WILDCARD = 'Data files (*.dat)|*.dat|ROI files (*.roi)|*.roi|All files (*.*)|*.*'
try:
    from epics import caget
    from .xrf_detectors import Epics_MultiXMAP, Epics_Xspress3
except:
    pass

HAS_SCANDB = False
try:
    from epicsscan import ScanDB
    HAS_SCANDB = True
except:
    pass

class DetectorSelectDialog(wx.Dialog):
    """Connect to an Epics MCA detector
    Can be either XIA xMAP  or Quantum XSPress3
    """
    msg = '''Select XIA xMAP or Quantum XSPress3 MultiElement MCA detector'''
    det_types = ('SXD-7', 'ME-7', 'ME-4', 'other')
    ioc_types = ('Xspress3.1', 'xMAP', 'Xspress3.0')
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

        self.SetBackgroundColour((240, 240, 230))
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


class EpicsXRFDisplayFrame(XRFDisplayFrame):
    _about = """Epics XRF Spectra Display
  Matt Newville <newville @ cars.uchicago.edu>
  """
    me4_layout = ((0, 0), (1, 0), (1, 1), (0, 1))
    main_title = 'Epics XRF Control'

    def __init__(self, parent=None, _larch=None, prefix=None,
                 det_type='ME-4', ioc_type='Xspress3', nmca=4,
                 size=(725, 580), environ_file=None, scandb_conn=None,
                 title='Epics XRF Display', output_title='XRF', **kws):

        self.det_type = det_type
        self.ioc_type = ioc_type
        self.nmca = nmca
        self.det_fore = 1
        self.det_back = 0
        self.scandb = None
        self.environ = []
        if environ_file is not None:
            self.read_environfile(environ_file)
        if HAS_SCANDB and scandb_conn is not None:
            self.ConnectScanDB(**scandb_conn)

        self.onConnectEpics(event=None, prefix=prefix)

        self.icon_file = os.path.join(icondir, 'ptable.ico')

        XRFDisplayFrame.__init__(self, parent=parent, _larch=_larch,
                                 title=title, size=size, **kws)

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
                pvname, desc = line.split(' ', 1)
                desc = desc.strip()
                self.environ.append((pvname, desc))

    def onConnectEpics(self, event=None, prefix=None, **kws):
        if prefix is None:
            res  = self.prompt_for_detector(prefix=prefix,
                                            ioc_type=self.ioc_type,
                                            nmca=self.nmca)
            self.prefix, self.det_type, self.ioc_type, self.nmca = res
        else:
            self.prefix = prefix
        self.det_fore = 1
        self.det_back = 0
        self.clear_mcas()
        self.connect_to_detector(prefix=self.prefix, ioc_type=self.ioc_type,
                                 det_type=self.det_type, nmca=self.nmca)

    def ConnectScanDB(self, **kws):
        if not HAS_SCANDB:
            return
        self.scandb = ScanDB(**kws)
        if self.scandb is not None:
            basedir = self.scandb.get_info('user_folder')
            fileroot = self.scandb.get_info('server_fileroot')
        basedir = str(basedir)
        fileroot = str(fileroot)
        if basedir.startswith(fileroot):
            basedir = basedir[len(fileroot):]
        fullpath = os.path.join(fileroot, basedir)
        fullpath = fullpath.replace('\\', '/').replace('//', '/')
        curdir = os.getcwd()
        try:
            os.chdir(fullpath)
        except:
            os.chdir(curdir)
        self.scandb.connect_pvs()

    def onSaveMCAFile(self, event=None, **kws):
        tmp = '''
        # print('SaveMCA File')
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

        environ = []
        if HAS_SCANDB and self.scandb is not None:
            c, table = self.scandb.get_table('pvs')
            pvrows = self.scandb.query(table).all()
            for row in pvrows:
                addr = str(row.name)
                desc = str(row.notes)
                val  = self.scandb.pvs[addr].get(as_string=True)
                environ.append((addr, val, desc))

        elif len(self.environ) > 0:
            for pvname, desc in self.environ:
                val  = caget(pvname, as_string=True)
                environ.append((pvname, val, desc))

        if outfile is not None:
            self.det.save_mcafile(outfile, environ=environ)

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
            time.sleep(0.5)
            self.det.get_mca(mca=1)
            self.needs_newplot=True
        else:
            self.det = Epics_MultiXMAP(prefix=prefix, nmca=nmca)
        time.sleep(0.05)
        # print(" Got detector ")
        # for name, p in self.det._xsp3._pvs.items():
        #    print(p, p._auto_monitor)
            
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

        roiname = self.get_roiname()

        if roiname in self.wids['roilist'].GetStrings():
            i = self.wids['roilist'].GetStrings().index(roiname)
            self.wids['roilist'].EnsureVisible(i)
            self.onROI(label=roiname)
        dtime = self.det.get_deadtime(mca=self.det_fore)
        if dtime is not None:
            self.wids['deadtime'].SetLabel("%.1f" % dtime)
        self.SetTitle("%s: %s" % (self.main_title, title))
        self.needs_newplot = False

    def onSaveROIs(self, event=None, **kws):
        dlg = wx.FileDialog(self, message="Save ROI File",
                            defaultDir=os.getcwd(),
                            wildcard=ROI_WILDCARD,
                            style = wx.FD_SAVE|wx.FD_CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            roifile = dlg.GetPath()

        self.det.save_rois(roifile)

    def onRestoreROIs(self, event=None, **kws):
        dlg = wx.FileDialog(self, message="Read ROI File",
                            defaultDir=os.getcwd(),
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

        try:
            self.SetIcon(wx.Icon(self.icon_file, wx.BITMAP_TYPE_ICO))
        except:
            pass
        self.set_roilist(mca=None)

    def create_detbuttons(self, pane):
        btnpanel = wx.Panel(pane, name='buttons')
        btnsizer = wx.GridBagSizer(1, 1)        
        btns = {}
        sx = 30
        sy = int(sx/2)
        for i in range(1, self.nmca+1):
            b = Button(btnpanel, '%d' % i, size=(sx, sx),
                       action=partial(self.onSelectDet, index=i))
            b.SetFont(Font(10))
            self.wids['det%i' % i] = b
            btns[i] = b
        dtype = self.det_type.lower().replace('-', '').replace(' ', '').replace('_', '')
           
        if dtype.startswith('sxd7') and self.nmca == 7:
            btnsizer.Add((sx, sy), (0, 0), (1, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[4],  (1, 0), (2, 2), wx.ALIGN_LEFT, 1)            
            btnsizer.Add(btns[5],  (3, 0), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add((sx, sy), (5, 0), (1, 2), wx.ALIGN_LEFT, 1)            
            btnsizer.Add(btns[3],  (0, 2), (2, 2), wx.ALIGN_LEFT, 1)            
            btnsizer.Add(btns[7],  (2, 2), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[6],  (4, 2), (2, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add((sx, sy), (0, 4), (1, 2), wx.ALIGN_LEFT, 1)
            btnsizer.Add(btns[2],  (1, 4), (2, 2), wx.ALIGN_LEFT, 1)            
            btnsizer.Add(btns[1],  (3, 4), (2, 2), wx.ALIGN_LEFT, 1)
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

        bkg_choices = ['None'] + ["%d" % (i+1) for i in range(self.nmca)]

        self.wids['det_status'] = SimpleText(pane, ' ', size=(120, -1), style=style)
        self.wids['deadtime']   = SimpleText(pane, ' ', size=(120, -1), style=style)

        self.wids['bkg_det'] = Choice(pane, size=(100, -1), choices=bkg_choices,
                                      action=self.onSelectDet)

        self.wids['dwelltime'] = FloatCtrl(pane, value=0.0, precision=1, minval=0,
                                           size=(80, -1), act_on_losefocus=True,
                                           action=self.onSetDwelltime)
        self.wids['elapsed'] = SimpleText(pane, ' ', size=(80, -1),  style=style)

        self.wids['mca_sum'] = Choice(pane, size=(100, -1),
                                      choices=['Single', 'Accumulate'],
                                      action=self.onMcaSumChoice,
                                      default=1 )

        b1 =  Button(pane, 'Start',      size=(90, -1), action=self.onStart)
        b2 =  Button(pane, 'Stop',       size=(90, -1), action=self.onStop)
        b3 =  Button(pane, 'Erase',      size=(90, -1), action=self.onErase)
        b4 =  Button(pane, 'Continuous', size=(90, -1), action=partial(self.onStart,
                                                                       dtime=0.0))

        sum_lab = SimpleText(pane, 'Accumulate Mode:',   size=(150, -1))
        bkg_lab = SimpleText(pane, 'Background MCA:',   size=(150, -1))
        pre_lab = SimpleText(pane, 'Dwell Time (s):',   size=(125, -1))
        ela_lab = SimpleText(pane, 'Elapsed Time (s):', size=(125, -1))
        sta_lab = SimpleText(pane, 'Status :',          size=(100, -1))
        dea_lab = SimpleText(pane, '% Deadtime:',       size=(100, -1))

        psizer = wx.GridBagSizer(5, 5)
        psizer.Add(SimpleText(pane, ' MCAs: '),  (0, 0), (1, 1), style, 1)
        psizer.Add(det_btnpanel,           (0, 1), (2, 1), style, 1)
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
        pack(pane, psizer)
        # pane.SetMinSize((500, 53))
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
        # self.elapsed_real = self.det.elapsed_real
        self.mca.real_time = self.det.elapsed_real
        # print("Update Data  ", force, self.det.needs_refresh)

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

            dtime = self.det.get_deadtime(mca=self.det_fore)
            if dtime is not None:
                self.wids['deadtime'].SetLabel("%.1f" % dtime)

            counts = self.det.get_array(mca=self.det_fore)*1.0
            energy = self.det.get_energy(mca=self.det_fore)
            if max(counts) < 1.0:
                counts    = 1e-4*np.ones(len(counts))
                counts[0] = 2.0
            self.update_mca(counts, energy=energy)

    def ShowROIStatus(self, left, right, name='', panel=0):
        if left > right:
            return
        sum = self.ydata[left:right].sum()

        try:
            ftime, nframes = self.det.get_frametime()
        except:
            ftime   = self.det.frametime
            nframes = self.det.nframes
        self.det.elapsed_real = nframes * ftime

        mca_counts = self.det.mcas[self.det_fore-1].get('VAL')
        sum =  mca_counts[left:right].sum()
        # print("ROI STATUS ", name, ftime, nframes, sum, cps, mca_counts.sum(),  mca_counts)
        if name in (None, ''):
            name = 'Selected'
        else:
            for roi in self.det.mcas[self.det_fore-1].rois:
                if name.lower() == roi.name.lower():
                    try:
                        sum = roi.sum
                    except:
                        pass
        cps = sum/ftime
        if cps < 0: cps = 0
        # print("ROI STATUS ", name, _counts, cps)
        fmt = " {:s}: Cts={:10,.0f} :{:10,.1f} Hz"
        self.write_message(fmt.format(name, sum, cps), panel=panel)

    def onSelectDet(self, event=None, index=0, init=False, **kws):
        if index > 0:
            self.det_fore = index
        self.det_back = self.wids['bkg_det'].GetSelection()
        if self.det_fore  == self.det_back:
            self.det_back = 0

        for i in range(1, self.nmca+1):
            dname = 'det%i' % i
            bcol = (210, 210, 210)
            fcol = (0, 0, 0)
            if i == self.det_fore:
                fcol = (200,  20,  20)
                bcol = (250, 250, 250)
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

    def onMcaSumChoice(self, event=None):
        wid = self.wids['mca_sum']
        self.det.set_usesum('accum' in wid.GetStringSelection().lower())

    def onSetDwelltime(self, event=None, **kws):
        if 'dwelltime' in self.wids:
            self.det.set_dwelltime(dtime=self.wids['dwelltime'].GetValue())

    def clear_mcas(self):
        self.mca = self.mca2 = None
        self.x2data = self.y2data = None
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
        self.onStop()
        XRFDisplayFrame.onClose(self)

    def onExit(self, event=None):
        self.onStop()
        XRFDisplayFrame.onExit(self)

class EpicsXRFApp(LarchWxApp):
    def __init__(self, _larch=None, prefix=None,
                 det_type='ME-4', ioc_type='Xspress3', nmca=4,
                 size=(725, 580), environ_file=None, scandb_conn=None,
                 title='Epics XRF Display', output_title='XRF', **kws):
        self.prefix = prefix
        self.det_type = det_type
        self.ioc_type = ioc_type
        self.nmca = nmca
        self.size = size
        self.environ_file = environ_file
        self.scandb_conn = scandb_conn
        self.title = title
        self.output_title = output_title
        LarchWxApp.__init__(self, _larch=_larch, **kws)

    def createApp(self):
        frame = EpicsXRFDisplayFrame(prefix=self.prefix,
                                     det_type=self.det_type,
                                     ioc_type=self.ioc_type,
                                     nmca=self.nmca, size=self.size,
                                     environ_file=self.environ_file,
                                     scandb_conn=self.scandb_conn,
                                     title=self.title,
                                     output_title=self.output_title,
                                     _larch=self._larch)
        frame.Show()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    EpicsXRFApp().MainLoop()
