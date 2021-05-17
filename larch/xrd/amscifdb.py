#!/usr/bin/env python
"""
AMCIFDB: American Mineralogical CIF database as sqlite3 database/python

Usage:
   amcifdb = AMCIFDB('amcif.db')

add a CIF file:
  amcifdb.add_ciffile('NewFile.cif')

generatt the text of a CIF file from index:
  cif_text = amcifdb.get_ciftext(300)

OK, that looks like "well, why not just save the CIF files"?


"""

import os
import json
from base64 import b64encode, b64decode
from collections import namedtuple
import numpy as np

from sqlalchemy import MetaData, create_engine, func, text, and_
from sqlalchemy.sql import select
from sqlalchemy.orm import sessionmaker

try:
    from pymatgen.io.cif import CifParser
    HAS_CIFPARSER = True
except IOError:
    HAS_CIFPARSER = False

from xraydb.chemparser import chemparse

from amscifdb_utils import (make_engine, isAMSCIFDB, create_amscifdb,
                            put_optarray, get_optarray)


CifPublication = namedtuple('CifPublication', ('id', 'journalname', 'year',
                                            'volume', 'page_first',
                                            'page_last', 'authors'))


class CifStructure():

    def __init__(self, ams_id=None, publication=None, mineral=None,
                 spacegroup=None, hm_symbol=None, formula_title=None,
                 compound=None, formula=None, pub_title=None, a=None,
                 b=None, c=None, alpha=None, beta=None, gamma=None,
                 cell_volume=None, crystal_density=None, atoms_sites='<missing>',
                 atoms_aniso_label='<missing>', atoms_x=None, atoms_y=None,
                 atoms_z=None, atoms_occupancy=None, atoms_u_iso=None,
                 atoms_aniso_u11=None, atoms_aniso_u22=None,
                 atoms_aniso_u33=None, atoms_aniso_u12=None,
                 atoms_aniso_u13=None, atoms_aniso_u23=None):

        self.ams_id = ams_id
        self.publication = publication
        self.mineral = mineral
        self.spacegroup = spacegroup
        self.hm_symbol = hm_symbol
        self.formula_title = formula_title
        self.compound = compound
        self.formula = formula
        self.pub_title = pub_title
        self.a = a
        self.b = b
        self.c = c
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.cell_volume = cell_volume
        self.crystal_density = crystal_density
        self.atoms_sites = atoms_sites
        self.atoms_aniso_label = atoms_aniso_label
        self.atoms_x = atoms_x
        self.atoms_y = atoms_y
        self.atoms_z = atoms_z
        self.atoms_occupancy = atoms_occupancy
        self.atoms_u_iso = atoms_u_iso
        self.atoms_aniso_u11 = atoms_aniso_u11
        self.atoms_aniso_u22 = atoms_aniso_u22
        self.atoms_aniso_u33 = atoms_aniso_u33
        self.atoms_aniso_u12 = atoms_aniso_u12
        self.atoms_aniso_u13 = atoms_aniso_u13
        self.atoms_aniso_u23 = atoms_aniso_u23
        self.natoms = 0
        if atoms_sites not in (None, '<missing>'):
            self.natoms = len(atoms_sites)


