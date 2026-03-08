"""
KrishiMandal — Background Scheduler
Periodic data refresh using APScheduler.
"""
from __future__ import annotations

import logging

from src.config import settings

logger = logging.getLogger(__name__)

_scheduler = None


def start_scheduler():
    """Start the background scheduler with all refresh jobs."""
    global _scheduler

    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled (SCHEDULER_ENABLED=false)")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning("apscheduler not installed — scheduler disabled. pip install apscheduler>=3.10.0")
        return

    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Job 1: Refresh mandi prices daily at 6 AM IST
    _scheduler.add_job(
        _refresh_all_prices,
        CronTrigger(hour=6, minute=0),
        id="refresh_prices",
        name="Daily mandi price refresh",
        replace_existing=True,
    )

    # Job 2: Check scheme deadlines daily at 8 AM IST
    _scheduler.add_job(
        _check_scheme_deadlines,
        CronTrigger(hour=8, minute=0),
        id="check_schemes",
        name="Daily scheme deadline check",
        replace_existing=True,
    )

    # Job 3: Refresh weather every 3 hours for all farms
    _scheduler.add_job(
        _refresh_weather,
        IntervalTrigger(hours=3),
        id="refresh_weather",
        name="Weather refresh (3-hourly)",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Background scheduler started with %d jobs", len(_scheduler.get_jobs()))


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
        _scheduler = None


def _refresh_all_prices():
    """Fetch real prices for all tracked crops."""
    from src.dummy_data import MAHARASHTRA_CROPS

    logger.info("Scheduled: refreshing mandi prices for all crops")
    try:
        from src.data_fetchers.mandi_prices import sync_mandi_prices_to_db
        count = sync_mandi_prices_to_db(MAHARASHTRA_CROPS, state="Maharashtra", days_back=3)
        logger.info("Scheduled price refresh complete: %d records synced", count)
    except Exception as e:
        logger.error("Scheduled price refresh failed: %s", e)
        # Fallback to random price generation
        from src.tasks import refresh_price_data
        for crop in MAHARASHTRA_CROPS[:5]:
            refresh_price_data(crop)


def _check_scheme_deadlines():
    """Check and log upcoming scheme deadlines."""
    logger.info("Scheduled: checking scheme deadlines")
    try:
        from src.tasks import check_scheme_deadlines
        count = check_scheme_deadlines()
        logger.info("Scheduled scheme check: %d schemes with upcoming deadlines", count)
    except Exception as e:
        logger.error("Scheduled scheme check failed: %s", e)


def _refresh_weather():
    """Refresh weather data for all farms in the database."""
    logger.info("Scheduled: refreshing weather for all farms")
    try:
        from src.database import SessionLocal
        from src.db_models import Farm
        from src.models import GeoCoordinates
        from src.agents.digital_twin_agent import DigitalTwinAgent
        from src.repositories import save_farm_state

        dt = DigitalTwinAgent()
        db = SessionLocal()
        try:
            farms = db.query(Farm).all()
            for farm in farms:
                try:
                    location = GeoCoordinates(lat=farm.location_lat, lng=farm.location_lng)
                    weather = dt.get_weather(location)
                    save_farm_state(
                        db, farm.id,
                        ndvi=0.65,  # Would come from satellite data
                        moisture=45.0,  # Would come from IoT sensors
                        health=80.0,
                        weather_dict=weather.model_dump(),
                    )
                except Exception as e:
                    logger.warning("Weather refresh failed for %s: %s", farm.id, e)
            logger.info("Weather refresh complete for %d farms", len(farms))
        finally:
            db.close()
    except Exception as e:
        logger.error("Scheduled weather refresh failed: %s", e)
