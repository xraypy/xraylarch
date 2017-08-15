#!/usr/bin/env pythonw
'''
GUI for displaying 2D XRD images

'''
import os
import numpy as np

import matplotlib.cm as colormap
from functools import partial

import wx
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception

from wxmplot.imagepanel import ImagePanel
from wxutils import MenuItem

import larch
from larch_plugins.io import tifffile
from larch import Group


from larch_plugins.xrd import integrate_xrd,E_from_lambda,xrd1d,read_lambda,calc_cake
from larch_plugins.xrmmap import read_xrd_netcdf
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

        self.open_image = []

        ## Default image information        
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
    
        if len(self.open_image) > 0:
            img_no = self.ch_img.GetSelection()
            self.open_image[img_no]
            
            self.ch_clr.Enable()
            self.sldr_cntrst.Enable()
            self.entr_min.Enable()
            self.entr_max.Enable()
            self.btn_ct1.Enable()
            self.ch_flp.Enable()
            self.ch_scl.Enable()
            self.btn_mask.Enable()
            self.btn_bkgd.Enable()
        
            if self.open_image[img_no].frames > 1:
                self.frmsldr.Enable()
                for btn in self.frm_btn: btn.Enable()
            else:
                self.frmsldr.Disable()
                for btn in self.frm_btn: btn.Disable()

##############################################
#### OPENING AND DISPLAYING IMAGES

    def loadIMAGE(self,event=None):
    
        wildcards = 'XRD image (*.*)|*.*|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose 2D XRD image',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            
            
            print('Reading file: %s' % path)
            try:
                image = tifffile.imread(path)
            except:
                image = read_xrd_netcdf(path,verbose=True)
            finally:
                print('  Successfully read.')
            iname = os.path.split(path)[-1]

            self.write_message('Displaying image: %s' % iname, panel=0)
            self.open_image.append(XRDImg(label=iname, path=path, image=image))

            name_images = [image.label for image in self.open_image]
            self.ch_img.Set(name_images)
            self.ch_img.SetStringSelection(iname)

            self.raw_img = self.open_image[-1].get_image()
            print ' calling displayIMAGE' 
            self.displayIMAGE()
                
            if self.open_image[-1].frames > 1:
                self.frmsldr.SetRange(0,(self.open_image[-1].frames-1))
                self.frmsldr.SetValue(self.open_image[-1].i)
            else:
                self.frmsldr.Disable()
                for btn in self.frm_btn: btn.Disable()

            
    def chng_image(self,flag='slider',event=None):
    
        print '  executing chng_image'
    
        if len(self.open_image) > 0:
            img_no = self.ch_img.GetSelection()
            if flag=='next':
                i = self.open_image[img_no].i + 1
            elif flag=='previous':
                i = self.open_image[img_no].i - 1
            elif flag=='slider':
                i = self.frmsldr.GetValue()
        
            self.raw_img = self.open_image[img_no].get_image(i=i)
            
            self.frmsldr.SetValue(self.open_image[img_no].i)
            print ' calling displayIMAGE' 
            self.displayIMAGE(contrast=False,unzoom=False)
           
    def displayIMAGE(self,contrast=True,unzoom=True):
        print '  executing displayIMAGE'
        
        print ' calling flipIMAGE'
        self.flipIMAGE()
        print ' calling checkIMAGE'
        self.checkIMAGE()
        print ' calling calcIMAGE'
        self.calcIMAGE()
        
        print 'DISPLAY...!'
        self.xrd2Dviewer.plot2D.display(self.plt_img,unzoom=unzoom)
        #self.displayCAKE()
                
        if contrast: self.autoContrast()

        self.txt_ct2.SetLabel('[ image range: %i to %i ]' % 
                         (np.min(self.plt_img),np.max(self.plt_img)))

        self.optionsON()

    def redrawIMAGE(self):
        print '  executing redrawIMAGE'

        print ' calling flipIMAGE'
        self.flipIMAGE()
        print ' calling checkIMAGE'
        self.checkIMAGE()
        print ' calling calcIMAGE'
        self.calcIMAGE()
        print ' calling colorIMAGE'
        self.colorIMAGE()
        
        self.xrd2Dviewer.plot2D.redraw()
        #self.displayCAKE()

    def selectIMAGE(self,event=None):
        print '  executing selectIMAGE'
        img_no = self.ch_img.GetSelection()
        self.raw_img = self.open_image[img_no].get_image()
        print ' calling displayIMAGE'        
        self.displayIMAGE()
        

