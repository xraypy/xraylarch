#!/usr/bin/env python
"""
Plugin wrapping epicsscan DB
"""
import larch

from larch import ValidateLarchPlugin

try:
    import epics
    HAS_EPICS = True
except ImportError:
    HAS_EPICS = False

try:
    import epicsscan
    from epicsscan.scandb import ScanDB, InstrumentDB
    HAS_EPICSSCAN = True
except ImportError:
    HAS_EPICSSCAN = False

MODNAME = '_scan'
SCANDB_NAME = '%s._scandb' % MODNAME
INSTDB_NAME = '%s._instdb' % MODNAME

@ValidateLarchPlugin
def connect_scandb(dbname=None, server='postgresql',
                   _larch=None, **kwargs):
    if (_larch.symtable.has_symbol(SCANDB_NAME) and
        _larch.symtable.get_symbol(SCANDB_NAME) is not None):
        scandb = _larch.symtable.get_symbol(SCANDB_NAME)
    else:
        scandb = ScanDB(dbname=dbname, server=server, **kwargs)
        _larch.symtable.set_symbol(SCANDB_NAME, scandb)

    if (_larch.symtable.has_symbol(INSTDB_NAME) and
        _larch.symtable.get_symbol(INSTDB_NAME) is not None):
        instdb = _larch.symtable.get_symbol(INSTDB_NAME)
    else:
        instdb = InstrumentDB(scandb)
        _larch.symtable.set_symbol(INSTDB_NAME, instdb)
    return scandb

def initializeLarchPlugin(_larch=None):
    """initialize _scan"""
    if not _larch.symtable.has_group(MODNAME):
        g = Group()
        g.__doc__ = MODDOC
        _larch.symtable.set_symbol(MODNAME, g)

def registerLarchPlugin():
    symbols = {}
    if HAS_EPICSSCAN:
        symbols['connect_scandb'] = connect_scandb
    return (MODNAME, symbols)
