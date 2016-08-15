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
    '''tests'''

    def test_basic_interp(self):
        self.runscript('interp.lar', dirname='../examples/basic/')
        assert(len(self.session.get_errors()) == 0)
        self.isNear("y0[1]", 0.535, places=2)
        self.isNear("y1[1]", 0.829, places=2)
        self.isNear("y2[1]", 0.477, places=2)

    def test_basic_smooth(self):
        self.runscript('smoothing.lar', dirname='../examples/basic/')
        assert(len(self.session.get_errors()) == 0)
        self.isNear("s_loren[5]", 0.207, places=2)
        self.isNear("s_gauss[5]", 0.027, places=2)
        self.isNear("s_voigt[5]", 0.256, places=2)

    def test_basic_smooth(self):
        self.runscript('local_namespaces.lar', dirname='../examples/basic/')
        assert(len(self.session.get_errors()) == 0)
        self.isNear("x", 1000.0, places=4)

    def test_basic_pi(self):
        self.runscript('pi_archimedes.lar', dirname='../examples/basic/')
        assert(len(self.session.get_errors()) == 0)
        self.isNear("result", 3.14159265358979267, places=8)

    def test_basic_use_params(self):
        self.runscript('use_params.lar', dirname='../examples/basic/')
        assert(len(self.session.get_errors()) == 0)
        self.isNear("a",  0.76863, places=4)


if __name__ == '__main__':  # pragma: no cover
    for suite in (TestScripts,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=13).run(suite)
