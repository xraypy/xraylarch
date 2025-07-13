import copy
from functools import partial
# from pathlib import Path
import numpy as np
from lmfit import Parameters, minimize
from matplotlib.ticker import FuncFormatter

import wx
# from wxmplot import PlotPanel
from xraydb import guess_edge
from larch.math import index_of, index_nearest, interp
from larch.utils.strutils import file2groupname
from larch.utils import path_split

from larch.wxlib import (GridPanel, FloatCtrl, FloatSpin,
                         FloatSpinWithPin, SimpleText, Choice, SetTip,
                         Button, HLine, LEFT, pack,
                         plotlabels, Font, FONTSIZE, FRAMESTYLE)

from larch.xafs import etok, ktoe, find_energy_step
from larch.utils.physical_constants import ATOM_SYMS
from larch.math import smooth

Plot_Choices = {'Normalized': 'norm', 'Derivative': 'dmude'}

EDGE_LIST = ('K', 'L3', 'L2', 'L1', 'M5', 'M4', 'M3')

NORM_MU = 'Normalized \u03BC(E)'

DEGLITCH_PLOTS = {'Raw \u03BC(E)': 'mu',
                  NORM_MU: 'norm',
                  '\u03c7(E)': 'chie',
                  '\u03c7(E)*(E-E_0)': 'chiew'}

SESSION_PLOTS = {'Normalized \u03BC(E)': 'norm',
                 'Raw \u03BC(E)': 'mu',
                 'k^2\u03c7(k)': 'chikw'}


def ensure_en_orig(dgroup):
    if not hasattr(dgroup, 'energy_orig'):
        dgroup.energy_orig = dgroup.energy[:]


def fit_frame(frame, panel):
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, LEFT, 5)
    pack(frame, sizer)
    frame.Fit()
    w0, h0 = frame.GetSize()
    w1, h1 = frame.GetBestSize()
    frame.SetSize((max(w0, w1)+25, max(h0, h1)+25))

def get_view_limits(ppanel):
    "get last zoom limits for a plot panel"
    xlim = ppanel.axes.get_xlim()
    ylim = ppanel.axes.get_ylim()
    return (xlim, ylim)

def set_view_limits(ppanel, xlim, ylim):
    "set zoom limits for a plot panel, as found from get_view_limits"
    ppanel.axes.set_xlim(xlim, emit=True)
    ppanel.axes.set_ylim(ylim, emit=True)


class OverAbsorptionFrame(wx.Frame):
    """window for correcting over-absorption"""
    def __init__(self, parent, controller, label='abscorr', **kws):
        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()

        self.label = label
        self.controller.register_group_callback(label, self, self.on_groupname)

        self.data = [self.dgroup.energy[:], self.dgroup.norm[:]]

        wx.Frame.__init__(self, parent, -1, size=(550, 400),
                          style=FRAMESTYLE)
        self.SetTitle("Correct Over-absorption")
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)
        self.wids = wids = {}

        wids['grouplabel'] = SimpleText(panel, self.dgroup.filename)

        # opts  = dict(size=(90, -1), precision=1, act_on_losefocus=True,
        #              minval=-90, maxval=180)

        fs_opts = dict(size=(90, -1), value=45, digits=1, increment=1)
        wids['phi_in']  = FloatSpin(panel, **fs_opts)
        wids['phi_out'] = FloatSpin(panel, **fs_opts)

        wids['elem'] = Choice(panel, choices=ATOM_SYMS[:98], size=(50, -1))
        wids['edge'] = Choice(panel, choices=EDGE_LIST, size=(50, -1))

        wids['formula'] = wx.TextCtrl(panel, -1, '', size=(250, -1))

        self.set_default_elem_edge(self.dgroup)

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
        panel.Add(wids['grouplabel'], dcol=5)

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
        # panel.Add(wids['apply'], dcol=2, newrow=True)

        panel.Add(wids['save_as'], newrow=True)
        panel.Add(wids['save_as_name'], dcol=3)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()
        fit_frame(self, panel)
        self.Bind(wx.EVT_CLOSE,  self.onDone)
        self.plot_results(use_zoom=False)
        self.Show()

    def onDone(self, event=None):
        self.controller.unregister_group_callback(self.label)
        self.Destroy()

    def set_default_elem_edge(self, dgroup):
        elem, edge = guess_edge(dgroup.e0)
        self.wids['elem'].SetStringSelection(elem)
        self.wids['edge'].SetStringSelection(edge)

    def on_groupname(self, event=None):
        self.dgroup = self.controller.get_group()
        self.set_default_elem_edge(self.dgroup)
        self.wids['grouplabel'].SetLabel(self.dgroup.filename)
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_abscorr')
        self.on_correct(use_zoom=False)

    def on_correct(self, event=None, use_zoom=True):
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
        self.cmd = cmd
        self.controller.larch.eval(cmd)
        self.plot_results(use_zoom=use_zoom)

    def on_apply(self, event=None):
        xplot, yplot = self.data
        dgroup = self.dgroup
        dgroup.xplot = dgroup.energy = xplot
        self.parent.process_normalization(dgroup)
        dgroup.journal.add('fluor_corr_command', self.cmd)
        self.plot_results()

    def on_saveas(self, event=None):
        wids = self.wids
        fname = self.dgroup.filename
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)

        if hasattr(self.dgroup, 'norm_corr' ):
            ngroup.mu = ngroup.norm_corr*1.0
            del ngroup.norm_corr

        ogroup = self.controller.get_group(fname)
        self.parent.install_group(ngroup, journal=ogroup.journal)
        olddesc = ogroup.journal.get('source_desc').value
        ngroup.journal.add('source_desc', f"fluo_corrected({olddesc})")
        ngroup.journal.add('fluor_correction_command', self.cmd)

    def plot_results(self, event=None, use_zoom=True):
        ppanel = self.controller.get_display(stacked=False).panel

        dgroup = self.dgroup
        xlim, ylim = get_view_limits(ppanel)
        path, fname = path_split(dgroup.filename)

        opts = dict(linewidth=3, ylabel=plotlabels.norm,
                    xlabel=plotlabels.energy, delay_draw=True,
                    show_legend=True)

        if self.controller.plot_erange is not None:
            opts['xmin'] = dgroup.e0 + self.controller.plot_erange[0]
            opts['xmax'] = dgroup.e0 + self.controller.plot_erange[1]

        if not hasattr(dgroup, 'norm_corr'):
            dgroup.norm_corr = dgroup.norm[:]

        ppanel.plot(dgroup.energy, dgroup.norm_corr, zorder=10, marker=None,
                    title='Over-absorption Correction:\n %s' % fname,
                    label='corrected', **opts)

        ppanel.oplot(dgroup.energy, dgroup.norm, zorder=10, marker='o',
                     markersize=3, label='original', **opts)
        if use_zoom:
            set_view_limits(ppanel, xlim, ylim)
        ppanel.canvas.draw()
        ppanel.conf.draw_legend(show=True)


