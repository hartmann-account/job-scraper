"""
Scraper für LinkedIn (öffentliche Guest-API).
Kein Login nötig — nutzt die öffentliche Job-Suche.

HINWEIS: LinkedIn kann diese Schnittstelle jederzeit ändern oder blockieren.
Fallback: RSS-Feed oder manuelle Überprüfung.
"""

import requests
import logging
import time
import random
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def build_url(keyword: str, geo_id: str, time_filter: str, start: int = 0) -> str:
    """Baut die LinkedIn Guest-API URL."""
    encoded_kw = quote(keyword)
    return (
        f"{BASE_URL}"
        f"?keywords={encoded_kw}"
        f"&location=Switzerland"
        f"&geoId={geo_id}"
        f"&f_TPR={time_filter}"
        f"&start={start}"
    )


def parse_html_results(html: str) -> List[Dict[str, str]]:
    """Parst die LinkedIn HTML-Antwort (kein JSON, sondern HTML-Fragmente)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    cards = soup.find_all("div", class_="base-card")
    if not cards:
        # Alternativer Selektor
        cards = soup.find_all("li")

    for card in cards:
        title_el = card.find("h3", class_="base-search-card__title")
        company_el = card.find("h4", class_="base-search-card__subtitle")
        location_el = card.find("span", class_="job-search-card__location")
        link_el = card.find("a", class_="base-card__full-link")
        date_el = card.find("time")

        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        company = company_el.get_text(strip=True) if company_el else "N/A"
        location = location_el.get_text(strip=True) if location_el else "N/A"
        url = link_el["href"].split("?")[0] if link_el and link_el.get("href") else "N/A"
        pub_date = date_el.get("datetime", "N/A") if date_el else "N/A"

        jobs.append({
            "source": "LinkedIn",
            "title": title,
            "company": company,
            "location": location,
            "workload": "N/A",
            "published": pub_date,
            "url": url,
            "scraped_at": datetime.now().isoformat()
        })

    return jobs


def scrape(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Hauptfunktion: Scrapet LinkedIn öffentliche Job-Listings."""
    linkedin_config = config.get("linkedin", {})
    if not linkedin_config.get("enabled", False):
        logger.info("LinkedIn scraper deaktiviert.")
        return []

    search_terms = config.get("search_terms", [])
    geo_id = linkedin_config.get("geo_id", "106693272")
    time_filter = linkedin_config.get("time_filter", "r2592000")

    all_results = []
    seen_urls = set()

    for term in search_terms:
        # Kombiniere mit Branchen-Keywords
        for sector in ["Bank", "Kantonalbank", "Asset Management", "Private Banking"]:
            query = f"{term} {sector}"
            logger.info(f"LinkedIn: Suche nach '{query}'...")

            url = build_url(query, geo_id, time_filter)

            try:
                # Rate limiting — LinkedIn blockt bei zu vielen Requests
                time.sleep(random.uniform(2, 5))

                resp = requests.get(url, headers=HEADERS, timeout=30)

                if resp.status_code == 429:
                    logger.warning("LinkedIn: Rate limit erreicht, pausiere 60s...")
                    time.sleep(60)
                    resp = requests.get(url, headers=HEADERS, timeout=30)

                if resp.status_code != 200:
                    logger.warning(f"LinkedIn: HTTP {resp.status_code} für '{query}'")
                    continue

                jobs = parse_html_results(resp.text)

                for job in jobs:
                    if job["url"] not in seen_urls:
                        seen_urls.add(job["url"])
                        all_results.append(job)

                logger.info(f"  → {len(jobs)} Ergebnisse")

            except requests.RequestException as e:
                logger.error(f"  Fehler bei '{query}': {e}")

    logger.info(f"LinkedIn: Total {len(all_results)} unique Jobs gefunden.")
    return all_results
