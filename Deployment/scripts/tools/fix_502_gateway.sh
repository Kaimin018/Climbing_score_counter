#!/bin/bash
# 502 Bad Gateway 错误修复脚本
# 使用方法：在 EC2 服务器上运行：bash Deployment/scripts/tools/fix_502_gateway.sh

set -e

PROJECT_DIR="/var/www/Climbing_score_counter"
SERVICE_NAME="climbing_system"

echo "========================================="
echo "502 Bad Gateway 错误诊断和修复"
echo "========================================="
echo ""

cd "$PROJECT_DIR"

# 1. 检查 Gunicorn 服务状态
echo "1. 检查 Gunicorn 服务状态..."
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "   ✅ Gunicorn 服务正在运行"
else
    echo "   ❌ Gunicorn 服务未运行，尝试启动..."
    sudo systemctl start $SERVICE_NAME
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "   ✅ 服务已启动"
    else
        echo "   ❌ 服务启动失败，查看日志："
        sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
        echo ""
        echo "   请检查上述错误信息并手动修复"
        exit 1
    fi
fi

# 2. 检查端口 8000 是否监听
echo "2. 检查端口 8000 监听状态..."
if sudo netstat -tlnp 2>/dev/null | grep -q ':8000 ' || sudo ss -tlnp 2>/dev/null | grep -q ':8000 '; then
    echo "   ✅ 端口 8000 正在监听"
    sudo netstat -tlnp 2>/dev/null | grep ':8000 ' || sudo ss -tlnp 2>/dev/null | grep ':8000 '
else
    echo "   ❌ 端口 8000 未监听"
    echo "   尝试重启服务..."
    sudo systemctl restart $SERVICE_NAME
    sleep 3
    if sudo netstat -tlnp 2>/dev/null | grep -q ':8000 ' || sudo ss -tlnp 2>/dev/null | grep -q ':8000 '; then
        echo "   ✅ 端口现在正在监听"
    else
        echo "   ❌ 端口仍未监听，请检查服务配置"
    fi
fi

# 3. 测试 Gunicorn 本地连接
echo "3. 测试 Gunicorn 本地连接..."
GUNICORN_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null || echo "000")
if [ "$GUNICORN_RESPONSE" = "200" ] || [ "$GUNICORN_RESPONSE" = "301" ] || [ "$GUNICORN_RESPONSE" = "302" ] || [ "$GUNICORN_RESPONSE" = "400" ]; then
    echo "   ✅ Gunicorn 响应正常 (HTTP $GUNICORN_RESPONSE)"
else
    echo "   ❌ Gunicorn 连接失败 (HTTP $GUNICORN_RESPONSE)"
    echo "   查看服务日志："
    sudo journalctl -u $SERVICE_NAME -n 30 --no-pager
fi

# 4. 检查 Nginx 配置
echo "4. 检查 Nginx 配置..."
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo "   ✅ Nginx 配置语法正确"
    sudo systemctl reload nginx
    echo "   ✅ Nginx 已重载"
else
    echo "   ❌ Nginx 配置语法错误："
    sudo nginx -t 2>&1 | grep -i error
fi

# 5. 检查 Nginx 错误日志
echo "5. 检查最近的 Nginx 错误日志..."
echo "   最后 10 行错误日志："
sudo tail -10 /var/log/nginx/error.log 2>/dev/null | grep -i "502\|bad gateway\|upstream" || echo "   未找到相关错误"

# 6. 检查虚拟环境
echo "6. 检查虚拟环境..."
if [ -d "$PROJECT_DIR/venv" ]; then
    echo "   ✅ 虚拟环境存在"
    if [ -f "$PROJECT_DIR/venv/bin/gunicorn" ]; then
        echo "   ✅ Gunicorn 已安装"
    else
        echo "   ⚠️  Gunicorn 未安装，尝试安装..."
        source venv/bin/activate
        pip install gunicorn
    fi
else
    echo "   ❌ 虚拟环境不存在"
    echo "   创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# 7. 检查配置文件路径
echo "7. 检查配置文件路径..."
if [ -f "$PROJECT_DIR/Deployment/configs/gunicorn_config.py" ]; then
    echo "   ✅ Gunicorn 配置文件存在"
elif [ -f "$PROJECT_DIR/Deployment/gunicorn_config.py" ]; then
    echo "   ⚠️  配置文件在旧位置，需要更新 systemd 服务文件"
else
    echo "   ❌ 找不到 Gunicorn 配置文件"
fi

# 8. 检查数据库权限
echo "8. 检查数据库权限..."
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    DB_OWNER=$(stat -c '%U:%G' db.sqlite3 2>/dev/null || stat -f '%Su:%Sg' db.sqlite3 2>/dev/null)
    if [ "$DB_OWNER" = "www-data:www-data" ]; then
        echo "   ✅ 数据库权限正确"
    else
        echo "   ⚠️  数据库权限不正确 ($DB_OWNER)，修复中..."
        sudo chown www-data:www-data db.sqlite3
        sudo chmod 664 db.sqlite3
        echo "   ✅ 数据库权限已修复"
    fi
else
    echo "   ℹ️  数据库文件不存在（首次部署）"
fi

# 9. 最终验证
echo ""
echo "========================================="
echo "最终验证"
echo "========================================="
echo ""

# 检查服务状态
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Gunicorn 服务：运行中"
else
    echo "❌ Gunicorn 服务：未运行"
fi

# 检查端口
if sudo netstat -tlnp 2>/dev/null | grep -q ':8000 ' || sudo ss -tlnp 2>/dev/null | grep -q ':8000 '; then
    echo "✅ 端口 8000：正在监听"
else
    echo "❌ 端口 8000：未监听"
fi

# 测试连接
GUNICORN_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null || echo "000")
if [ "$GUNICORN_TEST" != "000" ]; then
    echo "✅ Gunicorn 本地连接：正常 (HTTP $GUNICORN_TEST)"
else
    echo "❌ Gunicorn 本地连接：失败"
fi

echo ""
echo "========================================="
echo "诊断完成"
echo "========================================="
echo ""
echo "如果问题仍未解决，请："
echo "1. 查看详细日志：sudo journalctl -u climbing_system -n 50"
echo "2. 检查 Nginx 错误日志：sudo tail -20 /var/log/nginx/error.log"
echo "3. 参考文档：docs/troubleshooting/FIX_502_BAD_GATEWAY.md"
echo ""

