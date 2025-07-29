import time
from collections import namedtuple
from pathlib import Path
import numpy as np

import wx
from wxmplot import PlotPanel

from larch.wxlib import (GridPanel, FloatCtrl, set_color, SimpleText,
                         Choice, Check, Button, HLine, OkCancel, LEFT,
                         pack, plotlabels, ReportFrame, DictFrame,
                         FileCheckList, Font, FONTSIZE)

from larch.utils.physical_constants import DEG2RAD, PLANCK_HC

SESSION_PLOTS = {'Normalized \u03BC(E)': 'norm',
                 'Raw \u03BC(E)': 'mu',
                 'k^2\u03c7(k)': 'chikw'}


def fit_dialog_window(dialog, panel):
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, LEFT, 5)
    pack(dialog, sizer)
    dialog.Fit()
    w0, h0 = dialog.GetSize()
    w1, h1 = dialog.GetBestSize()
    dialog.SetSize((max(w0, w1)+25, max(h0, h1)+25))


class EnergyUnitsDialog(wx.Dialog):
    """dialog for selecting, changing energy units, forcing data to eV"""
    unit_choices = ['eV', 'keV', 'deg', 'steps']

    def __init__(self, parent, energy_array, unitname='eV',dspace=1, **kws):

        self.parent = parent
        self.energy = 1.0*energy_array

        title = "Select Energy Units to convert to 'eV'"
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LEFT)

        self.en_units = Choice(panel, choices=self.unit_choices, size=(125, -1),
                               action=self.onUnits)
        self.en_units.SetStringSelection(unitname)
        self.mono_dspace = FloatCtrl(panel, value=dspace, minval=0, maxval=100.0,
                                     precision=6, size=(125, -1))
        self.steps2deg  = FloatCtrl(panel, value=1.0, minval=0,
                                     precision=1, size=(125, -1))

        self.mono_dspace.Disable()
        self.steps2deg.Disable()

        panel.Add(SimpleText(panel, 'Energy Units : '), newrow=True)
        panel.Add(self.en_units)

        panel.Add(SimpleText(panel, 'Mono D spacing : '), newrow=True)
        panel.Add(self.mono_dspace)

        panel.Add(SimpleText(panel, 'Mono Steps per Degree : '), newrow=True)
        panel.Add(self.steps2deg)
        panel.Add((5, 5))

        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()

        fit_dialog_window(self, panel)


    def onUnits(self, event=None):
        units = self.en_units.GetStringSelection()
        self.steps2deg.Enable(units == 'steps')
        self.mono_dspace.Enable(units in ('steps', 'deg'))

    def GetResponse(self, master=None, gname=None, ynorm=True):
        self.Raise()
        response = namedtuple('EnergyUnitsResponse',
                              ('ok', 'units', 'energy', 'dspace'))
        ok, units, en, dspace = False, 'eV', None, -1

        if self.ShowModal() == wx.ID_OK:
            units = self.en_units.GetStringSelection()
            if units == 'eV':
                en = self.energy
            elif units == 'keV':
                en = self.energy * 1000.0
            elif units in ('steps', 'deg'):
                dspace = float(self.mono_dspace.GetValue())
                if units == 'steps':
                    self.energy /= self.steps2deg.GetValue()
                en = PLANCK_HC/(2*dspace*np.sin(self.energy * DEG2RAD))
            ok = True
        return response(ok, units, en, dspace)

