# Agent UI

一个优雅的UI界面，用于替代 Google ADK 的 web 界面，为 Agent- 提供美观的用户界面。

## 功能特性

- 🎨 **Apple 风格设计** - 简约美观的界面设计
- 📊 **实时任务监控** - 查看和管理符号回归任务
- 📄 **文件查看器** - 支持 Markdown 和 JSON 文件的优雅展示
- 🔄 **实时更新** - 通过 WebSocket 实现实时数据同步
- ⚙️ **系统设置** - 配置 AI 模型、符号回归参数等

## 快速开始

### 前端启动

```bash
cd -ui
npm install
npm run dev
```


## 技术栈

### 前端
- React 18 + TypeScript
- Vite - 快速的开发构建工具
- Tailwind CSS - 实用优先的 CSS 框架
- Framer Motion - 流畅的动画效果
- React Markdown - Markdown 渲染
- Lucide React - 优雅的图标库

### 后端
- FastAPI - 现代化的 Python Web 框架
- WebSocket - 实时通信
- Watchdog - 文件监控

## 项目结构

```
-ui/
├──c/
│   ├── components/      # 可复用组件
│   ├── pages/          # 页面组件
│   ├── api/            # API 客户端
│   ├── hooks/          # React Hooks
│   └── styles/         # 样式文件
├── public/             # 静态资源
└── ...

```

## 主要页面

1. **Dashboard** - 系统概览和快速操作
2. **Tasks** - 任务管理和监控
3. **Files** - 文件浏览和查看
4. **Settings** - 系统配置

## API 端点

- `GET /api/files/{path}` - 获取文件内容
- `GET /api/tasks` - 获取所有任务
- `POST /api/tasks` - 创建新任务
- `GET /api/stats` - 获取系统统计
- `WS /ws` - WebSocket 连接

## 开发说明

### 添加新组件

1. 在 `c/components` 创建组件文件
2. 使用 Apple 风格的设计规范
3. 利用 Tailwind CSS 类名

### 自定义主题

修改 `tailwind.config.js` 中的颜色配置：

```javascript
colors: {
  'apple-blue': '#0071e3',
  'apple-green': '#34c759',
  // ...
}
```