# 400 Bad Request 错误修复指南

当访问 `https://countclimbingscore.online/` 时收到 400 Bad Request 错误，通常是因为 Django 的 `ALLOWED_HOSTS` 配置问题。

## 🔍 问题诊断

### 快速诊断脚本

在 EC2 实例上运行：

```bash
bash Deployment/fix_400_error.sh
```

这个脚本会自动检查：
- Django ALLOWED_HOSTS 配置
- Nginx server_name 配置
- 服务运行状态
- 本地连接测试
- 错误日志

## 📋 常见原因和修复方法

### 原因 1: ALLOWED_HOSTS 未包含域名

**症状**：
- 访问 HTTPS 域名返回 400 Bad Request
- Django 日志显示 "DisallowedHost" 错误

**检查方法**：

```bash
# 检查 systemd 服务配置
sudo cat /etc/systemd/system/climbing_system.service | grep ALLOWED_HOSTS
```

**修复方法**：

1. **编辑 systemd 服务文件**：

```bash
sudo nano /etc/systemd/system/climbing_system.service
```

2. **更新 ALLOWED_HOSTS 环境变量**：

找到 `Environment="ALLOWED_HOSTS=..."` 这一行，确保包含您的域名：

```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"
```

**注意**：
- 多个域名用逗号分隔，**不要有空格**
- 必须包含主域名和 www 子域名
- 包含 EC2 IP 地址（用于直接 IP 访问）

3. **重新加载并重启服务**：

```bash
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
```

4. **验证修复**：

```bash
# 检查服务状态
sudo systemctl status climbing_system

# 测试访问
curl -I https://countclimbingscore.online
```

### 原因 2: Nginx 配置问题

**症状**：
- ALLOWED_HOSTS 配置正确
- 但仍返回 400 错误

**检查方法**：

```bash
# 检查 Nginx 配置
sudo nginx -t
sudo nginx -T | grep server_name
```

**修复方法**：

1. **编辑 Nginx 配置**：

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

2. **确保 server_name 包含域名**：

```nginx
server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
```

3. **确保 proxy_set_header Host 配置正确**：

在 `location /` 块中，确保有：

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**重要**：`proxy_set_header Host $host;` 确保 Django 收到正确的 Host 头。

4. **测试并重载 Nginx**：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 原因 3: HTTPS 配置后未更新 Django 设置

**症状**：
- 配置 SSL 后出现 400 错误
- 可能是 HTTPS 相关的安全设置导致

**检查方法**：

```bash
# 检查 systemd 服务配置中的 HTTPS 设置
sudo cat /etc/systemd/system/climbing_system.service | grep -E "(HTTPS|SSL|SECURE)"
```

**修复方法**：

如果配置了 SSL，确保 systemd 服务文件包含：

```ini
Environment="USE_HTTPS=True"
Environment="SECURE_SSL_REDIRECT=True"
Environment="SESSION_COOKIE_SECURE=True"
Environment="CSRF_COOKIE_SECURE=True"
```

但**不要**设置 `SECURE_SSL_REDIRECT=True`，因为 Nginx 已经处理了重定向。

**推荐配置**（如果使用 HTTPS）：

```ini
Environment="USE_HTTPS=True"
Environment="SESSION_COOKIE_SECURE=True"
Environment="CSRF_COOKIE_SECURE=True"
# 不设置 SECURE_SSL_REDIRECT，让 Nginx 处理重定向
```

### 原因 4: 请求头格式问题

**症状**：
- 某些浏览器可以访问，某些不行
- 可能是 Host 头格式问题

**检查方法**：

查看 Nginx 访问日志：

```bash
sudo tail -f /var/log/nginx/access.log
```

**修复方法**：

确保 Nginx 配置中有正确的请求头设置（见原因 2）。

## 🔧 完整修复步骤

### 步骤 1: 检查当前配置

```bash
# 运行诊断脚本
bash Deployment/fix_400_error.sh

# 或手动检查
sudo cat /etc/systemd/system/climbing_system.service | grep ALLOWED_HOSTS
sudo nginx -T | grep server_name
```

### 步骤 2: 更新 ALLOWED_HOSTS

```bash
# 编辑服务文件
sudo nano /etc/systemd/system/climbing_system.service
```

更新为：

```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"
```

### 步骤 3: 更新 Nginx 配置（如果需要）

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

确保 `server_name` 和 `proxy_set_header Host` 配置正确。

### 步骤 4: 重启服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 重启 Django 服务
sudo systemctl restart climbing_system

# 测试并重载 Nginx
sudo nginx -t
sudo systemctl reload nginx
```

### 步骤 5: 验证修复

```bash
# 检查服务状态
sudo systemctl status climbing_system
sudo systemctl status nginx

# 测试访问
curl -I https://countclimbingscore.online
curl -I http://countclimbingscore.online  # 应该重定向到 HTTPS

# 查看日志（如果没有错误）
sudo journalctl -u climbing_system -n 20
sudo tail -20 /var/log/nginx/error.log
```

## 📝 快速修复命令

### 如果只是 ALLOWED_HOSTS 问题

```bash
# 备份原文件
sudo cp /etc/systemd/system/climbing_system.service /etc/systemd/system/climbing_system.service.bak

# 编辑文件
sudo nano /etc/systemd/system/climbing_system.service

# 找到 Environment="ALLOWED_HOSTS=..." 这一行
# 更新为：
# Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"

# 保存后执行
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
```

### 使用 sed 快速修复（如果确定格式）

```bash
# 注意：请先备份文件！
sudo cp /etc/systemd/system/climbing_system.service /etc/systemd/system/climbing_system.service.bak

# 更新 ALLOWED_HOSTS（如果格式匹配）
sudo sed -i 's/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"/' /etc/systemd/system/climbing_system.service

# 重新加载并重启
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
```

## ⚠️ 重要提示

1. **ALLOWED_HOSTS 格式**：
   - 多个值用逗号分隔
   - **不要有空格**（除非是列表中的空格）
   - 区分大小写（通常使用小写）

2. **域名必须完全匹配**：
   - `countclimbingscore.online` 和 `www.countclimbingscore.online` 是不同的
   - 必须同时包含主域名和 www 子域名

3. **重启服务**：
   - 修改 systemd 服务文件后，必须运行 `systemctl daemon-reload`
   - 然后重启服务：`systemctl restart climbing_system`

4. **检查日志**：
   - Django 日志：`/var/www/Climbing_score_counter/logs/django.log`
   - Nginx 错误日志：`/var/log/nginx/error.log`
   - Systemd 日志：`sudo journalctl -u climbing_system -f`

## 🔗 相关文档

- [Django ALLOWED_HOSTS 文档](https://docs.djangoproject.com/en/4.2/ref/settings/#allowed-hosts)
- [Nginx proxy_set_header 文档](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header)

