#!/usr/bin/env python
'''
Diffraction functions require for fitting and analyzing data.

mkak 2016.10.04 (originally written spring 2016)
'''

## TO DO:
##  - remove global variables
##  - provide better commenting
##  - work into gui
## mkak 2016.10.26

##########################################################################
# IMPORT PYTHON PACKAGES

import math
import operator
import re
import os
import argparse
import textwrap
#import yaml
import time

import wx

import numpy as np
from scipy import optimize
from scipy import signal

import matplotlib.pyplot as plt
import pylab as plb

from lmfit import minimize, Parameters, Parameter, report_fit

HAS_XRAYUTIL = False
try:
    import xrayutilities as xu
    HAS_XRAYUTIL = True
except ImportError:
    pass

HAS_fabio = False
try:
    import fabio
    HAS_fabio = True
except ImportError:
    pass

HAS_pyFAI = False
try:
    import pyFAI
    import pyFAI.calibrant
    # from pyFAI.calibration import Calibration
    HAS_pyFAI = True
except ImportError:
    pass


##########################################################################
def find_peaks(q,I):

    ttlpnts = len(q)

    pnts = 50
    peak_indices = signal.find_peaks_cwt(I, np.arange(1,int(ttlpnts/pnts)),gap_thresh=5)
    print peak_indices
    peak_x, peak_y = [],[]
    for i in peak_indices:
        peak_x += [q[i]]
        peak_y += [I[i]]

    return peak_x,peak_y
#########################################################################
def integrate_xrd(xrd_map, ai=None,AI=None, calfile=None, unit='q', steps=10000, 
                  save=False, file='~/test.xy', mask=None, dark=None, verbose=False):

    if HAS_pyFAI:
        if ai is None:
            if AI is None:
                try:
                    ai = pyFAI.load(calfile)
                except IOError:
                    print('No calibration parameters specified.')
                    return
            else:
                ai = calculate_ai(AI)
        
        attrs = {}
        if unit == '2th':
            attrs.update({'unit':'2th_deg'})
        else:
            attrs.update({'unit':'q_A^-1'})
        if mask:
            attrs.update({'mask':mask})
        if dark:
            attrs.update({'dark':dark})        
        if save:
            print('Saving %s data to file: %s\n' % (unit,file))
            attrs.update({'filename':file})

        if verbose:
            t0 = time.time()
        qI = ai.integrate1d(xrd_map,steps,**attrs)
        if verbose:
            t1 = time.time()
            print('\tTime to integrate data = %0.3f s' % ((t1-t0)))

    else:
        print('pyFAI not imported. Cannot calculate 1D integration without it.')
        return

    return qI
##########################################################################
def calculate_ai(AI):
    '''
    Builds ai structure using AzimuthalIntegrator from hdf5 parameters
    mkak 2016.08.30
    '''

    if HAS_pyFAI:
        try:
            distance = float(AI.attrs['distance'])
        except:
            distance = 1
     
        ## Optional way to shorten this script... will need to change units of pixels
        ## mkak 2016.08.30   
        #floatattr = ['poni1','poni2','rot1','rot2','rot3','pixel1','pixel2']
        #valueattr = np.empty(7)
        #for f,fattr in enumerate(floatattr):
        #     try:
        #         valueattr[f] = float(AI.attr[fattr])
        #     except:
        #         valueattr[f] =  0
    
        try:
            poni_1 = float(AI.attrs['poni1'])
        except:
            poni_1 = 0
        try:
            poni_2 = float(AI.attrs['poni2'])
        except:
            poni_2 = 0
        
        try:
            rot_1 = float(AI.attrs['rot1'])
        except:
            rot_1 = 0
        try:
            rot_2 = float(AI.attrs['rot2'])
        except:
            rot_2 = 0
        try:
            rot_3 = float(AI.attrs['rot3'])
        except:
            rot_3 = 0

        try:
            pixel_1 = float(AI.attrs['ps1'])
        except:
            pixel_1 = 0
        try:
            pixel_2 = float(AI.attrs['ps2'])
        except:
            pixel_2 = 0

        try:
            spline = AI.attrs['spline']
            if spline == '':
                spline = None
        except:
            spline = None
        
        try:
            detname = AI.attrs['detector']
            if detname == '':
                detname = None
        except:
            detname = None
    
        try:
            xraylambda =float(AI.attrs['wavelength'])
        except:
            xraylambda = None
    else:
        print('pyFAI not imported. Cannot calculate ai for calibration.')
        return

        
    return pyFAI.AzimuthalIntegrator(dist = distance, poni1 = poni_1, poni2 = poni_2,
                                    rot1 = rot_1, rot2 = rot_2, rot3 = rot_3,
                                    pixel1 = pixel_1, pixel2 = pixel_2,
                                    splineFile = spline, detector = detname,
                                    wavelength = xraylambda)
##########################################################################
def calc_q_to_d(q):
    return (2.*math.pi)/q
##########################################################################
def calc_q_to_2th(q,wavelength,units='degrees'):
    twth = 2.*np.arcsin((q*wavelength)/(4.*math.pi))
    if units == 'radians':
        return twth
    else:
        return np.degrees(twth)
##########################################################################
def calc_d_to_q(d):
    return (2.*math.pi)/d
##########################################################################
def calc_2th_to_q(twth,wavelength,units='degrees'):
    if units == 'degrees':
        twth = np.radians(twth)
    return ((4.*math.pi)/wavelength)*np.sin(twth/2.)
##########################################################################
def fabioOPEN(path):

    if HAS_fabio:
        try:
            image = fabio.open(path).data
            return image
        except:
            print('fabio could not import the image: %s' % path)
    else:
        print('fabio package not available for opening images.')
        
    return
##########################################################################
def xy_file_reader(xyfile,char=None,verbose=False):
    '''
    Parses (x,y) data from pyFAI .xy file.
    '''

    with open(xyfile) as f:
        lines = f.readlines()

    for i,line in enumerate(lines):
        if '#' not in line:
            break

    x, y = [], []
    for j in range(i, len(lines)):
        if char:
            fields = re.split(' |%s' % char,lines[j])
        else:
            fields = lines[j].split()
        x += [float(fields[0])]
        y += [float(fields[1])]

    if verbose:
        print('\nFinished reading file %s.' % xyfile)

    return np.array(x),np.array(y)

