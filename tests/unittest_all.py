#!/usr/bin/env python

from __future__ import with_statement, print_function
import os
import sys
import unittest
import optparse
import code
import tempfile
import pdb
import shutil
from contextlib import contextmanager

# fix for my broken cygwin test environment
# does not alter behavior in real DOS or in UNIX
if '' not in sys.path: 
    sys.path.insert(0, '')

import larch
from larch.interpreter import search_dirs
from larch.symboltable import GroupAlias
from unittest_larchEval import TestLarchEval, TestParse, TestBuiltins
from unittest_SymbolTable import TestSymbolTable
from unittest_util import *

#------------------------------------------------------------------------------

class TestGroupAlias(TestCase): 

    def test_create(self):
        '''construct a group from an object instance'''

        # get a useful backtrace
        # must restore recursion limit or later tests will be VERY odd
        with temp_set(sys.setrecursionlimit, 35, sys.getrecursionlimit()):
            ga = GroupAlias({})

#------------------------------------------------------------------------------

class TestLarchEnvErr(TestCase):
    def run_in_context(self):
        '''imports larch in context'''

        with open(larch.__file__.replace(".pyc", ".py")) as inf:
            exec inf in globals()

    def test_version_check(self):
        '''checks python version'''

        with temp_set((sys, 'version_info'), (2, 5)):
            self.assertRaises(EnvironmentError, self.run_in_context)
        with temp_set((sys, 'version_info'), (1, 5)):
            self.assertRaises(EnvironmentError, self.run_in_context)
        with temp_set((sys, 'version_info'), (2, 6)):
            # ValueError comes from trying relative syntax like
            #     from .closure import Closure 
            # outside a package. If it gets that far, the version check passed
            self.assertRaises(ValueError, self.run_in_context)

#------------------------------------------------------------------------------

class TestLarchImport(TestCase):

    def test_import(self):
        '''import entire python module'''

        self.li("import csv")

        self.assert_(hasattr(self.li.symtable, 'csv'))
        self.assert_(hasattr(self.li.symtable.csv, 'reader'))

    def test_import_error(self):
        '''import python module with error'''

        self.li("import sdflksj")

        self.assert_(self.li.error and 
                [e.expr for e in self.li.error 
                    if isinstance(e.py_exc[1], ImportError)])

    def test_import_as(self):
        '''import entire python module as other name'''

        self.li("import csv as foo")

        self.assert_(hasattr(self.li.symtable, 'foo'))
        self.assert_(hasattr(self.li.symtable.foo, 'reader'))

    def test_from_import(self):
        '''import python submodule'''

        self.li("from csv import reader")

        self.assert_(hasattr(self.li.symtable, 'reader'))
        self.assert_(hasattr(self.li.symtable.reader, '__call__'))

    def test_from_import_as(self):
        '''import python submodule as other name'''

        self.li("from csv import reader as r")

        self.assert_(hasattr(self.li.symtable, 'r'))
        self.assert_(hasattr(self.li.symtable.r, '__call__'))

    def test_larch_import(self):
        '''import entire larch module'''

        self.li("import l_random")

        self.assert_(hasattr(self.li.symtable, 'l_random'))
        self.assert_(hasattr(self.li.symtable.l_random, 'weibull'))
        # make sure we didn't take the Python random module
        self.assert_(not hasattr(self.li.symtable.l_random, 'gauss'))

    def test_larch_from_import(self):
        '''import larch submodule'''

        self.li('from l_random import weibull')

        self.assert_(hasattr(self.li.symtable, 'weibull'))
        self.assert_(hasattr(self.li.symtable.weibull, '__call__'))

    def test_larch_from_import_as(self):
        '''import larch submodule as other name'''

        self.li('from l_random import weibull as wb')

        self.assert_(hasattr(self.li.symtable, 'wb'))
        self.assert_(hasattr(self.li.symtable.wb, '__call__'))

    def test_larch_import_error(self):
        '''import larch module with error'''

        larchcode = '''
a =
'''
        with tempfile.NamedTemporaryFile(prefix='larch', delete=False) as outf:
            print(larchcode, file=outf)
            fname = outf.name

        self.assert_(self.li.eval_file(fname))

    def test_larch_import_first_only(self):
        '''import only first matching larch module'''

        fakedir = tempfile.mkdtemp()
        self.li.symtable._sys.path.append(fakedir)
        with open(os.path.join(fakedir, "l_random.lar"), "a") as outf:
            print("from os import path", file=outf)
        
        self.li('import l_random')

        self.assert_(not hasattr(self.li.symtable.l_random, 'path'))

    def do_reload_test(self, suffix, do_reload=True):
        '''reload module'''

        original, new = 1, 2

        tmpdir = tempfile.mkdtemp(prefix='larch')
        self.s._sys.path.insert(0, tmpdir)

        with tempfile.NamedTemporaryFile(suffix=suffix, dir=tmpdir,
                delete=False) as tmpmod:
            print('x = %i' % original, file=tmpmod)
            filename = tmpmod.name
            mod = os.path.basename(tmpmod.name).replace(suffix, '')

        self.eval('import %s' % mod)
        self.assert_(hasattr(self.s._sys.moduleGroup, mod))
        self.assert_(getattr(self.s._sys.moduleGroup, mod).x == original)

        with open(filename, 'w') as outf:
            print('x = %i' % new, file=outf)

        self.assert_(len(self.li.error) == 0)
        self.li.import_module(mod, do_reload=do_reload)
        self.assert_(len(self.li.error) == 0)
    
        expected = new if do_reload else original 
        self.assert_(getattr(self.s._sys.moduleGroup, mod).x == expected)

        os.unlink(filename)
        filename += 'c'
        if os.path.isfile(filename):
            os.unlink(filename)
        os.rmdir(tmpdir)

    def test_reload_larch(self):
        '''reload larch module'''

        self.do_reload_test('.lar')

    def test_reload_python(self):
        '''reload python module'''

        self.do_reload_test('.py')

    def test_no_reload_larch(self):
        '''lookup existing larch module'''

        self.do_reload_test('.lar', do_reload=False)

    def test_no_reload_python(self):
        '''lookup existing python module'''

        self.do_reload_test('.py', do_reload=False)

