#!/usr/bin/env python
"""
Browse CIF Files, maybe run Feff
"""

import os
import sys
import time
import copy
# from threading import Thread
import numpy as np
np.seterr(all='ignore')
from pathlib import Path
from functools import partial
import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb
from wx.adv import AboutBox, AboutDialogInfo
from matplotlib.ticker import FuncFormatter

from wxmplot import PlotPanel
from xraydb.chemparser import chemparse
from xraydb import atomic_number

import larch
from larch import Group
from larch.xafs import feff8l, feff6l
from larch.xrd.cif2feff import cif_sites
from larch.utils import read_textfile, mkdir
from larch.utils.paths import unixpath
from larch.utils.strutils import fix_filename, unique_name, strict_ascii
from larch.site_config import user_larchdir

from larch.wxlib import (LarchFrame, FloatSpin, EditableListBox,
                         FloatCtrl, SetTip, get_icon, SimpleText, pack,
                         Button, Popup, HLine, FileSave, FileOpen, Choice,
                         Check, MenuItem, CEN, LEFT, FRAMESTYLE,
                         Font, FONTSIZE, flatnotebook, LarchUpdaterDialog,
                         PeriodicTablePanel, FeffResultsPanel, LarchWxApp,
                         ExceptionPopup, set_color)

from larch.xrd import CifStructure, get_amcsd, find_cifs, get_cif, parse_cif_file

LEFT = wx.ALIGN_LEFT
CEN |=  wx.ALL
FNB_STYLE = fnb.FNB_NO_X_BUTTON|fnb.FNB_SMART_TABS
FNB_STYLE |= fnb.FNB_NO_NAV_BUTTONS|fnb.FNB_NODRAG

MAINSIZE = (1150, 650)