def gaussian_peak_fit(x,y,double=False,plot=False):
    '''
    Fits one or two Gaussian functions.
    '''
    meanx = sum(x)/float(len(x))
    meany = sum(y)/float(len(y))
    sigma = np.sqrt(sum(y*(x-meanx)**2)/float(len(x)))
    
    print x
    print y
    print
    print
    print 'mean x',meanx
    print 'mean y',meany
    print 'sigma',sigma
        
    plx =  0.05*(max(x)-min(x)) + min(x)
    ply = -0.2*(max(y)-min(y)) + max(y)

    ## ASSUMES PEAK IN CENTER FOR FIRST GUESS
    #popt,pcov = optimize.curve_fit(gaussian,x,y,p0=[np.max(y),meanx,sigma])
    try:
        popt,pcov = optimize.curve_fit(gaussian,x,y,p0=[np.max(y),meanx,sigma])
    except:
        popt = [1,1,1]
        print 'used default...'
    
    if double:
        a,b,c = popt
        popt2,pcov2 = optimize.curve_fit(doublegaussian,x,y,p0=[a,b,c,np.min(y),meanx,sigma])

    rsqu_n1 = 0
    rsqu_n2 = 0
    rsqu_d = 0
    for i in range(x.shape[0]):
        rsqu_n1 = (y[i] - gaussian(x[i],*popt))**2 + rsqu_n1
        if double:
            rsqu_n2 = (y[i] - doublegaussian(x[i],*popt2))**2 + rsqu_n2
        rsqu_d = (y[i] - meany)**2 + rsqu_d

    print '---Single Gaussian'
    print '---Peak @',popt[1]
    print '---FWHM',abs(2*np.sqrt(2*math.log1p(2))*popt[2])
    print 'Goodness of fit, R^2: %0.4f' % (1-rsqu_n1/rsqu_d)
    print
    if double:
        print '---Double Gaussian'
        print '---Peak @',popt2[1]
        print '---FWHM',abs(2*np.sqrt(2*math.log1p(2))*popt2[2])
        print 'Goodness of fit, R^2:',1-rsqu_n2/rsqu_d
        print

    
    if double:
        pkpos = popt2[1]
        pkfwhm = abs(2*np.sqrt(2*math.log1p(2))*popt2[2])
    else:
        pkpos = popt[1]
        pkfwhm = abs(2*np.sqrt(2*math.log1p(2))*popt[2])

    if plot:
        title_str = 'Gaussian fit for Peak'
        fit_str =  'q = %0.2f 1/A\nFWHM = %0.4f 1/A\nR^2=%0.4f' % (pkpos,pkfwhm,1-rsqu_n2/rsqu_d)
        plt.plot(x,y,'r+',label='Data')
        plt.plot(x,gaussian(x,*popt),'b-',label='Fit: 1 Gaussian')
        if double:        
            plt.plot(x,doublegaussian(x,*popt2),'g-',label='Fit: 2 Guassians')
        plt.legend()
        plt.xlabel('q (1/A)')
        plt.ylabel('Intensity')
        plt.text(plx,ply,fit_str)
        plt.title(title_str)
        plt.show()
    
    return(pkpos,pkfwhm)

def data_gaussian_fit(args,x,y,pknum):
    '''
    Fits one or two Gaussian functions.
    '''
    meanx = sum(x)/float(len(x))
    meany = sum(y)/float(len(y))
    sigma = np.sqrt(sum(y*(x-meanx)**2)/float(len(x)))
    
    plx =  0.05*(max(x)-min(x)) + min(x)
    ply = -0.2*(max(y)-min(y)) + max(y)

    ## ASSUMES PEAK IN CENTER FOR FIRST GUESS
    #popt,pcov = optimize.curve_fit(gaussian,x,y,p0=[np.max(y),meanx,sigma])
    try:
        popt,pcov = optimize.curve_fit(gaussian,x,y,p0=[np.max(y),meanx,sigma])
    except:
        popt = [1,1,1]
    
    
    if args.instru:
        a,b,c = popt
        popt2,pcov2 = optimize.curve_fit(doublegaussian,x,y,p0=[a,b,c,np.min(y),meanx,sigma])

    rsqu_n1 = 0
    rsqu_n2 = 0
    rsqu_d = 0
    for i in range(x.shape[0]):
        rsqu_n1 = (y[i] - gaussian(x[i],*popt))**2 + rsqu_n1
        if args.instru:
            rsqu_n2 = (y[i] - doublegaussian(x[i],*popt2))**2 + rsqu_n2
        rsqu_d = (y[i] - meany)**2 + rsqu_d

    if args.plot:
        print '---Single Gaussian'
        print '---Peak @',popt[1]
        print '---FWHM',abs(2*np.sqrt(2*math.log1p(2))*popt[2])
        print 'Goodness of fit, R^2: %0.4f' % (1-rsqu_n1/rsqu_d)
        print
        if args.instru:
            print '---Double Gaussian'
            print '---Peak @',popt2[1]
            print '---FWHM',abs(2*np.sqrt(2*math.log1p(2))*popt2[2])
            print 'Goodness of fit, R^2:',1-rsqu_n2/rsqu_d
            print
    
    if args.instru:
        pkpos = popt2[1]
        pkfwhm = abs(2*np.sqrt(2*math.log1p(2))*popt2[2])
    else:
        pkpos = popt[1]
        pkfwhm = abs(2*np.sqrt(2*math.log1p(2))*popt[2])

    if args.plot:
        title_str = 'Gaussian fit for Peak %i' % (pknum+1)
        fit_str =  '2th = %0.2f deg.\nFWHM = %0.4f deg.\nR^2=%0.4f' % (pkpos,pkfwhm,1-rsqu_n2/rsqu_d)
        plt.plot(x,y,'r+',label='Data')
        plt.plot(x,gaussian(x,*popt),'b-',label='Fit: 1 Gaussian')
        if args.instru:        
            plt.plot(x,doublegaussian(x,*popt2),'g-',label='Fit: 2 Guassians')
        plt.legend()
        plt.xlabel('2th (deg.)')
        plt.ylabel('Intensity')
        plt.text(plx,ply,fit_str)
        plt.title(title_str)
        plt.show()
    
    return(pkpos,pkfwhm)
    
##########################################################################
def gaussian(x,a,b,c):
    return a*np.exp(-(x-b)**2/(2*c**2))

