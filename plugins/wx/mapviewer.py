#!/usr/bin/env python
"""
GUI for displaying maps from HDF5 files

Needed Visualizations:

   2x2 grid:
     +-------------+--------------+
     | map1        |  2-color map |
     +-------------+--------------+
     | correlation |  map2        |
     +-------------+--------------+

   All subplots "live" so that selecting regions in
   any (via box or lasso) highlights other plots
         box in map:  show XRF spectra, highlight correlations
         lasso in correlations:  show XRF spectra, enhance map points
"""

VERSION = '9 (22-July-2015)'

import os
import sys
import time
import json
import socket
import datetime
from functools import partial
from threading import Thread
from distutils.version import StrictVersion

import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection
try:
    from wx._core import PyDeadObjectError
except:
    PyDeadObjectError = Exception

# HAS_tomopy = False
# try:
#     import tomopy
#     HAS_tomopy = True
# except ImportError:
#     pass
#
# HAS_scikit = False
# try:
#     from skimage.transform import iradon
#     #from skimage.transform import radon, iradon_sart
#     HAS_scikit = True
# except:
#     pass

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

from wxutils import (SimpleText, EditableListBox, FloatCtrl, Font,
                     pack, Popup, Button, MenuItem, Choice, Check,
                     GridPanel, FileSave, HLine)

import larch
from larch.larchlib import read_workdir, save_workdir
from larch.wxlib import LarchPanel, LarchFrame
from larch.utils.strutils import bytes2str

from larch_plugins.wx.xrfdisplay import XRFDisplayFrame
from larch_plugins.wx.mapimageframe import MapImageFrame, CorrelatedMapFrame
from larch_plugins.diFFit import diFFit1DFrame,diFFit2DFrame
from larch_plugins.xrd import lambda_from_E,xrd1d,save1D
from larch_plugins.epics import pv_fullname
from larch_plugins.io import nativepath
from larch_plugins.xrmmap import GSEXRM_MapFile, GSEXRM_FileStatus, h5str, ensure_subgroup
from larch_plugins.tomo import return_methods


CEN = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
RIGHT = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
ALL_CEN =  wx.ALL|CEN
ALL_LEFT =  wx.ALL|LEFT
ALL_RIGHT =  wx.ALL|RIGHT

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

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
DBCONN = None
BEAMLINE = '13-ID-E'
FACILITY = 'APS'


def isGSECARS_Domain():
    return 'cars.aps.anl.gov' in socket.getfqdn().lower()

def suppress_hotcols(hotcols_wid, xrmfile):
    """returns whether to suppress hot columns"""
    scanversion = getattr(xrmfile, 'scan_version', 1.00)
    return hotcols_wid.IsChecked() and scanversion < 1.36


