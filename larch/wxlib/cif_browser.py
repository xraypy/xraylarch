#!/usr/bin/env python
"""
Browse CIF Files, maybe run Feff
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
from collections import OrderedDict
import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb
import wx.lib.mixins.inspection
from wx.adv import AboutBox, AboutDialogInfo

from wxmplot import PlotPanel
from xraydb.chemparser import chemparse

import larch
from larch import Group
from larch.xafs import feff6l

from larch.utils.strutils import (file2groupname, unique_name,
                                  common_startstring)

from larch.larchlib import read_workdir, save_workdir, read_config, save_config

from larch.wxlib import (LarchFrame, FloatSpin, EditableListBox, TextCtrl,
                         FloatCtrl, SetTip, get_icon, SimpleText, pack,
                         Button, Popup, HLine, FileSave, FileOpen, Choice,
                         Check, MenuItem, GUIColors, CEN, LEFT, FRAMESTYLE,
                         Font, FONTSIZE, flatnotebook, LarchUpdaterDialog,
                         PeriodicTablePanel)

from larch.wxlib.plotter import _newplot, _plot, last_cursor_pos
from larch.utils import group2dict
from larch.site_config import user_larchdir


from larch.xrd import CifStructure, get_amscifdb, find_cifs, get_cif

from xraydb import (material_mu, xray_edge, materials, add_material,
                    atomic_number, atomic_symbol, xray_line)

LEFT = wx.ALIGN_LEFT
CEN |=  wx.ALL

FNB_STYLE = fnb.FNB_NO_X_BUTTON|fnb.FNB_SMART_TABS
FNB_STYLE |= fnb.FNB_NO_NAV_BUTTONS|fnb.FNB_NODRAG

MAINSIZE = (850, 750)

class CIFFrame(wx.Frame):
    _about = """Larch Crystallographic Information File Browser
    Data from American Mineralogist Crystal Structure Database

    Matt Newville <newville @ cars.uchicago.edu>
    """
    def __init__(self, parent=None, _larch=None, filename=None, **kws):
        wx.Frame.__init__(self, parent, -1, size=MAINSIZE, style=FRAMESTYLE)

        title = "Larch American Mineralogist CIF Browser"

        if not isinstance(parent, LarchFrame):
            self.larch_buffer = LarchFrame(_larch=_larch, is_standalone=False)

        self.larch_buffer.Show()
        self.larch_buffer.Raise()
        self.larch = self.larch_buffer.larchshell

        self.cifdb = get_amscifdb()
        self.all_minerals = self.cifdb.all_minerals()
        self.subframes = {}
        self.plotframe = None
        self.has_xrd1d = False
        self.current_cif = None
        self.SetTitle(title)
        self.SetSize(MAINSIZE)
        self.SetFont(Font(FONTSIZE))
        self.larch_buffer.Hide()
        self.createMainPanel()
        self.createMenus()

        path = os.path.join(user_larchdir, 'feff6')
        if not os.path.exists(path):
            os.makedirs(path, mode=493)
        self.feff6_folder = path

        self.statusbar = self.CreateStatusBar(2, style=wx.STB_DEFAULT_STYLE)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = [" ", ""]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)
        self.Show()

    def createMainPanel(self):
        display0 = wx.Display(0)
        client_area = display0.ClientArea
        xmin, ymin, xmax, ymax = client_area
        xpos = int((xmax-xmin)*0.02) + xmin
        ypos = int((ymax-ymin)*0.04) + ymin
        self.SetPosition((xpos, ypos))

        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(250)

        leftpanel = wx.Panel(splitter)
        self.ciflist = EditableListBox(leftpanel,
                                       self.onShowCIF, size=(300,-1))
        self.cif_selections = {}

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ciflist, 1, LEFT|wx.GROW|wx.ALL, 1)
        pack(leftpanel, sizer)

        # right hand side
        rightpanel = wx.Panel(splitter)
        panel = wx.Panel(rightpanel)
        sizer = wx.GridBagSizer(2,2)

        self.title = SimpleText(panel, 'Search Am Min CIF Database:',
                                size=(250, -1))
        self.title.SetFont(Font(FONTSIZE+2))
        wids = self.wids = {}


        minlab = SimpleText(panel, ' Mineral Name: ')
        minhint= SimpleText(panel, ' example: mag* ')
        wids['mineral'] = TextCtrl(panel, value='',   size=(250, -1),
                                   action=self.onSearch)

        authlab = SimpleText(panel, ' Author Name: ')
        wids['author'] = wx.TextCtrl(panel, value='',   size=(250, -1))

        journlab = SimpleText(panel, ' Journal Name: ')
        wids['journal'] = wx.TextCtrl(panel, value='',   size=(250, -1))

        elemlab = SimpleText(panel, ' Include Elements: ')
        elemhint= SimpleText(panel, ' example: O, Fe, Si ')

        wids['contains_elements'] = wx.TextCtrl(panel, value='', size=(250, -1))

        exelemlab = SimpleText(panel, ' Exclude Elements: ')
        wids['excludes_elements'] = wx.TextCtrl(panel, value='', size=(250, -1))
        wids['excludes_elements'].Enable()
        wids['strict_contains'] = Check(panel, default=False,
                                       label='Include only the elements listed',
                                       action=self.onStrict)

        wids['full_occupancy'] = Check(panel, default=False,
                                       label='Only Structures with Full Occupancy')

        wids['search']   = Button(panel, 'Search for CIFs',  action=self.onSearch)
        wids['get_feff'] = Button(panel, 'Get Feff Input', action=self.onGetFeff)
        wids['run_feff'] = Button(panel, 'Run Feff',       action=self.onRunFeff)

        wids['get_feff'].Disable()
        wids['run_feff'].Disable()

        wids['central_atom'] = Choice(panel, choices=['<empty>'], size=(75, -1),
                                      action=self.onCentralAtom)
        wids['edge']         = Choice(panel, choices=['K', 'L3', 'L2', 'Ldddd1'],
                                      size=(50, -1))

        wids['site']         = Choice(panel, choices=['1', '2', '3', '4'],
                                      size=(50, -1))
        wids['cluster_size'] = FloatSpin(panel, value=7.50, digits=2,
                                         increment=0.1, max_val=10)
        wids['central_atom'].Disable()
        wids['edge'].Disable()
        wids['cluster_size'].Disable()
        catomlab = SimpleText(panel, ' Absorbing Atom: ')
        sitelab  = SimpleText(panel, ' Crystal Site: ')
        edgelab  = SimpleText(panel, ' Edge: ')
        csizelab = SimpleText(panel, ' Cluster Size (\u212B): ')

        ir = 0
        sizer.Add(self.title,     (0, 0), (1, 3), LEFT, 2)

        ir += 1
        sizer.Add(HLine(panel, size=(550, 2)), (ir, 0), (1, 6), LEFT, 3)

        ir += 1
        sizer.Add(minlab,          (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['mineral'], (ir, 1), (1, 3), LEFT, 3)
        sizer.Add(minhint,         (ir, 4), (1, 1), LEFT, 3)
        ir += 1
        sizer.Add(authlab,        (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['author'], (ir, 1), (1, 3), LEFT, 3)

        ir += 1
        sizer.Add(journlab,        (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['journal'], (ir, 1), (1, 3), LEFT, 3)

        ir += 1
        sizer.Add(elemlab,        (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['contains_elements'], (ir, 1), (1, 3), LEFT, 3)
        sizer.Add(elemhint,         (ir, 4), (1, 1), LEFT, 3)

        ir += 1
        sizer.Add(exelemlab,        (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['excludes_elements'], (ir, 1), (1, 3), LEFT, 3)
        ir += 1
        sizer.Add(wids['strict_contains'], (ir, 0), (1, 3), LEFT, 3)

        ir += 1
        sizer.Add(wids['full_occupancy'], (ir, 0), (1, 3), LEFT, 3)

        ir += 1
        sizer.Add(wids['search'], (ir, 0), (1, 2), LEFT, 3)

        ir += 1
        sizer.Add(HLine(panel, size=(550, 2)), (ir, 0), (1, 6), LEFT, 3)

        ir += 1
        sizer.Add(catomlab,             (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['central_atom'], (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(sitelab,              (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(wids['site'],         (ir, 3), (1, 1), LEFT, 3)

        ir += 1
        sizer.Add(csizelab,             (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['cluster_size'], (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(edgelab,              (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(wids['edge'],         (ir, 3), (1, 1), LEFT, 3)

        ir += 1
        sizer.Add(wids['get_feff'],     (ir, 0), (1, 2), LEFT, 3)
        sizer.Add(wids['run_feff'],     (ir, 2), (1, 2), LEFT, 3)

        ir += 1
        sizer.Add(HLine(panel, size=(550, 2)), (ir, 0), (1, 6), LEFT, 3)

        pack(panel, sizer)

        self.nb = flatnotebook(rightpanel, {}, drag_tabs=False,
                               on_change=self.onNBChanged)

        self.plotpanel = PlotPanel(rightpanel)
        self.plotpanel.SetMinSize((250, 250))
        self.plotpanel.onPanelExposed = self.showXRD1D

        cif_panel = wx.Panel(rightpanel)
        wids['cif_text'] = wx.TextCtrl(cif_panel,
                                       value='<CIF TEXT>',
                                       style=wx.TE_MULTILINE|wx.TE_READONLY,
                                       size=(300, 350))
        wids['cif_text'].SetFont(Font(FONTSIZE+1))
        cif_sizer = wx.BoxSizer(wx.VERTICAL)
        cif_sizer.Add(wids['cif_text'], 1, LEFT|wx.GROW, 1)
        pack(cif_panel, cif_sizer)

        feff_panel = wx.Panel(rightpanel)
        wids['feff_text'] = wx.TextCtrl(feff_panel,
                                       value='<FEFF TEXT>',
                                       style=wx.TE_MULTILINE,
                                       size=(300, 350))
        wids['feff_text'].CanCopy()

        feff_panel.onPanelExposed = self.onGetFeff
        wids['feff_text'].SetFont(Font(FONTSIZE+1))
        feff_sizer = wx.BoxSizer(wx.VERTICAL)
        feff_sizer.Add(wids['feff_text'], 1, LEFT|wx.GROW, 1)
        pack(feff_panel, feff_sizer)

        feffout_panel = wx.Panel(rightpanel)
        wids['feffout_text'] = wx.TextCtrl(feffout_panel,
                                           value='<Feff Outpu>',
                                           style=wx.TE_MULTILINE,
                                           size=(300, 350))
        wids['feffout_text'].CanCopy()
        wids['feffout_text'].SetFont(Font(FONTSIZE+1))
        feffout_sizer = wx.BoxSizer(wx.VERTICAL)
        feffout_sizer.Add(wids['feffout_text'], 1, LEFT|wx.GROW, 1)
        pack(feffout_panel, feffout_sizer)

        self.nbpages = []
        for label, page in (('CIF Text',  cif_panel),
                            ('1-D XRD Pattern', self.plotpanel),
                            ('Feff Input Text', feff_panel),
                            ('Feff Output Text', feffout_panel)):
            self.nb.AddPage(page, label, True)
            self.nbpages.append((label, page))
        self.nb.SetSelection(0)

        r_sizer = wx.BoxSizer(wx.VERTICAL)
        r_sizer.Add(panel, 0, LEFT|wx.GROW|wx.ALL)
        r_sizer.Add(self.nb, 1, LEFT|wx.GROW, 2)
        pack(rightpanel, r_sizer)
        splitter.SplitVertically(leftpanel, rightpanel, 1)
        # wx.CallAfter(self.init_larch)

    def get_nbpage(self, name):
        "get nb page by name"
        name = name.lower()
        for i, dat in enumerate(self.nbpages):
            label, page = dat
            if name in label.lower():
                return i, page
        return (0, self.npbages[0][1])

    def onStrict(self, event=None):
        strict = self.wids['strict_contains'].IsChecked()
        self.wids['excludes_elements'].Enable(not strict)

    def onSearch(self, event=None):
        mineral_name = self.wids['mineral'].GetValue().strip()
        if len(mineral_name) < 1:
            mineral_name = None
        author_name = self.wids['author'].GetValue().strip()
        if len(author_name) < 1:
            author_name = None
        journal_name = self.wids['journal'].GetValue().strip()
        if len(journal_name) < 1:
            journal_name = None
        contains_elements = self.wids['contains_elements'].GetValue().strip()
        if len(contains_elements) < 1:
            contains_elements = None
        else:
            contains_elements = [a.strip() for a in contains_elements.split(',')]
        excludes_elements = self.wids['excludes_elements'].GetValue().strip()
        if len(excludes_elements) < 1:
            excludes_elements = None
        else:
            excludes_elements = [a.strip() for a in excludes_elements.split(',')]
        strict_contains = self.wids['strict_contains'].IsChecked()
        full_occupancy = self.wids['full_occupancy'].IsChecked()
        all_cifs = find_cifs(mineral_name=mineral_name,
                             journal_name=journal_name,
                             author_name=author_name,
                             contains_elements=contains_elements,
                             excludes_elements=excludes_elements,
                             strict_contains=strict_contains,
                             full_occupancy=full_occupancy)
        if len(all_cifs) == 0:
            all_cifs = find_cifs(mineral_name=mineral_name + '*',
                                 journal_name=journal_name,
                                 author_name=author_name,
                                 contains_elements=contains_elements,
                                 excludes_elements=excludes_elements,
                                 strict_contains=strict_contains,
                                 full_occupancy=full_occupancy)
        self.cif_selections = {}
        self.ciflist.Clear()
        for cif in all_cifs:
            try:
                label = cif.formula.replace(' ', '')
                mineral = cif.mineral.name
                year = cif.publication.year
                journal= cif.publication.journalname
                label = f'{label}: {mineral}, {year} {journal}'
            except:
                label = None
            if label is not None:
                self.cif_selections[label] =  cif.ams_id
                self.ciflist.Append(label)

    def onShowCIF(self, event=None, cif_id=None):
        if cif_id is not None:
            cif = get_cif(cif_id)
            self.cif_label = '%d' % cif_id
        elif event is not None:
            self.cif_label = event.GetString()
            cif = get_cif(self.cif_selections[self.cif_label])
        self.current_cif = cif
        self.has_xrd1d = False
        self.wids['cif_text'].SetValue(cif.ciftext)
        elems =  chemparse(cif.formula.replace(' ', ''))

        self.wids['central_atom'].Enable()
        self.wids['edge'].Enable()
        self.wids['cluster_size'].Enable()
        self.wids['get_feff'].Enable()

        self.wids['central_atom'].Clear()
        self.wids['central_atom'].AppendItems(list(elems.keys()))
        self.wids['central_atom'].Select(0)

        el0 = list(elems.keys())[0]
        sites = [a for a in cif.atoms_sites if a.startswith(el0)]
        sites = ['%d' % (i+1) for i in range(len(sites))]
        self.wids['site'].Clear()
        self.wids['site'].AppendItems(sites)
        self.wids['site'].Select(0)
        i, p = self.get_nbpage('CIF Text')
        self.nb.SetSelection(i)


    def onCentralAtom(self, event=None):
        elem = event.GetString()
        sites = [a for a in self.current_cif.atoms_sites if a.startswith(elem)]
        sites = ['%d' % (i+1) for i in range(len(sites))]
        self.wids['site'].Clear()
        self.wids['site'].AppendItems(sites)
        self.wids['site'].Select(0)

    def onGetFeff(self, event=None):
        cif   = self.current_cif
        if cif is None:
            return
        edge  = self.wids['edge'].GetStringSelection()
        catom = self.wids['central_atom'].GetStringSelection()
        asite = int(self.wids['site'].GetStringSelection())
        csize = self.wids['cluster_size'].GetValue()

        feff6text = cif.get_feff6inp(catom, edge=edge, cluster_size=csize,
                                     absorber_site=asite)

        self.wids['feff_text'].SetValue(feff6text)
        self.wids['run_feff'].Enable()
        i, p = self.get_nbpage('Feff Input')
        self.nb.SetSelection(i)

    def onRunFeff(self, event=None):
        if self.current_cif is None:
            return
        fefftext = self.wids['feff_text'].GetValue()
        if len(fefftext) < 20:
            return
        cc = self.current_cif
        edge  = self.wids['edge'].GetStringSelection()
        catom = self.wids['central_atom'].GetStringSelection()
        asite = int(self.wids['site'].GetStringSelection())
        dirname = f'{catom:s}{asite:d}_{edge:s}_{cc.mineral.name}_cif{cc.ams_id:d}'
        dirname = os.path.join(self.feff6_folder, dirname)
        if not os.path.exists(dirname):
            os.makedirs(dirname, mode=493)
        ix, p = self.get_nbpage('Feff Output')
        self.nb.SetSelection(ix)

        out = self.wids['feffout_text']
        out.Clear()
        out.SetInsertionPoint(0)
        out.WriteText(f'# Run Feff at {dirname:s}\n')
        out.SetInsertionPoint(out.GetLastPosition())
        out.WriteText('##############\n')
        out.SetInsertionPoint(out.GetLastPosition())

        fname = os.path.join(dirname, 'feff.inp')
        with open(fname, 'w') as fh:
            fh.write(fefftext)
        time.sleep(0.5)
        fthread = Thread(target=feff6l,
                         kwargs=dict(folder=dirname,
                                     message_writer=self.feff_output))
        fthread.start()
        time.sleep(1.0)
        fthread.join()

    def feff_output(self, text):
        out = self.wids['feffout_text']
        ix, p = self.get_nbpage('Feff Output')
        self.nb.SetSelection(ix)
        pos0 = out.GetLastPosition()
        if not text.endswith('\n'):
            text = '%s\n' % text
        out.WriteText(text)
        out.SetInsertionPoint(out.GetLastPosition())
        out.Update()
        out.Refresh()


    def onExportFeff(self, event=None):
        if self.current_cif is None:
            return
        fefftext = self.wids['feff_text'].GetValue()
        if len(fefftext) < 20:
            return
        cc = self.current_cif

        dirname = f'{cc.mineral.name}_cif{cc.ams_id:d}'
        dirname = os.path.join(self.feff6_folder, dirname)
        if not os.path.exists(dirname):
            os.makedirs(dirname, mode=493)
        fname = os.path.join(dirname, 'feff.inp')

        wildcard = 'Feff Inut files (*.inp)|*.inp|All files (*.*)|*.*'
        path = FileSave(self, message='Save Feff File',
                        wildcard=wildcard,
                        default_file=fname)
        if path is not None:
            with open(path, 'w') as fh:
                fh.write(fefftext)
            self.write_message("Wrote Feff file %s" % path, 0)


    def onExportCIF(self, event=None):
        if self.current_cif is None:
            return
        cc = self.current_cif
        fname = f'{cc.mineral.name}_cif{cc.ams_id:d}.cif'
        wildcard = 'CIF files (*.cif)|*.cif|All files (*.*)|*.*'
        path = FileSave(self, message='Save CIF File',
                        wildcard=wildcard,
                        default_file=fname)
        if path is not None:
            with open(path, 'w') as fh:
                fh.write(cc.ciftext)
            self.write_message("Wrote CIF file %s" % path, 0)


    def onImportCIF(self, event=None):
        wildcard = 'CIF files (*.cif)|*.cif|All files (*.*)|*.*'
        path = FileOpen(self, message='Open CIF File',
                        wildcard=wildcard,
                        default_file='My.cif')
        if path is not None:
            try:
                cif_id = self.cifdb.add_ciffile(path)
                self.onShowCIF(cif_id=cif_id)
            except:
                title = "Cannot import CIF from '%s'" % path
                message = "Error reading CIF File: %s\n" % path
                r = Popup(self, message, title)

    def onFeffFolder(self, eventa=None):
        "prompt for Feff Folder"
        dlg = wx.DirDialog(parent, 'Select Main Folder for Feff Calculations',
                           style=wx.DD_DEFAULT_STYLE|wx.DD_CHANGE_DIR)

        dlg.SetPath(self.feff6_folder)
        if  dlg.ShowModal() == wx.ID_CANCEL:
            return None
        path = os.path.abspath(dlg.GetPath())
        if not os.path.exists(path):
            os.makedirs(path, mode=493)
        self.feff6_folder = path



    def onNBChanged(self, event=None):
        callback = getattr(self.nb.GetCurrentPage(), 'onPanelExposed', None)
        if callable(callback):
            callback()

    def showXRD1D(self, event=None):
        if self.has_xrd1d or self.current_cif is None:
            return
        sfact = self.current_cif.get_structure_factors()
        max_ = sfact.intensity.max()
        mask = np.where(sfact.intensity>max_/10.0)[0]
        qval = sfact.q[mask]
        ival = sfact.intensity[mask]
        title = '%s (cif %d)' % (self.cif_label, self.current_cif.ams_id)
        self.plotpanel.plot(qval, ival, linewidth=0, marker='o', markersize=2,
                            xlabel=r'$Q \rm\, (\AA^{-1})$',
                            ylabel='Intensity (arb units)',
                            title=title, titlefontsize=8)
        self.plotpanel.axes.bar(qval, ival, 0.05, color='blue')
        self.plotpanel.canvas.draw()
        self.has_xrd1d = True

    def onSelAll(self, event=None):
        self.controller.filelist.select_all()

    def onSelNone(self, event=None):
        self.controller.filelist.select_none()

    def write_message(self, msg, panel=0):
        """write a message to the Status Bar"""
        self.statusbar.SetStatusText(msg, panel)


    def createMenus(self):
        # ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        group_menu = wx.Menu()
        data_menu = wx.Menu()
        ppeak_menu = wx.Menu()
        m = {}

        MenuItem(self, fmenu, "&Open CIF File\tCtrl+O",
                 "Open CIF File",  self.onImportCIF)

        MenuItem(self, fmenu, "&Save CIF File\tCtrl+S",
                 "Save CIF File",  self.onExportCIF)

        MenuItem(self, fmenu, "Save &Feff6 File\tCtrl+F",
                 "Save Feff6 File",  self.onExportFeff)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "Select Main Feff Folder",
                 "Select Main Folder for running Feff",
                 self.onFeffFolder)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "Quit",  "Exit", self.onClose)

        self.menubar.Append(fmenu, "&File")

        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)

    def onShowLarchBuffer(self, evt=None):
        if self.larch_buffer is None:
            self.larch_buffer = LarchFrame(_larch=self.larch, is_standalone=False)
        self.larch_buffer.Show()
        self.larch_buffer.Raise()

    def onSaveLarchHistory(self, evt=None):
        wildcard = 'Larch file (*.lar)|*.lar|All files (*.*)|*.*'
        path = FileSave(self, message='Save Session History as Larch Script',
                        wildcard=wildcard,
                        default_file='xas_viewer_history.lar')
        if path is not None:
            self.larch._larch.input.history.save(path, session_only=True)
            self.write_message("Wrote history %s" % path, 0)

    def onAbout(self, event=None):
        info = AboutDialogInfo()
        info.SetName('XAS Viewer')
        info.SetDescription('X-ray Absorption Visualization and Analysis')
        info.SetVersion('Larch %s ' % larch.version.__version__)
        info.AddDeveloper('Matthew Newville: newville at cars.uchicago.edu')
        dlg = AboutBox(info)

    def onCheckforUpdates(self, event=None):
        dlg = LarchUpdaterDialog(self, caller='XAS Viewer')
        dlg.Raise()
        dlg.SetWindowStyle(wx.STAY_ON_TOP)
        res = dlg.GetResponse()
        dlg.Destroy()
        if res.ok and res.run_updates:
            from larch.apps import update_larch
            update_larch()
            self.onClose(event=event)

    def onClose(self, event=None):
        self.Destroy()


class CIFViewer(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, filename=None, description='Larch CIF Browser / Feff Runner',
                 version_info=None,  **kws):
        self.filename = filename
        self.description = description
        self.version_info = version_info
        wx.App.__init__(self, **kws)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = CIFFrame(filename=self.filename,
                         version_info=self.version_info)
        self.SetTopWindow(frame)

    def OnInit(self):
        self.createApp()
        return True

def cif_viewer(**kws):
    CIFViewer(**kws)

if __name__ == '__main__':
    CIFViewer().MainLoop()
