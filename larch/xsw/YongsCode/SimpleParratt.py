import math
import cmath
import numpy
#import fluo  # used in Layer.get_index, change to readf1f2, stop using fluo
import readf1f2a

# 9/20/2010: Y.Choi.
# Reflectivity calculation using Parratt's recursive formula
# Calculate reflected intensity as a function of angle or energy
# Needs accesss to index of refraction data
# layer0 is vaccum, layer1 is top film layer ...

class Layer:
    def __init__(self, tag, composition='Si', density=2.33, thickness=1000.1234, rms=1e-3):
        self.tag=tag                        # layer name, ex), 'top layer','film1'...
        self.composition=composition        # chemical formula ex) SiO2
        self.density=density                # nominal density in g/cm^3
        self.relden=1.0                     # relative density 1.0=100% of nominal density
        self.thickness=thickness            # in Angstroms  1e8 A = 1cm
        if rms==0:  rms=1e-9                # cannot handle 0 roughness.
        self.rms=rms                        # rms interface roughness in Agnstroms
        self.la=1.0                         # absoprtion length in cm, for inicident x-ray
        self.laFY=1.0                       # absorption length in Angstrom, for emitted fluorescence
        self.trans=0.5                      # transmission coefficient
        self.absrp=0.5                      # absorption coefficient
        self.delta=0.1                      # index of refraction, real part
        self.beta=0.1                       # index of refraction, imaginary part
        self.kz=1.0+1.0J                    # wavenumber, complex [wavenumZ]
        self.rr=0+0J                        # Fresnel coefficient, [FresnelR]
        self.rf=0+0J                        # Fresnel coefficient with roughness, refl:[FresnelR]+[RoughGauss]
        self.rrr=0+0J                       # reflectivity, [Reflect]
        self.tt=0+0J                        # Fresnel coeffcient, [FresnelT]
        self.tf=0+0J                        # Fresnel coefficient with roughness, for transmission
        self.ttt=0+0J                       # transmission, [Transmit]
        self.E_t=0+0J                       # electric field, transmission
        self.E_r=0+0J                       # electric field, relfection
        self.interface=0                    # interface depth, air/film is 0 for air layer
        self.index=-1                       # air=0, film1=1, ...substrate=n
        self.Nat=1                          # atomic number density for element of interest     
    def set_DenThickRms(self, RelativeDensity, thickness, roughness):
        self.relden=RelativeDensity
        self.thickness=thickness
        self.rms=roughness
    def get_index(self, energy=8370.0, indexNat=0):   # x-ray energy in eV, relative density
        temp=readf1f2a.get_delta(self.composition, self.density*self.relden, energy, indexNat)  # used to be fluo
        self.delta=temp[0]
        self.beta=temp[1]
        self.la=temp[2]                     # in cm,
        self.Nat=temp[3]
        self.trans=math.exp(-self.thickness*1e8/self.la)
        #la attenuation length cm, NumLayer for multiple layers
        self.absrp=1.0-self.trans
    def cal_kz(self, k0, th_rad):   # calculate wavenumber in each layer
        temp = cmath.sqrt((math.sin(th_rad))**2 - 2.0*self.delta - 2.0*self.beta*1.0j)
        self.kz = k0*(temp.real + abs(temp.imag)*1.0J)
        #kz = k0 * sqrt((sin(th_rad))^2 - 2*delta - 2*beta*i)
    def cal_rr(self, kz0, kz1):
        # Fresnel coefficient, [FresnelR] input: kz_(j), kz_(j+1)
        temp = (kz0-kz1)/(kz0+kz1)  
        self.rr = temp
    def cal_rf(self, rr, kz0, kz1):
        # add roughness effect to Fresnel coefficient, [RoughGauss], input:kz_(j), kz_(j+1), rr, rms
        temp = rr*cmath.exp(-2.0*kz0*kz1*self.rms)  
        self.rf = temp
    def cal_rrr(self, rf0, rrr1, kz1, d1):  # reflectivity, [Reflect]
        v = 2.0*kz1*d1
        u = -v.imag + v.real*1.0J
        z1 = rrr1*cmath.exp(u) + rf0
        z2 = 1.0 + rf0*rrr1*cmath.exp(u)
        z=z1/z2
        self.rrr=z
    def cal_tt(self, kz0, kz1):
        #Fresnel coefficient [FresnelT], upto here 0: ThisLayer_(i), 1: BelowLayer_(i+1)
        temp = 2*kz0/(kz0+kz1)
        self.tt=temp
    def cal_ttt(self, tf2, rf2, rrr0, d0, ttt2, kz0):
        #Fresnel coefficient [FresnelT], 0:ThisLayer_(i), 2: AboveLayer_(i-1)
        v1 = -2.0*d0*kz0.imag + (2.0*d0*kz0.real)*1.0J
        v2 = cmath.exp(v1)
        v3 = -d0*kz0.imag + (d0*kz0.real)*1.0J
        v4 = cmath.exp(v3)
        v5 = tf2*(ttt2*v4)
        v6 = rf2*(rrr0*v2)
        v7 = v6.real+1.0 + (v6.imag)*1.0J
        z=v5/v7
        self.ttt=z


