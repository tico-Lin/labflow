# LabFlow 國際化 (i18n) 模塊

## 概述

LabFlow 現在支持完整的多語言功能，包括中文（繁體）和英文兩種語言模式，並提供可擴展的接口供其他語言使用。

## 功能特性

### ✨ 核心功能

- **雙語支持**: 內建中文（繁體）和英文完整翻譯
- **動態切換**: 無需重新載入頁面即可切換語言
- **持久化**: 語言設置自動保存在瀏覽器的 localStorage
- **可擴展**: 易於添加新語言支持
- **類型安全**: 使用嵌套鍵結構組織翻譯
- **參數化翻譯**: 支持動態參數插入

### 🌐 支持的語言

- 🇨🇳 **中文** (`zh`) - 繁體中文
- 🇬🇧 **英文** (`en`) - English

## 架構設計

### 後端 (Python/FastAPI)

#### 文件結構

```
app/
├── i18n.py                 # i18n 核心模塊
└── locales/                # 翻譯文件目錄
    ├── zh.json            # 中文翻譯
    ├── en.json            # 英文翻譯
    └── [其他語言].json    # 可擴展的其他語言
```

#### 核心組件

1. **Translator 類**: 負責單個語言的翻譯
2. **I18nManager 類**: 管理所有語言的翻譯加載和獲取
3. **API 端點**: 提供 RESTful API 訪問翻譯數據

#### API 端點

| 端點                             | 方法 | 描述                   |
| -------------------------------- | ---- | ---------------------- |
| `/i18n/locales`                  | GET  | 獲取所有可用的語言代碼 |
| `/i18n/translations/{locale}`    | GET  | 獲取指定語言的完整翻譯 |
| `/i18n/translate/{locale}/{key}` | GET  | 獲取單個翻譯鍵的值     |

### 前端 (React)

#### 文件結構

```
frontend/src/
├── i18n.jsx               # i18n 模塊（上下文、Hooks、組件）
└── main.jsx              # 包含 I18nProvider 的應用入口
```

#### 核心組件

1. **I18nProvider**: React Context 提供者
2. **useTranslation**: 獲取翻譯函數的 Hook
3. **useLanguage**: 管理語言設置的 Hook
4. **LanguageSwitcher**: 語言切換器 UI 組件
5. **Trans**: JSX 中的翻譯組件

## 使用指南

### 後端使用

#### 基本用法

```python
from app.i18n import get_translator

# 獲取中文翻譯器
t = get_translator("zh")
print(t("common.welcome"))  # 輸出: 歡迎使用 LabFlow

# 獲取英文翻譯器
t = get_translator("en")
print(t("common.welcome"))  # 輸出: Welcome to LabFlow
```

#### 帶參數的翻譯

```python
t = get_translator("zh")
print(t("common.selected_count", count=5))  # 輸出: 已選擇 5 項
```

#### 在 API 端點中使用

```python
from app.i18n import get_translator
from fastapi import Header

@app.get("/some-endpoint")
def some_endpoint(accept_language: str = Header(default="zh")):
    t = get_translator(accept_language)
    return {"message": t("common.success")}
```

### 前端使用

#### 基本設置

在應用入口（`main.jsx`）中包裹 `I18nProvider`:

```jsx
import { I18nProvider } from './i18n.jsx';

<I18nProvider>
  <App />
</I18nProvider>;
```

#### 在組件中使用翻譯

```jsx
import { useTranslation } from '../i18n.jsx';

function MyComponent() {
  const { t } = useTranslation();

  return (
    <div>
      <h1>{t('common.welcome')}</h1>
      <button>{t('common.submit')}</button>
    </div>
  );
}
```

#### 帶參數的翻譯

```jsx
const { t } = useTranslation();
<p>{t('common.selected_count', { count: items.length })}</p>;
```

#### 使用語言切換器

```jsx
import { LanguageSwitcher } from '../i18n.jsx';

function Header() {
  return (
    <div>
      <h1>LabFlow</h1>
      <LanguageSwitcher />
    </div>
  );
}
```

#### 使用 Trans 組件

```jsx
import { Trans } from '../i18n.jsx';

<Trans i18nKey="common.welcome" />
<Trans i18nKey="common.selected_count" count={5} />
```

#### 編程式語言切換

```jsx
import { useLanguage } from '../i18n.jsx';

function LanguageSettings() {
  const { locale, setLocale, locales } = useLanguage();

  return (
    <div>
      <p>當前語言: {locales[locale]}</p>
      <button onClick={() => setLocale('zh')}>中文</button>
      <button onClick={() => setLocale('en')}>English</button>
    </div>
  );
}
```

## 添加新語言

### 步驟 1: 創建翻譯文件

在 `app/locales/` 目錄下創建新的 JSON 文件，例如 `ja.json` （日文）:

