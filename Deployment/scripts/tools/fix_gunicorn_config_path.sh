#!/bin/bash
# 修复 Gunicorn 配置文件路径（文件结构重构后使用）
# 使用方法：在 EC2 服务器上运行：bash Deployment/scripts/tools/fix_gunicorn_config_path.sh

set -e

SERVICE_FILE="/etc/systemd/system/climbing_system.service"
PROJECT_DIR="/var/www/Climbing_score_counter"

echo "========================================="
echo "修复 Gunicorn 配置文件路径"
echo "========================================="
echo ""

# 1. 检查新配置文件位置
echo "1. 检查配置文件位置..."
if [ -f "$PROJECT_DIR/Deployment/configs/gunicorn_config.py" ]; then
    echo "   ✅ 新路径存在: Deployment/configs/gunicorn_config.py"
    NEW_CONFIG_PATH="$PROJECT_DIR/Deployment/configs/gunicorn_config.py"
elif [ -f "$PROJECT_DIR/Deployment/gunicorn_config.py" ]; then
    echo "   ✅ 旧路径存在: Deployment/gunicorn_config.py"
    NEW_CONFIG_PATH="$PROJECT_DIR/Deployment/gunicorn_config.py"
else
    echo "   ❌ 找不到配置文件"
    echo "   请检查文件是否存在："
    echo "   - $PROJECT_DIR/Deployment/configs/gunicorn_config.py"
    echo "   - $PROJECT_DIR/Deployment/gunicorn_config.py"
    exit 1
fi

# 2. 检查 systemd 服务文件
echo "2. 检查 systemd 服务文件..."
if [ ! -f "$SERVICE_FILE" ]; then
    echo "   ❌ 服务文件不存在: $SERVICE_FILE"
    echo "   请先创建服务文件"
    exit 1
fi

# 3. 备份服务文件
echo "3. 备份服务文件..."
sudo cp "$SERVICE_FILE" "$SERVICE_FILE.backup.$(date +%Y%m%d_%H%M%S)"
echo "   ✅ 已备份到: $SERVICE_FILE.backup.*"

# 4. 更新配置文件路径
echo "4. 更新配置文件路径..."
OLD_PATHS=(
    "/var/www/Climbing_score_counter/Deployment/gunicorn_config.py"
    "/var/www/Climbing_score_counter/gunicorn_config.py"
)

for OLD_PATH in "${OLD_PATHS[@]}"; do
    if sudo grep -q "$OLD_PATH" "$SERVICE_FILE"; then
        echo "   🔧 找到旧路径: $OLD_PATH"
        sudo sed -i "s|$OLD_PATH|$NEW_CONFIG_PATH|g" "$SERVICE_FILE"
        echo "   ✅ 已更新为: $NEW_CONFIG_PATH"
    fi
done

# 5. 验证更新
echo "5. 验证更新..."
if sudo grep -q "$NEW_CONFIG_PATH" "$SERVICE_FILE"; then
    echo "   ✅ 路径已更新"
    echo "   当前配置路径:"
    sudo grep "gunicorn_config.py" "$SERVICE_FILE" | head -1
else
    echo "   ⚠️  未找到配置文件路径，可能需要手动检查"
    echo "   当前 ExecStart 行:"
    sudo grep "ExecStart" "$SERVICE_FILE"
fi

# 6. 验证配置文件是否存在
echo "6. 验证配置文件..."
if [ -f "$NEW_CONFIG_PATH" ]; then
    echo "   ✅ 配置文件存在"
else
    echo "   ❌ 配置文件不存在: $NEW_CONFIG_PATH"
    echo "   请检查文件路径"
    exit 1
fi

# 7. 重新加载 systemd 配置
echo "7. 重新加载 systemd 配置..."
sudo systemctl daemon-reload
echo "   ✅ systemd 配置已重新加载"

# 8. 重启服务
echo "8. 重启服务..."
sudo systemctl restart climbing_system
sleep 2

# 9. 检查服务状态
echo "9. 检查服务状态..."
if systemctl is-active --quiet climbing_system; then
    echo "   ✅ 服务已成功启动"
else
    echo "   ❌ 服务启动失败，查看日志："
    sudo journalctl -u climbing_system -n 20 --no-pager
    echo ""
    echo "   如果仍有问题，请检查："
    echo "   1. 配置文件路径是否正确"
    echo "   2. 虚拟环境路径是否正确"
    echo "   3. 查看完整日志: sudo journalctl -u climbing_system -n 50"
    exit 1
fi

echo ""
echo "========================================="
echo "修复完成！"
echo "========================================="
echo ""
echo "服务状态："
sudo systemctl status climbing_system --no-pager -l | head -10
echo ""

