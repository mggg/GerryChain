from __future__ import annotations

import math
from typing import TYPE_CHECKING

import gerrychain.metrics.partisan as pm
from gerrychain.updaters.tally import DataTally

if TYPE_CHECKING:
    from ..partition.partition import Partition


class Election:
    """
    Represents the data of one election, with races conducted in each part of
    the partition.

    As we vary the districting plan, we can use the same node-level vote totals
    to tabulate hypothetical elections. To do this manually with tallies, we would
    have to maintain tallies for each party, as well as the total number of votes,
    and then compute the electoral results and percentages from scratch every time.
    To make this simpler, this class provides an ElectionUpdater to manage
    these tallies. The updater returns an ElectionResults class giving
    a convenient view of the election results, with methods like
    `ElectionResults.wins` or `ElectionResults.percent` for common queries
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

    Attributes:
        name (str): The name of the election. (e.g. "2008 Presidential")
        parties (List[str]): A list of the names of the parties in the election.
        node_attribute_names (List[str]): A list of the node_attribute_names in the graph's node
        data that
            hold the vote totals for each party.
        party_names_to_node_attribute_names (Dict[str, str]): A dictionary mapping party names to
        the
            node_attribute_names in the graph's node data that hold the vote totals for that party.
        tallies (Dict[str, DataTally]): A dictionary mapping party names to DataTally
        objects
            that manage the vote totals for that party.
        updater (ElectionUpdater): An ElectionUpdater object that manages the tallies
            and returns an ElectionResults object.
        alias (str): The name that the election is registered under in the
            partition's dictionary of updaters.
    """

    def __init__(
        self,
        name: str,
        party_names_to_node_attribute_names: dict | list,
        alias: str | None = None,
    ) -> None:
        """Initialize a Election instance.

        Args:
            name (str): The name of the election. (e.g. "2008 Presidential")
            party_names_to_node_attribute_names (Union[Dict, List]): A mapping from the name of a
                party to the name of an attribute of a node that contains the vote totals for that
                party. This parameter can be either a list or a dict. If a list, then the name of
                the party and the name of the node attribute are the same, for instance: ["Dem",
                "Rep"] would indicate that the "Dem" party vote totals are stored in the "Dem" node
                attribute. If a list, then there are two possibilities.

                A dictionary matching party names to their data node_attribute_names, either as
                actual node_attribute_names (list-like, indexed by nodes) or as string keys for the
                node attributes that hold the party's vote totals. Or, a list of strings which will
                serve as both the party names and the node attribute keys.
            alias (Optional[str], optional): Alias that the election is registered under in the
                Partition's dictionary of updaters.

        """

        self.name = name

        if alias is None:
            alias = name
        self.alias = alias

        # Canonicalize "parties", "node_attribute_names", and "party_names_to_node_attribute_names":
        #
        # "parties" are the names of the parties for purposes of reporting
        # "node_attribute_names" are the names of the node attributes storing vote counts
        # "party_names_to_node_attribute_names" is a mapping from one to the other
        #
        if isinstance(party_names_to_node_attribute_names, dict):
            self.parties = list(party_names_to_node_attribute_names.keys())
            self.node_attribute_names = list(party_names_to_node_attribute_names.values())
            self.party_names_to_node_attribute_names = party_names_to_node_attribute_names
        elif isinstance(party_names_to_node_attribute_names, list):
            # name of the party and the attribute name containing value is the same
            self.parties = party_names_to_node_attribute_names
            self.node_attribute_names = party_names_to_node_attribute_names
            self.party_names_to_node_attribute_names = dict(
                zip(self.parties, self.node_attribute_names)
            )
        else:
            raise TypeError(
                "Election expects party_names_to_node_attribute_names to be a dict or list"
            )

        for party in self.parties:
            if isinstance(self.party_names_to_node_attribute_names[party], dict):
                raise Exception(
                    "Election: Using a map from node_id to vote totals is no longer permitted"
                )

        self.tallies = {
            party: DataTally(self.party_names_to_node_attribute_names[party], party)
            for party in self.parties
        }

        self.updater = ElectionUpdater(self)

    def _initialize_self(self, partition: Partition) -> None:

        # Create DataTally objects for each party in the election.
        self.tallies = {
            # For each party, create a DataTally using the string for the node
            # attribute where that party's vote totals can be found.
            party: DataTally(self.party_names_to_node_attribute_names[party], party)
            for party in self.parties
        }

    def __str__(self) -> str:
        return (
            f"Election '{self.name}' with vote totals for parties {self.parties} "
            f"from node_attribute_names {self.node_attribute_names}."
        )

    def __repr__(self) -> str:
        return (
            "Election("
            f"parties={str(self.parties)}, "
            f"node_attribute_names={str(self.node_attribute_names)}, "
            f"alias={str(self.alias)})"
        )

    def __call__(self, partition: Partition) -> ElectionResults:
        return self.updater(partition)


