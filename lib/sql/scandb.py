#!/usr/bin/env python
"""
SQLAlchemy wrapping of scan database

Main Class for full Database:  ScanDB
"""
import os
import json
import time
from socket import gethostname

from datetime import datetime

# from utils import backup_versions, save_backup

from sqlalchemy import MetaData, and_, create_engine, \
     Table, Column, Integer, Float, String, Text, DateTime, ForeignKey

from sqlalchemy.orm import sessionmaker,  mapper, clear_mappers, relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import  NoResultFound
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

def isScanDB(dbname, server='sqlite', **kws):
    """test if a file is a valid scan database:
    must be a sqlite db file, with tables named
       'postioners', 'detectors', and 'scans'
    """
    _tables = ('info', 'positioners', 'detectors', 'scans')
    result = False
    try:
        engine = make_engine(dbname, server=server, **kws)
        meta = MetaData(engine)
        meta.reflect()
        if all([t in meta.tables for t in _tables]):
            keys = [row.keyname for row in
                    meta.tables['info'].select().execute().fetchall()]
            result = 'version' in keys and 'create_date' in keys
    except:
        pass
    return result

def json_encode(val):
    "simple wrapper around json.dumps"
    if val is None or isinstance(val, (str, unicode)):
        return val
    return  json.dumps(val)

def isotime2datetime(isotime):
    "convert isotime string to datetime object"
    sdate, stime = isotime.replace('T', ' ').split(' ')
    syear, smon, sday = [int(x) for x in sdate.split('-')]
    sfrac = '0'
    if '.' in stime:
        stime, sfrac = stime.split('.')
    shour, smin, ssec  = [int(x) for x in stime.split(':')]
    susec = int(1e6*float('.%s' % sfrac))
    return datetime(syear, smon, sday, shour, smin, ssec, susec)


class ScanDBException(Exception):
    """DB Access Exception: General Errors"""
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg
    def __str__(self):
        return self.msg

def None_or_one(val, msg='Expected 1 or None result'):
    """expect result (as from query.all() to return
    either None or exactly one result
    """
    if len(val) == 1:
        return val[0]
    elif len(val) == 0:
        return None
    else:
        raise ScanDBException(msg)

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
                  ForeignKey('%s.%s' % (other, keyid), **kws))

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

def make_newdb(dbname, server='sqlite', **kws):
    engine  = make_engine(dbname, server, **kws)
    metadata =  MetaData(engine)
    info = Table('info', metadata,
                 Column('key', Text, primary_key=True, unique=True),
                 StrCol('value'))

    status = NamedTable('status', metadata)
    pos    = NamedTable('positioners', metadata, with_pv=True)
    cnts   = NamedTable('counters', metadata, with_pv=True)
    det    = NamedTable('detectors', metadata, with_pv=True,
                        cols=[StrCol('kind',   size=64),
                              StrCol('options', size=1024)])
    scans = NamedTable('scandefs', metadata,
                       cols=[StrCol('text', size=2048),
                             Column('time_last_used', DateTime)])

    macros = NamedTable('macros', metadata,
                        cols=[StrCol('arguments'),
                              StrCol('text'),
                              StrCol('output')])

    cmds = NamedTable('commands', metadata, name=False,
                      cols=[StrCol('command'),
                            StrCol('arguments'),
                            PointerCol('status'),
                            PointerCol('scandefs'),
                            Column('request_time', DateTime),
                            Column('start_time', DateTime),
                            Column('complete_time', DateTime),
                            StrCol('output_value'),
                            StrCol('output_file')])

    monpvs = NamedTable('monitor_pvs', metadata)
    monvals = NamedTable('monitor_values', metadata,
                         cols=[Column('date', DateTime),
                               PointerCol('monitor_pvs'),
                               StrCol('value')])
    metadata.create_all()
    session = sessionmaker(bind=engine)()

    # add some initial data:
    scans.insert().execute(name='NULL', text='')

    for name in CMD_STATUS:
        status.insert().execute(name=name)

    NOW = datetime.isoformat(datetime.now())
    for key, value in (("version", "1.0"),
                       ("user_name", ""),
                       ("experiment_id",  ""),
                       ("user_folder",    ""),
                       ("create_date", '<now>'),
                       ("modify_date", '<now>')):
        if value == '<now>':
            value = NOW
        info.insert().execute(key=key, value=value)
    session.commit()

