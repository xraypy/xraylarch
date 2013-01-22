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
from sqlalchemy import MetaData, Table, select, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import  NoResultFound

# needed for py2exe?
from sqlalchemy.dialects import sqlite, mysql, postgresql

from scandb_schema import make_engine, create_scandb, map_scandb

def isScanDB(dbname, server='sqlite', **kws):
    """test if a file is a valid scan database:
    must be a sqlite db file, with tables named
       'postioners', 'detectors', and 'scans'
    """
    _tables = ('info', 'positioners', 'detectors', 'scandefs')
    result = False
    try:
        engine = make_engine(dbname, server=server, **kws)
        meta = MetaData(engine)
        meta.reflect()
        if all([t in meta.tables for t in _tables]):
            keys = [row.name for row in
                    meta.tables['info'].select().execute().fetchall()]
            result = 'version' in keys and 'experiment_id' in keys
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

def make_datetime(t=None, iso=False):
    """unix timestamp to datetime iso format
    if t is None, current time is used"""
    if t is None:
        dt = datetime.now()
    else:
        dt = datetime.utcfromtimestamp(t)
    if iso:
        return datetime.isoformat(dt)
    return dt

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

class ScanDB(object):
    """

    Main Interface to Scans Database

    """
    def __init__(self, dbname=None, server='sqlite', **kws):
        self.dbname = dbname
        self.server = server
        self.tables = None
        self.engine = None
        self.session = None
        self.conn    = None
        self.metadata = None
        self.pvs = {}
        self.restoring_pvs = []
        if dbname is not None:
            self.connect(dbname, server=server, **kws)

    def create_newdb(self, dbname, server='sqlite',
                     connect=False, **kws):
        "create a new, empty database"
        create_scandb(dbname, server=server, **kws)
        if connect:
            time.sleep(0.5)
            self.connect(dbname, backup=False, **kws)

    def connect(self, dbname, server='sqlite', **kws):
        "connect to an existing database"
        if server == 'sqlite':
            if not os.path.exists(dbname):
                raise IOError("Database '%s' not found!" % dbname)

            if not isScanDB(dbname):
                raise ValueError("'%s' is not an Scans file!" % dbname)

            #if backup:
            #    save_backup(dbname)
        self.dbname = dbname
        self.engine = make_engine(dbname, server, **kws)
        self.conn = self.engine.connect()
        self.session = sessionmaker(bind=self.engine)()
        self.metadata =  MetaData(self.engine)
        self.metadata.reflect()
        self.tables, self.classes = map_scandb(self.metadata)

    def commit(self):
        "commit session state"
        self.set_info('modify_date', make_datetime())
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

    def get_info(self, name=None, default=None):
        """get a value for an entry in the info table"""
        errmsg = "get_info expected 1 or None value for name='%s'"
        table = self.tables['info']
        cls   = self.classes['info']
        if name is None:
            return self.query(table).all()
        out = self.query(table).filter(cls.name==name).all()
        thisrow = None_or_one(out, errmsg % name)
        if thisrow is None:
            return default
        return thisrow.value

    def set_info(self, name, value):
        """set key / value in the info table"""
        table = self.tables['info']
        cls   = self.classes['info']
        vals  = self.query(table).filter(cls.name==name).all()
        if len(vals) < 1:
            table.insert().execute(name=name, value=value)
        else:
            table.update(whereclause="name='%s'" % name).execute(value=value)

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
        ---------
           table: a valid table class, as mapped by mapper.
           value: can be one of the following table instance:
              keyid is returned string
        'name' attribute (or set which attribute with 'name' arg)
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

    def getall(self, table):
        """return rows from a named table"""
        # if table in self.classes:
        return self.query(self.classes[table]).all()


    def update_where(self, table, where, vals):
        """update a named table with dicts for 'where' and 'vals'"""
        if table in self.tables:
            table = self.tables[table]
        constraints = ["%s=%s" % (str(k), repr(v)) for k, v in where.items()]
        whereclause = ' AND '.join(constraints)
        table.update(whereclause=whereclause).execute(**vals)
        self.commit()

    def _get_table(self, tablename):
        "return (self.tables, self.classes) for a table name"
        if tablename not in self.classes:
            return None
        return self.classes[tablename], self.tables[tablename]

    def getrow(self, table, name, one_or_none=False):
        """return named row from a table"""
        cls, table = self._get_table(table)
        if table is None: return None
        if isinstance(name, Table):
            return name
        out = self.query(table).filter(cls.name==name).all()
        if one_or_none:
            return None_or_one(out, 'expected 1 or None from table %s' % table)
        return out

    # Scan Definitions
    def get_scandef(self, name):
        """return scandef by name"""
        return self.getrow('scandefs', name, one_or_none=True)

    def add_scandef(self, name, text='', notes='', **kws):
        """add scan"""
        cls, table = self._get_table('scandefs')
        kws.update('notes': notes, 'text': text})
        name = name.strip()
        row = self.__addRow(table, ('name',), (name,), **kws)
        self.session.add(row)
        self.commit()
        return row

    def remove_scandef(self, scan):
        s = self.get_scandef(scan)
        if s is None:
            raise ScanDBException('Remove Scan needs valid scan')
        tab = self.tables['scandefs']
        self.conn.execute(tab.delete().where(tab.c.id==s.id))

    # macros
    def get_macro(self, name):
        """return macro by name"""
        return self.getrow('macros', name, one_or_none=True)


    def add_macro(self, name, text, arguments='',
                  output='', notes='', **kws):
        """add macro"""
        cls, table = self._get_table('macros')
        name = name.strip()
        kws.update({'notes': notes, 'text': text,
                    'arguments': arguments})
        row = self.__addRow(table, ('name',), (name,), **kws)
        self.session.add(row)
        self.commit()
        return row

    # positioners
    def get_positioner(self, name):
        """return positioner by name"""
        return self.getrow('positioners', name, one_or_none=True)

    def add_positioner(self, name, pvname, notes='', **kws):
        """add positioner"""
        cls, table = self._get_table('positioners')
        name = name.strip()
        kws.update({'notes': notes, 'pvname': pvname})
        row = self.__addRow(table, ('name',), (name,), **kws)
        self.session.add(row)
        self.commit()
        return row

    # detectors
    def get_detector(self, name):
        """return detector by name"""
        return self.getrow('detectors', name, one_or_none=True)

    def add_detector(self, name, pvname, kind='', options='',
                     notes='', **kws):
        """add detector"""
        cls, table = self._get_table('detectors')
        name = name.strip()
        kws.update({'notes': notes, 'pvname': pvname,
                    'kind': kind, 'options': options})
        row = self.__addRow(table, ('name',), (name,), **kws)
        self.session.add(row)
        self.commit()
        return row

    # Monitor PVs
    def add_monitorpv(self, name, notes=''):
        """ """
        cls, table = self._get_table('monitorpvs')
        vals  = self.query(table).filter(cls.name == name).all()
        if len(vals) < 1:
            table.insert().execute(name=name, notes=notes)
        elif notes is not '':
            table.update(whereclause="name='%s'" % name).execute(notes=notes)
        return self.query(table).filter(cls.name == name).one()

    def record_monitorpv(self, pvname, value, commit=False):
        """save value for monitor pvs"""
        if pvname not in self.pvs:
            pv = self.add_monitorpv(pvname)
            self.pvs[pvname] = pv.id

        cls, table = self._get_table('monitorvalues')
        mval = cls()
        mval.monitorpvs_id = self.pvs[pvname]
        mval.value = value
        self.session.add(mval)
        if commit:
            self.commit()

    def get_monitorvalues(self, pvname, start_date=None, end_date=None):
        """get (value, time) pairs for a monitorpvs given a time range
        """
        if pvname not in self.pvs:
            pv = self.add_monitorpv(pvname)
            self.pvs[pvname] = pv.id
            
        cls, valtab = self._get_table('monitorvalues')
        cls, pvstab = self._get_table('monitorpvs')

        query = select([valtab.c.value, valtab.c.time],
                       valtab.c.monitorpvs_id==self.pvs[pvname])
        if start_date is not None:
            query = query.where(valtab.c.time >= start_date)
        if end_date is not None:
            query = query.where(valtab.c.time <= end_date)

        return query.execute().fetchall()



    # commands -- a very different interface
    def get_commands(self, status=None):
        """return command by status"""
        print 'get command by status'

    def add_command(self, command, arguments='', **kws):
        """add command"""
        cls, table = self._get_table('commands')
        kws.update({'arguments': arguments})

        row = self.__addRow(table, ('command',), (command,), **kws)
        self.session.add(row)
        self.commit()
        return row



if __name__ == '__main__':
    dbname = 'Test.sdb'
    create_scandb(dbname)
    print '''%s  created and initialized.''' % dbname
