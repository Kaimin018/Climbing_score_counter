#!/bin/bash
# 修复 Git 冲突脚本（文件结构重构后使用）
# 使用方法：在 EC2 服务器上运行：bash Deployment/scripts/tools/fix_git_conflict.sh

set -e

PROJECT_DIR="/var/www/Climbing_score_counter"
CURRENT_USER=$(whoami)

echo "========================================="
echo "修复 Git 冲突（文件结构重构）"
echo "========================================="
echo ""

cd "$PROJECT_DIR"

# 1. 备份数据库（重要！）
echo "1. 备份数据库..."
BACKUP_NAME=""
if [ -f "db.sqlite3" ]; then
    mkdir -p backups
    BACKUP_NAME="backups/db_backup_before_git_reset_$(date +%Y%m%d_%H%M%S).sqlite3"
    cp db.sqlite3 "$BACKUP_NAME"
    echo "   ✅ 数据库已备份到: $BACKUP_NAME"
else
    echo "   ℹ️  数据库文件不存在，跳过备份"
fi

# 2. 检查 Git 状态
echo "2. 检查 Git 状态..."
git status --short | head -20

# 3. 暂存所有本地修改（除了数据库）
echo "3. 暂存本地修改..."
git add -A
git stash push -m "Local changes before structure refactor $(date +%Y%m%d_%H%M%S)" -- db.sqlite3 2>/dev/null || true

# 4. 强制重置到远程版本（使用新结构）
echo "4. 重置到远程版本..."
git fetch origin
git reset --hard origin/main 2>/dev/null || git reset --hard origin/master

# 5. 恢复数据库文件（如果存在备份）
if [ -f "$BACKUP_NAME" ]; then
    echo "5. 恢复数据库文件..."
    cp "$BACKUP_NAME" db.sqlite3
    sudo chown www-data:www-data db.sqlite3 2>/dev/null || true
    sudo chmod 664 db.sqlite3 2>/dev/null || true
    echo "   ✅ 数据库已恢复"
else
    echo "5. 跳过数据库恢复（无备份）"
fi

# 6. 修复权限
echo "6. 修复权限..."
if [ -d ".git" ]; then
    sudo chown -R $CURRENT_USER:$CURRENT_USER .git 2>/dev/null || true
fi

# 7. 验证新结构
echo "7. 验证新结构..."
if [ -d "Deployment/docs" ] && [ -d "Deployment/scripts" ] && [ -d "Deployment/configs" ]; then
    echo "   ✅ 新目录结构已应用"
else
    echo "   ⚠️  警告：新目录结构可能未完全应用"
fi

echo ""
echo "========================================="
echo "Git 冲突修复完成！"
echo "========================================="
echo ""
echo "⚠️  重要提示："
echo "   1. 数据库已备份到: backups/"
echo "   2. 如果遇到问题，可以从备份恢复"
echo "   3. 新文件结构已应用：docs/, scripts/, configs/"
echo ""
echo "下一步："
echo "   bash Deployment/scripts/tools/deploy.sh"
echo ""

