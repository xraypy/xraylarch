#!/usr/bin/env python
"""

"""
import os
import time
import shutil
import numpy as np
np.seterr(all='ignore')

from random import randrange
from functools import partial
from datetime import timedelta

import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled
import wx.lib.mixins.inspection

from wx.richtext import RichTextCtrl

HAS_EPICS = False
try:
    import epics
    from epics.wx import DelayedEpicsCallback, EpicsFunction
    HAS_EPICS = True
except ImportError:
    pass

from larch import Interpreter, isParameter
from larch.larchlib import read_workdir, save_workdir
from larch.wxlib import larchframe
from larch.fitting import fit_report
from larch.utils import debugtime

from larch_plugins.math import fit_peak, index_of

from larch_plugins.io import gsescan_group, read_xdi

from larch_plugins.wx.mapviewer import MapViewerFrame

from wxmplot import PlotFrame, PlotPanel

from wxutils import (SimpleText, FloatCtrl, pack, Button,
                     Choice,  Check, MenuItem, GUIColors,
                     CEN, RCEN, LCEN, FRAMESTYLE, Font)

CEN |=  wx.ALL
FILE_WILDCARDS = "Scan Data Files(*.0*,*.dat,*.xdi)|*.0*;*.dat;*.xdi|All files (*.*)|*.*"
FNB_STYLE = flat_nb.FNB_NO_X_BUTTON|flat_nb.FNB_SMART_TABS|flat_nb.FNB_NO_NAV_BUTTONS


PRE_OPS = ('', 'log', '-log')
ARR_OPS = ('+', '-', '*', '/')

SCANGROUP = '_scan'
def randname(n=6):
    "return random string of n (default 6) lowercase letters"
    return ''.join([chr(randrange(26)+97) for i in range(n)])

def okcancel(panel, onOK=None, onCancel=None):
    btnsizer = wx.StdDialogButtonSizer()
    _ok = wx.Button(panel, wx.ID_OK)
    _no = wx.Button(panel, wx.ID_CANCEL)
    panel.Bind(wx.EVT_BUTTON, onOK,     _ok)
    panel.Bind(wx.EVT_BUTTON, onCancel, _no)
    _ok.SetDefault()
    btnsizer.AddButton(_ok)
    btnsizer.AddButton(_no)
    btnsizer.Realize()
    return btnsizer


class EditColumnFrame(wx.Frame) :
    """Set Column Labels for a file"""
    def __init__(self, parent, pos=(-1, -1)):

        self.parent = parent
        self.larch = parent.larch
        self.lgroup = parent.lgroup

        message = "Edit Column Labels for %s" % self.lgroup.filename

        wx.Frame.__init__(self, None, -1, 'Edit Column Labels',
                          style=FRAMESTYLE)

        FWID = 600
        self.SetFont(Font(10))
        sizer = wx.GridBagSizer(10, 5)
        panel = scrolled.ScrolledPanel(self)
        self.SetMinSize((600, 600))
        self.colors = GUIColors()

        # title row
        title = SimpleText(panel, message, font=Font(13),
                           colour=self.colors.title, style=LCEN)

        sizer.Add(title,        (0, 0), (1, 3), LCEN, 5)

        ir = 1
        sizer.Add(SimpleText(panel, label='Column #', size=(55, -1)),
                  (ir, 0), (1, 1), LCEN, 2)
        sizer.Add(SimpleText(panel, label='Current Label', size=(200, -1)),
                  (ir, 1), (1, 1), RCEN, 2)
        sizer.Add(SimpleText(panel, label='New Label'),
                  (ir, 2), (1, 1), LCEN, 2)

        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(FWID, 3), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), LCEN|wx.GROW|wx.ALL, 3)

        self.twids = []
        for icol, clab in enumerate(self.lgroup.array_labels):
            ix   = SimpleText(panel, label='%i' % icol, size=(55, -1))
            old  = SimpleText(panel, label=clab,        size=(200, -1))
            new  = wx.TextCtrl(panel, -1, value=clab,   size=(200, -1))
            self.twids.append((clab, new))

            ir +=1
            sizer.Add(ix,  (ir, 0), (1, 1), RCEN, 2)
            sizer.Add(old, (ir, 1), (1, 1), LCEN, 2)
            sizer.Add(new, (ir, 2), (1, 1), LCEN, 2)



        ir += 1
        sizer.Add(okcancel(panel, self.onOK, self.onClose),
                  (ir, 0), (1, 2), LCEN, 3)

        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(FWID, 3), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), LCEN|wx.GROW|wx.ALL, 3)
        #
        pack(panel, sizer)

        ftext = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY,
                               size=(-1, 275))
        try:
            m = open(self.lgroup.filename, 'r')
            text = m.read()
            m.close()
        except:
            text = "The file '%s'\n was not found" % self.lgroup.filename
        ftext.SetValue(text)
        ftext.SetFont(Font(9))


        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 0, wx.GROW|wx.ALL, 2)
        mainsizer.Add(ftext, 1, LCEN|wx.GROW,   2)
        pack(self, mainsizer)

        self.Show()
        self.Raise()

    def onOK(self, event=None):
        """ rename labels -- note that values for new names are first gathered,
        and then set, so that renaming 'a' and 'b' works."""
        labels = []
        tmp = {}
        for oldname, twid in self.twids:
            newname = twid.GetValue()
            labels.append(newname)
            if oldname != newname:
                tmp[newname] = getattr(self.lgroup, oldname)
        for name, val in tmp.items():
            setattr(self.lgroup, name, val)
        self.lgroup.array_labels = labels
        self.parent.set_array_labels(labels=labels)
        self.Destroy()

    def onClose(self, event=None):
        self.Destroy()


