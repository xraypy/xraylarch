import numpy.testing
from larch.io import read_ascii, AthenaProject


def test_add_athena_group():
    a = read_ascii('../examples/xafsdata/cu_10k.xmu')
    b = read_ascii('../examples/xafsdata/cu_10k.xmu')
    b.mutrans = b.mu[:]
    b.filename = 'cu_10k_copy.xmu'
    del b.mu


    p = AthenaProject('x1.prj')
    p.add_group(a)
    p.add_group(b)
    p.save()
