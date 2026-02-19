# Phase A/B/C Validation Examples

This page provides end-to-end examples for the analysis adapters and their API usage.

## 1) Tool Catalog

```bash
curl http://localhost:8000/analysis/tools
```

## 2) Phase A: Mendeleev + Pymatgen

### Mendeleev (element properties)
```bash
curl -X POST http://localhost:8000/analysis/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "mendeleev_props",
    "file_id": 123,
    "parameters": {"element": "Fe", "dopant": "Mn"},
    "store_output": true
  }'
```

### Pymatgen (CIF parse)
```bash
curl -X POST http://localhost:8000/analysis/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "pymatgen_cif",
    "file_id": 123,
    "parameters": {"symprec": 0.1},
    "store_output": true
  }'
```

## 3) Phase B: HDF5 + DOCX report

### HDF5 storage
```bash
curl -X POST http://localhost:8000/analysis/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "hdf5_storage",
    "file_id": 123,
    "parameters": {"dataset_name": "eis_sample", "x_col": "x", "y_col": "y"},
    "store_output": true
  }'
```

### DOCX report
```bash
curl -X POST http://localhost:8000/analysis/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "docx_report",
    "file_id": 123,
    "parameters": {
      "title": "Phase B Report",
      "summary": "Auto-generated report",
      "plot_x_col": "x",
      "plot_y_col": "y",
      "report_name": "phase-b-report"
    },
    "store_output": true
  }'
```

## 4) Phase C: Matminer + MP/COD XRD

### Matminer features
```bash
curl -X POST http://localhost:8000/analysis/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "matminer_features",
    "file_id": 123,
    "parameters": {"composition": "LiFePO4", "feature_set": "magpie"},
    "store_output": true
  }'
```

### XRD match with MP API
```bash
curl -X POST http://localhost:8000/analysis/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "xrd_match",
    "file_id": 123,
    "parameters": {
      "mp_id": "mp-149",
      "mp_api_key": "$MP_API_KEY",
      "two_theta_col": "2theta",
      "intensity_col": "intensity"
    },
    "store_output": true
  }'
```

## 5) Result Storage Verification

Use the stored IDs from the response:

```bash
curl http://localhost:8000/files/123/conclusions/
```

```bash
curl http://localhost:8000/files/123/annotations/
```

Report outputs are written under `REPORT_PATH` (default: `data/outputs/reports`).
