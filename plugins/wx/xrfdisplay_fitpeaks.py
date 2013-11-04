#!/usr/bin/env python
"""
utilities for XRF display
"""
import copy
from functools import partial

import wx
import wx.lib.agw.pycollapsiblepane as CP
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled

from wxutils import (SimpleText, FloatCtrl, Choice, Font, pack, Button,
                     Check, HLine, GridPanel, RowPanel, CEN, LEFT, RIGHT)

from larch import use_plugin_path, Group, Parameter
from larch.larchlib import Empty
use_plugin_path('xrf')

from xrf_bgr import xrf_background
from xrf_calib import xrf_calib_fitrois, xrf_calib_compute, xrf_calib_apply
from parameter import ParameterPanel
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


class FitSpectraFrame(wx.Frame):
    """Frame for Spectral Analysis"""

    Filter_Lengths = ['microns', 'mm', 'cm']
    Filter_Materials = ['None', 'air', 'nitrogen', 'helium', 'argon', 'kapton',
                        'mylar', 'pmma', 'water', 'aluminum', 'silicon nitride',
                        'silicon', 'quartz', 'sapphire', 'diamond', 'graphite',
                        'boron nitride']

    Detector_Materials = ['Si', 'Ge']

    gsig_offset = '_sigma_off'
    gsig_slope  = '_sigma_slope'
    gsig_quad   = '_sigma_quad'

    def __init__(self, parent, size=(675, 525)):
        self.parent = parent
        self.larch = parent._larch
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

        sizer.Add(Button(self, 'Done',
                         size=(80, -1), action=self.onClose), 0, CEN)
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
            cenval, ecen, fwhm, ampval, xfit = self.mca.init_calib[roi.name]
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

            _use   = Check(p, default=True)
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

        width = getattr(mca, 'bgr_width', 2.5)
        compr = getattr(mca, 'bgr_compress', 2)
        expon = getattr(mca, 'bgr_exponent', 2.5)

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
        sig_offset = Parameter(value=0.050, name=self.gsig_offset, **sopts)
        sig_slope  = Parameter(value=0.005, name=self.gsig_slope, **sopts)
        sig_quad   = Parameter(value=0.000, name=self.gsig_quad, **sopts)

        setattr(self.paramgroup, self.gsig_offset, sig_offset)
        setattr(self.paramgroup, self.gsig_slope, sig_slope)
        setattr(self.paramgroup, self.gsig_quad,  sig_quad)

        wids.sig_offset = ParameterPanel(p, sig_offset, **sopts)
        wids.sig_slope  = ParameterPanel(p, sig_slope, **sopts)
        wids.sig_quad   = ParameterPanel(p, sig_quad, **sopts)

        # row1 = RowPanel(p)

        wids.xray_en = FloatCtrl(p, value=20.0, size=(70, -1),
                                 minval=0, maxval=1000, precision=3)

        wids.fit_emin = FloatCtrl(p, value=conf.e_min, size=(70, -1),
                                  minval=0, maxval=1000, precision=3)
        wids.fit_emax = FloatCtrl(p, value=conf.e_max, size=(70, -1),
                                  minval=0, maxval=1000, precision=3)
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


        p.AddText(' Detector Material:  ', newrow=True)
        p.Add(wids.det_mat)
        p.AddText(' Thickness (mm): ', newrow=False)
        p.Add(wids.det_thk)

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
                     color=parent.conf.bgr_color)


    def onFilterMaterial(self, evt=None, index=0):
        name = evt.GetString()
        form, den = self.parent.filters_data.get(name, ('', 0))
        self.wids.filters[index][1].SetValue(den)
        thick = self.wids.filters[index][2]
        if thick.wids.val.GetValue()  < 1.e-5:
            thick.wids.val.SetValue(0.0250)

    def onEditFilters(self, evt=None):
        print 'on Edit Filters ',  evt


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

    def onClose(self, event=None):
        self.Destroy()



    def createpanel_bgr_withcollapse(self, panel):
        "create row for background settings"
        mca = self.parent.mca
        width = getattr(mca, 'bgr_width', 2.5)
        compr = getattr(mca, 'bgr_compress', 2)
        expon = getattr(mca, 'bgr_exponent', 2.5)

        label = 'Background Parameters  '
        cpane = wx.CollapsiblePane(panel,
                                   style=wx.CP_DEFAULT_STYLE|wx.CP_NO_TLW_RESIZE)

        cpane.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED,
                   partial(self.onCollapse, panel=cpane, label=label))
        cpane.Collapse(True)
        cpane.SetLabel('Hide %s' % label)

        container = cpane.GetPane()
        p = GridPanel(container)
        self.wids.bgr_use = Check(p, label='Include Background',
                                  default=True)
        self.wids.bgr_width = FloatCtrl(p, value=width, minval=0,
                                        maxval=10,
                                        precision=1, size=(50, -1))

        self.wids.bgr_compress = Choice(p, choices=['1', '2', '4', '8', '16'],
                                        size=(50, -1), default=1)

        self.wids.bgr_exponent = Choice(p, choices=['2', '4', '6'],
                                        size=(50, -1), default=0)

        p.AddText(" Compression: ", newrow=True)
        p.Add(self.wids.bgr_compress)
        p.AddText(" Exponent:")
        p.Add(self.wids.bgr_exponent)
        p.AddText(" Energy Width: ")
        p.Add(self.wids.bgr_width)
        p.AddText(" (keV)")
        p.Add(Button(p, 'Show Background',
                     size=(130, -1), action=self.onShowBgr), dcol=2, newrow=True)
        p.Add(self.wids.bgr_use, dcol=4)

        p.pack()
        s = wx.BoxSizer(wx.HORIZONTAL)
        s.Add(p, 1, wx.EXPAND|wx.ALL|CEN, 3)
        pack(container, s)
        return cpane

    def onCollapse(self, evt=None, panel=None, label=''):
        if panel is None:
            return
        txt = 'Show'
        if panel.IsExpanded():
            txt = 'Hide'
        panel.SetLabel('%s %s' % (txt, label))
        self.Layout()
        self.Refresh()
