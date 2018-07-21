import math
import random
from unittest.mock import MagicMock

from rundmcmc.output import ChainOutputTable, pipe_to_table, p_value_report


class TestChainOutputTable:
    def setup(self):
        table = ChainOutputTable()
        mock_row1 = {'population': {1: 100.0, 2: 50.0}, 'area': {1: 1000, 2: 400}}
        mock_row2 = {'population': {1: 125.0, 2: 25.0}, 'area': {1: 1200, 2: 200}}
        table.append(mock_row1)
        table.append(mock_row2)
        return table, mock_row1, mock_row2

    def test_chain_output_table_can_access_by_property(self):
        table, mock_row1, mock_row2 = self.setup()
        # The table can be accessed by property
        assert table['population'] == [mock_row1['population'], mock_row2['population']]

    def test_chain_output_table_can_access_by_row(self):
        table, mock_row1, mock_row2 = self.setup()
        # The table can be accessed by row
        assert table[0] == mock_row1
        assert table[1] == mock_row2

    def test_chain_output_table_can_access_by_district(self):
        table, mock_row1, mock_row2 = self.setup()
        assert table.district(1) == [{'population': 100.0, 'area': 1000},
                            {'population': 125.0, 'area': 1200}]


class TestPipeToTable:
    def setup(self):
        """
        Generates some random mock scores with mock data
        """
        number_of_scores = random.randint(2, 10)
        number_of_rows = random.randint(5, 50)

        def random_data(length):
            return list(random.random() for i in range(length))

        values = {str(i): random_data(number_of_rows) for i in range(number_of_scores)}

        mock_chain = MagicMock()
        mock_chain.__iter__.return_value = range(number_of_rows)

        handlers = dict()
        for key in values:
            mock_score = MagicMock()
            mock_score.side_effect = values[key]
            handlers[key] = mock_score

        return mock_chain, handlers, values

    def test_pipe_to_table_records_all_scores_by_default(self):
        mock_chain, handlers, values = self.setup()

        table = pipe_to_table(mock_chain, handlers, display=False)

        assert all(table[key] == values[key] for key in values)


def test_p_value_report_gives_the_right_value_when_the_whole_ensemble_is_lower_than_initial():
    mock_ensemble_scores = [1] * 199 + [17] * 1
    initial_plan_score = 17
    # We have 199 scores < 17, and 1 score >= 17, so we have 1/200
    # higher than the initial score. This should give a p-value of
    # sqrt(2 * 1/200) = 1/10.

    result = p_value_report('Mock Score', mock_ensemble_scores, initial_plan_score)

    assert result['fraction_as_high'] == 1 / 200
    assert result['p_value'] == 1 / 10
    assert result['opposite_p_value'] == math.sqrt(2 * 199 / 200)