class MergeDialog(wx.Dialog):
    """dialog for merging groups"""
    ychoices = ['raw mu(E)', 'normalized mu(E)']

    def __init__(self, parent, groupnames, outgroup='merge', **kws):
        title = "Merge %i Selected Groups" % (len(groupnames))
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LEFT)

        self.master_group = Choice(panel, choices=groupnames, size=(250, -1))
        self.yarray_name  = Choice(panel, choices=self.ychoices, size=(250, -1))
        self.group_name   = wx.TextCtrl(panel, -1, outgroup,  size=(250, -1))

        panel.Add(SimpleText(panel, 'Match Energy to : '), newrow=True)
        panel.Add(self.master_group)

        panel.Add(SimpleText(panel, 'Array to merge  : '), newrow=True)
        panel.Add(self.yarray_name)

        panel.Add(SimpleText(panel, 'New group name  : '), newrow=True)
        panel.Add(self.group_name)

        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()
        fit_dialog_window(self, panel)


    def GetResponse(self, master=None, gname=None, ynorm=True):
        self.Raise()
        response = namedtuple('MergeResponse', ('ok', 'master', 'ynorm', 'group'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            master= self.master_group.GetStringSelection()
            ynorm = 'norm' in self.yarray_name.GetStringSelection().lower()
            gname = self.group_name.GetValue()
            ok = True
        return response(ok, master, ynorm, gname)


class ExportCSVDialog(wx.Dialog):
    """dialog for exporting groups to CSV file"""

    def __init__(self, parent, groupnames, **kws):
        title = "Export Selected Groups"
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)
        self.SetFont(Font(FONTSIZE))
        self.xchoices = {'Energy': 'energy',
                         'k': 'k',
                         'R': 'r',
                         'q': 'q'}

        self.ychoices = {'normalized mu(E)': 'norm',
                         'raw mu(E)': 'mu',
                         'flattened mu(E)': 'flat',
                         'd mu(E) / dE': 'dmude',
                         'chi(k)': 'chi',
                         'chi(E)': 'chie',
                         'chi(q)': 'chiq',
                         '|chi(R)|': 'chir_mag',
                         'Re[chi(R)]': 'chir_re'}

        self.delchoices = {'comma': ',',
                           'space': ' ',
                           'tab': '\t'}

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LEFT)
        self.save_individual_files = Check(panel, default=False, label='Save individual files', action=self.onSaveIndividualFiles)
        self.master_group = Choice(panel, choices=groupnames, size=(200, -1))
        self.xarray_name  = Choice(panel, choices=list(self.xchoices.keys()), size=(200, -1))
        self.yarray_name  = Choice(panel, choices=list(self.ychoices.keys()), action=self.onYChoice, size=(200, -1))
        self.del_name     = Choice(panel, choices=list(self.delchoices.keys()), size=(200, -1))

        panel.Add(self.save_individual_files, newrow=True)

        panel.Add(SimpleText(panel, 'Group for Energy Array: '), newrow=True)
        panel.Add(self.master_group)

        panel.Add(SimpleText(panel, 'X Array to Export: '), newrow=True)
        panel.Add(self.xarray_name)

        panel.Add(SimpleText(panel, 'Y Array to Export: '), newrow=True)
        panel.Add(self.yarray_name)

        panel.Add(SimpleText(panel, 'Delimeter for File: '), newrow=True)
        panel.Add(self.del_name)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()
        fit_dialog_window(self, panel)

    def onYChoice(self, event=None):
        ychoice = self.yarray_name.GetStringSelection()
        yval = self.ychoices[ychoice]
        xarray = 'Energy'
        if yval in ('chi', 'chiq'):
            xarray = 'k'
        elif yval in ('chir_mag', 'chir_re'):
            xarray = 'R'
        self.xarray_name.SetStringSelection(xarray)

    def onSaveIndividualFiles(self, event=None):
        save_individual = self.save_individual_files.IsChecked()
        self.master_group.Enable(not save_individual)

    def GetResponse(self, master=None, gname=None, ynorm=True):
        self.Raise()
        response = namedtuple('ExportCSVResponse',
                              ('ok', 'individual', 'master', 'xarray', 'yarray', 'delim'))
        ok = False
        individual = master = ''
        xarray, yarray, delim = 'Energy', '', ','
        if self.ShowModal() == wx.ID_OK:
            individual = self.save_individual_files.IsChecked()
            master = self.master_group.GetStringSelection()
            xarray = self.xchoices[self.xarray_name.GetStringSelection()]
            yarray = self.ychoices[self.yarray_name.GetStringSelection()]
            delim  = self.delchoices[self.del_name.GetStringSelection()]
            ok = True
        return response(ok, individual, master, xarray, yarray, delim)

