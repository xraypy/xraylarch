#!/usr/bin/env python

from __future__ import print_function
import unittest
import code
import ast
import numpy
import os
import pdb
import tempfile

import larch
from larch.symboltable import isgroup
from unittest_util import *

class TestLarchEval(TestCase):
    '''testing evaluation of larch code'''

    default_search_groups = ['_sys', '_builtin', '_math']

    def test_while(self):
        '''while loops'''

        self.eval('''
n=0
while n < 8:
    n += 1
''')

        self.assertTrue(self.li.symtable.n == 8)

    def test_for(self):
        '''for loops'''

        self.eval('''
n=0
for i in arange(10):
    n += i
''')

        self.assertTrue(self.li.symtable.n == 45)

    def test_print(self):
        '''print a string'''

        self.eval("print 1")

        self.stdout.close()
        
        with open(self.stdout.name) as inf:
            self.assert_(inf.read() == '1\n')

    def test_cmp(self):
        '''numeric comparisons'''

        self.true("3 == 3")
        self.true("3.0 == 3")
        self.true("3.0 == 3.0")
        self.true("3 != 4")
        self.true("3.0 != 4")
        self.true("3 >= 1")
        self.true("3 >= 3")
        self.true("3 <= 3")
        self.true("3 <= 5")
        self.true("3 < 5")
        self.true("5 > 3")

        self.false("3 == 4")
        self.false("3 > 5")
        self.false("5 < 3")

    def test_bool(self):
        '''boolean logic'''

        self.li('''
yes = True
no = False
nottrue = False
a = arange(7)''')

        self.true("yes")
        self.false("no")
        self.false("nottrue")
        self.false("yes and no or nottrue")
        self.false("yes and (no or nottrue)")
        self.false("(yes and no) or nottrue")
        self.true("yes or no and nottrue")
        self.true("yes or (no and nottrue)")
        self.false("(yes or no) and nottrue")
        self.true("yes or not no")
        self.true("(yes or no)")
        self.false("not (yes or yes)")
        self.false("not (yes or no)")
        self.false("not (no or yes)")
        self.true("not no or yes")
        self.false("not yes")
        self.true("not no")

    def test_bool_coerce(self):
        '''coercion to boolean'''

        self.true("1")
        self.false("0")

        self.true("'1'")
        self.false("''")

        self.true("[1]")
        self.false("[]")

        self.true("(1)")
        self.true("(0,)")
        self.false("()")

        self.true("dict(y=1)")
        self.false("{}")

    def test_assign(self):
        '''variables assignment?'''
        self.li('n = 5')

        self.assertTrue(self.li.symtable.n == 5)

    def test_function_call(self):
        '''built-in functions'''
        self.li('n = [11]')

        self.assertTrue(isinstance(self.n(), numpy.ndarray))
        self.assertTrue(len(self.li.symtable.n) == len([11]))
        self.assertTrue(self.li.symtable.n[0] == 11)

    def test_convenience_imports(self):
        '''convenience imports

        imported functions like math.sqrt into the top level?'''

        self.li('n = sqrt(4)')

        self.assertTrue(self.li.symtable.n == 2)

class TestParse(TestCase):
    '''testing parsing of larch code to ASTs'''

    def test_while(self):
        '''while loops'''

        larchcode = 'n = 5'

        self.assertTrue(ast.dump(ast.parse(larchcode)) == 
                ast.dump(self.li.compile(larchcode)))

