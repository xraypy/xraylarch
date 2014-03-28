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

__version__ = '7 (28-March-2014)'

import os
import sys
import time
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

import h5py
import numpy as np
import scipy.stats as stats

from wxmplot import PlotFrame

from wxutils import (SimpleText, EditableListBox, FloatCtrl, Font,
                     pack, Popup, Button, MenuItem, Choice, Check,
                     GridPanel)

import larch
from larch.larchlib import read_workdir, save_workdir
from larch.wxlib import larchframe
larch.use_plugin_path('wx')
larch.use_plugin_path('io')
larch.use_plugin_path('xrfmap')
larch.use_plugin_path('std')

from xrfdisplay import XRFDisplayFrame
from mapimageframe import MapImageFrame

from fileutils import nativepath

from xrm_mapfile import (GSEXRM_MapFile, GSEXRM_FileStatus,
                         GSEXRM_Exception, GSEXRM_NotOwner)

CEN = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
RIGHT = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
ALL_CEN =  wx.ALL|CEN
ALL_LEFT =  wx.ALL|LEFT
ALL_RIGHT =  wx.ALL|RIGHT

FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

FILE_WILDCARDS = "X-ray Maps (*.h5)|*.h5|All files (*.*)|*.*"

# FILE_WILDCARDS = "X-ray Maps (*.0*)|*.0&"

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


