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
import glob
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

import h5py
import numpy as np
import scipy.stats as stats
from scipy import constants

from matplotlib.widgets import Slider, Button, RadioButtons

HAS_pyFAI = False
try:
    import pyFAI
    import pyFAI.calibrant
    from pyFAI.calibration import Calibration
    HAS_pyFAI = True
except ImportError:
    pass

from wxmplot import PlotFrame

from wxutils import (SimpleText, EditableListBox, FloatCtrl, Font,
                     pack, Popup, Button, MenuItem, Choice, Check,
                     GridPanel, FileSave, HLine)

import larch
from larch.larchlib import read_workdir, save_workdir
from larch.wxlib import larchframe

from larch_plugins.wx.xrfdisplay import XRFDisplayFrame
from larch_plugins.wx.xrddisplay import XRD1D_DisplayFrame,XRD2D_DisplayFrame

from larch_plugins.wx.mapimageframe import MapImageFrame

from larch_plugins.io import nativepath, tifffile
from larch_plugins.epics import pv_fullname
from larch_plugins.xrmmap import (GSEXRM_MapFile, GSEXRM_FileStatus,
                                  GSEXRM_Exception, GSEXRM_NotOwner)

from larch_plugins.xrd import integrate_xrd,calculate_ai

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

DETCHOICES = ['sum', '1', '2', '3', '4']
FRAMESTYLE = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL

def isGSECARS_Domain():
    return 'cars.aps.anl.gov' in socket.getfqdn().lower()

DBCONN = None



class MapMathPanel(scrolled.ScrolledPanel):
    """Panel of Controls for doing math on arrays from Map data"""
    label  = 'Map Math'
    def __init__(self, parent, owner, **kws):
        scrolled.ScrolledPanel.__init__(self, parent, -1,
                                        style=wx.GROW|wx.TAB_TRAVERSAL, **kws)
        self.owner = owner
        sizer = wx.GridBagSizer(8, 9)
        self.show_new = Button(self, 'Show New Map',     size=(125, -1),
                                   action=partial(self.onShowMap, new=True))
        self.show_old = Button(self, 'Replace Last Map', size=(125, -1),
                                   action=partial(self.onShowMap, new=False))

        self.map_mode = Choice(self, choices= ['Intensity', 'R, G, B'],
                                   size=(150, -1), action=self.onMode)

        self.expr_i = wx.TextCtrl(self, -1,   '', size=(150, -1))
        self.expr_r = wx.TextCtrl(self, -1,   '', size=(150, -1))
        self.expr_g = wx.TextCtrl(self, -1,   '', size=(150, -1))
        self.expr_b = wx.TextCtrl(self, -1,   '', size=(150, -1))

        ir = 0
        sizer.Add(SimpleText(self, 'Map Mode:'),    (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.map_mode,                    (ir, 1), (1, 1), ALL_LEFT, 2)
        txt = """Enter Math Expressions for Map:
 a+b,  (a-b)/c, log10(a+0.1),  etc"""

        sizer.Add(SimpleText(self, txt),    (ir, 2), (2, 4), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Intensity:'),    (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.expr_i,  (ir, 1), (1, 1), ALL_LEFT, 2)
        ir += 1
        sizer.Add(SimpleText(self, 'R, G, B:'),    (ir, 0), (1, 1), ALL_CEN, 2)

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.expr_r,  0, ALL_LEFT, 2)
        box.Add(self.expr_g,  0, ALL_LEFT, 2)
        box.Add(self.expr_b,  0, ALL_LEFT, 2)
        sizer.Add(box,  (ir, 1), (1, 5), ALL_LEFT, 2)

        ir += 1
        sizer.Add(self.show_new,  (ir, 0), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.show_old,  (ir, 2), (1, 2), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Name'),    (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'File'),        (ir, 1), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'ROI'),         (ir, 2), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Detector'),    (ir, 3), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'DT Correct?'), (ir, 4), (1, 1), ALL_CEN, 2)

        self.varfile  = {}
        self.varroi   = {}
        self.varshape   = {}
        self.varrange   = {}
        self.vardet   = {}
        self.varcor   = {}
        for varname in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'):
            self.varfile[varname]   = vfile  = Choice(self, choices=[], size=(200, -1),
                                                          action=partial(self.onROI, varname=varname))
            self.varroi[varname]    = vroi   = Choice(self, choices=[], size=(120, -1),
                                                          action=partial(self.onROI, varname=varname))
            self.vardet[varname]    = vdet   = Choice(self, choices=DETCHOICES,
                                                      size=(90, -1))
            self.varcor[varname]    = vcor   = wx.CheckBox(self, -1, ' ')
            self.varshape[varname]  = vshape = SimpleText(self, 'Array Shape = (, )',
                                                          size=(200, -1))
            self.varrange[varname]  = vrange = SimpleText(self, 'Range = [   :    ]',
                                                          size=(200, -1))
            vcor.SetValue(1)
            vdet.SetSelection(0)

            ir += 1
            sizer.Add(SimpleText(self, '%s = ' % varname),    (ir, 0), (1, 1), ALL_CEN, 2)
            sizer.Add(vfile,                        (ir, 1), (1, 1), ALL_CEN, 2)
            sizer.Add(vroi,                         (ir, 2), (1, 1), ALL_CEN, 2)
            sizer.Add(vdet,                         (ir, 3), (1, 1), ALL_CEN, 2)
            sizer.Add(vcor,                         (ir, 4), (1, 1), ALL_CEN, 2)
            ir +=1
            sizer.Add(vshape,                       (ir, 1), (1, 1), ALL_LEFT, 2)
            sizer.Add(vrange,                       (ir, 2), (1, 3), ALL_LEFT, 2)

        pack(self, sizer)
        self.SetupScrolling()
        self.onMode(evt=None, choice='int')

    def onMode(self, evt=None, choice=None):
        mode = self.map_mode.GetStringSelection()
        if choice is not None:
            mode = choice
        mode = mode.lower()
        self.expr_i.Disable()
        self.expr_r.Disable()
        self.expr_g.Disable()
        self.expr_b.Disable()
        if mode.startswith('i'):
            self.expr_i.Enable()
        else:
            self.expr_r.Enable()
            self.expr_g.Enable()
            self.expr_b.Enable()

    def onROI(self, evt, varname='a'):
        fname   = self.varfile[varname].GetStringSelection()
        roiname = self.varroi[varname].GetStringSelection()
        dname   = self.vardet[varname].GetStringSelection()
        dtcorr  = self.varcor[varname].IsChecked()
        det =  None
        if dname != 'sum':  det = int(dname)
        map = self.owner.filemap[fname].get_roimap(roiname, det=det, dtcorrect=dtcorr)
        self.varshape[varname].SetLabel('Array Shape = %s' % repr(map.shape))
        self.varrange[varname].SetLabel('Range = [%g: %g]' % (map.min(), map.max()))

    def update_xrmmap(self, xrmmap):
        self.set_roi_choices(xrmmap)

    def set_roi_choices(self, xrmmap):
        rois = ['1'] + list(xrmmap['roimap/sum_name'])
        for wid in self.varroi.values():
            wid.SetChoices(rois)

    def set_file_choices(self, fnames):
        for wid in self.varfile.values():
            wid.SetChoices(fnames)

    def onShowMap(self, event=None, new=True):
        mode = self.map_mode.GetStringSelection()
        def get_expr(wid):
            val = str(wid.Value)
            if len(val) == 0:
                val = '1'
            return val
        expr_i = get_expr(self.expr_i)
        expr_r = get_expr(self.expr_r)
        expr_g = get_expr(self.expr_g)
        expr_b = get_expr(self.expr_b)


        main_file = None
        _larch = self.owner.larch

        for varname in self.varfile.keys():
            fname   = self.varfile[varname].GetStringSelection()
            roiname = self.varroi[varname].GetStringSelection()
            dname   = self.vardet[varname].GetStringSelection()
            dtcorr  = self.varcor[varname].IsChecked()
            det =  None
            if dname != 'sum':  det = int(dname)
            if roiname == '1':
                map = 1
            else:
                map = self.owner.filemap[fname].get_roimap(roiname, det=det, dtcorrect=dtcorr)

            _larch.symtable.set_symbol(str(varname), map)
            if main_file is None:
                main_file = self.owner.filemap[fname]
        if mode.startswith('I'):
            map = _larch.eval(expr_i)
            info  = 'Intensity: [%g, %g]' %(map.min(), map.max())
            title = '%s: %s' % (fname, expr_i)
            subtitles = None
        else:
            rmap = _larch.eval(expr_r)
            gmap = _larch.eval(expr_g)
            bmap = _larch.eval(expr_b)
            map = np.array([rmap, gmap, bmap])
            map = map.swapaxes(0, 2).swapaxes(0, 1)
            title = '%s: (R, G, B) = (%s, %s, %s)' % (fname, expr_r, expr_g, expr_b)
            subtitles = {'red': expr_r, 'blue': expr_b, 'green': expr_g}
            info = ''
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
            iframe = self.owner.add_imdisplay(title, det=None)

        self.owner.display_map(map, title=title, subtitles=subtitles,
                               info=info, x=x, y=y,
                               det=None, xrmfile=main_file)

