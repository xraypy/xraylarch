#!/usr/bin/env pythonw
'''
GUI for displaying 1D XRD images

'''

import os
import numpy as np
from scipy import constants,signal
import sys

#import h5py
import matplotlib.cm as colormap

import wx
import wx.lib.scrolledpanel as scrolled

from wxmplot import PlotPanel
from wxutils import MenuItem,pack

from larch_plugins.diFFit.cifdb import cifDB

from larch_plugins.io import tifffile
from larch_plugins.diFFit.XRDCalculations import integrate_xrd,xy_file_reader
from larch_plugins.diFFit.XRDCalculations import calc_q_to_d,calc_q_to_2th,generate_hkl
from larch_plugins.diFFit.XRDCalculations import gaussian_peak_fit
from larch_plugins.diFFit.ImageControlsFrame import ImageToolboxFrame
from larch_plugins.diFFit.xrd_bgr import xrd_background

from functools import partial

import matplotlib.pyplot as plt

import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.mixins.listctrl  as listmix


HAS_pyFAI = False
try:
    import pyFAI
    import pyFAI.calibrant
    # from pyFAI.calibration import Calibration
    HAS_pyFAI = True
except ImportError:
    pass

HAS_XRAYUTIL = False
try:
    import xrayutilities as xu
    HAS_XRAYUTIL = True
except ImportError:
    pass


###################################

VERSION = '0 (30-November-2016)'

SLIDER_SCALE = 1000. ## sliders step in unit 1. this scales to 0.001

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

HC = constants.value(u'Planck constant in eV s') * \
           constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m

FIT_METHODS = ['scipy.signal.find_peaks_cwt']

###################################

def YesNo(parent, question, caption = 'Yes or no?'):
    dlg = wx.MessageDialog(parent, question, caption, wx.YES_NO | wx.ICON_QUESTION)
    result = dlg.ShowModal() == wx.ID_YES
    dlg.Destroy()
    return result
    
class diFFit1DFrame(wx.Frame):
    def __init__(self,_larch=None):

        label = 'diFFit : 1D XRD Data Analysis Software'
        wx.Frame.__init__(self, None,title=label,size=(1500, 700)) #desktop
#         wx.Frame.__init__(self, None,title=label,size=(900, 500)) #laptop
        
        self.statusbar = self.CreateStatusBar(3,wx.CAPTION)
        
        panel = wx.Panel(self)
        self.nb = wx.Notebook(panel)

        # create the page windows as children of the notebook
        self.xrd1Dviewer = Viewer1DXRD(self.nb,owner=self)
        self.xrd1Dfitting = Fitting1DXRD(self.nb,owner=self)
        self.xrddatabase = DatabaseXRD(self.nb)
        
        # add the pages to the notebook with the label to show on the tab
        self.nb.AddPage(self.xrd1Dviewer, 'Viewer')
        self.nb.AddPage(self.xrd1Dfitting, 'Fitting')
        self.nb.AddPage(self.xrddatabase, 'XRD Database')

        # finally, put the notebook in a sizer for the panel to manage
        # the layout
        sizer = wx.BoxSizer()
        sizer.Add(self.nb, -1, wx.EXPAND)
        panel.SetSizer(sizer)

        self.XRD1DMenuBar()
        
        self.energy = 19.0 ## keV
        self.wavelength = HC/(self.energy)*1e10 ## A


    def XRD1DMenuBar(self):

        menubar = wx.MenuBar()
        
        ###########################
        ## diFFit1D
        diFFitMenu = wx.Menu()
        
        MenuItem(self, diFFitMenu, '&Open 1D dataset', '', self.xrd1Dviewer.loadXYFILE)
        MenuItem(self, diFFitMenu, '&Open CIFile', '', self.xrd1Dviewer.loadCIF)
        MenuItem(self, diFFitMenu, 'Sa&ve displayed image to file', '', self.xrd1Dviewer.onSAVEfig)
        MenuItem(self, diFFitMenu, '&Add analysis to map file', '', None)
        
        menubar.Append(diFFitMenu, '&diFFit1D')


        ###########################
        ## Process
        ProcessMenu = wx.Menu()
        
        MenuItem(self, ProcessMenu, '&Load calibration file', '', self.openPONI)
        MenuItem(self, ProcessMenu, '&Define energy/wavelength', '', self.setLAMBDA)
        ProcessMenu.AppendSeparator()
        MenuItem(self, ProcessMenu, 'Fit &background', '', None)
        MenuItem(self, ProcessMenu, 'Save &background', '', None)
        MenuItem(self, ProcessMenu, '&Remove current background', '', None)
        
        menubar.Append(ProcessMenu, '&Process')

        ###########################
        ## Analyze
        AnalyzeMenu = wx.Menu()
        
        MenuItem(self, AnalyzeMenu, '&Select data for fitting', '', self.fit1Dxrd)

        menubar.Append(AnalyzeMenu, '&Analyze')

        ###########################
        ## Create Menu Bar
        self.SetMenuBar(menubar)

    def write_message(self, s, panel=0):
        '''write a message to the Status Bar'''
        self.statusbar.SetStatusText(s, panel)

    def fit1Dxrd(self,event=None):
    
        indicies = [i for i,name in enumerate(self.xrd1Dviewer.data_name) if 'cif' not in name]

        if len(indicies) > 0:
            self.list = [self.xrd1Dviewer.data_name[i] for i in indicies]
            self.all_data = self.xrd1Dviewer.xy_data
            
            dlg = SelectFittingData(self.list,self.all_data)

            okay = False
            if dlg.ShowModal() == wx.ID_OK:
                okay = True
                index = dlg.slct_1Ddata.GetSelection()
                self.list = dlg.list
                self.all_data = dlg.all_data
            dlg.Destroy()
            if okay:
                name = self.list[index]
                x = np.array(self.all_data[index][0]).flatten()
                y = np.array(self.all_data[index][1]).flatten()
                
                
        else:
            x,y,name = self.loadXYFILE()
            index = 1
        
        if index >= len(indicies):

            ## Add 'raw' data to array
            self.xrd1Dviewer.data_name.append(name)
            self.xrd1Dviewer.xy_scale.append(np.max(y))
            if self.xrd1Dviewer.xy_data is None:
                self.xrd1Dviewer.xy_data = [[x,y]]
            else:
                self.xrd1Dviewer.xy_data.append([[x],[y]])
        
            ## Add 'as plotted' data to array
            if self.xrd1Dviewer.xy_plot is None:
                self.xrd1Dviewer.xy_plot = [[x,y]]
            else:
                self.xrd1Dviewer.xy_plot.append([[x],[y]])

            ## Add to plot       
            self.xrd1Dviewer.plotted_data.append(self.xrd1Dviewer.plot1D.oplot(x,y,label=name,show_legend=True))

            self.xrd1Dviewer.ch_data.Set(self.xrd1Dviewer.data_name)
            self.xrd1Dviewer.ch_data.SetStringSelection(name)
            self.xrd1Dviewer.val_scale.SetValue(str(np.max(y)))
        
        self.nb.SetSelection(1)

        adddata = True
        if self.xrd1Dfitting.raw_data is not None:
            question = 'Do you want to replace current data file %s with selected file %s?' % (self.xrd1Dfitting.name,name)
            adddata = YesNo(self,question,caption='Overwrite warning')
        
        if adddata:

            self.xrd1Dfitting.raw_data = np.array([x,y])
            self.xrd1Dfitting.plt_data = np.array([x,y])
            self.xrd1Dfitting.xmin     = np.min(x)
            self.xrd1Dfitting.xmax     = np.max(x)

            self.xrd1Dfitting.plot1D.plot(x,y, title=name, color='blue', label='Raw data',
                                          show_legend=True)
            self.reset_fitting(name=name,min=np.min(x),max=np.max(x))

    def reset_fitting(self,name=None,min=0,max=1):

        #print '[reset_fitting]'
        self.xrd1Dfitting.name = name
        self.xrd1Dfitting.val_qmin.SetValue('%0.3f' % min)
        self.xrd1Dfitting.val_qmax.SetValue('%0.3f' % max)
        self.xrd1Dfitting.ck_bkgd.SetValue(False)
        self.xrd1Dfitting.btn_fbkgd.Enable()
        self.xrd1Dfitting.btn_rbkgd.Disable()
        self.xrd1Dfitting.ck_bkgd.Disable()
        self.xrd1Dfitting.btn_obkgd.Enable()
        self.xrd1Dfitting.btn_fpks.Enable()
        self.xrd1Dfitting.btn_opks.Enable()    
   
        self.xrd1Dfitting.delete_peaks()
        self.xrd1Dfitting.delete_background()  
        
        self.xrd1Dfitting.trim       = False
        self.xrd1Dfitting.indicies   = None      

        self.xrd1Dfitting.xmin       = min
        self.xrd1Dfitting.xmax       = max
        
        # Peak fitting defaults
        self.xrd1Dfitting.iregions = 50
        self.xrd1Dfitting.gapthrsh = 5
        
        # Background fitting defaults
        self.xrd1Dfitting.exponent   = 20
        self.xrd1Dfitting.compress   = 2
        self.xrd1Dfitting.width      = 4
   

    def loadXYFILE(self,event=None):
    
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
            except:
               print('incorrect xy file format: %s' % os.path.split(path)[-1])
               return

            return x,y,os.path.split(path)[-1]

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
                print('Loading calibration file: %s' % path)
                ai = pyFAI.load(path)
            except:
                print('Not recognized as a pyFAI calibration file.')
                return

            self.xrd1Dviewer.addLAMBDA(ai._wavelength,units='m')
            
            energy = HC/(ai._wavelength)
            self.setELvalues(energy,(ai._wavelength*1e10))

    def setLAMBDA(self,event=None):

        dlg = SetLambdaDialog(energy=self.energy)

        path, okay = None, False
        if dlg.ShowModal() == wx.ID_OK:
            okay = True
            if dlg.ch_EorL.GetSelection() == 0:
                energy = float(dlg.entr_EorL.GetValue()) ## units keV
                wavelength = HC/(energy)*1e10 ## units: A
            elif dlg.ch_EorL.GetSelection() == 1:
                wavelength = float(dlg.entr_EorL.GetValue()) ## units: A
                energy = HC/(wavelength*1e-10) ## units: keV
        dlg.Destroy()
        
        if okay:
            self.xrd1Dviewer.addLAMBDA(wavelength,units='A')
            self.setELvalues(energy,wavelength)

    def setELvalues(self,energy,wavelength):

            self.energy = energy
            self.wavelength = wavelength
            self.xrd1Dviewer.energy = energy
            self.xrd1Dviewer.wavelength = wavelength
            self.xrd1Dfitting.energy = energy
            self.xrd1Dfitting.wavelength = wavelength

            self.xrd1Dviewer.ttl_energy.SetLabel('Energy: %0.3f keV (%0.4f A)' % (energy,wavelength))
            self.xrd1Dfitting.ttl_energy.SetLabel('Energy: %0.3f keV (%0.4f A)' % (energy,wavelength))

