# 域名配置指南

本指南说明如何为域名配置 DNS 和 SSL 证书。

## 域名信息（本项目实际配置）

- **域名**: `countclimbingscore.online`
- **EC2 IP 地址**: `3.26.6.19`
- **区域**: ap-southeast-2 (悉尼)

**注意**：如果您使用不同的域名和 IP，请将本指南中的所有 `countclimbingscore.online` 和 `3.26.6.19` 替换为您的实际值。

## 步骤 1: 配置 DNS 记录

在您的域名注册商（例如 Namecheap、GoDaddy 等）的 DNS 管理界面中，添加以下 A 记录：

### 必需的 DNS 记录

1. **主域名 A 记录**:
   - 类型: `A`
   - 主机记录/名称: `@` 或 `countclimbingscore.online`
   - 值/指向: `3.26.6.19`
   - TTL: `600` 或 `自动`

2. **www 子域名 A 记录**:
   - 类型: `A`
   - 主机记录/名称: `www`
   - 值/指向: `3.26.6.19`
   - TTL: `600` 或 `自动`

### DNS 配置示例

```
类型    主机记录    值            TTL
A       @          3.26.6.19     600
A       www        3.26.6.19     600
```

## 步骤 2: 等待 DNS 生效

DNS 记录通常需要几分钟到几小时才能生效。您可以使用以下命令检查：

```bash
# 检查主域名
nslookup countclimbingscore.online

# 检查 www 子域名
nslookup www.countclimbingscore.online

# 或使用 dig 命令
dig countclimbingscore.online
dig www.countclimbingscore.online
```

当 DNS 生效后，这些命令应该返回 `3.26.6.19`。

## 步骤 3: 更新 EC2 上的配置

### 3.1 更新 Nginx 配置

在 EC2 服务器上：

```bash
# 编辑 Nginx 配置
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

确保 `server_name` 包含域名：

```nginx
server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
```

然后测试并重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 3.2 更新 Systemd 服务配置

```bash
# 编辑服务文件
sudo nano /etc/systemd/system/climbing_system.service
```

更新 `ALLOWED_HOSTS` 环境变量：

```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"
Environment="CORS_ALLOWED_ORIGINS=https://countclimbingscore.online,https://www.countclimbingscore.online"
```

然后重新加载并重启服务：

```bash
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
```

## 步骤 4: 测试域名访问

DNS 生效后，测试域名访问：

```bash
# 在本地电脑测试
curl -I http://countclimbingscore.online
curl -I http://www.countclimbingscore.online

# 或在浏览器中访问
# http://countclimbingscore.online
# http://www.countclimbingscore.online
```

## 步骤 5: 配置 SSL 证书（HTTPS）

### 5.1 安装 Certbot

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

### 5.2 获取 SSL 证书

```bash
# 获取证书（Certbot 会自动配置 Nginx）
sudo certbot --nginx -d countclimbingscore.online -d www.countclimbingscore.online
```

Certbot 会：
- 自动验证域名所有权
- 获取 SSL 证书
- 配置 Nginx 使用 HTTPS
- 设置 HTTP 到 HTTPS 的重定向

### 5.3 测试自动续期

```bash
# 测试证书自动续期
sudo certbot renew --dry-run
```

### 5.4 配置自动续期（已自动配置）

Certbot 会自动创建 cron 任务，证书会在到期前自动续期。

## 步骤 6: 更新 Django 设置（如果使用 HTTPS）

配置 SSL 后，更新 systemd 服务文件：

```bash
sudo nano /etc/systemd/system/climbing_system.service
```

添加或更新：

```ini
Environment="SECURE_SSL_REDIRECT=True"
Environment="SESSION_COOKIE_SECURE=True"
Environment="CSRF_COOKIE_SECURE=True"
```

然后重启服务：

```bash
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
```

## 验证清单

- [ ] DNS A 记录已配置（@ 和 www）
- [ ] DNS 已生效（nslookup 返回正确 IP）
- [ ] Nginx 配置已更新
- [ ] Systemd 服务配置已更新
- [ ] 可以通过域名访问（HTTP）
- [ ] SSL 证书已配置（HTTPS）
- [ ] HTTP 自动重定向到 HTTPS
- [ ] 证书自动续期已配置

## 故障排除

### DNS 未生效

- 等待更长时间（最多 48 小时）
- 检查 DNS 记录是否正确
- 清除本地 DNS 缓存

### SSL 证书获取失败

- 确认 DNS 已生效
- 确认 80 端口已开放（Let's Encrypt 需要）
  - 检查 AWS 安全组（Security Group）
  - 检查网络 ACL (Network ACL)
  - 检查操作系统防火墙（UFW/iptables）
  - 运行检查脚本：`bash Deployment/check_firewall.sh`
- 检查 Nginx 配置是否正确
- 查看 Certbot 日志：`sudo certbot certificates`
- 详细故障排除：参考 `Deployment/FIREWALL_TROUBLESHOOTING.md`

### 域名无法访问

- 检查 DNS 记录
- 检查 AWS 安全组（确保 80 和 443 端口开放）
- 检查网络 ACL (Network ACL) - 如果使用自定义 NACL
- 检查操作系统防火墙（UFW/iptables）
  - 运行检查脚本：`bash Deployment/check_firewall.sh`
- 检查 Nginx 配置
- 查看 Nginx 日志：`sudo tail -f /var/log/nginx/error.log`
- 详细故障排除：参考 `Deployment/FIREWALL_TROUBLESHOOTING.md`

## 常用命令

```bash
# 检查 DNS
nslookup countclimbingscore.online
dig countclimbingscore.online

# 检查 SSL 证书
sudo certbot certificates

# 手动续期证书
sudo certbot renew

# 查看 Nginx 配置
sudo nginx -t
sudo nginx -T | grep server_name

# 测试域名访问
curl -I http://countclimbingscore.online
curl -I https://countclimbingscore.online
```

