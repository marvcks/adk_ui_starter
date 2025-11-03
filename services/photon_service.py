"""
光子收费服务模块
实现与玻尔平台的光子收费接口集成
"""

import asyncio
import logging
import time
import secrets
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import httpx
from fastapi import Request

logger = logging.getLogger(__name__)


@dataclass
class PhotonChargeConfig:
    """光子收费配置"""
    sku_id: int  # 应用的 SKU ID
    dev_access_key: Optional[str] = None  # 开发者 AK（用于调试）
    client_name: Optional[str] = None  # 客户端名称
    base_url: str = "https://openapi.dp.tech/openapi/v1/api/integral/consume"
    
    # 收费规则配置
    input_token_rate: float = 0.001  # 输入token费率：0.001元/千token
    output_token_rate: float = 0.03  # 输出token费率：0.03元/千token
    tool_call_cost: int = 1  # 每次工具调用费用：1光子
    min_charge: int = 1  # 最小收费光子数
    max_charge: Optional[int] = None  # 最大收费光子数（已废弃，不再使用）
    photon_to_rmb_rate: float = 0.01  # 光子到人民币的换算率 (1光子 = 0.01元)


@dataclass
class PhotonChargeRequest:
    """光子收费请求"""
    access_key: str
    biz_no: int
    event_value: int  # 扣费数额
    sku_id: int
    change_type: int = 1
    scene: str = "appCustomizeCharge"


@dataclass
class PhotonChargeResult:
    """光子收费结果"""
    success: bool
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None
    biz_no: Optional[int] = None
    photon_amount: Optional[int] = None  # 消耗的光子数量
    rmb_amount: Optional[float] = None   # 对应的人民币金额