#------------------------------------------------------------------------------

class TestLarchSource(TestCase):
    '''interpreter can source larch code from strings, files, etc.'''

    def test_push_expr(self):
        '''push expression'''

        self.assert_(self.li.push("1"))

    def test_push_statement(self):
        '''push a statement'''

        self.assert_(self.li.push("a = 1"))

    def test_push_incomplete(self):
        '''push an incomplete construct'''

        self.assert_(not self.li.push("a = "))
        self.assert_(self.li.push("1"))
        #code.interact(local=locals())
        self.assert_(self.li.symtable.a == 1)

    def test_push_SyntaxError(self):
        '''push a syntax error'''

        self.assertRaises(SyntaxError, self.li.push, "1 = a")

    def test_push_buf_local(self):
        '''push buffer is local to larch interpreter instance'''

        li2 = larch.interpreter.Interpreter()
        self.li.push("a = ")

        self.assert_(not hasattr(li2, 'push_buf'))
    
    def test_push_no_indent(self):
        '''non-Pythonic indentation'''

        # FIXME can't handle non-Python indentation yet
        larchcode = '''a = 0
for i in arange(10):
a += i
#endfor'''.splitlines()

        self.assert_(self.li.push(larchcode[0]))
        self.assert_(not self.li.push(larchcode[1]))
        self.li.push(larchcode[2])
        #self.assert_(not self.li.push(larchcode[2]))
        self.assert_(self.li.push(larchcode[3]))

    def test_eval_file(self):
        '''eval a larch file'''

        # FIXME can't handle non-Python indentation yet
        larchcode = '''
a = 0
for i in arange(10):
    a += i
#endfor'''

        fname="testingtmp"
        with open(fname, "w") as outf:
            print(larchcode, file=outf)

        self.assert_(self.li.eval_file(fname))
        self.assert_(self.li.symtable.a == 45)

        os.unlink(fname)

#------------------------------------------------------------------------------

class TestSearchDirs(TestCase):
    def setUp(self):
        TestCase.setUp(self)

        self.dirname = tempfile.mkdtemp()
        self.haystack_name = "haystack"
        self.haystack = os.path.join(self.dirname, self.haystack_name)
        self.needle_name = "needle"
        self.needle = os.path.join(self.haystack, self.needle_name)

        self.PATH = [ os.path.join(self.dirname, str(subdir))
                for subdir in sum([[self.haystack_name], range(10)], []) ]
        map(os.mkdir, self.PATH)

        with open(self.needle, "w") as outf:
            print("You found me!", file=outf)

    def tearDown(self):
        shutil.rmtree(self.dirname)

    @property
    def first(self):

        return search_dirs(self.needle_name, self.PATH, only_first=True)

    @property
    def results(self):

        return search_dirs(self.needle_name, self.PATH, only_first=False)

    def test_one_existing(self):
        '''find one existing file'''

        self.assertListEqual(self.results, [self.needle])

    def test_multiple_existing(self):
        '''find all existing files'''

        other = os.path.join(self.PATH[5], self.needle_name)
        with open(other, "w") as outf:
            print("Found another!", file=outf)

        self.assertListEqual(self.results, [self.needle, other])

    def test_PATH_broken(self):
        '''skip nonexisting PATH elements'''

        os.rmdir(self.PATH[5])

        self.assertListEqual(self.results, [self.needle])

    def test_no_needle(self):
        '''return [] if no file exists'''

        os.unlink(self.needle)

        self.assert_(self.results == [])

    def test_one_existing_return_one(self):
        '''find first of one existing file'''

        self.assert_(self.first == self.needle)

    def test_multiple_existing_return_one(self):
        '''find first of all existing file'''

        other = os.path.join(self.PATH[0], self.needle_name)
        with open(other, "w") as outf:
            print("Found another!", file=outf)
        
        self.assert_(self.first == self.needle)

    def test_no_needle(self):
        '''return [] if no file exists'''

        os.unlink(self.needle)

        self.assert_(self.first is None)

#------------------------------------------------------------------------------

if __name__ == '__main__': # pragma: no cover

    def get_args():
        op = optparse.OptionParser()
        op.add_option('-v', '--verbose', action='count', dest="verbosity")
        options, args = op.parse_args()
        return dict(verbosity=options.verbosity, tests=args)

    def run_tests(verbosity=0, tests=[]):
        tests = [ unittest.TestLoader().loadTestsFromTestCase(v) 
                for k,v in globals().items() 
                if k.startswith("Test") and (tests == [] or k in tests)]
        unittest.TextTestRunner(verbosity=verbosity).run(unittest.TestSuite(tests))

    run_tests(**get_args())
