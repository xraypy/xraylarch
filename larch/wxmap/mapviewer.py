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
from collections import OrderedDict

import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception


HAS_DV = False
try:
    import wx.dataview as dv
    DVSTY = dv.DV_SINGLE|dv.DV_VERT_RULES|dv.DV_ROW_LINES
    HAS_DV = True
except:
    pass

HAS_EPICS = False
try:
    from epics import caput
    HAS_EPICS = True
except:
    pass

#import h5py
import numpy as np
import scipy.stats as stats

#from matplotlib.widgets import Slider, Button, RadioButtons

from wxmplot import PlotFrame


import larch
from larch.larchlib import read_workdir, save_workdir
from larch.wxlib import (LarchPanel, LarchFrame, EditableListBox, SimpleText,
                         FloatCtrl, Font, pack, Popup, Button, MenuItem,
                         Choice, Check, GridPanel, FileSave, HLine, flatnotebook)
from larch.utils.strutils import bytes2str, version_ge
from larch.io import nativepath
from larch.site_config import icondir

from ..xrd import lambda_from_E, xrd1d, save1D, calculate_xvalues
from ..xrmmap import GSEXRM_MapFile, GSEXRM_FileStatus, h5str, ensure_subgroup
from ..epics import pv_fullname
from ..wxlib.xrfdisplay import XRFDisplayFrame

from .mapimageframe import MapImageFrame, CorrelatedMapFrame
from .mapmathpanel import MapMathPanel
from .maptomopanel import TomographyPanel

from ..wxxrd import XRD1DViewerFrame, XRD2DViewerFrame

FONTSIZE = 8
if platform.system() in ('Windows', 'Darwin'):
    FONTSIZE = 10

CEN = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
RIGHT = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
ALL_CEN =  wx.ALL|CEN
ALL_LEFT =  wx.ALL|LEFT
ALL_RIGHT =  wx.ALL|RIGHT


FILE_WILDCARDS = 'X-ray Maps (*.h5)|*.h5|All files (*.*)|*.*'

XRF_ICON_FILE = 'gse_xrfmap.ico'

NOT_OWNER_MSG = """The File
   '%s'
appears to be open by another process.  Having two
processes writing to the file can cause corruption.

Do you want to take ownership of the file?
"""

NOT_GSEXRM_FILE = """The File
   '%s'
doesn't seem to be a Map File
"""

NOT_GSEXRM_FOLDER = """The Folder
   '%s'
doesn't seem to be a Map Folder
"""
FILE_ALREADY_READ = """The File
   '%s'
has already been read.
"""

FRAMESTYLE = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL
BEAMLINE = '13-ID-E'
FACILITY = 'APS'

PLOT_TYPES = ('Single ROI Map', 'Three ROI Map', 'Correlation Plot')
PLOT_OPERS = ('/', '*', '-', '+')

ESCAN_CRED = os.environ.get('ESCAN_CREDENTIALS', None)
if ESCAN_CRED is not None:
    try:
        from ..epics.larchscan import connect_scandb
    except ImportError:
        ESCAN_CRED = None

class MapPanel(GridPanel):
    '''Panel of Controls for viewing maps'''
    label  = 'ROI Map'
    def __init__(self, parent, owner=None, **kws):

        self.owner = owner
        self.cfile,self.xrmmap = None,None

        GridPanel.__init__(self, parent, nrows=8, ncols=6, **kws)

        self.plot_choice = Choice(self, choices=PLOT_TYPES, size=(140, -1))
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
                          SimpleText(self, 'Normalization')]
        self.roi_label = [SimpleText(self,''),
                          SimpleText(self,''),
                          SimpleText(self,''),
                          SimpleText(self,'')]

        fopts = dict(minval=-50000, precision=0, size=(70, -1))
        self.lims = [FloatCtrl(self, value= 0, **fopts),
                     FloatCtrl(self, value=-1, **fopts),
                     FloatCtrl(self, value= 0, **fopts),
                     FloatCtrl(self, value=-1, **fopts)]

        self.zigoff = FloatCtrl(self, value= 0, minval=-15, maxval=15,
                                precision=0, size=(70, -1))
        for wid in self.lims:
            wid.Disable()

        self.use_dtcorr  = Check(self, default=True,
                                 label='Correct for Detector Deadtime',
                                 action=self.onDTCorrect)
        self.use_hotcols = Check(self, default=False,
                                 label='Remove First and Last columns',
                                 action=self.onHotCols)

        self.use_zigzag = Check(self, default=False, label='Fix ZigZag',
                                action=self.onZigZag)

        self.limrange  = Check(self, default=False,
                               label=' Limit Map Range to Pixel Range:',
                               action=self.onLimitRange)

        map_shownew = Button(self, 'New Map',     size=(140, -1),
                               action=partial(self.onROIMap, new=True))
        map_update  =  Button(self, 'Replace', size=(140, -1),
                              action=partial(self.onROIMap, new=False))
        map_process =  Button(self, 'Add Rows from Raw Data', size=(250, -1),
                              action=self.onProcessMap)
        self.map_process = map_process

        self.AddMany((SimpleText(self,'Plot type:'), self.plot_choice),
                     style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,''), self.det_label[0],
                      self.det_label[1], self.det_label[2], self.det_label[3]),
                     style=LEFT,  newrow=True)

        self.AddMany((SimpleText(self,'Detector:'), self.det_choice[0],
                      self.det_choice[1], self.det_choice[2], self.det_choice[3]),
                     style=LEFT,  newrow=True)

        self.AddMany((SimpleText(self,'ROI:'),self.roi_choice[0],
                       self.roi_choice[1],self.roi_choice[2], self.roi_choice[3]),
                     style=LEFT,  newrow=True)

        self.AddMany((SimpleText(self,''),self.roi_label[0],
                      self.roi_label[1],self.roi_label[2], self.roi_label[3]),
                     style=LEFT,  newrow=True)
        self.Add((5, 5),                        dcol=1, style=LEFT,  newrow=True)
        self.Add(SimpleText(self, 'Display:'),   dcol=1, style=LEFT, newrow=True)
        self.Add(map_shownew,      dcol=1, style=LEFT)
        self.Add(map_update,       dcol=1, style=LEFT)
        self.Add(map_process,      dcol=2, style=LEFT)

        self.Add(HLine(self, size=(600, 5)),    dcol=8, style=LEFT, newrow=True)
        self.Add(SimpleText(self,'Options:'),   dcol=1, style=LEFT, newrow=True)
        self.Add(self.use_dtcorr,               dcol=2, style=LEFT)
        self.Add((5, 5),                        dcol=1, style=LEFT,  newrow=True)
        self.Add(self.use_hotcols,              dcol=2, style=LEFT)
        self.Add((5, 5),                        dcol=1, style=LEFT,  newrow=True)
        self.Add(self.limrange,                 dcol=2, style=LEFT)
        self.Add((5, 5),                        dcol=1, style=LEFT,  newrow=True)
        self.Add(SimpleText(self, 'X Range:'),  dcol=1, style=LEFT)
        self.Add(self.lims[0],                  dcol=1, style=LEFT)
        self.Add(self.lims[1],                  dcol=1, style=LEFT)
        self.Add((5, 5),                        dcol=1, style=LEFT,  newrow=True)
        self.Add(SimpleText(self, 'Y Range:'),  dcol=1, style=LEFT)
        self.Add(self.lims[2],                  dcol=1, style=LEFT)
        self.Add(self.lims[3],                  dcol=1, style=LEFT)
        self.Add((5, 5),                        dcol=1, style=LEFT,  newrow=True)
        self.Add(self.use_zigzag,               dcol=1, style=LEFT)
        self.Add(self.zigoff,                   dcol=1, style=LEFT)

        self.Add(HLine(self, size=(600, 5)),    dcol=8, style=LEFT,  newrow=True)
        self.pack()

    def onDTCorrect(self, event=None):
        self.owner.current_file.dtcorrect = self.use_dtcorr.IsChecked()

    def onHotCols(self, event=None):
        self.owner.current_file.hotcols = self.use_hotcols.IsChecked()

    def onZigZag(self, event=None):
        self.owner.current_file.zigzag = 0
        if self.use_zigzag.IsChecked():
            self.owner.current_file.zigzag = int(self.zigoff.GetValue())

    def update_xrmmap(self, xrmfile=None):
        if xrmfile is None:
            xrmfile = self.owner.current_file
        self.cfile  = xrmfile
        self.xrmmap = self.cfile.xrmmap
        self.set_det_choices()
        self.plotSELECT()

    def onLimitRange(self, event=None):
        if self.limrange.IsChecked():
            for wid in self.lims:
                wid.Enable()
        else:
            for wid in self.lims:
                wid.Disable()

    def detSELECT(self,idet,event=None):
        self.set_roi_choices(idet=idet)

    def roiSELECT(self,iroi,event=None):

        detname = self.det_choice[iroi].GetStringSelection()
        roiname = self.roi_choice[iroi].GetStringSelection()

        if version_ge(self.cfile.version, '2.0.0'):
            try:
                roi = self.cfile.xrmmap['roimap'][detname][roiname]
                limits = roi['limits'][:]
                units =  bytes2str(roi['limits'].attrs.get('units',''))
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
                for i in (1, 2):
                    self.det_choice[i].Disable()
                    self.roi_choice[i].Disable()
                    self.roi_label[i].SetLabel('')
                for i, label in enumerate([' Map ', ' ', ' ']):
                    self.det_label[i].SetLabel(label)
            elif 'three' in plot_type:
                for i in (1, 2):
                    self.det_choice[i].Enable()
                    self.roi_choice[i].Enable()
                for i, label in enumerate(['Red', 'Green', 'Blue']):
                    self.det_label[i].SetLabel(label)
                self.set_roi_choices()
            elif 'correl' in plot_type:
                self.det_choice[1].Enable()
                self.roi_choice[1].Enable()
                self.det_choice[2].Disable()
                self.roi_choice[2].Disable()
                for i, label in enumerate([' X ',' Y ', '']):
                    self.det_label[i].SetLabel(label)
                self.set_roi_choices()

    def onClose(self):
        for p in self.plotframes:
            try:
                p.Destroy()
            except:
                pass

    def ShowMap(self, xrmfile=None, new=True):
        subtitles = None
        plt3 = 'three' in self.plot_choice.GetStringSelection().lower()

        if xrmfile is None:
            xrmfile = self.owner.current_file

        self.onZigZag()

        args={'hotcols'   : xrmfile.hotcols,
              'dtcorrect' : xrmfile.dtcorrect}

        det_name, roi_name, plt_name = [], [], []
        for det, roi in zip(self.det_choice, self.roi_choice):
            det_name += [det.GetStringSelection()]
            roi_name += [roi.GetStringSelection()]
            if det_name[-1] == 'scalars':
                plt_name += ['%s' % roi_name[-1]]
            else:
                plt_name += ['%s(%s)' % (roi_name[-1],det_name[-1])]

        mapx = 1.0
        if roi_name[-1] != '1':
            mapx = xrmfile.get_roimap(roi_name[-1], det=det_name[-1], **args)
            mapx[np.where(mapx==0)] = 1.

        r_map = xrmfile.get_roimap(roi_name[0], det=det_name[0], **args)
        if plt3:
            g_map = xrmfile.get_roimap(roi_name[1], det=det_name[1], **args)
            b_map = xrmfile.get_roimap(roi_name[2], det=det_name[2], **args)

        x = xrmfile.get_pos(0, mean=True)
        y = xrmfile.get_pos(1, mean=True)

        pref, fname = os.path.split(xrmfile.filename)

        if plt3:
            map = np.array([r_map/mapx, g_map/mapx, b_map/mapx])
            map = np.einsum('kij->ijk', map)

            title = fname
            info = ''
            if roi_name[-1] == '1':
                subtitles = {'red':   'Red: %s'   % plt_name[0],
                             'green': 'Green: %s' % plt_name[1],
                             'blue':  'Blue: %s'  % plt_name[2]}
            else:
                subtitles = {'red':   'Red: %s / %s'   % (plt_name[0], plt_name[-1]),
                             'green': 'Green: %s / %s' % (plt_name[1], plt_name[-1]),
                             'blue':  'Blue: %s / %s'  % (plt_name[2], plt_name[-1])}

        else:
            map = r_map/mapx
            if roi_name[-1] == '1':
                title = plt_name[0]
            else:
                title = '%s / %s' % (plt_name[0], plt_name[-1])
            title = '%s: %s' % (fname, title)
            info  = 'Intensity: [%g, %g]' %(map.min(), map.max())
            subtitle = None

        det = None
        if (plt3 and det_name[0]==det_name[1] and det_name[0]==det_name[2]) or not plt3:
            for s in det_name[0]:
                if s.isdigit(): det = int(s)

        if len(self.owner.im_displays) == 0 or new:
            iframe = self.owner.add_imdisplay(title, det=det)

        xoff, yoff = 0, 0
        if self.limrange.IsChecked():
            lims = [wid.GetValue() for wid in self.lims]
            map = map[lims[2]:lims[3], lims[0]:lims[1]]
            xoff, yoff = lims[0], lims[2]

        self.owner.display_map(map, title=title, info=info, x=x, y=y, det=det,
                               xoff=xoff, yoff=yoff, subtitles=subtitles,
                               xrmfile=self.cfile)

    def onLasso(self, selected=None, mask=None, data=None, xrmfile=None, **kws):
        if xrmfile is None:
            xrmfile = self.owner.current_file
        ny, nx = xrmfile.get_shape()
        indices = []
        for idx in selected:
            iy, ix = divmod(idx, ny)
            indices.append((ix, iy))


    def ShowCorrel(self, xrmfile=None, new=True):

        if xrmfile is None:
            xrmfile = self.owner.current_file
        self.onZigZag()
        args={'hotcols'   : xrmfile.hotcols,
              'dtcorrect' : xrmfile.dtcorrect}
        det_name,roi_name = [],[]
        plt_name = []

        xdet = self.det_choice[0].GetStringSelection()
        xroi = self.roi_choice[0].GetStringSelection()
        xlab = "%s(%s)" % (xroi, xdet)
        if 'scalar' in xdet.lower():
            xlab = xroi
        ydet = self.det_choice[1].GetStringSelection()
        yroi = self.roi_choice[1].GetStringSelection()

        ylab = "%s(%s)" % (yroi, ydet)
        if 'scalar' in ydet.lower():
            ylab = yroi

        map1 = xrmfile.get_roimap(xroi, det=xdet, **args)
        map2 = xrmfile.get_roimap(yroi, det=ydet, **args)

        x = xrmfile.get_pos(0, mean=True)
        y = xrmfile.get_pos(1, mean=True)

        pref, fname = os.path.split(xrmfile.filename)
        title ='%s: %s vs. %s' %(fname, ylab, xlab)

        correl_plot = CorrelatedMapFrame(parent=self.owner, xrmfile=xrmfile)
        correl_plot.display(map1, map2, name1=xlab, name2=ylab,
                            x=x, y=y, title=title)
        correl_plot.Show()
        correl_plot.Raise()
        self.owner.plot_displays.append(correl_plot)

    def onProcessMap(self, event=None, max_new_rows=None):
        xrmfile = self.owner.current_file
        pref, fname = os.path.split(xrmfile.filename)
        self.owner.process_file(fname, max_new_rows=max_new_rows)
        self.update_xrmmap(xrmfile=self.owner.current_file)

    def onROIMap(self, event=None, new=True, plot=True):
        plot_type = self.plot_choice.GetStringSelection().lower()
        xrmfile = self.owner.current_file
        pref, fname = os.path.split(xrmfile.filename)
        self.owner.process_file(fname, max_new_rows=10)
        if plot:
            if 'correlation' in plot_type:
                self.ShowCorrel(new=new)
            else:
                self.ShowMap(new=new)

    def set_det_choices(self):
        det_list = self.cfile.get_detector_list()
        # print("map panel set_det_choices ", det_list, self.det_choice)
        for det_ch in self.det_choice:
            det_ch.SetChoices(det_list)
        if 'scalars' in det_list: ## should set 'denominator' to scalars as default
            self.det_choice[-1].SetStringSelection('scalars')

        self.set_roi_choices()

    def set_roi_choices(self, idet=None):
        if idet is None:
            for idet, det_ch in enumerate(self.det_choice):
                detname = self.det_choice[idet].GetStringSelection()
                rois = self.update_roi(detname)
                cur = self.roi_choice[idet].GetStringSelection()
                self.roi_choice[idet].SetChoices(rois)
                if cur in rois:
                    self.roi_choice[idet].SetStringSelection(cur)
                self.roiSELECT(idet)
        else:
            detname = self.det_choice[idet].GetStringSelection()
            rois = self.update_roi(detname)
            cur = self.roi_choice[idet].GetStringSelection()
            self.roi_choice[idet].SetChoices(rois)
            if cur in rois:
                self.roi_choice[idet].SetStringSelection(cur)
            self.roiSELECT(idet)

    def update_roi(self, detname):
        return self.cfile.get_roi_list(detname)

