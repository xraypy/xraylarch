import os
from collections import namedtuple, OrderedDict
from functools import partial
import numpy as np
from lmfit import Parameters, minimize

import wx

from larch.math import index_of, index_nearest, interp
from larch.xray import guess_edge
from larch.utils.strutils import file2groupname

from larch.wxlib import (GridPanel, BitmapButton, FloatCtrl, FloatSpin,
                         FloatSpinWithPin, get_icon, SimpleText, Choice,
                         SetTip, Check, Button, HLine, OkCancel, LCEN,
                         RCEN, plotlabels)

from larch.xafs.xafsutils  import etok, ktoe

PI = np.pi
DEG2RAD  = PI/180.0

# Planck constant over 2 pi times c: 197.3269718 (0.0000044) MeV fm
PLANCK_HC = 1973.269718 * 2 * PI # hc in eV * Ang = 12398.4193

Plot_Choices = OrderedDict((('Normalized', 'norm'),
                            ('Derivative', 'dmude')))

ELEM_LIST = ('H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na',
             'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti',
             'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge',
             'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo',
             'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te',
             'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm',
             'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf',
             'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb',
             'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U',
             'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf')

EDGE_LIST = ('K', 'L3', 'L2', 'L1', 'M5', 'M4', 'M3')


class OverAbsorptionDialog(wx.Dialog):
    """dialog for correcting over-absorption"""
    def __init__(self, parent, controller, **kws):
        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        groupnames = list(self.controller.file_groups.keys())

        self.data = [self.dgroup.energy[:], self.dgroup.norm[:]]

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 400),
                           title="Correct Over-absorption")

        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LCEN)
        self.wids = wids = {}

        wids['grouplist'] = Choice(panel, choices=groupnames, size=(250, -1),
                                   action=self.on_groupchoice)

        wids['grouplist'].SetStringSelection(self.dgroup.filename)

        opts  = dict(size=(90, -1), precision=1, act_on_losefocus=True,
                     minval=-90, maxval=180)

        fs_opts = dict(size=(90, -1), value=45, digits=1, increment=1)
        wids['phi_in']  = FloatSpin(panel, **fs_opts)
        wids['phi_out'] = FloatSpin(panel, **fs_opts)

        wids['elem'] = Choice(panel, choices=ELEM_LIST, size=(50, -1))
        wids['edge'] = Choice(panel, choices=EDGE_LIST, size=(50, -1))

        wids['formula'] = wx.TextCtrl(panel, -1, '', size=(250, -1))

        self.set_default_elem_edge(self.dgroup)

        wids['apply'] = Button(panel, 'Save / Overwrite', size=(150, -1),
                               action=self.on_apply)
        SetTip(wids['apply'], 'Save corrected data, overwrite current arrays')

        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                           action=self.on_saveas)
        SetTip(wids['save_as'], 'Save corrected data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1, self.dgroup.filename + '_abscorr',
                                           size=(250, -1))
        wids['correct'] = Button(panel, 'Do Correction',
                                 size=(150, -1), action=self.on_correct)
        SetTip(wids['correct'], 'Calculate Correction')

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text(' Correction for Group: ', newrow=False)
        panel.Add(wids['grouplist'], dcol=5)

        add_text(' Absorbing Element: ')
        panel.Add(wids['elem'])

        add_text('  Edge:  ', newrow=False)
        panel.Add(wids['edge'])

        add_text(' Material Formula: ')
        panel.Add(wids['formula'], dcol=3)

        add_text(' Incident Angle (deg): ')
        panel.Add(wids['phi_in'])

        add_text(' Exit Angle (deg): ')
        panel.Add(wids['phi_out'])

        panel.Add(wids['correct'], newrow=True)
        panel.Add(wids['apply'], dcol=2, newrow=True)

        panel.Add(wids['save_as'], newrow=True)
        panel.Add(wids['save_as_name'], dcol=3)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()

    def onDone(self, event=None):
        self.Destroy()

    def set_default_elem_edge(self, dgroup):
        elem, edge = guess_edge(dgroup.e0, _larch=self.controller.larch)
        self.wids['elem'].SetStringSelection(elem)
        self.wids['edge'].SetStringSelection(edge)

    def on_groupchoice(self, event=None):
        fname = self.wids['grouplist'].GetStringSelection()
        self.dgroup = self.controller.get_group(fname)
        self.set_default_elem_edge(self.dgroup)
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_abscorr')

    def on_saveas(self, event=None):
        wids = self.wids
        fname = self.wids['grouplist'].GetStringSelection()
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)
        if hasattr(self.dgroup, 'norm_corr' ):
            ngroup.mu = ngroup.norm_corr*1.0
            del ngroup.norm_corr
        self.parent.onNewGroup(ngroup)

    def on_correct(self, event=None):
        wids = self.wids
        dgroup = self.dgroup
        anginp = wids['phi_in'].GetValue()
        angout = wids['phi_out'].GetValue()
        elem   = wids['elem'].GetStringSelection()
        edge   = wids['edge'].GetStringSelection()
        formula = wids['formula'].GetValue()
        if len(formula) < 1:
            return

        cmd = """fluo_corr(%s.energy, %s.mu, '%s', '%s', edge='%s', group=%s,
     anginp=%.1f, angout=%.1f)""" % (dgroup.groupname, dgroup.groupname,
                                     formula, elem, edge, dgroup.groupname,
                                     anginp, angout)

        self.controller.larch.eval(cmd)
        self.plot_results()

    def on_apply(self, event=None):
        xdat, ydat = self.data
        dgroup = self.dgroup
        dgroup.xdat = dgroup.energy = xdat
        self.parent.nb.pagelist[0].process(dgroup)
        self.plot_results()

    def plot_results(self, event=None):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        dgroup = self.dgroup
        path, fname = os.path.split(dgroup.filename)


        opts = dict(linewidth=3, ylabel=plotlabels.norm,
                    xlabel=plotlabels.energy, delay_draw=True,
                    show_legend=True)

        ppanel.plot(dgroup.energy, dgroup.norm_corr, zorder=10, marker=None,
                    title='Over-absorption Correction:\n %s' % fname,
                    label='corrected', **opts)

        ppanel.oplot(dgroup.energy, dgroup.norm, zorder=10, marker='o',
                     markersize=3, label='original', **opts)

        ppanel.canvas.draw()
        ppanel.conf.draw_legend(show=True)

    def GetResponse(self):
        raise AttributError("use as non-modal dialog!")


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

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 400),
                           title="Calibrate / Align Energy")

        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LCEN)

        self.wids = wids = {}
        wids['grouplist'] = Choice(panel, choices=groupnames, size=(250, -1),
                                   action=self.on_groupchoice)
        wids['grouplist'].SetStringSelection(self.dgroup.filename)

        refgroups = ['None'] + groupnames

        wids['reflist'] = Choice(panel, choices=refgroups, size=(250, -1),
                              action=self.on_align)
        wids['reflist'].SetSelection(0)

        opts  = dict(size=(90, -1), digits=3, increment=0.1)
        for wname in ('e0_old', 'e0_new'):
            opts['action'] = partial(self.on_calib, name=wname)
            opts['pin_action'] = partial(self.on_select, name=wname)
            fspin, bmbtn = FloatSpinWithPin(panel, value=e0val, **opts)
            wids[wname] = fspin
            wids[wname+'btn'] = bmbtn

        opts['action'] = partial(self.on_calib, name='eshift')
        opts.pop('pin_action')
        wids['eshift'] = FloatSpin(panel, value=0, **opts)

        self.plottype = Choice(panel, choices=list(Plot_Choices.keys()),
                                   size=(250, -1), action=self.plot_results)


        apply_one = Button(panel, 'Save / Overwrite ', size=(150, -1),
                           action=self.on_apply_one)
        SetTip(apply_one, 'Save rebinned data, overwrite current arrays')

        apply_sel = Button(panel, 'Apply Shift to Selected Groups',
                           size=(250, -1),  action=self.on_apply_sel)
        SetTip(apply_sel, '''Apply the Energy Shift to all Selected Groups,
overwriting current arrays''')

        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                           action=self.on_saveas)
        SetTip(wids['save_as'], 'Save shifted data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1,
                                           self.dgroup.filename + '_eshift',
                                           size=(250, -1))

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text(' Energy Calibration for Group: ',  newrow=False)
        panel.Add(wids['grouplist'], dcol=3)

        add_text(' Plot Arrays as: ')
        panel.Add(self.plottype, dcol=3)

        add_text(' Auto-Align to : ')
        panel.Add(wids['reflist'], dcol=3)

        add_text(' Energy Reference (E0): ')
        panel.Add(wids['e0_old'])
        panel.Add(wids['e0_oldbtn'])
        add_text(' eV', newrow=False)

        add_text(' Calibrate to: ')
        panel.Add(wids['e0_new'])
        panel.Add(wids['e0_newbtn'])
        add_text(' eV', newrow=False)

        add_text(' Energy Shift : ')
        panel.Add(wids['eshift'], dcol=2)
        add_text(' eV', newrow=False)

        panel.Add(apply_one, newrow=True)
        panel.Add(apply_sel, dcol=4)

        panel.Add(wids['save_as'], newrow=True)
        panel.Add(wids['save_as_name'], dcol=3)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()
        self.plot_results()

    def onDone(self, event=None):
        self.Destroy()

    def on_select(self, event=None, opt=None):
        _x, _y = self.controller.get_cursor()
        if opt in self.wids:
            self.wids[opt].SetValue(_x)

    def on_groupchoice(self, event=None):
        dgroup = self.controller.get_group(self.wids['grouplist'].GetStringSelection())
        self.dgroup = dgroup
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_eshift')
        self.wids['e0_old'].SetValue(dgroup.e0)
        e0_new = dgroup.e0 + self.wids['eshift'].GetValue()
        self.wids['e0_new'].SetValue(e0_new)
        self.plot_results()

    def on_align(self, event=None, name=None, value=None):
        ref = self.controller.get_group(self.wids['reflist'].GetStringSelection())
        dat = self.dgroup
        if not hasattr(ref, 'dmude'):
            ref.dmude = np.gradient(ref.mu)/np.gradient(ref.energy)
        if not hasattr(dat, 'dmude'):
            dat.dmude = np.gradient(dat.mu)/np.gradient(dat.energy)

        i1 = index_of(ref.energy, ref.e0-15)
        i2 = index_of(ref.energy, ref.e0+35)

        def resid(pars, ref, dat, i1, i2):
            "fit residual"
            newx = dat.xdat + pars['eshift'].value
            scale = pars['scale'].value
            y = interp(newx, dat.dmude, ref.xdat, kind='cubic')
            return (y*scale - ref.dmude)[i1:i2]

        params = Parameters()
        params.add('eshift', value=ref.e0-dat.e0, min=-50, max=50)
        params.add('scale', value=1, min=0, max=50)

        result = minimize(resid, params, args=(ref, dat, i1, i2))
        eshift = result.params['eshift'].value
        self.wids['eshift'].SetValue(eshift)
        self.wids['e0_new'].SetValue(dat.e0 + eshift)

        xnew = self.dgroup.energy + eshift
        self.data = xnew, self.dgroup.norm[:]
        self.plot_results()

    def on_calib(self, event=None, name=None):
        wids = self.wids
        e0_old = wids['e0_old'].GetValue()
        e0_new = wids['e0_new'].GetValue()
        eshift = wids['eshift'].GetValue()

        if name in ('e0_old', 'e0_new'):
            eshift = e0_new - e0_old
            wids['eshift'].SetValue(eshift)
        elif name == 'eshift':
            e0_new = e0_old + eshift
            wids['e0_new'].SetValue(e0_new)

        xnew = self.dgroup.energy + eshift
        self.data = xnew, self.dgroup.norm[:]
        self.plot_results()

    def on_apply_one(self, event=None):
        xdat, ydat = self.data
        dgroup = self.dgroup
        dgroup.xdat = dgroup.energy = xdat
        self.parent.nb.pagelist[0].process(dgroup)
        self.plot_results()

    def on_apply_sel(self, event=None):
        eshift = self.wids['eshift'].GetValue()
        for checked in self.controller.filelist.GetCheckedStrings():
            fname  = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(fname)
            dgroup.xdat = dgroup.energy = eshift + dgroup.energy[:]
            self.parent.nb.pagelist[0].process(dgroup)

    def on_saveas(self, event=None):
        wids = self.wids
        fname = wids['grouplist'].GetStringSelection()
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)

        eshift = self.wids['eshift'].GetValue()
        ngroup.xdat = ngroup.energy = eshift + ngroup.energy[:]
        self.parent.onNewGroup(ngroup)

    def plot_results(self, event=None):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        xnew, ynew = self.data
        dgroup = self.dgroup
        path, fname = os.path.split(dgroup.filename)

        wids = self.wids
        e0_old = wids['e0_old'].GetValue()
        e0_new = wids['e0_new'].GetValue()

        xmin = min(e0_old, e0_new) - 25
        xmax = max(e0_old, e0_new) + 50

        use_deriv = self.plottype.GetStringSelection().lower().startswith('deriv')

        ylabel = plotlabels.norm
        if use_deriv:
            ynew = np.gradient(ynew)/np.gradient(xnew)
            ylabel = plotlabels.dmude

        opts = dict(xmin=xmin, xmax=xmax, linewidth=3,
                    ylabel=ylabel, xlabel=plotlabels.energy,
                    delay_draw=True, show_legend=True)

        ppanel.plot(xnew, ynew, zorder=20, marker=None,
                    title='Energy Calibration:\n %s' % fname,
                    label='shifted', **opts)


        xold, yold = self.dgroup.energy, self.dgroup.norm
        if use_deriv:
            yold = np.gradient(yold)/np.gradient(xold)

        ppanel.oplot(xold, yold, zorder=10, marker='o', markersize=3,
                     label='original', **opts)

        if wids['reflist'].GetStringSelection() != 'None':
            refgroup = self.controller.get_group(wids['reflist'].GetStringSelection())
            xref, yref = refgroup.energy, refgroup.norm
            if use_deriv:
                yref = np.gradient(yref)/np.gradient(xref)
            ppanel.oplot(xref, yref, style='short dashed', zorder=5,
                         marker=None, label=refgroup.filename, **opts)

        axv_opts = dict(ymin=0.05, ymax=0.95, linewidth=2.0, alpha=0.5,
                        zorder=1, label='_nolegend_')

        color1 = ppanel.conf.traces[0].color
        color2 = ppanel.conf.traces[1].color
        ppanel.axes.axvline(e0_new, color=color1, **axv_opts)
        ppanel.axes.axvline(e0_old, color=color2, **axv_opts)
        ppanel.canvas.draw()
        ppanel.conf.draw_legend(show=True)

    def GetResponse(self):
        raise AttributError("use as non-modal dialog!")

