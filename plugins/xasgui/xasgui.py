#!/usr/bin/env python
"""
XANES Data Viewer and Analysis Tool
"""
import os
import sys
import time
import copy
import platform
import numpy as np
np.seterr(all='ignore')

from functools import partial
from collections import OrderedDict
import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection

from wx.richtext import RichTextCtrl

is_wxPhoenix = 'phoenix' in wx.PlatformInfo
is_windows = platform.system().startswith('Windows')



from larch import Interpreter, Group
from larch.utils import index_of
from larch.utils.strutils import file2groupname, unique_name

from larch.larchlib import read_workdir, save_workdir, read_config, save_config

from larch.wxlib import (LarchPanel, LarchFrame, ColumnDataFileFrame,
                         ReportFrame, BitmapButton, FileCheckList,
                         FloatCtrl, SetTip, get_icon)

from larch.wxlib import (SimpleText, pack, Button, Popup, HLine, FileSave,
                         Choice, Check, MenuItem, GUIColors, CEN, RCEN,
                         LCEN, FRAMESTYLE, Font)


from larch.fitting import fit_report

from larch_plugins.std import group2dict

from larch_plugins.wx.plotter import _newplot, _plot, last_cursor_pos
from larch_plugins.wx.athena_importer import AthenaImporter

from larch_plugins.xasgui import (FONTSIZE, FNB_STYLE,
                                  PrePeakPanel, XASNormPanel,
                                  LinearComboPanel, PCAPanel, LASSOPanel,
                                  EXAFSPanel, MergeDialog, RenameDialog,
                                  RemoveDialog, DeglitchDialog,
                                  RebinDataDialog, EnergyCalibrateDialog,
                                  SmoothDataDialog, OverAbsorptionDialog,
                                  DeconvolutionDialog, QuitDialog)

from larch_plugins.io import (read_ascii, read_xdi, read_gsexdi,
                              gsescan_group, fix_varname, groups2csv,
                              is_athena_project, AthenaProject)

from larch_plugins.xafs import pre_edge, pre_edge_baseline

LCEN = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
CEN |=  wx.ALL
FILE_WILDCARDS = "Data Files(*.0*,*.dat,*.xdi,*.prj)|*.0*;*.dat;*.xdi;*.prj|All files (*.*)|*.*"

ICON_FILE = 'larch.ico'
XASVIEW_SIZE = (950, 625)
PLOTWIN_SIZE = (550, 550)

NB_PANELS = (('XAS Normalization', XASNormPanel),
             ('Pre-edge Peaks', PrePeakPanel),
             ('Linear Combos', LinearComboPanel),
             ('PCA',  PCAPanel),
             ('LASSO', LASSOPanel),
             ('EXAFS', EXAFSPanel) )

QUIT_MESSAGE = '''Really Quit? You may want to save your project before quitting.
 This is not done automatically!'''

WX_DEBUG = False

XASGUI_STARTUP = """
# Larch startup for XAS Viewer
def extract_athenagroup(pgroup):
    '''extract xas group from athena group'''
    g = pgroup
    g.datatype = 'xas'
    g.xdat = 1.0*g.energy
    g.ydat = 1.0*g.mu
    g.yerr = 1.0
    g.plot_xlabel = 'energy'
    g.plot_ylabel = 'mu'
    return g
#enddef
"""

"""
### extract group {group:s} from Athena project _prj
{group:s} = _prj.{prjgroup:s}
{group:s}.datatype = 'xas'
{group:s}.xdat = 1.0*{group:s}.energy
{group:s}.ydat = 1.0*{group:s}.mu
{group:s}.yerr = 1.0
{group:s}.plot_ylabel = 'mu'
{group:s}.plot_xlabel = 'energy'

### extract group {group:s} from Athena project _prj
{group:s} = _prj.{prjgroup:s}
{group:s}.datatype = 'xas'
{group:s}.xdat = 1.0*{group:s}.energy
{group:s}.ydat = 1.0*{group:s}.mu
{group:s}.yerr = 1.0
{group:s}.plot_ylabel = 'mu'
{group:s}.plot_xlabel = 'energy'
"""


#############################
## Hack System and Startfile on Windows to
## try to track down weird error of starting
## other applications
import platform