##############################################
#### IMAGE DISPLAY FUNCTIONS
    def calcIMAGE(self):
        print '  executing calcIMAGE'
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
        print '  executing flipIMAGE'
        if self.flip == 'vertical': # Vertical
            self.flp_img = self.raw_img[::-1,:]
        elif self.flip == 'horizontal': # Horizontal
            self.flp_img = self.raw_img[:,::-1]
        elif self.flip == 'both': # both
            self.flp_img = self.raw_img[::-1,::-1]
        else: # None
            self.flp_img = self.raw_img

    def checkIMAGE(self):
        print '  executing checkIMAGE'        
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
            self.sldr_bkgd.Disable()
            self.use_bkgd = False
        else:
            self.sldr_bkgd.Enable()
            self.use_bkgd = True

        self.sldr_bkgd.SetRange(0,self.bkgdMAX*SLIDER_SCALE)
        self.sldr_bkgd.SetValue(self.bkgd_scale*SLIDER_SCALE)

    def colorIMAGE(self):
        print '  executing colorIMAGE'
        self.xrd2Dviewer.plot2D.conf.cmap[0] = getattr(colormap, self.color)
        self.xrd2Dviewer.plot2D.display(self.plt_img,unzoom=False)

        if self.cake is not None:
            self.xrd2Dcake.plot2D.conf.cmap[0] = getattr(colormap, self.color)
            self.xrd2Dcake.plot2D.display(self.cake[0],unzoom=False)

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
        self.redrawIMAGE()        
        
##############################################
#### IMAGE CONTRAST FUNCTIONS
    def autoContrast(self,event=None):

        self.minCURRENT = int(np.min(self.plt_img))
        self.maxCURRENT = int(np.max(self.plt_img)) # /15 scales image to viewable 
        if self.maxCURRENT == self.minCURRENT:
            self.minCURRENT = self.minCURRENT
            self.maxCURRENT = self.minCURRENT+100
        
        self.entr_min.SetValue('%i' % self.minCURRENT)
        self.entr_max.SetValue('%i' % self.maxCURRENT)
        self.sldr_cntrst.SetRange(self.minCURRENT,self.maxCURRENT)
        self.sldr_cntrst.SetValue(int(self.maxCURRENT*0.4))

        self.setContrast() 
        
    def onContrastRange(self,event=None):
    
        self.minCURRENT = int(self.entr_min.GetValue())
        self.maxCURRENT = int(self.entr_max.GetValue())
        
        self.sldr_cntrst.SetRange(self.minCURRENT,self.maxCURRENT)

        self.sldr_cntrst.SetValue(self.maxCURRENT)
        
        self.setContrast()
            

    def onSlider(self,event=None):

        self.maxCURRENT = int(self.sldr_cntrst.GetValue())

        self.setContrast()

    def setContrast(self):

        self.xrd2Dviewer.plot2D.conf.auto_intensity = False        
        self.xrd2Dviewer.plot2D.conf.int_lo[0] = self.minCURRENT
        self.xrd2Dviewer.plot2D.conf.int_hi[0] = self.maxCURRENT
        
        self.xrd2Dviewer.plot2D.redraw()

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
                attrs.update({'label':self.open_image[self.ch_img.GetSelection()].label})
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

        self.ch_img = wx.Choice(self.panel,choices=[])
        self.ch_img.Bind(wx.EVT_CHOICE, self.selectIMAGE)
        vbox.Add(self.ch_img, flag=wx.EXPAND|wx.ALL, border=8)

        self.frmsldr = wx.Slider(self.panel, minValue=0, maxValue=1, 
                                 style = wx.SL_HORIZONTAL|wx.SL_LABELS)
        self.frm_btn = [ wx.Button(self.panel,label=u'\u2190', size=(40, -1)),
                         wx.Button(self.panel,label=u'\u2192', size=(40, -1))]

        frmszr = wx.BoxSizer(wx.HORIZONTAL)
        frmszr.Add(self.frm_btn[0],   flag=wx.RIGHT,            border=6)
        frmszr.Add(self.frmsldr,      flag=wx.EXPAND|wx.RIGHT,  border=6)
        frmszr.Add(self.frm_btn[1],   flag=wx.RIGHT,            border=6)
        
        self.frm_btn[0].Bind(wx.EVT_BUTTON, partial(self.chng_image,'previous') )
        self.frm_btn[1].Bind(wx.EVT_BUTTON, partial(self.chng_image,'next')     )
        self.frmsldr.Bind(wx.EVT_SLIDER,    partial(self.chng_image,'slider')   )

        vbox.Add(frmszr,flag=wx.ALL, border=8)
    
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
        
        self.sldr_cntrst = wx.Slider(self.panel, style=wx.SL_VALUE_LABEL)
        self.entr_min = wx.TextCtrl(self.panel,  style=wx.TE_PROCESS_ENTER, size=(60,-1))
        self.entr_max = wx.TextCtrl(self.panel,  style=wx.TE_PROCESS_ENTER, size=(60,-1))

        self.sldr_cntrst.Bind(wx.EVT_SLIDER,self.onSlider)
        self.entr_min.Bind(wx.EVT_TEXT_ENTER,self.onContrastRange)
        self.entr_max.Bind(wx.EVT_TEXT_ENTER,self.onContrastRange)

        self.btn_ct1 = wx.Button(self.panel,label='reset',size=(50,-1))

        self.btn_ct1.Bind(wx.EVT_BUTTON,self.autoContrast)

            
        vbox_ct.Add(self.sldr_cntrst, flag=wx.EXPAND|wx.RIGHT, border=6)


        ttl_rng = wx.StaticText(self.panel, label='Range:')
        ttl_to = wx.StaticText(self.panel, label='to')
        hbox_ct2.Add(ttl_rng, flag=wx.RIGHT|wx.ALIGN_RIGHT, border=6)
        hbox_ct2.Add(self.entr_min, flag=wx.RIGHT|wx.ALIGN_RIGHT, border=6)
        hbox_ct2.Add(ttl_to, flag=wx.RIGHT|wx.ALIGN_RIGHT, border=6)
        hbox_ct2.Add(self.entr_max, flag=wx.RIGHT|wx.ALIGN_RIGHT, border=6)
        hbox_ct2.Add(self.btn_ct1, flag=wx.RIGHT,              border=6)
        
        vbox_ct.Add(hbox_ct2,      flag=wx.ALIGN_RIGHT|wx.TOP, border=6)
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
        self.sldr_bkgd = wx.Slider(self.panel,style=wx.SL_VALUE_LABEL)

        self.sldr_bkgd.Bind(wx.EVT_SLIDER,self.onBkgdScale)
        self.btn_bkgd.Bind(wx.EVT_BUTTON,self.openBkgd)

        hbox_bkgd1.Add(self.btn_bkgd,  flag=wx.RIGHT|wx.TOP,                 border=6)
        hbox_bkgd1.Add(self.sldr_bkgd, flag=wx.EXPAND|wx.ALIGN_RIGHT|wx.TOP, border=6)
        vbox.Add(hbox_bkgd1,           flag=wx.TOP|wx.BOTTOM,                border=4)

        self.sldr_bkgd.SetValue(self.bkgd_scale*SLIDER_SCALE)

        ###########################
        ## Set defaults  
        self.ch_clr.SetStringSelection(self.color)
        self.ch_flp.SetStringSelection(self.flip)
        self.ch_msk.Disable()
        self.ch_clr.Disable()
        self.sldr_cntrst.Disable()
        self.entr_min.Disable()
        self.entr_max.Disable()
        self.btn_ct1.Disable()
        self.ch_flp.Disable()
        self.ch_scl.Disable()
        self.btn_mask.Disable()
        self.btn_bkgd.Disable()
        self.sldr_bkgd.Disable()
        self.frmsldr.Disable()
        for btn in self.frm_btn: btn.Disable()
        
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


