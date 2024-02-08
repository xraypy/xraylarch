from typing import NamedTuple, List, Optional
from numpy.typing import ArrayLike


class XasScan(NamedTuple):
    name: str
    description: str
    info: str
    start_time: str
    labels: List[str]
    data: ArrayLike


class XasDataSource:
    TYPE = NotImplemented

    def __init__(self, filename: str) -> None:
        self._filename = filename

    def get_source_info(self) -> str:
        raise NotImplementedError

    def get_scan(self, scan_name: str) -> Optional[XasScan]:
        raise NotImplementedError

    def get_scan_names(self) -> List[str]:
        raise NotImplementedError

    def get_sorted_scan_names(self) -> List[str]:
        scan_names = self.get_scan_names()
        return sorted(scan_names, key=lambda s: float(s) if s.isdigit() else s)
