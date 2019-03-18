#!/usr/bin/env pythonw
'''
popup for 2D XRD calibration

'''
import os
import numpy as np

import wx

from wxmplot.imagepanel import ImagePanel
from larch.io import tifffile
from larch.xrd import lambda_from_E, E_from_lambda

from .ImageControlsFrame import ImageToolboxFrame


HAS_pyFAI = False
try:
    import pyFAI
    import pyFAI.calibrant
    #from pyFAI.calibration import Calibration
    HAS_pyFAI = True
except ImportError:
    pass


###################################

class CalibrationPopup(wx.Frame):

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
        self.entr_pix.SetValue('400')     ## binned pixels (2x200um)
        self.entr_EorL.SetValue('19.0')     ## 19.0 keV
        self.entr_dist.SetValue('0.5')  ## 0.5 m
        self.ch_det.SetSelection(self.default_det)  ## Perkin detector
        self.ch_cal.SetSelection(self.default_cal)  ## CeO2
        self.entr_calimg.SetValue(self.img_fname)

        self.entr_cntrx.SetValue(str(int(self.raw_img.shape[0]/2))) ## x-position of beam
        self.entr_cntry.SetValue(str(int(self.raw_img.shape[1]/2))) ## y-position of beam

        self.onDorPSel()

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
        self.ParameterSizer()

        self.hmain.Add(self.imagebox,proportion=1,flag=wx.ALL|wx.EXPAND, border=10)
        self.hmain.Add(self.parbox, flag=wx.ALL, border=10)

        self.mainbox.Add(self.hmain, flag=wx.ALL|wx.EXPAND, border=10)

    def ParameterSizer(self):
        '''
        This is where the parameters will be.
        '''

        #self.parbox = wx.BoxSizer(wx.VERTICAL)
        prbx = wx.StaticBox(self.panel,label='PARAMETERS', size=(50, 100))
        self.parbox = wx.StaticBoxSizer(prbx,wx.VERTICAL)

        ###########################
        ## Establish lists from pyFAI
        clbrnts = [] #['None']
        self.dets = [] #['None']
        for key,value in pyFAI.detectors.ALL_DETECTORS.items():
            self.dets.append(key)
            if key == 'perkin':
                self.default_det = len(self.dets)-1
        for key,value in pyFAI.calibrant.ALL_CALIBRANTS.items():
            clbrnts.append(key)
            if key == 'CeO2':
                self.default_cal = len(clbrnts)-1


        #####
        ## Calibration Image selection
        hbox_cal1  = wx.BoxSizer(wx.HORIZONTAL)
        ttl_calimg = wx.StaticText(self.panel, label='Calibration Image:' )
        self.entr_calimg = wx.TextCtrl(self.panel, size=(210, -1))
#         btn_calimg = wx.Button(self.panel, label='Browse...')

#         btn_calimg.Bind(wx.EVT_BUTTON, self.loadIMAGE)

        hbox_cal1.Add(ttl_calimg,       flag=wx.RIGHT,  border=8)
        hbox_cal1.Add(self.entr_calimg, flag=wx.RIGHT|wx.EXPAND,  border=8)
