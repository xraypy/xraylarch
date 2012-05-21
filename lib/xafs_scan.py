#!/usr/bin/env python
"""
xafs scan
based on EpicsApps.StepScan.

"""
import numpy as np

from .stepscan import StepScan
from .positioner import Positioner

XAFS_K2E = 3.809980849311092

def etok(energy):
    return np.sqrt(energy/XAFS_K2E)

def ktoe(k):
    return k*k*XAFS_K2E

class XAFS_Scan(StepScan):
    def __init__(self, label=None, energy_pv=None, read_pv=None,
                 e0=0, dtime=1, **kws):
        self.label = label
        self.e0 = e0
        self.energies = []
        self.dwelltimes   = []
        self.dtime = dtime
        StepScan.__init__(self, **kws)

        self.energy_pos = None
        self.set_energy_pv(energy_pv, read_pv=read_pv)

    def set_energy_pv(energy_pv, read_pv=None):
        if energy_pv is not None:
            self.energy_pos = Positioner(energy_pv, label='Energy'))
            self.positioners = []
            self.add_positioner(self.energy_pos)
        if read_pv is not None:
            self.add_counter(read_pv, label='Energy (read)')

    def read_config_file(self, configfile):
        """read configuration from INI file"""
        pass

    def save_config_file(self, configfile):
        """write configuration from INI file"""
        pass

    def add_region(self, start, stop, step=None, npts=None,
                   relative=True, use_k=False, e0=None,
                   dtime=None, dtime_final=None, dtime_wt=1):
        """add a region to an EXAFS scan.
        Note that scans must be added in order of increasing energy

        """
        if e0 is None:
            e0 = self.e0
        if dtime is None:
            dtime = self.dtime
        self.e0 = e0
        self.dtime = dtime

        if npts is None and step is None:
            print 'add_region needs start, stop, and either step on npts'
            return

        if step is not None:
            npts = 1 + int(0.1  + abs(stop - start)/step)

        en_arr = list(np.linspace(start, stop, npts))
        if use_k:
            for i, k in enumerate(en_arr):
                en_arr[i] = e0 + ktoe(k)
        elif relative:
            for i, v in enumerate(en_arr):
                en_arr[i] = e0 + v

        # check that all energy values in this region are greater
        # than previously defined regions
        en_arr.sort()
        if len(self.energies)  > 0:
            en_arr = [e for e in en_arr if e > max(self.energies)]

        npts   = len(en_arr)
        dt_arr = [dtime]*npts
        # allow changing counting time linear or by a power law.
        if dtime_final is not None and dtime_wt > 0:
            _vtime = (dtime_final-dtime)*(1.0/(npts-1))**dtime_wt
            dt_arr= [dtime + _vtime *i**dtime_wt for i in range(npts)]
        self.energies.extend(en_arr)
        self.dwelltimes.extend(dt_arr)

    def clear(self):
        self.energies = []
        self.dwelltimes = []

    def load_scan(self):
        print 'load scan'
        if self.energy_pos is None:
            print 'Need Energy Positioner!'
            return
        self.energy_pos.array = self.energies

        # set detector dwelltime array
        for d in self.detectors:
            if d.dwelltime_pv is not None:
                thipos = None
                for p in self.positoners:
                    if p.pv.pvname == d.dwelltime_pv.pvname:
                        thispos = p
                if thispos is None:
                    thispos = Positioner(d.dwelltime_pv.pvname,
                                         label = "%s time" % d.label)
                    self.add_positioner(thispos)
                thispos.array = self.dwelltimes
        print 'Positioners: ', self.positioners
        print 'Detectors: ', self.detectors
        self.set_dwelltime(self.dwelltimes[0])
        if self.energy_pre_scan not in self.pre_scan_methods:
            self.pre_scan_methods.append(self.energy_pre_scan)

    def energy_pre_scan(self):
        """special pre_scan command for XAFS scans
        put here to be overridden -- may need setting mono modes.
        """
        self.energy_pos.move_to_start()

