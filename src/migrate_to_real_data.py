"""
KrishiMandal — Migration Script: Dummy → Real Data
One-time script to populate the database with real data.

Usage:
    python -m src.migrate_to_real_data
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-28s | %(levelname)-5s | %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


def _ensure_scheme_columns():
    """Add new columns to schemes table if they don't exist (SQLite ALTER TABLE)."""
    from src.database import engine
    from sqlalchemy import text, inspect

    insp = inspect(engine)
    existing_cols = {c["name"] for c in insp.get_columns("schemes")}

    new_cols = {
        "eligibility_json": "TEXT DEFAULT '{}'",
        "category": "VARCHAR(50) DEFAULT 'general'",
        "last_updated": "DATETIME",
    }

    with engine.begin() as conn:
        for col_name, col_def in new_cols.items():
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE schemes ADD COLUMN {col_name} {col_def}"))
                logger.info("Added column schemes.%s", col_name)


def migrate_schemes():
    """Update schemes table from real_schemes.json."""
    from src.database import SessionLocal
    from src.db_models import Scheme

    _ensure_scheme_columns()

    schemes_file = DATA_DIR / "real_schemes.json"
    if not schemes_file.exists():
        logger.warning("real_schemes.json not found — skipping scheme migration")
        return

    with open(schemes_file, "r", encoding="utf-8") as f:
        schemes_data = json.load(f)

    db = SessionLocal()
    try:
        # Delete existing schemes and re-insert
        db.query(Scheme).delete()
        db.commit()

        for s in schemes_data:
            deadline = None
            if s.get("deadline"):
                try:
                    deadline = date.fromisoformat(s["deadline"])
                except (ValueError, TypeError):
                    deadline = None

            scheme = Scheme(
                id=s["id"],
                name=s["name"],
                benefits_inr=s["benefits_inr"],
                deadline=deadline,
                requirements_json=json.dumps(s.get("requirements", [])),
                url=s.get("application_url", ""),
                description=s.get("description", ""),
                is_active=s.get("is_active", True),
                eligibility_json=json.dumps(s.get("eligibility", {})),
                category=s.get("category", "general"),
            )
            db.add(scheme)

        db.commit()
        logger.info("Migrated %d real schemes", len(schemes_data))
    except Exception as e:
        logger.error("Scheme migration failed: %s", e)
        db.rollback()
    finally:
        db.close()


def migrate_prices():
    """Fetch real mandi prices and replace dummy data."""
    from src.database import SessionLocal
    from src.db_models import PriceRecord
    from src.dummy_data import MAHARASHTRA_CROPS

    db = SessionLocal()
    try:
        # Try real fetcher first
        try:
            from src.data_fetchers.mandi_prices import sync_mandi_prices_to_db
            count = sync_mandi_prices_to_db(MAHARASHTRA_CROPS, state="Maharashtra", days_back=30)
            if count > 0:
                logger.info("Fetched %d real price records", count)
                return
        except Exception as e:
            logger.warning("Real price fetch failed: %s — keeping existing prices", e)

        # If real fetch failed and we have no prices, keep existing
        existing = db.query(PriceRecord).count()
        if existing > 0:
            logger.info("Keeping %d existing price records (real fetch unavailable)", existing)
        else:
            logger.warning("No price data available — run seed_db.py to generate synthetic prices")
    finally:
        db.close()


def migrate_weather():
    """Fetch current weather for all farms in DB."""
    from src.database import SessionLocal
    from src.db_models import Farm
    from src.models import GeoCoordinates
    from src.agents.digital_twin_agent import DigitalTwinAgent
    from src.repositories import save_farm_state

    dt = DigitalTwinAgent()
    db = SessionLocal()
    try:
        farms = db.query(Farm).all()
        if not farms:
            logger.info("No farms in DB — skipping weather migration")
            return

        updated = 0
        for farm in farms:
            try:
                location = GeoCoordinates(lat=farm.location_lat, lng=farm.location_lng)
                weather = dt.get_weather(location)
                save_farm_state(
                    db, farm.id,
                    ndvi=0.65,
                    moisture=45.0,
                    health=80.0,
                    weather_dict=weather.model_dump(),
                )
                updated += 1
            except Exception as e:
                logger.warning("Weather update failed for %s: %s", farm.id, e)

        logger.info("Updated weather for %d/%d farms", updated, len(farms))
    finally:
        db.close()


def migrate_knowledge():
    """Trigger re-ingestion of real knowledge documents into Pinecone."""
    knowledge_file = DATA_DIR / "real_knowledge.json"
    if not knowledge_file.exists():
        logger.warning("real_knowledge.json not found — skipping knowledge migration")
        return

    try:
        from src.ingest_knowledge import ingest_knowledge
        ingest_knowledge()
        logger.info("Knowledge ingestion complete")
    except Exception as e:
        logger.error("Knowledge ingestion failed: %s", e)


def main():
    from src.database import init_db
    init_db()

    print(f"\n{'='*60}")
    print(f"  KrishiMandal — Real Data Migration")
    print(f"{'='*60}\n")

    steps = [
        ("Schemes", migrate_schemes),
        ("Prices", migrate_prices),
        ("Weather", migrate_weather),
        ("Knowledge (Pinecone RAG)", migrate_knowledge),
    ]

    for name, func in steps:
        print(f"\n--- Migrating: {name} ---")
        try:
            func()
            print(f"  ✓ {name} migration complete")
        except Exception as e:
            print(f"  ✗ {name} migration failed: {e}")
            logger.error("%s migration error: %s", name, e, exc_info=True)

    print(f"\n{'='*60}")
    print(f"  Migration complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
