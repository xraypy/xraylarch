from typing import Optional
from . import sources
from . import hdf5_utils
from larch import Group


def open_xas_source(filename, **kw):
    with open(filename, "rb") as fh:
        topbytes = fh.read(10)

    if topbytes.startswith(b"\x89HDF\r"):
        creator = hdf5_utils.nexus_creator(filename).lower()
        class_name = None
        if creator == "bliss":
            class_name = "esrf"
        if not class_name:
            source = hdf5_utils.nexus_source(filename).lower()
            if "soleil" in source:
                class_name = "soleil"
        if not class_name:
            instrument = hdf5_utils.nexus_instrument(filename).lower()
            if "soleil" in instrument:
                class_name = "soleil"
        if not class_name:
            class_name = "nexus"
    elif topbytes.startswith(b"#S ") or topbytes.startswith(b"#F "):
        class_name = "spec"
    else:
        raise ValueError(f"Unknown file format: {filename}")
    return sources.get_source_type(class_name)(filename, **kw)


def read_xas_source(filename: str, scan: Optional[str] = None) -> Optional[Group]:
    if scan is None:
        return None
    source = open_xas_source(filename)
    scan = source.get_scan(scan)

    lgroup = Group(
        __name__=f"{source.TYPE} file: {filename}, scan: {scan.name}",
        filename=filename,
        source_info=source.get_source_info(),
        datatype="xas",
    )
    for name, value in scan._asdict().items():
        setattr(lgroup, name, value)
    for name, value in zip(scan.labels, scan.data):
        setattr(lgroup, name, value)
    return lgroup
