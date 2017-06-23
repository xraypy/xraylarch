#!/usr/bin/env pythonw
'''
GUI for displaying 2D XRD images

'''
import os
import numpy as np

import matplotlib.cm as colormap

import wx
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception

from wxmplot.imagepanel import ImagePanel
from wxutils import MenuItem

import larch
from larch_plugins.io import tifffile

from larch_plugins.xrd import integrate_xrd,E_from_lambda,xrd1d,read_lambda,calc_cake
from larch_plugins.diFFit.XRDCalibrationFrame import CalibrationPopup
from larch_plugins.diFFit.XRDMaskFrame import MaskToolsPopup
from larch_plugins.diFFit.XRD1Dviewer import Calc1DPopup,diFFit1DFrame

###################################

VERSION = '1 (03-April-2017)'
SLIDER_SCALE = 1000. ## sliders step in unit 1. this scales to 0.001

###################################

class diFFitCakePanel(wx.Panel):
    '''
    Panel for housing 2D XRD image
    '''
    label='Cake'
    def __init__(self,parent,owner=None,_larch=None):

        wx.Panel.__init__(self, parent)
        self.owner = owner

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.plot2D = ImagePanel(self,size=(500, 500),messenger=self.owner.write_message)
        vbox.Add(self.plot2D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        
        self.SetSizer(vbox)
        
class diFFit2DPanel(wx.Panel):
    '''
    Panel for housing 2D XRD cake
    '''
    label='2D XRD'
    def __init__(self,parent,owner=None,_larch=None):

        wx.Panel.__init__(self, parent)
        self.owner = owner

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.plot2D = ImagePanel(self,size=(500, 500),messenger=self.owner.write_message)
        vbox.Add(self.plot2D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        
        self.SetSizer(vbox)

class diFFit2DFrame(wx.Frame):
    '''
    Frame for housing all 2D XRD viewer widgets
    '''
    def __init__(self, _larch=None, xrd1Dviewer=None, ponifile=None, flip='vertical',
                 *args, **kw):
        
        screenSize = wx.DisplaySize()
        x,y = 1000, 720
        if x > screenSize[0] * 0.9:
            x = int(screenSize[0] * 0.9)
            y = int(x*0.6)
        
        label = 'diFFit : 2D XRD Data Analysis Software'
        wx.Frame.__init__(self, None,title=label,size=(x,y))
        
        self.SetMinSize((700,500))
        
        self.statusbar = self.CreateStatusBar(3,wx.CAPTION)

        ## Default image information
        self.name_images = []
        self.data_images = []
        self.raw_img = np.zeros((2048,2048))
        self.flp_img = np.zeros((2048,2048))
        self.plt_img = np.zeros((2048,2048))
        self.cake    = None
        
        self.msk_img  = np.ones((2048,2048))
        self.bkgd_img = np.zeros((2048,2048))
        
        self.bkgd_scale = 0
        self.bkgdMAX = 2
        
        self.use_mask = False
        self.use_bkgd = False
        
        self.xrddisplay1D = xrd1Dviewer
        
        self.color = 'bone'
        self.flip = flip

        self.XRD2DMenuBar()
        self.Panel2DViewer()
        
        self.Centre()
        self.Show()
        
        if ponifile is None:
            self.calfile = None
            self.btn_integ.Disable()
        else:
            self.calfile = ponifile
            self.btn_integ.Enable()

    def write_message(self, s, panel=0):
        '''write a message to the Status Bar'''
        self.SetStatusText(s, panel)

    def optionsON(self):
    
        self.ch_clr.Enable()
        self.sldr_min.Enable()
        self.entr_min.Enable()
        self.sldr_max.Enable()
        self.entr_max.Enable()
        self.btn_ct1.Enable()
        self.ch_flp.Enable()
        self.ch_scl.Enable()
        self.btn_mask.Enable()
        self.btn_bkgd.Enable()

##############################################
#### OPENING AND DISPLAYING IMAGES

    def loadIMAGE(self,event=None):
    
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
            try:
                newimg = tifffile.imread(path)
                print('Reading file: %s' % path)
            except:
                print('Cannot read as an image file: %s' % path)
                return
            
            self.plot2Dxrd(newimg,os.path.split(path)[-1])
            
    def plot2Dxrd(self,img,iname):
        str_msg = 'Displaying image: %s' % iname
        self.write_message(str_msg,panel=0)

        img_no = len(self.data_images)
        self.name_images.append(iname)
        self.data_images.append(img)
        
        self.ch_img.Set(self.name_images)
        self.ch_img.SetStringSelection(iname)

        self.raw_img = self.data_images[img_no]
        self.displayIMAGE()
           
    def displayIMAGE(self):
        self.flipIMAGE()
        self.checkIMAGE()
        self.calcIMAGE()
        
        self.xrd2Dviewer.plot2D.display(self.plt_img)
        self.displayCAKE()
                
        self.autoContrast()

        self.txt_ct2.SetLabel('[ image range: %i, %i ]' % 
                         (np.min(self.plt_img),np.max(self.plt_img)))

        self.optionsON()

    def redrawIMAGE(self):
        self.flipIMAGE()
        self.checkIMAGE()
        self.calcIMAGE()
        self.colorIMAGE()
        
        self.xrd2Dviewer.plot2D.redraw()
        self.displayCAKE()

    def selectIMAGE(self,event=None):
        img_no = self.ch_img.GetSelection()
        self.raw_img = self.data_images[img_no]
        self.displayIMAGE()
        

##############################################
#### IMAGE DISPLAY FUNCTIONS
    def calcIMAGE(self):

        if self.use_mask is True:
            if self.use_bkgd is True:
                self.plt_img = self.flp_img * self.msk_img - self.bkgd_img * self.bkgd_scale
            else:
                self.plt_img = self.flp_img * self.msk_img
        else:
            if self.use_bkgd is True:
                self.plt_img = self.flp_img - self.bkgd_img * self.bkgd_scale
            else:
                self.plt_img = self.flp_img

    def flipIMAGE(self):
        if self.flip == 'vertical': # Vertical
            self.flp_img = self.raw_img[::-1,:]
        elif self.flip == 'horizontal': # Horizontal
            self.flp_img = self.raw_img[:,::-1]
        elif self.flip == 'both': # both
            self.flp_img = self.raw_img[::-1,::-1]
        else: # None
            self.flp_img = self.raw_img

    def checkIMAGE(self):
        
        ## Reshapes/replaces mask and/or background if shape doesn't match that of image    
        if self.msk_img.shape != self.raw_img.shape:
            self.msk_img = np.ones(self.raw_img.shape)
        if self.bkgd_img.shape != self.raw_img.shape:
            self.bkgd_img = np.zeros(self.raw_img.shape)

        ## Calculates the number of pixels in image, masked pixels, and background pixels
        img_pxls  = self.raw_img.shape[0]*self.raw_img.shape[1]
        msk_pxls  = img_pxls - int(sum(sum(self.msk_img)))
        bkgd_pxls = int(sum(sum(self.bkgd_img)))

        ## Enables mask checkbox.
        if msk_pxls == 0 or msk_pxls == img_pxls:
            self.ch_msk.Disable()
            self.msk_img = np.ones(self.raw_img.shape)
        else:
            self.ch_msk.Enable()
        
        ## Enables background slider and sets range.
        if bkgd_pxls == 0:
            self.entr_scale.SetLabel('')
            
            self.sldr_bkgd.Disable()
            self.entr_scale.Disable()
            
            self.use_bkgd = False
            self.entr_scale.SetLabel('0')
        else:
            self.entr_scale.Enable()
            self.sldr_bkgd.Enable()

            self.use_bkgd = True
            self.entr_scale.SetLabel('1')

        self.sldr_bkgd.SetRange(0,self.bkgdMAX*SLIDER_SCALE)
        self.sldr_bkgd.SetValue(self.bkgd_scale*SLIDER_SCALE)

    def colorIMAGE(self):
        self.xrd2Dviewer.plot2D.conf.cmap[0] = getattr(colormap, self.color)
        self.xrd2Dviewer.plot2D.display(self.plt_img)

        if self.cake is not None:
            self.xrd2Dcake.plot2D.conf.cmap[0] = getattr(colormap, self.color)
            self.xrd2Dcake.plot2D.display(self.cake[0])

    def setCOLOR(self,event=None):
        if self.color != self.ch_clr.GetString(self.ch_clr.GetSelection()):
            self.color = self.ch_clr.GetString(self.ch_clr.GetSelection())
            self.colorIMAGE()

    def setFLIP(self,event=None):
        self.flip = self.ch_flp.GetString(self.ch_flp.GetSelection())
        self.redrawIMAGE()
        
               
    def setZSCALE(self,event=None):
        if self.ch_scl.GetSelection() == 1: ## log
            self.xrd2Dviewer.plot2D.conf.log_scale = True
            if self.cake is not None:
                self.xrd2Dcake.plot2D.conf.log_scale = True
        else:  ## linear
            self.xrd2Dviewer.plot2D.conf.log_scale = False
            if self.cake is not None:
                self.xrd2Dcake.plot2D.conf.log_scale = False
        self.xrd2Dviewer.plot2D.redraw()
        if self.cake is not None:
            self.xrd2Dcake.plot2D.redraw()
    

##############################################
#### BACKGROUND FUNCTIONS
    def onBkgdScale(self,event=None):
        
        self.bkgd_scale = self.sldr_bkgd.GetValue()/SLIDER_SCALE
        self.entr_scale.SetValue(str(self.bkgd_scale))
        
        self.redrawIMAGE()        
        
    def onChangeBkgdScale(self,event=None):

        self.bkgd_scale = float(self.entr_scale.GetValue())
        self.bkgdMAX = (float(self.entr_scale.GetValue()) * 2) / SLIDER_SCALE

        self.sldr_bkgd.SetRange(0,self.bkgdMAX*SLIDER_SCALE)
        self.sldr_bkgd.SetValue(self.bkgd_scale*SLIDER_SCALE)
        
        self.redrawIMAGE()       
        
##############################################
#### IMAGE CONTRAST FUNCTIONS
    def autoContrast(self,event=None):

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

    def onContrastRange(self,event=None):
    
        newMIN = int(self.entr_min.GetValue())
        newMAX = int(self.entr_max.GetValue())
        
        self.sldr_min.SetRange(newMIN,newMAX)
        self.sldr_max.SetRange(newMIN,newMAX)
        
        if newMAX < self.maxCURRENT:
            self.maxCURRENT = newMAX
        if newMIN < self.minCURRENT:
            self.minCURRENT = newMIN
        
        self.setContrast()
            

    def onSlider(self,event=None):

        self.minCURRENT = self.sldr_min.GetValue()
        self.maxCURRENT = self.sldr_max.GetValue()

        if self.minCURRENT > self.maxCURRENT:
            self.sldr_min.SetValue(self.maxCURRENT)
            self.sldr_max.SetValue(self.minCURRENT)       

        self.setContrast()

    def setContrast(self):

        self.sldr_min.SetValue(self.minCURRENT)
        self.sldr_max.SetValue(self.maxCURRENT)

        self.xrd2Dviewer.plot2D.conf.auto_intensity = False        
        self.xrd2Dviewer.plot2D.conf.int_lo[0] = self.minCURRENT
        self.xrd2Dviewer.plot2D.conf.int_hi[0] = self.maxCURRENT
        
        self.xrd2Dviewer.plot2D.redraw()
            
        self.entr_min.SetLabel(str(self.minCURRENT))
        self.entr_max.SetLabel(str(self.maxCURRENT))

        if self.cake is not None:
            self.xrd2Dcake.plot2D.conf.auto_intensity = False        
            self.xrd2Dcake.plot2D.conf.int_lo[0] = self.minCURRENT
            self.xrd2Dcake.plot2D.conf.int_hi[0] = self.maxCURRENT
        
            self.xrd2Dcake.plot2D.redraw()


##############################################
#### XRD MANIPULATION FUNTIONS 

    def saveIMAGE(self,event=None):
        wildcards = 'XRD image (*.tiff)|*.tiff|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, 'Save image as...',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards,
                           style=wx.SAVE|wx.OVERWRITE_PROMPT)

        path, save = None, False
        if dlg.ShowModal() == wx.ID_OK:
            save = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if save:
            
            tifffile.imsave(path,self.plt_img)

    def on1DXRD(self,event=None):
        
        read, save, plot = False, False, False
        if self.calfile is not None and self.plt_img is not None:
            myDlg = Calc1DPopup(self,self.plt_img)
            if myDlg.ShowModal() == wx.ID_OK:
                read = True
                save = myDlg.ch_save.GetValue()
                plot = myDlg.ch_plot.GetValue()

                if int(myDlg.xstep.GetValue()) < 1:
                    attrs = {'steps':5001}
                else:
                    attrs = {'steps':int(myDlg.steps)}
            #attrs = {'wedge':int(myDlg.wedges.GetValues())}
            myDlg.Destroy()
        else:
            print('Data and calibration files must be available for this function.')
            
        if read:
            if save:
                wildcards = '1D XRD file (*.xy)|*.xy|All files (*.*)|*.*'
                dlg = wx.FileDialog(self, 'Save file as...',
                                   defaultDir=os.getcwd(),
                                   wildcard=wildcards,
                                   style=wx.SAVE|wx.OVERWRITE_PROMPT)
                path, save = None, False
                if dlg.ShowModal() == wx.ID_OK:
                    save = True
                    path = dlg.GetPath().replace('\\', '/')
                    attrs.update({'file':path,'save':save})
                dlg.Destroy()
            data1D = integrate_xrd(self.plt_img,self.calfile,**attrs)
            
            ##self.xrd2Dcake.plot2D.display(cake[0])                   

            if plot:
                if self.xrddisplay1D is None:
                    self.xrddisplay1D = diFFit1DFrame()

                attrs = {}
                wvlngth = read_lambda(self.calfile)
                attrs.update({'wavelength':wvlngth,'energy':E_from_lambda(wvlngth)})
                attrs.update({'label':self.name_images[self.ch_img.GetSelection()]})
                data1dxrd = xrd1d(**attrs)
                data1dxrd.xrd_from_2d(data1D,'q')

                try:
                    self.xrddisplay1D.xrd1Dviewer.add1Ddata(data1dxrd)
                    self.xrddisplay1D.Show()
                except PyDeadObjectError:
                    self.xrddisplay1D = diFFit1DFrame()
                    self.xrddisplay1D.xrd1Dviewer.add1Ddata(data1dxrd)
                    self.xrddisplay1D.Show()

##############################################
#### CALIBRATION FUNCTIONS
    def Calibrate(self,event=None):

        CalibrationPopup(self)

    def openPONI(self,event=None):
             
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
            self.calfile = path
            print('Loading calibration file: %s' % path)
            self.btn_integ.Enable()
            self.displayCAKE()

    def displayCAKE(self):
    
        if self.plt_img is not None and self.calfile is not None:
            self.cake = calc_cake(self.plt_img, self.calfile, unit='q') #, mask=self.msk_img, dark=self.bkgd)
            self.xrd2Dcake.plot2D.display(self.cake[0])
            
            self.xrd2Dcake.plot2D.conf.auto_intensity = False        
            self.xrd2Dcake.plot2D.conf.int_lo[0] = self.xrd2Dviewer.plot2D.conf.int_lo[0]
            self.xrd2Dcake.plot2D.conf.int_hi[0] = self.xrd2Dviewer.plot2D.conf.int_hi[0]
        
            self.xrd2Dcake.plot2D.redraw()

            
            ## set to same contrast as 2D viewer
            ## call again anytime changing something like flip or mask or background
        
   
##############################################
#### BACKGROUND FUNCTIONS
    def clearBkgd(self,event=None):

        self.bkgd = np.zeros(self.raw_img.shape)
        self.checkIMAGE()

    def openBkgd(self,event=None):
    
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
            try:
                self.bkgd_img = np.array(tifffile.imread(path))
                self.checkIMAGE()
                print('Reading background: %s' % path)
            except:
                print('Cannot read as an image file: %s' % path)
                return


##############################################
#### MASK FUNCTIONS
    def openMask(self,event=None):

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
            try:
                try:
                    raw_mask = np.array(tifffile.imread(path))
                except:
                    import fabio
                    raw_mask = fabio.open(path).data
                self.msk_img = np.ones(raw_mask.shape)-raw_mask
                self.checkIMAGE()
                print('Reading mask: %s' % path)
            except:
                print('Cannot read as mask file: %s' % path)
                return

        self.ch_msk.SetValue(True)
        self.applyMask(event=True)

#     def createMask(self,event=None):
#         
#         MaskToolsPopup(self)
#         print('Popup to create mask!')

    def clearMask(self,event=None):

        self.msk_img = np.zeros(self.raw_img.shape)
        self.checkIMAGE()

    def applyMask(self,event=None):
                    
        self.use_mask = self.ch_msk.GetValue()
        self.redrawIMAGE() 

##############################################
#### HELP FUNCTIONS
    def onAbout(self, event=None):
        info = wx.AboutDialogInfo()
        info.SetName('diFFit2D XRD Data Viewer')
        desc = 'Using X-ray Larch version: %s' % larch.version.__version__
        info.SetDescription(desc)
        info.SetVersion(VERSION)
        info.AddDeveloper('Margaret Koker: koker at cars.uchicago.edu')
        dlg = wx.AboutBox(info)

##############################################
#### PANEL DEFINITIONS
    def onExit(self, event=None):
        try:
            if hasattr(self.exit_callback, '__call__'):
                self.exit_callback()
        except:
            pass

        try:
            self.Destroy()
        except:
            pass
        

    def XRD2DMenuBar(self):

        menubar = wx.MenuBar()
        
        ###########################
        ## diFFit2D
        diFFitMenu = wx.Menu()
        
        MenuItem(self, diFFitMenu, '&Open diffration image', '', self.loadIMAGE)
        MenuItem(self, diFFitMenu, 'Sa&ve displayed image to file', '', self.saveIMAGE)
#         MenuItem(self, diFFitMenu, '&Save settings', '', None)
#         MenuItem(self, diFFitMenu, '&Load settings', '', None)
#         MenuItem(self, diFFitMenu, 'A&dd analysis to map file', '', None)
        MenuItem(self, diFFitMenu, '&Quit', 'Quit program', self.onExit)

        menubar.Append(diFFitMenu, '&diFFit2D')

        ###########################
        ## Process
        ProcessMenu = wx.Menu()
        
        MenuItem(self, ProcessMenu, 'Load &mask file', '', self.openMask)
        MenuItem(self, ProcessMenu, 'Remove current mas&k', '', self.clearMask)
#         MenuItem(self, ProcessMenu, 'C&reate mas&k', '', self.createMask)
        ProcessMenu.AppendSeparator()
        MenuItem(self, ProcessMenu, 'Load &background image', '', self.openBkgd)
        MenuItem(self, ProcessMenu, 'Remove current back&ground image', '', self.clearBkgd)
        
        menubar.Append(ProcessMenu, '&Process')

        ###########################
        ## Analyze
        AnalyzeMenu = wx.Menu()
        
#         MenuItem(self, AnalyzeMenu, '&Calibrate', '', self.Calibrate)
        MenuItem(self, AnalyzeMenu, 'Load cali&bration file', '', self.openPONI)
#         MenuItem(self, AnalyzeMenu, 'Show current calibratio&n', '', None)
        AnalyzeMenu.AppendSeparator()
        MenuItem(self, AnalyzeMenu, '&Integrate (open 1D viewer)', '', self.on1DXRD)

        menubar.Append(AnalyzeMenu, 'Anal&yze')

        ###########################
        ## Help
        HelpMenu = wx.Menu()
        
        MenuItem(self, HelpMenu, '&About', 'About diFFit2D viewer', self.onAbout)

        menubar.Append(HelpMenu, '&Help')

        ###########################
        ## Create Menu Bar
        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_CLOSE, self.onExit)

    def LeftSidePanel(self,panel):
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        imgbox = self.ImageBox(self.panel)
        vistools = self.Toolbox(self.panel)
        
        vbox.Add(imgbox,flag=wx.ALL|wx.EXPAND,border=10)
        vbox.Add(vistools,flag=wx.ALL,border=10)

        return vbox

    def Panel2DViewer(self):
        '''
        Frame for housing all 2D XRD viewer widgets
        '''
        self.panel = wx.Panel(self)

        leftside = self.LeftSidePanel(self.panel)
        rightside = self.RightSidePanel(self.panel)        

        panel2D = wx.BoxSizer(wx.HORIZONTAL)
        panel2D.Add(leftside,flag=wx.ALL,border=10)
        panel2D.Add(rightside,proportion=1,flag=wx.EXPAND|wx.ALL,border=10)

        self.panel.SetSizer(panel2D)

    def ImageBox(self,panel):
        '''
        Frame for data toolbox
        '''
        
        tlbx = wx.StaticBox(self.panel,label='DISPLAYED IMAGE')
        vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)


        ###########################
        ## DATA CHOICE

        self.ch_img = wx.Choice(self.panel,choices=self.name_images)
        self.ch_img.Bind(wx.EVT_CHOICE, self.selectIMAGE)
        vbox.Add(self.ch_img, flag=wx.EXPAND|wx.ALL, border=8)
    
        return vbox    

    
    def Toolbox(self,panel):
        '''
        Frame for visual toolbox
        '''
        
        tlbx = wx.StaticBox(self.panel,label='TOOLBOX')#, size=(200, 200))
        vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)

        ###########################
        ## Color
        hbox_clr = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_clr = wx.StaticText(self.panel, label='COLOR')
        colors = []
        for key in colormap.datad:
            if not key.endswith('_r'):
                colors.append(key)
        self.ch_clr = wx.Choice(self.panel,choices=colors)

        self.ch_clr.Bind(wx.EVT_CHOICE,self.setCOLOR)
    
        hbox_clr.Add(self.txt_clr, flag=wx.RIGHT,  border=6)
        hbox_clr.Add(self.ch_clr,  flag=wx.RIGHT,  border=6)
        vbox.Add(hbox_clr,         flag=wx.ALL,    border=4)
    
        ###########################
        ## Contrast
        vbox_ct = wx.BoxSizer(wx.VERTICAL)
    
        hbox_ct1 = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_ct1 = wx.StaticText(self.panel, label='CONTRAST')
        self.txt_ct2 = wx.StaticText(self.panel, label='')
        
        hbox_ct1.Add(self.txt_ct1, flag=wx.RIGHT,         border=6)
        hbox_ct1.Add(self.txt_ct2, flag=wx.RIGHT,         border=6)
        vbox_ct.Add(hbox_ct1,      flag=wx.TOP|wx.BOTTOM, border=4)
    
        hbox_ct2 = wx.BoxSizer(wx.HORIZONTAL)
        self.ttl_min = wx.StaticText(self.panel, label='min')
        self.sldr_min = wx.Slider(self.panel)
        self.entr_min = wx.TextCtrl(self.panel,style=wx.TE_PROCESS_ENTER)

        self.sldr_min.Bind(wx.EVT_SLIDER,self.onSlider)
        self.entr_min.Bind(wx.EVT_TEXT_ENTER,self.onContrastRange)
            
        hbox_ct2.Add(self.ttl_min,  flag=wx.RIGHT,         border=6)
        hbox_ct2.Add(self.sldr_min, flag=wx.RIGHT,         border=6)
        hbox_ct2.Add(self.entr_min, flag=wx.RIGHT|wx.ALIGN_RIGHT, border=6)
        vbox_ct.Add(hbox_ct2,       flag=wx.TOP|wx.BOTTOM, border=4)        
    
        hbox_ct3 = wx.BoxSizer(wx.HORIZONTAL)
        self.ttl_max = wx.StaticText(self.panel, label='max')
        self.sldr_max = wx.Slider(self.panel)
        self.entr_max = wx.TextCtrl(self.panel,style=wx.TE_PROCESS_ENTER)

        self.sldr_max.Bind(wx.EVT_SLIDER,self.onSlider) 
        self.entr_max.Bind(wx.EVT_TEXT_ENTER,self.onContrastRange)
        
        hbox_ct3.Add(self.ttl_max,  flag=wx.RIGHT,         border=6)
        hbox_ct3.Add(self.sldr_max, flag=wx.RIGHT,         border=6)
        hbox_ct3.Add(self.entr_max, flag=wx.RIGHT|wx.ALIGN_RIGHT, border=6)
        vbox_ct.Add(hbox_ct3,       flag=wx.TOP|wx.BOTTOM, border=4)

        hbox_ct4 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_ct1 = wx.Button(self.panel,label='reset range')

        self.btn_ct1.Bind(wx.EVT_BUTTON,self.autoContrast)

        hbox_ct4.Add(self.btn_ct1, flag=wx.RIGHT,              border=6)
        vbox_ct.Add(hbox_ct4,      flag=wx.ALIGN_RIGHT|wx.TOP, border=6)
        vbox.Add(vbox_ct,          flag=wx.ALL,                border=4)

        ###########################
        ## Flip
        hbox_flp = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_flp = wx.StaticText(self.panel, label='IMAGE FLIP')
        flips = ['none','vertical','horizontal','both']
        self.ch_flp = wx.Choice(self.panel,choices=flips)

        self.ch_flp.Bind(wx.EVT_CHOICE,self.setFLIP)
    
        hbox_flp.Add(self.txt_flp, flag=wx.RIGHT|wx.TOP|wx.BOTTOM, border=6)
        hbox_flp.Add(self.ch_flp,  flag=wx.RIGHT|wx.TOP|wx.BOTTOM, border=6)
        vbox.Add(hbox_flp,         flag=wx.ALL,   border=4)
    
        ###########################
        ## Scale
        hbox_scl = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_scl = wx.StaticText(self.panel, label='SCALE')
        scales = ['linear','log']
        self.ch_scl = wx.Choice(self.panel,choices=scales)
    
        self.ch_scl.Bind(wx.EVT_CHOICE,self.setZSCALE)
    
        hbox_scl.Add(self.txt_scl, flag=wx.RIGHT|wx.TOP|wx.BOTTOM, border=6)
        hbox_scl.Add(self.ch_scl,  flag=wx.RIGHT|wx.TOP|wx.BOTTOM, border=6)
        vbox.Add(hbox_scl,         flag=wx.ALL,   border=4)


        ###########################
        ## Mask
        hbox_msk = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_mask = wx.Button(panel,label='MASK')
        self.ch_msk = wx.CheckBox(self.panel,label='Apply?')
        
        self.ch_msk.Bind(wx.EVT_CHECKBOX,self.applyMask)
        self.btn_mask.Bind(wx.EVT_BUTTON,self.openMask)
    
        hbox_msk.Add(self.btn_mask, flag=wx.RIGHT|wx.TOP|wx.BOTTOM, border=6)
        hbox_msk.Add(self.ch_msk,   flag=wx.RIGHT|wx.TOP|wx.BOTTOM, border=6)
        vbox.Add(hbox_msk,          flag=wx.ALL,   border=4)
    
        ###########################
        ## Background
        hbox_bkgd1 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_bkgd = wx.Button(panel,label='BACKGROUND')
        self.sldr_bkgd = wx.Slider(self.panel)

        self.sldr_bkgd.Bind(wx.EVT_SLIDER,self.onBkgdScale)
        self.btn_bkgd.Bind(wx.EVT_BUTTON,self.openBkgd)

        hbox_bkgd1.Add(self.btn_bkgd,  flag=wx.RIGHT|wx.TOP,         border=6)
        hbox_bkgd1.Add(self.sldr_bkgd, flag=wx.ALIGN_RIGHT|wx.TOP,   border=6)
        vbox.Add(hbox_bkgd1,           flag=wx.TOP|wx.BOTTOM, border=4)


        hbox_bkgd2 = wx.BoxSizer(wx.HORIZONTAL)
        self.entr_scale = wx.TextCtrl(self.panel,style=wx.TE_PROCESS_ENTER)
        
        self.entr_scale.Bind(wx.EVT_TEXT_ENTER,self.onChangeBkgdScale)
              
        hbox_bkgd2.Add(self.entr_scale, flag=wx.RIGHT,                        border=6)
        vbox.Add(hbox_bkgd2,            flag=wx.TOP|wx.BOTTOM|wx.ALIGN_RIGHT, border=4)

        self.sldr_bkgd.SetValue(self.bkgd_scale*SLIDER_SCALE)
        self.sldr_bkgd.Disable()
        self.entr_scale.Disable()

        ###########################
        ## Set defaults  
        self.ch_clr.SetStringSelection(self.color)
        self.ch_flp.SetStringSelection(self.flip)
        self.ch_msk.Disable()
        self.ch_clr.Disable()
        self.sldr_min.Disable()
        self.entr_min.Disable()
        self.sldr_max.Disable()
        self.entr_max.Disable()
        self.btn_ct1.Disable()
        self.ch_flp.Disable()
        self.ch_scl.Disable()
        self.btn_mask.Disable()
        self.btn_bkgd.Disable()
        
        return vbox    

    def panel2DXRDplot(self,panel):
    
        self.nb = wx.Notebook(panel)
        
        ## create the page windows as children of the notebook
        self.xrd2Dviewer = diFFit2DPanel(self.nb,owner=self)
        self.xrd2Dcake   = diFFitCakePanel(self.nb,owner=self)

        ## add the pages to the notebook with the label to show on the tab
        self.nb.AddPage(self.xrd2Dviewer, '2D Image')
        self.nb.AddPage(self.xrd2Dcake,   'Cake')

        ## put the notebook in a sizer for the panel to manage the layout
        sizer = wx.BoxSizer()
        sizer.Add(self.nb, -1, wx.EXPAND)
        panel.SetSizer(sizer)

    def RightSidePanel(self,panel):
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel2DXRDplot(panel)
        btnbox = self.QuickButtons(panel)
#         vbox.Add(self.plot2D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        vbox.Add(self.nb,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
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
    
class diFFit2D(wx.App):
    def __init__(self):
        wx.App.__init__(self)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = diFFit2DFrame()
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
        self.createApp()
        return True

if __name__ == '__main__':
    diFFit2D().run()
