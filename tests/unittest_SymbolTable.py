#!/usr/bin/env python

import unittest
import larch
import code
import numpy
from unittest_util import *
from larch.symboltable import isgroup, Group

class TestSymbolTable(TestCase):

    default_search_groups = ['_sys', '_builtin', '_math']

    def setUp(self):
        TestCase.setUp(self)
        self.s = larch.SymbolTable()
        self.g = self.s.create_group(name='g0', x=1, y=2)
        self.s.set_symbol(self.g.__name__, self.g)

    def test_searchGroups(self):
        '''search groups'''
        for g in self.default_search_groups:
            self.assertTrue(hasattr(self.s, g))
        self.assertTrue(self.default_search_groups == 
                self.s.get_symbol('_sys.searchGroups'))

    def test_getSymbol(self):
        '''get symbol from table'''
        self.assertTrue(self.s.g0 == self.s.get_symbol('g0'))

    def test_addTempGroup(self):
        '''not all groups in search'''
        self.assertFalse(self.g.__name__ in self.s._sys.searchGroups)
        self.assertTrue(self.g.__name__ in self.s._subgroups())

    def test_make_group(self):
        '''make group'''
        self.assertTrue(larch.symboltable.isgroup(self.g))
        self.assertTrue(self.g.__name__ == 'g0')
        self.assertTrue(self.g.x == 1 and self.g.y == 2)

    def test_make_group_with_attr(self):
        '''make group with attr'''
        self.s.new_group('g1', s='a string', en=722)
        self.assertTrue(self.s.g1.s == 'a string')
        self.assertTrue(self.s.g1.en == 722)

    def test_set_symbol(self):
        '''set symbol in table'''
        for k,v in dict(int_=1, float_=1.0, str_='value of b', 
                dict_={'yes': 1, 'no': 0}, tuple_=(1,2,3),
                func_=lambda x: 1).items():
            self.s.set_symbol('_main.%s' % k, value=v)
            self.assertTrue(self.s.get_symbol('_main.%s' % k) == v)

        # do this separately because list == array is undefined
        self.s.set_symbol('_main.list_', value=[1, 2, 3])
        self.assertListEqual([1, 2, 3], self.s.list_)

    def test_set_nested_symbol(self):
        '''set nested symbol in table'''

        self.s.set_symbol('_main.foo.bar.baz', value=1)
        self.assert_(hasattr(self.s._main, 'foo'))
        self.assert_(isgroup(getattr(self.s._main, 'foo')))
        self.assert_(hasattr(self.s._main.foo, 'bar'))
        self.assert_(isgroup(getattr(self.s._main.foo, 'bar')))
        self.assert_(hasattr(self.s._main.foo.bar, 'baz'))
        self.assert_(self.s._main.foo.bar.baz == 1)

    def test_set_symbol_as_array(self):
        '''convert to array and set symbol'''

        self.s.set_symbol('_main.foo', range(10))
        self.assert_(isinstance(self.s._main.foo, numpy.ndarray))
        self.assertListEqual(self.s._main.foo, range(10))

    def test_set_symbol_in_group(self):
        '''set symbol into group'''

        self.s.set_symbol('g', Group(name='g'))
        self.s.set_symbol('foo', 1, group='g')
        self.assert_(hasattr(self.s.get_symbol('g'), 'foo'))
        self.assert_(self.s.get_symbol('g').foo == 1)

        

if __name__ == '__main__': # pragma: no cover
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSymbolTable)
    unittest.TextTestRunner(verbosity=2).run(suite)