class PhotonService:
    """光子收费服务"""
    
    def __init__(self, config: PhotonChargeConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)
        self.accumulated_cost = 0.0  # 累积的小数部分费用（以元为单位）
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def generate_biz_no(self) -> int:
        """生成唯一的业务编号"""
        timestamp = int(time.time())
        rand_part = secrets.randbits(16)
        return int(f"{timestamp}{rand_part}")
    
    def get_access_key(self, request: Optional[Request] = None, context=None) -> Optional[str]:
        """
        获取用户 AccessKey
        优先级：用户 AccessKey（从 context 或 cookie）> 开发者 AccessKey
        
        Args:
            request: HTTP 请求对象（用于获取 cookie）
            context: WebSocket 连接上下文（用于获取认证信息）
        
        Returns:
            str: AccessKey 或 None
        """
        # 优先从 WebSocket 连接上下文获取用户 AccessKey
        if context and hasattr(context, 'app_access_key') and context.app_access_key:
            logger.info("Using user AccessKey from WebSocket context")
            return context.app_access_key
        
        # 从 HTTP 请求的 cookie 中获取用户 AccessKey
        if request and request.cookies:
            access_key = request.cookies.get("appAccessKey")
            if access_key:
                logger.info("Using user AccessKey from cookie")
                return access_key
        
        # 回退到开发者 AccessKey（用于调试）
        if self.config.dev_access_key:
            logger.info("Using developer AccessKey for debugging")
            return self.config.dev_access_key
        
        logger.warning("No AccessKey available")
        return None
    
    def calculate_charge_amount(self, input_tokens: int = 0, output_tokens: int = 0, tool_calls: int = 0) -> tuple[int, float]:
        """
        根据输入输出token数量和工具调用次数计算收费金额
        
        Args:
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            tool_calls: 工具调用次数（当前不计费）
            
        Returns:
            tuple[int, float]: (光子数量, 人民币金额)
        """
        if input_tokens <= 0 and output_tokens <= 0 and tool_calls <= 0:
            return 0, 0.0
        
        # 分档费率（按输入token规模选择）
        # ≤32k：输入 0.006，输出 0.024；≤128k：输入 0.01，输出 0.04；≤256k：输入 0.015，输出 0.06
        if input_tokens <= 32_000:
            input_rate = 0.006
            output_rate = 0.024
        elif input_tokens <= 128_000:
            input_rate = 0.01
            output_rate = 0.04
        else:
            input_rate = 0.015
            output_rate = 0.06

        # 计算输入/输出token费用（元/千token）
        input_cost = (input_tokens / 1000) * input_rate
        output_cost = (output_tokens / 1000) * output_rate
        
        # 当前不对工具调用计费
        tool_cost = 0.0
        
        # 总费用（以元为单位）
        total_cost_rmb = input_cost + output_cost + tool_cost
        
        # 加上累积的小数部分
        total_cost_rmb += self.accumulated_cost
        
        # 转换为光子数量（1光子 = 0.01元）
        total_photons_float = total_cost_rmb / self.config.photon_to_rmb_rate
        
        # 取整数部分作为本次扣费
        photons_to_charge = int(total_photons_float)
        
        # 更新累积的小数部分
        self.accumulated_cost = (total_photons_float - photons_to_charge) * self.config.photon_to_rmb_rate
        
        # 应用最小和最大收费限制
        if photons_to_charge > 0:
            photons_to_charge = max(self.config.min_charge, photons_to_charge)
            photons_to_charge = min(50, photons_to_charge)
            # 不再限制最大收费，避免大请求被截断
        
        # 计算实际人民币金额
        actual_rmb_amount = photons_to_charge * self.config.photon_to_rmb_rate
        
        return photons_to_charge, actual_rmb_amount
    
    async def charge_photon(
        self, 
        input_tokens: int = 0,
        output_tokens: int = 0,
        tool_calls: int = 0,
        request: Optional[Request] = None,
        custom_amount: Optional[int] = None,
        context=None
    ) -> PhotonChargeResult:
        """
        执行光子收费
        
        Args:
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            tool_calls: 工具调用次数
            request: HTTP 请求对象（用于获取用户 AccessKey）
            custom_amount: 自定义收费金额（如果不提供则根据 token 数量计算）
            context: WebSocket 连接上下文（用于获取认证信息）
        
        Returns:
            PhotonChargeResult: 收费结果
        """
        try:
            # 获取用户 AccessKey
            access_key = self.get_access_key(request, context)
            if not access_key:
                return PhotonChargeResult(
                    success=False,
                    code=-1,
                    message="无法获取用户 AccessKey，请确保用户已登录",
                    photon_amount=0,
                    rmb_amount=0.0
                )
            
            # 计算收费金额
            if custom_amount is not None:
                charge_amount = custom_amount
                rmb_amount = custom_amount * self.config.photon_to_rmb_rate
            else:
                charge_amount, rmb_amount = self.calculate_charge_amount(input_tokens, output_tokens, tool_calls)
            
            if charge_amount <= 0:
                # 检查是否有累积费用
                if self.accumulated_cost > 0:
                    message = f"费用已累积 {self.accumulated_cost:.4f}元，待下次结算"
                    logger.info(f"Input tokens: {input_tokens}, Output tokens: {output_tokens}, Tool calls: {tool_calls} results in 0 charge, accumulated cost: {self.accumulated_cost:.4f}")
                else:
                    message = "免费使用，无需扣费"
                    logger.info(f"Input tokens: {input_tokens}, Output tokens: {output_tokens}, Tool calls: {tool_calls} results in 0 charge, no cost")
                
                return PhotonChargeResult(
                    success=True,
                    code=0,
                    message=message,
                    photon_amount=0,
                    rmb_amount=0.0
                )
            
            # 生成业务单号
            biz_no = self.generate_biz_no()
            
            # 创建收费请求
            charge_request = PhotonChargeRequest(
                access_key=access_key,
                biz_no=biz_no,
                event_value=charge_amount,
                sku_id=self.config.sku_id
            )
            
            # 发送收费请求
            result = await self._send_charge_request(charge_request)
            
            # 更新结果中的光子数量和人民币金额
            result.photon_amount = charge_amount
            result.rmb_amount = rmb_amount
            
            # 记录收费日志
            await self._log_charge_record(charge_request, result, input_tokens + output_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"光子收费异常: {e}", exc_info=True)
            return PhotonChargeResult(
                success=False,
                code=-1,
                message=f"收费服务异常: {str(e)}",
                photon_amount=0,
                rmb_amount=0.0
            )
    
    async def _send_charge_request(self, charge_request: PhotonChargeRequest) -> PhotonChargeResult:
        """发送收费请求到玻尔平台"""
        headers = {
            "accessKey": charge_request.access_key,
            "Content-Type": "application/json"
        }
        
        if self.config.client_name:
            headers["x-app-key"] = self.config.client_name
        
        payload = {
            "bizNo": charge_request.biz_no,
            "changeType": charge_request.change_type,
            "eventValue": charge_request.event_value,
            "skuId": charge_request.sku_id,
            "scene": charge_request.scene
        }
        
        try:
            response = await self.client.post(
                self.config.base_url,
                headers=headers,
                json=payload
            )
            
            response_data = response.json()
            code = response_data.get("code", -1)
            
            if code == 0:
                return PhotonChargeResult(
                    success=True,
                    code=code,
                    message="收费成功",
                    data=response_data.get("data"),
                    biz_no=charge_request.biz_no,
                    photon_amount=charge_request.event_value,
                    rmb_amount=charge_request.event_value * self.config.photon_to_rmb_rate
                )
            else:
                return PhotonChargeResult(
                    success=False,
                    code=code,
                    message=f"收费失败: {response_data.get('message', 'Unknown error')}",
                    biz_no=charge_request.biz_no,
                    photon_amount=charge_request.event_value,
                    rmb_amount=charge_request.event_value * self.config.photon_to_rmb_rate
                )
                
        except httpx.TimeoutException:
            return PhotonChargeResult(
                success=False,
                code=-1,
                message="收费请求超时",
                biz_no=charge_request.biz_no,
                photon_amount=charge_request.event_value,
                rmb_amount=charge_request.event_value * self.config.photon_to_rmb_rate
            )
        except Exception as e:
            return PhotonChargeResult(
                success=False,
                code=-1,
                message=f"收费请求失败: {str(e)}",
                biz_no=charge_request.biz_no,
                photon_amount=charge_request.event_value,
                rmb_amount=charge_request.event_value * self.config.photon_to_rmb_rate
            )
    
    async def _log_charge_record(
        self, 
        charge_request: PhotonChargeRequest, 
        result: PhotonChargeResult,
        token_count: int
    ):
        """记录收费记录（用于数据核对）"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "biz_no": charge_request.biz_no,
            "token_count": token_count,
            "charge_amount": charge_request.event_value,
            "sku_id": charge_request.sku_id,
            "success": result.success,
            "code": result.code,
            "message": result.message
        }
        
        # 这里可以扩展为写入数据库或文件
        logger.info(f"Charge record: {log_data}")


# 全局光子服务实例（需要在应用启动时初始化）
photon_service: Optional[PhotonService] = None


def init_photon_service(config: PhotonChargeConfig) -> PhotonService:
    """初始化光子服务"""
    global photon_service
    photon_service = PhotonService(config)
    return photon_service


def get_photon_service() -> Optional[PhotonService]:
    """获取光子服务实例"""
    return photon_service