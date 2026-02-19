# LabFlow Requirements and Open Source Integrations

Updated: 2026-02-16
Owner: LabFlow

---

## 1. Goal and Scope

This document consolidates core requirements, development details, and open source integration requirements for LabFlow. It also defines stable integration interfaces to enable adding more open source tools in the future.

---

## 2. Core Requirements (Must Keep)

### 2.1 File Management
- Batch import of multiple formats (XRD .xy/.txt, EIS .txt/.csv, SEM images, Excel records).
- Automatic file-type detection and metadata extraction (date, instrument, sample ID).
- File de-duplication (SHA-256) and version tracking.
- Fast search by tags, date range, file type, keywords.
- Large file handling (chunked upload, progress reporting).
- Naming rule parsing for metadata extraction.
- Thumbnail/preview generation for images and plots.
- Raw file immutability (processing is done on copies).
- Storage abstraction to support local and object storage (S3/MinIO).

### 2.2 Tag and Conclusion System
- Multi-level tags (category tree or hierarchical labels).
- Quick tagging workflow (drag -> suggestions -> confirm).
- Conclusions with text + numeric + image snippets.
- Conclusion templates for standardized reporting.
- Versioned conclusions with edit history and traceability.
- Tag auto-complete and recommendations.
- Confidence labels for conclusions (high/medium/low or similar).

### 2.3 Annotations (Structured)
- JSON-based annotations with schema versioning.
- Provider field to support external labeling tools.
- Annotation search and linkage to files.

### 2.4 Reasoning Chain (Workflow Engine)
- Visual editor for DAG-style workflows.
- Auto-execution on new data import (rules and triggers).
- Manual execution with suggested analysis paths.
- Conditional branching based on output values.
- Execution history, result caching, and fault tolerance.

### 2.5 Security, Audit, and Sync
- JWT-based auth with RBAC (Admin/Editor/Viewer).
- Audit logging for sensitive changes.
- Sync status for filesystem and database.
- Backup strategy aligned with 3-2-1 rule.

---

## 3. Development Details (Must Keep)

### 3.1 Architecture and Stack
- Backend: FastAPI + SQLAlchemy + Pydantic.
- Database: SQLite (local) with PostgreSQL migration readiness.
- Cache: Redis (performance and background tasks).
- Task queue (optional): Celery + Redis.
- Storage abstraction: local filesystem + S3/MinIO.

### 3.2 Data Schema Baseline
Core tables and relations:
- Files, Tags, FileTags, Conclusions, Annotations.
- ReasoningChains, ReasoningNodes, ReasoningExecutions.
- Scripts, ScriptExecutions.
- Users, AuditLogs, SyncStatus.

### 3.3 v0.3 Reasoning Engine
- Node types: DATA_INPUT, TRANSFORM, CALCULATE, CONDITION, OUTPUT.
- DAG validation and topological execution.
- Node-level results, chain-level status aggregation.
- Caching and error recovery policies.

### 3.4 Script Library and Sandbox Execution
- Script upload, versioning, classification, search.
- Parameter injection and preset templates by file type/tag.
- Execution sandbox with timeout and resource constraints.
- Result capture with logs and artifacts.

### 3.5 File Classification Rules
- Rule-based file naming parser (YAML/JSON config).
- Metadata extraction for sample ID, test date, instrument.
- Auto-tagging on import.

### 3.6 Testing and Quality
- pytest with unit, integration, reasoning engine tests.
- Coverage target >= 80%, stretch to 85%+.
- Test structure cleanup and separation of smoke tests.

---

## 4. Open Source Integrations (Fiji, GSAS-II)

Note: Some integration adapters (e.g., scikit-image, pyFAI, impedance.py) are optional dependencies. When not installed, their adapters should return a failed result with a clear error message rather than raising unhandled exceptions.

### 4.1 Integration Strategy
Integrate bundled open source modules via a stable adapter layer so each tool can be swapped or updated independently.

**Integration modes**:
- Mode A: Bundled modules inside the LabFlow distribution (default).
- Mode B: External tool installed locally; LabFlow calls it via CLI or API (fallback).
- Mode C: Remote execution service (future).

**Core components**:
- Tool Adapter interface.
- Job Runner service for execution and logs.
- Data exchange standards (files, metadata, result payloads).
- Result import pipeline into LabFlow (Conclusions/Annotations).

### 4.2 Fiji Integration Requirements
**Purpose**: Image analysis and plugin ecosystem for microscopy and image processing.

**Integration**:
- Provide a Fiji adapter to call ImageJ/Fiji with macros or scripts.
- Support input from managed files and output artifacts (images, measurements).
- Record results as Conclusions/Annotations and store outputs in managed storage.

**Open source notes**:
- Fiji is largely GPL v2; exceptions listed in the Fiji LICENSES file.
- If bundling Fiji, include all required license texts and attribution.
- If modifying or distributing GPL components, comply with GPL obligations.
- Document license obligations and include notices for each bundled tool.

