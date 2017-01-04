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
    '''test read_ascii() for all example xafsdata'''
    def test_read_ascii(self):
        # self.symtable.set_symbol('testdir',  os.getcwd())
        self.runscript('read_ascii.lar', dirname='larch_scripts')
        assert(len(self.session.get_errors()) == 0)

        actual = self.session.get_symbol('results')
        expected = self.session.get_symbol('expected')

        for fname, ncol, nrow, labels in expected:
            acol, arow, alabs = actual[fname]
            assert(acol == ncol)
            assert(arow == nrow)
            assert(alabs == labels)

if __name__ == '__main__':  # pragma: no cover
    for suite in (TestScripts,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=13).run(suite)
