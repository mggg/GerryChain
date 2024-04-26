Working with Partitions
=======================

.. raw:: html

    <div class="center-container">
      <a href="https://github.com/mggg/GerryChain/tree/main/docs/_static/PA_VTDs.json" class="download-badge" download>Download PA File</a>
    </div>
    <br style="line-height: 5px;">

This document walks you through the most common ways that you might work with a
GerryChain ``Partition`` object.

.. code-block:: python

    from gerrychain import Partition, Graph
    from gerrychain.updaters import cut_edges

We'll use our 
`Pennsylvania VTD json <https://github.com/mggg/GerryChain/tree/main/docs/_static/PA_VTDs.json>`_ 
to create the graph we'll use in these examples.

.. code-block:: python

    graph = Graph.from_json("./PA_VTDs.json")

Creating a partition
--------------------

There are a couple of ways in which we could make a partition. The first way is to
just make a random assignment with a population balance of :math:`\varepsilon`

.. code-block:: python

    partition = Partition.from_random_assignment(
        graph=graph,
        n_parts=2,
        epsilon=0.01,
        pop_col="TOT_POP"
    )

However, in this example we will create a partition based on the "2011_PLA_1" plan
that already exists in the file:

.. code-block:: python

    partition = Partition(graph, "2011_PLA_1", {"cut_edges": cut_edges})

The ``Partition`` class takes three arguments to create a Partition:

- A **graph**.
- An **assignment of nodes to districts**. This can be the string name of a
  node attribute (shapefile column) that holds each node's district
  assignment, or a dictionary mapping each node ID to its assigned district
  ID.
- A dictionary of **updaters**.

This creates a partition of the ``graph`` object we created above from the
Pennsylvania shapefile. The partition is defined by the ``"CD_2011"`` column
from our shapefile's attribute table.

``partition.graph``: the underlying graph
-----------------------------------------

You can access the partition's underlying Graph as ``partition.graph``. This
contains no information about the partition---it will be the same graph object
that you passed in to ``Partition()`` when you created the partition instance.

``partition.graph`` is a 
`gerrychain.Graph <https://gerrychain.readthedocs.io/en/latest/api.html#gerrychain.Graph>`_ 
object. It is based on the NetworkX Graph object, so any functions (e.g. 
`connected_components <https://networkx.github.io/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.connected_components.html#networkx.algorithms.components.connected_components>`_) 
you can find in the `NetworkX documentation <https://networkx.github.io/>`_ will be compatible.

.. code-block:: python

    partition.graph

prints something like:

.. code-block:: console

    <gerrychain.graph.graph.FrozenGraph object at 0x7fb0a93bbfa0>

Now we have a graph of Pennsylvania's VTDs, with all of the data from our
shapefile's attribute table attached to the graph as *node attributes*. We can
see the data that a node has like this:

.. code-block:: python

    partition.graph.nodes[0]

which will output:

.. code-block:: console

    {'boundary_node': False,
    'area': 0.0063017857514999324,
    'STATEFP10': '42',
    'COUNTYFP10': '039',
    'VTDST10': '60',
    'GEOID10': '42039060',
    'VTDI10': 'A',
    'NAME10': 'CAMBRIDGE SPRINGS Voting District',
    'NAMELSAD10': 'CAMBRIDGE SPRINGS Voting District',
    'LSAD10': '00',
    'MTFCC10': 'G5240',
    'FUNCSTAT10': 'N',
    'ALAND10': 2258229,
    'AWATER10': 0,
    'INTPTLAT10': '+41.8018353',
    'INTPTLON10': '-080.0596566',
    'ATG12D': 0.0,
    'ATG12R': 0.0,
    'GOV10D': 0.0,
    'GOV10R': 0.0,
    'PRES12D': 0.0,
    'PRES12O': 0.0,
    'PRES12R': 0.0,
    'SEN10D': 0.0,
    'SEN10R': 0.0,
    'T16ATGD': 0.0,
    'T16ATGR': 0.0,
    'T16PRESD': 0,
    'T16PRESOTH': 0.0,
    'T16PRESR': 0,
    'T16SEND': 0,
    'T16SENR': 0,
    'USS12D': 0.0,
    'USS12R': 0.0,
    'GOV': 3,
    'TS': 5,
    'HISP_POP': 0,
    'TOT_POP': 0,
    'WHITE_POP': 0,
    'BLACK_POP': 0,
    'NATIVE_POP': 0,
    'ASIAN_POP': 0,
    'F2014GOVD': 1,
    'F2014GOVR': 1,
    '2011_PLA_1': 3,
    'REMEDIAL_P': 14,
    '538CPCT__1': 3,
    '538DEM_PL': 3,
    '538GOP_PL': 3,
    '8THGRADE_1': 1}

``partition.assignment``: assign nodes to parts
------------------------------------------------

