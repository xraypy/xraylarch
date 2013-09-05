#!/usr/bin/env python
"""
Main GUI form for setting up and executing Step Scans

Principle features:
   1.  read configuration file, tie to database...
   2.  wx.ChoiceBox (exclusive panel) for
         Linear Scans
         Mesh Scans (2d maps)
         XAFS Scans
         Fly Scans (optional)

   3.  Other notes:
       Linear Scans support Slave positioners
       A Scan Definition files describes an individual scan.
       Separate popup window for Detectors (Trigger + set of Counters)
       Allow adding any additional Counter
       Builtin Support for Detectors: Scalers, MultiMCAs, and AreaDetectors
       Give File Prefix on Scan Form
       options window for settling times
       Plot Window allows simple math of columns
       Plot Window supports shows position has "Go To" button.

   4. To consider / add:
       keep sqlite db of scan defs / scan names (do a scan like 'xxxx')
       plot window can do simple analysis?

To Do:
  calculate / display estimated scan time on changes
  plotting window with drop-downs for column math
  detector selection
  encapsulate (json?) scan parameters

"""
import os
import sys
import time
import shutil
import numpy as np
import json
from datetime import timedelta
from threading import Thread

import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection

import epics
from epics.wx import DelayedEpicsCallback, EpicsFunction, finalize_epics
from epics.wx.utils import popup

from .gui_utils import SimpleText, FloatCtrl, Closure
from .gui_utils import pack, add_button, add_menu, add_choice, add_menu

from ..stepscan import StepScan
from ..xafs_scan import XAFS_Scan

from ..file_utils import new_filename, increment_filename, nativepath
from ..ordereddict import OrderedDict

from ..station_config import StationConfig
from ..scandb import ScanDB

from .scan_panels import (LinearScanPanel, MeshScanPanel,
                          SlewScanPanel,   XAFSScanPanel)

from ..positioner import Positioner
from ..detectors import (SimpleDetector, ScalerDetector, McaDetector,
                         MultiMcaDetector, AreaDetector, get_detector)

from .edit_positioners import PositionerFrame
from .edit_detectors import DetectorFrame
from .edit_general import SetupFrame

ALL_CEN =  wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL
FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

