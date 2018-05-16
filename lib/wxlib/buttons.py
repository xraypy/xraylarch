import wx

is_wxPhoenix = 'phoenix' in wx.PlatformInfo

def Button(parent, label, action=None, **kws):
    """Simple button with bound action
    b = Button(parent, label, action=None, **kws)

    """
    thisb = wx.Button(parent, label=label, **kws)
    if hasattr(action, '__call__'):
        parent.Bind(wx.EVT_BUTTON, action, thisb)
    return thisb

def BitmapButton(parent, bmp, action=None, tooltip=None, size=(20, 20), **kws):
    b = wx.BitmapButton(parent, id=-1, bitmap=bmp, size=size, **kws)
    if action is not None:
        parent.Bind(wx.EVT_BUTTON, action, b)
    if tooltip is not None:
        if is_wxPhoenix:
            b.SetToolTip(tooltip)
        else:
            b.SetToolTipString(tooltip)
    return b

def ToggleButton(parent, label, action=None, tooltip=None,
                 size=(25, 25), **kws):
    b = wx.ToggleButton(parent, -1, label, size=size, **kws)
    if action is not None:
        b.Bind(wx.EVT_TOGGLEBUTTON, action)
    if tooltip is not None:
        if is_wxPhoenix:
            b.SetToolTip(tooltip)
        else:
            b.SetToolTipString(tooltip)
    return b
