import os
import sys
import time
import logging

from datetime import datetime, timedelta
import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv


from larch.wxlib import (GUIColors, Button, pack, SimpleText, FileOpen,
                     FileSave, Font, LEFT, FRAMESTYLE)

from larch.xafs import get_feff_pathinfo


LEFT = LEFT|wx.ALL
DVSTYLE = dv.DV_VERT_RULES|dv.DV_ROW_LINES|dv.DV_MULTIPLE
COLOR_MSG  = '#0099BB'
COLOR_OK   = '#0000BB'
COLOR_WARN = '#BB9900'
COLOR_ERR  = '#BB0000'

class FeffPathsModel(dv.DataViewIndexListModel):
    def __init__(self, feffpaths):
        dv.DataViewIndexListModel.__init__(self, 0)
        self.data = []
        self.paths = {}
        self.feffpaths = feffpaths
        self.read_data()
        
    def read_data(self):
        self.data = []
        if self.feffpaths is None:
            self.data.append(('feffNNNN.dat', '3', '2', '6', '100.0', False, '***'))
        else:
            for fp in self.feffpaths:
                use = False
                if fp.filename in self.paths:
                    use = self.paths[fp.filename]
                self.data.append([fp.filename, '%.4f' % fp.reff,
                                  '%.0f' % fp.nleg,
                                  '%.0f' % fp.degeneracy,
                                  '%.3f' % fp.cwratio,
                                  use, fp.geom])
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
        if col == 5:
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
            attr.SetColour('#002')
            attr.SetBold(False)
            return True
        elif nleg == '3':
            attr.SetColour('#040')
            attr.SetBold(False)
            return True
        elif nleg == '4':
            attr.SetColour('#400')
            attr.SetBold(False)
            return True
        else:
            attr.SetColour('#444')
            attr.SetBold(False)
            return True
        return False


FeffResultsPanel = 7

class FeffResultsPanel(wx.Panel):
    """ present Feff results """
    def __init__(self,  parent=None, feffresult=None, _larch=None):
        wx.Panel.__init__(self, parent, -1, size=(600, 500), style=FRAMESTYLE)

        self.parent = parent
        self._larch = _larch

        self.dvc = dv.DataViewCtrl(self, style=DVSTYLE)
        self.dvc.SetMinSize((600, 350))

        self.model = FeffPathsModel(None)
        self.dvc.AssociateModel(self.model)

        panel = wx.Panel(self)
        # panel.SetBackgroundColour(GUIColors.bg)

        sizer = wx.GridBagSizer(2,2)

        bkws = dict(size=(125, -1))
        btn_insert = Button(panel, "Import Paths", action=self.onInsert, **bkws)
        btn_all    = Button(panel, "Select All",    action=self.onSelAll, **bkws)
        btn_none   = Button(panel, "Select None",   action=self.onSelNone, **bkws)

        brow = wx.BoxSizer(wx.HORIZONTAL)
        brow.Add(btn_all ,  0, LEFT|wx.EXPAND, 1)
        brow.Add(btn_none,  0, LEFT|wx.EXPAND, 1)
        brow.Add(btn_insert,0, LEFT|wx.EXPAND, 1)

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
        sizer.Add(self.feff_folder,                  (ir, 1), (1, 1),  LEFT, 2)
        ir += 1
        sizer.Add(SimpleText(panel, 'Date Run:'),    (ir, 0), (1, 1),  LEFT, 2)
        sizer.Add(self.feff_datetime,                (ir, 1), (1, 2),  LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(panel, 'Header:'),      (ir, 0), (1, 1),  LEFT, 2)
        sizer.Add(self.feff_header[0],                 (ir, 1), (1, 2),  LEFT, 2)
        ir += 1
        sizer.Add(SimpleText(panel, ''),             (ir, 0), (1, 1),  LEFT, 2)
        sizer.Add(self.feff_header[1],                 (ir, 1), (1, 2),  LEFT, 2)
        ir += 1
        sizer.Add(SimpleText(panel, ''),             (ir, 0), (1, 1),  LEFT, 2)
        sizer.Add(self.feff_header[2],                 (ir, 1), (1, 2),  LEFT, 2)
        ir += 1
        sizer.Add(SimpleText(panel, ''),             (ir, 0), (1, 1),  LEFT, 2)
        sizer.Add(self.feff_header[3],                 (ir, 1), (1, 2),  LEFT, 2)
        ir += 1
        sizer.Add(SimpleText(panel, ''),             (ir, 0), (1, 1),  LEFT, 2)
        sizer.Add(self.feff_header[4],                 (ir, 1), (1, 2),  LEFT, 2)
        ir += 1
        sizer.Add(SimpleText(panel, ''),             (ir, 0), (1, 1),  LEFT, 2)
        sizer.Add(self.feff_header[5],                 (ir, 1), (1, 2),  LEFT, 2)                

        ir += 1
        sizer.Add(brow,                             (ir, 0), (1, 4),  LEFT, 2)
        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(600, 2)),(ir, 0), (1, 4),  LEFT, 2)

        pack(panel, sizer)

        for icol, dat in enumerate((('Feff File',  100, 'text'),
                                     ('R (Ang)',     60, 'text'),
                                     ('# legs',      60, 'text'),
                                     ('Degeneracy',  60, 'text'),
                                     ('Importance',  60, 'text'),
                                     ('Use',         60, 'bool'),
                                     ('Geometry',   200, 'text'))):
 
             label, width, dtype = dat
             method = self.dvc.AppendTextColumn
             mode = dv.DATAVIEW_CELL_EDITABLE
             if dtype == 'bool':
                 method = self.dvc.AppendToggleColumn
                 mode = dv.DATAVIEW_CELL_ACTIVATABLE
             kws = {}
             if icol > 0:
                 kws['mode'] = mode
             method(label, icol, width=width, **kws)
             c = self.dvc.Columns[icol]
             c.Alignment = wx.ALIGN_LEFT
             c.Sortable = False
             
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

    def onInsert(self, event=None):
        print("on Insert")

    def set_feffresult(self, feffresult):
        self.feff_folder.SetLabel(feffresult.folder)
        self.feff_datetime.SetLabel(feffresult.datetime)
        nhead = len(self.feff_header)
        
        for i, text in enumerate(feffresult.header.split('\n')[:nhead]):
            self.feff_header[i].SetLabel(text)

        self.model.feffpaths = feffresult.paths
        self.model.read_data()


    def onClose(self, event=None):
        self.Destroy()


class Viewer(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, dat,  **kws):
        self.dat = dat
        wx.App.__init__(self, **kws)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = FeffResultsFrame(feffresult=self.dat)
        self.SetTopWindow(frame)

    def OnInit(self):
        self.createApp()
        return True

if __name__ == '__main__':
    dat = None # get_feff_pathinfo('/Users/Newville/.larch/feff/Cu1_K_Cuprite_cif9326')
    Viewer(dat).MainLoop()
