
# LabFlow 系統需求與技術方案總覽

## 一、核心需求拆解

### 1.1 檔案管理系統
功能需求：
- 批次匯入多種格式（XRD .xy/.txt、EIS .txt/.csv、SEM 圖片、Excel 實驗記錄）
- 自動識別檔案類型並提取元數據（日期、儀器、樣品編號）
- 檔案去重（基於 hash）與版本追蹤
- 快速檢索（依標籤、日期範圍、檔案類型、關鍵字）
技術考量：
- 大檔案處理策略（分塊上傳、進度條）
- 檔案命名規範自動解析（如：Cr3_XRD_20250104.xy → 提取樣品/類型/日期）
- 縮圖生成（圖片/圖表預覽）
- 檔案存儲結構（扁平 vs 分層目錄）
補充建議：
- 檔案關聯：同一批實驗的多個檔案自動群組（如：同一樣品的 XRD + SEM + EIS）
- 原始檔保護：所有處理基於副本，保留原始檔不可變
- 元數據標準：定義最小欄位集（樣品編號、合成條件、測試參數）

### 1.2 標籤與結論系統
功能需求：
- 多層級標籤（實驗類型 > 樣品系列 > 具體條件）
- 快速標註介面（拖拉檔案 → 自動建議標籤 → 一鍵確認）
- 結論記錄（文字 + 數值 + 圖片截圖）
- 結論模板（如：「XRD 相純度判讀」固定格式）
技術考量：
- 標籤自動補全與推薦（基於歷史）
- 標籤層級關係（樹狀 vs 標籤組合）
- 結論版本控制（修改歷史、回溯）
- 富文本編輯器（支援 Markdown、LaTeX 公式）
補充建議：
- 智能標籤：基於檔案內容自動建議（如：XRD 峰位 → 建議「β-MnO₂」標籤）
- 結論鏈結：結論可引用其他檔案/結論（建立證據鏈）
- 置信度標記：結論可標記確定性（確認/待驗證/存疑）
- 協作功能：多人可對同一檔案添加不同視角的結論

### 1.3 推理鏈系統
功能需求：
- 視覺化編輯器：拖拉節點建立推理流程（如：XRD → 晶格參數 → 結構穩定性結論）
- 自動推理：新數據匯入 → 觸發相關推理鏈 → 自動計算 → 更新結論
- 手動推理：選擇數據 → 系統建議可用分析路徑 → 執行 → 比對結果
- 條件分支：依數據特徵選擇不同處理路徑（如：R_ct > 100 Ω → 執行 Warburg 分析）
技術考量：
- 節點類型設計（數據輸入/計算/判斷/輸出）
- 依賴關係管理（上游節點失敗如何處理）
- 推理歷史追蹤（可重現計算過程）
- 性能優化（避免重複計算、結果緩存）
補充建議：
- 推理模板庫：預設常用分析流程（如：「倍率性能評估鏈」）
- 異常偵測：數據異常時自動標記並暫停推理
- 推理解釋：每個節點輸出附帶「為什麼這樣算」的說明
- 推理分享：推理鏈可匯出為配置檔，供他人複用

### 1.4 數據處理程式整合
功能需求：
- 腳本庫管理：儲存/分類/搜尋預設分析腳本
- 一鍵執行：點擊檔案 → 選擇腳本 → 自動填充參數 → 執行 → 結果嵌入
- 參數預設：依檔案類型/標籤自動設定腳本參數
- 結果比對：分割視窗同時顯示多組數據處理結果
技術考量：
- 腳本沙盒執行（安全性、資源限制）
- 環境管理（不同腳本可能需要不同套件版本）
- 長時間計算處理（背景執行、進度通知）
- 腳本版本控制（追蹤修改、回溯）
補充建議：
- 腳本市場：社群分享腳本（如：「Rietveld 精修模板」）
- 參數記憶：記住每個樣品系列的常用參數
- 批次處理：選擇多個檔案 → 套用同一腳本 → 生成比對報告
- 互動式調整：執行後可調整參數重新計算（如：調整擬合範圍）

