#!/usr/bin/env pythonw
'''
GUI for displaying 1D XRD images

'''

import os
import numpy as np
from scipy import constants

#import h5py
import matplotlib.cm as colormap

import wx

#from wxmplot.imagepanel import ImagePanel
from wxmplot import PlotPanel
from wxutils import MenuItem

import xrayutilities as xu

from larch_plugins.io import tifffile
from larch_plugins.diFFit.XRDCalculations import integrate_xrd,xy_file_reader
from larch_plugins.diFFit.XRDCalculations import calc_q_to_d,calc_q_to_2th
from larch_plugins.diFFit.ImageControlsFrame import ImageToolboxFrame
from larch_plugins.diFFit.XRDCalibrationFrame import CalibrationPopup

import matplotlib.pyplot as plt

HAS_pyFAI = False
try:
    import pyFAI
    import pyFAI.calibrant
    from pyFAI.calibration import Calibration
    HAS_pyFAI = True
except ImportError:
    pass


###################################

VERSION = '0 (18-October-2016)'
SLIDER_SCALE = 1000. ## sliders step in unit 1. this scales to 0.001

###################################

class Viewer1DXRD(wx.Frame):
    '''
    Frame for housing all 1D XRD viewer widgets
    '''
    def __init__(self, _larch=None,parent=None):
        
        label = 'diFFit.py : 1D XRD Viewer'
        wx.Frame.__init__(self, None, -1,title=label, parent=parent, size=(1500, 600))
        
        self.SetMinSize((700,500))
        
        self.statusbar = self.CreateStatusBar(3,wx.CAPTION )

        ## Default information
        self.data_name    = []
        self.xy_data      = []
        self.xy_plot      = []
        self.plotted_data = []
        self.xy_scale     = []
        self.wavelength   = None
        self.xlabel       = 'q (A^-1)'

        self.cif_name     = []
        self.cif_data     = []
        self.cif_plot     = []
        self.plotted_cif  = []
        
        self.x_for_zoom = None

        self.XRD1DMenuBar()
        self.Panel1DViewer()
        
        self.Centre()
        self.Show(True)

    
    def plot1Dxrd(self,data,label=None,wavelength=None):

        self.add1Ddata(*data,name=label,wavelength=wavelength)
        print 'WAVELENGTH',wavelength
     
    def write_message(self, s, panel=0):
        '''write a message to the Status Bar'''
        self.SetStatusText(s, panel)


##############################################
#### PANEL DEFINITIONS
    def XRD1DMenuBar(self):

        menubar = wx.MenuBar()
        
        ###########################
        ## diFFit1D
        diFFitMenu = wx.Menu()
        
        MenuItem(self, diFFitMenu, '&Open 1D dataset', '', self.loadXYFILE)
        MenuItem(self, diFFitMenu, '&Open CIFile', '', self.loadCIF)
        MenuItem(self, diFFitMenu, 'Sa&ve displayed image to file', '', self.onSAVEfig)
        MenuItem(self, diFFitMenu, '&Add analysis to map file', '', None)
       
        menubar.Append(diFFitMenu, '&diFFit1D')

        ###########################
        ## Process
        ProcessMenu = wx.Menu()
        
        MenuItem(self, ProcessMenu, '&Load calibration file', '', self.openPONI)
        MenuItem(self, ProcessMenu, '&Define energy/wavelegth', '', self.setLAMBDA)
        ProcessMenu.AppendSeparator()
        MenuItem(self, ProcessMenu, 'Fit &background', '', None)
        MenuItem(self, ProcessMenu, 'Save &background', '', None)
        MenuItem(self, ProcessMenu, '&Remove current background', '', None)
        
        menubar.Append(ProcessMenu, '&Process')

        ###########################
        ## Analyze
        AnalyzeMenu = wx.Menu()
        
        MenuItem(self, AnalyzeMenu, '&Something about fitting...', '', None)

        menubar.Append(AnalyzeMenu, '&Analyze')

        ###########################
        ## Create Menu Bar
        self.SetMenuBar(menubar)

    def Panel1DViewer(self):
        '''
        Frame for housing all 1D XRD viewer widgets
        '''
        self.panel = wx.Panel(self)

        leftside  = self.LeftSidePanel(self.panel)
        rightside = self.RightSidePanel(self.panel)        

        panel1D = wx.BoxSizer(wx.HORIZONTAL)
        panel1D.Add(leftside,flag=wx.ALL,border=10)
        panel1D.Add(rightside,proportion=1,flag=wx.EXPAND|wx.ALL,border=10)

        self.panel.SetSizer(panel1D)
    
    def Toolbox(self,panel):
        '''
        Frame for visual toolbox
        '''
        
        tlbx = wx.StaticBox(self.panel,label='PLOT TOOLBOX')
        vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)

        ###########################
        ## X-Scale
        hbox_xaxis = wx.BoxSizer(wx.HORIZONTAL)
        ttl_xaxis = wx.StaticText(self.panel, label='X-SCALE')
        xunits = ['q','d']
        self.ch_xaxis = wx.Choice(self.panel,choices=xunits)

        self.ch_xaxis.Bind(wx.EVT_CHOICE, self.checkXaxis)
    
        hbox_xaxis.Add(ttl_xaxis, flag=wx.RIGHT, border=8)
        hbox_xaxis.Add(self.ch_xaxis, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_xaxis, flag=wx.ALL, border=10)

        ###########################
        ## Y-Scale
        hbox_yaxis = wx.BoxSizer(wx.HORIZONTAL)
        ttl_yaxis = wx.StaticText(self.panel, label='Y-SCALE')
        yscales = ['linear','log']
        self.ch_yaxis = wx.Choice(self.panel,choices=yscales)

        self.ch_yaxis.Bind(wx.EVT_CHOICE,   None)
    
        hbox_yaxis.Add(ttl_yaxis, flag=wx.RIGHT, border=8)
        hbox_yaxis.Add(self.ch_yaxis, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_yaxis, flag=wx.ALL, border=10)
        
        return vbox

    def DataBox(self,panel):
        '''
        Frame for data toolbox
        '''
        
        tlbx = wx.StaticBox(self.panel,label='DATA TOOLBOX')
        vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)


        ###########################
        ## DATA CHOICE

        self.ch_data = wx.Choice(self.panel,choices=self.data_name)
        self.ch_data.Bind(wx.EVT_CHOICE,   self.onSELECT)
        vbox.Add(self.ch_data, flag=wx.EXPAND|wx.ALL, border=8)
    
        #self.ttl_data = wx.StaticText(self.panel, label='')
        #vbox.Add(self.ttl_data, flag=wx.EXPAND|wx.ALL, border=8)

        ###########################

