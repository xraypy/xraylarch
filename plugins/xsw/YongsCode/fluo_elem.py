import math
import numpy
#import f1f2_data # an array of scattering factors from Chantler table
import readf1f2a
import elam # FY from Elam data

#global variables
re=2.82e-13  #cm
Barn=1e-24   #cm^2
Nav=6.022e23  #atoms/mol
pre_edge_margin=150.  # FY calculated from 150 eV below the absorption edge.
fluo_emit_min=500.      # minimum energy for emitted fluorescence.  ignore fluorescence emissions below 500eV

"""
Y. Choi
fluo_elam.py: elemental dependent part in fluorescence yield.
4/14/2011
Original fluo.py was modified to fluo_new.py.
readf1f2a.py is used instead of original readf1f2.py
fluo_new.py is being split into two.
fluo_elem.py is for elemtnal dependence: fluorescenc yield, crosssection.
fluo_det.py is for detection dependnece: detector efficiency, attenuation, sample
"""



def AtSym2AtNum(AtSym):  # returns atomic number using atomic symbol
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


def AtSym2AtWt(AtSym):  # returns atomic weight (g/mol) using atomic symbol
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


def cal_FluoYield(atom_sym, eV0, emission='', edge='', useAvg=1, xsect_res=0.0):
    # returns net fluorescence yield and xsection
    # emission is not empty calculate for one (Fe Ka). if empty check all emission lines.
    # if edge is not empyt, calculate all emission lines for the edge
    # useAvg=1: weighted average of all the emission lines.  Ka instead of Ka1, Ka2...
    edges      =['K',  'K',  'L1', 'L1', 'L2', 'L2', 'L2', 'L3', 'L3', 'L3']
    Fluo_lines =['Ka', 'Kb', 'Lb', 'Lg', 'Ln', 'Lb', 'Lg', 'Ll', 'La', 'Lb']
    OneEmitLineOnly=0;  OneEdgeOnly=1;     netFY=0.;             output=[]
    atnum=AtSym2AtNum(atom_sym)
    if emission!='':
        OneEmitLineOnly=1  # calculate only one emission line
    if edge!='':
        OneEdgeOnly=1  # calculate one edge with multiple emission lines
    if xsect_res == 0:  # use tabulated Xsection
        temp=readf1f2a.AtNum2f1f2Xsect(atnum, eV0)  # [f1, f2, photoXSect, mu_photo, mu_total]
        xsect_photo=temp[2]     # in barns/atom
    else:   # resonant xsection used
        xsect_photo = xsect_res
    if OneEmitLineOnly==1:  # regardless of OneEdgeOnly value, Ka from Ka1, Ka2...
        edge=emission[0]
        edge.upper()    # 1st letter indicates edge.  ex) 'K' in 'Ka'
        if useAvg:      # weight averaged
            tempFY = get_avgElamFY(atom_sym, edge, emission, eV0)
            # returns [float(FY), weighted_eV, net_prob]
            netYield = tempFY[0]*tempFY[2]  # fluorescence yield * net probability
            avgFYeV = tempFY[1]     # weighted average for emission energy
            netFY = netYield * xsect_photo  # netYield * Xsection
            emit_name=tempFY[3]
            # return a list
            return [netFY, avgFYeV, netYield, xsect_photo, emit_name]
        else:  # report individual lines, Ka1, Ka2, K3...
            tempFY = get_avgElamFY(atom_sym, edge, emission, eV0, useAvg=0)
            # returns list of [float(FY), weighted_eV, net_prob]
            for eachone in tempFY:
                netYield = eachone[0]*eachone[2]  # fluorescence yield * net probability
                FYeV = eachone[1]     # emission energy
                netFY = netYield * xsect_photo  # netYield * Xsection
                emit_name=eachone[3]
                this=[netFY, FYeV, netYield, xsect_photo, emit_name]
                output.append(this)
            # return a list of lists
            return output  # list of [netFY, FYeV, netYield, xsect_photo]
    if OneEmitLineOnly==0 and OneEdgeOnly==1:  # report Ka, Kb...
        for (ii, OneEdge) in enumerate(edges):
            if edge==OneEdge:
                emission=Fluo_lines[ii]
                tempFY=get_avgElamFY(atom_sym, edge, emission, eV0, useAvg=1)
                #[float(FY), weighted_eV, net_prob, emission]
                netYield = tempFY[0]*tempFY[2]  # fluorescence yield * net probability
                avgFYeV = tempFY[1]     # weighted average for emission energy
                netFY = netYield * xsect_photo  # netYield * Xsection
                emit_name=tempFY[3]
                this=[netFY, avgFYeV, netYield, xsect_photo, emit_name]
                output.append(this)
        # return a list of lists
        return output
        

