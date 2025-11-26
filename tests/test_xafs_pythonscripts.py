# this is meant to eventually replace test_larchexamples_xafs
#
#
import os
from pathlib import Path
from asteval import Interpreter
from pyshortcuts.utils import read_textfile

basedir = Path(__file__).parent.parent.resolve()

os.environ['XRAYLARCH_NO_PLOT'] = '1'

def run_in_asteval(pathobj):
    aeval = Interpreter(with_import=True, with_importfrom=True)

    scriptname = pathobj.name
    os.chdir(pathobj.absolute().parent)

    text = read_textfile(scriptname)
    aeval.run(text)

    assert len(aeval.error) == 0
    return aeval

def test_autobk_01():
    script = Path(basedir, 'examples', 'xafs', 'doc_autobk_01.py')
    out = run_in_asteval(script)
    assert len(out.error) == 0
    cu = out.symtable['cu']
    assert cu.e0 > 8950.
    assert cu.e0 < 9010.
    assert len(cu.k) > 200
    assert max(cu.chi) < 2.0


def test_autobk_02():
    script = Path(basedir, 'examples', 'xafs', 'doc_autobk_02.py')
    out = run_in_asteval(script)
    assert len(out.error) == 0

    dat = out.symtable['dat']
    assert dat.e0 > 10000.0
    assert len(dat.k) > 200
    assert max(dat.chi) < 2.0

def test_autobk_03():
    script = Path(basedir, 'examples', 'xafs', 'doc_autobk_03.py')
    out = run_in_asteval(script)
    assert len(out.error) == 0

    dat = out.symtable['dat']
    assert dat.e0 > 11000.0
    assert len(dat.k) > 200

def test_preedge_01():
    script = Path(basedir, 'examples', 'xafs', 'pre_edge_01.py')
    out = run_in_asteval(script)
    assert len(out.error) == 0
    dat = out.symtable['dat']
    assert dat.e0 > 7110
    assert dat.e0 < 7150
    assert len(dat.norm) > 200

def test_preedge_02():
    script = Path(basedir, 'examples', 'xafs', 'pre_edge_01.py')
    out = run_in_asteval(script)
    assert len(out.error) == 0
    dat = out.symtable['dat']
    assert dat.e0 > 7110
    assert dat.e0 < 7150
    assert len(dat.pre_edge) > 200

def test_mback_01():
    script = Path(basedir, 'examples', 'xafs', 'mback_01.py')
    out = run_in_asteval(script)
    assert len(out.error) == 0
    dat = out.symtable['dat']
    assert dat.e0 > 8950
    assert dat.e0 < 9040
    assert len(dat.fpp) > 200

def test_mback_02():
    script = Path(basedir, 'examples', 'xafs', 'mback_02.py')
    out = run_in_asteval(script)
    assert len(out.error) == 0
    dat = out.symtable['dat']
    assert dat.e0 > 3900
    assert dat.e0 < 4000
    assert len(dat.norm) > 200
    assert len(dat.norm_poly) > 200

if __name__ == '__main__':
    test_autobk_01()
