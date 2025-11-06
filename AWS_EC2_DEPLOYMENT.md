# AWS EC2 部署指南

本指南說明如何將攀岩計分系統部署到 AWS EC2，使用 SQLite 數據庫、Nginx 反向代理和 Gunicorn WSGI 服務器。

**重要提示**：
- ✅ 首次部署後，後續更新**不需要重新 clone**，只需使用 `git pull` 或 `deploy.sh` 腳本
- ✅ 推薦使用 CI/CD 自動部署流程（見 `DEPLOYMENT_CI_CD.md`）
- ✅ 手動更新時使用 `deploy.sh` 腳本，它會自動處理所有步驟
- ✅ 首次部署可以使用 `setup_ec2.sh` 腳本簡化環境設置
- ✅ 如果遇到虛擬環境路徑問題，使用 `fix_venv_path.sh` 腳本修復
- ✅ **域名配置**：已配置域名 `countclimbingscore.online`，詳細說明見 `DOMAIN_SETUP.md`

## 架構概覽

```
Internet
   ↓
AWS EC2 (Nginx:80)
   ↓
Gunicorn (127.0.0.1:8000)
   ↓
Django Application
   ↓
SQLite Database
```

## 前置需求

1. AWS EC2 實例（建議使用 Ubuntu 22.04 LTS）
2. 域名（可選，也可以使用 IP 地址）
3. SSH 訪問權限

## 步驟 1: 準備 EC2 實例

### 1.1 啟動 EC2 實例

1. 登入 AWS Console
2. 啟動新的 EC2 實例
3. 選擇 Ubuntu 22.04 LTS AMI（推薦）或 Ubuntu 20.04 LTS
4. 建議最小配置：
   - **Instance Type**: t3.micro（免費層）或 t3.small（生產環境）
   - **Storage**: 20GB 或更多（用於存儲媒體文件和日誌）
   - **Key Pair**: 創建或選擇現有的 SSH 密鑰對
5. 配置安全組：
   - **端口 22 (SSH)**: 僅允許您的 IP 地址訪問（提高安全性）
   - **端口 80 (HTTP)**: 允許所有流量（0.0.0.0/0）
   - **端口 443 (HTTPS)**: 允許所有流量（如果使用 SSL）

### 1.2 連接到 EC2 實例

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

## 步驟 2: 安裝系統依賴

### 方法 1: 使用自動設置腳本（推薦）

```bash
# 下載並運行初始設置腳本
cd /var/www/Climbing_score_counter
bash setup_ec2.sh
```

`setup_ec2.sh` 腳本會自動執行：
- 更新系統套件
- 安裝 Python、pip、venv、Nginx、Git 等必要工具
- 創建項目目錄和日誌目錄
- 設置基本權限

### 方法 2: 手動安裝

```bash
# 更新系統
sudo apt update
sudo apt upgrade -y

# 安裝 Python 和必要工具
sudo apt install -y python3 python3-pip python3-venv nginx

# 安裝其他必要工具
sudo apt install -y git curl
```

## 步驟 3: 設置項目目錄

**注意**：如果使用 `setup_ec2.sh` 腳本，此步驟會自動執行。

```bash
# 創建項目目錄
sudo mkdir -p /var/www/Climbing_score_counter
sudo chown -R $USER:$USER /var/www/Climbing_score_counter

# 創建必要的子目錄
mkdir -p /var/www/Climbing_score_counter/logs
mkdir -p /var/www/Climbing_score_counter/backups
mkdir -p /var/www/Climbing_score_counter/media
mkdir -p /var/www/Climbing_score_counter/staticfiles

# 進入目錄
cd /var/www/Climbing_score_counter
```

## 步驟 4: 上傳項目文件

### 方法 1: 使用 Git（強烈推薦）

**首次部署**：

```bash
# 克隆項目到項目目錄
# 注意：請將 your-username 和 repository-name 替換為您的實際 GitHub 用戶名和倉庫名稱
cd /var/www/Climbing_score_counter
git clone https://github.com/your-username/repository-name.git .

# 或克隆到臨時目錄後移動文件
# git clone https://github.com/your-username/repository-name.git /tmp/climbing_system
# sudo mv /tmp/climbing_system/* /var/www/Climbing_score_counter/
# sudo mv /tmp/climbing_system/.* /var/www/Climbing_score_counter/ 2>/dev/null || true
```

**後續更新**（不需要重新 clone）：

