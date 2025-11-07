# 快速部署指令

## 連接到 Ubuntu VM

```bash
ssh ubuntu@your-ec2-ip
```

## 切換到項目目錄

```bash
cd /var/www/Climbing_score_counter
```

## 創建虛擬環境

```bash
python3 -m venv venv
```

## 激活虛擬環境

```bash
source venv/bin/activate
```

## 拉取最新代碼

```bash
git pull origin main
```

## 執行部署腳本

```bash
bash Deployment/deploy.sh
```

