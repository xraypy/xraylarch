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
CMD_STATUS = ('unknown', 'requested', 'canceled', 'starting', 'running',
               'aborting', 'stopping', 'aborted', 'finished')

PV_TYPES = (('numeric', 'Numeric Value'),   ('enum',  'Enumeration Value'),
           ('string',  'String Value'),    ('motor', 'Motor Value'))

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
    keyname, value, modify_time = None, None, None

class Status(_BaseTable):
    "status table"
    name, notes = None, None

class ScanPositioners(_BaseTable):
    "positioners table"
    name, notes, pvname = None, None, None

class ScanCounters(_BaseTable):
    "counters table"
    name, notes, pvname = None, None, None

class ScanDetectors(_BaseTable):
    "detectors table"
    name, notes, pvname, kind, options = [None]*5

class ScanDefs(_BaseTable):
    "scandefs table"
    name, notes, text, modify_time, last_used_time = [None]*5

class PVTypes(_BaseTable):
    "pvtype table"
    name, notes = None, None

class PVs(_BaseTable):
    "pv table"
    name, notes = None, None
    is_monitor = 0

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
    request_time, start_time, modify_time = None, None, None
    output_value, output_file = None, None

    def __repr__(self):
        name = self.__class__.__name__
        fields = ['%s' % getattr(self, 'command', 'Unknown')]
        return "<%s(%s)>" % (name, ', '.join(fields))

class ScanData(_BaseTable):
    notes, output_file, modify_time = None, None, None
    pos, det, breakpoints = None, None, None

class Instruments(_BaseTable):
    "instrument table"
    name, notes = None, None

class Positions(_BaseTable):
    "position table"
    pvs, instrument, instrument_id, date, name, notes = None, None, None, None, None, None

class Position_PV(_BaseTable):
    "position-pv join table"
    name, notes, pv, value = None, None, None, None
    def __repr__(self):
        name = self.__class__.__name__
        fields = ['%s=%s' % (getattr(self, 'pv', '?'),
                             getattr(self, 'value', '?'))]
        return "<%s(%s)>" % (name, ', '.join(fields))

class Instrument_PV(_BaseTable):
    "intruemnt-pv join table"
    name, id, instrument, pv, display_order = None, None, None, None, None
    def __repr__(self):
        name = self.__class__.__name__
        fields = ['%s/%s' % (getattr(getattr(self, 'instrument', '?'),'name','?'),
                             getattr(getattr(self, 'pv', '?'), 'name', '?'))]
        return "<%s(%s)>" % (name, ', '.join(fields))

class Instrument_Precommand(_BaseTable):
    "instrument precommand table"
    name, notes = None, None

