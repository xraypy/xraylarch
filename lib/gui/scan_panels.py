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
import wx.lib.scrolledpanel as scrolled
import numpy as np
from datetime import timedelta
import epics
from epics.wx import EpicsFunction, PVText

from .gui_utils import SimpleText, FloatCtrl, Closure
from .gui_utils import pack, add_choice

from .. import etok, ktoe, XAFS_Scan, StepScan, Positioner, Counter

CEN = wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL
LEFT = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL
RIGHT = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL
LINWID = 700

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
    def __init__(self, parent, scandb=None, pvlist=None, larch=None,
                 size=(760, 380), style=wx.GROW|wx.TAB_TRAVERSAL):

        self.scandb = scandb

        self.pvlist = pvlist
        self.larch = larch
        scrolled.ScrolledPanel.__init__(self, parent,
                                        size=size, style=style,
                                        name=self.__name__)
        self.Font13=wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD, 0, "")
        self.sizer = wx.GridBagSizer(8, 8)
        self.get_positioners()
        self._initialized = False # used to shunt events while creating windows

    def get_positioners(self):
        self.pospvs = {'None': ('', ''), 'Dummy': ('', '')}
        self.poslist = ['None', 'Dummy']
        for pos in self.scandb.get_positioners():
            self.poslist.append(pos.name)
            self.pospvs[pos.name] = (pos.drivepv, pos.readpv)

        self.slewlist = []
        for pos in self.scandb.get_slewpositioners():
            self.slewlist.append(pos.name)

    def update_positioners(self):
        """meant to be overwritten"""
        self.get_positioners()

    def hline(self):
        return wx.StaticLine(self, size=(700, 3),
                             style=wx.LI_HORIZONTAL|wx.GROW)

    def layout(self):
        self.bgcol = self.GetBackgroundColour()
        pack(self, self.sizer)
        self.SetupScrolling()
        self._initialized = True

    def setStepNpts(self, wids, label, fix_npts=False):
        "set step / npts for start/stop/step/npts list of widgets"
        start = wids[0].GetValue()
        stop  = wids[1].GetValue()
        step = wids[2].GetValue()
        if label == 'npts' or fix_npts:
            npts = max(2, wids[3].GetValue())
        else:
            try:
                npts = max(2, 1 + int(0.1 + abs(stop-start)/abs(step)))
            except ZeroDivisionError:
                npts = 3
        wids[2].SetValue((stop-start)/(npts-1), act=False)
        if not fix_npts:
            try:
                wids[3].SetValue(npts, act=False)
            except AttributeError:
                pass

    def setScanTime(self):
        "set estimated scan time"
        dtime = (float(self.dwelltime.GetValue()) +
                 float(self.scandb.get_info('pos_settle_time')) +
                 float(self.scandb.get_info('det_settle_time')) )
        for p in self.pos_settings:
            if hasattr(p[6], 'GetValue'):
                dtime *= float(p[6].GetValue())
        self.est_time.SetLabel(str(timedelta(seconds=int(dtime))))

    def top_widgets(self, title, dwell_prec=3, dwell_value=1):
        self.absrel = add_choice(self, ('Absolute', 'Relative'),
                                 action = self.onAbsRel)
        self.absrel.SetSelection(1)
        self.dwelltime = FloatCtrl(self, precision=dwell_prec,
                                   value=dwell_value,
                                   act_on_losefocus=True,
                                   minval=0, size=(80, -1),
                                   action=Closure(self.onVal,
                                                  label='dwelltime'))

        self.est_time  = SimpleText(self, '  00:00:00  ')
        title  =  SimpleText(self, " %s" % title, style=LEFT,
                             font=self.Font13, colour='#880000')

        alabel = SimpleText(self, ' Mode: ', size=(60, -1))
        dlabel = SimpleText(self, ' Time/Point (sec):')
        tlabel = SimpleText(self, ' Estimated Scan Time:  ')

        sizer = self.sizer

        sizer.Add(title,          (0, 0), (1, 3), LEFT,  3)
        sizer.Add(tlabel,         (0, 4), (1, 2), RIGHT, 3)
        sizer.Add(self.est_time,  (0, 6), (1, 2), CEN,   3)
        sizer.Add(alabel,         (1, 0), (1, 1), LEFT,  3)
        sizer.Add(self.absrel,    (1, 1), (1, 1), LEFT,  3)
        sizer.Add(dlabel,         (1, 2), (1, 2), RIGHT, 3)
        sizer.Add(self.dwelltime, (1, 4), (1, 2), LEFT,  3)
        # return next row for sizer
        return 2

    def StartStopStepNpts(self, i, with_npts=True, initvals=(-1,1,1,3)):
        fsize = (95, -1)
        s0, s1, ds, ns = initvals

        start = FloatCtrl(self, size=fsize, value=s0, act_on_losefocus=True,
                          action=Closure(self.onVal, index=i, label='start'))
        stop  = FloatCtrl(self, size=fsize, value=s1, act_on_losefocus=True,
                          action=Closure(self.onVal, index=i, label='stop'))
        step  = FloatCtrl(self, size=fsize, value=ds, act_on_losefocus=True,
                          action=Closure(self.onVal, index=i, label='step'))
        if with_npts:
            npts  = FloatCtrl(self, precision=0,  value=ns, size=(50, -1),
                              act_on_losefocus=True,
                              action=Closure(self.onVal, index=i, label='npts'))
        else:
            npts  = wx.StaticText(self, -1, size=fsize, label=' ')
        return start, stop, step, npts

    def onVal(self, index=0, label=None, value=None, **kws):
        pass

    @EpicsFunction
    def update_position_from_pv(self, index, name=None):
        if not hasattr(self, 'pos_settings'):
            return
        if name is None:
            name = self.pos_settings[index][0].GetStringSelection()

        wids = self.pos_settings[index]
        # clear current widgets for this row
        try:
            wids[2].pv.clear_callbacks()
        except:
            pass
        for i in (1, 2):
            wids[i].SetLabel('')
        if name == 'None':
            for i in (3, 4, 5, 6):
                wids[i].Disable()
            return
        for i in (3, 4, 5, 6):
            wids[i].Enable()

        pvnames = self.pospvs[name]
        if len(pvnames[0]) < 1:
            return
        if '.' not in pvnames[1]: pvnames[1] = pvnames[1] + '.VAL'
        if '.' not in pvnames[0]: pvnames[0] = pvnames[0] + '.VAL'
        if pvnames[0] not in self.pvlist:
            self.pvlist[pvnames[0]] = epics.PV(pvnames[0])
            self.pvlist[pvnames[1]] = epics.PV(pvnames[1])
            return
        unitspv = pvnames[1][:-4] + '.EGU'
        has_unitspv = unitspv in self.pvlist
        if not has_unitspv:
            self.pvlist[unitspv]  = epics.PV(unitspv)

        mpv  = self.pvlist[pvnames[1]]
        units = mpv.units
        if has_unitspv:
            units  = self.pvlist[unitspv].get()

        hlim = mpv.upper_disp_limit
        llim = mpv.lower_disp_limit
        if hlim == llim:
            hlim = llim = None
        elif 1 == self.absrel.GetSelection(): # relative
            hlim = hlim - mpv.value
            llim = llim - mpv.value
        wids[1].SetLabel(units)
        wids[2].SetPV(mpv)
        wids[2].SetBackgroundColour(self.bgcol)
        for i in (3, 4):
            wids[i].SetMin(llim)
            wids[i].SetMax(hlim)
            wids[i].SetPrecision(mpv.precision)

    def onAbsRel(self, evt=None):
        "generic abs/rel"
        for index, wids in enumerate(self.pos_settings):
            if wids[3].Enabled:
                try:
                    offset = float(wids[2].GetLabel())
                except:
                    offset = 0.0

                if 1 == self.absrel.GetSelection(): # now relative (was absolute)
                    offset = -offset
                wids[3].SetMin(wids[3].GetMin() + offset)
                wids[3].SetMax(wids[3].GetMax() + offset)
                wids[4].SetMin(wids[4].GetMin() + offset)
                wids[4].SetMax(wids[4].GetMax() + offset)


                wids[3].SetValue(offset + wids[3].GetValue(), act=False)
                wids[4].SetValue(offset + wids[4].GetValue(), act=False)
                self.update_position_from_pv(index)

    def initialize_positions(self):
        if hasattr(self, 'pos_settings'):
            for index in range(len(self.pos_settings)):
                self.update_position_from_pv(index)

    def use_scandb(self, scandb):
        pass

    def generate_scan(self):
        print 'Def generate scan ', self.__name__

