#!/usr/bin/env pythonw
'''
GUI for displaying 2D XRD images

'''
import os
import numpy as np

import matplotlib.cm as colormap
from functools import partial

import h5py

import wx
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception

from wxmplot import PlotPanel
from wxmplot.imagepanel import ImagePanel
from wxutils import MenuItem
from wxmplot.imageconf import ImageConfig,ColorMap_List

# import matplotlib.pyplot as plt

import larch
from larch import Group
from larch.larchlib import read_workdir, save_workdir
from larch.utils.strutils import bytes2str
from larch.wxlib import LarchWxApp
from larch.io import tifffile, nativepath
from larch.xrd import (integrate_xrd,E_from_lambda,xrd1d,read_lambda,
                       calc_cake,twth_from_q,twth_from_d,
                       return_ai,twth_from_xy,q_from_xy,eta_from_xy)
from .XRDCalibrationFrame import CalibrationPopup
from .XRDMaskFrame import MaskToolsPopup
from .XRD1Dviewer import Calc1DPopup

###################################

VERSION = '2 (14-March-2018)'
SLIDER_SCALE = 1000. ## sliders step in unit 1. this scales to 0.001
PIXELS = 1024 #2048

QSTPS = 5000

XLABEL = ['q','2th','d']
XUNIT  = [u'q (\u212B\u207B\u00B9)',u'2\u03B8 (\u00B0)',u'd (\u212B)']

###################################

