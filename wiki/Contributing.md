# Contributing | 貢獻指南

---

## 📖 Language / 語言

- [English ↓](#english)
- [中文 ↓](#chinese)

---

<a id="english"></a>

## English

Thank you for your interest in contributing to LabFlow! Every contribution — bug reports, feature requests, code, or documentation — is appreciated.

### Code of Conduct

Please read and follow our [Code of Conduct](../CODE_OF_CONDUCT.md). We are committed to maintaining a welcoming and inclusive community.

---

### Ways to Contribute

#### 1. Report Bugs

- Check [GitHub Issues](https://github.com/tico-Lin/labflow/issues) first to avoid duplicates.
- Use the **Bug Report** issue template.
- Include: steps to reproduce, expected vs. actual behavior, environment details, and logs.

#### 2. Request Features

- Check existing issues and discussions first.
- Use the **Feature Request** issue template.
- Describe: the use case, your proposed solution, and any alternatives you've considered.

#### 3. Improve Documentation

- Fix typos, clarify explanations, add examples.
- Documentation follows the same PR workflow as code.
- Both English and Chinese documentation are equally important.

#### 4. Submit Code Changes

---

### Development Setup

#### Prerequisites

- Python 3.9+
- Node.js 16+
- Git

#### Clone and Install

```bash
# Clone the repository
git clone https://github.com/tico-Lin/labflow.git
cd labflow

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
pip install -r dev-requirements.txt

# Install Node.js dependencies
npm install
cd frontend && npm install && cd ..
```

---

### Development Workflow

#### 1. Create a Branch

```bash
# Feature branch
git checkout -b feature/your-feature-name

# Bug fix branch
git checkout -b fix/your-bug-fix-name

# Documentation branch
git checkout -b docs/your-doc-update
```

#### 2. Make Changes

Follow the project's code style:

| Language | Style Guide | Linter |
|----------|-------------|--------|
| Python | PEP 8 | Ruff |
| JavaScript/React | Prettier | ESLint |
| Documentation | Markdown best practices | — |

#### 3. Run Tests

```bash
# Python tests
pytest -v --cov=app --cov-report=html

# Frontend tests
cd frontend
npm test
```

Ensure that:
- All tests pass
- Test coverage does not decrease
- New code includes appropriate tests

#### 4. Commit Your Changes

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short description>

<optional body>

<optional footer>
```

**Commit types:**

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style (no logic change) |
| `refactor` | Code refactoring |
| `test` | Test changes |
| `chore` | Build, dependencies, tooling |
| `perf` | Performance improvement |

**Example:**

```
fix(reasoning-engine): resolve infinite loop in DAG execution

- Added circular dependency detection
- Fixed node completion callback timing
- Added integration test for cycle detection

Fixes #123
```

#### 5. Open a Pull Request

- Push your branch: `git push origin your-branch-name`
- Open a PR on GitHub using the PR template
- Link related issues
- Describe the changes and how you tested them

---

### Pull Request Checklist

Before submitting, verify:

- [ ] Tests pass and coverage doesn't decrease
- [ ] Code follows project style conventions
- [ ] Documentation is updated (docstrings, README, wiki)
- [ ] Commit messages are clear and follow conventions
- [ ] Changes address a single concern or feature
- [ ] No secrets or credentials in the code

---

### Project Structure

```
labflow/
├── app/                    # Python backend (FastAPI)
│   ├── api/               # Route handlers
│   ├── services/          # Business logic
│   ├── models.py          # Database models
│   ├── schemas.py         # Pydantic schemas
│   └── main.py            # Application entry point
├── frontend/              # React frontend (Vite)
│   └── src/
├── docs/                  # Technical documentation
├── wiki/                  # Wiki pages
└── tests/                 # Test suite
```

---

### Review Process

1. Automated checks run (tests, lint, coverage)
2. At least one maintainer review is required
3. Address review feedback and request re-review
4. Squash commits if needed before merge
5. Merge to `main` branch

---

### Attribution

All contributors will be credited in:
- Git commit history (automatic)
- Release notes (for major contributions)

---

<a id="chinese"></a>

## 中文

感謝您對 LabFlow 的貢獻興趣！每一份貢獻——問題報告、功能請求、代碼或文檔——都受到感謝。

### 行為準則

請閱讀並遵守我們的[行為準則](../CODE_OF_CONDUCT.md)。我們致力於維護一個友好和包容的社區。

---

### 貢獻方式

#### 1. 報告問題

- 先查看 [GitHub Issues](https://github.com/tico-Lin/labflow/issues) 避免重複。
- 使用**問題報告**模板。
- 包含：重現步驟、預期與實際行為、環境詳情和日誌。

#### 2. 請求功能

- 先查看現有 Issues 和討論。
- 使用**功能請求**模板。
- 描述：使用場景、您的建議方案以及您考慮的替代方案。

#### 3. 改進文檔

- 修復錯別字、澄清說明、添加示例。
- 文檔遵循與代碼相同的 PR 工作流程。
- 中英文文檔同等重要。

#### 4. 提交代碼更改

---

### 開發環境設置

#### 環境要求

- Python 3.9+
- Node.js 16+
- Git

#### 克隆和安裝

```bash
# 克隆倉庫
git clone https://github.com/tico-Lin/labflow.git
cd labflow

# 創建並激活虛擬環境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安裝 Python 依賴
pip install -r requirements.txt
pip install -r dev-requirements.txt

# 安裝 Node.js 依賴
npm install
cd frontend && npm install && cd ..
```

---

### 開發工作流程

#### 1. 創建分支

```bash
# 功能分支
git checkout -b feature/your-feature-name

# 問題修復分支
git checkout -b fix/your-bug-fix-name

# 文檔分支
git checkout -b docs/your-doc-update
```

#### 2. 進行更改

遵循項目的代碼風格：

| 語言 | 風格指南 | 代碼檢查工具 |
|------|----------|-------------|
| Python | PEP 8 | Ruff |
| JavaScript/React | Prettier | ESLint |
| 文檔 | Markdown 最佳實踐 | — |

#### 3. 運行測試

```bash
# Python 測試
pytest -v --cov=app --cov-report=html

# 前端測試
cd frontend
npm test
```

確保：
- 所有測試通過
- 測試覆蓋率不降低
- 新代碼包含適當的測試

#### 4. 提交更改

使用[約定式提交](https://www.conventionalcommits.org/zh-hant/)格式：

```
<類型>(<範圍>): <簡短描述>

<可選正文>

<可選頁腳>
```

**提交類型：**

| 類型 | 用法 |
|------|------|
| `feat` | 新功能 |
| `fix` | 問題修復 |
| `docs` | 文檔更改 |
| `style` | 代碼風格（無邏輯更改） |
| `refactor` | 代碼重構 |
| `test` | 測試更改 |
| `chore` | 構建、依賴、工具 |
| `perf` | 性能改進 |

**示例：**

```
fix(reasoning-engine): 解決 DAG 執行中的無限循環

- 添加循環依賴檢測
- 修復節點完成回調時序
- 添加循環檢測集成測試

Fixes #123
```

#### 5. 開啟 Pull Request

- 推送分支：`git push origin your-branch-name`
- 在 GitHub 上使用 PR 模板開啟 PR
- 鏈接相關 Issues
- 描述更改及測試方式

---

### Pull Request 核查清單

提交前請確認：

- [ ] 測試通過且覆蓋率不降低
- [ ] 代碼遵循項目風格規範
- [ ] 文檔已更新（文檔字符串、README、wiki）
- [ ] 提交消息清晰且遵循約定
- [ ] 更改只涉及單一關注點或功能
- [ ] 代碼中沒有密鑰或憑證

---

### 項目結構

```
labflow/
├── app/                    # Python 後端（FastAPI）
│   ├── api/               # 路由處理器
│   ├── services/          # 業務邏輯
│   ├── models.py          # 數據庫模型
│   ├── schemas.py         # Pydantic 模式
│   └── main.py            # 應用程序入口點
├── frontend/              # React 前端（Vite）
│   └── src/
├── docs/                  # 技術文檔
├── wiki/                  # Wiki 頁面
└── tests/                 # 測試套件
```

---

### 審查流程

1. 自動檢查運行（測試、代碼檢查、覆蓋率）
2. 需要至少一位維護者審查
3. 處理審查反饋並請求重新審查
4. 合併前如需要可壓縮提交
5. 合併到 `main` 分支

---

### 歸因

所有貢獻者將獲得以下認可：
- Git 提交歷史（自動）
- 發布說明（重大貢獻）

---

*← [API Reference](API-Reference) | [FAQ →](FAQ)*