class LinearScanPanel(GenericScanPanel):
    """ linear scan """
    __name__ = 'StepScan'

    def __init__(self, parent, **kws):
        GenericScanPanel.__init__(self, parent, **kws)

        sizer = self.sizer
        ir = self.top_widgets('Linear Step Scan')

        sizer.Add(self.hline(), (ir, 0), (1, 8), wx.ALIGN_CENTER)
        ir += 1
        for ic, lab in enumerate(("Role", "Positioner", "Units",
                                  "Current", "Start",
                                  "Stop", "Step", " Npts")):
            s  = CEN
            if lab == " Npts": s = LEFT
            sizer.Add(SimpleText(self, lab), (ir, ic), (1, 1), s, 2)

        self.pos_settings = []
        fsize = (95, -1)
        for i in range(3):
            lab = ' Follow'
            pchoices = self.poslist[:]
            idefault = 0
            if i == 0:
                lab = ' Lead'
                pchoices = pchoices[1:]
                idefault = 1
            pos = add_choice(self, pchoices, size=(100, -1),
                             action=Closure(self.onPos, index=i))
            pos.SetSelection(idefault)
            role  = wx.StaticText(self, -1, label=lab)
            units = wx.StaticText(self, -1, label='', size=(40, -1))
            cur   = PVText(self, pv=None, size=(100, -1))
            start, stop, step, npts = self.StartStopStepNpts(i, with_npts=(i==0))
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
        sizer.Add(self.hline(), (ir, 0), (1, 8), wx.ALIGN_CENTER)
        self.layout()
        self.update_position_from_pv(0)

    def update_positioners(self):
        """meant to be overwritten"""
        self.get_positioners()
        for irow, row in enumerate(self.pos_settings):
            thispos = row[0]
            cur = thispos.GetStringSelection()
            thispos.Clear()
            if irow == 0: 
                thispos.SetItems(self.poslist[1:])
            else:
                thispos.SetItems(self.poslist)
            if cur in self.poslist:
                thispos.SetStringSelection(cur)
            else:
                thispos.SetSelection(0)
            
    def onVal(self, index=0, label=None, value=None, **kws):
        if not self._initialized: return
        npts = self.pos_settings[0][6]
        wids = list(self.pos_settings[index][3:])

        if index == 0:
            self.setStepNpts(wids, label)
            for index, w in enumerate(self.pos_settings[1:]):
                if w[3].Enabled:
                    wids = list(w[3:])
                    wids[3] =  npts
                    self.setStepNpts(wids, label, fix_npts=True)
        else:
            wids[3] = npts
            self.setStepNpts(wids, label, fix_npts=True)
        self.setScanTime()

    def onPos(self, evt=None, index=0):
        self.update_position_from_pv(index)

    def use_scandb(self, scandb):
        self.get_positioners()
        if hasattr(self, 'pos_settings'):
            for i, wids in enumerate(self.pos_settings):
                a = wids[0].GetStringSelection()
                wids[0].Clear()
                #if i > 0: and 'None' not in self.poslist:
                #    poslist.insert(0, 'None')
                wids[0].SetItems(self.poslist)
                wids[0].SetStringSelection(a)

    def generate_scan(self):
        s = {'type': 'linear',
             'dwelltime':  float(self.dwelltime.GetValue()),
             'positioners': []}

        is_relative =  self.absrel.GetSelection()
        for i, wids in enumerate(self.pos_settings):
            pos, u, cur, start, stop, dx, wnpts = wids
            if i == 0:
                npts = wnpts.GetValue()
            if start.Enabled:
                name = pos.GetStringSelection()
                xpos = self.scandb.get_positioner(name)
                pvnames = (xpos.drivepv, xpos.readpv)
                p1 = start.GetValue()
                p2 = stop.GetValue()
                if is_relative:
                    try:
                        off = float(cur.GetLabel())
                    except:
                        off = 0
                    p1 += off
                    p2 += off
                s['positioners'].append((name, pvnames, p1, p2, npts))
        return s

