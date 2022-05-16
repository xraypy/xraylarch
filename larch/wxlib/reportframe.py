import sys
import wx
import wx.grid as wxgrid
import wx.lib.scrolledpanel as scrolled
from wx.richtext import RichTextCtrl

from . import (FONTSIZE, Font, FRAMESTYLE, MenuItem, LEFT, CEN, SimpleText,
               FileOpen, FileSave, GridPanel, Button, HLine, pack)

from larch.utils.strutils import break_longstring

LEFT = wx.ALIGN_LEFT
CEN |=  wx.ALL

# from larch.wxlib import (BitmapButton, SetTip, GridPanel, FloatCtrl,
#                          FloatSpin, FloatSpinWithPin, get_icon, SimpleText,
#                          pack, Button, HLine, Choice, Check, MenuItem,
#                          GUIColors, CEN, LEFT, FRAMESTYLE, Font, FileSave,
#                          FileOpen, FONTSIZE)

class ReportFrame(wx.Frame):
    """basic frame for displaying a text report -- should be improved!
    """
    def __init__(self, parent=None, text=None, size=(725, 600),
                 title='Report', default_filename='out.txt', wildcard='*.txt', **kws):
        self.default_filename = default_filename
        self.wildcard = wildcard
        wx.Frame.__init__(self, parent, size=size, style=FRAMESTYLE, **kws)
        self.SetTitle(title)
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()

        MenuItem(self, fmenu, "Save", "Save Text to File", self.onSave)
        MenuItem(self, fmenu, "Quit",  "Exit", self.onClose)
        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)

        self.report = RichTextCtrl(self,size=size, style=wx.VSCROLL)
        self.report.SetEditable(False)
        self.report.SetFont(wx.Font(FONTSIZE+1,  wx.MODERN, wx.NORMAL, wx.BOLD))

        self.report.SetMinSize((500, 500))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.report, 1, wx.ALL|wx.GROW, 2)
        pack(self, sizer)
        if text is not None:
            self.set_text(text)
        self.Show()
        self.Raise()

    def set_text(self, text):
        self.report.SetEditable(True)
        self.report.SetValue(text)
        self.report.SetEditable(False)


    def onClose(self, event=None):
        self.Destroy()

    def onSave(self, eventt=None):
        wildcard = f'{self.wildcard}|All files (*.*)|*.*'
        path = FileSave(self, message='Save text to file',
                        wildcard=wildcard,
                        default_file=self.default_filename)
        if path is not None:
            with open(path, 'w') as fh:
                fh.write(self.report.GetValue())
                fh.write('')


class DictFrame(wx.Frame):
    """ simple display of dict"""
    def __init__(self, parent, data=None, title='Dictionary', **kws):
        self.parent = parent
        self.title = title
        if data is None: data = {}
        self.data = data

        wx.Frame.__init__(self, None, -1,  title, style=FRAMESTYLE, **kws)


        export_btn = Button(self, 'Save to Tab-Separated File', size=(225, -1),
                            action=self.export)

        collabels = [' Label ', ' Value ']
        colsizes = [200, 550]
        coltypes = ['string', 'string']
        coldefs  = [' ', ' ']

        self.datagrid = DataTableGrid(self,
                                      nrows=min(25, len(self.data)+2),
                                      collabels=collabels,
                                      datatypes=coltypes,
                                      defaults=coldefs,
                                      colsizes=colsizes,
                                      rowlabelsize=40)

        self.datagrid.SetMinSize((850, 500))
        self.datagrid.EnableEditing(False)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(export_btn, 0, LEFT, 2)
        sizer.Add((5, 5), 0, LEFT, 2)
        sizer.Add(self.datagrid, 1, LEFT, 2)

        pack(self, sizer)

        self.Show()
        self.Raise()
        self.SetSize(self.GetBestSize())
        wx.CallAfter(self.set_data)

    def export(self, event=None):
        wildcard = 'CSV file (*.csv)|*.csv|All files (*.*)|*.*'
        fname = self.title + '.csv'
        fname = FileSave(self, message='Save Tab-Separated-Value Data File',
                         wildcard=wildcard,  default_file=fname)
        if fname is None:
            return

        buff = ['Label\tValue']
        for k, v in self.data.items():
            k = k.replace('\t', '_')
            if not isinstance(v, str): v = repr(v)
            v = v.replace('\t', '   ')
            buff.append(f"{k}\t{v}")

        buff.append('')
        with open(fname, 'w') as fh:
            fh.write('\n'.join(buff))

        msg = f"Exported data '{fname}'"
        writer = getattr(self.parent, 'write_message', sys.stdout)
        writer(msg)


    def set_data(self, data=None):
        if data is None:
            data = self.data
        if data is None:
            return

        grid_data = []
        rowsize = []
        n_entries = len(data)

        for key, val in data.items():
            if not isinstance(val, str):
                val = repr(val)
            xval = break_longstring(val)
            val = '\n'.join(xval)
            rowsize.append(len(xval))
            grid_data.append([key, val])

        self.datagrid.table.Clear()
        nrows = self.datagrid.table.GetRowsCount()
        if len(grid_data) > nrows:
            self.datagrid.table.AppendRows(len(grid_data)+8 - nrows)

        self.datagrid.table.data = grid_data
        for i, rsize in enumerate(rowsize):
            self.datagrid.SetRowSize(i, rsize*20)

        self.datagrid.table.View.Refresh()


