#!/usr/bin/env python
"""
utilities for XRF display
"""
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

from larch import Group, Parameter, Minimizer, fitting
from larch.larchlib import Empty
from larch.utils import index_of, gaussian
from larch.wxlib import flatnotebook

from larch_plugins.xrf import (xrf_background, xrf_calib_fitrois,
                               xrf_calib_compute, xrf_calib_apply)

from larch_plugins.xray import material_mu, material_get
from larch_plugins.wx import ParameterPanel
from larch_plugins.wx.periodictable import PeriodicTablePanel

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

    def __init__(self, parent, size=(550, 625)):
        self.parent = parent
        self.larch = parent.larch
        self.mca = parent.mca
        self.conf = {}

        self.paramgroup = Group()

        wx.Frame.__init__(self, parent, -1, 'Fit XRF Spectra',
                          size=size, style=wx.DEFAULT_FRAME_STYLE)

        if not hasattr(self.parent, 'filters_data'):
            self.parent.filters_data = read_filterdata(self.Filter_Materials,
                                                       _larch=self.larch)

        self.wids = {}
        # self.SetFont(Font(10))
        self.panels = OrderedDict()
        self.panels['Beam, Detector, Filters'] = self.beamdet_page
        self.panels['Elements and Peaks'] = self.elempeaks_page

        self.nb = flatnotebook(self, self.panels)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)

        bpanel = RowPanel(self)
        bpanel.Add(Button(bpanel, 'Run Fit', action=self.onFitPeaks), 0, LEFT)
        bpanel.pack()
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
        self.ptable = PeriodicTablePanel(p, multi_select=True, fontsize=12,
                                         tooltip_msg=tooltip_msg,
                                         onselect=self.onElemSelect)

        for roi in self.mca.rois:
            words = roi.name.split()
            elem = words[0].title()
            if elem in self.ptable.syms and elem not in self.ptable.selected:
                self.ptable.onclick(label=elem)

        p.AddText(' Select Elements to include :', colour='#880000', dcol=7)
        p.Add(self.ptable, dcol=6, newrow=True)

        p.Add(HLine(p, size=(550, 3)), dcol=8, newrow=True)
        p.AddText(' Elastic / Compton peaks: ', colour='#880000',
                  dcol=5, newrow=True)

        opts = dict(size=(100, -1),
                    min_val=0, digits=4, increment=0.010)
        for name, def_use  in (('Elastic', True), ('Compton1', True),
                               ('Compton2', False)):
            en = self.mca.incident_energy
            if name == 'Compton1':
                en = 0.96 * self.mca.incident_energy
            elif name == 'Compton2':
                en = 0.92 * self.mca.incident_energy
            t = name.lower()
            wids['%s_use'%t] = Check(p, label='Include in fit',
                                      default=def_use,
                                      action=partial(self.onUsePeak, name=t))
            wids['%s_show'%t] = Button(p, 'Show Peak', size=(150, -1),
                                       action=partial(self.onShowPeak, name=t))
            wids['%s_cen_vary'%t] = VarChoice(p, default=1)
            wids['%s_step_vary'%t] = VarChoice(p, default=0)
            wids['%s_tail_vary'%t] = VarChoice(p, default=0)
            wids['%s_sigm_vary'%t] = VarChoice(p, default=0)

            wids['%s_cen'%t]  = FloatSpin(p, value=en, digits=1, min_val=0,
                                           increment=10)
            wids['%s_step'%t] = FloatSpin(p, value=0.01, digits=3, min_val=0,
                                           max_val=1.0, increment=1.e-2)
            wids['%s_tail'%t] = FloatSpin(p, value=0.010, digits=3, min_val=0,
                                           max_val=3.0, increment=1.e-3)
            wids['%s_sigm'%t] = FloatSpin(p, value=2.0, digits=2, min_val=0,
                                           max_val=5.0, increment=0.1)
            if not def_use:
                self.onUsePeak(name=t, value=False)

            p.AddText("  %s " % name,  colour='#880000', newrow=True)
            p.Add(wids['%s_use' % t], dcol=3)
            p.Add(wids['%s_show' % t], dcol=3)
            p.AddText('  Energy (keV): ', newrow=True)
            p.Add(wids['%s_cen'%t])
            p.Add(wids['%s_cen_vary'%t])
            p.AddText('  Tail (%): ', newrow=False)
            p.Add(wids['%s_tail'%t])
            p.Add(wids['%s_tail_vary'%t])
            p.AddText('  Step : ', newrow=True)
            p.Add(wids['%s_step'%t])
            p.Add(wids['%s_step_vary'%t])
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
            xray_energy = mca.incident_energy = 20.0
        if xray_energy < 250:
            xray_energy = 1000.0 * xray_energy

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
                    digits=1, increment=0.010)
        wids['xray_en'] = FloatSpin(pdet, value=xray_energy, **opts)
        wids['fit_emin'] = FloatSpin(pdet, value=en_min, **opts)
        wids['fit_emax'] = FloatSpin(pdet, value=en_max, **opts)

        opts.update({'digits': 4, 'max_val': 500, 'increment': 1})
        wids['det_noise'] = FloatSpin(pdet, value=det_noise, **opts)

        opts.update({'max_val': 1, 'increment': 0.001})
        wids['det_efano'] = FloatSpin(pdet, value=det_efano, **opts)


        pdet.AddText(' Beam Energy, Fit Range :', colour='#880000', dcol=3)
        pdet.AddText('    X-ray Energy (eV): ', newrow=True)
        pdet.Add(wids['xray_en'])
        pdet.AddText('    Fit Range (eV): ', newrow=True)
        pdet.Add(wids['fit_emin'])
        pdet.AddText(' : ')
        pdet.Add(wids['fit_emax'])

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
        pflt.AddManyText(('    filter', 'material', 'density (gr/cm^3)',
                        'thickness (mm)', 'vary thickness'), style=CEN, newrow=True)
        opts = dict(size=(100, -1), min_val=0, digits=3, increment=0.010)
        for i in range(1, 5):
            t = 'filt%d' % i
            wids['%s_mat'%t] = Choice(pflt, choices=self.Filter_Materials, default=0,
                                      size=(125, -1),
                                      action=partial(self.onFilterMaterial, index=i))
            wids['%s_den'%t] = FloatCtrl(pflt, value=0, minval=0, maxval=30,
                                         precision=5, size=(100, -1))
            wids['%s_thk'%t] = FloatSpin(pflt, value=0.0, **opts)
            wids['%s_var'%t] = VarChoice(pflt, default=0)

            pflt.AddText('     %i' % (i), newrow=True)
            pflt.Add(wids['%s_mat' % t])
            pflt.Add(wids['%s_den' % t])
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
        width  = self.wids['bgr_width'].GetValue()
        expon  = int(self.wids['bgr_expon'].GetStringSelection())

        xrf_background(energy=mca.energy, counts=mca.counts, group=mca,
                       width=width, exponent=expon, _larch=parent.larch)

        mca.bgr_width = width
        mca.bgr_expoent = expon
        parent.plotmca(mca)
        parent.oplot(mca.energy, mca.bgr, label='background',
                     color=parent.conf.bgr_color, linewidth=1, style='--')

    def onDetMaterial(self, event=None):
        det_mat = self.wids['det_mat'].GetStringSelection()
        if det_mat not in EFano:
            det_mat = 'Si'
        self.wids['det_efano'].SetValue(EFano[det_mat])

    def onFilterMaterial(self, evt=None, index=0):
        name = evt.GetString()
        form, den = self.parent.filters_data.get(name, ('', 0))
        t = 'filt%d' % index
        self.wids['%s_den'%t].SetValue(den)
        thick = self.wids['%s_thk'%t]
        if den < 0.1 and thick.GetValue() < 0.1:
            thick.SetValue(5.0)
        elif den > 0.1 and thick.GetValue() < 1.e-5:
            thick.SetValue(0.0250)

    def onEditFilters(self, evt=None):
        print( 'on Edit Filters ',  evt)

    def onElemSelect(self, event=None, elem=None):
        # print('elem select ', event, elem, elem in self.ptable.selected)
        self.ptable.tsym.SetLabel('')
        self.ptable.title.SetLabel('%d elements selected' % len(self.ptable.selected))


    def onShowPeak(self, event=None, name=None):
        print('show peak ', name)
        opts = {}
        for a in ('cen', 'step', 'tail', 'sigm'):
            v = self.wids['%s_%s'%(name, a)].GetValue()
            opts[a] = v
        print(opts)


    def onUsePeak(self, event=None, name=None, value=None):
        if value is None and event is not None:
            value = event.IsChecked()
        if name is None:
            return
        for a in ('show', 'cen', 'step', 'tail', 'sigm'):
            self.wids['%s_%s'%(name, a)].Enable(value)
            varwid = self.wids.get('%s_%s_vary'%(name, a), None)
            if varwid is not None:
                varwid.Enable(value)



    def build_model(self):
        """build xrf_model from form settings"""

        opts = {}
        filters, peaks = [], []
        sig, det, bgr = {}, {}, {}

        print("on Fit " , self.mca)
        print(self.ptable.selected)

        print(list(self.wids.keys()))


    def onFitPeaks(self, event=None):
        opts = {}
        filters, peaks = [], []
        sig, det, bgr = {}, {}, {}

        print("on Fit " , self.mca)
        print(self.ptable.selected)

        print(list(self.wids.keys()))


