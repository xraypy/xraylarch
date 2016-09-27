#!/usr/bin/env python
"""
utilities for XRF display
"""
import copy
from functools import partial
import numpy as np
import wx
import wx.lib.agw.pycollapsiblepane as CP
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled

from wxutils import (SimpleText, FloatCtrl, Choice, Font, pack, Button,
                     Check, HLine, GridPanel, RowPanel, CEN, LEFT, RIGHT)

from larch import Group, Parameter, Minimizer, fitting
from larch.larchlib import Empty
from larch_plugins.math import index_of, gaussian

from larch_plugins.xrf import (xrf_background, xrf_calib_fitrois,
                               xrf_calib_compute, xrf_calib_apply)

from larch_plugins.xray import material_mu, material_get
from larch_plugins.wx import ParameterPanel

try:
    from collections import OrderedDict
except ImportError:
    from larch.utils import OrderedDict

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

def read_filterdata(flist, _larch):
    """ read filters data"""
    materials = _larch.symtable.get_symbol('_xray._materials')
    out = OrderedDict()
    out['None'] = ('', 0)
    for name in flist:
        if name in materials:
            out[name]  = materials[name]
    return out


def xrf_resid(pars, peaks=None, mca=None, det=None, bgr=None,
              sig=None, filters=None, flyield=None, use_bgr=False,
              xray_en=30.0, emin=0.0, emax=30.0, **kws):

    sig_o = pars.sig_o.value
    sig_s = pars.sig_s.value
    sig_q = pars.sig_q.value
    model = mca.data * 0.0
    if use_bgr:
        model += mca.bgr
    for use, pcen, psig, pamp in peaks:
        amp = pamp.value
        cen = pcen.value
        sig = sig_o + cen * (sig_s + sig_q * cen)
        psig.value = sig
        if use: model += amp*gaussian(mca.energy, cen, sig)

    mca.model = model
    imin = index_of(mca.energy, emin)
    imax = index_of(mca.energy, emax)
    resid = (mca.data - model)
    # if det['use']:
    #     resid = resid / np.maximum(1.e-29, (1.0 - mca.det_atten))

    return resid[imin:imax]