class _BaseTable(object):
    "generic class to encapsulate SQLAlchemy table"
    def __repr__(self):
        name = self.__class__.__name__
        fields = ['%s' % getattr(self, 'name', 'UNNAMED')]
        return "<%s(%s)>" % (name, ', '.join(fields))

class InfoTable(_BaseTable):
    "general information table (versions, etc)"
    keyname, value = None, None
    def __repr__(self):
        name = self.__class__.__name__
        fields = ['%s=%s' % (getattr(self, 'key', '?'),
                             getattr(self, 'value', '?'))]
        return "<%s(%s)>" % (name, ', '.join(fields))

class StatusTable(_BaseTable):
    "status table"
    name, notes = None, None

class PositionersTable(_BaseTable):
    "positioners table"
    name, notes, pvname = None, None, None

class CountersTable(_BaseTable):
    "counters table"
    name, notes, pvname = None, None, None

class DetectorsTable(_BaseTable):
    "detectors table"
    name, notes, pvname, kind, options = None, None, None, None, None

class ScanDefsTable(_BaseTable):
    "scandefs table"
    name, notes, text, time_last_used = None, None, None, None

class MonitorPVsTable(_BaseTable):
    "monitor PV table"
    name, notes = None, None

class MonitorValuesTable(_BaseTable):
    "monitor PV Values table"
    name, notes, date, = None, None, None
    monitor_pvs, monitor_pvs_id = None, None

class MacrosTable(_BaseTable):
    "macros table"
    name, notes, arguments, text, output = None, None, None, None, None

class CommandsTable(_BaseTable):
    "commands table"
    command, notes, arguments = None, None, None
    status, scandefs = None, None
    status_id, scandefs_id = None, None
    request_time, start_time, complete_time = None, None, None
    output_value, output_file = None, None

