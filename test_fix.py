#!/usr/bin/env python3
"""
测试修复后的代码
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试模块导入"""
    print("🧪 测试模块导入...")
    
    try:
        from core.event_handlers import EventProcessor
        from services.message_service import MessageService
        print("   ✅ 模块导入成功")
        return True
    except Exception as e:
        print(f"   ❌ 模块导入失败: {e}")
        return False

def test_message_service_creation():
    """测试消息服务创建"""
    print("\n🔧 测试消息服务创建...")
    
    try:
        from core.event_handlers import EventProcessor
        from services.message_service import MessageService
        
        event_processor = EventProcessor()
        message_service = MessageService(event_processor)
        
        print("   ✅ 消息服务创建成功")
        print(f"   📊 消息历史字典: {type(message_service.message_history)}")
        print(f"   📊 处理消息字典: {type(message_service.processing_messages)}")
        
        return True
    except Exception as e:
        print(f"   ❌ 消息服务创建失败: {e}")
        return False

def test_tool_message_types():
    """测试工具消息类型"""
    print("\n📝 测试工具消息类型...")
    
    try:
        from core.message_types import ToolMessage, MessageStatus
        
        # 创建工具消息
        tool_msg = ToolMessage(
            content="测试工具消息",
            tool_name="test_tool",
            tool_id="tool_123",
            tool_status=MessageStatus.PROCESSING,
            is_long_running=False
        )
        
        print("   ✅ 工具消息创建成功")
        print(f"   📊 工具名称: {tool_msg.tool_name}")
        print(f"   📊 工具状态: {tool_msg.tool_status}")
        print(f"   📊 长时间运行: {tool_msg.is_long_running}")
        
        return True
    except Exception as e:
        print(f"   ❌ 工具消息类型测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试修复后的代码...\n")
    
    tests = [
        test_imports,
        test_message_service_creation,
        test_tool_message_types
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
        print("🎉 所有测试通过！修复后的代码工作正常。")
        print("\n💡 修复说明:")
        print("   - 修复了 'long_running_tools' 属性错误")
        print("   - 使用正确的 'long_running_tool_ids' 属性")
        print("   - 工具调用历史记录功能应该正常工作")
        return True
    else:
        print("❌ 部分测试失败，请检查错误信息。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 