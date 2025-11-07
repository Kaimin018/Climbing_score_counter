# 使用 Let's Encrypt 時配置 IP 訪問指南

當您使用 Let's Encrypt SSL 證書時，**無法為 IP 地址頒發證書**（Let's Encrypt 只支持域名）。因此，需要為 IP 訪問提供特殊的配置。

## 🔍 問題說明

### Let's Encrypt 的限制

- ✅ **支持**：域名（如 `countclimbingscore.online`）
- ❌ **不支持**：IP 地址（如 `3.26.6.19`）

### 常見問題

當配置了 HTTPS 重定向後：
- 域名訪問：`http://domain.com` → 重定向到 `https://domain.com` ✅
- IP 訪問：`http://3.26.6.19` → 找不到匹配的 server 塊 → 404 ❌

## ✅ 解決方案

有兩種方案可以選擇：

### 方案 1：IP 使用 HTTP，域名使用 HTTPS（推薦）

**優點**：
- IP 可以直接訪問（HTTP）
- 域名使用 HTTPS（安全）
- 配置簡單

**缺點**：
- IP 訪問使用 HTTP（不安全，但可以接受）

**配置方法**：

編輯 Nginx 配置：

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

配置如下：

```nginx
# HTTP 重定向到 HTTPS（只針對域名）
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online;
    return 301 https://$server_name$request_uri;
}

# HTTP 直接訪問（針對 IP，不重定向）
server {
    listen 80;
    server_name 3.26.6.19;
    
    # 日誌設置
    access_log /var/log/nginx/climbing_system_access.log;
    error_log /var/log/nginx/climbing_system_error.log;
    
    # 客戶端最大請求體大小
    client_max_body_size 20M;
    
    # 靜態文件服務
    location /static/ {
        alias /var/www/Climbing_score_counter/staticfiles/;
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }
    
    # 媒體文件服務
    location /media/ {
        alias /var/www/Climbing_score_counter/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # 代理所有其他請求到 Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 安全標頭
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}

# HTTPS 配置（只針對域名）
server {
    listen 443 ssl http2;
    server_name countclimbingscore.online www.countclimbingscore.online;
    
    ssl_certificate /etc/letsencrypt/live/countclimbingscore.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/countclimbingscore.online/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # 日誌設置
    access_log /var/log/nginx/climbing_system_access.log;
    error_log /var/log/nginx/climbing_system_error.log;
    
    # 客戶端最大請求體大小
    client_max_body_size 20M;
    
    # 靜態文件服務
    location /static/ {
        alias /var/www/Climbing_score_counter/staticfiles/;
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }
    
    # 媒體文件服務
    location /media/ {
        alias /var/www/Climbing_score_counter/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # 代理所有其他請求到 Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 安全標頭
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### 方案 2：IP 訪問重定向到域名

**優點**：
- 所有訪問都使用 HTTPS（安全）
- 統一使用域名訪問

**缺點**：
- IP 訪問會重定向到域名（用戶需要知道域名）

**配置方法**：

```nginx
# HTTP 重定向到 HTTPS（包含 IP，重定向到域名）
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    return 301 https://countclimbingscore.online$request_uri;
}

# HTTPS 配置（只針對域名）
server {
    listen 443 ssl http2;
    server_name countclimbingscore.online www.countclimbingscore.online;
    
    ssl_certificate /etc/letsencrypt/live/countclimbingscore.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/countclimbingscore.online/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # ... 其他配置與方案 1 相同 ...
}
```

## 🔧 完整修復步驟

### 步驟 1: 檢查當前配置

```bash
# 查看當前的 Nginx 配置
sudo nginx -T | grep -A 30 "server {"
```

### 步驟 2: 備份當前配置

```bash
sudo cp /etc/nginx/sites-available/climbing_system.conf /etc/nginx/sites-available/climbing_system.conf.bak
```

### 步驟 3: 編輯 Nginx 配置

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

根據您選擇的方案，更新配置（推薦使用方案 1）。

### 步驟 4: 測試配置

```bash
# 測試 Nginx 配置語法
sudo nginx -t
```

如果測試通過，會顯示：
```
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 步驟 5: 重載 Nginx