if platform.system() == 'Windows':
    from os import system as os_system
    from os import startfile as os_startfile

    def my_system(command):
        print("#@ os.system: ", command)
        return os_system(command)

    def my_startfile(filepath, operation=None):
        print("#@ os.startfile: ", filepath, operation)
        try:
            if operation is None:
                return os_startfile(filepath)
            else:
                return os_startfile(filepath, operation)
        except WindowsError:
            print("#@ os.startfile failed: ", filepath, operation)


    os.system = my_system
    os.startfile = my_startfile

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

class XASController():
    """
    class hollding the Larch session and doing the
    processing work for Larch XAS GUI
    """
    config_file = 'xas_viewer.conf'
    def __init__(self, wxparent=None, _larch=None):
        self.wxparent = wxparent
        self.larch = _larch
        if self.larch is None:
            self.larch = Interpreter()
        self.filelist = None
        self.file_groups = OrderedDict()
        self.fit_opts = {}
        self.group = None

        self.groupname = None
        self.report_frame = None
        self.symtable = self.larch.symtable

    def init_larch(self):
        fico = self.get_iconfile()

        _larch = self.larch
        _larch.eval(XASGUI_STARTUP)
        old_config = read_config(self.config_file)

        config = self.make_default_config()
        for sname in config:
            if old_config is not None and sname in old_config:
                val = old_config[sname]
                if isinstance(val, dict):
                    config[sname].update(val)
                else:
                    config[sname] = val

        for key, value in config.items():
            setattr(_larch.symtable._sys.xas_viewer, key, value)
        os.chdir(config['workdir'])

    def make_default_config(self):
        """ default config, probably called on first run of program"""
        config = {'chdir_on_fileopen': True,
                  'workdir': os.getcwd()}
        return config

    def get_config(self, key, default=None):
        "get configuration setting"
        confgroup = self.larch.symtable._sys.xas_viewer
        return getattr(confgroup, key, default)

    def save_config(self):
        """save configuration"""
        conf = group2dict(self.larch.symtable._sys.xas_viewer)
        conf.pop('__name__')
        save_config(self.config_file, conf)

    def set_workdir(self):
        self.larch.symtable._sys.xas_viewer.workdir = os.getcwd()

    def show_report(self, fitresult, evt=None):
        shown = False
        try:
            self.report_frame.Raise()
            shown = True
        except:
            del self.report_frame
        if not shown:
            self.report_frame = ReportFrame(self.wxparent)

        model_repr = fitresult.model._reprstring(long=True)
        report = fit_report(fitresult, show_correl=True,
                            min_correl=0.25, sort_pars=True)

        self.report_frame.SetFont(Font(FONTSIZE-1))
        self.report_frame.set_text(report)
        self.report_frame.SetFont(Font(FONTSIZE-1))
        self.report_frame.Raise()

    def get_iconfile(self):
        larchdir = self.symtable._sys.config.larchdir
        return os.path.join(larchdir, 'icons', ICON_FILE)

    def get_display(self, win=1, stacked=False):
        wintitle='Larch XAS Plot Window %i' % win
        # if stacked:
        #     win = 2
        #    wintitle='Larch XAS Plot Window'
        opts = dict(wintitle=wintitle, stacked=stacked, win=win,
                    size=PLOTWIN_SIZE)
        out = self.symtable._plotter.get_display(**opts)
        if win > 1:
            p1 = getattr(self.symtable._plotter, 'plot1', None)
            if p1 is not None:
                try:
                    siz = p1.GetSize()
                    pos = p1.GetPosition()
                    pos[0] += int(siz[0]/4)
                    pos[1] += int(siz[1]/4)
                    out.SetSize(pos)
                    if not stacked:
                        out.SetSize(siz)
                except Exception:
                    pass
        return out

    def get_group(self, groupname=None):
        if groupname is None:
            groupname = self.groupname
            if groupname is None:
                return None
        dgroup = getattr(self.symtable, groupname, None)
        if dgroup is None and groupname in self.file_groups:
            groupname = self.file_groups[groupname]
            dgroup = getattr(self.symtable, groupname, None)
        return dgroup

    def merge_groups(self, grouplist, master=None, yarray='mu', outgroup=None):
        """merge groups"""
        cmd = """%s = merge_groups(%s, master=%s,
        xarray='energy', yarray='%s', kind='cubic', trim=True)"""
        glist = "[%s]" % (', '.join(grouplist))
        outgroup = fix_varname(outgroup.lower())
        if outgroup is None:
            outgroup = 'merged'

        outgroup = unique_name(outgroup, self.file_groups, max=1000)

        cmd = cmd % (outgroup, glist, master, yarray)
        self.larch.eval(cmd)

        if master is None:
            master = grouplist[0]
        this = self.get_group(outgroup)
        master = self.get_group(master)
        if not hasattr(this, 'xasnorm_config'):
            this.xasnorm_config = {}
        this.xasnorm_config.update(master.xasnorm_config)
        this.datatype = master.datatype
        this.xdat = 1.0*this.energy
        this.ydat = 1.0*getattr(this, yarray)
        this.plot_xlabel = 'energy'
        this.plot_ylabel = yarray
        return outgroup

    def copy_group(self, filename, new_filename=None):
        """copy XAS group (by filename) to new group"""
        groupname = self.file_groups[filename]
        if not hasattr(self.larch.symtable, groupname):
            return

        ogroup = self.get_group(groupname)

        ngroup = Group(datatype=ogroup.datatype,
                       copied_from=groupname)

        for attr in dir(ogroup):
            do_copy = True
            if attr in ('xdat', 'ydat', 'i0', 'data' 'yerr',
                        'energy', 'mu'):
                val = getattr(ogroup, attr)*1.0
            elif attr in ('norm', 'flat', 'deriv', 'deconv',
                        'post_edge', 'pre_edge'):
                do_copy = False
            else:
                try:
                    val = copy.deepcopy(getattr(ogroup, attr))
                except ValueError:
                    do_copy = False
            if do_copy:
                setattr(ngroup, attr, val)

        if new_filename is None:
            new_filename = filename + '_1'
        ngroup.filename = unique_name(new_filename, self.file_groups.keys())
        ngroup.groupname = unique_name(groupname, self.file_groups.values())
        setattr(self.larch.symtable, ngroup.groupname, ngroup)
        return ngroup

    def get_cursor(self, win=None):
        """get last cursor from selected window"""
        return last_cursor_pos(win=win, _larch=self.larch)

    def plot_group(self, groupname=None, title=None, plot_yarrays=None,
                   new=True, zoom_out=True, **kws):
        ppanel = self.get_display(stacked=False).panel
        newplot = ppanel.plot
        oplot   = ppanel.oplot
        plotcmd = oplot
        viewlims = ppanel.get_viewlimits()
        if new:
            plotcmd = newplot

        dgroup = self.get_group(groupname)
        if not hasattr(dgroup, 'xdat'):
            print("Cannot plot group ", groupname)

        if ((getattr(dgroup, 'plot_yarrays', None) is None or
             getattr(dgroup, 'energy', None) is None or
             getattr(dgroup, 'mu', None) is None)):
            self.process(dgroup)

        if plot_yarrays is None and hasattr(dgroup, 'plot_yarrays'):
            plot_yarrays = dgroup.plot_yarrays

        popts = kws
        path, fname = os.path.split(dgroup.filename)
        if not 'label' in popts:
            popts['label'] = dgroup.plot_ylabel
        zoom_out = (zoom_out or
                  min(dgroup.xdat) >= viewlims[1] or
                  max(dgroup.xdat) <= viewlims[0] or
                  min(dgroup.ydat) >= viewlims[3] or
                  max(dgroup.ydat) <= viewlims[2])

        if not zoom_out:
            popts['xmin'] = viewlims[0]
            popts['xmax'] = viewlims[1]
            popts['ymin'] = viewlims[2]
            popts['ymax'] = viewlims[3]

        popts['xlabel'] = dgroup.plot_xlabel
        popts['ylabel'] = dgroup.plot_ylabel
        if getattr(dgroup, 'plot_y2label', None) is not None:
            popts['y2label'] = dgroup.plot_y2label

        plot_extras = None
        if new:
            if title is None:
                title = fname
            plot_extras = getattr(dgroup, 'plot_extras', None)

        popts['title'] = title
        if hasattr(dgroup, 'custom_plotopts'):
            popts.update(dgroup.custom_plotopts)

        narr = len(plot_yarrays) - 1
        for i, pydat in enumerate(plot_yarrays):
            yaname, yopts, yalabel = pydat
            popts.update(yopts)
            if yalabel is not None:
                popts['label'] = yalabel
            popts['delay_draw'] = (i != narr)

            plotcmd(dgroup.xdat, getattr(dgroup, yaname), **popts)
            plotcmd = oplot

        if plot_extras is not None:
            axes = ppanel.axes
            for etype, x, y, opts in plot_extras:
                if etype == 'marker':
                    popts = {'marker': 'o', 'markersize': 4,
                             'label': '_nolegend_',
                             'markerfacecolor': 'red',
                             'markeredgecolor': '#884444'}
                    popts.update(opts)
                    axes.plot([x], [y], **popts)
                elif etype == 'vline':
                    popts = {'ymin': 0, 'ymax': 1.0,
                             'color': '#888888'}
                    popts.update(opts)
                    axes.axvline(x, **popts)
        ppanel.canvas.draw()