class ElectionUpdater:
    """
    The updater for computing the election results in each part of the partition after
    each step in the Markov chain. The actual results are returned to the user as
    an ElectionResults instance.

    Attributes:
        election (Election): The Election object that this updater is associated with.
    """

    def __init__(self, election: Election) -> None:
        self.election = election

    def __call__(self, partition: Partition) -> ElectionResults:
        previous_totals_for_party = self.get_previous_values(partition)
        parties = self.election.parties
        tallies = self.election.tallies

        counts = {
            party: tallies[party](partition, previous=previous_totals_for_party[party])
            for party in parties
        }

        return ElectionResults(self.election, counts, regions=partition.parts)

    def get_previous_values(self, partition: Partition) -> dict[str, dict[int, float] | None]:
        """Returns a dictionary mapping party names to the vote totals that party received in each.

        Args:
            partition (Partition): The partition whose parent we want to obtain the
                previous vote totals from.

        Returns:
            Dict[str, Dict[int, float]]: A dictionary mapping party names to the vote totals that
                party received in each part of the parent of the current partition.
        """
        parent = partition.parent
        if parent is None:
            previous_totals_for_party = {party: None for party in self.election.parties}
        else:
            previous_totals_for_party = partition.parent[self.election.alias].totals_for_party
        return previous_totals_for_party


def get_percents(counts: dict, totals: dict) -> dict:
    """Returns a dictionary mapping each part in a partition to the percentage of votes that a
    party received in that part.

    Args:
        counts (Dict): A dictionary mapping each part in a partition to the count of the number of
            votes that a party received in that part.
        totals (Dict): A dictionary mapping each part in a partition to the total number of votes
            cast in that part.

    Returns:
        Dict: A dictionary mapping each part in a partition to the percentage
    """
    return {part: counts[part] / totals[part] if totals[part] > 0 else math.nan for part in totals}


