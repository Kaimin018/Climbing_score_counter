# IP 地址访问修复指南

当使用 IP 地址 `3.26.6.19` 无法访问时，请按照以下步骤诊断和修复。

## 🔍 快速诊断

在 EC2 服务器上运行诊断脚本：

```bash
cd /var/www/Climbing_score_counter
bash Deployment/check_ip_access.sh
```

这个脚本会自动检查：
- Django ALLOWED_HOSTS 是否包含 IP
- Nginx server_name 是否包含 IP
- 服务运行状态
- 本地连接测试
- 错误日志

## 📋 常见问题和修复方法

### 问题 1: ALLOWED_HOSTS 未包含 IP 地址

**症状**：
- 通过 IP 访问返回 400 Bad Request
- Django 日志显示 "DisallowedHost" 错误

**检查方法**：

```bash
sudo cat /etc/systemd/system/climbing_system.service | grep ALLOWED_HOSTS
```

**修复方法**：

1. **编辑 systemd 服务文件**：

```bash
sudo nano /etc/systemd/system/climbing_system.service
```

2. **找到 `Environment="ALLOWED_HOSTS=..."` 这一行**

3. **确保包含 IP 地址**：

```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"
```

**重要**：
- 多个值用逗号分隔，**不要有空格**
- 必须包含：
  - ✅ 主域名
  - ✅ www 子域名
  - ✅ **IP 地址（3.26.6.19）**
  - ✅ 127.0.0.1 和 localhost

4. **重新加载并重启服务**：

```bash
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
```

### 问题 2: Nginx server_name 未包含 IP 地址

**症状**：
- ALLOWED_HOSTS 配置正确
- 但通过 IP 访问仍然失败

**检查方法**：

```bash
sudo nginx -T | grep server_name
```

**修复方法**：

1. **编辑 Nginx 配置文件**：

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

2. **找到 `server_name` 这一行**

3. **确保包含 IP 地址**：

```nginx
server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;
```

4. **测试并重载 Nginx**：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 问题 3: 服务未重启

**症状**：
- 配置已更新
- 但更改未生效

**修复方法**：

```bash
# 重新加载 systemd 配置（修改服务文件后必须执行）
sudo systemctl daemon-reload

# 重启 Django 服务
sudo systemctl restart climbing_system

# 重载 Nginx
sudo systemctl reload nginx

# 检查服务状态
sudo systemctl status climbing_system
sudo systemctl status nginx
```

### 问题 4: AWS 安全组未开放端口

**症状**：
- 服务器本地测试正常
- 但从外部无法访问

**检查方法**：
1. 登录 AWS Console
2. 进入 **EC2 → Security Groups**
3. 选择您的 EC2 实例使用的安全组
4. 检查 **Inbound rules**

**应该有的规则**：

| 类型 | 协议 | 端口范围 | 来源 |
|------|------|----------|------|
| HTTP | TCP | 80 | 0.0.0.0/0 |
| HTTPS | TCP | 443 | 0.0.0.0/0 |

**修复方法**：
1. 点击 **Edit inbound rules**
2. 点击 **Add rule**
3. 添加 HTTP (端口 80) 和 HTTPS (端口 443)
4. 来源设置为 `0.0.0.0/0`
5. 点击 **Save rules**

## 🔧 完整修复步骤

### 步骤 1: 运行诊断脚本

```bash
cd /var/www/Climbing_score_counter
bash Deployment/check_ip_access.sh
```

### 步骤 2: 更新 ALLOWED_HOSTS

```bash
# 编辑服务文件
sudo nano /etc/systemd/system/climbing_system.service

# 找到这一行并更新（确保包含 IP）：
# Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"

# 保存后执行
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
```

### 步骤 3: 更新 Nginx 配置

```bash
# 编辑 Nginx 配置
sudo nano /etc/nginx/sites-available/climbing_system.conf

# 找到 server_name 并更新（确保包含 IP）：
# server_name countclimbingscore.online www.countclimbingscore.online 3.26.6.19;

# 测试并重载
sudo nginx -t
sudo systemctl reload nginx
```

### 步骤 4: 验证修复

在服务器上测试：

