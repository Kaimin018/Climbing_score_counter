# Git 安全目錄問題修復指南

## 問題描述

當在 EC2 服務器上執行 `git fetch` 或 `git pull` 時，可能會遇到以下錯誤：

```
fatal: detected dubious ownership in repository at '/var/www/Climbing_score_counter'
To add an exception for this directory, call:
        git config --global --add safe.directory /var/www/Climbing_score_counter
```

## 問題原因

這是 Git 的安全機制。當 Git 檢測到倉庫目錄的所有者與當前執行 Git 命令的用戶不匹配時，會拒絕操作以防止潛在的安全風險。

常見情況：
- 項目目錄屬於 `www-data` 用戶（Nginx/Gunicorn 運行用戶）
- 但以 `ubuntu` 用戶身份執行 Git 命令

## 解決方案

### 方案 1: 添加安全目錄例外（推薦）

這是最簡單且安全的方法：

```bash
# 在 EC2 服務器上執行
git config --global --add safe.directory /var/www/Climbing_score_counter
```

**優點**:
- 快速解決問題
- 不影響目錄權限
- 保持 `www-data` 用戶對目錄的訪問權限

**注意**: 此命令只需要執行一次，配置會保存到 `~/.gitconfig`

### 方案 2: 修改目錄所有者

如果需要，可以將目錄所有者改為當前用戶：

```bash
# 在 EC2 服務器上執行
sudo chown -R ubuntu:ubuntu /var/www/Climbing_score_counter
```

**注意**: 
- 這會改變目錄所有者，可能影響 Nginx/Gunicorn 的訪問權限
- 需要確保 `www-data` 用戶仍有讀寫權限（通過組權限或 ACL）

### 方案 3: 使用部署腳本（自動處理）

`deploy.sh` 腳本會自動檢測並配置 Git 安全目錄，無需手動處理：

```bash
bash Deployment/deploy.sh
```

## 驗證修復

執行以下命令驗證問題是否已解決：

```bash
cd /var/www/Climbing_score_counter
git fetch origin
```

如果沒有錯誤訊息，說明問題已解決。

## 檢查當前配置

查看已配置的安全目錄：

```bash
git config --global --get-all safe.directory
```

## 相關文檔

- `AWS_EC2_DEPLOYMENT.md` - 完整部署指南
- `TROUBLESHOOTING_DEPLOYMENT.md` - 故障排除指南

