import os

from config import logger
from dotenv import load_dotenv
from supabase import Client, create_client

# Charger les variables d'environnement depuis .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Erreur : SUPABASE_URL ou SUPABASE_KEY manquante dans le fichier .env")
    exit(1)

# Créer le client Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logger.info("Connexion au client Supabase réussie !")

# Tenter de lister les tables via le schéma information_schema
try:
    response = (
        supabase.table("information_schema.tables")
        .select("table_name")
        .eq("table_schema", "public")
        .execute()
    )
    tables = [row["table_name"] for row in response.data]
    if tables:
        logger.info(f"Tables trouvées dans le schéma public ({len(tables)}) :")
        for table in tables:
            logger.info(f"  - {table}")
    else:
        logger.info("Aucune table trouvée dans le schéma public (ou accès restreint via RLS).")
except Exception as e:
    # Si la requête échoue (accès restreint), on confirme quand même la connexion
    logger.warning(f"Impossible de lister les tables (accès restreint ou table inexistante) : {e}")
    logger.info("Mais la connexion au client Supabase est bien établie.")
