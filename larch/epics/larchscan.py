#!/usr/bin/env python
from __future__ import print_function

MODDOC = """
=== Epics Scanning Functions for Larch ===


This does not used the Epics SScan Record, and the scan is intended to run
as a python application, but many concepts from the Epics SScan Record are
borrowed.  Where appropriate, the difference will be noted here.

A Step Scan consists of the following objects:
   a list of Positioners
   a list of Triggers
   a list of Counters

Each Positioner will have a list (or numpy array) of position values
corresponding to the steps in the scan.  As there is a fixed number of
steps in the scan, the position list for each positioners must have the
same length -- the number of points in the scan.  Note that, unlike the
SScan Record, the list of points (not start, stop, step, npts) must be
given.  Also note that the number of positioners or number of points is not
limited.

A Trigger is simply an Epics PV that will start a particular detector,
usually by having 1 written to its field.  It is assumed that when the
Epics ca.put() to the trigger completes, the Counters associated with the
triggered detector will be ready to read.

A Counter is simple a PV whose value should be recorded at every step in
the scan.  Any PV can be a Counter, including waveform records.  For many
detector types, it is possible to build a specialized class that creates
many counters.

Because Triggers and Counters are closely associated with detectors, a
Detector is also defined, which simply contains a single Trigger and a list
of Counters, and will cover most real use cases.

In addition to the core components (Positioners, Triggers, Counters, Detectors),
a Step Scan contains the following objects:

   breakpoints   a list of scan indices at which to pause and write data
                 collected so far to disk.
   extra_pvs     a list of (description, PV) tuples that are recorded at
                 the beginning of scan, and at each breakpoint, to be
                 recorded to disk file as metadata.
   pre_scan()    method to run prior to scan.
   post_scan()   method to run after scan.
   at_break()    method to run at each breakpoint.

Note that Postioners and Detectors may add their own pieces into extra_pvs,
pre_scan(), post_scan(), and at_break().

With these concepts, a Step Scan ends up being a fairly simple loop, going
roughly (that is, skipping error checking) as:

   pos = <DEFINE POSITIONER LIST>
   det = <DEFINE DETECTOR LIST>
   run_pre_scan(pos, det)
   [p.move_to_start() for p in pos]
   record_extra_pvs(pos, det)
   for i in range(len(pos[0].array)):
       [p.move_to_pos(i) for p in pos]
       while not all([p.done for p in pos]):
           time.sleep(0.001)
       [trig.start() for trig in det.triggers]
       while not all([trig.done for trig in det.triggers]):
           time.sleep(0.001)
       [det.read() for det in det.counters]

       if i in breakpoints:
           write_data(pos, det)
           record_exrta_pvs(pos, det)
           run_at_break(pos, det)
   write_data(pos, det)
   run_post_scan(pos, det)

Note that multi-dimensional mesh scans over a rectangular grid is not
explicitly supported, but these can be easily emulated with the more
flexible mechanism of unlimited list of positions and breakpoints.
Non-mesh scans are also possible.

A step scan can have an Epics SScan Record or StepScan database associated
with it.  It will use these for PVs to post data at each point of the scan.
"""
import os, shutil
import time
from threading import Thread
import json
import numpy as np
import random

from datetime import timedelta

from larch import Group, ValidateLarchPlugin
from larch.utils import debugtime, fix_varname

try:
    from epics import PV, caget, caput, get_pv, poll
    HAS_EPICS = True
except ImportError:
    HAS_EPICS = False

try:
    import epicsscan
    from epicsscan import (Counter, Trigger, AreaDetector, get_detector,
                           ASCIIScanFile, Positioner)
    from epicsscan.scandb import ScanDB, InstrumentDB, ScanDBException, ScanDBAbort
    from epics.devices.struck import Struck

    HAS_EPICSSCAN = True
except ImportError:
    HAS_EPICSSCAN = False


SCANDB_NAME = '_scan._scandb'
INSTDB_NAME = '_scan._instdb'
_scandb = None
_instdb = None

def scan_from_db(scanname, filename='scan.001',  _larch=None):
    """
    get scan definition from ScanDB by name
    """
    global _scandb
    if _scandb is None:
        print('scan_from_db: need to connect to scandb!')
        return
    try:
        scan = _scandb.make_scan(scanname, larch=_larch)
        scan.filename = filename
    except ScanDBException:
        raise ScanDBException("no scan definition '%s' found" % scanname)
    return scan

def do_scan(scanname, filename='scan.001', nscans=1, comments='', _larch=None):
    """do_scan(scanname, filename='scan.001', nscans=1, comments='')

    execute a step scan as defined in Scan database

    Parameters
    ----------
    scanname:     string, name of scan
    filename:     string, name of output data file
    comments:     string, user comments for file
    nscans:       integer (default 1) number of repeats to make.

    Examples
    --------
      do_scan('cu_xafs', 'cu_sample1.001', nscans=3)

    Notes
    ------
      1. The filename will be incremented so that each scan uses a new filename.
    """
    global _scandb
    if _scandb is None:
        print('do_scan: need to connect to scandb!')
        return
    if nscans is not None:
        _scandb.set_info('nscans', nscans)

    scan = scan_from_db(scanname, filename=filename,  _larch=_larch)
    scan.comments = comments
    if scan.scantype == 'slew':
        return scan.run(filename=filename, comments=comments)
    else:
        scans_completed = 0
        nscans = int(_scandb.get_info('nscans'))
        abort  = _scandb.get_info('request_abort', as_bool=True)
        while (scans_completed  < nscans) and not abort:
            scan.run()
            scans_completed += 1
            nscans = int(_scandb.get_info('nscans'))
            abort  = _scandb.get_info('request_abort', as_bool=True)
        return scan

def get_dbinfo(key, default=None, as_int=False, as_bool=False,
               full_row=False, _larch=None, **kws):
    """get a value for a keyword in the scan info table,
    where most status information is kept.

    Arguments
    ---------
     key        name of data to look up
     default    (default None) value to return if key is not found
     as_int     (default False) convert to integer
     as_bool    (default False) convert to bool
     full_row   (default False) return full row, not just value

    Notes
    -----
     1.  if this key doesn't exist, it will be added with the default
         value and the default value will be returned.
     2.  the full row will include notes, create_time, modify_time

    """
    global _scandb
    if _scandb is None:
        print('get_dbinfo: need to connect to scandb!')
        return
    return _scandb.get_info(key, default=default, full_row=full_row,
                            as_int=as_int, as_bool=as_bool, **kws)

def set_dbinfo(key, value, notes=None, _larch=None, **kws):
    """
    set a value for a keyword in the scan info table.
    """
    global _scandb
    if _scandb is None:
        print('set_dbinfo: need to connect to scandb!')
        return
    return _scandb.set_info(key, value, notes=notes)

def connect_scandb(scandb=None, dbname=None, _larch=None, **kwargs):
    global _scandb, _instdb
    if _scandb is not None:
        return _scandb
    if scandb is None:
        scandb = ScanDB(dbname=dbname, **kwargs)

    if scandb is not None:
        _scandb = scandb

    if _larch is not None:
        _larch.symtable.set_symbol(SCANDB_NAME, _scandb)

    if _instdb is None:
        _instdb = InstrumentDB(_scandb)

        if _larch is not None:
            _larch.symtable.set_symbol(INSTDB_NAME, _instdb)
    return _scandb
