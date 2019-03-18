#!/usr/bin/env python
"""
Use Epics Channel Access
"""

HAS_PYEPICS = False

try:
    import epics
    HAS_PYEPICS = True
except ImportError:
    HAS_PYEPICS = False

from . import larchscan

def pv_fullname(name):
    """ make sure an Epics PV name ends with .VAL or .SOMETHING!

    Parameters
    ----------
       pvname:   name of PV

    Returns
    -------
       string with full PV name

    """
    name = str(name)
    if '.' not in name:
        name = "%s.VAL" % name
    return name

def pv_units(pv, default=''):
    """get units for pv object, with optional default value

    Parameters
    ----------
       pv:       pv object (created by PV())
       default:  string value for default units

    Returns
    -------
       string with units

    """
    try:
        units = pv.units
    except:
        units = ''
    if units in (None, ''):
        units = default
    return units



def nullfcn(*args,  **kws):
    "pyepics is not installed"
    return None

caget = caput = cainfo = PV = nullfcn
__DOC__ = "pyepics is not installed"
epics_exports = {}
scan_exports = {}

_larch_name = '_epics'
_larch_builtins = {'_epics': {}}


if HAS_PYEPICS:
    from .xrf_detectors import Epics_MultiXMAP, Epics_Xspress3
    from .xrfcontrol import EpicsXRFApp

    caget = epics.caget
    caput = epics.caput
    cainfo = epics.cainfo
    PV = epics.get_pv
    __DOC__ = """
Functions for Epics Channel Access, using pyepics interface.
For further details, consult the pyepics documentation

  Functions
  -------------
  caget(pvname, as_string=False, count=None, timeout=None)
           get and return value for an Epics Process Variable
           with options to ensure return value is a string,
           to limit the count for array values, or to specify
           a maximum time to wait for a value.
  caput(pvname, value, wait=False, timeout=60)
           put a value to an Epics Process Variable, optionally
           waiting to return until record is fully processed,
           with a timeout value.
  cainfo(pvname, print_out=True)
           print out information about Process Variable. with
           print_out = False, returns string of information.
  PV(pvname)
           create a Process Variable object with get()/put()
           and several other methods.
  pv_units(pvname)
           return units for PV
  pv_fullname(pvname)
           return fullname (that is, including '.VAL' if needed) for PV
"""

    _larch_builtins = {'_epics': dict(PV=PV, caget=caget, caput=caput,
                                      cainifo=cainfo, pv_units=pv_units,
                                      pv_fullname=pv_fullname)}

    if larchscan.HAS_EPICSSCAN:
        _larch_builtins['_scan'] = dict(scan_from_db=larchscan.scan_from_db,
                                        connect_scandb=larchscan.connect_scandb,
                                        do_scan=larchscan.do_scan,
                                        do_slewscan=larchscan.do_scan,
                                        get_dbinfo=larchscan.get_dbinfo,
                                        set_dbinfo=larchscan.set_dbinfo)
