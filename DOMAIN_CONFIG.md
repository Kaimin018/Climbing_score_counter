# 域名配置说明

本项目已配置为使用域名 `countclimbingscore.online` 和 IP 地址 `3.26.6.19`。

## 配置文件中的实际值

以下配置文件包含实际的域名和 IP 地址，用于快速部署：

- `DOMAIN_SETUP.md`: 包含完整的域名配置指南和实际值
- `AWS_EC2_DEPLOYMENT.md`: 部署文档中包含实际值作为示例

## 模板文件（使用占位符）

以下文件使用占位符，部署时需要替换为实际值：

- `systemd/climbing_system.service`: 使用 `your-domain.com` 和 `your-ec2-ip` 占位符
- `nginx/climbing_system.conf`: 使用 `your-domain.com` 和 `your-ec2-ip` 占位符
- `env.example`: 使用 `your-domain.com` 和 `your-ec2-ip` 占位符

## 部署时替换

在 EC2 服务器上部署时，需要将以下占位符替换为实际值：

- `your-domain.com` → `countclimbingscore.online`
- `www.your-domain.com` → `www.countclimbingscore.online`
- `your-ec2-ip` → `3.26.6.19`

## 快速配置脚本

可以使用以下命令快速替换配置：

```bash
# 在 EC2 服务器上执行
cd /var/www/Climbing_score_counter

# 替换 systemd 服务文件
sudo sed -i 's/your-domain.com/countclimbingscore.online/g' /etc/systemd/system/climbing_system.service
sudo sed -i 's/www.your-domain.com/www.countclimbingscore.online/g' /etc/systemd/system/climbing_system.service
sudo sed -i 's/your-ec2-ip/3.26.6.19/g' /etc/systemd/system/climbing_system.service

# 替换 Nginx 配置
sudo sed -i 's/your-domain.com/countclimbingscore.online/g' /etc/nginx/sites-available/climbing_system.conf
sudo sed -i 's/www.your-domain.com/www.countclimbingscore.online/g' /etc/nginx/sites-available/climbing_system.conf
sudo sed -i 's/your-ec2-ip/3.26.6.19/g' /etc/nginx/sites-available/climbing_system.conf

# 重新加载配置
sudo systemctl daemon-reload
sudo systemctl restart climbing_system
sudo nginx -t && sudo systemctl reload nginx
```

## 安全说明

- ✅ 所有敏感信息（SECRET_KEY、密码等）都使用占位符或环境变量
- ✅ `.env` 文件已在 `.gitignore` 中，不会被提交
- ✅ GitHub Actions 使用 `secrets` 管理敏感信息
- ⚠️ 域名和 IP 地址是公开信息，但为了通用性，模板文件使用占位符