#         self.ck_bkgd = wx.CheckBox(self.panel,label='BACKGROUND')
#         self.ck_smth = wx.CheckBox(self.panel,label='SMOOTHING')
#         
#         self.ck_bkgd.Bind(wx.EVT_CHECKBOX,   None)
#         self.ck_smth.Bind(wx.EVT_CHECKBOX,   None)
# 
#         vbox.Add(self.ck_bkgd, flag=wx.ALL, border=8)
#         vbox.Add(self.ck_smth, flag=wx.ALL, border=8)
    
        ###########################
        ## Scale
        hbox_scl = wx.BoxSizer(wx.HORIZONTAL)
        ttl_scl = wx.StaticText(self.panel, label='SCALE Y TO:')
        self.entr_scale = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        btn_scale = wx.Button(self.panel,label='set')

        btn_scale.Bind(wx.EVT_BUTTON, self.normalize1Ddata)
        
        hbox_scl.Add(ttl_scl, flag=wx.RIGHT, border=8)
        hbox_scl.Add(self.entr_scale, flag=wx.RIGHT, border=8)
        hbox_scl.Add(btn_scale, flag=wx.RIGHT, border=8)

        vbox.Add(hbox_scl, flag=wx.BOTTOM|wx.TOP, border=8)

        ###########################
        ## Hide/show and reset
        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_hide  = wx.Button(self.panel,label='hide')
        btn_reset = wx.Button(self.panel,label='reset')
        btn_rmv   = wx.Button(self.panel,label='remove')
        
        btn_hide.Bind(wx.EVT_BUTTON,  self.hide1Ddata)
        btn_reset.Bind(wx.EVT_BUTTON, self.reset1Dscale)
        btn_rmv.Bind(wx.EVT_BUTTON,   self.remove1Ddata)
        
        hbox_btns.Add(btn_reset, flag=wx.ALL, border=10)
        hbox_btns.Add(btn_hide,  flag=wx.ALL, border=10)
        hbox_btns.Add(btn_rmv,   flag=wx.ALL, border=10)
        vbox.Add(hbox_btns, flag=wx.ALL, border=10)
        return vbox    