### 1.5 數據存儲策略
設計原則：SQL 存元數據、檔案/曲線等大型資料走外部存儲。

- 小型元數據：SQLite/PostgreSQL（File、Tag、Conclusion、Annotation）
- 大型曲線與矩陣：HDF5（CV/EIS/光譜）
- 原始檔：本機或 S3/MinIO

建議策略：
- 以 `file_id` 為索引，SQL 存路徑與摘要，HDF5 存原始數據
- HDF5 範例結構：`/Sample_A/Cycle_1/Raw_Data`

## 二、關鍵技術考量

### 2.1 擴展性設計
| 面向 | 初期 | 中期 | 長期 |
|---|---|---|---|
| 用戶數 | 單人 | 實驗室內（5–10人） | 跨機構協作 |
| 數據量 | <10 GB | 10–100 GB | >1 TB |
| 計算需求 | 本機 CPU | 本機 GPU / 多核 | 雲端分散式 |
| 功能模組 | 核心 3 功能 | +推理引擎 | +AI 輔助分析 |
設計原則：
- 模組化：每個功能獨立服務（檔案/標籤/推理/計算）
- 接口標準化：內部用 API 通訊，替換模組不影響其他部分
- 配置驅動：功能開關/參數透過配置檔控制

### 2.2 雲端同步策略
三種部署模式：
模式 A：本地優先（初期）
模式 B：混合模式（中期）
模式 C：完全雲端（長期）
建議路徑：先本地驗證，逐步加入同步，最後評估全雲端。

### 2.3 數據安全與隱私
- 敏感數據：研究數據可能涉及專利/未發表成果
- 訪問控制：多人使用時的權限管理（只讀/編輯/管理）
- 審計日誌：記錄誰在何時修改了什麼
- 備份策略：3-2-1 原則（3 份副本、2 種媒介、1 份異地）
技術方案：本地加密、雲端加密、私有雲部署

補充建議：
- 本地模式：SQLCipher 或檔案層加密
- 雲端模式：HTTPS + 伺服端靜態加密
- 私有雲：MinIO + VPN 隔離

## 三、技術架構完整方案

### 3.1 推薦架構（模組化 + 可遷移）
前端：React/Streamlit/Electron
後端：FastAPI + SQLAlchemy
資料層：SQLite/PostgreSQL + Local/S3/MinIO
任務隊列：Celery + Redis
存儲抽象層：FileStorage (Local/S3)
推理引擎：ReasoningEngine (節點型)

### 3.2 資料表設計草案
Files、Tags、FileTags、Conclusions、Scripts、ReasoningChains、ReasoningNodes、ReasoningExecutions、Users、AuditLogs、SyncStatus

### 3.3 推理引擎設計
節點類型：DATA_INPUT、TRANSFORM、CALCULATE、CONDITION、OUTPUT
執行引擎：依拓撲排序執行，支援錯誤處理與結果緩存

## 四、智能化與協作功能

### 4.1 智能化功能
- 自動標籤建議、異常偵測、推理鏈推薦、自動報告生成

### 4.2 協作功能
- 權限管理、評論討論、變更通知、版本控制

### 4.3 進階數據處理
- 批次比對、參數優化、機器學習整合

## 五、實施路線圖

階段 0：需求確認（1 週）
階段 1：基礎架構（2–3 週）
階段 2：結論系統（2 週）
階段 3：腳本整合（2–3 週）
階段 4：推理鏈（3–4 週）
階段 5：任務隊列（1–2 週）
階段 6：雲端同步（2–3 週）

# LabFlow API Spec (MVP v0.1)

## Analysis Tools API (v0.4 path)

### GET /analysis/tools
Returns the available analysis tools and parameter schemas.

### POST /analysis/run
Run a tool against a LabFlow-managed file.

Request:
```json
{
  "tool_id": "impedance",
  "file_id": 123,
  "parameters": {
    "freq_col": "frequency",
    "zreal_col": "zreal",
    "zimag_col": "zimag"
  },
  "store_output": true
}
```

