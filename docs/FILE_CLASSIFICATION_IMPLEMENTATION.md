# 檔案自動分類功能實現總結

## 實現日期

2026-02-17

## 對應任務

LabFlow v0.3 階段 1 - 第 8-9 週：檔案自動分類 (規則引擎 + API)

## 已完成內容

### 1. 規則配置文件 ✅

**文件**: `config/file_classification_rules.yml`

- 定義了多種檔案類型的分類規則 (XRD, SEM, EIS, CV, Battery Test)
- 支援正則表達式模式匹配
- 包含元數據提取規則
- 自動標籤生成邏輯
- 標籤同義詞映射
- 元數據驗證規則

**支援的檔案類型**:

- XRD (X-ray Diffraction)
- SEM (Scanning Electron Microscopy)
- EIS (Electrochemical Impedance Spectroscopy)
- CV (Cyclic Voltammetry)
- Battery Test (充放電測試)
- 以及更多通用類型 (Excel, Image, Data, PDF等)

### 2. 分類服務 ✅

**文件**: `app/services/classification_service.py` (已存在)

**核心功能**:

- `classify_file()`: 單檔案分類
- `batch_classify()`: 批量分類
- `get_supported_types()`: 查詢支援的檔案類型
- `get_classification_stats()`: 統計信息

**分類邏輯**:

- 基於檔案擴展名的分類 (置信度 0.8)
- 基於檔名關鍵字的分類 (置信度 0.95)
- 元數據提取 (樣品名、日期、儀器類型、序號等)
- 自動標籤生成 (基於檔案類型、樣品信息、日期、相位等)

### 3. Schema 定義 ✅

**文件**: `app/schemas.py` (已存在相關 Schema)

**定義的 Schema**:

- `ClassificationResult`: 分類結果
- `FileClassificationResponse`: 檔案分類響應
- `BatchClassificationRequest`: 批量分類請求
- `BatchClassificationResponse`: 批量分類響應
- `ClassificationStatsResponse`: 分類統計響應

### 4. API 路由 ✅

**文件**: `app/api/classification_routes.py` (新建)

**實現的端點**:

#### POST `/files/classify`

- 批量分類檔案
- 支援自動創建和添加標籤
- 返回每個檔案的分類結果和錯誤信息
- 權限: Editor 或 Admin

#### POST `/files/{file_id}/auto-classify`

- 自動分類單個檔案
- 可選自動添加標籤
- 將分類結果存儲為註解
- 權限: Editor 或 Admin

#### GET `/files/{file_id}/classification`

- 查詢檔案的分類結果
- 從註解中讀取最新的分類信息
- 權限: 已登錄用戶

#### GET `/files/classifications/stats`

- 查詢分類統計信息
- 包含類型分佈、平均置信度、未知檔案率等
- 權限: 已登錄用戶

#### GET `/files/supported-types`

- 查詢系統支援的檔案類型
- 返回類型到擴展名的映射
- 公開端點（無需認證）

### 5. 集成到主應用 ✅

**文件**: `app/main.py`

- 導入 `classification_router`
- 註冊分類路由到應用
- 在檔案上傳端點集成了自動分類功能 (`auto_classify` 參數)

### 6. 單元測試 ✅

**文件**:

- `app/test_classification.py` (服務層測試，已存在)
- `app/test_classification_api.py` (API 測試，新建)

**API 測試覆蓋**:

- 單檔案自動分類 (成功/失敗場景)
- 批量分類 (正常/包含無效檔案)
- 權限測試 (Editor 可以分類，Viewer 不可以)
- 分類結果查詢
- 統計信息查詢
- 元數據提取驗證
- 標籤自動創建與添加

**服務層測試覆蓋**:

- XRD/SEM/EIS 等不同檔案類型分類
- 元數據提取 (樣品名、日期、溫度等)
- 標籤生成邏輯
- 批量分類
- 統計功能

## 功能特點

### 智能識別

- **雙重驗證**: 結合檔案擴展名和檔名關鍵字進行分類
- **高置信度**: 當兩種方法都匹配時，置信度可達 0.95 以上
- **未知檔案處理**: 對無法識別的檔案返回 "Unknown" 類型

### 元數據提取

從檔名中自動提取:

- 樣品名稱 (如 Cr3, MnO2, Sample_A)
- 測試日期 (支援多種格式: YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD)
- 儀器類型 (XRD, SEM, EIS等)
- 序號 (如 01, 02, 001)
- 溫度信息 (如 300C)
- 樣品ID (如 S001)

