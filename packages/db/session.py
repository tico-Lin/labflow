"""Forwarding session and base from app.database for compatibility.
This allows other parts of the repo to import packages.db.session
as the DB entrypoint while keeping the main implementation in app/.
"""
from app.database import engine, SessionLocal, Base

__all__ = ["engine", "SessionLocal", "Base"]