class EnergyCalibrateFrame(wx.Frame):
    """window for calibrating energy"""
    def __init__(self, parent, controller, label='encalib', **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        self.label = label
        self.controller.register_group_callback(label, self, self.on_groupname)

        ensure_en_orig(self.dgroup)

        self.data = [self.dgroup.energy_orig[:], self.dgroup.norm[:]]


        wx.Frame.__init__(self, parent, -1, size=(550, 400), style=FRAMESTYLE)
        self.SetTitle("Calibrate / Align Energy")
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)

        self.wids = wids = {}
        wids['grouplabel'] = SimpleText(panel, self.dgroup.filename)

        refgroups = ['None'] + list(self.controller.file_groups.keys())
        wids['reflist'] = Choice(panel, choices=refgroups, size=(275, -1),
                                 action=self.on_align, default=0)

        opts = dict(size=(90, -1), digits=3, increment=0.1)

        opts['action'] = partial(self.on_calib, name='eshift')
        wids['eshift'] = FloatSpin(panel, value=0, **opts)

        self.plottype = Choice(panel, choices=list(Plot_Choices.keys()),
                                   size=(275, -1), action=self.plot_results)
        wids['do_align'] = Button(panel, 'Auto Align', size=(100, -1),
                                  action=self.on_align)

        wids['apply_one'] = Button(panel, 'Apply to Current Group', size=(200, -1),
                                   action=self.on_apply_one)

        wids['apply_sel'] = Button(panel, 'Apply to Selected Groups',
                                   size=(250, -1),  action=self.on_apply_sel)
        SetTip(wids['apply_sel'], 'Apply the Energy Shift to all Selected Groups')

        wids['save_as'] = Button(panel, 'Save As New Group ', size=(200, -1),
                           action=self.on_saveas)
        SetTip(wids['save_as'], 'Save shifted data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1,
                                           self.dgroup.filename + '_recalib',
                                           size=(275, -1))

        wids['sharedref_msg'] = wx.StaticText(panel, label="1 groups share this energy reference")
        wids['select_sharedref'] = Button(panel, 'Select Groups with shared reference',
                                          size=(300, -1),  action=self.on_select_sharedrefs)

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text(' Current Group: ',  newrow=False)
        panel.Add(wids['grouplabel'], dcol=2)

        add_text(' Auto-Align to : ')
        panel.Add(wids['reflist'], dcol=2)

        add_text(' Plot Arrays as: ')
        panel.Add(self.plottype, dcol=2)

        add_text(' Energy Shift (eV): ')
        panel.Add(wids['eshift'], dcol=1)
        panel.Add(wids['do_align'], dcol=1)
        panel.Add(HLine(panel, size=(500, 3)), dcol=4, newrow=True)

        panel.Add(wids['sharedref_msg'], dcol=2, newrow=True)
        panel.Add(wids['select_sharedref'], dcol=2)
        panel.Add(wids['apply_one'], dcol=1, newrow=True)
        panel.Add(wids['apply_sel'], dcol=2)

        panel.Add(HLine(panel, size=(500, 3)), dcol=4, newrow=True)

        panel.Add(wids['save_as'], newrow=True)
        panel.Add(wids['save_as_name'], dcol=3)

        panel.pack()

        fit_frame(self, panel)
        self.Bind(wx.EVT_CLOSE,  self.onDone)
        self.plot_results(use_zoom=False)
        wx.CallAfter(self.get_groups_shared_energyrefs)
        self.Show()

    def on_select(self, event=None, opt=None):
        _x, _y = self.controller.get_cursor()
        if opt in self.wids:
            self.wids[opt].SetValue(_x)

    def get_groups_shared_energyrefs(self, dgroup=None):
        if dgroup is None:
            dgroup = self.controller.get_group()
        sharedrefs = [dgroup.filename]
        try:
            eref = dgroup.config.xasnorm.get('energy_ref', None)
        except:
            eref = None
        if eref is None:
            eref = dgroup.groupname


        for key, val in self.controller.file_groups.items():
            if dgroup.groupname == val:
                continue
            g = self.controller.get_group(val)
            try:
                geref = g.config.xasnorm.get('energy_ref', None)
            except:
                geref = None
            # print(key, val, geref, geref == ref_filename)
            if geref == eref or geref == dgroup.filename:
                sharedrefs.append(key)
        self.wids['sharedref_msg'].SetLabel(f" {len(sharedrefs):d} groups share this energy reference")
        return sharedrefs

    def on_select_sharedrefs(self, event=None):
        groups = self.get_groups_shared_energyrefs()
        self.controller.filelist.SetCheckedStrings(groups)

    def onDone(self, event=None):
        self.controller.unregister_group_callback(self.label)
        self.Destroy()

    def on_groupname(self, event=None):
        self.dgroup = self.controller.get_group()
        self.wids['grouplabel'].SetLabel(self.dgroup.filename)
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_recalib')
        self.on_align(use_zoom=False)

    def on_align(self, event=None, name=None, value=None, use_zoom=True):
        ref = self.controller.get_group(self.wids['reflist'].GetStringSelection())
        dat = self.dgroup
        ensure_en_orig(dat)
        ensure_en_orig(ref)

        dat.xplot = dat.energy_orig[:]
        ref.xplot = ref.energy_orig[:]
        estep = find_energy_step(dat.xplot)
        i1 = index_of(ref.energy_orig, ref.e0-20)
        i2 = index_of(ref.energy_orig, ref.e0+20)

        def resid(pars, ref, dat, i1, i2):
            "fit residual"
            newx = dat.xplot + pars['eshift'].value
            scale = pars['scale'].value
            y = interp(newx, dat.dmude, ref.xplot, kind='cubic')
            return smooth(ref.xplot, y*scale-ref.dmude, xstep=estep, sigma=0.50)[i1:i2]

        params = Parameters()
        ex0 = ref.e0-dat.e0
        emax = 50.0
        if abs(ex0) > 75:
            ex0 = 0.00
            emax = (abs(ex0) + 75.0)
        elif abs(ex0) > 10:
            emax = (abs(ex0) + 75.0)
        params.add('eshift', value=ex0, min=-emax, max=emax)
        params.add('scale', value=1, min=1.e-8, max=50)
        # print("Fit params ", params)
        result = minimize(resid, params, args=(ref, dat, i1, i2),
                          max_nfev=1000)
        # print(fit_report(result))
        eshift = result.params['eshift'].value
        self.wids['eshift'].SetValue(eshift)

        ensure_en_orig(self.dgroup)
        xnew = self.dgroup.energy_orig + eshift
        self.data = xnew, self.dgroup.norm[:]
        self.plot_results(use_zoom=use_zoom)

    def on_calib(self, event=None, name=None, use_zoom=True):
        wids = self.wids
        eshift = wids['eshift'].GetValue()
        ensure_en_orig(self.dgroup)
        xnew = self.dgroup.energy_orig + eshift
        self.data = xnew, self.dgroup.norm[:]
        self.plot_results(use_zoom=use_zoom)

    def on_apply_one(self, event=None):
        xplot, yplot = self.data
        dgroup = self.dgroup
        eshift = self.wids['eshift'].GetValue()

        ensure_en_orig(dgroup)

        idx, norm_page = self.parent.get_nbpage('xasnorm')
        norm_page.wids['energy_shift'].SetValue(eshift)

        dgroup.energy_shift = eshift
        dgroup.xplot = dgroup.energy = eshift + dgroup.energy_orig[:]
        dgroup.journal.add('energy_shift ', eshift)
        self.parent.process_normalization(dgroup)
        self.plot_results()

    def on_apply_sel(self, event=None):
        eshift = self.wids['eshift'].GetValue()
        idx, norm_page = self.parent.get_nbpage('xasnorm')
        for checked in self.controller.filelist.GetCheckedStrings():
            fname  = self.controller.file_groups[str(checked)]
            dgroup = self.controller.get_group(fname)
            ensure_en_orig(dgroup)
            dgroup.energy_shift = eshift
            norm_page.wids['energy_shift'].SetValue(eshift)

            dgroup.xplot = dgroup.energy = eshift + dgroup.energy_orig[:]
            dgroup.journal.add('energy_shift ', eshift)
            self.parent.process_normalization(dgroup)

    def on_saveas(self, event=None):
        wids = self.wids
        fname = self.dgroup.filename
        eshift = wids['eshift'].GetValue()
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)

        ensure_en_orig(ngroup)
        ngroup.xplot = ngroup.energy = eshift + ngroup.energy_orig[:]
        ngroup.energy_shift = 0
        ngroup.energy_ref = ngroup.groupname

        ogroup = self.controller.get_group(fname)
        self.parent.install_group(ngroup, journal=ogroup.journal)
        olddesc = ogroup.journal.get('source_desc').value
        ngroup.journal.add('source_desc', f"energy_shifted({olddesc}, {eshift:.4f})")
        ngroup.journal.add('energy_shift ', 0.0)

    def plot_results(self, event=None, use_zoom=True):
        ppanel = self.controller.get_display(stacked=False).panel
        ppanel.oplot
        xnew, ynew = self.data
        dgroup = self.dgroup

        xlim, ylim = get_view_limits(ppanel)
        path, fname = path_split(dgroup.filename)

        wids = self.wids
        eshift = wids['eshift'].GetValue()
        e0_old = dgroup.e0
        e0_new = dgroup.e0 + eshift

        xmin = min(e0_old, e0_new) - 25
        xmax = max(e0_old, e0_new) + 50

        use_deriv = self.plottype.GetStringSelection().lower().startswith('deriv')

        ylabel = plotlabels.norm
        if use_deriv:
            ynew = np.gradient(ynew)/np.gradient(xnew)
            ylabel = plotlabels.dmude

        opts = dict(xmin=xmin, xmax=xmax, ylabel=ylabel, delay_draw=True,
                    xlabel=plotlabels.energy, show_legend=True)

        if self.controller.plot_erange is not None:
            opts['xmin'] = dgroup.e0 + self.controller.plot_erange[0]
            opts['xmax'] = dgroup.e0 + self.controller.plot_erange[1]

        xold, yold = self.dgroup.energy_orig, self.dgroup.norm
        if use_deriv:
            yold = np.gradient(yold)/np.gradient(xold)

        ppanel.plot(xold, yold, zorder=10, marker='o', markersize=3,
                     label='original', linewidth=2, color='#1f77b4',
                     title=f'Energy Calibration:\n {fname}', **opts)

        ppanel.oplot(xnew, ynew, zorder=15, marker='+', markersize=3,
                    linewidth=2, label='shifted',
                    color='#d62728', **opts)

        if wids['reflist'].GetStringSelection() != 'None':
            refgroup = self.controller.get_group(wids['reflist'].GetStringSelection())
            xref, yref = refgroup.energy, refgroup.norm
            if use_deriv:
                yref = np.gradient(yref)/np.gradient(xref)

            ppanel.oplot(xref, yref, style='solid', zorder=5, color='#2ca02c',
                         marker=None, label=refgroup.filename, **opts)
        if use_zoom:
            set_view_limits(ppanel, xlim, ylim)
        ppanel.canvas.draw()


