from rundmcmc.defaults import Grid


def setup():
    grid = Grid((4, 4), with_diagonals=False)
    flipped_grid = grid.merge({(2, 1): 3})
    return grid, flipped_grid


def test_perimeters_handles_flips_with_a_simple_grid():
    grid, flipped_grid = setup()

    result = sorted(flipped_grid['perimeters'].values())

    assert result == [8, 8, 8, 10]


def test_interior_perimeters_handles_flips_with_a_simple_grid():
    grid, flipped_grid = setup()

    result = sorted(flipped_grid['interior_boundaries'].values())

    assert result == [4, 4, 4, 6]


def test_cut_edges_by_part_handles_flips_with_a_simple_grid():
    grid, flipped_grid = setup()

    result = flipped_grid['cut_edges_by_part']

    assert result[0] == {((1, 0), (2, 0)), ((1, 1), (2, 1)), ((0, 1), (0, 2)), ((1, 1), (1, 2))}
    assert result[1] == {((1, 0), (2, 0)), ((2, 0), (2, 1)), ((2, 1), (3, 1)), ((3, 1), (3, 2))}
