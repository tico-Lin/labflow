"""
Pymatgen adapter for CIF parsing and lattice/composition extraction.
"""

from __future__ import annotations

from typing import Any, Dict

from ..base import ToolAdapter, ToolContext, ToolParameter, ToolResult, ToolSpec


class PymatgenAdapter(ToolAdapter):
    spec = ToolSpec(
        id="pymatgen_cif",
        name="Pymatgen CIF Parser",
        version="1.0",
        description="Parse CIF files and report composition and lattice parameters.",
        input_types=["cif"],
        parameters=[
            ToolParameter("symprec", "number", False, 0.1, "Symmetry tolerance for space group"),
        ],
        outputs=["formula", "composition", "lattice", "spacegroup"],
    )

    def run(self, context: ToolContext) -> ToolResult:
        if not context.file_bytes:
            return ToolResult(status="failed", error="Missing file bytes")

        try:
            from pymatgen.core import Structure
        except ImportError as exc:
            return ToolResult(status="failed", error=f"pymatgen not available: {exc}")

        params = context.parameters or {}
        symprec = float(params.get("symprec", 0.1))

        try:
            cif_text = context.file_bytes.decode("utf-8", errors="replace")
            structure = Structure.from_str(cif_text, fmt="cif")
        except Exception as exc:
            return ToolResult(status="failed", error=f"Failed to parse CIF: {exc}")

        composition = structure.composition
        lattice = structure.lattice
        spacegroup = None
        try:
            spacegroup = structure.get_space_group_info(symprec=symprec)
        except Exception:
            spacegroup = None

        output: Dict[str, Any] = {
            "formula": composition.reduced_formula,
            "composition": composition.get_el_amt_dict(),
            "fractional_composition": composition.fractional_composition.get_el_amt_dict(),
            "num_sites": int(structure.num_sites),
            "lattice": {
                "a": float(lattice.a),
                "b": float(lattice.b),
                "c": float(lattice.c),
                "alpha": float(lattice.alpha),
                "beta": float(lattice.beta),
                "gamma": float(lattice.gamma),
                "volume": float(lattice.volume),
            },
            "spacegroup": spacegroup[0] if spacegroup else None,
            "spacegroup_number": spacegroup[1] if spacegroup else None,
        }

        annotations = [
            {
                "analysis": "cif_parse",
                "formula": output["formula"],
                "lattice": output["lattice"],
                "spacegroup": output["spacegroup"],
            }
        ]
        conclusion = f"CIF parsed for {output['formula']}"

        return ToolResult(status="completed", output=output, annotations=annotations, conclusion=conclusion)
