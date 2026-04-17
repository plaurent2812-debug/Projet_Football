#!/bin/bash

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Detect Python interpreter
if [ -f "venv/bin/python" ]; then
    PYTHON_CMD="$PROJECT_DIR/venv/bin/python"
elif [ -f "../.venv/bin/python" ]; then
    PYTHON_CMD="$PROJECT_DIR/../.venv/bin/python"
else
    PYTHON_CMD=$(which python3)
fi

echo "📂 Projet : $PROJECT_DIR"
echo "🐍 Python : $PYTHON_CMD"

# Crontab entries
# 1. Every hour at minute 0: Update data (data only)
JOB_DATA="0 * * * * cd $PROJECT_DIR && $PYTHON_CMD run_pipeline.py data >> $PROJECT_DIR/cron_data.log 2>&1"

# 2. Every day at 23:59: Full run (data + analysis)
JOB_FULL="59 23 * * * cd $PROJECT_DIR && $PYTHON_CMD run_pipeline.py full >> $PROJECT_DIR/cron_full.log 2>&1"

# Backup current crontab
crontab -l > mycron.bak 2>/dev/null

# Remove existing jobs for this project to avoid duplicates (naive check)
grep -v "run_pipeline.py" mycron.bak > mycron.new

# Add new jobs
echo "$JOB_DATA" >> mycron.new
echo "$JOB_FULL" >> mycron.new

# Install new crontab
crontab mycron.new

echo ""
echo "✅ Tâches planifiées installées avec succès :"
echo "   - Toutes les heures (00min) : Mise à jour des matchs terminés"
echo "   - Tous les soirs (23h59)    : Analyse complète"
echo ""
echo "Commandes actives :"
crontab -l | grep "run_pipeline.py"

rm mycron.bak mycron.new
