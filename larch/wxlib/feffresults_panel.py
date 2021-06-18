import os
import sys
import time
import logging

from datetime import datetime, timedelta
import wx
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv

import larch
from larch.site_config import user_larchdir
from larch.wxlib import (GUIColors, Button, pack, SimpleText, FileOpen,
                         FileSave, Font, LEFT, FRAMESTYLE, FONTSIZE,
                         MenuItem,  EditableListBox, FileCheckList,
                         Choice, HLine)


from larch.xafs import get_feff_pathinfo
from larch.xray import atomic_symbols

ATSYMS = ['< All >'] + atomic_symbols
EDGES  = ['< All >', 'K', 'L3', 'L2', 'L1', 'M5']


LEFT = LEFT|wx.ALL
DVSTYLE = dv.DV_VERT_RULES|dv.DV_ROW_LINES|dv.DV_MULTIPLE

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
            self.data.append(('feffNNNN.dat', '0.0000', '2', '6', '100.0', False, '***'))
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



class FeffResultsPanel(wx.Panel):
    """ present Feff results """
    def __init__(self,  parent=None, feffresult=None, _larch=None):
        wx.Panel.__init__(self, parent, -1, size=(650, 650))

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
        btn_above  = Button(panel, "Select All Above Current Paths",  action=self.onSelAbove, **bkws)
        btn_none   = Button(panel, "Select No Paths",   action=self.onSelNone, **bkws)

        brow = wx.BoxSizer(wx.HORIZONTAL)
        brow.Add(btn_above,  0, LEFT|wx.EXPAND, 1)
        brow.Add(btn_none,   0, LEFT|wx.EXPAND, 1)
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

        for icol, dat in enumerate((('Feff File',   100, 'text'),
                                     ('R (Ang)',     75, 'text'),
                                     ('# legs',      50, 'text'),
                                     ('Degeneracy',  75, 'text'),
                                     ('Importance',  75, 'text'),
                                     ('Use',         50, 'bool'),
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




class FeffResultsFrame(wx.Frame):
    """ present Feff results """
    def __init__(self,  parent=None, feffresult=None, _larch=None):
        wx.Frame.__init__(self, parent, -1, size=(850, 650), style=FRAMESTYLE)


        title = "Manage Feff calculation results"
        self.larch = _larch
        if _larch is None:
            self.larch = larch.Interpreter()

        path = os.path.join(user_larchdir, 'feff')
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
        xpos = int((xmax-xmin)*0.12) + xmin
        ypos = int((ymax-ymin)*0.13) + ymin
        self.SetPosition((xpos, ypos))

        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(250)

        # left hand panel
        lpanel = wx.Panel(splitter)
        self.fefflist = FileCheckList(lpanel,
                                      select_action=self.onShowFeff,
                                      remove_action=self.onRemoveFeff,
                                      size=(300, -1))

        lsizer = wx.BoxSizer(wx.VERTICAL)
        lsizer.Add(self.fefflist, 1, LEFT|wx.GROW|wx.ALL, 1)
        pack(lpanel, lsizer)

        # right hand side
        panel = wx.Panel(splitter)
        wids = self.wids = {}
        toprow = wx.Panel(panel)
        wids['search'] = Button(toprow, 'Gather Feff Calculation',
                                action=self.onSearch)
        
        wids['central_atom'] = Choice(toprow, choices=ATSYMS, size=(100, -1),
                                      action=self.onCentralAtom)
        wids['edge']         = Choice(toprow, choices=EDGES, size=(100, -1),
                                      action=self.onAbsorbingEdge)

        flabel = SimpleText(toprow, 'Limit to Element/Edge:', size=(150, -1))
        tsizer = wx.BoxSizer(wx.HORIZONTAL)
        tsizer.Add(wids['search'],       0, LEFT|wx.GROW, 2)
        tsizer.Add(flabel,               1, LEFT, 2)
        tsizer.Add(wids['central_atom'], 0, LEFT|wx.GROW, 2)
        tsizer.Add(wids['edge'],         0, LEFT|wx.GROW, 2)
        pack(toprow, tsizer)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        pan = FeffResultsPanel(panel, _larch=_larch)
        sizer.Add(toprow, 0, LEFT|wx.GROW|wx.ALL, 2)
        sizer.Add(HLine(panel, size=(550, 2)), 0,  LEFT|wx.GROW|wx.ALL, 2)
        sizer.Add(pan, 1, LEFT|wx.GROW|wx.ALL, 2)
        pack(panel, sizer)
        splitter.SplitVertically(lpanel, panel, 1)        
        self.Show()

    def onShowFeff(self, event=None):
        print("show")

    def onRemoveFeff(self, event=None):
        print("remove")    

    def onSearch(self, event=None):
        print("search ", self.feff_folder)
        feffruns = {}
        for path in os.listdir(self.feff_folder):
            fullpath = os.path.join(self.feff_folder, path)
            if os.path.isdir(fullpath):
                try:
                    print('read path ', fullpath)
                except:
                    pass
                
        
    def onCentralAtom(self, event=None):
        print("cent")

    def onAbsorbingEdge(self, event=None):
        print("edge")

    def onSelAll(self, event=None):
        self.fefflist.select_all()

    def onSelNone(self, event=None):
        self.fefflist.select_none()
        
    def onCleanFeffFolders(self, event=None):
        print('clean')

    def onRemoveFeffFolders(self, event=None):
        print('remove')

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

    def createMenus(self):
        # ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()

        MenuItem(self, fmenu, "Select Main Feff Folder",
                 "Select Main Folder for running Feff",
                 self.onFeffFolder)

        MenuItem(self, fmenu, "Cleanup Selected Feff folders",
                 "Keep feff.dat files, but clean up unused files",
                 self.onCleanFeffFolders)

        MenuItem(self, fmenu, "Remove Selected Feff folders",
                 "Completely remove Feff folders",  self.onRemoveFeffFolders)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "Quit",  "Exit", self.onClose)

        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)

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
