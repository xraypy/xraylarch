#!/usr/bin/env python
'''
build American Mineralogist Crystal Structure Databse (amcsd)
'''

import os
import re
import requests

try:
    from cStringIO import StringIO #python 2
except:
    from io import StringIO #python 3

import numpy as np

from itertools import groupby

import larch
from larch_plugins.xrd import generate_hkl,peaklocater,create_cif,SPACEGROUPS,lambda_from_E

from sqlalchemy import (create_engine,MetaData,
                        Table,Column,Integer,String,Unicode,
                        PrimaryKeyConstraint,ForeignKeyConstraint,ForeignKey,
                        Numeric,func,
                        and_,or_,not_,tuple_)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,mapper,clear_mappers,relationship
from sqlalchemy.pool import SingletonThreadPool

HAS_CifFile = False
try:
    import CifFile
    HAS_CifFile = True
except ImportError:
    pass

SYMMETRIES = ['triclinic',
              'monoclinic',
              'orthorhombic',
              'tetragonal',
              'trigonal',
              'hexagonal',
              'cubic']
ELEMENTS = [['1',  'Hydrogen',  'H'], ['2',  'Helium',  'He'], ['3',  'Lithium',  'Li'],
            ['4',  'Beryllium',  'Be'], ['5',  'Boron',  'B'], ['6',  'Carbon',  'C'],
            ['7',  'Nitrogen',  'N'], ['8',  'Oxygen',  'O'], ['9',  'Fluorine',  'F'],
            ['10',  'Neon',  'Ne'], ['11',  'Sodium',  'Na'], ['12',  'Magnesium',  'Mg'],
            ['13',  'Aluminum',  'Al'], ['14',  'Silicon',  'Si'], ['15',  'Phosphorus',  'P'],
            ['16',  'Sulfur',  'S'], ['17',  'Chlorine',  'Cl'], ['18',  'Argon',  'Ar'],
            ['19',  'Potassium',  'K'], ['20',  'Calcium',  'Ca'], ['21',  'Scandium',  'Sc'],
            ['22',  'Titanium',  'Ti'], ['23',  'Vanadium',  'V'], ['24',  'Chromium',  'Cr'],
            ['25',  'Manganese',  'Mn'], ['26',  'Iron',  'Fe'], ['27',  'Cobalt',  'Co'],
            ['28',  'Nickel',  'Ni'], ['29',  'Copper',  'Cu'], ['30',  'Zinc',  'Zn'],
            ['31',  'Gallium',  'Ga'], ['32',  'Germanium',  'Ge'], ['33',  'Arsenic',  'As'],
            ['34',  'Selenium',  'Se'], ['35',  'Bromine',  'Br'], ['36',  'Krypton',  'Kr'],
            ['37',  'Rubidium',  'Rb'], ['38',  'Strontium',  'Sr'], ['39',  'Yttrium',  'Y'],
            ['40',  'Zirconium',  'Zr'], ['41',  'Niobium',  'Nb'], ['42',  'Molybdenum',  'Mo'],
            ['43',  'Technetium',  'Tc'], ['44',  'Ruthenium',  'Ru'], ['45',  'Rhodium',  'Rh'],
            ['46',  'Palladium',  'Pd'], ['47',  'Silver',  'Ag'], ['48',  'Cadmium',  'Cd'],
            ['49',  'Indium',  'In'], ['50',  'Tin',  'Sn'], ['51',  'Antimony',  'Sb'],
            ['52',  'Tellurium',  'Te'], ['53',  'Iodine',  'I'], ['54',  'Xenon',  'Xe'],
            ['55',  'Cesium',  'Cs'], ['56',  'Barium',  'Ba'], ['57',  'Lanthanum',  'La'],
            ['58',  'Cerium',  'Ce'], ['59',  'Praseodymium',  'Pr'], ['60',  'Neodymium',  'Nd'],
            ['61',  'Promethium',  'Pm'], ['62',  'Samarium',  'Sm'], ['63',  'Europium',  'Eu'],
            ['64',  'Gadolinium',  'Gd'], ['65',  'Terbium',  'Tb'], ['66',  'Dysprosium',  'Dy'],
            ['67',  'Holmium',  'Ho'], ['68',  'Erbium',  'Er'], ['69',  'Thulium',  'Tm'],
            ['70',  'Ytterbium',  'Yb'], ['71',  'Lutetium',  'Lu'], ['72',  'Hafnium',  'Hf'],
            ['73',  'Tantalum',  'Ta'], ['74',  'Tungsten',  'W'], ['75',  'Rhenium',  'Re'],
            ['76',  'Osmium',  'Os'], ['77',  'Iridium',  'Ir'], ['78',  'Platinum',  'Pt'],
            ['79',  'Gold',  'Au'], ['80',  'Mercury',  'Hg'], ['81',  'Thallium',  'Tl'],
            ['82',  'Lead',  'Pb'], ['83',  'Bismuth',  'Bi'], ['84',  'Polonium',  'Po'],
            ['85',  'Astatine',  'At'], ['86',  'Radon',  'Rn'], ['87',  'Francium',  'Fr'],
            ['88',  'Radium',  'Ra'], ['89',  'Actinium',  'Ac'], ['90',  'Thorium',  'Th'],
            ['91',  'Protactinium',  'Pa'], ['92',  'Uranium',  'U'], ['93',  'Neptunium',  'Np'],
            ['94',  'Plutonium',  'Pu'], ['95',  'Americium',  'Am'], ['96',  'Curium',  'Cm'],
            ['97',  'Berkelium',  'Bk'], ['98',  'Californium',  'Cf'], ['99',  'Einsteinium',  'Es'],
            ['100',  'Fermium',  'Fm'], ['101',  'Mendelevium',  'Md'], ['102',  'Nobelium',  'No'],
            ['103',  'Lawrencium',  'Lr'], ['104',  'Rutherfordium',  'Rf'], ['105',  'Dubnium',  'Db'],
            ['106',  'Seaborgium',  'Sg'], ['107',  'Bohrium',  'Bh'], ['108',  'Hassium',  'Hs'],
            ['109',  'Meitnerium',  'Mt'], ['110',  'Darmstadtium',  'Ds'], ['111',  'Roentgenium',  'Rg'],
            ['112',  'Ununbium',  'Uub'], ['113',  'Ununtrium',  'Uut'], ['114',  'Ununquadium',  'Uuq'],
            ['115',  'Ununpentium',  'Uup'], ['116',  'Ununhexium',  'Uuh'], ['117',  'Ununseptium',  'Uus'],
            ['118',  'Ununoctium',  'Uuo']]

