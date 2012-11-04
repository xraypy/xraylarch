import wx
import sys
import time

from epics.wx.utils import  (empty_bitmap, add_button, add_menu,
                 Closure, NumericCombo, pack, popup, SimpleText,
                             FileSave, FileOpen, SelectWorkdir)

from gui_utils import GUIColors, set_font_with_children

class PositionerFrame(wx.Frame) :
    """Frame to Setup Scan Positioners"""
    def __init__(self, parent=None, pos=(-1, -1), config=None):

        self.parent = parent
        self.config = config

        style    = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL
        labstyle  = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        rlabstyle = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        tstyle    = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL

        wx.Frame.__init__(self, None, -1,
                          'Epics Scanning: Set Up Positioners')

        font = parent.GetFont()
        titlefont  = self.GetFont()
        titlefont.PointSize += 2
        titlefont.SetWeight(wx.BOLD)

        sizer = wx.GridBagSizer(10, 5)
        panel = wx.Panel(self)
        # title row
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        title = SimpleText(panel, 'Positioners',  font=titlefont,
                           minsize=(130, -1),
                           colour=self.colors.title, style=tstyle)

        sizer.Add(title,        (0, 0), (1, 3), labstyle|wx.ALL, 5)
        sizer.Add(wx.StaticLine(panel, size=(2, 50), style=wx.LI_HORIZONTAL),
                  (1, 0), (1, 3), wx.ALIGN_CENTER|wx.GROW|wx.ALL, 3)

        print 'current positioners'

        pack(panel, sizer)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def get_page_map(self):
        out = {}
        for i in range(self.parent.nb.GetPageCount()):
            out[self.parent.nb.GetPageText(i)] = i
        return out

    def OnOK(self, event=None):
        print 'OK ...'

    def OnCancel(self, event=None):
        self.Destroy()

