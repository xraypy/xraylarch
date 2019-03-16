"""
Fluorescence Intensity calculations:
   Y. Choi

calculates fluorescence intensities for multiple elements at a fixed incident x-ray energy.
measured fluorescence depends on net fluorescence yield and transmission.
included are:
    (with incident energy dependence): atomic crosssection, fluorescence yield for each edge,
                                     transition probability for each emission line,
    (with emitted fluorescence energy dependence): transmission to vortex detector, detector efficiency.
global variables: re, Barn, Nav, pre_edge_margin, fluo_emit_min, det_res
AtNum2f1f2Xect: needs datafile readf1f2a.py which is from chantler table
cal_NetYield2: for XRF calculations.  major and minor lines are calculated
                output as 'Elemental_Sensitivity.txt'

sim_spectra: keeps individual emission lines with significant intensity without weight-averaging
             each element can have a different relative concentration.
             makes strongest emission to 100 and scales the rest accordingly.
             output as 'simSpectrum.txt'
             runs sim_GaussPeaks() to emulate measure intensity as gaussian peak
             output as 'simSpectrum.plot'
             runs cal_NetYield2()
5/24/2010:  self-absorption effect included, 4 options (top, bottom, all, surface)
            Each option makes different elemental distribution,
            but substrate elements are always distributed evenly.
            get_ChemName(), nominal_density() are in readf1f2a.py
5/26/2010:   incident x-ray attenuation effect added, and incident angle effect is also added.
            refraction effect added to the angle, below critical angle, th=1e-10.
6/4/2010:    SampleMatrix2 has two layers and each layer can have different composition
            Class ElemFY is for fluorescence elements with AtSym, Conc, tag attribues,
            inputs in SimSpect, Cal_NetFyield2 changed.
            Concentrations are normalized to the concentration of the substrate1 molecule.
            Ex) with CaCO3[2.71g/cc]/Fe2O3[5.26g/cc] substrate, Ca concentration is 1.0 meaning 1.63e22 Ca/cc
            and Fe concentration is 2.43 = 2*1.98e22/1.63e22 where 1.98e22 is number density (/cc) of Fe2O3
6/8/2010:    now using python2.6 instead of 2.5
4/14/2011:  fluo_det.py: detection dependent part in fluorescence yield.
            Original fluo.py was modified to fluo_new.py.
            readf1f2a.py is used instead of original readf1f2.py
            fluo_new.py is being split into two.
            fluo_elem.py is for elemtnal dependence: fluorescenc yield, crosssection.
            fluo_det.py is for detection dependnece: detector efficiency, attenuation, sample
            * for attenuation, total cross-section([4]) is used instead of photoelectric ([2]).
            ** for fluorescence yield, photoelectric is used.
"""


import math
import numpy
import sys
from larch.utils.physical_constants import AVOGADRO, BARN
from larch.xray import xray_delta_beta, chemparse

pre_edge_margin=150.    # FY calculated from 150 eV below the absorption edge.
fluo_emit_min=500.      # minimum energy for emitted fluorescence.  ignore fluorescence emissions below 500eV
det_res=100.            # detector resoltuion in eV, used in sim_GaussPeaks

'''
----------------------------------------------------------------------------------------------------------
class: Material, ElemFY, SampleMatrix2
----------------------------------------------------------------------------------------------------------
'''
class Material:
    def __init__(self, composition, density, thickness=1):
        self.composition=composition        # ex) SiO2
        self.density=density              # in g/cm^3
        self.thickness=thickness            # in cm
        self.la=1.0                         #absoprtion length in cm
        self.trans=0.5                      # transmission.
        self.absrp=0.5                 # absorption
        self.delta=0.1                  # index of refraction, real part
        self.beta=0.1                   # index of refraction, imaginary part
        # MN replace
        elements = chemparse(composition)
        AtomList = elements.keys()
        AtomIndex = elements.values()
        AtomWeight=0
        for (ii, atom) in enumerate(AtomList):
            # MN replace...
            AtWt= atomic_mass(atom)
            index=AtomIndex[ii]
            AtomWeight = AtomWeight + index*AtWt
        NumberDensity=density*AVOGARDRO/AtomWeight
        self.NumDen=NumberDensity       # number of molecules per cm^3
        self.AtWt=AtomWeight            # weight per mole
    def getLa(self, energy, NumLayer=1.0):    # get absorption legnth for incident x-ray, NumLayer for multiple layers
        # MN replace...
        temp= xray_delta_beta(self.composition, self.density, energy)
        # returns delta, beta, la_photoE, Nat, la_total
        self.delta=temp[0];     self.beta=temp[1]
        self.la=temp[2]  # temp[4] (total) instead of temp[2] (photoelectric)
        if NumLayer<0:  NumLayer=0     # Number of layers cannot be less than zero
        self.trans=math.exp(-self.thickness*NumLayer/self.la)  #la attenuation length cm, NumLayer for multiple layers
        self.absrp=1-self.trans


