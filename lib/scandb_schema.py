#!/usr/bin/env python
"""
SQLAlchemy wrapping of scan database

Main Class for full Database:  ScanDB
"""
import os
import time
from datetime import datetime

# from utils import backup_versions, save_backup

from sqlalchemy import MetaData, and_, create_engine, text, func,\
     Table, Column, ColumnDefault, Integer, Float, String, Text, DateTime, ForeignKey

from sqlalchemy.orm import sessionmaker,  mapper, clear_mappers, relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.pool import SingletonThreadPool

# needed for py2exe?
from sqlalchemy.dialects import sqlite, mysql, postgresql

## status states for commands
CMD_STATUS = ('requested', 'canceled', 'starting', 'running', 'aborting',
               'stopping', 'aborted', 'finished', 'unknown')

def make_engine(dbname, server='sqlite', user='', password='',
                host='', port=None):
    """create databse engine"""
    if server == 'sqlite':
        return create_engine('sqlite:///%s' % (dbname),
                             poolclass=SingletonThreadPool)
    elif server in ('mysql', 'postgresql'):
        if server == 'mysql':
            conn_str= 'mysql+mysqldb://%s:%s@%s:%i/%s'
            if port is None: port = 3306
        elif server == 'postgresql':
            conn_str= 'postgresql+psycopg2://%s:%s@%s:%i/%s'
            if port is None: port = 5432
        return create_engine(conn_str % (user, password, host, port, dbname))


def IntCol(name, **kws):
    return Column(name, Integer, **kws)

def StrCol(name, size=None, **kws):
    val = Text
    if size is not None:
        val = String(size)
    return Column(name, val, **kws)

def PointerCol(name, other=None, keyid='id', **kws):
    if other is None:
        other = name
    return Column("%s_%s" % (name, keyid), None,
                  ForeignKey('%s.%s' % (other, keyid)), **kws)

def NamedTable(tablename, metadata, keyid='id', nameid='name',
               name=True, notes=True, with_pv=False, cols=None):
    args  = [Column(keyid, Integer, primary_key=True)]
    if name:
        args.append(StrCol(nameid, size=512, nullable=False, unique=True))
    if notes:
        args.append(StrCol('notes'))
    if with_pv:
        args.append(StrCol('pvname', size=64))
    if cols is not None:
        args.extend(cols)
    return Table(tablename, metadata, *args)

class _BaseTable(object):
    "generic class to encapsulate SQLAlchemy table"
    def __repr__(self):
        name = self.__class__.__name__
        fields = ['%s' % getattr(self, 'name', 'UNNAMED')]
        return "<%s(%s)>" % (name, ', '.join(fields))

class Info(_BaseTable):
    "general information table (versions, etc)"
    name, value, modify_time = None, None, None

class Status(_BaseTable):
    "status table"
    name, notes = None, None

class Positioners(_BaseTable):
    "positioners table"
    name, notes, pvname = None, None, None

class Counters(_BaseTable):
    "counters table"
    name, notes, pvname = None, None, None

class Detectors(_BaseTable):
    "detectors table"
    name, notes, pvname, kind, options = [None]*5

class ScanDefs(_BaseTable):
    "scandefs table"
    name, notes, text, modify_time, last_used_time = [None]*5

class MonitorPVs(_BaseTable):
    "monitor PV table"
    name, notes = None, None

class MonitorValues(_BaseTable):
    "monitor PV Values table"
    id, time, value = None, None, None

class Macros(_BaseTable):
    "macros table"
    name, notes, arguments, text, output = None, None, None, None, None

class Commands(_BaseTable):
    "commands table"
    command, notes, arguments = None, None, None
    status, status_name = None, None
    scandef, scandefs_id = None, None
    request_time, start_time, complete_time = None, None, None
    output_value, output_file = None, None

class ScanData(_BaseTable):
    notes, output_file, modify_time = None, None, None
    pos, det, breakpoints = None, None, None