class SimpleMapPanel(GridPanel):
    """Panel of Controls for choosing what to display a simple ROI map"""
    label  = 'Simple XRF ROI Map'
    def __init__(self, parent, owner, **kws):
        self.owner = owner

        GridPanel.__init__(self, parent, nrows=8, ncols=5, **kws)

        self.roi1 = Choice(self, choices=[], size=(120, -1))
        self.roi2 = Choice(self, choices=[], size=(120, -1))
        self.op   = Choice(self, choices=['/', '*', '-', '+'], size=(80, -1))
        self.det  = Choice(self, choices=DETCHOICES, size=(90, -1))
        self.cor  = Check(self, label='Correct Deadtime?')
        self.hotcols  = Check(self, label='Ignore First/Last Columns?')

        self.show_new = Button(self, 'Show New Map',     size=(125, -1),
                               action=partial(self.onShowMap, new=True))
        self.show_old = Button(self, 'Replace Last Map', size=(125, -1),
                               action=partial(self.onShowMap, new=False))
        self.show_cor = Button(self, 'Map1 vs. Map2', size=(125, -1),
                               action=self.onShowCorrel)

        self.AddManyText(('Detector', 'Map 1', 'Operator', 'Map 2'))
        self.AddMany((self.det, self.roi1, self.op, self.roi2), newrow=True)

        self.Add(self.cor,       dcol=2, newrow=True, style=LEFT)
        self.Add(self.hotcols,   dcol=2, style=LEFT)
        self.Add(self.show_new,  dcol=2, newrow=True, style=LEFT)
        self.Add(self.show_old,  dcol=2,              style=LEFT)
        self.Add(self.show_cor,  dcol=2, newrow=True, style=LEFT)

        fopts = dict(minval=-20000, precision=0, size=(70, -1))
        self.lims = [FloatCtrl(self, value= 0, **fopts),
                     FloatCtrl(self, value=-1, **fopts),
                     FloatCtrl(self, value= 0, **fopts),
                     FloatCtrl(self, value=-1, **fopts)]

        for wid in self.lims: wid.Disable()

        self.limrange  = Check(self, default=False,
                               label=' Limit Map Range to Pixel Range:',
                               action=self.onLimitRange)
        self.Add(HLine(self, size=(350, 3)), dcol=4, newrow=True, style=CEN)
        self.Add(self.limrange, dcol=4,   newrow=True, style=LEFT)
        self.Add(SimpleText(self, 'X Range:'), dcol=1,
                 newrow=True, style=LEFT)
        self.Add(self.lims[0], dcol=1, style=LEFT)
        self.Add(SimpleText(self, ':'), dcol=1, style=LEFT)
        self.Add(self.lims[1], dcol=1, style=LEFT)
        self.Add(SimpleText(self, 'Y Range:'), dcol=1,
                 newrow=True, style=LEFT)
        self.Add(self.lims[2], dcol=1, style=LEFT)
        self.Add(SimpleText(self, ':'), dcol=1, style=LEFT)
        self.Add(self.lims[3], dcol=1, style=LEFT)

        self.pack()

    def onLimitRange(self, event=None):
        if self.limrange.IsChecked():
            for wid in self.lims:
                wid.Enable()
        else:
            for wid in self.lims:
                wid.Disable()

    def onClose(self):
        for p in self.plotframes:
            try:
                p.Destroy()
            except:
                pass

    def onLasso(self, selected=None, mask=None, data=None, xrmfile=None, **kws):
        if xrmfile is None:
            xrmfile = self.owner.current_file
        ny, nx, npos = xrmfile.xrmmap['positions/pos'].shape
        indices = []
        for idx in selected:
            iy, ix = divmod(idx, ny)
            indices.append((ix, iy))

    def onShowCorrel(self, event=None):
        roiname1 = self.roi1.GetStringSelection()
        roiname2 = self.roi2.GetStringSelection()
        if roiname1 in ('', '1') or roiname2 in ('', '1'):
            return

        datafile  = self.owner.current_file
        det =self.det.GetStringSelection()
        if det == 'sum':
            det =  None
        else:
            det = int(det)
        dtcorrect = self.cor.IsChecked()
        no_hotcols = self.hotcols.IsChecked()
        self.owner.no_hotcols = no_hotcols
        map1 = datafile.get_roimap(roiname1, det=det, no_hotcols=no_hotcols,
                                   dtcorrect=dtcorrect)
        map2 = datafile.get_roimap(roiname2, det=det, no_hotcols=no_hotcols,
                                   dtcorrect=dtcorrect)

        if self.limrange.IsChecked():
            lims = [wid.GetValue() for wid in self.lims]
            map1 = map1[lims[2]:lims[3], lims[0]:lims[1]]
            map2 = map2[lims[2]:lims[3], lims[0]:lims[1]]

        path, fname = os.path.split(datafile.filename)
        title ='%s: %s vs %s' %(fname, roiname2, roiname1)
        pframe = PlotFrame(title=title, output_title=title)
        pframe.plot(map2.flatten(), map1.flatten(),
                    xlabel=roiname2, ylabel=roiname1,
                    marker='o', markersize=4, linewidth=0)
        pframe.panel.cursor_mode = 'lasso'
        pframe.panel.lasso_callback = partial(self.onLasso, xrmfile=datafile)

        pframe.Show()
        pframe.Raise()
        self.owner.plot_displays.append(pframe)

    def onShowMap(self, event=None, new=True):
        datafile  = self.owner.current_file
        det =self.det.GetStringSelection()
        if det == 'sum':
            det =  None
        else:
            det = int(det)

        dtcorrect = self.cor.IsChecked()
        no_hotcols  = self.hotcols.IsChecked()
        self.owner.no_hotcols = no_hotcols
        roiname1 = self.roi1.GetStringSelection()
        roiname2 = self.roi2.GetStringSelection()
        map      = datafile.get_roimap(roiname1, det=det, no_hotcols=no_hotcols,
                                       dtcorrect=dtcorrect)
        title    = roiname1

        if roiname2 != '1':
            mapx =datafile.get_roimap(roiname2, det=det, no_hotcols=no_hotcols,
                                      dtcorrect=dtcorrect)
            op = self.op.GetStringSelection()
            if   op == '+': map +=  mapx
            elif op == '-': map -=  mapx
            elif op == '*': map *=  mapx
            elif op == '/':
                mxmin = min(mapx[np.where(mapx>0)])
                if mxmin < 1: mxmin = 1.0
                mapx[np.where(mapx<mxmin)] = mxmin
                map =  map/(1.0*mapx)

            title = '(%s) %s (%s)' % (roiname1, op, roiname2)

        try:
            x = datafile.get_pos(0, mean=True)
        except:
            x = None
        try:
            y = datafile.get_pos(1, mean=True)
        except:
            y = None

        pref, fname = os.path.split(datafile.filename)
        title = '%s: %s' % (fname, title)
        info  = 'Intensity: [%g, %g]' %(map.min(), map.max())

        xoff, yoff = 0, 0
        if self.limrange.IsChecked():
            nx, ny = map.shape
            lims = [wid.GetValue() for wid in self.lims]
            map = map[lims[2]:lims[3], lims[0]:lims[1]]
            if y is not None:
                y   = y[lims[2]:lims[3]]
            if x is not None:
                x   = x[lims[0]:lims[1]]
            xoff, yoff = lims[0], lims[2]

        if len(self.owner.im_displays) == 0 or new:
            iframe = self.owner.add_imdisplay(title, det=det)
        self.owner.display_map(map, title=title, info=info, x=x, y=y,
                               xoff=xoff, yoff=yoff, det=det,
                               xrmfile=datafile)

    def update_xrmmap(self, xrmmap):
        self.set_roi_choices(xrmmap)

    def set_roi_choices(self, xrmmap):
        rois = ['1'] + list(xrmmap['roimap/sum_name'])
        self.roi1.SetChoices(rois[1:])
        self.roi2.SetChoices(rois)

