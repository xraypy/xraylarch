import os
import sys
import time
import logging
import shutil
from datetime import datetime, timedelta
import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv

import larch
from larch.site_config import user_larchdir
from larch.utils import unixpath
from larch.wxlib import (GridPanel, GUIColors, Button, pack, SimpleText,
                         FileOpen, FileSave, Font, LEFT, FRAMESTYLE,
                         FONTSIZE, MenuItem, EditableListBox, OkCancel,
                         FileCheckList, Choice, HLine, ReportFrame, Popup,
                         LarchWxApp)

from larch.xafs import get_feff_pathinfo
from larch.xray import atomic_symbols

ATSYMS = ['< All >'] + atomic_symbols
EDGES  = ['< All >', 'K', 'L3', 'L2', 'L1', 'M5']


LEFT = LEFT|wx.ALL
DVSTYLE = dv.DV_VERT_RULES|dv.DV_ROW_LINES|dv.DV_MULTIPLE

class FeffPathsModel(dv.DataViewIndexListModel):
    def __init__(self, feffpaths, with_use=True):
        dv.DataViewIndexListModel.__init__(self, 0)
        self.data = []
        self.paths = {}
        self.with_use = with_use
        self.feffpaths = feffpaths
        self.read_data()

    def set_data(self, feffpaths):
        self.paths = {}
        self.feffpaths = feffpaths
        self.read_data()

    def read_data(self):
        self.data = []
        if self.feffpaths is None:
            row = ['feffNNNN.dat', '0.0000', '2', '6', '100.0']
            if self.with_use: row.append(False)
            row.append('* -> * -> *')
            self.data.append(row)
        else:
            for fp in self.feffpaths:
                row = [fp.filename, '%.4f' % fp.reff,
                       '%.0f' % fp.nleg, '%.0f' % fp.degeneracy,
                       '%.3f' % fp.cwratio]
                use = False
                if self.with_use:
                    if fp.filename in self.paths:
                        use = self.paths[fp.filename]
                    row.append(use)
                row.append(fp.geom)
                self.data.append(row)
                self.paths[fp.filename] = use
        self.Reset(len(self.data))


    def select_all(self, use=True):
        for pname in self.paths:
            self.paths[pname] = use
        self.read_data()

    def select_above(self, item):
        itemname = self.GetValue(item, 0)
        use = True
        for row in self.data:
            self.paths[row[0]] = use
            if row[0] == itemname:
                use = not use
        self.read_data()

    def GetColumnType(self, col):
        if self.with_use and col == 5:
            return "bool"
        return "string"

    def GetValueByRow(self, row, col):
        return self.data[row][col]

    def SetValueByRow(self, value, row, col):

        self.data[row][col] = value
        return True

    def GetColumnCount(self):
        return len(self.data[0])

    def GetCount(self):
        return len(self.data)

    def GetAttrByRow(self, row, col, attr):
        """set row/col attributes (color, etc)"""
        nleg = self.data[row][2]
        cname = self.data[row][0]
        if nleg == '2':
            attr.SetColour('#000')
            attr.SetBold(False)
            return True
        elif nleg == '3':
            attr.SetColour('#A11')
            attr.SetBold(False)
            return True
        elif nleg == '4':
            attr.SetColour('#11A')
            attr.SetBold(False)
            return True
        else:
            attr.SetColour('#393')
            attr.SetBold(False)
            return True
        return False


class RemoveFeffCalcDialog(wx.Dialog):
    """dialog for removing Feff Calculations"""

    def __init__(self, parent, ncalcs=1, **kws):
        title = "Remove Feff calculations?"
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title, size=(325, 275))
        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LEFT)

        panel.Add(SimpleText(panel, f'Remove {ncalcs:d} Feff calculations?'),
                             dcol=3, newrow=True)
        panel.Add(SimpleText(panel, 'Warning: this cannot be undone!'),
                             dcol=3, newrow=True)
        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(500, 3)), dcol=2, newrow=True)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()

    def GetResponse(self):
        self.Raise()
        return (self.ShowModal() == wx.ID_OK)