class ScanDB(object):
    "interface to Scans Database"
    def __init__(self, server='sqlite', dbname=None):
        self.dbname = dbname
        self.server = server
        self.tables = None
        self.engine = None
        self.session = None
        self.conn    = None
        self.metadata = None
        self.pvs = {}
        self.restoring_pvs = []
        if dbname is not None or server=='mysql':
            self.connect(dbname, server=server)

    def create_newdb(self, dbname, connect=False):
        "create a new, empty database"
        make_newdb(dbname)
        if connect:
            time.sleep(0.5)
            self.connect(dbname, backup=False)

    def connect(self, dbname, server='sqlite', backup=True):
        "connect to an existing database"
        if server == 'sqlite':
            if not os.path.exists(dbname):
                raise IOError("Database '%s' not found!" % dbname)

            if not isScanDB(dbname):
                raise ValueError("'%s' is not an Scans file!" % dbname)

            if backup:
                save_backup(dbname)
        self.dbname = dbname
        self.engine = make_engine(dbname, server)
        self.conn = self.engine.connect()
        self.session = sessionmaker(bind=self.engine)()

        self.metadata =  MetaData(self.engine)
        self.metadata.reflect()
        tables = self.tables = self.metadata.tables

        try:
            clear_mappers()
        except:
            pass
        mapper(ScansTable,      tables['scans'])
        mapper(InfoTable,       tables['info'])
        mapper(PostionersTable, table['positioners'])
        mapper(CountersTable,   table['counters'])
        mapper(DetectorsTable,  table['detectors'])
        mapper(ScanDefsTable,   table['scandefs'])
        mapper(CommandsTable,   table['commands'])
        mapper(MacrosTable,     table['macros'])
        mapper(MonitorPVsTable, table['monitor_pvs'])
        mapper(MonitorValuesTable, table['monitor_values'])

    def commit(self):
        "commit session state"
        self.set_info('modify_date', datetime.isoformat(datetime.now()))
        return self.session.commit()

    def close(self):
        "close session"
        self.set_hostpid(clear=True)
        self.session.commit()
        self.session.flush()
        self.session.close()

    def query(self, *args, **kws):
        "generic query"
        return self.session.query(*args, **kws)

    def get_info(self, keyname, default=None):
        """get a value from a key in the info table"""
        errmsg = "get_info expected 1 or None value for keyname='%s'"
        out = self.query(InfoTable).filter(InfoTable.keyname==keyname).all()
        thisrow = None_or_one(out, errmsg % keyname)
        if thisrow is None:
            return default
        return thisrow.value

    def set_info(self, keyname, value):
        """set key / value in the info table"""
        table = self.tables['info']
        vals  = self.query(table).filter(InfoTable.keyname==keyname).all()
        if len(vals) < 1:
            table.insert().execute(keyname=keyname, value=value)
        else:
            table.update(whereclause="keyname='%s'" % keyname).execute(value=value)

    def set_hostpid(self, clear=False):
        """set hostname and process ID, as on intial set up"""
        name, pid = '', '0'
        if not clear:
            name, pid = gethostname(), str(os.getpid())
        self.set_info('host_name', name)
        self.set_info('process_id', pid)

    def check_hostpid(self):
        """check whether hostname and process ID match current config"""
        if self.server != 'sqlite':
            return True
        db_host_name = self.get_info('host_name', default='')
        db_process_id  = self.get_info('process_id', default='0')
        return ((db_host_name == '' and db_process_id == '0') or
                (db_host_name == gethostname() and
                 db_process_id == str(os.getpid())))

    def __addRow(self, table, argnames, argvals, **kws):
        """add generic row"""
        me = table() #
        for name, val in zip(argnames, argvals):
            setattr(me, name, val)
        for key, val in kws.items():
            if key == 'attributes':
                val = json_encode(val)
            setattr(me, key, val)
        try:
            self.session.add(me)
            # self.session.commit()
        except IntegrityError, msg:
            self.session.rollback()
            raise Warning('Could not add data to table %s\n%s' % (table, msg))

        return me


    def _get_foreign_keyid(self, table, value, name='name',
                           keyid='id', default=None):
        """generalized lookup for foreign key
arguments
    table: a valid table class, as mapped by mapper.
    value: can be one of the following
         table instance:  keyid is returned
         string:          'name' attribute (or set which attribute with 'name' arg)
            a valid id
            """
        if isinstance(value, table):
            return getattr(table, keyid)
        else:
            if isinstance(value, (str, unicode)):
                xfilter = getattr(table, name)
            elif isinstance(value, int):
                xfilter = getattr(table, keyid)
            else:
                return default
            try:
                query = self.query(table).filter(
                    xfilter==value)
                return getattr(query.one(), keyid)
            except (IntegrityError, NoResultFound):
                return default

        return default

    def get_all_scans(self):
        """return list of scans
        """
        return [m for m in self.query(ScansTable)]

    def get_scan(self, name):
        """return scan by name
        """
        if isinstance(name, ScansTable):
            return name
        out = self.query(ScansTable).filter(ScansTable.name==name).all()
        return None_or_one(out, 'get_scans expected 1 or None Scan')

    def add_scan(self, name, notes=None, value=None, **kws):
        """add scan"""
        kws['notes'] = notes
        kws['value'] = value
        kws['time_last_used'] = 0
        name = name.strip()
        row = self.__addRow(ScansTable, ('name',), (name,), **kws)
        self.session.add(row)
        self.commit()
        return row

    def add_info(self, key, value):
        """add Info key value pair -- returns Info instance"""
        row = self.__addRow(InfoTable, ('keyname', 'value'), (key, value))
        self.commit()
        return row

    def remove_scan(self, scan):
        s = self.get_scan(scan)
        if s is None:
            raise ScanDBException('Remove Scan needs valid scan')
        tab = self.tables['scans']
        self.conn.execute(tab.delete().where(tab.c.id==s.id))


if __name__ == '__main__':
    dbname = 'ScanDb.sdb'
    make_newdb(dbname)
    print '''%s  created and initialized.''' % dbname
    # dumpsql(dbname)
