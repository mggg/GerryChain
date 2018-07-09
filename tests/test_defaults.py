import rundmcmc.defaults


def test_the_chain_runs():
    partition = rundmcmc.defaults.PA_partition('./rundmcmc/testData/PA_graph_with_data.json')
    chain = rundmcmc.defaults.BasicChain(partition, total_steps=100)
    for state in chain:
        assert state is not None


def test_defaults_are_importable():
    assert rundmcmc.defaults
