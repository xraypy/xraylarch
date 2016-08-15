#!/usr/bin/env python
"""
SQLAlchemy wrapping of x-ray database for data from
     Elam et al, Chantler et al, Waasmaier and Kirfel

Main Class for full Database:  xrayDB
"""

import os
import time
import json
import six
import numpy as np
from scipy.interpolate import interp1d, splrep, splev, UnivariateSpline
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker, mapper, clear_mappers
from sqlalchemy.pool import SingletonThreadPool

# needed for py2exe?
import sqlalchemy.dialects.sqlite
import larch
from larch_plugins.math import as_ndarray

def OLDas_ndarray(obj):
    """make sure a float, int, list of floats or ints,
    or tuple of floats or ints, acts as a numpy array
    """
    if isinstance(obj, (float, int)):
        return np.array([obj])
    return np.asarray(obj)

def make_engine(dbname):
    return create_engine('sqlite:///%s' % (dbname),
                         poolclass=SingletonThreadPool)

def isxrayDB(dbname):
    """test if a file is a valid scan database:
    must be a sqlite db file, with tables named
    'Coster_Kronig', 'elements', 'photoabsorption', 'scattering'

    """
    _tables = ('Chantler', 'Waasmaier', 'Coster_Kronig',
               'KeskiRahkonen_Krause',
               'elements', 'photoabsorption', 'scattering')
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


def elam_spline(xin, yin, yspl_in, x):
    """ interpolate values from Elam photoabsorption and scattering tables,
    according to Elam, Numerical Recipes.  Calc borrowed from D. Dale.
    """
    x = as_ndarray(x)
    x[np.where(x < min(xin))] =  min(xin)
    x[np.where(x > max(xin))] =  max(xin)

    lo, hi = np.array([(np.flatnonzero(xin < e)[-1],
                        np.flatnonzero(xin > e)[0])
                       for e in x]).transpose()

    diff = xin[hi] - xin[lo]
    if any(diff <= 0):
        raise ValueError('x must be strictly increasing')
    a = (xin[hi] - x) / diff
    b = (x - xin[lo]) / diff
    return (a * yin[lo] + b * yin[hi] +
            (diff*diff/6) * ((a*a - 1) * a * yspl_in[lo] +
                             (b*b - 1) * b * yspl_in[hi] ))


class DBException(Exception):
    """DB Access Exception: General Errors"""
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg
    def __str__(self):
        return self.msg

class _BaseTable(object):
    "generic class to encapsulate SQLAlchemy table"
    def __repr__(self):
        el = getattr(self, 'element', '??')
        return "<%s(%s)>" % (self.__class__.__name__, el)

class CosterKronigTable(_BaseTable):
    (id, element, initial_level, final_level,
     transition_probability, total_transition_probability) = [None]*6

class ElementsTable(_BaseTable):
    (atomic_number, element, molar_mass, density) = [None]*4

class PhotoAbsorptionTable(_BaseTable):
    (id, element, log_energy,
     log_photoabsorption, log_photoabsorption_spline) = [None]*5

class ScatteringTable(_BaseTable):
    (id, element, log_energy,
     log_coherent_scatter, log_coherent_scatter_spline,
     log_incoherent_scatter, log_incoherent_scatter_spline) = [None]*7

class XrayLevelsTable(_BaseTable):
    (id, element,  iupac_symbol,
     absorption_edge, fluorescence_yield, jump_ratio) = [None]*6
    def __repr__(self):
        el = getattr(self, 'element', '??')
        edge= getattr(self, 'iupac_symbol', '??')
        return "<%s(%s %s)>" % (self.__class__.__name__, el, edge)

class XrayTransitionsTable(_BaseTable):
    (id, element, iupac_symbol, siegbahn_symbol, initial_level,
     final_level, emission_energy, intensity) = [None]*8
    def __repr__(self):
        el = getattr(self, 'element', '??')
        line = getattr(self, 'siegbahn_symbol', '??')
        return "<%s(%s %s)>" % (self.__class__.__name__, el, line)

class WaasmaierTable(_BaseTable):
    (id, atomic_number, element, ion, offset, scale, exponents) = [None]*7
    def __repr__(self):
        el = getattr(self, 'ion', '??')
        return "<%s(%s)>" % (self.__class__.__name__, el)

class KeskiRahkonenKrauseTable(_BaseTable):
    (id, atomic_number, element, edge, width) = [None]*5
    def __repr__(self):
        el = getattr(self, 'element', '??')
        edge = getattr(self, 'edge', '??')
        return "<%s(%s %s)>" % (self.__class__.__name__, el, edge)

