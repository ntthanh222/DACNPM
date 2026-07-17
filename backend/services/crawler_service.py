"""
Standalone Crawler Service for CyberSec Assistant

Runs as independent FastAPI service on port 8002.
Provides scheduled and manual crawling of security news.
"""
import logging
import subprocess
import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
CRAWLER_PORT = int(os.getenv("CRAWLER_PORT", "8002"))


@asynccontextmanager
async def crawler_lifespan(app: FastAPI):
    """Manage crawler startup and shutdown via lifespan events."""
    # Startup
    try:
        scheduler = get_scheduler()
        if not scheduler.get_job('security_news_crawler'):
            schedule_crawler_job(hour_interval=4, max_articles=10)
        if not scheduler.running:
            scheduler.start()
            logger.info("✅ Crawler service started on port %s", CRAWLER_PORT)
    except Exception as e:
        logger.error("❌ Failed to start crawler service: %s", e)
    yield
    # Shutdown
    try:
        scheduler = get_scheduler()
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("⏹️ Crawler service stopped")
    except Exception as e:
        logger.error("❌ Failed to stop crawler service: %s", e)


# Initialize FastAPI app
crawler_app = FastAPI(
    title="Crawler Service",
    description="Standalone crawler service for security news aggregation",
    version="1.0.0",
    lifespan=crawler_lifespan
)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            timezone='Asia/Ho_Chi_Minh',
            job_defaults={
                'coalesce': True,  # Merge missed jobs into one
                'max_instances': 1,  # Only run 1 instance at a time
                'misfire_grace_time': 3600  # Allow retry within 1h if missed
            }
        )
    return _scheduler


def run_crawler_job(max_articles: int = 10) -> dict:
    """
    Execute crawler job and return results.

    Args:
        max_articles: Maximum number of articles to crawl

    Returns:
        dict: Job execution results
    """
    try:
        # Path to crawler script
        script_path = os.path.join(
            os.path.dirname(__file__),
            '..', 'scripts', 'crawl_security_news.py'
        )

        if not os.path.exists(script_path):
            logger.error(f"Crawler script not found: {script_path}")
            return {
                'success': False,
                'error': f'Crawler script not found: {script_path}'
            }

        cmd = [
            sys.executable,
            script_path,
            '--headless',
            '--articles', str(max_articles)
        ]

        logger.info(f"🔄 Starting crawler job at {datetime.now()}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )

        # Check result
        if result.returncode == 0:
            # Check if crawler ran in test mode
            output = result.stdout.lower() if result.stdout else ""
            if "test mode" in output or "database unavailable" in output or "⚠️ database" in output:
                logger.warning("⚠️ Crawler ran in test mode - no articles saved to database")
                return {
                    'success': True,
                    'mode': 'test',
                    'message': 'Crawler ran in test mode (database unavailable)',
                    'stdout': result.stdout[-500:] if result.stdout else '',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.info("✅ Crawler job completed successfully")
                return {
                    'success': True,
                    'mode': 'normal',
                    'message': 'Crawler completed successfully',
                    'stdout': result.stdout[-500:] if result.stdout else '',
                    'timestamp': datetime.now().isoformat()
                }
        else:
            logger.warning(f"⚠️ Crawler job failed with code {result.returncode}")
            return {
                'success': False,
                'error': f'Crawler failed with return code {result.returncode}',
                'stderr': result.stderr if result.stderr else '',
                'timestamp': datetime.now().isoformat()
            }

    except subprocess.TimeoutExpired:
        logger.error("❌ Crawler job timed out after 10 minutes")
        return {
            'success': False,
            'error': 'Crawler job timed out after 10 minutes',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Crawler job error: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def schedule_crawler_job(
    hour_interval: int = 4,
    max_articles: int = 10
) -> bool:
    """
    Schedule periodic crawler job.

    Args:
        hour_interval: Interval in hours (default: 4 hours)
        max_articles: Maximum articles per run

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        scheduler = get_scheduler()

        # Remove existing job if any
        if scheduler.get_job('security_news_crawler'):
            scheduler.remove_job('security_news_crawler')

        # Create job function
        def job_wrapper():
            result = run_crawler_job(max_articles)
            logger.info(f"Job result: {result.get('message', 'Unknown')}")

        # Schedule job
        scheduler.add_job(
            job_wrapper,
            trigger=CronTrigger(hour=f'*/{hour_interval}'),
            id='security_news_crawler',
            name='Security News Crawler',
            replace_existing=True
        )

        logger.info(f"✅ Scheduled crawler job to run every {hour_interval} hours")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to schedule crawler job: {e}")
        return False


# ============================================================================
# API Endpoints
# ============================================================================

@crawler_app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    scheduler = get_scheduler()
    job = scheduler.get_job('security_news_crawler')

    return {
        'status': 'healthy',
        'service': 'crawler_service',
        'scheduler_running': scheduler.running,
        'job_scheduled': job is not None,
        'next_run_time': job.next_run_time.isoformat() if job else None,
        'timestamp': datetime.now().isoformat()
    }


@crawler_app.post("/crawl")
async def trigger_crawler(
    background_tasks: BackgroundTasks,
    max_articles: int = 10
):
    """
    Manually trigger crawler job.

    Args:
        background_tasks: FastAPI background tasks
        max_articles: Maximum articles to crawl (default: 10)

    Returns:
        JSON response with job status
    """
    # Run crawler in background
    background_tasks.add_task(run_crawler_job, max_articles)

    return {
        'message': 'Crawler job started in background',
        'max_articles': max_articles,
        'timestamp': datetime.now().isoformat()
    }


@crawler_app.get("/status")
async def get_status():
    """Get crawler service status."""
    scheduler = get_scheduler()
    job = scheduler.get_job('security_news_crawler')

    return {
        'scheduler_running': scheduler.running,
        'job_scheduled': job is not None,
        'next_run_time': job.next_run_time.isoformat() if job else None,
        'timezone': 'Asia/Ho_Chi_Minh',
        'service_port': CRAWLER_PORT,
        'timestamp': datetime.now().isoformat()
    }


@crawler_app.post("/schedule")
async def setup_schedule(
    hour_interval: int = 4,
    max_articles: int = 10
):
    """
    Setup or update crawler schedule.

    Args:
        hour_interval: Hours between runs (default: 4)
        max_articles: Max articles per run (default: 10)

    Returns:
        JSON response with schedule status
    """
    success = schedule_crawler_job(hour_interval, max_articles)

    if success:
        return {
            'message': f'Crawler scheduled to run every {hour_interval} hours',
            'hour_interval': hour_interval,
            'max_articles': max_articles,
            'timestamp': datetime.now().isoformat()
        }
    else:
        raise HTTPException(
            status_code=500,
            detail='Failed to schedule crawler job'
        )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    logger.info("🚀 Starting Crawler Service on port %s...", CRAWLER_PORT)
    uvicorn.run(
        "crawler_service:crawler_app",
        host="0.0.0.0",
        port=CRAWLER_PORT,
        reload=False  # Don't reload in production
    )