class AMSCIFDB():
    """
    Database of CIF structure data from the American Mineralogical Crystal Structure Database

       http://rruff.geo.arizona.edu/AMS/amcsd.php

    """
    def __init__(self, dbname='amscif.db', read_only=False):
        "connect to an existing database"
        if not os.path.exists(dbname):
            parent, _ = os.path.split(__file__)
            dbname = os.path.join(parent, dbname)
            if not os.path.exists(dbname):
                raise IOError("Database '%s' not found!" % dbname)

        if not isAMSCIFDB(dbname):
            raise ValueError("'%s' is not a valid AMSCIF Database!" % dbname)

        self.dbname = dbname
        self.engine = make_engine(dbname)
        self.conn = self.engine.connect()
        kwargs = {}
        if read_only:
            kwargs = {'autoflush': True, 'autocommit': False}
            def readonly_flush(*args, **kwargs):
                return
            self.session = sessionmaker(bind=self.engine, **kwargs)()
            self.session.flush = readonly_flush
        else:
            self.session = sessionmaker(bind=self.engine)()

        self.metadata = MetaData(self.engine)
        self.metadata.reflect()
        self.tables = self.metadata.tables
        elems = self.tables['elements'].select().execute()

    def close(self):
        "close session"
        self.session.flush()
        self.session.close()

    def query(self, *args, **kws):
        "generic query"
        return self.session.query(*args, **kws)

    def get_version(self, long=False, with_history=False):
        """
        return sqlite3 database and python library version numbers

        Parameters:
            long (bool): show timestamp and notes of latest version [False]
            with_history (bool): show complete version history [False]

        Returns:
            string: version information
        """
        out = []
        rows = self.tables['Version'].select().execute().fetchall()
        if not with_history:
            rows = rows[-1:]
        if long or with_history:
            for row in rows:
                out.append(f"AMSCIF DB Version: {row.tag} [{row.date}] '{row.notes}'")
            out.append(f"Python Version: {__version__}")
            out = "\n".join(out)
        else:
            out = f"AMSCIF DB Version: {rows[0].tag}, Python Version: {__version__}"
        return out

    def _get_tablerow(self, table, name, add=True):
        tab = self.tables[table]
        if '"' in name:
            name = name.replace('"', '\"')
        rows = tab.select(tab.c.name==name).execute().fetchall()
        if len(rows) == 0:
            if not add:
                return None
            tab.insert().execute(name=name)
            rows = tab.select(tab.c.name==name).execute().fetchall()
        return rows[0]


    def get_spacegroup(self, hm_name):
        """get row from spacegroups table by HM notation.  See add_spacegroup()
        """
        tab = self.tables['spacegroups']
        rows = tab.select(tab.c.hm_notation==hm_name).execute().fetchall()
        if len(rows) >0:
            return rows[0]
        return None


    def add_spacegroup(self, hm_name, symmetry_xyz, category=None):
        """add entry to spacegroups table, including HM notation and CIF symmetry operations
        """                        
        sg = self.get_spacegroup(hm_name)
        if sg is not None and sg.symmetry_xyz == symmetry_xyz:
            return sg

        tab = self.tables['spacegroups']
        args = {'hm_notation': hm_name, 'symmetry_xyz': symmetry_xyz}
        if category is not None:
            args['category'] = category
        tab.insert().execute(**args)
        return self.get_spacegroup(hm_name)

    def get_publications(self, journalname=None, year=None, volume=None,
                        page_first=None, page_last=None, id=None): 
        """get rows from publications table by journalname, year (required)
        and optionally volume, page_first, or page_last.
        """                       
        tab = self.tables['publications']

        args = []
        if journalname is not None:
            args.append(func.lower(tab.c.journalname)==journalname.lower())
        if year is not None:
            args.append(tab.c.year==int(year))
        if volume is not None:
            args.append(tab.c.volume==str(volume))
        if page_first is not None:
            args.append(tab.c.page_first==str(page_first))
        if page_last is not None:
            args.append(tab.c.page_last==str(page_last))
        if id is not None:
            args.append(tab.c.id==id)

        rows = tab.select(and_(*args)).execute().fetchall()
        if len(rows) > 0:
            out = []
            authtab = self.tables['authors']
            patab = self.tables['publication_authors']
            for row in rows:
                q = select(authtab.c.name).where(and_(authtab.c.id==patab.c.author_id, 
                                                      patab.c.publication_id==row.id))
                authors = tuple([i[0] for i in self.conn.execute(q).fetchall()])
                out.append(CifPublication(row.id, row.journalname, row.year,
                                          row.volume, row.page_first,
                                          row.page_last, authors))
            return out
        return None


    def add_publication(self, journalname, year, authorlist, volume=None,
                        page_first=None, page_last=None, with_authors=True):

        tab = self.tables['publications']
        args = dict(journalname=journalname, year=year)
        if volume is not None:
            args['volume']  = volume
        if page_first is not None:
            args['page_first'] = page_first
        if page_last is not None:
            args['page_last'] = page_last

        tab.insert().execute(**args)
        self.session.flush()
        pub = self.get_publications(journalname, year, volume=volume,
                                    page_first=page_first,
                                    page_last=page_last)[0]

        if with_authors:
            vals = []
            for name in authorlist:
                auth = self._get_tablerow('authors', name, add=True)
                vals.append(dict(publication_id=pub.id, author_id=auth.id))
            self.tables['publication_authors'].insert().values(vals).execute()
        return pub

    def add_cifdata(self, cif_id, mineral_id, publication_id,
                    spacegroup_id, formula=None, compound=None,
                    formula_title=None, pub_title=None, a=None, b=None,
                    c=None, alpha=None, beta=None, gamma=None, url=None,
                    cell_volume=None, crystal_density=None,
                    atoms_sites=None, atoms_x=None, atoms_y=None,
                    atoms_z=None, atoms_occupancy=None, atoms_u_iso=None,
                    atoms_aniso_label=None, atoms_aniso_u11=None,
                    atoms_aniso_u22=None, atoms_aniso_u33=None,
                    atoms_aniso_u12=None, atoms_aniso_u13=None,
                    atoms_aniso_u23=None, with_elements=True):

        tab = self.tables['cif']

        tab.insert().execute(id=cif_id, mineral_id=mineral_id,
                             publication_id=publication_id,
                             spacegroup_id=spacegroup_id,
                             formula_title=formula_title,
                             pub_title=pub_title, formula=formula,
                             compound=compound, url=url, a=a, b=b, c=c,
                             alpha=alpha, beta=beta, gamma=gamma,
                             cell_volume=cell_volume,
                             crystal_density=crystal_density,
                             atoms_sites=atoms_sites, atoms_x=atoms_x,
                             atoms_y=atoms_y, atoms_z=atoms_z,
                             atoms_occupancy=atoms_occupancy,
                             atoms_u_iso=atoms_u_iso,
                             atoms_aniso_label=atoms_aniso_label,
                             atoms_aniso_u11=atoms_aniso_u11,
                             atoms_aniso_u22=atoms_aniso_u22,
                             atoms_aniso_u33=atoms_aniso_u33,
                             atoms_aniso_u12=atoms_aniso_u12,
                             atoms_aniso_u13=atoms_aniso_u13,
                             atoms_aniso_u23=atoms_aniso_u23)

        if with_elements:
            vals = []
            for element in chemparse(formula).keys():
                vals.append(dict(cif_id=cif_id, element=element))
            self.tables['cif_elements'].insert().values(vals).execute()
        return self.get_cif(cif_id)


    def add_ciffile(self, filename, url=''):
        if not HAS_CIFPARSER:
            raise ValueError("CifParser from pymatgen not available. Try 'pip install pymatgen'.")
        cif = CifParser(filename)
        dat = cif._cif.data['global'].data
        formula = dat['_chemical_formula_sum']
        compound  = dat.get('_chemical_compound_source', '<missing>')

        # get spacegroup and symmetry
        sgroup_name = dat['_symmetry_space_group_name_H-M']
        symm_xyz = json.dumps(dat['_space_group_symop_operation_xyz'])

        sgroup = self.get_spacegroup(sgroup_name)
        if sgroup is not None and sgroup.symmetry_xyz != symm_xyz:
            for i in range(1, 11):
                tgroup_name = sgroup_name + f' %var{i:d}%'
                sgroup = self.get_spacegroup(tgroup_name)
                if sgroup is None or sgroup.symmetry_xyz == symm_xyz:
                    sgroup_name = tgroup_name
                    break
        if sgroup is None:
            sgroup = self.add_spacegroup(sgroup_name, symm_xyz)

        min_name = dat.get('_chemical_name_mineral', '<missing>')
        mineral = self._get_tablerow('minerals', min_name)

        pubs = self.get_publications(journalname=dat['_journal_name_full'],
                                    year=dat['_journal_year'],
                                    volume=dat['_journal_volume'],
                                    page_first=dat['_journal_page_first'],
                                    page_last=dat['_journal_page_last'])
        
        if pubs is None:
            pub = self.add_publication(dat['_journal_name_full'],
                                       dat['_journal_year'],
                                       dat['_publ_author_name'],
                                       volume=dat['_journal_volume'],
                                       page_first=dat['_journal_page_first'],
                                       page_last=dat['_journal_page_last'])
        else:
            pub = pubs[0]


        cif_id = int(dat['_database_code_amcsd'])
        self.add_cifdata(cif_id, mineral.id, pub.id, sgroup.id,
                         formula=formula, compound=compound,
                         formula_title=dat.get('_amcsd_formula_title', '<missing>'),
                         pub_title=dat['_publ_section_title'],
                         atoms_sites=json.dumps(dat['_atom_site_label']),
                         atoms_x=put_optarray(dat, '_atom_site_fract_x'),
                         atoms_y=put_optarray(dat, '_atom_site_fract_y'),
                         atoms_z=put_optarray(dat, '_atom_site_fract_z'),
                         atoms_occupancy=put_optarray(dat, '_atom_site_occupancy'),
                         atoms_u_iso=put_optarray(dat, '_atom_site_U_iso_or_equiv'),
                         atoms_aniso_label=json.dumps(dat.get('_atom_site_aniso_label', '<missing>')),
                         atoms_aniso_u11=put_optarray(dat, '_atom_site_aniso_U_11'),
                         atoms_aniso_u22=put_optarray(dat, '_atom_site_aniso_U_22'),
                         atoms_aniso_u33=put_optarray(dat, '_atom_site_aniso_U_33'),
                         atoms_aniso_u12=put_optarray(dat, '_atom_site_aniso_U_12'),
                         atoms_aniso_u13=put_optarray(dat, '_atom_site_aniso_U_13'),
                         atoms_aniso_u23=put_optarray(dat, '_atom_site_aniso_U_23'),
                         a=dat['_cell_length_a'],
                         b=dat['_cell_length_b'],
                         c=dat['_cell_length_c'],
                         alpha=dat['_cell_angle_alpha'],
                         beta=dat['_cell_angle_beta'],
                         gamma=dat['_cell_angle_gamma'],
                         cell_volume=dat['_cell_volume'],
                         crystal_density=dat['_exptl_crystal_density_diffrn'],
                         url=url)


    def get_cif(self, cif_id, as_strings=False):
        """get Cif Structure object """
        tab = self.tables['cif']
        cif = tab.select(tab.c.id==cif_id).execute().fetchone()
        if cif is None:
            return

        tab_pub  = self.tables['publications']
        tab_auth = self.tables['authors']
        tab_pa   = self.tables['publication_authors']
        tab_min  = self.tables['minerals']
        tab_sp   = self.tables['spacegroups']
        mineral  = tab_min.select(tab_min.c.id==cif.mineral_id).execute().fetchone()
        sgroup   = tab_sp.select(tab_sp.c.id==cif.spacegroup_id).execute().fetchone()
        hm_symbol = sgroup.hm_notation
        if '%var' in hm_symbol:
            hm_symbol = hm_symbol.split('%var')[0]

        pub = self.get_publications(id=cif.publication_id)[0]

        out = CifStructure(ams_id=cif_id, publication=pub,
                           mineral=mineral, spacegroup=sgroup,
                           hm_symbol=hm_symbol)

        for attr in ('formula_title', 'compound', 'formula', 'pub_title'):
            setattr(out, attr, getattr(cif, attr, '<missing>'))
        for attr in ('a', 'b', 'c', 'alpha', 'beta', 'gamma',
                     'cell_volume', 'crystal_density'):
            val = getattr(cif, attr, '-1')
            if not as_strings:
                try:
                    val = float(val)
                except:
                    if ',' in val and '.' not in val:
                        val = val.replace(',', '.')
                        try:
                            val = float(val)
                        except:
                            pass
            setattr(out, attr, val)

        for attr in ('atoms_sites', 'atoms_aniso_label'):
            val = getattr(cif, attr, '<missing>')
            val = '<missing>' if val in (None, '<missing>') else json.loads(val)
            setattr(out, attr, val)

        if out.atoms_sites not in (None, '<missing>'):
            out.natoms = len(out.atoms_sites)
            for attr in ('atoms_x', 'atoms_y', 'atoms_z', 'atoms_occupancy',
                         'atoms_u_iso', 'atoms_aniso_u11', 'atoms_aniso_u22',
                         'atoms_aniso_u33', 'atoms_aniso_u12',
                         'atoms_aniso_u13', 'atoms_aniso_u23'):
                val =  get_optarray(getattr(cif, attr))
                if not as_strings and '?' not in val:
                    val = np.array([float(v) for v in val])
                setattr(out, attr, val)

        out.qval = None
        if cif.qdat is not None:
            out.qval = np.unpackbits(np.array([int(b) for b in b64decode(cif.qdat)],
                                              dtype='uint8'))
        return out


    def get_ciftext(self, cif_id):
        """generate and return text of CIF file"""
        cif = self.get_cif(cif_id, as_strings=True)
        if cif is None:
            return

        out = ['data_global']
        if cif.formula_title != '<missing>':
            out.append(f"_amcsd_formula_title '{cif.formula_title:s}'")

        if cif.mineral.name != '<missing>':
            out.append(f"_chemical_name_mineral '{cif.mineral.name:s}'")
        out.append('loop_')
        out.append('_publ_author_name')
        for a in authors:
            out.append(f"'{a:s}'")

        out.append(f"_journal_name_full '{cif.pub.journalname}'")
        out.append(f"_journal_volume {cif.pub.volume}")
        out.append(f"_journal_year {ciflpub.year}")
        out.append(f"_journal_page_first {cif.pub.page_first}")
        out.append(f"_journal_page_last {cif.pub.page_last}")
        out.append('_publ_section_title')
        out.append(';')
        out.append(f"{cif.pub_title:s}")
        out.append(';')
        out.append(f"_database_code_amcsd {cif_id:07d}")
        if cif.compound != '<missing>':
            out.append(f"_chemical_compound_source '{cif.compound}'")
        out.append(f"_chemical_formula_sum '{cif.formula}'")
        out.append(f"_cell_length_a {cif.a}")
        out.append(f"_cell_length_b {cif.b}")
        out.append(f"_cell_length_c {cif.c}")
        out.append(f"_cell_angle_alpha {cif.alpha}")
        out.append(f"_cell_angle_beta {cif.beta}")
        out.append(f"_cell_angle_gamma {cif.gamma}")
        out.append(f"_cell_volume {cif.cell_volume}")
        out.append(f"_exptl_crystal_density_diffrn  {cif.crystal_density}")
        out.append(f"_symmetry_space_group_name_H-M '{hm_symbol}'")
        out.append('loop_')
        out.append('_space_group_symop_operation_xyz')
        for xyzop in json.loads(cif.spacegroup.symmetry_xyz):
            out.append(f"  '{xyzop:s}'")

        atoms_sites =json.loads(cif.atoms_sites)
        if atoms_sites not in (None, 'None', '0', '<missing>'):
            out.append('loop_')
            out.append('_atom_site_label')
            out.append('_atom_site_fract_x')
            out.append('_atom_site_fract_y')
            out.append('_atom_site_fract_z')
            

            natoms = len(atoms_sites)
            atoms_x = get_optarray(cif.atoms_x)
            atoms_y = get_optarray(cif.atoms_y)
            atoms_z = get_optarray(cif.atoms_z)
            atoms_occ = get_optarray(cif.atoms_occupancy)
            atoms_u_iso = get_optarray(cif.atoms_u_iso)
            if atoms_occ != '0':
                out.append('_atom_site_occupancy')
            if atoms_u_iso != '0':
                out.append('_atom_site_U_iso_or_equiv')
            for i in range(natoms):
                adat = f"{atoms_sites[i]}   {atoms_x[i]}  {atoms_y[i]}  {atoms_z[i]}"
                if atoms_occ != '0':
                    adat +=  f"  {atoms_occ[i]}"
                if atoms_u_iso != '0':
                    adat +=  f"  {atoms_u_iso[i]}"
                out.append(adat)

            aniso_label =json.loads(cif.atoms_aniso_label)
            if aniso_label not in ('0', '<missing>'):
                out.append('loop_')
                out.append('_atom_site_aniso_label')
                out.append('_atom_site_aniso_U_11')
                out.append('_atom_site_aniso_U_22')
                out.append('_atom_site_aniso_U_33')
                out.append('_atom_site_aniso_U_12')
                out.append('_atom_site_aniso_U_13')
                out.append('_atom_site_aniso_U_23')
                natoms = len(aniso_label)
                u11 = get_optarray(cif.atoms_aniso_u11)
                u22 = get_optarray(cif.atoms_aniso_u22)
                u33 = get_optarray(cif.atoms_aniso_u33)
                u12 = get_optarray(cif.atoms_aniso_u12)
                u13 = get_optarray(cif.atoms_aniso_u13)
                u23 = get_optarray(cif.atoms_aniso_u23)

                for i in range(natoms):
                    out.append(f"{aniso_label[i]}   {u11[i]}  {u22[i]}  {u33[i]}  {u12[i]}  {u13[i]}  {u23[i]}")


        out.append('')
        out.append('')
        return '\n'.join(out)

    def find_cifs(self, id=None, mineral_name=None, mineral_id=None,
                  publication_id=None, elements=None):
        """return list of CIF Structures matching mineral, publication, or elements
        """
        if id is not None:
            thiscif = self.get_cif(id)
            if thiscif is not None:
                return [thiscif]

        tabcif = self.tables['cif']
        tabmin = self.tables['minerals']
        tabpub = self.tables['publications']
        tabcifelem = self.tables['cif_elements']
        args = []
        if mineral_name is not None:
            args.append(func.lower(tabmin.c.name)==mineral_name.lower())
            args.append(tabmin.c.id==tabcif.c.mineral_id)

        query = select(tabcif.c.id).where(and_(*args))
        found = []
        out = []
        for row in self.conn.execute(query).fetchall():
            if row[0] not in found:
                out.append(self.get_cif(row[0]))
                found.append(row[0])
        return out
    
            
        
            