CATEGORIES = ['soil',
              'salt',
              'clay']

QMIN = 0.2
QMAX = 10.0
QSTEP = 0.01
QWIDTH = 0.05

def make_engine(dbname):
    return create_engine('sqlite:///%s' % (dbname),
                         poolclass=SingletonThreadPool)

def iscifDB(dbname):
    '''
    test if a file is a valid scan database:
    must be a sqlite db file, with tables named according to _tables
    '''
    _tables = ('ciftbl',
               'elemtbl',
               'nametbl',
               'spgptbl',
               'symtbl',
               'authtbl',
               'qtbl',
               'cattbl',
               'symref',
               'compref',
               'authref',
               'qref',
               'catref')
    result = False
    try:
        engine = make_engine(dbname)
        meta = MetaData(engine)
        meta.reflect()
        result = all([t in meta.tables for t in _tables])
    except:
        pass
    return result

class _BaseTable(object):
    "generic class to encapsulate SQLAlchemy table"
    def __repr__(self):
        el = getattr(self, 'element', '??')
        return "<%s(%s)>" % (self.__class__.__name__, el)

class ElementTable(_BaseTable):
    (z, name, symbol) = [None]*3

class MineralNameTable(_BaseTable):
    (id,name) = [None]*2

class SpaceGroupTable(_BaseTable):
    (iuc_id, hm_notation) = [None]*2

class CrystalSymmetryTable(_BaseTable):
    (id, name) = [None]*2

class AuthorTable(_BaseTable):
    (id,name) = [None]*2

class QTable(_BaseTable):
    (id, q) = [None]*2

class CategoryTable(_BaseTable):
    (id,name) = [None]*2

class CIFTable(_BaseTable):
    (amcsd_id, mineral_id, iuc_id, cif) = [None]*4


