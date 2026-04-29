# Imports
import math
from collections import Counter, defaultdict
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

    Attributes:
        name (str): The name of the updater (e.g. "countysplits")
        col_id (str): The name of the column containing the locality
            attribute (i.e. county ids, municipality names, etc.)
        pop_col (str): The name of the column containing population counts.
        scores_to_compute (List[str]): A list/tuple/set of strings naming the
            score functions to compute at each step. This will generally be
            some subcollection of ```['num_parts', 'num_pieces',
            'naked_boundary', 'shannon_entropy', 'power_entropy',
            'symmetric_entropy', 'num_split_localities']```
        pent_alpha (float): A number between 0 and 1 which is passed as the
            exponent to `LocalitySplits.power_entropy`
        localities (List[str]): A list containing the unique locality identifiers
            (e.g. county names, municipality names, etc.) for the partition.
            This list is populated using the locality data stored on each of
            the nodes in the graph.
        localitydict (Dict[str, str]): A dictionary mapping node IDs to locality IDs.
            This is used to quickly look up the locality of a given node.
        locality_splits (Dict[int, Counter[str]]): A dictionary mapping district IDs to a counter
            of localities in that district. That is to say, this tells us
            how many nodes in each district are of the given locality type.
        locality_splits_inv (Dict[str, Dict[int, int]]): The inverted dictionary of locality_splits
        allowed_pieces (Dict[str, int]): A dictionary that maps each locality to the
            minimum number of districts that locality must touch. This is
            computed using the ideal district population. NOT CURRENTLY USED.
        scores (Dict[str, Any]): A dictionary initialized with the key values from the
            initializer's scores_to_compute parameter. The initial values are
            set to none and are updated in each call to store the compted
            score value for each metric of interest.
    """

    def __init__(
        self,
        name: str,
        col_id: str,
        pop_col: str,
        scores_to_compute: List[str] = ["num_parts"],
        pent_alpha: float = 0.05,
    ):
        """Initialize a LocalitySplits instance.

        Args:
            name (str): The name of the updater (e.g. "countysplits")
            col_id (str): The name of the column containing the locality attribute (i.e. county
                ids, municipality names, etc.)
            pop_col (str): The name of the column containing population counts.
            scores_to_compute (List[str], optional): A list/tuple/set of strings naming the score
                functions to compute at each step. This should be some subcollection of
                ```['num_parts', 'num_pieces', 'naked_boundary', 'shannon_entropy',
                'power_entropy', 'symmetric_entropy', 'num_split_localities']```. Default is
                ["num_parts"].
            pent_alpha (float, optional): A number between 0 and 1 which is passed as the exponent
                to `LocalitySplits.power_entropy`. Default is 0.05.
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

        if self.localities == []:
            self.localitydict = {}
            for node_id in partition.graph.node_indices:
                self.localitydict[node_id] = partition.graph.node_data(node_id)[self.col_id]

            self.localities = set(list(self.localitydict.values()))

        locality_splits = {
            k: [self.localitydict[v] for v in d] for k, d in partition.assignment.parts.items()
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
                # Note: It would be nice to cache the total population for the partition's
                # graph since it cannot be changed, but to do so we would need to know the
                # attribute in the partition's graph that stored population, and we don't
                # seem to have both the graph and the population attribute name at the
                # same time...  .

                totpop += partition.graph.node_data(node_id)[self.pop_col]

            num_districts = len(partition.assignment.parts.keys())

            # Compute the total population for each locality and then the number of
            # "allowed pieces"
            for _ in self.localities:

                # Compute the population associated with each location
                the_graph = partition.graph
                locality_population = (
                    {}
                )  # dict mapping locality name to population in that locality
                for node_id in the_graph.node_indices:
                    locality_name = the_graph.node_data(node_id)[self.col_id]
                    locality_pop = the_graph.node_data(node_id)[self.pop_col]
                    if locality_name not in locality_population:
                        locality_population[locality_name] = locality_pop
                    else:
                        locality_population[locality_name] += locality_pop

                ideal_population_per_district = totpop / num_districts

                # Compute the number of "allowed pieces" for each locality
                allowed_pieces = {}
                for locality_name in locality_population.keys():
                    pop_for_locality = locality_population[locality_name]
                    allowed_pieces[locality_name] = math.ceil(
                        pop_for_locality / ideal_population_per_district
                    )

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
        """Calculates the number of unique locality-district pairs.

        Args:
            partition (Partition): The partition to be scored.

        Returns:
            int: The number of parts, i.e. the number of unique locality-district pairs.
        """

        counter = 0
        for district in self.locality_splits.keys():
            counter += len(self.locality_splits[district])
        return counter

    def num_pieces(self, partition) -> int:
        """Calculates the number of pieces formed by cutting the graph by both locality and
        district boundaries.


        Args:
            partition (Partition): The partition to be scored.

        Returns:
            int: Number of pieces, where each piece is formed by cutting the graph by both locality
                and district boundaries.
        """
        locality_intersections = {}

        for n in partition.graph.node_indices:
            locality = partition.graph.node_data(n)[self.col_id]
            if locality not in locality_intersections:
                locality_intersections[locality] = set([partition.assignment.mapping[n]])

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
        """Computes the number of cut edges inside localities.

        Args:
            partition (Partition): The partition to be scored.

        Returns:
            int: The number of cut edges within a locality.
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
        """Computes the shannon entropy score of a district plan.

        Args:
            partition (Partition): The partition to be scored.

        Returns:
            float: Shannon entropy score.
        """

        total_vtds = 0
        for v in self.locality_splits.values():
            for x in list(v.values()):
                total_vtds += x

        entropy = 0
        for locality_j in self.localities:  # iter thru locs to get total count
            tot_county_vtds = 0
            # iter thru counters
            for v in self.locality_splits.values():
                v = dict(v)
                if locality_j in list(v.keys()):
                    tot_county_vtds += v[locality_j]

            inner_sum = 0
            q = tot_county_vtds / total_vtds

            # iter thru districts to get vtds in county in district
            # for district in range(num_districts):
            for v in self.locality_splits.values():
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
        """Computes the power entropy score of a district plan.

        Args:
            partition (Partition): The partition to be scored.

        Returns:
            float: Power entropy score.
        """

        total_vtds = 0  # count the total number of vtds in state
        for v in self.locality_splits.values():
            for x in list(v.values()):
                total_vtds += x

        entropy = 0
        for locality_j in self.localities:  # iter thru locs to get total count
            tot_county_vtds = 0
            # iter thru counters
            for v in self.locality_splits.values():
                v = dict(v)
                if locality_j in list(v.keys()):
                    tot_county_vtds += v[locality_j]

            inner_sum = 0

            q = tot_county_vtds / total_vtds
            # iter thru districts to get vtds in county in district
            # for district in range(num_districts):
            for v in self.locality_splits.values():
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
        """Calculates the symmetric entropy score

        Warning:
            This method is currently in progress and may not be fully functional.

        Args:
            partition (Partition): The partition to be scored.

        Returns:
            float: The symmetric square root entropy score.
        """

        district_dict = dict(partition.parts)

        for district in district_dict.keys():
            vtds = district_dict[district]
            locality_pop = {k: 0 for k in self.localities}
            for vtd in vtds:
                locality_pop[self.localitydict[vtd]] += partition.graph.node_data(vtd)[self.pop_col]
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
        """Calculates the number of localities touching 2 or more districts.

        Args:
            partition (Partition): The partition to be scored.

        Returns:
            int: The number of split localities, i.e. the number of localities touching 2 or more
                districts.
        """

        total_splits = 0

        for v in self.locality_splits_inv.values():
            if len(v) > 1:
                total_splits += 1

        return total_splits
