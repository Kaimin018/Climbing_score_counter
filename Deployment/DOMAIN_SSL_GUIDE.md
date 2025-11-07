# 域名綁定與 SSL 配置完整指南

本指南詳細說明如何為您的 EC2 實例綁定域名並配置 SSL 證書（HTTPS）。

## 📋 前置需求

1. ✅ EC2 實例已運行並可以訪問
2. ✅ 已有一個域名（例如：`countclimbingscore.online`）
3. ✅ 域名註冊商的管理權限
4. ✅ EC2 實例的 Public IP 地址

## 第一部分：綁定域名

### 步驟 1: 獲取 EC2 Public IP

1. 登入 AWS Console
2. 進入 EC2 → Instances
3. 選擇您的實例
4. 複製 **Public IPv4 address**（例如：`3.26.6.19`）

### 步驟 2: 配置 DNS A 記錄

在您的域名註冊商（如 Namecheap、GoDaddy、Cloudflare 等）的 DNS 管理界面中：

#### 2.1 添加主域名 A 記錄

| 欄位 | 值 | 說明 |
|------|-----|------|
| **類型** | `A` | A 記錄用於將域名指向 IP 地址 |
| **主機記錄/名稱** | `@` 或留空 | 表示主域名 |
| **值/指向/目標** | `3.26.6.19` | 您的 EC2 Public IP |
| **TTL** | `600` 或自動 | 緩存時間（秒） |

#### 2.2 添加 www 子域名 A 記錄

| 欄位 | 值 | 說明 |
|------|-----|------|
| **類型** | `A` | A 記錄 |
| **主機記錄/名稱** | `www` | www 子域名 |
| **值/指向/目標** | `3.26.6.19` | 您的 EC2 Public IP |
| **TTL** | `600` 或自動 | 緩存時間 |

#### 2.3 DNS 配置示例

```
類型    主機記錄    值            TTL
A       @          3.26.6.19     600
A       www        3.26.6.19     600
```

**不同註冊商的界面可能不同**：
- **Namecheap**: Advanced DNS → Add New Record
- **GoDaddy**: DNS Management → Add Record
- **Cloudflare**: DNS → Add record

### 步驟 3: 等待 DNS 生效

DNS 記錄通常需要 **5 分鐘到 48 小時** 才能完全生效。

**檢查 DNS 是否生效**：

```bash
# Windows (PowerShell)
nslookup countclimbingscore.online
nslookup www.countclimbingscore.online

# macOS/Linux
dig countclimbingscore.online
dig www.countclimbingscore.online

# 或在線工具
# https://www.whatsmydns.net/
```

**成功標誌**：命令返回您的 EC2 IP 地址（`3.26.6.19`）

### 步驟 4: 更新 EC2 配置

#### 4.1 更新 Nginx 配置

SSH 連接到 EC2：

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip
```

編輯 Nginx 配置：

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

更新 `server_name` 行：

```nginx
server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
```

**注意**：將 `countclimbingscore.online` 替換為您的實際域名

測試並重載 Nginx：

```bash
# 測試配置語法
sudo nginx -t

# 如果測試通過，重載配置
sudo systemctl reload nginx
```

#### 4.2 更新 Systemd 服務配置

編輯服務文件：

```bash
sudo nano /etc/systemd/system/climbing_system.service
```

更新環境變數：

```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"
Environment="CORS_ALLOWED_ORIGINS=https://countclimbingscore.online,https://www.countclimbingscore.online"
```

**注意**：將域名替換為您的實際域名

重新加載並重啟服務：

```bash
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
```

### 步驟 5: 測試域名訪問

```bash
# 在本地電腦測試
curl -I http://countclimbingscore.online
curl -I http://www.countclimbingscore.online

# 或在瀏覽器中訪問
# http://countclimbingscore.online
```

**成功標誌**：返回 `200 OK` 狀態碼

## 第二部分：配置 SSL 證書（HTTPS）

### 步驟 1: 安裝 Certbot

Certbot 是 Let's Encrypt 的官方工具，用於自動獲取和續期 SSL 證書。

```bash
# 更新系統套件
sudo apt update