``partition.assignment`` gives you a mapping from node IDs to part IDs ("part" is
our generic word for "district"). It is a custom data structure but you can use
it just like a dictionary. So the code:

.. code-block:: python

    first_ten_nodes = list(partition.graph.nodes)[:10]
    for node in first_ten_nodes:
        print(partition.assignment[node])

will output:

.. code-block:: console

    3
    3
    3
    3
    3
    3
    3
    10
    10
    10

``partition.parts``: the nodes in each part
-------------------------------------------

``partition.parts`` gives you a mapping from each part ID to the set of nodes that
belong to that part. This is the "opposite" mapping of ``assignment``.

As an example, let's print out the number of nodes in each part:

.. code-block:: python

    for part in partition.parts:
        number_of_nodes = len(partition.parts[part])
        print(f"Part {part} has {number_of_nodes} nodes")

This will give us:

.. code-block:: console

    Part 3 has 469 nodes
    Part 10 has 462 nodes
    Part 9 has 515 nodes
    Part 5 has 513 nodes
    Part 15 has 317 nodes
    Part 6 has 310 nodes
    Part 11 has 440 nodes
    Part 8 has 337 nodes
    Part 4 has 271 nodes
    Part 18 has 591 nodes
    Part 12 has 597 nodes
    Part 17 has 412 nodes
    Part 7 has 404 nodes
    Part 16 has 322 nodes
    Part 14 has 867 nodes
    Part 13 has 548 nodes
    Part 2 has 828 nodes
    Part 1 has 718 nodes

``partition.subgraphs``: the subgraphs of each part
---------------------------------------------------

For each part of our partition, we can look at the _subgraph_ that it defines.
That is, we can look at the graph made up of all the nodes in a certain part and
all the edges between those nodes.

``partition.subgraphs`` gives us a mapping (like a dictionary) from part IDs to
their subgraphs. These subgraphs are NetworkX Subgraph objects, and work exactly
like our main graph object---nodes, edges, and node attributes all work the same
way.

.. code-block:: python

    for part, subgraph in partition.subgraphs.items():
        number_of_edges = len(subgraph.edges)
        print(f"Part {part} has {number_of_edges} edges")

This will output:

.. code-block:: console

    Part 3 has 1195 edges
    Part 10 has 1183 edges
    Part 9 has 1314 edges
    Part 5 has 1349 edges
    Part 15 has 824 edges
    Part 6 has 745 edges
    Part 11 has 1134 edges
    Part 8 has 881 edges
    Part 4 has 693 edges
    Part 18 has 1575 edges
    Part 12 has 1559 edges
    Part 17 has 1015 edges
    Part 7 has 930 edges
    Part 16 has 825 edges
    Part 14 has 2344 edges
    Part 13 has 1362 edges
    Part 2 has 2159 edges
    Part 1 has 1780 edges

Let's use NetworkX's 
`diameter <https://networkx.github.io/documentation/stable/reference/algorithms/generated/networkx.algorithms.distance_measures.diameter.html>`_ 
function to compute the diameter of each part subgraph. (The _diameter_ of a graph is
the length of the longest path in the set of shortest paths between any two nodes in the
given graph, but you don't have to know that!)

.. code-block:: python

    import networkx
    for part, subgraph in partition.subgraphs.items():
        diameter = networkx.diameter(subgraph)
        print(f"Part {part} has diameter {diameter}")

This outputs:

.. code-block:: console

    Part 3 has diameter 40
    Part 10 has diameter 40
    Part 9 has diameter 40
    Part 5 has diameter 29
    Part 15 has diameter 28
    Part 6 has diameter 32
    Part 11 has diameter 31
    Part 8 has diameter 24
    Part 4 has diameter 19
    Part 18 has diameter 28
    Part 12 has diameter 35
    Part 17 has diameter 35
    Part 7 has diameter 38
    Part 16 has diameter 38
    Part 14 has diameter 38
    Part 13 has diameter 30
    Part 2 has diameter 28
    Part 1 has diameter 50

Outputs of updaters
-------------------

The other main way we can extract information from ``partition`` is through the
updaters that we configured when we created it. We gave ``partition`` just one
updater, ``cut_edges``. This is the set of edges that go between nodes that are in
_different_ parts of the partition. We should note that the updaters for
our partition are both an item and an attribute of the partition, so we can
access them with:

.. code-block:: python

    len(partition["cut_edges"])

which outputs:

.. code-block:: console

    2361

or 

.. code-block:: python

    len(partition.cut_edges)

which also outputs:

.. code-block:: console

    2361

So if we wanted to print out the proportion of cut edges present within our graph,
we might write:

.. code-block:: python

    proportion_of_cut_edges = len(partition.cut_edges) / len(partition.graph.edges)
    print("Proportion of edges that are cut:")
    print(proportion_of_cut_edges)

this will output:

.. code-block:: console

    Proportion of edges that are cut:
    0.09358649120025368
