"""
Plot styling helpers for analysis adapters.
"""

from __future__ import annotations

from typing import Optional, Tuple


def apply_scienceplots_style(style_name: str = "science", with_grid: bool = True) -> Tuple[bool, Optional[str]]:
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
    except ImportError:
        return False, "matplotlib not available"

    try:
        import scienceplots  # noqa: F401

        styles = [style_name]
        if with_grid:
            styles.append("grid")
        plt.style.use(styles)
        plt.rcParams["text.usetex"] = False
        return True, None
    except Exception as exc:
        try:
            plt.style.use("default")
        except Exception:
            pass
        return False, f"scienceplots not available: {exc}"
