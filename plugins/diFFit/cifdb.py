#!/usr/bin/env python
'''
build American Mineralogist Crystal Structure Databse (amcsd)

'''

import sqlite3
import os
import json

import glob
import re
import math

import json

import xrayutilities as xu
import CifFile

import numpy as np

import sqlalchemy as sqal

from datetime import datetime

import time

import os
import time
import json
import six
import numpy as np
from scipy.interpolate import interp1d, splrep, splev, UnivariateSpline
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker, mapper, clear_mappers
from sqlalchemy.pool import SingletonThreadPool

# from ?? import PrimaryKeyConstraint

# needed for py2exe?
import sqlalchemy.dialects.sqlite
import larch
from larch_plugins.math import as_ndarray


def make_engine(dbname):
    return create_engine('sqlite:///%s' % (dbname),
                         poolclass=SingletonThreadPool)

def iscifDB(dbname):
    '''
    test if a file is a valid scan database:
    must be a sqlite db file, with tables named according to _tables
    '''
    _tables = ('allcif',
               'allelements',
               'allminerals',
               'allspacegroups',
               'allsymmetries',
               'allauthors',
               'qrange',
               'allcategories',
               'symmetry',
               'composition',
               'author',
               'qpeaks',
               'category')
    result = False
    try:
        engine = make_engine(dbname)
        meta = MetaData(engine)
        meta.reflect()
        result = all([t in meta.tables for t in _tables])
    except:
        pass
    return result

def json_encode(val):
    "simple wrapper around json.dumps"
    if val is None or isinstance(val, six.string_types):
        return val
    return  json.dumps(val)

class _BaseTable(object):
    "generic class to encapsulate SQLAlchemy table"
    def __repr__(self):
        el = getattr(self, 'element', '??')
        return "<%s(%s)>" % (self.__class__.__name__, el)

class CIFTable(_BaseTable):
    (amcsd_id, mineral_id, iuc_id, cif) = [None]*4

class AllElementsTable(_BaseTable):
    (atomic_no, name, symbol) = [None]*3

class AllMineralsTable(_BaseTable):
    (id,name) = [None]*2

class AllSpaceGroupsTable(_BaseTable):
    (iuc_id, hm_notation) = [None]*2

class AllSymmetriesTable(_BaseTable):
    (id, name) = [None]*2

class AllAuthorsTable(_BaseTable):
    (id,name) = [None]*2

class QRangeTable(_BaseTable):
    (id, q) = [None]*2

class AllCategoriesTable(_BaseTable):
    (id,name) = [None]*2

class SymmetryTable(_BaseTable):
    (iuc_id,symmetry_id) = [None]*2
    
class CompositionTable(_BaseTable):
    (atomic_no,amcsd_id) = [None]*2

class AuthorTable(_BaseTable):
    (author_id,amcsd_id) = [None]*2

class QPeaksTable(_BaseTable):
    (q_id,amcsd_id) = [None]*2

class CategoryTable(_BaseTable):
    (category_id,amcsd_id) = [None]*2


