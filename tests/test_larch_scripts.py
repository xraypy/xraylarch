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

if __name__ == '__main__':  # pragma: no cover
    for suite in (TestScripts,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=3).run(suite)
        