class MapMathPanel(scrolled.ScrolledPanel):
    """Panel of Controls for doing math on arrays from Map data"""
    label  = 'Map Math'
    def __init__(self, parent, owner, **kws):
        self.map = None
        self.cfile = None

        scrolled.ScrolledPanel.__init__(self, parent, -1,
                                        style=wx.GROW|wx.TAB_TRAVERSAL, **kws)
        self.owner = owner
        sizer = wx.GridBagSizer(3, 3)
        bpanel = wx.Panel(self)
        show_new = Button(bpanel, 'Show New Map',     size=(120, -1),
                          action=partial(self.onShowMap, new=True))
        show_old = Button(bpanel, 'Replace Last Map', size=(120, -1),
                                   action=partial(self.onShowMap, new=False))
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.Add(show_new, 0, 3)
        bsizer.Add(show_old, 0, 3)
        pack(bpanel, bsizer)

        save_arr = Button(self, 'Save Array', size=(120, -1),
                          action=self.onSaveArray)

        self.expr_in = wx.TextCtrl(self, -1,   '', size=(180, -1))
        self.name_in = wx.TextCtrl(self, -1,   '', size=(180, -1))

        ir = 0
        txt = """Enter Math Expressions for Map: a+b, (a-b)/c, log10(a+0.1),  etc"""
        sizer.Add(SimpleText(self, txt),    (ir, 0), (1, 6), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Expression:'),    (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.expr_in,   (ir, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(bpanel,  (ir, 2), (1, 3), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Array Name:'),    (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.name_in,   (ir, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(save_arr,  (ir, 2), (1, 1), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Array'),       (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'File'),        (ir, 1), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Detector'),    (ir, 2), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'ROI'),         (ir, 3), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'DT Correct?'), (ir, 4), (1, 1), ALL_CEN, 2)

        self.varfile  = {}
        self.varroi   = {}
        self.varshape = {}
        self.varrange = {}
        self.vardet   = {}
        self.varcor   = {}
        for varname in ('a', 'b', 'c', 'd', 'e', 'f'):
            self.varfile[varname]  = vfile  = Choice(self, choices=[], size=(180, -1),
                                                          action=partial(self.onFILE, varname=varname))
            self.varroi[varname]   = vroi   = Choice(self, choices=[], size=(100, -1),
                                                          action=partial(self.onROI, varname=varname))
            self.vardet[varname]   = vdet   = Choice(self, choices=[], size=(80, -1),
                                                          action=partial(self.onDET, varname=varname))
            self.varcor[varname]   = vcor   = wx.CheckBox(self, -1, ' ')
            self.varshape[varname] = vshape = SimpleText(self, 'Array Shape = (, )',
                                                          size=(200, -1))
            self.varrange[varname] = vrange = SimpleText(self, 'Range = [   :    ]',
                                                          size=(200, -1))
            vcor.SetValue(1)
            vdet.SetSelection(0)

            ir += 1
            sizer.Add(SimpleText(self, '%s = ' % varname),    (ir, 0), (1, 1), ALL_CEN, 2)
            sizer.Add(vfile,                        (ir, 1), (1, 1), ALL_CEN, 2)
            sizer.Add(vdet,                         (ir, 2), (1, 1), ALL_CEN, 2)
            sizer.Add(vroi,                         (ir, 3), (1, 1), ALL_CEN, 2)
            sizer.Add(vcor,                         (ir, 4), (1, 1), ALL_CEN, 2)
            ir +=1
            sizer.Add(vshape,                       (ir, 1), (1, 1), ALL_LEFT, 2)
            sizer.Add(vrange,                       (ir, 2), (1, 3), ALL_LEFT, 2)

        ir += 1
        sizer.Add(HLine(self, size=(350, 4)), (ir, 0), (1, 5), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Work Arrays: '), (ir, 0), (1, 1), ALL_LEFT, 2)

        self.workarray_choice = Choice(self, choices=[], size=(200, -1),
                                       action=self.onSelectArray)
        btn_delete  = Button(self, 'Delete Array',  size=(90, -1),
                              action=self.onDeleteArray)
        self.info1   = wx.StaticText(self, -1, '',  size=(250, -1))
        self.info2   = wx.StaticText(self, -1, '',  size=(250, -1))


        sizer.Add(self.workarray_choice, (ir, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(btn_delete, (ir, 2), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.info1, (ir+1, 0), (1, 3), ALL_LEFT, 2)
        sizer.Add(self.info2, (ir+2, 0), (3, 3), ALL_LEFT, 2)

        pack(self, sizer)
        self.SetupScrolling()

    def onSelectArray(self, evt=None):
        xrmfile = self.owner.current_file
        name = self.workarray_choice.GetStringSelection()
        dset = xrmfile.get_work_array(h5str(name))
        expr = bytes2str(dset.attrs.get('expression', '<unknonwn>'))
        self.info1.SetLabel("Expression: %s" % expr)

        info = json.loads(bytes2str(dset.attrs.get('info', [])))
        buff = []
        for var, dat in info:
            fname, aname, det, dtc = dat
            if dat[1] != '1':
                buff.append("%s= %s('%s', det=%s, dtcorr=%s)" % (var, fname, aname, det, dtc))
        self.info2.SetLabel('\n'.join(buff))

    def onDeleteArray(self, evt=None):
        name = self.workarray_choice.GetStringSelection()
        xrmfile = self.owner.current_file

        if (wx.ID_YES == Popup(self.owner, """Delete Array '%s' for %s?
    WARNING: This cannot be undone
    """ % (name, xrmfile.filename),
                               'Delete Array?', style=wx.YES_NO)):
                xrmfile.del_work_array(h5str(name))
                self.update_xrmmap(xrmfile)

    def onSaveArray(self, evt=None):
        name = self.name_in.GetValue()
        expr = self.expr_in.GetValue()
        xrmfile = self.owner.current_file
        info = []
        for varname in sorted(self.varfile.keys()):
            fname   = self.varfile[varname].GetStringSelection()
            roiname = self.varroi[varname].GetStringSelection()
            dname   = self.vardet[varname].GetStringSelection()
            dtcorr  = self.varcor[varname].IsChecked()
            info.append((varname, (fname, roiname, dname, dtcorr)))

        if self.map is None:
            self.onShowMap()

        if name in xrmfile.work_array_names():
            if (wx.ID_YES == Popup(self.owner, """Overwrite Array '%s' for %s?
    WARNING: This cannot be undone
    """ % (name, xrmfile.filename),
                                   'Overwrite Array?', style=wx.YES_NO)):
                xrmfile.del_work_array(h5str(name))
            else:
                return

        xrmfile.add_work_array(self.map, h5str(name),
                               expression=h5str(expr),
                               info=json.dumps(info))

        for p in self.owner.nbpanels:
            if hasattr(p, 'update_xrmmap'):
                p.update_xrmmap(xrmfile.xrmmap)

    def onFILE(self, evt, varname='a'):

        print('\t%%%%%%%%%%%%%%%%%%%%%%%%%%%')
        print('\tNot doing anything yet...')
        print('\tShould switch from previous file to: %s' %
                  self.varfile[varname].GetStringSelection())
        print("\tNeeds to ignore 'currrent file' somehow.")
        print('\t%%%%%%%%%%%%%%%%%%%%%%%%%%%\n')

    def onDET(self, evt, varname='a'):

        self.set_roi_choices(self.xrmmap,varname=varname)


    def onROI(self, evt, varname='a'):

        fname   = self.varfile[varname].GetStringSelection()
        roiname = self.varroi[varname].GetStringSelection()
        dname   = self.vardet[varname].GetStringSelection()
        dtcorr  = self.varcor[varname].IsChecked()

        map = self.owner.filemap[fname].get_roimap(roiname, det=dname, dtcorrect=dtcorr)

        self.varshape[varname].SetLabel('Array Shape = %s' % repr(map.shape))
        self.varrange[varname].SetLabel('Range = [%g: %g]' % (map.min(), map.max()))

    def update_xrmmap(self, xrmmap):

        self.cfile = self.owner.current_file
        self.xrmmap = xrmmap

        self.set_det_choices(xrmmap)
        self.set_workarray_choices(xrmmap)

        for vfile in self.varfile.values(): vfile.SetSelection(-1)

    def set_det_choices(self, xrmmap, varname=None):

        det_list = []
        if StrictVersion(self.cfile.version) >= StrictVersion('2.0.0'):
            for grp in xrmmap['roimap'].keys():
                if xrmmap[grp].attrs.get('type', '').find('det') > -1: det_list += [grp]
            if 'scalars' in xrmmap: det_list += ['scalars']
        else:
            for grp in xrmmap.keys():
                if grp.startswith('det'): det_list += [grp]
            ## allows for adding roi in new format to old files
            for grp in xrmmap['roimap'].keys():
                try:
                    if xrmmap[grp].attrs.get('type', '').find('det') > -1:
                        if grp not in det_list: det_list += [grp]
                except:
                    pass

        for sumname in ('detsum','mcasum'):
           if sumname in det_list:
               det_list.remove(sumname)
               det_list.insert(0,sumname)

        if len(det_list) < 1: det_list = ['']

        if varname is None:
            for wid in self.vardet.values():
                wid.SetChoices(det_list)
        else:
            self.vardet[varname].SetChoices(det_list)
        self.set_roi_choices(xrmmap,varname=varname)


    def set_roi_choices(self, xrmmap, varname=None):

        if varname is None:
            for varname in self.vardet.keys():
                dname = self.vardet[varname].GetStringSelection()
                rois = self.update_roi(dname,xrmmap)
                self.varroi[varname].SetChoices(rois)
        else:
            dname = self.vardet[varname].GetStringSelection()
            rois = self.update_roi(dname,xrmmap)
            self.varroi[varname].SetChoices(rois)


    def update_roi(self, detname, xrmmap):

        if StrictVersion(self.cfile.version) >= StrictVersion('2.0.0'):
            if detname == 'scalars':
                rois = ['1'] + list(xrmmap[detname].keys())
            else:
                limits,names = [],xrmmap['roimap'][detname].keys()
                for name in names:
                    limits += [list(xrmmap['roimap'][detname][name]['limits'][:])]
                rois = [x for (y,x) in sorted(zip(limits,names))]
        else:
            rois = ['1']
            if detname in xrmmap.keys():
                rois += list(xrmmap['roimap/sum_name'])
            try:
                limits,names = [],xrmmap['roimap'][detname].keys()
                for name in names:
                    limits += [list(xrmmap['roimap'][detname][name]['limits'][:])]
                rois += [x for (y,x) in sorted(zip(limits,names))]
            except:
                pass

        return rois

    def set_workarray_choices(self, xrmmap):

        c = self.workarray_choice
        c.Clear()
        if 'work' in xrmmap:
            choices = [a for a in xrmmap['work']]
            c.AppendItems(choices)
            c.SetSelection(len(choices)-1)

    def set_file_choices(self, fnames):
        for wid in self.varfile.values():
            wid.SetChoices(fnames)

    def onShowMap(self, event=None, new=True):
        def get_expr(wid):
            val = str(wid.Value)
            if len(val) == 0:
                val = '1'
            return val
        expr_in = get_expr(self.expr_in)


        main_file = None
        _larch = self.owner.larch
        filemap = self.owner.filemap

        for varname in self.varfile.keys():
            fname   = self.varfile[varname].GetStringSelection()
            roiname = self.varroi[varname].GetStringSelection()
            dname   = self.vardet[varname].GetStringSelection()
            dtcorr  = self.varcor[varname].IsChecked()

            self.map = filemap[fname].get_roimap(roiname, det=dname, dtcorrect=dtcorr)

            _larch.symtable.set_symbol(str(varname), self.map)
            if main_file is None:
                main_file = filemap[fname]

        self.map = _larch.eval(expr_in)
        omap = self.map[:, 1:-1]
        info  = 'Intensity: [%g, %g]' %(omap.min(), omap.max())
        title = '%se: %s' % (fname, expr_in)
        subtitles = None
        try:
            x = main_file.get_pos(0, mean=True)
        except:
            x = None
        try:
            y = main_file.get_pos(1, mean=True)
        except:
            y = None

        fname = main_file.filename

        if len(self.owner.im_displays) == 0 or new:
            iframe = self.owner.add_imdisplay(title)

        self.owner.display_map(omap, title=title, subtitles=subtitles,
                               info=info, x=x, y=y, xrmfile=main_file)

class TomographyPanel(GridPanel):
    '''Panel of Controls for reconstructing a tomographic slice'''
    label  = 'Tomography Tools'
    def __init__(self, parent, owner, **kws):

        self.owner = owner
        self.cfile,self.xrmmap = None,None
        self.npts = None

        GridPanel.__init__(self, parent, nrows=8, ncols=6, **kws)

        self.plot_choice = Choice(self, choices=['One color plot','Three color plot'], size=(125, -1))
        self.plot_choice.Bind(wx.EVT_CHOICE, self.plotSELECT)

        self.det_choice = [Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1))]
        self.roi_choice = [Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1))]
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

        self.chk_dftcor  = wx.CheckBox(self, label='Correct Deadtime?')
        self.chk_hotcols = wx.CheckBox(self, label='Ignore First/Last Columns?')
        self.chk_hotcols.SetValue(False)

        self.oper = Choice(self, choices=['/', '*', '-', '+'], size=(80, -1))

        self.sino_show = [Button(self, 'Show New',     size=(100, -1),
                               action=partial(self.onShowSinogram, new=True)),
                          Button(self, 'Replace Last', size=(100, -1),
                               action=partial(self.onShowSinogram, new=False))]
        self.tomo_show = [Button(self, 'Show New',     size=(100, -1),
                               action=partial(self.onShowTomograph, new=True)),
                          Button(self, 'Replace Last', size=(100, -1),
                               action=partial(self.onShowTomograph, new=False))]

        self.tomo_pkg,self.tomo_alg_A,self.tomo_alg_B = return_methods()

        self.alg_choice = [Choice(self, choices=self.tomo_pkg,      size=(125, -1)),
                           Choice(self, choices=self.tomo_alg_A[0], size=(125, -1)),
                           Choice(self, choices=self.tomo_alg_B[0], size=(125, -1))]
        self.alg_choice[0].Bind(wx.EVT_CHOICE, self.onALGchoice)

        self.center_value = wx.SpinCtrlDouble(self, inc=0.1, size=(100, -1),
                                     style=wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP)
        self.refine_center = wx.CheckBox(self, label='Refine?')
        self.center_range = wx.SpinCtrlDouble(self, inc=1, size=(50, -1),
                                     style=wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP)
        self.refine_center.Bind(wx.EVT_CHECKBOX, self.refineCHOICE)

        self.refine_center.SetValue(False)

        #self.center_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.set_center)


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
        self.Add(self.chk_dftcor,                      dcol=2, style=RIGHT)
        self.AddMany((SimpleText(self,'ROI:'),self.roi_choice[-1]),
                                                               style=LEFT,  newrow=True)
        self.Add(self.chk_hotcols,                     dcol=2, style=RIGHT)
        self.AddMany((SimpleText(self,''),self.roi_label[-1]), style=LEFT,  newrow=True)
        #################################################################################
        self.Add(HLine(self, size=(500, 4)),          dcol=8, style=LEFT,  newrow=True)
        #################################################################################
        self.Add(SimpleText(self,'Sinogram:'),         dcol=1, style=RIGHT, newrow=True)
        self.Add(self.sino_show[0],                    dcol=1, style=LEFT)
        self.Add(self.sino_show[1],                    dcol=1, style=LEFT)
        #################################################################################
        self.Add(HLine(self, size=(500, 4)),          dcol=8, style=LEFT,  newrow=True)
        #################################################################################
        self.Add(SimpleText(self,'Reconstruction: '),  dcol=1, style=RIGHT, newrow=True)
        self.AddMany((self.alg_choice[0],self.alg_choice[1],self.alg_choice[2]),
                                                       dcol=1, style=LEFT)
        self.Add(SimpleText(self,'Center: '),          dcol=1, style=RIGHT, newrow=True)
        self.AddMany((self.center_value,self.refine_center,self.center_range),
                                                       dcol=1, style=LEFT)
        self.AddMany((SimpleText(self,''),self.tomo_show[0],self.tomo_show[1]),
                                                       dcol=1, style=LEFT,  newrow=True)
        #################################################################################
        self.pack()


        self.disable_options()

    def disable_options(self):

        all_choices = [self.plot_choice]+self.det_choice+self.roi_choice+self.alg_choice+[self.oper]
        for chc in all_choices: chc.Disable()
        for chk in (self.chk_dftcor,self.chk_hotcols,self.refine_center):
            chk.Disable()
        for btn in (self.sino_show+self.tomo_show):
            btn.Disable()
        self.center_value.Disable()
        self.center_range.Disable()

    def enable_options(self):

        self.plot_choice.Enable()

        self.det_choice[0].Enable()
        self.det_choice[-1].Enable()
        self.roi_choice[0].Enable()
        self.roi_choice[-1].Enable()

        self.oper.Enable()

        for chc in self.alg_choice: chc.Enable()

        for chk in (self.chk_dftcor,self.chk_hotcols): chk.Enable()
        for btn in (self.sino_show): btn.Enable()

        if self.tomo_pkg[0] != '':
            for btn in (self.tomo_show): btn.Enable()
            self.refine_center.Enable()
            self.center_value.Enable()
            self.center_range.SetValue(10)
            self.center_range.SetRange(1,20)

    def update_xrmmap(self, xrmmap):

        self.cfile  = self.owner.current_file
        self.xrmmap = self.cfile.xrmmap
        scan_version = getattr(self.cfile, 'scan_version', 2.00)
        hotcol = True if scan_version < 1.36 else False

        self.chk_hotcols.SetValue(hotcol)
        self.chk_dftcor.SetValue(True)

        self.enable_options()
        self.set_det_choices(xrmmap)

        try:
            self.npts = len(self.cfile.get_pos('fine x', mean=True))
        except:
            self.npts = len(self.cfile.get_pos('x', mean=True))

        if self.tomo_pkg[0] != '':
            center = self.cfile.get_tomo_center()
            self.center_value.SetRange(-0.5*self.npts,1.5*self.npts)
            self.center_value.SetValue(center)

        self.plotSELECT()
        self.refineCHOICE()

    def refineCHOICE(self,event=None):

        self.center_range.Disable()
        if self.alg_choice[0].GetStringSelection().startswith('sci'):
            if self.refine_center.GetValue():
                self.center_range.Enable()
            self.center_value.SetIncrement(1)
        else:
            self.center_value.SetIncrement(0.1)

    def onALGchoice(self,event=None):
        self.alg_choice[1].SetChoices(self.tomo_alg_A[self.alg_choice[0].GetSelection()])
        self.alg_choice[2].SetChoices(self.tomo_alg_B[self.alg_choice[0].GetSelection()])

        self.refineCHOICE()

    def detSELECT(self,idet,event=None):
        self.set_roi_choices(self.cfile.xrmmap,idet=idet)

    def roiSELECT(self,iroi,event=None):

        detname = self.det_choice[iroi].GetStringSelection()
        roiname = self.roi_choice[iroi].GetStringSelection()

        if StrictVersion(self.cfile.version) >= StrictVersion('2.0.0'):
            try:
                roi = self.cfile.xrmmap['roimap'][detname][roiname]
                limits = roi['limits'][:]
                units = roi['limits'].attrs['units']
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
            if self.plot_choice.GetSelection() == 0:
                for i in (1,2):
                    self.det_choice[i].Disable()
                    self.roi_choice[i].Disable()
                    self.roi_label[i].SetLabel('')
                for lbl in self.det_label:
                    lbl.SetLabel('')
            else:
                for i in (1,2):
                    self.det_choice[i].Enable()
                    self.roi_choice[i].Enable()
                for i,label in enumerate(['Red','Green','Blue']):
                    self.det_label[i].SetLabel(label)
                self.set_roi_choices(self.cfile.xrmmap)

    def onLasso(self, selected=None, mask=None, data=None, xrmfile=None, **kws):
        if xrmfile is None: xrmfile = self.owner.current_file
        ny, nx, npos = xrmfile.xrmmap['positions/pos'].shape
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
        plt3 = (self.plot_choice.GetSelection() == 1)
        oprtr = self.oper.GetStringSelection()

        if xrmfile is None: xrmfile = self.owner.current_file

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

        args={'trim_sino'  : flagxrd,
              'no_hotcols' : self.chk_hotcols.GetValue(),
              'dtcorrect'  : self.chk_dftcor.GetValue()}

        r_map = xrmfile.get_sinogram(det_name[0],roi_name[0],**args)
        if plt3:
            g_map = xrmfile.get_sinogram(det_name[1],roi_name[1],**args)
            b_map = xrmfile.get_sinogram(det_name[2],roi_name[2],**args)

        if roi_name[-1] != '1':
            mapx = xrmfile.get_sinogram(det_name[-1],roi_name[-1],**args)

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

        ### axes order: slices, x, 2theta
        if len(sino.shape) < 3: sino = np.reshape(sino,(1,sino.shape[0],sino.shape[1]))
        sino = np.flip(sino,1)

        return title,subtitles,info,xrmfile.x,xrmfile.ome,sino

    def onShowSinogram(self, event=None, new=True):

        title,subtitles,info,x,ome,sino = self.calculateSinogram()
        
        omeoff, xoff = 0, 0
        if len(self.owner.im_displays) == 0 or new:
            iframe = self.owner.add_imdisplay(title, _cursorlabels=False, _savecallback=False)

        ## reorder to: 2th, x, slice for viewing
        sino = np.einsum('kji->ijk', sino)

        ## for one color plot
        if sino.shape[2] == 1: sino = np.reshape(sino,(sino.shape[0],sino.shape[1]))
        self.owner.display_map(sino, title=title, info=info, x=x, y=ome,
                               xoff=xoff, yoff=omeoff, subtitles=subtitles,
                               xrmfile=self.cfile, _cursorlabels=False, _savecallback=False)


    def onShowTomograph(self, event=None, new=True):

        xrmfile = self.owner.current_file

        ## returns sino in order: slice, x, 2theta
        title,subtitles,info,x,ome,sino = self.calculateSinogram()

        args = {'refine_cen'  : self.refine_center.GetValue(),
                'cen_range'   : self.center_range.GetValue(),
                'center'      : self.center_value.GetValue(),
                'method'      : self.alg_choice[0].GetStringSelection(),
                'algorithm_A' : self.alg_choice[1].GetStringSelection(),
                'algorithm_B' : self.alg_choice[2].GetStringSelection(),
                'omega'       : ome}


        tomo_center, tomo = xrmfile.get_tomograph(sino, **args)

        self.set_center(tomo_center)
        self.refine_center.SetValue(False)

        omeoff, xoff = 0, 0
        alg = [alg_ch.GetStringSelection() for alg_ch in self.alg_choice]
        if alg[1] != '' and alg[1] is not None:
            title = '[%s : %s @ %0.1f] %s ' % (alg[0],alg[1],tomo_center,title)
        else:
            title = '[%s @ %0.1f] %s' % (alg[0],tomo_center,title)

        if len(self.owner.im_displays) == 0 or new:
            iframe = self.owner.add_imdisplay(title, _cursorlabels=False, _savecallback=False)

        self.owner.display_map(tomo, title=title, info=info, x=x, y=x,
                               xoff=xoff, yoff=xoff, subtitles=subtitles,
                               xrmfile=self.cfile, _cursorlabels=False, _savecallback=False)

    def set_center(self,center):

        self.center_value.SetValue(center)
        self.cfile.update_tomo_center(center)

    def set_det_choices(self, xrmmap):

        det_list = []
        if StrictVersion(self.cfile.version) >= StrictVersion('2.0.0'):
            for grp in xrmmap['roimap'].keys():
                if xrmmap[grp].attrs.get('type', '').find('det') > -1: det_list += [grp]
            if 'scalars' in xrmmap: det_list += ['scalars']
        else:
            for grp in xrmmap.keys():
                if grp.startswith('det'): det_list += [grp]
            ## allows for adding roi in new format to old files
            for grp in xrmmap['roimap'].keys():
                try:
                    if xrmmap[grp].attrs.get('type', '').find('det') > -1:
                        if grp not in det_list: det_list += [grp]
                except:
                    pass

        for sumname in ('detsum','mcasum'):
           if sumname in det_list:
               det_list.remove(sumname)
               det_list.insert(0,sumname)

        for det_ch in self.det_choice:
            det_ch.SetChoices(det_list)
        if 'scalars' in det_list: ## should set 'denominator' to scalars as default
            self.det_choice[-1].SetStringSelection('scalars')

        self.set_roi_choices(xrmmap)

    def set_roi_choices(self, xrmmap, idet=None):

        if idet is None:
            for idet,det_ch in enumerate(self.det_choice):
                detname = self.det_choice[idet].GetStringSelection()
                rois = self.update_roi(detname,xrmmap)

                self.roi_choice[idet].SetChoices(rois)
                self.roiSELECT(idet)
        else:
            detname = self.det_choice[idet].GetStringSelection()
            rois = self.update_roi(detname,xrmmap)

            self.roi_choice[idet].SetChoices(rois)
            self.roiSELECT(idet)


    def update_roi(self, detname, xrmmap):

        if StrictVersion(self.cfile.version) >= StrictVersion('2.0.0'):
            if detname == 'scalars':
                rois = ['1'] + list(xrmmap[detname].keys())
            else:
                limits,names = [],xrmmap['roimap'][detname].keys()
                for name in names:
                    limits += [list(xrmmap['roimap'][detname][name]['limits'][:])]
                rois = [x for (y,x) in sorted(zip(limits,names))]
        else:
            rois = ['1']
            if detname in xrmmap.keys():
                rois += list(xrmmap['roimap/sum_name'])
            try:
                limits,names = [],xrmmap['roimap'][detname].keys()
                for name in names:
                    limits += [list(xrmmap['roimap'][detname][name]['limits'][:])]
                rois += [x for (y,x) in sorted(zip(limits,names))]
            except:
                pass

        return rois