class cifDB(object):
    '''
    interface to the American Mineralogist Crystal Structure Database
    '''
    def __init__(self, dbname=None, read_only=True):

        ## This needs to be modified for creating new if does not exist.
        if not os.path.exists(dbname):
            parent, child = os.path.split(__file__)
            dbname = os.path.join(parent, dbname)
            if not os.path.exists(dbname):
                print("File '%s' not found; building a new database!" % dbname)
                self.build_new_database(name=dbname)
            else:
                if not iscifDB(dbname):
                    raise ValueError("'%s' is not a valid cif database file!" % dbname)

        print 'Ready to continue...'
        
        self.dbname = dbname
        self.engine = make_engine(dbname)
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

        print 'Now mapping...'
        mapper(CIFTable,                 tables['allcif'])
        mapper(AllElementsTable,         tables['allelements'])
        mapper(AllMineralsTable,         tables['allminerals'])
        mapper(AllSpaceGroupsTable,      tables['allspacegroups'])
        mapper(AllSymmetriesTable,       tables['allsymmetries'])
        mapper(AllAuthorsTable,          tables['allauthors'])
        mapper(QRangeTable,              tables['qrange'])
        mapper(AllCategoriesTable,       tables['allcategories'])
        mapper(SymmetryTable,            tables['symmetry'])
        mapper(CompositionTable,         tables['composition'])
        mapper(AuthorTable,              tables['author'])
        mapper(QPeaksTable,              tables['qpeaks'])
        mapper(CategoryTable,            tables['category'])

    def close(self):
        "close session"
        self.session.flush()
        self.session.close()

    def query(self, *args, **kws):
        "generic query"
        return self.session.query(*args, **kws)


    def open_database(self,dbname):

        print '\nAccessing database: %s' % dbname
        self.metadata = sqal.MetaData('sqlite:///%s' % dbname)
    
    def build_new_database(self,name=None):

        if name is None:
            dbname = 'amscd%02d.db'
            counter = 0
            while os.path.exists(dbname % counter):
                counter += 1
            dbname = dbname % counter
        else:
            dbname = name
    
        self.open_database(dbname)

        ###################################################
        ## Look up tables
        element_table = sqal.Table('allelements', self.metadata,
                sqal.Column('atomic_no', sqal.Integer, primary_key=True),
                sqal.Column('element_name', sqal.String(40), unique=True, nullable=True),
                sqal.Column('element_symbol', sqal.String(2), unique=True, nullable=False)
                )
        mineral_table = sqal.Table('allminerals', self.metadata,
                sqal.Column('mineral_id', sqal.Integer, primary_key=True),
                sqal.Column('mineral_name', sqal.String(30), unique=True, nullable=True)
                )
        spacegroup_table = sqal.Table('allspacegroups', self.metadata,
                sqal.Column('iuc_id', sqal.Integer, primary_key=True),
                sqal.Column('hm_notation', sqal.String(16), unique=True, nullable=True)
                )
        symmetry_table = sqal.Table('allsymmetries', self.metadata,
                sqal.Column('symmetry_id', sqal.Integer, primary_key=True),
                sqal.Column('symmetry_name', sqal.String(16), unique=True, nullable=True)
                )
        authorlist_table = sqal.Table('allauthors', self.metadata,
                sqal.Column('author_id', sqal.Integer, primary_key=True),
                sqal.Column('author_name', sqal.String(40), unique=True, nullable=True)
                )
        qrange_table = sqal.Table('qrange', self.metadata,
                sqal.Column('q_id', sqal.Integer, primary_key=True),
                #sqal.Column('q', sqal.Integer)
                sqal.Column('q', sqal.Float)
                )
        categorylist_table = sqal.Table('allcategories', self.metadata,
                sqal.Column('category_id', sqal.Integer, primary_key=True),
                sqal.Column('category_name', sqal.String(16), unique=True, nullable=True)
                )
        ###################################################
        ## Cross-reference tables
        geometry_table = sqal.Table('symmetry', self.metadata,
                sqal.Column('iuc_id', None, sqal.ForeignKey('allspacegroups.iuc_id')),
                sqal.Column('symmetry_id', None, sqal.ForeignKey('allsymmetries.symmetry_id')),
                sqal.PrimaryKeyConstraint('iuc_id', 'symmetry_id')
                )
        composition_table = sqal.Table('composition', self.metadata,
                sqal.Column('atomic_no', None, sqal.ForeignKey('allelements.atomic_no')),
                sqal.Column('amcsd_id', None, sqal.ForeignKey('allcif.amcsd_id')),
                sqal.PrimaryKeyConstraint('atomic_no', 'amcsd_id')
                )
        author_table = sqal.Table('author', self.metadata,
                sqal.Column('author_id', None, sqal.ForeignKey('allauthors.author_id')),
                sqal.Column('amcsd_id', None, sqal.ForeignKey('allcif.amcsd_id')),
                sqal.PrimaryKeyConstraint('author_id', 'amcsd_id')
                )
        qpeak_table = sqal.Table('qpeaks', self.metadata,
                sqal.Column('q_id', None, sqal.ForeignKey('qrange.q_id')),
                sqal.Column('amcsd_id', None, sqal.ForeignKey('allcif.amcsd_id')),
                sqal.PrimaryKeyConstraint('q_id', 'amcsd_id')
                )
        category_table = sqal.Table('category', self.metadata,
                sqal.Column('category_id', None, sqal.ForeignKey('allcategories.category_id')),
                sqal.Column('amcsd_id', None, sqal.ForeignKey('allcif.amcsd_id')),
                sqal.PrimaryKeyConstraint('category_id', 'amcsd_id')
                )
        ###################################################
        ## Main table
        cif_table = sqal.Table('allcif', self.metadata,
                sqal.Column('amcsd_id', sqal.Integer, primary_key=True),
                sqal.Column('mineral_id', sqal.Integer),
                sqal.Column('iuc_id', sqal.ForeignKey('allspacegroups.iuc_id')),
                sqal.Column('cifile', sqal.String(2500), nullable=True) ## later this should be false. mkak 2016.11.18
                )
        ###################################################
        ## Add all to file
        self.metadata.create_all()  ## if not exists function... can call even when already there

        ###################################################
        ## Define 'add/insert' functions for each table
        self.populate_elements   = element_table.insert()
        self.populate_symmetries = symmetry_table.insert()
        self.populate_q          = qrange_table.insert()
        self.populate_spgrp      = spacegroup_table.insert()

        self.correlate_geometry = geometry_table.insert()

        self.new_mineral  = mineral_table.insert()
        self.new_author   = authorlist_table.insert()
        # self.new_category = categorylist_table.insert()

        self.new_cif = cif_table.insert()

        self.cif_composition = composition_table.insert()
        self.cif_author      = author_table.insert()
        self.cif_qpeaks      = qpeak_table.insert()
        # self.cif_category    = category_table.insert()


        ###################################################
        ## Populate the fixed tables of the database

        ## Adds all elements into database
        with open('Database_Files/ALL_elements.txt', 'r') as efile:
            for element in efile:
                atomic_no, name, symbol = element.split()
                self.populate_elements.execute(atomic_no=int(atomic_no),
                                          element_name=name,
                                          element_symbol=symbol)

        ## Adds all crystal symmetries
        with open('Database_Files/ALL_crystal_symmetries.txt','r') as csfile:
            for symmetry_id,symmetry in enumerate(csfile):
                self.populate_symmetries.execute(symmetry_name=symmetry.strip())
                if symmetry.strip() == 'triclinic':      ## triclinic    :   1 -   2
                    for iuc_id in range(1,2+1):
                        self.correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
                elif symmetry.strip() == 'monoclinic':   ## monoclinic   :   3 -  15
                    for iuc_id in range(3,15+1):
                        self.correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
                elif symmetry.strip() == 'orthorhombic': ## orthorhombic :  16 -  74
                    for iuc_id in range(16,74+1):
                        self.correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
                elif symmetry.strip() == 'tetragonal':   ## tetragonal   :  75 - 142
                    for iuc_id in range(75,142+1):
                        self.correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
                elif symmetry.strip() == 'trigonal':     ## trigonal     : 143 - 167
                    for iuc_id in range(143,167+1):
                        self.correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
                elif symmetry.strip() == 'hexagonal':    ## hexagonal    : 168 - 194
                    for iuc_id in range(168,194+1):
                        self.correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
                elif symmetry.strip() == 'cubic':        ## cubic        : 195 - 230
                    for iuc_id in range(195,230+1):
                        self.correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))

        ## Adds qrange
        QMIN = 0.3
        QMAX = 8.0
        QSTEP = 0.01
        qrange = np.arange(QMIN,QMAX+QSTEP,QSTEP)
        for q in qrange:
            self.populate_q.execute(q=q)

        ## Adds all space groups AND cross-references 'symmetry' and 'spacegroup'
        with open('Database_Files/ALL_space_groups.txt','r') as sgfile:
            for sg in sgfile:
                row = [str(splits) for splits in sg.split('\t') if splits is not '' and splits not in '\n']
                iuc_id = int(row[0])
                name = row[1:][0]
                self.populate_spgrp.execute(iuc_id=str(iuc_id),hm_notation=name)
   

        ###################################################
        ## Populate the look-up tables of the database

        ## Adds all authors
        with open('Database_Files/ALL_authors.txt','r') as afile:
            for author in afile:
                self.new_author.execute(author_name=author.strip())

        ## Adds all mineral names   <---- should be checked and added to when importing new cif
        with open('Database_Files/ALL_mineral_names.txt','r') as mfile:
            for mineral in mfile:
                self.new_mineral.execute(mineral_name=mineral.strip())
 


    def load_database(self):

        ###################################################
        ## Look up tables
        self.allcif = sqal.Table('allcif', self.metadata)
        self.allelements = sqal.Table('allelements', self.metadata)
        self.allminerals = sqal.Table('allminerals', self.metadata)
        self.allspacegroups = sqal.Table('allspacegroups', self.metadata)
        self.allsymmetries = sqal.Table('allsymmetries', self.metadata)
        self.allauthors = sqal.Table('allauthors', self.metadata)
        self.qrange = sqal.Table('qrange', self.metadata)
        self.allcategories = sqal.Table('allcategories', self.metadata)

        ###################################################
        ## Cross-reference tables
        self.symmetry = sqal.Table('symmetry', self.metadata)
        self.composition = sqal.Table('composition', self.metadata)
        self.author = sqal.Table('author', self.metadata)
        self.qpeak = sqal.Table('qpeaks', self.metadata)
        self.category = sqal.Table('category', self.metadata)


    def add_cif_to_db(self,cifile,verbose=True):
    # ## Adds cifile into database
    # '''
    # When reading in new CIF:
    # -->  put entire cif into json - write 'cif' to 'cif data'
    # -->  read _database_code_amcsd - write 'amcsd_id' to 'cif data'
    # -->  read _chemical_name_mineral - find/add in' minerallist' - write 'mineral_id' to 'cif data'
    # -->  read _symmetry_space_group_name_H-M - find in 'spacegroup' - write iuc_id to 'cif data'
    # 
    # -->  read author name(s) - find/add in 'authorlist' - write 'author_id','amcsd_id' to 'author'
    # 
    # -->  read _chemical_formula_sum - write 'atomic_no','amcsd_id' to 'composition'
    # 
    # -->  calculate q - find each corresponding 'q_id' for all peaks - in write 'q_id','amcsd_id' to 'qpeak'
    # '''
        cf = CifFile.ReadCif(cifile)

        key = cf.keys()[0]

        ## Read icsd_id
        amcsd_id = None
        try:
            amcsd_id = int(cf[key][u'_database_code_icsd'])
        except:
            amcsd_id = int(cf[key][u'_database_code_amcsd'])

        ## Read elements
        ALLelements = cf[key][u'_chemical_formula_sum'].split()
        for e0,element in enumerate(ALLelements):
    #         element = re.sub(r"['+]", r"", element)
    #         element = re.sub(r"['-]", r"", element)
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

   
        ## generate hkl list
        hkllist = []
        maxhkl = 3
        for i in range(maxhkl):
            for j in range(maxhkl):
                for k in range(maxhkl):
                    if i+j+k > 0: # as long as h,k,l all positive, eliminates 0,0,0
                        hkllist.append([i,j,k])
        energy = 8048 # units eV

        QMIN = 0.3
        QMAX = 8.0
        QSTEP = 0.01

        try:
            cif = xu.materials.Crystal.fromCIF(cifile)
    
            qlist = cif.Q(hkllist)
            Flist = cif.StructureFactorForQ(qlist,energy)
    
            Fall = []
            qall = []
            for i,hkl in enumerate(hkllist):
                if np.abs(Flist[i]) > 0.01:
                    Fadd = np.abs(Flist[i])
                    qadd = round(np.linalg.norm(qlist[i]) / QSTEP) * QSTEP ## np.linalg.norm(qlist[i])
                    if qadd not in qall:
                        Fall.append(Fadd)
                        qall.append(qadd)
    #                    qstr = '%0.2f' % qadd

        except:
            print 'Error on file : %s' % os.path.split(cifile)[-1]
            return

        if verbose:
            self.print_cif_entry(amcds_id,ALLelements,mineral_name,iuc_id,authors,cifile=cifile)
        else:
            print 'File : %s' % os.path.split(cifile)[-1]

      
        
        self.load_database()
        
        ###################################################
        ## Define 'add/insert' functions for each table
        self.populate_elements   = self.allelements.insert()
        self.populate_symmetries = self.allsymmetries.insert()
        self.populate_q          = self.qrange.insert()
        self.populate_spgrp      = self.allspacegroups.insert()

        self.correlate_geometry = self.symmetry.insert()

        self.new_mineral  = self.allminerals.insert()
        self.new_author   = self.allauthors.insert()
        # self.new_category = self.allcategories.insert()

        self.new_cif = self.allcif.insert()

        self.cif_composition = self.composition.insert()
        self.cif_author      = self.author.insert()
        self.cif_qpeaks      = self.qpeak.insert()
        # self.cif_category    = self.category.insert()
        

        ## Find mineral_name
        match = False
        search_mineral = self.allminerals.select(self.allminerals.c.mineral_name == mineral_name)
        for row in search_mineral.execute():
            mineral_id = row.mineral_id
            match = True
        if match is False:
            self.new_mineral.execute(mineral_name=mineral_name)
            search_mineral = self.allminerals.select(self.allminerals.c.mineral_name == mineral_name)
            for row in search_mineral.execute():
                mineral_id = row.mineral_id
                match = True

        ## Find symmetry_name
        match = False
        search_spgrp = self.allspacegroups.select(self.allspacegroups.c.hm_notation == hm_notation)
        for row in search_spgrp.execute():
            iuc_id = row.iuc_id
            match = True
        if match is False:
            ## need a real way to deal with this trouble
            ## mkak 2016.11.04
            iuc_id = 0


        ## Add new entry for each cifile
        ## NEED CHECK TO SEE IF THIS amcsd_id/cif already exists in database
        ## mkak 2016.11.18
        with open(cifile,'r') as file:
    