class QuitDialog(wx.Dialog):
    """dialog for quitting, prompting to save project"""

    def __init__(self, parent, message, **kws):
        title = "Quit Larch Larix?"
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title, size=(500, 150))
        self.SetFont(Font(FONTSIZE))
        self.needs_save = True
        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LEFT)

        status, filename, stime = message
        warn_msg = 'All work in this session will be lost!'

        panel.Add((5, 5))
        if len(stime) > 2:
            status = f"{status} at {stime} to file"
            warn_msg = 'Changes made after that will be lost!'

        panel.Add(wx.StaticText(panel, label=status), dcol=2)

        if len(filename) > 0:
            if filename.startswith("'") and filename.endswith("'"):
                filename = filename[1:-1]
            panel.Add((15, 5), newrow=True)
            panel.Add(wx.StaticText(panel, label=filename), dcol=2)

        panel.Add((5, 5), newrow=True)
        panel.Add(wx.StaticText(panel, label=warn_msg), dcol=2)
        panel.Add(HLine(panel, size=(500, 3)), dcol=3, newrow=True)
        panel.Add((5, 5), newrow=True)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()

        fit_dialog_window(self, panel)

    def GetResponse(self):
        self.Raise()
        response = namedtuple('QuitResponse', ('ok',))
        ok = (self.ShowModal() == wx.ID_OK)
        return response(ok,)

