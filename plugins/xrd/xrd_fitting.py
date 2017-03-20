#!/usr/bin/env python
'''
Diffraction functions require for fitting and analyzing data.

mkak 2017.02.06 (originally written spring 2016)
'''


##########################################################################
# IMPORT PYTHON PACKAGES

import math

import numpy as np
from scipy import optimize,signal

from xrd_etc import d_from_q,d_from_twth,twth_from_d,twth_from_q,q_from_d,q_from_twth

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

    if verbose:
        print('Peaks under intensity %i filtered out.' % intthrsh)
    
    return ipks

def peaklocater(ipeaks,x,y):
    '''
    Returns x and y for data set corresponding to peak indices solution
    from peakfinder()
    '''
    xypeaks = np.zeros((2,len(ipeaks)))
    xypeaks[0,:] = [x[i] for i in ipeaks]
    xypeaks[1,:] = [y[i] for i in ipeaks]

    return np.array(xypeaks)

def peakfinder(x, y, regions=50, gapthrsh=5):
    '''
    Returns indices for peaks in y from dataset (x,y)
    '''
    ttlpnts = len(x)
    widths = np.arange(1,int(ttlpnts/regions))

    peak_indices = signal.find_peaks_cwt(y, widths, gap_thresh=gapthrsh)
# # scipy.signal.find_peaks_cwt(vector, widths, wavelet=None, max_distances=None, 
# #                   gap_thresh=None, min_length=None, min_snr=1, noise_perc=10)

    return peak_indices


def peakfitter(ipeaks, q, I, wavelength=0.6525, verbose=True, halfwidth=40, fittype='single'):

    peaktwth = []
    peakFWHM = []
    peakinty = []
    for j in ipeaks:
        if j > halfwidth and (np.shape(q)-j) > halfwidth:
            minval = int(j - halfwidth)
            maxval = int(j + halfwidth)

            if I[j] > I[minval] and I[j] > I[maxval]:
                
                xdata = q[minval:maxval]
                ydata = I[minval:maxval]

                xdata = twth_from_q(xdata,wavelength)
                try:
                    twth,fwhm,pkint = data_gaussian_fit(xdata,ydata,fittype=fittype)
                    peaktwth += [twth]
                    peakFWHM += [fwhm]
                    peakinty += [pkint]
                except:
                    pass
        
    return np.array(peaktwth),np.array(peakFWHM),np.array(peakinty)


def data_gaussian_fit(x,y,pknum=0,fittype='single'):
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
        pkint  = np.max(gaussian(x,*popt2))

   
    return pkpos,pkfwhm,pkint
    


def gaussian(x,a,b,c):
    return a*np.exp(-(x-b)**2/(2*c**2))



def doublegaussian(x,a1,b1,c1,a2,b2,c2):
    return a1*np.exp(-(x-b1)**2/(2*c1**2))+a2*np.exp(-(x-b2)**2/(2*c2**2))


def instrumental_fit_uvw(ipeaks, q, I, wavelength=0.6525, halfwidth=40, verbose=True):

    twth,FWHM,inten = peakfitter(ipeaks,q,I,wavelength=wavelength,halfwidth=halfwidth,
                           fittype='double',verbose=verbose)

    tanth = np.tan(np.radians(twth/2))
    sqFWHM  = FWHM**2

    (u,v,w) = data_poly_fit(tanth,sqFWHM,verbose=verbose)
    
    if verbose:
        print('\nFit results:')
        for i,(twthi,fwhmi,inteni) in enumerate(zip(twth,FWHM,inten)):
            print('Peak %i @ %0.2f deg. (fwhm %0.3f deg, %i counts)' % (i,twthi,fwhmi,inteni))
        print(                                         )
        print( '\nInstrumental broadening parameters:' )
        print( '---  U',u                              )
        print( '---  V',v                              )
        print( '---  W',w                              )
        print(                                         )

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
        print( '---Polynomial Fit'                      ) 
        print( '---  U',popt[0]                         ) 
        print( '---  V',popt[1]                         ) 
        print( '---  W',popt[2]                         ) 
        print( 'Goodness of fit, R^2:',1-rsqu_n/rsqu_d  ) 
        print(                                          ) 

    return popt

def trim_range(data,min,max,axis=0):

    maxi = -1
    mini = 0
    for i,val in enumerate(data[axis]):
        mini = i if val < min else mini
        maxi = i if val < max else maxi
   
    return data[:,mini:maxi]

def interpolate_for_y(x,x0,y0):
    t = interpolate.splrep(x0,y0,s=0)
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
    return [x[i] for i,yi in enumerate(y) if yi == np.max(y)]


def calcRsqu(y,ycalc):
    
    ss_res = 0
    ss_tot = 0
    
    ymean = np.mean(y) #sum(y)/float(len(y))
    
    for i,yi in enumerate(y):
        ss_res = ss_res + (yi - ycalc[i])**2
        ss_tot = ss_tot + (yi - ymean)**2
       
    return (1 - (ss_res/ss_tot))


def patternbroadening(data_q,nsize):

    ## Particle size broadening and instrumental broadening
    calc_int = size_broadening(pkQlist,data_q,instrU,instrV,instrW,nsize)

    ## Instrumental broadening
#     calc_int = instr_broadening(pkQlist,data_q,DATA_INT,instrU,instrV,instrW)

    return calc_int


