#!/usr/bin/env python
"""
GUI Panels for setting up positioners for different scan types.
Current scan types:
    Linear Scans
    Mesh Scans (2d maps)
    XAFS Scans
    Fly Scans (optional)
"""
import wx
import wx.lib.agw.flatnotebook as flat_nb
import wx.lib.scrolledpanel as scrolled

import epics
from epics.wx import DelayedEpicsCallback, EpicsFunction

from .gui_utils import SimpleText, FloatCtrl, Closure
from .gui_utils import pack, add_choice

from .. import etok, ktoe

CEN = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL

ELEM_LIST = ('H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na',
             'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti',
             'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge',
             'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo',
             'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te',
             'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm',
             'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf',
             'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb',
             'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U',
             'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf')

class GenericScanPanel(scrolled.ScrolledPanel):
    __name__ = 'genericScan'
    def __init__(self, parent, config=None, pvlist=None, larch=None,
                 size=(625,300), style=wx.GROW|wx.TAB_TRAVERSAL):

        self.config = config
        self.pvlist = pvlist
        self.larch = larch
        scrolled.ScrolledPanel.__init__(self, parent,
                                        size=size, style=style,
                                        name=self.__name__)
        self.Font13=wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self._initialized = False # used to shunt events while creating windows

    def layout(self, panel, sizer, irow):
        sizer.Add(SimpleText(panel, "Estimated Scan Time:"),
                  (irow, 0,), (1, 2), CEN, 3)
        sizer.Add(self.est_time, (irow, 2), (1, 2), LEFT, 2)

        pack(panel, sizer)
        msizer = wx.BoxSizer(wx.VERTICAL)
        msizer.Add(panel, 1, wx.EXPAND)
        pack(self, msizer)
        self.Layout()
        self.SetupScrolling()
        self._initialized = True

    def setStepNpts(self, wids, label):
        "set step / npts for start/stop/step/npts list of widgets"
        start = wids[0].GetValue()
        stop = wids[1].GetValue()
        if label == 'npts':
            npts = max(2, wids[3].GetValue())
        else:
            step = wids[2].GetValue()
            npts = max(2, 1 + int(0.1 + abs(stop-start)/step))
        wids[3].SetValue(npts, act=False)
        wids[2].SetValue((stop-start)/(npts-1), act=False)

    def top_widgets(self, panel, sizer, title, irow=1,
                    dwell_prec=3, dwell_value=1):
        self.absrel = add_choice(panel,('Absolute', 'Relative'),
                                 action = self.onAbsRel)
        self.absrel.SetSelection(1)
        self.dwelltime = FloatCtrl(panel, precision=dwell_prec, value=dwell_value,
                                   act_on_losefocus=True, minval=0, size=(80, -1),
                                   action=Closure(self.onVal, label='dwelltime'))

        self.est_time  = SimpleText(panel, '00:00:00')
        title =  SimpleText(panel, title, font=self.Font13, colour='#880000',
                            style=LEFT)
        alabel = SimpleText(panel, ' Mode:')
        dlabel  = SimpleText(panel, 'Time/Point (sec):')

        sizer.Add(title,          (0,    0), (1, 3), CEN, 4)
        sizer.Add(alabel,         (irow, 0), (1, 1), CEN, 4)
        sizer.Add(self.absrel,    (irow, 1), (1, 1), CEN, 4)
        sizer.Add(dlabel,         (irow, 2), (1, 2), CEN, 3)
        sizer.Add(self.dwelltime, (irow, 4), (1, 1), LEFT, 2)
        sizer.Add(wx.StaticLine(panel, size=(675, 3), style=wx.LI_HORIZONTAL),
                  (irow+1, 0), (1, 8), wx.ALIGN_CENTER)
        return irow+2

    def StartStopStepNpts(self, panel, i, npts=True, initvals=(-1,1,1,3)):
        fsize = (95, -1)
        s0, s1, ds, ns = initvals
        start = FloatCtrl(panel, size=fsize, value=s0, act_on_losefocus=True,
                          action=Closure(self.onVal, index=i, label='start'))
        stop  = FloatCtrl(panel, size=fsize, value=s1, act_on_losefocus=True,
                          action=Closure(self.onVal, index=i, label='stop'))
        step  = FloatCtrl(panel, size=fsize, value=ds, act_on_losefocus=True,
                          action=Closure(self.onVal, index=i, label='step'))
        if npts:
            npts  = FloatCtrl(panel, precision=0,  value=ns, size=(50, -1),
                              act_on_losefocus=True,
                              action=Closure(self.onVal, index=i, label='npts'))
        else:
            npts  = wx.StaticText(panel, -1, size=fsize, label='    1')
        return start, stop, step, npts

    def onVal(self, index=0, label=None, value=None, **kws):
        pass

    def onAbsRel(self, evt=None):
        for index, wids in enumerate(self.pos_settings):
            if wids[3].Enabled:
                try:
                    offset = float(wids[2].GetLabel())
                except:
                    offset = 0.0
                if 1 == self.absrel.GetSelection(): # now relative (was absolute)
                    offset = -offset
                wids[3].SetValue(offset + wids[3].GetValue(), act=False)
                wids[4].SetValue(offset + wids[4].GetValue(), act=False)

    def use_config(self, config):
        pass

    def generate_scan(self):
        print 'generate scan ', self.__name__


