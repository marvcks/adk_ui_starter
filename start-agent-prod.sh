#!/bin/bash

echo "🚀 启动 Agent 系统（生产环境）..."

# 清理现有进程
echo "清理现有进程..."
pkill -f "websocket-server-refactored.py" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 1

# 创建输出目录
mkdir -p output

# 获取配置信息
CONFIG_FILE="config/agent-config.json"
if [ -f "$CONFIG_FILE" ]; then
    FRONTEND_PORT=$(python -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('server',{}).get('port',50002))" 2>/dev/null || echo "50002")
    WEBSOCKET_PORT=$(python -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('websocket',{}).get('port',8000))" 2>/dev/null || echo "8000")
    ALLOWED_HOSTS=$(python -c "import json; c=json.load(open('$CONFIG_FILE')); hosts=c.get('server',{}).get('allowedHosts',[]); print(', '.join(hosts) if hosts else 'None')" 2>/dev/null || echo "None")
else
    FRONTEND_PORT="50002"
    WEBSOCKET_PORT="8000"
    ALLOWED_HOSTS="None"
fi

# 构建前端生产版本
echo "构建前端生产版本..."
cd ui
npm run build
if [ $? -ne 0 ]; then
    echo "❌ 前端构建失败！"
    exit 1
fi
echo "✅ 前端构建完成"

# 启动 WebSocket 服务器（集成了 Agent）
echo "启动 Agent WebSocket 服务器..."
cd ..
python websocket-server-refactored.py > websocket.log 2>&1 &
WEBSOCKET_PID=$!

# 启动前端预览服务器（生产构建）
echo "启动前端预览服务器..."
cd ui
npm run preview > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# 等待服务启动
sleep 2

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                ✅ Agent 系统已成功启动（生产模式）！              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "📡 服务状态："
echo "├─ WebSocket 服务器: http://localhost:$WEBSOCKET_PORT (PID: $WEBSOCKET_PID)"
echo "└─ 前端预览服务器:  http://localhost:$FRONTEND_PORT (PID: $FRONTEND_PID)"
echo ""
echo "🌐 访问地址："
echo "├─ 本地访问: http://localhost:$FRONTEND_PORT"
if [ "$ALLOWED_HOSTS" != "None" ]; then
    echo "└─ 额外允许的主机: $ALLOWED_HOSTS"
fi
echo ""
echo "📁 日志文件："
echo "├─ 服务器日志: ./websocket.log"
echo "└─ 前端日志:   ./frontend.log"
echo ""
echo "💡 生产环境提示："
echo "• 前端已构建为生产版本，性能更优"
echo "• 使用 npm run preview 提供静态文件服务"
echo "• 建议在生产环境中使用 Nginx 等 Web 服务器"
echo "• 使用 tail -f websocket.log 查看服务器日志"
echo "• 按 Ctrl+C 停止所有服务"
echo ""

# 捕获 Ctrl+C
trap "echo '停止所有服务...'; kill $WEBSOCKET_PID $FRONTEND_PID 2>/dev/null; exit" INT

# 保持脚本运行
wait 