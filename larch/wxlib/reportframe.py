import wx
from wx.richtext import RichTextCtrl

from wxutils import pack, FRAMESTYLE, Font
from . import FONTSIZE, MenuItem, FileSave

class ReportFrame(wx.Frame):
    """basic frame for displaying a text report -- should be improved!
    """
    def __init__(self, parent=None, text=None, size=(725, 600),
                 title='Report', default_filename='out.txt', wildcard='*.txt', **kws):
        self.default_filename = default_filename
        self.wildcard = wildcard
        wx.Frame.__init__(self, parent, size=size, style=FRAMESTYLE, **kws)
        self.SetTitle(title)
        self.menubar = wx.MenuBar()
        fmenu = wx.Menu()

        MenuItem(self, fmenu, "Save", "Save Text to File", self.onSave)
        MenuItem(self, fmenu, "Quit",  "Exit", self.onClose)
        self.menubar.Append(fmenu, "&File")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_CLOSE,  self.onClose)
        
        self.report = RichTextCtrl(self,size=size, style=wx.VSCROLL)
        self.report.SetEditable(False)
        self.report.SetFont(wx.Font(FONTSIZE+1,  wx.MODERN, wx.NORMAL, wx.BOLD))
        
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


    def onClose(self, event=None):
        self.Destroy()

    def onSave(self, eventt=None):
        wildcard = f'{self.wildcard}|All files (*.*)|*.*'
        path = FileSave(self, message='Save text to file',
                        wildcard=wildcard,
                        default_file=self.default_filename)
        if path is not None:
            with open(path, 'w') as fh:
                fh.write(self.report.GetValue())
                fh.write('')