```bash
sudo systemctl reload nginx
```

### 步驟 6: 驗證修復

**測試域名訪問（應該重定向到 HTTPS）**：

```bash
curl -I http://countclimbingscore.online
# 應該返回 301 重定向到 https://
```

**測試 IP 訪問（方案 1：HTTP，方案 2：重定向）**：

```bash
# 方案 1：應該返回 200 OK
curl -I http://3.26.6.19/

# 方案 2：應該返回 301 重定向到域名
curl -I http://3.26.6.19/
```

## 📝 配置檢查清單

修復後，確保：

- [ ] Nginx 配置語法正確（`nginx -t` 通過）
- [ ] 已重載 Nginx 配置
- [ ] 域名 HTTP 訪問重定向到 HTTPS ✅
- [ ] 域名 HTTPS 訪問正常 ✅
- [ ] IP HTTP 訪問正常（方案 1）或重定向到域名（方案 2）✅
- [ ] Django ALLOWED_HOSTS 包含 IP 地址 ✅

## ⚠️ 重要注意事項

### 1. 不要將 IP 添加到 HTTPS server 塊

❌ **錯誤配置**：
```nginx
server {
    listen 443 ssl http2;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    # ...
}
```

**問題**：如果用戶訪問 `https://3.26.6.19`，會出現 SSL 證書錯誤（因為證書是為域名頒發的，不是 IP）。

✅ **正確配置**：
```nginx
# HTTPS 只針對域名
server {
    listen 443 ssl http2;
    server_name countclimbingscore.online www.countclimbingscore.online;
    # ...
}
```

### 2. 確保 ALLOWED_HOSTS 包含 IP

即使 IP 使用 HTTP，Django 的 `ALLOWED_HOSTS` 也必須包含 IP 地址：

```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"
```

### 3. Certbot 可能會修改配置

如果使用 `certbot --nginx`，它可能會自動修改 Nginx 配置。修改後，需要手動添加 IP 的 HTTP server 塊。

## 🔍 故障排除

### 問題 1: IP 訪問仍然返回 404

**檢查**：
```bash
# 檢查 server_name 配置
sudo nginx -T | grep server_name

# 檢查是否有默認 server 塊
sudo nginx -T | grep -A 10 "listen.*80.*default"
```

**解決**：確保 IP 的 server 塊在配置文件中，並且 `server_name` 正確。

### 問題 2: IP 訪問返回 SSL 錯誤

**原因**：用戶訪問了 `https://3.26.6.19`，但證書是為域名頒發的。

**解決**：確保 HTTPS server 塊的 `server_name` **不包含** IP 地址。

### 問題 3: Certbot 更新後配置被覆蓋

**解決**：Certbot 更新配置後，需要手動重新添加 IP 的 HTTP server 塊。

## 💡 推薦方案

**推薦使用方案 1**（IP 使用 HTTP，域名使用 HTTPS）：

1. ✅ 配置簡單
2. ✅ IP 可以直接訪問
3. ✅ 域名使用 HTTPS（安全）
4. ✅ 不需要用戶知道域名

## 🔗 相關文檔

- `Deployment/FIX_404_IP_ACCESS.md` - IP 訪問 404 錯誤修復指南
- `Deployment/DOMAIN_SSL_GUIDE.md` - 域名和 SSL 配置指南
- `Deployment/FIX_IP_ACCESS.md` - IP 訪問修復指南

## 🎯 總結

**關鍵點**：
1. Let's Encrypt **不支持**為 IP 地址頒發證書
2. 為 IP 訪問提供**單獨的 HTTP server 塊**（不使用 HTTPS）
3. HTTPS server 塊的 `server_name` **不要包含** IP 地址
4. 確保 Django `ALLOWED_HOSTS` 包含 IP 地址

**推薦配置**：
- 域名：HTTP → 重定向到 HTTPS
- IP：直接使用 HTTP（不重定向）