Response:
```json
{
  "status": "completed",
  "output": {"parameters": [1.0, 2.0, 1e-5, 1.0]},
  "metrics": {},
  "warnings": [],
  "error": null,
  "stored": {"conclusion_id": 10, "annotation_ids": [11]}
}
```

## UI Strategy (Recommended)

- Tool catalog page backed by `GET /analysis/tools`.
- Parameter form generated from `parameters` (type, default, required).
- File picker using existing LabFlow file list.
- Run panel with status, outputs, and stored Conclusion/Annotation links.

---

## Phase Roadmap (Adapters + Data Layer)

### Phase A: Immediate (This Week)
- Pymatgen adapter: composition + CIF parsing + lattice output.
- Mendeleev adapter: element properties + dopant radius mismatch hints.
- SciencePlots: apply consistent plotting style for outputs.

Status:
- Implemented in code.
- Dependencies added in requirements.txt: `pymatgen`, `mendeleev`, `scienceplots`.

### Phase B: Data Layer Reinforcement
- h5py storage layer: SQL metadata + HDF5 arrays (CV/EIS/spectra).
- python-docx: report templates with plots + tables.

Status:
- Implemented in code.
- Dependencies added in requirements.txt: `h5py`, `python-docx`.

### Phase C: Research-grade Extensions
- COD / MP API: XRD reference matching and materials property queries.
- Matminer: composition features for screening/recommendation.

Status:
- Implemented in code (XRD match adapter + Matminer adapter).
- Dependencies added in requirements.txt: `mp-api`, `matminer`, `pymatgen`.

本文件定義 LabFlow 第一版（MVP）的 API：**檔案管理 / 標籤 / 結論 / 標註（接口預留）**。
設計目標：**本機可用、可模組化擴充、未來可切換雲端儲存與資料庫**。

---

## 0. 共同約定

### Base URL
- 本機開發：`http://127.0.0.1:8000`

### 內容格式
- Request/Response: `application/json`
- 檔案上傳：`multipart/form-data`

### 時間格式
- 所有時間使用 ISO 8601，例如：`2026-01-05T13:40:00+08:00`

### 認證（MVP）
- 預設為連線版（Auth: JWT）
- 支援離線操作（`OFFLINE_MODE=true` 時允許本機操作，限制外部同步）
- 後續擴充：Session / OAuth2（不影響既有路由）

