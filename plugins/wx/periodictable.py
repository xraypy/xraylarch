import wx

class HyperText(wx.StaticText):
    """HyperText-like extension of wx.StaticText that
        performs the supplied action on Left-Down button events
    """
    selcolour    = (180,  50,  50)
    regcolour    = ( 50,  50, 180)
    selbgcolour  = (250, 250, 230)
    regbgcolour  = (240, 240, 245)
    def  __init__(self, parent, label, onclick=None,style=None, **kws):
        self.onclick = onclick
        wx.StaticText.__init__(self, parent, -1, label=label, **kws)
        self.regbgcolour = parent.GetBackgroundColour()
        self.setNotSelected()
        self.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)

    def onLeftDown(self, event=None):
        "Left-Down Event Handler"
        self.setSelected()
        if self.onclick is not None:
            self.onclick(event=event, label=self.GetLabel())
        event.Skip()

    def setSelected(self):
        self.SetForegroundColour(self.selcolour)
        self.SetBackgroundColour(self.selbgcolour)

    def setNotSelected(self):
        self.SetForegroundColour(self.regcolour)
        self.SetBackgroundColour(self.regbgcolour)

class PeriodicTablePanel(wx.Panel):
    """periodic table of the elements"""
    elems = {'H':  ( 0,  0), 'He': ( 0, 17), 'Li': ( 1,  0), 'Be': ( 1,  1),
             'B':  ( 1, 12), 'C':  ( 1, 13), 'N':  ( 1, 14), 'O':  ( 1, 15),
             'F':  ( 1, 16), 'Ne': ( 1, 17), 'Na': ( 2,  0), 'Mg': ( 2,  1),
             'Al': ( 2, 12), 'Si': ( 2, 13), 'P':  ( 2, 14), 'S':  ( 2, 15),
             'Cl': ( 2, 16), 'Ar': ( 2, 17), 'K':  ( 3,  0), 'Ca': ( 3,  1),
             'Sc': ( 3,  2), 'Ti': ( 3,  3), 'V':  ( 3,  4), 'Cr': ( 3,  5),
             'Mn': ( 3,  6), 'Fe': ( 3,  7), 'Co': ( 3,  8), 'Ni': ( 3,  9),
             'Cu': ( 3, 10), 'Zn': ( 3, 11), 'Ga': ( 3, 12), 'Ge': ( 3, 13),
             'As': ( 3, 14), 'Se': ( 3, 15), 'Br': ( 3, 16), 'Kr': ( 3, 17),
             'Rb': ( 4,  0), 'Sr': ( 4,  1), 'Y':  ( 4,  2), 'Zr': ( 4,  3),
             'Nb': ( 4,  4), 'Mo': ( 4,  5), 'Tc': ( 4,  6), 'Ru': ( 4,  7),
             'Rh': ( 4,  8), 'Pd': ( 4,  9), 'Ag': ( 4, 10), 'Cd': ( 4, 11),
             'In': ( 4, 12), 'Sn': ( 4, 13), 'Sb': ( 4, 14), 'Te': ( 4, 15),
             'I':  ( 4, 16), 'Xe': ( 4, 17), 'Cs': ( 5,  0), 'Ba': ( 5,  1),
             'La': ( 5,  2), 'Ce': ( 7,  3), 'Pr': ( 7,  4), 'Nd': ( 7,  5),
             'Pm': ( 7,  6), 'Sm': ( 7,  7), 'Eu': ( 7,  8), 'Gd': ( 7,  9),
             'Tb': ( 7, 10), 'Dy': ( 7, 11), 'Ho': ( 7, 12), 'Er': ( 7, 13),
             'Tm': ( 7, 14), 'Yb': ( 7, 15), 'Lu': ( 7, 16), 'Hf': ( 5,  3),
             'Ta': ( 5,  4), 'W':  ( 5,  5), 'Re': ( 5,  6), 'Os': ( 5,  7),
             'Ir': ( 5,  8), 'Pt': ( 5,  9), 'Au': ( 5, 10), 'Hg': ( 5, 11),
             'Tl': ( 5, 12), 'Pb': ( 5, 13), 'Bi': ( 5, 14), 'Po': ( 5, 15),
             'At': ( 5, 16), 'Rn': ( 5, 17), 'Fr': ( 6,  0), 'Ra': ( 6,  1),
             'Ac': ( 6,  2), 'Th': ( 8,  3), 'Pa': ( 8,  4), 'U':  ( 8,  5),
             'Np': ( 8,  6), 'Pu': ( 8,  7), 'Am': ( 8,  8), 'Cm': ( 8,  9),
             'Bk': ( 8, 10), 'Cf': ( 8, 11), 'Es': ( 8, 12), 'Fm': ( 8, 13),
             'Md': ( 8, 14), 'No': ( 8, 15), 'Lr': ( 8, 16)}

    syms = ['H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg',
            'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V',
            'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se',
            'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh',
            'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba',
            'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho',
            'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt',
            'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac',
            'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm',
            'Md', 'No', 'Lr']

    def __init__(self, parent, title='Select Element',
                 action=None, size=(300, 120), **kws):
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
        """support browsing through elements with arrow keys"""
        if self.selected  in self.elems:
            coords = self.elems[self.selected]
            thiskey = event.GetKeyCode()
            newcoords = None
            if thiskey == wx.WXK_UP:
                newcoords = (coords[0]-1, coords[1])
            elif thiskey == wx.WXK_DOWN:
                newcoords = (coords[0]+1, coords[1])
            elif thiskey in (wx.WXK_LEFT, wx.WXK_RIGHT):
                newcoords = None
            # try to support jumping to/from lanthanide,
            # and wrapping around elements
            if newcoords not in self.elems.values():
                if thiskey == wx.WXK_DOWN:
                    newcoords = (coords[0]+2, coords[1])
                elif thiskey == wx.WXK_UP:
                    newcoords = (coords[0]-2, coords[1])
                elif thiskey in (wx.WXK_LEFT, wx.WXK_RIGHT):
                    try:
                        znum = self.syms.index(self.selected)
                    except:
                        return
                    if thiskey == wx.WXK_LEFT and znum > 0:
                        newcoords = self.elems[self.syms[znum-1]]
                    elif thiskey == wx.WXK_RIGHT and znum < len(self.syms)-1:
                        newcoords = self.elems[self.syms[znum+1]]

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
        txt = HyperText(self, label, onclick=self.onclick, size=size)
        self.wids[label] = txt
        txt.SetFont(self.elemfont)
        return txt

    def BuildPanel(self):
        sizer = wx.GridBagSizer(9, 18)
        for name, coords in self.elems.items():
            sizer.Add(self.make_elem(name), coords,
                      (1, 1), wx.ALIGN_LEFT, 0)
        title = wx.StaticText(self, -1,
                              label='Select Element')

        title.SetFont(self.titlefont)
        sizer.Add(title, (0, 3), (1, 10), wx.ALIGN_CENTER, 0)
        sizer.SetEmptyCellSize((0, 0))
        sizer.SetHGap(0)
        sizer.SetVGap(0)
        self.SetSizer(sizer)
        self.SetMinSize( self.GetBestSize() )
        sizer.Fit(self)
