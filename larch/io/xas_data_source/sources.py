from .nexus import NexusSingleXasDataSource
from .nexus import EsrfSingleXasDataSource
from .nexus import SoleilSingleXasDataSource
from .spec import SpecSingleXasDataSource

_SOURCE_TYPES = {
    "nexus": NexusSingleXasDataSource,
    "esrf": EsrfSingleXasDataSource,
    "soleil": SoleilSingleXasDataSource,
    "spec": SpecSingleXasDataSource,
}


def get_source_type(name):
    return _SOURCE_TYPES[name]