class cifDB(object):
    '''
    interface to the American Mineralogist Crystal Structure Database
    '''
    def __init__(self, dbname=None, read_only=True,verbose=False):

        ## This needs to be modified for creating new if does not exist.
        self.dbname=dbname
        if verbose:
            print('\n\n================ %s ================\n' % self.dbname)
        if not os.path.exists(self.dbname):
            parent, child = os.path.split(__file__)
            self.dbname = os.path.join(parent, self.dbname)
            if not os.path.exists(self.dbname):
                print("File '%s' not found; building a new database!" % self.dbname)
                self.create_database(name=self.dbname)
            else:
                if not iscifDB(self.dbname):
                    raise ValueError("'%s' is not a valid cif database file!" % self.dbname)
        
        self.dbname = self.dbname
        self.engine = make_engine(self.dbname)
        self.conn = self.engine.connect()
        kwargs = {}
        if read_only:
            kwargs = {'autoflush': True, 'autocommit':False}
            def readonly_flush(*args, **kwargs):
                return
            self.session = sessionmaker(bind=self.engine, **kwargs)()
            self.session.flush = readonly_flush
        else:
            self.session = sessionmaker(bind=self.engine, **kwargs)()

        self.metadata =  MetaData(self.engine)
        self.metadata.reflect()
        tables = self.tables = self.metadata.tables

        ## Load tables
        ciftbl  = tables['ciftbl']
        elemtbl = tables['elemtbl']
        nametbl = tables['nametbl']
        spgptbl = tables['spgptbl']
        symtbl  = tables['symtbl']
        authtbl = tables['authtbl']
        cattbl  = tables['cattbl']
        qtbl    = tables['qtbl']
        symref  = tables['symref']
        compref = tables['compref']
        authref = tables['authref']
        catref  = tables['catref']
        qref    = tables['qref']

        ## Define mappers
        clear_mappers()
        mapper(ElementTable, elemtbl, properties=dict(
                 a=relationship(ElementTable, secondary=compref,
                 primaryjoin=(compref.c.z == elemtbl.c.z),
                 secondaryjoin=(compref.c.amcsd_id == ciftbl.c.amcsd_id))))
        mapper(MineralNameTable, nametbl, properties=dict(
                 a=relationship(MineralNameTable, secondary=ciftbl,
                 primaryjoin=(ciftbl.c.mineral_id == nametbl.c.mineral_id))))
        mapper(SpaceGroupTable, spgptbl, properties=dict(
                 a=relationship(SpaceGroupTable, secondary=symref,
                 primaryjoin=(symref.c.iuc_id == spgptbl.c.iuc_id),
                 secondaryjoin=(symref.c.symmetry_id == symtbl.c.symmetry_id))))
        mapper(CrystalSymmetryTable, symtbl, properties=dict(
                 a=relationship(CrystalSymmetryTable, secondary=symref,
                 primaryjoin=(symref.c.symmetry_id == symtbl.c.symmetry_id),
                 secondaryjoin=(symref.c.iuc_id == spgptbl.c.iuc_id))))
        mapper(AuthorTable, authtbl, properties=dict(
                 a=relationship(AuthorTable, secondary=authref,
                 primaryjoin=(authref.c.author_id == authtbl.c.author_id))))
        mapper(QTable, qtbl, properties=dict(
                 a=relationship(QTable, secondary=qref,
                 primaryjoin=(qref.c.q_id == qtbl.c.q_id))))
        mapper(CategoryTable, cattbl, properties=dict(
                 a=relationship(CategoryTable, secondary=catref,
                 primaryjoin=(catref.c.category_id == cattbl.c.category_id))))
        mapper(CIFTable, ciftbl, properties=dict(
                 a=relationship(CIFTable, secondary=compref,
                 primaryjoin=(compref.c.amcsd_id == ciftbl.c.amcsd_id),
                 secondaryjoin=(compref.c.z == elemtbl.c.z))))

        self.load_database()


    def query(self, *args, **kws):
        "generic query"
        return self.session.query(*args, **kws)

    def open_database(self):

        print('\nAccessing database: %s' % self.dbname)
        self.metadata = MetaData('sqlite:///%s' % self.dbname)

    def close_database(self):
        "close session"
        self.session.flush()
        self.session.close()
        clear_mappers()
            
    def create_database(self,name=None,verbose=False):

        if name is None:
            self.dbname = 'amcsd%02d.db'
            counter = 0
            while os.path.exists(self.dbname % counter):
                counter += 1
            self.dbname = self.dbname % counter
        else:
            self.dbname = name
    
        self.open_database()

        ###################################################
        ## Look up tables
        elemtbl = Table('elemtbl', self.metadata,
                  Column('z', Integer, primary_key=True),
                  Column('element_name', String(40), unique=True, nullable=True),
                  Column('element_symbol', String(2), unique=True, nullable=False)
                  )
        nametbl = Table('nametbl', self.metadata,
                  Column('mineral_id', Integer, primary_key=True),
                  Column('mineral_name', String(30), unique=True, nullable=True)
                  )
        spgptbl = Table('spgptbl', self.metadata,
                  Column('iuc_id', Integer),
                  Column('hm_notation', String(16), unique=True, nullable=True),
                  PrimaryKeyConstraint('iuc_id', 'hm_notation')
                  )
        symtbl = Table('symtbl', self.metadata,
                 Column('symmetry_id', Integer, primary_key=True),
                 Column('symmetry_name', String(16), unique=True, nullable=True)
                 )
        authtbl = Table('authtbl', self.metadata,
                  Column('author_id', Integer, primary_key=True),
                  Column('author_name', String(40), unique=True, nullable=True)
                  )
        qtbl = Table('qtbl', self.metadata,
               Column('q_id', Integer, primary_key=True),
               #Column('q', Float()) ## how to make this work? mkak 2017.02.14
               Column('q', String())
               )
        cattbl = Table('cattbl', self.metadata,
                 Column('category_id', Integer, primary_key=True),
                 Column('category_name', String(16), unique=True, nullable=True)
                 )
        ###################################################
        ## Cross-reference tables
        symref = Table('symref', self.metadata,
                 Column('iuc_id', None, ForeignKey('spgptbl.iuc_id')),
                 Column('symmetry_id', None, ForeignKey('symtbl.symmetry_id')),
                 PrimaryKeyConstraint('iuc_id', 'symmetry_id')
                 )
        compref = Table('compref', self.metadata,
                  Column('z', None, ForeignKey('elemtbl.z')),
                  Column('amcsd_id', None, ForeignKey('ciftbl.amcsd_id')),
                  PrimaryKeyConstraint('z', 'amcsd_id')
                  )
        authref = Table('authref', self.metadata,
                  Column('author_id', None, ForeignKey('authtbl.author_id')),
                  Column('amcsd_id', None, ForeignKey('ciftbl.amcsd_id')),
                  PrimaryKeyConstraint('author_id', 'amcsd_id')
                  )
        qref = Table('qref', self.metadata,
               Column('q_id', None, ForeignKey('qtbl.q_id')),
               Column('amcsd_id', None, ForeignKey('ciftbl.amcsd_id')),
               PrimaryKeyConstraint('q_id', 'amcsd_id')
               )
        catref = Table('catref', self.metadata,
                 Column('category_id', None, ForeignKey('cattbl.category_id')),
                 Column('amcsd_id', None, ForeignKey('ciftbl.amcsd_id')),
                 PrimaryKeyConstraint('category_id', 'amcsd_id')
                 )
        ###################################################
        ## Main table
        ciftbl = Table('ciftbl', self.metadata,
                 Column('amcsd_id', Integer, primary_key=True),
                 Column('mineral_id', Integer),
                 Column('iuc_id', ForeignKey('spgptbl.iuc_id')),
                 Column('cif', String(25)) ## , nullable=True
                 )
        ###################################################
        ## Add all to file
        self.metadata.create_all() ## if not exists function (callable when exists)

        ###################################################
        ## Define 'add/insert' functions for each table
        def_elem = elemtbl.insert()
        def_name = nametbl.insert()
        def_spgp = spgptbl.insert()
        def_sym  = symtbl.insert()
        def_auth = authtbl.insert()
        def_q    = qtbl.insert()
        def_cat  = cattbl.insert()
        
        add_sym  = symref.insert()
        add_comp = compref.insert()
        add_auth = authref.insert()
        add_q    = qref.insert()
        add_cat  = catref.insert()

        new_cif  = ciftbl.insert()


        ###################################################
        ## Populate the fixed tables of the database

        ## Adds all elements into database
        for element in ELEMENTS:
            z, name, symbol = element
            def_elem.execute(z=int(z),element_name=name,element_symbol=symbol)

        ## Adds all crystal symmetries
        for symmetry_id,symmetry in enumerate(SYMMETRIES):
            def_sym.execute(symmetry_name=symmetry.strip())
            if symmetry.strip() == 'triclinic':      ## triclinic    :   1 -   2
                for iuc_id in range(1,2+1):
                    add_sym.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'monoclinic':   ## monoclinic   :   3 -  15
                for iuc_id in range(3,15+1):
                    add_sym.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'orthorhombic': ## orthorhombic :  16 -  74
                for iuc_id in range(16,74+1):
                    add_sym.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'tetragonal':   ## tetragonal   :  75 - 142
                for iuc_id in range(75,142+1):
                    add_sym.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'trigonal':     ## trigonal     : 143 - 167
                for iuc_id in range(143,167+1):
                    add_sym.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'hexagonal':    ## hexagonal    : 168 - 194
                for iuc_id in range(168,194+1):
                    add_sym.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'cubic':        ## cubic        : 195 - 230
                for iuc_id in range(195,230+1):
                    add_sym.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))

        for cat in CATEGORIES:
            def_cat.execute(category_name=cat)

        ## Adds qrange
        qrange = np.arange(QMIN,QMAX+QSTEP,QSTEP)
        for q in qrange:
            def_q.execute(q=float('%0.2f' % q))

        ## Adds all space groups
        for spgrp_no in SPACEGROUPS.keys():
            for spgrp_name in SPACEGROUPS[spgrp_no]:
                try:
                    def_spgp.execute(iuc_id=spgrp_no,hm_notation=spgrp_name)
                except:
                    if verbose:
                        print('Duplicate: %s %s' % (spgrp_no,spgrp_name))
                pass
  
    def load_database(self):

        ###################################################
        ## Look up tables
        self.elemtbl = Table('elemtbl', self.metadata)
        self.nametbl = Table('nametbl', self.metadata)
        self.spgptbl = Table('spgptbl', self.metadata)
        self.symtbl  = Table('symtbl',  self.metadata)
        self.authtbl = Table('authtbl', self.metadata)
        self.qtbl    = Table('qtbl',    self.metadata)
        self.cattbl  = Table('cattbl',  self.metadata)
        ###################################################
        ## Cross-reference tables
        self.symref  = Table('symref', self.metadata)
        self.compref = Table('compref', self.metadata)
        self.authref = Table('authref', self.metadata)
        self.qref    = Table('qref', self.metadata)
        self.catref  = Table('catref', self.metadata)
        ###################################################
        ## Main table
        self.ciftbl  = Table('ciftbl', self.metadata)
        
        
    def cif_to_database(self,cifile,verbose=True,url=False,ijklm=1):
        '''
            ## Adds cifile into database
            When reading in new CIF:
            i.   put entire cif into field
            ii.  read _database_code_amcsd; write 'amcsd_id' to 'cif data'
            iii. read _chemical_name_mineral; find/add in' minerallist'; write
                 'mineral_id' to 'cif data'
            iv.  read _symmetry_space_group_name_H-M - find in 'spacegroup'; write
                 iuc_id to 'cif data'
            v.   read author name(s) - find/add in 'authorlist'; write 'author_id',
                 'amcsd_id' to 'authref'
            vi.  read _chemical_formula_sum; write 'z' (atomic no.), 'amcsd_id'
                 to 'compref'
            vii. calculate q - find each corresponding 'q_id' for all peaks; in write
                 'q_id','amcsd_id' to 'qpeak'
        '''

        if not HAS_CifFile:
            print('Missing required package(s) for this function:')
            print('Have CifFile? %r' % HAS_CifFile)
            return
            
        cf = CifFile.ReadCif(cifile)

        key = cf.keys()[0]

        ## Read icsd_id
        amcsd_id = None
        try:
            amcsd_id = int(cf[key][u'_database_code_icsd'])
        except:
            amcsd_id = int(cf[key][u'_database_code_amcsd'])


        ## check for amcsd in file already
        ## Find amcsd_id in database
        self.ciftbl = Table('ciftbl', self.metadata)
        search_cif = self.ciftbl.select(self.ciftbl.c.amcsd_id == amcsd_id)
        for row in search_cif.execute():
            if url:
                print('AMCSD %i already exists in database %s: %s' % 
                     (amcsd_id,self.dbname,cifile))
            else:
                print('%s: AMCSD %i already exists in database %s.' % 
                     (os.path.split(cifile)[-1],amcsd_id,self.dbname))
            return

        ## Read elements
        ALLelements = cf[key][u'_chemical_formula_sum'].split()
        for e0,element in enumerate(ALLelements):
            element= re.sub('[(){}<>.]', '', element)
            element = re.sub(r'([0-9])', r'', element)
            ALLelements[e0] = element

        ## Read mineral name
        mineral_name = None
        try:
            mineral_name = cf[key][u'_chemical_name_mineral']
        except:
            try:
                mineral_name = cf[key][u'_amcsd_formula_title']
            except:
                pass
            pass

        ## Read Hermann-Mauguin/space group
        hm_notation = cf[key][u'_symmetry_space_group_name_h-m']

        ## Read author names    
        authors = cf[key][u'_publ_author_name']
        for i,author in enumerate(authors):
            author = re.sub(r"[.]", r"", author)
            authors[i] = re.sub(r"[,]", r"", author)



        if url:
            cifstr = requests.get(cifile).text
        else:
            with open(cifile,'r') as file:
                cifstr = str(file.read())

        energy = 8048 # units eV
        cif = create_cif(cifstr=cifstr)
        cif.structure_factors(wvlgth=lambda_from_E(energy))

        peak_qid = []
        for i,qi in enumerate(cif.qhkl):
            qid = self.search_for_q(qi)
            if qid not in peak_qid:
                peak_qid.append(qid)

        ###################################################
        def_elem = self.elemtbl.insert()
        def_name = self.nametbl.insert()
        def_spgp = self.spgptbl.insert()
        def_sym  = self.symtbl.insert()
        def_auth = self.authtbl.insert()
        def_q    = self.qtbl.insert()
        def_cat  = self.cattbl.insert()
        add_sym  = self.symref.insert()
        add_comp = self.compref.insert()
        add_auth = self.authref.insert()
        add_q    = self.qref.insert()
        add_cat  = self.catref.insert()
        new_cif  = self.ciftbl.insert()

        ## Find mineral_name
        match = False
        search_mineral = self.nametbl.select(self.nametbl.c.mineral_name == mineral_name)
        for row in search_mineral.execute():
            mineral_id = row.mineral_id
            match = True
        if match is False:
            def_name.execute(mineral_name=mineral_name)
            search_mineral = self.nametbl.select(self.nametbl.c.mineral_name == mineral_name)
            for row in search_mineral.execute():
                mineral_id = row.mineral_id
                match = True

        ## Find symmetry_name
        match = False
        search_spgrp = self.spgptbl.select(self.spgptbl.c.hm_notation == re.sub(' ','',hm_notation))
        for row in search_spgrp.execute():
            iuc_id = row.iuc_id
            match = True
        if match is False:
            ## need a real way to deal with this trouble
            ## mkak 2016.11.04
            iuc_id = 0
            print('\tSpace group? ----> %s (amcsd: %i)' % (hm_notation,int(amcsd_id)))

        ## Save CIF entry into database
        new_cif.execute(amcsd_id=int(amcsd_id),
                             mineral_id=int(mineral_id),
                             iuc_id=iuc_id,
                             cif=cifstr)    

        ## Find composition (loop over all elements)
        for element in ALLelements:
            search_elements = self.elemtbl.select(self.elemtbl.c.element_symbol == element)
            for row in search_elements.execute():
                z = row.z
            try:
                add_comp.execute(z=z,amcsd_id=int(amcsd_id))
            except:
                print('could not find element: %s (amcsd: %i)' % (element,int(amcsd_id)))
                pass


        ## Find author_name
        for author_name in authors:
            match = False
            search_author = self.authtbl.select(self.authtbl.c.author_name == author_name)
            for row in search_author.execute():
                author_id = row.author_id
                match = True
            if match is False:
                def_auth.execute(author_name=author_name)
                search_author = self.authtbl.select(self.authtbl.c.author_name == author_name)
                for row in search_author.execute():
                    author_id = row.author_id
                    match = True
            if match == True:
                add_auth.execute(author_id=author_id,
                                   amcsd_id=int(amcsd_id))


        for calc_q_id in peak_qid:
            add_q.execute(q_id=calc_q_id,amcsd_id=int(amcsd_id))
            

    #     ## not ready for defined categories
    #     cif_category.execute(category_id='none',
    #                          amcsd_id=int(amcsd_id))

        if url:
            if verbose:
                self.print_amcsd_info(amcsd_id,no_qpeaks=len(peak_qid))
        else:
            if verbose:
                self.print_amcsd_info(amcsd_id,no_qpeaks=len(peak_qid),cifile=cifile)
            else:
                print('File : %s' % os.path.split(cifile)[-1])

    def url_to_cif(self,verbose=False,savecif=False,trackerr=False,
                     addDB=True,url=None,all=False):
    
        if url is None:
            url = 'http://rruff.geo.arizona.edu/AMS/download.php?id=%05d.cif&down=cif'
            #url = 'http://rruff.geo.arizona.edu/AMS/CIF_text_files/%05d_cif.txt'
 
        if trackerr:
            dir = os.getcwd()
            ftrack = open('%s/trouble_cif.txt' % dir,'a+')
            ftrack.write('using URL : %s\n\n' % url)
        
        ## Defines url range for searching and adding to cif database
        if all == True:
            iindex = range(99999)
        else:
            iindex = np.arange(13600,13700)
        
        for i in iindex:
            url_to_scrape = url % i
            r = requests.get(url_to_scrape)
            if r.text.split()[0] == "Can't" or '':
                if verbose:
                    print('\t---> ERROR on amcsd%05d.cif' % i)
                    if trackerr:
                        ftrack.write('%s\n' % url_to_scrape)
            else:
                if verbose:
                    print('Reading %s' % url_to_scrape)
                if savecif:
                    file = 'amcsd%05d.cif' % i
                    f = open(file,'w')
                    f.write(r.text)
                    f.close()
                    if verbose:
                        print('Saved %s' % file)
                if addDB:
                    if 1==1:#try:
                        self.cif_to_database(url_to_scrape,url=True,verbose=verbose,ijklm=i)
