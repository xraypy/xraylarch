import os
from random import Random
from io import StringIO
import numpy as np

from xraydb import atomic_symbol, atomic_number, xray_edge
from larch.utils import fix_varname, strict_ascii, gformat

from .amcsd_utils import PMG_CIF_OPTS, CifParser, Molecule, SpacegroupAnalyzer

rng = Random()

def get_atom_map(structure):
    """generalization of pymatgen atom map
    Returns:
        dict of ipots
    """
    unique_pot_atoms = []
    all_sites  = []
    for site in structure:
        for elem in site.species.elements:
            if elem.symbol not in unique_pot_atoms:
                unique_pot_atoms.append(elem.symbol)

    atom_map = {}
    for i, atom in enumerate(unique_pot_atoms):
        atom_map[atom] = i + 1
    return atom_map


def read_cif_structure(ciftext):
    """read CIF text, return CIF Structure

    Arguments
    ---------
      ciftext (string): text of CIF file

    Returns
    -------
      pymatgen Structure object
    """
    if CifParser is None:
        raise ValueError("CifParser from pymatgen not available. Try 'pip install pymatgen'.")

    if os.path.exists(ciftext):
        ciftext = open(ciftext, 'r').read()
    try:
        cifstructs = CifParser(StringIO(ciftext), **PMG_CIF_OPTS)
        parse_ok = True
    except:
        parse_ok = False

    try:
        cstruct = cifstructs.parse_structures()[0]
    except:
        raise ValueError('could not get structure from text of CIF')
    return cstruct

def fcompact(val):
    """format a float value, removing extra trailing zeros"""
    val = f'{val:.6f}'
    while val.endswith('0'):
        val = val[:-1]
    if val.endswith('.'):
        val = val + '0'
    return val


def site_label(site):
    coords = ','.join([fcompact(s) for s in site.frac_coords])
    return f'{site.species_string}[{coords}]'

class CIF_Cluster():
    """
    CIF structure for generating clusters around a specific crystal site,
    as used for XAS calculations

    """
    def __init__(self, ciftext=None, filename=None, absorber=None,
                 absorber_site=1, with_h=False, cluster_size=8.0):
        self.filename = filename
        self.ciftext = ciftext
        self.set_absorber(absorber)
        self.absorber_site = absorber_site
        self.with_h = with_h
        self.cluster_size = cluster_size
        self.struct = None

        if isinstance(self.absorber, int):
            self.absorber   = atomic_symbol(self.absorber)
        if isinstance(self.absorber, str):
            self.absorber_z   = atomic_number(self.absorber)

        if ciftext is None and filename is not None:
            self.ciftext = open(filename, 'r').read()

        if self.ciftext is not None:
            self.parse_ciftext(self.ciftext)

    def set_absorber(self, absorber=None):
        self.absorber_z = None
        self.absorber = absorber
        if isinstance(self.absorber, int):
            self.absorber = atomic_symbol(self.absorber)
        if isinstance(self.absorber, str):
            self.absorber_z = atomic_number(self.absorber)

    def parse_ciftext(self, ciftext=None, absorber=None):
        if absorber is not None:
            self.set_absorber(absorber)
        if ciftext is not None:
            self.ciftext = ciftext
        self.struct = read_cif_structure(self.ciftext)
        self.get_cif_sites()

    def get_cif_sites(self):
        """parse sites of CIF structure to get several components:

           struct.sites:   list of all sites as parsed by pymatgen
           site_labels:    list of site labels
           unique_sites:   list of (site[0], wyckoff sym) for unique xtal sites
           unique_map:     mapping of all site_labels to unique_site index
           absorber_sites: list of unique sites with absorber

        """
        # get equivalent sites, mapping of all sites to unique sites,
        # and list of site indexes with absorber

        self.formula = self.struct.composition.reduced_formula
        sga = SpacegroupAnalyzer(self.struct)
        self.space_group = sga.get_symmetry_dataset().international

        sym_struct = sga.get_symmetrized_structure()
        wyckoff_symbols = sym_struct.wyckoff_symbols

        self.site_labels = []
        for site in self.struct.sites:
            self.site_labels.append(site_label(site))

        self.unique_sites = []
        self.unique_map = {}
        self.absorber_sites = []
        absorber = '~'*30 if self.absorber is None else self.absorber
        for i, sites in enumerate(sym_struct.equivalent_sites):
            self.unique_sites.append((sites[0], len(sites), wyckoff_symbols[i]))
            for site in sites:
                self.unique_map[site_label(site)] = (i+1)
            if absorber in site.species_string:
                self.absorber_sites.append(i)

    def build_cluster(self, absorber=None, absorber_site=1, cluster_size=None):
        if absorber is not None:
            self.set_absorber(absorber)
        if cluster_size is None:
            cluster_size = self.cluster_size

        csize2 = cluster_size**2

        site_atoms = {}  # map xtal site with list of atoms occupying that site
        site_tags = {}

        for i, site in enumerate(self.struct.sites):
            label = site_label(site)
            s_unique = self.unique_map.get(label, 0)
            site_species = [e.symbol for e in site.species]
            if len(site_species) > 1:
                s_els = [s.symbol for s in site.species.keys()]

                s_wts = [s for s in site.species.values()]
                site_atoms[i] = rng.choices(s_els, weights=s_wts, k=1000)
                site_tags[i] = f'({site.species_string:s})_{1+i:d}'
            else:
                site_atoms[i] = [site_species[0]] * 1000
                site_tags[i] = f'{site.species_string:s}_{s_unique:d}'

        # atom0 = self.struct[a_index]
        atom0 = self.unique_sites[absorber_site-1][0]
        sphere = self.struct.get_neighbors(atom0, self.cluster_size)

        self.symbols = [self.absorber]
        self.coords = [[0, 0, 0]]
        self.tags = [f'{self.absorber:s}_{absorber_site:d}']

        for i, site_dist in enumerate(sphere):
            s_index = site_dist[0].index
            site_symbol = site_atoms[s_index].pop()

            coords = site_dist[0].coords - atom0.coords
            if (coords[0]**2 + coords[1]**2  + coords[2]**2) < csize2:
                self.tags.append(site_tags[s_index])
                self.symbols.append(site_symbol)
                self.coords.append(coords)

        self.molecule = Molecule(self.symbols, self.coords)

