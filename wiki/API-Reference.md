# API Reference | API 參考

---

## 📖 Language / 語言

- [English ↓](#english)
- [中文 ↓](#chinese)

---

<a id="english"></a>

## English

### Overview

LabFlow provides a REST API built with FastAPI. Interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Authentication

Most endpoints require a JWT Bearer token.

#### Login

```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Refresh Token

```http
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

#### Use Token in Requests

```http
GET /files/
Authorization: Bearer <access_token>
```

---

### Endpoints

#### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info and version |
| `GET` | `/health` | Health check |

#### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users/me` | Get current user info |
| `GET` | `/users/` | List all users (Admin only) |
| `PUT` | `/users/{user_id}` | Update a user |
| `DELETE` | `/users/{user_id}` | Delete a user (Admin only) |

#### Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/files/` | Upload a file |
| `GET` | `/files/` | List all files |
| `GET` | `/files/search` | Search files by query |
| `GET` | `/files/{file_id}` | Get file details |
| `GET` | `/files/{file_id}/download` | Download a file |
| `DELETE` | `/files/{file_id}` | Delete a file |
| `POST` | `/files/batch-upload` | Upload multiple files |
| `POST` | `/files/batch-delete` | Delete multiple files |

**Upload a file:**

```http
POST /files/
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@/path/to/experiment.xy
```

**Search files:**

```http
GET /files/search?q=XRD&tag=sample-01&file_type=xrd
Authorization: Bearer <token>
```

#### Tags

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/tags/` | List all tags |
| `POST` | `/tags/` | Create a tag |
| `POST` | `/files/{file_id}/tags` | Add tags to a file |
| `DELETE` | `/files/{file_id}/tags/{tag_id}` | Remove tag from file |
| `POST` | `/tags/batch-create` | Create multiple tags |

**Create a tag:**

```http
POST /tags/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "XRD-Analysis",
  "description": "X-ray diffraction analysis files"
}
```

#### Conclusions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/files/{file_id}/conclusions/` | Get conclusions for a file |
| `PUT` | `/conclusions/{conclusion_id}` | Update a conclusion |
| `DELETE` | `/conclusions/{conclusion_id}` | Delete a conclusion |

#### Annotations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/files/{file_id}/annotations/` | Get annotations for a file |
| `POST` | `/files/{file_id}/annotations/` | Add annotation to file |

**Add an annotation:**

```http
POST /files/{file_id}/annotations/
Authorization: Bearer <token>
Content-Type: application/json

{
  "key": "synthesis_temperature",
  "value": {"celsius": 800, "duration_hours": 12}
}
```

#### Reasoning Chains

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/reasoning-chains` | List all reasoning chains |
| `POST` | `/reasoning-chains` | Create a reasoning chain |
| `GET` | `/reasoning-chains/{chain_id}` | Get chain details |
| `PUT` | `/reasoning-chains/{chain_id}` | Update a chain |
| `DELETE` | `/reasoning-chains/{chain_id}` | Delete a chain |
| `POST` | `/reasoning-chains/{chain_id}/execute` | Execute a chain |
| `GET` | `/executions/{execution_id}` | Get execution result |

**Execute a reasoning chain:**

```http
POST /reasoning-chains/{chain_id}/execute
Authorization: Bearer <token>
Content-Type: application/json

{
  "input_data": {"file_id": "abc123"}
}
```

#### Scripts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/scripts` | List all scripts |
| `POST` | `/scripts` | Create a script |
| `GET` | `/scripts/{script_id}` | Get script details |
| `PUT` | `/scripts/{script_id}` | Update a script |
| `DELETE` | `/scripts/{script_id}` | Delete a script |
| `POST` | `/scripts/{script_id}/execute` | Execute a script |

#### Intelligence / Classification

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/classification/supported-types` | List supported file types |
| `POST` | `/classify` | Classify a file |
| `POST` | `/naming/suggest` | Suggest standardized filename |
| `POST` | `/tags/recommend` | Get tag recommendations |
| `POST` | `/conclusions/generate` | Auto-generate a conclusion |

#### Internationalization

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/i18n/locales` | List available locales |
| `GET` | `/i18n/translations/{locale}` | Get all translations for locale |
| `GET` | `/i18n/translate/{locale}/{key}` | Translate a specific key |

#### Administration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/admin/sync-files/` | Sync file system state |
| `GET` | `/admin/file-status/` | Get file system status |

---

### Response Formats

#### File Object

```json
{
  "id": "abc123",
  "filename": "sample_XRD_20260101.xy",
  "file_type": "xrd",
  "size": 15360,
  "sha256": "d4e5f6...",
  "created_at": "2026-01-01T10:00:00Z",
  "tags": [{"id": 1, "name": "XRD-Analysis"}],
  "conclusions": [],
  "annotations": []
}
```

#### Tag Object

```json
{
  "id": 1,
  "name": "XRD-Analysis",
  "description": "X-ray diffraction analysis files",
  "created_at": "2026-01-01T10:00:00Z"
}
```

#### Error Response

```json
{
  "detail": "File not found",
  "status_code": 404
}
```

---

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | OK — Request succeeded |
| `201` | Created — Resource created successfully |
| `204` | No Content — Deleted successfully |
| `400` | Bad Request — Invalid input |
| `401` | Unauthorized — Authentication required |
| `403` | Forbidden — Insufficient permissions |
| `404` | Not Found — Resource does not exist |
| `409` | Conflict — Duplicate resource |
| `422` | Unprocessable Entity — Validation error |
| `500` | Internal Server Error — Server-side error |

---

<a id="chinese"></a>

## 中文

### 概述

LabFlow 提供基於 FastAPI 構建的 REST API。交互式 API 文檔可在以下地址訪問：

- **Swagger UI**：`http://localhost:8000/docs`
- **ReDoc**：`http://localhost:8000/redoc`

### 認證

大多數端點需要 JWT Bearer 令牌。

#### 登錄

```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

**響應：**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### 刷新令牌

```http
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

#### 在請求中使用令牌

```http
GET /files/
Authorization: Bearer <access_token>
```

---

### API 端點

#### 系統

| 方法 | 端點 | 描述 |
|------|------|------|
| `GET` | `/` | API 信息和版本 |
| `GET` | `/health` | 健康檢查 |

#### 用戶

| 方法 | 端點 | 描述 |
|------|------|------|
| `GET` | `/users/me` | 獲取當前用戶信息 |
| `GET` | `/users/` | 列出所有用戶（僅限 Admin） |
| `PUT` | `/users/{user_id}` | 更新用戶 |
| `DELETE` | `/users/{user_id}` | 刪除用戶（僅限 Admin） |

#### 文件

| 方法 | 端點 | 描述 |
|------|------|------|
| `POST` | `/files/` | 上傳文件 |
| `GET` | `/files/` | 列出所有文件 |
| `GET` | `/files/search` | 按查詢搜索文件 |
| `GET` | `/files/{file_id}` | 獲取文件詳情 |
| `GET` | `/files/{file_id}/download` | 下載文件 |
| `DELETE` | `/files/{file_id}` | 刪除文件 |
| `POST` | `/files/batch-upload` | 批量上傳文件 |
| `POST` | `/files/batch-delete` | 批量刪除文件 |

**上傳文件：**

```http
POST /files/
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@/path/to/experiment.xy
```

**搜索文件：**

```http
GET /files/search?q=XRD&tag=sample-01&file_type=xrd
Authorization: Bearer <token>
```

#### 標籤

| 方法 | 端點 | 描述 |
|------|------|------|
| `GET` | `/tags/` | 列出所有標籤 |
| `POST` | `/tags/` | 創建標籤 |
| `POST` | `/files/{file_id}/tags` | 為文件添加標籤 |
| `DELETE` | `/files/{file_id}/tags/{tag_id}` | 從文件移除標籤 |
| `POST` | `/tags/batch-create` | 批量創建標籤 |

**創建標籤：**

```http
POST /tags/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "XRD-Analysis",
  "description": "X射線衍射分析文件"
}
```

#### 結論

| 方法 | 端點 | 描述 |
|------|------|------|
| `GET` | `/files/{file_id}/conclusions/` | 獲取文件結論 |
| `PUT` | `/conclusions/{conclusion_id}` | 更新結論 |
| `DELETE` | `/conclusions/{conclusion_id}` | 刪除結論 |

#### 註解

| 方法 | 端點 | 描述 |
|------|------|------|
| `GET` | `/files/{file_id}/annotations/` | 獲取文件註解 |
| `POST` | `/files/{file_id}/annotations/` | 為文件添加註解 |

**添加註解：**

```http
POST /files/{file_id}/annotations/
Authorization: Bearer <token>
Content-Type: application/json

{
  "key": "synthesis_temperature",
  "value": {"celsius": 800, "duration_hours": 12}
}
```

#### 推理鏈

| 方法 | 端點 | 描述 |
|------|------|------|
| `GET` | `/reasoning-chains` | 列出所有推理鏈 |
| `POST` | `/reasoning-chains` | 創建推理鏈 |
| `GET` | `/reasoning-chains/{chain_id}` | 獲取推理鏈詳情 |
| `PUT` | `/reasoning-chains/{chain_id}` | 更新推理鏈 |
| `DELETE` | `/reasoning-chains/{chain_id}` | 刪除推理鏈 |
| `POST` | `/reasoning-chains/{chain_id}/execute` | 執行推理鏈 |
| `GET` | `/executions/{execution_id}` | 獲取執行結果 |

**執行推理鏈：**

```http
POST /reasoning-chains/{chain_id}/execute
Authorization: Bearer <token>
Content-Type: application/json

{
  "input_data": {"file_id": "abc123"}
}
```

#### 腳本

| 方法 | 端點 | 描述 |
|------|------|------|
| `GET` | `/scripts` | 列出所有腳本 |
| `POST` | `/scripts` | 創建腳本 |
| `GET` | `/scripts/{script_id}` | 獲取腳本詳情 |
| `PUT` | `/scripts/{script_id}` | 更新腳本 |
| `DELETE` | `/scripts/{script_id}` | 刪除腳本 |
| `POST` | `/scripts/{script_id}/execute` | 執行腳本 |

#### 智能分析 / 文件分類

| 方法 | 端點 | 描述 |
|------|------|------|
| `GET` | `/classification/supported-types` | 列出支持的文件類型 |
| `POST` | `/classify` | 分類文件 |
| `POST` | `/naming/suggest` | 建議標準化文件名 |
| `POST` | `/tags/recommend` | 獲取標籤推薦 |
| `POST` | `/conclusions/generate` | 自動生成結論 |

#### 國際化

| 方法 | 端點 | 描述 |
|------|------|------|
| `GET` | `/i18n/locales` | 列出可用語言環境 |
| `GET` | `/i18n/translations/{locale}` | 獲取語言環境的所有翻譯 |
| `GET` | `/i18n/translate/{locale}/{key}` | 翻譯特定鍵 |

#### 管理

| 方法 | 端點 | 描述 |
|------|------|------|
| `POST` | `/admin/sync-files/` | 同步文件系統狀態 |
| `GET` | `/admin/file-status/` | 獲取文件系統狀態 |

---

### 響應格式

#### 文件對象

```json
{
  "id": "abc123",
  "filename": "sample_XRD_20260101.xy",
  "file_type": "xrd",
  "size": 15360,
  "sha256": "d4e5f6...",
  "created_at": "2026-01-01T10:00:00Z",
  "tags": [{"id": 1, "name": "XRD-Analysis"}],
  "conclusions": [],
  "annotations": []
}
```

#### 標籤對象

```json
{
  "id": 1,
  "name": "XRD-Analysis",
  "description": "X射線衍射分析文件",
  "created_at": "2026-01-01T10:00:00Z"
}
```

#### 錯誤響應

```json
{
  "detail": "File not found",
  "status_code": 404
}
```

---

### HTTP 狀態碼

| 代碼 | 含義 |
|------|------|
| `200` | OK — 請求成功 |
| `201` | Created — 資源創建成功 |
| `204` | No Content — 刪除成功 |
| `400` | Bad Request — 無效輸入 |
| `401` | Unauthorized — 需要認證 |
| `403` | Forbidden — 權限不足 |
| `404` | Not Found — 資源不存在 |
| `409` | Conflict — 重複資源 |
| `422` | Unprocessable Entity — 驗證錯誤 |
| `500` | Internal Server Error — 服務器端錯誤 |

---

*← [Configuration](Configuration) | [Contributing →](Contributing)*
