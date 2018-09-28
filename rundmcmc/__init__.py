from ._version import get_versions
from .partition import Partition
from .chain import MarkovChain
from .updaters.election import Election

__version__ = get_versions()['version']
del get_versions
