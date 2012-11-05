
import sys
import time

import wx
import wx.lib.scrolledpanel as scrolled

from ..ordereddict import OrderedDict
from .gui_utils import GUIColors, set_font_with_children, YesNo
from .gui_utils import add_button, pack, SimpleText
from .pvconnector import PVNameCtrl

class DetectorFrame(wx.Frame) :
    """Frame to Setup Scan Detectors"""
    def __init__(self, parent=None, pos=(-1, -1), config=None, pvlist=None):
        self.parent = parent
        self.config = config
        self.pvlist = pvlist

        style    = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL
        labstyle  = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        rlabstyle = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        tstyle    = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL

        self.Font10=wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        titlefont = wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        wx.Frame.__init__(self, None, -1, 'Epics Scanning: Detector Setup')
        self.SetFont(self.Font10)

        sizer = wx.GridBagSizer(10, 7)
        panel = scrolled.ScrolledPanel(self, size=(725, 500))
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        # title row
        title = SimpleText(panel, 'Detector Setup',  font=titlefont,
                           minsize=(130, -1),   colour=self.colors.title, style=tstyle)

        sizer.Add(title,        (0, 0), (1, 2), labstyle|wx.ALL, 2)

        add_new = add_button(panel, 'Add Detector',     size=(120, -1),
                            action=self.onNewDetector)
        sizer.Add(add_new,      (0, 3), (1, 1), wx.ALIGN_CENTER|wx.ALL, 2)

        ir = 1
        self.add_subtitle(panel, sizer, ir, 'Available Detectors')
        ir += 1
        sizer.Add(SimpleText(panel, label='Type',  size=(50, -1)),
                  (ir, 0), (1, 1), labstyle, 1)
        sizer.Add(SimpleText(panel, label='PV Prefix', size=(175, -1)),
                  (ir, 1), (1, 1), labstyle, 1)
        sizer.Add(SimpleText(panel, label='Use?', size=(100, -1)),
                  (ir, 2), (1, 1), labstyle, 1)
        sizer.Add(SimpleText(panel, label='Options', size=(200, -1)),
                  (ir, 3), (1, 1), labstyle, 1)
        self.widlist = []
        for key, value in self.config.detectors.items():
            ir +=1
            pvname, opts = value

            desc   = SimpleText(panel, label=opts['kind'], size=(100, -1))
            pvctrl = PVNameCtrl(panel, value=pvname, pvlist=self.pvlist, size=(175, -1))
            opts   = SimpleText(panel, label=repr(opts))
            use    = YesNo(panel)
            sizer.Add(desc,   (ir, 0), (1, 1), labstyle, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 1)
            sizer.Add(use,    (ir, 2), (1, 1), labstyle, 1)
            sizer.Add(opts,   (ir, 3), (1, 1), labstyle, 1)
            self.widlist.append(('detectors', desc, pvctrl, use, opts))

        ir += 1
        self.add_subtitle(panel, sizer, ir, 'Additional Counters')

        for i,v in self.config.counters.items():
            print i, v

        ###
        ir += 1
        sizer.Add(SimpleText(panel, label='Label',  size=(50, -1)),
                  (ir, 0), (1, 1), labstyle, 1)
        sizer.Add(SimpleText(panel, label='PV name', size=(175, -1)),
                  (ir, 1), (1, 1), labstyle, 1)
        sizer.Add(SimpleText(panel, label='Use?', size=(100, -1)),
                  (ir, 2), (1, 1), labstyle, 1)

        for label, pv in self.config.counters.items():
            desc   = wx.TextCtrl(panel, -1, value=label, size=(175, -1))
            pvctrl = PVNameCtrl(panel, value=pv, pvlist=self.pvlist, size=(175, -1))
            use     = YesNo(panel)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), labstyle, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 1)
            sizer.Add(use,    (ir, 2), (1, 1), labstyle, 1)
            self.widlist.append(('counters', desc, pvctrl, use))

        for i in range(4):
            desc   = wx.TextCtrl(panel, -1, value='', size=(175, -1))
            pvctrl = PVNameCtrl(panel, value='', pvlist=self.pvlist, size=(175, -1))
            use     = YesNo(panel)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), labstyle, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 1)
            sizer.Add(use,    (ir, 2), (1, 1), labstyle, 1)
            self.widlist.append(('counters', desc, pvctrl, use))
        ###

        ir += 1
        sizer.Add(self.make_buttons(panel), (ir, 0), (1, 3), wx.ALIGN_CENTER|wx.GROW, 1)
        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 5), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), wx.ALIGN_LEFT|wx.GROW|wx.ALL, 1)

        pack(panel, sizer)

        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def add_subtitle(self, panel, sizer, row, text):
        sizer.Add(wx.StaticLine(panel, size=(50, 2), style=wx.LI_HORIZONTAL),
                  (row, 0), (1, 1), wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.GROW, 3)
        sizer.Add(SimpleText(panel, text,  colour='#333377'),
                  (row, 1), (1, 1), wx.ALIGN_LEFT|wx.GROW|wx.ALL, 3)
        sizer.Add(wx.StaticLine(panel, size=(50, 2), style=wx.LI_HORIZONTAL),
                  (row, 2), (1, 2), wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.GROW, 3)


    def make_buttons(self, panel):
        bpanel = wx.Panel(panel, size=(200, 25))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        _ok    = add_button(bpanel, 'OK',     size=(70, -1),
                            action=self.onOK)
        _cancel = add_button(bpanel, 'Cancel', size=(70, -1), action=self.onCancel)
        sizer.Add(_ok,     0, wx.ALIGN_LEFT,  2)
        sizer.Add(_cancel, 0, wx.ALIGN_RIGHT,  2)
        pack(bpanel, sizer)
        return bpanel

    def onNewDetector(self, event=None):
        print 'frame to add new detector'

    def onOK(self, event=None):
        step_pos = OrderedDict()
        slew_pos = OrderedDict()
        energy_drive= self.config.xafs['energy_drive']
        energy_read = self.config.xafs['energy_read']
        for wids in self.widlist:
            kind = wids[0]
            desc  = wids[1].GetValue().strip()
            drive = wids[2].GetValue().strip()
            read  = wids[3].GetValue().strip()
            use  = len(desc) > 0
            if wids[4] is not None:
                use = use and wids[4].GetSelection()==0
            if use and kind == 'stepscan':
                step_pos[desc] = (drive, read)
            elif use and kind == 'slewscan':
                slew_pos[desc] = (drive, read)
            elif use and kind == 'xafs':
                energy_drive = drive
                energy_read = read
        self.config.xafs['energy_drive'] = energy_drive
        self.config.xafs['energy_read']  = energy_read
        self.config.positioners = step_pos
        self.config.slewscan_positioners = slew_pos
        for p in self.scanpanels:
            p.use_config(self.config)
        self.Destroy()

    def onCancel(self, event=None):
        self.Destroy()