class AreaStatsFrame(wx.Frame) :
    """Shows Table of Statistics for a Map Area"""
    def __init__(self, parent, xrmfile, areaname):
        self.parent = parent
        self.xrmfile = xrmfile
        path, fname = os.path.split(xrmfile.filename)
        self.areaname = areaname
        self.area = xrmfile.get_area(name=areaname).value
        self.title = "Statistics for area '%s', map '%s'" % (areaname,
                                                             fname)
        
        wx.Frame.__init__(self, None, -1, self.title,
                          size=(450, 450), style=FRAMESTYLE)

        stats_thread = Thread(target=self.get_stats)
        self.draw_frame()
        self.Show()
        self.Raise()
        stats_thread.start()
        
    def draw_frame(self):
        d_names = [str(d) for d in self.xrmfile.xrfmap['roimap/det_name']]
        self.wids = {}
        sizer = wx.GridBagSizer(len(d_names), 7)
        panel = scrolled.ScrolledPanel(self)
        
        ir = 0
        sizer.Add(SimpleText(panel, self.title, colour='#880000'),
                  (0, 0), (1, 6), ALL_CEN)

        ir = 1
        sizer.Add(SimpleText(panel, '%i points' % self.area.sum()),
                  (ir, 0), (1, 2), ALL_CEN)
        sizer.Add(SimpleText(panel, 'values in counts/sec'),
                  (ir, 2), (1, 2), ALL_CEN)
                
        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(600, 3),
                                style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 6), ALL_CEN)

        ir += 1
        for j, txt in enumerate(('ROI', 'Mean', 'Sigma', 'Median',
                            'Mode', 'Min', 'Max')):
            sizer.Add(SimpleText(panel, txt), (ir, j), (1, 1), ALL_CEN)

        opts = {}   ## {'size': (120, -1)}
        for idet, name in enumerate(d_names):
            ir += 1
            roi = SimpleText(panel, name, **opts)
            wave, wsig = SimpleText(panel, '', **opts), SimpleText(panel, '', **opts)
            wmed, wmod = SimpleText(panel, '', **opts), SimpleText(panel, '', **opts)
            wmin, wmax = SimpleText(panel, '', **opts), SimpleText(panel, '', **opts)

            sizer.Add(roi,  (ir, 0), (1, 1), ALL_CEN)
            sizer.Add(wave, (ir, 1), (1, 1), ALL_CEN)
            sizer.Add(wsig, (ir, 2), (1, 1), ALL_CEN)
            sizer.Add(wmed, (ir, 3), (1, 1), ALL_CEN)
            sizer.Add(wmod, (ir, 4), (1, 1), ALL_CEN)
            sizer.Add(wmin, (ir, 5), (1, 1), ALL_CEN)
            sizer.Add(wmax, (ir, 6), (1, 1), ALL_CEN)
            self.wids[idet] = roi, wave, wsig, wmed, wmod, wmin, wmax
            
        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(600, 3),
                                style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 6), ALL_CEN)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)
        pack(self, mainsizer)
        
    
    def get_stats(self):
        # self.stats = self.xrmfile.get_area_stats(self.areaname)
        area   = self.area
        xrfmap = self.xrmfile.xrfmap
        d_addrs = [d.lower() for d in xrfmap['roimap/det_address']]
        d_names = [d for d in xrfmap['roimap/det_name']]
        # count times
        ctime = [1.e-6*xrfmap['roimap/det_raw'][:,:,0][area]]
        for i in range(xrfmap.attrs['N_Detectors']):
            tname = 'det%i/realtime' % (i+1)
            ctime.append(1.e-6*xrfmap[tname].value[area])
        
        for idet, dname in enumerate(d_names):
            daddr = d_addrs[idet]
            det = 0
            if 'mca' in daddr:
                det = 1
                words = daddr.split('mca')
                if len(words) > 1:
                    det = int(words[1].split('.')[0])
            if idet == 0:
                d = ctime[0]
            else:
                d = xrfmap['roimap/det_raw'][:,:,idet][area]/ctime[det]

            try:
                hmean, gmean = stats.gmean(d), stats.hmean(d)
                skew, kurtosis = stats.skew(d), stats.kurtosis(d)
            except ValueError:
                hmean, gmean, skew, kurtosis = 0, 0, 0, 0
            mode = stats.mode(d)

            wx.CallAfter(self.wids[idet][1].SetLabel, "%.1f" % d.mean())
            wx.CallAfter(self.wids[idet][2].SetLabel, "%.1f" % d.std())
            wx.CallAfter(self.wids[idet][3].SetLabel, "%.1f" % np.median(d))
            wx.CallAfter(self.wids[idet][5].SetLabel, "%.1f" % d.min())
            wx.CallAfter(self.wids[idet][6].SetLabel, "%.1f" % d.max())
            # print d.mean(), d.std(), np.median(d), d.min(), d.max()


            #roi, wave, wsig, wmed, wmod, wmin, wmax
            #roidata.append((dname, len(d), d.mean(), d.std(), np.median(d),
            #                stats.mode(d), d.min(), d.max(), 
            #                gmean, hmean, skew, kurtosis))

        

        

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
        txt = '''Enter Math Expressions for Map:
 a+b,  (a-b)/c, log10(a+0.1),  etc'''

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
            sizer.Add(SimpleText(self, "%s = " % varname),    (ir, 0), (1, 1), ALL_CEN, 2)
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
        self.varrange[varname].SetLabel("Range = [%g: %g]" % (map.min(), map.max()))

    def update_xrfmap(self, xrfmap):
        self.set_roi_choices(xrfmap)

    def set_roi_choices(self, xrfmap):
        rois = ['1'] + list(xrfmap['roimap/sum_name'])
        for wid in self.varroi.values():
            wid.SetChoices(rois)

    def set_file_choices(self, fnames):
        for wid in self.varfile.values():
            wid.SetChoices(fnames)

    def onShowMap(self, evt, new=True):
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
    label  = 'Simple ROI Map'
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
        self.Add(self.hotcols, dcol=2, style=LEFT)
        self.Add(self.show_new,  dcol=2, newrow=True, style=LEFT)
        self.Add(self.show_old,  dcol=2,              style=LEFT)
        self.Add(self.show_cor,  dcol=2, newrow=True, style=LEFT)
        self.pack()

    def onClose(self):
        for p in self.plotframes:
            try:
                p.Destroy()
            except:
                pass

    def onLasso(self, selected=None, mask=None, data=None, xrmfile=None, **kws):
        if xrmfile is None:
            xrmfile = self.owner.current_file
        ny, nx, npos = xrmfile.xrfmap['positions/pos'].shape
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

        map1 = datafile.get_roimap(roiname1, det=det, no_hotcols=no_hotcols,
                                   dtcorrect=dtcorrect).flatten()
        map2 = datafile.get_roimap(roiname2, det=det, no_hotcols=no_hotcols,
                                   dtcorrect=dtcorrect).flatten()

        path, fname = os.path.split(datafile.filename)
        title ='%s: %s vs %s' %(fname, roiname2, roiname1)
        pframe = PlotFrame(title=title, output_title=title)
        pframe.plot(map2, map1, xlabel=roiname2, ylabel=roiname1,
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
        roiname1 = self.roi1.GetStringSelection()
        roiname2 = self.roi2.GetStringSelection()
        map      = datafile.get_roimap(roiname1, det=det, no_hotcols=no_hotcols,
                                       dtcorrect=dtcorrect)
        title    = roiname1

        if roiname2 != '1':
            mapx = datafile.get_roimap(roiname2, det=det, no_hotcols=no_hotcols,
                                       dtcorrect=dtcorrect)
            op = self.op.GetStringSelection()
            if   op == '+': map +=  mapx
            elif op == '-': map -=  mapx
            elif op == '*': map *=  mapx
            elif op == '/': map /=  mapx

            title = "(%s) %s (%s)" % (roiname1, op, roiname2)

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

        if len(self.owner.im_displays) == 0 or new:
            iframe = self.owner.add_imdisplay(title, det=det)
        self.owner.display_map(map, title=title, info=info, x=x, y=y,
                               det=det, xrmfile=datafile)

    def update_xrfmap(self, xrfmap):
        self.set_roi_choices(xrfmap)

    def set_roi_choices(self, xrfmap):
        rois = ['1'] + list(xrfmap['roimap/sum_name'])
        self.roi1.SetChoices(rois[1:])
        self.roi2.SetChoices(rois)

class TriColorMapPanel(GridPanel):
    """Panel of Controls for choosing what to display a 3 color ROI map"""
    label  = '3-Color ROI Map'    
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

        self.pack()

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

        r = self.rcol.GetStringSelection()
        g = self.gcol.GetStringSelection()
        b = self.bcol.GetStringSelection()
        i0 = self.i0col.GetStringSelection()
        mapshape= datafile.xrfmap['roimap/sum_cor'][:, :, 0].shape
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
        i0map[np.where(i0map<=0)] = i0min
        i0map = i0map/i0map.max()

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

        map = np.array([rmap/i0map, gmap/i0map, bmap/i0map])
        map = map.swapaxes(0, 2).swapaxes(0, 1)
        if len(self.owner.im_displays) == 0 or new:
            iframe = self.owner.add_imdisplay(title, det=det)
        self.owner.display_map(map, title=title, subtitles=subtitles,
                               x=x, y=y, det=det, xrmfile=datafile)

    def update_xrfmap(self, xrfmap):
        self.set_roi_choices(xrfmap)

    def set_roi_choices(self, xrfmap):
        rois = ['1'] + list(xrfmap['roimap/sum_name'])
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

        sizer.Add(wx.StaticLine(self, size=(400, 3),
                                style=wx.LI_HORIZONTAL),
                  (0, 0), (1, 2), 1)

        for label in ('Scan Started', 'User Comments 1', 'User Comments 2',
                      'Scan Fast Motor', 'Scan Slow Motor', 'Dwell Time',
                      'Sample Fine Stages',
                      'Sample Stage X',     'Sample Stage Y',
                      'Sample Stage Z',     'Sample Stage Theta',
                      'Ring Current', 'X-ray Energy',  'X-ray Intensity (I0)'):
            
            ir += 1
            thislabel        = SimpleText(self, '%s:' % label,
                                          style=wx.LEFT, size=(125, -1))
            self.wids[label] = SimpleText(self, ' ' ,
                                          style=wx.LEFT, size=(300, -1)) 
            
            sizer.Add(thislabel,        (ir, 0), (1, 1), 1)
            sizer.Add(self.wids[label], (ir, 1), (1, 1), 1)
 
        sizer.Add(wx.StaticLine(self, size=(400, 3),
                                style=wx.LI_HORIZONTAL),
                  (ir+1, 0), (1, 2), 1)

        pack(self, sizer)
        self.SetupScrolling()


    def update_xrfmap(self, xrfmap):
        self.wids['Scan Started'].SetLabel( xrfmap.attrs['Start_Time'])

        comments = xrfmap['config/scan/comments'].value.split('\n', 2)
        for i, comm in enumerate(comments):
            self.wids['User Comments %i' %(i+1)].SetLabel(comm)

        pos_addrs = [str(x) for x in xrfmap['config/positioners'].keys()]
        pos_label = [str(x.value) for x in xrfmap['config/positioners'].values()]

        scan_pos1 = str(xrfmap['config/scan/pos1'].value)
        scan_pos2 = str(xrfmap['config/scan/pos2'].value)
        i1 = pos_addrs.index(scan_pos1)
        i2 = pos_addrs.index(scan_pos2)

        start1 = float(xrfmap['config/scan/start1'].value)
        start2 = float(xrfmap['config/scan/start2'].value)
        stop1 = float(xrfmap['config/scan/stop1'].value)
        stop2 = float(xrfmap['config/scan/stop2'].value)
        
        step1 = float(xrfmap['config/scan/step1'].value)
        step2 = float(xrfmap['config/scan/step2'].value)

        npts1 = int((abs(stop1 - start1) + 1.1*step1)/step1)
        npts2 = int((abs(stop2 - start2) + 1.1*step2)/step2)

        sfmt = "%s: [%.4f:%.4f], step=%.4f, %i pixels" 
        scan1 = sfmt % (pos_label[i1], start1, stop1, step1, npts1)
        scan2 = sfmt % (pos_label[i2], start2, stop2, step2, npts2)

        rowtime = float(xrfmap['config/scan/time1'].value)

        self.wids['Scan Fast Motor'].SetLabel(scan1)
        self.wids['Scan Slow Motor'].SetLabel(scan2)
        self.wids['Dwell Time'].SetLabel("%.3f sec per pixel" % (rowtime/(1+npts1)))

        env_names = list(xrfmap['config/environ/name'])
        env_vals  = list(xrfmap['config/environ/value'])
        env_addrs = list(xrfmap['config/environ/address'])
        
        fines = {'X': '?', 'Y': '?'}
        i0vals = {'flux':'?', 'current':'?'}
        cur_energy = ''
        
        for name, addr, val in zip(env_names, env_addrs, env_vals):
            name = str(name).lower()
            if 'ring current' in name:
                self.wids['Ring Current'].SetLabel("%s mA" % val)
            elif 'mono energy' in name and cur_energy=='':
                self.wids['X-ray Energy'].SetLabel("%s eV" % val)
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
                        self.wids['Sample Stage X'].SetLabel("%s mm" % val)
                    elif 'stage y' in plab:
                        self.wids['Sample Stage Y'].SetLabel("%s mm" % val)
                    elif 'stage z' in plab:
                        self.wids['Sample Stage Z'].SetLabel("%s mm" % val)
                    elif 'theta' in plab:
                        self.wids['Sample Stage Theta'].SetLabel("%s deg" % val)
                    elif 'x' in plab:
                        fines['X'] = val
                    elif 'y' in plab:
                        fines['Y'] = val

        i0val = 'Flux=%(flux)s Hz, I0 Current=%(current)s uA' % i0vals
        self.wids['X-ray Intensity (I0)'].SetLabel(i0val) 
        self.wids['Sample Fine Stages'].SetLabel('X, Y = %(X)s, %(Y)s mm' % (fines)) 
                
    def onClose(self):
        pass



class MapAreaPanel(wx.Panel):
    label  = 'Map Areas'    
    delstr = """   Delete Area '%s'?

WARNING: This cannot be undone!

"""

    def __init__(self, parent, owner, **kws):
        wx.Panel.__init__(self, parent, -1, **kws)
        self.owner = owner

        sizer = wx.GridBagSizer(8, 5)
        self.choices = {}
        self.choice = Choice(self, choices=[], size=(180, -1),
                             action=self.onSelect)
        self.desc  = wx.TextCtrl(self, -1,   '', size=(180, -1))
        self.info  = wx.StaticText(self, -1, '', size=(180, -1))

        self.report = Button(self, 'Show Report', size=(120, -1),
                             action=self.onReport)

        self.onmap = Button(self, 'Show on Map', size=(120, -1),
                            action=self.onShow)
        self.clear = Button(self, 'Clear on Map', size=(120, -1),
                            action=self.onClear)
        self.xrf   = Button(self, 'Show Spectrum (Foreground)',
                            size=(200, -1),
                            action=self.onXRF)
        self.xrf2  = Button(self, 'Show Spectrum (Background)',
                            size=(200, -1),
                            action=partial(self.onXRF, as_mca2=True))

        self.delete = Button(self, 'Delete Area', size=(100, -1),
                                      action=self.onDelete)
        self.update = Button(self, 'Save Label', size=(100, -1),
                                      action=self.onLabel)

        def txt(s):
            return SimpleText(self, s)
        sizer.Add(txt('Defined Map Areas'), (0, 0), (1, 3), ALL_CEN, 2)
        sizer.Add(self.info,                (0, 3), (1, 2), ALL_RIGHT, 2)
        sizer.Add(txt('Area: '),            (1, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.choice,              (1, 1), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.delete,              (1, 3), (1, 1), ALL_LEFT, 2)
        sizer.Add(txt('New Label: '),       (2, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.desc,                (2, 1), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.update,              (2, 3), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.report,              (3, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.onmap,               (3, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.clear,               (3, 2), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.xrf,                 (4, 0), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.xrf2,                (5, 0), (1, 2), ALL_LEFT, 2)


        sizer.Add(wx.StaticLine(self, size=(350, 3),
                                style=wx.LI_HORIZONTAL),
                  (6, 0), (1, 4), ALL_LEFT, 2)

        pack(self, sizer)

    # def get_stats(self, aname):
    #     self.stats = self.owner.current_file.get_area_stats(aname)
        
    def onReport(self, event=None):
        aname = self._getarea()
        f = AreaStatsFrame(self, self.owner.current_file, aname)
#         
# 
#         self.stats = None
#         stats_thread = Thread(target=self.get_stats, args=(aname,))
#         self.owner.message("Gathering Statistics for area '%s'..." % aname)
#         stats_thread.start()
#         stats_thread.join()
#         self.owner.message("Got Statistics for area '%s'" % aname)        
#         print 'Need to raise ROI Report Frame: ', aname
#         print 'name, length, mean, std, median, mode, minimum, maximum, gmean, hmean, skew, kurtosis'
#         for (name, length, mean, std, median, mode, xmin, 
#              xmax, gmean, hmean, skew, kurtosis) in self.stats:
#             print "%s: %i %.1f %.1f %.1f" % (name, length, mean, std, median)
# ;            

    def update_xrfmap(self, xrfmap):
        self.set_area_choices(xrfmap, show_last=True)
        
    def set_area_choices(self, xrfmap, show_last=False):
        areas = xrfmap['areas']
        c = self.choice
        c.Clear()
        self.choices =  dict([(areas[a].attrs['description'], a) for a in areas])
        choice_labels = [areas[a].attrs['description'] for a in areas]

        c.AppendItems(choice_labels)
        if len(self.choices) > 0:
            idx = 0
            if show_last: idx = len(self.choices)-1
            this_label = choice_labels[idx]
            c.SetStringSelection(this_label)
            self.desc.SetValue(this_label)

    def _getarea(self):
        dfile = self.owner.current_file
        return self.choices[self.choice.GetStringSelection()]

    def onSelect(self, event=None):
        aname = self._getarea()
        area  = self.owner.current_file.xrfmap['areas/%s' % aname]
        npix = len(area.value[np.where(area.value)])
        self.info.SetLabel("%i Pixels" % npix)
        self.desc.SetValue(area.attrs['description'])

    def onLabel(self, event=None):
        aname = self._getarea()
        area  = self.owner.current_file.xrfmap['areas/%s' % aname]
        new_label = str(self.desc.GetValue())
        area.attrs['description'] = new_label
        self.owner.current_file.h5root.flush()
        self.set_area_choices(self.owner.current_file.xrfmap)
        self.choice.SetStringSelection(new_label)
        self.desc.SetValue(new_label)

    def onShow(self, event=None):
        aname = self._getarea()
        area  = self.owner.current_file.xrfmap['areas/%s' % aname]
        if len(self.owner.im_displays) > 0:
            imd = self.owner.im_displays[-1]
            imd.panel.add_highlight_area(area.value,
                                         label=area.attrs['description'])

    def onDelete(self, event=None):
        aname = self._getarea()
        erase = Popup(self.owner, self.delstr % aname,
                      'Delete Area?', style=wx.YES_NO)
        if erase:
            xrfmap = self.owner.current_file.xrfmap
            del xrfmap['areas/%s' % aname]
            self.set_area_choices(xrfmap)

    def onClear(self, event=None):
        if len(self.owner.im_displays) > 0:
            imd = self.owner.im_displays[-1]
            for area in imd.panel.conf.highlight_areas:
                for w in area.collections + area.labelTexts:
                    w.remove()

            imd.panel.conf.highlight_areas = []
            imd.panel.redraw()

    def _getmca_area(self, areaname):
        self._mca = self.owner.current_file.get_mca_area(areaname)

    def onXRF(self, event=None, as_mca2=False):
        aname = self._getarea()
        xrmfile = self.owner.current_file
        area  = xrmfile.xrfmap['areas/%s' % aname]
        label = area.attrs['description']
        self._mca  = None
        mca_thread = Thread(target=self._getmca_area, args=(aname,))
        mca_thread.start()
        self.owner.show_XRFDisplay(xrmfile=xrmfile)
        mca_thread.join()

        pref, fname = os.path.split(self.owner.current_file.filename)
        npix = len(area.value[np.where(area.value)])
        self._mca.title = "%s, Area=%s (%i Pixels)" % (fname,
                                                       label, npix)
        self.owner.xrfdisplay.plotmca(self._mca, as_mca2=as_mca2)

class MapViewerFrame(wx.Frame):
    cursor_menulabels = {'lasso': ('Select Points for XRF Spectra\tCtrl+X',
                                   'Left-Drag to select points for XRF Spectra')}

    def __init__(self, conffile=None,  _larch=None, **kwds):

        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, None, -1, size=(700, 450),  **kwds)

        self.data = None
        self.filemap = {}
        self.im_displays = []
        self.plot_displays = []
        self.larch = _larch
        self.xrfdisplay = None
        self.larch_buffer = None
        self.watch_files = False
        self.file_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onFileWatchTimer, self.file_timer)
        self.files_in_progress = []
        
        self.SetTitle("GSE XRM MapViewer")
        self.SetFont(Font(9))

        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ["Initializing....", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        self.htimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer, self.htimer)
        self.h5convert_done = True
        self.h5convert_irow = 0
        self.h5convert_nrow = 0
        read_workdir('gsemap.dat')
        # self.onFolderSelect(evt=None)
        
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

    def get_mca_area(self, det, mask, xrmfile=None):
        if xrmfile is None:
            xrmfile = self.current_file
        aname = xrmfile.add_area(mask)
        self.sel_mca = xrmfile.get_mca_area(aname, det=det)

    def lassoHandler(self, mask=None, det=None, xrmfile=None, **kws):
        mca_thread = Thread(target=self.get_mca_area,
                            args=(det, mask), kwargs={'xrmfile':xrmfile})
        mca_thread.start()

        self.show_XRFDisplay(xrmfile=xrmfile)
        mca_thread.join()

        if hasattr(self, 'sel_mca'):
            path, fname = os.path.split(xrmfile.filename)
            aname = self.sel_mca.areaname
            area  = xrmfile.xrfmap['areas/%s' % aname]
            npix  = len(area.value[np.where(area.value)])
            title = "XRF Spectra:  %s, Area=%s,  %i Pixels" % (fname, aname, npix)

            self.xrfdisplay.plotmca(self.sel_mca, title=title)
            # SET AREA CHOICE
            for p in self.nbpanels:
                if hasattr(p, 'update_xrfmap'):
                    p.update_xrfmap(self.current_file.xrfmap)


    def show_XRFDisplay(self, do_raise=True, clear=True, xrmfile=None):
        "make sure plot frame is enabled, and visible"
        if xrmfile is None:
            xrmfile = self.current_file
        if self.xrfdisplay is None:
            self.xrfdisplay = XRFDisplayFrame(_larch=self.larch,
                                              gsexrmfile=xrmfile)
        try:
            self.xrfdisplay.Show()

        except PyDeadObjectError:
            self.xrfdisplay = XRFDisplayFrame(_larch=self.larch,
                                              gsexrmfile=xrmfile)
            self.xrfdisplay.Show()

        if do_raise:
            self.xrfdisplay.Raise()
        if clear:
            self.xrfdisplay.panel.clear()
            self.xrfdisplay.panel.reset_config()

    def add_imdisplay(self, title, det=None):
        on_lasso = partial(self.lassoHandler, det=det)
        imframe = MapImageFrame(output_title=title,
                                lasso_callback=on_lasso,
                                cursor_labels = self.cursor_menulabels)
        self.im_displays.append(imframe)

    def display_map(self, map, title='', info='', x=None, y=None,
                    det=None, subtitles=None, xrmfile=None):
        """display a map in an available image display"""
        displayed = False
        lasso_cb = partial(self.lassoHandler, det=det, xrmfile=xrmfile)
        while not displayed:
            try:
                imd = self.im_displays.pop()
                imd.display(map, title=title, x=x, y=y,
                            subtitles=subtitles, det=det, xrmfile=xrmfile)
                #for col, wid in imd.wid_subtitles.items():
                #    wid.SetLabel("%s: %s" % (col.title(), subtitles[col]))
                imd.lass_callback = lasso_cb
                displayed = True
            except IndexError:
                imd = MapImageFrame(output_title=title,
                                    lasso_callback=lasso_cb,
                                    cursor_labels = self.cursor_menulabels)
                imd.display(map, title=title, x=x, y=y, subtitles=subtitles,
                            det=det, xrmfile=xrmfile)
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

    def ShowFile(self, evt=None, filename=None,  **kws):
        if filename is None and evt is not None:
            filename = evt.GetString()

        if not self.h5convert_done or filename not in self.filemap:
            return
        if (self.check_ownership(filename) and
            self.filemap[filename].folder_has_newdata()):
            self.process_file(filename)

        self.current_file = self.filemap[filename]
        ny, nx, npos = self.filemap[filename].xrfmap['positions/pos'].shape
        self.title.SetLabel("%s: (%i x %i)" % (filename, nx, ny))

        fnames = self.filelist.GetItems()

        for p in self.nbpanels:
            if hasattr(p, 'update_xrfmap'):
                p.update_xrfmap(self.current_file.xrfmap)            
            if hasattr(p, 'set_file_choices'):
                p.set_file_choices(fnames)

    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "&Open Map File\tCtrl+O",
                 "Read Map File",  self.onReadFile)
        MenuItem(self, fmenu, "&Open Map Folder\tCtrl+F",
                 "Read Map Folder",  self.onReadFolder)

        MenuItem(self, fmenu, 'Change &Working Folder',
                  "Choose working directory",
                  self.onFolderSelect)
        fmenu.AppendSeparator()
        MenuItem(self, fmenu, "Show Larch Buffer",
                  "Show Larch Programming Buffer",
                  self.onShowLarchBuffer)

        mid = wx.NewId()
        fmenu.Append(mid,  '&Watch HDF5 Files\tCtrl+W',  'Watch HDF5 Files', kind=wx.ITEM_CHECK)
        fmenu.Check(mid, False)
        self.Bind(wx.EVT_MENU, self.onWatchFiles, id=mid)

        MenuItem(self, fmenu, "&Quit\tCtrl+Q",
                  "Quit program", self.onClose)

        hmenu = wx.Menu()
        MenuItem(self, hmenu, 'About', 'About MapViewer', self.onAbout)

        
        self.menubar.Append(fmenu, "&File")
        self.menubar.Append(hmenu, "&Help")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)
        

    def onShowLarchBuffer(self, evt=None):
        if self.larch_buffer is None:
            self.larch_buffer = larchframe.LarchFrame(_larch=self.larch)
        
        self.larch_buffer.Show()
        self.larch_buffer.Raise()
         
    def onFolderSelect(self, evt=None):
        style = wx.DD_DIR_MUST_EXIST|wx.DD_DEFAULT_STYLE
        dlg = wx.DirDialog(self, "Select Working Directory:", os.getcwd(),
                           style=style)

        if dlg.ShowModal() == wx.ID_OK:
            basedir = os.path.abspath(str(dlg.GetPath()))
            try:
                os.chdir(nativepath(basedir))
            except OSError:
                print( 'Changed folder failed')
                pass
        save_workdir('gsemap.dat')
        dlg.Destroy()

    def onAbout(self, evt):
        about = """GSECARS X-ray Microprobe Map Viewer:
Matt Newville <newville @ cars.uchicago.edu>
    MapViewer version: %s
    Built with X-ray Larch version: %s
    """  % (__version__, larch.__version__)

        dlg = wx.MessageDialog(self, about, "About GSE XRM MapViewer",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

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
                self.larch_buffer.Destroy()
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

        dlg = wx.DirDialog(self, message="Read Map Folder",
                           defaultPath=os.getcwd(),
                           style=wx.OPEN)

        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
        dlg.Destroy()
        if read:
            try:
                xrmfile = GSEXRM_MapFile(folder=str(path))
            except:
                Popup(self, NOT_GSEXRM_FOLDER % str(path),
                     "Not a Map folder")
                return
            parent, fx = os.path.split(str(path))
            self.add_xrmfile(xrmfile, parent)

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
        os.chdir(nativepath(parent))
        save_workdir(nativepath(parent))
        
    def onReadFile(self, evt=None):
        if not self.h5convert_done:
            print('cannot open file while processing a map folder')
            return

        dlg = wx.FileDialog(self, message="Read Map File",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS,
                            style=wx.OPEN)
        path, read = None, False
        if dlg.ShowModal() == wx.ID_OK:
            read = True
            path = dlg.GetPath().replace('\\', '/')
            if path in self.filemap:
                read = Popup(self, "Re-read file '%s'?" % path, 'Re-read file?',
                             style=wx.YES_NO)

        dlg.Destroy()

        if read:
            parent, fname = os.path.split(path)
            try:
                xrmfile = GSEXRM_MapFile(filename=str(path))
            except:
                Popup(self, NOT_GSEXRM_FILE % str(path),
                     "Not a Map folder")
                return
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

    def process_file(self, filename):
        """Request processing of map file.
        This can take awhile, so is done in a separate thread,
        with updates displayed in message bar
        """
        xrm_map = self.filemap[filename]
        if xrm_map.status == GSEXRM_FileStatus.created:
            xrm_map.initialize_xrfmap()

        if xrm_map.dimension is None and isGSEXRM_MapFolder(self.folder):
            xrm_map.read_master()

        if self.filemap[filename].folder_has_newdata():
            self.files_in_progress.append(filename)
            self.h5convert_fname = filename
            self.h5convert_done = False
            self.h5convert_irow, self.h5convert_nrow = 0, 0
            self.h5convert_t0 = time.time()
            self.htimer.Start(150)
            self.h5convert_thread = Thread(target=self.new_mapdata,
                                           args=(filename,))
            self.h5convert_thread.start()
            # self.new_mapdata(filename)

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
                t1 = time.time()
                xrm_map.add_rowdata(rowdat)
                t2 = time.time()
                irow  = irow + 1
                try:
                    wx.Yield()
                except:
                    pass

        xrm_map.resize_arrays(xrm_map.last_row+1)
        xrm_map.h5root.flush()
        self.h5convert_done = True
        time.sleep(0.025)

    def message(self, msg, win=0):
        self.statusbar.SetStatusText(msg, win)

    def check_ownership(self, fname):
        """
        check whether we're currently owner of the file.
        this is important!! HDF5 files can be corrupted.
        """
        if not self.filemap[fname].check_hostid():
            if Popup(self, NOT_OWNER_MSG % fname,
                     'Not Owner of HDF5 File', style=wx.YES_NO):
                self.filemap[fname].claim_hostid()
        return self.filemap[fname].check_hostid()

class MapViewer(wx.App):
    def __init__(self, **kws):
        wx.App.__init__(self, **kws)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = MapViewerFrame()
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

if __name__ == "__main__":
    DebugViewer().run()