class FitSpectraFrame(wx.Frame):
    """Frame for Spectral Analysis"""

    Filter_Lengths = ['microns', 'mm', 'cm']
    Filter_Materials = ['None', 'air', 'nitrogen', 'helium', 'argon', 'kapton',
                        'mylar', 'pmma', 'water', 'aluminum', 'silicon nitride',
                        'silicon', 'quartz', 'sapphire', 'diamond', 'graphite',
                        'boron nitride']

    Detector_Materials = ['Si', 'Ge']

    gsig_offset = 'sig_o'
    gsig_slope  = 'sig_s'
    gsig_quad   = 'sig_q'

    def __init__(self, parent, size=(675, 525)):
        self.parent = parent
        self.larch = parent.larch
        self.mca = parent.mca
        conf = parent.conf
        self.paramgroup = Group()

        if not hasattr(self.mca, 'init_calib'):
            xrf_calib_fitrois(self.mca, _larch=self.larch)

        wx.Frame.__init__(self, parent, -1, 'Fit XRF Spectra',
                          size=size, style=wx.DEFAULT_FRAME_STYLE)
        if not hasattr(self.parent, 'filters_data'):
            self.parent.filters_data = read_filterdata(self.Filter_Materials,
                                                       _larch=self.larch)

        self.wids = Empty()
        self.SetFont(Font(9))
        self.panels = {}
        self.nb = flat_nb.FlatNotebook(self, wx.ID_ANY, agwStyle=FNB_STYLE)
        self.nb.SetBackgroundColour('#FBFBF8')
        self.SetBackgroundColour('#F6F6F0')

        self.nb.AddPage(self.settings_page(), 'Fit & Background Settings')
        self.nb.AddPage(self.filters_page(),  'Filters and Attenuation')
        self.nb.AddPage(self.fitpeaks_page(), 'XRF Peaks')

        self.nb.SetSelection(0)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)

        sizer.Add((5,5))
        sizer.Add(HLine(self, size=(675, 3)),  0, CEN|LEFT|wx.TOP|wx.GROW)
        sizer.Add((5,5))

        bpanel = RowPanel(self)
        bpanel.Add(Button(bpanel, 'Fit Peaks', action=self.onFitPeaks), 0, LEFT)
        bpanel.Add(Button(bpanel, 'Done', action=self.onClose), 0, LEFT)
        bpanel.pack()
        sizer.Add(bpanel, 0, CEN)
        pack(self, sizer)
        self.Show()
        self.Raise()

    def fitpeaks_page(self):
        "create row for filters parameters"
        mca = self.parent.mca
        self.wids.peaks = []

        p = GridPanel(self)

        p.AddManyText((' ROI Name', 'Fit?', 'Center', 'Sigma', 'Amplitude'),
                      style=CEN)
        p.Add(HLine(p, size=(600, 3)), dcol=5, newrow=True)
        offset, slope = self.mca.offset, self.mca.slope
        for iroi, roi in enumerate(self.mca.rois):
            try:
                cenval, ecen, fwhm, ampval, _x = self.mca.init_calib[roi.name]
            except KeyError:
                continue
            sigval = 0.4*fwhm
            mincen = offset + slope*(roi.left  - 4 * roi.bgr_width)
            maxcen = offset + slope*(roi.right + 4 * roi.bgr_width)

            pname = roi.name.replace(' ', '').lower()
            ampnam = '%s_amp' % pname
            cennam = '%s_cen' % pname
            signam = '%s_sig' % pname
            sigexpr = "%s + %s*%s +%s*%s**2" % (self.gsig_offset,
                                                self.gsig_slope, cennam,
                                                self.gsig_quad, cennam)

            p_amp = Parameter(value=ampval, vary=True,    min=0, name=ampnam)
            p_sig = Parameter(value=sigval, expr=sigexpr, min=0, name=signam)
            p_cen = Parameter(value=cenval, vary=False, name=cennam,
                              min=mincen, max=maxcen)

            setattr(self.paramgroup, ampnam, p_amp)
            setattr(self.paramgroup, cennam, p_cen)
            setattr(self.paramgroup, signam, p_sig)

            _use   = Check(p, label='use' , default=True)
            _cen   = ParameterPanel(p, p_cen, precision=3)
            _sig   = ParameterPanel(p, p_sig, precision=3)
            _amp   = ParameterPanel(p, p_amp, precision=2)

            self.wids.peaks.append((_use, _cen, _sig, _amp))

            p.AddText(' %s' % roi.name,  newrow=True, style=LEFT)
            p.Add(_use, style=wx.ALIGN_CENTER)
            p.Add(_cen)
            p.Add(_sig)
            p.Add(_amp)
        p.Add(HLine(p, size=(600, 3)), dcol=5, newrow=True)
        p.pack()
        return p

    def settings_page(self):
        "create fit and background settings"
        mca = self.parent.mca
        conf = self.parent.conf
        wids = self.wids

        width = getattr(mca, 'bgr_width',    4)
        compr = getattr(mca, 'bgr_compress', 2)
        expon = getattr(mca, 'bgr_exponent', 2)

        p = GridPanel(self, itemstyle=LEFT)
        wids.bgr_use = Check(p, label='Fit Background-Subtracted Spectra',
                             default=True)
        wids.bgr_width = FloatCtrl(p, value=width, minval=0, maxval=10,
                                   precision=1, size=(70, -1))
        wids.bgr_compress = Choice(p, choices=['1', '2', '4', '8', '16'],
                                   size=(70, -1), default=1)
        wids.bgr_exponent = Choice(p, choices=['2', '4', '6'],
                                   size=(70, -1), default=0)

        sopts = {'vary': True, 'precision': 5}
        sig_offset = Parameter(value=0.050, name=self.gsig_offset, vary=True)
        sig_slope  = Parameter(value=0.005, name=self.gsig_slope, vary=True)
        sig_quad   = Parameter(value=0.000, name=self.gsig_quad, vary=False)

        setattr(self.paramgroup, self.gsig_offset, sig_offset)
        setattr(self.paramgroup, self.gsig_slope, sig_slope)
        setattr(self.paramgroup, self.gsig_quad,  sig_quad)

        wids.sig_offset = ParameterPanel(p, sig_offset, vary=True, precision=5)
        wids.sig_slope  = ParameterPanel(p, sig_slope, vary=True, precision=5)
        wids.sig_quad   = ParameterPanel(p, sig_quad, vary=False, precision=5)

        wids.xray_en = FloatCtrl(p, value=20.0, size=(70, -1),
                                 minval=0, maxval=1000, precision=3)

        wids.fit_emin = FloatCtrl(p, value=conf.e_min, size=(70, -1),
                                  minval=0, maxval=1000, precision=3)
        wids.fit_emax = FloatCtrl(p, value=conf.e_max, size=(70, -1),
                                  minval=0, maxval=1000, precision=3)
        wids.flyield_use = Check(p,
            label='Account for Absorption, Fluorescence Efficiency')

        p.AddText(' General Settings ', colour='#880000', dcol=3)

        p.AddText(' X-ray Energy (keV): ', newrow=True)
        p.Add(wids.xray_en)
        p.AddText(' Min Energy (keV): ', newrow=True)
        p.Add(wids.fit_emin)
        p.AddText(' Max Energy (keV): ', newrow=False)
        p.Add(wids.fit_emax)

        wids.det_mat = Choice(p, choices=self.Detector_Materials,
                              size=(55, -1), default=0)
        wids.det_thk = FloatCtrl(p, value=0.40, size=(70, -1),
                                 minval=0, maxval=100, precision=3)
        wids.det_use = Check(p, label='Account for Detector Thickness')

        p.AddText(' Detector Material:  ', newrow=True)
        p.Add(wids.det_mat)
        p.AddText(' Thickness (mm): ', newrow=False)
        p.Add(wids.det_thk)
        p.Add(wids.det_use,     dcol=4, newrow=True)
        p.Add(wids.flyield_use, dcol=4, newrow=True)

        p.Add(HLine(p, size=(600, 3)), dcol=5, newrow=True)

        p.AddText(' Energy Dependence of Peak Width:',
                  colour='#880000', newrow=True, dcol=2)
        # p.AddText(' ', newrow=True)
        p.AddText(' sigma = offset + slope * Energy + quad * Energy^2 (keV)',
                  dcol=3)
        p.AddText(' Offset: ', newrow=True)
        p.Add(wids.sig_offset, dcol=3)
        p.AddText(' Slope: ', newrow=True)
        p.Add(wids.sig_slope, dcol=3)
        p.AddText(' Quad: ', newrow=True)
        p.Add(wids.sig_quad, dcol=3)
        p.Add(HLine(p, size=(600, 3)), dcol=5, newrow=True)

        p.AddText(" Background Parameters: ", colour='#880000', dcol=2,
                  newrow=True)
        p.Add(wids.bgr_use, dcol=2)

        p.AddText(" Exponent:", newrow=True)
        p.Add(wids.bgr_exponent)
        p.AddText(" Energy Width (keV): ", newrow=False)
        p.Add(wids.bgr_width)

        p.AddText(" Compression: ", newrow=True)
        p.Add(wids.bgr_compress)
        p.Add(Button(p, 'Show Background', size=(130, -1),
                     action=self.onShowBgr), dcol=2)

        p.Add(HLine(p, size=(600, 3)), dcol=5, newrow=True)
        p.pack()
        return p

    def onShowBgr(self, event=None):
        wids     = self.wids
        mca      = self.mca
        parent   = self.parent
        width    = wids.bgr_width.GetValue()
        compress = int(wids.bgr_compress.GetStringSelection())
        exponent = int(wids.bgr_exponent.GetStringSelection())
        xrf_background(energy=mca.energy, counts=mca.counts,
                       group=mca, width=width, compress=compress,
                       exponent=exponent, _larch=parent.larch)
        mca.bgr_width = width
        mca.bgr_compress = compress
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
        p.Add(HLine(p, size=(600, 3)), dcol=5, newrow=True)
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
        bgr['compress']  = int(self.wids.bgr_compress.GetStringSelection())
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

        print( fitting.fit_report(self.paramgroup, _larch=_larch))

        # filters:
        #  75 microns kapton, etc
        #
        # form, nominal_density = material_get(material)
        # mu = material_mu(material, energy*1000.0, _larch=_larch)/10.0
        # mu = mu * nominal_density/user_density
        # scale = exp(-thickness*mu)


    def onClose(self, event=None):
        self.Destroy()
