

import numpy as np
from numpy.linalg import lstsq

from lmfit import  Parameters, minimize, fit_report

from ..math import index_of, savitzky_golay, hypermet, erfc
from ..xray import (atomic_mass, atomic_symbol, material_mu, mu_elam,
                    xray_edges, xray_lines, ck_probability)
from ..xafs import ftwindow

########
# Note on units:  energies are in eV, lengths in cm
#
# For many XRF Analysis needs, energies are in keV
####

class XRF_Material:
    def __init__(self, material='Si', thickness=0.050, efano=None, noise=10.):
        self.material = material
        self.thickness = thickness
        self.mu_total = self.mu_photo = None
        # note on efano:
        # self.efano = (energy to create e-h pair)  * FanoFactor
        # material     E-h excitation (eV)   Fano Factor
        #    Si              3.66              0.115
        #    Ge              3.0               0.130
        if efano is None:
            efano = 0.0
            if material.lower().startswith('si'):
                efano = 3.66 * 0.115
            elif material.lower().startswith('ge'):
                efano = 3.0 * 0.130
        self.efano = efano
        self.noise = noise

    def sigma(self, energy, efano=None, noise=None):
        """ energy width of peak """
        if efano is None:
            efano = self.efano
        if noise is None:
            noise = self.noise
        return np.sqrt(efano*energy + noise**2)

    def calc_mu(self, energy):
        self.mu_total = material_mu(self.material, energy, kind='total')
        self.mu_photo = material_mu(self.material, energy, kind='photo')

    def absorbance(self, energy, thickness=None, kind='total'):
        """calculate absorbance (fraction absorbed)

        Arguments
        ----------
        energy      float or ndarray   energy (eV) of X-ray
        thicknesss  float    material thickness (cm)

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
        return (1.0 - np.exp(-self.thickness*mu))


    def attenuation(self, energy, thickness=None, kind='total'):
        """calculate attenuation (fraction attenuated)

        Arguments
        ----------
        energy      float or ndarray   energy (eV) of X-ray
        thicknesss  float    material thickness (cm)

        Returns
        -------
        fraction of X-rays attenuated by material
        """

        if thickness is None:
            thickness = self.thickness
        if self.mu_total is None:
            self.calc_mu(energy)
        mu = self.mu_total
        if kind == 'photo':
            mu = self.mu_photo
        return np.exp(-thickness*mu)


class XRF_Element:
    def __init__(self, symbol, xray_energy=None, energy_min=1500):
        self.symbol = symbol
        self.xray_energy = xray_energy
        self.mu = 1.0
        self.edges = ['K']
        self.fyields = {}

        if xray_energy is not None:
            self.mu = mu_elam(symbol, xray_energy, kind='photo')

            self.edges = []
            for ename, xedge in xray_edges(self.symbol).items():
                if ename.lower() in ('k', 'l1', 'l2', 'l3', 'm5'):
                    edge_ev = xedge.edge
                    if (edge_ev < xray_energy and
                        edge_ev > energy_min):
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
            ck13 = ck_probability(symbol, 'L1', 'L3')
            ck12 = ck_probability(symbol, 'L1', 'L2')
            ck23 = ck_probability(symbol, 'L2', 'L3')
            fy3  = self.fyields['L3']
            fy2  = self.fyields.get('L2', 0)
            fy1  = self.fyields.get('L1', 0)
            if 'L2' in self.edges:
                fy3 = fy3 + fy2*ck23
                fy2 = fy2 * (1 - ck23)
                if 'L1' in self.edges:
                    fy3 = fy3 + fy1 * (ck13 + ck12*ck23)
                    fy2 = fy2 + fy1 * ck12
                    fy1 = fy1 * (1 - ck12 - ck13)
                    self.fyields['L1'] = fy1
                self.fyields['L2'] = fy2
            self.fyields['L3'] = fy3
        # look up xray lines
        self.lines = {}
        for ename in self.edges:
            self.lines.update(xray_lines(symbol, ename))


class XRF_Model:
    """model for X-ray fluorescence data

    consists of parameterized components for

      incident beam (energy, angle_in, angle_out)
      matrix        (list of material, thickness)
      filters       (list of material, thickness)
      detector      (material, thickness, efano, noise, step, tail, gamma, pileup_scale)
    """
    def __init__(self, xray_energy=None, energy_min=1500, energy_max=30000,
                 count_time=1, bgr=None, **kws):

        self.xray_energy = xray_energy
        self.energy_min = energy_min
        self.energy_max = energy_max
        self.count_time = count_time
        self.params = Parameters()
        self.elements = []
        self.scatter = []
        self.comps = {}
        self.eigenvalues = {}
        self.transfer_matrix = None
        self.filters = []
        self.fit_iter = 0
        self.fit_toler = 1.e-5
        self.fit_log = False
        self.bgr = None
        if bgr is not None:
            self.add_background(bgr)

    def set_detector(self, material='Si', thickness=0.025, efano=None,
                     noise=30., peak_step=1e-4, peak_tail=0.01,
                     peak_gamma=0.5, cal_offset=0, cal_slope=10.,
                     cal_quad=0, vary_thickness=False, vary_efano=False,
                     vary_noise=True, vary_peak_step=True,
                     vary_peak_tail=True, vary_peak_gamma=False,
                     vary_cal_offset=True, vary_cal_slope=True,
                     vary_cal_quad=False):

        self.detector = XRF_Material(material, thickness, efano=efano, noise=noise)
        self.params.add('det_thickness', value=thickness, vary=vary_thickness, min=0)
        self.params.add('det_efano', value=self.detector.efano, vary=vary_efano, min=0)
        self.params.add('det_noise', value=noise, vary=vary_noise, min=0)
        self.params.add('cal_offset', value=cal_offset, vary=vary_cal_offset, min=-500, max=500)
        self.params.add('cal_slope', value=cal_slope, vary=vary_cal_slope, min=0)
        self.params.add('cal_quad', value=cal_quad, vary=vary_cal_quad)
        self.params.add('peak_step', value=peak_step, vary=vary_peak_step, min=0, max=0.25)
        self.params.add('peak_tail', value=peak_tail, vary=vary_peak_tail, min=0, max=0.25)
        self.params.add('peak_gamma', value=peak_gamma, vary=vary_peak_gamma, min=0)

    def add_scatter_peak(self, name='elastic', amplitude=1000, center=None,
                         step=0.010, tail=0.5, sigmax=1.0, gamma=0.75,
                         vary_center=True, vary_step=True, vary_tail=True,
                         vary_sigmax=True, vary_gamma=False):
        """add Rayleigh (elastic) or Compton (inelastic) scattering peak
        """
        if name not in self.scatter:
            self.scatter.append(name)

        if center is None:
            center = self.xray_energy

        self.params.add('%s_amp' % name,    value=amplitude, vary=True, min=0)
        self.params.add('%s_center' % name, value=center, vary=vary_center,
                        min=center*0.8, max=center*1.2)
        self.params.add('%s_step' % name,   value=step, vary=vary_step, min=0, max=10)
        self.params.add('%s_tail' % name,   value=tail, vary=vary_tail, min=0, max=20)
        self.params.add('%s_gamma' % name,  value=gamma, vary=vary_gamma, min=0, max=10)
        self.params.add('%s_sigmax' % name, value=sigmax, vary=vary_sigmax,
                        min=0, max=100)

    def add_element(self, elem, amplitude=1.0, vary_amplitude=True):
        """add Element to XRF model
        """
        xelem = XRF_Element(elem, xray_energy=self.xray_energy,
                            energy_min=self.energy_min)
        self.elements.append(xelem)
        self.params.add('amp_%s' % elem.lower(), value=amplitude,
                        vary=vary_amplitude, min=0)

    def add_filter(self, material, thickness, vary_thickness=False):
        self.filters.append(XRF_Material(material=material,
                                         thickness=thickness))
        self.params.add('filterlen_%s' % material,
                        value=thickness, min=0, vary=vary_thickness)

    def add_background(self, data, vary=True):
        self.bgr = data
        self.params.add('amp_background', value=1.0, min=0, vary=vary)

    def clear_background(self):
        self.bgr = None
        self.params.pop('amp_background')


    def calc_spectrum(self, energy, params=None):
        if params is None:
            params = self.params
        pars = params.valuesdict()
        self.comps = {}
        self.eigenvalues = {}

        efano = pars['det_efano']
        noise = pars['det_noise']
        step = pars['peak_step']
        tail = pars['peak_tail']
        gamma = pars['peak_gamma']
        # factor for Detector absorbance and Filters
        factor = self.detector.absorbance(energy, thickness=pars['det_thickness'])
        for f in self.filters:
            thickness = pars['filterlen_%s' % f.material]
            factor *= f.attenuation(energy, thickness=thickness)
        self.atten = factor

        factor = factor * self.count_time
        for elem in self.elements:
            amp = pars['amp_%s' % elem.symbol.lower()]
            comp = 0. * energy
            for key, line in elem.lines.items():
                ecen = line.energy
                line_amp = line.intensity * elem.mu * elem.fyields[line.initial_level]
                sig = self.detector.sigma(ecen, efano=efano, noise=noise)
                comp += hypermet(energy, amplitude=line_amp, center=ecen,
                                sigma=sig, step=step, tail=tail, gamma=gamma)
            self.comps[elem.symbol] = amp * comp * factor
            self.eigenvalues[elem.symbol] = amp

        # scatter peaks for Rayleigh and Compton
        for p in self.scatter:
            amp  = pars['%s_amp' % p]
            ecen = pars['%s_center' % p]
            step = pars['%s_step' % p]
            tail = pars['%s_tail' % p]
            gamma = pars['%s_gamma' % p]
            sigma = pars['%s_sigmax' % p]
            sigma *= self.detector.sigma(ecen, efano=efano, noise=noise)
            comp = hypermet(energy, amplitude=1.0, center=ecen,
                            sigma=sigma, step=step, tail=tail, gamma=gamma)
            self.comps[p] = amp * comp * factor
            self.eigenvalues[p] = amp

        if self.bgr is not None:
            bgr_amp = pars['amp_background']
            self.comps['background'] = bgr_amp * self.bgr
            self.eigenvalues['background'] = bgr_amp
        # calculate total spectrum
        total = 0. * energy
        for comp in self.comps.values():
            total += comp
        # remove tiny values
        floor = 1.e-12*max(total)
        total[np.where(total<floor)] = floor
        self.init_fit = total
        return total

    def __resid(self, params, data, index):
        pars = params.valuesdict()
        self.best_en = (pars['cal_offset'] + pars['cal_slope'] * index +
                        pars['cal_quad'] * index**2)
        self.fit_iter += 1
        self.best_fit = self.calc_spectrum(self.best_en, params=params)
        resid = (data - self.best_fit) * self.fit_weight

        # emphasize negative residuals more than positive residuals
        # scale = 0.25 * (np.abs(resid)).max()
        return resid # + 1 - np.exp(-resid/scale))

    def set_fit_weight(self, energy, counts, emin, emax, ewid=25.0):
        """
        set weighting factor to smoothed square-root of data
        """
        stderr = 1.0 / np.sqrt(counts + 0.1)
        en_win = ftwindow(energy, xmin=emin, xmax=emax,
                          dx=ewid, window='hanning')
        self.fit_weight = en_win * savitzky_golay(stderr, 7, 2)

    def fit_spectrum(self, energy, counts, energy_min=None, energy_max=None):

        work_energy = 1.0*energy
        work_counts = 1.0*counts
        floor = 1.e-12*np.percentile(counts, [99])[0]
        work_counts[np.where(counts<floor)] = floor

        if max(energy) < 250.0: # input energies are in keV
            work_energy = 1000.0 * energy

        imin, imax = 0, len(counts)
        if energy_min is None:
            energy_min = self.energy_min
        if energy_min is not None:
            imin = index_of(work_energy, energy_min)
        if energy_max is None:
            energy_max = self.energy_max
        if energy_max is not None:
            imax = index_of(work_energy, energy_max)

        self.set_fit_weight(work_energy, work_counts, energy_min, energy_max)

        self.fit_iter = 0

        index = np.arange(len(counts))
        userkws = dict(data=work_counts, index=index)

        tol = self.fit_toler
        self.result = minimize(self.__resid, self.params, kws=userkws,
                               method='leastsq', maxfev=10000, scale_covar=True,
                               gtol=tol, ftol=tol, epsfcn=1.e-5)

        self.fit_report = fit_report(self.result, min_correl=0.5)
        pars = self.result.pars

        self.best_en = (pars['cal_offset'] + pars['cal_slope'] * index +
                        pars['cal_quad'] * index**2)
        self.fit_iter += 1
        self.best_fit = self.calc_spectrum(self.best_en, params=params)

        self.best_fit = self.calc_spectrum(energy, params=self.result.params)

        # calculate transfer matrix for linear analysis using this model
        tmat= []
        for key, val in self.comps.items():
            tmat.append(val / self.eigenvalues[key])
        self.transfer_matrix = np.array(tmat).transpose()

    def apply_model(self, spectrum):
        """
        apply fitted model to another spectrum,
        returning a dict of predicted eigenvalues
        for the supplied spectrum
        """
        out = {}
        if self.transfer_matrix is not None:
            weights, chi2, rank, s2 = lstsq(self.transfer_matrix, spectrum)
            for i, name in enumerate(self.eigenvalues.keys()):
                out[name] = weights[i]
        return out


def xrf_model(xray_energy=None, energy_min=1500, energy_max=None, use_bgr=False, **kws):
    """create an XRF Peak

    Returns:
    ---------
     an XRF_Model instance
    """

    return XRF_Model(xray_energy=xray_energy, use_bgr=use_bgr,
                     energy_min=energy_min, energy_max=energy_max, **kws)
