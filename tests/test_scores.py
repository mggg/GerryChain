from rundmcmc.scores import efficiency_gap, wasted_votes, mean_median

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


def test_partisan_scores_point_the_same_way():
    mock_election = dict()
    mock_election['a'] = data['A']
    mock_election['b'] = data['B']
    mock_election['a%'] = {key: mock_election['a'][key] /
        (mock_election['a'][key] + mock_election['b'][key]) for key in mock_election['b']}

    eg = efficiency_gap(mock_election, 'a', 'b')
    mm = mean_median(mock_election, 'a%')

    assert (eg > 0 and mm > 0) or (eg < 0 and mm < 0)


def test_partisan_scores_are_positive_if_second_party_has_advantage():
    mock_election = dict()
    mock_election['a'] = data['A']
    mock_election['b'] = data['B']
    mock_election['a%'] = {key: mock_election['a'][key] /
        (mock_election['a'][key] + mock_election['b'][key]) for key in mock_election['b']}

    eg = efficiency_gap(mock_election, 'a', 'b')
    mm = mean_median(mock_election, 'a%')

    assert (eg > 0 and mm > 0)