```json
{
  "common": {
    "welcome": "LabFlowへようこそ",
    "login": "ログイン",
    "logout": "ログアウト"
  },
  "auth": {
    "username": "ユーザー名",
    "password": "パスワード"
  }
}
```

### 步驟 2: 更新前端語言列表

編輯 `frontend/src/i18n.jsx`，在 `SUPPORTED_LOCALES` 中添加新語言:

```jsx
export const SUPPORTED_LOCALES = {
  zh: '中文',
  en: 'English',
  ja: '日本語', // 新增
};
```

### 步驟 3: 測試

重啟後端和前端，新語言會自動出現在語言切換器中。

## 翻譯鍵結構

翻譯使用嵌套的 JSON 結構組織，主要分類如下:

```
common.*          - 通用翻譯（按鈕、操作等）
auth.*            - 身份驗證相關
file.*            - 檔案管理
tag.*             - 標籤系統
conclusion.*      - 結論記錄
annotation.*      - 註解系統
reasoning.*       - 推理鏈引擎
navigation.*      - 導航菜單
settings.*        - 系統設置
error.*           - 錯誤訊息
validation.*      - 表單驗證
```

## 最佳實踐

### 命名約定

- 使用小寫字母和下劃線
- 使用描述性的鍵名
- 遵循現有的分類結構

```javascript
// ✅ 好的命名
t('file.upload_success');
t('auth.invalid_credentials');

// ❌ 避免
t('msg1');
t('text');
```

### 保持一致性

- 在整個應用中使用相同的術語
- 確保所有語言版本包含相同的鍵
- 定期審查和更新翻譯

### 性能優化

- 翻譯數據在應用啟動時一次性加載
- 使用 `useCallback` 優化翻譯函數
- 語言切換後自動重新加載翻譯

### 錯誤處理

- 當翻譯鍵不存在時，返回鍵本身（便於調試）
- 在控制台輸出警告（開發模式）
- 提供後備語言機制

## 測試

### 後端測試

```python
# test_i18n.py
from app.i18n import get_translator, get_available_locales

def test_translator():
    t = get_translator("zh")
    assert t("common.welcome") == "歡迎使用 LabFlow"

    t = get_translator("en")
    assert t("common.welcome") == "Welcome to LabFlow"

def test_available_locales():
    locales = get_available_locales()
    assert "zh" in locales
    assert "en" in locales
```

### 前端測試

```jsx
// i18n.test.jsx
import { render } from '@testing-library/react';
import { I18nProvider, useTranslation } from './i18n';

test('translates text correctly', () => {
  const TestComponent = () => {
    const { t } = useTranslation();
    return <div>{t('common.welcome')}</div>;
  };

  const { getByText } = render(
    <I18nProvider>
      <TestComponent />
    </I18nProvider>
  );

  expect(getByText('歡迎使用 LabFlow')).toBeInTheDocument();
});
```

## 故障排除

### 翻譯未顯示

1. 檢查 JSON 文件格式是否正確
2. 確認翻譯鍵路徑是否正確
3. 查看瀏覽器控制台是否有錯誤
4. 重啟後端服務以重新加載翻譯文件

### 語言切換不生效

1. 清除瀏覽器的 localStorage
2. 檢查 API 端點是否正常響應
3. 確認 I18nProvider 正確包裹了應用

### 新語言未出現

1. 確認 JSON 文件在 `app/locales/` 目錄下
2. 檢查文件名與語言代碼是否匹配
3. 重啟後端服務
4. 更新前端的 SUPPORTED_LOCALES

## 技術細節

### 後端實現

- 使用單例模式管理 i18n 實例
- 支持深度嵌套的翻譯結構
- 自動加載 `locales` 目錄下的所有 JSON 文件
- 支持參數化翻譯（使用 `{param}` 語法）

### 前端實現

- 使用 React Context API 管理全局狀態
- 翻譯數據從後端 API 動態加載
- 語言設置持久化到 localStorage
- 提供多種使用方式（Hook、組件、函數）

## 未來計劃

- [ ] 支持更多語言（日文、韓文、德文等）
- [ ] 翻譯管理後台（GUI 編輯器）
- [ ] 自動翻譯建議（機器翻譯輔助）
- [ ] 翻譯完整性檢查工具
- [ ] 支持 RTL（從右到左）語言
- [ ] 數字、日期、貨幣的本地化格式
- [ ] 複數形式處理
- [ ] 性別化翻譯

## 維護者

LabFlow Development Team

## 授權

本模塊遵循 LabFlow 項目的整體授權協議。

## 更新日誌

### v1.0.0 (2026-02-17)

- ✨ 初始發布
- 🌐 支持中文和英文
- 🔌 提供完整的後端和前端 API
- 📚 完整的使用文檔
- 🎨 美觀的語言切換器 UI

---

如有任何問題或建議，請提交 Issue 或聯繫開發團隊。
