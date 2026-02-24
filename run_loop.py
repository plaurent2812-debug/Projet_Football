import time
import subprocess
import sys
import os
from datetime import datetime

# Configuration
PROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Projet_Football")
PYTHON_CMD = sys.executable

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def run_pipeline(mode="data"):
    log(f"🚀 Lancement du pipeline ({mode})...")
    try:
        subprocess.run([PYTHON_CMD, "run_pipeline.py", mode], cwd=PROJECT_DIR, check=True)
        log(f"✅ Pipeline ({mode}) terminé.")
        
        # Run NHL Results evaluation right after the main pipeline
        if mode in ["data", "full"]:
            log("🚀 Évaluation des prédictions NHL (Top 1) terminées...")
            subprocess.run([PYTHON_CMD, "fetchers/fetch_nhl_results.py"], cwd=PROJECT_DIR, check=False)
            log("✅ Évaluation NHL terminée.")
            
    except subprocess.CalledProcessError as e:
        log(f"❌ Erreur lors de l'exécution : {e}")
    except Exception as e:
        log(f"❌ Erreur inattendue : {e}")

def main():
    log("🤖 Démarrage de la boucle d'automatisation Football IA")
    log("   - Update rapide : Toutes les heures à xx:00")
    log("   - Analyse complète : Tous les jours à 23:59")
    
    last_hour_run = -1
    last_day_run = -1

    while True:
        now = datetime.now()
        
        # 1. Hourly Data Update (at minute 0)
        if now.minute == 0 and now.hour != last_hour_run:
            # Skip if it's 23:00 (because full run is at 23:59)
            if now.hour != 23:
                run_pipeline("data")
                last_hour_run = now.hour

        # 2. Daily Full Analysis (at 23:59)
        if now.hour == 23 and now.minute == 59 and now.day != last_day_run:
            run_pipeline("full")
            last_day_run = now.day
            # Mark hourly run as done for 23h to avoid double run if loop restarts
            last_hour_run = 23 

        # Sleep for 30 seconds
        time.sleep(30)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("👋 Arrêt de la boucle.")
