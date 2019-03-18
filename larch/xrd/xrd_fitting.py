#!/usr/bin/env python
'''
Diffraction functions require for fitting and analyzing data.

mkak 2017.02.06 (originally written spring 2016)
'''


##########################################################################
# IMPORT PYTHON PACKAGES

import math

import numpy as np
from scipy import optimize,signal,interpolate

from .xrd_tools import (d_from_q, d_from_twth, twth_from_d, twth_from_q,
                        q_from_d, q_from_twth)


##########################################################################
# FUNCTIONS

def peakfilter(intthrsh,ipeaks,y,verbose=False):
    '''
    Returns x and y for data set corresponding to peak indices solution
    from peakfilter() with the option of setting a minimum intensity
    threshold for filtering peaks
    '''

    ipks = []
    ipks += [i for i in ipeaks if y[i] > intthrsh]
    if verbose: print('Peaks under intensity %i filtered out.' % intthrsh)

    return ipks

def peaklocater(ipeaks,x):
    '''
    Returns x and y for data set corresponding to peak indices solution
    from peakfinder()
    '''
    xypeaks = [x[i] for i in ipeaks]

    return np.array(xypeaks)

def peakfinder_methods():

    methods = []
    try:
        import peakutils
        methods += ['peakutils.indexes']
    except:
        pass
    try:
        from scipy import signal
        methods += ['scipy.signal.find_peaks_cwt']
    except:
        pass

    return methods


def peakfinder(y, method='scipy.signal.find_peaks_cwt',
               widths=20, gapthrsh=5, thres=0.0, min_dist=10,**kwargs):
    '''
    Returns indices for peaks in y from dataset
    '''

    if method == 'peakutils.indexes':
        try:
            import peakutils
        except:
            print('python package peakutils not installed')
            widths = np.arange(1,int(len(y)/widths))
            peak_indices = signal.find_peaks_cwt(y, widths, gap_thresh=gapthrsh)
        peak_indices = peakutils.indexes(y, thres=thres, min_dist=min_dist)
    elif method == 'scipy.signal.find_peaks_cwt':
        ## scipy.signal.find_peaks_cwt(vector, widths, wavelet=None, max_distances=None,
        ##                   gap_thresh=None, min_length=None, min_snr=1, noise_perc=10)
        widths = np.arange(1,int(len(y)/widths))
        peak_indices = signal.find_peaks_cwt(y, widths, gap_thresh=gapthrsh)

    return peak_indices

def peakfitter(ipeaks, twth, I, verbose=True, halfwidth=40, fittype='single'):

    peaktwth,peakFWHM,peakinty = [],[],[]
    for j in ipeaks:
        if j > halfwidth and (len(twth)-j) > halfwidth:
            minval = int(j - halfwidth)
            maxval = int(j + halfwidth)

            if I[j] > I[minval] and I[j] > I[maxval]:
                xdata = twth[minval:maxval]
                ydata = I[minval:maxval]

                try:
                    pktwth,pkfwhm,pkint = data_gaussian_fit(xdata,ydata,fittype=fittype)
                    peaktwth += [pktwth]
                    peakFWHM += [pkfwhm]
                    peakinty += [pkint]
                except:
                    pass

    return np.array(peaktwth),np.array(peakFWHM),np.array(peakinty)


def data_gaussian_fit(x,y,fittype='single'):
    '''
    Fits a single or double Gaussian functions.
    '''
    meanx = sum(x)/float(len(x))
    meany = sum(y)/float(len(y))
    sigma = np.sqrt(sum(y*(x-meanx)**2)/float(len(x)))

    try:
        popt,pcov = optimize.curve_fit(gaussian,x,y,p0=[np.max(y),meanx,sigma])
    except:
        popt = [1,1,1]

    if fittype == 'double':
        a,b,c = popt
        popt2,pcov2 = optimize.curve_fit(doublegaussian,x,y,p0=[a,b,c,np.min(y),meanx,sigma])

    rsqu_n1 = 0
    rsqu_n2 = 0
    rsqu_d = 0
    for i in range(x.shape[0]):
        rsqu_n1 = (y[i] - gaussian(x[i],*popt))**2 + rsqu_n1
        if fittype == 'double':
            rsqu_n2 = (y[i] - doublegaussian(x[i],*popt2))**2 + rsqu_n2
        rsqu_d = (y[i] - meany)**2 + rsqu_d


    if fittype == 'double':
        pkpos = popt2[1]
        pkfwhm = abs(2*np.sqrt(2*math.log1p(2))*popt2[2])
        pkint  = np.max(doublegaussian(x,*popt2))
    else:
        pkpos = popt[1]
        pkfwhm = abs(2*np.sqrt(2*math.log1p(2))*popt[2])
        pkint  = np.max(gaussian(x,*popt))

    return pkpos,pkfwhm,pkint



