import os
from larch.io import read_ascii, guess_beamline

def _tester(fname):
    fname = os.path.join('..', 'examples', 'xafsdata', 'beamlines', fname)
    group = read_ascii(fname)
    cls = guess_beamline(group.header)
    bldat = cls(group.header)
    labels = bldat.get_array_labels()
    print(fname, cls.__name__, len(labels), group.data.shape, labels)
    return bldat, labels

def test_apsxsd_new(fname):
    bldat, labels = _tester(fname)
    assert('aps xsd' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(labels[0]  == 'mono_energy')
    assert(labels[1].startswith('scaler_pre'))
    assert(labels[4].startswith('i0'))


def test_apsxsd_old(fname):
    bldat, labels = _tester(fname)
    assert('aps xsd' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(labels[0]  == 'mono_energy')
    assert(labels[1].startswith('scaler_pre'))
    assert(labels[2] == 'i0')


def test_apsmrcat(fname):
    bldat, labels = _tester(fname)
    assert('aps mrcat' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) == 5)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'io')
    assert(labels[2]  == 'it')
    assert(labels[3]  == 'iref')


def test_apsgse(fname):
    bldat, labels = _tester(fname)
    assert('gse epicsscan' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) == 21)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'tscaler')
    assert(labels[2]  == 'i0')
    assert(labels[3]  == 'i1')
    assert(labels[4]  == 'i2')
    assert(labels[5]  == 'mn_ka_mca1')

def test_apsgse_old(fname):
    bldat, labels = _tester(fname)
    assert('gse epicsscan' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) == 4)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'scaler_count_time')
    assert(labels[2]  == 'i0')
    assert(labels[3]  == 'i1')


def test_aps12bm(fname):
    bldat, labels = _tester(fname)
    assert('12bm' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('keV' == bldat.energy_units)
    assert(len(labels) == 26)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'sec')
    assert(labels[2]  == 'mononrg')
    assert(labels[3]  == 'i0')
    assert(labels[4]  == 'i1')
    assert(labels[5]  == 'i2')

def test_aps9bm2006(fname):
    bldat, labels = _tester(fname)
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 5)
    assert(labels[0]  == 'energy')
    assert('i0' in labels)

def test_esrfsnbl(fname):
    bldat, labels = _tester(fname)
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 5)
    assert(labels[0]  == 'mon')
    assert(labels[1]  == 'det1')
    assert(labels[2]  == 'det2')

def test_nsls2_6bm(fname):
    bldat, labels = _tester(fname)
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 5)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'requested_energy')
    assert(labels[2]  == 'measurement_time')
    assert(labels[3]  == 'xmu')
    assert(labels[4]  == 'i0')

def test_nsls2_8id(fname):
    bldat, labels = _tester(fname)
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 5)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'i0')
    assert(labels[2]  == 'ir')
    assert(labels[3]  == 'it')
    assert(labels[4]  == 'iff')

def test_ssrl1(fname):
    bldat, labels = _tester(fname)
    assert(3 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) == 6)
    assert(labels[0]  == 'real_time_clock')
    assert(labels[1]  == 'requested_energy')
    assert(labels[2]  == 'achieved_energy')
    assert(labels[3]  == 'i0')
    assert(labels[4]  == 'i1')
    assert(labels[5]  == 'i2')

def test_ssrl2(fname):
    bldat, labels = _tester(fname)
    assert(2 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 65)
    assert(labels[0]  == 'real_time_clock')
    assert(labels[1]  == 'requested_energy')
    assert(labels[2]  == 'i0')
    assert(labels[3]  == 'i1')
    assert(labels[4]  == 'i2')
    assert(labels[5]  == 'sca1_1')

def test_nslsxdac(fname):
    bldat, labels = _tester(fname)
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 15)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'i0')
    assert(labels[2]  == 'it')
    assert(labels[3]  == 'ifch1')
    assert(labels[4]  == 'ifch2')

def test_clshxma(fname):
    bldat, labels = _tester(fname)
    assert(4 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 10)
    assert(labels[0]  == 'event_id')
    assert(labels[1]  == 'absenergyname')
    assert(labels[2]  == 'energyfeedback')
    assert(labels[3]  == 'energyachieved')
    assert(labels[4]  == 'detector1')

def test_kekpf12c(fname):
    bldat, labels = _tester(fname)
    assert(2 == bldat.energy_column)
    assert('deg' == bldat.energy_units)
    assert(bldat.mono_dspace > 3)
    assert(len(labels) == 5)

if __name__ == '__main__':
    test_apsxsd_new('APS9BM_2019.dat')
    test_apsxsd_old('APS20BM_2001.dat')
    test_apsgse('APS13ID_2019.dat')
    test_apsgse_old('APS13ID_2008.dat')
    test_apsmrcat('APS10BM_2019.dat')
    test_aps12bm('APS12BM_2019.dat')
    test_aps9bm2006('APS9BM_2006.dat')
    test_esrfsnbl('ESRF_SNBL_2013.dat')
    test_nsls2_8id('NSLS8ID_2019.dat')
    test_nsls2_6bm('NSLS6BM_2019.dat')
    test_ssrl1('SSRL1_2006.dat')
    test_ssrl2('SSRLmicro_2008.dat')
    test_nslsxdac('NSLS_XDAC_2011.dat')
    test_clshxma('CLSHXMA.dat')
    test_kekpf12c('PFBL12C_2005.dat')
