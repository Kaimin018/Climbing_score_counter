# Deployment 目录索引

> **快速导航：根据你的需求，找到对应的文档和脚本**

## 📚 使用场景导航

### 🚀 首次部署（新项目）

**按顺序阅读：**

1. **[QUICK_START.md](QUICK_START.md)** - 快速部署步骤（5分钟上手）
2. **[docs/guides/AWS_EC2_DEPLOYMENT.md](docs/guides/AWS_EC2_DEPLOYMENT.md)** - 完整部署指南（详细步骤）
3. **[docs/setup/SSH_SETUP.md](docs/setup/SSH_SETUP.md)** - SSH 连接配置（如果还没配置）
4. **[scripts/tools/setup_ec2.sh](scripts/tools/setup_ec2.sh)** - 运行初始设置脚本

### 🔄 日常更新部署

**使用这些：**

- **[scripts/tools/deploy.sh](scripts/tools/deploy.sh)** - 自动部署脚本（推荐）
- **[QUICK_DEBUG.md](QUICK_DEBUG.md)** - 快速调试命令参考

### 🌐 配置域名和 SSL

**按顺序阅读：**

1. **[docs/setup/DOMAIN_SETUP.md](docs/setup/DOMAIN_SETUP.md)** - 域名配置指南
2. **[docs/setup/DOMAIN_SSL_GUIDE.md](docs/setup/DOMAIN_SSL_GUIDE.md)** - SSL 证书配置
3. **[docs/setup/IP_ACCESS_WITH_LETSENCRYPT.md](docs/setup/IP_ACCESS_WITH_LETSENCRYPT.md)** - 域名配置后的 IP 访问问题

### 🔧 配置管理

- **[docs/setup/CONFIG_MANAGEMENT.md](docs/setup/CONFIG_MANAGEMENT.md)** - 服务器配置管理策略
- **[docs/setup/SSH_CONFIG_CHECKLIST.md](docs/setup/SSH_CONFIG_CHECKLIST.md)** - SSH 配置检查清单

### 🗄️ 数据库相关

- **[docs/setup/DATABASE_SETUP.md](docs/setup/DATABASE_SETUP.md)** - 数据库设置（SQLite/MySQL）
- **[docs/setup/DATABASE_SYNC.md](docs/setup/DATABASE_SYNC.md)** - 本地与服务器数据库同步
- **[scripts/tools/sync_database_from_server.sh](scripts/tools/sync_database_from_server.sh)** - 从服务器下载数据库
- **[scripts/tools/sync_database_to_server.sh](scripts/tools/sync_database_to_server.sh)** - 上传数据库到服务器
- **[scripts/tools/sync_db_from_server.bat](scripts/tools/sync_db_from_server.bat)** - Windows 批处理版本

### 🐛 遇到问题？

**根据问题类型查找：**

#### 部署相关问题
- **[docs/troubleshooting/TROUBLESHOOTING_DEPLOYMENT.md](docs/troubleshooting/TROUBLESHOOTING_DEPLOYMENT.md)** - 通用故障排除指南
- **[docs/troubleshooting/FIX_400_ERROR.md](docs/troubleshooting/FIX_400_ERROR.md)** - 400 错误修复
- **[docs/troubleshooting/FIX_404_IP_ACCESS.md](docs/troubleshooting/FIX_404_IP_ACCESS.md)** - 404 错误和 IP 访问问题
- **[docs/troubleshooting/FIX_IP_ACCESS.md](docs/troubleshooting/FIX_IP_ACCESS.md)** - IP 访问问题
- **[docs/troubleshooting/WHY_IP_NOT_WORKING_AFTER_DOMAIN.md](docs/troubleshooting/WHY_IP_NOT_WORKING_AFTER_DOMAIN.md)** - 配置域名后 IP 无法访问的原因

#### 网络和防火墙问题
- **[docs/troubleshooting/FIREWALL_TROUBLESHOOTING.md](docs/troubleshooting/FIREWALL_TROUBLESHOOTING.md)** - 防火墙故障排除
- **[scripts/checks/check_firewall.sh](scripts/checks/check_firewall.sh)** - 检查防火墙配置
- **[scripts/checks/check_ip_access.sh](scripts/checks/check_ip_access.sh)** - 检查 IP 访问

