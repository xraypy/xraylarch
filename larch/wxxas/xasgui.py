#!/usr/bin/env python
"""
XANES Data Viewer and Analysis Tool
"""
import os
import sys
import time
import copy
import platform
from threading import Thread
import numpy as np
np.seterr(all='ignore')

from functools import partial

import wx
import wx.lib.scrolledpanel as scrolled

from wx.adv import AboutBox, AboutDialogInfo

from wx.richtext import RichTextCtrl

WX_DEBUG = True

import larch
from larch import Group, Journal, Entry
from larch.io import save_session, read_session
from larch.math import index_of
from larch.utils import isotime, time_ago, get_cwd, is_gzip, uname
from larch.utils.strutils import (file2groupname, unique_name,
                                  common_startstring, asfloat)

from larch.larchlib import read_workdir, save_workdir, read_config, save_config

from larch.wxlib import (LarchFrame, ColumnDataFileFrame, AthenaImporter,
                         SpecfileImporter, FileCheckList, FloatCtrl,
                         FloatSpin, SetTip, get_icon, SimpleText, TextCtrl,
                         pack, Button, Popup, HLine, FileSave, FileOpen,
                         Choice, Check, MenuItem, HyperText, set_color, COLORS,
                         CEN, LEFT, FRAMESTYLE, Font, FONTSIZE,
                         flatnotebook, LarchUpdaterDialog, GridPanel,
                         CIFFrame, Structure2FeffFrame, FeffResultsFrame, LarchWxApp, OkCancel,
                         ExceptionPopup, set_color)


from larch.wxlib.plotter import get_display

from larch.fitting import fit_report
from larch.site_config import icondir, home_dir, user_larchdir
from larch.version import check_larchversion

from .prepeak_panel import PrePeakPanel
from .xasnorm_panel import XASNormPanel
from .lincombo_panel import LinearComboPanel
from .pca_panel import PCAPanel
from .exafs_panel import EXAFSPanel
from .feffit_panel import FeffitPanel
from .regress_panel import RegressionPanel
from .xas_controller import XASController
from .taskpanel import GroupJournalFrame
from .config import FULLCONF, CONF_SECTIONS,  CVar, ATHENA_CLAMPNAMES

from .xas_dialogs import (MergeDialog, RenameDialog, RemoveDialog,
                          DeglitchDialog, ExportCSVDialog, RebinDataDialog,
                          EnergyCalibrateDialog, SmoothDataDialog,
                          OverAbsorptionDialog, DeconvolutionDialog,
                          SpectraCalcDialog,  QuitDialog, LoadSessionDialog,
                          fit_dialog_window)

from larch.io import (read_ascii, read_xdi, read_gsexdi, gsescan_group,
                      fix_varname, groups2csv, is_athena_project,
                      is_larch_session_file,
                      AthenaProject, make_hashkey, is_specfile, open_specfile)

from larch.xafs import pre_edge, pre_edge_baseline

LEFT = wx.ALIGN_LEFT
CEN |=  wx.ALL
FILE_WILDCARDS = "Data Files|*.0*;*.dat;*.DAT;*.xdi;*.prj;*.sp*c;*.h*5;*.larix|All files (*.*)|*.*"

ICON_FILE = 'onecone.ico'
XASVIEW_SIZE = (1020, 830)
PLOTWIN_SIZE = (550, 550)

NB_PANELS = {'Normalization': XASNormPanel,
             'Pre-edge Peak': PrePeakPanel,
             'PCA':  PCAPanel,
             'Linear Combo': LinearComboPanel,
             'Regression': RegressionPanel,
             'EXAFS':  EXAFSPanel,
             'Feff Fitting': FeffitPanel}

QUIT_MESSAGE = '''Really Quit? You may want to save your project before quitting.
 This is not done automatically!'''

LARIX_TITLE = "Larix (was XAS Viewer): XAS Visualization and Analysis"


def assign_gsescan_groups(group):
    labels = group.array_labels
    labels = []
    for i, name in enumerate(group.pos_desc):
        name = fix_varname(name.lower())
        labels.append(name)
        setattr(group, name, group.pos[i, :])

    for i, name in enumerate(group.sums_names):
        name = fix_varname(name.lower())
        labels.append(name)
        setattr(group, name, group.sums_corr[i, :])

    for i, name in enumerate(group.det_desc):
        name = fix_varname(name.lower())
        labels.append(name)
        setattr(group, name, group.det_corr[i, :])

    group.array_labels = labels


class PreferencesFrame(wx.Frame):
    """ edit preferences"""
    def __init__(self, parent, controller, **kws):
        self.controller = controller
        wx.Frame.__init__(self, None, -1,  'Larix Preferences',
                          style=FRAMESTYLE, size=(700, 725))

        sizer = wx.BoxSizer(wx.VERTICAL)
        tpanel = wx.Panel(self)

        self.title = SimpleText(tpanel, 'Edit Preference and Defaults',
                                size=(500, 25),
                                font=Font(FONTSIZE+1), style=LEFT,
                                colour=COLORS['nb_text'])

        self.save_btn = Button(tpanel, 'Save for Future sessions',
                               size=(200, -1), action=self.onSave)

        self.nb = flatnotebook(tpanel, {})
        self.wids = {}
        conf = self.controller.config

        def text(panel, label, size):
            return SimpleText(panel, label, size=(size, -1), style=LEFT)

        for name, data in FULLCONF.items():
            self.wids[name] = {}

            panel = GridPanel(self.nb, ncols=3, nrows=8, pad=3, itemstyle=LEFT)
            panel.SetFont(Font(FONTSIZE))
            title = CONF_SECTIONS.get(name, name)
            title = SimpleText(panel, f"  {title}",
                               size=(550, -1), font=Font(FONTSIZE+2),
                               colour=COLORS['title'], style=LEFT)

            self.wids[name]['_key_'] = SimpleText(panel, " <name> ",
                                                  size=(150, -1), style=LEFT)
            self.wids[name]['_help_'] = SimpleText(panel, " <click on name for description> ",
                                                   size=(525, 30), style=LEFT)

            panel.Add((5, 5), newrow=True)
            panel.Add(title, dcol=4)
            panel.Add((5, 5), newrow=True)
            panel.Add(self.wids[name]['_key_'])
            panel.Add(self.wids[name]['_help_'],  dcol=3)
            panel.Add((5, 5), newrow=True)
            panel.Add(HLine(panel, (625, 3)), dcol=4)

            panel.Add((5, 5), newrow=True)
            panel.Add(text(panel, 'Name', 150))

            panel.Add(text(panel, 'Value', 250))
            panel.Add(text(panel, 'Factory Default Value', 225))

            for key, cvar in data.items():
                val = conf[name][key]
                cb = partial(self.update_value, section=name, option=key)
                helpcb = partial(self.update_help, section=name, option=key)
                wid = None
                if cvar.dtype == 'choice':
                    wid = Choice(panel, size=(250, -1), choices=cvar.choices, action=cb)
                    if not isinstance(val, str): val = str(val)
                    wid.SetStringSelection(val)
                elif cvar.dtype == 'bool':
                    wid = Choice(panel, size=(250, -1), choices=['True', 'False'], action=cb)
                    wid.SetStringSelection('True' if val else 'False')
                elif cvar.dtype in ('int', 'float'):
                    digits = 2 if cvar.dtype == 'float' else 0
                    wid = FloatSpin(panel, value=val, min_val=cvar.min, max_val=cvar.max,
                                  digits=digits, increment=cvar.step, size=(250, -1), action=cb)
                else:
                    wid = TextCtrl(panel, size=(250, -1), value=val, action=cb)

                label = HyperText(panel, key, action=helpcb, size=(150, -1))
                panel.Add((5, 5), newrow=True)
                panel.Add(label)
                panel.Add(wid)
                panel.Add(text(panel, f'{cvar.value}', 225))
                SetTip(wid, cvar.desc)
                self.wids[name][key] = wid

            panel.pack()
            self.nb.AddPage(panel, name, True)

        self.nb.SetSelection(0)

        sizer.Add(self.title, 0, LEFT, 3)
        sizer.Add(self.save_btn, 0, LEFT, 5)
        sizer.Add((5, 5), 0, LEFT, 5)
        sizer.Add(self.nb, 1, LEFT|wx.EXPAND, 5)
        pack(tpanel, sizer)
        w0, h0 = self.GetSize()
        w1, h1 = self.GetBestSize()
        self.SetSize((max(w0, w1)+25, max(h0, h1)+25))

        self.Show()
        self.Raise()

    def update_help(self, label=None, event=None, section='main', option=None):
        cvar = FULLCONF[section][option]
        self.wids[section]['_key_'].SetLabel("%s : " % option)
        self.wids[section]['_help_'].SetLabel(cvar.desc)

    def update_value(self, event=None, section='main', option=None):
        cvar = FULLCONF[section][option]
        wid = self.wids[section][option]
        value = cvar.value
        if cvar.dtype == 'bool':
            value = wid.GetStringSelection().lower().startswith('t')
        elif cvar.dtype == 'choice':
            value = wid.GetStringSelection()
        elif cvar.dtype == 'int':
            value = int(wid.GetValue())
        elif cvar.dtype == 'float':
            value = float(wid.GetValue())
        else:
            value = wid.GetValue()
        self.controller.config[section][option] = value

    def onSave(self, event=None):
        self.controller.save_config()


