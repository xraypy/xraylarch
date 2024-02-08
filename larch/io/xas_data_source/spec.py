import re
from typing import List, Optional, Iterator
from silx.io.specfile import SpecFile
from . import base


class SpecSingleXasDataSource(base.XasDataSource):
    """SPEC file. Each scan contains 1 XAS spectrum."""

    TYPE = "SPEC"

    def __init__(self, *args, title_regex_pattern: Optional[str] = None, **kw) -> None:
        self.__specfile = None
        if title_regex_pattern:
            title_regex_pattern = re.compile(title_regex_pattern)
        self._title_regex_pattern = title_regex_pattern
        super().__init__(*args, **kw)

    @property
    def _specfile(self):
        if self.__specfile is None:
            self.__specfile = SpecFile(self._filename)
        return self.__specfile

    def get_source_info(self) -> str:
        return f"SPEC: {self._filename}"

    def get_scan(self, scan_name: str) -> Optional[base.XasScan]:
        scan = self._specfile[scan_name]
        description = "\n".join(scan.header)
        return base.XasScan(
            name=scan_name,
            description=description,
            start_time="TODO",
            info=self.get_source_info(),
            labels=scan.labels,
            data=scan.data,
        )

    def get_scan_names(self) -> List[str]:
        return list(self._iter_scan_names())

    def _iter_scan_names(self) -> Iterator[str]:
        for scan in self._specfile:
            if self._title_regex_pattern is not None:
                title = scan.scan_header_dict["S"]
                title = "".join(title.split(" ")[1:])
                if not self._title_regex_pattern.match(title):
                    continue
            yield f"{scan.number}.{scan.order}"
