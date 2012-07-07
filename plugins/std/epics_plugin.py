#!/usr/bin/env python
"""
Use Epics Channel Access
"""
import sys
try:
    import epics
    HAS_PYEPICS = True
except:
    HAS_PYEPICS = False

def caget(pvname, _larch=None, **kws):
    if _larch is None or not HAS_PYEPICS: return
    return epics.caget(pvname, *args, **kws)

caget.__doc__ = epics.caget.__doc__


def caput(pvname, value, _larch=None, **kws):
    if _larch is None or not HAS_PYEPICS: return
    return epics.caput(pvname, value, **kws)

caput.__doc__ = epics.caput.__doc__

def PV(pvname, _larch=None, **kws):
    if _larch is None or not HAS_PYEPICS: return
    return epics.PV(pvname, **kws)

PV.__doc__ = epics.PV.__doc__


def registerLarchPlugin():
    plugins = {}
    if HAS_PYEPICS:
        plugins = {'PV': PV, 'caget': caget, 'caput': caput}
    return ('_io', plugins)
