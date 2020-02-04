# Working with Partitions

This document walks you through the most common ways that you might work with a
GerryChain `Partition` object.

```python
>>> import geopandas
>>> from gerrychain import Partition, Graph
>>> from gerrychain.updaters import cut_edges
```

We'll use our
[Pennsylvania VTD json]( https://github.com/mggg/GerryChain/blob/master/docs/user/PA_VTDs.json) to
create the graph we'll use in these examples.

```python
graph = Graph.from_json("./PA_VTDs.json")
```

<!--
```python
>>> df = geopandas.read_file("https://github.com/mggg-states/PA-shapefiles/raw/master/PA/PA_VTD.zip")
>>> df.set_index("GEOID10", inplace=True)
>>> graph = Graph.from_geodataframe(df)
>>> graph.add_data(df)
```
-->
## Creating a partition

Here is how you can create a Partition:

```python
>>> partition = Partition(graph, "CD_2011", {"cut_edges": cut_edges})
```

The `Partition` class takes three arguments to create a Partition:

-   A **graph**.
-   An **assignment of nodes to districts**. This can be the string name of a
    node attribute (shapefile column) that holds each node's district
    assignment, or a dictionary mapping each node ID to its assigned district
    ID.
-   A dictionary of **updaters**.

This creates a partition of the `graph` object we created above from the
Pennsylvania shapefile. The partition is defined by the `"CD_2011"` column
from our shapefile's attribute table.

## `partition.graph`: the underlying graph

You can access the partition's underlying Graph as `partition.graph`. This
contains no information about the partition---it will be the same graph object
that you passed in to `Partition()` when you created the partition instance.

`partition.graph` is a
[`gerrychain.Graph`](https://gerrychain.readthedocs.io/en/latest/api.html#gerrychain.Graph)
object. It is based on the NetworkX Graph object, so any functions (e.g.
[`connected_components`](https://networkx.github.io/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.connected_components.html#networkx.algorithms.components.connected_components))
you can find in the [NetworkX documentation](https://networkx.github.io/) will
be compatible.

```python
>>> partition.graph
<Graph [8921 nodes, 25228 edges]>
```

Now we have a graph of Pennsylvania's VTDs, with all of the data from our
shapefile's attribute table attached to the graph as _node attributes_. We can
see the data that a node has like this:

```python
>>> partition.graph.nodes[0]
{'boundary_node': True,
 'boundary_perim': 0.06312599142331599,
 'area': 0.004278359631999892,
 'STATEFP10': '42',
 'COUNTYFP10': '085',
 'VTDST10': '960',
 'GEOID10': '42085960',
 'VTDI10': 'A',
 'NAME10': 'SHENANGO TWP VTD WEST',
 'NAMELSAD10': 'SHENANGO TWP VTD WEST',
 'LSAD10': '00',
 'MTFCC10': 'G5240',
 'FUNCSTAT10': 'N',
 'ALAND10': 39740056,
 'AWATER10': 141805,
 'INTPTLAT10': '+41.1564874',
 'INTPTLON10': '-080.4865792',
 'TOTPOP': 1915,
 'NH_WHITE': 1839,
 'NH_BLACK': 35'
 'NH_AMIN': 1,
 'NH_ASIAN': 8,
 'NH_NHPI': 0,
 'NH_OTHER': 3,
 'NH_2MORE': 19,
 'HISP': 10,
 'H_WHITE': 3,
 'H_BLACK': 0,
 'H_AMIN': 1,
 'H_ASIAN': 0,
 'H_NHPI': 0,
 'H_OTHER': 4,
 'H_2MORE': 2,
 'VAP': 1553,
 'HVAP': 7,
 'WVAP': 1494,
 'BVAP': 30,
 'AMINVAP': 1,
 'ASIANVAP': 6,
 'NHPIVAP': 0,
 'OTHERVAP': 2,
 '2MOREVAP': 13, 
 'ATG12D': 514.0001036045286,
 'ATG12R': 388.0000782073095, 
 'F2014GOVD': 290.0000584539169, 
 'F2014GOVR': 242.00004877878584, 
 'GOV10D': 289.00005825235166, 
 'GOV10R': 349.00007034626555, 
 'PRES12D': 492.0000991700935, 
 'PRES12O': 11.000002217217538, 
 'PRES12R': 451.0000909059191, 
 'SEN10D': 315.00006349304766, 
 'SEN10R': 328.0000661133957, 
 'T16ATGD': 416.00008385113597, 
 'T16ATGR': 558.0001124733988, 
 'T16PRESD': 342.0000689353089, 
 'T16PRESOTH': 32.00000645008738, 
 'T16PRESR': 631.0001271876606, 
 'T16SEND': 379.00007639322246, 
 'T16SENR': 590.0001189234862, 
 'USS12D': 505.00010179044153, 
 'USS12R': 423.0000852620926, 
 'REMEDIAL': '16', 
 'GOV': '3', 
 'TS': 3, 
 'CD_2011': 3, 
 'SEND': 50, 
 'HDIST': 7, 
 '538DEM': '03', 
 '538GOP': '03', 
 '538CMPCT': '03', 
 'geometry': <shapely.geometry.polygon.Polygon object at 0x7ff3edeb7f90>}
```

The nodes of the graph are identified by IDs. Here the IDs are the VTDs GEOIDs
from the `"GEOID10"` column from our shapefile.

## `partition.assignment`: assign nodes to parts

`partition.assignment` gives you a mapping from node IDs to part IDs ("part" is
our generic word for "district"). It is a custom data structure but you can use
it just like a dictionary.

```python
>>> first_ten_nodes = list(partition.graph.nodes)[:10]
>>> for node in first_ten_nodes:
...     print(partition.assignment[node])
3
3
3
3
3
3
3
3
3
3
```

## `partition.parts`: the nodes in each part

`partition.parts` gives you a mapping from each part ID to the set of nodes that
belong to that part. This is the "opposite" mapping of `assignment`.

As an example, let's print out the number of nodes in each part:

```python
>>> for part in partition.parts:
...    number_of_nodes = len(partition.parts[part])
...    print(f"Part {part} has {number_of_nodes} nodes")
Part 3 has 500 nodes
Part 5 has 580 nodes
Part 10 has 515 nodes
Part 9 has 575 nodes
Part 12 has 623 nodes
Part 6 has 313 nodes
Part 15 has 324 nodes
Part 7 has 405 nodes
Part 16 has 329 nodes
Part 11 has 456 nodes
Part 4 has 292 nodes
Part 8 has 340 nodes
Part 17 has 442 nodes
Part 18 has 600 nodes
Part 14 has 867 nodes
Part 13 has 548 nodes
Part 2 has 828 nodes
Part 1 has 718 nodes
```

Notice that `partition.parts` might not loop through the parts in numerical
order---but it will always loop through the parts in the same order. (You can
run the cell above multiple times to verify that the order doesn't change.)

## `partition.subgraphs`: the subgraphs of each part

For each part of our partition, we can look at the _subgraph_ that it defines.
That is, we can look at the graph made up of all the nodes in a certain part and
all the edges between those nodes.

`partition.subgraphs` gives us a mapping (like a dictionary) from part IDs to
their subgraphs. These subgraphs are NetworkX Subgraph objects, and work exactly
like our main graph object---nodes, edges, and node attributes all work the same
way.

```python
>>> for part, subgraph in partition.subgraphs.items():
...     number_of_edges = len(subgraph.edges)
...     print(f"Part {part} has {number_of_edges} edges")
Part 3 has 1229 edges
Part 5 has 1450 edges
Part 10 has 1252 edges
Part 9 has 1391 edges
Part 12 has 1601 edges
Part 6 has 749 edges
Part 15 has 834 edges
Part 7 has 931 edges
Part 16 has 836 edges
Part 11 has 1152 edges
Part 4 has 723 edges
Part 8 has 886 edges
Part 17 has 1092 edges
Part 18 has 1585 edges
Part 14 has 2344 edges
Part 13 has 1362 edges
Part 2 has 2159 edges
Part 1 has 1780 edges

```

Let's use NetworkX's
[diameter](https://networkx.github.io/documentation/stable/reference/algorithms/generated/networkx.algorithms.distance_measures.diameter.html)
function to compute the diameter of each part subgraph. (The _diameter_ of a
graph is the length of the longest shortest path between any two nodes in the
graph. You don't have to know that!)

```python
>>> import networkx
>>> for part, subgraph in partition.subgraphs.items():
...     diameter = networkx.diameter(subgraph)
...     print(f"Part {part} has diameter {diameter}")
Part 3 has diameter 40
Part 5 has diameter 30
Part 10 has diameter 40
Part 9 has diameter 40
Part 12 has diameter 36
Part 6 has diameter 32
Part 15 has diameter 28
Part 7 has diameter 38
Part 16 has diameter 38
Part 11 has diameter 31
Part 4 has diameter 19
Part 8 has diameter 24
Part 17 has diameter 34
Part 18 has diameter 28
Part 14 has diameter 38
Part 13 has diameter 30
Part 2 has diameter 28
Part 1 has diameter 50
```

## Outputs of updaters

The other main way we can extract information from `partition` is through the
updaters that we configured when we created it. We gave `partition` just one
updater, `cut_edges`. This is the set of edges that go between nodes that are in
_different_ parts of the partition.

```python
>>> len(partition["cut_edges"])
2367
>>> len(partition.cut_edges)
2367
```

```python
>>> proportion_of_cut_edges = len(partition.cut_edges) / len(partition.graph.edges)
>>> print("Proportion of edges that are cut:")
>>> print(proportion_of_cut_edges)
Proportion of edges that are cut:
0.09201881584574116
```