class RebinDataDialog(wx.Dialog):
    """dialog for rebinning data to standard XAFS grid"""
    def __init__(self, parent, controller, **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        groupnames = list(self.controller.file_groups.keys())

        xmin = min(self.dgroup.energy)
        xmax = max(self.dgroup.energy)
        e0val = getattr(self.dgroup, 'e0', xmin)

        self.data = [self.dgroup.energy[:], self.dgroup.mu[:],
                     self.dgroup.mu*0, e0val]

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 400),
                           title="Rebin mu(E) Data")

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.wids = wids = {}

        wids['grouplist'] = Choice(panel, choices=groupnames, size=(250, -1),
                                action=self.on_groupchoice)

        wids['grouplist'].SetStringSelection(self.dgroup.groupname)

        opts  = dict(size=(90, -1), precision=3, act_on_losefocus=True)

        wids['e0'] = FloatCtrl(panel, value=e0val, minval=xmin, maxval=xmax,
                             **opts)
        pre1 = 10.0*(1+int((xmin-e0val)/10.0))
        wids['pre1'] = FloatCtrl(panel, value=pre1,  **opts)
        wids['pre2'] = FloatCtrl(panel, value=-20, **opts)

        wids['xanes1'] = FloatCtrl(panel, value=-15,  **opts)
        wids['xanes2'] = FloatCtrl(panel, value=15, **opts)

        wids['exafs1'] = FloatCtrl(panel, value=etok(15),  **opts)
        wids['exafs2'] = FloatCtrl(panel, value=etok(xmax-e0val), **opts)

        wids['pre_step'] = FloatCtrl(panel, value=5.0,  **opts)
        wids['xanes_step'] = FloatCtrl(panel, value=0.25,  **opts)
        wids['exafs_step'] = FloatCtrl(panel, value=0.05,  **opts)

        for wname, wid in wids.items():
            if wname != 'grouplist':
                wid.SetAction(partial(self.on_rebin, name=wname))

        wids['apply'] = Button(panel, 'Save / Overwrite', size=(150, -1),
                               action=self.on_apply)
        SetTip(wids['apply'], 'Save rebinned data, overwrite current arrays')

        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                                 action=self.on_saveas)
        SetTip(wids['save_as'], 'Save corrected data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1, self.dgroup.filename + '_rebin',
                                           size=(250, -1))

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text('Rebin Data for Group: ', dcol=2, newrow=False)
        panel.Add(wids['grouplist'], dcol=3)

        add_text('E0: ')
        panel.Add(wids['e0'])
        add_text(' eV', newrow=False)

        add_text('Region ')
        add_text('Start ', newrow=False)
        add_text('Stop ', newrow=False)
        add_text('Step ', newrow=False)
        add_text('Units ', newrow=False)

        add_text('Pre-Edge: ')
        panel.Add(wids['pre1'])
        panel.Add(wids['pre2'])
        panel.Add(wids['pre_step'])
        add_text(' eV', newrow=False)

        add_text('XANES: ')
        panel.Add(wids['xanes1'])
        panel.Add(wids['xanes2'])
        panel.Add(wids['xanes_step'])
        add_text(' eV', newrow=False)

        add_text('EXAFS: ')
        panel.Add(wids['exafs1'])
        panel.Add(wids['exafs2'])
        panel.Add(wids['exafs_step'])
        add_text('1/\u212B', newrow=False)

        panel.Add(wids['apply'], dcol=2, newrow=True)
        panel.Add(wids['save_as'],  dcol=2, newrow=True)
        panel.Add(wids['save_as_name'], dcol=3)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()
        self.on_rebin()
        self.plot_results()

    def onDone(self, event=None):
        self.Destroy()

    def on_saveas(self, event=None):
        wids = self.wids
        fname = wids['grouplist'].GetStringSelection()
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)
        xdat, ydat, yerr, de0 = self.data
        ngroup.energy = ngroup.xdat = xdat
        ngroup.mu     = ngroup.ydat = ydat

        ngroup.delta_mu = getattr(ngroup, 'yerr', 1.0)
        self.parent.nb.pagelist[0].process(ngroup)
        self.parent.onNewGroup(ngroup)

    def on_groupchoice(self, event=None):
        self.dgroup = self.controller.get_group(self.wids['grouplist'].GetStringSelection())
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_rebin')
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
        args = dict(group=self.dgroup.groupname, e0=e0,
                    pre1=wids['pre1'].GetValue(),
                    pre2=wids['pre2'].GetValue(),
                    pre_step=wids['pre_step'].GetValue(),
                    exafs1=ktoe(wids['exafs1'].GetValue()),
                    exafs2=ktoe(wids['exafs2'].GetValue()),
                    exafs_kstep=wids['exafs_step'].GetValue(),
                    xanes_step=wids['xanes_step'].GetValue())

        # do rebin:
        cmd = """rebin_xafs({group}, e0={e0:f}, pre1={pre1:f}, pre2={pre2:f},
        pre_step={pre_step:f}, xanes_step={xanes_step:f}, exafs1={exafs1:f},
        exafs2={exafs2:f}, exafs_kstep={exafs_kstep:f})""".format(**args)
        self.controller.larch.eval(cmd)
        xnew = self.dgroup.rebinned.energy
        ynew = self.dgroup.rebinned.mu
        yerr = self.dgroup.rebinned.delta_mu
        self.data = xnew, ynew, yerr, e0
        self.plot_results()

    def on_apply(self, event=None):
        xdat, ydat, yerr, e0 = self.data
        dgroup = self.dgroup
        dgroup.energy = dgroup.xdat = xdat
        dgroup.mu     = dgroup.ydat = ydat
        self.parent.nb.pagelist[0].process(dgroup)
        self.plot_results()

    def on_done(self, event=None):
        self.Destroy()

    def plot_results(self):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        xnew, ynew, yerr, e0 = self.data
        dgroup = self.dgroup
        path, fname = os.path.split(dgroup.filename)

        ppanel.plot(xnew, ynew, zorder=20, delay_draw=True, marker='square',
                    linewidth=3, title='Enegy rebinning:\n %s' % fname,
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


        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 400),
                           title="Smooth mu(E) Data")

        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LCEN)

        self.wids = wids = {}

        wids['grouplist'] = Choice(panel, choices=groupnames, size=(250, -1),
                                action=self.on_groupchoice)

        wids['grouplist'].SetStringSelection(self.dgroup.groupname)
        SetTip(wids['grouplist'], 'select a new group, clear undo history')

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

        wids['apply'] = Button(panel, 'Save / Overwrite', size=(150, -1),
                               action=self.on_apply)
        SetTip(wids['apply'], 'Save corrected data, overwrite current arrays')

        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                           action=self.on_saveas)
        SetTip(wids['save_as'], 'Save corrected data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1, self.dgroup.filename + '_smooth',
                                           size=(250, -1))

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text('Smooth Data for Group: ', newrow=False)
        panel.Add(wids['grouplist'], dcol=5)

        add_text('Smoothing Method: ')
        panel.Add(self.smooth_op)
        add_text(' n= ', newrow=False)
        panel.Add(self.par_n)
        add_text(' order= ', newrow=False)
        panel.Add(self.par_o)

        add_text('Convolution Form: ')
        panel.Add(self.conv_op)
        add_text(' sigma: ', newrow=False)
        panel.Add(self.sigma)

        panel.Add((10, 10), newrow=True)
        panel.Add(self.message, dcol=5)

        panel.Add(wids['apply'], newrow=True)

        panel.Add(wids['save_as'],  newrow=True)
        panel.Add(wids['save_as_name'], dcol=5)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()
        self.plot_results()

    def onDone(self, event=None):
        self.Destroy()

    def on_saveas(self, event=None):
        wids = self.wids
        fname = wids['grouplist'].GetStringSelection()
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)
        xdat, ydat = self.data
        ngroup.energy = ngroup.xdat = xdat
        ngroup.mu     = ngroup.ydat = ydat
        self.parent.nb.pagelist[0].process(ngroup)
        self.parent.onNewGroup(ngroup)

    def on_groupchoice(self, event=None):
        self.dgroup = self.controller.get_group(self.wids['grouplist'].GetStringSelection())
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_smooth')
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
        self.parent.nb.pagelist[0].process(dgroup)
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
                    linewidth=3, title='Smoothing:\n %s' % fname,
                    label='smoothed', xlabel=plotlabels.energy,
                    ylabel=plotlabels.mu)

        xold, yold = self.dgroup.energy, self.dgroup.mu
        ppanel.oplot(xold, yold, zorder=10, delay_draw=False,
                     marker='o', markersize=4, linewidth=2.0,
                     label='original', show_legend=True)
        ppanel.canvas.draw()

    def GetResponse(self):
        raise AttributError("use as non-modal dialog!")

