import sys
import time

import wx
import wx.lib.scrolledpanel as scrolled

from .gui_utils import (GUIColors, set_font_with_children, YesNo,
                        add_button, pack, SimpleText, check, okcancel,
                        add_subtitle, Font, LCEN, CEN, RCEN)

RCEN |= wx.ALL
LCEN |= wx.ALL
CEN  |= wx.ALL

class ScandefsFrame(wx.Frame) :
    """Edit Scan Definitions"""
    def __init__(self, parent, pos=(-1, -1)):

        self.parent = parent
        self.scandb = parent.scandb

        LCEN  = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        RCEN = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL

        wx.Frame.__init__(self, None, -1,
                          'Epics Scanning: Scan Definitions',
                          style  = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.SetFont(Font(9))
        sizer = wx.GridBagSizer(10, 5)
        panel = scrolled.ScrolledPanel(self)
        self.SetMinSize((550, 500))
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        # title row
        title = SimpleText(panel, 'Scan Definitions',  font=Font(13),
                           colour=self.colors.title, style=LCEN)

        sizer.Add(title,        (0, 0), (1, 3), LCEN, 5)
            
        ir = 1
        sizer.Add(SimpleText(panel, label=' Scan Name', size=(175, -1)),
                  (ir, 0), (1, 1), RCEN, 2)
        sizer.Add(SimpleText(panel, label='Erase?'),
                  (ir, 1), (1, 1), LCEN, 2)
        sizer.Add(SimpleText(panel, label=' Scan Name', size=(175, -1)),
                  (ir, 2), (1, 1), RCEN, 2)
        sizer.Add(SimpleText(panel, label='Erase?'),
                  (ir, 3), (1, 1), LCEN, 2)

        sdefs = {}
        scantypes = ('linear', 'mesh', 'xafs', 'slew')
        for sname in scantypes:
            sdefs[sname] = []
        for this in self.scandb.getall('scandefs'):
            sdefs[this.type].append( this.name )

        self.widlist = []
        for typename in scantypes:
            if len(sdefs[typename]) > 0:
                ir += 1
                sizer.Add(add_subtitle(panel, ' %s Scans' % typename.title()),
                          (ir, 0),  (1, 5),  LCEN, 1)
                ir += 1
                for ix, sname in enumerate(sdefs[typename]):
                    ix = ix % 2
                    desc  = SimpleText(panel,  label=sname, size=(175, -1))
                    erase = YesNo(panel, defaultyes=False)
                    sizer.Add(desc,  (ir, 0 + ix*2), (1, 1), LCEN, 1)
                    sizer.Add(erase, (ir, 1 + ix*2), (1, 1), LCEN, 1)
                    ir = ir + ix
                    self.widlist.append((sname, erase))
                ir = ir - ix
                    

        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 3), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), LCEN, 3)
        #
        ir += 1
        sizer.Add(okcancel(panel, self.onOK, self.onClose),
                  (ir, 0), (1, 2), LCEN, 3)

        pack(panel, sizer)

        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)
        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def onOK(self, event=None):
        for name, erase in self.widlist:
            if erase.GetSelection():
                self.scandb.del_scandef(name)

        self.scandb.commit()
        self.Destroy()

    def onClose(self, event=None):
        self.Destroy()

