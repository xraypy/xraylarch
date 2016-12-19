#!/usr/bin/env python
'''
build American Mineralogist Crystal Structure Databse (amcsd)
'''

import os
import glob
import re
import math
import time
import six
import requests

import cStringIO

HAS_CifFile = False
try:
    import CifFile
    HAS_CifFile = True
except ImportError:
    pass

HAS_XRAYUTIL = False
try:
    import xrayutilities as xu
    HAS_XRAYUTIL = True
except ImportError:
    pass

import numpy as np

from larch_plugins.diFFit.XRDCalculations import generate_hkl

from sqlalchemy import create_engine,MetaData,PrimaryKeyConstraint,ForeignKey
from sqlalchemy import Table,Column,Integer,String
from sqlalchemy.orm import sessionmaker, mapper
from sqlalchemy.pool import SingletonThreadPool

# needed for py2exe?
import sqlalchemy.dialects.sqlite
import larch
from larch_plugins.math import as_ndarray

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
SPACEGROUPS = [['1', 'A 1'], ['1', 'B 1'], ['1', 'C 1'], ['1', 'A1'], ['1', 'B1'], ['1', 'C1'], ['1', 'F 1'], ['1', 'F1'], ['1', 'I 1'],
               ['2', 'A -1'], ['2', 'A-1'], ['2', 'B -1'], ['2', 'B-1'], ['2', 'C -1'], ['2', 'C-1'], ['2', 'F -1'], ['2', 'F-1'], ['2', 'I -1'], ['2', 'I-1'], ['2', 'P -1'], ['2', 'P 1'], ['2', 'P-1'], ['2', 'P1'],
               ['3', 'A 2 1 1'], ['3', 'B 1 2 1'], ['3', 'C 1 1 2'], ['3', 'P 1 1 2'], ['3', 'P 1 2 1'], ['3', 'P 2 1 1'], ['3', 'P2'],
               ['4', 'A 21 1 1'], ['4', 'B 1 21 1'], ['4', 'C 1 1 21'], ['4', 'P 1 1 21'], ['4', 'P 1 21 1'], ['4', 'P 21 1 1'], ['4', 'P21'],
               ['5', 'A 1 1 2'], ['5', 'A 1 2 1'], ['5', 'B 1 1 2'], ['5', 'B 2 1 1'], ['5', 'C 1 2 1'], ['5', 'C 2 1 1'], ['5', 'C2'], ['5', 'F 1 1 2'], ['5', 'F 1 2 1'], ['5', 'F 2 1 1'], ['5', 'I 1 1 2'], ['5', 'I 1 2 1'], ['5', 'I 2 1 1'],
               ['6', 'A m 1 1'], ['6', 'B 1 m 1'], ['6', 'C 1 1 m'], ['6', 'P 1 1 m'], ['6', 'P 1 m 1'], ['6', 'P m 1 1'], ['6', 'Pm'],
               ['7', 'A b 1 1'], ['7', 'A d 1 1'], ['7', 'B 1 a 1'], ['7', 'B 1 d 1'], ['7', 'C 1 1 a'], ['7', 'C 1 1 d'], ['7', 'P 1 1 a'], ['7', 'P 1 1 b'], ['7', 'P 1 1 n'], ['7', 'P 1 a 1'], ['7', 'P 1 c 1'], ['7', 'P 1 n 1'], ['7', 'P b 1 1'], ['7', 'P c 1 1'], ['7', 'P n 1 1'], ['7', 'Pc'],
               ['8', 'A 1 1 m'], ['8', 'A 1 m 1'], ['8', 'B 1 1 m'], ['8', 'B m 1 1'], ['8', 'C 1 m 1'], ['8', 'C m 1 1'], ['8', 'Cm'], ['8', 'F 1 1 m'], ['8', 'F 1 m 1'], ['8', 'F m 1 1'], ['8', 'I 1 1 m'], ['8', 'I 1 m 1'], ['8', 'I m 1 1'],
               ['9', 'A 1 1 a'], ['9', 'A 1 a 1'], ['9', 'B 1 1 b'], ['9', 'B b 1 1'], ['9', 'C 1 c 1'], ['9', 'C c 1 1'], ['9', 'Cc'], ['9', 'F 1 1 d'], ['9', 'F 1 d 1'], ['9', 'F d 1 1'], ['9', 'I 1 1 a'], ['9', 'I 1 a 1'], ['9', 'I b 1 1'], ['9', 'I 1 1 b'],
               ['10', 'A 2 / m 1 1'], ['10', 'B 1 2 / m 1'], ['10', 'C 1 1 2 / m'], ['10', 'P 1 1 2 / m'], ['10', 'P 1 2 / m 1'], ['10', 'P 2 / m 1 1'], ['10', 'P2/m'], ['10', 'P 1 2/m 1'], ['10', 'P 1 1 2/m'],
               ['11', 'A 21 / m 1 1'], ['11', 'B 1 21 / m 1'], ['11', 'C 1 1 21 / m'], ['11', 'P 1 1 21 / m'], ['11', 'P 1 21/m 1'], ['11', 'P 1 21 / m 1'], ['11', 'P 21 / m 1 1'], ['11', 'P21/m'], ['11', 'P 1 1 21/m'],
               ['12', 'A 1 1 2 / m'], ['12', 'A 1 2 / m 1'], ['12', 'B 1 1 2 / m'], ['12', 'B 1 1 2/m'], ['12', 'B 2 / m 1 1'], ['12', 'C 1 2 / m 1'], ['12', 'C 1 2/m 1'], ['12', 'C 2 / m 1 1'], ['12', 'C2/m'], ['12', 'F 1 1 2 / m'], ['12', 'F 1 2 / m 1'], ['12', 'F 2 / m 1 1'], ['12', 'I 1 1 2 / m'], ['12', 'I 1 2 / m 1'], ['12', 'I 2 / m 1 1'], ['12', 'I 1 2/m 1'], ['12', 'A 1 2/m 1'], ['12', 'C 2/m '], ['12', 'A 1 1 2/m'], ['12', 'F 1 2/m 1'],
               ['13', 'A 2 / b 1 1'], ['13', 'A 2 / d 1 1'], ['13', 'B 1 2 / a 1'],  ['13', 'B 1 2 / d 1'], ['13', 'C 1 1 2 / a'], ['13', 'C 1 1 2 / d'], ['13', 'P 1 1 2 / a'], ['13', 'P 1 1 2 / b'], ['13', 'P 1 1 2 / n'], ['13', 'P 1 1 2/b'], ['13', 'P 1 2 / a 1'], ['13', 'P 1 2 / c 1'], ['13', 'P 1 2 / n 1'], ['13', 'P 1 2/c 1'], ['13', 'P 2 / b 1 1'], ['13', 'P 2 / c 1 1'], ['13', 'P 2 / n 1 1'], ['13', 'P2/c'], ['13', 'P 1 2/n 1'], ['13', 'P 1 2/a 1'],
               ['14', 'A 21 / b 1 1'], ['14', 'A 21 / d 1 1'], ['14', 'B 1 21 / a 1'], ['14', 'B 1 21 / d 1'], ['14', 'C 1 1 21 / a'], ['14', 'C 1 1 21 / d'], ['14', 'P 1 1 21 / a'], ['14', 'P 1 1 21 / b'], ['14', 'P 1 1 21 / n'], ['14', 'P 1 1 21/b'], ['14', 'P 1 21 / a 1'], ['14', 'P 1 21 / c 1'], ['14', 'P 1 21 / n 1'], ['14', 'P 1 21/c 1'], ['14', 'P 21 / b 1 1'], ['14', 'P 21 / c 1 1'], ['14', 'P 21 / n 1 1'], ['14', 'P21/c'], ['14', 'P 1 21/a 1'], ['14', 'P 1 21/n 1'], ['14', 'P 21/b 1 1'], ['14', 'P 1 1 21/n'], ['14', 'B 1 21/d 1'], ['14', 'B 1 21/m 1'], ['14', 'P 21/n 1 1'], ['14', 'P 1 1 21/a'], ['14', 'P 21/c'], ['14', 'P 21/n'],
               ['15', 'A 1 1 2 / a'], ['15', 'A 1 2 / a 1'], ['15', 'B 1 1 2 / b'], ['15', 'B 1 1 2/b'], ['15', 'B 2 / b 1 1'], ['15', 'C 1 2 / c 1'], ['15', 'C 1 2/c 1'], ['15', 'C 2 / c 1 1'], ['15', 'C2/c'], ['15', 'F 1 1 2 / d'], ['15', 'F 1 2 / d 1'], ['15', 'F 2 / d 1 1'], ['15', 'I 1 2/a 1'], ['15', 'A 1 2/a 1'], ['15', 'I 1 1 2 / a'], ['15', 'I 1 2 / a 1'], ['15', 'I 2 / b 1 1'], ['15', 'C 1 1 2/a'], ['15', 'F 1 2/d 1'], ['15', 'I 1 2/c 1'], ['15', 'C 2/c'], ['15', 'I 1 1 2/b'], ['15', 'I 1 1 2/a'], ['15', 'B 1 1 2/n'], ['15', 'A 1 2/n 1'],
               ['16', 'P 2 2 2'], ['16', 'P222'],
               ['17', 'P 2 2 21'], ['17', 'P 2 21 2'], ['17', 'P 21 2 2'], ['17', 'P222_1'], ['17', 'P2221'],
               ['18', 'P 2 21 21'], ['18', 'P 21 2 21'], ['18', 'P 21 21 2'], ['118', 'P2_12_12'], ['18', 'P2_122_1'], ['18', 'P21212'], ['18', 'P22_12_1'],
               ['19', 'P 21 21 2 1'], ['19', 'P 21 21 21'], ['19', 'P2_12_12_1'], ['19', 'P212121'],
               ['20', 'A 21 2 2'], ['20', 'A2_122'], ['20', 'B 2 21 2'], ['20', 'C 2 2 21'], ['20', 'C222_1'], ['20', 'C2221'],
               ['21', 'A 2 2 2'], ['21', 'B 2 2 2'], ['21', 'C 2 2 2'], ['21', 'C222'],
               ['22', 'F 2 2 2'], ['22', 'F222'],
               ['23', 'I 2 2 2'], ['23', 'I222'],
               ['24', 'I 21 21 2 1'], ['24', 'I 21 21 21'], ['24', 'I2_12_12_1'], ['24', 'I212121'],
               ['25', 'P 2 m m'], ['25', 'P m 2 m'], ['25', 'P m m 2'], ['25', 'P2mm'], ['25', 'Pm2m'], ['25', 'Pmm2'],
               ['26', 'P 21 a m'], ['26', 'P 21 m a'], ['26', 'P b 21 m'], ['26', 'P c m 21'], ['26', 'P m 21 b'], ['26', 'P m c 21'], ['26', 'P2_1am'], ['26', 'P2_1ma'], ['26', 'Pb2_1m'], ['26', 'Pcm2_1'], ['26', 'Pmc2_1'], ['26', 'Pmc21'],
               ['27', 'P 2 a a'], ['27', 'P b 2 b'], ['27', 'P c c 2'], ['27', 'Pcc2'],
               ['28', 'P 2 c m'], ['28', 'P 2 m b'], ['28', 'P b m 2'], ['28', 'P c 2 m'], ['28', 'P m 2 a'], ['28', 'P m a 2'], ['28', 'P2cm'], ['28', 'Pbm2'], ['28', 'Pma2'],
               ['29', 'P 21 a b'], ['29', 'P 21 c a'], ['29', 'P b 21 a'], ['29', 'P b c 21'], ['29', 'P c 21 b'], ['29', 'P c a 21'], ['29', 'P2_1ab'], ['29', 'P2_1ca'], ['29', 'Pbc2_1'], ['29', 'Pc2_1b'], ['29', 'Pca2_1'], ['29', 'Pca21'],
               ['30', 'P 2 a n'], ['30', 'P 2 n a'], ['30', 'P b 2 n'], ['30', 'P c n 2'], ['30', 'P n 2 b'], ['30', 'P n c 2'], ['30', 'P2an'], ['30', 'Pnc2'],
               ['31', 'P 21 m n'], ['31', 'P 21 n m'], ['31', 'P m 21 n'], ['31', 'P m n 21'], ['31', 'P n 21 m'], ['31', 'P n m 21'], ['31', 'P2_1mn'], ['31', 'P2_1nm'], ['31', 'Pmn2_1'], ['31', 'Pmn21'], ['31', 'Pn2_1m'], ['31', 'Pnm2_1'],
               ['32', 'P 2 c b'], ['32', 'P b a 2'], ['32', 'P c 2 a'], ['32', 'Pba2'],
               ['33', 'P 21 c n'], ['33', 'P 21 n b'], ['33', 'P b n 21'], ['33', 'P c 21 n'], ['33', 'P n 21 a'], ['33', 'P n a 21'], ['33', 'P2_1cn'], ['33', 'P2_1nb'], ['33', 'Pbn2_1'], ['33', 'Pc2_1n'], ['33', 'Pn2_1a'], ['33', 'Pna21'],
               ['34', 'P 2 n n'], ['34', 'P n 2 n'], ['34', 'P n n 2'], ['34', 'P2nn'], ['34', 'Pn2n'], ['34', 'Pnn2'],
               ['35', 'A 2 m m'], ['35', 'A2mm'], ['35', 'B m 2 m'], ['35', 'Bm2m'], ['35', 'C m m 2'], ['35', 'Cmm2'],
               ['36', 'A 21 a m'], ['36', 'A 21 m a'], ['36', 'A2_1am'], ['36', 'A2_1ma'], ['36', 'B b 21 m'], ['36', 'B m 21 b'], ['36', 'Bb2_1m'], ['36', 'C c m 21'], ['36', 'C m c 21'], ['36', 'Ccm2_1'], ['36', 'Cmc2_1'], ['36', 'Cmc21'],
               ['37', 'A 2 a a'], ['37', 'B b 2 b'], ['37', 'C c c 2'], ['37', 'Ccc2'],
               ['38', 'A m 2 m'], ['38', 'A m m 2'], ['38', 'Amm2'], ['38', 'B 2 m m'], ['38', 'B m m 2'], ['38', 'C 2 m m'], ['38', 'C m 2 m'],
               ['39', 'A b 2 m'], ['39', 'A b m 2'], ['39', 'Abm2'], ['39', 'Aem2'], ['39', 'B 2 a m'], ['39', 'B m a 2'], ['39', 'C 2 m a'], ['39', 'C m 2 a'], ['39', 'Cm2a'],
               ['40', 'A m 2 a'], ['40', 'A m a 2'], ['40', 'Ama2'], ['40', 'B 2 m b'], ['40', 'B b m 2'], ['40', 'B2mb'], ['40', 'C 2 c m'], ['40', 'C c 2 m'],
               ['41', 'A b 2 a'], ['41', 'A b a 2'], ['41', 'Aba2'], ['41', 'Aea2'], ['41', 'B 2 a b'], ['41', 'B b a 2'], ['41', 'Bba2'], ['41', 'C 2 c a'], ['41', 'C c 2 a'], ['41', 'C 2 c b'],
               ['42', 'F m m 2'], ['42', 'Fmm2'], ['42', 'F m 2 m'],
               ['43', 'F 2 d d'], ['43', 'F d 2 d'], ['43', 'F d d 2'], ['43', 'F dd2'], ['43', 'F2dd'], ['43', 'Fd2d'], ['43', 'Fdd2'],
               ['44', 'I m m 2'], ['44', 'Imm2'], ['44', 'I 2 m m'], ['44', 'I m 2 m'],
               ['45', 'I 2 a a'], ['45', 'I b 2 a'], ['45', 'I b a 2'], ['45', 'Iba2'],
               ['46', 'I 2 a m'], ['46', 'I 2 m a'], ['46', 'I b 2 m'], ['46', 'I b m 2'], ['46', 'I m 2 a'], ['46', 'I m a 2'], ['46', 'Ibm2'], ['46', 'Ima2'], ['46', 'I 2 m b'], ['46', 'I 2 c m'],
               ['47', 'P 2/m 2/m 2/m'], ['47', 'P m m m'], ['47', 'Pmmm'],
               ['48', 'P 2/n 2/n 2/n'], ['48', 'P n n n'], ['48', 'Pnnn'],
               ['49', 'P 2/c 2/c 2/m'], ['49', 'P b m b'], ['49', 'P c c m'], ['49', 'P m a a'], ['49', 'Pccm'],
               ['50', 'P 2/b 2/a 2/n'], ['50', 'P b a n'], ['50', 'P c n a'], ['50', 'P n c b'], ['50', 'Pban'], ['50', 'Pncb'],
               ['51', 'P 21/m 2/m 2/a'], ['51', 'P b m m'], ['51', 'P c m m'], ['51', 'P m a m'], ['51', 'P m c m'], ['51', 'P m m a'], ['51', 'P m m b'], ['51', 'Pbmm'], ['51', 'Pmam'], ['51', 'Pmma'],
               ['52', 'P 2/n 21/n 2/a'], ['52', 'P b n n'], ['52', 'P c n n'], ['52', 'P n a n'], ['52', 'P n c n'], ['52', 'P n n a'], ['52', 'P n n b'], ['52', 'Pbnn'], ['52', 'Pcnn'], ['52', 'Pnan'], ['52', 'Pncn'], ['52', 'Pnna'],
               ['53', 'P 2/m 2/n 21/a'], ['53', 'P b m n'], ['53', 'P c n m'], ['53', 'P m a n'], ['53', 'P m n a'], ['53', 'P n c m'], ['53', 'P n m b'], ['53', 'Pbmn'], ['53', 'Pbnm'], ['53', 'Pman'], ['53', 'Pmna'], ['53', 'Pncm'], ['53', 'Pnmb'], ['54', 'P 21/c 2/c 2/a'],
               ['54', 'P b a a'], ['54', 'P b a b'], ['54', 'P b c b'], ['54', 'P c a a'], ['54', 'P c c a'], ['54', 'P c c b'], ['54', 'Pbaa'], ['54', 'Pbcb'], ['54', 'Pcca'],
               ['55', 'P 21/b 21/a 2/m'], ['55', 'P b a m'], ['55', 'P c m a'], ['55', 'P m c b'], ['55', 'Pbam'], ['55', 'Pmcb'],
               ['56', 'P 21/c 21/c 2/n'], ['56', 'P b n b'], ['56', 'P c c n'], ['56', 'P n a a'], ['56', 'Pbnb'], ['56', 'Pccn'], ['56', 'Pnaa'],
               ['57', 'P 2/b 21/c 21/m'], ['57', 'P b c m'], ['57', 'P b m a'], ['57', 'P c a m'], ['57', 'P c m b'], ['57', 'P m a b'], ['57', 'P m c a'], ['57', 'Pbcm'], ['57', 'Pbma'], ['57', 'Pcam'], ['57', 'Pcmb'], ['57', 'Pmab'],
               ['58', 'P 21/n 21/n 2/m'], ['58', 'P m n n'], ['58', 'P n m n'], ['58', 'P n n m'], ['58', 'Pmnn'], ['58', 'Pnmn'], ['58', 'Pnnm'],
               ['59', 'P 21/m 21/m 2/n'], ['59', 'P m m n'], ['59', 'P m n m'], ['59', 'P n m m'], ['59', 'Pmmn'], ['59', 'Pmnm'], ['59', 'Pnmm'],
               ['60', 'P 21/b 2/c 21/n'], ['60', 'P b c n'], ['60', 'P b n a'], ['60', 'P c a n'], ['60', 'P c n b'], ['60', 'P n a b'], ['60', 'P n c a'], ['60', 'Pbcn'], ['60', 'Pbna'], ['60', 'Pcan'], ['60', 'Pcnb'], ['60', 'Pnab'], ['60', 'Pnca'],
               ['61', 'P 21/b 21/c 21/a'], ['61', 'P b c a'], ['61', 'P c a b'], ['61', 'Pbca'],['61', 'Pcab'],
               ['62', 'P 21/n 21/m 21/a'], ['62', 'P b n m'], ['62', 'P c m n'], ['62', 'P m c n'], ['62', 'P m n b'], ['62', 'P n a m'], ['62', 'P n m a'], ['62', 'Pcmn'], ['62', 'Pmcn'], ['62', 'Pmnb'], ['62', 'Pnam'], ['62', 'Pnma'], ['62', 'P 1 n m a 1'], ['62', 'P 1 n a m 1'],
               ['63', 'A m a m'], ['63', 'A m m a'], ['63', 'Amam'], ['63', 'Amma'], ['63', 'B b m m'], ['63', 'B m m b'], ['63', 'Bbmm'], ['63', 'Bmmb'], ['63', 'C 2/m 2/c 21/m'], ['63', 'C c m m'], ['63', 'C m c m'], ['63', 'Ccmm'], ['63', 'Cmcm'],
               ['64', 'A b a m'], ['64', 'A b m a'], ['64', 'Abma'], ['64', 'B b a m'], ['64', 'B m a b'], ['64', 'Bbam'], ['64', 'Bmab'], ['64', 'C 2/m 2/c 21/a'], ['64', 'C c m a'], ['64', 'C m c a'], ['64', 'Cmca'], ['64', 'Cmce'], ['64', 'B b c m'], ['64', 'A c a m'], ['64', 'C c m b'],
               ['65', 'C 2/m 2/m 2/m'], ['65', 'C m m m'], ['65', 'Cmmm'], ['65', 'A m m m'],
               ['66', 'A m a a'], ['66', 'Amaa'], ['66', 'B b m b'], ['66', 'C 2/c 2/c 2/m'], ['66', 'C c c m'], ['66', 'Cccm'],
               ['67', 'A b m m'], ['67', 'Abmm'], ['67', 'B m a m'], ['67', 'Bmam'], ['67', 'C 2/m 2/m 2/e'], ['67', 'C m m a'], ['67', 'Cmma'], ['67', 'Cmme'], ['67', 'A c m m'],
               ['68', 'A b a a'], ['68', 'B b a b'], ['68', 'C 2/c 2/c 2/e'], ['68', 'C c c a'], ['68', 'Ccca'], ['68', 'Ccce'],
               ['69', 'F 2/m 2/m 2/m'], ['69', 'F m m m'], ['69', 'Fmmm'],
               ['70', 'F 2/d 2/d 2/d'], ['70', 'F d d d'], ['70', 'Fddd'],
               ['71', 'I 2/m 2/m 2/m'], ['71', 'I m m m'], ['71', 'Immm'],
               ['72', 'I 2/b 2/a 2/m'], ['72', 'I b a m'], ['72', 'I b m a'], ['72', 'I m a a'], ['72', 'Ibam'], ['72', 'I m c b'], ['72', 'I c m a'], ['72', 'I m a b'],
               ['73', 'I 2/b 2/c 2/a'], ['73', 'I b c a'], ['73', 'Ibca'],
               ['74', 'I 2/m 2/m 2/a'], ['74', 'I b m m'], ['74', 'I m a m'], ['74', 'I m m a'], ['74', 'Ibmm'], ['74', 'Imam'], ['74', 'Imma'], ['74', 'I m c m'], ['74','I 1 m m a 1'],
               ['75', 'C 4'], ['75', 'P 4'], ['75', 'P4'],
               ['76', 'C 41'], ['76', 'P 41'], ['76', 'P4_1'], ['76', 'P41'],
               ['77', 'C 42'], ['77', 'P 42'], ['77', 'P4_2'], ['77', 'P42'],
               ['78', 'C 43'], ['78', 'P 43'], ['78', 'P4_3'], ['78', 'P43'],
               ['79', 'F 4'], ['79', 'I 4'], ['79', 'I4'],
               ['80', 'F 41'], ['80', 'I 41'], ['80', 'I41'],
               ['81', 'C -4'], ['81', 'P -4'], ['81', 'P-4'],
               ['82', 'F -4'], ['82', 'I -4'], ['82', 'I-4'],
               ['83', 'C 4 / m'], ['83', 'P 4 / m'], ['83', 'P 4/m'], ['83', 'P4/m'],
               ['84', 'C 42 / m'], ['84', 'P 42 / m'], ['84', 'P 42/m'], ['84', 'P4_2/m'], ['84', 'P42/m'],
               ['85', 'C 4 / a'], ['85', 'P 4 / n'], ['85', 'P 4/n'], ['85', 'P4/n'],
               ['86', 'C 42 / a'], ['86', 'P 42 / n'], ['86', 'P 42/n'], ['86', 'P4_2/n'], ['86', 'P42/n'],
               ['87', 'F 4 / m'], ['87', 'I 4 / m'], ['87', 'I 4/m'], ['87', 'I4/m'],
               ['88', 'F 41 / d'], ['88', 'I 41 / a'], ['88', 'I 41/a'], ['88', 'I4_1/a'], ['88', 'I41/a'],
               ['89', 'C 4 2 2'], ['89', 'P 4 2 2'], ['89', 'P422'],
               ['90', 'C 4 2 21'], ['90', 'P 4 21 2'], ['90', 'P4212'],
               ['91', 'C 41 2 2'], ['91', 'P 41 2 2'], ['91', 'P4_122'], ['91', 'P4122'],
               ['92', 'C 41 2 21'], ['92', 'P 41 21 2'], ['92', 'P4_12_12'], ['92', 'P41212'],
               ['93', 'C 42 2 2'], ['93', 'P 42 2 2'], ['93', 'P4222'],
               ['94', 'C 42 2 21'], ['94', 'P 42 21 2'], ['94', 'P42212'],
               ['95', 'C 43 2 2'], ['95', 'P 43 2 2'], ['95', 'P4_322'], ['95', 'P4322'],
               ['96', 'C 43 2 21'], ['96', 'P 43 21 2'], ['96', 'P4_32_12'], ['96', 'P43212'],
               ['97', 'F 4 2 2'], ['97', 'I 4 2 2'], ['97', 'I422'],
               ['98', 'F 41 2 2'], ['98', 'I 41 2 2'], ['98', 'I4_122'], ['98', 'I4122'],
               ['99', 'C 4 m m'], ['99', 'P 4 m m'], ['99', 'P4mm'],
               ['100', 'C 4 m b'], ['100', 'P 4 b m'], ['100', 'P4bm'],
               ['101', 'C 42 m c'], ['101', 'P 42 c m'], ['101', 'P42cm'],
               ['102', 'C 42 m n'], ['102', 'P 42 n m'], ['102', 'P4_2nm'], ['102', 'P42nm'],
               ['103', 'C 4 c c'], ['103', 'P 4 c c'], ['103', 'P4cc'],
               ['104', 'C 4 c n'], ['104', 'P 4 n c'], ['104', 'P4nc'],
               ['105', 'C 42 c m'], ['105', 'P 42 m c'], ['105', 'P4_2mc'], ['105', 'P42mc'],
               ['106', 'C 42 c b'], ['106', 'P 42 b c'], ['106', 'P42bc'],
               ['107', 'F 4 m m'], ['107', 'I 4 m m'], ['107', 'I4mm'],
               ['108', 'F 4 m c'], ['108', 'I 4 c m'], ['108', 'I4cm'],
               ['109', 'F 41 d m'], ['109', 'I 41 m d'], ['109', 'I41md'],
               ['110', 'F 41 d c'], ['110', 'I 41 c d'], ['110', 'I4_1cd'], ['110', 'I41cd'],
               ['111', 'C -4 m 2'], ['111', 'P -4 2 m'], ['111', 'P-42m'], ['111', 'P42m'],
               ['112', 'C -4 c 2'], ['112', 'P -4 2 c'], ['112', 'P-42c'], ['112', 'P42c'],
               ['113', 'C -4 m 21'], ['113', 'P -4 21 m'], ['113', 'P421m'],
               ['114', 'C -4 c 21'], ['114', 'P -4 21 c'], ['114', 'P421c'],
               ['115', 'C -4 2 m'], ['115', 'P -4 m 2'], ['115', 'P-4m2'], ['115', 'P4m2'],
               ['116', 'C -4 2 c'], ['116', 'P -4 c 2'], ['116', 'P4c2'],
               ['117', 'C -4 2 b'], ['117', 'C-42b'], ['117', 'P -4 b 2'], ['117', 'P-4b2'], ['117', 'P4b2'],
               ['118', 'C -4 2 n'], ['118', 'P -4 n 2'], ['118', 'P-4n2'], ['118', 'P4n2'],
               ['119', 'F -4 2 m'], ['119', 'I -4 m 2'], ['119', 'I-4m2'], ['119', 'I4m2'],
               ['120', 'F -4 2 c'], ['120', 'I -4 c 2'], ['120', 'I-4c2'], ['120', 'I4c2'],
               ['121', 'F -4 m 2'], ['121', 'I -4 2 m'], ['121', 'I-42m'], ['121', 'I42m'],
               ['122', 'F -4 d 2'], ['122', 'F-4d2'], ['122', 'I -4 2 d'], ['122', 'I-42d'], ['122', 'I42d'],
               ['123', 'C 4 / m m m'], ['123', 'P 4 / m m m'], ['123', 'P 4/m 2/m 2/m'], ['123', 'P4/mmm'], ['123', 'P 4/m m m'],
               ['124', 'C 4 / m c c'], ['124', 'P 4 / m c c'], ['124', 'P 4/m 2/c 2/c'], ['124', 'P4/mcc'], ['124', 'P 4/m c c'],
               ['125', 'C 4 / a m b'], ['125', 'P 4 / n b m'], ['125', 'P 4/n 2/b 2/m'], ['125', 'P4/nbm'], ['125', 'P 4/n b m'],
               ['126', 'C 4 / a c n'], ['126', 'P 4 / n n c'], ['126', 'P 4/n 2/n 2/c'], ['126', 'P4/nnc'], ['126', 'P 4/n n c'],
               ['127', 'C 4 / m m b'], ['127', 'P 4 / m b m'], ['127', 'P 4/m 21/b 2/m'], ['127', 'P4/mbm'], ['127', 'P 4/m b m'],
               ['128', 'C 4 / m c n'], ['128', 'P 4 / m n c'], ['128', 'P 4/m 21/n 2/c'], ['128', 'P4/mnc'], ['128', 'P 4/m n c'],
               ['129', 'C 4 / a m m'], ['129', 'P 4 / n m m'], ['129', 'P 4/n 21/m 2/m'], ['129', 'P4/nmm'], ['129', 'P 4/n m m'],
               ['130', 'C 4 / a c c'], ['130', 'P 4 / n c c'], ['130', 'P 4/n c c'], ['130', 'P 4/n 21/c 2/c'], ['130', 'P4/ncc'],
               ['131', 'C 42 / m c m'], ['131', 'P 42 / m m c'], ['131', 'P 42/m 2/m 2/c'], ['131', 'P4_2/mmc'], ['131', 'P42/mmc'], ['131', 'P 42/m m c'],
               ['132', 'C 42 / m m c'], ['132', 'P 42 / m c m'], ['132', 'P 42/m 2/c 2/m'], ['132', 'P4_2/mcm'], ['132', 'P42/mcm'],
               ['133', 'C 42 / a c b'], ['133', 'P 42 / n b c'], ['133', 'P 42/n 2/b 2/c'], ['133', 'P4_2/nbc'], ['133', 'P42/nbc'], ['133', 'P 42/n b c'],
               ['134', 'C 42 / a n m'], ['134', 'P 42 / n n m'], ['134', 'P 42/n 2/n 2/m'], ['134', 'P4_2/nnm'], ['134', 'P42/nnm'], ['134', 'P 42/n n m'],
               ['135', 'C 42 / m c b'], ['135', 'P 42 / m b c'], ['135', 'P 42/m 21/b 2/c'], ['135', 'P4_2/mbc'], ['135', 'P42/mbc'], ['135', 'P 42/m b c'],
               ['136', 'C 42 / m m n'], ['136', 'P 42 / m n m'], ['136', 'P 42/m n m'], ['136', 'P 42/m 21/n 2/m'], ['136', 'P4_2/mnm'], ['136', 'P42/mnm'],
               ['137', 'C 42 / a c m'], ['137', 'P 42 / n m c'], ['137', 'P 42/n 21/m 2/c'], ['137', 'P4_2/nmc'], ['137', 'P42/nmc'], ['137', 'P 42/n m c'],
               ['138', 'C 42 / a m c'], ['138', 'P 42 / n c m'], ['138', 'P 42/n 21/c 2/m'], ['138', 'P4_2/ncm'], ['138', 'P42/ncm'], ['138', 'P 42/n c m'],
               ['139', 'F 4 / m m m'], ['139', 'F4/mmm'], ['139', 'I 4 / m m m'], ['139', 'I 4/m 2/m 2/m'], ['139', 'I4/mmm'], ['139', 'I 4/m m m'], ['139', 'F 4/m m m'],
               ['140', 'F 4 / m m c'], ['140', 'I 4 / m c m'], ['140', 'I 4/m 2/c 2/m'], ['140', 'I4/mcm'], ['140', 'I 4/m c m'], 
               ['141', 'F 41 / d d m'], ['141', 'I 41 / a m d'], ['141', 'I 41/a 2/m 2/d'],['141', 'I4_1/amd'], ['141', 'I41/amd'], ['141', 'I 41/a m d'],
               ['142', 'F 41 / d d c'], ['142', 'I 41 / a c d'], ['142', 'I 41/a c d'], ['142', 'I 41/a 2/c 2/d'], ['142', 'I4_1/acd'], ['142', 'I41/acd'],
               ['143', 'H 3'], ['143', 'P 3'], ['143', 'P3'],
               ['144', 'H 31'], ['144', 'P 31'], ['144', 'P3_1'], ['144', 'P31'],
               ['145', 'H 32'], ['145', 'P 32'], ['145', 'P3_2'], ['145', 'P32'],
               ['146', 'R 3'], ['146', 'R3'],
               ['147', 'H -3'], ['147', 'P -3'], ['147', 'P-3'],
               ['148', 'R -3'], ['148', 'R-3'],
               ['149', 'H 3 2 1'], ['149', 'P 3 1 2'], ['149', 'P312'],
               ['150', 'H 3 1 2'], ['150', 'P 3 2 1'],
               ['151', 'H 31 2 1'], ['151', 'P 31 1 2'], ['151', 'P3_112'], ['151', 'P3112'],
               ['152', 'H 31 1 2'], ['152', 'P 31 2 1'], ['152', 'P3_121'], ['152', 'P3121'],
               ['153', 'H 32 2 1'], ['153', 'P 32 1 2'], ['153', 'P3_212'], ['153', 'P3212'],
               ['154', 'H 32 1 2'], ['154', 'P 32 2 1'], ['154', 'P3_221'], ['154', 'P3221'],
               ['155', 'R 3 2'], ['155', 'R32'],
               ['156', 'H 3 1 m'], ['156', 'P 3 m 1'], ['156', 'P3m1'],
               ['157', 'H 3 m 1'], ['157', 'P 3 1 m'], ['157', 'P31m'],
               ['158', 'H 3 1 c'], ['158', 'P 3 c 1'], ['158', 'P3c1'],
               ['159', 'H 3 c 1'], ['159', 'P 3 1 c'], ['159', 'P31c'],
               ['160', 'R 3 m'], ['160', 'R3m'],
               ['161', 'R 3 c'], ['161', 'R3c'],
               ['162', 'H -3 m 1'], ['162', 'P -3 1 m'], ['162', 'P-31m'],
               ['163', 'H -3 c 1'], ['163', 'P -3 1 c'], ['163', 'P-31c'],
               ['164', 'H -3 1 m'], ['164', 'P -3 m 1'], ['164', 'P-3m1'],
               ['165', 'H -3 1 c'], ['165', 'P -3 c 1'], ['165', 'P-3c1'],
               ['166', 'R -3 m'], ['166', 'R-3m'],
               ['167', 'R -3 c'], ['167', 'R-3c'], ['167', 'R -3 2/c'],
               ['168', 'P 6'], ['168', 'P6'],
               ['169', 'P 61'], ['169', 'P6_1'], ['169', 'P61'],
               ['170', 'P 65'], ['170', 'P6_5'], ['170', 'P65'],
               ['171', 'P 62'], ['171', 'P62'],
               ['172', 'P 64'], ['172', 'P64'],
               ['173', 'P 63'], ['173', 'P6_3'], ['173', 'P63'],
               ['174', 'P -6'], ['174', 'P-6'],
               ['175', 'P 6 / m'], ['175', 'P 6/m'], ['175', 'P6/m'],
               ['176', 'P 63 / m'], ['176', 'P 63/m'], ['176', 'P6_3/m'], ['176', 'P63/m'],
               ['177', 'P 6 2 2'], ['177', 'P622'],
               ['178', 'P 61 2 2'], ['178', 'P6122'],
               ['179', 'P 65 2 2'], ['179', 'P6_522'], ['179', 'P6522'],
               ['180', 'P 62 2 2'], ['180', 'P6_222'], ['180', 'P6222'],
               ['181', 'P 64 2 2'], ['181', 'P6_422'], ['181', 'P6422'],
               ['182', 'P 63 2 2'], ['182', 'P6_322'], ['182', 'P6322'],
               ['183', 'P 6 m m'], ['183', 'P6mm'],
               ['184', 'P 6 c c'], ['184', 'P6cc'],
               ['185', 'P 63 c m'], ['185', 'P6_3cm'], ['185', 'P63cm'],
               ['186', 'P 63 m c'], ['186', 'P6_3mc'], ['186', 'P63mc'],
               ['187', 'P -6 m 2'], ['187', 'P-6m2'], ['187', 'P6m2'],
               ['188', 'P -6 c 2'], ['188', 'P-6c2'], ['188', 'P6c2'],
               ['189', 'P -6 2 m'], ['189', 'P-62m'], ['189', 'P62m'],
               ['190', 'P -6 2 c'], ['190', 'P-62c'], ['190', 'P62c'],
               ['191', 'P 6 / m m m'], ['191', 'P 6/m 2/m 2/m'], ['191', 'P6/mmm'], ['191', 'P 6/m m m '],
               ['192', 'P 6 / m c c'], ['192', 'P 6/m c c'], ['192', 'P 6/m 2/c 2/c'], ['192', 'P6/mcc'],
               ['193', 'P 63 / m c m'], ['193', 'P 63/m 2/c 2/m'], ['193', 'P6_3/mcm'], ['193', 'P63/mcm'], ['63', 'P 63/m c m'],
               ['194', 'P 63/m m c'], ['194', 'P 63 / m m c'], ['194', 'P 63/m 2/m 2/c'], ['194', 'P6_3/mmc'], ['194', 'P63/mmc'],
               ['195', 'P 2 3'], ['195', 'P23'],
               ['196', 'F 2 3'], ['196', 'F23'],
               ['197', 'I 2 3'], ['197', 'I23'],
               ['198', 'P2_13'], ['198', 'P213'], ['198', 'P 21 3'],
               ['199', 'I2_13'], ['199', 'I 21 3'],
               ['200', 'P m -3'], ['203', 'P m 3'],
               ['201', 'P n -3'], ['201', 'Pn3'], ['201', 'P n 3'],
               ['202', 'F m -3'], ['202', 'Fm3'], ['202', 'F m 3'],
               ['203', 'F d -3'], ['203', 'Fd3'], ['203', 'F d 3'],
               ['204', 'I m -3'], ['204', 'Im3'], ['204', 'I m 3'],
               ['205', 'P a -3'], ['205', 'P a 3'], ['205', 'Pa3'],
               ['206', 'I a -3'], ['206', 'Ia3'], ['206', 'I a 3'],
               ['207', 'P 4 3 2'], ['207', 'P432'],
               ['208', 'P 42 3 2'], ['208', 'P4_232'], ['208', 'P4232'],
               ['209', 'F 4 3 2'], ['209', 'F432'],
               ['210', 'F 41 3 2'], ['210', 'F4132'],
               ['211', 'I 4 3 2'], ['211', 'I432'], ['211', 'Pm-3m'],
               ['212', 'P 43 3 2'], ['212', 'P4_332'], ['212', 'P4332'],
               ['213', 'P 41 3 2'], ['213', 'P4_132'], ['213', 'P4132'],
               ['214', 'I 41 3 2'], ['214', 'I4_132'], ['214', 'I4132'],
               ['215', 'P -4 3 m'], ['215', 'P-43m'], ['215', 'P43m'],
               ['216', 'F -4 3 m'], ['216', 'F-43m'], ['216', 'F43m'],
               ['217', 'I -4 3 m'], ['217', 'I-43m'], ['217', 'I43m'],
               ['218', 'P -4 3 n'], ['218', 'P-43n'], ['218', 'P43n'],
               ['219', 'F -4 3 c'], ['219', 'F-43c'], ['219', 'F43c'],
               ['220', 'I -4 3 d'], ['220', 'I-43d'], ['220', 'I43d'],
               ['221', 'P m -3 m'], ['221', 'P m 3 m'], ['221', 'Pm3m'], ['221', 'P 4/m -3 2/m'],
               ['222', 'P n -3 n'], ['222', 'Pn3n'],
               ['223', 'P m -3 n'], ['223', 'Pm3n'], ['223', 'P m 3 n'],
               ['224', 'P n -3 m'], ['224', 'Pn3m'], ['224', 'P n 3 m'],
               ['225', 'F m -3 m'], ['225', 'F m 3 m'], ['225', 'Fm-3m'], ['225', 'Fm3m'],
               ['226', 'F m -3 c'], ['226', 'Fm3c'],
               ['227', 'F d -3 m'], ['227', 'Fd-3m'], ['227', 'F d 3 m'], ['227', 'Fd3m'],
               ['228', 'F d -3 c'], ['228', 'Fd3c'], ['228', 'F d 3 c'],
               ['229', 'I m -3 m'], ['229', 'Im-3m'], ['229', 'Im3m'], ['229', 'I m 3 m'],
               ['230', 'I a -3 d'], ['230', 'Ia-3d'], ['230', 'Ia3d'], ['230', 'I a 3 d']]