class XAFSScanPanel(GenericScanPanel):
    """xafs  scan """
    __name__ = 'XAFSScan'
    edges_list = ('K', 'L3', 'L2', 'L1', 'M5')
    units_list = ('eV', u'1/\u212B')

    def __init__(self, parent, **kws):
        GenericScanPanel.__init__(self, parent, **kws)
        self.reg_settings = []
        self.cur_units = []

        sizer = self.sizer
        ir = self.top_widgets('XAFS Scan')
        sizer.Add(self.hline(),  (ir, 0), (1, 8), wx.ALIGN_CENTER)

        nregs_wid = FloatCtrl(self, precision=0, value=3, minval=0, maxval=5,
                            size=(25, -1),  act_on_losefocus=True,
                            action=Closure(self.onVal, label='nreg'))
        nregs = nregs_wid.GetValue()

        sizer.Add(SimpleText(self, "# Regions:"), (ir-1, 6), (1, 1), LEFT)
        sizer.Add(nregs_wid,                      (ir-1, 7), (1, 1), LEFT)
        ir += 1
        sizer.Add(self.make_e0panel(),            (ir,   0), (1, 6), LEFT)
        ir += 1

        sizer.Add(self.hline(),    (ir, 0), (1, 8), wx.ALIGN_CENTER)
        ir += 1
        for ic, lab in enumerate((" Region", "Start", "Stop", "Step",
                                    "Npts", "Time (s)", "Units")):
            sizer.Add(SimpleText(self, lab),  (ir, ic), (1, 1), LEFT, 2)

        for i, reg in enumerate((('Pre-Edge', (-50, -10, 5, 9)),
                                  ('XANES',   (-10, 10, 1, 21)),
                                  ('EXAFS1',  (10, 200, 2, 96)),
                                  ('EXAFS2',  (200, 500, 3, 101)))):
            label, initvals = reg
            ir += 1
            reg   = wx.StaticText(self, -1, size=(100, -1), label=' %s' % label)
            start, stop, step, npts = self.StartStopStepNpts(i, initvals=initvals)
            dtime = FloatCtrl(self, size=(65, -1), value=1, minval=0,
                              precision=3,
                              action=Closure(self.onVal, index=i, label='dtime'))

            if i < 2:
                units = wx.StaticText(self, -1, size=(30, -1), label='eV')
            else:
                units = add_choice(self, self.units_list,
                                   action=Closure(self.onVal, label='units', index=i))
            self.cur_units.append('eV')

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
        sizer.Add(self.hline(), (ir, 0), (1, 7), wx.ALIGN_CENTER)

        self.kwtimechoice = add_choice(self, ('0', '1', '2', '3'), size=(70, -1),
                                     action=Closure(self.onVal, label='kwpow'))

        self.kwtime = FloatCtrl(self, precision=3, value=0, minval=0,
                                size=(65, -1),
                                action=Closure(self.onVal, label='kwtime'))

        ir += 1
        sizer.Add(SimpleText(self, "k-weight time of last region:"),  (ir, 1,), (1, 2), CEN, 3)
        sizer.Add(self.kwtimechoice, (ir, 3), (1, 1), LEFT, 2)
        sizer.Add(SimpleText(self, "Max Time:"),  (ir, 4,), (1, 1), CEN, 3)
        sizer.Add(self.kwtime, (ir, 5), (1, 1), LEFT, 2)

        self.layout()

    def setScanTime(self):
        etime = (float(self.scandb.get_info('pos_settle_time')) +
                 float(self.scandb.get_info('det_settle_time')) )
        dtime = 0.0
        kwt_max = float(self.kwtime.GetValue())
        kwt_pow = float(self.kwtimechoice.GetStringSelection())
        print ' Set  XAFS Scan Time ', etime, kwt_pow, kwt_max
        dtimes = []
        for reg in self.reg_settings:
            nx = float(reg[3].GetValue())
            dx = float(reg[4].GetValue())
            if reg[4].Enabled:
                dtimes.append((nx, dx))
        if kwt_pow != 0:
            #nx, dx = dtimes.pop()
            print 'need to calc k-weighted time correctly!!'

        for nx, dx in dtimes:
            dtime += nx*(dx + etime)

        self.est_time.SetLabel(str(timedelta(seconds=int(dtime))))


    def make_e0panel(self):
        p = wx.Panel(self)
        s = wx.BoxSizer(wx.HORIZONTAL)
        self.e0 = FloatCtrl(p, precision=2, value=20000., minval=0, maxval=1e7,
                            size=(80, -1), act_on_losefocus=True,
                            action=Closure(self.onVal, label='e0'))

        self.elemchoice = add_choice(p, ELEM_LIST,
                                     action=self.onEdgeChoice, size=(70, 25))
        self.elemchoice.SetMaxSize((50, 20))
        self.elemchoice.SetSelection(41)

        self.edgechoice = add_choice(p, self.edges_list,
                                     action=self.onEdgeChoice)

        s.Add(SimpleText(p, " Edge Energy:", size=(120, -1),
                         style=wx.ALIGN_LEFT), 0, CEN, 2)
        s.Add(self.e0,   0, LEFT, 2)
        s.Add(SimpleText(p, "    Element:  "),  0, LEFT, 3)
        s.Add(self.elemchoice,                   0, LEFT, 3)
        s.Add(SimpleText(p, "     Edge:  "),     0, LEFT, 3)
        s.Add(self.edgechoice,                   0, LEFT, 3)
        pack(p, s)
        return p

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
        old_units = self.cur_units[index]
        e0_off = 0
        update_esttime = label in ('dtime', 'dwelltime',
                                   'kwpow', 'kwtime', 'step', 'npts')
        if 0 == self.absrel.GetSelection(): # absolute
            e0_off = self.e0.GetValue()

        if label == 'dwelltime':
            for wid in self.reg_settings:
                wid[4].SetValue(value)
            try:
                self.kwtime.SetValue(value)
            except:
                pass
            update_esttime = True
        elif label == 'nreg':
            nregs = value
            for ireg, reg in enumerate(self.reg_settings):
                if ireg < nregs:
                    for wid in reg: wid.Enable()
                else:
                    for wid in reg: wid.Disable()

        elif label == 'units':
            if units == 'eV' and old_units != 'eV': # was 1/A, convert to eV
                wids[0].SetValue(ktoe(wids[0].GetValue()) + e0_off)
                wids[1].SetValue(ktoe(wids[1].GetValue()) + e0_off)
                wids[2].SetValue(2.0)
            elif units != 'eV' and old_units == 'eV': # was eV, convert to 1/A
                wids[0].SetValue(etok(wids[0].GetValue() - e0_off))
                wids[1].SetValue(etok(wids[1].GetValue() - e0_off))
                wids[2].SetValue(0.05)
            self.cur_units[index] = units
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

        self.setScanTime()

    def onAbsRel(self, evt=None):
        """xafs abs/rel"""
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

    def generate_scan(self):
        s = {'type': 'xafs',
             'e0': self.e0.GetValue(),
             'is_relative': 1==self.absrel.GetSelection(),
             'max_time': self.kwtime.GetValue(),
             'time_kw': int(self.kwtimechoice.GetSelection()),
             'regions': []}
        for index, wids in enumerate(self.reg_settings):
            start, stop, step, npts, dtime, units =  wids
            if start.Enabled:
                p1 = start.GetValue()
                p2 = stop.GetValue()
                np = npts.GetValue()
                dt = dtime.GetValue()
                un = self.getUnits(index)
                s['regions'].append((p1, p2, np, dt, un))
        return s

