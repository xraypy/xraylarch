#!/usr/bin/env python
""" Larch Tests Version 1 """
import unittest
import time
import ast
import numpy as np
from sys import version_info

from ut_base import TestCase
from larch import Interpreter

class TestEval(TestCase):
    '''testing of ast evaluation'''

    def test_function1(self):
        "test function definition and running"
        self.session("""
def fcn(x, scale=2):
    'test function'
    out = sqrt(x)
    if scale > 1:
        out = out * scale
    return out
""")
        self.session("a = fcn(4, scale=9)")
        self.isValue("a", 18)
        self.session("a = fcn(9, scale=0)")
        self.isValue("a", 3)

        self.session("print(fcn)")
        out = self.read_stdout()
        out = out.split('\n')

        self.assert_(out[0].startswith('<Procedure fcn(x, scale='))
        self.assert_('test func' in out[1])

    def test_function2(self):
        "test errors calling function -- too few args"
        self.session("""
def fcn(x, scale=2):
    'test function'
    out = sqrt(x)
    if scale > 1:
        out = out * scale
    return out
""")
        
        self.session("a = fcn()")
        errtype, errmsg = self.session.error[0].get_error()
        
        errlines = errmsg.split('\n')
        
        self.assertTrue(errtype == 'TypeError')
        self.assertTrue('not enough arg' in errmsg)

    def test_function3(self):
        "test errors calling function -- unknown key arg"
        self.session("""
def fcn(x, scale=2):
    'test function'
    out = sqrt(x)
    if scale > 1:
        out = out * scale
    return out
""")
        self.session("a = fcn(x)")
        errtype, errmsg = self.session.error[0].get_error()
        errlines = errmsg.split('\n')
        self.assertTrue(errtype == 'NameError')
        # print errlines

        self.session.error = []
        
        self.session("a = fcn(3, bogus=33)")
        errtype, errmsg = self.session.error[0].get_error()
        errlines = errmsg.split('\n')
        self.assertTrue(errtype == 'TypeError')
        # print errlines

    def test_function_vararg(self):
        "test function with var args"
        self.session("""
def fcn(*args):
    'test varargs function'
    out = 0
    for i in args:
        out = out + i*i
    return out
""")
        self.session("o = fcn(1,2,3)")
        self.isValue('o', 14)
        self.session("print(fcn)")
        out = self.read_stdout()
        out = out.split('\n')
        self.assert_(out[0].startswith('<Procedure fcn('))

    def test_function_kwargs(self):
        "test function with kw args, no **kws"
        self.session("""
def fcn(square=False, x=0, y=0, z=0, t=0):
    'test varargs function'
    out = 0
    for i in (x, y, z, t):
        if square:
            out = out + i*i
        else:
            out = out + i
    return out
""")
        self.session("print(fcn)")
        out = self.read_stdout()
        out = out.split('\n')
        self.assert_(out[0].startswith('<Procedure fcn(square'))

        self.session("o = fcn(x=1, y=2, z=3, square=False)")
        self.isValue('o', 6)

        self.session("o = fcn(x=1, y=2, z=3, square=True)")
        self.isValue('o', 14)

        self.session("o = fcn(x=1, y=2, z=3, t=-2)")

        self.isValue('o', 4)

        self.session("o = fcn(x=1, y=2, z=3, t=-12, s=1)")
        errtype, errmsg = self.session.error[0].get_error()
        self.assertTrue(errtype == 'TypeError')
        errlines = errmsg.split('\n')
        self.assertTrue('keyword arg' in errmsg)

    def test_function_kwargs1(self):
        "test function with **kws arg"
        self.session("""
def fcn(square=False, **kws):
    'test varargs function'
    out = 0
    for i in kws.values():
        if square:
            out = out + i*i
        else:
            out = out + i
    return out
""")
        self.session("print(fcn)")
        out = self.read_stdout()
        out = out.split('\n')
        self.assert_(out[0].startswith('<Procedure fcn(square'))

        self.session("o = fcn(x=1, y=2, z=3, square=False)")
        self.isValue('o', 6)

        self.session("o = fcn(x=1, y=2, z=3, square=True)")
        self.isValue('o', 14)


    def test_function_kwargs2(self):
        "test function with positional and **kws args"

        self.session("""
def fcn(x, y):
    'test function'
    return x + y**2

""")
        self.session("print(fcn)")
        out = self.read_stdout()
        out = out.split('\n')
        self.assert_(out[0].startswith('<Procedure fcn(x,'))

        self.session("o = -1")
        self.session("o = fcn(2, 1)")
        self.isValue('o', 3)

        self.session("xout1 = fcn(x=1, y=2)")
        self.session("xout2 = fcn(x=2.2, y=3)")

        if len(self.session.error) > 0:
            errtype, errmsg = self.session.error[0].get_error()
        
        self.isValue('xout1', 5)
        self.isNear('xout2', 11.2)

        self.session("o = fcn(y=2, x=7)")
        self.isValue('o', 11)

        self.session("o = fcn(1, y=2)")
        self.isValue('o', 5)

        self.session("o = fcn(1, x=2)")
        errtype, errmsg = self.session.error[0].get_error()
        self.assertTrue(errtype == 'TypeError')

    def xtest_astdump(self):
        "test ast parsing and dumping"
        astnode = self.session.parse('x = 1')
        self.assertTrue(isinstance(astnode, ast.Module))
        self.assertTrue(isinstance(astnode.body[0], ast.Assign))
        self.assertTrue(isinstance(astnode.body[0].targets[0], ast.Name))
        self.assertTrue(isinstance(astnode.body[0].value, ast.Num))
        self.assertTrue(astnode.body[0].targets[0].id == 'x')
        self.assertTrue(astnode.body[0].value.n == 1)
        dumped = self.session.dump(astnode.body[0])
        self.assertTrue(dumped.startswith('Assign'))

if __name__ == '__main__':  # pragma: no cover
    for suite in (TestEval,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=2).run(suite)
