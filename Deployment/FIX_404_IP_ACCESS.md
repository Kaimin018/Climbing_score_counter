# IP 访问返回 404 修复指南

当使用 IP 地址访问时返回 404 Not Found，但域名访问正常时，通常是 Nginx 配置问题。

## 🔍 问题诊断

### 快速诊断

在 EC2 服务器上运行详细诊断脚本：

```bash
cd /var/www/Climbing_score_counter
bash Deployment/check_nginx_config.sh
```

这个脚本会检查：
- 所有启用的 Nginx 配置
- 所有 server 块
- 默认 server 块
- HTTPS 重定向配置
- 访问日志和错误日志

## 📋 常见原因和修复方法

### 原因 1: 有多个 server 块，IP 访问匹配到了错误的 server 块

**症状**：
- 域名访问正常（返回 301 或 200）
- IP 访问返回 404
- 可能有 HTTPS 重定向配置

**检查方法**：

```bash
# 查看所有启用的配置
ls -la /etc/nginx/sites-enabled/

# 查看所有 server 块
sudo nginx -T | grep -A 20 "server {"
```

**修复方法**：

1. **检查是否有多个 server 块监听端口 80**

如果有多个 server 块，Nginx 会按照以下顺序匹配：
1. 精确匹配 `server_name`
2. 以 `*` 开头的通配符匹配
3. 以 `*` 结尾的通配符匹配
4. 正则表达式匹配
5. **默认 server 块**（第一个或标记为 `default_server` 的）

2. **确保主 server 块的 server_name 包含 IP**

编辑主配置文件：

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

确保主 server 块包含 IP：

```nginx
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    
    # ... 其他配置 ...
}
```

### 原因 2: HTTPS 重定向配置只针对域名

**症状**：
- 域名访问正常（可能重定向到 HTTPS）
- IP 访问返回 404
- 有 HTTPS 重定向配置

**检查方法**：

```bash
# 检查是否有 HTTPS 重定向
sudo nginx -T | grep -i "return 301\|return 302\|rewrite.*https"
```

**修复方法**：

如果配置了 HTTPS 重定向，通常会有两个 server 块：

```nginx
# HTTP 重定向到 HTTPS（只针对域名）
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online;
    return 301 https://$server_name$request_uri;
}

# HTTPS 配置
server {
    listen 443 ssl http2;
    server_name countclimbingscore.online www.countclimbingscore.online;
    # ... SSL 配置 ...
}
```

**问题**：上面的配置只处理域名，IP 访问会匹配到默认 server 块（可能不存在或返回 404）。

**解决方案 1：在重定向 server 块中也包含 IP**

```nginx
# HTTP 重定向到 HTTPS（包含 IP）
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    return 301 https://countclimbingscore.online$request_uri;
}

# HTTPS 配置（也包含 IP）
server {
    listen 443 ssl http2;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    # ... SSL 配置 ...
}
```

**解决方案 2：为 IP 访问单独配置 HTTP server 块**

```nginx
# HTTP 重定向到 HTTPS（只针对域名）
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online;
    return 301 https://$server_name$request_uri;
}

# HTTP 直接访问（针对 IP，不重定向）
server {
    listen 80;
    server_name 3.26.6.19;
    
    # 直接代理到 Gunicorn，不重定向
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 静态文件和媒体文件配置...
}

# HTTPS 配置（只针对域名）
server {
    listen 443 ssl http2;
    server_name countclimbingscore.online www.countclimbingscore.online;
    # ... SSL 配置 ...
}
```

### 原因 3: 默认 server 块配置不正确

**症状**：
- 没有明确匹配的 server 块
- 使用了默认 server 块
- 默认 server 块可能配置不正确

**检查方法**：

```bash
# 检查默认 server 块
sudo nginx -T | grep -A 20 "listen.*default_server"
```

**修复方法**：

确保主 server 块是默认的，或者明确设置：

```nginx
server {
    listen 80 default_server;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    
    # ... 其他配置 ...
}
```

## 🔧 完整修复步骤

### 步骤 1: 运行详细诊断

```bash
cd /var/www/Climbing_score_counter
bash Deployment/check_nginx_config.sh
```

### 步骤 2: 检查当前配置

