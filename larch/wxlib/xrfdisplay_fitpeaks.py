#!/usr/bin/env python
"""
fitting GUI for XRF display
"""
import time
import copy
from functools import partial
from collections import OrderedDict

from threading import Thread

import json
import numpy as np
import wx
import wx.lib.agw.pycollapsiblepane as CP
import wx.lib.scrolledpanel as scrolled
import wx.dataview as dv
DVSTYLE = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES

from lmfit import Parameter, Minimizer
from lmfit.printfuncs import gformat, CORREL_HEAD

from wxutils import (SimpleText, FloatCtrl, FloatSpin, Choice, Font, pack,
                     Button, Check, HLine, GridPanel, RowPanel, CEN, LEFT,
                     RIGHT, FileSave, GUIColors, RCEN, LCEN, FRAMESTYLE,
                     BitmapButton, SetTip, GridPanel, Popup,
                     FloatSpinWithPin, get_icon, fix_filename)

from . import FONTSIZE
from xraydb import material_mu, xray_edge, materials, add_material
from .notebooks import flatnotebook
from .parameter import ParameterPanel
from .periodictable import PeriodicTablePanel

from larch import Group

from ..xrf import xrf_background, MCA
from ..utils.jsonutils import encode4js, decode4js

def read_filterdata(flist, _larch):
    """ read filters data"""
    materials = _larch.symtable.get_symbol('_xray._materials')
    out = OrderedDict()
    out['None'] = ('', 0)
    for name in flist:
        if name in materials:
            out[name]  = materials[name]
    return out

def VarChoice(p, default=0, size=(75, -1)):
    return Choice(p, choices=['Fix', 'Vary'],
                  size=size, default=default)

NFILTERS = 4
MATRIX_LAYERNAMES = ('top', 'middle', 'bottom')

Detector_Materials = ['Si', 'Ge']
EFano = {'Si': 3.66 * 0.115, 'Ge': 3.0 * 0.130}
EFano_Text = 'Peak Widths:  sigma = sqrt(E_Fano * Energy + Noise**2) '
Energy_Text = 'All energies in eV'

MIN_CORREL = 0.10

mca_init = """
{group:s}.fit_history = getattr({group:s}, 'fit_history', [])
{group:s}.energy_ev = {group:s}.energy*{efactor:.1f}
"""

xrfmod_setup = """## Set up XRF Model
_xrfmodel = xrf_model(xray_energy={en_xray:.2f},
                      count_time={count_time:.5f},
                      energy_min={en_min:.2f}, energy_max={en_max:.2f})

_xrfmodel.set_detector(thickness={det_thk:.5f}, material='{det_mat:s}',
                cal_offset={cal_offset:.5f}, cal_slope={cal_slope:.5f},
                vary_cal_offset={cal_vary!r}, vary_cal_slope={cal_vary!r},
                vary_cal_quad=False,
                peak_step={peak_step:.5f}, vary_peak_step={peak_step_vary:s},
                peak_tail={peak_tail:.5f}, vary_peak_tail={peak_tail_vary:s},
                peak_gamma={peak_gamma:.5f}, vary_peak_gamma={peak_gamma_vary:s},
                peak_sigmax={peak_sigma:.5f}, vary_peak_sigmax={peak_sigma_vary:s},
                noise={det_noise:.5f}, vary_noise={det_noise_vary:s},
                efano={det_efano:.5f}, vary_efano={det_efano_vary:s})
"""

xrfmod_scattpeak = """_xrfmodel.add_scatter_peak(name='{peakname:s}', center={_cen:.2f},
                amplitude=1e5, step={_step:.5f}, tail={_tail:.5f}, gamma={_gamma:.5f},
                sigmax={_sigma:.5f},  vary_center={vcen:s}, vary_step={vstep:s},
                vary_tail={vtail:s}, vary_sigmax={vsigma:s}, vary_gamma={vgamma:s})
"""

xrfmod_fitscript = """_xrfmodel.fit_spectrum({group:s}.energy_ev, {group:s}.counts,
                energy_min={emin:.2f}, energy_max={emax:.2f})
_xrfresult = _xrfmodel.compile_fitresults()
"""

xrfmod_filter = "_xrfmodel.add_filter('{name:s}', {thick:.5f}, vary_thickness={vary:s})"
xrfmod_matrix = "_xrfmodel.add_matrix_layer('{name:s}', {thick:.5f}, density={density:.5f})"

xrfmod_bgr = """xrf_background(energy={group:s}.energy, counts={group:s}.counts,
             group={group:s}, width={bgr_wid:.2f}, exponent={bgr_exp:.2f})
_xrfmodel.add_background({group:s}.bgr, vary=False)
"""

xrfmod_jsondump  = """# save xrf model to json
_o = copy(group2dict({group:s}.fit_history[{nfit:d}]))
_o['params'] = _o.pop('params').dumps()
json_dump(_o, '{filename:s}')
"""

xrfmod_pileup = "_xrfmodel.add_pileup(scale={scale:.5f}, vary={vary:s})"
xrfmod_escape = "_xrfmodel.add_escape(scale={scale:.5f}, vary={vary:s})"

xrfmod_elems = """
for atsym in {elemlist:s}:
    _xrfmodel.add_element(atsym)
#endfor
"""

XRFGROUP = '_xrfdata'

Filter_Lengths = ['microns', 'mm', 'cm']
Filter_Materials = ['None', 'air', 'nitrogen', 'helium', 'kapton',
                    'beryllium', 'aluminum', 'mylar', 'pmma']


