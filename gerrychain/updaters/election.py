import math

from gerrychain.updaters.tally import DataTally


class Election:
    def __init__(self, name, parties_to_columns, alias=None):
        """
        :name: The name of the election. (e.g. "2008 Presidential")
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
    """
    The updater for computing the election results in each part of the partition after
    each step in the Markov chain. The actual results are returned to the user as
    an :class:`ElectionResults` instance.
    """

    def __init__(self, election):
        self.election = election

    def __call__(self, partition):
        previous_totals_for_party = self.get_previous_values(partition)
        parties = self.election.parties
        tallies = self.election.tallies

        counts = {
            party: tallies[party](partition, previous=previous_totals_for_party[party])
            for party in parties
        }

        return ElectionResults(self.election, counts, races=partition.parts)

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
    """
    Represents the results of an election. Provides helpful methods to answer
    common questions you might have about an election (Who won? How many seats?, etc.).
    """

    def __init__(self, election, counts, races):
        self.election = election
        self.totals_for_party = counts
        self.races = races

        self.totals = {
            race: sum(counts[party][race] for party in self.election.parties)
            for race in self.races
        }

        self.percents_for_party = {
            party: get_percents(counts[party], self.totals)
            for party in election.parties
        }

    def __str__(self):
        results_by_part = '\n'.join(
            format_part_results(self.percents_for_party, part)
            for part in self.totals)
        return 'Election Results for {name}\n{results}'.format(
            name=self.election.name, results=results_by_part)

    def seats(self, party):
        """
        Returns the number of races that `party` won.
        """
        return sum(self.won(party, race) for race in self.races)

    def wins(self, party):
        """
        An alias for :meth:`seats`.
        """
        return self.seats(party)

    def percent(self, party, race=None):
        """
        Returns the percentage of the vote that `party` received in a given race
        (part of the partition). If `race` is omitted, returns the overall vote
        share of `party`.
        :party: Party ID.
        :race: ID of the part of the partition whose votes we want to tally.
        """
        if race is not None:
            return self.percents_for_party[party][race]
        return self.votes(party) / sum(self.totals[race] for race in self.races)

    def percents(self, party):
        return tuple(self.percents_for_party[party][race] for race in self.races)

    def count(self, party, race=None):
        """
        Returns the total number of votes that `party` received in a given race
        (part of the partition). If `race` is omitted, returns the overall vote
        total of `party`.
        :party: Party ID.
        :race: ID of the part of the partition whose votes we want to tally.
        """
        if race is not None:
            return self.totals_for_party[party][race]
        return sum(self.totals_for_party[party][race] for race in self.races)

    def counts(self, party):
        return tuple(self.totals_for_party[party][race] for race in self.races)

    def won(self, party, race):
        """
        Answers "Did `party` win the race in part `race`?" with `True` or `False`.
        """
        return all(
            self.totals_for_party[party][race] >= self.totals_for_party[opponent][race]
            for opponent in self.election.parties
        )

    def total_votes(self):
        return sum(self.totals.values())


def format_part_results(percents_for_party, part):
    heading = '{part}:\n'.format(part=str(part))
    body = '\n'.join("  {party}: {percent}".format(
        party=str(party), percent=round(percents_for_party[party][part], 4))
        for party in percents_for_party)
    return heading + body
