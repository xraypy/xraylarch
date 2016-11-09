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


QMIN = 0.3
QMAX = 8.0
QSTEP = 0.01

def open_database(dbname):

    print '\nDatabase: %s' % dbname
    metadata = sqal.MetaData('sqlite:///%s' % dbname)
    
    return metadata

def build_new_database(name=None):

    if name is None:
        dbname = 'amscd%02d.db'
        counter = 0
        while os.path.exists(dbname % counter):
            counter += 1
        dbname = dbname % counter
    else:
        dbname = name
    
    metadata = open_database(dbname)

    ###################################################
    ## Look up tables
    mineral_table = sqal.Table('mineral', metadata,
            sqal.Column('amcsd_id', sqal.Integer, primary_key=True),
            sqal.Column('mineral_id', sqal.Integer),
            sqal.Column('iuc_id', sqal.Integer),
            #sqal.Column('cif', sqal.JSON)
            sqal.Column('cif', sqal.String(2500), nullable=False)
            #sqal.Column('cif', sqal.Unicode(255), nullable=False)
            )
    element_table = sqal.Table('element', metadata,
            sqal.Column('atomic_no', sqal.Integer, primary_key=True),
            sqal.Column('element_name', sqal.String(40), unique=True, nullable=True),
            sqal.Column('element_symbol', sqal.String(2), unique=True, nullable=False)
            )
    minerallist_table = sqal.Table('minerallist', metadata,
            sqal.Column('mineral_id', sqal.Integer, primary_key=True),
            sqal.Column('mineral_name', sqal.String(30), unique=True, nullable=True)
            )
    spacegroup_table = sqal.Table('spacegroup', metadata,
            sqal.Column('iuc_id', sqal.Integer),
            sqal.Column('hm_notation', sqal.String(16), unique=True, nullable=True)
            )
    symmetry_table = sqal.Table('symmetry', metadata,
            sqal.Column('symmetry_id', sqal.Integer, primary_key=True),
            sqal.Column('symmetry_name', sqal.String(16), unique=True, nullable=True)
            )
    authorlist_table = sqal.Table('authorlist', metadata,
            sqal.Column('author_id', sqal.Integer, primary_key=True),
            sqal.Column('author_name', sqal.String(40), unique=True, nullable=True)
            )
    qrange_table = sqal.Table('qrange', metadata,
            sqal.Column('q_id', sqal.Integer, primary_key=True),
            sqal.Column('q', sqal.Integer)
            #sqal.Column('q', sqal.Float)
            )
    # categorylist_table = sqal.Table('categorylist', metadata,
    #         sqal.Column('category_id', sqal.Integer, primary_key=True),
    #         sqal.Column('category_name', sqal.String(16), unique=True, nullable=True)
    #         )

    ###################################################
    ## Cross-reference tables
    geometry_table = sqal.Table('geometry', metadata,
            sqal.Column('iuc_id', None, sqal.ForeignKey('spacegroup.iuc_id')),
            sqal.Column('symmetry_id', None, sqal.ForeignKey('symmetry.symmetry_id'))
            )
    composition_table = sqal.Table('composition', metadata,
            sqal.Column('atomic_no', None, sqal.ForeignKey('element.atomic_no')),
            sqal.Column('amcsd_id', None, sqal.ForeignKey('mineral.amcsd_id'))
            )
    author_table = sqal.Table('author', metadata,
            sqal.Column('author_id', None, sqal.ForeignKey('authorlist.author_id')),
            sqal.Column('amcsd_id', None, sqal.ForeignKey('mineral.amcsd_id'))
            )
    qpeak_table = sqal.Table('qpeak', metadata,
            sqal.Column('q_id', None, sqal.ForeignKey('qrange.q_id')),
            sqal.Column('amcsd_id', None, sqal.ForeignKey('mineral.amcsd_id'))
            )
    # category_table = sqal.Table('category', metadata,
    #         sqal.Column('category_id', None, sqal.ForeignKey('categorylist.category_id')),
    #         sqal.Column('amcsd_id', None, sqal.ForeignKey('mineral.amcsd_id'))
    #         )

    ###################################################
    ## Add all to file
    metadata.create_all()  ## if not exists function... can call even when already there

    ###################################################
    ## Define 'add/insert' functions for each table

    populate_elements   = element_table.insert()
    populate_symmetries = symmetry_table.insert()
    populate_q          = qrange_table.insert()
    populate_spgrp      = spacegroup_table.insert()

    correlate_geometry = geometry_table.insert()

    new_mineral  = minerallist_table.insert()
    new_author   = authorlist_table.insert()
    # new_category = categorylist_table.insert()

    new_cif = mineral_table.insert()

    cif_composition = composition_table.insert()
    cif_author      = author_table.insert()
    cif_qpeaks      = qpeak_table.insert()
    # cif_category    = category_table.insert()


    ###################################################
    ## Populate the fixed tables of the database

    ## Adds all elements into database
    with open('Database_Files/ALL_elements.txt', 'r') as efile:
        for element in efile:
            atomic_no, name, symbol = element.split()
            populate_elements.execute(atomic_no=int(atomic_no),
                                      element_name=name,
                                      element_symbol=symbol)

    ## Adds all crystal symmetries
    with open('Database_Files/ALL_crystal_symmetries.txt','r') as csfile:
        for symmetry_id,symmetry in enumerate(csfile):
            populate_symmetries.execute(symmetry_name=symmetry.strip())
            if symmetry.strip() == 'triclinic':      ## triclinic    :   1 -   2
                for iuc_id in range(1,2+1):
                    correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'monoclinic':   ## monoclinic   :   3 -  15
                for iuc_id in range(3,15+1):
                    correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'orthorhombic': ## orthorhombic :  16 -  74
                for iuc_id in range(16,74+1):
                    correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'tetragonal':   ## tetragonal   :  75 - 142
                for iuc_id in range(75,142+1):
                    correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'trigonal':     ## trigonal     : 143 - 167
                for iuc_id in range(143,167+1):
                    correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'hexagonal':    ## hexagonal    : 168 - 194
                for iuc_id in range(168,194+1):
                    correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))
            elif symmetry.strip() == 'cubic':        ## cubic        : 195 - 230
                for iuc_id in range(195,230+1):
                    correlate_geometry.execute(iuc_id=iuc_id,symmetry_id=(symmetry_id+1))

    ## Adds qrange
    qrange = np.arange(QMIN,QMAX+QSTEP,QSTEP)
    for q in qrange:
        populate_q.execute(q=q)
    # populate_q.execute(q=q for q in qrange)


    ## Adds all space groups AND cross-references 'symmetry' and 'spacegroup'
    with open('Database_Files/ALL_space_groups.txt','r') as sgfile:
        for sg in sgfile:
            row = [str(splits) for splits in sg.split('\t') if splits is not '' and splits not in '\n']
            iuc_id = int(row[0])
            for name in row[1:]:
                populate_spgrp.execute(iuc_id=str(iuc_id),hm_notation=name)

    

    ###################################################
    ## Populate the look-up tables of the database

    ## Adds all authors
    with open('Database_Files/ALL_authors.txt','r') as afile:
        for author in afile:
            new_author.execute(author_name=author.strip())
        # new_author.execute(author_name=author.strip() for author in afile)


    ## Adds all mineral names   <---- should be checked and added to when importing new cif
    with open('Database_Files/ALL_mineral_names.txt','r') as mfile:
        for mineral in mfile:
            new_mineral.execute(mineral_name=mineral.strip())
        # new_mineral.execute(mineral_name=mineral.strip() for mineral in mfile)

    return metadata


