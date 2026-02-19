# 前端啟動指南

## 前提條件

確保已安裝：
- Node.js (建議 v18 或更高版本)
- npm (通常隨 Node.js 一起安裝)

## 安裝步驟

### 1. 進入前端目錄

```bash
cd frontend
```

### 2. 安裝依賴

```bash
npm install
```

這會安裝以下主要依賴：
- react (^18.3.1)
- react-dom (^18.3.1)
- react-router-dom (^6.26.2)
- reactflow (^11.11.4)
- antd (^5.19.3)
- vite (^5.4.0)

### 3. 配置環境變數

創建 `.env` 文件（如果不存在）：

```bash
cp .env.example .env
```

編輯 `.env` 文件，設置後端 API 地址：

```env
VITE_API_BASE=http://127.0.0.1:8000
VITE_OFFLINE_MODE=true
```

### 4. 啟動開發伺服器

```bash
npm run dev
```

輸出應該類似：

```
  VITE v5.4.0  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

### 5. 訪問應用

打開瀏覽器，訪問：

```
http://localhost:5173
```

## 生產構建

### 構建生產版本

```bash
npm run build
```

構建輸出會在 `dist/` 目錄中。

### 預覽生產構建

```bash
npm run preview
```

## 故障排除

### 問題：npm 命令無法識別

**Windows PowerShell 解決方案**：

1. 安裝 Node.js：https://nodejs.org/
2. 重新打開終端
3. 驗證安裝：
   ```powershell
   node --version
   npm --version
   ```

### 問題：依賴安裝失敗

**解決方案**：

1. 清理緩存：
   ```bash
   npm cache clean --force
   ```

2. 刪除 node_modules：
   ```bash
   rm -r node_modules
   ```

3. 重新安裝：
   ```bash
   npm install
   ```

### 問題：後端連接失敗

**解決方案**：

1. 確認後端服務正在運行：
   ```bash
   # 在項目根目錄
   python -m uvicorn app.main:app --reload
   ```

2. 檢查 `.env` 文件中的 `VITE_API_BASE` 設置

3. 確認後端運行在正確的端口（默認 8000）

### 問題：端口被占用

**解決方案**：

Vite 會自動選擇下一個可用端口。如果需要指定端口：

```bash
npm run dev -- --port 3000
```

## 開發提示

### 熱模塊替換 (HMR)

Vite 支持 HMR，修改代碼後會自動刷新瀏覽器。

### 開發者工具

建議安裝瀏覽器擴展：
- React Developer Tools
- Redux DevTools（如果使用 Redux）

### 代碼格式化

如果項目配置了 ESLint/Prettier，運行：

```bash
npm run lint
```

## 文件結構

```
frontend/
├── src/
│   ├── api/
│   │   └── client.js          # API 客戶端
│   ├── components/
│   │   ├── TopNav.jsx         # 頂部導航欄
│   │   └── NodeInspector.jsx  # 節點檢查器
│   ├── pages/
│   │   ├── Home.jsx                      # 首頁（推理鏈列表）
│   │   ├── FlowEditor.jsx                # 推理鏈編輯器
│   │   ├── ReasoningChainViewer.jsx      # 推理鏈查看器 (新增)
│   │   ├── Login.jsx                     # 登錄頁
│   │   ├── Register.jsx                  # 註冊頁
│   │   ├── AnalysisTools.jsx             # 分析工具
│   │   └── AnalysisRun.jsx               # 運行分析
│   ├── App.jsx                # 主應用組件
│   ├── main.jsx               # 入口文件
│   └── styles.css             # 全局樣式
├── index.html                 # HTML 模板
├── package.json               # 依賴配置
└── vite.config.js             # Vite 配置
```

## 相關命令

| 命令 | 說明 |
|------|------|
| `npm install` | 安裝依賴 |
| `npm run dev` | 啟動開發伺服器 |
| `npm run build` | 構建生產版本 |
| `npm run preview` | 預覽生產構建 |
| `npm run lint` | 運行 linter |

## 下一步

1. 確保後端服務正在運行
2. 訪問 http://localhost:5173
3. 登錄系統
4. 查看推理鏈列表
5. 點擊「View」按鈕查看推理鏈視覺化

## 更多資訊

- **使用指南**：`docs/USER_GUIDE_VISUALIZATION.md`
- **實現總結**：`IMPLEMENTATION_SUMMARY.md`
- **項目文檔**：`docs/README.md`
