import sys
import time

import json
import wx
import wx.lib.agw.flatnotebook as flat_nb

import wx.lib.scrolledpanel as scrolled
import  wx.grid as gridlib

from .gui_utils import (GUIColors, set_font_with_children, YesNo,
                        add_button, pack, SimpleText, check, okcancel,
                        add_subtitle, Font, LCEN, CEN, RCEN, FRAMESTYLE)

RCEN |= wx.ALL
LCEN |= wx.ALL
CEN  |= wx.ALL

ALL_CEN =  wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL
FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

SCANTYPES = ('linear', 'mesh', 'slew', 'xafs')

def buttonrow(panel, onOK=None, onCancel=None):
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


class GenericDataTable(gridlib.PyGridTableBase):
    def __init__(self):
        gridlib.PyGridTableBase.__init__(self)
        self.data = []
        self.scans = []
        self.colLabels = []
        self.dataTypes = []
        self.widths = []        
        self.colReadOnly = []

    def onOK(self):
        del_ids = []
        for iscan, dat in enumerate(self.data):
            if self.scans[iscan].name != dat[0]:
                self.scans[iscan].name = dat[0]
            if dat[-1] == 1:
                del_ids.append(self.scans[iscan].id)
        return del_ids
        
    def GetNumberRows(self):     return len(self.data) + 1
    def GetNumberCols(self):     return len(self.data[0])
    def GetColLabelValue(self, col):    return self.colLabels[col]
    def GetTypeName(self, row, col):     return self.dataTypes[col]

    def IsEmptyCell(self, row, col):
        try:
            return not self.data[row][col]
        except IndexError:
            return True

    def GetValue(self, row, col):
        try:
            return self.data[row][col]
        except IndexError:
            return ''

    def SetValue(self, row, col, value):
        def innerSetValue(row, col, value):
            try:
                self.data[row][col] = value
            except IndexError:
                pass 
        innerSetValue(row, col, value) 

    def CanGetValueAs(self, row, col, typeName):
        colType = self.dataTypes[col].split(':')[0]
        if typeName == colType:
            return True
        else:
            return False

    def CanSetValueAs(self, row, col, typeName):
        return self.CanGetValueAs(row, col, typeName)

class LinearScanDataTable(GenericDataTable):
    def __init__(self, scans):
        GenericDataTable.__init__(self)

        self.colLabels = [' Scan Name ', ' Positioner ', ' # Points ',
                          ' Created ', ' Last Used ', ' Erase? ']
        self.dataTypes = [gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_NUMBER,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_BOOL]
        self.set_data(scans)

    def set_data(self, scans):
        self.scans = scans[::-1]
        self.data = []
        self.widths = [150, 100, 80, 125, 125, 60]
        self.colReadOnly = [False, True, True, True, True, False]
        for scan in self.scans:
            sdat = json.loads(scan.text)
            axis = sdat['positioners'][0][0]
            npts = sdat['positioners'][0][4]
            mtime = scan.modify_time.strftime("%Y-%b-%d %H:%M")
            utime = scan.last_used_time.strftime("%Y-%b-%d %H:%M")
            self.data.append([scan.name, axis, npts, mtime, utime, 0])
                        
class MeshScanDataTable(GenericDataTable):
    def __init__(self, scans):
        GenericDataTable.__init__(self)

        self.colLabels = [' Scan Name ', ' Inner Positioner ',
                          ' Outer Positioner ', ' # Points ',
                          ' Created ', ' Last Used ', ' Erase? ']

        self.dataTypes = [gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_NUMBER,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_BOOL]
        self.set_data(scans)

    def set_data(self, scans):
        self.scans = scans[::-1]
        self.data = []
        self.widths = [150, 100, 100, 80, 125, 125, 60]
        self.colReadOnly = [False, True, True, True, True, True, False]
        for scan in self.scans:
            sdat  = json.loads(scan.text)
            axis0 = sdat['inner'][0]
            axis1 = sdat['outer'][0]
            npts  = int(sdat['outer'][4]) * int(sdat['inner'][4])
            mtime = scan.modify_time.strftime("%Y-%b-%d %H:%M")
            utime = scan.last_used_time.strftime("%Y-%b-%d %H:%M")
            self.data.append([scan.name, axis0, axis1, npts, mtime, utime, 0])

class SlewScanDataTable(GenericDataTable):
    def __init__(self, scans):
        GenericDataTable.__init__(self)

        self.colLabels = [' Scan Name ', ' Inner Positiner ',
                          ' Outer Positioner ', ' # Points ',
                          ' Created ', ' Last Used ', ' Erase? ']
        self.dataTypes = [gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_NUMBER,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_BOOL]
        self.set_data(scans)

    def set_data(self, scans):
        self.scans = scans[::-1]
        self.data = []
        self.widths = [150, 100, 100, 80, 125, 125, 60]
        self.colReadOnly = [False, True, True, True, True, True, False]
        for scan in self.scans:
            sdat  = json.loads(scan.text)
            axis0 = sdat['inner'][0]
            axis1 = 'None'
            npts  = int(sdat['inner'][4])
            if sdat['dimension'] > 1:
                axis1 = sdat['outer'][0]
                npts *= int(sdat['outer'][4])
            mtime = scan.modify_time.strftime("%Y-%b-%d %H:%M")
            utime = scan.last_used_time.strftime("%Y-%b-%d %H:%M")
            self.data.append([scan.name, axis0, axis1, npts, mtime, utime, 0])

