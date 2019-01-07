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


def partisan_bias(election_results):
    """
    Computes the partisan bias for the given ElectionResults.
    The partisan bias is defined as the number of districts with above-mean
    vote share by the first party divided by the total number of districts,
    minus 1/2.
    """
    first_party = election_results.election.parties[0]
    party_shares = numpy.array(election_results.percents(first_party))
    mean_share = numpy.mean(party_shares)
    above_mean_districts = len(party_shares[party_shares > mean_share])
    return (above_mean_districts / len(party_shares)) - 0.5


def partisan_gini(election_results):
    """
    Computes the partisan Gini score for the given ElectionResults.
    The partisan Gini score is defined as the area between the seats-votes
    curve and its reflection about (.5, .5).
    """
    # For two parties, the Gini score is symmetric--it does not vary by party.
    party = election_results.election.parties[0]

    # To find seats as a function of votes, we assume uniform partisan swing.
    # That is, if the statewide popular vote share for a party swings by some
    # delta, the vote share for that party swings by that delta in each
    # district.
    # We calculate the necessary delta to shift the district with the highest
    # vote share for the party to a vote share of 0.5. This delta, subtracted
    # from the original popular vote share, gives the minimum popular vote
    # share that yields 1 seat to the party.
    # We repeat this process for the district with the second-highest vote
    # share, which gives the minimum popular vote share yielding 2 seats,
    # and so on.
    overall_result = election_results.percent(party)
    race_results = sorted(election_results.percents(party), reverse=True)
    seats_votes = [overall_result - r + 0.5 for r in race_results]

    # Apply reflection of seats-votes curve about (.5, .5)
    reflected_sv = reversed([1 - s for s in seats_votes])
    # Calculate the unscaled, unsigned area between the seats-votes curve
    # and its reflection. For each possible number of seats attained, we find
    # the area of a rectangle of unit height, with a width determined by the
    # horizontal distance between the curves at that number of seats.
    unscaled_area = sum(abs(s - r) for s, r in zip(seats_votes, reflected_sv))
    # We divide by area by the number of seats to obtain a partisan Gini score
    # between 0 and 1.
    return unscaled_area / len(race_results)
