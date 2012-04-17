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
    '''testing of asteval'''
    def test_dict_index(self):
        '''dictionary indexing'''
        self.session("a_dict = {'a': 1, 'b': 2, 'c': 3, 'd': 4}")
        self.isTrue("a_dict['a'] == 1")
        self.isTrue("a_dict['d'] == 4")

    def test_list_index(self):
        '''list indexing'''
        self.session("a_list = ['a', 'b', 'c', 'd', 'o']")
        self.isTrue("a_list[0] == 'a'")
        self.isTrue("a_list[1] == 'b'")
        self.isTrue("a_list[2] == 'c'")

    def test_tuple_index(self):
        '''tuple indexing'''
        self.session("a_tuple = (5, 'a', 'x')")
        self.isTrue("a_tuple[0] == 5")
        self.isTrue("a_tuple[2] == 'x'")

    def test_string_index(self):
        '''string indexing'''
        self.session("a_string = 'hello world'")
        self.isTrue("a_string[0] == 'h'")
        self.isTrue("a_string[6] == 'w'")
        self.isTrue("a_string[-1] == 'd'")
        self.isTrue("a_string[-2] == 'l'")

    def test_ndarray_index(self):
        '''nd array indexing'''
        self.session("a_ndarray = 5*arange(20)")
        self.isTrue("a_ndarray[2] == 10")
        self.isTrue("a_ndarray[4] == 20")

    def test_ndarrayslice(self):
        '''array slicing'''
        self.session("a_ndarray = arange(200).reshape(10, 20)")
        self.isTrue("a_ndarray[1:3,5:7] == array([[25,26], [45,46]])")
        self.session("y = arange(20).reshape(4, 5)")
        self.isTrue("y[:,3]  == array([3, 8, 13, 18])")
        self.isTrue("y[...,1]  == array([1, 6, 11, 16])")
        self.session("y[...,1] = array([2, 2, 2, 2])")
        self.isTrue("y[1,:] == array([5, 2, 7, 8, 9])")
        # print(self.session.symtable["y"])

    def test_while(self):
        '''while loops'''
        self.session("""
n=0
while n < 8:
    n += 1
""")
        self.isValue('n',  8)

        self.session("""
n=0
while n < 8:
    n += 1
    if n > 3:
        break
else:
    n = -1
""")
        self.isValue('n',  4)


        self.session("""
n=0
while n < 8:
    n += 1
else:
    n = -1
""")
        self.isValue('n',  -1)

        self.session("""
n=0
while n < 10:
    n += 1
    if n < 3:
        continue
    n += 1
    print( ' n = ', n)
    if n > 5:
        break
print( 'finish: n = ', n)
""")
        self.isValue('n',  6)

    def test_assert(self):
        'test assert statements'
        self.session.error = []
        self.session('n=6')
        self.session('assert n==6')
        self.assertTrue(self.session.error == [])
        self.session('assert n==7')
        errtype, errmsg = self.session.error[0].get_error()
        self.assertTrue(errtype == 'AssertionError')

    def test_for(self):
        '''for loops'''
        self.session('''
n=0
for i in arange(10):
    n += i
''')
        self.isValue('n', 45)

        self.session('''
n=0
for i in arange(10):
    n += i
else:
    n = -1
''')
        self.isValue('n', -1)

        self.session('''
n=0
for i in arange(10):
    n += i
    if n > 2:
        break
else:
    n = -1
''')
        self.isValue('n', 3)


    def test_if(self):
        '''test if'''
        self.session("""zero = 0
if zero == 0:
    x = 1
if zero != 100:
    x = x+1
if zero > 2:
    x = x + 1
else:
    y = 33
""")
        self.isValue('x',  2)
        self.isValue('y', 33)

    def test_print(self):
        '''print (ints, str, ....)'''
        self.session("print(31)")
        self.session.writer.flush()
        time.sleep(0.1)
        out = self.read_stdout()
        self.assert_(out== '31\n')

        self.session("print('%s = %.3f' % ('a', 1.2012345))")
        self.session.writer.flush()
        time.sleep(0.1)
        out = self.read_stdout()
        self.assert_(out== 'a = 1.201\n')

        self.session("print('{0:s} = {1:.2f}'.format('a', 1.2012345))")
        self.session.writer.flush()
        time.sleep(0.1)
        out = self.read_stdout()
        self.assert_(out== 'a = 1.20\n')

    def test_repr(self):
        '''repr of dict, list'''
        self.session("x = {'a': 1, 'b': 2, 'c': 3}")
        self.session("y = ['a', 'b', 'c']")
        self.session("rep_x = repr(x['a'])")
        self.session("rep_y = repr(y)")
        self.session("print rep_y , rep_x")

        self.isValue("rep_x", "1")
        self.isValue("rep_y", "['a', 'b', 'c']")

    def test_cmp(self):
        '''numeric comparisons'''
        self.isTrue("3 == 3")
        self.isTrue("3.0 == 3")
        self.isTrue("3.0 == 3.0")
        self.isTrue("3 != 4")
        self.isTrue("3.0 != 4")
        self.isTrue("3 >= 1")
        self.isTrue("3 >= 3")
        self.isTrue("3 <= 3")
        self.isTrue("3 <= 5")
        self.isTrue("3 < 5")
        self.isTrue("5 > 3")

        self.isFalse("3 == 4")
        self.isFalse("3 > 5")
        self.isFalse("5 < 3")

    def test_bool(self):
        '''boolean logic'''

        self.session('''
yes = True
no = False
nottrue = False
a = arange(7)''')

        self.isTrue("yes")
        self.isFalse("no")
        self.isFalse("nottrue")
        self.isFalse("yes and no or nottrue")
        self.isFalse("yes and (no or nottrue)")
        self.isFalse("(yes and no) or nottrue")
        self.isTrue("yes or no and nottrue")
        self.isTrue("yes or (no and nottrue)")
        self.isFalse("(yes or no) and nottrue")
        self.isTrue("yes or not no")
        self.isTrue("(yes or no)")
        self.isFalse("not (yes or yes)")
        self.isFalse("not (yes or no)")
        self.isFalse("not (no or yes)")
        self.isTrue("not no or yes")
        self.isFalse("not yes")
        self.isTrue("not no")

    def test_bool_coerce(self):
        '''coercion to boolean'''

        self.isTrue("1")
        self.isFalse("0")

        self.isTrue("'1'")
        self.isFalse("''")

        self.isTrue("[1]")
        self.isFalse("[]")

        self.isTrue("(1)")
        self.isTrue("(0,)")
        self.isFalse("()")

        self.isTrue("dict(y=1)")
        self.isFalse("{}")

    def test_assignment(self):
        '''variables assignment'''
        self.session('n = 5')
        self.isValue("n",  5)
        self.session('s1 = "a string"')
        self.isValue("s1",  "a string")
        self.session('b = (1,2,3)')
        self.isValue("b",  (1,2,3))
        self.session('a = 1.*arange(10)')
        self.isValue("a", np.arange(10) )
        self.session('a[1:5] = 1 + 0.5 * arange(4)')
        self.isNear("a", np.array([ 0. ,  1. ,  1.5,  2. ,  2.5,  5. ,  6. ,  7. ,  8. ,  9. ]))

    def test_names(self):
        '''names test'''
        self.session('nx = 1')
        self.session('nx1 = 1')

    def test_syntaxerrors_1(self):
        '''assignment syntax errors test'''
        for expr in ('class = 1', 'for = 1', 'if = 1', 'raise = 1',
                     '1x = 1', '1.x = 1', '1_x = 1'):
            failed, errtype, errmsg = False, None, None
            self.session(expr)
            if self.session.error:
                err = self.session.error.pop(0)
                errtype, errmsg = err.get_error()
                failed = True

            self.assertTrue(failed)
            self.assertTrue(errtype == 'SyntaxError')
            #self.assertTrue(errmsg.startswith('invalid syntax'))

    def test_unsupportednodes(self):
        '''unsupported nodes'''

        for expr in ('f = lambda x: x*x', 'yield 10'):
            failed, errtype, errmsg = False, None, None
            self.session(expr)
            if self.session.error:
                err = self.session.error.pop(0)
                errtype, errmsg = err.get_error()
                failed = True

            self.assertTrue(failed)
            self.assertTrue(errtype == 'NotImplementedError')

    def test_syntaxerrors_2(self):
        '''syntax errors test'''
        for expr in ('x = (1/*)', 'x = 1.A', 'x = A.2'):

            failed, errtype, errmsg = False, None, None
            self.session(expr)
            if self.session.error:
                err = self.session.error.pop(0)
                errtype, errmsg = err.get_error()
                failed = True

            self.assertTrue(failed)
            self.assertTrue(errtype == 'SyntaxError')
            #self.assertTrue(errmsg.startswith('invalid syntax'))

    def test_runtimeerrors_1(self):
        '''runtime errors test'''
        self.session("zero = 0")
        self.session("astr ='a string'")
        self.session("atup = ('a', 'b', 11021)")
        self.session("arr  = arange(20)")
        for expr, errname in (('x = 1/zero', 'ZeroDivisionError'),
                              ('x = zero + nonexistent', 'NameError'),
                              ('x = zero + astr', 'TypeError'),
                              ('x = zero()', 'TypeError'),
                              ('x = astr * atup', 'TypeError'),
                              ('x = arr.shapx', 'AttributeError'),
                              ('arr.shapx = 4', 'AttributeError'),
                              ('del arr.shapx', 'LookupError')):
            failed, errtype, errmsg = False, None, None
            self.session(expr)
            if self.session.error:
                err = self.session.error.pop(0)
                errtype, errmsg = err.get_error()
                failed = True

            self.assertTrue(failed)
            self.assertTrue(errtype == errname)
            #self.assertTrue(errmsg.startswith('invalid syntax'))

    def test_ndarrays(self):
        '''simple ndarrays'''
        self.session('n = array([11, 10, 9])')
        self.isTrue("isinstance(n, ndarray)")
        self.isTrue("len(n) == 3")
        self.isValue("n", np.array([11, 10, 9]))
        self.session('n = arange(20).reshape(5, 4)')
        self.isTrue("isinstance(n, ndarray)")
        self.isTrue("n.shape == (5, 4)")
        self.session("myx = n.shape")
        self.session("n.shape = (4, 5)")
        self.isTrue("n.shape == (4, 5)")

        # self.session("del = n.shape")
        self.session("a = arange(20)")
        self.session("gg = a[1:13:3]")
        self.isValue('gg', np.array([1, 4, 7, 10]))

        self.session("gg[:2] = array([0,2])")
        self.isValue('gg', np.array([0, 2, 7, 10]))
        self.session('a, b, c, d = gg')
        self.isValue('c', 7)
        self.isTrue('(a, b, d) == (0, 2, 10)')

    def test_binop(self):
        '''test binary ops'''
        self.session('a = 10.0')
        self.session('b = 6.0')

        self.isTrue("a+b == 16.0")
        self.isNear("a-b", 4.0)
        self.isTrue("a/(b-1) == 2.0")
        self.isTrue("a*b     == 60.0")

    def test_unaryop(self):
        '''test binary ops'''
        self.session('a = -10.0')
        self.session('b = -6.0')

        self.isNear("a", -10.0)
        self.isNear("b", -6.0)

    def test_del(self):
        '''test del function'''
        self.session('a = -10.0')
        self.session('b = -6.0')

        self.assertTrue(self.symtable.has_symbol('a'))
        self.assertTrue(self.symtable.has_symbol('b'))

        self.session("del a")
        self.session("del b")

        self.assertFalse(self.symtable.has_symbol('a'))
        self.assertFalse(self.symtable.has_symbol('b'))

    def test_math1(self):
        '''builtin math functions'''
        self.session('n = sqrt(4)')
        self.isTrue('n == 2')
        self.isNear('sin(pi/2)', 1)
        self.isNear('cos(pi/2)', 0)
        self.isTrue('exp(0) == 1')
        self.isNear('exp(1)', np.e)

    def test_list_comprehension(self):
        "test list comprehension"
        self.session('x = [i*i for i in range(4)]')
        self.isValue('x', [0, 1, 4, 9])

        self.session('x = [i*i for i in range(6) if i > 1]')
        self.isValue('x', [4, 9, 16, 25])

    def test_ifexp(self):
        "test if expressions"
        self.session('x = 2')
        self.session('y = 4 if x > 0 else -1')
        self.session('z = 4 if x > 3 else -1')
        self.isValue('y', 4)
        self.isValue('z', -1)

    def test_index_assignment(self):
        "test indexing / subscripting on assignment"
        self.session('x = arange(10)')
        self.session('l = [1,2,3,4,5]')
        self.session('l[0] = 0')
        self.session('l[3] = -1')
        self.isValue('l', [0,2,3,-1,5])
        self.session('l[0:2] = [-1, -2]')
        self.isValue('l', [-1,-2,3,-1,5])

        self.session('x[1] = 99')
        self.isValue('x', np.array([0,99,2,3,4,5,6,7,8,9]))
        self.session('x[0:2] = [9,-9]')
        self.isValue('x', np.array([9,-9,2,3,4,5,6,7,8,9]))

    def test_reservedwords(self):
        "test reserved words"
        for w in ('and', 'as', 'while', 'raise', 'else',
                  'class', 'del', 'def', 'None', 'True', 'False'):
            self.session.error= []
            self.session("%s= 2" % w)
            self.assertTrue(len(self.session.error) > 0)
            errtype, errmsg = self.session.error[0].get_error()
            self.assertTrue(errtype=='SyntaxError')
            
    def test_raise(self):
        "test raise"
        self.session("raise NameError('bob')")
        errtype, errmsg = self.session.error[0].get_error()
        errmsgs = errmsg.split('\n')
        self.assertTrue(errtype == 'NameError')


    def test_tryexcept(self):
        "test try/except"
        self.session("""
x = 5
try:
    x = x/0
except ZeroDivsionError:
    print( 'Error Seen!')
    x = -999
""")
        self.isValue('x', -999)

        self.session("""
x = -1
try:
    x = x/0
except ZeroDivsionError:
    pass
""")
        self.isValue('x', -1)

    def xtest_function1(self):
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

        self.session("a = fcn()")
        errtype, errmsg = self.session.error[0].get_error()
        
        errlines = errmsg.split('\n')

        self.assertTrue(errtype == 'TypeError')

        self.session("a = fcn(x, bogus=3)")
        errtype, errmsg = self.session.error[0].get_error()
        errmsgs = errmsg.split('\n')
        self.assertTrue(errtype == 'NameError')

    def xtest_function_vararg(self):
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

    def xtest_function_kwargs(self):
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
        errmsg0, errmsg1 = errmsg.split('\n')
        self.assertTrue(errmsg1.startswith('extra keyword arg'))

    def xtest_function_kwargs1(self):
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


    def xtest_function_kwargs2(self):
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

        self.session("o = fcn(x=1, y=2)")
        self.isValue('o', 5)

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
