import os

import pytest

from backend.utils import pid_manager


def test_pid_manager_acquires_releases_and_reads_lock(tmp_path, monkeypatch):
    lock = tmp_path / "crawler.pid"
    monkeypatch.setattr(pid_manager.PIDManager, "_is_running", lambda self: False)
    manager = pid_manager.PIDManager(str(lock))

    assert manager.acquire_lock() is True
    assert manager.lock_acquired is True
    assert manager.get_lock_pid() == os.getpid()
    manager.release_lock()
    assert not lock.exists()
    assert manager.lock_acquired is False


def test_pid_manager_removes_stale_or_invalid_locks(tmp_path, monkeypatch):
    lock = tmp_path / "crawler.pid"
    lock.write_text("not-a-pid")
    manager = pid_manager.PIDManager(str(lock))
    monkeypatch.setattr(pid_manager.sys, "platform", "linux")

    assert manager._is_running() is False
    assert not lock.exists()


def test_pid_manager_context_manager_and_existing_instance(tmp_path, monkeypatch):
    lock = tmp_path / "crawler.pid"
    monkeypatch.setattr(pid_manager.PIDManager, "_is_running", lambda self: False)
    with pid_manager.PIDManager(str(lock)) as manager:
        assert manager.lock_acquired is True
    assert not lock.exists()
    assert pid_manager.check_existing_instance(str(lock)) is False
