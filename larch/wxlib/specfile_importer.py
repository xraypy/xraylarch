#!/usr/bin/env python
"""

"""
from pathlib import Path

import numpy as np
np.seterr(all='ignore')

from functools import partial

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb
from wxmplot import PlotPanel

from wxutils import (SimpleText, FloatCtrl, GUIColors, Button, Choice,
                     FileCheckList, pack, Popup, Check, MenuItem, CEN,
                     RIGHT, LEFT, FRAMESTYLE, HLine, Font)

import larch
from larch import Group
from larch.utils.strutils import fix_varname
from larch.xafs.xafsutils import guess_energy_units
from larch.io import look_for_nans, is_specfile, open_specfile
from larch.utils.physical_constants import PLANCK_HC, DEG2RAD, PI
from .columnframe import MultiColumnFrame, create_arrays, energy_may_need_rebinning

CEN |=  wx.ALL
FNB_STYLE = fnb.FNB_NO_X_BUTTON|fnb.FNB_SMART_TABS
FNB_STYLE |= fnb.FNB_NO_NAV_BUTTONS|fnb.FNB_NODRAG

XPRE_OPS = ('', 'log(', '-log(')
YPRE_OPS = ('', 'log(', '-log(')
ARR_OPS = ('+', '-', '*', '/')

YERR_OPS = ('Constant', 'Sqrt(Y)', 'Array')
CONV_OPS  = ('Lorenztian', 'Gaussian')

XDATATYPES = ('xydata', 'xas')
ENUNITS_TYPES = ('eV', 'keV', 'degrees', 'not energy')


