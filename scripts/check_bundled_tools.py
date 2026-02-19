"""
Validate expected bundled tool paths under tools/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List


EXPECTED_PATHS = {
    "fiji": "tools/Fiji",
    "gsas2": "tools/GSAS-II/GSASII",
    "pyfai": "tools/pyFAI/src",
    "larch": "tools/larch/larch",
    "lmfit": "tools/lmfit/lmfit",
    "hyperspy": "tools/hyperspy/hyperspy",
    "scikit_image": "tools/scikit-image/src",
    "impedance_py": "tools/impedance.py/impedance",
    "ixdat": "tools/ixdat/src",
    "pymatgen": "tools/pymatgen/pymatgen",
    "mendeleev": "tools/mendeleev/mendeleev",
    "h5py": "tools/h5py/h5py",
    "python_docx": "tools/python-docx/docx",
    "scienceplots": "tools/SciencePlots/scienceplots",
    "matminer": "tools/matminer/matminer",
    "mp_api": "tools/materialsproject-api/mp_api",
    "atomap": "tools/atomap/atomap",
    "pyechem": "tools/pyechem/pyechem",
}


def _load_enabled_tools(config_path: Path) -> Dict[str, bool]:
    if not config_path.exists():
        return {}

    enabled: Dict[str, bool] = {}
    current_tool = None
    in_integrations = False
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("integrations:"):
            in_integrations = True
            continue
        if not in_integrations:
            continue
        if raw_line.startswith("  ") and not raw_line.startswith("    "):
            tool_name = line.rstrip(":")
            current_tool = tool_name
            if tool_name not in enabled:
                enabled[tool_name] = False
            continue
        if current_tool and line.startswith("enabled:"):
            value = line.split(":", 1)[1].strip().lower()
            enabled[current_tool] = value == "true"

    return enabled


def _iter_paths(paths: Dict[str, str]) -> List[str]:
    return list(paths.values())


LICENSE_FILENAMES = [
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.md",
    "COPYING",
    "COPYING.txt",
]


def _tool_base_dir(root: Path, rel_path: str) -> Path:
    parts = Path(rel_path).parts
    if len(parts) >= 2 and parts[0].lower() == "tools":
        return root / parts[0] / parts[1]
    return root / rel_path


def _has_license_file(base_dir: Path) -> bool:
    for name in LICENSE_FILENAMES:
        if (base_dir / name).exists():
            return True
    return False


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check bundled tool paths.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all expected paths regardless of config enabled state.",
    )
    parser.add_argument(
        "--licenses",
        action="store_true",
        help="Check for LICENSE or COPYING files in each bundled tool root.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    config_path = root / "config" / "integrations.yml"
    enabled = _load_enabled_tools(config_path)

    expected_paths = _iter_paths(EXPECTED_PATHS)
    if not args.all and enabled:
        expected_paths = [
            path for key, path in EXPECTED_PATHS.items() if enabled.get(key, False)
        ]

    missing = []
    for rel in expected_paths:
        path = root / rel
        if not path.exists():
            missing.append(rel)

    if missing:
        print("Missing bundled tool paths:")
        for rel in missing:
            print(f"- {rel}")
        return 1

    if args.licenses:
        missing_licenses = []
        for rel in expected_paths:
            base_dir = _tool_base_dir(root, rel)
            if base_dir.exists() and not _has_license_file(base_dir):
                missing_licenses.append(str(base_dir.relative_to(root)))

        if missing_licenses:
            print("Missing LICENSE/COPYING files:")
            for rel in missing_licenses:
                print(f"- {rel}")
            return 1

    print("All expected bundled tool paths are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