```bash
cd /var/www/Climbing_score_counter

# 拉取最新代碼
git fetch origin
git reset --hard origin/main  # 或 origin/master，取決於您的默認分支

# 或使用部署腳本（推薦）
bash deploy.sh
```

**重要提示**：
- ✅ 使用 `git pull` 或 `git reset --hard` 更新代碼，**不需要重新 clone**
- ✅ 首次部署後，後續更新只需執行 `git pull` 或使用 `deploy.sh` 腳本
- ✅ `deploy.sh` 腳本會自動處理代碼更新、依賴安裝、遷移等所有步驟

### 方法 2: 使用 SCP（僅首次部署）

如果不想使用 Git，可以在本地電腦執行：

```bash
scp -r -i your-key.pem \
    climbing_system/ \
    scoring/ \
    templates/ \
    static/ \
    manage.py \
    requirements.txt \
    gunicorn_config.py \
    ubuntu@your-ec2-ip:/var/www/Climbing_score_counter/
```

**注意**：使用 SCP 方式後續更新需要手動上傳文件，建議使用 Git 方式。

## 步驟 5: 設置 Python 虛擬環境

**注意**：如果使用 `deploy.sh` 腳本，虛擬環境會自動創建，此步驟可跳過。

### 手動設置虛擬環境

```bash
cd /var/www/Climbing_score_counter

# 創建虛擬環境
python3 -m venv venv

# 激活虛擬環境
source venv/bin/activate

# 安裝依賴
pip install --upgrade pip
pip install -r requirements.txt
```

### 虛擬環境路徑問題修復

如果遇到虛擬環境路徑錯誤（例如：`-bash: /var/www/climbing_score_counting_system/venv/bin/pip: No such file or directory`），可以使用修復腳本：

```bash
cd /var/www/Climbing_score_counter
bash fix_venv_path.sh
```

詳細說明見「故障排除」章節。

## 步驟 6: 配置 Django 設置

### 6.1 生成新的 SECRET_KEY

```bash
# 確保在虛擬環境中
source venv/bin/activate

# 生成新的 SECRET_KEY
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

複製生成的 SECRET_KEY，稍後在 systemd 服務文件中使用。

### 6.2 設置環境變數

環境變數需要在 systemd 服務文件中設置（見步驟 10）。主要環境變數包括：

- `SECRET_KEY`: Django 密鑰（必須更改）
- `DEBUG`: 設置為 `False`（生產環境）
- `ALLOWED_HOSTS`: 已配置為 `countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost`
- `CORS_ALLOW_ALL_ORIGINS`: 設置為 `False`（生產環境）
- `CORS_ALLOWED_ORIGINS`: 已配置為 `https://countclimbingscore.online,https://www.countclimbingscore.online`

**重要**：不要將 `SECRET_KEY` 提交到 Git 倉庫。使用環境變數或 secrets 管理。

## 步驟 7: 初始化數據庫

```bash
# 確保在虛擬環境中
source venv/bin/activate

# 運行遷移
python manage.py migrate

# 創建超級用戶（可選）
python manage.py createsuperuser
```

## 步驟 8: 收集靜態文件

```bash
# 確保在虛擬環境中
source venv/bin/activate

# 創建靜態文件目錄（如果不存在）
mkdir -p staticfiles

# 收集靜態文件
python manage.py collectstatic --noinput

# 或使用 --clear 選項清除舊文件
python manage.py collectstatic --noinput --clear
```

**注意**：`deploy.sh` 腳本會自動執行此步驟。

## 步驟 9: 配置 Gunicorn

### 9.1 檢查 Gunicorn 配置文件

```bash
# 確保 gunicorn_config.py 在項目根目錄
cd /var/www/Climbing_score_counter
ls -la gunicorn_config.py
```

配置文件 `gunicorn_config.py` 包含以下主要設置：
- `bind`: 綁定地址（`127.0.0.1:8000`）
- `workers`: Worker 進程數（自動根據 CPU 核心數計算）
- `timeout`: 請求超時時間（30 秒）
- `accesslog` 和 `errorlog`: 日誌文件路徑
- `chdir`: 工作目錄（`/var/www/Climbing_score_counter`）

**注意**：通常不需要修改此配置文件，除非有特殊需求。

### 9.2 測試 Gunicorn

```bash
# 激活虛擬環境
source venv/bin/activate

# 設置環境變數
export SECRET_KEY="your-secret-key"
export DEBUG="False"
export ALLOWED_HOSTS="countclimbingscore.online,www.countclimbingscore.online,3.26.6.19"

# 測試運行 Gunicorn
gunicorn --config gunicorn_config.py climbing_system.wsgi:application
```

