import numpy


def mean_median(election_results):
    """
    Computes the Mean-Median score for the given ElectionResults.
    A positive value indicates an advantage for the first party listed
    in the Election's parties_to_columns dictionary.
    """
    first_party_results, *others = election_results.percents_for_party.values()
    data = list(first_party_results.values())

    return numpy.median(data) - numpy.mean(data)


def mean_thirdian(election_results):
    """
    Computes the Mean-Median score for the given ElectionResults.
    A positive value indicates an advantage for the first party listed
    in the Election's parties_to_columns dictionary.
    """
    first_party_results, *others = election_results.percents_for_party.values()
    data = list(first_party_results.values())

    thirdian_index = round(len(data) / 3)
    thirdian = sorted(data)[thirdian_index]

    return thirdian - numpy.mean(data)


def efficiency_gap(election_results):
    """
    Computes the efficiency gap for the given ElectionResults.
    A positive value indicates an advantage for the first party listed
    in the Election's parties_to_columns dictionary.
    """
    party1, party2 = election_results.totals_for_party.values()
    wasted_votes_by_part = {part: wasted_votes(party1[part], party2[part])
                            for part in party1}
    total_votes = sum(party1.values()) + sum(party2.values())
    numerator = sum(waste2 - waste1 for waste1, waste2 in wasted_votes_by_part.values())
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
