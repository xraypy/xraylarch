#!/usr/bin/env python
'''
popup frame for 2D XRD image control

'''
import numpy as np
import matplotlib.cm as colormap
import wx

###################################

class ImageToolboxFrame(wx.Frame):

    def __init__(self,imageframe,image): #,mask=False,bkgd=False):
        '''
        Frame for visual toolbox
        '''
        label = 'Image Toolbox'
        wx.Frame.__init__(self, None, -1,title=label, size=(330, 300))

        #self.SetMinSize((700,500))

        ## Set inputs
        self.plot2Dframe = imageframe
        #self.raw_img = image
        self.plt_img = image

        ## Set defaults
        self.bkgd_scale = 0

        self.color = 'bone'
        self.flip = 'vertical'

        self.Init()
        self.Centre()
        self.Show(True)

    def Init(self):

        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        ###########################
        ## Color
        hbox_clr = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_clr = wx.StaticText(self.panel, label='COLOR')
        colors = []
        for key in colormap.datad:
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
        self.sldr_min = wx.Slider(self.panel, style=wx.SL_LABELS, maxValue=5e6)
        self.entr_min = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)

        self.sldr_min.Bind(wx.EVT_SLIDER,self.onSlider)

        hbox_ct2.Add(self.ttl_min, flag=wx.RIGHT, border=8)
        hbox_ct2.Add(self.sldr_min, flag=wx.EXPAND, border=8)
        hbox_ct2.Add(self.entr_min, flag=wx.RIGHT, border=8)
        vbox_ct.Add(hbox_ct2, flag=wx.BOTTOM, border=8)

        hbox_ct3 = wx.BoxSizer(wx.HORIZONTAL)
        self.ttl_max = wx.StaticText(self.panel, label='max')
        self.sldr_max = wx.Slider(self.panel, style=wx.SL_LABELS, maxValue=5e6)
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
        ## Set defaults
        self.ch_clr.SetStringSelection(self.color)
        self.ch_flp.SetStringSelection(self.flip)
        self.setSlider()

        self.panel.SetSizer(vbox)

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

        self.minCURRENT = newMIN
        self.maxCURRENT = newMAX

        self.sldr_min.SetRange(newMIN,newMAX)
        self.sldr_max.SetRange(newMIN,newMAX)

        self.setContrast()

    def setSlider(self):

        self.minCURRENT = self.plot2Dframe.conf.int_lo[0]
        self.maxCURRENT = self.plot2Dframe.conf.int_hi[0]
#         self.minCURRENT = self.plot2Dframe.conf.int_lo['int']
#         self.maxCURRENT = self.plot2Dframe.conf.int_hi['int']

        self.entr_min.SetLabel(str(self.minCURRENT))
        self.entr_max.SetLabel(str(self.maxCURRENT))

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

        try:
            self.sldr_min.SetValue(self.minCURRENT)
            self.sldr_max.SetValue(self.maxCURRENT)
        except:
            pass

    def onSlider(self,event=None):

        self.minCURRENT = self.sldr_min.GetValue()
        self.maxCURRENT = self.sldr_max.GetValue()

        ## Create safety to keep min. below max.
        ## mkak 2016.10.20

        self.setContrast()

    def setContrast(self):

        self.sldr_min.SetValue(self.minCURRENT)
        self.sldr_max.SetValue(self.maxCURRENT)

        self.plot2Dframe.conf.auto_intensity = False
        self.plot2Dframe.conf.int_lo[0] = self.minCURRENT
        self.plot2Dframe.conf.int_hi[0] = self.maxCURRENT
#         self.plot2Dframe.conf.int_lo['int'] = self.minCURRENT
#         self.plot2Dframe.conf.int_hi['int'] = self.maxCURRENT

        self.plot2Dframe.redraw()

        self.entr_min.SetLabel(str(self.minCURRENT))
        self.entr_max.SetLabel(str(self.maxCURRENT))

    def onFlip(self,event=None):
        '''
        Eventually, should just set self.raw_img or self.fli_img - better than this
        mkak 2016.10.20
        '''

        if self.ch_flp.GetString(self.ch_flp.GetSelection()) != self.flip:
            self.flip = self.ch_flp.GetString(self.ch_flp.GetSelection())

            self.checkFLIPS()

            self.plot2Dframe.redraw()

    def checkFLIPS(self):

        if self.flip == 'vertical': # Vertical
            self.plot2Dframe.conf.flip_ud = True
            self.plot2Dframe.conf.flip_lr = False
        elif self.flip == 'horizontal': # Horizontal
            self.plot2Dframe.conf.flip_ud = False
            self.plot2Dframe.conf.flip_lr = True
        elif self.flip == 'both': # both
            self.plot2Dframe.conf.flip_ud = True
            self.plot2Dframe.conf.flip_lr = True
        else: # None
            self.plot2Dframe.conf.flip_ud = False
            self.plot2Dframe.conf.flip_lr = False

    def onScale(self,event=None):
        if self.ch_scl.GetSelection() == 1: ## log
            self.plot2Dframe.conf.log_scale = True
        else:  ## linear
            self.plot2Dframe.conf.log_scale = False
        self.plot2Dframe.redraw()

    def onColor(self,event=None):
        if self.color != self.ch_clr.GetString(self.ch_clr.GetSelection()):
            self.color = self.ch_clr.GetString(self.ch_clr.GetSelection())
            self.setColor()

    def setColor(self):
        self.plot2Dframe.conf.cmap[0] = getattr(colormap, self.color)
#         self.plot2Dframe.conf.cmap['int'] = getattr(colormap, self.color)
        self.plot2Dframe.display(self.plt_img)
        self.checkFLIPS()
        self.plot2Dframe.redraw()


    def SetContrast(self):

        self.txt_ct2.SetLabel('[ full range: %i, %i ]' %
                  (np.min(self.plt_img),np.max(self.plt_img)))

        self.autoContrast()
        self.checkFLIPS()

        self.plot2Dframe.redraw()

#############################################################
################    IN PROGRESS - START   ###################
#############################################################

# class ImageToolboxPanel(wx.Panel):
#
#     def __init__(self,parent):#,imageframe,image,mask=False,bkgd=False):
#         '''
#         Panel for visual toolbox
#         '''
#         label = 'Image Toolbox'
#         wx.Panel.__init__(self, parent, -1)
#         #wx.Panel.__init__(self, None, -1)
#         #wx.Panel.__init__(self, parent, -1, **kws)
#
#         #self.SetMinSize((700,500))
#
#         self.plot2Dframe = None
#         self.raw_img = None
#         self.mask = False
#         self.bkgd = False
#
#         self.Init()
#
#     def Init(self):
#
#         self.panel = wx.Panel(self)
#         vbox = wx.BoxSizer(wx.VERTICAL)
#
#
# #############################################################
# ################     IN PROGRESS - END    ###################
# #############################################################