##################################
class MapPanel(GridPanel):
    '''Panel of Controls for viewing maps'''
    label  = 'ROI Map'
    def __init__(self, parent, owner, **kws):

        self.owner = owner
        self.cfile,self.xrmmap = None,None

        GridPanel.__init__(self, parent, nrows=8, ncols=6, **kws)

        self.plot_choice = Choice(self, choices=['One color plot','Three color plot'], size=(125, -1))
        self.plot_choice.Bind(wx.EVT_CHOICE, self.plotSELECT)

        self.det_choice = [Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1))]
        self.roi_choice = [Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1)),
                           Choice(self, choices=[], size=(125, -1))]
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

        self.chk_dftcor  = Check(self, label='Correct Deadtime?')
        self.chk_hotcols = Check(self, label='Ignore First/Last Columns?')
        self.chk_hotcols.SetValue(False)

        self.oper = Choice(self, choices=['/', '*', '-', '+', 'vs'], size=(80, -1))

        fopts = dict(minval=-20000, precision=0, size=(70, -1))
        self.lims = [FloatCtrl(self, value= 0, **fopts),
                     FloatCtrl(self, value=-1, **fopts),
                     FloatCtrl(self, value= 0, **fopts),
                     FloatCtrl(self, value=-1, **fopts)]

        for wid in self.lims: wid.Disable()

        self.limrange  = Check(self, default=False,
                               label=' Limit Map Range to Pixel Range:',
                               action=self.onLimitRange)
        self.range_txt = [SimpleText(self, 'X Range:'),
                          SimpleText(self, ':'),
                          SimpleText(self, 'Y Range:'),
                          SimpleText(self, ':')]

        self.map_show = [Button(self, 'Show New',     size=(100, -1),
                               action=partial(self.onROIMap, new=True)),
                          Button(self, 'Replace Last', size=(100, -1),
                               action=partial(self.onROIMap, new=False))]

        #################################################################################
        self.AddMany((SimpleText(self,'Plot type:'),self.plot_choice),
                                                               style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,''),self.det_label[0],
                       self.det_label[1],self.det_label[2]),   style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,'Detector:'),self.det_choice[0],
                       self.det_choice[1],self.det_choice[2]), style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,'ROI:'),self.roi_choice[0],
                       self.roi_choice[1],self.roi_choice[2]), style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,''),self.roi_label[0],
                       self.roi_label[1],self.roi_label[2]),   style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,'Operator:'),self.oper), style=LEFT,  newrow=True)
        self.AddMany((SimpleText(self,'Detector:'),self.det_choice[-1]),
                                                               style=LEFT,  newrow=True)
        self.Add(self.chk_dftcor,                      dcol=2, style=RIGHT)
        self.AddMany((SimpleText(self,'ROI:'),self.roi_choice[-1]),
                                                               style=LEFT,  newrow=True)
        self.Add(self.chk_hotcols,  dcol=2, style=RIGHT)
        self.AddMany((SimpleText(self,''),self.roi_label[-1]), style=LEFT,  newrow=True)
        #################################################################################
        self.Add(HLine(self, size=(500, 4)),          dcol=8, style=LEFT,  newrow=True)
        #################################################################################
        self.Add(self.limrange,                        dcol=4, style=LEFT,  newrow=True)
        self.Add(self.range_txt[0],                    dcol=1, style=LEFT,  newrow=True)
        self.Add(self.lims[0],                         dcol=1, style=LEFT)
        self.Add(self.range_txt[1],                    dcol=1, style=LEFT)
        self.Add(self.lims[1],                         dcol=1, style=LEFT)
        self.Add(self.range_txt[2],                    dcol=1, style=LEFT,  newrow=True)
        self.Add(self.lims[2],                         dcol=1, style=LEFT)
        self.Add(self.range_txt[3],                    dcol=1, style=LEFT)
        self.Add(self.lims[3],                         dcol=1, style=LEFT)
        #################################################################################
        self.Add(HLine(self, size=(500, 4)),          dcol=8, style=LEFT,  newrow=True)
        #################################################################################
        self.Add(SimpleText(self,'ROI Map:'),          dcol=1, style=RIGHT, newrow=True)
        self.Add(self.map_show[0],                     dcol=1, style=LEFT)
        self.Add(self.map_show[1],                     dcol=1, style=LEFT)
        #################################################################################
        self.pack()

        self.disable_options()

    def disable_options(self):

        all_choices = [self.plot_choice]+self.det_choice+self.roi_choice+[self.oper]
        for chc in all_choices: chc.Disable()
        for chk in (self.chk_dftcor,self.chk_hotcols,self.limrange): chk.Disable()
        for btn in self.map_show: btn.Disable()

    def enable_options(self):

        self.plot_choice.Enable()

        self.det_choice[0].Enable()
        self.det_choice[-1].Enable()
        self.roi_choice[0].Enable()
        self.roi_choice[-1].Enable()

        self.oper.Enable()

        for chk in (self.chk_dftcor,self.chk_hotcols,self.limrange): chk.Enable()
        for btn in self.map_show: btn.Enable()

    def update_xrmmap(self, xrmmap):

        self.cfile  = self.owner.current_file
        self.xrmmap = self.cfile.xrmmap
        scan_version = getattr(self.cfile, 'scan_version', 2.00)
        hotcol = True if scan_version < 1.36 else False

        self.chk_hotcols.SetValue(hotcol)
        self.chk_dftcor.SetValue(True)

        self.enable_options()
        self.set_det_choices(xrmmap)
        self.plotSELECT()

    def onLimitRange(self, event=None):
        if self.limrange.IsChecked():
            for wid in self.lims:
                wid.Enable()
        else:
            for wid in self.lims:
                wid.Disable()

    def detSELECT(self,idet,event=None):

        self.set_roi_choices(self.cfile.xrmmap,idet=idet)

    def roiSELECT(self,iroi,event=None):

        detname = self.det_choice[iroi].GetStringSelection()
        roiname = self.roi_choice[iroi].GetStringSelection()

        if StrictVersion(self.cfile.version) >= StrictVersion('2.0.0'):
            try:
                roi = self.cfile.xrmmap['roimap'][detname][roiname]
                limits = roi['limits'][:]
                units = roi['limits'].attrs['units']
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
            oper_ch = self.oper.GetSelection()
            if self.plot_choice.GetSelection() == 0:
                for i in (1,2):
                    self.det_choice[i].Disable()
                    self.roi_choice[i].Disable()
                    self.roi_label[i].SetLabel('')
                for lbl in self.det_label:
                    lbl.SetLabel('')
                oper_chs = ['/', '*', '-', '+', 'vs']
            else:
                for i in (1,2):
                    self.det_choice[i].Enable()
                    self.roi_choice[i].Enable()
                for i,label in enumerate(['Red','Green','Blue']):
                    self.det_label[i].SetLabel(label)
                self.set_roi_choices(self.cfile.xrmmap)
                oper_chs = ['/', '*', '-', '+']

            self.oper.SetChoices(oper_chs)
            if oper_ch >= len(oper_chs):
                self.oper.SetSelection(0)
            else:
                self.oper.SetSelection(oper_ch)

    def onClose(self):
        for p in self.plotframes:
            try:
                p.Destroy()
            except:
                pass

    def ShowMap(self,xrmfile=None,new=True):

        subtitles = None
        plt3 = (self.plot_choice.GetSelection() == 1)
        oprtr = self.oper.GetStringSelection()

        args={'no_hotcols': self.chk_hotcols.GetValue(),
              'dtcorrect' : self.chk_dftcor.GetValue()}

        if xrmfile is None: xrmfile = self.owner.current_file

        det_name,roi_name = [],[]
        plt_name = []
        for det,roi in zip(self.det_choice,self.roi_choice):
            det_name += [det.GetStringSelection()]
            roi_name += [roi.GetStringSelection()]
            if det_name[-1] == 'scalars':
                plt_name += ['%s' % roi_name[-1]]
            else:
                plt_name += ['%s(%s)' % (roi_name[-1],det_name[-1])]

        if roi_name[-1] != '1':
            mapx = xrmfile.get_roimap(roi_name[-1],det=det_name[-1],**args)
            ## remove negative background counts for dividing
            if oprtr == '/': mapx[np.where(mapx==0)] = 1.
        else:
            mapx = 1.

        r_map = xrmfile.get_roimap(roi_name[0],det=det_name[0],**args)
        if plt3:
            g_map = xrmfile.get_roimap(roi_name[1],det=det_name[1],**args)
            b_map = xrmfile.get_roimap(roi_name[2],det=det_name[2],**args)

        x = xrmfile.get_pos(0, mean=True)
        y = xrmfile.get_pos(1, mean=True)

        pref, fname = os.path.split(xrmfile.filename)
        if plt3:
            if   oprtr == '+': map = np.array([r_map+mapx, g_map+mapx, b_map+mapx])
            elif oprtr == '-': map = np.array([r_map-mapx, g_map-mapx, b_map-mapx])
            elif oprtr == '*': map = np.array([r_map*mapx, g_map*mapx, b_map*mapx])
            elif oprtr == '/': map = np.array([r_map/mapx, g_map/mapx, b_map/mapx])
            map = np.einsum('kij->ijk', map)

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
            if   oprtr == '+': map = r_map+mapx
            elif oprtr == '-': map = r_map-mapx
            elif oprtr == '*': map = r_map*mapx
            elif oprtr == '/': map = r_map/mapx

            if roi_name[-1] == '1' and oprtr == '/':
                title = plt_name[0]
            else:
                title = '%s %s %s' % (plt_name[0],oprtr,plt_name[-1])
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
        ny, nx, npos = xrmfile.xrmmap['positions/pos'].shape
        indices = []
        for idx in selected:
            iy, ix = divmod(idx, ny)
            indices.append((ix, iy))


    def ShowCorrel(self,xrmfile=None):

        args={'no_hotcols': self.chk_hotcols.GetValue(),
              'dtcorrect' : self.chk_dftcor.GetValue()}

        if xrmfile is None: xrmfile = self.owner.current_file

        det_name,roi_name = [],[]
        plt_name = []
        for det,roi in zip(self.det_choice,self.roi_choice):
            det_name += [det.GetStringSelection()]
            roi_name += [roi.GetStringSelection()]
            if det_name[-1] == 'scalars':
                plt_name += ['%s' % roi_name[-1]]
            else:
                plt_name += ['%s(%s)' % (roi_name[-1],det_name[-1])]

        if roi_name[-1] == '1' or roi_name[0] == '1':
            print("WARNING: cannot make correlation plot with matrix of '1'")
            return

        map1 = xrmfile.get_roimap(roi_name[0],det=det_name[0],**args)
        map2 = xrmfile.get_roimap(roi_name[-1],det=det_name[-1],**args)

        x = xrmfile.get_pos(0, mean=True)
        y = xrmfile.get_pos(1, mean=True)

        pref, fname = os.path.split(xrmfile.filename)
        title ='%s: %s vs. %s' %(fname, plt_name[-1], plt_name[0])

        # try to use correlation plot from wxmplot 0.9.23 and later
        if CorrelatedMapFrame is not None:
            correl_plot = CorrelatedMapFrame(parent=self.owner, xrmfile=xrmfile)
            correl_plot.display(map1, map2, name1=plt_name[0], name2=plt_name[-1],
                                x=x, y=y, title=title)
        else:
            correl_plot = PlotFrame(title=title, output_title=title)
            correl_plot.plot(map2.flatten(), map1.flatten(),
                             xlabel=plt_name[-1], ylabel=plt_name[0],
                             marker='o', markersize=4, linewidth=0)
            correl_plot.panel.cursor_mode = 'lasso'
            coreel_plot.panel.lasso_callback = partial(self.onLasso, xrmfile=xrmfile)

        correl_plot.Show()
        correl_plot.Raise()
        self.owner.plot_displays.append(correl_plot)


    def onROIMap(self, event=None, new=True):

        if self.oper.GetStringSelection() == 'vs':
            self.ShowCorrel()
        else:
            self.ShowMap(new=new)

    def set_det_choices(self, xrmmap):

        det_list = []
        if StrictVersion(self.cfile.version) >= StrictVersion('2.0.0'):
            for grp in xrmmap['roimap'].keys():
                if xrmmap[grp].attrs.get('type', '').find('det') > -1: det_list += [grp]
            if 'scalars' in xrmmap: det_list += ['scalars']
        else:
            for grp in xrmmap.keys():
                if grp.startswith('det'): det_list += [grp]
            ## allows for adding roi in new format to old files
            for grp in xrmmap['roimap'].keys():
                try:
                    if xrmmap[grp].attrs.get('type', '').find('det') > -1:
                        if grp not in det_list: det_list += [grp]
                except:
                    pass

        for sumname in ('detsum','mcasum'):
           if sumname in det_list:
               det_list.remove(sumname)
               det_list.insert(0,sumname)

        if len(det_list) < 1: det_list = ['']

        for det_ch in self.det_choice:
            det_ch.SetChoices(det_list)
        if 'scalars' in det_list: ## should set 'denominator' to scalars as default
            self.det_choice[-1].SetStringSelection('scalars')

        self.set_roi_choices(xrmmap)

    def set_roi_choices(self, xrmmap, idet=None):

        if idet is None:
            for idet,det_ch in enumerate(self.det_choice):
                detname = self.det_choice[idet].GetStringSelection()
                rois = self.update_roi(detname,xrmmap)

                self.roi_choice[idet].SetChoices(rois)
                self.roiSELECT(idet)
        else:
            detname = self.det_choice[idet].GetStringSelection()
            rois = self.update_roi(detname,xrmmap)

            self.roi_choice[idet].SetChoices(rois)
            self.roiSELECT(idet)


    def update_roi(self, detname, xrmmap):

        if StrictVersion(self.cfile.version) >= StrictVersion('2.0.0'):
            if detname == 'scalars':
                rois = ['1'] + list(xrmmap[detname].keys())
            else:
                limits,names = [],xrmmap['roimap'][detname].keys()
                for name in names:
                    limits += [list(xrmmap['roimap'][detname][name]['limits'][:])]
                rois = [x for (y,x) in sorted(zip(limits,names))]
        else:
            rois = ['1']
            if detname in xrmmap.keys():
                rois += list(xrmmap['roimap/sum_name'])
            try:
                limits,names = [],xrmmap['roimap'][detname].keys()
                for name in names:
                    limits += [list(xrmmap['roimap'][detname][name]['limits'][:])]
                rois += [x for (y,x) in sorted(zip(limits,names))]
            except:
                pass

        return rois

