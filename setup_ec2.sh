#!/bin/bash
# AWS EC2 初始設置腳本
# 在 EC2 實例上首次運行此腳本來設置環境
# 使用方法：bash setup_ec2.sh

set -e

echo "========================================="
echo "AWS EC2 初始設置腳本"
echo "========================================="

# 檢查是否為 root 用戶
if [ "$EUID" -eq 0 ]; then 
   echo "請不要使用 root 用戶運行此腳本"
   exit 1
fi

# 更新系統
echo "1. 更新系統套件..."
sudo apt update
sudo apt upgrade -y

# 安裝必要套件
echo "2. 安裝必要套件..."
sudo apt install -y python3 python3-pip python3-venv nginx git curl

# 創建項目目錄
echo "3. 創建項目目錄..."
PROJECT_DIR="/var/www/Climbing_score_counter"
sudo mkdir -p $PROJECT_DIR
sudo chown -R $USER:$USER $PROJECT_DIR

# 創建日誌目錄
echo "4. 創建日誌目錄..."
mkdir -p $PROJECT_DIR/logs
mkdir -p $PROJECT_DIR/backups

# 設置權限
echo "5. 設置目錄權限..."
sudo chown -R www-data:www-data $PROJECT_DIR
sudo chmod -R 755 $PROJECT_DIR

echo "========================================="
echo "初始設置完成！"
echo "========================================="
echo ""
echo "下一步："
echo "1. 將項目文件上傳到: $PROJECT_DIR"
echo "2. 創建虛擬環境: python3 -m venv $PROJECT_DIR/venv"
echo "3. 安裝依賴: source $PROJECT_DIR/venv/bin/activate && pip install -r requirements.txt"
echo "4. 配置環境變數和服務文件"
echo "5. 運行部署腳本: bash deploy.sh"
echo ""
echo "詳細說明請參考: AWS_EC2_DEPLOYMENT.md"

