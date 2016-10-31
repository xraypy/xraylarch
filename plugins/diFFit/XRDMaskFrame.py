#!/usr/bin/env pythonw
'''
popup for 2D XRD mask file

'''

import os
import numpy as np
from scipy import constants

import wx

from wxmplot.imagepanel import ImagePanel

from larch_plugins.diFFit.ImageControlsFrame import ImageToolboxFrame

HAS_pyFAI = False
try:
    import pyFAI
    import pyFAI.calibrant
    from pyFAI.calibration import Calibration
    HAS_pyFAI = True
except ImportError:
    pass
    
HAS_fabio = False
try:
    import fabio
    HAS_fabio = True
except ImportError:
    pass

###################################

class MaskToolsPopup(wx.Frame):

    def __init__(self,parent):
    
        self.frame = wx.Frame.__init__(self, parent, title='Calibration',size=(900,700))
        
        self.parent = parent
                
        self.statusbar = self.CreateStatusBar(2,wx.CAPTION )
        self.default_cal = 0
        self.default_det = 0
        self.img_fname = ''

        try:
            self.raw_img = parent.plt_img ## raw_img or flp_img or plt_img mkak 2016.10.28
            self.img_fname = 'Image from diFFit2D viewer.'
        except:
            self.raw_img = np.zeros((1024,1024))
        
        self.Init()
        self.Show()
        
#        wx.Window.GetEffectiveMinSize
#        wx.GetBestSize(self)

        self.setDefaults()
        
        
        
    def Init(self):    

        self.panel = wx.Panel(self)

        self.DirectionsSizer()
        self.MainSizer()
#        self.OKsizer()

        self.framebox = wx.BoxSizer(wx.VERTICAL)
        self.framebox.Add(self.dirbox,  flag=wx.ALL|wx.EXPAND, border=10)
        self.framebox.Add(self.mainbox, flag=wx.ALL|wx.EXPAND, border=10)
