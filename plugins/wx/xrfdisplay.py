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

from wxutils import (SimpleText, EditableListBox, FloatCtrl,
                     Closure, pack,
                     popup, add_button, add_menu, add_choice, add_menu)

from periodictable import PeriodicTablePanel

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

AT_SYMS = ('H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na',
           'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti',
           'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As',
           'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru',
           'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs',
           'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb',
           'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os',
           'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
           'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk',
           'Cf')


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
    major_elinecolor = (0.6, 0.6, 0.4, 0.4)
    minor_elinecolor = (0.7, 0.7, 0.4, 0.3)

    roi_fillcolor = (0.9, 0.9, 0.5)
    roi_color     = '#AA0000'
    spectra_color = '#0000AA'
    K_major = ('Ka1', 'Ka2', 'Kb1')
    K_minor = ('Kb3', 'Kb2')
    L_major = ('La1', 'Lb1', 'Lb3', 'Lb4')
    L_minor = ('Ln', 'Ll', 'Lb2,15', 'Lg2', 'Lg3', 'Lg1', 'La2')
    M_major = ('Ma', 'Mb', 'Mg', 'Mz')


    def __init__(self, _larch=None, parent=None, size=(725, 450),
                 axissize=None, axisbg=None, title='XRF Display',
                 exit_callback=None, output_title='XRF', **kws):

        kws["style"] = wx.DEFAULT_FRAME_STYLE
        BaseFrame.__init__(self, parent=parent,
                           title=title, size=size,
                           axissize=axissize, axisbg=axisbg,
                           exit_callback=exit_callback,
                           **kws)

        self.data = None
        self.plotframe = None
        self.larch = _larch
        self.exit_callback = exit_callback
        self.selected_roi = None
        self.mca = None
        self.rois_shown = False
        self.eline_markers = []

        self.Font14 = wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font12 = wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font11 = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font10 = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.Font9  = wx.Font(9, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        self.SetTitle("XRF Spectra Viewer")
        self.SetFont(self.Font9)

        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(3)
        self.statusbar.SetStatusWidths([-3, -1, -1])
        statusbar_fields = ["XRF Display", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)


    def createMainPanel(self):
        self.wids = {}
        ctrlpanel = self.ctrlpanel = wx.Panel(self,  size=(320, 450))
        roipanel = self.roipanel = wx.Panel(self)
        plotpanel = self.panel = PlotPanel(self, fontsize=7,
                                               axisbg='#FDFDFA',
                                               axissize=[0.03, 0.10, 0.94, 0.88],
                                               output_title='test.xrf',
                                               messenger=self.write_message)

        ptable = PeriodicTablePanel(self, action=self.onShowLines)

        sizer = wx.GridBagSizer(10, 3)

        labstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM|wx.EXPAND
        ctrlstyle = wx.ALIGN_LEFT|wx.ALIGN_BOTTOM
        rlabstyle = wx.ALIGN_RIGHT|wx.RIGHT|wx.TOP|wx.EXPAND
        txtstyle=wx.ALIGN_LEFT|wx.ST_NO_AUTORESIZE|wx.TE_PROCESS_ENTER

        self.wids['ylog'] = add_choice(ctrlpanel, size=(80, -1),
                                       choices=['log', 'linear'],
                                       action=self.onLogLinear)

        spanel = wx.Panel(ctrlpanel)
        ssizer = wx.BoxSizer(wx.HORIZONTAL)

        self.wids['kseries'] = wx.CheckBox(spanel, label='K')
        self.wids['kseries'].SetValue(1)
        self.wids['lseries'] = wx.CheckBox(spanel, label='L')
        self.wids['lseries'].SetValue(1)
        self.wids['mseries'] = wx.CheckBox(spanel, label='M')
        self.wids['mseries'].SetValue(1)

        ssizer.Add(txt(' Series:', spanel), 0, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['kseries'],    1, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['lseries'],    1, wx.EXPAND|wx.ALL, 0)
        ssizer.Add(self.wids['mseries'],    1, wx.EXPAND|wx.ALL, 0)

        pack(spanel, ssizer)

        self.wids['roilist'] = EditableListBox(ctrlpanel, self.onROI,
                                               right_click=False, size=(150, 100))

        self.wids['noroi'] = add_button(ctrlpanel, 'Hide', size=(70, -1),
                                        action=self.onClearROIDisplay)
        self.wids['delroi'] = add_button(ctrlpanel, 'Delete', size=(70, -1),
                                         action=self.onNewROI)
        self.wids['newroi'] = add_button(ctrlpanel, 'Add', size=(70, -1),
                                         action=self.onNewROI)


        self.wids['counts_tot'] = txt('   ', ctrlpanel)
        self.wids['counts_net'] = txt('   ', ctrlpanel)

        ir = 0
        sizer.Add(ptable,  (ir, 0), (1, 3), wx.ALIGN_LEFT, border=0)

        ir += 1
        sizer.Add(spanel, (ir, 0), (1, 2), labstyle)

        ir += 1
        sizer.Add(lin(ctrlpanel, 195),   (ir, 0), (1, 3), labstyle)
        ir += 1
        sizer.Add(txt(' Regions of Interest: ', ctrlpanel),  (ir, 0), (1, 3), labstyle)
        ir += 1
        sizer.Add(self.wids['noroi'],     (ir, 0), (1, 1), wx.ALIGN_CENTER)
        sizer.Add(self.wids['delroi'],  (ir, 1), (1, 1),  wx.ALIGN_CENTER)
        sizer.Add(self.wids['newroi'],  (ir, 2), (1, 1), wx.ALIGN_CENTER)

        ir += 1
        sizer.Add(self.wids['roilist'],  (ir, 0), (1, 2), labstyle)

        ir += 1
        sizer.Add(txt(' Counts:', ctrlpanel),  (ir, 0), (1,1), labstyle)
        sizer.Add(txt(' Total ',  ctrlpanel),  (ir, 1), (1,1), labstyle)
        sizer.Add(txt(' Net:',    ctrlpanel),  (ir, 2), (1,1), labstyle)
        ir += 1
        sizer.Add(self.wids['counts_tot'],         (ir, 1), (1, 1), ctrlstyle)
        sizer.Add(self.wids['counts_net'],         (ir, 2), (1, 1), ctrlstyle)

        ir += 1
        sizer.Add(lin(ctrlpanel, 95),         (ir, 0), (1, 3), labstyle)

        ir += 1
        sizer.Add(txt(' Y Scale:', ctrlpanel),  (ir, 0), (1, 1), labstyle)
        sizer.Add(self.wids['ylog'],           (ir, 1), (1, 2), ctrlstyle)


        ctrlpanel.SetSizer(sizer)
        sizer.Fit(ctrlpanel)

        style = wx.ALIGN_LEFT|wx.EXPAND|wx.ALL
        msizer = wx.BoxSizer(wx.HORIZONTAL)
        msizer.Add(self.ctrlpanel, 0, style, 2)
        msizer.Add(self.panel,     1, style, 2)
        pack(self, msizer)

        self.add_rois(mca=None)

    def add_rois(self, mca=None):
        """ Add Roi names to roilist"""
        self.wids['roilist'].Clear()
        if mca is not None:
            for roi in mca.rois:
                self.wids['roilist'].Append(roi.name)


    def onClearROIDisplay(self, event=None):
        if self.selected_roi  is not None:
            try:
                self.selected_roi.remove()
            except:
                pass
        self.panel.canvas.draw()

    def onNewROI(self, event=None):
        print  'on New ROI'

    def onROI(self, event=None, label=None):
        if label is None and event is not None:
            label = event.GetString()

        name, left, right= None, -1, -1
        counts_tot, counts_net = '', ''
        label = label.lower().strip()
        if self.mca is not None:
            for roi in self.mca.rois:
                if roi.name.lower()==label:
                    name = roi.name
                    left = roi.left
                    right= roi.right
                    counts_tot = "%i" % roi.get_counts(self.mca.counts)
                    counts_net = "%i" % roi.get_counts(self.mca.counts, net=True)

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
        self.wids['counts_tot'].SetLabel(counts_tot)
        self.wids['counts_net'].SetLabel(counts_net)

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
        add_menu(self, fmenu,  "&Save\tCtrl+S",
                 "Save PNG Image of Plot", self.onSavePNG)
        add_menu(self, fmenu, "&Copy\tCtrl+C",
                 "Copy Plot Image to Clipboard",
                 self.onCopyImage)
        add_menu(self, fmenu, 'Page Setup...', 'Printer Setup', self.onPageSetup)
        add_menu(self, fmenu, 'Print Preview...', 'Print Preview', self.onPrintPreview)
        add_menu(self, fmenu, "&Print\tCtrl+P", "Print Plot", self.onPrint)


        fmenu.AppendSeparator()
        add_menu(self, fmenu, "&Quit\tCtrl+Q",
                  "Quit program", self.onExit)

        omenu = wx.Menu()
        add_menu(self, omenu, "&Calibrate Energy\tCtrl+B",
                 "Calibrate Energy",  self.onCalibrateEnergy)
        add_menu(self, omenu, "&Fit background\tCtrl+G",
                 "Fit smooth background",  self.onFitbackground)

        add_menu(self, omenu, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range", self.unzoom)

        self.menubar.Append(fmenu, "&File")
        self.menubar.Append(omenu, "&Options")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,self.onExit)

    def onSavePNG(self, event=None):
        if self.panel is not None:
            self.panel.save_figure(event=event)
    def onCopyImage(self, event=None):
        if self.panel is not None:
            self.panel.canvas.Copy_to_Clipboard(event=event)
    def onPageSetup(self, event=None):
        if self.panel is not None:
            self.panel.PrintSetup(event=event)

    def onPrintPreview(self, event=None):
        if self.panel is not None:
            self.panel.PrintPreview(event=event)

    def onPrint(self, event=None):
        if self.panel is not None:
            self.panel.Print(event=event)

    def onExit(self, event=None):
        try:
            if hasattr(self.exit_callback, '__call__'):
                self.exit_callback()
        except:
            pass
        try:
            if self.panel is not None:
                self.panel.win_config.Close(True)
            if self.panel is not None:
                self.panel.win_config.Destroy()
        except:
            pass

        try:
            self.Destroy()
        except:
            pass

    def onShowLines(self, event=None, elem=None):
        if elem is None:
            elem  = event.GetString()
        try:
            vline = self.panel.axes.axvline
            elines = self.larch.symtable._xray.xray_lines(elem)
        except:
            return
        for marker in self.eline_markers:
            try:
                marker.remove()
            except:
                pass
        self.eline_markers = []
        miss = [-1, '']
        minors, majors = [], []
        if self.wids['kseries'].IsChecked():
            majors.extend([elines.get(l, miss)[0]/1000 for l in self.K_major])
            minors.extend([elines.get(l, miss)[0]/1000 for l in self.K_minor])
        if self.wids['lseries'].IsChecked():
            majors.extend([elines.get(l, miss)[0]/1000 for l in self.L_major])
            minors.extend([elines.get(l, miss)[0]/1000 for l in self.L_minor])
        if self.wids['mseries'].IsChecked():
            majors.extend([elines.get(l, miss)[0]/1000 for l in self.M_major])

        erange = [max(0, self.xdata.min()), self.xdata.max()]
        for e in minors:
            if e > erange[0] and e < erange[1]:
                l = vline(e, color= self.minor_elinecolor, linewidth=0.75)
                self.eline_markers.append(l)

        for e in majors:
            if e > erange[0] and e < erange[1]:
                l = vline(e, color= self.major_elinecolor, linewidth=1.75)
                self.eline_markers.append(l)

        self.panel.canvas.draw()


    def onLogLinear(self, event=None):
        self.plot(self.xdata, self.ydata,
                  ylog_scale=('log' == event.GetString()))

    def plot(self, x, y, mca=None, **kws):
        if mca is not None:
            self.mca = mca
        mca = self.mca
        panel = self.panel
        kwargs = {'ylog_scale': True, 'grid': False,
                  'xlabel': 'E (keV)',
                  'color': self.spectra_color}
        kwargs.update(kws)
        self.xdata = 1.0*x[:]
        self.ydata = 1.0*y[:]
        if mca is not None:
            if not self.rois_shown:
                self.add_rois(mca=mca)
            yroi = -1*np.ones(len(y))
            ydat = 1.0*y[:]
            for r in mca.rois:
                yroi[r.left:r.right] = y[r.left:r.right]
                ydat[r.left+1:r.right-1] = -1
            yroi = np.ma.masked_less(yroi, 0)
            ydat = np.ma.masked_less(ydat, 0)
            panel.plot(x, ydat, label='spectra', **kwargs)
            kwargs['color'] = self.roi_color
            panel.oplot(x, yroi, label='roi', **kwargs)
        else:
            panel.plot(x, y, **kwargs)
        panel.axes.get_yaxis().set_visible(False)
        panel.unzoom_all()
        panel.cursor_mode = 'zoom'

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

    def onAbout(self,event):
        dlg = wx.MessageDialog(self, self._about,"About XRF Viewer",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,event):
        self.Destroy()

    def onReadFile(self, event=None):
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


class XRFApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, **kws):
        wx.App.__init__(self)
        print 'APP with mixin!'

    def OnInit(self):
        self.Init()
        frame = XRFDisplayFrame() #
        frame.Show()
        self.SetTopWindow(frame)
        self.ShowInspectionTool()
        return True

if __name__ == "__main__":
    XRFApp().MainLoop()