#     def CIFBox(self,panel):
#         '''
#         Frame for cif toolbox
#         '''
#        
#         tlbx = wx.StaticBox(self.panel,label='CIF TOOLBOX')
#         vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)
# 
#         ###########################
#         ## DATA CHOICE
# 
#         self.ch_cif = wx.Choice(self.panel,choices=self.cif_name)
# #         self.ch_cif.Bind(wx.EVT_CHOICE,   self.onSELECT)
#         vbox.Add(self.ch_cif, flag=wx.EXPAND|wx.ALL, border=8)
# 
#         ###########################
#         ## Scale
#         hbox_cifscl = wx.BoxSizer(wx.HORIZONTAL)
#         ttl_cifscl = wx.StaticText(self.panel, label='SCALE Y TO:')
#         self.entr_cifscl = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
#         btn_cifscl = wx.Button(self.panel,label='set scale')
# 
#         btn_cifscl.Bind(wx.EVT_BUTTON,   None)
# 
#         hbox_cifscl.Add(ttl_cifscl, flag=wx.RIGHT, border=8)
#         hbox_cifscl.Add(self.entr_cifscl, flag=wx.RIGHT, border=8)
#         hbox_cifscl.Add(btn_cifscl, flag=wx.RIGHT, border=8)
# 
#         vbox.Add(hbox_cifscl, flag=wx.BOTTOM|wx.TOP, border=8)
# 
#         return vbox

    def AddPanel(self,panel):
    
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_data = wx.Button(panel,label='ADD NEW DATA SET')
        btn_data.Bind(wx.EVT_BUTTON, self.loadXYFILE)

        btn_cif = wx.Button(panel,label='ADD NEW CIF')
        btn_cif.Bind(wx.EVT_BUTTON, self.loadCIF)
    
        hbox.Add(btn_data, flag=wx.ALL, border=8)
        hbox.Add(btn_cif, flag=wx.ALL, border=8)
        return hbox

    def LeftSidePanel(self,panel):
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        plttools = self.Toolbox(self.panel)
        addbtns = self.AddPanel(self.panel)
        dattools = self.DataBox(self.panel)
#         ciftools = self.CIFBox(self.panel)        
        
        vbox.Add(plttools,flag=wx.ALL,border=10)
        vbox.Add(addbtns,flag=wx.ALL,border=10)
        vbox.Add(dattools,flag=wx.ALL,border=10)
