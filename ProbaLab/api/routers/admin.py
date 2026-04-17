"""
api/routers/admin.py — Admin and pipeline management endpoints.

Handles pipeline execution, status monitoring, and score updates.
Requires admin JWT or CRON_SECRET depending on the endpoint.
"""

import logging
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request

from api.auth import verify_cron_auth, verify_internal_auth
from api.schemas import RunPipelineRequest
from src.config import supabase


def _require_internal_auth(
    authorization: str | None = Header(None),
    x_cron_secret: str | None = Header(None, alias="X-Cron-Secret"),
) -> None:
    """FastAPI dependency wrapping verify_internal_auth with both headers."""
    verify_internal_auth(authorization=authorization, x_cron_secret=x_cron_secret)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])

# ─── In-memory pipeline state ────────────────────────────────────
_pipeline_state: dict = {
    "status": "idle",  # idle | running | done | error
    "mode": None,
    "started_at": None,
    "finished_at": None,
    "logs": "",
    "return_code": None,
}
_pipeline_lock = threading.Lock()

_ALLOWED_PIPELINE_MODES = ("full", "data", "analyze", "results", "nhl")


# ─── Admin Auth Helper ──────────────────────────────────────────

def _require_admin(authorization: str | None) -> dict:
    """Verify the Supabase JWT and check the user has admin role."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        user_resp = supabase.auth.get_user(token)
        user_id = user_resp.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    profile = (
        supabase.table("profiles").select("role").eq("id", str(user_id)).single().execute().data
    )

    if not profile or profile.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return profile


# ─── Pipeline background runner ──────────────────────────────────

def _run_pipeline_background(mode: str) -> None:
    """Run the pipeline in a background thread and capture output."""
    global _pipeline_state
    if mode not in _ALLOWED_PIPELINE_MODES:
        raise ValueError(f"Invalid pipeline mode: {mode}")
    project_dir = str(Path(__file__).resolve().parent.parent.parent)

    if mode == "nhl":
        cmd = [
            sys.executable,
            "-c",
            "from src.fetchers.nhl_pipeline import run_nhl_pipeline; run_nhl_pipeline()",
        ]
    else:
        cmd = [sys.executable, "run_pipeline.py"]
        if mode != "full":
            cmd.append(mode)

    with _pipeline_lock:
        _pipeline_state["process"] = None

    try:
        process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True,
        )

        # Store the process inside lock to allow killing it
        with _pipeline_lock:
            _pipeline_state["process"] = process

        # Read output in real-time
        for line in process.stdout:
            with _pipeline_lock:
                # Append new line and keep last 10k chars
                current_logs = _pipeline_state["logs"] + line
                _pipeline_state["logs"] = current_logs[-10000:]

        process.wait()

        with _pipeline_lock:
            if _pipeline_state["status"] == "cancelled":
                _pipeline_state["logs"] += "\n[Action] Arrêté par l'administrateur."
            else:
                _pipeline_state["status"] = "done" if process.returncode == 0 else "error"
            _pipeline_state["return_code"] = process.returncode
            _pipeline_state["finished_at"] = datetime.now(timezone.utc).isoformat()
            _pipeline_state["process"] = None

    except Exception as e:
        logger.exception("_run_pipeline_background failed for mode=%s", mode)
        with _pipeline_lock:
            _pipeline_state["status"] = "error"
            _pipeline_state["logs"] += f"\nInternal Error: {str(e)}"
            _pipeline_state["finished_at"] = datetime.now(timezone.utc).isoformat()
            _pipeline_state["process"] = None


# ─── Endpoints ──────────────────────────────────────────────────

@router.post("/api/cron/run-pipeline")
def cron_run_pipeline(body: Annotated[RunPipelineRequest, Body()], request: Request, authorization: str = Header(None)):
    """
    Trigger the pipeline via Trigger.dev scheduled tasks.
    Authenticated via CRON_SECRET (not Supabase JWT).
    """
    verify_cron_auth(authorization)

    mode = body.mode
    if mode not in ("full", "data", "analyze", "results", "nhl"):
        raise HTTPException(status_code=400, detail="Invalid mode")

    with _pipeline_lock:
        if _pipeline_state["status"] == "running":
            return {"message": "Pipeline already running — skipping", "status": "skipped"}

        _pipeline_state["status"] = "running"
        _pipeline_state["mode"] = mode
        _pipeline_state["started_at"] = datetime.now(timezone.utc).isoformat()
        _pipeline_state["finished_at"] = None
        _pipeline_state["logs"] = ""
        _pipeline_state["return_code"] = None

    thread = threading.Thread(target=_run_pipeline_background, args=(mode,), daemon=True)
    thread.start()

    return {
        "ok": True,
        "message": f"Pipeline '{mode}' started via cron",
        "started_at": _pipeline_state["started_at"],
    }


@router.post("/api/admin/run-pipeline")
def admin_run_pipeline(
    request: Request,
    mode: str = Query("full", description="Pipeline mode: full, data, analyze, results, or nhl"),
    authorization: str | None = Header(None),
):
    """Trigger the pipeline (admin only, requires Supabase JWT)."""
    _require_admin(authorization)

    if mode not in ("full", "data", "analyze", "results", "nhl"):
        raise HTTPException(
            status_code=400, detail="Mode must be: full, data, analyze, results, or nhl"
        )

    with _pipeline_lock:
        if _pipeline_state["status"] == "running":
            raise HTTPException(status_code=409, detail="Pipeline already running")

        _pipeline_state["status"] = "running"
        _pipeline_state["mode"] = mode
        _pipeline_state["started_at"] = datetime.now(timezone.utc).isoformat()
        _pipeline_state["finished_at"] = None
        _pipeline_state["logs"] = ""
        _pipeline_state["return_code"] = None

    thread = threading.Thread(target=_run_pipeline_background, args=(mode,), daemon=True)
    thread.start()

    return {"message": f"Pipeline '{mode}' started", "started_at": _pipeline_state["started_at"]}


@router.post("/api/admin/stop-pipeline")
def admin_stop_pipeline(request: Request, authorization: str | None = Header(None)):
    """Stop the running pipeline (admin only, requires Supabase JWT)."""
    _require_admin(authorization)

    with _pipeline_lock:
        if _pipeline_state["status"] != "running":
            raise HTTPException(status_code=400, detail="No pipeline is currently running")

        process = _pipeline_state.get("process")
        if process:
            try:
                process.terminate()  # Try graceful SIGTERM
                _pipeline_state["status"] = "cancelled"
                return {"message": "Démarrage de l'arrêt du pipeline en cours..."}
            except Exception as e:
                logger.error("Failed to stop pipeline process: %s", e, exc_info=True)
                raise HTTPException(status_code=500, detail="Internal server error")

        # Fallback if status is running but no process found
        _pipeline_state["status"] = "cancelled"
        _pipeline_state["finished_at"] = datetime.now(timezone.utc).isoformat()

    return {"message": "Pipeline annulé"}


@router.get("/api/admin/pipeline-status")
def admin_pipeline_status(request: Request, authorization: str | None = Header(None)):
    """Get current pipeline status (admin only, requires Supabase JWT)."""
    _require_admin(authorization)

    with _pipeline_lock:
        state = dict(_pipeline_state)
        # Remove non-serializable fields
        state.pop("process", None)
        return state


@router.post(
    "/api/admin/update-scores",
    dependencies=[Depends(_require_internal_auth)],
)
def admin_update_scores(
    request: Request,
    date: str | None = Query(None, description="Date YYYY-MM-DD (default: today)"),
):
    """
    Update match scores for a given date from API Football.
    Designed to be called by a CRON job every 15 minutes during match hours.
    Requires either a valid CRON_SECRET (Authorization: Bearer or X-Cron-Secret
    header) or an admin Supabase JWT — enforced by verify_internal_auth to
    protect the paid API-Football quota against unauthenticated DoS.
    """
    import threading as _threading

    def _run_scores():
        try:
            from src.fetchers.results import fetch_and_update_results

            fetch_and_update_results(date)
        except Exception:
            logger.exception("[update-scores] Error")

    t = _threading.Thread(target=_run_scores, daemon=True)
    t.start()

    from datetime import datetime as _dt, timezone

    target = date or _dt.now(timezone.utc).date().isoformat()
    return {"message": f"Score update started for {target}"}
