import wx

COLORS = {'text': wx.Colour(0, 0, 0),
          'bg': wx.Colour(240,240,230),
          'nb_active': wx.Colour(254,254,195),
          'nb_area': wx.Colour(250,250,245),
          'nb_text': wx.Colour(10,10,180),
          'nb_activetext': wx.Colour(80,10,10),
          'title': wx.Colour(80,10,10),
          'pvname': wx.Colour(10,10,80),
          'list_bg': wx.Colour(255, 255, 250),
          'list_fg': wx.Colour(5, 5, 25)}

class GUIColors(object):
    def __init__(self):
        for key, rgb in COLORS.items():
            setattr(self, key,rgb)

def set_color(widget, color, bg=None):
    if color not in COLORS:
        color = 'text'
    widget.SetForegroundColour(COLORS[color])
    if bg is not None:
        if bg not in COLORS:
            color = 'bg'
        method = widget.SetBackgroundColour(COLORS[bg])