#         opts['xray_en']  = self.wids.xray_en.GetValue()
#         opts['emin']     = self.wids.fit_emin.GetValue()
#         opts['emax']     = self.wids.fit_emax.GetValue()
#
#         det['use']       = self.wids.det_use.IsChecked()
#         det['thickness'] = self.wids.det_thk.GetValue()
#         det['material']  = self.wids.det_mat.GetStringSelection()
#
#         bgr['use']       = self.wids.bgr_use.IsChecked()
#         bgr['width']     = self.wids.bgr_width.GetValue()
#         bgr['exponent']  = int(self.wids.bgr_expon.GetStringSelection())
#
#
#         mca    = self.mca
#         mca.data = mca.counts*1.0
#         energy = mca.energy
#         _larch = self.parent.larch
#         if bgr['use']:
#             bgr.pop('use')
#             xrf_background(energy=mca.energy, counts=mca.counts,
#                            group=mca, _larch=_larch, **bgr)
#             opts['use_bgr']=True
#         opts['mca'] = mca
#         if det['use']:
#             mu = material_mu(det['material'], energy*1000.0,
#                              _larch=_larch)/10.0
#             t = det['thickness']
#             mca.det_atten = np.exp(-t*mu)
#
#         fit = Minimizer(xrf_resid, self.paramgroup, toler=1.e-4,
#                         _larch=_larch, fcn_kws = opts)
#         fit.leastsq()
#         parent = self.parent
#         parent.oplot(mca.energy, mca.model,
#                      label='fit', style='solid',
#                      color='#DD33DD')

    def onClose(self, event=None):
        self.Destroy()
