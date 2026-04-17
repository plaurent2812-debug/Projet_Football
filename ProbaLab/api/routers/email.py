"""
api/routers/email.py — Transactional email endpoints (Resend).

Endpoints are internal/admin only, protected by verify_internal_auth.
"""

from typing import Annotated

from fastapi import APIRouter, Body, Header, HTTPException

from api.auth import verify_internal_auth
from api.schemas import EmailPayload
from api.services.email import _send_resend_email

router = APIRouter(prefix="/api/resend", tags=["Email"])


@router.post("/welcome")
def send_welcome_email(payload: Annotated[EmailPayload, Body()], authorization: str = Header(None)):
    """Send welcome email after registration (internal/admin only)."""
    verify_internal_auth(authorization)
    email = payload.email
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    html = """
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:32px;background:#f8faff">
      <div style="text-align:center;margin-bottom:32px">
        <h1 style="color:#1E40AF;font-size:28px;margin:0">⚡ ProbaLab</h1>
        <p style="color:#64748b;margin-top:8px">Analyses sportives augmentées par l'IA</p>
      </div>
      <div style="background:white;border-radius:12px;padding:32px;border:1px solid #e2e8f0">
        <h2 style="color:#1e293b;margin-top:0">Bienvenue sur ProbaLab ! 🎉</h2>
        <p style="color:#475569;line-height:1.6">
          Votre compte est créé. Vous avez maintenant accès aux probabilités 1X2 et aux paris recommandés
          pour tous les matchs de football et de NHL.
        </p>
        <p style="color:#475569;line-height:1.6">
          Passez en <strong style="color:#1E40AF">Premium</strong> pour débloquer toutes les statistiques avancées :
          BTTS, Over/Under, buteurs probables, analyse IA et bien plus.
        </p>
        <div style="text-align:center;margin-top:24px">
          <a href="https://probalab.fr/football" style="background:#1E40AF;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
            Voir les matchs →
          </a>
        </div>
      </div>
      <p style="color:#94a3b8;font-size:12px;text-align:center;margin-top:24px">
        ProbaLab fournit des analyses statistiques à titre informatif uniquement. Ce site ne constitue pas un conseil en paris sportifs.
      </p>
    </div>
    """
    ok = _send_resend_email(email, "Bienvenue sur ProbaLab ⚡", html)
    return {"sent": ok}


@router.post("/premium-confirm")
def send_premium_confirm_email(
    payload: Annotated[EmailPayload, Body()], authorization: str = Header(None)
):
    """Send premium confirmation email after payment (internal/admin only)."""
    verify_internal_auth(authorization)
    email = payload.email
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    html = """
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:32px;background:#f8faff">
      <div style="text-align:center;margin-bottom:32px">
        <h1 style="color:#1E40AF;font-size:28px;margin:0">⚡ ProbaLab</h1>
      </div>
      <div style="background:white;border-radius:12px;padding:32px;border:1px solid #e2e8f0">
        <h2 style="color:#1e293b;margin-top:0">Votre abonnement Premium est actif ! 🏆</h2>
        <p style="color:#475569;line-height:1.6">
          Félicitations ! Vous avez maintenant accès à toutes les fonctionnalités ProbaLab Premium :
        </p>
        <ul style="color:#475569;line-height:2">
          <li>✅ BTTS, Over 0.5 / 1.5 / 2.5 / 3.5</li>
          <li>✅ Score exact et penalty</li>
          <li>✅ Buteurs probables avec probabilités</li>
          <li>✅ Analyse IA complète de chaque match</li>
          <li>✅ Expected Goals (xG)</li>
          <li>✅ NHL : Top 5 buteurs, passeurs, tirs</li>
        </ul>
        <div style="text-align:center;margin-top:24px">
          <a href="https://probalab.fr/football" style="background:#1E40AF;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
            Accéder à ProbaLab →
          </a>
        </div>
      </div>
      <p style="color:#94a3b8;font-size:12px;text-align:center;margin-top:24px">
        ProbaLab fournit des analyses statistiques à titre informatif uniquement.
      </p>
    </div>
    """
    ok = _send_resend_email(email, "Votre abonnement Premium ProbaLab est actif 🏆", html)
    return {"sent": ok}