#                     except:
#                         if trackerr:
#                             ftrack.write('%s\n' % url_to_scrape)
#                         pass

        if trackerr:
            ftrack.close()


#     def database_array(self,maxrows=None):
#     
#         cif_array = {}
#         
#         search_cif = self.ciftbl.select()
#         count = 0
#         for cifrow in search_cif.execute():
#             amcsd_id = cifrow.amcsd_id
#             mineral_id = cifrow.mineral_id
#             iuc_id = cifrow.iuc_id
#             
#             mineral_name = ''
#             search_mineralname = self.nametbl.select(self.nametbl.c.mineral_id == mineral_id)
#             for mnrlrow in search_mineralname.execute():
#                 mineral_name = mnrlrow.mineral_name
#         
#             search_composition = self.compref.select(self.compref.c.amcsd_id == amcsd_id)
#             composition = ''
#             for cmprow in search_composition.execute():
#                 z = cmprow.z
#                 search_periodic = self.elemtbl.select(self.elemtbl.c.z == z)
#                 for elmtrow in search_periodic.execute():
#                     composition = '%s %s' % (composition,elmtrow.element_symbol)
#                     
#             search_authors = self.authref.select(self.authref.c.amcsd_id == amcsd_id)
#             authors = ''
#             for atrrow in search_authors.execute():
#                 author_id = atrrow.author_id
#                 search_alist = self.authtbl.select(self.authtbl.c.author_id == author_id)
#                 for block in search_alist.execute():
#                     if authors == '':
#                         authors = '%s' % (block.author_name)
#                     else:
#                         authors = '%s; %s' % (authors,block.author_name)
# 
#             count = count + 1
#             cif_array.update({count:(str(amcsd_id),str(mineral_name),str(iuc_id),str(composition),str(authors))})
#             if maxrows is not None:
#                  if count >= maxrows:
#                      return cif_array
#        
#         return cif_array



