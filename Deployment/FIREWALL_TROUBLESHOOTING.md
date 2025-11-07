# 防火墙和网络配置故障排除指南

本指南帮助您诊断和修复 EC2 实例的网络访问问题，特别是端口 80 (HTTP) 和 443 (HTTPS) 的访问问题。

## 🔍 问题诊断

### 快速检查脚本

在 EC2 实例上运行：

```bash
bash Deployment/check_firewall.sh
```

这个脚本会自动检查：
- UFW 防火墙状态
- iptables 规则
- 端口监听状态
- Nginx 服务状态
- 本地连接测试

## 📋 常见问题排查

### 问题 1: AWS 安全组 (Security Group) 未正确配置

**症状**：
- 外部无法访问网站
- `curl` 从外部测试超时
- 但本地 `curl http://127.0.0.1` 可以访问

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
| SSH | TCP | 22 | 您的 IP 或 0.0.0.0/0 |

**修复方法**：
1. 点击 **Edit inbound rules**
2. 点击 **Add rule**
3. 添加 HTTP (端口 80) 和 HTTPS (端口 443)
4. 来源设置为 `0.0.0.0/0`（允许所有 IP）
5. 点击 **Save rules**

### 问题 2: 网络 ACL (Network ACL) 阻止流量

**症状**：
- 安全组配置正确，但仍无法访问
- 可能影响整个子网的所有实例

**检查方法**：
1. 登录 AWS Console
2. 进入 **VPC → Network ACLs**
3. 找到您的 VPC 使用的 NACL（通常是默认 NACL）
4. 检查 **Inbound rules** 和 **Outbound rules**

**应该有的规则**：

**Inbound rules（入站规则）**：

| 规则 # | 类型 | 协议 | 端口范围 | 来源 | 允许/拒绝 |
|--------|------|------|----------|------|-----------|
| 100 | HTTP | TCP | 80 | 0.0.0.0/0 | 允许 |
| 110 | HTTPS | TCP | 443 | 0.0.0.0/0 | 允许 |
| * | All traffic | All | All | 0.0.0.0/0 | 拒绝 |

**Outbound rules（出站规则）**：

| 规则 # | 类型 | 协议 | 端口范围 | 目标 | 允许/拒绝 |
|--------|------|------|----------|------|-----------|
| 100 | All traffic | All | All | 0.0.0.0/0 | 允许 |
| * | All traffic | All | All | 0.0.0.0/0 | 拒绝 |

**重要**：
- 规则按数字顺序评估
- 星号 (*) 规则是默认规则，应该放在最后
- 如果 NACL 有自定义规则，确保允许端口 80 和 443

**修复方法**：
1. 选择您的 NACL
2. 点击 **Edit inbound rules** 或 **Edit outbound rules**
3. 添加或修改规则，确保端口 80 和 443 被允许
4. 规则编号应该小于默认拒绝规则（通常是 32767）

### 问题 3: 操作系统防火墙 (UFW) 阻止流量

**症状**：
- 安全组和 NACL 都正确
- 本地可以访问，但外部无法访问
- UFW 状态显示为 `active`

**检查方法**：

```bash
# 检查 UFW 状态
sudo ufw status

# 检查 UFW 规则
sudo ufw status numbered
```

**修复方法**：

```bash
# 允许 HTTP (端口 80)
sudo ufw allow 80/tcp

# 允许 HTTPS (端口 443)
sudo ufw allow 443/tcp

# 重新加载 UFW
sudo ufw reload

# 验证规则
sudo ufw status
```

**注意**：如果 UFW 显示 `inactive`，则不需要配置（默认未激活）。

### 问题 4: iptables 规则阻止流量

**症状**：
- UFW 未激活，但仍有防火墙规则
- 可能是手动配置的 iptables 规则

**检查方法**：

```bash
# 查看 iptables 规则
sudo iptables -L INPUT -n -v

# 查看特定端口的规则
sudo iptables -L INPUT -n | grep -E '(:80|:443)'
```

**修复方法**：

```bash
# 允许端口 80
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT

# 允许端口 443
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 保存规则（Ubuntu/Debian）
sudo netfilter-persistent save

# 或使用 iptables-save（需要手动配置持久化）
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

**持久化 iptables 规则**：

如果使用 `iptables-save`，需要确保规则在重启后仍然有效：

```bash
# 安装 iptables-persistent（如果未安装）
sudo apt install -y iptables-persistent

# 保存当前规则
sudo netfilter-persistent save
```

### 问题 5: Nginx 未监听正确的端口

**症状**：
- 防火墙配置正确
- 但端口未监听

**检查方法**：

```bash
# 检查端口监听
sudo netstat -tlnp | grep -E ':(80|443)'

# 或使用 ss 命令
sudo ss -tlnp | grep -E ':(80|443)'

# 检查 Nginx 配置
sudo nginx -t
sudo nginx -T | grep listen
```

**修复方法**：

确保 Nginx 配置文件中包含：

```nginx
server {
    listen 80;
    listen [::]:80;
    # ... 其他配置
}

# 如果配置了 SSL
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    # ... SSL 配置
}
```

然后重启 Nginx：

```bash
sudo systemctl restart nginx
```

## 🔧 完整修复步骤

如果遇到网络访问问题，按以下顺序检查：

### 步骤 1: 检查本地服务

```bash
# 检查 Nginx 是否运行
sudo systemctl status nginx

# 检查端口是否监听
sudo netstat -tlnp | grep -E ':(80|443)'

# 测试本地连接
curl -I http://127.0.0.1
```

### 步骤 2: 检查操作系统防火墙

```bash
# 检查 UFW
sudo ufw status

# 如果 UFW 激活，确保端口开放
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 检查 iptables
sudo iptables -L INPUT -n
```

### 步骤 3: 检查 AWS 安全组

1. AWS Console → EC2 → Security Groups
2. 选择您的安全组
3. 检查 Inbound rules
4. 确保端口 80 和 443 已开放

### 步骤 4: 检查网络 ACL

1. AWS Console → VPC → Network ACLs
2. 选择您的 VPC 的 NACL
3. 检查 Inbound 和 Outbound rules
4. 确保端口 80 和 443 被允许

### 步骤 5: 测试外部访问

```bash
# 从本地电脑测试
curl -I http://your-domain.com
curl -I https://your-domain.com

# 或使用在线工具
# https://www.yougetsignal.com/tools/open-ports/
```

## 📝 快速修复命令

### 如果 UFW 阻止了端口

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

### 如果 iptables 阻止了端口

```bash
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

### 如果 Nginx 未运行

```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

## ⚠️ 重要提示

1. **安全组是有状态的**：
   - 如果允许入站流量，出站流量会自动允许
   - 但 NACL 是无状态的，需要同时配置入站和出站规则

2. **默认 NACL**：
   - 默认 NACL 通常允许所有流量
   - 如果使用自定义 NACL，需要手动配置规则

3. **防火墙优先级**：
   - AWS 安全组 → 网络 ACL → 操作系统防火墙
   - 任何一个阻止都会导致无法访问

4. **测试顺序**：
   - 先测试本地访问（127.0.0.1）
   - 再测试外部访问（域名或 IP）
   - 这样可以快速定位问题所在

## 🔗 相关文档

- [AWS 安全组文档](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html)
- [AWS 网络 ACL 文档](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)
- [UFW 文档](https://help.ubuntu.com/community/UFW)
- [iptables 文档](https://netfilter.org/documentation/)

