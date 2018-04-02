import os
from collections import namedtuple, OrderedDict
from functools import partial

import numpy as np

import wx
from wxutils import (SimpleText, Choice, Check, Button, HLine,
                     OkCancel, GridPanel, LCEN)


from larch.utils import index_of, index_nearest, interp
from larch.wxlib import BitmapButton, FloatCtrl
from larch_plugins.wx.icons import get_icon
from larch_plugins.xafs.xafsutils  import etok, ktoe
from larch_plugins.xafs.xafsplots import plotlabels

PI = np.pi
DEG2RAD  = PI/180.0

# Planck constant over 2 pi times c: 197.3269718 (0.0000044) MeV fm
PLANCK_HC = 1973.269718 * 2 * PI # hc in eV * Ang = 12398.4193

Plot_Choices = OrderedDict((('Normalized', 'norm'),
                            ('Derivative', 'dmude')))


class EnergyCalibrateDialog(wx.Dialog):
    """dialog for calibrating energy"""
    def __init__(self, parent, controller, **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        groupnames = list(self.controller.file_groups.keys())

        self.data = [self.dgroup.energy[:], self.dgroup.norm[:]]
        xmin = min(self.dgroup.energy)
        xmax = max(self.dgroup.energy)
        e0val = getattr(self.dgroup, 'e0', xmin)

        title = "Calibrate / Align Energy"

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 250), title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.grouplist = Choice(panel, choices=groupnames, size=(250, -1),
                                action=self.on_groupchoice)

        self.grouplist.SetStringSelection(self.dgroup.groupname)

        refgroups = ['None'] + groupnames

        self.reflist = Choice(panel, choices=refgroups, size=(250, -1),
                              action=self.on_align)
        self.reflist.SetSelection(0)


        self.wids = wids = {}

        opts  = dict(size=(90, -1), precision=3, act_on_losefocus=True,
                     minval=xmin, maxval=xmax)

        wids['e0_old'] = FloatCtrl(panel, value=e0val, **opts)
        wids['e0_new'] = FloatCtrl(panel, value=e0val, **opts)

        opts['minval'] = -500
        opts['maxval'] = 500
        wids['eshift'] = FloatCtrl(panel, value=0.0, **opts)


        bb_e0old = BitmapButton(panel, get_icon('plus'),
                                action=partial(self.on_select, opt='e0_old'),
                                tooltip='use last point selected from plot')
        bb_e0new = BitmapButton(panel, get_icon('plus'),
                                action=partial(self.on_select, opt='e0_new'),
                                tooltip='use last point selected from plot')

        self.plottype = Choice(panel, choices=list(Plot_Choices.keys()),
                                   size=(250, -1), action=self.on_calib)

        for wname, wid in wids.items():
            wid.SetAction(partial(self.on_calib, name=wname))


        apply_one = Button(panel, 'Save Arrays for this Group', size=(175, -1),
                           action=self.on_apply_one)
        apply_one.SetToolTip('Save rebinned data, overwrite current arrays')

        apply_sel = Button(panel, 'Apply to Selected Groups', size=(175, -1),
                           action=self.on_apply_sel)
        apply_sel.SetToolTip('''Apply the Energy Shift to the Selected Groups
  in XAS GUI, overwriting current arrays''')


        done = Button(panel, 'Done', size=(125, -1), action=self.on_done)

        panel.Add(SimpleText(panel, ' Energy Calibration for Group: '), dcol=2)
        panel.Add(self.grouplist, dcol=5)

        panel.Add(SimpleText(panel, ' Plot Arrays as: '), dcol=2, newrow=True)
        panel.Add(self.plottype, dcol=5)

        panel.Add(SimpleText(panel, ' Energy Reference (E0): '), newrow=True)
        panel.Add(bb_e0old)
        panel.Add(wids['e0_old'])
        panel.Add(SimpleText(panel, ' eV'))

        panel.Add(SimpleText(panel, ' Calibrate to: '), newrow=True)
        panel.Add(bb_e0new)
        panel.Add(wids['e0_new'])
        panel.Add(SimpleText(panel, ' eV'))
        panel.Add(SimpleText(panel, ' Energy Shift : '), dcol=2, newrow=True)
        panel.Add(wids['eshift'])
        panel.Add(SimpleText(panel, ' eV '))
        panel.Add(apply_sel, dcol=2)

        panel.Add(SimpleText(panel, ' Auto-Align to : '), dcol=2, newrow=True)
        panel.Add(self.reflist, dcol=5)

        panel.Add(apply_one, dcol=4, newrow=True)

        panel.Add(HLine(panel, size=(550, 3)), dcol=7, newrow=True)
        panel.Add(done, dcol=4, newrow=True)
        panel.pack()
        self.plot_results()

    def on_select(self, event=None, opt=None):
        _x, _y = self.controller.get_cursor()
        if opt in self.wids:
            self.wids[opt].SetValue(_x)

    def on_groupchoice(self, event=None):
        self.dgroup = self.controller.get_group(self.grouplist.GetStringSelection())
        self.plot_results()

    def on_align(self, event=None, name=None, value=None):

        self.plot_results()

    def on_calib(self, event=None, name=None, value=None):
        wids = self.wids

        e0_old = wids['e0_old'].GetValue()
        e0_new = wids['e0_new'].GetValue()

        xnew = self.dgroup.energy - e0_old + e0_new
        self.data = xnew, self.dgroup.norm[:]
        self.plot_results()

    def on_apply_one(self, event=None):
        xdat, ydat = self.data
        dgroup = self.dgroup
        dgroup.energy = xdat
        dgroup.norm   = ydat
        self.parent.np_panels[0].process(dgroup)
        self.plot_results()

    def on_apply_sel(self, event=None):
        xdat, ydat = self.data
        print(" Apply to Selected!")

    def on_done(self, event=None):
        self.Destroy()

    def plot_results(self):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        xnew, ynew = self.data
        dgroup = self.dgroup
        path, fname = os.path.split(dgroup.filename)

        e0_old = self.wids['e0_old'].GetValue()
        e0_new = self.wids['e0_new'].GetValue()

        xmin = min(e0_old, e0_new) - 25
        xmax = max(e0_old, e0_new) + 50

        ppanel.plot(xnew, ynew, zorder=20, delay_draw=True, marker=None,
                    linewidth=3, title='calibrate: %s' % fname,
                    label='shifted', xlabel=plotlabels.energy,
                    ylabel=plotlabels.norm, xmin=xmin, xmax=xmax)

        xold, yold = self.dgroup.energy, self.dgroup.norm
        ppanel.oplot(xold, yold, zorder=10, delay_draw=False,
                     marker='o', markersize=2, linewidth=2.0,
                     label='original', show_legend=True,
                     xmin=xmin, xmax=xmax)

        ppanel.axes.axvline(e0_old, ymin=0.1, ymax=0.9, color='#B07070')
        ppanel.axes.axvline(e0_new, ymin=0.1, ymax=0.9, color='#7070B0')
        ppanel.canvas.draw()

    def GetResponse(self):
        raise AttributError("use as non-modal dialog!")


