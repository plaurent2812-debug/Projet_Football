import os
import sys

sys.path.insert(0, os.path.abspath("Projet_Football"))

from api.routers.trigger import nhl_update_live_scores

nhl_update_live_scores()
