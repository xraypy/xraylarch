#!/usr/bin/env python
"""
Browse CIF Files, maybe run Feff
"""

import os
import sys
import time
import copy
import numpy as np
np.seterr(all='ignore')

from functools import partial
import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb
from wx.adv import AboutBox, AboutDialogInfo

from wxmplot import PlotPanel
from xraydb.chemparser import chemparse

import larch
from larch import Group
from larch.xafs import feff8l, feff6l
from larch.xrd.cif2feff import cif_sites
from larch.utils.paths import unixpath
from larch.utils.strutils import fix_filename, unique_name, strict_ascii
from larch.site_config import user_larchdir

from larch.wxlib import (LarchFrame, FloatSpin, EditableListBox,
                         FloatCtrl, SetTip, get_icon, SimpleText, pack,
                         Button, Popup, HLine, FileSave, FileOpen, Choice,
                         Check, MenuItem, GUIColors, CEN, LEFT, FRAMESTYLE,
                         Font, FONTSIZE, flatnotebook, LarchUpdaterDialog,
                         PeriodicTablePanel, FeffResultsPanel, LarchWxApp)


from larch.xrd import CifStructure, get_amscifdb, find_cifs, get_cif

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

        self.larch = _larch
        if _larch is None:
            self.larch = larch.Interpreter()
        self.larch.eval("# started CIF browser\n")
        self.larch.eval("if not hasattr('_main', '_feffruns'): _feffruns = {}")

        self.cifdb = get_amscifdb()
        self.all_minerals = self.cifdb.all_minerals()
        self.subframes = {}
        self.plotframe = None
        self.has_xrd1d = False
        self.current_cif = None
        self.SetTitle(title)
        self.SetSize(MAINSIZE)
        self.SetFont(Font(FONTSIZE))
        self.createMainPanel()
        self.createMenus()

        path = unixpath(os.path.join(user_larchdir, 'feff'))
        if not os.path.exists(path):
            os.makedirs(path, mode=493)
        self.feff_folder = path
        self.runs_list = []
        for fname in os.listdir(self.feff_folder):
            full = os.path.join(self.feff_folder, fname)
            if os.path.isdir(full):
                self.runs_list.append(fname)

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
        xpos = int((xmax-xmin)*0.07) + xmin
        ypos = int((ymax-ymin)*0.09) + ymin
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

        self.title = SimpleText(panel, 'Search American Mineralogical CIF Database:',
                                size=(500, -1), style=LEFT)
        self.title.SetFont(Font(FONTSIZE+2))
        wids = self.wids = {}


        minlab = SimpleText(panel, ' Mineral Name: ')
        minhint= SimpleText(panel, ' example: hem* ')
        wids['mineral'] = wx.TextCtrl(panel, value='',   size=(250, -1),
                                      style=wx.TE_PROCESS_ENTER)
        wids['mineral'].Bind(wx.EVT_TEXT_ENTER, self.onSearch)

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
        # wids['get_feff'] = Button(panel, 'Get Feff Input', action=self.onGetFeff)
        # wids['get_feff'].Disable()

        folderlab = SimpleText(panel, ' Feff Folder: ')
        wids['run_folder'] = wx.TextCtrl(panel, value='calc1', size=(250, -1))

        wids['run_feff'] = Button(panel, ' Run Feff ',
                                  action=self.onRunFeff)
        wids['run_feff'].Disable()

        wids['central_atom'] = Choice(panel, choices=['<empty>'], size=(80, -1),
                                      action=self.onCentralAtom)
        wids['edge']         = Choice(panel, choices=['K', 'L3', 'L2', 'L1',
                                                      'M5', 'M4'],
                                      size=(80, -1),
                                      action=self.onGetFeff)

        wids['feffvers']      = Choice(panel, choices=['6', '8'], default=1,
                                       size=(80, -1),
                                      action=self.onGetFeff)
        wids['site']         = Choice(panel, choices=['1', '2', '3', '4'],
                                      size=(80, -1),
                                      action=self.onGetFeff)
        wids['cluster_size'] = FloatSpin(panel, value=7.0, digits=2,
                                         increment=0.1, max_val=10,
                                         action=self.onGetFeff)
        wids['central_atom'].Disable()
        wids['edge'].Disable()
        wids['cluster_size'].Disable()
        catomlab = SimpleText(panel, ' Absorbing Atom: ')
        sitelab  = SimpleText(panel, ' Crystal Site: ')
        edgelab  = SimpleText(panel, ' Edge: ')
        csizelab = SimpleText(panel, ' Cluster Size (\u212B): ')
        fverslab = SimpleText(panel, ' Feff Version:')

        ir = 0
        sizer.Add(self.title,     (0, 0), (1, 6), LEFT, 2)

        ir += 1
        sizer.Add(HLine(panel, size=(550, 2)), (ir, 0), (1, 6), LEFT, 3)

        ir += 1
        sizer.Add(minlab,          (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['mineral'], (ir, 1), (1, 3), LEFT, 3)
        sizer.Add(minhint,         (ir, 4), (1, 2), LEFT, 3)
        ir += 1
        sizer.Add(authlab,        (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['author'], (ir, 1), (1, 3), LEFT, 3)

        ir += 1
        sizer.Add(journlab,        (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['journal'], (ir, 1), (1, 3), LEFT, 3)

        ir += 1
        sizer.Add(elemlab,        (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['contains_elements'], (ir, 1), (1, 3), LEFT, 3)
        sizer.Add(elemhint,         (ir, 4), (1, 3), LEFT, 2)

        ir += 1
        sizer.Add(exelemlab,        (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['excludes_elements'], (ir, 1), (1, 3), LEFT, 3)

        ir += 1
        sizer.Add(wids['search'],          (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['strict_contains'], (ir, 1), (1, 4), LEFT, 3)

        ir += 1
        sizer.Add(wids['full_occupancy'], (ir, 1), (1, 4), LEFT, 3)

        ir += 1
        sizer.Add(HLine(panel, size=(550, 2)), (ir, 0), (1, 6), LEFT, 3)

        ir += 2

        sizer.Add(catomlab,             (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['central_atom'], (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(sitelab,              (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(wids['site'],         (ir, 3), (1, 1), LEFT, 3)
        sizer.Add(edgelab,              (ir, 4), (1, 1), LEFT, 3)
        sizer.Add(wids['edge'],         (ir, 5), (1, 1), LEFT, 3)

        ir += 1
        sizer.Add(csizelab,             (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['cluster_size'], (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(fverslab,             (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(wids['feffvers'],     (ir, 3), (1, 1), LEFT, 3)
        sizer.Add(wids['run_feff'],     (ir, 5), (1, 1), LEFT, 3)

        ir += 1
        sizer.Add(folderlab,             (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['run_folder'],    (ir, 1), (1, 4), LEFT, 3)

        ir += 1
        sizer.Add(HLine(panel, size=(550, 2)), (ir, 0), (1, 6), LEFT, 3)

        pack(panel, sizer)

        self.nb = flatnotebook(rightpanel, {}, drag_tabs=False,
                               on_change=self.onNBChanged)

        self.feffresults = FeffResultsPanel(rightpanel, _larch=self.larch)

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
                                       value='<Feff Input Text>',
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
                                           value='<Feff Output>',
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
                            ('Feff Output Text', feffout_panel),
                            ('Feff Results',    self.feffresults),
                            ):
            self.nb.AddPage(page, label, True)
            self.nbpages.append((label, page))
        self.nb.SetSelection(0)

        r_sizer = wx.BoxSizer(wx.VERTICAL)
        r_sizer.Add(panel, 0, LEFT|wx.GROW|wx.ALL)
        r_sizer.Add(self.nb, 1, LEFT|wx.GROW, 2)
        pack(rightpanel, r_sizer)
        splitter.SplitVertically(leftpanel, rightpanel, 1)

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
            contains_elements = [a.strip().title() for a in contains_elements.split(',')]
        excludes_elements = self.wids['excludes_elements'].GetValue().strip()
        if len(excludes_elements) < 1:
            excludes_elements = None
        else:
            excludes_elements = [a.strip().title() for a in excludes_elements.split(',')]
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
                mineral = cif.get_mineralname()
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
        # self.wids['get_feff'].Enable()

        self.wids['central_atom'].Clear()
        self.wids['central_atom'].AppendItems(list(elems.keys()))
        self.wids['central_atom'].Select(0)

        el0 = list(elems.keys())[0]
        sites = cif_sites(cif.ciftext, absorber=el0)
        sites = ['%d' % (i+1) for i in range(len(sites))]
        self.wids['site'].Clear()
        self.wids['site'].AppendItems(sites)
        self.wids['site'].Select(0)
        i, p = self.get_nbpage('CIF Text')
        self.nb.SetSelection(i)


    def onCentralAtom(self, event=None):
        cif  = self.current_cif
        if cif is None:
            return
        sites = cif_sites(cif.ciftext, absorber=event.GetString())
        sites = ['%d' % (i+1) for i in range(len(sites))]
        self.wids['site'].Clear()
        self.wids['site'].AppendItems(sites)
        self.wids['site'].Select(0)
        self.onGetFeff()

    def onGetFeff(self, event=None):
        cif  = self.current_cif
        if cif is None:
            return
        edge  = self.wids['edge'].GetStringSelection()
        version8 = '8' == self.wids['feffvers'].GetStringSelection()
        catom = self.wids['central_atom'].GetStringSelection()
        asite = int(self.wids['site'].GetStringSelection())
        csize = self.wids['cluster_size'].GetValue()
        mineral = cif.get_mineralname()
        folder = f'{catom:s}{asite:d}_{edge:s}_{mineral}_cif{cif.ams_id:d}'
        folder = unique_name(folder, self.runs_list)

        fefftext = cif.get_feffinp(catom, edge=edge, cluster_size=csize,
                                    absorber_site=asite, version8=version8)

        self.wids['run_folder'].SetValue(folder)
        self.wids['feff_text'].SetValue(fefftext)
        self.wids['run_feff'].Enable()
        i, p = self.get_nbpage('Feff Input')
        self.nb.SetSelection(i)

    def onRunFeff(self, event=None):
        fefftext = self.wids['feff_text'].GetValue()
        if len(fefftext) < 100 or 'ATOMS' not in fefftext:
            return
        # cc = self.current_cif
        # edge  = self.wids['edge'].GetStringSelection()
        # catom = self.wids['central_atom'].GetStringSelection()
        # asite = int(self.wids['site'].GetStringSelection())
        # mineral = cc.get_mineralname()
        # folder = f'{catom:s}{asite:d}_{edge:s}_{mineral}_cif{cc.ams_id:d}'
        # folder = unixpath(os.path.join(self.feff_folder, folder))
        version8 = '8' == self.wids['feffvers'].GetStringSelection()

        fname = self.wids['run_folder'].GetValue()
        fname = unique_name(fname, self.runs_list)
        self.runs_list.append(fname)
        folder = unixpath(os.path.join(self.feff_folder, fname))

        if not os.path.exists(folder):
            os.makedirs(folder, mode=493)
        ix, p = self.get_nbpage('Feff Output')
        self.nb.SetSelection(ix)

        self.folder = folder
        out = self.wids['feffout_text']
        out.Clear()
        out.SetInsertionPoint(0)
        out.WriteText(f'########\n###\n# Run Feff in folder: {folder:s}\n')
        out.SetInsertionPoint(out.GetLastPosition())
        out.WriteText('###\n########\n')
        out.SetInsertionPoint(out.GetLastPosition())

        fname = unixpath(os.path.join(folder, 'feff.inp'))
        with open(fname, 'w') as fh:
            fh.write(strict_ascii(fefftext))

        wx.CallAfter(self.run_feff, folder, version8=version8)
        # feffexe, folder=dirname, message_writer=self.feff_output)

    def run_feff(self, folder=None, version8=True):
        _, dname = os.path.split(folder)
        prog, cmd = feff8l, 'feff8l'
        if not version8:
            prog, cmd = feff6l, 'feff6l'
        command = f"{cmd:s}(folder='{folder:s}')"
        self.larch.eval(f"## running Feff as:\n#  {command:s}\n##\n")

        prog(folder=folder, message_writer=self.feff_output)
        self.larch.eval("## gathering results:\n")
        self.larch.eval(f"_feffruns['{dname:s}'] = get_feff_pathinfo('{folder:s}')")
        this_feffrun = self.larch.symtable._feffruns[f'{dname:s}']
        self.feffresults.set_feffresult(this_feffrun)
        ix, p = self.get_nbpage('Feff Results')
        self.nb.SetSelection(ix)

        # clean up unused, intermediate Feff files
        for fname in os.listdir(folder):
            if (fname.endswith('.json') or fname.endswith('.pad') or
                fname.endswith('.bin') or fname.startswith('log') or
                fname in ('chi.dat', 'xmu.dat', 'misc.dat')):
                os.unlink(unixpath(os.path.join(folder, fname)))

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
        minname = cc.get_mineralname()
        fname = f'{minname}_cif{cc.ams_id:d}_feff.inp'
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
        minname = cc.get_mineralname()
        fname = f'{minname}_cif{cc.ams_id:d}.cif'
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


    def onImportFeff(self, event=None):
        wildcard = 'Feff input files (*.inp)|*.inp|All files (*.*)|*.*'
        path = FileOpen(self, message='Open Feff Input File',
                        wildcard=wildcard,
                        default_file='feff.inp')
        if path is not None:
            fefftext = None
            _, fname = os.path.split(path)
            fname = fname.replace('.inp', '_run')
            fname = unique_name(fname, self.runs_list)
            with open(path, 'rb') as fh:
                fefftext = fh.read().decode('utf-8')
            if fefftext is not None:
                self.wids['feff_text'].SetValue(fefftext)
                self.wids['run_folder'].SetValue(fname)
                self.wids['run_feff'].Enable()
                i, p = self.get_nbpage('Feff Input')
                self.nb.SetSelection(i)

    def onFeffFolder(self, eventa=None):
        "prompt for Feff Folder"
        dlg = wx.DirDialog(self, 'Select Main Folder for Feff Calculations',
                           style=wx.DD_DEFAULT_STYLE|wx.DD_CHANGE_DIR)

        dlg.SetPath(self.feff_folder)
        if  dlg.ShowModal() == wx.ID_CANCEL:
            return None
        path = os.path.abspath(dlg.GetPath())
        if not os.path.exists(path):
            os.makedirs(path, mode=493)
        self.feff_folder = path


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

        MenuItem(self, fmenu, "Open Feff Input File",
                 "Open Feff input File",  self.onImportFeff)

        MenuItem(self, fmenu, "Save &Feff Inp File\tCtrl+F",
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

    def onClose(self, event=None):
        self.Destroy()


class CIFViewer(LarchWxApp):
    def __init__(self, filename=None, version_info=None,  **kws):
        self.filename = filename
        LarchWxApp.__init__(self, version_info=version_info, **kws)

    def createApp(self):
        frame = CIFFrame(filename=self.filename,
                         version_info=self.version_info)
        self.SetTopWindow(frame)
        return True

def cif_viewer(**kws):
    CIFViewer(**kws)

if __name__ == '__main__':
    CIFViewer().MainLoop()
