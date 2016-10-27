#!/usr/bin/env pythonw
'''
GUI for displaying 2D XRD images

'''

VERSION = '0 (18-October-2016)'

# Use the wxPython backend of matplotlib
import matplotlib       
matplotlib.use('WXAgg')

import wx

# import h5py
import numpy as np

# HAS_pyFAI = False
# try:
#     import pyFAI
#     import pyFAI.calibrant
#     from pyFAI.calibration import Calibration
#     HAS_pyFAI = True
# except ImportError:
#     pass

from wxmplot.imagepanel import ImagePanel

import matplotlib.pyplot as plt
import matplotlib.cm as colormap

from larch_plugins.diFFit.ImageControlsFrame import ImageToolboxFrame
#from ImageControlsFrame import ImageToolboxFrame
from larch_plugins.diFFit.XRDCalibrationFrame import CalibrationPopup
#from XRDCalibrationFrame import CalibrationPopup


#IMAGE_AND_PATH = '/Users/koker/Data/XRMMappingCode/Search_and_Match/exampleDIFF.tif'
IMAGE_AND_PATH = '/Users/margaretkoker/Data/XRMMappingCode/Search_and_Match/exampleDIFF.tif'

class Viewer2DXRD(wx.Frame):
    '''
    Frame for housing all 2D XRD viewer widgets
    '''
    def __init__(self, *args, **kw):
        label = 'diFFit.py : 2D XRD Viewer'
        wx.Frame.__init__(self, None, -1,title=label, size=(800, 600))
        
        self.SetMinSize((700,500))
        
        self.statusbar = self.CreateStatusBar(2,wx.CAPTION )

        ## Default image information
        self.raw_img  = np.zeros((1024,1024))
        self.plot_img = np.zeros((1024,1024))
        self.mask = np.ones((1024,1024))
        self.bkgd = np.zeros((1024,1024))
        self.bkgd_scale = 0
        
        self.img_pxls = int(self.raw_img.shape[0]*self.raw_img.shape[1])
        self.msk_pxls   = self.img_pxls - int(sum(sum(self.mask)))
        self.bkgd_pxls = int(sum(sum(self.bkgd)))
        self.use_mask = False
        self.use_bkgd = False
        
        self.color = 'bone'
        self.flip = 'vertical'
        
        self.XRD2DMenuBar()
        self.Panel2DViewer()
        
        self.Centre()
        self.Show(True)

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)
        
    def XRD2DMenuBar(self):

        menubar = wx.MenuBar()
        
        ## diFFit2D
        diFFitMenu = wx.Menu()
        
        dm_open = wx.MenuItem(diFFitMenu, -1, '&Open diffration image')
        dm_simg = wx.MenuItem(diFFitMenu, -1, 'Sa&ve image to file')
        dm_sset = wx.MenuItem(diFFitMenu, -1, '&Save settings')
        dm_lset = wx.MenuItem(diFFitMenu, -1, '&Load settings')
        dm_aana = wx.MenuItem(diFFitMenu, -1, '&Add analysis to map file')
        
        diFFitMenu.AppendItem(dm_open)
        diFFitMenu.AppendItem(dm_simg)
        diFFitMenu.AppendSeparator()
        diFFitMenu.AppendItem(dm_sset)
        diFFitMenu.AppendItem(dm_lset)
        diFFitMenu.AppendItem(dm_aana)
        
        menubar.Append(diFFitMenu, '&diFFit2D')

        ## Process
        ProcessMenu = wx.Menu()
        
        pm_lmak = wx.MenuItem(ProcessMenu, -1, '&Load mask file')
        pm_rmak = wx.MenuItem(ProcessMenu, -1, '&Remove current mask')
        pm_cmak = wx.MenuItem(ProcessMenu, -1, '&Create mask')
        pm_smak = wx.MenuItem(ProcessMenu, -1, '&Save mask to file')
        pm_lbak = wx.MenuItem(ProcessMenu, -1, 'Load &background image')
        pm_rbak = wx.MenuItem(ProcessMenu, -1, '&Remove current background image')
        
        ProcessMenu.AppendItem(pm_lmak)
        ProcessMenu.AppendItem(pm_rmak)
        ProcessMenu.AppendItem(pm_cmak)
        ProcessMenu.AppendItem(pm_smak)
        ProcessMenu.AppendSeparator()
        ProcessMenu.AppendItem(pm_lbak)
        ProcessMenu.AppendItem(pm_rbak)
        
        menubar.Append(ProcessMenu, '&Process')

        ## Analyze
        AnalyzeMenu = wx.Menu()
        
        am_ccal = wx.MenuItem(AnalyzeMenu, -1, '&Calibrate')
        am_lcal = wx.MenuItem(AnalyzeMenu, -1, '&Load calibration file')
        am_scal = wx.MenuItem(AnalyzeMenu, -1, '&Save calibration file')
        am_inte = wx.MenuItem(AnalyzeMenu, -1, '&Integrate (open 1D viewer)')
        
        AnalyzeMenu.AppendItem(am_ccal)
        AnalyzeMenu.AppendItem(am_lcal)
        AnalyzeMenu.AppendItem(am_scal)
        AnalyzeMenu.AppendSeparator()
        AnalyzeMenu.AppendItem(am_inte)
        
        menubar.Append(AnalyzeMenu, '&Analyze')

        
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
        self.txt_msk = wx.StaticText(self.panel, label='MASK')
        self.ch_msk = wx.CheckBox(self.panel,label='Apply?')
        
        self.ch_msk.Bind(wx.EVT_CHECKBOX,self.onApply)
    
        hbox_msk.Add(self.txt_msk, flag=wx.RIGHT, border=8)
        hbox_msk.Add(self.ch_msk, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_msk, flag=wx.ALL, border=10)
    
        ###########################
        ## Background
        hbox_bkgd = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_bkgd = wx.StaticText(self.panel, label='BACKGROUND')
        self.sldr_bkgd = wx.Slider(self.panel)

        self.sldr_bkgd.Bind(wx.EVT_SLIDER,self.onBkgdScale)

        self.sldr_bkgd.SetRange(0,5000)
        self.sldr_bkgd.SetValue(self.bkgd_scale)
        if self.bkgd_pxls == 0:
            self.sldr_bkgd.Disable()

        hbox_bkgd.Add(self.txt_bkgd, flag=wx.RIGHT, border=8)
        hbox_bkgd.Add(self.sldr_bkgd, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_bkgd, flag=wx.ALL, border=10)

        ###########################
        ## Set defaults  
        self.ch_clr.SetStringSelection(self.color)
        self.ch_flp.SetStringSelection(self.flip)
        if self.msk_pxls == 0:
            self.ch_msk.Disable()
        

    
        return vbox    

    def onBkgdScale(self,event):
        
        self.bkgd_scale = self.sldr_bkgd.GetValue()/1000.
        
        bkgd_msg = 'Scale bkgd: %.3f' % self.bkgd_scale
        self.write_message(bkgd_msg)
        
        self.calcIMAGE()
        #self.plot2D.display(self.plot_img)
        self.setColor()
        self.checkFLIPS()
        self.plot2D.redraw()      

    def onApply(self,event):
    
        if self.msk_pxls == 0:
            print('No mask defined.')
            self.ch_msk.SetValue(False)
                    
        if event.GetEventObject().GetValue():
            self.use_mask = True
        else:
            self.use_mask = False

        self.calcIMAGE()
        #self.plot2D.display(self.plot_img)
        self.setColor()
        self.checkFLIPS()
        self.plot2D.redraw()

    def autoContrast(self,event):

        self.minINT = int(np.min(self.plot_img))
        self.maxINT = int(np.max(self.plot_img)/15) # /15 scales image to viewable 
        if self.maxINT == self.minINT:
            self.minINT = self.minINT-50
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

        print self.ch_flp.GetString(self.ch_flp.GetSelection())
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
    
    def onColor(self,event):
        if self.color != self.ch_clr.GetString(self.ch_clr.GetSelection()):
            self.setColor()
    
    def setColor(self):
        self.plot2D.conf.cmap['int'] = getattr(colormap, self.color)
        self.plot2D.display(self.plot_img)        
        

    def RightSidePanel(self,panel):
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.plot2DXRD(panel)
        btnbox = self.QuickButtons(panel)
        vbox.Add(self.plot2D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        vbox.Add(btnbox,flag=wx.ALL|wx.ALIGN_RIGHT,border = 10)
        return vbox

    def QuickButtons(self,panel):
        buttonbox = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_calib = wx.Button(panel,label='CALIBRATE')
        self.btn_mask = wx.Button(panel,label='MASK')
        self.btn_integ = wx.Button(panel,label='INTEGRATE (1D)')
        
        self.btn_mask.Bind(wx.EVT_BUTTON,self.onMask)
        self.btn_calib.Bind(wx.EVT_BUTTON,self.onCalibration)
        self.btn_integ.Bind(wx.EVT_BUTTON,self.on1DXRD)
        
        buttonbox.Add(self.btn_calib, flag=wx.ALL, border=8)
        buttonbox.Add(self.btn_mask, flag=wx.ALL, border=8)
        buttonbox.Add(self.btn_integ, flag=wx.ALL, border=8)

        return buttonbox

    def on1DXRD(self,event):
        print 'Not yet functioning.... will eventually integrate.'
        print '\t Needs calibration and mask and background checks...'
        print

    def calcIMAGE(self):

        if self.use_mask is True:
            if self.use_bkgd is True:
                self.plot_img = self.raw_img * self.mask - self.bkgd * self.bkgd_scale
            else:
                self.plot_img = self.raw_img * self.mask
        else:
            if self.use_bkgd is True:
                self.plot_img = self.raw_img - self.bkgd * self.bkgd_scale
            else:
                self.plot_img = self.raw_img
        
        ## Update image control panel if there.
        try:
            self.txt_ct2.SetLabel('[ full range: %i, %i ]' % 
                         (np.min(self.plot_img),np.max(self.plot_img))) 
        except:
            pass

    def openIMAGE(self):

        try:
            import fabio
            self.raw_img = fabio.open(IMAGE_AND_PATH).data
        except:
            print 'Either fabio is missiong or it could not import image.'
            pass
        
        self.checkIMAGE()
        self.calcIMAGE()
            
    def checkIMAGE(self):
    
        if self.mask.shape is not self.raw_img.shape:
            self.mask = np.ones(self.raw_img.shape)

        if self.bkgd.shape is not self.raw_img.shape:
            self.bkgd = np.zeros(self.raw_img.shape)

        ## Remove once working
        ## mkak 2016.10.26
        self.mask[5:500,3:500] = 0
        self.bkgd = np.ones(self.raw_img.shape)

        self.img_pxls = int(self.raw_img.shape[0]*self.raw_img.shape[1])
        self.msk_pxls   = self.img_pxls - int(sum(sum(self.mask)))
        self.bkgd_pxls = int(sum(sum(self.bkgd)))

        if self.msk_pxls == 0:
            self.ch_msk.Disable()
        else:
            self.ch_msk.Enable()
        
        if self.bkgd_pxls == 0:
            self.sldr_bkgd.Disable()
            self.use_bkgd = False
        else:
            self.sldr_bkgd.Enable()
            self.sldr_bkgd.SetRange(0,5000)
            self.sldr_bkgd.SetValue(0)
            self.use_bkgd = True


    def plot2DXRD(self,panel):
    
        self.plot2D = ImagePanel(panel,size=(500, 500))
        self.plot2D.messenger = self.write_message

        ## eventually, don't need this
        self.openIMAGE()           

        self.plot2D.display(self.plot_img)
        self.plot2Ddefaults()
        
        
    def plot2Ddefaults(self):    

        self.setColor()
        self.autoContrast(None)
        self.checkFLIPS()

        self.plot2D.redraw()
        
    def onMask(self,event):
    
        myDlg = MaskToolsPopup()
        
        read = False
        if myDlg.ShowModal() == wx.ID_OK:
            print 'This worked!'
            read = True
        myDlg.Destroy()
        if read:
            print 'You pressed okay.'


    def onCalibration(self,event):
    
        test = CalibrationPopup(self)

        ## How to return information...?
        ## mkak 2016.10.26



class MaskToolsPopup(wx.Dialog):

    def __init__(self):
    
        dialog = wx.Dialog.__init__(self, None, title='Mask Tools',
                                    style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        
        self.panel = wx.Panel(self)

        ## remind me... what's the difference here?
        ## mkak 2016.10.24
        #tlbx = wx.StaticBox(self.panel)
        #vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)
        vbox = wx.BoxSizer(wx.VERTICAL)

        ###########################
        ## Drawing tools
        hbox_shp = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_shp = wx.StaticText(self.panel, label='DRAWING SHAPE')
        shapes = ['square','circle','pixel','polygon']

        self.ch_shp = wx.Choice(self.panel,choices=shapes)
        self.ch_shp.SetStringSelection(self.color)

        self.ch_shp.Bind(wx.EVT_CHOICE,self.onShape)
    
        hbox_shp.Add(self.txt_shp, flag=wx.RIGHT, border=8)
        hbox_shp.Add(self.ch_shp, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_shp, flag=wx.ALL|wx.EXPAND, border=10)
    
        ###########################
        ## Mask Buttons
        vbox_msk = wx.BoxSizer(wx.VERTICAL)
        
        self.btn_msk1 = wx.Button(self.panel,label='CLEAR MASK')
        self.btn_msk2 = wx.Button(self.panel,label='SAVE MASK')
        self.btn_msk3 = wx.Button(self.panel,label='APPLY MASK')

        self.btn_msk1.Bind(wx.EVT_BUTTON,self.onClearMask)
        self.btn_msk2.Bind(wx.EVT_BUTTON,self.onSaveMask)
        self.btn_msk3.Bind(wx.EVT_BUTTON,self.onApplyMask)

        vbox_msk.Add(self.btn_msk1, flag=wx.ALL|wx.EXPAND, border=8)
        vbox_msk.Add(self.btn_msk2, flag=wx.ALL|wx.EXPAND, border=8)
        vbox_msk.Add(self.btn_msk3, flag=wx.ALL|wx.EXPAND, border=8)

        vbox.Add(vbox_msk, flag=wx.ALL|wx.EXPAND, border=10)

        ###########################
        ## OK - CANCEL
        OKsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        okBtn  = wx.Button(self.panel, wx.ID_OK     )
        canBtn = wx.Button(self.panel, wx.ID_CANCEL )

        OKsizer.Add(canBtn,  flag=wx.RIGHT, border=5)
        OKsizer.Add(okBtn,   flag=wx.RIGHT, border=5)
        vbox.Add(OKsizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=10)


        ###########################
        ## Pack all together in self.panel
        self.panel.SetSizer(vbox) 
        

    def onShape(self, event):
    
        print 'The shape you chose: %s' %  self.ch_shp.GetString(self.ch_shp.GetSelection())
    
    def onClearMask(self, event):
        
        print 'Clearing the mask...'

    def onApplyMask(self, event):

        print 'This will apply drawn mask to current image.'
    
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

class DebugViewer(diFFit2D): #, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, **kws):
        diFFit2D.__init__(self, **kws)

    def OnInit(self):
        #self.Init()
        self.createApp()
        #self.ShowInspectionTool()
        return True

if __name__ == '__main__':
    diFFit2D().run()
