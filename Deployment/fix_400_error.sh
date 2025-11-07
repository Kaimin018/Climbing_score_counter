#!/bin/bash
# 400 Bad Request 错误诊断和修复脚本

echo "=========================================="
echo "400 Bad Request 错误诊断"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DOMAIN="countclimbingscore.online"

# 1. 检查 Django ALLOWED_HOSTS
echo "1. 检查 Django ALLOWED_HOSTS 配置..."
echo "   检查 systemd 服务配置..."

if [ -f /etc/systemd/system/climbing_system.service ]; then
    ALLOWED_HOSTS=$(grep "ALLOWED_HOSTS" /etc/systemd/system/climbing_system.service | grep -oP 'ALLOWED_HOSTS=\K[^"]*' || echo "")
    if [ -z "$ALLOWED_HOSTS" ]; then
        echo -e "${RED}✗${NC} 未找到 ALLOWED_HOSTS 环境变量"
    else
        echo -e "${GREEN}✓${NC} ALLOWED_HOSTS: $ALLOWED_HOSTS"
        if echo "$ALLOWED_HOSTS" | grep -q "$DOMAIN"; then
            echo -e "${GREEN}✓${NC} 域名 $DOMAIN 在 ALLOWED_HOSTS 中"
        else
            echo -e "${RED}✗${NC} 域名 $DOMAIN 不在 ALLOWED_HOSTS 中"
            echo "   需要添加: $DOMAIN"
        fi
    fi
else
    echo -e "${RED}✗${NC} 未找到 systemd 服务文件"
fi
echo ""

# 2. 检查 Nginx 配置
echo "2. 检查 Nginx 配置..."
if [ -f /etc/nginx/sites-available/climbing_system.conf ]; then
    SERVER_NAME=$(grep "server_name" /etc/nginx/sites-available/climbing_system.conf | head -1)
    echo -e "${GREEN}✓${NC} Nginx 配置文件存在"
    echo "   server_name: $SERVER_NAME"
    
    if echo "$SERVER_NAME" | grep -q "$DOMAIN"; then
        echo -e "${GREEN}✓${NC} 域名 $DOMAIN 在 server_name 中"
    else
        echo -e "${RED}✗${NC} 域名 $DOMAIN 不在 server_name 中"
    fi
    
    # 检查 proxy_set_header Host
    if grep -q "proxy_set_header Host" /etc/nginx/sites-available/climbing_system.conf; then
        echo -e "${GREEN}✓${NC} 找到 proxy_set_header Host 配置"
    else
        echo -e "${YELLOW}⚠${NC} 未找到 proxy_set_header Host 配置（可能需要添加）"
    fi
else
    echo -e "${RED}✗${NC} 未找到 Nginx 配置文件"
fi
echo ""

# 3. 检查服务状态
echo "3. 检查服务状态..."
if systemctl is-active --quiet climbing_system; then
    echo -e "${GREEN}✓${NC} climbing_system 服务正在运行"
else
    echo -e "${RED}✗${NC} climbing_system 服务未运行"
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓${NC} Nginx 服务正在运行"
else
    echo -e "${RED}✗${NC} Nginx 服务未运行"
fi
echo ""

# 4. 测试本地连接
echo "4. 测试本地连接..."
LOCAL_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null)
if [ "$LOCAL_RESPONSE" = "200" ] || [ "$LOCAL_RESPONSE" = "301" ] || [ "$LOCAL_RESPONSE" = "302" ]; then
    echo -e "${GREEN}✓${NC} 本地连接正常 (HTTP $LOCAL_RESPONSE)"
else
    echo -e "${RED}✗${NC} 本地连接失败 (HTTP $LOCAL_RESPONSE)"
fi

# 测试通过 Nginx
NGINX_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $DOMAIN" http://127.0.0.1/ 2>/dev/null)
if [ "$NGINX_RESPONSE" = "200" ] || [ "$NGINX_RESPONSE" = "301" ] || [ "$NGINX_RESPONSE" = "302" ]; then
    echo -e "${GREEN}✓${NC} Nginx 本地连接正常 (HTTP $NGINX_RESPONSE)"
else
    echo -e "${RED}✗${NC} Nginx 本地连接失败 (HTTP $NGINX_RESPONSE)"
fi
echo ""

# 5. 检查日志
echo "5. 检查最近的错误日志..."
echo "   Django 日志（最后 5 行）:"
if [ -f /var/www/Climbing_score_counter/logs/django.log ]; then
    tail -5 /var/www/Climbing_score_counter/logs/django.log 2>/dev/null | grep -i "400\|bad request\|disallowedhost" || echo "   未找到相关错误"
else
    echo "   日志文件不存在"
fi

echo "   Nginx 错误日志（最后 5 行）:"
sudo tail -5 /var/log/nginx/error.log 2>/dev/null | grep -i "400\|bad request" || echo "   未找到相关错误"
echo ""

# 6. 提供修复建议
echo "=========================================="
echo "修复建议"
echo "=========================================="
echo ""
echo "如果 ALLOWED_HOSTS 未包含域名，请执行以下步骤："
echo ""
echo "1. 编辑 systemd 服务文件："
echo "   sudo nano /etc/systemd/system/climbing_system.service"
echo ""
echo "2. 更新 ALLOWED_HOSTS 环境变量："
echo "   Environment=\"ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,3.26.6.19,127.0.0.1,localhost\""
echo ""
echo "3. 重新加载并重启服务："
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl restart climbing_system"
echo ""
echo "4. 检查 Nginx 配置："
echo "   sudo nginx -t"
echo "   sudo systemctl reload nginx"
echo ""