class LinearScanPanel(GenericScanPanel):
    """ linear scan """
    __name__ = 'StepScan'

    def __init__(self, parent, **kws):
        GenericScanPanel.__init__(self, parent, size=(750, 250), **kws)

        panel = wx.Panel(self)
        sizer = wx.GridBagSizer(7, 8)

        ir = self.top_widgets(panel, sizer, 'Linear Step Scan Setup')
        for ic, lab in enumerate(("Role", "Positioner", "Units", "Current", "Start",
                                  "Stop", "Step", " Npts")):
            s  = CEN
            if lab == " Npts": s = LEFT
            sizer.Add(SimpleText(panel, lab), (ir, ic), (1, 1), s, 2)

        self.pos_settings = []
        pchoices=self.config.positioners.keys()
        fsize = (95, -1)
        for i in range(4):
            lab = 'Slave'
            if i == 0: lab = 'Master'
            if i > 0 and 'None' not in pchoices:
                pchoices.insert(0, 'None')

            pos = add_choice(panel, pchoices, size=(100, -1),
                             action=Closure(self.onPos, index=i))

            role = wx.StaticText(panel, -1, label=lab)
            units = wx.StaticText(panel, -1, size=(30, -1), label='mm')
            cur = wx.StaticText(panel, -1, size=(80, -1), label='1.000')

            start, stop, step, npts = self.StartStopStepNpts(panel, i,
                                                             npts=(i==0))

            self.pos_settings.append((pos, units, cur, start, stop, step, npts))
            if i > 0:
                start.Disable()
                stop.Disable()
                step.Disable()
                npts.Disable()
            ir += 1
            sizer.Add(role,  (ir, 0), (1, 1), wx.ALL, 2)
            sizer.Add(pos,   (ir, 1), (1, 1), wx.ALL, 2)
            sizer.Add(units, (ir, 2), (1, 1), wx.ALL, 2)
            sizer.Add(cur,   (ir, 3), (1, 1), wx.ALL, 2)
            sizer.Add(start, (ir, 4), (1, 1), wx.ALL, 2)
            sizer.Add(stop,  (ir, 5), (1, 1), wx.ALL, 2)
            sizer.Add(step,  (ir, 6), (1, 1), wx.ALL, 2)
            sizer.Add(npts,  (ir, 7), (1, 1), wx.ALL, 2)

        ir += 1
        l = wx.StaticLine(panel, size=(675, 3), style=wx.LI_HORIZONTAL|wx.GROW)
        sizer.Add(l, (ir, 0), (1, 8), wx.ALIGN_CENTER)

        ir += 1
        self.layout(panel, sizer, ir)

    def onVal(self, index=0, label=None, value=None, **kws):
        if not self._initialized: return
        if label in ('start', 'stop', 'step', 'npts'):
            self.setStepNpts(self.pos_settings[index][3:], label)

    def onPos(self, evt=None, index=0):
        print 'On Position   ', index, evt

    def use_config(self, config):
        poslist = config.positioners.keys()
        poslist.append('Dummy')
        if hasattr(self, 'pos_settings'):
            for i, wids in enumerate(self.pos_settings):
                a = wids[0].GetStringSelection()
                wids[0].Clear()
                if i > 0 and 'None' not in poslist:
                    poslist.insert(0, 'None')
                wids[0].SetItems(poslist)
                wids[0].SetStringSelection(a)


