#!/usr/bin/env python
'''
build American Mineralogist Crystal Structure Databse (amcsd)
'''

import os
import requests
import numpy as np
from itertools import groupby
from distutils.version import StrictVersion

import larch
from .xrd_fitting import peaklocater
from .xrd_cif import create_cif, SPACEGROUPS
from .xrd_tools import lambda_from_E

import json
from larch.utils.jsonutils import encode4js, decode4js

from sqlalchemy import (create_engine, MetaData, Table, Column, Integer,
                        String, Unicode, PrimaryKeyConstraint,
                        ForeignKeyConstraint, ForeignKey, Numeric, func,
                        and_, or_, not_, tuple_)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import SingletonThreadPool

SYMMETRIES = ['triclinic', 'monoclinic', 'orthorhombic', 'tetragonal',
              'trigonal', 'hexagonal', 'cubic']

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
QAXIS = np.arange(QMIN, QMAX+QSTEP, QSTEP)

ENERGY = 19000 ## units eV
_cifdb = None

def get_cifdb(dbname='amcsd_cif.db', _larch=None):
    global _cifdb
    if _cifdb is None:
        _cifdb = cifDB(dbname=dbname)
    if _larch is not None:
        symname = '_xray._cifdb'
        if not _larch.symtable.has_symbol(symname):
            _larch.symtable.set_symbol(symname, _cifdb)
    return _cifdb

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
               #'formtbl',
               'spgptbl',
               'symtbl',
               'authtbl',
               'qtbl',
               'cattbl',
               'symref',
               #'compref',
               #'qref',
               'authref',
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