class MeshScanPanel(GenericScanPanel):
    """ mesh / 2-d scan """
    __name__ = 'MeshScan'
    def __init__(self, parent, **kws):
        GenericScanPanel.__init__(self, parent, **kws)
        sizer = self.sizer

        ir = self.top_widgets('Mesh Scan (Slow Map)')
        sizer.Add(self.hline(), (ir, 0), (1, 8), wx.ALIGN_CENTER)
        ir += 1

        for ic, lab in enumerate(("Loop", "Positioner", "Units",
                                  "Current", "Start","Stop", "Step", " Npts")):
            s  = CEN
            if lab == " Npts": s = LEFT
            sizer.Add(SimpleText(self, lab), (ir, ic), (1, 1), s, 2)

        self.pos_settings = []
        pchoices = [p.name for p in self.scandb.get_positioners()]
        fsize = (95, -1)
        for i, label in enumerate((" Inner ", " Outer ")):
            lab = wx.StaticText(self, -1, label=label)
            pos = add_choice(self, pchoices, size=(100, -1),
                             action=Closure(self.onPos, index=i))
            pos.SetSelection(i)
            units = wx.StaticText(self, -1, size=(40, -1), label='')
            cur   = PVText(self, pv=None, size=(100, -1))
            start, stop, step, npts = self.StartStopStepNpts(i)

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
        sizer.Add(self.hline(), (ir, 0), (1, 8), wx.ALIGN_CENTER)
        self.layout()

    def update_positioners(self):
        """meant to be overwritten"""
        self.get_positioners()
        for irow, row in enumerate(self.pos_settings):
            thispos = row[0]
            cur = thispos.GetStringSelection()
            thispos.Clear()
            thispos.SetItems(self.poslist[1:])
            if cur in self.poslist:
                thispos.SetStringSelection(cur)
            else:
                thispos.SetSelection(0)

    def onVal(self, index=0, label=None, value=None, **kws):
        if not self._initialized: return
        if label in ('start', 'stop', 'step', 'npts'):
            self.setStepNpts(self.pos_settings[index][3:], label)
        self.setScanTime()

    def onPos(self, evt=None, index=0):
        self.update_position_from_pv(index)

    def use_scandb(self, scandb):
        self.get_positioners()
        if hasattr(self, 'pos_settings'):
            for i, wids in enumerate(self.pos_settings):
                a = wids[0].GetStringSelection()
                wids[0].Clear()
                wids[0].SetItems(self.poslist)
                wids[0].SetStringSelection(a)

    def generate_scan(self):
        s = {'type': 'mesh',
             'dwelltime':  float(self.dwelltime.GetValue()),
             'inner': [],
             'outer': []}

        is_relative =  self.absrel.GetSelection()
        for i, wids in enumerate(self.pos_settings):
            pos, u, cur, start, stop, dx, wnpts = wids
            npts = wnpts.GetValue()
            name = pos.GetStringSelection()
            xpos = self.scandb.get_positioner(name)
            pvnames = (xpos.drivepv, xpos.readpv)
            p1 = start.GetValue()
            p2 = stop.GetValue()
            if is_relative:
                p1 += float(cur.GetLabel())
                p2 += float(cur.GetLabel())
            mname = 'outer'
            if i == 0: mname = 'inner'
            s[mname].append((name, pvnames, p1, p2, npts))
        return s

