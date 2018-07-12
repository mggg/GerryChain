import numpy

from rundmcmc.proposals import number_of_flips


class DukeGerrymanderingIndex:
    def __init__(self, initial_plan, vote_shares_column):
        self.column = vote_shares_column
        self.initial_plan_data = self.sorted_vote_shares(initial_plan)
        self.N = len(self.initial_plan_data)

    def sorted_vote_shares(self, partition, column='PR_DV08%'):
        return sorted(list(partition[self.column].values()))

    def __call__(self, chain):
        data = [self.sorted_vote_shares(state) for state in chain]

        medians = [numpy.median([data_row[i] for data_row in data]) for i in range(self.N)]

        terms_in_the_sum = [median_plan - plan
                            for median_plan, plan in zip(medians, self.initial_plan_data)]

        return numpy.sqrt(sum(term ** 2 for term in terms_in_the_sum))


def mean_median(partition, proportion_column_name):
    data = list(partition[proportion_column_name].values())
    return numpy.mean(data) - numpy.median(data)


def mean_thirdian(partition, proportion_column_name):
    data = list(partition[proportion_column_name].values())
    return numpy.mean(data) - numpy.percentile(data, 33)


def normalized_efficiency_gap(partition, proportion_column_name):
    """Right now this is the turnout-normalized version (just `2t-s`)."""
    vote_shares_by_district = list(partition[proportion_column_name].values())
    seats = len([votes for votes in vote_shares_by_district if votes > 0])
    seats_share = seats / len(vote_shares_by_district)
    total_vote_share = numpy.mean(vote_shares_by_district)
    return 2 * total_vote_share - seats_share


def efficiency_gap(partition, col1='PR_DV08', col2='PR_RV08'):
    party1 = partition[col1]
    party2 = partition[col2]
    wasted_votes_by_part = {part: wasted_votes(party1[part], party2[part])
                            for part in party1}
    total_votes = sum(party1.values()) + sum(party2.values())
    numerator = sum(waste1 - waste2 for waste1, waste2 in wasted_votes_by_part.values())
    return numerator / total_votes


def wasted_votes(party1_votes, party2_votes):
    total_votes = party1_votes + party2_votes
    if party1_votes > party2_votes:
        party1_waste = party1_votes - total_votes / 2
        party2_waste = party2_votes
    else:
        party2_waste = party2_votes - total_votes / 2
        party1_waste = party1_votes
    return party1_waste, party2_waste


def final_report():
    with open('../tests/test_run.txt') as f:
        f = f.read()
        print(f)


class MetaGraphDegree:
    def __init__(self, chain):
        self.is_valid = chain.is_valid
        self.data = []

    def __call__(self, partition):
        total_available_flips = 2 * len(partition['cut_edges'])
        total_valid_flips = sum(self.num_valid_flips(edge, partition)
                                for edge in partition['cut_edges'])
        return {'total': total_available_flips, 'valid': total_valid_flips}

    def num_valid_flips(self, edge, partition):
        """
        Takes an edge and a partition and returns the number of valid
        flips the partition can make across this edge (0, 1, or 2).
        """
        flip = {edge[0]: partition.assignment[edge[1]]}
        reverse_flip = {edge[1]: partition.assignment[edge[0]]}
        flip_valid = 1 if self.is_valid(partition.merge(flip)) else 0
        reverse_valid = 1 if self.is_valid(partition.merge(reverse_flip)) else 0
        return flip_valid + reverse_valid


def compute_meta_graph_degree(chain):
    degree = MetaGraphDegree(chain)
    data = []

    previous_assignment = None
    for state in chain:
        if state.assignment != previous_assignment:
            d = degree(state)
            data.append(d)
            print(state.flips)
            print(d)
            previous_assignment = state.assignment

    print("Local average degree of the metagraph:")
    print(numpy.mean([row['valid'] for row in data]))

    return data


def get_dict_of_flips(chain):
    dict_of_flips = {}
    prev_partition = {}
    for partition in chain:
        dict_of_flips, prev_partition = number_of_flips(
            partition, dict_of_flips, prev_partition)
        print(dict_of_flips)


def how_many_seats(col1, col2):
    def function(partition):
        return sum(partition[col1][part] > partition[col2][part] for part in partition.parts)
    return function
