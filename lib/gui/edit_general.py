#
# general parameter frame
import sys
import time

import wx
import wx.lib.scrolledpanel as scrolled

from ..ordereddict import OrderedDict
from .gui_utils import GUIColors, set_font_with_children, YesNo
from .gui_utils import add_button, pack, SimpleText

LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL

class SettingsFrame(wx.Frame) :
    """Frame for Setup General Settings:

    DB Connection, Settling Times, Extra PVs
    """
    def __init__(self, parent, pos=(-1, -1)):

        self.parent = parent
        self.pvlist = parent.pvlist
        self.scandb = parent.scandb
        self.scanpanels = parent.scanpanels

        style     = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL
        labstyle  = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        rlabstyle = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
        tstyle    = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL

        self.Font10=wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        titlefont = wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")

        wx.Frame.__init__(self, None, -1,
                          'Epics Scanning Setup:')

        self.SetFont(self.Font10)
        sizer = wx.GridBagSizer(10, 5)
        panel = scrolled.ScrolledPanel(self)
        self.SetMinSize((550, 500))
        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        # title row
        title = SimpleText(panel, 'General Setup',  font=titlefont,
                           colour=self.colors.title, style=tstyle)
        
        sizer.Add(title,        (0, 0), (1, 3), LEFT, 5)
        ir = 0
        self.wids = {}
        for sect, vars in (('User Setup', (('user_name', False),
                                           ('user_folder', False),
                                           ('experiment_id', False))),
                           ('Loading Scan Definitions',
                            (('scandefs_verify_overwrite', True), 
                             ('scandefs_load_showauto', True),
                             ('scandefs_load_showalltypes', True)))):
            
            ir += 1
            sizer.Add(self.add_subtitle(panel, '%s:' % sect), (ir, 0),  (1, 4),  LEFT, 1)
            for vname, as_bool in vars:
                val, label = self.scandb.get_info(vname, as_bool=as_bool, with_notes=True)

                desc = wx.StaticText(panel, -1, label="%s: " % label, size=(300, -1))
                if as_bool:
                    ctrl = wx.CheckBox(panel)
                    ctrl.SetValue(val)
                else:
                    ctrl = wx.TextCtrl(panel, value=val,  size=(200, -1))
                self.wids[vname] = ctrl
                ir += 1
                sizer.Add(desc,  (ir, 0), (1, 1), wx.ALIGN_LEFT|wx.EXPAND, 3)
                sizer.Add(ctrl,  (ir, 1), (1, 1), wx.ALIGN_LEFT|wx.EXPAND, 3)


        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 3), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), wx.ALIGN_LEFT|wx.EXPAND, 3)
        ir += 1
        sizer.Add(self.make_buttons(panel), (ir, 0), (1, 3), wx.ALIGN_CENTER|wx.GROW, 3)
        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 3), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), wx.ALIGN_LEFT|wx.GROW|wx.ALL, 3)

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
        s.Add(wx.StaticLine(p, size=(120, 3), style=wx.LI_HORIZONTAL), 0, LEFT, 5)
        s.Add(SimpleText(p, text,  colour='#333377'),  0, LEFT, 5)
        s.Add(wx.StaticLine(p, size=(200, 3), style=wx.LI_HORIZONTAL), 1, LEFT, 5)
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

    def onApply(self, event=None):
        for setting, wid in self.wids.items():
            if isinstance(wid, wx.CheckBox):
                val = {True:1, False:0}[wid.IsChecked()]
            else:
                val = self.wids[setting].GetValue().strip()
            self.scandb.set_info(setting, val)
        self.Destroy()

    def onClose(self, event=None):
        self.Destroy()

