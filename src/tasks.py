"""
KrishiMandal — Background task functions.
Called via FastAPI BackgroundTasks.
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def refresh_price_data(crop: str):
    """Refresh price data for a crop — tries real fetcher first, falls back to random."""
    # Try real data fetcher chain
    try:
        from src.data_fetchers.mandi_prices import sync_mandi_prices_to_db
        count = sync_mandi_prices_to_db([crop], state="Maharashtra", days_back=3)
        if count > 0:
            logger.info("Refreshed %d real price records for %s", count, crop)
            return
    except Exception as e:
        logger.debug("Real price fetch unavailable for %s: %s", crop, e)

    # Fallback: generate synthetic prices
    from src.database import SessionLocal
    from src.db_models import PriceRecord
    from src.dummy_data import MAHARASHTRA_MANDIS

    db = SessionLocal()
    try:
        price_bases = {
            "wheat": 2425, "cotton": 7521, "soybean": 4892, "sugarcane": 3150,
            "jowar": 3180, "bajra": 2500, "tur": 7000, "gram": 5440,
            "onion": 1800, "grapes": 4500,
        }
        base = price_bases.get(crop, 2500)
        for mandi in random.sample(MAHARASHTRA_MANDIS, k=3):
            price = round(base * random.uniform(0.92, 1.10), 0)
            db.add(PriceRecord(crop=crop, mandi=mandi, price=price))
        db.commit()
        logger.info("Refreshed price data for %s (synthetic fallback)", crop)
    except Exception as e:
        logger.error("Price refresh failed for %s: %s", crop, e)
        db.rollback()
    finally:
        db.close()


def check_scheme_deadlines():
    """Check for upcoming scheme deadlines and log alerts."""
    from src.database import SessionLocal
    from src.db_models import Scheme

    db = SessionLocal()
    try:
        soon = date.today() + timedelta(days=30)
        schemes = db.query(Scheme).filter(
            Scheme.is_active == True,  # noqa: E712
            Scheme.deadline <= soon,
            Scheme.deadline >= date.today(),
        ).all()
        for s in schemes:
            days_left = (s.deadline - date.today()).days
            logger.info("SCHEME ALERT: %s deadline in %d days", s.name, days_left)
        return len(schemes)
    finally:
        db.close()


def update_farm_state(farm_id: str):
    """Refresh NDVI/weather data for a farm (simulated)."""
    from src.database import SessionLocal
    from src.repositories import save_farm_state

    db = SessionLocal()
    try:
        ndvi = round(random.uniform(0.45, 0.82), 2)
        moisture = round(random.uniform(25, 65), 1)
        health = round(random.uniform(60, 95), 1)
        save_farm_state(db, farm_id, ndvi, moisture, health)
        logger.info("Updated farm state for %s", farm_id)
    except Exception as e:
        logger.error("Farm state update failed for %s: %s", farm_id, e)
    finally:
        db.close()
