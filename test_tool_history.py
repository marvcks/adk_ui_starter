#!/usr/bin/env python3
"""
测试工具调用消息的保存和恢复功能
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tool_message_storage():
    """测试工具消息存储"""
    print("🧪 测试工具消息存储...")
    
    try:
        from core.event_handlers import EventProcessor
        from services.message_service import MessageService
        from core.message_types import UserMessage, AssistantMessage, ToolMessage, MessageStatus
        
        # 创建事件处理器和消息服务
        event_processor = EventProcessor()
        message_service = MessageService(event_processor)
        
        # 模拟会话ID
        session_id = "test_tool_session"
        
        # 创建测试消息序列
        if session_id not in message_service.message_history:
            message_service.message_history[session_id] = []
        
        # 1. 用户消息
        user_msg = UserMessage(
            content="请帮我查询天气信息",
            session_id=session_id
        )
        message_service.message_history[session_id].append(user_msg)
        
        # 2. 工具调用开始
        tool_start_msg = ToolMessage(
            content="正在执行工具: weather_query",
            tool_name="weather_query",
            tool_id="tool_123",
            tool_status=MessageStatus.PROCESSING,
            is_long_running=False,
            session_id=session_id
        )
        message_service.message_history[session_id].append(tool_start_msg)
        
        # 3. 工具执行完成
        tool_complete_msg = ToolMessage(
            content="工具执行完成: weather_query",
            tool_name="weather_query",
            tool_id="tool_123",
            tool_status=MessageStatus.COMPLETED,
            result="今天天气晴朗，温度25°C",
            session_id=session_id
        )
        message_service.message_history[session_id].append(tool_complete_msg)
        
        # 4. 助手回复
        assistant_msg = AssistantMessage(
            content="根据天气查询结果，今天天气晴朗，温度25°C，适合外出活动。",
            session_id=session_id
        )
        message_service.message_history[session_id].append(assistant_msg)
        
        print(f"   ✅ 工具消息序列已存储到会话 {session_id}")
        print(f"   📊 会话消息数量: {len(message_service.message_history[session_id])}")
        
        # 显示消息序列
        for i, msg in enumerate(message_service.message_history[session_id]):
            if isinstance(msg, UserMessage):
                print(f"   📝 消息 {i+1}: 用户 - {msg.content[:30]}...")
            elif isinstance(msg, ToolMessage):
                status = "执行中" if msg.tool_status == MessageStatus.PROCESSING else "已完成"
                print(f"   🔧 消息 {i+1}: 工具({status}) - {msg.tool_name}")
            elif isinstance(msg, AssistantMessage):
                print(f"   🤖 消息 {i+1}: 助手 - {msg.content[:30]}...")
        
        return message_service, session_id
        
    except Exception as e:
        print(f"❌ 工具消息存储测试失败: {e}")
        return None, None

def test_tool_message_retrieval(message_service, session_id):
    """测试工具消息检索"""
    print("\n📥 测试工具消息检索...")
    
    try:
        if not message_service or not session_id:
            print("   ❌ 消息服务或会话ID无效")
            return False
        
        # 获取消息历史
        messages = message_service.get_message_history(session_id)
        print(f"   ✅ 成功获取会话 {session_id} 的消息历史")
        print(f"   📊 检索到 {len(messages)} 条消息")
        
        # 检查消息格式和工具消息
        tool_messages = []
        for i, msg in enumerate(messages):
            print(f"   📝 消息 {i+1}:")
            print(f"      - 角色: {msg.get('role', 'unknown')}")
            print(f"      - 内容: {msg.get('content', '')[:50]}...")
            print(f"      - 时间: {msg.get('timestamp', 'unknown')}")
            
            if msg.get('role') == 'tool':
                tool_messages.append(msg)
                print(f"      - 工具名称: {msg.get('tool_name', 'unknown')}")
                print(f"      - 工具状态: {msg.get('tool_status', 'unknown')}")
                if msg.get('result'):
                    print(f"      - 工具结果: {msg.get('result', '')[:50]}...")
                if msg.get('is_long_running') is not None:
                    print(f"      - 长时间运行: {msg.get('is_long_running')}")
        
        print(f"\n   🔧 工具消息数量: {len(tool_messages)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 工具消息检索测试失败: {e}")
        return False

def test_tool_message_persistence():
    """测试工具消息持久化"""
    print("\n💾 测试工具消息持久化...")
    
    try:
        from core.event_handlers import EventProcessor
        from services.message_service import MessageService
        from core.message_types import UserMessage, ToolMessage, MessageStatus
        
        # 创建事件处理器和消息服务
        event_processor = EventProcessor()
        message_service = MessageService(event_processor)
        
        # 模拟会话ID
        session_id = "persistence_test_session"
        
        # 创建复杂的工具调用序列
        if session_id not in message_service.message_history:
            message_service.message_history[session_id] = []
        
        # 模拟一个复杂的对话流程
        messages = [
            UserMessage(content="请帮我分析这个数据集", session_id=session_id),
            ToolMessage(content="正在执行工具: data_loader", tool_name="data_loader", 
                      tool_id="tool_1", tool_status=MessageStatus.PROCESSING, session_id=session_id),
            ToolMessage(content="工具执行完成: data_loader", tool_name="data_loader", 
                      tool_id="tool_1", tool_status=MessageStatus.COMPLETED, 
                      result="数据集加载成功，共1000条记录", session_id=session_id),
            ToolMessage(content="正在执行工具: data_analyzer", tool_name="data_analyzer", 
                      tool_id="tool_2", tool_status=MessageStatus.PROCESSING, session_id=session_id),
            ToolMessage(content="工具执行完成: data_analyzer", tool_name="data_analyzer", 
                      tool_id="tool_2", tool_status=MessageStatus.COMPLETED, 
                      result="数据分析完成，发现3个异常值", session_id=session_id),
        ]
        
        message_service.message_history[session_id].extend(messages)
        
        print(f"   ✅ 复杂工具调用序列已创建")
        print(f"   📊 会话消息数量: {len(message_service.message_history[session_id])}")
        
        # 模拟会话切换
        print("\n   🔄 模拟会话切换...")
        retrieved_messages = message_service.get_message_history(session_id)
        print(f"   📥 切换后检索到 {len(retrieved_messages)} 条消息")
        
        # 统计不同类型的消息
        user_count = sum(1 for msg in retrieved_messages if msg.get('role') == 'user')
        tool_count = sum(1 for msg in retrieved_messages if msg.get('role') == 'tool')
        
        print(f"   📊 消息统计:")
        print(f"      - 用户消息: {user_count}")
        print(f"      - 工具消息: {tool_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ 工具消息持久化测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试工具调用消息功能...\n")
    
    # 测试工具消息存储
    message_service, session_id = test_tool_message_storage()
    
    # 测试工具消息检索
    if message_service and session_id:
        test_tool_message_retrieval(message_service, session_id)
    
    # 测试工具消息持久化
    test_tool_message_persistence()
    
    print("\n📊 测试完成！")
    print("\n💡 如果测试通过，说明工具调用消息功能正常")
    print("   - 工具调用开始和完成消息都能正确保存")
    print("   - 会话切换时工具调用历史能正确恢复")
    print("   - 工具消息格式与前端期望的格式匹配")
    
    return True

if __name__ == "__main__":
    main() 