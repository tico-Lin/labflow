# Features | 核心功能

---

## 📖 Language / 語言

- [English ↓](#english)
- [中文 ↓](#chinese)

---

<a id="english"></a>

## English

### Feature Overview

LabFlow provides a comprehensive set of features organized into four categories:

1. [Base Features](#base-features) — available in all modes
2. [Intelligent Analysis](#intelligent-analysis) — AI-powered file analysis
3. [Network Features](#network-features) — scientific database integration
4. [Collaboration Features](#collaboration-features) — team workflows

---

### Base Features

Available in **all execution modes**.

#### File Management

- **Upload**: Drag-and-drop or API file upload
- **Auto-deduplication**: SHA-256 hash prevents duplicate files
- **Query**: Full-text search and filter by metadata
- **Download**: Direct file download with access control
- **Delete**: Soft-delete with optional permanent removal
- **Versioning**: Git-like object storage with rollback support

#### Tagging System

- Create, edit, and delete custom tags
- Many-to-many file-tag associations
- Tag-based filtering and search
- Bulk tag operations

#### Conclusion Records

- Add structured analysis conclusions to any file
- Edit and delete conclusions
- Support for rich text and structured data
- Auto-generated conclusions (via AI module)

#### Annotation System

- Arbitrary JSON structure for structured annotations
- Attach metadata to files, tags, or conclusions
- Query annotations by key-value pairs
- Bulk annotation management

#### Reasoning Chain Engine

- Create automated analysis workflows as visual DAGs
- 5 node types: Data Input, Transform, Calculate, Condition, Output
- Execute chains manually or on a schedule
- Result caching and fault-tolerant execution

#### Visualization Interface

- Visual reasoning chain editor (drag-and-drop nodes)
- Real-time execution status display
- Result visualization (charts, tables)
- Export workflow diagrams

---

### Intelligent Analysis

Powered by the **4 intelligence modules** (completed in v0.3).

#### File Identifier 🔬

Automatically identifies scientific instrument output files:

| File Type | Identified Formats | Extracted Features |
|-----------|-------------------|-------------------|
| XRD | `.xy`, `.xrdml`, `.ras` | 2θ range, peak positions, d-spacing |
| EIS | `.mpt`, `.dta`, `.txt` | Frequency range, impedance, phase |
| CV | `.mpt`, `.txt` | Scan rate, potential window, peak currents |
| SEM | `.tif`, `.jpg`, image formats | Scale bar, magnification, sample info |

#### Naming Manager 📝

- Standardize filenames according to lab conventions
- Learn from historical naming patterns using ML
- Batch rename operations
- Generate standardized names from file metadata

#### Tag Recommender 🏷️

- **Rule-based**: Pattern matching on filename and content
- **Collaborative filtering**: Learn from users' tagging history
- Confidence scores for each recommendation
- One-click tag application

#### Conclusion Generator 📄

- Auto-generate analysis conclusions from file content
- Support for both Chinese and English output
- Customizable templates per file type
- AI backend: Local LLM (Ollama) or Cloud AI (OpenAI/Claude)

---

### Network Features

Available in **Modes 2, 3, 4, and 5**.

#### Scientific API Integration

| Service | Data Type | Use Case |
|---------|-----------|----------|
| [Materials Project](https://materialsproject.org) | Crystal structures, properties | XRD reference matching |
| [PubChem](https://pubchem.ncbi.nlm.nih.gov) | Chemical compounds | Compound identification |
| [COD](https://www.crystallography.net/cod/) | Crystal structures | Structure comparison |
| Custom APIs | Any REST API | Lab-specific integrations |

#### Cloud Backup

- Encrypted upload to Google Drive, OneDrive, or NAS
- AES-256 encryption before upload (zero-knowledge)
- Configurable sync schedule
- Manual and automatic backup triggers

---

### Collaboration Features

Available in **Modes 4B and 5**.

#### Token System

- Lab-level access control via unique tokens
- Token generation, revocation, and audit
- Multi-lab support on a single server

#### Permission Management (RBAC)

| Role | Permissions |
|------|-------------|
| **Admin** | Full access: manage users, tokens, all data |
| **Editor** | Read/write: upload, tag, annotate, conclude |
| **Viewer** | Read-only: view and download files |

#### Conflict Resolution

- Smart merge for non-conflicting changes
- User choice dialog for conflicting edits
- Conflict history and resolution log
- Git-inspired merge strategy

#### Audit Logs

- Full log of all user actions with timestamps
- Filter by user, action type, resource, or time range
- Export audit logs as CSV or JSON
- Compliance-ready format

---

### AI Features

Configurable as **local, cloud, or disabled**.

| Config | Provider | Offline? | Cost |
|--------|----------|----------|------|
| Local LLM | Ollama | ✅ Yes | Free |
| Cloud AI | OpenAI GPT-4 | ❌ No | Pay-per-use |
| Cloud AI | Anthropic Claude | ❌ No | Pay-per-use |
| Disabled | Rule engine only | ✅ Yes | Free |

**Auto-fallback**: If AI is unavailable, the system gracefully degrades to the rule-based engine.

---

<a id="chinese"></a>

## 中文

### 功能概覽

LabFlow 提供四大類功能：

1. [基礎功能](#基礎功能) — 所有模式均可用
2. [智能分析](#智能分析) — AI 驅動的文件分析
3. [網絡功能](#網絡功能) — 科學數據庫集成
4. [協作功能](#協作功能) — 團隊工作流程

---

### 基礎功能

在**所有運行模式**中均可用。

#### 文件管理

- **上傳**：拖放或 API 文件上傳
- **自動去重**：SHA-256 哈希防止重複文件
- **查詢**：全文搜索和按元數據篩選
- **下載**：帶訪問控制的直接文件下載
- **刪除**：軟刪除，支持可選永久刪除
- **版本控制**：Git-like 對象存儲，支持回滾

#### 標籤系統

- 創建、編輯和刪除自定義標籤
- 文件-標籤多對多關聯
- 基於標籤的篩選和搜索
- 批量標籤操作

#### 結論記錄

- 為任何文件添加結構化分析結論
- 編輯和刪除結論
- 支持富文本和結構化數據
- 自動生成結論（通過 AI 模塊）

#### 註解系統

- 任意 JSON 結構的結構化註解
- 為文件、標籤或結論附加元數據
- 按鍵值對查詢註解
- 批量註解管理

#### 推理鏈引擎

- 以可視化 DAG 形式創建自動化分析工作流
- 5 種節點類型：數據輸入、轉換、計算、條件、輸出
- 手動或定時執行工作流
- 結果緩存和容錯執行

#### 可視化界面

- 可視化推理鏈編輯器（拖放節點）
- 實時執行狀態顯示
- 結果可視化（圖表、表格）
- 導出工作流程圖

---

### 智能分析

由 **4 個智能模塊**驅動（v0.3 已完成）。

#### 文件識別器 🔬

自動識別科學儀器輸出文件：

| 文件類型 | 識別格式 | 提取特徵 |
|----------|----------|----------|
| XRD | `.xy`、`.xrdml`、`.ras` | 2θ 範圍、峰位置、d 間距 |
| EIS | `.mpt`、`.dta`、`.txt` | 頻率範圍、阻抗、相位 |
| CV | `.mpt`、`.txt` | 掃速、電位窗口、峰電流 |
| SEM | `.tif`、`.jpg`、圖像格式 | 比例尺、放大倍數、樣品信息 |

#### 命名管理器 📝

- 根據實驗室規範標準化文件名
- 使用機器學習從歷史命名模式中學習
- 批量重命名操作
- 從文件元數據生成標準化名稱

#### 標籤推薦器 🏷️

- **規則引擎**：對文件名和內容進行模式匹配
- **協同過濾**：從用戶標籤歷史中學習
- 每個推薦都帶有置信度分數
- 一鍵應用標籤

#### 結論生成器 📄

- 從文件內容自動生成分析結論
- 支持中英文輸出
- 每種文件類型可自定義模板
- AI 後端：本地 LLM（Ollama）或雲端 AI（OpenAI/Claude）

---

### 網絡功能

在**模式 2、3、4 和 5** 中可用。

#### 科學 API 集成

| 服務 | 數據類型 | 使用場景 |
|------|----------|----------|
| [Materials Project](https://materialsproject.org) | 晶體結構、性質 | XRD 參考匹配 |
| [PubChem](https://pubchem.ncbi.nlm.nih.gov) | 化學化合物 | 化合物鑒定 |
| [COD](https://www.crystallography.net/cod/) | 晶體結構 | 結構比較 |
| 自定義 API | 任意 REST API | 實驗室特定集成 |

#### 雲端備份

- 加密上傳至 Google Drive、OneDrive 或 NAS
- 上傳前 AES-256 加密（零知識）
- 可配置同步計劃
- 手動和自動備份觸發

---

### 協作功能

在**模式 4B 和 5** 中可用。

#### 令牌系統

- 通過唯一令牌實現實驗室級訪問控制
- 令牌生成、撤銷和審計
- 單個服務器支持多實驗室

#### 權限管理（RBAC）

| 角色 | 權限 |
|------|------|
| **Admin** | 完整訪問：管理用戶、令牌、所有數據 |
| **Editor** | 讀/寫：上傳、打標籤、添加註解、寫結論 |
| **Viewer** | 只讀：查看和下載文件 |

#### 衝突解決

- 非衝突更改的智能合併
- 衝突編輯的用戶選擇對話框
- 衝突歷史和解決日誌
- Git 啟發的合併策略

#### 審計日誌

- 所有用戶操作的完整帶時間戳日誌
- 按用戶、操作類型、資源或時間範圍篩選
- 導出審計日誌為 CSV 或 JSON
- 符合合規要求的格式

---

### AI 功能

可配置為**本地、雲端或禁用**。

| 配置 | 提供商 | 可離線？ | 費用 |
|------|--------|----------|------|
| 本地 LLM | Ollama | ✅ 是 | 免費 |
| 雲端 AI | OpenAI GPT-4 | ❌ 否 | 按使用付費 |
| 雲端 AI | Anthropic Claude | ❌ 否 | 按使用付費 |
| 禁用 | 僅規則引擎 | ✅ 是 | 免費 |

**自動降級**：如果 AI 不可用，系統會優雅地降級到規則引擎。

---

*← [Architecture](Architecture) | [Configuration →](Configuration)*