#### Nginx 问题
- **[docs/troubleshooting/FIX_NGINX_SYNTAX_ERROR.md](docs/troubleshooting/FIX_NGINX_SYNTAX_ERROR.md)** - Nginx 语法错误修复
- **[scripts/checks/check_nginx_config.sh](scripts/checks/check_nginx_config.sh)** - 检查 Nginx 配置
- **[scripts/tools/fix_nginx_syntax.sh](scripts/tools/fix_nginx_syntax.sh)** - 修复 Nginx 语法

#### Git 和权限问题
- **[docs/troubleshooting/FIX_GIT_OWNERSHIP.md](docs/troubleshooting/FIX_GIT_OWNERSHIP.md)** - Git 所有权和权限问题修复
- **[docs/troubleshooting/FIX_GIT_CONFLICT.md](docs/troubleshooting/FIX_GIT_CONFLICT.md)** - Git 冲突修复（文件结构重构后，包含手动处理步骤）
- **[scripts/tools/fix_permissions.sh](scripts/tools/fix_permissions.sh)** - 一键修复所有权限问题（推荐）
- **[scripts/tools/fix_git_conflict.sh](scripts/tools/fix_git_conflict.sh)** - 修复 Git 冲突脚本（需要先推送代码）

#### 服务连接问题
- **[docs/troubleshooting/FIX_502_BAD_GATEWAY.md](docs/troubleshooting/FIX_502_BAD_GATEWAY.md)** - 502 Bad Gateway 错误修复
- **[scripts/tools/fix_502_gateway.sh](scripts/tools/fix_502_gateway.sh)** - 502 错误自动诊断和修复脚本

#### DNS 问题
- **[docs/troubleshooting/CHECK_DNS.md](docs/troubleshooting/CHECK_DNS.md)** - DNS 检查指南

### 🤖 CI/CD 自动部署

- **[docs/guides/DEPLOYMENT_CI_CD.md](docs/guides/DEPLOYMENT_CI_CD.md)** - GitHub Actions 自动部署设置
- **[docs/guides/DEPLOYMENT_CHANGES.md](docs/guides/DEPLOYMENT_CHANGES.md)** - 部署变更记录

### 🔍 检查和诊断工具

**脚本位置：`scripts/checks/`**

- `check_firewall.sh` - 检查防火墙规则
- `check_ip_access.sh` - 检查 IP 访问
- `check_nginx_config.sh` - 检查 Nginx 配置

### ⚙️ 配置文件

**位置：`configs/`**

- `nginx/` - Nginx 配置文件
  - `climbing_system.conf` - 基础配置
  - `climbing_system_with_letsencrypt.conf` - 带 SSL 的配置
- `systemd/` - Systemd 服务配置
  - `climbing_system.service` - Gunicorn 服务配置
- `gunicorn_config.py` - Gunicorn 配置

### 🛠️ 工具脚本

**位置：`scripts/tools/`**

- `deploy.sh` - 自动部署脚本
- `setup_ec2.sh` - EC2 初始设置
- `setup_config.sh` - 配置初始化
- `fix_permissions.sh` - **一键修复权限问题**（Git、虚拟环境等，推荐）
- `fix_git_conflict.sh` - **修复 Git 冲突**（文件结构重构后使用）
- `fix_502_gateway.sh` - **502 Bad Gateway 诊断和修复**
- `fix_venv_path.sh` - 虚拟环境路径修复
- `fix_400_error.sh` - 400 错误修复脚本
- `sync_database_from_server.sh` - 从服务器同步数据库
- `sync_database_to_server.sh` - 同步数据库到服务器
- `sync_db_from_server.bat` - Windows 批处理版本

## 📁 目录结构

