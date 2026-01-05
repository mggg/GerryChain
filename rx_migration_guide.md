# DRAFT - Migration Guide for GerryChain Alpha - DRAFT

In order to improve the performance of GerryChain, the graph 
object used when running a MarkovChain() has been changed from
a NetworkX.Graph object to a RustworkX.PyGraph object.  The RustworkX 
graph library is implemented in Rust and is much faster as a result.

This change has also come with a significant refactoring of the
GerryChain.Graph object turning it from a subclass of
NetworkX.Graph to a new class that wraps either a NetworkX.Graph
or a RustworkX.PyGraph object.  This refactoring was done to
allow us to maintain compatibility with legacy code that depends
on NetworkX functionality while still allowing us to take advantage
of the performance benefits of RustworkX.

## Minimizing the impact on legacy code

In order to minimize the changes needed in legacy code, 
several things were done:

* A new GerryChain Graph object (class) was defined that wraps
    an underlying graph object.  This allowed us to craft the 
    interface of the new Graph object to be as close to the 
    same as that of the old Graph object.  Those inherited NetworkX 
    functions that were most commonly used by legacy code
    have been implemented as explicit functions of the new Graph
    object, so the legacy code would run unchanged.

    Examples of formerly inherited functions that are 
    now explicit functions are: degree() and neighbors()

* The new GerryChain Graph object can still created from a 
    a NetworkX Graph object in the same way as the legacy
    code allowed. This should enable legacy users to 
    continue to use NetworkX to build a graph and to then 
    conveniently convert it to become a new Graph object.
    So, if legacy code depends on any NetworkX functionality
    in the creation of the graph to be run through a MarkovChain()
    that has not been implemented as part of the new Graph
    object, then the legacy code can opt to just create
    a pure NetworkX graph and then hand it over to be 
    converted to become a new Graph object.

* After running a MarkovChain(), legacy code often 
    uses NetworkX functionality - to extract data from the
    graph and/or partition or to plot the results.
    Routines have been provided to convert the embedded
    RustworkX.PyGraph back to become a NetworkX.Graph
    object with all of the data preserved (the 
    `to_networkx_graph()` function, specifically).  So 
    if it would be convenient to continue to do post-processing 
    analysis using NetworkX, you can conveniently get back 
    to a NetworkX environment.

There are a very few changes to legacy code that you will
probably need to make, but they are easy to 
identify and fix.  We will list them later on below.

If you have not written any custom code (e.g.
updaters, spanning_tree functions, tree bipartitioning 
functions, etc.), then your migration process should 
be something like:

* Create your graph.  Your existing code may "just
    work" but if it doesn't, then you can modify your
    code to create a pure NetworkX Graph and then 
    convert it to be a new GerryChain Graph.

* Run your MarkovChain()

* After running the chain, convert the graph
    used for the chain (a RustworkX.PyGraph object)
    back to become a NetworkX.Graph object.
    You may need to make some additional conversions
    if you care about data at the individual node level,
    but there are functions to make that straight-forward.

If, however, you have written custom code or if
your post-processing analysis depends on data associated 
with individual nodes, then there are some issues
that you need to be aware of.

====================================================

## Changes that most legacy code will need to make:

If your code updates the data associated with nodes or
edges then it probably contains code that looks something
like this:
```python

    my_graph.nodes[node_id][attribute_name] = new_value

    my_graph.edges[node1_id, node2_id][attribute_name] = new_value
```
Since the new GerryChain Graph object no longer
inherits from NetworkX.Graph, and instead wraps
both NetworkX.Graph and RustworkX.PyGraph,
the functionality in the above code needs to be changed to:
```python
    my_graph.node_data(node_id)[attribute_name] = new_value

    my_graph.edge_data(edge_id)[attribute_name] = new_value
```

For nodes, the needed change is a simple change in 
syntax - "node_data" instead of "nodes" and 
parentheses instead of square-brackets.

For edges, however, the change is more involved 
because in the RustworkX world, edges are identified
by an integer ID and not a tuple of node_ids.

There is discussion below about node_ids and edge_ids
but perhaps the easiest path forward if your code
deals with edge data is to convert your graph
to a pure NetworkX.Graph object which you then convert
to be a new GerryChain Graph object.  This will allow
you to use the exact code you already have to 
manipulate edge data.

====================================================

## Changes for code after running MarkovChain()

After running MarkovChain() it is time to explore
results.  Results can be stored in several places:

* In the data associated with the nodes or the
    edges in the graph, or

* In the data associated with a partition - for 
    instance in the assignments of nodes to a 
    district or in the attributes of the partition 
    (created by updaters).

Note, however, that the graph used in the MarkovChain()
processing is a RustworkX.PyGraph object, and 
the node_ids and the edge_ids for that graph are NOT
necessarily the same as the node_ids and the edge_ids (pair 
of node_ids) that were used to build the graph.

So, if your post-MarkovChain() analysis does not depend
on node_ids or edge_ids - that is if your code 
does not specifically reference the same node_ids
and edge_ids used to build your graph, then you
may not need to do anything to have your code work.

