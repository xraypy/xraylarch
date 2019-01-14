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

from wxutils import (SimpleText, FloatCtrl, Choice, Font, pack, Button, Check,
                     HLine, GridPanel, RowPanel, CEN, LEFT, RIGHT)

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
EFano_Text = ' Note on Peak Width: sigma = sqrt(e_Fano * Energy + Noise**2) with e_Fano from detector material '

class FitSpectraFrame(wx.Frame):
    """Frame for Spectral Analysis"""

    Filter_Lengths = ['microns', 'mm', 'cm']

    Filter_Materials = ['None', 'air', 'nitrogen', 'helium', 'kapton',
                        'aluminum', 'mylar', 'beryllium', 'diamond',
                        'argon', 'silicon nitride', 'pmma', 'silicon',
                        'quartz', 'sapphire', 'graphite', 'boron nitride']

    def __init__(self, parent, size=(725, 550)):
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

        self.wids = Empty()
        # self.SetFont(Font(10))
        self.panels = OrderedDict()
        self.panels['Beam, Detector, Filters'] = self.beamdet_page
        self.panels['Elements and Peaks'] = self.elempeaks_page
        # self.panels['Filter's] = self.filters_page

        self.nb = flatnotebook(self, self.panels)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)

        sizer.Add((5,5))
        sizer.Add(HLine(self, size=(675, 3)),  0, CEN|LEFT|wx.TOP|wx.GROW)
        sizer.Add((5,5))

        bpanel = RowPanel(self)
        bpanel.Add(Button(bpanel, 'Run Fit', action=self.onFitPeaks), 0, LEFT)
        bpanel.Add(Button(bpanel, 'Done', action=self.onClose), 0, LEFT)
        bpanel.pack()
        sizer.Add(bpanel, 0, CEN)
        pack(self, sizer)
        self.Show()
        self.Raise()

    def elempeaks_page(self, **kws):
        "create row for filters parameters"
        mca = self.parent.mca
        self.wids.peaks = []

        p = GridPanel(self)

        ptable = PeriodicTablePanel(p, multi_select=True, fontsize=12,
                                    tooltip_msg='Select Elements to include in model')

        p.Add(HLine(p, size=(600, 3)), dcol=5, newrow=True)
        p.Add(ptable, dcol=6, newrow=True)
        # offset, slope = self.mca.offset, self.mca.slope
        # for iroi, roi in enumerate(self.mca.rois):
        #     xx = roi