class XAFSScanPanel(GenericScanPanel):
    """xafs  scan """
    __name__ = 'XAFSScan'
    edges_list = ('K','L3','M5','L2','L1')
    units_list = ('eV', '1/A')

    def __init__(self, parent, **kws):
        GenericScanPanel.__init__(self, parent, size=(750, 325), **kws)
        self.reg_settings = []
        panel = wx.Panel(self)
        sizer = wx.GridBagSizer(7, 7)

        self.e0 = FloatCtrl(panel, precision=2, value=20000., minval=0, maxval=1e7,
                            size=(80, -1), act_on_losefocus=True,
                            action=Closure(self.onVal, label='e0'))

        self.elemchoice = add_choice(panel, ELEM_LIST,
                                     action=self.onEdgeChoice, size=(70, 25))
        self.elemchoice.SetMaxSize((50, 20))
        self.elemchoice.SetSelection(41)

        self.edgechoice = add_choice(panel, self.edges_list,
                                     action=self.onEdgeChoice)

        ir = self.top_widgets(panel, sizer,'XAFS Scan Setup', irow=2)

        nregs_wid = FloatCtrl(panel, precision=0, value=3, minval=0, maxval=5,
                            size=(25, -1),  act_on_losefocus=True,
                            action=Closure(self.onVal, label='nreg'))
        nregs = nregs_wid.GetValue()

        sizer.Add(SimpleText(panel, "# Regions:"),  (ir-2, 5), (1, 1), LEFT)
        sizer.Add(nregs_wid,                        (ir-2, 6), (1, 1), LEFT)

        sizer.Add(SimpleText(panel, "EdgeEnergy:", size=(100, -1),
                             style=wx.ALIGN_LEFT), (1, 0), (1, 1), CEN, 2)
        sizer.Add(self.e0,                        (1, 1), (1, 1), LEFT, 2)
        sizer.Add(SimpleText(panel, "Element:"),  (1, 2), (1, 1), LEFT)
        sizer.Add(self.elemchoice,                (1, 3), (1, 1), LEFT)
        sizer.Add(SimpleText(panel, "Edge:"),     (1, 4), (1, 1), LEFT)
        sizer.Add(self.edgechoice,                (1, 5), (1, 1), LEFT)

        for ic, lab in enumerate(("Region", "Start", "Stop", "Step",
                                    "Npts", "Time (s)", "Units")):
            sizer.Add(SimpleText(panel, lab),  (ir, ic), (1, 1), LEFT, 2)

        for i, reg in enumerate((('Pre-Edge', (-50, -10, 5, 9)),
                                  ('XANES',   (-10, 10, 1, 21)),
                                  ('EXAFS1',  (10, 200, 2, 96)),
                                  ('EXAFS2',  (200, 500, 3, 101)))):
            label, initvals = reg
            ir += 1
            reg   = wx.StaticText(panel, -1, size=(100, -1), label=' %s' % label)
            start, stop, step, npts = self.StartStopStepNpts(panel, i, initvals=initvals)
            dtime = FloatCtrl(panel, size=(65, -1), value=1, minval=0, precision=3,
                              action=Closure(self.onVal, index=i, label='dtime'))

            if i < 2:
                units = wx.StaticText(panel, -1, size=(30, -1), label='eV')
            else:
                units = add_choice(panel, self.units_list,
                                   action=Closure(self.onVal, label='units', index=i))
                # action=Closure(self.onUnitsChoice, index=i))

            self.reg_settings.append((start, stop, step, npts, dtime, units))
            if i >= nregs:
                start.Disable()
                stop.Disable()
                step.Disable()
                npts.Disable()
                dtime.Disable()
                units.Disable()
            sizer.Add(reg,   (ir, 0), (1, 1), wx.ALL, 5)
            sizer.Add(start, (ir, 1), (1, 1), wx.ALL, 2)
            sizer.Add(stop,  (ir, 2), (1, 1), wx.ALL, 2)
            sizer.Add(step,  (ir, 3), (1, 1), wx.ALL, 2)
            sizer.Add(npts,  (ir, 4), (1, 1), wx.ALL, 2)
            sizer.Add(dtime, (ir, 5), (1, 1), wx.ALL, 2)
            sizer.Add(units, (ir, 6), (1, 1), wx.ALL, 2)

        ir += 1
        l = wx.StaticLine(panel, size=(675, 3), style=wx.LI_HORIZONTAL|wx.GROW)
        sizer.Add(l, (ir, 0), (1, 7), wx.ALIGN_CENTER)

        self.kwtimechoice = add_choice(panel, ('0', '1', '2', '3'), size=(70, -1))

        self.kwtime = FloatCtrl(panel, precision=3, value=0, minval=0,
                                size=(65, -1),
                                action=Closure(self.onVal, label='kwtime'))

        ir += 1
        sizer.Add(SimpleText(panel, "k-weight time of last region:"),  (ir, 1,), (1, 2), CEN, 3)
        sizer.Add(self.kwtimechoice, (ir, 3), (1, 1), LEFT, 2)
        sizer.Add(SimpleText(panel, "Max Time:"),  (ir, 4,), (1, 1), CEN, 3)
        sizer.Add(self.kwtime, (ir, 5), (1, 1), LEFT, 2)

        ir += 1
        self.layout(panel, sizer, ir)

    def getUnits(self, index):
        un = self.reg_settings[index][5]
        if hasattr(un, 'GetStringSelection'):
            return un.GetStringSelection()
        else:
            return un.GetLabel()

    def onVal(self, evt=None, index=0, label=None, value=None, **kws):
        "XAFS onVal"
        if not self._initialized: return
        wids = self.reg_settings[index]
        units = self.getUnits(index)
        e0_off = 0
        if 0 == self.absrel.GetSelection(): # absolute
            e0_off = self.e0.GetValue()

        if label == 'dwelltime':
            for wid in self.reg_settings:
                wid[4].SetValue(value)
            try:
                self.kwtime.SetValue(value)
            except:
                pass
        elif label == 'nreg':
            nregs = value
            for ireg, reg in enumerate(self.reg_settings):
                if ireg < nregs:
                    for wid in reg: wid.Enable()
                else:
                    for wid in reg: wid.Disable()
        elif label == 'units':
            if units == 'eV': # was 1/A, convert to eV
                wids[0].SetValue(ktoe(wids[0].GetValue()) + e0_off)
                wids[1].SetValue(ktoe(wids[1].GetValue()) + e0_off)
                wids[2].SetValue(2.0)
            else:
                wids[0].SetValue(etok(wids[0].GetValue() - e0_off))
                wids[1].SetValue(etok(wids[1].GetValue() - e0_off))
                wids[2].SetValue(0.05)

            self.setStepNpts(wids, label)

        if label in ('start', 'stop', 'step', 'npts'):
            self.setStepNpts(wids, label)
            if label == 'stop' and index < len(self.reg_settings)-1:
                nunits = self.getUnits(index+1)
                if nunits != units:
                    if units == 'eV':
                        value = etok(value - e0_off)
                    else:
                        value = ktoe(value) + e0_off
                self.reg_settings[index+1][0].SetValue(value, act=False)
                self.setStepNpts(self.reg_settings[index+1], label)
            elif label == 'start' and index > 0:
                nunits = self.getUnits(index-1)
                if nunits != units:
                    if units == 'eV':
                        value = etok(value - e0_off)
                    else:
                        value = ktoe(value) + e0_off
                self.reg_settings[index-1][1].SetValue(value, act=False)
                self.setStepNpts(self.reg_settings[index-1], label)

    def onAbsRel(self, evt=None):
        offset = self.e0.GetValue()
        if 1 == self.absrel.GetSelection(): # relative (was absolute)
            offset = -offset
        for index, wids in enumerate(self.reg_settings):
            units = self.getUnits(index)
            if units == 'eV':
                for ix in range(2):
                    wids[ix].SetValue(wids[ix].GetValue() + offset, act=False)

    def onEdgeChoice(self, evt=None):
        edge = self.edgechoice.GetStringSelection()
        elem = self.elemchoice.GetStringSelection()
        if self.larch is not None:
            e0val = self.larch( "xray_edge('%s', '%s')" % (elem, edge))
            self.e0.SetValue(e0val[0])

