#!/usr/bin/env python
""" Larch Tests:
  Calling Functions from Plugins
"""
import unittest
import time
import ast
import numpy as np
from sys import version_info

from ut_base import TestCase
import larch
import sys
larch.site_config.plugins_path.insert(0, '.')


class TestPlugins(TestCase):
    '''testing plugins'''

    def setUp(self):
        self.session = larch.Interpreter()
        self.session("add_plugin('test_larch_plugin')")
        self.session("_sys.SearchGroups.insert(0, '_tests')")
        self.symtable = self.session.symtable
        self.set_stdout()
        
    def test0(self):
        "test function without arguments"
        self.session("a = _tests.fcn0()")
        self.isValue('a', True)
        self.NoExceptionRaised()

        self.session("b = _tests.fcn0('a')")
        self.ExceptionRaised()

    def test1(self):
        "test function with 1 argument"
        self.session("a = _tests.fcn1(3)")
        self.isValue('a', 3)
        self.NoExceptionRaised()
        self.session("a = _tests.fcn1(['a'])")
        self.isValue('a', ['a'])
        self.NoExceptionRaised()

        self.session("a = _tests.fcn1()")
        self.ExceptionRaised()        

        self.session("a = _tests.fcn1(1, 2, 3)")
        print self.session.error[0].msg
        self.ExceptionRaised()
        self.session("a = _tests.fcn1(1, scale=3)")
        print self.session.error[0].msg
        self.ExceptionRaised()

    def test2(self):
        "test function with 2 arguments 2*x+y"
        self.session("a = _tests.add2(3, 5)")
        self.isValue('a', 11)
        self.NoExceptionRaised()

        self.session("a = _tests.add2(y=0, x=8)")
        self.isValue('a', 16)
        self.NoExceptionRaised()

        self.session("a = _tests.add2('hello', 'world')")
        self.isValue('a', 'hellohelloworld')
        self.NoExceptionRaised()

    def test3(self):
        "test function with 2 arguments and keyword argument"
        self.session("a = _tests.add_scale(3, 5)")
        self.isValue('a', 11)
        self.NoExceptionRaised()

        self.session("a = _tests.add_scale(3, 5, scale=2)")
        self.isValue('a', 22)
        self.NoExceptionRaised()

        self.session("a = _tests.add_scale(3, 5, scale=0)")
        self.isValue('a', 0)
        self.NoExceptionRaised()

        self.session("a = _tests.add_scale(3, 5, 3)")
        self.isValue('a', 33)
        self.NoExceptionRaised()

        self.session("a = _tests.add_scale(y=1, scale=10, x=1)")
        self.isValue('a', 30)
        self.NoExceptionRaised()

        self.session("a = _tests.add_scale(scale=10, y=1, x=1)")
        self.isValue('a', 30)
        self.NoExceptionRaised()

        self.session("a = _tests.add_scale('a', 'b', scale=3)")
        self.isValue('a', 'aabaabaab')
        self.NoExceptionRaised()

        self.session("a = _tests.add_scale(scale=10, y=1, x=1)")
        self.isValue('a', 30)
        self.NoExceptionRaised()

        self.session("a = _tests.add_scale(x=1, x=2)")
        self.ExceptionRaised()

        self.session("a = _tests.add_scale(y=1, y=2)")
        self.ExceptionRaised()

        self.session("a = _tests.add_scale(1, 2, 3, 4)")
        self.ExceptionRaised()        

    def test4(self):
        "test function with _larch keyword..."
        self.session("b = _tests.f1_larch(5)")
        self.isValue('b', 10)
        self.NoExceptionRaised()

        self.session("c = _tests.f1_larch(5, _larch=None)")
        self.isValue('c', 5)
        self.NoExceptionRaised()

    def test5(self):
        "test function with ** kwargs"
        self.session("a = _tests.f1_kwargs(4)")
        self.isValue('a', 8)
        self.NoExceptionRaised()

        self.session("a = _tests.f1_kwargs(6)")
        self.isValue('a', 12)
        self.NoExceptionRaised()

        self.session("b = _tests.f1_kwargs(False, foo=0, scale=1)")
        self.isValue('b', 3)
        self.NoExceptionRaised()

        # print '--> ', self.getSym('b')

        #self.isValue('b', {'x':1})
        #self.NoExceptionRaised()


if __name__ == '__main__':  # pragma: no cover
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPlugins)
    unittest.TextTestRunner(verbosity=2).run(suite)