class FitSpectraFrame(wx.Frame):
    """Frame for Spectral Analysis"""

    def __init__(self, parent, size=(600, 775)):
        self.parent = parent
        self._larch = parent.larch
        if not self._larch.symtable.has_group(XRFGROUP):
            self._larch.eval("%s = group()" % XRFGROUP)
        xrfgroup = self._larch.symtable.get_group(XRFGROUP)
        for i in range(1, 1000):
            mcaname = 'mca%3.3d' % (i)
            if not hasattr(xrfgroup, mcaname):
                break

        self.mcagroup = '%s.%s' % (XRFGROUP, mcaname)
        self.mca = MCA()
        for attr in ('__name__', 'filename', 'incident_energy', 'live_time',
                     'real_time', 'slope', 'quad', 'offset'):
            setattr(self.mca, attr, getattr(self.parent.mca, attr, None))
        for attr in ('counts', 'energy', 'raw'):
            setattr(self.mca, attr, 1.0*getattr(self.parent.mca, attr, None))
        for attr in ('header', 'bad', 'mcas', 'rois', 'environ'):
            setattr(self.mca, attr, copy.copy(getattr(self.parent.mca, attr, None)))

        setattr(xrfgroup, mcaname, self.mca)

        efactor = 1.0 if max(self.mca.energy) > 250.0 else 1000.0
        self._larch.eval(mca_init.format(group=self.mcagroup, efactor=efactor))

        self.fit_history = getattr(self.mca, 'fit_history', [])
        self.nfit = 0
        self.colors = GUIColors()
        wx.Frame.__init__(self, parent, -1, 'Fit XRF Spectra',
                          size=size, style=wx.DEFAULT_FRAME_STYLE)

        self.wids = {}
        self.result_frame = None
        self.panels = {}
        self.panels['Beam and Detector']  = self.beamdet_page
        self.panels['Filters and Matrix'] = self.materials_page
        self.panels['Elements and Peaks'] = self.elempeaks_page
        self.panels['Fit Results']        = self.fitresult_page

        self.nb = flatnotebook(self, self.panels)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)

        bpanel = wx.Panel(self)
        self.SetBackgroundColour((235, 235, 235))
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.Add(Button(bpanel, 'Calculate Model', size=(200, -1),
                          action=self.onShowModel), 0, LEFT)
        bsizer.Add(Button(bpanel, 'Fit Model', size=(200, -1),
                          action=self.onFitModel), 0, LEFT)

        pack(bpanel, bsizer)
        sizer.Add(bpanel, 0, CEN)
        sizer.Add((5,5))
        pack(self, sizer)
        self.Show()
        self.Raise()

    def elempeaks_page(self, **kws):
        "elements and peaks parameters"
        mca = self.parent.mca
        wids = self.wids
        p = GridPanel(self)
        tooltip_msg = 'Select Elements to include in model'
        self.selected_elems = []
        self.ptable = PeriodicTablePanel(p, multi_select=True, fontsize=11,
                                         tooltip_msg=tooltip_msg,
                                         onselect=self.onElemSelect)
        for roi in self.mca.rois:
            words = roi.name.split()
            elem = words[0].title()
            if elem in self.ptable.syms and elem not in self.ptable.selected:
                self.ptable.onclick(label=elem)


        dstep, dtail, dsigma, dgamma = 0.1, 0.25, 1.0, 0.25
        wids['peak_step'] = FloatSpin(p, value=dstep, digits=4, min_val=0,
                                      max_val=10.0, increment=0.01)
        wids['peak_tail'] = FloatSpin(p, value=dtail, digits=4, min_val=0,
                                        max_val=0.5, increment=0.01)

        wids['peak_gamma'] = FloatSpin(p, value=dgamma, digits=4, min_val=0,
                                       max_val=30.0, increment=0.1)
        wids['peak_sigma'] = FloatSpin(p, value=dsigma, digits=4, min_val=0,
                                       max_val=10.0, increment=0.1)
        wids['peak_step_vary'] = VarChoice(p, default=0)
        wids['peak_tail_vary'] = VarChoice(p, default=0)
        wids['peak_gamma_vary'] = VarChoice(p, default=0)
        wids['peak_sigma_vary'] = VarChoice(p, default=0)

        btn_clear_elems = Button(p, 'Clear All', size=(150, -1),
                                 action=self.onElems_Clear)
        btn_from_rois = Button(p, 'Select from ROIS', size=(150, -1),
                               action=self.onElems_FromROIS)

        p.AddText('Elements to model:', colour='#880000', dcol=2)
        p.Add(btn_clear_elems,  dcol=2)
        p.Add(btn_from_rois,    dcol=2)
        p.Add((2, 2), newrow=True)
        p.Add(self.ptable, dcol=6)

        p.Add((2, 2), newrow=True)
        p.AddText('  Step (%): ')
        p.Add(wids['peak_step'])
        p.Add(wids['peak_step_vary'])

        p.AddText('  Tail: ')
        p.Add(wids['peak_tail'])
        p.Add(wids['peak_tail_vary'])

        p.Add((2, 2), newrow=True)
        p.AddText('  Gamma : ')
        p.Add(wids['peak_gamma'])
        p.Add(wids['peak_gamma_vary'])

        p.AddText('  Sigma Scale: ')
        p.Add(wids['peak_sigma'])
        p.Add(wids['peak_sigma_vary'])

        p.Add((2, 2), newrow=True)
        p.Add(HLine(p, size=(550, 3)), dcol=8)

        p.Add((2, 2), newrow=True)
        opts = dict(size=(100, -1),
                    min_val=0, digits=4, increment=0.010)
        for name, escale, dsigma in (('Elastic',  1.000, 1.0),
                                     ('Compton1', 0.975, 1.5),
                                     ('Compton2', 0.950, 2.0)):
            en = escale * self.mca.incident_energy
            t = name.lower()
            vary_en = 1 if t.startswith('compton') else 0

            wids['%s_use'%t] = Check(p, label='Include', default=True)
            wids['%s_cen_vary'%t]   = VarChoice(p, default=vary_en)
            wids['%s_step_vary'%t]  = VarChoice(p, default=0)
            wids['%s_gamma_vary'%t] = VarChoice(p, default=0)
            wids['%s_tail_vary'%t]  = VarChoice(p, default=0)
            wids['%s_sigma_vary'%t] = VarChoice(p, default=0)

            wids['%s_cen'%t]  = FloatSpin(p, value=en, digits=2, min_val=0,
                                           increment=10)
            wids['%s_step'%t] = FloatSpin(p, value=dstep, digits=4, min_val=0,
                                           max_val=20.0, increment=0.01)
            wids['%s_tail'%t] = FloatSpin(p, value=dtail, digits=4, min_val=0,
                                           max_val=30.0, increment=0.01)
            wids['%s_gamma'%t] = FloatSpin(p, value=dsigma, digits=4, min_val=0,
                                           max_val=30.0, increment=0.1)
            wids['%s_sigma'%t] = FloatSpin(p, value=dsigma, digits=4, min_val=0,
                                           max_val=10.0, increment=0.1)

            p.Add((2, 2), newrow=True)
            p.AddText("  %s Peak:" % name,  colour='#880000')
            p.Add(wids['%s_use' % t], dcol=2)

            p.AddText('  Energy (eV): ')
            p.Add(wids['%s_cen'%t])
            p.Add(wids['%s_cen_vary'%t])

            p.Add((2, 2), newrow=True)
            p.AddText('  Step (%): ')
            p.Add(wids['%s_step'%t])
            p.Add(wids['%s_step_vary'%t])

            p.AddText('  Tail: ')
            p.Add(wids['%s_tail'%t])
            p.Add(wids['%s_tail_vary'%t])

            p.Add((2, 2), newrow=True)
            p.AddText('  Gamma : ')
            p.Add(wids['%s_gamma'%t])
            p.Add(wids['%s_gamma_vary'%t])

            p.AddText('  Sigma Scale : ')
            p.Add(wids['%s_sigma'%t])
            p.Add(wids['%s_sigma_vary'%t])

            p.Add((2, 2), newrow=True)
            p.Add(HLine(p, size=(550, 3)), dcol=7)

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

        en_min = 2000.0
        en_max = xray_energy

        cal_offset = getattr(mca, 'offset',  0) * 1000.0
        cal_slope = getattr(mca, 'slope',  0.010) * 1000.0
        det_efano = getattr(mca, 'det_efano',  EFano['Si'])
        det_noise = getattr(mca, 'det_noise',  30)
        det_efano = getattr(mca, 'det_efano',  EFano['Si'])
        width = getattr(mca, 'bgr_width',    3000)
        expon = getattr(mca, 'bgr_exponent', 2)
        escape_amp = getattr(mca, 'escape_amp', 0.010)
        pileup_amp = getattr(mca, 'pileup_amp', 0.010)

        wids = self.wids
        # main = wx.Panel(self)
        pdet = GridPanel(self, itemstyle=LEFT)

        def addLine(pan):
            pan.Add(HLine(pan, size=(600, 3)), dcol=6, newrow=True)

        bgr_code1 = """
        wids['bgr_use'] = Check(pdet, label='Include Background in Fit',
                                default=False, action=self.onUseBackground)
        wids['bgr_width'] = FloatSpin(pdet, value=width, min_val=0, max_val=15000,
                                   digits=0, increment=500, size=(100, -1))
        wids['bgr_expon'] = Choice(pdet, choices=['2', '4', '6'],
                                   size=(70, -1), default=0)
        wids['bgr_show'] = Button(pdet, 'Show', size=(80, -1),
                                  action=self.onShowBgr)
        wids['bgr_width'].Disable()
        wids['bgr_expon'].Disable()
        wids['bgr_show'].Disable()
        """

        wids['escape_use'] = Check(pdet, label='Include Escape in Fit',
                                   default=True, action=self.onUsePileupEscape)
        wids['escape_amp'] = FloatSpin(pdet, value=escape_amp,
                                         min_val=0, max_val=0.5, digits=4,
                                         increment=0.001, size=(100, -1))

        wids['pileup_use'] = Check(pdet, label='Include Pileup in Fit',
                                   default=True, action=self.onUsePileupEscape)
        wids['pileup_amp'] = FloatSpin(pdet, value=pileup_amp,
                                         min_val=0, max_val=100, digits=4,
                                         increment=0.001, size=(100, -1))

        wids['escape_amp_vary'] = VarChoice(pdet, default=True)
        wids['pileup_amp_vary'] = VarChoice(pdet, default=True)


        wids['cal_slope'] = FloatSpin(pdet, value=cal_slope,
                                      min_val=0, max_val=100,
                                      digits=4, increment=0.01, size=(100, -1))
        wids['cal_offset'] = FloatSpin(pdet, value=cal_offset,
                                      min_val=-500, max_val=500,
                                      digits=4, increment=0.01, size=(100, -1))

        wids['cal_vary'] = Check(pdet, label='Vary Calibration in Fit', default=True)

        wids['det_mat'] = Choice(pdet, choices=Detector_Materials,
                                 size=(70, -1), default=0,
                                 action=self.onDetMaterial)

        wids['det_thk'] = FloatSpin(pdet, value=0.400, size=(100, -1),
                                     increment=0.010, min_val=0, max_val=10,
                                     digits=4)

        wids['det_noise_vary'] = VarChoice(pdet, default=1)
        wids['det_efano_vary'] = VarChoice(pdet, default=0)

        opts = dict(size=(100, -1), min_val=0, max_val=250000,
                    digits=2, increment=50)
        wids['en_xray'] = FloatSpin(pdet, value=xray_energy,
                                    action=self.onSetXrayEnergy, **opts)
        wids['en_min'] = FloatSpin(pdet, value=en_min, **opts)
        wids['en_max'] = FloatSpin(pdet, value=en_max, **opts)

        opts.update({'digits': 3, 'max_val': 500, 'increment': 1})
        wids['det_noise'] = FloatSpin(pdet, value=det_noise, **opts)

        opts.update({'max_val': 1, 'increment': 0.001})
        wids['det_efano'] = FloatSpin(pdet, value=det_efano, **opts)


        pdet.AddText(' Beam Energy, Fit Range :', colour='#880000', dcol=2)
        pdet.AddText(Energy_Text, dcol=2)
        pdet.AddText('   X-ray Energy: ', newrow=True)
        pdet.Add(wids['en_xray'])
        pdet.AddText('   Energy Min: ', newrow=True)
        pdet.Add(wids['en_min'])
        pdet.AddText('Energy Max: ')
        pdet.Add(wids['en_max'])

        addLine(pdet)
        pdet.AddText('Energy Calibration :', colour='#880000', dcol=2, newrow=True)
        pdet.Add(wids['cal_vary'], dcol=2)
        pdet.AddText('   Offset (eV): ', newrow=True)
        pdet.Add(wids['cal_offset'])
        pdet.AddText('Slope (eV/bin): ')
        pdet.Add(wids['cal_slope'])

        addLine(pdet)
        pdet.AddText(' Detector :', colour='#880000', newrow=True)
        pdet.AddText(EFano_Text, dcol=3)
        pdet.AddText('   Material:  ', newrow=True)
        pdet.Add(wids['det_mat'])
        pdet.AddText('Thickness (mm): ')
        pdet.Add(wids['det_thk'])

        pdet.AddText('   Noise: ', newrow=True)
        pdet.Add(wids['det_noise'])
        pdet.Add(wids['det_noise_vary'], dcol=2)
        pdet.AddText('   E_Fano: ', newrow=True)
        pdet.Add(wids['det_efano'])
        pdet.Add(wids['det_efano_vary'], dcol=2)

        """
        pdet.Add(HLine(pdet, size=(550, 3)), dcol=4, newrow=True)
        pdet.AddText(' Background: ', colour='#880000', newrow=True)
        pdet.Add(wids['bgr_use'], dcol=2)
        pdet.Add(wids['bgr_show'])
        pdet.AddText('   Exponent:', newrow=True)
        pdet.Add(wids['bgr_expon'])
        pdet.AddText('Energy Width: ')
        pdet.Add(wids['bgr_width'])
        """

        addLine(pdet)
        pdet.AddText(' Escape && Pileup:', colour='#880000', newrow=True)
        pdet.AddText('   Escape Scale:', newrow=True)
        pdet.Add(wids['escape_amp'])
        pdet.Add(wids['escape_amp_vary'])
        pdet.Add(wids['escape_use'], dcol=3)

        pdet.AddText('   Pileup Scale:', newrow=True)
        pdet.Add(wids['pileup_amp'])
        pdet.Add(wids['pileup_amp_vary'])
        pdet.Add(wids['pileup_use'], dcol=3)
        addLine(pdet)
        pdet.pack()

        # sizer = wx.BoxSizer(wx.VERTICAL)
        # sizer.Add(pdet)
        # pack(main, sizer)
        return pdet

    def materials_page(self, **kws):
        "filters and matrix settings"
        conf = self.parent.conf
        wids = self.wids

        pan = GridPanel(self, itemstyle=LEFT)

        pan.AddText(' Filters :', colour='#880000', dcol=2) # , newrow=True)
        pan.AddManyText(('  Filter #', 'Material',
                         'Thickness (mm)',
                         'Vary Thickness'), style=CEN, newrow=True)
        opts = dict(size=(100, -1), min_val=0, digits=5, increment=0.005)

        for i in range(1, NFILTERS+1):
            t = 'filt%d' % i
            wids['%s_mat'%t] = Choice(pan, choices=Filter_Materials, default=0,
                                      size=(150, -1),
                                      action=partial(self.onFilterMaterial, index=i))
            wids['%s_thk'%t] = FloatSpin(pan, value=0.0, **opts)
            wids['%s_var'%t] = VarChoice(pan, default=0)
            if i == 1: # first selection
                wids['%s_mat'%t].SetStringSelection('beryllium')
                wids['%s_thk'%t].SetValue(0.0250)
            elif i == 2: # second selection
                wids['%s_mat'%t].SetStringSelection('air')
                wids['%s_thk'%t].SetValue(50.00)
            elif i == 3: # third selection
                wids['%s_mat'%t].SetStringSelection('kapton')
                wids['%s_thk'%t].SetValue(0.00)
            elif i == 4: # third selection
                wids['%s_mat'%t].SetStringSelection('aluminum')
                wids['%s_thk'%t].SetValue(0.00)

            pan.AddText('    %i  ' % (i), newrow=True)
            pan.Add(wids['%s_mat' % t])
            pan.Add(wids['%s_thk' % t])
            pan.Add(wids['%s_var' % t])

        pan.Add(HLine(pan, size=(600, 3)), dcol=6, newrow=True)

        pan.AddText(' Matrix Layers:', colour='#880000', dcol=2, newrow=True)
        pan.AddManyText(('  Layer', 'Material/Formula',
                         'thickness (mm)', 'density'), style=CEN, newrow=True)
        for layer in MATRIX_LAYERNAMES:
            t = 'matrix_%s' % layer
            wids['%s_mat'%t] = wx.TextCtrl(pan, value='', size=(150, -1))
            wids['%s_thk'%t] = FloatSpin(pan, value=0.0, **opts)
            wids['%s_den'%t] = FloatSpin(pan, value=1.0, **opts)
            wids['%s_btn'%t] = Button(pan, 'Use Selected Material', size=(150, -1),
                                      action=partial(self.onUseCurrentMaterial,
                                                     layer=layer))
            pan.AddText('     %s' % (layer), style=LCEN, newrow=True)
            pan.Add(wids['%s_mat' % t])
            pan.Add(wids['%s_thk' % t])
            pan.Add(wids['%s_den' % t])
            pan.Add(wids['%s_btn' % t])

        pan.Add(HLine(pan, size=(600, 3)), dcol=6, newrow=True)

        # Materials
        pan.AddText(' Known Materials:', colour='#880000', dcol=4, newrow=True)
        bx = Button(pan, 'Update Filter List', size=(150, -1),
                    action=self.onUpdateFilterList)
        pan.Add(bx)

        mview = wids['materials'] = dv.DataViewListCtrl(pan, style=DVSTYLE)
        mview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectMaterial)
        self.selected_material = ('', '', 1.0)

        mview.AppendTextColumn('Name',      width=150)
        mview.AppendTextColumn('Formula',   width=325)
        mview.AppendTextColumn('density',    width=90)
        mview.AppendToggleColumn('Filter?',  width=50)
        for col in range(4):
            this = mview.Columns[col]
            align = wx.ALIGN_LEFT
            this.Sortable = True
            this.Alignment = this.Renderer.Alignment = align

        mview.SetMinSize((625, 175))
        mview.DeleteAllItems()
        self.materials_data = []
        self.materials_name = []
        for name, data in materials._read_materials_db().items():
            formula, density = data
            mview.AppendItem((name, formula, "%9.6f"%density,
                              name in Filter_Materials))
            self.materials_data.append((name, formula, density))
            self.materials_name.append(name)
        pan.Add(mview, dcol=5, newrow=True)

        pan.AddText(' Add Materials:', colour='#880000', dcol=2, newrow=True)
        wids['newmat_name'] = wx.TextCtrl(pan, value='', size=(150, -1))
        wids['newmat_dens'] = FloatSpin(pan, value=1.0, **opts)
        wids['newmat_form'] = wx.TextCtrl(pan, value='', size=(400, -1))

        pan.AddText(' Name:', newrow=True)
        pan.Add(wids['newmat_name'])
        pan.AddText(' Density:', newrow=False)
        pan.Add(wids['newmat_dens'])
        pan.AddText(' Formula:', newrow=True)
        pan.Add(wids['newmat_form'], dcol=3)
        bx = Button(pan, 'Add Material', size=(150, -1),
                    action=self.onAddMaterial)
        pan.Add(bx)


        pan.pack()
        return pan

    def fitresult_page(self, **kws):
        sizer = wx.GridBagSizer(10, 5)
        sizer.SetVGap(5)
        sizer.SetHGap(5)

        panel = scrolled.ScrolledPanel(self)
        # title row
        self.rwids = wids = {}
        title = SimpleText(panel, 'Fit Results', font=Font(FONTSIZE+1),
                           colour=self.colors.title, style=LCEN)

        wids['data_title'] = SimpleText(panel, '< > ', font=Font(FONTSIZE+1),
                                             colour=self.colors.title, style=LCEN)

        wids['fitlabel_lab'] = SimpleText(panel, ' Fit Label: ')
        wids['fitlabel_txt'] = wx.TextCtrl(panel, -1, ' ', size=(150, -1))
        wids['fitlabel_btn'] = Button(panel, 'Set Label',  size=(150, -1),
                                      action=self.onChangeFitLabel)

        opts = dict(default=False, size=(175, -1), action=self.onPlot)
        wids['plot_comps'] = Check(panel, label='Show Components?', **opts)
        self.plot_choice = Button(panel, 'Plot',
                                  size=(150, -1), action=self.onPlot)

        self.save_result = Button(panel, 'Save Model',
                                  size=(150, -1), action=self.onSaveFitResult)
        SetTip(self.save_result, 'save model and result to be loaded later')

        self.export_fit  = Button(panel, 'Export Fit',
                                  size=(150, -1), action=self.onExportFitResult)
        SetTip(self.export_fit, 'save arrays and results to text file')

        irow = 0
        sizer.Add(title,              (irow, 0), (1, 2), LCEN)
        sizer.Add(wids['data_title'], (irow, 2), (1, 2), LCEN)

        irow += 1
        sizer.Add(self.save_result,   (irow, 0), (1, 1), LCEN)
        sizer.Add(self.export_fit,    (irow, 1), (1, 1), LCEN)
        sizer.Add(self.plot_choice,   (irow, 2), (1, 1), LCEN)
        sizer.Add(wids['plot_comps'], (irow, 3), (1, 1), LCEN)

        irow += 1
        sizer.Add(wids['fitlabel_lab'], (irow, 0), (1, 1), LCEN)
        sizer.Add(wids['fitlabel_txt'], (irow, 1), (1, 1), LCEN)
        sizer.Add(wids['fitlabel_btn'], (irow, 2), (1, 2), LCEN)


        irow += 1
        sizer.Add(HLine(panel, size=(625, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Fit Statistics]]',  font=Font(FONTSIZE+1),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title, (irow, 0), (1, 4), LCEN)

        sview = wids['stats'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        sview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectFit)
        sview.AppendTextColumn('  Fit Label', width=90)
        sview.AppendTextColumn(' N_vary', width=65)
        sview.AppendTextColumn(' N_eval', width=65)
        sview.AppendTextColumn(' \u03c7\u00B2', width=125)
        sview.AppendTextColumn(' \u03c7\u00B2_reduced', width=125)
        sview.AppendTextColumn(' Akaike Info', width=125)

        for col in range(sview.ColumnCount):
            this = sview.Columns[col]
            isort, align = True, wx.ALIGN_RIGHT
            if col == 0:
                align = wx.ALIGN_CENTER
            this.Sortable = isort
            this.Alignment = this.Renderer.Alignment = align
        sview.SetMinSize((625, 150))

        irow += 1
        sizer.Add(sview, (irow, 0), (1, 5), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(625, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Variables]]',  font=Font(FONTSIZE+1),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title, (irow, 0), (1, 1), LCEN)

        pview = wids['params'] = dv.DataViewListCtrl(panel, style=DVSTYLE)
        wids['paramsdata'] = []
        pview.AppendTextColumn('Parameter',      width=150)
        pview.AppendTextColumn('Refined Value',  width=150)
        pview.AppendTextColumn('Standard Error', width=150)
        pview.AppendTextColumn('Info ',          width=150)

        for col in range(4):
            this = pview.Columns[col]
            align = wx.ALIGN_LEFT
            if col in (1, 2):
                align = wx.ALIGN_RIGHT
            this.Sortable = False
            this.Alignment = this.Renderer.Alignment = align

        pview.SetMinSize((625, 200))
        pview.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.onSelectParameter)

        irow += 1
        sizer.Add(pview, (irow, 0), (1, 5), LCEN)

        irow += 1
        sizer.Add(HLine(panel, size=(625, 3)), (irow, 0), (1, 5), LCEN)

        irow += 1
        title = SimpleText(panel, '[[Correlations]]',  font=Font(FONTSIZE+1),
                           colour=self.colors.title, style=LCEN)

        wids['all_correl'] = Button(panel, 'Show All',
                                    size=(100, -1), action=self.onAllCorrel)

        wids['min_correl'] = FloatSpin(panel, value=MIN_CORREL,
                                       min_val=0, size=(100, -1),
                                       digits=3, increment=0.1)

        ctitle = SimpleText(panel, 'minimum correlation: ')
        sizer.Add(title,  (irow, 0), (1, 1), LCEN)
        sizer.Add(ctitle, (irow, 1), (1, 1), LCEN)
        sizer.Add(wids['min_correl'], (irow, 2), (1, 1), LCEN)
        sizer.Add(wids['all_correl'], (irow, 3), (1, 1), LCEN)

        cview = wids['correl'] = dv.DataViewListCtrl(panel, style=DVSTYLE)

        cview.AppendTextColumn('Parameter 1',    width=150)
        cview.AppendTextColumn('Parameter 2',    width=150)
        cview.AppendTextColumn('Correlation',    width=150)

        for col in (0, 1, 2):
            this = cview.Columns[col]
            this.Sortable = False
            align = wx.ALIGN_LEFT
            if col == 2:
                align = wx.ALIGN_RIGHT
            this.Alignment = this.Renderer.Alignment = align
        cview.SetMinSize((550, 150))

        irow += 1
        sizer.Add(cview, (irow, 0), (1, 5), LCEN)

        pack(panel, sizer)
        panel.SetupScrolling()
        return panel

    def onElems_Clear(self, event=None):
        self.ptable.on_clear_all()

    def onElems_FromROIS(self, event=None):
        for roi in self.mca.rois:
            words = roi.name.split()
            elem = words[0].title()
            if (elem in self.ptable.syms and
                elem not in self.ptable.selected):
                self.ptable.onclick(label=elem)
        self.onSetXrayEnergy()

    def onSetXrayEnergy(self, event=None):
        en = self.wids['en_xray'].GetValue()
        self.wids['en_max'].SetValue(en)
        self.wids['elastic_cen'].SetValue(en)
        self.wids['compton1_cen'].SetValue(en*0.975)
        self.wids['compton2_cen'].SetValue(en*0.950)
        emin = self.wids['en_min'].GetValue() * 1.25

        self.ptable.on_clear_all()
        for roi in self.mca.rois:
            words = roi.name.split()
            elem = words[0].title()
            kedge = l3edge = l2edge = 0.0
            try:
                kedge = xray_edge(elem, 'K').energy
                l3edge = xray_edge(elem, 'L3').energy
                l2edge = xray_edge(elem, 'L3').energy
            except:
                pass
            if ((kedge < en and kedge > emin) or
                (l3edge < en and l3edge > emin) or
                (l2edge < en and l2edge > emin)):
                if elem not in self.ptable.selected:
                    self.ptable.onclick(label=elem)

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
        den = 1.0
        for  _name, _form, _dens in self.materials_data:
            if _name == name:
                den = _dens
        t = 'filt%d' % index
        thick = self.wids['%s_thk'%t]
        if den < 0.1 and thick.GetValue() < 0.1:
            thick.SetValue(10.0)
            thick.SetIncrement(0.5)
        elif den > 0.1 and thick.GetValue() < 1.e-5:
            thick.SetValue(0.0250)
            thick.SetIncrement(0.005)

    def onUseCurrentMaterial(self, evt=None, layer=None):
        name, formula, density = self.selected_material
        if layer is not None and len(name)>0:
            self.wids['matrix_%s_den'% layer].SetValue(density)
            self.wids['matrix_%s_mat'% layer].SetValue(name)

    def onSelectMaterial(self, evt=None):
        if self.wids['materials'] is None:
            return
        item = self.wids['materials'].GetSelectedRow()
        if item > -1:
            self.selected_material = self.materials_data[item]

    def onUpdateFilterList(self, evt=None):
        flist = ['None']
        for i in range(len(self.materials_data)):
            if self.wids['materials'].GetToggleValue(i, 3): # is filter
                flist.append(self.wids['materials'].GetTextValue(i, 0))

        for i in range(1, NFILTERS+1):
            t = 'filt%d' % i
            choice = self.wids['%s_mat'%t]
            cur = choice.GetStringSelection()
            choice.Clear()
            choice.SetChoices(flist)
            if cur in flist:
                choice.SetStringSelection(cur)
            else:
                choice.SetSelection(0)

    def onAddMaterial(self, evt=None):

        name = self.wids['newmat_name'].GetValue()
        formula = self.wids['newmat_form'].GetValue()
        density = self.wids['newmat_dens'].GetValue()
        add = len(name) > 0 and len(formula)>0
        if add and name in self.materials_name:
            add = (Popup(self,
                         "Overwrite definition of '%s'?" % name,
                         'Re-define material?',
                         style=wx.OK|wx.CANCEL)==wx.ID_OK)
            if add:
                irow = self.materials_name.index(name)
                self.wids['materials'].DeleteItem(irow)
        if add:
            add_material(name, formula, density)
            self.materials_data.append((name, formula, density))
            self.materials_name.append(name)
            #print()
            self.wids['materials'].AppendItem((name, formula,
                                               "%9.6f"%density,
                                               False))


    def onElemSelect(self, event=None, elem=None):
        self.ptable.tsym.SetLabel('')
        self.ptable.title.SetLabel('%d elements selected' % len(self.ptable.selected))

    def onUseBackground(self, event=None):
        use_bgr = self.wids['bgr_use'].IsChecked()
        self.wids['bgr_width'].Enable(use_bgr)
        self.wids['bgr_expon'].Enable(use_bgr)
        self.wids['bgr_show'].Enable(use_bgr)

    def onUsePileupEscape(self, event=None):
        puse = self.wids['pileup_use'].IsChecked()
        self.wids['pileup_amp'].Enable(puse)
        self.wids['pileup_amp_vary'].Enable(puse)

        puse = self.wids['escape_use'].IsChecked()
        self.wids['escape_amp'].Enable(puse)
        self.wids['escape_amp_vary'].Enable(puse)


    def onUsePeak(self, event=None, name=None, value=None):
        if value is None and event is not None:
            value = event.IsChecked()
        if name is None:
            return
        for a in ('cen', 'step', 'tail', 'sigma', 'gamma'):
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
            elif hasattr(wid, 'GetStringSelection'):
                val = wid.GetStringSelection()
            else:
                opts[key] = '????'
            if isinstance(val, str) and val.title() in vars:
                val = vars[val.title()]
            opts[key] = val
        opts['count_time'] = getattr(self.mca, 'real_time', 1.0)

        script = [xrfmod_setup.format(**opts)]

        for peak in ('Elastic', 'Compton1', 'Compton2'):
            t = peak.lower()
            if opts['%s_use'% t]:
                d = {'peakname': t}
                d['_cen']  = opts['%s_cen'%t]
                d['vcen']  = opts['%s_cen_vary'%t]
                d['_step'] = opts['%s_step'%t]
                d['vstep'] = opts['%s_step_vary'%t]
                d['_tail'] = opts['%s_tail'%t]
                d['vtail'] = opts['%s_tail_vary'%t]
                d['_gamma'] = opts['%s_gamma'%t]
                d['vgamma'] = opts['%s_gamma_vary'%t]
                d['_sigma'] = opts['%s_sigma'%t]
                d['vsigma'] = opts['%s_sigma_vary'%t]
                script.append(xrfmod_scattpeak.format(**d))

        for i in range(1, NFILTERS+1):
            t = 'filt%d' % i
            f_mat = opts['%s_mat'%t]
            if f_mat not in (None, 'None') and int(1e6*opts['%s_thk'%t]) > 1:
                script.append(xrfmod_filter.format(name=f_mat,
                                                   thick=opts['%s_thk'%t],
                                                   vary=opts['%s_var'%t]))

        for layer in MATRIX_LAYERNAMES:
            t = 'matrix_%s' % layer
            m_mat = opts['%s_mat'%t].strip()
            if len(m_mat) > 0 and int(1e6*opts['%s_thk'%t]) > 1:
                script.append(xrfmod_matrix.format(name=m_mat,
                                                   thick=opts['%s_thk'%t],
                                                   density=opts['%s_den'%t]))

        if opts.get('bgr_use', False) in ('True', True):
            bwid = self.wids['bgr_width'].GetValue()/1000.0
            bexp = int(self.wids['bgr_expon'].GetStringSelection())
            script.append(xrfmod_bgr.format(group=self.mcagroup, bwid=bwid, bexp=bexp))

        if opts['pileup_use'] in ('True', True):
            script.append(xrfmod_pileup.format(scale=opts['pileup_amp'],
                                               vary=opts['pileup_amp_vary']))

        if opts['escape_use'] in ('True', True):
            script.append(xrfmod_escape.format(scale=opts['escape_amp'],
                                               vary=opts['escape_amp_vary']))

        # sort elements selected on Periodic Table by Z
        elemz = []
        for elem in self.ptable.selected:
            elemz.append( 1 + self.ptable.syms.index(elem))
        elemz.sort()
        syms = ["'%s'" % self.ptable.syms[iz-1] for iz in sorted(elemz)]
        syms = '[%s]' % (', '.join(syms))
        script.append(xrfmod_elems.format(elemlist=syms))
        script.append("{group:s}.xrf_init = _xrfmodel.calc_spectrum({group:s}.energy_ev)")
        script = '\n'.join(script)
        self.model_script = script.format(group=self.mcagroup)

        self._larch.eval(self.model_script)

        cmds = []
        self.xrfmod = self._larch.symtable.get_symbol('_xrfmodel')
        floor = 1.e-12*max(self.mca.counts)
        if match_amplitudes:
            total = 0.0 * self.mca.counts
            for name, parr in self.xrfmod.comps.items():
                nam = name.lower()
                imax = np.where(parr == parr.max())[0][0]
                scale = self.mca.counts[imax] / (parr[imax]+1.e-5)
                ampname = 'amp_%s' % nam
                if nam in ('elastic', 'compton1', 'compton2', 'compton',
                           'background', 'pileup', 'escape'):
                    ampname = '%s_amp' % nam
                    if nam in ('background', 'pileup', 'escape'):
                        scale = 1.0
                paramval = self.xrfmod.params[ampname].value
                s = "_xrfmodel.params['%s'].value = %.5f" % (ampname, paramval*scale)
                cmds.append(s)
                parr *= scale
                parr[np.where(parr<floor)] = floor
                total += parr
            self.xrfmod.current_model = total
            script = '\n'.join(cmds)
            self._larch.eval(script)
            self.model_script = "%s\n%s" % (self.model_script, script)
        s = "{group:s}.xrf_init = _xrfmodel.calc_spectrum({group:s}.energy_ev)"
        self._larch.eval(s.format(group=self.mcagroup))


    def plot_model(self, model_spectrum=None, init=False, with_comps=True,
                   label=None):
        conf = self.parent.conf

        plotkws = {'linewidth': 2.5, 'delay_draw': True, 'grid': False,
                   'ylog_scale': self.parent.ylog_scale, 'show_legend': False,
                   'fullbox': False}

        ppanel = self.parent.panel
        ppanel.conf.reset_trace_properties()
        self.parent.plot(self.mca.energy, self.mca.counts, mca=self.mca,
                         xlabel='E (keV)', xmin=0, with_rois=False, **plotkws)

        if model_spectrum is None:
            model_spectrum = self.xrfmod.current_model if init else self.xrfmod.best_fit
        if label is None:
            label = 'predicted model' if init else 'best fit'

        self.parent.oplot(self.mca.energy, model_spectrum,
                          label=label, color=conf.fit_color, **plotkws)

        if with_comps:
            for label, arr in self.xrfmod.comps.items():
                ppanel.oplot(self.mca.energy, arr, label=label, **plotkws)

        yscale = {False:'linear', True:'log'}[self.parent.ylog_scale]
        ppanel.set_logscale(yscale=yscale)
        ppanel.set_viewlimits()
        ppanel.conf.set_legend_location('upper right', True)
        ppanel.conf.draw_legend(show=True, delay_draw=False)

    def onShowModel(self, event=None):
        self.build_model()
        self.plot_model(init=True, with_comps=True)

    def onFitIteration(self, iter=0, pars=None):
        pass
        # print("Fit iteration %d" % iter)
        # self.wids['fit_message'].SetLabel("Fit iteration %d" % iter)

    def onFitModel(self, event=None):
        self.build_model()
        xrfmod = self._larch.symtable.get_symbol('_xrfmodel')
        xrfmod.iter_callback = self.onFitIteration
        fit_script = xrfmod_fitscript.format(group=self.mcagroup,
                                             emin=self.wids['en_min'].GetValue(),
                                             emax=self.wids['en_max'].GetValue())

        self._larch.eval(fit_script)
        dgroup = self._larch.symtable.get_group(self.mcagroup)
        xrfresult = self._larch.symtable.get_symbol('_xrfresult')

        xrfresult.script = "%s\n%s" % (self.model_script, fit_script)
        xrfresult.label = "fit %d" % (1+len(dgroup.fit_history))

        append_hist = "{group:s}.fit_history.append(_xrfresult)"
        self._larch.eval(append_hist.format(group=self.mcagroup))

        self.plot_model(init=True, with_comps=True)
        for i in range(len(self.nb.pagelist)):
            if 'Results' in self.nb.GetPageText(i):
                self.nb.SetSelection(i)
        time.sleep(0.002)
        self.show_results()

    def onClose(self, event=None):
        self.Destroy()

    def onSaveFitResult(self, event=None):
        result = self.get_fitresult()

        deffile = self.mca.filename + '_' + result.label
        deffile = fix_filename(deffile.replace('.', '_')) + '_xrf.modl'
        ModelWcards = "XRF Models(*.modl)|*.modl|All files (*.*)|*.*"
        sfile = FileSave(self, 'Save XRF Model', default_file=deffile,
                         wildcard=ModelWcards)
        if sfile is not None:
            self._larch.eval(xrfmod_jsondump.format(group=self.mcagroup,
                                                    nfit=self.nfit,
                                                    filename=sfile))

    def onExportFitResult(self, event=None):
        result = self.get_fitresult()
        deffile = self.mca.filename + '_' + result.label
        deffile = fix_filename(deffile.replace('.', '_')) + '_xrf.txt'
        wcards = 'All files (*.*)|*.*'
        outfile = FileSave(self, 'Export Fit Result', default_file=deffile)
        if outfile is not None:
            buff = ['# XRF Fit %s: %s' % (self.mca.filename, result.label),
                    '## Fit Script:']
            for a in result.script.split('\n'):
                buff.append('#   %s' % a)
            buff.append('## Fit Report:')
            for a in result.fit_report.split('\n'):
                buff.append('#   %s' % a)

            buff.append('#')
            buff.append('########################################')

            labels = ['energy', 'counts', 'best_fit',
                      'best_energy', 'fit_window',
                      'fit_weight', 'attenuation']
            labels.extend(list(result.comps.keys()))

            buff.append('# %s' % (' '.join(labels)))

            npts = len(self.mca.energy)
            for i in range(npts):
                dline = [gformat(self.mca.energy[i]),
                         gformat(self.mca.counts[i]),
                         gformat(result.best_fit[i]),
                         gformat(result.best_en[i]),
                         gformat(result.fit_window[i]),
                         gformat(result.fit_weight[i]),
                         gformat(result.atten[i])]
                for c in result.comps.values():
                    dline.append(gformat(c[i]))
                buff.append(' '.join(dline))
            buff.append('\n')
            with open(outfile, 'w') as fh:
                fh.write('\n'.join(buff))

    def get_fitresult(self, nfit=None):
        if nfit is None:
            nfit = self.nfit
        self.fit_history = getattr(self.mca, 'fit_history', [])
        self.nfit = max(0, nfit)
        if self.nfit > len(self.fit_history):
            self.nfit = 0
        return self.fit_history[self.nfit]

    def onChangeFitLabel(self, event=None):
        label = self.rwids['fitlabel_txt'].GetValue()
        result = self.get_fitresult()
        result.label = label
        self.show_results()

    def onPlot(self, event=None):
        result = self.get_fitresult()
        xrfmod = self._larch.symtable.get_symbol('_xrfmodel')
        with_comps = self.rwids['plot_comps'].IsChecked()
        spect = xrfmod.calc_spectrum(self.mca.energy_ev,
                                     params=result.params)
        self.plot_model(model_spectrum=spect, with_comps=with_comps,
                        label=result.label)

    def onSelectFit(self, evt=None):
        if self.rwids['stats'] is None:
            return
        item = self.rwids['stats'].GetSelectedRow()
        if item > -1:
            self.show_fitresult(nfit=item)

    def onSelectParameter(self, evt=None):
        if self.rwids['params'] is None:
            return
        if not self.rwids['params'].HasSelection():
            return
        item = self.rwids['params'].GetSelectedRow()
        pname = self.rwids['paramsdata'][item]

        cormin= self.rwids['min_correl'].GetValue()
        self.rwids['correl'].DeleteAllItems()

        result = self.get_fitresult()
        this = result.params[pname]
        if this.correl is not None:
            sort_correl = sorted(this.correl.items(), key=lambda it: abs(it[1]))
            for name, corval in reversed(sort_correl):
                if abs(corval) > cormin:
                    self.rwids['correl'].AppendItem((pname, name, "% .4f" % corval))

    def onAllCorrel(self, evt=None):
        result = self.get_fitresult()
        params = result.params
        parnames = list(params.keys())

        cormin= self.rwids['min_correl'].GetValue()
        correls = {}
        for i, name in enumerate(parnames):
            par = params[name]
            if not par.vary:
                continue
            if hasattr(par, 'correl') and par.correl is not None:
                for name2 in parnames[i+1:]:
                    if (name != name2 and name2 in par.correl and
                            abs(par.correl[name2]) > cormin):
                        correls["%s$$%s" % (name, name2)] = par.correl[name2]

        sort_correl = sorted(correls.items(), key=lambda it: abs(it[1]))
        sort_correl.reverse()

        self.rwids['correl'].DeleteAllItems()

        for namepair, corval in sort_correl:
            name1, name2 = namepair.split('$$')
            self.rwids['correl'].AppendItem((name1, name2, "% .4f" % corval))

    def show_results(self):
        cur = self.get_fitresult()
        self.rwids['stats'].DeleteAllItems()
        for i, res in enumerate(self.fit_history):
            args = [res.label]
            for attr in ('nvarys', 'nfev', 'chisqr', 'redchi', 'aic'):
                val = getattr(res, attr)
                if isinstance(val, int):
                    val = '%d' % val
                else:
                    val = gformat(val, 11)
                args.append(val)
            self.rwids['stats'].AppendItem(tuple(args))
        self.rwids['data_title'].SetLabel(self.mca.filename)
        self.rwids['fitlabel_txt'].SetValue(cur.label)
        self.show_fitresult(nfit=0)

    def show_fitresult(self, nfit=0, mca=None):
        if mca is not None:
            self.mca = mca
        result = self.get_fitresult(nfit=nfit)

        self.rwids['data_title'].SetLabel(self.mca.filename)
        self.result = result
        self.rwids['fitlabel_txt'].SetValue(result.label)
        self.rwids['params'].DeleteAllItems()
        self.rwids['paramsdata'] = []
        for param in reversed(result.params.values()):
            pname = param.name
            try:
                val = gformat(param.value, 10)
            except (TypeError, ValueError):
                val = ' ??? '

            serr = ' N/A '
            if param.stderr is not None:
                serr = gformat(param.stderr, 10)
            extra = ' '
            if param.expr is not None:
                extra = ' = %s ' % param.expr
            elif not param.vary:
                extra = ' (fixed)'
            elif param.init_value is not None:
                extra = ' (init=%s)' % gformat(param.init_value, 8)

            self.rwids['params'].AppendItem((pname, val, serr, extra))
            self.rwids['paramsdata'].append(pname)
        self.Refresh()