class MapInfoPanel(scrolled.ScrolledPanel):
    """Info Panel """
    label  = 'Map Info'
    def __init__(self, parent, owner=None, **kws):
        scrolled.ScrolledPanel.__init__(self, parent, -1,
                                        style=wx.GROW|wx.TAB_TRAVERSAL, **kws)
        self.owner = owner

        sizer = wx.GridBagSizer(3, 3)
        self.wids = {}

        ir = 0

        for label in ('Facility','Run Cycle','Proposal Number','User group',
                      'H5 Map Created',
                      'Scan Time','File Compression','Map Data',
                      'Ring Current', 'X-ray Energy',  'X-ray Intensity (I0)',
                      'Original data path', 'User Comments 1', 'User Comments 2',
                      'Scan Fast Motor', 'Scan Slow Motor', 'Dwell Time',
                      'Sample Fine Stages',
                      'Sample Stage X',     'Sample Stage Y',
                      'Sample Stage Z',     'Sample Stage Theta',
                      'XRD Calibration'):

            ir += 1
            thislabel        = SimpleText(self, '%s:' % label, style=wx.LEFT, size=(125, -1))
            self.wids[label] = SimpleText(self, ' ' ,          style=wx.LEFT, size=(350, -1))

            sizer.Add(thislabel,        (ir, 0), (1, 1), 1)
            sizer.Add(self.wids[label], (ir, 1), (1, 1), 1)

        pack(self, sizer)
        self.SetupScrolling()


    def update_xrmmap(self, xrmfile=None):

        if xrmfile is None: xrmfile = self.owner.current_file
        xrmmap = xrmfile.xrmmap

        def time_between(d1, d2):
            d1 = datetime.datetime.strptime(d1, "%Y-%m-%d %H:%M:%S")
            d2 = datetime.datetime.strptime(d2, "%Y-%m-%d %H:%M:%S")
            diff =  d2 - d1 if d2 > d1 else d1 - d2
            return diff.days,diff.seconds

        config_grp = ensure_subgroup('config',xrmmap)
        notes_grp =  ensure_subgroup('notes',config_grp)
        time_str =  bytes2str(notes_grp.attrs.get('h5_create_time',''))

        self.wids['H5 Map Created'].SetLabel(time_str)

        try:
            d,s = time_between(bytes2str(notes_grp.attrs.get('scan_start_time','')),
                               bytes2str(notes_grp.attrs.get('scan_end_time','')))
            time_str =  str(datetime.timedelta(days=d,seconds=s))
        except:
            time_str = bytes2str(xrmmap.attrs.get('Start_Time',''))

        self.wids['Scan Time'].SetLabel( time_str )
        self.wids['File Compression'].SetLabel(bytes2str(xrmmap.attrs.get('Compression','')))

        comments = h5str(xrmmap['config/scan/comments'].value).split('\n', 2)
        for i, comm in enumerate(comments):
            self.wids['User Comments %i' %(i+1)].SetLabel(comm)

        pos_addrs = [str(x) for x in xrmmap['config/positioners'].keys()]
        pos_label = [h5str(x.value) for x in xrmmap['config/positioners'].values()]

        scan_pos1 = h5str(xrmmap['config/scan/pos1'].value)
        scan_pos2 = h5str(xrmmap['config/scan/pos2'].value)
        i1 = pos_addrs.index(scan_pos1)
        i2 = pos_addrs.index(scan_pos2)

        start1 = float(xrmmap['config/scan/start1'].value)
        start2 = float(xrmmap['config/scan/start2'].value)
        stop1  = float(xrmmap['config/scan/stop1'].value)
        stop2  = float(xrmmap['config/scan/stop2'].value)

        step1 = float(xrmmap['config/scan/step1'].value)
        step2 = float(xrmmap['config/scan/step2'].value)

        npts1 = int((abs(stop1 - start1) + 1.1*step1)/step1)
        npts2 = int((abs(stop2 - start2) + 1.1*step2)/step2)

        sfmt = '%s: [%.4f:%.4f], step=%.4f, %i pixels'
        scan1 = sfmt % (pos_label[i1], start1, stop1, step1, npts1)
        scan2 = sfmt % (pos_label[i2], start2, stop2, step2, npts2)

        rowtime = float(xrmmap['config/scan/time1'].value)

        self.wids['Scan Fast Motor'].SetLabel(scan1)
        self.wids['Scan Slow Motor'].SetLabel(scan2)
        pixtime = xrmfile.pixeltime
        if pixtime is None:
            pixtime = xrmfile.calc_pixeltime()
        pixtime =int(round(1000.0*pixtime))
        self.wids['Dwell Time'].SetLabel('%.1f ms per pixel' % pixtime)

        env_names = list(xrmmap['config/environ/name'])
        env_vals  = list(xrmmap['config/environ/value'])
        env_addrs = list(xrmmap['config/environ/address'])

        fines = {'X': '?', 'Y': '?'}
        i0vals = {'flux':'?', 'current':'?'}
        cur_energy = ''

        for name, addr, val in zip(env_names, env_addrs, env_vals):
            name = bytes2str(name).lower()
            val = h5str(val)

            if 'ring_current' in name or 'ring current' in name:
                self.wids['Ring Current'].SetLabel('%s mA' % val)
            elif ('mono.energy' in name or 'mono energy' in name) and cur_energy=='':
                self.owner.current_energy = float(val)/1000.
                xrmfile.mono_energy = float(val)/1000.
                wvlgth = lambda_from_E(self.owner.current_energy)
                self.wids['X-ray Energy'].SetLabel(u'%0.3f keV (%0.3f \u00c5)' % \
                                                   (self.owner.current_energy,wvlgth))
                cur_energy = val
            elif 'beamline.fluxestimate' in name or 'transmitted flux' in name:
                i0vals['flux'] = val
            elif 'i0 current' in name:
                i0vals['current'] = val

            elif name.startswith('sample'):
                name = name.replace('samplestage.', '')
                if 'coarsex' in name or 'coarse x' in name:
                    self.wids['Sample Stage X'].SetLabel('%s mm' % val)
                elif 'coarsey' in name or 'coarse y' in name:
                    self.wids['Sample Stage Y'].SetLabel('%s mm' % val)
                elif 'coarsez' in name or 'coarse z' in name:
                    self.wids['Sample Stage Z'].SetLabel('%s mm' % val)
                elif 'theta' in name:
                    self.wids['Sample Stage Theta'].SetLabel('%s deg' % val)
                elif 'finex' in name or 'fine x' in name:
                    fines['X'] = val
                elif 'finey' in name or 'fine y' in name:
                    fines['Y'] = val

        if i0vals['current'] == '?':
            i0val = 'Flux=%(flux)s Hz' % i0vals
        else:
            i0val = u'Flux=%(flux)s Hz, I0 Current=%(current)s \u03BCA' % i0vals
        self.wids['X-ray Intensity (I0)'].SetLabel(i0val)
        self.wids['Sample Fine Stages'].SetLabel('X, Y = %(X)s, %(Y)s mm' % (fines))

        folderpath = bytes2str(xrmmap.attrs.get('Map_Folder',''))
        if len(folderpath) > 35:
            folderpath = '...'+folderpath[-35:]
        self.wids['Original data path'].SetLabel(folderpath)

        self.wids['XRD Calibration'].SetLabel('')
        xrd_calibration = ''
        if 'xrd1d' in xrmmap:
            xrd_calibration = bytes2str(xrmmap['xrd1d'].attrs.get('calfile',''))
        if not os.path.exists(xrd_calibration):
            xrd_calibration = ''
        self.wids['XRD Calibration'].SetLabel(os.path.split(xrd_calibration)[-1])

        notes = {}
        config_grp = ensure_subgroup('config',xrmmap)
        notes_grp =  ensure_subgroup('notes',config_grp)
        for key in notes_grp.attrs.keys():
            try:
                notes[key] = bytes2str(notes_grp.attrs[key])
            except:
                pass
        note_title = ['Facility','Run Cycle','Proposal Number','User group']
        note_str = ['','','','']
        if 'beamline' in notes and 'facility' in notes:
            note_str[0] = '%s @ %s' % (notes['beamline'],notes['facility'])
        if 'run' in notes:
            note_str[1] = notes['run']
        if 'proposal' in notes:
            note_str[2] = notes['proposal']
        if 'user' in notes:
            note_str[3] = notes['user']

        for title,note in zip(note_title,note_str):
            self.wids[title].SetLabel(note)

        xrmfile.reset_flags()
        if xrmfile.has_xrf:
            if xrmfile.has_xrd2d and xrmfile.has_xrd1d:
                datastr = 'XRF, 2D- and 1D-XRD data'
            elif xrmfile.has_xrd2d:
                datastr = 'XRF, 2D-XRD data'
            elif xrmfile.has_xrd1d:
                datastr = 'XRF, 1D-XRD data'
            else:
                datastr = 'XRF data'
        else:
            if xrmfile.has_xrd2d and xrmfile.has_xrd1d:
                datastr = '2D- and 1D-XRD data'
            elif xrmfile.has_xrd2d:
                datastr = '2D-XRD data'
            elif xrmfile.has_xrd1d:
                datastr = '1D-XRD data'
            else:
                datastr = ''

        self.wids['Map Data'].SetLabel(datastr)

    def onClose(self):
        pass


