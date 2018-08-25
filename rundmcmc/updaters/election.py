import math

from rundmcmc.updaters.tally import DataTally


class Election:
    def __init__(self, name, parties_to_columns, alias=None):
        """
        :name: The name of the election.
        :parties_to_columns: A dictionary matching party names to their
            data columns, either as actual columns (list-like, indexed by nodes)
            or as string keys for the node attributes that hold the party's
            vote totals. Or, a list of strings which will serve as both
            the party names and the node attribute keys.
        :alias: (optional) Alias that the election is registered under
            in the Partition's dictionary of updaters.
        """
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
        else:
            raise TypeError("Election expects parties_to_columns to be a dict or list")

        self.tallies = {party: DataTally(self.parties_to_columns[party], party)
                        for party in self.parties}

        self.updater = ElectionUpdater(self)

    def __str__(self):
        return 'Election \'{}\' with vote totals for parties {} from columns {}.'.format(
            self.name, str(self.parties), str(self.columns))

    def __repr__(self):
        return 'Election(parties={}, columns={}, alias={})'.format(
            str(self.parties), str(self.columns), str(self.alias))

    def __call__(self, *args, **kwargs):
        return self.updater(*args, **kwargs)


class ElectionUpdater:
    def __init__(self, election):
        self.election = election

    def __call__(self, partition):
        previous_totals_for_party = self.get_previous_values(partition)
        parties = self.election.parties
        tallies = self.election.tallies

        totals_for_party = {
            party: tallies[party](partition, previous=previous_totals_for_party[party])
            for party in parties
        }

        totals = {
            part: sum(totals_for_party[party][part] for party in parties)
            for part in partition.parts
        }

        percents_for_party = {
            party: get_percents(totals_for_party[party], totals)
            for party in parties
        }
        return ElectionResults(self, totals_for_party, totals, percents_for_party)

    def get_previous_values(self, partition):
        parent = partition.parent
        if parent is None:
            previous_totals_for_party = {party: None for party in self.election.parties}
        else:
            previous_totals_for_party = partition.parent[self.election.alias].totals_for_party
        return previous_totals_for_party


def get_percents(counts, totals):
    return {part: counts[part] / totals[part]
            if totals[part] > 0
            else math.nan
            for part in totals}


class ElectionResults:
    def __init__(self, election, totals_for_party, totals, percents_for_party):
        self.election = election
        self.totals_for_party = totals_for_party
        self.totals = totals
        self.percents_for_party = percents_for_party

    def __str__(self):
        results_by_part = '\n'.join(
            format_part_results(self.percents_for_party, part)
            for part in self.totals)
        return 'Election Results for {name}\n{results}'.format(
            name=self.election.name, results=results_by_part)


def format_part_results(percents_for_party, part):
    heading = '{part}:\n'.format(part=str(part))
    body = '\n'.join("  {party}: {percent}".format(
        party=str(party), percent=percents_for_party[party][part])
        for party in percents_for_party)
    return heading + body