def gaussian(x,a,b,c):
    return a*np.exp(-(x-b)**2/(2*c**2))



def doublegaussian(x,a1,b1,c1,a2,b2,c2):
    return a1*np.exp(-(x-b1)**2/(2*c1**2))+a2*np.exp(-(x-b2)**2/(2*c2**2))


def instrumental_fit_uvw(ipeaks, twthaxis, I, halfwidth=40, verbose=True):

    twth,FWHM,inten = peakfitter(ipeaks,twthaxis,I,halfwidth=halfwidth,
                           fittype='double',verbose=verbose)

    tanth = np.tan(np.radians(twth/2))
    sqFWHM  = FWHM**2

    (u,v,w) = data_poly_fit(tanth,sqFWHM,verbose=verbose)

    if verbose:
        print('\nFit results:')
        for i,(twthi,fwhmi,inteni) in enumerate(zip(twth,FWHM,inten)):
            print('Peak %i @ %0.2f deg. (fwhm %0.3f deg, %i counts)' % (i,twthi,fwhmi,inteni))
    print('\nInstrumental broadening parameters:')
    print('---  U  : %0.8f'   % u)
    print('---  V  : %0.8f'   % v)
    print('---  W  : %0.8f\n' % w)

    return(u,v,w)


def poly_func(x,a,b,c):
    return a*x**2 + b*x + c


def data_poly_fit(x, y, plot=False, verbose=False):
    '''
    Fits a set of data with to a second order polynomial function.
    '''

    try:
        popt,pcov = optimize.curve_fit(poly_func,x,y,p0=[1,1,1])
    except:
        print( 'WARNING: scipy.optimize.curve_fit was unsuccessful.' )
        return [1,1,1]

    n = len(x)
    meany = sum(y)/n

    rsqu_n = 0
    rsqu_d = 0
    for i in range(x.shape[0]):
        rsqu_n = (y[i] - poly_func(x[i],*popt))**2 + rsqu_n
        rsqu_d = (y[i] - meany)**2 + rsqu_d

    if verbose:
        print('---Polynomial Fit:')
        print('---  U  : %0.8f'   % popt[0])
        print('---  V  : %0.8f'   % popt[1])
        print('---  W  : %0.8f\n' % popt[2])

    return popt

def trim_range(data,min,max,axis=0):

    maxi = -1
    mini = 0
    for i,val in enumerate(data[axis]):
        mini = i if val < min else mini
        maxi = i if val < max else maxi

    return data[:,mini:maxi]

def interpolate_for_y(x,x0,y0):
    t = interpolate.splrep(x0,y0)
    return interpolate.splev(x,t,der=0)

def calc_peak():

    x = np.arange(-2,2,0.001)

    ## Lorentzian
    b = 1/(1+(x**2))

    ## Gaussian
    c = np.exp(-math.log1p(2)*(x**2))

    ## VOIGT: Convolve, shift, and scale
    d = np.convolve(b,c,'same')
    d = norm_pattern(d,c)
    shiftx = find_max(x,d)
    newx = x-shiftx

    ## Diffraction pattern data.
    ## x,b    - 'Lorentzian'
    ## x,c    - 'Gaussian'
    ## newx,d - 'Voigt'

    return 'Lorentzian',b,x,'Gaussian',x,c,'Voigt',newx,d


def norm_pattern(intensity,scale_int):

    max_int = np.max(intensity)
    scale = np.max(scale_int)
    intensity = intensity/max_int*scale

    return(intensity)


def scale_100(intensity):

    intensity = norm_pattern(intensity,100)

    return(intensity)



def find_max(x,y):
    return [xi for xi,yi in zip(x,y) if yi == np.max(y)][0]



def calcRsqu(y,ycalc):

    ss_res = 0
    ss_tot = 0

    ymean = np.mean(y) #sum(y)/float(len(y))

    for i,yi in enumerate(y):
        ss_res = ss_res + (yi - ycalc[i])**2
        ss_tot = ss_tot + (yi - ymean)**2

    return (1 - (ss_res/ss_tot))


def outliers(y,scale=0.2):
    for i,yi in enumerate(y):
        if i > 0 and i < (len(y)-1):
#             if yi > y[i-1]*scale and yi > y[i+1]*scale:
#                 y[i] = (y[i-1]+y[i+1])/2
            if abs(yi-y[i-1]) > yi/scale and abs(yi - y[i+1]) > yi/scale:
                y[i] = (y[i-1]+y[i+1])/2

    return y


