import math

from .tally import Tally


class UpdaterContainer:
    def __init__(self, updaters):
        self.updaters = updaters

    def _update(self):
        self._cache = dict()

        for key in self.updaters:
            if key not in self._cache:
                self._cache[key] = self.updaters[key](self)

    def __getitem__(self, key):
        """Allows keying on a Partition instance.

        :key: Property to access.

        """
        if key not in self._cache:
            self._cache[key] = self.updaters[key](self)
        return self._cache[key]


class ElectionDataColumn:
    def __init__(self, party, data):
        self.party = party
        self.data = data

    def __iter__(self):
        return self.data

    @classmethod
    def from_node_attribute(cls, party, graph, attribute):
        data = [graph.nodes[node][attribute] for node in graph.nodes]
        return cls(party, data)


class ElectionDataView:
    def __init__(self, totals_for_party, totals, percents_for_party):
        self.totals_for_party = totals_for_party
        self.totals = totals
        self.percents_for_party = percents_for_party


class Election(UpdaterContainer):
    def __init__(self, name, parties_to_columns):
        self.name = name

        if isinstance(parties_to_columns, dict):
            self.parties = list(parties_to_columns.keys())
            self.columns = list(parties_to_columns.values())
        elif isinstance(parties_to_columns, list):
            self.columns = parties_to_columns

        self.updaters = votes_updaters(self)

    def __str__(self):
        return "Election \"{}\" with vote totals from columns {}.".format(
            self.name, str(self.columns))

    def __call__(self, partition):
        totals_for_party = {party: self[party] for party in self.parties}
        totals = self['total_votes' + self.name]
        percents_for_party = {party: self[party + '%'] for party in self.parties}
        return ElectionDataView(totals_for_party, totals, percents_for_party)


class Proportion:
    def __init__(self, tally_name, total_name):
        self.tally_name = tally_name
        self.total_name = total_name

    def __call__(self, partition):
        return {part: partition[self.tally_name][part] / partition[self.total_name][part]
                if partition[self.total_name][part] > 0
                else math.nan
                for part in partition.parts}


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
