# import random

# from gerrychain.defaults import DefaultChain, Grid
# from gerrychain.updaters.election import Election
# from gerrychain.validity import single_flip_contiguous, no_vanishing_districts

# def test_election_results_match_the_naive_values():
#     election = Election("election", {"Democratic": "D", "Republican": "R"})
#     partition = Grid((10, 10), with_diagonals=True)

#     for node in partition.graph.nodes:
#         partition.graph.nodes[node]['D'] = random.randint(1,1000)
#         partition.graph.nodes[node]['R'] = random.randint(1,1000)

#     chain = DefaultChain(partition, [single_flip_contiguous, no_vanishing_districts], 10)

#     for state in chain:
