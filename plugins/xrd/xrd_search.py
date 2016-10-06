#!/usr/bin/env python
"""
Tools for searching XRD pattern matches from database or provided CIF files
mkak 2016.09.23
"""
import time
import os

HAS_XRAYUTIL = False
try:
    import xrayutilities as xu
    HAS_XRAYUTIL = True
except ImportError:
    pass

import numpy as np
import glob
import os
import math
import wx

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


def show_F_depend_on_E(cry_strc,hkl,emin=500,emax=20000,esteps=5000):
    '''
    Dependence of F on E for single hkl for one cif
    mkak 2016.09.22
    '''
    E = np.linspace(emin,emax,esteps)
    F = cry_strc.StructureFactorForEnergy(cry_strc.Q(hkl), E)

    return E,F

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

    def onChemistry(self,event):
        print('Will eventually show Periodic Table...')

    def onSymmetry(self,event):
        XRDSymmetrySearch()

    def onReset(self,event):
        self.Mineral.Clear()
        self.Author.Clear()
        self.Chemistry.Clear()
        self.Symmetry.Clear()
        self.Search.Clear()
            
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
