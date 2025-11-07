#!/bin/bash
# Nginx 配置详细检查脚本
# 用于诊断为什么 IP 访问返回 404

echo "=========================================="
echo "Nginx 配置详细检查"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

IP_ADDRESS="3.26.6.19"
DOMAIN="countclimbingscore.online"

# 1. 检查所有启用的 Nginx 配置
echo "1. 检查所有启用的 Nginx 站点配置..."
echo ""
if [ -d /etc/nginx/sites-enabled ]; then
    echo "启用的站点配置文件："
    ls -la /etc/nginx/sites-enabled/
    echo ""
    
    for config in /etc/nginx/sites-enabled/*; do
        if [ -f "$config" ]; then
            echo "----------------------------------------"
            echo "配置文件: $config"
            echo "----------------------------------------"
            echo ""
            
            # 检查所有 server 块
            echo "所有 server 块："
            grep -n "server {" "$config" || echo "   未找到 server 块"
            echo ""
            
            # 检查所有 listen 指令
            echo "所有 listen 指令："
            grep -n "listen" "$config" || echo "   未找到 listen 指令"
            echo ""
            
            # 检查所有 server_name 指令
            echo "所有 server_name 指令："
            grep -n "server_name" "$config" || echo "   未找到 server_name 指令"
            echo ""
            
            # 检查是否有 HTTPS 重定向
            echo "HTTPS 重定向配置："
            grep -n "return 301\|return 302\|rewrite.*https" "$config" || echo "   未找到重定向配置"
            echo ""
        fi
    done
else
    echo -e "${RED}✗${NC} /etc/nginx/sites-enabled 目录不存在"
fi
echo ""

# 2. 检查默认 server 块
echo "2. 检查默认 server 块..."
echo ""
DEFAULT_SERVER=$(sudo nginx -T 2>/dev/null | grep -A 20 "listen.*default_server" || echo "")
if [ -n "$DEFAULT_SERVER" ]; then
    echo -e "${YELLOW}⚠${NC} 找到默认 server 块："
    echo "$DEFAULT_SERVER"
else
    echo -e "${GREEN}✓${NC} 未找到默认 server 块"
fi
echo ""

# 3. 检查所有监听端口 80 的 server 块
echo "3. 检查所有监听端口 80 的 server 块..."
echo ""
sudo nginx -T 2>/dev/null | grep -B 5 -A 20 "listen.*80" | head -100
echo ""

# 4. 检查完整的 Nginx 配置
echo "4. 检查完整的 Nginx 配置（仅 server 块）..."
echo ""
sudo nginx -T 2>/dev/null | grep -A 50 "server {" | head -200
echo ""

# 5. 测试不同的 Host 头
echo "5. 测试不同的 Host 头..."
echo ""
echo "测试 1: 使用 IP 作为 Host 头"
RESPONSE1=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $IP_ADDRESS" http://127.0.0.1/ 2>/dev/null)
echo "   响应码: $RESPONSE1"
if [ "$RESPONSE1" = "404" ]; then
    echo -e "${RED}✗${NC} 返回 404，说明 Nginx 找不到匹配的 server 块"
fi
echo ""

echo "测试 2: 使用域名作为 Host 头"
RESPONSE2=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $DOMAIN" http://127.0.0.1/ 2>/dev/null)
echo "   响应码: $RESPONSE2"
echo ""

echo "测试 3: 不使用 Host 头（默认）"
RESPONSE3=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/ 2>/dev/null)
echo "   响应码: $RESPONSE3"
echo ""

# 6. 检查 Nginx 访问日志
echo "6. 检查最近的 Nginx 访问日志..."
echo ""
if [ -f /var/log/nginx/access.log ]; then
    echo "最后 5 条访问记录："
    sudo tail -5 /var/log/nginx/access.log
else
    echo "   访问日志文件不存在"
fi
echo ""

# 7. 检查 Nginx 错误日志
echo "7. 检查最近的 Nginx 错误日志..."
echo ""
if [ -f /var/log/nginx/error.log ]; then
    echo "最后 10 条错误记录："
    sudo tail -10 /var/log/nginx/error.log
else
    echo "   错误日志文件不存在"
fi
echo ""

# 8. 提供修复建议
echo "=========================================="
echo "诊断结果和建议"
echo "=========================================="
echo ""

if [ "$RESPONSE1" = "404" ]; then
    echo -e "${RED}问题确认：${NC} 使用 IP 作为 Host 头返回 404"
    echo ""
    echo "可能的原因："
    echo "1. 有多个 server 块，IP 访问匹配到了错误的 server 块"
    echo "2. 有 HTTPS 重定向配置，但只针对域名"
    echo "3. 默认 server 块配置不正确"
    echo ""
    echo "修复建议："
    echo "1. 检查是否有多个 server 块监听端口 80"
    echo "2. 确保主 server 块的 server_name 包含 IP 地址"
    echo "3. 如果有 HTTPS 重定向，确保它也处理 IP 访问"
    echo ""
    echo "请检查上面的配置输出，特别是："
    echo "- 是否有多个 server 块监听端口 80"
    echo "- 每个 server 块的 server_name 是什么"
    echo "- 是否有 HTTPS 重定向配置"
fi

echo ""
echo "=========================================="
echo "快速修复命令"
echo "=========================================="
echo ""
echo "如果确认是配置问题，请执行："
echo "1. 编辑 Nginx 配置："
echo "   sudo nano /etc/nginx/sites-available/climbing_system.conf"
echo ""
echo "2. 确保主 server 块的 server_name 包含 IP："
echo "   server_name $DOMAIN www.$DOMAIN $IP_ADDRESS;"
echo ""
echo "3. 如果有 HTTPS 重定向，确保也处理 IP："
echo "   # 如果需要，可以添加一个专门处理 IP 的 server 块"
echo ""
echo "4. 测试并重载："
echo "   sudo nginx -t"
echo "   sudo systemctl reload nginx"
echo ""