##################################################################################
##################################################################################

#         usr_qry = self.query(self.ciftbl,
#                              self.elemtbl,self.nametbl,self.spgptbl,self.symtbl,
#                              self.authtbl,self.qtbl,self.cattbl,
#                              self.authref,self.qref,self.compref,self.catref,self.symref)\
#                       .filter(self.authref.c.amcsd_id == self.ciftbl.c.amcsd_id)\
#                       .filter(self.authtbl.c.author_id == self.authref.c.author_id)\
#                       .filter(self.qref.c.amcsd_id == self.ciftbl.c.amcsd_id)\
#                       .filter(self.qref.c.q_id == self.qtbl.c.q_id)\
#                       .filter(self.compref.c.amcsd_id == self.ciftbl.c.amcsd_id)\
#                       .filter(self.compref.c.z == self.elemtbl.c.z)\
#                       .filter(self.catref.c.amcsd_id == self.ciftbl.c.amcsd_id)\
#                       .filter(self.catref.c.category_id == self.cattbl.c.category_id)\
#                       .filter(self.nametbl.c.mineral_id == self.ciftbl.c.mineral_id)\
#                       .filter(self.symref.c.symmetry_id == self.symtbl.c.symmetry_id)\
#                       .filter(self.symref.c.iuc_id == self.spgptbl.c.iuc_id)\
#                       .filter(self.spgptbl.c.iuc_id == self.ciftbl.c.iuc_id)

##################################################################################
##################################################################################


##################################################################################

    def print_amcsd_info(self,amcsd_id,no_qpeaks=None,cifile=None):

        ALLelements,mineral_name,iuc_id,authors = self.all_by_amcsd(amcsd_id)
        
        if cifile:
            print(' ==== File : %s ====' % os.path.split(cifile)[-1])
        else:
            print(' ===================== ')
        print(' AMCSD: %i' % amcsd_id)

        elementstr = ' Elements: '
        for element in ALLelements:
            elementstr = '%s %s' % (elementstr,element)
        print(elementstr)
        print(' Name: %s' % mineral_name)
        print(' Space Group No.: %s' % iuc_id)
        if no_qpeaks:
            print(' No. q-peaks in range : %s' % no_qpeaks)
        authorstr = ' Author: '
        for author in authors:
            try:
                authorstr = '%s %s' % (authorstr,author.split()[0])
            except:
                pass
        print(authorstr)
        print(' ===================== ')
        print('')

    def return_cif(self,amcsd_id):

        search_cif = self.ciftbl.select(self.ciftbl.c.amcsd_id == amcsd_id)
        for row in search_cif.execute():
            return row.cif

