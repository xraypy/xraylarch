#!/usr/bin/env python
"""

"""
import os
import numpy as np
np.seterr(all='ignore')

from functools import partial

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.flatnotebook as fnb
from wxmplot import PlotPanel
from wxutils import (SimpleText, FloatCtrl, pack, Button,
                     Choice,  Check, MenuItem, GUIColors,
                     CEN, RCEN, LCEN, FRAMESTYLE, Font)

import larch
from larch import Group
from larch_plugins.io import fix_varname

CEN |=  wx.ALL
FNB_STYLE = fnb.FNB_NO_X_BUTTON|fnb.FNB_SMART_TABS
FNB_STYLE |= fnb.FNB_NO_NAV_BUTTONS|fnb.FNB_NODRAG


XPRE_OPS = ('', 'log(', '-log(')
YPRE_OPS = ('', 'log(', '-log(')
ARR_OPS = ('+', '-', '*', '/')

YERR_OPS = ('Constant', 'Sqrt(Y)', 'Array')
CONV_OPS  = ('Lorenztian', 'Gaussian')

DATATYPES = ('raw', 'xas')

class EditColumnFrame(wx.Frame) :
    """Edit Column Labels for a larch grouop"""
    def __init__(self, parent, group, on_ok=None, _larch=None):

        self.group = group
        self.on_ok = on_ok
        self._larch = _larch

        wx.Frame.__init__(self, None, -1, 'Edit Array Names',
                          style=wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.SetFont(Font(10))

        sizer = wx.GridBagSizer(4, 4)
        if not hasattr(group, 'orig_array_labels'):
            group.orig_array_labels = group.array_labels[:]


        self.SetMinSize((600, 600))
        self.colors = GUIColors()

        self.wids = {}

        cind = SimpleText(self, label='Column')
        cold = SimpleText(self, label='Current Name')
        cnew = SimpleText(self, label='Enter New Name')
        cret = SimpleText(self, label='  Result   ', size=(150, -1))
        cinfo = SimpleText(self, label='   Data Range')

        ir = 0
        sizer.Add(cind,  (ir, 0), (1, 1), LCEN, 3)
        sizer.Add(cold,  (ir, 1), (1, 1), LCEN, 3)
        sizer.Add(cnew,  (ir, 2), (1, 1), LCEN, 3)
        sizer.Add(cret,  (ir, 3), (1, 1), LCEN, 3)
        sizer.Add(cinfo, (ir, 4), (1, 1), LCEN, 3)

        for i, name in enumerate(group.array_labels):
            ir += 1
            cind = SimpleText(self, label='  %i ' % (i+1))
            cold = SimpleText(self, label=' %s ' % name)
            cret = SimpleText(self, label=fix_varname(name), size=(150, -1))
            cnew = wx.TextCtrl(self,  value=name, size=(150, -1))
            cnew.Bind(wx.EVT_KILL_FOCUS, partial(self.update, index=i))
            cnew.Bind(wx.EVT_CHAR, partial(self.update_char, index=i))
            cnew.Bind(wx.EVT_TEXT_ENTER, partial(self.update, index=i))

            # cnew.Bind(wx.EVT_TEXT,       partial(self.update3, index=i))

            arr = getattr(group, name)
            info_str = " [ %8g : %8g ] " % (arr.min(), arr.max())
            cinfo = SimpleText(self, label=info_str)
            self.wids[i] = cnew
            self.wids["ret_%i" % i] = cret

            sizer.Add(cind,  (ir, 0), (1, 1), LCEN, 3)
            sizer.Add(cold,  (ir, 1), (1, 1), LCEN, 3)
            sizer.Add(cnew,  (ir, 2), (1, 1), LCEN, 3)
            sizer.Add(cret,  (ir, 3), (1, 1), LCEN, 3)
            sizer.Add(cinfo, (ir, 4), (1, 1), LCEN, 3)

        sizer.Add(Button(self, 'OK', action=self.onOK), (ir+1, 1), (1, 2), LCEN, 3)
        pack(self, sizer)
        self.Show()
        self.Raise()

    def update(self, evt=None, index=-1):
        newval = fix_varname(self.wids[index].GetValue())
        self.wids["ret_%i" % index].SetLabel(newval)

    def update_char(self, evt=None, index=-1):
        if evt.GetKeyCode() == wx.WXK_RETURN:
            self.update(evt=evt, index=index)
        evt.Skip()

    def onOK(self, evt=None):
        group = self.group
        array_labels = []
        for name in group.array_labels:
            delattr(group, name)

        for i, name in enumerate(group.array_labels):
            newname = self.wids["ret_%i" % i].GetLabel()
            array_labels.append(newname)
            setattr(group, newname, group.data[i, :])

        group.array_labels = array_labels
        if callable(self.on_ok):
            self.on_ok(array_labels)

        self.Destroy()


class SelectColumnFrame(wx.Frame) :
    """Set Column Labels for a file"""
    def __init__(self, parent, group=None, last_array_sel=None,
                 read_ok_cb=None, edit_groupname=True,
                 _larch=None):
        self.parent = parent
        self.larch = _larch
        self.rawgroup = group
        self.subframes = {}
        self.outgroup  = Group(raw=group)
        for attr in ('path', 'filename', 'groupname', 'datatype'):
            setattr(self.outgroup, attr, getattr(group, attr, None))

        if self.outgroup.datatype is None:
            self.outgroup.datatype = 'raw'
            if ('energ' in self.rawgroup.array_labels[0].lower() or
                'energ' in self.rawgroup.array_labels[1].lower()):
                self.outgroup.datatype = 'xas'

        self.read_ok_cb = read_ok_cb

        self.array_sel = {'xpop': '', 'xarr': None,
                          'ypop': '', 'yop': '/',
                          'yarr1': None, 'yarr2': None,
                          'use_deriv': False}
        if last_array_sel is not None:
            self.array_sel.update(last_array_sel)

        if self.array_sel['yarr2'] is None and 'i0' in self.rawgroup.array_labels:
            self.array_sel['yarr2'] = 'i0'

        if self.array_sel['yarr1'] is None:
            if 'itrans' in self.rawgroup.array_labels:
                self.array_sel['yarr1'] = 'itrans'
            elif 'i1' in self.rawgroup.array_labels:
                self.array_sel['yarr1'] = 'i1'
        message = "Data Columns for %s" % self.rawgroup.filename
        wx.Frame.__init__(self, None, -1,
                          'Build Arrays from Data Columns for %s' % self.rawgroup.filename,
                          style=FRAMESTYLE)

        self.SetFont(Font(10))

        panel = wx.Panel(self)
        self.SetMinSize((600, 600))
        self.colors = GUIColors()

        # title row
        title = SimpleText(panel, message, font=Font(13),
                           colour=self.colors.title, style=LCEN)

        opts = dict(action=self.onUpdate, size=(120, -1))

        arr_labels = self.rawgroup.array_labels
        yarr_labels = arr_labels + ['1.0', '0.0', '']
        xarr_labels = arr_labels + ['<index>']

        self.xarr   = Choice(panel, choices=xarr_labels, **opts)
        self.yarr1  = Choice(panel, choices= arr_labels, **opts)
        self.yarr2  = Choice(panel, choices=yarr_labels, **opts)
        self.yerr_arr = Choice(panel, choices=yarr_labels, **opts)
        self.yerr_arr.Disable()

        self.datatype = Choice(panel, choices=DATATYPES, **opts)
        self.datatype.SetStringSelection(self.outgroup.datatype)


        opts['size'] = (50, -1)
        self.yop =  Choice(panel, choices=ARR_OPS, **opts)

        opts['size'] = (120, -1)

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
        bsizer.Add(Button(bpanel, 'OK', action=self.onOK), 4)
        bsizer.Add(Button(bpanel, 'Cancel', action=self.onCancel), 4)
        bsizer.Add(Button(bpanel, 'Edit Array Names', action=self.onEditNames), 4)
        pack(bpanel, bsizer)

        sizer = wx.GridBagSizer(4, 8)
        sizer.Add(title,     (0, 0), (1, 7), LCEN, 5)

        ir = 1
        sizer.Add(xlab,      (ir, 0), (1, 1), LCEN, 0)
        sizer.Add(self.xpop, (ir, 1), (1, 1), CEN, 0)
        sizer.Add(self.xarr, (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.xsuf, (ir, 3), (1, 1), CEN, 0)

        ir += 1
        sizer.Add(ylab,       (ir, 0), (1, 1), LCEN, 0)
        sizer.Add(self.ypop,  (ir, 1), (1, 1), CEN, 0)
        sizer.Add(self.yarr1, (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.yop,   (ir, 3), (1, 1), CEN, 0)
        sizer.Add(self.yarr2, (ir, 4), (1, 1), CEN, 0)
        sizer.Add(self.ysuf,  (ir, 5), (1, 1), CEN, 0)
        sizer.Add(self.use_deriv, (ir, 6), (1, 1), LCEN, 0)

        ir += 1
        sizer.Add(yerr_lab,      (ir, 0), (1, 1), LCEN, 0)
        sizer.Add(self.yerr_op,  (ir, 1), (1, 1), CEN, 0)
        sizer.Add(self.yerr_arr, (ir, 2), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, 'Value:'), (ir, 3), (1, 1), CEN, 0)
        sizer.Add(self.yerr_const, (ir, 4), (1, 2), CEN, 0)

        ir += 1
        sizer.Add(SimpleText(panel, 'Data Type:'),  (ir, 0), (1, 1), LCEN, 0)
        sizer.Add(self.datatype,                    (ir, 1), (1, 2), LCEN, 0)

        ir += 1
        self.wid_groupname = wx.TextCtrl(panel, value=self.rawgroup.groupname,
                                         size=(120, -1))
        if not edit_groupname:
            self.wid_groupname.Disable()

        sizer.Add(SimpleText(panel, 'Group Name:'), (ir, 0), (1, 1), LCEN, 0)
        sizer.Add(self.wid_groupname,               (ir, 1), (1, 1), LCEN, 0)


        ir += 1
        sizer.Add(bpanel,     (ir, 0), (1, 5), LCEN, 3)

        pack(panel, sizer)

        self.nb = fnb.FlatNotebook(self, -1, agwStyle=FNB_STYLE)
        self.nb.SetTabAreaColour(wx.Colour(248,248,240))
        self.nb.SetActiveTabColour(wx.Colour(254,254,195))
        self.nb.SetNonActiveTabTextColour(wx.Colour(40,40,180))
        self.nb.SetActiveTabTextColour(wx.Colour(80,0,0))

        self.plotpanel = PlotPanel(self, messenger=self.plot_messages)
        textpanel = wx.Panel(self)
        ftext = wx.TextCtrl(textpanel, style=wx.TE_MULTILINE|wx.TE_READONLY,
                               size=(400, 250))
        try:
            m = open(self.rawgroup.filename, 'r')
            text = m.read()
            m.close()
        except:
            text = "The file '%s'\n could not be read" % self.rawgroup.filename
        ftext.SetValue(text)
        ftext.SetFont(Font(11))

        textsizer = wx.BoxSizer(wx.VERTICAL)
        textsizer.Add(ftext, 1, LCEN|wx.GROW, 1)
        pack(textpanel, textsizer)

        self.nb.AddPage(textpanel, ' Text of Data File ', True)
        self.nb.AddPage(self.plotpanel, ' Plot of Selected Arrays ', True)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 0, wx.GROW|wx.ALL, 2)
        mainsizer.Add(self.nb, 1, LCEN|wx.GROW,   2)
        pack(self, mainsizer)

        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-1, -1])
        statusbar_fields = [self.rawgroup.filename, ""]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        self.Show()
        self.Raise()
        self.onUpdate(self)

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

    def onEditNames(self, evt=None):
        self.show_subframe('editcol', EditColumnFrame,
                           group=self.rawgroup,
                           on_ok=self.set_array_labels,
                           _larch=self.larch)

    def set_array_labels(self, array_labels):
        arr_labels = self.rawgroup.array_labels
        yarr_labels = arr_labels + ['1.0', '0.0', '']
        xarr_labels = arr_labels + ['<index>']

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
        if self.wid_groupname is not None:
            self.outgroup.groupname = fix_varname(self.wid_groupname.GetValue())

        yerr_op = self.yerr_op.GetStringSelection().lower()
        if yerr_op.startswith('const'):
            self.outgroup.yerr = self.yerr_const.GetValue()
        elif yerr_op.startswith('array'):
            yerr = self.yerr_arr.GetStringSelection().strip()
            self.outgroup.yerr = get_data(rawgroup, yerr)
        elif yerr_op.startswith('sqrt'):
            self.outgroup.yerr = np.sqrt(outgroup.ydat)

        if self.read_ok_cb is not None:
            self.read_ok_cb(self.outgroup, array_sel=self.array_sel)
        self.Destroy()

    def onCancel(self, event=None):
        self.outgroup.import_ok = False
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
        rawgroup = self.rawgroup
        outgroup = self.outgroup

        ix  = self.xarr.GetSelection()
        xname = self.xarr.GetStringSelection()
        if xname.startswith('<index'):
            xname = self.rawgroup.array_labels[0]
            rawgroup._index = 1.0*np.arange(len(getattr(rawgroup, xname)))
            xname = '_index'

        outgroup.datatype = self.datatype.GetStringSelection().strip().lower()
        outgroup.xdat = getattr(rawgroup, xname)

        def pre_op(opwid, arr):
            opstr = opwid.GetStringSelection().strip()
            suf = ''
            if opstr in ('-log(', 'log('):
                suf = ')'
                if opstr == 'log(':
                    arr = np.log(arr)
                elif opstr == '-log(':
                    arr = -np.log(arr)
            return suf, opstr, arr

        try:
            xsuf, xpop, outgroup.xdat = pre_op(self.xpop, outgroup.xdat)
            self.xsuf.SetLabel(xsuf)
        except:
            return
        try:
            xunits = rawgroup.array_units[ix].strip()
            xlabel = '%s (%s)' % (xname, xunits)
        except:
            xlabel = xname


        def get_data(grp, arrayname, correct=False):
            if hasattr(grp, 'get_data'):
                return grp.get_data(arrayname, correct=correct)
            return getattr(grp, arrayname, None)

        yname1  = self.yarr1.GetStringSelection().strip()
        yname2  = self.yarr2.GetStringSelection().strip()
        yop = self.yop.GetStringSelection().strip()

        ylabel = yname1
        if len(yname2) == 0:
            yname2 = '1.0'
        else:
            ylabel = "%s%s%s" % (ylabel, yop, yname2)

        yarr1 = get_data(rawgroup, yname1, correct=dtcorr)

        if yname2 in ('0.0', '1.0'):
            yarr2 = float(yname2)
            if yop == '/': yarr2 = 1.0
        else:
            yarr2 = get_data(rawgroup, yname2, correct=dtcorr)

        outgroup.ydat = yarr1
        if yop == '+':
            outgroup.ydat = yarr1.__add__(yarr2)
        elif yop == '-':
            outgroup.ydat = yarr1.__sub__(yarr2)
        elif yop == '*':
            outgroup.ydat = yarr1.__mul__(yarr2)
        elif yop == '/':
            outgroup.ydat = yarr1.__truediv__(yarr2)

        yerr_op = self.yerr_op.GetStringSelection().lower()
        if yerr_op.startswith('const'):
            yerr = self.yerr_const.GetValue()
        elif yerr_op.startswith('array'):
            yerr = self.yerr_arr.GetStringSelection().strip()
            yerr = get_data(rawgroup, yerr)
        elif yerr_op.startswith('sqrt'):
            yerr = np.sqrt(outgroup.ydat)


        ysuf, ypop, outgroup.ydat = pre_op(self.ypop, outgroup.ydat)
        self.ysuf.SetLabel(ysuf)

        if use_deriv:
            try:
                outgroup.ydat = (np.gradient(outgroup.ydat) /
                                 np.gradient(outgroup.xdat))
            except:
                pass

        self.array_sel = {'xpop': xpop, 'xarr': xname,
                     'ypop': ypop, 'yop': yop,
                     'yarr1': yname1, 'yarr2': yname2,
                     'use_deriv': use_deriv}

        try:
            npts = min(len(outgroup.xdat), len(outgroup.ydat))
        except AttributeError:
            return

        outgroup.filename    = rawgroup.filename
        outgroup.npts        = npts
        outgroup.plot_xlabel = xlabel
        outgroup.plot_ylabel = ylabel
        outgroup.xdat        = np.array(outgroup.xdat[:npts])
        outgroup.ydat        = np.array(outgroup.ydat[:npts])
        outgroup.y           = outgroup.ydat
        outgroup.yerr        = yerr
        if isinstance(yerr, np.ndarray):
            outgroup.yerr    = np.array(yerr[:npts])

        if outgroup.datatype == 'xas':
            outgroup.energy = outgroup.xdat
            outgroup.mu     = outgroup.ydat

        path, fname = os.path.split(outgroup.filename)
        popts = dict(marker='o', markersize=4, linewidth=1.5,
                     title=fname, ylabel=ylabel, xlabel=xlabel,
                     label="%s: %s" % (fname, outgroup.plot_ylabel))

        self.plotpanel.plot(outgroup.xdat, outgroup.ydat, **popts)

        for i in range(self.nb.GetPageCount()):
            if 'plot' in self.nb.GetPageText(i).lower():
                self.nb.SetSelection(i)

    def plot_messages(self, msg, panel=1):
        self.SetStatusText(msg, panel)
