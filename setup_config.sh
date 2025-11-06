#!/bin/bash
# 服務器配置初始化腳本
# 使用方法：bash setup_config.sh
# 此腳本用於首次部署時創建服務器配置文件

set -e

PROJECT_DIR="/var/www/Climbing_score_counter"
CONFIG_FILE="$PROJECT_DIR/.server-config"

echo "=== 服務器配置初始化 ==="

# 檢查項目目錄
if [ ! -d "$PROJECT_DIR" ]; then
    echo "錯誤: 項目目錄不存在: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1

# 檢查配置文件是否已存在
if [ -f "$CONFIG_FILE" ]; then
    echo "⚠️  配置文件已存在: $CONFIG_FILE"
    read -p "是否要覆蓋現有配置？(y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "取消操作"
        exit 0
    fi
fi

# 讀取配置
echo ""
echo "請輸入以下配置信息："
echo ""

read -p "域名 (例如: countclimbingscore.online): " DOMAIN
read -p "WWW 域名 (留空使用 www.$DOMAIN): " WWW_DOMAIN
read -p "EC2 IP 地址: " EC2_IP
read -sp "SECRET_KEY (留空將自動生成): " SECRET_KEY
echo ""

# 設置默認值
WWW_DOMAIN=${WWW_DOMAIN:-www.$DOMAIN}

# 如果沒有提供 SECRET_KEY，自動生成
if [ -z "$SECRET_KEY" ]; then
    echo "正在生成 SECRET_KEY..."
    if command -v python3 &> /dev/null; then
        SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
        echo "✅ SECRET_KEY 已自動生成"
    else
        echo "錯誤: 無法生成 SECRET_KEY，請手動提供"
        exit 1
    fi
fi

# 創建配置文件
cat > "$CONFIG_FILE" << EOF
# 服務器配置（不提交到 Git）
# 此文件由 setup_config.sh 創建
# 修改此文件後，運行 deploy.sh 會自動應用配置

DOMAIN=$DOMAIN
WWW_DOMAIN=$WWW_DOMAIN
EC2_IP=$EC2_IP
SECRET_KEY=$SECRET_KEY
EOF

# 設置文件權限
chmod 600 "$CONFIG_FILE"
echo "✅ 配置文件已創建: $CONFIG_FILE"
echo ""

# 顯示配置摘要（隱藏 SECRET_KEY）
echo "=== 配置摘要 ==="
echo "域名: $DOMAIN"
echo "WWW 域名: $WWW_DOMAIN"
echo "EC2 IP: $EC2_IP"
echo "SECRET_KEY: [已設置]"
echo ""

echo "✅ 配置完成！"
echo ""
echo "下一步："
echo "1. 檢查配置文件: cat $CONFIG_FILE"
echo "2. 運行部署腳本: bash deploy.sh"
echo "   部署腳本會自動讀取此配置並應用到 systemd 和 nginx"

