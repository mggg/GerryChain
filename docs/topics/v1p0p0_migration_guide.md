# Migration Guide for GerryChain v1.0.0

<!-- docs-test: skip-page -- every block is an illustrative fragment: placeholder names, literal `...` arguments, and signature-only stubs -->

This guide will help you understand what you need to change in your "legacy" GerryChain code so that
it can run in the v1.0.0 release.

## Table of Contents

- [Primary Benefit of GerryChain v1.0.0 for Legacy Users](#primary-benefit-of-gerrychain-v100-for-legacy-users)
  - [ Minimizing the Impact on Legacy Code](#minimizing-the-impact-on-legacy-code)
    - [Creating a Graph to use in your Partition](#creating-a-graph-to-use-in-your-partition)
    - [Changes to Accessing and Setting Node and Edge Data](#changes-to-accessing-and-setting-node-and-edge-data)
    - [Running a MarkovChain()](#running-a-markovchain)
    - [Changes to ReCom Proposals](#changes-to-recom-proposals)
      - [The `ReCom` Namespace](#the-recom-namespace)
      - [Renamed Proposal and Tree Parameters](#renamed-proposal-and-tree-parameters)
      - [Multi-Member ReCom](#multi-member-recom)
    - [Analyzing Data after running a MarkovChain()](#analyzing-data-after-running-a-markovchain)
      - [Translating node_ids and edge_ids after running a MarkovChain()](#translating-node_ids-and-edge_ids-after-running-a-markovchain)
  - [Node IDs and Edge IDs - a deep dive...](#node-ids-and-edge-ids---a-deep-dive)

## Primary Benefit of GerryChain v1.0.0 for Legacy Users

The primary benefit of the v1.0.0 release for legacy users is a significant performance boost: about
2X on large graphs.

This performance boost was realized by changing the underlying graph engine from NetworkX to
RustworkX - RustworkX is faster.

There are additional enhancements in v1.0.0 that this guide will not address. This guide will focus
on what you need to do to get your legacy code working.

To provide some context for what follows, the primary change that affects legacy code is that the
GerryChain.Graph object is no longer a subclass of NetworkX.Graph, but is instead a new class that
wraps the underlying graph engine. This allowed us to provide a single interface to user code that
could be implemented under the covers with either a NetworkX.Graph object or a RustworkX.PyGraph
object.

To the extent possible the functions exposed by the new GerryChain.Graph object are the same as
those exposed by the old NetworkX.Graph based graph object - details below.

## Minimizing the Impact on Legacy Code

The new GerryChain.Graph object supports most but not all of the functionality of the old NetworkX
based graph object, so most of the code to manipulate your graph will run unchanged, but some
changes will be required, in particular to set and access node and edge data. More on this below.

We crafted the interface of the new Graph object to be close to the same as that of the old Graph
object. Functions that were inherited from NetworkX that were most commonly used by legacy code have
been implemented as explicit functions of the new Graph object, so that legacy code would run
unchanged.

Examples of formerly inherited functions that are now explicit functions are:

- degree()
- neighbors()

In addition, those functions that had been added to the previous GerryChain.Graph object such as:

- Graph.from_json(...)
- my_gc_graph.to_json(...)
- Graph.from_file(...)
- Graph.from_geodataframe(...)
- etc.

have been implemented for the new Gerrychain.Graph object, to avoid requiring changes in legacy
code.

### Creating a Graph to use in your Partition

There are two ways to create a graph that you can use in your Partition object:

1. Creating a NetworkX.Graph object, making whatever modifications are needed before running a
   chain, and then using that NetworkX.Graph object to create your Partition object.

2. Creating a GerryChain.Graph object directly, and then making whatever modifications are needed to
   that graph object and then using that GerryChain.Graph object to create your Partition object.

Approach #1 is the most compatible with previous (legacy) workflows since, prior to release 1.0.0,
GerryChain treated the `Graph` class as a proper subclass of the NetworkX `Graph` class.

Your code in this case would look something like:

```python
    import networkx
    from gerrychain import Graph

    my_networkx_graph = networkx.Graph()

    ... code to create your NetworkX graph ...

    ... create a Partition using my_networkx_graph ...
```

However, it is often not possible (or convenient) to restructure your code to just use NetworkX
functionality to build your graph. For instance, you might have code that creates a graph from JSON
with:

```python
    my_graph = Graph.from_json(...)
```

or

```python
    my_graph = Graph.from_geodataframe(...)
```

In these cases, any modifications to your graph needed before running a chain will need to be done
using the new GerryChain.Graph object. So your code would look something like:

```python
    from gerrychain import Graph

    my_gerrychain_graph = Graph.from_json(...)

    ... code to modify your graph ...

    ... create a Partition using my_gerrychain_graph ...
```

### Changes to Accessing and Setting Node and Edge Data

As stated above, the new GerryChain Graph object no longer inherits from NetworkX.Graph, and instead
wraps either a NetworkX.Graph or a RustworkX.PyGraph.

As a result, the way to access and set node and edge data has changed.

If your code accesses or updates the data associated with nodes then it probably contains code that
looks something like this:

```python

    my_graph.nodes[node_id]["<attr_name>"] = new_value

    node_attr_value = mygraph.nodes[node_id]["<attr_name>"]
```

In v1.0.0, this code will need to be changed to be:

```python
    my_graph.node_data(node_id)["<attr_name>"] = new_value

    node_attr_value = mygraph.node_data(node_id)["<attr_name>"]

```

The needed change is a simple change in syntax - "node_data" instead of "nodes" and parentheses
instead of square-brackets.

If your code accesses or updates the data associated with edges then it probably contains code that
looks something like this:

```python
    my_graph.edges[node1_id, node2_id]["<attr_name>"] = new_value

    edge_attr_value = my_graph.edges[node1_id, node2_id]["<attr_name>"]
```

In v1.0.0, this code will need to be changed to be:

```python
    # Get an edge_id given the two nodes in the edge
    my_edge_id = my_graph.get_edge_id_from_edge((node1_id, node2_id))

    my_graph.edge_data(my_edge_id)["<attr_name>"] = new_value

    edge_attr_value = my_graph.edge_data(my_edge_id)["<attr_name>"]
```

The important change here is that you need to obtain the edge_id before calling
my_graph.edge_data(edge_id). In NetworkX an edge_id is a tuple of node_ids, but in RustworkX an
edge_id is an integer.

Note that the new GerryChain.Graph object also provides a way to obtain the node_ids associated with
an edge:

```python
    edge_node_ids = my_graph.get_edge_from_edge_id(my_edge_id)

    node1_id = edge_node_ids[0]
    node2_id = edge_node_ids[1]
```

### Running a MarkovChain()

The graph work in v1.0.0 requires very little change here: the code that creates a Partition object
will convert the graph provided into a RustworkX.PyGraph automatically, and all of the internal code
that runs when running a MarkovChain() has been updated to work with the RustworkX.PyGraph object.

Separately from the graph change, though, three MarkovChain() parameters were renamed in v1.0.0, so
legacy code that passes them **by keyword** will need updating:

| Legacy name     | v1.0.0 name         |
| --------------- | ------------------- |
| `proposal`      | `proposal_fn`       |
| `accept`        | `acceptance_fn`     |
| `initial_state` | `initial_partition` |

The parameter order did not change, so legacy code that passes these positionally keeps working
unchanged.

<!-- TODO: add in the deprecation shims and update this -->

```python
    # Legacy keyword form - now raises
    #   TypeError: MarkovChain.__init__() got an unexpected keyword argument 'proposal'
    chain = MarkovChain(
        proposal=my_proposal,
        constraints=[contiguous],
        accept=always_accept,
        initial_state=initial_partition,
        total_steps=1000,
    )

    # v1.0.0
    chain = MarkovChain(
        proposal_fn=my_proposal,
        constraints=[contiguous],
        acceptance_fn=always_accept,
        initial_partition=initial_partition,
        total_steps=1000,
    )
```

This rename is part of a general convention in v1.0.0: parameters that take a function end in `_fn`.
Plural collection parameters such as `constraints` and `updaters` keep their noun names. The same
rename applies to the acceptance functions, the optimizers, and the tree functions, so if a keyword
you are passing names a callable and it is rejected, try adding the `_fn` suffix.

The exception to this is if the legacy code contains custom code for updaters. Since any such code
will operate on a GerryChain.Graph object that is wrapped around a RustworkX.PyGraph object, that
code will need to be aware of the fact that node_ids and edge_ids will be different from those in
the original NetworkX.Graph object used to create the Partition object.

Another concern for such code is the use of subgraphs. In RustworkX, the node_ids and edge_ids for a
subgraph are different from those of the parent graph, so again, any code involving subgraphs that
runs when doing a MarkovChain() will need to be aware of the fact that node_ids and edge_ids are
different from the parent graph.

There is a more detailed discussion of node_ids and edge_ids later in this guide.

One other addition worth knowing: MarkovChain() now takes an `rng` argument (an integer seed or a
`random.Random`), and the chain's RNG is passed to your proposal and acceptance functions. This is
what makes runs reproducible. There is more on this in the reproducibility guide.

### Changes to ReCom Proposals

Legacy code almost always builds a ReCom proposal with `functools.partial`:

```python
    from functools import partial
    from gerrychain.proposals import recom

    my_proposal = partial(
        recom,
        pop_col="TOTPOP",
        pop_target=ideal_population,
        epsilon=0.01,
        node_repeats=2,
    )
```

That still works. `recom` is still exported and still takes a partition as its first argument, so
the `partial` idiom is not going away. But v1.0.0 adds a shorter way to say the same thing, and
renames a few parameters underneath.

#### The `ReCom` Namespace

Instead of the `partial` incantation, v1.0.0 provides slim, ready-made builders that provide a
simple interface to return a proposal function directly:

```python
    from gerrychain.proposals import ReCom

    my_proposal = ReCom.district_pairs_mst(
        pop_col="TOTPOP",
        pop_target=ideal_population,
        epsilon=0.01,
    )
```

The variants differ along two axes. `district_pairs_*` picks uniformly among adjacent district
pairs, while `cut_edges_*` picks a cut edge at random and merges the districts on either side, so a
pair's chance is proportional to how many cut edges it shares. `*_mst` draws a minimum spanning tree
over random edge weights using Kruskal's algorithm; `*_ust` draws a uniform spanning tree using
Wilson's algorithm. `ReCom.reversible(...)` is Reversible ReCom. The single-letter aliases `A`, `B`,
`C`, `D`, and `R` are also available.

> **Note:** If your legacy code used the old `ReCom` _class_ - the one you constructed with
> `ReCom(pop_col=..., ideal_pop=..., epsilon=...)` - that class is gone. `ReCom` is now a namespace
> and cannot be instantiated; calling `ReCom(...)` raises a `TypeError` pointing you at the builder
> methods. Note also that the old class's `ideal_pop` parameter is spelled `pop_target` throughout
> v1.0.0.

When you need parameters the slim builders do not expose, use `build_recom_proposal_fn`, which takes
the full set and returns a proposal function:

```python
    from gerrychain.proposals import build_recom_proposal_fn

    my_proposal = build_recom_proposal_fn(
        pop_col="TOTPOP",
        pop_target=ideal_population,
        epsilon=0.01,
        region_surcharge={"county": 0.5},
        bipartition_tree_fn=my_bipartition_tree_fn,
    )
```

#### Renamed Proposal and Tree Parameters

If you pass any of these by keyword, they need updating:

| Legacy name       | v1.0.0 name                  | Where                                  |
| ----------------- | ---------------------------- | -------------------------------------- |
| `method`          | `bipartition_tree_fn`        | `recom`                                |
| `balance_edge_fn` | `find_balanced_edge_cuts_fn` | `bipartition_tree`                     |
| `one_sided_cut`   | `single_district_cut`        | `bipartition_tree`, custom cut finders |
| `choice`          | `cut_choice_fn`              | `bipartition_tree`                     |

Two of these deserve extra attention.

`single_district_cut` was renamed because the old name described the cut rather than what the flag
actually controls: whether only the returned side must be population-balanced (peeling off one
district) or both sides must be (bisecting). If you wrote a custom balanced-edge-cut finder, it must
now accept this parameter unconditionally. Previously GerryChain inspected your function's signature
and only passed the flag if it was present; that probe has been removed.

`cut_choice_fn` is not a drop-in rename of `choice`. The old `choice` defaulted to `random.choice`
and was called with just the list of cuts. The new `cut_choice_fn` is called as
`cut_choice_fn(cuts, rng=rng)`, so that the chain can supply its own seeded RNG:

```python
    def choose_random_cut(cuts, *, rng):
        return rng.choice(cuts)
```

Also note that `node_repeats` now defaults to `0` rather than `1`. With the default memoized cut
finder, each search already examines every edge in the tree, so re-rooting cannot make an uncuttable
tree cuttable; the new default redraws the tree immediately instead. Legacy code that passes a
positive `node_repeats` still runs, but now emits a warning:

```console
    UserWarning: node_repeats is not beneficial with `find_balanced_edge_cuts_memoization`,
    which exhaustively searches each spanning tree. Set node_repeats=0 to redraw the tree
    after an unsuccessful search.
```

Setting `node_repeats=0` (or simply dropping the argument) is the fix. Positive values remain useful
only with `find_balanced_edge_cuts_contraction` or a custom cut-edge finder whose result depends on
the root choice.

#### Multi-Member ReCom

Multi-member ReCom - where districts elect different fixed numbers of members - lived on a separate
branch before the RustworkX migration and was rebuilt for v1.0.0. If you were using that branch, the
feature is now available from the main package:

```python
    from gerrychain.proposals import MultiMemberReCom

    members_per_district = {"1": 1, "2": 1, "3": 2, "4": 4}
    pop_target = total_population / sum(members_per_district.values())

    my_proposal = MultiMemberReCom.district_pairs_mst(
        pop_col="TOTPOP",
        pop_target=pop_target,
        epsilon=0.01,
        members_per_district=members_per_district,
    )
```

`MultiMemberReCom` offers the same four non-reversible variants as `ReCom`, plus
`build_multi_member_recom_proposal_fn` for the full parameter set. Three things differ from the
single-member case:

- `pop_target` is the population for a _single member_, so it is the total population divided by the
  total number of members, not by the number of districts.
- Member counts attach to district labels and stay fixed for the whole run. The keys of
  `members_per_district` must match the partition's district labels exactly, and every count must be
  a positive integer.
- The equal-population constraint is not appropriate, since districts are deliberately unequal in
  size. Use `within_percent_of_ideal_population_per_member` instead.

There is no reversible multi-member variant, and no random multi-member seed generation yet; build a
starting plan by merging single-member districts. The [ReCom user guide](../user/recom.ipynb) has a
worked example.

### Analyzing Data after running a MarkovChain()

After running a MarkovChain(), legacy code often uses NetworkX functionality - to extract data from
the graph and/or partition or to plot the results. A function has been provided to convert the
embedded RustworkX.PyGraph back to become a NetworkX.Graph object with all of the data preserved
(the `to_networkx_graph()` function, specifically).

So, if your legacy code uses NetworkX functionality to post-process the data after running a
MarkovChain(), or perhaps to plot results, then you probably want to convert the graph associated
with your Partition object to be a NetworkX.Graph object:

```python
    my_gc_graph = my_partition.graph

    my_networkx_graph = my_gc_graph.to_networkx_graph()

    ... do post-processing using my_networkx_graph ...
```

Note that all node_data and edge_data that was generated during the procssing of the MarkovChain()
is preserved in the generated NetworkX.Graph object.

For many legacy projects, this is all that will be required. However, if your post MarkovChain()
processing depends on the original NetworkX.Graph node_ids and/or edge_ids, then you have work to
do, because the node_ids and edge_ids that are stored in the chain are RustworkX.PyGraph node_ids
and edge_ids.

You will need to translate those node_ids and edge_ids back to the original NetworkX.Graph node_ids
and edge_ids.

We have provided routines to help you do this translation. Those routines are discussed below.

#### Translating node_ids and edge_ids after running a MarkovChain()

After running MarkovChain() results can be stored in several places:

- In the data associated with the nodes or the edges in the graph, or

- In the data associated with a partition - for instance in the assignments of nodes to a district
  or in the attributes of the partition (created by updaters).

As stated above, the graph used in the MarkovChain() processing is a RustworkX.PyGraph object, and
the node_ids and the edge_ids for that graph are NOT necessarily the same as the node_ids and the
edge_ids (pair of node_ids) that were used to build the graph.

So, if your code depends on the original NetworkX.Graph node_ids and edge_ids, you will need to
translate the node_ids and edge_ids back into what they were in the original NetworkX.Graph object.
There are routines to do this:

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

which are attached as methods of the new GerryChain Graph object and can thus be invoked as:

```python
    my_graph.original_nx_node_id_for_internal_node_id(internal_node_id)
    my_graph.original_nx_node_ids_for_set(set_of_node_ids)
    my_graph.original_nx_node_ids_for_list(list_of_node_ids)
```

> Note: the "internal_node_id" in the above routines refers to the RustworkX.PyGraph node_id as do
> the sets and lists of node_ids.

If you wish to extract NetworkX.Graph edges then you will need a tuple of node_ids. First you need
to get the RustworkX.PyGraph node_ids for an edge, given its RustworkX edge_id (an integer), and
then you need to use the `original_nx_node_id_for_internal_node_id()` routine to get the original NX
node_ids for the edge. The routines to do this are:

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

So, to extract the NetworkX.Graph edge for a specific edge from a new GerryChain Graph object that
embeds a RustworkX.PyGraph object, you would need to do:

```python
    rx_edge = my_graph.get_edge_from_edge_id(my_edge_id)
    nx_node_id_1 = my_graph.original_nx_node_id_for_internal_node_id(rx_edge[0])
    nx_node_id_2 = my_graph.original_nx_node_id_for_internal_node_id(rx_edge[1])
    my_nx_edge = (nx_node_id_1, nx_node_id_2)
```

## Node IDs and Edge IDs - a deep dive...

If you have written custom code, (for instance, a custom updater or a spanning function or a
bipartition function) then you need to understand how node_ids and edge_ids have changed.

In NetworkX a node_id can be any hashable Python object other than `None` (an integer, a string, a
tuple, etc.). In RustworkX a node_id is always an integer, and in the graphs that GerryChain builds
the node_ids always run sequentially from 0 with no gaps. RustworkX on its own can leave gaps when
nodes are removed, but GerryChain never removes them: the embedded graph is frozen once a Partition
is created.

In NetworkX an edge is a tuple of node_ids and an edge_id is the **_same_** tuple of node_ids, so
there is no difference between an edge and an edge_id. However, in RustworkX while edges are still a
tuple of node_ids, an edge_id is an integer. So an edge and an edge_id are different.

This creates some interesting challenges...

As discussed above, the new codebase converts NetworkX based graphs to be graphs based on RustworkX.
The codebase also maintains a mapping from NetworkX node_ids to RustworkX node_ids and vice versa.

So, legacy code that involves node_ids needs to be aware of whether it is manipulating "original"
NetworkX node_ids or "internal" RustworkX node_ids used during MarkovChain() calculations. This is
relatively straightforward - you just need to know which kind of node_id you need and perhaps
convert from one kind to the other.

Edges and edge_ids are more challenging, because you need to determine whether the "edge" in your
legacy code is referring to a tuple (you want to get at the node_ids for the edge) or to the ID for
the edge (needed when you want to get data associated with the edge). There are routines to get an
edge (tuple) from an edge_id and vice versa.

Remember that before running MarkovChain(), or more accurately, until you create a Partition object,
the embedded graph is still NetworkX based and so you can probably be clever and continue to use
NetworkX to deal with edges - one way to do this is to ask to get direct access to the embedded
NetworkX graph and operate directly on the embedded graph. The routine to gain access to the
embedded NetworkX.Graph object is:

```python
    def get_nx_graph(self) -> networkx.Graph:
```

The routines to go back and forth from edge_ids to/from edges are:

```python
    def get_edge_from_edge_id(self, edge_id: Any) -> tuple[Any, Any]:

    def get_edge_id_from_edge(self, edge: tuple[Any, Any]) -> Any:
```

Another issue is iterating over nodes and edges. These are properties, not methods, so access them
without parentheses:

```python
    @property
    def edge_indices(self) -> set[Any]:  # edge_ids

    @property
    def edges(self) -> set[tuple[Any, Any]]:

    @property
    def node_indices(self) -> set[Any]:

    @property
    def nodes(self) -> list[Any]:
```

That is, write `my_graph.nodes`, not `my_graph.nodes()`.

**Caution:** In pre v1.0.0 code graph.nodes[node_id] would return a data dict for the data
associated with the given node_id. However, in v1.0.0 this code will interpret the node_id as an
index into the list of nodes defined for the graph. This might end up being a subtle and hence hard
bug to find, so please search your legacy code for any uses of graph.nodes[node_id]...

Note that node_indices and nodes return the same thing - except that one is a list and the other a
set. The nodes function was retained because legacy code uses it a lot to iterate over the graph.

The edge_indices function returns edge_ids which for a graph with an embedded NetworkX graph will
return tuples of node_ids and for a graph with an embedded RustworkX graph will return integers. The
edges function always returns tuples of node_ids but for NetworkX the node_ids will be NetworkX
node_ids which do not have to be integers while for RustworkX the node_ids will always be integers.

The last and most important issue involving node_ids and edge_ids is subgraphs. We have noted
already that node_ids and edge_ids in RustworkX are always sequential integers with no gaps starting
at 0. This is one of the things that makes it possible for RustworkX to be faster than NetworkX.
However, it also means that node_ids and edge_ids in RustworkX subgraphs are also sequential
integers with no gaps starting at 0 - which means that the node_ids for the same node might be
different in a subgraph containing that node than in that same node's id in the parent graph. This
can cause some headaches pretty big headaches for anyone working with them, but we anticipate that
most users will not need to deal with this pain-point.

There are two major issues that result from subgraphs having new node_ids and edge_ids:

1. Results of computations performed on subgraphs that contain node_id or edge_id information will
   need to be converted to refer to the corresponding node_ids and/or edge_ids in the parent graph.
   For instance, if a subroutine operates on a subgraph and returns flips, then the node_ids in the
   flips will need to be converted back to be parent graph node_ids.

2. There is a danger that a computation mixes parent graph node/edge_ids and subgraph node/edge_ids.
   To guard against this in the new codebase, calls on graph.subgraph() are always made as actual
   parameters to a function call. This guarantees that the subgraph IDs cannot be used in the
   caller's context. In addition, as mentioned above in #1, it is the responsibility of the called
   function to convert any IDs in the return value to be those that are appropriate for the parent
   graph.

To make it possible to translate from a subgraph back to the parent, whenever a subgraph is created,
a mapping (dictionary) is created that converts the subgraph node_id to the parent graph's node_id.
This is hidden slightly from the public interface, but is accessible as
`_node_id_to_parent_node_id_map` and two routines exist to make it convenient to convert flips and
sets of nodes back to the node_ids appropriate for the parent graph:

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
