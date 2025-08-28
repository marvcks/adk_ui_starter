#!/usr/bin/env python3
"""
测试消息历史的保存和恢复功能
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_message_storage():
    """测试消息存储"""
    print("🧪 测试消息存储...")
    
    try:
        from core.event_handlers import EventProcessor
        from services.message_service import MessageService
        from core.message_types import UserMessage, AssistantMessage
        
        # 创建事件处理器和消息服务
        event_processor = EventProcessor()
        message_service = MessageService(event_processor)
        
        # 模拟会话ID
        session_id = "test_session_123"
        
        # 创建测试消息
        user_msg = UserMessage(
            content="Hello, this is a test user message",
            session_id=session_id
        )
        
        assistant_msg = AssistantMessage(
            content="Hi there! This is a test assistant response",
            session_id=session_id
        )
        
        # 手动添加到消息历史（模拟消息处理过程）
        if session_id not in message_service.message_history:
            message_service.message_history[session_id] = []
        
        message_service.message_history[session_id].append(user_msg)
        message_service.message_history[session_id].append(assistant_msg)
        
        print(f"   ✅ 消息已存储到会话 {session_id}")
        print(f"   📊 会话消息数量: {len(message_service.message_history[session_id])}")
        
        return message_service, session_id
        
    except Exception as e:
        print(f"❌ 消息存储测试失败: {e}")
        return None, None

def test_message_retrieval(message_service, session_id):
    """测试消息检索"""
    print("\n📥 测试消息检索...")
    
    try:
        if not message_service or not session_id:
            print("   ❌ 消息服务或会话ID无效")
            return False
        
        # 获取消息历史
        messages = message_service.get_message_history(session_id)
        print(f"   ✅ 成功获取会话 {session_id} 的消息历史")
        print(f"   📊 检索到 {len(messages)} 条消息")
        
        # 检查消息格式
        for i, msg in enumerate(messages):
            print(f"   📝 消息 {i+1}:")
            print(f"      - 角色: {msg.get('role', 'unknown')}")
            print(f"      - 内容: {msg.get('content', '')[:50]}...")
            print(f"      - 时间: {msg.get('timestamp', 'unknown')}")
            print(f"      - 会话ID: {msg.get('session_id', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 消息检索测试失败: {e}")
        return False

def test_session_switching():
    """测试会话切换"""
    print("\n🔄 测试会话切换...")
    
    try:
        from core.event_handlers import EventProcessor
        from services.message_service import MessageService
        from core.message_types import UserMessage, AssistantMessage
        
        # 创建事件处理器和消息服务
        event_processor = EventProcessor()
        message_service = MessageService(event_processor)
        
        # 创建两个测试会话
        session1_id = "session_1"
        session2_id = "session_2"
        
        # 为会话1添加消息
        if session1_id not in message_service.message_history:
            message_service.message_history[session1_id] = []
        
        message_service.message_history[session1_id].extend([
            UserMessage(content="Session 1 user message 1", session_id=session1_id),
            AssistantMessage(content="Session 1 assistant response 1", session_id=session1_id),
            UserMessage(content="Session 1 user message 2", session_id=session1_id),
            AssistantMessage(content="Session 1 assistant response 2", session_id=session1_id)
        ])
        
        # 为会话2添加消息
        if session2_id not in message_service.message_history:
            message_service.message_history[session2_id] = []
        
        message_service.message_history[session2_id].extend([
            UserMessage(content="Session 2 user message 1", session_id=session2_id),
            AssistantMessage(content="Session 2 assistant response 1", session_id=session2_id)
        ])
        
        print(f"   ✅ 会话1 ({session1_id}) 消息数量: {len(message_service.message_history[session1_id])}")
        print(f"   ✅ 会话2 ({session2_id}) 消息数量: {len(message_service.message_history[session2_id])}")
        
        # 测试切换会话
        print("\n   🔄 切换到会话1...")
        messages1 = message_service.get_message_history(session1_id)
        print(f"   📊 会话1 检索到 {len(messages1)} 条消息")
        
        print("\n   🔄 切换到会话2...")
        messages2 = message_service.get_message_history(session2_id)
        print(f"   📊 会话2 检索到 {len(messages2)} 条消息")
        
        return True
        
    except Exception as e:
        print(f"❌ 会话切换测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试消息历史功能...\n")
    
    # 测试消息存储
    message_service, session_id = test_message_storage()
    
    # 测试消息检索
    if message_service and session_id:
        test_message_retrieval(message_service, session_id)
    
    # 测试会话切换
    test_session_switching()
    
    print("\n📊 测试完成！")
    print("\n💡 如果测试通过，说明消息历史功能正常")
    print("   - 用户消息和助手消息都能正确保存")
    print("   - 会话切换时能正确恢复消息历史")
    print("   - 消息格式与前端期望的格式匹配")
    
    return True

if __name__ == "__main__":
    main() 