class ElemFY:  # fluorescing element
    def __init__(self, AtomicSymbol='Fe', Concentration=10e-6, tag='dilute'):
        temp=AtomicSymbol[0].upper()  # capitalize the first letter
        self.AtSym=temp+AtomicSymbol[1:]
        self.Conc=Concentration
        self.tag=tag  # dilute, substrate1, substrate2


class SampleMatrix2:  # sample matrix for self-absorption correction, 6/3: two layers with different compositions
    def __init__(self, composition1='Si', density1=2.33, thickness1=0.1, \
                 composition2='Si', density2=2.33, thickness2=0.1,
                 angle0=45.0, option='surface'):
        self.composition1 = composition1     # ex) Fe2O3
        # MN replace:
        out= chemparse(composition1)         # output from get_ChemName
        self.ElemList1 = out.keys()          # list of elments in matrix: 'Fe', 'O' for Fe2O3
        self.ElemInd1 = out.values()         # list of index: 2, 3 for Fe2O3
        # self.ElemFrt1 = out[2]             # list of fraction: 0.4, 0.6 for Fe2O3
        self.density1 = density1             # in g/cm^3
        self.thickness1 = thickness1         # top layer thickness in cm
        self.composition2 = composition2
        # MN replace with chemparse()
        out=chemparse(composition2)
        self.ElemList2 = out.keys()              # for the bottom substrate
        self.ElemInd2 = out.values()
        # self.ElemFrt2 = out[2]
        self.density2 = density2
        self.thickness2 = thickness2         # bottom layer thickness in cm
        self.angle = angle0*math.pi/180.     # in radian, incident beam angle, surface normal =pi/2
        self.option = option                 # option for fluorescing element location, surface/top/bottom
        self.la1 = 1.0                       # absoprtion length in cm
        self.delta1 = 0.1                    # index of refraction, real part correction
        self.beta1 = 0.1                     # index of refraction, imaginary part
        self.Nat1 = 1.0                      # atomic number density of the Fe2O3, 1e22 Fe2O3 atoms /cm^3
        self.la2 = 1.0
        self.delta2 = 0.1
        self.beta2 = 0.1
        self.Nat2 = 1.0                     # atomic number density of the first element, 1e22 Fe2O3 atoms/cm^3
        self.scale = 1.0                    # weighted average over the depth range: sum of (trans*factors)
        self.scale1 = 1.0                   # sum of (trans*1.0) this is for substrate element in top layer
        self.scale2 = 1.0                   # sum of (trans*thickness2/thickness1) for substrate element in bottom layer
        self.ElemListFY =[]                 # fluorescing element
        self.ElemFrtFY =[]                  # fraction for fluorescing element
        self.Nat1=1                  # atomic number density in atoms/cc, for example # of Fe2O3/cm^3 for Fe2O3 substrate
        self.Nat2=1                  # atomic number density in atoms/cc
        substrate1_material = Material(composition1, density1)
        AtNumDen1 = substrate1_material.NumDen      #  substrate1
        substrate2_material = Material(composition2, density2)
        AtNumDen2 = substrate2_material.NumDen      #  substrate2, fixed 8/12/10
        self.Nat1=AtNumDen1
        self.Nat2=AtNumDen2
        self.txt=''
        text1='substrate1:%6.3e %s/cm^3' % (AtNumDen1, composition1)
        #print(text1)
        text2='substrate2:%6.3e %s/cm^3' % (AtNumDen2, composition2)
        self.txt=text1+'  '+text2
        print(self.txt)
        # atom.conc is normalized to the number density of substrate1 molecule
        for (ii, item) in enumerate(self.ElemList1):
            # MN replace:
            if atomic_number(item)>=12:       # ignore elements below Mg
                #atom=ElemFY(item, self.ElemFrt1[ii], 'substrate1')
                atom=ElemFY(item, self.ElemInd1[ii], 'substrate1')
                # eg. for Fe2O3, Fe concentration is 2 (=2 x Fe2O3 number density)
                self.ElemListFY.append(atom)
        for (ii, item) in enumerate(self.ElemList2):
            # MN replace:
            if atomic_number(item)>=12:       # ignore elements below Mg
                #atom=ElemFY(item, self.ElemFrt2[ii], 'substrate2')
                atom=ElemFY(item, self.ElemInd2[ii]*AtNumDen2/AtNumDen1, 'substrate2')
                self.ElemListFY.append(atom)
        numLayer=100                        # each layer is sliced into 100 sublayers.
        self.depths=[]                      # depth values for calculation
        for ii in range(numLayer):
            step=1.0/numLayer
            self.depths.append(step*ii*self.thickness1)
        for ii in range(numLayer):
            step=1.0/numLayer
            self.depths.append(step*ii*self.thickness2+self.thickness1)
        self.factors=[]                     # 1 or pre if element present at each depth
        pre=self.thickness2/self.thickness1 # prefactor, if two layers have different thickness
        if self.option=='surface':          # fluorescecing atoms present in only on the surface
            for ii in range(len(self.depths)):
                if ii==0:
                    self.factors.append(1.0)
                else:
                    self.factors.append(0.0)
        if self.option=='all':              # fluorescecing atoms present throughout
            for ii in range(len(self.depths)):
                if self.depths[ii]<self.thickness1:
                    self.factors.append(1.0)
                else:
                    self.factors.append(pre)
        if self.option=='top':              # fluorescecing atoms present only in the top layer
            for ii in range(len(self.depths)):
                if self.depths[ii]<self.thickness1:
                    self.factors.append(1.0)
                else:
                    self.factors.append(0.0)
        if self.option=='bottom':           # fluorescecing atoms present only in the bottom layer
            for ii in range(len(self.depths)):
                if self.depths[ii]<self.thickness1:
                    self.factors.append(0.0)
                else:
                    self.factors.append(pre)
        # note: fluorescing substrate atoms present throughout regardless of the option.
        self.trans=[]                       # transmission to surface for emitted fluorescence
        self.absrp=[]                       # absorption until surface for emitted fluorescence
        self.inten0=[]                      # incident x-ray intensity at each depth
        for ii in range(len(self.depths)):
            self.trans.append(0.5)
            self.absrp.append(0.5)
            self.inten0.append(0.5)
    def getPenetration(self, energy0):  # incident x-ray penetration(attenuation)
        # refraction at air/top layer interface
        # MN replace:
        temp=f1f2.get_delta(self.composition1, self.density1, energy0)  # energy0: incident x-ray energy
        delta1=temp[0];  beta1=temp[1]
        la1=temp[4]     # in cm, temp[4] instead of temp[2], using total instead of photoelectric
        self.la1=la1                                        # absorption length in microns at incident x-ray energy
        angle_critical1 = (2.0*delta1)**(0.5)               # in radian, critical angle for total external reflection
        if angle_critical1>=self.angle:                     # below critical angle, the corrected should be zero.
            angle_corrected1=1.0e-15                        # a smaller number instead of zero
        else:                                               # above critical angle
            angle_corrected1 = (self.angle**2.0 - angle_critical1**2.0)**(0.5)  # in radian
        # refraction at top/bottom layers interface
        # MN replace:
        temp=f1f2.get_delta(self.composition2, self.density2, energy0)  # energy0: incident x-ray energy
        delta2=temp[0];  beta2=temp[1];
        la2=temp[4]     # in cm, temp[4] instead of temp[2], using total instead of photoelectric
        self.la2=la2                                            # absorption length in cm at incident x-ray energy
        angle_corrected2 = ( 2.0-(1.0-delta1)/(1.0-delta2)*(2.0-angle_corrected1**2) )**0.5
        # using Snell's law, assume beta effect not ignificant, in radian
        for (ii, depth) in enumerate(self.depths):
            if self.depths[ii]<self.thickness1:                 # top layer
                beampath = depth/math.sin(angle_corrected1)     # in cm
                inten0 = math.exp(-beampath/la1)                # attenuated incident beam intensity at depths
            else:                                               # bottom layer
                beampath1 = self.thickness1/math.sin(angle_corrected1)
                beampath2 = (depth-self.thickness1)/math.sin(angle_corrected2)
                inten0 = math.exp(-beampath1/la1)*math.exp(-beampath2/la2)
            self.inten0[ii] = inten0                            # incident x-ray attenuation
    def getLa(self, energy, NumLayer=1.0):  # emitted fluorescence trasmission attenuation up to top surface
        transmitted=1.0
        # MN replace:
        temp=f1f2.get_delta(self.composition1, self.density1, energy)  # energy is for fluorescence
        self.delta1 = temp[0]
        self.beta1 = temp[1]
        self.la1 = temp[4]      # in cm, temp[4] instead of temp[2], using total instead of photoelectric
        # absorption length in cm at emitted fluorescence energy
        # temp[3]: atomic number density of the first element in atoms/cc
        # MN replace:
        temp=f1f2.get_delta(self.composition2, self.density2, energy)  # energy is for fluorescence
        self.delta2 = temp[0]
        self.beta2 = temp[1]
        self.la2 = temp[4]                                      # absorption length in cm at emitted fluorescence energy
        # in cm, temp[4] instead of temp[2], using total instead of photoelectric
        angle_exit = (math.pi/2.0 - self.angle)                 # becomes 90 at a small incident angle
        for (ii, depth) in enumerate(self.depths):
            if self.depths[ii]<self.thickness1:                 # top layer
                 transmitted=math.exp(-depth/math.sin(angle_exit)*NumLayer/self.la1)
            else:                                               # bottom layer
                transmitted2 = math.exp(-(depth-self.thickness1)/math.sin(angle_exit)*NumLayer/self.la2)
                transmitted1 = math.exp(-self.thickness1/math.sin(angle_exit)*NumLayer/self.la1)
                transmitted = transmitted2*transmitted1
        self.trans[ii] = transmitted
        self.absrp[ii] = 1.0 - transmitted
        scale = 0.0; scale1=0.0; scale2=0.0
        for (ii,trans) in enumerate(self.trans):
            scale = scale + trans*self.inten0[ii]*self.factors[ii]
            if self.depths[ii]<self.thickness1:
                scale1 = scale1 + trans*self.inten0[ii]*1.0
            else:   # if thickness2 is different from thickness1, weight differently
                scale2 = scale2 + trans*self.inten0[ii]*(self.thickness2/self.thickness1)
        # scale, scale1, scale2: emitted fluorescence transmission and depth profile
        self.scale = scale      # sum of (trans*factors) for nonsubstrate FY
        self.scale1 = scale1    # sum of (trans*factors) for substrate FY. factors=1, top layer
        self.scale2 = scale2    # sum of (trans*factors) for substrate FY. factors=pre, bttom layer


