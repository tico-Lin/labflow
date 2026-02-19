"""Forwarding models from app.models for compatibility.
Other packages can import the SQLAlchemy models via this module.
"""
from app import models as models

__all__ = ["models"]
