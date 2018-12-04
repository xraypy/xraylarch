#!/usr/bin/env python
"""
GUI for displaying maps from HDF5 files

"""

VERSION = '10 (14-March-2018)'

import os
import platform
import sys
import time
import json
import six
import socket
import datetime
from functools import partial
from threading import Thread

import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception

HAS_tomopy = False
try:
    import tomopy
    HAS_tomopy = True
except ImportError:
    pass


import numpy as np
import scipy.stats as stats


import larch
from larch.wxlib import (EditableListBox, SimpleText,
                         FloatCtrl, Font, pack, Popup, Button, MenuItem,
                         Choice, Check, GridPanel, FileSave, HLine)
from larch.utils.strutils import bytes2str, version_ge

from larch_plugins.io import nativepath
from larch_plugins.xrmmap import GSEXRM_MapFile, GSEXRM_FileStatus, h5str, ensure_subgroup
from larch_plugins.tomo import (tomo_reconstruction, reshape_sinogram, trim_sinogram,
                                return_methods)


CEN = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
RIGHT = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
ALL_CEN =  wx.ALL|CEN
ALL_LEFT =  wx.ALL|LEFT
ALL_RIGHT =  wx.ALL|RIGHT


PLOT_TYPES = ('Single ROI Map', 'Three ROI Map', 'Correlation Plot')
PLOT_OPERS = ('/', '*', '-', '+')


