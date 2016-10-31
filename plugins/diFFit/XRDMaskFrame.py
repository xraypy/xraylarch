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
    
        self.frame = wx.Frame.__init__(self, parent, title='Create mask')#,size=(900,700))
        
        self.parent = parent
        self.statusbar = self.CreateStatusBar(2,wx.CAPTION )

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

        self.MainSizer()

        self.framebox = wx.BoxSizer(wx.VERTICAL)
        self.framebox.Add(self.mainbox, flag=wx.ALL|wx.EXPAND, border=10)
        
        ###########################
        ## Pack all together in self.panel
        self.panel.SetSizer(self.framebox) 


    def setDefaults(self):
    
        ## Sets some typical defaults specific to GSE 13-ID procedure
        print 'this is defaults getting set.'


    def MainSizer(self):
    
        self.mainbox = wx.BoxSizer(wx.VERTICAL)

        ###########################
        ## -----> Main Panel
        self.hmain = wx.BoxSizer(wx.HORIZONTAL)
        
        self.ImageSizer()
        self.DrawNewSizer()

        self.hmain.Add(self.imagebox,proportion=1,flag=wx.ALL|wx.EXPAND, border=10)
        self.hmain.Add(self.drawbox, flag=wx.ALL, border=10)
        
        self.btn_save = wx.Button(self.panel,label='SAVE MASK')
        self.btn_save.Bind(wx.EVT_BUTTON,self.saveMask)
        self.hmain.Add(self.btn_save, flag=wx.ALL, border=10)
        
        
        self.mainbox.Add(self.hmain, flag=wx.ALL|wx.EXPAND, border=10)

    def DrawNewSizer(self):
    
        ###########################
        ## Directions
        nwbx = wx.StaticBox(self.panel,label='Drawing Tools', size=(100, 50))
        self.drawbox = wx.StaticBoxSizer(nwbx,wx.VERTICAL)

        ###########################
        ## Drawing tools
        hbox_shp = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_shp = wx.StaticText(self.panel, label='SELECTED SHAPE')
        shapes = ['square','circle','pixel','polygon']

        self.ch_shp = wx.Choice(self.panel,choices=shapes)
        self.ch_shp.SetStringSelection(self.parent.color)

        self.ch_shp.Bind(wx.EVT_CHOICE,self.ShapeChoice)
    
        hbox_shp.Add(self.txt_shp, flag=wx.RIGHT, border=8)
        hbox_shp.Add(self.ch_shp, flag=wx.EXPAND, border=8)
        self.drawbox.Add(hbox_shp, flag=wx.ALL|wx.EXPAND, border=10)
    
        ###########################
        ## Mask Buttons
        vbox_msk = wx.BoxSizer(wx.VERTICAL)

        self.btn_msk1 = wx.Button(self.panel,label='DELETE SELECTED AREA')        
        self.btn_msk2 = wx.Button(self.panel,label='CLEAR MASK (ALL SHAPES)')

        self.btn_msk2.Bind(wx.EVT_BUTTON,self.clearMask)


        vbox_msk.Add(self.btn_msk1, flag=wx.ALL|wx.EXPAND, border=8)
        vbox_msk.Add(self.btn_msk2, flag=wx.ALL|wx.EXPAND, border=8)

        self.drawbox.Add(vbox_msk, flag=wx.ALL|wx.EXPAND, border=10)

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

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def onImageTools(self,event):
        
        self.toolbox = ImageToolboxFrame(self.plot2Dimg,self.raw_img)

    def plot2Dimage(self):
    
        self.plot2Dimg = ImagePanel(self.panel)#,size=(300, 300))
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

    def ShapeChoice(self, event):
    
        print 'The shape you chose: %s' %  self.ch_shp.GetString(self.ch_shp.GetSelection())
    
    def clearMask(self, event):
        
        print 'Clearing the mask...'

    def saveMask(self, event):

        print 'This will trigger the saving of a mask.'

class diFFit_XRDmask(wx.App):
    def __init__(self):
        wx.App.__init__(self)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = MaskToolsPopup(None)
        frame.Show()
        self.SetTopWindow(frame)

    def OnInit(self):
        self.createApp()
        return True

def registerLarchPlugin():
    return ('_diFFit', {})

class DebugViewer(diFFit_XRDmask):
    def __init__(self, **kws):
        diFFit_XRDmask.__init__(self, **kws)

    def OnInit(self):
        #self.Init()
        self.createApp()
        #self.ShowInspectionTool()
        return True

if __name__ == '__main__':
    diFFit_XRDmask().run()