class RebinDataDialog(wx.Dialog):
    """dialog for rebinning data to standard XAFS grid"""
    def __init__(self, parent, controller, **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        groupnames = list(self.controller.file_groups.keys())

        self.data = [self.dgroup.energy[:], self.dgroup.mu[:]]
        xmin = min(self.dgroup.energy)
        xmax = max(self.dgroup.energy)
        e0val = getattr(self.dgroup, 'e0', xmin)

        title = "Rebin mu(E) Data"

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(450, 250), title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.grouplist = Choice(panel, choices=groupnames, size=(250, -1),
                                action=self.on_groupchoice)

        self.grouplist.SetStringSelection(self.dgroup.groupname)

        opts  = dict(size=(90, -1), precision=3, act_on_losefocus=True)

        self.wids = wids = {}
        wids['e0'] = FloatCtrl(panel, value=e0val, minval=xmin, maxval=xmax,
                             **opts)

        wids['pre1'] = FloatCtrl(panel, value=xmin-e0val,  **opts)
        wids['pre2'] = FloatCtrl(panel, value=-20, **opts)

        wids['xanes1'] = FloatCtrl(panel, value=-20,  **opts)
        wids['xanes2'] = FloatCtrl(panel, value=30, **opts)

        wids['exafs1'] = FloatCtrl(panel, value=etok(30),  **opts)
        wids['exafs2'] = FloatCtrl(panel, value=etok(xmax-e0val), **opts)

        wids['pre_step'] = FloatCtrl(panel, value=5.0,  **opts)
        wids['xanes_step'] = FloatCtrl(panel, value=0.25,  **opts)
        wids['exafs_step'] = FloatCtrl(panel, value=0.05,  **opts)


        for wname, wid in wids.items():
            wid.SetAction(partial(self.on_rebin, name=wname))

        apply = Button(panel, 'Save Arrays for this Group', size=(200, -1),
                      action=self.on_apply)
        apply.SetToolTip('Save rebinned data, overwrite current arrays')

        done = Button(panel, 'Done', size=(125, -1), action=self.on_done)

        panel.Add(SimpleText(panel, 'Rebin Data for Group: '), dcol=2)
        panel.Add(self.grouplist, dcol=3)

        panel.Add(SimpleText(panel, 'E0: '), newrow=True)
        panel.Add(wids['e0'])
        panel.Add(SimpleText(panel, ' eV'))

        panel.Add(SimpleText(panel, 'Region '), newrow=True)
        panel.Add(SimpleText(panel, 'Start '))
        panel.Add(SimpleText(panel, 'Stop '))
        panel.Add(SimpleText(panel, 'Step '))
        panel.Add(SimpleText(panel, 'Units '))

        panel.Add(SimpleText(panel, 'Pre-Edge: '), newrow=True)
        panel.Add(wids['pre1'])
        panel.Add(wids['pre2'])
        panel.Add(wids['pre_step'])
        panel.Add(SimpleText(panel, ' eV'))

        panel.Add(SimpleText(panel, 'XANES: '), newrow=True)
        panel.Add(wids['xanes1'])
        panel.Add(wids['xanes2'])
        panel.Add(wids['xanes_step'])
        panel.Add(SimpleText(panel, ' eV'))

        panel.Add(SimpleText(panel, 'EXAFS: '), newrow=True)
        panel.Add(wids['exafs1'])
        panel.Add(wids['exafs2'])
        panel.Add(wids['exafs_step'])
        panel.Add(SimpleText(panel, u'1/\u212B'))

        panel.Add(apply, dcol=4, newrow=True)

        panel.Add(HLine(panel, size=(450, 3)), dcol=6, newrow=True)
        panel.Add(done, dcol=4, newrow=True)
        panel.pack()
        self.plot_results()

    def on_groupchoice(self, event=None):
        self.dgroup = self.controller.get_group(self.grouplist.GetStringSelection())
        self.plot_results()

    def on_rebin(self, event=None, name=None, value=None):
        wids = self.wids
        if name == 'pre2':
            val = wids['pre2'].GetValue()
            wids['xanes1'].SetValue(val, act=False)
        elif name == 'xanes1':
            val = wids['xanes1'].GetValue()
            wids['pre2'].SetValue(val, act=False)
        elif name == 'xanes2':
            val = wids['xanes2'].GetValue()
            wids['exafs1'].SetValue(etok(val), act=False)
        elif name == 'exafs1':
            val = wids['exafs1'].GetValue()
            wids['xanes2'].SetValue(ktoe(val), act=False)

        e0 = wids['e0'].GetValue()

        xarr = []
        for prefix in ('pre', 'xanes', 'exafs'):
            start= wids['%s1' % prefix].GetValue()
            stop = wids['%s2' % prefix].GetValue()
            step = wids['%s_step' % prefix].GetValue()

            npts = 1 + int(0.1  + abs(stop-start)/step)
            a = np.linspace(start, stop, npts)
            if prefix == 'exafs':
                a = ktoe(a)
            xarr.append(a+e0)

        xnew = np.concatenate((xarr[0], xarr[1], xarr[2]))
        ynew = interp(self.dgroup.energy, self.dgroup.mu, xnew, kind='cubic')
        self.data = xnew, ynew
        self.plot_results()

    def on_apply(self, event=None):
        xdat, ydat = self.data
        dgroup = self.dgroup
        dgroup.energy = xdat
        dgroup.mu     = ydat
        self.parent.np_panels[0].process(dgroup)
        self.plot_results()

    def on_done(self, event=None):
        self.Destroy()

    def plot_results(self):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        xnew, ynew = self.data
        dgroup = self.dgroup
        path, fname = os.path.split(dgroup.filename)

        ppanel.plot(xnew, ynew, zorder=20, delay_draw=True, marker='square',
                    linewidth=3, title='rebinning: %s' % fname,
                    label='rebinned', xlabel=plotlabels.energy,
                    ylabel=plotlabels.mu)

        xold, yold = self.dgroup.energy, self.dgroup.mu
        ppanel.oplot(xold, yold, zorder=10, delay_draw=False,
                     marker='o', markersize=4, linewidth=2.0,
                     label='original', show_legend=True)
        ppanel.canvas.draw()

    def GetResponse(self):
        raise AttributError("use as non-modal dialog!")


class SmoothDataDialog(wx.Dialog):
    """dialog for smoothing data"""
    def __init__(self, parent, controller, **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        groupnames = list(self.controller.file_groups.keys())

        self.data = [self.dgroup.energy[:], self.dgroup.mu[:]]

        title = "Smooth mu(E) Data"

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(600, 200), title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.grouplist = Choice(panel, choices=groupnames, size=(250, -1),
                                action=self.on_groupchoice)

        self.grouplist.SetStringSelection(self.dgroup.groupname)
        self.grouplist.SetToolTip('select a new group, clear undo history')

        smooth_ops = ('None', 'Boxcar', 'Savitzky-Golay', 'Convolution')
        conv_ops  = ('Lorenztian', 'Gaussian')

        self.smooth_op = Choice(panel, choices=smooth_ops, size=(150, -1),
                                action=self.on_smooth)
        self.smooth_op.SetSelection(0)

        self.conv_op = Choice(panel, choices=conv_ops, size=(150, -1),
                                action=self.on_smooth)
        self.conv_op.SetSelection(0)

        opts  = dict(size=(50, -1), act_on_losefocus=True, odd_only=False)

        self.sigma = FloatCtrl(panel, value=1, precision=2, minval=0, **opts)
        self.par_n = FloatCtrl(panel, value=2, precision=0, minval=1, **opts)
        self.par_o = FloatCtrl(panel, value=1, precision=0, minval=1, **opts)

        for fc in (self.sigma, self.par_n, self.par_o):
            fc.SetAction(self.on_smooth)

        self.message = SimpleText(panel, label='         ', size=(200, -1))

        apply = Button(panel, 'Save Array for this Group', size=(200, -1),
                      action=self.on_apply)
        apply.SetToolTip('Save smoothed data, overwrite current arrays')

        done = Button(panel, 'Done', size=(125, -1), action=self.on_done)

        panel.Add(SimpleText(panel, 'Smooth Data for Group: '))
        panel.Add(self.grouplist, dcol=5)

        panel.Add(SimpleText(panel, 'Smoothing Method: '), newrow=True)
        panel.Add(self.smooth_op)
        panel.Add(SimpleText(panel, ' n= '))
        panel.Add(self.par_n)
        panel.Add(SimpleText(panel, ' order= '))
        panel.Add(self.par_o)

        panel.Add(SimpleText(panel, 'Convolution Form: '), newrow=True)
        panel.Add(self.conv_op)
        panel.Add(SimpleText(panel, 'sigma='))
        panel.Add(self.sigma)

        panel.Add((10, 10), newrow=True)
        panel.Add(self.message, dcol=5)

        panel.Add(apply, dcol=4, newrow=True)

        panel.Add(HLine(panel, size=(600, 3)), dcol=6, newrow=True)
        panel.Add(done, dcol=4, newrow=True)
        panel.pack()
        self.plot_results()

    def on_groupchoice(self, event=None):
        self.dgroup = self.controller.get_group(self.grouplist.GetStringSelection())
        self.plot_results()

    def on_smooth(self, event=None, value=None):
        smoothop = self.smooth_op.GetStringSelection().lower()

        convop   = self.conv_op.GetStringSelection()
        self.message.SetLabel('')
        self.par_n.SetMin(1)
        self.par_n.odd_only = False
        par_n = int(self.par_n.GetValue())
        par_o = int(self.par_o.GetValue())
        sigma = self.sigma.GetValue()
        cmd = '{group:s}.mu' # No smoothing
        if smoothop.startswith('box'):
            self.par_n.Enable()
            cmd = "boxcar({group:s}.mu, {par_n:d})"
        elif smoothop.startswith('savi'):
            self.par_n.Enable()
            self.par_n.odd_only = True
            self.par_o.Enable()

            x0 = max(par_o + 1, par_n)
            if x0 % 2 == 0:
                x0 += 1
            self.par_n.SetMin(par_o + 1)
            if par_n != x0:
                self.par_n.SetValue(x0)
            self.message.SetLabel('n must odd and > order+1')

            cmd = "savitzky_golay({group:s}.mu, {par_n:d}, {par_o:d})"

        elif smoothop.startswith('conv'):
            cmd = "smooth({group:s}.energy, {group:s}.mu, sigma={sigma:f}, form='{convop:s}')"

        cmd = cmd.format(group=self.dgroup.groupname, convop=convop,
                         sigma=sigma, par_n=par_n, par_o=par_o)

        self.controller.larch.eval("_tmpy = %s" % cmd)
        self.data = self.dgroup.energy[:], self.controller.symtable._tmpy
        self.plot_results()

    def on_apply(self, event=None):
        xdat, ydat = self.data
        dgroup = self.dgroup
        dgroup.energy = xdat
        dgroup.mu     = ydat
        self.parent.np_panels[0].process(dgroup)
        self.plot_results()

    def on_done(self, event=None):
        self.Destroy()

    def plot_results(self):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        xnew, ynew = self.data
        dgroup = self.dgroup
        path, fname = os.path.split(dgroup.filename)

        ppanel.plot(xnew, ynew, zorder=20, delay_draw=True, marker=None,
                    linewidth=3, title='smoothing: %s' % fname,
                    label='smoothed', xlabel=plotlabels.energy,
                    ylabel=plotlabels.mu)

        xold, yold = self.dgroup.energy, self.dgroup.mu
        ppanel.oplot(xold, yold, zorder=10, delay_draw=False,
                     marker='o', markersize=4, linewidth=2.0,
                     label='original', show_legend=True)
        ppanel.canvas.draw()

    def GetResponse(self):
        raise AttributError("use as non-modal dialog!")


class DeglitchDialog(wx.Dialog):
    """dialog for deglitching or removing unsightly data points"""
    def __init__(self, parent, controller, **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        groupnames = list(self.controller.file_groups.keys())

        self.reset_data_history()
        xdat, ydat = self.data[-1]

        xrange = (max(xdat) - min(xdat))
        xmax = int(max(xdat) + xrange/5.0)
        xmin = int(min(xdat) - xrange/5.0)

        lastx, lasty = self.controller.get_cursor()
        if lastx is None:
            lastx = max(xdat)

        title = "Select Points to Remove"

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(520, 225), title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)


        self.grouplist = Choice(panel, choices=groupnames, size=(250, -1),
                                action=self.on_groupchoice)

        self.grouplist.SetStringSelection(self.dgroup.groupname)
        self.grouplist.SetToolTip('select a new group, clear undo history')

        bb_xlast = BitmapButton(panel, get_icon('plus'),
                                action=partial(self.on_select, opt='x'),
                                tooltip='use last point selected from plot')

        bb_range1 = BitmapButton(panel, get_icon('plus'),
                                action=partial(self.on_select, opt='range1'),
                                tooltip='use last point selected from plot')
        bb_range2 = BitmapButton(panel, get_icon('plus'),
                                action=partial(self.on_select, opt='range2'),
                                tooltip='use last point selected from plot')

        br_xlast = Button(panel, 'Remove point', size=(125, -1),
                          action=partial(self.on_remove, opt='x'))

        br_range = Button(panel, 'Remove range', size=(125, -1),
                          action=partial(self.on_remove, opt='range'))

        undo = Button(panel, 'Undo remove', size=(125, -1),
                      action=self.on_undo)
        apply = Button(panel, 'Save Array for this Group', size=(200, -1),
                      action=self.on_apply)
        apply.SetToolTip('Save current arrays, clear undo history')

        done = Button(panel, 'Done', size=(125, -1),
                      action=self.on_done)

        self.history_message = SimpleText(panel, '')

        floatopts = dict(precision=2, minval=xmin, maxval=xmax, size=(125, -1))

        self.wid_xlast = FloatCtrl(panel, value=lastx, **floatopts)
        self.wid_range1 = FloatCtrl(panel, value=lastx, **floatopts)
        self.wid_range2 = FloatCtrl(panel, value=lastx+1, **floatopts)

        self.choice_range = Choice(panel, choices=('above', 'below', 'between'),
                                    size=(100, -1), action=self.on_rangechoice)

        panel.Add(SimpleText(panel, 'Deglitch Data for Group: '), dcol=3)
        panel.Add(self.grouplist, dcol=2)

        panel.Add(SimpleText(panel, 'Single Energy : '), dcol=2, newrow=True)
        panel.Add(bb_xlast)
        panel.Add(self.wid_xlast)
        panel.Add(br_xlast)

        panel.Add(SimpleText(panel, 'Energy Range : '), newrow=True)
        panel.Add(self.choice_range)
        panel.Add(bb_range1)
        panel.Add(self.wid_range1)
        panel.Add(br_range)

        panel.Add((10, 10), dcol=2, newrow=True)
        panel.Add(bb_range2)
        panel.Add(self.wid_range2)

        panel.Add(apply, dcol=3, newrow=True)
        panel.Add(self.history_message)
        panel.Add(undo)

        panel.Add(HLine(panel, size=(500, 3)), dcol=5, newrow=True)
        panel.Add(done, dcol=4, newrow=True)

        panel.pack()
        self.plot_results()

    def reset_data_history(self):
        xdat = self.dgroup.xdat[:]
        if hasattr(self.dgroup, 'energy'):
            xdat = self.dgroup.energy[:]

        ydat = self.dgroup.ydat[:]
        if hasattr(self.dgroup, 'mu'):
            ydat = self.dgroup.mu[:]
        self.data = [(xdat, ydat)]

    def on_groupchoice(self, event=None):
        self.dgroup = self.controller.get_group(self.grouplist.GetStringSelection())
        self.reset_data_history()
        self.plot_results()

    def on_rangechoice(self, event=None):
        if self.choice_range.GetStringSelection() == 'between':
            self.wid_range2.Enable()

    def on_select(self, event=None, opt=None):
        _x, _y = self.controller.get_cursor()
        if opt == 'x':
            self.wid_xlast.SetValue(_x)
        elif opt == 'range1':
            self.wid_range1.SetValue(_x)
        elif opt == 'range2':
            self.wid_range2.SetValue(_x)

    def on_remove(self, event=None, opt=None):
        xwork, ywork = self.data[-1]
        if opt == 'x':
            bad = index_nearest(xwork, self.wid_xlast.GetValue())
        elif opt == 'range':
            rchoice = self.choice_range.GetStringSelection().lower()
            x1 = index_nearest(xwork, self.wid_range1.GetValue())
            x2 = None
            if rchoice == 'below':
                x2, x1 = x1, x2
            elif rchoice == 'between':
                x2 = index_nearest(xwork, self.wid_range2.GetValue())
                if x1 > x2:
                    x1, x2 = x2, x1
            bad = slice(x1, x2, None)

        self.data.append((np.delete(xwork, bad), np.delete(ywork, bad)))
        self.plot_results()

    def on_undo(self, event=None):
        if len(self.data) > 1:
            self.data.pop()
            self.plot_results()

    def on_apply(self, event=None):
        xdat, ydat = self.data[-1]
        dgroup = self.dgroup
        dgroup.energy = xdat
        dgroup.mu     = ydat
        self.reset_data_history()
        self.parent.np_panels[0].process(dgroup)
        self.plot_results()

    def on_done(self, event=None):
        self.Destroy()

    def plot_results(self):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        xnew, ynew = self.data[-1]
        dgroup = self.dgroup
        path, fname = os.path.split(dgroup.filename)

        ppanel.plot(xnew, ynew, zorder=20, delay_draw=True, marker=None,
                    linewidth=3, title='deglitching: %s' % fname,
                    label='current', xlabel=plotlabels.energy,
                    ylabel=plotlabels.mu)

        if len(self.data) > 1:
            xold, yold = self.data[0]
            ppanel.oplot(xold, yold, zorder=10, delay_draw=False,
                         marker='o', markersize=4, linewidth=2.0,
                         label='original', show_legend=True)
        ppanel.canvas.draw()
        self.history_message.SetLabel('%i items in history' % (len(self.data)-1))

    def GetResponse(self):
        raise AttributError("use as non-modal dialog!")

class EnergyUnitsDialog(wx.Dialog):
    """dialog for selecting, changing energy units, forcing data to eV"""
    unit_choices = ['eV', 'keV', 'deg', 'steps']

    def __init__(self, parent, unitname, energy_array, **kws):

        self.energy = energy_array[:]

        title = "Select Energy Units to convert to 'eV'"
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.en_units = Choice(panel, choices=self.unit_choices, size=(125, -1),
                               action=self.onUnits)
        self.en_units.SetStringSelection(unitname)
        self.mono_dspace = FloatCtrl(panel, value=1.0, minval=0, maxval=100.0,
                                     precision=6, size=(125, -1))
        self.steps2deg  = FloatCtrl(panel, value=1.0, minval=0,
                                     precision=1, size=(125, -1))

        self.mono_dspace.Disable()
        self.steps2deg.Disable()

        panel.Add(SimpleText(panel, 'Energy Units : '), newrow=True)
        panel.Add(self.en_units)

        panel.Add(SimpleText(panel, 'Mono D spacing : '), newrow=True)
        panel.Add(self.mono_dspace)

        panel.Add(SimpleText(panel, 'Mono Steps per Degree : '), newrow=True)
        panel.Add(self.steps2deg)
        panel.Add((5, 5))

        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()

    def onUnits(self, event=None):
        units = self.en_units.GetStringSelection()

        self.steps2deg.Disable()
        self.mono_dspace.Disable()

        if units in ('deg', 'steps'):
            self.mono_dspace.Enable()
            if units == 'steps':
                self.steps2deg.Enable()

    def GetResponse(self, master=None, gname=None, ynorm=True):
        self.Raise()
        response = namedtuple('EnergyUnitsResponse', ('ok', 'units', 'energy'))
        ok, units, en = False, 'eV', None

        if self.ShowModal() == wx.ID_OK:
            units = self.en_units.GetStringSelection()
            if units == 'eV':
                en = self.energy
            elif units == 'keV':
                en = self.energy * 1000.0
            elif units in ('steps', 'deg'):
                dspace = float(self.mono_dspace.GetValue())
                if units == 'steps':
                    self.energy /= self.steps2deg.GetValue()
                en = (PLANCK_HC/(2*dspace))/np.sin(self.energy * DEG2RAD)
            ok = True
        return response(ok, units, en)

class MergeDialog(wx.Dialog):
    """dialog for merging groups"""
    ychoices = ['raw mu(E)', 'normalized mu(E)']

    def __init__(self, parent, groupnames, outgroup='merge', **kws):
        title = "Merge %i Selected Groups" % (len(groupnames))
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.master_group = Choice(panel, choices=groupnames, size=(250, -1))
        self.yarray_name  = Choice(panel, choices=self.ychoices, size=(250, -1))
        self.group_name   = wx.TextCtrl(panel, -1, outgroup,  size=(250, -1))

        panel.Add(SimpleText(panel, 'Match Energy to : '), newrow=True)
        panel.Add(self.master_group)

        panel.Add(SimpleText(panel, 'Array to merge  : '), newrow=True)
        panel.Add(self.yarray_name)

        panel.Add(SimpleText(panel, 'New group name  : '), newrow=True)
        panel.Add(self.group_name)

        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()

    def GetResponse(self, master=None, gname=None, ynorm=True):
        self.Raise()
        response = namedtuple('MergeResponse', ('ok', 'master', 'ynorm', 'group'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            master= self.master_group.GetStringSelection()
            ynorm = 'norm' in self.yarray_name.GetStringSelection().lower()
            gname = self.group_name.GetValue()
            ok = True
        return response(ok, master, ynorm, gname)

class QuitDialog(wx.Dialog):
    """dialog for quitting, prompting to save project"""

    def __init__(self, parent, **kws):
        title = "Quit Larch XAS Viewer?"
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title, size=(425, 150))
        self.needs_save = True
        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.save = Check(panel, default=False,
                          label='Save Project before Quitting?')

        panel.Add((5, 5), newrow=True)
        panel.Add(self.save)
        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(500, 3)), dcol=2, newrow=True)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()

    def GetResponse(self):
        self.Raise()
        response = namedtuple('QuitResponse', ('ok', 'save'))
        ok = (self.ShowModal() == wx.ID_OK)
        return response(ok, self.save.IsChecked())

class RenameDialog(wx.Dialog):
    """dialog for renaming group"""
    def __init__(self, parent, oldname,  **kws):
        title = "Rename Group %s" % (oldname)
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.newname   = wx.TextCtrl(panel, -1, oldname,  size=(250, -1))

        panel.Add(SimpleText(panel, 'Old Name : '), newrow=True)
        panel.Add(SimpleText(panel, oldname))
        panel.Add(SimpleText(panel, 'New Name : '), newrow=True)
        panel.Add(self.newname)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()

    def GetResponse(self, newname=None):
        self.Raise()
        response = namedtuple('RenameResponse', ('ok', 'newname'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            newname = self.newname.GetValue()
            ok = True
        return response(ok, newname)

class RemoveDialog(wx.Dialog):
    """dialog for removing groups"""
    def __init__(self, parent, grouplist,  **kws):
        title = "Remove %i Selected Group" % len(grouplist)
        self.grouplist = grouplist
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        panel.Add(SimpleText(panel, 'Remove %i Selected Grous?' % (len(grouplist))),
                  newrow=True, dcol=2)

        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()

    def GetResponse(self, ngroups=None):
        self.Raise()
        response = namedtuple('RemoveResponse', ('ok','ngroups'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            ngroups = len(self.grouplist)
            ok = True
        return response(ok, ngroups)
