#!/usr/bin/env python
"""
Use Epics Channel Access
"""
plugins = {}
try:
    import epics
    def caget(pvname, _larch=None, **kws):
        return epics.caget(pvname, **kws)
    def caput(pvname, value, _larch=None, **kws):
        return epics.caput(pvname, value, **kws)
    def PV(pvname, _larch=None, **kws):
        return epics.PV(pvname, **kws)

    caget.__doc__ = epics.caget.__doc__
    caput.__doc__ = epics.caput.__doc__
    PV.__doc__ = epics.PV.__doc__
    
    plugins = {'PV': PV, 'caget': caget, 'caput': caput}
    
except:
    pass

def registerLarchPlugin():
    return ('_io', plugins)
    
