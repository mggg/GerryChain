class Subgraphs:
    """Updater providing the subgraphs of each part of the partition.
    """
    def __init__(self, graph):
        """
        :param graph: The underlying adjacency graph of the partition.
        """
        self._nodes_cache = {}
        self._subgraphs_cache = {}
        self.graph = graph

    def __call__(self, partition):
        for part, nodes in partition.assignment.parts.items():
            if part not in self._nodes_cache or self._nodes_cache[part] is not nodes:
                self._nodes_cache[part] = nodes
                if part in self._subgraphs_cache:
                    del self._subgraphs_cache[part]
        return self

    def __getitem__(self, part):
        if part in self._subgraphs_cache:
            return self._subgraphs_cache[part]
        elif part in self._nodes_cache:
            self._subgraphs_cache[part] = self.graph.subgraph(self._nodes_cache[part])
            return self._subgraphs_cache[part]
        raise KeyError
