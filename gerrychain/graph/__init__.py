"""
This module provides a Graph class that
extends the Graph and includes some useful methods
for working with graphs representing geographic data. The class
Graph is the only part of this module that
is intended to be used directly by users of GerryChain.

The other classes and functions in this module are used internally by
GerryChain. These include the geographic manipulation functions
available in `gerrychain.graph.geo`, the adjacency functions
in `gerrychain.graph.adjacency`, and the class
FrozenGraph in the file
`gerrychain.graph.graph`. See the documentation at the top
of those files for more information.
"""

# frm: TODO: Documentation:  Update documentation for graph/__init__.py
#
# It still refers to the old Graphy object extending NetworkX.Graph

from .adjacency import *
from .geo import *
from .graph import *
