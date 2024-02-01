import random
random.seed(2018)
import pytest
from functools import partial
from concurrent.futures import ProcessPoolExecutor
from gerrychain import (
    MarkovChain, Partition, accept,
    constraints, proposals, updaters, Graph, tree)
from gerrychain.tree import ReselectException, BipartitionWarning


def run_chain_single(
    seed,
    category, 
    steps, 
    weight, 
    max_attempts=100000, 
    reselect=False
):
    from gerrychain import MarkovChain, Partition, accept, constraints, proposals, updaters, Graph, tree
    from gerrychain.tree import ReselectException
    from functools import partial
    import random

    graph = Graph.from_json("tests/graphs_for_test/8x8_with_muni.json")
    population_col = "TOTPOP"

    updaters = {"population": updaters.Tally(population_col, alias="population"),
                "cut_edges": updaters.cut_edges,
                f"{category}_splits": updaters.tally_region_splits([category]),
                }
    initial_partition = Partition(graph, assignment="district", updaters=updaters) 

    ideal_pop = sum(initial_partition["population"].values()) / len(initial_partition)
    weights = {category: 0.8}
    num_steps = steps
    epsilon = 0.01

    random.seed(seed)
    weighted_proposal = partial(proposals.recom,
                                pop_col=population_col,
                                pop_target=ideal_pop,
                                epsilon=epsilon,
                                weight_dict=weights,
                                node_repeats=10,
                                method=partial(tree.bipartition_tree,
                                               max_attempts=max_attempts,
                                               allow_pair_reselection=reselect))

    weighted_chain = MarkovChain(proposal=weighted_proposal,
                                 constraints=[constraints.contiguous],
                                 accept=accept.always_accept,
                                 initial_state=initial_partition,
                                 total_steps=num_steps)
    
    n_splits = -1
    for item in weighted_chain:
        n_splits = item[f"{category}_splits"][category]
    
    return n_splits

@pytest.mark.slow
def test_region_aware_muni():
    n_samples = 30
    region = "muni"
    n_regions = 16
    
    with ProcessPoolExecutor() as executor:
        results = executor.map(partial(run_chain_single, 
                                       category=region,
                                       steps=500,
                                       weight=0.5),
                               range(n_samples))

    tot_splits = sum(results)
    
    random.seed(2018)
    # Check if splits less than 5% of the time on average
    assert (float(tot_splits) / (n_samples*n_regions)) < 0.05


def test_region_aware_muni_errors():
    region = "muni"

    with pytest.raises(RuntimeError) as exec_info:
        # Random seed 0 should fail here
        run_chain_single(seed=0,
                        category=region,
                        steps=10000,
                        max_attempts=10,
                        weight=2.0)

    random.seed(2018)
    assert "Could not find a possible cut after 10 attempts" in str(exec_info.value)


def test_region_aware_muni_warning():
    n_samples = 1
    region = "muni"

    with pytest.warns(UserWarning) as record:
        # Random seed 2 should succeed, but drawing the 
        # tree is hard, so we should get a warning
        run_chain_single(seed=2,
                    category=region,
                    steps=500,
                    weight=1.0)

    random.seed(2018)

    assert record[0].category == BipartitionWarning
    assert "Failed to find a balanced cut after 50 attempts." in str(record[0].message)

@pytest.mark.slow
def test_region_aware_muni_reselect():
    n_samples = 30
    region = "muni"
    n_regions = 16

    with ProcessPoolExecutor() as executor:
        results = executor.map(partial(run_chain_single, 
                                       category=region,
                                       steps=500,
                                       weight=1.0,
                                       reselect=True),
                               range(n_samples))

    tot_splits = sum(results)

    random.seed(2018)
    # Check if splits less than 5% of the time on average
    assert (float(tot_splits) / (n_samples*n_regions)) < 0.05


@pytest.mark.slow
def test_region_aware_county():
    n_samples = 100
    region = "county2"
    n_regions = 8

    with ProcessPoolExecutor() as executor:
        results = executor.map(partial(run_chain_single, 
                                       category=region,
                                       steps=5000,
                                       weight=2.0),
                               range(n_samples))

    tot_splits = sum(results)

    random.seed(2018)  
    # Check if splits less than 5% of the time on average
    assert (float(tot_splits) / (n_samples*n_regions)) < 0.05
    
    
def straddled_regions(partition, reg_attr, all_reg_names):
    """Returns the total number of district that straddle two regions in the partition."""
    split = {name: 0 for name in all_reg_names}
    
    for node1, node2 in (set(partition.graph.edges() - partition["cut_edges"])):
        split[partition.graph.nodes[node1][reg_attr]] += 1
        split[partition.graph.nodes[node2][reg_attr]] += 1

    return sum(1 for value in split.values() if value > 0)

def run_chain_dual(seed, steps):
    from gerrychain import MarkovChain, Partition, accept, constraints, proposals, updaters, Graph, tree
    from functools import partial
    import random

    graph = Graph.from_json("tests/graphs_for_test/8x8_with_muni.json")
    population_col = "TOTPOP"

    muni_names= [str(i) for i in range(1,17)]
    county_names = [str(i) for i in range(1,5)]

    updaters = {
        "population": updaters.Tally(population_col, alias="population"),
        "cut_edges": updaters.cut_edges,
        "splits": updaters.tally_region_splits(["muni", "county"]),
    }
    initial_partition = Partition(graph, assignment="district", updaters=updaters) 

    ideal_pop = sum(initial_partition["population"].values()) / len(initial_partition)
    weights = {"muni": 0.5, "county": 0.5}
    num_steps = steps
    epsilon = 0.01

    random.seed(seed)
    weighted_proposal = partial(proposals.recom,
                                pop_col=population_col,
                                pop_target=ideal_pop,
                                epsilon=epsilon,
                                weight_dict=weights,
                                node_repeats=10,
                                method=partial(tree.bipartition_tree, max_attempts=10000))

    weighted_chain = MarkovChain(proposal=weighted_proposal,
                                 constraints=[constraints.contiguous],
                                 accept=accept.always_accept,
                                 initial_state=initial_partition,
                                 total_steps=num_steps)
    
    n_muni_splits = -1
    n_county_splits = -1
    for item in weighted_chain:
        n_muni_splits = item["splits"]["muni"]
        n_county_splits = item["splits"]["county"]
    
    return (n_muni_splits, n_county_splits)

@pytest.mark.slow
def test_region_aware_dual():
    n_samples = 30
    n_munis = 16
    n_counties = 4 
    
    with ProcessPoolExecutor() as executor:
        results = executor.map(partial(run_chain_dual, 
                                       steps=10000),
                               range(n_samples))

    tot_muni_splits = sum([item[0] for item in results])
    tot_county_splits = sum([item[1] for item in results])
    
    random.seed(2018)  

    # Check if splits less than 5% of the time on average
    assert (float(tot_muni_splits) / (n_samples*n_munis)) < 0.05
    assert (float(tot_county_splits) / (n_samples*n_counties)) < 0.05