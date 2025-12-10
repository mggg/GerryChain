import pytest
import networkx as nx
import rustworkx as rx
from gerrychain import Graph

###############################################
# This file contains tests routines in graph.py
###############################################

@pytest.fixture
def four_by_five_grid_nx():

    # Create an NX Graph object with attributes
    #
    # This graph has the following properties
    # which are important for the tests below:
    #
    #  * The "nx_node_id" attribute serves as an
    #    effective "original" node_id so that we
    #    can track a node even when its internal
    #    node_id changes.
    #
    #  * The graph has two "connected" components:
    #    the first two rows and the last two
    #    rows.  This is used in the connected
    #    components tests

    # nx_node_id
    #
    #  0  1  2  3  4
    #  5  6  7  8  9
    # 10 11 12 13 14
    # 15 16 17 18 19

    # MVAP:
    #
    #  2  2  2  2  2
    #  2  2  2  2  2
    #  2  2  2  2  2
    #  2  2  2  2  2

    nx_graph = nx.Graph()
    nx_graph.add_nodes_from(
        [
            (0, {"population": 10, "nx_node_id": 0, "MVAP": 2}),
            (1, {"population": 10, "nx_node_id": 1, "MVAP": 2}),
            (2, {"population": 10, "nx_node_id": 2, "MVAP": 2}),
            (3, {"population": 10, "nx_node_id": 3, "MVAP": 2}),
            (4, {"population": 10, "nx_node_id": 4, "MVAP": 2}),
            (5, {"population": 10, "nx_node_id": 5, "MVAP": 2}),
            (6, {"population": 10, "nx_node_id": 6, "MVAP": 2}),
            (7, {"population": 10, "nx_node_id": 7, "MVAP": 2}),
            (8, {"population": 10, "nx_node_id": 8, "MVAP": 2}),
            (9, {"population": 10, "nx_node_id": 9, "MVAP": 2}),
            (10, {"population": 10, "nx_node_id": 10, "MVAP": 2}),
            (11, {"population": 10, "nx_node_id": 11, "MVAP": 2}),
            (12, {"population": 10, "nx_node_id": 12, "MVAP": 2}),
            (13, {"population": 10, "nx_node_id": 13, "MVAP": 2}),
            (14, {"population": 10, "nx_node_id": 14, "MVAP": 2}),
            (15, {"population": 10, "nx_node_id": 15, "MVAP": 2}),
            (16, {"population": 10, "nx_node_id": 16, "MVAP": 2}),
            (17, {"population": 10, "nx_node_id": 17, "MVAP": 2}),
            (18, {"population": 10, "nx_node_id": 18, "MVAP": 2}),
            (19, {"population": 10, "nx_node_id": 19, "MVAP": 2}),
        ]
    )

    nx_graph.add_edges_from(
        [
            (0, 1),
            (0, 5),
            (1, 2),
            (1, 6),
            (2, 3),
            (2, 7),
            (3, 4),
            (3, 8),
            (4, 9),
            (5, 6),
            # (5, 10),
            (6, 7),
            # (6, 11),
            (7, 8),
            # (7, 12),
            (8, 9),
            # (8, 13),
            # (9, 14),
            (10, 11),
            (10, 15),
            (11, 12),
            (11, 16),
            (12, 13),
            (12, 17),
            (13, 14),
            (13, 18),
            (14, 19),
            (15, 16),
            (16, 17),
            (17, 18),
            (18, 19),
        ]
    )

    return nx_graph

@pytest.fixture
def four_by_five_grid_rx(four_by_five_grid_nx):
    # Create an RX Graph object with attributes
    rx_graph = rx.networkx_converter(four_by_five_grid_nx, keep_attributes=True)
    return rx_graph

def top_level_graph_is_properly_configured(graph):
    # This routine tests that top-level graphs (not a subgraph) 
    # are properly configured
    assert graph._is_a_subgraph == False, \
      "Top-level graph _is_a_subgraph is True"
    assert hasattr(graph, "_node_id_to_parent_node_id_map"), \
      "Graph._node_id_to_parent_node_id_map is not set"
    assert hasattr(graph, "_node_id_to_original_nx_node_id_map"), \
      "Graph._node_id_to_original_nx_node_id_map is not set"

