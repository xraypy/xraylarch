#!/usr/bin/env python
"""
Base TestCase for larch unit tests
"""
import unittest
import time
import os
import numpy as np
from tempfile import NamedTemporaryFile
from larch import Interpreter

class TestCase(unittest.TestCase):
    '''testing of larch'''

    def setUp(self):
        self.session = Interpreter()
        self.symtable = self.session.symtable
        self.set_stdout()

    def set_stdout(self):
        self.stdout = NamedTemporaryFile('w', delete=False,
                                         prefix='larch_test_')
        self.session.writer = self.stdout

    def read_stdout(self):
        self.stdout.close()
        time.sleep(0.1)
        fname = self.stdout.name
        with open(self.stdout.name) as inp:
            out = inp.read()
        self.set_stdout()
        os.unlink(fname)
        return out

    def tearDown(self):
        if not self.stdout.closed:
            self.stdout.close()
        try:
            os.unlink(self.stdout.name)
        except:
            pass

    def getSym(self, sym):
        return self.symtable.get_symbol(sym, create=False)

    def isValue(self, sym, val):
        '''assert that a symboltable symbol has a particular value'''
        testval = self.getSym(sym)
        if isinstance(val, np.ndarray):
            return self.assertTrue(np.all(testval == val))
        else:
            return self.assertTrue(testval == val)

    def isNear(self, expr, val, places=7):
        '''assert that a symboltable symbol is near a particular value'''
        testval = self.session(expr)
        if isinstance(val, np.ndarray):
            for x, y in zip(testval, val):
                self.assertAlmostEqual(x, y, places=places)
        else:
            return self.assertAlmostEqual(testval, val, places=places)

    def isTrue(self, expr):
        '''assert that an expression evaluates to True'''
        testval = self.session(expr)
        if isinstance(testval, np.ndarray):
            testval = np.all(testval)
        return self.assertTrue(testval)

    def isFalse(self, expr):
        '''assert that an expression evaluates to False'''
        testval = self.session(expr)
        if isinstance(testval, np.ndarray):
            testval = np.all(testval)
        return self.assertFalse(testval)