'''
----------------------------------------------------------------------------------------------------------
Detector efficiency, fluorescence attenuation
----------------------------------------------------------------------------------------------------------
'''
# WD30 used for XSW, sample-->He-->Kapton-->Collimator-->Detector
# WD60 used for XRM, sample-->Collimator-->Detector
# eV1 is fluorescence energy in eV
# xHe=1 means Helium gas from sample to WD60 collimator.
# xAl=1 means 1 layer of 1.5mil Al foil as attenuator
# xKapton=1 means 1 layer of 0.3 mil Kapton (
# WD=6 means working distance of 6cm for the detector.

def Assemble_QuadVortex(eV1):
    # quad vortex detector efficiency. eV1: fluo energy
    net=1.
    BeVortex=Material('Be', 1.85, 0.00125)
    SiO2Vortex=Material('SiO2', 2.2, 0.00001)
    SiVortex=Material('Si', 2.33, 0.035)
    BeVortex.getLa(eV1, 1)  # one Be layer in Vortex
    SiO2Vortex.getLa(eV1, 1)    # oxide layer on Si detection layer
    SiVortex.getLa(eV1, 1)  # Si detection layer, what's absorbed is counted.
    net=net*BeVortex.trans*SiO2Vortex.trans*SiVortex.absrp
    if (print2screen):
        print( '%.3f eV : BeVortex.trans=%.3e , SiO2Vortex.trans=%.3e, SiVortex.absrp=%.3e, Det_efficiency=%.3e' % (eV1, BeVortex.trans,  SiO2Vortex.trans, SiVortex.absrp, net))
    return net


