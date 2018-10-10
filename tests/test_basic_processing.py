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
    '''testing of asteval'''
    def test_dict_index(self):
        '''dictionary indexing'''
        self.trytext("a_dict = {'a': 1, 'b': 2, 'c': 3, 'd': 4}")
        self.isTrue("a_dict['a'] == 1")
        self.isTrue("a_dict['d'] == 4")

    def test_list_index(self):
        '''list indexing'''
        self.trytext("a_list = ['a', 'b', 'c', 'd', 'o']")
        self.isTrue("a_list[0] == 'a'")
        self.isTrue("a_list[1] == 'b'")
        self.isTrue("a_list[2] == 'c'")

    def test_tuple_index(self):
        '''tuple indexing'''
        self.trytext("a_tuple = (5, 'a', 'x')")
        self.isTrue("a_tuple[0] == 5")
        self.isTrue("a_tuple[2] == 'x'")

    def test_string_index(self):
        '''string indexing'''
        self.trytext("a_string = 'hello world'")
        self.isTrue("a_string[0] == 'h'")
        self.isTrue("a_string[6] == 'w'")
        self.isTrue("a_string[-1] == 'd'")
        self.isTrue("a_string[-2] == 'l'")

    def test_ndarray_index(self):
        '''nd array indexing'''
        self.trytext("a_ndarray = 5*arange(20)")
        self.isTrue("a_ndarray[2] == 10")
        self.isTrue("a_ndarray[4] == 20")

    def test_ndarrayslice(self):
        '''array slicing'''
        self.trytext("a_ndarray = arange(200).reshape(10, 20)")
        self.isTrue("a_ndarray[1:3,5:7] == array([[25,26], [45,46]])")
        self.trytext("y = arange(20).reshape(4, 5)")
        self.isTrue("y[:,3]  == array([3, 8, 13, 18])")
        self.isTrue("y[...,1]  == array([1, 6, 11, 16])")
        self.trytext("y[...,1] = array([2, 2, 2, 2])")
        self.isTrue("y[1,:] == array([5, 2, 7, 8, 9])")
        # print(self.session.symtable["y"])

    def test_while(self):
        '''while loops'''
        self.trytext("""n=0
while n < 8:
    n += 1
endwhile
""")
        self.isValue('n',  8)

        self.trytext("""
n=0
while n < 8:
    n += 1
    if n > 3:
        break
    endif
else:
    n = -1
endwhile
""")
        self.isValue('n',  4)


        self.trytext("""
n=0
while n < 8:   # test while-else
    n += 1
else:
    n += -1
endwhile
""")
        self.isValue('n',  7)

        self.trytext("""
n=0
while n < 10:
    n += 1
    if n < 3:
        continue
    endif
    n += 1
    print( ' n = ', n)
    if n > 5:
        break
    endif
endwhile
""")
        self.isValue('n',  6)

    def test_assert(self):
        'test assert statements'
        self.trytext('n=6')
        out, err = self.trytext('assert n==6')
        self.assertTrue(len(err) == 0)
        out, err = self.trytext('assert n==7')
        errtype, errmsg = err[0].get_error()
        self.assertTrue(errtype == 'AssertionError')

    def test_for(self):
        '''for loops'''
        self.trytext('''
n=0
for i in arange(10):
    n += i
endfor
''')
        self.isValue('n', 45)

        self.trytext('''
n=0
for i in arange(10):
    n += i
else:
    n = -1
endfor
''')
        self.isValue('n', -1)

        self.trytext('''
n=0
for i in arange(10):
    n += i
    if n > 2:
        break
    endif
else:
    n = -1
endfor
''')
        self.isValue('n', 3)

    def test_if(self):
        '''test if'''
        self.trytext("""zero = 0
if zero == 0:
    x = 1
endif
if zero != 100:
    x = x+1
endif
if zero > 2:
    x = x + 1
else:
    y = 33
endif
""")
        self.isValue('x',  2)
        self.isValue('y', 33)

    def test_nestedif(self):
        """test of single-line ifs in if blocks"""
        self.trytext("""
def xtest(xt, out=None):
    if out is None:
        out = 'A'
        if xt < 9:  out = 'B'
        if xt < 5:  out = 'C'
        if xt < 2:  out = 'D'
    #endif
    return out
#enddef

a = xtest(100)
b = xtest(8)
c = xtest(4)
d = xtest(1)
q = xtest(4, out='Q')
""")
        self.isValue('a', 'A')
        self.isValue('b', 'B')
        self.isValue('c', 'C')
        self.isValue('d', 'D')
        self.isValue('q', 'Q')


    def test_print(self):
        '''print (ints, str, ....)'''
        out, err  = self.trytext("print(31)")
        self.assertTrue(out== '31\n')

        out, err = self.trytext("print('%s = %.3f' % ('a', 1.2012345))")
        self.assertTrue(out== 'a = 1.201\n')

        out, err = self.trytext("print('{0:s} = {1:.2f}'.format('a', 1.2012345))")
        self.assertTrue(out== 'a = 1.20\n')

    def test_repr(self):
        '''repr of dict, list'''
        self.trytext("x = {'a': 1, 'b': 2, 'c': 3}")
        self.trytext("y = ['a', 'b', 'c']")
        self.trytext("rep_x = repr(x['a'])")
        self.trytext("rep_y = repr(y)")
        self.trytext("print(rep_y , rep_x)")

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

        self.trytext('''
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
        self.trytext('n = 5')
        self.isValue("n",  5)
        self.trytext('s1 = "a string"')
        self.isValue("s1",  "a string")
        self.trytext('b = (1,2,3)')
        self.isValue("b",  (1,2,3))
        self.trytext('a = 1.*arange(10)')
        self.isValue("a", np.arange(10) )
        self.trytext('a[1:5] = 1 + 0.5 * arange(4)')
        self.isNear("a", np.array([ 0. ,  1. ,  1.5,  2. ,  2.5,  5. ,  6. ,  7. ,  8. ,  9. ]))

    def test_names(self):
        '''names test'''
        self.trytext('nx = 1')
        self.trytext('nx1 = 1')

    def test_syntaxerrors_1(self):
        '''assignment syntax errors test'''
        for expr in ('class = 1', 'for = 1', 'if = 1', 'raise = 1',
                     '1x = 1', '1.x = 1', '1_x = 1'):
            failed, errtype, errmsg = False, None, None
            out, err = self.trytext(expr)
            if len(err) > 0:
                errtype, errmsg = err[0].get_error()
                failed = True
            self.assertTrue(failed)
            self.assertTrue(errtype == 'SyntaxError')
            #self.assertTrue(errmsg.startswith('invalid syntax'))

    def test_unsupportednodes(self):
        '''unsupported nodes'''

        for expr in ('f = lambda x: x*x', 'yield 10'):
            failed, errtype, errmsg = False, None, None
            out, err = self.trytext(expr)
            if len(err) > 0:
                errtype, errmsg = err[0].get_error()
                failed = True

            self.assertTrue(failed)
            self.assertTrue(errtype == 'NotImplementedError')

    def test_syntaxerrors_2(self):
        '''syntax errors test'''
        for expr in ('x = (1/*)', 'x = 1.A', 'x = A.2'):

            failed, errtype, errmsg = False, None, None
            out, err = self.trytext(expr)
            if len(err) > 0:
                errtype, errmsg = err[0].get_error()
                failed = True

            self.assertTrue(failed)
            self.assertTrue(errtype == 'SyntaxError')
            #self.assertTrue(errmsg.startswith('invalid syntax'))

    def test_runtimeerrors_1(self):
        '''runtime errors test'''
        self.trytext("zero = 0")
        self.trytext("astr ='a string'")
        self.trytext("atup = ('a', 'b', 11021)")
        self.trytext("arr  = arange(20)")
        for expr, errname in (('x = 1/zero', 'ZeroDivisionError'),
                              ('x = zero + nonexistent', 'NameError'),
                              ('x = zero + astr', 'TypeError'),
                              ('x = zero()', 'TypeError'),
                              ('x = astr * atup', 'TypeError'),
                              ('x = arr.shapx', 'AttributeError'),
                              ('arr.shapx = 4', 'AttributeError'),
                              ('del arr.shapx', 'LookupError')):
            failed, errtype, errmsg = False, None, None

            out, err = self.trytext(expr)
            if len(err) > 0:
                errtype, errmsg = err[0].get_error()
                failed = True
            self.assertTrue(failed)
            self.assertTrue(errtype == errname)
            #self.assertTrue(errmsg.startswith('invalid syntax'))

    def test_ndarrays(self):
        '''simple ndarrays'''
        self.trytext('n = array([11, 10, 9])')
        self.isTrue("isinstance(n, ndarray)")
        self.isTrue("len(n) == 3")
        self.isValue("n", np.array([11, 10, 9]))
        self.trytext('n = arange(20).reshape(5, 4)')
        self.isTrue("isinstance(n, ndarray)")
        self.isTrue("n.shape == (5, 4)")
        self.trytext("myx = n.shape")
        self.trytext("n.shape = (4, 5)")
        self.isTrue("n.shape == (4, 5)")

        # self.trytext("del = n.shape")
        self.trytext("a = arange(20)")
        self.trytext("gg = a[1:13:3]")
        self.isValue('gg', np.array([1, 4, 7, 10]))

        self.trytext("gg[:2] = array([0,2])")
        self.isValue('gg', np.array([0, 2, 7, 10]))
        self.trytext('a, b, c, d = gg')
        self.isValue('c', 7)
        self.isTrue('(a, b, d) == (0, 2, 10)')

    def test_binop(self):
        '''test binary ops'''
        self.trytext('a = 10.0')
        self.trytext('b = 6.0')

        self.isTrue("a+b == 16.0")
        self.isNear("a-b", 4.0)
        self.isTrue("a/(b-1) == 2.0")
        self.isTrue("a*b     == 60.0")

    def test_unaryop(self):
        '''test binary ops'''
        self.trytext('a = -10.0')
        self.trytext('b = -6.0')

        self.isNear("a", -10.0)
        self.isNear("b", -6.0)

    def test_del(self):
        '''test del function'''
        self.trytext('a = -10.0')
        self.trytext('b = -6.0')

        self.assertTrue(self.symtable.has_symbol('a'))
        self.assertTrue(self.symtable.has_symbol('b'))

        self.trytext("del a")
        self.trytext("del b")

        self.assertFalse(self.symtable.has_symbol('a'))
        self.assertFalse(self.symtable.has_symbol('b'))

    def test_math1(self):
        '''builtin math functions'''
        self.trytext('n = sqrt(4)')
        self.isTrue('n == 2')
        self.isNear('sin(pi/2)', 1)
        self.isNear('cos(pi/2)', 0)
        self.isTrue('exp(0) == 1')
        self.isNear('exp(1)', np.e)

    def test_list_comprehension(self):
        "test list comprehension"
        self.trytext('x = [i*i for i in range(4)]')
        self.isValue('x', [0, 1, 4, 9])

        self.trytext('x = [i*i for i in range(6) if i > 1]')
        self.isValue('x', [4, 9, 16, 25])

    def test_ifexp(self):
        "test if expressions"
        self.trytext('x = 2')
        self.trytext('y = 4 if x > 0 else -1')
        self.trytext('z = 4 if x > 3 else -1')
        self.isValue('y', 4)
        self.isValue('z', -1)

    def test_index_assignment(self):
        "test indexing / subscripting on assignment"
        self.trytext('x = arange(10)')
        self.trytext('l = [1,2,3,4,5]')
        self.trytext('l[0] = 0')
        self.trytext('l[3] = -1')
        self.isValue('l', [0,2,3,-1,5])
        self.trytext('l[0:2] = [-1, -2]')
        self.isValue('l', [-1,-2,3,-1,5])

        self.trytext('x[1] = 99')
        self.isValue('x', np.array([0,99,2,3,4,5,6,7,8,9]))
        self.trytext('x[0:2] = [9,-9]')
        self.isValue('x', np.array([9,-9,2,3,4,5,6,7,8,9]))

    def test_reservedwords(self):
        "test reserved words"
        for w in ('and', 'as', 'while', 'raise', 'else',
                  'class', 'del', 'def', 'None', 'True', 'False'):
            out, err = self.trytext("%s= 2" % w)
            self.assertTrue(len(err) > 0)
            errtype, errmsg = err[0].get_error()
            self.assertTrue(errtype=='SyntaxError')

    def test_raise(self):
        "test raise"
        out, err = self.trytext("raise NameError('bob')")
        errtype, errmsg = err[0].get_error()
        errmsgs = errmsg.split('\n')
        self.assertTrue(errtype == 'NameError')


    def test_tryexcept(self):
        "test try/except"
        self.trytext("""
x = 5
try:
    x = x/0
except ZeroDivsionError:
    x = -999
endtry
""")
        self.isValue('x', -999)

        self.trytext("""
x = -1
try:
    x = x/0
except ZeroDivsionError:
    pass
endtry
""")
        self.isValue('x', -1)


    def test_astdump(self):
        "test ast parsing and dumping"
        astnode = self.session._larch.parse('x = 1')
        self.assertTrue(isinstance(astnode, ast.Module))
        self.assertTrue(isinstance(astnode.body[0], ast.Assign))
        self.assertTrue(isinstance(astnode.body[0].targets[0], ast.Name))
        self.assertTrue(isinstance(astnode.body[0].value, ast.Num))
        self.assertTrue(astnode.body[0].targets[0].id == 'x')
        self.assertTrue(astnode.body[0].value.n == 1)
        dumped = self.session._larch.dump(astnode.body[0])
        self.assertTrue(dumped.startswith('Assign'))

    def test_import(self):
        '''simple import'''
        self.trytext("import numpy")
        self.isTrue("callable(getattr(numpy, 'sqrt'))")
        self.isTrue("callable(getattr(numpy, 'arange'))")
        self.isNear("getattr(numpy, 'pi', 0)", 3.14159, places=5)

    def test_import_as(self):
        '''simple import'''
        self.trytext("import numpy as np")
        self.isTrue("callable(getattr(np, 'sqrt'))")
        self.isTrue("callable(getattr(np, 'arange'))")
        self.isNear("getattr(np, 'pi', 0)", 3.14159, places=5)


if __name__ == '__main__':  # pragma: no cover
    for suite in (TestEval,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=2).run(suite)
