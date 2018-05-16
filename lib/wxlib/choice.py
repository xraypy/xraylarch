import wx

class Choice(wx.Choice):
    """Simple Choice with default and bound action
    c = Choice(panel, choices, default=0, action=None, **kws)
    """
    def __init__(self, parent, choices=None, default=0,
                 action=None, **kws):
        if choices is None:
            choices = []
        wx.Choice.__init__(self, parent, -1,  choices=choices, **kws)
        self.Select(default)
        self.Bind(wx.EVT_CHOICE, action)

    def SetChoices(self, choices):
        index = 0
        try:
            current = self.GetStringSelection()
            if current in choices:
                index = choices.index(current)
        except:
            pass
        self.Clear()
        self.AppendItems(choices)
        self.SetStringSelection(choices[index])


class YesNo(wx.Choice):
    """
    A simple wx.Choice with choices set to ('No', 'Yes')
    c = YesNo(parent, defaultyes=True, choices=('No', 'Yes'))

    has methods SetChoices(self, choices) and Select(choice)
    """
    def __init__(self, parent, defaultyes=True,
                 choices=('No', 'Yes'), size=(60, -1)):
        wx.Choice.__init__(self, parent, -1, size=size)
        self.choices = choices
        self.Clear()
        self.SetItems(self.choices)
        try:
            default = int(defaultyes)
        except:
            default = 0
        self.SetSelection(default)

    def SetChoices(self, choices):
        self.Clear()
        self.SetItems(choices)
        self.choices = choices

    def Select(self, choice):
        if isinstance(choice, int):
            self.SetSelection(0)
        elif choice in self.choices:
            self.SetSelection(self.choices.index(choice))
