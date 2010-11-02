#!/usr/bin/env python

from __future__ import with_statement
import os
import sys
import unittest
from contextlib import contextmanager
import tempfile
import ast
import larch

#------------------------------------------------------------------------------

@contextmanager
def fake_call(original, replacement): # pragma: no cover
    '''context manager that swaps out a function when called with the
    given arguments. To be used for testing, not production.

    Args:
        original: function to replace
        replacement: function that answers some (possibly improper) subset
            of calls to original
    '''

    orig_mod = sys.modules[original.__module__]
    orig_name = original.__name__

    def dummy(*args, **kwargs):
        '''intercepts calls to original and substitutes replacement'''
        try: return replacement(*args, **kwargs)
        except KeyError: return original(*args, **kwargs)

    setattr(orig_mod, orig_name, dummy)
    yield
    setattr(orig_mod, orig_name, original)

@contextmanager
def temp_set(*args): # pragma: no cover
    '''temp_set(setter, temporary, original) -> context management
    calls setter(temporary) before and setter(original) after

    temp_set((obj, attrname), temporary)
    setattr(obj, attrname, temporary) before and restores original value after
    '''

    if len(args) == 3:
        setter, temporary, original = args
        setter(temporary)
        yield
        setter(original)
    elif len(args) == 2:
        obj, attrname = args[0]
        temporary = args[1]
        original = getattr(obj, attrname)

        setattr(obj, attrname, temporary)
        yield
        setattr(obj, attrname, original)
    else: raise ValueError("given %s\n\n%s" % (args, temp_set.__doc__))

#------------------------------------------------------------------------------

def call_logger(log):
    '''returns a function that writes its calls into log. e.g., 
        >>> log = []
        >>> f = call_logger(log)
        >>> f(1)
        >>> f(1, 2, 3, foo='bar')
        >>> log
        [((1,),{}), ((1, 2, 3), {'foo': 'bar'})]

    log can be anything with an `append` method.
    '''

    return lambda *args, **kwargs: log.append((args, kwargs))

#------------------------------------------------------------------------------

class TestCase(unittest.TestCase):
    def true(self, expr):
        '''assert that larch evaluates expr to True'''

        return self.assertTrue(self.li(expr))

    def false(self, expr):
        '''assert that larch evaluates expr to False'''

        return self.assertFalse(self.li(expr))

    def assertListEqual(self, A, B, do_print=False):
        '''A and B have the same items in the same order'''

        if do_print: print(A, B)
        self.assert_(len(A) == len(B))
        for a, b in zip(A, B):
            self.assert_(a == b)

    def assertPathEqual(self, A, B, do_print=False):
        '''A and B are the same path according to os.path.normpath()'''

        if do_print: print(A, B)
        self.assert_(os.path.normpath(A) == os.path.normpath(B))
    
    def assertNotRaises(self, excClass, *args, **kwargs):
        '''fails if an error is raised'''

        try: self.assertRaises(excClass, *args, **kwargs)
        except self.failureException, e:
            pass
        else: raise self.failureException("%s raised" % excClass.__name__)

    def setUp(self):
        self.stdout = tempfile.NamedTemporaryFile(delete=False, prefix='larch')
        self.li = larch.Interpreter(writer=self.stdout)
        self.n = lambda : self.li.symtable.n
        self.s = self.li.symtable

    def tearDown(self):
        if not self.stdout.closed:
            self.stdout.close()
        os.unlink(self.stdout.name)

    def eval(self, expr):
        '''evaluates expr in a way that the interpreter sometimes can't, for
        some reason. Appends a newline if necessary.
        '''

        if not expr.endswith('\n'):
            expr += '\n'

        return self.li.interp(ast.parse(expr))

    @contextmanager
    def get_stdout(self, flush=True):
        '''returns what has been written to stdout since last get_stdout().

        By default, flushes stdout afterward.
        ''' 

        self.stdout.close()
        with open(self.stdout.name) as inf:
            yield inf.read()
        os.unlink(self.stdout.name)
        self.stdout = tempfile.NamedTemporaryFile(delete=False, prefix='larch')

#------------------------------------------------------------------------------

class TestUtils(TestCase):

    def test_fake_call(self):
        '''fake_call context manager'''
        PATH = os.getenv('PATH')
        HOME = os.getenv('HOME')
        with fake_call(os.getenv, dict(HOME='here').__getitem__):
            self.assert_(os.getenv('HOME') == 'here')
            self.assert_(os.getenv('HOME') != HOME)
            self.assert_(os.getenv('PATH') == PATH)

    def test_temp_set_setter(self):
        '''temporarily set using setter'''

        d = dict(a=1)
        with temp_set(d.update, dict(a=2), dict(a=1)):
            self.assert_(d['a'] == 2)
        self.assert_(d['a'] == 1)

    def test_temp_set_setattr(self):
        '''temporarily set using setattr'''

        self.a = 1
        with temp_set((self, 'a'), 2):
            self.assert_(self.a == 2)
        self.assert_(self.a == 1)

    def test_assertNotRaises(self):
        '''assertNotRaises works'''

        def f(fail, arg_len, kwarg_len, *args, **kwargs):
            self.assert_(len(args) == arg_len)
            self.assert_(len(kwargs) == kwarg_len)
            if fail:
                raise IndexError

        self.assertNotRaises(IndexError, f, False, 3, 1, 1, 2, 3, a=5)
        self.assertRaises(self.failureException, self.assertNotRaises,
                IndexError, f, True, 0, 0)

    def test_call_logger(self):
        a = []
        f = call_logger(a)
        f(1)
        f(1, 2, 3, foo='bar')
        self.assertListEqual(a, [((1,),{}), ((1, 2, 3), dict(foo='bar'))])

#------------------------------------------------------------------------------