class SelectFittingData(wx.Dialog):
    def __init__(self,list,all_data):
    
        """Constructor"""
        dialog = wx.Dialog.__init__(self, None, title='Select data for fitting',
                                    style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.OK,
                                    size = (210,410))
        self.list = list
        self.all_data = all_data
        self.energy = 19.0
        
        self.Init()
        
        ix,iy = self.panel.GetBestSize()
        self.SetSize((ix+20, iy+20))

    def Init(self):
    
        self.panel = wx.Panel(self)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        
        ## Add things 
        self.slct_1Ddata = wx.ListBox(self.panel, 26, wx.DefaultPosition, (170, 130), self.list, wx.LB_SINGLE)

        btn_new = wx.Button(self.panel,label='Load data from file')
        
        btn_new.Bind(wx.EVT_BUTTON, self.loadXYFILE)

        #####
        ## OKAY!
        oksizer = wx.BoxSizer(wx.HORIZONTAL)
        #hlpBtn = wx.Button(self.panel, wx.ID_HELP    )
        self.okBtn  = wx.Button(self.panel, wx.ID_OK      )
        canBtn = wx.Button(self.panel, wx.ID_CANCEL  )

        #oksizer.Add(hlpBtn,flag=wx.RIGHT,  border=8)
        oksizer.Add(canBtn, flag=wx.RIGHT, border=8) 
        oksizer.Add(self.okBtn,  flag=wx.RIGHT,  border=8)

        mainsizer.Add(self.slct_1Ddata, flag=wx.ALL, border=8)
        mainsizer.AddSpacer(15)
        mainsizer.Add(btn_new, flag=wx.ALL, border=5)
        mainsizer.AddSpacer(15)
        mainsizer.Add(oksizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=10) 

        self.panel.SetSizer(mainsizer)

    def loadXYFILE(self,event=None):
    
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
                self.all_data.append(xy_file_reader(path))
                self.list.append(os.path.split(path)[-1])
                self.slct_1Ddata.Set(self.list)
                self.slct_1Ddata.SetSelection(-1)
            except:
               print('incorrect xy file format: %s' % os.path.split(path)[-1])
               return