class SpecfileImporter(wx.Frame) :
    """Column Data File, select columns"""
    def __init__(self, parent, filename=None, config=None, _larch=None,
                 read_ok_cb=None):
        if not is_specfile(filename):
            title = "Not a Specfile: %s" % filename
            message = "Error reading %s as a Specfile" % filename
            r = Popup(parent, message, title)
            return None

        self.parent = parent
        fpath = Path(filename).absolute()
        self.path = fpath.as_posix()
        self.filename = fpath.name
        self._larch = _larch
        self.specfile = open_specfile(self.path)
        self.scans = []
        curscan = None
        for scandata in self.specfile.get_scans():
            name, cmd, dtime = scandata
            self.scans.append("%s | %s" % (name, cmd))
            if curscan is None:
                curscan = name

        self.curscan = self.specfile.get_scan(curscan)
        self.subframes = {}
        self.workgroup = Group()
        for attr in ('path', 'filename', 'datatype',
                     'array_labels', 'data'):
            setattr(self.workgroup, attr, None)

        self.array_labels = [l.lower() for l in self.curscan.array_labels]

        if self.workgroup.datatype is None:
            self.workgroup.datatype = 'xydata'
            for arrlab in self.array_labels[:4]:
                if 'ener' in arrlab.lower():
                    self.workgroup.datatype = 'xas'

        self.read_ok_cb = read_ok_cb

        self.config = dict(xarr=self.curscan.axis.lower(), yarr1=None,
                           yarr2=None, yop='/', ypop='',
                           monod=3.1355316, en_units='eV',
                           yerror=YERR_OPS[0], yerr_val=1,
                           yerr_arr=None, dtc_config={}, multicol_config={})

        if config is not None:
            self.config.update(config)

        if self.config['yarr2'] is None and 'i0' in self.array_labels:
            self.config['yarr2'] = 'i0'

        if self.config['yarr1'] is None:
            if 'itrans' in self.array_labels:
                self.config['yarr1'] = 'itrans'
            elif 'i1' in self.array_labels:
                self.config['yarr1'] = 'i1'

        wx.Frame.__init__(self, None, -1, f'Build Arrays for {filename:s}',
                          style=FRAMESTYLE)

        self.SetMinSize((750, 550))
        self.SetSize((850, 650))
        self.colors = GUIColors()

        x0, y0 = parent.GetPosition()
        self.SetPosition((x0+60, y0+60))
        self.SetFont(Font(10))

        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(200)

        leftpanel = wx.Panel(splitter)
        ltop = wx.Panel(leftpanel)

        sel_none = Button(ltop, 'Select None', size=(100, 30), action=self.onSelNone)
        sel_all  = Button(ltop, 'Select All', size=(100, 30), action=self.onSelAll)
        sel_imp  = Button(ltop, 'Import Selected Scans', size=(200, -1), action=self.onOK)

        self.scanlist = FileCheckList(leftpanel, select_action=self.onScanSelect)
        self.scanlist.AppendItems(self.scans)

        tsizer = wx.GridBagSizer(2, 2)
        tsizer.Add(sel_all, (0, 0), (1, 1), LEFT, 0)
        tsizer.Add(sel_none,  (0, 1), (1, 1), LEFT, 0)
        tsizer.Add(sel_imp,  (1, 0), (1, 2), LEFT, 0)
        pack(ltop, tsizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ltop, 0, LEFT|wx.GROW, 1)
        sizer.Add(self.scanlist, 1, LEFT|wx.GROW|wx.ALL, 1)
        pack(leftpanel, sizer)

        # right hand side
        rightpanel = wx.Panel(splitter)

        panel = wx.Panel(rightpanel)
        # title row
        self.title = SimpleText(panel,
                                "  %s, scan %s" % (self.path, self.curscan.scan_name),
                                font=Font(11), colour=self.colors.title, style=LEFT)

        self.wid_scantitle = SimpleText(panel, " %s" % self.curscan.title,
                                       font=Font(11), style=LEFT)
        self.wid_scantime = SimpleText(panel, self.curscan.timestring,
                                       font=Font(11), style=LEFT)

        yarr_labels = self.yarr_labels = self.array_labels + ['1.0', '0.0', '']
        xarr_labels = self.xarr_labels = self.array_labels + ['_index']

        self.xarr   = Choice(panel, choices=xarr_labels, action=self.onXSelect, size=(150, -1))
        self.yarr1  = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        self.yarr2  = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        self.yerr_arr = Choice(panel, choices=yarr_labels, action=self.onUpdate, size=(150, -1))
        self.yerr_arr.Disable()

        self.datatype = Choice(panel, choices=XDATATYPES, action=self.onUpdate, size=(150, -1))
        self.datatype.SetStringSelection(self.workgroup.datatype)

        self.en_units = Choice(panel, choices=ENUNITS_TYPES, action=self.onEnUnitsSelect,
                               size=(150, -1))

        self.ypop = Choice(panel, choices=YPRE_OPS, action=self.onUpdate, size=(150, -1))
        self.yop =  Choice(panel, choices=ARR_OPS, action=self.onUpdate, size=(50, -1))
        self.yerr_op = Choice(panel, choices=YERR_OPS, action=self.onYerrChoice, size=(150, -1))

        self.yerr_val = FloatCtrl(panel, value=1, precision=4, size=(90, -1))
        self.monod_val  = FloatCtrl(panel, value=3.1355316, precision=7, size=(90, -1))

        xlab = SimpleText(panel, ' X array: ')
        ylab = SimpleText(panel, ' Y array: ')
        units_lab = SimpleText(panel, '  Units:  ')
        yerr_lab = SimpleText(panel, ' Yerror: ')
        dtype_lab = SimpleText(panel, ' Data Type: ')
        monod_lab = SimpleText(panel, ' Mono D spacing (Ang): ')
        yerrval_lab = SimpleText(panel, ' Value:')

        self.ysuf = SimpleText(panel, '')
        self.message = SimpleText(panel, '-', font=Font(11),
                           colour=self.colors.title, style=LEFT)

        self.ypop.SetStringSelection(self.config['ypop'])
        self.yop.SetStringSelection(self.config['yop'])
        self.monod_val.SetValue(self.config['monod'])
        self.monod_val.SetAction(self.onUpdate)

        self.monod_val.Enable(self.config['en_units'].startswith('deg'))
        self.en_units.SetStringSelection(self.config['en_units'])
        self.yerr_op.SetStringSelection(self.config['yerror'])
        self.yerr_val.SetValue(self.config['yerr_val'])
        if '(' in self.config['ypop']:
            self.ysuf.SetLabel(')')

        ixsel, iysel, iy2sel, iyesel = 0, 1, len(yarr_labels)-1,  len(yarr_labels)-1
        if self.config['xarr'] in xarr_labels:
            ixsel = xarr_labels.index(self.config['xarr'])
        if self.config['yarr1'] in self.array_labels:
            iysel = self.array_labels.index(self.config['yarr1'])
        if self.config['yarr2'] in yarr_labels:
            iy2sel = yarr_labels.index(self.config['yarr2'])
        if self.config['yerr_arr'] in yarr_labels:
            iyesel = yarr_labels.index(self.config['yerr_arr'])
        self.xarr.SetSelection(ixsel)
        self.yarr1.SetSelection(iysel)
        self.yarr2.SetSelection(iy2sel)
        self.yerr_arr.SetSelection(iyesel)

        bpanel = wx.Panel(panel)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.multi_sel = Button(bpanel, 'Select Multilple Columns',  action=self.onMultiColumn)
        self.multi_clear = Button(bpanel, 'Clear Multiple Columns',  action=self.onClearMultiColumn)
        self.multi_clear.Disable()
        self.multi_sel.SetToolTip('Select Multiple Columns to import as separate groups')
        self.multi_clear.SetToolTip('Clear Multiple Column Selection')
        bsizer.Add(self.multi_sel)
        bsizer.Add(self.multi_clear)
        pack(bpanel, bsizer)

        sizer = wx.GridBagSizer(2, 2)
        ir = 0
        sizer.Add(self.title,     (ir, 0), (1, 7), LEFT, 5)

        ir += 1
        sizer.Add(self.wid_scantitle,  (ir, 0), (1, 3), LEFT, 0)
        sizer.Add(self.wid_scantime,   (ir, 3), (1, 2), LEFT, 0)


        ir += 1
        sizer.Add(xlab,      (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.xarr,  (ir, 1), (1, 1), LEFT, 0)
        sizer.Add(units_lab,     (ir, 2), (1, 2), RIGHT, 0)
        sizer.Add(self.en_units,  (ir, 4), (1, 2), LEFT, 0)

        ir += 1
        sizer.Add(dtype_lab,          (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.datatype,      (ir, 1), (1, 1), LEFT, 0)
        sizer.Add(monod_lab,          (ir, 2), (1, 2), RIGHT, 0)
        sizer.Add(self.monod_val,     (ir, 4), (1, 1), LEFT, 0)

        ir += 1
        sizer.Add(ylab,       (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.ypop,  (ir, 1), (1, 1), LEFT, 0)
        sizer.Add(self.yarr1, (ir, 2), (1, 1), LEFT, 0)
        sizer.Add(self.yop,   (ir, 3), (1, 1), RIGHT, 0)
        sizer.Add(self.yarr2, (ir, 4), (1, 1), LEFT, 0)
        sizer.Add(self.ysuf,  (ir, 5), (1, 1), LEFT, 0)

        ir += 1
        sizer.Add(yerr_lab,      (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.yerr_op,  (ir, 1), (1, 1), LEFT, 0)
        sizer.Add(self.yerr_arr, (ir, 2), (1, 1), LEFT, 0)
        sizer.Add(yerrval_lab,   (ir, 3), (1, 1), RIGHT, 0)
        sizer.Add(self.yerr_val, (ir, 4), (1, 2), LEFT, 0)

        ir += 1
        sizer.Add(self.message,                     (ir, 0), (1, 4), LEFT, 0)
        ir +=1
        sizer.Add(bpanel,     (ir, 0), (1, 5), LEFT, 3)

        pack(panel, sizer)

        self.nb = fnb.FlatNotebook(rightpanel, -1, agwStyle=FNB_STYLE)
        self.nb.SetTabAreaColour(wx.Colour(248,248,240))
        self.nb.SetActiveTabColour(wx.Colour(254,254,195))
        self.nb.SetNonActiveTabTextColour(wx.Colour(40,40,180))
        self.nb.SetActiveTabTextColour(wx.Colour(80,0,0))

        self.plotpanel = PlotPanel(rightpanel, messenger=self.plot_messages)
        try:
            plotopts = self._larch.symtable._sys.wx.plotopts
            self.plotpanel.conf.set_theme(plotopts['theme'])
            self.plotpanel.conf.enable_grid(plotopts['show_grid'])
        except:
            pass

        self.plotpanel.SetMinSize((300, 250))

        shead = wx.Panel(rightpanel)
        self.scanheader = wx.TextCtrl(shead, style=wx.TE_MULTILINE|wx.TE_READONLY,
                                      size=(400, 250))
        self.scanheader.SetValue('\n'.join(self.curscan.scan_header))
        self.scanheader.SetFont(Font(10))
        textsizer = wx.BoxSizer(wx.VERTICAL)
        textsizer.Add(self.scanheader, 1, LEFT|wx.GROW, 1)
        pack(shead, textsizer)


        fhead = wx.Panel(rightpanel)
        self.fileheader = wx.TextCtrl(fhead, style=wx.TE_MULTILINE|wx.TE_READONLY,
                                      size=(400, 250))
        self.fileheader.SetValue('\n'.join(self.curscan.file_header))
        self.fileheader.SetFont(Font(10))
        textsizer = wx.BoxSizer(wx.VERTICAL)
        textsizer.Add(self.fileheader, 1, LEFT|wx.GROW, 1)
        pack(fhead, textsizer)



        self.nb.AddPage(fhead, ' File Header ', True)
        self.nb.AddPage(shead, ' Scan Header ', True)
        self.nb.AddPage(self.plotpanel, ' Plot of Selected Arrays ', True)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 0, LEFT|wx.GROW, 1)
        sizer.Add(self.nb, 1, LEFT|wx.GROW|wx.ALL, 1)
        pack(rightpanel, sizer)

        splitter.SplitVertically(leftpanel, rightpanel, 1)
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-1, -1])
        statusbar_fields = [filename, ""]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        self.set_energy_units()
        csize = self.GetSize()
        bsize = self.GetBestSize()
        if bsize[0] > csize[0]: csize[0] = bsize[0]
        if bsize[1] > csize[1]: csize[1] = bsize[1]
        self.SetSize(csize)
        self.Show()
        self.Raise()
        self.onUpdate(self)

    def set_energy_units(self):
        ix  = self.xarr.GetSelection()
        xname = self.xarr.GetStringSelection()
        rdata = self.curscan.data
        try:
            ncol, npts = rdata.shape
        except:
            self.statusbar.SetStatusText(f"Warning: Could not read data for scan '{self.curscan.title:s}'")

        workgroup = self.workgroup
        if xname.startswith('_index') or ix >= ncol:
            workgroup.xplot = 1.0*np.arange(npts)
        else:
            workgroup.xplot = 1.0*rdata[ix, :]
        eguess =  guess_energy_units(workgroup.xplot)
        if eguess.startswith('eV'):
            self.en_units.SetStringSelection('eV')
        elif eguess.startswith('keV'):
            self.en_units.SetStringSelection('keV')

    def onScanSelect(self, event=None):
        try:
            scan_desc = event.GetString()
            name = [s.strip() for s in scan_desc.split(' | ')][0]
            self.curscan = self.specfile.get_scan(name)
        except:
            return
        slist = list(self.scanlist.GetCheckedStrings())
        if scan_desc not in slist:
            slist.append(scan_desc)
        self.scanlist.SetCheckedStrings(slist)

        self.wid_scantitle.SetLabel("  %s" % self.curscan.title)
        self.wid_scantime.SetLabel(self.curscan.timestring)

        self.title.SetLabel("  %s, scan %s" % (self.path, self.curscan.scan_name))
        self.array_labels = [l.lower() for l in self.curscan.array_labels]
        self.workgroup.array_labels = self.array_labels
        self.workgroup.data = self.curscan.data

        yarr_labels = self.yarr_labels = self.array_labels + ['1.0', '0.0', '']
        xarr_labels = self.xarr_labels = self.array_labels + ['_index']

        xsel = self.xarr.GetStringSelection()
        self.xarr.Clear()
        self.xarr.AppendItems(xarr_labels)
        if xsel in xarr_labels:
            self.xarr.SetStringSelection(xsel)
        else:
            self.xarr.SetSelection(0)

        y1sel = self.yarr1.GetStringSelection()
        self.yarr1.Clear()
        self.yarr1.AppendItems(yarr_labels)
        if y1sel in yarr_labels:
            self.yarr1.SetStringSelection(y1sel)
        else:
            self.yarr1.SetSelection(1)

        y2sel = self.yarr2.GetStringSelection()
        self.yarr2.Clear()
        self.yarr2.AppendItems(yarr_labels)
        if y2sel in yarr_labels:
            self.yarr2.SetStringSelection(y2sel)

        xsel = self.xarr.GetStringSelection()
        self.workgroup.datatype = 'xas' if 'en' in xsel else 'xydata'
        self.datatype.SetStringSelection(self.workgroup.datatype)

        self.scanheader.SetValue('\n'.join(self.curscan.scan_header))
        self.set_energy_units()
        self.onUpdate()

    def onClearMultiColumn(self, event=None):
        self.config['multicol_config'] = {}
        self.message.SetLabel(f" cleared reading of multiple columns")
        self.multi_clear.Disable()
        self.yarr1.Enable()
        self.ypop.Enable()
        self.yop.Enable()
        self.onUpdate()

    def onMultiColumn(self, event=None):
        if 'multicol_config' not in self.config:
            self.config['multicol_config'] = {}

        if len(self.array_labels)  < 1:
            self.array_labels = [l.lower() for l in self.curscan.array_labels]
        self.workgroup.array_labels = self.array_labels
        self.workgroup.data = self.curscan.data
        self.show_subframe('multicol', MultiColumnFrame,
                           config=self.config['multicol_config'],
                           group=self.workgroup,
                           on_ok=self.onMultiColumn_OK)

    def onMultiColumn_OK(self, config, update=True, **kws):
        chans = config.get('channels', [])
        if len(chans) == 0:
            self.config['multicol_config'] = {}
        else:
            self.config['multicol_config'] = config
            self.yarr1.SetSelection(chans[0])
            self.yarr2.SetSelection(config['i0'])
            self.ypop.SetStringSelection('')
            self.yarr1.Disable()
            self.ypop.Disable()
            self.yop.Disable()
            y2 = self.yarr2.GetStringSelection()
            msg = f"  Will import {len(config['channels'])} Y arrays, divided by '{y2}'"
            self.message.SetLabel(msg)
            self.multi_clear.Enable()
        if update:
            self.onUpdate()


    def show_subframe(self, name, frameclass, **opts):
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except:
                pass
        if not shown:
            self.subframes[name] = frameclass(self, **opts)
            self.subframes[name].Show()
            self.subframes[name].Raise()

    def set_array_labels(self, arr_labels):
        self.workgroup.array_labels = arr_labels
        yarr_labels = self.yarr_labels = arr_labels + ['1.0', '0.0', '']
        xarr_labels = self.xarr_labels = arr_labels + ['_index']
        def update(wid, choices):
            curstr = wid.GetStringSelection()
            curind = wid.GetSelection()
            wid.SetChoices(choices)
            if curstr in choices:
                wid.SetStringSelection(curstr)
            else:
                wid.SetSelection(curind)
        update(self.xarr,  xarr_labels)
        update(self.yarr1, yarr_labels)
        update(self.yarr2, yarr_labels)
        update(self.yerr_arr, yarr_labels)
        self.onUpdate()

    def onSelAll(self, event=None):
        self.scanlist.SetCheckedStrings(self.scans)

    def onSelNone(self, event=None):
        self.scanlist.SetCheckedStrings([])

    def onOK(self, event=None):
        """ build arrays according to selection """

        scanlist = []
        for s in self.scanlist.GetCheckedStrings():
            words = [s.strip() for s in s.split('|')]
            scanlist.append(words[0])
        if len(scanlist) == 0:
            cancel = Popup(self, """No scans selected.
         Cancel import from this project?""", 'Cancel Import?',
                           style=wx.YES_NO)
            if wx.ID_YES == cancel:
                self.Destroy()
            else:
                return

        self.read_form()
        cout = create_arrays(self.workgroup, **self.config)
        self.config.update(cout)
        conf = self.config
        conf['array_labels'] = self.workgroup.array_labels

        if self.ypop.Enabled:  #not using multicolumn mode
            conf['multicol_config'] = {'channels': [], 'i0': conf['iy2']}

        self.expressions = conf['expressions']

        # generate script to pass back to calling program:
        # read_cmd = "_specfile.get_scan(scan='{scan}')"
        buff = ["{group} = {specfile}.get_scan(scan='{scan}')",
                "{group}.path = '{path}'",
                "{group}.is_frozen = False"]

        for attr in ('datatype', 'plot_xlabel', 'plot_ylabel'):
            val = getattr(self.workgroup, attr)
            buff.append("{group}.%s = '%s'" % (attr, val))

        xexpr = self.expressions['xplot']
        en_units = conf['en_units']
        if en_units.startswith('deg'):
            buff.append(f"mono_dspace = {dspace:.9f}")
            buff.append(f"{{group}}.xplot = PLANCK_HC/(2*mono_dspace*sin(DEG2RAD*({expr:s})))")
        elif en_units.startswith('keV'):
            buff.append(f"{{group}}.xplot = 1000.0*{xexpr:s}")
        else:
            buff.append(f"{{group}}.xplot = {xexpr:s}")

        for aname in ('yplot', 'yerr'):
            expr = self.expressions[aname]
            buff.append(f"{{group}}.{aname} = {expr}")

        dtype = getattr(self.workgroup, 'datatype', 'xytype')
        if dtype == 'xas':
            buff.append("{group}.energy = {group}.xplot"[:])
            buff.append("{group}.mu = {group}.yplot[:]")
            buff.append("sort_xafs({group}, overwrite=True, fix_repeats=True)")
        elif dtype == 'xydata':
            buff.append("{group}.x = {group}.xplot[:]")
            buff.append("{group}.y = {group}.yplot[:]")
            buff.append("{group}.scale = (ptp({group}.yplot)+1.e-15)")
            buff.append("{group}.xshift = 0.0")

        script = "\n".join(buff)

        self.config['array_desc'] = dict(xplot=self.workgroup.plot_xlabel,
                                         yplot=self.workgroup.plot_ylabel,
                                         yerr=self.expressions['yerr'])
        if self.read_ok_cb is not None:
            self.read_ok_cb(script, self.path, scanlist,
                            config=self.config)

        for f in self.subframes.values():
            try:
                f.Destroy()
            except:
                pass
        self.Destroy()

    def onCancel(self, event=None):
        self.workgroup.import_ok = False
        for f in self.subframes.values():
            try:
                f.Destroy()
            except:
                pass
        self.Destroy()

    def onYerrChoice(self, evt=None):
        yerr_choice = evt.GetString()
        self.yerr_arr.Disable()
        self.yerr_val.Disable()
        if 'const' in yerr_choice.lower():
            self.yerr_val.Enable()
        elif 'array' in yerr_choice.lower():
            self.yerr_arr.Enable()
        self.onUpdate()

    def onXSelect(self, evt=None):
        ix  = self.xarr.GetSelection()
        xname = self.xarr.GetStringSelection()

        workgroup = self.workgroup
        rdata = self.curscan.data
        ncol, npts = rdata.shape
        if xname.startswith('_index') or ix >= ncol:
            workgroup.xplot = 1.0*np.arange(npts)
        else:
            workgroup.xplot = 1.0*rdata[ix, :]

        self.monod_val.Disable()
        if self.datatype.GetStringSelection().strip().lower() == 'xydata':
            self.en_units.SetSelection(4)
        else:
            eguess = guess_energy_units(workgroup.xplot)
            if eguess.startswith('keV'):
                self.en_units.SetSelection(1)
            elif eguess.startswith('deg'):
                self.en_units.SetSelection(2)
                self.monod_val.Enable()
            else:
                self.en_units.SetSelection(0)

        self.onUpdate()

    def onEnUnitsSelect(self, evt=None):
        self.monod_val.Enable(self.en_units.GetStringSelection().startswith('deg'))
        self.onUpdate()

    def read_form(self, **kws):
        """return form configuration"""
        datatype = self.datatype.GetStringSelection().strip().lower()
        if datatype == 'xydata':
            self.en_units.SetStringSelection('not energy')

        conf = {'datatype': datatype,
                'ix':  self.xarr.GetSelection(),
                'xarr': self.xarr.GetStringSelection(),
                'en_units': self.en_units.GetStringSelection(),
                'monod': float(self.monod_val.GetValue()),
                'yarr1': self.yarr1.GetStringSelection().strip(),
                'yarr2': self.yarr2.GetStringSelection().strip(),
                'iy1': self.yarr1.GetSelection(),
                'iy2': self.yarr2.GetSelection(),
                'yop': self.yop.GetStringSelection().strip(),
                'ypop': self.ypop.GetStringSelection().strip(),
                'iyerr': self.yerr_arr.GetSelection(),
                'yerr_arr': self.yerr_arr.GetStringSelection(),
                'yerr_op': self.yerr_op.GetStringSelection().lower(),
                'yerr_val': self.yerr_val.GetValue(),
                }
        self.config.update(conf)
        return conf


    def onUpdate(self, value=None, evt=None):
        """column selections changed calc xplot and yplot"""
        workgroup = self.workgroup
        workgroup.data = self.curscan.data
        workgroup.filename = self.curscan.filename

        conf = self.read_form()
        cout = create_arrays(workgroup, **conf)

        self.expression = cout.pop('expressions')
        conf.update(cout)

        if energy_may_need_rebinning(workgroup):
            self.message.SetLabel("Warning: XAS data may need to be rebinned!")

        popts = dict(marker='o', markersize=4, linewidth=1.5,
                     title=Path(workgroup.filename).name,
                     ylabel=workgroup.plot_ylabel,
                     xlabel=workgroup.plot_xlabel,
                     label=workgroup.plot_ylabel)
        try:
            self.plotpanel.plot(workgroup.xplot, workgroup.yplot, **popts)
        except:
            pass


    def plot_messages(self, msg, panel=1):
        self.statusbar.SetStatusText(msg, panel)
