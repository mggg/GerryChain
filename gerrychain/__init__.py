from ._version import get_versions
from .chain import MarkovChain
from .graph import Graph
from .partition import GeographicPartition, Partition
from .updaters.election import Election

import geopandas

# warn about https://github.com/geopandas/geopandas/issues/2199
if geopandas.options.use_pygeos:
    raise ImportError(
        "GerryChain cannot use GeoPandas when PyGeos is enabled. Disable or "
        "uninstall PyGeos. You can disable PyGeos in GeoPandas by setting "
        "`geopandas.options.use_pygeos = False` before importing your shapefile."
    )

__version__ = get_versions()['version']
del get_versions