def test_from_networkx(four_by_five_grid_nx):
    graph = Graph.from_networkx(four_by_five_grid_nx)
    assert len(graph.node_indices) == 20, \
      f"Expected 20 nodes but got {len(graph.node_indices)}"
    assert len(graph.edge_indices) == 26, \
      f"Expected 26 edges but got {len(graph.edge_indices)}"
    assert graph.node_data(1)["population"] == 10, \
      f"Expected population of 10 but got {graph.node_data(1)['population']}"
    top_level_graph_is_properly_configured(graph)

def test_from_rustworkx(four_by_five_grid_nx):
    rx_graph = rx.networkx_converter(four_by_five_grid_nx, keep_attributes=True)
    graph = Graph.from_rustworkx(rx_graph)
    assert len(graph.node_indices) == 20, \
      f"Expected 20 nodes but got {len(graph.node_indices)}"
    assert graph.node_data(1)["population"] == 10, \
      f"Expected population of 10 but got {graph.node_data(1)['population']}"
    top_level_graph_is_properly_configured(graph)

@pytest.fixture
def four_by_five_graph_nx(four_by_five_grid_nx):
    # Create an NX Graph object with attributes
    graph = Graph.from_networkx(four_by_five_grid_nx)
    return graph

@pytest.fixture
def four_by_five_graph_rx(four_by_five_grid_nx):
    # Create an NX Graph object with attributes
    #
    # Instead of using from_rustworkx(), we use
    # convert_from_nx_to_rx() because tests below
    # depend on the node_id maps that are created
    # by convert_from_nx_to_rx()
    #
    graph = Graph.from_networkx(four_by_five_grid_nx)
    converted_graph = graph.convert_from_nx_to_rx()
    return converted_graph

def test_convert_from_nx_to_rx(four_by_five_graph_nx):
    graph = four_by_five_graph_nx    # more readable
    converted_graph = graph.convert_from_nx_to_rx()

    # Same number of nodes
    assert len(graph.node_indices) == 20, \
      f"Expected 20 nodes but got {len(graph.node_indices)}"
    assert len(converted_graph.node_indices) == 20, \
      f"Expected 20 nodes but got {len(graph.node_indices)}"

    # Same number of edges
    assert len(graph.edge_indices) == 26, \
      f"Expected 26 edges but got {len(graph.edge_indices)}"
    assert len(converted_graph.edge_indices) == 26, \
      f"Expected 26 edges but got {len(graph.edge_indices)}"

    # Node data is the same
    # frm: TODO: Refactoring:  Do this the clever Python way and test ALL at the same time
    for node_id in graph.node_indices:
        assert graph.node_data(node_id)["population"] == 10, \
          f"Expected population of 10 but got {graph.node_data(node_id)['population']}"
        assert graph.node_data(node_id)["nx_node_id"] == node_id, \
          f"Expected nx_node_id of {node_id} but got {graph.node_data(node_id)['nx_node_id']}"
        assert graph.node_data(node_id)["MVAP"] == 2, \
          f"Expected MVAP of 2 but got {graph.node_data(node_id)['MVAP']}"
    for node_id in converted_graph.node_indices:
        assert graph.node_data(node_id)["population"] == 10, \
          f"Expected population of 10 but got {graph.node_data(node_id)['population']}"
        # frm: TODO: Code: Need to use node_id map to get appropriate node_ids for RX graph
        # assert graph.node_data(node_id)["nx_node_id"] == node_id, \
        #   f"Expected nx_node_id of {node_id} but got {graph.node_data(node_id)['nx_node_id']}"
        assert graph.node_data(node_id)["MVAP"] == 2, \
          f"Expected MVAP of 2 but got {graph.node_data(node_id)['MVAP']}"

    # Confirm that the node_id map to the "original" NX node_ids is correct
    for node_id in converted_graph.nodes:
        # get the "original" NX node_id
        nx_node_id = converted_graph._node_id_to_original_nx_node_id_map[node_id]
        # confirm that the converted node has "nx_node_id" set to the NX node_id.  This
        # is an artifact of the way the NX graph was constructed.
        assert converted_graph.node_data(node_id)["nx_node_id"] == nx_node_id

