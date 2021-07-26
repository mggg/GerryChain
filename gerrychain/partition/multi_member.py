from gerrychain.partition import Partition

class MultiMemberPartition(Partition):
    """A :class:`Partition` with district magnitude information included.
    These additional data allows for districts of different scales (number of representatives)
    to be properly balanced.
    """

    def __init__(self, graph=None, assignment=None, updaters=None, magnitudes=None,
                 parent=None, flips=None):
        """
        :param graph: Underlying graph.
        :param assignment: Dictionary assigning nodes to districts.
        :param updaters: Dictionary of functions to track data about the partition.
            The keys are stored as attributes on the partition class,
            which the functions compute.
        :param magnitudes: Dictionary assigning districts to number of representatives
        """
        super().__init__(graph=graph, assignment=assignment, updaters=updaters, parent=parent, flips=flips)
        if parent is None:
            self._init_magnitudes(assignment, magnitudes)
        else:
            self._update_magnitudes_from_parent(parent, magnitudes)

    def _init_magnitudes(self, assignment, magnitudes):
        dist_ids = assignment.parts.keys()
        self.magnitudes = {dist_id: 1 for dist_id in dist_ids}
        if magnitudes != None:
            self.magnitudes = {**self.magnitudes, **magnitudes}


    def _update_magnitudes_from_parent(self, parent, magnitudes):
        self.magnitudes = {**parent.magnitudes, **magnitudes}

    def flip(self, flips, magnitudes):
        return self.__class__(parent=self, flips=flips, magnitudes=magnitudes)