def Assemble_Collimator(eV1, xHe=1, xAl=0,xKapton=0, WD=6.0, xsw=0):
    # from sample surface to detector
    # xsw=0/1/-1,  6cm, 3cm, no collimator
    # He_path depends on the collliator.
    if xHe==1:
        He_path=WD
    else:
        He_path=0.
    air_path = WD-He_path
    kapton_inside=0  # kapton inside collimator.  no collimator, no kapton_inside
    if xsw==0:  # WD60mm collimator
        kapton_inside=1                 # collimator has thin Kapton on the second aperture
        if xHe==1:
            air_path = 1.51             # 1.51cm between second aperture and Be of Vortex
        else:
            air_path=WD
        He_path = WD-air_path           # He is between sample surface to the second aperture of xrm collimator
    if xsw==1:  # WD30mm colllimator
        kapton_inside=1                 # collimator has thin Kapton on the second aperture
        if xHe==1:      # modified 11/18/2010
            He_path = 1.088   # from sample surface to Kapton cover/collimator
            air_path = WD - He_path            # 1.912cm between second aperture and Be of Vortex
            xKapton = xKapton+1         # one Kapton film used to fill He from sample surface to collimator
        else:
            air_path = WD0;     He_path=0
    air=Material('N1.56O0.48C0.03Ar0.01Kr0.000001Xe0.0000009', 0.0013, air_path)
    kapton=Material('C22H10O4N2', 1.42, 0.000762)       # 0.3mil thick
    HeGas=Material('He', 0.00009, He_path)
    AlFoil=Material('Al', 2.72, 0.00381)                # 1.5mil thick
    kaptonCollimator=Material('C22H10O4N2', 1.42, 0.000762) # 0.3mil thick
    #
    air.getLa(eV1, 1)   # 1 means number of layers here.
    kapton.getLa(eV1, xKapton)  #number of Kapton layers before collimator
    HeGas.getLa(eV1, xHe) # number of He gas layers, default=0
    AlFoil.getLa(eV1, xAl)  # number of Al foil,  default=0
    kaptonCollimator.getLa(eV1, kapton_inside)   # without collimator, no addition kapton inside
    #
    net=air.trans*HeGas.trans
    net=net*kapton.trans*AlFoil.trans*kaptonCollimator.trans
    if print2screen:
            print('%.3f eV: air.trans=%.3e, HeGas.trans=%.3e, kapton.trans=%.3e, AlFoil.trans=%.3e, kaptonCollimator.trans=%.3e, net=%.3e' %  \
            (eV1, air.trans, HeGas.trans, kapton.trans, AlFoil.trans,kaptonCollimator.trans, net))
    #print('%.3f eV: air.la=%.3e, HeGas.la=%.3e, kapton.la=%.3e' % (eV1, air.la, HeGas.la, kapton.la))
    return net


