
import sys
import time

import wx
import wx.lib.scrolledpanel as scrolled

from ..ordereddict import OrderedDict
from .gui_utils import GUIColors, set_font_with_children, YesNo
from .gui_utils import add_button, pack, SimpleText
from .pvconnector import PVNameCtrl

class PositionerFrame(wx.Frame) :
    """Frame to Setup Scan Positioners"""
    def __init__(self, parent=None, pos=(-1, -1),
                 config=None, pvlist=None, scanpanels=None):

        self.parent = parent
        self.config = config
        self.pvlist = pvlist
        self.scanpanels = scanpanels

        style    = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL
        labstyle  = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        rlabstyle = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        tstyle    = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL

        self.Font10=wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        titlefont = wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        wx.Frame.__init__(self, None, -1,
                          'Epics Scanning: Positioners Setup')

        self.SetFont(self.Font10)
        sizer = wx.GridBagSizer(10, 5)
        panel = scrolled.ScrolledPanel(self, size=(725, 500))
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        # title row
        title = SimpleText(panel, 'Positioners Setup',  font=titlefont,
                           minsize=(130, -1),   colour=self.colors.title, style=tstyle)

        sizer.Add(title,        (0, 1), (1, 3), labstyle|wx.ALL, 0)
        ir = 1
        self.add_subtitle(panel, sizer, ir, 'Linear/Mesh Scan Positioners')
        ir += 1
        sizer.Add(SimpleText(panel, label='Description', size=(175, -1)),
                  (ir, 0), (1, 1), rlabstyle, 2)
        sizer.Add(SimpleText(panel, label='Drive PV', size=(175, -1)),
                  (ir, 1), (1, 1), labstyle, 2)
        sizer.Add(SimpleText(panel, label='Readback PV', size=(175, -1)),
                  (ir, 2), (1, 1), labstyle, 2)
        sizer.Add(SimpleText(panel, label='Remove?', size=(100, -1)),
                  (ir, 3), (1, 1), labstyle, 2)

        self.widlist = []
        for label, pvs in self.config.positioners.items():
            desc   = wx.TextCtrl(panel, -1, value=label, size=(175, -1))
            pvctrl = PVNameCtrl(panel, value=pvs[0], pvlist=self.pvlist, size=(175, -1))
            rdctrl = PVNameCtrl(panel, value=pvs[1], pvlist=self.pvlist, size=(175, -1))
            delpv  = YesNo(panel, choices=('Remove', 'Keep'), size=(100, -1))
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
            sizer.Add(rdctrl, (ir, 2), (1, 1), labstyle, 2)
            sizer.Add(delpv,  (ir, 3), (1, 1), labstyle, 2)
            self.widlist.append(('stepscan', desc, pvctrl, rdctrl, delpv))

        for i in range(4):
            desc   = wx.TextCtrl(panel, -1, value='', size=(175, -1))
            pvctrl = PVNameCtrl(panel, value='', pvlist=self.pvlist, size=(175, -1))
            rdctrl = PVNameCtrl(panel, value='', pvlist=self.pvlist, size=(175, -1))
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
            sizer.Add(rdctrl, (ir, 2), (1, 1), labstyle, 2)
            self.widlist.append(('stepscan', desc, pvctrl, rdctrl, None))

        # xafs
        ir += 1
        self.add_subtitle(panel, sizer, ir, 'Energy for XAFS Scans')

        drive_pv = self.config.xafs['energy_drive']
        read_pv = self.config.xafs['energy_read']
        desc   = wx.TextCtrl(panel, -1, value='Energy PV', size=(175, -1))
        pvctrl = PVNameCtrl(panel, value=drive_pv, pvlist=self.pvlist, size=(175, -1))
        rdctrl = PVNameCtrl(panel, value=read_pv, pvlist=self.pvlist, size=(175, -1))
        ir +=1
        sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
        sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
        sizer.Add(rdctrl, (ir, 2), (1, 1), labstyle, 2)
        self.widlist.append(('xafs', desc, pvctrl, rdctrl, None))

        # slew scans
        ir += 1
        self.add_subtitle(panel, sizer, ir, 'Slew Scan Positioners')

        for label, pvs in self.config.slewscan_positioners.items():
            desc   = wx.TextCtrl(panel, -1, value=label, size=(175, -1))
            pvctrl = PVNameCtrl(panel, value=pvs[0], pvlist=self.pvlist, size=(175, -1))
            rdctrl = PVNameCtrl(panel, value=pvs[1], pvlist=self.pvlist, size=(175, -1))
            delpv  = YesNo(panel, choices=('Remove', 'Keep'), size=(100, -1))
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
            sizer.Add(rdctrl, (ir, 2), (1, 1), labstyle, 2)
            sizer.Add(delpv,  (ir, 3), (1, 1), labstyle, 2)
            self.widlist.append(('slewscan', desc, pvctrl, rdctrl, delpv))

        for i in range(1):
            desc   = wx.TextCtrl(panel, -1, value='', size=(175, -1))
            pvctrl = PVNameCtrl(panel, value='', pvlist=self.pvlist, size=(175, -1))
            rdctrl = PVNameCtrl(panel, value='', pvlist=self.pvlist, size=(175, -1))
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
            sizer.Add(rdctrl, (ir, 2), (1, 1), labstyle, 2)
            self.widlist.append(('slewscan', desc, pvctrl, rdctrl, None))

        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 5), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), wx.ALIGN_LEFT|wx.GROW|wx.ALL, 3)
        #
        ir += 1
        sizer.Add(self.make_buttons(panel), (ir, 0), (1, 3), wx.ALIGN_CENTER|wx.GROW, 3)
        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 5), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), wx.ALIGN_LEFT|wx.GROW|wx.ALL, 3)

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
                use = use and wids[4].GetSelection()==1
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

