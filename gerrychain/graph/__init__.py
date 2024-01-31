"""
This module provides a :class:`~gerrychain.graph.Graph` class that
extends the :class:`networkx.Graph` and includes some useful methods
for working with graphs representing geographic data. The class 
:class:`~gerrychain.graph.Graph` is the only part of this module that
is intended to be used directly by users of GerryChain.

The other classes and functions in this module are used internally by
GerryChain. These include the geographic manipulation functions
available in :mod:`gerrychain.graph.geo`, the adjacency functions
in :mod:`gerrychain.graph.adjacency`, and the class
:class:`~gerrychain.graph.FrozenGraph` in the file
:mod:`gerrychain.graph.graph`. See the documentation at the top
of those files for more information.
"""

from .adjacency import *
from .geo import *
from .graph import *