class XASFrame(wx.Frame):
    _about = """Larch XAS GUI: XAS Visualization and Analysis

    Matt Newville <newville @ cars.uchicago.edu>
    """
    def __init__(self, parent=None, _larch=None, **kws):
        wx.Frame.__init__(self, parent, -1, size=XASVIEW_SIZE, style=FRAMESTYLE)

        self.last_array_sel = {}
        self.paths2read = []

        title = "Larch XAS GUI: XAS Visualization and Analysis"

        self.larch_buffer = parent
        if not isinstance(parent, LarchFrame):
            self.larch_buffer = LarchFrame(_larch=_larch)

        self.larch_buffer.Show()
        self.larch_buffer.Raise()
        self.larch = self.larch_buffer.larchshell
        self.larch.symtable._sys.xas_viewer = Group()

        self.controller = XASController(wxparent=self, _larch=self.larch)
        self.current_filename = None
        self.subframes = {}
        self.plotframe = None
        self.SetTitle(title)
        self.SetSize(XASVIEW_SIZE)

        self.SetFont(Font(FONTSIZE))
        self.larch_buffer.Hide()
        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ["Initializing....", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

    def createMainPanel(self):
        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(250)

        leftpanel = wx.Panel(splitter)
        ltop = wx.Panel(leftpanel)

        def Btn(msg, x, act):
            b = Button(ltop, msg, size=(x, 30),  action=act)
            b.SetFont(Font(FONTSIZE))
            return b

        sel_none = Btn('Select None',   120, self.onSelNone)
        sel_all  = Btn('Select All',    120, self.onSelAll)

        self.controller.filelist = FileCheckList(leftpanel,
                                                 # main=self,
                                                 select_action=self.ShowFile,
                                                 remove_action=self.RemoveFile)

        tsizer = wx.BoxSizer(wx.HORIZONTAL)
        tsizer.Add(sel_all, 1, LCEN|wx.GROW, 1)
        tsizer.Add(sel_none, 1, LCEN|wx.GROW, 1)
        pack(ltop, tsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ltop, 0, LCEN|wx.GROW, 1)
        sizer.Add(self.controller.filelist, 1, LCEN|wx.GROW|wx.ALL, 1)

        pack(leftpanel, sizer)

        # right hand side
        panel = wx.Panel(splitter)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.title = SimpleText(panel, 'initializing...', size=(300, -1))
        self.title.SetFont(Font(FONTSIZE+1))

        ir = 0
        sizer.Add(self.title, 0, LCEN|wx.GROW|wx.ALL, 1)

        self.nb = flat_nb.FlatNotebook(panel, -1, agwStyle=FNB_STYLE)

        self.nb.SetTabAreaColour(wx.Colour(250,250,250))
        self.nb.SetActiveTabColour(wx.Colour(254,254,195))

        self.nb.SetNonActiveTabTextColour(wx.Colour(10,10,128))
        self.nb.SetActiveTabTextColour(wx.Colour(128,0,0))

        self.nb_panels = []
        for name, creator in NB_PANELS:
            _panel = creator(parent=self, controller=self.controller)
            self.nb.AddPage(_panel," %s " % name, True)
            self.nb_panels.append(_panel)

        sizer.Add(self.nb, 1, LCEN|wx.EXPAND, 2)
        self.nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onNBChanged)
        self.nb.SetSelection(0)

        pack(panel, sizer)

        splitter.SplitVertically(leftpanel, panel, 1)
        wx.CallAfter(self.init_larch)

    def onNBChanged(self, event=None):
        idx = self.nb.GetSelection()
        pan = self.nb_panels[idx]

        callback = getattr(pan, 'onPanelExposed', None)
        if callable(callback):
            callback()

    def onSelAll(self, event=None):
        self.controller.filelist.SetCheckedStrings(self.controller.file_groups.keys())

    def onSelNone(self, event=None):
        self.controller.filelist.SetCheckedStrings([])

    def init_larch(self):
        self.SetStatusText('initializing Larch')
        self.title.SetLabel('')

        self.controller.init_larch()

        plotframe = self.controller.get_display(stacked=False)
        xpos, ypos = self.GetPosition()
        xsiz, ysiz = self.GetSize()
        plotframe.SetPosition((xpos+xsiz+5, ypos))

        self.SetStatusText('ready')
        self.Raise()

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def RemoveFile(self, fname=None, **kws):
        if fname is not None:
            s = str(fname)
            if s in self.controller.file_groups:
                group = self.controller.file_groups.pop(s)

    def ShowFile(self, evt=None, groupname=None, process=True,
                 plot=True, **kws):
        filename = None
        if evt is not None:
            filename = str(evt.GetString())

        if groupname is None and filename is not None:
            groupname = self.controller.file_groups[filename]

        if not hasattr(self.larch.symtable, groupname):
            return

        dgroup = self.controller.get_group(groupname)
        if filename is None:
            filename = dgroup.filename
        self.title.SetLabel(filename)
        self.current_filename = filename

        self.controller.group = dgroup
        self.controller.groupname = groupname
        cur_panel = self.nb_panels[self.nb.GetSelection()]
        if process:
            cur_panel.fill_form(dgroup=dgroup)
            cur_panel.process(dgroup=dgroup)
            if plot and hasattr(cur_panel, 'plot'):
                cur_panel.plot(dgroup=dgroup)

    def createMenus(self):
        # ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        #
        fmenu = wx.Menu()
        group_menu = wx.Menu()
        data_menu = wx.Menu()
        ppeak_menu = wx.Menu()
        m = {}

        MenuItem(self, fmenu, "&Open Data File\tCtrl+O",
                 "Open Data File",  self.onReadDialog)

        MenuItem(self, fmenu, "&Save Project\tCtrl+S",
                 "Save Session to Project File",  self.onSaveProject)

        MenuItem(self, fmenu, "Export Selected Groups to Athena Project",
                 "Export Selected Groups to Athena Project",
                 self.onExportAthena)

        MenuItem(self, fmenu, "Export Selected Groups to CSV",
                 "Export Selected Groups to CSV",  self.onExportCSV)

        fmenu.AppendSeparator()

        MenuItem(self, fmenu, 'Show Larch Buffer\tCtrl+L',
                 'Show Larch Programming Buffer',
                 self.onShowLarchBuffer)


        MenuItem(self, fmenu, 'Save History Script\tCtrl+H',
                 'Save History as Larch Script',
                 self.onSaveLarchHistory)

        if WX_DEBUG:
            MenuItem(self, fmenu, "&Inspect \tCtrl+J",
                     " wx inspection tool ",  self.showInspectionTool)

        MenuItem(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)


        MenuItem(self, group_menu, "Copy This Group",
                 "Copy This Group", self.onCopyGroup)

        MenuItem(self, group_menu, "Rename This Group",
                 "Rename This Group", self.onRenameGroup)

        MenuItem(self, group_menu, "Remove Selected Groups",
                 "Remove Selected Group", self.onRemoveGroups)


        MenuItem(self, group_menu, "Merge Selected Groups",
                 "Merge Selected Groups", self.onMergeData)


        MenuItem(self, data_menu, "Deglitch Data",  "Deglitch Data",
                 self.onDeglitchData)

        MenuItem(self, data_menu, "Recalibrate Energy",
                 "Recalibrate Energy",
                 self.onEnergyCalibrateData)

        MenuItem(self, data_menu, "Smooth Data", "Smooth Data",
                 self.onSmoothData)

        MenuItem(self, data_menu, "Rebin Data", "Rebin Data",
                 self.onRebinData)

        MenuItem(self, data_menu, "Deconvolve Data",
                 "Deconvolution of Data",  self.onDeconvolveData)

        MenuItem(self, data_menu, "Correct Over-absorption", "Correct Over-absorption",
                 self.onCorrectOverAbsorptionData)

        MenuItem(self, ppeak_menu, "&Read Fit Model\tCtrl+R",
                 "Read Fit Model from File", self.onLoadFitResult)

        fsave = MenuItem(self, ppeak_menu, "Save Fit Model",
                            "Save Fit Model to File", self.onSaveFitResult)

        fexport = MenuItem(self, ppeak_menu, "Export Data and Fit",
                           "Export Data and Fit",
                           self.onExportFitResult)


        self.afterfit_menus = (fsave, fexport)

        for m in self.afterfit_menus:
            m.Enable(False)

        self.menubar.Append(fmenu, "&File")
        self.menubar.Append(group_menu, "Groups")
        self.menubar.Append(data_menu, "Data")

        self.menubar.Append(ppeak_menu, "PreEdgePeaks")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)

    def onShowLarchBuffer(self, evt=None):
        if self.larch_buffer is None:
            self.larch_buffer = LarchFrame(_larch=self.larch)
        self.larch_buffer.Show()
        self.larch_buffer.Raise()

    def onSaveLarchHistory(self, evt=None):
        wildcard = 'Larch file (*.lar)|*.lar|All files (*.*)|*.*'
        deffile = 'xas_viewer_history.lar'
        dlg = FileSave(self, message='Save Session History File',
                       wildcard=wildcard,
                       defaultFile=deffile,
                       style=wx.FD_SAVE|wx.FD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            fout = os.path.abspath(dlg.GetPath())
            self.larch.input.history.save(fout, session_only=True)
            self.SetStatusText("Wrote %s" % fout, 0)
        dlg.Destroy()

    def onExportCSV(self, evt=None):
        group_ids = self.controller.filelist.GetCheckedStrings()
        savegroups = []
        groupnames = []
        for checked in group_ids:
            groupname = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(groupname)
            savegroups.append(dgroup)
            groupnames.append(groupname)
        if len(savegroups) < 1:
             Popup(self, "No files selected to export to CSV",
                   "No files selected")
             return

        deffile = "%s_%i.csv" % (groupname, len(groupnames))
        wcards  = 'CSV Files (*.csv)|*.cvs|All files (*.*)|*.*'

        outfile = FileSave(self, 'Export Selected Groups to CSV File',
                           default_file=deffile, wildcard=wcards)

        if outfile is None:
            return

        groups2csv(savegroups, outfile, x='energy', y='norm', _larch=self.larch)

    def onExportAthena(self, evt=None):
        groups = []
        for checked in self.controller.filelist.GetCheckedStrings():
            groups.append(self.controller.file_groups[str(checked)])

        if len(groups) < 1:
             Popup(self, "No files selected to export to Athena",
                   "No files selected")
             return
        self.save_athena_project(groups[0], groups, prompt=True)

    def onSaveProject(self, evt=None):
        groups = [gname for gname in self.controller.file_groups]
        if len(groups) < 1:
            Popup(self, "No files selected to export to Athena",
                  "No files selected")
            return
        self.save_athena_project(groups[0], groups, prompt=True)

    def save_athena_project(self, filename, grouplist, prompt=True):
        if len(grouplist) < 1:
            return
        savegroups = [self.controller.get_group(gname) for gname in grouplist]

        deffile = "%s_%i.prj" % (filename, len(grouplist))
        wcards  = 'Athena Projects (*.prj)|*.prj|All files (*.*)|*.*'

        outfile = FileSave(self, 'Save Groups to Athena Project File',
                           default_file=deffile, wildcard=wcards)

        if outfile is None:
            return

        aprj = AthenaProject(filename=outfile, _larch=self.larch)
        for label, grp in zip(grouplist, savegroups):
            aprj.add_group(grp, label=label)

        aprj.save(use_gzip=True)

    def onConfigDataProcessing(self, event=None):
        pass

    def onNewGroup(self, datagroup):
        """
        install and display a new group, as from 'copy / modify'
        Note: this is a group object, not the groupname or filename
        """
        dgroup = datagroup
        self.install_group(dgroup.groupname, dgroup.filename, overwrite=False)
        self.ShowFile(groupname=dgroup.groupname)

    def onCopyGroup(self, event=None):
        fname = self.current_filename
        if fname is None:
            fname = self.controller.filelist.GetStringSelection()
        ngroup = self.controller.copy_group(fname)
        self.onNewGroup(ngroup)

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
            self.controller.file_groups[res.newname] = groupname
            self.controller.filelist.rename_item(self.current_filename, res.newname)
            dgroup = self.controller.get_group(groupname)
            dgroup.filename = self.current_filename = res.newname

            self.controller.filelist.SetCheckedStrings(selected)
            self.controller.filelist.SetStringSelection(res.newname)

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


    def onMergeData(self, event=None):
        groups = []
        for checked in self.controller.filelist.GetCheckedStrings():
            groups.append(self.controller.file_groups[str(checked)])
        if len(groups) < 1:
            return

        outgroup = unique_name('merge', self.controller.file_groups)
        dlg = MergeDialog(self, groups, outgroup=outgroup)
        res = dlg.GetResponse()
        dlg.Destroy()
        if res.ok:
            fname = res.group
            gname = fix_varname(res.group.lower())
            yname = 'norm' if res.ynorm else 'mu'
            self.controller.merge_groups(groups, master=res.master,
                                         yarray=yname, outgroup=gname)
            self.install_group(gname, fname, overwrite=False)
            self.controller.filelist.SetStringSelection(fname)


    def onDeglitchData(self, event=None):
        DeglitchDialog(self, self.controller).Show()

    def onSmoothData(self, event=None):
        SmoothDataDialog(self, self.controller).Show()

    def onRebinData(self, event=None):
        RebinDataDialog(self, self.controller).Show()

    def onCorrectOverAbsorptionData(self, event=None):
        OverAbsorptionDialog(self, self.controller).Show()

    def onEnergyCalibrateData(self, event=None):
        EnergyCalibrateDialog(self, self.controller).Show()

    def onDeconvolveData(self, event=None):
        DeconvolutionDialog(self, self.controller).Show()

    def onConfigDataFitting(self, event=None):
        pass

    def showInspectionTool(self, event=None):
        app = wx.GetApp()
        app.ShowInspectionTool()

    def onAbout(self,evt):
        dlg = wx.MessageDialog(self, self._about,
                               "About Larch XAS GUI",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self, event):
        dlg = QuitDialog(self)
        res = dlg.GetResponse()
        dlg.Destroy()

        if not res.ok:
            return

        if res.save:
            groups = [gname for gname in self.controller.file_groups]
            if len(groups) > 0:
                self.save_athena_project(groups[0], groups, prompt=True)

        self.controller.save_config()
        self.controller.get_display().Destroy()

        if self.larch_buffer is not None:
            try:
                self.larch_buffer.Destroy()
            except:
                pass
            time.sleep(0.05)

        for nam in dir(self.larch.symtable._plotter):
            obj = getattr(self.larch.symtable._plotter, nam)
            time.sleep(0.05)
            try:
                obj.Destroy()
            except:
                pass

        for name, wid in self.subframes.items():
            if wid is not None:
                try:
                    wid.Destroy()
                except:
                    pass

        for nam in dir(self.larch.symtable._sys.wx):
            obj = getattr(self.larch.symtable._sys.wx, nam)

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

    def onSelectColumns(self, event=None):
        dgroup = self.controller.get_group()
        self.show_subframe('readfile', ColumnDataFileFrame,
                           group=dgroup.raw,
                           last_array_sel=self.last_array_sel,
                           _larch=self.larch,
                           read_ok_cb=partial(self.onRead_OK,
                                              overwrite=True))

    def onLoadFitResult(self, event=None):
        self.nb.SetSelection(1)
        self.nb_panels[1].onLoadFitResult(event=event)

    def onSaveFitResult(self, event=None):
        self.nb_panels[1].onSaveFitResult(event=event)

    def onExportFitResult(self, event=None):
        self.nb_panels[1].onExportFitResult(event=event)

    def onReadDialog(self, event=None):
        dlg = wx.FileDialog(self, message="Read Data File",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.FD_OPEN|wx.FD_MULTIPLE)
        self.paths2read = []
        if dlg.ShowModal() == wx.ID_OK:
            self.paths2read = dlg.GetPaths()
        dlg.Destroy()

        if len(self.paths2read) < 1:
            return

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
        filedir, filename = os.path.split(path)
        if self.controller.get_config('chdir_on_fileopen'):
            os.chdir(filedir)
            self.controller.set_workdir()

        # check for athena projects
        if is_athena_project(path):
            kwargs = dict(filename=path,
                          _larch = self.controller.larch,
                          read_ok_cb=self.onReadAthenaProject_OK)
            self.show_subframe('athena_import', AthenaImporter, **kwargs)
        else:
            kwargs = dict(filename=path,
                          _larch=self.larch_buffer.larchshell,
                          last_array_sel = self.last_array_sel,
                          read_ok_cb=self.onRead_OK)

            self.show_subframe('readfile', ColumnDataFileFrame, **kwargs)

    def onReadAthenaProject_OK(self, path, namelist):
        """read groups from a list of groups from an athena project file"""
        self.larch.eval("_prj = read_athena('{path:s}', do_fft=False, do_bkg=False)".format(path=path))
        dgroup = None
        script = "{group:s} = extract_athenagroup(_prj.{prjgroup:s})"
        for gname in namelist:
            this = getattr(self.larch.symtable._prj, gname)
            gid = str(getattr(this, 'athena_id', gname))
            self.larch.eval(script.format(group=gid, prjgroup=gname))
            dgroup = self.install_group(gid, gname, process=True, plot=False)
        self.larch.eval("del _prj")

    def onRead_OK(self, script, path, groupname=None, array_sel=None,
                  overwrite=False):
        """ called when column data has been selected and is ready to be used
        overwrite: whether to overwrite the current datagroup, as when
        editing a datagroup
        """
        abort_read = False
        filedir, filename = os.path.split(path)
        if not overwrite and hasattr(self.larch.symtable, groupname):
            newname = file2groupname(filename, symtable=self.larch.symtable)
            msg = """Warning: groupname '%s' already used.
            Will use groupname '%s' instead """  % (groupname, newname)
            dlg = wx.MessageDialog(self, msg, 'Warning',
                                   wx.OK | wx.CANCEL )

            abort_read = (wx.ID_OK != dlg.ShowModal())
            dlg.Destroy()
            groupname = newname

        if abort_read:
            return
        self.larch.eval(script.format(group=groupname, path=path))
        if array_sel is not None:
            self.last_array_sel = array_sel
        self.install_group(groupname, filename, overwrite=overwrite)

        for path in self.paths2read:
            path = path.replace('\\', '/')
            filedir, filename = os.path.split(path)
            gname = file2groupname(filename, symtable=self.larch.symtable)
            self.larch.eval(script.format(group=gname, path=path))
            self.install_group(gname, filename, overwrite=True)

    def install_group(self, groupname, filename, overwrite=False,
                      process=True, plot=True):
        """add groupname / filename to list of available data groups"""
        thisgroup = getattr(self.larch.symtable, groupname)
        thisgroup.groupname = groupname
        thisgroup.filename = filename

        datatype = getattr(thisgroup, 'datatype', 'raw')
        # file /group may already exist in list
        if filename in self.controller.file_groups and not overwrite:
            for i in range(1, 101):
                ftest = "%s (%i)"  % (filename, i)
                if ftest not in self.controller.file_groups:
                    filename = ftest
                    break

        if filename not in self.controller.file_groups:
            self.controller.filelist.Append(filename)
            self.controller.file_groups[filename] = groupname
        self.nb.SetSelection(0)
        self.ShowFile(groupname=groupname, process=process, plot=plot)
        self.controller.filelist.SetStringSelection(filename)
        return thisgroup


class XASViewer(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, **kws):
        wx.App.__init__(self, **kws)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = XASFrame()
        frame.Show()
        self.SetTopWindow(frame)

    def OnInit(self):
        self.createApp()
        return True

def initializeLarchPlugin(_larch=None):
    """add XAS Frame to _sys.gui_apps """
    if _larch is not None:
        _sys = _larch.symtable._sys
        if not hasattr(_sys, 'gui_apps'):
            _sys.gui_apps = {}
        _sys.gui_apps['xas_viewer'] = ('XAS Visualization and Analysis', XASFrame)

def registerLarchPlugin():
    return ('_sys.wx', {})

if __name__ == "__main__":
    XASViewer().run()
