import sys
import networkx

a = [[3,8838,2],[8956,8843,5,7,45,3,2,8838]]
b = [[0.01528087,0.00587986,0.01549645],[0.0028062936,0.00869499,0.02802319,0.02752234,0.03923771,0.05836117,0.03923771,0.0028062936]]
c = [1, 1, 1, 1, 2, 2, 2, 2, 2, 2]
pop = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

def add_data_to_graph(your_data, graph, data_name):
    '''Adds data to the graph after it has been constructed.
    
    :your_data: A column with the data you would like to add to the nodes(VTDs).
    :graph: The graph you constructed and want to run chain on.
    :data_name: How you would like the data on the node layer labeled.
    
    '''
    #Check to make sure threre is a one-to-one between data and VTDs
    if len(graph) != len(your_data):
        print("Your column length doesn't match the number of nodes!")
        sys.exit(1)
        
    #Adding data to the nodes
    for i,j in enumerate(graph.nodes()):
        graph.nodes[j][data_name] = your_data[i]

def construct_graph(lists_of_neighbors, lists_of_perims, district_list):
    '''Constructs your starting graph to run chain on
    
    :lists_of_neighbors: A list of lists stating the neighbors of each VTD.
    :lists_of_perims: List of lists of perimeters.
    :district_list: List of congressional districts associated to each node(VTD).
    
    '''
    graph = networkx.Graph()
    
    #Creating the graph itself
    for vtd, list_nbs in enumerate(lists_of_neighbors):
        for d in list_nbs:
            graph.add_edge(vtd, d)
    
    #Add perims to edges
    for i, nbs in enumerate(lists_of_neighbors):
        for x, nb in enumerate(nbs):
            graph.add_edge(i, nb, perim=lists_of_perims[i][x])
    
    #Add districts to each node(VTD)
    for i,j in enumerate(graph.nodes()):
        graph.nodes[j]['CD'] = district_list[i]
            
    return graph

#Creating the base graph
G = construct_graph(a, b, c)

#Adding data to our nodes(VTDs)
add_data_to_graph(pop, G, 'Pop')

nx.draw(G)
print(G.edges(data=True))
print(G.nodes(data=True))