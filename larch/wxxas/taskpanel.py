import time
import os
import sys
import platform
from functools import partial

import numpy as np
np.seterr(all='ignore')

import wx
import wx.grid as wxgrid
import wx.lib.scrolledpanel as scrolled

from larch import Group
from larch.wxlib import (BitmapButton, SetTip, GridPanel, FloatCtrl,
                         FloatSpin, FloatSpinWithPin, get_icon, SimpleText,
                         pack, Button, HLine, Choice, Check, MenuItem,
                         GUIColors, CEN, LEFT, FRAMESTYLE, Font, FileSave,
                         FileOpen, FONTSIZE, DataTableGrid)


from larch.utils import group2dict
from larch.utils.strutils import break_longstring

LEFT = wx.ALIGN_LEFT
CEN |=  wx.ALL

ARRAYS = {'mu':      'Raw \u03BC(E)',
          'norm':    'Normalized \u03BC(E)',
          'flat':    'Flattened \u03BC(E)',
          'prelines':   '\u03BC(E) + Pre-/Post-edge',
          'mback_norm': '\u03BC(E) + MBACK  \u03BC(E)',
          'mback_poly': 'MBACK + Poly Normalized',
          'dnormde':    'd\u03BC(E)/dE (normalized)',
          'norm+dnormde': 'Normalized \u03BC(E) + d\u03BC(E)/dE',
          'd2normde':     'd^2\u03BC(E)/dE^2 (normalized)',
          'norm+d2normde': 'Normalized \u03BC(E) + d^2\u03BC(E)/dE^2',
          'deconv': 'Deconvolved \u03BC(E)',
          'chi':  '\u03c7(k)',
          'chi0':  '\u03c7(k)',
          'chi1': 'k \u03c7(k)',
          'chi2': 'k^2 \u03c7(k)'}

def make_array_choice(opts):
    """
    make (ordered) dict of {Array Description: varname}
    """
    out = {}
    for n in opts:
        if n in ARRAYS:
            out[ARRAYS[n]] = n
    return out

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

class GroupJournalFrame(wx.Frame):
    """ edit parameters"""
    def __init__(self, parent, dgroup=None, xasmain=None, **kws):
        self.xasmain = xasmain
        self.dgroup = dgroup
        self.n_entries = 0
        wx.Frame.__init__(self, None, -1,  'Group Journal',
                          style=FRAMESTYLE, size=(1050, 700))

        panel = GridPanel(self, ncols=3, nrows=10, pad=2, itemstyle=LEFT)

        self.label = SimpleText(panel, 'Group Journal', size=(750, 30))

        export_btn = Button(panel, 'Save to Tab-Separated File', size=(225, -1),
                            action=self.export)


        collabels = [' Label ', ' Value ', 'Date/Time']

        colsizes = [150, 550, 150]
        coltypes = ['string', 'string', 'string']
        coldefs  = [' ', ' ', ' ']

        self.datagrid = DataTableGrid(panel, nrows=80,
                                      collabels=collabels,
                                      datatypes=coltypes,
                                      defaults=coldefs,
                                      colsizes=colsizes,
                                      rowlabelsize=40)

        self.datagrid.SetMinSize((1000, 650))
        self.datagrid.EnableEditing(False)

        panel.Add(self.label, dcol=2)
        panel.Add(HLine(panel, size=(850, 2)), dcol=2, newrow=True)

        # panel.Add(update_btn, newrow=True)
        panel.Add(export_btn, newrow=True)
        panel.Add(self.datagrid, dcol=3, drow=4, newrow=True)
        panel.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, LEFT, 3)
        pack(self, sizer)

        self.xasmain.timers['journal_updater'] = wx.Timer(self.xasmain)
        self.xasmain.Bind(wx.EVT_TIMER, self.onRefresh,
                          self.xasmain.timers['journal_updater'])
        self.Bind(wx.EVT_CLOSE,  self.onClose)

        self.Show()
        self.Raise()
        self.xasmain.timers['journal_updater'].Start(1000)

        if dgroup is not None:
            wx.CallAfter(self.set_group, dgroup=dgroup)

    def onClose(self, event=None):
        self.xasmain.timers['journal_updater'].Stop()
        self.Destroy()

    def onRefresh(self, event=None):
        if self.dgroup is None:
            return
        if self.n_entries == len(self.dgroup.journal.data):
            return
        self.set_group(self.dgroup)


    def export(self, event=None):
        wildcard = 'CSV file (*.csv)|*.csv|All files (*.*)|*.*'
        fname = FileSave(self, message='Save Tab-Separated-Value Data File',
                         wildcard=wildcard,
                         default_file= f"{self.dgroup.filename}_journal.csv")
        if fname is None:
            return

        buff = ['Label\tValue\tDateTime']
        for entry in self.dgroup.journal:
            k, v, dt = entry.key, entry.value, entry.datetime.isoformat()
            k = k.replace('\t', '_')
            if not isinstance(v, str): v = repr(v)
            v = v.replace('\t', '   ')
            buff.append(f"{k}\t{v}\t{dt}")

        buff.append('')
        with open(fname, 'w') as fh:
            fh.write('\n'.join(buff))

        msg = f"Exported journal for {self.dgroup.filename} to '{fname}'"
        writer = getattr(self.xasmain, 'write_message', sys.stdout)
        writer(msg)


    def set_group(self, dgroup=None):
        if dgroup is None:
            dgroup = self.dgroup

        if dgroup is None:
            return
        self.dgroup = dgroup
        self.SetTitle(f'Group Journal for {dgroup.filename:s}')

        label = f'Journal for {dgroup.filename}'
        desc = dgroup.journal.get('source_desc')
        if desc is not None:
            label = f'Journal for {desc.value}'
        self.label.SetLabel(label)

        grid_data = []
        rowsize = []
        self.n_entries = len(dgroup.journal.data)

        for entry in dgroup.journal:
            val = entry.value
            if not isinstance(val, str):
                val = repr(val)
            xval = break_longstring(val)
            val = '\n'.join(xval)
            rowsize.append(len(xval))

            xtime = entry.datetime.strftime("%Y/%m/%d %H:%M:%S")
            grid_data.append([entry.key, val, xtime])

        self.datagrid.table.Clear()
        nrows = self.datagrid.table.GetRowsCount()
        if len(grid_data) > nrows:
            self.datagrid.table.AppendRows(len(grid_data)+8 - nrows)

        self.datagrid.table.data = grid_data
        for i, rsize in enumerate(rowsize):
            self.datagrid.SetRowSize(i, rsize*20)

        self.datagrid.table.View.Refresh()