class MeshScanPanel(GenericScanPanel):
    """ mesh / 2-d scan """
    __name__ = 'MeshScan'
    def __init__(self, parent, **kws):
        GenericScanPanel.__init__(self, parent, size=(750, 250), **kws)

        panel = wx.Panel(self)
        sizer = wx.GridBagSizer(7, 8)

        ir = self.top_widgets(panel, sizer, 'Mesh Scan (Slow Map) Setup')

        for ic, lab in enumerate(("Loop", "Positioner", "Units",
                                  "Current", "Start","Stop", "Step", " Npts")):
            s  = CEN
            if lab == " Npts": s = LEFT
            sizer.Add(SimpleText(panel, lab), (ir, ic), (1, 1), s, 2)

        self.pos_settings = []
        pchoices=self.config.positioners.keys()
        fsize = (95, -1)
        for i, label in enumerate(("Inner", "Outer")):
            lab = wx.StaticText(panel, -1, label=label)
            pos = add_choice(panel, pchoices, size=(100, -1),
                             action=Closure(self.onPos, index=i))

            units = wx.StaticText(panel, -1, size=(30, -1), label='mm')
            cur = wx.StaticText(panel, -1, size=(80, -1), label='1.000')
            start, stop, step, npts = self.StartStopStepNpts(panel, i)

            self.pos_settings.append((pos, units, cur, start, stop, step, npts))
            ir += 1
            sizer.Add(lab,   (ir, 0), (1, 1), wx.ALL, 2)
            sizer.Add(pos,   (ir, 1), (1, 1), wx.ALL, 2)
            sizer.Add(units, (ir, 2), (1, 1), wx.ALL, 2)
            sizer.Add(cur,   (ir, 3), (1, 1), wx.ALL, 2)
            sizer.Add(start, (ir, 4), (1, 1), wx.ALL, 2)
            sizer.Add(stop,  (ir, 5), (1, 1), wx.ALL, 2)
            sizer.Add(step,  (ir, 6), (1, 1), wx.ALL, 2)
            sizer.Add(npts,  (ir, 7), (1, 1), wx.ALL, 2)

        ir += 1
        l = wx.StaticLine(panel, size=(675, 3), style=wx.LI_HORIZONTAL|wx.GROW)
        sizer.Add(l, (ir, 0), (1, 8), wx.ALIGN_CENTER)

        ir += 1
        self.layout(panel, sizer, ir)

    def onVal(self, index=0, label=None, value=None, **kws):
        if not self._initialized: return
        print 'MeshScan on Value ', index, label, value, kws
        if label in ('start', 'stop', 'step', 'npts'):
            self.setStepNpts(self.pos_settings[index][3:], label)

    def onPos(self, evt=None, index=0):
        print 'On Position   ', index, evt

    def use_config(self, config):
        poslist = config.positioners.keys()
        poslist.append('Dummy')
        if hasattr(self, 'pos_settings'):
            for i, wids in enumerate(self.pos_settings):
                a = wids[0].GetStringSelection()
                wids[0].Clear()
                wids[0].SetItems(poslist)
                wids[0].SetStringSelection(a)

