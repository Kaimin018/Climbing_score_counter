#!/bin/bash
# IP 访问诊断脚本
# 用于诊断为什么 IP 地址 3.26.6.19 无法访问

echo "=========================================="
echo "IP 访问诊断 (3.26.6.19)"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

IP_ADDRESS="3.26.6.19"
DOMAIN="countclimbingscore.online"

# 1. 检查 Django ALLOWED_HOSTS 是否包含 IP
echo "1. 检查 Django ALLOWED_HOSTS 配置..."
if [ -f /etc/systemd/system/climbing_system.service ]; then
    ALLOWED_HOSTS=$(grep "ALLOWED_HOSTS" /etc/systemd/system/climbing_system.service | grep -oP 'ALLOWED_HOSTS=\K[^"]*' || echo "")
    if [ -z "$ALLOWED_HOSTS" ]; then
        echo -e "${RED}✗${NC} 未找到 ALLOWED_HOSTS 环境变量"
    else
        echo -e "${GREEN}✓${NC} ALLOWED_HOSTS: $ALLOWED_HOSTS"
        
        # 检查是否包含 IP
        if echo "$ALLOWED_HOSTS" | grep -q "$IP_ADDRESS"; then
            echo -e "${GREEN}✓${NC} IP 地址 $IP_ADDRESS 在 ALLOWED_HOSTS 中"
        else
            echo -e "${RED}✗${NC} IP 地址 $IP_ADDRESS 不在 ALLOWED_HOSTS 中"
            echo "   需要添加: $IP_ADDRESS"
        fi
        
        # 检查是否包含域名
        if echo "$ALLOWED_HOSTS" | grep -q "$DOMAIN"; then
            echo -e "${GREEN}✓${NC} 域名 $DOMAIN 在 ALLOWED_HOSTS 中"
        else
            echo -e "${YELLOW}⚠${NC} 域名 $DOMAIN 不在 ALLOWED_HOSTS 中"
        fi
    fi
else
    echo -e "${RED}✗${NC} 未找到 systemd 服务文件"
fi
echo ""

# 2. 检查 Nginx server_name 是否包含 IP
echo "2. 检查 Nginx server_name 配置..."
if [ -f /etc/nginx/sites-available/climbing_system.conf ]; then
    SERVER_NAME=$(grep "server_name" /etc/nginx/sites-available/climbing_system.conf | head -1)
    echo -e "${GREEN}✓${NC} Nginx 配置文件存在"
    echo "   server_name: $SERVER_NAME"
    
    # 检查是否包含 IP
    if echo "$SERVER_NAME" | grep -q "$IP_ADDRESS"; then
        echo -e "${GREEN}✓${NC} IP 地址 $IP_ADDRESS 在 server_name 中"
    else
        echo -e "${RED}✗${NC} IP 地址 $IP_ADDRESS 不在 server_name 中"
        echo "   需要添加: $IP_ADDRESS"
    fi
    
    # 检查是否包含域名
    if echo "$SERVER_NAME" | grep -q "$DOMAIN"; then
        echo -e "${GREEN}✓${NC} 域名 $DOMAIN 在 server_name 中"
    else
        echo -e "${YELLOW}⚠${NC} 域名 $DOMAIN 不在 server_name 中"
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
    echo "   尝试启动: sudo systemctl start climbing_system"
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓${NC} Nginx 服务正在运行"
else
    echo -e "${RED}✗${NC} Nginx 服务未运行"
    echo "   尝试启动: sudo systemctl start nginx"
fi
echo ""

# 4. 测试本地连接（使用 IP 作为 Host 头）
echo "4. 测试本地连接（模拟 IP 访问）..."
echo "   测试 1: 直接访问 localhost:8000 (Gunicorn)..."
LOCAL_GUNICORN=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null)
if [ "$LOCAL_GUNICORN" = "200" ] || [ "$LOCAL_GUNICORN" = "301" ] || [ "$LOCAL_GUNICORN" = "302" ] || [ "$LOCAL_GUNICORN" = "400" ]; then
    echo -e "${GREEN}✓${NC} Gunicorn 响应正常 (HTTP $LOCAL_GUNICORN)"
    if [ "$LOCAL_GUNICORN" = "400" ]; then
        echo -e "${YELLOW}⚠${NC} 返回 400，可能是 ALLOWED_HOSTS 问题"
    fi
