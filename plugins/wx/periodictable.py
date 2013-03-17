import wx

class HyperText(wx.StaticText):
    """HyperText is a simple extension of wx.StaticText that

       1. adds an underscore to the lable to appear to be a hyperlink
       2. performs the supplied action on Left-Up button events
    """
    selcolour = (180, 50, 50)
    regcolour = (50, 50, 180)
    def  __init__(self, parent, label, action=None, style=None, **kws):
        self.action = action
        wx.StaticText.__init__(self, parent, -1, label=label, **kws)
        font  = self.GetFont() # .Bold()
        font.SetUnderlined(True)
        self.SetFont(font)
        self.SetForegroundColour(self.regcolour)
        self.Bind(wx.EVT_LEFT_DOWN, self.onSelect)

    def onSelect(self, event=None):
        "Left-Down Event Handler"
        self.setSelected()
        if self.action is not None:
            self.action(event=event, label=self.GetLabel())
        event.Skip()

    def setSelected(self):
        self.SetForegroundColour(self.selcolour)

    def setNotSelected(self):
        self.SetForegroundColour(self.regcolour)


class PeriodicTablePanel(wx.Panel):
    """periodic table"""

    elems = {'H': (0, 0), 'Li': ( 1, 0), 'Na': (2, 0), 'K': (3, 0),
             'Rb': (4, 0), 'Cs': (5, 0), 'Fr': (6, 0), 'Be': (1, 1),
             'Mg': (2, 1), 'Ca': (3, 1), 'Sr': (4, 1), 'Ba': (5, 1),
             'Ra': (6, 1), 'Sc': (3, 2), 'Y': (4, 2), 'La': (5, 2),
             'Ac': (6, 2), 'Ti': (3, 3), 'Zr': (4, 3), 'Hf': (5, 3),
             'V': (3, 4), 'Nb': (4, 4), 'Ta': (5, 4), 'Cr': (3, 5),
             'Mo': (4, 5), 'W': (5, 5), 'Mn': (3, 6), 'Tc': (4, 6),
             'Re': (5, 6), 'Fe': (3, 7), 'Ru': (4, 7), 'Os': (5, 7),
             'Co': (3, 8), 'Rh': (4, 8), 'Ir': (5, 8), 'Ni': (3, 9),
             'Pd': (4, 9), 'Pt': (5, 9), 'Cu': (3, 10), 'Ag': (4,
             10), 'Au': (5, 10), 'Zn': (3, 11), 'Cd': (4, 11), 'Hg':
             (5, 11), 'B': (1, 12), 'Al': (2, 12), 'Ga': (3, 12),
             'In': (4, 12), 'Tl': (5, 12), 'C': (1, 13), 'Si': (2,
             13), 'Ge': (3, 13), 'Sn': (4, 13), 'Pb': (5, 13), 'N':
             (1, 14), 'P': (2, 14), 'As': (3, 14), 'Sb': (4, 14),
             'Bi': (5, 14), 'O': (1, 15), 'S': (2, 15), 'Se': (3,
             15), 'Te': (4, 15), 'Po': (5, 15), 'F': (1, 16), 'Cl':
             (2, 16), 'Br': (3, 16), 'I': (4, 16), 'At': (5, 16),
             'He': (0, 17), 'Ne': (1, 17), 'Ar': (2, 17), 'Kr': (3,
             17), 'Xe': (4, 17), 'Rn': (5, 17), 'Ce': (7, 3), 'Pr':
             (7, 4), 'Nd': (7, 5), 'Pm': (7, 6), 'Sm': (7, 7), 'Eu':
             (7, 8), 'Gd': (7, 9), 'Tb': (7, 10), 'Dy': (7, 11),
             'Ho': (7, 12), 'Er': (7, 13), 'Tm': (7, 14), 'Yb': (7,
             15), 'Lu': (7, 16), 'Th': (8, 3), 'Pa': (8, 4), 'U': (8,
             5), 'Np': (8, 6), 'Pu': (8, 7), 'Am': (8, 8), 'Cm': (8,
             9), 'Bk': (8, 10), 'Cf': (8, 11), 'Es': (8, 12), 'Fm':
             (8, 13), 'Md': (8, 14), 'No': (8, 15), 'Lr': (8, 16)}

    def __init__(self, parent, action=None, size=(300, 120), **kws):
        wx.Panel.__init__(self, parent, -1, size=size, **kws)
        self.parent = parent
        self.action = action
        self.wids = {}
        self.selected = None
        self.elemfont  = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.titlefont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.BuildPanel()
        self.Bind(wx.EVT_KEY_UP, self.onKey)

    def onKey(self, event=None):
        if self.selected  in self.elems:
            coords  = self.elems[self.selected]
            thiskey = event.GetKeyCode()
            newcoords = coords
            if thiskey == wx.WXK_UP:
                newcoords = (coords[0]-1, coords[1])
            elif thiskey == wx.WXK_DOWN:
                newcoords = (coords[0]+1, coords[1])
            elif thiskey == wx.WXK_LEFT:
                newcoords = (coords[0], coords[1]-1)
            elif thiskey == wx.WXK_RIGHT:
                newcoords = (coords[0], coords[1]+1)
            if newcoords == coords:
                return
            # try to support jumping to/from lanthanide,
            # and wrapping around at alkali/halides
            if newcoords not in self.elems.values():
                if thiskey == wx.WXK_DOWN:
                    newcoords = (coords[0]+2, coords[1])
                elif thiskey == wx.WXK_UP:
                    newcoords = (coords[0]-2, coords[1])
                elif thiskey == wx.WXK_LEFT and newcoords[1] < 0:
                    newcoords = (coords[0]-1, 17)
                elif thiskey == wx.WXK_RIGHT and newcoords[1] > 17:
                    newcoords = (coords[0]+1, 0)

            if newcoords in self.elems.values():
                newlabel = None
                for xlabel, xcoords in self.elems.items():
                    if newcoords == xcoords:
                        newlabel = xlabel
                if newlabel is not None:
                    self.onclick(label=newlabel)
        event.Skip()

    def onclick(self, event=None, label=None):
        if self.selected in self.wids:
            self.wids[self.selected].setNotSelected()
        self.selected = label
        if self.action is not None:
            self.action(elem=label, event=event)
        self.wids[self.selected].setSelected()

    def make_elem(self, label, size=(-1, -1)):
        btn = HyperText(self, label, action=self.onclick, size=size)
        btn.Bind(wx.EVT_KEY_UP, self.onKey)
        self.wids[label] = btn
        btn.SetFont(self.elemfont)
        return btn

    def BuildPanel(self):
        sizer = wx.GridBagSizer(9, 18)
        for name, coords in self.elems.items():
            sizer.Add(self.make_elem(name), coords,
                      (1, 1), wx.ALIGN_LEFT, 0)
        title = wx.StaticText(self, -1,
                              label='Select Element for K,L,M Markers')
        title.SetFont(self.titlefont)
        sizer.Add(title,  (0, 3), (1, 13), wx.ALIGN_CENTER, 0)
        sizer.Add(self.make_elem('Hide K,L,M Markers'),
                  (1, 3), (1, 7), wx.ALIGN_CENTER, 0)
        sizer.SetEmptyCellSize((0, 0))
        sizer.SetHGap(0)
        sizer.SetVGap(0)
        self.SetSizer(sizer)
        self.SetMinSize( self.GetBestSize() )
        sizer.Fit(self)
