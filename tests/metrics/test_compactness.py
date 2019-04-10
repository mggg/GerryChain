import math
from gerrychain.metrics.compactness import compute_polsby_popper


def test_polsby_popper_returns_nan_when_perimeter_is_0():
    area = 10
    perimeter = 0
    assert compute_polsby_popper(area, perimeter) is math.nan
