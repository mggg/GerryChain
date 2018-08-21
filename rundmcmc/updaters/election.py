import math

from .tally import Tally, DataTally


class ElectionDataView:
    def __init__(self, totals_for_party, totals, percents_for_party):
        self.totals_for_party = totals_for_party
        self.totals = totals
        self.percents_for_party = percents_for_party


class Election:
    def __init__(self, name, parties_to_columns, alias=None):
        self.name = name

        if alias is None:
            alias = name
        self.alias = alias

        if isinstance(parties_to_columns, dict):
            self.parties = list(parties_to_columns.keys())
            self.columns = list(parties_to_columns.values())
            self.parties_to_columns = parties_to_columns
        elif isinstance(parties_to_columns, list):
            self.parties = parties_to_columns
            self.columns = parties_to_columns
            self.parties_to_columns = dict(zip(self.parties, self.columns))

        self.tallies = {party: DataTally(self.parties_to_columns[party], party)
                        for party in self.parties}

    def __str__(self):
        return "Election \"{}\" with vote totals from columns {}.".format(
            self.name, str(self.columns))

    def get_previous_values(self, partition):
        parent = partition.parent
        if parent is None:
            previous_totals_for_party = {party: None for party in self.parties}
        else:
            previous_totals_for_party = partition.parent[self.alias].totals_for_party
        return previous_totals_for_party

    def __call__(self, partition):
        previous_totals_for_party = self.get_previous_values(partition)

        totals_for_party = {
            party: self.tallies[party](partition, previous=previous_totals_for_party[party])
            for party in self.parties
        }

        totals = {
            part: sum(totals_for_party[party][part] for party in self.parties)
            for part in partition.parts
        }

        percents_for_party = {
            party: get_proportion(totals_for_party[party], totals)
            for party in self.parties
        }
        return ElectionDataView(totals_for_party, totals, percents_for_party)


def get_proportion(counts, totals):
    return {part: counts[part] / totals[part]
            if totals[part] > 0
            else math.nan
            for part in totals}


class Proportion:
    def __init__(self, tally_name, total_name):
        self.tally_name = tally_name
        self.total_name = total_name

    def __call__(self, partition):
        return get_proportion(partition[self.tally_name], partition[self.total_name])


def votes_updaters(election):
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
        return str(party)

    def name_proportion(party):
        """Returns the Partition attribute name where we'll save the percentage
        of the total vote count for the given party"""
        return str(party) + "%"

    tallies = {name_count(column): Tally(column, alias=name_count(column))
               for column in election.columns}

    total_name = 'total_votes' + election.name

    tallies[total_name] = Tally(election.columns, alias=total_name)

    proportions = {name_proportion(column): Proportion(
        name_count(column), total_name) for column in election.columns}

    return {**tallies, **proportions}
