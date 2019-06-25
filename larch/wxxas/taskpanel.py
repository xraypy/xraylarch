import time
import os
import platform
from functools import partial
from collections import OrderedDict

import numpy as np
np.seterr(all='ignore')

import wx
import wx.grid as wxgrid

from larch import Group
from larch.wxlib import (BitmapButton, SetTip, GridPanel, FloatCtrl,
                         FloatSpin, FloatSpinWithPin, get_icon, SimpleText,
                         pack, Button, HLine, Choice, Check, MenuItem,
                         GUIColors, CEN, RCEN, LCEN, FRAMESTYLE, Font,
                         FileSave, FileOpen, FONTSIZE)

from larch.wxlib.plotter import last_cursor_pos
from larch.utils import group2dict

LCEN = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
CEN |=  wx.ALL

def autoset_fs_increment(wid, value):
    """set increment for floatspin to be
    1, 2, or 5 x 10^(integer) and ~0.02 X current value
    """
    if abs(value) < 1.e-20:
        return
    ndig = int(1-round(np.log10(abs(value*0.5))))
    wid.SetDigits(ndig+1)
    c, inc = 0, 10.0**(-ndig)
    while (inc/abs(value) > 0.02):
        scale = 0.5 if (c % 2 == 0) else 0.4
        inc *= scale
        c += 1
    wid.SetIncrement(inc)

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


class TaskPanel(wx.Panel):
    """generic panel for main tasks.
    meant to be subclassed
    """
    def __init__(self, parent, controller, title='Generic Panel',
                 configname='task_config', config=None, **kws):
        wx.Panel.__init__(self, parent, -1, size=(550, 625), **kws)
        self.parent = parent
        self.controller = controller
        self.larch = controller.larch
        self.title = title
        self.configname = configname
        if config is not None:
            self.set_defaultconfig(config)
        self.wids = {}
        self.subframes = {}
        self.SetFont(Font(FONTSIZE))
        self.titleopts = dict(font=Font(FONTSIZE+2), colour='#AA0000')

        self.panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LCEN)
        self.panel.sizer.SetVGap(5)
        self.panel.sizer.SetHGap(5)
        self.skip_process = True
        self.skip_plotting = False
        self.build_display()
        self.skip_process = False

    def show_subframe(self, name, frameclass, **opts):
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except:
                del self.subframes[name]
        if not shown:
            self.subframes[name] = frameclass(self, **opts)

    def onPanelExposed(self, **kws):
        # called when notebook is selected
        fname = self.controller.filelist.GetStringSelection()
        if fname in self.controller.file_groups:
            gname = self.controller.file_groups[fname]
            dgroup = self.controller.get_group(gname)
            self.fill_form(dgroup)
            self.process(dgroup=dgroup)

    def write_message(self, msg, panel=0):
        self.controller.write_message(msg, panel=panel)

    def larch_eval(self, cmd):
        """eval"""
        self.controller.larch.eval(cmd)

    def larch_get(self, sym):
        """get value from larch symbol table"""
        return self.controller.larch.symtable.get_symbol(sym)

    def build_display(self):
        """build display"""

        self.panel.Add(SimpleText(self.panel, self.title, **titleopts),
                       dcol=7)
        self.panel.Add(SimpleText(self.panel, ' coming soon....'),
                       dcol=7, newrow=True)
        self.panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.panel, 1, wx.LEFT|wx.CENTER, 3)
        pack(self, sizer)

    def set_defaultconfig(self, config):
        """set the default configuration for this session"""
        conf = self.controller.larch.symtable._sys.xas_viewer
        setattr(conf, self.configname, {key:val for key, val in config.items()})

    def get_defaultconfig(self):
        """get the default configuration for this session"""
        conf = self.controller.larch.symtable._sys.xas_viewer
        defconf = getattr(conf, self.configname, {})
        return {key:val for key, val in defconf.items()}

    def get_config(self, dgroup=None):
        """get and set processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()
        conf = getattr(dgroup, self.configname, self.get_defaultconfig())
        if dgroup is not None:
            setattr(dgroup, self.configname, conf)
        return conf

    def update_config(self, config, dgroup=None):
        """set/update processing configuration for a group"""
        if dgroup is None:
            dgroup = self.controller.get_group()
        conf = getattr(dgroup, self.configname, self.get_defaultconfig())
        conf.update(config)
        if dgroup is not None:
            setattr(dgroup, self.configname, conf)

    def fill_form(self, dat):
        if isinstance(dat, Group):
            dat = group2dict(dat)

        for name, wid in self.wids.items():
            if isinstance(wid, FloatCtrl) and name in dat:
                wid.SetValue(dat[name])

    def read_form(self):
        "read for, returning dict of values"
        dgroup = self.controller.get_group()
        form_opts = {'groupname': dgroup.groupname}
        for name, wid in self.wids.items():
            val = None
            for method in ('GetValue', 'GetStringSelection', 'IsChecked',
                           'GetLabel'):
                meth = getattr(wid, method, None)
                if callable(meth):
                    try:
                        val = meth()
                    except TypeError:
                        pass
                if val is not None:
                    break
            form_opts[name] = val
        return form_opts

    def process(self, dgroup=None, **kws):
        """override to handle data process step"""
        if self.skip_process:
            return
        self.skip_process = True

    def add_text(self, text, dcol=1, newrow=True):
        self.panel.Add(SimpleText(self.panel, text),
                       dcol=dcol, newrow=newrow)

    def add_floatspin(self, name, value, with_pin=True, relative_e0=False,
                      **kws):
        """create FloatSpin with Pin button for onSelPoint"""
        if with_pin:
            pin_action = partial(self.onSelPoint, opt=name,
                                 relative_e0=relative_e0)
            fspin, bb = FloatSpinWithPin(self.panel, value=value,
                                         pin_action=pin_action, **kws)
        else:
            fspin = FloatSpin(self.panel, value=value, **kws)
            bb = (1, 1)

        self.wids[name] = fspin
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(fspin)
        sizer.Add(bb)
        return sizer

    def onPlot(self, evt=None):
        pass

    def onPlotOne(self, evt=None, dgroup=None, **kws):
        pass

    def onPlotSel(self, evt=None, groups=None, **kws):
        pass

    def onSelPoint(self, evt=None, opt='__', relative_e0=False, win=None):
        """
        get last selected point from a specified plot window
        and fill in the value for the widget defined by `opt`.

        by default it finds the latest cursor position from the
        cursor history of the first 20 plot windows.
        """
        if opt not in self.wids:
            return None

        _x, _y = last_cursor_pos(win=win, _larch=self.larch)

        if _x is not None:
            if relative_e0 and 'e0' in self.wids and opt is not 'e0':
                _x -= self.wids['e0'].GetValue()
            self.wids[opt].SetValue(_x)
            cb = getattr(self, 'onProcess', None)
            if callable(cb):
                cb(event=None)
