"""
Integration helper utilities.
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional


def write_temp_file(data: bytes, filename: Optional[str] = None) -> str:
    suffix = ""
    if filename and "." in filename:
        _, ext = os.path.splitext(filename)
        suffix = ext
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        handle.write(data)
        return handle.name
    finally:
        handle.close()
