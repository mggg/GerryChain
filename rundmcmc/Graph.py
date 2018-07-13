# I know this is an abhorrent way to import things, but I promise that this is
# the way the docs told me to do it.
from graph_tool.all import *
import geopandas as gp
import os
import networkx as nx
import json
import numpy as np
from rundmcmc.make_graph import construct_graph

from rundmcmc.make_graph import add_data_to_graph, construct_graph


class Graph:
    """
        This class is an abstraction layer that sits in between NetworkX (or
        graph-tool) and the rest of the program.

        TODO Figure out which methods run faster at scale. Currently, getting
        vertices and edges are faster with graph-tool, but NetworkX has the
        upper hand on getting node attributes and neighbors.
    """

    def __init__(self, path=None, geoid_col=None, graph_tool=False):
        """
            Main properties of the Graph instance.
                :library:   String denoting which graph implementation library
                            is being used.
                :graph:     Graph object.
                :path:      Path to the source file of the graph.
        """
        self.library = "graph_tool" if graph_tool else "networkx"
        self.graph = None
        self.path = None
        self.id = geoid_col

        """
            Internal properties:
                :_converted:               Has this graph been converted to graph-tool?
                :_data_added:              Has data been added to this graph?
                :_xml_location:            GraphML filepath.
                :_nodelookup_geoid_to_idx: Netowrkx node ID to graph-tool node index lookup
                :_nodelookup_idx_to_geoid: Graph-tool node index to netowrkx node ID lookup
                :_edgelookup:
                :_vertexdata:
                :_edgedata:
        """
        self._converted = False
        self._data_added = False
        self._xml_location = None
        self._nodelookup_geoid_to_idx = None
        self._nodelookup_idx_to_geoid = None
        self._edgelookup = None
        self._vertexdata = None
        self._edgedata = None

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
            raise RuntimeError(err)
            return

        # Determines whether to read in from shapefiles or geojson.
        if extension == ".shp":
            df = gp.read_file(path)
            self.graph = construct_graph(df, geoid_col, data_source_type='geo_data_frame', data_cols=['CD', 'ALAND'])
        elif extension == ".json":
            # Prepping for the file-read
            adjacency = None
            with open(path) as f:
                adjacency = json.load(f)
                self.graph = nx.readwrite.json_graph.adjacency_graph(adjacency)

        # Generate a lookup table, assuming the user is going to convert to
        # graph-tool.


    def add_data(self, path=None, col_names=None, id_col=None):
        """
            Shoves data (from the dataframe) into the graph. Uses Preston's
            add_data_to_graph.
        """
        df = gp.read_file(path)
        add_data_to_graph(df, self.graph, col_names, id_col)


    def convert(self):
        """
            Converts an existing NetworkX graph to graph-tool. This method uses
            a simple XML write/read; i.e. NetworkX writes the graph to XML in a
            format readable by graph-tool. Additionally, the XML file that's
            written is available for the life of the Graph instance, then thrown
            out afterward.

            TODO See if we can write to a buffer/stream instead of a file... that
            may prove faster.

            TODO Do a user's permissions affect this program's ability to write
            in the directory where it's installed? Currently, the XML file is
            being created in the *user's* current working directory, not where
            the RunDMCMC is put... might be worth looking into.

            TODO Discuss if there should be a flag (--preserve-conversion, maybe)
            to not delete the XML file when this object is garbage-collected. If
            a user is running a bunch of chains and getting their adjacency (and
            other) data from, say, a GeoJSON file, and they're using graph-tool,
            wouldn't it make sense to provide them with an option to not have to
            re-convert each time? I feel this is something to address.
        """

        # Check that the user actually wants to convert to graph-tool.
        if self.library != "graph-tool":
            # Try to convert the graph to GraphML
            try:
                self._xml_location = os.getcwd() + "/graph.xml"
                nx.write_graphml_xml(self.graph, (self._xml_location))
                self.graph = load_graph(self._xml_location)
                self._converted = True
                self.library = "graph_tool"
                self._nodelookup_geoid_to_idx = {self.graph.vertex_properties[self.id][x]: x for x in range(len(list(self.graph.vertices())))}
                self._nodelookup_idx_to_geoid = {x: self.graph.vertex_properties[self.id][x] for x in range(len(list(self.graph.vertices())))}
                self._edgelookup = {(self._nodelookup_idx_to_geoid[tuple(e)[0]], self._nodelookup_idx_to_geoid[tuple(e)[1]]): i for i, e in enumerate(list(self.graph.edges()))}
                self._edgelookup.update({(self._nodelookup_idx_to_geoid[tuple(e)[1]], self._nodelookup_idx_to_geoid[tuple(e)[0]]): i for i, e in enumerate(list(self.graph.edges()))})
                #print(self._edgelookup)
                self._vertexdata = {
                    x: list(y) for x, y in list(self.graph.vertex_properties.items())
                }
                self._edgedata = {
                    x: list(y) for x, y in list(self.graph.edge_properties.items())
                }
                self._num_nodes = len(list(self._nodelookup_geoid_to_idx))
                self._nodelist = np.asarray(list(self.graph.vertex_properties["_graphml_vertex_id"]))
                return self.graph
            except:
                err = "Encountered an error during conversion. Aborting."
                raise RuntimeError(err)
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


    def node(self, node_id, attribute):
        if self.library == "networkx":
            return self.graph.nodes[node_id][attribute]
        else:
            gt_node_id = self._nodelookup_geoid_to_idx[node_id]
            #return list(self.graph.vertex_properties[attribute])[gt_node_id]
            return self._vertexdata[attribute][gt_node_id]


    def nodes(self, data=False):
        """
            Returns a numpy array over the nodes of the graph. Finding neighbors
            in graph-tool is significantly faster.
        """
        if self.library == "networkx":
            return iter(np.asarray(self.graph.nodes(data=data)))
        else:
            return self._nodelist

    def node_properties(self, prop):
        if self.library == "networkx":
            return [self.graph.node[x][prop] for x in self.graph.nodes()]
        else:
            return self._vertexdata[prop]


    def edge(self, edge_id, attribute):
        if self.library == "networkx":
            return self.graph.edges[edge_id][attribute]
        else:
            #print(edge_id)
            gt_edge_id = self._edgelookup[edge_id]
            return self._edgedata[attribute][gt_edge_id]


    def edges(self):
        """
            Returns a numpy array over the edges of the graph. See
            `Graph.nodes()` for more info on why the graph-tool call to get_edges
            is different.
        """
        if self.library == "networkx":
            return np.asarray(self.graph.edges())
        else:
            # the first two columns are the edges
            # connected and the last is the index
            geoids = np.asarray(list(self.graph.vertex_properties["_graphml_vertex_id"]))

            lookup = {}
            for idx, geoid in enumerate(geoids):
                lookup[idx] = geoid
            arr = np.asarray(list(self.graph.get_edges()))
            return np.vectorize(lookup.get)(arr[:, :2])


    def neighbors(self, node):
        if self.library == "networkx":
            return np.asarray(list(nx.all_neighbors(self.graph, node)))
        else:
            nodeidx = self._nodelookup_geoid_to_idx[node]
            return [self._nodelookup_idx_to_geoid[x] for x in self.graph.get_out_neighbors(nodeidx)]


    def get_node_attributes(self, node):
        """
            Returns a dict of each node's attributes.
        """
        if self.library == "networkx":
            return self.graph.node[node]
        else:
            # Create an empty properties dictionary and get the PropertyMap
            properties = {}
            propertymap = self.graph.vertex_properties

            # Iterate over each key in the PropertyMap, storing values on the way
            for prop in propertymap.keys():
                vprop = propertymap[prop]
                properties[prop] = vprop[self.graph.vertex(node)]

            return properties


    def connected(self, nodes):
        """
            Checks that the set of nodes is connected.
        """
        if self.library == 'networkx':
            return nx.is_connected(self.graph.subgraph(nodes))
        else:
            label = label_components(self.graph)[0]
            sub = GraphView(self.graph, vfilt=label.a == nodes)
            # need to keep thinking about this moving on for now
            pass


    def subgraph(self, nodes):
        """
            Finds the subgraph containing all nodes in `nodes`.
        """
        if self.library == 'networkx':
            return self.graph.subgraph(nodes)
        else:
            vfilt = np.zeros(self._num_nodes, dtype=bool)
            nodes = map(self._nodelookup_geoid_to_idx.get, nodes)
            for x in nodes:
                vfilt[x] = True
            return GraphView(self.graph,  vfilt=vfilt)


    def to_dict_of_dicts(self, part=None):
        """
            Returns the graph as a dictionary of dictionaries.
        """
        pass

    def from_dict_of_dicts(self):
        """
            Loads in the graph as a dictionary of dictionaries.
        """
        pass

    def to_dict_of_lists(self, nodelist=None):
        """
            Returns the graph as a dictionary of lists.
        """
        if self.library == 'networkx':
            return nx.to_dict_of_lists(self.graph, nodelist=nodelist)
        else:
            if nodelist is None:
                nodelist = list(range(self._num_nodes))
            d = {}
            for n in nodelist:
                d[n] = [nbr for nbr in self.neighbors(n) if nbr in nodelist]
            return d

    def from_dict_of_lists(self):
        """
            Loads in the graph as a dictionary of lists.
        """
        pass


if __name__ == "__main__":
    g = Graph("./testData/MO_graph.json")
    # g.convert()
    g.nodes()
    #print(g.connected())
