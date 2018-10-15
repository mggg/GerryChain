from gerrychain.constraints import within_percent_of_ideal_population


def test_within_percent_fails_when_deviation_too_large():
    partition = {"population": {1: 100, 2: 100, 3: 100}}

    percent = 0.5
    constraint = within_percent_of_ideal_population(partition, percent)

    ideal = 100
    too_much_deviation = ideal * (percent + 0.2)
    new_partition = {"population": {
        1: 100 - too_much_deviation / 2,
        2: 100 - too_much_deviation / 2,
        3: 100 + too_much_deviation}
    }

    assert not constraint(new_partition)


def test_within_percent_fails_when_expected():
    partition = {"population": {1: 100, 2: 100, 3: 100}}

    percent = 0.5
    constraint = within_percent_of_ideal_population(partition, percent)

    new_partition = {"population": {1: 280, 2: 100, 3: 100}}

    assert not constraint(new_partition)


def test_within_percent_fails_when_expected2():
    partition = {"population": {1: 100, 2: 100, 3: 100}}

    percent = 0.5
    constraint = within_percent_of_ideal_population(partition, percent)

    new_partition = {"population": {1: 200, 2: 10, 3: 100}}

    assert not constraint(new_partition)
