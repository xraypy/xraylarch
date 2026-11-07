import os
import sys
import json
import time
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv

from wxutils import get_color
from pyshortcuts import uname
import larch
from larch.site_config import user_larchdir
from larch.utils import unixpath, mkdir, read_textfile

from larch.wxlib import (GridPanel, Button, pack, SimpleText,
                         Font, LEFT,CEN,  FRAMESTYLE,
                         FONTSIZE, MenuItem, EditableListBox, OkCancel,
                         FileCheckList, Choice, HLine, ReportFrame, Popup,
                         PeriodicTablePanel, LarchWxApp)

from larch.xafs import get_feff_pathinfo
from larch.xafs.feffutils import FPathInfo
from larch.utils.physical_constants import ATOM_SYMS

try:
    from feffdb import FeffDatabase
except ImportError:
    FeffDatabase = None

ATSYMS = ['< All Atoms>'] + ATOM_SYMS[:96]
EDGES  = {'< All Edges>': 'All', 'K': 'K', 'L3': 'L3', 'L2':'L2'}
SCATTERERS = {'< All Scatterers>': 'All', 'oxygen only': 'Only_O', 'no oxygen': 'No_O'}


LEFT = LEFT|wx.ALL
DVSTYLE = dv.DV_VERT_RULES|dv.DV_ROW_LINES|dv.DV_MULTIPLE


class FeffDBPathsModel(dv.DataViewIndexListModel):
    def __init__(self, feffpaths, with_use=True):
        dv.DataViewIndexListModel.__init__(self, 0)
        self.data = []
        self.paths = {}
        self.with_use = with_use
        self.feffpaths = feffpaths
        self.read_data()

    def set_data(self, feffpaths):
        self.feffpaths = feffpaths
        self.read_data()

    def read_data(self):
        self.data = []
        self.paths = {}
        if self.feffpaths is None:
            row = ['', '', '0.000', '2', '6', '-', False]
            self.data.append(row)
        else:
            for path in self.feffpaths:
                desc = path['compound']
                if desc.startswith('<missing'):
                    desc = path['formula']
                reff  = path['reff']
                degen = path['degen']
                geom  = path['geometry']
                label = path['label']
                use = False
                if label in self.paths:
                    use = self.paths[label]

                self.data.append([label,
                                  path['scatterer'],
                                  f'{reff:.3f}',
                                  f'{len(geom):d}',
                                  f'{degen}',
                                  desc, use])
                self.paths[label] = use
        self.Reset(len(self.data))


    def select_all(self, use=True):
        for pname in self.paths:
            self.paths[pname] = use
        self.read_data()


    def GetColumnType(self, col):
        if self.with_use and col == 6:
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
        return False



