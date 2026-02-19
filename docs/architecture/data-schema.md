# data-schema.md
版本：v0.1（MVP 取向，可擴充）  
目的：統一「檔案—標籤—結論—標註—分析結果」的最小欄位。

---
## 1. 設計原則
- **ID 策略**：全面使用 **UUID (String)**，確保未來遷移/同步無衝突。
- **Storage 策略**：明確記錄 `storage_backend`，支援混合雲模式。
- **原始檔不可變**：Raw file 只讀不改。

---
## 2. 核心實體 (Tables)

### 2.1 Files (檔案)
| 欄位名 | 類型 | 說明 | 備註 |
| :--- | :--- | :--- | :--- |
| `id` | String (UUID) | 主鍵 | |
| `filename` | String | 原始檔名 | |
| `file_type` | String | 檔案類型識別 | 例：`xrd_pattern` |
| `storage_backend` | String | 儲存位置類型 | `local`, `s3`, `minio` |
| `storage_key` | String | 儲存路徑/Key | 不含 base path |
| `sha256` | String | 檔案雜湊 | 用於去重 |
| `size_bytes` | Integer | 檔案大小 | |
| `created_at` | DateTime | 上傳時間 | UTC/ISO |
| `metadata_json` | JSON | 擴充屬性 | 存放儀器參數等 |

### 2.2 Tags (標籤)
| 欄位名 | 類型 | 說明 | 備註 |
| :--- | :--- | :--- | :--- |
| `id` | String (UUID) | 主鍵 | |
| `name` | String | 標籤名 | Unique |
| `category` | String | 分類 | 可選 |
| `created_at` | DateTime | 建立時間 | |

### 2.3 FileTags (關聯表)
- `file_id`: FK -> Files.id
- `tag_id`: FK -> Tags.id
- (Composite PK: file_id + tag_id)

### 2.4 Conclusions (結論)
| 欄位名 | 類型 | 說明 | 備註 |
| :--- | :--- | :--- | :--- |
| `id` | String (UUID) | 主鍵 | |
| `file_id` | String (UUID) | 外鍵 -> Files | |
| `content_md` | Text | Markdown 內容 | |
| `confidence` | String | 置信度 | `high`, `medium`, `low` |
| `created_at` | DateTime | 建立時間 | |
| `updated_at` | DateTime | 修改時間 | |

### 2.5 Annotations (標註)
| 欄位名 | 類型 | 說明 | 備註 |
| :--- | :--- | :--- | :--- |
| `id` | String (UUID) | 主鍵 | |
| `file_id` | String (UUID) | 外鍵 -> Files | |
| `provider` | String | 標註來源 | `local`, `label_studio` |
| `schema_version`| String | 格式版本 | `v1` |
| `payload_json` | JSON | 標註本體 | 座標、範圍、類別 |
| `created_at` | DateTime | 建立時間 | |

---
## 3. 檔案類型列舉 (建議)
- `xrd_pattern`
- `eis_spectrum`
- `cv_curve`
- `sem_image`
- `general_data` (Excel/CSV)