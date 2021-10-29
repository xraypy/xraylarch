import os
import sqlite3
from base64 import b64encode, b64decode

import numpy as np

from sqlalchemy import MetaData, create_engine, func, text, and_
from sqlalchemy.sql import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import SingletonThreadPool



__version__ = '1'

def make_engine(dbname):
    "create engine for sqlite connection"
    return create_engine('sqlite:///%s' % (dbname),
                         poolclass=SingletonThreadPool,
                         connect_args={'check_same_thread': False})

def isAMSCIFDB(dbname):
    """whether a file is a valid AMSCIF database

    Args:
        dbname (string): name of AMSCIF database file

    Returns:
        bool: is file a valid AMSCIF database

    Notes:
      1. must be a sqlite db file, with tables
        'cif', 'elements', 'spacegroup'
    """
    _tables = ('cif', 'elements', 'spacegroups')
    result = False
    try:
        engine = make_engine(dbname)
        meta = MetaData(engine)
        meta.reflect()
        result = all([t in meta.tables for t in _tables])
    except:
        pass
    return result


farray_scale = 4.e6

def encode_farray(dat):
    """encodes a list of fractional coordinate as strings (stricly on (-1,1))
    to an string for saving to db, to be decoded by  decode_farray()
    preserves precision to slightly better than 6 digits
    """
    work = []
    for d in dat:
        if d == '?':
            work.append(2) # out-of-bounds as '?'
        elif d == '.':
            work.append(3) # out-of-bounds as '.'
        else:
            if '(' in d or '(' in d:
                d = d.replace(')', ' : ').replace('(', ' : ')
                d = d.split(':')[0].strip()
            try:
                fval = float(d)
            except ValueError:
                d  = '0'
            work.append(d)
    x = (farray_scale*np.array([float(x) for x in work])).round()
    return b64encode(x.astype(np.int32).tobytes()).decode('ascii')

def decode_farray(dat):
    """decodes a string encoded by encode_farray()
    returns list of string
    """
    arr = np.fromstring(b64decode(dat), dtype=np.int32)/farray_scale
    out = []
    for a in arr:
        if (abs(a-2.0) < 1.e-5):
            out.append('?')
        elif (abs(a-3.0) < 1.e-5):
            out.append('.')
        else:
            out.append(f"{a:f}")
    return out

def put_optarray(dat, attr):
    d = dat.get(attr, '0')
    if d != '0':
        d = encode_farray(d)
    return d

def get_optarray(dat):
    if dat not in (0, '0'):
        dat = decode_farray(dat)
    return dat


schema = (
    '''CREATE TABLE version (id integer primary key, tag text, date text, notes text);''',
    '''CREATE TABLE elements (
        id  integer not null,
	z INTEGER NOT NULL,
	name VARCHAR(40),
	symbol VARCHAR(2) NOT NULL primary key);''',

    '''CREATE TABLE spacegroups (
        id INTEGER primary key,
	hm_notation VARCHAR(16) not null unique,
	symmetry_xyz text NOT NULL,
	category text     );''',

    '''CREATE TABLE minerals (
	id INTEGER not null primary key,
	name text not null unique);''',

    '''CREATE TABLE authors (
        id INTEGER NOT NULL primary key,
	name text unique);''',
    '''CREATE TABLE publications (
	id INTEGER NOT NULL primary key,
	journalname text not null,
	volume text,
	year  integer not null,
	page_first text,
	page_last text);''',

    '''CREATE TABLE publication_authors (
        publication_id INTEGER not null,
	author_id integer not null,
	FOREIGN KEY(publication_id) REFERENCES publications (id),
	FOREIGN KEY(author_id) REFERENCES authors (id));''',

    '''CREATE TABLE cif (
        id integer not null primary key,
	mineral_id INTEGER,
	spacegroup_id INTEGER,
	publication_id INTEGER,
	formula text,
        compound text,
        pub_title text,
        formula_title text,
	a text,
	b text,
	c text,
	alpha text,
	beta text,
	gamma text,
        cell_volume text,
        crystal_density text,
	atoms_sites text,
        atoms_x text,
        atoms_y text,
        atoms_z text,
        atoms_occupancy text,
        atoms_u_iso text,
        atoms_aniso_label text,
        atoms_aniso_u11 text,
        atoms_aniso_u22 text,
        atoms_aniso_u33 text,
        atoms_aniso_u12 text,
        atoms_aniso_u13 text,
        atoms_aniso_u23 text,
	qdat text,
     	amcsd_url text,
	FOREIGN KEY(spacegroup_id) REFERENCES spacegroups (id),
	FOREIGN KEY(mineral_id) REFERENCES minerals (id),
	FOREIGN KEY(publication_id) REFERENCES publications (id));''',

    '''CREATE TABLE cif_elements (
        cif_id text not null,
	element VARCHAR(2) not null);''',
    )


atsyms = ['H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg',
        'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V',
        'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se',
        'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh',
        'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba',
        'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho',
        'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt',
        'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac',
        'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm',
        'Md', 'No', 'Lr', 'D']


atnames = ['hydrogen', 'helium', 'lithium', 'beryllium',
         'boron', 'carbon', 'nitrogen', 'oxygen', 'fluorine', 'neon',
         'sodium', 'magnesium', 'aluminum', 'silicon', 'phosphorus',
         'sulfur', 'chlorine', 'argon', 'potassium', 'calcium', 'scandium',
         'titanium', 'vanadium', 'chromium', 'manganese', 'iron', 'cobalt',
         'nickel', 'copper', 'zinc', 'gallium', 'germanium', 'arsenic',
         'selenium', 'bromine', 'krypton', 'rubidium', 'strontium',
         'yttrium', 'zirconium', 'niobium', 'molybdenum', 'technetium',
         'ruthenium', 'rhodium', 'palladium', 'silver', 'cadmium',
         'indium', 'tin', 'antimony', 'tellurium', 'iodine', 'xenon',
         'cesium', 'barium', 'lanthanum', 'cerium', 'praseodymium',
         'neodymium', 'promethium', 'samarium', 'europium', 'gadolinium',
         'terbium', 'dysprosium', 'holmium', 'erbium', 'thulium',
         'ytterbium', 'lutetium', 'hafnium', 'tantalum', 'tungsten',
         'rhenium', 'osmium', 'iridium', 'platinum', 'gold', 'mercury',
         'thallium', 'lead', 'bismuth', 'polonium', 'astatine', 'radon',
         'francium', 'radium', 'actinium', 'thorium', 'protactinium',
         'uranium', 'neptunium', 'plutonium', 'americium', 'curium',
         'berkelium', 'californium', 'einsteinium', 'fermium',
         'mendelevium', 'nobelium', 'lawrencium', 'deuterium' ]

def create_amscifdb(dbname='test.db'):
    if os.path.exists(dbname):
        os.unlink(dbname)

    conn = sqlite3.connect(dbname)
    cursor = conn.cursor()
    for s in schema:
        cursor.execute(s)

    cursor.execute('insert into version values (?,?,?,?)',
                   ('0', 'in progress', 'today', 'in progress'))

    atz, i = 0, 0
    for sym, name in zip(atsyms, atnames):
        i += 1
        atz += 1
        if sym == 'D':
            atz = 1
        cursor.execute('insert into elements values (?,?,?,?)', (i, atz, sym, name))
