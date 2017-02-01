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
import wx.lib.agw.flatnotebook as flat_nb

from wxmplot import PlotPanel
from wxmplot.basepanel import BasePanel
from wxutils import MenuItem,pack,EditableListBox,SimpleText

from larch_plugins.diFFit.cifdb import cifDB

from larch_plugins.io import tifffile

from larch_plugins.diFFit.XRDCalculations import d_from_q,twth_from_q
from larch_plugins.diFFit.XRDCalculations import lambda_from_E,E_from_lambda
from larch_plugins.diFFit.XRDCalculations import xy_file_reader
from larch_plugins.diFFit.XRDCalculations import peakfinder,peaklocater,peakfitter,peakfilter
from larch_plugins.diFFit.XRDCalculations import generate_hkl
from larch_plugins.diFFit.XRDCalculations import instrumental_fit_uvw
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

VERSION = '0 (9-January-2017)'

SLIDER_SCALE = 1000. ## sliders step in unit 1. this scales to 0.001

FIT_METHODS = ['scipy.signal.find_peaks_cwt']

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

CEN = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
RIGHT = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
ALL_CEN =  wx.ALL|CEN
ALL_LEFT =  wx.ALL|LEFT
ALL_RIGHT =  wx.ALL|RIGHT
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
        
        self.openDB(dbname='amcsd_cif.db')
        #self.cifdatabase = cifDB(dbname='amcsd_cif.db')

        # create the page windows as children of the notebook
        self.xrd1Dviewer  = Viewer1DXRD(self.nb,owner=self)
        self.xrd1Dfitting = Fitting1DXRD(self.nb,owner=self)
        self.xrddatabase  = DatabaseXRD(self.nb,owner=self)
        
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
        self.wavelength = lambda_from_E(self.energy)

    def closeDB(self,event=None):
    
        self.cifdatabase.close()
        del self.cifdatabase
        
    def openDB(self,dbname='amcsd_cif.db'):
    
        try:
            self.closeDB()
        except:
            pass

        self.cifdatabase = cifDB(dbname=dbname)
        

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
        AnalyzeMenu.AppendSeparator()
        MenuItem(self, AnalyzeMenu, '&Fit instrumental broadening coefficients', '', self.xrd1Dfitting.fit_instrumental)

        menubar.Append(AnalyzeMenu, '&Analyze')

        ###########################
        ## Create Menu Bar
        self.SetMenuBar(menubar)

    def write_message(self, s, panel=0):
        '''write a message to the Status Bar'''
        self.statusbar.SetStatusText(s, panel)

    def fit1Dxrd(self,event=None):
    
        indicies = [i for i,name in enumerate(self.xrd1Dviewer.data_name) if 'cif' not in name]
        index = 0
        
        if len(indicies) > 0:
            self.list = [self.xrd1Dviewer.data_name[i] for i in indicies]
            self.all_data = self.xrd1Dviewer.xy_data
            
            dlg = SelectFittingData(self.list,self.all_data)

            okay = False
            if dlg.ShowModal() == wx.ID_OK:
                okay = True
                self.list = dlg.list
                self.all_data = dlg.all_data
            dlg.Destroy()
            if okay:
                name = self.list[index]
                q    = np.array(self.all_data[index][0]).flatten()
                d    = np.array(self.all_data[index][1]).flatten()
                twth = np.array(self.all_data[index][2]).flatten()
                I    = np.array(self.all_data[index][3]).flatten()
                
        else:
            x,y,name = self.loadXYFILE()

            ## Add 'raw' data to array
            self.xrd1Dviewer.data_name.append(name)
            self.xrd1Dviewer.idata.append(len(self.xrd1Dviewer.plotlist))
            self.xrd1Dviewer.xy_scale.append(np.max(y))
            
            q    = x
            d    = d_from_q(q)
            twth = twth_from_q(q,self.wavelength)
            I    = y
            self.xrd1Dviewer.xy_data.append([q,d,twth,y])
            self.xrd1Dviewer.xy_plot.append([q,d,twth,y])
            
            ## Add to plot       
            xi = self.xrd1Dviewer.ch_xaxis.GetSelection()
            self.xrd1Dviewer.plotlist.append(self.xrd1Dviewer.plot1D.oplot(self.xrd1Dviewer.xy_plot[-1][xi],
                                                                           self.xrd1Dviewer.xy_plot[-1][3],
                                                                           label=name,show_legend=True))

            self.xrd1Dviewer.ch_data.Set(self.xrd1Dviewer.data_name)
            self.xrd1Dviewer.ch_data.SetStringSelection(name)
            self.xrd1Dviewer.val_scale.SetValue(str(np.max(y)))
        
        self.nb.SetSelection(1) ## switches to fitting panel

        adddata = True
        if self.xrd1Dfitting.raw_data is not None:
            question = 'Do you want to replace current data file %s with selected file %s?' % (self.xrd1Dfitting.name,name)
            adddata = YesNo(self,question,caption='Overwrite warning')
        
        if adddata:

            self.xrd1Dfitting.raw_data = np.array([q,d,twth,I])
            self.xrd1Dfitting.plt_data = np.array([q,d,twth,I])
            
            xi = self.xrd1Dviewer.ch_xaxis.GetSelection()
            self.xrd1Dfitting.rngpl.ch_xaxis.SetSelection(xi)
            
            self.xrd1Dfitting.xmin     = np.min(self.xrd1Dfitting.plt_data[xi])
            self.xrd1Dfitting.xmax     = np.max(self.xrd1Dfitting.plt_data[xi])
            

            self.xrd1Dfitting.plot1D.plot(self.xrd1Dfitting.plt_data[xi],
                                          self.xrd1Dfitting.plt_data[3],
                                          title=name, color='blue', label='Raw data',
                                          show_legend=True)
            minx = np.min(self.xrd1Dfitting.plt_data[xi])
            maxx = np.max(self.xrd1Dfitting.plt_data[xi])
            self.xrd1Dfitting.reset_fitting(name=name,min=minx,max=maxx)

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
            
            energy = E_from_lambda(ai._wavelength,lambda_units='m')
            self.setELvalues(energy,(ai._wavelength*1e10))

    def setLAMBDA(self,event=None):

        dlg = SetLambdaDialog(energy=self.energy)

        path, okay = None, False
        if dlg.ShowModal() == wx.ID_OK:
            okay = True
            if dlg.ch_EorL.GetSelection() == 0:
                energy = float(dlg.entr_EorL.GetValue()) ## units keV
                wavelength = lambda_from_E(energy) ## units: A
            elif dlg.ch_EorL.GetSelection() == 1:
                wavelength = float(dlg.entr_EorL.GetValue()) ## units: A
                energy = E_from_lambda(wavelength) ## units: keV
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
    def __init__(self,parent,owner=None,_larch=None):
        """"""
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.owner = owner

        self.createAndLayout()
        
    def createDATABASEarray(self):
    
        return self.owner.cifdatabase.create_array(maxrows=50)

    
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

class Fitting1DXRD(BasePanel):
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
        self.peaklist   = []
        
        self.trim       = False
        self.indicies   = None    
        
        self.subtracted = False  

        self.xmin       = None
        self.xmax       = None

        self.name       = ''
        self.energy     = 19.0   ## keV
        self.wavelength = lambda_from_E(self.energy) ## A
        
        self.SetFittingDefaults()
        self.Panel1DFitting()
        
    def SetFittingDefaults(self):

        # Peak fitting defaults
        self.iregions = 20
        self.gapthrsh = 5
        self.halfwidth = 40
        self.intthrsh = 100
        
        # Background fitting defaults
        self.exponent   = 20
        self.compress   = 2
        self.width      = 4

     
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


    def createFittingPanels(self,parent):
        
        pattern_title    = SimpleText(parent, 'DATA FITTING', size=(200, -1))
        #self.pnb = flat_nb.FlatNotebook(parent, wx.ID_ANY, agwStyle=FNB_STYLE)
        self.pnb = wx.Notebook(parent)
        self.pnbpanels = []
        for creator in (DatabasePanel, RefinementPanel, ResultsPanel):
            #p = creator(parent, owner=self)
            p = creator(self.pnb, owner=self)
            self.pnb.AddPage(p,p.label.title(),True)
            self.pnbpanels.append(p)
            p.SetSize((300,600))

        self.pnb.SetSelection(0)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(pattern_title, 0, ALL_CEN)
        sizer.Add(self.pnb,1, wx.ALL|wx.EXPAND)
        parent.SetSize((300,600))
        pack(parent,sizer)

    
    def FittingTools(self,panel):
        '''
        Frame for visual toolbox
        '''
        
        vbox = wx.BoxSizer(wx.VERTICAL)

        fitting_panel = wx.Panel(panel)
        self.createFittingPanels(fitting_panel)
        vbox.Add(fitting_panel, flag=wx.ALL, border=10) 

        return vbox


    def createPatternPanels(self,parent):
        
        pattern_title    = SimpleText(parent, 'PATTERN PROCESSING', size=(200, -1))
        #self.pnb = flat_nb.FlatNotebook(parent, wx.ID_ANY, agwStyle=FNB_STYLE)
        self.pnb = wx.Notebook(parent)
        self.pnbpanels = []
        
