# Configuration | 環境配置

---

## 📖 Language / 語言

- [English ↓](#english)
- [中文 ↓](#chinese)

---

<a id="english"></a>

## English

### Overview

LabFlow uses a `.env` file for environment configuration. Copy `.env.example` to `.env` and customize as needed.

```bash
cp .env.example .env
```

---

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment: `development`, `staging`, `production` |
| `DEBUG` | `False` | Enable debug mode (`True` / `False`) |

---

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./labflow.db` | Database connection string |

**Examples:**

```bash
# SQLite (local development)
DATABASE_URL=sqlite:///./labflow.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:password@localhost:5432/labflow

# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost/labflow
```

---

### File Storage Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_PATH` | `data/managed` | Root directory for file storage |
| `MAX_UPLOAD_SIZE` | `52428800` | Maximum file upload size in bytes (default: 50 MiB) |

---

### Security Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(change required)* | JWT signing key — **must be changed in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access token expiry (minutes) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token expiry (days) |

**Generate a secure key:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

> ⚠️ **Important**: Always change `SECRET_KEY` before deploying to production.

---

### Redis / Cache Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `CACHE_TTL` | `3600` | Cache time-to-live in seconds (default: 1 hour) |
| `ENABLE_CACHE` | `true` | Enable/disable caching |

---

### Task Queue (Celery) Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Message broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Task result storage URL |

---

### Logging Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | `text` | Log format: `text` or `json` |
| `LOG_FILE` | `logs/labflow.log` | Log file path |
| `LOG_MAX_BYTES` | `10485760` | Maximum log file size in bytes (default: 10 MB) |
| `LOG_BACKUP_COUNT` | `5` | Number of log backup files to keep |

---

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_TITLE` | `LabFlow API` | API title shown in docs |
| `API_DESCRIPTION` | *(lab system description)* | API description |
| `API_VERSION` | `0.3.0-alpha` | API version string |

---

### Initialization Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_PASSWORD` | `admin123` | Admin password for initial setup (**change this!**) |
| `FORCE_INIT_ADMIN` | `false` | Force re-initialization of admin account |
| `FORCE_INIT_TAGS` | `false` | Force re-initialization of default tags |

---

### Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `OFFLINE_MODE` | `true` | Local-only mode, no cloud sync |
| `ENABLE_BATCH_OPERATIONS` | `true` | Enable bulk file operations |
| `ENABLE_CACHE` | `true` | Enable Redis caching layer |
| `ENABLE_AUDIT_LOG` | `true` | Enable audit logging |

---

### Execution Mode Configuration

Set `OFFLINE_MODE` to configure the execution mode:

| Mode | `OFFLINE_MODE` | Additional Requirements |
|------|---------------|------------------------|
| **Mode 1** — Local Fully Offline | `true` | None |
| **Mode 2** — Local-Connected Privacy | `false` | API keys for scientific DBs |
| **Mode 3** — Local-Connected Full | `false` | Cloud storage credentials |
| **Mode 4A** — Collab Simple | `false` | 3rd-party cloud credentials |
| **Mode 4B** — Collab Full | `false` | LabFlow Server running |
| **Mode 5** — Cloud Collaboration | `false` | Full server infrastructure |

---

### Docker Configuration

When using Docker Compose, environment variables can be set in:
1. `.env` file (recommended)
2. `docker-compose.yml` environment section
3. Shell environment variables (override `.env`)

```yaml
# docker-compose.yml example
services:
  backend:
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/labflow
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
```

---

<a id="chinese"></a>

## 中文

### 概述

LabFlow 使用 `.env` 文件進行環境配置。將 `.env.example` 複製為 `.env` 並根據需要自定義。

```bash
cp .env.example .env
```

---

### 應用程式設置

| 變量 | 默認值 | 描述 |
|------|--------|------|
| `APP_ENV` | `development` | 環境：`development`、`staging`、`production` |
| `DEBUG` | `False` | 啟用調試模式（`True` / `False`） |

---

### 數據庫配置

| 變量 | 默認值 | 描述 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./labflow.db` | 數據庫連接字符串 |

**示例：**

```bash
# SQLite（本地開發）
DATABASE_URL=sqlite:///./labflow.db

# PostgreSQL（生產環境）
DATABASE_URL=postgresql://user:password@localhost:5432/labflow

# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost/labflow
```

---

### 文件存儲配置

| 變量 | 默認值 | 描述 |
|------|--------|------|
| `STORAGE_PATH` | `data/managed` | 文件存儲根目錄 |
| `MAX_UPLOAD_SIZE` | `52428800` | 最大文件上傳大小（字節，默認：50 MiB） |

---

### 安全配置

| 變量 | 默認值 | 描述 |
|------|--------|------|
| `SECRET_KEY` | *（必須修改）* | JWT 簽署密鑰——**生產環境必須修改** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT 訪問令牌過期時間（分鐘） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT 刷新令牌過期時間（天） |

**生成安全密鑰：**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

> ⚠️ **重要**：在部署到生產環境之前，始終更改 `SECRET_KEY`。

---

### Redis / 緩存配置

| 變量 | 默認值 | 描述 |
|------|--------|------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 連接字符串 |
| `CACHE_TTL` | `3600` | 緩存生存時間（秒，默認：1 小時） |
| `ENABLE_CACHE` | `true` | 啟用/禁用緩存 |

---

### 任務隊列（Celery）配置

| 變量 | 默認值 | 描述 |
|------|--------|------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | 消息代理 URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | 任務結果存儲 URL |

---

### 日誌配置

| 變量 | 默認值 | 描述 |
|------|--------|------|
| `LOG_LEVEL` | `INFO` | 日誌級別：`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL` |
| `LOG_FORMAT` | `text` | 日誌格式：`text` 或 `json` |
| `LOG_FILE` | `logs/labflow.log` | 日誌文件路徑 |
| `LOG_MAX_BYTES` | `10485760` | 最大日誌文件大小（字節，默認：10 MB） |
| `LOG_BACKUP_COUNT` | `5` | 保留的備份日誌文件數量 |

---

### API 配置

| 變量 | 默認值 | 描述 |
|------|--------|------|
| `API_TITLE` | `LabFlow API` | 文檔中顯示的 API 標題 |
| `API_DESCRIPTION` | *（實驗室系統描述）* | API 描述 |
| `API_VERSION` | `0.3.0-alpha` | API 版本字符串 |

---

### 初始化配置

| 變量 | 默認值 | 描述 |
|------|--------|------|
| `ADMIN_PASSWORD` | `admin123` | 初始設置的管理員密碼（**請修改此密碼！**） |
| `FORCE_INIT_ADMIN` | `false` | 強制重新初始化管理員帳號 |
| `FORCE_INIT_TAGS` | `false` | 強制重新初始化默認標籤 |

---

### 功能開關

| 變量 | 默認值 | 描述 |
|------|--------|------|
| `OFFLINE_MODE` | `true` | 僅本地模式，無雲端同步 |
| `ENABLE_BATCH_OPERATIONS` | `true` | 啟用批量文件操作 |
| `ENABLE_CACHE` | `true` | 啟用 Redis 緩存層 |
| `ENABLE_AUDIT_LOG` | `true` | 啟用審計日誌 |

---

### 運行模式配置

設置 `OFFLINE_MODE` 以配置運行模式：

| 模式 | `OFFLINE_MODE` | 額外要求 |
|------|---------------|----------|
| **模式 1** — 本地完全離網 | `true` | 無 |
| **模式 2** — 本地聯網隱私版 | `false` | 科學數據庫 API 密鑰 |
| **模式 3** — 本地聯網全面版 | `false` | 雲存儲憑證 |
| **模式 4A** — 協作簡化版 | `false` | 第三方雲端憑證 |
| **模式 4B** — 協作完整版 | `false` | LabFlow 服務器在運行 |
| **模式 5** — 雲端協作模式 | `false` | 完整服務器基礎設施 |

---

### Docker 配置

使用 Docker Compose 時，環境變量可以設置在：
1. `.env` 文件（推薦）
2. `docker-compose.yml` 的 environment 部分
3. Shell 環境變量（覆蓋 `.env`）

```yaml
# docker-compose.yml 示例
services:
  backend:
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/labflow
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
```

---

*← [Features](Features) | [API Reference →](API-Reference)*
