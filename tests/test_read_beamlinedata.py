from pathlib import Path
from larch.io import read_ascii, guess_beamline, guess_filereader, read_fdmnes

base_dir = Path(__file__).parent.parent.resolve()

def _tester(fname, return_group=False):
    fname =  base_dir / 'examples' / 'xafsdata' / 'beamlines' / fname
    group = read_ascii(fname)
    cls = guess_beamline(group.header)
    bldat = cls(group.header)
    labels = bldat.get_array_labels()
    print(fname, cls.__name__, len(labels), group.data.shape, labels)
    if return_group:
        return bldat, labels, group
    else:
        return bldat, labels

def test_apsxsd_new(fname='APS9BM_2019.dat'):
    bldat, labels = _tester(fname)
    assert('aps xsd' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(labels[0]  == 'mono_energy')
    assert(labels[1].startswith('scaler_pre'))
    assert(labels[4].startswith('i0'))


def test_apsxsd20id_newer(fname='APS20ID_2022.dat'):
    bldat, labels = _tester(fname)
    assert('aps xsd' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(labels[0].startswith('mono_energy'))
    assert(labels[1].startswith('scaler_pre'))
    assert(labels[-1] == "xsp3_4_total")
    assert('it' in labels)


def test_apsxsd20id_new(fname='APS20ID_2018.dat'):
    bldat, labels = _tester(fname)
    assert('aps xsd' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(labels[0].startswith('mono_energy'))
    assert(labels[1].startswith('scaler_pre'))
    assert('it' in labels)


def test_apsxsd_old(fname='APS20BM_2001.dat'):
    bldat, labels = _tester(fname)
    assert('aps xsd' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(labels[0]  == 'mono_energy')
    assert(labels[1].startswith('scaler_pre'))
    assert(labels[2] == 'i0')


def test_apsmrcat(fname='APS10BM_2019.dat'):
    bldat, labels = _tester(fname)
    assert('aps mrcat' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) == 5)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'io')
    assert(labels[2]  == 'it')
    assert(labels[3]  == 'iref')

def test_apsgse(fname='APS13ID_2019.dat'):
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

def test_apsgse_old(fname='APS13ID_2008.dat'):
    bldat, labels = _tester(fname)
    assert('gse epicsscan' in bldat.name.lower())
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) == 4)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'scaler_count_time')
    assert(labels[2]  == 'i0')
    assert(labels[3]  == 'i1')

def test_aps12bm(fname='APS12BM_2019.dat'):
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

def test_aps9bm2006(fname='APS9BM_2006.dat'):
    bldat, labels = _tester(fname)
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 5)
    assert(labels[0]  == 'energy')
    assert('i0' in labels)

def test_esrfsnbl(fname='ESRF_SNBL_2013.dat'):
    bldat, labels = _tester(fname)
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 5)
    assert(labels[0]  == 'mon')
    assert(labels[1]  == 'det1')
    assert(labels[2]  == 'det2')

def test_nsls2_6bm(fname='NSLS6BM_2019.dat'):
    bldat, labels = _tester(fname)
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 5)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'requested_energy')
    assert(labels[2]  == 'measurement_time')
    assert(labels[3]  == 'xmu')
    assert(labels[4]  == 'i0')

def test_nsls2_8id(fname='NSLS8ID_2019.dat'):
    bldat, labels = _tester(fname)
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 5)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'i0')
    assert(labels[2]  == 'ir')
    assert(labels[3]  == 'it')
    assert(labels[4]  == 'iff')

def test_ssrl1(fname='SSRL1_2006.dat'):
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

def test_ssrl2(fname='SSRLmicro_2008.dat'):
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

def test_nslsxdac(fname='NSLS_XDAC_2011.dat'):
    bldat, labels = _tester(fname)
    assert(1 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 15)
    assert(labels[0]  == 'energy')
    assert(labels[1]  == 'i0')
    assert(labels[2]  == 'it')
    assert(labels[3]  == 'ifch1')
    assert(labels[4]  == 'ifch2')

def test_clshxma(fname='CLSHXMA.dat'):
    bldat, labels = _tester(fname)
    assert(4 == bldat.energy_column)
    assert('eV' == bldat.energy_units)
    assert(len(labels) > 10)
    assert(labels[0]  == 'event_id')
    assert(labels[1]  == 'absenergyname')
    assert(labels[2]  == 'energyfeedback')
    assert(labels[3]  == 'energyachieved')
    assert(labels[4]  == 'detector1')

def test_kekpf12c(fname='PFBL12C_2005.dat'):
    bldat, labels = _tester(fname)
    assert(2 == bldat.energy_column)
    assert('deg' == bldat.energy_units)
    assert(bldat.mono_dspace > 3)
    assert(len(labels) == 5)

def test_one_line_header(fname='ESRF_BM08_LISA_2021.dat'):
    bldat, labels = _tester(fname)
    assert(labels == ['ebraggenergy', 'i0_eh1', 'i1_eh1', 'mu', 'i1_eh2', 'ir_eh2', 'mu_ref'])

def test_zero_line_header(fname='generic_columns_no_header.dat'):
    bldat, labels, group = _tester(fname, return_group=True)
    assert(group.array_labels == ['col1', 'col2', 'col3', 'col4', 'col5', 'col6', 'col7'])

def test_fdmnes(fnames=['FDMNES_2022_Mo2C_out.dat', 'FDMNES_2022_Mo2C_out_conv.dat']):
    for fname in fnames:
        fname =  base_dir / 'examples' / 'xafsdata' / 'beamlines' / fname
        assert(guess_filereader(fname) == 'read_fdmnes')
        group = read_fdmnes(fname)
        assert(group.array_labels == ['energy', 'xanes'])
        assert(group.header_dict['E_edge'] == 20000.0)

if __name__ == '__main__':
    test_apsxsd_new()
    test_apsxsd_old()
    test_apsgse()
    test_apsgse_old()
    test_apsmrcat()
    test_aps12bm()
    test_aps9bm2006()
    test_esrfsnbl()
    test_nsls2_8id()
    test_nsls2_6bm()
    test_ssrl1()
    test_ssrl2()
    test_nslsxdac()
    test_clshxma()
    test_kekpf12c()
    test_one_line_header()
    test_zero_line_header()
    test_fdmnes()