class MapAreaPanel(scrolled.ScrolledPanel):

    label  = 'Map Areas'
    delstr = """    Delete Area '%s'?

    WARNING: This cannot be undone!

    """

    def __init__(self, parent, owner=None, **kws):
        scrolled.ScrolledPanel.__init__(self, parent, -1,
                                        style=wx.GROW|wx.TAB_TRAVERSAL, **kws)

        ######################################
        ## GENERAL MAP AREAS
        self.owner = owner
        pane = wx.Panel(self)
        sizer = wx.GridBagSizer(3, 3)
        self.choices = {}
        bsize = (140, -1)
        self.choice = Choice(pane, size=(225, -1), action=self.onSelect)
        self.desc    = wx.TextCtrl(pane,   -1, '',  size=(225, -1))
        self.info1   = wx.StaticText(pane, -1, '',  size=(275, -1))
        self.info2   = wx.StaticText(pane, -1, '',  size=(275, -1))
        self.onmap   = Button(pane, 'Show on Map',  size=bsize, action=self.onShow)
        self.clear   = Button(pane, 'Clear Map',    size=bsize, action=self.onClear)
        self.bdelete = Button(pane, 'Delete',       size=bsize, action=self.onDelete)
        self.update  = Button(pane, 'Apply',        size=bsize, action=self.onLabel)
        self.bexport = Button(pane, 'Export Areas', size=bsize, action=self.onExport)
        self.bimport = Button(pane, 'Import Areas', size=bsize, action=self.onImport)
        self.bcopy   = Button(pane, 'Copy to Other Maps',  size=bsize, action=self.onCopy)
        self.xrf     = Button(pane, 'Show XRF (Fore)', size=bsize, action=self.onXRF)
        self.xrf2    = Button(pane, 'Show XRF (Back)', size=bsize,
                              action=partial(self.onXRF, as_mca2=True))

        self.onstats  = Button(pane, 'Calculate XRF Stats', size=bsize,
                               action=self.onShowStats)
        self.onreport = Button(pane, 'Save XRF Stats', size=bsize,
                               action=self.onReport)

        self.xrd1d_plot  = Button(pane, 'Show 1D XRD', size=bsize,
                                  action=partial(self.onXRD,show=True,xrd1d=True))

        self.xrd2d_plot  = Button(pane, 'Show 2D XRD', size=bsize,
                                  action=partial(self.onXRD,show=True,xrd2d=True))

        legend = wx.StaticText(pane, -1, 'Values in Counts per second', size=(200, -1))

        #  self.cor = Check(pane, label='Correct Deadtime?')
        # self.xrd2d_save  = Button(pane, 'Save 2D XRD Data', size=bsize,
        #                           action=partial(self.onXRD,save=True,xrd2d=True))
        # self.xrd1d_save  = Button(pane, 'Save 1D XRD Data', size=bsize,
        #                           action=partial(self.onXRD,save=True,xrd1d=True))

        def txt(s):
            return SimpleText(pane, s)
        irow = 1
        sizer.Add(txt('Map Areas and Saved Points'),  ( 0, 0), (1, 5), ALL_CEN,  2)
        sizer.Add(txt('Area: '),            (irow, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.choice,              (irow, 1), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.bdelete,             (irow, 3), (1, 1), ALL_LEFT, 2)


        irow += 1
        sizer.Add(txt('Info: '),            (irow, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.info1,               (irow, 1), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.info2,               (irow, 3), (1, 2), ALL_LEFT, 2)

        irow += 1
        sizer.Add(txt('Rename: '),          (irow, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.desc,                (irow, 1), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.update,              (irow, 3), (1, 1), ALL_LEFT, 2)

        irow += 1
        sizer.Add(txt('Show: '),            (irow, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.onmap,               (irow, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.clear,               (irow, 2), (1, 1), ALL_LEFT, 2)

        irow += 1
        sizer.Add(txt('Save: '),            (irow, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.bexport,             (irow, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.bimport,             (irow, 2), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.bcopy,               (irow, 3), (1, 1), ALL_LEFT, 2)

        irow += 1
        sizer.Add(txt('XRF: '),             (irow, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.xrf,                 (irow, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.xrf2,                (irow, 2), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.onstats,             (irow, 3), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.onreport,            (irow, 4), (1, 1), ALL_LEFT, 2)


        irow += 1
        sizer.Add(txt('XRD: '),             (irow, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.xrd1d_plot,          (irow, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.xrd2d_plot,          (irow, 2), (1, 1), ALL_LEFT, 2)

        # sizer.Add(self.xrd1d_save,          (irow, 0), (1, 2), ALL_LEFT, 2)
        # sizer.Add(self.xrd2d_save,          (irow, 2), (1, 2), ALL_LEFT, 2)
        irow += 1
        sizer.Add(legend,                   (irow, 1), (1, 2), ALL_LEFT, 2)
        pack(pane, sizer)

        for btn in (self.xrd1d_plot, self.xrd2d_plot):
            btn.Disable()

        # main sizer
        msizer = wx.BoxSizer(wx.VERTICAL)
        msizer.Add(pane, 0, wx.ALIGN_LEFT|wx.ALL, 1)

        msizer.Add(wx.StaticLine(self, size=(375, 2), style=wx.LI_HORIZONTAL),
                      0, wx.EXPAND|wx.ALL, 1)

        self.report = None
        if HAS_DV:
            rep = self.report = dv.DataViewListCtrl(self, style=DVSTY)
            rep.AppendTextColumn('ROI ',     width=100)
            rep.AppendTextColumn('Min',      width=75)
            rep.AppendTextColumn('Max',      width=75)
            rep.AppendTextColumn('Mean ',    width=75)
            rep.AppendTextColumn('Sigma',    width=75)
            rep.AppendTextColumn('Median',   width=75)
            rep.AppendTextColumn('Mode',     width=75)
            for col in range(7):
                align = wx.ALIGN_RIGHT
                if col == 0: align = wx.ALIGN_LEFT
                rep.Columns[col].Sortable = False
                rep.Columns[col].Renderer.Alignment = align
                rep.Columns[col].Alignment = align

            rep.SetMinSize((590, 300))
            msizer.Add(rep, 1, wx.ALIGN_LEFT|wx.ALL, 1)

        pack(self, msizer)
        self.SetupScrolling()

    def onCopy(self, event=None):
        xrmfile   = self.owner.current_file
        xrmmap    = xrmfile.xrmmap
        print("Copy Area : shape", xrmfile, xrmmap.shape)

    def show_stats(self):
        # self.stats = self.xrmfile.get_area_stats(self.areaname)
        if self.report is None:
            return

        self.report.DeleteAllItems()
        self.report_data = []

        def report_info(dname,d):
            try:
                hmean, gmean = stats.gmean(d), stats.hmean(d)
                skew, kurtosis = stats.skew(d), stats.kurtosis(d)
            except ValueError:
                hmean, gmean, skew, kurtosis = 0, 0, 0, 0

            smode = '--'
            fmt = '{:,.1f}'.format # use thousands commas, 1 decimal place
            mode = stats.mode(d)
            if len(mode) > 0:
                mode = mode[0]
                if len(mode) > 0:
                    smode = fmt(mode[0])
            dat = (dname, fmt(d.min()), fmt(d.max()), fmt(d.mean()),
                   fmt(d.std()), fmt(np.median(d)), smode)
            self.report_data.append(dat)
            self.report.AppendItem(dat)

        areaname  = self._getarea()
        xrmfile   = self.owner.current_file
        xrmmap    = xrmfile.xrmmap
        ctime     = xrmfile.pixeltime

        area = xrmfile.get_area(name=areaname)
        amask = area.value

        def match_mask_shape(det, mask):
           if mask.shape[1] == det.shape[1] - 2: # hotcols
              det = det[:,1:-1]
           if mask.shape[0] < det.shape[0]:
              det = det[:mask.shape[0]]
           return det[mask]

        if 'roistats' in area.attrs:
           for dat in json.loads(area.attrs.get('roistats','')):
               dat = tuple(dat)
               self.report_data.append(dat)
               self.report.AppendItem(dat)
           self.choice.Enable()
           return

        version = xrmmap.attrs.get('Version','1.0.0')

        if version_ge(version, '2.0.0'):
            d_pref = 'mca'
            d_scas = [d for d in xrmmap['scalars']]
            detnames = ["%s%i" % (d_pref, i) for i in range(1, xrmfile.nmca+1)]
            d_rois = xrmfile.get_roi_list(detnames[0])

        else:
            d_addrs = [d.lower() for d in xrmmap['roimap/det_address']]
            d_names = [d for d in xrmmap['roimap/det_name']]
            d_pref = 'det'


        for i in range(1, xrmfile.nmca+1):
            tname = '%s%i/realtime' % (d_pref, i)
            rtime = xrmmap[tname].value
            if amask.shape[1] == rtime.shape[1] - 2: # hotcols
                rtime = rtime[:,1:-1]

        if version_ge(version, '2.0.0'):
            for scalar in d_scas:
                d = xrmmap['scalars'][scalar].value
                d = match_mask_shape(d, amask)
                report_info(scalar, d/ctime)

            for roi in d_rois:
                for det in detnames:
                    d = xrmfile.get_roimap(roi, det=det, dtcorrect=False)
                    d = match_mask_shape(d, amask)
                    report_info('%s (%s)' % (roi, det), d/ctime)

        else:
            for idet, dname in enumerate(d_names):
                try:
                    daddr = h5str(d_addrs[idet])
                except IndexError:
                    break
                if 'mca' in daddr:
                    det = 1
                    words = daddr.split('mca')
                    if len(words) > 1:
                        det = int(words[1].split('.')[0])

                d = xrmmap['roimap/det_raw'][:,:,idet]
                d = match_mask_shape(d, amask)
                report_info(dname, d/ctime)

        if 'roistats' not in area.attrs:
           area.attrs['roistats'] = json.dumps(self.report_data)
           xrmfile.h5root.flush()

    def update_xrmmap(self, xrmfile=None):
        if xrmfile is None: xrmfile = self.owner.current_file
        xrmmap = xrmfile.xrmmap

        self.set_area_choices(xrmmap, show_last=True)
        self.set_enabled_btns(xrmfile=xrmfile)

        self.report.DeleteAllItems()
        self.report_data = []
        try:
            self.onSelect()
        except:
            pass

    def set_enabled_btns(self, xrmfile=None):
        if xrmfile is None:
            xrmfile = self.owner.current_file

        xrmfile.reset_flags()

        self.xrd2d_plot.Enable(xrmfile.has_xrd2d)
        self.xrd1d_plot.Enable(xrmfile.has_xrd1d)


    def clear_area_choices(self):

        self.info1.SetLabel('')
        self.info2.SetLabel('')
        self.desc.SetValue('')
        self.choice.Clear()

    def set_area_choices(self, xrmmap, show_last=False):

        self.clear_area_choices()

        areas = xrmmap['areas']

        c = self.choice
        c.Clear()
        self.choices = {}
        choice_labels = []
        for a in areas:
            desc = bytes2str(areas[a].attrs.get('description', a))
            self.choices[desc] = a
            choice_labels.append(desc)

        c.AppendItems(choice_labels)
        this_label = ''
        if len(self.choices) > 0:
            idx = 0
        if show_last:
            idx = len(self.choices)-1
        try:
            this_label = choice_labels[idx]
        except:
            return
        c.SetStringSelection(this_label)
        self.desc.SetValue(this_label)


    def onReport(self, event=None):
        aname = self._getarea()
        path, fname = os.path.split(self.owner.current_file.filename)
        deffile = '%s_%s' % (fname, aname)
        deffile = deffile.replace('.', '_') + '.dat'
        outfile = FileSave(self, 'Save Area XRF Statistics File',
                           default_file=deffile,
                           wildcard=FILE_WILDCARDS)

        if outfile is None:
            return

        area  = self.owner.current_file.xrmmap['areas/%s' % aname]

        npix = len(area.value[np.where(area.value)])
        pixtime = self.owner.current_file.pixeltime

        mca   = self.owner.current_file.get_mca_area(aname)
        dtime = mca.real_time
        info_fmt = '%i Pixels, %i ms/pixel, %.3f total seconds'
        buff = ['# Map %s, Area %s' % (self.owner.current_file.filename, aname),
                '# %i Pixels' % npix,
                '# %i ms per pixel' % int(round(1000.0*pixtime)),
                '# %.3f total seconds'  % dtime,
                '# Time (TSCALER) in ms',
                '# All other values in counts per second',
                '#----------------------------------',
                '#  ROI    Min   Max    Mean     Sigma    Median     Mode']
        for dat in self.report_data:
            buff.append('  '.join(dat))
        buff.append('')
        try:
            fout = open(outfile, 'w')
            fout.write('\n'.join(buff))
            fout.close()
        except IOError:
            print('could not write %s' % outfile)


    def _getarea(self):
        return self.choices[self.choice.GetStringSelection()]

    def onExport(self, event=None):
        ofile = self.owner.current_file.export_areas()
        self.owner.message('Exported Areas to %s' % ofile)

    def onImport(self, event=None):
        wildcards = 'Area Files (*_Areas.npz)|*_Areas.npz|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Read Areas File',
                            defaultDir=os.getcwd(),
                            wildcard=wildcards, style=wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            fname = dlg.GetPath().replace('\\', '/')
            self.owner.current_file.import_areas(fname)
            self.owner.message('Imported Areas from %s' % fname)
            self.set_area_choices(self.owner.current_file.xrmmap)
            self.onSelect()

    def onSelect(self, event=None):
        try:
            aname = self._getarea()
        except:
            return
        area  = self.owner.current_file.xrmmap['areas/%s' % aname]
        npix = len(area.value[np.where(area.value)])
        yvals, xvals = np.where(area.value)
        pixtime = self.owner.current_file.pixeltime
        dtime = npix*pixtime
        try:
            mca   = self.owner.current_file.get_mca_area(aname)
            dtime = mca.real_time
        except:
            pass

        info1_fmt = '%i Pixels, %.3f seconds'
        info2_fmt = ' Range (pixels)   X: [%i:%i], Y: [%i:%i] '
        self.info1.SetLabel(info1_fmt % (npix, dtime))
        self.info2.SetLabel(info2_fmt % (xvals.min(), xvals.max(),
                                         yvals.min(), yvals.max()))

        self.desc.SetValue(area.attrs.get('description', aname))
        self.report.DeleteAllItems()
        self.report_data = []
        if 'roistats' in area.attrs:
           self.show_stats()

    def onShowStats(self, event=None):
        if self.report is None:
            return
        self.show_stats()

    def onLabel(self, event=None):
        aname = self._getarea()
        area  = self.owner.current_file.xrmmap['areas/%s' % aname]
        new_label = str(self.desc.GetValue())
        area.attrs['description'] = new_label
        self.owner.current_file.h5root.flush()
        self.set_area_choices(self.owner.current_file.xrmmap)
        self.choice.SetStringSelection(new_label)
        self.desc.SetValue(new_label)

    def onShow(self, event=None):
        aname = self._getarea()
        area  = self.owner.current_file.xrmmap['areas'][aname]
        label = bytes2str(area.attrs.get('description', aname))

        if len(self.owner.tomo_displays) > 0:
            imd = self.owner.tomo_displays[-1]
            try:
                imd.add_highlight_area(area.value, label=label)
            except:
                pass

        if len(self.owner.im_displays) > 0:
            imd = self.owner.im_displays[-1]
            h, w = self.owner.current_file.get_shape()
            highlight = np.zeros((h, w))

            highlight[np.where(area.value)] = 1
            imd.panel.add_highlight_area(highlight, label=label)

    def onDelete(self, event=None):
        aname = self._getarea()
        erase = (wx.ID_YES == Popup(self.owner, self.delstr % aname,
                                    'Delete Area?', style=wx.YES_NO))

        if erase:
            xrmmap = self.owner.current_file.xrmmap
            del xrmmap['areas/%s' % aname]

            self.set_area_choices(xrmmap)

            self.onSelect()

    def onClear(self, event=None):
        if len(self.owner.im_displays) > 0:
            imd = self.owner.im_displays[-1]
            try:
                for area in imd.panel.conf.highlight_areas:
                    for w in area.collections + area.labelTexts:
                        w.remove()
                imd.panel.conf.highlight_areas = []
                imd.panel.redraw()
            except:
                pass

        if len(self.owner.tomo_displays) > 0:
            imd = self.owner.tomo_displays[-1]
            try:
                imd.clear_highlight_area()
            except:
                pass

    def _getmca_area(self, areaname, **kwargs):
        self._mca = self.owner.current_file.get_mca_area(areaname, **kwargs)

    def _getxrd_area(self, areaname, **kwargs):

        self._xrd = None
        self._xrd = self.owner.current_file.get_xrd_area(areaname, **kwargs)

    def onXRF(self, event=None, as_mca2=False):
        aname = self._getarea()
        xrmfile = self.owner.current_file
        area  = xrmfile.xrmmap['areas/%s' % aname]

        label = bytes2str(area.attrs.get('description', aname))
        self._mca  = None


        self.owner.message("Getting XRF Spectra for area '%s'..." % aname)
        mca_thread = Thread(target=self._getmca_area, args=(aname,),
                            kwargs={'dtcorrect': self.owner.dtcor})
        mca_thread.start()
        self.owner.show_XRFDisplay()
        mca_thread.join()

        pref, fname = os.path.split(self.owner.current_file.filename)
        npix = len(area.value[np.where(area.value)])
        self._mca.filename = fname
        self._mca.title = label
        self._mca.npixels = npix
        self.owner.message("Plotting XRF Spectra for area '%s'..." % aname)
        self.owner.xrfdisplay.plotmca(self._mca, as_mca2=as_mca2)

    def onXRD(self, event=None, save=False, show=False,
              xrd1d=False, xrd2d=False, verbose=True):

        try:
            aname = self._getarea()
            xrmfile = self.owner.current_file
            area  = xrmfile.xrmmap['areas/%s' % aname]

            title = area.attrs.get('description', aname)

            env_names = list(xrmfile.xrmmap['config/environ/name'])
            env_vals  = list(xrmfile.xrmmap['config/environ/value'])
            for name, val in zip(env_names, env_vals):
                if 'mono.energy' in str(name).lower():
                    energy = float(val)/1000.
        except:
            if verbose:
                print('No map file and/or areas specified.')
            return

        xrmfile.reset_flags()
        if not xrmfile.has_xrd1d and not xrmfile.has_xrd2d:
            if verbose:
                print('No XRD data in map file: %s' % self.owner.current_file.filename)
            return

        ponifile = bytes2str(xrmfile.xrmmap['xrd1d'].attrs.get('calfile',''))
        ponifile = ponifile if os.path.exists(ponifile) else None

        if show:
            self.owner.message('Plotting XRD pattern for \'%s\'...' % title)
        if save:
            self.owner.message('Saving XRD pattern for \'%s\'...' % title)
            path,stem = os.path.split(self.owner.current_file.filename)
            stem = '%s_%s' % (stem,title)

        kwargs = dict(filename=self.owner.current_file.filename,
                      npixels = len(area.value[np.where(area.value)]),
                      energy = self.owner.current_energy,
                      calfile = ponifile, title = title, xrd2d=False)

        if xrd1d and xrmfile.has_xrd1d:
            kwargs['xrd'] = '1D'
            self._xrd = xrmfile.get_xrd_area(aname, **kwargs)

            if show:
                label = '%s: %s' % (os.path.split(self._xrd.filename)[-1], title)
                self.owner.display_xrd1d(self._xrd.data1D, self._xrd.q,
                                         self._xrd.energy, label=label)
            if save:
                wildcards = '1D XRD file (*.xy)|*.xy|All files (*.*)|*.*'
                dlg = wx.FileDialog(self, 'Save file as...',
                                   defaultDir=os.getcwd(),
                                   defaultFile='%s.xy' % stem,
                                   wildcard=wildcards,
                                   style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
                if dlg.ShowModal() == wx.ID_OK:
                    filename = dlg.GetPath().replace('\\', '/')
                dlg.Destroy()

                print('\nSaving 1D XRD in file: %s' % (filename))
                save1D(filename, self._xrd.data1D[0], self._xrd.data1D[1], calfile=ponifile)

            ## turns off flag since it has already been displayed/saved
            xrd1d = False


        if xrmfile.has_xrd2d and (xrd2d or xrd1d):
            kwargs['xrd'] = '2D'
            self._getxrd_area(aname,**kwargs)

            if xrd2d:
                if save:
                    wildcards = '2D XRD file (*.tiff)|*.tif;*.tiff;*.edf|All files (*.*)|*.*'
                    dlg = wx.FileDialog(self, 'Save file as...',
                                       defaultDir=os.getcwd(),
                                       defaultFile='%s.tiff' % stem,
                                       wildcard=wildcards,
                                       style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
                    if dlg.ShowModal() == wx.ID_OK:
                        filename = dlg.GetPath().replace('\\', '/')
                    dlg.Destroy()
                    print('\nSaving 2D XRD in file: %s' % (filename))
                    self._xrd.save_2D(file=filename,verbose=True)

                if show:
                    label = '%s: %s' % (os.path.split(self._xrd.filename)[-1], title)
                    self.owner.display_2Dxrd(self._xrd.data2D, label=label, xrmfile=xrmfile,
                                             flip=True)

            if xrd1d and ponifile is not None:
                self._xrd.calc_1D(save=save,verbose=True)
                print("show 1D XRD from 2D XRD")
                # if show:
                    #  label = '%s: %s' % (os.path.split(self._xrd.filename)[-1], title)
                    # self.owner.display_xrd1d(self._xrd.data1D,
                    #                          self._xrd.energy,label=label)


class MapViewerFrame(wx.Frame):
    cursor_menulabels = {'lasso': ('Select Points for XRF Spectra\tCtrl+X',
                                   'Left-Drag to select points for XRF Spectra')}

    def __init__(self, parent=None,  size=(925, 650), _larch=None, use_scandb=False, **kwds):

        kwds['style'] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, parent, -1, size=size,  **kwds)

        self.data = None
        self.use_scandb = use_scandb
        self.filemap = {}
        self.im_displays = []
        self.tomo_displays = []
        self.plot_displays = []
        self.current_file = None

        self.larch_buffer = parent
        if not isinstance(parent, LarchFrame):
            self.larch_buffer = LarchFrame(_larch=_larch, is_standalone=False)

        self.larch_buffer.Show()
        self.larch_buffer.Raise()
        self.larch = self.larch_buffer.larchshell
        self.larch_buffer.Hide()

        self.xrfdisplay = None
        self.xrddisplay1D = None
        self.xrddisplay2D = None

        self.watch_files = False
        self.file_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onFileWatchTimer, self.file_timer)

        self.files_in_progress = []

        # self.hotcols = False
        self.dtcor   = True
        self.showxrd = False

        self.SetTitle('GSE XRM MapViewer')

        self.createMainPanel()

        self.SetFont(Font(FONTSIZE))

        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ['Initializing....', ' ']
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        self.htimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer, self.htimer)
        self.h5convert_done = True
        self.h5convert_irow = 0
        self.h5convert_nrow = 0
        read_workdir('gsemap.dat')

        w0, h0 = self.GetSize()
        w1, h1 = self.GetBestSize()
        self.SetSize((max(w0, w1)+5, max(h0, h1)+5))
        self.SetMinSize((500, 300))

        self.scandb = None
        self.instdb = None
        self.inst_name = None
        self.move_callback = None
        self.current_energy = None


    def CloseFile(self, filename, event=None):
        if filename in self.filemap:
            self.filemap[filename].close()
            self.filemap.pop(filename)

    def createMainPanel(self):
        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(250)

        self.filelist = EditableListBox(splitter, self.ShowFile,
                                        remove_action=self.CloseFile,
                                        size=(250, -1))

        dpanel = self.detailspanel = wx.Panel(splitter)
        self.createNBPanels(dpanel)
        splitter.SplitVertically(self.filelist, self.detailspanel, 1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)
        pack(self, sizer)
        wx.CallAfter(self.init_larch)

    def createNBPanels(self, parent):
        self.title    = SimpleText(parent, 'initializing...', size=(680, -1))

        self.SetBackgroundColour('#F0F0E8')

        nbpanels = OrderedDict()
        for panel in (MapPanel, MapInfoPanel, MapAreaPanel, MapMathPanel,
                      TomographyPanel):
            nbpanels[panel.label] = panel

        self.nb = flatnotebook(parent, nbpanels, panelkws={'owner':self},
                               on_change=self.onNBChanged)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.title, 0, ALL_CEN)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)
        parent.SetSize((700, 400))
        pack(parent, sizer)

    def onNBChanged(self, event=None):
        callback = getattr(self.nb.GetCurrentPage(), 'on_select', None)
        if callable(callback):
            callback()

    def get_mca_area(self, mask, xoff=0, yoff=0, det=None, xrmfile=None):
        if xrmfile is None:
            xrmfile = self.current_file
        aname = xrmfile.add_area(mask)
        self.sel_mca = xrmfile.get_mca_area(aname, det=det)

    def lassoHandler(self, mask=None, xrmfile=None, xoff=0, yoff=0, det=None,
                     **kws):

        if xrmfile is None:
            xrmfile = self.current_file

        ny, nx = xrmfile.get_shape()
        if mask.sum() < 1:
            return

        if (xoff>0 or yoff>0) or mask.shape != (ny, nx):
            if mask.shape == (nx, ny): ## sinogram
                mask = np.swapaxes(mask,0,1)
            # elif mask.shape == (ny, ny) or mask.shape == (nx, nx): ## tomograph
            #    tomo = True
            else:
                ym, xm = mask.shape
                tmask = np.zeros((ny, nx)).astype(bool)
                xmax = min(nx, xm+xoff)
                # print("lassoHandler " , ny, nx, ym, xm, xoff, yoff, xmax)
                for iy in range(ym):
                    if iy+yoff < ny:
                        tmask[iy+yoff, xoff:xmax] = mask[iy]
                mask = tmask

        kwargs = dict(xrmfile=xrmfile, xoff=xoff, yoff=yoff, det=det)
        mca_thread = Thread(target=self.get_mca_area,
                            args=(mask,), kwargs=kwargs)
        mca_thread.start()
        self.show_XRFDisplay()
        mca_thread.join()
        if hasattr(self, 'sel_mca'):
            path, fname = os.path.split(xrmfile.filename)
            aname = self.sel_mca.areaname
            area  = xrmfile.xrmmap['areas/%s' % aname]
            npix  = len(area.value[np.where(area.value)])
            self.sel_mca.filename = fname
            self.sel_mca.title = aname
            self.sel_mca.npixels = npix
            self.xrfdisplay.plotmca(self.sel_mca)

            for page in self.nb.pagelist:
                if hasattr(page, 'update_xrmmap'):
                    page.update_xrmmap(xrmfile=self.current_file)

        if self.showxrd:
            for page in self.nb.pagelist:
                if hasattr(page, 'onXRD'):
                    page.onXRD(show=True, xrd1d=True,verbose=False)

    def show_XRFDisplay(self, do_raise=True, clear=True, xrmfile=None):
        'make sure XRF plot frame is enabled and visible'
        if xrmfile is None:
            xrmfile = self.current_file
        if self.xrfdisplay is None:
            self.xrfdisplay = XRFDisplayFrame(parent=self.larch_buffer)

        try:
            self.xrfdisplay.Show()

        except PyDeadObjectError:
            self.xrfdisplay = XRFDisplayFrame(parent=self.larch_buffer)
            self.xrfdisplay.Show()

        if do_raise:
            self.xrfdisplay.Raise()
        if clear:
            self.xrfdisplay.panel.clear()
            self.xrfdisplay.panel.reset_config()

    def onMoveToPixel(self, xval, yval):
        if not HAS_EPICS:
            return

        xrmmap = self.current_file.xrmmap
        pos_addrs = [str(x) for x in xrmmap['config/positioners'].keys()]
        pos_label = [str(x.value) for x in xrmmap['config/positioners'].values()]

        pos1 = str(xrmmap['config/scan/pos1'].value)
        pos2 = str(xrmmap['config/scan/pos2'].value)
        i1 = pos_addrs.index(pos1)
        i2 = pos_addrs.index(pos2)
        msg = '%s(%s) = %.4f, %s(%s) = %.4f?' % (pos_label[i1], pos_addrs[i1], xval,
                                                 pos_label[i2], pos_addrs[i2], yval)

        if (wx.ID_YES == Popup(self, 'Really move stages to\n   %s?' % msg,
                               'move stages to pixel?', style=wx.YES_NO)):
            caput(pos_addrs[i1], xval)
            caput(pos_addrs[i2], yval)

    def onSavePixel(self, name, ix, iy, x=None, y=None, title=None, xrmfile=None):
        'save pixel as area, and perhaps to scandb'
        if x is None:
            x = float(xrmfile.get_pos(0, mean=True)[ix])
        if y is None:
            y = float(xrmfile.get_pos(1, mean=True)[iy])

        if len(name) < 1:
            return
        if xrmfile is None:
            xrmfile = self.current_file

        # first, create 1-pixel mask for area, and save that
        ny, nx = xrmfile.get_shape()
        tmask = np.zeros((ny, nx)).astype(bool)
        tmask[int(iy), int(ix)] = True
        xrmfile.add_area(tmask, name=name)
        for page in self.nb.pagelist:
            if hasattr(page, 'update_xrmmap'):
                page.update_xrmmap(xrmfile=xrmfile)

        # show position on map
        self.im_displays[-1].panel.add_highlight_area(tmask, label=name)

        # make sure we can save position into database
        if self.scandb is None or self.instdb is None:
            return
        samplestage = self.instdb.get_instrument(self.inst_name)
        if samplestage is None:
            return
        allpvs = [pv.name for pv in samplestage.pv]

        pvn  = pv_fullname
        conf = xrmfile.xrmmap['config']
        pos_addrs = [pvn(h5str(tval)) for tval in conf['positioners']]
        env_addrs = [pvn(h5str(tval)) for tval in conf['environ/address']]
        env_vals  = [h5str(tval) for tval in conf['environ/value']]

        position = {}
        for pv in allpvs:
            position[pv] = None

        for addr, val in zip(env_addrs, env_vals):
            if addr in allpvs:
                position[addr] = float(val)
        position[pvn(h5str(conf['scan/pos1'].value))] = x
        position[pvn(h5str(conf['scan/pos2'].value))] = y

        notes = {'source': '%s: %s' % (xrmfile.filename, name)}
        self.instdb.save_position(self.inst_name, name, position,
                                  notes=json.dumps(notes))


    def add_tomodisplay(self, title, det=None, _lassocallback=True):

        if _lassocallback:
             lasso_cb = partial(self.lassoHandler, det=det)
        else:
             lasso_cb = None

        imframe = MapImageFrame(output_title   = title,
                                  lasso_callback = lasso_cb)

        self.tomo_displays.append(imframe)

    def display_tomo(self, tomo, title='', info='', x=None, y=None, xoff=0,
                     yoff=0, det=None, subtitles=None, xrmfile=None,
                     _lassocallback=True):

        displayed = False
        if _lassocallback:
             lasso_cb = partial(self.lassoHandler, det=det, xrmfile=xrmfile)
        else:
             lasso_cb = None

        while not displayed:
            try:
                tmd = self.tomo_displays.pop()
                tmd.display(tomo, title=title, subtitles=subtitles,
                            contrast_level=0.5)
                tmd.lasso_callback = lasso_cb
                displayed = True
            except IndexError:
                tmd = MapImageFrame(output_title=title,
                                    lasso_callback=lasso_cb)
                tmd.display(tomo, title=title, subtitles=subtitles,
                            contrast_level=0.5)
                displayed = True
            except PyDeadObjectError:
                displayed = False
        self.tomo_displays.append(tmd)
        tmd.SetStatusText(info, 1)
        tmd.Show()
        tmd.Raise()

    def add_imdisplay(self, title, det=None):
        imd = MapImageFrame(output_title=title,
                            lasso_callback=partial(self.lassoHandler, det=det),
                            cursor_labels=self.cursor_menulabels,
                            save_callback=self.onSavePixel)
        self.im_displays.append(imd)
        return imd

    def display_map(self, map, title='', info='', x=None, y=None, xoff=0, yoff=0,
                    det=None, subtitles=None, xrmfile=None, with_savepos=True):
        """display a map in an available image display"""

        if xrmfile is None:
            hotcols = False
        else:
            hotcols = xrmfile.hotcols
        if x is not None and hotcols and map.shape[1] != x.shape[0]:
            x = x[1:-1]

        dopts = dict(title=title, x=x, y=y, xoff=xoff, yoff=yoff,
                     det=det, subtitles=subtitles, contrast_level=0.5,
                     xrmfile=xrmfile, with_savepos=with_savepos)
        displayed = False
        while not displayed:
            if len(self.im_displays) == 0:
                imd = self.add_imdisplay(title=title, det=det)
                imd.display(map, **dopts)
            else:
                try:
                    imd = self.im_displays[-1]
                    imd.display(map, **dopts)
                    displayed = True
                except PyDeadObjectError:
                    self.im_displays.pop()
                except IndexError:
                    pass
        imd.SetStatusText(info, 1)
        imd.Show()
        imd.Raise()

    def display_2Dxrd(self, map, label='image 0', xrmfile=None, flip=True):
        '''
        displays 2D XRD pattern in diFFit viewer
        '''
        flptyp = 'vertical' if flip is True else False

        poni = bytes2str(self.current_file.xrmmap['xrd1d'].attrs.get('calfile',''))
        if not os.path.exists(poni):
            poni = None

        if self.xrddisplay2D is None:
            self.xrddisplay2D = XRD2DViewerFrame(_larch=self.larch,flip=flptyp,
                                                 xrd1Dviewer=self.xrddisplay1D,
                                                 ponifile=poni)
        try:
            self.xrddisplay2D.plot2Dxrd(label,map)
        except PyDeadObjectError:
            self.xrddisplay2D = XRD2DViewerFrame(_larch=self.larch,flip=flptyp,
                                                 xrd1Dviewer=self.xrddisplay1D)
            self.xrddisplay2D.plot2Dxrd(label,map)
        self.xrddisplay2D.Show()

    def display_xrd1d(self, counts, q, energy, label='dataset 0', xrmfile=None):
        '''
        displays 1D XRD pattern in diFFit viewer
        '''
        wavelength = lambda_from_E(energy, E_units='keV')

        xdat = xrd1d(label=label, energy=energy, wavelength=wavelength)
        xdat.set_xy_data(np.array([q, counts]), 'q')

        if self.xrddisplay1D is None:
            self.xrddisplay1D = XRD1DViewerFrame(_larch=self.larch)
        try:
            self.xrddisplay1D.xrd1Dviewer.add1Ddata(xdat)
            self.xrddisplay1D.Show()
        except PyDeadObjectError:
            self.xrddisplay1D = XRD1DViewerFrame(_larch=self.larch)
            self.xrddisplay1D.xrd1Dviewer.add1Ddata(xdat)
            self.xrddisplay1D.Show()

    def init_larch(self):
        self.SetStatusText('ready')
        self.datagroups = self.larch.symtable
        self.title.SetLabel('')
        fico = os.path.join(icondir, XRF_ICON_FILE)
        try:
            self.SetIcon(wx.Icon(fico, wx.BITMAP_TYPE_ICO))
        except:
            pass

        self.Raise()

        self.onFolderSelect()

        if ESCAN_CRED is not None:
            self.move_callback = self.onMoveToPixel
            try:
                self.scandb = connect_scandb(_larch=self.larch)
                self.instdb = self.larch.symtable._scan._instdb
                self.inst_name = self.scandb.get_info('samplestage_instrument',
                                                      default='SampleStage')
                print(" ScanDB: %s, Instrument=%s" % (self.scandb.engine, self.inst_name))
            except:
                etype, emsg, tb = sys.exc_info()
                print('Could not connect to ScanDB: %s' % (emsg))
                self.scandb = self.instdb = None

    def ShowFile(self, evt=None, filename=None,  process_file=True, **kws):
        if filename is None and evt is not None:
            filename = evt.GetString()

        if not self.h5convert_done or filename not in self.filemap:
            return
        if (self.check_ownership(filename) and
            self.filemap[filename].folder_has_newdata()):
            if process_file:
                self.process_file(filename, max_new_rows=25)

        self.current_file = self.filemap[filename]
        ny, nx = self.filemap[filename].get_shape()
        self.title.SetLabel('%s: (%i x %i)' % (filename, nx, ny))

        fnames = self.filelist.GetItems()
        for page in self.nb.pagelist:
            if hasattr(page, 'update_xrmmap'):
                page.update_xrmmap(xrmfile=self.current_file)
            if hasattr(page, 'set_file_choices'):
                page.set_file_choices(fnames)

    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()

        MenuItem(self, fmenu, '&Open XRM Map File\tCtrl+O',  'Read XRM Map File',  self.onReadFile)
        MenuItem(self, fmenu, '&Open XRM Map Folder\tCtrl+F', 'Read XRM Map Folder',  self.onReadFolder)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, 'Change &Working Folder',    'Choose working directory',        self.onFolderSelect)
        MenuItem(self, fmenu, 'Show Larch Buffer\tCtrl+L', 'Show Larch Programming Buffer',  self.onShowLarchBuffer)

        cmenu = fmenu.Append(-1, '&Watch HDF5 Files\tCtrl+W', 'Watch HDF5 Files', kind=wx.ITEM_CHECK)
        fmenu.Check(cmenu.Id, self.watch_files) ## False
        self.Bind(wx.EVT_MENU, self.onWatchFiles, id=cmenu.Id)

        fmenu.AppendSeparator()
        MenuItem(self, fmenu, '&Quit\tCtrl+Q',
                  'Quit program', self.onClose)

        rmenu = wx.Menu()
        MenuItem(self, rmenu, 'Define new ROI',
                 'Define new ROI',  self.defineROI)
        MenuItem(self, rmenu, 'Load ROI File for 1DXRD',
                 'Load ROI File for 1DXRD',  self.add1DXRDFile)
        rmenu.AppendSeparator()
        MenuItem(self, rmenu, 'Load XRD calibration file',
                 'Load XRD calibration file',  self.openPONI)
        MenuItem(self, rmenu, 'Add 1DXRD for HDF5 file',
                 'Calculate 1DXRD for HDF5 file',  self.add1DXRD)


        # cmenu = fmenu.Append(-1, 'Display 1DXRD for areas',
        #                    'Display 1DXRD for areas',
        #                     kind=wx.ITEM_CHECK)
        #fmenu.Check(cmenu.Id, self.showxrd) ## False
        #self.Bind(wx.EVT_MENU, self.onShow1DXRD, id=cmenu.Id)

        hmenu = wx.Menu()
        cmenu = hmenu.Append(-1, '&About', 'About GSECARS MapViewer')
        self.Bind(wx.EVT_MENU, self.onAbout, id=cmenu.Id)

        self.menubar.Append(fmenu, '&File')
        self.menubar.Append(rmenu, '&ROIs')
        self.menubar.Append(hmenu, '&Help')
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)

    def onShowLarchBuffer(self, evt=None):
        if self.larch_buffer is None:
            self.larch_buffer = LarchFrame(_larch=self.larch, is_standalone=False)

        self.larch_buffer.Show()
        self.larch_buffer.Raise()

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

    def onAbout(self, event=None):
        info = wx.AboutDialogInfo()
        info.SetName('GSECARS X-ray Microprobe Map Viewer')
        desc = 'Using X-ray Larch version: %s' % larch.version.__version__
        info.SetDescription(desc)
        info.SetVersion(VERSION)
        info.AddDeveloper('Matt Newville: newville at cars.uchicago.edu')
        dlg = wx.AboutBox(info)


    def onClose(self, evt):
        dlg = wx.MessageDialog(None, 'Really Quit?', 'Question',
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)

        ret = dlg.ShowModal()
        if ret != wx.ID_YES:
            return

        save_workdir('gsemap.dat')
        for xrmfile in self.filemap.values():
            xrmfile.close()

        ## Closes maps, 2D XRD image
        for disp in self.im_displays + self.plot_displays + self.tomo_displays:
            try:
                disp.Destroy()
            except:
                pass
        try:
            self.xrfdisplay.Destroy()
        except:
            pass

        try:
            self.xrddisplay1D.Destroy()
        except:
            pass

        try:
            self.xrddisplay2D.Destroy()
        except:
            pass

        for nam in dir(self.larch.symtable._plotter):
            obj = getattr(self.larch.symtable._plotter, nam)
            try:
                obj.Destroy()
            except:
                pass

        if self.larch_buffer is not None:
            try:
                self.larch_buffer.Show()
                self.larch_buffer.onExit(force=True)
            except:
                pass

        for nam in dir(self.larch.symtable._sys.wx):
            obj = getattr(self.larch.symtable._sys.wx, nam)
            del obj
        self.Destroy()

    def onReadFile(self, evt=None):
        if not self.h5convert_done:
            print('cannot open file while processing a map folder')
            return

        dlg = wx.FileDialog(self, message='Read XRM Map File',
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.FD_OPEN|wx.FD_MULTIPLE)
        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            paths = [p.replace('\\', '/') for p in dlg.GetPaths()]
        dlg.Destroy()

        if not read:
            return

        for path in paths:
            parent, fname = os.path.split(path)
            read = True
            if fname in self.filemap:
                read = (wx.ID_YES == Popup(self, "Re-read file '%s'?" % path,
                                           'Re-read file?', style=wx.YES_NO))
            if read:
                xrmfile = GSEXRM_MapFile(filename=str(path), scandb=self.scandb)
                self.add_xrmfile(xrmfile)


    def onReadFolder(self, evt=None):
        if not self.h5convert_done:
            print( 'cannot open file while processing a map folder')
            return


        dlg = wx.DirDialog(self, message='Read XRM Map Folder',
                           defaultPath=os.getcwd(),
                           style=wx.FD_OPEN)
        folder = None
        if dlg.ShowModal() != wx.ID_OK:
            return

        folder = os.path.abspath(dlg.GetPath())
        dlg.Destroy()


        myDlg = OpenMapFolder(folder=folder)

        path, read = None, False
        if myDlg.ShowModal() == wx.ID_OK:
            read        = True

            args = {'folder':   folder,
                    'HAS_xrf':          myDlg.ChkBx[0].GetValue(),
                    'HAS_xrd2D':        myDlg.ChkBx[1].GetValue(),
                    'HAS_xrd1D':        myDlg.ChkBx[2].GetValue(),
                    'facility':         myDlg.info[0].GetValue(),
                    'beamline':         myDlg.info[1].GetValue(),
                    'run':              myDlg.info[2].GetValue(),
                    'proposal':         myDlg.info[3].GetValue(),
                    'user':             myDlg.info[4].GetValue(),
                    'compression':      myDlg.H5cmprInfo[0].GetStringSelection(),
                    'compression_opts': myDlg.H5cmprInfo[1].GetSelection()}

            if len(myDlg.XRDInfo[1].GetValue()) > 0:
                flipchoice = False if myDlg.XRDInfo[0].GetSelection() == 1 else True
                args.update({'xrdcal'     : myDlg.XRDInfo[1].GetValue(),
                             'azwdgs'     : myDlg.XRDInfo[6].GetValue(),
                             'qstps'      : myDlg.XRDInfo[4].GetValue(),
                              'flip'      : flipchoice,
                              'bkgdscale' : float(myDlg.XRDInfo[11].GetValue())})
            if len(myDlg.XRDInfo[8].GetValue()) > 0:
                bkgd = 2 if myDlg.XRDInfo[7].GetSelection() == 0 else 1
                args.update({'xrd%idbkgd' % bkgd:myDlg.XRDInfo[8].GetValue()})
            if len(myDlg.XRDInfo[13].GetValue()) > 0:
                args.update({'xrd2dmask':myDlg.XRDInfo[13].GetValue()})

        myDlg.Destroy()

        if read:
            args['scandb'] = self.scandb
            xrmfile = GSEXRM_MapFile(**args)
            self.add_xrmfile(xrmfile)

    def add_xrmfile(self, xrmfile):
        parent, fname = os.path.split(xrmfile.filename)
        # print("Add XRM File ", fname)
        # look for group with this name or for next available group
        for i in range(1000):
            gname = 'map%3.3i' % (i+1)
            xgroup = getattr(self.datagroups, gname, None)
            if xgroup is None:
                break
            gpar, gfname  = os.path.split(xgroup.filename)
            if gfname == fname:
                break

        setattr(self.datagroups, gname, xrmfile)

        if fname not in self.filemap:
            self.filemap[fname] = xrmfile
        if fname not in self.filelist.GetItems():
            self.filelist.Append(fname)
            self.filelist.SetStringSelection(fname)

        if self.check_ownership(fname):
            self.process_file(fname, max_new_rows=50)

        self.ShowFile(filename=fname)
        if parent is not None and len(parent) > 0:
            try:
                os.chdir(nativepath(parent))
                save_workdir(nativepath(parent))
            except:
                pass

    def openPONI(self, evt=None):
        """
        Read specified poni file.
        mkak 2016.07.21
        """

        if len(self.filemap) > 0:
            myDlg = OpenPoniFile()
            read = False
            if myDlg.ShowModal() == wx.ID_OK:
                read = True
                path = myDlg.XRDInfo[1].GetValue()
                flip = False if myDlg.XRDInfo[0].GetSelection() == 1 else True
            myDlg.Destroy()

            if read:
                self.current_file.add_XRDfiles(xrdcalfile=path,flip=flip)
                for page in self.nb.pagelist:
                    if hasattr(page, 'update_xrmmap'):
                        page.update_xrmmap(xrmfile=self.current_file)

    def defineROI(self, event=None):
        if not self.h5convert_done:
            print( 'cannot open file while processing a map folder')
            return

        if len(self.filemap) > 0:
            myDlg = ROIPopUp(self)

            path, read = None, False
            if myDlg.ShowModal() == wx.ID_OK:
                read        = True
            myDlg.Destroy()

            if read:
                for page in self.nb.pagelist:
                    if hasattr(page, 'update_xrmmap'):
                        page.update_xrmmap(xrmfile=self.current_file)

    def add1DXRDFile(self, event=None):

        if len(self.filemap) > 0:
            read = False
            wildcards = '1D-XRD ROI file (*.dat)|*.dat|All files (*.*)|*.*'
            dlg = wx.FileDialog(self, message='Select 1D-XRD ROI file',
                               defaultDir=os.getcwd(),
                               wildcard=wildcards,
                               style=wx.FD_OPEN)

            if dlg.ShowModal() == wx.ID_OK:
                read = True
                path = dlg.GetPath().replace('\\', '/')
            dlg.Destroy()

            if read and os.path.exists(path):
                time.sleep(1) ## will hopefully allow time for dialog window to close
                self.current_file.read_xrd1D_ROIFile(path)

    def add1DXRD(self, event=None):

        if len(self.filemap) > 0:
            xrd1Dgrp = ensure_subgroup('xrd1d',self.current_file.xrmmap)
            poni_path = bytes2str(xrd1Dgrp.attrs.get('calfile',''))

            if not os.path.exists(poni_path):
                self.openPONI()
                poni_path = bytes2str(xrd1Dgrp.attrs.get('calfile',''))

            if os.path.exists(poni_path):
                self.current_file.add_xrd1d()

    def onShow1DXRD(self, event=None):
        self.showxrd = event.IsChecked()
        if self.showxrd:
            msg = 'Show 1DXRD data for area'
        else:
            msg = 'Not displaying 1DXRD for area'
        self.message(msg)
        ##print(msg)

#     def onCorrectDeadtime(self, event=None):
#         self.dtcor = event.IsChecked()
#         if self.dtcor:
#             msg = 'Using deadtime corrected data...'
#         else:
#             msg = 'Using raw data...'
#         self.message(msg)
#         ##print(msg)
#
#     def onHotColumns(self, event=None):
#         self.hotcols = event.IsChecked()
#         if self.hotcols:
#             msg = 'Ignoring first/last data columns.'
#         else:
#             msg = 'Using all data columns'
#         self.message(msg)
#         ##print(msg)

    def onWatchFiles(self, event=None):
        self.watch_files = event.IsChecked()
        if not self.watch_files:
            self.file_timer.Stop()
            msg = 'Watching Files/Folders for Changes: Off'
        else:
            self.file_timer.Start(10000)
            msg = 'Watching Files/Folders for Changes: On'
        self.message(msg)

    def onFileWatchTimer(self, event=None):
        if self.current_file is not None and len(self.files_in_progress) == 0:
            if self.current_file.folder_has_newdata():
                self.process_file(fname, max_new_rows=1200300)


    def process_file(self, filename, max_new_rows=None):
        """Request processing of map file.
        This can take awhile, so is done in a separate thread,
        with updates displayed in message bar
        """
        xrmfile = self.filemap[filename]
        if xrmfile.status == GSEXRM_FileStatus.created:
            xrmfile.initialize_xrmmap(callback=self.updateTimer)

        if xrmfile.dimension is None and isGSEXRM_MapFolder(self.folder):
            xrmfile.read_master()

        if (xrmfile.folder_has_newdata() and self.h5convert_done
            and filename not in self.files_in_progress):

            self.files_in_progress.append(filename)
            self.h5convert_fname = filename
            self.h5convert_done = False
            self.htimer.Start(1500)
            maxrow = None
            if max_new_rows is not None:
                maxrow = max_new_rows + xrmfile.last_row + 1

            ## this calls process function of xrm_mapfile class
            self.h5convert_thread = Thread(target=xrmfile.process,
                                           kwargs={'callback':self.updateTimer,
                                                   'maxrow': maxrow})
            self.h5convert_thread.start()

    def updateTimer(self, row=None, maxrow=None, filename=None, status=None):
        if row      is not None: self.h5convert_irow  = row
        if maxrow   is not None: self.h5convert_nrow  = maxrow
        if filename is not None: self.h5convert_fname = filename
        self.h5convert_done = True if status is 'complete' else False

    def onTimer(self, event=None):
        fname, irow, nrow = self.h5convert_fname, self.h5convert_irow, self.h5convert_nrow
        self.message('MapViewer processing %s:  row %i of %i' % (fname, irow, nrow))
        if self.h5convert_done:
            self.htimer.Stop()
            self.h5convert_thread.join()
            self.files_in_progress = []
            self.message('MapViewer processing %s: complete!' % fname)

            _path, _fname = os.path.split(fname)
            self.ShowFile(filename=_fname)
            if _fname in self.filemap:
                for page in self.nb.pagelist:
                    if hasattr(page, 'update_xrmmap'):
                        page.update_xrmmap(xrmfile=self.filemap[_fname])


    def message(self, msg, win=0):
        self.statusbar.SetStatusText(msg, win)

    def check_ownership(self, fname):
        """
        check whether we're currently owner of the file.
        this is important!! HDF5 files can be corrupted.
        """
        if not self.filemap[fname].check_hostid():
            if (wx.ID_YES == Popup(self, NOT_OWNER_MSG % fname,
                                   'Not Owner of HDF5 File',
                                   style=wx.YES_NO)):
                self.filemap[fname].take_ownership()
        return self.filemap[fname].check_hostid()

class OpenPoniFile(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):

        """Constructor"""
        dialog = wx.Dialog.__init__(self, None, title='XRD Calibration File', size=(350, 280))

        panel = wx.Panel(self)

        ################################################################################
        cal_chc = ['Dioptas calibration file:','pyFAI calibration file:']
        cal_spn = wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP
        self.PoniInfo = [ Choice(panel,      choices=cal_chc ),
                          wx.TextCtrl(panel, size=(320, 25)),
                          Button(panel,      label='Browse...')]

        self.PoniInfo[2].Bind(wx.EVT_BUTTON, self.onBROWSEponi)

        ponisizer = wx.BoxSizer(wx.VERTICAL)
        ponisizer.Add(self.PoniInfo[0], flag=wx.TOP,            border=15)
        ponisizer.Add(self.PoniInfo[1], flag=wx.TOP,            border=5)
        ponisizer.Add(self.PoniInfo[2], flag=wx.TOP|wx.BOTTOM,  border=5)

        ################################################################################
        hlpBtn       = wx.Button(panel,   wx.ID_HELP   )
        okBtn        = wx.Button(panel,   wx.ID_OK     )
        canBtn       = wx.Button(panel,   wx.ID_CANCEL )

        minisizer = wx.BoxSizer(wx.HORIZONTAL)
        minisizer.Add(hlpBtn,  flag=wx.RIGHT, border=5)
        minisizer.Add(canBtn,  flag=wx.RIGHT, border=5)
        minisizer.Add(okBtn,   flag=wx.RIGHT, border=5)
        ################################################################################
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((-1, 10))
        sizer.Add(ponisizer, flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add((-1, 15))
        sizer.Add(minisizer, flag=wx.ALIGN_RIGHT, border=5)

        panel.SetSizer(sizer)
        ################################################################################

        ## Set defaults
        self.PoniInfo[0].SetSelection(0)

        self.FindWindowById(wx.ID_OK).Disable()

    def checkOK(self,event=None):

        if os.path.exists(self.PoniInfo[1].GetValue()):
            self.FindWindowById(wx.ID_OK).Enable()
        else:
            self.FindWindowById(wx.ID_OK).Disable()

    def onBROWSEponi(self,event=None):
        wildcards = 'XRD calibration file (*.poni)|*.poni|All files (*.*)|*.*'
        if os.path.exists(self.PoniInfo[1].GetValue()):
           dfltDIR = self.PoniInfo[1].GetValue()
        else:
           dfltDIR = os.getcwd()

        dlg = wx.FileDialog(self, message='Select XRD calibration file',
                           defaultDir=dfltDIR,
                           wildcard=wildcards, style=wx.FD_OPEN)
        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()

        if read:
            self.PoniInfo[1].Clear()
            self.PoniInfo[1].SetValue(str(path))
            self.checkOK()

##################
class ROIPopUp(wx.Dialog):
    """"""
    #----------------------------------------------------------------------
    def __init__(self, owner, **kws):

        """Constructor"""
        dialog = wx.Dialog.__init__(self, None, title='ROI Tools', size=(450, 500))

        panel = wx.Panel(self)

        ################################################################################

        self.owner = owner

        self.cfile   = self.owner.current_file
        self.xrmmap = self.cfile.xrmmap

        self.gp = GridPanel(panel, nrows=8, ncols=4,
                            itemstyle=LEFT, gap=3, **kws)

        self.roi_name =  wx.TextCtrl(self, -1, 'ROI_001',  size=(120, -1))
        self.roi_chc  = [Choice(self, size=(150, -1)),
                         Choice(self, size=(150, -1))]
        fopts = dict(minval=-1, precision=3, size=(100, -1))
        self.roi_lims = [FloatCtrl(self, value=0,  **fopts),
                         FloatCtrl(self, value=-1, **fopts),
                         FloatCtrl(self, value=0,  **fopts),
                         FloatCtrl(self, value=-1, **fopts)]

        self.gp.Add(SimpleText(self, ' Add new ROI: '), dcol=2, style=LEFT, newrow=True)

        self.gp.Add(SimpleText(self, ' Name:'),  newrow=True)
        self.gp.Add(self.roi_name, dcol=2)
        self.gp.Add(SimpleText(self, ' Type:'), newrow=True)
        self.gp.Add(self.roi_chc[0], dcol=2)

        self.gp.Add(SimpleText(self, ' Limits:'), newrow=True)
        self.gp.AddMany((self.roi_lims[0],self.roi_lims[1],self.roi_chc[1]),
                        dcol=1, style=LEFT)
        self.gp.AddMany((SimpleText(self, ' '),self.roi_lims[2],self.roi_lims[3]),
                        dcol=1, style=LEFT, newrow=True)
        self.gp.AddMany((SimpleText(self, ' '),
                         Button(self, 'Add ROI', size=(100, -1), action=self.onCreateROI)),
                        dcol=1, style=LEFT, newrow=True)

        ###############################################################################

        self.rm_roi_ch = [Choice(self, size=(120, -1)),
                          Choice(self, size=(120, -1))]
        fopts = dict(minval=-1, precision=3, size=(100, -1))
        self.rm_roi_lims = SimpleText(self, '')

        self.gp.Add(SimpleText(self, 'Delete ROI: '), dcol=2, newrow=True)

        self.gp.AddMany((SimpleText(self, 'Detector:'),self.rm_roi_ch[0]),  newrow=True)
        self.gp.AddMany((SimpleText(self, 'ROI:'),self.rm_roi_ch[1]), newrow=True)
        self.gp.Add(SimpleText(self, 'Limits:'), newrow=True)
        self.gp.Add(self.rm_roi_lims, dcol=3)
        self.gp.AddMany((SimpleText(self, ''),Button(self, 'Remove ROI', size=(100, -1), action=self.onRemoveROI)), newrow=True)
        self.gp.Add(SimpleText(self, ''),newrow=True)

        self.gp.AddMany((SimpleText(self, ''),SimpleText(self, ''),
                         wx.Button(self, wx.ID_OK, label='Done')), newrow=True)

        self.roi_chc[0].Bind(wx.EVT_CHOICE, self.roiUNITS)
        self.roi_lims[2].Disable()
        self.roi_lims[3].Disable()

        self.rm_roi_ch[1].Bind(wx.EVT_CHOICE, self.roiSELECT)

        self.gp.pack()

        self.cfile.reset_flags()
        self.roiTYPE()

    def roiTYPE(self,event=None):
        roitype = []
        delroi = []
        if self.cfile.has_xrf:
            roitype += ['XRF']
        if self.cfile.has_xrd1d:
            roitype += ['1DXRD']
            delroi  = ['xrd1d']
        if self.cfile.has_xrd2d:
            roitype += ['2DXRD']
        if len(roitype) < 1:
            roitype = ['']
        self.roi_chc[0].SetChoices(roitype)
        self.roiUNITS()
        if len(delroi) > 0:
            self.rm_roi_ch[0].SetChoices(delroi)
            self.setROI()

    def onRemoveROI(self,event=None):

        detname = self.rm_roi_ch[0].GetStringSelection()
        roiname = self.rm_roi_ch[1].GetStringSelection()

        if detname == 'xrd1d':
            self.cfile.del_xrd1droi(roiname)
            self.setROI()

    def setROI(self):

        detname = self.rm_roi_ch[0].GetStringSelection()
        try:
            detgrp = self.cfile.xrmmap['roimap'][detname]
        except:
            return
        limits,names = [],detgrp.keys()
        for name in names:
            limits += [list(detgrp[name]['limits'][:])]

        self.rm_roi_ch[1].SetChoices([x for (y,x) in sorted(zip(limits,names))])
        self.roiSELECT()


    def roiSELECT(self,event=None):

        detname = self.rm_roi_ch[0].GetStringSelection()
        roiname = self.rm_roi_ch[1].GetStringSelection()

        roi = self.cfile.xrmmap['roimap'][detname][roiname]
        limits = roi['limits'][:]
        units = bytes2str(roi['limits'].attrs.get('units',''))

        if units == '1/A':
            roistr = '[%0.2f to %0.2f %s]' % (limits[0],limits[1],units)
        else:
            roistr = '[%0.1f to %0.1f %s]' % (limits[0],limits[1],units)

        self.rm_roi_lims.SetLabel(roistr)


    def roiUNITS(self,event=None):

        choice = self.roi_chc[0].GetStringSelection()
        roiunit = ['']
        if choice == 'XRF':
            roiunit = ['eV','keV','channels']
            self.roi_lims[2].Disable()
            self.roi_lims[3].Disable()
        elif choice == '1DXRD':
            roiunit = [u'\u212B\u207B\u00B9 (q)',u'\u00B0 (2\u03B8)',u'\u212B (d)']
            self.roi_lims[2].Disable()
            self.roi_lims[3].Disable()
        elif choice == '2DXRD':
            roiunit = ['pixels']
            self.roi_lims[2].Enable()
            self.roi_lims[3].Enable()
        self.roi_chc[1].SetChoices(roiunit)

    def onCreateROI(self,event=None):

        xtyp  = self.roi_chc[0].GetStringSelection()
        xunt  = self.roi_chc[1].GetStringSelection()
        xname = self.roi_name.GetValue()
        xrange = [float(lims.GetValue()) for lims in self.roi_lims]
        if xtyp != '2DXRD': xrange = xrange[:2]

        self.owner.message('Building ROI data for: %s' % xname)
        if xtyp == 'XRF':
            self.cfile.add_xrfroi(xrange,xname,unit=xunt)
        elif xtyp == '1DXRD':
            xrd = ['q','2th','d']
            unt = xrd[self.roi_chc[1].GetSelection()]
            self.cfile.add_xrd1droi(xrange, xname, unit=unt)
        elif xtyp == '2DXRD':
            self.cfile.add_xrd2droi(xrange,xname,unit=xunt)
        self.owner.message('Added ROI:  %s' % xname)
##################


class OpenMapFolder(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self, folder):
        """Constructor"""
        self.folder = folder
        pref, f = os.path.split(folder)
        title = "Read XRM Map Folder: %s" % f
        dialog = wx.Dialog.__init__(self, None,
                                    title=title, size=(475, 750))


        panel = wx.Panel(self)

        ChkTtl        = SimpleText(panel,  label='Build map including data:' )
        self.ChkBx = [ Check(panel, label='XRF'   ),
                       Check(panel, label='2DXRD' ),
                       Check(panel, label='1DXRD (requires calibration file)' )]

        for chkbx in self.ChkBx:
            chkbx.Bind(wx.EVT_CHECKBOX, self.checkOK)

        cbsizer = wx.BoxSizer(wx.HORIZONTAL)
        cbsizer.Add(self.ChkBx[0])
        cbsizer.Add(self.ChkBx[1])
        cbsizer.Add(self.ChkBx[2])

        ckbxsizer = wx.BoxSizer(wx.VERTICAL)
        ckbxsizer.Add(ChkTtl, flag=wx.BOTTOM|wx.LEFT)
        ckbxsizer.Add(cbsizer)
        ################################################################################
        infoTtl =  [ SimpleText(panel,  label='Facility'),
                     SimpleText(panel,  label='Beamline'),
                     SimpleText(panel,  label='Run cycle'),
                     SimpleText(panel,  label='Proposal'),
                     SimpleText(panel,  label='User group')]
        self.info = [ wx.TextCtrl(panel, size=(100, 25) ),
                      wx.TextCtrl(panel, size=(100, 25) ),
                      wx.TextCtrl(panel, size=(100, 25) ),
                      wx.TextCtrl(panel, size=(100, 25) ),
                      wx.TextCtrl(panel, size=(320, 25) )]

        infosizer0 = wx.BoxSizer(wx.HORIZONTAL)
        infosizer0.Add(infoTtl[0],   flag=wx.RIGHT, border=5)
        infosizer0.Add(self.info[0], flag=wx.RIGHT, border=15)
        infosizer0.Add(infoTtl[1],   flag=wx.RIGHT, border=5)
        infosizer0.Add(self.info[1], flag=wx.RIGHT, border=15)

        infosizer1 = wx.BoxSizer(wx.HORIZONTAL)
        infosizer1.Add(infoTtl[2],   flag=wx.RIGHT, border=5)
        infosizer1.Add(self.info[2], flag=wx.RIGHT, border=15)
        infosizer1.Add(infoTtl[3],   flag=wx.RIGHT, border=5)
        infosizer1.Add(self.info[3], flag=wx.RIGHT, border=15)

        infosizer2 = wx.BoxSizer(wx.HORIZONTAL)
        infosizer2.Add(infoTtl[4],   flag=wx.RIGHT, border=5)
        infosizer2.Add(self.info[4], flag=wx.RIGHT, border=15)

        infosizer = wx.BoxSizer(wx.VERTICAL)
        infosizer.Add(infosizer0, flag=wx.TOP,           border=5)
        infosizer.Add(infosizer1, flag=wx.TOP|wx.BOTTOM, border=5)
        infosizer.Add(infosizer2, flag=wx.BOTTOM,        border=15)
        ################################################################################
        cal_chc  = ['Dioptas calibration file:','pyFAI calibration file:']
        bkgd_chc = ['2DXRD background (optional):','1DXRD background (optional):']
        cal_spn = wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP
        self.XRDInfo = [  Choice(panel,      choices=cal_chc ),
                          wx.TextCtrl(panel, size=(320, 25)),
                          Button(panel,      label='Browse...'),
                          SimpleText(panel,  label='Steps:'),
                          wx.TextCtrl(panel, size=(80,  25)),
                          SimpleText(panel,  label='Wedges:'),
                          wx.SpinCtrl(panel, style=cal_spn, size=(100,  -1)),
                          Choice(panel,      choices=bkgd_chc ),
                          wx.TextCtrl(panel, size=(320, 25)),
                          Button(panel,      label='Browse...'),
                          SimpleText(panel,  label='Background scale:'),
                          wx.TextCtrl(panel, size=(80,  25)),
                          SimpleText(panel,  label='2DXRD mask file (optional):'),
                          wx.TextCtrl(panel, size=(320, 25)),
                          Button(panel,      label='Browse...'),]

        for i in [1,8,13]:
            self.XRDInfo[i+1].Bind(wx.EVT_BUTTON,  partial(self.onBROWSEfile,i=i))

        xrdsizer1 = wx.BoxSizer(wx.HORIZONTAL)

        xrdsizer1.Add(self.XRDInfo[3], flag=wx.RIGHT, border=5)
        xrdsizer1.Add(self.XRDInfo[4], flag=wx.RIGHT, border=5)
        xrdsizer1.Add(self.XRDInfo[5], flag=wx.RIGHT, border=5)
        xrdsizer1.Add(self.XRDInfo[6], flag=wx.RIGHT, border=5)

        xrdsizer2 = wx.BoxSizer(wx.HORIZONTAL)

        xrdsizer2.Add(self.XRDInfo[9], flag=wx.RIGHT, border=30)
        xrdsizer2.Add(self.XRDInfo[10], flag=wx.RIGHT, border=5)
        xrdsizer2.Add(self.XRDInfo[11], flag=wx.RIGHT, border=5)

        xrdsizer = wx.BoxSizer(wx.VERTICAL)
        xrdsizer.Add(self.XRDInfo[0],  flag=wx.TOP,            border=5)
        xrdsizer.Add(self.XRDInfo[1],  flag=wx.TOP,            border=5)
        xrdsizer.Add(self.XRDInfo[2],  flag=wx.TOP|wx.BOTTOM,  border=5)
        xrdsizer.Add(xrdsizer1,       flag=wx.BOTTOM,         border=5)
        xrdsizer.Add(self.XRDInfo[7],  flag=wx.TOP,            border=8)
        xrdsizer.Add(self.XRDInfo[8],  flag=wx.TOP,            border=5)
#         xrdsizer.Add(self.XRDInfo[9],  flag=wx.TOP|wx.BOTTOM,  border=5)
        xrdsizer.Add(xrdsizer2,       flag=wx.TOP|wx.BOTTOM,  border=5)
        xrdsizer.Add(self.XRDInfo[12], flag=wx.TOP,            border=8)
        xrdsizer.Add(self.XRDInfo[13], flag=wx.TOP,            border=5)
        xrdsizer.Add(self.XRDInfo[14], flag=wx.TOP|wx.BOTTOM,  border=5)


        ################################################################################
        h5cmpr_chc = ['gzip','lzf']
        h5cmpr_opt = ['%i' % i for i in np.arange(10)]

        self.H5cmprInfo = [Choice(panel,      choices=h5cmpr_chc),
                           Choice(panel,      choices=h5cmpr_opt)]
        h5txt = SimpleText(panel, label='H5 File Comppression:')

        self.H5cmprInfo[0].SetSelection(0)
        self.H5cmprInfo[1].SetSelection(2)

        self.H5cmprInfo[0].Bind(wx.EVT_CHOICE, self.onH5cmpr)

        h5cmprsizer = wx.BoxSizer(wx.HORIZONTAL)
        h5cmprsizer.Add(h5txt,              flag=wx.RIGHT, border=5)
        h5cmprsizer.Add(self.H5cmprInfo[0], flag=wx.RIGHT, border=5)
        h5cmprsizer.Add(self.H5cmprInfo[1], flag=wx.RIGHT, border=5)
        ################################################################################
        self.ok_btn  = wx.Button(panel, wx.ID_OK)
        self.cancel_btn  = wx.Button(panel, wx.ID_CANCEL)

        minisizer = wx.BoxSizer(wx.HORIZONTAL)
        minisizer.Add(self.cancel_btn,  flag=wx.RIGHT, border=5)
        minisizer.Add(self.ok_btn,   flag=wx.RIGHT, border=5)
        ################################################################################
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(ckbxsizer,   flag=wx.TOP|wx.LEFT, border=5)

        sizer.Add(HLine(panel, size=(320, 2)),flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add(infosizer,   flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add(HLine(panel, size=(320, 2)),flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add(xrdsizer,   flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add(HLine(panel, size=(320, 2)),flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add(h5cmprsizer, flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add(minisizer,   flag=wx.ALIGN_RIGHT, border=5)


        pack(panel, sizer)
        w, h = panel.GetBestSize()
        w = 25*(2 + int(w*0.04))
        h = 25*(2 + int(h*0.04))
        panel.SetSize((w, h))

        # HX
        ################################################################################

        ## Set defaults
        self.ChkBx[0].SetValue(True)
        self.ChkBx[1].SetValue(False)
        self.ChkBx[2].SetValue(False)

        self.XRDInfo[0].SetSelection(0)
        self.XRDInfo[7].SetSelection(0)

        self.XRDInfo[4].SetValue('5001')
        self.XRDInfo[6].SetValue(1)
        self.XRDInfo[6].SetRange(0,36)

        self.XRDInfo[11].SetValue('1.0')

        for poniinfo in self.XRDInfo:
            poniinfo.Disable()

        self.info[0].SetValue(FACILITY)
        self.info[1].SetValue(BEAMLINE)
        for line in open(os.path.join(self.folder, 'Scan.ini'), 'r'):
            if line.split()[0] == 'basedir':
                npath = line.split()[-1].replace('\\', '/').split('/')
                cycle, usr = npath[-2], npath[-1]
                self.info[2].SetValue(cycle)
                self.info[4].SetValue(usr)
        self.checkOK()

    def checkOK(self, evt=None):

        if self.ChkBx[2].GetValue():
            for poniinfo in self.XRDInfo:
                poniinfo.Enable()
        elif self.ChkBx[1].GetValue():
            for poniinfo in self.XRDInfo[8:]:
                poniinfo.Enable()
            for poniinfo in self.XRDInfo[:8]:
                poniinfo.Disable()
            self.XRDInfo[7].SetSelection(0)
        else:
            for poniinfo in self.XRDInfo:
                poniinfo.Disable()

    def onH5cmpr(self,event=None):

        if self.H5cmprInfo[0].GetSelection() == 0:
            self.H5cmprInfo[1].Enable()
            self.H5cmprInfo[1].SetChoices(['%i' % i for i in np.arange(10)])
            self.H5cmprInfo[1].SetSelection(2)
        else:
            self.H5cmprInfo[1].Disable()
            self.H5cmprInfo[1].SetChoices([''])

    def onBROWSEfile(self,event=None,i=1):

        if i == 8:
            wldcd = '2D XRD background file (*.tiff)|*.tif;*.tiff;*.edf|All files (*.*)|*.*'
        if i == 13:
            wldcd = '1D XRD background file (*.xy)|*.xy|All files (*.*)|*.*'
        else: ## elif i == 1:
            wldcd = 'XRD calibration file (*.poni)|*.poni|All files (*.*)|*.*'

        if os.path.exists(self.XRDInfo[i].GetValue()):
           dfltDIR = self.XRDInfo[i].GetValue()
        else:
           dfltDIR = os.getcwd()

        dlg = wx.FileDialog(self, message='Select %s' % wldcd.split(' (')[0],
                           defaultDir=dfltDIR,
                           wildcard=wldcd, style=wx.FD_OPEN)
        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()

        if read:
            self.XRDInfo[i].Clear()
            self.XRDInfo[i].SetValue(str(path))

class MapViewer(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, use_scandb=False, with_inspect=False, **kws):
        self.use_scandb = use_scandb
        self.with_inspect = with_inspect
        wx.App.__init__(self, **kws)

    def createApp(self):
        frame = MapViewerFrame(use_scandb=self.use_scandb)
        frame.Show()
        self.SetTopWindow(frame)

    def OnInit(self):
        self.Init()
        self.createApp()
        if self.with_inspect:
            self.ShowInspectionTool()
        return True

def mapviewer(**kws):
    s = MapViewer(**kws)
    s.Show()
    s.Raise()
