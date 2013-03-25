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
import os
import sys
import time
from threading import Thread

import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection
from wx._core import PyDeadObjectError

import h5py
import numpy as np

from wxmplot import ImageFrame
import larch

sys.path.insert(0, larch.plugin_path('wx'))
from xrfdisplay import XRFDisplayFrame

from wxutils import (SimpleText, EditableListBox, FloatCtrl,
                     Closure, pack, popup,
                     add_button, add_menu, add_choice)

sys.path.insert(0, larch.plugin_path('xrf'))
from mca import MCA

sys.path.insert(0, larch.plugin_path('io'))
from fileutils import nativepath

sys.path.insert(0, larch.plugin_path('xrfmap'))

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


def set_choices(choicebox, choices):
    index = 0
    try:
        current = choicebox.GetStringSelection()
        if current in choices:
            index = choices.index(current)
    except:
        pass
    choicebox.Clear()
    choicebox.AppendItems(choices)
    choicebox.SetStringSelection(choices[index])


class SimpleMapPanel(wx.Panel):
    """Panel of Controls for choosing what to display a simple ROI map"""

    def __init__(self, parent, owner, **kws):
        wx.Panel.__init__(self, parent, -1, **kws)
        self.owner = owner

        sizer = wx.GridBagSizer(8, 5)

        self.roi1 = add_choice(self, choices=[], size=(120, -1))
        self.roi2 = add_choice(self, choices=[], size=(120, -1))
        self.scale = FloatCtrl(self, precision=4, value=1, size=(80,-1))
        self.op   = add_choice(self, choices=['/', '*', '-', '+'], size=(80, -1))
        self.det  = add_choice(self, choices=['sum', '1', '2', '3', '4'], size=(80, -1))
        self.newid  = wx.CheckBox(self, -1, 'Reuse Previous Display?')
        self.cor  = wx.CheckBox(self, -1, 'Correct Deadtime?')
        self.newid.SetValue(1)
        self.cor.SetValue(1)
        self.op.SetSelection(0)
        self.det.SetSelection(0)
        self.show = add_button(self, 'Show Map', size=(90, -1), action=self.onShowMap)

        ir = 0
        sizer.Add(SimpleText(self, 'Detector'),          (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Map 1'),             (ir, 1), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Operator'),          (ir, 2), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Map 2'),             (ir, 3), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Factor'),            (ir, 5), (1, 1), ALL_CEN, 2)

        ir += 1
        sizer.Add(self.det,           (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.roi1,          (ir, 1), (1, 1), ALL_CEN, 2)
        sizer.Add(self.op,            (ir, 2), (1, 1), ALL_CEN, 2)
        sizer.Add(self.roi2,          (ir, 3), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, '/', size=(10,-1)), (ir, 4), (1, 1), CEN, 2)
        sizer.Add(self.scale,         (ir, 5), (1, 1), ALL_CEN, 2)

        ir += 1
        sizer.Add(self.cor,   (ir,   0), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.newid, (ir,   2), (1, 4), ALL_LEFT, 2)
        sizer.Add(self.show,  (ir+1, 0), (1, 1), ALL_LEFT, 2)

        pack(self, sizer)


    def onShowMap(self, event=None):
        datafile  = self.owner.current_file
        det =self.det.GetStringSelection()
        if det == 'sum':
            det =  None
        else:
            det = int(det)
        dtcorrect = self.cor.IsChecked()
        roiname1 = self.roi1.GetStringSelection()
        roiname2 = self.roi2.GetStringSelection()
        scale    = self.scale.GetValue()
        if abs(scale) < 1.e-8: scale = 1.e-8

        map      = datafile.get_roimap(roiname1, det=det, dtcorrect=dtcorrect)
        title    = roiname1

        if roiname2 != '':
            mapx = datafile.get_roimap(roiname2, det=det, dtcorrect=dtcorrect)
            op = self.op.GetStringSelection()
            if   op == '+': map +=  mapx/scale
            elif op == '-': map -=  mapx/scale
            elif op == '*': map *=  mapx/scale
            elif op == '/': map /=  mapx/scale

            title = "(%s) %s (%s/%g)" % (roiname1, op, roiname2, scale)

        try:
            x = datafile.get_pos(0, mean=True)
        except:
            x = None
        try:
            y = datafile.get_pos(1, mean=True)
        except:
            y = None

        title = '%s: %s' % (datafile.filename, title)
        info  = 'Intensity: [%g, %g]' %(map.min(), map.max())
        if len(self.owner.im_displays) == 0 or not self.newid.IsChecked():
            iframe = self.owner.add_imdisplay(title, det=det)
        self.owner.display_map(map, title=title, info=info, x=x, y=y, det=det)

