#!/bin/bash

echo "=========================================="
echo "🔍 验证导入修复"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd "$(dirname "$0")"

echo "📂 检查项目目录..."
if [ -d "ai-assistant/backend/app" ]; then
    echo -e "${GREEN}✅ 项目目录存在${NC}"
else
    echo -e "${RED}❌ 项目目录不存在${NC}"
    exit 1
fi

echo ""
echo "🔎 检查相对导入..."

cd ai-assistant/backend/app

# 检查 from .. 导入
DOUBLE_DOT=$(grep -r "from \.\." . --include="*.py" 2>/dev/null | wc -l)
if [ "$DOUBLE_DOT" -eq 0 ]; then
    echo -e "${GREEN}✅ 没有发现 'from ..' 相对导入${NC}"
else
    echo -e "${RED}❌ 发现 $DOUBLE_DOT 个 'from ..' 相对导入${NC}"
    grep -r "from \.\." . --include="*.py"
    exit 1
fi

# 检查 from . 导入（排除 from dotenv）
SINGLE_DOT=$(grep -r "^from \." . --include="*.py" 2>/dev/null | grep -v "from dotenv" | wc -l)
if [ "$SINGLE_DOT" -eq 0 ]; then
    echo -e "${GREEN}✅ 没有发现 'from .' 相对导入${NC}"
else
    echo -e "${RED}❌ 发现 $SINGLE_DOT 个 'from .' 相对导入${NC}"
    grep -r "^from \." . --include="*.py" | grep -v "from dotenv"
    exit 1
fi

echo ""
echo "📋 检查关键文件的导入..."

# 检查每个关键文件
declare -a files=(
    "agents/base_agent.py"
    "agents/agent_manager.py"
    "agents/chat_agent.py"
    "agents/chatbi_agent.py"
    "services/conversation_service.py"
    "services/database_service.py"
    "api/chat.py"
    "api/system.py"
    "api/database.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        if grep -q "^from \." "$file" 2>/dev/null && ! grep -q "from dotenv" "$file" 2>/dev/null; then
            echo -e "${RED}❌ $file 包含相对导入${NC}"
            exit 1
        else
            echo -e "${GREEN}✅ $file${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  $file 不存在${NC}"
    fi
done

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 所有导入检查通过！${NC}"
echo "=========================================="
echo ""
echo "📝 下一步："
echo "1. 启动后端: cd ai-assistant/backend && python app/main.py"
echo "2. 启动前端: cd ai-assistant/frontend && npm run dev"
echo ""
