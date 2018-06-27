
# I know this is an abhorrent way to import things, but I promise that this is
# the way the docs told me to do it.
from graph_tool.all import *
from termcolor import colored
import geopandas as gp
import pysal as ps
import os
import networkx as nx
import json
import numpy as np
import time

from rundmcmc.make_graph import add_data_to_graph, construct_graph
from rundmcmc.validity import bfs

class Graph:
    """
        This class is an abstraction layer that sits in between NetworkX (or
        graph-tool) and the rest of the program.

        TODO Figure out which methods run faster at scale. Currently, getting
        vertices and edges are faster with graph-tool, but NetworkX has the
        upper hand on getting node attributes and getting neighbors.
    """
    def __init__(self, path=None, geoid_col=None, graph_tool=False):
        # Main properties of the Graph object.
        self.library = "graph_tool" if graph_tool else "networkx"
        self.graph = None

        """
            Internal properties:
                :_converted:    Has this graph been converted to graph-tool?
                :_data_added:   Has data been added to this graph?
                :_xml_location: GraphML filepath.
        """
        self._converted = False
        self._data_added = False
        self._xml_location = None

        # Try to make a graph if `path` is provided.
        if path:
            self.make_graph(path, geoid_col)


    def __del__(self):
        """
            Removes a file if a converted graph exists so there aren't any
            artifacts.
        """
        if self._xml_location:
            os.remove(self._xml_location)


    def make_graph(self, path, geoid_col=None):
        """ 
            Loads a graph from the specified data source. Called automatically
            in __init__, but can also be used as a simple auxiliary function if
            somebody wants to initialize the graph in a more visible way.

            Additionally, it automatically detects the filetype and loads the
            provided file the correct way.
        """
        _, extension = os.path.splitext(path)
        self.path = path

        # If we encounter an unsupported filetype, kill the program
        if not (extension == ".shp" or extension == ".json"):
            err = "The {} filetype is unsupported. Aborting.".format(extension)
            print(err, "red")
            return

        # Determines whether to read in from shapefiles or geojson.
        if extension == ".shp":
            df = gp.read_file(path)
            self.graph = construct_graph(df, geoid_col)
        elif extension == ".json":
            # Prepping for the file-read
            adjacency = None
            with open(path) as f:
                adjacency = json.load(f)
                self.graph = nx.readwrite.json_graph.adjacency_graph(adjacency)


    def add_data(self, path=None, col_names=None, id_col=None):
        """
            Shoves data (from the dataframe) into the graph. Uses Preston's
            add_data_to_graph.
        """
        df = gp.read_file(path)
        add_data_to_graph(df, self.graph, col_names, id_col) 


    def convert(self):
        """
            Converts an existing NetworkX graph to graph-tool.
        """
        err = "Are you sure you want to convert to graph-tool? [y/N] "

        # Check that the user actually wants to convert to graph-tool.
        if self.library != "graph-tool":
            answer = input(colored(err, "blue")).lower()
            if answer == "n" or answer == "no":
                print(colored("Aborting.", "red"))
                return

        # Try to convert the graph to GraphML
        try:
            self._xml_location = os.getcwd() + "/graph.xml"
            nx.write_graphml_xml(self.graph,(self._xml_location))
            self.graph = load_graph(self._xml_location)
            self._converted = True
            self.library = "graph_tool"
        except:
            print(colored("Encountered an error during conversion. Aborting.", "red"))
            return

    
    def export_to_file(self, format="json"):
        """
            Exports a graph in the specified file format. We'll include support
            for JSON, GeoJSON (if this is somehow different from regular JSON),
            GraphML, and shapefiles.

            TODO Passing graphs between NetworkX and Graph-Tool allows us to
            support a wide range of functionality, including exporting as
            shapefile.
        """
        pass


    def nodes(self):
        """
            Returns a numpy array over the nodes of the graph. Finding neighbors
            in graph-tool is significantly faster.

            TODO @psward, please work magic so that NetworkX and graph-tool both
            index by geoid – as of now, only NetworkX does that.
        """
        if self.library == "networkx":
            return np.asarray(self.graph.nodes())
        else:
            return self.graph.get_vertices()


    def edges(self):
        """
            Returns a numpy array over the edges of the graph. See
            `Graph.nodes()` for more info on why the graph-tool call to get_edges
            is different.
        """
        if self.library == "networkx":
            return np.asarray(self.graph.edges())
        else:
            return self.graph.get_edges()[:,1:]


    def neighbors(self, node):
        """
            Returns numpy array over the neighbors of node `node`. For whatever
            reason, graph-tool is worse than NetworkX at this call, but they're
            still close.
        """
        if self.library == "networkx":
            return np.asarray(list(nx.all_neighbors(self.graph, node)))
        else:
            return self.graph.get_out_neighbors(node)

    
    def get_node_attributes(self, node):
        """
            Returns a dict of each node's attributes.
        """
        if self.library == "networkx":
            return self.graph.node[node]
        else:
            properties = {}
            propertymap = self.graph.vertex_properties

            for prop in propertymap.keys():
                vprop = propertymap[prop]
                properties[prop] = vprop[self.graph.vertex(node)]
            
            return properties


    def connected(self, nodes):
        """
            Checks that the set of nodes is connected.
        """
        pass

        
    
    def subgraph(self, nodes):
        """
            Finds the subgraph containing all nodes in `nodes`.
        """
        pass


    def is_connected(self):
        """
            Checks whether the graph is connected.
        """
        pass


    def to_dict_of_dicts(self):
        """
            Returns the graph as a dictionary of dictionaries.
        """
        pass


    def from_dict_of_dicts(self):
        """
            Loads in the graph as a dictionary of dictionaries.
        """
        pass

    
    def to_dict_of_lists(self):
        """
            Returns the graph as a dictionary of lists.
        """
        pass


    def from_dict_of_lists(self):
        """
            Loads in the graph as a dictionary of lists.
        """
        pass


if __name__ == "__main__":
    g = Graph()
    g.make_graph("./testData/MO_graph.json")
    g.convert()

    start = time.time()
    
    print("Operation took {} seconds".format(str(end - start)))