class DeconvolutionDialog(wx.Dialog):
    """dialog for energy deconvolution"""
    def __init__(self, parent, controller, **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        groupnames = list(self.controller.file_groups.keys())

        self.data = [self.dgroup.energy[:], self.dgroup.norm[:]]


        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 400),
                           title="Deconvolve mu(E) Data")

        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LCEN)

        self.wids = wids = {}

        wids['grouplist'] = Choice(panel, choices=groupnames, size=(250, -1),
                                action=self.on_groupchoice)

        wids['grouplist'].SetStringSelection(self.dgroup.groupname)
        SetTip(wids['grouplist'], 'select a new group, clear undo history')

        deconv_ops  = ('Lorenztian', 'Gaussian')

        wids['deconv_op'] = Choice(panel, choices=deconv_ops, size=(150, -1),
                                   action=self.on_deconvolve)

        wids['esigma'] = FloatSpin(panel, value=0.5, digits=2, size=(90, -1),
                                   increment=0.1, action=self.on_deconvolve)


        wids['apply'] = Button(panel, 'Save / Overwrite', size=(150, -1),
                               action=self.on_apply)
        SetTip(wids['apply'], 'Save corrected data, overwrite current arrays')

        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                           action=self.on_saveas)
        SetTip(wids['save_as'], 'Save corrected data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1, self.dgroup.filename + '_deconv',
                                           size=(250, -1))

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text('Deconvolve Data for Group: ', newrow=False)
        panel.Add(wids['grouplist'], dcol=5)

        add_text('Functional Form: ')
        panel.Add(wids['deconv_op'])

        add_text(' sigma= ')
        panel.Add(wids['esigma'])
        panel.Add(wids['apply'], newrow=True)
        panel.Add(wids['save_as'],  newrow=True)
        panel.Add(wids['save_as_name'], dcol=5)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()
        self.plot_results()

    def onDone(self, event=None):
        self.Destroy()

    def on_saveas(self, event=None):
        wids = self.wids
        fname = wids['grouplist'].GetStringSelection()
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)
        xdat, ydat = self.data
        ngroup.energy = ngroup.xdat = xdat
        ngroup.mu     = ngroup.ydat = ydat
        self.parent.nb.pagelist[0].process(ngroup)
        self.parent.onNewGroup(ngroup)

    def on_groupchoice(self, event=None):
        self.dgroup = self.controller.get_group(self.wids['grouplist'].GetStringSelection())
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_deconv')
        self.plot_results()

    def on_deconvolve(self, event=None, value=None):
        deconv_form  = self.wids['deconv_op'].GetStringSelection()

        esigma = self.wids['esigma'].GetValue()

        dopts = [self.dgroup.groupname,
                 "form='%s'" % (deconv_form),
                 "esigma=%.4f" % (esigma)]
        self.controller.larch.eval("xas_deconvolve(%s)" % (', '.join(dopts)))

        self.data = self.dgroup.energy[:], self.dgroup.deconv[:]
        self.plot_results()

    def on_apply(self, event=None):
        xdat, ydat = self.data
        dgroup = self.dgroup
        dgroup.energy = xdat
        dgroup.mu     = ydat
        self.parent.nb.pagelist[0].process(dgroup)
        self.plot_results()

    def plot_results(self):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        xnew, ynew = self.data
        dgroup = self.dgroup
        path, fname = os.path.split(dgroup.filename)

        ppanel.plot(xnew, ynew, zorder=20, delay_draw=True, marker=None,
                    linewidth=3, title='Deconvolving:\n %s' % fname,
                    label='deconvolved', xlabel=plotlabels.energy,
                    ylabel=plotlabels.mu)

        xold, yold = self.dgroup.energy, self.dgroup.norm
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

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 400),
                           title="Select Points to Remove")

        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LCEN)
        self.wids = wids = {}

        wids['grouplist'] = Choice(panel, choices=groupnames, size=(250, -1),
                                action=self.on_groupchoice)

        wids['grouplist'].SetStringSelection(self.dgroup.groupname)
        SetTip(wids['grouplist'], 'select a new group, clear undo history')

        bb_xlast = BitmapButton(panel, get_icon('pin'),
                                action=partial(self.on_select, opt='x'),
                                tooltip='use last point selected from plot')

        bb_range1 = BitmapButton(panel, get_icon('pin'),
                                action=partial(self.on_select, opt='range1'),
                                tooltip='use last point selected from plot')
        bb_range2 = BitmapButton(panel, get_icon('pin'),
                                action=partial(self.on_select, opt='range2'),
                                tooltip='use last point selected from plot')

        br_xlast = Button(panel, 'Remove point', size=(125, -1),
                          action=partial(self.on_remove, opt='x'))

        br_range = Button(panel, 'Remove range', size=(125, -1),
                          action=partial(self.on_remove, opt='range'))

        undo = Button(panel, 'Undo remove', size=(125, -1),
                      action=self.on_undo)
        wids['apply'] = Button(panel, 'Save / Overwrite', size=(150, -1),
                               action=self.on_apply)
        SetTip(wids['apply'], '''Save deglitched, overwrite current arrays,
clear undo history''')

        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                                 action=self.on_saveas)
        SetTip(wids['save_as'], 'Save deglitched data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1, self.dgroup.filename + '_clean',
                                           size=(250, -1))

        self.history_message = SimpleText(panel, '')

        floatopts = dict(precision=2, minval=xmin, maxval=xmax, size=(125, -1))

        self.wid_xlast = FloatCtrl(panel, value=lastx, **floatopts)
        self.wid_range1 = FloatCtrl(panel, value=lastx, **floatopts)
        self.wid_range2 = FloatCtrl(panel, value=lastx+1, **floatopts)

        self.choice_range = Choice(panel, choices=('above', 'below', 'between'),
                                    size=(90, -1), action=self.on_rangechoice)

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text('Deglitch Data for Group: ', dcol=2, newrow=False)
        panel.Add(wids['grouplist'], dcol=5)

        add_text('Single Energy : ', dcol=2)
        panel.Add(self.wid_xlast)
        panel.Add(bb_xlast)
        panel.Add(br_xlast)

        add_text('Energy Range : ')
        panel.Add(self.choice_range)
        panel.Add(self.wid_range1)
        panel.Add(bb_range1)
        panel.Add(br_range)

        panel.Add((10, 10), dcol=2, newrow=True)
        panel.Add(self.wid_range2)
        panel.Add(bb_range2)

        panel.Add(wids['apply'], dcol=2, newrow=True)
        panel.Add(self.history_message, dcol=2)
        panel.Add(undo)

        panel.Add(wids['save_as'], dcol=2, newrow=True)
        panel.Add(wids['save_as_name'], dcol=4)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()
        self.plot_results()

    def onDone(self, event=None):
        self.Destroy()

    def on_saveas(self, event=None):
        wids = self.wids
        fname = wids['grouplist'].GetStringSelection()
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)
        xdat, ydat = self.data[-1]
        ngroup.energy = ngroup.xdat = xdat
        ngroup.mu     = ngroup.ydat = ydat
        self.parent.nb.pagelist[0].process(ngroup)
        self.parent.onNewGroup(ngroup)

    def reset_data_history(self):
        xdat = self.dgroup.xdat[:]
        if hasattr(self.dgroup, 'energy'):
            xdat = self.dgroup.energy[:]

        ydat = self.dgroup.ydat[:]
        if hasattr(self.dgroup, 'mu'):
            ydat = self.dgroup.mu[:]
        self.data = [(xdat, ydat)]

    def on_groupchoice(self, event=None):
        self.dgroup = self.controller.get_group(self.wids['grouplist'].GetStringSelection())
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_clean')
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
        self.parent.nb.pagelist[0].process(dgroup)
        self.plot_results()

    def plot_results(self):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        xnew, ynew = self.data[-1]
        dgroup = self.dgroup
        path, fname = os.path.split(dgroup.filename)

        ppanel.plot(xnew, ynew, zorder=20, delay_draw=True, marker=None,
                    linewidth=3, title='De-glitching:\n %s' % fname,
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


class SpectraCalcDialog(wx.Dialog):
    """dialog for adding and subtracting spectra"""
    def __init__(self, parent, controller, **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        self.group_a = None
        groupnames = list(self.controller.file_groups.keys())

        self.data = [self.dgroup.energy[:], self.dgroup.norm[:]]
        xmin = min(self.dgroup.energy)
        xmax = max(self.dgroup.energy)
        e0val = getattr(self.dgroup, 'e0', xmin)

        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=(550, 400),
                           title="Spectra Calculations: Add, Subtract Spectra")

        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LCEN)

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        self.wids = wids = {}
        array_choices = ('Normalized \u03BC(E)', 'Raw \u03BC(E)')

        wids['array'] = Choice(panel, choices=array_choices, size=(250, -1))

        add_text('Array to use: ',  newrow=True)
        panel.Add(wids['array'], dcol=2)

        # group 'a' cannot be none, and defaults to current group
        gname = 'a'
        wname = 'group_%s' % gname
        wids[wname] = Choice(panel, choices=groupnames, size=(250, -1))
        wids[wname].SetStringSelection(self.dgroup.filename)
        add_text('   %s = ' % gname,  newrow=True)
        panel.Add(wids[wname], dcol=2)

        groupnames.insert(0, 'None')
        for gname in ('b', 'c', 'd', 'e', 'f', 'g'):
            wname = 'group_%s' % gname
            wids[wname] = Choice(panel, choices=groupnames, size=(250, -1))
            wids[wname].SetSelection(0)
            add_text('   %s = ' % gname,  newrow=True)
            panel.Add(wids[wname], dcol=2)

        wids['formula'] = wx.TextCtrl(panel, -1, 'a-b', size=(250, -1))
        add_text('Expression = ',  newrow=True)
        panel.Add(wids['formula'], dcol=2)

        wids['docalc'] = Button(panel, 'Calculate',
                                size=(150, -1), action=self.on_docalc)

        panel.Add(wids['docalc'], dcol=2, newrow=True)

        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                           action=self.on_saveas)
        SetTip(wids['save_as'], 'Save as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1,
                                           self.dgroup.filename + '_calc',
                                           size=(250, -1))
        panel.Add(wids['save_as'], newrow=True)
        panel.Add(wids['save_as_name'], dcol=2)
        wids['save_as'].Disable()
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()

    def onDone(self, event=None):
        self.Destroy()

    def on_docalc(self, event=None):
        self.expr = self.wids['formula'].GetValue()

        self.yname = 'mu'
        if self.wids['array'].GetStringSelection().lower().startswith('norm'):
            self.yname = 'norm'

        groups = {}
        for aname in ('a', 'b', 'c', 'd', 'e', 'f', 'g'):
            fname = self.wids['group_%s' % aname].GetStringSelection()
            if fname not in (None, 'None'):
                grp = self.controller.get_group(fname)
                groups[aname] = grp

        self.group_map = {key: group.groupname for key, group in groups.items()}
        # note: 'a' cannot be None, all others can be None
        group_a = self.group_a = groups.pop('a')
        xname = 'energy'
        if not hasattr(group_a, xname):
            xname = 'xdat'

        cmds = ['#From SpectraCalc dialog: ',
                'a = b = c = d = e = f = g = None',
                '_x = %s.%s' % (group_a.groupname, xname),
                'a = %s.%s' % (group_a.groupname, self.yname)]
        fmt = '%s = interp(%s.%s, %s.%s, _x)'
        for key, group in groups.items():
            cmds.append(fmt % (key, group.groupname, xname,
                               group.groupname, self.yname))
        cmds.append('_y = %s' % self.expr)
        cmds.append("""plot(_x, _y, label='%s', new=True,
   show_legend=True, xlabel='%s', title='Spectral Calculation')"""
                    % (self.expr, xname))

        self.controller.larch.eval('\n'.join(cmds))
        self.wids['save_as'].Enable()

    def on_saveas(self, event=None):
        wids = self.wids
        _larch = self.controller.larch
        fname = wids['group_a'].GetStringSelection()
        new_fname =self.wids['save_as_name'].GetValue()
        new_gname = file2groupname(new_fname, slen=5, symtable=_larch.symtable)

        cmds = ['%s = copy_group(%s)' % (new_gname, self.group_a.groupname),
                '%s.groupname = \'%s\'' % (new_gname, new_gname),
                '%s.filename = \'%s\'' % (new_gname, new_fname),
                '%s.calc_groups = %s' % (new_gname, repr(self.group_map)),
                '%s.calc_expr = \'%s\'' % (new_gname, self.expr),
                '%s.%s = %s' % (new_gname, self.yname, self.expr),
                'del _x, _y, a, b, c, d, e, f, g']

        _larch.eval('\n'.join(cmds))

        ngroup = getattr(_larch.symtable, new_gname, None)
        if ngroup is not None:
            self.parent.install_group(ngroup.groupname, ngroup.filename)
            self.parent.ShowFile(groupname=ngroup.groupname)

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


