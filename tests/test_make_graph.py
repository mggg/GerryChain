import pandas

from gerrychain.graph import Graph


def test_add_data_to_graph_can_handle_column_names_that_start_with_numbers():
    graph = Graph([('01', '02'), ('02', '03'), ('03', '01')])
    df = pandas.DataFrame({'16SenDVote': [20, 30, 50], 'node': ['01', '02', '03']})
    df = df.set_index('node')

    graph.add_data(df, ['16SenDVote'])

    assert graph.nodes['01']['16SenDVote'] == 20
    assert graph.nodes['02']['16SenDVote'] == 30
    assert graph.nodes['03']['16SenDVote'] == 50


def test_add_data_to_graph_can_handle_unset_index_when_id_col_is_passed():
    graph = Graph([('01', '02'), ('02', '03'), ('03', '01')])
    df = pandas.DataFrame({'16SenDVote': [20, 30, 50], 'node': ['01', '02', '03']})

    graph.join(df, ['16SenDVote'], right_index='node')

    assert graph.nodes['01']['16SenDVote'] == 20
    assert graph.nodes['02']['16SenDVote'] == 30
    assert graph.nodes['03']['16SenDVote'] == 50
