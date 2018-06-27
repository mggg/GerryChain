from rundmcmc.output import ChainOutputTable


def setup():
    table = ChainOutputTable()
    mock_row1 = {'population': {1: 100.0, 2: 50.0}, 'area': {1: 1000, 2: 400}}
    mock_row2 = {'population': {1: 125.0, 2: 25.0}, 'area': {1: 1200, 2: 200}}
    table.append(mock_row1)
    table.append(mock_row2)
    return table, mock_row1, mock_row2


def test_chain_output_table_can_access_by_property():
    table, mock_row1, mock_row2 = setup()
    # The table can be accessed by property
    assert table['population'] == [mock_row1['population'], mock_row2['population']]


def test_chain_output_table_can_access_by_row():
    table, mock_row1, mock_row2 = setup()
    # The table can be accessed by row
    assert table[0] == mock_row1
    assert table[1] == mock_row2


def test_chain_output_table_can_access_by_district():
    table, mock_row1, mock_row2 = setup()
    assert table.district(1) == [{'population': 100.0, 'area': 1000},
                          {'population': 125.0, 'area': 1200}]
