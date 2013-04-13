# 2/17/2011: readf1f2a.py
# read atomic scattering factors
# data file: f1f2chantler.py
# f1, f2, mu_photoelectric, mu_total
# mu_total should be used for filter transmission
# get_delta returns la for total crosssection as well

import math
#import numpy
#import f1f2_data  # old version of f1f2chantler
#import elam
import f1f2chantler as f1f2

#global variables
re=2.82e-13  #cm
Barn=1e-24   #cm^2
Nav=6.022e23  #atoms/mol


# 2/17/2011: linear interpolation, 4th order by default 
# 7/1/2011: should be -3rd order.  mu=density*Z^4/A/E^3.
def interpN(x0, listX, listY, N0=-3):  # get y0 for x0 using listX, listY, n0-th power
    num=len(listX)
    y0=0.; x00=x0**N0
    if x0<=listX[0]:
        y0=listY[0]
        return y0
    if x0>=listX[num-1]:
        y0=listY[num-1]
        return y0    
    for ii in range(0, num):
        if listX[ii]<x0<=listX[ii+1]:
            x1=float(listX[ii])**N0
            x2=float(listX[ii+1])**N0
            y1=listY[ii]
            y2=listY[ii+1]
    #print N0, x00**(1./N0), x1**(1./N0), x2**(1./N0), y1, y2        
    try:
        y0=y1+(y2-y1)/(x2-x1)*(x00-x1)
    except:
        y0=0
    return y0
        

# 2/17/2011: reading atomic scattering factors using interPN           
def AtNum2f1f2Xsect(AtNum, eV0):  # returns f1 f2, crosssection using atomic number and incident energy
    eV0impo=float(eV0)  # in eV
    data=f1f2.keVf1f2[AtNum]  # data== [[keV, f1, f2], [...], [...}
    f1=0; f2=0; Xsection=0
    xList=[]; yList=[]; zList=[]
    pList=[]; tList=[]
    for ix in range(len(data)):
        xx=float(data[ix][0])*1000.  # keV to eV
        yy=float(data[ix][1])  # f1
        zz=float(data[ix][2])  # f2
        muP=float(data[ix][3])  # photoelectric mu [cm^2/g]
        muT=float(data[ix][5])  # total mu [cm^2/g]
        xList.append(xx)
        yList.append(yy)
        zList.append(zz)
        pList.append(muP)
        tList.append(muT)
    f1=interpN(eV0, xList, yList, -3)  # interpolation with 3rd powers
    f2=interpN(eV0, xList, zList, -3)
    mu_pho=interpN(eV0, xList, pList, -3)  # interpolation with 3rd powers
    mu_tot=interpN(eV0, xList, tList, -3)
    lamb=12.39842/(eV0/1000.)*1e-8	# in cm, 1e-8cm = 1 Angstrom
    Xsection=2*re*lamb*f2/Barn    # in Barns/atom
    return [f1, f2, Xsection, mu_pho, mu_tot]

        



def AtSym2AtNum(AtSym):	 # returns atomic number using atomic symbol
    dict={'H':1,'He':2,'Li':3,'Be':4,'B':5,'C':6,'N':7,'O':8,'F':9,'Ne':10,
    'Na':11,'Mg':12,'Al':13,'Si':14,'P':15,'S':16,'Cl':17,'Ar':18,'K':19,'Ca':20,
    'Sc':21,'Ti':22,'V':23,'Cr':24,'Mn':25,'Fe':26,'Co':27,'Ni':28,'Cu':29,'Zn':30,
    'Ga':31,'Ge':32,'As':33,'Se':34,'Br':35,'Kr':36,'Rb':37,'Sr':38,'Y':39,'Zr':40,
    'Nb':41,'Mo':42,'Tc':43,'Ru':44,'Rh':45,'Pd':46,'Ag':47,'Cd':48,'In':49,'Sn':50,
    'Sb':51,'Te':52,'I':53,'Xe':54,'Cs':55,'Ba':56,'La':57,'Ce':58,'Pr':59,'Nd':60,
    'Pm':61,'Sm':62,'Eu':63,'Gd':64,'Tb':65,'Dy':66,'Ho':67,'Er':68,'Tm':69,'Yb':70,
    'Lu':71,'Hf':72,'Ta':73,'W':74,'Re':75,'Os':76,'Ir':77,'Pt':78,'Au':79,'Hg':80,
    'Tl':81,'Pb':82,'Bi':83,'Po':84,'At':85,'Rn':86,'Fr':87,'Ra':88,'Ac':89,'Th':90,
    'Pa':91,'U':92,'Np':93,'Pu':94,'Am':95,'Cm':96,'Bk':97,'Cf':98,'Es':99,'Fm':100
    }
    out=dict[AtSym]
    return out


