#!/usr/bin/env python
"""
"""
import os
import time
import shutil
import numpy as np
from random import randrange
from functools import partial
from datetime import timedelta

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection

HAS_EPICS = False
try:
    import epics
    from epics.wx import DelayedEpicsCallback, EpicsFunction
    HAS_EPICS = True
except ImportError:
    pass

import larch
from ..larchlib import read_workdir, save_workdir

from ..io  import (gsescan_deadtime_correct, gsexdi_deadtime_correct,
                   is_GSEXDI, AthenaProject, new_filename, increment_filename)

from wxutils import (SimpleText, FloatCtrl, pack, Button, Popup,
                     Choice,  Check, MenuItem, GUIColors,
                     CEN, LEFT, FRAMESTYLE, Font)

CEN |=  wx.ALL
FILE_WILDCARDS = "Scan Data Files(*.0*,*.1*,*.dat,*.xdi)|*.0*;*.1*;*.dat;*.xdi|All files (*)|*"


def okcancel(panel, onOK=None, onCancel=None):
    btnsizer = wx.StdDialogButtonSizer()
    _ok = wx.Button(panel, wx.ID_OK)
    _no = wx.Button(panel, wx.ID_CANCEL)
    panel.Bind(wx.EVT_BUTTON, onOK,     _ok)
    panel.Bind(wx.EVT_BUTTON, onCancel, _no)
    _ok.SetDefault()
    btnsizer.AddButton(_ok)
    btnsizer.AddButton(_no)
    btnsizer.Realize()
    return btnsizer

class DTCorrectFrame(wx.Frame):
    _about = """GSECARS Deadtime Corrections
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, _larch=None, **kws):

        wx.Frame.__init__(self, None, -1, style=FRAMESTYLE)
        self.file_groups = {}
        self.file_paths  = []
        title = "DeadTime Correction "
        self.larch = _larch
        self.subframes = {}

        self.SetSize((500, 275))
        self.SetFont(Font(10))

        self.config = {'chdir_on_fileopen': True}
        self.SetTitle(title)
        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ["Initializing....", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

    def onBrowse(self, event=None):
        dlg = wx.FileDialog(parent=self,
                        message='Select Files',
                        defaultDir=os.getcwd(),
                        wildcard =FILE_WILDCARDS,
                        style=wx.FD_OPEN|wx.FD_MULTIPLE|wx.FD_CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            mdir, p = os.path.split(path)
            os.chdir(mdir)
            roiname = self.wid_roi.GetValue().strip()
            if len(roiname) < 1:
                Popup(self,
                    'Must give ROI name!', 'No ROI name')
                return
            dirname = self.wid_dir.GetValue().strip()
            if len(dirname) > 1 and not os.path.exists(dirname):
                try:
                    os.mkdir(dirname)
                except:
                    Popup(self,
                        'Could not create directory %s' % dirname,
                        "could not create directory")
                    return
            badchans = self.wid_bad.GetValue().strip()
            bad_channels = []
            if len(badchans)  > 0:
                bad_channels = [int(i.strip()) for i in badchans.split(',')]

            groups = []
            for fname in dlg.GetFilenames():
                corr_fcn = gsescan_deadtime_correct
                if is_GSEXDI(fname):
                    corr_fcn = gsexdi_deadtime_correct
                self.write_message("Correcting %s" % (fname))
                out = corr_fcn(fname, roiname, subdir=dirname,
                               bad=bad_channels, _larch=self.larch)
                if out is not None:
                    out.mu = out.mufluor
                    out.filename = fname
                    groups.append((out, fname))

            athena_name = os.path.join(dirname, self.wid_ath.GetValue().strip())
            if self.wid_autoname.IsChecked():
                athena_name = new_filename(athena_name)

            _, aname = os.path.split(athena_name)
            self.wid_ath.SetValue(increment_filename(aname))

            aprj = AthenaProject(filename=athena_name, _larch=self.larch)
            for grp, label in groups:
                aprj.add_group(grp, signal='mu')
            aprj.save(use_gzip=True)
            self.write_message("Corrected %i files, wrote %s" % (len(groups), aname))

    def createMainPanel(self):
        panel = wx.Panel(self)
        sizer = wx.GridBagSizer(5, 4)

        lab_roi = SimpleText(panel, ' Element / ROI Name:')
        lab_dir = SimpleText(panel, ' Output Folder:')
        lab_ath = SimpleText(panel, ' Athena Project File:')
        lab_bad = SimpleText(panel, ' Bad Channels:')
        lab_sel = SimpleText(panel, ' Select Files:')

        self.wid_roi = wx.TextCtrl(panel, -1, '', size=(200, -1))
        self.wid_dir = wx.TextCtrl(panel, -1, 'DT_Corrected', size=(200, -1))
        self.wid_ath = wx.TextCtrl(panel, -1, 'Athena_001.prj', size=(200, -1))
        self.wid_bad = wx.TextCtrl(panel, -1, ' ', size=(200, -1))
        self.wid_autoname = Check(panel, default=True,
                                  size=(150, -1), label='auto-increment?')

        self.sel_wid = Button(panel, 'Browse', size=(100, -1),
                                action=self.onBrowse)

        ir = 0
        sizer.Add(lab_roi,       (ir, 0), (1, 1), LEFT, 2)
        sizer.Add(self.wid_roi, (ir, 1), (1, 1), LEFT, 2)
        ir += 1
        sizer.Add(lab_dir,       (ir, 0), (1, 1), LEFT, 2)
        sizer.Add(self.wid_dir,  (ir, 1), (1, 1), LEFT, 2)
        ir += 1
        sizer.Add(lab_ath,       (ir, 0), (1, 1), LEFT, 2)
        sizer.Add(self.wid_ath,  (ir, 1), (1, 1), LEFT, 2)
        sizer.Add(self.wid_autoname,  (ir, 2), (1, 1), LEFT, 2)

        ir += 1
        sizer.Add(lab_bad,            (ir, 0), (1, 1), LEFT, 2)
        sizer.Add(self.wid_bad,  (ir, 1), (1, 1), LEFT, 2)
        ir += 1
        sizer.Add(lab_sel,       (ir, 0), (1, 1), LEFT, 2)
        sizer.Add(self.sel_wid,  (ir, 1), (1, 1), LEFT, 2)

        pack(panel, sizer)
        wx.CallAfter(self.init_larch)
        return

    def init_larch(self):
        t0 = time.time()
        if self.larch is None:
            self.larch = larch.Interpreter()
        self.larch.symtable.set_symbol('_sys.wx.wxapp', wx.GetApp())
        self.larch.symtable.set_symbol('_sys.wx.parent', self)
        self.SetStatusText('ready')

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def createMenus(self):
        # ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)
        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)

    def onClose(self,evt):
        self.Destroy()


class DTViewer(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, _larch=None, **kws):
        self._larch = _larch
        wx.App.__init__(self, **kws)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = DTCorrectFrame(_larch=self._larch)
        frame.Show()
        self.SetTopWindow(frame)

    def OnInit(self):
        self.createApp()
        return True

def dtcorrect(wxparent=None, _larch=None,  **kws):
    s = DTCorrectFrame(_larch=_larch, **kws)
    s.Show()
    s.Raise()
