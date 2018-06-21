"""
    #TODO
    - smart histograms
    - graph metadata:
        • #vertices, #edges
        • discrete diameter
        • # of faces (by eulerian characteristic)
        • graph density
"""
import networkx as nx
import networkx.algorithms as nxa


def graph_report(graph):
    """
        Generates a basic report on simple properties of the graph.
        :graph: NetworkX graph object.
    """
    vertices, edges = len(list(nx.nodes(graph))), len(list(nx.edges(graph)))
    density = nx.density(graph)
    connectivity = nxa.node_connectivity(graph)
    return vertices, edges, density, connectivity
    