def load_database(metadata):

    ###################################################
    ## Look up tables
    mineral_table = sqal.Table('mineral', metadata)
    element_table = sqal.Table('element', metadata)
    minerallist_table = sqal.Table('minerallist', metadata)
    spacegroup_table = sqal.Table('spacegroup', metadata)
    symmetry_table = sqal.Table('symmetry', metadata)
    authorlist_table = sqal.Table('authorlist', metadata)
    qrange_table = sqal.Table('qrange', metadata)
    # categorylist_table = sqal.Table('categorylist', metadata)

    ###################################################
    ## Cross-reference tables
    geometry_table = sqal.Table('geometry', metadata)
    composition_table = sqal.Table('composition', metadata)
    author_table = sqal.Table('author', metadata)
    qpeak_table = sqal.Table('qpeak', metadata)
    
    return

def add_cif_to_db(cifile,metadata,verbose=True):
# ## Adds cifile into database
# '''
# When reading in new CIF:
# -->  put entire cif into json - write 'cif' to 'mineral'
# -->  read _database_code_amcsd - write 'amcsd_id' to 'mineral'
# -->  read _chemical_name_mineral - find/add in' minerallist' - write 'mineral_id' to 'mineral'
# -->  read _symmetry_space_group_name_H-M - find in 'spacegroup' - write iuc_id to 'mineral'
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
        print_cif_entry(amcds_id,ALLelements,mineral_name,iuc_id,authors,cifile=cifile)
    else:
        print 'File : %s' % os.path.split(cifile)[-1]

    
    ## Find mineral_name
    match = False
    search_mineral = minerallist_table.select(minerallist_table.c.mineral_name == mineral_name)
    for row in search_mineral.execute():
        mineral_id = row.mineral_id
        match = True
    if match is False:
        new_mineral.execute(mineral_name=mineral_name)
        search_mineral = minerallist_table.select(minerallist_table.c.mineral_name == mineral_name)
        for row in search_mineral.execute():
            mineral_id = row.mineral_id
            match = True

    ## Find symmetry_name
    match = False
    search_spgrp = spacegroup_table.select(spacegroup_table.c.hm_notation == hm_notation)
    for row in search_spgrp.execute():
        iuc_id = row.iuc_id
        match = True
    if match is False:
        ## need a real way to deal with this trouble
        ## mkak 2016.11.04
        iuc_id = 0


    ## Add new entry for each cifile
    with open(cifile,'r') as file:
        
        cifstr = json.dumps(file.read()) 
        
        new_cif.execute(amcsd_id=int(amcsd_id),
                        mineral_id=int(mineral_id),
                        iuc_id=iuc_id,
                        cif=cifstr)    

    ## Find composition (loop over all elements)
    for element in ALLelements:
        search_elements = element_table.select(element_table.c.element_symbol == element)
        for row in search_elements.execute():
            atomic_no = row.atomic_no
        try:
            cif_composition.execute(atomic_no=atomic_no,
                                    amcsd_id=int(amcsd_id))
        except:
            print 'could not find element: ',element
            pass
    

    ## Find author_name
    for author_name in authors:
        match = False
        search_author = authorlist_table.select(authorlist_table.c.author_name == author_name)
        for row in search_author.execute():
            author_id = row.author_id
            match = True
        if match is False:
            new_author.execute(author_name=author_name)
            search_author = authorlist_table.select(authorlist_table.c.author_name == author_name)
            for row in search_author.execute():
                author_id = row.author_id
                match = True
        if match == True:
            cif_author.execute(author_id=author_id,
                               amcsd_id=int(amcsd_id))

    ## Find q (loop over all peaks)
    for q in qall:
        calc_q_id = int(((q-QMIN)/QSTEP)+1)
        search_q = qrange_table.select(qrange_table.c.q_id == calc_q_id)
        for row in search_q.execute():
            q_id = row.q_id
            cif_qpeaks.execute(q_id=q_id,
                               amcsd_id=int(amcsd_id))