def test_get_edge_from_edge_id(four_by_five_graph_nx, four_by_five_graph_rx):

    # Test that get_edge_from_edge_id works for both NX and RX based Graph objects

    # NX edges and edge_ids are the same, so this first test is trivial
    #
    nx_edge_id = (0, 1)
    nx_edge = four_by_five_graph_nx.get_edge_from_edge_id(nx_edge_id)
    assert nx_edge == (0, 1)

    # RX edge_ids are assigned arbitrarily, so without using the nx_to_rx_node_id_map
    # we can't know which edge got what edge_id, so this test just verifies that
    # there is an edge tuple associated with edge_id, 0
    #
    rx_edge_id = 0    # arbitrary id - but there is always an edge with id == 0
    rx_edge = four_by_five_graph_rx.get_edge_from_edge_id(rx_edge_id)
    assert isinstance(rx_edge[0], int), "RX edge does not exist (0)"
    assert isinstance(rx_edge[1], int), "RX edge does not exist (1)"

def test_get_edge_id_from_edge(four_by_five_graph_nx, four_by_five_graph_rx):

    # Test that get_edge_id_from_edge works for both NX and RX based Graph objects

    # NX edges and edge_ids are the same, so this first test is trivial
    #
    nx_edge = (0, 1)
    nx_edge_id = four_by_five_graph_nx.get_edge_id_from_edge(nx_edge)
    assert nx_edge_id == (0, 1)

    # Test that get_edge_id_from_edge returns an integer value and that
    # when that value is used to retrieve an edge tuple, we get the
    # tuple value that is expected
    #
    rx_edge = (0, 1)
    rx_edge_id = four_by_five_graph_rx.get_edge_id_from_edge(rx_edge)
    assert isinstance(rx_edge_id, int), "Edge ID not found for edge"
    found_rx_edge = four_by_five_graph_rx.get_edge_from_edge_id(rx_edge_id)
    assert found_rx_edge == rx_edge, "Edge ID does not yield correct edge value"

def test_add_edge():
    # At present (October 2025), there is nothing to test.  The
    # code just delegates to NetworkX or RustworkX to create
    # the edge.
    #
    # However, it is conceivable that in the future, when users
    # stop using NX altogether, there might be a reason for a
    # test, so this is just a placeholder for that future test...
    #
    assert True

def test_subgraph(four_by_five_graph_rx):

    """
    Subgraphs are one of the most dangerous areas of the code.
    In NX, subgraphs preserve node_ids - that is, the node_id
    in the subgraph is the same as the node_id in the parent.
    However, in RX, that is not the case - RX always creates
    new node_ids starting at 0 and increasing by one 
    sequentially, so in general a node in an RX subgraph 
    will have a different node_id than it has in the parent
    graph.

    To deal with this, the code creates a map from the 
    node_id in a subgraph to the node_id in the parent
    graph, _node_id_to_parent_node_id_map.  This test verifies
    that this map is properly created.

    In addition, all RX based graphs that came from an NX
    based graph record the "original" NX node_ids in 
    another node_id map, _node_id_to_original_nx_node_id_map

    When we create a subgraph, this map needs to be 
    established for the subgraph.  This test verifies
    that this map is properly created.

    Note that this test is only configured to work on
    RX based Graph objects because the only uses of subgraph 
    in the gerrychain codebase is on RX based Graph objects.
    """

    # Create a subgraph for an arbitrary set of nodes:
    subgraph_node_ids = [2, 4, 5, 8, 11, 13]
    parent_graph_rx = four_by_five_graph_rx     # make the code below clearer
    subgraph_rx = parent_graph_rx.subgraph(subgraph_node_ids)

    assert \
      len(subgraph_node_ids) == len(subgraph_rx), \
      "Number of nodes do not agree"

    # verify that _node_id_to_parent_node_id_map is correct
    for subgraph_node_id, parent_node_id in subgraph_rx._node_id_to_parent_node_id_map.items():
        # check that each node in subgraph has the same data (is the same node)
        # as the node in the parent that it is mapped to
        #
        subgraph_stored_node_id = subgraph_rx.node_data(subgraph_node_id)["nx_node_id"]
        subgraph_stored_node_id = subgraph_rx.node_data(subgraph_node_id)["nx_node_id"]
        parent_stored_node_id = parent_graph_rx.node_data(parent_node_id)["nx_node_id"]
        assert \
          parent_stored_node_id == subgraph_stored_node_id, \
          f"_node_id_to_parent_node_id_map is incorrect"

    # verify that _node_id_to_original_nx_node_id_map is correct
    for subgraph_node_id, original_node_id in subgraph_rx._node_id_to_original_nx_node_id_map.items():
        subgraph_stored_node_id = subgraph_rx.node_data(subgraph_node_id)["nx_node_id"]
        assert \
          subgraph_stored_node_id  == original_node_id, \
          f"_node_id_to_original_nx_node_id_map is incorrect"