class MapInfoPanel(scrolled.ScrolledPanel):
    """Info Panel """
    label  = 'Map Info'
    def __init__(self, parent, owner, **kws):
        scrolled.ScrolledPanel.__init__(self, parent, -1,
                                        style=wx.GROW|wx.TAB_TRAVERSAL, **kws)
        self.owner = owner

        sizer = wx.GridBagSizer(3, 3)
        self.wids = {}

        ir = 0

        for label in ('Facility','Run Cycle','Proposal Number','User group',
                      'Scan Started','File Compression','Map Data',
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


    def update_xrmmap(self, xrmmap):
        self.wids['Scan Started'].SetLabel( bytes2str(xrmmap.attrs['Start_Time']))

        try:
            self.wids['File Compression'].SetLabel( bytes2str(xrmmap.attrs['Compression']))
        except:
            self.wids['File Compression'].SetLabel('')

        comments = h5str(xrmmap['config/scan/comments'].value).split('\n', 2)
        for i, comm in enumerate(comments):
            self.wids['User Comments %i' %(i+1)].SetLabel(comm)

        pos_addrs = [str(x) for x in xrmmap['config/positioners'].keys()]
        pos_label = [str(x.value) for x in xrmmap['config/positioners'].values()]

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
        pixtime = self.owner.current_file.pixeltime
        if pixtime is None:
            pixtime = self.owner.current_file.calc_pixeltime()
        pixtime =int(round(1000.0*pixtime))
        self.wids['Dwell Time'].SetLabel('%.1f ms per pixel' % pixtime)

        env_names = list(xrmmap['config/environ/name'])
        env_vals  = list(xrmmap['config/environ/value'])
        env_addrs = list(xrmmap['config/environ/address'])

        fines = {'X': '?', 'Y': '?'}
        i0vals = {'flux':'?', 'current':'?'}
        cur_energy = ''

        for name, addr, val in zip(env_names, env_addrs, env_vals):
            name = str(name).lower()

            if 'ring_current' in name or 'ring current' in name:
                self.wids['Ring Current'].SetLabel('%s mA' % val)
            elif ('mono.energy' in name or 'mono energy' in name) and cur_energy=='':
                self.owner.current_energy = float(val)/1000.
                self.owner.current_file.mono_energy = float(val)/1000.
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

        folderpath = bytes2str(xrmmap.attrs['Map_Folder'])
        if len(folderpath) > 35:
            folderpath = '...'+bytes2str(xrmmap.attrs['Map_Folder'][-35:])
        self.wids['Original data path'].SetLabel('%s' % folderpath)

        self.wids['XRD Calibration'].SetLabel('')
        try:
            xrdgp = xrmmap['xrd1D']
            if os.path.exists(xrdgp.attrs['calfile']):
                self.wids['XRD Calibration'].SetLabel('%s' % os.path.split(xrdgp.attrs['calfile'])[-1])
        except:
            pass

        try:
            notegrp = xrmmap['config/notes']
        except:
            notegrp = None

        if notegrp is not None:
            self.wids['Facility'].SetLabel('%s @ %s' % (notegrp.attrs['beamline'],
                                                        notegrp.attrs['facility']))
            self.wids['Run Cycle'].SetLabel(notegrp.attrs['run'])
            self.wids['Proposal Number'].SetLabel(notegrp.attrs['proposal'])
            self.wids['User group'].SetLabel(notegrp.attrs['user'])
        else:
            self.wids['Facility'].SetLabel('')
            self.wids['Run Cycle'].SetLabel('')
            self.wids['Proposal Number'].SetLabel('')
            self.wids['User group'].SetLabel('')

        FLAGXRD2D,FLAGXRD1D,FLAGXRF = False,False,True
        for key,val in zip(xrmmap['flags'].attrs.keys(),xrmmap['flags'].attrs.values()):
            if   key == 'xrf':           FLAGXRF = val
            elif key == 'xrd':           FLAGXRD2D = val
            elif key.lower() == 'xrd2d': FLAGXRD2D = val
            elif key.lower() == 'xrd1d': FLAGXRD1D = val

        if FLAGXRF:
            if FLAGXRD2D and FLAGXRD1D:
                datastr = 'XRF, 2D- and 1D-XRD data'
            elif FLAGXRD2D:
                datastr = 'XRF, 2D-XRD data'
            elif FLAGXRD1D:
                datastr = 'XRF, 1D-XRD data'
            else:
                datastr = 'XRF data'
        else:
            if FLAGXRD2D and FLAGXRD1D:
                datastr = '2D- and 1D-XRD data'
            elif FLAGXRD2D:
                datastr = '2D-XRD data'
            elif FLAGXRD1D:
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

    def __init__(self, parent, owner, **kws):
        scrolled.ScrolledPanel.__init__(self, parent, -1,
                                        style=wx.GROW|wx.TAB_TRAVERSAL, **kws)

        ######################################
        ## GENERAL MAP AREAS
        self.owner = owner
        pane = wx.Panel(self)
        sizer = wx.GridBagSizer(3, 3)
        self.choices = {}
        self.choice = Choice(pane, choices=[], size=(200, -1), action=self.onSelect)
        self.desc    = wx.TextCtrl(pane,   -1, '',  size=(200, -1))
        self.info1   = wx.StaticText(pane, -1, '',  size=(250, -1))
        self.info2   = wx.StaticText(pane, -1, '',  size=(250, -1))
        self.onmap   = Button(pane, 'Show on Map',  size=(135, -1), action=self.onShow)
        self.clear   = Button(pane, 'Clear Map',    size=(135, -1), action=self.onClear)
        self.delete  = Button(pane, 'Delete Area',  size=(135, -1), action=self.onDelete)
        self.update  = Button(pane, 'Save Label',   size=(135, -1), action=self.onLabel)
        self.bexport = Button(pane, 'Export Areas', size=(135, -1), action=self.onExport)
        self.bimport = Button(pane, 'Import Areas', size=(135, -1), action=self.onImport)
        ######################################

        ######################################
        ## SPECIFIC TO XRF MAP AREAS
        self.onstats  = Button(pane, 'Calculate Stats', size=(135, -1),
                                                action=self.onShowStats)
        self.xrf      = Button(pane, 'Show XRF (Fore)', size=(135, -1),
                                                action=self.onXRF)
        self.xrf2     = Button(pane, 'Show XRF (Back)', size=(135, -1),
                                                action=partial(self.onXRF, as_mca2=True))
        self.onreport = Button(pane, 'Save XRF Report', size=(135, -1),
                                                action=self.onReport)
        self.cor = Check(pane, label='Correct Deadtime?')
        legend = wx.StaticText(pane, -1, 'Values in CPS, Time in ms', size=(200, -1))

        ######################################
        ## SPECIFIC TO XRD MAP AREAS
        self.xrd_save  = Button(pane, 'Save XRD Data', size=(135, -1),
                                                action=partial(self.onXRD,save=True))
        self.xrd_plot  = Button(pane, 'Show XRD Data', size=(135, -1),
                                                action=partial(self.onXRD,show=True))
        ######################################

        def txt(s):
            return SimpleText(pane, s)
        sizer.Add(txt('Map Areas'),         ( 0, 0), (1, 1), ALL_CEN,  2)
        sizer.Add(self.info1,               ( 0, 1), (1, 4), ALL_LEFT, 2)
        sizer.Add(self.info2,               ( 1, 1), (1, 4), ALL_LEFT, 2)
        sizer.Add(txt('Area: '),            ( 2, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.choice,              ( 2, 1), (1, 3), ALL_LEFT, 2)
        sizer.Add(self.delete,              ( 2, 4), (1, 1), ALL_LEFT, 2)
        sizer.Add(txt('New Label: '),       ( 3, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.desc,                ( 3, 1), (1, 3), ALL_LEFT, 2)
        sizer.Add(self.update,              ( 3, 4), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.onmap,               ( 4, 0), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.clear,               ( 4, 2), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.onstats,             ( 4, 4), (1, 1), ALL_LEFT, 2)

        sizer.Add(self.bexport,             ( 5, 0), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.bimport,             ( 5, 2), (1, 2), ALL_LEFT, 2)

        sizer.Add(self.xrf,                 ( 6, 0), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.xrf2,                ( 6, 2), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.cor,                 ( 6, 4), (1, 2), ALL_LEFT, 2)

        sizer.Add(self.onreport,            ( 7, 0), (1, 2), ALL_LEFT, 2)

        sizer.Add(self.xrd_save,            ( 8, 0), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.xrd_plot,            ( 8, 2), (1, 2), ALL_LEFT, 2)

        sizer.Add(legend,                   (10, 1), (1, 2), ALL_LEFT, 2)
        pack(pane, sizer)

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

    def show_stats(self):
        # self.stats = self.xrmfile.get_area_stats(self.areaname)
        if self.report is None:
            return

        self.choice.Disable()
        self.report.DeleteAllItems()
        self.report_data = []
        areaname  = self._getarea()
        xrmfile  = self.owner.current_file
        xrmmap  = xrmfile.xrmmap
        area = xrmfile.get_area(name=areaname)
        amask = area.value
        if 'roistats' in area.attrs:
           for dat in json.loads(area.attrs['roistats']):
               dat = tuple(dat)
               self.report_data.append(dat)
               self.report.AppendItem(dat)
           self.choice.Enable()
           return

        d_addrs = [d.lower() for d in xrmmap['roimap/det_address']]
        d_names = [d for d in xrmmap['roimap/det_name']]

        # count times
        ctime = xrmmap['roimap/det_raw'][:,:,0]
        if amask.shape[1] == ctime.shape[1] - 2: # hotcols
            ctime = ctime[:,1:-1]

        ctime = [1.e-6*ctime[amask]]
        for i in range(xrmmap.attrs['N_Detectors']):
            tname = 'det%i/realtime' % (i+1)
            rtime = xrmmap[tname].value
            if amask.shape[1] == rtime.shape[1] - 2: # hotcols
                rtime = rtime[:,1:-1]
            ctime.append(1.e-6*rtime[amask])

        for idet, dname in enumerate(d_names):
            daddr = d_addrs[idet]
            det = 0
            if 'mca' in daddr:
                det = 1
                words = daddr.split('mca')
                if len(words) > 1:
                    det = int(words[1].split('.')[0])
            if idet == 0:
                d = 1.e3*ctime[0]
            else:
                d = xrmmap['roimap/det_raw'][:,:,idet]
                if amask.shape[1] == d.shape[1] - 2: # hotcols
                    d = d[:,1:-1]
                d = d[amask]/ctime[det]

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
        if False and 'roistats' not in area.attrs:
           area.attrs['roistats'] = json.dumps(self.report_data)
           xrmfile.h5root.flush()

        self.choice.Enable()

    def update_xrmmap(self, xrmmap):
        self.set_area_choices(xrmmap, show_last=True)

    def set_area_choices(self, xrmmap, show_last=False):
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

        mca   = self.owner.current_file.get_mca_area(aname)
        area  = self.owner.current_file.xrmmap['areas/%s' % aname]
        npix = len(area.value[np.where(area.value)])
        pixtime = self.owner.current_file.pixeltime
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

    def onSelect(self, event=None):
        aname = self._getarea()
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

        info1_fmt = '%i Pixels, %i ms/pixel, %.3f total seconds'
        info2_fmt = ' Range (pixels)   X : [%i:%i],  Y : [%i:%i] '

        self.info1.SetLabel(info1_fmt%(npix, int(round(1000.0*pixtime)), dtime))
        self.info2.SetLabel(info2_fmt%(xvals.min(), xvals.max(),
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
        area  = self.owner.current_file.xrmmap['areas/%s' % aname]
        label = bytes2str(area.attrs.get('description', aname))
        if len(self.owner.im_displays) > 0:
            imd = self.owner.im_displays[-1]
            imd.panel.add_highlight_area(area.value, label=label)

    def onDelete(self, event=None):
        aname = self._getarea()
        erase = Popup(self.owner, self.delstr % aname,
                      'Delete Area?', style=wx.YES_NO)
        if erase:
            xrmmap = self.owner.current_file.xrmmap
            del xrmmap['areas/%s' % aname]
            self.set_area_choices(xrmmap)

    def onClear(self, event=None):
        if len(self.owner.im_displays) > 0:
            imd = self.owner.im_displays[-1]
            for area in imd.panel.conf.highlight_areas:
                for w in area.collections + area.labelTexts:
                    w.remove()

            imd.panel.conf.highlight_areas = []
            imd.panel.redraw()

    def _getmca_area(self, areaname, **kwargs):
        self._mca = self.owner.current_file.get_mca_area(areaname, **kwargs)

    def _getxrd_area(self, areaname, xrd, **kwargs):
        if xrd == '1D':
            self._xrd = self.owner.current_file.get_1Dxrd_area(areaname, **kwargs)
        elif xrd == '2D':
            self._xrd = self.owner.current_file.get_2Dxrd_area(areaname, **kwargs)

    def onXRF(self, event=None, as_mca2=False):
        aname = self._getarea()
        xrmfile = self.owner.current_file
        area  = xrmfile.xrmmap['areas/%s' % aname]
        label = bytes2str(area.attrs.get('description', aname))
        self._mca  = None
        dtcorrect = self.cor.IsChecked()

        self.owner.message("Getting XRF Spectra for area '%s'..." % aname)
        mca_thread = Thread(target=self._getmca_area, args=(aname,),
                            kwargs={'dtcorrect': dtcorrect})
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

    def onXRD(self, event=None, save=False, show=False):

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
            print('No map file and/or areas specified.')
            return

        xrmfile.reset_flags()
        if not xrmfile.flag_xrd1d and not xrmfile.flag_xrd2d:
            print('No XRD data in map file: %s' % self.owner.current_file.filename)
            return

        try:
            ponifile = bytes2str(xrmfile.xrmmap['xrd1D'].attrs['calfile'])
            ponifile = ponifile if os.path.exists(ponifile) else None
        except:
            ponifile = None

        if show:
            self.owner.message('Plotting XRD pattern for area \'%s\'...' % title)
        if save:
            self.owner.message('Saving XRD pattern for area \'%s\'...' % title)
            path,stem = os.path.split(self.owner.current_file.filename)
            stem = '%s_%s' % (stem,title)

        if xrmfile.flag_xrd1d:
            self._xrd  = None
            self._getxrd_area(aname,'1D') ## creates self._xrd group of type XRD
            self._xrd.filename = self.owner.current_file.filename
            self._xrd.title = title
            self._xrd.npixels = len(area.value[np.where(area.value)])
            self._xrd.energy = self.owner.current_energy
            self._xrd.wavelength = lambda_from_E(self._xrd.energy)

            if show:
                self.owner.display_1Dxrd(self._xrd.data1D,self._xrd.energy,
                                         label=self._xrd.title)
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

                print('Saving 1D XRD in file: %s' % (filename))
                save1D(filename, self._xrd.data1D[0], self._xrd.data1D[1], calfile=ponifile)

#             if not xrmfile.flag_xrd2d:
#                 datapath = xrmfile.xrmmap.attrs['Map_Folder']

        if xrmfile.flag_xrd2d:
            self._xrd  = None
            self._getxrd_area(aname,'2D') ## creates self._xrd group of type XRD
            self._xrd.filename = self.owner.current_file.filename
            self._xrd.title = title
            self._xrd.npixels = len(area.value[np.where(area.value)])
            self._xrd.energy = self.owner.current_energy
            self._xrd.wavelength = lambda_from_E(self.owner.current_energy)

            if save:
                wildcards = '2D XRD file (*.tiff)|*.tiff|All files (*.*)|*.*'
                dlg = wx.FileDialog(self, 'Save file as...',
                                   defaultDir=os.getcwd(),
                                   defaultFile='%s.tiff' % stem,
                                   wildcard=wildcards,
                                   style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
                if dlg.ShowModal() == wx.ID_OK:
                    filename = dlg.GetPath().replace('\\', '/')
                dlg.Destroy()
                print('Saving 2D XRD in file: %s' % (filename))
                self._xrd.save_2D(file=filename,verbose=True)

            if show:
                label = '%s: %s' % (os.path.split(self._xrd.filename)[-1], title)
                self.owner.display_2Dxrd(self._xrd.data2D, title=label, xrmfile=xrmfile,
                                         flip=True)

            if not xrmfile.flag_xrd1d:
                if ponifile is not None:
                    self._xrd.calfile = ponifile
                    self._xrd.steps = 5001
                    self._xrd.calc_1D(save=save,verbose=True)

                    if show:
                        self.owner.display_1Dxrd(self._xrd.data1D,self._xrd.energy,label=self._xrd.title)
                        
        self.owner.message('ready')



class MapViewerFrame(wx.Frame):
    cursor_menulabels = {'lasso': ('Select Points for XRF Spectra\tCtrl+X',
                                   'Left-Drag to select points for XRF Spectra')}

    def __init__(self, parent=None,  size=(825, 550),
                 use_scandb=False, _larch=None, **kwds):

        kwds['style'] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, parent, -1, size=size,  **kwds)

        self.data = None
        self.use_scandb = use_scandb
        self.filemap = {}
        self.im_displays = []
        self.plot_displays = []

        self.larch_buffer = parent
        if not isinstance(parent, LarchFrame):
            self.larch_buffer = LarchFrame(_larch=_larch)

        self.larch = self.larch_buffer._larch
        self.larch_buffer.Show()
        self.larch_buffer.Raise()

        self.xrfdisplay = None
        self.xrddisplay1D = None
        self.xrddisplay2D = None

        self.watch_files = False
        self.file_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onFileWatchTimer, self.file_timer)
        self.files_in_progress = []
        self.no_hotcols = True
        self.SetTitle('GSE XRM MapViewer')

        self.createMainPanel()

        self.SetFont(Font(10))

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

        self.scandb = None
        self.instdb = None
        self.inst_name = None
        self.move_callback = None

        self.larch_buffer.Hide()
        self.onFolderSelect()

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

        self.nb = flat_nb.FlatNotebook(parent, wx.ID_ANY, agwStyle=FNB_STYLE)
        self.nb.SetBackgroundColour('#FCFCFA')
        self.SetBackgroundColour('#F0F0E8')

        self.nbpanels = []

        for creator in (MapPanel, TomographyPanel, MapInfoPanel,
                        MapAreaPanel, MapMathPanel):

            p = creator(parent, owner=self)
            self.nb.AddPage(p, p.label, True)
            bgcol = p.GetBackgroundColour()
            self.nbpanels.append(p)
            p.SetSize((750, 550))

        self.larch_panel = None # LarchPanel(_larch=self.larch, parent=self.nb)
        # self.nb.AddPage(self.larch_panel, ' Larch Shell ', True)
        # self.nbpanels.append(self.larch_panel)

        self.nb.SetSelection(0)
        self.nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onNBChanged)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.title, 0, ALL_CEN)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)
        parent.SetSize((700, 400))
        pack(parent, sizer)

    def onNBChanged(self, event=None):
        idx = self.nb.GetSelection()
        # if self.nb.GetPage(idx) is self.larch_panel:
        #     self.larch_panel.update()

    def get_mca_area(self, mask, xoff=0, yoff=0, det=None, xrmfile=None):
        if xrmfile is None:
            xrmfile = self.current_file
        aname = xrmfile.add_area(mask)
        self.sel_mca = xrmfile.get_mca_area(aname,det=det)

    def lassoHandler(self, mask=None, xrmfile=None, xoff=0, yoff=0, det=None, **kws):
        ny, nx, npos = xrmfile.xrmmap['positions/pos'].shape
        if (xoff>0 or yoff>0) or mask.shape != (ny, nx):
            ym, xm = mask.shape
            tmask = np.zeros((ny, nx)).astype(bool)
            for iy in range(ym):
                tmask[iy+yoff, xoff:xoff+xm] = mask[iy]
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

            for p in self.nbpanels:
                if hasattr(p, 'update_xrmmap'):
                    p.update_xrmmap(self.current_file.xrmmap)

    def show_XRFDisplay(self, do_raise=True, clear=True, xrmfile=None):
        'make sure XRF plot frame is enabled and visible'
        if xrmfile is None:
            xrmfile = self.current_file
        if self.xrfdisplay is None:
            self.xrfdisplay = XRFDisplayFrame(_larch=self.larch)

        try:
            self.xrfdisplay.Show()

        except PyDeadObjectError:
            self.xrfdisplay = XRFDisplayFrame(_larch=self.larch)
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
        if len(name) < 1:
            return
        if xrmfile is None:
            xrmfile = self.current_file
        xrmmap  = xrmfile.xrmmap

        # first, create 1-pixel mask for area, and save that
        ny, nx, npos = xrmmap['positions/pos'].shape
        tmask = np.zeros((ny, nx)).astype(bool)
        tmask[int(iy), int(ix)] = True
        xrmfile.add_area(tmask, name=name)
        for p in self.nbpanels:
            if hasattr(p, 'update_xrmmap'):
                p.update_xrmmap(xrmmap)

        # next, save file into database
        if self.use_scandb and self.instdb is not None:
            pvn  = pv_fullname
            conf = xrmmap['config']
            pos_addrs = [pvn(tval) for tval in conf['positioners']]
            env_addrs = [pvn(tval) for tval in conf['environ/address']]
            env_vals  = [str(tval) for tval in conf['environ/value']]

            position = {}
            for p in pos_addrs:
                position[p] = None

            if x is None:
                x = float(xrmfile.get_pos(0, mean=True)[ix])
            if y is None:
                y = float(xrmfile.get_pos(1, mean=True)[iy])

            position[pvn(conf['scan/pos1'].value)] = x
            position[pvn(conf['scan/pos2'].value)] = y

            for addr, val in zip(env_addrs, env_vals):
                if addr in pos_addrs and position[addr] is None:
                    position[addr] = float(val)

            if title is None:
                title = '%s: %s' % (xrmfile.filename, name)

            notes = {'source': title}

            self.instdb.save_position(self.inst_name, name, position,
                                      notes=json.dumps(notes))


    def add_imdisplay(self, title, det=None, _cursorlabels=True, _savecallback=True):

        cursor_labels = self.cursor_menulabels if _cursorlabels else None
        lasso_cb = partial(self.lassoHandler, det=det) if _cursorlabels else None
        save_callback = self.onSavePixel if _savecallback else None

        imframe = MapImageFrame(output_title   = title,
                                lasso_callback = lasso_cb,
                                cursor_labels  = cursor_labels,
                                #move_callback  = self.move_callback,
                                save_callback  = save_callback)

        self.im_displays.append(imframe)

    def display_map(self, map, title='', info='', x=None, y=None, xoff=0, yoff=0,
                    det=None, subtitles=None, xrmfile=None,
                    _cursorlabels=True, _savecallback=True):
        """display a map in an available image display"""
        displayed = False

        cursor_labels = self.cursor_menulabels if _cursorlabels else None
        lasso_cb = partial(self.lassoHandler, det=det, xrmfile=xrmfile) if _cursorlabels else None
        save_callback = self.onSavePixel if _savecallback else None

        if x is not None:
            if self.no_hotcols and map.shape[1] != x.shape[0]:
                x = x[1:-1]

        while not displayed:
            try:
                imd = self.im_displays.pop()
                imd.display(map, title=title, x=x, y=y, xoff=xoff, yoff=yoff,
                            det=det, subtitles=subtitles, xrmfile=xrmfile)
                #for col, wid in imd.wid_subtitles.items():
                #    wid.SetLabel('%s: %s' % (col.title(), subtitles[col]))
                imd.lasso_callback = lasso_cb
                displayed = True
            except IndexError:
                imd = MapImageFrame(output_title=title,
                                    lasso_callback = lasso_cb,
                                    cursor_labels  = cursor_labels,
                                    #move_callback  = self.move_callback,
                                    save_callback  = save_callback)

                imd.display(map, title=title, x=x, y=y, xoff=xoff, yoff=yoff,
                            det=det, subtitles=subtitles, xrmfile=xrmfile)
                displayed = True
            except PyDeadObjectError:
                displayed = False
        self.im_displays.append(imd)
        imd.SetStatusText(info, 1)
        imd.Show()
        imd.Raise()

    def display_2Dxrd(self, map, title='image 0', xrmfile=None, flip=True):
        '''
        displays 2D XRD pattern in diFFit viewer
        '''
        flptyp = 'vertical' if flip is True else False
        poni = ''
        try:
            poni = bytes2str(self.current_file.xrmmap['xrd1D'].attrs['calfile'])
        except:
            pass
        if not os.path.exists(poni): poni = None

        if self.xrddisplay2D is None:
            self.xrddisplay2D = diFFit2DFrame(_larch=self.larch,flip=flptyp,
                                              xrd1Dviewer=self.xrddisplay1D,
                                              ponifile=poni)
        try:
            self.xrddisplay2D.plot2Dxrd(title,map)
        except PyDeadObjectError:
            self.xrddisplay2D = diFFit2DFrame(_larch=self.larch,flip=flptyp,
                                              xrd1Dviewer=self.xrddisplay1D)
            self.xrddisplay2D.plot2Dxrd(title,map)
        self.xrddisplay2D.Show()

    def display_1Dxrd(self, xy, energy, label='dataset 0', xrmfile=None):
        '''
        displays 1D XRD pattern in diFFit viewer
        '''
        data1dxrd = xrd1d(label=label,
                          energy=energy,
                          wavelength=lambda_from_E(energy))

        data1dxrd.xrd_from_2d(xy,'q')

        if self.xrddisplay1D is None:
            self.xrddisplay1D = diFFit1DFrame(_larch=self.larch)
        try:
            self.xrddisplay1D.xrd1Dviewer.add1Ddata(data1dxrd)
            self.xrddisplay1D.Show()
        except PyDeadObjectError:
            self.xrddisplay1D = diFFit1DFrame(_larch=self.larch)
            self.xrddisplay1D.xrd1Dviewer.add1Ddata(data1dxrd)
            self.xrddisplay1D.Show()

    def init_larch(self):
        self.SetStatusText('ready')
        self.datagroups = self.larch.symtable
        self.title.SetLabel('')
        fico = os.path.join(larch.site_config.larchdir, 'icons', XRF_ICON_FILE)
        try:
            self.SetIcon(wx.Icon(fico, wx.BITMAP_TYPE_ICO))
        except:
            pass

        if isGSECARS_Domain():
            self.move_callback = self.onMoveToPixel
            try:
                sys.path.insert(0, '//cars5/Data/xas_user/pylib')
                from escan_credentials import conn as DBCONN
                from larch_plugins.epics.scandb_plugin import connect_scandb
                DBCONN['_larch'] = self.larch
                connect_scandb(**DBCONN)
                self.scandb = self.larch.symtable._scan._scandb
                self.instdb = self.larch.symtable._scan._instdb
                self.inst_name = 'IDE_SampleStage'
                print(" Connected to scandb='%s' on server at '%s'" %
                      (DBCONN['dbname'], DBCONN['host']))
            except:
                etype, emsg, tb = sys.exc_info()
                print('Could not connect to ScanDB: %s' % (emsg.message))
                self.use_scandb = False

    def ShowFile(self, evt=None, filename=None,  **kws):
        if filename is None and evt is not None:
            filename = evt.GetString()

        if not self.h5convert_done or filename not in self.filemap:
            return
        if (self.check_ownership(filename) and
            self.filemap[filename].folder_has_newdata()):
            self.process_file(filename)


        self.current_file = self.filemap[filename]
        ny, nx, npos = self.filemap[filename].xrmmap['positions/pos'].shape
        self.title.SetLabel('%s: (%i x %i)' % (filename, nx, ny))

        fnames = self.filelist.GetItems()

        for p in self.nbpanels:
            if hasattr(p, 'update_xrmmap'):
                p.update_xrmmap(self.current_file.xrmmap)
            if hasattr(p, 'set_file_choices'):
                p.set_file_choices(fnames)

    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        MenuItem(self, fmenu, '&Open XRM Map File\tCtrl+O',
                 'Read XRM Map File',  self.onReadFile)
        MenuItem(self, fmenu, '&Open XRM Map Folder\tCtrl+F',
                 'Read XRM Map Folder',  self.onReadFolder)
        MenuItem(self, fmenu, 'Change &Working Folder',
                  'Choose working directory',
                  self.onFolderSelect)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, 'Show Larch Buffer\tCtrl+L',
                 'Show Larch Programming Buffer',
                 self.onShowLarchBuffer)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, 'Define new ROI',
                 'Define new ROI',  self.defineROI)
        MenuItem(self, fmenu, 'Load ROI File for 1DXRD',
                 'Load ROI File for 1DXRD',  self.add1DXRDFile)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, 'Load XRD calibration file',
                 'Load XRD calibration file',  self.openPONI)
        MenuItem(self, fmenu, 'Add 1DXRD for HDF5 file',
                 'Calculate 1DXRD for HDF5 file',  self.add1DXRD)
        fmenu.AppendSeparator()

        mid = wx.NewId()
        fmenu.Append(mid,  '&Watch HDF5 Files\tCtrl+W',  'Watch HDF5 Files', kind=wx.ITEM_CHECK)
        fmenu.Check(mid, False)
        self.Bind(wx.EVT_MENU, self.onWatchFiles, id=mid)

        MenuItem(self, fmenu, '&Quit\tCtrl+Q',
                  'Quit program', self.onClose)

        hmenu = wx.Menu()
        ID_ABOUT = wx.NewId()
        hmenu.Append(ID_ABOUT, '&About', 'About GSECARS MapViewer')
        self.Bind(wx.EVT_MENU, self.onAbout, id=ID_ABOUT)

        self.menubar.Append(fmenu, '&File')
        self.menubar.Append(hmenu, '&Help')
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)

    def onShowLarchBuffer(self, evt=None):
        if self.larch_buffer is None:
            self.larch_buffer = LarchFrame(_larch=self.larch)

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
        for disp in self.im_displays + self.plot_displays:
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
                            #style=wx.FD_OPEN)
        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            paths = [p.replace('\\', '/') for p in dlg.GetPaths()]
        dlg.Destroy()

        if read:
            for path in paths:
                read2 = read
                if path in self.filemap:
                    read2 = (wx.ID_YES == Popup(self, "Re-read file '%s'?" % path,
                                                   'Re-read file?', style=wx.YES_NO))
                if read2:
                    xrmfile = GSEXRM_MapFile(filename=str(path))
                    self.add_xrmfile(xrmfile)


