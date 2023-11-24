import numpy.testing
from larch.math import utils

tiny=1.e-6

def test_remove_dups():
    expected = numpy.array([])
    calculated = utils.remove_dups([])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([1])
    calculated = utils.remove_dups([1])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([1, 1 + tiny])
    calculated = utils.remove_dups([1, 1])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([1, 1 + tiny, 1 + 2*tiny])
    calculated = utils.remove_dups([1, 1, 1])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([1, numpy.nan])
    calculated = utils.remove_dups([1, numpy.nan])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([1, numpy.nan, 1 + tiny])
    calculated = utils.remove_dups([1, numpy.nan, 1])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([numpy.nan, 1, 1 + tiny])
    calculated = utils.remove_dups([numpy.nan, 1, 1])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([numpy.nan, 1, 1 + tiny, 1 + 2*tiny])
    calculated = utils.remove_dups([[numpy.nan, 1], [1, 1]])
    numpy.testing.assert_allclose(calculated, expected, atol=tiny/4)
