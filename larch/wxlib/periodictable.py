import sys
import wx
import wx.lib.mixins.inspection

from wxutils import SetTip

FRAME_BG = (253, 253, 250) ## light grey
TITLE_BG = (253, 253, 250) ## light grey
FGCOL    = ( 20,  20, 120) ## blue
BGCOL    = (253, 253, 250) ## light grey
BGSEL    = (250, 250, 200) ## yellow
FGSEL    = (200,   0,   0) ## red

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


    names = ['hydrogen', 'helium', 'lithium', 'beryllium', 'boron',
             'carbon', 'nitrogen', 'oxygen', 'fluorine', 'neon', 'sodium',
             'magnesium', 'aluminum', 'silicon', 'phosphorus', 'sulfur',
             'chlorine', 'argon', 'potassium', 'calcium', 'scandium',
             'titanium', 'vanadium', 'chromium', 'manganese', 'iron',
             'cobalt', 'nickel', 'copper', 'zinc', 'gallium', 'germanium',
             'arsenic', 'selenium', 'bromine', 'krypton', 'rubidium',
             'strontium', 'yttrium', 'zirconium', 'niobium', 'molybdenum',
             'technetium', 'ruthenium', 'rhodium', 'palladium', 'silver',
             'cadmium', 'indium', 'tin', 'antimony', 'tellurium', 'iodine',
             'xenon', 'cesium', 'barium', 'lanthanum', 'cerium',
             'praseodymium', 'neodymium', 'promethium', 'samarium',
             'europium', 'gadolinium', 'terbium', 'dysprosium', 'holmium',
             'erbium', 'thulium', 'ytterbium', 'lutetium', 'hafnium',
             'tantalum', 'tungsten', 'rhenium', 'osmium', 'iridium',
             'platinum', 'gold', 'mercury', 'thallium', 'lead', 'bismuth',
             'polonium', 'astatine', 'radon', 'francium', 'radium',
             'actinium', 'thorium', 'protactinium', 'uranium', 'neptunium',
             'plutonium', 'americium', 'curium', 'berkelium', 'californium',
             'einsteinium', 'fermium', 'mendelevium', 'nobelium',
             'lawrencium']


    def __init__(self, parent, title='Select Element', multi_select=False,
                 onselect=None, tooltip_msg=None, size=(-1, -1), fontsize=10,
                 fgcol=None, bgcol=None, fgsel=None, bgsel=None, **kws):
        wx.Panel.__init__(self, parent, -1, size=size, name='PeriodicTable', **kws)
        self.parent = parent
        self.onselect = onselect
        self.tooltip_msg = tooltip_msg
        self.wids = {}
        self.ctrls = {}
        self.SetBackgroundColour(FRAME_BG)
        self.selected = []
        if fgcol is None: fgcol = FGCOL
        if bgcol is None: bgcol = BGCOL
        if fgsel is None: fgsel = FGSEL
        if bgsel is None: bgsel = BGSEL
        self.fgcol = fgcol
        self.bgcol = bgcol
        self.fgsel = fgsel
        self.bgsel = bgsel

        self.current = None
        self.multi_select = multi_select
        if sys.platform.lower().startswith('win'):
            fonstize = fontsize - 1
        subfontsize = fontsize
        if sys.platform.lower().startswith('lin'):
            subfontsize -= 1
        self.titlefont = wx.Font(fontsize, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        self.elemfont = wx.Font(fontsize,  wx.SWISS, wx.NORMAL, wx.BOLD)
        self.subtitlefont = wx.Font(subfontsize, wx.DEFAULT, wx.NORMAL, wx.BOLD)

        self.BuildPanel()

    def onKey(self, event=None, name=None):
        """support browsing through elements with arrow keys"""
        if self.current is None:
            return
        selname = self.current.GetLabel()
        if selname  in self.elems:
            coords = self.elems[selname]
            if name is None and event is not None:
                thiskey = event.GetKeyCode()
            if name == 'left':
                thiskey = wx.WXK_LEFT
            elif name == 'right':
                thiskey = wx.WXK_RIGHT
            elif name == 'up':
                thiskey = wx.WXK_UP
            elif name == 'down':
                thiskey = wx.WXK_DOWN
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
                        znum = self.syms.index(selname)
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
        # event.Skip()

    def on_clear_all(self, event=None):
        for wid in list(self.ctrls.values()) + list(self.wids.values()):
            wid.SetBackgroundColour(self.bgcol)
            wid.SetForegroundColour(self.fgcol)
        self.selected = []
        self.current = None

    def onclick(self, event=None, label=None):
        if event is None and label is None:
            return
        textwid = None
        if label is None and event.Id in self.wids:
            textwid = self.wids[event.Id]
            label = textwid.GetLabel()
        if label is None:
            return
        if textwid is None and label is not None:
            textwid = self.ctrls[label]

        if self.multi_select:
            if label in self.selected: # already selected
                textwid.SetBackgroundColour(self.bgcol)
                textwid.SetForegroundColour(self.fgcol)
                self.selected.remove(label)
            else:
                textwid.SetBackgroundColour(self.bgsel)
                textwid.SetForegroundColour(self.fgsel)
                self.selected.append(label)

        else:
            textwid.SetBackgroundColour(self.bgsel)
            textwid.SetForegroundColour(self.fgsel)
            if self.current is not None and self.current != textwid:
                self.current.SetBackgroundColour(self.bgcol)
                self.current.SetForegroundColour(self.fgcol)
            self.current = textwid
            self.selected = [textwid]

        znum = self.syms.index(label)
        name = self.names[znum]

        self.tsym.SetLabel(label)
        self.title.SetLabel(name)
        self.tznum.SetLabel("{:d}".format(znum+1))
        if self.onselect is not None:
            self.onselect(elem=label, event=event)
        self.Refresh()

    def BuildPanel(self):
        sizer = wx.GridBagSizer()
        sizer.SetHGap(0)
        sizer.SetVGap(1)

        for name, coords in self.elems.items():
            tw = wx.StaticText(self, -1, label=name)
            tw.SetFont(self.elemfont)
            tw.SetForegroundColour(self.fgcol)
            tw.SetBackgroundColour(self.bgcol)
            tw.SetMinSize((20, 18))
            tw.Bind(wx.EVT_LEFT_DOWN, self.onclick)
            if self.tooltip_msg is not None:
                SetTip(tw, self.tooltip_msg)
            self.wids[tw.Id] = tw
            self.ctrls[name] = tw
            sizer.Add(tw, coords, (1, 1), wx.ALIGN_LEFT, 0)
        self.title = wx.StaticText(self, -1, label=' Select Element ')
        self.tsym  = wx.StaticText(self, -1, label='__')
        self.tznum = wx.StaticText(self, -1, label='__')

        for a in (self.title, self.tsym, self.tznum):
            a.SetFont(self.titlefont)
            a.SetBackgroundColour(TITLE_BG)

        sizer.Add(self.title, (0, 4), (1, 8), wx.ALIGN_CENTER, 5)
        sizer.Add(self.tsym,  (0, 2), (1, 2), wx.ALIGN_LEFT, 5)
        sizer.Add(self.tznum, (0, 12), (1, 3), wx.ALIGN_LEFT, 5)

        self.subtitle = [None, None]
        self.subtitle[0] = wx.StaticText(self, -1, label='         ')
        self.subtitle[0].SetFont(self.subtitlefont)
        self.subtitle[1] = wx.StaticText(self, -1, label='         ')
        self.subtitle[1].SetFont(self.subtitlefont)

        sizer.Add(self.subtitle[0], (1, 2), (1, 9), wx.ALIGN_LEFT)
        sizer.Add(self.subtitle[1], (2, 2), (1, 9), wx.ALIGN_LEFT)

        sizer.SetEmptyCellSize((2, 2))
        self.Bind(wx.EVT_KEY_UP, self.onKey)
        self.SetSizer(sizer)
        ix, iy = self.GetBestSize()
        self.SetSize((ix+2, iy+2))
        sizer.Fit(self)

    def set_subtitle(self, label, index=0):
        if index not in (0, 1): index = 0
        self.subtitle[index].SetLabel(label)

class PTableFrame(wx.Frame):
    def __init__(self, size=(-1, -1)):
        wx.Frame.__init__(self, parent=None, size=size)
        ptab  = PeriodicTablePanel(self, title='Periodic Table',
                                   tooltip_msg='Select Element',
                                   onselect=self.onElement)
        sx, sy = ptab.GetBestSize()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ptab, 1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetMinSize((sx+10, sy+10))
        self.Raise()

    def onElement(self, elem=None, event=None):
        print( 'Element Selected:  ', elem)

