from unittest.mock import MagicMock

import pytest

from gerrychain.updaters.election import ElectionResults


@pytest.fixture
def mock_election():
    election = MagicMock()
    election.parties = ["B", "A"]

    return ElectionResults(
        election,
        {
            "B": {1: 5, 2: 60, 3: 25, 4: 55, 5: 55},
            "A": {1: 95, 2: 40, 3: 75, 4: 45, 5: 45},
        },
        [1, 2, 3, 4, 5],
    )

def test_election_results_can_compute_mm(mock_election):
    assert mock_election.mean_median() is not None

def test_election_results_can_compute_mt(mock_election):
    assert mock_election.mean_thirdian() is not None

def test_election_results_can_compute_eg(mock_election):
    assert mock_election.efficiency_gap() is not None

def test_election_results_can_copmute_bias(mock_election):
    assert mock_election.partisan_bias() is not None

def test_election_results_can_compute_gini(mock_election):
    assert mock_election.partisan_gini() is not None

def test_election_results_can_compute_percents(mock_election):
    assert mock_election.percent("A") > 0
