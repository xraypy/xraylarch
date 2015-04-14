import wx, sys
from threading import Thread
import time
import subprocess
from cStringIO import StringIO

class mywxframe(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self,None)
        pnl = wx.Panel(self)
        szr = wx.BoxSizer(wx.VERTICAL)
        pnl.SetSizer(szr)
        szr2 = self.sizer2(pnl)
        szr.Add(szr2, 1, wx.ALL|wx.EXPAND, 10)
        self.log = wx.TextCtrl(pnl, -1, style= wx.TE_MULTILINE, size = (300, -1))
        self.log.SetInsertionPointEnd()

        self.ftmp = StringIO()

        self.logtimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onLogTimer, self.logtimer)

        szr.Add(self.log, 0, wx.ALL, 10)
        btn3 = wx.Button(pnl, -1, "Stop")
        btn3.Bind(wx.EVT_BUTTON, self.OnStop)
        szr.Add(btn3, 0, wx.ALL, 10)
        self.CreateStatusBar()

        
        szr.Fit(self)
        self.Show()

    def sizer2(self, panel):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.tc2 = wx.TextCtrl(panel, -1, 'Set Range', size = (100, -1))
        btn2 = wx.Button(panel, -1, "OK",)
        self.Bind(wx.EVT_BUTTON, self.OnStart, btn2)
        sizer.Add(self.tc2, 0, wx.ALL, 10)
        sizer.Add(btn2, 0, wx.ALL, 10)
        return sizer

    def onLogTimer(self, event=None):
        print 'Tick ',event
        print 'New Data: ',  self.ftmp.read()
        
    def OnStart(self, event):
        self.p=subprocess.Popen(["C:\Python27\python.exe", "slow_process.py"], stdout=self.ftmp)
        self.logtimer.Start(500)
        
    def OnStop(self, event):
        self.p.terminate()
        self.logtimer.Stop()

    def write(self, text):
        pos0 = self.log.GetLastPosition()
        self.log.WriteText(text)
        self.log.SetInsertionPoint(self.log.GetLastPosition())
        self.log.Refresh()


app = wx.App()
frm = mywxframe()
app.MainLoop()
