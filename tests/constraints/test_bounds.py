from gerrychain import constraints
from gerrychain.constraints import within_percent_of_ideal_population


class TestWithinPercent:
    def test_within_percent_fails_when_deviation_too_large(self):
        partition = {"population": {1: 100, 2: 100, 3: 100}}

        percent = 0.5
        constraint = within_percent_of_ideal_population(partition, percent)

        ideal = 100
        too_much_deviation = ideal * (percent + 0.2)
        new_partition = {
            "population": {
                1: 100 - too_much_deviation / 2,
                2: 100 - too_much_deviation / 2,
                3: 100 + too_much_deviation,
            }
        }

        assert not constraint(new_partition)

    def test_within_percent_fails_when_expected(self):
        partition = {"population": {1: 100, 2: 100, 3: 100}}

        percent = 0.5
        constraint = within_percent_of_ideal_population(partition, percent)

        new_partition = {"population": {1: 280, 2: 100, 3: 100}}

        assert not constraint(new_partition)

    def test_within_percent_fails_when_expected2(self):
        partition = {"population": {1: 100, 2: 100, 3: 100}}

        percent = 0.5
        constraint = within_percent_of_ideal_population(partition, percent)

        new_partition = {"population": {1: 200, 2: 10, 3: 100}}

        assert not constraint(new_partition)


class TestLowerBound:
    def test_fails_values_below_bound(self):
        bound = constraints.LowerBound(lambda x: x, 100)

        assert bound(50) is False

    def test_passes_values_above_bound(self):
        bound = constraints.LowerBound(lambda x: x, 100)

        assert bound(150) is True

    def test_bound_allows_equality(self):
        bound = constraints.LowerBound(lambda x: x, 100)

        assert bound(100) is True

    def test_has_informative_repr(self):
        def my_function(x):
            return 150

        bound = constraints.LowerBound(my_function, 100)

        assert repr(bound) == "<LowerBound(my_function <= 100)>"


class TestUpperBound:
    def test_passes_values_below_bound(self):
        bound = constraints.UpperBound(lambda x: x, 100)

        assert bound(50) is True

    def test_fails_values_above_bound(self):
        bound = constraints.UpperBound(lambda x: x, 100)

        assert bound(150) is False

    def test_bound_allows_equality(self):
        bound = constraints.UpperBound(lambda x: x, 100)

        assert bound(100) is True

    def test_has_informative_repr(self):
        def my_function(x):
            return 150

        bound = constraints.UpperBound(my_function, 100)

        assert repr(bound) == "<UpperBound(my_function >= 100)>"