```bash
# 查看所有启用的配置
ls -la /etc/nginx/sites-enabled/

# 查看完整的 Nginx 配置
sudo nginx -T | grep -A 50 "server {"
```

### 步骤 3: 编辑 Nginx 配置

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

### 步骤 4: 根据情况修复

**情况 A：只有 HTTP，没有 HTTPS**

确保 server_name 包含 IP：

```nginx
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    
    # ... 其他配置 ...
}
```

**情况 B：有 HTTPS 重定向**

选择以下方案之一：

**方案 1：IP 也重定向到 HTTPS（推荐）**

```nginx
# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    return 301 https://countclimbingscore.online$request_uri;
}

# HTTPS 配置
server {
    listen 443 ssl http2;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    
    ssl_certificate /etc/letsencrypt/live/countclimbingscore.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/countclimbingscore.online/privkey.pem;
    
    # ... 其他配置 ...
}
```

**方案 2：IP 使用 HTTP，域名使用 HTTPS**

```nginx
# HTTP 重定向到 HTTPS（只针对域名）
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online;
    return 301 https://$server_name$request_uri;
}

# HTTP 直接访问（针对 IP）
server {
    listen 80;
    server_name 3.26.6.19;
    
    # ... 代理配置 ...
}

# HTTPS 配置（只针对域名）
server {
    listen 443 ssl http2;
    server_name countclimbingscore.online www.countclimbingscore.online;
    
    # ... SSL 和代理配置 ...
}
```

### 步骤 5: 测试并重载

```bash
# 测试配置语法
sudo nginx -t

# 如果测试通过，重载配置
sudo systemctl reload nginx
```

### 步骤 6: 验证修复

```bash
# 测试 IP 访问
curl -I -H "Host: 3.26.6.19" http://127.0.0.1/
curl -I http://3.26.6.19/

# 测试域名访问
curl -I http://countclimbingscore.online/
curl -I https://countclimbingscore.online/
```

## 📝 配置检查清单

修复后，确保：

- [ ] 主 server 块的 `server_name` 包含 IP 地址
- [ ] 如果有 HTTPS 重定向，也处理 IP 访问
- [ ] 没有多个冲突的 server 块
- [ ] 默认 server 块配置正确
- [ ] Nginx 配置语法正确（`nginx -t`）
- [ ] 已重载 Nginx 配置
- [ ] IP 访问测试通过

## ⚠️ 常见错误

### 错误 1: HTTPS 重定向只针对域名

❌ **错误配置**：
```nginx
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online;
    return 301 https://$server_name$request_uri;
}
```

✅ **正确配置**：
```nginx
server {
    listen 80;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    return 301 https://countclimbingscore.online$request_uri;
}
```

### 错误 2: 多个 server 块冲突

❌ **错误配置**：
```nginx
# Server 块 1：只处理域名
server {
    listen 80;
    server_name countclimbingscore.online;
    # ...
}

# Server 块 2：默认（但没有配置）
server {
    listen 80 default_server;
    # 没有 server_name，可能返回 404
}
```

✅ **正确配置**：
```nginx
# 主 server 块：处理所有访问
server {
    listen 80 default_server;
    server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
    # ...
}
```

## 🔗 相关文档

- `Deployment/check_nginx_config.sh` - Nginx 配置详细检查脚本
- `Deployment/FIX_IP_ACCESS.md` - IP 访问修复指南
- `Deployment/FIX_400_ERROR.md` - 400 错误修复指南

## 💡 为什么会出现 404？

Nginx 使用 `server_name` 来匹配请求的 `Host` 头。如果：
1. 请求的 `Host` 头是 IP 地址
2. 但没有 server 块的 `server_name` 包含这个 IP
3. Nginx 会使用默认 server 块
4. 如果默认 server 块配置不正确或不存在，就会返回 404

**解决方法**：确保至少有一个 server 块的 `server_name` 包含 IP 地址。

## 🎯 总结

**问题根源**：Nginx 配置中，没有 server 块的 `server_name` 匹配 IP 地址的请求。

**解决方法**：
1. 在主 server 块的 `server_name` 中添加 IP 地址
2. 如果有 HTTPS 重定向，确保也处理 IP 访问
3. 确保没有多个冲突的 server 块

**关键点**：修改配置后，**必须**执行 `nginx -t` 测试语法，然后 `systemctl reload nginx` 重载配置！

