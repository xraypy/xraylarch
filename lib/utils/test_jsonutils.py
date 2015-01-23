import unittest
import nose
import json
import numpy as np
from numpy.testing import assert_
import larch
from jsonutils import json_encode, json_decode

from larch import isParameter, Parameter, Group

class JSONTest(unittest.TestCase):
    def setUp(self):
        self._larch = larch.Interpreter()

    def eval(self, obj):
        return json_encode(repr(obj), _larch=self._larch)

    def test_encode_string(self):
        x = self.eval('hello')
        assert(x == 'hello')

    def test_encode_int(self):
        x = self.eval(99)
        assert(x == 99)

    def test_encode_double(self):
        x = self.eval(2.0)
        assert(x == 2.0)

    def test_encode_complex(self):
        x = self.eval(2.0 + 1.0j)
        assert(isinstance(x, dict))
        assert(x['__class__'] == 'Complex')
        assert(x['value'] == (2.0, 1.0))

    def test_encode_list(self):
        dat = [1, 2, 'a', ['x', 'y', 'z']]
        x = self.eval(dat)
        assert(isinstance(x, dict))
        assert(x['__class__'] == 'List')
        assert(x['value'][0] == 1)
        assert(x['value'][2] == 'a')
        assert(isinstance(x['value'][3], dict))
        assert(x['value'][3]['__class__'] == 'List')
        assert(x['value'][3]['value'][1] == 'y')

    def test_encode_array1(self):
        dat = np.arange(10)/7.0
        x = self.eval(dat)
        print x
        assert(isinstance(x, dict))
        assert(x['__class__'] == 'Array')
        assert(x['__shape__'] == (10, ))
        assert(x['value'][0] == 0)
        assert(len(x['value']) == 10)
        assert(abs(x['value'][1] - 1.4) < 0.2)

    def test_encode_array1(self):
        dat = np.arange(20)/2.0
        dat.shape = (4, 5)
        x = self.eval(dat)
        print x
        assert(isinstance(x, dict))
        assert(x['__class__'] == 'Array')
        assert(x['__shape__'] == (4, 5))
        assert(len(x['value']) == 4)




if __name__ == '__main__':
    nose.main()
