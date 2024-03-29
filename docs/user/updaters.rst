Updaters
========

Depending on the questions you are investigating, there are many different
values you might want to compute for each partition in your Markov chain. If you
are interested in compactness, you might want to compute the area and perimeter
of each part of the partition so that you can compute compactness scores. If you
are interested in partisan lean, you might want to compute hypothetical election
results using the districts defined by the partition.

The ``Partition`` class allows you to define custom properties for the partitions
in your Markov chain. You can do this by providing a dictionary of updater
functions when you first create a partition.

.. code-block:: python

    from gerrychain import Partition, Graph

    graph = Graph()
    graph.add_edges_from([(0, 1), (1, 2), (2, 0)])
    assignment = {0: 1, 1: 1, 2: 2}

    def my_updater(partition):
        return "Hello!"

    partition = Partition(graph, assignment, {"my_custom_property": my_updater})
    print(partition["my_custom_property"])

This will output:

.. code-block:: console

    Hello!

Recall from `the Partitions section <./partitions.html>`_ that we can also
access this property using:

.. code-block:: python

    partition.my_custom_property

Which also outputs:

.. code-block:: console

    'Hello!'

This partition and all subsequent partitions in the chain will have this
``my_custom_property`` attribute. If we flip a node in ``partition`` to create a new
partition, we can still access this property:

.. code-block:: python

    new_partition = partition.flip({1: 2})
    print(f"Are the partitions different? {new_partition is not partition}")
    print(new_partition["my_custom_property"])

This outputs:

.. code-block:: console

    Are the partitions different? True
    Hello!

Useful updater functions in GerryChain
--------------------------------------

The ``gerrychain.updaters`` submodule provides some updaters for common tasks like
aggregating data and computing the cut edges of a partition:

-   ``Tally``: Aggregates a node attribute (e.g. population) over each part of the
    partition.
-   ``cut_edges``: Returns the set of cut edges (edges whose nodes are in
    different parts of the partition) of the partition. This is required for
    most of the proposal functions in ``gerrychain.proposals``.

Here is an example using both of these updaters:

.. code-block:: python

    from gerrychain.updaters import cut_edges, Tally
    # We'll use a 2x2 grid graph:
    graph = Graph()
    graph.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0)])
    # Give each of the nodes population 100:
    for node in graph:
        graph.nodes[node]["population"] = 100

    # Partition the grid into two halves:
    assignment = {0: 0, 1: 0, 2: 1, 3: 1}
    partition = Partition(
        graph,
        assignment,
        updaters={
            "cut_edges": cut_edges, 
            "population": Tally("population")
        }
    )
    print(f"Population by district:\n\t{partition['population']}")
    print(f"Cut edges in partition:\n\t{partition['cut_edges']}")

This outputs:

.. code-block:: console

    Population by district:
        {0: 200, 1: 200}
    Cut edges in partition:
        {(1, 2), (0, 3)}

Our ``cut_edges`` updater returns a set of edges, each represented as a tuple of
two nodes. Our ``population`` updater returns a dictionary mapping each part of
the partition to the total population in that part. Since we divided our grid in
half, we see parts ``0`` and ``1`` both have population 200.

Now when we create a new partition by flipping a node of ``partition``, we see the
values of the updaters change:

.. code-block:: python

    new_partition = partition.flip({0: 1})
    print(f"Population by district:\n\t{new_partition['population']}")
    print(f"Cut edges in partition:\n\t{new_partition['cut_edges']}")

This outputs:

.. code-block:: console

    Population by district:
        {0: 100, 1: 300}
    Cut edges in partition:
        {(0, 1), (1, 2)}

As we should expect, flipping node ``0`` into part ``1`` increases the population of
part ``1`` to 300 and decreases the population of part ``0`` to 100. The cut edges
of the new partition are both of the edges incident to node ``1``, since this is
the last remaining node in part ``0``.

Writing your own updater function
---------------------------------

When using GerryChain to experiment with new metrics, proposals, or acceptance
rules, there usually comes a point when you need to implement a new updater. As
we saw in the first example, an updater is a function that takes the partition
as its argument and returns any type of value.

Let's create an updater that returns the number of cut edges in the partition.

.. code-block:: python

    def number_of_cut_edges(partition):
        return len(partition["cut_edges"])

.. attention::

  Note that this updater uses the value of the ``cut_edges`` updater in its
  computation. This is completely allowed! All you need to do is make sure that
  any updater that your updater depends on is included in the ``updaters``
  dictionary that we pass to ``Partition``. We also need to make sure that we have
  no cyclic dependencies: if the ``cut_edges`` updater also depended on
  ``number_of_cut_edges``, we would fall into an infinite loop when we called either
  of them, resulting in a ``RuntimeError: maximum recursion depth exceeded`` error.

To try out our updater, we'll use `NetworkX <https://networkx.github.io>`_ to
create a complete graph on 4 nodes, which we'll partition in halves like the 2x2
grid. NetworkX is the graph library that GerryChain uses under the hood in its
``Graph`` class.

.. code-block:: python

    import networkx
    graph = Graph(networkx.complete_graph(4))
    assignment = {0: 0, 1: 0, 2: 1, 3: 1}
    my_updaters = {
        "cut_edges": cut_edges, 
        "number_of_cut_edges": number_of_cut_edges
    }
    partition = Partition(graph, assignment, my_updaters)

Now we can try out our custom ``number_of_cut_edges`` updater, and verify that its
value changes when the partition changes:

.. code-block:: python

    print(partition["number_of_cut_edges"])
    new_partition = partition.flip({0: 1})
    print(new_partition["number_of_cut_edges"])

This will output:

.. code-block:: console

    4
    3