class CIFDatabaseList(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        
class DatabaseXRD(wx.Panel, listmix.ColumnSorterMixin):
    """
    This will be the second notebook tab
    """
    #----------------------------------------------------------------------
    def __init__(self, parent):
        """"""
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        self.createAndLayout()
        
    def createDATABASEarray(self,file='amscd_cif.db'):
    
        mycifdatabase = cifDB(dbname=file)
        display_array = mycifdatabase.create_array()

        return display_array
    
    def createAndLayout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.list = CIFDatabaseList(self, wx.ID_ANY, style=wx.LC_REPORT
                                 | wx.BORDER_NONE
                                 | wx.LC_EDIT_LABELS
                                 | wx.LC_SORT_ASCENDING)
        sizer.Add(self.list, 1, wx.EXPAND)
        
        self.database_info = self.createDATABASEarray()
        
        self.populateList()
        
        self.itemDataMap = self.database_info
        listmix.ColumnSorterMixin.__init__(self, 4)
        self.SetSizer(sizer)
        self.SetAutoLayout(True)
        
    def populateList(self):
        self.list.InsertColumn(0, 'AMSCD ID', wx.LIST_FORMAT_RIGHT)
        self.list.InsertColumn(1, 'Name')
        self.list.InsertColumn(2, 'Space Group')
        self.list.InsertColumn(3, 'Elements')
        self.list.InsertColumn(4, 'Authors')
        
        for key, data in self.database_info.items():
            index = self.list.InsertStringItem(sys.maxint, data[0])
            self.list.SetStringItem(index, 1, data[1])
            self.list.SetStringItem(index, 2, data[2])
            self.list.SetStringItem(index, 3, data[3])
            self.list.SetStringItem(index, 4, data[4])
            self.list.SetItemData(index, key)

        self.list.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.list.SetColumnWidth(1, 100)
        self.list.SetColumnWidth(2, wx.LIST_AUTOSIZE)
        self.list.SetColumnWidth(3, wx.LIST_AUTOSIZE)
        self.list.SetColumnWidth(4, wx.LIST_AUTOSIZE)
        
# 
#         # show how to select an item
#         self.list.SetItemState(5, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
# 
#         # show how to change the colour of a couple items
#         item = self.list.GetItem(1)
#         item.SetTextColour(wx.BLUE)
#         self.list.SetItem(item)
#         item = self.list.GetItem(4)
#         item.SetTextColour(wx.RED)
#         self.list.SetItem(item)

        self.currentItem = 0
        
    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self.list

class Fitting1DXRD(wx.Panel):
    '''
    Panel for housing 1D XRD fitting
    '''
    label='Fitting'
    def __init__(self,parent,owner=None,_larch=None):
        
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.owner = owner

        ## Default information
        self.raw_data   = None
        self.plt_data   = None
        self.bgr_data   = None
        
        self.bgr        = None
        self.bgr_info   = None
        
        self.ipeaks     = None
        self.plt_peaks  = None  
        
        self.trim       = False
        self.indicies   = None    
        
        self.subtracted = False  

        self.xmin       = None
        self.xmax       = None

        self.name       = ''
        self.energy     = 19.0   ## keV
        self.wavelength = HC/(self.energy)*1e10 ## A
        
        # Peak fitting defaults
        self.iregions = 50
        self.gapthrsh = 5
        
        # Background fitting defaults
        self.exponent   = 20
        self.compress   = 2
        self.width      = 4

        self.Panel1DFitting()
    

     
##############################################
#### PANEL DEFINITIONS
    def Panel1DFitting(self):
        '''
        Frame for housing all 1D XRD viewer widgets
        '''
        leftside  = self.LeftSidePanel(self)
        rightside = self.RightSidePanel(self)        

        panel1D = wx.BoxSizer(wx.HORIZONTAL)
        panel1D.Add(leftside,flag=wx.ALL,border=10)
        panel1D.Add(rightside,proportion=1,flag=wx.EXPAND|wx.ALL,border=10)

        self.SetSizer(panel1D)
    
    def FittingTools(self,panel):
        '''
        Frame for visual toolbox
        '''
        
        tlbx = wx.StaticBox(self,label='FITTING TOOLS')
        vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)

        ###########################
        ## Range tools
        vbox_rng = wx.BoxSizer(wx.VERTICAL)
        hbox_qmin = wx.BoxSizer(wx.HORIZONTAL)
        hbox_qmax = wx.BoxSizer(wx.HORIZONTAL)
        hbox_qset = wx.BoxSizer(wx.HORIZONTAL)

        ttl_rng = wx.StaticText(self, label='Q-RANGE (1/A)')
        
        ttl_qmin = wx.StaticText(self, label='minimum') 
        self.val_qmin = wx.TextCtrl(self,wx.TE_PROCESS_ENTER)
        hbox_qmin.Add(ttl_qmin, flag=wx.RIGHT, border=8)
        hbox_qmin.Add(self.val_qmin, flag=wx.RIGHT, border=8)
        
        ttl_qmax= wx.StaticText(self, label='maximum') 
        self.val_qmax = wx.TextCtrl(self,wx.TE_PROCESS_ENTER)
        hbox_qmax.Add(ttl_qmax, flag=wx.RIGHT, border=8)
        hbox_qmax.Add(self.val_qmax, flag=wx.RIGHT, border=8)

        btn_rngreset = wx.Button(self,label='reset')
        btn_rngreset.Bind(wx.EVT_BUTTON, self.reset_range)
        btn_rngset = wx.Button(self,label='set')
        btn_rngset.Bind(wx.EVT_BUTTON, self.set_range)
        
        hbox_qset.Add(btn_rngreset, flag=wx.RIGHT, border=8)
        hbox_qset.Add(btn_rngset, flag=wx.RIGHT, border=8)
        
        vbox_rng.Add(ttl_rng,   flag=wx.BOTTOM, border=8)
        vbox_rng.Add(hbox_qmin, flag=wx.BOTTOM, border=8)
        vbox_rng.Add(hbox_qmax, flag=wx.BOTTOM, border=8)
        vbox_rng.Add(hbox_qset,   flag=wx.BOTTOM|wx.ALIGN_RIGHT, border=8)

        vbox.Add(vbox_rng, flag=wx.ALL, border=8)

        ###########################
        ## Background tools
        vbox_bkgd = wx.BoxSizer(wx.VERTICAL)        
        hbox_bkgd = wx.BoxSizer(wx.HORIZONTAL)
        
        ttl_bkgd = wx.StaticText(self, label='BACKGROUND')
        vbox_bkgd.Add(ttl_bkgd, flag=wx.BOTTOM, border=8)

        self.btn_fbkgd = wx.Button(self,label='Fit')
        self.btn_fbkgd.Bind(wx.EVT_BUTTON,   self.background_fit)
        hbox_bkgd.Add(self.btn_fbkgd, flag=wx.RIGHT, border=8)

        self.btn_obkgd = wx.Button(self,label='Options')
        self.btn_obkgd.Bind(wx.EVT_BUTTON,   self.background_options)
        hbox_bkgd.Add(self.btn_obkgd, flag=wx.RIGHT, border=8)

        self.btn_rbkgd = wx.Button(self,label='Remove')
        self.btn_rbkgd.Bind(wx.EVT_BUTTON,   self.remove_background)
      
        vbox_bkgd.Add(hbox_bkgd, flag=wx.BOTTOM, border=8)
        vbox_bkgd.Add(self.btn_rbkgd, flag=wx.BOTTOM, border=8)

        self.ck_bkgd = wx.CheckBox(self,label='Subtract')
        self.ck_bkgd.Bind(wx.EVT_CHECKBOX,  self.subtract_background)
        vbox_bkgd.Add(self.ck_bkgd, flag=wx.BOTTOM, border=8)        
        
        vbox.Add(vbox_bkgd, flag=wx.ALL, border=10)

        ###########################
        ## Peak tools
        vbox_pks = wx.BoxSizer(wx.VERTICAL)        
        hbox1_pks = wx.BoxSizer(wx.HORIZONTAL)
        hbox2_pks = wx.BoxSizer(wx.HORIZONTAL)
        hbox3_pks = wx.BoxSizer(wx.HORIZONTAL)

        ttl_pks = wx.StaticText(self, label='PEAKS')
        vbox_pks.Add(ttl_pks, flag=wx.BOTTOM, border=8)

        self.btn_fpks = wx.Button(self,label='Find peaks')
        self.btn_fpks.Bind(wx.EVT_BUTTON,   self.find_peaks)
        hbox1_pks.Add(self.btn_fpks, flag=wx.RIGHT, border=8)

        self.btn_opks = wx.Button(self,label='Options')
        self.btn_opks.Bind(wx.EVT_BUTTON,   self.peak_options)
        hbox1_pks.Add(self.btn_opks, flag=wx.RIGHT, border=8)

        self.btn_rpks = wx.Button(self,label='Remove all')
        self.btn_rpks.Bind(wx.EVT_BUTTON,   self.remove_peaks)
        hbox2_pks.Add(self.btn_rpks, flag=wx.RIGHT, border=8)

        self.btn_spks = wx.Button(self,label='Select to remove')
        self.btn_spks.Bind(wx.EVT_BUTTON,   self.edit_peaks)
        hbox2_pks.Add(self.btn_spks, flag=wx.RIGHT, border=8)
        
        self.btn_fitpks = wx.Button(self,label='Fit peaks')
        self.btn_fitpks.Bind(wx.EVT_BUTTON,   self.fit_peaks)
        hbox3_pks.Add(self.btn_fitpks, flag=wx.RIGHT, border=8)

#         self.btn_opks = wx.Button(self,label='Options')
#         self.btn_opks.Bind(wx.EVT_BUTTON,   self.peak_options)
#         hbox3_pks.Add(self.btn_opks, flag=wx.RIGHT, border=8)
        
        vbox_pks.Add(hbox1_pks, flag=wx.BOTTOM, border=8)
        vbox_pks.Add(hbox2_pks, flag=wx.BOTTOM, border=8)
        vbox_pks.Add(hbox3_pks, flag=wx.BOTTOM, border=8)
        vbox.Add(vbox_pks, flag=wx.ALL, border=10)

        self.btn_fbkgd.Disable()
        self.btn_rbkgd.Disable()
        self.ck_bkgd.Disable()
        self.btn_obkgd.Disable()
        
        self.btn_fpks.Disable()
        self.btn_opks.Disable()
        self.btn_rpks.Disable()        
        self.btn_spks.Disable()

        return vbox

    def LeftSidePanel(self,panel):
        
        vbox = wx.BoxSizer(wx.VERTICAL)

        settings = self.SettingsPanel(self)
        vbox.Add(settings,flag=wx.ALL,border=10)
        
        fittools = self.FittingTools(self)
        vbox.Add(fittools,flag=wx.ALL,border=10)

        return vbox
        
    def SettingsPanel(self,panel):

        vbox = wx.BoxSizer(wx.VERTICAL)