class RenameDialog(wx.Dialog):
    """dialog for renaming group"""
    def __init__(self, parent, oldname,  **kws):
        title = "Rename Group %s" % (oldname)
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LEFT)

        self.newname   = wx.TextCtrl(panel, -1, oldname,  size=(250, -1))

        panel.Add(SimpleText(panel, 'Old Name : '), newrow=True)
        panel.Add(SimpleText(panel, oldname))
        panel.Add(SimpleText(panel, 'New Name : '), newrow=True)
        panel.Add(self.newname)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()
        fit_dialog_window(self, panel)


    def GetResponse(self, newname=None):
        self.Raise()
        response = namedtuple('RenameResponse', ('ok', 'newname'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            newname = self.newname.GetValue()
            ok = True
        return response(ok, newname)

class RemoveDialog(wx.Dialog):
    """dialog for removing groups"""
    def __init__(self, parent, grouplist,  **kws):
        title = "Remove %i Selected Group" % len(grouplist)
        self.grouplist = grouplist
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LEFT)

        panel.Add(SimpleText(panel, 'Remove %i Selected Groups?' % (len(grouplist))),
                  newrow=True, dcol=2)

        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()
        fit_dialog_window(self, panel)

    def GetResponse(self, ngroups=None):
        self.Raise()
        response = namedtuple('RemoveResponse', ('ok','ngroups'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            ngroups = len(self.grouplist)
            ok = True
        return response(ok, ngroups)


class LoadSessionDialog(wx.Frame):
    """Read, show data from saved larch session"""

    xasgroups_name = '_xasgroups'
    feffgroups_name = ['_feffpaths', '_feffcache']

    def __init__(self, parent, session, filename, controller, **kws):
        self.parent = parent
        self.session = session
        self.filename = filename
        self.controller = controller
        title = f"Read Larch Session from '{filename}'"
        wx.Frame.__init__(self, parent, wx.ID_ANY, title=title)

        x0, y0 = parent.GetPosition()
        self.SetPosition((x0+450, y0+75))

        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(250)

        leftpanel = wx.Panel(splitter)
        rightpanel = wx.Panel(splitter)

        ltop = wx.Panel(leftpanel)

        sel_none = Button(ltop, 'Select None', size=(100, 30), action=self.onSelNone)
        sel_all  = Button(ltop, 'Select All', size=(100, 30), action=self.onSelAll)
        sel_imp  = Button(ltop, 'Import Selected Data', size=(200, 30),
                          action=self.onImport)

        self.select_imported = sel_imp
        self.grouplist = FileCheckList(leftpanel, select_action=self.onShowGroup)
        set_color(self.grouplist, 'list_fg', bg='list_bg')

        tsizer = wx.GridBagSizer(2, 2)
        tsizer.Add(sel_all, (0, 0), (1, 1), LEFT, 0)
        tsizer.Add(sel_none,  (0, 1), (1, 1), LEFT, 0)
        tsizer.Add(sel_imp,  (1, 0), (1, 2), LEFT, 0)

        pack(ltop, tsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ltop, 0, LEFT|wx.GROW, 1)
        sizer.Add(self.grouplist, 1, LEFT|wx.GROW|wx.ALL, 1)
        pack(leftpanel, sizer)


        panel = GridPanel(rightpanel, ncols=3, nrows=4, pad=2, itemstyle=LEFT)
        self.wids = wids = {}

        symtable = controller.symtable

        self.allgroups = session.symbols.get(self.xasgroups_name, {})
        self.extra_groups = []
        for key, val in session.symbols.items():
            if key == self.xasgroups_name or key in self.feffgroups_name:
                continue
            if key in self.allgroups:
                continue
            if hasattr(val, 'energy') and hasattr(val, 'mu'):
                if key in self.allgroups.keys() or key in self.allgroups.values():
                    continue
                self.allgroups[key] = key
                self.extra_groups.append(key)


        checked = []
        for fname, gname in self.allgroups.items():
            self.grouplist.Append(fname)
            checked.append(fname)

        self.grouplist.SetCheckedStrings(checked)

        group_names = list(self.allgroups.values())
        group_names.append(self.xasgroups_name)
        group_names.extend(self.feffgroups_name)

        wids['view_conf'] = Button(panel, 'Show Session Configuration',
                                     size=(200, 30), action=self.onShowConfig)
        wids['view_cmds'] = Button(panel, 'Show Session Commands',
                                     size=(200, 30), action=self.onShowCommands)

        wids['plotopt'] = Choice(panel, choices=list(SESSION_PLOTS.keys()),
                                 action=self.onPlotChoice, size=(175, -1))

        panel.Add(wids['view_conf'], dcol=1)
        panel.Add(wids['view_cmds'], dcol=1, newrow=False)
        panel.Add(HLine(panel, size=(450, 2)), dcol=3, newrow=True)

        over_msg = 'Importing these Groups/Data will overwrite values in the current session:'
        panel.Add(SimpleText(panel, over_msg), dcol=2, newrow=True)
        panel.Add(SimpleText(panel, "Symbol Name"), dcol=1, newrow=True)
        panel.Add(SimpleText(panel, "Import/Overwrite?"), dcol=1)
        i = 0
        self.overwrite_checkboxes = {}
        for g in self.session.symbols:
            if g not in group_names and hasattr(symtable, g):
                chbox = Check(panel, default=True)
                panel.Add(SimpleText(panel, g),  dcol=1, newrow=True)
                panel.Add(chbox,  dcol=1)
                self.overwrite_checkboxes[g] = chbox

                i += 1

        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(450, 2)), dcol=3, newrow=True)
        panel.Add(SimpleText(panel, 'Plot Type:'), newrow=True)
        panel.Add(wids['plotopt'], dcol=2, newrow=False)
        panel.pack()

        self.plotpanel = PlotPanel(rightpanel, messenger=self.plot_messages)
        self.plotpanel.SetSize((475, 450))
        plotconf = self.controller.get_config('plot')
        self.plotpanel.conf.set_theme(plotconf['theme'])
        self.plotpanel.conf.enable_grid(plotconf['show_grid'])

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 0, LEFT, 2)
        sizer.Add(self.plotpanel, 1, LEFT, 2)

        pack(rightpanel, sizer)

        splitter.SplitVertically(leftpanel, rightpanel, 1)
        self.SetSize((750, 725))

        self.Show()
        self.Raise()

    def plot_messages(self, msg, panel=1):
        pass

    def onSelAll(self, event=None):
        self.grouplist.SetCheckedStrings(list(self.allgroups.keys()))

    def onSelNone(self, event=None):
        self.grouplist.SetCheckedStrings([])

    def onShowGroup(self, event=None):
        """column selections changed calc xplot and yplot"""
        fname = event.GetString()
        gname = self.allgroups.get(fname, None)
        if gname in self.session.symbols:
            self.plot_group(gname, fname)

    def onPlotChoice(self, event=None):
        fname = self.grouplist.GetStringSelection()
        gname = self.allgroups.get(fname, None)
        self.plot_group(gname, fname)

    def plot_group(self, gname, fname):
        grp = self.session.symbols[gname]
        plottype = SESSION_PLOTS.get(self.wids['plotopt'].GetStringSelection(), 'norm')
        xdef = np.zeros(1)
        xplot = getattr(grp, 'energy', xdef)
        yplot = getattr(grp, 'mu', xdef)
        xlabel = plotlabels.energy
        ylabel = plotlabels.mu
        if plottype == 'norm' and hasattr(grp, 'norm'):
            yplot = getattr(grp, 'norm', xdef)
            ylabel = plotlabels.norm
        elif plottype == 'chikw' and hasattr(grp, 'chi'):
            xplot = getattr(grp, 'k', xdef)
            yplot = getattr(grp, 'chi', xdef)
            yplot = yplot*xplot*xplot
            xlabel = plotlabels.chikw.format(2)

        if len(yplot) > 1:
            self.plotpanel.plot(xplot, yplot, xlabel=xlabel,
                                ylabel=ylabel, title=fname)


    def onShowConfig(self, event=None):
        DictFrame(parent=self.parent,
                  data=self.session.config,
                  title=f"Session Configuration for '{self.filename}'")

    def onShowCommands(self, event=None):
        oname = self.filename.replace('.larix', '.lar')
        wildcard='Larch Command Files (*.lar)|*.lar'
        text = '\n'.join(self.session.command_history)
        ReportFrame(parent=self.parent,
                    text=text,
                    title=f"Session Commands from '{self.filename}'",
                    default_filename=oname,
                    wildcard=wildcard)

    def onClose(self, event=None):
        self.Destroy()

    def onImport(self, event=None):
        ignore = []
        for gname, chbox in self.overwrite_checkboxes.items():
            if not chbox.IsChecked():
                ignore.append(gname)

        sel_groups = self.grouplist.GetCheckedStrings()
        for fname, gname in self.allgroups.items():
            if fname not in sel_groups:
                ignore.append(gname)

        fname = Path(self.filename).as_posix()
        if fname.endswith('/'):
            fname = fname[:-1]
        lcmd = [f"load_session('{fname}'"]
        if len(ignore) > 0:
            ignore = repr(ignore)
            lcmd.append(f", ignore_groups={ignore}")
        if len(self.extra_groups) > 0:
            extra = repr(self.extra_groups)
            lcmd.append(f", include_xasgroups={extra}")

        lcmd = ''.join(lcmd) + ')'

        cmds = ["# Loading Larch Session with ", lcmd, '######']

        self.controller.larch.eval('\n'.join(cmds))
        last_fname = None
        xasgroups = getattr(self.controller.symtable, self.xasgroups_name, {})

        new_dtypes = []
        for key, val in xasgroups.items():
            dgroup = self.controller.get_group(val)
            if key not in self.controller.filelist.GetItems():
                self.controller.filelist.Append(key)
                last_fname = key
                dtype = getattr(dgroup, 'datatype', 'xas')
                if dtype is not None and dtype not in new_dtypes:
                    new_dtypes.append(dtype)

        for dtype in new_dtypes:
            pagename = {'xas': 'xasnorm', 'xydata': 'xydata'}.get(dtype, 'xasnorm')
            if pagename not in self.parent.get_panels():
                self.parent.add_analysis_panel(pagename)
            ipag, ppanl = self.parent.get_nbpage(pagename)
            self.parent.nb.SetSelection(ipag)

        self.controller.recentfiles.append((time.time(), self.filename))

        #wx.CallAfter(self.Destroy)
        if last_fname is not None:
            self.parent.ShowFile(filename=last_fname)

        self.Destroy()
