"""PID file manager for preventing concurrent crawler execution."""

import os
import sys
import subprocess
from typing import Optional
import tempfile
import time

from utils.logging_setup import get_logger


class PIDManager:
    """Manage PID file to prevent concurrent crawler execution."""

    def __init__(self, pid_file: Optional[str] = None, lock_timeout: int = 3600):
        """
        Initialize PID manager.

        Args:
            pid_file: Path to PID file. If None, uses default path based on OS
            lock_timeout: Lock timeout in seconds (default: 1 hour)
        """
        self.lock_timeout = lock_timeout
        self.logger = get_logger('PIDManager')
        self.lock_acquired = False

        # Set default PID file path based on OS
        if pid_file is None:
            if sys.platform == 'win32':
                # Windows
                pid_file = os.path.join(tempfile.gettempdir(), 'crawler.pid')
            else:
                # Unix-like
                pid_file = '/tmp/crawler.pid'

        self.pid_file = pid_file

    def acquire_lock(self) -> bool:
        """
        Acquire exclusive lock to prevent concurrent execution.

        Returns:
            True if lock acquired, False if another instance is running
        """
        try:
            # Check if another instance is already running
            if self._is_running():
                self.logger.warning(f"Another crawler instance is already running (PID file: {self.pid_file})")
                return False

            # Create PID directory if needed
            pid_dir = os.path.dirname(self.pid_file)
            if pid_dir and not os.path.exists(pid_dir):
                os.makedirs(pid_dir)

            # Write current PID to file
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
                f.flush()

            self.lock_acquired = True
            self.logger.info(f"Acquired lock at {self.pid_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error acquiring lock: {e}")
            return False

    def release_lock(self):
        """Release lock and clean up PID file."""
        try:
            # Remove PID file
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                self.logger.info(f"Removed PID file: {self.pid_file}")

            self.lock_acquired = False

        except Exception as e:
            self.logger.warning(f"Error releasing lock: {e}")

    def _is_running(self) -> bool:
        """
        Check if another instance is already running.

        Returns:
            True if another instance is running, False otherwise
        """
        try:
            if not os.path.exists(self.pid_file):
                return False

            # Read PID from file
            with open(self.pid_file, 'r') as f:
                pid_str = f.read().strip()

            if not pid_str:
                return False

            # Check if process with that PID is still running
            try:
                pid = int(pid_str)

                if sys.platform == 'win32':
                    # Windows: Use tasklist to check if process exists
                    result = subprocess.run(
                        ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                        capture_output=True,
                        text=True
                    )
                    return str(pid) in result.stdout
                else:
                    # Unix-like: Send signal 0 to check if process exists
                    os.kill(pid, 0)
                    return True  # Process is still running

            except (OSError, ValueError, subprocess.SubprocessError):
                # Process doesn't exist
                # Clean up stale PID file
                self._remove_stale_lock()
                return False

        except Exception as e:
            self.logger.error(f"Error checking if process is running: {e}")
            return False

    def _remove_stale_lock(self):
        """Remove stale PID file."""
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                self.logger.info(f"Removed stale PID file: {self.pid_file}")
        except Exception as e:
            self.logger.error(f"Error removing stale lock: {e}")

    def get_lock_pid(self) -> Optional[int]:
        """
        Get PID of process holding the lock.

        Returns:
            PID if available, None otherwise
        """
        try:
            if not os.path.exists(self.pid_file):
                return None

            with open(self.pid_file, 'r') as f:
                pid_str = f.read().strip()
            if pid_str:
                return int(pid_str)
        except Exception as e:
            self.logger.error(f"Error reading lock PID: {e}")

        return None

    def __enter__(self):
        """Context manager entry."""
        if not self.acquire_lock():
            raise RuntimeError(f"Another crawler instance is already running (PID file: {self.pid_file})")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release_lock()


def check_existing_instance(pid_file: Optional[str] = None) -> bool:
    """
    Check if another crawler instance is already running.

    Args:
        pid_file: Path to PID file

    Returns:
        True if another instance is running, False otherwise
    """
    manager = PIDManager(pid_file=pid_file)
    return manager._is_running()
