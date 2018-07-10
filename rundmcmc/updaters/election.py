import math

from .tally import Tally


class Proportion:
    def __init__(self, tally_name, total_name):
        self.tally_name = tally_name
        self.total_name = total_name

    def __call__(self, partition):
        return {part: partition[self.tally_name][part] / partition[self.total_name][part]
                if partition[self.total_name][part] > 0
                else math.nan
                for part in partition.parts}


def votes_updaters(columns, election_name=''):
    """
    Returns a dictionary of updaters that tally total votes and compute
    vote share. Example: `votes_updaters(['D','R'], election_name='08')` would
    have entries `'R'`, `'D'`, `'total_votes'` (the tallies) as well as
    `'R%'`, `'D%'` (the percentages of the total vote).

    :columns: the names of the node attributes storing vote counts for each
        party that you are interested in
    :election_name: an optional identifier that will be appended to the names of the
        returned updaters. This is in order to support computing scores
        for multiple elections at the same time, so that the names of the
        updaters don't collide.
    """

    def name_count(party):
        """Return the Partition attribute name where we'll save the total
        vote count for a party"""
        return f"{party}"

    def name_proportion(party):
        """Returns the Partition attribute name where we'll save the percentage
        of the total vote count for the given party"""
        return f"{party}%"

    tallies = {name_count(column): Tally(column, alias=name_count(column))
               for column in columns}
    total_name = 'total_votes' + election_name
    tallies[total_name] = Tally(columns, alias=total_name)
    proportions = {name_proportion(column): Proportion(
        name_count(column), total_name) for column in columns}
    return {**tallies, **proportions}