##########################################################################
def doublegaussian(x,a1,b1,c1,a2,b2,c2):
    return a1*np.exp(-(x-b1)**2/(2*c1**2))+a2*np.exp(-(x-b2)**2/(2*c2**2))

##########################################################################
def poly_func(x,a,b,c):
    return a*x**2 + b*x + c
    
##########################################################################
def data_poly_fit(x,y):
    '''
    Fits a set of data with to a second order polynomial function.
    '''
    
    n = len(x)
    plx =  0.05*(max(x)-min(x)) + min(x)
    ply = -0.25*(max(y)-min(y)) + max(y)
    meany = sum(y)/n

    try:
        popt,pcov = optimize.curve_fit(poly_func,x,y,p0=[1,1,1])
    except:
        print 'WARNING: scipy.optimize.curve_fit was unsuccessful.'
        return [1,1,1]

    rsqu_n = 0
    rsqu_d = 0
    for i in range(x.shape[0]):
        rsqu_n = (y[i] - poly_func(x[i],*popt))**2 + rsqu_n
        rsqu_d = (y[i] - meany)**2 + rsqu_d

    print '---Polynomial Fit'
    print '---  U',popt[0]
    print '---  V',popt[1]
    print '---  W',popt[2]
    print 'Goodness of fit, R^2:',1-rsqu_n/rsqu_d
    print
    fit_str = 'B^2 = U [tan(TH)]^2 + V tan(TH) + W\n\nU = %f\nV = %f\nW = %f\n\nR^2 = %0.4f'
    
    plt.plot(x,y,'r+',label='Data')
    plt.plot(x,poly_func(x,*popt),'b-',label='Poly. Fit')
    plt.legend()
    plt.xlabel('tan(TH)')
    plt.ylabel('FWHM^2 (degrees)')
    plt.text(plx,ply,fit_str % (popt[0],popt[1],popt[2],1-rsqu_n/rsqu_d))
    plt.show()
    
    return popt

##########################################################################
def file_length(filename):

    ##########################################################################
    ## Open .dat file for reading
    ##
    f=open(filename,'r')

    ##########################################################################
    ## Determine length of file
    ##
    eof = 0
    count = 0
    while not(eof):
        line = f.readline()
        s = line.split()
        if len(s)>0:
            count = count + 1
        else:
            eof = 1
    if VERBOSE:
        print '\n%s has %i lines.' % (filename,count)

    ##########################################################################
    ## Close file
    ##
    f.close()

    return(count)    

##########################################################################

##########################################################################
def read_datfile(filename):
    '''
    Reads text file continaining two columns of data.
    mkak 2016.10.05 --> perhaps replace with xy_file_reader
    '''
    with open(filename,'r') as f:
        lines = f.readlines()
    filelen = len(lines)

    x, y = [], []
    for line in lines:
        x += [float(line.split()[0])]
        y += [float(line.split()[1])]        

    if VERBOSE:
        print('\nFinished reading file %s.' % filename)

    return np.array(x),np.array(y)   

##########################################################################
def read_peakfile(peakfile):

    (d,I) = xy_file_reader(peakfile,char=',')
    for i,val in enumerate(d):
        if val <= 0:
            d = np.delete(d,i)
            I = np.delete(I,i)
    q = convertd_q(d)

    pkqlist = [q,I]
   
    qmin = np.min([MINq,np.min(q)])
    qmax = np.max([MAXq,np.max(q)])

    q1 = int((qmax-qmin)/STEPq)+1
    q2 = np.shape(q)[0]
    q3 = q1 + q2
   
    newq   = np.zeros(q3)
    newint = np.zeros(q3)
    
    newq[0]   = qmax
    newint[0] = 0

    j = 0
    for k in range(q3-1):
        if j < q2:
            if newq[k] > q[j]:
                newq[k+1]   = newq[k] - STEPq
                newint[k+1] = 0
            else:
                newq[k+1]   = q[j]
                newint[k+1] = I[j]
                j = j + 1
        else:
            newq[k+1]   = newq[k] - STEPq
            newint[k+1] = 0
            
    return np.array(pkqlist),np.array(newq),np.array(newint)

##########################################################################
def generate_hkl(maxhkl=8,symmetry=None):

    ## Generate hkl list
    maxhkl = 8
    hkllist = []
    for i in range(maxhkl):
        for j in range(maxhkl):
            for k in range(maxhkl):
                hkllist.append([i,j,k])

    return hkllist


def calculate_peaks(ciffile):
    '''
    Calculate structure factor, F from cif
    mkak 2016.09.22
    '''

    ## Calculate the wavelength/energy
    wvlgth = LAMBDA
    try:
        energy = xu.utilities.lam2en(wvlgth)
    except:
        hc = constants.value(u'Planck constant in eV s') * \
                       constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m
        energy = hc/(self.wavelength*(1e-10))*1e3
    
    ## Generate hkl list
    hkllist = generate_hkl()

    ## Set an upper bound on calculations
    qmax=10
    #qmax = ((4*math.pi)/wvlgth)*np.sin(np.radians(twthmax/2))
    twthmax = 2*np.degrees(np.arcsin((wvlgth*qmax)/(4*math.pi)))


    try:
        ## Open CIF using xu functions
        cif_strc = xu.materials.Crystal.fromCIF(ciffile)
    except:
        print('xrayutilities error: Could not read %s' % os.path.split(ciffile)[-1])
        return
        
    ## For each hkl, calculate q and F
    q_cif, F_cif = [],[]
    qlist, Flist = [],[]
    for hkl in hkllist:
        qvec = cif_strc.Q(hkl)
        q = np.linalg.norm(qvec)
        if q < qmax:
            F = cif_strc.StructureFactor(qvec,energy)
            if np.abs(F) > 0.01 and np.linalg.norm(qvec) > 0:
                q_cif += [q,q,q]
                F_cif += [0,np.abs(F),0]
                qlist += [q]
                Flist += [np.abs(F)]

    if F_cif and max(F_cif) > 0:
        q_cif = np.array(q_cif)
    else:
        print('Could not calculate any structure factors.')
        return
    
    return np.array([qlist,Flist]),np.array(q_cif),np.array(F_cif)

