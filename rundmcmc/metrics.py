import numpy


# I'm assuming the partition has a data column (a field), maybe called 'votes',
# that is a dict from district ids to one side's vote proportition in that
# district.

# Also assuming that votes are normalized by turnout in some way.

# This needs testing!

def mean_median(partition, data_column='votes'):
    data = list(partition[data_column].values())
    return numpy.mean(data) - numpy.median(data)


def mean_thirdian(partition, data_column='votes'):
    data = list(partition[data_column].values())
    return numpy.mean(data) - numpy.percentile(data, 33)


def efficiency_gap(partition, data_column='votes'):
    """Right now this is the turnout-normalized version (just `2t-s`)."""
    vote_shares_by_district = list(partition[data_column].values())
    seats = len(votes for votes in vote_shares_by_district if votes > 0)
    seats_share = seats / len(vote_shares_by_district)
    total_vote_share = numpy.mean(vote_shares_by_district)
    return 2 * total_vote_share - seats_share