# 安裝 Certbot 和 Nginx 插件
sudo apt install -y certbot python3-certbot-nginx
```

### 步驟 2: 確保端口開放

在 AWS EC2 安全組中，確保以下端口已開放：

- **端口 80 (HTTP)**: 允許所有流量（`0.0.0.0/0`）- Let's Encrypt 驗證需要
- **端口 443 (HTTPS)**: 允許所有流量（`0.0.0.0/0`）- HTTPS 訪問需要

**檢查方法**：
1. AWS Console → EC2 → Security Groups
2. 選擇您的安全組
3. 檢查 Inbound rules

### 步驟 3: 獲取 SSL 證書

**重要**：確保 DNS 已生效（步驟 1-5 已完成）

```bash
# 獲取 SSL 證書（Certbot 會自動配置 Nginx）
sudo certbot --nginx -d countclimbingscore.online -d www.countclimbingscore.online
```

**替換域名**：將 `countclimbingscore.online` 替換為您的實際域名

**Certbot 會詢問**：
1. **Email 地址**：輸入您的郵箱（用於證書到期提醒）
2. **同意服務條款**：輸入 `A` 同意
3. **是否分享郵箱**：可選，輸入 `N` 跳過

**Certbot 會自動**：
- ✅ 驗證域名所有權
- ✅ 獲取 SSL 證書
- ✅ 配置 Nginx 使用 HTTPS
- ✅ 設置 HTTP 到 HTTPS 的自動重定向

### 步驟 4: 驗證 SSL 配置

#### 4.1 檢查證書狀態

```bash
# 查看已安裝的證書
sudo certbot certificates
```

#### 4.2 測試 HTTPS 訪問

```bash
# 在本地測試
curl -I https://countclimbingscore.online
curl -I https://www.countclimbingscore.online

# 或在瀏覽器中訪問
# https://countclimbingscore.online
```

**成功標誌**：
- 瀏覽器顯示 🔒 鎖圖標
- URL 顯示 `https://`
- 無安全警告

#### 4.3 測試 HTTP 重定向

訪問 `http://countclimbingscore.online`，應該自動重定向到 `https://countclimbingscore.online`

### 步驟 5: 配置自動續期

Let's Encrypt 證書有效期為 90 天，需要定期續期。

#### 5.1 測試自動續期

```bash
# 測試續期流程（不會真正續期）
sudo certbot renew --dry-run
```

**成功標誌**：顯示 "The dry run was successful"

#### 5.2 確認自動續期已配置

Certbot 會自動創建 systemd timer 或 cron 任務：

```bash
# 檢查 systemd timer
systemctl list-timers | grep certbot

# 或檢查 cron 任務
sudo crontab -l | grep certbot
```

**自動續期**：Certbot 會在證書到期前 30 天自動續期

### 步驟 6: 更新 Django 設置（啟用 HTTPS）

配置 SSL 後，更新 systemd 服務文件以啟用 HTTPS 安全設置：

```bash
sudo nano /etc/systemd/system/climbing_system.service
```

添加或更新以下環境變數：

```ini
Environment="USE_HTTPS=True"
Environment="SECURE_SSL_REDIRECT=True"
Environment="SESSION_COOKIE_SECURE=True"
Environment="CSRF_COOKIE_SECURE=True"
```

重新加載並重啟服務：

```bash
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
```

## 驗證清單

### 域名綁定驗證

- [ ] DNS A 記錄已配置（@ 和 www）
- [ ] DNS 已生效（`nslookup` 返回正確 IP）
- [ ] Nginx `server_name` 已更新
- [ ] Systemd `ALLOWED_HOSTS` 已更新
- [ ] 可以通過域名訪問（HTTP）

### SSL 配置驗證

- [ ] Certbot 已安裝
- [ ] SSL 證書已獲取
- [ ] Nginx 已配置 HTTPS
- [ ] HTTP 自動重定向到 HTTPS
- [ ] 可以通過 HTTPS 訪問
- [ ] 證書自動續期已配置
- [ ] Django HTTPS 設置已啟用

## 故障排除

### 問題 1: DNS 未生效