#             path = dlg.GetPath().replace('\\', '/')
#             if path in self.filemap:
#                 read = (wx.ID_YES == Popup(self, "Re-read file '%s'?" % path,
#                                            'Re-read file?', style=wx.YES_NO))
#
#         dlg.Destroy()
#
#         if read:
#             xrmfile = GSEXRM_MapFile(filename=str(path))
#             self.add_xrmfile(xrmfile)

    def onReadFolder(self, evt=None):
        if not self.h5convert_done:
            print( 'cannot open file while processing a map folder')
            return

        myDlg = OpenMapFolder()

        path, read = None, False
        if myDlg.ShowModal() == wx.ID_OK:
            read        = True

            flipchoice = False if myDlg.PoniInfo[0].GetSelection() == 1 else True
            args = {'folder':           myDlg.Fldr.GetValue(),
                    'FLAGxrf':          myDlg.ChkBx[0].GetValue(),
                    'FLAGxrd2D':        myDlg.ChkBx[1].GetValue(),
                    'FLAGxrd1D':        myDlg.ChkBx[2].GetValue(),
                    'poni':             myDlg.PoniInfo[1].GetValue(),
                    'azwdgs':           myDlg.PoniInfo[6].GetValue(),
                    'qstps':            myDlg.PoniInfo[4].GetValue(),
                    'flip':             flipchoice,
                    'facility':         myDlg.info[0].GetValue(),
                    'beamline':         myDlg.info[1].GetValue(),
                    'date':             myDlg.info[2].GetValue(),
                    'run':              myDlg.info[3].GetValue(),
                    'proposal':         myDlg.info[4].GetValue(),
                    'user':             myDlg.info[5].GetValue(),
                    'compression':      myDlg.H5cmprInfo[0].GetStringSelection(),
                    'compression_opts': myDlg.H5cmprInfo[1].GetSelection()}
        myDlg.Destroy()

        if read:
            xrmfile = GSEXRM_MapFile(**args)
            self.add_xrmfile(xrmfile)

    def add_xrmfile(self, xrmfile):
        gname = 'map001'
        count, maxcount = 1, 999
        while hasattr(self.datagroups, gname) and count < maxcount:
            count += 1
            gname = 'map%3.3i' % count
        setattr(self.datagroups, gname, xrmfile)

        parent, fname = os.path.split(xrmfile.filename)

        if fname not in self.filemap:
            self.filemap[fname] = xrmfile
        if fname not in self.filelist.GetItems():
            self.filelist.Append(fname)
        if self.check_ownership(fname):
            self.process_file(fname)
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

        myDlg = OpenPoniFile()
        read = False
        if myDlg.ShowModal() == wx.ID_OK:
            read = True
            path = myDlg.PoniInfo[1].GetValue()
            flip = False if myDlg.PoniInfo[0].GetSelection() == 1 else True
        myDlg.Destroy()

        if read:
            self.current_file.add_calibration(path,flip)
            for p in self.nbpanels:
                if hasattr(p, 'update_xrmmap'):
                    p.update_xrmmap(self.current_file.xrmmap)

    def defineROI(self, event=None):
    
        if not self.h5convert_done:
            print( 'cannot open file while processing a map folder')
            return

        myDlg = ROIPopUp(self)

        path, read = None, False
        if myDlg.ShowModal() == wx.ID_OK:
            read        = True
        myDlg.Destroy()

        if read:
            for p in self.nbpanels:
                if hasattr(p, 'update_xrmmap'):
                    p.update_xrmmap(self.current_file.xrmmap)

    def add1DXRDFile(self, event=None):

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
            self.current_file.read_xrd1D_ROIFile(path,verbose=True)

    def add1DXRD(self, event=None):

        try:
            xrd1Dgrp = ensure_subgroup('xrd1D',self.current_file.xrmmap)
            path = xrd1Dgrp.attrs['calfile']
        except:
            self.openPONI()

        if os.path.exists(xrd1Dgrp.attrs['calfile']):
            self.current_file.add_1DXRD()

    def onWatchFiles(self, event=None):
        self.watch_files = event.IsChecked()
        if not self.watch_files:
            self.file_timer.Stop()
            self.message('Watching Files/Folders for Changes: Off')
        else:
            self.file_timer.Start(10000)
            self.message('Watching Files/Folders for Changes: On')


    def onFileWatchTimer(self, event=None):
        for filename in self.filemap:
            if (filename not in self.files_in_progress and
                self.filemap[filename].folder_has_newdata()):
                self.process_file(filename)
                thispanel = self.nbpanels[self.nb.GetSelection()]
                thispanel.onShowMap(event=None, new=False)
                # print('Processed File ', thispanel)

    def process_file(self, filename):
        """Request processing of map file.
        This can take awhile, so is done in a separate thread,
        with updates displayed in message bar
        """
        xrm_map = self.filemap[filename]
        if xrm_map.status == GSEXRM_FileStatus.created:
            xrm_map.initialize_xrmmap()

        if xrm_map.dimension is None and isGSEXRM_MapFolder(self.folder):
            xrm_map.read_master()

        if self.filemap[filename].folder_has_newdata():
            self.files_in_progress.append(filename)
            self.h5convert_fname = filename
            self.h5convert_done = False
            self.h5convert_irow, self.h5convert_nrow = 0, 0
            self.h5convert_t0 = time.time()
            self.htimer.Start(150)
            ##self.h5convert_thread = Thread(target=self.filemap[filename].process)
            self.h5convert_thread = Thread(target=self.new_mapdata,
                                           args=(filename,))
            self.h5convert_thread.start()

    def onTimer(self,event=None):
        fname, irow, nrow = self.h5convert_fname, self.h5convert_irow, self.h5convert_nrow
        self.message('MapViewer Timer Processing %s:  row %i of %i' % (fname, irow, nrow))
        if self.h5convert_done:
            self.htimer.Stop()
            self.h5convert_thread.join()
            if fname in self.files_in_progress:
                self.files_in_progress.remove(fname)
            self.message('MapViewerTimer Processing %s: complete!' % fname)
            self.ShowFile(filename=self.h5convert_fname)