#        self.framebox.Add(self.okbox,   flag=wx.ALL|wx.ALIGN_RIGHT, border=10)
        
        ###########################
        ## Pack all together in self.panel
        self.panel.SetSizer(self.framebox) 

        ###########################
        ## Set default information
        self.stepno = 0
        self.checkRANGE()
        self.showDirection()

    def setDefaults(self):
    
        ## Sets some typical defaults specific to GSE 13-ID procedure
        print 'this is defaults getting set.'

    def DirectionsSizer(self):

        ###########################
        ## Directions
        dirbx = wx.StaticBox(self.panel,label='DIRECTIONS', size=(100, 50))
        self.dirbox = wx.StaticBoxSizer(dirbx,wx.VERTICAL)
        
        hbox_direct = wx.BoxSizer(wx.HORIZONTAL)
        self.followdir = wx.StaticText(self.panel,label='')

        #hbox_direct.Add(self.txt_shp, flag=wx.RIGHT, border=8)
        hbox_direct.Add(self.followdir, flag=wx.ALL|wx.EXPAND, border=8)
       
        self.dirbox.Add(hbox_direct, flag=wx.ALL|wx.EXPAND, border=10)
    
        hbox_next = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_prev = wx.Button(self.panel,label='PREVIOUS')
        self.btn_next = wx.Button(self.panel,label='NEXT')

        self.btn_prev.Bind(wx.EVT_BUTTON,self.onPREVIOUS)
        self.btn_next.Bind(wx.EVT_BUTTON,self.onNEXT)

        hbox_next.Add(self.btn_prev, flag=wx.ALL, border=8)
        hbox_next.Add((-1, 100))
        hbox_next.Add(self.btn_next, flag=wx.ALIGN_RIGHT|wx.ALL, border=8)
       
        self.dirbox.Add(hbox_next, flag=wx.ALL|wx.EXPAND, border=10)

    def MainSizer(self):
    
        self.mainbox = wx.BoxSizer(wx.VERTICAL)

        ###########################
        ## -----> Main Panel
        self.hmain = wx.BoxSizer(wx.HORIZONTAL)
        
        self.ImageSizer()
        self.DrawNewSizer()

        self.hmain.Add(self.imagebox,proportion=1,flag=wx.ALL|wx.EXPAND, border=10)
        self.hmain.Add(self.drawbox, flag=wx.ALL, border=10)
        
        self.mainbox.Add(self.hmain, flag=wx.ALL|wx.EXPAND, border=10)

    def DrawNewSizer(self):
    
        ###########################
        ## Directions
        nwbx = wx.StaticBox(self.panel,label='CREATE NEW MASK', size=(100, 50))
        self.drawbox = wx.StaticBoxSizer(nwbx,wx.VERTICAL)

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
        self.drawbox.Add(hbox_shp, flag=wx.ALL|wx.EXPAND, border=10)
    
        ###########################
        ## Mask Buttons
        vbox_msk = wx.BoxSizer(wx.VERTICAL)
        
        self.btn_msk1 = wx.Button(self.panel,label='CLEAR MASK')
        self.btn_msk2 = wx.Button(self.panel,label='SAVE MASK')

        self.btn_msk1.Bind(wx.EVT_BUTTON,self.onClearMask)
        self.btn_msk2.Bind(wx.EVT_BUTTON,self.onSaveMask)

        vbox_msk.Add(self.btn_msk1, flag=wx.ALL|wx.EXPAND, border=8)
        vbox_msk.Add(self.btn_msk2, flag=wx.ALL|wx.EXPAND, border=8)

        self.drawbox.Add(vbox_msk, flag=wx.ALL|wx.EXPAND, border=10)

    def onCalSel(self,event):
        print 'Selected calibrant: ',self.ch_cal.GetString(self.ch_cal.GetSelection())

    def onDetSel(self,event):
        print 'Selected detector: ',self.ch_det.GetString(self.ch_det.GetSelection())


    def onEorLSel(self,event): 
        hc = constants.value(u'Planck constant in eV s') * \
                       constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m
        if self.ch_EorL.GetSelection() == 1:
            energy = float(self.entr_EorL.GetValue()) ## units keV
            wavelength = hc/(energy)*1e10 ## units: A
            self.entr_EorL.SetValue(str(wavelength))
        else:
            wavelength = float(self.entr_EorL.GetValue())*1e-10 ## units: m
            energy = hc/(wavelength) ## units: keV
            self.entr_EorL.SetValue(str(energy))

    def onDorPSel(self,event): 
        if self.ch_DorP.GetSelection() == 0:
            self.entr_pix.Hide()
            self.ch_det.Show()
        else:
            self.ch_det.Hide()
            self.entr_pix.Show()

        self.panel.GetSizer().Layout() 
        self.panel.GetParent().Layout()

    def loadIMAGE(self, event): 
        wildcards = 'XRD image (*.edf,*.tif,*.tiff)|*.tif;*.tiff;*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD calibration file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            try:
                self.raw_img = fabio.open(path).data
            except:
                print 'This is not an image openable by fabio.'
                pass
            self.plot2Dimg.display(self.raw_img)       
            self.plot2Dimg.redraw()
            self.AutoContrast()

            self.entr_calimg.Clear()
            self.entr_calimg.SetValue(path) #os.path.split(path)[-1]
 

    def ImageSizer(self):
        '''
        Image Panel
        '''
        self.imagebox = wx.BoxSizer(wx.VERTICAL)
        
        self.plot2Dimage()
        
        self.btn_image = wx.Button(self.panel,label='IMAGE TOOLS')

        self.btn_image.Bind(wx.EVT_BUTTON,self.onImageTools)

        self.imagebox.Add(self.plot2Dimg,proportion=1,flag=wx.ALL|wx.EXPAND, border=10)
        self.imagebox.Add(self.btn_image, flag=wx.ALL, border=10) 