class ScanFrame(wx.Frame):
    _about = """StepScan GUI
  Matt Newville <newville @ cars.uchicago.edu>
  """
    _ini_wildcard = "Epics Scan Settings(*.ini)|*.ini|All files (*.*)|*.*"
    ini_default  = "epicsscans.ini"
    _cnf_wildcard = "Scan Definition(*.cnf)|*.cnf|All files (*.*)|*.*"
    _cnf_default  = "scan.cnf"

    def __init__(self, inifile=None,  **kwds):

        if inifile is None:
            inifile = self.ini_default

        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, None, -1, **kwds)

        self.pvlist = {}
        # list of available detectors and whether to use them
        self.detectors  =  OrderedDict()
        # list of extra counters and whether to use them
        self.extra_counters = OrderedDict()

        self.init_scandb(inifile)
        self._larch = None
        self.epics_status = 0
        self.larch_status = 0
        wx.EVT_CLOSE(self, self.onClose)

        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ["Initializing...", "Status"]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        self.scantimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onScanTimer, self.scantimer)

        # self.connect_epics()
        self.inittimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onInitTimer, self.inittimer)
        self.inittimer.Start(100)

    def init_scandb(self, inifile):
        """initialize connection to scan db,
        make sure values from ini file are in database"""
        config = StationConfig(inifile)        
        kwargs = {'create': True}
        kwargs.update(config.server)
        dbname = kwargs.pop('dbname')
        # kwargs.pop('use')
        if 'port' in kwargs:
            kwargs['port'] = int(kwargs['port'])

        self._scandb = ScanDB(dbname, **kwargs)
        self._scandb.read_station_config(config)

    def add_scanpanel(self, creator, title):
        span = creator(self, scandb=self._scandb, pvlist=self.pvlist)
        self.nb.AddPage(span, title, True)
        self.scanpanels[title] = span

    def createMainPanel(self):
        self.Font16=wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font14=wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font12=wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font11=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        self.SetTitle("Epics Scans")
        self.SetSize((700, 575))
        self.SetFont(self.Font11)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.nb = flat_nb.FlatNotebook(self, wx.ID_ANY, agwStyle=FNB_STYLE)
        self.nb.SetBackgroundColour('#FCFCFA')
        self.SetBackgroundColour('#F0F0E8')

        self.scanpanels = {}
        for name, creator in (('Linear Scan',  LinearScanPanel),
                              ('Mesh Scan',    MeshScanPanel),
                              ('Slew Scan',    SlewScanPanel),
                              ('XAFS Scan',    XAFSScanPanel)
                              ):
            self.add_scanpanel(creator, name)

        self.nb.SetSelection(0)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)
        sizer.Add(wx.StaticLine(self, size=(675, 3),
                                style=wx.LI_HORIZONTAL), 0, wx.EXPAND)

        # bottom panel
        bpanel = wx.Panel(self)
        bsizer = wx.GridBagSizer(3, 5)

        self.nscans = FloatCtrl(bpanel, precision=0, value=1, minval=0, size=(45, -1))

        self.filename = wx.TextCtrl(bpanel, -1, self._scandb.get_info('filename', ''))
        self.filename.SetMinSize((400, 25))

        self.user_comms = wx.TextCtrl(bpanel, -1, "", style=wx.TE_MULTILINE)
        self.user_comms.SetMinSize((400, 75))

        self.msg1  = SimpleText(bpanel, "    ", size=(200, -1))
        self.msg2  = SimpleText(bpanel, "    ", size=(200, -1))
        self.msg3  = SimpleText(bpanel, "    ", size=(200, -1))
        self.start_btn = add_button(bpanel, "Start Scan", action=self.onStartScan)
        self.abort_btn = add_button(bpanel, "Abort Scan", action=self.onAbortScan)
        self.abort_btn.Disable()

        sty = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        bsizer.Add(SimpleText(bpanel, "Number of Scans:"), (0, 0), (1, 1), sty)
        bsizer.Add(SimpleText(bpanel, "File Name:"),       (1, 0), (1, 1), sty)
        bsizer.Add(SimpleText(bpanel, "Comments:"),        (2, 0), (1, 1), sty)
        bsizer.Add(self.nscans,     (0, 1), (1, 1), sty, 2)
        bsizer.Add(self.filename,   (1, 1), (1, 2), sty, 2)
        bsizer.Add(self.user_comms, (2, 1), (1, 2), sty, 2)
        bsizer.Add(self.msg1,       (0, 4), (1, 1), sty, 2)
        bsizer.Add(self.msg2,       (1, 4), (1, 1), sty, 2)
        bsizer.Add(self.msg3,       (2, 4), (1, 1), sty, 2)
        bsizer.Add(self.start_btn,  (3, 0), (1, 1), sty, 5)
        bsizer.Add(self.abort_btn,  (3, 1), (1, 1), sty, 5)

        bpanel.SetSizer(bsizer)
        bsizer.Fit(bpanel)
        sizer.Add(bpanel, 0, ALL_CEN, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)

    def onScanTimer(self, evt=None):
        if self.scan_cpt == self.scan.cpt:
            return
        self.scan_cpt = self.scan.cpt
        msg = "Point %i / %i" % (self.scan.cpt, self.scan.npts)
        self.statusbar.SetStatusText(msg, 0)
        if self.scan.complete:
            self.scantimer.Stop()

    def onInitTimer(self, evt=None):
        if self.larch_status == 0:
            self.ini_larch_thread = Thread(target=self.init_larch)
            self.ini_larch_thread.start()

        if self.epics_status == 0:
            # self.connect_epics()
            # pass
            self.ini_epics_thread = Thread(target=self.connect_epics)
            self.ini_epics_thread.start()

        if (self.epics_status == 1 and self.larch_status == 1):
            time.sleep(0.05)
            self.ini_larch_thread.join()
            self.ini_epics_thread.join()
            for span in self.scanpanels.values():
                span.initialize_positions()
            self.inittimer.Stop()
            self.statusbar.SetStatusText('', 0)
            self.statusbar.SetStatusText('Ready', 1)

    def init_larch(self):
        self.larch_status = -1
        import larch
        self._larch = larch.Interpreter()
        for span in self.scanpanels.values():
            span.larch = self._larch
        self.statusbar.SetStatusText('Larch Ready')
        self.larch_status = 1


    @EpicsFunction
    def connect_epics(self):
        t0 = time.time()
        for db_pv in self._scandb.getall('pvs'):
            name = db_pv.name
            self.pvlist[name] = epics.PV(name)

        for det in self._scandb.getall('scandetectors'):
            opts = json.loads(det.options)
            opts['label'] = det.name
            opts['kind'] = det.kind 
            self.detectors[det.name] = get_detector(det.pvname, **opts)

        self.epics_status = 1
        time.sleep(0.05)
        self.statusbar.SetStatusText('Epics Ready')

    def onStartScan(self, evt=None):
        panel = self.nb.GetCurrentPage()
        scan = panel.generate_scan()

        scan['detectors'] = []
        scan['counters'] = []
        scan['extra_pvs'] = []
        print 'START SCAN ..'
        for label, val in self.config.detectors.items():
            prefix, opts = val
            opts['label'] = label
            opts['prefix'] = prefix
            scan['detectors'].append(opts)
        for label, pvname in self.config.counters.items():
            scan['counters'].append((label, pvname))

        for label, pvname in self.config.extra_pvs.items():
            scan['extra_pvs'].append((label, pvname))

        scan['nscans'] = int(self.nscans.GetValue())
        scan['filename'] = self.filename.GetValue()
        scan['user_comments'] = self.user_comms.GetValue()
        scan['pos_settle_time'] = 0.010
        scan['det_settle_time'] = 0.010
        f = open('scan.cnf', 'w')
        f.write("%s\n" % json.dumps(scan, ensure_ascii=True))
        self.run_scan(scan)

    def run_scan(self, conf):
        """runs a scan as specified in a scan configuration dictionary"""
        self.statusbar.SetStatusText('Starting...', 1)

        if conf['type'] == 'xafs':
            scan  = XAFS_Scan()
            isrel = conf['is_relative']
            e0    = conf['e0']
            t_kw  = conf['time_kw']
            t_max = conf['max_time']
            nreg  = len(conf['regions'])
            kws   = {'relative': isrel, 'e0':e0}

            for i, det in enumerate(conf['regions']):
                start, stop, npts, dt, units = det
                kws['dtime'] =  dt
                kws['use_k'] =  units.lower() !='ev'
                if i == nreg-1: # final reg
                    if t_max > 0.01 and t_kw>0 and kws['use_k']:
                        kws['dtime_final'] = t_max
                        kws['dtime_wt'] = t_kw
                scan.add_region(start, stop, npts=npts, **kws)

        elif conf['type'] == 'linear':
            scan = StepScan()
            for pos in conf['positioners']:
                label, pvs, start, stop, npts = pos
                p = Positioner(pvs[0], label=label)
                p.array = np.linspace(start, stop, npts)
                scan.add_positioner(p)
                if len(pvs) > 0:
                    scan.add_counter(pvs[1], label="%s(read)" % label)

        for det in conf['detectors']:
            scan.add_detector(get_detector(**det))

        if 'counters' in conf:
            for label, pvname  in conf['counters']:
                scan.add_counter(pvname, label=label)

        scan.add_extra_pvs(conf['extra_pvs'])

        scan.dwelltime = conf['dwelltime']
        scan.comments  = conf['user_comments']
        scan.filename  = conf['filename']
        scan.pos_settle_time = conf['pos_settle_time']
        scan.det_settle_time = conf['det_settle_time']

        self.scan = scan
        self.scan_cpt = -1

        self.statusbar.SetStatusText('Scanning ', 1)
        self.scantimer.Start(100)
        app = wx.GetApp()
        for i in range(conf['nscans']):
            self.scan_thread = Thread(target=scan.run)
            self.scan_thread.start()
            while not scan.complete:
                t0 = time.time()
                eloop = wx.EventLoop()
                eact = wx.EventLoopActivator(eloop)
                while eloop.Pending() and time.time()-t0 < 0.25:
                    eloop.Dispatch()
                app.ProcessIdle()
                del eact
                if scan.cpt > 2 and scan.cpt == scan.npts:
                    break
            self.scantimer.Stop()
            self.scan_thread.join()
            print 'done!  wrote %s' % scan.filename
            self.statusbar.SetStatusText('Wrote %s' %  scan.filename, 0)
        self.statusbar.SetStatusText('Scan Complete', 1)
        self.scantimer.Stop()

    def onAbortScan(self, evt=None):
        print 'Abort Scan ', evt

    def createMenus(self):
        self.menubar = wx.MenuBar()
        # file
        fmenu = wx.Menu()
        add_menu(self, fmenu, "&Open Scan Definition\tCtrl+O",
                 "Read Scan Defintion",  self.onReadScanDef)
        add_menu(self, fmenu,"&Save Scan Definition\tCtrl+S",
                  "Save Scan Definition", self.onSaveScanDef)

        fmenu.AppendSeparator()
        add_menu(self, fmenu, "Load Settings\tCtrl+L",
                 "Load Settings", self.onLoadSettings)

        add_menu(self, fmenu,"Save Settings\tCtrl+R",
                  "Save Settings", self.onSaveSettings)

        fmenu.AppendSeparator()

        add_menu(self, fmenu,'Change &Working Folder\tCtrl+W',
                  "Choose working directory",  self.onFolderSelect)
        fmenu.AppendSeparator()
        add_menu(self, fmenu, "&Quit\tCtrl+Q",
                  "Quit program", self.onClose)

        # options
        pmenu = wx.Menu()
        add_menu(self, pmenu, "General\tCtrl+G",
                 "General Setup", self.onSetupMisc)

        add_menu(self, pmenu, "Positioners\tCtrl+P",
                  "Setup Motors and Positioners", self.onSetupPositioners)
        add_menu(self, pmenu, "Detectors\tCtrl+D",
                  "Setup Detectors and Counters", self.onSetupDetectors)
        # help
        hmenu = wx.Menu()
        add_menu(self, hmenu, "&About",
                  "More information about this program",  self.onAbout)

        self.menubar.Append(fmenu, "&File")
        self.menubar.Append(pmenu, "&Setup")
        self.menubar.Append(hmenu, "&Help")
        self.SetMenuBar(self.menubar)

    def onAbout(self,evt):
        dlg = wx.MessageDialog(self, self._about,"About Epics StepScan",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self, evt=None):
        ret = popup(self, "Really Quit?", "Exit Epics Scan?",
                    style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
        if ret == wx.ID_YES:
            self.Destroy()

    def onSetupMisc(self, evt=None):
        SetupFrame(self)

    def onSetupPositioners(self, evt=None):
        PositionerFrame(self)

    def onSetupDetectors(self, evt=None):
        DetectorFrame(self)

    def onFolderSelect(self,evt):
        style = wx.DD_DIR_MUST_EXIST|wx.DD_DEFAULT_STYLE

        dlg = wx.DirDialog(self, "Select Working Directory:", os.getcwd(),
                           style=style)

        if dlg.ShowModal() == wx.ID_OK:
            basedir = os.path.abspath(str(dlg.GetPath()))
            try:
                os.chdir(nativepath(basedir))
            except OSError:
                pass
        dlg.Destroy()

    def onSaveScanDef(self, evt=None):
        print 'on SaveScan Def'

    def onReadScanDef(self, evt=None):
        print 'on ReadScan Def event (for a particular scan)'

    def onSaveSettings(self, evt=None):
        fout = self.conffile
        if fout is None:
            fout = self._ini_default
        dlg = wx.FileDialog(self, message="Save EpicsScan Settings",
                            defaultDir=os.getcwd(),
                            defaultFile=fout,
                            wildcard=self._ini_wildcard,
                            style=wx.SAVE|wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            self.config.Save(dlg.GetPath())
        dlg.Destroy()

    def onLoadSettings(self, evt=None):
        fname = self.conffile
        if fname is None: fname = ''
        dlg = wx.FileDialog(self, message="Load EpicsScan Settings",
                            defaultDir=os.getcwd(),
                            defaultFile=fname,
                            wildcard=self._ini_wildcard,
                            style=wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.config.Read(path)
            print 'read settings - should run init_epics to redefine self.detectors....'
            for span in self.scanpanels.values():
                span.use_config(self.config)
        dlg.Destroy()

class ScanApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, config=None, dbname=None, **kws):
        self.config  = config
        self.dbname  = dbname
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        frame = ScanFrame()
        frame.Show()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    app = wx.App()
    i = ScanFrame()
    i.Show()
    app.MainLoop()
