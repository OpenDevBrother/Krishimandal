"""
KrishiMandal — Knowledge Scraper (Optional)
Scrapes Vikaspedia and other agricultural portals for knowledge refresh.
Not required for core operation — real_knowledge.json is the primary source.
"""
from __future__ import annotations

import logging
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


def fetch_vikaspedia_articles(topics: List[str]) -> List[Dict[str, str]]:
    """
    Scrape Vikaspedia agriculture pages for given topics.
    Returns list of {topic, source, text, url, language} dicts.
    """
    articles: List[Dict[str, str]] = []

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("beautifulsoup4 not installed — Vikaspedia scraper unavailable")
        return articles

    base_url = "https://vikaspedia.in/agriculture"

    topic_paths = {
        "pest_management": "/crop-production/integrated-pest-managment",
        "organic_farming": "/crop-production/organic-farming",
        "irrigation": "/crop-production/crop-water-management",
        "soil_health": "/soil",
        "government_schemes": "/policies-and-schemes",
        "crop_insurance": "/policies-and-schemes/crops-related",
        "market_information": "/market-information",
    }

    for topic in topics:
        path = topic_paths.get(topic)
        if not path:
            logger.debug("No Vikaspedia path for topic: %s", topic)
            continue

        url = f"{base_url}{path}"
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "KrishiMandal/1.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            # Extract main content
            content_div = soup.find("div", {"id": "content-area"}) or soup.find("div", {"class": "field-items"})
            if not content_div:
                continue

            # Get text, clean up
            text = content_div.get_text(separator=" ", strip=True)
            # Truncate to reasonable length
            text = text[:3000] if len(text) > 3000 else text

            if len(text) > 100:  # Only keep substantial content
                articles.append({
                    "topic": topic,
                    "source": f"Vikaspedia - {topic.replace('_', ' ').title()}",
                    "text": text,
                    "url": url,
                    "language": "en",
                })
                logger.info("Scraped Vikaspedia article for: %s (%d chars)", topic, len(text))

        except Exception as e:
            logger.warning("Failed to scrape Vikaspedia for %s: %s", topic, e)

    return articles
