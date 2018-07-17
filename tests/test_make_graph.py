import networkx
import pandas

from rundmcmc.make_graph import add_data_to_graph


def test_add_data_to_graph_can_handle_column_names_that_start_with_numbers():
    graph = networkx.Graph([('01', '02'), ('02', '03'), ('03', '01')])
    df = pandas.DataFrame({'16SenDVote': [20, 30, 50], 'node': ['01', '02', '03']})
    df = df.set_index('node')

    add_data_to_graph(df, graph, ['16SenDVote'])

    assert graph.nodes['01']['16SenDVote'] == 20
    assert graph.nodes['02']['16SenDVote'] == 30
    assert graph.nodes['03']['16SenDVote'] == 50
