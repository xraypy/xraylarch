#!/usr/bin/env python
"""
floatspin controls
"""
import wx
from wx.lib.agw import floatspin as fspin

from wxutils import get_icon, is_wxPhoenix

def FloatSpin(parent, value=0, action=None, tooltip=None,
                 size=(100, -1), digits=1, increment=1, **kws):
    """FloatSpin with action and tooltip"""
    if value is None:
        value = 0
    fs = fspin.FloatSpin(parent, -1, size=size, value=value,
                         digits=digits, increment=increment, **kws)
    if action is not None:
        fs.Bind(fspin.EVT_FLOATSPIN, action)
    if tooltip is not None:
        if is_wxPhoenix:
            fs.SetToolTip(tooltip)
        else:
            fs.SetToolTipString(tooltip)
    return fs

def FloatSpinWithPin(parent, value=0, pin_action=None, **kws):
    """create a FloatSpin with Pin button with action"""
    tooltip = 'use last point selected from plot'
    fspin = FloatSpin(parent, value=value, **kws)
    bmbtn = wx.BitmapButton(parent, id=-1, bitmap=get_icon('pin'),
                            size=(25, 25))
    if pin_action is not None:
        parent.Bind(wx.EVT_BUTTON, pin_action, bmbtn)
    if is_wxPhoenix:
        bmbtn.SetToolTip(tooltip)
    else:
        bmbtn.SetToolTipString(tooltip)
    return fspin, bmbtn