#         vbox.Add(ciftools,flag=wx.ALL,border=10)
        return vbox

    def RightSidePanel(self,panel):
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.plot1DXRD(panel)
        btnbox = self.QuickButtons(panel)
        vbox.Add(self.plot1D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        vbox.Add(btnbox,flag=wx.ALL|wx.ALIGN_RIGHT,border = 10)
        return vbox

    def QuickButtons(self,panel):
        buttonbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_img = wx.Button(panel,label='SAVE FIGURE')
        btn_calib = wx.Button(panel,label='PLOT SETTINGS')
        btn_integ = wx.Button(panel,label='RESET PLOT')
        
        btn_img.Bind(wx.EVT_BUTTON,   self.onSAVEfig)
        btn_calib.Bind(wx.EVT_BUTTON, self.onPLOTset)
        btn_integ.Bind(wx.EVT_BUTTON, self.onRESETplot)
        
        buttonbox.Add(btn_img, flag=wx.ALL, border=8)
        buttonbox.Add(btn_calib, flag=wx.ALL, border=8)
        buttonbox.Add(btn_integ, flag=wx.ALL, border=8)
        return buttonbox


##############################################
#### PLOTPANEL FUNCTIONS
    def plot1DXRD(self,panel):
    
        self.plot1D = PlotPanel(panel,size=(1000, 500))
        self.plot1D.messenger = self.write_message
        

        ## Set defaults for plotting  
        self.plot1D.set_ylabel('Intensity (a.u.)')
        self.plot1D.cursor_mode = 'zoom'
  
        ## trying to get this functionality into our gui
        ## mkak 2016.11.10      
#         interactive_legend().show()

    def onSAVEfig(self,event):
        self.plot1D.save_figure()
        
    def onPLOTset(self,event):
        self.plot1D.configure()
        
    def onRESETplot(self,event):
        self.plot1D.reset_config()



##############################################
#### XRD PLOTTING FUNCTIONS
       
    def add1Ddata(self,x,y,name=None,cif=False,wavelength=None):
        
        plt_no = len(self.data_name)
        
        if cif:
            if name is None:
                name = 'cif %i' % plt_no
            else:
               name = 'cif: %s' % name
        else:
            if name is None:
                name = 'dataset %i' % plt_no
            else:
                name = 'data: %s' % name
                
        if wavelength is not None:
            self.addLAMBDA(wavelength)

        ## Add to data array lists
        self.data_name.append(name)
        self.xy_scale.append(max(y))
        self.xy_data.extend([x,y])

        ## redefine x,y based on scales
        self.xy_plot.extend([x,y])
       
        ## Add to plot       
        self.plotted_data.append(self.plot1D.oplot(x,y,label=name,show_legend=True))#,xlabel=self.xlabel))

        ## Use correct x-axis units
        self.checkXaxis(None)

        self.ch_data.Set(self.data_name)
        self.ch_data.SetStringSelection(name)
        
        ## Update toolbox panel, scale all cif to 1000
        if cif is True:
            self.entr_scale.SetValue('1000')
            self.normalize1Ddata(None)
        else:
            self.entr_scale.SetValue(str(self.xy_scale[plt_no]))

    def addLAMBDA(self,wavelength,units='m'):
        
        ## convert to units A
        if units == 'm':
            self.wavelength = wavelength*1e10 
        elif units == 'cm':
            self.wavelength = wavelength*1e8
        elif units == 'mm':
            self.wavelength = wavelength*1e7        
        elif units == 'um':
            self.wavelength = wavelength*1e4
        elif units == 'nm':
            self.wavelength = wavelength*1e1
        else: ## units 'A'        
            self.wavelength = wavelength

        xunits = ['q','d',u'2\u03B8']
        self.ch_xaxis.Set(xunits)

    def normalize1Ddata(self,event):
    
        plt_no = self.ch_data.GetSelection()
        self.xy_scale[plt_no] = float(self.entr_scale.GetValue())
        if self.xy_scale[plt_no] <= 0:
            self.xy_scale[plt_no] = max(self.xy_data[(plt_no*2+1)])
            self.entr_scale.SetValue(str(self.xy_scale[plt_no]))

        y = self.xy_data[(plt_no*2+1)]
        self.xy_plot[(plt_no*2+1)] = y/np.max(y) * self.xy_scale[plt_no]

        self.updatePLOT()
        

    def remove1Ddata(self,event):
        
        ## Needs pop up warning: "Do you really want to delete this data set from plotter?
        ## Current settings will not be saved."
        ## mkak 2016.11.10
        
        plt_no = self.ch_data.GetSelection()        
        print 'EVENTUALLY, button will remove plot: ',self.data_name[plt_no]

        ## removing name from list works... do not activate till rest is working
        ## mkak 2016.11.10
#         self.data_name.remove(self.data_name[plt_no])
#         self.ch_data.Set(self.data_name)

    def hide1Ddata(self,event):

        plt_no = self.ch_data.GetSelection()        
        print 'EVENTUALLY, button will hide plot: ',self.data_name[plt_no]

    def onSELECT(self,event):
    
        data_str = self.ch_data.GetString(self.ch_data.GetSelection())
#         self.ttl_data.SetLabel('SELECTED: %s' % data_str)
        
        plt_no = self.ch_data.GetSelection()
        self.entr_scale.SetValue(str(self.xy_scale[plt_no]))

    def checkXaxis(self, event):
        
        if self.ch_xaxis.GetSelection() == 2:
            for plt_no in range(len(self.plotted_data)):
                self.xy_plot[plt_no*2] = calc_q_to_2th(self.xy_data[plt_no*2],self.wavelength)
        elif self.ch_xaxis.GetSelection() == 1:
            for plt_no in range(len(self.plotted_data)):
                self.xy_plot[plt_no*2] = calc_q_to_d(self.xy_data[plt_no*2])
        else:
            for plt_no in range(len(self.plotted_data)):
                self.xy_plot[plt_no*2] = self.xy_data[plt_no*2]

        if self.ch_xaxis.GetSelection() == 2:
            self.xlabel = r'$2\Theta$'+r' $(^\circ)$'
        elif self.ch_xaxis.GetSelection() == 1:
            self.xlabel = 'd ($\AA$)'
        else:
            self.xlabel = 'q (1/$\AA$)'
         
        self.plot1D.set_xlabel(self.xlabel)
        self.updatePLOT()

    def updatePLOT(self):

        xmax,xmin,ymax,ymin = None,0,None,0
    
        if len(self.plotted_data) > 0:
            for plt_no in range(len(self.plotted_data)):

                i = plt_no*2
                j = i+1
 
                x = self.xy_plot[i]
                y = self.xy_plot[j]
                
                if xmax is None or xmax < max(x):
                    xmax = max(x)
                if xmin > min(x):
                    xmin = min(x)
                if ymax is None or ymax < max(y):
                    ymax = max(y)
                if ymin > min(y):
                    ymin = min(y)
                
                self.plot1D.update_line(plt_no,x,y)
            
            self.unzoom_all()
            self.plot1D.canvas.draw()
            
            if self.ch_xaxis.GetSelection() == 1:
                xmax = 5
            self.plot1D.set_xylims([xmin, xmax, ymin, ymax])

    def reset1Dscale(self,event):

        plt_no = self.ch_data.GetSelection()        
       
        self.xy_plot[(plt_no*2+1)] = self.xy_data[(plt_no*2+1)]
        self.plot1D.update_line(plt_no,self.xy_plot[(plt_no*2)],
                                       self.xy_plot[(plt_no*2+1)])
        self.plot1D.canvas.draw()
        self.unzoom_all()
        
        self.updatePLOT()
        self.xy_scale[plt_no] = max(self.xy_data[(plt_no*2+1)])
        self.entr_scale.SetValue(str(self.xy_scale[plt_no]))

####### BEGIN #######            
## THIS IS DIRECTLY FROM XRDDISPLAY.PY
## mkak 2016.11.11
    def unzoom_all(self, event=None):

        xmid, xrange, xmin, xmax = self._get1Dlims()

        self._set_xview(xmin, xmax)
        self.xview_range = None

    def _get1Dlims(self):
        xmin, xmax = self.plot1D.axes.get_xlim()
        xrange = xmax-xmin
        xmid   = (xmax+xmin)/2.0
        if self.x_for_zoom is not None:
            xmid = self.x_for_zoom
        return (xmid, xrange, xmin, xmax)

    def _set_xview(self, x1, x2, keep_zoom=False, pan=False):

        xmin,xmax = self.abs_limits()
        xrange = x2-x1
        x1 = max(xmin,x1)
        x2 = min(xmax,x2)

        if pan:
            if x2 == xmax:
                x1 = x2-xrange
            elif x1 == xmin:
                x2 = x1+xrange
        if not keep_zoom:
            self.x_for_zoom = (x1+x2)/2.0
        self.plot1D.axes.set_xlim((x1, x2))
        self.xview_range = [x1, x2]
        self.plot1D.canvas.draw()

    def abs_limits(self):
        if len(self.data_name) > 0:
            xmin, xmax = self.xy_plot[0].min(), self.xy_plot[0].max()
   
        return xmin,xmax
#######  END  #######
       

##############################################
#### XRD FILE OPENING/SAVING 
    def loadXYFILE(self,event):
    
        wildcards = 'XRD data file (*.xy)|*.xy|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose 1D XRD data file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            try:
                x,y = xy_file_reader(path)

                self.add1Ddata(x,y,name=os.path.split(path)[-1])
            except:
               print 'incorrect xy file format: %s' % os.path.split(path)[-1]



    def saveXYFILE(self,event):
        wildcards = 'XRD data file (*.xy)|*.xy|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, 'Save data as...',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards,
                           style=wx.SAVE|wx.OVERWRITE_PROMPT)

        path, save = None, False
        if dlg.ShowModal() == wx.ID_OK:
            save = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if save:
            print 'need to write something to save data - like pyFAI does?'

    def loadCIF(self,event):
    
        wildcards = 'XRD cifile (*.cif)|*.cif|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose CIF',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            cifile = os.path.split(path)[-1]

            try:
                cif = xu.materials.Crystal.fromCIF(path)
            except:
                print 'incorrect file format: %s' % os.path.split(path)[-1]
                return

            ## generate hkl list
            hkllist = []
            maxhkl = 8
            for i in range(-maxhkl,maxhkl+1):
                for j in range(-maxhkl,maxhkl+1):
                    for k in range(-maxhkl,maxhkl+1):
                        if i+j+k > 0: # as long as h,k,l all positive, eliminates 0,0,0
                            hkllist.append([i,j,k])
            
