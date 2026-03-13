"""
Generischer Scraper für Unternehmens-Karriereseiten.
Konfigurierbar über config.yaml — pro Unternehmen individuelle CSS-Selektoren.

HINWEIS: Karriereseiten ändern ihr Layout regelmässig.
Wenn ein Scraper bricht, müssen die Selektoren in config.yaml angepasst werden.
"""

import requests
import logging
import time
import random
from datetime import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-CH,de;q=0.9,en;q=0.5",
}


def scrape_single_company(company: Dict[str, Any], search_terms: List[str]) -> List[Dict[str, str]]:
    """Scrapet eine einzelne Karriereseite."""
    name = company.get("name", "Unknown")
    url = company.get("url", "")
    selectors = company.get("selectors", {})

    if not url:
        logger.warning(f"  {name}: Keine URL konfiguriert, übersprungen.")
        return []

    logger.info(f"  Lade {name}: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"  {name}: Laden fehlgeschlagen — {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Finde Job-Einträge via konfiguriertem Selektor
    job_list_selector = selectors.get("job_list", ".job-item")
    title_selector = selectors.get("title", ".job-title")
    location_selector = selectors.get("location", ".job-location")
    link_selector = selectors.get("link", "a")

    job_elements = soup.select(job_list_selector)

    if not job_elements:
        # Fallback: Suche nach generischen Patterns
        logger.warning(f"  {name}: Keine Elemente mit '{job_list_selector}' gefunden. "
                       f"Versuche Fallback-Selektoren...")
        for fallback in [".job-listing", ".vacancy", ".position", "[class*='job']", "tr[data-job]"]:
            job_elements = soup.select(fallback)
            if job_elements:
                logger.info(f"  {name}: Fallback '{fallback}' hat {len(job_elements)} Elemente gefunden.")
                break

    if not job_elements:
        logger.warning(f"  {name}: Keine Jobs gefunden. Selektoren prüfen!")
        return []

    jobs = []
    search_terms_lower = [t.lower() for t in search_terms]

    for el in job_elements:
        title_el = el.select_one(title_selector)
        loc_el = el.select_one(location_selector)
        link_el = el.select_one(link_selector)

        if not title_el:
            # Versuche den gesamten Text als Titel
            title = el.get_text(strip=True)[:120]
        else:
            title = title_el.get_text(strip=True)

        location = loc_el.get_text(strip=True) if loc_el else "N/A"

        job_url = "N/A"
        if link_el and link_el.get("href"):
            job_url = urljoin(url, link_el["href"])

        # Relevanz-Filter: Nur Jobs, die zu den Suchbegriffen passen
        title_lower = title.lower()
        is_relevant = any(term in title_lower for term in search_terms_lower)

        if is_relevant or not search_terms:
            jobs.append({
                "source": f"Karriereseite: {name}",
                "title": title,
                "company": name,
                "location": location,
                "workload": "N/A",
                "published": "N/A",
                "url": job_url,
                "scraped_at": datetime.now().isoformat()
            })

    logger.info(f"  {name}: {len(jobs)} relevante Jobs gefunden.")
    return jobs


def scrape(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Hauptfunktion: Iteriert über alle konfigurierten Karriereseiten."""
    career_config = config.get("career_pages", {})
    if not career_config.get("enabled", False):
        logger.info("Karriereseiten-Scraper deaktiviert.")
        return []

    companies = career_config.get("companies", [])
    search_terms = config.get("search_terms", [])

    if not companies:
        logger.info("Keine Unternehmen konfiguriert.")
        return []

    logger.info(f"Karriereseiten: {len(companies)} Unternehmen konfiguriert.")

    all_results = []
    for company in companies:
        results = scrape_single_company(company, search_terms)
        all_results.extend(results)
        # Pause zwischen Anfragen
        time.sleep(random.uniform(1, 3))

    logger.info(f"Karriereseiten: Total {len(all_results)} Jobs gefunden.")
    return all_results
