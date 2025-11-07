# SSH 配置檢查清單

本文件用於檢查 GitHub Actions 自動部署的 SSH 配置是否完整。

## ✅ 當前配置狀態

### 1. GitHub Actions 工作流配置

#### ✅ `deploy.yml` (自動部署)
- **Configure SSH 步驟**：已配置（第50-63行）
- **SSH 密鑰設置**：已配置
- **主機指紋掃描**：已配置（`ssh-keyscan`）
- **部署步驟**：已配置 SSH 連接

#### ✅ `deploy-manual.yml` (手動部署)
- **Configure SSH 步驟**：已配置（第61-74行）
- **SSH 密鑰設置**：已配置
- **主機指紋掃描**：已配置
- **部署步驟**：已配置 SSH 連接

### 2. 必需的 GitHub Secrets

需要在 GitHub 倉庫中配置以下 Secrets：

| Secret 名稱 | 說明 | 狀態 | 檢查方法 |
|-----------|------|------|---------|
| `EC2_HOST` | EC2 實例 IP 或域名 | ⚠️ 需檢查 | GitHub → Settings → Secrets |
| `EC2_USER` | SSH 用戶名（通常是 `ubuntu`） | ⚠️ 需檢查 | GitHub → Settings → Secrets |
| `EC2_SSH_KEY` | SSH 私鑰完整內容 | ⚠️ 需檢查 | GitHub → Settings → Secrets |

## 🔍 檢查步驟

### 步驟 1: 檢查 GitHub Secrets 是否已配置

1. 進入 GitHub 倉庫
2. 點擊 `Settings` → `Secrets and variables` → `Actions`
3. 確認以下 Secrets 是否存在：
   - ✅ `EC2_HOST`
   - ✅ `EC2_USER`
   - ✅ `EC2_SSH_KEY`

**如果缺少任何 Secret**：
- 點擊 `New repository secret` 添加
- 參考 `Deployment/DEPLOYMENT_CI_CD.md` 中的詳細說明

### 步驟 2: 驗證 EC2_HOST 格式

**正確格式**：
- IP 地址：`3.26.6.19`
- 域名：`countclimbingscore.online`

**檢查方法**：
```bash
# 測試連接
ping 3.26.6.19
# 或
ping countclimbingscore.online
```

### 步驟 3: 驗證 EC2_USER

**常見值**：
- Ubuntu: `ubuntu` ✅
- Amazon Linux: `ec2-user`
- Debian: `admin` 或 `debian`

**檢查方法**：
- 查看 EC2 實例的 AMI 類型
- 或參考 AWS 文檔

### 步驟 4: 驗證 EC2_SSH_KEY 格式

**正確格式**：
```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
（多行密鑰內容）
...
-----END RSA PRIVATE KEY-----
```

**檢查要點**：
- ✅ 必須包含首行：`-----BEGIN RSA PRIVATE KEY-----`
- ✅ 必須包含尾行：`-----END RSA PRIVATE KEY-----`
- ✅ 中間包含完整的密鑰內容
- ✅ 沒有額外的空格或換行

**獲取方法**：
```bash
# 在本地查看密鑰文件
cat ~/.ssh/your-key.pem

# 複製完整內容（包括首尾標記）到 GitHub Secrets
```

### 步驟 5: 測試 SSH 連接

在本地測試 SSH 連接是否正常：

```bash
# 使用您的密鑰文件測試
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip

# 如果連接成功，說明 SSH 配置正確
```

### 步驟 6: 檢查 EC2 安全組

確保 EC2 安全組允許 SSH 連接：

1. 進入 AWS Console → EC2 → Security Groups
2. 檢查入站規則：
   - **端口 22 (SSH)**: 應該允許您的 IP 或 GitHub Actions IP
   - **注意**：如果使用 GitHub Actions，需要允許來自 GitHub 的連接

**GitHub Actions IP 範圍**：
- GitHub Actions 使用動態 IP，建議允許所有 IP（`0.0.0.0/0`）或使用 GitHub 的 IP 範圍
- 參考：https://api.github.com/meta

## 📋 快速檢查命令

### 在本地檢查 SSH 配置

```bash
# 1. 檢查密鑰文件是否存在
ls -la ~/.ssh/your-key.pem

# 2. 檢查密鑰文件權限（應該是 600）
stat -c "%a %n" ~/.ssh/your-key.pem

# 3. 測試 SSH 連接
ssh -i ~/.ssh/your-key.pem -o ConnectTimeout=5 ubuntu@your-ec2-ip "echo '連接成功'"
```

### 檢查 GitHub Actions 日誌

1. 進入 GitHub 倉庫 → `Actions` 標籤
2. 查看最新的部署工作流
3. 檢查 "Configure SSH" 步驟的輸出：
   - ✅ 應該顯示 "SSH 配置成功"
   - ❌ 如果顯示 "跳過 SSH 配置：未配置 EC2 secrets"，說明 Secrets 未配置

## ⚠️ 常見問題

### 問題 1: Secrets 未配置

**症狀**：GitHub Actions 日誌顯示 "跳過 SSH 配置"

**解決方法**：
1. 進入 GitHub → Settings → Secrets and variables → Actions
2. 添加缺少的 Secrets
3. 重新運行工作流

### 問題 2: SSH 連接失敗

**症狀**：`Permission denied (publickey)`

**可能原因**：
1. `EC2_SSH_KEY` 格式不正確（缺少首尾標記）
2. 密鑰文件內容不完整
3. EC2 實例未配置該 SSH 密鑰

**解決方法**：
1. 檢查 `EC2_SSH_KEY` 是否包含完整的私鑰內容
2. 確認密鑰文件格式正確
3. 在 EC2 上檢查 `~/.ssh/authorized_keys` 是否包含對應的公鑰

### 問題 3: 連接超時

**症狀**：`Connection timed out`

**可能原因**：
1. EC2 實例未運行
2. 安全組未允許 SSH 連接
3. IP 地址不正確

**解決方法**：
1. 檢查 EC2 實例狀態
2. 檢查安全組規則（端口 22）
3. 確認 IP 地址正確

## ✅ 配置完成檢查清單

- [ ] GitHub Secrets 已配置（EC2_HOST, EC2_USER, EC2_SSH_KEY）
- [ ] EC2_HOST 格式正確（IP 或域名）
- [ ] EC2_USER 正確（通常是 `ubuntu`）
- [ ] EC2_SSH_KEY 包含完整的私鑰內容（包括首尾標記）
- [ ] 本地 SSH 連接測試成功
- [ ] EC2 安全組允許 SSH 連接（端口 22）
- [ ] GitHub Actions 工作流可以成功執行 "Configure SSH" 步驟
- [ ] GitHub Actions 工作流可以成功執行 "Deploy to EC2" 步驟

## 📚 相關文檔

- `Deployment/SSH_SETUP.md` - SSH 連接配置指南
- `Deployment/DEPLOYMENT_CI_CD.md` - CI/CD 自動部署指南
- `Deployment/AWS_EC2_DEPLOYMENT.md` - 完整部署指南

