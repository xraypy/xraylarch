#!/usr/bin/env python
"""
fitting GUI for XRF display
"""
import time
import copy
from functools import partial
from collections import OrderedDict

import numpy as np
import wx
import wx.lib.agw.pycollapsiblepane as CP
import wx.lib.scrolledpanel as scrolled

from wxutils import (SimpleText, FloatCtrl, FloatSpin, Choice, Font, pack,
                     Button, Check, HLine, GridPanel, RowPanel, CEN, LEFT,
                     RIGHT)

from .notebooks import flatnotebook
from .parameter import ParameterPanel
from .periodictable import PeriodicTablePanel

from larch import Group
from ..fitting import Parameter, Minimizer

from ..math import index_of, gaussian
from ..xray import material_mu, material_get

from ..xrf import xrf_background

def read_filterdata(flist, _larch):
    """ read filters data"""
    materials = _larch.symtable.get_symbol('_xray._materials')
    out = OrderedDict()
    out['None'] = ('', 0)
    for name in flist:
        if name in materials:
            out[name]  = materials[name]
    return out

def VarChoice(p, default=0):
    return Choice(p, choices=['Fix', 'Vary'],
                  size=(70, -1), default=default)

NFILTERS = 4
Detector_Materials = ['Si', 'Ge']
EFano = {'Si': 3.66 * 0.115, 'Ge': 3.0 * 0.130}
EFano_Text = '      Peak Widths:  sigma = sqrt(E_Fano * Energy + Noise**2) '