def reflectivity(eV0=14000.0, th_deg=[], mat=[], thick=[], den=[], rough=[], tag=[],  depths=[], xsw_mode=0):
#   --------------------set default values------------------------
    if th_deg==[]:  # set default th list
        th_min=0.0         # minimum th
        th_max=1.0          # maximum th
        th_step=0.002      # stepsize th
        th_deg=numpy.arange(th_min, th_max+th_step, th_step) 	
    th=[]               #   theta(incident angle) in radian
    qz=[]               #   momentum transfer (1/Angstrom)
    if mat==[] or thick==[] or den==[] or rough==[]:
    #set defalut layer material, air, film1, film2, substrate
        tag=['air', 'film', 'underlayer', 'substrate'] 
        mat=['N1.56O0.48C0.03Ar0.01Kr0.000001Xe0.0000009', 'Pt', 'Cr', 'Si'] 
        thick=[0., 200., 50., 10000]  # air, film1, film2, substrate
        den=[1.e-10, 21.45, 7.19, 2.33]
        rough=[1.0, 1.0, 1.0, 1.0]
    if depths==[]:  # set default depth list
        depths=[0.0]    # in Angstroms
    depth_num=len(depths)
    layers=[]  
    for (ii, d) in enumerate(thick):
        layer0=Layer(tag[ii], mat[ii], den[ii])
        layer0.set_DenThickRms(1.0, thick[ii], rough[ii])
        layers.append(layer0)
    NumLayers=len(layers)       # this value is (# of film layer + 2[air, substrate])
    FilmThick=0.0  # film thickness
    for (ix, item) in enumerate(layers):
        item.get_index(eV0)         # get index of refraction, delta, beta for eV0
        FilmThick+=item.thickness   # get total film thickness
        item.interface=FilmThick    # interface location: depth from surface
        item.index=ix               # layer index
    WaveLength=12.39842/(eV0/1000.0)  # in Angstroms, 1e-8cm = 1 Angstrom
    k0=2.*math.pi/WaveLength
    for (ix, angle) in enumerate(th_deg):   # convert th_deg to th(rad) and qz(1/A)
        temp=angle/180.0*math.pi
        th.append(temp)                     # th in radian
        temp1=4.*math.pi/WaveLength*math.sin(temp)   #qz=4pi/lambda*sin(th)*2k0sin(th)
        qz.append(temp1)
    NumTh=len(th)
    out_parratt='SimpleParratt.txt'     # output file name
    fp=open(out_parratt, 'w')
    ListOut=[]
    for angle in th:
        # define wavenumber within each layer
        for layer in layers:     
            layer.cal_kz(k0, angle)
        # calculate reflection and transmission coefficients
        for ix in range(NumLayers-1):     
            layer=layers[ix]
            kz0=layers[ix].kz
            kz1=layers[ix+1].kz
            layer.cal_rr(kz0, kz1)                      # Fresnel coefficient, rr
            layer.cal_rf( layer.rr, kz0, kz1)           # Fresnel coefficient with roughness, rf
            layer.cal_tt(kz0, kz1)                      # Fresnel coefficient, tt, in e-field intensity
            layer.tf=layer.rf+1.0                       # T=1+R
        # calculate reflectivity
        layers[NumLayers-1].rrr=0.0                     # nothing reflects back from below the substrate
        layers[NumLayers-2].rrr=layers[NumLayers-2].rf  # interface between the substrate and layer above it
        ixs=numpy.arange(NumLayers-3, -1, -1)           # start from second interface from the substrate to 0
        for ix in ixs:          # calculate RRR
            BelowLayer=layers[ix+1]
            ThisLayer=layers[ix]
            ThisLayer.cal_rrr(ThisLayer.rf, BelowLayer.rrr, BelowLayer.kz, BelowLayer.thickness)
        intenR = (layers[0].rrr.real)**2 + (layers[0].rrr.imag)**2
        # intenR is reflected intensity
        # calculate transmission
        layers[0].ttt=1.0 + 0J
        ixs=numpy.arange(1, NumLayers-1, 1)     # from 1 to <(NumLayers-1)
        for ix in ixs:          # Calculate TTT
            ThisLayer=layers[ix]
            AboveLayer=layers[ix-1]
            ThisLayer.cal_ttt(AboveLayer.tf, AboveLayer.rf, ThisLayer.rrr, \
                              ThisLayer.thickness, AboveLayer.ttt, ThisLayer.kz)
        ixs=numpy.arange(0, NumLayers-1, 1)     # from 1 to <(NumLayers-1)
        for ix in ixs:
            ThisLayer=layers[ix]
            ThisLayer.E_t=ThisLayer.ttt
            ThisLayer.E_r=ThisLayer.ttt*ThisLayer.rrr
        layers[NumLayers-1].E_t = layers[NumLayers-2].tf*layers[NumLayers-2].ttt
