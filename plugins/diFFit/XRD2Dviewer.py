#!/usr/bin/env pythonw
'''
GUI for displaying 2D XRD images

'''

VERSION = '0 (18-October-2016)'

# Use the wxPython backend of matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as colormap
import matplotlib       
matplotlib.use('WXAgg')

import os
import wx

# import h5py
import numpy as np
from scipy import constants

HAS_pyFAI = False
try:
    import pyFAI
    import pyFAI.calibrant
    from pyFAI.calibration import Calibration
    HAS_pyFAI = True
except ImportError:
    pass
    
from wxmplot.imagepanel import ImagePanel
from wxutils import MenuItem

from larch_plugins.diFFit.XRDCalculations import fabioOPEN
from larch_plugins.diFFit.ImageControlsFrame import ImageToolboxFrame
from larch_plugins.diFFit.XRDCalibrationFrame import CalibrationPopup,CalibrationChoice

SLIDER_SCALE = 1000. ## sliders step in unit 1. this scales to 0.001
IMAGE_AND_PATH = '/Users/koker/Data/XRMMappingCode/Search_and_Match/exampleDIFF.tif'
#IMAGE_AND_PATH = '/Users/margaretkoker/Data/XRMMappingCode/Search_and_Match/exampleDIFF.tif'

class Viewer2DXRD(wx.Frame):
    '''
    Frame for housing all 2D XRD viewer widgets
    '''
    def __init__(self, *args, **kw):
        label = 'diFFit.py : 2D XRD Viewer'
        wx.Frame.__init__(self, None, -1,title=label, size=(800, 600))
        
        self.SetMinSize((700,500))
        
        self.statusbar = self.CreateStatusBar(3,wx.CAPTION )

        ## Default image information
        self.raw_img  = np.zeros((1024,1024))
        self.plt_img = np.zeros((1024,1024))
        self.mask = np.ones((1024,1024))
        self.bkgd = np.zeros((1024,1024))
        self.bkgd_scale = 1
        self.bkgdMAX = 5
        
        self.countPIXELS()
        
        self.use_mask = False
        self.use_bkgd = False
        if self.msk_pxls > 0:
            self.use_mask = True
        if self.bkgd_pxls > 0:
            self.use_bkgd = True
        
        self.color = 'bone'
        self.flip = 'none'
        
        self.ai = None
        
        self.XRD2DMenuBar()
        self.Panel2DViewer()
        
        self.Centre()
        self.Show(True)

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)