else
    echo -e "${RED}✗${NC} Gunicorn 连接失败 (HTTP $LOCAL_GUNICORN)"
fi

echo "   测试 2: 通过 Nginx 访问，使用 IP 作为 Host 头..."
NGINX_IP=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $IP_ADDRESS" http://127.0.0.1/ 2>/dev/null)
if [ "$NGINX_IP" = "200" ] || [ "$NGINX_IP" = "301" ] || [ "$NGINX_IP" = "302" ]; then
    echo -e "${GREEN}✓${NC} Nginx + IP Host 头响应正常 (HTTP $NGINX_IP)"
elif [ "$NGINX_IP" = "400" ]; then
    echo -e "${RED}✗${NC} 返回 400 Bad Request (可能是 ALLOWED_HOSTS 问题)"
else
    echo -e "${RED}✗${NC} Nginx + IP Host 头连接失败 (HTTP $NGINX_IP)"
fi

echo "   测试 3: 通过 Nginx 访问，使用域名作为 Host 头..."
NGINX_DOMAIN=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $DOMAIN" http://127.0.0.1/ 2>/dev/null)
if [ "$NGINX_DOMAIN" = "200" ] || [ "$NGINX_DOMAIN" = "301" ] || [ "$NGINX_DOMAIN" = "302" ]; then
    echo -e "${GREEN}✓${NC} Nginx + 域名 Host 头响应正常 (HTTP $NGINX_DOMAIN)"
else
    echo -e "${YELLOW}⚠${NC} Nginx + 域名 Host 头响应异常 (HTTP $NGINX_DOMAIN)"
fi
echo ""

# 5. 检查 Nginx 配置语法
echo "5. 检查 Nginx 配置语法..."
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo -e "${GREEN}✓${NC} Nginx 配置语法正确"
else
    echo -e "${RED}✗${NC} Nginx 配置语法错误:"
    sudo nginx -t 2>&1 | grep -i error
fi
echo ""

# 6. 检查端口监听
echo "6. 检查端口监听状态..."
if sudo netstat -tlnp 2>/dev/null | grep -q ':80 '; then
    echo -e "${GREEN}✓${NC} 端口 80 正在监听"
    sudo netstat -tlnp | grep ':80 '
else
    echo -e "${RED}✗${NC} 端口 80 未监听"
fi

if sudo netstat -tlnp 2>/dev/null | grep -q ':8000 '; then
    echo -e "${GREEN}✓${NC} 端口 8000 正在监听 (Gunicorn)"
    sudo netstat -tlnp | grep ':8000 '
else
    echo -e "${RED}✗${NC} 端口 8000 未监听 (Gunicorn 可能未运行)"
fi
echo ""

# 7. 检查最近的错误日志
echo "7. 检查最近的错误日志..."
echo "   Django/Gunicorn 日志（最后 10 行，查找 DisallowedHost 或 400 错误）:"
if [ -f /var/www/Climbing_score_counter/logs/django.log ]; then
    sudo tail -10 /var/www/Climbing_score_counter/logs/django.log 2>/dev/null | grep -i "disallowedhost\|400\|bad request" || echo "   未找到相关错误"
else
    echo "   日志文件不存在，检查 systemd 日志..."
    sudo journalctl -u climbing_system -n 20 --no-pager | grep -i "disallowedhost\|400\|bad request" || echo "   未找到相关错误"
fi

echo "   Nginx 错误日志（最后 10 行）:"
sudo tail -10 /var/log/nginx/error.log 2>/dev/null | grep -i "400\|bad request\|error" || echo "   未找到相关错误"
echo ""

