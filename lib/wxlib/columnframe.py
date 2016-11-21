#!/usr/bin/env python
"""

"""
import os
import numpy as np
np.seterr(all='ignore')

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
from larch_plugins.math.smoothing import (savitzky_golay, smooth, boxcar)

CEN |=  wx.ALL
FNB_STYLE = fnb.FNB_NO_X_BUTTON|fnb.FNB_SMART_TABS
FNB_STYLE |= fnb.FNB_NO_NAV_BUTTONS|fnb.FNB_NODRAG


XPRE_OPS = ('', 'log(', '-log(')
YPRE_OPS = ('', 'log(', '-log(')
ARR_OPS = ('+', '-', '*', '/')

YERR_OPS = ('Constant', 'Sqrt(Y)', 'Array')
SMOOTH_OPS = ('None', 'Boxcar', 'Savitzky-Golay', 'Convolution')
CONV_OPS  = ('Lorenztian', 'Gaussian')

DATATYPES = ('raw', 'xas')


class EditColumnFrame(wx.Frame) :
    """Set Column Labels for a file"""
    def __init__(self, parent, group=None, last_array_sel=None,
                 read_ok_cb=None, edit_groupname=True, with_smooth=False,
                 _larch=None):
        self.parent = parent
        self.larch = _larch
        self.rawgroup = group
        self.with_smooth = with_smooth
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

        if with_smooth:
            opts['action'] = self.onSmoothChoice
            self.smooth_op = Choice(panel, choices=SMOOTH_OPS, **opts)
            self.smooth_op.SetSelection(0)

            opts['size'] = (100, -1)

            opts['action'] = self.onUpdate
            smooth_panel = wx.Panel(panel)
            smooth_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.smooth_conv = Choice(smooth_panel, choices=CONV_OPS, **opts)
            opts['size'] =  (30, -1)
            self.smooth_c0 = FloatCtrl(smooth_panel, value=3, precision=0, **opts)
            self.smooth_c1 = FloatCtrl(smooth_panel, value=1, precision=0, **opts)
            opts['size'] =  (75, -1)
            self.smooth_sig = FloatCtrl(smooth_panel, value=1, precision=4, **opts)
            self.smooth_c0.Disable()
            self.smooth_c1.Disable()
            self.smooth_sig.Disable()
            self.smooth_conv.SetSelection(0)
            self.smooth_conv.Disable()


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

        if with_smooth:
            ir += 1
            sizer.Add(SimpleText(panel, 'Smoothing:'), (ir, 0), (1, 1), LCEN, 0)
            sizer.Add(self.smooth_op,  (ir, 1), (1, 1), CEN, 0)

            smooth_sizer.Add(SimpleText(smooth_panel, ' n='), 0, LCEN, 1)
            smooth_sizer.Add(self.smooth_c0,  0, LCEN, 1)
            smooth_sizer.Add(SimpleText(smooth_panel, ' order='), 0, LCEN, 1)
            smooth_sizer.Add(self.smooth_c1,  0, LCEN, 1)
            smooth_sizer.Add(SimpleText(smooth_panel, ' form='), 0, LCEN, 1)
            smooth_sizer.Add(self.smooth_conv,  0, LCEN, 1)
            smooth_sizer.Add(SimpleText(smooth_panel, ' sigma='), 0, LCEN, 1)
            smooth_sizer.Add(self.smooth_sig,  0, LCEN, 1)
            pack(smooth_panel, smooth_sizer)

            sizer.Add(smooth_panel,  (ir, 2), (1, 5), LCEN, 1)

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

    def onSmoothChoice(self, evt=None):
        choice = self.smooth_op.GetStringSelection().lower()
        conv  = self.smooth_conv.GetStringSelection()
        self.smooth_c0.Disable()
        self.smooth_c1.Disable()
        self.smooth_conv.Disable()
        self.smooth_sig.Disable()

        if choice.startswith('box'):
            self.smooth_c0.Enable()
        elif choice.startswith('savi'):
            self.smooth_c0.Enable()
            self.smooth_c1.Enable()
        elif choice.startswith('conv'):
            self.smooth_conv.Enable()
            self.smooth_sig.Enable()
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
        if xname == '<index>':
            xname = self.rawgroup.array_labels[0]
            outgroup._index = 1.0*np.arange(len(getattr(rawgroup, xname)))
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

        # apply smoothhing here
        if self.with_smooth:
            smoother = self.smooth_op.GetStringSelection().lower()
            if smoother.startswith('box'):
                n = int(self.smooth_c0.GetValue())
                outgroup.ydat = boxcar(outgroup.ydat, n)
            elif smoother.startswith('savit'):
                n = int(self.smooth_c0.GetValue())
                win_size = 2*n + 1
                order = int(self.smooth_c1.GetValue())
                outgroup.ydat = savitzky_golay(outgroup.ydat, win_size, order)
            elif smoother.startswith('conv'):
                sigma = float(self.smooth_sig.GetValue())
                form  = str(self.smooth_conv.GetStringSelection()).lower()
                outgroup.ydat = smooth(outgroup.xdat, outgroup.ydat,
                                       sigma=sigma, form=form)

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

        popts = {}
        path, fname = os.path.split(outgroup.filename)
        popts['label'] = "%s: %s" % (fname, outgroup.plot_ylabel)
        popts['title']  = fname
        popts['ylabel'] = outgroup.plot_ylabel
        popts['xlabel'] = outgroup.plot_xlabel

        self.plotpanel.plot(outgroup.xdat, outgroup.ydat, **popts)

        for i in range(self.nb.GetPageCount()):
            if 'plot' in self.nb.GetPageText(i).lower():
                self.nb.SetSelection(i)

    def plot_messages(self, msg, panel=1):
        self.SetStatusText(msg, panel)
