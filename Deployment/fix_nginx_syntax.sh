#!/bin/bash
# Nginx 配置语法检查和修复辅助脚本

echo "=========================================="
echo "Nginx 配置语法检查"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CONFIG_FILE="/etc/nginx/sites-available/climbing_system.conf"

# 1. 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}✗${NC} 配置文件不存在: $CONFIG_FILE"
    exit 1
fi

echo -e "${GREEN}✓${NC} 配置文件存在: $CONFIG_FILE"
echo ""

# 2. 显示第 91 行附近的内容
echo "第 91 行附近的内容（前后 10 行）："
echo "----------------------------------------"
sed -n '81,101p' "$CONFIG_FILE" | cat -n
echo ""

# 3. 检查常见的语法错误
echo "检查常见语法错误..."
echo ""

# 检查是否有未关闭的大括号
OPEN_BRACES=$(grep -o '{' "$CONFIG_FILE" | wc -l)
CLOSE_BRACES=$(grep -o '}' "$CONFIG_FILE" | wc -l)

if [ "$OPEN_BRACES" -ne "$CLOSE_BRACES" ]; then
    echo -e "${RED}✗${NC} 大括号不匹配！"
    echo "   开括号: $OPEN_BRACES"
    echo "   闭括号: $CLOSE_BRACES"
    echo ""
else
    echo -e "${GREEN}✓${NC} 大括号匹配"
fi

# 检查是否有 "HTTP" 作为指令（应该是注释）
if grep -n "^[^#]*HTTP" "$CONFIG_FILE" | grep -v "#.*HTTP"; then
    echo -e "${RED}✗${NC} 发现可能的错误：'HTTP' 作为指令（应该是注释）"
    echo "   问题行："
    grep -n "^[^#]*HTTP" "$CONFIG_FILE" | grep -v "#.*HTTP"
    echo ""
fi

# 4. 尝试测试配置
echo "尝试测试 Nginx 配置..."
echo "----------------------------------------"
sudo nginx -t 2>&1
echo ""

# 5. 提供修复建议
echo "=========================================="
echo "修复建议"
echo "=========================================="
echo ""
echo "如果看到 'unknown directive \"HTTP\"' 错误，可能的原因："
echo ""
echo "1. 注释格式错误："
echo "   ❌ 错误: HTTP 重定向到 HTTPS"
echo "   ✅ 正确: # HTTP 重定向到 HTTPS"
echo ""
echo "2. 配置块未正确关闭："
echo "   检查每个 server { ... } 块是否都有对应的 }"
echo ""
echo "3. 指令拼写错误："
echo "   确保所有指令都是有效的 Nginx 指令"
echo ""
echo "修复步骤："
echo "1. 编辑配置文件："
echo "   sudo nano $CONFIG_FILE"
echo ""
echo "2. 检查第 91 行附近的内容"
echo "3. 确保所有注释都以 # 开头"
echo "4. 确保所有 server 块都正确关闭"
echo "5. 测试配置：sudo nginx -t"
echo ""