def test_num_connected_components(four_by_five_graph_nx, four_by_five_graph_rx):
    num_components_nx = four_by_five_graph_nx.num_connected_components() 
    num_components_rx = four_by_five_graph_rx.num_connected_components() 
    assert \
      num_components_nx == 2, \
      f"num_components: expected 2 but got {num_components_nx}"
    assert \
      num_components_rx == 2, \
      f"num_components: expected 2 but got {num_components_rx}"

def test_subgraphs_for_connected_components(four_by_five_graph_nx, four_by_five_graph_rx):

    subgraphs_nx = four_by_five_graph_nx.subgraphs_for_connected_components()
    subgraphs_rx = four_by_five_graph_rx.subgraphs_for_connected_components()

    assert len(subgraphs_nx) == 2
    assert len(subgraphs_rx) == 2

    assert len(subgraphs_nx[0]) == 10
    assert len(subgraphs_nx[1]) == 10
    assert len(subgraphs_rx[0]) == 10
    assert len(subgraphs_rx[1]) == 10

    # Check that each subgraph (NX-based Graph) has correct nodes in it
    node_ids_nx_0 = subgraphs_nx[0].node_indices   
    node_ids_nx_1 = subgraphs_nx[1].node_indices   
    assert node_ids_nx_0 == {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}
    assert node_ids_nx_1 == {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}

    # Check that each subgraph (RX-based Graph) has correct nodes in it
    node_ids_rx_0 = subgraphs_rx[0].node_indices   
    node_ids_rx_1 = subgraphs_rx[1].node_indices   
    original_nx_node_ids_rx_0 = subgraphs_rx[0].original_nx_node_ids_for_set(node_ids_rx_0)
    original_nx_node_ids_rx_1 = subgraphs_rx[1].original_nx_node_ids_for_set(node_ids_rx_1)
    assert original_nx_node_ids_rx_0 == {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}
    assert original_nx_node_ids_rx_1 == {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}

def test_to_networkx_graph():
    # There is already a test for this in another file
    assert True

def test_add_data():
    # This is already tested in test_make_graph.py
    assert True

########################################################
# Long utility routine to determine if there is a cycle
# in a graph (with integer node_ids).
########################################################

def graph_has_cycle(set_of_edges):

    #
    # Given a set of edges that define a graph, determine
    # if the graph has cycles.
    #
    # This will allow us to test that predecessors and
    # successors are in fact trees with no cycles.
    #
    # The approach is to do a depth-first-search that
    # remembers each node it has visited, and which
    # signals that a cycle exists if it revisits a node
    # it has already visited
    #
    # Note that this code assumes that the set of nodes
    # is a sequential list starting at zero with no gaps
    # in the sequence.  This allows us to use a simplified
    # adjacency matrix which is adequate for testing
    # purposes.
    #
    # The adjacency matrix is just a 2D square matrix
    # that has a 1 value for element (i,j) iff there
    # is an edge from node i to node j.  Note that
    # because we deal with undirected graphs the matrix
    # is symetrical - edges go both ways...
    #

    def add_edge(adj_matrix, s, t):
        # Add an edge to an adjacency matrix
        adj_matrix[s][t] = 1
        adj_matrix[t][s] = 1  # Since it's an undirected graph

    def delete_edge(adj_matrix, s, t):
        # Delete an edge from an adjacency matrix
        adj_matrix[s][t] = 0
        adj_matrix[t][s] = 0  # Since it's an undirected graph

    def create_empty_adjacency_matrix(num_nodes):
        # create 2D array, num_nodes x num_nodes
        adj_matrix = [[0] * num_nodes for _ in range(num_nodes)]
        return adj_matrix

    def create_adjacency_matrix_from_set_of_edges(set_of_edges):

        # determine num_nodes
        #
        set_of_nodes = set()
        for edge in set_of_edges:
            for node in edge:
                set_of_nodes.add(node)
        num_nodes = len(set_of_nodes)
        list_of_nodes = list(set_of_nodes)

        # We need node_ids that start at zero and go
        # up sequentially with no gaps, so create a
        # map for new node_ids
        new_node_id_map = {}
        for index, node_id in enumerate(list_of_nodes):
            new_node_id_map[node_id] = index

        # Now create a new set of edges with the new node_ids
        new_set_of_edges = set()
        for edge in set_of_edges:
            new_edge = (
              new_node_id_map[edge[0]], new_node_id_map[edge[1]]
            )
            new_set_of_edges.add(new_edge)

        # debugging:

        # create an empty adjacency matrix
        #
        adj_matrix = create_empty_adjacency_matrix(num_nodes)

        # add the edges to the adjacency matrix
        #
        for edge in new_set_of_edges:
            add_edge(adj_matrix, edge[0], edge[1])

        return adj_matrix

    def inner_has_cycle(adj_matrix, visited, s, visit_list):
        # This routine does a depth first search looking
        # for cycles - if it encounters a node that it has
        # already seen then it returns True.

        # Record having visited this node
        #
        visited[s] = True
        visit_list.append(s)

        # Recursively visit all adjacent vertices looking for cycles
        # If we have already visited a node, then there is a cycle...
        #
        for i in range(len(adj_matrix)):
            # Recurse on every adjacent / child node...
            if adj_matrix[s][i] == 1:
                if visited[i]:
                    return True
                else:
                    # remove this edge from adjacency matrix so we
                    # don't follow link back to node, i.
                    #
                    delete_edge(adj_matrix, s, i)
                    if inner_has_cycle(adj_matrix, visited, i, visit_list):
                        return True
        return False

    adj_matrix = create_adjacency_matrix_from_set_of_edges(set_of_edges)
    visited = [False] * len(adj_matrix)
    visit_list = []
    root_node = 0 # arbitrary, but every graph has a node 0
    cycle_found = \
      inner_has_cycle(adj_matrix, visited, root_node, visit_list)
    return cycle_found

def test_graph_has_cycle():
    # Test to make sure the utility routine, graph_has_cycle, works

    # First try with no cycle
    # Define the edges of the graph
    set_of_edges = {
      (11, 2),
      (11, 0),
      # (2, 0),   # no cycle without this edge
      (2, 3),
      (2, 4)
    }
    the_graph_has_a_cycle = graph_has_cycle(set_of_edges)
    assert the_graph_has_a_cycle == False

    # Now try with a cycle
    # Define the edges of the graph
    set_of_edges = {
      (11, 2),
      (11, 0),
      (2, 0),      # this edge creates a cycle
      (2, 3),
      (2, 4)
    }
    the_graph_has_a_cycle = graph_has_cycle(set_of_edges)
    assert the_graph_has_a_cycle == True

