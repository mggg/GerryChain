"""
This module provides the Graph class that is used
by GerryChain code.

A Graph object is typically created by first creating
a NetworkX Graph object and then converting it to
a GerryChain Graph object using from_networkx().

Internally, a Graph object contains and embedded graph
object based either on NetworkX or RustworkX.  After
creating a Partition object in GerryChain, the embedded
graph object is converted to be based on RustworkX (for
performance reasons).

The class Graph is the only part of this module that
is intended to be used directly by users of GerryChain.
"""

from .adjacency import *
from .geo import *
from .graph import *
