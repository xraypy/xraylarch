
import sys
import time

import wx
import wx.lib.scrolledpanel as scrolled

from .gui_utils import (GUIColors, set_font_with_children, YesNo,
                        add_button, add_subtitle, okcancel, Font,
                        pack, SimpleText, LCEN, CEN, RCEN)

LCEN |= wx.ALL
RCEN |= wx.ALL
CEN  |= wx.ALL

class PositionerFrame(wx.Frame) :
    """Frame to Setup Scan Positioners"""
    def __init__(self, parent, pos=(-1, -1)):

        self.parent = parent
        self.scandb = parent.scandb

        wx.Frame.__init__(self, None, -1,
                          'Epics Scanning: Positioners Setup',
                          style=wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.SetFont(Font(9))
        sizer = wx.GridBagSizer(10, 5)
        panel = scrolled.ScrolledPanel(self) 
        self.SetMinSize((650, 600))
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        # title row
        title = SimpleText(panel, 'Positioners Setup',  font=Font(13),
                           colour=self.colors.title, style=LCEN)

        sizer.Add(title,      (0, 0), (1, 3), LCEN, 5)


        desc = wx.StaticText(panel, -1, label='Positioner Settling Time (sec): ',
                             size=(180, -1))
        
        self.settle_time = wx.TextCtrl(panel, size=(75, -1),
                            value=self.scandb.get_info('pos_settle_time', '0.001'))
        sizer.Add(desc,              (1, 0), (1, 2), CEN,  1)
        sizer.Add(self.settle_time,  (1, 2), (1, 1), LCEN, 1)

        
        ir = 2
        sizer.Add(add_subtitle(panel, 'Linear/Mesh Scan Positioners'),
                  (ir, 0),  (1, 4),  LCEN, 1)
        ir += 1
        sizer.Add(SimpleText(panel, label='Description', size=(175, -1)),
                  (ir, 0), (1, 1), RCEN, 1)
        sizer.Add(SimpleText(panel, label='Drive PV', size=(175, -1)),
                  (ir, 1), (1, 1), RCEN, 1)
        sizer.Add(SimpleText(panel, label='Readback PV', size=(175, -1)),
                  (ir, 2), (1, 1), LCEN, 1)
        sizer.Add(SimpleText(panel, label='Erase?', size=(60, -1)),
                  (ir, 3), (1, 1), LCEN, 1)

        self.widlist = []
        poslist = []
        for pos in self.scandb.getall('scanpositioners'):
            poslist.append(pos.name)
            desc   = wx.TextCtrl(panel, -1, value=pos.name, size=(175, -1))
            pvctrl = wx.TextCtrl(panel, value=pos.drivepv,  size=(175, -1))
            rdctrl = wx.TextCtrl(panel, value=pos.readpv,  size=(175, -1))
            delpv  = YesNo(panel, defaultyes=False)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), RCEN, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LCEN, 1)
            sizer.Add(rdctrl, (ir, 2), (1, 1), LCEN, 1)
            sizer.Add(delpv,  (ir, 3), (1, 1), LCEN, 1)
            self.widlist.append(('line', pos, desc, pvctrl, rdctrl, delpv))

        for i in range(2):
            desc   = wx.TextCtrl(panel, -1, value='', size=(175, -1))
            pvctrl = wx.TextCtrl(panel, value='', size=(175, -1))
            rdctrl = wx.TextCtrl(panel, value='', size=(175, -1))
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), RCEN, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LCEN, 1)
            sizer.Add(rdctrl, (ir, 2), (1, 1), LCEN, 1)
            self.widlist.append(('line', None, desc, pvctrl, rdctrl, None))

        # xafs
        ir += 1
        sizer.Add(add_subtitle(panel, 'Positioner for XAFS Scans'),
                  (ir, 0),  (1, 4),  LCEN, 1)

        energy = self.scandb.get_info('xafs_energy')
        desc   = wx.StaticText(panel, -1, label='Energy Positioner', size=(175, -1))
        pvctrl = wx.Choice(panel, choices=poslist, size=(175, -1))
        pvctrl.SetStringSelection(energy)
        ir +=1
        sizer.Add(desc,   (ir, 0), (1, 1), RCEN, 1)
        sizer.Add(pvctrl, (ir, 1), (1, 2), LCEN, 1)
        self.widlist.append(('xafs', None, desc, pvctrl, None, None))

        # slew scans
        ir += 1
        sizer.Add(add_subtitle(panel, 'Slew Scan Positioners'),
                  (ir, 0),  (1, 4),  LCEN, 1)

        for pos in self.scandb.getall('slewscanpositioners'):
            desc   = wx.TextCtrl(panel, -1, value=pos.name, size=(175, -1))
            pvctrl = wx.TextCtrl(panel, value=pos.drivepv,  size=(175, -1))
            rdctrl = wx.TextCtrl(panel, value=pos.readpv,  size=(175, -1))
            delpv  = YesNo(panel, defaultyes=False)
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), RCEN, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LCEN, 1)
            sizer.Add(rdctrl, (ir, 2), (1, 1), LCEN, 1)
            sizer.Add(delpv,  (ir, 3), (1, 1), LCEN, 1)
            self.widlist.append(('slew', pos, desc, pvctrl, rdctrl, delpv))

        for i in range(1):
            desc   = wx.TextCtrl(panel, -1, value='', size=(175, -1))
            pvctrl = wx.TextCtrl(panel, value='', size=(175, -1))
            rdctrl = wx.TextCtrl(panel, value='', size=(175, -1))
            ir +=1
            sizer.Add(desc,   (ir, 0), (1, 1), RCEN, 1)
            sizer.Add(pvctrl, (ir, 1), (1, 1), LCEN, 1)
            sizer.Add(rdctrl, (ir, 2), (1, 1), LCEN, 1)
            self.widlist.append(('slew', None, desc, pvctrl, rdctrl, None))

        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 3), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), LCEN, 3)
        #
        ir += 1
        sizer.Add(okcancel(panel, self.onOK, self.onClose),
                  (ir, 0), (1, 2), LCEN, 1)

        pack(panel, sizer)
        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()


    def onOK(self, event=None):
        self.scandb.set_info('pos_settle_time',
                             float(self.settle_time.GetValue()))
        for w in self.widlist:
            wtype, obj, name, drivepv, readpv, erase = w
            if wtype == 'xafs':
                name = drivepv.GetStringSelection()
                energy = self.scandb.set_info('xafs_energy', name)
                continue
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
                obj.use = 1
                obj.drivepv = drivepv
                obj.readpv = readpv
            elif obj is None and wtype == 'line':
                self.scandb.add_positioner(name, drivepv, readpv=readpv)
            elif obj is None and wtype == 'slew':
                self.scandb.add_slewpositioner(name, drivepv, readpv=readpv)

        self.scandb.commit()
        for inb, panel in self.parent.scanpanels.values():
            panel.update_positioners()

        self.Destroy()


    def onClose(self, event=None):
        self.Destroy()