Even so, it might be convenient to convert the
RustworkX.PyGraph object back to be a NetworkX.Graph
object, perhaps just to use existing NetworkX based
plotting routines or other NetworkX functionality.

There is a routine that will do that conversion, 
preserving all of the node data and edge data.
The routine is:
```python
    my_graph.to_networkx_graph()
```
If your code DOES depend on node_ids and edge_ids,
meaning that your code uses the same node_ids and 
edge_ids that were used to create your graph, then
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
to use the original_nx_node_id_for_internal_node_id()
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

====================================================

## Node IDs and Edge IDs

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

In NetworkX an edge is a tuple of node_ids and the ID
for an edge is also the ***same*** tuple of node_ids,
so there is no difference between an edge and an edge_id.
However, in RustworkX edges are effectively stored in
a list and the ID for an edge is the index in the list
at which the edge is stored.

This creates some interesting challenges...

As discussed above, the new codebase converts 
NetworkX based graphs to be graphs based on RustworkX.
The codebase also maintains a mapping from NetworkX 
node_ids to RustworkX node_ids and vice versa.

So, legacy code that involves node_ids needs to be 
aware of whether it is manipulating "original" NetworkX
node_ids or RustworkX node_ids used during MarkovChain()
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
 
# DELETE EVERYTHING AFTER THIS...



====================================================
====================================================
====================================================
====================================================
====================================================
====================================================

Random stuff that I have decided to NOT include, but am 
leaving in for now so that reviewers (Peter?) can 
decide there is something here worth saying...

NOTE: Peter: A lot of this would be good to put into the Release 
notes when we go to the final release!

====================================================

NOTE: Peter: Internal function name changes are good for the changelog
which I will be making later. We don't need to include them in the migration 
guide or the release notes.

Function Name Changes:

Some functions had their names changed because they are "internal" functions
meaning that they are not intended to be used outside the module that they
are defined in.  Their names were changed to have a leading underscore
which is Python's convention for internal function names:

-def are_reachable(G: nx.Graph, source: Any, avoid: Callable, targets: Any) -> bool:
+def _are_reachable(graph: Graph, start_node: Any, avoid: Callable, targets: Any) -> bool:
    => name change, param name change

-    def partition_edge_avoid(start_node: Any, end_node: Any, edge_attrs: Dict):
+    def _partition_edge_avoid(start_node: Any, end_node: Any):
    => name change, param change

-def affected_parts(partition: Partition) -> Set[int]:
+def _affected_parts(partition: Partition) -> Set[int]:
    => name change


-def create_grid_graph(dimensions: Tuple[int, int], with_diagonals: bool) -> Graph:
+def _create_grid_nx_graph(dimensions: Tuple[int, int], with_diagonals: bool) -> Graph:
    => name change 

-def tag_boundary_nodes(graph: Graph, dimensions: Tuple[int, int]) -> None:
+def _tag_boundary_nodes(nx_graph: networkx.Graph, dimensions: Tuple[int, int]) -> None:
    => Name change, NX-Graph to Graph

