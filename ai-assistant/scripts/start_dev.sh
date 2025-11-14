#!/bin/bash

echo "================================"
echo "🚀 启动AI助手开发环境"
echo "================================"

# 检查是否在项目根目录
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

# 启动后端
echo ""
echo "📦 启动后端服务..."
cd backend
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到.env文件，请复制.env.example并配置"
    cp .env.example .env
    echo "请编辑 backend/.env 文件，设置 DASHSCOPE_API_KEY"
    exit 1
fi

python app/main.py &
BACKEND_PID=$!
cd ..

# 等待后端启动
echo "等待后端启动..."
sleep 3

# 启动前端
echo ""
echo "🎨 启动前端服务..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "================================"
echo "✅ 服务启动成功！"
echo "================================"
echo ""
echo "📝 访问地址："
echo "  前端: http://localhost:3000"
echo "  后端: http://localhost:8000"
echo "  API文档: http://localhost:8000/api/docs"
echo ""
echo "⏹️  按 Ctrl+C 停止所有服务"
echo "================================"

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait