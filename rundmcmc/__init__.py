from .__main__ import main
from ._version import get_versions

__version__ = get_versions()['version']
del get_versions