def Assemble_Detector(eV1, xHe=1, xAl=0,xKapton=0, WD=6.0, xsw=0):
    det_efficiency=Assemble_QuadVortex(eV1)
    trans2det=Assemble_Collimator(eV1, xHe, xAl,xKapton, WD, xsw)
    net=det_efficiency*trans2det
    return net



'''
----------------------------------------------------------------------------------------------------------
Combine detector, transmission, sample self-absorption, and fluorescing element distribution/concentration.
----------------------------------------------------------------------------------------------------------
'''
# this function is for XSW/XRM.
def cal_NetYield2(eV0, Atoms, xHe=0, xAl=0, xKapton=0, WD=6.0, xsw=0, WriteFile='Y' , xsect_resonant=0.0, sample=''):
    #   incident energy, list of elements, experimental conditions
    #   this one tries Ka, Kb, Lg, Lb, La, Lb
    angle0=45.; textOut=''
    if xsw!=0 and WriteFile=='Y':  print( 'XSW measurements')
    if sample=='':
        Include_SelfAbsorption='No'
    else:
        Include_SelfAbsorption='Yes'
        angle0=sample.angle/math.pi*180.
        textOut=sample.txt          # substrate concentration
    NetYield=[];    NetTrans=[]; Net=[];    out2='';	net=0.0
    text0=''
    edges      =['K',  'K',  'L1', 'L1', 'L2', 'L2', 'L2', 'L3', 'L3', 'L3']
    Fluo_lines =['Ka', 'Kb', 'Lb', 'Lg', 'Ln', 'Lb', 'Lg', 'Ll', 'La', 'Lb']
    outputfile='Elemental_Sensitivity.txt'
    if WriteFile=='Y':
        fo=open(outputfile, 'w')
        desc=' '
        if xHe==0:   desc=' not '
        if xsw==-1:
            out1='# 13IDC XRM/XSW using QuadVortex, incident x-ray energy at '+str(eV0)+' eV at '+str(angle0)+' degrees \n'
            out1+='# Helium path'+desc+'used, '+str(xAl)+' Al attenuators, '+str(xKapton+1)+' Kapton attenuators, '\
              +str(WD)+' cm working distance. \n'
        else:
            out1='# 13IDC XRM/XSW using QuadVortex + collimator,  incident x-ray energy at '+str(eV0)+' eV at '+str(angle0)+' degrees \n'
            out1+='# Helium path'+desc+'used, '+str(xAl)+' Al attenuators, '+str(xKapton)+' Kapton attenuators, '\
              +str(WD)+' cm working distance. \n'
        print( out1)
        fo.write(out1)
        if sample!='':
            for stuff in Atoms:
                text1='%6.3e %s/cm^3' % (stuff.Conc*sample.Nat1, stuff.AtSym)
                text0=text0+' '+text1
        textOut=textOut+' '+text0       # substrate concentration + other concentrations
        out1='# '+text0+'\n'
        if print2screen:
            print( out1)
        fo.write(out1)
        out1='%s\t%s\t%s   \t%s   \t%s   \t%s   \t%s\n' % ('atom', 'emit', 'emit_energy', 'yield', 'transmission', 'net_sensitivity', 'sensitivity*concentration')
        if print2screen:
            print( out1)
        fo.write(out1)
    for (ii, atom) in enumerate(Atoms):
        # MN replace:
        atnum=f1f2.AtSym2AtNum(atom.AtSym)
        # MN replace:
        temp=f1f2.AtNum2f1f2Xsect(atnum, eV0)
        xsect=temp[2]                           # photo-electric cross-section for fluorescence yield, temp[4] is total for attenuation
        con=atom.Conc
        for (nn, edge) in enumerate(edges):
            emit=Fluo_lines[nn]
            fy, emit_eV, emit_prob = fluo_yield(atom.AtSym, edge, emit, eV0)
            print(emit)
            if fy==0.0 or emit_prob==0:
                continue                        # try next item if FY=0
            else:
                if xsect_resonant!=0.0:         # use input value near edge
                    xsect=xsect_resonant	# for cross-section near absoprtion edge
                #print(xsect,fy,emit_prob)
                net_yield=xsect*fy*emit_prob    # net_yield --> cross-section, yield, emission_probability
                # net transmission --> transmission from surface through detector
