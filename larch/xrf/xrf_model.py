
from collections import namedtuple
import time
import json
import numpy as np
from numpy.linalg import lstsq
from scipy.optimize import nnls
from lmfit import  Parameters, minimize, fit_report

from xraydb import (material_mu, mu_elam, ck_probability, xray_edge,
                    xray_edges, xray_lines, xray_line)
from xraydb.xray import XrayLine

from .. import Group
from ..math import index_of, interp, savitzky_golay, hypermet, erfc
from ..xafs import ftwindow
from ..utils import group2dict, json_dump

xrf_prediction = namedtuple("xrf_prediction", ("weights", "prediction"))
xrf_peak = namedtuple('xrf_peak', ('name', 'amplitude', 'center', 'step',
                                   'tail', 'sigmax', 'beta', 'gamma',
                                   'vary_center', 'vary_step', 'vary_tail',
                                   'vary_sigmax', 'vary_beta', 'vary_gamma'))

####
# Note on units:  energies are in keV, lengths in cm
#
####
HAS_PINT = False

# note on Fano Factors
# efano = (energy to create e-h pair)  * FanoFactor
# material     E-h excitation (eV)   Fano Factor  EFano (keV)
#    Si              3.66              0.115      0.000 4209
#    Ge              3.0               0.130      0.000 3900
FanoFactors = {'Si':  0.4209e-3, 'Ge': 0.3900e-3}

def is_pint_quantity(val):
    return HAS_PINT and isinstance(val, pint.quantity._Quantity)

class XRF_Material:
    def __init__(self, material='Si', thickness=0.050, density=None,
                 thickness_units='mm'):
        self.material = material
        self.density = density
        self.thickness_units = thickness_units
        self.thickness = thickness
        if HAS_PINT:
            self.thickness_units = getattr(pint.UnitRegistry(), thickness_units)
            self.thickness = thickness * self.thickness_units

        self.mu_total = self.mu_photo = None

    def calc_mu(self, energy):
        "calculate mu for energy in keV"
        # note material_mu works in eV!
        self.mu_total = material_mu(self.material, 1000*energy,
                                    density=self.density,
                                    kind='total')
        self.mu_photo = material_mu(self.material, 1000*energy,
                                    density=self.density,
                                    kind='photo')

    def absorbance(self, energy, thickness=None, kind='total'):
        """calculate absorbance (fraction absorbed)

        Arguments
        ----------
        energy      float or ndarray  energy (keV) of X-ray
        thicknesss  float or pint.Quantity   material thickness (cm)

        Returns
        -------
        fraction of X-rays absorbed by material
        """
        if thickness is None:
            thickness = self.thickness
        if self.mu_total is None:
            self.calc_mu(energy)
        mu = self.mu_total
        if kind == 'photo':
            mu = self.mu_photo
        if is_pint_quantity(thickness):
            t = thickness.to('cm').magnitude
        else:
            t = 0.1*thickness
        return (1.0 - np.exp(-t*mu))

    def transmission(self, energy, thickness=None, kind='total'):
        """calculate transmission (fraction transmitted through material)

        Arguments
        ---------
        energy      float or ndarray energy (keV) of X-ray
        thicknesss  float or pint.Quantity   material thickness (cm)

        Returns
        -------
        fraction of X-rays transmitted through material
        """

        if thickness is None:
            thickness = self.thickness
        if self.mu_total is None:
            self.calc_mu(energy)
        mu = self.mu_total
        if kind == 'photo':
            mu = self.mu_photo
        if is_pint_quantity(thickness):
            t = thickness.to('cm').magnitude
        else:
            t = 0.1*thickness
        return np.exp(-t*mu)