如果成功，應該能看到 Gunicorn 啟動訊息。按 Ctrl+C 停止。

## 步驟 10: 配置 Systemd 服務

### 10.1 複製服務文件

```bash
# 複製 systemd 服務文件
sudo cp systemd/climbing_system.service /etc/systemd/system/

# 編輯服務文件，設置正確的路徑和環境變數
sudo nano /etc/systemd/system/climbing_system.service
```

### 10.2 修改服務文件

確保以下設置正確：

- `WorkingDirectory`: `/var/www/Climbing_score_counter`
- `User` 和 `Group`: `www-data`（或您的用戶）
- `Environment`: 設置所有必要的環境變數
- `ExecStart`: Gunicorn 命令路徑正確

### 10.3 啟動服務

```bash
# 重新加載 systemd
sudo systemctl daemon-reload

# 啟用服務（開機自動啟動）
sudo systemctl enable climbing_system

# 啟動服務
sudo systemctl start climbing_system

# 檢查狀態
sudo systemctl status climbing_system
```

### 10.4 查看日誌

```bash
# 查看服務日誌
sudo journalctl -u climbing_system -f

# 查看應用日誌
tail -f /var/www/Climbing_score_counter/logs/gunicorn_error.log
```

## 步驟 11: 配置 Nginx

### 11.1 複製 Nginx 配置文件

```bash
# 複製配置文件
sudo cp nginx/climbing_system.conf /etc/nginx/sites-available/

# 創建符號連結
sudo ln -s /etc/nginx/sites-available/climbing_system.conf /etc/nginx/sites-enabled/

# 刪除默認配置（可選）
sudo rm /etc/nginx/sites-enabled/default
```

### 11.2 編輯 Nginx 配置

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

修改以下內容：

- `server_name`: 已配置為 `countclimbingscore.online www.countclimbingscore.online 3.26.6.19`
- 確保所有路徑正確

**注意**：如果使用域名，需要先配置 DNS 記錄（見 `DOMAIN_SETUP.md`）

### 11.3 測試和重載 Nginx

```bash
# 測試配置
sudo nginx -t

# 如果測試通過，重載 Nginx
sudo systemctl reload nginx

# 或重啟 Nginx
sudo systemctl restart nginx

# 檢查狀態
sudo systemctl status nginx
```

## 步驟 12: 設置文件權限

```bash
# 設置項目目錄權限
sudo chown -R www-data:www-data /var/www/Climbing_score_counter
sudo chmod -R 755 /var/www/Climbing_score_counter

# 設置媒體和日誌目錄權限（需要寫入權限）
sudo chmod -R 775 /var/www/Climbing_score_counter/media
sudo chmod -R 775 /var/www/Climbing_score_counter/logs
sudo chmod -R 775 /var/www/Climbing_score_counter/staticfiles
```

## 步驟 13: 創建日誌和備份目錄

```bash
# 創建日誌目錄
mkdir -p /var/www/Climbing_score_counter/logs
sudo chown -R www-data:www-data /var/www/Climbing_score_counter/logs

# 創建備份目錄（用於數據庫和媒體文件備份）
mkdir -p /var/www/Climbing_score_counter/backups
sudo chown -R www-data:www-data /var/www/Climbing_score_counter/backups
```

**注意**：`deploy.sh` 腳本會自動創建日誌目錄。

## 步驟 14: 測試部署

1. 在瀏覽器中訪問 `http://3.26.6.19` 或 `http://countclimbingscore.online`
2. 檢查是否能看到首頁
3. 測試創建房間、上傳圖片等功能

## 步驟 15: 配置 SSL（可選但強烈推薦）

**重要**：配置 SSL 前，請先完成 DNS 配置（見 `DOMAIN_SETUP.md`），確保域名已指向 EC2 IP。

### 使用 Let's Encrypt

```bash
# 安裝 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 獲取 SSL 證書（Certbot 會自動配置 Nginx）
sudo certbot --nginx -d countclimbingscore.online -d www.countclimbingscore.online

# 自動續期測試
sudo certbot renew --dry-run
```

**注意**：
- 確保 DNS 記錄已生效（`nslookup countclimbingscore.online` 應返回 `3.26.6.19`）
- 確保 AWS 安全組已開放 80 和 443 端口
- Certbot 會自動配置 Nginx 使用 HTTPS 並設置 HTTP 重定向

