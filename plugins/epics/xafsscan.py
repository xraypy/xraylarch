#!/usr/bin/env python
"""
xafs scan
based on EpicsApps.StepScan.

"""
import numpy as np

from larch import use_plugin_path
use_plugin_path('epics')

from stepscan import LarchStepScan
from positioner import Positioner
XAFS_K2E = 3.809980849311092

def etok(energy):  return np.sqrt(energy/XAFS_K2E)
def ktoe(k):       return k*k*XAFS_K2E


class XAFS_Scan(LarchStepScan):
    def __init__(self, label=None, energy_pv=None, read_pv=None,
                 extra_pvs=None,  e0=0, **kws):
        self.label = label
        self.e0 = e0
        self.energies = []
        self.regions = []
        LarchStepScan.__init__(self, **kws)
        self.dwelltime = []
        self.energy_pos = None
        self.set_energy_pv(energy_pv, read_pv=read_pv, extra_pvs=extra_pvs)

    def set_energy_pv(self, energy_pv, read_pv=None, extra_pvs=None):
        self.energy_pv = energy_pv
        self.read_pv = read_pv
        if energy_pv is not None:
            self.energy_pos = Positioner(energy_pv, label='Energy',
                                         extra_pvs=extra_pvs)
            self.positioners = []
            self.add_positioner(self.energy_pos)
        if read_pv is not None:
            self.add_counter(read_pv, label='Energy_readback')

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
        
        self.regions.append((start, stop, npts, relative, e0,
                             use_k, dtime, dtime_final, dtime_wt))

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
        self.dwelltime.extend(dt_arr)
        self.energy_pos.array = np.array(self.energies)

