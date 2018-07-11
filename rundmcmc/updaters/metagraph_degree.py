class MetagraphDegree:

    """
    Updater that computes the metagraph degree of a proposed partition; i.e.,
    the number of possible single flips to make to turn into another partition.

    """

    def __init__(self, validator, alias):
        """
        :validator: :class:`~rundmcmc.validty.Validator` instance.

        """
        self.validator = validator
        self.alias = alias

    def __call__(self, partition):
        total_available_flips = 2 * len(partition['cut_edges'])

        total_valid_flips = sum(self.num_valid_flips(edge, partition)
                                for edge in partition['cut_edges'])

        return {'total': total_available_flips, 'valid': total_valid_flips}

    def num_valid_flips(self, edge, partition):
        """Determine number of valid flips for the given edge (0, 1, or 2)."""
        flip = {edge[0]: partition.assignment[edge[1]]}
        reverse_flip = {edge[1]: partition.assignment[edge[0]]}

        # XXX: This is really awful.
        del partition.updaters[self.alias]
        flip_valid = self.validator(partition.merge(flip))
        reverse_valid = self.validator(partition.merge(reverse_flip))
        partition.updaters[self.alias] = self

        return flip_valid + reverse_valid
