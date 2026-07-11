import json

from backend.utils.performance_dashboard import PerformanceAlertManager, PerformanceDashboard


def test_dashboard_loads_metrics_summarizes_and_saves_html(tmp_path):
    (tmp_path / "baseline_latest.json").write_text(json.dumps({"analysis": {"total_benchmarks": 2, "performance_categories": {"excellent": [1, 2]}, "summary": {"average": 0.1}}}))
    (tmp_path / "comparison_one.json").write_text(json.dumps({"regressions": [{"test": "a", "current": 2, "baseline": 1, "change_percentage": 100}], "improvements": [{"test": "b", "current": 1, "baseline": 2, "change_percentage": -50}], "stable": [], "summary": {"regressions": 1, "improvements": 1, "stable": 0}}))
    dashboard = PerformanceDashboard(tmp_path)
    summary = dashboard.get_performance_summary()
    assert summary["overall_health"] == "critical"
    assert dashboard.get_endpoint_performance()["a"]["status"] == "regression"
    assert "Performance Dashboard" in dashboard.generate_html_dashboard()
    output = dashboard.save_dashboard(tmp_path / "dashboard.html")
    assert output.exists()


def test_alert_manager_reports_threshold_breaches():
    manager = PerformanceAlertManager()
    alerts = manager.check_performance_alerts({"regressions": [{"test": "slow", "current": 6}]})
    assert len(alerts) == 2
    assert "slow" in manager.generate_alert_report()