class TriColorMapPanel(GridPanel):
    """Panel of Controls for choosing what to display a 3 color ROI map"""
    label  = '3-Color XRF ROI Map'
    def __init__(self, parent, owner, **kws):
        GridPanel.__init__(self, parent, nrows=8, ncols=5, **kws)
        self.owner = owner
        self.SetMinSize((650, 275))

        self.rcol  = Choice(self, choices=[], size=(120, -1))
        self.gcol  = Choice(self, choices=[], size=(120, -1))
        self.bcol  = Choice(self, choices=[], size=(120, -1))
        self.i0col = Choice(self, choices=[], size=(120, -1))
        self.det   = Choice(self, choices=DETCHOICES, size=(90, -1))
        self.cor   = Check(self, label='Correct Deadtime?')
        self.hotcols  = Check(self, label='Ignore First/Last Columns?')

        self.show_new = Button(self, 'Show New Map',     size=(125, -1),
                               action=partial(self.onShowMap, new=True))
        self.show_old = Button(self, 'Replace Last Map', size=(125, -1),
                               action=partial(self.onShowMap, new=False))

        self.AddManyText(('Detector', 'Red', 'Green', 'Blue'))
        self.AddMany((self.det, self.rcol, self.gcol, self.bcol), newrow=True)

        self.AddText('Normalization:',  newrow=True, style=LEFT)
        self.Add(self.i0col,    dcol=2,              style=LEFT)
        self.Add(self.cor,      dcol=2, newrow=True, style=LEFT)
        self.Add(self.hotcols, dcol=2, style=LEFT)

        self.Add(self.show_new, dcol=2, newrow=True, style=LEFT)
        self.Add(self.show_old, dcol=2,              style=LEFT)

        fopts = dict(minval=-1, precision=0, size=(70, -1))
        self.lims = [FloatCtrl(self, value= 0, **fopts),
                     FloatCtrl(self, value=-1, **fopts),
                     FloatCtrl(self, value= 0, **fopts),
                     FloatCtrl(self, value=-1, **fopts)]

        for wid in self.lims: wid.Disable()

        self.limrange  = Check(self, default=False,
                               label=' Limit Map Range to Pixel Range:',
                               action=self.onLimitRange)
        self.Add(HLine(self, size=(350, 3)), dcol=4, newrow=True, style=CEN)
        self.Add(self.limrange, dcol=4,   newrow=True, style=LEFT)
        self.Add(SimpleText(self, 'X Range:'), dcol=1,
                 newrow=True, style=LEFT)
        self.Add(self.lims[0], dcol=1, style=LEFT)
        self.Add(SimpleText(self, ':'), dcol=1, style=LEFT)
        self.Add(self.lims[1], dcol=1, style=LEFT)
        self.Add(SimpleText(self, 'Y Range:'), dcol=1,
                 newrow=True, style=LEFT)
        self.Add(self.lims[2], dcol=1, style=LEFT)
        self.Add(SimpleText(self, ':'), dcol=1, style=LEFT)
        self.Add(self.lims[3], dcol=1, style=LEFT)

        self.pack()

    def onLimitRange(self, event=None):
        if self.limrange.IsChecked():
            for wid in self.lims:
                wid.Enable()
        else:
            for wid in self.lims:
                wid.Disable()

    def onShowMap(self, event=None, new=True):
        """show 3 color map"""
        datafile = self.owner.current_file
        det =self.det.GetStringSelection()
        if det == 'sum':
            det =  None
        else:
            det = int(det)
        dtcorrect = self.cor.IsChecked()
        no_hotcols  = self.hotcols.IsChecked()
        self.owner.no_hotcols = no_hotcols
        r = self.rcol.GetStringSelection()
        g = self.gcol.GetStringSelection()
        b = self.bcol.GetStringSelection()
        i0 = self.i0col.GetStringSelection()
        mapshape= datafile.xrmmap['roimap/sum_cor'][:, :, 0].shape
        if no_hotcols:
            mapshape = mapshape[0], mapshape[1]-2

        rmap = np.ones(mapshape, dtype='float')
        gmap = np.ones(mapshape, dtype='float')
        bmap = np.ones(mapshape, dtype='float')
        i0map = np.ones(mapshape, dtype='float')
        if r != '1':
            rmap  = datafile.get_roimap(r, det=det, no_hotcols=no_hotcols,
                                        dtcorrect=dtcorrect)
        if g != '1':
            gmap  = datafile.get_roimap(g, det=det, no_hotcols=no_hotcols,
                                        dtcorrect=dtcorrect)
        if b != '1':
            bmap  = datafile.get_roimap(b, det=det, no_hotcols=no_hotcols,
                                        dtcorrect=dtcorrect)
        if i0 != '1':
            i0map = datafile.get_roimap(i0, det=det, no_hotcols=no_hotcols,
                                        dtcorrect=dtcorrect)

        i0min = min(i0map[np.where(i0map>0)])
        if i0min < 1: i0min = 1.0
        i0map[np.where(i0map<i0min)] = i0min
        i0map = 1.0 * i0map / i0map.max()
        # print( 'I0 map : ', i0map.min(), i0map.max(), i0map.mean())

        pref, fname = os.path.split(datafile.filename)
        title = '%s: (R, G, B) = (%s, %s, %s)' % (fname, r, g, b)
        subtitles = {'red': 'Red: %s' % r,
                     'green': 'Green: %s' % g,
                     'blue': 'Blue: %s' % b}

        try:
            x = datafile.get_pos(0, mean=True)
        except:
            x = None
        try:
            y = datafile.get_pos(1, mean=True)
        except:
            y = None

        if self.limrange.IsChecked():
            lims = [wid.GetValue() for wid in self.lims]
            rmap = rmap[lims[2]:lims[3], lims[0]:lims[1]]
            gmap = gmap[lims[2]:lims[3], lims[0]:lims[1]]
            bmap = bmap[lims[2]:lims[3], lims[0]:lims[1]]
            i0map = i0map[lims[2]:lims[3], lims[0]:lims[1]]
            if y is not None:
                y   = y[lims[2]:lims[3]]
            if x is not None:
                x   = x[lims[0]:lims[1]]

        map = np.array([rmap/i0map, gmap/i0map, bmap/i0map])
        map = map.swapaxes(0, 2).swapaxes(0, 1)
        if len(self.owner.im_displays) == 0 or new:
            iframe = self.owner.add_imdisplay(title, det=det)
        self.owner.display_map(map, title=title, subtitles=subtitles,
                               x=x, y=y, det=det, xrmfile=datafile)

    def update_xrmmap(self, xrmmap):
        self.set_roi_choices(xrmmap)

    def set_roi_choices(self, xrmmap):
        rois = ['1'] + list(xrmmap['roimap/sum_name'])
        for cbox in (self.rcol, self.gcol, self.bcol, self.i0col):
            cbox.SetChoices(rois)



