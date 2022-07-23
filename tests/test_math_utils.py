import numpy.testing
from larch.math import utils


def test_remove_dups():
    expected = numpy.array([])
    calculated = utils.remove_dups([])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([1])
    calculated = utils.remove_dups([1])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([1, 1 + 1e-7])
    calculated = utils.remove_dups([1, 1])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([1, 1 + 1e-7, 1 + 2e-7])
    calculated = utils.remove_dups([1, 1, 1])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([1, numpy.nan])
    calculated = utils.remove_dups([1, numpy.nan])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([1, numpy.nan, 1 + 1e-7])
    calculated = utils.remove_dups([1, numpy.nan, 1])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([numpy.nan, 1, 1 + 1e-7])
    calculated = utils.remove_dups([numpy.nan, 1, 1])
    numpy.testing.assert_array_equal(calculated, expected)

    expected = numpy.array([[numpy.nan, 1], [1 + 1e-7, 1 + 2e-7]])
    calculated = utils.remove_dups([[numpy.nan, 1], [1, 1]])
    numpy.testing.assert_array_equal(calculated, expected)
