#!/usr/bin/env python
"""
GUI Frame for XRF display, reading larch MCA group

"""
import sys
import os
import time
import wx
import wx.lib.mixins.inspection
from wx._core import PyDeadObjectError

import numpy as np
import matplotlib
from wxmplot import BaseFrame, PlotPanel

from larch import Group, Parameter, isParameter, plugin_path

sys.path.insert(0, plugin_path('wx'))

from wxutils import (SimpleText, EditableListBox, FloatCtrl, HyperText,
                     Closure, pack,
                     popup, add_button, add_menu, add_choice, add_menu)

#from ..io.xrm_mapfile import (GSEXRM_MapFile, GSEXRM_FileStatus,
#                              GSEXRM_Exception, GSEXRM_NotOwner)

CEN = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
RIGHT = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
ALL_CEN =  wx.ALL|CEN
ALL_LEFT =  wx.ALL|LEFT
ALL_RIGHT =  wx.ALL|RIGHT

## FILE_WILDCARDS = "X-ray Maps (*.h5)|*.h5|All files (*.*)|*.*"
## FILE_WILDCARDS = "X-ray Maps (*.0*)|*.0&"

FILE_ALREADY_READ = """The File
   '%s'
has already been read.
"""

def txt(label, panel, size=75, colour=None,  style=None):
    if style is None:
        style = wx.ALIGN_LEFT|wx.ALL|wx.GROW
    if colour is None:
        colour = wx.Colour(0, 0, 50)
    return SimpleText(panel, label, size=(size, -1),
                      colour=colour, style=style)

def lin(panel, len=30, wid=2, style=wx.LI_HORIZONTAL):
    return wx.StaticLine(panel, size=(len, wid), style=style)


class Menu_IDs:
    def __init__(self):
        self.EXIT   = wx.NewId()
        self.SAVE   = wx.NewId()
        self.CONFIG = wx.NewId()
        self.UNZOOM = wx.NewId()
        self.HELP   = wx.NewId()
        self.ABOUT  = wx.NewId()
        self.PRINT  = wx.NewId()
        self.PSETUP = wx.NewId()
        self.PREVIEW= wx.NewId()
        self.CLIPB  = wx.NewId()
        self.SELECT_COLOR = wx.NewId()
        self.SELECT_SMOOTH= wx.NewId()
        self.TOGGLE_LEGEND = wx.NewId()
        self.TOGGLE_GRID = wx.NewId()

