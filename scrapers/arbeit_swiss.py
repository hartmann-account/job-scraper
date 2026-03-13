"""
Scraper für Arbeit.swiss / job-room.ch
Nutzt die öffentliche REST-API (kein API-Key nötig).
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

API_URL = "https://www.job-room.ch/api/jobAdvertisements/_search"

# Kantons-Codes für Location-Filter
CANTON_MAP = {
    "zürich": "ZH",
    "zug": "ZG",
    "luzern": "LU",
    "basel": "BS",
    "bern": "BE",
    "genf": "GE",
}


def build_query(search_term: str, locations: List[str], profession_codes: List[str] = None) -> Dict[str, Any]:
    """Baut den POST-Body für die job-room.ch API."""
    # Letzter Monat als Zeitfenster
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    canton_codes = []
    for loc in locations:
        code = CANTON_MAP.get(loc.lower())
        if code:
            canton_codes.append(code)

    body = {
        "page": 0,
        "size": 100,
        "sort": "date",
        "body": {
            "keyword": search_term,
            "publicationDate": {
                "from": date_from
            }
        }
    }

    if canton_codes:
        body["body"]["cantons"] = canton_codes

    if profession_codes:
        body["body"]["professionCodes"] = profession_codes

    return body


def parse_result(item: Dict[str, Any]) -> Dict[str, str]:
    """Extrahiert relevante Felder aus einem API-Ergebnis."""
    job_content = item.get("jobContent", {})
    job_desc = job_content.get("jobDescriptions", [{}])
    title = job_desc[0].get("title", "N/A") if job_desc else "N/A"

    company = job_content.get("company", {})
    company_name = company.get("name", "N/A")

    location = job_content.get("location", {})
    city = location.get("city", "")
    canton = location.get("cantonCode", "")
    location_str = f"{city}, {canton}".strip(", ")

    employment = job_content.get("employment", {})
    workload_from = employment.get("workloadPercentageFrom", "")
    workload_to = employment.get("workloadPercentageTo", "")
    workload = f"{workload_from}-{workload_to}%" if workload_from else "N/A"

    pub_date = item.get("publicationDate", "N/A")
    job_id = item.get("id", "")
    url = f"https://www.job-room.ch/job/{job_id}" if job_id else "N/A"

    return {
        "source": "arbeit.swiss",
        "title": title,
        "company": company_name,
        "location": location_str,
        "workload": workload,
        "published": pub_date,
        "url": url,
        "scraped_at": datetime.now().isoformat()
    }


def scrape(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Hauptfunktion: Scrapet Arbeit.swiss für alle Suchbegriffe."""
    arbeit_config = config.get("arbeit_swiss", {})
    if not arbeit_config.get("enabled", False):
        logger.info("Arbeit.swiss scraper deaktiviert.")
        return []

    search_terms = config.get("search_terms", [])
    locations = config.get("locations", [])
    profession_codes = arbeit_config.get("profession_codes", [])

    all_results = []
    seen_ids = set()

    for term in search_terms:
        logger.info(f"Arbeit.swiss: Suche nach '{term}'...")
        query = build_query(term, locations, profession_codes)

        try:
            resp = requests.post(API_URL, json=query, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0)",
                "Content-Type": "application/json"
            })
            resp.raise_for_status()
            data = resp.json()

            results = data.get("content", []) if isinstance(data, dict) else []
            for item in results:
                job_id = item.get("id", "")
                if job_id and job_id not in seen_ids:
                    seen_ids.add(job_id)
                    parsed = parse_result(item)
                    all_results.append(parsed)

            logger.info(f"  → {len(results)} Ergebnisse (Duplikate gefiltert)")

        except requests.RequestException as e:
            logger.error(f"  Fehler bei Suche '{term}': {e}")

    logger.info(f"Arbeit.swiss: Total {len(all_results)} unique Jobs gefunden.")
    return all_results
