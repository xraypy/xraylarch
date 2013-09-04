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
from sqlalchemy import MetaData, Table, select, and_, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import  NoResultFound

# needed for py2exe?
from sqlalchemy.dialects import sqlite, mysql, postgresql

from scandb_schema import get_dbengine, create_scandb, map_scandb

def isScanDB(dbname, server='sqlite',
             user='', password='', host='', port=None):
    """test if a file is a valid scan database:
    must be a sqlite db file, with tables named
       'postioners', 'detectors', and 'scans'
    """
    if server == 'sqlite':
        if not os.path.exists(dbname):
            return False
    else:
        if port is None:
            if server.startswith('my'): port = 3306
            if server.startswith('p'):  port = 5432
        conn = "%s://%s:%s@%s:%i/%s"

        try:
            _db = create_engine(conn % (server, user, password,
                                        host, port, dbname))
        except:
            return False
    
    _tables = ('info', 'status', 'commands', 'pvs', 'scandefs')
    engine = get_dbengine(dbname, server=server, create=False, 
                          user=user, password=password, host=host, port=port)
    try:
        meta = MetaData(engine)
        meta.reflect()
    except:
        return False
    
    if all([t in meta.tables for t in _tables]):
        keys = [row.keyname for row in
                meta.tables['info'].select().execute().fetchall()]
        return 'version' in keys and 'experiment_id' in keys
    return False


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
    def __init__(self, dbname=None, server='sqlite', create=False, **kws):
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
            self.connect(dbname, server=server, create=create, **kws)

    def create_newdb(self, dbname, connect=False, **kws):
        "create a new, empty database"
        create_scandb(dbname,  **kws)
        if connect:
            time.sleep(0.5)
            self.connect(dbname, backup=False, **kws)

    def connect(self, dbname, server='sqlite', create=False,
                user='', password='', host='', port=None, **kws):
        "connect to an existing database"
        creds = dict(user=user, password=password, host=host,
                     port=port, server=server)

        if not isScanDB(dbname,  **creds):
            if create:
                en = get_dbengine(dbname, create=True, **creds)
                create_scandb(dbname, create=True, **creds)
            else:
                raise ValueError("'%s' is not a Scan Database!" % dbname)

        self.dbname = dbname
        self.engine =get_dbengine(dbname, create=create, **creds)
        self.conn = self.engine.connect()
        self.session = sessionmaker(bind=self.engine)()
        self.metadata =  MetaData(self.engine)
        self.metadata.reflect()
        self.tables, self.classes = map_scandb(self.metadata)

        self.status_codes = {}
        for row in self.getall('status'):
            self.status_codes[row.name] = row.id

    def read_station_config(self, config):
        """convert station config to db entries"""

        for key, val in config.setup.items():
            self.set_info(key, val)

        for key, val in config.xafs.items():
            self.set_info(key, val)

        for key, val in config.slewscan.items():
            self.set_info('slew_%s' % key, val)
            
        for name, data in config.detectors.items():
            thisdet  = self.get_detector(name)
            pvname, opts = data
            dkind = opts.pop('kind')
            opts = json_encode(opts)
            if thisdet is None:
                self.add_detector(name, pvname, kind=dkind, options=opts)
            else:
                self.update_where('scandetectors', {'name': name},
                                  {'pvname': pvname, 'kind': dkind,
                                   'options': opts})

        for name, data in config.positioners.items():
            thispos  = self.get_positioner(name)
            drivepv, readpv = data
            if '.' not in drivepv: drivepv = '%s.VAL' % drivepv
            if thispos is None:
                self.add_positioner(name, drivepv, readpv=readpv)
            else:
                self.update_where('scanpositioners', {'name': name},
                                  {'drivepv': drivepv, 'readpv': readpv})

        for name, data in config.slewscan_positioners.items():
            thispos  = self.get_slewpositioner(name)
            drivepv, readpv = data
            if '.' not in drivepv: drivepv = '%s.VAL' % drivepv
            if thispos is None:
                self.add_slewpositioner(name, drivepv, readpv=readpv)
            else:
                self.update_where('slewscanpositioners', {'name': name},
                                  {'drivepv': drivepv, 'readpv': readpv})

        for name, pvname in config.counters.items():
            this  = self.get_counter(name)
            if this is None:
                self.add_counter(name, pvname)
            else:
                self.update_where('scancounters', {'name': name},
                                  {'pvname': pvname})

        for name, pvname in config.extra_pvs.items():
            this  = self.add_pv(pvname, notes=name, monitor=True)


    def commit(self):
        "commit session state"
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

    def get_info(self, key=None, default=None):
        """get a value for an entry in the info table"""
        errmsg = "get_info expected 1 or None value for name='%s'"
        cls, table = self._get_table('info')
        if key is None:
            return self.query(table).all()
        out = self.query(table).filter(cls.keyname==key).all()
        thisrow = None_or_one(out, errmsg % key)
        if thisrow is None:
            return default
        return thisrow.value

    def set_info(self, key, value):
        """set key / value in the info table"""
        cls, table = self._get_table('info')
        vals  = self.query(table).filter(cls.keyname==key).all()
        if len(vals) < 1:
            table.insert().execute(keyname=key,
                                   value=value)
        else:
            table.update(whereclause="keyname='%s'" % key).execute(value=value)

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
        table = table()
        for name, val in zip(argnames, argvals):
            setattr(table, name, val)
        for key, val in kws.items():
            if key == 'attributes':
                val = json_encode(val)
            setattr(table, key, val)
        try:
            self.session.add(table)
            # self.session.commit()
        except IntegrityError, msg:
            self.session.rollback()
            raise Warning('Could not add data to table %s\n%s' % (table, msg))

        return table

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
        """return all rows from a named table"""
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
        kws.update({'notes': notes, 'text': text})
        
        name = name.strip()
        row = self.__addRow(cls, ('name',), (name,), **kws)
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
        row = self.__addRow(cls, ('name',), (name,), **kws)
        self.session.add(row)
        self.commit()
        return row

    # positioners
    def get_positioner(self, name):
        """return positioner by name"""
        return self.getrow('scanpositioners', name, one_or_none=True)

    def add_positioner(self, name, drivepv, readpv=None, notes='', **kws):
        """add positioner"""
        cls, table = self._get_table('scanpositioners')
        name = name.strip()
        kws.update({'notes': notes, 'drivepv': drivepv,
                    'readpv': readpv})
        row = self.__addRow(cls, ('name',), (name,), **kws)
        self.session.add(row)
        self.commit()
        self.add_pv(drivepv, notes=name)
        if readpv is not None:
            self.add_pv(readpv, notes="%s readback" % name)
        return row

    def get_slewpositioner(self, name):
        """return slewscan positioner by name"""
        return self.getrow('slewscanpositioners', name, one_or_none=True)

    def add_slewpositioner(self, name, drivepv, readpv=None, notes='', **kws):
        """add slewscan positioner"""
        cls, table = self._get_table('slewscanpositioners')
        name = name.strip()
        kws.update({'notes': notes, 'drivepv': drivepv,
                    'readpv': readpv})
        row = self.__addRow(cls, ('name',), (name,), **kws)
        self.session.add(row)
        self.commit()
        self.add_pv(drivepv, notes=name)
        if readpv is not None:
            self.add_pv(readpv, notes="%s readback" % name)
        return row

    # detectors
    def get_detector(self, name):
        """return detector by name"""
        return self.getrow('scandetectors', name, one_or_none=True)

    def add_detector(self, name, pvname, kind='', options='', **kws):
        """add detector"""
        cls, table = self._get_table('scandetectors')
        name = name.strip()
        kws.update({'pvname': pvname,
                    'kind': kind, 'options': options})
        row = self.__addRow(cls, ('name',), (name,), **kws)
        self.session.add(row)
        self.commit()
        return row

    # counters -- simple, non-triggered PVs to add to detectors
    def get_counter(self, name):
        """return counter by name"""
        return self.getrow('scancounters', name, one_or_none=True)

    def add_counter(self, name, pvname, **kws):
        """add counter (non-triggered detector)"""
        cls, table = self._get_table('scancounters')
        name = name.strip()
        kws.update({'pvname': pvname})
        row = self.__addRow(cls, ('name',), (name,), **kws)
        self.session.add(row)
        self.add_pv(pvname, notes=name)
        self.commit()
        return row

    # add PV to list of PVs
    def add_pv(self, name, notes='', monitor=False):
        """add pv to PV table if not already there """
        cls, table = self._get_table('pvs')
        vals  = self.query(table).filter(cls.name == name).all()
        ismon = {False:0, True:1}[monitor]
        if len(vals) < 1:
            table.insert().execute(name=name, notes=notes, is_monitor=ismon)
        elif notes is not '':
            where = "name='%s'" % name
            table.update(whereclause=where).execute(notes=notes,
                                                    is_monitor=ismon)
        thispv = self.query(table).filter(cls.name == name).one()
        if name not in self.pvs:
            self.pvs[name] = thispv.id
        return thispv

    def record_monitorpv(self, pvname, value, commit=False):
        """save value for monitor pvs"""
        if pvname not in self.pvs:
            pv = self.add_pv(pvname, monitor=True)
            self.pvs[pvname] = pv.id

        cls, table = self._get_table('monitorvalues')
        mval = cls()
        mval.pv_id = self.pvs[pvname]
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

        query = select([valtab.c.value, valtab.c.time],
                       valtab.c.monitorpvs_id==self.pvs[pvname])
        if start_date is not None:
            query = query.where(valtab.c.time >= start_date)
        if end_date is not None:
            query = query.where(valtab.c.time <= end_date)

        return query.execute().fetchall()

    # commands -- a more complex interface
    def get_commands(self, status=None):
        """return command by status"""

        cls, table = self._get_table('commands')
        if status is None:
            return self.query(table).all()

        if status not in self.status_codes:
            status = 'unknown'

        statid = self.status_codes[status]
        return self.query(table).filter(cls.status_id==statid).all()


    def add_command(self, command, arguments='',output_value='',
                    output_file='', **kws):
        """add command"""
        cls, table = self._get_table('commands')

        statid = self.status_codes.get('requested', 1)

        kws.update({'arguments': arguments,
                    'output_file': output_file,
                    'output_value': output_value,
                    'status_id': statid})

        row = self.__addRow(cls, ('command',), (command,), **kws)
        self.session.add(row)
        self.commit()
        return row

    def set_command_status(self, id, status):
        """set the status of a command (by id)"""
        cls, table = self._get_table('commands')
        if status not in self.status_codes:
            status = 'unknown'
        statid = self.status_codes[status]
        table.update(whereclause="id='%i'" % id).execute(status_id=statid)

    def cancel_command(self, id):
        """cancel command"""
        self.set_command_status(id, 'canceled')
        self.commit()


if __name__ == '__main__':
    dbname = 'Test.sdb'
    create_scandb(dbname)
    print '''%s  created and initialized.''' % dbname
