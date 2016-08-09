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

def nullfunction(*args, **kwargs):
    pass

class LarchSession(object):
    def __init__(self):
        self._larch = Interpreter()
        self.input  = InputText(prompt='test>', _larch=self._larch)
        self.symtable = self._larch.symtable
        self.symtable.set_symbol('_plotter.newplot',  nullfunction)
        self.symtable.set_symbol('_plotter.plot',     nullfunction)
        self.symtable.set_symbol('_plotter.oplot',    nullfunction)
        self.symtable.set_symbol('_plotter.imshow',   nullfunction)
        self.symtable.set_symbol('_plotter.plot_text',   nullfunction)
        self.symtable.set_symbol('_plotter.plot_arrow',   nullfunction)
        self.symtable.set_symbol('_plotter.xrfplot',   nullfunction)

        self._larch.writer = sys.stdout = open('_stdout_', 'w')

    def read_stdout(self):
        sys.stdout.flush()
        time.sleep(0.1)
        with open(sys.stdout.name) as inp:
            out = inp.read()
        sys.stdout.close()
        self._larch.writer = sys.stdout = open('_stdout_', 'w')
        return out

    def run(self, text):
        self.input.put(text)
        ret = None
        buff = []
        while len(self.input) > 0:
            block, fname, lineno = self.input.get()
            buff.append(block)
            if not self.input.complete:
                continue
            ret = self._larch.eval("\n".join(buff), fname=fname, lineno=lineno)
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

    def runscript(self, fname, dirname='.'):
        origdir = os.path.abspath(os.getcwd())
        dirname = os.path.abspath(dirname)
        os.chdir(dirname)
        fh = open(fname, 'r')
        text = fh.read()
        fh.close()
        self.session.run(text)
        os.chdir(origdir)

    def trytext(self, text):
        ret = self.session.run(text)
        out = self.session.read_stdout()
        err = self.session.get_errors()
        return out, err

    def tearDown(self):
        sys.stdout.close()
        try:
            os.unlink(sys.stdout.name)
        except:
            pass

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
