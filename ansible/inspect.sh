#!/bin/bash
# =============================================================================
# BURGINSPEKTION: Wrapper fuer verify.yml mit Protokoll
# =============================================================================
#
# Ausfuehrung:
#   ./inspect.sh                    # Alle Module
#   ./inspect.sh module01           # Nur Module 01
#   ./inspect.sh module02           # Nur Module 02
#
# Ergebnis: reports/YYYY-MM-DD_HH-MM_inspektion.log
#           reports/YYYY-MM-DD_HH-MM_inspektion.xml (JUnit)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

TIMESTAMP=$(date +%Y-%m-%d_%H-%M)
LOG_FILE="reports/${TIMESTAMP}_inspektion.log"
XML_PREFIX="reports/${TIMESTAMP}_inspektion"

mkdir -p reports

# Tags (optional)
TAGS=""
if [ -n "$1" ]; then
    TAGS="--tags $1"
fi

echo "=== BURGINSPEKTION $(date) ===" | tee "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Playbook ausfuehren, Output in Log + Terminal
JUNIT_OUTPUT_DIR=reports \
JUNIT_TASK_RELATIVE_PATH=true \
ansible-playbook -i inventory.yml verify.yml --limit rheinstein $TAGS 2>&1 | \
    # Nur die relevanten Zeilen filtern (OK/FEHLER/PLAY/TASK)
    grep -E '(^PLAY|^TASK|ok:|fatal:|changed:|PLAY RECAP|rheinstein|"msg":)' | \
    # Farbcodes entfernen
    sed 's/\x1b\[[0-9;]*m//g' | \
    tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "=== INSPEKTION ABGESCHLOSSEN $(date) ===" | tee -a "$LOG_FILE"
echo ""
echo "Protokoll: $LOG_FILE"

# JUnit XML umbenennen (lesbarerer Name)
LATEST_XML=$(ls -t reports/*.xml 2>/dev/null | head -1)
if [ -n "$LATEST_XML" ]; then
    mv "$LATEST_XML" "${XML_PREFIX}.xml"
    echo "JUnit XML: ${XML_PREFIX}.xml"
fi