### 錯誤回應格式
- `HTTP 400/404/500`
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "filename is required",
    "details": null
  }
}
```

---

## 1. System

### GET `/health`
用途：健康檢查
**Response 200**
```json
{ "ok": true, "version": "0.1.0" }
```

---

## 2. Files（檔案）

### File Object Model
```json
{
  "id": "uuid-string",
  "filename": "Cr3_XRD_20260105.xy",
  "content_type": "text/plain",
  "size_bytes": 123456,
  "sha256": "hex-string",
  "storage_backend": "local",
  "storage_key": "managed/2026/01/Cr3_XRD_20260105.xy",
  "created_at": "2026-01-05T13:40:00+08:00",
  "tags": [] 
  "metadata_json": { "instrument": "Rigaku", "sample_id": "Cr3", "date": "2026-01-05" }
}
```

### GET `/files`
用途：列出檔案（支援簡單篩選）
**Query**
- `q`: 檔名關鍵字 (Optional)
- `tag_id`: 篩選特定標籤 ID (Optional)
- `limit`: 預設 50
- `offset`: 預設 0

**Response 200**
```json
{
  "items": [ { "id": "...", "filename": "...", "tags": [...] } ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

### POST `/files`
用途：上傳檔案
**Request (multipart/form-data)**
- `file`: binary
- `note`: string (Optional)

**Response 201**
- 回傳完整 File Object

### GET `/files/{file_id}`
用途：取得單檔資訊 (Metadata)

### GET `/files/{file_id}/download`
用途：下載原始檔
**Response 200**
- Header: `Content-Disposition: attachment; filename="..."`
- Body: File Binary

### DELETE `/files/{file_id}`
用途：刪除檔案（Metadata + 實體檔視策略而定）
**Response 204** (No Content)

---

## 3. Tags（標籤）

### GET `/tags`
用途：取得所有標籤
**Response 200**
```json
[
  { "id": "uuid", "name": "XRD", "category": "type" },
  { "id": "uuid", "name": "Cr3%", "category": "sample" }
]
```

### POST `/tags`
用途：建立新標籤
**Request**
```json
{ "name": "EIS", "category": "type" } // category 可選，預設 null
```
**Response 201**
- 回傳建立的 Tag Object

### POST `/files/{file_id}/tags`
用途：為檔案貼標籤 (Associate)
**Request**
```json
{ "tag_id": "uuid" }
```
**Response 200**
```json
{ "ok": true, "message": "Tag added" }
```

### DELETE `/files/{file_id}/tags/{tag_id}`
用途：移除檔案的某個標籤
**Response 204**

---

## 4. Conclusions（結論）

### GET `/files/{file_id}/conclusions`
用途：取得該檔案的所有結論
**Response 200**
```json
[
  {
    "id": "uuid",
    "content_md": "## 初步判讀\n無雜相，峰位偏移 0.2度",
    "confidence": "high",
    "created_at": "..."
  }
]
```

### POST `/files/{file_id}/conclusions`
用途：新增結論
**Request**
```json
{
  "content_md": "Markdown text...",
  "confidence": "high" 
}
```
**Response 201**
 回傳 Conclusion Object，包含 created_at, updated_at 欄位

### PUT `/conclusions/{conclusion_id}`
用途：修改結論
**Request**
```json
{ "content_md": "Updated text...", "confidence": "medium" }
```
**Response 200**
```json
{
  "id": "uuid",
  "file_id": "uuid",
  "content_md": "Updated text...",
  "confidence": "medium",
  "created_at": "...",
  "updated_at": "..."
}
```

### DELETE `/conclusions/{conclusion_id}`
用途：刪除結論

---

## 5. Annotations（標註 - 預留接口）

### GET `/files/{file_id}/annotations`
用途：取得該檔案的所有結構化標註
**Response 200**
```json
[
  {
    "id": "uuid",
    "provider": "local",
    "schema_version": "v1",
    "payload_json": {
      "type": "range",
      "x_min": 20,
      "x_max": 25,
      "label": "Peak (101)",
      "extra": { "intensity": 1200 }
    },
    "created_at": "..."
  }
]
```

### POST `/files/{file_id}/annotations`
用途：新增標註 (Generic)
**Request**
```json
{
  "provider": "local",
  "schema_version": "v1",
  "payload_json": { ... }
}
```
**Response 201**
- 回傳 Annotation Object

---

## 6. Reasoning（推理鏈）

### POST `/reasoning-chains`
用途：建立推理鏈
**Request**
```json
{
  "name": "XRD 相純度分析",
  "description": "計算 XRD 樣品相純度",
  "nodes": [
    {
      "node_id": "node1",
      "node_type": "data_input",
      "config": {"file_type": "xrd"}
    }
  ],
  "is_template": false
}
```

### POST `/reasoning-chains/{chain_id}/execute`
用途：執行推理鏈並儲存執行紀錄
**Request**
```json
{
  "input_data": {"file_id": "file-uuid-123"},
  "model_name": "gpt-4o-mini",
  "tool_name": "pyFAI"
}
```
**Response 200**
```json
{
  "execution_id": "exec-uuid",
  "chain_id": "chain-uuid",
  "status": "completed",
  "user_id": 1,
  "model_name": "gpt-4o-mini",
  "tool_name": "pyFAI",
  "started_at": "2026-02-16T10:00:00Z"
}
```

### GET `/executions/{execution_id}`
用途：取得推理鏈執行結果
**Response 200**
```json
{
  "execution_id": "exec-uuid",
  "chain_id": "chain-uuid",
  "status": "completed",
  "user_id": 1,
  "model_name": "gpt-4o-mini",
  "tool_name": "pyFAI",
  "input_data": {"file_id": "file-uuid-123"},
  "results": {"node1": {"status": "completed", "output": {}}},
  "error": null,
  "execution_time_ms": 1200,
  "started_at": "2026-02-16T10:00:00Z",
  "completed_at": "2026-02-16T10:00:01Z"
}
```

---

## 7. Final Goal Extensions (Planned)

### 7.1 Materials Recipe + Synthesis Conditions
目標：配方、溫度、時間、氣氛與批次關聯，建立可追溯流程。

實作細節：
- 新增資料表：`Samples`, `Batches`, `SynthesisConditions`
- `Files` 連結 `sample_id`，`Conclusions` 可對樣品/批次生效
- API: `POST /samples`, `POST /batches`, `POST /synthesis-conditions`

詳細規格：
- Samples: `id`, `name`, `formula`, `doping`, `created_at`
- Batches: `id`, `sample_id`, `batch_code`, `operator`, `created_at`
- SynthesisConditions: `id`, `batch_id`, `temperature_c`, `time_hr`, `atmosphere`, `notes_md`
- API 範例：
```json
{ "name": "MnO2-Cr0.1", "formula": "Mn0.9Cr0.1O2", "doping": {"Cr": 0.1} }
```
- 流程：建立 Sample -> 建立 Batch -> 掛條件 -> 上傳檔案關聯 batch_id

### 7.2 Reference Card / Spectrum Matching (XRD/Raman/IR)
目標：自動比對標準卡並給出相位建議。

實作細節：
- 標準卡索引表：`ReferenceCards` (phase, peaks, source, metadata)
- 分析流程：峰值提取 -> 相似度計算 -> 候選相位排序
- API: `POST /analysis/match` (file_id + type)

詳細規格：
- ReferenceCards: `id`, `phase`, `peaks`, `source`, `metadata_json`
- MatchingResult: `file_id`, `phase`, `score`, `matched_peaks`
- API 請求：
```json
{ "file_id": 123, "type": "xrd", "top_k": 5 }
```
- 輸出：候選相位 + 分數 + 匹配峰位

### 7.3 Data Quality Scoring
目標：自動計算 SNR、雜訊指標、飽和/漂移檢測。

實作細節：
- Quality 指標 schema：`data_quality` 存入 `Annotations`
- API: `POST /analysis/quality` -> 回傳 metrics
- UI: 顯示分數與警告標記

詳細規格：
- 指標：`snr`, `noise_rms`, `drift_slope`, `saturation_ratio`
- Annotation payload: `{ "type": "quality", "metrics": {...} }`
- 觸發：檔案上傳後可選擇自動執行

### 7.4 Reproducibility Audit
目標：同一樣品多次測試差異統計，輸出穩定性指標。

實作細節：
- 聚合同一 `sample_id` + `test_type`
- 指標：均值/標準差/漂移係數
- API: `GET /samples/{id}/reproducibility`

詳細規格：
- 輸出：`metric`, `mean`, `stdev`, `cv` (變異係數)
- 依據：同類型檔案 + 相同 test_type

### 7.5 Research Log / Experiment Flow
目標：把筆記、步驟、設定、結果綁在同一流程卡。

實作細節：
- 新增 `LabNotes`、`ExperimentFlows`，每個 flow 可掛多個 file/conclusion
- API: `POST /flows`, `POST /flows/{id}/notes`

詳細規格：
- ExperimentFlows: `id`, `title`, `owner_id`, `created_at`
- LabNotes: `id`, `flow_id`, `content_md`, `created_at`
- 關聯：`FlowFiles`、`FlowConclusions`

### 7.6 Auto Naming Rules
目標：依條件自動生成檔名與標籤。

實作細節：
- 新增 `NamingRules` (pattern + tags + metadata mapping)
- 上傳檔案時套用，回傳建議檔名與標籤
- API: `POST /naming-rules`, `POST /files/preview-name`

詳細規格：
- rule: `regex`, `template`, `tags`, `metadata_map`
- preview 回應：`suggested_filename`, `suggested_tags`, `metadata_json`

### 7.7 Knowledge Base / FAQ
目標：儀器 SOP、常見錯誤排解、實驗流程整理。

實作細節：
- 新增 `KnowledgeBase` (title, category, content_md)
- API: `GET /kb`, `POST /kb`

詳細規格：
- 支援全文檢索：`q` + `category`
- 版本欄位：`version`, `updated_at`

### 7.8 Export Pipelines
目標：批次匯出為 CSV/JSON/HDF5/報告包。

實作細節：
- Export job queue + storage output
- API: `POST /exports`, `GET /exports/{id}`

詳細規格：
- ExportJob: `id`, `type`, `status`, `output_path`, `created_at`
- 支援 `files`, `samples`, `date_range`

### 7.9 Data Ingestion Automation
目標：定時監控資料夾，自動解析與入庫。

實作細節：
- Watcher 任務 + 命名規則解析
- API: `POST /ingestion/jobs` (path + schedule)

詳細規格：
- IngestionJob: `id`, `path`, `schedule`, `status`, `last_run`
- 解析結果寫入 `Files` + `Annotations`

### 7.10 Analysis Template Library
目標：常用分析流程一鍵套用，支援分享與版本。

實作細節：
- `AnalysisTemplates` (nodes + metadata)
- API: `GET /templates`, `POST /templates`

詳細規格：
- template: `id`, `name`, `nodes`, `version`, `owner_id`
- 支援 public/private

### 7.11 Anomaly Detection + Alerts
目標：標記異常曲線/範圍並推送提醒。

實作細節：
- 規則引擎 + 指標閾值
- API: `POST /analysis/anomaly`, `GET /alerts`

詳細規格：
- Alert: `id`, `file_id`, `severity`, `message`, `created_at`
- 通知渠道：UI badge + email (後續)

### 7.12 Report Generation
目標：一鍵輸出 PDF/Word (圖表+結論+參數表)。

實作細節：
- 報告模板 + export pipeline
- API: `POST /reports`, `GET /reports/{id}`

詳細規格：
- ReportJob: `id`, `template_id`, `status`, `output_path`
- 內容：sample + plots + conclusions

### 7.13 Sample/Experiment Graph
目標：樣品→批次→測試→結論的關聯圖譜。

實作細節：
- Graph 視圖由 SQL 聚合生成
- API: `GET /samples/{id}/graph`

詳細規格：
- 回應格式：nodes/edges
- 支援 graph filters (date, test_type)

### 7.14 Visualization Dashboard
目標：多圖聯動對比 (多樣品、多條件、時間序列)。

實作細節：
- 前端 dashboard with filters
- API: `GET /dashboards/summary`

詳細規格：
- summary: aggregates + series + comparisons
- 支援 time range + tag filters

### 7.15 Version Tracking
目標：推理鏈、腳本、結論版本歷史與差異比對。

實作細節：
- `VersionHistory` table + diff snapshots
- API: `GET /versions/{resource}/{id}`

詳細規格：
- version: `id`, `resource_type`, `resource_id`, `diff`, `created_at`

### 7.16 Batch Jobs + Scheduling
目標：批次分析 + 背景執行 + 進度/重試/優先級。

實作細節：
- Celery queues + job table
- API: `POST /jobs`, `GET /jobs/{id}`

詳細規格：
- Job: `id`, `type`, `status`, `progress`, `priority`
- 支援 retry/backoff

### 7.17 Backup + Restore
目標：快照/版本化，可回復指定時間點。

實作細節：
- 備份策略 + restore 作業
- API: `POST /backups`, `POST /restores`

詳細規格：
- Backup: `id`, `scope`, `created_at`, `storage_path`
- Restore: `id`, `backup_id`, `status`

### 7.18 Localization (i18n)
目標：中英雙語介面與文件。

實作細節：
- 前端字典檔 + 後端訊息碼
- API: `GET /i18n/strings`

詳細規格：
- locale: `zh-TW`, `en-US`
- key-value 字典，支持版本號