#         btn_chc = wx.Button(panel,label='Select data to fit')
#         btn_chc.Bind(wx.EVT_BUTTON,   None) ## ---> need a way to point to parent's function, mkak 2016.12.02
#         vbox.Add(btn_chc, flag=wx.EXPAND|wx.ALL, border=8)

        self.ttl_energy = wx.StaticText(self, label=('Energy: %0.3f keV (%0.4f A)' % (self.energy,self.wavelength)))
        vbox.Add(self.ttl_energy, flag=wx.EXPAND|wx.ALL, border=8)
        
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
#### DATA CALCULATIONS FUNCTIONS

    def plot_data(self,event=None):
        #print '[plot_data]'
        
        if self.trim:
            self.plot1D.plot(*self.raw_data, title=self.name, 
                             color='grey', label='Raw data',
                             show_legend=True)
            self.plot1D.oplot(*self.plt_data, title=self.name, 
                              color='blue', label='Trimmed data',
                              show_legend=True)
        else:
            self.plot1D.plot(*self.raw_data, title=self.name, 
                             color='blue', label='Raw data',
                             show_legend=True)

        
##############################################
#### RANGE FUNCTIONS

    def set_range(self,event=None):
        #print '[set_range]'
        
        if float(self.val_qmax.GetValue()) < float(self.val_qmin.GetValue()):
            min = float(self.val_qmax.GetValue())
            max = float(self.val_qmin.GetValue())
            self.val_qmin.SetValue('%0.3f' % min)
            self.val_qmax.SetValue('%0.3f' % max)        
        
        self.check_range()
        self.trim_data()
        if self.bgr is not None:
            self.fit_background()

        self.plot_data()
        self.plot_background()

        if self.ipeaks is not None:
            self.calc_peaks()
            self.plot_peaks()
    
    def check_range(self,event=None):
        #print '[check_range]'

        self.trim = True
        if float(self.val_qmin.GetValue()) - np.min(self.raw_data[0]) > 0.005:
            self.xmin = float(self.val_qmin.GetValue())
        else:
            self.xmin = np.min(self.raw_data[0])
            
        if np.max(self.raw_data[0]) - float(self.val_qmax.GetValue()) > 0.005:
            self.xmax = float(self.val_qmax.GetValue())
        else:
            self.xmax = np.max(self.raw_data[0])

        self.val_qmin.SetValue('%0.3f' % self.xmin)
        self.val_qmax.SetValue('%0.3f' % self.xmax)
            
        if np.max(self.raw_data[0])-self.xmax < 0.005 and self.xmin-np.min(self.raw_data[0]) < 0.005:
            self.trim = False
    
            
    def reset_range(self,event=None):
        #print '[reset_range]'
        
        self.xmin = np.min(self.raw_data[0])
        self.xmax = np.max(self.raw_data[0])
        
        self.val_qmin.SetValue('%0.3f' % self.xmin)
        self.val_qmax.SetValue('%0.3f' % self.xmax)
        
        self.trim = False
        self.trim_data()
        if self.bgr is not None:
            self.fit_background()
                    
        self.plot_data()
        self.plot_background()

        if self.ipeaks is not None:
            self.calc_peaks()
            self.plot_peaks()

    def trim_data(self):
        #print '[trim_data]'

        if self.trim:
            indicies = [i for i,value in enumerate(self.raw_data[0]) if value>=self.xmin and value<=self.xmax]
            if len(indicies) > 0:
                x = [self.raw_data[0,i] for i in indicies]
                y = [self.raw_data[1,i] for i in indicies]
                self.plt_data = np.array([x,y])
        else:
            self.plt_data = np.copy(self.raw_data)
     

##############################################
#### BACKGROUND FUNCTIONS

    def background_fit(self,event=None):        

        if self.bgr is not None:
            self.plot_data()
            if self.ipeaks is not None:
                self.calc_peaks()
                self.plot_peaks()
        self.fit_background()
        self.plot_background()

    def fit_background(self,event=None):
        #print '[fit_background]'
        
        self.delete_background()
        
        ## this creates self.bgr and self.bgr_info
        xrd_background(*self.plt_data, group=self, exponent=self.exponent, 
                           compress=self.compress, width=self.width)
   
        self.bgr_data    = np.copy(self.plt_data[:,:np.shape(self.bgr)[0]])
        self.bgr_data[1] = self.bgr
        
        self.ck_bkgd.Enable()
        self.btn_rbkgd.Enable()
  
    def remove_background(self,event=None):
        #print '[remove_background]'

        self.delete_background()
        self.plot_data()
        if self.ipeaks is not None:
            self.calc_peaks()
            self.plot_peaks()
        
        self.ck_bkgd.SetValue(False)
        self.ck_bkgd.Disable()
        self.btn_rbkgd.Disable()

        
    def delete_background(self,event=None):
        #print '[delete_background]'    
        self.bgr_data = None
        self.bgr = None
        self.bgr_info = None

    def plot_background(self,event=None):
        #print '[plot_background]'

        if self.bgr is not None:
            self.plot1D.oplot(*self.bgr_data, title=self.name, 
                              color='red', label='Background',
                              show_legend=True)

    def background_options(self,event=None):
        #print '[background_options]'
    
        myDlg = BackgroundOptions(self)
        
        fit = False
        if myDlg.ShowModal() == wx.ID_OK:
            self.exponent = int(myDlg.val_exp.GetValue())
            self.compress = int(myDlg.val_comp.GetValue())
            self.width    = int(myDlg.val_wid.GetValue())
            fit = True
        myDlg.Destroy()

        if fit:
            self.background_fit()

    def subtract_background(self,event=None):
        #print '[subtract_background]'

        if self.ck_bkgd.GetValue() == True:
            if np.shape(self.plt_data)[1] != np.shape(self.bgr_data)[1]:
                if (np.shape(self.plt_data)[1] - np.shape(self.bgr_data)[1]) > 2:
                    print '**** refitting background from subtract button'
                    self.fit_background()
                self.plt_data = self.plt_data[:,:np.shape(self.bgr_data)[1]]
            self.plt_data[1] = self.plt_data[1] - self.bgr_data[1]
            self.subtracted = True

            self.plot1D.plot(*self.plt_data, title=self.name,
                             color='blue', label='Background subtracted',
                             show_legend=True)

            self.btn_rbkgd.Disable()
            self.btn_fbkgd.Disable()
            self.btn_obkgd.Disable()
        
        else:
            if self.subtracted:
                self.plt_data[1] = self.plt_data[1] + self.bgr_data[1]
                self.subtracted = False

            self.btn_rbkgd.Enable()
            self.btn_fbkgd.Enable()
            self.btn_obkgd.Enable()
            
            self.plot_data()
            self.plot_background()

        if self.ipeaks is not None:
            self.calc_peaks()
            self.plot_peaks()

           

            
##############################################
#### PEAK FUNCTIONS

    def find_peaks(self,event=None):
        #print '[find_peaks]'
        
        ## clears previous searches
        self.delete_peaks()
        
        ttlpnts = len(self.plt_data[0])
        widths = np.arange(1,int(ttlpnts/self.iregions))
        
        self.ipeaks = signal.find_peaks_cwt(self.plt_data[1], widths,
                                           gap_thresh=self.gapthrsh)
# # #   scipy.signal.find_peaks_cwt(vector, widths, wavelet=None, max_distances=None, 
# # #                     gap_thresh=None, min_length=None, min_snr=1, noise_perc=10)

        self.calc_peaks()
        self.plot_peaks()
        
        self.btn_rpks.Enable()        
        self.btn_spks.Enable()

    def fit_peaks(self,event=None):
        #print '[fit_peaks]'
        ilmt = 50
        for i,j in enumerate(self.ipeaks):
            if j > ilmt and j < (np.shape(self.plt_data)[1]-ilmt):
                x = self.plt_data[0,(j-ilmt):(j+ilmt)]
                y = self.plt_data[1,(j-ilmt):(j+ilmt)]
                print np.min(y),np.max(y)
                if (np.max(y)/np.min(y)) > 3:
                    print 'enough!'
                    try:
                        pkpos,pkfwhm = gaussian_peak_fit(x,y,double=True,plot=True)
                        print pkpos,pkfwhm
                        print
                        print
                    except:
                        pass



    def calc_peaks(self):
        #print '[calc_peaks]'
        self.plt_peaks = np.zeros((2,len(self.ipeaks)))
        for i,j in enumerate(self.ipeaks):
            self.plt_peaks[0,i] = self.plt_data[0,j]
            self.plt_peaks[1,i] = self.plt_data[1,j]
            
    def plot_peaks(self):
        #print '[plot_peaks]'
        self.plot1D.scatterplot(*self.plt_peaks,
                          color='red',edge_color='yellow', selectcolor='green',size=12,
                          show_legend=True)
        self.plot1D.cursor_mode = 'zoom'
 
