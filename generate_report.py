#!/usr/bin/env python3
"""
Report-Generator — Monatlicher Job-Markt Report
=================================================
Liest die CSV aus output/ und erstellt einen Markdown-Report.
Optionaler Vormonatsvergleich, wenn eine ältere CSV vorhanden ist.

Ausführung:
    python generate_report.py
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("output")
FIELDNAMES = ["source", "title", "company", "location", "workload", "published", "url", "scraped_at"]

# Rollen-Kategorien mit Schlüsselwörtern
ROLE_CATEGORIES = {
    "Compliance / AML / KYC": [
        "compliance", "aml", "anti-money", "kyc", "know your customer",
        "financial crime", "geldwäsche", "regulatory", "fincrime",
    ],
    "Forensic / Investigations": [
        "forensic", "investigation", "fraud", "integrity", "whistleblow",
    ],
    "Relationship Management / Client Advisory": [
        "relationship manager", "client advisor", "kundenberater",
        "wealth advisor", "private banker", "client service",
    ],
    "Portfolio Management / Investment": [
        "portfolio", "investment", "asset management", "fund manager",
        "anlage", "vermögensverwaltung",
    ],
    "Risk / Audit": [
        "risk", "audit", "internal control", "risiko", "prüf",
    ],
    "Operations / IT": [
        "operations", "it ", "developer", "engineer", "devops", "data",
        "infrastructure", "system", "software", "cloud", "cyber",
    ],
}

# Profil-Keywords für Highlights
PROFILE_KEYWORDS = [
    "forensic", "investigation", "advisory", "consulting", "family office",
    "aml", "kyc", "compliance", "sap", "transformation", "finance",
    "due diligence", "fraud",
]

SENIOR_KEYWORDS = [
    "director", "head of", "vice president", "vp", "managing director",
    "principal", "partner", "chief", "leiter", "lead",
]

PRESTIGE_EMPLOYERS = [
    "ubs", "credit suisse", "julius bär", "julius baer", "lombard odier",
    "pictet", "vontobel", "zkb", "zürcher kantonalbank", "swiss re",
    "zurich insurance", "partners group", "ey", "deloitte", "kpmg", "pwc",
    "mckinsey", "bcg", "bain", "rothschild", "lazard",
]


def load_csv(filepath: Path) -> list[dict]:
    """Lädt eine CSV-Datei (Semikolon-separiert, UTF-8-BOM)."""
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            rows.append(row)
    return rows


def find_csvs() -> tuple[Path | None, Path | None]:
    """Findet aktuelle und Vormonats-CSV im Output-Ordner."""
    csvs = sorted(OUTPUT_DIR.glob("job_scrape_*.csv"))
    if not csvs:
        return None, None
    current = csvs[-1]
    previous = csvs[-2] if len(csvs) >= 2 else None
    return current, previous


def categorize_role(title: str) -> str:
    """Ordnet einen Stellentitel einer Kategorie zu."""
    title_lower = title.lower()
    for category, keywords in ROLE_CATEGORIES.items():
        if any(kw in title_lower for kw in keywords):
            return category
    return "Andere"


def pct(count: int, total: int) -> str:
    """Prozentwert formatiert."""
    if total == 0:
        return "0.0"
    return f"{count / total * 100:.1f}"


def delta_str(current: int, previous: int) -> str:
    """Delta-Symbol für Monatsvergleich."""
    diff = current - previous
    if diff > 0:
        return f" ↑{diff}"
    elif diff < 0:
        return f" ↓{abs(diff)}"
    return " →"


def generate_report(jobs: list[dict], prev_jobs: list[dict] | None, csv_path: Path) -> str:
    """Generiert den Markdown-Report."""
    total = len(jobs)
    sources = Counter(j["source"] for j in jobs)
    scrape_date = jobs[0].get("scraped_at", "n/a")[:10] if jobs else "n/a"

    # Monat aus Dateinamen extrahieren
    match = re.search(r"(\d{4}-\d{2})", csv_path.name)
    month_str = match.group(1) if match else datetime.now().strftime("%Y-%m")
    year, month = month_str.split("-")

    has_prev = prev_jobs is not None
    prev_total = len(prev_jobs) if has_prev else 0
    prev_sources = Counter(j["source"] for j in prev_jobs) if has_prev else Counter()

    lines = []

    # ─── 1. Kopfzeile ──────────────────────────────────────
    lines.append(f"# Job-Markt Report — {month_str}")
    lines.append("")
    delta_total = delta_str(total, prev_total) if has_prev else ""
    lines.append(f"**Monat:** {month}/{year} | **Stellen total:** {total}{delta_total} | "
                 f"**Quellen:** {len(sources)} | **Scraping-Datum:** {scrape_date}")
    lines.append("")

    # ─── 2. Executive Summary ──────────────────────────────
    lines.append("## Executive Summary")
    lines.append("")

    companies = Counter(j["company"] for j in jobs if j.get("company"))
    top_companies = companies.most_common(3)
    locations = Counter(j["location"] for j in jobs if j.get("location"))
    top_locations = locations.most_common(3)
    roles = Counter(categorize_role(j["title"]) for j in jobs)
    top_roles = roles.most_common(2)

    summary_parts = []
    summary_parts.append(f"Im {month_str} wurden **{total} Stellen** aus {len(sources)} Quellen erfasst.")
    if top_companies:
        top_str = ", ".join(f"{c} ({n})" for c, n in top_companies)
        summary_parts.append(f"Die aktivsten Arbeitgeber sind {top_str}.")
    if top_locations:
        loc_str = ", ".join(f"{l}" for l, _ in top_locations)
        summary_parts.append(f"Standort-Schwerpunkte liegen in {loc_str}.")
    if top_roles:
        role_str = " und ".join(f"{r}" for r, _ in top_roles)
        summary_parts.append(f"Dominierende Rollenkategorien: {role_str}.")
    if has_prev:
        diff = total - prev_total
        if diff > 0:
            summary_parts.append(f"Gegenüber dem Vormonat ein Anstieg um {diff} Stellen ({diff/prev_total*100:.1f}%)." if prev_total else "")
        elif diff < 0:
            summary_parts.append(f"Gegenüber dem Vormonat ein Rückgang um {abs(diff)} Stellen ({abs(diff)/prev_total*100:.1f}%)." if prev_total else "")
        else:
            summary_parts.append("Die Stellenzahl ist gegenüber dem Vormonat unverändert.")

    lines.append(" ".join(s for s in summary_parts if s))
    lines.append("")

    # ─── 3. Aufschlüsselung nach Quelle ───────────────────
    lines.append("## Aufschlüsselung nach Quelle")
    lines.append("")
    header = "| Quelle | Anzahl Stellen | Anteil (%)"
    if has_prev:
        header += " | Delta"
    header += " |"
    lines.append(header)
    sep = "|--------|---------------|----------"
    if has_prev:
        sep += "|------"
    sep += "|"
    lines.append(sep)

    for src in sorted(sources.keys()):
        count = sources[src]
        row = f"| {src} | {count} | {pct(count, total)}%"
        if has_prev:
            row += f" | {delta_str(count, prev_sources.get(src, 0))}"
        row += " |"
        lines.append(row)
    lines.append("")

    # ─── 4. Top Arbeitgeber ────────────────────────────────
    lines.append("## Top Arbeitgeber")
    lines.append("")
    lines.append("| Unternehmen | Offene Stellen | Häufigste Rolle | Standort(e) |")
    lines.append("|------------|---------------|----------------|------------|")

    prev_companies = Counter(j["company"] for j in prev_jobs if j.get("company")) if has_prev else Counter()
    company_jobs = defaultdict(list)
    for j in jobs:
        if j.get("company"):
            company_jobs[j["company"]].append(j)

    for company, count in companies.most_common():
        if count < 2:
            break
        cjobs = company_jobs[company]
        role_counter = Counter(j["title"] for j in cjobs)
        top_role = role_counter.most_common(1)[0][0] if role_counter else "–"
        locs = sorted(set(j.get("location", "–") for j in cjobs))
        loc_str = ", ".join(locs[:3])
        delta = ""
        if has_prev:
            delta = delta_str(count, prev_companies.get(company, 0))
        lines.append(f"| {company} | {count}{delta} | {top_role} | {loc_str} |")
    lines.append("")

    # ─── 5. Rollen-Analyse ─────────────────────────────────
    lines.append("## Rollen-Analyse")
    lines.append("")

    prev_roles = Counter(categorize_role(j["title"]) for j in prev_jobs) if has_prev else Counter()
    role_jobs = defaultdict(list)
    for j in jobs:
        cat = categorize_role(j["title"])
        role_jobs[cat].append(j)

    for cat in list(ROLE_CATEGORIES.keys()) + ["Andere"]:
        cat_jobs = role_jobs.get(cat, [])
        if not cat_jobs:
            continue
        count = len(cat_jobs)
        delta = ""
        if has_prev:
            delta = delta_str(count, prev_roles.get(cat, 0))
        lines.append(f"### {cat} — {count} Stellen{delta}")
        example_titles = list(set(j["title"] for j in cat_jobs))[:3]
        lines.append(f"- Beispiele: {', '.join(example_titles)}")
        cat_companies = sorted(set(j.get("company", "–") for j in cat_jobs))[:5]
        lines.append(f"- Firmen: {', '.join(cat_companies)}")
        lines.append("")

    # ─── 6. Standort-Verteilung ────────────────────────────
    lines.append("## Standort-Verteilung")
    lines.append("")
    header = "| Standort | Anzahl | Anteil (%)"
    if has_prev:
        header += " | Delta"
    header += " |"
    lines.append(header)
    sep = "|----------|--------|----------"
    if has_prev:
        sep += "|------"
    sep += "|"
    lines.append(sep)

    prev_locations = Counter(j["location"] for j in prev_jobs if j.get("location")) if has_prev else Counter()
    for loc, count in locations.most_common():
        if not loc:
            continue
        row = f"| {loc} | {count} | {pct(count, total)}%"
        if has_prev:
            row += f" | {delta_str(count, prev_locations.get(loc, 0))}"
        row += " |"
        lines.append(row)
    lines.append("")

    # ─── 7. Highlights ─────────────────────────────────────
    lines.append("## Highlights")
    lines.append("")

    scored_jobs = []
    for j in jobs:
        score = 0
        title_lower = j.get("title", "").lower()
        company_lower = j.get("company", "").lower()

        # Senior-Positionen
        if any(kw in title_lower for kw in SENIOR_KEYWORDS):
            score += 3
        # Prestige-Arbeitgeber
        if any(kw in company_lower for kw in PRESTIGE_EMPLOYERS):
            score += 2
        # Profil-Match
        matches = sum(1 for kw in PROFILE_KEYWORDS if kw in title_lower)
        score += matches * 2
        # Seltene Rollen (weniger als 3 in der Kategorie)
        cat = categorize_role(j["title"])
        if len(role_jobs.get(cat, [])) <= 3 and cat != "Andere":
            score += 1

        if score > 0:
            scored_jobs.append((score, j))

    scored_jobs.sort(key=lambda x: x[0], reverse=True)

    for _, j in scored_jobs[:10]:
        title = j.get("title", "–")
        company = j.get("company", "–")
        location = j.get("location", "–")
        url = j.get("url", "#")
        lines.append(f"- **{title}** @ {company} — {location} [↗ Link]({url})")

    if not scored_jobs:
        lines.append("*Keine herausragenden Highlights in diesem Monat.*")
    lines.append("")

    # ─── 8. Datenqualität ──────────────────────────────────
    lines.append("## Datenqualität")
    lines.append("")

    no_date = sum(1 for j in jobs if not j.get("published") or j["published"].lower() in ("n/a", ""))
    no_location = sum(1 for j in jobs if not j.get("location") or j["location"].lower() in ("n/a", ""))

    lines.append(f"- **Kein Publikationsdatum:** {no_date} Einträge ({pct(no_date, total)}%)")
    lines.append(f"- **Keine Location:** {no_location} Einträge ({pct(no_location, total)}%)")

    # Quellen mit 0 Ergebnissen
    all_expected_sources = {"arbeit.swiss", "LinkedIn"}
    # Karriereseiten aus Config laden
    try:
        import yaml
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        for company in config.get("career_pages", {}).get("companies", []):
            all_expected_sources.add(company["name"])
    except Exception:
        pass

    actual_sources = set(sources.keys())
    empty_sources = all_expected_sources - actual_sources
    if empty_sources:
        lines.append(f"- **0 Ergebnisse von:** {', '.join(sorted(empty_sources))} (Selektoren prüfen)")
    else:
        lines.append("- Alle konfigurierten Quellen haben Ergebnisse geliefert.")

    lines.append("")
    lines.append("---")
    lines.append(f"*Generiert am {datetime.now().strftime('%Y-%m-%d %H:%M')} durch generate_report.py*")

    return "\n".join(lines)


def main():
    current_csv, prev_csv = find_csvs()

    if not current_csv:
        print("Keine CSV-Datei in output/ gefunden. Zuerst main.py ausführen.")
        sys.exit(1)

    print(f"Aktuelle Datei: {current_csv}")
    jobs = load_csv(current_csv)
    print(f"  → {len(jobs)} Einträge geladen")

    prev_jobs = None
    if prev_csv:
        print(f"Vormonat: {prev_csv}")
        prev_jobs = load_csv(prev_csv)
        print(f"  → {len(prev_jobs)} Einträge geladen")

    if not jobs:
        print("CSV ist leer. Kein Report möglich.")
        sys.exit(1)

    report = generate_report(jobs, prev_jobs, current_csv)

    # Monat aus Dateiname
    match = re.search(r"(\d{4}-\d{2})", current_csv.name)
    month_str = match.group(1) if match else datetime.now().strftime("%Y-%m")
    report_path = OUTPUT_DIR / f"report_{month_str}.md"

    report_path.write_text(report, encoding="utf-8")
    print(f"Report gespeichert: {report_path}")


if __name__ == "__main__":
    main()
