#!/usr/bin/env python
"""
Base TestCase for larch unit tests
"""
import unittest
import time
import os
import numpy as np
from tempfile import NamedTemporaryFile
from larch import Interpreter, InputText

class LarchSession(object):
    def __init__(self):
        self._larch = Interpreter()
        self.input  = InputText(prompt='test>', _larch=self._larch)
        self.symtable = self._larch.symtable

    def run(self, text):
        self.input.put(text)
        ret = None
        while len(self.input) > 0:
            block, fname, lineno = self.input.get()
            if len(block) <= 0:
                continue
            ret = self._larch.eval(block, fname=fname, lineno=lineno)
            if self._larch.error:
                break
        return ret


    def get_errors(self):
        return self._larch.error

    def get_symbol(self, name):
        return self.symtable.get_symbol(name, create=False)

class TestCase(unittest.TestCase):
    '''testing of larch'''
    def setUp(self):
        self.session = LarchSession()
        self.symtable = self.session.symtable
        self.set_stdout()

    def set_stdout(self):
        self.stdout = NamedTemporaryFile('w', delete=False,
                                    prefix='larch_test_')
        self.session._larch.writer = self.stdout

    def read_stdout(self):
        self.stdout.flush()
        self.stdout.close()
        time.sleep(0.25)
        fname = self.stdout.name
        with open(self.stdout.name) as inp:
            out = inp.read()
        self.set_stdout()
        # os.unlink(fname)
        return out

    def trytext(self, text):
        ret = self.session.run(text)
        out = self.read_stdout()
        err = self.session.get_errors()
        return out, err

    def tearDown(self):
        if not self.stdout.closed:
            self.stdout.close()
        #try:
        #    os.unlink(self.stdout.name)
        #except:
        #    pass


    def getSym(self, sym):
        return self.session.get_symbol(sym)

    def isValue(self, sym, val):
        '''assert that a symboltable symbol has a particular value'''
        testval = self.getSym(sym)
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

