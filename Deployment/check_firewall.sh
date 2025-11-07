#!/bin/bash
# 防火墙和网络配置检查脚本
# 用于检查 AWS EC2 实例的网络配置，确保端口 80 和 443 可以正常访问

echo "=========================================="
echo "防火墙和网络配置检查"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# 1. 检查 UFW 状态
echo "1. 检查 UFW (Uncomplicated Firewall) 状态..."
ufw_status=$(sudo ufw status 2>/dev/null | head -1)
if echo "$ufw_status" | grep -q "inactive"; then
    echo -e "${YELLOW}⚠${NC} UFW 未激活（通常默认未激活，这是正常的）"
    echo "   如果 UFW 已激活，需要确保端口 80 和 443 已开放"
else
    echo -e "${GREEN}✓${NC} UFW 状态: $ufw_status"
    echo "   检查 UFW 规则..."
    sudo ufw status | grep -E '(80|443)' || echo -e "${YELLOW}⚠${NC} 未找到端口 80 或 443 的规则"
fi
echo ""

# 2. 检查 iptables 规则
echo "2. 检查 iptables 规则..."
iptables_80=$(sudo iptables -L INPUT -n | grep -E '(:80|80 )' | head -1)
iptables_443=$(sudo iptables -L INPUT -n | grep -E '(:443|443 )' | head -1)

if [ -z "$iptables_80" ]; then
    echo -e "${GREEN}✓${NC} 端口 80: 无限制规则（允许访问）"
else
    echo -e "${YELLOW}⚠${NC} 端口 80 有 iptables 规则:"
    echo "   $iptables_80"
fi

if [ -z "$iptables_443" ]; then
    echo -e "${GREEN}✓${NC} 端口 443: 无限制规则（允许访问）"
else
    echo -e "${YELLOW}⚠${NC} 端口 443 有 iptables 规则:"
    echo "   $iptables_443"
fi
echo ""

# 3. 检查端口监听状态
echo "3. 检查端口监听状态..."
if sudo netstat -tlnp 2>/dev/null | grep -q ':80 '; then
    echo -e "${GREEN}✓${NC} 端口 80 正在监听"
    sudo netstat -tlnp | grep ':80 '
else
    echo -e "${RED}✗${NC} 端口 80 未监听（Nginx 可能未运行）"
fi

if sudo netstat -tlnp 2>/dev/null | grep -q ':443 '; then
    echo -e "${GREEN}✓${NC} 端口 443 正在监听"
    sudo netstat -tlnp | grep ':443 '
else
    echo -e "${YELLOW}⚠${NC} 端口 443 未监听（如果未配置 SSL，这是正常的）"
fi
echo ""

# 4. 检查 Nginx 状态
echo "4. 检查 Nginx 状态..."
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓${NC} Nginx 正在运行"
else
    echo -e "${RED}✗${NC} Nginx 未运行"
fi
echo ""

# 5. 检查本地连接测试
echo "5. 测试本地连接..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓${NC} 本地 HTTP (端口 80) 连接正常"
else
    echo -e "${RED}✗${NC} 本地 HTTP (端口 80) 连接失败"
fi

if curl -s -o /dev/null -w "%{http_code}" https://127.0.0.1:443 2>/dev/null | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓${NC} 本地 HTTPS (端口 443) 连接正常"
else
    echo -e "${YELLOW}⚠${NC} 本地 HTTPS (端口 443) 连接失败（如果未配置 SSL，这是正常的）"
fi
echo ""

# 6. 检查 VPC 和网络 ACL（需要 AWS CLI）
echo "6. 检查 AWS 网络配置..."
if command -v aws &> /dev/null; then
    echo "   检测到 AWS CLI，可以检查安全组配置"
    echo "   注意：网络 ACL 需要在 AWS Console 中手动检查"
else
    echo -e "${YELLOW}⚠${NC} 未安装 AWS CLI，无法自动检查安全组"
    echo "   请在 AWS Console 中手动检查："
    echo "   1. EC2 → Security Groups → 检查入站规则（端口 80 和 443）"
    echo "   2. VPC → Network ACLs → 检查入站和出站规则"
fi
echo ""

# 7. 总结和建议
echo "=========================================="
echo "检查完成"
echo "=========================================="
echo ""
echo "如果端口无法从外部访问，请检查："
echo ""
echo "1. AWS 安全组（Security Group）:"
echo "   - EC2 Console → Security Groups → 选择您的安全组"
echo "   - Inbound rules 应该包含："
echo "     * 类型: HTTP, 端口: 80, 来源: 0.0.0.0/0"
echo "     * 类型: HTTPS, 端口: 443, 来源: 0.0.0.0/0"
echo ""
echo "2. 网络 ACL (Network ACL):"
echo "   - VPC Console → Network ACLs → 选择您的 VPC 的 NACL"
echo "   - Inbound rules 应该允许："
echo "     * 端口 80 (HTTP) 从 0.0.0.0/0"
echo "     * 端口 443 (HTTPS) 从 0.0.0.0/0"
echo "   - Outbound rules 应该允许所有流量（或至少允许到 0.0.0.0/0）"
echo ""
echo "3. 操作系统防火墙:"
echo "   如果 UFW 已激活，运行："
echo "   sudo ufw allow 80/tcp"
echo "   sudo ufw allow 443/tcp"
echo ""
echo "   如果使用 iptables，运行："
echo "   sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT"
echo "   sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT"
echo "   sudo iptables-save"
echo ""

