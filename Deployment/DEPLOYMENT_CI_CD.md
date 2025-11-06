# CI/CD 自動部署指南

本指南說明如何設置 GitHub Actions 自動部署到 AWS EC2。

## 概述

系統提供兩種部署方式：
1. **自動部署** (`deploy.yml`): 推送到 main/master 分支時自動部署
2. **手動部署** (`deploy-manual.yml`): 通過 GitHub Actions 界面手動觸發部署

## 前置需求

1. GitHub 倉庫
2. AWS EC2 實例已設置並運行
3. EC2 實例已配置 SSH 訪問
4. 項目已通過 Git 部署到 EC2（見 `Deployment/AWS_EC2_DEPLOYMENT.md`）

## 步驟 1: 配置 GitHub Secrets

在 GitHub 倉庫設置中添加以下 Secrets：

1. 進入倉庫：`Settings` → `Secrets and variables` → `Actions`
2. 點擊 `New repository secret`，添加以下 secrets：

### 必需的 Secrets

- **`EC2_HOST`**: EC2 實例的 IP 地址或域名
  - 例如：`54.123.45.67` 或 `your-domain.com`

- **`EC2_USER`**: SSH 用戶名
  - Ubuntu: `ubuntu`
  - Amazon Linux: `ec2-user`
  - 其他: 根據您的 AMI 調整

- **`EC2_SSH_KEY`**: SSH 私鑰內容
  - 複製您的 `.pem` 文件的完整內容（包括 `-----BEGIN RSA PRIVATE KEY-----` 和 `-----END RSA PRIVATE KEY-----`）

### 設置示例

```bash
# 在本地查看私鑰內容
cat your-key.pem

# 複製完整內容（包括首尾標記）到 GitHub Secrets
```

## 步驟 2: 配置 EC2 實例

### 2.1 確保 Git 倉庫已設置

在 EC2 實例上：

```bash
cd /var/www/Climbing_score_counter

# 確認 Git 倉庫已初始化
git remote -v

# 如果沒有，設置遠程倉庫
git remote add origin https://github.com/your-username/climbing_score_counting_system.git
```

### 2.2 設置 Git 憑證（可選）

如果使用私有倉庫，需要設置 Git 憑證：

```bash
# 方法 1: 使用 Personal Access Token
git remote set-url origin https://YOUR_TOKEN@github.com/your-username/climbing_score_counting_system.git

# 方法 2: 使用 SSH 密鑰
# 在 EC2 上生成 SSH 密鑰並添加到 GitHub
ssh-keygen -t rsa -b 4096 -C "ec2-deploy@your-domain.com"
cat ~/.ssh/id_rsa.pub
# 將公鑰添加到 GitHub Settings → SSH and GPG keys
git remote set-url origin git@github.com:your-username/climbing_score_counting_system.git
```

### 2.3 確保部署腳本可執行

```bash
chmod +x /var/www/Climbing_score_counter/deploy.sh
```

## 步驟 3: 測試自動部署

### 3.1 觸發自動部署

1. 推送代碼到 `main` 或 `master` 分支：
   ```bash
   git push origin main
   ```

2. 在 GitHub 上查看 Actions：
   - 進入倉庫 → `Actions` 標籤
   - 查看 "Deploy to AWS EC2" 工作流執行情況

### 3.2 手動觸發部署

1. 進入 GitHub 倉庫
2. 點擊 `Actions` 標籤
3. 選擇 "Manual Deploy to AWS EC2" 工作流
4. 點擊 `Run workflow`
5. 選擇要部署的分支
6. 點擊 `Run workflow` 按鈕

## 部署流程說明

### 自動部署流程 (`deploy.yml`)

1. **觸發條件**:
   - 推送到 `main` 或 `master` 分支
   - 創建版本標籤（`v*`）
   - 手動觸發

2. **執行步驟**:
   - ✅ 檢出代碼
   - ✅ 運行測試（確保代碼質量）
   - ✅ 配置 SSH 連接
   - ✅ 連接到 EC2 並執行部署
   - ✅ 驗證部署結果