#             try:
#                 cenval, ecen, fwhm, ampval, _x = self.mca.init_calib[roi.name]
#             except KeyError:
#                 continue
#             sigval = 0.4*fwhm
#             mincen = offset + slope*(roi.left  - 4 * roi.bgr_width)
#             maxcen = offset + slope*(roi.right + 4 * roi.bgr_width)
#
#             pname = roi.name.replace(' ', '').lower()
#             ampnam = '%s_amp' % pname
#             cennam = '%s_cen' % pname
#             signam = '%s_sig' % pname
#             sigexpr = "%s + %s*%s +%s*%s**2" % (self.gsig_offset,
#                                                 self.gsig_slope, cennam,
#                                                 self.gsig_quad, cennam)
#
#             p_amp = Parameter(value=ampval, vary=True,    min=0, name=ampnam)
#             p_sig = Parameter(value=sigval, expr=sigexpr, min=0, name=signam)
#             p_cen = Parameter(value=cenval, vary=False, name=cennam,
#                               min=mincen, max=maxcen)
#
#             setattr(self.paramgroup, ampnam, p_amp)
#             setattr(self.paramgroup, cennam, p_cen)
#             setattr(self.paramgroup, signam, p_sig)
#
#             _use   = Check(p, label='use' , default=True)
#             _cen   = ParameterPanel(p, p_cen, precision=3)
#             _sig   = ParameterPanel(p, p_sig, precision=3)
#             _amp   = ParameterPanel(p, p_amp, precision=2)
#
#             self.wids.peaks.append((_use, _cen, _sig, _amp))
#
#             p.AddText(' %s' % roi.name,  newrow=True, style=LEFT)
#             p.Add(_use, style=wx.ALIGN_CENTER)
#             p.Add(_cen)
#             p.Add(_sig)
#             p.Add(_amp)
        p.Add(HLine(p, size=(600, 3)), dcol=5, newrow=True)
        p.pack()
        return p

    def beamdet_page(self, **kws):
        "beam / detector settings"
        mca = self.parent.mca
        conf = self.parent.conf
        wids = self.wids

        width = getattr(mca, 'bgr_width',    5)
        expon = getattr(mca, 'bgr_exponent', 2)

        det_noise = getattr(mca, 'det_noise',  30)
        det_efano = getattr(mca, 'det_efano',  EFano['Si'])

        main = wx.Panel(self)

        p = GridPanel(main, itemstyle=LEFT)
        wids.bgr_use = Check(p, label='Fit Background-Subtracted Spectra',
                             default=True)
        wids.bgr_width = FloatCtrl(p, value=width, minval=0, maxval=10,
                                   precision=1, size=(70, -1))
        wids.bgr_exponent = Choice(p, choices=['2', '4', '6'],
                                   size=(70, -1), default=0)

        wids.det_mat = Choice(p, choices=Detector_Materials,
                              size=(55, -1), default=0, action=self.onDetMaterial)
        wids.det_thk = FloatCtrl(p, value=0.40, size=(70, -1),
                                 minval=0, maxval=100, precision=3)


        wids.det_noise_vary = VarChoice(p, default=1)
        wids.det_efano_vary = VarChoice(p, default=0)

        opts = dict(size=(70, -1), minval=0, maxval=1000, precision=3)
        wids.xray_en = FloatCtrl(p, value=20.0, **opts)
        wids.fit_emin = FloatCtrl(p, value=conf.e_min, **opts)
        wids.fit_emax = FloatCtrl(p, value=conf.e_max, **opts)

        opts['precision'] = 4
        opts.pop('maxval')
        wids.det_noise = FloatCtrl(p, value=det_noise, maxval=500, **opts)
        wids.det_efano = FloatCtrl(p, value=det_efano, maxval=1, **opts)
        wids.filters = []

        p.AddText(' Beam Energy :', colour='#880000', dcol=3)
        p.AddText(' X-ray Energy (keV): ', newrow=True)
        p.Add(wids.xray_en)
        p.AddText(' Min Energy (keV): ')
        p.Add(wids.fit_emin)
        p.AddText(' Max Energy (keV): ')
        p.Add(wids.fit_emax)

        p.Add(HLine(p, size=(600, 3)), dcol=6, newrow=True)
        p.AddText(' Detector :', colour='#880000', dcol=3, newrow=True)
        p.AddText(' Detector Material:  ', newrow=True)
        p.Add(wids.det_mat)
        p.AddText(' Thickness (mm): ', newrow=False)
        p.Add(wids.det_thk)

        p.AddText(' Det Noise (eV): ', newrow=True)
        p.Add(wids.det_noise)
        p.Add(wids.det_noise_vary)
        p.AddText(' Detector e_Fano (eV): ')
        p.Add(wids.det_efano)
        p.Add(wids.det_efano_vary)
        p.AddText(EFano_Text, newrow=True,  dcol=6)
        p.Add(HLine(p, size=(600, 3)), dcol=6, newrow=True)

        p.AddText(" Background Parameters: ", colour='#880000', dcol=2,
                  newrow=True)
        p.Add(wids.bgr_use, dcol=2)

        p.AddText(" Exponent:", newrow=True)
        p.Add(wids.bgr_exponent)
        p.AddText(" Energy Width (keV): ", newrow=False)
        p.Add(wids.bgr_width)

        p.Add(Button(p, 'Show Background', size=(130, -1),
                     action=self.onShowBgr), dcol=2)

        p.Add(HLine(p, size=(600, 3)), dcol=6, newrow=True)
        p.pack()

        # filters section
        fp = GridPanel(main, itemstyle=LEFT)
        bx = Button(fp, 'Customize Filter List', size=(150, -1),
                    action = self.onEditFilters)
        bx.Disable()
        fp.AddText(' Filters :', colour='#880000', dcol=3, newrow=True)
        fp.Add(bx, dcol=3)
        fp.AddManyText((' filter', 'material', 'density (gr/cm^3)',
                        'thickness (mm)'), style=CEN, newrow=True)
        fp.Add(HLine(fp, size=(600, 3)), dcol=6, newrow=True)
        for i in range(4):
            _mat = Choice(fp, choices=self.Filter_Materials, default=0,
                          size=(125, -1),
                          action=partial(self.onFilterMaterial, index=i))
            _den = FloatCtrl(fp, value=0, minval=0, maxval=30,
                             precision=4, size=(75, -1))
            pnam = 'filter%i_thickness' % (i+1)
            param = Parameter(value=0.0, vary=False, min=0, name=pnam)
            setattr(self.paramgroup, pnam, param)
            _len  = ParameterPanel(fp, param, precision=4)
            self.wids.filters.append((_mat, _den, _len))
            fp.AddText('  %i ' % (i+1), newrow=True)
            fp.Add(_mat)
            fp.Add(_den, style=wx.ALIGN_CENTER)
            fp.Add(_len)
        fp.pack()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(p)
        sizer.Add(fp)
        pack(main, sizer)
        return main

    def onDetMaterial(self, event=None):
        det_mat = self.wids.det_mat.GetStringSelection()
        if det_mat not in EFano:
            det_mat = 'Si'
        self.wids.det_efano.SetValue(EFano[det_mat])


    def onShowBgr(self, event=None):
        wids     = self.wids
        mca      = self.mca
        parent   = self.parent
        width    = wids.bgr_width.GetValue()
        exponent = int(wids.bgr_exponent.GetStringSelection())

        xrf_background(energy=mca.energy, counts=mca.counts, group=mca,
                       width=width, exponent=exponent, _larch=parent.larch)

        mca.bgr_width = width
        mca.bgr_exponent = exponent
        parent.plotmca(mca)
        parent.oplot(mca.energy, mca.bgr, label='background',
                     color=parent.conf.bgr_color, linewidth=1, style='--')

    def onFilterMaterial(self, evt=None, index=0):
        name = evt.GetString()
        form, den = self.parent.filters_data.get(name, ('', 0))
        self.wids.filters[index][1].SetValue(den)
        thick = self.wids.filters[index][2]
        if thick.wids.val.GetValue()  < 1.e-5:
            thick.wids.val.SetValue(0.0250)

    def onEditFilters(self, evt=None):
        print( 'on Edit Filters ',  evt)


    def filters_page(self):
        "create row for filters parameters"
        mca = self.parent.mca
        self.wids.filters = []

        p = GridPanel(self, itemstyle=LEFT)

        bx = Button(p, 'Customize Filter List', size=(150, -1),
                    action = self.onEditFilters)
        bx.Disable()
        p.AddManyText((' filter', 'material', 'density (gr/cm^3)',
                       'thickness (mm)'), style=CEN)
        p.Add(HLine(p, size=(600, 3)), dcol=6, newrow=True)
        for i in range(4):
            _mat = Choice(p, choices=self.Filter_Materials, default=0,
                          size=(125, -1),
                          action=partial(self.onFilterMaterial, index=i))
            _den = FloatCtrl(p, value=0, minval=0, maxval=30,
                             precision=4, size=(75, -1))

            pnam = 'filter%i_thickness' % (i+1)
            param = Parameter(value=0.0, vary=False, min=0, name=pnam)
            setattr(self.paramgroup, pnam, param)
            _len  = ParameterPanel(p, param, precision=4)

            self.wids.filters.append((_mat, _den, _len))
            p.AddText('  %i ' % (i+1), newrow=True)
            p.Add(_mat)
            p.Add(_den, style=wx.ALIGN_CENTER)
            p.Add(_len)
        p.Add(HLine(p, size=(600, 3)), dcol=5, newrow=True)
        p.AddText(' ', newrow=True)
        p.Add(bx, dcol=3)

        p.pack()
        return p

    def onFitPeaks(self, event=None):
        opts = {}
        filters, peaks = [], []
        sig, det, bgr = {}, {}, {}

        opts['flyield']  = self.wids.flyield_use.IsChecked()
        opts['xray_en']  = self.wids.xray_en.GetValue()
        opts['emin']     = self.wids.fit_emin.GetValue()
        opts['emax']     = self.wids.fit_emax.GetValue()

        det['use']       = self.wids.det_use.IsChecked()
        det['thickness'] = self.wids.det_thk.GetValue()
        det['material']  = self.wids.det_mat.GetStringSelection()

        bgr['use']       = self.wids.bgr_use.IsChecked()
        bgr['width']     = self.wids.bgr_width.GetValue()
        bgr['exponent']  = int(self.wids.bgr_exponent.GetStringSelection())

        sig['offset']    = self.wids.sig_offset.param
        sig['slope']     = self.wids.sig_slope.param
        sig['quad']      = self.wids.sig_quad.param

        for k in self.wids.filters:
            f = (k[0].GetStringSelection(), k[1].GetValue(), k[2].param)
            filters.append(f)

        for k in self.wids.peaks:
            use = k[0].IsChecked()
            p = (k[0].IsChecked(), k[1].param, k[2].param, k[3].param)
            peaks.append(p)
            if not use:
                k[1].param.vary = False
                k[2].param.vary = False
                k[3].param.vary = False

        opts['det'] = det
        opts['bgr'] = bgr
        opts['sig'] = sig
        opts['filters'] = filters
        opts['peaks'] = peaks

        mca    = self.mca
        mca.data = mca.counts*1.0
        energy = mca.energy
        _larch = self.parent.larch
        if bgr['use']:
            bgr.pop('use')
            xrf_background(energy=mca.energy, counts=mca.counts,
                           group=mca, _larch=_larch, **bgr)
            opts['use_bgr']=True
        opts['mca'] = mca
        if det['use']:
            mu = material_mu(det['material'], energy*1000.0,
                             _larch=_larch)/10.0
            t = det['thickness']
            mca.det_atten = np.exp(-t*mu)

        fit = Minimizer(xrf_resid, self.paramgroup, toler=1.e-4,
                        _larch=_larch, fcn_kws = opts)
        fit.leastsq()
        parent = self.parent
        parent.oplot(mca.energy, mca.model,
                     label='fit', style='solid',
                     color='#DD33DD')

        # print( fitting.fit_report(self.paramgroup, _larch=_larch))

        # filters:
        #  75 microns kapton, etc
        #
        # form, nominal_density = material_get(material)
        # mu = material_mu(material, energy*1000.0, _larch=_larch)/10.0
        # mu = mu * nominal_density/user_density
        # scale = exp(-thickness*mu)


    def onClose(self, event=None):
        self.Destroy()
