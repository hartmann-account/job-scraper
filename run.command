#!/bin/bash
# ─── Job Scraper — Lokaler Lauf ─────────────────────────
# Doppelklick im Finder oder: ./run.command
# ─────────────────────────────────────────────────────────

cd "$(dirname "$0")"

echo "=================================="
echo "  Job Scraper — Lokaler Lauf"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo "=================================="
echo ""

# Python prüfen
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 nicht gefunden. Bitte installieren: brew install python3"
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

# Venv erstellen falls nötig
if [ ! -d "venv" ]; then
    echo "→ Erstelle virtuelle Umgebung..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "→ Installiere Abhängigkeiten..."
pip install -q -r requirements.txt

echo ""
echo "→ Starte Scraper..."
python3 main.py

echo ""
echo "→ Erstelle Report..."
python3 generate_report.py

echo ""
echo "=================================="
echo "  Fertig!"

# Neueste Dateien anzeigen
CSV=$(ls -t output/job_scrape_*.csv 2>/dev/null | head -1)
REPORT=$(ls -t output/report_*.md 2>/dev/null | head -1)

if [ -n "$CSV" ]; then
    JOBS=$(tail -n +2 "$CSV" | wc -l | tr -d ' ')
    echo "  $JOBS Jobs gescrapet → $CSV"
fi
if [ -n "$REPORT" ]; then
    echo "  Report → $REPORT"
fi
echo "=================================="

# Report im Finder öffnen
if [ -n "$REPORT" ]; then
    echo ""
    read -p "Report öffnen? (j/n) " -n 1 answer
    echo ""
    if [[ "$answer" =~ ^[jJyY]$ ]]; then
        open "$REPORT"
    fi
fi

read -p "Drücke Enter zum Beenden..."
