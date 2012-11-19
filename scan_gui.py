import wx
from lib.gui import ScanFrame, ScanApp

app = wx.App()
s = ScanFrame()
s.Show()
app.MainLoop()
    
# s = ScanApp()
# s.MainLoop()
# 
# 
print 's done ', s