class XRF_Element:
    def __init__(self, symbol, xray_energy=None, energy_min=1.5,
                 overlap_energy=None):
        self.symbol = symbol
        self.xray_energy = xray_energy
        self.mu = 1.0
        self.edges = ['K']
        self.fyields = {}
        if xray_energy is not None:
            self.mu = mu_elam(symbol, 1000*xray_energy, kind='photo')

            self.edges = []
            for ename, xedge in xray_edges(self.symbol).items():
                if ename.lower() in ('k', 'l1', 'l2', 'l3', 'm5'):
                    edge_kev = 0.001*xedge.energy
                    if (edge_kev < xray_energy and
                        edge_kev > energy_min):
                        self.edges.append(ename)
                        self.fyields[ename] = xedge.fyield

        # currently, we consider only one edge per element
        if 'K' in self.edges:
            self.edges = ['K']
        if 'L3' in self.edges:
            tmp = []
            for ename in self.edges:
                if ename.lower().startswith('l'):
                    tmp.append(ename)
            self.edges = tmp

        # apply CK corrections to fluorescent yields
        if 'L3' in self.edges:
            nlines = 1.0
            ck13 = ck_probability(symbol, 'L1', 'L3')
            ck12 = ck_probability(symbol, 'L1', 'L2')
            ck23 = ck_probability(symbol, 'L2', 'L3')
            fy3  = self.fyields['L3']
            fy2  = self.fyields.get('L2', 0)
            fy1  = self.fyields.get('L1', 0)
            if 'L2' in self.edges:
                nlines = 2.0
                fy3 = fy3 + fy2*ck23
                fy2 = fy2 * (1 - ck23)
                if 'L1' in self.edges:
                    nlines = 3.0
                    fy3 = fy3 + fy1 * (ck13 + ck12*ck23)
                    fy2 = fy2 + fy1 * ck12
                    fy1 = fy1 * (1 - ck12 - ck13 - ck12*ck23)
                    self.fyields['L1'] = fy1
                self.fyields['L2'] = fy2
            self.fyields['L3'] = fy3/nlines
            self.fyields['L2'] = fy2/nlines
            self.fyields['L1'] = fy1/nlines

        # look up X-ray lines, keep track of very close lines
        # so that they can be consolidate
        # slightly confusing (and working with XrayLine energies in ev)
        self.lines = {}
        self.all_lines = {}
        energy0 = None
        for ename in self.edges:
            for key, xline in xray_lines(symbol, ename).items():
                self.all_lines[key] = xline
                if xline.intensity > 0.002:
                    self.lines[key] = xline
                    if energy0 is None:
                        energy0 = xline.energy

        if overlap_energy is None:
            if xray_energy is None: xray_energy = 10.0
            if energy0 is not None: xray_energy = energy0
            # note: at this point xray_energy is in keV
            overlap_energy = 5.0*(2+np.sqrt(5 + xray_energy))

        # collect lines from the same initial level that are close in energy
        nlines = len(self.lines)
        combos = [[] for k in range(nlines)]
        comboe = [-1 for k in range(nlines)]
        combol = [None for k in range(nlines)]
        for key, xline in self.lines.items():
            assigned = False
            for i, en in enumerate(comboe):
                if (abs(0.001*xline.energy - en) < overlap_energy and
                    xline.initial_level == combol[i]):
                    combos[i].append(key)
                    assigned = True
                    break
            if not assigned:
                for k in range(nlines):
                    if comboe[k] < 0:
                        break
                combol[k] = xline.initial_level
                comboe[k] = xline.energy
                combos[k].append(key)

        # consolidate overlapping X-ray lines
        for comps in combos:
            if len(comps) > 0:
                key = comps[0]
                l0 = self.lines.pop(key)
                ilevel = l0.initial_level
                iweight = l0.intensity
                flevel = [l0.final_level]
                en = [l0.energy]
                wt = [l0.intensity]
                for other in comps[1:]:
                    lx = self.lines.pop(other)
                    if lx.intensity > iweight:
                        iweight = lx.intensity
                        ilevel  = lx.initial_level
                    flevel.append(lx.final_level)
                    en.append(lx.energy)
                    wt.append(lx.intensity)
                wt = np.array(wt)
                en = np.array(en)
                flevel = ', '.join(flevel)
                if len(comps) > 1:
                    newkey = key.replace('1', '').replace('2', '').replace('3', '')
                    newkey = newkey.replace('4', '').replace('5', '').replace(',', '')
                    if newkey not in self.lines:
                        key = newkey
                self.lines[key] = XrayLine(energy=(en*wt).sum()/wt.sum(),
                                           intensity=wt.sum(),
                                           initial_level=ilevel,
                                           final_level=flevel)