##############################################
#### PANEL DEFINITIONS
    def XRD2DMenuBar(self):

        menubar = wx.MenuBar()
        
        ###########################
        ## diFFit2D
        diFFitMenu = wx.Menu()
        
        MenuItem(self, diFFitMenu, '&Open diffration image', '', self.loadIMAGE)
        MenuItem(self, diFFitMenu, 'Sa&ve image to file', '', None)
        MenuItem(self, diFFitMenu, '&Save settings', '', None)
        MenuItem(self, diFFitMenu, '&Load settings', '', None)
        MenuItem(self, diFFitMenu, '&Add analysis to map file', '', None)
       
        menubar.Append(diFFitMenu, '&diFFit2D')

        ###########################
        ## Process
        ProcessMenu = wx.Menu()
        
        MenuItem(self, ProcessMenu, '&Load mask file', '', self.openMask)
        MenuItem(self, ProcessMenu, '&Remove current mask', '', None)
        MenuItem(self, ProcessMenu, '&Create mask', '', self.createMask)
        MenuItem(self, ProcessMenu, 'Load &background image', '', self.openBkgd)
        MenuItem(self, ProcessMenu, '&Remove current background image', '', None)
        
        menubar.Append(ProcessMenu, '&Process')

        ###########################
        ## Analyze
        AnalyzeMenu = wx.Menu()
        
        MenuItem(self, AnalyzeMenu, '&Calibrate', '', self.Calibrate)
        MenuItem(self, AnalyzeMenu, '&Load calibration file', '', self.openPONI)
        MenuItem(self, AnalyzeMenu, '&Show current calibration', '', self.showPONI)
        AnalyzeMenu.AppendSeparator()
        MenuItem(self, AnalyzeMenu, '&Integrate (open 1D viewer)', '', None)

        menubar.Append(AnalyzeMenu, '&Analyze')

        ###########################
        ## Create Menu Bar
        self.SetMenuBar(menubar)

    def Panel2DViewer(self):
        '''
        Frame for housing all 2D XRD viewer widgets
        '''
        self.panel = wx.Panel(self)

        vistools = self.VisualToolbox(self.panel)
        rightside = self.RightSidePanel(self.panel)        

        panel2D = wx.BoxSizer(wx.HORIZONTAL)
        panel2D.Add(vistools,flag=wx.ALL,border=10)
        panel2D.Add(rightside,proportion=1,flag=wx.EXPAND|wx.ALL,border=10)

        self.panel.SetSizer(panel2D)
    
    def VisualToolbox(self,panel):
        '''
        Frame for visual toolbox
        '''
        
        tlbx = wx.StaticBox(self.panel,label='VISUAL TOOLBOX')#, size=(200, 200))
        vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)

        ###########################
        ## Color
        hbox_clr = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_clr = wx.StaticText(self.panel, label='COLOR')
        colors = []
        for key in plt.cm.datad:
            if not key.endswith('_r'):
                colors.append(key)
        self.ch_clr = wx.Choice(self.panel,choices=colors)

        self.ch_clr.Bind(wx.EVT_CHOICE,self.onColor)
    
        hbox_clr.Add(self.txt_clr, flag=wx.RIGHT, border=8)
        hbox_clr.Add(self.ch_clr, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_clr, flag=wx.ALL, border=10)
    
        ###########################
        ## Contrast
        vbox_ct = wx.BoxSizer(wx.VERTICAL)
    
        hbox_ct1 = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_ct1 = wx.StaticText(self.panel, label='CONTRAST')
        self.txt_ct2 = wx.StaticText(self.panel, label='')
        
        hbox_ct1.Add(self.txt_ct1, flag=wx.EXPAND|wx.RIGHT, border=8)
        hbox_ct1.Add(self.txt_ct2, flag=wx.ALIGN_RIGHT, border=8)
        vbox_ct.Add(hbox_ct1, flag=wx.BOTTOM, border=8)
    
        hbox_ct2 = wx.BoxSizer(wx.HORIZONTAL)
        self.ttl_min = wx.StaticText(self.panel, label='min')
        self.sldr_min = wx.Slider(self.panel)
        self.entr_min = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)

        self.sldr_min.Bind(wx.EVT_SLIDER,self.onSlider)
            
        hbox_ct2.Add(self.ttl_min, flag=wx.RIGHT, border=8)
        hbox_ct2.Add(self.sldr_min, flag=wx.EXPAND, border=8)
        hbox_ct2.Add(self.entr_min, flag=wx.RIGHT, border=8)
        vbox_ct.Add(hbox_ct2, flag=wx.BOTTOM, border=8)        
    
        hbox_ct3 = wx.BoxSizer(wx.HORIZONTAL)
        self.ttl_max = wx.StaticText(self.panel, label='max')
        self.sldr_max = wx.Slider(self.panel)
        self.entr_max = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)

        self.sldr_max.Bind(wx.EVT_SLIDER,self.onSlider) 
        
        hbox_ct3.Add(self.ttl_max, flag=wx.RIGHT, border=8)
        hbox_ct3.Add(self.sldr_max, flag=wx.EXPAND, border=8)
        hbox_ct3.Add(self.entr_max, flag=wx.RIGHT, border=8)
        vbox_ct.Add(hbox_ct3, flag=wx.BOTTOM, border=8)

        hbox_ct4 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_ct1 = wx.Button(self.panel,label='reset range')
        self.btn_ct2 = wx.Button(self.panel,label='set range')

        self.btn_ct1.Bind(wx.EVT_BUTTON,self.autoContrast)
        self.btn_ct2.Bind(wx.EVT_BUTTON,self.onContrastRange)

        hbox_ct4.Add(self.btn_ct1, flag=wx.RIGHT, border=8)
        hbox_ct4.Add(self.btn_ct2, flag=wx.RIGHT, border=8)
        vbox_ct.Add(hbox_ct4, flag=wx.ALIGN_RIGHT|wx.BOTTOM,border=8)
        vbox.Add(vbox_ct, flag=wx.ALL, border=10)

        ###########################
        ## Flip
        hbox_flp = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_flp = wx.StaticText(self.panel, label='IMAGE FLIP')
        flips = ['none','vertical','horizontal','both']
        self.ch_flp = wx.Choice(self.panel,choices=flips)

        self.ch_flp.Bind(wx.EVT_CHOICE,self.onFlip)
    
        hbox_flp.Add(self.txt_flp, flag=wx.RIGHT, border=8)
        hbox_flp.Add(self.ch_flp, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_flp, flag=wx.ALL, border=10)
    
        ###########################
        ## Scale
        hbox_scl = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_scl = wx.StaticText(self.panel, label='SCALE')
        scales = ['linear','log']
        self.ch_scl = wx.Choice(self.panel,choices=scales)
    
        self.ch_scl.Bind(wx.EVT_CHOICE,self.onScale)
    
        hbox_scl.Add(self.txt_scl, flag=wx.RIGHT, border=8)
        hbox_scl.Add(self.ch_scl, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_scl, flag=wx.ALL, border=10)


        ###########################
        ## Mask
        hbox_msk = wx.BoxSizer(wx.HORIZONTAL)
 #       self.txt_msk = wx.StaticText(self.panel, label='MASK')
        self.btn_mask = wx.Button(panel,label='MASK')
        self.ch_msk = wx.CheckBox(self.panel,label='Apply?')
        
        self.ch_msk.Bind(wx.EVT_CHECKBOX,self.applyMask)
        self.btn_mask.Bind(wx.EVT_BUTTON,self.openMask)
    
