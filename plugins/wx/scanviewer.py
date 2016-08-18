#!/usr/bin/env python
"""
Scan Data File Viewer
"""
import os
import time
import numpy as np
np.seterr(all='ignore')

from functools import partial

import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection

from wx.richtext import RichTextCtrl

is_wxPhoenix = 'phoenix' in wx.PlatformInfo

from larch import Interpreter, isParameter
from larch.larchlib import read_workdir, save_workdir
from larch.wxlib import larchframe, EditColumnFrame

from larch.fitting import fit_report
from larch.utils import debugtime

from larch_plugins.std import group2dict
from larch_plugins.math import fit_peak, index_of
from larch_plugins.wx.plotter import _newplot, _plot, _getDisplay
from larch_plugins.wx.icons import get_icon

from larch_plugins.io import (read_ascii, read_xdi, read_gsexdi,
                              gsescan_group, fix_varname)

from larch_plugins.xafs import pre_edge

from wxutils import (SimpleText, FloatCtrl, pack, Button,
                     Choice,  Check, MenuItem, GUIColors,
                     CEN, RCEN, LCEN, FRAMESTYLE, Font)

CEN |=  wx.ALL
FILE_WILDCARDS = "Scan Data Files(*.0*,*.dat,*.xdi)|*.0*;*.dat;*.xdi|All files (*.*)|*.*"
FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS

PLOTOPTS_1 = dict(style='solid', linewidth=3, marker='None', markersize=4)
PLOTOPTS_2 = dict(style='short dashed', linewidth=2, zorder=-5,
                  marker='None', markersize=4)
PLOTOPTS_D = dict(style='solid', linewidth=2, zorder=-5,
                  side='right',  marker='None', markersize=4)


def assign_gsescan_groups(group):
    labels = group.array_labels
    labels = []
    for i, name in enumerate(group.pos_desc):
        name = fix_varname(name.lower())
        labels.append(name)
        setattr(group, name, group.pos[i, :])

    for i, name in enumerate(group.sums_names):
        name = fix_varname(name.lower())
        labels.append(name)
        setattr(group, name, group.sums_corr[i, :])

    for i, name in enumerate(group.det_desc):
        name = fix_varname(name.lower())
        labels.append(name)
        setattr(group, name, group.det_corr[i, :])

    group.array_labels = labels


def BitmapButton(parent, bmp, action=None, tooltip=None):
    b = wx.BitmapButton(parent, -1, bmp)
    if action is not None:
        parent.Bind(wx.EVT_BUTTON, action, b)
    if tooltip is not None:
        b.SetToolTip(tooltip)
    return b

class EditableCheckListBox(wx.CheckListBox):
    """
    A ListBox with pop-up menu to arrange order of
    items and remove items from list
    supply select_action for EVT_LISTBOX selection action
    """
    def __init__(self, parent, select_action=None, right_click=True,
                 remove_action=None, **kws):
        wx.CheckListBox.__init__(self, parent, **kws)

        self.SetBackgroundColour(wx.Colour(248, 248, 235))
        if select_action is not None:
            self.Bind(wx.EVT_LISTBOX,  select_action)
        self.remove_action = remove_action
        if right_click:
            self.Bind(wx.EVT_RIGHT_DOWN, self.onRightClick)
            for item in ('popup_up1', 'popup_dn1',
                         'popup_upall', 'popup_dnall', 'popup_remove'):
                setattr(self, item,  wx.NewId())
                self.Bind(wx.EVT_MENU, self.onRightEvent,
                          id=getattr(self, item))

    def onRightClick(self, evt=None):
        menu = wx.Menu()
        menu.Append(self.popup_up1,    "Move up")
        menu.Append(self.popup_dn1,    "Move down")
        menu.Append(self.popup_upall,  "Move to top")
        menu.Append(self.popup_dnall,  "Move to bottom")
        menu.Append(self.popup_remove, "Remove from list")
        self.PopupMenu(menu)
        menu.Destroy()

    def onRightEvent(self, event=None):
        idx = self.GetSelection()
        if idx < 0: # no item selected
            return
        wid   = event.GetId()
        names = self.GetItems()
        this  = names.pop(idx)
        if wid == self.popup_up1 and idx > 0:
            names.insert(idx-1, this)
        elif wid == self.popup_dn1 and idx < len(names):
            names.insert(idx+1, this)
        elif wid == self.popup_upall:
            names.insert(0, this)
        elif wid == self.popup_dnall:
            names.append(this)
        elif wid == self.popup_remove and self.remove_action is not None:
            self.remove_action(this)

        self.Clear()
        for name in names:
            self.Append(name)