```bash
# 测试 1: 使用 IP 作为 Host 头
curl -I -H "Host: 3.26.6.19" http://127.0.0.1/

# 测试 2: 直接访问 Gunicorn
curl -I http://127.0.0.1:8000/
```

从外部测试（在您的本地电脑上）：

```bash
# 测试 HTTP
curl -I http://3.26.6.19/

# 测试 HTTPS（如果配置了 SSL）
curl -I https://3.26.6.19/
```

**成功标志**：返回 `200 OK` 或 `301/302` 重定向

## 📝 配置检查清单

确保以下配置正确：

- [ ] `ALLOWED_HOSTS` 包含 `3.26.6.19`
- [ ] `ALLOWED_HOSTS` 包含域名（主域名和 www）
- [ ] `ALLOWED_HOSTS` 包含 `127.0.0.1` 和 `localhost`
- [ ] Nginx `server_name` 包含 `3.26.6.19`
- [ ] Nginx `server_name` 包含域名
- [ ] 已执行 `systemctl daemon-reload`
- [ ] 已重启 `climbing_system` 服务
- [ ] 已重载 Nginx 配置
- [ ] AWS 安全组开放了端口 80 和 443
- [ ] 服务状态正常（`systemctl status`）

## 🚀 快速修复命令

如果确定配置格式，可以使用以下命令快速修复：

```bash
# 备份原文件
sudo cp /etc/systemd/system/climbing_system.service /etc/systemd/system/climbing_system.service.bak

# 更新 ALLOWED_HOSTS（确保包含 IP）
sudo sed -i 's/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"/' /etc/systemd/system/climbing_system.service

# 重新加载并重启
sudo systemctl daemon-reload
sudo systemctl restart climbing_system

# 检查 Nginx server_name（手动编辑如果需要）
sudo nano /etc/nginx/sites-available/climbing_system.conf
# 确保 server_name 包含 3.26.6.19

# 重载 Nginx
sudo nginx -t && sudo systemctl reload nginx
```

## ⚠️ 常见错误

### 错误 1: 忘记包含 IP 地址

❌ **错误配置**：
```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online"
```

✅ **正确配置**：
```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19,127.0.0.1,localhost"
```

### 错误 2: 值之间有空格

❌ **错误配置**：
```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online, www.countclimbingscore.online, 3.26.6.19"
```

✅ **正确配置**：
```ini
Environment="ALLOWED_HOSTS=countclimbingscore.online,www.countclimbingscore.online,3.26.6.19"
```

### 错误 3: 修改后未重启服务

❌ **错误操作**：
```bash
# 只修改了文件，但忘记重启
sudo nano /etc/systemd/system/climbing_system.service
# 忘记执行 daemon-reload 和 restart
```

✅ **正确操作**：
```bash
sudo nano /etc/systemd/system/climbing_system.service
sudo systemctl daemon-reload  # 必须执行
sudo systemctl restart climbing_system  # 必须执行
```

## 🔗 相关文档

- `Deployment/check_ip_access.sh` - IP 访问诊断脚本
- `Deployment/FIX_400_ERROR.md` - 400 错误修复指南
- `Deployment/WHY_IP_NOT_WORKING_AFTER_DOMAIN.md` - IP 访问问题原因说明
- `Deployment/FIREWALL_TROUBLESHOOTING.md` - 防火墙故障排除

## 💡 为什么需要同时支持域名和 IP？

1. **灵活性**：某些情况下可能需要直接通过 IP 访问
2. **调试方便**：开发和调试时可以直接使用 IP
3. **备用方案**：如果 DNS 出现问题，仍可通过 IP 访问
4. **兼容性**：确保所有访问方式都能正常工作

## 🎯 总结

**问题根源**：`ALLOWED_HOSTS` 和 Nginx `server_name` 只配置了域名，没有包含 IP 地址。

**解决方法**：
1. 在 `ALLOWED_HOSTS` 中添加 IP 地址
2. 在 Nginx `server_name` 中添加 IP 地址
3. 重新加载并重启服务

**关键点**：修改配置后，**必须**执行 `systemctl daemon-reload` 和 `systemctl restart climbing_system`！

