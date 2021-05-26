import wx
from collections import namedtuple
from ..version import check_larchversion
from . import GridPanel, SimpleText, OkCancel, LEFT, HLine

class LarchUpdaterDialog(wx.Dialog):
    """dialog for running larch updates"""
    def __init__(self, parent, caller='this program', **kws):
        title = "Checking for Larch updates..."
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title, size=(400, 200))

        vinfo = check_larchversion()
        cver = ' Your Current Version: {:s}'.format(vinfo.local_version)
        lver = ' Latest Available Version: {:s}'.format(vinfo.remote_version)
        self.update_available = vinfo.update_available

        if self.update_available:
            tmessage = ' Update Available! '
            umessage = ' Click OK to update (you will need to restart %s)' % (caller)
        else:
            tmessage = ' Your version is up to date.'
            umessage = ' '

        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)

        panel.Add((5, 5))
        panel.Add(SimpleText(panel, tmessage), newrow=True)
        panel.Add((5, 5))
        panel.Add(SimpleText(panel, cver), newrow=True)
        panel.Add(SimpleText(panel, lver), newrow=True)
        panel.Add(SimpleText(panel, umessage), newrow=True)
        panel.Add((5, 5), newrow=True)
        panel.Add(HLine(panel, size=(240, 3)), dcol=2, newrow=True)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()

    def GetResponse(self):
        self.Raise()
        out = namedtuple('UpgradeResponse', ('ok', 'run_updates'))
        return out((wx.ID_OK==self.ShowModal()), self.update_available)