class cifDB(object):
    '''
    interface to the American Mineralogist Crystal Structure Database
    '''
    def __init__(self, dbname=None, read_only=True,verbose=False):

        ## This needs to be modified for creating new if does not exist.
        self.version = '0.0.2'
        self.dbname = dbname
        if verbose:
            print('\n\n================ %s ================\n' % self.dbname)
        if not os.path.exists(self.dbname):
            parent, child = os.path.split(__file__)
            self.dbname = os.path.join(parent, self.dbname)
            if not os.path.exists(self.dbname):
                print("File '%s' not found; building a new database!" % self.dbname)
                self.create_cifdb(name=self.dbname)
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
        self.elemtbl = Table('elemtbl', self.metadata)
        self.nametbl = Table('nametbl', self.metadata)
        self.formtbl = Table('formtbl', self.metadata)
        self.spgptbl = Table('spgptbl', self.metadata)
        self.symtbl  = Table('symtbl',  self.metadata)
        self.authtbl = Table('authtbl', self.metadata)
        self.qtbl    = Table('qtbl',    self.metadata)
        self.cattbl  = Table('cattbl',  self.metadata)

        self.symref  = Table('symref',  self.metadata)
        self.compref = Table('compref', self.metadata)
        self.qref    = Table('qref',    self.metadata)
        self.authref = Table('authref', self.metadata)
        self.catref  = Table('catref',  self.metadata)

        self.ciftbl  = Table('ciftbl', self.metadata)

        self.axis = np.array([float(q[0]) for q in self.query(self.qtbl.c.q).all()])


    def query(self, *args, **kws):
        "generic query"
        return self.session.query(*args, **kws)

    def close(self):
        "close session"
        self.session.flush()
        self.session.close()

    def create_cifdb(self,name=None,verbose=False):

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
        formtbl = Table('formtbl', self.metadata,
                  Column('formula_id', Integer, primary_key=True),
                  Column('formula_name', String(30), unique=True, nullable=True)
                  )
        spgptbl = Table('spgptbl', self.metadata,
                  Column('iuc_id', Integer),
                  Column('hm_notation', String(16), unique=True, nullable=True),
                  PrimaryKeyConstraint('iuc_id', 'hm_notation')
                  )
        symtbl  = Table('symtbl', self.metadata,
                  Column('symmetry_id', Integer, primary_key=True),
                  Column('symmetry_name', String(16), unique=True, nullable=True)
                  )
        authtbl = Table('authtbl', self.metadata,
                  Column('author_id', Integer, primary_key=True),
                  Column('author_name', String(40), unique=True, nullable=True)
                  )
        qtbl    = Table('qtbl', self.metadata,
                  Column('q_id', Integer, primary_key=True),
                  #Column('q', Float()) ## how to make this work? mkak 2017.02.14
                  Column('q', String())
                  )
        cattbl  = Table('cattbl', self.metadata,
                  Column('category_id', Integer, primary_key=True),
                  Column('category_name', String(16), unique=True, nullable=True)
                  )
        ###################################################
        ## Cross-reference tables
        symref  = Table('symref', self.metadata,
                  Column('iuc_id', None, ForeignKey('spgptbl.iuc_id')),
                  Column('symmetry_id', None, ForeignKey('symtbl.symmetry_id')),
                  PrimaryKeyConstraint('iuc_id', 'symmetry_id')
                  )
        compref = Table('compref', self.metadata,
                  Column('z', None, ForeignKey('elemtbl.z')),
                  Column('amcsd_id', None, ForeignKey('ciftbl.amcsd_id')),
                  PrimaryKeyConstraint('z', 'amcsd_id')
                  )
        qref    = Table('qref', self.metadata,
                  Column('q_id', None, ForeignKey('qtbl.q_id')),
                  Column('amcsd_id', None, ForeignKey('ciftbl.amcsd_id')),
                  PrimaryKeyConstraint('q_id', 'amcsd_id')
                  )
        authref = Table('authref', self.metadata,
                  Column('author_id', None, ForeignKey('authtbl.author_id')),
                  Column('amcsd_id', None, ForeignKey('ciftbl.amcsd_id')),
                  PrimaryKeyConstraint('author_id', 'amcsd_id')
                  )
        catref  = Table('catref', self.metadata,
                  Column('category_id', None, ForeignKey('cattbl.category_id')),
                  Column('amcsd_id', None, ForeignKey('ciftbl.amcsd_id')),
                  PrimaryKeyConstraint('category_id', 'amcsd_id')
                  )
        ###################################################
        ## Main table
        ciftbl  = Table('ciftbl', self.metadata,
                  Column('amcsd_id', Integer, primary_key=True),
                  Column('mineral_id', Integer),
                  Column('formula_id', Integer),
                  Column('iuc_id', ForeignKey('spgptbl.iuc_id')),
                  Column('a', String(5)),
                  Column('b', String(5)),
                  Column('c', String(5)),
                  Column('alpha', String(5)),
                  Column('beta', String(5)),
                  Column('gamma', String(5)),
                  Column('cif', String(25)), ## , nullable=True
                  Column('zstr',String(25)),
                  Column('qstr',String(25)),
                  Column('url',String(25))
                  )
        ###################################################
        ## Add all to file
        self.metadata.create_all() ## if not exists function (callable when exists)

        ###################################################
        ## Define 'add/insert' functions for each table
        def_elem = elemtbl.insert()
        def_name = nametbl.insert()
        def_form = formtbl.insert()
        def_spgp = spgptbl.insert()
        def_sym  = symtbl.insert()
        def_auth = authtbl.insert()
        def_q    = qtbl.insert()
        def_cat  = cattbl.insert()

        add_sym  = symref.insert()
        add_comp = compref.insert()
        add_q    = qref.insert()
        add_auth = authref.insert()
        add_cat  = catref.insert()

        new_cif  = ciftbl.insert()


        ###################################################
        ## Populate the fixed tables of the database

        ## Adds all elements into database
        for element in ELEMENTS:
            z, name, symbol = element
            def_elem.execute(z=int(z), element_name=name, element_symbol=symbol)

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
        for q in QAXIS:
            def_q.execute(q='%0.2f' % q)

        ## Adds all space groups
        for spgrp_no in SPACEGROUPS.keys():
            for spgrp_name in SPACEGROUPS[spgrp_no]:
                try:
                    def_spgp.execute(iuc_id=spgrp_no,hm_notation=spgrp_name)
                except:
                    if verbose:
                        print('Duplicate: %s %s' % (spgrp_no,spgrp_name))
                pass


    def __add_space_groups(self):
        ## Add missing space groups
        for spgrp_no in SPACEGROUPS.keys():
            for spgrp_name in SPACEGROUPS[spgrp_no]:
                match = False
                search_spgrp = self.spgptbl.select(self.spgptbl.c.hm_notation == spgrp_name)
                for row in search_spgrp.execute():
                    match = True
                if match is False:
                    print('Adding: %s %s' % (spgrp_no,spgrp_name))
                    self.spgptbl.insert().execute(iuc_id=spgrp_no,hm_notation=spgrp_name)

    def add_ciffile(self, ciffile, verbose=True, url=False, ijklm=1, file=None):
        '''
        ## Adds ciffile into database
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

        if url:
            cifstr = requests.get(ciffile).text
        else:
            with open(ciffile,'r') as file:
                cifstr = str(file.read())
        cif = create_cif(text=cifstr)

        if cif.id_no is None:
            cif_no = 99999
            search_cif = self.query(self.ciftbl.c.amcsd_id).filter(self.ciftbl.c.amcsd_id == cif_no).all()
            cnt_lp = 0
            while len(search_cif) > 0:
                cif_no += 1
                cnt_lp += 1
                search_cif = self.query(self.ciftbl.c.amcsd_id).filter(self.ciftbl.c.amcsd_id == cif_no).all()
                if cnt_lp > 500: ##  safe guards against infinite loop
                    print(' *** too many loops to find unassigned AMCSD number.')
                    return
            print(' *** Assigning unnumbered CIF to AMCSD %i' % cif_no)
            cif.id_no = cif_no

        ## check for amcsd in file already
        ## Find amcsd_id in database
        self.ciftbl = Table('ciftbl', self.metadata)
        search_cif = self.ciftbl.select(self.ciftbl.c.amcsd_id == cif.id_no)
        for row in search_cif.execute():
            if verbose:
                if url:
                    print('AMCSD %i already exists in database.\n' % cif.id_no)
                else:
                    print('%s: AMCSD %i already exists in database %s.' %
                         (os.path.split(ciffile)[-1],cif.id_no,self.dbname))
            return

        ## Define q-array for each entry at given energy
        qhkl = cif.calc_q(wvlgth=lambda_from_E(ENERGY), q_min=QMIN, q_max=QMAX)
        qarr = self.create_q_array(qhkl)

        ###################################################
        def_name = self.nametbl.insert()
        def_form = self.formtbl.insert()
        def_spgp = self.spgptbl.insert()
        def_sym  = self.symtbl.insert()
        def_auth = self.authtbl.insert()
        def_q    = self.qtbl.insert()
        def_cat  = self.cattbl.insert()
        add_sym  = self.symref.insert()
        add_comp = self.compref.insert()
        add_q    = self.qref.insert()
        add_auth = self.authref.insert()
        add_cat  = self.catref.insert()
        new_cif  = self.ciftbl.insert()

        ## Find mineral_name
        match = False
        search_mineral = self.nametbl.select(self.nametbl.c.mineral_name == cif.label)
        for row in search_mineral.execute():
            mineral_id = row.mineral_id
            match = True
        if match is False:
            def_name.execute(mineral_name=cif.label)
            search_mineral = self.nametbl.select(self.nametbl.c.mineral_name == cif.label)
            for row in search_mineral.execute():
                mineral_id = row.mineral_id

        ## Find formula_name
        match = False
        search_formula = self.formtbl.select(self.formtbl.c.formula_name == cif.formula)
        for row in search_formula.execute():
            formula_id = row.formula_id
            match = True
        if match is False:
            def_form.execute(formula_name=cif.formula)
            search_formula = self.formtbl.select(self.formtbl.c.formula_name == cif.formula)
            for row in search_formula.execute():
                formula_id = row.formula_id

        ## Find composition (loop over all elements)
        z_list = []
        for element in set(cif.atom.label):
            search_elements = self.elemtbl.select(self.elemtbl.c.element_symbol == element)
            for row in search_elements.execute():
                z_list += [row.z]
        zarr = self.create_z_array(z_list)


        ## Save CIF entry into database
        new_cif.execute(amcsd_id=cif.id_no,
                        mineral_id=int(mineral_id),
                        formula_id=int(formula_id),
                        iuc_id=cif.symmetry.no,
                        a=str(cif.unitcell[0]),
                        b=str(cif.unitcell[1]),
                        c=str(cif.unitcell[2]),
                        alpha=str(cif.unitcell[3]),
                        beta=str(cif.unitcell[4]),
                        gamma=str(cif.unitcell[5]),
                        cif=cifstr,
                        zstr=json.dumps(zarr.tolist(),default=str),
                        qstr=json.dumps(qarr.tolist(),default=str),
                        url=str(ciffile))

        ## Build q cross-reference table
        for q in qhkl:
            search_q = self.qtbl.select(self.qtbl.c.q == '%0.2f' % (int(q * 100) / 100.))
            for row in search_q.execute():
                q_id = row.q_id

            try:
                add_q.execute(q_id=q_id,amcsd_id=cif.id_no)
            except:
                pass


        ## Build composition cross-reference table
        for element in set(cif.atom.label):
            search_elements = self.elemtbl.select(self.elemtbl.c.element_symbol == element)
            for row in search_elements.execute():
                z = row.z

            try:
                add_comp.execute(z=z, amcsd_id=cif.id_no)
            except:
                print('could not find element: %s (amcsd: %i)' % (element,cif.id_no))
                pass

        ## Find author_name
        for author_name in cif.publication.author:
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
                                   amcsd_id=cif.id_no)

    #     ## not ready for defined categories
    #     cif_category.execute(category_id='none',
    #                          amcsd_id=cif.id_no)

        if url:
            self.amcsd_info(cif.id_no, no_qpeaks=np.sum(qarr))
        else:
            self.amcsd_info(cif.id_no, no_qpeaks=np.sum(qarr),ciffile=ciffile)

    def url_to_cif(self, url=None, verbose=False, savecif=False, addDB=True,
                   all=False, minval=None):

        maxi = 20573
        exceptions = [0,7271,10783,14748,15049,15050,15851,18368,
                      18449,18450,18451,18452,18453,20029]

        ## ALL CAUSE FAILURE IN CIFFILE FUNCTION:
        ##  7271 : author name doubled in cif
        ## 14748 : has label of amcsd code but no number (or anything) assigned
        ## 15049 : page number 'L24307 1' could not be parsed as number
        ## 15050 : page number 'L24307 1' could not be parsed as number
        ## 15851 : no first page number provided despite providing field label
        ## 18368 : non-numerical entries in B_iso fields
        ## 18449 : no first page number provided despite providing field label
        ## 18450 : no first page number provided despite providing field label
        ## 20029 : no volume number provided despite providing field label

        if url is None:
            url = 'http://rruff.geo.arizona.edu/AMS/download.php?id=%05d.cif&down=cif'

        ## Defines url range for searching and adding to cif database
        if all:
            iindex = range(99999) ## trolls whole database online
        elif minval is not None:
            iindex = np.arange(minval, 99999) ## starts at given min and counts up
        else:
            iindex = np.arange(13600, 13700) ## specifies small range including CeO2 match

        for i in iindex:
            if i not in exceptions and i < maxi:
                url_to_scrape = url % i
                r = requests.get(url_to_scrape)
                if r.text.split()[0] == "Can't" or '':
                    if verbose:
                        print('\t---> ERROR on amcsd%05d.cif' % i)
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
                        try:
                            self.add_ciffile(url_to_scrape, url=True, verbose=verbose, ijklm=i)
                        except:
                            pass




##################################################################################
##################################################################################

#         usr_qry = self.query(self.ciftbl,
#                              self.elemtbl,self.nametbl,self.spgptbl,self.symtbl,
#                              self.authtbl,self.qtbl,self.cattbl,
#                              self.authref,self.compref,self.catref,self.symref)\
#                       .filter(self.authref.c.amcsd_id == self.ciftbl.c.amcsd_id)\
#                       .filter(self.authtbl.c.author_id == self.authref.c.author_id)\
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

    def amcsd_info(self, amcsd_id, no_qpeaks=None, ciffile=None):

        mineral_id,iuc_id = self.cif_by_amcsd(amcsd_id,only_ids=True)

        mineral_name = self.search_for_mineral(minid=mineral_id)[0].mineral_name
        authors      = self.author_by_amcsd(amcsd_id)

        ## ALLelements,mineral_name,iuc_id,authors = self.all_by_amcsd(amcsd_id)

        if ciffile:
            print(' ==== File : %s ====' % os.path.split(ciffile)[-1])
        else:
            print(' ===================== ')
        print(' AMCSD: %i' % amcsd_id)
        print(' Name: %s' % mineral_name)
        print(' %s' % self.composition_by_amcsd(amcsd_id,string=True))
        try:
            print(' Space Group No.: %s (%s)' % (iuc_id,self.symm_id(iuc_id)))
        except:
            print(' Space Group No.: %s' % iuc_id)
        if no_qpeaks:
            print(' No. q-peaks in range : %s' % no_qpeaks)

        authorstr = ' Author(s): '
        for author in authors:
             authorstr = '%s %s' % (authorstr,author.split()[0])
        print(authorstr)
        print(' ===================== ')

    def symm_id(sel, iuc_id):

        if not isinstance(iuc_id, int):
            iuc_id = int(iuc_id.split(':')[0])

        if   iuc_id < 3  : return 'triclinic'    ##   1 -   2 : Triclinic
        elif iuc_id < 16 : return 'monoclinic'   ##   3 -  15 : Monoclinic
        elif iuc_id < 75 : return 'orthorhombic' ##  16 -  74 : Orthorhombic
        elif iuc_id < 143: return 'tetragonal'   ##  75 - 142 : Tetragonal
        elif iuc_id < 168: return 'trigonal'     ## 143 - 167 : Trigonal
        elif iuc_id < 195: return 'hexagonal'    ## 168 - 194 : Hexagonal
        elif iuc_id < 231: return 'cubic'        ## 195 - 230 : Cubic
        else:
            return

    def return_cif(self,amcsd_id):
        search_cif = self.ciftbl.select(self.ciftbl.c.amcsd_id == amcsd_id)
        for row in search_cif.execute():
            return row.cif

##################################################################################

    def all_by_amcsd(self, amcsd_id):

        mineral_id,iuc_id = self.cif_by_amcsd(amcsd_id,only_ids=True)

        mineral_name = self.search_for_mineral(minid=mineral_id)[0].mineral_name
        ALLelements  = self.composition_by_amcsd(amcsd_id)
        authors      = self.author_by_amcsd(amcsd_id)

        return ALLelements, mineral_name, iuc_id, authors

    def q_by_amcsd(self,amcsd_id,qmin=QMIN,qmax=QMAX):

        q_results = self.query(self.ciftbl.c.qstr).filter(self.ciftbl.c.amcsd_id == amcsd_id).all()
        q_all = [json.loads(qrow[0]) for qrow in q_results]

        return [self.axis[i] for i,qi in enumerate(q_all[0]) if qi == 1 and self.axis[i] >= qmin and self.axis[i] <= qmax]

    def author_by_amcsd(self,amcsd_id):

        search_authors = self.authref.select(self.authref.c.amcsd_id == amcsd_id)
        authors = []
        for row in search_authors.execute():
            authors.append(self.search_for_author(row.author_id,id_no=False)[0][0])
        return authors

    def composition_by_amcsd(self, amcsd_id):
        q = self.query(self.compref).filter(self.compref.c.amcsd_id==amcsd_id)
        return [row.z for row in q.all()]

    def cif_by_amcsd(self,amcsd_id,only_ids=False):

        search_cif = self.ciftbl.select(self.ciftbl.c.amcsd_id == amcsd_id)
        for row in search_cif.execute():
            if only_ids:
                return row.mineral_id, row.iuc_id
            else:
                return row.cif

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

    def amcsd_by_q(self, peaks, qmin=None, qmax=None, qstep=None, list=None,
                   verbose=False):

        if qmin is None: qmin = QMIN
        if qmax is None: qmax = QMAX
        if qstep is None: qstep = QSTEP

        ## Defines min/max limits of q-range
        imin, imax = 0, len(self.axis)
        if qmax < np.max(self.axis):
            imax = abs(self.axis-qmax).argmin()
        if qmin > np.min(self.axis):
            imin = abs(self.axis-qmin).argmin()
        qaxis = self.axis[imin:imax]
        stepq = (qaxis[1]-qaxis[0])

        amcsd, q_amcsd = self.match_q(list=list, qmin=qmin, qmax=qmax)

        ## Re-bins data if different step size is specified
        if qstep > stepq:
            new_qaxis   = np.arange(np.min(qaxis),np.max(qaxis)+stepq,qstep)
            new_q_amcsd = np.zeros((np.shape(q_amcsd)[0],np.shape(new_qaxis)[0]))
            for m,qrow in enumerate(q_amcsd):
                for n,qn in enumerate(qrow):
                    if qn == 1:
                        k = np.abs(new_qaxis-qaxis[n]).argmin()
                        new_q_amcsd[m][k] = 1
            qaxis = new_qaxis
            q_amcsd = new_q_amcsd


        ## Create data array
        peaks_weighting = np.ones(len(qaxis),dtype=int)*-1
        peaks_true = np.zeros(len(qaxis),dtype=int)
        peaks_false = np.ones(len(qaxis),dtype=int)
        for p in peaks:
            i = np.abs(qaxis-p).argmin()
            peaks_weighting[i],peaks_true[i],peaks_false[i] = 1,1,0

        ## Calculate score/matches/etc.
        total_peaks = np.sum((q_amcsd),axis=1)
        match_peaks = np.sum((peaks_true*q_amcsd),axis=1)
        miss_peaks = np.sum((peaks_false*q_amcsd),axis=1)
        scores = np.sum((peaks_weighting*q_amcsd),axis=1)

        return sorted(zip(scores, amcsd, total_peaks, match_peaks, miss_peaks), reverse=True)


    def amcsd_by_chemistry(self, include=[], exclude=[]):

        amcsd_incld = []
        amcsd_excld = []
        z_incld = []
        z_excld = []

        if len(include) > 0:
            for element in include:
                z = self.get_element(element).z
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
                    z = self.get_element(element).z
                    if z is not None and z not in z_excld:
                        z_excld += [z]

        z_list_include = [1 if z in z_incld else 0 for z in np.arange(len(ELEMENTS)+1)]
        z_list_exclude = [1 if z in z_excld else 0 for z in np.arange(len(ELEMENTS)+1)]

        amcsd,z_amcsd = self.return_z_matches(list=list)

        ## Calculate score/matches/etc.
        match_z = np.sum((np.array(z_list_include)*np.array(z_amcsd)),axis=1)
        miss_z  = np.sum((np.array(z_list_exclude)*np.array(z_amcsd)),axis=1)

        for i,amcsd_id in enumerate(amcsd):
            if match_z[i] == np.sum(z_list_include) and miss_z[i] <= 0:
                amcsd_incld += [amcsd_id]
            else:
                amcsd_excld += [amcsd_id]

        return amcsd_incld


    def amcsd_by_mineral(self, min_name, list=None, verbose=True):
        """
        search by mineral name
        """
        out = []
        minerals = self.search_for_mineral(name=min_name)

        q = self.query(self.ciftbl)
        if list is not None:
            q = q.filter(self.ciftbl.c.amcsd_id.in_(list))

        ##  Searches mineral name for database entries
        if len(minerals) > 0:
            mids = [m.mineral_id for m in minerals]
            q = q.filter(self.ciftbl.c.mineral_id.in_(mids))
            for row in q.all():
                if row.amcsd_id not in out:
                    out.append(row.amcsd_id)
        return out

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


    def match_elements(self, elems, exclude=None):
        """match structues containing all elements in a list

        Arguments:
        ----------
        elems    list of elements to match
        exclude  list of elements to exclude for match (default None)

        Returns:
        --------
        list of amcsd ids for structures

        """
        matches = None
        q = self.query(self.compref)

        for elem in elems:
            elem = self.get_element(elem).z
            rows = q.filter(self.compref.c.z==elem).all()
            sids = [row.amcsd_id for row in rows]
            if matches is None:
                matches = sids
            else:
                matches = [s for s in sids if s in matches]

        if exclude is not None:
            for elem in exclude:
                elem = self.get_element(elem).z
                for row in q.filter(self.compref.c.z==elem).all():
                    if row.amcsd_id in matches:
                        matches.remove(row.amcsd_id)
        return matches

    def create_z_array(self,z):
        z_array = np.zeros((len(ELEMENTS)+1),dtype=int) ## + 1 gives index equal to z; z[0]:nothing
        for zn in z:
            z_array[zn] = 1
        return z_array


##################################################################################
##################################################################################
    def match_qc(self, list=None, qmin=QMIN, qmax=QMAX):

        if list is None:
            qqry = self.query(self.ciftbl.c.qstr).all()
            idqry = self.query(self.ciftbl.c.amcsd_id).all()
        else:
            qqry = self.query(self.ciftbl.c.qstr)\
                   .filter(self.ciftbl.c.amcsd_id.in_(list))\
                   .all()
            idqry = self.query(self.ciftbl.c.amcsd_id)\
                    .filter(self.ciftbl.c.amcsd_id.in_(list))\
                    .all()

        imin,imax = 0,len(self.axis)
        if qmax < QMAX: imax = abs(self.axis-qmax).argmin()
        if qmin > QMIN: imin = abs(self.axis-qmin).argmin()

        return [id[0] for id in idqry],[json.loads(q[0])[imin:imax] for q in qqry]

    def create_q_array(self, q):

        q_array = np.zeros(len(self.axis), dtype=int)
        for qn in q:
            i = np.abs(self.axis-qn).argmin()
            q_array[i] = 1
        return q_array

##################################################################################

    def get_element(self, element):
        '''
        searches elements for match in symbol, name, or atomic number;
        match must be exact.

        returns row with attributes  .z, .element_name, .element_symbol
        '''
        if isinstance(element, int):
            element = '%d' % element
        elif isinstance(element, str):
            element = element.title()
        q = self.query(self.elemtbl)
        row = q.filter(or_(self.elemtbl.c.z == element,
                           self.elemtbl.c.element_symbol == element,
                           self.elemtbl.c.element_name == element)).one()
        return row

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

        id, name = filter_int_and_str(name,exact=exact)
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

    def search_for_mineral(self, name=None, minid=None, exact=False):
        '''
        searches database for mineral by name or by ID

        Arguments:
        ----------
          name  (str or None): mineral name to match
          minid (int or None): mineral ID in database to match
          exact (bool):  whether to match name exactly [False]


        Returns:
        --------
        list of matching rows

        # [row.mineral_name, row.mineral_id]
        '''

        rows = []
        q = self.query(self.nametbl)

        if name is not None:
            if not exact:
                name = '%%%s%%' % name
            rows = q.filter(self.nametbl.c.mineral_name.like(name)).all()
        elif minid is not None:
            rows = q.filter(self.nametbl.c.mineral_id == minid).all()
        return rows

    def cif_count(self):
        return self.query(self.ciftbl).count()

    def return_q(self):
        q = [float(row.q) for row in self.query(self.qtbl).all()]
        return np.array(q)

    def get_mineral_names(self):
        names = []
        for name in self.query(self.nametbl.c.mineral_name).all():
            if isinstance(name[0], str):
                names.append(name[0])
        return sorted(names)

    def return_author_names(self):

        authorqry = self.query(self.authtbl)
        names = []
        for row in authorqry.all():
            names += [row.author_name]

        return sorted(names)

def filter_int_and_str(s, exact=False):
        try:
            i = int(s)
        except:
            i = 0
        if not exact:
            try:
                s = '%'+s+'%'
            except:
                pass
        return i, s


def column(matrix, i):
    return [row[i] for row in matrix]

class RangeParameter(object):
    def __init__(self,min=None,max=None,unit=None):
        self.min   = min
        self.max   = max
        self.unit  = unit

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
        self.allelem   = column(ELEMENTS, 2)

        self.lattice_keys = ['a', 'b', 'c', 'alpha', 'beta', 'gamma']

        self.sg    = None
        self.a     = RangeParameter()
        self.b     = RangeParameter()
        self.c     = RangeParameter()
        self.alpha = RangeParameter()
        self.beta  = RangeParameter()
        self.gamma = RangeParameter()


    def show_all(self):
        for key in ['authors','mnrlname','keywords','categories','amcsd','qpks']:
             print('%s : %s' % (key,self.show_parameter(key=key)))
        print('chemistry : %s' % self.show_chemistry())
        print('geometry : %s' % self.show_geometry())

    def show_parameter(self, key='authors'):
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

    def show_chemistry(self):

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

    def show_geometry(self,unit='A'):

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

def match_database(cifdb, peaks, minq=QMIN, maxq=QMAX, verbose=True):
    """
    fracq  : min. ratio of matched q to possible in q range, i.e. 'goodness gauge'
    pk_wid : maximum range in q which qualifies as a match between fitted and ideal
    """
    stepq = 0.05
    scores,amcsd,total_peaks,match_peaks,miss_peaks = zip(*cifdb.amcsd_by_q(peaks,
                                                       qmin=minq,qmax=maxq,qstep=stepq,
                                                       list=None,verbose=False))

    MATCHES = [match for i,match in enumerate(amcsd) if scores[i] > 0]

    if verbose:
        print('\n')
        if len(MATCHES) > 100:
            print('DISPLAYING TOP 100 of %i TOTAL MATCHES FOUND.' % len(MATCHES))
        else:
            print('%i TOTAL MATCHES FOUND.' % len(MATCHES))
        j = 0
        for i,id_no in enumerate(amcsd):
            if j < 100:
                if scores[i] > 0:
                    j += 1
                    str = 'AMCSD %5d, %s (score of %2d --> %i of %i peaks)' % (id_no,
                             cifdb.mineral_by_amcsd(id_no),scores[i],
                             match_peaks[i],total_peaks[i])
                    print(str)
        print('')

    return MATCHES


def cif_match(peaks, qmin=None, qmax=None, verbose=False, _larch=None):
    """
    fracq  : min. ratio of matched q to possible in q range, i.e. 'goodness gauge'
    pk_wid : maximum range in q which qualifies as a match between fitted and ideal
    """
    cifdb = get_cifdb(_larch=_larch)
    qstep = 0.05

    rows = cifdb.amcsd_by_q(peaks, qmin=qmin,qmax=qmax, qstep=qstep)

    scores, amcsd, total_peaks, match_peaks, miss_peaks = rows

    matches = []
    for i, cdat in enumerate(amcsd):
        if score[i] > 0:
            matches.append(cdat)

    if verbose:
        print('\n')
        if len(MATCHES) > 100:
            print('DISPLAYING TOP 100 of %i TOTAL MATCHES FOUND.' % len(MATCHES))
        else:
            print('%i TOTAL MATCHES FOUND.' % len(MATCHES))
        matches = matches[:100]
        for i, id_no in enumerate(amcsd):
            if j < 100:
                if scores[i] > 0:
                    j += 1
                    str = 'AMCSD %5d, %s (score of %2d --> %i of %i peaks)' % (id_no,
                             cifdb.mineral_by_amcsd(id_no),scores[i],
                             match_peaks[i],total_peaks[i])
                    print(str)
        print('')

    return matches


def read_cif(filename=None, amcsd_id=None, _larch=None):
    """make a representation of a CIF data structure
    for crystallographic computations

    Arguments:
    ----------
    filename  (str or None) name of CIF file
    amcsd_id  (int or None) index of CIF in Am Min Cystal Structure database

    Returns
    -------
    CIF representation
    """
    cifdb = get_cifdb(_larch=_larch)
    return create_cif(filename=filename, cifdb=cifdb, amcsd_id=amcsd_id)