class ScanViewerFrame(wx.Frame):
    _about = """Scan 2D Plotter
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, _larch=None, **kws):

        wx.Frame.__init__(self, None, -1, style=FRAMESTYLE)
        self.file_groups = {}
        self.last_array_sel = {}
        title = "Column Data File Viewer"
        self.larch = _larch
        self.larch_buffer = None
        self.subframes = {}
        self.plotframe = None
        self.groupname = None
        self.SetTitle(title)
        self.SetSize((850, 650))
        self.SetFont(Font(10))

        self.config = {'chdir_on_fileopen': True}

        self.createMainPanel()
        self.createMenus()
        self.statusbar = self.CreateStatusBar(2, 0)
        self.statusbar.SetStatusWidths([-3, -1])
        statusbar_fields = ["Initializing....", " "]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)
        read_workdir('scanviewer.dat')
        self.need_xas_update = False
        self.xas_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onXASProcessTimer, self.xas_timer)
        self.xas_timer.Start(500)

    def createMainPanel(self):
        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(225)

        self.filelist  = EditableCheckListBox(splitter)
        self.filelist.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.filelist.Bind(wx.EVT_LISTBOX, self.ShowFile)

        self.detailspanel = self.createDetailsPanel(splitter)

        splitter.SplitVertically(self.filelist, self.detailspanel, 1)
        wx.CallAfter(self.init_larch)

    def createDetailsPanel(self, parent):
        mainpanel = wx.Panel(parent)
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.Panel(mainpanel)
        sizer = wx.GridBagSizer(8, 7)

        self.title = SimpleText(panel, 'initializing...')
        ir = 0
        sizer.Add(self.title, (ir, 0), (1, 6), LCEN, 2)
        # x-axis

        self.plot_one = Button(panel, 'Plot', size=(200, 30),
                               action=self.onPlotOne)
        self.plot_sel = Button(panel, 'Plot Selected', size=(200, 30),
                               action=self.onPlotSel)

        ir += 1
        sizer.Add(self.plot_one, (ir, 0), (1, 2), LCEN, 0)
        sizer.Add(self.plot_sel, (ir, 2), (1, 2), LCEN, 0)
        pack(panel, sizer)

        mainsizer.Add(panel,   0, LCEN|wx.EXPAND, 2)

        o = """
        btnbox   = wx.Panel(mainpanel)
        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        for ttl, opt in (('New Plot',   'new'),
                         ('Over Plot (left)',  'left'),
                         ('Over Plot (right)', 'right')):

            btnsizer.Add(Button(btnbox, ttl, size=(135, -1),
                                action=partial(self.onPlot, opt=opt)),
                         LCEN, 1)

        pack(btnbox, btnsizer)
        mainsizer.Add(btnbox, 0, LCEN, 2)
        """

        self.nb = flat_nb.FlatNotebook(mainpanel, -1, agwStyle=FNB_STYLE)

        self.nb.SetTabAreaColour(wx.Colour(248,248,240))
        self.nb.SetActiveTabColour(wx.Colour(254,254,195))

        self.nb.SetNonActiveTabTextColour(wx.Colour(40,40,180))
        self.nb.SetActiveTabTextColour(wx.Colour(80,0,0))

        self.xas_panel = self.CreateXASPanel(self.nb) # mainpanel)
        self.fit_panel = self.CreateFitPanel(self.nb) # mainpanel)

        self.nb.AddPage(self.fit_panel, ' General Curve Fitting ', True)
        self.nb.AddPage(self.xas_panel, ' XAS Processing ',   True)


        mainsizer.Add(self.nb, 1, LCEN|wx.EXPAND, 2)

        pack(mainpanel, mainsizer)

        return mainpanel

    def CreateFitPanel(self, parent):
        panel = wx.Panel(parent)
        tpan = wx.Panel(panel)
        self.fit_model = Choice(tpan, size=(100, -1),
                                choices=('Gaussian', 'Lorentzian',
                                         'Voigt', 'Linear', 'Quadratic',
                                         'Step', 'Rectangle',
                                         'Exponential'))
        self.fit_bkg = Choice(tpan, size=(100, -1),
                              choices=('None', 'constant', 'linear', 'quadratic'))
        self.fit_step = Choice(tpan, size=(100, -1),
                               choices=('linear', 'error function', 'arctan'))

        tsizer = wx.GridBagSizer(10, 4)
        tsizer.Add(SimpleText(tpan, 'Fit Model: '),     (0, 0), (1, 1), LCEN)
        tsizer.Add(self.fit_model,                      (0, 1), (1, 1), LCEN)

        tsizer.Add(SimpleText(tpan, 'Background: '),    (0, 2), (1, 1), LCEN)
        tsizer.Add(self.fit_bkg,                        (0, 3), (1, 1), LCEN)

        tsizer.Add(Button(tpan, 'Show Fit', size=(100, -1),
                         action=self.onFitPeak),       (1, 1), (1, 1), LCEN)

        tsizer.Add(SimpleText(tpan, 'Step Form: '),     (1, 2), (1, 1), LCEN)
        tsizer.Add(self.fit_step,                       (1, 3), (1, 1), LCEN)

        pack(tpan, tsizer)

        self.fit_report = RichTextCtrl(panel,  size=(525, 250),
                                     style=wx.VSCROLL|wx.NO_BORDER)

        self.fit_report.SetEditable(False)
        self.fit_report.SetFont(Font(9))


        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(tpan, 0, wx.GROW|wx.ALL, 2)
        sizer.Add(self.fit_report, 1, LCEN|wx.GROW,  2)
        pack(panel, sizer)
        return panel

    def InitializeXASPanel(self, dgroup):
        predefs = dict(e0=0, pre1=-200, pre2=-30, norm1=50,
                       edge_step=0, norm2=-10, nnorm=3, nvict=2,
                       auto_step=True, auto_e0=True, show_e0=True)

        if hasattr(dgroup, 'pre_edge_details'):
            predefs.update(group2dict(dgroup.pre_edge_details))

        self.xas_e0.SetValue(predefs['e0'])
        self.xas_step.SetValue(predefs['edge_step'])
        self.xas_pre1.SetValue(predefs['pre1'])
        self.xas_pre2.SetValue(predefs['pre2'])
        self.xas_nor1.SetValue(predefs['norm1'])
        self.xas_nor2.SetValue(predefs['norm2'])
        self.xas_vict.SetSelection(predefs['nvict'])
        self.xas_nnor.SetSelection(predefs['nnorm'])

        self.xas_showe0.SetValue(predefs['show_e0'])
        self.xas_autoe0.SetValue(predefs['auto_e0'])
        self.xas_autostep.SetValue(predefs['auto_step'])

    def CreateXASPanel(self, parent):
        opchoices=('Raw Data', 'Normalized', 'Derivative',
                   'Normalized + Derivative',
                   'Pre-edge subtracted',
                   'Raw Data + Pre-edge/Post-edge')
        p = panel = wx.Panel(parent)
        opts = {'action': self.UpdateXASPlot}
        self.xas_autoe0   = Check(panel, default=True, label='auto?', **opts)
        self.xas_showe0   = Check(panel, default=True, label='show?', **opts)
        self.xas_autostep = Check(panel, default=True, label='auto?', **opts)
        self.xas_op       = Choice(panel, size=(300, -1),
                                   choices=opchoices,  **opts)


        self.btns = {}
        for name in ('e0', 'pre1', 'pre2', 'nor1', 'nor2'):
            bb = BitmapButton(panel, get_icon('plus'),
                              action=partial(self.onXAS_selpoint, opt=name),
                              tooltip='use last point selected from plot')
            self.btns[name] = bb

        opts = {'size': (85, -1), 'precision': 3,
                'action': self.UpdateXASPlot}
        self.xwids = {}
        self.xas_e0   = FloatCtrl(panel, value  = 0, **opts)
        self.xas_step = FloatCtrl(panel, value  = 0, **opts)
        opts['precision'] = 1
        self.xas_pre1 = FloatCtrl(panel, value=-200, **opts)
        self.xas_pre2 = FloatCtrl(panel, value= -30, **opts)
        self.xas_nor1 = FloatCtrl(panel, value=  50, **opts)
        self.xas_nor2 = FloatCtrl(panel, value= -50, **opts)

        opts = {'size': (50, -1),
                'choices': ('0', '1', '2', '3'),
                'action': self.UpdateXASPlot}
        self.xas_vict = Choice(panel, **opts)
        self.xas_nnor = Choice(panel, **opts)
        self.xas_vict.SetSelection(1)
        self.xas_nnor.SetSelection(2)
        sizer = wx.GridBagSizer(10, 7)

        sizer.Add(SimpleText(p, 'Plot XAS as: '),         (0, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'E0 : '),                 (1, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Edge Step: '),           (2, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Pre-edge range: '),      (3, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Normalization range: '), (4, 0), (1, 1), LCEN)

        sizer.Add(self.xas_op,                 (0, 1), (1, 6), LCEN)
        sizer.Add(self.btns['e0'],             (1, 1), (1, 1), LCEN)
        sizer.Add(self.xas_e0,                 (1, 2), (1, 1), LCEN)
        sizer.Add(self.xas_autoe0,             (1, 3), (1, 3), LCEN)
        sizer.Add(self.xas_showe0,             (1, 6), (1, 2), LCEN)

        sizer.Add(self.xas_step,               (2, 2), (1, 1), LCEN)
        sizer.Add(self.xas_autostep,           (2, 3), (1, 3), LCEN)

        sizer.Add(self.btns['pre1'],           (3, 1), (1, 1), LCEN)
        sizer.Add(self.xas_pre1,               (3, 2), (1, 1), LCEN)
        sizer.Add(SimpleText(p, ':'),          (3, 3), (1, 1), LCEN)
        sizer.Add(self.btns['pre2'],           (3, 4), (1, 1), LCEN)
        sizer.Add(self.xas_pre2,               (3, 5), (1, 1), LCEN)
        sizer.Add(self.btns['nor1'],           (4, 1), (1, 1), LCEN)
        sizer.Add(self.xas_nor1,               (4, 2), (1, 1), LCEN)
        sizer.Add(SimpleText(p, ':'),          (4, 3), (1, 1), LCEN)
        sizer.Add(self.btns['nor2'],           (4, 4), (1, 1), LCEN)
        sizer.Add(self.xas_nor2,               (4, 5), (1, 1), LCEN)


        sizer.Add(SimpleText(p, 'Victoreen:'), (3, 6), (1, 1), LCEN)
        sizer.Add(self.xas_vict,               (3, 7), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'PolyOrder:'), (4, 6), (1, 1), LCEN)
        sizer.Add(self.xas_nnor,               (4, 7), (1, 1), LCEN)

        pack(panel, sizer)
        return panel

    def onXAS_selpoint(self, evt=None, opt='e0'):
        xval = None
        try:
            xval = self.larch.symtable._plotter.plot1_x
        except:
            pass
        if xval is None:
            return

        e0 = self.xas_e0.GetValue()
        if opt == 'e0':
            self.xas_e0.SetValue(xval)
            self.xas_autoe0.SetValue(0)
        elif opt == 'pre1':
            self.xas_pre1.SetValue(xval-e0)
        elif opt == 'pre2':
            self.xas_pre2.SetValue(xval-e0)
        elif opt == 'nor1':
            self.xas_nor1.SetValue(xval-e0)
        elif opt == 'nor2':
            self.xas_nor2.SetValue(xval-e0)


    def onCustomColumns(self, evt=None):
        pass

    def onFitPeak(self, evt=None):
        gname = self.groupname

        dtext = []
        model = self.fit_model.GetStringSelection().lower()
        dtext.append('Fit Model: %s' % model)
        bkg =  self.fit_bkg.GetStringSelection()
        if bkg == 'None':
            bkg = None
        if bkg is None:
            dtext.append('No Background')
        else:
            dtext.append('Background: %s' % bkg)

        step = self.fit_step.GetStringSelection().lower()
        if model in ('step', 'rectangle'):
            dtext.append('Step form: %s' % step)

        try:
            lgroup =  getattr(self.larch.symtable, gname)
            x = lgroup._xdat
            y = lgroup._ydat
        except AttributeError:
            self.write_message('need data to fit!')
            return
        if step.startswith('error'):
            step = 'erf'
        elif step.startswith('arctan'):
            step = 'atan'

        pgroup = fit_peak(x, y, model, background=bkg, step=step,
                          _larch=self.larch)

        dtext = '\n'.join(dtext)
        dtext = '%s\n%s\n' % (dtext, fit_report(pgroup.params, min_correl=0.25,
                                                _larch=self.larch))

        self.fit_report.SetEditable(True)
        self.fit_report.SetValue(dtext)
        self.fit_report.SetEditable(False)

        lgroup.plot_yarrays = [(lgroup._ydat, PLOTOPTS_1, lgroup.plot_ylabel)]
        if bkg is None:
            lgroup._fit = pgroup.fit[:]
            lgroup.plot_yarrays.append((lgroup._fit, PLOTOPTS_2, 'fit'))
        else:
            lgroup._fit     = pgroup.fit[:]
            lgroup._fit_bgr = pgroup.bkg[:]
            lgroup.plot_yarrays.append((lgroup._fit,    PLOTOPTS_2, 'fit'))
            lgroup.plot_yarrays.append((lgroup._fit_bgr, PLOTOPTS_2, 'background'))
        self.plot_group(gname, new=True)

    def xas_process(self, gname, new_mu=False, **kws):
        """ process (pre-edge/normalize) XAS data from XAS form, overwriting
        larch group '_y1_' attribute to be plotted
        """
        dgroup = getattr(self.larch.symtable, gname)

        if not hasattr(dgroup, 'energy'):
            dgroup.energy = dgroup._xdat
        if not hasattr(dgroup, 'mu'):
            dgroup.mu = dgroup._ydat

        e0 = None
        if not self.xas_autoe0.IsChecked():
            _e0 = self.xas_e0.GetValue()
            if _e0 < max(dgroup.energy) and _e0 > min(dgroup.energy):
                e0 = float(_e0)

        preopts = {'e0': e0}
        if not self.xas_autostep.IsChecked():
            preopts['step'] = self.xas_step.GetValue()
        preopts['pre1']  = self.xas_pre1.GetValue()
        preopts['pre2']  = self.xas_pre2.GetValue()
        preopts['norm1'] = self.xas_nor1.GetValue()
        preopts['norm2'] = self.xas_nor2.GetValue()
        preopts['nvict'] = self.xas_vict.GetSelection()
        preopts['nnorm'] = self.xas_nnor.GetSelection()
        preopts['make_flat'] = False
        preopts['_larch'] = self.larch

        pre_edge(dgroup, **preopts)
        dgroup.pre_edge_details.e0 = dgroup.e0
        dgroup.pre_edge_details.edge_step = dgroup.edge_step
        dgroup.pre_edge_details.auto_e0 = self.xas_autoe0.IsChecked()
        dgroup.pre_edge_details.show_e0 = self.xas_showe0.IsChecked()
        dgroup.pre_edge_details.auto_step = self.xas_autostep.IsChecked()

        if self.xas_autoe0.IsChecked():
            self.xas_e0.SetValue(dgroup.e0)
        if self.xas_autostep.IsChecked():
            self.xas_step.SetValue(dgroup.edge_step)

        details_group = dgroup.pre_edge_details
        self.xas_pre1.SetValue(details_group.pre1)
        self.xas_pre2.SetValue(details_group.pre2)
        self.xas_nor1.SetValue(details_group.norm1)
        self.xas_nor2.SetValue(details_group.norm2)

        dgroup.orig_ylabel = dgroup.plot_ylabel
        dgroup.plot_ylabel = '$\mu$'
        dgroup.plot_y2label = None
        dgroup.plot_xlabel = '$E \,\mathrm{(eV)}$'
        dgroup.plot_yarrays = [(dgroup.mu, PLOTOPTS_1, dgroup.plot_ylabel)]
        y4e0 = dgroup.mu

        out = self.xas_op.GetStringSelection().lower() # raw, pre, norm, flat
        if out.startswith('raw data + pre'):
            dgroup.plot_yarrays = [(dgroup.mu,        PLOTOPTS_1, '$\mu$'),
                                   (dgroup.pre_edge,  PLOTOPTS_2, 'pre edge'),
                                   (dgroup.post_edge, PLOTOPTS_2, 'post edge')]
        elif out.startswith('pre'):
            dgroup.pre_edge_sub = dgroup.norm * dgroup.edge_step
            dgroup.plot_yarrays = [(dgroup.pre_edge_sub, PLOTOPTS_1,
                                    'pre-edge subtracted $\mu$')]
            y4e0 = dgroup.pre_edge_sub
            dgroup.plot_ylabel = 'pre-edge subtracted $\mu$'
        elif 'norm' in out and 'deriv' in out:
            dgroup.plot_yarrays = [(dgroup.norm, PLOTOPTS_1, 'normalized $\mu$'),
                                   (dgroup.dmude, PLOTOPTS_D, '$d\mu/dE$')]
            y4e0 = dgroup.norm
            dgroup.plot_ylabel = 'normalized $\mu$'
            dgroup.plot_y2label = '$d\mu/dE$'
        elif out.startswith('norm'):
            dgroup.plot_yarrays = [(dgroup.norm, PLOTOPTS_1, 'normalized $\mu$')]
            y4e0 = dgroup.norm
            dgroup.plot_ylabel = 'normalized $\mu$'
        elif out.startswith('deriv'):
            dgroup.plot_yarrays = [(dgroup.dmude, PLOTOPTS_1, '$d\mu/dE$')]
            y4e0 = dgroup.dmude
            dgroup.plot_ylabel = '$d\mu/dE$'

        dgroup.plot_ymarkers = []
        if self.xas_showe0.IsChecked():
            ie0 = index_of(dgroup._xdat, dgroup.e0)
            dgroup.plot_ymarkers = [(dgroup.e0, y4e0[ie0], {'label': 'e0'})]
        return

    def init_larch(self):
        t0 = time.time()
        if self.larch is None:
            self.larch = Interpreter()
        self.larch.symtable.set_symbol('_sys.wx.wxapp', wx.GetApp())
        self.larch.symtable.set_symbol('_sys.wx.parent', self)

        self.SetStatusText('ready')
        self.title.SetLabel('')

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def onXASProcessTimer(self, evt=None):
        if self.groupname is None:
            return
        if self.need_xas_update:
            self.xas_process(self.groupname)
            self.plot_group(self.groupname, new=True)
            self.need_xas_update = False

    def UpdateXASPlot(self, evt=None, **kws):
        self.need_xas_update = True

    def onPlotOne(self, evt=None, groupname=None):
        if groupname is None:
            groupname = self.groupname

        dgroup = getattr(self.larch.symtable, groupname, None)
        if dgroup is None:
            return
        self.groupname = groupname
        if (dgroup.is_xas and
            (getattr(dgroup, 'plot_yarrays', None) is None or
             getattr(dgroup, 'energy', None) is None or
             getattr(dgroup, 'mu', None) is None)):
            self.xas_process(groupname)
        self.plot_group(groupname, new=True)

    def onPlotSel(self, evt=None):
        newplot = True
        group_ids = self.filelist.GetCheckedStrings()
        for checked in group_ids:
            groupname = self.file_groups[str(checked)]
            dgroup = getattr(self.larch.symtable, groupname, None)
            if dgroup is None:
                continue
            if dgroup.is_xas:
                if ((getattr(dgroup, 'plot_yarrays', None) is None or
                     getattr(dgroup, 'energy', None) is None or
                     getattr(dgroup, 'mu', None) is None)):
                    self.xas_process(groupname)

                dgroup.plot_yarrays = [(dgroup.norm, PLOTOPTS_1,
                                        '%s norm' % dgroup._filename)]
                dgroup.plot_ylabel = 'normalized $\mu$'
                dgroup.plot_xlabel = '$E\,\mathrm{(eV)}$'
                dgroup.plot_ymarkers = []

            else:
                dgroup.plot_yarrays = [(dgroup._ydat, PLOTOPTS_1,
                                        dgroup._filename)]

            self.plot_group(groupname, title='', new=newplot)
            newplot=False

    def plot_group(self, groupname, title=None, new=True):

        oplot = self.larch.symtable._plotter.plot
        newplot = self.larch.symtable._plotter.newplot
        getdisplay = self.larch.symtable._plotter.get_display

        plotcmd = oplot
        if new:
            plotcmd = newplot

        dgroup = getattr(self.larch.symtable, groupname, None)
        if not hasattr(dgroup, '_xdat'):
            print("Cannot plot group ", groupname)

        if hasattr(dgroup, 'plot_yarrays'):
            plot_yarrays = dgroup.plot_yarrays
        else:
            plot_yarrays = [(dgroup._ydat, {}, None)]
        print("Plt Group ", groupname, hasattr(dgroup,'plot_yarrays'))

        popts = {}
        path, fname = os.path.split(dgroup.filename)
        popts['label'] = "%s: %s" % (fname, dgroup.plot_ylabel)
        popts['xlabel'] = dgroup.plot_xlabel
        popts['ylabel'] = dgroup.plot_ylabel
        if getattr(dgroup, 'plot_y2label', None) is not None:
            popts['y2label'] = dgroup.plot_y2label


        if plotcmd == newplot and title is None:
            title = fname

        popts['title'] = title

        for yarr in plot_yarrays:
            popts.update(yarr[1])
            if yarr[2] is not None:
                popts['label'] = yarr[2]
            plotcmd(dgroup._xdat, yarr[0], **popts)
            plotcmd = oplot # self.plotpanel.oplot

        ppanel = getdisplay(_larch=self.larch).panel
        if hasattr(dgroup, 'plot_ymarkers'):
            axes = ppanel.axes
            for x, y, opts in dgroup.plot_ymarkers:
                popts = {'marker': 'o', 'markersize': 4,
                         'markerfacecolor': 'red',
                         'markeredgecolor': 'black'}
                popts.update(opts)
                axes.plot([x], [y], **popts)
        ppanel.canvas.draw()

    def onShowLarchBuffer(self, evt=None):
        if self.larch_buffer is None:
            self.larch_buffer = larchframe.LarchFrame(_larch=self.larch)

        self.larch_buffer.Show()
        self.larch_buffer.Raise()

    def ShowFile(self, evt=None, groupname=None, **kws):
        if groupname is None and evt is not None:
            groupname = self.file_groups[str(evt.GetString())]

        if not hasattr(self.larch.symtable, groupname):
            print( 'Error reading file ', groupname)
            return

        self.groupname = groupname
        self.dgroup = getattr(self.larch.symtable, groupname, None)

        if self.dgroup.is_xas:
            self.nb.SetSelection(1)
        else:
            self.nb.SetSelection(0)

    def createMenus(self):
        # ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        #
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "&Open Data File\tCtrl+O",
                 "Read Scan File",  self.onReadScan)

        MenuItem(self, fmenu, "Show Larch Buffer\tCtrl+L",
                  "Show Larch Programming Buffer",
                  self.onShowLarchBuffer)

        fmenu.AppendSeparator()

        MenuItem(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)

        self.menubar.Append(fmenu, "&File")

        omenu = wx.Menu()
        MenuItem(self, omenu, "Edit Column Labels\tCtrl+E",
                 "Edit Column Labels", self.onEditColumnLabels)

        self.menubar.Append(omenu, "Options")

        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)

    def onAbout(self,evt):
        dlg = wx.MessageDialog(self, self._about,"About ScanViewer",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,evt):
        save_workdir('scanviewer.dat')


        for nam in dir(self.larch.symtable._plotter):
            obj = getattr(self.larch.symtable._plotter, nam)
            try:
                obj.Destroy()
            except:
                pass

        for nam in dir(self.larch.symtable._sys.wx):
            obj = getattr(self.larch.symtable._sys.wx, nam)
            del obj


        if self.larch_buffer is not None:
            try:
                self.larch_buffer.onClose()
            except:
                pass
        for w in self.GetChildren():
            w.Destroy()

        self.Destroy()

    def show_subframe(self, name, frameclass, **opts):
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except:
                del self.subframes[name]
        if not shown:
            self.subframes[name] = frameclass(self, **opts)

    def onEditColumnLabels(self, evt=None):
        self.show_subframe('coledit', EditColumnFrame, group=self.dgroup,
                           last_array_sel=self.last_array_sel,
                           read_ok_cb=self.onReadScan_Success)

    def onReadScan(self, evt=None):
        dlg = wx.FileDialog(self, message="Load Column Data File",
                            defaultDir=os.getcwd(),
                            wildcard=FILE_WILDCARDS, style=wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            path = path.replace('\\', '/')
            if path in self.file_groups:
                if wx.ID_YES != popup(self, "Re-read file '%s'?" % path,
                                      'Re-read file?'):
                    return

            filedir, filename = os.path.split(path)
            pref = fix_varname((filename + '____')[:7]).replace('.', '_')
            count, maxcount = 1, 9999
            groupname = "%s%3.3i" % (pref, count)
            while hasattr(self.larch.symtable, groupname) and count < maxcount:
                count += 1
                groupname = '%s%3.3i' % (pref, count)

            if self.config['chdir_on_fileopen']:
                os.chdir(filedir)

            fh = open(path, 'r')
            line1 = fh.readline().lower()
            fh.close()
            reader = read_ascii
            if 'epics stepscan file' in line1:
                reader = read_gsexdi
            elif 'epics scan' in line1:
                reader = gsescan_group
            elif 'xdi' in line1:
                reader = read_xdi

            dgroup = reader(str(path), _larch=self.larch)
            if reader == gsescan_group:
                assign_gsescan_groups(dgroup)
            dgroup._path = path
            dgroup._filename = filename
            dgroup._groupname = groupname

            self.show_subframe('coledit', EditColumnFrame, group=dgroup,
                               last_array_sel=self.last_array_sel,
                               read_ok_cb=self.onReadScan_Success)

        dlg.Destroy()


    def onReadScan_Success(self, datagroup, array_sel):
        """ called when column data has been selected and is ready to be used"""
        self.last_array_sel = array_sel
        filename = datagroup._filename
        groupname= datagroup._groupname
        # print("   storing datagroup ", datagroup, groupname, filename)
        # file /group may already exist in list
        if groupname not in self.file_groups:
            self.filelist.Append(filename)

            self.file_groups[filename] = groupname

        setattr(self.larch.symtable, groupname, datagroup)
        if datagroup.is_xas:
            self.nb.SetSelection(1)
            self.InitializeXASPanel(datagroup)
        else:
            self.nb.SetSelection(0)
        self.onPlotOne(groupname=groupname)

class ScanViewer(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, _larch=None, **kws):
        self._larch = _larch
        wx.App.__init__(self, **kws)

    def run(self):
        self.MainLoop()

    def createApp(self):
        frame = ScanViewerFrame(_larch=self._larch)
        frame.Show()
        self.SetTopWindow(frame)

    def OnInit(self):
        self.createApp()
        return True

class DebugViewer(ScanViewer, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, **kws):
        ScanViewer.__init__(self, **kws)

    def OnInit(self):
        self.Init()
        self.createApp()
        self.ShowInspectionTool()
        return True

if __name__ == "__main__":
    ScanViewer().run()
