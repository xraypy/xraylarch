#!/usr/bin/env python
"""
AMCIFDB: American Mineralogical CIF database as sqlite3 database/python

Usage:
   amcifdb = AMCIFDB('amcif.db')

add a CIF file:
  amcifdb.add_ciffile('NewFile.cif')

generatt the text of a CIF file from index:
  cif_text = amcifdb.get_ciftext(300)

OK, that looks like 'well, why not just save the CIF files'?

And the answers are that there are simple methods for:
   a) getting the XRD Q points
   b) getting structure factors
   c) getting atomic clustes as for feff files
   d) saving Feff.inp files

"""

import sys
import os
import re
import time
import json
from io import StringIO
from string import ascii_letters
from base64 import b64encode, b64decode
from collections import namedtuple

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import atexit
import numpy as np

from sqlalchemy import MetaData, create_engine, func, text, and_, Table
from sqlalchemy import __version__ as sqla_version
from sqlalchemy.sql import select as sqla_select
from sqlalchemy.orm import sessionmaker


from .amcsd_utils import (make_engine, isAMCSD, put_optarray, get_optarray,
                          PMG_CIF_OPTS, CifParser, SpacegroupAnalyzer, pmg_version)

from xraydb.chemparser import chemparse
from xraydb import f0, f1_chantler, f2_chantler


from .xrd_tools import generate_hkl, d_from_hkl, twth_from_q, E_from_lambda
from .cif2feff import cif2feffinp
from ..utils import isotime, mkdir
from ..utils.strutils import version_ge, bytes2str
from ..utils.physical_constants import TAU, ATOM_SYMS
from ..site_config import user_larchdir
from .. import logger

_CIFDB = None
ALL_HKLS = None
AMCSD_TRIM = 'amcsd_cif1.db'
AMCSD_FULL = 'amcsd_cif2.db'

SOURCE_URLS = ('https://docs.xrayabsorption.org/databases/',
               'https://millenia.cars.aps.anl.gov/xraylarch/downloads/')

CIF_TEXTCOLUMNS = ('formula', 'compound', 'pub_title', 'formula_title', 'a',
                   'b', 'c', 'alpha', 'beta', 'gamma', 'cell_volume',
                   'crystal_density', 'atoms_sites', 'atoms_x', 'atoms_y',
                   'atoms_z', 'atoms_occupancy', 'atoms_u_iso',
                   'atoms_aniso_label', 'atoms_aniso_u11', 'atoms_aniso_u22',
                   'atoms_aniso_u33', 'atoms_aniso_u12', 'atoms_aniso_u13',
                   'atoms_aniso_u23', 'qdat','url', 'hkls')



CifPublication = namedtuple('CifPublication', ('id', 'journalname', 'year',
                                            'volume', 'page_first',
                                            'page_last', 'authors'))


StructureFactor = namedtuple('StructureFactor', ('q', 'intensity', 'hkl',
                                                 'twotheta', 'd',
                                                 'wavelength', 'energy',
                                                 'f2hkl', 'degen', 'lorentz'))