## ------------------   [self-absorption]     ------------------------------
                trans_SelfAbsorp = 1.0           # for self-absorption.
                if Include_SelfAbsorption=='Yes':
                    sample.getPenetration(eV0)   # incident x-ray attenuation
                    if fy*emit_eV*emit_prob==0:  # any one of three is zero
                        break                    # skip
                    sample.getLa(emit_eV)
                    # account for incident x-ray attenuation, emitted x-ray attenuation
                    trans_SelfAbsorp = sample.scale         # for elements that are not part of substrate
                    if (atom in sample.ElemListFY):
                        if atom.tag=='substrate1':
                            trans_SelfAbsorp = sample.scale1  # for elements that are part of top substrate
                        if atom.tag=='substrate2':
                            trans_SelfAbsorp = sample.scale2  # for elements that are part of bottom substrate
## ----------------------------------------------------------------------------
            net_trans = Assemble_Detector(emit_eV, xHe, xAl,xKapton, WD, xsw)
            net = net_yield*net_trans*trans_SelfAbsorp  # elemental sensitivity
            inten = net*con  # sensitivity * concentration
            if WriteFile=='Y':
                out1='%s\t%s\t%6.1f   \t%.3e   \t%.3e   \t%.3e   \t%.3e\n' % (atom.AtSym+'_'+edge, emit, emit_eV, net_yield, net_trans, net, inten)
                fo.write(out1)
            if print2screen:
                print('%s %s %6.1f net_yield=%.3e net_trans=%.3e net=%.3e\t' % (atom.AtSym+'_'+edge, emit, emit_eV, net_yield, net_trans, net))
            #print(out1+'  %s, depth-dependent factor= %6.4f' % (atom.tag, trans_SelfAbsorp))
            if emit=='Kb' and fy!=0:        # if above K edge, don't bother trying L edges
                break
    return textOut


#def sim_spectra(eV0, Atoms, Conc, xHe=0, xAl=0, xKapton=0, WD=6.0, xsw=0, sample=''):
def sim_spectra(eV0, Atoms, xHe=0, xAl=0, xKapton=0, WD=6.0, xsw=0, sample=''):
    # sample=sample matrix with object attribues to add self-absorption effect
    # Atoms is a list with elements that have attributes AtSym, Conc, tag
    if xsw==-1:     xKapton=xKapton-1   # no collimator
    Include_SelfAbsorption='Yes'
    Print2Screen='No'
    if sample=='': Include_SelfAbsorption='No'
    if xsw!=0:  print('XSW measurements')
    xx=[]; yy=[]; tag=[];   intensity_max=-10.0; LoLimit=1e-10
    angle0=''; text1=''
    if sample!='':      # sample matrix option is used
        angle0=str(sample.angle*180./math.pi)
        angle0=angle0[:5]
        for (ii, item) in enumerate(sample.ElemListFY):  # add matrix elements to the lists
            Atoms.append(item)
    outputfile='simSpectrum_table.txt'
    fo=open(outputfile, 'w')
    out1='#incident x-ray at '+str(eV0)+' eV and '+angle0+' Deg.\n'
    if Print2Screen=='Yes': print(out1)
    fo.write(out1)
    out1='#Emission\tenergy(eV)\tintensity \n'
    if Print2Screen=='Yes': print(out1)
    fo.write(out1)
    out2='#'
    for (ix,atom) in enumerate(Atoms):
        # MN replace:
        atnum=f1f2.AtSym2AtNum(atom.AtSym)
        # con=Conc[ix]
        con=atom.Conc
        out2=out2+atom.AtSym+'['+str(con)+']   '
        for edge in ['K', 'L1', 'L2', 'L3']:
            # MN replace:
            temp=f1f2.AtNum2f1f2Xsect(atnum, eV0)
            xsect=temp[2]           # photoelectric crosssection for each element at incident x-ray, fluorescence yield
            # MN replace:
            temp=elam.use_ElamFY(atom.AtSym, edge)
            edge_eV=float(temp[2])   # absorption edge
            if eV0>edge_eV:
                fy=float(temp[3])
                for EmitLine in temp[4]:
                    EmitName=EmitLine[1]
                    emit_eV=float(EmitLine[2])
                    emit_prob=float(EmitLine[3])
                    if emit_eV<fluo_emit_min:  continue        # ignore fluorescence below fluo_emit_min (global variable)
                    name = atom.AtSym + '_'+ EmitName
                    # net transmission --> transmission from surface through detector
