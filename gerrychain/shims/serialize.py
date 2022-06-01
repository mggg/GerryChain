import gerrychain
import pandas as pd


def serialize_partition(partition: gerrychain.Partition, filename: str):
    graph = partition.graph
    graph.to_json(filename)

    graph = gerrychain.Graph.from_json(filename)
    graph.add_data(pd.DataFrame({"assignment": partition.assignment.to_series() + 1}))
    graph.to_json(filename)
