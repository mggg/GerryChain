import pytest
from rundmcmc.scores import efficiency_gap, wasted_votes, mean_median
from rundmcmc.updaters.election import ElectionResults


@pytest.fixture
def mock_election():
    return ElectionResults(None,
    {
        'A': {1: 95, 2: 40, 3: 75, 4: 45, 5: 45},
        'B': {1: 5, 2: 60, 3: 25, 4: 55, 5: 55}
    },
    {1: 100, 2: 100, 3: 100, 4: 100, 5: 100},
    {
        'A': {1: 0.95, 2: 0.40, 3: 0.75, 4: 0.45, 5: 0.45},
        'B': {1: 0.05, 2: 0.60, 3: 0.25, 4: 0.55, 5: 0.55}
    })


def test_efficiency_gap(mock_election):
    result = efficiency_gap(mock_election)
    assert result == 0.3


def test_wasted_votes(mock_election):
    result = [wasted_votes(mock_election.totals_for_party['A'][i],
                           mock_election.totals_for_party['B'][i]) for i in range(1, 6)]
    assert result == [(45, 5), (40, 10), (25, 25), (45, 5), (45, 5)]


def test_partisan_scores_point_the_same_way(mock_election):
    eg = efficiency_gap(mock_election)
    mm = mean_median(mock_election)

    assert (eg > 0 and mm > 0) or (eg < 0 and mm < 0)


def test_mean_median_has_right_value(mock_election):
    mm = mean_median(mock_election)

    assert abs(mm - -0.15) < 0.00001


def test_partisan_scores_are_positive_if_second_party_has_advantage(mock_election):
    eg = efficiency_gap(mock_election)
    mm = mean_median(mock_election)

    assert (eg > 0 and mm > 0)
