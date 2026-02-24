# Installation Guide | 安裝指南

---

## 📖 Language / 語言

- [English ↓](#english)
- [中文 ↓](#chinese)

---

<a id="english"></a>

## English

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.9+ | Required for backend |
| Node.js | 16+ | Required for frontend |
| Git | Any | For cloning the repo |
| Docker | 20+ | Optional, for containerized deployment |

### Method 1: Local Development

#### Step 1 — Clone the Repository

```bash
git clone https://github.com/tico-Lin/labflow.git
cd labflow
```

#### Step 2 — Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

#### Step 3 — Install Python Dependencies

```bash
# Install production + development dependencies
pip install -e ".[dev]"

# Or install only production dependencies
pip install -r requirements.txt
```

#### Step 4 — Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings (see Configuration page for details)
```

#### Step 5 — Initialize the Database

```bash
python -m labflow.core.init_db
```

#### Step 6 — Start the Backend

```bash
python -m uvicorn labflow.core.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`
Interactive API docs: `http://localhost:8000/docs`

#### Step 7 — Start the Frontend

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at: `http://localhost:5173`

---

### Method 2: Docker Compose (Recommended for Production)

```bash
# Clone repository
git clone https://github.com/tico-Lin/labflow.git
cd labflow

# Configure environment
cp .env.example .env
# Edit .env as needed

# Start all services
docker-compose up --build

# Run in background (detached)
docker-compose up -d --build
```

Services started:
- **Backend API**: `http://localhost:8000`
- **Frontend**: `http://localhost:3000`

---

### Verifying the Installation

```bash
# Run the test suite
pytest

# Check the API is running
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok", "version": "1.0.0"}
```

---

### Choosing an Execution Mode

LabFlow supports 5 execution modes. Set `OFFLINE_MODE` in your `.env` file:

| Mode | `OFFLINE_MODE` | Use Case |
|------|---------------|----------|
| 1 — Local Fully Offline | `true` | Maximum privacy, no network |
| 2 — Local-Connected Privacy | `false` (limited) | Query scientific DBs only |
| 3 — Local-Connected Full | `false` | Full network features |
| 4A — Collab Simple | `false` | Small team, 3rd-party cloud |
| 4B — Collab Full | `false` | Lab team, LabFlow Server |
| 5 — Cloud Collaboration | `false` | Central server mode |

---

<a id="chinese"></a>

## 中文

### 環境要求

| 要求 | 版本 | 說明 |
|------|------|------|
| Python | 3.9+ | 後端必需 |
| Node.js | 16+ | 前端必需 |
| Git | 任意版本 | 克隆倉庫 |
| Docker | 20+ | 可選，用於容器化部署 |

### 方式一：本地開發

#### 第一步 — 克隆倉庫

```bash
git clone https://github.com/tico-Lin/labflow.git
cd labflow
```

#### 第二步 — 建立 Python 虛擬環境

```bash
# 創建虛擬環境
python -m venv venv

# 啟動（Linux/macOS）
source venv/bin/activate

# 啟動（Windows）
venv\Scripts\activate
```

#### 第三步 — 安裝 Python 依賴

```bash
# 安裝生產 + 開發依賴
pip install -e ".[dev]"

# 或只安裝生產依賴
pip install -r requirements.txt
```

#### 第四步 — 配置環境變量

```bash
# 複製示例環境配置文件
cp .env.example .env

# 編輯 .env 文件（詳見環境配置頁面）
```

#### 第五步 — 初始化數據庫

```bash
python -m labflow.core.init_db
```

#### 第六步 — 啟動後端

```bash
python -m uvicorn labflow.core.main:app --reload --host 0.0.0.0 --port 8000
```

API 地址：`http://localhost:8000`
交互式 API 文檔：`http://localhost:8000/docs`

#### 第七步 — 啟動前端

開啟**新的終端**：

```bash
cd frontend
npm install
npm run dev
```

前端地址：`http://localhost:5173`

---

### 方式二：Docker Compose（推薦用於生產環境）

```bash
# 克隆倉庫
git clone https://github.com/tico-Lin/labflow.git
cd labflow

# 配置環境
cp .env.example .env
# 根據需要編輯 .env

# 啟動所有服務
docker-compose up --build

# 後台運行（守護進程模式）
docker-compose up -d --build
```

啟動後的服務：
- **後端 API**：`http://localhost:8000`
- **前端**：`http://localhost:3000`

---

### 驗證安裝

```bash
# 運行測試套件
pytest

# 檢查 API 是否運行
curl http://localhost:8000/health
```

期望的響應：
```json
{"status": "ok", "version": "1.0.0"}
```

---

### 選擇運行模式

LabFlow 支持 5 種運行模式。在 `.env` 文件中設置 `OFFLINE_MODE`：

| 模式 | `OFFLINE_MODE` | 使用場景 |
|------|---------------|----------|
| 1 — 本地完全離網 | `true` | 最高隱私，無網絡 |
| 2 — 本地聯網隱私版 | `false`（限定） | 僅查詢科學數據庫 |
| 3 — 本地聯網全面版 | `false` | 完整網絡功能 |
| 4A — 協作簡化版 | `false` | 小團隊，第三方雲端 |
| 4B — 協作完整版 | `false` | 實驗室團隊，LabFlow 服務器 |
| 5 — 雲端協作模式 | `false` | 中央服務器模式 |

---

*← [Home](Home) | [Architecture →](Architecture)*