class ScanViewerFrame(wx.Frame):
    _about = """Scan 2D Plotter
  Matt Newville <newville @ cars.uchicago.edu>
  """
    def __init__(self, _larch=None, **kws):

        wx.Frame.__init__(self, None, -1, style=FRAMESTYLE)
        self.file_groups = {}
        self.file_paths  = []
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


    def createMainPanel(self):
        splitter  = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(225)

        self.filelist  = wx.ListBox(splitter)
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

        self.xarr = Choice(panel, choices=[],
                               action=self.onColumnChoices,  size=(120, -1))
        self.xop  = Choice(panel, choices=('', 'log'),
                               action=self.onColumnChoices, size=(90, -1))

        ir += 1
        sizer.Add(SimpleText(panel, 'X = '), (ir, 0), (1, 1), CEN, 0)
        sizer.Add(self.xop,                  (ir, 1), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, '('),    (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.xarr,                 (ir, 3), (1, 1), RCEN, 0)
        sizer.Add(SimpleText(panel, ')'),    (ir, 4), (1, 1), CEN, 0)

        self.yops = []
        self.yarr = []

        opts= {'choices':[], 'size':(120, -1), 'action':self.onColumnChoices}
        for i in range(3):
            self.yarr.append(Choice(panel, **opts))


        for opts, sel, siz in ((PRE_OPS, 0, 90),
                               (ARR_OPS, 3, 50), (ARR_OPS, 3, 50)):
            w1 = Choice(panel, choices=opts, action=self.onColumnChoices,
                            size=(siz, -1))
            w1.SetSelection(sel)
            self.yops.append(w1)

        ir += 1
        label = 'Y = '
        sizer.Add(SimpleText(panel, label), (ir, 0), (1, 1), CEN, 0)
        sizer.Add(self.yops[0],             (ir, 1), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, '[('),  (ir, 2), (1, 1), CEN, 0)
        sizer.Add(self.yarr[0],             (ir, 3), (1, 1), CEN, 0)
        sizer.Add(self.yops[1],             (ir, 4), (1, 1), CEN, 0)
        sizer.Add(self.yarr[1],             (ir, 5), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, ')'),   (ir, 6), (1, 1), LCEN, 0)
        ir += 1
        sizer.Add(self.yops[2],             (ir, 4), (1, 1), CEN, 0)
        sizer.Add(self.yarr[2],             (ir, 5), (1, 1), CEN, 0)
        sizer.Add(SimpleText(panel, ']'),   (ir, 6), (1, 1), LCEN, 0)

        self.use_deriv = Check(panel, default=False, label='Use Derivative?',
                              action=self.onColumnChoices)
        self.dtcorr   = Check(panel, default=True, label='correct deadtime?',
                              action=self.onColumnChoices)
        ir += 1
        sizer.Add(self.use_deriv, (ir,   0), (1, 3), LCEN, 0)
        sizer.Add(self.dtcorr,    (ir,   3), (1, 3), LCEN, 0)

        pack(panel, sizer)

        self.nb = flat_nb.FlatNotebook(mainpanel, -1, agwStyle=FNB_STYLE)

        self.nb.SetTabAreaColour(wx.Colour(248,248,240))
        self.nb.SetActiveTabColour(wx.Colour(254,254,195))

        self.nb.SetNonActiveTabTextColour(wx.Colour(40,40,180))
        self.nb.SetActiveTabTextColour(wx.Colour(80,0,0))

        self.xas_panel = self.CreateXASPanel(self.nb) # mainpanel)
        self.fit_panel = self.CreateFitPanel(self.nb) # mainpanel)

        self.nb.AddPage(self.fit_panel, ' General Analysis ', True)
        self.nb.AddPage(self.xas_panel, ' XAS Processing ',   True)
        mainsizer.Add(panel,   0, LCEN|wx.EXPAND, 2)


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

    def InitializeXASPanel(self):
        if self.groupname is None:
            lgroup = None
        lgroup = getattr(self.larch.symtable, self.groupname)
        self.xas_e0.SetValue(getattr(lgroup, 'e0', 0))
        self.xas_step.SetValue(getattr(lgroup, 'edge_step', 0))
        self.xas_pre1.SetValue(getattr(lgroup, 'pre1',   -200))
        self.xas_pre2.SetValue(getattr(lgroup, 'pre2',   -30))
        self.xas_nor1.SetValue(getattr(lgroup, 'norm1',  50))
        self.xas_nor2.SetValue(getattr(lgroup, 'norm2', -10))

        self.xas_vict.SetSelection(getattr(lgroup, 'nvict', 1))
        self.xas_nnor.SetSelection(getattr(lgroup, 'nnorm', 2))

    def CreateXASPanel(self, parent):
        p = panel = wx.Panel(parent)
        self.xas_autoe0   = Check(panel, default=True, label='auto?')
        self.xas_showe0   = Check(panel, default=True, label='show?')
        self.xas_autostep = Check(panel, default=True, label='auto?')
        self.xas_op       = Choice(panel, size=(225, -1),
                                       choices=('Raw Data', 'Normalized',
                                                'Derivative',
                                                'Normalized + Derivative',
                                                'Pre-edge subtracted',
                                   'Raw Data With Pre-edge/Post-edge Curves'),
                                   action=self.onXASChoice)
        opts = {'size': (95, -1), 'precision': 3} # , 'action': self.onXASChoice}
        self.xas_e0   = FloatCtrl(panel, value  = 0, **opts)
        self.xas_step = FloatCtrl(panel, value  = 0, **opts)
        opts['precision'] = 1
        self.xas_pre1 = FloatCtrl(panel, value=-200, **opts)
        self.xas_pre2 = FloatCtrl(panel, value= -30, **opts)
        self.xas_nor1 = FloatCtrl(panel, value=  50, **opts)
        self.xas_nor2 = FloatCtrl(panel, value= -50, **opts)
        opts = {'size': (50, -1), 'choices': ('0', '1', '2', '3'),
               'action': self.onXASChoice}
        self.xas_vict = Choice(panel, **opts)
        self.xas_nnor = Choice(panel, **opts)
        self.xas_vict.SetSelection(1)
        self.xas_nnor.SetSelection(2)
        sizer = wx.GridBagSizer(10, 4)

        sizer.Add(SimpleText(p, 'Plot XAS as: '),         (0, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'E0 : '),                 (1, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Edge Step: '),           (2, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Pre-edge range: '),      (3, 0), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'Normalization range: '), (4, 0), (1, 1), LCEN)

        sizer.Add(self.xas_op,                 (0, 1), (1, 3), LCEN)
        sizer.Add(self.xas_e0,                 (1, 1), (1, 1), LCEN)
        sizer.Add(self.xas_step,               (2, 1), (1, 1), LCEN)
        sizer.Add(self.xas_pre1,               (3, 1), (1, 1), LCEN)
        sizer.Add(SimpleText(p, ':'),          (3, 2), (1, 1), LCEN)
        sizer.Add(self.xas_pre2,               (3, 3), (1, 1), LCEN)
        sizer.Add(self.xas_nor1,               (4, 1), (1, 1), LCEN)
        sizer.Add(SimpleText(p, ':'),          (4, 2), (1, 1), LCEN)
        sizer.Add(self.xas_nor2,               (4, 3), (1, 1), LCEN)

        sizer.Add(self.xas_autoe0,             (1, 2), (1, 2), LCEN)
        sizer.Add(self.xas_showe0,             (1, 4), (1, 2), LCEN)
        sizer.Add(self.xas_autostep,           (2, 2), (1, 2), LCEN)

        sizer.Add(SimpleText(p, 'Victoreen:'), (3, 4), (1, 1), LCEN)
        sizer.Add(self.xas_vict,               (3, 5), (1, 1), LCEN)
        sizer.Add(SimpleText(p, 'PolyOrder:'), (4, 4), (1, 1), LCEN)
        sizer.Add(self.xas_nnor,               (4, 5), (1, 1), LCEN)

        pack(panel, sizer)
        return panel

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
            x = lgroup._xdat_
            y = lgroup._ydat_
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

        popts1 = dict(style='solid', linewidth=3,
                      marker='None', markersize=4)
        popts2 = dict(style='short dashed', linewidth=2,
                      marker='None', markersize=4)

        lgroup.plot_yarrays = [(lgroup._ydat_, popts1, lgroup.plot_ylabel)]
        if bkg is None:
            lgroup._fit = pgroup.fit[:]
            lgroup.plot_yarrays.append((lgroup._fit, popts2, 'fit'))
        else:
            lgroup._fit     = pgroup.fit[:]
            lgroup._fit_bgr = pgroup.bkg[:]
            lgroup.plot_yarrays.append((lgroup._fit,     popts2, 'fit'))
            lgroup.plot_yarrays.append((lgroup._fit_bgr, popts2, 'background'))
        self.onPlot()

    def xas_process(self, gname, new_mu=False, **kws):
        """ process (pre-edge/normalize) XAS data from XAS form, overwriting
        larch group '_y1_' attribute to be plotted
        """

        out = self.xas_op.GetStringSelection().lower() # raw, pre, norm, flat
        preopts = {'group': gname, 'e0': None}

        lgroup = getattr(self.larch.symtable, gname)
        dtcorr = self.dtcorr.IsChecked()
        if new_mu:
            try:
                del lgroup.e0, lgroup.edge_step
            except:
                pass

        if not self.xas_autoe0.IsChecked():
            e0 = self.xas_e0.GetValue()
            if e0 < max(lgroup._xdat_) and e0 > min(lgroup._xdat_):
                preopts['e0'] = e0

        if not self.xas_autostep.IsChecked():
            preopts['step'] = self.xas_step.GetValue()

        dt = debugtime()

        preopts['pre1']  = self.xas_pre1.GetValue()
        preopts['pre2']  = self.xas_pre2.GetValue()
        preopts['norm1'] = self.xas_nor1.GetValue()
        preopts['norm2'] = self.xas_nor2.GetValue()

        preopts['nvict'] = self.xas_vict.GetSelection()
        preopts['nvict'] = self.xas_vict.GetSelection()
        preopts['nnorm'] = self.xas_nnor.GetSelection()

        preopts['make_flat'] = 'False'
        preopts['group'] = gname
        preopts = ", ".join(["%s=%s" %(k, v) for k,v in preopts.items()])

        preedge_cmd = "pre_edge(%s._xdat_, %s._ydat_, %s)"
        self.larch(preedge_cmd % (gname, gname, preopts))
        if self.xas_autoe0.IsChecked():
            self.xas_e0.SetValue(lgroup.e0)
        if self.xas_autostep.IsChecked():
            self.xas_step.SetValue(lgroup.edge_step)

        details_group = lgroup
        try:
            details_group = lgroup.pre_edge_details
        except:
            pass
            
        self.xas_pre1.SetValue(details_group.pre1)
        self.xas_pre2.SetValue(details_group.pre2)
        self.xas_nor1.SetValue(details_group.norm1)
        self.xas_nor2.SetValue(details_group.norm2)

        popts1 = dict(style='solid', linewidth=3,
                      marker='None', markersize=4)
        popts2 = dict(style='short dashed', linewidth=2, zorder=-5,
                      marker='None', markersize=4)
        poptsd = dict(style='solid', linewidth=2, zorder=-5,
                      side='right',  y2label='derivative',
                      marker='None', markersize=4)

        lgroup.plot_yarrays = [(lgroup._ydat_, popts1, lgroup.plot_ylabel)]
        y4e0 = lgroup._ydat_
        if out.startswith('raw data with'):
            lgroup.plot_yarrays = [(lgroup._ydat_,    popts1, lgroup.plot_ylabel),
                                   (lgroup.pre_edge,  popts2, 'pre edge'),
                                   (lgroup.post_edge, popts2, 'post edge')]
        elif out.startswith('pre'):
            self.larch('%s.pre_edge_sub = %s.norm * %s.edge_step' %
                       (gname, gname, gname))
            lgroup.plot_yarrays = [(lgroup.pre_edge_sub, popts1,
                                    'pre edge subtracted XAFS')]
            y4e0 = lgroup.pre_edge_sub
        elif 'norm' in out and 'deriv' in out:
            lgroup.plot_yarrays = [(lgroup.norm, popts1, 'normalized XAFS'),
                                   (lgroup.dmude, poptsd, 'derivative')]
            y4e0 = lgroup.norm

        elif out.startswith('norm'):
            lgroup.plot_yarrays = [(lgroup.norm, popts1, 'normalized XAFS')]
            y4e0 = lgroup.norm
        elif out.startswith('deriv'):
            lgroup.plot_yarrays = [(lgroup.dmude, popts1, 'derivative')]
            y4e0 = lgroup.dmude

        lgroup.plot_ymarkers = []
        if self.xas_showe0.IsChecked():
            ie0 = index_of(lgroup._xdat_, lgroup.e0)
            lgroup.plot_ymarkers = [(lgroup.e0, y4e0[ie0], {'label': 'e0'})]
        return

    def init_larch(self):
        t0 = time.time()
        if self.larch is None:
            self.larch = Interpreter()
        self.larch.symtable.set_symbol('_sys.wx.wxapp', wx.GetApp())
        self.larch.symtable.set_symbol('_sys.wx.parent', self)

        self.SetStatusText('ready')
        self.datagroups = self.larch.symtable
        self.title.SetLabel('')

    def write_message(self, s, panel=0):
        """write a message to the Status Bar"""
        self.SetStatusText(s, panel)

    def get_data(self, group, arrayname, correct=False):
        if hasattr(group, 'get_data'):
            return group.get_data(arrayname, correct=correct)
        return getattr(group, arrayname, None)

    def onXASChoice(self, evt=None, **kws):
        if self.groupname is None:
            return
        self.xas_process(self.groupname, **kws)
        self.onPlot()

    def onColumnChoices(self, evt=None):
        """column selections changed ..
        recalculate _xdat_ and _ydat_
        arrays for this larch group"""
        dtcorr = self.dtcorr.IsChecked()
        use_deriv = self.use_deriv.IsChecked()
        ix  = self.xarr.GetSelection()
        x   = self.xarr.GetStringSelection()
        xop = self.xop.GetStringSelection()
        op1 = self.yops[0].GetStringSelection()
        op2 = self.yops[1].GetStringSelection()
        op3 = self.yops[2].GetStringSelection()
        y1  = self.yarr[0].GetStringSelection()
        y2  = self.yarr[1].GetStringSelection()
        y3  = self.yarr[2].GetStringSelection()

        array_sel = {'xop': xop, 'xarr': x,
                     'op1': op1, 'op2': op2, 'op3': op3,
                     'y1': y1, 'y2': y2, 'y3': y3,
                     'dtcorr': dtcorr, 'use_deriv': use_deriv}
        try:
            gname = self.groupname
            lgroup = getattr(self.larch.symtable, gname)
        except:
            gname = SCANGROUP
            lgroup = getattr(self.larch.symtable, gname)

        xlabel = x
        try:
            xunits = lgroup.array_units[ix]
        except:
            xunits = ''
        if xop != '':
            xlabel = "%s(%s)" % (xop, xlabel)
        if xunits != '':
            xlabel = '%s (%s)' % (xlabel, xunits)

        ylabel = y1
        if y2 == '':
            y2, op2 = '1.0', '*'
        else:
            ylabel = "%s%s%s" % (ylabel, op2, y2)
        if y3 == '':
            y3, op3 = '1.0', '*'
        else:
            ylabel = "(%s)%s%s" % (ylabel, op3, y3)

        if op1 != '':
            ylabel = "%s(%s)" % (op1, ylabel)

        if y1 in ('0.0', '1.0'):
            y1 = float(yl1)
        else:
            y1 = self.get_data(lgroup, y1, correct=dtcorr)

        if y2 in ('0.0', '1.0'):
            y2 = float(y2)
            if op2 == '/': y2 = 1.0
        else:
            y2 = self.get_data(lgroup, y2, correct=dtcorr)
        if y3 in ('0.0', '1.0'):
            y3 = float(y3)
            if op3 == '/': y3 = 1.0
        else:
            y3 = self.get_data(lgroup, y3, correct=dtcorr)
        if x not in ('0', '1'):
            x = self.get_data(lgroup, x)
        lgroup._x  = x
        lgroup._y1 = y1
        lgroup._y2 = y2
        lgroup._y3 = y3

        self.larch("%s._xdat_ = %s(%s._x)" % (gname, xop, gname))
        try:
            yexpr = "%s._ydat_ = %s((%s._y1 %s %s._y2) %s %s._y3)"  % (gname,
                    op1, gname, op2, gname, op3, gname)
            self.larch(yexpr)
        except RuntimeWarning:
            self.larch("%s._ydat_ = %s._y1")

        try:
            if use_deriv:
                d_calc = "%s._ydat_ = gradient(%s._ydat_)/gradient(%s._xdat_)"
                self.larch(d_calc % (gname, gname, gname))
        except:
            pass

        try:
            npts = min(len(lgroup._xdat_), len(lgroup._ydat_))
        except AttributeError:
            print( 'Error calculating arrays (npts not correct)')
            return

        del lgroup._x, lgroup._y1, lgroup._y2, lgroup._y3

        lgroup.array_sel   = array_sel
        lgroup.plot_xlabel = xlabel
        lgroup.plot_ylabel = ylabel
        lgroup._xdat_ = np.array( lgroup._xdat_[:npts])
        lgroup._ydat_ = np.array( lgroup._ydat_[:npts])

        if (self.nb.GetCurrentPage() == self.xas_panel):
            self.xas_process(self.groupname, new_mu=True)
        else:
            lgroup.plot_yarrays = [(lgroup._ydat_, {}, None)]

    def onPlot(self, evt=None, opt='new', npts=None, reprocess=False):

        try:
            self.plotframe.Show()
        except: #  wx.PyDeadObjectError
            self.plotframe = PlotFrame(None, size=(650, 400))
            self.plotframe.Show()
            self.plotpanel = self.plotframe.panel

        if reprocess:
            if (self.nb.GetCurrentPage() == self.xas_panel):
                self.xas_process(self.groupname, new_mu=True)

        side = 'left'
        update = False
        plotcmd = self.plotpanel.plot
        if opt in ('left', 'right'):
            side = opt
            plotcmd = self.plotpanel.oplot
        elif opt == 'update'  and npts > 4:
            plotcmd = self.plotpanel.update_line
            update = True
        if 'new' in opt:
            self.plotpanel.clear()
        popts = {'side': side}

        try:
            gname = self.groupname
            lgroup = getattr(self.larch.symtable, gname)
        except:
            gname = SCANGROUP
            lgroup = getattr(self.larch.symtable, gname)
            return

        if not hasattr(lgroup, '_xdat_'):
            self.onColumnChoices()

        lgroup._xdat_ = np.array( lgroup._xdat_[:npts])
        plot_yarrays = [(lgroup._ydat_, {}, None)]
        if hasattr(lgroup, 'plot_yarrays'):
            plot_yarrays = lgroup.plot_yarrays
        #for yarr in plot_yarrays:
        #    yarr = np.array(yarr[:npts])

        path, fname = os.path.split(lgroup.filename)
        popts['label'] = "%s: %s" % (fname, lgroup.plot_ylabel)
        if side == 'right':
            popts['y2label'] = lgroup.plot_ylabel
        else:
            popts['ylabel'] = lgroup.plot_ylabel

        if plotcmd == self.plotpanel.plot:
            popts['title'] = fname

        if update:
            self.plotpanel.set_xlabel(lgroup.plot_xlabel)
            self.plotpanel.set_ylabel(lgroup.plot_ylabel)
            for itrace, yarr, label in enumerate(plot_yarrays):
                plotcmd(itrace, lgroup._xdat_, yarr[0], draw=True,
                        update_limits=((npts < 5) or (npts % 5 == 0)),
                        **yarr[1])
                self.plotpanel.set_xylims((
                    min(lgroup._xdat_), max(lgroup._xdat_),
                    min(yarr), max(yarr)))

        else:
            for yarr in plot_yarrays:
                popts.update(yarr[1])
                if yarr[2] is not None:
                    popts['label'] = yarr[2]
                plotcmd(lgroup._xdat_, yarr[0], **popts)
                plotcmd = self.plotpanel.oplot
            if hasattr(lgroup, 'plot_ymarkers'):
                for x, y, opts in lgroup.plot_ymarkers:
                    popts = {'marker': 'o', 'markersize': 4}
                    popts.update(opts)
                    self.plotpanel.oplot([x], [y], **popts)
            self.plotpanel.canvas.draw()


    def onShowLarchBuffer(self, evt=None):
        if self.larch_buffer is None:
            self.larch_buffer = larchframe.LarchFrame(_larch=self.larch)

        self.larch_buffer.Show()
        self.larch_buffer.Raise()

    def ShowFile(self, evt=None, groupname=None, **kws):
        if groupname is None and evt is not None:
            fpath = self.file_paths[evt.GetInt()]
            groupname = self.file_groups[fpath]

        if not hasattr(self.datagroups, groupname):
            print( 'Error reading file ', groupname)
            return

        self.groupname = groupname
        self.lgroup = getattr(self.datagroups, groupname, None)

        if groupname == SCANGROUP:
            self.lgroup.filename = filename
        elif self.lgroup is not None:
            if hasattr(self.lgroup, 'array_labels'):
                array_labels = self.lgroup.array_labels[:]
            elif hasattr(self.lgroup, 'column_labels'):
                array_labels = self.lgroup.column_labels[:]
            else:
                array_labels = []
                for attr in dir(self.lgroup):
                    if isinstance(getattr(self.lgroup, attr), np.ndarray):
                        array_labels.append(attr)
                self.lgroup.array_labels = array_labels
            self.set_array_labels()
            if hasattr(self.lgroup, 'array_sel'):
                sel = self.lgroup.array_sel
                try:
                    self.xarr.SetStringSelection(sel['xarr'])
                    self.xop.SetStringSelection(sel['xop'])
                    self.yops[0].SetStringSelection(sel['op1'])
                    self.yops[1].SetStringSelection(sel['op2'])
                    self.yops[2].SetStringSelection(sel['op3'])
                    self.yarr[0].SetStringSelection(sel['y1'])
                    self.yarr[1].SetStringSelection(sel['y2'])
                    self.yarr[2].SetStringSelection(sel['y3'])
                    self.dtcorr.SetValue({True: 1, False:0}[sel['dtcorr']])
                    self.use_deriv.SetValue({True: 1, False:0}[sel['use_deriv']])
                except:
                    pass

    def set_array_labels(self, labels=None):
        """set choices for array dropdowns from array labels"""
        array_labels = self.lgroup.array_labels
        xcols  = array_labels[:]
        ycols  = array_labels[:]
        y2cols = array_labels[:] + ['1.0', '0.0', '']
        ncols  = len(xcols)
        self.title.SetLabel(self.lgroup.filename)

        _xarr = self.xarr.GetStringSelection()
        if len(_xarr) < 1 or _xarr not in xcols:
            _xarr = xcols[0]

        _yarr = [[], [], []]
        for j in range(3):
            _yarr[j] = self.yarr[j].GetStringSelection()
            if _yarr[j] not in ycols:
                _yarr[j] = ''

        self.xarr.SetItems(xcols)
        self.xarr.SetStringSelection(_xarr)
        for j in range(3):
            if j == 0:
                self.yarr[j].SetItems(ycols)
                if _yarr[j] in ycols and len(_yarr[j]) > 0:
                    self.yarr[j].SetStringSelection(_yarr[j])
                elif ycols[0] == _xarr and len(ycols)> 1:
                    self.yarr[j].SetStringSelection(ycols[1])
            else:
                self.yarr[j].SetItems(y2cols)
                self.yarr[j].SetStringSelection(_yarr[j])

        inb = 0
        for colname in xcols:
            if 'energ' in colname.lower():
                inb = 1
        self.nb.SetSelection(inb)
        if inb == 1:
            self.InitializeXASPanel()

    def createMenus(self):
        # ppnl = self.plotpanel
        self.menubar = wx.MenuBar()
        #
        fmenu = wx.Menu()
        MenuItem(self, fmenu, "&Open Data File\tCtrl+O",
                 "Read Scan File",  self.onReadScan)

        MenuItem(self, fmenu, "Show Larch Buffer",
                  "Show Larch Programming Buffer",
                  self.onShowLarchBuffer)

        fmenu.AppendSeparator()

        MenuItem(self, fmenu, "&Quit\tCtrl+Q", "Quit program", self.onClose)

        self.menubar.Append(fmenu, "&File")

        omenu = wx.Menu()
        MenuItem(self, omenu, "Edit Column Labels\tCtrl+E",
                 "Edit Column Labels", self.onEditColumnLabels)



        self.menubar.Append(omenu, "Options")


        # fmenu.AppendSeparator()
        # MenuItem(self, fmenu, "&Copy\tCtrl+C",
        #          "Copy Figure to Clipboard", self.onClipboard)
        # MenuItem(self, fmenu, "&Save\tCtrl+S", "Save Figure", self.onSaveFig)
        # MenuItem(self, fmenu, "&Print\tCtrl+P", "Print Figure", self.onPrint)
        # MenuItem(self, fmenu, "Page Setup", "Print Page Setup", self.onPrintSetup)
        # MenuItem(self, fmenu, "Preview", "Print Preview", self.onPrintPreview)
        #

        #MenuItem(self, pmenu, "Unzoom\tCtrl+Z", "Unzoom Plot", self.onUnzoom)
        ##pmenu.AppendSeparator()
        #MenuItem(self, pmenu, "Toggle Legend\tCtrl+L",
        #         "Toggle Legend on Plot", self.onToggleLegend)
        #MenuItem(self, pmenu, "Toggle Grid\tCtrl+G",
        #         "Toggle Grid on Plot", self.onToggleGrid)
        # self.menubar.Append(pmenu, "Plot Options")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)

    def onAbout(self,evt):
        dlg = wx.MessageDialog(self, self._about,"About Epics StepScan",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onClose(self,evt):
        save_workdir('scanviewer.dat')

        try:
            self.plotframe.Destroy()
        except:
            pass
        if self.larch_buffer is not None:
            try:
                self.larch_buffer.onClose()
            except:
                pass

        for nam in dir(self.larch.symtable._sys.wx):
            obj = getattr(self.larch.symtable._sys.wx, nam)
            del obj

        self.Destroy()

    def show_subframe(self, name, frameclass):
        shown = False
        if name in self.subframes:
            try:
                self.subframes[name].Raise()
                shown = True
            except:
                del self.subframes[name]
        if not shown:
            self.subframes[name] = frameclass(self)


    def onEditColumnLabels(self, evt=None):
        self.show_subframe('coledit', EditColumnFrame)

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

            gname = '_sview0001'
            count, maxcount = 1, 9999
            while hasattr(self.datagroups, gname) and count < maxcount:
                count += 1
                gname = '_sview%4.4i' % count

            if hasattr(self.datagroups, gname):
                gname = randname()

            parent, fname = os.path.split(path)
            if self.config['chdir_on_fileopen']:
                os.chdir(parent)

            fh = open(path, 'r')
            line1 = fh.readline().lower()
            fh.close()
            reader = 'read_ascii'
            if 'epics scan' in line1:
                reader = 'read_gsescan'
            elif 'xdi' in line1:
                reader = 'read_xdi'
                if 'epics stepscan file' in line1:
                    reader = 'read_gsexdi'

            self.larch("%s = %s('%s')" % (gname, reader, path))
            self.larch("%s.path  = '%s'"     % (gname, path))
            self.filelist.Append(fname)
            self.file_paths.append(path)
            self.file_groups[path] = gname

            self.ShowFile(groupname=gname)

        dlg.Destroy()

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

def _scanviewer(wxparent=None, _larch=None,  **kws):
    s = ScanViewerFrame(_larch=_larch, **kws)
    s.Show()
    s.Raise()

def _mapviewer(wxparent=None, _larch=None,  **kws):
    s = MapViewerFrame(_larch=_larch, **kws)
    s.Show()
    s.Raise()

def _larchgui(wxparent=None, _larch=None, **kws):
    lg =larchframe.LarchFrame(_larch=_larch)
    lg.Show()
    lg.Raise()


def registerLarchPlugin():
    return ('_plotter', {'scanviewer':_scanviewer,
                         'mapviewer':_mapviewer,
                         'larchgui':_larchgui})