class XRDImg(Group):
    '''
    XRD image class
    
    Attributes:
    ------------
    * self.label         = 'Data: CeO2_Allende'              # name of data set
    * self.path          = '/Volumes/Data/CeO2_Allende.tif'  # file containing x-y data
    * self.type          = 'tiff'                            # file type

    # Data parameters
    * self.image         = None or array          # should be a 3-D array [no * x * y]
    * self.frames        = 1                      # number of frames in self.image
    * self.i             = 0                      # integer indicating current frame
    * self.minval        = 0                      # integer of minimum display contrast
    * self.maxval        = 100                    # integer of maximum display contrast
    * self.curval        = 80                     # integer of current display contrast

    mkak 2017.08.15
    '''

    def __init__(self, label=None, path=None, type='tiff', image=None):

        self.label = label
        self.path  = path
        self.type  = type
        
        self.frames = 1
        self.i = 0
        self.image = np.zeros((1,2048,2048)) if image is None else image
        
        self.check_image()
        self.calc_range()
        

    def check_image(self):

        shp = np.shape(self.image)
        if len(shp) == 2:
            self.image = np.reshape(self.image,(1,shp[0],shp[1]))

        self.frames = np.shape(self.image)[0]
        self.i = 0 if self.frames < 4 else int(self.frames)/2
        
        print 'SHAPE',np.shape(self.image)


    def calc_range(self):

        self.minval = self.image[self.i].min()
        self.maxval = self.image[self.i].max()
        self.curval = (self.maxval-self.minval) * 0.4 + self.minval
    

    def get_image(self,i=None):
    
        if i is not None and i != self.i:
            if i < 0: i == self.frames-1
            if i >= self.frames: i = 0
            self.i = i
        
        return self.image[self.i]



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
