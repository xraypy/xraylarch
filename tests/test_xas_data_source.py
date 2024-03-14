import pathlib
import datetime
from typing import Optional

import h5py
import numpy

from larch.io.xas_data_source import open_xas_source
from larch.io.xas_data_source import read_xas_source


def test_xas_data_source_spec(tmp_path):
    filename = tmp_path / "scans.spec"

    energy1 = numpy.linspace(7, 7.1, 10)
    energy2 = numpy.linspace(7, 7.1, 20)
    mu1 = numpy.random.uniform(low=-1, high=2, size=10)
    mu2 = numpy.random.uniform(low=-1, high=2, size=20)

    _save_spec_scan(filename, "escan", energy=energy1, mu=mu1)
    _save_spec_scan(
        filename,
        "ascan",
        samx=numpy.linspace(1, 2, 10),
        diode1=numpy.random.uniform(size=10),
    )
    _save_spec_scan(filename, "escan", energy=energy2, mu=mu2)

    source = open_xas_source(str(filename), title_regex_pattern="escan")
    assert source.TYPE == "SPEC"
    assert source.get_source_info() == f"SPEC: {filename}"
    assert source.get_scan_names() == ["1.1", "3.1"]

    scan1 = source.get_scan("1.1")
    assert scan1.labels == ["energy", "mu"]
    numpy.testing.assert_array_equal(energy1, scan1.data[0])
    numpy.testing.assert_array_equal(mu1, scan1.data[1])

    scan2 = source.get_scan("3.1")
    assert scan2.labels == ["energy", "mu"]
    numpy.testing.assert_array_equal(energy2, scan2.data[0])
    numpy.testing.assert_array_equal(mu2, scan2.data[1])

    scan1 = read_xas_source(str(filename), "1.1")
    numpy.testing.assert_array_equal(energy1, scan1.energy)
    numpy.testing.assert_array_equal(mu1, scan1.mu)

    scan2 = read_xas_source(str(filename), "3.1")
    numpy.testing.assert_array_equal(energy2, scan2.energy)
    numpy.testing.assert_array_equal(mu2, scan2.mu)


def test_xas_data_source_esrf(tmp_path):
    filename = tmp_path / "dataset.h5"

    energy1 = numpy.linspace(7, 7.1, 10)
    energy2 = numpy.linspace(7, 7.1, 20)
    mu1 = numpy.random.uniform(low=-1, high=2, size=10)
    mu2 = numpy.random.uniform(low=-1, high=2, size=20)

    _save_nexus_scan(filename, "escan", facility="esrf", energy=energy1, mu=mu1)
    _save_nexus_scan(
        filename,
        "ascan",
        facility="esrf",
        samx=numpy.linspace(1, 2, 10),
        diode1=numpy.random.uniform(size=10),
    )
    _save_nexus_scan(filename, "escan", facility="esrf", energy=energy2, mu=mu2)

    source = open_xas_source(str(filename), title_regex_pattern="escan")
    assert source.TYPE == "HDF5-NEXUS-ESRF"
    assert source.get_source_info() == f"HDF5: {filename}"
    assert source.get_scan_names() == ["1.1", "3.1"]

    scan1 = source.get_scan("1.1")
    assert scan1.labels == ["energy", "mu"]
    numpy.testing.assert_array_equal(energy1, scan1.data[0])
    numpy.testing.assert_array_equal(mu1, scan1.data[1])

    scan2 = source.get_scan("3.1")
    assert scan2.labels == ["energy", "mu"]
    numpy.testing.assert_array_equal(energy2, scan2.data[0])
    numpy.testing.assert_array_equal(mu2, scan2.data[1])

    scan1 = read_xas_source(str(filename), "1.1")
    numpy.testing.assert_array_equal(energy1, scan1.energy)
    numpy.testing.assert_array_equal(mu1, scan1.mu)

    scan2 = read_xas_source(str(filename), "3.1")
    numpy.testing.assert_array_equal(energy2, scan2.energy)
    numpy.testing.assert_array_equal(mu2, scan2.mu)


