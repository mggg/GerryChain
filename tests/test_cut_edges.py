from rundmcmc.defaults import PA_partition, BasicChain


def invalid_cut_edges(partition):
    invalid = [edge for edge in partition['cut_edges']
               if partition.assignment[edge[0]] == partition.assignment[edge[1]]]
    return invalid


def test_cut_edges_only_returns_edges_that_are_actually_cut():
    partition = PA_partition()
    chain = BasicChain(partition, 100)
    for state in chain:
        assert invalid_cut_edges(state) == []
