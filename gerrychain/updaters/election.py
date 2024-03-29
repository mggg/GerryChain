import math
from typing import Dict, List, Optional, Tuple, Union
from gerrychain.updaters.tally import DataTally
import gerrychain.metrics.partisan as pm


class Election:
    """
    Represents the data of one election, with races conducted in each part of
    the partition.

    As we vary the districting plan, we can use the same node-level vote totals
    to tabulate hypothetical elections. To do this manually with tallies, we would
    have to maintain tallies for each party, as well as the total number of votes,
    and then compute the electoral results and percentages from scratch every time.
    To make this simpler, this class provides an :class:`ElectionUpdater` to manage
    these tallies. The updater returns an :class:`ElectionResults` class giving
    a convenient view of the election results, with methods like
    :meth:`~ElectionResults.wins` or :meth:`~ElectionResults.percent` for common queries
    the user might make on election results.

    Example usage:

    .. code-block:: python

        # Assuming your nodes have attributes "2008_D", "2008_R"
        # with (for example) 2008 senate election vote totals
        election = Election(
            "2008 Senate",
            {"Democratic": "2008_D", "Republican": "2008_R"},
            alias="2008_Sen"
        )

        # Assuming you already have a graph and assignment:
        partition = Partition(
            graph,
            assignment,
            updaters={"2008_Sen": election}
        )

        # The updater returns an ElectionResults instance, which
        # we can use (for example) to see how many seats a given
        # party would win in this partition using this election's
        # vote distribution:
        partition["2008_Sen"].wins("Republican")

    :ivar name: The name of the election. (e.g. "2008 Presidential")
    :type name: str
    :ivar parties: A list of the names of the parties in the election.
    :type parties: List[str]
    :ivar columns: A list of the columns in the graph's node data that hold
        the vote totals for each party.
    :type columns: List[str]
    :ivar parties_to_columns: A dictionary mapping party names to the columns
        in the graph's node data that hold the vote totals for that party.
    :type parties_to_columns: Dict[str, str]
    :ivar tallies: A dictionary mapping party names to :class:`DataTally` objects
        that manage the vote totals for that party.
    :type tallies: Dict[str, DataTally]
    :ivar updater: An :class:`ElectionUpdater` object that manages the tallies
        and returns an :class:`ElectionResults` object.
    :type updater: ElectionUpdater
    :ivar alias: The name that the election is registered under in the
        partition's dictionary of updaters.
    :type alias: str
    """

    def __init__(
        self,
        name: str,
        parties_to_columns: Union[Dict, List],
        alias: Optional[str] = None,
    ) -> None:
        """
        :param name: The name of the election. (e.g. "2008 Presidential")
        :type name: str
        :param parties_to_columns: A dictionary matching party names to their
            data columns, either as actual columns (list-like, indexed by nodes)
            or as string keys for the node attributes that hold the party's
            vote totals. Or, a list of strings which will serve as both
            the party names and the node attribute keys.
        :type parties_to_columns: Union[Dict, List]
        :param alias: Alias that the election is registered under
            in the Partition's dictionary of updaters.
        :type alias: Optional[str], optional
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

        self.tallies = {
            party: DataTally(self.parties_to_columns[party], party)
            for party in self.parties
        }

        self.updater = ElectionUpdater(self)

    def __str__(self):
        return "Election '{}' with vote totals for parties {} from columns {}.".format(
            self.name, str(self.parties), str(self.columns)
        )

    def __repr__(self):
        return "Election(parties={}, columns={}, alias={})".format(
            str(self.parties), str(self.columns), str(self.alias)
        )

    def __call__(self, *args, **kwargs):
        return self.updater(*args, **kwargs)


class ElectionUpdater:
    """
    The updater for computing the election results in each part of the partition after
    each step in the Markov chain. The actual results are returned to the user as
    an :class:`ElectionResults` instance.

    :ivar election: The :class:`Election` object that this updater is associated with.
    :type election: Election
    """

    def __init__(self, election: Election) -> None:
        self.election = election

    def __call__(self, partition):
        previous_totals_for_party = self.get_previous_values(partition)
        parties = self.election.parties
        tallies = self.election.tallies

        counts = {
            party: tallies[party](partition, previous=previous_totals_for_party[party])
            for party in parties
        }

        return ElectionResults(self.election, counts, regions=partition.parts)

    def get_previous_values(self, partition) -> Dict[str, Dict[int, float]]:
        """
        :param partition: The partition whose parent we want to obtain the
            previous vote totals from.
        :type partition: :class:`Partition`

        :returns: A dictionary mapping party names to the vote totals that
            party received in each part of the parent of the current partition.
        :rtype: Dict[str, Dict[int, float]]
        """
        parent = partition.parent
        if parent is None:
            previous_totals_for_party = {party: None for party in self.election.parties}
        else:
            previous_totals_for_party = partition.parent[
                self.election.alias
            ].totals_for_party
        return previous_totals_for_party


def get_percents(counts: Dict, totals: Dict) -> Dict:
    """
    :param counts: A dictionary mapping each part in a partition to the
        count of the number of votes that a party received in that part.
    :type counts: Dict
    :param totals: A dictionary mapping each part in a partition to the
        total number of votes cast in that part.
    :type totals: Dict

    :returns: A dictionary mapping each part in a partition to the percentage
    :rtype: Dict
    """
    return {
        part: counts[part] / totals[part] if totals[part] > 0 else math.nan
        for part in totals
    }


class ElectionResults:
    """
    Represents the results of an election. Provides helpful methods to answer
    common questions you might have about an election (Who won? How many seats?, etc.).

    :ivar election: The :class:`Election` object that these results are associated with.
    :type election: Election
    :ivar totals_for_party: A dictionary mapping party names to the total number of votes
        that party received in each part of the partition.
    :type totals_for_party: Dict[str, Dict[int, float]]
    :ivar regions: A list of regions that we would like the results for.
    :type regions: List[int]
    :ivar totals: A dictionary mapping each part of the partition to the total number
        of votes cast in that part.
    :type totals: Dict[int, int]
    :ivar percents_for_party: A dictionary mapping party names to the percentage of votes
        that party received in each part of the partition.
    :type percents_for_party: Dict[str, Dict[int, float]]

    .. note::

        The variable "regions" is generally called "parts" in other sections of the
        codebase, but we have changed it here to avoid confusion with the parameter
        "party" that often appears within the class.
    """

    def __init__(
        self,
        election: Election,
        counts: Dict[str, Dict[int, float]],
        regions: List[int],
    ) -> None:
        """
        :param election: The :class:`Election` object that these results are associated with.
        :type election: Election
        :counts: A dictionary mapping party names to the total number of votes that party
            received in each part of the partition.
        :type counts: Dict[str, Dict[int, float]]
        :param regions: A list of regions that we would like to consider (e.g. congressional
            districts).
        :type regions: List[int]

        :returns: None
        """
        self.election = election
        self.totals_for_party = counts
        self.regions = regions

        self.totals = {
            region: sum(counts[party][region] for party in self.election.parties)
            for region in self.regions
        }

        self.percents_for_party = {
            party: get_percents(counts[party], self.totals)
            for party in election.parties
        }

    def __str__(self):
        results_by_part = "\n".join(
            format_part_results(self.percents_for_party, part) for part in self.totals
        )
        return "Election Results for {name}\n{results}".format(
            name=self.election.name, results=results_by_part
        )

    def seats(self, party: str) -> int:
        """
        :param party: Party name
        :type party: str

        :returns: The number of seats that ``party`` won.
        :rtype: int
        """
        return sum(self.won(party, region) for region in self.regions)

    def wins(self, party: str) -> int:
        """
        An alias for :meth:`seats`.

        :param party: Party name
        :type party: str

        :returns: The number of seats that ``party`` won.
        :rtype: int
        """
        return self.seats(party)

    def percent(self, party: str, region: Optional[int] = None) -> float:
        """
        :param party: Party ID.
        :type party: str
        :param region: ID of the part of the partition whose votes we want to tally.
        :type region: Optional[int], optional

        :returns: The percentage of the vote that ``party`` received in a given region
            (part of the partition). If ``region`` is omitted, returns the overall vote
            share of ``party``.
        :rtype: float
        """
        if region is not None:
            return self.percents_for_party[party][region]
        return sum(self.votes(party)) / sum(
            self.totals[region] for region in self.regions
        )

    def percents(self, party: str) -> Tuple:
        """
        :param party: Party ID
        :type party: str

        :returns: The tuple of the percentage of votes that ``party`` received
            in each part of the partition
        :rtype: Tuple
        """
        return tuple(self.percents_for_party[party][region] for region in self.regions)

    def count(self, party: str, region: Optional[str] = None) -> int:
        """
        :param party: Party ID.
        :type party: str
        :param region: ID of the part of the partition whose votes we want to tally.
        :type region: Optional[int], optional

        :returns: The total number of votes that ``party`` received in a given region
            (part of the partition). If ``region`` is omitted, returns the overall vote
            total of ``party``.
        :rtype: int
        """
        if region is not None:
            return self.totals_for_party[party][region]
        return sum(self.totals_for_party[party][region] for region in self.regions)

    def counts(self, party: str) -> Tuple:
        """
        :param party: Party ID
        :type party: str

        :returns: tuple of the total votes cast for ``party`` in each part of
            the partition
        :rtype: Tuple
        """
        return tuple(self.totals_for_party[party][region] for region in self.regions)

    def votes(self, party: str) -> Tuple:
        """
        An alias for :meth:`counts`.

        :param party: Party ID
        :type party: str

        :returns: tuple of the total votes cast for ``party`` in each part of
            the partition
        :rtype: Tuple
        """
        return self.counts(party)

    def won(self, party: str, region: str) -> bool:
        """
        :param party: Party ID
        :type party: str
        :param region: ID of the part of the partition whose votes we want to tally.
        :type region: str

        :returns: Answer to "Did ``party`` win the region in part ``region``?"
        :rtype: bool
        """
        return all(
            self.totals_for_party[party][region]
            > self.totals_for_party[opponent][region]
            for opponent in self.election.parties
            if opponent != party
        )

    def total_votes(self) -> int:
        """
        :returns: The total number of votes cast in the election.
        :rtype: int
        """
        return sum(self.totals.values())

    def mean_median(self) -> float:
        """
        Computes the mean-median score for this ElectionResults object.

        See: :func:`~gerrychain.metrics.partisan.mean_median`

        :returns: The mean-median score for this election.
        :rtype: float
        """
        return pm.mean_median(self)

    def mean_thirdian(self) -> float:
        """
        Computes the mean-thirdian score for this ElectionResults object.

        See: :func:`~gerrychain.metrics.partisan.mean_thirdian`

        :returns: The mean-thirdian score for this election.
        :rtype: float
        """
        return pm.mean_thirdian(self)

    def efficiency_gap(self) -> float:
        """
        Computes the efficiency gap for this ElectionResults object.

        See: :func:`~gerrychain.metrics.partisan.efficiency_gap`

        :returns: The efficiency gap for this election.
        :rtype: float
        """
        return pm.efficiency_gap(self)

    def partisan_bias(self) -> float:
        """
        Computes the partisan bias for this ElectionResults object.

        See: :func:`~gerrychain.metrics.partisan.partisan_bias`

        :returns: The partisan bias for this election.
        :rtype: float
        """
        return pm.partisan_bias(self)

    def partisan_gini(self) -> float:
        """
        Computes the Gini score for this ElectionResults object.

        See: :func:`~gerrychain.metrics.partisan.partisan_gini`

        :returns: The partisan Gini score for this election.
        :rtype: float
        """
        return pm.partisan_gini(self)


def format_part_results(
    percents_for_party: Dict[str, Dict[int, float]], part: int
) -> str:
    """
    :param percents_for_party: A dictionary mapping party names to a dict
        containing the percentage of votes that party received in each part
        of the partition.
    :type percents_for_party: Dict[str, Dict[int, float]]
    :param part: The part of the partition whose results we want to format.
    :type part: int

    :returns: A formatted string containing the results for the given part
        of the partition.
    :rtype: str
    """
    heading = "{part}:\n".format(part=str(part))
    body = "\n".join(
        "  {party}: {percent}".format(
            party=str(party), percent=round(percents_for_party[party][part], 4)
        )
        for party in percents_for_party
    )
    return heading + body
