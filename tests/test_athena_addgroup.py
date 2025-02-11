import numpy.testing
from pathlib import Path
from larch.io import read_ascii, AthenaProject

data_dir = Path(__file__).parent.parent / "examples" / "xafsdata"


def test_add_athena_group():
    a = read_ascii(data_dir / "cu_10k.xmu")
    b = read_ascii(data_dir / "cu_10k.xmu")
    b.mutrans = b.mu[:]
    b.filename = "cu_10k_copy.xmu"
    del b.mu

    p = AthenaProject("x1.prj")
    p.add_group(a)
    p.add_group(b)
    p.save()

    # remove file after test
    Path("x1.prj").unlink(missing_ok=True)


if __name__ == "__main__":
    test_add_athena_group()