#         for creator in (RangeToolsPanel, BackgroundToolsPanel, PeakToolsPanel):
#             #p = creator(parent, owner=self)
#             p = creator(self.pnb, owner=self)
#             self.pnb.AddPage(p,p.label.title(),True)
#             self.pnbpanels.append(p)
#             p.SetSize((300,600))
        self.rngpl = RangeToolsPanel(self.pnb, owner=self)
        self.bkgdpl = BackgroundToolsPanel(self.pnb, owner=self)
        self.pkpl = PeakToolsPanel(self.pnb, owner=self)
        for p in (self.rngpl, self.bkgdpl, self.pkpl):
            self.pnb.AddPage(p,p.label.title(),True)
            self.pnbpanels.append(p)
            p.SetSize((300,600))


        self.pnb.SetSelection(0)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(pattern_title, 0, ALL_CEN)
        sizer.Add(self.pnb,1, wx.ALL|wx.EXPAND)
        parent.SetSize((300,600))
        pack(parent,sizer)
        
        
    def PatternTools(self,panel):
        '''
        Frame for visual toolbox
        '''

        vbox = wx.BoxSizer(wx.VERTICAL)

        pattern_panel = wx.Panel(panel)
        self.createPatternPanels(pattern_panel)
        vbox.Add(pattern_panel, flag=wx.ALL, border=10) 

        return vbox


    def LeftSidePanel(self,panel):
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        pattools = self.PatternTools(self)
        vbox.Add(pattools,flag=wx.ALL,border=10)
        
        btn_db = wx.Button(self,label='Select database file')
        btn_db.Bind(wx.EVT_BUTTON,   self.open_database)
        vbox.Add(btn_db, flag=wx.LEFT,  border=25)
        
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
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        self.plot1DXRD(panel)
        
        settings = self.SettingsPanel(self)
        btnbox = self.QuickButtons(panel)
        
        vbox.Add(self.plot1D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        hbox.Add(settings,flag=wx.RIGHT,border=10)
        hbox.Add(btnbox,flag=wx.LEFT,border = 1)
        vbox.Add(hbox,flag=wx.ALL|wx.ALIGN_RIGHT,border = 10)
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
        
        xi = self.rngpl.ch_xaxis.GetSelection()
        if self.subtracted:
            self.plot1D.plot(self.plt_data[xi],self.plt_data[3],
                             title=self.name, 
                             color='blue', label='Data',
                             show_legend=True)
        else:
            if self.trim:
                self.plot1D.plot(self.raw_data[xi],self.raw_data[3],
                                 title=self.name, 
                                 color='grey', label='Raw data',
                                 show_legend=True)
                self.plot1D.oplot(self.plt_data[xi],self.plt_data[3],
                                  title=self.name, 
                                  color='blue', label='Trimmed data',
                                  show_legend=True)
            else:
                self.plot1D.plot(self.raw_data[xi],self.raw_data[3],
                                 title=self.name, 
                                 color='blue', label='Raw data',
                                 show_legend=True)
            self.plot_background()

        
##############################################
#### RANGE FUNCTIONS

    def reset_fitting(self,name=None,min=0,max=1):


        self.name = name
        self.rngpl.val_qmin.SetValue('%0.3f' % min)
        self.rngpl.val_qmax.SetValue('%0.3f' % max)
        self.rngpl.ch_xaxis.SetSelection(0)
        self.bkgdpl.ck_bkgd.SetValue(False)
        self.bkgdpl.btn_fbkgd.Enable()
        self.bkgdpl.btn_rbkgd.Disable()
        self.bkgdpl.ck_bkgd.Disable()
        self.bkgdpl.btn_obkgd.Enable()
        self.pkpl.btn_fpks.Enable()
        self.pkpl.btn_opks.Enable()    
   
        self.delete_all_peaks()
        self.delete_background()  
        
        self.trim       = False
        self.indicies   = None      

        self.xmin       = min
        self.xmax       = max

        self.SetFittingDefaults()
        
        self.check1Daxis()

    def set_range(self,event=None):
        
        if self.xmax != float(self.rngpl.val_qmax.GetValue()) or self.xmin != float(self.rngpl.val_qmin.GetValue()):

            if float(self.rngpl.val_qmax.GetValue()) < float(self.rngpl.val_qmin.GetValue()):
                min = float(self.rngpl.val_qmax.GetValue())
                max = float(self.rngpl.val_qmin.GetValue())
                self.rngpl.val_qmin.SetValue('%0.3f' % min)
                self.rngpl.val_qmax.SetValue('%0.3f' % max)
        
            self.check_range()
            self.trim_data()
        
            self.delete_background()
            self.remove_all_peaks()
        
            self.plot_data()
    
    def check_range(self,event=None):

        xi = self.rngpl.ch_xaxis.GetSelection()
        self.trim = True
        if float(self.rngpl.val_qmin.GetValue()) - np.min(self.raw_data[xi]) > 0.005:
            self.xmin = float(self.rngpl.val_qmin.GetValue())
        else:
            self.xmin = np.min(self.raw_data[xi])
            
        if np.max(self.raw_data[xi]) - float(self.rngpl.val_qmax.GetValue()) > 0.005:
            self.xmax = float(self.rngpl.val_qmax.GetValue())
        else:
            self.xmax = np.max(self.raw_data[xi])
        if xi == 1: self.xmax = min(self.xmax,5)

        self.rngpl.val_qmin.SetValue('%0.3f' % self.xmin)
        self.rngpl.val_qmax.SetValue('%0.3f' % self.xmax)
            
        if np.max(self.raw_data[xi])-self.xmax < 0.005 and self.xmin-np.min(self.raw_data[xi]) < 0.005:
            self.trim = False
    
            
    def reset_range(self,event=None):
        
        xi = self.rngpl.ch_xaxis.GetSelection()
        self.xmin = np.min(self.raw_data[xi])
        self.xmax = np.max(self.raw_data[xi])
        if xi == 1: self.xmax = min(self.xmax,5)
        
        self.rngpl.val_qmin.SetValue('%0.3f' % self.xmin)
        self.rngpl.val_qmax.SetValue('%0.3f' % self.xmax)
        
        self.trim = False
        self.trim_data()
        if self.bgr is not None:
            self.fit_background()
                    
        self.plot_data()

        if self.ipeaks is not None:
            self.ipeaks     = None
            self.plt_peaks  = None  
            self.peaklist   = []

    def trim_data(self):

        if self.trim:
            xi = self.rngpl.ch_xaxis.GetSelection()
            indicies = [i for i,value in enumerate(self.raw_data[xi]) if value>=self.xmin and value<=self.xmax]
            if len(indicies) > 0:
                q    = [self.raw_data[0,i] for i in indicies]
                d    = [self.raw_data[1,i] for i in indicies]
                twth = [self.raw_data[2,i] for i in indicies]
                I    = [self.raw_data[3,i] for i in indicies]
                self.plt_data = np.array([q,d,twth,I])
            else:
                self.plt_data = np.copy(self.raw_data)
                self.reset_range()
        else:
            self.plt_data = np.copy(self.raw_data)
     

##############################################
#### BACKGROUND FUNCTIONS

    def background_fit(self,event=None):        

        if self.bgr is not None:
            self.plot_data()
            if self.ipeaks is not None:
                xi = self.rngpl.ch_xaxis.GetSelection()
                self.plt_peaks = peaklocater(self.ipeaks,self.plt_data[xi],self.plt_data[3])
                self.plot_peaks()
        self.fit_background()
        self.plot_background()

    def fit_background(self,event=None):
        
        self.delete_background()
        
        ## this creates self.bgr and self.bgr_info
        xi = self.rngpl.ch_xaxis.GetSelection()
        xrd_background(self.plt_data[xi],self.plt_data[3], group=self, exponent=self.exponent, 
                           compress=self.compress, width=self.width)
   
        self.bgr_data    = np.copy(self.plt_data[:,:np.shape(self.bgr)[0]])

        self.bgr_data[3] = self.bgr
        
        self.bkgdpl.ck_bkgd.Enable()
        self.bkgdpl.btn_rbkgd.Enable()
  
    def remove_background(self,event=None):

        self.delete_background()
        self.plot_data()
        if self.ipeaks is not None:
            xi = self.rngpl.ch_xaxis.GetSelection()
            self.plt_peaks = peaklocater(self.ipeaks,self.plt_data[xi],self.plt_data[3])
            self.plot_peaks()
        
    def delete_background(self,event=None):

        self.bgr_data = None
        self.bgr = None
        self.bgr_info = None
        self.subtracted = False
        
        try:
            self.bkgdpl.ck_bkgd.SetValue(False)
            self.bkgdpl.ck_bkgd.Disable()
            self.bkgdpl.btn_rbkgd.Disable()
            self.bkgdpl.btn_fbkgd.Enable()
        except:
            pass

    def plot_background(self,event=None):

        if self.bgr is not None and self.subtracted is False:
            xi = self.rngpl.ch_xaxis.GetSelection()
            self.plot1D.oplot(self.bgr_data[xi],self.bgr_data[3],
                              title=self.name, 
                              color='red', label='Background',
                              show_legend=True)

    def background_options(self,event=None):

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

        xi = self.rngpl.ch_xaxis.GetSelection()
        if self.bkgdpl.ck_bkgd.GetValue() == True:
            if np.shape(self.plt_data)[-1] != np.shape(self.bgr_data)[-1]:
                if (np.shape(self.plt_data)[-1] - np.shape(self.bgr_data)[-1]) > 2:
                    #print '**** refitting background from subtract button'
                    self.fit_background()
                self.plt_data = self.plt_data[:,:np.shape(self.bgr_data)[-1]]
            self.plt_data[3] = self.plt_data[3] - self.bgr_data[3]
            self.subtracted = True
            
            self.plot1D.plot(self.plt_data[xi],self.plt_data[3], title=self.name,
                             color='blue', label='Background subtracted',
                             show_legend=True)

#             self.bkgdpl.btn_rbkgd.Disable()
            self.bkgdpl.btn_fbkgd.Disable()
            self.bkgdpl.btn_obkgd.Disable()
        
        else:
            if self.subtracted:
                self.plt_data[3] = self.plt_data[3] + self.bgr_data[3]
                self.subtracted = False

            self.bkgdpl.btn_rbkgd.Enable()
            self.bkgdpl.btn_fbkgd.Enable()
            self.bkgdpl.btn_obkgd.Enable()
            
            self.plot_data()
            #self.plot_background()

        if self.ipeaks is not None:
            self.plt_peaks = peaklocater(self.ipeaks,self.plt_data[xi],self.plt_data[3])
            self.plot_peaks()

           

            
##############################################
#### PEAK FUNCTIONS

    def find_peaks(self,event=None,filter=False):

        newpeaks = True
        if self.ipeaks is not None:
            question = 'Are you sure you want to remove current peaks and search again?'
            newpeaks = YesNo(self,question,caption='Replace peaks warning')
        
        if newpeaks:
            xi = self.rngpl.ch_xaxis.GetSelection()
            
            ## clears previous searches
            self.remove_all_peaks()

            self.ipeaks = peakfinder(self.plt_data[xi],self.plt_data[3],
                                     regions=self.iregions,
                                     gapthrsh=self.gapthrsh)
        
        
            if filter:
                self.intthrsh = int(self.pkpl.val_intthr.GetValue())
                self.ipeaks = peakfilter(self.intthrsh,self.ipeaks,self.plt_data[3])
            
            self.peak_display()
        

            self.plot_data()
            self.plot_peaks()
        
            self.pkpl.btn_rpks.Enable()        
            self.pkpl.btn_fitpks.Enable()
            
    def peak_display(self):
    
        xi = self.rngpl.ch_xaxis.GetSelection()
        self.plt_peaks = peaklocater(self.ipeaks,self.plt_data[xi],self.plt_data[3])
        
        self.peaklist = []
        self.peaklistbox.Clear()
        
        str = 'Peak (%6d @ %2.3f )'
        for i,ii in enumerate(self.ipeaks):
            peakname = str % (self.plt_peaks[1,i],self.plt_peaks[0,i])
            self.peaklist += [peakname]
            self.peaklistbox.Append(peakname)
        self.pkpl.ttl_cntpks.SetLabel('Total: %i peaks' % (len(self.ipeaks)))

    def fit_instrumental(self,event=None):

        xi = self.rngpl.ch_xaxis.GetSelection()
        u,v,w = instrumental_fit_uvw(self.ipeaks,
                                     self.plt_data[xi],self.plt_data[3],
                                     wavelength=self.wavelength,
                                     halfwidth=self.halfwidth,
                                     verbose=True)

    def fit_peaks(self,event=None):

        peaktwth,peakFWHM,peakinty = peakfitter(self.ipeaks,
                                                self.plt_data[0],self.plt_data[3],
                                                wavelength=self.wavelength,
                                                halfwidth=self.halfwidth,
                                                fittype='double',
                                                verbose=True)
        print('\nFit results:')
        for i,(twthi,fwhmi,inteni) in enumerate(zip(peaktwth,peakFWHM,peakinty)):
            print('Peak %i @ %0.2f deg. (fwhm %0.3f deg, %i counts)' % (i,twthi,fwhmi,inteni))
        print

    def plot_peaks(self):
        
        self.plot1D.scatterplot(*self.plt_peaks,
                          color='red',edge_color='yellow', selectcolor='green',size=12,
                          show_legend=True)
        self.plot1D.cursor_mode = 'zoom'
 
# # #   scatterplot(self, xdata, ydata, label=None, size=10, color=None, edgecolor=None,
# # #           selectcolor=None, selectedge=None, xlabel=None, ylabel=None, y2label=None,
# # #           xmin=None, xmax=None, ymin=None, ymax=None, title=None, grid=None,
# # #           callback=None, **kw):

    def remove_all_peaks(self,event=None):

        self.delete_all_peaks()
        self.plot_data()

        self.pkpl.btn_rpks.Disable()        
#         self.btn_spks.Disable()
        self.pkpl.btn_fitpks.Disable()

    def delete_all_peaks(self,event=None):

        self.plt_peaks = None
        self.ipeaks = None
        # self.peaklistbox.Destroy()
        self.peaklist = []
        self.peaklistbox.Clear()
        self.pkpl.ttl_cntpks.SetLabel('Total: 0 peaks')

    def edit_peaks(self,event=None):

        print 'this will pop up a list of peaks for removing (and adding?)'

    def peak_options(self,event=None):

        myDlg = PeakOptions(self)

        fit = False
        if myDlg.ShowModal() == wx.ID_OK:
            self.iregions  = int(myDlg.val_regions.GetValue())
            self.gapthrsh  = int(myDlg.val_gapthr.GetValue())
            self.halfwidth = int(myDlg.val_hw.GetValue())
#             self.intthrsh  = int(myDlg.val_intthr.GetValue())
            fit = True
        myDlg.Destroy()
        
        if fit:
            self.find_peaks(filter=True)

    def select_peak(self, evt=None, peakname=None,  **kws):

        if peakname is None and evt is not None:
            peakname = evt.GetString()
##      if pki is None and evt is not None:
##          pki = self.peaklistbox.GetSelections()
    
    def rm_sel_peaks(self, peakname, event=None):

        if peakname in self.peaklist:
            
            pki = self.peaklist.index(peakname)
            
            self.peaklist.pop(pki)
            self.ipeaks.pop(pki)
            xi = self.rngpl.ch_xaxis.GetSelection()
            self.plt_peaks = peaklocater(self.ipeaks,self.plt_data[xi],self.plt_data[3])
            
            self.plot_data()
            self.plot_peaks()
            
        self.pkpl.ttl_cntpks.SetLabel('Total: %i peaks' % (len(self.ipeaks)))

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


    def check1Daxis(self,event=None,yaxis=False):
    
        self.plot1D.unzoom_all()
        xi = self.rngpl.ch_xaxis.GetSelection()
        
        ## 2theta
        if xi == 2: 
            self.xlabel = r'$2\Theta$'+r' $(^\circ)$'
        ## d
        elif xi == 1:
            self.xlabel = 'd ($\AA$)'
        ## q
        else: 
            self.xlabel = 'q (1/$\AA$)'

        self.xmin = np.min(self.raw_data[xi])
        self.xmax = np.max(self.raw_data[xi])
        if xi == 1: self.xmax = min(self.xmax,5)
        self.rngpl.val_qmin.SetValue('%0.3f' % self.xmin)
        self.rngpl.val_qmax.SetValue('%0.3f' % self.xmax)
 
        self.plot_data()
        if self.ipeaks:
            self.peak_display()
            self.plot_peaks()

        self.plot1D.set_xlabel(self.xlabel)
        self.rescale1Daxis(xaxis=True,yaxis=yaxis)



    def rescale1Daxis(self,xaxis=True,yaxis=False):

        xi = self.rngpl.ch_xaxis.GetSelection()
        if self.trim:
            x = self.plt_data[xi]
            y = self.plt_data[3]        
        else:
            x = self.raw_data[xi]
            y = self.raw_data[3]
        
        if xaxis:
            xmax = np.max(x)
            xmin = np.min(x)
            self.set_xview(xmin, xmax)
        if yaxis:
            ymax = np.max(y)
            ymin = np.min(y)
            self.set_yview(ymin, ymax)
            
    def set_xview(self, x1, x2):

        xi = self.rngpl.ch_xaxis.GetSelection()
        if self.trim:
            xydata = self.plt_data
        else:
            xydata = self.raw_data
        xmin,xmax = np.min(xydata[xi]),np.max(xydata[xi])
            
        x1 = max(xmin,x1)
        x2 = min(xmax,x2)
        
        if xi == 1: x2 = 5

        self.plot1D.axes.set_xlim((x1, x2))
        self.plot1D.canvas.draw()

    def set_yview(self, y1, y2):

        if self.trim:
            xydata = self.plt_data
        else:
            xydata = self.raw_data
        ymin,ymax = np.min(xydata[3]),np.max(xydata[3])
            
        y1 = max(ymin,y1)
        y2 = min(ymax,y2)

        self.plot1D.axes.set_ylim((y1, y2))
        self.plot1D.canvas.draw()




##############################################
#### DATABASE FUNCTIONS


    def open_database(self,event=None):
    
        wildcards = 'AMCSD database file (*.db)|*.db|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose AMCSD database file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            try:
                self.owner.openDB(dbname=path)
                print('Now using database: %s' % os.path.split(path)[-1])
            except:
               print('Failed to import file as database: %s' % path)


    def search_database(self,event=None):

        myDlg = XRDSearchGUI()
        
        fit = False
        if myDlg.ShowModal() == wx.ID_OK:
#             self.exponent = int(myDlg.val_exp.GetValue())
#             self.compress = int(myDlg.val_comp.GetValue())
#             self.width    = int(myDlg.val_wid.GetValue())
            fit = True
        myDlg.Destroy()

        if fit:
            self.background_fit()
            
    def match_database(self,event=None,fracq=0.75,pk_wid=0.05):
    
#         pks_0 = self.plt_peaks[0]

        try:
            minfracq = float(self.val_gdnss.GetValue())
        except:
            minfracq = fracq
            

        pks_0 = [2.010197, 2.321101, 3.284799, 3.851052, 4.023064, 4.647011, 5.063687, 5.1951]
        self.xmin = 1.75
        self.xmax = 5.25
        print '\n',pks_0,'\n range: ',self.xmin,self.xmax,'\n fraction: ',minfracq

        qstep = 0.01 ## read this from cifdb.py; mkak 2017.01.24
        qmin  = 0.2  ## read this from cifdb.py; mkak 2017.01.24
        
        peaks = []
        p_ids = []

        for pk0 in pks_0:
            pk=pk0
            pk_id = int((pk0-qmin)/qstep)
            
            ## performs peak broadening here
            if pk_wid > 0:    
                st = int(pk_wid/qstep/2)
                for p in np.arange(-1*st,st+1):
                    peaks += [pk+p*qstep]
                    p_ids += [pk_id+p]
            else:
                peaks += [pk]
                p_ids += [pk_id]

        import time
        a = time.time()

        matches,count = self.owner.cifdatabase.find_by_q(peaks)

        b = time.time()
        if (b-a) > 1:
            print('\n%d matched pattern(s) in %0.3f s' % (len(matches),((b-a)* 1e0)))
        else:
            print('\n%d matched pattern(s) in %0.3f ms' % (len(matches),((b-a)* 1e3)))

        goodness = np.zeros(np.shape(count))       

        for i, (amcsd,cnt) in enumerate(zip(matches,count)):
            goodness[i] = self.owner.cifdatabase.fraction_in_range(amcsd,cnt,
                                                                qmin=self.xmin,
                                                                qmax=self.xmax)

        try:
            matches,count,goodness = zip(*[(x,y,t) for t,x,y in sorted(zip(goodness,matches,count)) if t > minfracq])
        except:
            matches,count,goodness = [],[],[]


        c = time.time()
        if (c-a) > 1:
            print('\n%d matched pattern(s) for goodness %0.2f in %0.3f s' % (len(matches),minfracq,((c-a)* 1e0)))
            print('\t(%0.3f s and %0.3f s)' % (((b-a)* 1e0),((c-b)* 1e0)))
        elif (c-a) > 120:
            print('\n%d matched pattern(s) for goodness %0.2f in %0.2f min' % (len(matches),minfraq,((c-a)/60)))
            print('\t(%0.3f s and %0.2f min)' % (((b-a)* 1e0),((c-b)/60)))
        
        else:
            print('\n%d matched pattern(s) for goodness %0.2f in %0.3f ms' % (len(matches),minfracq,((c-a)* 1e3)))
            print('\t(%0.3f ms and %0.3f ms)' % (((b-a)* 1e3),((c-b)* 1e3)))
        if len(matches) > 0:
            for i,amcsd in enumerate(matches):
                str = 'AMCSD %i (matched %0.3f or %i out of %i): ' % (amcsd,goodness[i],count[i],count[i]/goodness[i])
                print str, self.owner.cifdatabase.q_in_range(amcsd,qmin=self.xmin,qmax=self.xmax)

            
        print



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
        self.val_hw.SetValue(str(self.parent.halfwidth))
#         self.val_intthr.SetValue(str(self.parent.intthrsh))
        
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
        hwsizer = wx.BoxSizer(wx.VERTICAL)

        ttl_hw = wx.StaticText(self.panel, label='Number of data points in half width')
        self.val_hw = wx.TextCtrl(self.panel,wx.TE_PROCESS_ENTER)

        hwsizer.Add(ttl_hw,  flag=wx.RIGHT, border=5)
        hwsizer.Add(self.val_hw,  flag=wx.RIGHT, border=5)
 
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
        mainsizer.AddSpacer(10)
        mainsizer.Add(hwsizer,   flag=wx.ALL, border=8)
        mainsizer.AddSpacer(10)
        mainsizer.Add(rgnsizer,   flag=wx.ALL, border=8)
        mainsizer.AddSpacer(10)
        mainsizer.Add(gpthrsizer, flag=wx.ALL, border=5)        
        mainsizer.AddSpacer(10)
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
        self.plotlist     = []
        self.xlabel       = 'q (A^-1)'
        
        self.data_name    = []
        self.xy_data      = [] #None #[]
        self.xy_plot      = [] #None #[]
        self.xy_scale     = []
        self.idata        = []
        
        self.cif_name     = []
        self.cif_data     = [] #None #[]
        self.cif_plot     = [] #None #[]
        self.cif_scale    = []
        self.icif         = []
        
        self.energy = 19.0   ## keV
        self.wavelength = lambda_from_E(self.energy) ## A

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

    def LeftSidePanel(self,panel):
        
        vbox = wx.BoxSizer(wx.VERTICAL)

        plttools = self.Toolbox(self)
        addbtns = self.AddPanel(self)
        dattools = self.DataBox(self)
        ciftools = self.CIFBox(self)
        
        vbox.Add(plttools,flag=wx.ALL,border=10)
        vbox.Add(addbtns,flag=wx.ALL,border=10)
        vbox.Add(dattools,flag=wx.ALL,border=10)
        vbox.Add(ciftools,flag=wx.ALL,border=10)
        return vbox

    def RightSidePanel(self,panel):
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        self.plot1DXRD(panel)
        
        settings = self.SettingsPanel(self)
        btnbox = self.QuickButtons(panel)
        
        vbox.Add(self.plot1D,proportion=1,flag=wx.ALL|wx.EXPAND,border = 10)
        hbox.Add(settings,flag=wx.RIGHT,border=10)
        hbox.Add(btnbox,flag=wx.LEFT,border = 1)
        vbox.Add(hbox,flag=wx.ALL|wx.ALIGN_RIGHT,border = 10)
        return vbox


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

        self.ch_xaxis.Bind(wx.EVT_CHOICE, self.check1Daxis)
    
        hbox_xaxis.Add(ttl_xaxis, flag=wx.RIGHT, border=8)
        hbox_xaxis.Add(self.ch_xaxis, flag=wx.EXPAND, border=8)
        vbox.Add(hbox_xaxis, flag=wx.ALL, border=10)

        ###########################
        ## Y-Scale
        hbox_yaxis = wx.BoxSizer(wx.HORIZONTAL)
        ttl_yaxis = wx.StaticText(self, label='Y-SCALE')
        yscales = ['linear','log']
        self.ch_yaxis = wx.Choice(self,choices=yscales)

        self.ch_yaxis.Bind(wx.EVT_CHOICE,   self.onLogLinear)
    
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
        self.val_scale = wx.TextCtrl(self,style=wx.TE_PROCESS_ENTER)
        btn_reset = wx.Button(self,label='reset')

        self.val_scale.Bind(wx.EVT_TEXT_ENTER, self.normalize1Ddata)
        btn_reset.Bind(wx.EVT_BUTTON, self.reset1Dscale)
        
        hbox_scl.Add(ttl_scl, flag=wx.RIGHT, border=8)
        hbox_scl.Add(self.val_scale, flag=wx.RIGHT, border=8)
        hbox_scl.Add(btn_reset, flag=wx.RIGHT, border=8)

        vbox.Add(hbox_scl, flag=wx.BOTTOM|wx.TOP, border=8)

        ###########################
        ## Hide/show and reset
        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_hide  = wx.Button(self,label='hide')
        btn_rmv   = wx.Button(self,label='remove')
        
        btn_hide.Bind(wx.EVT_BUTTON,  self.hide1Ddata)
        btn_rmv.Bind(wx.EVT_BUTTON,   self.remove1Ddata)

        btn_hide.Disable()
        btn_rmv.Disable()
        
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
        self.val_cifscale = wx.TextCtrl(self,style=wx.TE_PROCESS_ENTER)
#         btn_scale = wx.Button(self,label='set')

        self.val_cifscale.Bind(wx.EVT_TEXT_ENTER, partial(self.normalize1Ddata,cif=True))
#         btn_scale.Bind(wx.EVT_BUTTON, partial(self.normalize1Ddata,cif=True))
        
        hbox_scl.Add(ttl_scl, flag=wx.RIGHT, border=8)
        hbox_scl.Add(self.val_cifscale, flag=wx.RIGHT, border=8)
#         hbox_scl.Add(btn_scale, flag=wx.RIGHT, border=8)

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

    def onLogLinear(self, event=None):

        self.plot1D.axes.set_yscale(self.ch_yaxis.GetString(self.ch_yaxis.GetSelection()))
        self.rescale1Daxis(xaxis=False,yaxis=True)


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
        self.icif.append(len(self.plotlist))
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
        self.plotlist.append(self.plot1D.oplot(x,y,label=name,show_legend=True))

        ## Use correct x-axis units
        self.check1Daxis()

        self.ch_cif.Set(self.cif_name)
        self.ch_cif.SetStringSelection(name)
        
        ## Update toolbox panel, scale all cif to 1000
        self.val_cifscale.SetValue(str(self.cif_scale[plt_no]))
       
    def add1Ddata(self,x,y,name=None):
        
        plt_no = len(self.data_name)
        
        if name is None:
            name = 'dataset %i' % plt_no
        else:
            name = 'data: %s' % name

        self.data_name.append(name)
        self.idata.append(len(self.plotlist))
        self.xy_scale.append(np.max(y))

        q    = x
        d    = d_from_q(q)
        twth = twth_from_q(q,self.wavelength)
        self.xy_data.append([q,d,twth,y])
        self.xy_plot.append([q,d,twth,y])
        
        ## Plot data (x,y)
        xi = self.ch_xaxis.GetSelection()
        self.plotlist.append(self.plot1D.oplot(self.xy_plot[-1][xi],
                                               self.xy_plot[-1][3],
                                               label=name,show_legend=True))

        ## Use correct x-axis units
        self.check1Daxis(yaxis=True)

        self.ch_data.Set(self.data_name)
        self.ch_data.SetStringSelection(name)
        
        ## Update toolbox panel
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

        self.energy = E_from_lambda(wavelength) ## units keV 

    def normalize1Ddata(self,event=None,cif=False):
    
        if cif:
            plt_no = self.ch_cif.GetSelection()
            y = self.cif_data[plt_no][3]
        
            self.cif_scale[plt_no] = float(self.val_cifscale.GetValue())
            if self.cif_scale[plt_no] <= 0:
                self.cif_scale[plt_no] = np.max(y)
                self.val_cifscale.SetValue(str(self.cif_scale[plt_no]))
            self.cif_plot[plt_no][3] = y/np.max(y) * self.cif_scale[plt_no]
        else:
            plt_no = self.ch_data.GetSelection()
            y = self.xy_data[plt_no][3]
        
            self.xy_scale[plt_no] = float(self.val_scale.GetValue())
            if self.xy_scale[plt_no] <= 0:
                self.xy_scale[plt_no] = np.max(y)
                self.val_scale.SetValue(str(self.xy_scale[plt_no]))
            self.xy_plot[plt_no][3] = y/np.max(y) * self.xy_scale[plt_no]

        self.plot1D.unzoom_all()
        self.rescale1Daxis(xaxis=False,yaxis=True)

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

    def check1Daxis(self,event=None,yaxis=False):
    
        self.plot1D.unzoom_all()

        ## 2theta
        if self.ch_xaxis.GetSelection() == 2: 
            self.xlabel = r'$2\Theta$'+r' $(^\circ)$'
        ## d
        elif self.ch_xaxis.GetSelection() == 1:
            self.xlabel = 'd ($\AA$)'
        ## q
        else: 
            self.xlabel = 'q (1/$\AA$)'

        self.plot1D.set_xlabel(self.xlabel)
        self.rescale1Daxis(xaxis=True,yaxis=yaxis)

    def rescale1Daxis(self,xaxis=True,yaxis=False):

        xmax,xmin,ymax,ymin = 0,10,0,10
        xi = self.ch_xaxis.GetSelection()

        for i,plt_no in enumerate(self.icif):
            x = np.array(self.cif_plot[i][xi])
            y = np.array(self.cif_plot[i][3])

            if xmax < np.max(x): xmax = np.max(x)
            if xmin > np.min(x): xmin = np.min(x)
            if ymax < np.max(y): ymax = np.max(y)
            if ymin > np.min(y): ymin = np.min(y)

            self.plot1D.update_line(plt_no,x,y)
    
        for i,plt_no in enumerate(self.idata):
            x = np.array(self.xy_plot[i][xi])
            y = np.array(self.xy_plot[i][3])

            if xmax < np.max(x): xmax = np.max(x)
            if xmin > np.min(x): xmin = np.min(x)
            if ymax < np.max(y): ymax = np.max(y)
            if ymin > np.min(y): ymin = np.min(y)

            self.plot1D.update_line(plt_no,x,y)
    
        if xi == 1: xmax = 5
        if xaxis: self.set_xview(xmin, xmax)
        if yaxis: self.set_yview(ymin, ymax)

    def reset1Dscale(self,event=None):

        plt_no = self.ch_data.GetSelection()
        xi = self.ch_xaxis.GetSelection()        
       
        self.xy_plot[plt_no][3] = self.xy_data[plt_no][3]
        self.plot1D.update_line(int(self.idata[plt_no]),
                                np.array(self.xy_plot[plt_no][xi]),
                                np.array(self.xy_plot[plt_no][3]))
        self.plot1D.canvas.draw()
        self.plot1D.unzoom_all()
        
        self.rescale1Daxis(xaxis=False,yaxis=True)
        self.xy_scale[plt_no] = np.max(self.xy_data[plt_no][3])
        self.val_scale.SetValue(str(self.xy_scale[plt_no]))

    def set_xview(self, x1, x2):

        if self.xy_plot is not None:
            xydata = self.xy_plot
        elif self.cif_plot is not None:
            xydata = self.cif_plot
        else:
            return
        xi = self.ch_xaxis.GetSelection()
        xmin,xmax = self.abs_limits(xydata,axis=xi)
            
        x1 = max(xmin,x1)
        x2 = min(xmax,x2)

        self.plot1D.axes.set_xlim((x1, x2))
        self.plot1D.canvas.draw()

    def set_yview(self, y1, y2):

        if self.xy_plot is not None:
            xydata = self.xy_plot
        elif self.cif_plot is not None:
            xydata = self.cif_plot
        else:
            return
        ymin,ymax = self.abs_limits(xydata,axis=3)
            
        y1 = max(ymin,y1)
        y2 = min(ymax,y2)

        self.plot1D.axes.set_ylim((y1, y2))
        self.plot1D.canvas.draw()


    def abs_limits(self,xydata,axis=0):
    
        mini, maxi = 10,0 
        for axisi in xydata:
            mini = np.min(axisi[axis]) if np.min(axisi[axis]) < mini else mini
            maxi = np.max(axisi[axis]) if np.max(axisi[axis]) > maxi else maxi
  
        return mini,maxi

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
            hkllist = generate_hkl()
            
            if self.wavelength is not None:
                qlist = cif.Q(hkllist)
                Flist = cif.StructureFactorForQ(qlist,E_from_lambda(self.wavelength))
            
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
#     def on_pick(self,event=None):
#         handle = event.artist
#         if handle in self.lookup_artist:
#             artist = self.lookup_artist[handle]
#             artist.set_visible(not artist.get_visible())
#             self.update()
# 
#     def on_click(self,event=None):
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

class RangeToolsPanel(wx.Panel):
    '''
    Panel for housing range tools in fitting panel
    '''
    label='Range'
    def __init__(self,parent,owner=None,_larch=None):
        
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.owner = owner

        ## Default information


        rangepanel = self.RangeTools()

        panel1D = wx.BoxSizer(wx.HORIZONTAL)
        panel1D.Add(rangepanel,flag=wx.ALL,border=10)
        self.SetSizer(panel1D)

    def RangeTools(self):
    
        ###########################
        ## Range tools
        vbox_rng = wx.BoxSizer(wx.VERTICAL)
        hbox_xaxis = wx.BoxSizer(wx.HORIZONTAL)
        hbox_qmin = wx.BoxSizer(wx.HORIZONTAL)
        hbox_qmax = wx.BoxSizer(wx.HORIZONTAL)
        hbox_qset = wx.BoxSizer(wx.HORIZONTAL)
        
        ###########################
        ## X-Scale

        ttl_xaxis = wx.StaticText(self, label='X-SCALE')
        xunits = ['q','d',u'2\u03B8']
        self.ch_xaxis = wx.Choice(self,choices=xunits)
        self.ch_xaxis.Bind(wx.EVT_CHOICE, self.owner.check1Daxis)
        hbox_xaxis.Add(ttl_xaxis, flag=wx.RIGHT, border=8)
        hbox_xaxis.Add(self.ch_xaxis, flag=wx.EXPAND, border=8)
        
        ###########################
        ## X-Range        
        ttl_qmin = wx.StaticText(self, label='minimum') 
        self.val_qmin = wx.TextCtrl(self,style=wx.TE_PROCESS_ENTER)
        self.val_qmin.Bind(wx.EVT_TEXT_ENTER, self.owner.set_range)
        hbox_qmin.Add(ttl_qmin, flag=wx.RIGHT, border=8)
        hbox_qmin.Add(self.val_qmin, flag=wx.RIGHT, border=8)
        
        ttl_qmax= wx.StaticText(self, label='maximum') 
        self.val_qmax = wx.TextCtrl(self,style=wx.TE_PROCESS_ENTER)
        self.val_qmax.Bind(wx.EVT_TEXT_ENTER, self.owner.set_range)
        hbox_qmax.Add(ttl_qmax, flag=wx.RIGHT, border=8)
        hbox_qmax.Add(self.val_qmax, flag=wx.RIGHT, border=8)

        btn_rngreset = wx.Button(self,label='reset')
        btn_rngreset.Bind(wx.EVT_BUTTON, self.owner.reset_range)
        
        hbox_qset.Add(btn_rngreset, flag=wx.RIGHT, border=8)
        
        vbox_rng.Add(hbox_xaxis, flag=wx.ALL, border=10)
        vbox_rng.Add(hbox_qmin, flag=wx.BOTTOM, border=8)
        vbox_rng.Add(hbox_qmax, flag=wx.BOTTOM, border=8)
        vbox_rng.Add(hbox_qset, flag=wx.BOTTOM|wx.ALIGN_RIGHT, border=8)
        
        return vbox_rng


class BackgroundToolsPanel(wx.Panel):
    '''
    Panel for housing background tools in fitting panel
    '''
    label='Background'
    def __init__(self,parent,owner=None,_larch=None):
        
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.owner = owner

        ## Default information
        


        bkgdpanel = self.BackgroundTools()

        panel1D = wx.BoxSizer(wx.HORIZONTAL)
        panel1D.Add(bkgdpanel,flag=wx.ALL,border=10)
        self.SetSizer(panel1D)

    def BackgroundTools(self):
    
        ###########################
        ## Background tools
        vbox_bkgd = wx.BoxSizer(wx.VERTICAL)        
        hbox_bkgd = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_fbkgd = wx.Button(self,label='Fit')
        self.btn_fbkgd.Bind(wx.EVT_BUTTON,   self.owner.background_fit)
        hbox_bkgd.Add(self.btn_fbkgd, flag=wx.RIGHT, border=8)

        self.btn_obkgd = wx.Button(self,label='Options')
        self.btn_obkgd.Bind(wx.EVT_BUTTON,   self.owner.background_options)
        hbox_bkgd.Add(self.btn_obkgd, flag=wx.RIGHT, border=8)

        self.btn_rbkgd = wx.Button(self,label='Remove')
        self.btn_rbkgd.Bind(wx.EVT_BUTTON,   self.owner.remove_background)
      
        vbox_bkgd.Add(hbox_bkgd, flag=wx.BOTTOM, border=8)
        vbox_bkgd.Add(self.btn_rbkgd, flag=wx.BOTTOM, border=8)

        self.ck_bkgd = wx.CheckBox(self,label='Subtract')
        self.ck_bkgd.Bind(wx.EVT_CHECKBOX,  self.owner.subtract_background)
        vbox_bkgd.Add(self.ck_bkgd, flag=wx.BOTTOM, border=8)        
        
        return vbox_bkgd


class PeakToolsPanel(wx.Panel):
    '''
    Panel for housing background tools in fitting panel
    '''
    label='Peaks'
    def __init__(self,parent,owner=None,_larch=None):
        
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.owner = owner

        ## Default information
        

        pkspanel = self.PeakTools()

        panel1D = wx.BoxSizer(wx.HORIZONTAL)
        panel1D.Add(pkspanel,flag=wx.ALL,border=10)
        self.SetSizer(panel1D)

    def PeakTools(self):
    
        ###########################
        ## Peak tools
        vbox_pks = wx.BoxSizer(wx.VERTICAL)        
        hbox1_pks = wx.BoxSizer(wx.HORIZONTAL)
        hbox2_pks = wx.BoxSizer(wx.HORIZONTAL)
        hbox3_pks = wx.BoxSizer(wx.HORIZONTAL)
        hbox4_pks = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_fpks = wx.Button(self,label='Find peaks')
        #self.btn_fpks.Bind(wx.EVT_BUTTON, self.owner.find_peaks)
        self.btn_fpks.Bind(wx.EVT_BUTTON, partial(self.owner.find_peaks, filter=True))
        hbox1_pks.Add(self.btn_fpks, flag=wx.RIGHT, border=8)

        self.btn_opks = wx.Button(self,label='Search options')
        self.btn_opks.Bind(wx.EVT_BUTTON, self.owner.peak_options)
        hbox1_pks.Add(self.btn_opks, flag=wx.RIGHT, border=8)


        intthrsizer = wx.BoxSizer(wx.VERTICAL)

        ttl_intthr = wx.StaticText(self, label='Intensity threshold')
        self.val_intthr = wx.TextCtrl(self,wx.TE_PROCESS_ENTER)
        self.val_intthr.Bind(wx.EVT_TEXT_ENTER, partial(self.owner.find_peaks, filter=True))
        hbox2_pks.Add(ttl_intthr,  flag=wx.RIGHT, border=8)
        hbox2_pks.Add(self.val_intthr,  flag=wx.RIGHT, border=8)

        self.owner.peaklistbox = EditableListBox(self, self.owner.select_peak,
                                        remove_action=self.owner.rm_sel_peaks,
                                        size=(250, -1) #, style =  wx.LB_MULTIPLE
                                        )

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.ttl_cntpks = wx.StaticText(self, label=('Total: 0 peaks'))
        hbox3_pks.Add(self.ttl_cntpks, flag=wx.EXPAND|wx.ALL, border=8)


        self.btn_rpks = wx.Button(self,label='Remove all')
        self.btn_rpks.Bind(wx.EVT_BUTTON, self.owner.remove_all_peaks)
        hbox4_pks.Add(self.btn_rpks, flag=wx.RIGHT, border=8)

#         self.btn_spks = wx.Button(self,label='Select peaks manually')
#         self.btn_spks.Bind(wx.EVT_BUTTON,self.owner.DeleteSinglePeak)
#         hbox4_pks.Add(self.btn_spks, flag=wx.RIGHT, border=8)
        
        self.btn_fitpks = wx.Button(self,label='Fit peaks')
        self.btn_fitpks.Bind(wx.EVT_BUTTON, self.owner.fit_peaks)
        hbox4_pks.Add(self.btn_fitpks, flag=wx.RIGHT, border=8)

        
        vbox_pks.Add(hbox1_pks, flag=wx.BOTTOM, border=8)
        vbox_pks.Add(hbox2_pks, flag=wx.BOTTOM, border=8)
        vbox_pks.Add(self.owner.peaklistbox, flag=wx.BOTTOM, border=8)
        vbox_pks.Add(hbox3_pks, flag=wx.BOTTOM, border=8)
        vbox_pks.Add(hbox4_pks, flag=wx.BOTTOM, border=8)
        
        self.val_intthr.SetValue(str(self.owner.intthrsh))
        
        
        return vbox_pks  

class DatabasePanel(wx.Panel):
    '''
    Panel for housing range tools in fitting panel
    '''
    label='Search'
    def __init__(self,parent,owner=None,_larch=None):
        
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.owner = owner

        ## Default information
        

        newpanel = self.NewPanelTools()

        panel1D = wx.BoxSizer(wx.HORIZONTAL)
        panel1D.Add(newpanel,flag=wx.ALL,border=10)
        self.SetSizer(panel1D)
    
    def NewPanelTools(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_srch = wx.Button(self,label='Search parameters')

        ttl_gdnss = wx.StaticText(self, label='min. fraction')
        self.owner.val_gdnss = wx.TextCtrl(self,style=wx.TE_PROCESS_ENTER)
        hbox.Add(ttl_gdnss, flag=wx.RIGHT, border=8)
        hbox.Add(self.owner.val_gdnss, flag=wx.RIGHT, border=8)

        self.owner.val_gdnss.SetValue('0.85')

        btn_mtch = wx.Button(self,label='Find matches')
        
        btn_srch.Bind(wx.EVT_BUTTON,   self.owner.search_database)
        btn_mtch.Bind(wx.EVT_BUTTON,   self.owner.match_database)
        
        vbox.Add(btn_srch, flag=wx.BOTTOM,  border=8)
        vbox.Add(hbox,  flag=wx.BOTTOM, border=8)
        vbox.Add(btn_mtch, flag=wx.BOTTOM, border=8)
        
        
        
        
        return vbox
        
    

class RefinementPanel(wx.Panel):
    '''
    Panel for housing background tools in fitting panel
    '''
    label='Refinement'
    def __init__(self,parent,owner=None,_larch=None):
        
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.owner = owner

        ## Default information
        

        newpanel = self.NewPanelTools()

        panel1D = wx.BoxSizer(wx.HORIZONTAL)
        panel1D.Add(newpanel,flag=wx.ALL,border=10)
        self.SetSizer(panel1D)
    
    def NewPanelTools(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_1 = wx.Button(self,label='Button 3')
        btn_2 = wx.Button(self,label='Button 4')
        hbox.Add(btn_1, flag=wx.RIGHT, border=20)
        hbox.Add(btn_2, flag=wx.RIGHT, border=20)
        
        vbox.Add(hbox,flag=wx.ALL,border=10)
        
        return vbox

class ResultsPanel(wx.Panel):
    '''
    Panel for housing background tools in fitting panel
    '''
    label='Results'
    def __init__(self,parent,owner=None,_larch=None):
        
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.owner = owner

        ## Default information
        

        newpanel = self.NewPanelTools()

        panel1D = wx.BoxSizer(wx.HORIZONTAL)
        panel1D.Add(newpanel,flag=wx.ALL,border=10)
        self.SetSizer(panel1D)
    
    def NewPanelTools(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_1 = wx.Button(self,label='Button 5')
        btn_2 = wx.Button(self,label='Button 6')
        hbox.Add(btn_1, flag=wx.RIGHT, border=20)
        hbox.Add(btn_2, flag=wx.RIGHT, border=20)
        
        vbox.Add(hbox,flag=wx.ALL,border=10)
        
        return vbox

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
#             wavelength = lambda_from_E(energy) ## units: A
#             self.EorL.SetValue(str(wavelength))
#         else:
#             wavelength = float(self.EorL.GetValue()) ## units: A
#             energy = E_from_lambda(wavelength) ## units: keV
#             self.EorL.SetValue(str(energy))

    def onSPIN(self,event=None):
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
        self.wavelength = lambda_from_E(self.energy) ## units: A
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
                self.wavelength = lambda_from_E(self.energy) ## units: A
            else:
                self.wavelength = float(self.entr_EorL.GetValue()) ## units: A
                self.energy = E_from_lambda(self.wavelength) ## units: keV
        else:
            if self.ch_EorL.GetSelection() == 0:
                self.wavelength = float(self.entr_EorL.GetValue()) ## units: A
                self.energy = E_from_lambda(self.wavelength) ## units: keV
                self.entr_EorL.SetValue('%0.3f' % self.energy)
            else:
                self.energy = float(self.entr_EorL.GetValue()) ## units keV
                self.wavelength = lambda_from_E(self.energy) ## units: A
                self.entr_EorL.SetValue('%0.4f' % self.wavelength)
            self.pre_sel = self.ch_EorL.GetSelection()

#########################################################################
class XRDSearchGUI(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
    
        ## Constructor
        dialog = wx.Dialog.__init__(self, None, title='Crystal Structure Database Search',size=(500, 440))
        ## remember: size=(width,height)
        self.panel = wx.Panel(self)

        LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        
        ## Mineral search
        lbl_Mineral  = wx.StaticText(self.panel, label='Mineral:' )
        self.Mineral = wx.TextCtrl(self.panel,   size=(270, -1))
        #mineral_list = [] #['None']
        #self.Mineral = wx.Choice(self.panel,    choices=mineral_list)

        ## Author search
        lbl_Author  = wx.StaticText(self.panel, label='Author:' )
        self.Author = wx.TextCtrl(self.panel,   size=(270, -1))

        ## Chemistry search
        lbl_Chemistry  = wx.StaticText(self.panel, label='Chemistry:' )
        self.Chemistry = wx.TextCtrl(self.panel,   size=(175, -1))
        self.chmslct  = wx.Button(self.panel,     label='Specify...')
        
        ## Cell parameter symmetry search
        lbl_Symmetry  = wx.StaticText(self.panel, label='Symmetry/parameters:' )
        self.Symmetry = wx.TextCtrl(self.panel,   size=(175, -1))
        self.symslct  = wx.Button(self.panel,     label='Specify...')
        
        ## General search
        lbl_Search  = wx.StaticText(self.panel,  label='Keyword search:' )
        self.Search = wx.TextCtrl(self.panel, size=(270, -1))


        ## Define buttons
        self.rstBtn = wx.Button(self.panel, label='Reset' )
        hlpBtn = wx.Button(self.panel, wx.ID_HELP    )
        okBtn  = wx.Button(self.panel, wx.ID_OK      )
        canBtn = wx.Button(self.panel, wx.ID_CANCEL  )

        ## Bind buttons for functionality
        self.rstBtn.Bind(wx.EVT_BUTTON,  self.onReset     )
        self.chmslct.Bind(wx.EVT_BUTTON, self.onChemistry )
        self.symslct.Bind(wx.EVT_BUTTON, self.onSymmetry  )

        self.sizer = wx.GridBagSizer( 5, 6)

        self.sizer.Add(lbl_Mineral,    pos = ( 1,1)               )
        self.sizer.Add(self.Mineral,   pos = ( 1,2), span = (1,3) )

        self.sizer.Add(lbl_Author,     pos = ( 2,1)               )
        self.sizer.Add(self.Author,    pos = ( 2,2), span = (1,3) )

        self.sizer.Add(lbl_Chemistry,  pos = ( 3,1)               )
        self.sizer.Add(self.Chemistry, pos = ( 3,2), span = (1,2) )
        self.sizer.Add(self.chmslct,   pos = ( 3,4)               )

        self.sizer.Add(lbl_Symmetry,   pos = ( 4,1)               )
        self.sizer.Add(self.Symmetry,  pos = ( 4,2), span = (1,2) )
        self.sizer.Add(self.symslct,   pos = ( 4,4)               )

        self.sizer.Add(lbl_Search,     pos = ( 5,1)               )
        self.sizer.Add(self.Search,    pos = ( 5,2), span = (1,3) )

        self.sizer.Add(hlpBtn,        pos = (11,1)                )
        self.sizer.Add(canBtn,        pos = (11,2)                )
        self.sizer.Add(self.rstBtn,   pos = (11,3)                )
        self.sizer.Add(okBtn,         pos = (11,4)                )
        
        self.panel.SetSizer(self.sizer)

        self.Show()
#########################################################################
    def onChemistry(self,event=None):
        print('Will eventually show Periodic Table...')
#########################################################################
    def onSymmetry(self,event=None):
        XRDSymmetrySearch()
#########################################################################
    def onReset(self,event=None):
        self.Mineral.Clear()
        self.Author.Clear()
        self.Chemistry.Clear()
        self.Symmetry.Clear()
        self.Search.Clear()
#########################################################################            
class XRDSymmetrySearch(wx.Dialog):
    """"""

    def __init__(self):
    
        ## Constructor
        dialog = wx.Dialog.__init__(self, None, title='Cell Parameters and Symmetry',size=(460, 440))
        ## remember: size=(width,height)
        self.panel = wx.Panel(self)


        LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
        
        ## Lattice parameters
        lbl_a = wx.StaticText(self.panel,    label='a (A)' )
        self.min_a = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_a = wx.TextCtrl(self.panel, size=(100, -1))

        lbl_b = wx.StaticText(self.panel,    label='b (A)' )
        self.min_b = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_b = wx.TextCtrl(self.panel, size=(100, -1))

        lbl_c = wx.StaticText(self.panel,    label='a (A)' )
        self.min_c = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_c = wx.TextCtrl(self.panel, size=(100, -1))

        lbl_alpha = wx.StaticText(self.panel,    label='alpha (deg)' )
        self.min_alpha = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_alpha = wx.TextCtrl(self.panel, size=(100, -1))

        lbl_beta = wx.StaticText(self.panel,    label='beta (deg)' )
        self.min_beta = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_beta = wx.TextCtrl(self.panel, size=(100, -1))

        lbl_gamma = wx.StaticText(self.panel,    label='gamma (deg)' )
        self.min_gamma = wx.TextCtrl(self.panel, size=(100, -1))
        self.max_gamma = wx.TextCtrl(self.panel, size=(100, -1))

        SG_list = ['']
        for sgno in np.arange(230):
            SG_list.append('%3d' % (sgno+1))

#         sgfile = 'space_groups.txt'
#         if not os.path.exists(sgfile):
#             parent, child = os.path.split(__file__)
#             sgfile = os.path.join(parent, sgfile)
#             if not os.path.exists(sgfile):
#                 raise IOError("Space group file '%s' not found!" % sgfile)
#         sg = open(sgfile,'r')
#         for sgno,line in enumerate(sg):
#             try:
#                 sgno = sgno+1
#                 SG_list.append('%3d  %s' % (sgno,line))
#             except:
#                 sg.close()
#                 break

        
        lbl_SG = wx.StaticText(self.panel, label='Space group:')
        self.SG = wx.Choice(self.panel,    choices=SG_list)

        ## Define buttons
        self.rstBtn = wx.Button(self.panel, label='Reset' )
        hlpBtn = wx.Button(self.panel, wx.ID_HELP   )
        okBtn  = wx.Button(self.panel, wx.ID_OK     )
        canBtn = wx.Button(self.panel, wx.ID_CANCEL )

        ## Bind buttons for functionality
        self.rstBtn.Bind(wx.EVT_BUTTON,  self.onReset     )

        self.sizer = wx.GridBagSizer( 5, 6)

        self.sizer.Add(lbl_a,          pos = ( 1,1) )
        self.sizer.Add(self.min_a,     pos = ( 1,2) )
        self.sizer.Add(self.max_a,     pos = ( 1,3) )

        self.sizer.Add(lbl_b,          pos = ( 2,1) )
        self.sizer.Add(self.min_b,     pos = ( 2,2) )
        self.sizer.Add(self.max_b,     pos = ( 2,3) )

        self.sizer.Add(lbl_c,          pos = ( 3,1) )
        self.sizer.Add(self.min_c,     pos = ( 3,2) )
        self.sizer.Add(self.max_c,     pos = ( 3,3) )

        self.sizer.Add(lbl_alpha,      pos = ( 4,1) )
        self.sizer.Add(self.min_alpha, pos = ( 4,2) )
        self.sizer.Add(self.max_alpha, pos = ( 4,3) )

        self.sizer.Add(lbl_beta,       pos = ( 5,1) )
        self.sizer.Add(self.min_beta,  pos = ( 5,2) )
        self.sizer.Add(self.max_beta,  pos = ( 5,3) )

        self.sizer.Add(lbl_gamma,      pos = ( 6,1) )
        self.sizer.Add(self.min_gamma, pos = ( 6,2) )
        self.sizer.Add(self.max_gamma, pos = ( 6,3) )

        self.sizer.Add(lbl_SG,         pos = ( 7,1) )
        self.sizer.Add(self.SG,        pos = ( 7,2) )


        self.sizer.Add(hlpBtn,        pos = (11,1)  )
        self.sizer.Add(canBtn,        pos = (11,2)  )
        self.sizer.Add(self.rstBtn,   pos = (11,3)  )
        self.sizer.Add(okBtn,         pos = (11,4)  )

        self.panel.SetSizer(self.sizer)

        self.Show()
#########################################################################
    def onReset(self,event=None):
        self.min_a.Clear()
        self.max_a.Clear()
        self.min_b.Clear()
        self.max_b.Clear()
        self.min_c.Clear()
        self.max_c.Clear()
        self.min_alpha.Clear()
        self.max_alpha.Clear()
        self.min_beta.Clear()
        self.max_beta.Clear()
        self.min_gamma.Clear()
        self.max_gamma.Clear()
        self.SG.SetSelection(0)


      
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