#             hkllist.append([i,j,k] for i,j,k in np.arange(maxhkl),np.arange(maxhkl),np.arange(maxhkl))
#             print hkllist
            

            hc = constants.value(u'Planck constant in eV s') * \
                       constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m

            qlist = cif.Q(hkllist)
            Flist = cif.StructureFactorForQ(qlist,(hc/(self.wavelength*(1e-10))*1e3))
            
            Fall = []
            qall = []
            hklall = []
            for i,hkl in enumerate(hkllist):
                if np.abs(Flist[i]) > 0.01:
                    Fadd = np.abs(Flist[i])
                    qadd = np.linalg.norm(qlist[i])
                    if qadd not in qall and qadd < 6:
                        Fall.extend((0,Fadd,0))
                        qall.extend((qadd,qadd,qadd))
            if np.shape(Fall)[0] > 0:
                Fall = np.array(Fall)
                qall = np.array(qall)
                self.add1Ddata(qall,Fall,name=os.path.split(path)[-1],cif=True)
            else:
                print 'Could not calculate real structure factors.'

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
                print 'Loading calibration file: %s' % path
                ai = pyFAI.load(path)
            except:
                print('Not recognized as a pyFAI calibration file.')
                return

            self.addLAMBDA(ai._wavelength,units='m')

    def setLAMBDA(self,event):

        dlg = SetLambdaDialog()

        path, okay = None, False
        if dlg.ShowModal() == wx.ID_OK:
            okay = True
            wavelength = dlg.wavelength
        dlg.Destroy()
        
        if okay:
            self.addLAMBDA(wavelength,units='A')
              

