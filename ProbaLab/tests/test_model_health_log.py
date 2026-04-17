"""Test d'intégration : table model_health_log (insert/read/delete).

Marqués integration : nécessitent une connexion Supabase active.
Exécution : pytest tests/test_model_health_log.py -m integration -v
"""

import pytest

from src.config import supabase

pytestmark = pytest.mark.integration


def test_model_health_log_table_exists():
    """La table model_health_log doit être accessible via le client Supabase."""
    result = supabase.table("model_health_log").select("id").limit(1).execute()
    assert hasattr(result, "data")


def test_model_health_log_insert_read():
    """Un enregistrement inséré doit être retrouvable, puis supprimé (cleanup)."""
    from uuid import uuid4

    note = f"test-{uuid4()}"
    supabase.table("model_health_log").insert(
        {
            "sport": "football",
            "brier_7d": 0.21,
            "brier_30d": 0.22,
            "notes": note,
        }
    ).execute()
    rows = supabase.table("model_health_log").select("*").eq("notes", note).execute().data
    assert len(rows) == 1
    assert rows[0]["sport"] == "football"
    assert float(rows[0]["brier_7d"]) == pytest.approx(0.21, abs=1e-6)
    # Cleanup
    supabase.table("model_health_log").delete().eq("notes", note).execute()


def test_model_health_log_sport_constraint():
    """Le check constraint sport IN ('football','nhl') doit être respecté."""
    from postgrest.exceptions import APIError

    with pytest.raises((APIError, Exception)):
        supabase.table("model_health_log").insert(
            {
                "sport": "tennis",
                "brier_7d": 0.20,
            }
        ).execute()
