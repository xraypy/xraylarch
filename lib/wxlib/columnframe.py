#!/usr/bin/env python
"""

"""
import os
import numpy as np
np.seterr(all='ignore')

import wx
import wx.lib.scrolledpanel as scrolled

from wxmplot import PlotFrame
from wxutils import (SimpleText, FloatCtrl, pack, Button,
                     Choice,  Check, MenuItem, GUIColors,
                     CEN, RCEN, LCEN, FRAMESTYLE, Font)

from larch_plugins.io import fix_varname

CEN |=  wx.ALL


XPRE_OPS = ('', 'log(', '-log(')
YPRE_OPS = ('', 'log(', '-log(')
ARR_OPS = ('+', '-', '*', '/')

def okcancel(panel, onOK=None, onCancel=None):
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


class EditColumnFrame(wx.Frame) :
    """Set Column Labels for a file"""
    def __init__(self, parent, group=None, last_array_sel=None,
                 read_ok_cb=None, edit_groupname=True):
        self.parent = parent
        self.dgroup = group
        if not hasattr(self.dgroup, 'is_xas'):
            try:
                self.dgroup.is_xas = 'energ' in self.dgroup.array_labels[0].lower()
            except:
                self.dgroup.is_xas = False
        self.read_ok_cb = read_ok_cb

        self.array_sel = {'xpop': '', 'xarr': None,
                          'ypop': '', 'yop': '/',
                          'yarr1': None, 'yarr2': None,
                          'use_deriv': False}
        if last_array_sel is not None:
            self.array_sel.update(last_array_sel)

        if self.array_sel['yarr2'] is None and 'i0' in self.dgroup.array_labels:
            self.array_sel['yarr2'] = 'i0'

        if self.array_sel['yarr1'] is None:
            if 'itrans' in self.dgroup.array_labels:
                self.array_sel['yarr1'] = 'itrans'
            elif 'i1' in self.dgroup.array_labels:
                self.array_sel['yarr1'] = 'i1'
        message = "Build Arrys from Data Columns for %s" % self.dgroup.filename
        wx.Frame.__init__(self, None, -1, 'Build Arrays from Data Columns for %s' % self.dgroup.filename,
                          style=FRAMESTYLE)

        self.SetFont(Font(10))
        panel = scrolled.ScrolledPanel(self)
        self.SetMinSize((600, 600))
        self.colors = GUIColors()
        self.plotframe = None

        # title row
        title = SimpleText(panel, message, font=Font(13),
                           colour=self.colors.title, style=LCEN)

        opts = dict(action=self.onColumnChoice, size=(120, -1))

        arr_labels = self.dgroup.array_labels
        yarr_labels = arr_labels + ['1.0', '0.0', '']
        xarr_labels = arr_labels + ['<index>']

        self.xarr   = Choice(panel, choices=xarr_labels, **opts)
        self.yarr1  = Choice(panel, choices= arr_labels, **opts)
        self.yarr2  = Choice(panel, choices=yarr_labels, **opts)

        opts['size'] = (90, -1)

        self.xpop = Choice(panel, choices=XPRE_OPS, **opts)
        self.ypop = Choice(panel, choices=YPRE_OPS, **opts)
        opts['size'] = (50, -1)
        self.yop =  Choice(panel, choices=ARR_OPS, **opts)

        ylab = SimpleText(panel, 'Y = ')
        xlab = SimpleText(panel, 'X = ')
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

        opts['size'] = (150, -1)
        self.use_deriv = Check(panel, label='use derivative',
                               default=self.array_sel['use_deriv'], **opts)

        self.is_xas = Check(panel, label='use as XAS data',
                               default=self.dgroup.is_xas, **opts)

        bpanel = wx.Panel(panel)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.Add(Button(bpanel, 'Preview', action=self.onColumnChoice), 4)
        bsizer.Add(Button(bpanel, 'OK', action=self.onOK), 4)
        bsizer.Add(Button(bpanel, 'Cancel', action=self.onCancel), 4)
        pack(bpanel, bsizer)

        sizer = wx.GridBagSizer(4, 8)
        sizer.Add(title,     (0, 0), (1, 7), LCEN, 5)

        ir = 1
        sizer.Add(xlab,      (ir, 0), (1, 1), CEN, 0)
        sizer.Add(self.xpop, (ir, 1), (1, 1), CEN, 0)
        sizer.Add(self.xarr, (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.xsuf, (ir, 3), (1, 1), CEN, 0)

        ir += 1
        sizer.Add(ylab,       (ir, 0), (1, 1), CEN, 0)
        sizer.Add(self.ypop,  (ir, 1), (1, 1), CEN, 0)
        sizer.Add(self.yarr1, (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.yop,   (ir, 3), (1, 1), CEN, 0)
        sizer.Add(self.yarr2, (ir, 4), (1, 1), CEN, 0)
        sizer.Add(self.ysuf,  (ir, 5), (1, 1), CEN, 0)

        ir += 1
        sizer.Add(self.use_deriv, (ir, 0), (1, 3), LCEN, 0)
        ir += 1
        sizer.Add(self.is_xas, (ir, 0), (1, 3), LCEN, 0)

        self.wid_groupname = None
        if edit_groupname:
            wid_grouplab = SimpleText(panel, 'Use Group Name: ')
            self.wid_groupname = wx.TextCtrl(panel, value=self.dgroup._groupname,
                                             size=(100, -1))
            ir += 1
            sizer.Add(wid_grouplab,     (ir, 0), (1, 2), LCEN, 3)
            sizer.Add(self.wid_groupname, (ir, 2), (1, 3), LCEN, 3)

        ir += 1
        sizer.Add(bpanel,     (ir, 0), (1, 5), LCEN, 3)

        pack(panel, sizer)


        ftext = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY,
                               size=(-1, 150))
        try:
            m = open(self.dgroup.filename, 'r')
            text = m.read()
            m.close()
        except:
            text = "The file '%s'\n was not found" % self.dgroup.filename
        ftext.SetValue(text)
        ftext.SetFont(Font(9))

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 0, wx.GROW|wx.ALL, 2)
        mainsizer.Add(ftext, 1, LCEN|wx.GROW,   2)
        pack(self, mainsizer)

        self.Show()
        self.Raise()

    def onOK(self, event=None):
        """ build arrays according to selection """

        if not hasattr(self.dgroup, '_xdat'):
            self.onColumnChoice()

        if self.wid_groupname is not None:
            self.dgroup._groupname = fix_varname(self.wid_groupname.GetValue())
        if self.plotframe is not None:
            try:
                self.plotframe.Destroy()
            except:
                pass
        if self.read_ok_cb is not None:
            self.read_ok_cb(self.dgroup, self.array_sel)
        self.Destroy()

    def onCancel(self, event=None):
        self.dgroup.import_ok = False
        if self.plotframe is not None:
            self.plotframe.Destroy()
        self.Destroy()

    def onColumnChoice(self, evt=None):
        """column selections changed calc _xdat and _ydat"""
        # dtcorr = self.dtcorr.IsChecked()
        dtcorr = False
        use_deriv = self.use_deriv.IsChecked()
        dgroup = self.dgroup

        ix  = self.xarr.GetSelection()
        xname = self.xarr.GetStringSelection()
        if xname == '<index>':
            xname = self.dgroup.array_labels[0]
            dgroup._index = 1.0*np.arange(len(getattr(dgroup, xname)))
            xname = '_index'

        dgroup.is_xas = self.is_xas.IsChecked()
        dgroup._xdat = getattr(dgroup, xname)

        def do_preop(opwid, arr):
            opstr = opwid.GetStringSelection().strip()
            suf = ''
            if opstr in ('-log(', 'log('):
                suf = ')'
                if opstr == 'log(':
                    arr = np.log(arr)
                elif opstr == '-log(':
                    arr = -np.log(arr)
            return suf, opstr, arr

        xsuf, xpop, dgroup._xdat = do_preop(self.xpop, dgroup._xdat)
        self.xsuf.SetLabel(xsuf)

        try:
            xunits = dgroup.array_units[ix].strip()
            xlabel = '%s (%s)' % (xname, xunits)
        except:
            xlabel = xname


        def get_data(group, arrayname, correct=False):
            if hasattr(group, 'get_data'):
                return group.get_data(arrayname, correct=correct)
            return getattr(group, arrayname, None)

        yname1  = self.yarr1.GetStringSelection().strip()
        yname2  = self.yarr2.GetStringSelection().strip()
        yop = self.yop.GetStringSelection().strip()

        ylabel = yname1
        if len(yname2) == 0:
            yname2, yop = '1.0', '*'
        else:
            ylabel = "%s%s%s" % (ylabel, yop, yname2)

        yarr1 = get_data(dgroup, yname1, correct=dtcorr)

        if yname2 in ('0.0', '1.0'):
            yarr2 = float(yname2)
            if yop == '/': yarr2 = 1.0
        else:
            yarr2 = get_data(dgroup, yname2, correct=dtcorr)

        dgroup._ydat = yarr1
        if yop == '+':
            dgroup._ydat = yarr1.__add__(yarr2)
        elif yop == '-':
            dgroup._ydat = yarr1.__sub__(yarr2)
        elif yop == '*':
            dgroup._ydat = yarr1.__mul__(yarr2)
        elif yop == '/':
            dgroup._ydat = yarr1.__truediv__(yarr2)


        ysuf, ypop, dgroup._ydat = do_preop(self.ypop, dgroup._ydat)
        self.ysuf.SetLabel(ysuf)

        if use_deriv:
            try:
                dgroup._ydat = np.gradient(dgroup._ydat)/np.gradient(dgroup._xdat)
            except:
                pass

        self.array_sel = {'xpop': xpop, 'xarr': xname,
                     'ypop': ypop, 'yop': yop,
                     'yarr1': yname1, 'yarr2': yname2,
                     'use_deriv': use_deriv}


        try:
            npts = min(len(dgroup._xdat), len(dgroup._ydat))
        except AttributeError:
            print( 'Error calculating arrays (npts not correct)')
            return

        dgroup._npts       = npts
        dgroup.plot_xlabel = xlabel
        dgroup.plot_ylabel = ylabel
        dgroup._xdat       = np.array( dgroup._xdat[:npts])
        dgroup._ydat       = np.array( dgroup._ydat[:npts])
        if dgroup.is_xas:
            dgroup.energy = dgroup._xdat
            dgroup.mu     = dgroup._ydat

        self.raise_plotframe()

        ppanel = self.plotframe.panel

        popts = {}
        path, fname = os.path.split(dgroup.filename)

        popts['label'] = "%s: %s" % (fname, dgroup.plot_ylabel)
        popts['title']  = fname
        popts['ylabel'] = dgroup.plot_ylabel
        popts['xlabel'] = dgroup.plot_xlabel

        ppanel.plot(dgroup._xdat, dgroup._ydat, **popts)

    def raise_plotframe(self):
        if self.plotframe is not None:
            try:
                self.plotframe.Show()
            except:
                self.plotframe = None
        if self.plotframe is None:
            self.plotframe = PlotFrame(None, size=(650, 400))
            self.plotframe.Show()
