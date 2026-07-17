import json

from backend.utils.statistics import StatisticsTracker


def test_statistics_records_persists_and_reloads(tmp_path, monkeypatch, capsys):
    path = tmp_path / "stats.json"
    clock = iter([10, 70])
    monkeypatch.setattr("backend.utils.statistics._current_time", lambda: next(clock))
    tracker = StatisticsTracker(stats_file=str(path))
    tracker.start()
    tracker.record_article_found("nvd", 4)
    tracker.record_article_parsed("nvd", 3)
    tracker.record_article_inserted("nvd", 2)
    tracker.record_article_skipped("nvd")
    tracker.record_error("nvd")
    tracker.stop()
    assert tracker.get_duration() == 60
    assert tracker.get_articles_per_minute() == 3
    assert tracker.get_success_rate() == 75
    assert tracker.save_statistics() is True
    assert json.loads(path.read_text())["total"]["found"] == 4
    tracker.display_summary()
    assert "Overall" in capsys.readouterr().out
    restored = StatisticsTracker(stats_file=str(path))
    assert restored.total_parsed == 3
    restored.reset()
    assert restored.total_found == 0


def test_disabled_statistics_is_a_noop(tmp_path):
    tracker = StatisticsTracker(enabled=False, stats_file=str(tmp_path / "ignored.json"))
    tracker.start(); tracker.record_article_found("nvd"); tracker.stop()
    assert tracker.total_found == 0
    assert tracker.save_statistics() is True
