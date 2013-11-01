#!/usr/bin/env python
"""
utilities for XRF display
"""
import copy
from functools import partial

import wx
import wx.lib.agw.pycollapsiblepane as CP

from wxutils import (SimpleText, FloatCtrl, Choice, Font, pack, Button,
                     Check, HLine, GridPanel, RowPanel, CEN, LEFT, RIGHT)

import larch
from larch.larchlib import Empty
larch.use_plugin_path('xrf')

from xrf_bgr import xrf_background
from xrf_calib import xrf_calib_fitrois, xrf_calib_compute, xrf_calib_apply

try:
    from collections import OrderedDict
except ImportError:
    from larch.utils import OrderedDict    

def read_filterdata(flist, _larch):
    """ read filters data"""
    materials = _larch.symtable.get_symbol('_xray._materials')
    out = OrderedDict()
    out['None'] = ('', 0)
    for name in flist:
        if name in materials:
            out[name]  = materials[name]
    return out

class FitVariable(wx.Panel):
    def __init__(self, parent, value=None, minval=None, maxval=None,
                 size=(90, -1), precision=4, allow_expr=False,
                 allow_global=False):
        wx.Panel.__init__(self, parent, -1)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        vary_choices = ['vary', 'fix']
        if allow_global:
            vary_choices.append('global')
        if allow_expr:
            vary_choices.append('constrain')
        self.val = FloatCtrl(self, value=value, size=size,
                             precision=precision,
                             minval=minval, maxval=maxval)
        self.vary = Choice(self, choices=vary_choices, size=(90, -1))

        sizer.Add(self.val, 1, LEFT|wx.GROW|wx.ALL)
        sizer.Add(self.vary, 0, LEFT|wx.GROW|wx.ALL)
        pack(self, sizer)
            

