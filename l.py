#!/usr/bin/env python

import sys
import wx
import lib as larch
    
from lib.wxlib import larchframe

app = wx.App()
frame = larchframe.LarchFrame(exit_on_close=True)
frame.Show()
app.MainLoop()