class XRFDisplayFrame(BaseFrame):
    _about = """XRF Spectral Viewer
  Matt Newville <newville @ cars.uchicago.edu>
  """
    roi_fillcolor = '#EAEA44'
    roi_color     = '#AA0000'
    spectra_color = '#0000AA'

    def __init__(self, _larch=None, parent=None, size=(700, 400),
                 axissize=None, axisbg=None, title='XRF Display',
                 exit_callback=None, output_title='XRF', **kws):

        kws["style"] = wx.DEFAULT_FRAME_STYLE
        BaseFrame.__init__(self, parent=parent,
                           title=title, size=size,
                           axissize=axissize, axisbg=axisbg,
                           **kws)

        self.data = None
        self.plotframe = None
        self.larch = _larch
        self.exit_callback = exit_callback
        self.selected_roi = None
        self.mca = None

        self.Font14 = wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font12 = wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font11 = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font10 = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font9  = wx.Font(9, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        self.SetTitle("XRF Spectra Viewer")
        self.SetFont(self.Font9)

        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ["XRF Display", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        # self.BindMenuToPanel()


    def createMainPanel(self):
        self.wids = {}
        ctrlpanel = self.ctrlpanel = wx.Panel(self)
        roipanel = self.roipanel = wx.Panel(self)
        plotpanel = self.panel = PlotPanel(self, fontsize=7,
                                               axisbg='#FDFDFA',
                                               axissize=[0.04, 0.08, 0.94, 0.90],
                                               output_title='test.xrf',
                                               messenger=self.write_message)
        ## need to customize cursor modes:
        # plotpane.add_cursor_mode('zoom', .....)
        # plotpane.add_cursor_mode('report', .....)


        sizer = wx.GridBagSizer(10, 4)

        labstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM|wx.EXPAND
        ctrlstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM
        rlabstyle = wx.ALIGN_RIGHT|wx.RIGHT|wx.TOP|wx.EXPAND
        txtstyle=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE|wx.TE_PROCESS_ENTER

        self.wids['ylog'] = add_choice(ctrlpanel, size=(80, -1),
                                       choices=['log', 'linear'],
                                       action=self.onLogLinear)
        self.wids['series'] = add_choice(ctrlpanel, size=(80, -1),
                                         choices=['K', 'L', 'M', 'N'])
        self.wids['elems'] = add_choice(ctrlpanel, size=(80, -1),
                                        choices=['H', 'He'])

        ir = 0
        sizer.Add(txt('  Settings: ', ctrlpanel),  (ir, 0), (1, 2), labstyle)

        ir += 1
        sizer.Add(lin(ctrlpanel, 95),         (ir, 0), (1, 2), labstyle)

        ir += 1
        sizer.Add(txt(' Series:', ctrlpanel),  (ir, 0), (1, 1), labstyle)
        sizer.Add(self.wids['series'],          (ir, 1), (1, 1), ctrlstyle)

        ir += 1
        sizer.Add(txt(' Elements:', ctrlpanel),  (ir, 0), (1, 1), labstyle)
        sizer.Add(self.wids['elems'],          (ir, 1), (1, 1), ctrlstyle)

        ir += 1
        sizer.Add(lin(ctrlpanel, 95),         (ir, 0), (1, 2), labstyle)

        ir += 1
        sizer.Add(txt(' Y Scale:', ctrlpanel),  (ir, 0), (1, 1), labstyle)
        sizer.Add(self.wids['ylog'],           (ir, 1), (1, 1), ctrlstyle)

        ir += 1
        sizer.Add(txt(' ', ctrlpanel),  (ir, 0), (1, 1), wx.ALL|wx.EXPAND|labstyle)

        ir += 1
        sizer.Add(txt(' Counts: ', ctrlpanel),  (ir, 0), (1, 1), labstyle)
        ir += 1
        sizer.Add(txt('   : ', ctrlpanel),  (ir, 0), (1, 1), labstyle)


        ctrlpanel.SetSizer(sizer)
        sizer.Fit(ctrlpanel)

        rsizer = wx.GridBagSizer(10, 3)
        ir = 0
        rsizer.Add(txt('  Regions of Interest: ', roipanel),  (ir, 0), (1, 2), labstyle)
        ir += 1
        rsizer.Add(lin(roipanel, 120),         (ir, 0), (1, 2), labstyle)
        roipanel.SetSizer(rsizer)
        rsizer.Fit(roipanel)

        style = wx.EXPAND|wx.ALL

        msizer = wx.BoxSizer(wx.HORIZONTAL)
        msizer.Add(self.ctrlpanel, 0, style, 0)
        msizer.Add(self.panel,     1, style, 0)
        msizer.Add(self.roipanel,  0, style, 0)

        pack(self, msizer)
        self.add_rois(mca=None)

    def add_rois(self, mca=None):
        """ Add Roi names and counts to ROI Panel"""
        sizer = wx.GridBagSizer(10, 3)
        panel = self.roipanel

        for wid in self.roipanel.Children:
            try:
                wid.Destroy()
            except PyDeadObjectError:
                pass

        labstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM|wx.EXPAND
        ir = 0
        sizer.Add(txt('  Regions of Interest  ', panel),  (ir, 0), (1, 2), labstyle)
        ir += 1
        sizer.Add(lin(panel, 105),         (ir, 0), (1, 2), labstyle)

        ir += 1
        sizer.Add(txt(' Name ', panel),  (ir, 0), (1, 1), labstyle)
        sizer.Add(txt(' Counts ', panel, style=RIGHT|wx.EXPAND),
                  (ir, 1), (1, 1), labstyle)

        if mca is not None:
            for roi in mca.rois:
                name = " %s " % roi.name
                counts = "%d " % mca.get_roi_counts(roi.name)
                ir += 1
                sizer.Add(HyperText(panel, name, action=self.onROI,
                                    size=(80, -1),
                                    style=wx.ALIGN_LEFT|wx.EXPAND),
                          (ir, 0), (1, 1), labstyle)
                sizer.Add(txt(counts, panel, style=wx.ALIGN_RIGHT|wx.EXPAND),
                          (ir, 1), (1, 1), labstyle)

        ir += 1
        sizer.Add(lin(panel, 105),         (ir, 0), (1, 2), labstyle)

        panel.SetSizer(sizer)
        sizer.Fit(panel)

    def onROI(self, evt=None, label=None):
        name, left, right= None, -1, -1
        label = label.lower().strip()
        if self.mca is not None:
            for roi in self.mca.rois:
                if roi.name.lower()==label:
                    name = roi.name
                    left = roi.left
                    right= roi.right

        if name is None or right == -1:
            return

        if self.selected_roi  is not None:
            try:
                self.selected_roi.remove()
            except:
                pass

        e = np.zeros(right-left+2)
        r = np.ones(right-left+2)
        e[1:-1] = self.mca.energy[left:right]
        r[1:-1] = self.mca.counts[left:right]
        e[0]    = e[1]
        e[-1]   = e[-2]
        fill = self.panel.axes.fill_between
        self.selected_roi  = fill(e, r, color=self.roi_fillcolor)

        self.panel.canvas.draw()
        self.panel.Refresh()


    def createMenus(self):
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()
        add_menu(self, fmenu, "&Read MCA Spectra File\tCtrl+O",
                 "Read GSECARS MCA File",  self.onReadMCAFile)
        add_menu(self, fmenu, "&Read XRM Map File\tCtrl+F",
                 "Read GSECARS XRM MAp File",  self.onReadGSEXRMFile)
        add_menu(self, fmenu, "&Open Epics MCA\tCtrl+E",
                 "Read Epics MCA",  self.onOpenEpicsMCA)

        fmenu.AppendSeparator()
        add_menu(self, fmenu, "&Save MCA File\tCtrl+S",
                 "Save GSECARS MCA File",  self.onSaveMCAFile)
        add_menu(self, fmenu, "&Save ASCII Column File\tCtrl+A",
                 "Save Column File",  self.onSaveColumnFile)

        fmenu.AppendSeparator()
        add_menu(self, fmenu, "&Quit\tCtrl+Q",
                  "Quit program", self.onClose)

        omenu = wx.Menu()
        add_menu(self, omenu, "&Calibrate Energy\tCtrl+B",
                 "Calibrate Energy",  self.onCalibrateEnergy)
        add_menu(self, omenu, "&Fit background\tCtrl+G",
                 "Fit smooth background",  self.onFitbackground)

        self.menubar.Append(fmenu, "&File")
        self.menubar.Append(omenu, "&Options")
        self.SetMenuBar(self.menubar)


    def BindMenuToPanel(self, panel=None):
        if panel is None: panel = self.panel
        if panel is not None:
            p = panel
            mids = self.menuIDs
            self.Bind(wx.EVT_MENU, panel.configure,    id=mids.CONFIG)
            self.Bind(wx.EVT_MENU, panel.toggle_legend, id=mids.TOGGLE_LEGEND)
            self.Bind(wx.EVT_MENU, panel.toggle_grid, id=mids.TOGGLE_GRID)
            self.Bind(wx.EVT_MENU, panel.configure,    id=mids.CONFIG)
            self.Bind(wx.EVT_MENU, panel.unzoom,       id=mids.UNZOOM)

            self.Bind(wx.EVT_MENU, panel.save_figure,  id=mids.SAVE)
            self.Bind(wx.EVT_MENU, panel.Print,        id=mids.PRINT)
            self.Bind(wx.EVT_MENU, panel.PrintSetup,   id=mids.PSETUP)
            self.Bind(wx.EVT_MENU, panel.PrintPreview, id=mids.PREVIEW)
            self.Bind(wx.EVT_MENU, panel.canvas.Copy_to_Clipboard,
                      id=mids.CLIPB)

    def onLogLinear(self, event=None):
        self.plot(self.xdata, self.ydata,
                  ylog_scale=('log' == event.GetString()))

    def plot(self, x, y, mca=None, **kws):
        panel = self.panel
        kwargs = {'ylog_scale': True, 'xmin': 0}
        kwargs.update(kws)
        self.xdata = x
        self.ydata = y
        panel.plot(x, y, **kwargs)
        panel.axes.get_yaxis().set_visible(False)
        panel.unzoom_all()
        panel.cursor_mode = 'zoom'
        if mca is not None:
            self.mca = mca
            self.add_rois(mca=mca)

    def oplot(self, x, y, mcagroup=None, **kws):
        panel.oplot(x, y, **kws)

    def onReadMCAFile(self, event=None):
        pass

    def onReadGSEXRMFile(self, event=None, **kws):
        print '  onReadGSEXRMFile   '
        pass

    def onOpenEpicsMCA(self, event=None, **kws):
        print '  onOpenEpicsMCA   '
        pass

    def onSaveMCAFile(self, event=None, **kws):
        print '  onSaveMCAFile   '
        pass

    def onSaveColumnFile(self, event=None, **kws):
        print '  onSaveColumnFile   '
        pass

    def onCalibrateEnergy(self, event=None, **kws):
        print '  onCalibrateEnergy   '
        pass

    def onFitbackground(self, event=None, **kws):
        print '  onFitbackground   '
        pass

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def onAbout(self,evt):
        dlg = wx.MessageDialog(self, self._about,"About XRF Viewer",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,evt):
        self.Destroy()

    def onReadFile(self, evt=None):
        dlg = wx.FileDialog(self, message="Read MCA File",
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
            try:
                parent, fname = os.path.split(path)
                # xrmfile = GSEXRM_MapFile(fname)
            except:
                # popup(self, NOT_GSEXRM_FILE % fname,
                # "Not a Map file!")
                return
            if fname not in self.filemap:
                self.filemap[fname] = xrmfile
            if fname not in self.filelist.GetItems():
                self.filelist.Append(fname)
            if self.check_ownership(fname):
                self.process_file(fname)
            self.ShowFile(filename=fname)


class XRFApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, **kws):
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        frame = XRFDisplayFrame() #
        frame.Show()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    XRFApp().MainLoop()
