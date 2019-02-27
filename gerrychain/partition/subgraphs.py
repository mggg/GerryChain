class SubgraphView:
    def __init__(self, graph, parts):
        self.graph = graph
        self.parts = parts
        self.subgraphs_cache = {}

    def __getitem__(self, part):
        if part not in self.subgraphs_cache:
            self.subgraphs_cache[part] = self.graph.subgraph(self.parts[part])
        return self.subgraphs_cache[part]

    def __iter__(self):
        for part in self.parts:
            yield self[part]

    def items(self):
        for part in self.parts:
            yield part, self[part]