#     def OKsizer(self):
#         ###########################
#         ## OK - CANCEL
#         self.okbox = wx.BoxSizer(wx.HORIZONTAL)
#         
#         okBtn  = wx.Button(self.panel, wx.ID_OK     )
#         canBtn = wx.Button(self.panel, wx.ID_CANCEL )
# 
#         self.okbox.Add(canBtn,  flag=wx.RIGHT, border=5)
#         self.okbox.Add(okBtn,   flag=wx.RIGHT, border=5)
     
    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def onImageTools(self,event):
        
        self.toolbox = ImageToolboxFrame(self.plot2Dimg,self.raw_img)

    def plot2Dimage(self):
    
        self.plot2Dimg = ImagePanel(self.panel,size=(300, 300))
        self.plot2Dimg.messenger = self.write_message

        self.plot2Dimg.display(self.raw_img) 
        self.AutoContrast()      

        self.plot2Dimg.redraw()

    def AutoContrast(self):
    
        self.minINT = int(np.min(self.raw_img))
        self.maxINT = int(np.max(self.raw_img)/15) # /15 scales image to viewable 
        if self.maxINT == self.minINT:
            self.minINT = self.minINT-50
            self.maxINT = self.minINT+100

        self.minCURRENT = self.minINT
        self.maxCURRENT = self.maxINT
        if self.maxCURRENT > self.maxINT:
            self.maxCURRENT = self.maxINT
        
        self.plot2Dimg.conf.auto_intensity = False        
        self.plot2Dimg.conf.int_lo['int'] = self.minCURRENT
        self.plot2Dimg.conf.int_hi['int'] = self.maxCURRENT
        
        ## vertical flip default
        self.plot2Dimg.conf.flip_ud = True
        self.plot2Dimg.conf.flip_lr = False 
       
        self.plot2Dimg.redraw()   
        
    def checkRANGE(self):
    
        if self.stepno <= 0:
            self.stepno = 0
            self.btn_prev.Disable()
        else:
            self.btn_prev.Enable()

        if self.stepno >= 8:
            self.stepno = 8
            self.btn_next.Disable()
        else:
            self.btn_next.Enable()

    def onNEXT(self, event):
        self.stepno = self.stepno + 1
        self.checkRANGE()
        self.showDirection()
    
    def onPREVIOUS(self,event):
        self.stepno = self.stepno - 1
        self.checkRANGE()
        self.showDirection()
    
    def showDirection(self):
        
        dirsteps = ['Enter parameters into the fields below.',
                    'Select point(s) on the first ring.',
                    'Select point(s) on the second ring.',
                    'Select point(s) on the third ring.',
                    'Select point(s) on the fourth ring.',
                    'Select point(s) on the fifth ring.',
                    'Select point(s) on the sixth ring.',
                    'Check preliminary calibration. Continue for final refinement.',
                    'Refinement complete.' ]
                    
        self.followdir.SetLabel(dirsteps[self.stepno])

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
                print
                self.ai = pyFAI.load(path)
                print 'Loading calibration file: %s' % path
            except:
                print('Not recognized as a pyFAI calibration file: %s' % path)
                return

            ## Sets viewer to values in .poni file
            self.entr_dist.SetValue('%0.4f' % self.ai._dist)
            self.entr_pix.SetValue('%0.1f' % float(self.ai.detector.pixel1*1000000.))
            self.ch_DorP.SetSelection(1)
            self.entr_EorL.SetValue('%0.4f' % float(self.ai._wavelength*1.e10))
            self.ch_EorL.SetSelection(1)
            self.onDorPSel(None)
            
            cenx = float(self.ai._poni1)/float(self.ai.detector.pixel1)
            ceny = float(self.ai._poni2)/float(self.ai.detector.pixel2)
            self.entr_cntrx.SetValue('%0.3f' % cenx)
            self.entr_cntry.SetValue('%0.3f' % ceny)

def registerLarchPlugin():
    return ('_diFFit', {})