## ------------------   [self-absorption]     ------------------------------
                    trans_SelfAbsorp = 1.0              # for self-absorption.
                    if Include_SelfAbsorption=='Yes':
                        sample.getPenetration(eV0)      # incident x-ray attenuation
                        eV0str=str(eV0)
                        text1=' absorption_length1(%seV)= %2.2e%s \
                                absorption_length2(%seV)= %2.2e%s' % (eV0str, sample.la1*1.e4, 'microns', eV0str, sample.la2*1.e4, 'microns')
                        # text1 is added to sample.txt later
                        sample.getLa(emit_eV)           # emitted fluorescence attenuation
                        trans_SelfAbsorp = sample.scale # for elements that are not part of substrate
                        if (atom in sample.ElemListFY):
                            if atom.tag=='substrate1':
                                trans_SelfAbsorp = sample.scale1  # for elements that are part of top substrate
                            if atom.tag=='substrate2':
                                trans_SelfAbsorp = sample.scale2  # for elements that are part of bottom substrate
## ----------------------------------------------------------------------------
                    trans = Assemble_Detector(emit_eV, xHe, xAl,xKapton, WD, xsw)
                    intensity = con * fy * emit_prob * xsect * trans * trans_SelfAbsorp
                    if intensity<LoLimit: continue            # skip weak emission, arbtraray limit =1e-10.
                    if intensity>intensity_max: intensity_max=intensity
                    xx.append(emit_eV);    yy.append(intensity);   tag.append(name)
    for ix in range(len(yy)):
        yy[ix]=yy[ix]/intensity_max*100.00          # makes the strongest line to 100.0
        out1='%s\t%f\t%f \n' % (tag[ix], xx[ix], yy[ix])
        if Print2Screen=='Yes': print(out1)
        fo.write(out1)
    if Print2Screen=='Yes': print(out2)
    fo.write(out2)
    fo.close()
    out1=sim_GaussPeaks(xx, yy, det_res, eV0)        # det_res: detector resoultion for Gaussian width (global variable)
    if Include_SelfAbsorption=='Yes':
        sample.txt=sample.txt+text1                 # sample.txt is combined to output of cal_NetYield
    text=cal_NetYield2(eV0, Atoms, xHe, xAl, xKapton, WD, xsw, sample=sample)  # calculate net yield with weight-averaged emission
    print(out2)
    return text  # cal_NetYield2 output is str with number densities of elements


def sim_GaussPeaks(xx, yy, width, eV0):  #xx, yy: lists, width: a peak width, eV0: incident energy
    xline=[]; yline=[]; dX=10.0;    minX=fluo_emit_min #10eV steps, lowest-->fluo_emit_min
    amp=100                             # arbitrary multiplier to shift up spectrum
    NumOfSteps = int((eV0-minX)/dX)
    NumOfPeaks = len(xx)
    for ix in range(NumOfSteps+1):
        xline.append(0);  yline.append(0)
    for (iy,peak) in enumerate(xx):
        X0=float(peak)
        Y0=float(yy[iy])
        for ix in range(NumOfSteps+1):
            energy = minX + ix*dX
            inten = Y0*math.exp(-((energy-X0)/width)**2)*amp
            xline[ix]=energy
            yline[ix]+=inten
    outputfile='simSpectrum_plot.txt'
    fo=open(outputfile, 'w')
#    DetectorLimit=1e5                   # upperlimit for total counts to 1e5 (1e5 CPS)
    LoLimit=0.001                         # low limit for each channel
#    total=0.0
    factor=1.0
    for ix in range(NumOfSteps+1):
        if yline[ix]<LoLimit: yline[ix]=LoLimit
#        total+=yline[ix]  # add counts
#    factor=total/DetectorLimit
    for ix in range(NumOfSteps+1):
        yline[ix]=yline[ix]/factor
        out1=str(xline[ix])+'\t'+str(yline[ix])+'\n'
        fo.write(out1)
    fo.close()
    #return xline, yline


class input_param:
    def __init__(self, eV0=14000,
                 Atoms=[],
                 xHe=0.0,
                 xAl=0,
                 xKap=0,
                 WD=6.0,
                 xsw=0):
        if Atoms==[]:
            atom1=ElemFY()
            Atoms.append(atom1)
        self.eV0=eV0
        #incident x-ray energy in eV
        list1=[]; list2=[]
        for item in Atoms:
            list1.append(item.AtSym)
            list2.append(item.Conc)
        self.Atoms=list1
        #elements list
        self.Conc=list2
        #relative concentrations list
        self.xHe=xHe
        #He gas path before collimator?
        self.xAl=xAl
        #number of Al foils as attenuator
        self.xKap=xKap
        #number of Kapton foils as attenuator
        self.WD=WD
        #working distance in cm
        self.xsw=xsw
        #x-ray standing wave setup?  WD=3.0 for xsw=1



# ----------------------------------------------------------------



