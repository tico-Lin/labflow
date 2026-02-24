# FAQ | 常見問題

---

## 📖 Language / 語言

- [English ↓](#english)
- [中文 ↓](#chinese)

---

<a id="english"></a>

## English

### General Questions

#### What is LabFlow?

LabFlow is an intelligent laboratory data management system for scientific researchers. It helps you organize experimental files, apply tags, record analysis conclusions, and build automated analysis workflows — all while working offline if needed.

#### Is LabFlow free?

Yes. LabFlow is open-source software released under the **GNU General Public License v3.0 (GPL-3.0)**. It is free to use, modify, and distribute, provided that derivative works are also released under GPL-3.0.

#### What operating systems are supported?

LabFlow supports:
- **Windows** 10/11
- **macOS** 11+
- **Linux** (Ubuntu 20.04+, Debian, Fedora, etc.)

The backend and CLI work on any platform with Python 3.9+. The desktop app (Electron) is available for Windows, macOS, and Linux.

#### What file types are supported?

LabFlow can store and manage **any file type**. Additionally, the intelligent analysis modules can identify and extract metadata from:
- XRD files (`.xy`, `.xrdml`, `.ras`)
- EIS files (`.mpt`, `.dta`, `.txt`)
- CV files (`.mpt`, `.txt`)
- SEM images (`.tif`, `.jpg`, and common image formats)

---

### Installation & Setup

#### How do I get started quickly?

See the [Installation](Installation) page. The fastest way is:

```bash
git clone https://github.com/tico-Lin/labflow.git
cd labflow
pip install -e ".[dev]"
python -m uvicorn labflow.core.main:app --reload
```

#### Can I run LabFlow without Docker?

Yes. Docker is optional. You can run LabFlow directly with Python and Node.js. See [Installation](Installation) for details.

#### What is the default admin password?

The default admin password is `admin123`. **Change this immediately** in your `.env` file before using LabFlow in any shared or production environment.

#### How do I change the database from SQLite to PostgreSQL?

Update the `DATABASE_URL` in your `.env` file:

```bash
DATABASE_URL=postgresql://username:password@localhost:5432/labflow
```

Then run the database migration:

```bash
alembic upgrade head
```

---

### Features & Usage

#### How does file deduplication work?

When you upload a file, LabFlow computes its **SHA-256 hash**. If a file with the same hash already exists in the database, the upload is rejected with a "duplicate file" error. This prevents wasting storage on identical files.

#### What is a "Reasoning Chain"?

A Reasoning Chain is a visual workflow editor for automating analysis tasks. You drag and drop "nodes" (e.g., Load Data → Transform → Calculate → Output) to build a pipeline. Once built, you can run it on any compatible dataset with a single click.

#### Can LabFlow work completely offline?

Yes. Set `OFFLINE_MODE=true` in your `.env` file (this is the default). In offline mode, LabFlow operates entirely locally with no network requests. All features except cloud backup and scientific API queries work offline.

#### Does LabFlow support multiple languages?

Yes. LabFlow supports **Chinese (Traditional/Simplified) and English**. The language can be set per-user or system-wide through the i18n settings.

#### How do I back up my data?

Options include:
1. **Cloud Backup** (Modes 3/4/5): Encrypted upload to Google Drive, OneDrive, or NAS
2. **Manual**: Copy the `data/managed/` directory and the `labflow.db` SQLite file
3. **Docker volumes**: Back up mounted volumes using Docker's backup tools

---

### Performance & Scalability

#### How many files can LabFlow handle?

LabFlow is designed for laboratory-scale data. With SQLite, it handles tens of thousands of files comfortably. For larger datasets or multi-user environments, switch to PostgreSQL.

#### Why is the first file analysis slow?

If using a local LLM (Ollama), the model loads into memory on first use. Subsequent calls are faster. To disable AI analysis, set `OFFLINE_MODE=true` or configure the AI backend appropriately.

#### Does LabFlow support multi-user access?

Yes. In **Modes 4B and 5**, LabFlow supports multiple users with role-based access control (Admin, Editor, Viewer). JWT tokens provide secure authentication.

---

### Troubleshooting

#### The API returns a 401 Unauthorized error

Your JWT token has expired. Re-authenticate:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

Use the new `access_token` in subsequent requests.

#### File upload fails with "File too large"

Increase `MAX_UPLOAD_SIZE` in your `.env` file:

```bash
# Set to 200 MiB
MAX_UPLOAD_SIZE=209715200
```

Then restart the server.

#### The database is not found

Ensure the `DATABASE_URL` path is correct. For SQLite, the path is relative to the working directory. The database file is created automatically on first run.

#### Tests fail with import errors

Ensure you've installed development dependencies:

```bash
pip install -r dev-requirements.txt
# or
pip install -e ".[dev]"
```

---

### Security

#### Is my data encrypted?

- **In transit**: All API communication can be encrypted with TLS (configure your reverse proxy or load balancer).
- **At rest**: Cloud backups are AES-256 encrypted before upload.
- **Local files**: Local storage is not encrypted by default — use disk encryption (e.g., BitLocker, FileVault, LUKS) if needed.

#### Can I disable the AI features?

Yes. Set `OFFLINE_MODE=true` to disable all AI features. The system will fall back to rule-based analysis only.

#### How do I report a security vulnerability?

Please see [SECURITY.md](../SECURITY.md) for responsible disclosure guidelines. Do **not** open a public GitHub issue for security vulnerabilities.

---

<a id="chinese"></a>

## 中文

### 一般問題

#### LabFlow 是什麼？

LabFlow 是一個為科學研究人員設計的智能實驗室數據管理系統。它幫助您整理實驗文件、應用標籤、記錄分析結論，並構建自動化分析工作流程——在需要時可完全離線工作。

#### LabFlow 是免費的嗎？

是的。LabFlow 是在 **GNU 通用公共許可證 v3.0（GPL-3.0）** 下發布的開源軟件。可以免費使用、修改和分發，但前提是衍生作品也需在 GPL-3.0 下發布。

#### 支持哪些操作系統？

LabFlow 支持：
- **Windows** 10/11
- **macOS** 11+
- **Linux**（Ubuntu 20.04+、Debian、Fedora 等）

後端和 CLI 可在任何帶有 Python 3.9+ 的平台上運行。桌面應用（Electron）適用於 Windows、macOS 和 Linux。

#### 支持哪些文件類型？

LabFlow 可以存儲和管理**任何文件類型**。此外，智能分析模塊可以識別並提取以下文件的元數據：
- XRD 文件（`.xy`、`.xrdml`、`.ras`）
- EIS 文件（`.mpt`、`.dta`、`.txt`）
- CV 文件（`.mpt`、`.txt`）
- SEM 圖像（`.tif`、`.jpg` 及常見圖像格式）

---

### 安裝與設置

#### 如何快速開始？

請參閱[安裝指南](Installation)頁面。最快的方式是：

```bash
git clone https://github.com/tico-Lin/labflow.git
cd labflow
pip install -e ".[dev]"
python -m uvicorn labflow.core.main:app --reload
```

#### 可以不用 Docker 運行 LabFlow 嗎？

可以。Docker 是可選的。您可以直接使用 Python 和 Node.js 運行 LabFlow。詳見[安裝指南](Installation)。

#### 默認管理員密碼是什麼？

默認管理員密碼是 `admin123`。在任何共享或生產環境中使用 LabFlow 之前，請**立即**在 `.env` 文件中更改此密碼。

#### 如何將數據庫從 SQLite 改為 PostgreSQL？

在 `.env` 文件中更新 `DATABASE_URL`：

```bash
DATABASE_URL=postgresql://username:password@localhost:5432/labflow
```

然後運行數據庫遷移：

```bash
alembic upgrade head
```

---

### 功能與使用

#### 文件去重是如何工作的？

當您上傳文件時，LabFlow 會計算其 **SHA-256 哈希**。如果數據庫中已存在相同哈希的文件，上傳將被拒絕並提示"重複文件"錯誤。這防止了在相同文件上浪費存儲空間。

#### 什麼是"推理鏈"？

推理鏈是一個可視化工作流編輯器，用於自動化分析任務。您拖放"節點"（例如，加載數據 → 轉換 → 計算 → 輸出）來構建管道。構建完成後，只需點擊一次即可在任何兼容數據集上運行。

#### LabFlow 可以完全離線工作嗎？

可以。在 `.env` 文件中設置 `OFFLINE_MODE=true`（這是默認值）。在離線模式下，LabFlow 完全在本地運行，沒有任何網絡請求。除雲端備份和科學 API 查詢外，所有功能均可離線使用。

#### LabFlow 支持多語言嗎？

是的。LabFlow 支持**中文（繁體/簡體）和英文**。語言可以通過 i18n 設置按用戶或系統範圍設置。

#### 如何備份我的數據？

選項包括：
1. **雲端備份**（模式 3/4/5）：加密上傳到 Google Drive、OneDrive 或 NAS
2. **手動備份**：複製 `data/managed/` 目錄和 `labflow.db` SQLite 文件
3. **Docker 卷**：使用 Docker 備份工具備份掛載的卷

---

### 性能與可擴展性

#### LabFlow 可以處理多少文件？

LabFlow 為實驗室規模的數據設計。使用 SQLite 時，可以輕鬆處理數萬個文件。對於更大的數據集或多用戶環境，請切換到 PostgreSQL。

#### 為什麼第一次文件分析很慢？

如果使用本地 LLM（Ollama），模型在首次使用時需要加載到內存中。後續調用速度更快。要禁用 AI 分析，請設置 `OFFLINE_MODE=true` 或適當配置 AI 後端。

#### LabFlow 是否支持多用戶訪問？

是的。在**模式 4B 和 5** 中，LabFlow 支持多用戶基於角色的訪問控制（Admin、Editor、Viewer）。JWT 令牌提供安全認證。

---

### 故障排除

#### API 返回 401 Unauthorized 錯誤

您的 JWT 令牌已過期。重新認證：

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

在後續請求中使用新的 `access_token`。

#### 文件上傳失敗，提示"文件太大"

在 `.env` 文件中增加 `MAX_UPLOAD_SIZE`：

```bash
# 設置為 200 MiB
MAX_UPLOAD_SIZE=209715200
```

然後重新啟動服務器。

#### 找不到數據庫

確保 `DATABASE_URL` 路徑正確。對於 SQLite，路徑相對於工作目錄。數據庫文件在首次運行時自動創建。

#### 測試因導入錯誤而失敗

確保已安裝開發依賴：

```bash
pip install -r dev-requirements.txt
# 或
pip install -e ".[dev]"
```

---

### 安全性

#### 我的數據是加密的嗎？

- **傳輸中**：所有 API 通信可以使用 TLS 加密（配置您的反向代理或負載均衡器）。
- **靜態存儲**：雲端備份在上傳前使用 AES-256 加密。
- **本地文件**：默認情況下本地存儲不加密——如需要請使用磁盤加密（例如 BitLocker、FileVault、LUKS）。

#### 我可以禁用 AI 功能嗎？

可以。設置 `OFFLINE_MODE=true` 以禁用所有 AI 功能。系統將退回到僅使用規則引擎進行分析。

#### 如何報告安全漏洞？

請查閱 [SECURITY.md](../SECURITY.md) 了解負責任披露指南。**不要**為安全漏洞在 GitHub 上開啟公開 Issue。

---

*← [Contributing](Contributing) | [Home →](Home)*