class ChantlerTable(_BaseTable):
    (id, element, sigma_mu, mue_f2, density,
     corr_henke, corr_cl35, corr_nucl,
     energy, f1, f2, mu_photo, mu_incoh, mu_total) = [None]*14

class xrayDB(object):
    "interface to Xray Data"
    def __init__(self, dbname='xrayref.db', read_only=True):
        "connect to an existing database"
        if not os.path.exists(dbname):
            parent, child = os.path.split(__file__)
            dbname = os.path.join(parent, dbname)
            if not os.path.exists(dbname):
                raise IOError("Database '%s' not found!" % dbname)

        if not isxrayDB(dbname):
            raise ValueError("'%s' is not a valid X-ray Database file!" % dbname)

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

        clear_mappers()
        mapper(ChantlerTable,            tables['Chantler'])
        mapper(WaasmaierTable,           tables['Waasmaier'])
        mapper(KeskiRahkonenKrauseTable, tables['KeskiRahkonen_Krause'])
        mapper(ElementsTable,            tables['elements'])
        mapper(XrayLevelsTable,          tables['xray_levels'])
        mapper(XrayTransitionsTable,     tables['xray_transitions'])
        mapper(CosterKronigTable,        tables['Coster_Kronig'])
        mapper(PhotoAbsorptionTable,     tables['photoabsorption'])
        mapper(ScatteringTable,          tables['scattering'])


    def close(self):
        "close session"
        self.session.flush()
        self.session.close()

    def query(self, *args, **kws):
        "generic query"
        return self.session.query(*args, **kws)

    def f0_ions(self, element=None):
        """return list of ion names supported for the .f0() calculation
        from Waasmaier and Kirfel

        arguments
        ---------
        element:  atomic number, atomic symbol or ionic symbol
                  (case insensitive) of scatterer

        if element is None, all 211 ions are returned.  If element is
        not None, the ions for that element (atomic symbol) are returned
        """
        rows = self.query(WaasmaierTable)
        if element is not None:
            if isinstance(element, int):
                rows = rows.filter(WaasmaierTable.atomic_number==element)
            else:
                rows = rows.filter(WaasmaierTable.element==element.title())
        return [str(r.ion) for r in rows.all()]

    def f0(self, ion, q):
        """Calculate f0(q) -- elastic x-ray scattering factor
        from Waasmaier and Kirfel

        arguments
        ---------
        ion:  atomic number, atomic symbol or ionic symbol
              (case insensitive) of scatterer

        q: single q value, list, tuple, or numpy array of q value
             q = sin(theta) / lambda
             theta = incident angle, lambda = x-ray wavelength

        Z values from 1 to 98 (and symbols 'H' to 'Cf') are supported.
        The list of ionic symbols can be read with the function .f0_ions()
        """
        tab = WaasmaierTable
        row = self.query(tab)
        if isinstance(ion, int):
            row = row.filter(tab.atomic_number==ion).all()
        else:
            row = row.filter(tab.ion==ion.title()).all()
        if len(row) > 0:
            row = row[0]
        if isinstance(row, tab):
            q = as_ndarray(q)
            f0 = row.offset
            for s, e in zip(json.loads(row.scale), json.loads(row.exponents)):
                f0 += s * np.exp(-e*q*q)
            return f0

    def _getChantler(self, element, energy, column='f1', smoothing=0):
        """return energy-dependent data from Chantler table
        columns: f1, f2, mu_photo, mu_incoh, mu_total
        """
        tab = ChantlerTable
        row = self.query(tab)
        if isinstance(element, int):
            row = row.filter(tab.id==element).all()
        else:
            row = row.filter(tab.element==element.title()).all()
        if len(row) > 0:
            row = row[0]
        if isinstance(row, tab):
            energy = as_ndarray(energy)
            emin, emax = min(energy), max(energy)
            # te = self.chantler_energies(element, emin=emin, emax=emax)
            te = np.array(json.loads(row.energy))
            nemin = max(0, -5 + max(np.where(te<=emin)[0]))
            nemax = min(len(te), 6 + max(np.where(te<=emax)[0]))
            region = np.arange(nemin, nemax)
            te = te[region]
            if column == 'mu':
                column = 'mu_total'
            ty = np.array(json.loads(getattr(row, column)))[region]
            if column == 'f1':
                out = UnivariateSpline(te, ty, s=smoothing)(energy)
            else:
                out = np.exp(np.interp(np.log(energy),
                                       np.log(te),
                                       np.log(ty)))
            if isinstance(out, np.ndarray) and len(out) == 1:
                return out[0]
            return out

    def chantler_energies(self, element, emin=0, emax=1.e9):
        """ return array of energies (in eV) at which data is
        tabulated in the Chantler tables for a particular element.

        arguments
        ---------
        element:  atomic number, atomic symbol for element

        emin:  lower bound of energies in eV returned (default=0)
        emax:  upper bound of energies in eV returned (default=1.e9)
        """
        tab = ChantlerTable
        row = self.query(tab)
        if isinstance(element, int):
            row = row.filter(tab.id==element).all()
        else:
            row = row.filter(tab.element==element.title()).all()
        if len(row) > 0:
            row = row[0]
        if not isinstance(row, tab):
            return None
        te = np.array(json.loads(row.energy))
        tf1 = np.array(json.loads(row.f1))
        tf2 = np.array(json.loads(row.f2))

        if emin <= min(te):
            nemin = 0
        else:
            nemin = max(0,  -2 + max(np.where(te<=emin)[0]))
        if emax > max(te):
            nemax = len(te)
        else:
            nemax = min(len(te), 2 + max(np.where(te<=emax)[0]))
        region = np.arange(nemin, nemax)
        return te[region] # , tf1[region], tf2[region]

    def f1_chantler(self, element, energy, **kws):
        """returns f1 -- real part of anomalous x-ray scattering factor
        for selected input energy (or energies) in eV.
        """
        return self._getChantler(element, energy, column='f1', **kws)

    def f2_chantler(self, element, energy, **kws):
        """returns f2 -- imaginary part of anomalous x-ray scattering factor
        for selected input energy (or energies) in eV.
        """
        return self._getChantler(element, energy, column='f2', **kws)

    def mu_chantler(self, element, energy, incoh=False, photo=False):
        """returns mu/rho in cm^2/gr -- x-ray mass attenuation coefficient
        for selected input energy (or energies) in eV.
        default is to return total attenuation coefficient.
        use
          photo=True to return only the photo-electric contribution or
          incoh=True to return on the incoherent contribution
        """
        col = 'mu_total'
        if photo:
            col = 'mu_photo'
        elif incoh:
            col = 'mu_incoh'
        return self._getChantler(element, energy, column=col)

    def _getElementData(self, element):
        "get data from elements table"
        tab = ElementsTable
        row = self.query(tab)
        if isinstance(element, int):
            row = row.filter(tab.atomic_number==element).all()
        else:
            row = row.filter(tab.element==element.title()).all()
        if len(row) > 0: row = row[0]
        return row

    def zofsym(self, element):
        "return z for element name"
        return int(self._getElementData(element).atomic_number)

    def symbol(self, z):
        "return element symbol from z"
        return self._getElementData(z).element

    def molar_mass(self, element):
        "return molar mass of element"
        return self._getElementData(element).molar_mass

    def density(self, element):
        "return density of pure element"
        return self._getElementData(element).density

    def xray_edges(self, element):
        """returns dictionary of all x-ray absorption
        edge energy (in eV), fluorescence yield, and
        jump ratio for an element.

        the returned dictionary has keys of edge (iupac symol),
        each with value containing a tuple of (energy,
        fluorescence_yield, edge_jump)
        """
        if isinstance(element, int):
            element = self.symbol(element)
        tab = XrayLevelsTable
        out = {}
        for r in self.query(tab).filter(tab.element==element.title()).all():
            out[str(r.iupac_symbol)] = (r.absorption_edge,
                                        r.fluorescence_yield,
                                        r.jump_ratio)
        return out

    def xray_edge(self, element, edge):
        """returns tuple of (energy, fluorescence_yield, edge_jump)
        for an x-ray absorption edge
        """
        edge = edge.title()
        edges = self.xray_edges(element)
        if edge in edges:
            return edges[edge]

    def xray_lines(self, element, initial_level=None, excitation_energy=None):
        """returns dictionary of x-ray emission lines of an element, with
         key = siegbahn symbol (Ka1, Lb1, etc)  and
         value = (energy (in eV), intensity, initial_level, final_level)

        options:
         initial_level:     limit output to an initial level(s) -- a string or list of strings
         excitation_energy: limit output to those excited by given energy (in eV)

        Note that excitation energy will overwrite initial_level
        """
        if isinstance(element, int):
            element = self.symbol(element)
        tab = XrayTransitionsTable
        row = self.query(tab).filter(tab.element==element.title())
        if excitation_energy is not None:
            initial_level = []
            for ilevel, dat in self.xray_edges(element).items():
                if dat[0] < excitation_energy:
                    initial_level.append(ilevel.title())

        if initial_level is not None:
            if isinstance(initial_level, (list, tuple)):
                row = row.filter(tab.initial_level.in_(initial_level))
            else:
                row = row.filter(tab.initial_level==initial_level.title())
        out = {}
        for r in row.all():
            out[str(r.siegbahn_symbol)] = (r.emission_energy, r.intensity,
                                           r.initial_level, r.final_level)
        return out

    def CK_probability(self, element, initial, final, total=True):
        """return transition probability for an element and initial/final levels
        """
        if isinstance(element, int):
            element = self.symbol(element)
        tab = CosterKronigTable
        row = self.query(tab).filter(
            tab.element==element.title()
            ).filter(
            tab.initial_level==initial.title()
            ).filter(
            tab.final_level==final.title()).all()
        if len(row) > 0:
            row = row[0]
        if isinstance(row, tab):
            if total:
                return row.total_transition_probability
            else:
                return row.transition_probability

    def corehole_width(self, element=None, edge=None):
        """returns core hole width for an element and edge
        if element is None, values are returned for all elements
        if edge is None, values are return for all edges"""
        tab = KeskiRahkonenKrauseTable
        rows = self.query(tab)
        has_elem = element is not None
        has_edge = edge is not None
        if has_elem:
            if isinstance(element, int):
                rows = rows.filter(tab.atomic_number==element)
            else:
                rows = rows.filter(tab.element==element.title())
        if has_edge:
            rows = rows.filter(tab.edge==edge.title())
        out = rows.all()
        if len(out) == 1:
            return(out[0].width)
        elif has_elem:
            return [(r.edge, r.width) for r in out]
        elif has_edge:
            return [(r.atomic_number, r.width) for r in out]
        else:
            return [(r.atomic_number, r.edge, r.width) for r in out]

    def Elam_CrossSection(self, element, energies, kind='photo'):
        """returns Elam Cross Section values for an element and energies

        arguments
        ---------
        element:  atomic number, atomic symbol for element

        energies: energies in eV to calculate cross-sections
        kind:     one of 'photo', 'coh', and 'incoh' for photo-absorption,
                  coherent scattering, and incoherent scattering
                  cross sections, respectively.

        Data from Elam, Ravel, and Sieber.
        """
        if isinstance(element, int):
            element = self.symbol(element)
        energies = 1.0 * as_ndarray(energies)

        tab = ScatteringTable
        if kind == 'photo':
            tab = PhotoAbsorptionTable
        row = self.query(tab).filter(tab.element==element.title()).all()
        if len(row) > 0:
            row = row[0]
        if not isinstance(row, tab):
            return None

        tab_lne = np.array(json.loads(row.log_energy))
        if kind.lower().startswith('coh'):
            tab_val = np.array(json.loads(row.log_coherent_scatter))
            tab_spl = np.array(json.loads(row.log_coherent_scatter_spline))
        elif kind.lower().startswith('incoh'):
            tab_val = np.array(json.loads(row.log_incoherent_scatter))
            tab_spl = np.array(json.loads(row.log_incoherent_scatter_spline))
        else:
            tab_val = np.array(json.loads(row.log_photoabsorption))
            tab_spl = np.array(json.loads(row.log_photoabsorption_spline))

        emin_tab = 10*int(0.102*np.exp(tab_lne[0]))
        energies[np.where(energies < emin_tab)] = emin_tab
        out = np.exp(elam_spline(tab_lne, tab_val, tab_spl, np.log(energies)))
        if len(out) == 1:
            return out[0]
        return out

    def mu_elam(self, element, energies, kind='total'):
        """returns X-ray attenuation cross section for an element
        at energies (in eV)

        returns values in units of cm^2 / gr

        arguments
        ---------
        element:  atomic number, atomic symbol for element
        energies: energies in eV to calculate cross-sections
        kind:     'photo' or 'total' (default) for whether to
                  return photo-absorption or total cross-section.

        Data from Elam, Ravel, and Sieber.
        """
        calc = self.Elam_CrossSection
        xsec = calc(element, energies, kind='photo')
        if kind.lower().startswith('tot'):
            xsec += calc(element, energies, kind='coh')
            xsec += calc(element, energies, kind='incoh')

        return xsec

    def coherent_cross_section_elam(self, element, energies):
        """returns coherenet scattering cross section for an element
        at energies (in eV)

        returns values in units of cm^2 / gr

        arguments
        ---------
        element:  atomic number, atomic symbol for element
        energies: energies in eV to calculate cross-sections

        Data from Elam, Ravel, and Sieber.
        """
        return self.Elam_CrossSection(element, energies, kind='coh')

    def incoherent_cross_section_elam(self, element, energies):
        """returns incoherenet scattering cross section for an element
        at energies (in eV)

        returns values in units of cm^2 / gr

        arguments
        ---------
        element:  atomic number, atomic symbol for element
        energies: energies in eV to calculate cross-sections

        Data from Elam, Ravel, and Sieber.
        """
        return self.Elam_CrossSection(element, energies, kind='incoh')
