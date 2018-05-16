import wx
from .text import SimpleText

class GridPanel(wx.Panel):
    """A simple panel with a GridBagSizer"""

    def __init__(self, parent, nrows=10, ncols=10, pad=2, gap=5,
                 itemstyle=wx.ALIGN_CENTER, **kws):

        wx.Panel.__init__(self, parent, **kws)
        self.sizer = wx.GridBagSizer(nrows, ncols)
        self.sizer.SetVGap(gap)
        self.sizer.SetHGap(gap)

        self.irow = 0
        self.icol = 0
        self.itemstyle = itemstyle
        self.pad=pad

    def Add(self, item, irow=None, icol=None, drow=1, dcol=1, style=None,
            newrow=False, pad=None, **kws):
        """add item with default values for col, row, and size"""
        if newrow:
            self.NewRow()
        if style is None:
            style = self.itemstyle
        if irow is None:
            irow = self.irow
        if pad is None:
            pad = self.pad
        if icol is None:
            icol = self.icol
        self.sizer.Add(item, (irow, icol), (drow, dcol), style, pad, **kws)
        self.icol = self.icol + dcol

    def AddMany(self, items, newrow=False, **kws):
        """add items"""
        if newrow: self.NewRow()
        for item in items:
            self.Add(item, **kws)

    def AddManyText(self, items, newrow=False, **kws):
        """add items"""
        if newrow: self.NewRow()
        for item in items:
            self.AddText(item, **kws)

    def NewRow(self):
        "advance row, set col # = 0"
        self.irow += 1
        self.icol = 0

    def AddText(self, label, newrow=False, dcol=1, style=None, **kws):
        """add a Simple StaticText item"""
        if style is None:
            style = LCEN
        self.Add(SimpleText(self, label, style=style, **kws),
                 dcol=dcol, style=style, newrow=newrow)

    def pack(self):
        tsize = self.GetSize()
        msize = self.GetMinSize()

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)
        nsize = (10*int(1.1*(max(msize[0], tsize[0])/10)),
                 10*int(1.1*(max(msize[1], tsize[1])/10.)))
        self.SetSize(nsize)
