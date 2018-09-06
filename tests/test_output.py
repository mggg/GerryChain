from unittest.mock import MagicMock

import pytest

from rundmcmc.output import SlimPValueReport


@pytest.fixture
def mock_election():
    mock = MagicMock()
    mock.name = "2008 Presidential"
    mock.alias = "2008 Presidential"
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


def test_slim_p_value_report_has_a_histogram(mock_election):
    mock_score = MagicMock()
    mock_score.side_effect = [0.1, 0.1, 0.5, 0.9]
    report = SlimPValueReport(mock_election, scores={"mock_score": mock_score})

    for i in range(3):
        mock_results = MagicMock()
        report(mock_results)

    total_number_binned = sum(report.histograms["mock_score"].counter.values())
    assert total_number_binned == 3


def test_slim_p_value_report_includes_histogram_in_rendered_version(mock_election):
    mock_score = MagicMock()
    mock_score.side_effect = [0.1, 0.1, 0.5, 0.9]
    report = SlimPValueReport(mock_election, scores={"mock_score": mock_score})

    for i in range(3):
        mock_results = MagicMock()
        report(mock_results)

    rendered_report = report.render()
    assert all("histogram" in item for item in rendered_report["analysis"])


def test_slim_p_value_renders_without_histograms_if_requested(mock_election):
    mock_score = MagicMock()
    mock_score.side_effect = [0.1, 0.1, 0.5, 0.9]
    report = SlimPValueReport(mock_election, scores={"mock_score": mock_score})

    for i in range(3):
        mock_results = MagicMock()
        report(mock_results)

    rendered_report = report.render_without_histograms()
    assert all("histogram" not in item for item in rendered_report["analysis"])
