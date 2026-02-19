# 檔案自動分類功能

## 功能概述

檔案自動分類是LabFlow v0.3新增的智能功能，能夠根據檔案名稱和擴展名自動識別檔案類型、提取元數據，並建議相關標籤。

## 主要特性

### 1. 自動檔案類型識別

支援多種實驗室常用檔案類型：

- **XRD** (X-ray Diffraction): `.xy`, `.txt`, `.xrdml`, `.raw`, `.cif`
- **SEM** (Scanning Electron Microscopy): `.tif`, `.tiff`, `.jpg`, `.png`, `.dm3`, `.dm4`
- **TEM** (Transmission Electron Microscopy): `.tif`, `.tiff`, `.dm3`, `.dm4`
- **EIS** (Electrochemical Impedance Spectroscopy): `.txt`, `.csv`, `.xlsx`, `.mpt`, `.mpr`
- **CV** (Cyclic Voltammetry): `.txt`, `.csv`, `.xlsx`, `.mpt`, `.mpr`
- **Excel**: `.xlsx`, `.xls`
- **Image**: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`
- **Data**: `.txt`, `.csv`, `.dat`, `.asc`

### 2. 元數據自動提取

從檔案名稱中智能提取：

- **樣品名稱**: Cr3, MnO2, Sample_A 等
- **日期**: 支援多種格式 (YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD)
- **序號**: 01, 02, 001 等
- **儀器類型**: XRD, SEM, EIS 等
- **溫度**: 300°C, 400C 等
- **樣品編號**: S001, S002 等

### 3. 智能標籤建議

根據分析結果自動建議標籤：

- **檔案類型標籤**: XRD, SEM, EIS 等
- **樣品標籤**: sample:Cr3, sample:MnO2
- **摻雜標籤**: Cr-doped, Mn-based
- **相位標籤**: beta-phase, alpha-phase, gamma-phase
- **時間標籤**: year:2025, month:2025-01
- **測試類型標籤**: cycle-test, rate-test, charge-discharge
- **處理階段標籤**: raw-data, processed, refined

## 支援的命名規範

系統能夠識別多種命名格式：

### 格式1: 樣品_儀器_日期.擴展名
```
Cr3_XRD_20250104.xy
→ 類型: XRD, 樣品: Cr3, 日期: 2025-01-04
```

### 格式2: 樣品_儀器_日期_序號.擴展名
```
Sample_A_SEM_2025-01-15_01.tif
→ 類型: SEM, 樣品: Sample_A, 日期: 2025-01-15, 序號: 01
```

### 格式3: 儀器_樣品_日期.擴展名
```
EIS_MnO2_20250110.txt
→ 類型: EIS, 樣品: MnO2, 日期: 2025-01-10
```

### 格式4: 樣品-相位-儀器.擴展名
```
MnO2-Cr3-beta_XRD.xy
→ 類型: XRD, 樣品: MnO2, 相位: beta
```

## API 使用

### 1. 上傳時自動分類

上傳檔案時會自動進行分類和標籤添加：

```bash
POST /files/
Content-Type: multipart/form-data

file: <檔案>
auto_classify: true  # 預設為true
auto_tag: true       # 預設為true
```

**響應示例：**
```json
{
  "id": 123,
  "filename": "Cr3_XRD_20250104.xy",
  "file_hash": "abc123...",
  "created_at": "2025-01-04T10:00:00Z",
  "tags": [
    {"id": 1, "name": "XRD"},
    {"id": 2, "name": "sample:Cr3"},
    {"id": 3, "name": "year:2025"},
    {"id": 4, "name": "month:2025-01"}
  ]
}
```

### 2. 手動觸發分類

對已存在的檔案進行分類：

```bash
POST /files/{file_id}/classify
Content-Type: application/json

{
  "auto_tag": true,
  "auto_create_tags": true
}
```

**響應示例：**
```json
{
  "file_id": 123,
  "filename": "Cr3_XRD_20250104.xy",
  "classification": {
    "file_type": "XRD",
    "confidence": 0.95,
    "suggested_tags": ["XRD", "sample:Cr3", "year:2025"],
    "metadata": {
      "sample": "Cr3",
      "date": "2025-01-04",
      "instrument": "XRD"
    },
    "source": "auto"
  },
  "tags_created": ["sample:Cr3"],
  "tags_added": ["XRD", "sample:Cr3", "year:2025"]
}
```

### 3. 批量分類

對多個檔案進行批量分類：

```bash
POST /files/classify/batch
Content-Type: application/json