class FeffResultsPanel(wx.Panel):
    """ present Feff results """
    def __init__(self, parent=None, feffresult=None, path_importer=None, xasmain=None,
                 _larch=None):
        wx.Panel.__init__(self, parent, -1, size=(650, 650))
        self.parent = parent
        self.xasmain = xasmain
        self.path_importer = path_importer
        self._larch = _larch
        self.feffresult = feffresult
        self.report_frame = None

        self.dvc = dv.DataViewCtrl(self, style=DVSTYLE)
        self.dvc.SetMinSize((600, 350))

        self.model = FeffPathsModel(None, with_use=callable(path_importer))
        self.dvc.AssociateModel(self.model)

        panel = wx.Panel(self)
        # panel.SetBackgroundColour(GUIColors.bg)

        sizer = wx.GridBagSizer(1, 1)

        bkws = dict(size=(175, -1))
        btn_header = Button(panel, "Show Full Header", action=self.onShowHeader, **bkws)
        btn_feffinp = Button(panel, "Show Feff.inp",   action=self.onShowFeffInp, **bkws)

        if callable(self.path_importer):
            btn_import = Button(panel, "Import Paths",     action=self.onImportPath, **bkws)
            btn_above  = Button(panel, "Select All Above Current", action=self.onSelAbove,  **bkws)
            btn_none   = Button(panel, "Select None",      action=self.onSelNone, **bkws)

        opts = dict(size=(400, -1), style=LEFT)
        self.feff_folder = SimpleText(panel, '',  **opts)
        self.feff_datetime = SimpleText(panel, '',**opts)
        self.feff_header = [SimpleText(panel, '', **opts),
                            SimpleText(panel, '', **opts),
                            SimpleText(panel, '', **opts),
                            SimpleText(panel, '', **opts),
                            SimpleText(panel, '', **opts),
                            SimpleText(panel, '', **opts)]


        ir = 0
        sizer.Add(SimpleText(panel, 'Feff Folder:'), (ir, 0), (1, 1),  LEFT, 2)
        sizer.Add(self.feff_folder,                  (ir, 1), (1, 4),  LEFT, 2)
        ir += 1
        sizer.Add(SimpleText(panel, 'Date Run:'),    (ir, 0), (1, 1),  LEFT, 2)
        sizer.Add(self.feff_datetime,                (ir, 1), (1, 5),  LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(panel, 'Header:'),      (ir, 0), (1, 1),  LEFT, 1)
        sizer.Add(self.feff_header[0],               (ir, 1), (1, 5),  LEFT, 1)
        ir += 1
        sizer.Add(SimpleText(panel, ''),             (ir, 0), (1, 1),  LEFT, 1)
        sizer.Add(self.feff_header[1],               (ir, 1), (1, 5),  LEFT, 1)
        ir += 1
        sizer.Add(SimpleText(panel, ''),             (ir, 0), (1, 1),  LEFT, 1)
        sizer.Add(self.feff_header[2],               (ir, 1), (1, 5),  LEFT, 1)
        ir += 1
        sizer.Add(SimpleText(panel, ''),             (ir, 0), (1, 1),  LEFT, 1)
        sizer.Add(self.feff_header[3],               (ir, 1), (1, 5),  LEFT, 1)
        ir += 1
        sizer.Add(SimpleText(panel, ''),             (ir, 0), (1, 1),  LEFT, 1)
        sizer.Add(self.feff_header[4],               (ir, 1), (1, 5),  LEFT, 1)
        ir += 1
        sizer.Add(SimpleText(panel, ''),             (ir, 0), (1, 1),  LEFT, 1)
        sizer.Add(self.feff_header[5],               (ir, 1), (1, 5),  LEFT, 1)

        ir += 1
        sizer.Add(btn_header,      (ir, 0), (1, 2),  LEFT, 2)
        sizer.Add(btn_feffinp,     (ir, 2), (1, 2),  LEFT, 2)

        if callable(self.path_importer):
            ir += 1
            sizer.Add(btn_above,     (ir, 0), (1, 2),  LEFT, 2)
            sizer.Add(btn_none,      (ir, 2), (1, 2),  LEFT, 2)
            sizer.Add(btn_import,    (ir, 4), (1, 2),  LEFT, 2)

        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(600, 2)),(ir, 0), (1, 6),  LEFT, 2)

        pack(panel, sizer)

        columns = [('Feff File',   90, 'text'),
                   ('R (\u212B)',  65, 'text'),
                   ('# legs',      60, 'text'),
                   ('# paths',     65, 'text'),
                   ('Importance',  90, 'text')]
        if callable(self.path_importer):
            columns.append(('Use',     50, 'bool'))
        columns.append(('Geometry',   200, 'text'))

        for icol, dat in enumerate(columns):
             label, width, dtype = dat
             method = self.dvc.AppendTextColumn
             mode = dv.DATAVIEW_CELL_EDITABLE
             if dtype == 'bool':
                 method = self.dvc.AppendToggleColumn
                 mode = dv.DATAVIEW_CELL_ACTIVATABLE
             method(label, icol, width=width, mode=mode)
             c = self.dvc.Columns[icol]
             align = wx.ALIGN_RIGHT if icol in (1, 2, 3, 4) else wx.ALIGN_LEFT
             c.Alignment = c.Renderer.Alignment = align
             c.SetSortable(False)


        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel,    0, LEFT|wx.GROW, 1)
        mainsizer.Add(self.dvc, 1, LEFT|wx.GROW, 1)

        pack(self, mainsizer)
        self.dvc.EnsureVisible(self.model.GetItem(0))

        if feffresult is not None:
            self.set_feffresult(feffresult)

    def onSelAll(self, event=None):
        self.model.select_all(True)

    def onSelNone(self, event=None):
        self.model.select_all(False)

    def onSelAbove(self, event=None):
        if self.dvc.HasSelection():
            self.model.select_above(self.dvc.GetSelection())

    def onShowHeader(self, event=None):
        if self.feffresult is not None:
            self.show_report(self.feffresult.header,
                             title=f'Header for {self.feffresult.folder:s}',
                             default_filename=f'{self.feffresult.folder:s}_header.txt')

    def onShowFeffInp(self, event=None):
        if self.feffresult is not None:
            text = None
            fname = unixpath(os.path.join(self.feffresult.folder, 'feff.inp'))
            if os.path.exists(fname):
                with open(fname, 'rb') as fh:
                    text = fh.read().decode('utf-8')
            else:
                fname = unixpath(os.path.join(user_larchdir, 'feff',
                                              self.feffresult.folder, 'feff.inp'))
                if os.path.exists(fname):
                    with open(fname, 'rb') as fh:
                        text = fh.read().decode('utf-8')
            if text is not None:
                self.show_report(text, title=f'Feff.inp for {self.feffresult.folder:s}',
                                 default_filename=f'{self.feffresult.folder:s}_feff.inp',
                                 wildcard='Input Files (*.inp)|*.inp')

    def show_report(self, text, title='Text', default_filename='out.txt', wildcard=None):
        if wildcard is None:
            wildcard='Text Files (*.txt)|*.txt'
        default_filename = os.path.split(default_filename)[1]
        try:
            self.report_frame.set_text(text)
            self.report_frame.SetTitle(title)
            self.report_frame.default_filename = default_filename
            self.report_frame.wildcard = wildcard
        except:
            self.report_frame = ReportFrame(parent=self,
                                            text=text, title=title,
                                            default_filename=default_filename,
                                            wildcard=wildcard)


    def onImportPath(self, event=None):
        folder  = self.feffresult.folder
        _, fname = os.path.split(folder)
        for data in self.model.data:
            if data[5]:
                self.path_importer(unixpath(os.path.join(folder, data[0])),
                                   self.feffresult)

        self.onSelNone()
        # print(' on import xasmain = ', self.xasmain)
        if self.xasmain is not None:
            self.xasmain.nb.SetSelection(self.xasmain.get_nbpage('feffit')[0])

    def set_feffresult(self, feffresult):
        self.feffresult = feffresult
        self.feff_folder.SetLabel(feffresult.folder)
        self.feff_datetime.SetLabel(feffresult.datetime)
        nhead = len(self.feff_header)

        for i, text in enumerate(feffresult.header.split('\n')[:nhead]):
            self.feff_header[i].SetLabel(text)
        self.model.set_data(feffresult.paths)