#     ## not ready for defined categories
#     cif_category.execute(category_id='none',
#                          amcsd_id=int(amcsd_id))




def find_by_amcsd(amcsd_id,metadata):

    search_mineral = mineral_table.select(mineral_table.c.amcsd_id == amcsd_id)
    for row in search_mineral.execute():
        cifile = row.cif
        mineral_id = row.mineral_id
        iuc_id = row.iuc_id
    search_mineralname = minerallist_table.select(minerallist_table.c.mineral_id == mineral_id)
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


def print_cif_entry(amcds_id,ALLelements,mineral_name,iuc_id,authors,cifile=None):

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




#######################################
######  TEST BUILDING DATABASE 
#######################################
# metadata = build_new_database()

#######################################
######  TEST OPENING DATABASE 
#######################################
dbname = 'amscd00.db'
metadata = open_database(dbname)
load_database(metadata)

#######################################
######  TEST ADDING CIF DATABASE 
#######################################
print '\n\n\n\n -------- GOING TO READ CIF NOW ---------- '

cifpath = '/Users/koker/Data/XRMMappingCode/Search_and_Match/practice/cif_stuff'
cifiles = glob.glob('%s/*.cif' % cifpath)
for file in cifiles:
    t0 = time.time()
    add_cif_to_db(file,metadata,verbose=False)
#    print '\tTOOK %0.2f s' % (time.time()-t0)

cifpath = '/Users/koker/Data/XRMMappingCode/Search_and_Match/practice/cif_stuff/Clays_Cif'
cifiles = glob.glob('%s/*.cif' % cifpath)
for file in cifiles:
    t0 = time.time()
    add_cif_to_db(file,metadata,verbose=False)
#    print '\tTOOK %0.2f s' % (time.time()-t0)

# t0 = time.time()
# cifile = '/Users/koker/Data/XRMMappingCode/Search_and_Match/practice/cif_stuff/CsCl.cif'
# add_cif_to_db(cifile,verbose=True)
# print 'TOOK %0.2f s' % (time.time()-t0)

#######################################
######   TEST ACCESSING DATA
#######################################

find_by_amcsd(213)
find_by_amcsd(392)
find_by_amcsd(12232)