class FitSpectraFrame(wx.Frame):
    """Frame for Spectral Analysis"""

    Filter_Lengths = ['microns', 'mm', 'cm']

    Filter_Materials = ['None', 'air', 'nitrogen', 'helium', 'kapton',
                        'aluminum', 'mylar', 'beryllium', 'diamond',
                        'argon', 'silicon nitride', 'pmma', 'silicon',
                        'quartz', 'sapphire', 'graphite', 'boron nitride']

    def __init__(self, parent, size=(550, 700)):
        self.parent = parent
        self._larch = parent.larch
        self.mca = parent.mca
        self.conf = {}

        self.paramgroup = Group()

        wx.Frame.__init__(self, parent, -1, 'Fit XRF Spectra',
                          size=size, style=wx.DEFAULT_FRAME_STYLE)

        if not hasattr(self.parent, 'filters_data'):
            self.parent.filters_data = read_filterdata(self.Filter_Materials,
                                                       _larch=self._larch)

        self.wids = {}

        self.panels = OrderedDict()
        self.panels['Beam, Detector, Filters'] = self.beamdet_page
        self.panels['Elements and Peaks'] = self.elempeaks_page

        self.nb = flatnotebook(self, self.panels)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)

        bpanel = wx.Panel(self)
        self.SetBackgroundColour((235, 235, 235))
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.wids['show_components'] = Check(bpanel, label='Show All Components',
                                             default=False)
        bsizer.Add(Button(bpanel, 'Calculate Model',
                          action=self.onShowModel), 0, LEFT)
        bsizer.Add(Button(bpanel, 'Fit Model',
                          action=self.onFitModel), 0, LEFT)
        bsizer.Add(self.wids['show_components'], 0, LEFT)

        pack(bpanel, bsizer)
        sizer.Add(bpanel, 0, CEN)
        sizer.Add((5,5))
        pack(self, sizer)
        self.Show()
        self.Raise()

    def elempeaks_page(self, **kws):
        "create row for filters parameters"
        mca = self.parent.mca
        wids = self.wids
        p = GridPanel(self)
        tooltip_msg = 'Select Elements to include in model'
        self.selected_elems = []
        self.ptable = PeriodicTablePanel(p, multi_select=True, fontsize=13,
                                         tooltip_msg=tooltip_msg,
                                         onselect=self.onElemSelect)

        for roi in self.mca.rois:
            words = roi.name.split()
            elem = words[0].title()
            if elem in self.ptable.syms and elem not in self.ptable.selected:
                self.ptable.onclick(label=elem)

        p.AddText(' Select Elements to include :', colour='#880000', dcol=7)
        p.Add(self.ptable, dcol=6, newrow=True)

        wids['peak_step'] = FloatSpin(p, value=0.01, digits=3, min_val=0,
                                      max_val=10.0, increment=1.e-2)
        wids['peak_tail'] = FloatSpin(p, value=0.01, digits=3, min_val=0,
                                        max_val=0.25, increment=1.e-3)

        wids['peak_step_vary'] = VarChoice(p, default=0)
        wids['peak_tail_vary'] = VarChoice(p, default=0)


        p.AddText('  Step (%): ', newrow=True)
        p.Add(wids['peak_step'])
        p.Add(wids['peak_step_vary'])

        p.AddText('  Tail: ', newrow=False)
        p.Add(wids['peak_tail'])


        p.Add(wids['peak_tail_vary'])


        p.Add(HLine(p, size=(550, 3)), dcol=8, newrow=True)
        p.AddText(' Elastic / Compton peaks: ', colour='#880000',
                  dcol=5, newrow=True)

        opts = dict(size=(100, -1),
                    min_val=0, digits=4, increment=0.010)
        for name, def_use  in (('Elastic', True), ('Compton1', True),
                               ('Compton2', False)):
            en = self.mca.incident_energy
            dtail = 0.01
            dgamm = 0.75
            if name == 'Compton1':
                en = 0.97 * self.mca.incident_energy
                dtail = 0.1
                dgamm = 2.0
            elif name == 'Compton2':
                en = 0.94 * self.mca.incident_energy
                dtail = 0.2
                dgamm = 2.0
            t = name.lower()
            wids['%s_use'%t] = Check(p, label='Include',
                                      default=def_use,
                                      action=partial(self.onUsePeak, name=t))
            wids['%s_cen_vary'%t] = VarChoice(p, default=1)
            wids['%s_step_vary'%t] = VarChoice(p, default=0)
            wids['%s_gamm_vary'%t] = VarChoice(p, default=0)
            wids['%s_tail_vary'%t] = VarChoice(p, default=0)
            wids['%s_sigm_vary'%t] = VarChoice(p, default=0)

            wids['%s_cen'%t]  = FloatSpin(p, value=en, digits=1, min_val=0,
                                           increment=10)
            wids['%s_step'%t] = FloatSpin(p, value=0.05, digits=3, min_val=0,
                                           max_val=20.0, increment=1.e-2)
            wids['%s_tail'%t] = FloatSpin(p, value=dtail, digits=3, min_val=0,
                                           max_val=30.0, increment=1.e-3)
            wids['%s_gamm'%t] = FloatSpin(p, value=dgamm, digits=3, min_val=0,
                                           max_val=30.0, increment=0.1)
            wids['%s_sigm'%t] = FloatSpin(p, value=2.0, digits=2, min_val=0,
                                           max_val=10.0, increment=0.1)
            if not def_use:
                self.onUsePeak(name=t, value=False)

            p.AddText("  %s " % name,  colour='#880000', newrow=True)
            p.Add(wids['%s_use' % t], dcol=2)
            p.AddText('  Energy (eV): ', newrow=False)
            p.Add(wids['%s_cen'%t])
            p.Add(wids['%s_cen_vary'%t])

            p.AddText('  Step (%): ', newrow=True)
            p.Add(wids['%s_step'%t])
            p.Add(wids['%s_step_vary'%t])

            p.AddText('  Tail: ', newrow=False)
            p.Add(wids['%s_tail'%t])
            p.Add(wids['%s_tail_vary'%t])

            p.AddText('  Gamma : ', newrow=True)
            p.Add(wids['%s_gamm'%t])
            p.Add(wids['%s_gamm_vary'%t])

            p.AddText('  Sigma Scale : ', newrow=False)
            p.Add(wids['%s_sigm'%t])
            p.Add(wids['%s_sigm_vary'%t])

            p.Add(HLine(p, size=(550, 3)), dcol=7, newrow=True)

        p.pack()
        return p

    def beamdet_page(self, **kws):
        "beam / detector settings"
        mca = self.parent.mca
        conf = self.parent.conf

        xray_energy = getattr(mca, 'incident_energy', None)
        if xray_energy is None:
            xray_energy = 20.0
        if xray_energy < 250:
            xray_energy = 1000.0 * xray_energy
        mca.incident_energy = xray_energy

        en_min = getattr(conf, 'e_min', 1.0) * 1000.0
        en_max = getattr(conf, 'e_max', None)
        if en_max is None:
            en_max = mca.incident_energy
        en_max = en_max * 1000.0

        cal_offset = getattr(mca, 'offset',  0) * 1000.0
        cal_slope = getattr(mca, 'slope',  0.010) * 1000.0
        det_efano = getattr(mca, 'det_efano',  EFano['Si'])
        det_noise = getattr(mca, 'det_noise',  30)
        det_efano = getattr(mca, 'det_efano',  EFano['Si'])
        width = getattr(mca, 'bgr_width',    5000)
        expon = getattr(mca, 'bgr_exponent', 2)

        wids = self.wids
        main = wx.Panel(self)

        pdet = GridPanel(main, itemstyle=LEFT)
        pflt = GridPanel(main, itemstyle=LEFT)

        wids['bgr_use'] = Check(pdet, label='Fit Background-Subtracted Spectrum',
                                default=False, action=self.onUseBackground)
        wids['bgr_width'] = FloatSpin(pdet, value=width, min_val=0, max_val=15000,
                                   digits=0, increment=500, size=(100, -1))
        wids['bgr_expon'] = Choice(pdet, choices=['2', '4', '6'],
                                   size=(70, -1), default=0)
        wids['bgr_show'] = Button(pdet, 'Show Background', size=(150, -1),
                                  action=self.onShowBgr)
        wids['bgr_width'].Disable()
        wids['bgr_expon'].Disable()
        wids['bgr_show'].Disable()

        wids['cal_slope'] = FloatSpin(pdet, value=cal_slope,
                                      min_val=0, max_val=100,
                                      digits=3, increment=0.01, size=(100, -1))
        wids['cal_offset'] = FloatSpin(pdet, value=cal_offset,
                                      min_val=-500, max_val=500,
                                      digits=3, increment=0.01, size=(100, -1))

        wids['cal_vary'] = VarChoice(pdet, default=0)

        wids['det_mat'] = Choice(pdet, choices=Detector_Materials,
                                 size=(55, -1), default=0,
                                 action=self.onDetMaterial)

        wids['det_thk'] = FloatSpin(pdet, value=0.400, size=(100, -1),
                                     increment=0.010, min_val=0, max_val=10,
                                     digits=3)

        wids['det_noise_vary'] = VarChoice(pdet, default=1)
        wids['det_efano_vary'] = VarChoice(pdet, default=0)

        opts = dict(size=(100, -1), min_val=0, max_val=250000,
                    digits=1, increment=10)
        wids['en_xray'] = FloatSpin(pdet, value=xray_energy, **opts)
        wids['en_min'] = FloatSpin(pdet, value=en_min, **opts)
        wids['en_max'] = FloatSpin(pdet, value=en_max, **opts)

        opts.update({'digits': 4, 'max_val': 500, 'increment': 1})
        wids['det_noise'] = FloatSpin(pdet, value=det_noise, **opts)

        opts.update({'max_val': 1, 'increment': 0.001})
        wids['det_efano'] = FloatSpin(pdet, value=det_efano, **opts)


        pdet.AddText(' Beam Energy, Fit Range :', colour='#880000', dcol=3)
        pdet.AddText('    X-ray Energy (eV): ', newrow=True)
        pdet.Add(wids['en_xray'])
        pdet.AddText('    Fit Range (eV): ', newrow=True)
        pdet.Add(wids['en_min'])
        pdet.AddText(' : ')
        pdet.Add(wids['en_max'])

        pdet.Add(HLine(pdet, size=(550, 3)), dcol=4, newrow=True)
        pdet.AddText(' Energy Calibration :', colour='#880000', dcol=1, newrow=True)
        pdet.AddText('   Vary in fit:')
        pdet.Add(wids['cal_vary'], dcol=2)
        pdet.AddText('    Offset (eV): ', newrow=True)
        pdet.Add(wids['cal_offset'])
        pdet.AddText('    Slope (eV/bin): ', newrow=True)
        pdet.Add(wids['cal_slope'])


        pdet.Add(HLine(pdet, size=(550, 3)), dcol=4, newrow=True)
        pdet.AddText(' Detector :', colour='#880000', dcol=4, newrow=True)
        pdet.AddText('    Material:  ', newrow=True)
        pdet.Add(wids['det_mat'])
        pdet.AddText('    Thickness (mm): ', newrow=True)
        pdet.Add(wids['det_thk'])

        pdet.AddText('    Noise (eV): ', newrow=True)
        pdet.Add(wids['det_noise'])
        pdet.Add(wids['det_noise_vary'], dcol=2)
        pdet.AddText('    E_Fano (eV): ', newrow=True)
        pdet.Add(wids['det_efano'])
        pdet.Add(wids['det_efano_vary'], dcol=2)
        pdet.AddText(EFano_Text, newrow=True,  dcol=4)

        pdet.Add(HLine(pdet, size=(550, 3)), dcol=4, newrow=True)
        pdet.AddText(" Background: ", colour='#880000', newrow=True)
        pdet.Add(wids['bgr_use'], dcol=3)
        pdet.AddText('    Exponent:', newrow=True)
        pdet.Add(wids['bgr_expon'])
        pdet.AddText('    Width (keV): ', newrow=True)
        pdet.Add(wids['bgr_width'], dcol=2)
        pdet.Add(wids['bgr_show'])
        pdet.pack()

        # filters section
        bx = Button(pflt, 'Customize Filter List', size=(150, -1),
                    action = self.onEditFilters)
        bx.Disable()
        pflt.Add(HLine(pflt, size=(550, 3)), dcol=6)
        pflt.AddText(' Filters :', colour='#880000', dcol=3, newrow=True)
        pflt.Add(bx, dcol=3)
        pflt.AddManyText(('    filter', 'material',
                        'thickness (mm)', 'vary thickness'), style=CEN, newrow=True)
        opts = dict(size=(100, -1), min_val=0, digits=3, increment=0.010)
        for i in range(1, NFILTERS+1):
            t = 'filt%d' % i
            wids['%s_mat'%t] = Choice(pflt, choices=self.Filter_Materials, default=0,
                                      size=(125, -1),
                                      action=partial(self.onFilterMaterial, index=i))
            wids['%s_thk'%t] = FloatSpin(pflt, value=0.0, **opts)
            wids['%s_var'%t] = VarChoice(pflt, default=0)

            pflt.AddText('     %i' % (i), newrow=True)
            pflt.Add(wids['%s_mat' % t])
            pflt.Add(wids['%s_thk' % t])
            pflt.Add(wids['%s_var' % t])

        pflt.Add(HLine(pflt, size=(550, 3)), dcol=6, newrow=True)
        pflt.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(pdet)
        sizer.Add(pflt)
        pack(main, sizer)
        return main

    def onUseBackground(self, event=None):
        use = self.wids['bgr_use'].IsChecked()
        self.wids['bgr_width'].Enable(use)
        self.wids['bgr_expon'].Enable(use)
        self.wids['bgr_show'].Enable(use)


    def onShowBgr(self, event=None):
        mca    = self.mca
        parent = self.parent
        width  = self.wids['bgr_width'].GetValue()/1000.0
        expon  = int(self.wids['bgr_expon'].GetStringSelection())

        xrf_background(energy=mca.energy, counts=mca.counts, group=mca,
                       width=width, exponent=expon, _larch=parent.larch)

        mca.bgr_width = width
        mca.bgr_expoent = expon
        parent.plotmca(mca)
        parent.oplot(mca.energy, mca.bgr, label='background',
                     color=parent.conf.bgr_color, linewidth=2, style='--')

    def onDetMaterial(self, event=None):
        det_mat = self.wids['det_mat'].GetStringSelection()
        if det_mat not in EFano:
            det_mat = 'Si'
        self.wids['det_efano'].SetValue(EFano[det_mat])

    def onFilterMaterial(self, evt=None, index=0):
        name = evt.GetString()
        form, den = self.parent.filters_data.get(name, ('', 0))
        t = 'filt%d' % index
        thick = self.wids['%s_thk'%t]
        if den < 0.1 and thick.GetValue() < 0.1:
            thick.SetValue(5.0)
            thick.SetIncrement(0.5)
        elif den > 0.1 and thick.GetValue() < 1.e-5:
            thick.SetValue(0.0250)
            thick.SetIncrement(0.005)

    def onEditFilters(self, evt=None):
        print( 'on Edit Filters ',  evt)

    def onElemSelect(self, event=None, elem=None):
        self.ptable.tsym.SetLabel('')
        self.ptable.title.SetLabel('%d elements selected' % len(self.ptable.selected))


    def onUsePeak(self, event=None, name=None, value=None):
        if value is None and event is not None:
            value = event.IsChecked()
        if name is None:
            return
        for a in ('cen', 'step', 'tail', 'sigm', 'gamm'):
            self.wids['%s_%s'%(name, a)].Enable(value)
            varwid = self.wids.get('%s_%s_vary'%(name, a), None)
            if varwid is not None:
                varwid.Enable(value)

    def build_model(self, match_amplitudes=True):
        """build xrf_model from form settings"""
        vars = {'Vary':'True', 'Fix': 'False', 'True':True, 'False': False}
        opts = {}
        for key, wid in self.wids.items():
            if hasattr(wid, 'GetValue'):
                val = wid.GetValue()
            elif hasattr(wid, 'IsChecked'):
                val = wid.IsChecked()
            elif isinstance(wid, Choice):
                val = wid.GetStringSelection()
                if val.title() in vars:
                    val = vars[val.title()]
            elif hasattr(wid, 'GetStringSelection'):
                val = wid.GetStringSelection()
            else:
                opts[key] = '????'
            opts[key] = val
        opts['count_time'] = getattr(self.mca, 'real_time', 1.0)

        # convert thicknesses from mm to cm:
        opts['det_thk'] /= 10.0
        # peak step is displayed as percent, used as fraction
        opts['peak_step'] /= 100.0

        script = ["""xrfmod = xrf_model(xray_energy={en_xray:.1f}, count_time={count_time:.3f},
        energy_min={en_min:.1f}, energy_max={en_max:.1f})""".format(**opts),
                  """xrfmod.set_detector(thickness={det_thk:.4f},
         material='{det_mat:s}', cal_offset={cal_offset:.4f},
         cal_slope={cal_slope:.4f}, vary_cal_offset={cal_vary:s},
         vary_cal_slope={cal_vary:s}, vary_cal_quad=False,
         peak_step={peak_step:.4f}, vary_peak_step={peak_step_vary:s},
         peak_tail={peak_tail:.4f}, vary_peak_tail={peak_tail_vary:s},
         peak_gamma=0.5, vary_peak_gamma=False,
         noise={det_noise:.2f}, vary_noise={det_noise_vary:s},
         efano={det_efano:.5f}, vary_efano={det_efano_vary:s})""".format(**opts)]

        for peak in ('Elastic', 'Compton1', 'Compton2'):
            t = peak.lower()
            if opts['%s_use'% t]:
                d = {}
                d['_cen']  = opts['%s_cen'%t]
                d['vcen']  = opts['%s_cen_vary'%t]
                d['_step'] = opts['%s_step'%t] * 0.01
                d['vstep'] = opts['%s_step_vary'%t]
                d['_tail'] = opts['%s_tail'%t]
                d['vtail'] = opts['%s_tail_vary'%t]
                d['_gamm'] = opts['%s_gamm'%t]
                d['vgamm'] = opts['%s_gamm_vary'%t]
                d['_sigm'] = opts['%s_sigm'%t]
                d['vsigm'] = opts['%s_sigm_vary'%t]
                s = """amplitude=1e5, center={_cen:.1f}, step={_step:.5f},
    tail={_tail:.5f}, gamma={_gamm:.5f}, sigmax={_sigm:.3f}, vary_center={vcen:s},
    vary_step={vstep:s}, vary_tail={vtail:s},
    vary_sigmax={vsigm:s}, vary_gamma={vgamm:s}""".format(**d)
                script.append("xrfmod.add_scatter_peak(name='%s', %s)" % (t, s))

        for i in range(1, NFILTERS+1):
            t = 'filt%d' % i
            _mat =opts['%s_mat'%t]
            if _mat not in (None, 'None'):
                _thk = opts['%s_thk'%t] / 10.0
                _var = opts['%s_var'%t]
                s = "'%s', %.4f, vary_thickness=%s" % (_mat, _thk, _var)
                script.append("xrfmod.add_filter(%s)" % s)

        # sort elements selected on Periodic Table by Z
        elemz = []
        for elem in self.ptable.selected:
            elemz.append( 1 + self.ptable.syms.index(elem))
        elemz.sort()
        for iz in elemz:
            sym = self.ptable.syms[iz-1]
            script.append("xrfmod.add_element('%s', amplitude=1e5)" % sym)

        self._larch.symtable.set_symbol('work_mca', self.mca)
        en_assign = "work_mca.energy_ev = work_mca.energy[:]"
        if max(self.mca.energy) < 250.0:
            en_str = "work_mca.energy_ev = work_mca.energy*1000.0"
        script.append(en_str)
        script.append("work_mca.xrf_init = xrfmod.calc_spectrum(work_mca.energy_ev)")
        script = '\n'.join(script)
        self._larch.eval(script)
        self.model_script = script

        cmds = []
        self.xrfmod = self._larch.symtable.get_symbol('xrfmod')
        floor = 1.e-12*max(self.mca.counts)
        if match_amplitudes:
            total = 0.0 * self.mca.counts
            for name, parr in self.xrfmod.comps.items():
                nam = name.lower()
                imax = np.where(parr == parr.max())[0][0]
                scale = self.mca.counts[imax] / (parr[imax]+1.e-5)
                ampname = 'amp_%s' % nam
                paramval = self.xrfmod.params[ampname].value
                s = "xrfmod.params['%s'].value = %.1f"
                cmds.append(s % (ampname, paramval * scale))
                parr *= scale
                parr[np.where(parr<floor)] = floor
                total += parr
            self.xrfmod.init_fit = total
            script = '\n'.join(cmds)
            self._larch.eval(script)
            self.model_script = "%s\n%s" % (self.model_script, script)


    def plot_model(self, init=False):

        plotkws = {'linewidth': 2.5,
                   'delay_draw': True,
                   'grid': self.parent.panel.conf.show_grid,
                   'ylog_scale': self.parent.ylog_scale,
                   'show_legend': False,
                   'fullbox': False}

        ppanel = self.parent.panel
        ppanel.conf.reset_trace_properties()

        self.parent.plot(self.mca.energy, self.mca.counts, mca=self.mca,
             xlabel='E (keV)', xmin=0,  **plotkws)

        if init:
            self.parent.oplot(self.mca.energy, self.xrfmod.init_fit,
                  label='predicted model', **plotkws)
        else:
            self.parent.oplot(self.mca.energy, self.xrfmod.best_fit,
                  label='best fit', **plotkws)

        if self.wids['show_components'].IsChecked():
            for label, arr in self.xrfmod.comps.items():
                ppanel.oplot(self.mca.energy, arr, label=label, **plotkws)

        yscale = {False:'linear', True:'log'}[self.parent.ylog_scale]
        ppanel.set_logscale(yscale=yscale)
        ppanel.set_viewlimits()
        ppanel.conf.draw_legend(show=True, delay_draw=False)

    def onShowModel(self, event=None):
        self.build_model()
        self.plot_model(init=True)

    def onFitModel(self, event=None):
        self.build_model()

        emin = self.wids['en_min'].GetValue()
        emax = self.wids['en_max'].GetValue()
        script = """xrfmod.fit_spectrum(work_mca.energy_ev, work_mca.counts,
         energy_min=%.1f, energy_max=%.1f)"""
        script = script % (emin, emax)
        self._larch.eval(script)

        # display report,
        self._larch.eval("print(xrfmod.fit_report)")
        self.plot_model(init=False)


    def onClose(self, event=None):
        self.Destroy()
