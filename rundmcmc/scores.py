import numpy


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


def efficiency_gap(partition, col1='D', col2='R', total='total_votes'):
    return wasted_votes(partition, col1, col2) / sum(partition[total].values())


def wasted_votes(partition, col1='D', col2='R'):
    return sum(partition[col1][part] - partition[col2][part] for part in partition.parts)


def final_report():
    with open('../tests/test_run.txt') as f:
        f = f.read()
        print(f)