class TestBuiltins(TestCase):

    # These probably aren't unit tests any more, but going through the eval
    # was the easier way to test these functions, even if we are now relying
    # on the interpretation layer to call the builtins correctly.

    def test_group(self):
        '''group builtin'''

        self.eval('g = group()')
        self.assert_(isgroup(self.li.symtable.g))

    def test_showgroup(self):
        '''showgroup builtin'''

        self.eval('g = group()')
        self.assert_(self.eval('showgroup(g)') == self.li.symtable.show_group(self.li.symtable.g))

    def test_showgroup_defarg(self):
        '''showgroup builtin default argument'''

        self.eval('g = group()')
        self.assert_(self.eval('showgroup()') == self.s.show_group(self.s._main))

    def test_run(self):
        '''run builtin'''

        self.eval(r'run("larch/modules/l_random.lar")')
        #pdb.set_trace()
        self.assert_(hasattr(self.li.symtable, 'laplace'))

    def test_run_nonexistent(self):
        '''run builting with nonexistent file'''

        self.eval(r'run("nonexistent_lasdfjsdl")')
        self.assert_("No such file" in self.li.error[0].get_error()[1])

    def test_which(self):
        '''which builtin'''

        self.eval('g = group()')
        self.eval('which("g")')
        self.stdout.close()
        with open(self.stdout.name) as outf:
            self.assert_(str(self.s.get_parent('g')) in outf.read())

    def test_reload_larch(self):
        '''reload builtin, larch'''

        self.eval('import l_random')
        delattr(self.s.l_random, 'bytes')
        self.assert_(not hasattr(self.s.l_random, 'bytes'))
        self.eval('reload(l_random)')
        self.assert_(hasattr(self.s.l_random, 'bytes'))

    def test_reload_python(self):
        '''reload builtin, python'''

        from larch.builtins import _reload as reload_func
        log = []
        self.li.import_module = call_logger(log)
        reload_func('csv', self.li)
        self.assert_(log[0] == (('csv',), {'do_reload': True}))

    def test_ls(self):
        '''ls builtin'''

        self.assertListEqual(self.eval("ls()"), os.listdir(os.getcwd()))

    def test_ls_other(self):
        '''ls builtin, non-working directory'''

        dirname = self.li.symtable._sys.path[-1]
        self.assertListEqual(self.eval("ls('%s')" % dirname), 
                os.listdir(dirname))

    def test_ls_glob(self):
        '''ls builtin, glob'''

        from glob import glob
        dirname = os.path.join(os.path.dirname(larch.__file__), '*.py')
        self.assertListEqual(sorted(map(os.path.normpath, glob(dirname))), 
                sorted(map(os.path.normpath, self.eval("ls('%s')" % dirname))))

    def test_cwd(self):
        '''cwd builtin'''

        self.assertPathEqual(self.eval('cwd()'), os.getcwd())

    def test_cd(self):
        '''cd builtin'''

        with temp_set(os.chdir, os.getcwd(), os.getcwd()):
            dirname = self.li.symtable._sys.path[-1]
            ret = self.eval('cd("%s")' % dirname)
            self.assertPathEqual(ret, os.getcwd())
            self.assertPathEqual(os.getcwd(), dirname)

    def test_cs(self):
        '''cs builtin'''

        self.eval('g = group(a=5)')
        self.assert_(self.eval('a') is None)
        err_len = len(self.li.error)
        self.assert_(err_len != 0)
        self.eval('cs(g)')
        self.assert_(self.s._sys.localGroup == self.s.g)
        self.assert_(self.eval('a') == 5)
        self.assert_(len(self.li.error) == err_len)

    def test_cs_GroupAlias(self):
        '''cs builtin uses GroupAlias'''

        self.eval('d = dict()')
        self.eval('cs(d)')
        self.assert_('larch.symboltable.GroupAlias' in 
                str(self.s._sys.localGroup.__class__))

    def test_more(self):
        '''more builtin shows file contents'''

        log = []
        with fake_call(larch.builtins.pager, call_logger(log)):
            self.eval('more("%s")' % larch.__file__)
        with open(larch.__file__) as inf:
            self.assert_(log[0] == ((inf.read(),), {}))

    def test_more(self):
        '''more builtin notices nonexistent files'''

        log = []
        with fake_call(larch.builtins.pager, call_logger(log)):
            self.eval('more("%s")' % 'sdlfksjdl')
        with self.get_stdout() as stdout:
            self.assert_('cannot open file' in stdout)

    def test_help(self):
        '''help builtin'''

        pass

if __name__ == '__main__':  # pragma: no cover
    for suite in (TestParse, TestLarchEval):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.ColoredTextTestRunner(verbosity=2).run(suite)