# def interactive_legend(ax=None):
#     if ax is None:
#         ax = plt.gca()
#     if ax.legend_ is None:
#         ax.legend()
# 
#     return InteractiveLegend(ax.legend_)
# 
# class InteractiveLegend(object):
#     def __init__(self, legend):
#         self.legend = legend
#         self.fig = legend.axes.figure
# 
#         self.lookup_artist, self.lookup_handle = self._build_lookups(legend)
#         self._setup_connections()
# 
#         self.update()
# 
#     def _setup_connections(self):
#         for artist in self.legend.texts + self.legend.legendHandles:
#             artist.set_picker(10) # 10 points tolerance
# 
#         self.fig.canvas.mpl_connect('pick_event', self.on_pick)
#         self.fig.canvas.mpl_connect('button_press_event', self.on_click)
# 
#     def _build_lookups(self, legend):
#         labels = [t.get_text() for t in legend.texts]
#         handles = legend.legendHandles
#         label2handle = dict(zip(labels, handles))
#         handle2text = dict(zip(handles, legend.texts))
# 
#         lookup_artist = {}
#         lookup_handle = {}
#         for artist in legend.axes.get_children():
#             if artist.get_label() in labels:
#                 handle = label2handle[artist.get_label()]
#                 lookup_handle[artist] = handle
#                 lookup_artist[handle] = artist
#                 lookup_artist[handle2text[handle]] = artist
# 
#         lookup_handle.update(zip(handles, handles))
#         lookup_handle.update(zip(legend.texts, handles))
# 
#         return lookup_artist, lookup_handle
# 
#     def on_pick(self, event):
#         handle = event.artist
#         if handle in self.lookup_artist:
#             artist = self.lookup_artist[handle]
#             artist.set_visible(not artist.get_visible())
#             self.update()
# 
#     def on_click(self, event):
#         if event.button == 3:
#             visible = False
#         elif event.button == 2:
#             visible = True
#         else:
#             return
# 
#         for artist in self.lookup_artist.values():
#             artist.set_visible(visible)
#         self.update()
# 
#     def update(self):
#         for artist in self.lookup_artist.values():
#             handle = self.lookup_handle[artist]
#             if artist.get_visible():
#                 handle.set_visible(True)
#             else:
#                 handle.set_visible(False)
#         self.fig.canvas.draw()
# 
#     def show(self):
#         plt.show()