class diFFit2DPanel(wx.Panel):
    '''
    Panel for housing 2D XRD Image
    '''
    label='2D XRD'
    def __init__(self,parent,type='2D image',owner=None,_larch=None,size=(500, 500)):

        wx.Panel.__init__(self, parent)
        self.owner = owner
        self.type  = type
        self.ai    = None
        self.on_calibration()

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.plot2D = ImagePanel(self,size=size,messenger=self.owner.write_message)
        vbox.Add(self.plot2D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        self.SetSizer(vbox)

        self.plot2D.cursor_callback = self.on_cursor


    def on_calibration(self):

        if self.owner.calfile is not None and os.path.exists(self.owner.calfile):
            self.ai = return_ai(self.owner.calfile)

            self.ai.detector.shape = np.shape(self.owner.plt_img)

            fit2d_param = self.ai.getFit2D()
            self.center = (fit2d_param['centerX'],fit2d_param['centerY'])

    def on_cursor(self,x=None, y=None, **kw):

        if self.ai is not None:
            if self.type == 'cake':
                self.owner.twth = self.plot2D.xdata[int(x)]

                self.owner.xrd2Dcake.plot_line(x=x)
                self.owner.xrd2Dviewer.plot_ring()
            else:
                self.owner.twth = twth_from_xy(x,y,ai=self.ai)

                self.owner.xrd2Dviewer.plot_ring(x=x,y=y)
                self.owner.xrd2Dcake.plot_line()
        else:
            return

        self.owner.xrd1Dviewer.plot_line()

    def plot_line(self,x=None):

        if x is None: x = np.abs(self.plot2D.xdata-self.owner.twth).argmin()

        try:
            self.xrd_line.remove()
        except:
            pass

        self.xrd_line = self.plot2D.axes.axvline(x=x, color='r', linewidth=1)
        self.plot2D.canvas.draw()

    def plot_ring(self,x=None,y=None):
        import matplotlib.pyplot as plt
        if x is not None and y is not None:
            radius = np.sqrt((x-self.center[0])**2+(y-self.center[1])**2)
        else:
            radius = self.ai._dist * np.tan(np.radians(self.owner.twth))
            radius = radius / self.ai.detector.pixel1
        xrd_ring = plt.Circle(self.center, radius, color='red', fill=False)

        try:
            self.xrd_ring.remove()
        except:
            pass

        self.xrd_ring = self.plot2D.axes.add_artist(xrd_ring)
        self.plot2D.canvas.draw()

class diFFit1DPanel(wx.Panel):
    '''
    Panel for housing 1D XRD
    '''
    def __init__(self,parent,owner=None,_larch=None,size=(500, 100)):

        wx.Panel.__init__(self, parent)
        self.owner = owner

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.plot1D = PlotPanel(self,size=size,messenger=self.owner.write_message)
        vbox.Add(self.plot1D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        self.SetSizer(vbox)

        self.plot1D.cursor_callback = self.on_cursor

    def on_cursor(self,x=None, y=None, **kw):

        xi = self.owner.xaxis_type.GetSelection()
        if xi == 1:
            self.owner.twth = x
        else:
            ix = np.abs(self.owner.data1dxrd[1]-self.owner.twth).argmin()
            self.owner.twth = self.owner.data1dxrd[1][ix]

        self.owner.xrd1Dviewer.plot_line(x=x)
        self.owner.xrd2Dviewer.plot_ring()
        self.owner.xrd2Dcake.plot_line()

    def plot_line(self,x=None):

        if x is None:
            xi = self.owner.xaxis_type.GetSelection()
            if xi != 1:
                ix = np.abs(self.owner.data1dxrd[1]-self.owner.twth).argmin()
                x = self.owner.data1dxrd[xi][ix]
            else:
                x = self.owner.twth

        try:
            self.xrd_line.remove()
        except:
            pass

        self.xrd_line = self.plot1D.axes.axvline(x=x, color='r', linewidth=1)
        self.plot1D.draw()



class XRD2DViewerFrame(wx.Frame):
    '''
    Frame for housing all 2D XRD viewer widgets
    '''
    def __init__(self, _larch=None, xrd1Dviewer=None, ponifile=None, flip='vertical',
                 *args, **kw):

        screenSize = wx.DisplaySize()
        x,y = 1000,720 #1000,760
        if x > screenSize[0] * 0.9:
            x = int(screenSize[0] * 0.9)
            y = int(x*0.6)

        label = 'diFFit : 2D XRD Data Analysis Software'
        wx.Frame.__init__(self, None,title=label, size=(x,y))

        self.SetMinSize((700,500))

        self.statusbar = self.CreateStatusBar(3,wx.CAPTION)

        self.open_image = []
        self.open_scale = []

        ## Default image information
        self.raw_img = np.zeros((PIXELS,PIXELS))
        self.flp_img = np.zeros((PIXELS,PIXELS))
        self.plt_img = np.zeros((PIXELS,PIXELS))
        self.cake    = None
        self.twth    = None

        self.calfile = ponifile

        self.msk_img  = np.ones((PIXELS,PIXELS))
        self.bkgd_img = np.zeros((PIXELS,PIXELS))

        self.bkgd_scale = 0
        self.bkgdMAX = 2

        self.use_mask = False
        self.use_bkgd = False

        self.xrddisplay1D = xrd1Dviewer

        self.xrd1Dviewer = None
        self.xrd2Dcake  = None

        self.color = 'bone'
        self.flip = flip

        read_workdir('gsemap.dat')

        self.XRD2DMenuBar()
        self.Panel2DViewer()

        self.Centre()
        self.Show()

        if ponifile is None:
            self.btn_integ.Disable()
        else:
            self.btn_integ.Enable()

    def write_message(self, s, panel=0):
        '''write a message to the Status Bar'''
        self.SetStatusText(s, panel)

    def optionsON(self):

        if len(self.open_image) > 0:

            self.ch_clr.Enable()
            self.sldr_cntrst.Enable()
            self.entr_min.Enable()
            self.entr_max.Enable()
            self.btn_ct1.Enable()
            self.ch_flp.Enable()
            self.ch_scl.Enable()
            self.btn_mask.Enable()
            self.btn_bkgd.Enable()

            img_no = self.ch_img.GetSelection()
            if self.open_image[img_no].iframes > 1:
                self.hrz_frm_sldr.Enable()
                self.hrz_frm_sldr.SetRange(0,(self.open_image[img_no].iframes-1))
                self.hrz_frm_sldr.SetValue(self.open_image[img_no].i)
                for btn in self.hrz_frm_btn: btn.Enable()
            else:
                self.hrz_frm_sldr.Disable()
                self.hrz_frm_sldr.SetRange(0,0)
                self.hrz_frm_sldr.SetValue(0)
                for btn in self.hrz_frm_btn: btn.Disable()

            if self.open_image[img_no].jframes > 1:
                self.vrt_frm_sldr.Enable()
                self.vrt_frm_sldr.SetRange(0,(self.open_image[img_no].jframes-1))
                self.vrt_frm_sldr.SetValue(self.open_image[img_no].j)
                for btn in self.vrt_frm_btn: btn.Enable()
            else:
                self.vrt_frm_sldr.Disable()
                self.vrt_frm_sldr.SetRange(0,0)
                self.vrt_frm_sldr.SetValue(0)
                for btn in self.vrt_frm_btn: btn.Disable()

##############################################
#### OPENING AND DISPLAYING IMAGES

    def loadIMAGE(self,event=None):
        wildcards = '2DXRD image files (*.*)|*.*|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose 2D XRD image',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = '', False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()

        if read:
            print('\nReading XRD image file: %s' % path)

            image,xrmfile = None,None
            try:
                xrmfile = h5py.File(path, 'r')
            except IOError:
                try:
                    from larch.io import read_xrd_netcdf
                    image = read_xrd_netcdf(path)
                except TypeError:
                    try:
                        image = tifffile.imread(path)
                    except ValueError:
                        print('Could not read file.')
                        return

            iname = os.path.split(path)[-1]
            self.plot2Dxrd(iname, image, path=path, h5file=xrmfile)

    def close2Dxrd(self,event=None):

        img_no = self.ch_img.GetSelection()
        try:
            print('Closing XRD image file: %s' % self.open_image[img_no].path)
            try:
                self.open_image[img_no].h5file.close()
            except:
                pass
            del self.open_image[img_no]
        except:
            pass

        self.ch_img.Set([image.label for image in self.open_image])
        if len(self.open_image) > 0:
            self.ch_img.SetSelection(0)
            self.selectIMAGE()
        else:
            self.clearIMAGE()


    def plot2Dxrd(self,iname,image,path='',h5file=None):

        self.write_message('Displaying image: %s' % iname, panel=0)

        try:
            new_img = XRDImg(label=iname, path=path, image=image, h5file=h5file)
        except:
            fail_msg = 'Image failed to load.'
            self.write_message(fail_msg, panel=0)
            print (fail_msg)
            return

        self.open_image.append(new_img)

        if self.open_image[-1].calfile is not None:
            if os.path.exists(self.open_image[-1].calfile):
                self.calfile = self.open_image[-1].calfile
                self.xrd2Dviewer.on_calibration()


        self.ch_img.Set([image.label for image in self.open_image])
        self.ch_img.SetStringSelection(iname)

        self.raw_img = self.open_image[-1].get_image()
        self.twth = None
        self.displayIMAGE(auto_contrast=True,unzoom=True)

        if self.open_image[-1].iframes > 1:
            self.hrz_frm_sldr.SetRange(0,(self.open_image[-1].iframes-1))
            self.hrz_frm_sldr.SetValue(self.open_image[-1].i)
        else:
            self.hrz_frm_sldr.Disable()
            for btn in self.hrz_frm_btn: btn.Disable()

        if self.open_image[-1].jframes > 1:
            self.vrt_frm_sldr.SetRange(0,(self.open_image[-1].jframes-1))
            self.vrt_frm_sldr.SetValue(self.open_image[-1].j)
        else:
            self.vrt_frm_sldr.Disable()
            for btn in self.vrt_frm_btn: btn.Disable()


    def changeFRAME(self,flag='hslider',event=None):

        img_no = self.ch_img.GetSelection()
        if self.open_image[img_no].iframes > 1 or self.open_image[img_no].jframes > 1:
            i,j = self.open_image[img_no].i,self.open_image[img_no].j
            if   flag=='next':     i = i + 1
            elif flag=='previous': i = i - 1
            elif flag=='hslider':  i = self.hrz_frm_sldr.GetValue()
            elif flag=='up':       j = j + 1
            elif flag=='down':     j = j - 1
            elif flag=='vslider':  j = self.vrt_frm_sldr.GetValue()

            if i < 0: i = self.open_image[img_no].iframes + i
            if j < 0: j = self.open_image[img_no].jframes + j
            if i > self.open_image[img_no].iframes: i = i - self.open_image[img_no].iframes
            if j > self.open_image[img_no].jframes: j = j - self.open_image[img_no].jframes

            self.raw_img =  self.open_image[img_no].get_image(i=i,j=j)

            self.hrz_frm_sldr.SetValue(i)
            self.vrt_frm_sldr.SetValue(j)
            self.displayIMAGE(auto_contrast=False,unzoom=False)#unzoom=True)

    def clearIMAGE(self):

        try:
            self.xrd2Dviewer.plot2D.clear()
            self.xrd2Dviewer.plot2D.redraw()
        except:
            pass

    def displayIMAGE(self,auto_contrast=True,unzoom=False):

        self.flipIMAGE()
        self.checkIMAGE()
        self.calcIMAGE()

        if unzoom:
            self.xrd2Dviewer.plot2D.display(self.plt_img,unzoom=unzoom)
        else:
            self.xrd2Dviewer.plot2D.conf.data = self.plt_img
            self.xrd2Dviewer.plot2D.redraw()
        self.display1DXRD()

        if auto_contrast: self.setContrast(auto_contrast=True)

        self.txt_ct2.SetLabel('[ image range: %i to %i ]' %
                         (np.min(self.plt_img),np.max(self.plt_img)))

        self.optionsON()
        self.xrd2Dviewer.plot2D.redraw()

    def redrawIMAGE(self,unzoom=False):

        self.flipIMAGE()
        self.checkIMAGE()
        self.calcIMAGE()
        self.colorIMAGE()

        self.xrd2Dviewer.plot2D.redraw()
        self.display1DXRD()

    def selectIMAGE(self,event=None):

        img_no = self.ch_img.GetSelection()
        self.raw_img = self.open_image[img_no].get_image()

        self.write_message('Displaying image: %s' % self.open_image[img_no].label, panel=0)
        try:
            self.displayIMAGE(auto_contrast=False,unzoom=True)
            self.setContrast()
        except:
            self.write_message('Image failed to load.', panel=0)

    def onChangeXscale(self,event=None):

        xi = self.xaxis_type.GetSelection()

        self.xrd1Dviewer.plot1D.update_line(0, self.data1dxrd[xi],self.data1dxrd[3])
        if self.twth is not None: self.xrd1Dviewer.plot_line()
        self.xrd1Dviewer.plot1D.set_viewlimits()
        self.xrd1Dviewer.plot1D.set_xlabel(XUNIT[xi])
        if xi == 2: self.xrd1Dviewer.plot1D.axes.set_xlim(np.min(self.data1dxrd[xi]), 6)
        self.xrd1Dviewer.plot1D.draw()


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
            self.sldr_bkgd.Disable()
            self.use_bkgd = False
        else:
            self.sldr_bkgd.Enable()
            self.use_bkgd = True

        self.sldr_bkgd.SetRange(0,self.bkgdMAX*SLIDER_SCALE)
        self.sldr_bkgd.SetValue(self.bkgd_scale*SLIDER_SCALE)

    def colorIMAGE(self,unzoom=False):
        self.xrd2Dviewer.plot2D.conf.cmap[0] = getattr(colormap, self.color)
        self.xrd2Dviewer.plot2D.display(self.plt_img) #,unzoom=unzoom)

        if self.cake is not None:
            self.xrd2Dcake.plot2D.conf.cmap[0] = getattr(colormap, self.color)
            self.xrd2Dcake.plot2D.display(self.cake[0]) #,unzoom=unzoom)

    def setCOLOR(self,event=None):
        if self.color != self.ch_clr.GetString(self.ch_clr.GetSelection()):
            self.color = self.ch_clr.GetString(self.ch_clr.GetSelection())
            self.colorIMAGE()

    def setFLIP(self,event=None):

        if self.flip != self.ch_flp.GetString(self.ch_flp.GetSelection()):
            self.flip = self.ch_flp.GetString(self.ch_flp.GetSelection())
            self.redrawIMAGE(unzoom=False)

    def setZSCALE(self,event=None):
        if self.ch_scl.GetSelection() == 1: ## log
            self.xrd2Dviewer.plot2D.conf.log_scale = True
            if self.xrd2Dcake is not None:
                self.xrd2Dcake.plot2D.conf.log_scale = True
            if self.xrd1Dviewer is not None:
                self.xrd1Dviewer.plot1D.axes.set_yscale('log')
                self.xrd1Dviewer.plot1D.set_viewlimits()
                self.xrd1Dviewer.plot1D.draw()
        else:  ## linear
            self.xrd2Dviewer.plot2D.conf.log_scale = False
            if self.xrd2Dcake is not None:
                self.xrd2Dcake.plot2D.conf.log_scale = False
            if self.xrd1Dviewer is not None:
                self.xrd1Dviewer.plot1D.axes.set_yscale('linear')
                self.xrd1Dviewer.plot1D.set_viewlimits()
                self.xrd1Dviewer.plot1D.draw()

        self.xrd2Dviewer.plot2D.redraw()
        if self.cake is not None:
            self.xrd2Dcake.plot2D.redraw()


##############################################
#### BACKGROUND FUNCTIONS
    def onBkgdScale(self,event=None):
        self.bkgd_scale = self.sldr_bkgd.GetValue()/SLIDER_SCALE
        self.redrawIMAGE(unzoom=False)

##############################################
#### IMAGE CONTRAST FUNCTIONS

    def onContrastRange(self,event=None):

        img_no = self.ch_img.GetSelection()
        img = self.open_image[img_no]

        img.minval = int(self.entr_min.GetValue())
        img.maxval = int(self.entr_max.GetValue())

        self.setContrast()


    def onSlider(self,event=None):

        img_no = self.ch_img.GetSelection()
        img = self.open_image[img_no]

        curval = int(self.sldr_cntrst.GetValue())

        self.xrd2Dviewer.plot2D.conf.auto_intensity = False
        self.xrd2Dviewer.plot2D.conf.int_lo[0] = img.minval
        self.xrd2Dviewer.plot2D.conf.int_hi[0] = curval
        self.xrd2Dviewer.plot2D.redraw()

        if self.cake is not None:
            self.xrd2Dcake.plot2D.conf.auto_intensity = False
            self.xrd2Dcake.plot2D.conf.int_lo[0] = img.minval
            self.xrd2Dcake.plot2D.conf.int_hi[0] = curval
            self.xrd2Dcake.plot2D.redraw()

    def setContrast(self,event=None,auto_contrast=False):
        img_no = self.ch_img.GetSelection()
        img = self.open_image[img_no]

        if auto_contrast: img.set_contrast(np.min(self.plt_img),np.max(self.plt_img))

        self.xrd2Dviewer.plot2D.conf.auto_intensity = False
        self.xrd2Dviewer.plot2D.conf.int_lo[0] = img.minval
        if auto_contrast:
            self.xrd2Dviewer.plot2D.conf.int_hi[0] = img.maxval*0.4
        else:
            self.xrd2Dviewer.plot2D.conf.int_hi[0] = img.maxval
        self.xrd2Dviewer.plot2D.redraw()

        self.sldr_cntrst.SetRange(img.minval,img.maxval)
        if auto_contrast:
            self.sldr_cntrst.SetValue(int(img.maxval*0.4))
        else:
            self.sldr_cntrst.SetValue(img.maxval)
        self.entr_min.SetValue('%i' % img.minval)
        self.entr_max.SetValue('%i' % img.maxval)

        if self.cake is not None:
            self.xrd2Dcake.plot2D.conf.auto_intensity = False
            self.xrd2Dcake.plot2D.conf.int_lo[0] = img.minval
            if auto_contrast:
                self.xrd2Dcake.plot2D.conf.int_hi[0] = img.maxval*0.4
            else:
                self.xrd2Dcake.plot2D.conf.int_hi[0] = img.maxval
            self.xrd2Dcake.plot2D.redraw()


##############################################
#### XRD MANIPULATION FUNTIONS

    def saveIMAGE(self,event=None,raw=False):
        wildcards = 'XRD image (*.tiff)|*.tiff|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, 'Save image as...',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards,
                           style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

        path, save = None, False
        if dlg.ShowModal() == wx.ID_OK:
            save = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()

        if save:
            if raw:
                tifffile.imsave(path,self.raw_img)
            else:
                tifffile.imsave(path,self.plt_img)

    def on1DXRD(self,event=None):

        read, save, plot = False, False, False
        if self.calfile is not None and self.plt_img is not None:
            myDlg = Calc1DPopup(self,self.plt_img)
            if myDlg.ShowModal() == wx.ID_OK:
                read = True
                save = myDlg.ch_save.GetValue()
                plot = myDlg.ch_plot.GetValue()
                unts = myDlg.save_choice.GetSelection()
                wdgs = myDlg.wedges.GetValue()
                if int(myDlg.xstep.GetValue()) < 1:
                    attrs = {'steps':5001}
                else:
                    attrs = {'steps':int(myDlg.xstep.GetValue())}
                unit = '2th' if unts == 1 else 'q'
                attrs.update({'unit':unit,'verbose':True})
            myDlg.Destroy()
        else:
            print('Data and calibration files must be available for this function.')
            return

        if read:
            if save:
                wildcards = '1D XRD file (*.xy)|*.xy|All files (*.*)|*.*'
                dlg = wx.FileDialog(self, 'Save file as...',
                                   defaultDir=os.getcwd(),
                                   wildcard=wildcards,
                                   style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
                if dlg.ShowModal() == wx.ID_OK:
                    filename = dlg.GetPath().replace('\\', '/')
                    if not filename.endswith('.xy'):
                        filename = '%s.xy' % filename
                    attrs.update({'file':filename})

                dlg.Destroy()
            data1D = integrate_xrd(self.plt_img,self.calfile,**attrs)
            if wdgs > 1:
                xrdq_wdg,xrd1d_wdg,lmts_wdg = [],[],[]
                wdg_sz = 360./int(wdgs)
                for iwdg in range(wdgs):
                    wdg_lmts = np.array([iwdg*wdg_sz, (iwdg+1)*wdg_sz]) - 180
                    attrs.update({'wedge_limits':wdg_lmts})

                    if save:
                        wedgename = '%s_%i_to_%ideg.xy' % (filename.split('.xy')[0],
                                                           (wdg_lmts[0]+180),
                                                           (wdg_lmts[1]+180))
                        attrs.update({'file':wedgename})
                    q,counts = integrate_xrd(self.plt_img,self.calfile,**attrs)
                    xrdq_wdg  += [q]
                    xrd1d_wdg += [counts]
                    lmts_wdg  += [wdg_lmts]


            if plot:
                if self.xrddisplay1D is None:
                    self.xrddisplay1D = diFFit1DFrame()

                kwargs = {}
                wvlngth = read_lambda(self.calfile)
                kwargs.update({'wavelength':wvlngth,'energy':E_from_lambda(wvlngth)})
                kwargs.update({'label':self.open_image[self.ch_img.GetSelection()].label})
                data1dxrd = xrd1d(**kwargs)
                data1dxrd.xrd_from_2d(data1D,attrs['unit'])

                try:
                    self.xrddisplay1D.xrd1Dviewer.add1Ddata(data1dxrd)
                except PyDeadObjectError:
                    self.xrddisplay1D = diFFit1DFrame()
                    self.xrddisplay1D.xrd1Dviewer.add1Ddata(data1dxrd)

                if wdgs > 1:
                    for lmts,q,cnts in zip(lmts_wdg,xrdq_wdg,xrd1d_wdg):
                        label = '%s (%i to %i deg)' % (self.open_image[self.ch_img.GetSelection()].label,
                                                        (lmts[0]+180), (lmts[1]+180))
                        kwargs.update({'label':label})
                        data1dxrd = xrd1d(**kwargs)
                        data1dxrd.xrd_from_2d([q,cnts],'q')
                        self.xrddisplay1D.xrd1Dviewer.add1Ddata(data1dxrd)
                self.xrddisplay1D.Show()




##############################################
#### CALIBRATION FUNCTIONS
    def display1DXRD(self,event=None):

        if len(self.open_image) > 0 and self.calfile is not None:

            if self.xrd2Dcake is None or self.xrd1Dviewer is None:
                rightside = self.RightSidePanel(self.panel)
                self.panel2D.Add(rightside,proportion=1,flag=wx.EXPAND|wx.ALL,border=10)
                self.panel2D.Layout()
                self.Fit()
                self.SetSize((1400,720))

                tools1dxrd = self.ToolBox_1DXRD(self.panel)
                self.leftside.Add(tools1dxrd,flag=wx.ALL|wx.EXPAND,border=10)
                self.leftside.Layout()

                self.panel2D.Layout()
                self.Fit()
                self.SetSize((1400,720))

            self.btn_integ.Enable()

            ## Cake calculations
            xi = 1
            self.xaxis_type.SetSelection(xi)

            self.cake = calc_cake(self.plt_img, self.calfile, unit=XLABEL[xi], xsteps=QSTPS, ysteps=QSTPS)
            self.xrd2Dcake.plot2D.display(self.cake[0],x=self.cake[1],y=self.cake[2],
                                          xlabel=XLABEL[xi],ylabel='eta')
            self.xrd2Dcake.plot2D.conf.auto_intensity = False
            self.xrd2Dcake.plot2D.conf.int_lo[0] = self.xrd2Dviewer.plot2D.conf.int_lo[0]
            self.xrd2Dcake.plot2D.conf.int_hi[0] = self.xrd2Dviewer.plot2D.conf.int_hi[0]
            self.xrd2Dcake.plot2D.redraw()

            ## 1DXRD calculations

            q,I = integrate_xrd(self.plt_img, self.calfile, unit=XLABEL[xi], steps=QSTPS)
            self.data1dxrd = xrd1d(x=q,xtype=XLABEL[xi],I=I).all_data()

            self.xrd1Dviewer.plot1D.plot(self.data1dxrd[xi],self.data1dxrd[3],color='blue',
                                         xlabel=XUNIT[xi])
            self.xrd1Dviewer.plot1D.axes.yaxis.set_visible(False)
            self.xrd1Dviewer.plot1D.axes.spines['left'].set_visible(False)
            self.xrd1Dviewer.plot1D.axes.spines['right'].set_visible(False)
            self.xrd1Dviewer.plot1D.axes.spines['top'].set_visible(False)
            self.xrd1Dviewer.plot1D.draw()


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
            print('Loading calibration file:\n\t%s' % path)
            self.calfile = path
            self.xrd2Dviewer.on_calibration()
            self.display1DXRD()


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
                print('Reading background:\n\t%s' % path)
            except:
                print('\nCannot read as an image file: %s\n' % path)
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
                print('Reading mask:\n\t%s' % path)
            except:
                print('\nCannot read as mask file: %s\n' % path)
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
        self.redrawIMAGE(unzoom=False)

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
#### MENU FUNCTIONS
    def onFolderSelect(self, evt=None):
        style = wx.DD_DIR_MUST_EXIST|wx.DD_DEFAULT_STYLE
        dlg = wx.DirDialog(self, 'Select Working Directory:', os.getcwd(),
                           style=style)

        if dlg.ShowModal() == wx.ID_OK:
            basedir = os.path.abspath(str(dlg.GetPath()))
            try:
                if len(basedir)  > 0:
                    os.chdir(nativepath(basedir))
                    save_workdir(nativepath(basedir))
            except OSError:
                print( 'Changed folder failed')
                pass
        save_workdir('gsemap.dat')
        dlg.Destroy()

    def onExit(self, event=None):

        dlg = wx.MessageDialog(None, 'Really Quit?', 'Question',
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)

        ret = dlg.ShowModal()
        if ret != wx.ID_YES:
            return

        for image in self.open_image:
            try:
                image.h5file.close()
            except:
                pass

        try:
            self.Destroy()
        except:
            pass

##############################################
#### PANEL DEFINITIONS
    def XRD2DMenuBar(self):

        menubar = wx.MenuBar()

        ###########################
        ## diFFit2D
        diFFitMenu = wx.Menu()

        MenuItem(self, diFFitMenu, '&Open diffration image', '', self.loadIMAGE)
        MenuItem(self, diFFitMenu, 'Sa&ve displayed image to file', '', partial(self.saveIMAGE,raw=False))
        MenuItem(self, diFFitMenu, 'Save r&aw image to file', '', partial(self.saveIMAGE,raw=True))
        MenuItem(self, diFFitMenu, 'Change larch &working folder', '', self.onFolderSelect)

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
        ProcessMenu.AppendSeparator()
        MenuItem(self, ProcessMenu, 'Close current image', '', self.close2Dxrd)

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

        imgbox   = self.ImageBox(self.panel)
        vistools = self.Toolbox(self.panel)

        vbox.Add(imgbox,flag=wx.ALL|wx.EXPAND,border=10)
        vbox.Add(vistools,flag=wx.ALL|wx.EXPAND,border=10)

        return vbox

    def Panel2DViewer(self):
        '''
        Frame for housing all 2D XRD viewer widgets
        '''
        self.panel = wx.Panel(self)

        self.leftside = self.LeftSidePanel(self.panel)
        center = self.CenterPanel(self.panel)
        #rightside = self.RightSidePanel(self.panel)

        self.panel2D = wx.BoxSizer(wx.HORIZONTAL)
        self.panel2D.Add(self.leftside,flag=wx.ALL,border=10)
        self.panel2D.Add(center,proportion=1,flag=wx.EXPAND|wx.ALL,border=10)
        #self.panel2D.Add(rightside,proportion=1,flag=wx.EXPAND|wx.ALL,border=10)

        self.panel.SetSizer(self.panel2D)


    def ToolBox_1DXRD(self,panel):

        tlbx = wx.StaticBox(self.panel,label='1DXRD TOOLBOX')
        hbox = wx.StaticBoxSizer(tlbx,wx.HORIZONTAL)

        ttl_xaxis = wx.StaticText(self, label='X-SCALE')
        xunits = [u'q (\u212B\u207B\u00B9)',u'2\u03B8 (\u00B0)',u'd (\u212B)']

        self.xaxis_type = wx.Choice(self,choices=xunits)
        self.xaxis_type.Bind(wx.EVT_CHOICE, self.onChangeXscale)

        hbox.Add(ttl_xaxis, flag=wx.RIGHT, border=8)
        hbox.Add(self.xaxis_type, flag=wx.EXPAND, border=8)

        return hbox

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

        self.hrz_frm_sldr = wx.Slider(self.panel, minValue=0, maxValue=100, size=(120,-1),
                                 style = wx.SL_HORIZONTAL|wx.SL_LABELS)
        self.vrt_frm_sldr = wx.Slider(self.panel, minValue=0, maxValue=100, size=(-1,120),
                                 style = wx.SL_VERTICAL|wx.SL_LABELS|wx.SL_INVERSE)

        self.vrt_frm_btn = [ wx.Button(self.panel,label=u'\u2191', size=(40, -1)),
                             wx.Button(self.panel,label=u'\u2193', size=(40, -1))]
        self.hrz_frm_btn = [ wx.Button(self.panel,label=u'\u2190', size=(40, -1)),
                             wx.Button(self.panel,label=u'\u2192', size=(40, -1))]

        self.hrz_frm_btn[0].Bind(wx.EVT_BUTTON, partial(self.changeFRAME,'previous') )
        self.hrz_frm_btn[1].Bind(wx.EVT_BUTTON, partial(self.changeFRAME,'next')     )
        self.hrz_frm_sldr.Bind(wx.EVT_SLIDER,    partial(self.changeFRAME,'hslider')   )

        self.vrt_frm_btn[0].Bind(wx.EVT_BUTTON, partial(self.changeFRAME,'up') )
        self.vrt_frm_btn[1].Bind(wx.EVT_BUTTON, partial(self.changeFRAME,'down')     )
        self.vrt_frm_sldr.Bind(wx.EVT_SLIDER,    partial(self.changeFRAME,'vslider')   )

        aszr = wx.BoxSizer(wx.HORIZONTAL)
        bszr = wx.BoxSizer(wx.VERTICAL)
        cszr = wx.BoxSizer(wx.VERTICAL)
        dszr = wx.BoxSizer(wx.HORIZONTAL)

        aszr.Add(self.hrz_frm_btn[0],  flag=wx.RIGHT|wx.CENTER,  border=18)
        aszr.Add(self.hrz_frm_btn[1],  flag=wx.LEFT|wx.CENTER,   border=18)

        bszr.Add(self.vrt_frm_btn[0],  flag=wx.BOTTOM|wx.CENTER,    border=8)
        bszr.Add(aszr,             flag=wx.CENTER,              border=8)
        bszr.Add(self.vrt_frm_btn[1],  flag=wx.TOP|wx.CENTER,       border=8)

        cszr.Add(bszr,             flag=wx.CENTER,    border=6)
        cszr.Add(self.hrz_frm_sldr,  flag=wx.CENTER,    border=6)

        dszr.AddSpacer(50)
        dszr.Add(cszr,             flag=wx.CENTER,    border=6)
        dszr.Add(self.vrt_frm_sldr,  flag=wx.CENTER,    border=6)



        vbox.Add(dszr, flag=wx.EXPAND|wx.CENTER|wx.ALL, border=8)

        return vbox


    def Toolbox(self,panel):
        '''
        Frame for visual toolbox
        '''

        tlbx = wx.StaticBox(self.panel,label='2DXRD TOOLBOX')#, size=(200, 200))
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
        #self.ch_clr = wx.Choice(self.panel,choices=ColorMap_List)

        self.ch_clr.Bind(wx.EVT_CHOICE,self.setCOLOR)

        hbox_clr.Add(self.txt_clr, flag=wx.RIGHT,  border=6)
        hbox_clr.Add(self.ch_clr,  flag=wx.RIGHT,  border=6)
        vbox.Add(hbox_clr,         flag=wx.ALL,    border=4)

        ###########################
        ## Contrast
        vbox_ct = wx.BoxSizer(wx.VERTICAL)

        hbox_ct1 = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_ct1 = wx.StaticText(self.panel, label='CONTRAST')
        self.txt_ct2 = wx.StaticText(self.panel, label='',   size=(175,-1))

        hbox_ct1.Add(self.txt_ct1, flag=wx.RIGHT,         border=6)
        hbox_ct1.Add(self.txt_ct2, flag=wx.RIGHT,         border=6)
        vbox_ct.Add(hbox_ct1,      flag=wx.TOP|wx.BOTTOM, border=4)

        hbox_ct2 = wx.BoxSizer(wx.HORIZONTAL)

        self.sldr_cntrst = wx.Slider(self.panel, style=wx.SL_LABELS,
                                     size=(275,-1), maxValue=5e6)

        self.entr_min = wx.TextCtrl(self.panel,  style=wx.TE_PROCESS_ENTER, size=(50,-1))
        self.entr_max = wx.TextCtrl(self.panel,  style=wx.TE_PROCESS_ENTER, size=(80,-1))

        self.sldr_cntrst.Bind(wx.EVT_SLIDER,self.onSlider)
        self.entr_min.Bind(wx.EVT_TEXT_ENTER,self.onContrastRange)
        self.entr_max.Bind(wx.EVT_TEXT_ENTER,self.onContrastRange)

        self.btn_ct1 = wx.Button(self.panel,label='reset',size=(50,-1))

        self.btn_ct1.Bind(wx.EVT_BUTTON,partial(self.setContrast,auto_contrast=True) )

        ttl_to = wx.StaticText(self.panel, label='to')
        hbox_ct2.Add(self.entr_min, flag=wx.RIGHT, border=6)
        hbox_ct2.Add(ttl_to, flag=wx.RIGHT, border=6)
        hbox_ct2.Add(self.entr_max, flag=wx.RIGHT, border=6)
        hbox_ct2.Add(self.btn_ct1, flag=wx.RIGHT,              border=6)

        vbox_ct.Add(self.sldr_cntrst, flag=wx.EXPAND|wx.RIGHT,    border=6)
        vbox_ct.Add(hbox_ct2,         flag=wx.CENTER|wx.TOP,      border=6)
        vbox.Add(vbox_ct,             flag=wx.ALL,                border=4)

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
        self.sldr_bkgd = wx.Slider(self.panel,style=wx.SL_VALUE_LABEL, maxValue=1e3)

        self.sldr_bkgd.Bind(wx.EVT_SLIDER,self.onBkgdScale)
        self.btn_bkgd.Bind(wx.EVT_BUTTON,self.openBkgd)

        hbox_bkgd1.Add(self.btn_bkgd,  flag=wx.RIGHT|wx.TOP,                 border=6)
        hbox_bkgd1.Add(self.sldr_bkgd, flag=wx.EXPAND|wx.TOP, border=6)
        vbox.Add(hbox_bkgd1,           flag=wx.TOP|wx.BOTTOM,                border=4)

        self.sldr_bkgd.SetValue(self.bkgd_scale*SLIDER_SCALE)

        ###########################
        ## Set defaults
        self.ch_clr.SetStringSelection(self.color)
        self.ch_flp.SetStringSelection(self.flip)
        self.ch_scl.SetSelection(0)
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

        self.hrz_frm_sldr.Disable()
        for btn in self.hrz_frm_btn: btn.Disable()

        self.vrt_frm_sldr.Disable()
        for btn in self.vrt_frm_btn: btn.Disable()

        return vbox


    def RightSidePanel(self,panel):
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.xrd2Dcake   = diFFit2DPanel(panel,owner=self,size=(400,400),type='cake')
        self.xrd1Dviewer = diFFit1DPanel(panel,owner=self,size=(400,100))

        vbox.Add(self.xrd2Dcake,   proportion=1, flag=wx.TOP|wx.EXPAND,    border = 10)
        vbox.Add(self.xrd1Dviewer, proportion=1, flag=wx.BOTTOM|wx.EXPAND, border = 10)

        return vbox

    def CenterPanel(self,panel):

        self.xrd2Dviewer = diFFit2DPanel(panel,owner=self)
        btnbox = self.QuickButtons(panel)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.xrd2Dviewer,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        vbox.Add(btnbox,flag=wx.ALL, border = 10)
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


class XRDImg(Group):
    '''
    XRD image class

    Attributes:
    ------------
    * self.label         = 'Data: CeO2_Allende'              # name of data set
    * self.path          = '/Volumes/Data/CeO2_Allende.tif'  # file containing x-y data
    * self.type          = 'tiff'                            # file type

    # Data parameters
    * self.image         = None or array        # should be a 3-D array [no * x * y]
    * self.iframes       = 1                    # number of frames in self.image   (row)
    * self.i             = 0                    # integer indicating current frame (row)
    * self.jframes       = 1                    # number of frames in self.image   (col)
    * self.j             = 0                    # integer indicating current frame (col)
    * self.minval        = 0                    # integer of minimum display contrast
    * self.maxval        = 100                  # integer of maximum display contrast

    mkak 2017.08.15
    '''

    def __init__(self, label=None, path='', type='tiff', image=None, h5file=None):

        self.label = label
        self.path  = path
        self.type  = type

        self.calfile = None

        self.h5file = h5file
        self.image = np.zeros((1,1,PIXELS,PIXELS)) if image is None else image

        self.check_image()
        self.calc_range()


    def check_image(self):

        if self.h5file is None:
            shp = np.shape(self.image)
            if len(shp) == 2:
                self.image = np.reshape(self.image,(1,1,shp[0],shp[1]))
            if len(shp) == 3:
                self.image = np.reshape(self.image,(1,shp[0],shp[1],shp[2]))

            self.jframes,self.iframes,self.xpix,self.ypix = np.shape(self.image)
        else:
            try:
                self.h5xrd = self.h5file['xrmmap/xrd2D/counts']
            except:
                self.image = None
                print('No 2DXRD data in %s' % os.path.split(self.h5file.filename)[-1])
                return
            self.calfile = bytes2str(self.h5file['xrmmap/xrd1D'].attrs.get('calfile',''))
            if not os.path.exists(self.calfile):
                self.calfile = None

            ## making an assumption that h5 map file always has multiple rows and cols
            self.jframes,self.iframes,self.xpix,self.ypix = self.h5xrd.shape

        self.i = 0 if self.iframes < 4 else int(self.iframes)/2
        self.j = 0 if self.jframes < 4 else int(self.jframes)/2

    def calc_range(self):

        if self.h5file is None:
            self.minval = self.image[self.j,self.i].min()
            self.maxval = self.image[self.j,self.i].max()
        else:
            self.minval = self.h5xrd[self.j,self.i].min()
            self.maxval = self.h5xrd[self.j,self.i].max()

    def get_image(self,i=None,j=None):

        if i is not None and i != self.i:
            if i < 0: i == self.iframes-1
            if i >= self.iframes: i = 0
            self.i = i

        if j is not None and j != self.j:
            if j < 0: j == self.jframes-1
            if j >= self.jframes: j = 0
            self.j = j

        if self.h5file is None:
            return self.image[self.j,self.i]
        else:
            return self.h5xrd[self.j,self.i]

    def set_contrast(self,minval,maxval):

        if maxval == minval: maxval = minval+100

        self.minval = int(minval)
        self.maxval = int(maxval)


class XRD2DViewer(LarchWxApp):
    def __init__(self, **kws):
        LarchWxApp.__init__(self, **kws)

    def createApp(self):
        frame = XRD2DViewerFrame()
        frame.Show()
        self.SetTopWindow(frame)
        return True


if __name__ == '__main__':
    XRD2DViewer().MainLoop()