#        hbox_msk.Add(self.txt_msk, flag=wx.RIGHT, border=8)
        hbox_msk.Add(self.btn_mask, flag=wx.RIGHT, border=8)
        hbox_msk.Add(self.ch_msk, flag=wx.RIGHT, border=8)
        vbox.Add(hbox_msk, flag=wx.ALL, border=10)
    
        ###########################
        ## Background
        hbox_bkgd = wx.BoxSizer(wx.HORIZONTAL)
#        self.txt_bkgd = wx.StaticText(self.panel, label='BACKGROUND')
        self.btn_bkgd = wx.Button(panel,label='BACKGROUND')
        self.sldr_bkgd = wx.Slider(self.panel)
        self.entr_scale = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)

        self.sldr_bkgd.Bind(wx.EVT_SLIDER,self.onBkgdScale)
        self.btn_bkgd.Bind(wx.EVT_BUTTON,self.openBkgd)

#        hbox_bkgd.Add(self.txt_bkgd, flag=wx.RIGHT, border=8)
        hbox_bkgd.Add(self.btn_bkgd, flag=wx.RIGHT, border=8)
        hbox_bkgd.Add(self.sldr_bkgd, flag=wx.RIGHT, border=8)
        hbox_bkgd.Add(self.entr_scale, flag=wx.RIGHT, border=8)
        vbox.Add(hbox_bkgd, flag=wx.ALL, border=10)

        self.btn_scale = wx.Button(self.panel,label='set range')
        self.btn_scale.Bind(wx.EVT_BUTTON,self.onChangeBkgdScale)
        vbox.Add(self.btn_scale, flag=wx.ALIGN_RIGHT|wx.BOTTOM, border=10)

        self.sldr_bkgd.SetValue(self.bkgd_scale*SLIDER_SCALE)
        if self.bkgd_pxls == 0:
            self.sldr_bkgd.Disable()
            self.entr_scale.Disable()
            self.btn_scale.Disable()

        ###########################
        ## Set defaults  
        self.ch_clr.SetStringSelection(self.color)
        self.ch_flp.SetStringSelection(self.flip)
        if self.msk_pxls == 0:
            self.ch_msk.Disable()
        
        return vbox    

    def RightSidePanel(self,panel):
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.plot2DXRD(panel)
        btnbox = self.QuickButtons(panel)
        vbox.Add(self.plot2D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        vbox.Add(btnbox,flag=wx.ALL|wx.ALIGN_RIGHT,border = 10)
        return vbox

    def QuickButtons(self,panel):
        buttonbox = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_img = wx.Button(panel,label='LOAD IMAGE')
        self.btn_calib = wx.Button(panel,label='CALIBRATION')
        self.btn_integ = wx.Button(panel,label='INTEGRATE (1D)')
        
        self.btn_img.Bind(wx.EVT_BUTTON,self.loadIMAGE)
        self.btn_calib.Bind(wx.EVT_BUTTON,self.openPONI)
        self.btn_integ.Bind(wx.EVT_BUTTON,self.on1DXRD)
        
        buttonbox.Add(self.btn_img, flag=wx.ALL, border=8)
        buttonbox.Add(self.btn_calib, flag=wx.ALL, border=8)
        buttonbox.Add(self.btn_integ, flag=wx.ALL, border=8)
        
        return buttonbox

##############################################
#### IMAGE DISPLAY FUNCTIONS
    def countPIXELS(self):
        ## Calculates the number of pixels in image, masked pixels, and background pixels
        self.img_pxls = int(self.raw_img.shape[0]*self.raw_img.shape[1])
        self.msk_pxls   = self.img_pxls - int(sum(sum(self.mask)))
        self.bkgd_pxls = int(sum(sum(self.bkgd)))

    def checkIMAGE(self):
        ## Reshapes/replaces mask and/or background if shape doesn't match that of image    
        if self.mask.shape != self.raw_img.shape:
            self.mask = np.ones(self.raw_img.shape)
        if self.bkgd.shape != self.raw_img.shape:
            self.bkgd = np.zeros(self.raw_img.shape)

        self.countPIXELS()

        ## Enables mask checkbox.
        if self.msk_pxls == 0:
            self.ch_msk.Disable()
        else:
            self.ch_msk.Enable()
        
        ## Enables background slider and sets range.
        if self.bkgd_pxls == 0:
            self.entr_scale.SetLabel('')
            
            self.sldr_bkgd.Disable()
            self.entr_scale.Disable()
            self.btn_scale.Disable()
            
            self.use_bkgd = False
        else:
            self.btn_scale.Enable()
            self.entr_scale.Enable()
            self.sldr_bkgd.Enable()

            self.sldr_bkgd.SetRange(0,self.bkgdMAX*SLIDER_SCALE)
            self.sldr_bkgd.SetValue(self.bkgd_scale*SLIDER_SCALE)
            self.entr_scale.SetLabel(str(self.bkgdMAX))

            self.use_bkgd = True

    def calcIMAGE(self):

        if self.use_mask is True:
            if self.use_bkgd is True:
                self.plt_img = self.raw_img * self.mask - self.bkgd * self.bkgd_scale
            else:
                self.plt_img = self.raw_img * self.mask
        else:
            if self.use_bkgd is True:
                self.plt_img = self.raw_img - self.bkgd * self.bkgd_scale
            else:
                self.plt_img = self.raw_img

        ## Update image control panel if there.
        try:
            self.txt_ct2.SetLabel('[ full range: %i, %i ]' % 
                         (np.min(self.plt_img),np.max(self.plt_img))) 
        except:
            pass

    def plot2DXRD(self,panel):
    
        self.plot2D = ImagePanel(panel,size=(500, 500))
        self.plot2D.messenger = self.write_message

        ## eventually, don't need this
        #self.openIMAGE()           

        self.plot2D.display(self.plt_img)

        self.setColor()
        self.autoContrast(None)
        self.checkFLIPS()

        self.plot2D.redraw()

    def onBkgdScale(self,event):
        
        self.bkgd_scale = self.sldr_bkgd.GetValue()/SLIDER_SCALE
        self.entr_scale.SetValue(str(self.bkgd_scale))
        
        self.calcIMAGE()
        #self.plot2D.display(self.plt_img)
        self.setColor()
        self.checkFLIPS()
        self.plot2D.redraw()      

    def onChangeBkgdScale(self,event):

        self.bkgdMAX = float(self.entr_scale.GetValue())
        self.bkgd_scale = self.sldr_bkgd.GetValue()/SLIDER_SCALE
        
        self.sldr_bkgd.SetRange(0,self.bkgdMAX*SLIDER_SCALE)
        self.sldr_bkgd.SetValue(self.bkgd_scale*SLIDER_SCALE)        

    def autoContrast(self,event):

        self.minINT = int(np.min(self.plt_img))
        self.maxINT = int(np.max(self.plt_img)/15) # /15 scales image to viewable 
        if self.maxINT == self.minINT:
            self.minINT = self.minINT
            self.maxINT = self.minINT+100
        try:
            self.sldr_min.SetRange(self.minINT,self.maxINT)
            self.sldr_max.SetRange(self.minINT,self.maxINT)
        except:
            pass
        self.minCURRENT = self.minINT
        self.maxCURRENT = self.maxINT
        if self.maxCURRENT > self.maxINT:
            self.maxCURRENT = self.maxINT
        self.setContrast()    

    def onContrastRange(self,event):
    
        newMIN = int(self.entr_min.GetValue())
        newMAX = int(self.entr_max.GetValue())
        
        self.minCURRENT = newMIN
        self.maxCURRENT = newMAX

        self.sldr_min.SetRange(newMIN,newMAX)
        self.sldr_max.SetRange(newMIN,newMAX)
        
        self.setContrast()
            

    def onSlider(self,event):

        self.minCURRENT = self.sldr_min.GetValue()
        self.maxCURRENT = self.sldr_max.GetValue()

        ## Create safety to keep min. below max.
        ## mkak 2016.10.20

        self.setContrast()

    def setContrast(self):
        
        self.sldr_min.SetValue(self.minCURRENT)
        self.sldr_max.SetValue(self.maxCURRENT)

        self.plot2D.conf.auto_intensity = False        
        self.plot2D.conf.int_lo['int'] = self.minCURRENT
        self.plot2D.conf.int_hi['int'] = self.maxCURRENT
        
        self.plot2D.redraw()
            
        self.entr_min.SetLabel(str(self.minCURRENT))
        self.entr_max.SetLabel(str(self.maxCURRENT))

    def onFlip(self,event):
        '''
        Eventually, should just set self.raw_img or self.fli_img - better than this
        mkak 2016.10.20
        '''
        
        if self.ch_flp.GetString(self.ch_flp.GetSelection()) != self.flip:
            self.flip = self.ch_flp.GetString(self.ch_flp.GetSelection())

            self.checkFLIPS()
        
            self.plot2D.redraw()

    def checkFLIPS(self):

        if self.flip == 'vertical': # Vertical
            self.plot2D.conf.flip_ud = True
            self.plot2D.conf.flip_lr = False
        elif self.flip == 'horizontal': # Horizontal
            self.plot2D.conf.flip_ud = False
            self.plot2D.conf.flip_lr = True
        elif self.flip == 'both': # both
            self.plot2D.conf.flip_ud = True
            self.plot2D.conf.flip_lr = True
        else: # None
            self.plot2D.conf.flip_ud = False
            self.plot2D.conf.flip_lr = False
                
    def onScale(self,event):
        if self.ch_scl.GetSelection() == 1: ## log
            self.plot2D.conf.log_scale = True
        else:  ## linear
            self.plot2D.conf.log_scale = False
        self.plot2D.redraw()
    
    def onColor(self,event):
        if self.color != self.ch_clr.GetString(self.ch_clr.GetSelection()):
            self.color = self.ch_clr.GetString(self.ch_clr.GetSelection())
            self.setColor()
    
    def setColor(self):
        self.plot2D.conf.cmap['int'] = getattr(colormap, self.color)
        self.plot2D.display(self.plt_img)

##############################################
#### XRD MANIPULATION FUNTIONS 
    def loadIMAGE(self,event):
    
        wildcards = 'XRD image (*.edf,*.tif,*.tiff)|*.tif;*.tiff;*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose 2D XRD image',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            self.openIMAGE(path)
            self.plot2D.display(self.plt_img)       
            self.autoContrast(None)

            str_msg = 'Displaying image: %s' % os.path.split(path)[-1]
            self.write_message(str_msg,panel=0)

    def openIMAGE(self,path):
        self.raw_img = fabioOPEN(path)
        self.checkIMAGE()
        self.calcIMAGE()

    def on1DXRD(self,event):
        print 'Not yet functioning.... will eventually integrate.'
        print '\t Needs calibration and mask and background checks...'
        print

##############################################
#### CALIBRATION FUNCTIONS
    def Calibrate(self,event):
        CalibrationPopup(self)

    def openPONI(self,event):
             
        wildcards = 'pyFAI calibration file (*.poni)|*.poni|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose pyFAI calibration file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:

            try:
                self.ai = pyFAI.load(path)
            except:
                print('Not recognized as a pyFAI calibration file: %s' % path)
                pass

            self.showPONI(None)

    def showPONI(self,event):
        if self.ai == None:
            print ' xxxxx NO CALIBRATION INFORMATION TO PRINT xxxxx '
        else:
            print
            print
            print ' ====== CURRENT CALIBRATION INFORMATION ====== '
            print
            try:
                print 'Detector name: %s' % self.ai.detector.name
                #ai.detector.splineFile
            except:
                pass
            prt_str = 'Detector distance: %.1f mm'
            print prt_str % (self.ai._dist*1000.)
            prt_str = 'Pixel size (x,y): %.1f um, %.1f um'
            print prt_str % (self.ai.detector.pixel1*1000000.,
                             self.ai.detector.pixel2*1000000.)
            prt_str = 'Detector center (x,y): %i pixels, %i pixels'
            print prt_str % (self.ai._poni1/self.ai.detector.pixel1,
                             self.ai._poni2/self.ai.detector.pixel2)
            prt_str = 'Detector tilts: %0.5f, %0.5f %0.5f'
            print prt_str % (self.ai._rot1,self.ai._rot2,self.ai._rot3)
            prt_str = 'Incident energy, wavelegth: %0.2f keV, %0.4f A'
            hc = constants.value(u'Planck constant in eV s') * \
                    constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m
            E = hc/(self.ai._wavelength) ## units: keV
            print prt_str % (E,self.ai._wavelength*1.e10)


##############################################
#### BACKGROUND FUNCTIONS
    def clearBkgd(self,event):
        self.bkgd = np.zeros(self.raw_img.shape)
        self.checkIMAGE()

    def openBkgd(self,event):
    
        wildcards = 'XRD background image (*.edf,*.tif,*.tiff)|*.tif;*.tiff;*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD background image',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            self.bkgd = fabioOPEN(path)
            self.checkIMAGE()

##############################################
#### MASK FUNCTIONS
    def openMask(self,event):

        wildcards = 'pyFAI mask file (*.edf)|*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose pyFAI mask file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            raw_mask = fabioOPEN(path)
            self.mask = np.ones(np.shape(raw_mask))-raw_mask

            self.checkIMAGE()

    def createMask(self,event):
        MaskToolsPopup(self)        

    def clearMask(self,event):
        self.mask = np.zeros(self.raw_img.shape)
        self.checkIMAGE()

    def applyMask(self,event):
        if self.msk_pxls == 0:
            print('No mask defined.')
            self.ch_msk.SetValue(False)
                    
        if event.GetEventObject().GetValue():
            self.use_mask = True
        else:
            self.use_mask = False

        self.calcIMAGE()

        self.setColor()
        self.checkFLIPS()
        self.plot2D.redraw()



class MaskToolsPopup(wx.Dialog):

    def __init__(self,parent):
    
        dialog = wx.Dialog.__init__(self, parent, title='Mask Tools',
                                    style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,
                                    size=(400,350)) ## width x height
        
        self.panel = wx.Panel(self)
        self.parent = parent
        
        self.Init()
        

    def Init(self):

        self.DrawNewPanel()
        self.OKpanel()

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(self.newbox, flag=wx.ALL|wx.EXPAND, border=8)
        vbox.Add(self.OKsizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=10)

        ###########################
        ## Pack all together in self.panel
        self.panel.SetSizer(vbox) 


    def DrawNewPanel(self):
    
        ###########################
        ## Directions
        nwbx = wx.StaticBox(self.panel,label='CREATE NEW MASK', size=(100, 50))
        self.newbox = wx.StaticBoxSizer(nwbx,wx.VERTICAL)

        ###########################
        ## Drawing tools
        hbox_shp = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_shp = wx.StaticText(self.panel, label='DRAWING SHAPE')
        shapes = ['square','circle','pixel','polygon']

        self.ch_shp = wx.Choice(self.panel,choices=shapes)
        self.ch_shp.SetStringSelection(self.parent.color)

        self.ch_shp.Bind(wx.EVT_CHOICE,self.onShape)
    
        hbox_shp.Add(self.txt_shp, flag=wx.RIGHT, border=8)
        hbox_shp.Add(self.ch_shp, flag=wx.EXPAND, border=8)
        self.newbox.Add(hbox_shp, flag=wx.ALL|wx.EXPAND, border=10)
    
        ###########################
        ## Mask Buttons
        vbox_msk = wx.BoxSizer(wx.VERTICAL)
        
        self.btn_msk1 = wx.Button(self.panel,label='CLEAR MASK')
        self.btn_msk2 = wx.Button(self.panel,label='SAVE MASK')

        self.btn_msk1.Bind(wx.EVT_BUTTON,self.onClearMask)
        self.btn_msk2.Bind(wx.EVT_BUTTON,self.onSaveMask)

        vbox_msk.Add(self.btn_msk1, flag=wx.ALL|wx.EXPAND, border=8)
        vbox_msk.Add(self.btn_msk2, flag=wx.ALL|wx.EXPAND, border=8)

        self.newbox.Add(vbox_msk, flag=wx.ALL|wx.EXPAND, border=10)

    def OKpanel(self):
        
        ###########################
        ## OK - CANCEL
        self.OKsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        okBtn  = wx.Button(self.panel, wx.ID_OK     )
        canBtn = wx.Button(self.panel, wx.ID_CANCEL )

        self.OKsizer.Add(canBtn,  flag=wx.RIGHT, border=5)
        self.OKsizer.Add(okBtn,   flag=wx.RIGHT, border=5)
        

    def onShape(self, event):
    
        print 'The shape you chose: %s' %  self.ch_shp.GetString(self.ch_shp.GetSelection())
    
    def ClearMask(self, event):
        
        print 'Clearing the mask...'

    def onSaveMask(self, event):

        print 'This will trigger the saving of a mask.'




      
class diFFit2D(wx.App):
    def __init__(self):
        wx.App.__init__(self)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = Viewer2DXRD()
        frame.Show()
        self.SetTopWindow(frame)

    def OnInit(self):
        self.createApp()
        return True

def registerLarchPlugin():
    return ('_diFFit', {})

class DebugViewer(diFFit2D):
    def __init__(self, **kws):
        diFFit2D.__init__(self, **kws)

    def OnInit(self):
        #self.Init()
        self.createApp()
        #self.ShowInspectionTool()
        return True

if __name__ == '__main__':
    diFFit2D().run()
