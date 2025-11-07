# 為什麼部署到新網域之後原本的 IP 就不能用了？

## 🔍 問題原因

當您將應用部署到新域名後，如果配置不完整，原本的 IP 地址訪問可能會失效。主要有兩個原因：

### 原因 1: Django ALLOWED_HOSTS 配置

**Django 的安全機制**：
- Django 會檢查請求的 `Host` 頭部
- 只有 `ALLOWED_HOSTS` 中列出的主機名/IP 才能訪問
- 如果 IP 地址不在 `ALLOWED_HOSTS` 中，Django 會返回 **400 Bad Request** 錯誤

**常見情況**：
- 部署到新域名時，只配置了新域名
- 忘記將原來的 IP 地址加入 `ALLOWED_HOSTS`
- 結果：通過 IP 訪問時被 Django 拒絕

### 原因 2: Nginx server_name 配置

**Nginx 的路由機制**：
- `server_name` 指定哪些主機名/IP 可以訪問這個 server 塊
- 如果 IP 地址不在 `server_name` 中，Nginx 可能：
  - 使用默認 server 塊（可能配置不正確）
  - 返回 404 或無法正確路由請求

## ✅ 解決方案

### 步驟 1: 檢查當前配置

在 EC2 服務器上執行：

```bash
# 檢查 Django ALLOWED_HOSTS 配置
sudo cat /etc/systemd/system/climbing_system.service | grep ALLOWED_HOSTS

# 檢查 Nginx server_name 配置
sudo nginx -T | grep server_name
```

### 步驟 2: 更新 Django ALLOWED_HOSTS

編輯 systemd 服務文件：

```bash
sudo nano /etc/systemd/system/climbing_system.service
```

找到 `Environment="ALLOWED_HOSTS=..."` 這一行，確保**同時包含域名和 IP 地址**：

```ini
Environment="ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-ec2-ip,127.0.0.1,localhost"
```

**實際範例**（假設域名是 `countclimbingscore.online`，IP 是 `3.26.6.19`）：

```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"
```

**重要提示**：
- 多個值用**逗號分隔**，**不要有空格**
- 必須包含：
  - ✅ 主域名（`your-domain.com`）
  - ✅ www 子域名（`www.your-domain.com`）
  - ✅ EC2 IP 地址（`3.26.6.19`）
  - ✅ 本地回環地址（`127.0.0.1`、`localhost`）

### 步驟 3: 更新 Nginx server_name

編輯 Nginx 配置文件：

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

確保 `server_name` **同時包含域名和 IP 地址**：

```nginx
server_name your-domain.com www.your-domain.com your-ec2-ip;
```

**實際範例**：

```nginx
server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
```

### 步驟 4: 重新加載配置

```bash
# 重新加載 systemd 配置
sudo systemctl daemon-reload

# 重啟 Django 服務
sudo systemctl restart climbing_system

# 測試 Nginx 配置
sudo nginx -t

# 重載 Nginx
sudo systemctl reload nginx
```

### 步驟 5: 驗證修復

測試所有訪問方式：

```bash
# 測試域名訪問
curl -I http://your-domain.com
curl -I http://www.your-domain.com

# 測試 IP 訪問（這是最重要的！）
curl -I http://your-ec2-ip

# 如果配置了 HTTPS
curl -I https://your-domain.com
curl -I https://your-ec2-ip
```

**成功標誌**：所有訪問方式都返回 `200 OK` 或 `301/302` 重定向

## 📋 完整配置範例

### Systemd 服務配置（`/etc/systemd/system/climbing_system.service`）

```ini
[Unit]
Description=Climbing Score Counting System
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/var/www/Climbing_score_counter
Environment="PATH=/var/www/Climbing_score_counter/venv/bin"
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"
Environment="CORS_ALLOWED_ORIGINS=https://countclimbingscore.online,https://www.countclimbingscore.online"
ExecStart=/var/www/Climbing_score_counter/venv/bin/gunicorn climbing_system.wsgi:application --config /var/www/Climbing_score_counter/Deployment/gunicorn_config.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx 配置（`/etc/nginx/sites-available/climbing_system.conf`）

```nginx
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;

    # ... 其他配置 ...
}
```

## 🔧 快速修復腳本

如果確定格式，可以使用以下命令快速修復：

```bash
# 備份原文件
sudo cp /etc/systemd/system/climbing_system.service /etc/systemd/system/climbing_system.service.bak

# 更新 ALLOWED_HOSTS（替換為您的實際域名和 IP）
sudo sed -i 's/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"/' /etc/systemd/system/climbing_system.service

# 重新加載並重啟
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
```

## ⚠️ 常見錯誤

### 錯誤 1: 忘記包含 IP 地址

❌ **錯誤配置**：
```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online"
```

✅ **正確配置**：
```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"
```

### 錯誤 2: 值之間有空格

❌ **錯誤配置**：
```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online, www.countclimbingscore.online, 3.26.6.19"
```

✅ **正確配置**：
```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19"
```

### 錯誤 3: 只配置了域名，忘記 IP

❌ **錯誤配置**：
```nginx
server_name countclimbingscore.online www.countclimbingscore.online;
```

✅ **正確配置**：
```nginx
server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
```

## 📝 檢查清單

部署到新域名後，確保：

- [ ] `ALLOWED_HOSTS` 包含新域名（主域名和 www）
- [ ] `ALLOWED_HOSTS` 包含原來的 IP 地址
- [ ] `ALLOWED_HOSTS` 包含 `127.0.0.1` 和 `localhost`
- [ ] Nginx `server_name` 包含新域名
- [ ] Nginx `server_name` 包含原來的 IP 地址
- [ ] 重新加載了 systemd 配置（`daemon-reload`）
- [ ] 重啟了 Django 服務
- [ ] 重載了 Nginx 配置
- [ ] 測試了域名訪問
- [ ] 測試了 IP 訪問（**重要！**）

## 🔗 相關文檔

- `Deployment/FIX_400_ERROR.md` - 400 錯誤修復指南
- `Deployment/DOMAIN_SSL_GUIDE.md` - 域名和 SSL 配置指南
- `Deployment/AWS_EC2_DEPLOYMENT.md` - 完整部署指南

## 💡 為什麼要同時支持域名和 IP？

1. **靈活性**：某些情況下可能需要直接通過 IP 訪問
2. **調試方便**：開發和調試時可以直接使用 IP
3. **備用方案**：如果 DNS 出現問題，仍可通過 IP 訪問
4. **兼容性**：確保所有訪問方式都能正常工作

## 🎯 總結

**問題根源**：Django 的 `ALLOWED_HOSTS` 和 Nginx 的 `server_name` 只配置了新域名，沒有包含原來的 IP 地址。

**解決方法**：在兩個配置中都同時添加域名和 IP 地址，然後重新加載服務。

**關鍵點**：部署到新域名時，**不要忘記保留原來的 IP 地址訪問能力**！

