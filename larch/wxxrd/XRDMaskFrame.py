#!/usr/bin/env pythonw
'''
popup for 2D XRD mask file

'''

import os
import numpy as np

import wx

from wxmplot.imagepanel import ImagePanel
from .ImageControlsFrame import ImageToolboxFrame

from larch.io import tifffile

# HAS_pyFAI = False
# try:
#     import pyFAI
#     import pyFAI.calibrant
#     from pyFAI.calibration import Calibration
#     HAS_pyFAI = True
# except ImportError:
#     pass

# HAS_fabio = False
# try:
#     import fabio
#     HAS_fabio = True
# except ImportError:
#     pass

###################################

class MaskToolsPopup(wx.Frame):

    def __init__(self,parent):

        self.frame = wx.Frame.__init__(self, parent, title='Create mask',size=(800,600))

        self.parent = parent
        self.statusbar = self.CreateStatusBar(2,wx.CAPTION )

        try:
            self.raw_img = parent.plt_img ## raw_img or flp_img or plt_img mkak 2016.10.28
        except:
            self.loadIMAGE()


        self.setDefaults()


        self.Init()
        self.Show()

#        wx.Window.GetEffectiveMinSize
#        wx.GetBestSize(self)


    def Init(self):

        self.panel = wx.Panel(self)

        self.MainSizer()

        self.framebox = wx.BoxSizer(wx.VERTICAL)
        self.framebox.Add(self.mainbox, flag=wx.ALL|wx.EXPAND, border=10)

        ###########################
        ## Pack all together in self.panel
        self.panel.SetSizer(self.framebox)


    def setDefaults(self):

        self.area_list = []

    def MainSizer(self):

        self.mainbox = wx.BoxSizer(wx.VERTICAL)

        ###########################
        ## -----> Main Panel
        self.hmain = wx.BoxSizer(wx.HORIZONTAL)

        self.ImageSizer()
        self.DrawNewSizer()

        self.hmain.Add(self.imagebox,proportion=1,flag=wx.ALL|wx.EXPAND, border=10)
        self.hmain.Add(self.toolbox, flag=wx.ALL, border=10)

        self.mainbox.Add(self.hmain, flag=wx.ALL|wx.EXPAND, border=10)


    def DrawNewSizer(self):

        self.toolbox = wx.BoxSizer(wx.VERTICAL)

        ###########################
        ## Directions
        nwbx = wx.StaticBox(self.panel,label='Drawing Tools', size=(100, 50))
        drawbox = wx.StaticBoxSizer(nwbx,wx.VERTICAL)

        ###########################
        ## Drawing tools
        hbox_shp = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_shp = wx.StaticText(self.panel, label='DRAWING SHAPE')
        shapes = ['circle','pixel','polygon','square']

        self.ch_shp = wx.Choice(self.panel,choices=shapes)

        self.ch_shp.Bind(wx.EVT_CHOICE,self.ShapeChoice)

        hbox_shp.Add(self.txt_shp, flag=wx.RIGHT, border=8)
        hbox_shp.Add(self.ch_shp, flag=wx.EXPAND, border=8)

        drawbox.Add(hbox_shp, flag=wx.ALL|wx.EXPAND, border=10)

        ###########################
        ## Drawn Areas
        vbox_areas = wx.BoxSizer(wx.VERTICAL)
        hbox_areas = wx.BoxSizer(wx.HORIZONTAL)

        self.slct_area = wx.ListBox(self.panel, 26, wx.DefaultPosition, (170, 130), self.area_list, wx.LB_SINGLE)

        self.btn_SHWarea = wx.Button(self.panel,label='SHOW')
        self.btn_DELarea = wx.Button(self.panel,label='DELETE')

        self.btn_SHWarea.Bind(wx.EVT_BUTTON,self.showAREA)
        self.btn_DELarea.Bind(wx.EVT_BUTTON,self.deleteAREA)

        hbox_areas.Add(self.btn_SHWarea, flag=wx.BOTTOM, border=10)
        hbox_areas.Add(self.btn_DELarea, flag=wx.BOTTOM, border=10)

        self.btn_clear = wx.Button(self.panel,label='CLEAR ALL')

        self.btn_clear.Bind(wx.EVT_BUTTON,self.clearMask)

        vbox_areas.Add(self.slct_area, flag=wx.ALL|wx.EXPAND, border=10)
        vbox_areas.Add(hbox_areas, flag=wx.ALL|wx.EXPAND, border=10)
        vbox_areas.Add(self.btn_clear, flag=wx.ALL|wx.EXPAND, border=10)
        drawbox.Add(vbox_areas, flag=wx.ALL|wx.EXPAND, border=10)

        self.toolbox.Add(drawbox, flag=wx.ALL, border=10)

        self.btn_save = wx.Button(self.panel,label='SAVE MASK')
        self.btn_save.Bind(wx.EVT_BUTTON,self.saveMask)
        self.toolbox.Add(self.btn_save, flag=wx.ALL, border=10)

        self.btn_SHWarea.Disable()
        self.btn_DELarea.Disable()
        self.btn_clear.Disable()
        self.btn_save.Disable()

    def startIMAGE(self):

        self.loadIMAGE()

    def loadIMAGE(self,event=None):
        wildcards = 'XRD image (*.edf,*.tif,*.tiff)|*.tif;*.tiff;*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD image',
                           defaultDir=os.getcwd(),
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
                self.raw_img = np.zeros((1024,1024))
        else:
            print('No image selected.')
            self.raw_img = np.zeros((1024,1024))

    def ImageSizer(self):
        '''
        Image Panel
        '''
        self.imagebox = wx.BoxSizer(wx.VERTICAL)

        self.plot2Dimage()

        imagetools = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_image = wx.Button(self.panel,label='IMAGE TOOLS')
        self.btn_load = wx.Button(self.panel,label='CHANGE IMAGE')

        self.btn_image.Bind(wx.EVT_BUTTON,self.onImageTools)
        self.btn_load.Bind(wx.EVT_BUTTON,self.loadIMAGE)

        imagetools.Add(self.btn_load, flag=wx.ALL, border=10)
        imagetools.Add(self.btn_image, flag=wx.ALL, border=10)


        self.imagebox.Add(self.plot2Dimg,proportion=1,flag=wx.ALL|wx.EXPAND, border=10)
        self.imagebox.Add(imagetools, flag=wx.ALL, border=10)

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def onImageTools(self,event=None):

        self.toolbox = ImageToolboxFrame(self.plot2Dimg,self.raw_img)

    def plot2Dimage(self):

        self.plot2Dimg = ImagePanel(self.panel)#,size=(300, 300))
        self.plot2Dimg.messenger = self.write_message

        self.Bind(wx.EVT_PAINT, self.OnPaint)

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

    def ShapeChoice(self,event=None):

        print('The shape you choose: %s' %  self.ch_shp.GetString(self.ch_shp.GetSelection()))

        print()
        print('Not implemented: ShapeChoice')
        self.addAREA()


    def OnPaint(self, event=None):

        print('Shape : %s' %  self.ch_shp.GetString(self.ch_shp.GetSelection()))