##        Next, the current depth within the film structure is searched.
##        depth=0 is air/film, depth>0 film, depth<0 above film
##        xx=0 is film/substrate, xx<0 inside substrate, xx>0 above substrate
##        for reflectivity only, fix depth=0 and skip full xsw calculation
        layer_index=0   # air/layer1
        netFY=0.0; EFIat0=0.0; FY=0.0
        TransFY=1.0;    TransFYList=[]
        EFI_atTH=[]     # EFI as a function of depth at current th
        EFI = 0
        #print(depth_num)
        for depth in depths:
            # calculate e-field intensity at each depth
            xx=FilmThick-depth
            ThisLayer = layers[layer_index]
            if layer_index==(NumLayers-1):   #inside substrate
                cph = -xx*ThisLayer.kz
                cph_t = cmath.exp(cph*(0.0+1.0J))
                Etot = ThisLayer.E_t*cph_t
            elif layer_index==(NumLayers-2):    # layer above the substrate
                d_n=0
                cph = ThisLayer.kz*(xx-d_n)
                cph_t = cmath.exp(cph*(0.0-1.0J))
                cph_r = cmath.exp(cph*(0.0+1.0J))
                Etot = ThisLayer.E_t*cph_t + ThisLayer.E_r*cph_r
            else:
                d_n=FilmThick-ThisLayer.interface
                cph = ThisLayer.kz*(xx-d_n)
                cph_t = cmath.exp(cph*(0.0-1.0J))
                cph_r = cmath.exp(cph*(0.0+1.0J))
                Etot = ThisLayer.E_t*cph_t + ThisLayer.E_r*cph_r
            EFI = (Etot.real)**2 + (Etot.imag)**2
        if xsw_mode:
            pass
        temp=angle*180.0/math.pi
        out=str(temp)+'  '+str(intenR)+'  '+str(EFI)+'\n'
        ListOut.append([temp, intenR, EFI])
        fp.write(out)      
    fp.close()
    #for layer in layers:
    #    print(layer.tag, layer.composition, layer.thickness, layer.rms, layer.density)
    return ListOut  #list of [[th1, refl1], [th2, refl2] ...]
    



if __name__=='__main__':
    #test
    reload(readf1f2a)
    import time
    a=time.clock()
    reflectivity()  
    print(time.clock()-a, 'seconds')



