import wx
from functools import partial

class SimpleText(wx.StaticText):
    "simple static text wrapper"
    def __init__(self, parent, label, minsize=None, font=None, colour=None,
                 bgcolour=None, style=wx.ALIGN_CENTRE, **kws):

        wx.StaticText.__init__(self, parent, -1, label=label, style=style,
                               **kws)
        if minsize is not None:
            self.SetMinSize(minsize)
        if font is not None:
            self.SetFont(font)
        if colour is not None:
            self.SetForegroundColour(colour)
        if bgcolour is not None:
            self.SetBackgroundColour(bgcolour)


class TextCtrl(wx.TextCtrl):
    """simple TextCtrl
    t = TextCtrl(parent, value, font=None
                 colour=None, bgcolour=None,
                 action=None, action_kws=None,
                 act_on_losefocus=True, **kws)
    has a method SetAction(action, action_kws)
    for setting action on RETURN (and optionally LoseFocus)
    """
    def __init__(self, parent, value, font=None,
                 colour=None, bgcolour=None,
                 action=None, action_kws=None,
                 act_on_losefocus=True, **kws):

        self.act_on_losefocus = act_on_losefocus

        this_sty =  wx.TE_PROCESS_ENTER|wx.ALIGN_CENTRE
        if 'style' in kws:
            this_sty = this_sty | kws['style']
        kws['style'] = this_sty
        wx.TextCtrl.__init__(self, parent, -1, **kws)
        self.SetValue(value)
        if font is not None:
            self.SetFont(font)
        if colour is not None:
            self.SetForegroundColour(colour)
        if bgcolour is not None:
            self.SetBackgroundColour(bgcolour)

        self.SetAction(action, **action_kws)

        self.Bind(wx.EVT_CHAR, self.onChar)
        self.Bind(wx.EVT_KILL_FOCUS, self.onFocus)

    def SetAction(self, action, **kws):
        "set action callback"
        self.__act = None
        if hasattr(action,'__call__'):
            self.__act = partial(action, **kws)

    def onFocus(self, evt=None):
        "focus events -- may act on KillFocus"
        if self.act_on_losefocus and self.__act is not None:
            self.__act(self.GetValue())
        evt.Skip()

    def onChar(self, evt=None):
        "character events -- may act on RETURN"
        if evt.GetKeyCode() == wx.WXK_RETURN and self.__act is not None:
            self.__act(self.GetValue())
        evt.Skip()


class LabeledTextCtrl(TextCtrl):
    """
    simple extension of TextCtrl with a .label attribute holding a SimpleText
    Typical usage:
      entry = LabeledTextCtrl(self, value='22', labeltext='X:')
      row   = wx.BoxSizer(wx.HORIZONTAL)
      row.Add(entry.label, 1,wx.ALIGN_LEFT|wx.EXPAND)
      row.Add(entry,    1,wx.ALIGN_LEFT|wx.EXPAND)
    """
    def __init__(self, parent, value, font=None, action=None,
                 action_kws=None, act_on_losefocus=True, size=(-1, -1),
                 bgcolour=None, colour=None, style=None,
                 labeltext=None, labelsize=(-1, -1),
                 labelcolour=None, labelbgcolour=None, **kws):

        if labeltext is not None:
            self.label = SimpleText(parent, labeltext, size=labelsize,
                                    font=font, style=style,
                                    colour=labelcolour,
                                    bgcolour=labelbgcolour)

        try:
            value = str(value)
        except:
            value = ' '

        TextCtrl.__init__(self, parent, value, font=font,
                          colour=colour, bgcolour=bgcolour,
                          style=stye, size=size,
                          action=action, action_kws=action_kws,
                          act_on_losefocus=act_on_losefocus, **kws)


class HyperText(wx.StaticText):
    """HyperText is a simple extension of wx.StaticText that

       1. adds an underscore to the label to appear to be a hyperlink
       2. performs the supplied action on Left-Up button events
    """

    def __init__(self, parent, label, action=None, colour=(50, 50, 180),
                  bgcolour=None, underline=True, **kws):
        wx.StaticText.__init__(self, parent, -1, label=label, **kws)
        self.SetForegroundColour(colour)
        if bgcolour is not None:
            self.SetBackgroundColour(bgcolour)
        if underline:
            font  = self.GetFont()
            try:
                font.SetUnderlined(True)
            except:
                pass
            self.SetFont(font)
        self.action = action
        self.Bind(wx.EVT_LEFT_UP, self.OnSelect)

    def OnSelect(self, event=None):
        "Left-Up Event Handler"
        if hasattr(self.action,'__call__'):
            self.action(label=self.GetLabel(), event=event)
        event.Skip()
