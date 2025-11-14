"""
光子收费配置文件
"""

import os
from services.photon_service import PhotonChargeConfig
from dotenv import load_dotenv
load_dotenv()



# 从环境变量或配置文件中读取配置
PHOTON_CONFIG = PhotonChargeConfig(
    # 应用的 SKU ID（需要从玻尔平台获取）
    sku_id=int(os.getenv("PHOTON_SKU_ID", "12345")),  # 请替换为实际的 SKU ID
    
    # 开发者 AccessKey（用于调试，生产环境应该使用用户的 AccessKey）
    dev_access_key=os.getenv("PHOTON_DEV_ACCESS_KEY"),  # 可选，用于调试
    
    # 客户端名称
    client_name=os.getenv("PHOTON_CLIENT_NAME", "adk_ui_starter"),
    
    # 收费规则配置
    min_charge=int(os.getenv("PHOTON_MIN_CHARGE", "1")),  # 最小收费光子数
)

# 收费开关配置
CHARGING_ENABLED = os.getenv("CHARGING_ENABLED", "false").lower() == "true"

# 免费额度配置（每日免费 token 数量）
FREE_TOKEN_QUOTA = int(os.getenv("FREE_TOKEN_QUOTA", "1000"))

# 收费提示配置
CHARGE_NOTIFICATION_CONFIG = {
    "show_before_request": True,  # 是否在请求前显示收费提示
    "show_after_request": True,   # 是否在请求后显示收费结果
    "threshold_for_warning": 100,  # 超过多少 token 时显示警告
}