class SlewScanPanel(GenericScanPanel):
    """ mesh / 2-d scan """
    __name__ = 'SlewScan'
    def __init__(self, parent, **kws):
        GenericScanPanel.__init__(self, parent, size=(750, 250), **kws)

        panel = wx.Panel(self)
        sizer = wx.GridBagSizer(7, 8)

        ir = self.top_widgets(panel, sizer, 'Slew Scan (Fast Map) Setup')

        for ic, lab in enumerate(("Loop", "Positioner", "Units",
                                  "Current", "Start","Stop", "Step", " Npts")):
            s  = CEN
            if lab == " Npts": s = LEFT
            sizer.Add(SimpleText(panel, lab), (ir, ic), (1, 1), s, 2)

        self.pos_settings = []
        fsize = (95, -1)
        for i, label in enumerate(("Inner", "Outer")):
            lab = wx.StaticText(panel, -1, label=label)
            pchoices = self.config.positioners.keys()
            if i == 0:
                pchoices = self.config.slewscan_positioners.keys()
            pos = add_choice(panel, pchoices, size=(100, -1),
                             action=Closure(self.onPos, index=i))
            units = wx.StaticText(panel, -1, size=(30, -1), label='mm')
            cur = wx.StaticText(panel, -1, size=(80, -1), label='1.000')
            start, stop, step, npts = self.StartStopStepNpts(panel, i)

            self.pos_settings.append((pos, units, cur, start, stop, step, npts))
            ir += 1
            sizer.Add(lab,   (ir, 0), (1, 1), wx.ALL, 2)
            sizer.Add(pos,   (ir, 1), (1, 1), wx.ALL, 2)
            sizer.Add(units, (ir, 2), (1, 1), wx.ALL, 2)
            sizer.Add(cur,   (ir, 3), (1, 1), wx.ALL, 2)
            sizer.Add(start, (ir, 4), (1, 1), wx.ALL, 2)
            sizer.Add(stop,  (ir, 5), (1, 1), wx.ALL, 2)
            sizer.Add(step,  (ir, 6), (1, 1), wx.ALL, 2)
            sizer.Add(npts,  (ir, 7), (1, 1), wx.ALL, 2)

        ir += 1
        l = wx.StaticLine(panel, size=(675, 3), style=wx.LI_HORIZONTAL|wx.GROW)
        sizer.Add(l, (ir, 0), (1, 8), wx.ALIGN_CENTER)

        ir += 1
        self.layout(panel, sizer, ir)

    def onVal(self, index=0, label=None, value=None, **kws):
        if not self._initialized: return
        if label in ('start', 'stop', 'step', 'npts'):
            self.setStepNpts(self.pos_settings[index][3:], label)

    def onPos(self, evt=None, index=0):
        print 'On Position   ', index, evt

    def use_config(self, config):
        slewlist = config.slewscan_positioners.keys()
        poslist = config.positioners.keys()
        poslist.append('Dummy')
        inner = self.pos_settings[0][0]
        outer = self.pos_settings[1][0]
        for wid, vals in ((inner, slewlist), (outer, poslist)):
            a = wid.GetStringSelection()
            wid.Clear()
            wid.SetItems(vals)
            wid.SetStringSelection(a)

    def OLDSLEWSCANPanel(self):
        pane = wx.Panel(self, -1)

        self.dimchoice = wx.Choice(pane, size=(120,30))
        self.m1choice = wx.Choice(pane,  size=(120,30))
        self.m1units  = SimpleText(pane, "",minsize=(50,20))
        self.m1start  = FloatCtrl(pane, precision=4, value=0)
        self.m1stop   = FloatCtrl(pane, precision=4, value=1)
        self.m1step   = FloatCtrl(pane, precision=4, value=0.1)

        self.m1npts   = SimpleText(pane, "0",minsize=(55,20))
        # self.rowtime  = FloatCtrl(pane, precision=1, value=10., minval=0.)
        self.pixtime  = FloatCtrl(pane, precision=3, value=0.100, minval=0.)

        self.m2choice = wx.Choice(pane, size=(120,30),choices=[])
        self.m2units  = SimpleText(pane, "",minsize=(50,20))
        self.m2start  = FloatCtrl(pane, precision=4, value=0)
        self.m2stop   = FloatCtrl(pane, precision=4, value=1)
        self.m2step   = FloatCtrl(pane, precision=4, value=0.1)
        self.m2npts   = SimpleText(pane, "0",minsize=(60,20))

        self.maptime  = SimpleText(pane, "0")
        self.rowtime  = SimpleText(pane, "0")
        self.t_rowtime = 0.0

        self.filename = wx.TextCtrl(pane, -1, "")
        self.filename.SetMinSize((350, 25))

        self.usertitles = wx.TextCtrl(pane, -1, "",
                                      style=wx.TE_MULTILINE)
        self.usertitles.SetMinSize((350, 75))
        self.startbutton = wx.Button(pane, -1, "Start")
        self.abortbutton = wx.Button(pane, -1, "Abort")

        self.startbutton.Bind(wx.EVT_BUTTON, self.onStartScan)
        self.abortbutton.Bind(wx.EVT_BUTTON, self.onAbortScan)

        self.m1choice.Bind(wx.EVT_CHOICE, self.onM1Select)
        self.m2choice.Bind(wx.EVT_CHOICE, self.onM2Select)
        self.dimchoice.Bind(wx.EVT_CHOICE, self.onDimension)


        self.m1choice.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.m2choice.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.abortbutton.SetBackgroundColour(wx.Colour(255, 72, 31))

        gs = wx.GridBagSizer(8, 8)
        all_cvert = wx.ALL|wx.ALIGN_CENTER_VERTICAL
        all_bot   = wx.ALL|wx.ALIGN_BOTTOM|wx.ALIGN_CENTER_HORIZONTAL
        all_cen   = wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL

        # Title row
        nr = 0
        gs.Add(SimpleText(pane, "XRF Map Setup",
                     minsize=(200, 30),
                     font=self.Font16, colour=(120,0,0)),
               (nr,0), (1,4),all_cen)
        gs.Add(SimpleText(pane, "Scan Type",
                     minsize=(80,20),style=wx.ALIGN_RIGHT),
               (nr,5), (1,1), all_cvert)
        gs.Add(self.dimchoice, (nr,6), (1,2),
               wx.ALIGN_LEFT)
        nr +=1
        gs.Add(wx.StaticLine(pane, size=(650,3)),
               (nr,0), (1,8), all_cen)
        # title
        nr +=1
        gs.Add(SimpleText(pane, "Stage"),  (nr,1), (1,1), all_bot)
        gs.Add(SimpleText(pane, "Units",minsize=(50,20)),  (nr,2), (1,1), all_bot)
        gs.Add(SimpleText(pane, "Start"),  (nr,3), (1,1), all_bot)
        gs.Add(SimpleText(pane, "Stop"),   (nr,4), (1,1), all_bot)
        gs.Add(SimpleText(pane, "Step"),   (nr,5), (1,1), all_bot)
        gs.Add(SimpleText(pane, "Npoints"),(nr,6), (1,1), all_bot)
        gs.Add(SimpleText(pane, "Time Per Point (s)",
                     minsize=(140,20)),(nr,7), (1,1), all_cvert|wx.ALIGN_LEFT)
        # fast motor row
        nr +=1
        gs.Add(SimpleText(pane, "Fast Motor", minsize=(90,20)),
               (nr,0),(1,1), all_cvert )
        gs.Add(self.m1choice, (nr,1))
        gs.Add(self.m1units,  (nr,2))
        gs.Add(self.m1start,  (nr,3))
        gs.Add(self.m1stop,   (nr,4)) # 0, all_cen)
        gs.Add(self.m1step,   (nr,5))
        gs.Add(self.m1npts,   (nr,6),(1,1),wx.ALIGN_CENTER_HORIZONTAL)
        gs.Add(self.pixtime,  (nr,7))

        # slow motor row
        nr +=1
        gs.Add(SimpleText(pane, "Slow Motor", minsize=(90,20)),
               (nr,0),(1,1), all_cvert )
        gs.Add(self.m2choice, (nr,1))
        gs.Add(self.m2units,  (nr,2))
        gs.Add(self.m2start,  (nr,3))
        gs.Add(self.m2stop,   (nr,4)) # 0, all_cen)
        gs.Add(self.m2step,   (nr,5))
        gs.Add(self.m2npts,   (nr,6),(1,1),wx.ALIGN_CENTER_HORIZONTAL)
        #
        nr +=1
        gs.Add(wx.StaticLine(pane, size=(650,3)),(nr,0), (1,8),all_cen)

        # filename row
        nr +=1
        gs.Add(SimpleText(pane, "File Name", minsize=(90,20)), (nr,0))
        gs.Add(self.filename, (nr,1), (1,4))

        gs.Add(SimpleText(pane, "Time per line (sec):",
                     minsize=(-1, 20), style=wx.ALIGN_LEFT),
               (nr,5), (1,2), wx.ALIGN_LEFT)
        gs.Add(self.rowtime, (nr,7))

        # title row
        nr +=1
        gs.Add(SimpleText(pane, "Comments ",
                     minsize=(80,50)), (nr,0))
        gs.Add(self.usertitles,        (nr,1),(1,4))
        gs.Add(SimpleText(pane, "Time for map (H:Min:Sec):",
                     minsize=(-1,20), style=wx.ALIGN_LEFT),
               (nr,5), (1,2), wx.ALIGN_LEFT)
        gs.Add(self.maptime, (nr,7))

        # button row
        nr +=1
        gs.Add(SimpleText(pane, " ", minsize=(90,35)), (nr,0))
        gs.Add(self.startbutton, (nr,1))
        gs.Add(self.abortbutton, (nr,3))
        #
        # nr +=1
        #gs.Add(wx.StaticLine(pane, size=(650,3)),(nr,0), (1,7),all_cen)

        pane.SetSizer(gs)

        MainSizer = wx.BoxSizer(wx.VERTICAL)
        MainSizer.Add(pane, 1, 0,0)
        self.SetSizer(MainSizer)
        MainSizer.SetSizeHints(self)
        MainSizer.Fit(self)
        self.Layout()


