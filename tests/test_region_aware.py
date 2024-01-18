import random
random.seed(2018)
import pytest
from functools import partial
from concurrent.futures import ProcessPoolExecutor
from gerrychain import MarkovChain, Partition, accept, constraints, proposals, updaters, Graph, tree

def total_reg_splits(partition, reg_attr, all_reg_names):
    """Returns the total number of region splits in the partition."""
    split = {name: 0 for name in all_reg_names}
    # Require that the cut_edges updater is attached to the partition
    for node1, node2 in partition["cut_edges"]:
        if partition.assignment[node1] != partition.assignment[node2] \
            and partition.graph.nodes[node1][reg_attr] == partition.graph.nodes[node2][reg_attr]:
           split[partition.graph.nodes[node1][reg_attr]] += 1
           split[partition.graph.nodes[node2][reg_attr]] += 1
           
    return sum(1 for value in split.values() if value > 0)


def run_chain_single(seed, category, names, steps):
    from gerrychain import MarkovChain, Partition, accept, constraints, proposals, updaters, Graph, tree
    from functools import partial
    import random

    graph = Graph.from_json("tests/graphs_for_test/8x8_with_muni.json")
    population_col = "TOTPOP"

    updaters = {"population": updaters.Tally(population_col, alias="population"),
                "cut_edges": updaters.cut_edges,
                f"{category}_splits": partial(total_reg_splits,
                                       reg_attr=category,
                                       all_reg_names=names)
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
                                method=partial(tree.bipartition_tree, max_attempts=1000000))

    weighted_chain = MarkovChain(proposal=weighted_proposal,
                                 constraints=[constraints.contiguous],
                                 accept=accept.always_accept,
                                 initial_state=initial_partition,
                                 total_steps=num_steps)
    
    n_splits = -1
    for item in weighted_chain:
        n_splits = item[f"{category}_splits"]
    
    return n_splits

@pytest.mark.slow
def test_region_aware_muni():
    n_samples = 30
    region = "muni"
    region_names = [str(i) for i in range(1,17)]

    with ProcessPoolExecutor() as executor:
        results = executor.map(partial(run_chain_single, 
                                       category=region,
                                       names=region_names,
                                       steps=500),
                               range(n_samples))

    tot_splits = sum(results)

    random.seed(2018)
    # Check if splits less than 1% of the time on average
    assert (float(tot_splits) / (n_samples*len(region_names))) < 0.01


@pytest.mark.slow
def test_region_aware_county():
    n_samples = 30
    region = "county2"
    region_names = [str(i) for i in range(1,9)]

    with ProcessPoolExecutor() as executor:
        results = executor.map(partial(run_chain_single, 
                                       category=region,
                                       names=region_names,
                                       steps=10000),
                               range(n_samples))

    tot_splits = sum(results)

    random.seed(2018)  
    # Check if splits less than 5% of the time on average
    assert (float(tot_splits) / (n_samples*len(region_names))) < 0.05
    
    
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

    updaters = {"population": updaters.Tally(population_col, alias="population"),
                "cut_edges": updaters.cut_edges,
                f"muni_splits": partial(total_reg_splits,
                                       reg_attr="muni",
                                       all_reg_names=muni_names),
                f"county_splits": partial(straddled_regions,
                                       reg_attr="county",
                                       all_reg_names=county_names)
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
                                method=partial(tree.bipartition_tree, max_attempts=1000000))

    weighted_chain = MarkovChain(proposal=weighted_proposal,
                                 constraints=[constraints.contiguous],
                                 accept=accept.always_accept,
                                 initial_state=initial_partition,
                                 total_steps=num_steps)
    
    n_muni_splits = -1
    n_county_splits = -1
    for item in weighted_chain:
        n_muni_splits = item[f"muni_splits"]
        n_county_splits = item[f"county_splits"]
    
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

    # Check if splits less than 1% of the time on average
    # The condition on counties is stricter this time since the 
    # munis and districts can be made to fit neatly within the counties
    assert (float(tot_muni_splits) / (n_samples*n_munis)) < 0.01 and \
           (float(tot_county_splits) / (n_samples*n_counties)) < 0.01