class CIFFrame(wx.Frame):
    _about = """Larch Crystallographic Information File Browser
    Data from American Mineralogist Crystal Structure Database

    Matt Newville <newville @ cars.uchicago.edu>
    """

    def __init__(self, parent=None, _larch=None, with_feff=False,
                 with_fdmnes=False, usecif_callback=None, path_importer=None,
                 filename=None, **kws):

        wx.Frame.__init__(self, parent, -1, size=MAINSIZE, style=FRAMESTYLE)

        title = "Larch American Mineralogist CIF Browser"
        self.with_feff = with_feff
        self.with_fdmnes = with_fdmnes
        self.usecif_callback = usecif_callback
        self.larch = _larch
        if _larch is None:
            self.larch = larch.Interpreter()
        self.larch.eval("# started CIF browser\n")

        self.path_importer = path_importer
        self.cifdb = get_amcsd()
        self.all_minerals = self.cifdb.all_minerals()
        self.subframes = {}
        self.has_xrd1d = False
        self.xrd1d_thread = None
        self.current_cif = None
        self.SetTitle(title)
        self.SetSize(MAINSIZE)
        self.SetFont(Font(FONTSIZE))

        self.createMainPanel()
        self.createMenus()

        if with_feff:
            self.larch.eval("if not hasattr('_sys', '_feffruns'): _sys._feffruns = {}")
            self.feff_folder = unixpath(Path(user_larchdir, 'feff'))
            mkdir(self.feff_folder)
            self.feffruns_list = []
            for fname in os.listdir(self.feff_folder):
                full = Path(self.feff_folder, fname).absolute()
                if full.is_dir():
                    self.feffruns_list.append(fname)

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

        leftpanel = wx.Panel(splitter, size=(375, -1))
        self.ciflist = EditableListBox(leftpanel, self.onShowCIF, size=(375, -1))
        set_color(self.ciflist, 'list_fg', bg='list_bg')
        self.cif_selections = {}

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ciflist, 1, LEFT|wx.GROW|wx.ALL, 1)
        pack(leftpanel, sizer)

        # right hand side
        rightpanel = scrolled.ScrolledPanel(splitter)
        panel = wx.Panel(rightpanel, size=(725, -1))

        self.ciflist.SetMinSize((375, 250))
        rightpanel.SetMinSize((400, 250))

        sizer = wx.GridBagSizer(2, 2)

        self.title = SimpleText(panel, 'Search American Mineralogical CIF Database:',
                                size=(700, -1), style=LEFT)
        self.title.SetFont(Font(FONTSIZE+2))
        wids = self.wids = {}

        minlab = SimpleText(panel, ' Mineral Name: ')
        minhint= SimpleText(panel, ' example: hem* ')
        wids['mineral'] = wx.TextCtrl(panel, value='',   size=(250, -1),
                                      style=wx.TE_PROCESS_ENTER)
        wids['mineral'].Bind(wx.EVT_TEXT_ENTER, self.onSearch)

        authlab = SimpleText(panel, ' Author Name: ')
        wids['author'] = wx.TextCtrl(panel, value='',   size=(250, -1),
                                     style=wx.TE_PROCESS_ENTER)
        wids['author'].Bind(wx.EVT_TEXT_ENTER, self.onSearch)

        journlab = SimpleText(panel, ' Journal Name: ')
        wids['journal'] = wx.TextCtrl(panel, value='',   size=(250, -1),
                                      style=wx.TE_PROCESS_ENTER)
        wids['journal'].Bind(wx.EVT_TEXT_ENTER, self.onSearch)

        elemlab = SimpleText(panel, ' Include Elements: ')
        elemhint= SimpleText(panel, ' example: O, Fe, Si ')

        wids['contains_elements'] = wx.TextCtrl(panel, value='', size=(250, -1),
                                                style=wx.TE_PROCESS_ENTER)
        wids['contains_elements'].Bind(wx.EVT_TEXT_ENTER, self.onSearch)

        exelemlab = SimpleText(panel, ' Exclude Elements: ')
        wids['excludes_elements'] = wx.TextCtrl(panel, value='', size=(250, -1),
                                                style=wx.TE_PROCESS_ENTER)
        wids['excludes_elements'].Bind(wx.EVT_TEXT_ENTER, self.onSearch)

        wids['excludes_elements'].Enable()
        wids['strict_contains'] = Check(panel, default=False,
                                       label='Include only the elements listed',
                                       action=self.onStrict)

        wids['full_occupancy'] = Check(panel, default=False,
                                       label='Only Structures with Full Occupancy')

        wids['search']   = Button(panel, 'Search for CIFs',  action=self.onSearch)


        ir = 0
        sizer.Add(self.title,     (0, 0), (1, 6), LEFT, 2)

        ir += 1
        sizer.Add(HLine(panel, size=(650, 2)), (ir, 0), (1, 6), LEFT, 3)

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

        #
        if self.with_feff:
            wids['feff_runfolder'] = wx.TextCtrl(panel, value='calc1', size=(250, -1))
            wids['feff_runbutton'] = Button(panel, ' Run Feff ', action=self.onRunFeff)
            wids['feff_runbutton'].Disable()
            wids['feff_without_h'] = Check(panel, default=True, label='Remove H atoms',
                                           action=self.onGetFeff)


            wids['feff_central_atom'] = Choice(panel, choices=['<empty>'], size=(80, -1),
                                          action=self.onFeffCentralAtom)
            wids['feff_edge']         = Choice(panel, choices=['K', 'L3', 'L2', 'L1',
                                                          'M5', 'M4'],
                                          size=(80, -1),
                                          action=self.onGetFeff)

            wids['feffvers']      = Choice(panel, choices=['6', '8'], default=1,
                                           size=(80, -1),
                                          action=self.onGetFeff)
            wids['feff_site']         = Choice(panel, choices=['1', '2', '3', '4'],
                                          size=(80, -1),
                                          action=self.onGetFeff)
            wids['feff_cluster_size'] = FloatSpin(panel, value=7.0, digits=2,
                                             increment=0.1, max_val=10,
                                             action=self.onGetFeff)
            wids['feff_central_atom'].Disable()
            wids['feff_edge'].Disable()
            wids['feff_cluster_size'].Disable()

            ir += 1
            sizer.Add(HLine(panel, size=(650, 2)), (ir, 0), (1, 6), LEFT, 3)

            ir += 1

            sizer.Add(SimpleText(panel, ' Absorbing Atom: '),  (ir, 0), (1, 1), LEFT, 3)
            sizer.Add(wids['feff_central_atom'], (ir, 1), (1, 1), LEFT, 3)
            sizer.Add(SimpleText(panel, ' Crystal Site: '), (ir, 2), (1, 1), LEFT, 3)
            sizer.Add(wids['feff_site'],     (ir, 3), (1, 1), LEFT, 3)
            sizer.Add(SimpleText(panel, ' Edge: '),  (ir, 4), (1, 1), LEFT, 3)
            sizer.Add(wids['feff_edge'],     (ir, 5), (1, 1), LEFT, 3)

            ir += 1
            sizer.Add(SimpleText(panel, ' Cluster Size (\u212B): '),  (ir, 0), (1, 1), LEFT, 3)
            sizer.Add(wids['feff_cluster_size'], (ir, 1), (1, 1), LEFT, 3)
            sizer.Add(SimpleText(panel, ' Feff Version:'),     (ir, 2), (1, 1), LEFT, 3)
            sizer.Add(wids['feffvers'],     (ir, 3), (1, 1), LEFT, 3)
            sizer.Add(wids['feff_without_h'],    (ir, 4), (1, 2), LEFT, 3)

            ir += 1
            sizer.Add(SimpleText(panel, ' Feff Folder: '),      (ir, 0), (1, 1), LEFT, 3)
            sizer.Add(wids['feff_runfolder'],    (ir, 1), (1, 4), LEFT, 3)
            sizer.Add(wids['feff_runbutton'],      (ir, 5), (1, 1), LEFT, 3)

        if self.usecif_callback is not None:
            wids['cif_use_button'] = Button(panel, ' Use This CIF', action=self.onUseCIF)
            wids['cif_use_button'].Disable()

            ir += 1
            sizer.Add(wids['cif_use_button'],    (ir, 5), (1, 1), LEFT, 3)


        ir += 1
        sizer.Add(HLine(panel, size=(650, 2)), (ir, 0), (1, 6), LEFT, 3)

        pack(panel, sizer)

        self.nb = flatnotebook(rightpanel, {}, on_change=self.onNBChanged)


        def _swallow_plot_messages(s, panel=0):
            pass

        self.plotpanel = PlotPanel(rightpanel, messenger=_swallow_plot_messages)
        try:
            plotopts = self.larch.symtable._sys.wx.plotopts
            self.plotpanel.conf.set_theme(plotopts['theme'])
            self.plotpanel.conf.enable_grid(plotopts['show_grid'])
        except:
            pass

        self.plotpanel.SetMinSize((250, 250))
        self.plotpanel.SetMaxSize((675, 400))
        self.plotpanel.onPanelExposed = self.showXRD1D

        cif_panel = wx.Panel(rightpanel)
        wids['cif_text'] = wx.TextCtrl(cif_panel, value='<CIF TEXT>',
                                       style=wx.TE_MULTILINE|wx.TE_READONLY,
                                       size=(700, 450))
        wids['cif_text'].SetFont(Font(FONTSIZE+1))
        cif_sizer = wx.BoxSizer(wx.VERTICAL)
        cif_sizer.Add(wids['cif_text'], 0, LEFT, 1)
        pack(cif_panel, cif_sizer)


        self.nbpages = []
        for label, page in (('CIF Text',  cif_panel),
                            ('1-D XRD Pattern', self.plotpanel),
                            ):
            self.nb.AddPage(page, label, True)
            self.nbpages.append((label, page))

        if self.with_feff:
            self.feffresults = FeffResultsPanel(rightpanel,
                                                path_importer=self.path_importer,
                                                _larch=self.larch)

            feffinp_panel = wx.Panel(rightpanel)
            wids['feff_text'] = wx.TextCtrl(feffinp_panel,
                                           value='<Feff Input Text>',
                                           style=wx.TE_MULTILINE,
                                           size=(700, 450))
            wids['feff_text'].CanCopy()

            feffinp_panel.onPanelExposed = self.onGetFeff
            wids['feff_text'].SetFont(Font(FONTSIZE+1))
            feff_sizer = wx.BoxSizer(wx.VERTICAL)
            feff_sizer.Add(wids['feff_text'], 0, LEFT, 1)
            pack(feffinp_panel, feff_sizer)

            feffout_panel = wx.Panel(rightpanel)
            wids['feffout_text'] = wx.TextCtrl(feffout_panel,
                                               value='<Feff Output>',
                                               style=wx.TE_MULTILINE,
                                               size=(700, 450))
            wids['feffout_text'].CanCopy()
            wids['feffout_text'].SetFont(Font(FONTSIZE+1))
            feffout_sizer = wx.BoxSizer(wx.VERTICAL)
            feffout_sizer.Add(wids['feffout_text'], 0, LEFT, 1)
            pack(feffout_panel, feffout_sizer)

            for label, page in (('Feff Input Text', feffinp_panel),
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
        rightpanel.SetupScrolling()
        splitter.SplitVertically(leftpanel, rightpanel, 1)


    def get_nbpage(self, name):
        "get nb page by name"
        name = name.lower()
        for i, dat in enumerate(self.nbpages):
            label, page = dat
            if name in label.lower():
                return i, page
        return (0, self.nbpages[0][1])

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
                cid = cif.ams_id
                label = f'{label}: {mineral}, {year} {journal} [{cid}]'
            except:
                label = None
            if label is not None:
                if label in self.cif_selections:
                    lorig, n = label, 1
                    while label in self.cif_selections and n < 10:
                        n += 1
                        label = f'{lorig} (v{n})'

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

        if self.with_feff:
            elems =  chemparse(cif.formula.replace(' ', ''))
            self.wids['feff_central_atom'].Enable()
            self.wids['feff_edge'].Enable()
            self.wids['feff_cluster_size'].Enable()

            self.wids['feff_central_atom'].Clear()
            self.wids['feff_central_atom'].AppendItems(list(elems.keys()))
            self.wids['feff_central_atom'].Select(0)

            el0 = list(elems.keys())[0]
            edge_val = 'K' if atomic_number(el0) < 60 else 'L3'
            self.wids['feff_edge'].SetStringSelection(edge_val)

            sites = cif_sites(cif.ciftext, absorber=el0)
            try:
                sites = ['%d' % (i+1) for i in range(len(sites))]
            except:
                title = "Could not make sense of atomic sites"
                message = [f"Elements: {list(elems.keys())}",
                           f"Sites: {sites}"]
                ExceptionPopup(self, title, message)

            self.wids['feff_site'].Clear()
            self.wids['feff_site'].AppendItems(sites)
            self.wids['feff_site'].Select(0)

        if self.usecif_callback is not None:
            self.wids['cif_use_button'].Enable()

        i, p = self.get_nbpage('CIF Text')
        self.nb.SetSelection(i)

    def onUseCIF(self, event=None):
        if self.usecif_callback is not None:
            self.usecif_callback(cif=self.current_cif)


    def onFeffCentralAtom(self, event=None):
        cif  = self.current_cif
        if cif is None:
            return
        catom = event.GetString()
        try:
            sites = cif_sites(cif.ciftext, absorber=catom)
            sites = ['%d' % (i+1) for i in range(len(sites))]
            self.wids['feff_site'].Clear()
            self.wids['feff_site'].AppendItems(sites)
            self.wids['feff_site'].Select(0)
        except:
            self.write_message(f"could not get sites for central atom '{catom}'")
            title = f"Could not get sites for central atom '{catom}'"
            message = []
            ExceptionPopup(self, title, message)

        edge_val = 'K' if atomic_number(catom) < 60 else 'L3'
        self.wids['feff_edge'].SetStringSelection(edge_val)
        self.onGetFeff()

    def onGetFeff(self, event=None):
        cif  = self.current_cif
        if cif is None or not self.with_feff:
            return

        edge  = self.wids['feff_edge'].GetStringSelection()
        version8 = '8' == self.wids['feffvers'].GetStringSelection()
        catom = self.wids['feff_central_atom'].GetStringSelection()
        asite = int(self.wids['feff_site'].GetStringSelection())
        csize = self.wids['feff_cluster_size'].GetValue()
        with_h = not self.wids['feff_without_h'].IsChecked()
        mineral = cif.get_mineralname()
        folder = f'{catom:s}{asite:d}_{edge:s}_{mineral}_cif{cif.ams_id:d}'
        folder = unique_name(fix_filename(folder), self.feffruns_list)

        fefftext = cif.get_feffinp(catom, edge=edge, cluster_size=csize,
                                   absorber_site=asite, version8=version8,
                                   with_h=with_h)

        self.wids['feff_runfolder'].SetValue(folder)
        self.wids['feff_text'].SetValue(fefftext)
        self.wids['feff_runbutton'].Enable()
        i, p = self.get_nbpage('Feff Input')
        self.nb.SetSelection(i)

    def onRunFeff(self, event=None):
        fefftext = self.wids['feff_text'].GetValue()
        if len(fefftext) < 100 or 'ATOMS' not in fefftext or not self.with_feff:
            return

        ciftext = self.wids['cif_text'].GetValue()
        cif  = self.current_cif
        cif_fname = None
        if cif is not None and len(ciftext) > 100:
            mineral = cif.get_mineralname()
            cif_fname = f'{mineral}_cif{cif.ams_id:d}.cif'

        # cc = self.current_cif
        # edge  = self.wids['feff_edge'].GetStringSelection()
        # catom = self.wids['feff_central_atom'].GetStringSelection()
        # asite = int(self.wids['feff_site'].GetStringSelection())
        # mineral = cc.get_mineralname()
        # folder = f'{catom:s}{asite:d}_{edge:s}_{mineral}_cif{cc.ams_id:d}'
        # folder = unixpath(Path(self.feff_folder, folder))
        version8 = '8' == self.wids['feffvers'].GetStringSelection()

        fname = self.wids['feff_runfolder'].GetValue()
        fname = unique_name(fix_filename(fname), self.feffruns_list)
        self.feffruns_list.append(fname)
        self.folder = folder = unixpath(Path(self.feff_folder, fname))
        mkdir(self.folder)
        ix, p = self.get_nbpage('Feff Output')
        self.nb.SetSelection(ix)

        out = self.wids['feffout_text']
        out.Clear()
        out.SetInsertionPoint(0)
        out.WriteText(f'########\n###\n# Run Feff in folder: {folder}\n')
        out.SetInsertionPoint(out.GetLastPosition())
        out.WriteText('###\n########\n')
        out.SetInsertionPoint(out.GetLastPosition())

        fname = unixpath(Path(folder, 'feff.inp').absolute())
        with open(fname, 'w', encoding=sys.getdefaultencoding()) as fh:
            fh.write(strict_ascii(fefftext))

        if cif_fname is not None:
            cname = unixpath(Path(folder, fix_filename(cif_fname)))
            with open(cname, 'w', encoding=sys.getdefaultencoding()) as fh:
                fh.write(strict_ascii(ciftext))
        wx.CallAfter(self.run_feff, folder, version8=version8)

    def run_feff(self, folder=None, version8=True):
        # print("RUN FEFF ", folder)
        dname = Path(folder).name
        prog, cmd = feff8l, 'feff8l'
        if not version8:
            prog, cmd = feff6l, 'feff6l'
        command = f"{cmd:s}(folder='{folder:s}')"
        self.larch.eval(f"## running Feff as:\n#  {command:s}\n##\n")

        prog(folder=folder, message_writer=self.feff_output)
        self.larch.eval("## gathering results:\n")
        self.larch.eval(f"_sys._feffruns['{dname:s}'] = get_feff_pathinfo('{folder:s}')")
        this_feffrun = self.larch.symtable._sys._feffruns[f'{dname:s}']
        self.feffresults.set_feffresult(this_feffrun)
        ix, p = self.get_nbpage('Feff Results')
        self.nb.SetSelection(ix)

        # clean up unused, intermediate Feff files
        for fname in os.listdir(folder):
            if (fname.endswith('.json') or fname.endswith('.pad') or
                fname.endswith('.bin') or fname.startswith('log') or
                fname in ('chi.dat', 'xmu.dat', 'misc.dat')):
                os.unlink(unixpath(Path(folder, fname).absolute()))

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
        path = unixpath(path)
        if path is not None:
            with open(path, 'w', encoding=sys.getdefaultencoding()) as fh:
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
        path = unixpath(path)
        if path is not None:
            with open(path, 'w', encoding=sys.getdefaultencoding()) as fh:
                fh.write(cc.ciftext)
            self.write_message("Wrote CIF file %s" % path, 0)

    def onImportCIF(self, event=None):
        wildcard = 'CIF files (*.cif)|*.cif|All files (*.*)|*.*'
        path = FileOpen(self, message='Open CIF File',
                        wildcard=wildcard, default_file='My.cif')
        path = unixpath(path)
        if path is not None:
            try:
                cif_data = parse_cif_file(path)
            except:
                title = f"Cannot parse CIF file '{path}'"
                message = [f"Error reading CIF File: {path}"]
                ExceptionPopup(self, title, message)
                return

            try:
                cif_id = self.cifdb.add_ciffile(path)
            except:
                title = f"Cannot add CIF from '{path}' to CIF database"
                message = [f"Error adding CIF File to database: {path}"]
                ExceptionPopup(self, title, message)
                return

            try:
                self.onShowCIF(cif_id=cif_id)
            except:
                title = f"Cannot show CIF from '{path}'"
                message = [f"Error displaying CIF File: {path}"]
                ExceptionPopup(self, title, message)

    def onImportFeff(self, event=None):
        if not self.with_feff:
            return
        wildcard = 'Feff input files (*.inp)|*.inp|All files (*.*)|*.*'
        path = FileOpen(self, message='Open Feff Input File',
                        wildcard=wildcard, default_file='feff.inp')
        path = unixpath(path)
        if path is not None:
            fefftext = None
            fname = Path(path).name
            fname = fname.replace('.inp', '_run')
            fname = unique_name(fix_filename(fname), self.feffruns_list)
            fefftext = read_textfile(path)
            if fefftext is not None:
                self.wids['feff_text'].SetValue(fefftext)
                self.wids['feff_runfolder'].SetValue(fname)
                self.wids['feff_runbutton'].Enable()
                i, p = self.get_nbpage('Feff Input')
                self.nb.SetSelection(i)

    def onFeffFolder(self, eventa=None):
        "prompt for Feff Folder"
        dlg = wx.DirDialog(self, 'Select Main Folder for Feff Calculations',
                           style=wx.DD_DEFAULT_STYLE|wx.DD_CHANGE_DIR)

        dlg.SetPath(self.feff_folder)
        if  dlg.ShowModal() == wx.ID_CANCEL:
            return None
        self.feff_folder = Path(dlg.GetPath()).absolute().as_posix()
        mkdir(self.feff_folder)

    def onNBChanged(self, event=None):
        callback = getattr(self.nb.GetCurrentPage(), 'onPanelExposed', None)
        if callable(callback):
            callback()

    def showXRD1D(self, event=None):
        if self.has_xrd1d or self.current_cif is None:
            return

        def display_xrd1d():
            t0 = time.time()
            sfact = self.current_cif.get_structure_factors()
            try:
                self.cifdb.set_hkls(self.current_cif.ams_id, sfact.hkls)
            except:
                pass

            max_ = sfact.intensity.max()
            mask = np.where(sfact.intensity>max_/10.0)[0]
            qval = sfact.q[mask]
            ival = sfact.intensity[mask]
            ival = ival/(1.0*ival.max())

            def qd_formatter(q, pos):
                qval = float(q)
                dval = '\n[%.2f]' % (2*np.pi/max(qval, 1.e-6))
                return r"%.2f%s" % (qval, dval)

            qd_label = r'$Q\rm\,(\AA^{-1}) \,\> [d \rm\,(\AA)]$'
            title = self.cif_label + '\n' + '(cif %d)' % (self.current_cif.ams_id)
            ppan = self.plotpanel
            ppan.plot(qval, ival, linewidth=0, marker='o', markersize=2,
                      xlabel=qd_label, ylabel='Relative Intensity',
                      title=title, titlefontsize=8, delay_draw=True)

            ppan.axes.bar(qval, ival, 0.1, color='blue')
            ppan.axes.xaxis.set_major_formatter(FuncFormatter(qd_formatter))
            ppan.canvas.draw()
            self.has_xrd1d = True

        display_xrd1d()
#         self.xrd1d_thread = Thread(target=display_xrd1d)
#         self.xrd1d_thread.start()
#         time.sleep(0.25)
#         self.xrd1d_thread.join()


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
