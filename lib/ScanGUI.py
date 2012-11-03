#!/usr/bin/env python
"""
Main GUI form for setting up and executing Step Scans

Principle features:
   1.  Overall Configuration file in home directory
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

"""
import os
import time
import shutil

from datetime import timedelta

import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection

import epics
from epics.wx import DelayedEpicsCallback, EpicsFunction

from larch import Interpreter

from gui_utils import SimpleText, FloatCtrl, Closure
from gui_utils import pack, add_button, add_menu, add_choice, add_menu

# from config import FastMapConfig, conf_files, default_conf
# from mapper import mapper

from file_utils import new_filename, increment_filename, nativepath
from scan_config import ScanConfig

from gui_panels import (LinearScanPanel, MeshScanPanel,
                        SlewScanPanel,   XAFSScanPanel)
MAX_POINTS = 4000
ALL_CEN =  wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL
FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS


class ScanFrame(wx.Frame):
    _about = """StepScan GUI
  Matt Newville <newville @ cars.uchicago.edu>
  """
    _cnf_wildcard = "Scan Definition Files(*.ini)|*.ini|All files (*.*)|*.*"

    def __init__(self, configfile='defconf.ini',  **kwds):

        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, None, -1, **kwds)
        self.larch = Interpreter()

        self.Font16=wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font14=wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font12=wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font11=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font10=wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        self.SetTitle("Epics Scans")
        self.SetSize((700, 575))
        self.SetFont(self.Font11)

        self.config = ScanConfig(configfile)
        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ["Messages", "Status"]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

    def createMainPanel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.nb = flat_nb.FlatNotebook(self, wx.ID_ANY, agwStyle=FNB_STYLE)
        self.nb.SetBackgroundColour('#FCFCFA')
        self.SetBackgroundColour('#F0F0E8')

        self.scan_choices = []
        for name, creator in (('Linear Step Scan', LinearScanPanel),
                           ('2-D Mesh Scan',    MeshScanPanel),
                           ('Slew Scan',        SlewScanPanel),
                           ('XAFS Scan',        XAFSScanPanel)):
            panel = creator(self, config=self.config, larch=self.larch)
            self.nb.AddPage(panel, name, True)

        self.nb.SetSelection(0)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)
        sizer.Add(wx.StaticLine(self, size=(675, 3),
                                style=wx.LI_HORIZONTAL), 0, wx.EXPAND)

        # bottom panel
        bpanel = wx.Panel(self)
        bsizer = wx.GridBagSizer(3, 5)

        self.nscans = FloatCtrl(bpanel, precision=0, value=1, minval=0, size=(45, -1))

        self.filename = wx.TextCtrl(bpanel, -1, self.config.setup['filename'])
        self.filename.SetMinSize((400, 25))

        self.usertitles = wx.TextCtrl(bpanel, -1, "", style=wx.TE_MULTILINE)
        self.usertitles.SetMinSize((400, 75))

        self.msg1  = SimpleText(bpanel, "<message1>", size=(200, -1))
        self.msg2  = SimpleText(bpanel, "<message2>", size=(200, -1))
        self.msg3  = SimpleText(bpanel, "<message3>", size=(200, -1))
        self.start_btn = add_button(bpanel, "Start Scan", action=self.onStartScan)
        self.abort_btn = add_button(bpanel, "Abort Scan", action=self.onAbortScan)
        self.abort_btn.Disable()

        sty = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        bsizer.Add(SimpleText(bpanel, "Number of Scans:"), (0, 0), (1, 1), sty)
        bsizer.Add(SimpleText(bpanel, "File Name:"),       (1, 0), (1, 1), sty)
        bsizer.Add(SimpleText(bpanel, "Comments:"),        (2, 0), (1, 1), sty)
        bsizer.Add(self.nscans,     (0, 1), (1, 1), sty, 2)
        bsizer.Add(self.filename,   (1, 1), (1, 2), sty, 2)
        bsizer.Add(self.usertitles, (2, 1), (1, 2), sty, 2)
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

    def onStartScan(self, evt=None):
        panel = self.nb.GetCurrentPage()
        panel.generate_scan()

    def onAbortScan(self, evt=None):
        print 'Abort Scan ', evt


    def createMenus(self):
        self.menubar = wx.MenuBar()
        # file
        fmenu = wx.Menu()
        add_menu(self, fmenu, "&Read Scan Definition File",
                  "Read Scan Defintion File",
                  self.onReadConfigFile)

        add_menu(self, fmenu,"&Save Scan Definition File",
                  "Save Scan Definition File", self.onSaveScanFile)

        fmenu.AppendSeparator()
        add_menu(self, fmenu,'Change &Working Folder',
                  "Choose working directory",
                  self.onFolderSelect)
        fmenu.AppendSeparator()
        add_menu(self,fmenu, "E&xit",
                  "Quit program", self.onClose)

        # options
        pmenu = wx.Menu()
        add_menu(self, pmenu, "Setup &Motors and Positioners",
                  "Setup Motors and Positioners", self.onSetupPositioners)
        dmenu = wx.Menu()
        add_menu(self, dmenu, "Setup &Detectors and Counters",
                  "Setup Detectors and Counters", self.onSetupDetectors)
        # help
        hmenu = wx.Menu()
        add_menu(self, hmenu, "&About",
                  "More information about this program",  self.onAbout)

        self.menubar.Append(fmenu, "&File")
        self.menubar.Append(pmenu, "&Positioners")
        self.menubar.Append(dmenu, "&Detectors")
        self.menubar.Append(hmenu, "&Help")
        self.SetMenuBar(self.menubar)

    def onAbout(self,evt):
        dlg = wx.MessageDialog(self, self._about,"About Me",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,evt):
        self.Destroy()

    def onSetupPositioners(self, evt=None):
        print 'Setup Positioners'

    def onSetupDetectors(self, evt=None):
        print 'Setup Detectors'

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

    def onSaveScanFile(self,evt=None):
        self.onSaveConfigFile(evt=evt,scan_only=True)

    def onSaveConfigFile(self,evt=None,scan_only=False):
        fout=self.configfile
        if fout is None:
            fout = 'config.ini'
        dlg = wx.FileDialog(self,
                            message="Save Scan Definition File",
                            defaultDir=os.getcwd(),
                            defaultFile=fout,
                            wildcard=self._cnf_wildcard,
                            style=wx.SAVE|wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.SaveConfigFile(path,scan_only=scan_only)
        dlg.Destroy()

    def onReadConfigFile(self,evt=None):
        fname = self.configfile
        if fname is None: fname = ''
        dlg = wx.FileDialog(self, message="Read Scan Definition File",
                            defaultDir=os.getcwd(),
                            defaultFile='',  wildcard=self._cnf_wildcard,
                            style=wx.OPEN | wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            self.ReadConfigFile(paths[0])
        dlg.Destroy()


        os.chdir(nativepath(self.mapper.basedir))
        self.SetMotorLimits()


    @DelayedEpicsCallback
    def onMapRow(self,pvname=None,value=0,**kw):
        " the map row changed -- another row is finished"
        rowtime  = 0.5 + self.t_rowtime
        nrows    = float(self.m2npts.GetLabel().strip())
        time_left = int(0.5+ rowtime * max(0, nrows - value))
        message = "Estimated Time remaining: %s" % timedelta(seconds=time_left)
        self.statusbar.SetStatusText(message, 0)

    @DelayedEpicsCallback
    def onMapInfo(self,pvname=None,char_value=None,**kw):
        self.statusbar.SetStatusText(char_value,1)

    @DelayedEpicsCallback
    def onMapMessage(self,pvname=None,char_value=None,**kw):
        self.statusbar.SetStatusText(char_value,0)

    @DelayedEpicsCallback
    def onMapStart(self,pvname=None,value=None,**kw):
        if value == 0: # stop of map
            self.startbutton.Enable()
            self.abortbutton.Disable()

            self.usertitles.Enable()
            self.filename.Enable()

            fname = str(self.filename.GetValue())
            if os.path.exists(fname):
                self.filename.SetValue(increment_filename(fname))

            fname = str(self.filename.GetValue())

            nfile = new_filename(os.path.abspath(fname))
            self.filename.SetValue(os.path.split(nfile)[1])
        else: # start of map
            self.startbutton.Disable()
            self.abortbutton.Enable()

    @DelayedEpicsCallback
    def onMapAbort(self,pvname=None,value=None,**kw):
        if value == 0:
            self.abortbutton.Enable()
            self.startbutton.Disable()
        else:
            self.abortbutton.Disable()
            self.startbutton.Enable()

    def epics_CtrlVars(self,posname):
        posname = str(posname)
        ctrlvars = {'lower_ctrl_limit':-0.001,
                    'upper_ctrl_limit':0.001,
                    'units': 'mm'}

        if posname not in self._pvs:
            labels = self.config['slow_positioners'].values()
            if posname in labels:
                keys   = self.config['slow_positioners'].keys()
                pvname = keys[labels.index(posname)]
                self._pvs[posname] = epics.PV(pvname)

        if (posname in self._pvs and
            self._pvs[posname] is not None and
            self._pvs[posname].connected):
            self._pvs[posname].get() # make sure PV is connected
            c  = self._pvs[posname].get_ctrlvars()
            if c is not None: ctrlvars = c
        return ctrlvars

    @EpicsFunction
    def SetMotorLimits(self):
        m1name = self.m1choice.GetStringSelection()
        m1 = self._pvs[m1name]
        if m1.lower_ctrl_limit is None:
            m1.get_ctrlvars()
        xmin,xmax =  m1.lower_ctrl_limit, m1.upper_ctrl_limit
        self.m1units.SetLabel(m1.units)
        self.m1step.SetMin(-abs(xmax-xmin))
        self.m1step.SetMax( abs(xmax-xmin))
        self.m1start.SetMin(xmin)
        self.m1start.SetMax(xmax)
        self.m1stop.SetMin(xmin)
        self.m1stop.SetMax(xmax)

        m2name = self.m2choice.GetStringSelection()
        if not self.m2choice.IsEnabled() or len(m2name) < 1:
            return

        m2 = self._pvs[m2name]
        if m2.lower_ctrl_limit is None:
            m2.get_ctrlvars()

        xmin,xmax =  m2.lower_ctrl_limit, m2.upper_ctrl_limit
        self.m2units.SetLabel( m2.units)
        self.m2step.SetMin(-abs(xmax-xmin))
        self.m2step.SetMax( abs(xmax-xmin))
        self.m2start.SetMin(xmin)
        self.m2start.SetMax(xmax)
        self.m2stop.SetMin(xmin)
        self.m2stop.SetMax(xmax)

    def onDimension(self,evt=None):
        cnf = self.config
        dim = self.dimchoice.GetSelection() + 1
        cnf['scan']['dimension'] = dim
        if dim == 1:
            self.m2npts.SetLabel("1")
            self.m2choice.Disable()
            for m in (self.m2start,self.m2units,self.m2stop,self.m2step):
                m.Disable()
        else:
            self.m2choice.Enable()
            for m in (self.m2start,self.m2units,self.m2stop,self.m2step):
                m.Enable()
        self.onM2step()

    def onM1Select(self,evt=None):
        m1name = evt.GetString()
        m2name = self.m2choice.GetStringSelection()

        sm_labels = self.config['slow_positioners'].values()[:]
        sm_labels.remove(m1name)
        if m1name == m2name:
            m2name = sm_labels[0]

        self.m2choice.Clear()
        self.m2choice.AppendItems(sm_labels)
        self.m2choice.SetStringSelection(m2name)
        self.SetMotorLimits()

    def onM2Select(self,evt=None):
        self.SetMotorLimits()

    def onM2step(self, value=None, **kw):
        try:
            s1 = self.m2start.GetValue()
            s2 = self.m2stop.GetValue()
            ds = self.m2step.GetValue()
            npts2 = 1 + int(0.5  + abs(s2-s1)/(max(ds,1.e-10)))
            if npts2 > MAX_POINTS:
                npts2 = MAX_POINTS
            if self.config['scan']['dimension'] == 1:
                npts2 = 1
            self.m2npts.SetLabel("  %i" % npts2)
            maptime = int((self.t_rowtime + 1.25) * max(1, npts2))
            self.maptime.SetLabel("%s" % timedelta(seconds=maptime))
        except AttributeError:
            pass

    def calcRowTime(self, value=None, **kw):
        try:
            s1 = self.m1start.GetValue()
            s2 = self.m1stop.GetValue()
            ds = self.m1step.GetValue()
            pixt = self.pixtime.GetValue()
            npts = 1 + int(0.5  + abs(s2-s1)/(max(ds,1.e-10)))
            if npts > MAX_POINTS:
                npts = MAX_POINTS
            self.m1npts.SetLabel("  %i" % npts)
            self.t_rowtime = pixt * max(1, npts-1)
            self.rowtime.SetLabel("%.1f" % (self.t_rowtime))

            npts2 = float(self.m2npts.GetLabel().strip())
            maptime = int((self.t_rowtime + 1.25) * max(1, npts2))
            self.maptime.SetLabel("%s" % timedelta(seconds=maptime))

        except AttributeError:
            pass

    @EpicsFunction
    def xonStartScan(self, evt=None):
        fname = str(self.filename.GetValue())
        if os.path.exists(fname):
            fname = increment_filename(fname)
            self.filename.SetValue(fname)

        sname = 'CurrentScan.ini'
        if os.path.exists(sname):
            shutil.copy(sname, 'PreviousScan.ini')

        self.SaveConfigFile(sname, scan_only=True)
        self.mapper.StartScan(fname, sname)

        # setup escan saver
        self.data_mode   = 'w'
        self.data_fname  = os.path.abspath(os.path.join(
            nativepath(self.mapper.basedir), self.mapper.filename))

        self.usertitles.Disable()
        self.filename.Disable()
        self.abortbutton.Enable()
        self.start_time = time.time()

    @EpicsFunction
    def xonAbortScan(self,evt=None):
        self.mapper.AbortScan()

class ScanApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, config=None, dbname=None, **kws):
        self.config  = config
        self.dbname  = dbname
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        frame = ScanFrame() # conf=self.conf, dbname=self.dbname)
        frame.Show()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    ScanApp().MainLoop()