class SlewScanPanel(GenericScanPanel):
    """ mesh / 2-d scan """
    __name__ = 'SlewScan'
    def __init__(self, parent, **kws):
        GenericScanPanel.__init__(self, parent, **kws)

        sizer = self.sizer

        ir = self.top_widgets('Slew Scan (Fast Map)')

        self.dimchoice = add_choice(self, ('1', '2'),
                                 action = self.onDim)
        self.dimchoice.SetSelection(1)
        sizer.Add(SimpleText(self, ' Dimension:'), (ir-1, 6), (1, 1), CEN)
        sizer.Add(self.dimchoice,                  (ir-1, 7), (1, 2), CEN)

        sizer.Add(self.hline(), (ir, 0), (1, 8), wx.ALIGN_CENTER)
        ir += 1
        for ic, lab in enumerate(("Loop", "Positioner", "Units",
                                  "Current", "Start","Stop", "Step", " Npts")):
            s  = CEN
            if lab == " Npts": s = LEFT
            sizer.Add(SimpleText(self, lab), (ir, ic), (1, 1), s, 2)

        self.pos_settings = []
        fsize = (95, -1)
        for i, label in enumerate((" Inner ", " Outer ")):
            lab = wx.StaticText(self, -1, label=label)
            pchoices = [p.name for p in self.scandb.get_positioners()]
            if i == 0:
                pchoices = [p.name for p in self.scandb.get_slewpositioners()]

            pos = add_choice(self, pchoices, size=(100, -1),
                             action=Closure(self.onPos, index=i))
            pos.SetSelection(i)
            units = wx.StaticText(self, -1, size=(40, -1), label='')
            cur   = PVText(self, pv=None, size=(100, -1))
            start, stop, step, npts = self.StartStopStepNpts(i)

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
        sizer.Add(self.hline(), (ir, 0), (1, 8), wx.ALIGN_CENTER)

        self.layout()

    def update_positioners(self):
        """meant to be overwritten"""
        self.get_positioners()
        for irow, row in enumerate(self.pos_settings):
            thispos = row[0]
            cur = thispos.GetStringSelection()
            thispos.Clear()
            plist = self.poslist[2:]
            if irow == 0:
                plist = self.slewlist
            thispos.SetItems(plist)
            if cur in plist:
                thispos.SetStringSelection(cur)
            else:
                thispos.SetSelection(0)

    def onVal(self, index=0, label=None, value=None, **kws):
        if not self._initialized: return
        if label in ('start', 'stop', 'step', 'npts'):
            self.setStepNpts(self.pos_settings[index][3:], label)
        self.setScanTime()

    def onDim(self, evt=None):
        wids = self.pos_settings[1]
        self.update_position_from_pv(0)

        if self.dimchoice.GetSelection() == 0: # 1-d
            for i in (1, 2): wids[i].SetLabel('')
            for i in (3, 4, 5, 6): wids[i].Disable()
        else:
            for i in (3, 4, 5, 6): wids[i].Enable()
            self.update_position_from_pv(1)

    def onPos(self, evt=None, index=0):
        self.update_position_from_pv(index)

    def use_scandb(self, scandb):
        self.get_positioners()
        inner = self.pos_settings[0][0]
        outer = self.pos_settings[1][0]
        for wid, vals in ((inner, self.slewlist), (outer, self.poslist)):
            a = wid.GetStringSelection()
            wid.Clear()
            wid.SetItems(vals)
            wid.SetStringSelection(a)

    def generate_scan(self):
        s = {'type': 'slew',
             'dwelltime':  float(self.dwelltime.GetValue()),
             'dimension': 2,
             'inner': [],
             'outer': []}

        is_relative =  self.absrel.GetSelection()
        for i, wids in enumerate(self.pos_settings):
            pos, u, cur, start, stop, dx, wnpts = wids
            if start.Enabled:
                npts = wnpts.GetValue()
                name = pos.GetStringSelection()
                xpos = self.scandb.get_positioner(name)
                pvnames = (xpos.drivepv, xpos.readpv)
                p1 = start.GetValue()
                p2 = stop.GetValue()
                if is_relative:
                    p1 += float(cur.GetLabel())
                    p2 += float(cur.GetLabel())
                mname = 'outer'
                if i == 01: mname = 'inner'
                s[mname].append((name, pvnames, p1, p2, npts))
        return s