class RebinDataFrame(wx.Frame):
    """window for rebinning data to standard XAFS grid"""
    def __init__(self, parent, controller, label='rebin', **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        self.label = label
        self.controller.register_group_callback(label, self, self.on_groupname)

        xmin = min(self.dgroup.energy)
        xmax = max(self.dgroup.energy)
        e0val = getattr(self.dgroup, 'e0', xmin)
        xanes_step = 0.05 * (1 + max(1, int(e0val / 2000.0)))
        self.data = [self.dgroup.energy[:], self.dgroup.mu[:],
                     self.dgroup.mu*0, e0val]

        wx.Frame.__init__(self, parent, -1, size=(550, 400), style=FRAMESTYLE)
        self.SetTitle("Rebin mu(E) Data")
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LEFT)

        self.wids = wids = {}
        wids['grouplabel'] = SimpleText(panel, self.dgroup.filename)

        opts  = dict(size=(90, -1), precision=3, act_on_losefocus=True)

        wids['e0'] = FloatCtrl(panel, value=e0val, minval=xmin, maxval=xmax, **opts)
        pre1 = 10.0*(1+int((xmin-e0val)/10.0))
        wids['pre1'] = FloatCtrl(panel, value=pre1,  **opts)
        wids['pre2'] = FloatCtrl(panel, value=-15, **opts)
        wids['xanes1'] = FloatCtrl(panel, value=-15,  **opts)
        wids['xanes2'] = FloatCtrl(panel, value=15, **opts)
        wids['exafs1'] = FloatCtrl(panel, value=etok(15),  **opts)
        wids['exafs2'] = FloatCtrl(panel, value=etok(xmax-e0val), **opts)

        wids['pre_step'] = FloatCtrl(panel, value=2.0,  **opts)
        wids['xanes_step'] = FloatCtrl(panel, value=xanes_step,  **opts)
        wids['exafs_step'] = FloatCtrl(panel, value=0.05,  **opts)

        wids['method'] = Choice(panel, choices=('spline', 'boxcar', 'centroid'),
                                 size=(80, -1), action=self.on_rebin)
        for wname, wid in wids.items():
            if wname not in ('grouplabel', 'method') and hasattr(wid, 'SetAction'):
                wid.SetAction(partial(self.on_rebin, name=wname))

        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                                 action=self.on_saveas)
        SetTip(wids['save_as'], 'Save corrected data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1, self.dgroup.filename + '_rebin_s',
                                           size=(250, -1))

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text('Rebin Data for Group: ', dcol=2, newrow=False)
        panel.Add(wids['grouplabel'], dcol=3)

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

        add_text('Smoothing Method: ', dcol=2)
        panel.Add(wids['method'])

        # panel.Add(wids['apply'], dcol=2, newrow=True)
        panel.Add(wids['save_as'],  dcol=2, newrow=True)
        panel.Add(wids['save_as_name'], dcol=3)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()

        fit_frame(self, panel)
        self.Bind(wx.EVT_CLOSE,  self.onDone)
        self.on_rebin()
        self.plot_results(use_zoom=False)
        self.Show()

    def onDone(self, event=None):
        self.controller.unregister_group_callback(self.label)
        self.Destroy()

    def on_groupname(self, event=None):
        self.dgroup = self.controller.get_group()
        self.wids['grouplabel'].SetLabel(self.dgroup.filename)
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_rebin')
        self.on_rebin(use_zoom=False)

    def on_rebin(self, event=None, name=None, value=None, use_zoom=True):
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

        method = wids['method'].GetStringSelection().lower()
        e0 = wids['e0'].GetValue()
        args = dict(group=self.dgroup.groupname, e0=e0,
                    method=method,
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
        exafs2={exafs2:f}, exafs_kstep={exafs_kstep:f}, method='{method}')""".format(**args)
        self.cmd = cmd
        self.controller.larch.eval(cmd)
        wids['save_as_name'].SetValue(f'{self.dgroup.filename}_rebin_{method[:3]}')

        if hasattr(self.dgroup, 'rebinned'):
            xnew = self.dgroup.rebinned.energy
            ynew = self.dgroup.rebinned.mu
            yerr = self.dgroup.rebinned.delta_mu
            self.data = xnew, ynew, yerr, e0
            self.plot_results(use_zoom=use_zoom)

    def on_apply(self, event=None):
        xplot, yplot, yerr, e0 = self.data
        dgroup = self.dgroup
        dgroup.energy = dgroup.xplot = xplot
        dgroup.mu     = dgroup.yplot = yplot
        dgroup.journal.add('rebin_command ', self.cmd)
        self.parent.process_normalization(dgroup)
        self.plot_results()

    def on_saveas(self, event=None):
        wids = self.wids
        fname = self.dgroup.filename
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)
        xplot, yplot, yerr, de0 = self.data
        ngroup.energy = ngroup.xplot = xplot
        ngroup.mu     = ngroup.yplot = yplot

        ogroup = self.controller.get_group(fname)
        olddesc = ogroup.journal.get('source_desc').value

        ngroup.delta_mu = getattr(ngroup, 'yerr', 1.0)
        self.parent.process_normalization(ngroup)

        self.parent.install_group(ngroup, journal=ogroup.journal)
        ngroup.journal.add('source_desc', f"rebinned({olddesc})")
        ngroup.journal.add('rebin_command ', self.cmd)

    def plot_results(self, event=None, use_zoom=True):
        ppanel = self.controller.get_display(stacked=False).panel
        xnew, ynew, yerr, e0 = self.data
        dgroup = self.dgroup
        xlim, ylim = get_view_limits(ppanel)
        path, fname = path_split(dgroup.filename)

        opts = {'delay_draw': True}
        if self.controller.plot_erange is not None:
            opts['xmin'] = dgroup.e0 + self.controller.plot_erange[0]
            opts['xmax'] = dgroup.e0 + self.controller.plot_erange[1]

        ppanel.plot(xnew, ynew, zorder=20, marker='square',
                    linewidth=3, title='Enegy rebinning:\n %s' % fname,
                    label='rebinned', xlabel=plotlabels.energy,
                    ylabel=plotlabels.mu, **opts)

        xold, yold = self.dgroup.energy, self.dgroup.mu
        ppanel.oplot(xold, yold, zorder=10,
                     marker='o', markersize=4, linewidth=2.0,
                     label='original', show_legend=True, **opts)
        if use_zoom:
            set_view_limits(ppanel, xlim, ylim)
        ppanel.canvas.draw()

class SmoothDataFrame(wx.Frame):
    """window for smoothing data"""
    def __init__(self, parent, controller, label='smooth', **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        self.label = label
        self.controller.register_group_callback(label, self, self.on_groupname)

        self.data = [self.dgroup.energy[:], self.dgroup.mu[:]]

        wx.Frame.__init__(self, parent, -1, size=(550, 400), style=FRAMESTYLE)
        self.SetTitle("Smooth mu(E) Data")
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)

        self.wids = wids = {}

        wids['grouplabel'] = SimpleText(panel, self.dgroup.filename)

        smooth_ops = ('None', 'Boxcar', 'Savitzky-Golay', 'Convolution')
        conv_ops  = ('Lorenztian', 'Gaussian')

        self.smooth_op = Choice(panel, choices=smooth_ops, size=(150, -1),
                                action=self.on_smooth)
        self.smooth_op.SetSelection(0)

        self.conv_op = Choice(panel, choices=conv_ops, size=(150, -1),
                                action=self.on_smooth)
        self.conv_op.SetSelection(0)

        # opts  = dict(size=(50, -1), act_on_losefocus=True, odd_only=False)

        self.sigma = FloatSpin(panel, value=1, digits=2, min_val=0, increment=0.1,
                               size=(60, -1), action=self.on_smooth)

        self.par_n = FloatSpin(panel, value=2, digits=0, min_val=1, increment=1,
                               size=(60, -1), action=self.on_smooth)

        self.par_o = FloatSpin(panel, value=1, digits=0, min_val=1, increment=1,
                               size=(60, -1), action=self.on_smooth)

        self.message = SimpleText(panel, label='         ', size=(200, -1))


        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                           action=self.on_saveas)
        SetTip(wids['save_as'], 'Save corrected data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1, self.dgroup.filename + '_smooth',
                                           size=(250, -1))

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text('Smooth Data for Group: ', newrow=False)
        panel.Add(wids['grouplabel'], dcol=5)

        add_text('Smoothing Method: ')
        panel.Add(self.smooth_op)
        add_text(' n = ', newrow=False)
        panel.Add(self.par_n)
        add_text(' order=  ', newrow=False)
        panel.Add(self.par_o)

        add_text('Convolution Form: ')
        panel.Add(self.conv_op)
        add_text(' sigma: ', newrow=False)
        panel.Add(self.sigma)

        panel.Add((10, 10), newrow=True)
        panel.Add(self.message, dcol=5)

        panel.Add(wids['save_as'],  newrow=True)
        panel.Add(wids['save_as_name'], dcol=5)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()
        fit_frame(self, panel)
        self.Bind(wx.EVT_CLOSE,  self.onDone)
        self.plot_results(use_zoom=False)
        self.Show()

    def onDone(self, event=None):
        self.controller.unregister_group_callback(self.label)
        self.Destroy()

    def on_groupname(self, event=None):
        self.dgroup = self.controller.get_group()
        self.wids['grouplabel'].SetLabel(self.dgroup.filename)
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_smooth')
        self.on_smooth(use_zoom=False)

    def on_smooth(self, event=None, value=None, use_zoom=True):
        smoothop = self.smooth_op.GetStringSelection().lower()
        convop   = self.conv_op.GetStringSelection()
        self.conv_op.Enable(smoothop.startswith('conv'))
        self.sigma.Enable(smoothop.startswith('conv'))
        self.message.SetLabel('')
        self.par_n.SetMin(1)
        self.par_n.odd_only = False
        par_n = int(self.par_n.GetValue())
        par_o = int(self.par_o.GetValue())
        sigma = self.sigma.GetValue()
        cmd = '{group:s}.mu' # No smoothing
        estep = find_energy_step(self.data[0])
        if smoothop.startswith('box'):
            self.par_n.Enable()
            cmd = "boxcar({group:s}.mu, {par_n:d})"
            self.conv_op.Disable()
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
            cmd = "smooth({group:s}.energy, {group:s}.mu, xstep={estep:f}, sigma={sigma:f}, form='{convop:s}')"
        self.cmd = cmd.format(group=self.dgroup.groupname, convop=convop,
                              estep=estep, sigma=sigma, par_n=par_n, par_o=par_o)

        self.controller.larch.eval("_tmpy = %s" % self.cmd)
        self.data = self.dgroup.energy[:], self.controller.symtable._tmpy
        self.plot_results(use_zoom=use_zoom)

    def on_apply(self, event=None):
        xplot, yplot = self.data
        dgroup = self.dgroup
        dgroup.energy = xplot
        dgroup.mu     = yplot
        dgroup.journal.add('smooth_command', self.cmd)
        self.parent.process_normalization(dgroup)
        self.plot_results()

    def on_saveas(self, event=None):
        wids = self.wids
        fname = self.controller.get_group().filename
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)

        xplot, yplot = self.data
        ngroup.energy = ngroup.xplot = xplot
        ngroup.mu     = ngroup.yplot = yplot

        ogroup = self.controller.get_group(fname)
        olddesc = ogroup.journal.get('source_desc').value

        self.parent.install_group(ngroup, journal=ogroup.journal)
        ngroup.journal.add('source_desc', f"smoothed({olddesc})")
        ngroup.journal.add('smooth_command', self.cmd)
        self.parent.process_normalization(ngroup)


    def plot_results(self, event=None, use_zoom=True):
        ppanel = self.controller.get_display(stacked=False).panel
        xnew, ynew = self.data
        dgroup = self.dgroup
        path, fname = path_split(dgroup.filename)
        opts = {'delay_draw': True}
        xlim, ylim = get_view_limits(ppanel)

        if self.controller.plot_erange is not None:
            opts['xmin'] = dgroup.e0 + self.controller.plot_erange[0]
            opts['xmax'] = dgroup.e0 + self.controller.plot_erange[1]

        ppanel.plot(xnew, ynew, zorder=20, marker=None,
                    linewidth=3, title='Smoothing:\n %s' % fname,
                    label='smoothed', xlabel=plotlabels.energy,
                    ylabel=plotlabels.mu, **opts)

        xold, yold = self.dgroup.energy, self.dgroup.mu
        ppanel.oplot(xold, yold, zorder=10,
                     marker='o', markersize=4, linewidth=2.0,
                     label='original', show_legend=True, **opts)
        if use_zoom:
            set_view_limits(ppanel, xlim, ylim)
        ppanel.canvas.draw()

class DeconvolutionFrame(wx.Frame):
    """window for energy deconvolution"""
    def __init__(self, parent, controller, label='deconv', **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        self.label = label
        self.controller.register_group_callback(label, self, self.on_groupname)

        # groupnames = list(self.controller.file_groups.keys())

        self.data = [self.dgroup.energy[:], self.dgroup.norm[:]]


        wx.Frame.__init__(self, parent, -1, size=(550, 400), style=FRAMESTYLE)
        self.SetTitle("Deconvolve mu(E) Data")
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)

        self.wids = wids = {}

        wids['grouplabel'] = SimpleText(panel, self.dgroup.filename)

        deconv_ops  = ('Lorenztian', 'Gaussian')

        wids['deconv_op'] = Choice(panel, choices=deconv_ops, size=(150, -1),
                                   action=self.on_deconvolve)

        wids['esigma'] = FloatSpin(panel, value=0.5, digits=2, size=(90, -1),
                                   increment=0.1, action=self.on_deconvolve)

        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                           action=self.on_saveas)
        SetTip(wids['save_as'], 'Save corrected data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1, self.dgroup.filename + '_deconv',
                                           size=(250, -1))

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text('Deconvolve Data for Group: ', newrow=False)
        panel.Add(wids['grouplabel'], dcol=5)

        add_text('Functional Form: ')
        panel.Add(wids['deconv_op'])

        add_text(' sigma= ')
        panel.Add(wids['esigma'])
        # panel.Add(wids['apply'], newrow=True)
        panel.Add(wids['save_as'],  newrow=True)
        panel.Add(wids['save_as_name'], dcol=5)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  newrow=True)
        panel.pack()
        fit_frame(self, panel)
        self.Bind(wx.EVT_CLOSE,  self.onDone)
        self.plot_results(use_zoom=False)
        self.Show()

    def onDone(self, event=None):
        self.controller.unregister_group_callback(self.label)
        self.Destroy()

    def on_saveas(self, event=None):
        wids = self.wids
        fname = self.dgroup.filename
        new_fname = wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)
        xplot, yplot = self.data
        ngroup.energy = ngroup.xplot = xplot
        ngroup.mu     = ngroup.yplot = yplot

        ogroup = self.controller.get_group(fname)
        olddesc = ogroup.journal.get('source_desc').value

        self.parent.install_group(ngroup, journal=ogroup.journal)
        ngroup.journal.add('source_desc', f"deconvolved({olddesc})")
        ngroup.journal.add('deconvolve_command', self.cmd)
        self.parent.process_normalization(ngroup)

    def on_groupname(self, event=None):
        self.dgroup = self.controller.get_group()
        self.wids['grouplabel'].SetLabel(self.dgroup.filename)
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_deconv')
        self.on_deconvolve(use_zoom=False)


    def on_deconvolve(self, event=None, value=None, use_zoom=True):
        deconv_form  = self.wids['deconv_op'].GetStringSelection()

        esigma = self.wids['esigma'].GetValue()

        dopts = [self.dgroup.groupname,
                 "form='%s'" % (deconv_form),
                 "esigma=%.4f" % (esigma)]
        self.cmd = "xas_deconvolve(%s)" % (', '.join(dopts))
        self.controller.larch.eval(self.cmd)

        self.data = self.dgroup.energy[:], self.dgroup.deconv[:]
        self.plot_results(use_zoom=use_zoom)

    def on_apply(self, event=None):
        xplot, yplot = self.data
        dgroup = self.dgroup
        dgroup.energy = xplot
        dgroup.mu     = yplot
        dgroup.journal.add('deconvolve_command ', self.cmd)
        self.parent.process_normalization(dgroup)
        self.plot_results()

    def plot_results(self, event=None, use_zoom=True):
        ppanel = self.controller.get_display(stacked=False).panel
        xnew, ynew = self.data
        dgroup = self.dgroup
        xlim, ylim = get_view_limits(ppanel)
        path, fname = path_split(dgroup.filename)

        opts = {'delay_draw': True}
        if self.controller.plot_erange is not None:
            opts['xmin'] = dgroup.e0 + self.controller.plot_erange[0]
            opts['xmax'] = dgroup.e0 + self.controller.plot_erange[1]

        ppanel.plot(xnew, ynew, zorder=20, marker=None,
                    linewidth=3, title='Deconvolving:\n %s' % fname,
                    label='deconvolved', xlabel=plotlabels.energy,
                    ylabel=plotlabels.mu, **opts)

        xold, yold = self.dgroup.energy, self.dgroup.norm
        ppanel.oplot(xold, yold, zorder=10,
                     marker='o', markersize=4, linewidth=2.0,
                     label='original', show_legend=True, **opts)
        if use_zoom:
            set_view_limits(ppanel, xlim, ylim)
        ppanel.canvas.draw()

class DeglitchFrame(wx.Frame):
    """window for deglitching or removing unsightly data points"""
    def __init__(self, parent, controller, label='deglitch', **kws):
        self.parent = parent
        self.controller = controller
        self.label = label
        self.controller.register_group_callback(label, self, self.on_groupname)
        self.wids = {}
        self.plot_markers = None
        self.dgroup = self.controller.get_group()

        self.reset_data_history()
        xplot, yplot = self.data

        lastx, lasty = self.controller.get_cursor()
        if lastx is None:
            lastx = max(xplot)

        wx.Frame.__init__(self, parent, -1, size=(550, 400), style=FRAMESTYLE)
        self.SetTitle("Select Points to Remove")
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)
        wids = self.wids

        wids['grouplabel'] = SimpleText(panel, self.dgroup.filename)

        br_xlast = Button(panel, 'Remove point', size=(125, -1),
                          action=partial(self.on_remove, opt='x'))

        br_range = Button(panel, 'Remove range', size=(125, -1),
                          action=partial(self.on_remove, opt='range'))

        undo = Button(panel, 'Undo remove', size=(125, -1),
                          action=self.on_undo)

        wids['save_as'] = Button(panel, 'Save As New Group: ', size=(150, -1),
                                 action=self.on_saveas)
        SetTip(wids['save_as'], 'Save deglitched data as new group')

        wids['save_as_name'] = wx.TextCtrl(panel, -1, self.dgroup.filename + '_clean',
                                           size=(250, -1))

        self.history_message = SimpleText(panel, '')

        # opts  = dict(size=(125, -1), digits=2, increment=0.1)
        for wname in ('xlast', 'range1', 'range2'):
            if wname == 'range2':
                lastx += 1
            pin_action = partial(self.parent.onSelPoint, opt=wname,
                                 relative_e0=False,
                                 callback=self.on_pinvalue)

            float_action=partial(self.on_floatvalue, opt=wname)
            fspin, pinb = FloatSpinWithPin(panel, value=lastx,
                                           pin_action=pin_action,
                                           action=float_action)
            wids[wname] = fspin
            wids[wname+'_pin'] = pinb

        self.choice_range = Choice(panel, choices=('above', 'below', 'between'),
                                    size=(90, -1), action=self.on_rangechoice)

        self.choice_range.SetStringSelection('above')
        wids['range2'].Disable()

        wids['plotopts'] = Choice(panel, choices=list(DEGLITCH_PLOTS.keys()),
                                  size=(175, -1),
                                  action=self.on_plotchoice)

        wids['plotopts'].SetStringSelection(NORM_MU)

        def add_text(text, dcol=1, newrow=True):
            panel.Add(SimpleText(panel, text), dcol=dcol, newrow=newrow)

        add_text('Deglitch Data for Group: ', dcol=2, newrow=False)
        panel.Add(wids['grouplabel'], dcol=5)

        add_text('Single Energy : ', dcol=2)
        panel.Add(wids['xlast'])
        panel.Add(wids['xlast_pin'])
        panel.Add(br_xlast)

        add_text('Plot Data as:  ', dcol=2)
        panel.Add(wids['plotopts'], dcol=5)

        add_text('Energy Range : ')
        panel.Add(self.choice_range)
        panel.Add(wids['range1'])
        panel.Add(wids['range1_pin'])
        panel.Add(br_range)

        panel.Add((10, 10), dcol=2, newrow=True)
        panel.Add(wids['range2'])
        panel.Add(wids['range2_pin'])

        # panel.Add(wids['apply'], dcol=2, newrow=True)

        panel.Add(wids['save_as'], dcol=2, newrow=True)
        panel.Add(wids['save_as_name'], dcol=4)
        panel.Add(Button(panel, 'Done', size=(150, -1), action=self.onDone),
                  dcol=2, newrow=True)
        panel.Add(self.history_message, dcol=2)
        panel.Add(undo)

        panel.pack()
        self.Bind(wx.EVT_CLOSE,  self.onDone)
        fit_frame(self, panel)
        self.plot_results(use_zoom=False)
        self.Show()

    def on_groupname(self, event=None):
        self.dgroup = self.controller.get_group()
        self.wids['grouplabel'].SetLabel(self.dgroup.filename)
        self.wids['save_as_name'].SetValue(self.dgroup.filename + '_clean')

    def onDone(self, event=None):
        self.controller.unregister_group_callback(self.label)
        self.Destroy()

    def reset_data_history(self):
        plottype = 'norm'
        if 'plotopts' in self.wids:
            plotstr = self.wids['plotopts'].GetStringSelection()
            plottype = DEGLITCH_PLOTS[plotstr]
        self.data = self.get_xydata(datatype=plottype)
        self.xmasks = [np.ones(len(self.data[0]), dtype=bool)]
        self.plot_markers = None

    def get_xydata(self, datatype='mu'):
        if hasattr(self.dgroup, 'energy'):
            xplot = self.dgroup.energy[:]
        else:
            xplot = self.dgroup.xplot[:]
        yplot = self.dgroup.yplot[:]
        if datatype == 'mu' and hasattr(self.dgroup, 'mu'):
            yplot = self.dgroup.mu[:]
        elif datatype == 'norm':
            if not hasattr(self.dgroup, 'norm'):
                self.parent.process_normalization(self.dgroup)
            yplot = self.dgroup.norm[:]
        elif datatype in ('chie', 'chiew'):
            if not hasattr(self.dgroup, 'chie'):
                self.parent.process_exafs(self.dgroup)
            yplot = self.dgroup.chie[:]
            if datatype == 'chiew':
                yplot = self.dgroup.chie[:] * (xplot-self.dgroup.e0)
        return (xplot, yplot)

    def on_rangechoice(self, event=None):
        sel = self.choice_range.GetStringSelection()
        self.wids['range2'].Enable(sel == 'between')


    def on_plotchoice(self, event=None):
        plotstr = self.wids['plotopts'].GetStringSelection()
        plottype = DEGLITCH_PLOTS[plotstr]
        self.data = self.get_xydata(datatype=plottype)
        self.plot_results()

    def on_pinvalue(self, opt='__', xsel=None, **kws):
        if xsel is not None and opt in self.wids:
            self.wids[opt].SetValue(xsel)
        self.plot_markers = opt
        self.plot_results()

    def on_floatvalue(self, val=None, opt='_', **kws):
        self.plot_markers = opt
        self.plot_results()

    def on_remove(self, event=None, opt=None):
        xwork, ywork = self.data
        mask = copy.deepcopy(self.xmasks[-1])
        if opt == 'x':
            bad = index_nearest(xwork, self.wids['xlast'].GetValue())
            mask[bad] = False
        elif opt == 'range':
            rchoice = self.choice_range.GetStringSelection().lower()
            x1 = index_nearest(xwork, self.wids['range1'].GetValue())
            x2 = None
            if rchoice == 'below':
                x2, x1 = x1, x2
            elif rchoice == 'between':
                x2 = index_nearest(xwork, self.wids['range2'].GetValue())
                if x1 > x2:
                    x1, x2 = x2, x1
            mask[x1:x2] = False
        self.xmasks.append(mask)
        self.plot_results()

    def on_undo(self, event=None):
        if len(self.xmasks) == 1:
            self.xmasks = [np.ones(len(self.data[0]), dtype=bool)]
        else:
            self.xmasks.pop()
        self.plot_results()

    def on_apply(self, event=None):
        xplot, yplot = self.get_xydata(datatype='xydata')
        mask = self.xmasks[-1]
        dgroup = self.dgroup
        energies_removed  = xplot[np.where(~mask)].tolist()
        dgroup.energy = dgroup.xplot = xplot[mask]
        dgroup.mu     = dgroup.yplot = yplot[mask]
        self.reset_data_history()
        dgroup.journal.add('deglitch_removed_energies', energies_removed)
        self.parent.process_normalization(dgroup)
        self.plot_results()

    def on_saveas(self, event=None):
        fname = self.controller.get_group().filename
        new_fname = self.wids['save_as_name'].GetValue()
        ngroup = self.controller.copy_group(fname, new_filename=new_fname)
        xplot, yplot = self.get_xydata(datatype='mu')
        mask = self.xmasks[-1]
        energies_removed  = xplot[np.where(~mask)].tolist()

        ngroup.energy = ngroup.xplot = xplot[mask]
        ngroup.mu     = ngroup.yplot = yplot[mask]
        ngroup.energy_orig = 1.0*ngroup.energy

        ogroup = self.controller.get_group(fname)
        olddesc = ogroup.journal.get('source_desc').value

        self.parent.install_group(ngroup, journal=ogroup.journal)
        ngroup.journal.add('source_desc', f"deglitched({olddesc})")
        ngroup.journal.add('deglitch_removed_energies', energies_removed)

        self.parent.process_normalization(ngroup)

    def plot_results(self, event=None, use_zoom=True):
        ppanel = self.controller.get_display(stacked=False).panel

        xplot, yplot = self.data
        dgroup = self.dgroup

        path, fname = path_split(dgroup.filename)

        plotstr = self.wids['plotopts'].GetStringSelection()
        plottype = DEGLITCH_PLOTS[plotstr]

        xlabel=plotlabels.energy
        if plottype in ('chie', 'chiew'):
            # xmin = self.dgroup.e0
            xlabel = xlabel=plotlabels.ewithk

        opts = dict(xlabel=xlabel, title='De-glitching:\n %s' % fname,
                    delay_draw=True)

        ylabel =  {'mu': plotlabels.mu,
                   'norm': plotlabels.norm,
                   'chie':  plotlabels.chie,
                   'chiew': plotlabels.chiew.format(1),
                   }.get(plottype, plotlabels.norm)

        dgroup.plot_xlabel = xlabel
        dgroup.plot_ylabel = ylabel

        xlim, ylim = get_view_limits(ppanel)

        ppanel.plot(xplot, yplot, zorder=10, marker=None, linewidth=3,
                    label='original', ylabel=ylabel, **opts)

        if len(self.xmasks) > 1:
            mask = self.xmasks[-1]
            ppanel.oplot(xplot[mask], yplot[mask], zorder=15,
                         marker='o', markersize=3, linewidth=2.0,
                         label='current', show_legend=True, **opts)

        def ek_formatter(x, pos):
            ex = float(x) - self.dgroup.e0
            s = '' if ex < 0 else '\n[%.1f]' % (etok(ex))
            return r"%1.4g%s" % (x, s)

        if use_zoom:
            set_view_limits(ppanel, xlim, ylim)
        if plottype in ('chie', 'chiew'):
            ppanel.axes.xaxis.set_major_formatter(FuncFormatter(ek_formatter))

        if self.plot_markers is not None:
            rchoice = self.choice_range.GetStringSelection().lower()
            xwork, ywork = self.data
            opts = dict(marker='o', markersize=6, zorder=2, label='_nolegend_',
                        markerfacecolor='#66000022', markeredgecolor='#440000')
            if self.plot_markers == 'xlast':
                bad = index_nearest(xwork, self.wids['xlast'].GetValue())
                ppanel.axes.plot([xwork[bad]], [ywork[bad]], **opts)
            else:
                bad = index_nearest(xwork, self.wids['range1'].GetValue())
                if rchoice == 'above':
                    ppanel.axes.plot([xwork[bad:]], [ywork[bad:]], **opts)
                elif rchoice == 'below':
                    ppanel.axes.plot([xwork[:bad+1]], [ywork[:bad+1]], **opts)
                elif rchoice == 'between':
                    bad2 = index_nearest(xwork, self.wids['range2'].GetValue())
                    ppanel.axes.plot([xwork[bad:bad2+1]],
                                     [ywork[bad:bad2+1]], **opts)


        ppanel.canvas.draw()

        self.history_message.SetLabel('%i items in history' % (len(self.xmasks)-1))


SPECCALC_SETUP = """#From SpectraCalc window:
_x = {group:s}.{xname:s}
a = {group:s}.{yname:s}
b = c = d = e = f = g = None
"""

SPECCALC_INTERP = "{key:s} = interp({group:s}.{xname:s}, {group:s}.{yname:s}, _x)"
SPECCALC_PLOT = """plot(_x, ({expr:s}), label='{expr:s}', new=True,
   show_legend=True, xlabel='{xname:s}', title='Spectral Calculation')"""

SPECCALC_SAVE = """{new:s} = copy_xafs_group({group:s})
{new:s}.groupname = '{new:s}'
{new:s}.mu = ({expr:s})
{new:s}.filename = '{fname:s}'
{new:s}.journal.add('calc_groups', {group_map:s})
{new:s}.journal.add('calc_arrayname', '{yname:s}')
{new:s}.journal.add('calc_expression', '{expr:s}')
del _x, a, b, c, d, e, f, g"""


class SpectraCalcFrame(wx.Frame):
    """window for adding and subtracting spectra"""
    def __init__(self, parent, controller, label='scalc', **kws):

        self.parent = parent
        self.controller = controller
        self.dgroup = self.controller.get_group()
        self.group_a = None

        self.label = label
        groupnames = list(self.controller.file_groups.keys())

        self.data = [self.dgroup.energy[:], self.dgroup.norm[:]]


        wx.Frame.__init__(self, parent, -1, size=(475, 525), style=FRAMESTYLE)
        self.SetTitle("Spectra Calculations: Add, Subtract Spectra")
        self.SetFont(Font(FONTSIZE))
        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)

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
        fit_frame(self, panel)
        self.Bind(wx.EVT_CLOSE,  self.onDone)
        self.Show()

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
            xname = 'xplot'

        cmds = [SPECCALC_SETUP.format(group=group_a.groupname,
                                      xname=xname, yname=self.yname)]

        for key, group in groups.items():
            cmds.append(SPECCALC_INTERP.format(key=key, group=group.groupname,
                                               xname=xname, yname=self.yname))

        cmds.append(SPECCALC_PLOT.format(expr=self.expr, xname=xname))
        self.controller.larch.eval('\n'.join(cmds))
        self.wids['save_as'].Enable()

    def on_saveas(self, event=None):
        # wids = self.wids
        _larch = self.controller.larch
        # fname = wids['group_a'].GetStringSelection()
        new_fname =self.wids['save_as_name'].GetValue()
        new_gname = file2groupname(new_fname, slen=5, symtable=_larch.symtable)

        gmap = []
        for k, v in self.group_map.items():
            gmap.append(f'"{k}": "{v}"')
        gmap = '{%s}' % (', '.join(gmap))

        _larch.eval(SPECCALC_SAVE.format(new=new_gname, fname=new_fname,
                                         group=self.group_a.groupname,
                                         group_map=gmap,
                                         yname=self.yname, expr=self.expr))


        journal={'source_desc': f"{new_fname}: calc({self.expr})",
                 'calc_groups': gmap,  'calc_expression': self.expr}

        ngroup = getattr(_larch.symtable, new_gname, None)
        if ngroup is not None:
            self.parent.install_group(ngroup, source=journal['source_desc'],
                                      journal=journal)
