#!/usr/bin/env python3
"""
测试重构后的模块导入
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试所有模块的导入"""
    print("🧪 测试重构后的模块导入...")
    
    try:
        # 测试核心模块导入
        print("📦 测试核心模块...")
        from core.message_types import MessageType, WebSocketMessage
        print("   ✅ message_types 导入成功")
        
        from core.state_machine import SessionState, StateMachine, SessionStateManager
        print("   ✅ state_machine 导入成功")
        
        from core.event_handlers import EventProcessor, EventContext, EventType
        print("   ✅ event_handlers 导入成功")
        
        # 测试服务模块导入
        print("🔧 测试服务模块...")
        from services.message_service import MessageService
        print("   ✅ message_service 导入成功")
        
        print("\n🎉 所有模块导入成功！")
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_message_creation():
    """测试消息创建"""
    print("\n📝 测试消息创建...")
    
    try:
        from core.message_types import MessageType, UserMessage, AssistantMessage
        
        # 创建用户消息
        user_msg = UserMessage(content="Hello, world!")
        print(f"   ✅ 用户消息创建成功: {user_msg.content}")
        
        # 创建助手消息
        assistant_msg = AssistantMessage(content="Hi there!")
        print(f"   ✅ 助手消息创建成功: {assistant_msg.content}")
        
        # 测试消息序列化
        user_dict = user_msg.to_dict()
        print(f"   ✅ 消息序列化成功: {user_dict['type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 消息创建测试失败: {e}")
        return False

def test_state_machine():
    """测试状态机"""
    print("\n🔄 测试状态机...")
    
    try:
        from core.state_machine import SessionState, StateMachine
        
        # 创建状态机
        sm = StateMachine(SessionState.INITIALIZING)
        print(f"   ✅ 状态机创建成功，当前状态: {sm.current_state.value}")
        
        # 测试状态转换
        if sm.transition_to(SessionState.READY, reason="测试转换"):
            print(f"   ✅ 状态转换成功，当前状态: {sm.current_state.value}")
        else:
            print("   ❌ 状态转换失败")
            return False
        
        # 获取状态信息
        state_info = sm.get_state_info()
        print(f"   ✅ 状态信息获取成功，历史记录数: {len(state_info['state_history'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ 状态机测试失败: {e}")
        return False

def test_event_processor():
    """测试事件处理器"""
    print("\n📡 测试事件处理器...")
    
    try:
        from core.event_handlers import EventProcessor, EventType, EventContext
        from datetime import datetime
        
        # 创建事件处理器
        ep = EventProcessor()
        print("   ✅ 事件处理器创建成功")
        
        # 创建事件上下文
        context = EventContext(
            session_id="test_session",
            user_id="test_user",
            message_id="test_message",
            timestamp=datetime.now(),
            metadata={}
        )
        print("   ✅ 事件上下文创建成功")
        
        # 测试自定义事件处理器注册
        def test_handler(ctx, data):
            print(f"   📨 自定义事件处理器被调用: {data}")
        
        ep.register_custom_handler(EventType.TOOL_CALL_STARTED, test_handler)
        print("   ✅ 自定义事件处理器注册成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 事件处理器测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试重构后的模块...\n")
    
    tests = [
        test_imports,
        test_message_creation,
        test_state_machine,
        test_event_processor
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("📊 测试结果汇总:")
    print(f"   通过: {passed}/{total}")
    print(f"   失败: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！重构后的模块工作正常。")
        return True
    else:
        print("❌ 部分测试失败，请检查错误信息。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 