def calc_broadening(pklist, twth, wavelength, u=1.0, v=1.0, w=1.0, C=1.0, D=None, verbose=False,smooth=False):
    '''
    == Broadening calculation performed in 2theta - not q ==

    pklist     - location of peaks in range [q,2th,d,I]
    twth       -  2-theta axis
    wavelength - in units A

    u,v,w - instrumental broadening parameters
    C - shape factor (1 for sphere)
    D - particle size in units A (if D is None, no size broadening)
    '''

    ## TERMS FOR INSTRUMENTAL BROADENING
    thrad = np.radians(pklist[1]/2)
    Bi = np.sqrt( u*(np.tan(thrad))**2 + v*np.tan(thrad) + w )

    ## TERMS FOR SIZE BROADENING
    ## FWHM(2th) = (C*wavelength)/(D*math.cos(math.radians(twth/2)))
    ## FWHM(q)   = (C*wavelength)/D*(1/np.sqrt(1-termB))
    if D is not None:
        termB = ((wavelength*pklist[0])/(2*math.pi))**2
        Bs = (C*wavelength)/D*(1/np.sqrt(1-termB))

    ## Define intensity array for broadened peaks
    Itot = np.zeros(len(twth))

    step = twth[1]-twth[0]

    ## Loop through all peaks
    for i,peak in enumerate(zip(*pklist)):
        if peak[1] > min(twth) and peak[1] < max(twth):
            A = peak[3]
            B = peak[1]

            c_i = Bi[i]/abs(2*np.sqrt(2*math.log1p(2)))

            if D is not None: c_s = Bs[i]/abs(2*np.sqrt(2*math.log1p(2)))

            #    Bm = np.sqrt(Bi[i]**2+Bs[i]**2)
            #else:
            #    Bm = np.sqrt(Bi[i]**2)

            #c_m = Bm/abs(2*np.sqrt(2*math.log1p(2)))

            width1 = max(Bs[i],Bi[i]) if D is not None else Bi[i]
            width2 = min(Bs[i],Bi[i]) if D is not None else Bi[i]

            min2th = B-2*width1
            max2th = B+2*width1

            num = abs((max2th-min2th)/step)
            twthG = np.linspace(max2th,min2th,num)

            intBi = A*np.exp(-(twthG-B)**2/(2*c_i**2))
            if D is not None: intBs = A*np.exp(-(twthG-B)**2/(2*c_s**2))
            #intBm = A*np.exp(-(twthG-B)**2/(2*c_m**2))

            if D is not None:
                new_intensity = np.convolve(intBs,intBi,'same')
            else:
                new_intensity = intBi

            new_intensity = norm_pattern(new_intensity,A)

            X = twthG
            Y = new_intensity

            bins = len(twth)
            idx  = np.digitize(X,twth)
            Ii    = [np.sum(Y[idx==k]) for k in range(bins)]
            Itot = Itot + Ii

    if smooth:
        Itot = outliers(Itot)
    return Itot

##########################################################################
# def fit_with_minimization(q,I,parameters=None,fit_method='leastsq'):
#     '''
#     fit_method options: 'leastsq','cobyla','slsqp','nelder'
#
#     parameters of type Parameters(): needs a,b,c,nsize,pkshift?
#
#     my_pars = Parameters()
#     my_pars.add('nsize', value= NPsize, min= 3.0,  max=100.0,vary=False)
#     my_pars.add('a', value=bkgdA, min=minA, max=maxA)
#     my_pars.add('b', value=bkgdB, min=minB, max=maxB)
#     my_pars.add('c', value=bkgdC, min=minC, max=maxC)
#     '''
#
#     from lmfit import minimize,Parameters,report_fit
#
# #     ## First, fit background alone:
# #     result = minimize(BACKGROUND_FUNCTION, my_pars, args=(q,I),method=fit_method)
# #     ## Second, add fitted parameters into parameter set
# #     my_pars.add('?',  value=result.params['?'].value)
# #     ## Third, fit peaks on top of background
# #     result = minimize(BACKGROUND_FUNCTION+PEAKS_FUNCTION, my_pars, args=(q,I),method=fit_method)
# #     ## Fourth, view error report
# #     report_fit(result)
# #     ## Fifth, return results
# #     NPsize = result.params['nsize'].value
# #     bkgdA  = result.params['a'].value
# #     bkgdB  = result.params['b'].value
# #     bkgdC  = result.params['c'].value
#
#
#     return
