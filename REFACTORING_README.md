# WebSocket 服务器重构说明

## 重构概述

本次重构将原有的单体 `websocket-server.py` 重构为模块化架构，主要解决了以下问题：

1. **代码可维护性差**：`process_message` 函数过于复杂（超过100行）
2. **职责分离不清**：业务逻辑和通信逻辑混合在一起
3. **缺乏标准化**：消息类型和事件处理缺乏统一标准
4. **状态管理混乱**：会话状态、连接状态混合管理

## 新架构特点

### 1. 模块化设计

```
websocket-server/
├── core/                          # 核心模块
│   ├── message_types.py          # 消息类型定义
│   ├── event_handlers.py         # 事件处理器
│   └── state_machine.py          # 状态机管理
├── services/                      # 服务层
│   ├── message_service.py        # 消息处理服务
│   ├── tool_service.py           # 工具执行服务（待实现）
│   ├── session_service.py        # 会话管理服务（待实现）
│   └── websocket_service.py      # WebSocket通信服务（待实现）
├── websocket-server-refactored.py # 重构后的主服务器
└── start-refactored-server.sh     # 启动脚本
```

### 2. 核心组件

#### 消息类型系统 (`core/message_types.py`)
- 定义了完整的消息类型枚举
- 实现了标准化的消息模型
- 支持消息验证和序列化

#### 状态机管理 (`core/state_machine.py`)
- 实现了会话状态机
- 支持状态转换和验证
- 提供状态历史记录

#### 事件处理器 (`core/event_handlers.py`)
- 标准化的事件处理机制
- 支持工具事件和消息事件
- 可扩展的自定义事件处理

#### 消息服务 (`services/message_service.py`)
- 将消息处理逻辑从主服务器中分离
- 实现了与Google ADK的集成
- 支持工具调用和响应处理

### 3. 主要改进

#### 代码结构优化
- **原有问题**：`process_message` 函数超过100行，包含太多职责
- **解决方案**：拆分为多个小函数，每个函数负责单一职责
- **收益**：代码可读性提升，便于维护和测试

#### 状态管理优化
- **原有问题**：会话状态、连接状态、工具状态混合管理
- **解决方案**：引入状态机，清晰管理状态转换
- **收益**：状态管理更加清晰，支持状态回放和恢复

#### 事件处理标准化
- **原有问题**：事件处理逻辑混乱，缺乏统一标准
- **解决方案**：实现标准化的事件处理器
- **收益**：事件处理更加规范，支持事件缓冲和批量处理

#### 服务层抽象
- **原有问题**：业务逻辑和通信逻辑混合
- **解决方案**：引入服务层，分离业务逻辑
- **收益**：架构更加清晰，便于扩展和测试

## 使用方法

### 1. 启动重构后的服务器

```bash
# 方法1：使用启动脚本
chmod +x start-refactored-server.sh
./start-refactored-server.sh

# 方法2：直接启动
python3 websocket-server-refactored.py
```

### 2. 前端连接

前端代码无需修改，WebSocket连接地址保持不变：
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### 3. 消息格式

重构后的服务器保持了与原有前端的兼容性，消息格式基本不变，但内部处理更加标准化。

## 性能优化

### 1. 事件流处理
- 实现了事件缓冲机制
- 支持批量事件处理
- 减少了不必要的网络传输

### 2. 状态缓存
- 会话状态缓存
- 工具执行结果缓存
- 减少了重复计算

### 3. 异步处理
- 工具执行异步化
- 消息处理非阻塞
- 提升了并发处理能力

## 扩展性

### 1. 添加新的消息类型
```python
# 在 core/message_types.py 中添加
class NewMessageType(MessageType):
    NEW_TYPE = "new_type"

# 在相应的服务中处理
```

### 2. 添加新的事件处理器
```python
# 在 core/event_handlers.py 中添加
class NewEventProcessor:
    async def process_new_event(self, context, data):
        # 处理逻辑
        pass

# 注册到 EventProcessor
```

### 3. 添加新的服务
```python
# 创建新的服务文件
class NewService:
    def __init__(self):
        pass
    
    async def process(self, data):
        # 业务逻辑
        pass
```

## 测试建议

### 1. 功能测试
- 测试消息发送和接收
- 测试会话创建和切换
- 测试工具执行流程
- 测试错误处理机制

### 2. 性能测试
- 测试并发连接数
- 测试消息处理延迟
- 测试内存使用情况
- 测试长时间运行稳定性

### 3. 兼容性测试
- 测试与现有前端的兼容性
- 测试消息格式的向后兼容
- 测试API接口的兼容性

## 后续计划

### 第一阶段（已完成）
- ✅ 创建基础架构
- ✅ 实现消息类型系统
- ✅ 重构消息处理逻辑

### 第二阶段（进行中）
- 🔄 完善工具服务
- 🔄 实现会话管理服务
- 🔄 优化WebSocket通信服务

### 第三阶段（计划中）
- 📋 实现高级功能
- 📋 性能优化
- 📋 监控和日志系统

## 总结

本次重构显著提升了代码的可维护性、可扩展性和性能。通过模块化设计和标准化的事件处理，为后续功能扩展奠定了坚实的基础。重构后的架构更加清晰，代码质量更高，维护成本更低。 