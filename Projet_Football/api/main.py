# Compatibility shim — redirects to the real api.main module.
# Railway's start command is: uvicorn Projet_Football.api.main:app
from api.main import app  # noqa: F401

__all__ = ["app"]
