import networkx

from rundmcmc.defaults import BasicChain, PA_partition


def parts_adjacency_matrix(partition):
    parts_graph = networkx.Graph()
    for part in partition.parts:
        parts_graph.add_node(part)
    for edge in partition['cut_edges']:
        source, destination = (partition.assignment[node] for node in edge)
        parts_graph.add_edge(source, destination)
    nodelist = sorted(partition.parts)
    return networkx.to_numpy_matrix(parts_graph, nodelist=nodelist)


def main():
    partition = PA_partition()
    chain = BasicChain(partition, 100)
    for state in chain:
        print(parts_adjacency_matrix(state))


if __name__ == '__main__':
    main()