##########################################################################
def write_rawfile(a,b,filename):

    ##########################################################################
    ## Open .raw file for writing
    ##
    open(filename,'w')

    ##########################################################################
    ## Write values to file
    ##
    for i in range(a.shape[0]):
        f.write('%s %s\n' % (a[i],b[i]))

    ##########################################################################
    ## Close file
    ##    
    f.close()
    print('\nCreated file %s.' % filename)

    return()

##########################################################################
def convertq_2th(q,wavelength):

    #print wavelength

    if np.shape(q):  
        twth = np.zeros(q.shape[0])
        for i in range(q.shape[0]):
            twth[i] = 2*math.degrees(math.asin((wavelength*q[i])/(4*math.pi)))
    else:
        twth = 2*math.degrees(math.asin((wavelength*q)/(4*math.pi)))
            
    return(twth)

##########################################################################
def convertd_q(d):

    q = 2*math.pi/d
    #if np.shape(d):  
    #    q = np.zeros(d.shape[0])    
    #    for i in range(d.shape[0]):
    #        q[i] = 2*math.pi/d[i] if d[i] > 0 else 0
    #else:
    #    q = 2*math.pi/d
            
    return(q)


##########################################################################
def convert2th_q(twth,wavelength):

    if np.shape(twth):  
        q = np.zeros(twth.shape[0])
        for i in range(twth.shape[0]):
            q[i] = ((4*math.pi)/wavelength)*math.sin(math.radians(twth[i]/2))
    else:
        q = ((4*math.pi)/wavelength)*math.sin(math.radians(twth/2))
        
    return(q)

##########################################################################
def plot_diff(x,int,tag):

    ## Plot intensity as a function of 2theta/d/q...
    ##plt.figure(2*ind+1)
    #plt.figure()
    plt.plot(x, int,'-',label=tag)
    #plt.xlabel('Two theta (degrees)')
    #plt.xlabel('q (1/A)')
    plt.ylabel('Intensity (counts)')
    #plt.title()
    #plt.xlim(min2th,max2th)

##########################################################################
def find_y(x,stdx,stdy):

    len_x   = x.shape[0]
    len_std = stdx.shape[0]
    
    y = np.zeros(len_x)
     
    for i in range(1,len_x):
        for j in range(1,len_std):
            if x[i] > stdx[j] and x[i] < stdx[j-1]:
                y[i] = stdy[j] + ((stdy[j-1]-stdy[j])/(stdx[j-1]-stdx[j]))*(x[i]-stdx[j])
                
    return y

##########################################################################
def trim_range(x,y,xmin,xmax):

    maxi = -1
    mini = 0
    for i,val in enumerate(x):
        mini = i if val < xmin else mini
        maxi = i if val < xmax else maxi
   
    return x[mini:maxi],y[mini:maxi]

##########################################################################
def calc_peak(q1,int1): # inputs: q, intensity

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
    
    ## Plot diffraction pattern and data.
    plt.figure()
    plot_diff(x,b,'Lorentzian')
    plot_diff(x,c,'Gaussian')
    plot_diff(newx,d,'Voigt')
    plt.legend()
    plt.show()

##########################################################################
def instr_broadening(pkqlist,q,intensity,u,v,w): 

    ## Broadening calculation performed in 2theta - not q
    twthlist = convertq_2th(pkqlist[0],LAMBDA)
    twth = convertq_2th(q,LAMBDA)

    ## TERMS FOR INSTRUMENTAL BROADENING
    Bi = np.zeros(np.shape(pkqlist)[1])
    for i in range(np.shape(pkqlist)[1]):
        thrad = math.radians(twthlist[i]/2)
        Bi[i] = np.sqrt(u*(math.tan(thrad))**2+v*math.tan(thrad)+w)
        
    ## Define intensity array for broadened peaks
    intenB = np.zeros(np.shape(q)[0])
    
    ## Loop through all peaks
    for i in range(np.shape(pkqlist)[1]):

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
        qG = convert2th_q(twthG,LAMBDA)

        ## Calculate peak for corresponding width
        intBi = A*np.exp(-(twthG-B)**2/(2*c_i**2))
        ## Normalize to correct intensity
        intBi = norm_pattern(intBi,A)

        ## Interpolate peak onto q scale and add
        nintensity = find_y(q,qG,intBi)        
        for j in range(np.shape(intenB)[0]):
            intenB[j] = nintensity[j] + intenB[j]
            
    intenB = norm_pattern(intenB,intensity)

    return(intenB)

##########################################################################

##########################################################################
def size_broadening(pkqlist,q,u,v,w,nsize,pk_shift): 

    #global LAMBDA
    #pk_shift = 1.00307298
    
    ## Broadening calculation performed in 2theta - not q
    twth = convertq_2th(q,LAMBDA)
##    twthlist = convertq_2th(pkqlist[0],0.3917)
    twthlist = convertq_2th(pkqlist[0],LAMBDA*pk_shift)


    ## TERMS FOR INSTRUMENTAL BROADENING
    Bi = np.zeros(np.shape(pkqlist)[1])
    for i in range(np.shape(pkqlist)[1]):
##    len_list = len(pkqlist[0])
##    Bi = pkqlist[0]
##    for i in range(len_list):
        thrad = math.radians(twthlist[i]/2)
        Bi[i] = np.sqrt(u*(math.tan(thrad))**2+v*math.tan(thrad)+w)


    ## TERMS FOR SIZE BROADENING
    ## FWHM(2th) = (C*LAMBDA)/(D*math.cos(math.radians(twth/2)))
    ## FWHM(q)   = (C*LAMBDA)/D*(1/np.sqrt(1-termB))

    D = nsize/10 # convert size from nm to A
    C = 1.1 # shape factor?
    #C = 1.0 # shape factor (1 for sphere)
    termB = ((LAMBDA*pkqlist[0])/(2*math.pi))**2
    Bs = (C*LAMBDA)/D*(1/np.sqrt(1-termB))
    
        
    ## Define intensity array for broadened peaks
    intenB = np.zeros(np.shape(q)[0])
    
    ## Loop through all peaks
    for i in range(np.shape(pkqlist)[1]):
    
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
                plot_diff(twthG,intBi,'instrument') 
                plot_diff(twthG,intBs,'size')
                plot_diff(twthG,intBm,'comb.')
                #plt.legend()
                #plt.show()
            
            new_intensity = np.convolve(intBs,intBi,'same')
            ## Normalize to correct intensity
            new_intensity = norm_pattern(new_intensity,A)
        
            shift2th = find_max(twthG,new_intensity)
            twthG = twthG - (B-shift2th)

            qG = convert2th_q(twthG,LAMBDA)
                        
            nintensity = find_y(q,qG,new_intensity)        
        
            ## Interpolate peak onto q scale and add
            for j in range(np.shape(intenB)[0]):
                intenB[j] = nintensity[j] + intenB[j]


            if i < 10 and noplot == 0:
                print('2theda shift is %0.4f' %(B-shift2th))
                plot_diff(twthG,new_intensity,'conv.')
                plt.legend()
                plt.show()
                
    intenB = scale_100(intenB)
            

    return(intenB)