def AtSym2AtWt(AtSym):	# returns atomic weight (g/mol) using atomic symbol
    dict={'H':1.008,'He':4.003,'Li':6.941,'Be':9.01218,'B':10.81,'C':12.011,'N':14.0067,'O':15.9994,'F':18.9984,'Ne':20.179,
    'Na':22.9898,'Mg':24.305,'Al':26.9815,'Si':28.0855,'P':30.9738,'S':32.06,'Cl':35.453,'Ar':39.948,'K':39.0983,'Ca':40.08,
    'Sc':44.9559,'Ti':47.88,'V':50.9415,'Cr':51.996,'Mn':54.938,'Fe':55.847,'Co':58.9332,'Ni':58.69,'Cu':63.546,'Zn':65.38,
    'Ga':69.72,'Ge':72.59,'As':74.9216,'Se':78.96,'Br':79.904,'Kr':83.8,'Rb':85.4678,'Sr':87.62,'Y':88.9059,'Zr':91.22,
    'Nb':92.9064,'Mo':95.94,'Tc':98.0,'Ru':101.07,'Rh':102.9055,'Pd':106.42,'Ag':107.8682,'Cd':112.41,'In':114.82,'Sn':118.69,
    'Sb':121.75,'Te':127.6,'I':126.9045,'Xe':131.29,'Cs':132.9054,'Ba':137.33,'La':138.9055,'Ce':140.12,'Pr':140.9077,'Nd':144.24,
    'Pm':145.0,'Sm':150.36,'Eu':151.96,'Gd':157.25,'Tb':158.9254,'Dy':162.5,'Ho':164.9304,'Er':167.26,'Tm':168.9342,'Yb':173.04,
    'Lu':174.967,'Hf':178.49,'Ta':180.9479,'W':183.85,'Re':186.207,'Os':190.2,'Ir':192.22,'Pt':195.08,'Au':196.9665,'Hg':200.59,
    'Tl':204.383,'Pb':207.2,'Bi':208.9804,'Po':209.0,'At':210.0,'Rn':222.0,'Fr':223.0,'Ra':226.0254,'Ac':227.0278,'Th':232.0381,
    'Pa':231.0359,'U':238.0289
    }
    out=dict[AtSym]
    return out

def AtSym2Den(AtSym):  # returns nominal density in (g/cm^3) using atomic symbol
    dict={ 
    'H':8.375E-05, 'He':1.663E-04, 'Li':5.340E-01, 'Be':1.848E+00, 'B':2.370E+00
    , 'C':1.700E+00, 'N':1.165E-03, 'O':1.332E-03, 'F':1.580E-03, 'Ne':8.385E-04
    , 'Na':9.710E-01, 'Mg':1.740E+00, 'Al':2.699E+00, 'Si':2.330E+00, 'P':2.200E+00
    , 'S':2.000E+00, 'Cl':2.995E-03, 'Ar':1.662E-03, 'K':8.620E-01, 'Ca':1.550E+00
    , 'Sc':2.989E+00, 'Ti':4.540E+00, 'V':6.110E+00, 'Cr':7.180E+00, 'Mn':7.440E+00
    , 'Fe':7.874E+00, 'Co':8.900E+00, 'Ni':8.902E+00, 'Cu':8.960E+00, 'Zn':7.133E+00
    , 'Ga':5.904E+00, 'Ge':5.323E+00, 'As':5.730E+00, 'Se':4.500E+00, 'Br':7.072E-03
    , 'Kr':3.478E-03, 'Rb':1.532E+00, 'Sr':2.540E+00, 'Y':4.469E+00, 'Zr':6.506E+00
    , 'Nb':8.570E+00, 'Mo':1.022E+01, 'Tc':1.150E+01, 'Ru':1.241E+01, 'Rh':1.241E+01
    , 'Pd':1.202E+01, 'Ag':1.050E+01, 'Cd':8.650E+00, 'In':7.310E+00, 'Sn':7.310E+00
    , 'Sb':6.691E+00, 'Te':6.240E+00, 'I':4.930E+00, 'Xe':5.485E-03, 'Cs':1.873E+00
    , 'Ba':3.500E+00, 'La':6.154E+00, 'Ce':6.657E+00, 'Pr':6.710E+00, 'Nd':6.900E+00
    , 'Pm':7.220E+00, 'Sm':7.460E+00, 'Eu':5.243E+00, 'Gd':7.900E+00, 'Tb':8.229E+00
    , 'Dy':8.550E+00, 'Ho':8.795E+00, 'Er':9.066E+00, 'Tm':9.321E+00, 'Yb':6.730E+00
    , 'Lu':9.840E+00, 'Hf':1.331E+01, 'Ta':1.665E+01, 'W':1.930E+01, 'Re':2.102E+01
    , 'Os':2.257E+01, 'Ir':2.242E+01, 'Pt':2.145E+01, 'Au':1.932E+01, 'Hg':1.355E+01
    , 'Tl':1.172E+01, 'Pb':1.135E+01, 'Bi':9.747E+00, 'Po':9.320E+00, 'At':1.000E+01
    , 'Rn':9.066E-03, 'Fr':1.000E+01, 'Ra':5.000E+00, 'Ac':1.007E+01, 'Th':1.172E+01
    } 
    out=dict[AtSym] 
    return out 

