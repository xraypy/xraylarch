
import wx
is_wxPhoenix = 'phoenix' in wx.PlatformInfo

from wxutils import (SimpleText, pack, Button,
                     Choice, Check, MenuItem, OkCancel,
                     GridPanel, CEN,
                     RCEN, LCEN, FRAMESTYLE, Font)


class MergeDialog(wx.Dialog):
    """popup dialog for merging groups"""
    msg = """Merge Selected Groups"""
    def __init__(self, parent, groupnames, **kws):

        title = "Merge %i Selected Groups" % (len(groupnames))
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        panel = GridPanel(self, ncols=3, nrows=4, pad=2, itemstyle=LCEN)

        ychoices = ['raw mu(E)', 'normalized mu(E)']

        self.master_group = Choice(panel, choices=groupnames, size=(250, -1))
        self.yarray_name  = Choice(panel, choices=ychoices, size=(250, -1))
        self.group_name   = wx.TextCtrl(panel, -1, 'merge',  size=(250, -1))

        panel.Add(SimpleText(panel, 'Match Energy to : '), newrow=True)
        panel.Add(self.master_group)

        panel.Add(SimpleText(panel, 'Array to merge  : '), newrow=True)
        panel.Add(self.yarray_name)

        panel.Add(SimpleText(panel, 'New group name  : '), newrow=True)
        panel.Add(self.group_name)

        panel.Add(OkCancel(panel), dcol=2, newrow=True)

        panel.pack()

        # sizer = wx.BoxSizer(wx.VERTICAL)
        # sizer.Add(panel, 0, 0, 0)
        # pack(self, sizer)
