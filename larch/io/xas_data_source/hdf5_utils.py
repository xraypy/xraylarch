from contextlib import contextmanager
from typing import Iterator, Optional
import h5py

H5PY_VERSION = h5py.version.version_tuple[:3]
H5PY_HAS_LOCKING = H5PY_VERSION >= (3, 5)


@contextmanager
def open(filename) -> Iterator[h5py.File]:
    kw = {"mode": "r"}
    if H5PY_HAS_LOCKING:
        kw["locking"] = False
    with h5py.File(filename, **kw) as f:
        yield f


def nexus_creator(filename: str) -> str:
    with open(filename) as nxroot:
        return nxroot.attrs.get("creator", "")


def nexus_instrument(filename: str) -> str:
    with open(filename) as nxroot:
        entry = find_nexus_class(nxroot, "NXentry")
        if entry is None:
            return ""

        instrument = find_nexus_class(entry, "NXinstrument")
        if instrument is None:
            return ""

        if "name" in instrument:
            return asstr(instrument["name"][()])
    return ""


def nexus_source(filename: str) -> str:
    with open(filename) as nxroot:
        entry = find_nexus_class(nxroot, "NXentry")
        if entry is None:
            return ""

        source = find_nexus_class(entry, "NXsource")
        if source is None:
            instrument = find_nexus_class(entry, "NXinstrument")
            if instrument is None:
                return ""
            source = find_nexus_class(instrument, "NXsource")
            if source is None:
                return ""

        if "name" in source:
            return asstr(source["name"][()])
    return ""


def asstr(s):
    if isinstance(s, bytes):
        return s.decode()
    return s


def find_nexus_class(parent: h5py.Group, nxclass: str) -> Optional[h5py.Group]:
    for name in parent:
        try:
            child = parent[name]
        except KeyError:
            continue  # broken line
        if asstr(child.attrs.get("NX_class", "")) != nxclass:
            continue
        return child