#            cifstr = json.dumps(file.read()) 
            cifstr = None
    
            self.new_cif.execute(amcsd_id=int(amcsd_id),
                            mineral_id=int(mineral_id),
                            iuc_id=iuc_id,
                            cif=cifstr)    

        ## Find composition (loop over all elements)
        for element in ALLelements:
            search_elements = self.allelements.select(self.allelements.c.element_symbol == element)
            for row in search_elements.execute():
                atomic_no = row.atomic_no
            try:
                self.cif_composition.execute(atomic_no=atomic_no,
                                        amcsd_id=int(amcsd_id))
            except:
                print 'could not find element: ',element
                pass


        ## Find author_name
        for author_name in authors:
            match = False
            search_author = self.allauthors.select(self.allauthors.c.author_name == author_name)
            for row in search_author.execute():
                author_id = row.author_id
                match = True
            if match is False:
                self.new_author.execute(author_name=author_name)
                search_author = self.allauthors.select(self.allauthors.c.author_name == author_name)
                for row in search_author.execute():
                    author_id = row.author_id
                    match = True
            if match == True:
                self.cif_author.execute(author_id=author_id,
                                   amcsd_id=int(amcsd_id))

        ## Find q (loop over all peaks)
        for q in qall:
            calc_q_id = int(((q-QMIN)/QSTEP)+1)
            search_q = self.qrange.select(self.qrange.c.q_id == calc_q_id)
            for row in search_q.execute():
                q_id = row.q_id
                self.cif_qpeaks.execute(q_id=q_id,
                                   amcsd_id=int(amcsd_id))


    #     ## not ready for defined categories
    #     cif_category.execute(category_id='none',
    #                          amcsd_id=int(amcsd_id))




    def find_by_amcsd(self,amcsd_id):

        search_mineral = cif_table.select(cif_table.c.amcsd_id == amcsd_id)
        for row in search_mineral.execute():
            cifile = row.cif
            mineral_id = row.mineral_id
            iuc_id = row.iuc_id
        search_mineralname = mineral_table.select(mineral_table.c.mineral_id == mineral_id)
        for row in search_mineralname.execute():
            mineral_name = row.mineral_name
        search_composition = composition_table.select(composition_table.c.amcsd_id == amcsd_id)
        ALLelements = []
        for row in search_composition.execute():
            atomic_no = row.atomic_no
            search_periodic = element_table.select(element_table.c.atomic_no == atomic_no)
            for block in search_periodic.execute():
                ALLelements.append(block.element_symbol)
        search_authors = author_table.select(author_table.c.amcsd_id == amcsd_id)
        authors = []
        for row in search_authors.execute():
            author_id = row.author_id
            search_alist = authorlist_table.select(authorlist_table.c.author_id == author_id)
            for block in search_alist.execute():
                authors.append(block.author_name)
        
        print_cif_entry(amcds_id,ALLelements,mineral_name,iuc_id,authors)


    def print_cif_entry(self,amcds_id,ALLelements,mineral_name,iuc_id,authors,cifile=None):

        if cifile:
            print ' ==== File : %s ====' % os.path.split(cifile)[-1] 
        else:
            print ' ===================== '
        print 'AMCSD: %i' % amcsd_id

        elementstr = 'Elements: '
        for element in ALLelements:
            elementstr = '%s %s' % (elementstr,element)
        print elementstr
        print 'Name: %s' % mineral_name
        print 'Space Group No.: %s' % iuc_id
        authorstr = 'Author: '
        for author in authors:
            authorstr = '%s %s' % (authorstr,author.split()[0])
        print authorstr
        print ' ===================== '
        print



# mycifdatabase = cifDB(dbname='new_amscd.db')
# 
# 
# #######################################
# ######  TEST ADDING CIF DATABASE 
# #######################################
# print '\n\n\n\n -------- GOING TO READ CIF NOW ---------- '
# 
# cifpath = '/Users/koker/Data/XRMMappingCode/Search_and_Match/practice/cif_stuff'
# cifiles = glob.glob('%s/*.cif' % cifpath)
# for file in cifiles:
#     mycifdatabase.add_cif_to_db(file,verbose=False)
# 
# cifpath = '/Users/koker/Data/XRMMappingCode/Search_and_Match/practice/cif_stuff/Clays_Cif'
# cifiles = glob.glob('%s/*.cif' % cifpath)
# for file in cifiles:
#     mycifdatabase.add_cif_to_db(file,verbose=False)
# 
# # cifile = '/Users/koker/Data/XRMMappingCode/Search_and_Match/practice/cif_stuff/CsCl.cif'
# # mycifdatabase.add_cif_to_db(cifile,verbose=True)
