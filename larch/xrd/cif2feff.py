import os
import random
from io import StringIO

HAS_PYMATGEN = False
try:
    from pymatgen.io.cif import CifParser
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.core import Molecule
    HAS_PYMATGEN = True
except:
    HAS_PYMATGEN = False

from xraydb import atomic_symbol, atomic_number, xray_edge
from larch.io.fileutils import gformat


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
      ciftext (string):         text of CIF file or name of the CIF file.

    Returns
    -------
      pymatgen Structure object
    """
    if not HAS_PYMATGEN:
        raise ImportError('pymatgen required')
    try:
        cifstructs = CifParser(StringIO(ciftext))
        parse_ok = True
        file_found = True
    except:
        parse_ok = False
        file_found = False
        if os.path.exists(ciftext):
            file_found = True
            try:
                cifstructs = CifParser(ciftext)
                parse_ok = True
            except:
                parse_ok = False

    try:
        cstruct = cifstructs.get_structures()[0]
    except:
        raise ValueError('could not get structure from text of CIF file')    

    if not parse_ok:
        if not file_found:
            raise FileNotFoundError(f'file {ciftext:s} not found')
        else:
            raise ValueError('invalid text of CIF file')
    return cstruct

def cif_sites(ciftext):
    "return list of sites for the structure"
    cstruct = read_cif_structure(ciftext)
    return cstruct.sites

def cif2feff6l(ciftext, absorber, edge=None, cluster_size=8.0, absorber_site=0,
               extra_titles=None):
    """convert CIF text to Feff6l input

    Arguments
    ---------
      ciftext (string):         text of CIF file or name of the CIF file.
      absorber (string or int): atomic symbol or atomic number of absorbing element
                                (see Note 1)
      edge (string or None):    edge for calculation (see Note 2)     [None]
      cluster_size (float):     size of cluster, in Angstroms         [8.0]
      absorber_site (int):      index of site for absorber (see Note 3) [1]

    Returns
    -------
      text of Feff input file

    Notes
    -----
      1. absorber is the atomic symbol or number of the absorbing element, and
         must be an element in the CIF structure.
      2. If edge is a string, it must be one of 'K', 'L1', 'L2', or 'L3' (the
         edges that Feff6 supports). If edge is None, it will be assigned to
         be 'K' for absorbers with Z < 58 (Ce, with an edge energy < 40 keV),
         and 'L3' for absorbers with Z >= 58.
      3. for structures with multiple sites for the absorbing atom, the site
         can be selected by the order in which they are listed in the sites
         list. This depends on the details of the CIF structure, which can be
         found with `cif_sites(ciftext)`, starting counting by 0.

    """
    cstruct = read_cif_structure(ciftext)

    sgroup = SpacegroupAnalyzer(cstruct).get_symmetry_dataset()
    space_group = sgroup["international"]

    if isinstance(absorber, int):
        absorber   = atomic_symbol(absorber_z)
    absorber_z = atomic_number(absorber)

    if edge is None:
        edge = 'K' if absorber_z < 58 else 'L3'
    edge_index = {'K': 1, 'L1': 2, 'L2': 3, 'L3': 4}[edge]
    edge_energy = xray_edge(absorber, edge).energy
    edge_comment = f'{absorber:s} {edge:s} edge, around {edge_energy:.0f} eV'

    atoms_map = get_atom_map(cstruct)
    if absorber not in atoms_map:
        atlist = ', '.join(atoms_map.keys())
        raise ValueError(f'atomic symbol {absorber:s} not listed in CIF data: ({atlist})')


    site_atoms = {}  # map Xtal site with list of atoms occupying that site
    absorber_count = 0
    for site_index, site in enumerate(cstruct.sites):
        site_species = [e.symbol for e in site.species]

        if len(site_species) > 1:
            s_els = [s.symbol for s in site.species.keys()]
            s_wts = [s for s in site.species.values()]
            site_atoms[site_index] = random.choices(s_els, weights=s_wts, k=1000)
        else:
            site_atoms[site_index] = [site_species[0]] * 1000            
        if absorber in site_species:
            absorber_count += 1
            if absorber_count == absorber_site:
                absorber_index = site_index

    
    absorber_comment = f'* note: using absorber at site {absorber_index:d} above, selected as "{absorber:s}, absorber_site={absorber_site:d}" '

    center = cstruct[absorber_index].coords
    sphere = cstruct.get_neighbors(cstruct[absorber_index], cluster_size)
    symbols = [absorber]
    coords = [[0, 0, 0]]
    for i, site_dist in enumerate(sphere):
        s_index = site_dist[0].index
        site_symbol = site_atoms[s_index].pop()
        symbols.append(site_symbol)
        coords.append(site_dist[0].coords - center)
    cluster = Molecule(symbols, coords)

    out_text = ['*** feff6 input generated by cif2feff6l using pymatgen ***']

    if extra_titles is not None:
        for etitle in extra_titles[:]:
            
            if not etitle.startswith('TITLE '):
                etitle = 'TITLE ' + etitle
            out_text.append(etitle)

    out_text.append(f'TITLE Formula:    {cstruct.composition.reduced_formula:s}')
    out_text.append(f'TITLE SpaceGroup: {space_group:s}')
    out_text.append(f'TITLE # sites:    {cstruct.num_sites}')
    for i, site in enumerate(cstruct):
        out_text.append(f'* {i:3d}  {site.species_string:s}  {site.frac_coords[0]:.6f} {site.frac_coords[1]:.6f} {site.frac_coords[2]:.6f}')

    out_text.extend([absorber_comment, ''])
    out_text.append(f'HOLE    {edge_index:d}  1.0  * {edge_comment:s} (2nd number is S02)')
    out_text.append(f'CONTROL 1 1 1 0 * phase, paths, feff, chi')
    out_text.append(f'PRINT   1 0 0 0')
    out_text.append(f'RMAX    {cluster_size:.2f}')
    out_text.extend(['', 'POTENTIALS', '*    IPOT  Z   Tag'])

    ipot, z = 0, absorber_z
    out_text.append(f'   {ipot:4d}  {z:4d}   {absorber:s}')
    for tag in atoms_map.keys():
        ipot += 1
        z = atomic_number(tag)
        out_text.append(f'   {ipot:4d}  {z:4d}   {tag:s}')

    out_text.append('')
    out_text.append('ATOMS')
    out_text.append('*    x         y         z       ipot  tag     distance')

    at_lines = [(cluster[0].x, cluster[0].y, cluster[0].z, 0, absorber, 0)]

    for i, site in enumerate(cluster[1:]):
        site_symbol = str(site.species_string)
        ipot = atoms_map[site_symbol]
        at_lines.append((site.x, site.y, site.z,
                      ipot, site_symbol, cluster.get_distance(0, i+1)))

    for x, y, z, ipot, sym, dist in sorted(at_lines, key=lambda x: x[5]):
        sym = (sym + '     ')[:4]
        out_text.append(f'   {x: .5f}  {y: .5f}  {z: .5f} {ipot:4d}   {sym:s}    {dist:.5f}')

    out_text.append('')
    out_text.append('* END')
    out_text.append('')
    return '\n'.join(out_text)


        
