# 配置管理说明

本项目的配置管理采用**服务器端配置文件**的方式，避免每次部署都需要手动修改敏感信息。

## 工作原理

1. **模板文件**（提交到 Git）：
   - `systemd/climbing_system.service` - 使用占位符
   - `nginx/climbing_system.conf` - 使用占位符
   - `env.example` - 使用占位符

2. **服务器配置文件**（不提交到 Git）：
   - `/var/www/Climbing_score_counter/.server-config` - 包含实际配置值

3. **自动配置应用**：
   - `deploy.sh` 脚本会自动读取 `.server-config`
   - 自动替换 systemd 和 nginx 配置文件中的占位符
   - 保护已存在的配置文件不被覆盖

## 首次部署

### 步骤 1: 创建服务器配置文件

```bash
# 在 EC2 服务器上执行
cd /var/www/Climbing_score_counter

# 方法 1: 使用交互式脚本（推荐）
bash setup_config.sh

# 方法 2: 手动创建
nano .server-config
```

配置文件内容示例：

```bash
# 服务器配置（不提交到 Git）
DOMAIN=your-domain.com
WWW_DOMAIN=www.your-domain.com
EC2_IP=your-ec2-ip
SECRET_KEY=your-actual-secret-key-here
```

**注意**：请将示例值替换为您的实际域名、IP 地址和密钥。

### 步骤 2: 运行部署脚本

```bash
bash deploy.sh
```

部署脚本会自动：
- 读取 `.server-config` 文件
- 复制模板文件到系统目录（如果不存在）
- 自动替换所有占位符
- 应用配置到 systemd 和 nginx

## 后续部署

后续部署时，**无需任何手动操作**：

```bash
# 只需运行部署脚本
bash deploy.sh
```

脚本会自动：
1. 拉取最新代码（git pull）
2. 重新读取 `.server-config`
3. 自动更新 systemd 和 nginx 配置
4. 完成部署

## 更新配置

如果需要更新配置（例如更换域名或 IP）：

```bash
# 编辑服务器配置文件
nano /var/www/Climbing_score_counter/.server-config

# 运行部署脚本应用新配置
bash deploy.sh
```

## 配置文件格式

`.server-config` 文件格式：

```bash
# 服务器配置（不提交到 Git）
DOMAIN=your-domain.com              # 必需：主域名
WWW_DOMAIN=www.your-domain.com      # 可选：WWW 子域名（默认：www.$DOMAIN）
EC2_IP=your-ec2-ip                  # 必需：EC2 IP 地址
SECRET_KEY=your-secret-key          # 必需：Django SECRET_KEY
```

## 安全说明

- ✅ `.server-config` 文件已在 `.gitignore` 中，不会被提交到 Git
- ✅ 文件权限自动设置为 `600`（只有所有者可读写）
- ✅ 配置文件包含敏感信息，请妥善保管
- ✅ 建议定期备份配置文件

## 故障排除

### 配置文件不存在

如果看到警告：
```
⚠️  警告: 未找到服務器配置文件 .server-config
```

解决方法：
```bash
# 运行配置初始化脚本
bash setup_config.sh
```

### 配置未应用

如果配置没有正确应用：

1. 检查配置文件格式：
```bash
cat /var/www/Climbing_score_counter/.server-config
```

2. 检查配置文件权限：
```bash
ls -la /var/www/Climbing_score_counter/.server-config
# 应该是 -rw------- (600)
```

3. 手动验证配置：
```bash
# 检查 systemd 配置
sudo grep "ALLOWED_HOSTS" /etc/systemd/system/climbing_system.service

# 检查 nginx 配置
sudo grep "server_name" /etc/nginx/sites-available/climbing_system.conf
```

### 配置文件被 Git 覆盖

如果 `git pull` 后配置丢失：

1. 确保 `.server-config` 在 `.gitignore` 中
2. 检查 Git 状态：
```bash
git status
# .server-config 不应该出现在未跟踪文件中
```

3. 如果文件被跟踪，移除：
```bash
git rm --cached .server-config
```

## 优势

✅ **一次配置，永久使用** - 首次配置后，后续部署自动应用  
✅ **安全** - 敏感信息不提交到 Git  
✅ **灵活** - 可以随时更新配置  
✅ **自动化** - 无需手动替换占位符  
✅ **保护** - 已存在的配置文件不会被覆盖  

## 相关文件

- `deploy.sh` - 部署脚本（包含自动配置逻辑）
- `setup_config.sh` - 配置初始化脚本
- `.server-config` - 服务器配置文件（不提交到 Git）
- `.gitignore` - 确保配置文件不被提交