class Instrument_Postcommand(_BaseTable):
    "instrument postcommand table"
    name, notes = None, None

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
                 Column('keyname', Text, primary_key=True, unique=True),
                 StrCol('value'),
                 Column('modify_time', DateTime),
                 Column('create_time', DateTime, default=datetime.now))

    status = NamedTable('status', metadata)
    pos    = NamedTable('scanpositioners', metadata, with_pv=True)
    cnts   = NamedTable('scancounters', metadata, with_pv=True)
    det    = NamedTable('scandetectors', metadata, with_pv=True,
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
                            PointerCol('status', default=1),
                            PointerCol('scandefs'),
                            Column('request_time', DateTime,
                                   default=datetime.now),
                            Column('start_time',    DateTime),
                            Column('modify_time',   DateTime),
                            StrCol('output_value'),
                            StrCol('output_file')])

    pvtypes = NamedTable('pvtypes', metadata)
    pv      = NamedTable('pvs', metadata,
                         cols=[PointerCol('pvtypes'),
                               Column('is_monitor', Integer, default=0)])

    monvals = Table('monitorvalues', metadata,
                    Column('id', Integer, primary_key=True),
                    PointerCol('pvs'),
                    StrCol('value'),
                    Column('time', DateTime))

    scandat = NamedTable('scandata', metadata, name=False,
                         cols=[PointerCol('scandefs'),
                               StrCol('output_file', default=''),
                               StrCol('pos'),
                               StrCol('det'),
                               StrCol('breakpoints', default=''),
                               Column('modify_time', DateTime)])

    instrument = NamedTable('instruments', metadata,
                            cols=[Column('show', Integer, default=1),
                                  Column('display_order', Integer, default=0)])

    position  = NamedTable('positions', metadata,
                           cols=[Column('modify_time', DateTime),
                                 PointerCol('instruments')])

    instrument_precommand = NamedTable('instrument_precommand', metadata,
                                       cols=[Column('exec_order', Integer),
                                             PointerCol('commands'),
                                             PointerCol('instruments')])

    instrument_postcommand = NamedTable('instrument_postcommand', metadata,
                                        cols=[Column('exec_order', Integer),
                                              PointerCol('commands'),
                                              PointerCol('instruments')])

    instrument_pv = Table('instrument_pv', metadata,
                          Column('id', Integer, primary_key=True),
                          PointerCol('instruments'),
                          PointerCol('pvs'),
                          Column('display_order', Integer, default=0))


    position_pv = Table('position_pv', metadata,
                        Column('id', Integer, primary_key=True),
                        StrCol('notes'),
                        PointerCol('positions'),
                        PointerCol('pvs'),
                        StrCol('value'))

    metadata.create_all()
    session = sessionmaker(bind=engine)()

    # add some initial data:
    scans.insert().execute(name='NULL', text='')

    for name in CMD_STATUS:
        status.insert().execute(name=name)

    for name, notes in PV_TYPES:
        pvtypes.insert().execute(name=name, notes=notes)

    for keyname, value in (("version", "1.0"),
                        ("user_name", ""),
                        ("experiment_id",  ""),
                        ("user_folder",    "")):
        info.insert().execute(keyname=keyname, value=value)
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

    for cls in (Info, Status, PVTypes, PVs, MonitorValues, Macros, Commands,
                ScanData, ScanPositioners, ScanCounters, ScanDetectors, ScanDefs,
                Instruments, Positions, Position_PV, Instrument_PV,
                Instrument_Precommand, Instrument_Postcommand):

        name = cls.__name__.lower()
        props = {}
        if name == 'commands':
            props = {'status': relationship(Status),
                     'scandefs': relationship(ScanDefs)}
        elif name == 'scandata':
            props = {'scandefs': relationship(ScanDefs)}
        elif name == 'monitorvalues':
            props = {'pv': relationship(PVs)}
        elif name == 'pvs':
            props = {'pvtype': relationship(PVTypes)}
        elif name == 'instruments':
            properties={'pvs': relationship(PVs,
                                            backref='instruments',
                                            secondary=tables['instrument_pv'])}

        mapper(cls, tables[name], properties=props)
        classes[name] = cls

    mapping_Settings = """
        props = {}

        #if name == 'commands':
        #    props = {'status_name': relationship(Status),
        #             'scandef': relationship(ScanDefs, backref='scan')}
        #elif name == 'scandata':
        #    props = {'scandef': relationship(ScanDefs, backref='scanname')}
        # mapper(t_cls, tables[name], properties=props)

        mapper(Instrument, tables['instrument'],
               properties={'pvs': relationship(PV,
                                               backref='instrument',
                                    secondary=tables['instrument_pv'])})

        mapper(PVType,   tables['pvtype'],
               properties={'pv':
                           relationship(PV, backref='pvtype')})

        mapper(Position, tables['position'],
               properties={'instrument': relationship(Instrument,
                                                      backref='positions'),
                           'pvs': relationship(Position_PV) })

        mapper(Instrument_PV, tables['instrument_pv'],
               properties={'pv':relationship(PV),
                           'instrument':relationship(Instrument)})

        mapper(Position_PV, tables['position_pv'],
               properties={'pv':relationship(PV)})

        mapper(Instrument_Precommand,  tables['instrument_precommand'],
               properties={'instrument': relationship(Instrument,
                                                      backref='precommands'),
                           'command':   relationship(Command,
                                                     backref='inst_precoms')})
        mapper(Instrument_Postcommand,   tables['instrument_postcommand'],
               properties={'instrument': relationship(Instrument,
                                                      backref='postcommands'),
                           'command':   relationship(Command,
                                                     backref='inst_postcoms')})
    """

    # set onupdate and default constraints for several datetime columns
    # note use of ColumnDefault to wrap onpudate/default func
    fnow = ColumnDefault(datetime.now)
    for tname, cname in (('info',  'modify_time'),
                         ('commands', 'modify_time'),
                         ('positions', 'modify_time'),
                         ('scandefs', 'modify_time'),
                         ('scandata', 'modify_time')):
        tables[tname].columns[cname].onupdate =  fnow

    for tname, cname in (('info', 'create_time'),
                         ('commands', 'request_time'),
                         ('monitorvalues', 'time')):
        tables[tname].columns[cname].default = fnow
    return tables, classes

