"""
End-to-end tests for Phase A/B/C analysis tooling.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from app import main
from app.models import Annotation, Conclusion, File
from app.storage import LocalStorage


CIF_SAMPLE = """data_NaCl
_symmetry_space_group_name_H-M   'F m -3 m'
_symmetry_Int_Tables_number      225
_cell_length_a   5.6402
_cell_length_b   5.6402
_cell_length_c   5.6402
_cell_angle_alpha  90
_cell_angle_beta   90
_cell_angle_gamma  90

loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Na1 Na 0 0 0
Cl1 Cl 0.5 0.5 0.5
"""


def _create_db_file(db, storage: LocalStorage, filename: str, content: bytes) -> File:
    file_hash = hashlib.sha256(content).hexdigest()
    path = os.path.join(storage.base_dir, f"{file_hash}.bin")
    with open(path, "wb") as handle:
        handle.write(content)

    record = File(filename=filename, storage_key=path, file_hash=file_hash)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@pytest.mark.integration
def test_analysis_mendeleev_stores_outputs(test_client, test_db, monkeypatch, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path / "managed"))
    monkeypatch.setattr(main, "storage", storage)

    db_file = _create_db_file(test_db, storage, "dummy.txt", b"phase-a")

    response = test_client.post(
        "/analysis/run",
        json={
            "tool_id": "mendeleev_props",
            "file_id": db_file.id,
            "parameters": {"element": "Fe", "dopant": "Mn"},
            "store_output": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["stored"]["conclusion_id"] is not None
    assert payload["stored"]["annotation_ids"]

    conclusion = test_db.query(Conclusion).filter_by(id=payload["stored"]["conclusion_id"]).first()
    assert conclusion is not None
    annotations = (
        test_db.query(Annotation)
        .filter(Annotation.id.in_(payload["stored"]["annotation_ids"]))
        .all()
    )
    assert annotations


@pytest.mark.integration
def test_analysis_hdf5_storage_creates_file(test_client, test_db, monkeypatch, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path / "managed"))
    monkeypatch.setattr(main, "storage", storage)
    monkeypatch.setenv("HDF5_PATH", str(tmp_path / "hdf5"))

    csv_bytes = b"x,y\n1,2\n2,4\n3,9\n"
    db_file = _create_db_file(test_db, storage, "curve.csv", csv_bytes)

    response = test_client.post(
        "/analysis/run",
        json={
            "tool_id": "hdf5_storage",
            "file_id": db_file.id,
            "parameters": {"x_col": "x", "y_col": "y", "kind": "curve"},
            "store_output": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"

    hdf5_path = payload["output"]["hdf5_path"]
    assert Path(hdf5_path).exists()

    conclusion = test_db.query(Conclusion).filter_by(id=payload["stored"]["conclusion_id"]).first()
    assert conclusion is not None
    annotations = (
        test_db.query(Annotation)
        .filter(Annotation.id.in_(payload["stored"]["annotation_ids"]))
        .all()
    )
    assert annotations


@pytest.mark.integration
def test_analysis_docx_report_writes_report(test_client, test_db, monkeypatch, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path / "managed"))
    monkeypatch.setattr(main, "storage", storage)
    monkeypatch.setenv("REPORT_PATH", str(tmp_path / "reports"))

    csv_bytes = b"x,y\n0,0\n1,1\n2,4\n"
    db_file = _create_db_file(test_db, storage, "plot.csv", csv_bytes)

    response = test_client.post(
        "/analysis/run",
        json={
            "tool_id": "docx_report",
            "file_id": db_file.id,
            "parameters": {
                "title": "Phase B Report",
                "summary": "Auto-generated report.",
                "plot_x_col": "x",
                "plot_y_col": "y",
                "report_name": "phase-b-report",
            },
            "store_output": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"

    report_path = payload["output"]["report_path"]
    assert Path(report_path).exists()

    conclusion = test_db.query(Conclusion).filter_by(id=payload["stored"]["conclusion_id"]).first()
    assert conclusion is not None


@pytest.mark.integration
def test_analysis_matminer_features_store_outputs(test_client, test_db, monkeypatch, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path / "managed"))
    monkeypatch.setattr(main, "storage", storage)

    db_file = _create_db_file(test_db, storage, "composition.txt", b"LiFePO4")

    response = test_client.post(
        "/analysis/run",
        json={
            "tool_id": "matminer_features",
            "file_id": db_file.id,
            "parameters": {"composition": "LiFePO4", "feature_set": "magpie"},
            "store_output": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["stored"]["conclusion_id"] is not None
    assert payload["stored"]["annotation_ids"]


@pytest.mark.integration
def test_analysis_pymatgen_cif_parsing(test_client, test_db, monkeypatch, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path / "managed"))
    monkeypatch.setattr(main, "storage", storage)

    db_file = _create_db_file(test_db, storage, "sample.cif", CIF_SAMPLE.encode("utf-8"))

    response = test_client.post(
        "/analysis/run",
        json={
            "tool_id": "pymatgen_cif",
            "file_id": db_file.id,
            "parameters": {"symprec": 0.1},
            "store_output": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["output"]["formula"]


@pytest.mark.integration
def test_analysis_xrd_match_runs(test_client, test_db, monkeypatch, tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path / "managed"))
    monkeypatch.setattr(main, "storage", storage)

    xrd_csv = b"2theta,intensity\n20,100\n30,80\n40,60\n"
    db_file = _create_db_file(test_db, storage, "peaks.csv", xrd_csv)

    response = test_client.post(
        "/analysis/run",
        json={
            "tool_id": "xrd_match",
            "file_id": db_file.id,
            "parameters": {
                "reference_cif_text": CIF_SAMPLE,
                "two_theta_col": "2theta",
                "intensity_col": "intensity",
                "peak_count": 3,
                "tolerance": 0.5,
            },
            "store_output": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert "match_score" in payload["output"]
