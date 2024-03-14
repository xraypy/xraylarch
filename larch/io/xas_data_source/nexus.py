import re
from contextlib import contextmanager
from typing import Iterator, List, Optional, Tuple
import numpy
import h5py
from . import base
from . import hdf5_utils


class NexusSingleXasDataSource(base.XasDataSource):
    """NeXus compliant HDF5 file. Each NXentry contains 1 XAS spectrum."""

    TYPE = "HDF5-NEXUS"

    def __init__(
        self,
        filename: str,
        title_regex_pattern: Optional[str] = None,
        counter_group: Optional[str] = None,
        **kw,
    ) -> None:
        self._nxroot = None
        if title_regex_pattern:
            title_regex_pattern = re.compile(title_regex_pattern)
        self._title_regex_pattern = title_regex_pattern
        self._counter_group = counter_group
        self._instrument = None
        super().__init__(filename, **kw)

    def get_source_info(self) -> str:
        return f"HDF5: {self._filename}"

    def get_scan(self, scan_name: str) -> Optional[base.XasScan]:
        with self._open() as nxroot:
            scan = nxroot[scan_name]
            datasets = sorted(self._iter_datasets(scan), key=lambda tpl: tpl[0])
            if datasets:
                labels, data = zip(*datasets)
            else:
                labels = list()
                data = list()
            description = self._get_string(scan, "title")
            if not description:
                description = scan_name
            start_time = self._get_string(scan, "start_time")
            return base.XasScan(
                name=scan_name,
                description=description,
                start_time=start_time,
                info=description,
                labels=list(labels),
                data=numpy.asarray(data),
            )

    def get_scan_names(self) -> List[str]:
        return list(self._iter_scan_names())

    def _iter_scan_names(self) -> Iterator[str]:
        with self._open() as nxroot:
            for name in nxroot["/"]:  # index at "/" to preserve order
                try:
                    scan = nxroot[name]
                except KeyError:
                    continue  # broken link
                if self._title_regex_pattern is not None:
                    title = self._get_string(scan, "title")
                    if not self._title_regex_pattern.match(title):
                        continue
                yield name

    @contextmanager
    def _open(self) -> Iterator[h5py.File]:
        """Re-entrant context to get access to the HDF5 file"""
        if self._nxroot is not None:
            yield self._nxroot
            return
        with hdf5_utils.open(self._filename) as nxroot:
            self._nxroot = nxroot
            try:
                yield nxroot
            finally:
                self._nxroot = None

    def _iter_datasets(self, scan: h5py.Group) -> Iterator[Tuple[str, h5py.Dataset]]:
        if self._counter_group:
            yield from self._iter_counter_group(scan)
        else:
            yield from self._iter_instrument_group(scan)

    def _iter_counter_group(
        self, scan: h5py.Group
    ) -> Iterator[Tuple[str, h5py.Dataset]]:
        try:
            counter_group = scan[self._counter_group]
        except KeyError:
            return  # broken link or not existing
        for name in counter_group:
            try:
                dset = counter_group[name]
            except KeyError:
                continue  # broken link
            if not hasattr(dset, "ndim"):
                continue
            if dset.ndim == 1:
                yield name, dset

    def _iter_instrument_group(
        self, scan: h5py.Group
    ) -> Iterator[Tuple[str, h5py.Dataset]]:
        instrument = self._get_instrument(scan)
        if instrument is None:
            return
        for name in instrument:
            try:
                detector = instrument[name]
            except KeyError:
                continue  # broken link
            nxclass = detector.attrs.get("NX_class")
            if nxclass not in ("NXdetector", "NXpositioner"):
                continue
            try:
                if nxclass == "NXpositioner":
                    dset = detector["value"]
                else:
                    dset = detector["data"]
            except KeyError:
                continue  # no data
            if dset.ndim == 1:
                yield name, dset

    def _get_instrument(self, scan: h5py.Group) -> Optional[h5py.Group]:
        if self._instrument:
            return scan[self._instrument]
        instrument = hdf5_utils.find_nexus_class(scan, "NXinstrument")
        if instrument is not None:
            self._instrument = instrument.name.split("/")[-1]
        return instrument

    def _get_string(self, group: h5py.Group, name) -> str:
        try:
            s = group[name][()]
        except KeyError:
            return ""
        return hdf5_utils.asstr(s)


class EsrfSingleXasDataSource(NexusSingleXasDataSource):
    TYPE = "HDF5-NEXUS-ESRF"

    def __init__(self, filename: str, **kw) -> None:
        kw.setdefault("counter_group", "measurement")
        super().__init__(filename, **kw)


class SoleilSingleXasDataSource(NexusSingleXasDataSource):
    TYPE = "HDF5-NEXUS-SOLEIL"

    def __init__(self, filename: str, **kw) -> None:
        kw.setdefault("counter_group", "scan_data")
        super().__init__(filename, **kw)