class XAFSScanDataTable(GenericDataTable):
    def __init__(self, scans):
        GenericDataTable.__init__(self)

        self.colLabels = [' Scan Name ', ' E0 ', ' # Regions', ' # Points ',
                          ' Created ', ' Last Used ', ' Erase? ']
        self.dataTypes = [gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_FLOAT + ':9,2',
                          gridlib.GRID_VALUE_NUMBER,
                          gridlib.GRID_VALUE_NUMBER,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_STRING,
                          gridlib.GRID_VALUE_BOOL]
        self.set_data(scans)

    def set_data(self, scans):
        self.scans = scans[::-1]
        self.data = []
        self.widths = [150, 80, 80, 80, 125, 125, 60]
        self.colReadOnly = [False, True, True, True, True, True, False]
        for scan in self.scans:
            sdat  = json.loads(scan.text)
            e0   = sdat['e0']
            nreg = len(sdat['regions'])
            npts = 1 - nreg
            for ireg in range(nreg):
                npts += sdat['regions'][ireg][2]
            mtime = scan.modify_time.strftime("%Y-%b-%d %H:%M")
            utime = scan.last_used_time.strftime("%Y-%b-%d %H:%M")
            self.data.append([scan.name, e0, nreg, npts, mtime, utime, 0])

class ScandefsFrame(wx.Frame) :
    """Edit Scan Definitions"""
    def __init__(self, parent, pos=(-1, -1)):

        self.parent = parent
        self.scandb = parent.scandb
        wx.Frame.__init__(self, None, -1,
                          'Epics Scanning: Scan Definitions',
                          style=FRAMESTYLE)

        self.SetFont(Font(10))
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetMinSize((740, 450))
        self.colors = GUIColors()
        panel = scrolled.ScrolledPanel(self)
        panel.SetBackgroundColour(self.colors.bg)
        self.nb = flat_nb.FlatNotebook(panel, wx.ID_ANY, agwStyle=FNB_STYLE)
        self.nb.SetBackgroundColour('#FAFCFA')
        self.SetBackgroundColour('#FAFCFA')
        
        sizer.Add(SimpleText(panel, 'Scan Definitions',
                             font=Font(13),
                             colour=self.colors.title, style=LCEN),
                  0, LCEN, 5)

        allscans = {}
        for t in SCANTYPES:
            allscans[t] = []

        for this in self.scandb.getall('scandefs',
                                       orderby='last_used_time'):
            allscans[this.type].append(this)
            utime = this.last_used_time.strftime("%Y-%b-%d %H:%M")
            
        self.tables = []
        self.nblabels = []
        for pname, creator in (('Linear', LinearScanDataTable),
                               ('Mesh', MeshScanDataTable),
                               ('Slew', SlewScanDataTable),
                               ('XAFS', XAFSScanDataTable)):
            tgrid = gridlib.Grid(panel)
            tgrid.SetBackgroundColour('#FAFAF8')            
            table = creator(allscans[pname.lower()])
            tgrid.SetTable(table, True)
            self.tables.append(table)
            self.nb.AddPage(tgrid, "%s Scans" % pname)
            self.nblabels.append((pname.lower(), tgrid))
            
            nrows = tgrid.GetNumberRows()
            for icol, wid in enumerate(table.widths):
                tgrid.SetColMinimalWidth(icol, wid)
                tgrid.SetColSize(icol, wid)
                for irow in range(nrows-1):
                    tgrid.SetReadOnly(irow, icol, table.colReadOnly[icol])
            tgrid.SetRowLabelSize(1)
            tgrid.SetMargins(1,1)
            tgrid.HideRow(nrows-1)
            
        self.nb.SetSelection(0)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND, 5)

        bpanel = wx.Panel(panel)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.Add(add_button(bpanel, label='Load Current Scan', action=self.onView))
        bsizer.Add(add_button(bpanel, label='Apply Changes', action=self.onApply))
        bsizer.Add(add_button(bpanel, label='Refresh List',  action=self.onRefresh))
        bsizer.Add(add_button(bpanel, label='Done', action=self.onDone))

        pack(bpanel, bsizer)
        sizer.Add(bpanel, 0, LCEN, 5)
        
        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)
        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def onRefresh(self, evt=None):
        allscans = {}
        for t in SCANTYPES:
            allscans[t] = []

        for this in self.scandb.getall('scandefs',
                                       orderby='last_used_time'):
            allscans[this.type].append(this)
            utime = this.last_used_time.strftime("%Y-%b-%d %H:%M")
            
        for i, pname in enumerate(SCANTYPES):
            self.tables[i].set_data(allscans[pname.lower()])

        inb  = self.nb.GetSelection()
        self.nb.SetSelection(inb)
        self.Refresh()

    def onApply(self, event=None):
        for table in self.tables:
            del_ids = table.onOK()
            for scanid in del_ids:
                self.scandb.del_scandef(scanid=scanid)
        self.scandb.commit()
        self.onRefresh()

    def onDone(self, event=None):
        self.Destroy()
            
    def onView(self, event=None):
        inb =  self.nb.GetSelection()
        label, thisgrid = self.nblabels[inb]
        irow = thisgrid.GetGridCursorRow()
        scandef = json.loads(self.tables[inb].scans[irow].text)
        scanpanel = self.parent.scanpanels[label.lower()][1]
        scanpanel.load_scandict(scandef)
        self.parent.nb.SetSelection(inb)

