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
    '''testing of examples/xray'''
    def test1_mu_elam(self):
        self.runscript('get_mu_tables.lar', dirname=base_dir / 'examples' / 'xray')
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("len(mu1) == 401")
        self.isTrue("min(mu1) < 20")

    def test2_mu_elam(self):
        self.session.run("zn_iz = atomic_number('zn')")
        self.session.run("zn_mass = atomic_mass('zn')")
        assert(len(self.session.get_errors()) == 0)
        self.isTrue("zn_iz == 30")
        self.isTrue("zn_mass > 60.")


if __name__ == '__main__':  # pragma: no cover
    for suite in (TestScripts,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=3).run(suite)
