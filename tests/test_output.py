from unittest.mock import MagicMock

import pytest

from rundmcmc.output import SlimPValueReport


@pytest.fixture
def mock_election():
    mock = MagicMock()
    mock.name = "2008 Presidential"
    mock.parties_to_columns = ["Republican", "Democratic"]
    return mock


def test_slim_p_value_report_has_a_str_method(mock_election):
    report = SlimPValueReport(mock_election)
    assert str(report)


def test_slim_p_value_renders_with_election_name_in_it(mock_election):
    report = SlimPValueReport(mock_election)
    assert "election" in report.render()


def test_slim_p_value_renders_with_reports_for_each_score(mock_election):
    report = SlimPValueReport(mock_election)
    analysis = report.render()["analysis"]
    scores = {result["score"] for result in analysis}
    assert scores == {"Mean-Median", "Mean-Thirdian", "Efficiency Gap"}
