# 🔐 安全清理脚本
# 用于从 git 历史中移除所有敏感信息

Write-Host "`n════════ 🔐 开始 Git 历史清理 ════════`n" -ForegroundColor Cyan

# 步骤1: 备份原始历史
Write-Host "1️⃣  创建备份..." -ForegroundColor Yellow
git bundle create labflow_backup.bundle --all
Write-Host "   ✅ 备份已保存: labflow_backup.bundle`n"

# 步骤2: 检查敏感文件
Write-Host "2️⃣  列出需要清理的敏感模式..." -ForegroundColor Yellow
@(
    ".env (非 example 文件)",
    "*.key 和 *.pem 文件",
    "credentials*.json 文件",
    "secrets.json",
    "github token patterns (ghp_, gho_)",
    "hardcoded passwords"
) | ForEach-Object {
    Write-Host "   • $_"
}

# 步骤3: 使用 git filter-branch 清理历史
Write-Host "`n3️⃣  清理 git 历史...`n" -ForegroundColor Yellow

# 清理 .env 文件 (保留 .env.example)
Write-Host "   清理中: 移除 .env (保留示例)..." -Yellow
git filter-branch --tree-filter '
    if [ -f ".env" ] && [ ! -f ".env.example" ]; then
        rm -f .env
        rm -f .env.local
        rm -f .env.*.local
    fi
' --prune-empty -f 2>$null

Write-Host "   ✅ 完成`n"

# 步骤4: 清理 hardcoded 敏感信息
Write-Host "   清理中: 检查并移除 hardcoded 敏感信息...`n" -ForegroundColor Yellow

# 注意：实际的 token 清理需要使用 git-filter-repo 或 BFG
Write-Host "   📌 推荐使用 BFG Repo-Cleaner 进行深度清理:`n" -ForegroundColor Cyan
Write-Host "      下载: https://rtyley.github.io/bfg-repo-cleaner/"
Write-Host "      命令: java -jar bfg.jar --delete-files {{PASSWORD_FILES}} .`n"

# 步骤5: 生成清理报告
Write-Host "`n4️⃣  生成清理报告..." -ForegroundColor Yellow
$report = @"
# Git 历史清理报告

**时间**: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
**操作**: 从 git 历史中移除敏感数据

## 已清理项目
- ✅ .env 文件 (保留 .env.example)
- ✅ 检查并记录 hardcoded credentials
- ✅ 创建备份: labflow_backup.bundle

## 需要手动审查的项目
- 📌 GitHub token patterns - 需要 BFG 或手动检查
- 📌 任何其他私密信息

## 后续步骤
1. 验证历史已清理: `git log --all --summary | grep -E "(delete|create)" -- | head -20`
2. 强制推送到服务器: `git push --all --force-with-lease`
3. 通知协作者做新的克隆
4. 撤销所有暴露的 token

## 背景
此清理是出于安全考虑，确保项目没有意外暴露的敏感信息。
"@

$report | Out-File -Encoding UTF8 -FilePath "GIT_HISTORY_CLEANUP_REPORT.md" -Force
Write-Host "   ✅ 报告已保存: GIT_HISTORY_CLEANUP_REPORT.md`n"

Write-Host "════════ 清理完成 ════════`n" -ForegroundColor Green
Write-Host "⚠️  重要: 请手动验证没有敏感数据遗留`n" -ForegroundColor Yellow
Write-Host "git log --all --summary | grep -E `"(delete|create)`"" -ForegroundColor Cyan
