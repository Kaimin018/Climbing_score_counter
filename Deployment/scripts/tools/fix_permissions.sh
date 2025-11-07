#!/bin/bash
# 修复项目目录权限脚本
# 使用方法：在 EC2 服务器上运行：bash Deployment/scripts/tools/fix_permissions.sh

set -e

PROJECT_DIR="/var/www/Climbing_score_counter"
CURRENT_USER=$(whoami)

echo "========================================="
echo "修复项目目录权限"
echo "========================================="
echo ""

# 检查是否在正确的目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 错误: 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# 1. 配置 Git 安全目录
echo "1. 配置 Git 安全目录..."
if ! git config --global --get-all safe.directory | grep -q "$PROJECT_DIR"; then
    git config --global --add safe.directory "$PROJECT_DIR"
    echo "   ✅ Git 安全目录已配置"
else
    echo "   ℹ️  Git 安全目录已存在"
fi

# 2. 修复 .git 目录权限
echo "2. 修复 .git 目录权限..."
if [ -d ".git" ]; then
    sudo chown -R $CURRENT_USER:$CURRENT_USER .git
    echo "   ✅ .git 目录权限已修复"
else
    echo "   ⚠️  未找到 .git 目录"
fi

# 3. 将当前用户添加到 www-data 组
echo "3. 将 $CURRENT_USER 添加到 www-data 组..."
if ! groups | grep -q www-data; then
    sudo usermod -a -G www-data $CURRENT_USER
    echo "   ✅ 用户已添加到 www-data 组"
    echo "   ⚠️  需要重新登录才能使组变更生效"
else
    echo "   ℹ️  用户已在 www-data 组中"
fi

# 4. 给项目目录添加组写权限
echo "4. 给项目目录添加组写权限..."
sudo chmod -R g+w "$PROJECT_DIR"
echo "   ✅ 组写权限已添加"

# 5. 确保项目目录的所有者是 www-data，组是 www-data
echo "5. 设置项目目录所有者..."
sudo chown -R www-data:www-data "$PROJECT_DIR"
echo "   ✅ 目录所有者已设置为 www-data:www-data"

# 6. 修复 .git 目录为当前用户（以便执行 Git 操作）
if [ -d ".git" ]; then
    sudo chown -R $CURRENT_USER:$CURRENT_USER .git
    echo "   ✅ .git 目录所有者已设置为 $CURRENT_USER"
fi

# 7. 设置特定目录的权限
echo "6. 设置特定目录权限..."
sudo chmod -R 775 "$PROJECT_DIR"/{logs,media,backups} 2>/dev/null || true
sudo chmod -R 755 "$PROJECT_DIR"/staticfiles 2>/dev/null || true
echo "   ✅ 目录权限已设置"

echo ""
echo "========================================="
echo "权限修复完成！"
echo "========================================="
echo ""
echo "⚠️  重要提示："
echo "   如果用户组已更改，请重新登录 SSH 会话以使组变更生效"
echo ""
echo "验证命令："
echo "   groups                    # 查看当前用户组"
echo "   ls -la .git/FETCH_HEAD    # 检查 .git 权限"
echo "   git pull                  # 测试 Git 操作"
echo ""

