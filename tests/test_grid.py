from rundmcmc.defaults import GridChain, Grid


def test_grid_can_run_with_grid_chain():
    grid = Grid((10, 10))

    # verify we can initialize a chain without error
    chain = GridChain(grid, total_steps=10)

    # verify that we can step through the chain  without error
    for state in chain:
        assert isinstance(state, Grid)
