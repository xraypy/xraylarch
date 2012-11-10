
import sys
import time

import wx
import wx.lib.scrolledpanel as scrolled

from ..ordereddict import OrderedDict
from ..detectors import (SimpleDetector, ScalerDetector, McaDetector,
                         MultiMcaDetector, AreaDetector)

from .gui_utils import GUIColors, set_font_with_children, YesNo, Closure
from .gui_utils import add_button, add_choice, pack, SimpleText, FloatCtrl, HyperText
from .pvconnector import PVNameCtrl

LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
CEN  = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL|wx.ALL

DET_CHOICES = ('Scaler', 'MCA', 'MultiMCA', 'AreaDetector')
AD_File_plugins = ('None','TIFF1', 'JPEG1', 'NetCDF1', 'HDF1', 'Nexus1', 'Magick1')

class DetectorFrame(wx.Frame) :
    """Frame to Setup Scan Detectors"""
    def __init__(self, parent=None, pos=(-1, -1), config=None, pvlist=None,
                 detectors=None,  extra_counters=None):
        self.parent = parent
        self.config = config
        self.pvlist = pvlist
        if detectors is None: detectors = OrderedDict()
        if extra_counters is None: extra_counters = OrderedDict()
        self.detectors = detectors
        self.extra_counter = extra_counters
        self.pvlist = pvlist

        style    = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL

        self.Font10=wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        titlefont = wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        wx.Frame.__init__(self, None, -1, 'Epics Scanning: Detector Setup')
        self.SetFont(self.Font10)

        sizer = wx.GridBagSizer(12, 5)
        panel = scrolled.ScrolledPanel(self, size=(750, 525))
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        # title row
        title = SimpleText(panel, 'Detector Setup',  font=titlefont,
                           minsize=(130, -1),   colour=self.colors.title, style=LEFT)

        sizer.Add(title,        (0, 0), (1, 1), LEFT|wx.ALL, 2)

        add_new = HyperText(panel, 'Show all Triggers and Counters',
                            colour=(120, 0, 200), action=self.onView)
        sizer.Add(add_new,      (0, 1), (1, 2), LEFT, 2)

        ir = 1
        sizer.Add(self.add_subtitle(panel, 'Available Detectors'),
                  (ir, 0),  (1, 5),  LEFT, 0)

        ir +=1
        sizer.Add(SimpleText(panel, label='Kind',  size=(75, -1)),
                  (ir, 0), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='PV prefix', size=(175, -1)),
                  (ir, 1), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='Use?', size=(100, -1)),
                  (ir, 2), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='Configure:', size=(100, -1)),
                  (ir, 3), (1, 1), LEFT, 1)
        self.widlist = []
        for key, value in self.config.detectors.items():
            ir +=1
            prefix, opts = value
            if 'use' not in opts:
                opts['use'] = 'Yes'
            desc   = SimpleText(panel, label=opts['kind'].title().strip(), size=(125, -1))
            pvctrl = wx.TextCtrl(panel, value=prefix,   size=(175, -1))
            use    = YesNo(panel, defaultyes=(opts['use'] == 'Yes'))
            det    = None

            detail = add_button(panel, ' Details',     size=(70, -1),
                            action=Closure(self.onDetDetails, prefix=prefix, opts=opts, det=det))

            sizer.Add(desc,   (ir, 0), (1, 1), LEFT, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LEFT, 1)
            sizer.Add(use,    (ir, 2), (1, 1), LEFT, 1)
            sizer.Add(detail, (ir, 3), (1, 1), LEFT, 1)

            #             opanel, owids = self.opts_panel(panel, opts)
            #             sizer.Add(opanel, (ir, 3), (1, 1), wx.ALIGN_CENTER|wx.GROW|wx.ALL, 1)
            wids = ['det', ir, desc, pvctrl, detail, det]
            self.widlist.append(wids)

        # select a new detector
        for i in range(2):
            ir +=1
            desc   = add_choice(panel, DET_CHOICES, size=(125, -1))
            pvctrl = wx.TextCtrl(panel, value='',   size=(175, -1))
            use    = YesNo(panel)
            sizer.Add(desc,   (ir, 0), (1, 1), CEN,  2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LEFT, 1)
            sizer.Add(use,    (ir, 2), (1, 1), LEFT, 1)
            wids = ['det', ir, desc, pvctrl, use]
            self.widlist.append(wids)

        ir += 1
        sizer.Add(self.add_subtitle(panel, 'Additional Counters'),
                  (ir, 0),  (1, 5),  LEFT, 1)

        ###
        ir += 1
        sizer.Add(SimpleText(panel, label='Label',  size=(50, -1)),
                  (ir, 0), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='PV name', size=(175, -1)),
                  (ir, 1), (1, 1), LEFT, 1)
        sizer.Add(SimpleText(panel, label='Use?', size=(100, -1)),
                  (ir, 2), (1, 2), LEFT, 1)

        for label, pv in self.config.counters.items():
            desc   = wx.TextCtrl(panel, -1, value=label, size=(175, -1))
            pvctrl = PVNameCtrl(panel, value=pv, pvlist=self.pvlist, size=(175, -1))
            use     = YesNo(panel)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), LEFT, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LEFT, 1)
            sizer.Add(use,    (ir, 2), (1, 1), LEFT, 1)
            self.widlist.append(('counters', desc, pvctrl, use))

        for i in range(3):
            desc   = wx.TextCtrl(panel, -1, value='', size=(175, -1))
            pvctrl = PVNameCtrl(panel, value='', pvlist=self.pvlist, size=(175, -1))
            use     = YesNo(panel)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), LEFT, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LEFT, 1)
            sizer.Add(use,    (ir, 2), (1, 1), LEFT, 1)
            self.widlist.append(('counters', desc, pvctrl, use))
        ###
        ir += 1
        sizer.Add(self.make_buttons(panel), (ir, 0), (1, 3), wx.ALIGN_CENTER|wx.GROW, 1)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def onDetDetails(self, evt=None, prefix=None, opts=None,  **kws):
        print 'show detector detail frame: include options, trigger, etc'
        print prefix, opts

    def opts_panel(self, parent, opts):
        pane = wx.Panel(parent)
        sizer  = wx.BoxSizer(wx.HORIZONTAL)
        kind = opts.get('kind', '').lower()
        wids = []
        if kind == 'scaler':
            sizer.Add(SimpleText(pane, '#Channels=', size=(100, -1)), 0,  LEFT, 0)
            nchan = FloatCtrl(pane, value=opts.get('nchan', 8),
                              size=(25, -1), precision=0, minval=0)
            sizer.Add(nchan, 0, LEFT, 0)
            sizer.Add(SimpleText(pane, 'Use Raw/Calc:', size=(120, -1)), 0,  LEFT, 0)
            val = {True:1, False:0}[opts.get('use_calc', True)]
            use_calc = YesNo(pane, choices=('Raw', 'Calc'), size=(75, -1))
            sizer.Add(use_calc, 0,  LEFT, 0)
            wids = [nchan, use_calc]
        elif kind.startswith('area'):
            sizer.Add(SimpleText(pane, 'Use File Plugin:', size=(120, -1)), 0,  LEFT, 0)
            plugin = wx.Choice(pane, choices=AD_File_plugins)
            plugin.SetStringSelection(opts.get('file_plugin', 'None'))
            sizer.Add(plugin, 0, LEFT, 0)
            wids = [plugin]
        elif kind == 'mca':
            sizer.Add(SimpleText(pane, '#ROIs=', size=(80, -1)), 0,  LEFT, 0)
            nrois = FloatCtrl(pane, value=opts.get('nrois', 32),
                              size=(25, -1), precision=0, minval=0)
            sizer.Add(nrois, 0, LEFT, 0)
            sizer.Add(SimpleText(pane, 'Use Sum/Net:', size=(120, -1)), 0,  LEFT, 0)
            val = {True:1, False:0}[opts.get('use_net', False)]
            use_net = YesNo(pane, choices=('Sum', 'Net'), size=(75, -1))
            sizer.Add(use_net, 0,  LEFT, 0)
            sizer.Add(SimpleText(pane, 'Save Full Spectra:', size=(120, -1)), 0,  LEFT, 0)
            val = {True:1, False:0}[opts.get('use_full', False)]
            use_full = YesNo(pane, size=(75, -1))
            sizer.Add(use_full, 0,  LEFT, 0)
            wids = [nrois, use_net, use_full]

        elif kind.startswith('multi'):
            sizer.Add(SimpleText(pane, '#MCAs=', size=(80, -1)), 0,  LEFT, 0)
            nchan = FloatCtrl(pane, value=opts.get('nmcas', 4),
                              size=(25, -1), precision=0, minval=0)
            sizer.Add(nchan, 0, LEFT, 0)
            sizer.Add(SimpleText(pane, '#ROIs=', size=(80, -1)), 0,  LEFT, 0)
            nrois = FloatCtrl(pane, value=opts.get('nrois', 32),
                              size=(25, -1), precision=0, minval=0)
            sizer.Add(nrois, 0, LEFT, 0)
            sizer.Add(SimpleText(pane, 'Use Sum/Net:', size=(120, -1)), 0,  LEFT, 0)
            val = {True:1, False:0}[opts.get('use_net', False)]
            use_net = YesNo(pane, choices=('Sum', 'Net'), size=(75, -1))
            sizer.Add(use_net, 0,  LEFT, 0)
            sizer.Add(SimpleText(pane, 'Save Full Spectra:', size=(120, -1)), 0,  LEFT, 0)
            val = {True:1, False:0}[opts.get('use_full', False)]
            use_full = YesNo(pane, size=(75, -1))
            sizer.Add(use_full, 0,  LEFT, 0)
            wids = [nchan, nrois, use_net, use_full]

        pack(pane, sizer)
        return pane, wids

    def add_subtitle(self, panel, text):
        p = wx.Panel(panel)
        s = wx.BoxSizer(wx.HORIZONTAL)
        s.Add(wx.StaticLine(p, size=(120, 3), style=wx.LI_HORIZONTAL), 0, LEFT, 5)
        s.Add(SimpleText(p, text,  colour='#333377'),  0, LEFT, 5)
        s.Add(wx.StaticLine(p, size=(260, 3), style=wx.LI_HORIZONTAL), 1, LEFT, 5)
        pack(p, s)
        return p

    def make_buttons(self, panel):
        bpanel = wx.Panel(panel, size=(200, 25))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        _ok    = add_button(bpanel, 'Apply',     size=(70, -1),
                            action=self.onApply)
        _cancel = add_button(bpanel, 'Close', size=(70, -1), action=self.onClose)
        sizer.Add(_ok,     0, wx.ALIGN_LEFT,  2)
        sizer.Add(_cancel, 0, wx.ALIGN_RIGHT,  2)
        pack(bpanel, sizer)
        return bpanel

    def onView(self, event=None, label=None):
        print 'list all triggers, list all counters with add/remove button'

    def onNewDetector(self, event=None, **kws):
        print 'add new detector ', row

    def onApply(self, event=None):
        print 'Detector apply'

    def onClose(self, event=None):
        self.Destroy()