class XASFrame(wx.Frame):
    _about = f"""{LARIX_TITLE}
    Matt Newville <newville @ cars.uchicago.edu>
    """
    def __init__(self, parent=None, _larch=None, filename=None,
                 check_version=True, **kws):
        wx.Frame.__init__(self, parent, -1, size=XASVIEW_SIZE, style=FRAMESTYLE)

        if check_version:
            def version_checker():
                self.vinfo = check_larchversion()
            version_thread = Thread(target=version_checker)
            version_thread.start()

        self.last_col_config = {}
        self.last_spec_config = {}
        self.last_session_file = None
        self.last_session_read = None
        self.last_athena_file = None
        self.paths2read = []
        self.current_filename = filename
        title = LARIX_TITLE

        self.larch_buffer = parent
        if not isinstance(parent, LarchFrame):
            self.larch_buffer = LarchFrame(_larch=_larch,
                                           parent=self,
                                           is_standalone=False,
                                           with_raise=False,
                                           exit_on_close=False)

        self.larch = self.larch_buffer.larchshell

        self.controller = XASController(wxparent=self, _larch=self.larch)
        iconfile = os.path.join(icondir, ICON_FILE)
        self.SetIcon(wx.Icon(iconfile, wx.BITMAP_TYPE_ICO))

        self.last_autosave = 0
        self.last_save_message = ('Session has not been saved', '', '')


        self.timers = {'pin': wx.Timer(self),
                       'autosave': wx.Timer(self)}
        self.Bind(wx.EVT_TIMER, self.onPinTimer, self.timers['pin'])
        self.Bind(wx.EVT_TIMER, self.onAutoSaveTimer, self.timers['autosave'])
        self.cursor_dat = {}

        self.subframes = {}
        self.plotframe = None
        self.SetTitle(title)
        self.SetSize(XASVIEW_SIZE)
        self.SetFont(Font(FONTSIZE))
        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, style=wx.STB_DEFAULT_STYLE)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = [" ", "ready"]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)
        self.Show()

        self.Raise()
        self.statusbar.SetStatusText('ready', 1)
        self.timers['autosave'].Start(30_000)

        plotframe = self.controller.get_display(stacked=False)
        xpos, ypos = self.GetPosition()
        xsiz, ysiz = self.GetSize()
        wx.CallAfter(plotframe.SetPosition, (xpos+xsiz+2, ypos))
        if self.current_filename is not None:
            wx.CallAfter(self.onRead, self.current_filename)

        # show_wxsizes(self)
        if check_version:
            version_thread.join()
            if self.vinfo is not None:
                if self.vinfo.update_available:
                    self.statusbar.SetStatusText(f'Larch Version {self.vinfo.remote_version} is available!', 0)
                    self.statusbar.SetStatusText(f'Larch Version {self.vinfo.local_version}', 1)
                else:
                    self.statusbar.SetStatusText(f'Larch Version {self.vinfo.local_version} (latest)', 1)


    def createMainPanel(self):
        display0 = wx.Display(0)
        client_area = display0.ClientArea
        xmin, ymin, xmax, ymax = client_area
        xpos = int((xmax-xmin)*0.02) + xmin
        ypos = int((ymax-ymin)*0.04) + ymin
        self.SetPosition((xpos, ypos))

        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE,
                                      size=(700, 700))
        splitter.SetMinimumPaneSize(250)

        leftpanel = wx.Panel(splitter)
        ltop = wx.Panel(leftpanel)

        def Btn(msg, x, act):
            b = Button(ltop, msg, size=(x, 30),  action=act)
            b.SetFont(Font(FONTSIZE))
            return b

        sel_none = Btn('Select None',   120, self.onSelNone)
        sel_all  = Btn('Select All',    120, self.onSelAll)

        file_actions = [('Show Group Journal', self.onGroupJournal),
                        ('Copy Group', self.onCopyGroup),
                        ('Rename Group', self.onRenameGroup),
                        ('Remove Group', self.onRemoveGroup)]

        self.controller.filelist = FileCheckList(leftpanel, main=self,
                                                 pre_actions=file_actions,
                                                 select_action=self.ShowFile,
                                                 remove_action=self.RemoveFile)
        set_color(self.controller.filelist, 'list_fg', bg='list_bg')

        tsizer = wx.BoxSizer(wx.HORIZONTAL)
        tsizer.Add(sel_all, 1, LEFT|wx.GROW, 1)
        tsizer.Add(sel_none, 1, LEFT|wx.GROW, 1)
        pack(ltop, tsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ltop, 0, LEFT|wx.GROW, 1)
        sizer.Add(self.controller.filelist, 1, LEFT|wx.GROW|wx.ALL, 1)

        pack(leftpanel, sizer)

        # right hand side
        panel = scrolled.ScrolledPanel(splitter)
        panel.SetSize((650, 650))
        panel.SetMinSize((450, 550))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.title = SimpleText(panel, ' ', size=(500, 25),
                                font=Font(FONTSIZE+3), style=LEFT,
                                colour=COLORS['nb_text'])

        ir = 0
        sizer.Add(self.title, 0, CEN, 3)
        self.nb = flatnotebook(panel, NB_PANELS,
                               panelkws=dict(xasmain=self,
                                             controller=self.controller),
                               on_change=self.onNBChanged,
                               size=(700, 700))

        sizer.Add(self.nb, 1, LEFT|wx.EXPAND, 2)
        panel.SetupScrolling()

        pack(panel, sizer)
        splitter.SplitVertically(leftpanel, panel, 1)

    def process_normalization(self, dgroup, force=True, use_form=True):
        self.get_nbpage('xasnorm')[1].process(dgroup, force=force, use_form=use_form)

    def process_exafs(self, dgroup, force=True):
        self.get_nbpage('exafs')[1].process(dgroup, force=force)

    def get_nbpage(self, name):
        "get nb page by name"
        name = name.lower()
        out = (0, self.nb.GetCurrentPage())
        for i, page in enumerate(self.nb.pagelist):
            if name in page.__class__.__name__.lower():
                out = (i, page)
        return out

    def onNBChanged(self, event=None):
        callback = getattr(self.nb.GetCurrentPage(), 'onPanelExposed', None)
        if callable(callback):
            callback()

    def onSelAll(self, event=None):
        self.controller.filelist.select_all()

    def onSelNone(self, event=None):
        self.controller.filelist.select_none()

    def write_message(self, msg, panel=0):
        """write a message to the Status Bar"""
        self.statusbar.SetStatusText(msg, panel)

    def RemoveFile(self, fname=None, **kws):
        if fname is not None:
            s = str(fname)
            if s in self.controller.file_groups:
                group = self.controller.file_groups.pop(s)
            self.controller.sync_xasgroups()

    def ShowFile(self, evt=None, groupname=None, process=True,
                 filename=None, plot=True, **kws):
        if filename is None and evt is not None:
            filename = str(evt.GetString())

        if groupname is None and filename is not None:
            groupname = self.controller.file_groups[filename]

        if not hasattr(self.larch.symtable, groupname):
            return

        dgroup = self.controller.get_group(groupname)
        if dgroup is None:
            return

        if (getattr(dgroup, 'datatype', 'raw').startswith('xa') and not
            (hasattr(dgroup, 'norm') and hasattr(dgroup, 'e0'))):
            self.process_normalization(dgroup, force=True, use_form=False)

        if filename is None:
            filename = dgroup.filename
        self.current_filename = filename
        journal = getattr(dgroup, 'journal', Journal(source_desc=filename))
        if isinstance(journal, Journal):
            sdesc = journal.get('source_desc', latest=True)
        else:
            sdesc = journal.get('source_desc', '?')

        if isinstance(sdesc, Entry):
            sdesc = sdesc.value
        if not isinstance(sdesc, str):
            sdesc = repr(sdesc)
        self.title.SetLabel(sdesc)

        self.controller.group = dgroup
        self.controller.groupname = groupname
        cur_panel = self.nb.GetCurrentPage()
        if process:
            cur_panel.fill_form(dgroup)
            cur_panel.skip_process = False
            cur_panel.process(dgroup=dgroup)
            if plot and hasattr(cur_panel, 'plot'):
                cur_panel.plot(dgroup=dgroup)
            cur_panel.skip_process = False

        self.controller.filelist.SetStringSelection(filename)


    def createMenus(self):
        # ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        group_menu = wx.Menu()
        data_menu = wx.Menu()
        feff_menu = wx.Menu()
        m = {}

        MenuItem(self, fmenu, "&Open Data File\tCtrl+O",
                 "Open Data File",  self.onReadDialog)

        MenuItem(self, fmenu, "&Read Larch Session\tCtrl+R",
                 "Read Previously Saved Session",  self.onLoadSession)

        MenuItem(self, fmenu, "&Save Larch Session\tCtrl+S",
                 "Save Session to a File",  self.onSaveSession)

        MenuItem(self, fmenu, "&Save Larch Session As ...\tCtrl+A",
                 "Save Session to a File",  self.onSaveSessionAs)

        MenuItem(self, fmenu, "Clear Larch Session",
                 "Clear all data from this Session",  self.onClearSession)

        # autosaved session
        conf = self.controller.get_config('autosave',
                                          {'fileroot': 'autosave'})
        froot= conf['fileroot']

        recent_menu = wx.Menu()
        for tstamp, fname in self.controller.get_recentfiles():
            MenuItem(self, recent_menu,
                     "%s [%s ago]" % (fname, time_ago(tstamp)),
                     f"file saved {isotime(tstamp)}",
                     partial(self.onLoadSession, path=fname))

        recent_menu.AppendSeparator()
        for tstamp, fname in self.controller.recent_autosave_sessions():
            MenuItem(self, recent_menu,
                     "%s [%s ago]" % (fname, time_ago(tstamp)),
                     f"file saved {isotime(tstamp)}",
                     partial(self.onLoadSession, path=fname))

        fmenu.Append(-1, 'Recent Session Files',  recent_menu)


        MenuItem(self, fmenu, "&Auto-Save Larch Session",
                 f"Save Session now",  self.autosave_session)
        fmenu.AppendSeparator()

        MenuItem(self, fmenu, "Save Selected Groups to Athena Project File",
                 "Save Selected Groups to an Athena Project File",
                 self.onExportAthenaProject)

        MenuItem(self, fmenu, "Save Selected Groups to CSV File",
                 "Save Selected Groups to a CSV File",
                 self.onExportCSV)

        MenuItem(self, fmenu, 'Save Larch History as Script\tCtrl+H',
                 'Save Session History as Larch Script',
                 self.onSaveLarchHistory)

        fmenu.AppendSeparator()

        MenuItem(self, fmenu, 'Show Larch Buffer\tCtrl+L',
                 'Show Larch Programming Buffer',
                 self.onShowLarchBuffer)

        MenuItem(self, fmenu, 'wxInspect\tCtrl+I',
                 'Show wx inspection window',   self.onwxInspect)
        
        MenuItem(self, fmenu, 'Edit Preferences\tCtrl+E', 'Customize Preferences',
                 self.onPreferences)

        MenuItem(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)


        MenuItem(self, group_menu, "Copy This Group",
                 "Copy This Group", self.onCopyGroup)

        MenuItem(self, group_menu, "Rename This Group",
                 "Rename This Group", self.onRenameGroup)

        MenuItem(self, group_menu, "Show Journal for This Group",
                 "Show Processing Journal for This Group", self.onGroupJournal)


        group_menu.AppendSeparator()

        MenuItem(self, group_menu, "Remove Selected Groups",
                 "Remove Selected Group", self.onRemoveGroups)

        group_menu.AppendSeparator()

        MenuItem(self, group_menu, "Merge Selected Groups",
                 "Merge Selected Groups", self.onMergeData)

        group_menu.AppendSeparator()

        MenuItem(self, group_menu, "Freeze Selected Groups",
                 "Freeze Selected Groups", self.onFreezeGroups)

        MenuItem(self, group_menu, "UnFreeze Selected Groups",
                 "UnFreeze Selected Groups", self.onUnFreezeGroups)

        MenuItem(self, data_menu, "Deglitch Data",  "Deglitch Data",
                 self.onDeglitchData)

        MenuItem(self, data_menu, "Calibrate Energy",
                 "Calibrate Energy",
                 self.onEnergyCalibrateData)

        MenuItem(self, data_menu, "Smooth Data", "Smooth Data",
                 self.onSmoothData)

        MenuItem(self, data_menu, "Deconvolve Data",
                 "Deconvolution of Data",  self.onDeconvolveData)

        MenuItem(self, data_menu, "Rebin Data", "Rebin Data",
                 self.onRebinData)

        MenuItem(self, data_menu, "Correct Over-absorption",
                 "Correct Over-absorption",
                 self.onCorrectOverAbsorptionData)

        MenuItem(self, data_menu, "Add and Subtract Spectra",
                 "Calculations of Spectra",  self.onSpectraCalc)


        self.menubar.Append(fmenu, "&File")
        self.menubar.Append(group_menu, "Groups")
        self.menubar.Append(data_menu, "Data")

        MenuItem(self, feff_menu, "Browse CIF Structures, Run Feff",
                 "Browse CIF Structure, run Feff", self.onCIFBrowse)
        MenuItem(self, feff_menu, "Generate Feff input from general structures, Run Feff",
                 "Generate Feff input from general structures, run Feff", self.onStructureBrowse)
        MenuItem(self, feff_menu, "Browse Feff Calculations",
                 "Browse Feff Calculations, Get Feff Paths", self.onFeffBrowse)

        self.menubar.Append(feff_menu, "Feff")

        hmenu = wx.Menu()
        MenuItem(self, hmenu, 'About Larix', 'About Larix',
                 self.onAbout)
        MenuItem(self, hmenu, 'Check for Updates', 'Check for Updates',
                 self.onCheckforUpdates)

        self.menubar.Append(hmenu, '&Help')
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)

    def onwxInspect(self, evt=None):
        wx.GetApp().ShowInspectionTool()
        
    def onShowLarchBuffer(self, evt=None):
        if self.larch_buffer is None:
            self.larch_buffer = LarchFrame(_larch=self.larch, is_standalone=False)
        self.larch_buffer.Show()
        self.larch_buffer.Raise()

    def onSaveLarchHistory(self, evt=None):
        wildcard = 'Larch file (*.lar)|*.lar|All files (*.*)|*.*'
        path = FileSave(self, message='Save Session History as Larch Script',
                        wildcard=wildcard,
                        default_file='larix_history.lar')
        if path is not None:
            self.larch._larch.input.history.save(path, session_only=True)
            self.write_message("Wrote history %s" % path, 0)

    def onExportCSV(self, evt=None):
        filenames = self.controller.filelist.GetCheckedStrings()
        if len(filenames) < 1:
            Popup(self, "No files selected to export to CSV",
                  "No files selected")
            return

        deffile = "%s_%i.csv" % (filenames[0], len(filenames))

        dlg = ExportCSVDialog(self, filenames)
        res = dlg.GetResponse()

        dlg.Destroy()
        if not res.ok:
            return

        deffile = f"{filenames[0]:s}_{len(filenames):d}.csv"
        wcards  = 'CSV Files (*.csv)|*.csv|All files (*.*)|*.*'

        outfile = FileSave(self, 'Save Groups to CSV File',
                           default_file=deffile, wildcard=wcards)

        if outfile is None:
            return
        if os.path.exists(outfile) and uname != 'darwin':  # darwin prompts in FileSave!
            if wx.ID_YES != Popup(self,
                                  "Overwrite existing CSV File?",
                                  "Overwrite existing file?", style=wx.YES_NO):
                return

        savegroups = [self.controller.filename2group(res.master)]
        for fname in filenames:
            dgroup = self.controller.filename2group(fname)
            if dgroup not in savegroups:
                savegroups.append(dgroup)

        try:
            groups2csv(savegroups, outfile, x=res.xarray, y=res.yarray,
                    delim=res.delim, individual=res.individual)
            self.write_message(f"Exported CSV file {outfile:s}")
        except:
            title = "Could not export CSV File"
            message = [f"Could not export CSV File {outfile}"]
            ExceptionPopup(self, title, message)

    # Athena
    def onExportAthenaProject(self, evt=None):
        groups = []
        self.controller.sync_xasgroups()
        for checked in self.controller.filelist.GetCheckedStrings():
            groups.append(self.controller.file_groups[str(checked)])

        if len(groups) < 1:
             Popup(self, "No files selected to export to Project",
                   "No files selected")
             return
        prompt, prjfile = self.get_athena_project()
        self.save_athena_project(prjfile, groups)

    def get_athena_project(self):
        prjfile = self.last_athena_file
        prompt = False
        if prjfile is None:
            tstamp = isotime(filename=True)[:15]
            prjfile = f"{tstamp:s}.prj"
            prompt = True
        return prompt, prjfile

    def onSaveAthenaProject(self, evt=None):
        groups = self.controller.filelist.GetItems()
        if len(groups) < 1:
            Popup(self, "No files to export to Project", "No files to export")
            return

        prompt, prjfile = self.get_athenaproject()
        self.save_athena_project(prjfile, groups, prompt=prompt,
                                 warn_overwrite=False)

    def onSaveAsAthenaProject(self, evt=None):
        groups = self.controller.filelist.GetItems()
        if len(groups) < 1:
            Popup(self, "No files to export to Project", "No files to export")
            return

        prompt, prjfile = self.get_athena_project()
        self.save_athena_project(prjfile, groups)

    def save_athena_project(self, filename, grouplist, prompt=True,
                            warn_overwrite=True):
        if len(grouplist) < 1:
            return
        savegroups = [self.controller.get_group(gname) for gname in grouplist]
        if prompt:
            _, filename = os.path.split(filename)
            wcards  = 'Project Files (*.prj)|*.prj|All files (*.*)|*.*'
            filename = FileSave(self, 'Save Groups to Project File',
                                default_file=filename, wildcard=wcards)
            if filename is None:
                return

        if os.path.exists(filename) and warn_overwrite and uname != 'darwin':  # darwin prompts in FileSave!
            if wx.ID_YES != Popup(self,
                                  "Overwrite existing Project File?",
                                  "Overwrite existing file?", style=wx.YES_NO):
                return

        aprj = AthenaProject(filename=filename)
        for label, grp in zip(grouplist, savegroups):
            aprj.add_group(grp)
        aprj.save(use_gzip=True)
        self.write_message("Saved project file %s" % (filename))
        self.last_athena_file = filename


    def onPreferences(self, evt=None):
        self.show_subframe('preferences', PreferencesFrame,
                           controller=self.controller)

    def onLoadSession(self, evt=None, path=None):
        if path is None:
            wildcard = 'Larch Session File (*.larix)|*.larix|All files (*.*)|*.*'
            path = FileOpen(self, message="Load Larch Session",
                            wildcard=wildcard, default_file='larch.larix')
        if path is None:
            return

        if is_athena_project(path):
            self.show_subframe('athena_import', AthenaImporter,
                               controller=self.controller, filename=path,
                               read_ok_cb=self.onReadAthenaProject_OK)
            return

        try:
            _session  = read_session(path)
        except:
            title = "Invalid Path for Larch Session"
            message = [f"{path} is not a valid Larch Session File"]
            ExceptionPopup(self, title, message)
            return

        LoadSessionDialog(self, _session, path, self.controller).Show()
        self.last_session_read = path
        fdir, fname = os.path.split(path)
        if self.controller.chdir_on_fileopen() and len(fdir) > 0:
            os.chdir(fdir)
            self.controller.set_workdir()

    def onSaveSessionAs(self, evt=None):
        groups = self.controller.filelist.GetItems()
        if len(groups) < 1:
            return
        self.last_session_file = None
        self.onSaveSession()


    def onSaveSession(self, evt=None):
        groups = self.controller.filelist.GetItems()
        if len(groups) < 1:
            return

        fname = self.last_session_file
        if fname is None:
            fname = self.last_session_read
            if fname is None:
                fname = time.strftime('%Y%b%d_%H%M') + '.larix'

            _, fname = os.path.split(fname)
            wcards  = 'Larch Project Files (*.larix)|*.larix|All files (*.*)|*.*'
            fname = FileSave(self, 'Save Larch Session File',
                             default_file=fname, wildcard=wcards)
            if fname is None:
                return

            if os.path.exists(fname) and uname != 'darwin':  # darwin prompts in FileSave!
                if wx.ID_YES != Popup(self, "Overwrite existing Project File?",
                                      "Overwrite existing file?", style=wx.YES_NO):
                    return

        save_session(fname=fname, _larch=self.larch._larch)
        stime = time.strftime("%H:%M")
        self.last_save_message = ("Session last saved", f"'{fname}'", f"{stime}")
        self.write_message(f"Saved session to '{fname}' at {stime}")
        self.last_session_file = self.last_session_read = fname

    def onClearSession(self, evt=None):
        conf = self.controller.get_config('autosave',
                                          {'fileroot': 'autosave'})
        afile = os.path.join(self.controller.larix_folder,
                             conf['fileroot']+'.larix')

        msg = f"""Session will be saved to
         '{afile:s}'
before clearing"""

        dlg = wx.Dialog(None, -1, title="Clear all Session data?", size=(550, 300))
        dlg.SetFont(Font(FONTSIZE))
        panel = GridPanel(dlg, ncols=3, nrows=4, pad=2, itemstyle=LEFT)

        panel.Add(wx.StaticText(panel, label="Clear all Session Data?"), dcol=2)
        panel.Add(wx.StaticText(panel, label=msg), dcol=4, newrow=True)

        panel.Add((5, 5) ,  newrow=True)
        panel.Add((5, 5), newrow=True)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()

        fit_dialog_window(dlg, panel)


        if wx.ID_OK == dlg.ShowModal():
            self.autosave_session()
            self.controller.clear_session()
        dlg.Destroy()


    def onConfigDataProcessing(self, event=None):
        pass


    def onCopyGroup(self, event=None, journal=None):
        fname = self.current_filename
        if fname is None:
            fname = self.controller.filelist.GetStringSelection()
        ogroup = self.controller.get_group(fname)
        ngroup = self.controller.copy_group(fname)
        self.install_group(ngroup, journal=ogroup.journal)

    def onGroupJournal(self, event=None):
        dgroup = self.controller.get_group()
        if dgroup is not None:
            self.show_subframe('group_journal', GroupJournalFrame, xasmain=self)
            self.subframes['group_journal'].set_group(dgroup)


    def onRenameGroup(self, event=None):
        fname = self.current_filename = self.controller.filelist.GetStringSelection()
        if fname is None:
            return
        dlg = RenameDialog(self, fname)
        res = dlg.GetResponse()
        dlg.Destroy()

        if res.ok:
            selected = []
            for checked in self.controller.filelist.GetCheckedStrings():
                selected.append(str(checked))
            if self.current_filename in selected:
                selected.remove(self.current_filename)
                selected.append(res.newname)

            groupname = self.controller.file_groups.pop(fname)
            self.controller.sync_xasgroups()
            self.controller.file_groups[res.newname] = groupname
            self.controller.filelist.rename_item(self.current_filename, res.newname)
            dgroup = self.controller.get_group(groupname)
            dgroup.filename = self.current_filename = res.newname

            self.controller.filelist.SetCheckedStrings(selected)
            self.controller.filelist.SetStringSelection(res.newname)

    def onRemoveGroup(self, event=None):
        n = int(self.controller.filelist.GetSelection())
        all_names = self.controller.filelist.GetItems()
        fname = all_names[n]

        do_remove = (wx.ID_YES == Popup(self,
                                        f"Remove Group '{fname}'?",
                                        'Remove Group? Cannot be undone!',
                                        style=wx.YES_NO))
        if do_remove:
            fname = all_names.pop(n)
            self.controller.filelist.refresh(all_names)
            self.RemoveFile(fname)


    def onRemoveGroups(self, event=None):
        groups = []
        for checked in self.controller.filelist.GetCheckedStrings():
            groups.append(str(checked))
        if len(groups) < 1:
            return

        dlg = RemoveDialog(self, groups)
        res = dlg.GetResponse()
        dlg.Destroy()

        if res.ok:
            filelist = self.controller.filelist
            all_fnames = filelist.GetItems()
            for fname in groups:
                gname = self.controller.file_groups.pop(fname)
                delattr(self.controller.symtable, gname)
                all_fnames.remove(fname)

            filelist.Clear()
            for name in all_fnames:
                filelist.Append(name)
            self.controller.sync_xasgroups()

    def onFreezeGroups(self, event=None):
        self._freeze_handler(True)

    def onUnFreezeGroups(self, event=None):
        self._freeze_handler(False)

    def _freeze_handler(self, freeze):
        current_filename = self.current_filename
        reproc_group = None
        for fname in self.controller.filelist.GetCheckedStrings():
            groupname = self.controller.file_groups[str(fname)]
            dgroup = self.controller.get_group(groupname)
            if fname == current_filename:
                reproc_group = groupname
            dgroup.is_frozen = freeze
        if reproc_group is not None:
            self.ShowFile(groupname=reproc_group, process=True)

    def onMergeData(self, event=None):
        groups = {}
        for checked in self.controller.filelist.GetCheckedStrings():
            cname = str(checked)
            groups[cname] = self.controller.file_groups[cname]
        if len(groups) < 1:
            return

        outgroup = common_startstring(list(groups.keys()))
        if len(outgroup) < 2: outgroup = "data"
        outgroup = "%s (merge %d)" % (outgroup, len(groups))
        outgroup = unique_name(outgroup, self.controller.file_groups)
        dlg = MergeDialog(self, list(groups.keys()), outgroup=outgroup)
        res = dlg.GetResponse()
        dlg.Destroy()
        if res.ok:
            fname = res.group
            gname = fix_varname(res.group.lower())
            master = self.controller.file_groups[res.master]
            yname = 'norm' if res.ynorm else 'mu'
            this = self.controller.merge_groups(list(groups.values()),
                                                master=master,
                                                yarray=yname,
                                                outgroup=gname)

            mfiles, mgroups = [], []
            for g in groups.values():
                mgroups.append(g)
                mfiles.append(self.controller.get_group(g).filename)
            mfiles  = '[%s]' % (', '.join(mfiles))
            mgroups = '[%s]' % (', '.join(mgroups))
            desc = "%s: merge of %d groups" % (fname, len(groups))
            self.install_group(gname, fname, source=desc,
                               journal={'source_desc': desc,
                                        'merged_groups': mgroups,
                                        'merged_filenames': mfiles})

    def has_datagroup(self):
        return hasattr(self.controller.get_group(), 'energy')

    def onDeglitchData(self, event=None):
        if self.has_datagroup():
            DeglitchDialog(self, self.controller).Show()

    def onSmoothData(self, event=None):
        if self.has_datagroup():
            SmoothDataDialog(self, self.controller).Show()

    def onRebinData(self, event=None):
        if self.has_datagroup():
            RebinDataDialog(self, self.controller).Show()

    def onCorrectOverAbsorptionData(self, event=None):
        if self.has_datagroup():
            OverAbsorptionDialog(self, self.controller).Show()

    def onSpectraCalc(self, event=None):
        if self.has_datagroup():
            SpectraCalcDialog(self, self.controller).Show()

    def onEnergyCalibrateData(self, event=None):
        if self.has_datagroup():
            EnergyCalibrateDialog(self, self.controller).Show()

    def onDeconvolveData(self, event=None):
        if self.has_datagroup():
            DeconvolutionDialog(self, self.controller).Show()

    def onConfigDataFitting(self, event=None):
        pass

    def onAbout(self, event=None):
        info = AboutDialogInfo()
        info.SetName('Larix')
        info.SetDescription('X-ray Absorption Visualization and Analysis')
        info.SetVersion('Larch %s ' % larch.version.__version__)
        info.AddDeveloper('Matthew Newville: newville at cars.uchicago.edu')
        dlg = AboutBox(info)

    def onCheckforUpdates(self, event=None):
        dlg = LarchUpdaterDialog(self, caller='Larix')
        dlg.Raise()
        dlg.SetWindowStyle(wx.STAY_ON_TOP)
        res = dlg.GetResponse()
        dlg.Destroy()
        if res.ok and res.run_updates:
            from larch.apps import update_larch
            update_larch()
            self.onClose(event=event, prompt=False)

    def onClose(self, event=None, prompt=True):
        if prompt:
            dlg = QuitDialog(self, self.last_save_message)
            dlg.Raise()
            dlg.SetWindowStyle(wx.STAY_ON_TOP)
            res = dlg.GetResponse()
            dlg.Destroy()
            if not res.ok:
                return

        self.controller.save_workdir()
        try:
            self.controller.close_all_displays()
        except Exception:
            pass

        if self.larch_buffer is not None:
            try:
                self.larch_buffer.Destroy()
            except Exception:
                pass

        def destroy(wid):
            if hasattr(wid, 'Destroy'):
                try:
                    wid.Destroy()
                except Exception:
                    pass
                time.sleep(0.01)

        for name, wid in self.subframes.items():
            destroy(wid)

        for i in range(self.nb.GetPageCount()):
            nbpage = self.nb.GetPage(i)
            timers = getattr(nbpage, 'timers', None)
            if timers is not None:
                for t in timers.values():
                    t.Stop()

            if hasattr(nbpage, 'subframes'):
                for name, wid in nbpage.subframes.items():
                    destroy(wid)
        for t in self.timers.values():
            t.Stop()

        time.sleep(0.05)
        self.Destroy()

    def show_subframe(self, name, frameclass, **opts):
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except:
                del self.subframes[name]
        if not shown:
            self.subframes[name] = frameclass(self, **opts)


    def onCIFBrowse(self, event=None):
        self.show_subframe('cif_feff', CIFFrame, _larch=self.larch,
                           path_importer=self.get_nbpage('feffit')[1].add_path,
                           with_feff=True)

    def onStructureBrowse(self, event=None):
        self.show_subframe('structure_feff', Structure2FeffFrame, _larch=self.larch,
                           path_importer=self.get_nbpage('feffit')[1].add_path)

    def onFeffBrowse(self, event=None):
        self.show_subframe('feff_paths', FeffResultsFrame, _larch=self.larch,
                           path_importer=self.get_nbpage('feffit')[1].add_path)

    def onLoadFitResult(self, event=None):
        pass
        # print("onLoadFitResult??")
        # self.nb.SetSelection(1)
        # self.nb_panels[1].onLoadFitResult(event=event)

    def onReadDialog(self, event=None):
        dlg = wx.FileDialog(self, message="Read Data File",
                            defaultDir=get_cwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.FD_OPEN|wx.FD_MULTIPLE)
        self.paths2read = []
        if dlg.ShowModal() == wx.ID_OK:
            self.paths2read = dlg.GetPaths()
        dlg.Destroy()

        if len(self.paths2read) < 1:
            return

        def file_mtime(x):
            return os.stat(x).st_mtime

        self.paths2read = sorted(self.paths2read, key=file_mtime)

        path = self.paths2read.pop(0)
        path = path.replace('\\', '/')
        do_read = True
        if path in self.controller.file_groups:
            do_read = (wx.ID_YES == Popup(self,
                                          "Re-read file '%s'?" % path,
                                          'Re-read file?'))
        if do_read:
            self.onRead(path)

    def onRead(self, path):
        filedir, filename = os.path.split(os.path.abspath(path))
        if self.controller.chdir_on_fileopen() and len(filedir) > 0:
            os.chdir(filedir)
            self.controller.set_workdir()

        # check for athena projects
        if is_athena_project(path):
            self.show_subframe('athena_import', AthenaImporter,
                               controller=self.controller, filename=path,
                               read_ok_cb=self.onReadAthenaProject_OK)
        # check for Spec File
        elif is_specfile(path):
            self.show_subframe('spec_import', SpecfileImporter,
                               filename=path,
                               _larch=self.larch_buffer.larchshell,
                               config=self.last_spec_config,
                               read_ok_cb=self.onReadSpecfile_OK)
        # check for Larch Session File
        elif is_larch_session_file(path):
            self.onLoadSession(path=path)
        # default to Column File
        else:
            self.show_subframe('readfile', ColumnDataFileFrame, filename=path,
                               config=self.last_col_config,
                               _larch=self.larch_buffer.larchshell,
                               read_ok_cb=self.onRead_OK)

    def onReadSpecfile_OK(self, script, path, scanlist, config=None):
        """read groups from a list of scans from a specfile"""
        self.larch.eval("_specfile = specfile('{path:s}')".format(path=path))
        dgroup = None
        _path, fname = os.path.split(path)
        first_group = None
        cur_panel = self.nb.GetCurrentPage()
        cur_panel.skip_plotting = True
        symtable = self.larch.symtable
        if config is not None:
            self.last_spec_config = config

        array_desc = config.get('array_desc', {})

        multiconfig = config.get('multicol_config', {'channels':[], 'i0': config['iy2']})
        multi_i0  = multiconfig.get('i0', config['iy2'])
        multi_chans = copy.copy(multiconfig.get('channels', []))

        if len(multi_chans) > 0:
            if (multi_chans[0] == config['iy1'] and multi_i0 == config['iy2']
                and 'log' not in config['expressions']['ydat']):
                yname = config['array_labels'][config['iy1']]
                # filename = f"{spath}:{yname}"
                multi_chans.pop(0)

        for scan in scanlist:
            gname = fix_varname("{:s}{:s}".format(fname[:6], scan))
            if hasattr(symtable, gname):
                count, tname = 0, gname
                while count < 1e7 and self.larch.symtable.has_group(tname):
                    tname = gname + make_hashkey(length=7)
                    count += 1
                gname = tname

            cur_panel.skip_plotting = (scan == scanlist[-1])
            yname = config['yarr1']
            if first_group is None:
                first_group = gname
            cmd = script.format(group=gname, specfile='_specfile',
                                path=path, scan=scan, **config)

            self.larch.eval(cmd)
            displayname = f"{fname} scan{scan} {yname}"
            jrnl = {'source_desc': f"{fname}: scan{scan} {yname}"}
            dgroup = self.install_group(gname, displayname, journal=jrnl)
            if len(multi_chans) > 0:
                ydatline = None
                for line in script.split('\n'):
                    if line.startswith("{group}.ydat ="):
                        ydatline = line.replace("{group}", "{ngroup}")
                mscript = '\n'.join(["{ngroup} = deepcopy({group})",
                                     ydatline,
                                    "{ngroup}.mu = {ngroup}.ydat",
                                     "{ngroup}.plot_ylabel = '{ylabel}'"])
                i0 = '1.0'
                if multi_i0  < len(config['array_labels']):
                    i0 = config['array_labels'][multi_i0]

                for mchan in multi_chans:
                    yname = config['array_labels'][mchan]
                    ylabel = f"{yname}/{i0}"
                    dname = f"{fname} scan{scan} {yname}"
                    ngroup = file2groupname(dname, symtable=self.larch.symtable)
                    njournal = {'source': path,
                                'xdat': array_desc['xdat'].format(group=ngroup),
                                'ydat': ylabel,
                                'source_desc': f"{fname}: scan{scan} {yname}",
                                'yerr': array_desc['yerr'].format(group=ngroup)}
                    cmd = mscript.format(group=gname, ngroup=ngroup,
                                         iy1=mchan, iy2=multi_i0, ylabel=ylabel)
                    self.larch.eval(cmd)
                    self.install_group(ngroup, dname, source=path, journal=njournal)


        cur_panel.skip_plotting = False

        if first_group is not None:
            self.ShowFile(groupname=first_group, process=True, plot=True)
        self.write_message("read %d datasets from %s" % (len(scanlist), path))
        self.larch.eval('del _specfile')


    def onReadAthenaProject_OK(self, path, namelist):
        """read groups from a list of groups from an athena project file"""
        self.larch.eval("_prj = read_athena('{path:s}', do_fft=False, do_bkg=False)".format(path=path))
        dgroup = None
        script = "{group:s} = extract_athenagroup(_prj.{prjgroup:s})"
        cur_panel = self.nb.GetCurrentPage()
        cur_panel.skip_plotting = True
        parent, spath = os.path.split(path)
        labels = []
        groups_added = []

        for ig, gname in enumerate(namelist):
            cur_panel.skip_plotting = (gname == namelist[-1])
            this = getattr(self.larch.symtable._prj, gname)
            gid = file2groupname(str(getattr(this, 'athena_id', gname)),
                                 symtable=self.larch.symtable)
            if self.larch.symtable.has_group(gid):
                count, prefix = 0, gname[:3]
                while count < 1e7 and self.larch.symtable.has_group(gid):
                    gid = prefix + make_hashkey(length=7)
                    count += 1
            label = getattr(this, 'label', gname).strip()
            labels.append(label)

            jrnl = {'source_desc': f'{spath:s}: {gname:s}'}
            self.larch.eval(script.format(group=gid, prjgroup=gname))
            dgroup = self.install_group(gid, label, process=False,
                                        source=path, journal=jrnl)
            groups_added.append(gid)

        for gid in groups_added:
            rgroup = gid
            dgroup = self.larch.symtable.get_group(gid)

            conf_xasnorm = dgroup.config.xasnorm
            conf_exafs= dgroup.config.exafs

            apars = getattr(dgroup, 'athena_params', {})
            abkg = getattr(apars, 'bkg', {})
            afft = getattr(apars, 'fft', {})

            # norm
            for attr in ('e0', 'pre1', 'pre2', 'nnorm'):
                if hasattr(abkg, attr):
                    conf_xasnorm[attr] = float(getattr(abkg, attr))

            for attr, alt in (('norm1', 'nor1'), ('norm2', 'nor2'),
                              ('edge_step', 'step')):
                if hasattr(abkg, alt):
                    conf_xasnorm[attr]  = float(getattr(abkg, alt))
            if hasattr(abkg, 'fixstep'):
                a = float(getattr(abkg, 'fixstep', 0.0))
                conf_xasnorm['auto_step'] = (a < 0.5)


            # bkg
            for attr in ('e0', 'rbkg'):
                if hasattr(abkg, attr):
                    conf_exafs[attr] = float(getattr(abkg, attr))

            for attr, alt in (('bkg_kmin', 'spl1'), ('bkg_kmax', 'spl2'),
                              ('bkg_kweight', 'kw'), ('bkg_clamplo', 'clamp1'),
                              ('bkg_clamphi', 'clamp2')):
                if hasattr(abkg, alt):
                    val = getattr(abkg, alt)
                    try:
                        val = float(getattr(abkg, alt))
                    except:
                        if alt.startswith('clamp') and isinstance(val, str):
                            val = ATHENA_CLAMPNAMES.get(val.lower(), 0)
                    conf_exafs[attr] = val


            # fft
            for attr in ('kmin', 'kmax', 'dk', 'kwindow', 'kw'):
                if hasattr(afft, attr):
                    n = f'fft_{attr}'
                    if attr == 'kw': n = 'fft_kweight'
                    if attr == 'kwindow':
                        conf_exafs[n] = getattr(afft, attr)
                    else:
                        conf_exafs[n] = float(getattr(afft, attr))

            # reference
            refgroup = getattr(apars, 'reference', '')
            if refgroup in groups_added:
                newname = None
                for key, val in self.controller.file_groups.items():
                    if refgroup in (key, val):
                        newname = key

                if newname is not None:
                    refgroup = newname
            else:
                refgroup = dgroup.filename
            dgroup.energy_ref = refgroup

        self.larch.eval("del _prj")
        cur_panel.skip_plotting = False

        plot_first = True
        if len(labels) > 0:
            gname = self.controller.file_groups[labels[0]]
            self.ShowFile(groupname=gname, process=True, plot=plot_first)
            plot_first = False
        self.write_message("read %d datasets from %s" % (len(namelist), path))
        self.last_athena_file = path
        self.controller.sync_xasgroups()
        self.controller.recentfiles.append((time.time(), path))

    def onRead_OK(self, script, path, config):
        #groupname=None, filename=None,
        #          ref_groupname=None, ref_filename=None, config=None,
        #          array_desc=None):

        """ called when column data has been selected and is ready to be used
        overwrite: whether to overwrite the current datagroup, as when
        editing a datagroup
        """
        filedir, spath = os.path.split(path)
        filename = config.get('filename', spath)
        groupname = config.get('groupname', None)
        if groupname is None:
            return
        array_desc = config.get('array_desc', {})

        if hasattr(self.larch.symtable, groupname):
            groupname = file2groupname(filename,
                                       symtable=self.larch.symtable)

        refgroup = config.get('refgroup', groupname + '_ref')

        multiconfig = config.get('multicol_config', {'channels':[], 'i0': config['iy2']})
        multi_i0  = multiconfig.get('i0', config['iy2'])
        multi_chans = copy.copy(multiconfig.get('channels', []))

        if len(multi_chans) > 0:
            if (multi_chans[0] == config['iy1'] and multi_i0 == config['iy2']
                and 'log' not in config['expressions']['ydat']):
                yname = config['array_labels'][config['iy1']]
                filename = f"{spath}:{yname}"
                multi_chans.pop(0)

        config = copy.copy(config)
        config['group'] = groupname
        config['path'] = path
        has_yref = config.get('has_yref', False)


        self.larch.eval(script.format(**config))

        if config is not None:
            self.last_col_config = config

        journal = {'source': path}
        refjournal = {}

        if 'xdat' in array_desc:
            journal['xdat'] = array_desc['xdat'].format(group=groupname)
        if 'ydat' in array_desc:
            journal['ydat'] = ylab = array_desc['ydat'].format(group=groupname)
            journal['source_desc'] = f'{spath}: {ylab}'
        if 'yerr' in array_desc:
            journal['yerr'] = array_desc['yerr'].format(group=groupname)

        self.install_group(groupname, filename, source=path, journal=journal)

        def install_multichans(config):
            ydatline = None
            for line in script.split('\n'):
                if line.startswith("{group}.ydat ="):
                    ydatline = line.replace("{group}", "{ngroup}")
            mscript = '\n'.join(["{ngroup} = deepcopy({group})",
                                 ydatline,
                                 "{ngroup}.mu = {ngroup}.ydat",
                                 "{ngroup}.plot_ylabel = '{ylabel}'"])
            i0 = '1.0'
            if multi_i0  < len(config['array_labels']):
                i0 = config['array_labels'][multi_i0]

            for mchan in multi_chans:
                yname = config['array_labels'][mchan]
                ylabel = f"{yname}/{i0}"
                fname = f"{spath}:{yname}"
                ngroup = file2groupname(fname, symtable=self.larch.symtable)
                njournal = {'source': path,
                            'xdat': array_desc['xdat'].format(group=ngroup),
                            'ydat': ylabel,
                            'source_desc': f"{spath}: {ylabel}",
                            'yerr': array_desc['yerr'].format(group=ngroup)}
                cmd = mscript.format(group=config['group'], ngroup=ngroup,
                                     iy1=mchan, iy2=multi_i0, ylabel=ylabel)
                self.larch.eval(cmd)
                self.install_group(ngroup, fname, source=path, journal=njournal)

        if len(multi_chans) > 0:
            install_multichans(config)

        if has_yref:

            if 'xdat' in array_desc:
                refjournal['xdat'] = array_desc['xdat'].format(group=refgroup)
            if 'yref' in array_desc:
                refjournal['ydat'] = ydx = array_desc['yref'].format(group=refgroup)
                refjournal['source_desc'] = f'{spath:s}: {ydx:s}'
            self.install_group(refgroup, config['reffile'],
                               source=path, journal=refjournal)

        # check if rebin is needed
        thisgroup = getattr(self.larch.symtable, groupname)

        do_rebin = False
        if thisgroup.datatype == 'xas':
            try:
                en = thisgroup.energy
            except:
                do_rebin = True
                en = thisgroup.energy = thisgroup.xdat
            # test for rebinning:
            #  too many data points
            #  unsorted energy data or data in angle
            #  too fine a step size at the end of the data range
            if (len(en) > 1200 or
                any(np.diff(en) < 0) or
                ((max(en)-min(en)) > 300 and
                 (np.diff(en[-50:]).mean() < 0.75))):
                msg = """This dataset may need to be rebinned.
                Rebin now?"""
                dlg = wx.MessageDialog(self, msg, 'Warning',
                                       wx.YES | wx.NO )
                do_rebin = (wx.ID_YES == dlg.ShowModal())
                dlg.Destroy()
        gname = None

        for path in self.paths2read:
            path = path.replace('\\', '/')
            filedir, spath = os.path.split(path)
            fname = spath
            if len(multi_chans) > 0:
                yname = config['array_labels'][config['iy1']]
                fname = f"{spath}:{yname}"

            gname = file2groupname(fname, symtable=self.larch.symtable)
            refgroup = config['refgroup']
            if has_yref:
                refgroup = gname + '_ref'
                reffile = spath + '_ref'
            config = copy.copy(config)
            config['group'] = gname
            config['refgroup'] = refgroup
            config['path'] = path

            self.larch.eval(script.format(**config))
            if has_yref:
                self.larch.eval(f"{gname}.energy_ref = {refgroup}.energy_ref = '{refgroup}'\n")

            if 'xdat' in array_desc:
                journal['xdat'] = array_desc['xdat'].format(group=gname)
            if 'ydat' in array_desc:
                journal['ydat'] = ydx = array_desc['ydat'].format(group=gname)
                journal['source_desc'] = f'{spath:s}: {ydx:s}'
            if 'yerr' in array_desc:
                journal['yerr'] = array_desc['yerr'].format(group=gname)

            self.install_group(gname, fname, source=path, journal=journal, plot=False)
            if len(multi_chans) > 0:
                install_multichans(config)

            if has_yref:
                if 'xdat' in array_desc:
                    refjournal['xdat'] = array_desc['xdat'].format(group=refgroup)
                if 'yref' in array_desc:
                    refjournal['ydat'] = ydx = array_desc['yref'].format(group=refgroup)
                    refjournal['source_desc'] = f'{spath:s}: {ydx:s}'

                self.install_group(refgroup, reffile, source=path, journal=refjournal, plot=False)


        if gname is not None:
            self.ShowFile(groupname=gname)

        self.write_message("read %s" % (spath))
        if do_rebin:
            RebinDataDialog(self, self.controller).Show()

    def install_group(self, groupname, filename=None, source=None, journal=None,
                      process=True, plot=True):
        """add groupname / filename to list of available data groups"""
        if isinstance(groupname, Group):
            groupname = groupname.groupname
        if filename is None:
            g = getattr(self.controller.symtable, groupname)
            filename = g.filename

        self.controller.install_group(groupname, filename,
                                      source=source, journal=journal)

        self.nb.SetSelection(0)
        self.ShowFile(groupname=groupname, filename=filename,
                      process=process, plot=plot)

    ##
    def onAutoSaveTimer(self, event=None):
        """autosave session periodically, using autosave_config settings
        and avoiding saving sessions while program is inactive.
        """
        conf = self.controller.get_config('autosave', {})
        savetime = conf.get('savetime', 600)
        symtab = self.larch.symtable
        if (time.time() > self.last_autosave + savetime and
            symtab._sys.last_eval_time > (self.last_autosave+60) and
            len(symtab._xasgroups) > 0):
            self.autosave_session()

    def autosave_session(self, event=None):
        """autosave session now"""
        savefile = self.controller.autosave_session()
        # save_session(savefile, _larch=self.larch._larch)
        self.last_autosave = time.time()
        stime = time.strftime("%H:%M")
        self.last_save_message = ("Session last saved", f"'{savefile}'", f"{stime}")
        self.write_message(f"Session saved to '{savefile}' at {stime}")


    ## float-spin / pin timer events
    def onPinTimer(self, event=None):
        if 'start' not in self.cursor_dat:
            self.cursor_dat['xsel'] = None
            self.onPinTimerComplete(reason="bad")
        pin_config = self.controller.get_config('pin',
                                                {'style': 'pin_first',
                                                 'max_time':15.0,
                                                 'min_time': 2.0})
        min_time = float(pin_config['min_time'])
        timeout = float(pin_config['max_time'])

        curhist_name = self.cursor_dat['name']
        cursor_hist = getattr(self.larch.symtable._plotter, curhist_name, [])
        if len(cursor_hist) > self.cursor_dat['nhist']: # got new data!
            self.cursor_dat['xsel'] = cursor_hist[0][0]
            self.cursor_dat['ysel'] = cursor_hist[0][1]
            if time.time() > min_time + self.cursor_dat['start']:
                self.timers['pin'].Stop()
                self.onPinTimerComplete(reason="new")
        elif time.time() > timeout + self.cursor_dat['start']:
            self.onPinTimerComplete(reason="timeout")

        if 'win' in self.cursor_dat and 'xsel' in self.cursor_dat:
            time_remaining = timeout + self.cursor_dat['start'] - time.time()
            msg = 'Select Point from Plot #%d' % (self.cursor_dat['win'])
            if self.cursor_dat['xsel'] is not None:
                msg = '%s, [current value=%.1f]' % (msg, self.cursor_dat['xsel'])
            msg = '%s, expiring in %.0f sec' % (msg, time_remaining)
            self.write_message(msg)

    def onPinTimerComplete(self, reason=None, **kws):
        self.timers['pin'].Stop()
        if reason != "bad":
            msg = 'Selected Point at %.1f' % self.cursor_dat['xsel']
            if reason == 'timeout':
                msg = msg + '(timed-out)'
            self.write_message(msg)
            if (self.cursor_dat['xsel'] is not None and
                callable(self.cursor_dat['callback'])):
                self.cursor_dat['callback'](**self.cursor_dat)
                time.sleep(0.05)
        else:
            self.write_message('Select Point Error')
        self.cursor_dat = {}


    def onSelPoint(self, evt=None, opt='__', relative_e0=True, callback=None,
                   win=None):
        """
        get last selected point from a specified plot window
        and fill in the value for the widget defined by `opt`.

        start Pin Timer to get last selected point from a specified plot window
        and fill in the value for the widget defined by `opt`.
        """
        if win is None:
            win = 1

        display = get_display(win=win, _larch=self.larch)
        display.Raise()
        msg = 'Select Point from Plot #%d' % win
        self.write_message(msg)

        now = time.time()
        curhist_name = 'plot%d_cursor_hist' % win
        cursor_hist = getattr(self.larch.symtable._plotter, curhist_name, [])

        self.cursor_dat = dict(relative_e0=relative_e0, opt=opt,
                               callback=callback,
                               start=now, xsel=None, ysel=None,
                               win=win, name=curhist_name,
                               nhist=len(cursor_hist))

        pin_config = self.controller.get_config('pin',
                                                {'style': 'pin first',
                                                 'max_time':15.0,
                                                 'min_time': 2.0})
        if pin_config['style'].startswith('plot'):
            if len(cursor_hist) > 0:
                x, y, t = cursor_hist[0]
                if now < (t + 60.0):
                    self.cursor_dat['xsel'] = x
                    self.cursor_dat['ysel'] = y
                    msg = 'Selected Point at %.1f' % self.cursor_dat['xsel']
                    self.cursor_dat['callback'](**self.cursor_dat)
            else:
                self.write_message('No Points selected from plot window!')
        else: # "pin first" mode
            if len(cursor_hist) > 2:  # purge old cursor history
                setattr(self.larch.symtable._plotter, curhist_name, cursor_hist[:2])

            if len(cursor_hist) > 0:
                x, y, t = cursor_hist[0]
                if now < (t + 30.0):
                    self.cursor_dat['xsel'] = x
                    self.cursor_dat['ysel'] = y
            self.timers['pin'].Start(250)


class XASViewer(LarchWxApp):
    def __init__(self, filename=None, check_version=True, **kws):
        self.filename = filename
        self.check_version = check_version
        LarchWxApp.__init__(self, **kws)

    def createApp(self):
        frame = XASFrame(filename=self.filename,
                         check_version=self.check_version)
        self.SetTopWindow(frame)
        return True

def larix(**kws):
    XASViewer(**kws)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=LARIX_TITLE)
    parser.add_argument(
        '-f', '--filename',
        dest='filename',
        help='data file to load')
    args = parser.parse_args()
    app = XASViewer(**vars(args))
    app.MainLoop()