##########################################################################
def norm_pattern(intensity,scale_int):

    max_int = np.max(intensity)
    scale = np.max(scale_int)
    intensity = intensity/max_int*scale
    
    return(intensity)

##########################################################################
def scale_100(intensity):

    intensity = norm_pattern(intensity,100)
    
    return(intensity)

##########################################################################
def calc_fraction(intensity,fraction):

## THIS NEEDS TO BE INCORPORATED.
    
    return intensity*fraction

##########################################################################
def fit_uvw(args,data_q,data_int):

    print '\nFitting instrumental broadening parameters...'

    bkgrd = 100
    pkct = 0
    ilist = np.zeros(100)
    qlist = np.zeros(100)
    for i in range(1,np.shape(data_int)[0]-1):
        if data_int[i] > data_int[i-1] and data_int[i] > data_int[i+1] and pkct < 10:
            if data_int[i] > bkgrd and data_q[i] > MINq and data_q[i] < MAXq:
                pkct = pkct + 1
                ilist[pkct] = i
                qlist[pkct] = data_q[i]
                #print('Peak %i found at %0.3f 1/A.' % (pkct,qlist[pkct]))
    if VERBOSE:
        print('%i peaks found.' % pkct)

    #pkct = 14 ## OVERRIDE
    fit_2th  = np.zeros(pkct)
    tanth    = np.zeros(pkct)
    fit_FWHM = np.zeros(pkct)
    sqFWHM   = np.zeros(pkct)
    HW = 15
    for i in range(pkct):
        j = ilist[i+1]
        if VERBOSE: # and args.plot:
            print('Fitting peak #%i' % (i+1))
        if j > HW and abs(np.shape(data_int)[0]-j) > HW:
            minval = int(j - HW)
            maxval = int(j + HW)
        else:
            print('need to limit range')

        
        xdata = data_q[minval:maxval]
        ydata = data_int[minval:maxval]
        
        xdata = convertq_2th(xdata,LAMBDA)
        (fit_2th[i],fit_FWHM[i]) = data_gaussian_fit(args,xdata,ydata,i)
        tanth[i] = math.tan(math.radians(fit_2th[i]/2)) 
        sqFWHM[i] = fit_FWHM[i]**2
        #print(fit_2th[i],fit_FWHM[i])    

    (u,v,w) = data_poly_fit(tanth,sqFWHM)
    
    if VERBOSE:
        print '\nInstrumental broadening parameters:'
        print '---  U',u
        print '---  V',v
        print '---  W',w
        print

    return(u,v,w)

##########################################################################
def find_max(q,intensity):

    max_int = np.max(intensity)

    if intensity.shape[0] != intensity.shape[0]:
        raise IOError('Array lengths do not match.')
    for i in range(intensity.shape[0]):
        if intensity[i] == max_int:
            max_q = q[i]
 
    return(max_q)
##########################################################################
def checkparameter(args):

    ## Check to make sure LAMBDA is postitive and .dat file exists
    if LAMBDA <= 0:
        raise IOError('Wavelength has to be a positive number.')
    if not os.path.exists(DATfile):
        raise IOError('File %s does not exist.' % DATfile)
    if args.csvfile and not os.path.exists(args.csvfile):
        raise IOError('File %s does not exist.' % args.csvfile)    
    if PEAKfile and not os.path.exists(PEAKfile):
        raise IOError('File %s does not exist.' % PEAKfile)
        
    return(args)
