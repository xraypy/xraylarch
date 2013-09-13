#
# general parameter frame
import sys
import time

import wx
import wx.lib.scrolledpanel as scrolled

from .gui_utils import (GUIColors, add_button, pack, SimpleText, check,
                        okcancel, add_subtitle, LCEN, Font)

class SettingsFrame(wx.Frame) :
    """Frame for Setup General Settings:
    DB Connection, Settling Times, Extra PVs
    """
    def __init__(self, parent, pos=(-1, -1)):
        self.parent = parent
        self.pvlist = parent.pvlist
        self.scandb = parent.scandb

        wx.Frame.__init__(self, None, -1,
                          'Epics Scanning Setup: General Settings',
                          style=wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.SetFont(Font(9))
        sizer = wx.GridBagSizer(10, 5)
        panel = scrolled.ScrolledPanel(self)
        self.SetMinSize((550, 500))

        self.colors = GUIColors()
        panel.SetBackgroundColour(self.colors.bg)

        # title row
        title = SimpleText(panel, ' General Settings',  font=Font(13),
                           colour=self.colors.title, style=LCEN)
        sizer.Add(title,    (0, 0), (1, 3), LCEN|wx.ALL, 2)
        ir = 0
        self.wids = {}
        for sect, vars in (('User Setup',
                            (('user_name', False),
                             ('user_folder', False),
                             ('experiment_id', False),
                             ('scangui_verify_quit', True))
                            ),
                           ('Scan Definitions',
                            (('scandefs_verify_overwrite', True), 
                             ('scandefs_load_showalltypes', True),
                             ('scandefs_load_showauto', True))
                            )
                           ):
            
            ir += 1
            sizer.Add(add_subtitle(panel, '%s:' % sect),  (ir, 0),  (1, 4), LCEN, 1)
            for vname, as_bool in vars:
                val, label = self.scandb.get_info(vname, as_bool=as_bool, with_notes=True)

                desc = wx.StaticText(panel, -1, label="  %s: " % label, size=(300, -1))
                if as_bool:
                    ctrl = check(panel, default=val)
                else:
                    ctrl = wx.TextCtrl(panel, value=val,  size=(250, -1))
                self.wids[vname] = ctrl
                ir += 1
                sizer.Add(desc,  (ir, 0), (1, 1), LCEN|wx.ALL, 1)
                sizer.Add(ctrl,  (ir, 1), (1, 1), LCEN|wx.ALL, 1)


        ir += 1
        sizer.Add(wx.StaticLine(panel, size=(350, 3), style=wx.LI_HORIZONTAL),
                  (ir, 0), (1, 4), LCEN|wx.ALL, 1)
        ir += 1
        sizer.Add(okcancel(panel, self.onOK, self.onClose),
                  (ir, 0), (1, 3), LCEN|wx.ALL, 1)

        pack(panel, sizer)

        panel.SetupScrolling()

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(panel, 1, wx.GROW|wx.ALL, 1)

        pack(self, mainsizer)
        self.Show()
        self.Raise()

    def onOK(self, event=None):
        for setting, wid in self.wids.items():
            if isinstance(wid, wx.CheckBox):
                val = {True:1, False:0}[wid.IsChecked()]
            else:
                val = self.wids[setting].GetValue().strip()
            self.scandb.set_info(setting, val)
        self.Destroy()

    def onClose(self, event=None):
        self.Destroy()

