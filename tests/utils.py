#!/usr/bin/env python
"""

Basic unit testing utilities for larch

"""
import unittest
import time
import os
import sys
import numpy as np
from tempfile import NamedTemporaryFile
from larch import Interpreter, InputText

from six.moves import StringIO

def nullfunction(*args, **kwargs):
    pass


class LarchSession(object):
    def __init__(self):
        self._larch = Interpreter()
        self.input  = self._larch.input
        #  InputText(prompt='test>', _larch=self._larch)
        self.symtable = self._larch.symtable
        setsym = self.symtable.set_symbol
        setsym('testdir',  os.getcwd())
        setsym('_plotter.no_plotting', True)
        setsym('_plotter.get_display',  nullfunction)
        self.set_stdout()

    def set_stdout(self, fname='_stdout_'):
        # self._outfile = os.path.abspath(fname)
        # self._larch.writer = open(self._outfile, 'w')
        self._larch.writer = StringIO()

    def read_stdout(self):
        self._larch.writer.flush()
        self._larch.writer.seek(0)
        t0 = time.time()
        time.sleep(0.01)

        out = self._larch.writer.read()
        self._larch.writer.close()
        self.set_stdout()
        return out

    def run(self, text):
        return self._larch.eval(text, fname='test', lineno=0)

    def get_errors(self):
        return self._larch.error

    def get_symbol(self, name):
        return self.symtable.get_symbol(name, create=False)

class TestCase(unittest.TestCase):
    '''testing of larch'''
    def setUp(self):
        self.session = LarchSession()
        self.symtable = self.session.symtable

    def runscript(self, fname, dirname='.'):
        origdir = os.path.abspath(os.getcwd())
        dirname = os.path.abspath(dirname)
        os.chdir(dirname)
        with open(fname, 'r') as fh:
            text = fh.read()
        self.session.run(text)
        os.chdir(origdir)

    def trytext(self, text):
        self.session.set_stdout()
        ret = self.session.run(text)
        out = self.session.read_stdout()
        err = self.session.get_errors()
        return out, err

    def tearDown(self):
        pass

    def getSym(self, sym):
        return self.session.get_symbol(sym)

    def isValue(self, sym, val):
        '''assert that a symboltable symbol has a particular value'''
        testval = self.session.get_symbol(sym)
        if isinstance(val, np.ndarray):
            return self.assertTrue(np.all(testval == val))
        else:
            return self.assertTrue(testval == val)

    def isNear(self, expr, val, places=7):
        '''assert that a symboltable symbol is near a particular value'''
        testval = self.session.run(expr)
        if isinstance(val, np.ndarray):
            for x, y in zip(testval, val):
                self.assertAlmostEqual(x, y, places=places)
        else:
            return self.assertAlmostEqual(testval, val, places=places)

    def isTrue(self, expr):
        '''assert that an expression evaluates to True'''
        testval = self.session.run(expr)
        if isinstance(testval, np.ndarray):
            testval = np.all(testval)
        return self.assertTrue(testval)

    def isFalse(self, expr):
        '''assert that an expression evaluates to False'''
        testval = self.session.run(expr)
        if isinstance(testval, np.ndarray):
            testval = np.all(testval)
        return self.assertFalse(testval)

    def ExceptionRaised(self):
        return self.assertTrue(len(self.session.get_errors()) > 0)

    def NoExceptionRaised(self):
        return self.assertTrue(len(self.session.get_errors()) == 0)
