#!/usr/bin/env python
"""
Use Epics Channel Access
"""

MODDOC = """
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

caget_doc = """caget(pvname, as_string=False, use_numpy=True, timeout=None)

    get value for Epics PV

    Parameters
    ----------
      pvname:    string name of PV
      as_string: True/False(default) return string representation
      use_numpy: True(default)/False return numpy array for array PVs
      count:     max count to return for array PVs
      timeout:   time in seconds to wait for slow/unconnected PV

    Returns
    -------
       PV's value, can by any type.

    Examples
    --------
       x = caget('XXX.VAL')
       x = caget('XXX.VAL', as_string=True)

    Notes
    ------
      1. The default timeout is 0.5 sec for scalar PVs.
%s
"""

caput_doc = """caput(pvname, value, wait=False, timeout=60)

    put value for Epics PV

    Parameters
    ----------
      pvname:    string name of PV
      value:     value to put.
      wait:      True/False(default) whether to wait for processing
                 to complete before returning.
      timeout:   time in seconds to wait for completion

    Examples
    --------
       caput('XXX.VAL', 22)
       caput('XXX.VAL', 0.0, wait=True)

    Returns
    -------
       None

    Notes
    -----
     1.  waiting may take a long time, as it waits for all processing
         to complete (motor move, detector acquire to finish, etc).
%s
"""

cainfo_doc = """cainfo(pvname, print_out=True)

    return printable information about pv

    Parameters
    ----------
      pvname:    string name of PV
      print_out: True(default)/False whether to print info to standard out
                 or return sring with info

    Returns
    -------
       None or string with info paragraph

    Examples
    --------
      cainfo('xx.VAL')
%s    
   """

pv_doc = """PV(pvname)

    create an Epics PV (Process Variable) object

    Parameters
    ----------
      pvname:    string name of PV

    Examples
    --------
      mypv = PV('xx.VAL')
      mypv.get()
      mypv.put(value)
      print mypv.pvname, mypv.count, mypv.type

    Notes
    -----
      A PV has many attributes and methods.  Consult the documentation.
%s
"""


def nullfcn(*args, **kwargs): 
    return None

def caget(pvname, _larch=None, **kws):
    return nullfcn(pvname, **kws)

def caput(pvname, value, _larch=None, **kws):
    return nullfcn(pvname, value, **kws)

def cainfo(pvname, print_out=True, _larch=None):
    return nullfcn(pvname, print_out=print_out)

def PV(pvname, _larch=None, **kws):
    return nullfcn(pvname, **kws)

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


msg = """
    !!! WARNING: !!!
    ---------------- 
       epics not installed!  Function will return None!
"""

try:
    import epics
    msg = ''
except:
    pass
else:
    def caget(pvname, _larch=None, **kws):
        return epics.caget(pvname, **kws)

    def caput(pvname, value, _larch=None, **kws):
        return epics.caput(pvname, value, **kws)

    def cainfo(pvname, print_out=True, _larch=None):
        return epics.cainfo(pvname, print_out=print_out)

    def PV(pvname, _larch=None, **kws):
        return epics.get_pv(pvname, **kws)

caget.__doc__ = caget_doc % msg
caput.__doc__ = caput_doc % msg
cainfo.__doc__ = cainfo_doc % msg
PV.__doc__ = pv_doc % msg

def initializeLarchPlugin(_larch=None):
    """initialize _epics"""
    _larch.symtable._epics.__doc__ = MODDOC

def registerLarchPlugin():
    return ('_epics', {'PV': PV, 
                       'caget': caget, 
                       'caput': caput, 
                       'cainfo': cainfo, 
                       'pv_units': pv_units,
                       'pv_fullname': pv_fullname})