class Elements:
    def __init__(self, AtSym, eV0=7000.):  # atomic symbol and incident x-ray energy (eV)
        self.AtSym=AtSym
        self.AtNum=AtSym2AtNum(AtSym)
        self.AtWt=AtSym2AtWt(AtSym)
        f1f2=AtNum2f1f2Xsect(self.AtNum, eV0)
        self.f1=f1f2[0]
        self.f2=f1f2[1]
        self.Xsect=f1f2[2]
        self.muPho=f1f2[3]
        self.muTot=f1f2[4]



def get_ChemName(chemical):  # returns element, index, and fraction as lists
    # get_ChemName('SiO2') will return ['Si', 'O'], [1, 2], [0.333, 0.666]
    # 11/17/2010: modified to handle noninteger index
    Elem=[]; Ind=[]; Frac=[]; Pos=[]; net=0
    numpnts=len(chemical)
    if chemical[numpnts-1].isalpha():
        chemical=chemical+'1'
    for (ii, letter) in enumerate(chemical):
        if letter.isalpha():
            if letter.isupper():
                Pos.append(ii)
    for (ii, nn) in enumerate(Pos):
        if chemical[nn+1].isalpha() and chemical[nn+1].islower():
            Elem.append(chemical[nn]+chemical[nn+1])
        else:
            Elem.append(chemical[nn])
    for (ii, atom) in enumerate(Elem):
        if len(atom)==1:
            shift=0
        else:
            shift=1
        pos1=Pos[ii]
        if ii==len(Elem)-1:  # last one
            pos2=len(chemical)
        else:
            pos2=Pos[ii+1]
        inbetween=chemical[pos1+1+shift:pos2]
        if inbetween=='': inbetween='1'
        Ind.append(float(inbetween))
        net+=float(inbetween)
    for item in Ind:
        temp=float(item)/net
        Frac.append(temp)
    return Elem , Ind , Frac

def nominal_density(composition): # returns nominal density in g/cc
    dict={
        'Ag': 10.5 ,
	'Al': 2.72 ,
        'Al2O3': 3.97,  # Sapphire
	'Au': 19.37 ,  
	'Be': 1.848 ,
	'BN': 2.29, # Boron Nitride
	'C': 3.51 , # diamond
#      'C': 2.25, # graphite
	'C2F4': 2.2 ,	# Teflon
        'C3H4O2': 1.65 ,  # PAA
	'C22H10O4N2': 1.42,	 # Kapton
        'CaCO3': 2.71 ,     # Calcite
	'CaF2': 3.18,	 # Fluorite
        'Cr': 7.19 ,
	'Co': 8.9 , 
	'Cu': 8.94 , 
	'Fe': 7.86, 
        'Fe2O3': 5.26  , # hematite
	'Ge': 5.323 , 
        'H2O': 1.0 ,
        'Ir': 22.42 ,
	'KAl3Si3O12H2': 2.83 ,  # Mica
	'Mn': 7.42 ,
	'Ni': 8.9 , 
	'Pb': 11.34 , 
        'PbTiO3': 7.9 ,
        'Pd': 12.16 ,
        'Pt': 21.37 ,
        'Rh': 12.44 ,
        'Si': 2.33 ,
        'SiO2': 2.2 , # silica
	'Sr': 2.54 , 
        'SrTiO3': 5.12 , 
	'Ti': 4.54 ,
	'TiO2': 4.26,   # Rutile
	'V': 6.11 , 
	'Zn': 7.14 , 
        'ZnO': 5.7
        }
    if (dict.has_key(composition)==0):
        return 1.0
    density=dict[composition]
    return density


