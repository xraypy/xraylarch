import wx

class GUIColors(object):
    """a container for colour attributes
         bg
         nb_active
         nb_area
         nb_text
         nb_activetext
         title
         pvname
    """
    def __init__(self):
        self.bg        = wx.Colour(240,240,230)
        self.nb_active = wx.Colour(254,254,195)
        self.nb_area   = wx.Colour(250,250,245)
        self.nb_text   = wx.Colour(10,10,180)
        self.nb_activetext = wx.Colour(80,10,10)
        self.title     = wx.Colour(80,10,10)
        self.pvname    = wx.Colour(10,10,80)