# 8. 检查防火墙
echo "8. 检查防火墙配置..."
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null | head -1)
    if echo "$UFW_STATUS" | grep -q "inactive"; then
        echo -e "${GREEN}✓${NC} UFW 未激活（通常默认未激活，这是正常的）"
    else
        echo -e "${YELLOW}⚠${NC} UFW 已激活: $UFW_STATUS"
        echo "   检查端口 80 和 443 是否开放..."
        sudo ufw status | grep -E '(80|443)' || echo -e "${YELLOW}⚠${NC} 未找到端口 80 或 443 的规则"
    fi
else
    echo -e "${YELLOW}⚠${NC} UFW 未安装"
fi
echo ""

# 9. 提供修复建议
echo "=========================================="
echo "诊断结果和建议"
echo "=========================================="
echo ""

# 检查是否需要修复
NEEDS_FIX=0

if [ -f /etc/systemd/system/climbing_system.service ]; then
    ALLOWED_HOSTS=$(grep "ALLOWED_HOSTS" /etc/systemd/system/climbing_system.service | grep -oP 'ALLOWED_HOSTS=\K[^"]*' || echo "")
    if [ -n "$ALLOWED_HOSTS" ] && ! echo "$ALLOWED_HOSTS" | grep -q "$IP_ADDRESS"; then
        NEEDS_FIX=1
        echo -e "${RED}需要修复:${NC} ALLOWED_HOSTS 未包含 IP 地址"
        echo ""
        echo "修复步骤："
        echo "1. 编辑 systemd 服务文件："
        echo "   sudo nano /etc/systemd/system/climbing_system.service"
        echo ""
        echo "2. 找到 Environment=\"ALLOWED_HOSTS=...\" 这一行"
        echo "   更新为："
        echo "   Environment=\"ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,$IP_ADDRESS,127.0.0.1,localhost\""
        echo ""
        echo "3. 重新加载并重启服务："
        echo "   sudo systemctl daemon-reload"
        echo "   sudo systemctl restart climbing_system"
        echo ""
    fi
fi

if [ -f /etc/nginx/sites-available/climbing_system.conf ]; then
    SERVER_NAME=$(grep "server_name" /etc/nginx/sites-available/climbing_system.conf | head -1)
    if [ -n "$SERVER_NAME" ] && ! echo "$SERVER_NAME" | grep -q "$IP_ADDRESS"; then
        NEEDS_FIX=1
        echo -e "${RED}需要修复:${NC} Nginx server_name 未包含 IP 地址"
        echo ""
        echo "修复步骤："
        echo "1. 编辑 Nginx 配置文件："
        echo "   sudo nano /etc/nginx/sites-available/climbing_system.conf"
        echo ""
        echo "2. 找到 server_name 这一行"
        echo "   更新为："
        echo "   server_name $DOMAIN www.$DOMAIN $IP_ADDRESS;"
        echo ""
        echo "3. 测试并重载 Nginx："
        echo "   sudo nginx -t"
        echo "   sudo systemctl reload nginx"
        echo ""
    fi
fi

if [ $NEEDS_FIX -eq 0 ]; then
    echo -e "${GREEN}配置检查通过！${NC}"
    echo ""
    echo "如果 IP 仍然无法访问，可能的原因："
    echo "1. AWS 安全组未开放端口 80/443"
    echo "2. 服务未正确重启（尝试重启服务）"
    echo "3. DNS 或网络问题"
    echo ""
    echo "尝试以下命令："
    echo "  sudo systemctl restart climbing_system"
    echo "  sudo systemctl restart nginx"
    echo "  sudo systemctl status climbing_system"
    echo "  sudo systemctl status nginx"
fi

echo ""
echo "=========================================="
echo "快速测试命令"
echo "=========================================="
echo ""
echo "在服务器上测试："
echo "  curl -I -H \"Host: $IP_ADDRESS\" http://127.0.0.1/"
echo "  curl -I http://127.0.0.1:8000/"
echo ""
echo "从外部测试（在您的本地电脑上）："
echo "  curl -I http://$IP_ADDRESS/"
echo "  curl -I https://$IP_ADDRESS/"
echo ""