class DataTable(wxgrid.GridTableBase):
    def __init__(self, nrows=50, collabels=['a', 'b'],
                 datatypes=['str', 'float:12,4'],
                 defaults=[None, None]):

        wxgrid.GridTableBase.__init__(self)

        self.ncols = len(collabels)
        self.nrows = nrows
        self.colLabels = collabels
        self.dataTypes = []
        for i, d in enumerate(datatypes):
            if d.lower().startswith('str'):
                self.dataTypes.append(wxgrid.GRID_VALUE_STRING)
                defval = ''
            elif d.lower().startswith('float:'):
                xt, opt = d.split(':')
                self.dataTypes.append(wxgrid.GRID_VALUE_FLOAT+':%s' % opt)
                defval = 0.0
            if defaults[i] is None:
                defaults[i] = defval

        self.data = []
        for i in range(self.nrows):
            self.data.append(defaults)

    def GetNumberRows(self):
        return self.nrows

    def GetNumberCols(self):
        return self.ncols

    def GetValue(self, row, col):
        try:
            return self.data[row][col]
        except IndexError:
            return ''

    def SetValue(self, row, col, value):
        self.data[row][col] = value

    def GetColLabelValue(self, col):
        return self.colLabels[col]

    def GetRowLabelValue(self, row):
        return "%d" % (row+1)

    def GetTypeName(self, row, col):
        return self.dataTypes[col]

    def CanGetValueAs(self, row, col, typeName):
        colType = self.dataTypes[col].split(':')[0]
        if typeName == colType:
            return True
        else:
            return False

    def CanSetValueAs(self, row, col, typeName):
        return self.CanGetValueAs(row, col, typeName)

class DataTableGrid(wxgrid.Grid):
    def __init__(self, parent, nrows=50, rowlabelsize=35, collabels=['a', 'b'],
                 datatypes=['str', 'float:12,4'],
                 defaults=[None, None],
                 colsizes=[200, 100]):

        wxgrid.Grid.__init__(self, parent, -1)

        self.table = DataTable(nrows=nrows, collabels=collabels,
                                datatypes=datatypes, defaults=defaults)

        self.SetTable(self.table, True)
        self.SetRowLabelSize(rowlabelsize)
        self.SetMargins(10, 10)
        self.EnableDragRowSize()
        self.EnableDragColSize()
        self.AutoSizeColumns(False)
        for i, csize in enumerate(colsizes):
            self.SetColSize(i, csize)

        self.Bind(wxgrid.EVT_GRID_CELL_LEFT_DCLICK, self.OnLeftDClick)

    def OnLeftDClick(self, evt):
        if self.CanEnableCellControl():
            self.EnableCellEditControl()