詳細說明請參考 `DOMAIN_SETUP.md`。

## CI/CD 自動部署

系統已配置 GitHub Actions 自動部署流程。詳細說明請參考 `DEPLOYMENT_CI_CD.md`。

### 快速設置

1. **配置 GitHub Secrets**:
   - `EC2_HOST`: EC2 IP 或域名
   - `EC2_USER`: SSH 用戶名（通常是 `ubuntu`）
   - `EC2_SSH_KEY`: SSH 私鑰內容

2. **自動部署**: 推送到 `main`/`master` 分支時自動觸發

3. **手動部署**: 在 GitHub Actions 界面手動觸發

### 優勢

- ✅ **自動化**: 推送代碼後自動部署，無需手動操作
- ✅ **測試先行**: 部署前自動運行測試，確保代碼質量
- ✅ **版本控制**: 每次部署都有完整的 Git 歷史記錄
- ✅ **快速回滾**: 可以輕鬆回滾到之前的版本

## 日常維護

### 更新代碼

**推薦方式：使用部署腳本**

```bash
cd /var/www/Climbing_score_counter
bash deploy.sh
```

部署腳本會自動執行：
1. 拉取最新代碼（如果使用 Git）
2. 更新 Python 依賴
3. 運行數據庫遷移
4. 收集靜態文件
5. 重啟服務

**手動更新方式**：

```bash
cd /var/www/Climbing_score_counter

# 拉取最新代碼（如果使用 Git）
git fetch origin
git reset --hard origin/main  # 或 origin/master

# 激活虛擬環境
source venv/bin/activate

# 更新依賴
pip install --upgrade pip
pip install -r requirements.txt

# 運行遷移
python manage.py migrate --noinput

# 收集靜態文件
python manage.py collectstatic --noinput --clear

# 重啟服務
sudo systemctl restart climbing_system
sudo systemctl reload nginx
```

**重要提示**：
- ✅ **不需要重新 clone**，只需使用 `git pull` 或 `git reset --hard` 更新代碼
- ✅ 建議使用 `deploy.sh` 腳本，它會自動處理所有更新步驟
- ✅ 更新前建議先備份數據庫和重要文件

### 查看日誌

```bash
# Gunicorn 日誌
tail -f /var/www/Climbing_score_counter/logs/gunicorn_error.log
tail -f /var/www/Climbing_score_counter/logs/gunicorn_access.log

# Django 日誌
tail -f /var/www/Climbing_score_counter/logs/django.log

# Nginx 日誌
sudo tail -f /var/log/nginx/climbing_system_error.log
sudo tail -f /var/log/nginx/climbing_system_access.log

# Systemd 服務日誌
sudo journalctl -u climbing_system -f
```

### 重啟服務

```bash
# 重啟 Gunicorn
sudo systemctl restart climbing_system

# 重啟 Nginx
sudo systemctl restart nginx

# 重載配置（不中斷服務）
sudo systemctl reload nginx
```

### 備份數據庫

**重要**：定期備份數據庫和媒體文件，建議設置自動備份任務。

```bash
# 確保備份目錄存在
mkdir -p /var/www/Climbing_score_counter/backups

# 備份 SQLite 數據庫
cp /var/www/Climbing_score_counter/db.sqlite3 \
   /var/www/Climbing_score_counter/backups/db_$(date +%Y%m%d_%H%M%S).sqlite3

# 備份媒體文件
tar -czf /var/www/Climbing_score_counter/backups/media_$(date +%Y%m%d_%H%M%S).tar.gz \
    /var/www/Climbing_score_counter/media/

# 清理舊備份（保留最近 7 天的備份）
find /var/www/Climbing_score_counter/backups -name "db_*.sqlite3" -mtime +7 -delete
find /var/www/Climbing_score_counter/backups -name "media_*.tar.gz" -mtime +7 -delete
```

### 設置自動備份（可選）

創建 cron 任務自動備份：

```bash
# 編輯 crontab
crontab -e

# 添加以下行（每天凌晨 2 點備份）
0 2 * * * /var/www/Climbing_score_counter/backup.sh
```

創建備份腳本 `/var/www/Climbing_score_counter/backup.sh`：

```bash
#!/bin/bash
BACKUP_DIR="/var/www/Climbing_score_counter/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 備份數據庫
cp $BACKUP_DIR/../db.sqlite3 $BACKUP_DIR/db_$DATE.sqlite3

# 備份媒體文件
tar -czf $BACKUP_DIR/media_$DATE.tar.gz $BACKUP_DIR/../media/

# 清理舊備份（保留 7 天）
find $BACKUP_DIR -name "db_*.sqlite3" -mtime +7 -delete
find $BACKUP_DIR -name "media_*.tar.gz" -mtime +7 -delete
```

