###############################################################
#
# frm: Overview of test_frm_regression.py
#
# This code was copied from the GerryChain User Guide / Tutorial as a way
# to have a functional test that exercised the overall logic of GerryChain.
#
# It is NOT comprehensive, but it does get all the way to executing
# a chain.
#
# It is a quick and dirty way to make sure I haven't really screwed things up ;-)
#


from gerrychain import MarkovChain, Partition, accept, updaters
from gerrychain.constraints import contiguous
from gerrychain.examples import gerrymandria
from gerrychain.proposals import build_recom_proposal_fn

graph = gerrymandria()

my_updaters = {"population": updaters.Tally("TOTPOP"), "cut_edges": updaters.cut_edges}

initial_partition = Partition(graph, assignment="district", updaters=my_updaters)

# This should be 8 since each district has 1 person in it.
# Note that the key "population" corresponds to the population updater
# that we defined above and not with the population column in the json file.
ideal_population = sum(initial_partition["population"].values()) / len(initial_partition)

proposal = build_recom_proposal_fn(pop_col="TOTPOP", pop_target=ideal_population, epsilon=0.01)

recom_chain = MarkovChain(
    proposal_fn=proposal,
    constraints=[contiguous],
    acceptance_fn=accept.always_accept,
    initial_partition=initial_partition,
    total_steps=40,
    rng=2024,
)

assignment_list = []

for i, item in enumerate(recom_chain):
    print(f"Finished step {i + 1}/{len(recom_chain)}")
    assignment_list.append(item.assignment)

print("Enumerated the chain: number of entries in list is: ", len(assignment_list))


def test_success():
    len(assignment_list) == 40
