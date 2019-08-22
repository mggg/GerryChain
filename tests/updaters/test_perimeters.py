from collections import defaultdict

from gerrychain import MarkovChain
from gerrychain.accept import always_accept
from gerrychain.constraints import no_vanishing_districts, single_flip_contiguous
from gerrychain.grid import Grid
from gerrychain.proposals import propose_random_flip


def setup():
    grid = Grid((4, 4), with_diagonals=False)
    flipped_grid = grid.flip({(2, 1): 3})
    return grid, flipped_grid


def test_perimeter_handles_flips_with_a_simple_grid():
    grid, flipped_grid = setup()

    result = sorted(flipped_grid["perimeter"].values())

    assert result == [8, 8, 8, 10]


def test_interior_perimeter_handles_flips_with_a_simple_grid():
    grid, flipped_grid = setup()

    result = sorted(flipped_grid["interior_boundaries"].values())

    assert result == [4, 4, 4, 6]


def test_cut_edges_by_part_handles_flips_with_a_simple_grid():
    grid, flipped_grid = setup()

    result = flipped_grid["cut_edges_by_part"]

    assert result[0] == {
        ((1, 0), (2, 0)),
        ((1, 1), (2, 1)),
        ((0, 1), (0, 2)),
        ((1, 1), (1, 2)),
    }
    assert result[1] == {
        ((1, 0), (2, 0)),
        ((2, 0), (2, 1)),
        ((2, 1), (3, 1)),
        ((3, 1), (3, 2)),
    }
    assert result[2] == {
        ((0, 1), (0, 2)),
        ((1, 1), (1, 2)),
        ((1, 2), (2, 2)),
        ((1, 3), (2, 3)),
    }
    assert result[3] == {
        ((1, 1), (2, 1)),
        ((2, 0), (2, 1)),
        ((2, 1), (3, 1)),
        ((3, 1), (3, 2)),
        ((1, 2), (2, 2)),
        ((1, 3), (2, 3)),
    }


def test_cut_edges_by_part_agrees_with_cut_edges_on_a_simple_grid():
    grid, flipped_grid = setup()

    result = flipped_grid["cut_edges_by_part"]

    for edge in flipped_grid["cut_edges"]:
        source, target = edge
        assert edge in result[flipped_grid.assignment[source]]
        assert edge in result[flipped_grid.assignment[target]]

    for part in result:
        for edge in result[part]:
            assert edge in flipped_grid["cut_edges"]


def test_tally_handles_flips_for_a_simple_grid():
    grid, flipped_grid = setup()

    result = flipped_grid["area"]

    assert result == {0: 4, 1: 3, 2: 4, 3: 5}


def test_perimeter_match_naive_perimeter_at_every_step():
    partition = Grid((10, 10), with_diagonals=True)

    chain = MarkovChain(
        propose_random_flip,
        [single_flip_contiguous, no_vanishing_districts],
        always_accept,
        partition,
        1000,
    )

    def get_exterior_boundaries(partition):
        graph_boundary = partition["boundary_nodes"]
        exterior = defaultdict(lambda: 0)
        for node in graph_boundary:
            part = partition.assignment[node]
            exterior[part] += partition.graph.nodes[node]["boundary_perim"]
        return exterior

    def get_interior_boundaries(partition):
        cut_edges = {
            edge for edge in partition.graph.edges if partition.crosses_parts(edge)
        }
        interior = defaultdict(int)
        for edge in cut_edges:
            for node in edge:
                interior[partition.assignment[node]] += partition.graph.edges[edge][
                    "shared_perim"
                ]
        return interior

    def expected_perimeter(partition):
        interior_boundaries = get_interior_boundaries(partition)
        exterior_boundaries = get_exterior_boundaries(partition)
        expected = {
            part: interior_boundaries[part] + exterior_boundaries[part]
            for part in partition.parts
        }
        return expected

    for state in chain:
        expected = expected_perimeter(state)
        assert expected == state["perimeter"]

