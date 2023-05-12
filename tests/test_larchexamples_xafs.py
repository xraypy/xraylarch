#!/usr/bin/env python
""" Tests of Larch Scripts  """
import unittest
from pathlib import Path
import time
import ast
import numpy as np
from sys import version_info

from utils import TestCase
from larch import Interpreter

base_dir = Path(__file__).parent.parent.resolve()

class TestScripts(TestCase):
    '''testing of asteval'''
    def test01_basic(self):
        self.runscript('a.lar', dirname=base_dir / 'tests' / 'larch_scripts')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("n < 10")
        self.isTrue("n >  5")
        self.isTrue("x >  3")

    def test02_autobk(self):
        self.runscript('doc_autobk1.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("cu.e0 > 8950.0")
        self.isTrue("len(cu.k) > 200")
        self.isTrue("max(abs(cu.chi)) < 2.0")

    def test03_autobk2(self):
        self.runscript('doc_autobk2.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("dat.e0 > 10000.0")
        self.isTrue("len(dat.k) > 200")

    def test04_autobk_clamp(self):
        self.runscript('doc_autobk3.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("dat.e0 > 11000.0")
        self.isTrue("len(dat.k) > 200")

    def test05_autobk_with_std(self):
        self.runscript('doc_autobk4.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("cu2.e0 > 8950.0")
        self.isTrue("len(cu2.k) > 200")
        self.isTrue("max(abs(cu2.chi)) < 2.0")

    def test06_ftwin1(self):
        self.runscript('doc_ftwin1.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(hann_win1) == 401")
        self.isTrue("hann_win3.sum() > 50.0")

        self.runscript('doc_ftwin2.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(kai_win1) == 401")
        self.isTrue("kai_win1.sum() > 20.0")

    def test07_xafsft1(self):
        self.runscript('doc_xafsft1.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(d2.k) > 200")
        self.isTrue("len(d2.kwin) > 200")
        self.isTrue("d1.chir_mag.sum() > 30")
        self.isTrue("where(d1.chir_mag>1)[0][0] > 60")

    def test08_xafsft2(self):
        self.runscript('doc_xafsft2.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(d3.k) > 200")
        self.isTrue("len(d3.kwin) > 200")
        self.isTrue("len(d4.k) > 200")
        self.isTrue("len(d4.kwin) > 200")
        self.isTrue("len(d1.r) > 100")
        self.isTrue("len(d1.chir_mag) > 100")
        self.isTrue("len(d3.r) > 100")
        self.isTrue("len(d3.chir_mag) > 100")
        self.isTrue("len(d4.r) > 100")
        self.isTrue("len(d4.chir_mag) > 100")
        self.isTrue("len(d4.chir_re) > 100")
        self.isTrue("len(d4.chir_im) > 100")


    def test09_xafsft3(self):
        self.runscript('doc_xafsft3.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(dat.k) > 200")
        self.isTrue("len(dat.kwin) > 200")

    def test10_xafsft3(self):
        self.runscript('doc_xafsft4.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(dat.r) > 200")
        self.isTrue("len(dat.rwin) > 200")
        self.isTrue("len(dat.q) > 200")
        self.isTrue("len(dat.chiq_re) > 200")

    def test11_wavelet1(self):
        self.runscript('wavelet_example.lar', dirname=base_dir / 'examples' / 'xafs')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("f.wcauchy_im.shape == (326, 318)")
        self.isTrue("f.wcauchy_mag.sum() > 300")

    def test12_feffit_kws(self):
        self.runscript('test_epsk_kws.lar', dirname=base_dir / 'examples' / 'feffit')
        assert(len(self.session.get_errors()) == 0)
        out = self.session.run('out')
        for row in out:
            amp = row[5]
            amp_err = row[5]
            delr= row[7]
            self.assertTrue(amp > 0.5)
            self.assertTrue(amp < 2.0)
            self.assertTrue(amp_err > 0.0)
            self.assertTrue(amp_err < 2.0)
            self.assertTrue(abs(delr) < 0.1)

    def test13_feffit1(self):
        self.runscript('doc_feffit1.lar', dirname=base_dir / 'examples' / 'feffit')
        assert(len(self.session.get_errors()) == 0)

        self.isTrue('out.nfev > 20')
        self.isTrue('out.nfev < 100')
        self.isTrue('out.chi_square > 0.2')
        self.isTrue('out.chi_square < 2000')
        self.isNear('pars.amp.value',     1.0, places=1)
        self.isNear('pars.del_e0.value',    0, places=1)
        self.isNear('pars.del_r.value',     0, places=1)
        self.isNear('out.paramgroup.amp.value',     0.93, places=1)
        self.isNear('out.paramgroup.del_e0.value',  4.364, places=1)
        self.isNear('out.paramgroup.del_e0.stderr', 0.52, places=1)
        self.isNear('out.paramgroup.del_r.value',  -0.006, places=3)
        self.isNear('out.paramgroup.sig2.value',    0.0087, places=3)

    def test14_feffdat3(self):
        self.runscript('doc_feffdat3.lar', dirname=base_dir / 'examples' / 'feffit')
        assert(len(self.session.get_errors()) == 0)

        self.isNear('path1.degen',  6.0, places=1)
        self.isNear('path1.e0', -0.5, places=1)
        self.isNear('path1.reff',  2.1387, places=2)
        self.isNear('path1.rmass',  12.436, places=2)
        self.isNear('path1.s02',     0.9, places=2)
        self.isNear('path1.sigma2',  0.003, places=2)

        self.isTrue('path1.deltar == 0')
        self.isTrue('path1.ei == 0')
        self.isTrue('path1.filename == "feff_feo01.dat"')
        self.isTrue('path1.fourth == 0')
        self.isTrue('path1.nleg == 2')
        self.isTrue('path1.third == 0')
        self.isTrue('path1.geom[0][0] == "Fe"')
        self.isTrue('path1.geom[1][0] == "O"')
        self.isTrue('path1.geom[0][1] == 26')
        self.isTrue('path1.geom[1][1] == 8')


    def test15_feffit2(self):
        self.runscript('doc_feffit2.lar', dirname=base_dir / 'examples' / 'feffit')
        assert(len(self.session.get_errors()) == 0)

        self.isTrue('out.nfev > 50')
        self.isTrue('out.nfev < 200')

        self.isTrue('out.chi_square > 4')
        self.isTrue('out.chi_square < 100')
        self.isTrue('out.rfactor < 0.003')
        self.isTrue('out.aic < 1000')
        self.isNear("out.params['sig2_1'].value", 0.00868, places=2)
        self.isNear("out.params['del_e0'].value",    5.75,    places=1)
        self.isNear("out.params['amp'].value",    0.933,  places=1)

        self.isNear('path1.reff',    2.5478,  places=3)
        self.isNear('path1.rmass',  31.773,   places=2)


    def test16_feffit3(self):
        self.runscript('doc_feffit3.lar', dirname=base_dir / 'examples' / 'feffit')
        assert(len(self.session.get_errors()) == 0)

        self.isTrue('out.nfev > 15')
        self.isTrue('out.nfev < 50')

        self.isTrue('out.chi_square > 140')
        self.isTrue('out.chi_square < 10000')

        self.isTrue('out.aic < 1000')
        self.isNear("out.params['theta'].value", 233., places=0)
        self.isNear("out.params['del_e0'].value", 5.3,  places=0)
        self.isNear("out.params['amp'].value", 0.87,  places=0)


    def test17_feffit3extra(self):
        self.runscript('doc_feffit3.lar', dirname=base_dir / 'examples' / 'feffit')
        self.runscript('doc_feffit3_extra.lar', dirname=base_dir / 'examples' / 'feffit')
        assert(len(self.session.get_errors()) == 0)
        self.isNear('_ave', 0.005030, places=4)
        self.isNear('_dlo', 0.000315, places=4)




if __name__ == '__main__':  # pragma: no cover
    for suite in (TestScripts,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=13).run(suite)
