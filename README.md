# LabFlow v1.0

**Intelligent Laboratory Data Management System** | **智能實驗室數據管理系統**

_Modular · Flexible · Offline-First_ | _模式化 · 靈活 · 離線優先_

> 🎯 **Status**: Production-ready v1.0 (Released 2026-02-24) | 🎯 **狀態**: 生產版本 v1.0（2026-02-24 發布）
>
> 📋 **Documentation**: [docs/README.md](docs/README.md) | 📋 **文檔**: [docs/README.md](docs/README.md)

---

## 📖 Language Selection / 語言選擇

- **[Read in English ↓](#english)**
- **[用中文閱讀 ↓](#中文)**

---

---

<a id="english"></a>

# LabFlow v1.0 - English Edition

**Intelligent Laboratory Data Management System** - Modular, Flexible, Offline-First

## Core Principles

1. **Offline by Default** - Full functionality without network dependency
2. **Modular Deployment** - 5 execution modes, install only what you need
3. **Flexible AI Strategy** - Support for local/cloud/no AI configurations
4. **Dual Cloud System** - Separate private backup and team collaboration

## 5 Execution Modes

| Mode                            | Description                | Use Case             | Network    | AI              | Cloud Backup | Collaboration |
| ------------------------------- | -------------------------- | -------------------- | ---------- | --------------- | ------------ | ------------- |
| **1️⃣ Local Fully Offline**      | Complete offline operation | Airplane, secure lab | ❌         | 🏠 Local        | ❌           | ❌            |
| **2️⃣ Local-Connected Privacy**  | Download data, no upload   | Query scientific DBs | ✅ Limited | 🏠 Local        | ✅ Encrypted | ❌            |
| **3️⃣ Local-Connected Full**     | Full network features      | Trust cloud          | ✅ Full    | ⚙️ Optional     | ✅ Encrypted | ❌            |
| **4️⃣A Collab-Connected Simple** | 3rd-party cloud sync       | Small team           | ✅         | 🏠 Local        | ✅ Encrypted | ⚠️ Limited    |
| **4️⃣B Collab-Connected Full**   | LabFlow Server             | Lab team             | ✅         | 🔬 Lab-deployed | ✅           | ✅ Full       |
| **5️⃣ Cloud Collaboration**      | Server mode                | Central server       | ✅         | ⚙️ Deployable   | ⚙️           | ✅ Full       |

## ✨ Core Features

### Base Features (All Modes)

- **File Management**: Upload, auto-dedup (SHA-256), query, download, delete
- **Tagging System**: Create tags, many-to-many associations
- **Conclusion Records**: Add, edit, delete file conclusions
- **Annotation System**: Structured annotations with arbitrary JSON
- **Reasoning Chain Engine**: Create and execute automated analysis workflows
- **Visualization Interface**: Reasoning chain visual viewer

### Intelligent Analysis (v0.3 Complete)

- **File Identifier** 🔬: Auto-identify XRD/EIS/CV/SEM, extract features
- **Naming Manager** 📝: Standardize filenames, learn historical patterns
- **Tag Recommender** 🏷️: Rule + collaborative filtering recommendations
- **Conclusion Generator** 📄: Auto-generate analysis conclusions (Chinese & English)

### Network Features (Modes 2/3/4)

- **Scientific API Integration**: Materials Project, PubChem, COD, etc.
- **Cloud Backup**: Encrypted upload to Google Drive, OneDrive, NAS
- **Version Control**: Git-like object storage with rollback support

### Collaboration Features (Modes 4/5)

- **Token System**: Lab-level access control
- **Permission Management**: RBAC (Admin, Editor, Viewer)
- **Conflict Resolution**: Smart merge + user choice
- **Audit Logs**: Who did what, when

### AI Features (Optional)

- **Local LLM**: Ollama support (offline available)
- **Cloud AI**: OpenAI / Claude (optional, can disable)
- **Lab AI**: Self-hosted model deployment
- **Auto-Fallback**: AI → rule engine graceful degradation

## 🗺️ Development Status

### ✅ v0.2.0 - Production Ready (Completed)

- JWT auth, RBAC access control
- Docker support, Redis caching
- 95%+ test coverage

### ✅ v0.3.0 - Intelligent Expansion (Completed)

- Reasoning chain engine (DAG execution, 5 node types)
- Visual editor and viewer
- Script engine & automation workflows
- Intelligent analysis modules

### ✅ v1.0.0 - Architecture Redesign (Completed 2026-02-24)

- ⭐ **[Architecture Decisions](docs/architecture/FINAL_ARCHITECTURE_DECISIONS.md)** - Complete v1.0 design
- 📋 **[Implementation Plan](docs/roadmap/V1_0_IMPLEMENTATION_CHECKLIST.md)** - 22-week roadmap
- All phases designed and documented

## 📚 Documentation

> 📋 **Full Index**: [docs/README.md](docs/README.md) | [docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md)

### Core Documents

- **[Architecture Final Decisions](docs/architecture/FINAL_ARCHITECTURE_DECISIONS.md)** ⭐ - v1.0 design (2200+ lines)
- [Architecture Overview](docs/architecture/ARCHITECTURE_OVERVIEW.md)
- [Mode Comparison](docs/architecture/MODE_COMPARISON.md)
- [Quick Start Guide](docs/getting-started/quick-start.md)

### Feature Documentation

- [File Identifier](docs/features/intelligence/FILE_IDENTIFIER_IMPLEMENTATION.md) 🔬
- [Naming Manager](docs/features/intelligence/NAMING_MANAGER_IMPLEMENTATION.md) 📝
- [Tag Recommender](docs/features/intelligence/TAG_RECOMMENDER_IMPLEMENTATION.md) 🏷️
- [Conclusion Generator](docs/features/intelligence/CONCLUSION_GENERATOR_IMPLEMENTATION.md) 📄
- [Reasoning Engine](docs/features/reasoning/REASONING_ENGINE_ENHANCEMENT.md)
- [Internationalization](docs/features/i18n/I18N_MODULE.md) (Chinese & English)

### Desktop Application

- [Build Guide](docs/desktop/DESKTOP_BUILD_GUIDE.md)
- [Quick Start](docs/desktop/DESKTOP_QUICKSTART.md)
- [Deployment Guide](docs/desktop/DESKTOP_DEPLOYMENT_GUIDE.md)

### Legal & Compliance

- [Security Policy](SECURITY.md)
- [Copyright & License](COPYRIGHT.md) - GNU General Public License v3.0
- [Third-Party Notices](THIRD_PARTY_NOTICES.md)

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/labflow.git
cd labflow

# Create Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start backend
python -m uvicorn labflow.core.main:app --reload

# Start frontend (in another terminal)
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker-compose up --build
```

## 🔧 Environment Variables

- `STORAGE_PATH`: File storage root (default: `data/managed`)
- `DATABASE_URL`: Database connection (default: `sqlite:///./labflow.db`)
- `MAX_UPLOAD_SIZE`: Max upload size (default: 52428800 / 50 MiB)
- `OFFLINE_MODE`: Local-only mode (default: `true`)
- `SECRET_KEY`: JWT signing key (change in production)

## 📦 Project Structure

```
labflow/
├── core/                    # Backend core (FastAPI)
├── frontend/               # React frontend
├── electron/              # Desktop application
├── docs/                  # Documentation
└── tests/                 # Test suite
```

## 🤝 Contributing

We welcome contributions! Please fork, create a feature branch, commit changes, and open a Pull Request.

## 📄 License

**GNU General Public License v3.0 (GPL-3.0)** - See [LICENSE](LICENSE) and [COPYRIGHT.md](COPYRIGHT.md)

## 📞 Support

- **Documentation**: [docs/README.md](docs/README.md)
- **Issues**: GitHub Issues
- **Email**: contact@labflow.local

---

---

<a id="中文"></a>

# LabFlow v1.0 - 中文版

**智能實驗室數據管理系統** - 模式化、靈活、離線優先

## 🎯 核心理念

1. **默認離線** - 完整功能不依賴網絡
2. **模式化部署** - 5 種運行模式，按需安裝模塊
3. **靈活 AI 策略** - 支持本地/雲端/無 AI 三種配置
4. **雙雲端系統** - 分離私有備份和團隊協作

## 🏗️ 五種運行模式

| 模式                  | 描述                 | 使用場景         | 網絡    | AI        | 雲端備份 | 協作    |
| --------------------- | -------------------- | ---------------- | ------- | --------- | -------- | ------- |
| **1️⃣ 本地完全離網**   | 完全離線運行         | 飛機、保密實驗室 | ❌      | 🏠 本地   | ❌       | ❌      |
| **2️⃣ 本地聯網隱私版** | 下載科學數據，不上傳 | 需要查詢數據庫   | ✅ 限定 | 🏠 本地   | ✅ 加密  | ❌      |
| **3️⃣ 本地聯網全面版** | 完整網絡功能         | 信任雲端服務     | ✅ 完整 | ⚙️ 可選   | ✅ 加密  | ❌      |
| **4️⃣A 協作簡化版**    | 第三方雲端同步       | 小團隊簡單協作   | ✅      | 🏠 本地   | ✅ 加密  | ⚠️ 受限 |
| **4️⃣B 協作完整版**    | LabFlow Server       | 實驗室團隊       | ✅      | 🔬 實驗室 | ✅       | ✅ 完整 |
| **5️⃣ 雲端協作模式**   | 服務器模式           | 中央服務器       | ✅      | ⚙️ 可部署 | ⚙️       | ✅ 完整 |

## ✨ 核心功能

### 基礎功能（所有模式）

- **檔案管理**：上傳、自動去重（SHA-256）、查詢、下載、刪除
- **標籤系統**：建立標籤、多對多關聯管理
- **結論記錄**：新增、編輯、刪除檔案結論
- **註解系統**：支援任意 JSON 結構的結構化註解
- **推理鏈引擎**：創建和執行自動化分析工作流程
- **視覺化介面**：推理鏈視覺化查看器

### 智能分析（v0.3 已完成）

- **文件識別器** 🔬：自動識別 XRD/EIS/CV/SEM，提取特徵
- **命名管理器** 📝：標準化檔案名稱，學習歷史模式
- **標籤推薦器** 🏷️：規則 + 協同過濾的智能推薦
- **結論生成器** 📄：自動生成分析結論（中英文雙語）

### 網絡功能（模式 2/3/4）

- **科學 API 集成**：Materials Project、PubChem、COD 等
- **雲端備份**：加密上傳至 Google Drive、OneDrive、NAS
- **版本控制**：Git-like 對象存儲，支持回滾

### 協作功能（模式 4/5）

- **身份令牌系統**：實驗室級訪問控制
- **權限管理**：RBAC（Admin、Editor、Viewer）
- **衝突解決**：智能合併 + 用戶選擇
- **審計日誌**：誰在何時做了什麼

### AI 功能（可選配置）

- **本地 LLM**：Ollama 支持（離線可用）
- **雲端 AI**：OpenAI / Claude（可選，可關閉）
- **實驗室 AI**：自建模型部署
- **自動降級**：AI → 規則引擎 fallback

## 🗺️ 開發狀況

### ✅ v0.2.0 - Production Ready（已完成）

- JWT 認證、RBAC 權限控制
- Docker 支持、Redis 緩存
- 測試覆蓋率 95%+

### ✅ v0.3.0 - Intelligent Expansion（已完成）

- 推理鏈引擎（DAG 執行、5 種節點類型）
- 視覺化編輯器和查看器
- 腳本引擎與自動化工作流
- 智能分析模塊（文件識別、命名、標籤、結論）

### ✅ v1.0.0 - Architecture Redesign（已完成 2026-02-24）

- ⭐ **[架構最終決策](docs/architecture/FINAL_ARCHITECTURE_DECISIONS.md)** - 完整 v1.0 設計
- 📋 **[實施清單](docs/roadmap/V1_0_IMPLEMENTATION_CHECKLIST.md)** - 22 週路線圖
- 所有階段已設計並記錄

## 📚 文檔導航

> 📋 **完整索引**: [docs/README.md](docs/README.md) | [docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md)

### 核心文檔

- **[架構最終決策](docs/architecture/FINAL_ARCHITECTURE_DECISIONS.md)** ⭐ - v1.0 設計（2200+ 行）
- [架構概覽](docs/architecture/ARCHITECTURE_OVERVIEW.md)
- [模式對比](docs/architecture/MODE_COMPARISON.md)
- [快速入門指南](docs/getting-started/quick-start.md)

### 功能實現文檔

- [文件識別器](docs/features/intelligence/FILE_IDENTIFIER_IMPLEMENTATION.md) 🔬
- [命名管理器](docs/features/intelligence/NAMING_MANAGER_IMPLEMENTATION.md) 📝
- [標籤推薦器](docs/features/intelligence/TAG_RECOMMENDER_IMPLEMENTATION.md) 🏷️
- [結論生成器](docs/features/intelligence/CONCLUSION_GENERATOR_IMPLEMENTATION.md) 📄
- [推理引擎](docs/features/reasoning/REASONING_ENGINE_ENHANCEMENT.md)
- [國際化模塊](docs/features/i18n/I18N_MODULE.md)（中英雙語）

### 桌面應用

- [構建指南](docs/desktop/DESKTOP_BUILD_GUIDE.md)
- [快速開始](docs/desktop/DESKTOP_QUICKSTART.md)
- [部署指南](docs/desktop/DESKTOP_DEPLOYMENT_GUIDE.md)

### 法律及合規

- [安全政策](SECURITY.md)
- [版權聲明](COPYRIGHT.md) - GNU 通用公共許可證 v3.0
- [第三方聲明](THIRD_PARTY_NOTICES.md)

## 🚀 快速開始

### 本地開發

```bash
# 克隆倉庫
git clone https://github.com/yourusername/labflow.git
cd labflow

# 創建 Python 環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝依賴
pip install -e ".[dev]"

# 運行測試
pytest

# 啟動後端
python -m uvicorn labflow.core.main:app --reload

# 在另一個終端啟動前端
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker-compose up --build
```

## 🔧 環境變數

- `STORAGE_PATH`：檔案儲存根目錄（預設: `data/managed`）
- `DATABASE_URL`：資料庫連接字符串（預設: `sqlite:///./labflow.db`）
- `MAX_UPLOAD_SIZE`：最大上傳大小（預設: 52428800 / 50 MiB）
- `OFFLINE_MODE`：本機離線模式（預設: `true`）
- `SECRET_KEY`：JWT 簽署密鑰（生產環境必須修改）

## 📦 項目結構

```
labflow/
├── core/                    # 後端核心（FastAPI）
├── frontend/               # React 前端
├── electron/              # 桌面應用
├── docs/                  # 文檔
└── tests/                 # 測試套件
```

## 🤝 貢獻指南

歡迎貢獻！請 fork 倉庫，創建功能分支，提交更改，並開啟 Pull Request。

## 📄 許可證

**GNU 通用公共許可證 v3.0（GPL-3.0）** - 見 [LICENSE](LICENSE) 和 [COPYRIGHT.md](COPYRIGHT.md)

## 📞 支持

- **文檔**: [docs/README.md](docs/README.md)
- **問題**: GitHub Issues
- **郵件**: contact@labflow.local

---

**Version**: 1.0.0
**Release Date**: 2026-02-24
**License**: GNU General Public License v3.0 (GPL-3.0)