##################################################################################

    def all_by_amcsd(self,amcsd_id,verbose=False):

        mineral_id,iuc_id,cifstr = self.cif_by_amcsd(amcsd_id,all=True)
        
        #mineral_name = self.mineral_by_amcsd(amcsd_id)
        mineral_name = self.search_for_mineral(mineral_id,id_no=False)[0][0]
        ALLelements  = self.composition_by_amcsd(amcsd_id)
        authors      = self.author_by_amcsd(amcsd_id)
        
        return ALLelements,mineral_name,iuc_id,authors

    def q_by_amcsd(self,amcsd,qmin=None,qmax=None):

        usr_qry = self.query(self.ciftbl,self.qref,self.qtbl)\
                      .filter(self.qref.c.amcsd_id == self.ciftbl.c.amcsd_id)\
                      .filter(self.qref.c.q_id == self.qtbl.c.q_id)\
                      .filter(self.qref.c.amcsd_id == amcsd)
        if qmin is not None and qmax is not None:
            usr_qry = usr_qry.filter(and_(self.qtbl.c.q > qmin,self.qtbl.c.q < qmax))
        elif qmin is not None:
            usr_qry = usr_qry.filter(self.qtbl.c.q > qmin)        
        elif qmax is not None:
            usr_qry = usr_qry.filter(self.qtbl.c.q < qmax)
            
        return [float(row.q) for row in usr_qry.all()]

    def author_by_amcsd(self,amcsd_id):

        search_authors = self.authref.select(self.authref.c.amcsd_id == amcsd_id)
        authors = []
        for row in search_authors.execute():
            authors.append(self.search_for_author(row.author_id,id_no=False)[0][0])
        return authors

    def composition_by_amcsd(self,amcsd_id):

        search_composition = self.compref.select(self.compref.c.amcsd_id == amcsd_id)
        ALLelements = []
        for row in search_composition.execute():
            z = row.z
            search_periodic = self.elemtbl.select(self.elemtbl.c.z == z)
            for block in search_periodic.execute():
                ALLelements.append(block.element_symbol)
                
        return ALLelements

    def cif_by_amcsd(self,amcsd_id,all=False):

        search_cif = self.ciftbl.select(self.ciftbl.c.amcsd_id == amcsd_id)
        for row in search_cif.execute():
            if all: return row.mineral_id,row.iuc_id,row.cif
            else: return row.cif

    def mineral_by_amcsd(self,amcsd_id):

        search_cif = self.ciftbl.select(self.ciftbl.c.amcsd_id == amcsd_id)
        for row in search_cif.execute():
            cifstr = row.cif
            mineral_id = row.mineral_id
            iuc_id = row.iuc_id
        
        search_mineralname = self.nametbl.select(self.nametbl.c.mineral_id == mineral_id)
        for row in search_mineralname.execute():
            mineral_name = row.mineral_name
        return mineral_name

##################################################################################
##################################################################################

    def amcsd_by_q(self,include=[],list=None,verbose=False,minpeaks=2):

        q_incld  = []
        id_incld = []

        all_matches = []
        matches = []
        count = []

        
        if len(include) > 0:
            for q in include:
                q  = round_value(q,base=QSTEP)
                id = self.search_for_q(q)
                if id is not None and id not in id_incld:
                    id_incld += [id]
                        
        usr_qry = self.query(self.ciftbl,self.qtbl,self.qref)\
                      .filter(self.qref.c.amcsd_id == self.ciftbl.c.amcsd_id)\
                      .filter(self.qref.c.q_id == self.qtbl.c.q_id)
        if list is not None:
            usr_qry = usr_qry.filter(self.ciftbl.c.amcsd_id.in_(list))

        ##  Searches composition of database entries

        if len(id_incld) > 0:
            fnl_qry = usr_qry.filter(self.qref.c.q_id.in_(id_incld))
#             fnl_qry = usr_qry.filter(self.qref.c.q_id.in_(id_incld))\
#                              .group_by(self.qref.c.amcsd_id)\
#                              .having(func.count()>2)## having at least two in range is important
            for row in fnl_qry.all():

                if row.amcsd_id not in matches:
                    matches += [row.amcsd_id]
                    count += [1]
                else:
                    idx = matches.index(row.amcsd_id)
                    count[idx] = count[idx]+1

        amcsd_matches = [x for y, x in sorted(zip(count,matches)) if y > minpeaks]
        count_matches = [y for y, x in sorted(zip(count,matches)) if y > minpeaks]
       
        return amcsd_matches,count_matches


    def amcsd_by_chemistry(self,include=[],exclude=[],list=None,verbose=False):

        amcsd_incld = []
        amcsd_excld = []
        z_incld = []
        z_excld = []
        
        if len(include) > 0:
            for element in include:
                z = self.search_for_element(element)
                if z is not None and z not in z_incld:
                    z_incld += [z]
        if isinstance(exclude,bool):
            if exclude:
                for element in ELEMENTS:
                    z, name, symbol = element
                    z = int(z)
                    if z not in z_incld:
                        z_excld += [z]
        else:
            if len(exclude) > 0:
                for element in exclude:
                    z = self.search_for_element(element)
                    if z is not None and z not in z_excld:
                        z_excld += [z] 


                        
        usr_qry = self.query(self.ciftbl,self.elemtbl,self.compref)\
                      .filter(self.compref.c.amcsd_id == self.ciftbl.c.amcsd_id)\
                      .filter(self.compref.c.z == self.elemtbl.c.z)
        if list is not None:
            usr_qry = usr_qry.filter(self.ciftbl.c.amcsd_id.in_(list))

        ##  Searches composition of database entries
        if len(z_excld) > 0:
            fnl_qry = usr_qry.filter(self.compref.c.z.in_(z_excld))
            for row in fnl_qry.all():
                if row.amcsd_id not in amcsd_excld:
                    amcsd_excld += [row.amcsd_id]

        if len(z_incld) > 0:
            ## more elegant method but overloads query when too many (e.g. all others)
            ## used for exclusion
            ## mkak 2017.02.20
            #if len(amcsd_excld) > 0:
            #    usr_qry = usr_qry.filter(not_(self.compref.c.amcsd_id.in_(amcsd_excld)))
            fnl_qry = usr_qry.filter(self.compref.c.z.in_(z_incld))\
                             .group_by(self.compref.c.amcsd_id)\
                             .having(func.count()==len(z_incld))
            for row in fnl_qry.all():
                if row.amcsd_id not in amcsd_incld and row.amcsd_id not in amcsd_excld:
                    amcsd_incld += [row.amcsd_id]
        
        return amcsd_incld


    def amcsd_by_mineral(self,include='',list=None,verbose=True):

        amcsd_incld = []
        mnrl_id = self.search_for_mineral(include)

        usr_qry = self.query(self.ciftbl)
        if list is not None:
            usr_qry = usr_qry.filter(self.ciftbl.c.amcsd_id.in_(list))

 
        ##  Searches mineral name for database entries
        if len(mnrl_id) > 0:
            fnl_qry = usr_qry.filter(self.ciftbl.c.mineral_id.in_(mnrl_id))
            for row in fnl_qry.all():
                if row.amcsd_id not in amcsd_incld:
                    amcsd_incld += [row.amcsd_id]

        return amcsd_incld


    def amcsd_by_author(self,include=[''],list=None,verbose=True):

        amcsd_incld = []
        auth_id = []
        
        for author in include:
            id = self.search_for_author(author)
            auth_id += id

        ##  Searches mineral name for database entries
        usr_qry = self.query(self.ciftbl,self.authtbl,self.authref)\
                      .filter(self.authref.c.amcsd_id == self.ciftbl.c.amcsd_id)\
                      .filter(self.authref.c.author_id == self.authtbl.c.author_id)
        if list is not None:
            usr_qry = usr_qry.filter(self.ciftbl.c.amcsd_id.in_(list))

        ##  Searches author name in database entries
        if len(auth_id) > 0:
            fnl_qry = usr_qry.filter(self.authref.c.author_id.in_(auth_id))
            ## This currently works in an 'or' fashion, as each name in list
            ## can be matched to multiple auth_id values, so it is simpler to
            ## consider them all separately. Making a 2D list and restructuring
            ## query could improve this
            ## mkak 2017.02.24
            for row in fnl_qry.all():
                if row.amcsd_id not in amcsd_incld:
                    amcsd_incld += [row.amcsd_id]
        
        return amcsd_incld