class MapInfoPanel(scrolled.ScrolledPanel):
    """Info Panel """
    label  = 'Map Info'
    def __init__(self, parent, owner, **kws):
        scrolled.ScrolledPanel.__init__(self, parent, -1,
                                        style=wx.GROW|wx.TAB_TRAVERSAL, **kws)
        self.owner = owner

        sizer = wx.GridBagSizer(8, 2)
        self.wids = {}

        ir = 0
        
        for label in ('Scan Started', 'User Comments 1', 'User Comments 2',
                      'Scan Fast Motor', 'Scan Slow Motor', 'Dwell Time',
                      'Sample Fine Stages',
                      'Sample Stage X',     'Sample Stage Y',
                      'Sample Stage Z',     'Sample Stage Theta',
                      'Ring Current', 'X-ray Energy',  'X-ray Intensity (I0)',
                      ## add rows for XRD Calibration File:
                      'XRD Parameters',  'XRD Detector',     
                      'XRD Wavelength',  'XRD Detector Distance', 
                      'XRD Pixel Size',  'XRD Beam Center (x,y)',  'XRD Detector Tilts',
                      'XRD Spline',      'XRD Mask',         'XRD Background'):

            ir += 1
            thislabel        = SimpleText(self, '%s:' % label, style=wx.LEFT, size=(125, -1))
            self.wids[label] = SimpleText(self, ' ' ,          style=wx.LEFT, size=(300, -1))

            sizer.Add(thislabel,        (ir, 0), (1, 1), 1)
            sizer.Add(self.wids[label], (ir, 1), (1, 1), 1)

        pack(self, sizer)
        self.SetupScrolling()


    def update_xrmmap(self, xrmmap):
        self.wids['Scan Started'].SetLabel( xrmmap.attrs['Start_Time'])

        comments = xrmmap['config/scan/comments'].value.split('\n', 2)
        for i, comm in enumerate(comments):
            self.wids['User Comments %i' %(i+1)].SetLabel(comm)

        pos_addrs = [str(x) for x in xrmmap['config/positioners'].keys()]
        pos_label = [str(x.value) for x in xrmmap['config/positioners'].values()]

        scan_pos1 = str(xrmmap['config/scan/pos1'].value)
        scan_pos2 = str(xrmmap['config/scan/pos2'].value)
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
        self.wids['Dwell Time'].SetLabel('%.1f milliseconds per pixel' % pixtime)

        env_names = list(xrmmap['config/environ/name'])
        env_vals  = list(xrmmap['config/environ/value'])
        env_addrs = list(xrmmap['config/environ/address'])

        fines = {'X': '?', 'Y': '?'}
        i0vals = {'flux':'?', 'current':'?'}
        cur_energy = ''

        for name, addr, val in zip(env_names, env_addrs, env_vals):
            name = str(name).lower()
            if 'ring current' in name:
                self.wids['Ring Current'].SetLabel('%s mA' % val)
            elif 'mono energy' in name and cur_energy=='':
                self.wids['X-ray Energy'].SetLabel('%s eV' % val)
                cur_energy = val
            elif 'i0 trans' in name:
                i0vals['flux'] = val
            elif 'i0 current' in name:
                i0vals['current'] = val
            else:
                addr = str(addr)
                if addr.endswith('.VAL'):
                    addr = addr[:-4]
                if addr in pos_addrs:
                    plab = pos_label[pos_addrs.index(addr)].lower()

                    if 'stage x' in plab:
                        self.wids['Sample Stage X'].SetLabel('%s mm' % val)
                    elif 'stage y' in plab:
                        self.wids['Sample Stage Y'].SetLabel('%s mm' % val)
                    elif 'stage z' in plab:
                        self.wids['Sample Stage Z'].SetLabel('%s mm' % val)
                    elif 'theta' in plab:
                        self.wids['Sample Stage Theta'].SetLabel('%s deg' % val)
                    elif 'x' in plab:
                        fines['X'] = val
                    elif 'y' in plab:
                        fines['Y'] = val

        i0val = 'Flux=%(flux)s Hz, I0 Current=%(current)s uA' % i0vals
        self.wids['X-ray Intensity (I0)'].SetLabel(i0val)
        self.wids['Sample Fine Stages'].SetLabel('X, Y = %(X)s, %(Y)s mm' % (fines))

        xrdgp = xrmmap['xrd']
        try:
            pref, calfile = os.path.split(xrdgp.attrs['calfile'])
            self.wids['XRD Parameters'].SetLabel('%s' % calfile)
            xrd_exists = True
        except:
            self.wids['XRD Parameters'].SetLabel('No XRD calibration file in map.')
            xrd_exists = False
            
        if xrd_exists:
            try:
                self.wids['XRD Detector'].SetLabel('%s' % xrdgp.attrs['detector'])
            except:
                self.wids['XRD Detector'].SetLabel('')
            try:
                self.wids['XRD Wavelength'].SetLabel('%0.4f A (%0.3f keV)' % \
                                    (float(xrdgp.attrs['wavelength'])*1.e10,
                                     float(xrdgp.attrs['energy'])))
            except:
                self.wids['XRD Wavelength'].SetLabel('')
            try:
                self.wids['XRD Detector Distance'].SetLabel('%0.3f mm' % \
                                    (float(xrdgp.attrs['distance'])*1.e3))
            except:
                self.wids['XRD Detector Distance'].SetLabel('')
            try:
                self.wids['XRD Pixel Size'].SetLabel('%0.1f um, %0.1f um ' % ( \
                                    float(xrdgp.attrs['ps1'])*1.e6,
                                    float(xrdgp.attrs['ps2'])*1.e6))
            except:
                self.wids['XRD Pixel Size'].SetLabel('')
            try:
                self.wids['XRD Beam Center (x,y)'].SetLabel( \
                                    '%0.4f m, %0.4f m (%i pix, %i pix)' % ( \
                                    float(xrdgp.attrs['poni2']),
                                    float(xrdgp.attrs['poni1']),
                                    float(xrdgp.attrs['poni2'])/float(xrdgp.attrs['ps2']),
                                    float(xrdgp.attrs['poni1'])/float(xrdgp.attrs['ps1'])))
            except:
                self.wids['XRD Beam Center (x,y)'].SetLabel('')
            try:
                self.wids['XRD Detector Tilts'].SetLabel( \
                                    '%0.6f rad., %0.6f rad., %0.6f rad.' % ( \
                                    float(xrdgp.attrs['rot1']),
                                    float(xrdgp.attrs['rot2']),
                                    float(xrgredgp.attrs['rot3'])))
            except:
                self.wids['XRD Detector Tilts'].SetLabel('')
            try:
                self.wids['XRD Spline'].SetLabel('%s' % xrdgp.attrs['spline'])
            except:
                self.wids['XRD Spline'].SetLabel('')
            try:
                pref, maskfile = os.path.split(xrdgp.attrs['maskfile'])
                self.wids['XRD Mask'].SetLabel('%s' % maskfile)
            except:
                self.wids['XRD Mask'].SetLabel('')
            try:
                pref, bkgdfile = os.path.split(xrdgp.attrs['bkgdfile'])
                self.wids['XRD Background'].SetLabel('%s' % bkgdfile)
            except:
                self.wids['XRD Background'].SetLabel('')


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
        sizer = wx.GridBagSizer(10, 7) #6)
        self.choices = {}
        self.choice = Choice(pane, choices=[], size=(200, -1), action=self.onSelect)
        self.desc    = wx.TextCtrl(pane,   -1, '',  size=(200, -1))
        self.info1   = wx.StaticText(pane, -1, '',  size=(250, -1))
        self.info2   = wx.StaticText(pane, -1, '',  size=(250, -1))
        self.onmap   = Button(pane, 'Show on Map',  size=(135, -1), action=self.onShow)
        self.clear   = Button(pane, 'Clear Map',    size=(135, -1), action=self.onClear)
        self.delete  = Button(pane, 'Delete Area',  size=( 90, -1), action=self.onDelete)
        self.update  = Button(pane, 'Save Label',   size=( 90, -1), action=self.onLabel)
        self.bexport = Button(pane, 'Export Areas', size=(135, -1), action=self.onExport)
        self.bimport = Button(pane, 'Import Areas', size=(135, -1), action=self.onImport)
        ######################################

        ######################################
        ## SPECIFIC TO XRF MAP AREAS
        self.onstats  = Button(pane, 'Calculate Stats', size=( 90, -1),
                                                action=self.onShowStats)
        self.xrf      = Button(pane, 'Show XRF (Fore)', size=(135, -1),
                                                action=self.onXRF)
        self.xrf2     = Button(pane, 'Show XRF (Back)', size=(135, -1),
                                                action=partial(self.onXRF, as_mca2=True))
        self.onreport = Button(pane, 'Save XRF report to file', size=(135, -1),
                                                action=self.onReport)
        self.cor = Check(pane, label='Correct Deadtime?')
        legend = wx.StaticText(pane, -1, 'Values in CPS, Time in ms', size=(200, -1))

        ######################################
        ## SPECIFIC TO XRD MAP AREAS
        self.xrd_plot  = Button(pane, 'Show XRD pattern', size=(135, -1),
                                                action=partial(self.onXRD,   new=True))
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

        sizer.Add(self.xrd_plot,            ( 8, 0), (1, 2), ALL_LEFT, 2)

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
            desc = areas[a].attrs.get('description', a)
            self.choices[desc] = a
            choice_labels.append(desc)

        c.AppendItems(choice_labels)
        if len(self.choices) > 0:
            idx = 0
        if show_last:
            idx = len(self.choices)-1
        try:
            this_label = choice_labels[idx]
        except IndexError:
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
                '# %i milliseconds per pixel' % int(round(1000.0*pixtime)),
                '# %.3f total seconds'  % dtime,
                '# Time (TSCALER) in milliseconds',
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
        label = area.attrs.get('description', aname)
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

    def _getxrd_area(self, areaname, **kwargs):
        self._xrd = self.owner.current_file.get_xrd_area(areaname, **kwargs)

    def onXRF(self, event=None, as_mca2=False):
        aname = self._getarea()
        xrmfile = self.owner.current_file
        area  = xrmfile.xrmmap['areas/%s' % aname]
        label = area.attrs.get('description', aname)
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

    def onXRD(self, event=None, new=True):

        ## First, check to make sure there is XRD data
        ## either use FLAG or look for data structures.
        flag1D,flag2D = self.owner.current_file.check_xrd()
        
        if not flag1D and not flag2D:
            print('No XRD data in map file: %s' % self.owner.current_file.filename)
            return

        ## Calculate area
        try:
            aname = self._getarea()
            xrmfile = self.owner.current_file
            area  = xrmfile.xrmmap['areas/%s' % aname]
            label = area.attrs.get('description', aname)
            self._xrd  = None
        except:
            print('No map file and/or areas specified.')
            return

        xrd_thread = Thread(target=self._getxrd_area, args=(aname,))
        xrd_thread.start()
        xrd_thread.join()

        pref, fname = os.path.split(self.owner.current_file.filename)
        npix = len(area.value[np.where(area.value)])
        self._xrd.filename = fname
        self._xrd.title = label
        self._xrd.npixels = npix
        self.owner.message('Plotting XRD pattern for area \'%s\'...' % aname)

        ## DATA      : xrmfile.xrmmap['xrd/data2D'][i,j,] !!!!!!
        ## AREA MASK : area.value

        if flag2D:
            self.onXRD2D()
        if flag1D:
            self.onXRD1D()

                              
    def onXRD2D(self, event=None, new=True):

        ## Rewrite this text into subroutine: wx/xrddisplay.py -> plot2Dxrd
        #self.owner.xrddisplay.plot2Dxrd(self._xrd)
        _larch = self.owner.larch

        aname = self._getarea()
        xrmfile = self.owner.current_file
        area  = xrmfile.xrmmap['areas/%s' % aname]
        label = area.attrs.get('description', aname)
        self._xrd  = None
        
        ## calibration file: self.owner.current_file.xrmmap['xrd'].attrs['calfile']

        xrmfile = self.owner.current_file
        ## DATA      : xrmfile.xrmmap['xrd/data2D'][i,j,] !!!!!!
        ## AREA MASK : area.value

        xrd_thread = Thread(target=self._getxrd_area, args=(aname,))
        xrd_thread.start()
        #self.owner.show_2DXRDDisplay()
        xrd_thread.join()

        pref, fname = os.path.split(self.owner.current_file.filename)
        npix = len(area.value[np.where(area.value)])
        self._xrd.filename = fname
        self._xrd.title = label
        self._xrd.npixels = npix
        self.owner.message('Plotting 2D XRD pattern for area \'%s\'...' % aname)

        ## Rewrite this text into subroutine: wx/xrddisplay.py -> plot2Dxrd
        #self.owner.xrddisplay.plot2Dxrd(self._xrd)
        _larch = self.owner.larch

        map = self._xrd.data2D
        info  = 'Size: %s; Intensity: [%g, %g]' %(map.shape,map.min(), map.max())
        title = '%s: %s' % (fname, aname)

        counter = 1
        while os.path.exists('%s/%s-%s-%03d.tiff' % (pref,fname,aname,counter)):
            counter += 1
        tiffname = '%s/%s-%s-%03d.tiff' % (pref,fname,aname,counter)
        print('Saving 2D data in file: %s\n' % (tiffname))
        
        tifffile.imsave(tiffname,map)
       
        xrdgp = self.owner.current_file.xrmmap['xrd']

        fname = xrmfile.filename

        if len(self.owner.im_displays) == 0 or new:
            iframe = self.owner.add_xrd_display(title, det=None)

        self.owner.display_2Dxrd(map, title=title, info=info, xrmfile=xrmfile)

    def onXRD1D(self, event=None, as_2=False, unit='q'):

        aname = self._getarea()
        xrmfile = self.owner.current_file
        area  = xrmfile.xrmmap['areas/%s' % aname]
        label = area.attrs.get('description', aname)
        self._xrd  = None

        xrmfile = self.owner.current_file
        ## DATA      : xrmfile.xrmmap['xrd/data2D'][i,j,] !!!!!!
        ## AREA MASK : area.value

        xrd_thread = Thread(target=self._getxrd_area, args=(aname,))
        xrd_thread.start()
        self.owner.show_1DXRDDisplay()
        xrd_thread.join()

        pref, fname = os.path.split(self.owner.current_file.filename)
        npix = len(area.value[np.where(area.value)])
        self._xrd.filename = fname
        self._xrd.title = label
        self._xrd.npixels = npix
        self.owner.message('Plotting 1D XRD pattern for area \'%s\'...' % aname)

        _larch = self.owner.larch
        map = self._xrd.data2D
        try:
            ## can add in dark (background) and mask??
            self._xrd.data1D = integrate_xrd(map, unit=unit, steps=5001,
                                    #calfile=xrmfile.xrmmap['xrd'].attrs['calfile'],
                                    AI = xrmfile.xrmmap['xrd'],
                                    aname=aname, prefix=fname, path=pref)
            self._xrd.wavelength = xrmfile.xrmmap['xrd'].attrs['wavelength']
        except:
            return

        self.owner.xrddisplay1D.plot1Dxrd(self._xrd,unit=unit)