class XRF_Model:
    """model for X-ray fluorescence data

    consists of parameterized components for

      incident beam (energy, angle_in, angle_out)
      matrix        (list of material, thickness)
      filters       (list of material, thickness)
      detector      (material, thickness, step, tail, beta, gamma)
    """
    def __init__(self, xray_energy=None, energy_min=1.5, energy_max=30.,
                 count_time=1, bgr=None, iter_callback=None, **kws):

        self.xray_energy = xray_energy
        self.energy_min = energy_min
        self.energy_max = energy_max
        self.count_time = count_time
        self.iter_callback = None
        self.params = Parameters()
        self.elements = []
        self.scatter = []
        self.comps = {}
        self.eigenvalues = {}
        self.transfer_matrix = None
        self.matrix_layers = []
        self.matrix = None
        self.matrix_atten = 1.0
        self.filters = []
        self.fit_iter = 0
        self.fit_toler = 1.e-5
        self.fit_log = False
        self.bgr = None
        self.use_pileup = False
        self.use_escape = False
        self.escape_scale = None
        self.script = ''
        if bgr is not None:
            self.add_background(bgr)

    def set_detector(self, material='Si', thickness=0.40, noise=0.05,
                     peak_step=1e-3, peak_tail=0.01, peak_gamma=0,
                     peak_beta=0.5, cal_offset=0, cal_slope=10., cal_quad=0,
                     vary_thickness=False, vary_noise=True,
                     vary_peak_step=True, vary_peak_tail=True,
                     vary_peak_gamma=False, vary_peak_beta=False,
                     vary_cal_offset=True, vary_cal_slope=True,
                     vary_cal_quad=False):
        """
        set up detector material, calibration, and general settings for
        the hypermet functions for the fluorescence and scatter peaks
        """
        self.detector = XRF_Material(material, thickness)
        matname = material.title()
        if matname not in FanoFactors:
            matname = 'Si'
        self.efano = FanoFactors[matname]
        self.params.add('det_thickness', value=thickness, vary=vary_thickness, min=0)
        self.params.add('det_noise', value=noise, vary=vary_noise, min=0)
        self.params.add('cal_offset', value=cal_offset, vary=vary_cal_offset, min=-500, max=500)
        self.params.add('cal_slope', value=cal_slope, vary=vary_cal_slope, min=0)
        self.params.add('cal_quad', value=cal_quad, vary=vary_cal_quad)
        self.params.add('peak_step', value=peak_step, vary=vary_peak_step, min=0, max=10)
        self.params.add('peak_tail', value=peak_tail, vary=vary_peak_tail, min=0, max=10)
        self.params.add('peak_beta', value=peak_beta, vary=vary_peak_beta, min=0)
        self.params.add('peak_gamma', value=peak_gamma, vary=vary_peak_gamma, min=0)

    def add_scatter_peak(self, name='elastic', amplitude=1000, center=None,
                         step=0.010, tail=0.5, sigmax=1.0, beta=0.5,
                         vary_center=True, vary_step=True, vary_tail=True,
                         vary_sigmax=True, vary_beta=False):
        """add Rayleigh (elastic) or Compton (inelastic) scattering peak
        """
        if name not in self.scatter:
            self.scatter.append(xrf_peak(name, amplitude, center, step, tail,
                                         sigmax, beta, 0.0, vary_center, vary_step,
                                         vary_tail, vary_sigmax, vary_beta, False))

        if center is None:
            center = self.xray_energy

        self.params.add('%s_amp' % name,    value=amplitude, vary=True, min=0)
        self.params.add('%s_center' % name, value=center, vary=vary_center,
                        min=center*0.5, max=center*1.25)
        self.params.add('%s_step' % name,   value=step, vary=vary_step, min=0, max=10)
        self.params.add('%s_tail' % name,   value=tail, vary=vary_tail, min=0, max=20)
        self.params.add('%s_beta' % name,   value=beta, vary=vary_beta, min=0, max=20)
        self.params.add('%s_sigmax' % name, value=sigmax, vary=vary_sigmax,
                        min=0, max=100)

    def add_element(self, elem, amplitude=1.e6, vary_amplitude=True):
        """add Element to XRF model
        """
        self.elements.append(XRF_Element(elem, xray_energy=self.xray_energy,
                                         energy_min=self.energy_min))
        self.params.add('amp_%s' % elem.lower(), value=amplitude,
                        vary=vary_amplitude, min=0)

    def add_filter(self, material, thickness, density=None, vary_thickness=False):
        self.filters.append(XRF_Material(material=material,
                                         density=density,
                                         thickness=thickness))
        self.params.add('filterlen_%s' % material,
                        value=thickness, min=0, vary=vary_thickness)

    def set_matrix(self, material, thickness, density=None):
        self.matrix = XRF_Material(material=material, density=density,
                                   thickness=thickness)
        self.matrix_atten = 1.0

    def add_background(self, data, vary=True):
        self.bgr = data
        self.params.add('background_amp', value=1.0, min=0, vary=vary)

    def add_escape(self, scale=1.0, vary=True):
        self.use_escape = True
        self.params.add('escape_amp', value=scale, min=0, vary=vary)

    def add_pileup(self, scale=1.0, vary=True):
        self.use_pileup = True
        self.params.add('pileup_amp', value=scale, min=0, vary=vary)

    def clear_background(self):
        self.bgr = None
        self.params.pop('background_amp')

    def calc_matrix_attenuation(self, energy):
        """
        calculate beam attenuation by a matrix built from layers
        note that matrix layers and composition cannot be variable
        so the calculation can be done once, ahead of time.
        """
        atten = 1.0
        if self.matrix is not None:
            ixray_en = index_of(energy, self.xray_energy)
            print("MATRIX ", ixray_en, self.matrix)
           # layer_trans = self.matrix.transmission(energy) # transmission through layer
            # incid_trans = layer_trans[ixray_en] # incident beam trans to lower layers
            # ncid_absor = 1.0 - incid_trans     # incident beam absorption by layer
            # atten = layer_trans * incid_absor
        self.matrix_atten = atten

    def calc_escape_scale(self, energy, thickness=None):
        """
        calculate energy dependence of escape effect

        X-rays penetrate a depth 1/mu(material, energy) and the
        detector fluorescence escapes from that depth as
            exp(-mu(material, KaEnergy)*thickness)
        with a fluorecence yield of the material

        """
        det = self.detector
        # note material_mu, xray_edge, xray_line work in eV!
        escape_energy_ev = xray_line(det.material, 'Ka').energy
        mu_emit = material_mu(det.material, escape_energy_ev)
        self.escape_energy = 0.001 * escape_energy_ev

        mu_input = material_mu(det.material, 1000*energy)

        edge = xray_edge(det.material, 'K')
        self.escape_scale = edge.fyield * np.exp(-mu_emit / (2*mu_input))
        self.escape_scale[np.where(energy < 0.001*edge.energy)] = 0.0

    def det_sigma(self, energy, noise=0):
        """ energy width of peak """
        return np.sqrt(self.efano*energy + noise**2)

    def calc_spectrum(self, energy, params=None):
        if params is None:
            params = self.params
        pars = params.valuesdict()
        self.comps = {}
        self.eigenvalues = {}

        det_noise = pars['det_noise']
        step = pars['peak_step']
        tail = pars['peak_tail']
        beta = pars['peak_beta']
        gamma = pars['peak_gamma']

        # detector attenuation
        atten = self.detector.absorbance(energy, thickness=pars['det_thickness'])

        # filters
        for f in self.filters:
           thickness = pars.get('filterlen_%s' % f.material, None)
           if thickness is not None and int(thickness*1e6) > 1:
               atten *= f.transmission(energy, thickness=thickness)
        self.atten = atten
        # matrix
        # if self.matrix_atten is None:
        #     self.calc_matrix_attenuation(energy)
        # atten *= self.matrix_atten
        if self.use_escape:
            if self.escape_scale is None:
                self.calc_escape_scale(energy, thickness=pars['det_thickness'])
            escape_amp = pars.get('escape_amp', 0.0) * self.escape_scale

        for elem in self.elements:
            comp = 0. * energy
            amp = pars.get('amp_%s' % elem.symbol.lower(), None)
            if amp is None:
                continue
            for key, line in elem.lines.items():
                ecen = 0.001*line.energy
                line_amp = line.intensity * elem.mu * elem.fyields[line.initial_level]
                sigma = self.det_sigma(ecen, det_noise)
                comp += hypermet(energy, amplitude=line_amp, center=ecen,
                                 sigma=sigma, step=step, tail=tail,
                                 beta=beta, gamma=gamma)
            comp *= amp * atten * self.count_time
            if self.use_escape:
                comp += escape_amp * interp(energy-self.escape_energy, comp, energy)

            self.comps[elem.symbol] = comp
            self.eigenvalues[elem.symbol] = amp

        # scatter peaks for Rayleigh and Compton
        for peak in self.scatter:
            p = peak.name
            amp  = pars.get('%s_amp' % p, None)
            if amp is None:
                continue
            ecen = pars['%s_center' % p]
            step = pars['%s_step' % p]
            tail = pars['%s_tail' % p]
            beta = pars['%s_beta' % p]
            sigma = pars['%s_sigmax' % p]
            sigma *= self.det_sigma(ecen, det_noise)
            comp = hypermet(energy, amplitude=1.0, center=ecen,
                            sigma=sigma, step=step, tail=tail, beta=beta,
                            gamma=gamma)
            comp *= amp * atten * self.count_time
            if self.use_escape:
                comp += escape_amp * interp(energy-self.escape_energy, comp, energy)
            self.comps[p] = comp
            self.eigenvalues[p] = amp

        if self.bgr is not None:
            bgr_amp = pars.get('background_amp', 0.0)
            self.comps['background'] = bgr_amp * self.bgr
            self.eigenvalues['background'] = bgr_amp

        # calculate total spectrum
        total = 0. * energy
        for comp in self.comps.values():
            total += comp

        if self.use_pileup:
            pamp = pars.get('pileup_amp', 0.0)
            npts = len(energy)
            pileup = pamp*1.e-9*np.convolve(total, total*1.0, 'full')[:npts]
            self.comps['pileup'] = pileup
            self.eigenvalues['pileup'] = pamp
            total += pileup

        # remove tiny values so that log plots are usable
        floor = 1.e-10*max(total)
        total[np.where(total<floor)] = floor
        self.current_model = total
        return total

    def __resid(self, params, data, index):
        pars = params.valuesdict()
        self.best_en = (pars['cal_offset'] + pars['cal_slope'] * index +
                        pars['cal_quad'] * index**2)
        self.fit_iter += 1
        model = self.calc_spectrum(self.best_en, params=params)
        if callable(self.iter_callback):
            self.iter_callback(iter=self.fit_iter, pars=pars)
        return ((data - model) * self.fit_weight)[self.imin:self.imax]


    def set_fit_weight(self, energy, counts, emin, emax, ewid=25.0):
        """
        set weighting factor to smoothed square-root of data
        """
        ewin = ftwindow(energy, xmin=emin, xmax=emax, dx=ewid, window='hanning')
        self.fit_window = ewin
        stderr = np.sqrt(counts + 1)
        self.fit_weight = ewin / (0.1 + savitzky_golay(stderr, 7, 2))

    def fit_spectrum(self, energy, counts, energy_min=None, energy_max=None):
        work_energy = 1.0*energy
        work_counts = 1.0*counts
        floor = 1.e-10*np.percentile(counts, [99])[0]
        work_counts[np.where(counts<floor)] = floor

        if max(energy) > 250.0: # if input energies are in eV
            work_energy = 0.001 * energy

        imin, imax = 0, len(counts)
        if energy_min is None:
            energy_min = self.energy_min
        if energy_min is not None:
            imin = index_of(work_energy, energy_min)
        if energy_max is None:
            energy_max = self.energy_max
        if energy_max is not None:
            imax = index_of(work_energy, energy_max)

        self.imin = max(0, imin-5)
        self.imax = min(len(counts), imax+5)
        self.npts = (self.imax - self.imin)
        self.set_fit_weight(work_energy, work_counts, energy_min, energy_max)
        self.fit_iter = 0

        # reset attenuation calcs for matrix, detector, filters
        self.matrix_atten = 1.0
        self.escape_scale = None
        self.detector.mu_total = None
        for f in self.filters:
            f.mu_total = None

        self.init_fit = self.calc_spectrum(energy, params=self.params)
        index = np.arange(len(counts))
        userkws = dict(data=work_counts, index=index)

        tol = self.fit_toler
        self.result = minimize(self.__resid, self.params, kws=userkws,
                               method='leastsq', maxfev=10000, scale_covar=True,
                               gtol=tol, ftol=tol, epsfcn=1.e-5)

        self.fit_report = fit_report(self.result, min_correl=0.5)
        pars = self.result.params

        self.best_en = (pars['cal_offset'] + pars['cal_slope'] * index +
                        pars['cal_quad'] * index**2)
        self.fit_iter += 1
        self.best_fit = self.calc_spectrum(energy, params=self.result.params)

        # calculate transfer matrix for linear analysis using this model
        tmat= []
        for key, val in self.comps.items():
            arr = val / self.eigenvalues[key]
            floor = 1.e-12*max(arr)
            arr[np.where(arr<floor)] = 0.0
            tmat.append(arr)
        self.transfer_matrix = np.array(tmat).transpose()

    def apply_model(self, spectrum):
        """
        apply fitted model to another spectrum,
        returning a dict of predicted eigenvalues
        for the supplied spectrum
        """
        if self.transfer_matrix is None:
            raise ValueError("need to fit a spectrum first")

        wts, rnorm = nnls(self.transfer_matrix, spectrum*self.fit_window)

        weights = {}
        prediction = 0.0*spectrum[:]
        for i, name in enumerate(self.eigenvalues.keys()):
            weights[name] = wts[i]
            prediction += wts[i] * self.transfer_matrix[:, i]

        return xrf_prediction(weights, prediction)

    def apply_to_map(self, mapdata):
        """
        apply fitted model to  NY x NX array of spectra as from an XRF Map
        returning a dict of predicted maps for the supplied spectrum
        """
        if self.transfer_matrix is None:
            raise ValueError("need to fit a spectrum first")

        ny, nx, nchan = mapdata.shape
        nchanx, ncomps = self.transfer_matrix.shape
        nchanw = self.fit_window.shape[0]
        if nchan != nchanx or nchan != nchanw:
            raise ValueError("mapdata has wrong shape ", mapdata.shape)

        pred = np.zeros((ny, nx, ncomps), dtype='float32')
        print(ny, nx, ncomps)
        t0 = time.time()
        for iy in range(ny):
            print(iy)
            for ix in range(nx):
                wts, rnorm = nnls(self.transfer_matrix,
                                  mapdata[iy,ix,:]*self.fit_window)
                for i in range(ncomps):
                    pred[iy,ix,i] = wts[i]

        maps = {}
        for i, name in enumerate(self.eigenvalues.keys()):
            maps[name] = pred[:,:,i]
        print("Done %.2f sec " % (time.time()-t0))
        return maps

    def compile_fitresults(self, label='fit result', script='# noscript'):
        """a simple compilation of fit settings results
        to be able to easily save and inspect"""
        out = Group(label=label, script=script)
        for attr in ('params', 'var_names', 'chisqr', 'redchi', 'nvarys',
                     'nfev', 'ndata', 'aic', 'bic', 'aborted', 'covar', 'ier',
                     'message', 'method', 'nfree', 'init_values', 'success',
                     'residual', 'errorbars', 'lmdif_message', 'nfree'):
            setattr(out, attr, getattr(self.result, attr, None))

        for attr in ('atten', 'best_en', 'best_fit', 'bgr', 'comps', 'count_time',
                     'eigenvalues', 'energy_max', 'energy_min', 'fit_iter', 'fit_log',
                     'fit_report', 'fit_toler', 'fit_weight', 'fit_window', 'init_fit',
                     'scatter', 'script', 'transfer_matrix', 'xray_energy'):
            setattr(out, attr, getattr(self, attr, None))

        elem_attrs = ('all_lines', 'edges', 'fyields', 'lines', 'mu',
                      'symbol', 'xray_energy')
        out.elements = []
        for el in self.elements:
            out.elements.append({attr: getattr(el, attr) for attr in elem_attrs})

        mater_attrs = ('material', 'mu_photo', 'mu_total', 'thickness')
        out.detector = {attr: getattr(self.detector, attr) for attr in mater_attrs}
        out.matrix = None
        if self.matrix is not None:
            out.matrix = {attr: getattr(self.matrix, attr) for attr in mater_attrs}
        out.filters = []
        for ft in self.filters:
            out.filters.append({attr: getattr(ft, attr) for attr in mater_attrs})
        # out.matrix_layers = []
        return out

    def save(self, fname=None):
        """save XRF model and result in a manner that can be loaded later"""
        result = group2dict(self.compile_fitresults())
        result['params'] = result.pop('params').dumps()
        if fname is not None:
            json_dump(result, filename=fname)
        else:
            return result

    def load(self, s):
        """load a saved XRF model from a string (json)"""
        pass

    def export(self, fname):
        """save result to text file"""
        result = group2dict(self.compile_fitresults())


def xrf_model(xray_energy=None, energy_min=1500, energy_max=None, use_bgr=False, **kws):
    """create an XRF Peak

    Returns:
    ---------
     an XRF_Model instance
    """

    return XRF_Model(xray_energy=xray_energy, use_bgr=use_bgr,
                     energy_min=energy_min, energy_max=energy_max, **kws)