# for packing/unpacking H, K, L to 2-character hash
HKL_ENCODE = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_%'
def pack_hkl(h, k, l):
    """pack H, K, L values into 2 character sequence of
    printable characters for storage and transmission

    H, K, L must be unsigned integers from 0 to 15

    see also unpack_hkl() to reverse the process.
    """
    if (h > 15 or k > 15 or l > 15 or
        h < 0  or k < 0  or l < 0):
        raise ValueError("hkl values out of range (max=15)")
    x = h*256 + k*16 + l
    return HKL_ENCODE[x//64] + HKL_ENCODE[x%64]


def unpack_hkl(hash):
    """unpack encoded H, K, L integers packed with pack_hkl()"""
    a, b = HKL_ENCODE.index(hash[0]), HKL_ENCODE.index(hash[1])
    s = a*64 + b
    t = s//16
    return t//16, t%16, s%16


def pack_hkl_degen(hkls, degen):
    """pack array of H, K, L and degeneracy values into printable
    string for storage and transmission
    hkl must be an array or list of list/tuples for H, K, L, with
    each H, K, L value an unsigned integers from 0 to 15

    hkls and degen must be ndarrays or lists of the same length
    see also unpack_hkl_degen() to reverse the process.
    """
    if len(hkls) != len(degen):
        raise ValueError("hkls and degen must be the same length in pack_hkl_degen()")

    shkl = [pack_hkl(h, k, l) for h, k, l in hkls]
    sdegen = json.dumps(degen.tolist()).replace(' ', '')
    return f"{''.join(shkl)}|{sdegen}"


def unpack_hkl_degen(sinp):
    """pack arrays of h, k, l and degeneracies from string stored by pack_hkl_degen
    see also pack_hkl_degen()
    """
    shkl, sdegen = sinp.split('|')
    n = len(shkl)//2
    hkls = []
    for i in range(n):
        hkls.append(unpack_hkl(shkl[2*i:2*i+2]))
    degen = json.loads(sdegen)
    return np.array(hkls), np.array(degen)



def select(*args):
    """wrap sqlalchemy select for version 1.3 and 2.0"""
    # print("SELECT ", args, type(args))
    # print(sqla_version, version_ge(sqla_version, '1.4.0'))
    if version_ge(sqla_version, '1.4.0'):
        return sqla_select(*args)
    else:
        return sqla_select(tuple(args))


def get_nonzero(thing):
    try:
        if len(thing) == 1 and abs(thing[0]) < 1.e-5:
            return None
    except:
        pass
    return thing

def clean_elemsym(sym):
    sx = (sym + ' ')[:2]
    return ''.join([s.strip() for s in sx if s in ascii_letters])


def parse_cif_file(filename):
    """parse ciffile, extract data for 1st listed structure,
    and do some basic checks:
        must have formula
        must have spacegroup
    returns dat, formula, json-dumped symm_xyz
    """
    if CifParser is None:
        raise ValueError("CifParser from pymatgen not available. Try 'pip install pymatgen'.")

    cif = CifParser(filename, **PMG_CIF_OPTS)
    cifkey = list(cif._cif.data.keys())[0]
    dat = cif._cif.data[cifkey].data

    formula = None
    for formname in ('_chemical_formula_sum', '_chemical_formula_moiety'):
        if formname in dat:
            try:
                parsed_formula = chemparse(dat[formname])
                formula = dat[formname]
            except:
                pass
    if formula is None and '_atom_site_type_symbol' in dat:
        comps = {}
        complist = dat['_atom_site_type_symbol']
        for c in complist:
            if c not in comps:
                nx = complist.count(c)
                comps[c] = '%s%d' % (c, nx) if nx != 1 else c
        formula = ''.join(comps.values())

    if formula is None:
        raise ValueError(f'Cannot read chemical formula from file {filename:s}')

    # get spacegroup and symmetry
    sgroup_name = dat.get('_symmetry_space_group_name_H-M', None)
    if sgroup_name is None:
        for key, val in dat.items():
            if 'space_group' in key and 'H-M' in key:
                sgroup_name = val

    symm_xyz = dat.get('_space_group_symop_operation_xyz', None)
    if symm_xyz is None:
        symm_xyz = dat.get('_symmetry_equiv_pos_as_xyz', None)
    if symm_xyz is None:
        raise ValueError(f'Cannot read symmetries from file {filename:s}')

    symm_xyz = json.dumps(symm_xyz)
    return dat, formula, symm_xyz


class CifStructure():
    """representation of a Cif Structure
    """

    def __init__(self, ams_id=None, ams_db=None, publication=None, mineral=None,
                 spacegroup=None, hm_symbol=None, formula_title=None,
                 compound=None, formula=None, pub_title=None, a=None, b=None,
                 c=None, alpha=None, beta=None, gamma=None, hkls=None,
                 cell_volume=None, crystal_density=None,
                 atoms_sites='<missing>', atoms_aniso_label='<missing>',
                 atoms_x=None, atoms_y=None, atoms_z=None,
                 atoms_occupancy=None, atoms_u_iso=None, atoms_aniso_u11=None,
                 atoms_aniso_u22=None, atoms_aniso_u33=None,
                 atoms_aniso_u12=None, atoms_aniso_u13=None,
                 atoms_aniso_u23=None):

        self.ams_id = ams_id
        self.ams_db = ams_db
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
        self.hkls = hkls
        self.cell_volume = cell_volume
        self.crystal_density = crystal_density
        self.atoms_sites = atoms_sites
        self.atoms_aniso_label = atoms_aniso_label
        self.atoms_x = atoms_x
        self.atoms_y = atoms_y
        self.atoms_z = atoms_z
        self.atoms_occupancy = get_nonzero(atoms_occupancy)
        self.atoms_u_iso = get_nonzero(atoms_u_iso)
        self.atoms_aniso_u11 = get_nonzero(atoms_aniso_u11)
        self.atoms_aniso_u22 = get_nonzero(atoms_aniso_u22)
        self.atoms_aniso_u33 = get_nonzero(atoms_aniso_u33)
        self.atoms_aniso_u12 = get_nonzero(atoms_aniso_u12)
        self.atoms_aniso_u13 = get_nonzero(atoms_aniso_u13)
        self.atoms_aniso_u23 = get_nonzero(atoms_aniso_u23)
        self.natoms = 0
        self._ciftext = None
        self.pmg_pstruct = None
        self.pmg_cstruct = None
        if atoms_sites not in (None, '<missing>'):
            self.natoms = len(atoms_sites)

    def __repr__(self):
        if self.ams_id is None or self.formula is None:
            return '<CifStructure empty>'
        return f'<CifStructure, ams_id={self.ams_id:d}, formula={self.formula:s}>'

    def get_mineralname(self):
        minname = self.mineral.name
        if minname == '<missing>':
            minname =self.formula_title
        if minname == '<missing>':
            minname = 'missing'
        return minname


    @property
    def ciftext(self):
        if self._ciftext is not None:
            return self._ciftext

        out = ['data_global']
        if self.formula_title != '<missing>':
            out.append(f"_amcsd_formula_title '{self.formula_title:s}'")

        if self.mineral.name != '<missing>':
            out.append(f"_chemical_name_mineral '{self.mineral.name:s}'")
        out.append('loop_')
        out.append('_publ_author_name')
        for a in self.publication.authors:
            out.append(f"'{a:s}'")

        out.append(f"_journal_name_full '{self.publication.journalname}'")
        out.append(f"_journal_volume {self.publication.volume}")
        out.append(f"_journal_year {self.publication.year}")
        out.append(f"_journal_page_first {self.publication.page_first}")
        out.append(f"_journal_page_last {self.publication.page_last}")
        out.append('_publ_section_title')
        out.append(';')
        out.append(f"{self.pub_title:s}")
        out.append(';')
        out.append(f"_database_code_amcsd {self.ams_id:07d}")
        if self.compound != '<missing>':
            out.append(f"_chemical_compound_source '{self.compound}'")
        out.append(f"_chemical_formula_sum '{self.formula}'")
        out.append(f"_cell_length_a {self.a}")
        out.append(f"_cell_length_b {self.b}")
        out.append(f"_cell_length_c {self.c}")
        out.append(f"_cell_angle_alpha {self.alpha}")
        out.append(f"_cell_angle_beta {self.beta}")
        out.append(f"_cell_angle_gamma {self.gamma}")
        out.append(f"_cell_volume {self.cell_volume}")
        out.append(f"_exptl_crystal_density_diffrn  {self.crystal_density}")
        out.append(f"_symmetry_space_group_name_H-M '{self.hm_symbol}'")
        out.append('loop_')
        out.append('_space_group_symop_operation_xyz')
        for xyzop in json.loads(self.spacegroup.symmetry_xyz):
            out.append(f"  '{xyzop:s}'")

        atoms_sites = self.atoms_sites
        if atoms_sites not in (None, 'None', '0', '<missing>'):
            out.append('loop_')
            out.append('_atom_site_label')
            out.append('_atom_site_fract_x')
            out.append('_atom_site_fract_y')
            out.append('_atom_site_fract_z')


            natoms = len(atoms_sites)
            atoms_x = self.atoms_x
            atoms_y = self.atoms_y
            atoms_z = self.atoms_z
            atoms_occ = self.atoms_occupancy
            atoms_u_iso = self.atoms_u_iso
            if atoms_occ is not None:
                out.append('_atom_site_occupancy')
            if atoms_u_iso is not None:
                out.append('_atom_site_U_iso_or_equiv')
            for i in range(natoms):
                adat = f"{atoms_sites[i]}   {atoms_x[i]}  {atoms_y[i]}  {atoms_z[i]}"
                if atoms_occ is not None:
                    adat +=  f"  {atoms_occ[i]}"
                if atoms_u_iso is not None:
                    adat +=  f"  {atoms_u_iso[i]}"
                out.append(adat)

            aniso_label = self.atoms_aniso_label
            if aniso_label not in (None, '0', '<missing>'):
                out.append('loop_')
                out.append('_atom_site_aniso_label')
                out.append('_atom_site_aniso_U_11')
                out.append('_atom_site_aniso_U_22')
                out.append('_atom_site_aniso_U_33')
                out.append('_atom_site_aniso_U_12')
                out.append('_atom_site_aniso_U_13')
                out.append('_atom_site_aniso_U_23')
                natoms = len(aniso_label)
                u11 = self.atoms_aniso_u11
                u22 = self.atoms_aniso_u22
                u33 = self.atoms_aniso_u33
                u12 = self.atoms_aniso_u12
                u13 = self.atoms_aniso_u13
                u23 = self.atoms_aniso_u23

                for i in range(natoms):
                    out.append(f"{aniso_label[i]}   {u11[i]}  {u22[i]}  {u33[i]}  {u12[i]}  {u13[i]}  {u23[i]}")

        out.append('')
        out.append('')
        self._ciftext = '\n'.join(out)
        return self.ciftext


    def find_hkls(self, nmax=64, qmax=10, wavelength=0.75):
        """find the HKLs and degeneracies of the strongest reflections

        this will calculate structure factors, and sort them, but the
        purpose is really to do a filter to find the strongest HKLs that
        can then be saved and restored for structure factor calcs using
        only the most important HKL values.

        returns hkls, degen of the nmax reflections with the highest scattered intensity
        """
        self.get_pmg_struct()

        pstruct = self.pmg_pstruct
        cstruct = self.pmg_cstruct
        if pstruct is None:
            print(f"pymatgen could not parse CIF structure for CIF {self.ams_id}")
            return

        global ALL_HKLS
        if ALL_HKLS is None:
            ALL_HKLS = generate_hkl(hmax=15, kmax=15, lmax=15, positive_only=False)

        hkls = ALL_HKLS[:]
        unitcell = self.get_unitcell()
        qhkls = TAU / d_from_hkl(hkls, **unitcell)

        # remove q values outside of range
        qfilt = (qhkls < qmax)
        qhkls = qhkls[qfilt]
        hkls  = hkls[qfilt]

        # find duplicate q-values, set degen
        # scale up q values to better find duplicates
        qscaled = [int(round(q*1.e9)) for q in qhkls]
        q_unique, q_degen, hkl_unique = [], [], []
        for i, q in enumerate(qscaled):
            if q in q_unique:
                q_degen[q_unique.index(q)] += 1
            else:
                q_unique.append(q)
                q_degen.append(1)
                hkl_unique.append(hkls[i])

        qorder = np.argsort(q_unique)
        qhkls  = 1.e-9*np.array(q_unique)[qorder]
        hkls   = abs(np.array(hkl_unique)[qorder])
        degen  = np.array(q_degen)[qorder]

        # note the f2 is calculated here without resonant corrections
        f2 = self.calculate_f2(hkls, qhkls=qhkls, wavelength=None)

        # filter out very small structure factors
        ffilt = (f2 > 1.e-6*max(f2))
        qhkls = qhkls[ffilt]
        hkls  = hkls[ffilt]
        degen = degen[ffilt]
        f2    = f2[ffilt]

        # lorentz and polarization correction
        arad = (TAU/360)*twth_from_q(qhkls, wavelength)
        corr = (1+np.cos(arad)**2)/(np.sin(arad/2)**2*np.cos(arad/2))

        intensity = f2 * degen * corr
        ifilt = (intensity > 0.005*max(intensity))

        intensity  = intensity[ifilt] / max(intensity)
        qhkls  = qhkls[ifilt]
        hkls   =  hkls[ifilt]
        degen  = degen[ifilt]

        # indices of peaks in descending order of intensity
        main_peaks = np.argsort(intensity)[::-1][:nmax]

        hkls_main, degen_main = hkls[main_peaks], degen[main_peaks]
        if self.ams_db is not None:
            self.hkls = self.ams_db.set_hkls(self.ams_id, hkls_main, degen_main)

        return hkls_main, degen_main

    def get_structure_factors(self, wavelength=0.75):
        """given arrays of HKLs and degeneracies (perhaps from find_hkls(),
        return structure factors

        This is a lot like find_hkls(), but with the assumption that HKLs
        are not to be filtered or altered.
        """
        if self.hkls is None:
            self.find_hkls(nmax=64, qmax=10, wavelength=wavelength)

        hkls, degen = unpack_hkl_degen(self.hkls)

        self.get_pmg_struct()
        pstruct = self.pmg_pstruct
        if pstruct is None:
            print(f"pymatgen could not parse CIF structure for CIF {self.ams_id}")
            return

        unitcell = self.get_unitcell()
        dhkls = d_from_hkl(hkls, **unitcell)
        qhkls = TAU / dhkls

        # sort by q
        qsort = np.argsort(qhkls)
        qhkls = qhkls[qsort]
        dhkls = dhkls[qsort]
        hkls  = hkls[qsort]
        degen = degen[qsort]

        energy = E_from_lambda(wavelength, E_units='eV')

        f2hkl = self.calculate_f2(hkls, qhkls=qhkls, wavelength=wavelength)

        # lorentz and polarization correction
        twoth = twth_from_q(qhkls, wavelength)
        arad = (TAU/360)*twoth
        corr = (1+np.cos(arad)**2)/(np.sin(arad/2)**2*np.cos(arad/2))

        intensity = f2hkl * degen * corr

        return StructureFactor(q=qhkls, intensity=intensity, hkl=hkls, d=dhkls,
                               f2hkl=f2hkl, twotheta=twoth, degen=degen,
                               lorentz=corr, wavelength=wavelength,
                               energy=energy)


    def calculate_f2(self, hkls, qhkls=None, energy=None, wavelength=None):
        """calculate F*F'.

        If wavelength (in Ang) or energy (in eV) is not None, then
        resonant corrections will be included.
        """
        if qhkls is None:
            unitcell = self.get_unitcell()
            qhkls = TAU / d_from_hkl(hkls, **unitcell)
        sq = qhkls/(2*TAU)
        sites = self.get_sites()

        if energy is None and wavelength is not None:
            energy = E_from_lambda(wavelength, E_units='eV')

        # get f0 and resonant scattering factors
        f0vals, f1vals, f2vals = {}, {}, {}
        for elem in sites.keys():
            if elem not in f0vals:
                f0vals[elem] = f0(elem, sq)
                if energy is not None:
                    f1vals[elem] = f1_chantler(elem, energy)
                    f2vals[elem] = f2_chantler(elem, energy)

        # and f2
        f2 = np.zeros(len(hkls))
        for i, hkl in enumerate(hkls):
            fsum = 0.
            for elem in f0vals:
                fval = f0vals[elem][i]
                if energy is not None:
                    fval += f1vals[elem] - 1j*f2vals[elem]
                for occu, fcoord in sites[elem]:
                    fsum += fval*occu*np.exp(1j*TAU*(fcoord*hkl).sum())
            f2[i] = (fsum*fsum.conjugate()).real
        return f2


    def get_pmg_struct(self):
        if self.pmg_cstruct is not None and self.pmg_pstruct is not None:
            return
        err = f"pymatgen {pmg_version} could not"
        try:
            pmcif = CifParser(StringIO(self.ciftext), **PMG_CIF_OPTS)
        except:
            print(f"{err} parse CIF text for CIF {self.ams_id}")

        try:
            self.pmg_cstruct = pmcif.parse_structures()[0]
        except:
            print(f"{err} parse structure for CIF {self.ams_id}")

        try:
            self.pmg_pstruct = SpacegroupAnalyzer(self.pmg_cstruct
                                                  ).get_conventional_standard_structure()
        except:
            print(f"{err} could not analyze spacegroup for CIF {self.ams_id}")
            
    def get_unitcell(self):
        "unitcell as dict, from PMG structure"
        self.get_pmg_struct()
        pstruct = self.pmg_pstruct
        if pstruct is None:
            print(f"pymatgen could not parse CIF structure for CIF {self.ams_id}")
            return
        pdict = pstruct.as_dict()
        unitcell = {}
        for a in ('a', 'b', 'c', 'alpha', 'beta', 'gamma', 'volume'):
            unitcell[a] = pdict['lattice'][a]
        return unitcell

    def get_sites(self):
        "dictionary of sites, from PMG structure"
        self.get_pmg_struct()
        pstruct = self.pmg_pstruct
        if pstruct is None:
            print(f"pymatgen could not parse CIF structure for CIF {self.ams_id}")
            return

        sites = {}
        for site in pstruct.sites:
            sdat = site.as_dict()
            fcoords = sdat['abc']

            for spec in sdat['species']:
                elem = spec['element']
                if elem == 'Nh': elem = 'N'
                if elem == 'Og':
                    elem = 'O'
                if elem in ('Hs', 'D'):
                    elem = 'H'
                if elem.startswith('Dh') or elem.startswith('Dd') or elem.startswith('Dw'):
                    elem = 'H'
                if elem == 'Fl':
                    elem = 'F'
                occu = spec['occu']
                if elem not in sites:
                    sites[elem] = [(occu, fcoords)]
                else:
                    sites[elem].append([occu, fcoords])
        return sites



    def get_feffinp(self, absorber, edge=None, cluster_size=8.0, absorber_site=1,
                    with_h=False, version8=True):
        pub = self.publication
        journal = f"{pub.journalname} {pub.volume}, pp. {pub.page_first}-{pub.page_last} ({pub.year:d})"
        authors = ', '.join(pub.authors)
        titles = [f'Structure from AMCSD, AMS_ID: {self.ams_id:d}',
                  f'Mineral Name: {self.mineral.name:s}']

        if not self.formula_title.startswith('<missing'):
            titles.append(f'Formula Title: {self.formula_title}')

        titles.extend([f'Journal: {journal}', f'Authors: {authors}'])
        if not self.pub_title.startswith('<missing'):
            for i, line in enumerate(self.pub_title.split('\n')):
                titles.append(f'Title{i+1:d}: {line}')

        return cif2feffinp(self.ciftext, absorber, edge=edge,
                           cluster_size=cluster_size, with_h=with_h,
                           absorber_site=absorber_site,
                           extra_titles=titles, version8=version8)

    def save_feffinp(self, absorber, edge=None, cluster_size=8.0, absorber_site=1,
                      filename=None, version8=True):
        feff6text = self.get_feffinp(absorber, edge=edge, cluster_size=cluster_size,
                                      absorber_site=absorber_site, version8=version8)
        if filename is None:
            min_name = self.mineral.name.lower()
            if min_name in ('', '<missing>', 'None'):
                name = f'{absorber:s}_{edge:s}_CIF{self.ams_id:06d}'
            else:
                name = f'{absorber:s}_{edge:s}_{min_name:s}_CIF{self.ams_id:06d}'

            ffolder = os.path.join(user_larchdir, 'feff', name)
            mkdir(ffolder)
            filename = os.path.join(ffolder, 'feff.inp')
        with open(filename, 'w', encoding=sys.getdefaultencoding()) as fh:
            fh.write(feff6text)
        return filename

class AMCSD():
    """
    Database of CIF structure data from the American Mineralogical Crystal Structure Database

       http://rruff.geo.arizona.edu/AMS/amcsd.php

    """
    def __init__(self, dbname=None, read_only=False):
        "connect to an existing database"
        if dbname is None:
            parent, _ = os.path.split(__file__)
            dbname = os.path.join(parent, AMCSD_TRIM)
        if not os.path.exists(dbname):
            raise IOError("Database '%s' not found!" % dbname)

        if not isAMCSD(dbname):
            raise ValueError("'%s' is not a valid AMCSD Database!" % dbname)

        self.connect(dbname, read_only=read_only)
        atexit.register(self.finalize_amcsd)
        ciftab = self.tables['cif']
        for colname in CIF_TEXTCOLUMNS:
            if colname not in ciftab.columns and not read_only:
                self.session.execute(text(f'alter table cif add column {colname} text'))
                self.close()
                self.connect(dbname, read_only=read_only)
                time.sleep(0.1)
                self.insert('version', tag=f'with {colname}', date=isotime(),
                            notes=f'added {colname} column to cif table')

    def finalize_amcsd(self):
        conn = getattr(self, 'conn', None)
        if conn is not None:
            conn.close()

    def connect(self, dbname, read_only=False):
        self.dbname = dbname
        self.engine = make_engine(dbname)
        self.conn = self.engine.connect()
        kwargs = {'bind': self.engine, 'autoflush': True, 'autocommit': False}
        self.session = sessionmaker(**kwargs)()
        if read_only:
            def readonly_flush(*args, **kwargs):
                return
            self.session.flush = readonly_flush

        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)
        self.tables = self.metadata.tables
        self.cif_elems = None

    def close(self):
        "close session"
        self.session.flush()
        self.session.close()

    def query(self, *args, **kws):
        "generic query"
        return self.session.query(*args, **kws)

    def insert(self, tablename, **kws):
        if isinstance(tablename, Table):
            table = tablename
        else:
            table = self.tables[tablename]
        stmt = table.insert().values(kws)
        out = self.session.execute(stmt)
        self.session.commit()
        self.session.flush()

    def update(self, tablename, whereclause=False, **kws):
        if isinstance(tablename, Table):
            table = tablename
        else:
            table = self.tables[tablename]

        stmt = table.update().where(whereclause).values(kws)
        out = self.session.execute(stmt)
        self.session.commit()
        self.session.flush()

    def execall(self, query):
        return self.session.execute(query).fetchall()

    def execone(self, query):
        results = self.session.execute(query).fetchone()
        if results is None or len(results) < 1:
            return None
        return results

    def get_all(self, tablename):
        return self.execall(self.tables[tablename].select())


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
        rows = self.get_all('version')
        if not with_history:
            rows = rows[-1:]
        if long or with_history:
            for row in rows:
                out.append(f"AMCSD Version: {row.tag} [{row.date}] '{row.notes}'")
            out.append(f"Python Version: {__version__}")
            out = "\n".join(out)
        elif rows is None:
            out = f"AMCSD Version: unknown, Python Version: {__version__}"
        else:
            out = f"AMCSD Version: {rows[0].tag}, Python Version: {__version__}"
        return out

    def _get_tablerow(self, table, name, add=True):
        tab = self.tables[table]
        if '"' in name:
            name = name.replace('"', '\"')
        rows = self.execall(tab.select().where(tab.c.name==name))
        if len(rows) == 0:
            if not add:
                return None
            self.insert(tab, name=name)
            rows = self.execall(tab.select().where(tab.c.name==name))
        return rows[0]

    def get_spacegroup(self, hm_name):
        """get row from spacegroups table by HM notation.  See add_spacegroup()
        """
        tab = self.tables['spacegroups']
        rows = self.execall(tab.select().where(tab.c.hm_notation==hm_name))
        if len(rows) >0:
            return rows[0]
        return None


    def add_spacegroup(self, hm_name, symmetry_xyz, category=None):
        """add entry to spacegroups table, including HM notation and CIF symmetry operations
        """
        sg = self.get_spacegroup(hm_name)
        if sg is not None and sg.symmetry_xyz == symmetry_xyz:
            return sg

        args = {'hm_notation': hm_name, 'symmetry_xyz': symmetry_xyz}
        if category is not None:
            args['category'] = category
        self.insert('spacegroups', **args)
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

        rows = self.execall(tab.select().where(and_(*args)))
        if len(rows) > 0:
            out = []
            authtab = self.tables['authors']
            patab = self.tables['publication_authors']
            for row in rows:
                q = select(authtab.c.name).where(and_(authtab.c.id==patab.c.author_id,
                                                      patab.c.publication_id==row.id))
                authors = tuple([i[0] for i in self.execall(q)])
                out.append(CifPublication(row.id, row.journalname, row.year,
                                          row.volume, row.page_first,
                                          row.page_last, authors))
            return out
        return None


    def add_publication(self, journalname, year, authorlist, volume=None,
                        page_first=None, page_last=None, with_authors=True):

        args = dict(journalname=journalname, year=year)
        if volume is not None:
            args['volume']  = volume
        if page_first is not None:
            args['page_first'] = page_first
        if page_last is not None:
            args['page_last'] = page_last

        self.insert('publications', **args)
        self.session.flush()
        pub = self.get_publications(journalname, year, volume=volume,
                                    page_first=page_first,
                                    page_last=page_last)[0]

        if with_authors:
            for name in authorlist:
                auth = self._get_tablerow('authors', name, add=True)
                self.insert('publication_authors',
                            publication_id=pub.id, author_id=auth.id)
        return pub

    def add_cifdata(self, cif_id, mineral_id, publication_id,
                    spacegroup_id, formula=None, compound=None,
                    formula_title=None, pub_title=None, a=None, b=None,
                    c=None, alpha=None, beta=None, gamma=None, url='',
                    cell_volume=None, crystal_density=None,
                    atoms_sites=None, atoms_x=None, atoms_y=None,
                    atoms_z=None, atoms_occupancy=None, atoms_u_iso=None,
                    atoms_aniso_label=None, atoms_aniso_u11=None,
                    atoms_aniso_u22=None, atoms_aniso_u33=None,
                    atoms_aniso_u12=None, atoms_aniso_u13=None,
                    atoms_aniso_u23=None, with_elements=True):

        self.insert('cif', id=cif_id, mineral_id=mineral_id,
                    publication_id=publication_id,
                    spacegroup_id=spacegroup_id,
                    formula_title=formula_title, pub_title=pub_title,
                    formula=formula, compound=compound, url=url, a=a, b=b,
                    c=c, alpha=alpha, beta=beta, gamma=gamma,
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
            for element in chemparse(formula).keys():
                self.insert('cif_elements', cif_id=cif_id, element=element)
        return self.get_cif(cif_id)


    def add_ciffile(self, filename, cif_id=None, url='', debug=False):

        if CifParser is None:
            raise ValueError("CifParser from pymatgen not available. Try 'pip install pymatgen'.")
        try:
            dat, formula, symm_xyz = parse_cif_file(filename)
        except:
            raise ValueError(f"unknown error trying to parse CIF file: {filename}")

        # compound
        compound = '<missing>'
        for compname in ('_chemical_compound_source',
                         '_chemical_name_systematic',
                         '_chemical_name_common'):
            if compname in dat:
                compound = dat[compname]


        # spacegroup
        sgroup_name = dat.get('_symmetry_space_group_name_H-M', None)
        if sgroup_name is None:
            for key, val in dat.items():
                if 'space_group' in key and 'H-M' in key:
                    sgroup_name = val

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

        min_name = '<missing>'
        for mname in ('_chemical_name_mineral',
                       '_chemical_name_common'):
            if mname in dat:
                min_name = dat[mname]
        mineral = self._get_tablerow('minerals', min_name)

        # get publication data (including ISCD style of 'citation' in place of 'journal' )
        pubdict = dict(journalname=dat.get('_journal_name_full', None),
                       year=dat.get('_journal_year', None),
                       volume=dat.get('_journal_volume', None),
                       page_first=dat.get('_journal_page_first', None),
                       page_last=dat.get('_journal_page_last', None))

        for key, alt, dval in (('journalname', 'journal_full', 'No Journal'),
                               ('year', None, -1),
                               ('volume', 'journal_volume', 0),
                               ('page_first', None, 0),
                               ('page_last', None, 0)):
            if pubdict[key] is None:
                if alt is None:
                    alt = key
                alt = '_citation_%s' % alt
                pubdict[key] = dat.get(alt, [dval])[0]
        authors = dat.get('_publ_author_name', None)
        if authors is None:
            authors = dat.get('_citation_author_name', ['Anonymous'])

        pubs = self.get_publications(**pubdict)
        if pubs is None:
            pub = self.add_publication(pubdict['journalname'],
                                       pubdict['year'], authors,
                                       volume=pubdict['volume'],
                                       page_first=pubdict['page_first'],
                                       page_last=pubdict['page_last'])
        else:
            pub = pubs[0]

        density = dat.get('_exptl_crystal_density_meas', None)
        if density is None:
            density = dat.get('_exptl_crystal_density_diffrn', -1.0)

        if cif_id is None:
            cif_id = dat.get('_database_code_amcsd', None)
            if cif_id is None:
                cif_id = dat.get('_cod_database_code', None)
            if cif_id is None:
                cif_id = self.next_cif_id()
        cif_id = int(cif_id)

        # check again for this cif id (must match CIF AMS id and formula
        tabcif = self.tables['cif']
        this = self.execone(select(tabcif.c.id, tabcif.c.formula
                               ).where(tabcif.c.id==int(cif_id)))
        if this is not None:
            _cid, _formula = this
            if formula.replace(' ', '') == _formula.replace(' ', ''):
                return cif_id
            else:
                cif_id = self.next_cif_id()

        if debug:
            print("##CIF Would add Cif Data !" )
            print(cif_id, mineral.id, pub.id, sgroup.id)
            print("##CIF formuala / compound: ", formula, compound)
            print("titles: ",
                  dat.get('_amcsd_formula_title', '<missing>'),
                  dat.get('_publ_section_title', '<missing>'))
            print("##CIF atom sites :", json.dumps(dat['_atom_site_label']))
            print("##CIF locations : ",
                  put_optarray(dat, '_atom_site_fract_x'),
                  put_optarray(dat, '_atom_site_fract_y'),
                  put_optarray(dat, '_atom_site_fract_z'),
                  put_optarray(dat, '_atom_site_occupancy'),
                  put_optarray(dat, '_atom_site_U_iso_or_equiv'))
            print("##CIF aniso label : ",
                  json.dumps(dat.get('_atom_site_aniso_label', '<missing>')))
            print("##CIF aniso : ",
                  put_optarray(dat, '_atom_site_aniso_U_11'),
                  put_optarray(dat, '_atom_site_aniso_U_22'),
                  put_optarray(dat, '_atom_site_aniso_U_33'),
                  put_optarray(dat, '_atom_site_aniso_U_12'),
                  put_optarray(dat, '_atom_site_aniso_U_13'),
                  put_optarray(dat, '_atom_site_aniso_U_23'))
            print('##CIF cell data: ', dat['_cell_length_a'],
                  dat['_cell_length_b'],
                  dat['_cell_length_c'],
                  dat['_cell_angle_alpha'],
                  dat['_cell_angle_beta'],
                  dat['_cell_angle_gamma'])
            print("##CIF volume/ density ", dat.get('_cell_volume', -1),  density)
            print("##CIF  url : ", type(url), url)

        self.add_cifdata(cif_id, mineral.id, pub.id, sgroup.id,
                         formula=formula, compound=compound,
                         formula_title=dat.get('_amcsd_formula_title', '<missing>'),
                         pub_title=dat.get('_publ_section_title', '<missing>'),
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
                         cell_volume=dat.get('_cell_volume', -1),
                         crystal_density=density,
                         url=url)
        return cif_id

    def get_cif(self, cif_id, as_strings=False):
        """get Cif Structure object """
        tab = self.tables['cif']

        cif = self.execone(tab.select().where(tab.c.id==cif_id))
        if cif is None:
            return

        tab_pub  = self.tables['publications']
        tab_auth = self.tables['authors']
        tab_pa   = self.tables['publication_authors']
        tab_min  = self.tables['minerals']
        tab_sp   = self.tables['spacegroups']
        mineral  = self.execone(tab_min.select().where(tab_min.c.id==cif.mineral_id))
        sgroup   = self.execone(tab_sp.select().where(tab_sp.c.id==cif.spacegroup_id))
        hm_symbol = sgroup.hm_notation
        if '%var' in hm_symbol:
            hm_symbol = hm_symbol.split('%var')[0]

        pub = self.get_publications(id=cif.publication_id)[0]

        out = CifStructure(ams_id=cif_id, publication=pub,
                           mineral=mineral, spacegroup=sgroup,
                           hm_symbol=hm_symbol, ams_db=self)

        for attr in ('formula_title', 'compound', 'formula', 'pub_title'):
            setattr(out, attr, getattr(cif, attr, '<missing>'))
        for attr in ('a', 'b', 'c', 'alpha', 'beta', 'gamma',
                     'cell_volume', 'crystal_density'):
            val = getattr(cif, attr, '-1')
            if not as_strings:
                if val is not None:
                    if '(' in val:
                        val = val.split('(')[0]
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
                try:
                    val =  get_optarray(getattr(cif, attr))
                    if val == '0':
                        val = None
                    elif not as_strings:
                        tmp = []
                        for i in range(len(val)):
                            v = val[i]
                            if v in ('?', '.'):
                                v = 2.
                            else:
                                v = float(v)
                            tmp.append(v)
                        val = tmp
                    setattr(out, attr, val)
                except:
                    print(f"could not parse CIF entry for {cif_id} '{attr}': {val} ")

        # we're now ignoring per-cif qvalues
        # out.qval = None
        # if cif.qdat is not None:
        #     out.qval = np.unpackbits(np.array([int(b) for b in b64decode(cif.qdat)],
        #                                       dtype='uint8'))

        out.hkls = None
        if hasattr(cif, 'hkls'):
            out.hkls = cif.hkls

        return out

    def next_cif_id(self):
        """next available CIF ID > 200000 that is not in current table"""
        max_id = 200_000
        tabcif = self.tables['cif']
        for row in self.execall(select(tabcif.c.id).where(tabcif.c.id>200000)):
            if row[0] > max_id:
                max_id = row[0]
        return max_id + 1


    def all_minerals(self):
        names = []
        for row in self.get_all('minerals'):
            if row.name not in names:
                names.append(row.name)
        return names

    def all_authors(self):
        names = []
        for row in self.get_all('authors'):
            if row.name not in names:
                names.append(row.name)
        return names

    def all_journals(self):
        names = []
        for row in self.get_all('publications'):
            if row.journalname not in names:
                names.append(row.journalname)
        return names

    def get_cif_elems(self):
        if self.cif_elems is None:
            out = {}
            for row in self.get_all('cif_elements'):
                cifid = int(row.cif_id)
                if cifid not in out:
                    out[cifid] = []
                if row.element not in out[cifid]:
                    out[cifid].append(row.element)

            self.cif_elems = out
        return self.cif_elems


    def find_cifs(self, id=None, mineral_name=None, author_name=None,
                  journal_name=None, contains_elements=None,
                  excludes_elements=None, strict_contains=False,
                  full_occupancy=False, max_matches=1000):
        """return list of CIF Structures matching mineral, publication, or elements
        """
        if id is not None:
            thiscif = self.get_cif(id)
            if thiscif is not None:
                return [thiscif]

        tabcif = self.tables['cif']
        tabmin = self.tables['minerals']
        tabpub = self.tables['publications']
        tabaut = self.tables['authors']
        tab_ap = self.tables['publication_authors']
        tab_ce = self.tables['cif_elements']

        matches = []
        t0 = time.time()
        if mineral_name is None:
            mineral_name = ''
        mineral_name = mineral_name.strip()

        if mineral_name not in (None, '') and ('*' in mineral_name or
                                               '^' in mineral_name or
                                               '$' in mineral_name):
            pattern = mineral_name.replace('*', '.*').replace('..*', '.*')
            matches = []
            for row in self.get_all('minerals'):
                if re.search(pattern, row.name, flags=re.IGNORECASE) is not None:
                    query = select(tabcif.c.id).where(tabcif.c.mineral_id==row.id)
                    for m in [row[0] for row in self.execall(query)]:
                        if m not in matches:
                           matches.append(m)

            if journal_name not in (None, ''):
                pattern = journal_name.replace('*', '.*').replace('..*', '.*')
                new_matches = []
                for c in matches:
                    pub_id = self.execone(select(tabcif.c.publication_id
                                             ).where(tabcif.c.id==c))
                    this_journal = self.execone(select(tabpub.c.journalname
                                                   ).where(tabpub.c.id==pub_id))
                    if re.search(pattern,  this_journal, flags=re.IGNORECASE) is not None:
                        new_matches.append[c]
                matches = new_matches


        else: # strict mineral name or no mineral name
            args = []
            if mineral_name not in (None, ''):
                args.append(func.lower(tabmin.c.name)==mineral_name.lower())
                args.append(tabmin.c.id==tabcif.c.mineral_id)

            if journal_name not in (None, ''):
                args.append(func.lower(tabpub.c.journalname)==journal_name.lower())
                args.append(tabpub.c.id==tabcif.c.publication_id)

            if author_name not in (None, ''):
                args.append(func.lower(tabaut.c.name)==author_name.lower())
                args.append(tabcif.c.publication_id==tab_ap.c.publication_id)
                args.append(tabaut.c.id==tab_ap.c.author_id)

            query = select(tabcif.c.id)
            if len(args) > 0:
                query = select(tabcif.c.id).where(and_(*args))
            matches = [row[0] for row in self.execall(query)]
            matches = list(set(matches))
        #
        cif_elems = self.get_cif_elems()
        if contains_elements is not None:
            for el in contains_elements:
                new_matches = []
                for row in matches:
                    if row in cif_elems and el in cif_elems[row]:
                        new_matches.append(row)
                matches = new_matches

            if strict_contains:
                excludes_elements = ATOM_SYMS[:]
                for c in contains_elements:
                    if c in excludes_elements:
                        excludes_elements.remove(c)
        if excludes_elements is not None:
            bad = []
            for el in excludes_elements:
                for row in matches:
                    if el in cif_elems[row] and row not in bad:
                        bad.append(row)
            for row in bad:
                matches.remove(row)


        if full_occupancy:
            good = []
            for cif_id in matches:
                cif = self.execone(tabcif.select().where(tabcif.c.id==cif_id))
                occ = get_optarray(getattr(cif, 'atoms_occupancy'))
                if occ in ('0', 0, None):
                    good.append(cif_id)
                else:
                    try:
                        min_wt = min([float(x) for x in occ])
                    except:
                        min_wt = 0
                    if min_wt > 0.96:
                        good.append(cif_id)
            matches = good

        if len(matches) > max_matches:
            matches = matches[:max_matches]
        return [self.get_cif(cid) for cid in matches]

    def set_hkls(self, cifid, hkls, degens):
        ctab = self.tables['cif']
        packed_hkls = pack_hkl_degen(hkls, degens)
        self.update(ctab, whereclause=(ctab.c.id == cifid), hkls=packed_hkls)
        return packed_hkls

def get_amcsd(download_full=True, timeout=30):
    """return instance of the AMCSD CIF Database

    Returns:
        AMCSD database
    Example:

    """
    global _CIFDB
    if _CIFDB is not None:
        return _CIFDB

    dbfull = os.path.join(user_larchdir, AMCSD_FULL)
    if os.path.exists(dbfull):
        _CIFDB = AMCSD(dbfull)
        return _CIFDB
    t0 = time.time()
    if download_full:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        for src in SOURCE_URLS:
            url = f"{src:s}/{AMCSD_FULL:s}"
            req = requests.get(url, verify=True, timeout=timeout)
            if req.status_code == 200:
                break
        if req.status_code == 200:
            with open(dbfull, 'wb') as fh:
                fh.write(req.content)
            print("Downloaded  %s : %.2f sec" % (dbfull, time.time()-t0))
            time.sleep(0.25)
            _CIFDB = AMCSD(dbfull)
            return _CIFDB
    # finally download of full must have failed
    return AMCSD()

def get_cif(ams_id):
    """
    get CIF Structure by AMS ID
    """
    db = get_amcsd()
    return db.get_cif(ams_id)

def find_cifs(mineral_name=None, journal_name=None, author_name=None,
              contains_elements=None, excludes_elements=None,
              strict_contains=False, full_occupancy=False):

    """
    return a list of CIF Structures matching a set of criteria:

     mineral_name:  case-insensitive match of mineral name
     journal_name:
     author_name:
     containselements:  list of atomic symbols required to be in structure
     excludes_elements:  list of atomic symbols required to NOT be in structure
     strict_contains:    `contains_elements` is complete -- no other elements


    """
    db = get_amcsd()
    return db.find_cifs(mineral_name=mineral_name,
                        journal_name=journal_name,
                        author_name=author_name,
                        contains_elements=contains_elements,
                        excludes_elements=excludes_elements,
                        strict_contains=strict_contains,
                        full_occupancy=full_occupancy)