# # #   scatterplot(self, xdata, ydata, label=None, size=10, color=None, edgecolor=None,
# # #           selectcolor=None, selectedge=None, xlabel=None, ylabel=None, y2label=None,
# # #           xmin=None, xmax=None, ymin=None, ymax=None, title=None, grid=None,
# # #           callback=None, **kw):

    def remove_peaks(self,event=None):
        #print '[remove_peaks]'

        self.delete_peaks()
        self.plot_data()
        self.plot_background()

        self.btn_rpks.Disable()        
        self.btn_spks.Disable()

    def delete_peaks(self,event=None):
        #print '[delete_peaks]'
        self.peaks = None
        self.ipeaks = None

    def edit_peaks(self,event=None):
        #print '[edit_peaks]'
        print 'this will pop up a list of peaks for removing (and adding?)'

    def peak_options(self,event=None):
        #print '[peak_options]'
        myDlg = PeakOptions(self)

        fit = False
        if myDlg.ShowModal() == wx.ID_OK:
            self.iregions = int(myDlg.val_regions.GetValue())
            self.gapthrsh = int(myDlg.val_gapthr.GetValue())
            fit = True
        myDlg.Destroy()
        
        if fit:
            self.find_peaks()

##############################################
#### PLOTPANEL FUNCTIONS
    def plot1DXRD(self,panel):
    
        self.plot1D = PlotPanel(panel,size=(1000, 500))
        self.plot1D.messenger = self.owner.write_message
        

        ## Set defaults for plotting  
        self.plot1D.set_ylabel('Intensity (a.u.)')
        self.plot1D.set_xlabel('q (1/$\AA$)')  #'q (1/A)')
        self.plot1D.cursor_mode = 'zoom'

    def onSAVEfig(self,event=None):
        self.plot1D.save_figure()
        
    def onPLOTset(self,event=None):
        self.plot1D.configure()
        
    def onRESETplot(self,event=None):
        self.plot1D.reset_config()

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
        x1 = np.max(xmin,x1)
        x2 = np.min(xmax,x2)

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
            xmin, xmax = np.min(self.xy_plot[0][0]), np.max(self.xy_plot[0][0])
   
        return xmin,xmax
#######  END  #######

class BackgroundOptions(wx.Dialog):
    def __init__(self,parent):
    
        """Constructor"""
        dialog = wx.Dialog.__init__(self, None, title='Background fitting options',
                                    style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,
                                    size = (210,410))
        self.parent = parent
        
        self.Init()

        ## Set defaults
        self.val_exp.SetValue(str(self.parent.exponent))
        self.val_comp.SetValue(str(self.parent.compress))
        self.val_wid.SetValue(str(self.parent.width))
        
        ix,iy = self.panel.GetBestSize()
        self.SetSize((ix+20, iy+20))

    def Init(self):
    
        self.panel = wx.Panel(self)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        
        ## Exponent
        expsizer = wx.BoxSizer(wx.VERTICAL)

        ttl_exp = wx.StaticText(self.panel, label='EXPONENT')

        self.val_exp = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        expsizer.Add(ttl_exp,  flag=wx.RIGHT, border=5)
        expsizer.Add(self.val_exp,  flag=wx.RIGHT, border=5)

        ## Compress
        compsizer = wx.BoxSizer(wx.VERTICAL)

        ttl_comp = wx.StaticText(self.panel, label='COMPRESS')

        self.val_comp = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        compsizer.Add(ttl_comp,  flag=wx.RIGHT, border=5)
        compsizer.Add(self.val_comp,  flag=wx.RIGHT, border=5)
        
        ## Width
        widsizer = wx.BoxSizer(wx.VERTICAL)

        ttl_wid = wx.StaticText(self.panel, label='WIDTH')

        self.val_wid = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        widsizer.Add(ttl_wid,  flag=wx.RIGHT, border=5)
        widsizer.Add(self.val_wid,  flag=wx.RIGHT, border=5)


        #####
        ## OKAY!
        oksizer = wx.BoxSizer(wx.HORIZONTAL)

        hlpBtn     = wx.Button(self.panel, wx.ID_HELP   )
        self.okBtn = wx.Button(self.panel, wx.ID_OK     )
        canBtn     = wx.Button(self.panel, wx.ID_CANCEL )

        hlpBtn.Bind(wx.EVT_BUTTON, lambda(evt): wx.TipWindow(
            self, 'These values are specific to the background fitting defined in:'
            ' Nucl. Instrum. Methods (1987) B22, 78-81.\n'
            ' EXPONENT : Specifies the power of polynomial which is used.\n'
            ' COMPRESS : Compression factor to apply before fitting the background.\n'
            ' WIDTH : Specifies the width of the polynomials which are concave downward.'))

        oksizer.Add(hlpBtn,     flag=wx.RIGHT,  border=8 )
        oksizer.Add(canBtn,     flag=wx.RIGHT,  border=8 ) 
        oksizer.Add(self.okBtn, flag=wx.RIGHT,  border=8 )

        mainsizer.Add(expsizer,  flag=wx.ALL, border=8)
        mainsizer.AddSpacer(15)
        mainsizer.Add(compsizer, flag=wx.ALL, border=5)        
        mainsizer.AddSpacer(15)
        mainsizer.Add(widsizer,  flag=wx.ALL, border=8)
        mainsizer.AddSpacer(15)
        mainsizer.Add(oksizer,   flag=wx.ALL|wx.ALIGN_RIGHT, border=10) 


        self.panel.SetSizer(mainsizer)

class PeakOptions(wx.Dialog):
    def __init__(self,parent):
    
        """Constructor"""
        dialog = wx.Dialog.__init__(self, None, title='Peak searching options',
                                    style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,
                                    size = (210,410))
        self.parent = parent
        
        self.Init()

        ## Set defaults
        self.val_regions.SetValue(str(self.parent.iregions))
        self.val_gapthr.SetValue(str(self.parent.gapthrsh))
        
        ix,iy = self.panel.GetBestSize()
        self.SetSize((ix+20, iy+20))

    def Init(self):
    
        self.panel = wx.Panel(self)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        
        ##  Fit type
        fitsizer = wx.BoxSizer(wx.VERTICAL)
        
        ttl_fit = wx.StaticText(self.panel, label='Fit type')
        self.ch_pkfit = wx.Choice(self.panel,choices=FIT_METHODS)

        self.ch_pkfit.Bind(wx.EVT_CHOICE, None)
        
        fitsizer.Add(ttl_fit,  flag=wx.RIGHT, border=5)
        fitsizer.Add(self.ch_pkfit,  flag=wx.RIGHT, border=5)
        
        ## Regions
        rgnsizer = wx.BoxSizer(wx.VERTICAL)

        ttl_rgn = wx.StaticText(self.panel, label='Number of regions')
        self.val_regions = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)

        rgnsizer.Add(ttl_rgn,  flag=wx.RIGHT, border=5)
        rgnsizer.Add(self.val_regions,  flag=wx.RIGHT, border=5)

        ## Gap threshold
        gpthrsizer = wx.BoxSizer(wx.VERTICAL)

        ttl_gpthr = wx.StaticText(self.panel, label='Gap threshold')

        self.val_gapthr = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)
        gpthrsizer.Add(ttl_gpthr,  flag=wx.RIGHT, border=5)
        gpthrsizer.Add(self.val_gapthr,  flag=wx.RIGHT, border=5)
        

        #####
        ## OKAY!
        oksizer = wx.BoxSizer(wx.HORIZONTAL)

        hlpBtn     = wx.Button(self.panel, wx.ID_HELP   )
        self.okBtn = wx.Button(self.panel, wx.ID_OK     )
        canBtn     = wx.Button(self.panel, wx.ID_CANCEL )

        hlpBtn.Bind(wx.EVT_BUTTON, lambda(evt): wx.TipWindow(
            self, 'These values are specific to the built-in scipy function:'
            ' scipy.signal.find_peaks_cwt(vector, widths, wavelet=None,'
            ' max_distances=None, gap_thresh=None, min_length=None,'
            ' min_snr=1, noise_perc=10), where he number of regions defines the'
            ' width squence [widths = arange(int(len(x_axis)/regions))]'))

        oksizer.Add(hlpBtn,     flag=wx.RIGHT,  border=8)
        oksizer.Add(canBtn,     flag=wx.RIGHT, border=8) 
        oksizer.Add(self.okBtn, flag=wx.RIGHT,  border=8)

        mainsizer.Add(fitsizer,   flag=wx.ALL, border=8)
        mainsizer.AddSpacer(15)
        mainsizer.Add(rgnsizer,   flag=wx.ALL, border=8)
        mainsizer.AddSpacer(15)
        mainsizer.Add(gpthrsizer, flag=wx.ALL, border=5)        
        mainsizer.AddSpacer(15)
        mainsizer.Add(oksizer,    flag=wx.ALL|wx.ALIGN_RIGHT, border=10) 


        self.panel.SetSizer(mainsizer)

