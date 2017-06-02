#!/usr/bin/env python
""" Tests of Larch Scripts  """
import unittest
import time
import ast
import numpy as np
import os
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

    def test_basic_localnames(self):
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

    def test_nested_runfiles(self):
        origdir = os.path.abspath(os.getcwd())
        dirname = os.path.abspath('larch_scripts')
        os.chdir(dirname)
        out, err = self.trytext("run('nested_outer.lar')")

        os.chdir(origdir)
        out = out.split('\n')
        assert(len(out) > 4)
        assert('before nested_inner.lar' in out[0])
        assert('in nested_inner.lar' in out[1])
        assert('in nested_deep.lar' in out[2])
        assert('in nested_inner.lar, after nested_deep' in out[3])
        assert('in nested_outer.lar, after nested_inner' in out[4])
        self.isNear("deep_x",  5.0, places=2)



    def test_runfit(self):
        origdir = os.path.abspath(os.getcwd())
        dirname = os.path.abspath('larch_scripts')
        os.chdir(dirname)

        out, err = self.trytext("run('fit_constraint.lar')")

        os.chdir(origdir)
        self.isTrue('out.nfev > 30')
        self.isTrue('out.nfev < 70')
        self.isNear('params.amp1.value', 6.05, places=2)
        self.isNear('params.amp2.value', 2.02, places=2)
        self.isNear('params.cen1.value', 3.01, places=2)
        self.isNear('params.cen1.stderr', 0.0073, places=2)
        self.isNear('out.chi_square', 8.4,places=2)


if __name__ == '__main__':  # pragma: no cover
    for suite in (TestScripts,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=13).run(suite)
