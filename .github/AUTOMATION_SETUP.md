## GitHub 自動化配置指南

此文件記錄了 LabFlow repository 的所有自動化設置，用於減少手動干預並確保一致的開發流程。

### 📋 已配置的自動化設置

#### 1. Repository 合併設定
✅ **允許的合併方法**:
- Squash merge（推薦用於單提交歷史）
- Merge commit（保留完整歷史）
- Rebase merge（線性歷史）

✅ **自動清理**:
- 合併後自動刪除分支 ✓

#### 2. Main 分支保護規則 (Ruleset)

**Rule ID**: main-branch-rules (13177400)

**禁止操作**:
- ✓ 刪除分支
- ✓ 非快進推送 (non-fast-forward)

**PR 要求**:
- ✓ 必須通過 PR 提交（0 個批准即可合併）
- ✓ 允許的合併方法: squash, merge, rebase

#### 3. Repository 功能

已啟用:
- ✓ Issues（議題跟蹤）
- ✓ Projects（項目管理）
- ✓ Wiki（知識庫）
- ✓ Discussions（討論區）

已禁用:
- ✗ Downloads（GitHub Releases 下載）

#### 4. 代碼所有者 (CODEOWNERS)

Location: `.github/CODEOWNERS`

責任分配:
- **根目錄和一般更改**: @tico-Lin
- **應用代碼** (`/app/`): @tico-Lin
- **前端** (`/frontend/`): @tico-Lin
- **測試** (`/tests/`): @tico-Lin
- **文檔和配置**: @tico-Lin
- **安全檔案**: @tico-Lin

#### 5. GitHub Actions 工作流程

**auto-merge.yml** - 自動合併工作流
- 監聽: PR 開啟/同步到 main
- 條件: PR 標題以 `fix:`、`docs:`、`chore:` 開頭
- 動作: 
  1. 添加 `auto-merge` 標籤
  2. 檢查可合併性
  3. 使用 squash 方法自動合併
- 效果: **減少手動批准次數**

#### 6. Pull Request 模板

Location: `.github/PULL_REQUEST_TEMPLATE.md`

包含:
- 描述欄位
- 變更類型選項
- 相關議題連結
- 變更清單
- 測試說明
- 截圖欄位

### 🔄 工作流程流程

```
1. 創建功能分支
   git checkout -b fix/bug-description
   
2. 提交更改
   git commit -m "fix: bug description"
   
3. 推送更改
   git push origin fix/bug-description
   
4. 創建 PR
   - 系統自動應用 PR 模板
   - 自動驗證提交訊息格式
   
5. 自動處理
   ✓ 檢查提交格式（fix:/docs:/chore:）
   ✓ 添加自動合併標籤
   ✓ 檢查可合併性
   ✓ 自動合併（無需手動批准）
   
6. 後處理
   ✓ 分支自動刪除
   ✓ 更新 main 分支
```

### 🚀 便利功能

#### 自動提交格式驗證
提交訊息應遵循 Conventional Commits:
```
fix: 修復 bug 描述
feat: 新功能描述
docs: 文檔更新
chore: 維護任務
```

#### 標籤自動應用
根據 PR 標題自動添加標籤:
- `fix:*` → 適用 bug 標籤
- `feat:*` → 適用 feature 標籤
- `docs:*` → 適用 documentation 標籤

### 🔐 安全考慮

✓ 保護 main 分支免於直接推送
✓ 強制使用 PR 進行所有更改
✓ 代碼所有者自動審查需求
✓ CODEOWNERS 檔案控制責任分配

### 📊 統計

- **Repository Rulesets**: 1 (main-branch-rules)
- **GitHub Actions Workflow**: 1 (auto-merge.yml)
- **Collaborators**: 1 (@tico-Lin)
- **Protected Branches**: 1 (main)

### 🔧 維護

如需修改自動化設置:

1. **編輯 Ruleset**: GitHub 網頁 → Settings → Rules → main-branch-rules
2. **編輯 CODEOWNERS**: 編輯 `.github/CODEOWNERS` 文件
3. **編輯工作流程**: 編輯 `.github/workflows/auto-merge.yml`
4. **編輯 PR 模板**: 編輯 `.github/PULL_REQUEST_TEMPLATE.md`

### ✅ 最新更新

**日期**: 2026-02-24
**版本**: v1.0
**更新內容**:
- ✅ 配置 Repository 合併設定
- ✅ 更新 Main 分支 Ruleset
- ✅ 啟用 Discussions
- ✅ 創建 CODEOWNERS
- ✅ 添加自動合併工作流程
- ✅ 驗證 PR 模板

### 📞 支援

有問題或需要修改自動化設置，請聯繫 @tico-Lin。
