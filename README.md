# Job Scraper — Monatliche Automatisierung

Automatisierter Job-Scraper für den Schweizer Finanzmarkt. Läuft monatlich via GitHub Actions und sammelt Stellenanzeigen von:

- **Arbeit.swiss** (job-room.ch API)
- **LinkedIn** (öffentliche Guest-API)
- **Karriereseiten** (konfigurierbare Selektoren pro Unternehmen)

## Setup

### 1. Repository erstellen

```bash
# Neues Repo auf GitHub erstellen, dann:
git clone https://github.com/DEIN-USER/job-scraper.git
cd job-scraper
```

### 2. Alle Dateien kopieren

Kopiere den gesamten Inhalt dieses Pakets ins Repo.

### 3. Konfiguration anpassen

Bearbeite `config.yaml`:

- **search_terms**: Deine Suchbegriffe
- **locations**: Kantone / Städte
- **career_pages.companies**: Weitere Unternehmen hinzufügen (CSS-Selektoren müssen stimmen)

### 4. Lokal testen

```bash
# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Dependencies installieren
pip install -r requirements.txt

# Testlauf (ohne Speichern)
python main.py --dry-run

# Normaler Lauf
python main.py

# Als Excel
python main.py --format xlsx
```

### 5. Push & Automation aktivieren

```bash
git add .
git commit -m "feat: Job-Scraper initial setup"
git push
```

Die GitHub Action läuft automatisch am **1. jedes Monats um 10:00 CET**.

Manueller Trigger: GitHub → Actions → "Monthly Job Scrape" → "Run workflow".

## Architektur

```
job-scraper/
├── .github/workflows/
│   └── scrape.yml          # GitHub Actions Workflow (Cron)
├── scrapers/
│   ├── __init__.py
│   ├── arbeit_swiss.py     # Arbeit.swiss API-Scraper
│   ├── linkedin.py         # LinkedIn Guest-API Scraper
│   └── career_pages.py     # Generischer Karriereseiten-Scraper
├── output/                 # Ergebnisse (CSV/XLSX, auto-committed)
├── config.yaml             # Suchkonfiguration
├── main.py                 # Orchestrator
├── requirements.txt
└── README.md
```

## Output

Ergebnisse werden in `output/` gespeichert als:

| Feld       | Beschreibung                    |
|------------|---------------------------------|
| source     | Quelle (arbeit.swiss, LinkedIn) |
| title      | Stellentitel                    |
| company    | Unternehmen                     |
| location   | Standort                        |
| workload   | Pensum (wenn verfügbar)         |
| published  | Publikationsdatum               |
| url        | Link zur Stelle                 |
| scraped_at | Zeitpunkt des Scrapings         |

## Karriereseiten erweitern

Um eine neue Firma hinzuzufügen:

1. Öffne die Karriereseite im Browser
2. Rechtsklick → "Untersuchen" auf einem Job-Eintrag
3. Finde die CSS-Klasse für: Job-Container, Titel, Standort, Link
4. Trage sie in `config.yaml` ein:

```yaml
- name: "Neue Firma AG"
  url: "https://firma.ch/karriere"
  type: "html"
  selectors:
    job_list: ".stellenanzeige"
    title: ".titel"
    location: ".ort"
    link: "a"
```

## Einschränkungen

- **LinkedIn**: Nutzt die öffentliche Guest-API ohne Login. Kann jederzeit brechen, wenn LinkedIn die Schnittstelle ändert. Bei 429-Fehlern (Rate Limit) wartet der Scraper automatisch.
- **Karriereseiten**: CSS-Selektoren müssen manuell gepflegt werden. Wenn eine Firma ihr Layout ändert, bricht der Scraper für diese Seite.
- **JS-lastige Seiten**: Der Scraper nutzt kein Browser-Rendering (kein Selenium/Playwright). Seiten, die Jobs erst per JavaScript laden, werden nicht gescraped. Lösung: Playwright-Integration (erhöht Komplexität).

## Lizenz

Privat. Für eigene Nutzung bestimmt.