class FeffResultsFrame(wx.Frame):
    """ present Feff results """
    def __init__(self,  parent=None, feffresult=None, xasmain=None, _larch=None):
        wx.Frame.__init__(self, parent, -1, size=(850, 650), style=FRAMESTYLE)

        title = "Manage Feff calculation results"
        self.larch = _larch
        if _larch is None:
            self.larch = larch.Interpreter()
        self.larch.eval("# started Feff results browser\n")
        self.larch.eval("if not hasattr('_main', '_feffruns'): _feffruns = {}")
        self.parent = parent
        path_importer = None
        if parent is not None:
            try:
                path_importer = parent.get_nbpage('feffit')[1].add_path
            except:
                pass

        path = unixpath(os.path.join(user_larchdir, 'feff'))
        if not os.path.exists(path):
            os.makedirs(path, mode=493)
        self.feff_folder = path

        self.SetTitle(title)
        self.SetSize((850, 650))
        self.SetFont(Font(FONTSIZE))
        self.createMenus()

        display0 = wx.Display(0)
        client_area = display0.ClientArea
        xmin, ymin, xmax, ymax = client_area
        xpos = int((xmax-xmin)*0.15) + xmin
        ypos = int((ymax-ymin)*0.20) + ymin
        self.SetPosition((xpos, ypos))

        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(250)

        # left hand panel
        lpanel = wx.Panel(splitter)
        ltop = wx.Panel(lpanel)

        def Btn(msg, x, act):
            b = Button(ltop, msg, size=(x, 30),  action=act)
            b.SetFont(Font(FONTSIZE))
            return b

        sel_none = Btn('Select None',   120, self.onSelNone)
        sel_all  = Btn('Select All',    120, self.onSelAll)
        tsizer = wx.BoxSizer(wx.HORIZONTAL)
        tsizer.Add(sel_all, 1, LEFT|wx.GROW, 1)
        tsizer.Add(sel_none, 1, LEFT|wx.GROW, 1)
        pack(ltop, tsizer)

        self.fefflist = FileCheckList(lpanel, select_action=self.onShowFeff,
                                      size=(300, -1))

        lsizer = wx.BoxSizer(wx.VERTICAL)
        lsizer.Add(ltop, 0, LEFT|wx.GROW, 1)
        lsizer.Add(self.fefflist, 1, LEFT|wx.GROW|wx.ALL, 1)
        pack(lpanel, lsizer)

        # right hand side
        panel = wx.Panel(splitter)
        wids = self.wids = {}
        toprow = wx.Panel(panel)

        wids['central_atom'] = Choice(toprow, choices=ATSYMS, size=(100, -1),
                                      action=self.onCentralAtom)
        wids['edge']         = Choice(toprow, choices=EDGES, size=(100, -1),
                                      action=self.onAbsorbingEdge)

        flabel = SimpleText(toprow, 'Filter Calculations by Element and Edge:', size=(275, -1))
        tsizer = wx.BoxSizer(wx.HORIZONTAL)
        tsizer.Add(flabel,               1, LEFT, 2)
        tsizer.Add(wids['central_atom'], 0, LEFT|wx.GROW, 2)
        tsizer.Add(wids['edge'],         0, LEFT|wx.GROW, 2)
        pack(toprow, tsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.feff_panel = FeffResultsPanel(panel, path_importer=path_importer,
                                           xasmain=xasmain, _larch=_larch)
        sizer.Add(toprow, 0, LEFT|wx.GROW|wx.ALL, 2)
        sizer.Add(HLine(panel, size=(550, 2)), 0,  LEFT|wx.GROW|wx.ALL, 2)
        sizer.Add(self.feff_panel, 1, LEFT|wx.GROW|wx.ALL, 2)
        pack(panel, sizer)
        splitter.SplitVertically(lpanel, panel, 1)
        self.Show()
        wx.CallAfter(self.onSearch)

    def onShowFeff(self, event=None):
        fr = self.feffruns.get(self.fefflist.GetStringSelection(), None)
        if fr is not None:
            self.feff_panel.set_feffresult(fr)

    def onSearch(self, event=None):
        catom = self.wids['central_atom'].GetStringSelection()
        edge = self.wids['edge'].GetStringSelection()
        all_catoms = 'All' in catom
        all_edges  = 'All' in edge

        self.fefflist.Clear()
        self.feffruns = {}
        self.larch.eval("## gathering results:\n")
        flist = os.listdir(self.feff_folder)
        flist = sorted(flist, key=lambda t: -os.stat(unixpath(os.path.join(self.feff_folder, t))).st_mtime)

        for path in flist:
            fullpath = unixpath(os.path.join(self.feff_folder, path))
            if os.path.isdir(fullpath):
                try:
                    self.larch.eval(f"_feffruns['{path:s}'] = get_feff_pathinfo('{fullpath:s}')")
                    self.feffruns[path] = thisrun = self.larch.symtable._feffruns[path]
                    if ((all_catoms or (thisrun.absorber == catom)) and
                        (all_edges  or (thisrun.edge == edge))):
                        self.fefflist.Append(path)
                except:
                    print(f"could not read Feff calculation from '{path}'")

    def onCentralAtom(self, event=None):
        self.onSearch()

    def onAbsorbingEdge(self, event=None):
        self.onSearch()

    def onSelAll(self, event=None):
        self.fefflist.select_all()

    def onSelNone(self, event=None):
        self.fefflist.select_none()

    def onRemoveFeffFolders(self, event=None):
        dlg = RemoveFeffCalcDialog(self, ncalcs=len(self.fefflist.GetCheckedStrings()))
        dlg.Raise()
        dlg.SetWindowStyle(wx.STAY_ON_TOP)
        remove = dlg.GetResponse()
        dlg.Destroy()
        if remove:
            for checked in self.fefflist.GetCheckedStrings():
                shutil.rmtree(unixpath(os.path.join(self.feff_folder, checked)))
            self.onSearch()

    def onFeffFolder(self, event=None):
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

    def onImportFeffCalc(self, event=None):
        "prompt to import Feff calculation folder"
        dlg = wx.DirDialog(self, 'Select Folder wth Feff Calculations',
                           style=wx.DD_DEFAULT_STYLE|wx.DD_CHANGE_DIR)

        dlg.SetPath(self.feff_folder)
        if  dlg.ShowModal() == wx.ID_CANCEL:
            return None
        path = os.path.abspath(dlg.GetPath())
        if os.path.exists(path):
            flist = os.listdir(path)
            if ('paths.dat' in flist and 'files.dat' in flist and
                'feff0001.dat' in flist and 'feff.inp' in flist):
                _, dname = os.path.split(path)
                dest = unixpath(os.path.join(self.feff_folder, dname))
                shutil.copytree(path, dest)
                self.onSearch()
            else:
                Popup(self, f"{path:s} is not a complete Feff calculation",
                      "cannot import Feff calculation")

    def createMenus(self):
        # ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()

        MenuItem(self, fmenu, "Rescan Main Feff Folder",
                 "Rescan Feff Folder for Feff calculations",
                 self.onSearch)

        MenuItem(self, fmenu, "Import Feff calculation",
                 "Import other Feff calculation",
                 self.onImportFeffCalc)

        fmenu.AppendSeparator()

        MenuItem(self, fmenu, "Set Main Feff Folder",
                 "Select Main Feff Folder for Feff calculations",
                 self.onFeffFolder)


        MenuItem(self, fmenu, "Remove Selected Feff calculations",
                 "Completely remove Feff calculations",  self.onRemoveFeffFolders)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "Quit",  "Exit", self.onClose)

        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)

    def onClose(self, event=None):
        self.Destroy()


class FeffResultsBrowserApp(LarchWxApp):
    def __init__(self, dat=None,  **kws):
        self.dat = dat
        LarchWxApp.__init__(self, **kws)

    def createApp(self):
        frame = FeffResultsFrame(feffresult=self.dat)
        self.SetTopWindow(frame)
        return True

if __name__ == '__main__':
    dat = None
    FeffResultsBrowserApp(dat).MainLoop()
