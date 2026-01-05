
The contents of this file are (at present) a stream of consciousness
bunch of stuff that was done in the RX work.  I am including it
because some of it should be included in the eventual release notes
for the RX work.

-Fred January 5, 2026

====================================================
====================================================
====================================================
====================================================
====================================================
====================================================

Random stuff that I have decided to NOT include in the migration guide, but am 
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
