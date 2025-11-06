# 部署相關文件

本目錄包含所有與部署相關的文件和腳本。

## 文件結構

```
Deployment/
├── README.md                          # 本文件
├── AWS_EC2_DEPLOYMENT.md              # AWS EC2 完整部署指南
├── DEPLOYMENT_CI_CD.md                # CI/CD 自動部署指南
├── DEPLOYMENT_CHANGES.md              # 部署修改總結
├── DOMAIN_SETUP.md                    # 域名配置指南
├── CONFIG_MANAGEMENT.md                # 配置管理指南
├── TROUBLESHOOTING_DEPLOYMENT.md      # 故障排除指南
├── deploy.sh                          # 自動部署腳本
├── setup_ec2.sh                       # EC2 初始設置腳本
├── setup_config.sh                    # 配置初始化腳本
├── fix_venv_path.sh                   # 虛擬環境路徑修復腳本
├── gunicorn_config.py                 # Gunicorn 配置文件
├── nginx/                              # Nginx 配置
│   └── climbing_system.conf
└── systemd/                            # Systemd 服務配置
    └── climbing_system.service
```

## 快速開始

### 首次部署

1. **初始設置**：
   ```bash
   bash Deployment/setup_ec2.sh
   ```

2. **配置服務器**：
   ```bash
   bash Deployment/setup_config.sh
   ```

3. **執行部署**：
   ```bash
   bash Deployment/deploy.sh
   ```

### 更新部署

```bash
bash Deployment/deploy.sh
```

## 文檔說明

### 主要指南

- **`AWS_EC2_DEPLOYMENT.md`**: 完整的 AWS EC2 部署指南，包含所有步驟和詳細說明
- **`DEPLOYMENT_CI_CD.md`**: GitHub Actions 自動部署設置和使用指南
- **`DOMAIN_SETUP.md`**: 域名和 SSL 證書配置指南
- **`CONFIG_MANAGEMENT.md`**: 服務器配置管理策略說明
- **`TROUBLESHOOTING_DEPLOYMENT.md`**: 常見部署問題和解決方案

### 腳本說明

- **`deploy.sh`**: 自動化部署腳本，處理代碼更新、依賴安裝、遷移、服務重啟等
- **`setup_ec2.sh`**: EC2 初始環境設置腳本
- **`setup_config.sh`**: 交互式配置初始化腳本
- **`fix_venv_path.sh`**: 虛擬環境路徑問題修復工具

### 配置文件

- **`gunicorn_config.py`**: Gunicorn WSGI 服務器配置
- **`nginx/climbing_system.conf`**: Nginx 反向代理配置模板
- **`systemd/climbing_system.service`**: Systemd 服務單元文件模板

## 使用注意事項

1. **路徑引用**: 所有腳本和配置文件中的路徑引用已更新為 `Deployment/` 前綴
2. **配置文件**: 模板文件使用占位符，實際部署時會自動替換
3. **權限**: 確保腳本有執行權限：`chmod +x Deployment/*.sh`
4. **Git 倉庫**: 部署腳本會自動從 Git 倉庫拉取最新代碼

## 相關文檔

- 項目主 README: `../README.md`
- 架構文檔: `../ARCHITECTURE.md`
- 快速參考: `../QUICK_START.md`

