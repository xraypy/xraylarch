#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Generic discrete convolution

Description
-----------

 This is a manual (not optimized!) implementation of discrete 1D
 convolution intended for spectroscopy analysis. The difference with
 commonly used methods is the possibility to adapt the convolution
 kernel for each convolution point, e.g. change the FWHM of the
 Gaussian kernel as a function of the energy scale.

Resources
---------

.. [WPconv] <http://en.wikipedia.org/wiki/Convolution#Discrete_convolution>
.. [Fisher] <http://homepages.inf.ed.ac.uk/rbf/HIPR2/convolve.htm>
.. [GP1202] <http://glowingpython.blogspot.fr/2012/02/convolution-with-numpy.html>

TODO
----
- [] get_ene_index: substitute with more elegant
     'np.argmin(np.abs(ene-(x)))'
- [] atan_gamma_fdmnes: define atan_gamma as in FDMNES
"""

from __future__ import print_function

__author__ = "Mauro Rovezzi"
__email__ = "mauro.rovezzi@gmail.com"
__credits__ = ""
__license__ = "BSD license <http://opensource.org/licenses/BSD-3-Clause>"
__organization__ = "European Synchrotron Radiation Facility"
__owner__ = "Mauro Rovezzi"
__year__ = "2013-2014"
__version__ = "0.0.4"
__status__ = "Alpha"
__date__ = "Jan 2014"

DEBUG = 0

import os, sys
import subprocess
from optparse import OptionParser
from datetime import date
from string import Template
import numpy as np

from .lineshapes import gaussian, lorentzian

def get_ene_index(ene, cen, hwhm):
    """ returns the min/max indexes for array ene at (cen-hwhm) and (cen+hwhm)
    very similar to index_of in larch
    """
    try:
        if ((cen-hwhm) <= min(ene)):
            ene_imin = 0
        else:
            ene_imin = max(np.where(ene < (cen-hwhm))[0])
        if ((cen+hwhm) >= max(ene)):
            ene_imax = (len(e)-1)
        else:
            ene_imax = min(np.where(ene > (cen+hwhm))[0])
        return ene_imin, ene_imax
    except:
        print('index not found for {0} +/- {1}'.format(cen, hwhm))
        return None, None

def lin_gamma(ene, fwhm=1.0, linbroad=None):
    """returns constant or linear energy-dependent broadening

    Parameters
    ----------
    ene : energy array in eV
    fwhm : first full width at half maximum in eV
    linbroad : list of 3-elements giving
               'second full width at half maximum'
               'energy starting point of the linear increase'
               'energy ending point of the linear increase'
    """
    w = np.ones_like(ene)
    if linbroad is None:
        return w*fwhm
    else:
        try:
            fwhm2 = linbroad[0]
            e1 = linbroad[1]
            e2 = linbroad[2]
        except:
            raise ValueError('wrong format for linbroad')
        for en, ee in enumerate(ene):
            if ee < e1:
                w[en] *= fwhm
            elif ee <= e2:
                wlin = (fwhm + (ee - e1) * (fwhm2 - fwhm) / (e2 - e1))
                w[en] *= wlin
            elif ee >= e2:
                w[en] *= fwhm2
        return w

def atan_gamma(ene, gamma_hole, gamma_max=15., e0=0, eslope=1.):
    r"""returns arctangent-like broadening, $\Gamma(E)$

    ..math

    \Gamma(E) = \Gamma_{hole} + \Gamma_{max} * ( \arctan( \frac{E-E_{0}}{E_{slope}} ) / \pi + 1/2) )
    """
    if (eslope == 0):
        print('Warning: eslope cannot be zero, using default value of 1')
        eslope = 1.
    return gamma_hole + gamma_max * ( ( np.arctan( (ene - e0) / eslope ) / np.pi ) + 0.5 )

def conv(e, mu, kernel='gaussian', fwhm_e=None, efermi=None):
    """ linear broadening

    Parameters
    ----------
    e : x-axis (energy)
    mu : f(x) to convolve with g(x) kernel, mu(energy)
    kernel : convolution kernel, g(x)
             'gaussian'
             'lorentzian'
    fwhm_e: the full width half maximum in eV for the kernel
            broadening. It is an array of size 'e' with constants or
            an energy-dependent values determined by a function as
            'lin_gamma()' or 'atan_gamma()'
    """
    f = np.copy(mu)
    z = np.zeros_like(f)
    if efermi is not None:
        #ief = index_nearest(e, efermi)
        ief = np.argmin(np.abs(e-efermi))
        f[0:ief] *= 0
    if e.shape != fwhm_e.shape:
        print("Error: 'fwhm_e' does not have the same shape of 'e'")
        return 0
    # linar fit upper part of the spectrum to avoid border effects
    # polyfit => pf
    lpf = len(e)/2.
    cpf = np.polyfit(e[-lpf:], f[-lpf:], 1)
    fpf = np.poly1d(cpf)
    # extend upper energy border to 3*fhwm_e[-1]
    estep = (e[-1] - e[-2])
    eup = np.append(e, np.arange(e[-1]+estep, e[-1]+3*fwhm_e[-1], estep))
    for n in range(len(f)):
        #from now on I change e with eup
        eimin, eimax = get_ene_index(eup, eup[n], 1.5*fwhm_e[n])
        if ((eimin is None) or (eimax is None)):
            if DEBUG:
                raise IndexError('e[{0}]'.format(n))
        if len(range(eimin, eimax)) % 2 == 0:
            kx = eup[eimin:eimax+1] # odd range centered at the convolution point
        else:
            kx = eup[eimin:eimax]
        ### kernel ###
        hwhm = fwhm_e[n]/2.0
        if ('gauss' in kernel.lower()):
            ky = gaussian(kx, center=eup[n], sigma=hwhm)
        elif ('lor' in kernel.lower()):
            ky = lorentzian(kx, center=eup[n], sigma=hwhm)
        else:
            raise ValueError("convolution kernel '{0}' not implemented".format(kernel))
        ky = ky/ky.sum() # normalize
        zn = 0
        lk = len(kx)
        for mf, mg in zip( range(-(lk/2), (lk/2)+1), range(lk) ):
            if ( ((n+mf) >= 0) and ((n+mf) < len(f)) ):
                zn += f[n+mf] * ky[mg]
            elif ((n+mf) >= 0):
                zn += fpf(eup[n+mf]) * ky[mg]
        z[n] = zn
    return z

def glinbroad(e, mu, fwhm_e=None, efermi=None, _larch=None):
    """ gaussian linear convolution in Larch """
    if _larch is None:
        raise Warning("larch broken?")
    return conv(e, mu, kernel='gaussian', fwhm_e=fwhm_e, efermi=efermi)
glinbroad.__doc__ = conv.__doc__

### CONVOLUTION WITH FDMNES VIA SYSTEM CALL ###
class FdmnesConv(object):
    """ Performs convolution with FDMNES within Python """
    def __init__(self, opts=None, calcroot=None, fn_in=None, fn_out=None):
        if opts is None:
            self.opts = dict(creator = 'FDMNES toolbox',
                             today = date.today(),
                             calcroot = calcroot,
                             fn_in = fn_in,
                             fn_out = fn_out,
                             fn_ext = 'txt',
                             estart_sel = '',
                             estart = '-20.',
                             efermi_sel = '',
                             efermi = '-5.36',
                             spin = '',
                             core_sel = '!',
                             core = '!',
                             hole_sel = '',
                             hole = '0.5',
                             conv_const = '!',
                             conv_sel = '',
                             ecent = '25.0',
                             elarg = '20.0',
                             gamma_max = '10.0',
                             gamma_type = 'Gamma_fix',
                             gauss_sel = '',
                             gaussian = '0.9')
        else:
            self.opts = opts
        if calcroot is not None:
            self.opts['calcroot'] = calcroot
            self.opts['fn_in'] = '{}.{}'.format(calcroot,
                                                self.opts['fn_ext'])
            self.opts['fn_out'] = '{}_conv{}.{}'.format(calcroot,
                                                        self.opts['spin'],
                                                        self.opts['fn_ext'])
        if fn_in is not None:
            self.opts['calcroot'] = fn_in[:-4]
            self.opts['fn_in'] = fn_in
            self.opts['fn_out'] = '{}_conv{}.{}'.format(fn_in[:-4],
                                                        self.opts['spin'],
                                                        self.opts['fn_ext'])
        if fn_out is not None:
            self.opts['fn_out'] = fn_out
        # then check all options
        self.checkopts()

    def checkopts(self):
        if (self.opts['calcroot'] is None) or (self.opts['fn_in'] is None):
            raise NameError("missing 'calcroot' or 'fn_in'")
        if self.opts['estart'] == '!':
            self.opts['estart_sel'] = '!'
        if self.opts['efermi'] == '!':
            self.opts['efermi_sel'] = '!'
        if self.opts['spin'] == 'up':
            self.opts['core_sel'] = ''
            self.opts['core'] = '2 !spin up'
        elif self.opts['spin'] == 'down':
            self.opts['core_sel'] = ''
            self.opts['core'] = '1 !spin down'
        elif self.opts['spin'] == '':
            self.opts['core_sel'] = '!'
        elif self.opts['spin'] == 'both':
            raise NameError('spin="both" not implemented!')
        else:
            self.opts['spin'] = ''
            self.opts['core_sel'] = '!'
            self.opts['core'] = '!'
        if self.opts['hole'] == '!':
            self.opts['hole_sel'] = '!'
        if self.opts['conv_const'] == '!':
            self.opts['conv_sel'] = '!'
        else:
            self.opts['conv_sel'] = ''
        if self.opts['gamma_type'] == 'Gamma_fix':
            pass
        elif self.opts['gamma_type'] == 'Gamma_var':
            pass
        else:
            raise NameError('gamma_type="Gamma_fix"/"Gamma_var"')
        if self.opts['gaussian'] == '!':
            self.opts['gauss_sel'] = '!'
        else:
            self.opts['gauss_sel'] = ''
        # update the output file name
        self.opts['fn_out'] = '{}_conv{}.{}'.format(self.opts['calcroot'],
                                                    self.opts['spin'],
                                                    self.opts['fn_ext'])
    def setopt(self, opt, value):
        self.opts[opt] = value
        self.checkopts()

    def wfdmfile(self):
        """ write a simple fdmfile.txt to enable the convolution
        first makes a copy of previous fdmfile.txt if not already done """
        if os.path.exists('fdmfile.bak'):
            print('fdmfile.bak exists, good')
        else:
            subprocess.call('cp fdmfile.txt fdmfile.bak', shell=True)
            print('copied fdmfile.txt to fmdfile.bak')
        #
        s = Template('!fdmfile.txt automatically created by ${creator} on ${today} (for convolution)\n\
!--------------------------------------------------------------------!\n\
! Number of calculations\n\
 1\n\
! FOR CONVOLUTION STEP\n\
convfile.txt\n\
!--------------------------------------------------------------------!\n\
')
        outstr = s.substitute(self.opts)
        f = open('fdmfile.txt', 'w')
        f.write(outstr)
        f.close()

    def wconvfile(self):
        s = Template("""
!FDMNES convolution file\n\
!created by ${creator} on ${today}\n\
!
Calculation\n\
${fn_in}\n\
Conv_out\n\
${fn_out}\n\
${estart_sel}Estart\n\
${estart_sel}${estart}\n\
${efermi_sel}Efermi\n\
${efermi_sel}${efermi}\n\
${core_sel}Selec_core\n\
${core_sel}${core}\n\
${hole_sel}Gamma_hole\n\
${hole_sel}${hole}\n\
${conv_sel}Convolution\n\
${conv_sel}${ecent} ${elarg} ${gamma_max} !Ecent Elarg Gamma_max\n\
${conv_sel}${gamma_type}\n\
${gauss_sel}Gaussian\n\
${gauss_sel}${gaussian} !Gaussian conv for experimental res\n\
""")
        outstr = s.substitute(self.opts)
        f = open('convfile.txt', 'w')
        f.write(outstr)
        f.close()

    def run(self):
        """ runs fdmnes """
        self.wfdmfile()  # write fdmfile.txt
        self.wconvfile() # write convfile.txt
        try:
            subprocess.call('fdmnes', shell=True)
        except OSError:
            print("check 'fdmnes' executable exists!")
