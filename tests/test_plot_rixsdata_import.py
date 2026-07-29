"""Regression tests for a bug where merely importing larch's non-wx,
matplotlib-based RIXS plotting tools (e.g. in a Jupyter notebook) pulled in
the entire wx GUI subsystem (larch.wxlib) as a side effect. That subsystem
forces IPython's "%gui wx" event-loop hook at import time, which can
deadlock a real Jupyter kernel (its asyncio/zmq event loop fights wx's).

larch.plot is documented as "independent of the Wx GUI" and intended for
standalone scripts and Jupyter notebooks, so importing it (or anything
under it, like larch.plot.plot_rixsdata) must not import larch.wxlib.

These run each check in a subprocess so that a clean sys.modules is
guaranteed, regardless of import side effects from other tests in the
same pytest session.
"""
import subprocess
import sys

import pytest

pytest.importorskip("wx")  # the bug only exists when wxPython is installed


def _run(code):
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"subprocess failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    return result.stdout


def test_import_plot_rixsdata_does_not_load_wxlib():
    """importing the RIXS io/plot modules must not pull in larch.wxlib"""
    code = (
        "import sys\n"
        "from larch.io.specfile_reader import DataSourceSpecH5\n"
        "from larch.io.rixsdata import RixsData\n"
        "from larch.plot.plot_rixsdata import plot_rixs, plot_rixs_cuts\n"
        "from larch.io.rixs_esrf_fame import (get_rixs_bm16, save_rixs,\n"
        "                                     search_samples, get_rixs_filenames)\n"
        "assert 'larch.wxlib' not in sys.modules, 'larch.wxlib was imported eagerly'\n"
        "print('OK')\n"
    )
    out = _run(code)
    assert "OK" in out


def test_import_larch_plot_does_not_load_wxlib():
    """plain `import larch.plot` alone must not pull in larch.wxlib"""
    code = (
        "import sys\n"
        "import larch.plot\n"
        "assert 'larch.wxlib' not in sys.modules, 'larch.wxlib was imported eagerly'\n"
        "print('OK')\n"
    )
    out = _run(code)
    assert "OK" in out


def test_import_plot_rixsdata_does_not_trigger_ipython_gui_hook():
    """importing the RIXS io/plot modules must not force IPython's
    '%gui wx' event-loop integration, even when running "inside" IPython
    (simulated here via a fake get_ipython()). Installing that hook is
    what deadlocked a real Jupyter kernel before this was fixed.
    """
    pytest.importorskip("IPython")
    code = (
        "import IPython\n"
        "calls = []\n"
        "class FakeMagic:\n"
        "    def __call__(self, name):\n"
        "        calls.append(name)\n"
        "class FakeIPython:\n"
        "    def find_magic(self, name):\n"
        "        return FakeMagic()\n"
        "IPython.get_ipython = lambda: FakeIPython()\n"
        "\n"
        "from larch.io.specfile_reader import DataSourceSpecH5\n"
        "from larch.io.rixsdata import RixsData\n"
        "from larch.plot.plot_rixsdata import plot_rixs, plot_rixs_cuts\n"
        "from larch.io.rixs_esrf_fame import (get_rixs_bm16, save_rixs,\n"
        "                                     search_samples, get_rixs_filenames)\n"
        "assert calls == [], f'IPython gui hook was installed: {calls}'\n"
        "print('OK')\n"
    )
    out = _run(code)
    assert "OK" in out


if __name__ == "__main__":
    test_import_plot_rixsdata_does_not_load_wxlib()
    test_import_larch_plot_does_not_load_wxlib()
    test_import_plot_rixsdata_does_not_trigger_ipython_gui_hook()
