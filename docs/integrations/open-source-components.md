# Open Source Components Registry

This registry tracks tool versions, source URLs, and distribution modes for integrated open source software.

Updated: 2026-02-16

---

## Tools

| Tool | Version | Source URL | Distribution Mode | Notes |
| --- | --- | --- | --- | --- |
| Fiji (ImageJ) | TBD | https://github.com/fiji/fiji | Bundled (binary) | Stored at tools/Fiji; full distribution retained. |
| GSAS-II | TBD | https://github.com/AdvancedPhotonSource/GSAS-II | Bundled (core only) | Core package at tools/GSAS-II/GSASII. |
| pyFAI | TBD | https://github.com/silx-kit/pyFAI | Bundled (core only) | Core package at tools/pyFAI/src. |
| Larch | TBD | https://github.com/xraypy/xraylarch | Bundled (core only) | Core package at tools/larch/larch. |
| lmfit | TBD | https://github.com/lmfit/lmfit-py | Bundled (core only) | Core package at tools/lmfit/lmfit. |
| HyperSpy | TBD | https://github.com/hyperspy/hyperspy | Bundled (core only) | Core package at tools/hyperspy/hyperspy. |
| scikit-image | TBD | https://github.com/scikit-image/scikit-image | Bundled (core only) | Core package at tools/scikit-image/src. |
| pymatgen | TBD | https://github.com/materialsproject/pymatgen | Bundled (core only) | CIF parsing, structure analysis, XRD reference patterns. |
| mendeleev | TBD | https://github.com/lmmentel/mendeleev | Bundled (core only) | Element property queries. |
| h5py | TBD | https://github.com/h5py/h5py | Bundled (core only) | HDF5 storage for curves/arrays. |
| python-docx | TBD | https://github.com/python-openxml/python-docx | Bundled (core only) | DOCX report generation. |
| SciencePlots | TBD | https://github.com/garrettj403/SciencePlots | Bundled (core only) | Matplotlib style presets. |
| Matminer | TBD | https://github.com/hackingmaterials/matminer | Bundled (core only) | Composition feature extraction. |
| MP API | TBD | https://github.com/materialsproject/api | Bundled (core only) | Materials Project API client. |
| COD | N/A | https://www.crystallography.net/cod/ | Remote (HTTP) | CIF fetch for reference patterns. |
| Atomap | TBD | https://github.com/atomap/atomap | Bundled (core only) | Core package stored under tools/atomap. |
| impedance.py | TBD | https://github.com/ECSHackWeek/impedance.py | Bundled (core only) | Core package at tools/impedance.py/impedance. |
| ixdat | TBD | https://github.com/ixdat/ixdat | Bundled (core only) | Core package at tools/ixdat/src. |
| PyEchem | TBD | https://github.com/pyEchem/pyEchem | Bundled (core only) | Core package stored under tools/pyechem. |

---

## Versioning Rules

- Record exact versions and build identifiers used for integration.
- For bundled tools, store the downloaded archive name and checksum.
- For external installs, capture minimum supported version and detection rules.

---

## Distribution Modes

- External: Tool is installed by the user and invoked by LabFlow.
- Bundled: Tool is shipped inside LabFlow distribution (requires license review).
- Remote: Tool is hosted externally and invoked via API (future option).