3. **部署操作**:
   - 拉取最新代碼（`git fetch` + `git reset --hard`）
   - 執行 `deploy.sh` 腳本
   - 自動處理依賴、遷移、靜態文件等

### 手動部署流程 (`deploy-manual.yml`)

1. **觸發方式**: 通過 GitHub Actions 界面手動觸發

2. **可選參數**:
   - **分支選擇**: 選擇要部署的分支（main/master/develop）
   - **跳過測試**: 可選，用於緊急部署

3. **執行步驟**: 與自動部署相同，但可以選擇分支

## 部署腳本詳情

`deploy.sh` 會自動執行以下操作：

```bash
1. 拉取最新代碼（git fetch + git reset --hard）
2. 激活虛擬環境
3. 更新 Python 依賴
4. 運行數據庫遷移
5. 收集靜態文件
6. 創建日誌目錄
7. 設置文件權限
8. 重啟 Gunicorn 服務
9. 重載 Nginx
```

## 故障排除

### 部署失敗：SSH 連接錯誤

**問題**: `Permission denied (publickey)`

**解決方案**:
1. 檢查 `EC2_SSH_KEY` secret 是否正確（包含完整私鑰內容）
2. 確認私鑰格式正確（包括首尾標記）
3. 檢查 EC2 安全組是否允許來自 GitHub Actions 的連接

### 部署失敗：Git 拉取錯誤

**問題**: `fatal: not a git repository`

**解決方案**:
```bash
# 在 EC2 上檢查
cd /var/www/Climbing_score_counter
git remote -v

# 如果沒有遠程倉庫，設置它
git remote add origin https://github.com/your-username/climbing_score_counting_system.git
```

### 部署失敗：權限錯誤

**問題**: `Permission denied`

**解決方案**:
```bash
# 在 EC2 上檢查文件權限
ls -la /var/www/Climbing_score_counter/deploy.sh

# 確保腳本可執行
chmod +x /var/www/Climbing_score_counter/deploy.sh

# 確保目錄權限正確
sudo chown -R www-data:www-data /var/www/Climbing_score_counter
```

### 部署成功但服務未更新

**問題**: 代碼已更新但網站未反映變化

**解決方案**:
1. 檢查服務狀態：`sudo systemctl status climbing_system`
2. 查看日誌：`sudo journalctl -u climbing_system -n 50`
3. 確認 `deploy.sh` 已重啟服務
4. 手動重啟：`sudo systemctl restart climbing_system`

## 安全建議

1. **使用 GitHub Secrets**: 永遠不要將 SSH 密鑰提交到代碼倉庫
2. **限制 SSH 訪問**: 在 EC2 安全組中只允許必要的 IP 訪問
3. **使用部署用戶**: 創建專用的部署用戶，而不是使用 root
4. **定期輪換密鑰**: 定期更新 SSH 密鑰
5. **審計日誌**: 定期檢查部署日誌和訪問日誌

## 最佳實踐

1. **測試優先**: 自動部署會先運行測試，確保代碼質量
2. **分支策略**: 
   - `main/master`: 生產環境，自動部署
   - `develop`: 開發環境，手動部署
3. **版本標籤**: 使用版本標籤（`v1.0.0`）觸發部署，便於追蹤
4. **回滾機制**: 保留之前的版本，必要時可以快速回滾
5. **通知機制**: 配置 Slack/Email 通知，及時了解部署狀態

## 回滾部署

如果需要回滾到之前的版本：

```bash
# 在 EC2 上執行
cd /var/www/Climbing_score_counter

# 查看提交歷史
git log --oneline -10

# 回滾到指定版本
git reset --hard <commit-hash>

# 執行部署腳本
bash deploy.sh
```

或通過 GitHub Actions 手動部署指定分支/標籤。

## 相關文檔

- `Deployment/AWS_EC2_DEPLOYMENT.md` - 初始部署指南
- `deploy.sh` - 部署腳本詳情
- `QUICK_START.md` - 快速參考