def size_broadening(pkqlist, q, wavelength,
                    instr_u=1.0, instr_v=1.0, instr_w=1.0,
                    C=1.0, D=None):
    '''
    pkqlist - location of peaks in range
    q - axis
    wavelength - in units A
    
    u,v,w - instrumental broadening parameters
    C - shape factor (1 for sphere)
    D - particle size in units A (if D is None, no size broadening)
    '''

    lenlist = np.shape(pkqlist)[1]
    
    ## Broadening calculation performed in 2theta - not q
    twth = twth_from_q(q,wavelength)
    twthlist = twth_from_q(pkqlist[0],wavelength)

    ## TERMS FOR INSTRUMENTAL BROADENING
    thrad = np.radians(twthlist/2)
    Bi = np.sqrt( u*(np.tan(thrad))**2 + v*pn.tan(thrad) + w )

    ## TERMS FOR SIZE BROADENING
    ## FWHM(2th) = (C*wavelength)/(D*math.cos(math.radians(twth/2)))
    ## FWHM(q)   = (C*wavelength)/D*(1/np.sqrt(1-termB))
    
    termB = ((wavelength*pkqlist[0])/(2*math.pi))**2
    Bs = (C*wavelength)/D*(1/np.sqrt(1-termB))
    
        
    ## Define intensity array for broadened peaks
    intenB = np.zeros(np.shape(q)[0])
    
    ## Loop through all peaks
    for i in range(lenlist):
    
        if pkqlist[0][i] > np.min(q) and pkqlist[0][i] < np.max(q):

            ## Create Gaussian of correct width
            ## FWHM = abs(2*np.sqrt(2*math.log1p(2))*c)
            A = pkqlist[1][i]   ## intensity
            B = twthlist[i]     ## position (in 2theta)
        
            ## INSTRUMENT contribution
            c_i = Bi[i]/abs(2*np.sqrt(2*math.log1p(2)))
            ## SIZE contribution
            c_s = Bs[i]/abs(2*np.sqrt(2*math.log1p(2)))
            
            Bm = np.sqrt(Bi[i]**2+Bs[i]**2)
            c_m = Bm/abs(2*np.sqrt(2*math.log1p(2)))
      
            width1 = np.max(Bs[i],Bi[i])
            width2 = np.min(Bs[i],Bi[i])

            ## Define 2th axis for calculation
            min2th = B-2*width1
            max2th = B+2*width1
            twthG = np.arange(max2th,min2th,-width2/400)

            ## Calculate peak for corresponding width
            intBi = A*np.exp(-(twthG-B)**2/(2*c_i**2))
            intBs = A*np.exp(-(twthG-B)**2/(2*c_s**2))
            intBm = A*np.exp(-(twthG-B)**2/(2*c_m**2))
            
            noplot = 1
            if i < 10 and noplot == 0:
                plt_str = 'inst = %0.6f\nsize = %0.6f\n comb = %0.6f'
                print(plt_str % (Bi[i],Bs[i],Bm))
            
            new_intensity = np.convolve(intBs,intBi,'same')
            ## Normalize to correct intensity
            new_intensity = norm_pattern(new_intensity,A)
        
            shift2th = find_max(twthG,new_intensity)
            twthG = twthG - (B-shift2th)

            qG = q_from_twth(twthG,wavelength)
                        
            nintensity = interpolate_for_y(q,qG,new_intensity)        
        
            ## Interpolate peak onto q scale and add
            for j in range(np.shape(intenB)[0]):
                intenB[j] = nintensity[j] + intenB[j]


            print('2theda shift is %0.4f' %(B-shift2th))
                
    intenB = scale_100(intenB)
            

    return(intenB)


def instr_broadening(pkqlist,q,wavelength,intensity,u,v,w): 

    lenlist = np.shape(pkqlist)[1]
    
    ## Broadening calculation performed in 2theta - not q
    twthlist = twth_from_q(pkqlist[0],wavelength)
    twth = twth_from_q(q,wavelength)

    ## TERMS FOR INSTRUMENTAL BROADENING
    Bi = np.zeros(lenlist)
    for i in range(lenlist):
        thrad = math.radians(twthlist[i]/2)
        Bi[i] = np.sqrt(u*(math.tan(thrad))**2+v*math.tan(thrad)+w)
        
    ## Define intensity array for broadened peaks
    intenB = np.zeros(np.shape(q)[0])
    
    ## Loop through all peaks
    for i in range(lenlist):

        ## Create Gaussian of correct width
        A = pkqlist[1][i]   ## intensity
        B = twthlist[i]     ## position (in 2theta)
        
        ## FWHM = abs(2*np.sqrt(2*math.log1p(2))*c)
        
        ## INSTRUMENT contribution
        c_i = Bi[i]/abs(2*np.sqrt(2*math.log1p(2)))      
        
        width = Bi[i]

        ## Define 2th axis for calculation
        min2th = B-2*width
        max2th = B+2*width        
        twthG = np.arange(max2th,min2th,-width/200)
        qG = q_from_twth(twthG,wavelength)

        ## Calculate peak for corresponding width
        intBi = A*np.exp(-(twthG-B)**2/(2*c_i**2))
        ## Normalize to correct intensity
        intBi = norm_pattern(intBi,A)

        ## Interpolate peak onto q scale and add
        nintensity = interpolate_for_y(q,qG,intBi)        
        for j in range(np.shape(intenB)[0]):
            intenB[j] = nintensity[j] + intenB[j]
            
    intenB = norm_pattern(intenB,intensity)

    return(intenB)

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

                     
def registerLarchPlugin():
    return ('_xrd', {'peakfinder': peakfinder,
                     'peakfitter': peakfitter,
                     'peakfilter': peakfilter,
                     'peaklocater': peaklocater,
                     'data_gaussian_fit': data_gaussian_fit,
                     'gaussian': gaussian,
                     'doublegaussian': doublegaussian,
                     'instrumental_fit_uvw': instrumental_fit_uvw,
                     'poly_func': poly_func,
                     'data_poly_fit': data_poly_fit
                      })