#         dc = wx.PaintDC(self)
#         dc.Clear()
#         dc.SetPen(wx.Pen(wx.BLACK, 4))
#         dc.DrawLine(0, 0, 50, 50)

    def clearMask(self,event=None):

        print('Clearing the mask...')
        ## provide a warning message?
        self.area_list = []
        self.slct_area.Set(self.area_list)

        self.btn_SHWarea.Disable()
        self.btn_DELarea.Disable()
        self.btn_clear.Disable()
        self.btn_save.Disable()


    def saveMask(self,event=None):

        print('This will trigger the saving of a mask.')

    def addAREA(self,event=None):
        area_name = 'area %i (%s)' % (len(self.area_list),self.ch_shp.GetString(self.ch_shp.GetSelection()))
        self.area_list.append(area_name)
        self.slct_area.Set(self.area_list)


        if len(self.area_list) > 0:
            self.btn_SHWarea.Enable()
            self.btn_DELarea.Enable()
            self.btn_clear.Enable()
            self.btn_save.Enable()

    def showAREA(self,event=None):

        if len(self.area_list) > 0:
            area_str = self.slct_area.GetString(self.slct_area.GetSelection())
            str_msg = 'Displaying: %s' % area_str
            self.write_message(str_msg,panel=0)

            ## show area on map, image

    def deleteAREA(self,event=None):

        if len(self.area_list) > 0:
            area_str = self.slct_area.GetString(self.slct_area.GetSelection())
            str_msg = 'Deleting: %s' % area_str
            self.write_message(str_msg,panel=0)

            self.area_list.remove(self.slct_area.GetString(self.slct_area.GetSelection()))
            self.slct_area.Set(self.area_list)

        if len(self.area_list) == 0:
            self.btn_SHWarea.Disable()
            self.btn_DELarea.Disable()
            self.btn_clear.Disable()
            self.btn_save.Disable()

# class diFFit_XRDmask(wx.App):
#     def __init__(self):
#         wx.App.__init__(self)
#
#     def run(self):
#         self.MainLoop()
#
#     def createApp(self):
#         frame = MaskToolsPopup(None)
#         frame.Show()
#         self.SetTopWindow(frame)
#
#     def OnInit(self):
#         self.createApp()
#         return True
#
# class DebugViewer(diFFit_XRDmask):
#     def __init__(self, **kws):
#         diFFit_XRDmask.__init__(self, **kws)
#
#     def OnInit(self):
#         #self.Init()
#         self.createApp()
#         #self.ShowInspectionTool()
#         return True
#
# if __name__ == '__main__':
#     diFFit_XRDmask().run()