設置執行權限：

```bash
chmod +x /var/www/Climbing_score_counter/backup.sh
```

## 故障排除

### 虛擬環境路徑錯誤

**問題**: 安裝依賴時出現 `-bash: /var/www/climbing_score_counting_system/venv/bin/pip: No such file or directory`

**原因**: 虛擬環境仍指向舊路徑，但項目已移動到新路徑。

**解決方法**:

1. **使用修復腳本（推薦）**:
   ```bash
   cd /var/www/Climbing_score_counter
   bash fix_venv_path.sh
   ```

2. **手動修復**:
   ```bash
   # 退出當前虛擬環境
   deactivate
   
   # 進入項目目錄
   cd /var/www/Climbing_score_counter
   
   # 如果舊虛擬環境存在，可以刪除或遷移
   # 選項 1: 刪除舊虛擬環境並創建新的
   rm -rf /var/www/climbing_score_counting_system/venv
   python3 -m venv venv
   
   # 選項 2: 遷移舊虛擬環境
   # cp -r /var/www/climbing_score_counting_system/venv venv
   # python3 -m venv --upgrade venv
   
   # 激活新虛擬環境
   source venv/bin/activate
   
   # 驗證路徑
   which python  # 應該顯示 /var/www/Climbing_score_counter/venv/bin/python
   which pip     # 應該顯示 /var/www/Climbing_score_counter/venv/bin/pip
   
   # 安裝依賴
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **更新 shell 配置**（如果問題持續）:
   ```bash
   # 檢查 ~/.bashrc 或 ~/.bash_profile 中是否有舊路徑的虛擬環境激活
   grep -n "climbing_score_counting_system" ~/.bashrc ~/.bash_profile
   
   # 如果有，請編輯並更新路徑
   nano ~/.bashrc
   ```

### Gunicorn 無法啟動

1. 檢查服務狀態：`sudo systemctl status climbing_system`
2. 查看日誌：`sudo journalctl -u climbing_system -n 50`
3. 檢查配置文件路徑和權限
4. 確認環境變數設置正確

### Nginx 502 Bad Gateway

1. 檢查 Gunicorn 是否運行：`sudo systemctl status climbing_system`
2. 檢查端口 8000 是否被監聽：`sudo netstat -tlnp | grep 8000`
3. 查看 Nginx 錯誤日誌：`sudo tail -f /var/log/nginx/climbing_system_error.log`

### 靜態文件無法加載

1. 確認已運行 `collectstatic`
2. 檢查 `STATIC_ROOT` 目錄是否存在且有正確權限
3. 檢查 Nginx 配置中的 `alias` 路徑是否正確

### 媒體文件無法上傳

1. 檢查 `media` 目錄是否存在：`ls -la /var/www/Climbing_score_counter/media`
2. 確認目錄有寫入權限：
   ```bash
   sudo chown -R www-data:www-data /var/www/Climbing_score_counter/media
   sudo chmod -R 775 /var/www/Climbing_score_counter/media
   ```
3. 檢查磁盤空間：`df -h`
4. 檢查 Nginx 配置中的 `client_max_body_size` 設置（應該至少 20M）
5. 查看 Django 日誌：`tail -f /var/www/Climbing_score_counter/logs/django.log`

## 安全建議

1. **更改 SECRET_KEY**: 使用強隨機密鑰
2. **設置 DEBUG=False**: 生產環境必須關閉調試模式
3. **配置 ALLOWED_HOSTS**: 已配置為 `countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost`
4. **使用 HTTPS**: 配置 SSL 證書
5. **定期更新**: 保持系統和依賴包更新
6. **防火牆**: 只開放必要端口
7. **備份**: 定期備份數據庫和媒體文件

## 性能優化

1. **增加 Gunicorn Workers**: 根據 CPU 核心數調整
2. **啟用 Nginx 緩存**: 對靜態文件啟用緩存
3. **使用 CDN**: 將靜態文件放到 CDN（可選）
4. **數據庫優化**: 如果數據量大，考慮遷移到 PostgreSQL

## 聯繫與支持

如有問題，請查看：
- 項目文檔：`ARCHITECTURE.md`
- Django 日誌：`logs/django.log`
- Gunicorn 日誌：`logs/gunicorn_error.log`

