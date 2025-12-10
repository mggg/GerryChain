# Imports
from collections import defaultdict, Counter
# frm TODO: Refactoring: Remove dependence on NetworkX.  
#           The only use is:
#                pieces += nx.number_connected_components(subgraph)
import networkx as nx
import math
from typing import List

# frm: TODO: Performance: Do performance testing and improve performance of these routines.
#
# Peter made the comment in a PR that we should make this code more efficient:
#
# A note on this file: A ton of the code in here is inefficient. This was 
# made 6 years ago and hasn't really been touched since then other than 
# when I was doing an overhaul on many of the doc strings

class LocalitySplits:
    """
    Computes various splitting measures for a partition

    Can be used to compute how a districting plan splits
    against any static attribute. The prototypical example
    is to consider how a districting plan subdivides counties
    or municipalities, but other units, such as city
    neighborhoods, state legislative districts, or Census
    tracts could be treated as 'localities'

    Example usage::

        # Assuming your nodes have attributes "countyID"
        # with (for example) the name of the county that
        # node lies in and a population attribute "pop":
        county_splits = LocalitySplits(
            "countysplits",
            "countyID",
            "pop",
            ["num_parts", "symmetric_entropy","power_entropy"],
            pent_alpha = 0.8
        )
        # Assuming you already have a graph and assignment:
        partition = Partition(
            graph,
            assignment,
            updaters={"county_splits" : county_splits}
        )
        # The updater returns an dictionary instance, which
        # at each step of the chain has the name of the score
        # and its value at that step

    :ivar name: The name of the updater (e.g. "countysplits")
    :type name: str
    :ivar col_id: The name of the column containing the locality
        attribute (i.e. county ids, municipality names, etc.)
    :type col_id: str
    :ivar pop_col: The name of the column containing population counts.
    :type pop_col: str
    :ivar scores_to_compute: A list/tuple/set of strings naming the
        score functions to compute at each step. This will generally be
        some subcollection of ```['num_parts', 'num_pieces',
        'naked_boundary', 'shannon_entropy', 'power_entropy',
        'symmetric_entropy', 'num_split_localities']```
    :type scores_to_compute: List[str]
    :ivar pent_alpha: A number between 0 and 1 which is passed as the
        exponent to :meth:`~LocalitySplits.power_entropy`
    :type pent_alpha: float
    :ivar localities: A list containing the unique locality identifiers
        (e.g. county names, municipality names, etc.) for the partition.
        This list is populated using the locality data stored on each of
        the nodes in the graph.
    :type localities: List[str]
    :ivar localitydict: A dictionary mapping node IDs to locality IDs.
        This is used to quickly look up the locality of a given node.
    :type localitydict: Dict[str, str]
    :ivar locality_splits: A dictionary mapping district IDs to a counter
        of localities in that district. That is to say, this tells us
        how many nodes in each district are of the given locality type.
    :type locality_splits: Dict[int, Counter[str]]
    :ivar locality_splits_inv: The inverted dictionary of locality_splits
    :type locality_splits_inv: Dict[str, Dict[int, int]]
    :ivar allowed_pieces: A dictionary that maps each locality to the
        minimum number of districts that locality must touch. This is
        computed using the ideal district population. NOT CURRENTLY USED.
    :type allowed_pieces: Dict[str, int]
    :ivar scores: A dictionary initialized with the key values from the
        initializer's scores_to_compute parameter. The initial values are
        set to none and are updated in each call to store the compted
        score value for each metric of interest.
    :type scores: Dict[str, Any]
    """

    def __init__(
        self,
        name: str,
        col_id: str,
        pop_col: str,
        scores_to_compute: List[str] = ["num_parts"],
        pent_alpha: float = 0.05,
    ):
        """
        :param name: The name of the updater (e.g. "countysplits")
        :type name: str
        :param col_id: The name of the column containing the locality
            attribute (i.e. county ids, municipality names, etc.)
        :type col_id: str
        :param pop_col: The name of the column containing population counts.
        :type pop_col: str
        :param scores_to_compute: A list/tuple/set of strings naming the
            score functions to compute at each step. This should be
            some subcollection of ```['num_parts', 'num_pieces',
            'naked_boundary', 'shannon_entropy', 'power_entropy',
            'symmetric_entropy', 'num_split_localities']```.
            Default is ["num_parts"].
        :type scores_to_compute: List[str], optional
        :param pent_alpha: A number between 0 and 1 which is
            passed as the exponent to :meth:`~LocalitySplits.power_entropy`.
            Default is 0.05.
        :type pent_alpha: float, optional
        """

        self.name = name
        self.col_id = col_id

        self.pop_col = pop_col

        self.pent_alpha = pent_alpha

        self.localities = []
        self.localitydict = {}
        self.locality_splits = {}
        self.locality_splits_inv = {}

        # A dictionary containing the number minimum number
        # of districts which a locality must touch. I.e. if
        # the ideal district population is 10,000 and a
        # locality has 35,000 people, then that locality
        # must be in at least four districts.  Not
        # presently used to compute any score functions,
        # but may be useful for future development or
        # certain use cases.
        self.allowed_pieces = {}

        self.scores = dict.fromkeys(scores_to_compute)

    def __call__(self, partition):

        # frm: TODO: Refactoring:   LocalitySplits: Figure out how this is intended to be used...
        # 
        # Not quite sure why it is better to have a "__call()__" method instead of a 
        # get_scores(self) method, but whatever...
        #
        # This routine indeed just computes the requested scores (specified in the constructor).
        # It stashed those scores as a data member in the class and returns them to the caller as well.
        #
        # This all seems kind of misguided to me - and there is no instance of this being used in 
        # the gerrychain code except in a test, so I am not sure how it is intended to be used.
        #
        # Probably need to look at some user code that Peter sent me to see if anyone actually uses
        # this and if so, how...
        #

        if self.localities == []:
            self.localitydict = {}
            for node_id in partition.graph.node_indices:
                self.localitydict[node_id] = partition.graph.node_data(node_id)[self.col_id]

            self.localities = set(list(self.localitydict.values()))

        locality_splits = {
            k: [self.localitydict[v] for v in d]
            for k, d in partition.assignment.parts.items()
        }
        self.locality_splits = {k: Counter(v) for k, v in locality_splits.items()}

        self.locality_splits_inv = defaultdict(dict)
        for k, v in self.locality_splits.items():
            for k2, v2 in v.items():
                self.locality_splits_inv[k2][k] = v2

        if self.allowed_pieces == {}:

            allowed_pieces = {}

            totpop = 0
            for node_id in partition.graph.node_indices:
                # frm: TODO: Refactoring:  Once you have a partition, you cannot change the total population
                #               in the Partition, so why don't we cache the total population as
                #               a data member in Partition?
                #
                # Peter agreed that this would be a good thing to do

                totpop += partition.graph.node_data(node_id)[self.pop_col]

            # frm: TODO: Refactoring:  Ditto with num_districts - isn't this a constant once you create a Partition?
            #
            # Peter agreed that this would be a good thing to do.

            num_districts = len(partition.assignment.parts.keys())

            # Compute the total population for each locality and then the number of "allowed pieces"
            for loc in self.localities:
                # frm: TODO: Refactoring:    The code below just calculates the total population for a set of nodes.
                #               This sounds like a good candidate for a utility function.  See if this
                #               logic is repeated elsewhere...

                # Compute the population associated with each location
                the_graph = partition.graph
                locality_population = {}  # dict mapping locality name to population in that locality
                for node_id in the_graph.node_indices:
                    locality_name = the_graph.node_data(node_id)[self.col_id]
                    locality_pop = the_graph.node_data(node_id)[self.pop_col]
                    if locality_name not in locality_population:
                        locality_population[locality_name] = locality_pop
                    else:
                        locality_population[locality_name] += locality_pop

                # frm: TODO: Refactoring:  Peter commented (in PR) that this is another thing that
                #               could be cached so we didn't recompute it over and over...
                ideal_population_per_district = totpop / num_districts

                # Compute the number of "allowed pieces" for each locality
                allowed_pieces = {}
                for locality_name in locality_population.keys():
                    pop_for_locality = locality_population[locality_name]
                    allowed_pieces[locality_name] = math.ceil(pop_for_locality / ideal_population_per_district)

            self.allowed_pieces = allowed_pieces

        for s in self.scores:
            if s == "num_parts":
                self.scores[s] = self.num_parts(partition)

            if s == "num_pieces":
                self.scores[s] = self.num_pieces(partition)

            if s == "naked_boundary":
                self.scores[s] = self.naked_boundary(partition)

            if s == "shannon_entropy":
                self.scores[s] = self.shannon_entropy(partition)

            if s == "power_entropy":
                self.scores[s] = self.power_entropy(partition)

            if s == "symmetric_entropy":
                self.scores[s] = self.symmetric_entropy(partition)

            if s == "num_split_localities":
                self.scores[s] = self.num_split_localities(partition)

        return self.scores

    def num_parts(self, partition) -> int:
        """
        Calculates the number of unique locality-district pairs.

        :param partition: The partition to be scored.
        :type partition: :class:`~gerrychain.Partition`

        :returns: The number of parts, i.e. the number of unique
           locality-district pairs.
        :rtype: int
        """

        counter = 0
        for district in self.locality_splits.keys():
            counter += len(self.locality_splits[district])
        return counter

    def num_pieces(self, partition) -> int:
        """
        Calculates the number of pieces.

        :param partition: The partition to be scored.
        :type partition: :class:`~gerrychain.Partition`

        :returns: Number of pieces, where each piece is formed by
            cutting the graph by both locality and district boundaries.
        :rtype: int
        """
        locality_intersections = {}

        for n in partition.graph.node_indices:
            locality = partition.graph.node_data(n)[self.col_id]
            if locality not in locality_intersections:
                locality_intersections[locality] = set(
                    [partition.assignment.mapping[n]]
                )

            locality_intersections[locality].update([partition.assignment.mapping[n]])

        pieces = 0
        for locality in locality_intersections:
            for d in locality_intersections[locality]:
                subgraph = partition.graph.subgraph(
                    [
                        x
                        for x in partition.parts[d]
                        if partition.graph.node_data(x)[self.col_id] == locality
                    ]
                )

                pieces += subgraph.num_connected_components()
        return pieces

    def naked_boundary(self, partition) -> int:
        """
        Computes the number of cut edges inside localities (i.e. the
            number of cut edges with both endpoints in the same locality).

        :param partition: The partition to be scored.
        :type partition: :class:`~gerrychain.Partition`

        :returns: The number of cut edges within a locality.
        :rtype: int
        """

        cut_edges_within = 0
        cut_edge_set = partition["cut_edges"]
        for i in cut_edge_set:
            vtd_1 = i[0]
            vtd_2 = i[1]
            county_1 = self.localitydict.get(vtd_1)
            county_2 = self.localitydict.get(vtd_2)
            if county_1 == county_2:  # not on county boundary
                cut_edges_within += 1
        return cut_edges_within

    def shannon_entropy(self, partition) -> float:
        """
        Computes the shannon entropy score of a district plan.

        :param partition: The partition to be scored.
        :type partition: :class:`~gerrychain.Partition`

        :returns: Shannon entropy score.
        :rtype: float
        """

        total_vtds = 0
        for k, v in self.locality_splits.items():
            for x in list(v.values()):
                total_vtds += x

        entropy = 0
        for locality_j in self.localities:  # iter thru locs to get total count
            tot_county_vtds = 0
            # iter thru counters
            for k, v in self.locality_splits.items():
                v = dict(v)
                if locality_j in list(v.keys()):
                    tot_county_vtds += v[locality_j]

            inner_sum = 0
            q = tot_county_vtds / total_vtds

            # iter thru districts to get vtds in county in district
            # for district in range(num_districts):
            for k, v in self.locality_splits.items():
                # counter = dict(locality_splits[district+1])
                count = dict(v)
                if locality_j in count:
                    intersection = count[str(locality_j)]
                    p = intersection / tot_county_vtds

                    if p != 0:
                        inner_sum += p * math.log(1 / p)

            entropy += q * (inner_sum)
        return entropy

    def power_entropy(self, partition) -> float:
        """
        Computes the power entropy score of a district plan.

        :param partition: The partition to be scored.
        :type partition: :class:`~gerrychain.Partition`

        :returns: Power entropy score.
        :rtype: float
        """

        total_vtds = 0  # count the total number of vtds in state
        for k, v in self.locality_splits.items():
            for x in list(v.values()):
                total_vtds += x

        entropy = 0
        for locality_j in self.localities:  # iter thru locs to get total count
            tot_county_vtds = 0
            # iter thru counters
            for k, v in self.locality_splits.items():
                v = dict(v)
                if locality_j in list(v.keys()):
                    tot_county_vtds += v[locality_j]

            inner_sum = 0

            q = tot_county_vtds / total_vtds
            # iter thru districts to get vtds in county in district
            # for district in range(num_districts):
            for k, v in self.locality_splits.items():
                # counter = dict(locality_splits[district+1])
                count = dict(v)
                if locality_j in count:
                    intersection = count[str(locality_j)]
                    p = intersection / tot_county_vtds

                    if p != 0:
                        inner_sum += p ** (1 - self.pent_alpha)

            entropy += 1 / q * (inner_sum - 1)
        return entropy

    def symmetric_entropy(self, partition) -> float:  # IN PROGRESS
        """
        Calculates the symmetric entropy score.

        Warning::

            This function is previously marked incomplete.

        :param partition: The partition to be scored.
        :type partition: :class:`~gerrychain.Partition`

        :returns: The symmetric square root entropy score.
        :rtype: float
        """

        district_dict = dict(partition.parts)

        for district in district_dict.keys():
            vtds = district_dict[district]
            locality_pop = {k: 0 for k in self.localities}
            for vtd in vtds:
                locality_pop[self.localitydict[vtd]] += partition.graph.node_data(vtd)[
                    self.pop_col
                ]
            district_dict[district] = locality_pop

        district_dict_inv = defaultdict(dict)
        for k, v in district_dict.items():
            for k2, v2 in v.items():
                district_dict_inv[k2][k] = v2

        # how do districts split localities?
        score = 0
        for district in district_dict.keys():
            localities_and_pops = district_dict[district]
            total = sum(localities_and_pops.values())
            fractional_sum = 0
            for locality in localities_and_pops.keys():
                fractional_sum += math.sqrt(localities_and_pops[locality] / total)
            score += total * fractional_sum

        # how do localities split districts?
        for locality in district_dict_inv.keys():
            districts_and_pops = district_dict_inv[locality]
            total = sum(districts_and_pops.values())
            fractional_sum = 0
            for district in districts_and_pops.keys():
                fractional_sum += math.sqrt(districts_and_pops[district] / total)
            score += total * fractional_sum

        return score

    def num_split_localities(self, partition) -> int:
        """
        Calculates the number of localities touching 2 or more districts.

        :param partition: The partition to be scored.
        :type partition: :class:`~gerrychain.Partition`

        :returns: The number of split localities, i.e. the number of localities
            touching 2 or more districts.
        :rtype: int
        """

        total_splits = 0

        for v in self.locality_splits_inv.values():
            if len(v) > 1:
                total_splits += 1

        return total_splits