##### Pop-up from 2D XRD Viewer to calculate 1D pattern
class Calc1DPopup(wx.Dialog):
    def __init__(self,xrd2Ddata,ai):
    
        """Constructor"""
        dialog = wx.Dialog.__init__(self, None, title='Calculate 1DXRD options',
                                    style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,
                                    size = (210,410))
        
        self.data2D = xrd2Ddata
        self.ai = ai
        self.steps = 5001

        self.Init()
        self.setDefaults()
        
        ## Set defaults
        self.wedges.SetValue('1')
        

    def Init(self):
    
        self.panel = wx.Panel(self)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        
        ## Azimutal wedges 
        wedgesizer = wx.BoxSizer(wx.VERTICAL)

        ttl_wedges = wx.StaticText(self.panel, label='AZIMUTHAL WEDGES')
        
        wsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.wedges = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        self.wedge_arrow = wx.SpinButton(self.panel, style=wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP)
       
        self.wedge_arrow.Bind(wx.EVT_SPIN, self.onSPIN)
        
        wsizer.Add(self.wedges,flag=wx.RIGHT,border=8)
        wsizer.Add(self.wedge_arrow,flag=wx.RIGHT,border=8)
        
        wedgesizer.Add(ttl_wedges,flag=wx.BOTTOM,border=8)
        wedgesizer.Add(wsizer,flag=wx.BOTTOM,border=8)

        mainsizer.Add(wedgesizer,flag=wx.ALL,border=8)

        ## Y-Range
        ysizer = wx.BoxSizer(wx.VERTICAL)
        
        ttl_yrange = wx.StaticText(self.panel, label='Y-RANGE (a.u.)')
                
        yminsizer = wx.BoxSizer(wx.HORIZONTAL)
        ttl_ymin = wx.StaticText(self.panel, label='minimum')
        self.ymin = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        yminsizer.Add(ttl_ymin,  flag=wx.RIGHT, border=5)        
        yminsizer.Add(self.ymin,  flag=wx.RIGHT, border=5)        
        
        ymaxsizer = wx.BoxSizer(wx.HORIZONTAL)
        ttl_ymax = wx.StaticText(self.panel, label='maximum')
        self.ymax = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        ymaxsizer.Add(ttl_ymax,  flag=wx.RIGHT, border=5)        
        ymaxsizer.Add(self.ymax,  flag=wx.RIGHT, border=5)

        ysizer.Add(ttl_yrange,  flag=wx.BOTTOM, border=5)        
        ysizer.Add(yminsizer,  flag=wx.BOTTOM, border=5)
        ysizer.Add(ymaxsizer,  flag=wx.BOTTOM, border=5)
        mainsizer.Add(ysizer,  flag=wx.ALL, border=5)


        ## X-Range
        xsizer = wx.BoxSizer(wx.VERTICAL)
        
        ttl_xrange = wx.StaticText(self.panel, label='X-RANGE')
        
        xunitsizer = wx.BoxSizer(wx.HORIZONTAL)
        xunits = ['q','d',u'2\u03B8']
        ttl_xunit = wx.StaticText(self.panel, label='units')
        self.ch_xunit = wx.Choice(self.panel,choices=xunits)
        self.ch_xunit.Bind(wx.EVT_CHOICE,self.onUnits)
        
        xunitsizer.Add(ttl_xunit, flag=wx.RIGHT, border=5)
        xunitsizer.Add(self.ch_xunit, flag=wx.RIGHT, border=5)

        xstepsizer = wx.BoxSizer(wx.HORIZONTAL)
        ttl_xstep = wx.StaticText(self.panel, label='steps')
        self.xstep = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        xstepsizer.Add(ttl_xstep,  flag=wx.RIGHT, border=5)
        xstepsizer.Add(self.xstep,  flag=wx.RIGHT, border=5)
                        
        xminsizer = wx.BoxSizer(wx.HORIZONTAL)
        ttl_xmin = wx.StaticText(self.panel, label='minimum')
        self.xmin = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        xminsizer.Add(ttl_xmin,  flag=wx.RIGHT, border=5)
        xminsizer.Add(self.xmin,  flag=wx.RIGHT, border=5)
        
        xmaxsizer = wx.BoxSizer(wx.HORIZONTAL)
        ttl_xmax = wx.StaticText(self.panel, label='maximum')
        self.xmax = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        xmaxsizer.Add(ttl_xmax,  flag=wx.RIGHT, border=5)        
        xmaxsizer.Add(self.xmax,  flag=wx.RIGHT, border=5)

        xsizer.Add(ttl_xrange,  flag=wx.BOTTOM, border=5)
        xsizer.Add(xunitsizer, flag=wx.TOP|wx.BOTTOM, border=5)
        xsizer.Add(xstepsizer, flag=wx.TOP|wx.BOTTOM, border=5)
        xsizer.Add(xminsizer,  flag=wx.TOP|wx.BOTTOM, border=5)
        xsizer.Add(xmaxsizer,  flag=wx.TOP|wx.BOTTOM, border=5)
        mainsizer.Add(xsizer,  flag=wx.ALL, border=5)

        ## Okay Buttons
#         btn_cncl = wx.Button(self.panel, wx.CANCEL)
        btn_save = wx.Button(self.panel, label = 'Save 1D')
        btn_plot  = wx.Button(self.panel, label = 'Plot 1D')

        btn_save.Bind(wx.EVT_BUTTON,self.onSAVE)
        btn_plot.Bind(wx.EVT_BUTTON,self.onPLOT)
#         btn_cncl.SetLabel('Close')

        minisizer = wx.BoxSizer(wx.HORIZONTAL)
#         minisizer.Add(btn_cncl,  flag=wx.RIGHT, border=5)
        minisizer.Add(btn_save,  flag=wx.RIGHT, border=5)
        minisizer.Add(btn_plot,  flag=wx.RIGHT, border=5)
        
        mainsizer.Add(minisizer, flag=wx.ALL, border=8)
#         mainsizer.Add(btn_cncl, flag=wx.ALL, border=8)

        self.panel.SetSizer(mainsizer)
        
        
    def setDefaults(self):

        self.ymin.SetValue(str(0))
        self.ymax.SetValue(str(10000))
        self.xstep.SetValue(str(5001))
        self.xmin.SetValue(str(0.1))
        self.xmax.SetValue(str(5.5))
        self.wedges.SetValue(str(1))
        
        self.wedge_arrow.SetRange(1, 10)
        self.wedge_arrow.SetValue(1)
        
    def onUnits(self,event):

        hc = constants.value(u'Planck constant in eV s') * \
                       constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m