class TriColorMapPanel(wx.Panel):
    """Panel of Controls for choosing what to display a 3 color ROI map"""
    def __init__(self, parent, owner, **kws):
        wx.Panel.__init__(self, parent, -1, **kws)
        self.owner = owner
        sizer = wx.GridBagSizer(8, 8)

        self.SetMinSize((425, 275))

        self.rchoice = add_choice(self, choices=[], size=(120, -1),
                                  action=Closure(self.onSetRGBScale, color='r'))
        self.gchoice = add_choice(self, choices=[], size=(120, -1),
                                  action=Closure(self.onSetRGBScale, color='g'))
        self.bchoice = add_choice(self, choices=[], size=(120, -1),
                                  action=Closure(self.onSetRGBScale, color='b'))
        self.i0choice = add_choice(self, choices=[], size=(120, -1),
                                   action=Closure(self.onSetRGBScale, color='i0'))
        self.show = add_button(self, 'Show Map', size=(90, -1), action=self.onShow3ColorMap)

        self.det  = add_choice(self, choices=['sum', '1', '2', '3', '4'], size=(80, -1))
        self.newid  = wx.CheckBox(self, -1, 'Reuse Previous Display?')
        self.cor  = wx.CheckBox(self, -1, 'Correct Deadtime?')
        self.newid.SetValue(1)
        self.cor.SetValue(1)

        self.rauto = wx.CheckBox(self, -1, 'Autoscale?')
        self.gauto = wx.CheckBox(self, -1, 'Autoscale?')
        self.bauto = wx.CheckBox(self, -1, 'Autoscale?')
        self.rauto.SetValue(1)
        self.gauto.SetValue(1)
        self.bauto.SetValue(1)
        self.rauto.Bind(wx.EVT_CHECKBOX, Closure(self.onAutoScale, color='r'))
        self.gauto.Bind(wx.EVT_CHECKBOX, Closure(self.onAutoScale, color='g'))
        self.bauto.Bind(wx.EVT_CHECKBOX, Closure(self.onAutoScale, color='b'))

        self.rscale = FloatCtrl(self, precision=0, value=1, minval=0)
        self.gscale = FloatCtrl(self, precision=0, value=1, minval=0)
        self.bscale = FloatCtrl(self, precision=0, value=1, minval=0)

        ir = 0
        sizer.Add(SimpleText(self, 'Detector'),  (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Red'),       (ir, 1), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Green'),     (ir, 2), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Blue'),      (ir, 3), (1, 1), ALL_CEN, 2)


        ir += 1
        sizer.Add(self.det,                  (ir, 0), (1, 1), ALL_CEN, 2)
        sizer.Add(self.rchoice,              (ir, 1), (1, 1), ALL_CEN, 2)
        sizer.Add(self.gchoice,              (ir, 2), (1, 1), ALL_CEN, 2)
        sizer.Add(self.bchoice,              (ir, 3), (1, 1), ALL_CEN, 2)

        ir += 1
        sizer.Add(self.rauto,            (ir, 1), (1, 1), ALL_CEN, 2)
        sizer.Add(self.gauto,            (ir, 2), (1, 1), ALL_CEN, 2)
        sizer.Add(self.bauto,            (ir, 3), (1, 1), ALL_CEN, 2)
        ir += 1
        sizer.Add(self.rscale,            (ir, 1), (1, 1), ALL_CEN, 2)
        sizer.Add(self.gscale,            (ir, 2), (1, 1), ALL_CEN, 2)
        sizer.Add(self.bscale,            (ir, 3), (1, 1), ALL_CEN, 2)
        sizer.Add(SimpleText(self, 'Max Intensity:'),     (ir, 0), (1, 1), ALL_LEFT, 2)

        ir += 1
        sizer.Add(SimpleText(self, 'Normalization'), (ir, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.i0choice,             (ir, 1), (1, 2), ALL_LEFT, 2)

        ir += 1
        sizer.Add(self.cor,   (ir, 0), (1, 2), ALL_LEFT, 2)
        sizer.Add(self.newid, (ir, 2), (1, 2), ALL_LEFT, 2)

        ir += 1
        sizer.Add(self.show,  (ir, 0), (1, 1), ALL_LEFT, 2)

        pack(self, sizer)

    def onSetRGBScale(self, event=None, color=None, **kws):
        datafile = self.owner.current_file
        det =self.det.GetStringSelection()
        if det == 'sum':
            det =  None
        else:
            det = int(det)
        dtcorrect = self.cor.IsChecked()

        if color=='r':
            roi = self.rchoice.GetStringSelection()
            map = datafile.get_roimap(roi, det=det, dtcorrect=dtcorrect)
            self.rauto.SetValue(1)
            self.rscale.SetValue(map.max())
            self.rscale.Disable()
        elif color=='g':
            roi = self.gchoice.GetStringSelection()
            map = datafile.get_roimap(roi, det=det, dtcorrect=dtcorrect)
            self.gauto.SetValue(1)
            self.gscale.SetValue(map.max())
            self.gscale.Disable()
        elif color=='b':
            roi = self.bchoice.GetStringSelection()
            map = datafile.get_roimap(roi, det=det, dtcorrect=dtcorrect)
            self.bauto.SetValue(1)
            self.bscale.SetValue(map.max())
            self.bscale.Disable()

    def onShow3ColorMap(self, event=None):
        datafile = self.owner.current_file
        det =self.det.GetStringSelection()
        if det == 'sum':
            det =  None
        else:
            det = int(det)
        dtcorrect = self.cor.IsChecked()

        r = self.rchoice.GetStringSelection()
        g = self.gchoice.GetStringSelection()
        b = self.bchoice.GetStringSelection()
        i0 = self.i0choice.GetStringSelection()
        mapshape= datafile.xrfmap['roimap/sum_cor'][:, :, 0].shape

        rmap = np.ones(mapshape, dtype='float')
        gmap = np.ones(mapshape, dtype='float')
        bmap = np.ones(mapshape, dtype='float')
        i0map = np.ones(mapshape, dtype='float')
        if r != '1':
            rmap  = datafile.get_roimap(r, det=det, dtcorrect=dtcorrect)
        if g != '1':
            gmap  = datafile.get_roimap(g, det=det, dtcorrect=dtcorrect)
        if b != '1':
            bmap  = datafile.get_roimap(b, det=det, dtcorrect=dtcorrect)
        if i0 != '1':
            i0map = datafile.get_roimap(i0, det=det, dtcorrect=dtcorrect)

        rscale = 1.0/self.rscale.GetValue()
        gscale = 1.0/self.gscale.GetValue()
        bscale = 1.0/self.bscale.GetValue()
        if self.rauto.IsChecked():  rscale = 1.0/rmap.max()
        if self.gauto.IsChecked():  gscale = 1.0/gmap.max()
        if self.bauto.IsChecked():  bscale = 1.0/bmap.max()

        i0min = min(i0map[np.where(i0map>0)])
        i0map[np.where(i0map<=0)] = i0min
        i0map = i0map/i0map.max()

        title = '%s: (R, G, B) = (%s, %s, %s)' % (datafile.filename, r, g, b)
        map = np.array([rmap*rscale/i0map, gmap*gscale/i0map, bmap*bscale/i0map])
        map = map.swapaxes(0, 2).swapaxes(0, 1)
        if len(self.owner.im_displays) == 0 or not self.newid.IsChecked():
            iframe = self.owner.add_imdisplay(title, config_on_frame=False, det=det)
        self.owner.display_map(map, title=title, with_config=False, det=det)

    def set_roi_choices(self, choices):
        roichoices = ['1']
        roichoices.extend(choices)
        for cbox in (self.rchoice, self.bchoice, self.gchoice, self.i0choice):
            set_choices(cbox, roichoices)

    def onAutoScale(self, event=None, color=None, **kws):
        if color=='r':
            self.rscale.Enable()
            if self.rauto.GetValue() == 1:  self.rscale.Disable()
        elif color=='g':
            self.gscale.Enable()
            if self.gauto.GetValue() == 1:  self.gscale.Disable()
        elif color=='b':
            self.bscale.Enable()
            if self.bauto.GetValue() == 1:  self.bscale.Disable()



class AreaSelectionPanel(wx.Panel):
    delstr = """   Delete Area '%s'?

WARNING: This cannot be undone!

"""

    def __init__(self, parent, owner, **kws):
        wx.Panel.__init__(self, parent, -1, **kws)
        self.owner = owner

        sizer = wx.GridBagSizer(8, 3)

        bpanel = wx.Panel(self)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.choice = add_choice(self, choices=[], size=(200, -1), action=self.onSelect)
        self.desc   = wx.TextCtrl(self, -1, '', size=(200, -1))

        self.onmap  = add_button(bpanel, 'Show Area on Map', size=(140, -1),
                                      action=self.onShow)
        self.clear  = add_button(bpanel, 'Clear Areas on Map', size=(140, -1),
                                      action=self.onClear)
        self.xrf    = add_button(bpanel, 'Show XRF Spectrum', size=(140, -1),
                                      action=self.onXRF)

        self.delete = add_button(self, 'Delete This Area', size=(140, -1),
                                      action=self.onDelete)
        self.update = add_button(self, 'Save Label', size=(140, -1),
                                      action=self.onDesc)

        bsizer.Add(self.onmap, 0, ALL_CEN, 2)
        bsizer.Add(self.clear, 0, ALL_CEN, 2)
        bsizer.Add(self.xrf, 0, ALL_CEN, 2)
        pack(bpanel, bsizer)
        def txt(s):
            return SimpleText(self, s)
        sizer.Add(txt('Defined Map Areas'), (0, 0), (1, 2), ALL_CEN, 2)
        sizer.Add(txt('Area Name: '),       (1, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.choice,              (1, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.delete,              (1, 2), (1, 1), ALL_LEFT, 2)
        sizer.Add(txt('Label: '),           (2, 0), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.desc,                (2, 1), (1, 1), ALL_LEFT, 2)
        sizer.Add(self.update,              (2, 2), (1, 1), ALL_LEFT, 2)
        sizer.Add(bpanel,                   (3, 0), (1, 3), ALL_LEFT, 2)
        pack(self, sizer)

    def set_choices(self, choices, show_last=False):
        c = self.choice
        c.Clear()
        c.AppendItems(choices)
        if len(choices) > 0:
            idx = 0
            if show_last: idx = len(choices)-1
            c.SetStringSelection(choices[idx])
            area = self.owner.current_file.xrfmap['areas/%s' % choices[idx]]
            self.desc.SetValue(area.attrs['description'])

    def _getarea(self):
        dfile = self.owner.current_file
        aname = self.choice.GetStringSelection()
        return dfile.xrfmap['areas/%s' % aname]

    def onSelect(self, event=None):
        area = self._getarea()
        self.desc.SetValue(area.attrs['description'])

    def onDesc(self, event=None):
        area = self._getarea()
        area.attrs['description'] = str(self.desc.GetValue())
        self.owner.current_file.h5root.flush()

    def onShow(self, event=None):
        area = self._getarea()
        aname = self.choice.GetStringSelection()
        if len(self.owner.im_displays) > 0:
            imd = self.owner.im_displays[-1]
            imd.panel.add_highlight_area(area.value,
                                         label=area.attrs['description'])

    def onDelete(self, event=None):
        area = self._getarea()
        dfile = self.owner.current_file
        aname = self.choice.GetStringSelection()

        erase = popup(self.owner, self.delstr % aname,
                      'Delete Area?', style=wx.YES_NO)
        if erase:
            del dfile.xrfmap['areas/%s' % aname]
            self.set_choices(dfile.xrfmap['areas'].keys())

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

    def onXRF(self, event=None):
        area  = self._getarea()
        aname = self.choice.GetStringSelection()
        label = area.attrs['description']
        self._mca  = None
        mca_thread = Thread(target=self._getmca_area, args=(aname,))
        mca_thread.start()
        self.owner.show_XRFDisplay()
        mca_thread.join()
        fname = self.owner.current_file.filename
        title = "XRF Spectra:  %s, Area=%s:  %s" % (fname, aname, label)
        self.owner.xrfdisplay.SetTitle(title)
        self.owner.xrfdisplay.plot(self._mca.energy,
                                   self._mca.counts,
                                   mca=self._mca)

class MapViewerFrame(wx.Frame):
    _about = """XRF Map Viewer
  Matt Newville <newville @ cars.uchicago.edu>
  """
    cursor_menulabels = {'lasso': ('Select Points for XRF Spectra\tCtrl+X',
                                   'Left-Drag to select points for XRF Spectra')}

    def __init__(self, conffile=None,  **kwds):

        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, None, -1, size=(700, 450),  **kwds)

        self.data = None
        self.filemap = {}
        self.im_displays = []
        self.larch = None
        self.xrfdisplay = None

        self.Font12=wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font11=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font10=wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font9 =wx.Font(9, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        self.SetTitle("GSE XRM MapViewer")
        self.SetFont(self.Font9)

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

    def createMainPanel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(175)

        self.filelist = EditableListBox(splitter, self.ShowFile)
        # self.detailspanel = self.createViewOptsPanel(splitter)

        dpanel = self.detailspanel = wx.Panel(splitter)
        dpanel.SetMinSize((575, 425))
        self.createNBPanels(dpanel)
        splitter.SplitVertically(self.filelist, self.detailspanel, 1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 1, wx.GROW|wx.ALL, 5)
        wx.CallAfter(self.init_larch)
        pack(self, sizer)

    def createNBPanels(self, parent):
        self.title = SimpleText(parent, 'initializing...', size=(250, -1))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.title, 0, ALL_CEN)

        self.nb = flat_nb.FlatNotebook(parent, wx.ID_ANY, agwStyle=FNB_STYLE)
        self.nb.SetBackgroundColour('#FCFCFA')
        self.SetBackgroundColour('#F0F0E8')

        self.nbpanels = {}
        for name, key, creator in (('Simple ROI Map',  'roimap', SimpleMapPanel),
                                   ('3-Color ROI Map', '3color',  TriColorMapPanel)):
            #  ('2x2 Grid',         self.MapGridPanel)):
            # print 'panel ' , name, parent, creator
            self.nbpanels[key] = p = creator(parent, owner=self)
            self.nb.AddPage(p, name, True)
            bgcol = p.GetBackgroundColour()

        self.nb.SetSelection(0)
        sizer.Add(self.nb, 1, wx.ALL|wx.EXPAND)

        self.area_sel = AreaSelectionPanel(parent, owner=self)
        self.area_sel.SetBackgroundColour('#F0F0E8')

        sizer.Add(wx.StaticLine(parent, size=(250, 2),
                                style=wx.LI_HORIZONTAL),
                  0,  wx.ALL|wx.EXPAND)
        sizer.Add(self.area_sel, 0, wx.ALL|wx.EXPAND)
        pack(parent, sizer)

    def get_masked_mca(self, data, selected, detname, mask):
        t0 = time.time()
        mask.shape = data.shape[:2]
        mask = mask.transpose()
        map = self.current_file.xrfmap[detname]
        energy  = map['energy'].value
        cal     = map['energy'].attrs
        spectra = map['counts'].value
        spectra = spectra[mask].sum(axis=0)
        self.selected = selected
        self.mask = mask
        name = self.current_file.add_area(mask)

        self.sel_mca = MCA(counts=spectra, offset=cal['cal_offset'],
                           slope=cal['cal_slope'])
        self.sel_mca.energy = energy
        self.sel_mca.areaname = name
        roinames = map['roi_names'].value[:]
        roilims  = map['roi_limits'].value[:]
        for roi, lims in zip(roinames, roilims):
            self.sel_mca.add_roi(roi, left=lims[0], right=lims[1])

        return

    def lassoHandler(self, data=None, selected=None, det=None, mask=None, **kws):
        t0 = time.time()
        detname = 'detsum'
        if det is not None:
            detname = 'det%i' % det
        mca_thread = Thread(target=self.get_masked_mca,
                            args=(data, selected, detname, mask))
        mca_thread.start()
        self.show_XRFDisplay()

        mca_thread.join()

        fname = self.current_file.filename
        aname = self.sel_mca.areaname
        title = "XRF Spectra:  %s, Area=%s:  %s" % (fname, aname, aname)
        self.xrfdisplay.SetTitle(title)

        self.xrfdisplay.plot(self.sel_mca.energy,
                             self.sel_mca.counts,
                             mca=self.sel_mca)
        self.area_sel.set_choices(self.current_file.xrfmap['areas'].keys(),
                                  show_last=True)


    def show_XRFDisplay(self, do_raise=True, clear=True):
        "make sure plot frame is enabled, and visible"
        if self.xrfdisplay is None:
            self.xrfdisplay = XRFDisplayFrame(_larch=self.larch)
        try:
            self.xrfdisplay.Show()
        except wx.PyDeadObjectError:
            self.xrfdisplay = XRFDisplayFrame(_larch=self.larch)
            self.xrfdisplay.Show()

        if do_raise:
            self.xrfdisplay.Raise()
        if clear:
            self.xrfdisplay.panel.clear()
            self.xrfdisplay.panel.reset_config()

    def add_imdisplay(self, title, det=None, config_on_frame=True):
        on_lasso = Closure(self.lassoHandler, det=det)
        imframe = ImageFrame(output_title=title,
                             lasso_callback=on_lasso,
                             cursor_labels = self.cursor_menulabels,
                             config_on_frame=config_on_frame)
        self.im_displays.append(imframe)


    def display_map(self, map, title='', info='', x=None, y=None, det=None,
                    with_config=True):
        """display a map in an available image display"""
        displayed = False
        while not displayed:
            try:
                imd = self.im_displays.pop()
                imd.display(map, title=title, x=x, y=y)
                displayed = True
            except IndexError:
                on_lasso = Closure(self.lassoHandler, det=det)
                imd = ImageFrame(output_title=title,
                                 lasso_callback=on_lasso,
                                 cursor_labels = self.cursor_menulabels,
                                 config_on_frame=with_config)
                imd.display(map, title=title, x=x, y=y)
                displayed = True
            except PyDeadObjectError:
                displayed = False
        self.im_displays.append(imd)
        imd.SetStatusText(info, 1)

        imd.Show()
        imd.Raise()

    def init_larch(self):
        self.larch = larch.Interpreter()
        #self.larch.symtable.set_symbol('_sys.wx.wxapp', wx.GetApp())
        self.larch.symtable.set_symbol('_sys.wx.parent', self)
        self.SetStatusText('ready')
        self.datagroups = self.larch.symtable
        self.title.SetLabel('')

    def ShowFile(self, evt=None, filename=None, **kws):
        if filename is None and evt is not None:
            filename = evt.GetString()

        if not self.h5convert_done:
            return
        if self.check_ownership(filename):
            self.filemap[filename].process()

        self.current_file = self.filemap[filename]
        self.title.SetLabel("%s" % filename)

        rois = list(self.filemap[filename].xrfmap['roimap/sum_name'])
        rois_extra = [''] + rois

        set_choices(self.nbpanels['roimap'].roi1, rois)
        set_choices(self.nbpanels['roimap'].roi2, rois_extra)

        self.nbpanels['3color'].set_roi_choices(rois)
        self.area_sel.set_choices(self.current_file.xrfmap['areas'].keys())

    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        add_menu(self, fmenu, "&Open Map File\tCtrl+O",
                 "Read Map File",  self.onReadFile)
        add_menu(self, fmenu, "&Open Map Folder\tCtrl+F",
                 "Read Map Folder",  self.onReadFolder)
        add_menu(self, fmenu, 'Change &Working Folder',
                  "Choose working directory",
                  self.onFolderSelect)
        fmenu.AppendSeparator()
        add_menu(self, fmenu, "&Quit\tCtrl+Q",
                  "Quit program", self.onClose)

        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)

    def onFolderSelect(self,evt):
        style = wx.DD_DIR_MUST_EXIST|wx.DD_DEFAULT_STYLE
        dlg = wx.DirDialog(self, "Select Working Directory:", os.getcwd(),
                           style=style)

        if dlg.ShowModal() == wx.ID_OK:
            basedir = os.path.abspath(str(dlg.GetPath()))
            try:
                os.chdir(nativepath(basedir))
            except OSError:
                print 'Changed folder failed'
                pass
        dlg.Destroy()

    def onAbout(self,evt):
        dlg = wx.MessageDialog(self, self._about,"About GSEXRM MapViewer",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,evt):
        for xrmfile in self.filemap.values():
            xrmfile.close()

        for imd in self.im_displays:
            try:
                imd.Destroy()
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
            print 'cannot open file while processing a map folder'
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
                popup(self, NOT_GSEXRM_FOLDER % fname,
                     "Not a Map folder")
                return
            fname = xrmfile.filename
            if fname not in self.filemap:
                self.filemap[fname] = xrmfile
            if fname not in self.filelist.GetItems():
                self.filelist.Append(fname)
            if self.check_ownership(fname):
                self.process_file(fname)
            self.ShowFile(filename=fname)

    def onReadFile(self, evt=None):
        if not self.h5convert_done:
            print 'cannot open file while processing a map folder'
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
                read = popup(self, "Re-read file '%s'?" % path, 'Re-read file?',
                             style=wx.YES_NO)
        dlg.Destroy()

        if read:
            parent, fname = os.path.split(path)
            xrmfile = GSEXRM_MapFile(filename=str(path))
            #try:
            #except:
            #    popup(self, NOT_GSEXRM_FILE % fname,
            #          "Not a Map file!")
            #    return
            if fname not in self.filemap:
                self.filemap[fname] = xrmfile
            if fname not in self.filelist.GetItems():
                self.filelist.Append(fname)
            if self.check_ownership(fname):
                self.process_file(fname)
            self.h5convert_done = True
            self.ShowFile(filename=fname)

    def onGSEXRM_Data(self,  **kws):
        print 'Saw GSEXRM_Data ', kws

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
            print 'Has New Data! '
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
        self.message('Processing %s:  row %i of %i' % (fname, irow, nrow))
        if self.h5convert_done:
            self.htimer.Stop()
            self.h5convert_thread.join()
            self.message('Processing %s: complete!' % fname)
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
            if popup(self, NOT_OWNER_MSG % fname,
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
