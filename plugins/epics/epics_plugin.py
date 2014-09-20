#!/usr/bin/env python
"""
Use Epics Channel Access
"""

MODDOC = '''
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
'''

plugins = {}
try:
    import epics
    def caget(pvname, _larch=None, **kws):
        return epics.caget(pvname, **kws)
    def caput(pvname, value, _larch=None, **kws):
        return epics.caput(pvname, value, **kws)
    def cainfo(pvname, print_out=True, _larch=None):
        return epics.cainfo(pvname, print_out=print_out)
    def PV(pvname, _larch=None, **kws):
        return epics.PV(pvname, **kws)

    caget.__doc__ = epics.caget.__doc__
    caput.__doc__ = epics.caput.__doc__
    cainfo.__doc__ = epics.cainfo.__doc__
    PV.__doc__ = epics.PV.__doc__


    def pv_units(pv, default):
        try:
            units = pv.units
        except:
            units = ''
        if units in (None, ''):
            units = default
        return units

    def pv_fullname(name):
        """ make sure Epics PV name either ends with .VAL or .SOMETHING!"""
        if  '.' in name:
            return name
        return "%s.VAL" % name

    plugins = {'PV': PV, 'caget': caget, 'caput': caput,
               'pv_units': pv_units, 'pv_fullname': pv_fullname}

except:
    pass

def registerLarchPlugin():
    return ('_epics', plugins)