##########################################################################
def plot_patterns(args):

    ## Plot diffraction pattern and data.
    if args.skip:
        print('Skipping diffraction data plot.')
    else:
        print('\nPlotting:')
        letint = ord('a')
        fit_str = ''
        plt.figure()
        
        fit_str = '%s\nSpecimen: %s' % (fit_str,DATfile)
        fit_str = '%s\nWavelength: %0.4f A' % (fit_str,LAMBDA)
        if abs((PKshift-1))*10000 > 1:
            fit_str = '%s (shift: %0.4f per.)' % (fit_str,(PKshift-1)*100)
        else:
            fit_str = '%s (no shift)' % (fit_str)

        ytext = 0.2*(np.max(DATA_INT)-np.min(DATA_INT))+np.min(DATA_INT)        
        xtext = 0.6*(np.max(DATA_Q)-np.min(DATA_Q))+np.min(DATA_Q)
        
        ## i. DATA
 
        try:
            plot_diff(DATA_Q,RAW_INT,'Raw data')
            print '  %s. RAW DATA' % chr(letint)
            plot_diff(DATA_Q,DATA_INT,'Data, no Kapton') 
            print '  %s. DATA, NO KAPTON' % chr(letint)
            plot_diff(DATA_Q,KAPT_INT,'Kapton') 
            print '  %s. KAPTON' % chr(letint)
        except:
            plot_diff(DATA_Q,DATA_INT,'Data')
            print '  %s. RAW DATA' % chr(letint)        
        

        letint = letint + 1

        ## ii. STANDARD (broadened)
        if NPsize and PEAKfile:
            ## a. both INTRUMENT + SIZE BROADENING
            plot_diff(DATA_Q,CALC_INT,'Calculated pattern')
            print '  %s. CALCULATED: both INTRUMENT + SIZE BROADENING' % chr(letint)
            letint = letint + 1
            diff_int = DATA_INT-CALC_INT
            fit_str = '%s\n\nParticle size: %0.2f nm\n\nInstrument:\nU = %0.4f\nV = %0.4f\nW = %0.4f' % (fit_str,NPsize,instrU,instrV,instrW)
        elif PEAKfile:
            ## b. just INTRUMENT BROADENING
            plot_diff(DATA_Q,CALC_INT,'Calculated pattern')
            print '  %s. CALCULATED: just INTRUMENT BROADENING' % chr(letint)
            letint = letint + 1
            diff_int = DATA_INT-CALC_INT
            fit_str = '%s\n\nInstrument:\nU = %f\nV = %f\nW = %f' % (fit_str,instrU,instrV,instrW)
        
        ## ii. DIFFERENCE
        try:
            diff_int
        except:
            junk = 5
        else:
            print '  %s. DIFFERENCE between DATA and CALCULATED' % chr(letint)
            letint = letint + 1
            plot_diff(DATA_Q,diff_int,'Difference')

        ## iv. BACKGROUND
        if args.back:
            print '  %s. BACKGROUND' % chr(letint)
            letint = letint + 1
            plot_diff(DATA_Q,BKGD_INT,'Background')
            fit_str = '%s\n\nBackground:' % (fit_str)
            if args.bkfit:
                fit_str = '%s (Fitted values.)' % (fit_str)
            fit_str = '%s\na = %0.4f\nb = %0.4f\nc = %0.4f' % (fit_str,bkgdA,bkgdB,bkgdC)

            
        ## v. STANDARD (delta)
        if PEAKfile:
            print '  %s. IDEAL STANDARD' % chr(letint)
            letint = letint + 1
            plot_diff(args.peak_q,args.peak_int*0.85,'Standard')

        ## vi. CSV data
        if args.csvfile:
            ## c. CSV file
            #(stand_d,stand_int) = read_csvfile(args.csvfile)
            (stand_d,stand_int) = xy_file_reader(args.csvfile,char=',')
            stand_q = convertd_q(stand_d,LAMBDA)
            ## Trim
            (stand_q,stand_int) = trim_range(stand_q,stand_int,MINq,MAXq)
            ## Normalize
            stand_int = find_y(DATA_Q,stand_q,norm_pattern(stand_int,DATA_INT))
            
            #plot_diff(stand_q,stand_int,'Standard')
            plot_diff(DATA_Q,stand_int,'CSV file')
            print '  %s. CSV file' % chr(letint)
            letint = letint + 1
            fit_str = '%s\n\nCSV file: %s' % (fit_str,args.csvfile)
            
        ##plot_diff(DATA_Q[:-1],np.diff(signal.savgol_filter(DATA_INT, 51, 3))*100,'Derivative')


        plt.xlabel('q (1/A)')
        plt.xlim(MINq,MAXq)
        plt.ylim(-15,105)
        
        try:
            CALC_INT
        except:
            junk = 7
        else:
            fit_str = '%s\n\nR^2 = %0.4f' % (fit_str,calcRsqu(DATA_INT,CALC_INT))
        if args.bkfit:
            fit_str = '%s\n\nMethod: %s' % (fit_str,fitMETHOD)
        
        plt.text(xtext,ytext,fit_str)
        plt.legend()
        print
        if args.save:
            pngfile = '%s.png' % DATfile.split('.')[0]
            plb.savefig(pngfile, bbox_inches='tight')
            print('Saved diffraction data: %s' % pngfile)
        else:
            plt.show()

    return()
##########################################################################    
def calcRsqu(y,ycalc):
    
    ss_res = 0
    ss_tot = 0
    
    ymean = sum(y)/float(len(y))
    
    for i in range(ycalc.shape[0]):
        ss_res = ss_res + (y[i] - ycalc[i])**2
        ss_tot = ss_tot + (y[i] - ymean)**2
       
    Rsqu = 1 - (ss_res/ss_tot)

    return(Rsqu)

#########################################################################
def remove_kapton(data_q,data_int):

    global KAPT_INT

    #kapton_q,kapton_int = read_datfile(KAPTfile)
    kapton_q,kapton_int = xy_file_reader(KAPTfile)

    ##min_index, min_ value = min(enumerate(kapton_int), key=operator.itemgetter(1))
    max_index, max_value = max(enumerate(kapton_int), key=operator.itemgetter(1))
   
    KAPT_INT = kapton_int*(data_int[max_index]/kapton_int[max_index])
    data_int = data_int - KAPT_INT
    data_int = scale_100(data_int)
    
    return data_int
    #return
    
##########################################################################    
def patternbroadening(data_q,nsize,pk_shift):

    ## Particle size broadening and instrumental broadening
    if NPsize and PEAKfile:
        calc_int = size_broadening(pkQlist,data_q,instrU,instrV,instrW,nsize,pk_shift)

    ## Instrumental broadening
    elif PEAKfile:
        calc_int = instr_broadening(pkQlist,data_q,DATA_INT,instrU,instrV,instrW)

    return calc_int

##########################################################################    
def background(q,a,b,c):

    return a*q**2 + b*q + c

##########################################################################
def fit_background(my_pars, data_q, data_int):

    a = my_pars['a'].value
    b = my_pars['b'].value
    c = my_pars['c'].value
    
    if ERRORcheck == 1:
        print(a,b,c)
    
    calc_int = background(data_q,a,b,c)

    return calc_int - data_int # minimize difference between data and calculated

##########################################################################
def fit_pattern(my_pars, data_q, data_int):

    nsize = my_pars['nsize'].value
    a = my_pars['a'].value
    b = my_pars['b'].value
    c = my_pars['c'].value
    pk_shift = my_pars['pk_shift'].value
    
    if ERRORcheck == 1:
        print(nsize,a,b,c,pk_shift)
    
    calc_int = patternbroadening(data_q,nsize,pk_shift)+background(data_q,a,b,c)

    return calc_int - data_int # minimize difference between data and calculated

