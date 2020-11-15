#!/usr/bin/env python
""" Tests of Larch Scripts  """

from utils import TestCase

class TestScripts(TestCase):
    '''test read_ascii() for all example xafsdata'''
    def test_read_ascii(self):
        # self.symtable.set_symbol('testdir',  os.getcwd())
        self.runscript('read_ascii.lar', dirname='larch_scripts')
        assert(len(self.session.get_errors()) == 0)

        actual = self.session.get_symbol('results')
        expected = self.session.get_symbol('expected')
        print("actual ", actual)
        print("expected ", expected)
        
        for fname, ncol, nrow, labels in expected:
            acol, arow, alabs = actual[fname]
            assert(acol == ncol)
            assert(arow == nrow)
            assert(alabs == labels)

