#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Struct2XAS: convert CIFs and XYZs files to FDMNES and FEFF inputs
"""
# main imports
import os
import json
import time
import tempfile
import numpy as np

# pymatgen
from pymatgen.core import Structure, Element, Lattice
from pymatgen.io.xyz import XYZ
from pymatgen.io.cif import CifParser
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

import larch.utils.logging as logging
from larch.utils import mkdir, unixpath
from larch.utils.strutils import fix_filename, unique_name, strict_ascii
from larch.site_config import user_larchdir
from larch.io import read_ascii
from larch.math.convolution1D import lin_gamma, conv

try:
    import pandas as pd
    from pandas.io.formats.style import Styler

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import py3Dmol

    HAS_PY3DMOL = True
except ImportError:
    HAS_PY3DMOL = False


__author__ = ["Beatriz G. Foschiani", "Mauro Rovezzi"]
__email__ = ["beatrizgfoschiani@gmail.com", "mauro.rovezzi@esrf.fr"]
__credits__ = ["Jade Chongsathapornpong", "Marius Retegan"]
__version__ = "2023.3.0"


# initialize the logger
logger = logging.getLogger("struct2xas", level="INFO")


def _get_timestamp() -> str:
    """return a custom time stamp string: YYY-MM-DD_HHMM"""
    return "{0:04d}-{1:02d}-{2:02d}_{3:02d}{4:02d}".format(*time.localtime())


def _pprint(matrix):
    """pretty print a list of lists (in case Pandas is not available)
    from: https://stackoverflow.com/questions/13214809/pretty-print-2d-list
    an alternative could be: https://pypi.org/project/tabulate/
    """
    s = [[str(e) for e in row] for row in matrix]
    lens = [max(map(len, col)) for col in zip(*s)]
    fmt = "\t".join("{{:{}}}".format(x) for x in lens)
    table = [fmt.format(*row) for row in s]
    print("\n".join(table))


def xyz2struct(molecule):
    """Convert pymatgen molecule to dummy pymatgen structure"""

    alat, blat, clat = 1, 1, 1

    # Set the lattice dimensions in each direction
    for i in range(len(molecule) - 1):
        if molecule.cart_coords[i][0] > molecule.cart_coords[i + 1][0]:
            alat = molecule.cart_coords[i][0]
        if molecule.cart_coords[i][1] > molecule.cart_coords[i + 1][1]:
            blat = molecule.cart_coords[i][1]
        if molecule.cart_coords[i][2] > molecule.cart_coords[i + 1][2]:
            clat = molecule.cart_coords[i][2]

    # Set the lattice dimensions in each direction
    lattice = Lattice.from_parameters(
        a=alat, b=blat, c=clat, alpha=90, beta=90, gamma=90
    )

    # Create a list of species
    species = [Element(sym) for sym in molecule.species]

    # Create a list of coordinates
    coords = molecule.cart_coords

    # Create the Structure object
    struct = Structure(lattice, species, coords, coords_are_cartesian=True)
    return struct


def structure_folders():
    """
    return folders under USER_LARCHDIR for FDMNES, Feff,  and structure files,
    making sure each exists
    """
    folders = {}
    for name in ("feff", "fdmnes", "mp_structs"):
        folders[name] = unixpath(os.path.join(user_larchdir, name))
        mkdir(folders[name])
    return folders


class Struct2XAS:
    """Class to convert data from CIF and XYZ files to FDMNES and FEFF inputs"""

    def __init__(self, file, abs_atom) -> None:
        """

        Arguments
        ---------
        file : str
            full path string to cif or xyz file
        abs_atom : str
            Absorber element in the structure, e.g.: "Fe", "Ni".

        Returns
        -------
        None

        ..note::

        --> IMPORTANT: <--

        for xyz files:
            Structures from xyz files are always considered non-symmetric for
            the lack of lattice information. For creating the object from an
            XYZ file, a non-symmetric `structure` object from pymatgen is
            generated (spacegroup: P1) from a `molecule` one via
            :func:`xyz2struct`. The lattice parameters chosen for this
            structure are arbitrary and are based on the size of the molecule,
            as are the fractional coordinates. Therefore, the analysis of this
            structure is limited to the central atoms and is not valid for
            atoms at the border of the molecule.

        for cif files:
            For creating the object from cif file, a pymatgen structure is
            generated with symmetry information from cif file.
        """

        self.file = file
        self.abs_atom = abs_atom
        self.frame = 0
        self.abs_site = 0
        self.is_cif = False
        self.is_xyz = False
        self.read_structure(file)
        self.nabs_sites = len(self.get_abs_sites())
        self.elems = self._get_elems()
        self.species = self._get_species()
        self.parent_path = user_larchdir
        self.folders = structure_folders()
        logger.info(
            f"Frames: {self.nframes}, Absorbing sites: {self.nabs_sites}. (Indexes for frames and abs_sites start at 0)"
        )

    def set_frame(self, frame=0):
        """For multiframe xyz file, set the frame index site."""
        self.frame = frame
        if self.molecules is not None:
            self.struct = xyz2struct(self.molecules[self.frame])
            self.mol = self.molecules[self.frame]
        else:
            logger.error("single frame structure")
        logger.debug(f"frame idx: {frame} ")

    def get_frame(self):
        """For multiframe xyz file, get the frame index site."""
        return self.frame

    def set_abs_site(self, abs_site=0):
        """Set the crystallographic index site for the absorbing atom."""
        try:
            self.get_abs_sites()[abs_site]
        except IndexError:
            logger.error("absorber site index out of range")
            raise IndexError("absorber site index out of range")
        logger.debug(f"abs_site idx: {abs_site} ")
        self.abs_site = abs_site

    def get_abs_site(self):
        """Get the crystallographic index site for the absorbing atom."""
        return self.abs_site

    def _get_elems(self):
        """Get elements present in the structure"""
        elems_list = []
        for _, elem in enumerate(self.struct):
            # if self.is_cif:
            for e in elem.species.elements:
                if e.name not in elems_list:
                    elems_list.append(e.name)

            # if self.is_xyz:
            #     if elem.species_string not in elems_list:
            #         elems_list.append(elem.species_string)

        return elems_list

    def _get_species(self):
        """Get elements present in the structure"""
        species_list = []
        species_list_occu = []
        for _, elem in enumerate(self.struct):
            if not self.full_occupancy:
                if str(elem.species) not in species_list_occu:
                    species_list_occu.append(str(elem.species))
            self.atoms_occu = species_list_occu

            for e in elem.species.elements:
                if str(e) not in species_list:
                    species_list.append(str(e))

        return species_list

    def read_structure(self, file):
        """Read and initialize the structure/molecule from the input file"""
        # Split the file name and extension
        self.file = file
        if os.path.isfile(self.file):
            # file_dirname = os.path.dirname(file)
            file = os.path.basename(self.file)
            split_file = os.path.splitext(file)
            self.file_name = split_file[0]
            self.file_ext = split_file[1]
        else:
            self.file_name, self.file_ext = None, None
            errmsg = f"{self.file} not found"
            logger.error(errmsg)
            raise FileNotFoundError(errmsg)

        if self.file_ext == ".cif":
            self.is_cif = True
            self.xyz = None
            self.molecules = None
            self.mol = None
            self.nframes = 1
            self.cif = CifParser(self.file)
            self.struct = Structure.from_file(self.file)
            # self.struct = self.cif.get_structures()[0]  #: NOT WORKING!
            logger.debug("structure created from a CIF file")
        elif self.file_ext == ".xyz":
            self.is_xyz = True
            self.cif = None
            self.xyz = XYZ.from_file(self.file)
            self.molecules = self.xyz.all_molecules
            self.mol = self.molecules[self.frame]
            self.nframes = len(self.molecules)
            self.struct = xyz2struct(self.mol)
            logger.debug("structure created from a XYZ file")
        elif self.file_ext == ".mpjson":
            self.is_xyz = False
            self.is_cif = True
            self.molecules = None
            self.mol = None
            self.nframes = 1
            self.struct = Structure.from_dict(json.load(open(self.file, "r")))
            logger.debug("structure created from JSON file")

        else:
            errmsg = "only CIF and XYZ files are currently supported"
            logger.error(errmsg)
            raise NotImplementedError(errmsg)

    def _get_atom_sites(self):
        """get atomic positions from the cif file

        Returns
        -------
        atom_sites : list of list
            same output as self.get_abs_sites()
        """
        if not self.is_cif:
            errmsg = "not a CIF file!"
            logger.error(errmsg)
            raise NotImplementedError(errmsg)
        cf = self.cif.as_dict()
        cf = cf[list(cf.keys())[0]]

        atom_lists = []
        try:
            labels = cf["_atom_site_label"]
            natoms = len(labels)
            try:
                type_symbols = cf["_atom_site_type_symbol"]
            except KeyError:
                type_symbols = None
                pass
            if type_symbols is None:
                atom_lists.append(labels)
            else:
                atom_lists.append(type_symbols)
            atom_lists.append(cf["_atom_site_fract_x"])
            atom_lists.append(cf["_atom_site_fract_y"])
            atom_lists.append(cf["_atom_site_fract_z"])
            atom_lists.append(cf["_atom_site_occupancy"])
        except KeyError:
            errmsg = (
                "the CIF file does not contain all required `_atom_site_*` information"
            )
            logger.error(errmsg)
            raise KeyError(errmsg)
        try:
            atom_lists.append(cf["_atom_site_symmetry_multiplicity"])
        except KeyError:
            atom_lists.append(["?"] * natoms)

        try:
            atom_lists.append(cf["_atom_site_Wyckoff_symbol"])
        except KeyError:
            atom_lists.append(["?"] * natoms)

        atom_sites = []
        for ikey, key in enumerate(zip(*atom_lists)):
            atom_row = [
                ikey,
                key[0],
                np.array(
                    [key[1].split("(")[0], key[2].split("(")[0], key[3].split("(")[0]],
                    dtype=float,
                ),
                key[5] + key[6],
                np.array([None, None, None]),
                float(key[4]),
                None,
            ]
            atom_sites.append(atom_row)

        # atom_site_keys = [key for key in cf.keys() if '_atom_site' in key]
        # atom_lists = [cf[key] for key in atom_site_keys]
        # atom_sites = []
        # for ikey, key in enumerate(zip(*atom_lists)):
        #    atom_row = [ikey, key[1], np.array([key[4], key[5], key[6]], dtype=float), key[2] + key[3], np.array([None, None, None]), float(key[8]), None]
        #    atom_sites.append(atom_row)
        return atom_sites

    def _get_idx_struct(self, atom_coords):
        """get the index of the pymatgen Structure corresponding to the given atomic coordinates"""
        for idx, atom in enumerate(self.struct):
            if np.allclose(atom.coords, atom_coords, atol=0.001) is True:
                return idx
        errmsg = f"atomic coordinates {atom_coords} not found in self.struct"
        logger.error(errmsg)
        # raise IndexError(errmsg)
        return None

    def get_abs_sites(self):
        """
        Get information about the possible absorbing sites present of the
        structure.

        ..note:: If the structure has a readable symmetry given by a cif file,
        the method will return just equivalent sites. If the structure does not
        have symmetry or the symmetry is not explicit in the files, this method
        will return all possible sites for absorber atoms.

        Returns
        -------
        abs_sites : list of lists
            The lists inside the list contain the following respective
            information:
            [
            abs_idx,        # index identifier of the absorber site
                             #     used by self.set_abs_site().
            species_string,  #  The specie for absorber sites.
            frac_coords,     # Fractional coordinate position
                             #   If the structure was created using xyz file,
                             #   the frac. coords. are arbitrary and the lattice
                             #   parameters are based on the molecule size.
            wyckoff_symbols, # Wyckoff site for absorber sites.
                             #      For structures created from xyz
                             #      files, Wyckoff sites are always equal to 1a.
                             #      (No symmetry)
            cart_coords,     # Cartesian coordinate position
            occupancy,       # Occupancy for absorber sites. For structures
                             #      created from xyz files,
                             #      occupancy are always equal to 1.
            structure index  # Original index in the pymatgen structure
                             #  (private usage)
            ]
        """

        abs_sites = []
        if self.is_cif:
            sym_struct = SpacegroupAnalyzer(self.struct).get_symmetrized_structure()

            # Get multiples sites for absorber atom
            for idx, sites in enumerate(sym_struct.equivalent_sites):
                sites = sorted(
                    sites, key=lambda s: tuple(abs(x) for x in s.frac_coords)
                )
                site = sites[0]
                abs_row = [idx, site.species_string]
                abs_row.append([j for j in np.round(site.frac_coords, 4)])
                abs_row.append(sym_struct.wyckoff_symbols[idx])
                abs_row.append(np.array([j for j in np.round(site.coords, 4)]))
                if self.abs_atom in abs_row[1]:
                    try:
                        ats_occ = abs_row[1].split(",")
                        at_occ = [at for at in ats_occ if self.abs_atom in at][0]
                        occupancy = float(at_occ.split(":")[1])
                        self.full_occupancy = False
                    except Exception:
                        occupancy = 1
                        self.full_occupancy = True
                    abs_row.append(occupancy)
                    abs_row.append(self._get_idx_struct(abs_row[4]))
                    abs_sites.append(abs_row)

        if self.is_xyz:
            self.full_occupancy = True
            k = 0
            for idx, elem in enumerate(self.struct):
                if f"{self.abs_atom}" in elem:
                    abs_sites += [
                        (
                            int(f"{k}"),
                            (str(elem.specie)) + f"{k}",
                            elem.coords.round(4),
                            "1a",
                            elem.coords.round(4),
                            1,
                            idx,
                        )
                    ]
                    k += 1
        if len(abs_sites) == 0:
            _errmsg = f"---- Absorber {self.abs_atom} not found ----"
            logger.error(_errmsg)
            raise AttributeError(_errmsg)
        return abs_sites

    def get_abs_sites_info(self):
        """pretty print for self.get_abs_sites()"""
        header = [
            "idx_abs",
            "specie",
            "frac_coords",
            "wyckoff_site",
            "cart_coords",
            "occupancy",
            "idx_in_struct",
        ]
        abs_sites = self.get_abs_sites()
        if HAS_PANDAS:
            df = pd.DataFrame(
                abs_sites,
                columns=header,
            )
            df = Styler(df).hide(axis="index")
            return df
        else:
            matrix = [header]
            matrix.extend(abs_sites)
            _pprint(matrix)

    def get_atoms_from_abs(self, radius):
        """Get atoms in sphere from absorbing atom with certain radius"""
        abs_sites = self.get_abs_sites()

        if self.is_cif:
            nei_list = self.struct.get_sites_in_sphere(
                abs_sites[self.abs_site][4], float(radius)
            )  # list os neighbors atoms in sphere
            sites = []

            for i in range(len(nei_list)):
                nei_list[i].cart_coords = (
                    nei_list[i].coords - abs_sites[self.abs_site][4]
                )

            for i, _ in enumerate(nei_list):
                if np.allclose(nei_list[i].cart_coords, [0, 0, 0], atol=0.01) is True:
                    sites.append(
                        [
                            nei_list[i],
                            f"{self.abs_atom}(abs)",
                            0.000,
                            {f"{self.abs_atom}(abs)": 1},
                        ]
                    )
                    nei_list.remove(nei_list[i])

            for i in range(len(nei_list)):
                occu_dict = dict(nei_list[i].as_dict()["species"])
                sites += [
                    [
                        nei_list[i],
                        str(nei_list[i].species.elements[0]),
                        round(np.linalg.norm(nei_list[i].cart_coords - [0, 0, 0]), 5),
                        occu_dict,
                    ]
                ]
        if self.is_xyz:
            nei_list = self.mol.get_sites_in_sphere(
                abs_sites[self.abs_site][4], float(radius)
            )  # list os neighbors atoms in sphere
            sites = []

            for i in range(len(nei_list)):
                nei_list[i].cart_coords = (
                    nei_list[i].coords - abs_sites[self.abs_site][4]
                )

            for i, _ in enumerate(nei_list):
                if np.allclose(nei_list[i].cart_coords, [0, 0, 0], atol=0.01) is True:
                    sites.append([nei_list[i], f"{self.abs_atom}(abs)", 0.000])
                    nei_list.remove(nei_list[i])

            sites += [
                [
                    nei_list[i],
                    nei_list[i].species_string,
                    round(np.linalg.norm(nei_list[i].cart_coords - [0, 0, 0]), 5),
                ]
                for i in range(len(nei_list))
            ]

        sites = sorted(sites, key=lambda x: x[2])
        return sites

    def get_coord_envs(self):
        """
        For structures from cif files, this method will try to find the
        coordination environment type and return the elements and the
        coordination env. symbol from the first using the classes from pymatgen
        as LocalGeometryFinder(), BVAnalyzer(), MultiWeightsChemenvStrategy()
        and LightStructureEnvironments() .

            > coordination env. symbol.
                        - `S:4` - Square Plane
                        - `T:4` - Tetrahedral
                        - `T:5` - Trigonal bipyramid
                        - `S:5` - Square pyramidal
                        - `O:6` - Octahedral
                        - `T:6` - Trigonal prism
            > ce_fraction:
                        probability for given coordination env. (between 0 and
                        1)

            > CSM:
                        a measure of the degree of symmetry in the coordination
                        environment. It is based on the idea that symmetric
                        environments are more stable than asymmetric ones, and
                        is calculated using a formula that takes into account
                        the distances and angles between the coordinating
                        atoms. The CSM can be understood as a distance to a
                        shape and can take values between 0.0 (if a given
                        environment is perfect) and 100.0 (if a given
                        environment is very distorted). The environment of the
                        atom is then the model polyhedron for which the
                        similarity is the highest, that is, for which the CSM
                        is the lowest.

            > permutation:
                        possible permutation of atoms surrounding the central
                        atom. This is a list that indicates the order in which
                        the neighboring atoms are arranged around the central
                        atom in the coordination environment. The numbering
                        starts from 0, and the list indicates the indices of
                        the neighboring atoms in this order. For example, in
                        the second entry of the list above, the permutation [0,
                        2, 3, 1, 4] means that the first neighboring atom is in
                        position 0, the second is in position 2, the third is
                        in position 3, the fourth is in position 1, and the
                        fifth is in position 4. The permutation is used to
                        calculate the csm value.

            > site:
                        element in the coordination environment and its
                        coordinates (cartesian and fractional).

            > site_index:
                        structure index for the coordinated atom.


        For structures from the xyz file the methods will try to return the
        elements (but not the coord. env. symbol) for the first coordination
        env. shell using the the class CrystalNN from pymatgen, which gives
        better results than BrunnerNN_real and CutOffDictNN (as previously
        tested)

        List of lists:

            [0]: Info about which site is being analyzed.

            [1]: Coord. env as dictionary.

            [2]: Info about coord. env.
                > site:
                    element in the coordination environment and its coordinates
                    (cartesian and fractional).

                > image:
                    image is defined as displacement from original site in
                    structure to a given site. i.e. if structure has a site at
                    (-0.1, 1.0, 0.3), then (0.9, 0, 2.3) -> jimage = (1, -1,
                    2). Note that this method takes O(number of sites) due to
                    searching an original site.

                > weight:
                    quantifies the significance or contribution of each
                    coordinated site to the central site's coordination.

                > site_index:
                    structure index for the coerdinated atom.


        """
        abs_sites = self.get_abs_sites()
        idx_abs_site = abs_sites[self.abs_site][-1]

        if self.is_cif:
            from pymatgen.analysis.bond_valence import BVAnalyzer
            from pymatgen.analysis.chemenv.coordination_environments.coordination_geometry_finder import (
                LocalGeometryFinder,
            )
            from pymatgen.analysis.chemenv.coordination_environments.structure_environments import (
                LightStructureEnvironments,
            )
            from pymatgen.analysis.chemenv.coordination_environments.chemenv_strategies import (
                # SimplestChemenvStrategy,
                MultiWeightsChemenvStrategy,
                # WeightedNbSetChemenvStrategy,
            )

            lgf = LocalGeometryFinder()
            lgf.setup_structure(self.struct)

            bva = BVAnalyzer()  # Bond Valence Analyzer
            try:
                valences = bva.get_valences(structure=self.struct)
            except ValueError:
                valences = "undefined"

            coord_env_list = []
            se = lgf.compute_structure_environments(
                max_cn=6,
                valences=valences,
                only_indices=[idx_abs_site],
                only_symbols=["S:4", "T:4", "T:5", "S:5", "O:6", "T:6"],
            )

            dist_1st_shell = se.voronoi.neighbors_distances[idx_abs_site][0]["max"]
            logger.debug(dist_1st_shell)
            # atom_coord = lgf.compute_coordination_environments(self.struct)
            strategy = MultiWeightsChemenvStrategy.stats_article_weights_parameters()
            # strategy = SimplestChemenvStrategy(distance_cutoff=1.1, angle_cutoff=0.3)
            lse = LightStructureEnvironments.from_structure_environments(
                strategy=strategy, structure_environments=se
            )
            coord_env_ce = lse.coordination_environments[idx_abs_site]
            ngbs_sites = lse._all_nbs_sites
            coord_env_list.append(
                [
                    f"Coord. Env. for Site {abs_sites[self.abs_site][0]}",
                    coord_env_ce,
                    ngbs_sites,
                ]
            )

        if self.is_xyz:
            from pymatgen.analysis.local_env import CrystalNN

            obj = CrystalNN()
            coord_env_list = []
            coord_env = obj.get_nn_info(self.struct, idx_abs_site)
            for site in coord_env:
                site["site"].cart_coords = self.struct[site["site_index"]].coords
            coord_dict = obj.get_cn_dict(self.struct, idx_abs_site)
            coord_env_list.append(
                [
                    f"Coord. Env. for Site {abs_sites[self.abs_site][0]}",
                    {"ce_symbol": f"Elements Dict = {coord_dict}"},
                    coord_env,
                ]
            )

        return coord_env_list

    def get_coord_envs_info(self):
        """
        Class with summarized and more readable information from get_coord_envs() method
        """

        coord_env = self.get_coord_envs()[0]
        abs_site_coord = self.get_abs_sites()[self.abs_site][4]

        elems_dist = []
        for site in coord_env[2]:
            if self.is_cif:
                coord_sym = [
                    coord_env[1][i]["ce_symbol"] for i in range(len(coord_env[1]))
                ]
                elems_dist.append(
                    (
                        site["site"].species,
                        round(np.linalg.norm(site["site"].coords - abs_site_coord), 5),
                    )
                )
            if self.is_xyz:
                coord_sym = coord_env[1]["ce_symbol"]
                elems_dist.append(
                    (
                        site["site"].species,
                        round(
                            np.linalg.norm(site["site"].cart_coords - abs_site_coord), 5
                        ),
                    )
                )
        elems_dist = sorted(elems_dist, key=lambda x: x[1])
        print(
            f"Coord. Env. from absorber atom: {self.abs_atom} at site {self.get_abs_site()}"
        )
        print(coord_sym)
        header = ["Element", "Distance"]
        if HAS_PANDAS:
            df = pd.DataFrame(data=elems_dist, columns=header)
            return df
        else:
            matrix = [header]
            matrix.extend(elems_dist)
            _pprint(matrix)

    def make_cluster(self, radius):
        """Create a cluster with absorber atom site at the center.

        Arguments
        ---------
        radius :float
            cluster radius [Angstrom]

        Returns
        -------
        atoms : list
            species and coords for the new cluster structure
        """

        selected_site = self.get_abs_sites()[self.abs_site]
        cluster = self.mol.get_sites_in_sphere(selected_site[-3], radius)

        # showing and storing cartesian coords and species
        atoms = []

        # abs_atom at the cluster center
        for i in range((len(cluster))):
            try:
                species = round(Element((cluster[i].specie).element).Z)
            except AttributeError:
                species = round(Element(cluster[i].specie).Z)

            # getting species, after atomic number() and rounding
            coords = (
                cluster[i].coords - selected_site[2]
            )  # cartesial coords and ""frac_coords"" are the same for molecule structure (a = b = c = 1)
            coords = np.around(coords, 5)
            dist = round(np.linalg.norm(coords - [0, 0, 0]), 5)
            atoms.append((species, coords, dist))
        atoms = sorted(atoms, key=lambda x: x[2])
        return atoms

    def make_input_fdmnes(
        self, radius=7, parent_path=None, template=None, green=True, **kwargs
    ):
        """
        Create a fdmnes input from a template.

        Arguments
        ---------
        radius : float, [7]
            radius for fdmnes calculation in Angstrom
        parent_path : str, [None]
            path to the parent directory where the input files are stored
            if None it will create a temporary directory
        template : str, [None]
            full path to the template file
        green : boolean [True]
            True: use `Green` (muffin-tin potentials, faster)
            False: use finite-difference method (slower)

        ..note:: SCF is always used
        ..note:: for further information about FDMNES keywords, search for "FDMNES users guide"

        Returns
        -------
        None -> writes FDMNES input to disk
        directory structure: {parent_path}/fdmnes/{self.file_name}/{self.abs_atom}/frame{self.frame}/site{self.abs_site}/

        """
        replacements = {}
        replacements.update(**kwargs)
        replacements["version"] = __version__

        if template is None:
            template = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "templates", "fdmnes.tmpl"
            )

        if parent_path is None:
            parent_path = self.folders["fdmnes"]

        self.outdir = os.path.join(
            parent_path,
            self.file_name,
            self.abs_atom,
            f"frame{self.frame}",
            f"site{self.abs_site}",
        )

        method = "green" if green else ""
        absorber = ""
        crystal = ""
        occupancy = ""
        comment = f"input structure: {self.file_name}{self.file_ext}\ncreation date: {_get_timestamp()}"

        if self.is_cif:
            try:
                selected_site = self.get_abs_sites()[self.abs_site]
            except IndexError:
                logger.error("IndexError: check if abs_atom is correct")

            if not selected_site[-2] == 1:
                logger.warning("the selected site does not have full occupancy!")

            # SpacegroupAnalyzer to get symmetric structure
            analyzer = SpacegroupAnalyzer(self.struct)
            structure = analyzer.get_refined_structure()

            symmetry_data = analyzer.get_symmetry_dataset()
            group_number = symmetry_data["number"]
            group_choice = symmetry_data["choice"]

            # FDMNES doesn't recognize 2 as a space group.
            if group_number == 2:
                group_number = "P-1"

            crystal = f"{crystal}"
            replacements["crystal"] = "crystal"

            group = f"{group_number}"
            if group_choice:
                group += f":{group_choice}"
            replacements["group"] = f"spgroup\n{group}"

            unique_sites = []
            for sites in analyzer.get_symmetrized_structure().equivalent_sites:
                sites = sorted(
                    sites, key=lambda s: tuple(abs(x) for x in s.frac_coords)
                )
                unique_sites.append((sites[0], len(sites)))
                sites = str()
            if self.full_occupancy:
                for i, (site, _) in enumerate(unique_sites):
                    try:
                        e = site.specie
                    except AttributeError:
                        e = Element(site.species_string.split(":")[0])
                    sites += "\n" + (
                        f"{e.Z:>2d} {site.a:12.8f} {site.b:12.8f} {site.c:12.8f}"
                        f" {site.species_string:>4s}"
                    )
            else:
                occupancy = "occupancy"
                for site, _ in unique_sites:
                    for i, e in enumerate(site.species.elements):
                        occu = site.as_dict()["species"][i]["occu"]
                        sites += "\n" + (
                            f"{e.Z:>2d} {site.a:12.8f} {site.b:12.8f} {site.c:12.8f} {occu}"
                            f" {str(e):>4s}"
                        )
            lat = structure.lattice
            replacements["lattice"] = (
                f"{lat.a:<12.8f} {lat.b:12.8f} {lat.c:12.8f} "
                f"{lat.alpha:12.8f} {lat.beta:12.8f} {lat.gamma:12.8f}"
            )

            absorber = f"{absorber}"
            for i in range(len(unique_sites)):
                if (
                    np.allclose(unique_sites[i][0].coords, selected_site[4], atol=0.01)
                    is True
                ):
                    replacements["absorber"] = f"absorber\n{i+1}"

            # absorber = f"{absorber}"
            # replacements["absorber"] = f"Z_absorber\n{round(Element(elem).Z)}"

        if self.is_xyz:
            replacements["crystal"] = "molecule"

            atoms = self.make_cluster(radius=radius)
            sites = str()
            for i in range(len(atoms)):
                e = atoms[i][0]
                c = atoms[i][1]
                sites += "\n" + (
                    f"{e:>2d} {c[0]:12.8f} {c[1]:12.8f} {c[2]:12.8f}"
                    f" {Element.from_Z(e).name}"
                )

            absorber = f"{absorber}"
            for i in range(len(atoms)):
                if np.allclose(atoms[i][1], [0, 0, 0], atol=0.01) is True:
                    replacements["absorber"] = f"absorber\n{i+1}"

            replacements["group"] = ""

            lat = self.struct.lattice
            replacements["lattice"] = (
                f"{lat.a:<12.8f} {lat.b:12.8f} {lat.c:12.8f} "
                f"{lat.alpha:12.8f} {lat.beta:12.8f} {lat.gamma:12.8f}"
            )

        replacements["sites"] = sites
        replacements["radius"] = radius
        replacements["method"] = method
        replacements["comment"] = comment
        replacements["occupancy"] = occupancy

        try:
            os.makedirs(self.outdir, mode=0o755)
        except FileExistsError:
            pass

        # Write the input file.
        fnout = os.path.join(self.outdir, "job_inp.txt")
        with open(fnout, "w") as fp, open(template) as tp:
            inp = tp.read().format(**replacements)
            fp.write(inp)

        # Write the fdmfile.txt.
        with open(os.path.join(self.outdir, "fdmfile.txt"), "w") as fp:
            fp.write("1\njob_inp.txt")

        logger.info(f"written FDMNES input -> {fnout}")

    def make_input_feff(
        self,
        radius=7,
        parent_path=None,
        template=None,
        feff_comment="*",
        edge="K",
        sig2=None,
        debye=None,
        **kwargs,
    ):
        """
        Create a FEFF input from a template.

        Arguments
        ---------
        radius : float, [7]
            radius for feff calculation [Angstrom].
        parent_path : str, [None]
            path to the parent directory where the input files are stored
            if None it will create a temporary directory
        template : str, [None]
            full path to the template file
        feff_coment : str, ["*"]
            comment character used in the input file
        sig2 : float or None, [None]
            SIG2 keywork, if None it will be commented
        debye : list of two floats or None, [None]
            DEBYE keyword, if None it will be commented, otherwise:
            debye=[temperature, debye_temperature]
                temperatue : float
                    temperature at which the Debye-Waller factors are calculated [Kelvin].
                debye_temperature : float
                    Debye Temperature of the material [Kelvin].

        ..note:: refer to [FEFF documentation](https://feff.phys.washington.edu/feffproject-feff-documentation.html)

        Returns
        -------
        None -> writes FEFF input to disk
        directory structure: {parent_path}/feff/{self.file_name}/{self.abs_atom}/frame{self.frame}/site{self.abs_site}/
        """
        replacements = {}
        replacements.update(**kwargs)
        replacements["version"] = __version__

        if parent_path is None:
            parent_path = self.folders["feff"]
        self.outdir = os.path.join(
            parent_path,
            self.file_name,
            self.abs_atom,
            f"frame{self.frame}",
            f"site{self.abs_site}",
        )

        if template is None:
            template = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "templates",
                "feff_exafs.tmpl",
            )

        if sig2 is None:
            use_sig2 = "*"
            sig2 = 0.005
        else:
            use_sig2 = ""

        if debye is None:
            use_debye = "*"
            temperature, debye_temperature = 0, 0
        else:
            use_debye = ""
            temperature, debye_temperature = debye[0], debye[1]

        feff_comment = f"{feff_comment}"
        edge = f"{edge}"
        radius = f"{radius}"
        use_sig2 = f"{use_sig2}"
        sig2 = f"{sig2}"
        use_debye = f"{use_debye}"
        temperature = f"{temperature}"
        debye_temperature = f"{debye_temperature}"

        if self.is_cif:
            sites = self.get_atoms_from_abs(radius)
            ipot_list = [(0, Element(f"{self.abs_atom}").Z, sites[0][1])]
            ipot = {f"{self.abs_atom}(abs)": 0}
            elems = self.species

            for i, elem in enumerate(elems):
                ipot[elem] = i + 1
            for i in range(1, len(sites)):
                for j, _ in enumerate(sites[i][0].species.elements):
                    if str(sites[i][0].species.elements[j]) in elems:
                        ipot_list.append(
                            (
                                ipot[str(sites[i][0].species.elements[j])],
                                sites[i][0].species.elements[j].Z,
                                str(sites[i][0].species.elements[j]),
                            )
                        )
            pot = list(dict.fromkeys(ipot_list))
            potentials = str("* ipot  Z   tag [lmax1 lmax2 xnatph sphinph]")
            for i, _ in enumerate(pot):
                potentials += "\n" + (f"{pot[i][0]:>5} {pot[i][1]:>3} {pot[i][2]:>5}")

            atoms_list = [
                (sites[0][0].cart_coords, 0, sites[0][1], sites[0][2], sites[0][3])
            ]
            for i in range(1, len(sites)):
                atoms_list.append(
                    (
                        sites[i][0].cart_coords,
                        ipot[str(sites[i][0].species.elements[0])],
                        sites[i][1],
                        sites[i][2],
                        sites[i][3],
                    )  # cart, ipot, tag, dist
                )

        if self.is_xyz:
            sites = self.get_atoms_from_abs(radius=radius)
            ipot_list = [(0, Element(f"{self.abs_atom}").Z, sites[0][1])]
            elems = []
            ipot = {}
            for i in range(1, len(sites)):
                if sites[i][0].species_string not in elems:
                    elems.append((sites[i][0].species_string))
            for i, elem in enumerate(elems):
                ipot[elem] = i + 1
            for i in range(1, len(sites)):
                if sites[i][0].species_string in elems:
                    ipot_list.append(
                        (
                            ipot[sites[i][0].species_string],
                            sites[i][0].specie.Z,
                            sites[i][0].species_string,
                        )
                    )
            pot = list(dict.fromkeys(ipot_list))
            potentials = str("* ipot  Z   tag [lmax1 lmax2 xnatph sphinph]")
            for i in range(len(pot)):
                potentials += "\n" + (f"{pot[i][0]:>5} {pot[i][1]:>3} {pot[i][2]:>5}")
            atoms_list = []
            for i in range(len(sites)):
                atoms_list.append(
                    (
                        sites[i][0].cart_coords,
                        ipot_list[i][0],
                        sites[i][1],  # tag
                        sites[i][2],
                    )
                )
        atoms = str(
            "*   x          y          z     ipot   tag    distance   occupancy"
        )
        at = atoms_list
        for i in range(len(at)):
            if self.full_occupancy:
                atoms += "\n" + (
                    f"{at[i][0][0]:10.6f} {at[i][0][1]:10.6f} {at[i][0][2]:10.6f} {  int(at[i][1])}  {at[i][2]:>5} {at[i][3]:10.5f}         *1 "
                )
            else:
                choice = np.random.choice(
                    list(at[i][4].keys()), p=list(at[i][4].values())
                )
                atoms += "\n" + (
                    f"{at[i][0][0]:10.6f} {at[i][0][1]:10.6f} {at[i][0][2]:10.6f} {ipot[choice]}  {choice:>5} {at[i][3]:10.5f} *{at[i][4]}"
                )

        title = f"TITLE {self.file_name}{self.file_ext}\nTITLE {_get_timestamp()}\nTITLE site {self.abs_site}"

        replacements["feff_comment"] = feff_comment
        replacements["edge"] = edge
        replacements["radius"] = radius
        replacements["use_sig2"] = use_sig2
        replacements["sig2"] = sig2
        replacements["use_debye"] = use_debye
        replacements["temperature"] = temperature
        replacements["debye_temperature"] = debye_temperature
        replacements["potentials"] = potentials
        replacements["atoms"] = atoms
        replacements["title"] = title
        # replacements[""] =

        try:
            os.makedirs(self.outdir, mode=0o755)
        except FileExistsError:
            pass

        # Write the input file.
        fnout = os.path.join(self.outdir, "feff.inp")
        with open(fnout, "w") as fp, open(template) as tp:
            inp = tp.read().format(**replacements)
            fp.write(inp)

        logger.info(f"written FEFF input -> {fnout}")

    def _get_xyz_and_elements(self, radius):
        """
        Get information about cartesian coords and elements surrounding the central atom given
        a radius.

         Args:
            > radius(float):
                    radius from the central atom [Angstrom].

         return list of elements with coords and list of elements, both lists of strings.

        """
        sites = self.get_atoms_from_abs(radius)
        coords = []
        elements = []
        for _, site in enumerate(sites):
            try:
                coords.append(
                    (str((site[0].species).elements[0].name), site[0].cart_coords)
                )
            except AttributeError:
                coords.append((str(site[0].specie), site[0].cart_coords))

        output_str = str(len(coords)) + "\n\n"
        for element, coords in coords:
            coords_str = " ".join([f"{c:.6f}" for c in coords])
            output_str += f"{element} {coords_str}\n"
            if element not in elements:
                elements.append(element)
        elements = sorted(elements)
        return output_str, elements

    def _round_up(self, x):
        rounded_x = np.ceil(x * 100) / 100
        return rounded_x

    def visualize(self, radius=2.5, unitcell=False):
        """
        Display a 3D visualization for material local structure.

        Args:
            > radius (float):
                    radius visualization from the central atom.

            > unitcell (boolean):
                    if True, allows the visualization of the structure unit cell.

        return 3D structure visualization from py3Dmol.
        """
        if HAS_PY3DMOL is False:
            logger.error("py3Dmol not installed! -> run `pip install py3Dmol`")
            return

        radius = self._round_up(radius)

        xyz, elems = self._get_xyz_and_elements(radius)

        a = self.struct.lattice.a
        b = self.struct.lattice.b
        c = self.struct.lattice.c
        alpha = self.struct.lattice.alpha
        beta = self.struct.lattice.beta
        gamma = self.struct.lattice.gamma
        xyzview = py3Dmol.view(
            width=600, height=600
        )  # http://3dmol.org/doc/GLViewer.html#setStyle
        xyzview.addModel(xyz, "xyz")

        if unitcell is True:
            m = xyzview.getModel()
            m.setCrystData(a, b, c, alpha, beta, gamma)
            xyzview.addUnitCell()

        colors = [
            "red",
            "green",
            "blue",
            "orange",
            "yellow",
            "white",
            "purple",
            "pink",
            "brown",
            "black",
            "gray",
            "cyan",
            "magenta",
            "olive",
            "navy",
            "teal",
            "maroon",
            "turquoise",
            "indigo",
            "salmon",
        ]
        color_elems = {}
        for idx, elem in enumerate(self.elems):
            color_elems[f"{elem}"] = colors[idx]

        for idx, elem in enumerate(elems):
            color = color_elems[f"{elem}"]
            xyzview.setStyle(
                {"elem": f"{elem}"},
                {
                    "stick": {
                        "radius": 0.1,
                        "opacity": 1,
                        "hidden": False,
                        "color": f"{color}",
                    },
                    "sphere": {"color": f"{color}", "radius": 0.4, "opacity": 1},
                },
            )
        xyzview.addLabel(
            "Abs",
            {
                "fontColor": "black",
                "fontSize": 14,
                "backgroundColor": "white",
                "backgroundOpacity": 0.8,
                "showBackground": True,
            },
            {"index": 0},
        )

        xyzview.zoomTo()
        xyzview.show()

        logger.info(color_elems)
        if not self.full_occupancy:
            logger.warning("3D displayed image does not consider partial occupancy")
            logger.info("check atoms occupancy here:", self.atoms_occu)
            # color_elems = {}
            # for idx, elem in enumerate(self.species_occu):
            #     color_elems[f"{list(elem.values())[0]}"] = colors[idx]
            # print("Label:\n", color_elems)


def get_fdmnes_info(file, labels=("energy", "mu")):
    """Get info from the fdmnes output file such as edge energy, atomic number Z,
      and fermi level energy, and returns a group with the storage information

      Parameters:

        file (str): path to the fdmnes output file.
    Obs: The INPUT file must have the "Header" keyword to use this function in the OUTPUT file

    """
    group = read_ascii(file, labels=labels)

    with open(group.path) as f:
        line = f.readlines()[3]
        header = line.split()
        (
            e_edge,
            Z,
            e_fermi,
        ) = (float(header[0]), float(header[1]), float(header[6]))
        print(
            f"Calculated Fermi level: {e_fermi}\nAtomic_number: {Z}\nEnergy_edge: {e_edge}"
        )

    group.e_edge = e_edge
    group.Z = Z
    group.e_fermi = e_fermi

    return group


def convolve_data(
    energy, mu, group, fwhm=1, linbroad=[1.5, 0, 50], kernel="gaussian", efermi=None
):
    """
    Function for manual convolution using Convolution1D from larch and returning a group

    Generic discrete convolution

    Description
    -----------

    This is a manual (not optimized!) implementation of discrete 1D
    convolution intended for spectroscopy analysis. The difference with
    commonly used methods is the possibility to adapt the convolution
    kernel for each convolution point, e.g. change the FWHM of the
    Gaussian kernel as a function of the energy scale.

    Resources
    ---------

    .. [WPconv] <http://en.wikipedia.org/wiki/Convolution#Discrete_convolution>
    .. [Fisher] <http://homepages.inf.ed.ac.uk/rbf/HIPR2/convolve.htm>
    .. [GP1202] <http://glowingpython.blogspot.fr/2012/02/convolution-with-numpy.html>

    """

    gamma_e = lin_gamma(energy, fwhm=fwhm, linbroad=linbroad)
    mu_conv = conv(energy, mu, kernel=kernel, fwhm_e=gamma_e, efermi=efermi)
    group.conv = mu_conv
    return group


def save_cif_from_mp(api_key, material_id, parent_path=None):
    """Collect a CIF file from the Materials Project Database, given the material id

    Parameters
    ----------
    api_key : str
        api-key from Materials Project
    material id : str
        material id (format mp-xxxx) from Materials Project
    parent_path : str
        path where to store the CIF files
        if None, a temporary one is created

    Returns
    -------
        [str, str] : parent_path, CIF file name

    """
    if parent_path is None:
        parent_path = structure_folders()["mp_structs"]

    from pymatgen.ext.matproj import _MPResterLegacy

    cif = _MPResterLegacy(api_key).get_data(material_id, prop="cif")
    pf = _MPResterLegacy(api_key).get_data(material_id, prop="pretty_formula")[0][
        "pretty_formula"
    ]
    outfn = f"{pf}_{material_id}.cif"
    with open(file=os.path.join(parent_path, outfn), mode="w") as f:
        f.write(cif[0]["cif"])
        logger.info(f"{material_id} -> {outfn}")
    return [parent_path, outfn]


def save_mp_structure(api_key, material_id, parent_path=None):
    """Save structure from Materials Project Database as json, given the material id

    Parameters
    ----------
    api_key : str
        api-key from Materials Project
    material id : str
        material id (format mp-xxxx) from Materials Project
    parent_path : str
        path where to store the Structure files
        if None, user_larchdir + 'mp_structs' is used

    Returns
    -------
        name of structure file, which will have an 'mpjson' extension

    Notes
    ------
    The structure is saved as json that can be loaded with
          from pymatgen.core import Structure
          import json
          struct = Structure.from_dict(json.load(open(filename, 'r')))

    """

    if parent_path is None:
        parent_path = structure_folders()["mp_structs"]

    try:
        from mp_api.client import MPRester
    except ImportError:
        print("need to install mp_api:  pip install mp_api")

    mpr = MPRester(api_key)
    results = mpr.summary.search(
        material_ids=[material_id], fields=["structure", "formula_pretty"]
    )
    formula = results[0].formula_pretty
    structure = results[0].structure

    outfile = os.path.join(parent_path, f"{formula}_{material_id}.mpjson")
    with open(outfile, "w") as fh:
        fh.write(structure.to_json())
    logger.info(f"saved {material_id} to {outfile}")

    return outfile