def test_xas_data_source_soleil(tmp_path):
    filename = tmp_path / "dataset.nxs"

    energy1 = numpy.linspace(7, 7.1, 10)
    energy2 = numpy.linspace(7, 7.1, 20)
    mu1 = numpy.random.uniform(low=-1, high=2, size=10)
    mu2 = numpy.random.uniform(low=-1, high=2, size=20)

    _save_nexus_scan(filename, "escan", facility="soleil", energy=energy1, mu=mu1)
    _save_nexus_scan(
        filename,
        "ascan",
        facility="soleil",
        samx=numpy.linspace(1, 2, 10),
        diode1=numpy.random.uniform(size=10),
    )
    _save_nexus_scan(filename, "escan", facility="soleil", energy=energy2, mu=mu2)

    source = open_xas_source(str(filename), title_regex_pattern="escan")
    assert source.TYPE == "HDF5-NEXUS-SOLEIL"
    assert source.get_source_info() == f"HDF5: {filename}"
    assert source.get_scan_names() == ["exp1", "exp3"]

    scan1 = source.get_scan("exp1")
    assert scan1.labels == ["energy", "mu"]
    numpy.testing.assert_array_equal(energy1, scan1.data[0])
    numpy.testing.assert_array_equal(mu1, scan1.data[1])

    scan2 = source.get_scan("exp3")
    assert scan2.labels == ["energy", "mu"]
    numpy.testing.assert_array_equal(energy2, scan2.data[0])
    numpy.testing.assert_array_equal(mu2, scan2.data[1])

    scan1 = read_xas_source(str(filename), "exp1")
    numpy.testing.assert_array_equal(energy1, scan1.energy)
    numpy.testing.assert_array_equal(mu1, scan1.mu)

    scan2 = read_xas_source(str(filename), "exp3")
    numpy.testing.assert_array_equal(energy2, scan2.energy)
    numpy.testing.assert_array_equal(mu2, scan2.mu)


def test_xas_data_source_nexus(tmp_path):
    filename = tmp_path / "dataset.nxs"

    energy1 = numpy.linspace(7, 7.1, 10)
    energy2 = numpy.linspace(7, 7.1, 20)
    mu1 = numpy.random.uniform(low=-1, high=2, size=10)
    mu2 = numpy.random.uniform(low=-1, high=2, size=20)

    _save_nexus_scan(filename, "escan", energy=energy1, mu=mu1)
    _save_nexus_scan(
        filename,
        "ascan",
        samx=numpy.linspace(1, 2, 10),
        diode1=numpy.random.uniform(size=10),
    )
    _save_nexus_scan(filename, "escan", energy=energy2, mu=mu2)

    source = open_xas_source(str(filename), title_regex_pattern="escan")
    assert source.TYPE == "HDF5-NEXUS"
    assert source.get_source_info() == f"HDF5: {filename}"
    assert source.get_scan_names() == ["scan1", "scan3"]

    scan1 = source.get_scan("scan1")
    assert scan1.labels == ["energy", "mu"]
    numpy.testing.assert_array_equal(energy1, scan1.data[0])
    numpy.testing.assert_array_equal(mu1, scan1.data[1])

    scan2 = source.get_scan("scan3")
    assert scan2.labels == ["energy", "mu"]
    numpy.testing.assert_array_equal(energy2, scan2.data[0])
    numpy.testing.assert_array_equal(mu2, scan2.data[1])

    scan1 = read_xas_source(str(filename), "scan1")
    numpy.testing.assert_array_equal(energy1, scan1.energy)
    numpy.testing.assert_array_equal(mu1, scan1.mu)

    scan2 = read_xas_source(str(filename), "scan3")
    numpy.testing.assert_array_equal(energy2, scan2.energy)
    numpy.testing.assert_array_equal(mu2, scan2.mu)