class ElectionResults:
    """
    Represents the results of an election. Provides helpful methods to answer
    common questions you might have about an election (Who won? How many seats?, etc.).

    Attributes:
        election (Election): The Election object that these results are associated with.
        totals_for_party (Dict[str, Dict[int, float]]): A dictionary mapping party names to the
        total number of votes
            that party received in each part of the partition.
        regions (List[int]): A list of regions that we would like the results for.
        totals (Dict[int, int]): A dictionary mapping each part of the partition to the total number
            of votes cast in that part.
        percents_for_party (Dict[str, Dict[int, float]]): A dictionary mapping party names to the
        percentage of votes
            that party received in each part of the partition.
    .. note::

        The variable "regions" is generally called "parts" in other sections of the
        codebase, but we have changed it here to avoid confusion with the parameter
        "party" that often appears within the class.
    """

    def __init__(
        self,
        election: Election,
        counts: dict[str, dict[int, float]],
        regions: list[int],
    ) -> None:
        """Initialize a ElectionResults instance.

        Args:
            election (Election): The Election object that these results are associated
                with.
            counts (Dict[str, Dict[int, float]]): A dictionary mapping party names to the total
                number of votes that party received in each part of the partition.
            regions (List[int]): A list of regions that we would like to consider (e.g.
                congressional districts).

        """
        self.election = election
        self.totals_for_party = counts
        self.regions = regions

        self.totals = {
            region: sum(counts[party][region] for party in self.election.parties)
            for region in self.regions
        }

        self.percents_for_party = {
            party: get_percents(counts[party], self.totals) for party in election.parties
        }

    def __str__(self) -> str:
        results_by_part = "\n".join(
            format_part_results(self.percents_for_party, part) for part in self.totals
        )
        return f"Election Results for {self.election.name}\n{results_by_part}"

    def seats(self, party: str) -> int:
        """Return number of seats that ``party`` won.

        Args:
            party (str): Party name

        Returns:
            int: The number of seats that ``party`` won.
        """
        return sum(self.won(party, region) for region in self.regions)

    def wins(self, party: str) -> int:
        """An alias for `seats`.

        Args:
            party (str): Party name

        Returns:
            int: The number of seats that ``party`` won.
        """
        return self.seats(party)

    def percent(self, party: str, region: int | None = None) -> float:
        """Return vote share for ``party`` in one region or overall.

        If ``region`` is provided, this returns the vote share in that region. Otherwise, it
        returns the overall vote share of ``party`` across all regions.

        Args:
            party (str): Party ID.
            region (Optional[int], optional): ID of the part of the partition whose votes we want
                to tally.

        Returns:
            float: The percentage of the vote that ``party`` received in a given region (part of
                the partition). If ``region`` is omitted, returns the overall vote share of
                ``party``.
        """
        if region is not None:
            return self.percents_for_party[party][region]
        return sum(self.votes(party)) / sum(self.totals[region] for region in self.regions)

    def percents(self, party: str) -> tuple:
        """Return vote shares for ``party`` across all regions.

        The returned tuple contains one vote-share value per region, in the order of
        ``self.regions``.

        Args:
            party (str): Party ID

        Returns:
            Tuple: The tuple of the percentage of votes that ``party`` received in each part of the
                partition
        """
        return tuple(self.percents_for_party[party][region] for region in self.regions)

    def count(self, party: str, region: str | None = None) -> int:
        """Return vote total for ``party`` in one region or overall.

        If ``region`` is provided, this returns the total vote count in that region. Otherwise, it
        returns the overall vote total of ``party`` across all regions.

        Args:
            party (str): Party ID.
            region (Optional[int], optional): ID of the part of the partition whose votes we want
                to tally.

        Returns:
            int: The total number of votes that ``party`` received in a given region (part of the
                partition). If ``region`` is omitted, returns the overall vote total of ``party``.
        """
        if region is not None:
            return self.totals_for_party[party][region]
        return sum(self.totals_for_party[party][region] for region in self.regions)

    def counts(self, party: str) -> tuple:
        """Return tuple of the total votes cast for ``party`` in each part of the partition.

        Args:
            party (str): Party ID

        Returns:
            Tuple: tuple of the total votes cast for ``party`` in each part of the partition
        """
        return tuple(self.totals_for_party[party][region] for region in self.regions)

    def votes(self, party: str) -> tuple:
        """An alias for `counts`.

        It returns a tuple of the total votes cast for ``party`` in each part of the partition.

        Args:
            party (str): Party ID

        Returns:
            Tuple: tuple of the total votes cast for ``party`` in each part of the partition
        """
        return self.counts(party)

    def won(self, party: str, region: str) -> bool:
        """Determines if ``party`` won in the region given by ``region``?".

        Args:
            party (str): Party ID
            region (str): ID of the part of the partition whose votes we want to tally.

        Returns:
            bool: Answer to "Did ``party`` win the region in part ``region``?"
        """
        return all(
            self.totals_for_party[party][region] > self.totals_for_party[opponent][region]
            for opponent in self.election.parties
            if opponent != party
        )

    def total_votes(self) -> int:
        """Return total number of votes cast in the election.

        Returns:
            int: The total number of votes cast in the election.
        """
        return sum(self.totals.values())

    def mean_median(self) -> float:
        """Computes the mean-median score for this ElectionResults object.

        See: `gerrychain.metrics.partisan.mean_median`

        Returns:
            float: The mean-median score for this election.
        """
        return pm.mean_median(self)

    def mean_thirdian(self) -> float:
        """Computes the mean-thirdian score for this ElectionResults object.

        See: `gerrychain.metrics.partisan.mean_thirdian`

        Returns:
            float: The mean-thirdian score for this election.
        """
        return pm.mean_thirdian(self)

    def efficiency_gap(self) -> float:
        """Computes the efficiency gap for this ElectionResults object.

        See: `gerrychain.metrics.partisan.efficiency_gap`

        Returns:
            float: The efficiency gap for this election.
        """
        return pm.efficiency_gap(self)

    def partisan_bias(self) -> float:
        """Computes the partisan bias for this ElectionResults object.

        See: `gerrychain.metrics.partisan.partisan_bias`

        Returns:
            float: The partisan bias for this election.
        """
        return pm.partisan_bias(self)

    def partisan_gini(self) -> float:
        """Computes the Gini score for this ElectionResults object.

        See: `gerrychain.metrics.partisan.partisan_gini`

        Returns:
            float: The partisan Gini score for this election.
        """
        return pm.partisan_gini(self)


def format_part_results(percents_for_party: dict[str, dict[int, float]], part: int) -> str:
    """Return A formatted string containing the results for the given part of the partition.

    Args:
        percents_for_party (Dict[str, Dict[int, float]]): A dictionary mapping party names to a
            dict containing the percentage of votes that party received in each part of the
            partition.
        part (int): The part of the partition whose results we want to format.

    Returns:
        str: A formatted string containing the results for the given part of the partition.
    """
    heading = f"{str(part)}:\n"
    body = "\n".join(
        f"  {str(party)}: {round(percents_for_party[party][part], 4)}"
        for party in percents_for_party
    )
    return heading + body