CATEGORIES = ['soil',
              'salt',
              'clay']

QMIN = 0.3
QMAX = 8.0
QSTEP = 0.01

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
    def __init__(self, dbname=None, read_only=True,verbose=False):

        ## This needs to be modified for creating new if does not exist.
        self.dbname=dbname
        if verbose:
            print '\n\n================ %s ================\n' % self.dbname
        if not os.path.exists(self.dbname):
            parent, child = os.path.split(__file__)
            self.dbname = os.path.join(parent, self.dbname)
            if not os.path.exists(self.dbname):
                print("File '%s' not found; building a new database!" % self.dbname)
                self.build_new_database(name=self.dbname)
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


    def open_database(self):

        print '\nAccessing database: %s' % self.dbname
        self.metadata = MetaData('sqlite:///%s' % self.dbname)
    
    def build_new_database(self,name=None):

        if name is None:
            self.dbname = 'amscd%02d.db'
            counter = 0
            while os.path.exists(self.dbname % counter):
                counter += 1
            self.dbname = self.dbname % counter
        else:
            self.dbname = name
    
        self.open_database()

        ###################################################
        ## Look up tables
        element_table = Table('allelements', self.metadata,
                Column('atomic_no', Integer, primary_key=True),
                Column('element_name', String(40), unique=True, nullable=True),
                Column('element_symbol', String(2), unique=True, nullable=False)
                )
        mineral_table = Table('allminerals', self.metadata,
                Column('mineral_id', Integer, primary_key=True),
                Column('mineral_name', String(30), unique=True, nullable=True)
                )
        spacegroup_table = Table('allspacegroups', self.metadata,
                Column('iuc_id', Integer),
                Column('hm_notation', String(16), unique=True, nullable=True),
                PrimaryKeyConstraint('iuc_id', 'hm_notation')
                )
        symmetry_table = Table('allsymmetries', self.metadata,
                Column('symmetry_id', Integer, primary_key=True),
                Column('symmetry_name', String(16), unique=True, nullable=True)
                )
        authorlist_table = Table('allauthors', self.metadata,
                Column('author_id', Integer, primary_key=True),
                Column('author_name', String(40), unique=True, nullable=True)
                )
        qrange_table = Table('qrange', self.metadata,
                Column('q_id', Integer, primary_key=True),
                #Column('q', Integer)
                Column('q', String())
                )
        categorylist_table = Table('allcategories', self.metadata,
                Column('category_id', Integer, primary_key=True),
                Column('category_name', String(16), unique=True, nullable=True)
                )
        ###################################################
        ## Cross-reference tables
        geometry_table = Table('symmetry', self.metadata,
                Column('iuc_id', None, ForeignKey('allspacegroups.iuc_id')),
                Column('symmetry_id', None, ForeignKey('allsymmetries.symmetry_id')),
                PrimaryKeyConstraint('iuc_id', 'symmetry_id')
                )
        composition_table = Table('composition', self.metadata,
                Column('atomic_no', None, ForeignKey('allelements.atomic_no')),
                Column('amcsd_id', None, ForeignKey('allcif.amcsd_id')),
                PrimaryKeyConstraint('atomic_no', 'amcsd_id')
                )
        author_table = Table('author', self.metadata,
                Column('author_id', None, ForeignKey('allauthors.author_id')),
                Column('amcsd_id', None, ForeignKey('allcif.amcsd_id')),
                PrimaryKeyConstraint('author_id', 'amcsd_id')
                )
        qpeak_table = Table('qpeaks', self.metadata,
                Column('q_id', None, ForeignKey('qrange.q_id')),
                Column('amcsd_id', None, ForeignKey('allcif.amcsd_id')),
                PrimaryKeyConstraint('q_id', 'amcsd_id')
                )
        category_table = Table('category', self.metadata,
                Column('category_id', None, ForeignKey('allcategories.category_id')),
                Column('amcsd_id', None, ForeignKey('allcif.amcsd_id')),
                PrimaryKeyConstraint('category_id', 'amcsd_id')
                )
        ###################################################
        ## Main table
        cif_table = Table('allcif', self.metadata,
                Column('amcsd_id', Integer, primary_key=True),
                Column('mineral_id', Integer),
                Column('iuc_id', ForeignKey('allspacegroups.iuc_id')),
                Column('cif', String(25)) ## , nullable=True
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
        self.new_category = categorylist_table.insert()

        self.new_cif = cif_table.insert()

        self.cif_composition = composition_table.insert()
        self.cif_author      = author_table.insert()
        self.cif_qpeaks      = qpeak_table.insert()
        # self.cif_category    = category_table.insert()


        ###################################################
        ## Populate the fixed tables of the database

        ## Adds all elements into database
        for element in ELEMENTS:
            atomic_no, name, symbol = element
            self.populate_elements.execute(atomic_no=int(atomic_no),
                                           element_name=name,
                                           element_symbol=symbol)

        ## Adds all crystal symmetries
        for symmetry_id,symmetry in enumerate(SYMMETRIES):
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

        for cat in CATEGORIES:
            self.new_category.execute(category_name=cat)

        ## Adds qrange
        qrange = np.arange(QMIN,QMAX+QSTEP,QSTEP)
        for q in qrange:
            self.populate_q.execute(q=float('%0.2f' % q))

        ## Adds all space groups
        for spgrp in SPACEGROUPS:
            iuc_id,name = spgrp
            try:
                self.populate_spgrp.execute(iuc_id=str(iuc_id),hm_notation=name)
            except:
                print('Duplicate: %s %s' % (str(iuc_id),name))
                pass
  
    def load_database(self):

        ###################################################
        ## Look up tables
        self.allcif = Table('allcif', self.metadata)
        self.allelements = Table('allelements', self.metadata)
        self.allminerals = Table('allminerals', self.metadata)
        self.allspacegroups = Table('allspacegroups', self.metadata)
        self.allsymmetries = Table('allsymmetries', self.metadata)
        self.allauthors = Table('allauthors', self.metadata)
        self.qrange = Table('qrange', self.metadata)
        self.allcategories = Table('allcategories', self.metadata)

        ###################################################
        ## Cross-reference tables
        self.symmetry = Table('symmetry', self.metadata)
        self.composition = Table('composition', self.metadata)
        self.author = Table('author', self.metadata)
        self.qpeak = Table('qpeaks', self.metadata)
        self.category = Table('category', self.metadata)


    def add_cif_to_db(self,cifile,verbose=True,url=False):
        '''
            ## Adds cifile into database
            When reading in new CIF:
            -->  put entire cif into field
            -->  read _database_code_amcsd - write 'amcsd_id' to 'cif data'
            -->  read _chemical_name_mineral - find/add in' minerallist' - write 'mineral_id' to 'cif data'
            -->  read _symmetry_space_group_name_H-M - find in 'spacegroup' - write iuc_id to 'cif data'
            -->  read author name(s) - find/add in 'authorlist' - write 'author_id','amcsd_id' to 'author'
            -->  read _chemical_formula_sum - write 'atomic_no','amcsd_id' to 'composition'
            -->  calculate q - find each corresponding 'q_id' for all peaks - in write 'q_id','amcsd_id' to 'qpeak'
        '''

        if not HAS_CifFile or not HAS_XRAYUTIL:
            print('Missing required package(s) for this function:')
            print('Have CifFile? %r' % HAS_CifFile)
            print('Have xrayutilities? %r' % HAS_XRAYUTIL)
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
        self.allcif = Table('allcif', self.metadata)
        search_cif = self.allcif.select(self.allcif.c.amcsd_id == amcsd_id)
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

   
        ## generate hkl list
        hkllist = generate_hkl(maxhkl=3)

        energy = 8048 # units eV

        if url:
            cifstr = requests.get(cifile).text
        else:
            with open(cifile,'r') as file:
                cifstr = str(file.read())

        try:
            if url:
                cif = xu.materials.Crystal.fromCIF('/fromweb/file.cif',fid=cStringIO.StringIO(cifstr))
            else:
                cif = xu.materials.Crystal.fromCIF(cifile)
    
            qlist = cif.Q(hkllist)
            Flist = cif.StructureFactorForQ(qlist,energy)


            all_qid = []
            for i,hkl in enumerate(hkllist):
                if np.abs(Flist[i]) > 0.01:
                    qid = int((np.linalg.norm(qlist[i])-QMIN)/QSTEP)
                    if qid not in all_qid:
                        all_qid.append(qid)
        except:
            
            print 'Could not import : %s' % cifile
            
            path = '%s/CIF_Errant/' % os.path.split(__file__)[0]
            if not os.path.exists(path):
                command = 'mkdir %s' % path
                os.system(command)
            
            if url:
                i = int(cifile.split('=')[-2].split('.')[0])
                file = 'amcsd%05d.cif' % i
                r = requests.get(cifile)
                f = open(file,'w')
                f.write(r.text)
            else:
                command = 'cp %s %s/.' % (cifile,path)
                os.system(command)
            return

       
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
            print '\tSpace group? ----> %s (amcsd: %i)' % (hm_notation,int(amcsd_id))

        ## Save CIF entry into database
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
                print('could not find element: %s (amcsd: %i)' % (element,int(amcsd_id)))
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

        for calc_q_id in all_qid:
            search_q = self.qrange.select(self.qrange.c.q_id == calc_q_id)
            for row in search_q.execute():
                q_id = row.q_id
                self.cif_qpeaks.execute(q_id=q_id,amcsd_id=int(amcsd_id))

    #     ## not ready for defined categories
    #     cif_category.execute(category_id='none',
    #                          amcsd_id=int(amcsd_id))

        if url:
            if verbose:
                self.print_cif_entry(amcsd_id,ALLelements,mineral_name,iuc_id,authors)
        else:
            if verbose:
                self.print_cif_entry(amcsd_id,ALLelements,mineral_name,iuc_id,authors,cifile=cifile)
            else:
                print 'File : %s' % os.path.split(cifile)[-1]

    def find_by_amcsd(self,amcsd_id):

        self.load_database()

        search_cif = self.allcif.select(self.allcif.c.amcsd_id == amcsd_id)
        for row in search_cif.execute():
            cifstr = row.cif
            mineral_id = row.mineral_id
            iuc_id = row.iuc_id

        search_mineralname = self.allminerals.select(self.allminerals.c.mineral_id == mineral_id)
        for row in search_mineralname.execute():
            mineral_name = row.mineral_name

        search_composition = self.composition.select(self.composition.c.amcsd_id == amcsd_id)
        ALLelements = []
        for row in search_composition.execute():
            atomic_no = row.atomic_no
            search_periodic = self.allelements.select(self.allelements.c.atomic_no == atomic_no)
            for block in search_periodic.execute():
                ALLelements.append(block.element_symbol)

        search_authors = self.author.select(self.author.c.amcsd_id == amcsd_id)
        authors = []
        for row in search_authors.execute():
            author_id = row.author_id
            search_alist = self.allauthors.select(self.allauthors.c.author_id == author_id)
            for block in search_alist.execute():
                authors.append(block.author_name)
        
        self.print_cif_entry(amcsd_id,ALLelements,mineral_name,iuc_id,authors)
        
    def create_array(self):
    
        self.load_database()
        cif_array = {}
        
        search_cif = self.allcif.select()
        count = 0
        for cifrow in search_cif.execute():
            amcsd_id = cifrow.amcsd_id
            mineral_id = cifrow.mineral_id
            iuc_id = cifrow.iuc_id
            
            mineral_name = ''
            search_mineralname = self.allminerals.select(self.allminerals.c.mineral_id == mineral_id)
            for mnrlrow in search_mineralname.execute():
                mineral_name = mnrlrow.mineral_name
        
            search_composition = self.composition.select(self.composition.c.amcsd_id == amcsd_id)
            composition = ''
            for cmprow in search_composition.execute():
                atomic_no = cmprow.atomic_no
                search_periodic = self.allelements.select(self.allelements.c.atomic_no == atomic_no)
                for elmtrow in search_periodic.execute():
                    composition = '%s %s' % (composition,elmtrow.element_symbol)
                    
            search_authors = self.author.select(self.author.c.amcsd_id == amcsd_id)
            authors = ''
            for atrrow in search_authors.execute():
                author_id = atrrow.author_id
                search_alist = self.allauthors.select(self.allauthors.c.author_id == author_id)
                for block in search_alist.execute():
                    if authors == '':
                        authors = '%s' % (block.author_name)
                    else:
                        authors = '%s; %s' % (authors,block.author_name)

            count = count + 1
            cif_array.update({count:(str(amcsd_id),str(mineral_name),str(iuc_id),str(composition),str(authors))})
        
        return cif_array

    def print_cif_entry(self,amcsd_id,ALLelements,mineral_name,iuc_id,authors,cifile=None):

        if cifile:
            print ' ==== File : %s ====' % os.path.split(cifile)[-1] 
        else:
            print ' ===================== '
        print ' AMCSD: %i' % amcsd_id

        elementstr = ' Elements: '
        for element in ALLelements:
            elementstr = '%s %s' % (elementstr,element)
        print elementstr
        print ' Name: %s' % mineral_name
        print ' Space Group No.: %s' % iuc_id
        authorstr = ' Author: '
        for author in authors:
            authorstr = '%s %s' % (authorstr,author.split()[0])
        print authorstr
        print ' ===================== '
        print

    
    def mine_for_cif(self,verbose=False,save=False,addDB=True,url=None):
    
        if url is None:
            url = 'http://rruff.geo.arizona.edu/AMS/download.php?id=%05d.cif&down=cif'

        for i in range(99999):
        #for i in range(100,200):
            url_to_scrape = url % i
            try:
                r = requests.get(url_to_scrape)

                if r.text.split()[0] == "Can't" or '':
                    if verbose:
                        print('\t---> ERROR on amcsd%05d.cif' % i)
                else:
                    if verbose:
                        print('Reading %s' % url_to_scrape)

                    if save:
                        file = 'amcsd%05d.cif' % i
                        f = open(file,'w')
                        f.write(r.text)
                        f.close()
                        if verbose:
                            print 'Saved %s' % file
                    if addDB:
                        self.add_cif_to_db(url_to_scrape,url=True,verbose=verbose)
            except:
                pass

## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
##
## --- xrayutilities method for reading cif ---
##
##         search_cif = self.allcif.select(self.allcif.c.amcsd_id == amcsd_id)
##         for row in search_cif.execute():
##             cifstr = row.cif
##         cif = xu.materials.Crystal.fromCIF('/fromdatabase/file.cif',fid=cStringIO.StringIO(cifstr))
##
## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
