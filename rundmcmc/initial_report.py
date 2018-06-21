
import geopandas as gp
from rundmcmc.make_graph import construct_graph, add_data_to_graph
from rundmcmc.graph_report import graph_report


def report(prorated=None, location="./testData/mo_dists.geojson"):
    """
        Takes in a geopandas dataframe of prorated voting data or the location
        of a shape/geojson file, generates a graph, and runs the initial report
        functions.
        :prorated: A dataframe of prorated data.
        :location: Filepath for a shape/geojson/csv file.
    """
    df = gp.read_file(location)
    graph = construct_graph(df, geoid_col="GEOID10")
    add_data_to_graph(df, graph, list(df), id_col="GEOID10")

    ### RUN ALL THE REPORTING THINGS! ###
    print(graph_report(graph))

if __name__ == "__main__":
    report()