#########################################################################
def fit_with_minimization():

    global bkgdA,bkgdB,bkgdC
    global instrU,instrV,instrW
    global NPsize, PKshift
    
    ## Create a set of Parameters
    my_pars = Parameters()

    ##my_pars.add('nsize', value= NPsize, min= 3.0,  max=100.0)
    my_pars.add('nsize', value= NPsize, min= 3.0,  max=100.0,vary=False)
    my_pars.add('pk_shift',  value=PKshift,  min=0.98, max=1.02,vary=False)
    
    if bkgdA == 0:
        minA = -100
        maxA =  100
    else:
        minA = -1.2*abs(bkgdA)
        maxA =  1.2*abs(bkgdA)

    if bkgdB == 0:
        minB = -100
        maxB =  100        
    else:
        minB = -1.2*abs(bkgdB)
        maxB =  1.2*abs(bkgdB)
    if bkgdC == 0:
        minC = 0
        maxC = max(DATA_INT)
    else:
        minC =  0.8*bkgdC
        maxC =  1.2*bkgdC
        
    print(minA,minB,minC,maxA,maxB,maxC)

    my_pars.add('a', value=bkgdA, min=minA, max=maxA)
    my_pars.add('b', value=bkgdB, min=minB, max=maxB)
    my_pars.add('c', value=bkgdC, min=minC, max=maxC)
    
    print
    # Do fit
    
    ## First, fit background alone:
    result = minimize(fit_background, my_pars, args=(DATA_Q,DATA_INT),method=fitMETHOD)
    
    my_pars.add('a',  value=result.params['a'].value)
    my_pars.add('b',  value=result.params['b'].value)
    my_pars.add('c',  value=result.params['c'].value)
    
    ## Now, include more fitting...    
    result = minimize(fit_pattern, my_pars, args=(DATA_Q,DATA_INT),method=fitMETHOD)

    ## Default: method='leastsq'
    ## method='nelder'
    ## didn't quit, more or less landed on parameters:
    ## 6.43477783086 0.609120604191 -9.76760647538 56.4337260003

#    # write error report
#    report_fit(result)
    
    NPsize = result.params['nsize'].value
    bkgdA  = result.params['a'].value
    bkgdB  = result.params['b'].value
    bkgdC  = result.params['c'].value
    PKshift  = result.params['pk_shift'].value
        
    return
#########################################################################
def struc_from_cif(ciffile,verbose=True):

    if verbose:
        print('Reading: %s' % ciffile)

    try:
        ## Open CIF using xu functions
        cif_strc = xu.materials.Crystal.fromCIF(ciffile)
    except:
        print('xrayutilities error: Could not read %s' % os.path.split(ciffile)[-1])
        return
        
    return cif_strc 
#########################################################################
def calc_all_F(cry_strc,energy,maxhkl=10,qmax=10,twthmax=None,verbose=True):
    '''
    Calculate F for one energy for range of hkl for one structure
    mkak 2016.09.22
    '''
    ## Generate hkl list
    hkllist = []
    for i in range(maxhkl):
        for j in range(maxhkl):
            for k in range(maxhkl):
                hkllist.append([i,j,k])

    ## Calculate the wavelength
    wvlgth = xu.utilities.en2lam(energy)
    if twthmax:
        qmax = ((4*math.pi)/wvlgth)*np.sin(np.radians(twthmax/2))
    else:
        twthmax = 2*np.degrees(np.arcsin((wvlgth*qmax)/(4*math.pi)))

    q = []
    F_norm = []

    if verbose:
        print('Calculating XRD pattern for: %s' % cry_strc.name)
        
    ## For each hkl, calculate q and F
    for hkl in hkllist:
        qvec = cry_strc.Q(hkl)
        qnorm = np.linalg.norm(qvec)
        if qnorm < qmax:
            F = cry_strc.StructureFactor(qvec,energy)
            if np.abs(F) > 0.01 and np.linalg.norm(qvec) > 0:

                q.append(qnorm)
                q.append(qnorm)
                q.append(qnorm)

                F_norm.append(0)
                F_norm.append(np.abs(F))
                F_norm.append(0)

    if F_norm and max(F_norm) > 0:
        q = np.array(q)
        F_norm = np.array(F_norm)/max(F_norm)
        return q,F_norm
    return
#########################################################################
def show_F_depend_on_E(cry_strc,hkl,emin=500,emax=20000,esteps=5000):
    '''
    Dependence of F on E for single hkl for one cif
    mkak 2016.09.22
    '''
    E = np.linspace(emin,emax,esteps)
    F = cry_strc.StructureFactorForEnergy(cry_strc.Q(hkl), E)

    return E,F
