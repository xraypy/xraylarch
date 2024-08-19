#!/usr/bin/env python
"""
Read Structure input file, Make Feff input file, and run Feff
"""

import os
import sys
from pathlib import Path
import numpy as np
np.seterr(all='ignore')

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb

from xraydb.chemparser import chemparse
from xraydb import atomic_number

import larch
from larch.xafs import feff8l, feff6l
from larch.utils import unixpath, mkdir, read_textfile
from larch.utils.strutils import fix_filename, unique_name, strict_ascii
from larch.site_config import user_larchdir

from larch.wxlib import (LarchFrame, FloatSpin, EditableListBox,
                         FloatCtrl, SetTip, get_icon, SimpleText, pack,
                         Button, Popup, HLine, FileSave, FileOpen, Choice,
                         Check, MenuItem, CEN, LEFT, FRAMESTYLE,
                         Font, FONTSIZE, flatnotebook, LarchUpdaterDialog,
                         PeriodicTablePanel, FeffResultsPanel, LarchWxApp,
                         ExceptionPopup, set_color)


from larch.xrd import structure2feff

LEFT = wx.ALIGN_LEFT
CEN |=  wx.ALL
FNB_STYLE = fnb.FNB_NO_X_BUTTON|fnb.FNB_SMART_TABS
FNB_STYLE |= fnb.FNB_NO_NAV_BUTTONS|fnb.FNB_NODRAG

MAINSIZE = (850, 750)