## This routine processes the data identically to 'process()' in xrmmap/xrm_mapfile.py .
## mkak 2016.09.07
    def new_mapdata(self, filename):
        xrm_map = self.filemap[filename]
        nrows = len(xrm_map.rowdata)
        xrm_map.reset_flags()
        self.h5convert_nrow = nrows
        self.h5convert_done = False
        if xrm_map.folder_has_newdata():
            irow = xrm_map.last_row + 1
            self.h5convert_irow = irow
            while irow < nrows:
                t0 = time.time()
                self.h5convert_irow = irow
                rowdat = xrm_map.read_rowdata(irow)
                if rowdat.read_ok:
                    t1 = time.time()
                    xrm_map.add_rowdata(rowdat)
                    t2 = time.time()
                    irow  = irow + 1
                else:
                    break
                try:
                    wx.Yield()
                except:
                    pass

        xrm_map.resize_arrays(xrm_map.last_row+1)
        xrm_map.h5root.flush()
        self.h5convert_done = True
        time.sleep(0.025)

        print(datetime.datetime.fromtimestamp(time.time()).strftime('End: %Y-%m-%d %H:%M:%S'))

#        ## Create 'full area' mask with edges trimmed
#        mask = np.ones((201,201))
#        mask[0:3,] = mask[-4:-1,] = mask[:,0:3] = mask[:,-4:-1] = 0
#        xrm_map.add_area(mask, name='full-area', desc='full-area')

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
                self.filemap[fname].claim_hostid()
        return self.filemap[fname].check_hostid()

