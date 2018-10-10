#
"""
tests for code in lib/utils/jsonutils to convert Python/Larch
objects to and from representations that can be serialized with JSON.
"""
from __future__ import print_function
import unittest
import nose
import numpy as np
from numpy.testing import assert_allclose

from larch import isParameter, Parameter, isgroup, Group
from larch.utils.jsonutils import encode4js, decode4js

def encode(obj):
    out = encode4js(obj)
    print("Encoded to: ", out)
    return out

def deval(obj):
    out = decode4js(encode(obj))
    print("Decoded to: ", out)
    return out

def evaltest(obj):
    assert(deval(obj) == obj)

class EncodeDecode4Json_Test(unittest.TestCase):
    def setUp(self):
        self.param1 = Parameter(name='a', value=2.0, vary=True, min=0)
        self.param2 = Parameter(name='b', expr='sqrt(x/2)')
        self.group1 = Group(a     = 1.030405,
                            label = 'a string',
                            opts  = {'a':1, 'b':2},
                            x     = np.linspace(0, 10, 21),
                            y     = np.sqrt(np.arange(3)/5.))

        self.group2 = Group(par1 = Parameter(name='p1', value=3.0, min=0.0, vary=False),
                            par2 = Parameter(name='p2', value=1.0, vary=True),
                            sub  = Group(label='a label',
                                         x = np.linspace(0, 10, 21)))

        self.group3 = Group(par1 = Parameter(name='p1', value=3.0, min=0.0),
                            dx    = {'a': 1.3+0.2j, 'blist': [1,2,3.0],
                                     'tup': (0, None)} )


    def test_encode_string(self):
        out = encode('hello')
        assert(out == 'hello')

    def test_eval_string(self):
        evaltest('hello')

    def test_encode_int(self):
        out = encode(99)
        assert(out == 99)

    def test_eval_int(self):
        evaltest(99)

    def test_encode_double(self):
        out = encode(2.0)
        assert(out == 2.0)

    def test_eval_double(self):
        evaltest(9.95)


    def test_encode_complex(self):
        out = encode(2.0 + 1.0j)
        assert(isinstance(out, dict))
        assert(out['__class__'] == 'Complex')
        assert(out['value'] == (2.0, 1.0))

    def test_eval_complex(self):
        evaltest(2.103 + 99.11j)

    def test_encode_list(self):
        out = encode([1, 2, 'a', ['x', 'y', 'z']])
        assert(isinstance(out, dict))
        assert(out['__class__'] == 'List')
        assert(out['value'][0] == 1)
        assert(out['value'][2] == 'a')
        assert(isinstance(out['value'][3], dict))
        assert(out['value'][3]['__class__'] == 'List')
        assert(out['value'][3]['value'][1] == 'y')

    def test_eval_list(self):
        evaltest( [1, 2, 'a', ['x', 'y', 'z']])

    def test_encode_tuple(self):
        out = encode(('s', None, False))
        assert(isinstance(out, dict))
        assert(out['__class__'] == 'Tuple')
        assert(out['value'][0] == 's')
        assert(out['value'][1] == None)
        assert(out['value'][2] == False)

    def test_eval_tuple(self):
        evaltest(('s', None, False, ('a', 'b', 'c')))

    def test_encode_array1(self):
        out = encode(np.arange(10)/7.0)
        assert(isinstance(out, dict))
        assert(out['__class__'] == 'Array')
        assert(out['__shape__'] == (10, ))
        assert(out['value'][0] == 0)
        assert(len(out['value']) == 10)
        assert_allclose(out['value'][1], 0.142857, rtol=1.e-4)

    def test_eval_array1(self):
        testval = np.arange(10)/7.2
        assert_allclose(deval(testval), testval, rtol=1.e-4)

    def test_encode_array2(self):
        out = encode((np.arange(20)/2.0).reshape((4, 5)))
        assert(isinstance(out, dict))
        assert(out['__class__'] == 'Array')
        assert(out['__shape__'] == (4, 5))
        assert(len(out['value']) == 20)
        arr = np.array(out['value']).reshape(out['__shape__'])
        assert_allclose(arr[1][2], 3.5, rtol=1.e-4)

    def test_eval_array2(self):
        testval = (np.arange(20)/7.2).reshape((4, 5))
        out = deval(testval)
        assert(out.shape == (4, 5))
        assert_allclose(out, testval, rtol=1.e-4)

    def test_encode_array3(self):
        out = encode(np.arange(10)/2.0 - 1j*np.arange(10))
        assert(isinstance(out, dict))
        assert(out['__class__'] == 'Array')
        assert(out['__shape__'] == (10,))
        assert(out['__dtype__'].startswith('complex'))
        assert(len(out['value']) == 2)
        val = out['value']
        assert(isinstance(val, list))
        assert(len(val)    == 2)
        assert(len(val[0]) == 10)
        assert_allclose(val[0][4],  2.0, rtol=1.e-4)
        assert_allclose(val[1][3], -3.0, rtol=1.e-4)

    def test_eval_array3(self):
        testval = np.arange(10)/2.0 - 1j*np.arange(10)
        out = deval(testval)
        assert(out.dtype == np.complex)
        assert_allclose(out, testval, rtol=1.e-4)

    def test_encode_param1(self):
        out = encode(self.param1)
        assert(isinstance(out, dict))
        assert(out['__class__'] == 'Parameter')
        assert(out['name'] == 'a')
        assert(out['vary'] == True)
        assert_allclose(out['value'], 2.0)
        assert_allclose(out['min'], 0.0)

    def test_eval_param1(self):
        out = deval(self.param1)
        assert(isParameter(out))
        assert(out.name == 'a')
        assert(out.vary == True)
        assert(out.value == 2.0)
        assert(out.min == 0)

    def test_encode_param2(self):
        out = encode(self.param2)
        assert(isinstance(out, dict))
        assert(out['__class__'] == 'Parameter')
        assert(out['name'] == 'b')
        assert(out['vary'] == False)
        assert(len(out['expr']) > 2)

    def test_eval_param2(self):
        out = deval(self.param2)
        assert(isParameter(out))
        assert(out.name == 'b')
        assert(out.expr.startswith('sqrt(x/2)'))

    def test_encode_group1(self):
        out = encode(self.group1)
        assert(isinstance(out, dict))
        assert(out['__class__'] == 'Group')
        assert(out['label'] == 'a string')
        assert(isinstance(out['x'], dict))
        assert(isinstance(out['opts'], dict))
        assert(out['opts']['__class__'] == 'Dict')
        assert(out['x']['__class__'] == 'Array')
        assert(out['y']['__class__'] == 'Array')
        assert_allclose(out['opts']['a'],  1.0, rtol=1.e-4)
        assert_allclose(out['x']['value'][:3], [0, 0.5, 1.0], rtol=1.e-4)

    def test_eval_group1(self):
        out = deval(self.group1)
        assert(isgroup(out))
        assert(getattr(out, 'label') == 'a string')
        assert(out.opts['a'] == 1)
        assert_allclose(out.a, 1.03, rtol=1.e-2)
        assert_allclose(out.x, np.linspace(0, 10, 21), rtol=1.e-2)

    def test_encode_group2(self):
        out = encode(self.group2)
        assert(isinstance(out, dict))
        assert(out['__class__'] == 'Group')
        assert(isinstance(out['par1'], dict))
        assert(out['par1']['__class__'] == 'Parameter')
        assert(out['par1']['name'] == 'p1')
        assert(out['par1']['value'] == 3.0)
        assert(out['par1']['vary'] == False)
        assert(out['par1']['min'] == 0.0)
        assert(out['par2']['__class__'] == 'Parameter')
        assert(out['par2']['name'] == 'p2')
        assert(out['par2']['vary'] == True)
        assert(out['par2']['value'] == 1.0)
        assert(out['sub']['__class__'] == 'Group')
        assert(out['sub']['label'] == 'a label')
        assert(out['sub']['x']['__class__'] == 'Array')
        assert(out['sub']['x']['__class__'] == 'Array')
        assert_allclose(out['sub']['x']['value'][:3], [0, 0.5, 1.0], rtol=1.e-4)

    def test_eval_group2(self):
        out = deval(self.group2)
        assert(isgroup(out))
        assert(out.sub.label == 'a label')
        assert(isParameter(out.par1))
        assert(isParameter(out.par2))
        assert(out.par1.name == 'p1')
        assert(out.par2.name == 'p2')
        assert(out.par1.vary == False)
        assert(out.par2.vary == True)
        assert(out.par1.value == 3.0)
        assert(out.par2.value == 1.0)
        assert(out.par1.min   == 0.0)

    def test_eval_group3(self):
        out = deval(self.group3)
        assert(isgroup(out))
        assert(out.dx['a']     == 1.3 + 0.2j)
        assert(out.dx['tup']   == (0, None))
        assert(out.dx['blist'] == [1,2,3.0])

if __name__ == '__main__':
    for suite in (EncodeDecode4Json_Test,):
        suite = unittest.TestLoader().loadTestsFromTestCase(suite)
        unittest.TextTestRunner(verbosity=0).run(suite)
