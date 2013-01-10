#!/usr/bin/env python
"""
 provides make_newdb() function to create an empty ScanDatabase

"""
import sys
import os

from datetime import datetime

from sqlalchemy.orm import sessionmaker, create_session
from sqlalchemy import MetaData, create_engine, \
     Table, Column, Integer, Float, String, Text, DateTime, ForeignKey

from utils import dumpsql, backup_versions

def PointerCol(name, other=None, keyid='id', **kws):
    if other is None:
        other = name
    return Column("%s_%s" % (name, keyid), None,
                  ForeignKey('%s.%s' % (other, keyid), **kws))
    
def StrCol(name, size=None, **kws):
    if size is None:
        return Column(name, Text, **kws)
    else:
        return Column(name, String(size), **kws)

def NamedTable(tablename, metadata, keyid='id', nameid='name',
               name=True, notes=True, attributes=True, cols=None):
    args  = [Column(keyid, Integer, primary_key=True)]
    if name:
        args.append(StrCol(nameid, nullable=False, unique=True))
    if notes:
        args.append(StrCol('notes'))
    if attributes:
        args.append(StrCol('attributes'))
    if cols is not None:
        args.extend(cols)
    return Table(tablename, metadata, *args)

class InitialData:
    info    = [["version", "1.1"],
               ["verify_erase", "1"],
               ["verify_move",   "1"],
               ["verify_overwrite",  "1"],
               ["epics_prefix",   ""],               
               ["create_date", '<now>'],
               ["modify_date", '<now>']]

    status = ['requested', 'canceled', 'starting', 'running', 'aborting',
              'stopping', 'aborted', 'finished', 'unknown', ]
    

def  make_newdb(dbname, server= 'sqlite', user='', password='',
                host='localhost'):
    engine  = create_engine('%s:///%s' % (server, dbname))
    metadata =  MetaData(engine)
    
    info = Table('info', metadata,
                     Column('key', Text, primary_key=True, unique=True), 
                     StrCol('value'))

    status = NamedTable('status', metadata)
    pv = NamedTable('pv', metadata)

    cmds = NamedTable('commands', metadata,
                          cols=[StrCol('command'),
                                StrCol('arguments'),
                                PointerCol('status'),
                                StrCol('output_value'),
                                StrCol('output_file')])

    monitored_pvs = NamedTable('monitored_pvs', metadata,
                               cols=[Column('date', DateTime),
                                     PointerCol('pv'),
                                     StrCol('value')])
    
    metadata.create_all()
    session = sessionmaker(bind=engine)()

    for name in InitialData.status:
        status.insert().execute(name=name)

    now = datetime.isoformat(datetime.now())

    for key, value in InitialData.info:
        if value == '<now>':
            value = now
        info.insert().execute(key=key, value=value)

    for key, value in InitialData.info:
        if value == '<now>':
            value = now
        info.insert().execute(key=key, value=value)


    session.commit()    

    
if __name__ == '__main__':
    dbname = 'ScanDb.sdb'
    backup_versions(dbname)
    make_newdb(dbname)
    print '''%s  created and initialized.''' % dbname
    dumpsql(dbname)
