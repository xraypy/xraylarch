import numpy as np
import h5py
from larch.io import read_xdi
from larch.utils.strutils import bytes2str
from larch.math.utils import safe_log
from larch.utils.physical_constants import (STD_LATTICE_CONSTANTS,
                                            DEG2RAD, PLANCK_HC)
NXXAS_URL = 'https://download.nexusformat.org/doc/html/classes/applications/NXxas.html'

def parse_mono_reflection(refl):
    refl = refl.replace(',', ' ').strip()
    if refl.startswith('(') and refl.endswith(')'):
        refl = refl[1:-1]
    if len(refl) == 3:
        return tuple([int(refl[0]), int(refl[1]), int(refl[2])])
    return tuple([int(r) for r in refl.split()])


NXXAS_LINKS = {'element': 'scan/xrayedge/element',
               'edge':    'scan/xrayedge/edge',
               'energy':  'instrument/monochromator/energy',
               'rawdata': 'scan/data',
               'column_labels': '/scan/column_labels',
               'i0':      'instrument/i0/data'}


def xdi2NXxas(xdidata, h5root, name='entry', compress=None):
    """add XDI data to an NXxas group in a NeXuS HDF5 file:

    Arguments
    -----------
    xdidata   an XDI data group as read with read_xdi()
    h5root    hdf5 group to add new NXxas group to
    name      str, name of group under h5root                ['entry']
    compress  dict, options for compression of array datasets   [None]


    Notes
    ------
    1 the default compress dict is {'compression': 'gzip', 'compression_opts': 4}
    """
    if compress is None:
        compress = {'compression': 'gzip', 'compression_opts': 4}

    if name in h5root:
        base = name[:]
        for i in range(1, 100000):
            name = f'{base}_{i:02d}'
            if name not in h5root:
                break
    entry_name = name
    xas = h5root.create_group(entry_name)
    xas.attrs['NX_class'] = 'NXentry'

    xdi_scan = xdidata.attrs.get('scan', {})
    xdi_mono = xdidata.attrs.get('mono', {})
    xdi_dets = xdidata.attrs.get('detectpr', {})
    xdi_sample = xdidata.attrs.get('sample', {})
    xdi_bline = xdidata.attrs.get('beamline', {})
    xdi_facil = xdidata.attrs.get('facility', {})

    start_time = xdi_scan.get('start_time', '')

    title = xdi_sample.get('name', None)
    if title is None:
        title = xdidata.filename
    title = f'{title}  [{xdidata.element} {xdidata.edge} edge]'

    xas.create_dataset('title',  data=title)
    s =xas.create_dataset('start_time',  data=start_time)
    s.attrs['NX_class'] = 'NX_DATE_TIME'
    s = xas.create_dataset('definition',  data='NXxas')
    s.attrs['URL'] = NXXAS_URL

    # instrument
    instrument = xas.create_group('instrument')
    instrument.attrs['NX_class'] = 'NXinstrument'

    # instrument/source
    isource = instrument.create_group('source')
    isource.attrs['NX_class'] = 'NXsource'
    sname = [xdi_facil.get('name', 'unknown facility'),
             xdi_facil.get('xray_source', 'unknkown source'),
             xdi_bline.get('name', 'unknown beamline')]
    isource.create_dataset('name', data=', '.join(sname))

    source_energy = xdi_facil.get('energy', '0 Unknown')
    try:
        s_en, units = source_energy.split()
        source_energy = float(s_en)
    except:
        source_energy, units = 0, 'Unknown'
    s = isource.create_dataset('energy', data=source_energy)
    s.attrs['units'] = units
    isource.create_dataset('type', data='X-ray Source')
    isource.create_dataset('probe', data='X-ray')
    for key, val in xdi_facil.items():
        isource.create_dataset(f'facility_{key}', data=val)
    for key, val in xdi_bline.items():
        isource.create_dataset(f'beamline_{key}', data=val)

    # instrument/mono
    imono = instrument.create_group('monochromator')
    imono.attrs['NX_class'] = 'NXmonochromator'

    # instrument/mono/crystal
    imonoxtal = imono.create_group('crystal')
    imonoxtal.attrs['NX_class'] = 'NXcrystal'
    mono_name = xdi_mono.get('name', 'Si (111)')
    try:
        mono_chem, mono_refl = mono_name.split()
    except:
        mono_chem, mono_refl = 'Si', '111'
    mono_chem = mono_chem.title()
    mono_refl = parse_mono_reflection(mono_refl)
    mono_dspacing = xdi_mono.get('d_spacing', None)
    if mono_dspacing is None:
        mono_dspacing = 0.0
        if mono_chem in STD_LATTICE_CONSTANTS:
            latt_c  = STD_LATTICE_CONSTANTS[mono_chem]
            hkl2 = mono_refl[0]**2 + mono_refl[1]**2 + mono_refl[2]**2
            mono_dspacing = latt_c / np.sqrt(hkl2)
    else:
         mono_dspacing = float(mono_dspacing)

    if not hasattr(xdidata, 'energy') and hasattr(xdidata, 'angle'):
        omega = PLANCK_HC/(2*mono_dspacing)
        xdidata.energy = omega/np.sin(xdidata.angle*DEG2RAD)
        en_units = 'eV'
    else:
        ien = xdidata.array_labels.index('energy')
        en_units = 'eV'
        if ien > -1:
            en_units = xdidata.array_units[ien]

    s = imono.create_dataset('energy', data=xdidata.energy, **compress)
    s.attrs['units'] = en_units
    if hasattr(xdidata, 'angle'):
        s = imono.create_dataset('angle', data=xdidata.angle, **compress)
        s.attrs['units'] = 'degrees'


    imonoxtal.create_dataset('chemical_formula', data=mono_chem)
    imonoxtal.create_dataset('reflection', data=mono_refl)
    s = imonoxtal.create_dataset('d_spacing', data=mono_dspacing)
    s.attrs['units'] = 'Angstroms'

    # instrument/i0
    idet = instrument.create_group('i0')
    idet.attrs['NX_class'] = 'NXdetector'
    idet.create_dataset('data', data=xdidata.i0, **compress)
    desc = xdi_dets.get('i0', None)
    if desc is None:
        desc = xdi_dets.get('monitor', None)
    if desc is not None:
        idet.create_dataset('description', data=desc)

    # instrument/itrans
    if hasattr(xdidata, 'itrans'):
        idet = instrument.create_group('itrans')
        idet.attrs['NX_class'] = 'NXdetector'
        idet.create_dataset('data', data=xdidata.itrans, **compress)
        desc = xdi_dets.get('itrans', None)
        if desc is None:
            desc = xdi_dets.get('i1', None)
        if desc is not None:
            idet.create_dataset('description', data=desc)

    # instrument/ifluor
    if hasattr(xdidata, 'ifluor'):
        idet = instrument.create_group('ifluor')
        idet.attrs['NX_class'] = 'NXdetector'

        idet.create_dataset('data', data=xdidata.ifluor, **compress)
        desc = xdi_dets.get('ifluor', None)
        if desc is None:
            desc = xdi_dets.get('if', None)
        if desc is not None:
            idet.create_dataset('description', data=desc)
        mode = xdi_dets.get('fluor_mode', 'Unknown')
        idet.create_dataset('mode', data=mode)

    # instrument/irefer
    if hasattr(xdidata, 'irefer'):
        idet = instrument.create_group('irefer')
        idet.attrs['NX_class'] = 'NXdetector'

        idet.create_dataset('data', data=xdidata.irefer, **compress)
        desc = xdi_dets.get('irefer', None)
        if desc is None:
            desc = xdi_dets.get('ir', None)
        if desc is not None:
            idet.create_dataset('description', data=desc)
        refmode = xdi_dets.get('refer_mode', 'Unknown')
        idet.create_dataset('mode', data=mode)

    # sample
    sample = xas.create_group('sample')
    sample.attrs['NX_class'] = 'NXsample'
    for key, val in xdi_sample.items():
        sample.create_dataset(key, data=val)

    # scan
    scan = xas.create_group('scan')
    scan.attrs['NX_class']  = 'NXscan'
    for key, val in xdi_scan.items():
        scan.create_dataset(key, data=val)

    ncol, nrow = xdidata.data.shape
    scan.create_dataset('nP', data=nrow)
    scan.create_dataset('nCol', data=ncol)

    xedge = scan.create_group('xrayedge')
    xedge.attrs['NX_class'] = 'NXxrayedge'
    xedge.create_dataset('element', data=xdidata.element)
    xedge.create_dataset('edge', data=xdidata.edge)

    scan.create_dataset('scan_mode', data=xdi_scan.get('mode', 'Unknown'))
    scan.create_dataset('data', data=xdidata.data.transpose(), **compress)
    scan.create_dataset('column_labels', data=xdidata.array_labels)

    # data arrays: mostly links to the data above
    dat = xas.create_group('data')
    dat.attrs['NX_class'] = 'NXdata'
    mode = 'Transmission'
    if not hasattr(xdidata, 'itrans') and hasattr(xdidata, 'ifluor'):
        mode = 'Fluorescence'
    dat.create_dataset('mode', data=mode)

    slinks = {k: v for k,v in NXXAS_LINKS.items()}

    if hasattr(xdidata, 'itrans'):
        slinks['itrans'] = 'instrument/itrans/data'
        mutrans = -safe_log(xdidata.itrans/xdidata.i0)
        dat.create_dataset('mutrans', data=mutrans, **compress)

    if hasattr(xdidata, 'ifluor'):
        slink['ifluor'] = 'instrument/ifluor/data'
        mufluor = xdidata.ifluor/xdidata.i0
        dat.create_dataset('mufluor', data=mufluor, **compress)

    if hasattr(xdidata, 'irefer'):
        slink['irefer'] = 'instrument/irefer/data'
        if refmode.startswith('Fluo'):
            muref = xdidata.irefer/xdidata.i0
        else:
            muref = -safe_log(xdidata.irefer/xdidata.itrans)
        dat.create_dataset('murefer', data=murefer, **compress)

    for dest, source in slinks.items():
        dat[dest] =  h5py.SoftLink(f'/{entry_name}/{source}')

class NXxasFile(object):
    """
    NeXuS NXxas data file
    """
    def __init__(self, filename):
        self.filename = filename
        self.xas_groups = None
        if filename is not None:
            self.read(filename)

    def read(self, filename):
        self.root = h5py.File(filename, 'r')
        self.xas_groups = []
        for key, grp in self.root.items():
            attrs = grp.attrs.items()
            if grp.attrs.get('NX_class', None) != 'NXentry':
                continue
            defn = grp.get('definition', None)
            if isinstance(defn, h5py.Dataset):
                if bytes2str(defn[()]) == 'NXxas':
                    self.xas_groups.append(key)

    def add_xdidata(xdidata, name='entry'):
        """add Entry/Group for data from an XDI file"""
        xdi2NXxas(xdidata, self.root, name=name)