### 4.3 GSAS-II Integration Requirements
**Purpose**: XRD/neutron diffraction analysis and refinement.

**Integration**:
- Provide a GSAS-II adapter to run scripted analyses using its API.
- Support batch workflows for multiple datasets.
- Store outputs (refinement logs, plots, result tables) as artifacts and structured metadata.

**Open source notes**:
- GSAS-II is open source; check the license file in the distribution.
- Cite GSAS-II in publications as requested by its documentation.
- Preserve required notices and license text with distributions.

## 5. Domain Integration Matrix (Additions)

This section records domain-specific open source cores, recommended integration notes, and citation requirements.

### 5.1 Structure and Spectroscopy (XRD, XAS, XPS)

| Technique | Core | Language | License | Integration + Citation Notes |
| --- | --- | --- | --- | --- |
| XRD | GSAS-II | Python | CCP14 (BSD-like) | Integration: use `GSASIIscriptable` module. Citation: Toby & Von Dreele (2013). |
| XRD (2D to 1D) | pyFAI | Python | MIT | Integration: convert detector raw images to 1D patterns. Citation: Kieffer et al. (2013). |
| XRD reference cards | COD | Remote | See project | Integration: fetch CIF by COD ID for standard cards. |
| Materials data | Materials Project API | Python | See project | Integration: query structures and properties via MP API. |
| XAS (XANES/EXAFS) | Larch | Python | BSD | Integration: replace IFEFFIT; strong for synchrotron data. Citation: Newville (2013). |
| XPS | lmfit | Python | BSD | Strategy: no dominant OSS; implement Gaussian-Lorentz fitting with lmfit. Citation: Newville et al. (2014). |

### 5.2 Microscopy (SEM, TEM)

| Technique | Core | Language | License | Integration + Citation Notes |
| --- | --- | --- | --- | --- |
| SEM/TEM (General) | HyperSpy | Python | GPL v3 | Integration: multi-dimensional data handling (EDX/EELS). Note: GPL has copyleft implications. Citation: de la Pena et al. |
| Particle analysis | scikit-image | Python | BSD | Integration: particle size distribution for SEM stats. Citation: van der Walt et al. (2014). |
| Lattice analysis | Atomap | Python | GPL v3 | Integration: TEM atomic column and strain analysis. Citation: Nord et al. (2017). |

### 5.4 Materials Informatics

| Capability | Core | Language | License | Integration + Citation Notes |
| --- | --- | --- | --- | --- |
| Composition features | Matminer | Python | See project | Integration: composition feature extraction for screening/recommendation. |

### 5.3 Electrochemistry (CV, EIS, GCD)

| Technique | Core | Language | License | Integration + Citation Notes |
| --- | --- | --- | --- | --- |
| EIS (Impedance fit) | impedance.py | Python | MIT | Integration: fit equivalent circuits from frequency/real/imag. Citation: Murbach et al. (2020). |
| CV/GCD | ixdat | Python | MIT | Integration: electrochem + MS data handling. Citation: ixdat GitHub repo. |
| General electrochemistry | PyEchem (legacy) | Python | MIT | Strategy: prefer custom NumPy/Pandas for simple integration (capacitance) and derivatives (redox peaks); dependencies may be unnecessary. |

---

## 6. Compliance Checklist (Open Source)

- Keep a central THIRD_PARTY_NOTICES file with all licenses and attribution.
- Bundle license texts for each included tool and dependency.
- Document whether tools are bundled or user-installed.
- For GPL or copyleft licenses, ensure distribution obligations are met.
- Track tool versions and source URLs in a metadata registry.
- Provide citation guidance for GSAS-II when used in reports.

---

## 7. Future Integration Extension Points

### 6.1 Adapter Interface (Required)
Each tool must implement:
- `name`, `version`, `license`, `homepage`.
- `supported_file_types` and `capabilities`.
- `prepare_inputs()`, `run()`, `parse_outputs()`.

### 6.2 Job Runner Service
- Unified job submission and execution.
- Captures stdout/stderr and artifacts.
- Supports timeouts and resource limits.

### 6.3 Data Exchange Contract
- Standard input bundle: raw file + metadata JSON + params JSON.
- Standard output bundle: result JSON + artifact files + logs.
- Mapping rules into LabFlow Conclusions and Annotations.

### 6.4 API Space Reserved
Reserve API endpoints for future tool integration:
- `GET /integrations`
- `POST /integrations/{tool}/execute`
- `GET /integrations/{tool}/jobs/{job_id}`
- `GET /integrations/{tool}/capabilities`

---

## 8. Items to Confirm

- Verify exact license terms for bundled distributions.
- Record bundled vs external fallback decisions in open-source-components.md.
- Confirm preferred integration interface (CLI, scripting API, or service-based).