def _save_spec_scan(filename: pathlib.Path, scan_title: str, **data) -> None:
    date = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")

    header = list()
    if filename.exists():
        with open(filename, "r") as f:
            scan_number = len([None for line in f if line.startswith("#S")]) + 1
    else:
        header += [f"#F {filename}", f"#D {date}"]
        scan_number = 1
    header += [
        "",
        f"#S {scan_number} {scan_title}",
        f"#D {date}",
        f"#N {len(data)}",
        f"#L {'  '.join(list(data))}",
    ]

    array = numpy.array(list(data.values())).T
    with open(filename, "ab") as f:
        numpy.savetxt(f, array, header="\n".join(header), comments="")


def _save_nexus_scan(
    filename: pathlib.Path, scan_title: str, facility: Optional[str] = None, **data
) -> None:
    with h5py.File(filename, "a") as nxroot:
        scan_names = list(nxroot)
        if not scan_names:
            scan_numbers = [0]
            nxroot.attrs["NX_class"] = "NXroot"
            if facility == "esrf":
                nxroot.attrs["creator"] = "Bliss"
        else:
            if facility == "esrf":
                scan_numbers = [int(float(name)) for name in scan_names]
            elif facility == "soleil":
                scan_numbers = [int(name.replace("exp", "")) for name in scan_names]
            else:
                scan_numbers = [int(name.replace("scan", "")) for name in scan_names]

        if facility == "esrf":
            scan_name = f"{max(scan_numbers)+1}.1"
            instrument_name = "instrument"
            source_name = "machine"
            source_info = {
                "type": "Synchrotron X-ray Source",
                "name": "ESRF",
            }
            scan_data_name = "measurement"
            scan_data_type = "NXcollection"
        elif facility == "soleil":
            scan_name = f"exp{max(scan_numbers)+1}"
            instrument_name = "PUMA"
            source_name = "ans-ca-machinestatus"
            source_info = {
                "type": "Synchrotron X-ray Source",
                "probe": "x-ray",
                "name": "SOLEIL",
            }
            scan_data_name = "scan_data"
            scan_data_type = "NXdata"
        else:
            scan_name = f"scan{max(scan_numbers)+1}"
            instrument_name = "instrument"
            source_name = None
            scan_data_name = None
            scan_data_type = None

        nxentry = nxroot.create_group(scan_name)
        nxentry.attrs["NX_class"] = "NXentry"
        nxentry["title"] = scan_title

        if facility == "esrf":
            nxentry["name"] = "ESRF-ID21"
            nxentry["name"].attrs["short_name"] = "ID21"

        nxinstrument = nxentry.create_group(instrument_name)
        nxinstrument.attrs["NX_class"] = "NXinstrument"

        if source_name:
            nxsource = nxinstrument.create_group(source_name)
            nxsource.attrs["NX_class"] = "NXsource"
            for name, value in source_info.items():
                nxsource[name] = value

        if scan_data_name:
            scan_data = nxentry.create_group(scan_data_name)
            scan_data.attrs["NX_class"] = scan_data_type

        for name, value in data.items():
            if name.startswith("sam"):
                nxpositioner = nxinstrument.create_group(name)
                nxpositioner.attrs["NX_class"] = "NXpositioner"
                dset = nxpositioner.create_dataset("value", data=value)
                dset.attrs["units"] = "mm"
            elif name == "energy":
                nxpositioner = nxinstrument.create_group(name)
                nxpositioner.attrs["NX_class"] = "NXpositioner"
                dset = nxpositioner.create_dataset("value", data=value)
                dset.attrs["units"] = "keV"
            else:
                nxdetector = nxinstrument.create_group(name)
                nxdetector.attrs["NX_class"] = "NXdetector"
                dset = nxdetector.create_dataset("data", data=value)
                dset.attrs["units"] = "keV"

            if scan_data_name:
                scan_data[name] = h5py.SoftLink(dset.name)