```
Deployment/
├── INDEX.md                    # 本文件 - 导航索引
├── README.md                   # 部署目录说明
├── QUICK_START.md             # 快速开始（保留在根目录，方便查找）
├── QUICK_DEBUG.md             # 快速调试参考（保留在根目录）
│
├── docs/                       # 文档目录
│   ├── guides/                # 主要指南
│   │   ├── AWS_EC2_DEPLOYMENT.md
│   │   ├── DEPLOYMENT_CI_CD.md
│   │   └── DEPLOYMENT_CHANGES.md
│   │
│   ├── setup/                 # 配置设置
│   │   ├── SSH_SETUP.md
│   │   ├── SSH_CONFIG_CHECKLIST.md
│   │   ├── DOMAIN_SETUP.md
│   │   ├── DOMAIN_SSL_GUIDE.md
│   │   ├── IP_ACCESS_WITH_LETSENCRYPT.md
│   │   ├── CONFIG_MANAGEMENT.md
│   │   ├── DATABASE_SETUP.md
│   │   └── DATABASE_SYNC.md
│   │
│   └── troubleshooting/       # 故障排除
│       ├── TROUBLESHOOTING_DEPLOYMENT.md
│       ├── FIX_400_ERROR.md
│       ├── FIX_404_IP_ACCESS.md
│       ├── FIX_IP_ACCESS.md
│       ├── FIX_NGINX_SYNTAX_ERROR.md
│       ├── FIX_GIT_OWNERSHIP.md
│       ├── FIREWALL_TROUBLESHOOTING.md
│       ├── CHECK_DNS.md
│       └── WHY_IP_NOT_WORKING_AFTER_DOMAIN.md
│
├── scripts/                   # 脚本目录
│   ├── tools/                # 工具脚本
│   │   ├── deploy.sh
│   │   ├── setup_ec2.sh
│   │   ├── setup_config.sh
│   │   ├── fix_venv_path.sh
│   │   ├── fix_400_error.sh
│   │   ├── sync_database_from_server.sh
│   │   ├── sync_database_to_server.sh
│   │   └── sync_db_from_server.bat
│   │
│   └── checks/               # 检查脚本
│       ├── check_firewall.sh
│       ├── check_ip_access.sh
│       └── check_nginx_config.sh
│
└── configs/                   # 配置文件
    ├── nginx/
    │   ├── climbing_system.conf
    │   └── climbing_system_with_letsencrypt.conf
    ├── systemd/
    │   └── climbing_system.service
    └── gunicorn_config.py
```

## 🎯 快速查找

### 我想...

- **首次部署项目** → 看 `QUICK_START.md` → `docs/guides/AWS_EC2_DEPLOYMENT.md`
- **更新代码到服务器** → 运行 `scripts/tools/deploy.sh`
- **配置域名** → 看 `docs/setup/DOMAIN_SETUP.md`
- **配置 SSL 证书** → 看 `docs/setup/DOMAIN_SSL_GUIDE.md`
- **同步数据库** → 看 `docs/setup/DATABASE_SYNC.md`
- **网站无法访问** → 看 `docs/troubleshooting/TROUBLESHOOTING_DEPLOYMENT.md`
- **遇到 400/404 错误** → 看 `docs/troubleshooting/FIX_400_ERROR.md` 或 `FIX_404_IP_ACCESS.md`
- **遇到 502 Bad Gateway** → 看 `docs/troubleshooting/FIX_502_BAD_GATEWAY.md` 或运行 `scripts/tools/fix_502_gateway.sh`
- **Git pull 冲突** → 看 `docs/troubleshooting/FIX_GIT_CONFLICT.md`（包含手动处理步骤）
- **配置 GitHub Actions** → 看 `docs/guides/DEPLOYMENT_CI_CD.md`
- **检查服务器状态** → 运行 `scripts/checks/` 下的检查脚本
- **查看常用命令** → 看 `QUICK_DEBUG.md`

## 💡 提示

1. **首次部署**：建议按照 `QUICK_START.md` → `AWS_EC2_DEPLOYMENT.md` 的顺序阅读
2. **日常使用**：主要使用 `deploy.sh` 和 `QUICK_DEBUG.md`
3. **遇到问题**：先查看 `TROUBLESHOOTING_DEPLOYMENT.md`，再根据具体错误查找对应文档
4. **配置变更**：查看 `DEPLOYMENT_CHANGES.md` 了解最新变更