class Structure2FeffFrame(wx.Frame):
    _about = """Larch structure browser for generating and running Feff.

    Ryuichi Shimogawa <ryuichi.shimogawa@stonybrook.edu>
    """
    def __init__(self, parent=None, _larch=None, path_importer=None, filename=None, **kws):
        wx.Frame.__init__(self, parent, -1, size=MAINSIZE, style=FRAMESTYLE)

        title = "Larch FEFF Input Generator and FEFF Runner"

        self.larch = _larch
        if _larch is None:
            self.larch = larch.Interpreter()
        self.larch.eval("# started Structure browser\n")
        self.larch.eval("if not hasattr('_sys', '_feffruns'): _sys._feffruns = {}")
        self.path_importer = path_importer
        self.subframes = {}
        self.current_structure = None
        self.SetTitle(title)
        self.SetSize(MAINSIZE)
        self.SetFont(Font(FONTSIZE))
        self.createMainPanel()
        self.createMenus()

        self.feff_folder = Path(user_larchdir, 'feff').as_posix()
        mkdir(self.feff_folder)

        self.runs_list = []
        for fname in os.listdir(self.feff_folder):
            full = Path(self.feff_folder, fname).absolute()
            if full.is_dir():
                self.runs_list.append(full.name)

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

        # main panel with scrolled panel
        scrolledpanel = scrolled.ScrolledPanel(self)
        panel = wx.Panel(scrolledpanel)
        sizer = wx.GridBagSizer(2,2)

        wids = self.wids = {}

        folderlab = SimpleText(panel, ' Feff Folder: ')
        wids['run_folder'] = wx.TextCtrl(panel, value='calc1', size=(250, -1))

        wids['run_feff'] = Button(panel, ' Run Feff ',
                                  action=self.onRunFeff)
        wids['run_feff'].Disable()
        wids['without_h'] = Check(panel, default=True, label='Remove H atoms',
                                  action=self.onGetFeff)


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

        ir = 1

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
        sizer.Add(wids['without_h'],    (ir, 4), (1, 2), LEFT, 3)

        ir += 1
        sizer.Add(folderlab,             (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(wids['run_folder'],    (ir, 1), (1, 4), LEFT, 3)
        sizer.Add(wids['run_feff'],      (ir, 5), (1, 1), LEFT, 3)

        pack(panel, sizer)

        self.nb = flatnotebook(scrolledpanel, {}, on_change=self.onNBChanged)

        self.feffresults = FeffResultsPanel(scrolledpanel,
                                            path_importer=self.path_importer,
                                            _larch=self.larch)

        structure_panel = wx.Panel(scrolledpanel)
        wids['structure_text'] = wx.TextCtrl(structure_panel, value='<STRUCTURE TEXT>',
                                       style=wx.TE_MULTILINE|wx.TE_READONLY,
                                       size=(300, 350))
        wids['structure_text'].SetFont(Font(FONTSIZE+1))
        structure_sizer = wx.BoxSizer(wx.VERTICAL)
        structure_sizer.Add(wids['structure_text'], 1, LEFT|wx.GROW, 1)
        pack(structure_panel, structure_sizer)

        feff_panel = wx.Panel(scrolledpanel)
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

        feffout_panel = wx.Panel(scrolledpanel)
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
        for label, page in (('Structure Text',  structure_panel),
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
        pack(scrolledpanel, r_sizer)
        scrolledpanel.SetupScrolling()

    def get_nbpage(self, name):
        "get nb page by name"
        name = name.lower()
        for i, dat in enumerate(self.nbpages):
            label, page = dat
            if name in label.lower():
                return i, page
        return (0, self.npbages[0][1])

    def onCentralAtom(self, event=None):
        structure  = self.current_structure
        if structure is None:
            return
        catom = event.GetString()
        try:
            sites = structure2feff.structure_sites(structure['structure_text'], absorber=catom, fmt=structure['fmt'])
            sites = ['%d' % (i+1) for i in range(len(sites))]
            self.wids['site'].Clear()
            self.wids['site'].AppendItems(sites)
            self.wids['site'].Select(0)
        except:
            self.write_message(f"could not get sites for central atom '{catom}'")
            title = f"Could not get sites for central atom '{catom}'"
            message = []
            ExceptionPopup(self, title, message)

        edge_val = 'K' if atomic_number(catom) < 60 else 'L3'
        self.wids['edge'].SetStringSelection(edge_val)
        self.onGetFeff()

    def onGetFeff(self, event=None):
        structure  = self.current_structure
        if structure is None:
            return
        edge  = self.wids['edge'].GetStringSelection()
        version8 = '8' == self.wids['feffvers'].GetStringSelection()
        catom = self.wids['central_atom'].GetStringSelection()
        asite = int(self.wids['site'].GetStringSelection())
        csize = self.wids['cluster_size'].GetValue()
        with_h = not self.wids['without_h'].IsChecked()
        folder = f'{catom:s}{asite:d}_{edge:s}'
        folder = unique_name(fix_filename(folder), self.runs_list)

        fefftext = structure2feff.structure2feffinp(structure['structure_text'], catom, edge=edge,
                                                    cluster_size=csize,
                                                    absorber_site=asite,
                                                    version8=version8,
                                                    with_h=with_h,
                                                    fmt=structure['fmt'])

        self.wids['run_folder'].SetValue(folder)
        self.wids['feff_text'].SetValue(fefftext)
        self.wids['run_feff'].Enable()
        i, p = self.get_nbpage('Feff Input')
        self.nb.SetSelection(i)

    def onRunFeff(self, event=None):
        fefftext = self.wids['feff_text'].GetValue()
        if len(fefftext) < 100 or 'ATOMS' not in fefftext:
            return

        structure_text = self.wids['structure_text'].GetValue()
        structure  = self.current_structure
        structure_fname = None

        if structure is not None:
            structure_fname = structure['fname']

        version8 = '8' == self.wids['feffvers'].GetStringSelection()

        fname = self.wids['run_folder'].GetValue()
        fname = unique_name(fix_filename(fname), self.runs_list)
        self.runs_list.append(fname)
        folder = Path(self.feff_folder, fname).absolute()
        mkdir(folder)

        ix, p = self.get_nbpage('Feff Output')
        self.nb.SetSelection(ix)

        self.folder = folder.as_posix()
        out = self.wids['feffout_text']
        out.Clear()
        out.SetInsertionPoint(0)
        out.WriteText(f'########\n###\n# Run Feff in folder: {folder:s}\n')
        out.SetInsertionPoint(out.GetLastPosition())
        out.WriteText('###\n########\n')
        out.SetInsertionPoint(out.GetLastPosition())

        fname = Path(folder, 'feff.inp').absolute()
        with open(fname, 'w', encoding=sys.getdefaultencoding()) as fh:
            fh.write(strict_ascii(fefftext))

        if structure_fname is not None:
            cname = Path(folder, structure_fname).absolute()
            with open(cname, 'w', encoding=sys.getdefaultencoding()) as fh:
                fh.write(strict_ascii(structure_text))

        wx.CallAfter(self.run_feff, self.folder, version8=version8)

    def run_feff(self, folder, version8=True):
        folder = Path(folder).absolute()
        dname = folder.name
        prog, cmd = feff8l, 'feff8l'
        if not version8:
            prog, cmd = feff6l, 'feff6l'
        command = f"{cmd:s}(folder='{folder}')"
        self.larch.eval(f"## running Feff as:\n#  {command:s}\n##\n")

        prog(folder=folder.as_posix(), message_writer=self.feff_output)
        self.larch.eval("## gathering results:\n")
        self.larch.eval(f"_sys._feffruns['{dname}'] = get_feff_pathinfo('{folder}')")
        this_feffrun = self.larch.symtable._sys._feffruns[f'{dname}']
        self.feffresults.set_feffresult(this_feffrun)
        ix, p = self.get_nbpage('Feff Results')
        self.nb.SetSelection(ix)

        # clean up unused, intermediate Feff files
        for fname in os.listdir(folder):
            if (fname.endswith('.json') or fname.endswith('.pad') or
                fname.endswith('.bin') or fname.startswith('log') or
                fname in ('chi.dat', 'xmu.dat', 'misc.dat')):
                os.unlink(Path(folder, fname).absolute())

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
        if self.current_structure is None:
            return
        fefftext = self.wids['feff_text'].GetValue()
        if len(fefftext) < 20:
            return
        cc = self.current_structure
        fname = f'{cc["fname"]}_feff.inp'
        wildcard = 'Feff Inut files (*.inp)|*.inp|All files (*.*)|*.*'
        path = FileSave(self, message='Save Feff File',
                        wildcard=wildcard,
                        default_file=fname)
        if path is not None:
            with open(path, 'w', encoding=sys.getdefaultencoding()) as fh:
                fh.write(fefftext)
            self.write_message("Wrote Feff file %s" % path, 0)

    def onExportStructure(self, event=None):
        if self.current_structure is None:
            return

        cc = self.current_structure
        fname = cc["fname"]
        wildcard = f'Sturcture files (*.{cc["fmt"]})|*.{cc["fmt"]}|All files (*.*)|*.*'
        path = FileSave(self, message='Save Structure File',
                        wildcard=wildcard,
                        default_file=fname)

        if path is not None:
            with open(path, 'w', encoding=sys.getdefaultencoding()) as fh:
                fh.write(cc['structure_text'])
            self.write_message("Wrote structure file %s" % path, 0)

    def onImportStructure(self, event=None):
        wildcard = 'Strucuture files (*.cif/*.postcar/*.contcar/*.chgcar/*locpot/*.cssr)|*.cif;*.postcar;*.contcar;*.chgcar;*locpot;*.cssr|Molecule files (*.xyz/*.gjf/*.g03/*.g09/*.com/*.inp)|*.xyz;*.gjf;*.g03;*.g09;*.com;*.inp|All other files readable with Openbabel (*.*)|*.*'
        path = FileOpen(self, message='Open Structure File',
                        wildcard=wildcard, default_file='My.cif')

        if path is not None:
            fmt = path.split('.')[-1]
            fname = Path(path).name
            with open(path, 'r', encoding=sys.getdefaultencoding()) as f:
                structure_text = f.read()

            self.current_structure = structure2feff.parse_structure(structure_text=structure_text, fmt=fmt, fname=fname)

        self.wids['structure_text'].SetValue(self.current_structure['structure_text'])

        # use pytmatgen to get formula
        elems =  chemparse(self.current_structure['formula'].replace(' ', ''))

        self.wids['central_atom'].Enable()
        self.wids['edge'].Enable()
        self.wids['cluster_size'].Enable()

        self.wids['central_atom'].Clear()
        self.wids['central_atom'].AppendItems(list(elems.keys()))
        self.wids['central_atom'].Select(0)



        el0 = list(elems.keys())[0]
        edge_val = 'K' if atomic_number(el0) < 60 else 'L3'
        self.wids['edge'].SetStringSelection(edge_val)

        # sites
        sites = structure2feff.structure_sites(self.current_structure['structure_text'], fmt=self.current_structure["fmt"], absorber=el0)
        try:
            sites = ['%d' % (i+1) for i in range(len(sites))]
        except:
            title = "Could not make sense of atomic sites"
            message = [f"Elements: {list(elems.keys())}",
                       f"Sites: {sites}"]
            ExceptionPopup(self, title, message)


        self.wids['site'].Clear()
        self.wids['site'].AppendItems(sites)
        self.wids['site'].Select(0)
        i, p = self.get_nbpage('Structure Text')
        self.nb.SetSelection(i)

    def onImportFeff(self, event=None):
        wildcard = 'Feff input files (*.inp)|*.inp|All files (*.*)|*.*'
        path = FileOpen(self, message='Open Feff Input File',
                        wildcard=wildcard, default_file='feff.inp')
        if path is not None:
            fefftext = None
            fname = Path(path).name.replace('.inp', '_run')
            fname = unique_name(fix_filename(fname), self.runs_list)
            fefftext = read_textfile(path)
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
        self.feff_folder = Path(dlg.GetPath()).absolute().as_posix()
        mkdir(self.feff_folder)

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

    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        group_menu = wx.Menu()
        data_menu = wx.Menu()
        ppeak_menu = wx.Menu()
        m = {}

        MenuItem(self, fmenu, "&Open Structure File\tCtrl+O",
                 "Open Structure File",  self.onImportStructure)

        MenuItem(self, fmenu, "&Save Structure File\tCtrl+S",
                 "Save Structure File",  self.onExportStructure)

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


class Structure2FeffViewer(LarchWxApp):
    def __init__(self, filename=None, version_info=None,  **kws):
        self.filename = filename
        LarchWxApp.__init__(self, version_info=version_info, **kws)

    def createApp(self):
        frame = Structure2FeffFrame(filename=self.filename,
                         version_info=self.version_info)
        self.SetTopWindow(frame)
        return True

def structure_viewer(**kws):
    Structure2FeffViewer(**kws)

if __name__ == '__main__':
    Structure2FeffViewer().MainLoop()