class ExportCSVDialog(wx.Dialog):
    """dialog for exporting groups to CSV file"""

    def __init__(self, parent, groupnames, **kws):
        title = "Export Selected Groups"
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        self.ychoices = OrderedDict((('normalized mu(E)', 'norm'),
                                     ('raw mu(E)', 'mu'),
                                     ('flattened mu(E)', 'flat'),
                                     ('d mu(E) / dE', 'dmude')))

        default_fname = 'Data.csv'
        if len(groupnames) > 0:
            default_fname = "%s_%i.csv" % (groupnames[0], len(groupnames))

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        self.master_group = Choice(panel, choices=groupnames, size=(200, -1))
        self.yarray_name  = Choice(panel, choices=list(self.ychoices.keys()), size=(200, -1))
        self.ofile_name   = wx.TextCtrl(panel, -1, default_fname,  size=(200, -1))

        panel.Add(SimpleText(panel, 'Group for Energy Array: '), newrow=True)
        panel.Add(self.master_group)

        panel.Add(SimpleText(panel, 'Array to Export: '), newrow=True)
        panel.Add(self.yarray_name)
        panel.Add(SimpleText(panel, 'File Name: '), newrow=True)
        panel.Add(self.ofile_name)

        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()

    def GetResponse(self, master=None, gname=None, ynorm=True):
        self.Raise()
        response = namedtuple('ExportCSVResponse', ('ok', 'master', 'yarray', 'filename'))
        ok = False
        if self.ShowModal() == wx.ID_OK:
            master = self.master_group.GetStringSelection()
            yarray = self.ychoices[self.yarray_name.GetStringSelection()]
            fname  = self.ofile_name.GetValue()
            ok = True
        return response(ok, master, yarray, fname)

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

        panel.Add(SimpleText(panel, 'Remove %i Selected Groups?' % (len(grouplist))),
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
