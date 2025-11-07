# Deployment 目录

本目录包含所有与部署相关的文件、脚本和文档。

## 🚀 快速开始

**👉 首次使用？请先查看 [INDEX.md](INDEX.md) - 根据你的需求找到对应的文档和脚本**

### 最常用的文件

- **[INDEX.md](INDEX.md)** - 📚 **导航索引**（推荐从这里开始）
- **[QUICK_START.md](QUICK_START.md)** - 快速部署步骤（5分钟上手）
- **[QUICK_DEBUG.md](QUICK_DEBUG.md)** - 快速调试命令参考

## 📁 目录结构

```
Deployment/
├── INDEX.md                    # 📚 导航索引 - 根据需求查找文档
├── README.md                   # 本文件
├── QUICK_START.md             # 快速开始指南
├── QUICK_DEBUG.md             # 快速调试参考
│
├── docs/                       # 📖 文档目录
│   ├── guides/                # 主要指南
│   │   ├── AWS_EC2_DEPLOYMENT.md
│   │   ├── DEPLOYMENT_CI_CD.md
│   │   └── DEPLOYMENT_CHANGES.md
│   │
│   ├── setup/                 # 配置设置文档
│   │   ├── SSH_SETUP.md
│   │   ├── SSH_CONFIG_CHECKLIST.md
│   │   ├── DOMAIN_SETUP.md
│   │   ├── DOMAIN_SSL_GUIDE.md
│   │   ├── IP_ACCESS_WITH_LETSENCRYPT.md
│   │   ├── CONFIG_MANAGEMENT.md
│   │   ├── DATABASE_SETUP.md
│   │   └── DATABASE_SYNC.md
│   │
│   └── troubleshooting/       # 故障排除文档
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
├── scripts/                   # 🛠️ 脚本目录
│   ├── tools/                # 工具脚本
│   │   ├── deploy.sh                    # 自动部署脚本
│   │   ├── setup_ec2.sh                 # EC2 初始设置
│   │   ├── setup_config.sh              # 配置初始化
│   │   ├── fix_venv_path.sh             # 虚拟环境路径修复
│   │   ├── fix_400_error.sh             # 400 错误修复
│   │   ├── fix_nginx_syntax.sh          # Nginx 语法修复
│   │   ├── sync_database_from_server.sh # 从服务器同步数据库
│   │   ├── sync_database_to_server.sh   # 同步数据库到服务器
│   │   └── sync_db_from_server.bat      # Windows 批处理版本
│   │
│   └── checks/               # 检查脚本
│       ├── check_firewall.sh            # 检查防火墙
│       ├── check_ip_access.sh           # 检查 IP 访问
│       └── check_nginx_config.sh        # 检查 Nginx 配置
│
└── configs/                   # ⚙️ 配置文件
    ├── nginx/
    │   ├── climbing_system.conf
    │   └── climbing_system_with_letsencrypt.conf
    ├── systemd/
    │   └── climbing_system.service
    └── gunicorn_config.py
```

## 🎯 使用场景

### 首次部署
1. 查看 [INDEX.md](INDEX.md) → "首次部署" 部分
2. 阅读 [QUICK_START.md](QUICK_START.md)
3. 参考 [docs/guides/AWS_EC2_DEPLOYMENT.md](docs/guides/AWS_EC2_DEPLOYMENT.md)

### 日常更新
- 运行 `scripts/tools/deploy.sh`
- 参考 [QUICK_DEBUG.md](QUICK_DEBUG.md) 查看常用命令

### 配置域名/SSL
- 查看 [docs/setup/DOMAIN_SETUP.md](docs/setup/DOMAIN_SETUP.md)
- 查看 [docs/setup/DOMAIN_SSL_GUIDE.md](docs/setup/DOMAIN_SSL_GUIDE.md)

### 遇到问题
- 查看 [INDEX.md](INDEX.md) → "遇到问题？" 部分
- 或直接查看 [docs/troubleshooting/TROUBLESHOOTING_DEPLOYMENT.md](docs/troubleshooting/TROUBLESHOOTING_DEPLOYMENT.md)

## 📚 详细导航

**👉 请查看 [INDEX.md](INDEX.md) 获取完整的导航指南**

INDEX.md 包含：
- 按使用场景分类的文档索引
- 快速查找表
- 每个文件的用途说明
- 推荐阅读顺序

## ⚠️ 重要提示

1. **路径引用**：所有脚本中的路径引用已更新为新的目录结构
2. **脚本权限**：确保脚本有执行权限：`chmod +x scripts/tools/*.sh scripts/checks/*.sh`
3. **配置文件**：模板文件使用占位符，实际部署时会自动替换
4. **Git 仓库**：部署脚本会自动从 Git 仓库拉取最新代码

## 🔗 相关文档

- 项目主 README: `../README.md`
- 架构文档: `../ARCHITECTURE.md`
- 设置指南: `../SETUP.md`
