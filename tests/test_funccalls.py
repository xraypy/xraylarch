#!/usr/bin/env python
""" Larch Tests Version 1 """
import unittest
import time
import ast
import numpy as np
from sys import version_info

from utils import TestCase
from larch import Interpreter

class TestEval(TestCase):
    '''testing of ast evaluation'''

    def test_function1(self):
        "test function definition and running"
        self.trytext("""
def fcn(x, scale=2):
    'test function'
    out = sqrt(x)
    if scale > 1:
        out = out * scale
    endif
    return out
enddef
""")
        self.trytext("a = fcn(4, scale=9)")
        self.isValue("a", 18)
        self.NoExceptionRaised()

        self.trytext("a = fcn(9, scale=0)")
        self.isValue("a", 3)
        self.NoExceptionRaised()

        out, err = self.trytext("print(fcn)")
        self.NoExceptionRaised()
        out = out.split('\n')
        self.assertTrue(out[0].startswith('<Procedure fcn'))

        out, err = self.trytext("a = fcn()")
        self.ExceptionRaised()
        errtype, errmsg = err[0].get_error()

        errlines = errmsg.split('\n')

        self.assertTrue(errtype == 'TypeError')

        out, err = self.trytext("a = fcn(x, bogus=3)")
        self.ExceptionRaised()
        errtype, errmsg = err[0].get_error()
        errmsgs = errmsg.split('\n')
        self.assertTrue(errtype == 'NameError')

    def test_function_vararg(self):
        "test function with var args"
        self.trytext("""
def fcn(*args):
    'test varargs function'
    out = 0
    for i in args:
        out = out + i*i
    endfor
    return out
enddef
""")
        self.NoExceptionRaised()
        self.trytext("o = fcn(1,2,3)")
        self.NoExceptionRaised()
        self.isValue('o', 14)
        out, err = self.trytext("print(fcn)")
        out = out.split('\n')
        self.assertTrue(out[0].startswith('<Procedure fcn'))

    def test_function_kwargs(self):
        "test function with kw args, no **kws"
        self.trytext("""
def fcn(square=False, x=0, y=0, z=0, t=0):
    'test varargs function'
    out = 0
    for i in (x, y, z, t):
        if square:
            out = out + i*i
        else:
            out = out + i
        endif
    endfor
    return out
enddef
""")
        self.NoExceptionRaised()
        out, err = self.trytext("print(fcn)")
        self.NoExceptionRaised()
        out = out.split('\n')
        self.assertTrue(out[0].startswith('<Procedure fcn'))

        self.trytext("o = fcn(x=1, y=2, z=3, square=False)")
        self.NoExceptionRaised()
        self.isValue('o', 6)

        self.trytext("o = fcn(x=1, y=2, z=3, square=True)")
        self.NoExceptionRaised()
        self.isValue('o', 14)

        self.trytext("o = fcn(x=1, y=2, z=3, t=-2)")
        self.NoExceptionRaised()
        self.isValue('o', 4)

        out, err = self.trytext("o = fcn(x=1, y=2, z=3, t=-12, s=1)")
        self.ExceptionRaised()
        errtype, errmsg = err[0].get_error()
        self.assertTrue(errtype == 'TypeError')
        self.assertTrue('extra keyword arg' in errmsg)

    def test_function_kwargs1(self):
        "test function with **kws arg"
        self.trytext("""
def fcn(square=False, **kws):
    'test varargs function'
    out = 0
    for i in kws.values():
        if square:
            out = out + i*i
        else:
            out = out + i
        endif
    endfor
    return out
enddef
""")

        out, err = self.trytext("print(fcn)")
        out = out.split('\n')
        self.assertTrue(out[0].startswith('<Procedure fcn'))
        self.trytext("o = fcn(x=1, y=2, z=3, square=False)")
        self.isValue('o', 6)
        self.NoExceptionRaised()

        self.trytext("o = fcn(x=1, y=2, z=3, square=True)")
        self.isValue('o', 14)
        self.NoExceptionRaised()

    def test_function_kwargs2(self):
        "test function with positional and **kws args"
        self.trytext("""
def fcn(x, y, **kws):  # end of line comment
    'test function'
    if 'scale' in kws:  # optional scale
        scale = kws['scale']
    else:
        scale = 1
    #endif
    return scale*(x + y**2)
#enddef
""")
        out, err = self.trytext("print(fcn)")
        self.NoExceptionRaised()
        out = out.split('\n')
        self.assertTrue(out[0].startswith('<Procedure fcn'))

        self.trytext("o = -1")
        self.NoExceptionRaised()
        self.trytext("o = fcn(2, 1)")
        self.isValue('o', 3)
        self.NoExceptionRaised()

        self.trytext("o = fcn(x=1, y=2)")
        self.isValue('o', 5)
        self.NoExceptionRaised()

        self.trytext("o = fcn(y=2, x=7)")
        self.isValue('o', 11)
        self.NoExceptionRaised()

        self.trytext("o = fcn(1, y=2)")
        self.isValue('o', 5)
        self.NoExceptionRaised()

        self.trytext("o = fcn(1, y=2, scale=0)")
        self.isValue('o', 0)
        self.NoExceptionRaised()

        self.trytext("o = fcn(1, y=2, scale=2)")
        self.isValue('o', 10)
        self.NoExceptionRaised()

        self.trytext("o = fcn(1, y=2, unused_opt=1)")
        self.isValue('o', 5)
        self.NoExceptionRaised()

        out, err = self.trytext("o = fcn(1, x=2)")
        self.ExceptionRaised()
        errtype, errmsg = err[0].get_error()
        self.assertTrue(errtype == 'TypeError')


if __name__ == '__main__':  # pragma: no cover
    for suite in (TestEval,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=2).run(suite)