class MapViewerFrame(wx.Frame):
    cursor_menulabels = {'lasso': ('Select Points for XRF Spectra\tCtrl+X',
                                   'Left-Drag to select points for XRF Spectra')}

    def __init__(self, conffile=None,  use_scandb=False, _larch=None, **kwds):

        kwds['style'] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, None, -1, size=(700, 450),  **kwds)

        self.data = None
        self.use_scandb = use_scandb
        self.filemap = {}
        self.im_displays = []
        self.plot_displays = []
        self.larch = _larch
        self.xrfdisplay = None
        self.xrddisplay1D = None
        self.xrddisplay2D = None
        self.larch_buffer = None
        self.watch_files = False
        self.file_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onFileWatchTimer, self.file_timer)
        self.files_in_progress = []
        self.no_hotcols = True
        self.SetTitle('GSE XRM MapViewer')
        self.SetFont(Font(9))

        self.createMainPanel()
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


    def CloseFile(self, filename, event=None):
        if filename in self.filemap:
            self.filemap[filename].close()
            self.filemap.pop(filename)

    def createMainPanel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(275)

        self.filelist = EditableListBox(splitter, self.ShowFile,
                                        remove_action=self.CloseFile,
                                        size=(250, -1))

        dpanel = self.detailspanel = wx.Panel(splitter)
        dpanel.SetMinSize((700, 450))
        self.createNBPanels(dpanel)
        splitter.SplitVertically(self.filelist, self.detailspanel, 1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)
        wx.CallAfter(self.init_larch)
        pack(self, sizer)

    def createNBPanels(self, parent):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # title area:
        tpanel = wx.Panel(parent)
        self.title    = SimpleText(tpanel, 'initializing...', size=(600, -1))
        tsizer = wx.BoxSizer(wx.HORIZONTAL)
        tsizer.Add(self.title,     0, ALL_LEFT)
        pack(tpanel, tsizer)

        sizer.Add(tpanel, 0, ALL_CEN)

        self.nb = flat_nb.FlatNotebook(parent, wx.ID_ANY, agwStyle=FNB_STYLE)
        self.nb.SetBackgroundColour('#FCFCFA')
        self.SetBackgroundColour('#F0F0E8')

        self.nbpanels = []

        for creator in (SimpleMapPanel, TriColorMapPanel, MapInfoPanel,
                        MapAreaPanel, MapMathPanel):

            p = creator(parent, owner=self)
            self.nb.AddPage(p, p.label.title(), True)
            bgcol = p.GetBackgroundColour()
            self.nbpanels.append(p)

            self.nb.SetSelection(0)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)

        # self.area_sel = AreaSelectionPanel(parent, owner=self)
        # self.area_sel.SetBackgroundColour('#F0F0E8')

        # sizer.Add(wx.StaticLine(parent, size=(250, 2),
        #                         style=wx.LI_HORIZONTAL),
        #          0,  wx.ALL|wx.EXPAND)
        # sizer.Add(self.area_sel, 0, wx.ALL|wx.EXPAND)
        pack(parent, sizer)

    def get_mca_area(self, det, mask, xoff=0, yoff=0, xrmfile=None):
        if xrmfile is None:
            xrmfile = self.current_file
        aname = xrmfile.add_area(mask)
        self.sel_mca = xrmfile.get_mca_area(aname, det=det)

    def get_xrd_area(self, mask, xoff=0, yoff=0, xrmfile=None):
        if xrmfile is None:
            xrmfile = self.current_file
        ##aname = xrmfile.add_area(mask)
        ##self.sel_xrd = xrmfile.get_xrd_area(aname)
        self.sel_xrd = xrmfile.xrd2d[50,50,]

    def lassoHandler(self, mask=None, det=None, xrmfile=None,
                     xoff=0, yoff=0, **kws):
        ny, nx, npos = xrmfile.xrmmap['positions/pos'].shape
        # print('lasso handler ', mask.shape, ny, nx)
        if (xoff>0 or yoff>0) or mask.shape != (ny, nx):
            ym, xm = mask.shape
            tmask = np.zeros((ny, nx)).astype(bool)
            for iy in range(ym):
                tmask[iy+yoff, xoff:xoff+xm] = mask[iy]
            mask = tmask
            # print('shifted mask!')

        kwargs = dict(xrmfile=xrmfile, xoff=xoff, yoff=yoff)
        mca_thread = Thread(target=self.get_mca_area,
                            args=(det,mask), kwargs=kwargs)
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
            
            # SET AREA CHOICE
            for p in self.nbpanels:
                if hasattr(p, 'update_xrmmap'):
                    p.update_xrmmap(self.current_file.xrmmap)

    def show_XRFDisplay(self, do_raise=True, clear=True, xrmfile=None):
        'make sure plot frame is enabled, and visible'
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

    def show_1DXRDDisplay(self, do_raise=True, clear=True, xrmfile=None):
        'make sure plot frame is enabled, and visible'
        if xrmfile is None:
            xrmfile = self.current_file
        if self.xrddisplay is None:
            self.xrddisplay = XRD1D_DisplayFrame(_larch=self.larch)

        try:
            self.xrddisplay.Show()
        except PyDeadObjectError:
            self.xrddisplay = XRD1D_DisplayFrame(_larch=self.larch)
            self.xrddisplay.Show()

        if do_raise:
            self.xrddisplay.Raise()
        if clear:
            self.xrddisplay.panel.clear()
            self.xrddisplay.panel.reset_config()

    def show_1DXRDDisplay(self, do_raise=True, clear=True, xrmfile=None):
        'make sure plot frame is enabled, and visible'
        if xrmfile is None:
            xrmfile = self.current_file
        if self.xrddisplay1D is None:
            self.xrddisplay1D = XRD1D_DisplayFrame(_larch=self.larch)

        try:
            self.xrddisplay1D.Show()
        except PyDeadObjectError:
            self.xrddisplay1D = XRD1D_DisplayFrame(_larch=self.larch)
            self.xrddisplay1D.Show()

        if do_raise:
            self.xrddisplay1D.Raise()
        if clear:
            self.xrddisplay1D.panel.clear()
            self.xrddisplay1D.panel.reset_config()

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

    def onSavePixel(self, name, ix, iy, x=None, y=None, title=None, datafile=None):
        'save pixel as area, and perhaps to scandb'
        # print(' On Save Pixel ', name, ix, iy, x, y)
        if len(name) < 1:
            return
        if datafile is None:
            datafile = self.current_file
        xrmmap  = datafile.xrmmap

        # first, create 1-pixel mask for area, and save that
        ny, nx, npos = xrmmap['positions/pos'].shape
        tmask = np.zeros((ny, nx)).astype(bool)
        tmask[int(iy), int(ix)] = True
        datafile.add_area(tmask, name=name)
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
                x = float(datafile.get_pos(0, mean=True)[ix])
            if y is None:
                y = float(datafile.get_pos(1, mean=True)[iy])

            position[pvn(conf['scan/pos1'].value)] = x
            position[pvn(conf['scan/pos2'].value)] = y

            for addr, val in zip(env_addrs, env_vals):
                if addr in pos_addrs and position[addr] is None:
                    position[addr] = float(val)

            if title is None:
                title = '%s: %s' % (datafile.filename, name)

            notes = {'source': title}
            # print(' Save Position : ', self.inst_name, name, position, notes)

            self.instdb.save_position(self.inst_name, name, position,
                                      notes=json.dumps(notes))





    def add_imdisplay(self, title, det=None):
        on_lasso = partial(self.lassoHandler, det=det)
        imframe = MapImageFrame(output_title=title,
                                lasso_callback=on_lasso,
                                cursor_labels = self.cursor_menulabels,
                                move_callback=self.move_callback,
                                save_callback=self.onSavePixel)

        self.im_displays.append(imframe)

    def display_map(self, map, title='', info='', x=None, y=None,
                    xoff=0, yoff=0, det=None, subtitles=None, xrmfile=None):
        """display a map in an available image display"""
        displayed = False
        lasso_cb = partial(self.lassoHandler, det=det, xrmfile=xrmfile)
        if x is not None:
            if self.no_hotcols and map.shape[1] != x.shape[0]:
                x = x[1:-1]

        while not displayed:
            try:
                imd = self.im_displays.pop()
                imd.display(map, title=title, x=x, y=y, xoff=xoff, yoff=yoff,
                            subtitles=subtitles, det=det, xrmfile=xrmfile)
                #for col, wid in imd.wid_subtitles.items():
                #    wid.SetLabel('%s: %s' % (col.title(), subtitles[col]))
                imd.lasso_callback = lasso_cb
                displayed = True
            except IndexError:
                imd = MapImageFrame(output_title=title,
                                    lasso_callback=lasso_cb,
                                    cursor_labels = self.cursor_menulabels,
                                    move_callback=self.move_callback,
                                    save_callback=self.onSavePixel)

                imd.display(map, title=title, x=x, y=y, xoff=xoff, yoff=yoff,
                            subtitles=subtitles, det=det, xrmfile=xrmfile)
                displayed = True
            except PyDeadObjectError:
                displayed = False
        self.im_displays.append(imd)
        imd.SetStatusText(info, 1)
        imd.Show()
        imd.Raise()

    def add_xrd_display(self, title, det=None):
        on_lasso = partial(self.lassoHandler, det=det)
        imframe = XRD2D_DisplayFrame(output_title=title,
                                     lasso_callback=on_lasso,
                                     cursor_labels = self.cursor_menulabels,
                                     move_callback=self.move_callback,
                                     save_callback=self.onSavePixel)

        self.im_displays.append(imframe)

    def display_2Dxrd(self, map, title='', info='', xrmfile=None):
        """display a map in an available image display"""
        displayed = False
        lasso_cb = partial(self.lassoHandler, xrmfile=xrmfile)

        try:
            calfile = self.current_file.xrmmap['xrd'].attrs['calfile']
            AI = calculate_ai(self.current_file.xrmmap['xrd'])
        except:
            AI = None

        while not displayed:
            try:
                imd = self.im_displays.pop()
                imd.display(map, title=title, xrmfile=xrmfile, ai=AI)
                imd.lasso_callback = lasso_cb
                displayed = True
            except IndexError:
                imd = XRD2D_DisplayFrame(output_title=title,
                                    lasso_callback=lasso_cb,
                                    cursor_labels = self.cursor_menulabels,
                                    move_callback=self.move_callback,
                                    save_callback=self.onSavePixel)

                imd.display(map, title=title, xrmfile=xrmfile, ai=AI)
                displayed = True
            except PyDeadObjectError:
                displayed = False
        self.im_displays.append(imd)
        imd.SetStatusText(info, 1)
        imd.Show()
        imd.Raise()

    def init_larch(self):
        if self.larch is None:
            self.larch = larch.Interpreter()
            self.larch.symtable.set_symbol('_sys.wx.parent', self)
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
                sys.path.insert(0, '//cars5/Data/xas_user/bin/python')
                from scan_credentials import conn as DBCONN
                import scan_credentials

                from larch_plugins.epics.scandb_plugin import connect_scandb
                DBCONN['_larch'] = self.larch
                connect_scandb(**DBCONN)
                self.scandb = self.larch.symtable._scan._scandb
                self.instdb = self.larch.symtable._scan._instdb
                self.inst_name = 'IDE_SampleStage'
                print(" Connected to scandb='%s' on server at '%s'" %
                      (DBCONN['dbname'], DBCONN['host']))
            except:
                print('Could not connect to ScanDB')
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
        MenuItem(self, fmenu, 'Perform XRD &Calibration',
                 'Calibrate XRD Detector',  self.onCalXRD)
        MenuItem(self, fmenu, '&Update XRD Calibration File to Map File',
                 'Load XRD Calibration File',  self.onReadXRD)
        MenuItem(self, fmenu, '&Save As...  without 2D XRD data',
                 'Save without 2D XRD data',  self.onReSave)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, 'Show Larch Buffer',
                  'Show Larch Programming Buffer',
                  self.onShowLarchBuffer)

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
            self.larch_buffer = larchframe.LarchFrame(_larch=self.larch)

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
        save_workdir('gsemap.dat')
        for xrmfile in self.filemap.values():
            xrmfile.close()

        for disp in self.im_displays + self.plot_displays:
            try:
                disp.Destroy()
            except:
                pass

        try:
            self.xrfdisplay.Destroy()
        except:
            pass
        if self.larch_buffer is not None:
            try:
                self.larch_buffer.onClose()
            except:
                pass

        for nam in dir(self.larch.symtable._plotter):
            obj = getattr(self.larch.symtable._plotter, nam)
            try:
                obj.Destroy()
            except:
                pass
        for nam in dir(self.larch.symtable._sys.wx):
            obj = getattr(self.larch.symtable._sys.wx, nam)
            del obj
        self.Destroy()

    def onReadFolder(self, evt=None):
        if not self.h5convert_done:
            print( 'cannot open file while processing a map folder')
            return
            
        myDlg = OpenMapFolder()

        path, read = None, False
        FLAGxrf, FLAGxrd = False, False
        if myDlg.ShowModal() == wx.ID_OK:
            read        = True
            path        = myDlg.FldrPath
            xrdcalfile  = myDlg.CaliPath
            xrdmaskfile = myDlg.MaskPath
            xrdbkgdfile = myDlg.BkgdPath
            FLAGxrf     = myDlg.FLAGxrf
            FLAGxrd     = myDlg.FLAGxrd

        myDlg.Destroy()
        
        if read:
            xrmfile = GSEXRM_MapFile(folder=str(path),
                                     calibration=xrdcalfile,
                                     mask=xrdmaskfile, bkgd=xrdbkgdfile,
                                     FLAGxrf=FLAGxrf,FLAGxrd=FLAGxrd)
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
            os.chdir(nativepath(parent))
            save_workdir(nativepath(parent))

    def onReadXRD(self, evt=None):
        """
        Read specified poni file.
        mkak 2016.07.21
        """
 
        myDlg = OpenXRDPar()

        path, read = None, False
        FLAGxrf, FLAGxrd = False, False
        if myDlg.ShowModal() == wx.ID_OK:
            if myDlg.CaliPath or myDlg.MaskPath or myDlg.BkgdPath:
                read = True

            try:
                xrdcalfile = self.current_file.xrmmap['xrd'].attrs['calfile']
            except:
                xrdcalfile = None
            try:
                xrdmaskfile = self.current_file.xrmmap['xrd'].attrs['maskfile']
            except:
                xrdmaskfile = None
            try:
                xrdbkgdfile = self.current_file.xrmmap['xrd'].attrs['bkgdfile']
            except:
                xrdbkgdfile = None
            
            if myDlg.CaliPath:
                xrdcalfile = myDlg.CaliPath
            if myDlg.MaskPath:
                xrdmaskfile = myDlg.MaskPath            
            if myDlg.BkgdPath:
                xrdbkgdfile = myDlg.BkgdPath

        myDlg.Destroy()
        
        if read:
            xrmfile = self.current_file

            xrmfile.calibration = xrdcalfile
            xrmfile.xrdmask     = xrdmaskfile
            xrmfile.xrdbkgd     = xrdbkgdfile
            xrmfile.add_calibration()
            
            for p in self.nbpanels:
                if hasattr(p, 'update_xrmmap'):
                    p.update_xrmmap(self.current_file.xrmmap)

    def onCalXRD(self, evt=None):
        """
        Perform calibration with pyFAI
        mkak 2016.09.16
        """
        if HAS_pyFAI:

            myDlg = CalXRD()
            
            path, read = None, False
            FLAGxrf, FLAGxrd = False, False
            if myDlg.ShowModal() == wx.ID_OK:
                read = True

            myDlg.Destroy()
        
            if read:
            
                usr_calimg = myDlg.CaliPath

                ## E = hf ; E = hc/lambda
                hc = constants.value(u'Planck constant in eV s') * \
                       constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m
                if myDlg.slctEorL.GetSelection() == 1:
                    usr_lambda = float(myDlg.EorL.GetValue())*1e-10 ## units: m
                    usr_E = hc/(usr_lambda) ## units: keV
                else:
                    usr_E = float(myDlg.EorL.GetValue()) ## units keV
                    usr_lambda = hc/(usr_E) ## units: m

                if myDlg.slctDorP.GetSelection() == 1:
                    usr_pixel = float(myDlg.pixel.GetValue())*1e-6
                else:
                    usr_det  = myDlg.detslct.GetString(myDlg.detslct.GetSelection())
                usr_clbrnt  = myDlg.calslct.GetString(myDlg.calslct.GetSelection())
                usr_dist = float(myDlg.Distance.GetValue())

                verbose = True #False
                if verbose:
                    print('\n=== Calibration input ===')
                    print('XRD image: %s' % usr_calimg)
                    print('Calibrant: %s' % usr_clbrnt)
                    if myDlg.slctDorP.GetSelection() == 1:
                        print('Pixel size: %0.1f um' % (usr_pixel*1e6))
                    else:
                        print('Detector: %s' % usr_det)
                    print('Incident energy: %0.2f keV (%0.4f A)' % (usr_E,usr_lambda*1e10))
                    print('Starting distance: %0.3f m' % usr_dist)
                    print('=========================\n')
                
                ## Adapted from pyFAI-calib
                ## note: -l:units mm; -dist:units m
                ## mkak 2016.09.19

                if myDlg.slctDorP.GetSelection() == 1:
                    pform1 = 'pyFAI-calib -c %s -p %s -e %0.1f -dist %0.3f %s'
                    command1 = pform1 % (usr_clbrnt,usr_pixel,usr_E,usr_dist,usr_calimg)
                
                
                else:
                    pform1 = 'pyFAI-calib -c %s -D %s -e %0.1f -dist %0.3f %s'
                    command1 = pform1 % (usr_clbrnt,usr_det,usr_E,usr_dist,usr_calimg)
                pform2 = 'pyFAI-recalib -i %s -c %s %s'
                command2 = pform2 % (usr_calimg.split('.')[0]+'.poni',usr_clbrnt,usr_calimg)

                if verbose:
                    print('\nNot functioning within code yet... but you could execute:')
                    print('\t $ %s' % command1)
                    print('\t $ %s\n\n' % command2)
                #os.system(command1)
                #os.system(command2)
                
                ## Try 1: fails to open/find file. Problem with fabio? -> could
                ##        be that we need 'trying PIL' option, e.g. WARNING:tifimage:Unable
                ##        to read /Users/mkak/xl_CeO2-19keV.tif with TiffIO due to unpack
                ##        requires a string argument of length 8, trying PIL
                #cal = Calibration(dataFiles=usr_calimg,           
                #                  detector=usr_det,
                #                  wavelength=usr_lambda,
                #                  #pixelSize=usr_pixel,
                #                  calibrant=usr_clbrnt,
                #                  )
                
                ## Try 2: Not providing CeO2 correctly... Hmmm...
                #usr_detect = pyFAI.detectors.Detector().factory(usr_det)
                #usr_clb = pyFAI.calibrant.Calibrant(filename=usr_clbrnt,wavelength=usr_lambda)
                #pyFAI.calibration.calib(usr_calimg,usr_clb,usr_detect,dist=usr_dist)
                #usr_calibrate = pyFAI.calibrant.ALL_CALIBRANTS[usr_clbrnt]

        else:
            print('pyFAI must be available for calibration.')


    def onReSave(self, evt=None):
        """
        Re-save hdf5 without 2D data
        mkak 2016.09.09
        """
        try:
            print('Copy file: %s' % self.current_file.filename)
        except:
            print('No h5 file to copy.')
            return
 
        ## Check to make sure 2D xrd data AND calibration file there.
         
        ## Choose XRD data calibration file (*.poni)
        wildcards = 'pyFAI files (*.h5)|*.h5|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message = 'Save As',
                            defaultDir=os.getcwd(),
                            wildcard=wildcards,
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()

        if read:
            if path.split('.')[-1] != 'h5':
                path = '%s.h5' % path
            try:
                self.current_file.copy_hdf5(path)
                
                ## This steps opens file in left panel.
                xrmfile = GSEXRM_MapFile(filename=str(path))
                self.add_xrmfile(xrmfile)
            except:
                print('Copying failed.')

    def onReadFile(self, evt=None):
        if not self.h5convert_done:
            print('cannot open file while processing a map folder')
            return

        dlg = wx.FileDialog(self, message='Read Map File',
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.FD_OPEN)
        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
            if path in self.filemap:
                read = (wx.ID_YES == Popup(self, "Re-read file '%s'?" % path,
                                           'Re-read file?', style=wx.YES_NO))

        dlg.Destroy()

        if read:
            parent, fname = os.path.split(path)
            xrmfile = GSEXRM_MapFile(filename=str(path))
            self.add_xrmfile(xrmfile)

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

    def onTimer(self, event):
        fname, irow, nrow = self.h5convert_fname, self.h5convert_irow, self.h5convert_nrow
        self.message('MapViewer Timer Processing %s:  row %i of %i' % (fname, irow, nrow))
        if self.h5convert_done:
            self.htimer.Stop()
            self.h5convert_thread.join()
            if fname in self.files_in_progress:
                self.files_in_progress.remove(fname)
            self.message('MapViewerTimer Processing %s: complete!' % fname)
            self.ShowFile(filename=self.h5convert_fname)

