"""
The partisan metrics in this file are later used in the module
gerrychain.updaters.election.py. Thus, all of the election
results objects here are implicilty typed as ElectionResults,
but cannot be given an explicit type annotation due to problems
with circular imports.
"""

import numpy
from typing import Tuple


def mean_median(election_results) -> float:
    """
    Computes the Mean-Median score for the given ElectionResults.
    A positive value indicates an advantage for the first party listed
    in the Election's parties_to_columns dictionary.

    :param election_results: An ElectionResults object
    :type election_results: ElectionResults

    :returns: The Mean-Median score for the given ElectionResults
    :rtype: float
    """
    first_party = election_results.election.parties[0]
    data = election_results.percents(first_party)

    return numpy.median(data) - numpy.mean(data)


def mean_thirdian(election_results) -> float:
    """
    Computes the Mean-Median score for the given ElectionResults.
    A positive value indicates an advantage for the first party listed
    in the Election's parties_to_columns dictionary.

    The motivation for this score is that the minority party in many
    states struggles to win even a third of the seats.

    :param election_results: An ElectionResults object
    :type election_results: ElectionResults

    :returns: The Mean-Thirdian score for the given ElectionResults
    :rtype: float
    """
    first_party = election_results.election.parties[0]
    data = election_results.percents(first_party)

    thirdian_index = round(len(data) / 3)
    thirdian = sorted(data)[thirdian_index]

    return thirdian - numpy.mean(data)


def efficiency_gap(election_results) -> float:
    """
    Computes the efficiency gap for the given ElectionResults.
    A positive value indicates an advantage for the first party listed
    in the Election's parties_to_columns dictionary.

    :param election_results: An ElectionResults object
    :type election_results: ElectionResults

    :returns: The efficiency gap for the given ElectionResults
    :rtype: float
    """
    party1, party2 = [
        election_results.counts(party) for party in election_results.election.parties
    ]
    wasted_votes_by_part = map(wasted_votes, party1, party2)
    total_votes = election_results.total_votes()
    numerator = sum(waste2 - waste1 for waste1, waste2 in wasted_votes_by_part)
    return numerator / total_votes


def wasted_votes(party1_votes: int, party2_votes: int) -> Tuple[int, int]:
    """
    Computes the wasted votes for each party in the given race.
    :param party1_votes: the number of votes party1 received in the race
    :type party1_votes: int
    :param party2_votes: the number of votes party2 received in the race
    :type party2_votes: int

    :returns: a tuple of the wasted votes for each party
    :rtype: Tuple[int, int]
    """
    total_votes = party1_votes + party2_votes
    if party1_votes > party2_votes:
        party1_waste = party1_votes - total_votes / 2
        party2_waste = party2_votes
    else:
        party2_waste = party2_votes - total_votes / 2
        party1_waste = party1_votes
    return party1_waste, party2_waste


def partisan_bias(election_results) -> float:
    """
    Computes the partisan bias for the given ElectionResults.
    The partisan bias is defined as the number of districts with above-mean
    vote share by the first party divided by the total number of districts,
    minus 1/2.

    :param election_results: An ElectionResults object
    :type election_results: ElectionResults

    :returns: The partisan bias for the given ElectionResults
    :rtype: float
    """
    first_party = election_results.election.parties[0]
    party_shares = numpy.array(election_results.percents(first_party))
    mean_share = numpy.mean(party_shares)
    above_mean_districts = len(party_shares[party_shares > mean_share])
    return (above_mean_districts / len(party_shares)) - 0.5


def partisan_gini(election_results) -> float:
    """
    Computes the partisan Gini score for the given ElectionResults.
    The partisan Gini score is defined as the area between the seats-votes
    curve and its reflection about (.5, .5).

    For more information on the computation, see Definition 1 in:
    https://arxiv.org/pdf/2008.06930.pdf

    :param election_results: An ElectionResults object
    :type election_results: ElectionResults

    :returns: The partisan Gini score for the given ElectionResults
    :rtype: float
    """
    # For two parties, the Gini score is symmetric--it does not vary by party.
    party = election_results.election.parties[0]

    overall_result = election_results.percent(party)
    race_results = sorted(election_results.percents(party), reverse=True)
    seats_votes = [overall_result - r + 0.5 for r in race_results]

    # Apply reflection of seats-votes curve about (.5, .5)
    reflected_sv = reversed([1 - s for s in seats_votes])
    # Calculate the unscaled, unsigned area between the seats-votes curve
    # and its reflection.
    unscaled_area = sum(abs(s - r) for s, r in zip(seats_votes, reflected_sv))

    # We divide by area by the number of seats to obtain a partisan Gini score
    # between 0 and 1.
    return unscaled_area / len(race_results)