def get_avgElamFY(AtSym, edge, emission, eV0, useAvg=1):
    #ex) Fe, K, Ka, 8000, returns FY weighted-averaged emission energy
    # if useAvg!=1, then report individual lines instead of weight average
    margin=pre_edge_margin       # FY is zero if eV0 is margin below the edge, pre_edge_marge global
    OneEmit=[]; MultEmit=[]
    test=edge[0]    # capitalized 1st letter
    test.upper()
    edge=test+edge[1:]
    net=elam.use_ElamFY(AtSym, edge)
    #AtSym, edge, edge-energy, FY, [ [transition, emission, energy, probability],[]...]
    atom=net[0]
    edge_energy=net[2]
    if edge==net[1] and eV0>float(edge_energy): pass #print 'above the selected edge'
    FY=net[3]
    agg=net[4]  # list for emission lines.
    num=len(agg)  # number of emission lines
    temp=0.0;       net_prob=0.0
    if useAvg:		# ex) La weighted average for La1, La2 and Lb for Lb2, Lb6
        for (ix, tran) in enumerate(agg):
            emit_name=tran[1]  # emission, Ka1, Ka2 ...
            emit_eV=tran[2]  #  energy
            emit_prob=tran[3]   # probability
            if emit_name.startswith(emission):
                temp+=float(emit_eV)*float(emit_prob)
                net_prob+=float(emit_prob)
            if net_prob==0:    # prevent division by zero
            #print AtSym, edge, emission, eV0, emit_name, emit_eV, emit_prob
                weighted_eV=0.0
            else:  # net_prob is not zero
                weighted_eV=temp/net_prob
            if (eV0+margin)<float(edge_energy):  # always returns weighted eV 
                return [0.0, weighted_eV, 0.0]		# 3/20/2010
        return [float(FY), weighted_eV, net_prob, emission]
    if useAvg!=1:  # report each lines separately
        # July 2012: this part causes problem since the returned values are different 
        for (ix, tran) in enumerate(agg):
            emit_name=tran[1]  # emission, Ka1, Ka2 ...
            emit_eV=tran[2]  #  energy
            emit_prob=tran[3]   # probability
            if emit_name.startswith(emission):
                OneEmit=[float(FY), float(emit_eV), float(emit_prob), emit_name]
                MultEmit.append(OneEmit)
        return MultEmit


def get_all_avgElamFY(AtSym, eV0):
    # check all averaged emission lines for this element at this energy
    #ex) Fe, 8000, returns Ka, Kb, La ...  igonores M edges and beyond
    # useAvg=1: use weighted average.
    edges      =['K',  'K',  'L1', 'L1', 'L2', 'L2', 'L2', 'L3', 'L3', 'L3']
    Fluo_lines =['Ka', 'Kb', 'Lb', 'Lg', 'Ln', 'Lb', 'Lg', 'Ll', 'La', 'Lb']
    output=[]
    for (nn, edge) in enumerate(edges):
        emit=Fluo_lines[nn]
        temp=get_avgElamFY(AtSym, edge, emit, eV0)
        fy=temp[0]  # Fluo Yield
        emit_eV=temp[1]     # weight averaged emission energy
        emit_prob=temp[2]   # transition probability
        oneline=[]
        if fy!=0.0 and emit_prob!=0.0:
            oneline.append(edge)
            oneline.append(emit)
            oneline.append(fy)
            oneline.append(emit_eV)
            oneline.append(emit_prob)
            output.append(oneline)
    return output # list of [edge, emission, fy, emit_eV, prob].
            

def get_all_indElamFY(AtSym, eV0):
    #ex) Fe, 8000, returns all individual emission lines.
    edges = ['K', 'L1', 'L2', 'L3', 'M3', 'M4']
    eVmargin=pre_edge_margin       # global variable for pre-edge margin
    eVMin=fluo_emit_min  # global variable for minimum fluorescence emission energy
    output=[];  OneEmission=[]
    for edge in edges:
        temp=elam.use_ElamFY(AtSym, edge)
        #AtSym, edge, edge-energy, FY, [ [transition, emission, energy, probability],[]...]
        if temp[2]!=0 and temp[3]!=0:  # returns 0, 0 if no match
            edge_eV=float(temp[2])
            if eV0>(edge_eV-eVmargin):
                fy=float(temp[3])
                EmitLines=temp[4]
                for oneline in EmitLines:
                    emit_name=oneline[1]
                    emit_eV=float(oneline[2])
                    emit_prob=float(oneline[3])
                    if emit_eV>eVMin:
                        OneEmission.append(edge)
                        OneEmission.append(emit_name)
                        OneEmission.append(fy)
                        OneEmission.append(emit_eV)
                        OneEmission.append(emit_prob)
                        output.append(OneEmission); OneEmission=[]
    return output
        

#------------  Remove below and make a module for sample, attenuator, detector conditions.


if __name__=='__main__':
    atom0='Fe'
    emission0='Ka'
    eV0=8000.
    edge0='K'
    print 'net_FluoYield/atom, emission energy, FY, Xsection, emission_name'
    print    cal_FluoYield(atom0, eV0, edge=edge0)# , xsect_res=0.0):
    print '-'*10
    print    cal_FluoYield(atom0, eV0, edge=edge0 , xsect_res=30000.)
    print '-'*20
    print    cal_FluoYield(atom0, eV0, emission=emission0 )# , xsect_res=0.0):
    print '-'*30
    print    cal_FluoYield(atom0, eV0, emission=emission0, useAvg=0 )# , xsect_res=0.0):
    print '-'*40
    print get_all_indElamFY(atom0, eV0)
    print '-'*50
    print ' Fe Ka fluorescence: FY, emission energy, emission probability, emission name'
    print get_avgElamFY('Fe', 'K', 'Ka', 7200., useAvg=0)    
    print ' Fe Ka fluorescence: FY, emission energy, emission probability, emission name, averaged'
    print get_avgElamFY('Fe', 'K', 'Ka', 7200., useAvg=1)    
