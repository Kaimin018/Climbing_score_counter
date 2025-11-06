# 自動部署故障排除指南

## 問題：本地代碼已更新但 AWS 沒有更改

### 快速診斷步驟

1. **檢查 GitHub Actions 是否觸發**
   - 進入 GitHub 倉庫 → `Actions` 標籤
   - 查看是否有 "Deploy to AWS EC2" 工作流執行
   - 如果沒有執行，檢查是否已推送到 `main`/`master` 分支

2. **檢查 GitHub Secrets 配置**
   - 進入 `Settings` → `Secrets and variables` → `Actions`
   - 確認以下 secrets 已配置：
     - `EC2_HOST`: EC2 IP 或域名
     - `EC2_USER`: SSH 用戶名（通常是 `ubuntu`）
     - `EC2_SSH_KEY`: SSH 私鑰完整內容

3. **檢查部署工作流日誌**
   - 在 GitHub Actions 中點擊失敗的工作流
   - 查看 "Deploy to EC2" 步驟的日誌
   - 查找錯誤訊息

### 常見問題及解決方案

#### 問題 1: 工作流未觸發

**症狀**: 推送代碼後沒有看到 GitHub Actions 執行

**可能原因**:
- 代碼未推送到 `main`/`master` 分支
- 工作流文件語法錯誤
- GitHub Actions 被禁用

**解決方案**:
```bash
# 確認當前分支
git branch

# 確認已推送到遠程
git push origin main

# 檢查工作流文件語法
# 在 GitHub 上查看 Actions 標籤是否有錯誤提示
```

#### 問題 2: Secrets 未配置或配置錯誤

**症狀**: 日誌顯示 "⚠️ 跳過部署：未配置 EC2 secrets"

**解決方案**:
1. 檢查 GitHub Secrets 是否正確配置
2. 確認 `EC2_SSH_KEY` 包含完整的私鑰內容（包括首尾標記）
3. 確認 `EC2_HOST` 是正確的 IP 或域名
4. 確認 `EC2_USER` 是正確的 SSH 用戶名

#### 問題 3: SSH 連接失敗

**症狀**: `Permission denied (publickey)` 或連接超時

**解決方案**:
```bash
# 在本地測試 SSH 連接
ssh -i your-key.pem ubuntu@your-ec2-ip

# 檢查 EC2 安全組是否允許來自 GitHub Actions 的連接
# 可能需要添加 GitHub Actions IP 範圍到安全組
```

#### 問題 4: Git 拉取失敗

**症狀**: `fatal: not a git repository` 或 `fatal: Could not read from remote repository`

**解決方案**:
在 EC2 上執行：
```bash
cd /var/www/Climbing_score_counter

# 檢查 Git 遠程倉庫
git remote -v

# 如果沒有，設置遠程倉庫
git remote add origin https://github.com/your-username/Climbing_score_counter.git

# 如果是私有倉庫，需要設置認證
# 方法 1: 使用 Personal Access Token
git remote set-url origin https://YOUR_TOKEN@github.com/your-username/Climbing_score_counter.git

# 方法 2: 使用 SSH（推薦）
# 在 EC2 上生成 SSH 密鑰並添加到 GitHub
ssh-keygen -t rsa -b 4096 -C "ec2-deploy@your-domain.com"
cat ~/.ssh/id_rsa.pub
# 將公鑰添加到 GitHub Settings → SSH and GPG keys
git remote set-url origin git@github.com:your-username/Climbing_score_counter.git
```

#### 問題 5: 部署腳本執行失敗

**症狀**: `錯誤: 找不到 deploy.sh 腳本` 或權限錯誤

**解決方案**:
在 EC2 上執行：
```bash
cd /var/www/Climbing_score_counter

# 檢查文件是否存在
ls -la deploy.sh

# 確保腳本可執行
chmod +x deploy.sh

# 檢查目錄權限
sudo chown -R www-data:www-data /var/www/Climbing_score_counter
```

#### 問題 6: 代碼已更新但服務未重啟

**症狀**: 代碼已拉取但網站未反映變化

**解決方案**:
```bash
# 檢查服務狀態
sudo systemctl status climbing_system

# 查看服務日誌
sudo journalctl -u climbing_system -n 50

# 手動重啟服務
sudo systemctl restart climbing_system
sudo systemctl reload nginx

# 檢查靜態文件是否已更新
ls -la /var/www/Climbing_score_counter/staticfiles/
```

### 手動觸發部署

如果自動部署失敗，可以手動觸發：

1. **使用 GitHub Actions 手動觸發**:
   - 進入 GitHub 倉庫 → `Actions` 標籤
   - 選擇 "Deploy to AWS EC2" 工作流
   - 點擊 "Run workflow" 按鈕

2. **在 EC2 上手動執行部署**:
   ```bash
   cd /var/www/Climbing_score_counter
   bash Deployment/deploy.sh
   ```

### 驗證部署

部署完成後，驗證更改是否生效：

```bash
# 檢查 Git 提交歷史
cd /var/www/Climbing_score_counter
git log --oneline -5

# 檢查文件修改時間
ls -la templates/index.html
ls -la static/css/style.css

# 檢查服務是否運行
sudo systemctl status climbing_system

# 測試網站訪問
curl -I http://your-domain.com
```

### 調試技巧

1. **啟用詳細日誌**:
   在 `deploy.sh` 中添加 `set -x` 來顯示每個執行的命令

2. **檢查工作流日誌**:
   - GitHub Actions 會保存所有執行日誌
   - 查看完整的錯誤訊息和堆棧跟踪

3. **測試 SSH 連接**:
   在本地使用相同的 SSH 密鑰測試連接到 EC2

4. **檢查 EC2 資源**:
   - 確認 EC2 實例正在運行
   - 檢查安全組規則
   - 查看 CloudWatch 日誌（如果啟用）

### 聯繫支持

如果以上步驟都無法解決問題，請提供以下信息：

1. GitHub Actions 工作流執行日誌
2. EC2 上的部署日誌（`/var/www/Climbing_score_counter/logs/`）
3. 服務狀態（`sudo systemctl status climbing_system`）
4. Git 遠程倉庫配置（`git remote -v`）

