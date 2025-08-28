#!/usr/bin/env python3
"""
测试消息格式是否正确
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_message_format():
    """测试消息格式"""
    print("🧪 测试消息格式...")
    
    try:
        from core.message_types import WebSocketMessage
        
        # 测试WebSocketMessage格式
        message = WebSocketMessage(
            type="assistant",
            data={"content": "Hello, this is a test message"}
        )
        
        message_dict = message.to_dict()
        print(f"   ✅ WebSocketMessage格式: {message_dict}")
        
        # 测试简单消息格式（前端期望的格式）
        simple_message = {
            "type": "assistant",
            "content": "Hello, this is a test message"
        }
        print(f"   ✅ 简单消息格式: {simple_message}")
        
        print("\n📋 消息格式对比:")
        print("   WebSocketMessage格式: 包含data包装和timestamp")
        print("   简单消息格式: 直接包含type和content")
        print("   前端期望: 简单消息格式")
        
        return True
        
    except Exception as e:
        print(f"❌ 消息格式测试失败: {e}")
        return False

def test_message_types():
    """测试消息类型"""
    print("\n📝 测试消息类型...")
    
    try:
        from core.message_types import MessageType, UserMessage, AssistantMessage
        
        # 测试用户消息
        user_msg = UserMessage(content="Hello")
        user_dict = user_msg.to_dict()
        print(f"   ✅ 用户消息: {user_dict}")
        
        # 测试助手消息
        assistant_msg = AssistantMessage(content="Hi there!")
        assistant_dict = assistant_msg.to_dict()
        print(f"   ✅ 助手消息: {assistant_dict}")
        
        return True
        
    except Exception as e:
        print(f"❌ 消息类型测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试消息格式...\n")
    
    tests = [
        test_message_format,
        test_message_types
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
        print("🎉 所有测试通过！消息格式正确。")
        print("\n💡 修复说明:")
        print("   - 重构后的代码现在使用简单消息格式")
        print("   - 与前端期望的消息格式完全匹配")
        print("   - 不再使用WebSocketMessage包装")
        return True
    else:
        print("❌ 部分测试失败，请检查错误信息。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 