-def get_seed_chunks(
-    graph: nx.Graph,
+# frm: only used in this file, so I changed the name to have a leading underscore
+def _get_seed_chunks(
    => I think the only change is leading underscore and NX-Graph to Graph...

-def recursive_seed_part_inner(
-    graph: nx.Graph,
+def _recursive_seed_part_inner(
    => ???

-def put_edges_into_parts(edges: List, assignment: Dict) -> Dict:
+
+def _put_edges_into_parts(cut_edges: List, assignment: Dict) -> Dict:
    => Name change, param name change

-def new_cuts(partition) -> Set[Tuple]:
+def _new_cuts(partition) -> Set[Tuple]:
    => Name change

-def obsolete_cuts(partition) -> Set[Tuple]:
+def _obsolete_cuts(partition) -> Set[Tuple]:
    => Name change

====================================================

New Functions: 

Some of these are referenced in the text above, but many 
of these seem not of great interest to someone migrating 
code.

     @property
-    def edge_indices(self):
-        return set(self.edges)
+    def edges(self) -> set[tuple[Any, Any]]:
    => New Semantic change - edges vs edge_ids

+    def add_edge(self, node_id1: Any, node_id2: Any) -> None:
    => New (I think) Add support in new Graph for old NX syntax

+    def from_rustworkx(cls, rx_graph: rustworkx.PyGraph) -> "Graph":
    => New

+    def to_networkx_graph(self) -> networkx.Graph:
    => New

+    def internal_node_id_for_original_nx_node_id(self, original_nx_node_id: Any) -> Any:
    => New

+    def verify_graph_is_valid(self) -> bool:
    => New

+    def is_nx_graph(self) -> bool:
    => New

+    def get_nx_graph(self) -> networkx.Graph:
    => New

+    def get_rx_graph(self) -> rustworkx.PyGraph:
    => New

+    def is_rx_graph(self) -> bool:
    => New

+    def convert_from_nx_to_rx(self) -> "Graph":
    => New

+    def get_nx_to_rx_node_id_map(self) -> dict[Any, Any]:
    => New

+    def node_indices(self) -> set[Any]:
    => New

+    def edge_indices(self) -> set[Any]:
    => New

+    def get_edge_from_edge_id(self, edge_id: Any) -> tuple[Any, Any]:
    => New

+    def get_edge_id_from_edge(self, edge: tuple[Any, Any]) -> Any:
    => New

+    def is_directed(self) -> bool:
    => New

+    def translate_subgraph_node_ids_for_flips(self, flips: dict[Any, int]) -> dict[Any, int]:
    => New

+    def translate_subgraph_node_ids_for_set_of_nodes(self, set_of_nodes: set[Any]) -> set[Any]:
    => New

+    def generic_bfs_edges(self, source, neighbors=None, depth_limit=None) -> Generator[tuple[Any, Any], None, None]:
    => New

+    def generic_bfs_successors_generator(self, root_node_id: Any) -> Generator[tuple[Any, Any], None, None]:
    => New

+    def generic_bfs_successors(self, root_node_id: Any) -> dict[Any: Any]:
    => New

+    def generic_bfs_predecessors(self, root_node_id: Any) -> dict[Any, Any]:
    => New

+    def node_data(self, node_id: Any) -> dict[Any, Any]:
    => New - lots to say here...

+    def edge_data(self, edge_id: Any) -> dict[Any, Any]:
    => New - lots to say here...

+    def new_assignment_convert_old_node_ids_to_new_node_ids(self, node_id_mapping: Dict) -> "Assignment":
    => New

+def bipartition_tree_random_with_num_cuts(
    => New 
+#######################
+# frm: Note:  This routine is EXACTLY the same as bipartition_tree_random() except
+#               that it returns in addition to the nodes for a new district, the 
+#               number of possible new districts.  This additional information 
+#               is needed by reversible_recom(), but I did not want to change the
+#               function signature of bipartition_tree_random() in case it is used
+#               as part of the public API by someone.
+#
+#               It is bad form to have two functions that are the same except for 
+#               a tweak - an invitation for future bugs when you fix something in 
+#               one place and not the other, so maybe this is something we should
+#               revisit when we decide a general code cleanup is in order...
+#

NOTE: Peter: Agreed! My hope is to actually move the bipartitioning functions over to
Rust as part of a future performance improvement effort, so this may be moot soon.


====================================================

Functions moved into graph.py

+    def laplacian_matrix(self) -> scipy.sparse.csr_array:
    => Moved from tree.py (I think) - implemented for RX


+    def normalized_laplacian_matrix(self) -> scipy.sparse.dia_array:
    => Moved from tree.py (I think) - implemented for RX


====================================================

Misc. Odd Cases:

-    def __repr__(self):
    => ???

+    def __len__(self) -> int:
    => ???

+    def __getattr__(self, __name: str) -> Any:
    => ???

+    def __getitem__(self, __name: str) -> Any:
    => ???

+    def __iter__(self) -> Iterable[Any]:
    => ???

-    def lookup(self, node: Any, field: Any) -> Any:
    => ???

-    def to_json(
-        self, json_file: str, *, include_geometries_as_geojson: bool = False
-    ) -> None:
+    def to_json(self, json_file_name: str, include_geometries_as_geojson: bool = False) -> None:
    => Param name change 
    => Note that this only works on NX-based new Graph objects (at least for now)

-def add_boundary_perimeters(graph: Graph, geometries: pd.Series) -> None:
+def add_boundary_perimeters(nx_graph: networkx.Graph, geometries: pd.Series) -> None:
    => This is an oddity - it adds node_data on whether a node is a "boundary_node"
       but it currently only works on NX-based graphs.  There is an exception
       that will tell the user this, but there seems to be no good reason to not
       just make it work for RX-based graphs (so long as they have geometry
       data associated).

====================================================

Miscellaneous stuff not yet dealt with

Functions that take (or return) a new Graph instead of a NetworkX.Graph:


-    def from_networkx(cls, graph: networkx.Graph) -> "Graph":
+    def from_networkx(cls, nx_graph: networkx.Graph) -> "Graph":
    => NX-Graph to Graph


-    def from_json(cls, json_file: str) -> "Graph":
+    def from_json(cls, json_file_name: str) -> "Graph":
    => param name change

+    def predecessors(self, root_node_id: Any) -> dict[Any: Any]:
    => ???
-def predecessors(h: nx.Graph, root: Any) -> Dict:
    => ???


+    def successors(self, root_node_id: Any) -> dict[Any: Any]:
    => ???
-def successors(h: nx.Graph, root: Any) -> Dict:
    => ???


+    def subgraphs_for_connected_components(self) -> list["Graph"]:
    => ???


+    def num_connected_components(self) -> int:
    => ???


-    def flip(self, flips: Dict) -> "Partition":
+    def flip(self, flips: Dict, flips_passed_in_use_original_nx_node_ids=False) -> "Partition":
    => Added optional param to help with testing

====================================================
====================================================
====================================================
====================================================
====================================================