#         hbox_cal1.Add(btn_calimg,       flag=wx.RIGHT,  border=8)
        self.parbox.Add(hbox_cal1,      flag=wx.BOTTOM|wx.TOP, border=8)

        btn_calimg = wx.Button(self.panel, label='Browse...')
        btn_calimg.Bind(wx.EVT_BUTTON, self.loadIMAGE)
        self.parbox.Add(btn_calimg,      flag=wx.BOTTOM|wx.ALIGN_RIGHT, border=8)

        #####
        ## Calibrant selection
        hbox_cal2 = wx.BoxSizer(wx.HORIZONTAL)
        ttl_cal = wx.StaticText(self.panel, label='Calibrant:')
        self.ch_cal = wx.Choice(self.panel,choices=clbrnts)

        self.ch_cal.Bind(wx.EVT_CHOICE,  self.onCalSel)

        hbox_cal2.Add(ttl_cal,     flag=wx.RIGHT,  border=8)
        hbox_cal2.Add(self.ch_cal, flag=wx.RIGHT,  border=8)
        self.parbox.Add(hbox_cal2, flag=wx.BOTTOM, border=30)

        #####
        ## Set-up specific parameters
        hbox_cal3 = wx.BoxSizer(wx.HORIZONTAL)
        txt_exp = wx.StaticText(self.panel, label='SET-UP PARAMETERS')
        btn_pni = wx.Button(self.panel, label='Load file')

        btn_pni.Bind(wx.EVT_BUTTON,  self.openPONI)

        hbox_cal3.Add(txt_exp,     flag=wx.RIGHT,  border=8)
        hbox_cal3.Add(btn_pni,     flag=wx.LEFT,  border=60)
        self.parbox.Add(hbox_cal3, flag=wx.BOTTOM, border=8)

        #####
        ## Detector selection
        hbox_cal4 = wx.BoxSizer(wx.HORIZONTAL)
        self.ch_DorP = wx.Choice(self.panel,choices=['Detector name','Pixel size (um)'])
        self.ch_det  = wx.Choice(self.panel, choices=self.dets)
        self.entr_pix    = wx.TextCtrl(self.panel, size=(110, -1))

        self.ch_det.Bind(wx.EVT_CHOICE,  self.onDetSel)
        self.ch_DorP.Bind(wx.EVT_CHOICE, self.onDorPSel)

        hbox_cal4.Add(self.ch_DorP,  flag=wx.RIGHT,  border=8)
        hbox_cal4.Add(self.ch_det,   flag=wx.RIGHT,  border=8)
        hbox_cal4.Add(self.entr_pix, flag=wx.RIGHT,  border=8)
        self.parbox.Add(hbox_cal4,   flag=wx.BOTTOM, border=8)

        #####
        ## Energy or Wavelength
        hbox_cal5 = wx.BoxSizer(wx.HORIZONTAL)
        self.ch_EorL = wx.Choice(self.panel,choices=['Energy (keV)','Wavelength (A)'])
        self.entr_EorL = wx.TextCtrl(self.panel, size=(110, -1))

        self.ch_EorL.Bind(wx.EVT_CHOICE, self.onEorLSel)

        hbox_cal5.Add(self.ch_EorL,   flag=wx.RIGHT,  border=8)
        hbox_cal5.Add(self.entr_EorL, flag=wx.RIGHT,  border=8)
        self.parbox.Add(hbox_cal5,    flag=wx.BOTTOM, border=8)

        ## Distance
        hbox_cal6 = wx.BoxSizer(wx.HORIZONTAL)
        ttl_dist = wx.StaticText(self.panel, label='Detector distance (m):')
        self.entr_dist = wx.TextCtrl(self.panel, size=(110, -1))

        hbox_cal6.Add(ttl_dist,       flag=wx.RIGHT,  border=8)
        hbox_cal6.Add(self.entr_dist, flag=wx.RIGHT,  border=8)

        self.parbox.Add(hbox_cal6,   flag=wx.BOTTOM, border=8)

        ## Beam center x
        hbox_cal7 = wx.BoxSizer(wx.HORIZONTAL)
        ttl_cntrx = wx.StaticText(self.panel, label='Beam center, x (pixels):')
        self.entr_cntrx = wx.TextCtrl(self.panel, size=(110, -1))

        hbox_cal7.Add(ttl_cntrx,       flag=wx.RIGHT,  border=8)
        hbox_cal7.Add(self.entr_cntrx, flag=wx.RIGHT,  border=8)

        self.parbox.Add(hbox_cal7,   flag=wx.BOTTOM, border=8)

        ## Beam center y
        hbox_cal8 = wx.BoxSizer(wx.HORIZONTAL)
        ttl_cntry = wx.StaticText(self.panel, label='Beam center, y (pixels):')
        self.entr_cntry = wx.TextCtrl(self.panel, size=(110, -1))

        hbox_cal8.Add(ttl_cntry,       flag=wx.RIGHT,  border=8)
        hbox_cal8.Add(self.entr_cntry, flag=wx.RIGHT,  border=8)

        self.parbox.Add(hbox_cal8,   flag=wx.BOTTOM, border=8)


    def onCalSel(self,event=None):
        print('Selected calibrant: %s' % self.ch_cal.GetString(self.ch_cal.GetSelection()))

    def onDetSel(self,event=None):
        print('Selected detector: %s' % self.ch_det.GetString(self.ch_det.GetSelection()))


    def onEorLSel(self,event=None):

        if self.ch_EorL.GetSelection() == 1:
            energy = float(self.entr_EorL.GetValue()) ## units keV
            wavelength = lambda_from_E(energy) ## units: A
            self.entr_EorL.SetValue(str(wavelength))
        else:
            wavelength = float(self.entr_EorL.GetValue())*1e-10 ## units: m
            energy = E_from_lambda(wavelength) ## units: keV
            self.entr_EorL.SetValue(str(energy))

    def onDorPSel(self,event=None):
        if self.ch_DorP.GetSelection() == 0:
            self.entr_pix.Hide()
            self.ch_det.Show()
        else:
            self.ch_det.Hide()
            self.entr_pix.Show()

        self.panel.GetSizer().Layout()
        self.panel.GetParent().Layout()

    def loadIMAGE(self,event=None):
        wildcards = 'XRD image (*.edf,*.tif,*.tiff)|*.tif;*.tiff;*.edf|All files (*.*)|*.*'
        if os.path.exists(self.entr_calimg.GetValue()):
           dfltDIR = self.entr_calimg.GetValue()
        else:
           dfltDIR = os.getcwd()

        dlg = wx.FileDialog(self, message='Choose XRD calibration file',
                           defaultDir=dfltDIR,
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()

        if read:
            try:
#                 self.raw_img = plt.imread(path)
                self.raw_img = tifffile.imread(path)
                #self.raw_img = fabio.open(path).data
            except:
                print('Image not properly opened.')
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

    def onImageTools(self,event=None):

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
        self.plot2Dimg.conf.int_lo[0] = self.minCURRENT
        self.plot2Dimg.conf.int_hi[0] = self.maxCURRENT
#         self.plot2Dimg.conf.int_lo['int'] = self.minCURRENT
#         self.plot2Dimg.conf.int_hi['int'] = self.maxCURRENT

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

    def onNEXT(self,event=None):
        self.stepno = self.stepno + 1
        self.checkRANGE()
        self.showDirection()

    def onPREVIOUS(self,event=None):
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

            try:
                print
                self.ai = pyFAI.load(path)
                print('Loading calibration file: %s' % path)
            except:
                print('Not recognized as a pyFAI calibration file: %s' % path)
                return

            ## Sets viewer to values in .poni file
            self.entr_dist.SetValue('%0.4f' % self.ai._dist)
            self.entr_pix.SetValue('%0.1f' % float(self.ai.detector.pixel1*1000000.))
            self.ch_DorP.SetSelection(1)
            self.entr_EorL.SetValue('%0.4f' % float(self.ai._wavelength*1.e10))
            self.ch_EorL.SetSelection(1)
            self.onDorPSel()

            cenx = float(self.ai._poni1)/float(self.ai.detector.pixel1)
            ceny = float(self.ai._poni2)/float(self.ai.detector.pixel2)
            self.entr_cntrx.SetValue('%0.3f' % cenx)
            self.entr_cntry.SetValue('%0.3f' % ceny)

class CalXRD(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):

        if HAS_pyFAI:
            ## Constructor
            dialog = wx.Dialog.__init__(self, None, title='XRD Calibration',size=(460, 440))
            ## remember: size=(width,height)
            self.panel = wx.Panel(self)

            self.InitUI()
            self.Centre()
            self.Show()

            ## Sets some typical defaults specific to GSE 13-ID procedure
            self.pixel.SetValue('400')     ## binned pixels (2x200um)
            self.EorL.SetValue('19.0')     ## 19.0 keV
            self.Distance.SetValue('0.5')  ## 0.5 m
            self.detslct.SetSelection(22)  ## Perkin detector
            self.calslct.SetSelection(20)  ## CeO2

            if self.slctDorP.GetSelection() == 0:
                self.sizer.Hide(self.pixel)

            ## Do not need flags if defaults are set
            #self.FlagCalibrant = False
            #self.FlagDetector  = False
            self.FlagCalibrant = True
            self.FlagDetector  = True

        else:
            print('pyFAI must be available for calibration.')
            return

    def InitUI(self):


        ## Establish lists from pyFAI
        clbrnts = [] #['None']
        self.dets = [] #['None']
        for key,value in pyFAI.detectors.ALL_DETECTORS.items():
            self.dets.append(key)
        for key,value in pyFAI.calibrant.ALL_CALIBRANTS.items():
            clbrnts.append(key)
        self.CaliPath = None


        ## Calibration Image selection
        caliImg     = wx.StaticText(self.panel,  label='Calibration Image:' )
        self.calFil = wx.TextCtrl(self.panel, size=(190, -1))
        fileBtn1    = wx.Button(self.panel,      label='Browse...'             )

        ## Calibrant selection
        self.calslct = wx.Choice(self.panel,choices=clbrnts)
        CalLbl = wx.StaticText(self.panel, label='Calibrant:' ,style=LEFT)

        ## Detector selection
        self.slctDorP = wx.Choice(self.panel,choices=['Detector','Pixel size (um)'])
        self.detslct  = wx.Choice(self.panel, choices=self.dets)
        self.pixel    = wx.TextCtrl(self.panel, size=(140, -1))

        ## Energy or Wavelength
        self.slctEorL = wx.Choice(self.panel,choices=['Energy (keV)','Wavelength (A)'])
        self.EorL = wx.TextCtrl(self.panel, size=(140, -1))

        ## Refine label
        RefLbl = wx.StaticText(self.panel, label='To be refined...' ,style=LEFT)

        ## Distance
        self.Distance = wx.TextCtrl(self.panel, size=(140, -1))
        DstLbl = wx.StaticText(self.panel, label='Distance (m):' ,style=LEFT)

        hlpBtn = wx.Button(self.panel, wx.ID_HELP   )
        okBtn  = wx.Button(self.panel, wx.ID_OK     )
        canBtn = wx.Button(self.panel, wx.ID_CANCEL )

        self.Bind(wx.EVT_BUTTON,   self.onBROWSE1,  fileBtn1 )
        self.calslct.Bind(wx.EVT_CHOICE,  self.onCalSel)
        self.detslct.Bind(wx.EVT_CHOICE,  self.onDetSel)
        self.slctDorP.Bind(wx.EVT_CHOICE, self.onDorPSel)
        self.slctEorL.Bind(wx.EVT_CHOICE, self.onEorLSel)

        self.sizer = wx.GridBagSizer(3, 3)

        self.sizer.Add(caliImg,       pos = ( 1,1)               )
        self.sizer.Add(self.calFil,   pos = ( 1,2), span = (1,2) )
        self.sizer.Add(fileBtn1,      pos = ( 1,4)               )
        self.sizer.Add(CalLbl,        pos = ( 3,1)               )
        self.sizer.Add(self.calslct,  pos = ( 3,2), span = (1,2) )

        self.sizer.Add(self.slctDorP, pos = ( 4,1)               )
        self.sizer.Add(self.detslct,  pos = ( 4,2), span = (1,4) )
        self.sizer.Add(self.pixel,    pos = ( 5,2), span = (1,2) )

        self.sizer.Add(self.slctEorL, pos = ( 6,1)               )
        self.sizer.Add(self.EorL,     pos = ( 6,2), span = (1,2) )

        self.sizer.Add(RefLbl,        pos = ( 8,1)               )
        self.sizer.Add(DstLbl,        pos = ( 9,1)               )
        self.sizer.Add(self.Distance, pos = ( 9,2), span = (1,2) )

        self.sizer.Add(hlpBtn,        pos = (11,1)               )
        self.sizer.Add(canBtn,        pos = (11,2)               )
        self.sizer.Add(okBtn,         pos = (11,3)               )

        self.FindWindowById(wx.ID_OK).Disable()

        self.panel.SetSizer(self.sizer)


    def onCalSel(self,event=None):
        #if self.calslct.GetSelection() == 0:
        #    self.FlagCalibrant = False
        #else:
        #    self.FlagCalibrant = True
        self.checkOK()

    def onDetSel(self,event=None):
        #if self.detslct.GetSelection() == 0:
        #    self.FlagDetector = False
        #else:
        #    self.FlagDetector = True
        self.checkOK()

    def onCheckOK(self,event=None):
        self.checkOK()

    def checkOK(self):
        if self.FlagCalibrant and self.CaliPath is not None:
            if self.slctDorP.GetSelection() == 1:
                self.FindWindowById(wx.ID_OK).Enable()
            else:
                if self.FlagDetector:
                    self.FindWindowById(wx.ID_OK).Enable()
                else:
                    self.FindWindowById(wx.ID_OK).Disable()
        else:
            self.FindWindowById(wx.ID_OK).Disable()

    def onEorLSel(self,event=None):

        if self.slctEorL.GetSelection() == 1:
            energy = float(self.EorL.GetValue()) ## units keV
            wavelength = lambda_from_E(energy) ## units: A
            self.EorL.SetValue(str(wavelength))
        else:
            wavelength = float(self.EorL.GetValue()) ## units: A
            energy = E_from_lambda(wavelength) ## units: keV
            self.EorL.SetValue(str(energy))

        self.checkOK()

    def onDorPSel(self,event=None):
        if self.slctDorP.GetSelection() == 0:
            self.sizer.Hide(self.pixel)
            self.sizer.Show(self.detslct)
        else:
            self.sizer.Hide(self.detslct)
            self.sizer.Show(self.pixel)

        self.checkOK()

    def onBROWSE1(self,event=None):
        wildcards = 'XRD image (*.edf,*.tif,*.tiff)|*.tif;*.tiff;*.edf|All files (*.*)|*.*'
        if os.path.exists(self.calFil.GetValue()):
           dfltDIR = self.calFil.GetValue()
        else:
           dfltDIR = os.getcwd()

        dlg = wx.FileDialog(self, message='Choose XRD calibration file',
                           defaultDir=dfltDIR,
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()

        if read:
            self.calFil.Clear()
            self.calFil.SetValue(os.path.split(path)[-1])
            self.CaliPath = path
            self.checkOK()

# # # # # # # WAS IN mapviewer.py ; needs to be corrected or removed
#
# # # # def onCalXRD(self, evt=None):
# # # #     """
# # # #     Perform calibration with pyFAI
# # # #     mkak 2016.09.16
# # # #     """
# # # #
# # # #     ### can this pop up pyFAI or Dioptas GUI instead of creating own?
# # # #
# # # #     myDlg = CalXRD()
# # # #
# # # #     path, read = None, False
# # # #     if myDlg.ShowModal() == wx.ID_OK:
# # # #         read = True
# # # #
# # # #     myDlg.Destroy()
# # # #
# # # #     if read:
# # # #
# # # #         usr_calimg = myDlg.CaliPath
# # # #
# # # #         if myDlg.slctEorL.GetSelection() == 1:
# # # #             usr_lambda = float(myDlg.EorL.GetValue())*1e-10 ## units: m
# # # #             usr_E = E_from_lambda(usr_lambda,lambda_units='m') ## units: keV
# # # #         else:
# # # #             usr_E = float(myDlg.EorL.GetValue()) ## units keV
# # # #             usr_lambda = lambda_from_E(usr_E,lambda_units='m') ## units: m
# # # #
# # # #         if myDlg.slctDorP.GetSelection() == 1:
# # # #             usr_pixel = float(myDlg.pixel.GetValue())*1e-6
# # # #         else:
# # # #             usr_det  = myDlg.detslct.GetString(myDlg.detslct.GetSelection())
# # # #         usr_clbrnt  = myDlg.calslct.GetString(myDlg.calslct.GetSelection())
# # # #         usr_dist = float(myDlg.Distance.GetValue())
# # # #
# # # #         verbose = True #False
# # # #         if verbose:
# # # #             print('\n=== Calibration input ===')
# # # #             print('XRD image: %s' % usr_calimg)
# # # #             print('Calibrant: %s' % usr_clbrnt)
# # # #             if myDlg.slctDorP.GetSelection() == 1:
# # # #                 print('Pixel size: %0.1f um' % (usr_pixel*1e6))
# # # #             else:
# # # #                 print('Detector: %s' % usr_det)
# # # #             print('Incident energy: %0.2f keV (%0.4f A)' % (usr_E,usr_lambda*1e10))
# # # #             print('Starting distance: %0.3f m' % usr_dist)
# # # #             print('=========================\n')
# # # #
# # # #         ## Adapted from pyFAI-calib
# # # #         ## note: -l:units mm; -dist:units m
# # # #         ## mkak 2016.09.19
# # # #
# # # #         if myDlg.slctDorP.GetSelection() == 1:
# # # #             pform1 = 'pyFAI-calib -c %s -p %s -e %0.1f -dist %0.3f %s'
# # # #             command1 = pform1 % (usr_clbrnt,usr_pixel,usr_E,usr_dist,usr_calimg)
# # # #         else:
# # # #             pform1 = 'pyFAI-calib -c %s -D %s -e %0.1f -dist %0.3f %s'
# # # #             command1 = pform1 % (usr_clbrnt,usr_det,usr_E,usr_dist,usr_calimg)
# # # #         pform2 = 'pyFAI-recalib -i %s -c %s %s'
# # # #         command2 = pform2 % (usr_calimg.split('.')[0]+'.poni',usr_clbrnt,usr_calimg)
# # # #
# # # #         if verbose:
# # # #             print('\nNot functioning within code yet... but you could execute:')
# # # #             print('\t $ %s' % command1)
# # # #             print('\t $ %s\n\n' % command2)




# class diFFit_XRDcal(wx.App):
#     def __init__(self):
#         wx.App.__init__(self)
#
#     def run(self):
#         self.MainLoop()
#
#     def createApp(self):
#         frame = CalibrationPopup()
#         frame.Show()
#         self.SetTopWindow(frame)
#
#     def OnInit(self):
#         self.createApp()
#         return True
#

# class DebugViewer(diFFit_XRDcal):
#     def __init__(self, **kws):
#         diFFit_XRDcal.__init__(self, **kws)
#
#     def OnInit(self):
#         #self.Init()
#         self.createApp()
#         #self.ShowInspectionTool()
#         return True
#
# if __name__ == '__main__':
#     diFFit_XRDcal().run()