class TomographyPanel(GridPanel):
    '''Panel of Controls for reconstructing a tomographic slice'''
    label  = 'Tomography Tools'
    def __init__(self, parent, owner, **kws):

        self.owner = owner
        self.cfile,self.xrmmap = None,None
        self.npts = None
        self.resave = False

        GridPanel.__init__(self, parent, nrows=8, ncols=6, **kws)

        self.plot_choice = Choice(self, choices=PLOT_TYPES[:-1], size=(125, -1))
        self.plot_choice.Bind(wx.EVT_CHOICE, self.plotSELECT)

        self.det_choice = [Choice(self, size=(125, -1)),
                           Choice(self, size=(125, -1)),
                           Choice(self, size=(125, -1)),
                           Choice(self, size=(125, -1))]
        self.roi_choice = [Choice(self, size=(125, -1)),
                           Choice(self, size=(125, -1)),
                           Choice(self, size=(125, -1)),
                           Choice(self, size=(125, -1))]
        for i,det_chc in enumerate(self.det_choice):
            det_chc.Bind(wx.EVT_CHOICE, partial(self.detSELECT,i))
        for i,roi_chc in enumerate(self.roi_choice):
            roi_chc.Bind(wx.EVT_CHOICE, partial(self.roiSELECT,i))

        self.det_label = [SimpleText(self,''),
                          SimpleText(self,''),
                          SimpleText(self,'')]
        self.roi_label = [SimpleText(self,''),
                          SimpleText(self,''),
                          SimpleText(self,''),
                          SimpleText(self,'')]

        self.oper = Choice(self, choices=PLOT_OPERS, size=(80, -1))

        self.tomo_show = [Button(self, 'Show New',     size=(100, -1),
                               action=partial(self.onShowTomograph, new=True)),
                          Button(self, 'Replace Last', size=(100, -1),
                               action=partial(self.onShowTomograph, new=False))]

        self.tomo_pkg,self.tomo_alg_A,self.tomo_alg_B = return_methods()

        self.alg_choice = [Choice(self, choices=self.tomo_pkg,      size=(125, -1)),
                           Choice(self, choices=self.tomo_alg_A[0], size=(125, -1)),
                           Choice(self, choices=self.tomo_alg_B[0], size=(125, -1))]
        self.alg_choice[0].Bind(wx.EVT_CHOICE, self.onALGchoice)

        self.center_value = wx.SpinCtrlDouble(self, inc=0.25, size=(100, -1),
                                     style=wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP)
        self.refine_center = wx.CheckBox(self, label='Refine center')
        self.center_range = wx.SpinCtrlDouble(self, inc=1, size=(50, -1),
                                     style=wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP)
        self.refine_center.Bind(wx.EVT_CHECKBOX, self.refineCHOICE)

        self.refine_center.SetValue(False)

        self.sino_data   = Choice(self, size=(250, -1))
        self.tomo_save   = Button(self, 'Save reconstruction',     size=(150, -1),
                               action=self.onSaveTomograph)


        #################################################################################
        self.AddMany((SimpleText(self,'Plot type:'),self.plot_choice),
                                                               style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,''),self.det_label[0],
                        self.det_label[1],self.det_label[2]),  style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,'Detector:'),self.det_choice[0],
                      self.det_choice[1],self.det_choice[2]),  style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,'ROI:'),self.roi_choice[0],
                      self.roi_choice[1],self.roi_choice[2]),  style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,''),self.roi_label[0],
                        self.roi_label[1],self.roi_label[2]),  style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,'Operator:'),self.oper), style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,'Detector:'),self.det_choice[-1]),
                                                               style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,'ROI:'),self.roi_choice[-1]),
                                                               style=LEFT,  newrow=True)

        self.AddMany((SimpleText(self,''),self.roi_label[-1]), style=LEFT,  newrow=True)

        self.Add(HLine(self, size=(500, 4)),           dcol=8, style=LEFT,  newrow=True)

        self.Add(SimpleText(self,' '),         dcol=1, style=LEFT,  newrow=True)
        self.Add(SimpleText(self,'Engine'),    dcol=1, style=LEFT)
        self.Add(SimpleText(self,'Algorithm'), dcol=1, style=LEFT)
        self.Add(SimpleText(self,'Filter'),    dcol=1, style=LEFT)
        self.Add(SimpleText(self,'Reconstruct: '), dcol=1, style=LEFT,  newrow=True)
        self.AddMany((self.alg_choice[0], self.alg_choice[1], self.alg_choice[2]),
                                                       dcol=1, style=LEFT)
        self.Add(SimpleText(self,'Center: '),          dcol=1, style=LEFT,  newrow=True)
        self.Add(self.center_value,    dcol=1, style=LEFT)
        self.Add(self.refine_center,    dcol=1, style=LEFT)

        os = wx.BoxSizer(wx.HORIZONTAL)
        os.Add(SimpleText(self,' Max Range: '), 0, LEFT)
        os.Add(self.center_range, 1, LEFT)
        self.Add(os,    dcol=1, style=LEFT)


        self.Add(HLine(self, size=(500, 4)),           dcol=8, style=LEFT,  newrow=True)

        self.Add(SimpleText(self,'Display:'),          dcol=1, style=LEFT,  newrow=True)
        self.Add(self.tomo_show[0],                    dcol=1, style=LEFT)
        self.Add(self.tomo_show[1],                    dcol=1, style=LEFT)

        self.Add(HLine(self, size=(500, 4)),           dcol=8, style=LEFT,  newrow=True)

        self.Add(SimpleText(self,'Data:'),             dcol=1, style=LEFT,  newrow=True)
        self.Add(self.sino_data,                       dcol=2, style=LEFT)
        self.Add(self.tomo_save,                       dcol=1, style=LEFT)

        #################################################################################
        self.pack()
        self.disable_options()

    def disable_options(self):
        # print(" tomo panel disable options ")

        all_choices = [self.plot_choice]+[self.oper]+[self.sino_data]
        all_choices += self.alg_choice+self.det_choice+self.roi_choice
        for chc in all_choices:
            chc.Disable()

        self.refine_center.Disable()

        for btn in (self.tomo_show+[self.tomo_save]):
            btn.Disable()

        self.center_value.Disable()
        self.center_range.Disable()


    def enable_options(self):
        # print(" tomo panel enable options ")
        self.plot_choice.Enable()

        self.det_choice[0].Enable()
        self.det_choice[-1].Enable()
        self.sino_data.Enable()
        self.roi_choice[0].Enable()
        self.roi_choice[-1].Enable()

        self.oper.Enable()

        for chc in self.alg_choice:
            chc.Enable()

        if self.tomo_pkg[0] != '':
            for btn in (self.tomo_show+[self.tomo_save]):
                btn.Enable()
            self.refine_center.Enable()
            self.center_value.Enable()
            self.center_range.SetValue(10)
            self.center_range.SetRange(1, 20)

    def update_xrmmap(self, xrmfile=None):

        if xrmfile is None:
            xrmfile = self.owner.current_file

        self.cfile  = xrmfile
        self.xrmmap = self.cfile.xrmmap
        # print("tomopanel update xrmmap ", xrmfile, self.cfile)
        # print(" -- " , self.cfile.get_rotation_axis() )

        if self.cfile.get_rotation_axis() is None:
            self.center_value.SetValue(0)
            self.disable_options()
            return

        self.enable_options()
        self.set_det_choices()

        try:
            self.npts = len(self.cfile.get_pos(0, mean=True))
        except:
            self.npts = len(self.cfile.get_pos('x', mean=True))

        if self.tomo_pkg[0] != '':
            center = self.cfile.get_tomography_center()
            self.center_value.SetRange(-0.5*self.npts,1.5*self.npts)
            self.center_value.SetValue(center)

        self.plotSELECT()

    def refineCHOICE(self,event=None):

        if self.refine_center.GetValue():
            self.center_range.Enable()
        else:
            self.center_range.Disable()

    def onALGchoice(self,event=None):

        self.alg_choice[1].SetChoices(self.tomo_alg_A[self.alg_choice[0].GetSelection()])
        self.alg_choice[2].SetChoices(self.tomo_alg_B[self.alg_choice[0].GetSelection()])

        if self.alg_choice[0].GetStringSelection().startswith('sci'):
            self.center_value.SetIncrement(1)
        else:
            self.center_value.SetIncrement(0.25)

    def detSELECT(self,idet,event=None):
        self.set_roi_choices(idet=idet)

    def roiSELECT(self,iroi,event=None):

        detname = self.det_choice[iroi].GetStringSelection()
        roiname = self.roi_choice[iroi].GetStringSelection()

        if version_ge(self.cfile.version, '2.0.0'):
            try:
                roi = self.cfile.xrmmap['roimap'][detname][roiname]
                limits = roi['limits'][:]
                units = bytes2str(roi['limits'].attrs.get('units',''))
                if units == '1/A':
                    roistr = '[%0.2f to %0.2f %s]' % (limits[0],limits[1],units)
                else:
                    roistr = '[%0.1f to %0.1f %s]' % (limits[0],limits[1],units)
            except:
                roistr = ''
        else:
            try:
                roi = self.cfile.xrmmap[detname]
                en     = list(roi['energy'][:])
                index  = list(roi['roi_name'][:]).index(roiname)
                limits = list(roi['roi_limits'][:][index])
                roistr = '[%0.1f to %0.1f keV]' % (en[limits[0]],en[limits[1]])
            except:
                roistr = ''

        self.roi_label[iroi].SetLabel(roistr)

    def plotSELECT(self,event=None):
        if len(self.owner.filemap) > 0:
            plot_type = self.plot_choice.GetStringSelection().lower()
            if 'single' in plot_type:
                for i in (1,2):
                    self.det_choice[i].Disable()
                    self.roi_choice[i].Disable()
                    self.roi_label[i].SetLabel('')
                for i,label in enumerate([' Map ', ' ', ' ']):
                    self.det_label[i].SetLabel(label)
            elif 'three' in plot_type:
                for i in (1,2):
                    self.det_choice[i].Enable()
                    self.roi_choice[i].Enable()
                for i,label in enumerate(['Red', 'Green', 'Blue']):
                    self.det_label[i].SetLabel(label)
                self.set_roi_choices()

    def onLasso(self, selected=None, mask=None, data=None, xrmfile=None, **kws):
        if xrmfile is None: xrmfile = self.owner.current_file
        ny, nx = xrmfile.get_shape()
        indices = []
        for idx in selected:
            iy, ix = divmod(idx, ny)
            indices.append((ix, iy))


    def onClose(self):
        for p in self.plotframes:
            try:
                p.Destroy()
            except:
                pass

    def calculateSinogram(self,xrmfile=None):

        '''
        returns slice as [slices, x, 2th]
        '''

        subtitles = None
        plt3 = ('three' in self.plot_choice.GetStringSelection().lower())
        oprtr = self.oper.GetStringSelection()

        det_name,roi_name = [],[]
        plt_name = []
        for det,roi in zip(self.det_choice,self.roi_choice):
            det_name += [det.GetStringSelection()]
            roi_name += [roi.GetStringSelection()]
            if det_name[-1] == 'scalars':
                plt_name += ['%s' % roi_name[-1]]
            else:
                plt_name += ['%s(%s)' % (roi_name[-1],det_name[-1])]

        if plt3:
            flagxrd = False
            for det in det_name:
                if det.startswith('xrd'): flagxrd = True
        else:
            flagxrd = True if det_name[0].startswith('xrd') else False

        if xrmfile is None: xrmfile = self.owner.current_file

        args={'trim_sino' : flagxrd,
              'hotcols'   : self.owner.hotcols,
              'dtcorrect' : self.owner.dtcor}

        x     = xrmfile.get_translation_axis(hotcols=args['hotcols'])
        omega = xrmfile.get_rotation_axis(hotcols=args['hotcols'])

        if omega is None:
            print('\n** Cannot compute tomography: no rotation axis specified in map. **')
            return

        r_map,sino_order = xrmfile.get_sinogram(roi_name[0],det=det_name[0],**args)
        if plt3:
            g_map,sino_order = xrmfile.get_sinogram(roi_name[1],det=det_name[1],**args)
            b_map,sino_order = xrmfile.get_sinogram(roi_name[2],det=det_name[2],**args)

        if roi_name[-1] != '1':
            mapx,sino_order = xrmfile.get_sinogram(roi_name[-1],det=det_name[-1],**args)

            ## remove negative background counts for dividing
            if oprtr == '/': mapx[np.where(mapx==0)] = 1.
        else:
            mapx = 1.

        pref, fname = os.path.split(xrmfile.filename)
        if plt3:
            if   oprtr == '+': sino = np.array([r_map+mapx, g_map+mapx, b_map+mapx])
            elif oprtr == '-': sino = np.array([r_map-mapx, g_map-mapx, b_map-mapx])
            elif oprtr == '*': sino = np.array([r_map*mapx, g_map*mapx, b_map*mapx])
            elif oprtr == '/': sino = np.array([r_map/mapx, g_map/mapx, b_map/mapx])
            sino.resize(tuple(i for i in sino.shape if i!=1))
            title = fname
            info = ''
            if roi_name[-1] == '1' and oprtr == '/':
                subtitles = {'red':   'Red: %s'   % plt_name[0],
                             'green': 'Green: %s' % plt_name[1],
                             'blue':  'Blue: %s'  % plt_name[2]}
            else:
                subtitles = {'red':   'Red: %s %s %s'   % (plt_name[0],oprtr,plt_name[-1]),
                             'green': 'Green: %s %s %s' % (plt_name[1],oprtr,plt_name[-1]),
                             'blue':  'Blue: %s %s %s'  % (plt_name[2],oprtr,plt_name[-1])}

        else:
            if   oprtr == '+': sino = r_map+mapx
            elif oprtr == '-': sino = r_map-mapx
            elif oprtr == '*': sino = r_map*mapx
            elif oprtr == '/': sino = r_map/mapx

            if roi_name[-1] == '1' and oprtr == '/':
                title = plt_name[0]
            else:
                title = '%s %s %s' % (plt_name[0],oprtr,plt_name[-1])
            title = '%s: %s' % (fname, title)
            info  = 'Intensity: [%g, %g]' %(sino.min(), sino.max())
            subtitle = None

        return title,subtitles,info,x,omega,sino_order,sino

    def onSaveTomograph(self, event=None):

        xrmfile = self.owner.current_file
        detpath     = self.sino_data.GetStringSelection()
        tomo_center = self.center_value.GetValue()

        if not self.owner.dtcor and 'scalars' in detpath:
            detpath = '%s_raw' % detpath

        tomo_alg = [self.alg_choice[0].GetStringSelection(),
                    self.alg_choice[1].GetStringSelection(),
                    self.alg_choice[2].GetStringSelection()]

        print('\nSaving tomographic reconstruction for %s ...' % detpath)

        xrmfile.save_tomograph(detpath, tomo_alg=tomo_alg,
                               center=tomo_center,dtcorrect=self.owner.dtcor,
                               hotcols=self.owner.hotcols)
        print('Saved.')


    def onShowTomograph(self, event=None, new=True):

        xrmfile = self.owner.current_file
        tomo_center = self.center_value.GetValue()
        det = None

        ## returns sino in order: slice, x, 2theta
        title,subtitles,info,x,ome,sino_order,sino = self.calculateSinogram()

        tomo_alg = [self.alg_choice[0].GetStringSelection(),
                    self.alg_choice[1].GetStringSelection(),
                    self.alg_choice[2].GetStringSelection()]

        args = {'refine_center'  : self.refine_center.GetValue(),
                'center_range'   : self.center_range.GetValue(),
                'center'         : tomo_center,
                'tomo_alg'       : tomo_alg,
                'sinogram_order' : sino_order,
                'omega'          : ome,
                'hotcols'        : self.owner.hotcols}

        # print("On Show Tomo ", tomo_alg, args)

        tomo = xrmfile.get_tomograph(sino, **args)

        if args['refine_center']:
            self.set_center(xrmfile.xrmmap['tomo/center'].value)
            self.refine_center.SetValue(False)

        omeoff, xoff = 0, 0
        alg = [alg_ch.GetStringSelection() for alg_ch in self.alg_choice]
        if alg[1] != '' and alg[1] is not None:
            title = '[%s : %s @ %0.1f] %s ' % (alg[0],alg[1],tomo_center,title)
        else:
            title = '[%s @ %0.1f] %s' % (alg[0],tomo_center,title)

        ## for one color plot
        if sino.shape[0] == 1 and tomo.shape[0] == 1:
            sino = sino[0]
            tomo = tomo[0]
            det = self.det_choice[0].GetStringSelection()

        if len(self.owner.tomo_displays) == 0 or new:
            iframe = self.owner.add_tomodisplay(title)

        self.owner.display_tomo(tomo, title=title, det=det)

    def set_center(self,cen):

        self.center_value.SetValue(cen)
        self.cfile.set_tomography_center(center=cen)

    def set_det_choices(self):

        det_list = self.cfile.get_detector_list()

        for det_ch in self.det_choice:
            det_ch.SetChoices(det_list)
        if 'scalars' in det_list: ## should set 'denominator' to scalars as default
            self.det_choice[-1].SetStringSelection('scalars')

        data_list = self.cfile.get_datapath_list(remove='raw')
        self.sino_data.SetChoices(data_list)

        self.set_roi_choices()

    def set_roi_choices(self, idet=None):

        if idet is None:
            for idet,det_ch in enumerate(self.det_choice):
                detname = self.det_choice[idet].GetStringSelection()
                rois = self.update_roi(detname)

                self.roi_choice[idet].SetChoices(rois)
                self.roiSELECT(idet)
        else:
            detname = self.det_choice[idet].GetStringSelection()
            rois = self.update_roi(detname)

            self.roi_choice[idet].SetChoices(rois)
            self.roiSELECT(idet)


    def update_roi(self, detname):
        return self.cfile.get_roi_list(detname)
