#!/usr/bin/env python3
"""
光子收费功能测试脚本
测试新的计费逻辑：输入token 0.001元/千token，输出token 0.03元/千token，工具调用 1光子/次
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.photon_service import PhotonService, PhotonChargeRequest
from config.photon_config import PHOTON_CONFIG, FREE_TOKEN_QUOTA

async def test_new_charging_logic():
    """测试新的计费逻辑"""
    print("🧪 开始测试新的光子收费逻辑...")
    print(f"📋 测试配置:")
    print(f"   - SKU ID: {PHOTON_CONFIG.sku_id}")
    print(f"   - 客户端名称: {PHOTON_CONFIG.client_name}")
    print(f"   - 输入token费率: {PHOTON_CONFIG.input_token_rate} 元/千token")
    print(f"   - 输出token费率: {PHOTON_CONFIG.output_token_rate} 元/千token")
    print(f"   - 工具调用费用: {PHOTON_CONFIG.tool_call_cost} 光子/次")
    print(f"   - 最小收费: {PHOTON_CONFIG.min_charge} 光子")
    print(f"   - 最大收费: {PHOTON_CONFIG.max_charge} 光子")
    print(f"   - 光子换算率: {PHOTON_CONFIG.photon_to_rmb_rate} 元/光子")
    print("-" * 60)
    
    # 初始化光子服务
    photon_service = PhotonService(PHOTON_CONFIG)
    
    # 测试场景 1: 少量输入输出token（应该累积小数部分）
    print("🧪 测试场景 1: 少量token使用（测试小数累积）")
    result1 = await photon_service.charge_photon(
        input_tokens=100,   # 100个输入token = 0.0001元
        output_tokens=50,   # 50个输出token = 0.0015元
        tool_calls=0        # 无工具调用
    )
    
    print(f"💬 模拟使用:")
    print(f"   - 输入token: 100 (费用: 0.0001元)")
    print(f"   - 输出token: 50 (费用: 0.0015元)")
    print(f"   - 工具调用: 0")
    print(f"   - 总费用: 0.0016元 = 0.16光子")
    
    print(f"💰 收费结果:")
    print(f"   - 成功: {result1.success}")
    print(f"   - 代码: {result1.code}")
    print(f"   - 消息: {result1.message}")
    print(f"   - 光子数量: {result1.photon_amount}")
    print(f"   - 人民币金额: {result1.rmb_amount}")
    print(f"   - 累积小数: {photon_service.accumulated_cost:.6f}元")
    print("-" * 60)
    
    # 测试场景 2: 大量输出token
    print("🧪 测试场景 2: 大量输出token")
    result2 = await photon_service.charge_photon(
        input_tokens=500,   # 500个输入token = 0.0005元
        output_tokens=2000, # 2000个输出token = 0.06元
        tool_calls=0        # 无工具调用
    )
    
    print(f"💬 模拟使用:")
    print(f"   - 输入token: 500 (费用: 0.0005元)")
    print(f"   - 输出token: 2000 (费用: 0.06元)")
    print(f"   - 工具调用: 0")
    print(f"   - 总费用: 0.0605元 + 累积 = {0.0605 + 0.0016:.6f}元")
    
    print(f"💰 收费结果:")
    print(f"   - 成功: {result2.success}")
    print(f"   - 代码: {result2.code}")
    print(f"   - 消息: {result2.message}")
    print(f"   - 光子数量: {result2.photon_amount}")
    print(f"   - 人民币金额: {result2.rmb_amount}")
    print(f"   - 累积小数: {photon_service.accumulated_cost:.6f}元")
    print("-" * 60)
    
    # 测试场景 3: 工具调用收费
    print("🧪 测试场景 3: 工具调用收费")
    result3 = await photon_service.charge_photon(
        input_tokens=200,   # 200个输入token = 0.0002元
        output_tokens=300,  # 300个输出token = 0.009元
        tool_calls=3        # 3次工具调用 = 3光子 = 0.03元
    )
    
    print(f"💬 模拟使用:")
    print(f"   - 输入token: 200 (费用: 0.0002元)")
    print(f"   - 输出token: 300 (费用: 0.009元)")
    print(f"   - 工具调用: 3次 (费用: 0.03元)")
    print(f"   - 总费用: 0.0392元 + 累积")
    
    print(f"💰 收费结果:")
    print(f"   - 成功: {result3.success}")
    print(f"   - 代码: {result3.code}")
    print(f"   - 消息: {result3.message}")
    print(f"   - 光子数量: {result3.photon_amount}")
    print(f"   - 人民币金额: {result3.rmb_amount}")
    print(f"   - 累积小数: {photon_service.accumulated_cost:.6f}元")
    print("-" * 60)
    
    # 测试场景 4: 测试累积效果
    print("🧪 测试场景 4: 再次少量使用（测试累积效果）")
    result4 = await photon_service.charge_photon(
        input_tokens=50,    # 50个输入token = 0.00005元
        output_tokens=100,  # 100个输出token = 0.003元
        tool_calls=0        # 无工具调用
    )
    
    print(f"💬 模拟使用:")
    print(f"   - 输入token: 50 (费用: 0.00005元)")
    print(f"   - 输出token: 100 (费用: 0.003元)")
    print(f"   - 工具调用: 0")
    print(f"   - 总费用: 0.00305元 + 累积")
    
    print(f"💰 收费结果:")
    print(f"   - 成功: {result4.success}")
    print(f"   - 代码: {result4.code}")
    print(f"   - 消息: {result4.message}")
    print(f"   - 光子数量: {result4.photon_amount}")
    print(f"   - 人民币金额: {result4.rmb_amount}")
    print(f"   - 累积小数: {photon_service.accumulated_cost:.6f}元")

if __name__ == "__main__":
    print("🚀 启动新的光子收费测试...")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 运行异步测试
    asyncio.run(test_new_charging_logic())
    
    print("=" * 70)
    print("✨ 测试完成")