def create_scandb(dbname, server='sqlite', **kws):
    """Create a ScanDB:

    arguments:
    ---------
    dbname    name of database (filename for sqlite server)

    options:
    --------
    server    type of database server ([sqlite], mysql, postgresql)
    host      host serving database   (mysql,postgresql only)
    port      port number for database (mysql,postgresql only)
    user      user name for database (mysql,postgresql only)
    password  password for database (mysql,postgresql only)
    """

    engine  = make_engine(dbname, server, **kws)
    metadata =  MetaData(engine)
    info = Table('info', metadata,
                 Column('name', Text, primary_key=True, unique=True),
                 StrCol('value'),
                 Column('modify_time', DateTime),
                 Column('create_time', DateTime, default=datetime.now))

    status = NamedTable('status', metadata)
    pos    = NamedTable('positioners', metadata, with_pv=True)
    cnts   = NamedTable('counters', metadata, with_pv=True)
    det    = NamedTable('detectors', metadata, with_pv=True,
                        cols=[StrCol('kind',   size=64),
                              StrCol('options', size=1024)])
    scans = NamedTable('scandefs', metadata,
                       cols=[StrCol('text', size=2048),
                             Column('modify_time', DateTime),
                             Column('last_used_time', DateTime)])


    macros = NamedTable('macros', metadata,
                        cols=[StrCol('arguments'),
                              StrCol('text'),
                              StrCol('output')])

    cmds = NamedTable('commands', metadata, name=False,
                      cols=[StrCol('command'),
                            StrCol('arguments'),
                            PointerCol('status'),
                            PointerCol('scandefs'),
                            Column('request_time', DateTime,
                                   default=datetime.now),
                            Column('start_time',    DateTime),
                            Column('complete_time', DateTime),
                            StrCol('output_value'),
                            StrCol('output_file')])

    monpvs  = NamedTable('monitorpvs', metadata)
    monvals = Table('monitorvalues', metadata,
                    Column('id', Integer, primary_key=True),
                    PointerCol('monitorpvs'),
                    StrCol('value'),
                    Column('time', DateTime))


    scandat = NamedTable('scandata', metadata, name=False,
                         cols=[PointerCol('scandefs'),
                               StrCol('output_file'),
                               StrCol('pos'),
                               StrCol('det'),
                               StrCol('breakpoints'),
                               Column('modify_time', DateTime)])

    metadata.create_all()
    session = sessionmaker(bind=engine)()

    # add some initial data:
    scans.insert().execute(name='NULL', text='')

    for name in CMD_STATUS:
        status.insert().execute(name=name)

    for name, value in (("version", "1.0"),
                        ("user_name", ""),
                        ("experiment_id",  ""),
                        ("user_folder",    "")):
        info.insert().execute(name=name, value=value)
    session.commit()

def map_scandb(metadata):
    """ set up mapping of SQL metadata and classes
    returns two dictionaries, tables and classes
    each with entries
    tables:    {tablename: table instance}
    classes:   {tablename: table class}

    """
    tables = metadata.tables
    classes = {}
    try:
        clear_mappers()
    except:
        pass

    for t_cls in (Info, Positioners, Counters,
                  Detectors, ScanDefs, Commands,
                  ScanData, Macros, Status,
                  MonitorPVs, MonitorValues):
        name = t_cls.__name__.lower()
        # props = {}
        #if name == 'commands':
        #    props = {'status_name': relationship(Status),
        #             'scandef': relationship(ScanDefs, backref='scan')}
        #elif name == 'scandata':
        #    props = {'scandef': relationship(ScanDefs, backref='scanname')}
        # mapper(t_cls, tables[name], properties=props)
        mapper(t_cls, tables[name])
        classes[name] = t_cls

    # set onupdate and default constraints for several datetime columns
    # note use of ColumnDefault to wrap onpudate/default func
    fnow = ColumnDefault(datetime.now)
    for tname, cname in (('info',  'modify_time'),
                         ('scandefs', 'modify_time'),
                         ('scandata', 'modify_time')):
        tables[tname].columns[cname].onupdate =  fnow

    for tname, cname in (('info', 'create_time'),
                         ('commands', 'request_time'),
                         ('monitorvalues', 'time')):
        tables[tname].columns[cname].default = fnow
    return tables, classes