class FitSpectraFrame(wx.Frame):
    """Frame for Spectral Analysis"""

    Filter_Lengths = ['microns', 'mm', 'cm']                  
    Filter_Materials = ['None', 'air', 'nitrogen', 'helium', 'argon', 'kapton',
                        'mylar', 'pmma', 'water', 'aluminum', 'silicon nitride',
                        'silicon', 'quartz', 'sapphire', 'diamond', 'graphite',
                        'boron nitride']

    Detector_Materials = ['Si', 'Ge']
    
    def __init__(self, parent, size=(750, 700)):
        self.parent = parent
        self.mca = parent.mca
        conf = parent.conf
        wx.Frame.__init__(self, parent, -1, 'Fit XRF Spectra',
                          size=size, style=wx.DEFAULT_FRAME_STYLE)
        if not hasattr(self.parent, 'filters_data'):
            self.parent.filters_data = read_filterdata(self.Filter_Materials,
                                                       _larch=parent._larch)
            
        self.wids = Empty()
        self.SetFont(Font(9))
        panel = self.panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.createpanel_bgr(panel),  0, LEFT, 5)
        sizer.Add(HLine(panel, size=(675, 2)),  0, CEN|LEFT|wx.TOP|wx.GROW)

        sizer.Add(self.createpanel_filters(panel), 0, LEFT, 5)
        sizer.Add((5,5))
        sizer.Add(HLine(panel, size=(675, 2)),  0, CEN|LEFT|wx.TOP|wx.GROW)
        sizer.Add((5,5))

        # sizer.Add(self.createpanel_bgr_withcollapse(panel),  0, wx.ALL|wx.EXPAND|LEFT)
        # sizer.Add((10,10))

        sizer.Add(self.createpanel_settings(panel),  0, LEFT, 5)

        sizer.Add((5,5))        
        sizer.Add(HLine(panel, size=(675, 2)),  0, CEN|LEFT|wx.TOP|wx.GROW)
        sizer.Add((5,5))
        
        sizer.Add(self.createpanel_peaks(panel),  0, LEFT, 5)

        sizer.Add((5,5))        
        sizer.Add(HLine(panel, size=(675, 2)),  0, CEN|LEFT|wx.TOP|wx.GROW)
        sizer.Add((5,5))

        sizer.Add(Button(panel, 'Done',
                         size=(80, -1), action=self.onClose), 0, CEN)
        pack(panel, sizer)
        self.Show()
        self.Raise()
       

    def createpanel_peaks(self, panel):
        "create row for filters parameters"
        mca = self.parent.mca
        self.wids.peaks = []

        p = GridPanel(panel)
        
        p.AddText(" Peaks to Analyze: ",
                  colour='#880000', style=LEFT, dcol=3)
        
        p.AddManyText((' ROI Name', 'Fit?', 'Center', 'FWHM',
                       'Amplitude', 'Amplitude Expression'),   newrow=True)
        
        offset, slope = self.mca.offset, self.mca.slope
        for iroi, roi in enumerate(self.mca.rois):
            cenval = offset + slope*(roi.left + roi.right)/2.0
            fwhm   = slope*(roi.right - roi.left) / 2.0
            amp   = self.mca.counts[(roi.left + roi.right)/2.0]*4.0
            
            minval = offset + slope*(roi.left  - 4 * roi.bgr_width)
            maxval = offset + slope*(roi.right + 4 * roi.bgr_width)
            # print roi.left, roi.right, (roi.left + roi.right)/2.0, cenval
            # print roi,  cenval, fwhm , minval, maxval

            _use   = Check(p, default=True)
            _cen   = FitVariable(p, value=cenval, minval=minval,
                                 maxval=maxval, size=(65, -1))
            
            _fwhm   = FitVariable(p, value=fwhm, minval=0, 
                                  allow_global=True,  size=(65, -1))
            
            _amp    = FitVariable(p, value=amp, minval=0, precision=2, 
                                  allow_expr=True, size=(90, -1))

            _ampexpr = wx.TextCtrl(p, value='', size=(180, -1))
            
            self.wids.peaks.append((_use, _cen, _fwhm, _amp, _ampexpr))

            p.AddText(' %s' % roi.name,  newrow=True, style=LEFT)
            p.Add(_use, style=wx.ALIGN_CENTER)
            p.Add(_cen)
            p.Add(_fwhm)
            p.Add(_amp)
            p.Add(_ampexpr)
        p.pack()
        return p


    def createpanel_settings(self, panel):
        p = GridPanel(panel)
        conf = self.parent.conf
        wids = self.wids

        wids.fwhm_off   = FitVariable(p, value=0.100, size=(70, -1),
                                      precision=3, allow_expr=False)
        wids.fwhm_slope = FitVariable(p, value=0.000, size=(70, -1),
                                      precision=3, allow_expr=False)
        
       
        p.AddText(" Fit Settings: ", colour='#880000', style=LEFT, dcol=3)
        
        row1 = RowPanel(p)

        wids.fit_emin = FloatCtrl(row1, value=conf.e_min, size=(70, -1),
                                  minval=0, maxval=1000, precision=2)
        wids.fit_emax = FloatCtrl(row1, value=conf.e_max, size=(70, -1),
                                  minval=0, maxval=1000, precision=2)

        wids.det_mat = Choice(row1, choices=self.Detector_Materials,
                              size=(50, -1), default=0)
        wids.det_thk = FloatCtrl(row1, value=0.40, size=(70, -1),
                                 minval=0, maxval=100, precision=3)

        row1.AddText(' Energy Range = [ ')
        row1.Add(wids.fit_emin)
        row1.AddText(' : ')
        row1.Add(wids.fit_emax)
        row1.AddText(' ] (keV)     Detector Material:  ')
        row1.Add(wids.det_mat)
        row1.AddText(' thickness =')
        row1.Add(wids.det_thk)
        row1.AddText(' mm')
        row1.pack()

        p.Add(row1, dcol=8, newrow=True, style=LEFT)

        p.AddText('  Global FWHM Energy Dependence: ', newrow=True, dcol=3, style=LEFT)
        p.AddText('   FWHM = ', style=LEFT, newrow=True)

        p.Add(wids.fwhm_off)
        p.AddText( ' + ')
        p.Add(wids.fwhm_slope)
        p.AddText( ' * Energy (keV)')

        p.pack()
        return p

    def createpanel_bgr(self, panel):
        "create row for background settings"
        mca = self.parent.mca
        width = getattr(mca, 'bgr_width', 2.5)
        compr = getattr(mca, 'bgr_compress', 2)
        expon = getattr(mca, 'bgr_exponent', 2.5)

        p = GridPanel(panel)
        self.wids.bgr_use = Check(p, label='Include Background',
                                  default=True)
        self.wids.bgr_width = FloatCtrl(p, value=width, minval=0,
                                        maxval=10,
                                        precision=1, size=(50, -1))

        self.wids.bgr_compress = Choice(p, choices=['1', '2', '4', '8', '16'],
                                        size=(50, -1), default=1)

        self.wids.bgr_exponent = Choice(p, choices=['2', '4', '6'],
                                        size=(50, -1), default=0)

        p.AddText(" Background Params: ", colour='#880000', style=LEFT)
        p.Add(self.wids.bgr_use, dcol=3)
        p.Add(Button(p, 'Show Background',
                     size=(130, -1), action=self.onShowBgr), dcol=2)

        p.AddText(" Compression: ", newrow=True)
        p.Add(self.wids.bgr_compress)
        p.AddText(" Exponent:")
        p.Add(self.wids.bgr_exponent)
        p.AddText(" Energy Width: ")
        p.Add(self.wids.bgr_width)
        p.AddText(" (keV)")

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
        print 'onFilterMat ', name, index, form, den
        self.wids.filters[index][1].SetValue(den)
        thick = self.wids.filters[index][2]
        if thick.GetValue()  < 1.e-5:
            thick.SetValue(1)
            
    def onEditFilters(self, evt=None):
        print 'on Edit Filters ',  evt



    def createpanel_filters(self, panel):
        "create row for filters parameters"
        mca = self.parent.mca
        self.wids.filters = []

        p = GridPanel(panel)
        
        p.AddText(" Filters and Attenuation Paths: ",
                  colour='#880000', style=LEFT, dcol=3)
        
        bx = Button(p, 'Customize Filter List', size=(150, -1),
                    action = self.onEditFilters)
        bx.Disable()
        p.Add(bx, dcol=3)
       
        p.AddManyText((' filter', 'material', 'density (gr/cm^3)',
                       'thickness', 'units', 'refine thickness?'),
                      newrow=True)
        
        for i in range(4):
            _mat = Choice(p, choices=self.Filter_Materials, default=0, size=(125, -1),
                          action=partial(self.onFilterMaterial, index=i))
            _den = FloatCtrl(p, value=0, minval=0, maxval=30,
                             precision=4, size=(60, -1))
            _len = FloatCtrl(p, value=0, minval=0,
                             precision=4, size=(60, -1))
            _units  = Choice(p, choices=self.Filter_Lengths,
                             default=1, size=(100, -1))
            _fit = Check(p, default=False)
            
            self.wids.filters.append((_mat, _den, _len, _units, _fit))
            p.AddText('  %i ' % (i+1), newrow=True, style=LEFT)
            p.Add(_mat)
            p.Add(_den, style=wx.ALIGN_CENTER)
            p.Add(_len)
            p.Add(_units)
            p.Add(_fit, style=wx.ALIGN_CENTER)
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