##################################################################################
##################################################################################

    def search_for_q(self,q,qstep=None):
        '''
        searches q-reference table for match q value.
        '''
        if qstep is None:
            q1 = self.query(self.qtbl).filter(self.qtbl.c.q_id == 1)
            q2 = self.query(self.qtbl).filter(self.qtbl.c.q_id == 2)
            for qi,qj in zip(q1.all(),q2.all()):
                qstep = float(qj.q)-float(qi.q)
            
        q = round_value(q,base=qstep) 
     
        qrow = self.query(self.qtbl).filter(self.qtbl.c.q == q)
        if len(qrow.all()) == 1:
            for q0 in qrow.all():
                q_id = q0.q_id
                return q_id
        return
     
    def search_for_element(self,element,id_no=True,verbose=False):
        '''
        searches elements for match in symbol, name, or atomic number; match must be 
        exact.
        '''
        element = capitalize_string(element)
        elemrow = self.query(self.elemtbl)\
                      .filter(or_(self.elemtbl.c.z == element,
                                  self.elemtbl.c.element_symbol == element,
                                  self.elemtbl.c.element_name == element))
        if len(elemrow.all()) == 0:
            if verbose: print('%s not found in element database.' % element)
            return
        else:
            for row in elemrow.all():
                if id_no: return row.z
                else: return row

    def search_for_author(self,name,exact=False,id_no=True,verbose=False):
        '''
        searches database for author matching criteria given in 'name'
           - if name is a string:
                  - will match author name containing text
                  - will match id number if integer given in string
                  - will only look for exact match if exact flag is given
           - if name is an integer, will only match id number from database
        id_no: if True, will only return the id number of match(es)
               if False, returns name and id number
        e.g.   as INTEGER
               >>> cif.search_for_author(6,id_no=False)
                    ([u'Chao G Y'], [6])
               as STRING
               >>> cif.search_for_author('6',id_no=False)
                    ([u'Chao G Y', u'Geology Team 654'], [6, 7770])
        '''
    
        authname = []
        authid   = []

        id,name = filter_int_and_str(name,exact=exact)
        authrow = self.query(self.authtbl)\
                      .filter(or_(self.authtbl.c.author_name.like(name),
                                  self.authtbl.c.author_id  == id))
        if len(authrow.all()) == 0:
            if verbose: print('%s not found in author database.' % name)
        else:
            for row in authrow.all():
                authname += [row.author_name]
                authid   += [row.author_id]
                
        if id_no: return authid
        else: return authname,authid

    def search_for_mineral(self,name,exact=False,id_no=True,verbose=False):
        '''
        searches database for mineral matching criteria given in 'name'
           - if name is a string:
                  - will match mineral name containing text
                  - will match id number if integer given in string
                  - will only look for exact match if exact flag is given
           - if name is an integer, will only match id number from database
        id_no: if True, will only return the id number of match(es)
               if False, returns name and id number
        e.g.   as INTEGER
               >>> newcif.search_for_mineral(884,id_no=False)
                    ([u'Mg8(Mg2Al2)Al8Si12(O,OH)56'], [884])
               as STRING
               >>> newcif.search_for_mineral('884',id_no=False)
                    ([u'Mg8(Mg2Al2)Al8Si12(O,OH)56', u'Co3 Ge2.884 Tb0.624'], [884, 5973])
        
        '''
        mrlname = []
        mrlid   = []

        id,name = filter_int_and_str(name,exact=exact)
        mnrlrow = self.query(self.nametbl)\
                      .filter(or_(self.nametbl.c.mineral_name.like(name),
                                  self.nametbl.c.mineral_id  == id))
        if len(mnrlrow.all()) == 0:
            if verbose: print('%s not found in mineral name database.' % name)
        else:
            for row in mnrlrow.all():
                mrlname += [row.mineral_name]
                mrlid   += [row.mineral_id]
                
        if id_no: return mrlid
        else: return mrlname,mrlid
     
    def return_no_of_cif(self):
        
        lines = len(self.query(self.ciftbl).all())
        return lines

    def return_q(self):
        
        qqry = self.query(self.qtbl)
        q = [float(row.q) for row in qqry.all()]

        return np.array(q)

    def return_mineral_names(self):
        
        mineralqry = self.query(self.nametbl)
        names = ['']
        for row in mineralqry.all():
            names += [row.mineral_name]
        
        return sorted(names)

    def return_author_names(self):
        
        authorqry = self.query(self.authtbl)
        names = []
        for row in authorqry.all():
            names += [row.author_name]
        
        return sorted(names)

def round_value(x, prec=2, base=0.05):
  return round(base * round(float(x)/base),prec)

def capitalize_string(s):

    try:
        return s[0].upper() + s[1:].lower()
    except:
        return s
    
def filter_int_and_str(s,exact=False):

        try: i = int(s)
        except: i = 0
        if not exact:
            try: s = '%'+s+'%'
            except: pass
        
        return i,s


def column(matrix, i):
    return [row[i] for row in matrix]

class RangeParameter(object):

    def __init__(self,min=None,max=None,unit=None):

        self.min   = min
        self.max   = max
        self.unit  = unit
        
    def set_values(self,min=None,max=None,unit=None):

        self.__init__(min=min,max=max,unit=unit)

