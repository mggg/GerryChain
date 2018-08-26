from rundmcmc.output import SlimPValueReport


def test_slim_p_value_report_has_a_str_method():
    report = SlimPValueReport()
    assert str(report)


def test_slim_p_value_report_can_render():
    report = SlimPValueReport()
    assert report.render()
