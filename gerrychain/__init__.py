from ._version import get_versions
from .chain import MarkovChain
from .graph import Graph
from .partition import GeographicPartition, Partition
from .updaters.election import Election

import geopandas

# mitigate https://github.com/geopandas/geopandas/issues/2199
geopandas.options.use_pygeos = False

__version__ = get_versions()['version']
del get_versions
