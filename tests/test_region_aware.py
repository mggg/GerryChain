import random
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import networkx as nx
import pytest

from gerrychain import (
    Graph,
    MarkovChain,
    Partition,
    accept,
    constraints,
    proposals,
    tree,
)
from gerrychain import updaters as gc_updaters
from gerrychain.tree import BipartitionWarning

random.seed(2018)


def run_chain_single(seed, category, steps, surcharge, max_attempts=100000, reselect=False):
    import random
    from functools import partial

    graph = Graph.from_json("tests/graphs_for_test/8x8_with_muni.json")
    population_col = "TOTPOP"

    updaters = {
        "population": gc_updaters.Tally(population_col, alias="population"),
        "cut_edges": gc_updaters.cut_edges,
        f"{category}_splits": gc_updaters.tally_region_splits([category]),
    }
    initial_partition = Partition(graph, assignment="district", updaters=updaters)

    ideal_pop = sum(initial_partition["population"].values()) / len(initial_partition)
    surcharges = {category: surcharge}
    num_steps = steps
    epsilon = 0.01

    random.seed(seed)
    surcharged_proposal = partial(
        proposals.recom,
        pop_col=population_col,
        pop_target=ideal_pop,
        epsilon=epsilon,
        region_surcharge=surcharges,
        node_repeats=10,
        bipartition_tree_fn=partial(
            tree.bipartition_tree,
            max_attempts=max_attempts,
            allow_pair_reselection=reselect,
        ),
    )

    surcharged_chain = MarkovChain(
        proposal=surcharged_proposal,
        constraints=[constraints.contiguous],
        accept=accept.always_accept,
        initial_state=initial_partition,
        total_steps=num_steps,
    )

    n_splits = -1
    for item in surcharged_chain:
        n_splits = item[f"{category}_splits"][category]

    return n_splits


@pytest.mark.slow
def test_region_aware_muni():
    n_samples = 30
    region = "muni"
    n_regions = 16
    random.seed(2018)

    with ProcessPoolExecutor() as executor:
        results = executor.map(
            partial(run_chain_single, category=region, steps=5000, surcharge=0.5),
            range(n_samples),
        )

    tot_splits = sum(results)

    random.seed(2018)
    assert (float(tot_splits) / (n_samples * n_regions)) < 0.10


def test_region_aware_muni_errors():
    region = "muni"

    with pytest.raises(RuntimeError) as exec_info:
        # Random seed 0 should fail here
        run_chain_single(seed=0, category=region, steps=10000, max_attempts=1, surcharge=2.0)

    random.seed(2018)
    assert "Could not find a possible cut after 1 attempts" in str(exec_info.value)


@pytest.mark.slow
def test_region_aware_muni_reselect():
    n_samples = 30
    region = "muni"
    n_regions = 16

    with ProcessPoolExecutor() as executor:
        results = executor.map(
            partial(
                run_chain_single,
                category=region,
                steps=500,
                surcharge=1.0,
                reselect=True,
                max_attempts=100,
            ),
            range(n_samples),
        )

    tot_splits = sum(results)

    random.seed(2018)
    assert (float(tot_splits) / (n_samples * n_regions)) < 0.10


@pytest.mark.slow
def test_region_aware_county():
    n_samples = 100
    region = "county2"
    n_regions = 8

    with ProcessPoolExecutor() as executor:
        results = executor.map(
            # reselect=True so a rare hard-to-split district pair triggers reselection
            # instead of raising after max_attempts (seen for ~1 seed under some hash seeds).
            partial(run_chain_single, category=region, steps=5000, surcharge=0.8, reselect=True),
            range(n_samples),
        )

    tot_splits = sum(results)

    random.seed(2018)
    assert (float(tot_splits) / (n_samples * n_regions)) < 0.10


def straddled_regions(partition, reg_attr, all_reg_names):
    """Returns the total number of district that straddle two regions in the partition."""
    split = {name: 0 for name in all_reg_names}

    # frm: TODO: Testing: Grok what this tests - not clear to me at this time...

    for node1, node2 in set(partition.graph.edges() - partition["cut_edges"]):
        split[partition.graph.node_data(node1)[reg_attr]] += 1
        split[partition.graph.node_data(node2)[reg_attr]] += 1

    return sum(1 for value in split.values() if value > 0)


def run_chain_dual(seed, steps, surcharges={"muni": 0.5, "county": 0.5}, warn_attempts=1000):
    import random
    from functools import partial

    graph = Graph.from_json("tests/graphs_for_test/8x8_with_muni.json")
    population_col = "TOTPOP"

    updaters = {
        "population": gc_updaters.Tally(population_col, alias="population"),
        "cut_edges": gc_updaters.cut_edges,
        "splits": gc_updaters.tally_region_splits(["muni", "county"]),
    }
    initial_partition = Partition(graph, assignment="district", updaters=updaters)

    ideal_pop = sum(initial_partition["population"].values()) / len(initial_partition)
    num_steps = steps
    epsilon = 0.01

    random.seed(seed)
    surcharged_proposal = partial(
        proposals.recom,
        pop_col=population_col,
        pop_target=ideal_pop,
        epsilon=epsilon,
        region_surcharge=surcharges,
        node_repeats=10,
        bipartition_tree_fn=partial(
            tree.bipartition_tree,
            max_attempts=10000,
            warn_attempts=warn_attempts,
        ),
    )

    surcharged_chain = MarkovChain(
        proposal=surcharged_proposal,
        constraints=[constraints.contiguous],
        accept=accept.always_accept,
        initial_state=initial_partition,
        total_steps=num_steps,
    )

    n_muni_splits = -1
    n_county_splits = -1
    for item in surcharged_chain:
        n_muni_splits = item["splits"]["muni"]
        n_county_splits = item["splits"]["county"]

    return (n_muni_splits, n_county_splits)


def test_region_aware_muni_warning():
    # bipartition_tree emits a BipartitionWarning when it cannot find a population-balanced
    # cut within `warn_attempts`. A path 0-1-2 with populations [1, 100, 1] has no cut close to
    # the target population of 51, so every attempt fails regardless of hash seed or backend.
    # The warning fires at `warn_attempts`, then a RuntimeError is raised at `max_attempts`.
    nx_graph = nx.path_graph(3)
    for node_id, pop in zip(sorted(nx_graph.nodes), [1, 100, 1]):
        nx_graph.nodes[node_id]["pop"] = pop
    graph = Graph.from_networkx(nx_graph)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        with pytest.raises(RuntimeError):
            tree.bipartition_tree(
                graph,
                pop_col="pop",
                pop_target=51,
                epsilon=0.01,
                warn_attempts=2,
                max_attempts=5,
            )

    assert any(
        issubclass(w.category, BipartitionWarning)
        and "Failed to find a balanced cut after 2 attempts." in str(w.message)
        for w in record
    )


@pytest.mark.slow
def test_region_aware_dual():
    n_samples = 30
    n_munis = 16
    n_counties = 4

    with ProcessPoolExecutor() as executor:
        results = executor.map(partial(run_chain_dual, steps=10000), range(n_samples))

    tot_muni_splits = sum([item[0] for item in results])
    tot_county_splits = sum([item[1] for item in results])

    random.seed(2018)

    assert (float(tot_muni_splits) / (n_samples * n_munis)) < 0.10
    assert (float(tot_county_splits) / (n_samples * n_counties)) < 0.10