class TaskPanel(wx.Panel):
    """generic panel for main tasks.
    meant to be subclassed
    """
    def __init__(self, parent, controller, xasmain=None, title='Generic Panel',
                 configname=None,  **kws):
        wx.Panel.__init__(self, parent, -1, size=(550, 625), **kws)
        self.parent = parent
        self.xasmain = xasmain or parent
        self.controller = controller
        self.larch = controller.larch
        self.title = title
        self.configname = configname

        self.wids = {}
        self.subframes = {}
        self.command_hist = []
        self.SetFont(Font(FONTSIZE))
        self.titleopts = dict(font=Font(FONTSIZE+2),
                              colour='#AA0000', style=LEFT)

        self.panel = GridPanel(self, ncols=7, nrows=10, pad=2, itemstyle=LEFT)
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
        self.command_hist.append(cmd)
        return self.controller.larch.eval(cmd)

    def _plain_larch_eval(self, cmd):
        return self.controller.larch._larch.eval(cmd)

    def get_session_history(self):
        """return full session history"""
        larch = self.controller.larch
        return getattr(larch.input, 'hist_buff',
                       getattr(larch.parent, 'hist_buff', []))

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
        if self.configname not in self.controller.conf_group:
            self.controller.conf_group[self.configname] = {}
        self.controller.conf_group[self.configname].update(config)


    def get_defaultconfig(self):
        """get the default configuration for this session"""
        return self.controller.get_config(self.configname)

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
        form_opts = {'groupname': getattr(dgroup, 'groupname', 'No Group')}
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


    def add_floatspin(self, name, value, with_pin=True,
                      relative_e0=False, **kws):
        """create FloatSpin with Pin button for onSelPoint"""
        if with_pin:
            pin_action = partial(self.xasmain.onSelPoint, opt=name,
                                 relative_e0=relative_e0,
                                 callback=self.pin_callback)
            fspin, pinb = FloatSpinWithPin(self.panel, value=value,
                                           pin_action=pin_action, **kws)
        else:
            fspin = FloatSpin(self.panel, value=value, **kws)
            pinb = None

        self.wids[name] = fspin

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(fspin)
        if pinb is not None:
            sizer.Add(pinb)
        return sizer

    def pin_callback(self, opt='__', xsel=None, relative_e0=False, **kws):
        """called to do reprocessing after a point is selected as from Pin/Plot"""
        if xsel is not None and opt in self.wids:
            if relative_e0 and 'e0' in self.wids:
                xsel -= self.wids['e0'].GetValue()
            self.wids[opt].SetValue(xsel)
            wx.CallAfter(self.onProcess)

    def onPlot(self, evt=None):
        pass

    def onPlotOne(self, evt=None, dgroup=None, **kws):
        pass

    def onPlotSel(self, evt=None, groups=None, **kws):
        pass

    def onProcess(self, evt=None, **kws):
        pass
