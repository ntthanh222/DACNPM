"""
Crawler Scheduler using APScheduler

Lên lịch chạy crawler tự động mỗi 4 tiếng để thu thập tin tức bảo mật.
Chạy ngầm như background process mà không ảnh hưởng đến performance của FastAPI.
"""
import logging
import subprocess
import os
import sys
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """
    Get or create global scheduler instance.

    Returns:
        AsyncIOScheduler: Global scheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            timezone='Asia/Ho_Chi_Minh',
            job_defaults={
                'coalesce': True,  # Gộp các job bị miss thành 1
                'max_instances': 1,  # Chỉ chạy 1 instance tại 1 thời điểm
                'misfire_grace_time': 3600  # Cho phép chạy lại nếu miss trong 1h
            }
        )
    return _scheduler


def schedule_crawler_job(
    hour_interval: int = 4,
    headless: bool = True,
    max_articles: int = 10
) -> bool:
    """
    Lên lịch chạy crawler định kỳ.

    Args:
        hour_interval: Khoảng thời gian chạy (giờ) - default 4 tiếng
        headless: Chạy browser ở chế độ headless (không hiển thị GUI)
        max_articles: Số bài viết tối đa mỗi lần chạy

    Returns:
        bool: True nếu thành công, False nếu fail
    """
    try:
        scheduler = get_scheduler()

        # Build command to run crawler
        script_path = os.path.join(
            os.path.dirname(__file__),
            '..', 'scripts', 'crawl_security_news.py'
        )

        cmd = [
            sys.executable,
            script_path,
            '--headless' if headless else '',
            '--articles', str(max_articles)
        ]

        # Remove empty strings
        cmd = [c for c in cmd if c]

        def crawl_job():
            """Job function to run crawler"""
            try:
                logger.info(f"🔄 Starting scheduled crawler job at {datetime.now()}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes timeout
                )

                if result.returncode == 0:
                    # Check if crawler ran in test mode (database unavailable)
                    output = result.stdout.lower() if result.stdout else ""
                    if "test mode" in output or "database unavailable" in output or "⚠️ database" in output:
                        logger.warning(f"⚠️ Crawler ran in test mode - no articles saved to database")
                        if result.stdout:
                            logger.debug(f"Crawler output: {result.stdout[-500:]}")
                    else:
                        logger.info(f"✅ Crawler job completed successfully")
                        if result.stdout:
                            logger.debug(f"Crawler output: {result.stdout[-500:]}")
                else:
                    logger.warning(f"⚠️ Crawler job failed with code {result.returncode}")
                    if result.stderr:
                        logger.error(f"Crawler error: {result.stderr}")

            except subprocess.TimeoutExpired:
                logger.error("❌ Crawler job timed out after 10 minutes")
            except Exception as e:
                logger.error(f"❌ Crawler job error: {e}")

        # Schedule job using cron-like syntax
        # Chạy mỗi 4 tiếng: 0, 4, 8, 12, 16, 20, 24
        try:
            scheduler.add_job(
                crawl_job,
                trigger=CronTrigger(hour=f'*/{hour_interval}'),
                id='security_news_crawler',
                name='Security News Crawler',
                replace_existing=True
            )

            logger.info(f"✅ Scheduled crawler job to run every {hour_interval} hours")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add job to scheduler: {e}")
            return False

    except Exception as e:
        logger.error(f"❌ Failed to schedule crawler job: {e}")
        return False


def start_scheduler():
    """Khởi động scheduler nên được gọi khi FastAPI start."""
    try:
        scheduler = get_scheduler()

        # Add crawler job if not already scheduled
        if not scheduler.get_job('security_news_crawler'):
            schedule_crawler_job()

        # Start scheduler
        if not scheduler.running:
            scheduler.start()
            logger.info("✅ Crawler scheduler started")

    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")


def stop_scheduler():
    """Dừng scheduler nên được gọi khi FastAPI shutdown."""
    try:
        scheduler = get_scheduler()
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("⏹️ Crawler scheduler stopped")
    except Exception as e:
        logger.error(f"❌ Failed to stop scheduler: {e}")


def get_scheduler_status() -> dict:
    """
    Lấy trạng thái scheduler cho monitoring.

    Returns:
        dict: Status info including running state, next run time, etc.
    """
    scheduler = get_scheduler()
    job = scheduler.get_job('security_news_crawler')

    return {
        'scheduler_running': scheduler.running,
        'job_scheduled': job is not None,
        'next_run_time': job.next_run_time.isoformat() if job else None,
        'timezone': 'Asia/Ho_Chi_Minh'
    }


# Manual trigger for testing/execution
def trigger_crawler_now(max_articles: int = 10) -> dict:
    """
    Trigger crawler ngay lập tức (manual).

    Args:
        max_articles: Số bài viết tối đa

    Returns:
        dict: Result info
    """
    try:
        script_path = os.path.join(
            os.path.dirname(__file__),
            '..', 'scripts', 'crawl_security_news.py'
        )

        cmd = [
            sys.executable,
            script_path,
            '--headless',
            '--articles', str(max_articles)
        ]

        logger.info(f"🔄 Manually triggering crawler at {datetime.now()}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }

    except Exception as e:
        logger.error(f"❌ Manual crawler trigger failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