def test_generic_bfs_edges(four_by_five_graph_nx, four_by_five_graph_rx):
    #
    # The routine, generic_bfs_edges() returns an ordered list of 
    # edges from a breadth-first traversal of a graph, starting
    # at the given node.
    #
    # For our graphs, there are two connected components (the first
    # two rows and the last two rows) and each component is a
    # grid:
    #
    #    0 -  1 -  2 -  3 -  4
    #    |    |    |    |    |
    #    5 -  6 -  7 -  8 -  9
    #
    #   10 - 11 - 12 - 13 - 14
    #    |    |    |    |    |
    #   15 - 16 - 17 - 18 - 19
    #
    # So, a BFS starting at 0 should produce something like:
    #
    #   [ (0,5), (0,1), (1,6), (1,2), (2,7), (2,3), (3,8), (3,4), (4,9) ]
    #
    # However, the specific order that is returned depends on the 
    # internals of the algorithm.
    #

    #
    bfs_edges_nx_0 = set(four_by_five_graph_nx.generic_bfs_edges(0))
    expected_set_of_edges = { \
      (0,5), (0,1), (1,6), (1,2), (2,7), (2,3), (3,8), (3,4), (4,9) \
    }
    # debugging:
    assert bfs_edges_nx_0 == expected_set_of_edges

    # Check that generic_bfs_edges() does not produce a cycle
    the_graph_has_a_cycle = graph_has_cycle(bfs_edges_nx_0)
    assert the_graph_has_a_cycle == False
    bfs_edges_nx_12 = set(four_by_five_graph_nx.generic_bfs_edges(12))
    the_graph_has_a_cycle = graph_has_cycle(bfs_edges_nx_12)
    assert the_graph_has_a_cycle == False

    """
    TODO: Testing:
      * Think about whether this test is actually appropriate.  The
        issue is that the expected_set_of_edges is the right set
        for this particular graph, but I am not sure that this is
        a good enough test.  Think about other situations...

      * Think about whether to verify that the BFS returned
        has no cycles.  It doesn't in this particular case,
        but perhaps we should have more cases that stress the test...
    """
def test_generic_bfs_successors_generator():
    # TODO: Testing: Write a test for this routine
    # 
    # Note that the code for this routine is very straight-forward, so
    # writing a test is not high-priority.  The only reason I did not 
    # just go ahead and write one is because it was not immediately 
    # clear to me how to write the test - more work than doing a 
    # thorough code review...
    #
    assert True

def test_generic_bfs_successors():
    # TODO: Testing: Write a test for this routine
    #
    # Code is trivial, but because this routine is important it 
    # deserves a test - just not clear off top of my head how 
    # to write the test...
    #
    assert True

def test_generic_bfs_predecessors():
    # TODO: Testing: Write a test for this routine
    #
    # Code is trivial, but because this routine is important it 
    # deserves a test - just not clear off top of my head how 
    # to write the test...
    #
    assert True

def test_predecessors():
    # TODO: Testing: Write a test for this routine
    #
    # Code is trivial, but because this routine is important it 
    # deserves a test - just not clear off top of my head how 
    # to write the test...
    #
    assert True

def test_successors():
    # TODO: Testing: Write a test for this routine
    #
    # Code is trivial, but because this routine is important it 
    # deserves a test - just not clear off top of my head how 
    # to write the test...
    #
    assert True

def test_laplacian_matrix():
    # TODO: Testing: Write a test for this routine
    #
    # Not clear off the top of my head how 
    # to write the test...
    #
    assert True

def test_normalized_laplacian_matrix():
    # TODO: Testing: Write a test for this routine
    #
    # This routine has not yet been implemented (as
    # of October 2025), but when it is implemented
    # we should add a test for it...
    #
    assert True


"""
=============================================================

TODO: Code: ???

  * Aliasing concerns:

    It occurs to me that the RX node_data is aliased with the NX node_data.
    That is, the data dictionaries in the NX Graph are just retained
    when the NX Graph is converted to be an RX Graph - so if you change
    the data in the RX Graph, the NX Graph from which we created the RX
    graph will also be changed.

    I believe that this is also true for subgraphs for both NX and RX,
    meaning that the node_data in the subgraph is the exact same
    data dictionary in the parent graph and the subgraph.

    I am not sure if this is a problem or not, but it is something
    to be tested / thought about...

  * NX allows node_ids to be almost anything - they can be integers,
    strings, even tuples.  I think that they just need to be hashable.

    I don't know if we need to test that non-integer NX node_ids 
    don't cause a problem.  There are tests elsewhere that have
    NX node_ids that are tuples, and that test passes, so I think
    we are OK, but there are no tests specifically targeting this
    issue that I know of.

=============================================================
"""
