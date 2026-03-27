#!/bin/bash
# Adds cron job to run termik forecast every 3 hours
# Usage: bash termik/cron_setup.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV="$SCRIPT_DIR/.venv/bin/python"
LOG="$SCRIPT_DIR/output/cron.log"

CRON_CMD="0 */3 * * * cd $PROJECT_DIR && $VENV -m termik >> $LOG 2>&1"

# Check if already installed
if crontab -l 2>/dev/null | grep -q "termik"; then
    echo "Cron job already exists. Current entry:"
    crontab -l | grep termik
    exit 0
fi

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
echo "Cron job installed:"
echo "  $CRON_CMD"
echo ""
echo "Forecast will run every 3 hours (00, 03, 06, 09, 12, 15, 18, 21)"
echo "Log: $LOG"
