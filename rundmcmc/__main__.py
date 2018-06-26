import json
import geopandas as gp
import networkx.readwrite

from rundmcmc.accept import always_accept
from rundmcmc.chain import MarkovChain
from rundmcmc.make_graph import add_data_to_graph, get_assignment_dict
from rundmcmc.partition import Partition
from rundmcmc.proposals import propose_random_flip
from rundmcmc.scores import mean_median, mean_thirdian
from rundmcmc.updaters import Tally, cut_edges, votes_updaters, county_splits
from rundmcmc.validity import Validator, single_flip_contiguous, refuse_new_splits


def example_partition():
    df = gp.read_file("./testData/mo_cleaned_vtds.shp")

    with open("./testData/MO_graph.json") as f:
        graph_json = json.load(f)

    graph = networkx.readwrite.json_graph.adjacency_graph(graph_json)

    assignment = get_assignment_dict(df, "GEOID10", "CD")

    add_data_to_graph(df, graph, ['PR_DV08', 'PR_RV08', 'POP100', 'COUNTYFP10'], id_col='GEOID10')

    updaters = {
        **votes_updaters(['PR_DV08', 'PR_RV08'], election_name='08'),
        'population': Tally('POP100', alias='population'),
        'cut_edges': cut_edges,
        'counties': county_splits("counties", "COUNTYFP10")
    }

    return Partition(graph, assignment, updaters)


def print_summary(partition, scores):
    print("")
    for name, score in scores.items():
        print(f"{name}: {score(partition, 'PR_DV08%')}")


def main():
    initial_partition = example_partition()

    validator = Validator([single_flip_contiguous, refuse_new_splits("counties")])
    chain = MarkovChain(propose_random_flip, validator, always_accept,
                        initial_partition, total_steps=1000)
    scores = {
        'Mean-Median': mean_median,
        'Mean-Thirdian': mean_thirdian
    }

    test_counties = ["007", "099", "205", "127"]
    for partition in chain:
        print_summary(partition, scores)
        for county in test_counties:
            info = partition["counties"][county]
            print("county {}: {} ({})".format(county, info.split, info.contains))


if __name__ == "__main__":
    import sys
    sys.path.append('/usr/local/Cellar/graph-tool/2.26_2/lib/python3.6/site-packages/')
    main()
