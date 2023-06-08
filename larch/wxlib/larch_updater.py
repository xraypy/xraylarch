import wx
import sys
from collections import namedtuple
from pyshortcuts import platform
from ..version import check_larchversion
from . import GridPanel, SimpleText, OkCancel, LEFT, HLine, Button


class LarchUpdaterDialog(wx.Dialog):
    """dialog for running larch updates"""
    def __init__(self, parent, caller='this program', **kws):
        title = "Checking for Larch updates..."
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title, size=(525, 250))

        vinfo = check_larchversion()
        self.update_available = vinfo.update_available

        upgrade_pycmd = f'{sys.executable} -m pip install --upgrade xraylarch'
        panel = GridPanel(self, ncols=3, nrows=4, pad=4, itemstyle=LEFT)
        panel.Add((5, 5))

        def addline(text):
            panel.Add(SimpleText(panel, text), newrow=True)

        def toclipboard(event=None, **kws):
            cb = wx.TheClipboard
            if cb.IsOpened():
                cb.Close()
            cb.Open()
            cb.SetData(wx.TextDataObject(upgrade_pycmd))
            cb.Close()

        addline(' Installed Version: {:s}'.format(vinfo.local_version))
        addline(' Latest Version: {:s}'.format(vinfo.remote_version))
        panel.Add((5, 5))

        if not vinfo.update_available:
            addline(' Your version is up to date!')
        else:
            if platform.startswith('win'):
                addline(f' Close {caller} and Run "Larch Updater" from your Larch Desktop Folder')
            else:
                addline(f' Click OK to update (you will need to restart {caller})')
            panel.Add((5, 5))
            addline(' You can also update from a Terminal with:')
            addline(f' {upgrade_pycmd}')
            panel.Add(Button(panel, 'Copy Upgrade Command To Clipboard',
                             action=toclipboard), newrow=True)
            panel.Add((5, 5), newrow=True)

        panel.Add(HLine(panel, size=(240, 3)), dcol=2, newrow=True)
        panel.Add(OkCancel(panel), dcol=2, newrow=True)
        panel.pack()

    def GetResponse(self):
        self.Raise()
        out = namedtuple('UpgradeResponse', ('ok', 'run_updates'))
        result = out((wx.ID_OK==self.ShowModal()), self.update_available)
        if platform.startswith('win'):
            result = out(False, self.update_available)
        return result