{
  "file_ids": [1, 2, 3, 4, 5],
  "auto_tag": true,
  "auto_create_tags": true
}
```

**響應示例：**
```json
{
  "total": 5,
  "successful": 4,
  "failed": 1,
  "results": [
    {
      "file_id": 1,
      "filename": "file1.xy",
      "classification": {...},
      "tags_created": [],
      "tags_added": ["XRD"]
    },
    ...
  ],
  "errors": [
    {
      "file_id": 5,
      "error": "檔案不存在"
    }
  ]
}
```

### 4. 獲取分類統計

查看系統中檔案的分類統計信息：

```bash
GET /classification/stats
```

**響應示例：**
```json
{
  "total": 100,
  "by_type": {
    "XRD": 35,
    "SEM": 25,
    "EIS": 20,
    "CV": 15,
    "Unknown": 5
  },
  "avg_confidence": 0.87,
  "unknown_count": 5,
  "unknown_rate": 0.05
}
```

### 5. 獲取支援的檔案類型

查詢系統支援的所有檔案類型：

```bash
GET /classification/supported-types
```

**響應示例：**
```json
{
  "supported_types": {
    "XRD": [".xy", ".txt", ".xrdml", ".raw"],
    "SEM": [".tif", ".tiff", ".jpg", ".png"],
    "EIS": [".txt", ".csv", ".xlsx"],
    ...
  },
  "total_types": 10
}
```

## 分類置信度

系統會為每次分類提供置信度評分（0.0-1.0）：

- **0.9-1.0**: 檔名關鍵字匹配（如檔名包含"XRD"）
- **0.7-0.9**: 擴展名匹配（如.xy檔案）
- **0.0-0.5**: 未知類型

## 自動生成的註解

分類結果會自動存儲為註解，可通過以下方式查詢：

```bash
GET /files/{file_id}/annotations/
```

註解內容示例：
```json
{
  "id": 1,
  "file_id": 123,
  "source": "auto_classification",
  "data": {
    "classification": {
      "file_type": "XRD",
      "confidence": 0.95,
      "metadata": {
        "sample": "Cr3",
        "date": "2025-01-04",
        "instrument": "XRD"
      }
    }
  },
  "created_at": "2025-01-04T10:00:00Z"
}
```

## 最佳實踐

### 檔案命名建議

為了獲得最佳的分類效果，建議遵循以下命名規範：

1. **包含檔案類型關鍵字**: XRD, SEM, EIS, CV 等
2. **包含樣品名稱**: 放在檔名開頭或緊跟儀器類型後
3. **使用標準日期格式**: YYYYMMDD 或 YYYY-MM-DD
4. **使用下劃線分隔**: 便於解析（如 Sample_XRD_20250104.xy）
5. **包含序號**: 如有多個相關檔案，使用 _01, _02 等

### 標籤管理建議

1. **定期審查自動標籤**: 檢查 `/classification/stats` 確保標籤質量
2. **手動補充標籤**: 自動分類可能無法識別所有語義信息
3. **統一標籤命名**: 使用一致的命名規範（如 sample:XXX, year:YYYY）
4. **批量重新分類**: 更新分類規則後，使用批量分類重新處理舊檔案

## 常見問題

### Q: 為什麼我的檔案被分類為 "Unknown"？

可能原因：
- 檔案擴展名不在支援列表中
- 檔名不包含可識別的關鍵字
- 命名格式不符合任何已知模式

解決方案：
- 重命名檔案以包含檔案類型關鍵字
- 使用標準的檔案擴展名
- 手動添加適當的標籤

### Q: 如何關閉自動分類？

在上傳檔案時設置參數：
```bash
POST /files/?auto_classify=false&auto_tag=false
```

### Q: 分類錯誤怎麼辦？

1. 手動刪除錯誤的標籤
2. 手動添加正確的標籤
3. 如果需要，可以刪除自動生成的分類註解

### Q: 如何自定義分類規則？

目前分類規則在 `app/services/classification_service.py` 中定義，可以通過修改以下內容來自定義：

- `FILE_TYPE_EXTENSIONS`: 添加新的檔案類型和擴展名
- `KEYWORD_PATTERNS`: 添加新的關鍵字模式
- `_generate_tags()`: 自定義標籤生成邏輯

## 技術架構

### 核心組件

```
FileClassificationService
├── classify_file()          # 單個檔案分類
├── batch_classify()         # 批量分類
├── _classify_by_extension() # 根據擴展名分類
├── _classify_by_keywords()  # 根據關鍵字分類
├── _extract_metadata()      # 提取元數據
└── _generate_tags()         # 生成標籤建議
```

### 數據流

```
上傳檔案
  ↓
計算檔案Hash
  ↓
儲存檔案
  ↓
創建資料庫記錄
  ↓
自動分類 ←─────────────┐
  ↓                     │
提取元數據              │
  ↓                     │
生成標籤建議            │
  ↓                     │
創建/添加標籤           │
  ↓                     │
存儲分類註解            │
  ↓                     │
返回結果                │
                        │
手動觸發分類 ───────────┘
```

## 未來擴展

計劃中的功能改進：

1. **基於內容的分類**: 不僅依賴檔名，還分析檔案內容
2. **機器學習模型**: 使用ML模型提高分類準確度
3. **自定義規則引擎**: 允許用戶通過UI配置分類規則
4. **分類結果反饋機制**: 用戶可以標記分類正確性，用於改進模型
5. **多語言支援**: 支援中文、英文等多種語言的檔名識別

## 測試

運行分類功能測試：

```bash
# 運行單元測試
pytest app/test_classification.py -v

# 運行手動測試
python app/test_classification.py
```

## 相關文檔

- [API 規格說明](../docs/specs/api.md)
- [系統架構](../docs/architecture/system-architecture.md)
- [數據模型](../docs/architecture/data-schema.md)

## 更新日誌

### v0.3.0 (2026-02-17)
- ✨ 新增檔案自動分類服務
- ✨ 支援10+種實驗室常用檔案類型
- ✨ 智能元數據提取
- ✨ 自動標籤建議和創建
- ✨ 批量分類API
- ✨ 分類統計功能
- 📝 完整的測試覆蓋
