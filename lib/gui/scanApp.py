#!/usr/bin/env python
"""
Main GUI form for setting up and executing Step Scans

Principle features:
   1. overall configuration in database (postgres/sqlite for testing)
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

from .gui_utils import (SimpleText, FloatCtrl, Closure, pack, add_button,
                        add_menu, add_choice, add_menu, CEN, LCEN, FRAMESTYLE)

from ..utils import normalize_pvname
from ..stepscan import StepScan
from ..xafs_scan import XAFS_Scan

from ..file_utils import new_filename, increment_filename, nativepath

from ..scandb import ScanDB

from .scan_panels import (LinearScanPanel, MeshScanPanel,
                          SlewScanPanel,   XAFSScanPanel)

from ..positioner import Positioner
from ..detectors import (SimpleDetector, ScalerDetector, McaDetector,
                         MultiMcaDetector, AreaDetector, get_detector)

from .liveviewerApp    import ScanViewerFrame
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
    def __init__(self, dbname='Test.db', server='sqlite', host=None,
                 user=None, password=None, port=None, create=True,  **kws):

        wx.Frame.__init__(self, None, -1, style=FRAMESTYLE, **kws)

        self.pvlist = {}
        self.subframes = {}
        self._larch = None
        self.epics_status = 0
        self.larch_status = 0
        self.last_scanname = ''

        self.scandb = ScanDB(dbname=dbname, server=server, host=host,
                 user=user, password=password, port=port, create=create)

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

        self.inittimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onInitTimer, self.inittimer)
        self.inittimer.Start(100)

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

        self.filename = wx.TextCtrl(bpanel, -1,
                                    self.scandb.get_info('filename', default=''))
        self.filename.SetMinSize((400, 25))

        self.user_comms = wx.TextCtrl(bpanel, -1, "", style=wx.TE_MULTILINE)
        self.user_comms.SetMinSize((400, 75))

        self.msg1  = SimpleText(bpanel, "    ", size=(200, -1))
        self.msg2  = SimpleText(bpanel, "    ", size=(200, -1))
        self.msg3  = SimpleText(bpanel, "    ", size=(200, -1))


        bsizer.Add(SimpleText(bpanel, "Number of Scans:"), (0, 0), (1, 1), LCEN)
        bsizer.Add(SimpleText(bpanel, "File Name:"),       (1, 0), (1, 1), LCEN)
        bsizer.Add(SimpleText(bpanel, "Comments:"),        (2, 0), (1, 1), LCEN)
        bsizer.Add(self.nscans,     (0, 1), (1, 1), LCEN, 2)
        bsizer.Add(self.filename,   (1, 1), (1, 2), LCEN, 2)
        bsizer.Add(self.user_comms, (2, 1), (1, 2), LCEN, 2)
        bsizer.Add(self.msg1,       (0, 4), (1, 1), LCEN, 2)
        bsizer.Add(self.msg2,       (1, 4), (1, 1), LCEN, 2)
        bsizer.Add(self.msg3,       (2, 4), (1, 1), LCEN, 2)

        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btnpanel = wx.Panel(bpanel)
        for ibtn, label in enumerate(("Start", "Pause", "Resume", "Abort")):
            btn = add_button(btnpanel, label, size=(120, -1),
                             action=Closure(self.onCtrlScan, cmd=label))
            btnsizer.Add(btn, 0, CEN, 8)
        pack(btnpanel, btnsizer)

        ir = 3
        bsizer.Add(btnpanel,  (3, 0), (1, 4), LCEN, 5)

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
            wx.CallAfter(self.onShowPlot)
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
        for pv in self.scandb.getall('pvs'):
            name = normalize_pvname(pv.name)
            self.pvlist[name] = epics.PV(name)
        self.epics_status = 1
        time.sleep(0.05)
        self.statusbar.SetStatusText('Epics Ready')

    def generate_scan(self, scanname=None):
        """generate scan definition from current values on GUI"""
        if scanname is None:
            scanname = time.strftime("__%b%d_%H:%M:%S__")

        scan = self.nb.GetCurrentPage().generate_scan()
        scan['nscans'] = int(self.nscans.GetValue())

        sdb = self.scandb
        fname = self.filename.GetValue()
        scan['filename'] = fname
        scan['user_comments'] = self.user_comms.GetValue()

        scan['pos_settle_time'] = float(sdb.get_info('pos_settle_time', default=0.))
        scan['det_settle_time'] = float(sdb.get_info('det_settle_time', default=0.))

        scan['detectors'] = []
        scan['counters']  = []
        if 'extra_pvs' not in scan:
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

        sdb.add_scandef(scanname,  text=json.dumps(scan),
                        type=scan['type'])
        return scanname

    def onStartScan(self, evt=None):
        scanname = self.generate_scan()
        fname = self.filename.GetValue()
        self.scandb.add_command('doscan', arguments=scanname,
                                output_file=fname)


    def onCtrlScan(self, evt=None, cmd=''):
        cmd = cmd.lower()
        if cmd == 'start':
            self.onStartScan()
        elif cmd == 'abort':
            self.scandb.set_info('request_command_abort', 1)
        elif cmd == 'pause':
            self.scandb.set_info('request_command_pause', 1)
        elif cmd == 'resume':
            self.scandb.set_info('request_command_pause', 0)

    def createMenus(self):
        self.menubar = wx.MenuBar()
        # file
        fmenu = wx.Menu()
        add_menu(self, fmenu, "Load Scan Definition\tCtrl+O",
                 "Load Scan Defintion",  self.onReadScanDef)

        add_menu(self, fmenu, "Save Scan Definition\tCtrl+S",
                 "Save Scan Definition", self.onSaveScanDef)

        fmenu.AppendSeparator()

        add_menu(self, fmenu,'Change &Working Folder\tCtrl+W',
                 "Choose working directory",  self.onFolderSelect)
        add_menu(self, fmenu,'Show Plot Window',
                 "Show Window for Plotting Scan", self.onShowPlot)

        fmenu.AppendSeparator()
        add_menu(self, fmenu, "Quit\tCtrl+Q",
        "Quit program", self.onClose)

        # options
        pmenu = wx.Menu()

        add_menu(self, pmenu, "Positioners\tCtrl+P",
                 "Setup Motors and Positioners", self.onEditPositioners)
        add_menu(self, pmenu, "Detectors\tCtrl+D",
                 "Setup Detectors and Counters", self.onEditDetectors)
        pmenu.AppendSeparator()

        add_menu(self, pmenu, "Extra PVs",
                 "Setup Extra PVs to save with scan", self.onEditExtraPVs)

        add_menu(self, pmenu, "Scan Definitions",
                 "Manage Saved Scans", self.onEditScans)

        pmenu.AppendSeparator()
        add_menu(self, pmenu, "General Settings",
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

    def onShowPlot(self, evt=None):
        self.show_subframe('plot', ScanViewerFrame)

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
        dlg.SetValue(self.last_scanname)
        if dlg.ShowModal() == wx.ID_OK:
            sname =  dlg.GetValue()
        dlg.Destroy()
        if sname is not None:
            scannames = [s.name for s in self.scandb.select('scandefs')]
            if sname in scannames:
                _ok = wx.ID_NO
                if self.scandb.get_info('scandefs_verify_overwrite',
                                        as_bool=True, default=1):
                    _ok =  popup(self,
                                 "Overwrite Scan Definition '%s'?" % sname,
                                 "Overwrite Scan Definition?",
                                 style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)

                if (_ok == wx.ID_YES):
                    self.scandb.del_scandef(sname)
                else:
                    sname = ''
            if len(sname) > 0:
                self.generate_scan(scanname=sname)
                self.statusbar.SetStatusText("Saved scan '%s'" % sname)
            else:
                self.statusbar.SetStatusText("Could not overwrite scan '%s'" % sname)

        if len(sname) > 0:
            self.last_scanname = sname

    def onReadScanDef(self, evt=None):
        _autotypes = self.scandb.get_info('scandefs_load_showauto',
                                          as_bool=True, default=0)
        _alltypes  = self.scandb.get_info('scandefs_load_showalltypes',
                                          as_bool=True, default=0)
        stype = None
        if not _alltypes:
            inb =  self.nb.GetSelection()
            for key, val in self.scanpanels.items():
                if val[0] == inb:
                    stype = key

        snames = []
        for sdef in self.scandb.getall('scandefs', orderby='last_used_time'):
            if ((_alltypes or stype == sdef.type) and
                (_autotypes or not sdef.name.startswith('__'))):
                snames.append(sdef.name)

        snames.reverse()
        dlg = wx.SingleChoiceDialog(self, "Select Saved Scan:", "", snames)

        sname = None
        if dlg.ShowModal() == wx.ID_OK:
            sname =  dlg.GetStringSelection()
        dlg.Destroy()

        if sname is not None:
            self.statusbar.SetStatusText("Read Scan '%s'" % sname)
            thisscan = json.loads(self.scandb.get_scandef(sname).text)
            self.load_scandef( thisscan)
            self.last_scanname = sname

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

        for detdat in scan['detectors']:
            det = sdb.get_detector(detdat['label'])
            if det is None:
                name   = detdat.pop('label')
                prefix = detdat.pop('prefix')
                dkind  = detdat.pop('kind')
                use = True
                if 'use' in detdat:
                    use = detdat.pop('use')
                opts   = json.dumps(detdat)
                sdb.add_detector(name, prefix,
                                 kind=dkind,
                                 options=opts,
                                 use=use)
            else:
                det.prefix = detdat.pop('prefix')
                det.dkind  = detdat.pop('kind')
                det.use = True
                if 'use' in detdat:
                    det.use  = detdat.pop('use')
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
    def __init__(self, dbname='TestScan.db', server='sqlite', host=None,
                 port=None, user=None, password=None, create=True, **kws):

        self.scan_opts = dict(dbname=dbname, server=server, host=host,
                              port=port, create=create, user=user,
                              password=password)
        self.scan_opts.update(kws)
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        frame = ScanFrame(**self.scan_opts)
        frame.Show()
        self.SetTopWindow(frame)
        return True
