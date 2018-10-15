import numpy


def mean_median(election_results):
    """
    Computes the Mean-Median score for the given ElectionResults.
    A positive value indicates an advantage for the first party listed
    in the Election's parties_to_columns dictionary.
    """
    first_party = election_results.election.parties[0]
    data = election_results.percents(first_party)

    return numpy.median(data) - numpy.mean(data)


def mean_thirdian(election_results):
    """
    Computes the Mean-Median score for the given ElectionResults.
    A positive value indicates an advantage for the first party listed
    in the Election's parties_to_columns dictionary.

    The motivation for this score is that the minority party in many
    states struggles to win even a third of the seats.
    """
    first_party = election_results.election.parties[0]
    data = election_results.percents(first_party)

    thirdian_index = round(len(data) / 3)
    thirdian = sorted(data)[thirdian_index]

    return thirdian - numpy.mean(data)


def efficiency_gap(results):
    """
    Computes the efficiency gap for the given ElectionResults.
    A positive value indicates an advantage for the first party listed
    in the Election's parties_to_columns dictionary.
    """
    party1, party2 = [results.counts(party) for party in results.election.parties]
    wasted_votes_by_part = map(wasted_votes, party1, party2)
    total_votes = results.total_votes()
    numerator = sum(waste2 - waste1 for waste1, waste2 in wasted_votes_by_part)
    return numerator / total_votes


def wasted_votes(party1_votes, party2_votes):
    """
    Computes the wasted votes for each party in the given race.
    :party1_votes: the number of votes party1 received in the race
    :party2_votes: the number of votes party2 received in the race
    """
    total_votes = party1_votes + party2_votes
    if party1_votes > party2_votes:
        party1_waste = party1_votes - total_votes / 2
        party2_waste = party2_votes
    else:
        party2_waste = party2_votes - total_votes / 2
        party1_waste = party1_votes
    return party1_waste, party2_waste