class Viewer1DXRD(wx.Panel):
    '''
    Panel for housing 1D XRD viewer
    '''
    label='Viewer'
    def __init__(self,parent,owner=None,_larch=None):
        
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.owner = owner

        ## Default information
        self.data_name    = []
        self.xy_data      = None #[]
        self.xy_plot      = None #[]
        self.plotted_data = []
        self.xy_scale     = []
        self.xlabel       = 'q (A^-1)'
        
        self.cif_name     = []
        self.cif_data     = None #[]
        self.cif_plot     = None #[]
        self.plotted_cif  = []
        self.cif_scale    = []

        self.idata        = []
        self.icif         = []
        self.icount       = 0
        
        self.x_for_zoom = None
        
        self.energy = 19.0   ## keV
        self.wavelength = HC/(self.energy)*1e10 ## A

        self.Panel1DViewer()

##############################################
#### PANEL DEFINITIONS
    def Panel1DViewer(self):
        '''
        Frame for housing all 1D XRD viewer widgets
        '''
        leftside  = self.LeftSidePanel(self)
        rightside = self.RightSidePanel(self)        

        panel1D = wx.BoxSizer(wx.HORIZONTAL)
        panel1D.Add(leftside,flag=wx.ALL,border=10)
        panel1D.Add(rightside,proportion=1,flag=wx.ALL,border=10)

        self.SetSizer(panel1D)
    
    def Toolbox(self,panel):
        '''
        Frame for visual toolbox
        '''
        
        tlbx = wx.StaticBox(self,label='PLOT TOOLBOX')
        vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)

        ###########################
        ## X-Scale
        hbox_xaxis = wx.BoxSizer(wx.HORIZONTAL)
        ttl_xaxis = wx.StaticText(self, label='X-SCALE')
        xunits = ['q','d',u'2\u03B8']
        self.ch_xaxis = wx.Choice(self,choices=xunits)

        self.ch_xaxis.Bind(wx.EVT_CHOICE, self.checkXaxis)
    
        hbox_xaxis.Add(ttl_xaxis, flag=wx.RIGHT, border=8)
        hbox_xaxis.Add(self.ch_xaxis, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_xaxis, flag=wx.ALL, border=10)

        ###########################
        ## Y-Scale
        hbox_yaxis = wx.BoxSizer(wx.HORIZONTAL)
        ttl_yaxis = wx.StaticText(self, label='Y-SCALE')
        yscales = ['linear','log']
        self.ch_yaxis = wx.Choice(self,choices=yscales)

        self.ch_yaxis.Bind(wx.EVT_CHOICE,   None)
    
        hbox_yaxis.Add(ttl_yaxis, flag=wx.RIGHT, border=8)
        hbox_yaxis.Add(self.ch_yaxis, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_yaxis, flag=wx.ALL, border=10)
        
        return vbox

    def DataBox(self,panel):
        '''
        Frame for data toolbox
        '''
        
        tlbx = wx.StaticBox(self,label='DATA TOOLBOX')
        vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)


        ###########################
        ## DATA CHOICE

        self.ch_data = wx.Choice(self,choices=self.data_name)
        self.ch_data.Bind(wx.EVT_CHOICE,   self.onSELECT)
        vbox.Add(self.ch_data, flag=wx.EXPAND|wx.ALL, border=8)

        ###########################

        ## Scale
        hbox_scl = wx.BoxSizer(wx.HORIZONTAL)
        ttl_scl = wx.StaticText(self, label='SCALE Y TO:')
        self.val_scale = wx.TextCtrl(self,wx.TE_PROCESS_ENTER)
        btn_scale = wx.Button(self,label='set')

        btn_scale.Bind(wx.EVT_BUTTON, self.normalize1Ddata)
        
        hbox_scl.Add(ttl_scl, flag=wx.RIGHT, border=8)
        hbox_scl.Add(self.val_scale, flag=wx.RIGHT, border=8)
        hbox_scl.Add(btn_scale, flag=wx.RIGHT, border=8)

        vbox.Add(hbox_scl, flag=wx.BOTTOM|wx.TOP, border=8)

        ###########################
        ## Hide/show and reset
        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_hide  = wx.Button(self,label='hide')
        btn_reset = wx.Button(self,label='reset')
        btn_rmv   = wx.Button(self,label='remove')
        
        btn_hide.Bind(wx.EVT_BUTTON,  self.hide1Ddata)
        btn_reset.Bind(wx.EVT_BUTTON, self.reset1Dscale)
        btn_rmv.Bind(wx.EVT_BUTTON,   self.remove1Ddata)

        btn_hide.Disable()
        btn_rmv.Disable()
        
        hbox_btns.Add(btn_reset, flag=wx.ALL, border=10)
        hbox_btns.Add(btn_hide,  flag=wx.ALL, border=10)
        hbox_btns.Add(btn_rmv,   flag=wx.ALL, border=10)
        vbox.Add(hbox_btns, flag=wx.ALL, border=10)
        return vbox   
        
    def CIFBox(self,panel):
        '''
        Frame for data toolbox
        '''
        
        tlbx = wx.StaticBox(self,label='CIF TOOLBOX')
        vbox = wx.StaticBoxSizer(tlbx,wx.VERTICAL)

        ###########################
        ## DATA CHOICE

        self.ch_cif = wx.Choice(self,choices=self.cif_name)
        self.ch_cif.Bind(wx.EVT_CHOICE,   self.selectCIF)
        vbox.Add(self.ch_cif, flag=wx.EXPAND|wx.ALL, border=8)

        ###########################

        ## Scale
        hbox_scl = wx.BoxSizer(wx.HORIZONTAL)
        ttl_scl = wx.StaticText(self, label='SCALE Y TO:')
        self.val_cifscale = wx.TextCtrl(self,wx.TE_PROCESS_ENTER)
        btn_scale = wx.Button(self,label='set')

        btn_scale.Bind(wx.EVT_BUTTON, partial(self.normalize1Ddata,cif=True))
        
        hbox_scl.Add(ttl_scl, flag=wx.RIGHT, border=8)
        hbox_scl.Add(self.val_cifscale, flag=wx.RIGHT, border=8)
        hbox_scl.Add(btn_scale, flag=wx.RIGHT, border=8)

        vbox.Add(hbox_scl, flag=wx.BOTTOM|wx.TOP, border=8)

        return vbox   
        

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

        settings = self.SettingsPanel(self)        
        plttools = self.Toolbox(self)
        addbtns = self.AddPanel(self)
        dattools = self.DataBox(self)
        ciftools = self.CIFBox(self)
        
        vbox.Add(settings,flag=wx.ALL,border=10)
        vbox.Add(plttools,flag=wx.ALL,border=10)
        vbox.Add(addbtns,flag=wx.ALL,border=10)
        vbox.Add(dattools,flag=wx.ALL,border=10)
        vbox.Add(ciftools,flag=wx.ALL,border=10)
        return vbox

    def RightSidePanel(self,panel):
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.plot1DXRD(panel)
        btnbox = self.QuickButtons(panel)
        vbox.Add(self.plot1D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        vbox.Add(btnbox,flag=wx.ALL|wx.ALIGN_RIGHT,border = 10)
        return vbox

        
    def SettingsPanel(self,panel):

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.ttl_energy = wx.StaticText(self, label=('Energy: %0.3f keV (%0.4f A)' % (self.energy,self.wavelength)))
        vbox.Add(self.ttl_energy, flag=wx.EXPAND|wx.ALL, border=8)
        
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
        self.plot1D.messenger = self.owner.write_message
        

        ## Set defaults for plotting  
        self.plot1D.set_ylabel('Intensity (a.u.)')
        self.plot1D.cursor_mode = 'zoom'
  
        ## trying to get this functionality into our gui
        ## mkak 2016.11.10      
#         interactive_legend().show()

    def onSAVEfig(self,event=None):
        self.plot1D.save_figure()
        
    def onPLOTset(self,event=None):
        self.plot1D.configure()
        
    def onRESETplot(self,event=None):
        self.plot1D.reset_config()



##############################################
#### XRD PLOTTING FUNCTIONS

    def addCIFdata(self,x,y,name=None):
        
        plt_no = len(self.cif_name)
        
        if name is None:
            name = 'cif %i' % plt_no
        else:
            name = 'cif: %s' % name
            
        cifscale = 1000
        y = y/np.max(y)*cifscale

        ## Add 'raw' data to array
        self.cif_name.append(name)
        self.icif.append(self.icount)
        self.icount = self.icount+1
        self.cif_scale.append(cifscale)
        if self.cif_data is None:
            self.cif_data = [[x,y]]
        else:
            self.cif_data.append([[x],[y]])
        
        ## Add 'as plotted' data to array
        if self.cif_plot is None:
            self.cif_plot = [[x,y]]
        else:
            self.cif_plot.append([[x],[y]])
        
        ## Plot data (x,y) 
        self.plotted_cif.append(self.plot1D.oplot(x,y,label=name,show_legend=True))

        ## Use correct x-axis units
        self.checkXaxis()

        self.ch_cif.Set(self.cif_name)
        self.ch_cif.SetStringSelection(name)
        
        ## Update toolbox panel, scale all cif to 1000
        self.val_cifscale.SetValue(str(self.cif_scale[plt_no]))
       
    def add1Ddata(self,x,y,name=None,cif=False):
        
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

        ## Add 'raw' data to array
        self.data_name.append(name)
        self.idata.append(self.icount)
        self.icount = self.icount+1
        self.xy_scale.append(np.max(y))
        if self.xy_data is None:
            self.xy_data = [[x,y]]
        else:
            self.xy_data.append([[x],[y]])
        
        ## Add 'as plotted' data to array
        if self.xy_plot is None:
            self.xy_plot = [[x,y]]
        else:
            self.xy_plot.append([[x],[y]])
        
        ## Plot data (x,y) 
        self.plotted_data.append(self.plot1D.oplot(x,y,label=name,show_legend=True))

        ## Use correct x-axis units
        self.checkXaxis()

        self.ch_data.Set(self.data_name)
        self.ch_data.SetStringSelection(name)
        
        ## Update toolbox panel, scale all cif to 1000
        if cif is True:
            self.val_scale.SetValue('1000')
            self.normalize1Ddata()
        else:
            self.val_scale.SetValue(str(self.xy_scale[plt_no]))

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

        self.energy = HC/(wavelength*(1e-10))*1e3

    def normalize1Ddata(self,event=None,cif=False):
    
        if cif:
            plt_no = self.ch_cif.GetSelection()
            y = self.cif_data[plt_no][1]
        
            self.cif_scale[plt_no] = float(self.val_cifscale.GetValue())
            if self.cif_scale[plt_no] <= 0:
                self.cif_scale[plt_no] = np.max(y)
                self.val_cifscale.SetValue(str(self.cif_scale[plt_no]))
            self.cif_plot[plt_no][1] = y/np.max(y) * self.cif_scale[plt_no]
        else:
            plt_no = self.ch_data.GetSelection()
            y = self.xy_data[plt_no][1]
        
            self.xy_scale[plt_no] = float(self.val_scale.GetValue())
            if self.xy_scale[plt_no] <= 0:
                self.xy_scale[plt_no] = np.max(y)
                self.val_scale.SetValue(str(self.xy_scale[plt_no]))
            self.xy_plot[plt_no][1] = y/np.max(y) * self.xy_scale[plt_no]

        self.updatePLOT()

    def remove1Ddata(self,event=None):
        
        ## Needs pop up warning: "Do you really want to delete this data set from plotter?
        ## Current settings will not be saved."
        ## mkak 2016.11.10
        
        plt_no = self.ch_data.GetSelection()        
        print('EVENTUALLY, button will remove plot: %s' % self.data_name[plt_no])

        ## removing name from list works... do not activate till rest is working
        ## mkak 2016.11.10
#         self.data_name.remove(self.data_name[plt_no])
#         self.ch_data.Set(self.data_name)

    def hide1Ddata(self,event=None):

        plt_no = self.ch_data.GetSelection()        
        print('EVENTUALLY, button will hide plot: %s' % self.data_name[plt_no])

    def onSELECT(self,event=None):
    
        data_str = self.ch_data.GetString(self.ch_data.GetSelection())
        
        plt_no = self.ch_data.GetSelection()
        self.val_scale.SetValue(str(self.xy_scale[plt_no]))

    def selectCIF(self,event=None):
    
        cif_str = self.ch_cif.GetString(self.ch_cif.GetSelection())
        
        plt_no = self.ch_cif.GetSelection()
        self.val_cifscale.SetValue(str(self.cif_scale[plt_no]))

    def checkXaxis(self,event=None):
        
        if self.ch_xaxis.GetSelection() == 2:
            self.xlabel = r'$2\Theta$'+r' $(^\circ)$'
            for plt_no in range(len(self.plotted_data)):
                self.xy_plot[plt_no][0] = calc_q_to_2th(np.array(self.xy_data[plt_no][0]),self.wavelength)
            for plt_no in range(len(self.plotted_cif)):
                self.cif_plot[plt_no][0] = calc_q_to_2th(np.array(self.cif_data[plt_no][0]),self.wavelength)
        elif self.ch_xaxis.GetSelection() == 1:
            self.xlabel = 'd ($\AA$)'
            for plt_no in range(len(self.plotted_data)):
                self.xy_plot[plt_no][0] = calc_q_to_d(np.array(self.xy_data[plt_no][0]))
            for plt_no in range(len(self.plotted_cif)):
                self.cif_plot[plt_no][0] = calc_q_to_d(np.array(self.cif_data[plt_no][0]))
        else:
            self.xlabel = 'q (1/$\AA$)'
            for plt_no in range(len(self.plotted_data)):
                self.xy_plot[plt_no][0] = np.array(self.xy_data[plt_no][0])
            for plt_no in range(len(self.plotted_cif)):
                self.cif_plot[plt_no][0] = np.array(self.cif_data[plt_no][0])

        self.plot1D.set_xlabel(self.xlabel)
        self.updatePLOT()


    def updatePLOT(self):

        xmax,xmin,ymax,ymin = None,0,None,0
        

        for i,plt_no in enumerate(self.icif):
            x = np.array(self.cif_plot[i][0])
            y = np.array(self.cif_plot[i][1])

            self.plot1D.update_line(plt_no,x,y)

        for i,plt_no in enumerate(self.idata):
            x = np.array(self.xy_plot[i][0])
            y = np.array(self.xy_plot[i][1])

            if xmax is None or xmax < np.max(x):
                xmax = np.max(x)
            if xmin > np.min(x):
                xmin = np.min(x)
            if ymax is None or ymax < np.max(y):
                ymax = np.max(y)
            if ymin > np.min(y):
                ymin = np.min(y)

            self.plot1D.update_line(plt_no,x,y)

        self.unzoom_all()
        self.plot1D.canvas.draw()

        if len(self.plotted_data) > 0:
            if self.ch_xaxis.GetSelection() == 1:
                xmax = 5
            self.plot1D.set_xylims([xmin, xmax, ymin, ymax])

    def reset1Dscale(self,event=None):

        plt_no = self.ch_data.GetSelection()        
       
        self.xy_plot[plt_no][1] = self.xy_data[plt_no][1]
        self.plot1D.update_line(int(self.idata[plt_no]),
                                np.array(self.xy_plot[plt_no][0]),
                                np.array(self.xy_plot[plt_no][1]))
        self.plot1D.canvas.draw()
        self.unzoom_all()
        
        self.updatePLOT()
        self.xy_scale[plt_no] = np.max(self.xy_data[plt_no][1])
        self.val_scale.SetValue(str(self.xy_scale[plt_no]))

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
            xmin, xmax = np.min(self.xy_plot[0][0]), np.max(self.xy_plot[0][0])
        elif len(self.cif_name) > 0:
            xmin, xmax = np.min(self.cif_plot[0][0]), np.max(self.cif_plot[0][0])
   
        return xmin,xmax
#######  END  #######
       

##############################################
#### XRD FILE OPENING/SAVING 
    def loadXYFILE(self,event=None):
    
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
               print('incorrect xy file format: %s' % os.path.split(path)[-1])



    def saveXYFILE(self,event=None):
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
            ## mkak 2016.11.16
            print('need to write something to save data - like pyFAI does?')

    def loadCIF(self,event=None):
    
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
                print('incorrect file format: %s' % os.path.split(path)[-1])
                return

            ## generate hkl list
            hkllist = generate_hkl(maxhkl=8)
            
            if self.wavelength is not None:
                qlist = cif.Q(hkllist)
                Flist = cif.StructureFactorForQ(qlist,(HC/(self.wavelength*(1e-10))*1e3))
            
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
                    # self.add1Ddata(qall,Fall,name=os.path.split(path)[-1],cif=True)
                    self.addCIFdata(qall,Fall,name=os.path.split(path)[-1])
                else:
                    print('Could not calculate real structure factors.')
            else:
                print('Wavelength/energy must be specified for structure factor calculations.')

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
        
        ix,iy = self.panel.GetBestSize()
        self.SetSize((ix+20, iy+20))

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



        ## X-Range
        xsizer = wx.BoxSizer(wx.VERTICAL)
        
        ttl_xrange = wx.StaticText(self.panel, label='X-RANGE')
        
        self.xunitsizer = wx.BoxSizer(wx.HORIZONTAL)
        xunits = ['q','d',u'2\u03B8']
        ttl_xunit = wx.StaticText(self.panel, label='units')
        self.ch_xunit = wx.Choice(self.panel,choices=xunits)
        self.ch_xunit.Bind(wx.EVT_CHOICE,None)#self.onUnits)
        
        self.xunitsizer.Add(ttl_xunit, flag=wx.RIGHT, border=5)
        self.xunitsizer.Add(self.ch_xunit, flag=wx.RIGHT, border=5)

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
        xsizer.Add(self.xunitsizer, flag=wx.TOP|wx.BOTTOM, border=5)
        xsizer.Add(xstepsizer, flag=wx.TOP|wx.BOTTOM, border=5)
        xsizer.Add(xminsizer,  flag=wx.TOP|wx.BOTTOM, border=5)
        xsizer.Add(xmaxsizer,  flag=wx.TOP|wx.BOTTOM, border=5)

        ## Plot/save

        self.ch_save = wx.CheckBox(self.panel, label = 'Save 1D?')
        self.ch_plot  = wx.CheckBox(self.panel, label = 'Plot 1D?')
        
        self.ch_save.Bind(wx.EVT_CHECKBOX, self.onCHECK)
        self.ch_plot.Bind(wx.EVT_CHECKBOX, self.onCHECK)

        minisizer = wx.BoxSizer(wx.VERTICAL)
        minisizer.Add(self.ch_save,  flag=wx.RIGHT, border=5)
        minisizer.Add(self.ch_plot,  flag=wx.RIGHT, border=5)

        #####
        ## OKAY!
        oksizer = wx.BoxSizer(wx.HORIZONTAL)
        #hlpBtn = wx.Button(self.panel, wx.ID_HELP    )
        self.okBtn  = wx.Button(self.panel, wx.ID_OK      )
        canBtn = wx.Button(self.panel, wx.ID_CANCEL  )

        #oksizer.Add(hlpBtn,flag=wx.RIGHT,  border=8)
        oksizer.Add(canBtn, flag=wx.RIGHT, border=8) 
        oksizer.Add(self.okBtn,  flag=wx.RIGHT,  border=8)

        mainsizer.Add(wedgesizer, flag=wx.ALL, border=8)
        mainsizer.AddSpacer(15)
        mainsizer.Add(ysizer,     flag=wx.ALL, border=5)        
        mainsizer.AddSpacer(15)
        mainsizer.Add(xsizer,     flag=wx.ALL, border=5)        
        mainsizer.AddSpacer(15)
        mainsizer.Add(minisizer,  flag=wx.ALL, border=8)
        mainsizer.AddSpacer(15)
        mainsizer.Add(oksizer,    flag=wx.ALL|wx.ALIGN_RIGHT, border=10) 


        self.panel.SetSizer(mainsizer)
        

    def onCHECK(self,event=None):
    
        if self.ch_save.GetValue() or self.ch_plot.GetValue():
           self.okBtn.Enable()
        else:
            self.okBtn.Disable()
        
    def setDefaults(self):

        self.ymin.SetValue(str(0))
        self.ymax.SetValue(str(10000))
        self.xstep.SetValue(str(5001))
        self.xmin.SetValue(str(0.1))
        self.xmax.SetValue(str(5.5))
        self.wedges.SetValue(str(1))
        
        self.wedge_arrow.SetRange(1, 10)
        self.wedge_arrow.SetValue(1)
        self.okBtn.Disable()

        self.ymin.Disable()
        self.ymax.Disable()
        self.xmin.Disable()
        self.xmax.Disable()
        self.wedges.Disable()
        self.wedge_arrow.Disable()
        self.ch_xunit.Disable()
        
#     def onUnits(self,event=None):
# 
#         if self.slctEorL.GetSelection() == 1:
#             energy = float(self.EorL.GetValue()) ## units keV
#             wavelength = HC/(energy)*1e10 ## units: A
#             self.EorL.SetValue(str(wavelength))
#         else:
#             wavelength = float(self.EorL.GetValue())*1e-10 ## units: m
#             energy = HC/(wavelength) ## units: keV
#             self.EorL.SetValue(str(energy))

    def onSPIN(self, event):
        self.wedges.SetValue(str(event.GetPosition())) 
        print('WARNING: not currently using multiple wedges for calculations')

    def getValues(self):
    
        self.steps = int(self.xstep.GetValue())
    
class SetLambdaDialog(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self,energy=19.0):
    
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
        main.Add(hmain2, flag=wx.ALL|wx.ALIGN_RIGHT, border=10) 

        panel.SetSizer(main)

        self.Show()
        ix,iy = panel.GetBestSize()
        self.SetSize((ix+20, iy+20))
        
        ## set default
        self.energy = energy      
        self.wavelength = HC/(self.energy)*1e10 ## units: A
        self.ch_EorL.SetSelection(0)
        self.entr_EorL.SetValue('%0.3f' % self.energy)
        self.pre_sel = 0

    def onEorLSel(self,event=None): 
        
        if float(self.entr_EorL.GetValue()) < 0 or self.entr_EorL.GetValue() == '':
            self.ch_EorL.SetSelection(1)
            self.entr_EorL.SetValue('19.0')     ## 19.0 keV
            return
        
        if self.pre_sel == self.ch_EorL.GetSelection():
            if self.ch_EorL.GetSelection() == 0:
                self.energy = float(self.entr_EorL.GetValue()) ## units keV
                self.wavelength = HC/(self.energy)*1e10 ## units: A
            else:
                self.wavelength = float(self.entr_EorL.GetValue()) ## units: A
                self.energy = HC/(self.wavelength*1e-10) ## units: keV
        else:
            if self.ch_EorL.GetSelection() == 0:
                self.wavelength = float(self.entr_EorL.GetValue()) ## units: A
                self.energy = HC/(self.wavelength*1e-10) ## units: keV
                self.entr_EorL.SetValue('%0.3f' % self.energy)
            else:
                self.energy = float(self.entr_EorL.GetValue()) ## units keV
                self.wavelength = HC/(self.energy)*1e10 ## units: A
                self.entr_EorL.SetValue('%0.4f' % self.wavelength)
            self.pre_sel = self.ch_EorL.GetSelection()
      
class diFFit1D(wx.App):
    def __init__(self):
        wx.App.__init__(self)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = diFFit1DFrame()
        #frame = Viewer1DXRD()
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
