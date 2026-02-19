# LabFlow

LabFlow 是一個簡易的實驗室資料管理後端（FastAPI + SQLAlchemy + SQLite）。

快速開始
請參考 [docs/getting-started/quick-start.md](docs/getting-started/quick-start.md) 取得本地與 Docker 的完整步驟。

## 核心功能

- **檔案管理**：上傳、自動去重（SHA-256）、查詢、下載、刪除。
- **標籤系統**：建立標籤、多對多關聯管理。
- **結論記錄**：新增、編輯、刪除檔案結論。
- **註解系統**：支援任意 JSON 結構的結構化註解。
- **資料同步**：一鍵刷新資料庫與實體檔案的同步狀態。
- **身份驗證**：基於 JWT 的用戶註冊、登錄和 RBAC (Admin, Editor, Viewer)。
- **推理鏈引擎** (v0.3): 創建和執行自動化分析工作流程。
- **視覺化介面** (v0.3): 只讀模式的推理鏈視覺化查看器，支持執行歷史和結果展示。
- **國際化 (i18n)** 🌐 **NEW**: 完整的多語言支持，內建中文和英文，可擴展至其他語言。

## Roadmap

- **v0.2.0**: ✅ **Production Ready**. Includes JWT authentication, role-based access control (RBAC), Docker support, performance optimizations with Redis caching, and expanded test coverage.

- **v0.3.0 (In Progress)**: 🚀 **Intelligent Expansion**. The next major version focuses on a **Reasoning Engine** for automated analysis workflows. Current status:
  - **Reasoning Engine Core**: ✅ Implemented (node types, DAG execution, handlers).
  - **Visual Workflow Viewer**: ✅ **NEW** - Read-only visualization interface for reasoning chains (2026-02-17).
  - **Visual Workflow Editor**: Implemented (basic editing capabilities).
  - **Scripting Engine**: Pending (framework only).
  - **Automation**: Pending.

## Integration Summary

- **Fiji**: Image analysis workflows via adapter (macros/scripts), results stored as artifacts + conclusions.
- **GSAS-II**: Diffraction analysis via scripted adapter, outputs captured as structured metadata + reports.
- **Open source compliance**: Central notices and license tracking are required for any bundled tools.

## Optional Adapter Dependencies

部分整合工具（例如 scikit-image、pyFAI、impedance.py）屬於選配依賴，未安裝時對應 adapter 會回傳 failed 與錯誤訊息。

See integration requirements and implementation notes:

- docs/integrations/requirements.md
- docs/integrations/open-source-components.md
- THIRD_PARTY_NOTICES.md

## Testing

To run the full test suite, use the following command:

```powershell
pytest
```

To run only specific tests, you can use markers:

```powershell
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

To generate a test coverage report, run:

```powershell
pytest --cov=app --cov-report=html
```

## 環境變數

- `STORAGE_PATH`：檔案儲存根目錄，預設 `data/managed`
- `DATABASE_URL`：資料庫連線字串，預設使用 `sqlite:///./labflow.db`
- `MAX_UPLOAD_SIZE`：上傳檔案大小上限（位元組），預設 `52428800`（50 MiB）
- `OFFLINE_MODE`：本地離線模式（`true/false`），`true` 代表僅本機運行、無雲端同步
- `SECRET_KEY`：JWT 簽署密鑰（必須在生產環境修改）
- `ACCESS_TOKEN_EXPIRE_MINUTES`：Access Token 過期時間，預設 30 分鐘
- `REFRESH_TOKEN_EXPIRE_DAYS`：Refresh Token 過期時間，預設 7 天

## 離線部署

- 預設為本地離線模式（`OFFLINE_MODE=true`），僅使用本機資料庫與檔案系統。
- 前端會在頂部顯示 `Local-only` 標記（由 `/health` 回傳的 `offline_mode` 決定）。

## Documentation

For more detailed information, see docs/README.md:

- **[Quick Start](docs/getting-started/quick-start.md)**: Local and Docker setup steps.
- **[API Reference](docs/specs/api.md)**: Detailed descriptions of all API endpoints.
- **[Architecture](docs/architecture/system-architecture.md)**: An overview of the system architecture and design principles.
- **[Data Schema](docs/architecture/data-schema.md)**: Details on the database models.
- **[Visualization User Guide](docs/USER_GUIDE_VISUALIZATION.md)**: How to use the reasoning chain visualization interface.
- **[Internationalization (i18n)](docs/I18N_MODULE.md)**: 🌐 **NEW** - Multi-language support guide (Chinese/English + extensible).
- **[Frontend Setup](frontend/FRONTEND_SETUP.md)**: Frontend installation and setup guide.
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)**: Summary of the visualization interface implementation.
