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
import socket
import datetime
from functools import partial
from threading import Thread

import wx
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

from  ..wxlib import (EditableListBox, SimpleText,
                       FloatCtrl, Font, pack, Popup, Button, MenuItem,
                       Choice, Check, GridPanel, FileSave, HLine)
from ..utils.strutils import bytes2str, version_ge
from ..io import nativepath
from ..math.tomography import TOMOPY_ALG, TOMOPY_FILT

from ..xrmmap import GSEXRM_MapFile, GSEXRM_FileStatus, h5str, ensure_subgroup


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
    def __init__(self, parent, owner=None, **kws):

        self.owner = owner
        self.cfile,self.xrmmap = None,None
        self.npts = None
        self.resave = False

        GridPanel.__init__(self, parent, nrows=8, ncols=6, **kws)

        self.plot_choice = Choice(self, choices=PLOT_TYPES[:-1], size=(140, -1))
        self.plot_choice.Bind(wx.EVT_CHOICE, self.plotSELECT)

        self.det_choice = [Choice(self, size=(140, -1)),
                           Choice(self, size=(140, -1)),
                           Choice(self, size=(140, -1)),
                           Choice(self, size=(140, -1))]
        self.roi_choice = [Choice(self, size=(140, -1)),
                           Choice(self, size=(140, -1)),
                           Choice(self, size=(140, -1)),
                           Choice(self, size=(140, -1))]

        for i,det_chc in enumerate(self.det_choice):
            det_chc.Bind(wx.EVT_CHOICE, partial(self.detSELECT,i))

        for i,roi_chc in enumerate(self.roi_choice):
            roi_chc.Bind(wx.EVT_CHOICE, partial(self.roiSELECT,i))

        self.det_label = [SimpleText(self,''),
                          SimpleText(self,''),
                          SimpleText(self,''),
                          SimpleText(self,'Normalization')]
        self.roi_label = [SimpleText(self,''),
                          SimpleText(self,''),
                          SimpleText(self,''),
                          SimpleText(self,'')]


        self.use_dtcorr  = Check(self, default=True,
                                 label='Correct for Detector Deadtime',
                                 action=self.onDTCorrect)
        self.use_hotcols = Check(self, default=False,
                                 label='Remove First and Last columns',
                                 action=self.onHotCols)
        self.i1trans = Check(self, default=True,
                             label='Column labeled "i1" is transmission data')

        self.tomo_show = [Button(self, 'Show New',     size=(100, -1),
                               action=partial(self.onShowTomograph, new=True)),
                          Button(self, 'Replace Last', size=(100, -1),
                               action=partial(self.onShowTomograph, new=False))]

        self.tomo_algo = Choice(self, choices=TOMOPY_ALG, size=(140, -1),
                                action=self.onALGchoice)
        self.tomo_filt = Choice(self, choices=TOMOPY_FILT, size=(140, -1))
        self.tomo_niter = wx.SpinCtrl(self, min=1, max=500, initial=1,
                                      size=(100, -1),
                                      style=wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP)

        self.center_value = wx.SpinCtrlDouble(self, inc=0.25, size=(100, -1),
                                     style=wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP)
        self.center_value.SetIncrement(0.25)
        self.refine_center = wx.CheckBox(self, label='Refine')
        self.refine_center.SetValue(False)

        self.sino_data   = Choice(self, size=(200, -1))
        self.tomo_save   = Button(self, 'Save reconstruction',     size=(150, -1),
                               action=self.onSaveTomograph)


        #################################################################################
        self.AddMany((SimpleText(self,'Plot type:'),self.plot_choice),
                     style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,''), self.det_label[0],
                        self.det_label[1], self.det_label[2], self.det_label[3]),
                     style=LEFT,  newrow=True)

        self.AddMany((SimpleText(self,'Detector:'), self.det_choice[0],
                      self.det_choice[1], self.det_choice[2], self.det_choice[3]),
                      style=LEFT,  newrow=True)

        self.AddMany((SimpleText(self,'ROI:'), self.roi_choice[0],
                      self.roi_choice[1], self.roi_choice[2], self.roi_choice[3]),
                     style=LEFT,  newrow=True)

        self.AddMany((SimpleText(self,''), self.roi_label[0],
                        self.roi_label[1], self.roi_label[2], self.roi_label[3]),
                     style=LEFT,  newrow=True)

        self.Add((5, 5),                        dcol=1, style=LEFT,  newrow=True)
        self.Add(SimpleText(self,'Display:'),   dcol=1, style=LEFT, newrow=True)
        self.Add(self.tomo_show[0],             dcol=1, style=LEFT)
        self.Add(self.tomo_show[1],             dcol=1, style=LEFT)

        self.Add(HLine(self, size=(600, 5)),    dcol=8, style=LEFT,  newrow=True)
        self.Add(SimpleText(self,'Options:'),   dcol=1, style=LEFT, newrow=True)
        self.Add(self.use_dtcorr,               dcol=2, style=LEFT)
        self.Add((5, 5),                        dcol=1, style=LEFT,  newrow=True)
        self.Add(self.use_hotcols,              dcol=2, style=LEFT)
        self.Add((5, 5),                        dcol=1, style=LEFT,  newrow=True)
        self.Add(self.i1trans,                  dcol=2, style=LEFT)
        self.Add((5, 5),                        dcol=1, style=LEFT,  newrow=True)

        self.Add(HLine(self, size=(600, 5)),    dcol=8, style=LEFT,  newrow=True)

        self.Add(SimpleText(self,'Reconstruction '), dcol=2, style=LEFT,  newrow=True)

        self.Add((5, 5),                            dcol=1, style=LEFT,  newrow=True)
        self.Add(SimpleText(self,'Algorithm:'),     dcol=1, style=LEFT)
        self.Add(self.tomo_algo,                    dcol=1, style=LEFT)
        self.Add((5, 5),                            dcol=1, style=LEFT, newrow=True)
        self.Add(SimpleText(self,'Filter: '),       dcol=1, style=LEFT)
        self.Add(self.tomo_filt,                    dcol=1, style=LEFT)
        self.Add((5, 5),                            dcol=1, style=LEFT, newrow=True)
        self.Add(SimpleText(self,'# Iterations'),   dcol=1, style=LEFT)
        self.Add(self.tomo_niter,                   dcol=1, style=LEFT)
        self.Add((5, 5),                            dcol=1, style=LEFT, newrow=True)
        self.Add(SimpleText(self,'Center Pixel:'),      dcol=1, style=LEFT)
        self.Add(self.center_value, dcol=1, style=LEFT)
        self.Add(self.refine_center, dcol=1, style=LEFT)


        self.Add(HLine(self, size=(600, 5)),     dcol=8, style=LEFT,  newrow=True)


        self.Add(SimpleText(self,'Data:'),             dcol=1, style=LEFT,  newrow=True)
        self.Add(self.sino_data,                       dcol=2, style=LEFT)
        self.Add(self.tomo_save,                       dcol=2, style=LEFT)

        #################################################################################
        self.pack()

    def onDTCorrect(self, event=None):
        self.owner.current_file.dtcorrect = self.use_dtcorr.IsChecked()

    def onHotCols(self, event=None):
        self.owner.current_file.hotcols = self.use_hotcols.IsChecked()

    def update_xrmmap(self, xrmfile=None):

        if xrmfile is None:
            xrmfile = self.owner.current_file

        self.cfile  = xrmfile
        self.xrmmap = self.cfile.xrmmap


        if self.cfile.get_rotation_axis() is None:
            self.center_value.SetValue(0)
            return

        self.set_det_choices()

        try:
            self.npts = len(self.cfile.get_pos(0, mean=True))
        except:
            self.npts = len(self.cfile.get_pos('x', mean=True))

        center = self.cfile.get_tomography_center()
        self.center_value.SetRange(-0.5*self.npts,1.5*self.npts)
        self.center_value.SetValue(center)

        self.plotSELECT()


    def onALGchoice(self,event=None):

        alg = self.tomo_algo.GetStringSelection().lower()
        enable_filter = False
        enable_niter = False

        if alg.startswith('gridrec'):
            enable_filter = True
        else:
            enable_niter = True

        self.tomo_niter.Enable(enable_niter)
        self.tomo_filt.Enable(enable_filter)


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
        plt3 = 'three' in self.plot_choice.GetStringSelection().lower()

        det_name, roi_name, plt_name = [], [], []
        for det, roi in zip(self.det_choice,self.roi_choice):
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

        if xrmfile is None:
            xrmfile = self.owner.current_file

        args={'trim_sino' : flagxrd,
              'hotcols'   : False,
              'dtcorrect' : self.owner.dtcor}

        x     = xrmfile.get_translation_axis(hotcols=args['hotcols'])
        omega = xrmfile.get_rotation_axis(hotcols=args['hotcols'])

        if omega is None:
            print('\n** Cannot compute tomography: no rotation axis specified in map. **')
            return

        # check for common case of a few too many angles -- in which case, always
        # remove the first and last:
        domega  = abs(np.diff(omega).mean())
        if abs(omega[-1] - omega[0]) > 360+2*domega:
            omega = omega[1:-1]
            args['hotcols'] = True

        def normalize_map(xmap, normmap, roiname):
            xmap /= normmap
            label = ''
            if self.i1trans.IsChecked() and roiname.lower().startswith('i1'):
                xmap = -np.log(xmap)
                xmrange = xmap.max()-xmap.min()
                xmap = (xmap - xmap.min() + 1.e-6*xmrange)/xmrange
                label = '-log'
            return xmap, label

        normmap = 1.
        if roi_name[-1] != '1':
            normmap, sino_order = xrmfile.get_sinogram(roi_name[-1],det=det_name[-1], **args)
            normmap[np.where(normmap==0)] = 1.

        r_map, sino_order = xrmfile.get_sinogram(roi_name[0], det=det_name[0], **args)
        r_map, r_lab = normalize_map(r_map, normmap, roi_name[0])


        if plt3:
            g_map, sino_order = xrmfile.get_sinogram(roi_name[1], det=det_name[1], **args)
            b_map, sino_order = xrmfile.get_sinogram(roi_name[2], det=det_name[2], **args)
            g_map, g_lab = normalize_map(g_map, normmap, roi_name[1])
            b_map, b_lab = normalize_map(b_map, normmap, roi_name[2])


        pref, fname = os.path.split(xrmfile.filename)
        if plt3:
            sino = np.array([r_map, g_map, b_map])
            sino.resize(tuple(i for i in sino.shape if i!=1))
            title = fname
            info = ''
            if roi_name[-1] == '1':
                subtitles = {'red':   'Red: %s'   % plt_name[0],
                             'green': 'Green: %s' % plt_name[1],
                             'blue':  'Blue: %s'  % plt_name[2]}
            else:
                subtitles = {'red':   'Red: %s(%s/%s)'   % (r_lab, plt_name[0], plt_name[-1]),
                             'green': 'Green: %s(%s/%s)' % (g_lab, plt_name[1], plt_name[-1]),
                             'blue':  'Blue: %s(%s/%s)'  % (b_lab, plt_name[2], plt_name[-1])}

        else:
            sino = r_map
            if roi_name[-1] == '1':
                title = plt_name[0]
            else:
                title = '%s(%s/%s)' % (r_lab, plt_name[0] , plt_name[-1])
            title = '%s: %s' % (fname, title)
            info  = 'Intensity: [%g, %g]' %(sino.min(), sino.max())
            subtitle = None

        return title, subtitles, info, x, omega, sino_order, sino

    def onSaveTomograph(self, event=None):

        xrmfile = self.owner.current_file
        detpath = self.sino_data.GetStringSelection()
        center = self.center_value.GetValue()

        if not self.owner.dtcor and 'scalars' in detpath:
            detpath = '%s_raw' % detpath

        print('\nSaving tomographic reconstruction for %s ...' % detpath)

        xrmfile.save_tomograph(detpath,
                               algorithm=self.tomo_algo.GetStringSelection(),
                               filter_name=self.tomo_filt.GetStringSelection(),
                               num_iter=self.tomo_niter.GetValue(),
                               center=center, dtcorrect=self.owner.dtcor,
                               hotcols=xrmfile.hotcols)
        print('Saved.')


    def onShowTomograph(self, event=None, new=True):
        xrmfile = self.owner.current_file
        det = None
        title, subtitles, info, x, omega, sino_order, sino = self.calculateSinogram()

        algorithm = self.tomo_algo.GetStringSelection()
        filter_name = self.tomo_filt.GetStringSelection()
        niter = self.tomo_niter.GetValue()
        center = self.center_value.GetValue()
        refine_center = self.refine_center.GetValue()

        tomo = xrmfile.get_tomograph(sino, refine_center=refine_center,
                                     algorithm=algorithm,
                                     filter_name=filter_name, num_iter=niter,
                                     center=center, omega=omega,
                                     sinogram_order=sino_order,
                                     hotcols=xrmfile.hotcols)

        if refine_center:
            self.set_center(xrmfile.xrmmap['tomo/center'].value)
            self.refine_center.SetValue(False)

        omeoff, xoff = 0, 0
        title = '%s, center=%0.1f' % (title, center)

        ## for one color plot
        if sino.shape[0] == 1 and tomo.shape[0] == 1:
            sino = sino[0]
            tomo = tomo[0]
            det = self.det_choice[0].GetStringSelection()

        if len(self.owner.tomo_displays) == 0 or new:
            iframe = self.owner.add_tomodisplay(title)
        self.owner.display_tomo(tomo, title=title, subtitles=subtitles, det=det)

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