**症狀**：`nslookup` 返回錯誤或舊 IP

**解決方法**：
1. 等待更長時間（最多 48 小時）
2. 檢查 DNS 記錄是否正確
3. 清除本地 DNS 緩存：
   ```bash
   # Windows
   ipconfig /flushdns
   
   # macOS
   sudo dscacheutil -flushcache
   
   # Linux
   sudo systemd-resolve --flush-caches
   ```

### 問題 2: SSL 證書獲取失敗

**症狀**：`certbot` 命令失敗

**常見錯誤**：
- `Failed to connect to host`：DNS 未生效或端口 80 未開放
- `The domain name does not point to this server`：DNS 記錄錯誤

**解決方法**：
1. 確認 DNS 已生效（`nslookup` 返回正確 IP）
2. 確認端口 80 已開放（AWS 安全組）
3. 確認 Nginx 正在運行：`sudo systemctl status nginx`
4. 檢查 Nginx 配置：`sudo nginx -t`
5. 查看詳細錯誤：`sudo certbot --nginx -d your-domain.com -d www.your-domain.com --verbose`

### 問題 3: 域名無法訪問

**症狀**：瀏覽器顯示 "無法訪問此網站"

**檢查步驟**：
1. **檢查 DNS**：
   ```bash
   nslookup countclimbingscore.online
   ```

2. **檢查 AWS 安全組**：
   - 端口 80 (HTTP) 是否開放
   - 端口 443 (HTTPS) 是否開放（如果已配置 SSL）

3. **檢查 Nginx**：
   ```bash
   sudo systemctl status nginx
   sudo nginx -t
   ```

4. **查看 Nginx 日誌**：
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

### 問題 4: HTTPS 顯示不安全

**症狀**：瀏覽器顯示 "不安全" 警告

**可能原因**：
1. 證書未正確安裝
2. 混合內容（HTTP 和 HTTPS 資源混用）
3. 證書過期

**解決方法**：
1. 檢查證書：`sudo certbot certificates`
2. 重新獲取證書：`sudo certbot --nginx -d your-domain.com -d www.your-domain.com --force-renewal`
3. 檢查網站是否使用 HTTPS 資源（圖片、CSS、JS 等）

## 常用命令

### DNS 檢查

```bash
# 檢查 DNS 解析
nslookup countclimbingscore.online
dig countclimbingscore.online

# 在線工具
# https://www.whatsmydns.net/
```

### SSL 證書管理

```bash
# 查看已安裝的證書
sudo certbot certificates

# 手動續期證書
sudo certbot renew

# 測試續期（不真正續期）
sudo certbot renew --dry-run

# 強制重新獲取證書
sudo certbot --nginx -d your-domain.com -d www.your-domain.com --force-renewal

# 撤銷證書（如果需要）
sudo certbot revoke --cert-path /etc/letsencrypt/live/your-domain.com/cert.pem
```

### Nginx 管理

```bash
# 測試配置
sudo nginx -t

# 查看完整配置
sudo nginx -T

# 查看 server_name
sudo nginx -T | grep server_name

# 重載配置（不中斷服務）
sudo systemctl reload nginx

# 重啟 Nginx
sudo systemctl restart nginx

# 查看狀態
sudo systemctl status nginx
```

### 測試訪問

```bash
# 測試 HTTP
curl -I http://countclimbingscore.online

# 測試 HTTPS
curl -I https://countclimbingscore.online

# 測試重定向
curl -L -I http://countclimbingscore.online
```

## 安全建議

1. **使用 HTTPS**：所有流量都應該通過 HTTPS
2. **定期檢查證書**：確保自動續期正常工作
3. **監控證書到期**：Certbot 會發送郵件提醒
4. **備份證書**：定期備份 `/etc/letsencrypt/` 目錄
5. **使用強密碼**：保護 EC2 實例和域名管理賬戶

## 相關文檔

- `Deployment/AWS_EC2_DEPLOYMENT.md` - 完整部署指南
- `Deployment/SSH_SETUP.md` - SSH 連接配置
- `Deployment/TROUBLESHOOTING_DEPLOYMENT.md` - 故障排除

