
import sys
import time

import wx
import wx.lib.scrolledpanel as scrolled

from ..ordereddict import OrderedDict
from .gui_utils import GUIColors, set_font_with_children, YesNo
from .gui_utils import add_button, pack, SimpleText


LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
CEN  = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL|wx.ALL

class PositionerFrame(wx.Frame) :
    """Frame to Setup Scan Positioners"""
    def __init__(self, parent, pos=(-1, -1)):

        self.parent = parent
        self.scandb = parent._scandb

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
        panel = scrolled.ScrolledPanel(self, size=(675, 500))
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        # title row
        title = SimpleText(panel, 'Positioners Setup',  font=titlefont,
                           colour=self.colors.title, style=tstyle)

        sizer.Add(title,        (0, 0), (1, 3), LEFT, 5)


        desc = wx.StaticText(panel, -1, label='Positioner Settling Time (sec): ',
                             size=(180, -1))
        
        self.settle_time = wx.TextCtrl(panel, size=(75, -1),
                            value=self.scandb.get_info('pos_settle_time', '0.001'))
        sizer.Add(desc,              (1, 0), (1, 2), CEN,  3)
        sizer.Add(self.settle_time,  (1, 2), (1, 1), LEFT, 3)

        
        ir = 2
        sizer.Add(self.add_subtitle(panel, 'Linear/Mesh Scan Positioners'),
                  (ir, 0),  (1, 4),  LEFT, 1)
        ir += 1
        sizer.Add(SimpleText(panel, label='Description', size=(175, -1)),
                  (ir, 0), (1, 1), rlabstyle, 2)
        sizer.Add(SimpleText(panel, label='Drive PV', size=(175, -1)),
                  (ir, 1), (1, 1), labstyle, 2)
        sizer.Add(SimpleText(panel, label='Readback PV', size=(175, -1)),
                  (ir, 2), (1, 1), labstyle, 2)
        sizer.Add(SimpleText(panel, label='Erase?', size=(60, -1)),
                  (ir, 3), (1, 1), labstyle, 2)

        self.widlist = []
        for pos in self.scandb.getall('scanpositioners'):
            desc   = wx.TextCtrl(panel, -1, value=pos.name, size=(175, -1))
            pvctrl = wx.TextCtrl(panel, value=pos.drivepv,  size=(175, -1))
            rdctrl = wx.TextCtrl(panel, value=pos.readpv,  size=(175, -1))
            delpv  = YesNo(panel, defaultyes=False)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
            sizer.Add(rdctrl, (ir, 2), (1, 1), labstyle, 2)
            sizer.Add(delpv,  (ir, 3), (1, 1), labstyle, 2)
            self.widlist.append(('line', pos, desc, pvctrl, rdctrl, delpv))

        for i in range(2):
            desc   = wx.TextCtrl(panel, -1, value='', size=(175, -1))
            pvctrl = wx.TextCtrl(panel, value='', size=(175, -1))
            rdctrl = wx.TextCtrl(panel, value='', size=(175, -1))
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
            sizer.Add(rdctrl, (ir, 2), (1, 1), labstyle, 2)
            self.widlist.append(('line', None, desc, pvctrl, rdctrl, None))

        # xafs
        ir += 1
        sizer.Add(self.add_subtitle(panel, 'Energy for XAFS Scans'),
                  (ir, 0),  (1, 4),  LEFT, 1)

        drive_pv = self.scandb.get_info('energy_drive')
        read_pv = self.scandb.get_info('energy_read')
        desc   = wx.TextCtrl(panel, -1, value='Energy PV', size=(175, -1))
        pvctrl = wx.TextCtrl(panel, value=drive_pv, size=(175, -1))
        rdctrl = wx.TextCtrl(panel, value=read_pv,  size=(175, -1))
        ir +=1
        sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
        sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
        sizer.Add(rdctrl, (ir, 2), (1, 1), labstyle, 2)
        self.widlist.append(('xafs', None, desc, pvctrl, rdctrl, None))

        # slew scans
        ir += 1
        sizer.Add(self.add_subtitle(panel, 'Slew Scan Positioners'),
                  (ir, 0),  (1, 4),  LEFT, 1)

        for pos in self.scandb.getall('slewscanpositioners'):
            desc   = wx.TextCtrl(panel, -1, value=pos.name, size=(175, -1))
            pvctrl = wx.TextCtrl(panel, value=pos.drivepv,  size=(175, -1))
            rdctrl = wx.TextCtrl(panel, value=pos.readpv,  size=(175, -1))
            delpv  = YesNo(panel, defaultyes=False)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
            sizer.Add(rdctrl, (ir, 2), (1, 1), labstyle, 2)
            sizer.Add(delpv,  (ir, 3), (1, 1), labstyle, 2)
            self.widlist.append(('slew', pos, desc, pvctrl, rdctrl, delpv))

        for i in range(1):
            desc   = wx.TextCtrl(panel, -1, value='', size=(175, -1))
            pvctrl = wx.TextCtrl(panel, value='', size=(175, -1))
            rdctrl = wx.TextCtrl(panel, value='', size=(175, -1))
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), rlabstyle, 2)
            sizer.Add(pvctrl, (ir, 1), (1, 1), labstyle, 2)
            sizer.Add(rdctrl, (ir, 2), (1, 1), labstyle, 2)
            self.widlist.append(('slew', None, desc, pvctrl, rdctrl, None))

        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 3), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), wx.ALIGN_LEFT|wx.EXPAND, 3)
        #
        ir += 1
        sizer.Add(self.make_buttons(panel), (ir, 0), (1, 2), wx.ALIGN_LEFT, 3)

        pack(panel, sizer)

        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def add_subtitle(self, panel, text):
        p = wx.Panel(panel)
        s = wx.BoxSizer(wx.HORIZONTAL)
        s.Add(wx.StaticLine(p, size=(125, 3), style=wx.LI_HORIZONTAL), 0, LEFT, 5)
        s.Add(SimpleText(p, text,  colour='#333377'),  0, LEFT, 5)
        s.Add(wx.StaticLine(p, size=(185, 3), style=wx.LI_HORIZONTAL), 1, LEFT, 5)
        pack(p, s)
        return p

    def make_buttons(self, panel):
        btnsizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(panel, wx.ID_OK)
        btn_no = wx.Button(panel, wx.ID_CANCEL)
        panel.Bind(wx.EVT_BUTTON, self.onApply, btn_ok)
        panel.Bind(wx.EVT_BUTTON, self.onClose, btn_no)
        btn_ok.SetDefault()
        btnsizer.AddButton(btn_ok)
        btnsizer.AddButton(btn_no)

        btnsizer.Realize()
        return btnsizer

    def onApply(self, event=None):
        self.scandb.set_info('pos_settle_time',
                             float(self.settle_time.GetValue()))
        for w in self.widlist:
            wtype, obj, name, drivepv, readpv, erase = w
            if erase is not None:
                erase = erase.GetSelection()
            else:
                erase = False
            name    = name.GetValue().strip()
            drivepv = drivepv.GetValue().strip()
            if len(name) < 1 or len(drivepv) < 1:
                continue

            readpv  = readpv.GetValue().strip()
            if len(readpv) < 1:
                readpv = drivepv
            if erase and obj is not None:
                delete = self.scandb.del_positioner
                if wtype == 'slew':
                    delete = self.scandb.del_slewpositioner
                delete(obj.name)
            elif obj is not None:
                obj.name = name
                obj.drivepv = drivepv
                obj.readpv = readpv
            elif wtype == 'xafs':
                self.scandb.set_info('energy_read', readpv)
                self.scandb.set_info('energy_drive', drivepv)
            elif obj is None and wtype == 'line':
                self.scandb.add_positioner(name, drivepv, readpv=readpv)
            elif obj is None and wtype == 'slew':
                self.scandb.add_slewpositioner(name, drivepv, readpv=readpv)

        self.scandb.commit()
        for panel in self.parent.scanpanels.values():
            panel.update_positioners()

        self.Destroy()


    def onClose(self, event=None):
        self.Destroy()

