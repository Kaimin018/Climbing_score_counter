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

## 問題 2: Permission denied 錯誤

如果配置安全目錄後仍然出現以下錯誤：

```
error: cannot open .git/FETCH_HEAD: Permission denied
```

**原因**: `.git` 目錄屬於 `www-data` 用戶，而當前以 `ubuntu` 用戶執行 Git 命令，沒有寫入權限。

**解決方案**:

### 方案 1: 修改 .git 目錄所有者（推薦）

將 `.git` 目錄的所有者改為 `ubuntu` 用戶，這樣可以執行 Git 操作，同時不影響項目其他文件：

```bash
# 在 EC2 服務器上執行
cd /var/www/Climbing_score_counter
sudo chown -R ubuntu:ubuntu .git
```

**優點**:
- 只修改 `.git` 目錄，不影響項目文件
- `www-data` 用戶仍可正常訪問項目文件
- 解決 Git 操作權限問題

### 方案 2: 添加組權限

將 `ubuntu` 用戶添加到 `www-data` 組，並給 `.git` 目錄添加組寫權限：

```bash
# 將 ubuntu 添加到 www-data 組
sudo usermod -a -G www-data ubuntu

# 給 .git 目錄添加組寫權限
sudo chmod -R g+w /var/www/Climbing_score_counter/.git

# 重新登錄以使組變更生效
exit
# 重新 SSH 登錄
```

### 方案 3: 使用 sudo 執行 Git 命令（臨時方案）

如果只是臨時需要，可以使用 `sudo`：

```bash
sudo -u ubuntu git fetch origin
```

**注意**: 不推薦長期使用此方案。

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

