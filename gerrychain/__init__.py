from modulefinder import Module
import warnings

from ._version import get_versions
from .chain import MarkovChain
from .graph import Graph
from .partition import GeographicPartition, Partition
from .updaters.election import Election

# Will need to change this to a logging option later
# It might be good to see how often this happens
warnings.simplefilter("once")

try:
    import geopandas

    # warn about https://github.com/geopandas/geopandas/issues/2199
    if geopandas.options.use_pygeos:
        warnings.warn(
            "GerryChain cannot use GeoPandas when PyGeos is enabled. Disable or "
            "uninstall PyGeos. You can disable PyGeos in GeoPandas by setting "
            "`geopandas.options.use_pygeos = False` before importing your shapefile."
        )
except ModuleNotFoundError:
    pass

__version__ = get_versions()["version"]
del get_versions

from . import _version
__version__ = _version.get_versions()['version']