if __name__=='__main__':
    testing = 0
    if testing:
        #atom0='Fe'
        #emission0='Ka'
        #eV0=10000.
        #edge0='K'
        #eV1=6400.
        #mat0=Material('SiO2', 2.2, 0.001)
        #mat0.getLa(8000)
        #print(mat0.la, mat0.trans)
        #print(Assemble_QuadVortex(eV1))
        #print(Assemble_Collimator(eV1, xHe=1, xAl=0,xKapton=0, WD=6.0, xsw=0))
        # MN replace:
        matrix=SampleMatrix2('CaCO3', f1f2.nominal_density('CaCO3'), 0.001,'Fe2O3', f1f2.nominal_density('Fe2O3'), 0.001, 45.,  'all')
        eV0=7500.
        Atoms=[]
        atom=ElemFY('La', 10e-6);     Atoms.append(atom)
        atom=ElemFY('Ce', 10e-6);     Atoms.append(atom)
        atom=ElemFY('Nd', 10e-6);     Atoms.append(atom)
        for (ii, item) in enumerate(matrix.ElemListFY):
            pass
        sim_spectra(eV0, Atoms, sample=matrix)  # xKapton=-1 to remove WD60, -2 for WD30
    else:
        # March 2012 for Nov2011 beamtime
        eV0 = 10000.
        print2screen=0
        Atoms = []
        atom=ElemFY('Al', 10e-6);     Atoms.append(atom)
        atom=ElemFY('Si', 10e-6);     Atoms.append(atom)
        atom=ElemFY('Ca', 10e-6);     Atoms.append(atom)
        atom=ElemFY('Cr', 10e-6);     Atoms.append(atom)
        atom=ElemFY('Mn', 10e-6);     Atoms.append(atom)
        atom=ElemFY('Fe', 10e-6);     Atoms.append(atom)
        atom=ElemFY('Ni', 10e-6);     Atoms.append(atom)
        #sim_spectra(eV0, Atoms, xHe=1, xAl=0, xKapton=0, WD=3.0, xsw=1, sample='')
        #Assemble_QuadVortex(1486.56)
        #Assemble_Collimator(1486.56, 1, 0, 0, 3., 1)
        #
        air_path = 1.088
        He_path = 1.912
        air=Material('N1.56O0.48C0.03Ar0.01Kr0.000001Xe0.0000009', 0.0013, air_path)
        kapton=Material('C22H10O4N2', 1.42, 0.000762)       # 0.3mil thick
        HeGas=Material('He', 0.00009, He_path)
        AlFoil=Material('Al', 2.72, 0.00381)                # 1.5mil thick
        #
        from math import *
        emitE = [
            1486.4, 1557.0, 1739.6, 1837.0, 3691.1, 4013.1, 5411.6,
            5947.0, 5896.5, 6492.0, 6400.8, 7059.6, 7474.4, 8266.6
            ]
        for eV1 in emitE:
            air.getLa(eV1, 1)   # 1 means number of layers here.
            print( eV1, air.la, exp(-1./air.la))


'''
def AtSym2FY(AtSym, Shell):  #returns fluorescence yield using atomic symbol and edge(K,L1,L2,L3,M)
    out=elam.use_ElamFY(AtSym, Shell)
    #AtSym, edge, edge-energy, FY, [ [transition, emission, energy, probability],[]...]
    FY=out[3]
    return FY

class Element:
    def __init__(self, AtNum, AtWt, f1, f2, Xsection):
        self.AtNum=AtNum
        self.AtWt=AtWt              #atomic weight g/mol
        self.f1=f1                  #real part of scattering factor
        self.f2=f2                  #imaginary part of scattering factor
        self.Xsection=Xsection      #atomic crossection Barns/atom
        # f1, f2, Xsection depends on incident x-ray energy


def setElement(AtSym, shell, eV0):
    AtNum=AtSym2AtNum(AtSym)
    AtWt=AtSym2AtWt(AtSym)
    f1f2=AtNum2f1f2Xsect(AtNum, eV0)
    AtSym=Element(AtNum, AtWt, f1f2[0], f1f2[1], f1f2[2])
    return AtSym


class input_param:
    def __init__(self, eV0=14000,
                 Atoms=[],
                 xHe=0.0,
                 xAl=0,
                 xKap=0,
                 WD=6.0,
                 xsw=0):
        if Atoms==[]:
            atom1=ElemFY()
            Atoms.append(atom1)
        self.eV0=eV0
        #incident x-ray energy in eV
        list1=[]; list2=[]
        for item in Atoms:
            list1.append(item.AtSym)
            list2.append(item.Conc)
        self.Atoms=list1
        #elements list
        self.Conc=list2
        #relative concentrations list
        self.xHe=xHe
        #He gas path before collimator?
        self.xAl=xAl
        #number of Al foils as attenuator
        self.xKap=xKap
        #number of Kapton foils as attenuator
        self.WD=WD
        #working distance in cm
        self.xsw=xsw
        #x-ray standing wave setup?  WD=3.0 for xsw=1
'''