### 自動標籤

- 檔案類型標籤 (XRD, SEM, EIS等)
- 樣品相關標籤 (sample:Cr3, Cr-doped, Mn-based)
- 時間標籤 (year:2025, month:2025-01)
- 相位標籤 (alpha-phase, beta-phase, gamma-phase)
- 測試類型標籤 (cycle-test, rate-test, charge-discharge)
- 處理階段標籤 (raw-data, processed, refined)

### 批量處理

- 支援一次分類多個檔案
- 部分失敗不影響其他檔案的處理
- 詳細的錯誤報告

### 存儲機制

- 分類結果作為註解 (Annotation) 存儲在資料庫
- source 標記為 "auto_classification" 便於查詢
- 保留完整的分類信息和元數據

## API 使用示例

### 1. 分類單個檔案

```bash
POST /files/{file_id}/auto-classify?auto_tag=true&auto_create_tags=true
Authorization: Bearer <token>
```

**響應**:

```json
{
  "file_id": 1,
  "filename": "Cr3_XRD_20250104.xy",
  "classification": {
    "file_type": "XRD",
    "confidence": 0.95,
    "suggested_tags": ["XRD", "X-ray衍射", "Cr-doped", "year:2025", "month:2025-01"],
    "metadata": {
      "sample": "Cr3",
      "date": "2025-01-04",
      "instrument": "XRD"
    },
    "source": "auto"
  },
  "tags_created": ["XRD", "X-ray衍射", "Cr-doped"],
  "tags_added": ["XRD", "X-ray衍射", "Cr-doped", "year:2025", "month:2025-01"]
}
```

### 2. 批量分類

```bash
POST /files/classify
Authorization: Bearer <token>
Content-Type: application/json

{
  "file_ids": [1, 2, 3],
  "auto_tag": true,
  "auto_create_tags": true
}
```

**響應**:

```json
{
  "total": 3,
  "successful": 3,
  "failed": 0,
  "results": [...],
  "errors": []
}
```

### 3. 查詢分類結果

```bash
GET /files/{file_id}/classification
Authorization: Bearer <token>
```

### 4. 查詢統計

```bash
GET /files/classifications/stats
Authorization: Bearer <token>
```

**響應**:

```json
{
  "total": 10,
  "by_type": {
    "XRD": 4,
    "SEM": 3,
    "EIS": 2,
    "Unknown": 1
  },
  "avg_confidence": 0.87,
  "unknown_count": 1,
  "unknown_rate": 0.1
}
```

## 開發說明

### 擴展新的檔案類型

1. 在 `config/file_classification_rules.yml` 中添加新規則
2. 在 `FileClassificationService.FILE_TYPE_EXTENSIONS` 中添加擴展名映射
3. 在 `FileClassificationService.KEYWORD_PATTERNS` 中添加關鍵字模式
4. 添加相應的測試用例

### 自定義標籤生成

在 `FileClassificationService._generate_tags()` 方法中添加自定義邏輯。

### 元數據提取規則

修改以下方法:

- `_extract_date()`: 日期提取
- `_extract_sample_name()`: 樣品名提取
- `_extract_instrument_type()`: 儀器類型提取

## 測試運行

```bash
# 運行所有分類測試
pytest app/test_classification.py app/test_classification_api.py -v

# 運行服務層測試
pytest app/test_classification.py -v

# 運行 API 測試
pytest app/test_classification_api.py -v
```

## 注意事項

1. **權限要求**: 分類操作需要 Editor 或 Admin 權限
2. **標籤創建**: 可通過 `auto_create_tags` 參數控制是否自動創建不存在的標籤
3. **置信度閾值**: 默認閾值為 0.5，低於此值視為未分類
4. **存儲格式**: 分類結果作為 Annotation 存儲，source="auto_classification"

## 後續優化建議

1. **配置文件加載**: 將 YAML 規則配置文件動態加載到服務中
2. **內容分析**: 添加檔案內容分析以提高分類準確度
3. **機器學習**: 集成 ML 模型實現更智能的分類
4. **規則管理 API**: 提供 API 端點動態管理分類規則
5. **批量操作優化**: 對大量檔案的批量分類進行性能優化

## 相關文檔

- [API Reference](docs/specs/api.md)
- [Architecture](docs/architecture/system-architecture.md)
- [v0.3 Phase 1 Plan](docs/roadmap/v0.3-phase1-detailed-plan.md)

---

**實現者**: GitHub Copilot
**完成日期**: 2026-02-17
**版本**: v0.3.0-alpha
