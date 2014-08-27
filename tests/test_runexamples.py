#!/usr/bin/env python
""" Tests of Larch Scripts  """
import unittest
import time
import ast
import numpy as np
from sys import version_info

from utils import TestCase
from larch import Interpreter
class TestScripts(TestCase):
    '''testing of asteval'''
    def test1_basic(self):
        self.runscript('a.lar', dirname='larch_scripts')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("n < 10")
        self.isTrue("n >  5")
        self.isTrue("x >  3")

    def test2_autobk(self):
        self.runscript('doc_autobk1.lar', dirname='../examples/xafs/')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("cu.e0 > 8950.0")
        self.isTrue("len(cu.k) > 200")
        self.isTrue("max(abs(cu.chi)) < 2.0")

    def test3_autobk2(self):
        self.runscript('doc_autobk2.lar', dirname='../examples/xafs/')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("dat.e0 > 10000.0")
        self.isTrue("len(dat.k) > 200")

    def test4_autobk_clamp(self):
        self.runscript('doc_autobk3.lar', dirname='../examples/xafs/')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("dat.e0 > 11000.0")
        self.isTrue("len(dat.k) > 200")

    def test5_autobk_with_std(self):
        self.runscript('doc_autobk4.lar', dirname='../examples/xafs/')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("cu2.e0 > 8950.0")
        self.isTrue("len(cu2.k) > 200")
        self.isTrue("max(abs(cu2.chi)) < 2.0")

    def test6_ftwin1(self):
        self.runscript('doc_ftwin1.lar', dirname='../examples/xafs/')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(hann_win1) == 401")
        self.isTrue("hann_win3.sum() > 50.0")

        self.runscript('doc_ftwin2.lar', dirname='../examples/xafs/')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(kai_win1) == 401")
        self.isTrue("kai_win1.sum() > 20.0")
       
    def test7_xafsft1(self):
        self.runscript('doc_xafsft1.lar', dirname='../examples/xafs/')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(d2.k) > 200")
        self.isTrue("len(d2.kwin) > 200")
        self.isTrue("d1.chir_mag.sum() > 30")
        self.isTrue("where(d1.chir_mag>1)[0][0] > 60")

    def test8_xafsft2(self):
        self.runscript('doc_xafsft2.lar', dirname='../examples/xafs/')
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


    def test9_xafsft3(self):
        self.runscript('doc_xafsft3.lar', dirname='../examples/xafs/')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(dat.k) > 200")
        self.isTrue("len(dat.kwin) > 200")

    def test10_xafsft3(self):
        self.runscript('doc_xafsft4.lar', dirname='../examples/xafs/')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(dat.r) > 200")
        self.isTrue("len(dat.rwin) > 200")
        self.isTrue("len(dat.q) > 200")
        self.isTrue("len(dat.chiq_re) > 200")


    def test11_wavelet1(self):
        self.runscript('wavelet_example.lar', dirname='../examples/xafs/')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("f.wcauchy_im.shape == (326, 318)")
        self.isTrue("f.wcauchy_mag.sum() > 300")


if __name__ == '__main__':  # pragma: no cover
    for suite in (TestScripts,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=3).run(suite)
        

