# 推理鏈編輯器與模板庫使用指南

## 概述

本指南介紹 LabFlow 的推理鏈前端編輯器和模板庫功能，讓您可以輕鬆地創建、編輯和重用自動化分析工作流。

## 功能特性

### 1. 視覺化流程編輯器

推理鏈編輯器提供了一個直觀的可視化界面，用於構建和編輯數據分析工作流。

**主要功能：**

- 拖拽式節點連接
- 可視化工作流程圖
- 實時執行和調試
- 保存和載入推理鏈

**訪問方式：**

- 創建新推理鏈：點擊主頁"創建新推理鏈"或導航到 `/flow/new`
- 編輯現有推理鏈：在主頁列表中點擊"Edit"按鈕

### 2. 增強的節點配置編輯器

新的節點配置編輯器為每種節點類型提供了專門的可視化配置界面，無需手動編輯 JSON。

**支持的節點類型：**

#### Data Input（數據輸入）

- **Source Type**：選擇數據來源（Global Input、File、Database）
- **Key Path**：指定數據的鍵路徑（例如：`file_id`、`data.measurements`）

#### Transform（數據轉換）

- **Operation**：選擇轉換操作
  - Smooth：數據平滑（可配置窗口大小）
  - Normalize：數據歸一化
  - Filter：數據過濾
  - Convert Units：單位轉換（配置源單位和目標單位）

#### Calculate（計算）

- **Operation**：選擇計算類型
  - Peak Fit：峰位擬合（可選擇模型：Gaussian、Lorentzian、Voigt）
  - Impedance Analysis：阻抗分析
  - Statistics：統計計算
  - Custom：自定義計算（可輸入表達式）

#### Condition（條件判斷）

- **Left Operand**：左操作數
- **Operator**：運算符（>、<、==、>=、<=）
- **Right Operand**：右操作數

#### Output（輸出）

- **Output Type**：輸出類型
  - Return：返回值
  - Plot：圖表（可選擇圖表類型和標題）
  - Save File：保存文件（可指定文件名）
  - Conclusion：結論

**使用方式：**

1. 在流程編輯器中點擊任何節點
2. 右側面板顯示節點配置編輯器
3. 使用"Visual Editor"標籤進行可視化配置
4. 需要高級配置時，切換到"JSON Editor"標籤

### 3. 模板庫

模板庫允許您保存常用的推理鏈配置作為模板，以便快速創建新的工作流。

**訪問方式：**

- 主頁快捷卡片：點擊"模板庫"卡片
- 頂部導航欄：點擊"Templates"
- 直接訪問：`/templates`

**模板庫功能：**

- **瀏覽模板**：查看所有可用的推理鏈模板
- **預覽模板**：查看模板的工作流程圖和節點配置
- **使用模板**：從模板創建新的推理鏈
- **編輯模板**：修改現有模板
- **刪除模板**：移除不需要的模板

### 4. 創建和保存模板

**創建新模板：**

1. 點擊模板庫頁面的"創建新模板"按鈕
2. 在流程編輯器中構建您的工作流
3. 勾選"保存為可重用模板"複選框
4. 點擊"Save"保存

**將現有推理鏈轉換為模板：**

1. 打開要轉換的推理鏈
2. 勾選"保存為可重用模板"複選框
3. 點擊"Save"保存

**從模板創建推理鏈：**

1. 在模板庫中找到所需模板
2. 點擊"使用"按鈕
3. 系統會創建一個新的推理鏈副本
4. 根據需要修改新推理鏈
5. 保存（不勾選模板複選框）

## 工作流程示例

### 示例 1：基本數據處理流程

```
Data Input → Transform (Smooth) → Calculate (Statistics) → Output (Plot)
```

1. **Data Input節點**：
   - Source Type: Global Input
   - Key Path: measurements

2. **Transform節點**：
   - Operation: Smooth
   - Window Size: 5

3. **Calculate節點**：
   - Operation: Statistics

4. **Output節點**：
   - Output Type: Plot
   - Chart Type: Line Chart

### 示例 2：條件分支流程

```
Data Input → Calculate → Condition
                         ├─ True → Output (Conclusion A)
                         └─ False → Output (Conclusion B)
```

1. **Condition節點**：
   - Left Operand: result.mean
   - Operator: >
   - Right Operand: 0.5

## 最佳實踐

1. **命名規範**：為節點和推理鏈使用描述性名稱
2. **模塊化**：將複雜的工作流分解為小的可重用模板
3. **測試執行**：在保存為模板之前測試推理鏈
4. **添加描述**：為模板添加詳細的描述，方便團隊使用
5. **版本控制**：創建多個版本的模板以追踪改進

## 常見問題

**Q: 模板和普通推理鏈有什麼區別？**
A: 模板是可重用的推理鏈配置，專門用於快速創建新工作流。普通推理鏈是可以直接執行的工作流實例。

**Q: 如何在節點之間傳遞數據？**
A: 使用連接線（edges）連接節點。下游節點可以通過 inputs 接收上游節點的輸出。

**Q: 可以導出和導入模板嗎？**
A: 當前版本支持在界面中創建和使用模板。導入導出功能將在未來版本中添加。

**Q: 如何調試推理鏈執行錯誤？**
A: 在流程編輯器中點擊"Run"按鈕執行推理鏈，右側面板會顯示執行結果和錯誤信息。

## 技術實現

### 前端組件

- **TemplateLibrary.jsx**：模板庫頁面
- **FlowEditor.jsx**：流程編輯器（增強版）
- **NodeInspector.jsx**：節點配置編輯器（增強版）

### API 端點

- `GET /reasoning/chains`：獲取所有推理鏈（包括模板）
- `POST /reasoning/chains`：創建推理鏈或模板
- `PUT /reasoning/chains/{id}`：更新推理鏈或模板
- `DELETE /reasoning/chains/{id}`：刪除推理鏈或模板

### 數據模型

推理鏈和模板共享相同的數據模型，通過 `is_template` 字段區分：

```json
{
  "name": "模板名稱",
  "description": "模板描述",
  "is_template": true,
  "nodes": [...]
}
```

## 更新日誌

**2026-02-17**

- ✨ 新增模板庫功能
- ✨ 增強節點配置編輯器（可視化表單）
- ✨ FlowEditor 支持模板創建和編輯
- 🎨 改進主頁 UI，添加快捷卡片
- 📝 添加模板庫導航鏈接

## 相關文檔

- [推理引擎核心文檔](../app/reasoning_engine/README.md)
- [API 參考](specs/api.md)
- [視覺化用戶指南](USER_GUIDE_VISUALIZATION.md)
- [快速開始](getting-started/quick-start.md)