class OpenPoniFile(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):

        """Constructor"""
        dialog = wx.Dialog.__init__(self, None, title='XRD Calibration File', size=(350, 280))

        panel = wx.Panel(self)

        ################################################################################
        poni_chc = ['Dioptas calibration file:','pyFAI calibration file:']
        poni_spn = wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP
        self.PoniInfo = [ Choice(panel,      choices=poni_chc ),
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

        self.gp = GridPanel(panel, nrows=8, ncols=4, **kws)

        self.roi_name =  wx.TextCtrl(self, -1, 'ROI_001',  size=(120, -1))
        self.roi_chc  = [Choice(self, choices=[''],        size=(120, -1)),
                         Choice(self, choices=[''],        size=(120, -1))]
        fopts = dict(minval=-1, precision=3, size=(100, -1))
        self.roi_lims = [FloatCtrl(self, value=0,  **fopts),
                         FloatCtrl(self, value=-1, **fopts),
                         FloatCtrl(self, value=0,  **fopts),
                         FloatCtrl(self, value=-1, **fopts)]

        self.gp.Add(SimpleText(self, '--    Add new ROI definitions    --'), dcol=4, style=CEN, newrow=True)

#         self.gp.AddMany((SimpleText(self, 'Name:'),self.roi_name,Button(self, 'Add ROI', size=(100, -1), action=self.onCreateROI)), dcol=1, style=LEFT, newrow=True)
        self.gp.AddMany((SimpleText(self, 'Name:'),self.roi_name), dcol=1, style=LEFT, newrow=True)
        self.gp.AddMany((SimpleText(self, 'Type:'),self.roi_chc[0]), dcol=1, style=LEFT,newrow=True)
        self.gp.AddMany((SimpleText(self, 'Limits:'),self.roi_lims[0],self.roi_lims[1],self.roi_chc[1]), dcol=1, style=LEFT, newrow=True)
        self.gp.AddMany((SimpleText(self, ''),self.roi_lims[2],self.roi_lims[3]), dcol=1, style=LEFT, newrow=True)
        self.gp.AddMany((SimpleText(self, ''),Button(self, 'Add ROI', size=(100, -1), action=self.onCreateROI)), dcol=1, style=LEFT, newrow=True)
        self.gp.Add(SimpleText(self, ''),newrow=True)


        ###############################################################################

        self.rm_roi_ch = [Choice(self, choices=[''],        size=(120, -1)),
                          Choice(self, choices=[''],        size=(120, -1))]
        fopts = dict(minval=-1, precision=3, size=(100, -1))
        self.rm_roi_lims = SimpleText(self, '')

        self.gp.Add(SimpleText(self, ''),newrow=True)
        self.gp.Add(SimpleText(self, '--    Delete saved ROI    --'), dcol=4, style=CEN, newrow=True)

        self.gp.AddMany((SimpleText(self, 'Detector:'),self.rm_roi_ch[0]), dcol=1, style=LEFT, newrow=True)
        self.gp.AddMany((SimpleText(self, 'ROI:'),self.rm_roi_ch[1]), dcol=1, style=LEFT,newrow=True)
        self.gp.Add(SimpleText(self, 'Limits:'), dcol=1, style=LEFT, newrow=True)
        self.gp.Add(self.rm_roi_lims, dcol=3, style=LEFT)
        self.gp.AddMany((SimpleText(self, ''),Button(self, 'Remove ROI', size=(100, -1), action=self.onRemoveROI)), dcol=1, style=LEFT, newrow=True)
        self.gp.Add(SimpleText(self, ''),newrow=True)
#         self.gp.Add(SimpleText(self, ''),newrow=True)
        self.gp.AddMany((SimpleText(self, ''),SimpleText(self, ''),SimpleText(self, ''),wx.Button(self, wx.ID_OK, label='Close window')), dcol=1, style=LEFT, newrow=True)

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
        if self.cfile.flag_xrf:
            roitype += ['XRF']
        if self.cfile.flag_xrd1d:
            roitype += ['1DXRD']
            delroi  = ['xrd1D']
        if self.cfile.flag_xrd2d:
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

        if detname == 'xrd1D':
            self.cfile.del_xrd1Droi(roiname)
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
        units = roi['limits'].attrs['units']

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

        self.owner.message('Calculating ROI: %s' % xname)
        if xtyp == 'XRF':
            self.cfile.add_xrfroi(xrange,xname,unit=xunt)
        elif xtyp == '1DXRD':
            xrd = ['q','2th','d']
            unt = xrd[self.roi_chc[1].GetSelection()]
            self.cfile.add_xrd1Droi(xrange,xname,unit=unt)
        elif xtyp == '2DXRD':
            self.cfile.add_xrd2Droi(xrange,xname,unit=xunt)
        self.owner.message('Ready')
##################


class OpenMapFolder(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):

        """Constructor"""
        dialog = wx.Dialog.__init__(self, None, title='XRM Map Folder', size=(350, 620))

        panel = wx.Panel(self)

        ################################################################################
        fldrTtl   = SimpleText(panel,  label='XRM Map Folder:' )
        self.Fldr = wx.TextCtrl(panel, size=(320, 25)          )
        fldrBtn   = Button(panel,      label='Browse...'       )

        self.Bind(wx.EVT_BUTTON, self.onBROWSE, fldrBtn)

        fldrsizer = wx.BoxSizer(wx.VERTICAL)
        fldrsizer.Add(fldrTtl,      flag=wx.TOP|wx.LEFT,           border=5)
        fldrsizer.Add(self.Fldr,    flag=wx.EXPAND|wx.TOP|wx.LEFT, border=5)
        fldrsizer.Add(fldrBtn,      flag=wx.TOP|wx.LEFT,           border=5)
        ################################################################################
        ChkTtl        = SimpleText(panel,  label='Build map including data:' )
        self.ChkBx = [ Check(panel, label='XRF'   ),
                       Check(panel, label='2DXRD' ),
                       Check(panel, label='1DXRD (requires calibration file)' )]

        for chkbx in self.ChkBx: chkbx.Bind(wx.EVT_CHECKBOX, self.checkOK)

        ckbxsizer1 = wx.BoxSizer(wx.VERTICAL)
        ckbxsizer1.Add(self.ChkBx[1], flag=wx.BOTTOM|wx.LEFT, border=5)
        ckbxsizer1.Add(self.ChkBx[2], flag=wx.BOTTOM|wx.LEFT, border=5)

        ckbxsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        ckbxsizer2.Add(self.ChkBx[0],  flag=wx.RIGHT, border=15)
        ckbxsizer2.Add(ckbxsizer1, flag=wx.RIGHT, border=15)

        ckbxsizer = wx.BoxSizer(wx.VERTICAL)
        ckbxsizer.Add(ChkTtl, flag=wx.BOTTOM|wx.LEFT, border=5)
        ckbxsizer.Add(ckbxsizer2, flag=wx.BOTTOM|wx.LEFT, border=5)
        ################################################################################
        infoTtl =  [ SimpleText(panel,  label='Facility'),
                     SimpleText(panel,  label='Beamline'),
                     SimpleText(panel,  label='Date'),
                     SimpleText(panel,  label='Run cycle'),
                     SimpleText(panel,  label='Proposal number'),
                     SimpleText(panel,  label='User group')]
        self.info = [ wx.TextCtrl(panel, size=(100, 25) ),
                      wx.TextCtrl(panel, size=(100, 25) ),
                      wx.TextCtrl(panel, size=(100, 25) ),
                      wx.TextCtrl(panel, size=(100, 25) ),
                      wx.TextCtrl(panel, size=(250, 25) ),
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

        infosizer3 = wx.BoxSizer(wx.HORIZONTAL)
        infosizer3.Add(infoTtl[5],   flag=wx.RIGHT, border=5)
        infosizer3.Add(self.info[5], flag=wx.RIGHT, border=15)

        infosizer = wx.BoxSizer(wx.VERTICAL)
        infosizer.Add(infosizer0, flag=wx.TOP,            border=15)
        infosizer.Add(infosizer1, flag=wx.TOP,            border=5)
        infosizer.Add(infosizer2, flag=wx.TOP|wx.BOTTOM,  border=5)
        infosizer.Add(infosizer3, flag=wx.BOTTOM,         border=15)
        ################################################################################
        poni_chc = ['Dioptas calibration file:','pyFAI calibration file:']
        poni_spn = wx.SP_VERTICAL|wx.SP_ARROW_KEYS|wx.SP_WRAP
        self.PoniInfo = [ Choice(panel,      choices=poni_chc ),
                          wx.TextCtrl(panel, size=(320, 25)),
                          Button(panel,      label='Browse...'),
                          SimpleText(panel,  label='Steps:'),
                          wx.TextCtrl(panel, size=(80,  25)),
                          SimpleText(panel,  label='Wedges:'),
                          wx.SpinCtrl(panel, style=poni_spn, size=(100,  -1))]

        self.PoniInfo[2].Bind(wx.EVT_BUTTON, self.onBROWSEponi)

        ponisizer1 = wx.BoxSizer(wx.HORIZONTAL)
        ponisizer1.Add(self.PoniInfo[3], flag=wx.RIGHT, border=5)
        ponisizer1.Add(self.PoniInfo[4], flag=wx.RIGHT, border=5)
        ponisizer1.Add(self.PoniInfo[5], flag=wx.RIGHT, border=5)
        ponisizer1.Add(self.PoniInfo[6], flag=wx.RIGHT, border=5)

        ponisizer = wx.BoxSizer(wx.VERTICAL)
        ponisizer.Add(self.PoniInfo[0], flag=wx.TOP,            border=15)
        ponisizer.Add(self.PoniInfo[1], flag=wx.TOP,            border=5)
        ponisizer.Add(self.PoniInfo[2], flag=wx.TOP|wx.BOTTOM,  border=5)
        ponisizer.Add(ponisizer1,       flag=wx.BOTTOM,         border=15)
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
        h5cmprsizer.Add(h5txt, flag=wx.RIGHT, border=5)
        h5cmprsizer.Add(self.H5cmprInfo[0], flag=wx.RIGHT, border=5)
        h5cmprsizer.Add(self.H5cmprInfo[1], flag=wx.RIGHT, border=5)
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
        sizer.Add(fldrsizer, flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add((-1, 15))
        sizer.Add(ckbxsizer, flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add((-1, 8))
        sizer.Add(infosizer, flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add((-1, 8))
        sizer.Add(ponisizer, flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add((-1, 8))
        sizer.Add(h5cmprsizer, flag=wx.TOP|wx.LEFT, border=5)
        sizer.Add((-1, 25))
        sizer.Add(minisizer, flag=wx.ALIGN_RIGHT, border=5)

        panel.SetSizer(sizer)
        ################################################################################

        ## Set defaults
        self.ChkBx[0].SetValue(True)
        self.ChkBx[1].SetValue(False)
        self.ChkBx[2].SetValue(False)

        self.PoniInfo[0].SetSelection(0)

        self.PoniInfo[4].SetValue('5001')
        self.PoniInfo[6].SetValue(1)
        self.PoniInfo[6].SetRange(0,36)

        self.FindWindowById(wx.ID_OK).Disable()

        for poniinfo in self.PoniInfo: poniinfo.Disable()

        self.info[0].SetValue(FACILITY)
        self.info[1].SetValue(BEAMLINE)
        self.info[2].SetValue(datetime.date.today().isoformat())

    def checkOK(self,event=None):

        if self.ChkBx[2].GetValue():
            for poniinfo in self.PoniInfo: poniinfo.Enable()
        else:
            for poniinfo in self.PoniInfo: poniinfo.Disable()

        if os.path.exists(self.Fldr.GetValue()):
            self.FindWindowById(wx.ID_OK).Enable()
        else:
            self.Fldr.SetValue('')
            self.FindWindowById(wx.ID_OK).Disable()

    def onH5cmpr(self,event=None):

        if self.H5cmprInfo[0].GetSelection() == 0:
            self.H5cmprInfo[1].Enable()
            self.H5cmprInfo[1].SetChoices(['%i' % i for i in np.arange(10)])
            self.H5cmprInfo[1].SetSelection(2)
        else:
            self.H5cmprInfo[1].Disable()
            self.H5cmprInfo[1].SetChoices([''])

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

    def onBROWSE(self,event=None):

        if os.path.exists(self.Fldr.GetValue()):
           dfltDIR = self.Fldr.GetValue()
        else:
           dfltDIR = os.getcwd()

        dlg = wx.DirDialog(self, message='Read XRM Map Folder',
                           defaultPath=dfltDIR,
                           style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()

        if read:
            self.Fldr.Clear()
            self.Fldr.SetValue(str(path))

            for line in open(os.path.join(path, 'Scan.ini'), 'r'):
                if line.split()[0] == 'basedir':
                    path = line.split()[-1].split('/')
                    cycle,usr = path[-2],path[-1]
                    self.info[3].SetValue(cycle)
                    self.info[5].SetValue(usr)

        self.checkOK()


class MapViewer(wx.App):
    def __init__(self, use_scandb=False, **kws):
        self.use_scandb = use_scandb
        wx.App.__init__(self, **kws)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = MapViewerFrame(use_scandb=self.use_scandb)
        frame.Show()
        self.SetTopWindow(frame)

    def OnInit(self):
        self.createApp()
        return True

class DebugViewer(MapViewer, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, **kws):
        MapViewer.__init__(self, **kws)

    def OnInit(self):
        self.Init()
        self.createApp()
        self.ShowInspectionTool()
        return True

def initializeLarchPlugin(_larch=None):
    """add MapFrameViewer to _sys.gui_apps """
    if _larch is not None:
        _sys = _larch.symtable._sys
        if not hasattr(_sys, 'gui_apps'):
            _sys.gui_apps = {}
        _sys.gui_apps['mapviewer'] = ('XRF Map Viewer', MapViewerFrame)

def registerLarchPlugin():
    return ('_sys.wx', {})

if __name__ == '__main__':
    DebugViewer().run()