##

def cif_cluster(ciftext=None, filename=None, absorber=None):
    "return list of sites for the structure"
    return CIF_Cluster(ciftext=ciftext, filename=filename, absorber=absorber)

def cif2feffinp(ciftext, absorber, edge=None, cluster_size=8.0, absorber_site=1,
                extra_titles=None, with_h=False, version8=True, rng_seed=None):

    """convert CIF text to Feff8 or Feff6l input file

    Arguments
    ---------
      ciftext (string):         text of CIF file or name of the CIF file.
      absorber (string or int): atomic symbol or atomic number of absorbing element
                                (see Note 1)
      edge (string or None):    edge for calculation (see Note 2)     [None]
      cluster_size (float):     size of cluster, in Angstroms         [8.0]
      absorber_site (int):      index of site for absorber (see Note 3) [1]
      extra_titles (list of str or None): extra title lines to include [None]
      with_h (bool):            whether to include H atoms [False]
      version8 (bool):          whether to write Feff8l input (see Note 5)[True]
      rng_seed (int or None):   seed for RNG to get reproducible occupancy selections [None]
    Returns
    -------
      text of Feff input file

    Notes
    -----
      1. absorber is the atomic symbol or number of the absorbing element, and
         must be an element in the CIF structure.
      2. If edge is a string, it must be one of 'K', 'L', 'M', or 'N' edges (note
         Feff6 supports only 'K', 'L3', 'L2', and 'L1' edges). If edge is None,
         it will be assigned to be 'K' for absorbers with Z < 58 (Ce, with an
         edge energy < 40 keV), and 'L3' for absorbers with Z >= 58.
      3. for structures with multiple sites for the absorbing atom, the site
         can be selected by the order in which they are listed in the sites
         list. This depends on the details of the CIF structure, which can be
         found with `cif_sites(ciftext)`, starting counting by 1.
      5. if version8 is False, outputs will be written for Feff6l

    """
    global rng
    if rng_seed is not None:
        rng.seed(rng_seed)

    cluster = CIF_Cluster(ciftext=ciftext, absorber=absorber)
    cluster.build_cluster(absorber_site=absorber_site, cluster_size=cluster_size)

    mol = cluster.molecule

    absorber = cluster.absorber
    absorber_z = cluster.absorber_z


    if edge is None:
        edge = 'K' if absorber_z < 58 else 'L3'

    edge_energy = xray_edge(absorber, edge).energy
    edge_comment = f'{absorber:s} {edge:s} edge, around {edge_energy:.0f} eV'

    unique_pot_atoms = []
    for site in cluster.struct:
        for elem in site.species.elements:
            if elem.symbol not in unique_pot_atoms:
                unique_pot_atoms.append(elem.symbol)

    atoms_map = {}
    for i, atom in enumerate(unique_pot_atoms):
        atoms_map[atom] = i + 1

    if absorber not in atoms_map:
        atlist = ', '.join(atoms_map.keys())
        raise ValueError(f'atomic symbol {absorber:s} not listed in CIF data: ({atlist})')

    out_text = ['*** feff input generated by xraylarch cif2feff using pymatgen ***']


    out_text.append(f'TITLE Formula: {cluster.formula:s}')
    out_text.append(f'TITLE SpaceGroup: {cluster.space_group:s}')

    if extra_titles is not None:
        for etitle in extra_titles[:]:
            out_text.append('TITLE ' + etitle)

    out_text.append('* ')
    out_text.append( '* crystallographic sites:')
    out_text.append(f'*  to change absorber site, re-run using `absorber_site`')
    out_text.append(f'*  with the corresponding site index (counting from 1)')
    out_text.append('* site    X        Y        Z      Wyckoff     species')

    for i, dat in enumerate(cluster.unique_sites):
        site, n, wsym = dat
        fc = site.frac_coords
        species_string = fix_varname(site.species_string.strip())
        marker = '  <- absorber' if  ((i+1) == absorber_site) else ''
        s1 = f'{i+1:3d}   {fc[0]:.6f} {fc[1]:.6f} {fc[2]:.6f}'
        s2 = f'{wsym}     {species_string:s} {marker:s}'
        out_text.append(f'* {s1}  {s2}')

    out_text.extend(['* ', '', ''])
    if version8:
        out_text.append(f'EDGE    {edge:s}')
        out_text.append('S02     1.0')
        out_text.append('CONTROL 1 1 1 1 1 1')
        out_text.append('PRINT   1 0 0 0 0 3')
        out_text.append('EXAFS   20.0')
        out_text.append('NLEG     6')
        out_text.append(f'RPATH   {cluster_size:.2f}')
        out_text.append('*SCF    5.0')

    else:
        edge_index = {'K': 1, 'L1': 2, 'L2': 3, 'L3': 4}[edge]
        out_text.append(f'HOLE    {edge_index:d}  1.0  * {edge_comment:s} (2nd number is S02)')
        out_text.append('CONTROL 1 1 1 0 * phase, paths, feff, chi')
        out_text.append('PRINT   1 0 0 0')
        out_text.append(f'RMAX    {cluster_size:.2f}')

    out_text.extend(['', 'EXCHANGE 0', '',
                     '*  POLARIZATION  0 0 0', '',
                     'POTENTIALS',  '*    IPOT  Z   Tag'])

    # loop to find atoms actually in cluster, in case some atom
    # (maybe fractional occupation) is not included

    at_lines = [(0, mol[0].x, mol[0].y, mol[0].z, 0, absorber, cluster.tags[0])]
    ipot_map = {}
    next_ipot = 0
    for i, site in enumerate(mol[1:]):
        sym = site.species_string
        if sym == 'H' and not with_h:
            continue
        if sym in ipot_map:
            ipot = ipot_map[sym]
        else:
            next_ipot += 1
            ipot_map[sym] = ipot = next_ipot

        dist = mol.get_distance(0, i+1)
        at_lines.append((dist, site.x, site.y, site.z, ipot, sym, cluster.tags[i+1]))

    ipot, z = 0, absorber_z
    out_text.append(f'   {ipot:4d}  {z:4d}   {absorber:s}')
    for sym, ipot in ipot_map.items():
        z = atomic_number(sym)
        out_text.append(f'   {ipot:4d}  {z:4d}   {sym:s}')

    out_text.append('')
    out_text.append('ATOMS')
    out_text.append(f'*    x         y         z       ipot  tag   distance  site_info')

    acount = 0
    for dist, x, y, z, ipot, sym, tag in sorted(at_lines, key=lambda x: x[0]):
        acount += 1
        if acount > 500:
            break
        sym = (sym + ' ')[:2]
        out_text.append(f'   {x: .5f}  {y: .5f}  {z: .5f} {ipot:4d}   {sym:s}    {dist:.5f}  * {tag:s}')

    out_text.append('')
    out_text.append('* END')
    out_text.append('')
    return strict_ascii('\n'.join(out_text))