def get_delta(material, density, eV, indexNat=0):  # get index of refraction and absorption length for eV
    # indexNat is index for element
    temp=get_ChemName(material)
    lamb=12.39842/(eV/1000.0)*1e-8	# in cm, 1e-8cm = 1 Angstrom
    atoms=temp[0]   # list of atomic symbols
    index=temp[1]   # list of index
    fraction=temp[2]	# list of fraction
    NumComp=len(temp[0])
    ElemList=[]
    Nat=[]	# atomic number density # of atoms/cm^3
    for atom in atoms:
        OneElement=Elements(atom, eV)
        ElemList.append(OneElement)
    bot=0
    for (ix, OneElem) in enumerate(ElemList):
        bot+=float(index[ix])*float(OneElem.AtWt) #; print bot, index[ix], elements[ix].AtWt
    for (ix, OneElem) in enumerate(ElemList):
        temp=float(index[ix])*density*Nav/bot
        Nat.append(temp) #; print Nat[ix]
    bot1=0; bot2=0; bot3=0
    for (ix, OneElem) in enumerate(ElemList):
        bot1+=Nat[ix]*OneElem.f1
        bot2+=Nat[ix]*OneElem.f2	#; print Nat[ix], elements[ix].f1, elements[ix].f2
        bot3+=Nat[ix]*OneElem.f2*(OneElem.muTot/OneElem.muPho)
        # f2 is for photoelectric, so correct for total crosssection
    #print bot1, bot2, lamb
    delta=lamb**2*re/(2*math.pi)*bot1
    beta=lamb**2*re/(2*math.pi)*bot2
    la=lamb/(4*math.pi*beta)  # in cm  for photoelectric crosssection
    beta0=lamb**2*re/(2*math.pi)*bot3   # for total crosssection
    la0=lamb/(4*math.pi*beta0)  # in cm, for total crosssection
    return [delta, beta, la, Nat[indexNat], la0]

# Mar2011: get scattering factors
def get_ScatFact(atoms, energies, option='xsection'):  # photoelectric cross-section
    opt=0
    if option=='xsection' or option=='Xsection':
        outputfile='XSect.txt'
        opt=1
    else:
        outputfile='ScatFact.txt'
    fo=open(outputfile,'w')
    colname1='eV_f1f2'
    colname2='f1'
    colname3='f2'
    for atom in atoms:
        if opt==1:
            out='\n'+atom+' energy (eV), cross-section (Barns/Atom) \n'
        else:
            #out='\n'+atom+" energy (eV), f1, f2 \n"
            out='\n '+colname1+', '+colname2+atom+', '+colname3+atom+' \n'
        fo.write(out)
        atnum = AtSym2AtNum(atom)
        for eV in energies:
            temp=AtNum2f1f2Xsect(atnum, eV)
            f1=temp[0]
            f2=temp[1]
            xsect=temp[2]   #in Barns/atom
            mu_photo=temp[3]  # in cm^2/g
            mu_total=temp[4]  # in cm^2/g
            if opt==1:
                out=str(eV)+'\t'+str(xsect)+'\n'
            else:
                out=str(eV)+'\t'+str(f1)+'\t'+str(f2)+'\n'
            fo.write(out)
    fo.close()
    print 'output saved to ', outputfile

if __name__=='__main__':
    option=0
    if option==0:
        print AtNum2f1f2Xsect(26, 7000)
        print AtNum2f1f2Xsect(26, 8000)
    if option==1:
        import time
        list_eV=range(500, 30000, 100)
        # below takes 2.72 seconds
        a=time.clock()
        for eV0 in list_eV:
            AtNum2f1f2Xsect(26, eV0)
        print AtNum2f1f2Xsect(13, 35000.)
        b=time.clock()-a
        print b
    #-------------------------------------
    if option==2:
        eV0=30014.05
        temp=AtNum2f1f2Xsect(13, eV0)
        print temp[0], temp[1], temp[2], temp[3], temp[4]
        temp=get_delta('Al2O3', 3.97, 35000)
        print temp
    #-------------------------------------
    if option==3:
        import numpy
        energies=[]
        atoms=['Si', 'Fe', 'Co', 'Ni', 'Gd', 'Ta', 'Au']
        for i in numpy.arange(500., 1500., 0.2):
            energies.append(i)
        get_ScatFact(atoms, energies, 'scatfact')
    #-------------------------------------
    if option==4:
        import numpy
        energies=[]
        atoms=['Fe','N', 'O', 'Ga', 'As', 'Au']
        for i in numpy.arange(7000., 8100., 1):
            energies.append(i)
        get_ScatFact(atoms, energies, 'scatfact')
    #-------------------------------------
    if option==5:
        eV0=8800.0
        out=AtNum2f1f2Xsect(25, eV0)
        print out[2]
        out=AtNum2f1f2Xsect(26, eV0)
        print out[2]