## This routine is almost identical to 'process()' in xrmmap/xrm_mapfile.py ,
## however 'new_mapdata()' updates messages in mapviewer.py window!!
## For now, keep as is.
## mkak 2016.09.07
    def new_mapdata(self, filename):

        xrm_map = self.filemap[filename]
        nrows = len(xrm_map.rowdata)
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

class OpenMapFolder(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
    
        self.FLAGxrf  = False
        self.FLAGxrd  = False
        self.FldrPath = None
        self.CaliPath = None
        self.MaskPath = None
        self.BkgdPath = None
    
    
        """Constructor"""
        dialog = wx.Dialog.__init__(self, None, title='XRM Map Folder',size=(400, 550))
        
        panel = wx.Panel(self)

        fldrTtl  = wx.StaticText(panel,  label='XRM Map Folder:'       )
        fldrBtn  = wx.Button(panel,      label='Browse...'             )
        chTtl    = wx.StaticText(panel,  label='Include data for...'   )
        xrfCkBx  = wx.CheckBox(panel,    label='XRF'                   )
        xrdCkBx  = wx.CheckBox(panel,    label='XRD'                   )
        optTtl   = wx.StaticBox(panel,   label='XRD Options'           )
        caliTtl  = wx.StaticText(panel,  label='XRD Calibration File:' )
        fileBtn1 = wx.Button(panel,      label='Browse...'             )
        blnkTtl1 = wx.StaticText(panel,  label=''                      )
        maskTtl  = wx.StaticText(panel,  label='XRD Mask File:'        )
        fileBtn2 = wx.Button(panel,      label='Browse...'             )
        blnkTtl2 = wx.StaticText(panel,  label=''                      )
        bkgdTtl  = wx.StaticText(panel,  label='XRD Background File:'  )
        fileBtn3 = wx.Button(panel,      label='Browse...'             )

        self.Fldr = wx.TextCtrl(panel,
#                                value ='Please select folder.',
                                size=(350, 25))
        self.CalFl = wx.TextCtrl(panel, 
#                                 value='Please select calibration file.',
                                 size=(350, 25))
        self.MskFl = wx.TextCtrl(panel, 
#                                 value='Please select mask file.',
                                 size=(350, 25))
        self.BkgdFl = wx.TextCtrl(panel, 
#                                 value='Please select background file.',
                                 size=(350, 25))


        hlpBtn = wx.Button(panel, wx.ID_HELP   )
        okBtn  = wx.Button(panel, wx.ID_OK     )
        canBtn = wx.Button(panel, wx.ID_CANCEL )
        self.FindWindowById(wx.ID_OK).Disable()

        self.Bind(wx.EVT_BUTTON,   self.onBROWSE,   fldrBtn  )
        self.Bind(wx.EVT_CHECKBOX, self.onXRFcheck, xrfCkBx  )
        self.Bind(wx.EVT_CHECKBOX, self.onXRDcheck, xrdCkBx  )
        self.Bind(wx.EVT_BUTTON,   self.onBROWSE1,  fileBtn1 )
        self.Bind(wx.EVT_BUTTON,   self.onBROWSE2,  fileBtn2 )
        self.Bind(wx.EVT_BUTTON,   self.onBROWSE3,  fileBtn3 )

        boxsizer = wx.StaticBoxSizer(optTtl, wx.VERTICAL)

        boxsizer.Add(caliTtl,     flag=wx.TOP|wx.LEFT|wx.BOTTOM )
        boxsizer.Add(self.CalFl,  flag=wx.TOP|wx.EXPAND         )
        boxsizer.Add(fileBtn1,    flag=wx.TOP|wx.RIGHT          )
        boxsizer.Add(blnkTtl1,    flag=wx.TOP|wx.LEFT|wx.BOTTOM )
        boxsizer.Add(maskTtl,     flag=wx.TOP|wx.LEFT|wx.BOTTOM )
        boxsizer.Add(self.MskFl,  flag=wx.TOP|wx.EXPAND         )
        boxsizer.Add(fileBtn2,    flag=wx.TOP|wx.RIGHT          )
        boxsizer.Add(blnkTtl2,    flag=wx.TOP|wx.LEFT|wx.BOTTOM )
        boxsizer.Add(bkgdTtl,     flag=wx.TOP|wx.LEFT|wx.BOTTOM )
        boxsizer.Add(self.BkgdFl, flag=wx.TOP|wx.EXPAND         )
        boxsizer.Add(fileBtn3,    flag=wx.TOP|wx.RIGHT          )

        sizer = wx.GridBagSizer(5, 6)

        sizer.Add(fldrTtl,   pos = (1,1) )
        sizer.Add(self.Fldr, pos = (2,1), span = (1,4) )
        sizer.Add(fldrBtn,   pos = (3,1) )
        sizer.Add(chTtl,     pos = (5,1) )
        sizer.Add(xrfCkBx,   pos = (6,1) )
        sizer.Add(xrdCkBx,   pos = (7,1) )
        sizer.Add(boxsizer,  pos = (9,1), span = (1,4)  )       
        sizer.Add(hlpBtn,    pos = (10,1) )
        sizer.Add(okBtn,     pos = (10,3) )
        sizer.Add(canBtn,    pos = (10,2) )
        
        sizer.AddGrowableCol(2)
        panel.SetSizer(sizer)       

    def onXRFcheck(self, event):
        self.FLAGxrf = event.GetEventObject().GetValue()
      
        if self.FLAGxrf or self.FLAGxrd:
            if self.FldrPath:
                self.FindWindowById(wx.ID_OK).Enable()
        else:
                self.FindWindowById(wx.ID_OK).Disable()

    def onXRDcheck(self, event): 
        self.FLAGxrd = event.GetEventObject().GetValue()
        
        if self.FLAGxrf or self.FLAGxrd:
            if self.FldrPath:
                self.FindWindowById(wx.ID_OK).Enable()
        else:
                self.FindWindowById(wx.ID_OK).Disable()

    def onBROWSE(self, event): 
        dlg = wx.DirDialog(self, message='Read XRF Map Folder',
                           defaultPath=os.getcwd(),
                           style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            self.Fldr.Clear()
            self.Fldr.SetValue(str(path))
            #self.Fldr.AppendText(str(path))
            self.FldrPath = path
        
        if self.FLAGxrf or self.FLAGxrd:
            if self.FldrPath:
                self.FindWindowById(wx.ID_OK).Enable()
        else:
                self.FindWindowById(wx.ID_OK).Disable()

    def onBROWSE1(self, event): 
        wildcards = 'pyFAI calibration (*.poni)|*.poni|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD calibration file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            self.CalFl.Clear()
            self.CalFl.SetValue(str(path))
            #self.CalFl.AppendText(str(path))
            self.CaliPath = path

    def onBROWSE2(self, event): 
        wildcards = 'pyFAI mask (*.edf)|*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD mask file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            self.MskFl.Clear()
            self.MskFl.SetValue(str(path))
            self.MaskPath = path
            
    def onBROWSE3(self, event): 
        wildcards = 'pyFAI background (*.edf)|*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD background file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            self.BkgdFl.Clear()
            self.BkgdFl.SetValue(str(path))
            self.BkgdPath = path
        
class CalXRD(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
    
        ## Constructor
        dialog = wx.Dialog.__init__(self, None, title='XRD Calibration',size=(460, 440))
        ## remember: size=(width,height)
        self.panel = wx.Panel(self)

        self.InitUI()
        self.Centre()
        self.Show()

        ## Sets some typical defaults specific to GSE 13-ID procedure
        self.pixel.SetValue('400')     ## binned pixels (2x200um)
        self.EorL.SetValue('19.0')     ## 19.0 keV
        self.Distance.SetValue('0.5')  ## 0.5 m
        self.detslct.SetSelection(22)  ## Perkin detector
        self.calslct.SetSelection(20)  ## CeO2
        
        if self.slctDorP.GetSelection() == 0:
            self.sizer.Hide(self.pixel)

        ## Do not need flags if defaults are set
        #self.FlagCalibrant = False
        #self.FlagDetector  = False
        self.FlagCalibrant = True
        self.FlagDetector  = True

    def InitUI(self):        


        ## Establish lists from pyFAI        
        clbrnts = [] #['None']
        self.dets = [] #['None']
        for key,value in pyFAI.detectors.ALL_DETECTORS.items():
            self.dets.append(key)
        for key,value in pyFAI.calibrant.ALL_CALIBRANTS.items():
            clbrnts.append(key)    
        self.CaliPath = None
    

        ## Calibration Image selection
        caliImg     = wx.StaticText(self.panel,  label='Calibration Image:' )
        self.calFil = wx.TextCtrl(self.panel, size=(190, -1))
        fileBtn1    = wx.Button(self.panel,      label='Browse...'             )

        ## Calibrant selection
        self.calslct = wx.Choice(self.panel,choices=clbrnts)
        CalLbl = wx.StaticText(self.panel, label='Calibrant:' ,style=LEFT) 

        ## Detector selection
        self.slctDorP = wx.Choice(self.panel,choices=['Detector','Pixel size (um)'])
        self.detslct  = wx.Choice(self.panel, choices=self.dets)
        self.pixel    = wx.TextCtrl(self.panel, size=(140, -1))

        ## Energy or Wavelength
        self.slctEorL = wx.Choice(self.panel,choices=['Energy (keV)','Wavelength (A)'])
        self.EorL = wx.TextCtrl(self.panel, size=(140, -1))

        ## Refine label
        RefLbl = wx.StaticText(self.panel, label='To be refined...' ,style=LEFT)

        ## Distance
        self.Distance = wx.TextCtrl(self.panel, size=(140, -1))
        DstLbl = wx.StaticText(self.panel, label='Distance (m):' ,style=LEFT)

        hlpBtn = wx.Button(self.panel, wx.ID_HELP   )
        okBtn  = wx.Button(self.panel, wx.ID_OK     )
        canBtn = wx.Button(self.panel, wx.ID_CANCEL )

        self.Bind(wx.EVT_BUTTON,   self.onBROWSE1,  fileBtn1 )
        self.calslct.Bind(wx.EVT_CHOICE,  self.onCalSel)
        self.detslct.Bind(wx.EVT_CHOICE,  self.onDetSel)
        self.slctDorP.Bind(wx.EVT_CHOICE, self.onDorPSel)
        self.slctEorL.Bind(wx.EVT_CHOICE, self.onEorLSel)

        self.sizer = wx.GridBagSizer( 5, 6)

        self.sizer.Add(caliImg,       pos = ( 1,1)               )
        self.sizer.Add(self.calFil,   pos = ( 1,2), span = (1,2) )
        self.sizer.Add(fileBtn1,      pos = ( 1,4)               )
        self.sizer.Add(CalLbl,        pos = ( 3,1)               )
        self.sizer.Add(self.calslct,  pos = ( 3,2), span = (1,2) )
        
        self.sizer.Add(self.slctDorP, pos = ( 4,1)               )
        self.sizer.Add(self.detslct,  pos = ( 4,2), span = (1,4) )
        self.sizer.Add(self.pixel,    pos = ( 5,2), span = (1,2) )
        
        self.sizer.Add(self.slctEorL, pos = ( 6,1)               )
        self.sizer.Add(self.EorL,     pos = ( 6,2), span = (1,2) )

        self.sizer.Add(RefLbl,        pos = ( 8,1)               )
        self.sizer.Add(DstLbl,        pos = ( 9,1)               )
        self.sizer.Add(self.Distance, pos = ( 9,2), span = (1,2) )

        self.sizer.Add(hlpBtn,        pos = (11,1)               )
        self.sizer.Add(canBtn,        pos = (11,2)               )
        self.sizer.Add(okBtn,         pos = (11,3)               )

        self.FindWindowById(wx.ID_OK).Disable()
        
        self.panel.SetSizer(self.sizer)


    def onCalSel(self,event):
        #if self.calslct.GetSelection() == 0:
        #    self.FlagCalibrant = False
        #else:
        #    self.FlagCalibrant = True
        self.checkOK()

    def onDetSel(self,event):
        #if self.detslct.GetSelection() == 0:
        #    self.FlagDetector = False
        #else:
        #    self.FlagDetector = True
        self.checkOK()

    def onCheckOK(self,event):
        self.checkOK()

    def checkOK(self):
        if self.FlagCalibrant and self.CaliPath is not None:
            if self.slctDorP.GetSelection() == 1:
                self.FindWindowById(wx.ID_OK).Enable()
            else:
                if self.FlagDetector:
                    self.FindWindowById(wx.ID_OK).Enable()
                else:
                    self.FindWindowById(wx.ID_OK).Disable()
        else:
            self.FindWindowById(wx.ID_OK).Disable()

    def onEorLSel(self,event): 
        hc = constants.value(u'Planck constant in eV s') * \
                       constants.value(u'speed of light in vacuum') * 1e-3 ## units: keV-m
        if self.slctEorL.GetSelection() == 1:
            energy = float(self.EorL.GetValue()) ## units keV
            wavelength = hc/(energy)*1e10 ## units: A
            self.EorL.SetValue(str(wavelength))
        else:
            wavelength = float(self.EorL.GetValue())*1e-10 ## units: m
            energy = hc/(wavelength) ## units: keV
            self.EorL.SetValue(str(energy))
            
        self.checkOK()

    def onDorPSel(self,event): 
        if self.slctDorP.GetSelection() == 0:
            self.sizer.Hide(self.pixel)
            self.sizer.Show(self.detslct)
        else:
            self.sizer.Hide(self.detslct)
            self.sizer.Show(self.pixel)

        self.checkOK()

    def onBROWSE1(self, event): 
        wildcards = 'XRD image (*.edf,*.tif,*.tiff)|*.tif;*.tiff;*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD calibration file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            self.calFil.Clear()
            self.calFil.SetValue(os.path.split(path)[-1])
            self.CaliPath = path
            self.checkOK()

class OpenXRDPar(wx.Dialog):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
    
        self.CaliPath = None
        self.MaskPath = None
        self.BkgdPath = None
    
    
        """Constructor"""
        dialog = wx.Dialog.__init__(self, None, title='XRD Parameters',size=(400, 400))
        
        panel = wx.Panel(self)

        caliTtl  = wx.StaticText(panel,  label='XRD Calibration File:' )
        fileBtn1 = wx.Button(panel,      label='Browse...'             )
        maskTtl  = wx.StaticText(panel,  label='XRD Mask File:'        )
        fileBtn2 = wx.Button(panel,      label='Browse...'             )
        bkgdTtl  = wx.StaticText(panel,  label='XRD Background File:'  )
        fileBtn3 = wx.Button(panel,      label='Browse...'             )

        self.CalFl = wx.TextCtrl(panel, 
#                                 value='Please select calibration file.',
                                 size=(350, 25))
        self.MskFl = wx.TextCtrl(panel, 
#                                 value='Please select mask file.',
                                 size=(350, 25))
        self.BkgdFl = wx.TextCtrl(panel, 
#                                 value='Please select background file.',
                                 size=(350, 25))


        hlpBtn = wx.Button(panel, wx.ID_HELP   )
        okBtn  = wx.Button(panel, wx.ID_OK     )
        canBtn = wx.Button(panel, wx.ID_CANCEL )

        self.Bind(wx.EVT_BUTTON,   self.onBROWSE1,  fileBtn1 )
        self.Bind(wx.EVT_BUTTON,   self.onBROWSE2,  fileBtn2 )
        self.Bind(wx.EVT_BUTTON,   self.onBROWSE3,  fileBtn3 )

        sizer = wx.GridBagSizer(5, 6)

        sizer.Add(caliTtl,     pos = ( 1,1)               )
        sizer.Add(self.CalFl,  pos = ( 2,1), span = (1,4) )
        sizer.Add(fileBtn1,    pos = ( 3,1)               )
        sizer.Add(maskTtl,     pos = ( 5,1)               )
        sizer.Add(self.MskFl,  pos = ( 6,1), span = (1,4) )
        sizer.Add(fileBtn2,    pos = ( 7,1)               )
        sizer.Add(bkgdTtl,     pos = ( 9,1)               )
        sizer.Add(self.BkgdFl, pos = (10,1), span = (1,4) )
        sizer.Add(fileBtn3,    pos = (11,1)               )
        sizer.Add(hlpBtn,      pos = (13,1)               )
        sizer.Add(okBtn,       pos = (13,3)               )
        sizer.Add(canBtn,      pos = (13,2)               )        
        sizer.AddGrowableCol(2)
        panel.SetSizer(sizer)       

    def onBROWSE1(self, event): 
        wildcards = 'pyFAI calibration (*.poni)|*.poni|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD calibration file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            self.CalFl.Clear()
            self.CalFl.SetValue(str(path))
            self.CaliPath = path

    def onBROWSE2(self, event): 
        wildcards = 'pyFAI mask (*.edf)|*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD mask file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            self.MskFl.Clear()
            self.MskFl.SetValue(str(path))
            self.MaskPath = path
            
    def onBROWSE3(self, event): 
        wildcards = 'pyFAI background (*.edf)|*.edf|All files (*.*)|*.*'
        dlg = wx.FileDialog(self, message='Choose XRD background file',
                           defaultDir=os.getcwd(),
                           wildcard=wildcards, style=wx.FD_OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        
        if read:
            self.BkgdFl.Clear()
            self.BkgdFl.SetValue(str(path))
            self.BkgdPath = path


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

if __name__ == '__main__':
    DebugViewer().run()
