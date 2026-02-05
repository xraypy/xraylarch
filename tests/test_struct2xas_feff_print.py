#!/usr/bin/env python
"""Test feff_print parameter in Struct2XAS.make_input_feff()

Tests the configurable PRINT card values feature added to struct2xas.py.
"""

import re
import pytest
import tempfile
from pathlib import Path

from larch.xrd.struct2xas import Struct2XAS

toppath = Path(__file__).parent.parent
structpath = toppath / "examples" / "structuredata" / "struct2xas"
CIF_FILE = structpath / "ZnO_mp-2133.cif"


@pytest.fixture
def cif_file():
    """Return path to test CIF file."""
    if not CIF_FILE.exists():
        pytest.skip(f"Test CIF file not found: {CIF_FILE}")
    return CIF_FILE


def extract_print_values(feff_inp_path):
    """Extract PRINT card values from feff.inp file."""
    content = Path(feff_inp_path).read_text()
    match = re.search(
        r"^PRINT\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
        content,
        re.MULTILINE,
    )
    if not match:
        return None
    return [int(match.group(i)) for i in range(1, 7)]


def test_default_feff_print_has_ff2chi_3(cif_file):
    """Default feff_print should be [1, 0, 0, 0, 0, 3] matching structure2feff.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mat = Struct2XAS(file=str(cif_file), abs_atom="Zn")
        mat.set_abs_site(0)
        mat.make_input_feff(radius=6.0, parent_path=tmpdir)

        feff_files = list(Path(tmpdir).glob("**/feff.inp"))
        assert len(feff_files) == 1, "feff.inp should be generated"

        values = extract_print_values(feff_files[0])
        assert values is not None, "PRINT card should be present"
        assert values == [1, 0, 0, 0, 0, 3], f"Expected [1,0,0,0,0,3], got {values}"


def test_custom_feff_print_values(cif_file):
    """Custom feff_print values should be written to feff.inp."""
    custom_print = [1, 1, 1, 1, 1, 2]

    with tempfile.TemporaryDirectory() as tmpdir:
        mat = Struct2XAS(file=str(cif_file), abs_atom="Zn")
        mat.set_abs_site(0)
        mat.make_input_feff(radius=6.0, parent_path=tmpdir, feff_print=custom_print)

        feff_files = list(Path(tmpdir).glob("**/feff.inp"))
        assert len(feff_files) == 1

        values = extract_print_values(feff_files[0])
        assert values == custom_print, f"Expected {custom_print}, got {values}"


def test_feff_print_old_behavior_recoverable(cif_file):
    """Old behavior (ff2chi=0) should be recoverable via feff_print parameter."""
    old_print = [1, 0, 0, 0, 0, 0]

    with tempfile.TemporaryDirectory() as tmpdir:
        mat = Struct2XAS(file=str(cif_file), abs_atom="Zn")
        mat.set_abs_site(0)
        mat.make_input_feff(radius=6.0, parent_path=tmpdir, feff_print=old_print)

        feff_files = list(Path(tmpdir).glob("**/feff.inp"))
        assert len(feff_files) == 1

        values = extract_print_values(feff_files[0])
        assert values == old_print, f"Expected {old_print}, got {values}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