class FeffDBFrame(wx.Frame):
    """ Feff DB interface"""
    def __init__(self,  parent=None, path_importer=None, feffdb=None, _larch=None):
        wx.Frame.__init__(self, parent, -1, size=(900, 650), style=FRAMESTYLE)
        self.path_importer = path_importer
        title = "FeffDB Path Browser"
        self.larch = _larch
        self.feffdb = feffdb
        if self.feffdb is None and FeffDatabase is not None:
            self.feffdb = FeffDatabase()

        self.elem = None
        self.edge = None
        self.scatterer = None

        if _larch is None:
            self.larch = larch.Interpreter()

        if not hasattr(self.larch.symtable._sys, '_feffruns'):
            self.larch.symtable._sys._feffruns = {}
        self.parent = parent

        self.SetTitle(title)
        self.SetSize((700, 600))
        self.SetFont(Font(FONTSIZE))
        # self.createMenus()

        panel = GridPanel(self)
        wids = self.wids = {}

        wids['dvc'] = dv.DataViewCtrl(panel, style=DVSTYLE)
        wids['dvc'].SetMinSize((690, 300))

        self.model = FeffDBPathsModel(None, with_use=callable(path_importer))
        wids['dvc'].AssociateModel(self.model)

        toplabel = SimpleText(panel, 'Select Absorbing Atom from Periodic Table:',
                              size=(375, -1))


        pfont = 13 if uname=='darwin' else 11

        wids['ptable'] = PeriodicTablePanel(panel, multi_select=False,
                                            fontsize=pfont,
                                            size=(375, 200),
                                            onselect=self.onElement)


        def Btn(msg, action, wid=175):
            b = Button(panel, msg, size=(wid, -1),  action=action)
            b.SetFont(Font(FONTSIZE))
            return b

        wids['feffinp'] = Btn("Show Feff.inp", self.onShowFeffInp)
        wids['ciffile'] = Btn("Show CIF File", self.onShowCIFFile)

        if callable(self.path_importer):
            wids['import'] = Btn("Import Selected Paths", self.onImportPath)
            wids['selnone']   = Btn("Select None",   self.onSelNone)


        panel.Add(toplabel,  dcol=3, style=CEN|wx.GROW)

        # edge radio button
        edgepan = wx.Panel(panel)
        btnsizer = wx.BoxSizer(wx.VERTICAL)
        btnsizer.Add(SimpleText(edgepan, 'Edges'))

        style = wx.RB_GROUP
        iset = False
        for label in EDGES:
            rb = wx.RadioButton(edgepan, -1, f' {label} ', style=style|wx.ALIGN_LEFT)
            rb.Bind(wx.EVT_RADIOBUTTON, self.onEdge)
            style = 0
            if not iset:
                iset = True
                rb.SetValue(1)
            btnsizer.Add(rb)
        # wids['rb_edge_All'].SetValue(1)
        pack(edgepan, btnsizer)

        # scatterer radio button
        scatpan = wx.Panel(panel)
        btnsizer = wx.BoxSizer(wx.VERTICAL)
        btnsizer.Add(SimpleText(scatpan, 'Scatterers'))

        style = wx.RB_GROUP
        iset = False
        for label in SCATTERERS:
            rb = wx.RadioButton(scatpan, -1, f' {label} ', style=style|wx.ALIGN_LEFT)
            rb.Bind(wx.EVT_RADIOBUTTON, self.onScatterer)
            style = 0
            if not iset:
                iset = True
                rb.SetValue(1)
            btnsizer.Add(rb)
        pack(scatpan, btnsizer)

        panel.Add(wids['ptable'], dcol=3, drow=3, style=CEN, newrow=True)
        panel.Add(edgepan,    icol=3, irow=1, dcol=1, drow=1, style=LEFT)
        panel.Add(scatpan,    icol=3, irow=2, dcol=1, drow=1, style=LEFT)
        panel.irow = 4
        panel.Add(HLine(panel, size=(600, 3)), dcol=5, newrow=True)

        panel.Add(wids['feffinp'], newrow=True)
        panel.Add(wids['ciffile'])

        if callable(self.path_importer):
            panel.Add(wids['import'])
            panel.Add(wids['selnone'])

        panel.Add(HLine(panel, size=(600, 3)), dcol=5, newrow=True)

        columns = [('Label',        90, 'text'),
                   ('Scatterer',    90, 'text'),
                   ('R (\u212B)',   60, 'text'),
                   ('# legs',       50, 'text'),
                   ('# paths',      60, 'text'),
                   ('Description', 150, 'text'),
                   ('Use?',         60, 'bool')]

        for icol, dat in enumerate(columns):
             label, width, dtype = dat
             method = wids['dvc'].AppendTextColumn
             mode = dv.DATAVIEW_CELL_EDITABLE
             if dtype == 'bool':
                 method = wids['dvc'].AppendToggleColumn
                 mode = dv.DATAVIEW_CELL_ACTIVATABLE
             method(label, icol, width=width, mode=mode)
             c = wids['dvc'].Columns[icol]
             align = wx.ALIGN_LEFT if icol==0 else wx.ALIGN_RIGHT
             c.Alignment = c.Renderer.Alignment = align
             c.SetSortable(True)

        panel.Add(wids['dvc'], dcol=5, drow=7, newrow=True)
        wids['dvc'].EnsureVisible(self.model.GetItem(0))

        panel.pack()
        self.Show()
        self.wids['mainpanel'] = panel
        self.Bind(wx.EVT_SIZE, self.onSizeEvent)


    def onSizeEvent(self, event=None):
        wnew, hnew = event.GetSize()
        self.wids['mainpanel'].SetSize((wnew, hnew))

        w, h = self.wids['dvc'].GetSize()
        self.wids['dvc'].SetSize((wnew-12, hnew-300))

    def onEdge(self, event=None):
        sel = event.GetEventObject().GetLabel().strip()
        self.edge = EDGES.get(sel, 'All')
        self.onElement(elem=self.elem)

    def onScatterer(self, event=None):
        sel = event.GetEventObject().GetLabel().strip()
        self.scatterer = SCATTERERS.get(sel, 'All')
        self.onElement(elem=self.elem)

    def onElement(self, event=None, elem=None):
        if elem is not None:
            self.elem = elem
        if self.edge == 'All':
            self.edge = None

        filter_oxy = False
        scatt = None
        if self.scatterer == 'Only_O':
            scatt = 8
        elif self.scatterer == 'No_O':
            filter_oxy = True

        if self.elem is not None:
            paths = self.feffdb.list_feffdat(absorber=self.elem,
                                             scatterer=scatt,
                                             edge=self.edge)

            if filter_oxy:
                filt = []
                for p in paths:
                    if p['scatterer'] != 'O':
                        filt.append(p)
                paths = filt

            self.model.set_data(paths)

    def get_current_feffdat_row(self):
        curr =  self.wids['dvc'].GetSelection()
        label = self.model.GetValue(curr, 0)
        return self.feffdb.get_rows('feffdat', where={'label': label}, limit_one=True)

    def onShowFeffInp(self, event=None):
        if len(self.model.feffpaths) > 0:
            row = self.get_current_feffdat_row()
            print(row.id, row.label, row.feffinp_id)

            text = self.feffdb.get_feffinp_for_feffdat(row.id)

            self.show_report(text, title=f"Feff.inp for feffdb['{row.label}'",
                             default_filename=f'{row.label}_feff.inp',
                             wildcard='Feff Input Files (*.inp)|*.inp')


    def onShowCIFFile(self, event=None):
        if len(self.model.feffpaths) > 0:
            row = self.get_current_feffdat_row()
            text = self.feffdb.get_cifinp_for_feffinp(row.feffinp_id)

            self.show_report(text, title=f"CIF for feffdb['{row.label}'",
                             default_filename=f'{row.label}.cif',
                             wildcard='CIF Files (*.cif)|*.cif')


    def onImportPath(self, event=None):
        if len(self.model.feffpaths) > 0:
            sel = [dat for dat in self.model.data if dat[6]]

            row = self.get_current_feffdat_row()
            if len(sel) == 0 and row is not None:
                for dat in self.model.data:
                    if dat[0] == row.label:
                        sel.append(dat)

            for dat in sel:
                label = dat[0]
                row = self.feffdb.get_rows('feffdat',
                                           where={'label': label},
                                        limit_one=True)
                abso, scat = ATSYMS[row.absorber], ATSYMS[row.scatterer]

                # Single-scattering only!
                #  see feffutils.py for expected geometry
                geomstr = f'[{abso}] > {scat} > [{abso}]'
                catom, satom = json.loads(row.geometry)
                geometry = [[satom[0], int(satom[2]), float(row.reff),
                             float(satom[4]), float(satom[5]),
                             float(satom[6]), 180.0, 0.0],
                            [catom[0], int(catom[2]), float(row.reff),
                             float(catom[4]), float(catom[5]),
                             float(catom[6]), 180.0, 0.0]]


                pathinfo = FPathInfo(filename=f'feffdb{label}',
                                     absorber=abso, shell=row.edge,
                                     reff=float(row.reff),
                                     nleg=len(geometry),
                                     degen=row.degen,
                                     cwratio=100.0,
                                     geom=geomstr,
                                     geometry=geometry)

                self.path_importer(f'feffdb[{label}]', pathinfo)

            self.onSelNone()

    def onSelAll(self, event=None):
        self.model.select_all()

    def onSelNone(self, event=None):
        self.model.select_all(use=False)

    def show_report(self, text, title='Text', default_filename='out.txt', wildcard=None):
        if wildcard is None:
            wildcard='Text Files (*.txt)|*.txt'
        default_filename = Path(default_filename).name
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


    def onClose(self, event=None):
        self.Destroy()

class FeffDBApp(LarchWxApp):
    def __init__(self, **kws):
        LarchWxApp.__init__(self, **kws)

    def createApp(self):
        frame = FeffDBFrame()
        self.SetTopWindow(frame)
        return True

if __name__ == '__main__':
    FeffDBApp().MainLoop()