#         if self.slctEorL.GetSelection() == 1:
#             energy = float(self.EorL.GetValue()) ## units keV
#             wavelength = hc/(energy)*1e10 ## units: A
#             self.EorL.SetValue(str(wavelength))
#         else:
#             wavelength = float(self.EorL.GetValue())*1e-10 ## units: m
#             energy = hc/(wavelength) ## units: keV
#             self.EorL.SetValue(str(energy))

    def onSPIN(self, event):
        self.wedges.SetValue(str(event.GetPosition())) 
        print 'not currently using multiple wedges for calculations'

    def onSAVE(self,event):

        self.getValues()
        
        wildcards = '1D XRD file (*.xy)|*.xy|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, 'Save file as...',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards,
                           style=wx.SAVE|wx.OVERWRITE_PROMPT)

        path, save = None, False
        if dlg.ShowModal() == wx.ID_OK:
            save = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if save:
            self.data1D = integrate_xrd(self.data2D,steps=self.steps,ai = self.ai,file=path,verbose=True)

    def onPLOT(self,event):

        self.getValues()
        
        self.data1D = integrate_xrd(self.data2D,steps=self.steps,ai = self.ai,save=False,verbose=True)
        xrddisplay1D = Viewer1DXRD()
        xrddisplay1D.plot1Dxrd(self.data1D,wavelength=self.ai._wavelength)
        

    def getValues(self):
    
        self.steps = int(self.xstep.GetValue())
    

class SetLambdaDialog(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
    
        ## Constructor
        dialog = wx.Dialog.__init__(self, None, title='Define wavelength/energy')#,size=(500, 440))
        ## remember: size=(width,height)
        
        panel = wx.Panel(self)
        
        main = wx.BoxSizer(wx.VERTICAL)
        hmain1 = wx.BoxSizer(wx.HORIZONTAL)
        
        #####
        ## Energy or Wavelength
        hmain1 = wx.BoxSizer(wx.HORIZONTAL)
        self.ch_EorL = wx.Choice(panel,choices=['Energy (keV)','Wavelength (A)'])
        self.entr_EorL = wx.TextCtrl(panel)#, size=(110, -1))
 
        self.ch_EorL.Bind(wx.EVT_CHOICE, self.onEorLSel)
 
        hmain1.Add(self.ch_EorL,   flag=wx.RIGHT,  border=8)
        hmain1.Add(self.entr_EorL, flag=wx.RIGHT,  border=8)
        
        #####
        ## OKAY!
        hmain2 = wx.BoxSizer(wx.HORIZONTAL)
        #hlpBtn = wx.Button(panel, wx.ID_HELP    )
        okBtn  = wx.Button(panel, wx.ID_OK      )
        canBtn = wx.Button(panel, wx.ID_CANCEL  )

        #hmain2.Add(hlpBtn,flag=wx.RIGHT,  border=8)
        hmain2.Add(canBtn, flag=wx.RIGHT, border=8) 
        hmain2.Add(okBtn,  flag=wx.RIGHT,  border=8)

        main.Add(hmain1, flag=wx.ALL, border=10) 
        main.Add(hmain2, flag=wx.ALL, border=10) 

        panel.SetSizer(main)

        self.Show()
        
        ## set default
        self.hc = constants.value(u'Planck constant in eV s') * \
                       constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m
        self.energy = 19.0        
        self.wavelength = self.hc/(self.energy)*1e10 ## units: A
        self.ch_EorL.SetSelection(0)
        self.entr_EorL.SetValue(str(self.energy))

    def onEorLSel(self,event): 
        
        if float(self.entr_EorL.GetValue()) < 0 or self.entr_EorL.GetValue() == '':
            self.ch_EorL.SetSelection(1)
            self.entr_EorL.SetValue('19.0')     ## 19.0 keV

        if self.ch_EorL.GetSelection() == 1:
            self.energy = float(self.entr_EorL.GetValue()) ## units keV
            self.wavelength = self.hc/(self.energy)*1e10 ## units: A
            self.entr_EorL.SetValue(str(self.wavelength))
        else:
            self.wavelength = float(self.entr_EorL.GetValue())*1e-10 ## units: m
            self.energy = self.hc/(self.wavelength) ## units: keV
            self.entr_EorL.SetValue(str(self.energy))
    
      
class diFFit1D(wx.App):
    def __init__(self):
        wx.App.__init__(self)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = Viewer1DXRD(None)
        frame.Show()
        self.SetTopWindow(frame)

    def OnInit(self):
        self.createApp()
        return True

def registerLarchPlugin():
    return ('_diFFit', {})

class DebugViewer(diFFit1D):
    def __init__(self, **kws):
        diFFit1D.__init__(self, **kws)

    def OnInit(self):
        #self.Init()
        self.createApp()
        #self.ShowInspectionTool()
        return True

if __name__ == '__main__':
    diFFit1D().run()