class SearchCIFdb(object):
    '''
    interface to the search the cif database
    '''
    def __init__(self, verbose=False):
    
        self.verbose = verbose
        
        ## running list of included amcsd id numbers
        self.amcsd_id = []

        ## tags for searching
        self.authors    = []
        self.keywords   = []
        self.categories = []
        self.amcsd      = []
        self.qpks       = []

        self.mnrlname   = ''

        self.elem_incl = []
        self.elem_excl = []
        self.allelem   = column(ELEMENTS,2)

        self.lattice_keys = ['a','b','c','alpha','beta','gamma']

        self.sg    = None
        self.a     = RangeParameter()
        self.b     = RangeParameter()
        self.c     = RangeParameter()
        self.alpha = RangeParameter()
        self.beta  = RangeParameter()
        self.gamma = RangeParameter()


        


    def print_all(self):
    
        for key in ['authors','mnrlname','keywords','categories','amcsd','qpks']:
             print('%s : %s' % (key,self.print_parameter(key=key)))
        print('chemistry : %s' % self.print_chemistry())
        print('geometry : %s' % self.print_geometry())
    
    def print_parameter(self,key='authors'):

        s = ''
        if len(self.__dict__[key]) > 0:
            for i,item in enumerate(self.__dict__[key]):
                item = item.split()[0]
                if i == 0:
                    s = '%s' % (item)
                else:
                    s = '%s, %s' % (s,item)
        return s

        
    def read_parameter(self,s,clear=True,key='authors'):
        '''
        This function works for keys: 
        'authors'
        'mnrlname
        keywords','categories','amcsd','qpks'
        '''
       
        if clear:
            self.__dict__[key] = []
        if len(s) > 0:
            for a in s.split(','):
                try:
                    self.__dict__[key] += [a.split()[0]]
                except:
                    pass

    def print_chemistry(self):
    
        s = ''
        for i,elem in enumerate(self.elem_incl):
            if i==0:
                s = '(%s' % elem
            else:
                s = '%s,%s' % (s,elem)
        if len(self.elem_incl) > 0:
            s = '%s) ' % s 
        if len(self.elem_excl) > 0:
            s = '%s- ' % s
        # if all else excluded, don't list
        if (len(self.allelem)-20) > (len(self.elem_incl)+len(self.elem_excl)): 
            for i,elem in enumerate(self.elem_excl):
                if i==0:
                    s = '%s(%s' % (s,elem)
                else:
                    s = '%s,%s' % (s,elem)
            if len(self.elem_excl) > 0:
                s = '%s)' % s
        return s
                
    def read_chemistry(self,s,clear=True):
       
        if clear:
            self.elem_incl,self.elem_excl = [],[]
        chem_incl,chem_excl = [],[]

        chemstr = re.sub('[( )]','',s)
        ii = -1
        for i,s in enumerate(chemstr):
            if s == '-':
                ii = i
        if ii > 0:
            chem_incl = chemstr[0:ii].split(',')
            if len(chemstr)-ii == 1:
                for elem in self.allelem:
                    if elem not in chem_incl:
                        chem_excl += [elem]
            elif ii < len(chemstr)-1:
                chem_excl = chemstr[ii+1:].split(',')
        else:
            chem_incl = chemstr.split(',')

        for elem in chem_incl:
            elem = capitalize_string(elem)
            if elem in self.allelem and elem not in self.elem_incl:
                self.elem_incl += [elem]
                if elem in self.elem_excl:
                    j = self.elem_excl.index(elem)
                    self.elem_excl.pop(j)
        for elem in chem_excl:
            elem = capitalize_string(elem)
            if elem in self.allelem and elem not in self.elem_excl and elem not in self.elem_incl:
                self.elem_excl += [elem]

    def print_geometry(self,unit='A'):

        s = ''

        key = 'sg'
        if self.__dict__[key] is not None:
            s = '%s%s=%s,' % (s,key,self.__dict__[key])
        for i,key in enumerate(self.lattice_keys):
            if self.__dict__[key].min is not None:
                s = '%s%s=%0.2f' % (s,key,float(self.__dict__[key].min))
                if self.__dict__[key].max is not None:
                    s = '%sto%0.2f' % (s,float(self.__dict__[key].max))
                s = '%s%s,' % (s,self.__dict__[key].unit)

        if len(s) > 1:
            if s[-1] == ',':
                s = s[:-1]

        return s

    def read_geometry(self,s):
        
        geostr = s.split(',')
        used = []
        for par in geostr:
            key = par.split('=')[0]
            val = par.split('=')[1]
            if key in 'sg':
                self.__dict__[key] = val
                used += [key]            
            elif key in self.lattice_keys:
                values = [''.join(g) for _, g in groupby(val, str.isalpha)]
                self.__dict__[key].min = values[0]
                if len(values) > 1: 
                    self.__dict__[key].unit = values[-1]
                if len(values) > 2:
                    self.__dict__[key].max = values[2]
                else:
                    self.__dict__[key].max = None
                used += [key]

        ## Resets undefined to None
        for key in self.lattice_keys:
            if key not in used:
                self.__dict__[key] = RangeParameter()
        key = 'sg'
        if key not in used:
            self.__dict__[key] = None
            
def match_database(fracq=0.75, pk_wid=0.05, q=None, ipks=None,
                   cifdatabase=None, verbose=False):
    '''
    fracq  : min. ratio of matched q to possible in q range, i.e. 'goodness gauge'
    pk_wid : maximum range in q which qualifies as a match between fitted and ideal

    '''

    q_pks = peaklocater(ipks,q)
    minq = np.min(q)
    maxq = np.max(q)

    qstep = QSTEP ## these quantities come from cifdb.py

    peaks = []
    p_ids = []

    for pk_q in q_pks:
        pk_id = cifdatabase.search_for_q(pk_q)

        ## performs peak broadening here
        if pk_wid > 0:
            st = int(pk_wid/qstep/2)
            for p in np.arange(-1*st,st+1):
                peaks += [pk_q+p*qstep]
                p_ids += [pk_id+p]
        else:
            peaks += [pk_q]
            p_ids += [pk_id]

    matches,count = cifdatabase.amcsd_by_q(peaks)
    goodness = np.zeros(len(count))

    for i, (amcsd,cnt) in enumerate(zip(matches,count)):
        peak_id = sorted(cifdatabase.q_by_amcsd(amcsd,qmin=minq,qmax=maxq))
        if len(peak_id) > 0:
            goodness[i] = float(cnt)/len(peak_id)

    try:
        matches,count,goodness = zip(*[(x,y,t) for t,x,y in sorted(zip(goodness,matches,count)) if t > fracq])
    except:
        matches,count,goodness = [],[],[]

    for i,amcsd in enumerate(matches):
        if verbose:
            str = 'AMCSD %i, %s (%0.3f --> %i of %i peaks)' % (amcsd,
                     cifdatabase.mineral_by_amcsd(amcsd),goodness[i],
                     count[i],count[i]/goodness[i])
            print(str)

               
    return matches
                
                          
                





