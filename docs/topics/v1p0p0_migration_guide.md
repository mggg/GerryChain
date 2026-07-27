# Migration Guide for GerryChain v1.0.0

This guide will help you understand what you need to change in your "legacy" GerryChain code so that it can run in the v1.0.0 release.

## Table of Contents
* [Primary Benefit of GerryChain v1.0.0 for Legacy Users](#primary-benefit-of-gerrychain-v100-for-legacy-users)
    * [ Minimizing the Impact on Legacy Code](#minimizing-the-impact-on-legacy-code)
        * [Creating a Graph to use in your Partition](#creating-a-graph-to-use-in-your-partition)
        * [Changes to Accessing and Setting Node and Edge Data](#changes-to-accessing-and-setting-node-and-edge-data)
        * [Running a MarkovChain()](#running-a-markovchain)
        * [Analyzing Data after running a MarkovChain()](#analyzing-data-after-running-a-markovchain)
            * [Translating node_ids and edge_ids after running a MarkovChain()](#translating-node_ids-and-edge_ids-after-running-a-markovchain)
    * [Node IDs and Edge IDs - a deep dive...](#node-ids-and-edge-ids---a-deep-dive)

## Primary Benefit of GerryChain v1.0.0 for Legacy Users

The primary benefit of the v1.0.0 release for legacy users 
is a significant performance boost: about 2X on large graphs.

This performance boost was realized by changing the underlying graph engine from NetworkX to RustworkX - RustworkX is faster.

There are additional enhancements in v1.0.0 that 
this guide will not address.  This guide will
focus on what you need to do to get your legacy 
code working.

To provide some context for what follows, the 
primary change that affects legacy code is that
the GerryChain.Graph object is no longer a 
subclass of NetworkX.Graph, but is instead a
new class that wraps the underlying graph engine.
This allowed us to provide a single interface to 
user code that could be implemented under 
the covers with either a NetworkX.Graph object 
or a RustworkX.PyGraph object.

To the extent possible the functions exposed by
the new GerryChain.Graph object are the same as
those exposed by the old NetworkX.Graph based
graph object - details below.

## Minimizing the Impact on Legacy Code

The new GerryChain.Graph object supports most
but not all of the functionality of the old
NetworkX based graph object, so most of the 
code to manipulate your graph will run unchanged,
but some changes will be required, in particular
to set and access node and edge data.  More on 
this below.

We crafted the interface 
of the new Graph object to be close to the same 
as that of the old Graph object.  Functions that were
inherited from NetworkX that were most commonly used by 
legacy code have been implemented as explicit 
functions of the new Graph object, so that 
legacy code would run unchanged.

Examples of formerly inherited functions that are 
now explicit functions are: 

* degree() 
* neighbors()

In addition, those functions that had been added to 
the previous GerryChain.Graph object such as:

* Graph.from_json(...)
* my_gc_graph.to_json(...)
* Graph.from_file(...)
* Graph.from_geodataframe(...)
* etc.

have been implemented for the new Gerrychain.Graph object, 
to avoid requiring changes in legacy code.

### Creating a Graph to use in your Partition

There are two ways to create a graph that you can 
use in your Partition object:

1. Creating a NetworkX.Graph object, making
whatever modifications are needed before
running a chain, and then
using that NetworkX.Graph object to create your
Partition object.

2. Creating a GerryChain.Graph object directly,
and then making whatever modifications are
needed to that graph object and then using that
GerryChain.Graph object to create your Partition
object.

Approach #1 is the most compatible with previous
(legacy) workflows since, prior to release 1.0.0, 
GerryChain treated the `Graph` class as a  proper
subclass of the NetworkX `Graph` class.

Your code in this case would look something
like:

```python
    import networkx
    from gerrychain import Graph

    my_networkx_graph = networkx.Graph()

    ... code to create your NetworkX graph ...

    ... create a Partition using my_networkx_graph ...
```

However, it is often not possible (or convenient) 
to restructure your code to just use NetworkX
functionality to build your graph.  For instance,
you might have code that creates a graph from
JSON with:

```python
    my_graph = Graph.from_json(...)
```
or 

```python
    my_graph = Graph.from_geodataframe(...)
```
In these cases, any modifications to your graph
needed before running a chain will need to be
done using the new GerryChain.Graph object.
So your code would look something like:

```python
    from gerrychain import Graph

    my_gerrychain_graph = \
        Graph.from_json(...)

    ... code to modify your graph ...

    ... create a Partition using my_gerrychain_graph ...
```

### Changes to Accessing and Setting Node and Edge Data

As stated above, the new GerryChain Graph object no longer
inherits from NetworkX.Graph, and instead wraps
either a NetworkX.Graph or a RustworkX.PyGraph.

As a result, the way to access and set node and edge data
has changed.

If your code accesses or updates the data associated with nodes 
then it probably contains code that looks something
like this:
```python

    my_graph.nodes[node_id]["<attr_name>"] = new_value

    node_attr_value = mygraph.nodes[node_id]["<attr_name>"]
```
In v1.0.0, this code will need to be changed to be:

```python
    my_graph.node_data(node_id)["<attr_name>"] = new_value

    node_attr_value = mygraph.node_data(node_id)["<attr_name>"]

```

The needed change is a simple change in 
syntax - "node_data" instead of "nodes" and 
parentheses instead of square-brackets.

If your code accesses or updates the data associated with edges 
then it probably contains code that looks something
like this:

```python
    my_graph.edges[node1_id, node2_id]["<attr_name>"] = new_value

    edge_attr_value = my_graph.edges[node1_id, node2_id]["<attr_name>"]
```

In v1.0.0, this code will need to be changed to be:

```python
    # Get an edge_id given the two nodes in the edge
    my_edge_id = \
        Graph.get_edge_id_from_edge((node1_id, node2_id))

    my_graph.edge_data(my_edge_id)["<attr_name>"] = new_value

    edge_attr_value = my_graph.edge_data(my_edge_id)["<attr_name>"]
```

The important change here is that you need to obtain the 
edge_id before calling my_graph.edge_data(edge_id).  In NetworkX
an edge_id is a tuple of node_ids, but in RustworkX an edge_id
is an integer.  

Note that the new GerryChain.Graph object also provides a way
to obtain the node_ids associated with an edge:

```python
    edge_node_ids = my_graph.get_edge_from_edge_id(my_edge_id)
    
    node1_id = edge_node_ids[0]
    node2_id = edge_node_ids[1]
```

### Running a MarkovChain()

In most cases, there will be no need to change any legacy
code in order to run a MarkovChain() in v1.0.0.

The code that creates a Partition object will convert the
graph provided into a RustworkX.PyGraph automatically and
all of the internal code that runs when running a MarkovChain()
has been updated to work with the RustworkX.PyGraph object.

The exception to this is if the legacy code contains custom
code for updaters.  Since any such code will operate on a
GerryChain.Graph object that is wrapped around a RustworkX.PyGraph
object, that code will need to be aware of the fact that 
node_ids and edge_ids will be different from those in the 
original NetworkX.Graph object used to create the Partition 
object.

Another concern for such code is the use of subgraphs.
In RustworkX, the node_ids and edge_ids for a subgraph are 
different from those of the parent graph, so again, any code
involving subgraphs that runs when doing a MarkovChain()
will need to be aware of the fact that node_ids and edge_ids
are different from the parent graph.

There is a more detailed discussion of node_ids and edge_ids
later in this guide.

### Analyzing Data after running a MarkovChain()

After running a MarkovChain(), legacy code often 
uses NetworkX functionality - to extract data from the
graph and/or partition or to plot the results.
A function has been provided to convert the embedded
RustworkX.PyGraph back to become a NetworkX.Graph
object with all of the data preserved (the 
`to_networkx_graph()` function, specifically).  

So, if your legacy code uses NetworkX functionality 
to post-process the data after running a MarkovChain(),
or perhaps to plot results,
then you probably want to convert the graph associated
with your Partition object to be a NetworkX.Graph 
object:

```python
    my_gc_graph = my_partition.graph
    
    my_networkx_graph = my_gc_graph.to_networkx_graph()

    ... do post-processing using my_networkx_graph ...
```

Note that all node_data and edge_data that was 
generated during the procssing of the MarkovChain()
is preserved in the generated NetworkX.Graph object.

For many legacy projects, this is all that will be required.
However, if your post MarkovChain() processing depends on 
the original NetworkX.Graph node_ids and/or edge_ids, then
you have work to do, because the node_ids and edge_ids that
are stored in the chain are RustworkX.PyGraph node_ids and
edge_ids.

You will need to translate those node_ids and edge_ids back
to the original NetworkX.Graph node_ids and edge_ids.  

We have provided routines to help you do this translation.
Those routines are discussed below.

#### Translating node_ids and edge_ids after running a MarkovChain()

After running MarkovChain() results can be 
stored in several places:

* In the data associated with the nodes or the
    edges in the graph, or

* In the data associated with a partition - for 
    instance in the assignments of nodes to a 
    district or in the attributes of the partition 
    (created by updaters).

As stated above, the graph used in the MarkovChain()
processing is a RustworkX.PyGraph object, and 
the node_ids and the edge_ids for that graph are NOT
necessarily the same as the node_ids and the edge_ids (pair 
of node_ids) that were used to build the graph.

So, if your code depends on the original
NetworkX.Graph node_ids and edge_ids,
you will need to translate the node_ids and edge_ids
back into what they were in the original NetworkX.Graph
object.  There are routines to do this:
```python
    def original_nx_node_id_for_internal_node_id(
      self, 
      internal_node_id: Any
    ) -> Any:

    def original_nx_node_ids_for_set(
      self, 
      set_of_node_ids: set[Any]
    ) -> Any:

    def original_nx_node_ids_for_list(
      self, 
      list_of_node_ids: list[Any]
    ) -> list[Any]:
```
which are attached as methods of the new GerryChain Graph 
object and can thus be invoked as:
```python
    my_graph.original_nx_node_id_for_internal_node_id(internal_node_id)
    my_graph.original_nx_node_ids_for_set(set_of_node_ids)
    my_graph.original_nx_node_ids_for_list(list_of_node_ids)
```
> Note: the "internal_node_id" in the above routines refers
> to the RustworkX.PyGraph node_id as do the sets and lists
> of node_ids.

If you wish to extract NetworkX.Graph edges then you will need
a tuple of node_ids.  First you need to get the
RustworkX.PyGraph node_ids for an edge, given its
RustworkX edge_id (an integer), and then you need
to use the `original_nx_node_id_for_internal_node_id()`
routine to get the original NX node_ids for the edge.  The routines to do this are:
```python
    def get_edge_from_edge_id(
      self, 
      edge_id: Any
    ) -> tuple[Any, Any]:
    def original_nx_node_id_for_internal_node_id(
      self, 
      internal_node_id: Any
    ) -> Any:
```
So, to extract the NetworkX.Graph edge for a specific edge from a new GerryChain Graph object that embeds a RustworkX.PyGraph object, you would need to do: 
```python
    rx_edge = my_graph.get_edge_from_edge_id(my_edge_id)
    nx_node_id_1 = (
      my_graph.original_nx_node_id_for_internal_node_id(rx_edge[0]
    )
    nx_node_id_2 = (
      my_graph.original_nx_node_id_for_internal_node_id(rx_edge[1]
    )
    my_nx_edge = (nx_node_id_1, nx_node_id_2)
```

## Node IDs and Edge IDs - a deep dive...

If you have written custom code, (for instance, a 
custom updater or a spanning function or a bipartition
function) then you need to understand how node_ids
and edge_ids have changed.

In NetworkX a node_id can be any hashable Python object
other than `None` (an integer, a string, a tuple, etc.).
In RustworkX a node_id is always
an integer, and even more, the set of node_ids is always
a sequential list of integers starting at 0 with no 
gaps.

In NetworkX an edge is a tuple of node_ids and an edge_id is the ***same*** tuple of node_ids,
so there is no difference between an edge and an edge_id.
However, in RustworkX while edges are still
a tuple of node_ids, an edge_id is an integer.
So an edge and an edge_id are different.

This creates some interesting challenges...

As discussed above, the new codebase converts 
NetworkX based graphs to be graphs based on RustworkX.
The codebase also maintains a mapping from NetworkX 
node_ids to RustworkX node_ids and vice versa.

So, legacy code that involves node_ids needs to be 
aware of whether it is manipulating "original" NetworkX
node_ids or "internal" RustworkX node_ids used during MarkovChain()
calculations.  This is relatively straight-forward - you
just need to know which kind of node_id you need and 
perhaps convert from one kind to the other.

Edges and edge_ids are more challenging, because you 
need to determine whether the "edge" in your legacy
code is referring to a tuple (you want to get at 
the node_ids for the edge) or to the ID for the edge
(needed when you want to get data associated with 
the edge).  There are routines to get an edge (tuple)
from an edge_id and vice versa.

Remember that before running MarkovChain(), or more
accurately, until you create a Partition object, the
embedded graph is still NetworkX based and so you
can probably be clever and continue to use NetworkX
to deal with edges - one way to do this is to ask
to get direct access to the embedded NetworkX graph
and operate directly on the embedded graph.  The
routine to gain access to the embedded NetworkX.Graph
object is:
```python
    def get_nx_graph(self) -> networkx.Graph:
```
The routines to go back and forth from edge_ids 
to/from edges are:
```python
    def get_edge_from_edge_id(self, edge_id: Any) -> tuple[Any, Any]:

    def get_edge_id_from_edge(self, edge: tuple[Any, Any]) -> Any:
```
Another issue is iterating over nodes and edges.
The routines to do this are:
```python
    def edge_indices(self) -> set[Any]:  # edge_ids

    def edges(self) -> set[tuple[Any, Any]]:

    def node_indices(self) -> set[Any] 

    def nodes(self) -> list[Any]:
```

**Caution:**  In pre v1.0.0 code 
graph.nodes[node_id] would return a
data dict for the data associated with 
the given node_id.  However, in v1.0.0 this
code will interpret the node_id as an index
into the list of nodes defined for the
graph.  This might end up being a subtle and 
hence hard bug to find, so please search
your legacy code for any uses of 
graph.nodes[node_id]...

Note that node_indices and nodes return the same thing - except
that one is a list and the other a set.  The nodes function was
retained because legacy code uses it a lot to iterate over the graph.

The edge_indices function returns edge_ids which for a graph
with an embedded NetworkX graph will return tuples of 
node_ids and for a graph with an embedded RustworkX graph 
will return integers.  The edges function always returns tuples
of node_ids but for NetworkX the node_ids will be NetworkX node_ids
which do not have to be integers while for RustworkX the node_ids
will always be integers.

The last and most important issue involving node_ids and 
edge_ids is subgraphs.  We have noted already that node_ids 
and edge_ids in RustworkX are always sequential integers with no
gaps starting at 0.  This is one of the things that makes
it possible for RustworkX to be faster than NetworkX.  However,
it also means that node_ids and edge_ids in RustworkX 
subgraphs are also sequential integers with no gaps starting
at 0 - which means that the node_ids for the same node might 
be different in a subgraph containing that node than in that 
same node's id in the parent graph.  This can cause some 
headaches pretty big headaches for anyone working with them, 
but we anticipate that most users will not need to deal with 
this pain-point.

There are two major issues that result from subgraphs having
new node_ids and edge_ids:

1. Results of computations performed on subgraphs that contain
     node_id or edge_id information will need to be converted
     to refer to the corresponding node_ids and/or edge_ids in 
     the parent graph.  For instance, if a subroutine operates
     on a subgraph and returns flips, then the node_ids in the
     flips will need to be converted back to be parent graph 
     node_ids.

2. There is a danger that a computation mixes parent graph
     node/edge_ids and subgraph node/edge_ids.  To guard 
     against this in the new codebase, calls on graph.subgraph()
     are always made as actual parameters to a function call.
     This guarantees that the subgraph IDs cannot be used
     in the caller's context.  In addition, as mentioned
     above in #1, it is the responsibility of the called 
     function to convert any IDs in the return value to be 
     those that are appropriate for the parent graph.

To make it possible to translate from a subgraph back to
the parent, whenever a subgraph is created, a mapping 
(dictionary) is created that converts the subgraph node_id 
to the parent graph's node_id.  This is hidden slightly
from the public interface, but is accessible as 
`_node_id_to_parent_node_id_map` and two routines exist to 
make it convenient to convert flips and sets of nodes back 
to the node_ids appropriate for the parent graph:
```python
    def translate_subgraph_node_ids_for_flips(
      self, 
      flips: dict[Any, int]
    ) -> dict[Any, int]:

    def translate_subgraph_node_ids_for_set_of_nodes(
      self, 
      set_of_nodes: set[Any]
    ) -> set[Any]:
```
