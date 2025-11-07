# SSH 連接配置指南

本指南說明如何配置 SSH 連接到 AWS EC2 實例。

## 前置需求

1. **SSH 密鑰文件**（`.pem` 文件）
   - 在創建 EC2 實例時下載的密鑰對文件
   - 如果遺失，需要在 AWS Console 中創建新的密鑰對

2. **EC2 實例信息**
   - EC2 實例的 IP 地址或域名
   - 用戶名（Ubuntu 系統通常是 `ubuntu`）

## 方法 1: 直接使用 SSH 命令（最簡單）

### Windows 用戶

**使用 Git Bash 或 PowerShell**：

```bash
# 基本連接命令
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip

# 示例（替換為您的實際值）
ssh -i ~/.ssh/climbing-key.pem ubuntu@3.26.6.19
```

**注意事項**：
- 如果密鑰文件在 `C:\Users\YourName\.ssh\`，路徑應該是 `~/.ssh/your-key.pem` 或 `/c/Users/YourName/.ssh/your-key.pem`
- 首次連接時會提示確認主機指紋，輸入 `yes` 確認

### macOS/Linux 用戶

```bash
# 設置密鑰文件權限（首次使用必須執行）
chmod 600 ~/.ssh/your-key.pem

# 連接
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip
```

## 方法 2: 配置 SSH Config 文件（推薦，更方便）

配置 SSH config 文件後，可以使用簡短的別名連接，無需每次都輸入完整命令。

### Windows 用戶

1. **創建或編輯 SSH config 文件**：

```bash
# 在 Git Bash 中執行
nano ~/.ssh/config
# 或使用記事本編輯
notepad ~/.ssh/config
```

2. **添加以下配置**（替換為您的實際值）：

```
Host climbing-ec2
    HostName 3.26.6.19
    User ubuntu
    IdentityFile ~/.ssh/climbing-key.pem
    IdentitiesOnly yes
```

3. **保存文件後，使用簡短命令連接**：

```bash
ssh climbing-ec2
```

### macOS/Linux 用戶

1. **創建或編輯 SSH config 文件**：

```bash
nano ~/.ssh/config
# 或
vim ~/.ssh/config
```

2. **添加配置**（與 Windows 相同）：

```
Host climbing-ec2
    HostName 3.26.6.19
    User ubuntu
    IdentityFile ~/.ssh/climbing-key.pem
    IdentitiesOnly yes
```

3. **設置文件權限**：

```bash
chmod 600 ~/.ssh/config
chmod 600 ~/.ssh/climbing-key.pem
```

4. **使用簡短命令連接**：

```bash
ssh climbing-ec2
```

## 配置說明

### SSH Config 文件參數說明

- **Host**: 別名，可以自定義（如 `climbing-ec2`）
- **HostName**: EC2 實例的 IP 地址或域名
- **User**: SSH 用戶名（Ubuntu 系統通常是 `ubuntu`）
- **IdentityFile**: SSH 密鑰文件的完整路徑
- **IdentitiesOnly**: 只使用指定的密鑰文件

### 多個 EC2 實例配置

如果有多個 EC2 實例，可以在 config 文件中添加多個配置：

```
Host climbing-ec2
    HostName 3.26.6.19
    User ubuntu
    IdentityFile ~/.ssh/climbing-key.pem
    IdentitiesOnly yes

Host another-ec2
    HostName 1.2.3.4
    User ubuntu
    IdentityFile ~/.ssh/another-key.pem
    IdentitiesOnly yes
```

## 常見問題

### 問題 1: Permission denied (publickey)

**原因**：密鑰文件權限不正確或密鑰未正確配置

**解決方法**：

**Windows (Git Bash)**：
```bash
# 設置密鑰文件權限
chmod 600 ~/.ssh/your-key.pem
```

**macOS/Linux**：
```bash
chmod 600 ~/.ssh/your-key.pem
```

### 問題 2: 找不到密鑰文件

**原因**：路徑不正確

**解決方法**：
- 確認密鑰文件是否在 `~/.ssh/` 目錄下
- 使用絕對路徑：`/c/Users/YourName/.ssh/your-key.pem`（Windows Git Bash）
- 或使用相對路徑：`./your-key.pem`（如果密鑰文件在當前目錄）

### 問題 3: 連接超時

**原因**：
1. EC2 實例未運行
2. 安全組未允許 SSH 連接（端口 22）
3. IP 地址不正確

**解決方法**：
1. 檢查 EC2 實例狀態（AWS Console）
2. 檢查安全組規則（允許端口 22 的 SSH 連接）
3. 確認 IP 地址是否正確（使用 Public IP 或 Public DNS）

### 問題 4: 首次連接提示確認主機指紋

**症狀**：
```
The authenticity of host '3.26.6.19 (3.26.6.19)' can't be established.
ECDSA key fingerprint is SHA256:...
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

**解決方法**：
輸入 `yes` 確認，這會將主機添加到 `~/.ssh/known_hosts` 文件中。

## 快速測試連接

```bash
# 測試連接（不登錄，只執行一個命令）
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip "echo '連接成功'"

# 或使用 config 別名
ssh climbing-ec2 "echo '連接成功'"
```

## 使用 SSH 進行文件傳輸

### 從本地複製文件到 EC2

```bash
# 使用 scp 命令
scp -i ~/.ssh/your-key.pem local-file.txt ubuntu@your-ec2-ip:/home/ubuntu/

# 或使用 config 別名
scp local-file.txt climbing-ec2:/home/ubuntu/
```

### 從 EC2 複製文件到本地

```bash
# 使用 scp 命令
scp -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip:/home/ubuntu/remote-file.txt ./

# 或使用 config 別名
scp climbing-ec2:/home/ubuntu/remote-file.txt ./
```

## 安全建議

1. **保護密鑰文件**：
   - 不要將 `.pem` 文件提交到 Git 倉庫
   - 設置正確的文件權限（600）
   - 定期備份密鑰文件

2. **限制 SSH 訪問**：
   - 在 EC2 安全組中只允許必要的 IP 地址訪問端口 22
   - 避免允許 `0.0.0.0/0`（所有 IP）

3. **使用 SSH 密鑰而非密碼**：
   - 禁用密碼登錄，只使用密鑰認證

4. **定期更新密鑰**：
   - 定期輪換 SSH 密鑰以提高安全性

## 相關文檔

- `Deployment/AWS_EC2_DEPLOYMENT.md` - 完整部署指南
- `Deployment/QUICK_DEBUG.md` - 快速調試命令
- `Deployment/DATABASE_SYNC.md` - 數據庫同步（需要 SSH）

