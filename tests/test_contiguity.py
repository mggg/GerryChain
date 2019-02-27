from gerrychain import Partition
from gerrychain.constraints.contiguity import contiguous_components


def test_contiguous_components(graph):
    partition = Partition(graph, {0: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 1, 7: 1, 8: 1})

    components = contiguous_components(partition)

    assert len(components[1]) == 2
    assert len(components[2]) == 1

    assert set(frozenset(g.nodes) for g in components[1]) == {
        frozenset([0, 1, 2]),
        frozenset([6, 7, 8]),
    }

    assert set(components[2][0].nodes) == {3, 4, 5}
