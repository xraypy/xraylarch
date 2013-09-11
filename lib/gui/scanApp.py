#!/usr/bin/env python
"""
Main GUI form for setting up and executing Step Scans

Principle features:
   1. read simple configuration file, tie to database (postgres)
   2. notebook panels for
         Linear Scans
         Mesh Scans (2d maps)
         XAFS Scans
         Fly Scans (optional)

   3.  Other notes:
       Linear Scans support Slave positioners
       A Scan Definition files describes an individual scan.
       Separate window for configuring Detectors (Trigger + set of Counters)
           and Positioners, including adding any additional Counter
       Builtin Support for Detectors: Scalers, MultiMCAs, and AreaDetectors
       calculate / display estimated scan time on changes

       Give File Prefix on Scan Form

To Do:
   Plot Window allows simple math of columns, has "Go To" button.
   Plot window with drop-downs for column math, simple fits

   Sequence Window
   Edit Macros
   

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
from .edit_detectors   import DetectorFrame
from .edit_general     import SettingsFrame
from .edit_extrapvs    import ExtraPVsFrame
from .edit_scandefs    import ScandefsFrame
from .edit_sequences   import SequencesFrame
from .edit_macros      import MacrosFrame


ALL_CEN =  wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL
FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

class ScanFrame(wx.Frame):
    _about = """StepScan GUI
  Matt Newville <newville @ cars.uchicago.edu>
  """
    _ini_wildcard = "Epics Scan Settings(*.ini)|*.ini|All files (*.*)|*.*"
    ini_default   = "epicsscans.ini"
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
        self.subframes = {}
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

        self.scandb = ScanDB(dbname, **kwargs)
        self.scandb.read_station_config(config)


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
        inb  = 0
        for name, creator in (('Linear',  LinearScanPanel),
                              ('Mesh',    MeshScanPanel),
                              ('Slew',    SlewScanPanel),
                              ('XAFS',    XAFSScanPanel)):
            span = creator(self, scandb=self.scandb, pvlist=self.pvlist)
            self.nb.AddPage(span, "%s Scan" % name, True)
            self.scanpanels[name.lower()] =  (inb, span)
            inb += 1

        self.nb.SetSelection(0)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)
        sizer.Add(wx.StaticLine(self, size=(675, 3),
                                style=wx.LI_HORIZONTAL), 0, wx.EXPAND)

        # bottom panel
        bpanel = wx.Panel(self)
        bsizer = wx.GridBagSizer(3, 5)

        self.nscans = FloatCtrl(bpanel, precision=0, value=1, minval=0, size=(45, -1))

        self.filename = wx.TextCtrl(bpanel, -1, self.scandb.get_info('filename', ''))
        self.filename.SetMinSize((400, 25))

        self.user_comms = wx.TextCtrl(bpanel, -1, "", style=wx.TE_MULTILINE)
        self.user_comms.SetMinSize((400, 75))

        self.msg1  = SimpleText(bpanel, "    ", size=(200, -1))
        self.msg2  = SimpleText(bpanel, "    ", size=(200, -1))
        self.msg3  = SimpleText(bpanel, "    ", size=(200, -1))
        self.start_btn = add_button(bpanel, "Start", action=self.onStartScan)
        self.abort_btn = add_button(bpanel, "Abort", action=self.onAbortScan)
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
        # print 'on init ', self.larch_status, self.epics_status, time.ctime()
        if self.larch_status == 0:
            self.ini_larch_thread = Thread(target=self.init_larch)
            self.ini_larch_thread.start()

        if self.epics_status == 0:
            self.ini_epics_thread = Thread(target=self.connect_epics)
            self.ini_epics_thread.start()

        if (self.epics_status == 1 and self.larch_status == 1):
            time.sleep(0.05)
            self.ini_larch_thread.join()
            self.ini_epics_thread.join()
            for inb, span in self.scanpanels.values():
                span.initialize_positions()
            self.inittimer.Stop()
            self.statusbar.SetStatusText('', 0)
            self.statusbar.SetStatusText('Ready', 1)

    def init_larch(self):
        self.larch_status = -1
        import larch
        self._larch = larch.Interpreter()
        for inb, span in self.scanpanels.values():
            span.larch = self._larch
        self.statusbar.SetStatusText('Larch Ready')
        self.larch_status = 1


    @EpicsFunction
    def connect_epics(self):
        t0 = time.time()
        for db_pv in self.scandb.getall('pvs'):
            name = db_pv.name
            if len(name) < 1:
                continue
            self.pvlist[name] = epics.PV(name)
        for det in self.scandb.get_detectors():
            opts = json.loads(det.options)
            opts['label'] = det.name
            opts['kind'] = det.kind 
            self.detectors[det.name] = get_detector(det.pvname, **opts)
        
        self.epics_status = 1
        time.sleep(0.05)
        self.statusbar.SetStatusText('Epics Ready')

    def generate_scan(self, scanname=None):
        """generate scan definition from current values on GUI"""
        if scanname is None:
            scanname = time.strftime("__%b%d%H%M%S_")
            
        scan = self.nb.GetCurrentPage().generate_scan()
        scan['nscans'] = int(self.nscans.GetValue())

        sdb = self.scandb
        fname = self.filename.GetValue()
        scan['filename'] = fname
        scan['user_comments'] = self.user_comms.GetValue()

        scan['pos_settle_time'] = float(sdb.get_info('pos_settle_time'))
        scan['det_settle_time'] = float(sdb.get_info('det_settle_time'))
        
        scan['detectors'] = []
        scan['counters']  = []
        scan['extra_pvs'] = []
        for det in sdb.select('scandetectors', use=1):
            opts = json.loads(det.options)
            opts['label']  = det.name
            opts['prefix'] = det.pvname
            opts['kind']   = det.kind
            opts['notes']  = det.notes
            scan['detectors'].append(opts)
                
        for ct in sdb.select('scancounters', use=1):
            scan['counters'].append((ct.name, ct.pvname))

        for ep in sdb.select('extrapvs', use=1):
            scan['extra_pvs'].append((ep.name, ep.pvname))
            
        sdb.add_scandef(scanname,  json.dumps(scan))
        return scanname

    def onStartScan(self, evt=None):
        scanname = self.generate_scan()
        fname = self.filename.GetValue()
        self.scandb.add_command('doscan', arguments=scanname,
                                output_file=fname)

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
        add_menu(self, fmenu,"&Save Scan Definition\tCtrl+S",
                  "Save Scan Definition", self.onSaveScanDef)

        add_menu(self, fmenu, "&Read Scan Definition\tCtrl+O",
                 "Read Scan Defintion",  self.onReadScanDef)

        fmenu.AppendSeparator()

        add_menu(self, fmenu,'Change &Working Folder\tCtrl+W',
                  "Choose working directory",  self.onFolderSelect)
        fmenu.AppendSeparator()
        add_menu(self, fmenu, "&Quit\tCtrl+Q",
        "Quit program", self.onClose)

        # options
        pmenu = wx.Menu()
        
        add_menu(self, pmenu, "Positioners\tCtrl+P",
                 "Setup Motors and Positioners", self.onEditPositioners)
        add_menu(self, pmenu, "Detectors\tCtrl+D",
                 "Setup Detectors and Counters", self.onEditDetectors)
        add_menu(self, pmenu, "Extra PVs",
                 "Setup Extra PVs to save with scan", self.onEditExtraPVs)
        
        add_menu(self, pmenu, "Scan Definitions",
                 "Manage Saved Scans", self.onEditScans)
        
           
        fmenu.AppendSeparator()
        add_menu(self, pmenu, "Settings",
                 "General Setup", self.onEditSettings)

        # Sequences
        smenu = wx.Menu()
        add_menu(self, smenu, "Sequences",
                  "Run Sequences of Scans",  self.onEditSequences)
        add_menu(self, smenu, "Macros",
                  "Edit Macros",  self.onEditMacros)

        # help
        hmenu = wx.Menu()
        add_menu(self, hmenu, "&About",
                  "More information about this program",  self.onAbout)

        self.menubar.Append(fmenu, "&File")
        self.menubar.Append(pmenu, "&Setup")
        self.menubar.Append(smenu, "Sequences")
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
            for child in self.subframes.values():
                try:
                    child.Destroy()
                except:
                    pass
            self.Destroy()

    def show_subframe(self, name, frameclass):
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except:
                del self.subframes[name]
        if not shown:
            self.subframes[name] = frameclass(self)

        
    def onEditPositioners(self, evt=None):
        self.show_subframe('pos', PositionerFrame)        

    def onEditExtraPVs(self, evt=None):
        self.show_subframe('pvs', ExtraPVsFrame)        

    def onEditDetectors(self, evt=None):
        self.show_subframe('det', DetectorFrame)                

    def onEditScans(self, evt=None):
        self.show_subframe('scan', ScandefsFrame)

    def onEditSettings(self, evt=None):
        self.show_subframe('settings', SettingsFrame)
        
    def onEditSequences(self, evt=None):
        self.show_subframe('sequences', SequencesFrame)        

    def onEditMacros(self, evt=None):
        self.show_subframe('macros', MacrosFrame)        

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
            self.scandb.set_info('user_folder', basedir)
        dlg.Destroy()

    def onSaveScanDef(self, evt=None):
        dlg = wx.TextEntryDialog(self, "Scan Name:",
                                 "Enter Name for this Scan", "")
        sname = ''
        dlg.SetValue(sname)
        if dlg.ShowModal() == wx.ID_OK:
            sname =  dlg.GetValue()
        dlg.Destroy()
        if sname is not None:
            scannames = [s.name for s in self.scandb.select('scandefs')]
            name_exists = sname in scannames
            if name_exists:
                erase_ok = True
                if self.scandb.get_info('scandefs_verify_overwrite', as_bool=True):
                    erase_ok = popup(self,
                                     "Overwrite Scan Definition '%s'?" % sname,
                                     "Overwrite Scan Definition?",
                                     style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
                if erase_ok:
                    self.scandb.del_scandef(sname)
                    name_exists = False
            if not name_exists and len(sname) > 0:
                self.generate_scan(scanname=sname)
                self.statusbar.SetStatusText("Saved scan '%s'" % sname)
            else:
                self.statusbar.SetStatusText("Could not overwrite scan '%s'" % sname)
            
    def onReadScanDef(self, evt=None):
        if self.scandb.get_info('scandefs_load_showall', as_bool=True):
            scannames = [s.name for s in self.scandb.select('scandefs')]
        else:
            scannames = [s.name for s in self.scandb.select('scandefs') 
                         if not s.name.startswith('__')]
            
        dlg = wx.SingleChoiceDialog(self, "Select Saved Scan:",
                                    "", scannames)
        sname = None
        if dlg.ShowModal() == wx.ID_OK:
            sname =  dlg.GetStringSelection()
        dlg.Destroy()

        if sname is not None:
            self.statusbar.SetStatusText("Read Scan '%s'" % sname)
            thisscan = json.loads(self.scandb.get_scandef(sname).text)
            self.load_scandef( thisscan)
            
    def load_scandef(self, scan):
        """load scan definition from dictionary, as stored
        in scandb scandef.text field
        """
        sdb = self.scandb
        sdb.set_info('det_settle_time', scan['det_settle_time'])
        sdb.set_info('pos_settle_time', scan['pos_settle_time'])

        ep = [x.pvname for x in sdb.select('extrapvs')]
        for name, pvname in scan['extra_pvs']:
            if pvname not in ep:
                self.scandb.add_extrapv(name, pvname)

        for detdat  in scan['detectors']:
            det = sdb.get_detector(detdat['label'])
            if det is None:
                name   = detdat.pop('label')
                prefix = detdat.pop('prefix')
                dkind  = detdat.pop('kind')
                use    = detdat.pop('use')
                opts   = json.dumps(detdat) 
                sdb.add_detector(name, prefix,
                                 kind=dkind,
                                 options=opts,
                                 use=use)
            else:
                det.prefix = detdat.pop('prefix')
                det.dkind  = detdat.pop('kind')
                det.use    = detdat.pop('use')
                det.options = json.dumps(detdat) 

        if 'positioners' in scan:
            for data in scan['positioners']:
                name = data[0]
                pos = self.scandb.get_positioner(name)
                name = data[0]
                drivepv, readpv = data[1]
                if pos is None:
                    sdb.add_positioner(name, drivepv,
                                       readpv=readpv)
                else:
                    pos.drivepv = drivepv
                    pos.readpv = readpv
                    
        # now fill in page
        stype = scan['type'].lower()
        if stype in self.scanpanels:
            inb, span = self.scanpanels[stype]
            self.nb.SetSelection(inb)
            span.load_scandict(scan)


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
