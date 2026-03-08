"""
KrishiMandal — Mandi Price Fetchers
Multi-source strategy with graceful fallback:
  1. CEDA Agri Market Data (Ashoka University cleaned Agmarknet)
  2. Agmarknet scraper (direct HTML scraping)
  3. CSV bulk import (offline backup from data.gov.in)
"""
from __future__ import annotations

import csv
import logging
import os
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from src.config import settings

logger = logging.getLogger(__name__)


# ── Shared types ─────────────────────────────────────────────────────────────

class PriceEntry:
    """Lightweight price record before DB insertion."""
    __slots__ = ("crop", "mandi", "price", "date", "state")

    def __init__(self, crop: str, mandi: str, price: float, date: date, state: str = "Maharashtra"):
        self.crop = crop
        self.mandi = mandi
        self.price = price
        self.date = date
        self.state = state

    def __repr__(self):
        return f"PriceEntry({self.crop}, {self.mandi}, ₹{self.price}, {self.date})"


# ── Crop name mappings (English ↔ Agmarknet commodity names) ─────────────────

CROP_TO_COMMODITY = {
    "wheat": "Wheat",
    "cotton": "Cotton",
    "soybean": "Soyabean",
    "sugarcane": "Sugarcane",
    "jowar": "Jowar(Sorghum)",
    "bajra": "Bajra(Pearl Millet)",
    "tur": "Arhar (Tur/Red Gram)(Whole)",
    "gram": "Bengal Gram(Gram)(Whole)",
    "onion": "Onion",
    "rice": "Rice",
    "grapes": "Grapes",
}

COMMODITY_TO_CROP = {v.lower(): k for k, v in CROP_TO_COMMODITY.items()}


# ── Abstract interface ───────────────────────────────────────────────────────

class PriceDataFetcher(ABC):
    """Interface for any price data source."""

    @abstractmethod
    def fetch_prices(
        self, crops: List[str], state: str = "Maharashtra", days_back: int = 7
    ) -> List[PriceEntry]:
        """Fetch price entries for given crops and state."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this data source is currently reachable."""
        ...


# ── Source 1: CEDA Agri Market Data ──────────────────────────────────────────

class CEDAPriceFetcher(PriceDataFetcher):
    """
    Fetches cleaned Agmarknet data from CEDA (Ashoka University).
    API: https://agmarknet.ceda.ashoka.edu.in
    """

    BASE_URL = settings.CEDA_API_BASE_URL

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.BASE_URL}/api/commodities", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def fetch_prices(
        self, crops: List[str], state: str = "Maharashtra", days_back: int = 7
    ) -> List[PriceEntry]:
        entries: List[PriceEntry] = []
        for crop in crops:
            commodity = CROP_TO_COMMODITY.get(crop, crop.title())
            try:
                params = {
                    "commodity": commodity,
                    "state": state,
                    "days": days_back,
                }
                r = requests.get(
                    f"{self.BASE_URL}/api/prices",
                    params=params,
                    timeout=10,
                )
                r.raise_for_status()
                data = r.json()
                for record in data.get("data", data if isinstance(data, list) else []):
                    try:
                        price = float(record.get("modal_price") or record.get("price", 0))
                        mandi = record.get("market") or record.get("mandi", "Unknown")
                        date_str = record.get("arrival_date") or record.get("date", "")
                        rec_date = _parse_date(date_str) if date_str else date.today()
                        if price > 0:
                            entries.append(PriceEntry(
                                crop=crop,
                                mandi=mandi,
                                price=price,
                                date=rec_date,
                                state=state,
                            ))
                    except (ValueError, KeyError) as e:
                        logger.debug("Skipping malformed CEDA record: %s", e)
                logger.info("CEDA: fetched %d prices for %s", len(entries), crop)
            except Exception as e:
                logger.warning("CEDA fetch failed for %s: %s", crop, e)
        return entries


# ── Source 2: Agmarknet Scraper ──────────────────────────────────────────────

