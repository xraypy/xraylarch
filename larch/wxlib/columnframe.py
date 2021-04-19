#!/usr/bin/env python
"""

"""
import os
import re
import numpy as np
np.seterr(all='ignore')

from functools import partial

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb
from wxmplot import PlotPanel

from wxutils import (SimpleText, FloatCtrl, GUIColors, Button, Choice,
                     pack, Popup, Check, MenuItem, CEN, RIGHT, LEFT,
                     FRAMESTYLE, HLine, Font)

import larch
from larch import Group
from larch.utils.strutils import fix_varname, file2groupname
from larch.io import look_for_nans

CEN |=  wx.ALL
FNB_STYLE = fnb.FNB_NO_X_BUTTON|fnb.FNB_SMART_TABS
FNB_STYLE |= fnb.FNB_NO_NAV_BUTTONS|fnb.FNB_NODRAG

XPRE_OPS = ('', 'log(', '-log(')
YPRE_OPS = ('', 'log(', '-log(')
ARR_OPS = ('+', '-', '*', '/')

YERR_OPS = ('Constant', 'Sqrt(Y)', 'Array')
CONV_OPS  = ('Lorenztian', 'Gaussian')

DATATYPES = ('raw', 'xas')

class AddColumnsFrame(wx.Frame):
    """Add Column Labels for a larch grouop"""
    def __init__(self, parent, group, on_ok=None):
        self.parent = parent
        self.group = group
        self.on_ok = on_ok
        wx.Frame.__init__(self, None, -1, 'Add Selected Columns',
                          style=wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.SetFont(Font(10))
        sizer = wx.GridBagSizer(2, 2)
        panel = scrolled.ScrolledPanel(self)

        self.SetMinSize((550, 550))

        self.wids = {}

        lab_aname = SimpleText(panel, label=' Save Array Name:')
        lab_range = SimpleText(panel, label=' Use column index:')
        lab_regex = SimpleText(panel, label=' Use column label:')

        wids = self.wids = {}

        wids['arrayname'] = wx.TextCtrl(panel, value='sum',   size=(175, -1))
        wids['tc_nums']   = wx.TextCtrl(panel, value='1,3-10', size=(175, -1))
        wids['tc_regex']  = wx.TextCtrl(panel, value='*fe*',  size=(175, -1))

        savebtn   = Button(panel, 'Save',       action=self.onOK)
        plotbtn   = Button(panel, 'Plot Sum',   action=self.onPlot)
        sel_nums  = Button(panel, 'Select by Index',
                           action=self.onSelColumns)
        sel_re    = Button(panel, 'Select by Pattern',
                           action=self.onSelRegex)


        sizer.Add(lab_aname,         (0, 0), (1, 2), LEFT, 3)
        sizer.Add(wids['arrayname'], (0, 2), (1, 1), LEFT, 3)

        sizer.Add(plotbtn,         (0, 3), (1, 1), LEFT, 3)
        sizer.Add(savebtn,         (0, 4), (1, 1), LEFT, 3)

        sizer.Add(lab_range,       (1, 0), (1, 2), LEFT, 3)
        sizer.Add(wids['tc_nums'], (1, 2), (1, 1), LEFT, 3)
        sizer.Add(sel_nums,        (1, 3), (1, 2), LEFT, 3)

        sizer.Add(lab_regex,        (2, 0), (1, 2), LEFT, 3)
        sizer.Add(wids['tc_regex'], (2, 2), (1, 1), LEFT, 3)
        sizer.Add(sel_re,           (2, 3), (1, 2), LEFT, 3)

        sizer.Add(HLine(panel, size=(550, 2)), (3, 0), (1, 5), LEFT, 3)
        ir = 4

        cind = SimpleText(panel, label=' Index ')
        csel = SimpleText(panel, label=' Select ')
        cname = SimpleText(panel, label=' Array Name ')

        sizer.Add(cind,  (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(csel,  (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(cname, (ir, 2), (1, 3), LEFT, 3)

        for i, name in enumerate(group.array_labels):
            ir += 1
            cind = SimpleText(panel, label='  %i ' % (i+1))
            cname = SimpleText(panel, label=' %s ' % name)
            csel = Check(panel, label='', default=False)

            self.wids["col_%d" % i] = csel

            sizer.Add(cind,  (ir, 0), (1, 1), LEFT, 3)
            sizer.Add(csel,  (ir, 1), (1, 1), LEFT, 3)
            sizer.Add(cname, (ir, 2), (1, 3), LEFT, 3)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def make_sum(self):
        sel =[]
        for name, wid in self.wids.items():
            if name.startswith('col_') and wid.IsChecked():
                sel.append(int(name[4:]))
        self.selected_columns = np.array(sel)
        narr, npts = self.group.raw.data.shape
        ydat = np.zeros(npts, dtype=np.float)
        for i in sel:
            ydat += self.group.raw.data[i, :]
        return ydat

    def get_label(self):
        label_in = self.wids["arrayname"].GetValue()
        label = fix_varname(label_in)
        if label in self.group.array_labels:
            count = 1
            while label in self.group.array_labels and count < 1000:
                label = "%s_%d" % (label, count)
                count +=1
        if label != label_in:
            self.wids["arrayname"].SetValue(label)
        return label

    def onOK(self, event=None):
        ydat = self.make_sum()
        npts = len(ydat)
        label = self.get_label()

        self.group.array_labels.append(label)
        new = np.append(self.group.raw.data, ydat.reshape(1, npts), axis=0)
        self.group.raw.data = new
        self.on_ok(label, self.selected_columns)

    def onPlot(self, event=None):
        ydat = self.make_sum()
        xdat = self.group.xdat
        label = self.get_label()
        label = "%s (not saved)" % label
        popts = dict(marker='o', markersize=4, linewidth=1.5, ylabel=label,
                     label=label, xlabel=self.group.plot_xlabel)
        self.parent.plotpanel.plot(xdat, ydat, **popts)


    def onSelColumns(self, event=None):
        pattern = self.wids['tc_nums'].GetValue().split(',')
        sel = []
        for part in pattern:
            if '-' in part:
                start, stop = part.split('-')
                try:
                    istart = int(start)
                except ValueError:
                    istart = 1
                try:
                    istop = int(stop)
                except ValueError:
                    istop = len(self.group.array_labels) + 1

                sel.extend(range(istart-1, istop))
            else:
                try:
                    sel.append(int(part)-1)
                except:
                    pass

        for name, wid in self.wids.items():
            if name.startswith('col_'):
                wid.SetValue(int(name[4:]) in sel)

    def onSelRegex(self, event=None):
        pattern = self.wids['tc_regex'].GetValue().replace('*', '.*')
        pattern = pattern.replace('..*', '.*')
        sel =[]
        for i, name in enumerate(self.group.array_labels):
            sel = re.search(pattern, name, flags=re.IGNORECASE) is not None
            self.wids["col_%d" % i].SetValue(sel)


class EditColumnFrame(wx.Frame) :
    """Edit Column Labels for a larch grouop"""
    def __init__(self, parent, group, on_ok=None):
        self.parent = parent
        self.group = group
        self.on_ok = on_ok
        wx.Frame.__init__(self, None, -1, 'Edit Array Names',
                          style=wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.SetFont(Font(10))
        sizer = wx.GridBagSizer(2, 2)
        panel = scrolled.ScrolledPanel(self)

        self.SetMinSize((675, 450))

        self.wids = {}
        ir = 0
        sizer.Add(Button(panel, 'Apply Changes', size=(200, -1),
                         action=self.onOK),
                  (0, 1), (1, 2), LEFT, 3)
        sizer.Add(Button(panel, 'Use Column Number', size=(200, -1),
                         action=self.onColNumber),
                  (0, 3), (1, 2), LEFT, 3)
        sizer.Add(HLine(panel, size=(550, 2)),
                  (1, 1), (1, 5), LEFT, 3)

        cind = SimpleText(panel, label='Column')
        cold = SimpleText(panel, label='Current Name')
        cnew = SimpleText(panel, label='Enter New Name')
        cret = SimpleText(panel, label='  Result   ', size=(150, -1))
        cinfo = SimpleText(panel, label='   Data Range')
        cplot = SimpleText(panel, label='   Plot')

        ir = 2
        sizer.Add(cind,  (ir, 0), (1, 1), LEFT, 3)
        sizer.Add(cold,  (ir, 1), (1, 1), LEFT, 3)
        sizer.Add(cnew,  (ir, 2), (1, 1), LEFT, 3)
        sizer.Add(cret,  (ir, 3), (1, 1), LEFT, 3)
        sizer.Add(cinfo, (ir, 4), (1, 1), LEFT, 3)
        sizer.Add(cplot, (ir, 5), (1, 1), LEFT, 3)

        for i, name in enumerate(group.array_labels):
            ir += 1
            cind = SimpleText(panel, label='  %i ' % (i+1))
            cold = SimpleText(panel, label=' %s ' % name)
            cret = SimpleText(panel, label=fix_varname(name), size=(150, -1))
            cnew = wx.TextCtrl(panel,  value=name, size=(150, -1))

            cnew.Bind(wx.EVT_KILL_FOCUS, partial(self.update, index=i))
            cnew.Bind(wx.EVT_CHAR, partial(self.update_char, index=i))
            cnew.Bind(wx.EVT_TEXT_ENTER, partial(self.update, index=i))

            arr = group.data[i,:]
            info_str = " [ %8g : %8g ] " % (arr.min(), arr.max())
            cinfo = SimpleText(panel, label=info_str)
            cplot = Button(panel, 'Plot', action=partial(self.onPlot, index=i))


            self.wids["%d" % i] = cnew
            self.wids["ret_%d" % i] = cret

            sizer.Add(cind,  (ir, 0), (1, 1), LEFT, 3)
            sizer.Add(cold,  (ir, 1), (1, 1), LEFT, 3)
            sizer.Add(cnew,  (ir, 2), (1, 1), LEFT, 3)
            sizer.Add(cret,  (ir, 3), (1, 1), LEFT, 3)
            sizer.Add(cinfo, (ir, 4), (1, 1), LEFT, 3)
            sizer.Add(cplot, (ir, 5), (1, 1), LEFT, 3)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def onPlot(self, event=None, index=None):
        if index is not None:
            x = self.parent.workgroup.index
            y = self.parent.workgroup.data[index, :]
            label = self.wids["ret_%i" % index].GetLabel()
            popts = dict(marker='o', markersize=4, linewidth=1.5,
                         ylabel=label, xlabel='data point', label=label)
            self.parent.plotpanel.plot(x, y, **popts)

    def onColNumber(self, evt=None, index=-1):
        for name, wid in self.wids.items():
            val = name
            if name.startswith('ret_'):
                val = name[4:]
                setter = wid.SetLabel
            else:
                setter = wid.SetValue
            setter("col_%d" % (int(val) +1))

    def update(self, evt=None, index=-1):
        newval = fix_varname(self.wids["%d" % index].GetValue())
        self.wids["ret_%i" % index].SetLabel(newval)

    def update_char(self, evt=None, index=-1):
        if evt.GetKeyCode() == wx.WXK_RETURN:
            self.update(evt=evt, index=index)
        evt.Skip()

    def onOK(self, evt=None):
        group = self.group
        array_labels = []
        for i in range(len(self.group.array_labels)):
            newname = self.wids["ret_%i" % i].GetLabel()
            array_labels.append(newname)

        if callable(self.on_ok):
            self.on_ok(array_labels)
        self.Destroy()

class ColumnDataFileFrame(wx.Frame) :
    """Column Data File, select columns"""
    def __init__(self, parent, filename=None, groupname=None,
                 last_array_sel=None, read_ok_cb=None,
                 edit_groupname=True, _larch=None):
        self.parent = parent
        self._larch = _larch
        self.path = filename
        self.extra_sums = {}

        group = self.initgroup = self.read_column_file(self.path)

        self.subframes = {}
        self.workgroup  = Group(raw=group)
        for attr in ('path', 'filename', 'groupname', 'datatype',
                     'array_labels', 'data'):
            setattr(self.workgroup, attr, getattr(group, attr, None))

        arr_labels = [l.lower() for l in self.initgroup.array_labels]
        self.orig_labels = arr_labels[:]

        if self.workgroup.datatype is None:
            self.workgroup.datatype = 'raw'
            for arrlab in arr_labels[:4]:
                if 'energ' in arrlab:
                    self.workgroup.datatype = 'xas'

        self.read_ok_cb = read_ok_cb
        self.array_sel = {'xpop': '',  'xarr': None,
                          'ypop': '',  'yop': '/',
                          'yarr1': None, 'yarr2': None, 'use_deriv': False}

        if last_array_sel is not None:
            self.array_sel.update(last_array_sel)

        if self.array_sel['yarr2'] is None and 'i0' in arr_labels:
            self.array_sel['yarr2'] = 'i0'

        if self.array_sel['yarr1'] is None:
            if 'itrans' in arr_labels:
                self.array_sel['yarr1'] = 'itrans'
            elif 'i1' in arr_labels:
                self.array_sel['yarr1'] = 'i1'
        message = "Data Columns for %s" % group.filename
        wx.Frame.__init__(self, None, -1,
                          'Build Arrays from Data Columns for %s' % group.filename,
                          style=FRAMESTYLE)

        x0, y0 = parent.GetPosition()
        self.SetPosition((x0+60, y0+60))
        self.SetFont(Font(10))

        panel = wx.Panel(self)
        self.SetMinSize((600, 600))
        self.colors = GUIColors()

        # title row
        title = SimpleText(panel, message, font=Font(13),
                           colour=self.colors.title, style=LEFT)

        opts = dict(action=self.onUpdate, size=(120, -1))
        yarr_labels = self.yarr_labels = arr_labels + ['1.0', '0.0', '']
        xarr_labels = self.xarr_labels = arr_labels + ['_index']

        self.xarr   = Choice(panel, choices=xarr_labels, **opts)
        self.yarr1  = Choice(panel, choices= arr_labels, **opts)
        self.yarr2  = Choice(panel, choices=yarr_labels, **opts)
        self.yerr_arr = Choice(panel, choices=yarr_labels, **opts)
        self.yerr_arr.Disable()

        self.datatype = Choice(panel, choices=DATATYPES, **opts)
        self.datatype.SetStringSelection(self.workgroup.datatype)


        opts['size'] = (50, -1)
        self.yop =  Choice(panel, choices=ARR_OPS, **opts)

        opts['size'] = (150, -1)

        self.use_deriv = Check(panel, label='use derivative',
                               default=self.array_sel['use_deriv'], **opts)

        self.xpop = Choice(panel, choices=XPRE_OPS, **opts)
        self.ypop = Choice(panel, choices=YPRE_OPS, **opts)

        opts['action'] = self.onYerrChoice
        self.yerr_op = Choice(panel, choices=YERR_OPS, **opts)
        self.yerr_op.SetSelection(0)

        self.yerr_const = FloatCtrl(panel, value=1, precision=4, size=(90, -1))

        ylab = SimpleText(panel, 'Y = ')
        xlab = SimpleText(panel, 'X = ')
        yerr_lab = SimpleText(panel, 'Yerror = ')
        self.xsuf = SimpleText(panel, '')
        self.ysuf = SimpleText(panel, '')
        self.message = SimpleText(panel, '', font=Font(11),
                           colour=self.colors.title, style=LEFT)

        self.xpop.SetStringSelection(self.array_sel['xpop'])
        self.ypop.SetStringSelection(self.array_sel['ypop'])
        self.yop.SetStringSelection(self.array_sel['yop'])
        if '(' in self.array_sel['ypop']:
            self.ysuf.SetLabel(')')

        ixsel, iysel, iy2sel = 0, 1, len(yarr_labels)-1
        if self.array_sel['xarr'] in xarr_labels:
            ixsel = xarr_labels.index(self.array_sel['xarr'])
        if self.array_sel['yarr1'] in arr_labels:
            iysel = arr_labels.index(self.array_sel['yarr1'])
        if self.array_sel['yarr2'] in yarr_labels:
            iy2sel = yarr_labels.index(self.array_sel['yarr2'])
        self.xarr.SetSelection(ixsel)
        self.yarr1.SetSelection(iysel)
        self.yarr2.SetSelection(iy2sel)

        bpanel = wx.Panel(panel)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        _ok    = Button(bpanel, 'OK', action=self.onOK)
        _cancel = Button(bpanel, 'Cancel', action=self.onCancel)
        _edit   = Button(bpanel, 'Edit Array Names', action=self.onEditNames)
        _add    = Button(bpanel, 'Select Columns to Sum', action=self.onAddColumns)

        bsizer.Add(_ok)
        bsizer.Add(_cancel)
        bsizer.Add(_edit)
        bsizer.Add(_add)
        _ok.SetDefault()
        pack(bpanel, bsizer)

        sizer = wx.GridBagSizer(4, 8)
        sizer.Add(title,     (0, 0), (1, 7), LEFT, 5)

        ir = 1
        sizer.Add(xlab,      (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.xpop, (ir, 1), (1, 1), CEN, 0)
        sizer.Add(self.xarr, (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.xsuf, (ir, 3), (1, 1), CEN, 0)

        ir += 1
        sizer.Add(ylab,       (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.ypop,  (ir, 1), (1, 1), CEN, 0)
        sizer.Add(self.yarr1, (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.yop,   (ir, 3), (1, 1), CEN, 0)
        sizer.Add(self.yarr2, (ir, 4), (1, 1), CEN, 0)
        sizer.Add(self.ysuf,  (ir, 5), (1, 1), CEN, 0)
        sizer.Add(self.use_deriv, (ir, 6), (1, 1), LEFT, 0)

        ir += 1
        sizer.Add(yerr_lab,      (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.yerr_op,  (ir, 1), (1, 1), CEN, 0)
        sizer.Add(self.yerr_arr, (ir, 2), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, 'Value:'), (ir, 3), (1, 1), CEN, 0)
        sizer.Add(self.yerr_const, (ir, 4), (1, 2), CEN, 0)

        ir += 1
        sizer.Add(SimpleText(panel, 'Data Type:'),  (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.datatype,                    (ir, 1), (1, 2), LEFT, 0)

        self.wid_filename = wx.TextCtrl(panel, value=group.filename,
                                         size=(300, -1))
        self.wid_groupname = wx.TextCtrl(panel, value=group.groupname,
                                         size=(150, -1))
        if not edit_groupname:
            self.wid_groupname.Disable()

        ir += 1
        sizer.Add(SimpleText(panel, 'Displayed Name:'), (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.wid_filename,                (ir, 1), (1, 2), LEFT, 0)
        ir += 1
        sizer.Add(SimpleText(panel, 'Group/Code Name:'), (ir, 0), (1, 1), LEFT, 0)
        sizer.Add(self.wid_groupname,               (ir, 1), (1, 2), LEFT, 0)
        sizer.Add(self.message,                     (ir, 3), (1, 4), LEFT, 0)


        ir += 1
        sizer.Add(bpanel,     (ir, 0), (1, 5), LEFT, 3)

        pack(panel, sizer)

        self.nb = fnb.FlatNotebook(self, -1, agwStyle=FNB_STYLE)
        self.nb.SetTabAreaColour(wx.Colour(248,248,240))
        self.nb.SetActiveTabColour(wx.Colour(254,254,195))
        self.nb.SetNonActiveTabTextColour(wx.Colour(40,40,180))
        self.nb.SetActiveTabTextColour(wx.Colour(80,0,0))

        self.plotpanel = PlotPanel(self, messenger=self.plot_messages)
        self.plotpanel.SetMinSize((200, 200))
        textpanel = wx.Panel(self)
        ftext = wx.TextCtrl(textpanel, style=wx.TE_MULTILINE|wx.TE_READONLY,
                               size=(400, 250))

        ftext.SetValue(group.text)
        ftext.SetFont(Font(10))

        textsizer = wx.BoxSizer(wx.VERTICAL)
        textsizer.Add(ftext, 1, LEFT|wx.GROW, 1)
        pack(textpanel, textsizer)

        self.nb.AddPage(textpanel, ' Text of Data File ', True)
        self.nb.AddPage(self.plotpanel, ' Plot of Selected Arrays ', True)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 0, wx.GROW|wx.ALL, 2)
        mainsizer.Add(self.nb, 1, LEFT|wx.GROW,   2)
        pack(self, mainsizer)

        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-1, -1])
        statusbar_fields = [group.filename, ""]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        self.Show()
        self.Raise()
        self.onUpdate(self)

    def read_column_file(self, path):
        """read column file, generally as initial read"""
        parent, filename = os.path.split(path)
        with open(path, 'r') as fh:
            lines = fh.readlines()

        text = ''.join(lines)
        line1 = lines[0].lower()

        reader = 'read_ascii'
        if 'epics scan' in line1:
            reader = 'read_gsescan'
        if 'epics stepscan file' in line1:
            reader = 'read_gsexdi'
        if 'xdi' in line1:
            reader = 'read_xdi'
        if ("#s" in line1) or ("#f" in line1):
            reader = 'read_specfile'

        if reader in ('read_xdi', 'read_gsexdi'):
            # first check for Nans and Infs
            nan_result = look_for_nans(path)
            if 'read error' in nan_result.message:
                title = "Cannot read %s" % path
                message = "Error reading %s\n%s" %(path, nan_result.message)
                r = Popup(self.parent, message, title)
                return None
            if 'no data' in nan_result.message:
                title = "No data in %s" % path
                message = "No data found in file %s" % path
                r = Popup(self.parent, message, title)
                return None

            if ('has nans' in nan_result.message or
                'has infs' in nan_result.message):
                reader = 'read_ascii'

        tmpname = '_tmp_file_'
        read_cmd = "%s = %s('%s')" % (tmpname, reader, path)
        self.reader = reader
        _larch = self._larch
        if (not isinstance(_larch, larch.Interpreter) and
            hasattr(_larch, '_larch')):
            _larch = _larch._larch
        try:
            _larch.eval(read_cmd, add_history=True)
        except:
            pass
        if _larch.error:
            msg = ["Error trying to read '%s':" % path, ""]
            for err in _larch.error:
                exc_name, errmsg = err.get_error()
                msg.append(errmsg)

            title = "Cannot read %s" % path
            r = Popup(self.parent, "\n".join(msg), title)
            return None
        group = _larch.symtable.get_symbol(tmpname)
        # _larch.symtable.del_symbol(tmpname)

        group.text = text
        group.path = path
        group.filename = filename
        group.groupname = file2groupname(filename,
                                         symtable=self._larch.symtable)
        return group

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


    def onAddColumns(self, event=None):
        self.show_subframe('addcol', AddColumnsFrame,
                           group=self.workgroup,
                           on_ok=self.add_columns)

    def add_columns(self, label, selection):
        new_labels = self.workgroup.array_labels
        self.set_array_labels(new_labels)
        self.yarr1.SetStringSelection(new_labels[-1])
        self.extra_sums[label] = selection
        self.onUpdate()

    def onEditNames(self, evt=None):
        self.show_subframe('editcol', EditColumnFrame,
                           group=self.workgroup,
                           on_ok=self.set_array_labels)

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

    def onOK(self, event=None):
        """ build arrays according to selection """
        user_filename = self.wid_filename.GetValue()
        if self.wid_groupname is not None:
            groupname = fix_varname(self.wid_groupname.GetValue())

        yerr_op = self.yerr_op.GetStringSelection().lower()
        yerr_expr = '1'
        if yerr_op.startswith('const'):
            yerr_expr = "%f" % self.yerr_const.GetValue()
        elif yerr_op.startswith('array'):
            yerr_expr = '%%s.data[%i, :]' % self.yerr_arr.GetSelection()
        elif yerr_op.startswith('sqrt'):
            yerr_expr = 'sqrt(%s.ydat)'
        self.expressions['yerr'] = yerr_expr

        # generate script to pass back to calling program:
        read_cmd = "%s('{path}', labels='%s')" % (self.reader,
                                                  ', '.join(self.orig_labels))
        buff = ["{group} = %s" % read_cmd,
                "{group}.path = '{path}'",
                "{group}.is_frozen = False"]

        for label, selection in self.extra_sums.items():
            buff.append("{group}.array_labels.append('%s')" % label)
            buff.append("_tmparr = {group}.data[%s, :].sum(axis=0)" % repr(selection))
            buff.append("_tmpn   = len(_tmparr)")
            buff.append("{group}.data = append({group}.data, _tmparr.reshape(1, _tmpn), axis=0)")
            buff.append("del _tmparr, _tmpn")


        for attr in ('datatype', 'plot_xlabel', 'plot_ylabel'):
            val = getattr(self.workgroup, attr)
            buff.append("{group}.%s = '%s'" % (attr, val))

        for aname in ('xdat', 'ydat', 'yerr'):
            expr = self.expressions[aname].replace('%s', '{group:s}')
            buff.append("{group}.%s = %s" % (aname, expr))

        if getattr(self.workgroup, 'datatype', 'raw') == 'xas':
            if self.reader == 'read_gsescan':
                buff.append("{group}.energy = {group}.x")
            else:
                buff.append("{group}.energy = {group}.xdat")
            buff.append("{group}.mu = {group}.ydat")
            buff.append("sort_xafs({group}, overwrite=True, fix_repeats=True)")
        else:
            buff.append("{group}.scale = 1./({group}.ydat.ptp()+1.e-16)")
        script = "\n".join(buff)

        if self.read_ok_cb is not None:
            self.read_ok_cb(script, self.path, groupname=groupname,
                            filename=user_filename,
                            array_sel=self.array_sel)

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
        self.yerr_const.Disable()
        if 'const' in yerr_choice.lower():
            self.yerr_const.Enable()
        elif 'array' in yerr_choice.lower():
            self.yerr_arr.Enable()
        self.onUpdate()


    def onUpdate(self, value=None, evt=None):
        """column selections changed calc xdat and ydat"""
        # dtcorr = self.dtcorr.IsChecked()

        dtcorr = False
        use_deriv = self.use_deriv.IsChecked()
        rawgroup = self.initgroup
        workgroup = self.workgroup
        rdata = self.initgroup.data

        ix  = self.xarr.GetSelection()
        xname = self.xarr.GetStringSelection()

        exprs = dict(xdat=None, ydat=None, yerr=None)

        ncol, npts = rdata.shape
        workgroup.index = 1.0*np.arange(npts)
        if xname.startswith('_index') or ix >= ncol:
            workgroup.xdat = 1.0*np.arange(npts)
            xname = '_index'
            exprs['xdat'] = 'arange(%i)' % npts
        else:
            workgroup.xdat = rdata[ix, :]
            exprs['xdat'] = '%%s.data[%i, : ]' % ix

        workgroup.datatype = self.datatype.GetStringSelection().strip().lower()

        def pre_op(opwid, arr):
            opstr = opwid.GetStringSelection().strip()
            suf = ''
            if opstr in ('-log(', 'log('):
                suf = ')'
                if opstr == 'log(':
                    arr = np.log(arr)
                elif opstr == '-log(':
                    arr = -np.log(arr)
                arr[np.where(np.isnan(arr))] = 0
            return suf, opstr, arr

        try:
            xsuf, xpop, workgroup.xdat = pre_op(self.xpop, workgroup.xdat)
            self.xsuf.SetLabel(xsuf)
            exprs['xdat'] = '%s%s%s' % (xpop, exprs['xdat'], xsuf)
        except:
            return

        try:
            xunits = rawgroup.array_units[ix].strip()
            xlabel = '%s (%s)' % (xname, xunits)
        except:
            xlabel = xname

        yname1  = self.yarr1.GetStringSelection().strip()
        yname2  = self.yarr2.GetStringSelection().strip()
        iy1    = self.yarr1.GetSelection()
        iy2    = self.yarr2.GetSelection()
        yop = self.yop.GetStringSelection().strip()

        ylabel = yname1
        if len(yname2) == 0:
            yname2 = '1.0'
        else:
            ylabel = "%s%s%s" % (ylabel, yop, yname2)

        if yname1 == '0.0':
            yarr1 = np.zeros(npts)*1.0
            yexpr1 = 'zeros(%i)' % npts
        elif len(yname1) == 0 or yname1 == '1.0' or iy1 >= ncol:
            yarr1 = np.ones(npts)*1.0
            yexpr1 = 'ones(%i)' % npts
        else:
            yarr1 = rdata[iy1, :]
            yexpr1 = '%%s.data[%i, : ]' % iy1

        if yname2 == '0.0':
            yarr2 = np.zeros(npts)*1.0
            yexpr2 = '0.0'
        elif len(yname2) == 0 or yname2 == '1.0' or iy2 >= ncol:
            yarr2 = np.ones(npts)*1.0
            yexpr2 = '1.0'
        else:
            yarr2 = rdata[iy2, :]
            yexpr2 = '%%s.data[%i, : ]' % iy2

        workgroup.ydat = yarr1

        exprs['ydat'] = yexpr1
        if yop in ('+', '-', '*', '/'):
            exprs['ydat'] = "%s %s %s" % (yexpr1, yop, yexpr2)
            if yop == '+':
                workgroup.ydat = yarr1.__add__(yarr2)
            elif yop == '-':
                workgroup.ydat = yarr1.__sub__(yarr2)
            elif yop == '*':
                workgroup.ydat = yarr1.__mul__(yarr2)
            elif yop == '/':
                workgroup.ydat = yarr1.__truediv__(yarr2)

        ysuf, ypop, workgroup.ydat = pre_op(self.ypop, workgroup.ydat)
        self.ysuf.SetLabel(ysuf)
        exprs['ydat'] = '%s%s%s' % (ypop, exprs['ydat'], ysuf)

        yerr_op = self.yerr_op.GetStringSelection().lower()
        exprs['yerr'] = '1'
        if yerr_op.startswith('const'):
            yerr = self.yerr_const.GetValue()
            exprs['yerr'] = '%f' % yerr
        elif yerr_op.startswith('array'):
            iyerr = self.yerr_arr.GetSelection()
            yerr = rdata[iyerr, :]
            exprs['yerr'] = '%%s.data[%i, :]' % iyerr
        elif yerr_op.startswith('sqrt'):
            yerr = np.sqrt(workgroup.ydat)
            exprs['yerr'] = 'sqrt(%s.ydat)'

        if use_deriv:
            try:
                workgroup.ydat = (np.gradient(workgroup.ydat) /
                                 np.gradient(workgroup.xdat))
                exprs['ydat'] = 'deriv(%s)/deriv(%s)' % (exprs['ydat'],
                                                         exprs['xdat'])
            except:
                pass

        self.expressions = exprs
        self.array_sel = {'xpop': xpop, 'xarr': xname,
                          'ypop': ypop, 'yop': yop,
                          'yarr1': yname1, 'yarr2': yname2,
                          'use_deriv': use_deriv}

        try:
            npts = min(len(workgroup.xdat), len(workgroup.ydat))
        except AttributeError:
            return
        except ValueError:
            return

        en = workgroup.xdat
        if ((workgroup.datatype == 'xas') and
            ((len(en) > 1000 or any(np.diff(en) < 0) or
              ((max(en)-min(en)) > 350 and
               (np.diff(en[:100]).mean() < 1.0))))):
            self.message.SetLabel("Warning: XAS data may need to be rebinned!")
        else:
            self.message.SetLabel("")

        workgroup.filename    = rawgroup.filename
        workgroup.npts        = npts
        workgroup.plot_xlabel = xlabel
        workgroup.plot_ylabel = ylabel
        workgroup.xdat        = np.array(workgroup.xdat[:npts])
        workgroup.ydat        = np.array(workgroup.ydat[:npts])
        workgroup.y           = workgroup.ydat
        workgroup.yerr        = yerr
        if isinstance(yerr, np.ndarray):
            workgroup.yerr    = np.array(yerr[:npts])

        if workgroup.datatype == 'xas':
            workgroup.energy = workgroup.xdat
            workgroup.mu     = workgroup.ydat

        path, fname = os.path.split(workgroup.filename)
        popts = dict(marker='o', markersize=4, linewidth=1.5,
                     title=fname, ylabel=ylabel, xlabel=xlabel,
                     label="%s: %s" % (fname, workgroup.plot_ylabel))

        self.plotpanel.plot(workgroup.xdat, workgroup.ydat, **popts)

        for i in range(self.nb.GetPageCount()):
            if 'plot' in self.nb.GetPageText(i).lower():
                self.nb.SetSelection(i)

    def plot_messages(self, msg, panel=1):
        self.SetStatusText(msg, panel)
