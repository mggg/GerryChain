from rundmcmc.scores import efficiency_gap, wasted_votes

# data from Moon's slides
data = {
    'A': {1: 95, 2: 40, 3: 75, 4: 45, 5: 45},
    'B': {1: 5, 2: 60, 3: 25, 4: 55, 5: 55}
}


def test_efficiency_gap():
    mock_partition = data
    result = efficiency_gap(mock_partition, 'A', 'B')
    assert result == 0.3


def test_wasted_votes():
    result = [wasted_votes(data['A'][i], data['B'][i]) for i in range(1, 6)]
    assert result == [(45, 5), (40, 10), (25, 25), (45, 5), (45, 5)]