class AgmarknetScraper(PriceDataFetcher):
    """
    Scrapes agmarknet.gov.in directly using BeautifulSoup.
    Fallback when CEDA API is unavailable.
    """

    BASE_URL = "https://agmarknet.gov.in/SearchCmmMkt.aspx"

    def is_available(self) -> bool:
        if not settings.AGMARKNET_SCRAPE_ENABLED:
            return False
        try:
            r = requests.get(self.BASE_URL, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def fetch_prices(
        self, crops: List[str], state: str = "Maharashtra", days_back: int = 7
    ) -> List[PriceEntry]:
        entries: List[PriceEntry] = []
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("beautifulsoup4 not installed — Agmarknet scraper unavailable")
            return entries

        for crop in crops:
            commodity = CROP_TO_COMMODITY.get(crop, crop.title())
            try:
                # Agmarknet uses ASP.NET ViewState; we do a simplified GET approach
                params = {
                    "Ession_id": "1",
                    "cmbCommodity": commodity,
                    "cmbState": state,
                    "cmbDistrict": "Select",
                    "cmbMarket": "Select",
                    "DateFrom": (
                        date.today().__format__("%d-%b-%Y")
                        if days_back <= 1
                        else _days_ago(days_back).strftime("%d-%b-%Y")
                    ),
                    "DateTo": date.today().strftime("%d-%b-%Y"),
                }
                r = requests.get(self.BASE_URL, params=params, timeout=15)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")

                table = soup.find("table", {"id": "cphBody_GridPriceData"})
                if not table:
                    logger.debug("No price table found on Agmarknet for %s", crop)
                    continue

                rows = table.find_all("tr")[1:]  # skip header
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 7:
                        try:
                            mandi = cells[1].get_text(strip=True)
                            modal_price = float(cells[5].get_text(strip=True).replace(",", ""))
                            date_str = cells[6].get_text(strip=True)
                            rec_date = _parse_date(date_str)
                            if modal_price > 0:
                                entries.append(PriceEntry(
                                    crop=crop,
                                    mandi=mandi,
                                    price=modal_price,
                                    date=rec_date,
                                    state=state,
                                ))
                        except (ValueError, IndexError):
                            continue

                logger.info("Agmarknet scraper: fetched %d prices for %s", len(entries), crop)
            except Exception as e:
                logger.warning("Agmarknet scrape failed for %s: %s", crop, e)

        return entries


# ── Source 3: CSV Import ─────────────────────────────────────────────────────

class CSVPriceImporter(PriceDataFetcher):
    """
    Imports from downloaded CSV files (e.g., from data.gov.in).
    Place CSV files in data/ directory.
    Expected columns: commodity, market, state, modal_price, arrival_date
    """

    CSV_DIR = Path("data")

    def is_available(self) -> bool:
        return any(self.CSV_DIR.glob("*prices*.csv")) if self.CSV_DIR.exists() else False

    def fetch_prices(
        self, crops: List[str], state: str = "Maharashtra", days_back: int = 30
    ) -> List[PriceEntry]:
        entries: List[PriceEntry] = []
        cutoff = _days_ago(days_back)

        csv_files = list(self.CSV_DIR.glob("*prices*.csv")) if self.CSV_DIR.exists() else []
        for csv_file in csv_files:
            try:
                with open(csv_file, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            commodity = (row.get("commodity") or row.get("Commodity") or "").strip()
                            crop_name = COMMODITY_TO_CROP.get(commodity.lower(), commodity.lower())
                            if crop_name not in crops:
                                continue

                            row_state = (row.get("state") or row.get("State") or "").strip()
                            if state and row_state.lower() != state.lower():
                                continue

                            price = float(
                                (row.get("modal_price") or row.get("Modal Price") or "0")
                                .replace(",", "")
                            )
                            mandi = (row.get("market") or row.get("Market") or "Unknown").strip()
                            date_str = row.get("arrival_date") or row.get("Arrival Date") or ""
                            rec_date = _parse_date(date_str) if date_str else date.today()

                            if price > 0 and rec_date >= cutoff:
                                entries.append(PriceEntry(
                                    crop=crop_name,
                                    mandi=mandi,
                                    price=price,
                                    date=rec_date,
                                    state=row_state or state,
                                ))
                        except (ValueError, KeyError):
                            continue
                logger.info("CSV import: loaded %d prices from %s", len(entries), csv_file.name)
            except Exception as e:
                logger.warning("CSV import failed for %s: %s", csv_file, e)

        return entries


# ── Factory & sync ───────────────────────────────────────────────────────────

_fetcher_cache: Optional[PriceDataFetcher] = None


def get_price_fetcher() -> PriceDataFetcher:
    """Return the best available price fetcher (with caching)."""
    global _fetcher_cache
    if _fetcher_cache is not None:
        return _fetcher_cache

    # Priority order
    fetchers = [CEDAPriceFetcher(), AgmarknetScraper(), CSVPriceImporter()]
    for fetcher in fetchers:
        try:
            if fetcher.is_available():
                logger.info("Using price fetcher: %s", fetcher.__class__.__name__)
                _fetcher_cache = fetcher
                return fetcher
        except Exception:
            continue

    # If nothing is available, return CSV importer (it will return empty list gracefully)
    logger.warning("No real price data source available — using CSV importer as stub")
    _fetcher_cache = CSVPriceImporter()
    return _fetcher_cache


def sync_mandi_prices_to_db(
    crops: List[str],
    state: str = "Maharashtra",
    days_back: int = 7,
) -> int:
    """
    Fetch prices from best available source and upsert into price_records table.
    Returns number of records inserted.
    """
    from src.database import SessionLocal
    from src.db_models import PriceRecord

    fetcher = get_price_fetcher()
    entries = fetcher.fetch_prices(crops, state, days_back)

    if not entries:
        logger.info("No new prices fetched — falling back to existing DB data")
        return 0

    db = SessionLocal()
    try:
        count = 0
        for e in entries:
            # Upsert: check if record already exists for same crop/mandi/date
            existing = (
                db.query(PriceRecord)
                .filter(
                    PriceRecord.crop == e.crop,
                    PriceRecord.mandi == e.mandi,
                )
                .order_by(PriceRecord.recorded_at.desc())
                .first()
            )
            # Only insert if no record for today or price differs
            if not existing or existing.recorded_at.date() != e.date:
                db.add(PriceRecord(
                    crop=e.crop,
                    mandi=e.mandi,
                    price=e.price,
                    recorded_at=datetime.combine(e.date, datetime.min.time()),
                ))
                count += 1

        db.commit()
        logger.info("Synced %d price records to DB", count)
        return count
    except Exception as e:
        logger.error("Price sync failed: %s", e)
        db.rollback()
        return 0
    finally:
        db.close()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_date(date_str: str) -> date:
    """Parse date from various formats used by Indian government data."""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


def _days_ago(n: int) -> date:
    from datetime import timedelta
    return date.today() - timedelta(days=n)