#########################################################################
class XRDSearchGUI(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
    
        ## Constructor
        dialog = wx.Dialog.__init__(self, None, title='Crystal Structure Database Search',size=(500, 440))
        ## remember: size=(width,height)
        self.panel = wx.Panel(self)

        LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        
        ## Mineral search
        lbl_Mineral  = wx.StaticText(self.panel, label='Mineral:' )
        self.Mineral = wx.TextCtrl(self.panel,   size=(270, -1))
        #mineral_list = [] #['None']
        #self.Mineral = wx.Choice(self.panel,    choices=mineral_list)

        ## Author search
        lbl_Author  = wx.StaticText(self.panel, label='Author:' )
        self.Author = wx.TextCtrl(self.panel,   size=(270, -1))

        ## Chemistry search
        lbl_Chemistry  = wx.StaticText(self.panel, label='Chemistry:' )
        self.Chemistry = wx.TextCtrl(self.panel,   size=(175, -1))
        self.chmslct  = wx.Button(self.panel,     label='Specify...')
        
        ## Cell parameter symmetry search
        lbl_Symmetry  = wx.StaticText(self.panel, label='Symmetry/parameters:' )
        self.Symmetry = wx.TextCtrl(self.panel,   size=(175, -1))
        self.symslct  = wx.Button(self.panel,     label='Specify...')
        
        ## General search
        lbl_Search  = wx.StaticText(self.panel,  label='Keyword search:' )
        self.Search = wx.TextCtrl(self.panel, size=(270, -1))


        ## Define buttons
        self.rstBtn = wx.Button(self.panel, label='Reset' )
        hlpBtn = wx.Button(self.panel, wx.ID_HELP    )
        okBtn  = wx.Button(self.panel, wx.ID_OK      )
        canBtn = wx.Button(self.panel, wx.ID_CANCEL  )

        ## Bind buttons for functionality
        self.rstBtn.Bind(wx.EVT_BUTTON,  self.onReset     )
        self.chmslct.Bind(wx.EVT_BUTTON, self.onChemistry )
        self.symslct.Bind(wx.EVT_BUTTON, self.onSymmetry  )

        self.sizer = wx.GridBagSizer( 5, 6)

        self.sizer.Add(lbl_Mineral,    pos = ( 1,1)               )
        self.sizer.Add(self.Mineral,   pos = ( 1,2), span = (1,3) )

        self.sizer.Add(lbl_Author,     pos = ( 2,1)               )
        self.sizer.Add(self.Author,    pos = ( 2,2), span = (1,3) )

        self.sizer.Add(lbl_Chemistry,  pos = ( 3,1)               )
        self.sizer.Add(self.Chemistry, pos = ( 3,2), span = (1,2) )
        self.sizer.Add(self.chmslct,   pos = ( 3,4)               )

        self.sizer.Add(lbl_Symmetry,   pos = ( 4,1)               )
        self.sizer.Add(self.Symmetry,  pos = ( 4,2), span = (1,2) )
        self.sizer.Add(self.symslct,   pos = ( 4,4)               )

        self.sizer.Add(lbl_Search,     pos = ( 5,1)               )
        self.sizer.Add(self.Search,    pos = ( 5,2), span = (1,3) )

        self.sizer.Add(hlpBtn,        pos = (11,1)                )
        self.sizer.Add(canBtn,        pos = (11,2)                )
        self.sizer.Add(self.rstBtn,   pos = (11,3)                )
        self.sizer.Add(okBtn,         pos = (11,4)                )
        
        self.panel.SetSizer(self.sizer)

        self.Show()
#########################################################################
    def onChemistry(self,event):
        print('Will eventually show Periodic Table...')
#########################################################################
    def onSymmetry(self,event):
        XRDSymmetrySearch()
#########################################################################
    def onReset(self,event):
        self.Mineral.Clear()
        self.Author.Clear()
        self.Chemistry.Clear()
        self.Symmetry.Clear()
        self.Search.Clear()
#########################################################################            
class XRDSymmetrySearch(wx.Dialog):
    """"""

    def __init__(self):
    
        ## Constructor
        dialog = wx.Dialog.__init__(self, None, title='Cell Parameters and Symmetry',size=(460, 440))
        ## remember: size=(width,height)
        self.panel = wx.Panel(self)


        LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        
        ## Lattice parameters
        lbl_a = wx.StaticText(self.panel,    label='a (A)' )
        self.min_a = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_a = wx.TextCtrl(self.panel, size=(100, -1))

        lbl_b = wx.StaticText(self.panel,    label='b (A)' )
        self.min_b = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_b = wx.TextCtrl(self.panel, size=(100, -1))

        lbl_c = wx.StaticText(self.panel,    label='a (A)' )
        self.min_c = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_c = wx.TextCtrl(self.panel, size=(100, -1))

        lbl_alpha = wx.StaticText(self.panel,    label='alpha (deg)' )
        self.min_alpha = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_alpha = wx.TextCtrl(self.panel, size=(100, -1))

        lbl_beta = wx.StaticText(self.panel,    label='beta (deg)' )
        self.min_beta = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_beta = wx.TextCtrl(self.panel, size=(100, -1))

        lbl_gamma = wx.StaticText(self.panel,    label='gamma (deg)' )
        self.min_gamma = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_gamma = wx.TextCtrl(self.panel, size=(100, -1))

        SG_list = ['']
        sgfile = 'space_groups.txt'
        if not os.path.exists(sgfile):
            parent, child = os.path.split(__file__)
            sgfile = os.path.join(parent, sgfile)
            if not os.path.exists(sgfile):
                raise IOError("Space group file '%s' not found!" % sgfile)
        sg = open(sgfile,'r')
        for sgno,line in enumerate(sg):
            try:
                sgno = sgno+1
                SG_list.append('%3d  %s' % (sgno,line))
            except:
                sg.close()
                break

        
        lbl_SG = wx.StaticText(self.panel, label='Space group:')
        self.SG = wx.Choice(self.panel,    choices=SG_list)

        ## Define buttons
        self.rstBtn = wx.Button(self.panel, label='Reset' )
        hlpBtn = wx.Button(self.panel, wx.ID_HELP   )
        okBtn  = wx.Button(self.panel, wx.ID_OK     )
        canBtn = wx.Button(self.panel, wx.ID_CANCEL )

        ## Bind buttons for functionality
        self.rstBtn.Bind(wx.EVT_BUTTON,  self.onReset     )

        self.sizer = wx.GridBagSizer( 5, 6)

        self.sizer.Add(lbl_a,          pos = ( 1,1) )
        self.sizer.Add(self.min_a,     pos = ( 1,2) )
        self.sizer.Add(self.max_a,     pos = ( 1,3) )

        self.sizer.Add(lbl_b,          pos = ( 2,1) )
        self.sizer.Add(self.min_b,     pos = ( 2,2) )
        self.sizer.Add(self.max_b,     pos = ( 2,3) )

        self.sizer.Add(lbl_c,          pos = ( 3,1) )
        self.sizer.Add(self.min_c,     pos = ( 3,2) )
        self.sizer.Add(self.max_c,     pos = ( 3,3) )

        self.sizer.Add(lbl_alpha,      pos = ( 4,1) )
        self.sizer.Add(self.min_alpha, pos = ( 4,2) )
        self.sizer.Add(self.max_alpha, pos = ( 4,3) )

        self.sizer.Add(lbl_beta,       pos = ( 5,1) )
        self.sizer.Add(self.min_beta,  pos = ( 5,2) )
        self.sizer.Add(self.max_beta,  pos = ( 5,3) )

        self.sizer.Add(lbl_gamma,      pos = ( 6,1) )
        self.sizer.Add(self.min_gamma, pos = ( 6,2) )
        self.sizer.Add(self.max_gamma, pos = ( 6,3) )

        self.sizer.Add(lbl_SG,         pos = ( 7,1) )
        self.sizer.Add(self.SG,        pos = ( 7,2) )


        self.sizer.Add(hlpBtn,        pos = (11,1)  )
        self.sizer.Add(canBtn,        pos = (11,2)  )
        self.sizer.Add(self.rstBtn,   pos = (11,3)  )
        self.sizer.Add(okBtn,         pos = (11,4)  )

        self.panel.SetSizer(self.sizer)

        self.Show()
#########################################################################
    def onReset(self,event):
        self.min_a.Clear()
        self.max_a.Clear()
        self.min_b.Clear()
        self.max_b.Clear()
        self.min_c.Clear()
        self.max_c.Clear()
        self.min_alpha.Clear()
        self.max_alpha.Clear()
        self.min_beta.Clear()
        self.max_beta.Clear()
        self.min_gamma.Clear()
        self.max_gamma.Clear()
        self.SG.SetSelection(0)


def registerLarchPlugin():
    return ('_diFFit', {})
