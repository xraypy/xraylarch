import wx

from wxutils import (SimpleText, FloatCtrl, pack, Button, HLine,
                     Choice,  Check, MenuItem, GUIColors,
                     CEN, RCEN, LCEN, FRAMESTYLE, Font)

from wx.richtext import RichTextCtrl

is_wxPhoenix = 'phoenix' in wx.PlatformInfo

class ReportFrame(wx.Frame):
    """basic frame for displaying a text report -- should be improved!
    """
    def __init__(self, parent=None, text=None, size=(550, 600), **kws):
        wx.Frame.__init__(self, parent, size=size, style=FRAMESTYLE)
        self.report = RichTextCtrl(self,size=(500, 500),
                                   style=wx.VSCROLL)

        self.report.SetEditable(False)
        self.report.SetFont(Font(11))
        self.report.SetMinSize((500, 500))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.report, 1, wx.ALL|wx.GROW, 2)
        pack(self, sizer)
        if text is not None:
            self.set_text(text)
        self.Show()
        self.Raise()

    def set_text(self, text):
        self.report.SetEditable(True)
        self.report.SetValue(text)
        self.report.SetEditable(False)
