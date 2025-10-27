#!/u/bin/env python3
"""
Agent WebSocket 服务器
使用 Session 运行 rootagent，并通过 WebSocket 与前端通信
"""

import os

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from dataclasses import dataclass, field, asdict
import uuid
import subprocess
import shlex

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import tempfile
import shutil

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import configuration
from config.agent_config import agentconfig

# Import photon charging service
from services.photon_service import PhotonService, init_photon_service, get_photon_service
from config.photon_config import PHOTON_CONFIG, CHARGING_ENABLED, FREE_TOKEN_QUOTA

# Get agent from configuration
rootagent = agentconfig.get_agent()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化光子收费服务
if CHARGING_ENABLED:
    init_photon_service(PHOTON_CONFIG)
    logger.info("光子收费服务已启用")
else:
    logger.info("光子收费服务已禁用")

@dataclass
class Message:
    id: str
    role: str  # 'user' or 'assistant' or 'tool'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_name: Optional[str] = None
    tool_status: Optional[str] = None

@dataclass 
class Session:
    id: str
    title: str = "新对话"
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_message_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str, tool_name: Optional[str] = None, tool_status: Optional[str] = None):
        """添加消息到会话"""
        message = Message(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            tool_name=tool_name,
            tool_status=tool_status
        )
        self.messages.append(message)
        self.last_message_at = datetime.now()
        
        if self.title == "新对话" and role == "user" and len(self.messages) <= 2:
            self.title = content[:30] + "..." if len(content) > 30 else content
        
        return message

app = FastAPI(title="Agent WebSocket Server")

# 获取服务器配置
server_config = agentconfig.get_server_config()
allowed_hosts = server_config.get("allowedHosts", ["localhost", "127.0.0.1", "0.0.0.0"])

# 构建允许的 CORS origins
allowed_origins = []
for host in allowed_hosts:
    allowed_origins.extend([
        f"http://{host}:*",
        f"https://{host}:*",
        f"http://{host}",
        f"https://{host}"
    ])

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Host 验证中间件
class HostValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        if host and host not in allowed_hosts:
            return PlainTextResponse(
                content=f"Host '{host}' is not allowed",
                status_code=403
            )
        response = await call_next(request)
        return response

app.add_middleware(HostValidationMiddleware)

class ConnectionContext:
    """每个WebSocket连接的独立上下文"""
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.sessions: Dict[str, Session] = {}
        self.runners: Dict[str, Runner] = {}
        self.session_services: Dict[str, InMemorySessionService] = {}
        self.current_session_id: Optional[str] = None
        self.shell_state: Dict[str, any] = {
            "cwd": os.getcwd(),
            "env": os.environ.copy()
        }
        # 为每个连接生成唯一的user_id
        self.user_id = f"user_{uuid.uuid4().hex[:8]}"
        # 用户认证信息
        self.app_access_key: Optional[str] = None
        self.client_name: Optional[str] = None
        self.is_authenticated: bool = False

class SessionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, ConnectionContext] = {}
        # Use configuration values
        self.app_name = agentconfig.config.get("agent", {}).get("name", "Agent")
        
    async def create_session(self, context: ConnectionContext) -> Session:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        session = Session(id=session_id)
        
        # 先将会话添加到连接的会话列表
        context.sessions[session_id] = session
        logger.info(f"为用户 {context.user_id} 创建新会话: {session_id}")
        
        # 异步创建 session service 和 runner，避免阻塞
        task = asyncio.create_task(self._init_session_runner(context, session_id))
        
        # 添加错误处理回调
        def handle_init_error(future):
            try:
                future.result()
            except Exception as e:
                logger.error(f"初始化会话Runner时发生未处理的错误: {e}", exc_info=True)
        
        task.add_done_callback(handle_init_error)
        
        return session
    
    async def _init_session_runner(self, context: ConnectionContext, session_id: str):
        """异步初始化会话的runner"""
        try:
            session_service = InMemorySessionService()
            await session_service.create_session(
                app_name=self.app_name,
                user_id=context.user_id,
                session_id=session_id
            )
            
            runner = Runner(
                agent=rootagent,
                session_service=session_service,
                app_name=self.app_name
            )
            
            context.session_services[session_id] = session_service
            context.runners[session_id] = runner
            
            logger.info(f"Runner 初始化完成: {session_id}")
            
        except Exception as e:
            logger.error(f"初始化Runner失败: {e}")
            # 清理失败的会话
            if session_id in context.sessions:
                del context.sessions[session_id]
            if session_id in context.session_services:
                del context.session_services[session_id]
            if session_id in context.runners:
                del context.runners[session_id]
    
    def get_session(self, context: ConnectionContext, session_id: str) -> Optional[Session]:
        """获取会话"""
        return context.sessions.get(session_id)
    
    def get_all_sessions(self, context: ConnectionContext) -> List[Session]:
        """获取连接的所有会话列表"""
        return list(context.sessions.values())
    
    def delete_session(self, context: ConnectionContext, session_id: str) -> bool:
        """删除会话"""
        if session_id in context.sessions:
            del context.sessions[session_id]
            if session_id in context.runners:
                del context.runners[session_id]
            if session_id in context.session_services:
                del context.session_services[session_id]
            logger.info(f"用户 {context.user_id} 删除会话: {session_id}")
            return True
        return False
    
    async def switch_session(self, context: ConnectionContext, session_id: str) -> bool:
        """切换当前会话"""
        if session_id in context.sessions:
            context.current_session_id = session_id
            logger.info(f"用户 {context.user_id} 切换到会话: {session_id}")
            return True
        return False
    
    async def connect_client(self, websocket: WebSocket):
        """连接新客户端"""
        await websocket.accept()
        
        # 为新连接创建独立的上下文
        context = ConnectionContext(websocket)
        self.active_connections[websocket] = context
        
        logger.info(f"新用户连接: {context.user_id}")
        
        # 创建默认会话
        session = await self.create_session(context)
        context.current_session_id = session.id
            
        # 发送初始会话信息
        await self.send_sessions_list(context)
        
    def disconnect_client(self, websocket: WebSocket):
        """断开客户端连接"""
        if websocket in self.active_connections:
            context = self.active_connections[websocket]
            logger.info(f"用户断开连接: {context.user_id}")
            # 清理该连接的所有资源
            del self.active_connections[websocket]
    
    async def send_sessions_list(self, context: ConnectionContext):
        """发送会话列表到客户端"""
        sessions_data = []
        for session in context.sessions.values():
            sessions_data.append({
                "id": session.id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "last_message_at": session.last_message_at.isoformat(),
                "message_count": len(session.messages)
            })
        
        message = {
            "type": "sessions_list",
            "sessions": sessions_data,
            "current_session_id": context.current_session_id
        }
        
        await context.websocket.send_json(message)
    
    async def send_session_messages(self, context: ConnectionContext, session_id: str):
        """发送会话的历史消息"""
        session = self.get_session(context, session_id)
        if not session:
            return
            
        messages_data = []
        for msg in session.messages:
            messages_data.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "tool_name": msg.tool_name,
                "tool_status": msg.tool_status
            })
        
        message = {
            "type": "session_messages",
            "session_id": session_id,
            "messages": messages_data
        }
        
        await context.websocket.send_json(message)
    
    async def send_to_connection(self, context: ConnectionContext, message: dict):
        """发送消息到特定连接"""
        # 为消息添加唯一标识符
        if 'id' not in message:
            message['id'] = f"{message.get('type', 'unknown')}_{datetime.now().timestamp()}"
        
        try:
            await context.websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            self.disconnect_client(context.websocket)
    
    async def process_message(self, context: ConnectionContext, message: str):
        """处理用户消息"""
        if not context.current_session_id:
            await context.websocket.send_json({
                "type": "error", 
                "content": "没有活动的会话"
            })
            return
            
        # 等待runner初始化完成
        retry_count = 0
        while context.current_session_id not in context.runners and retry_count < 50:  # 最多等待5秒
            await asyncio.sleep(0.1)
            retry_count += 1
            
        if context.current_session_id not in context.runners:
            await context.websocket.send_json({
                "type": "error", 
                "content": "会话初始化失败，请重试"
            })
            return
            
        session = context.sessions[context.current_session_id]
        runner = context.runners[context.current_session_id]
        
        # 保存用户消息到会话历史
        session.add_message("user", message)
        
        try:
            
            content = types.Content(
                role='user',
                parts=[types.Part(text=message)]
            )
            
            # 收集所有事件
            all_events = []
            seen_tool_calls = set()  # 跟踪已发送的工具调用
            seen_tool_responses = set()  # 跟踪已发送的工具响应
            usage_metadata = None  # 存储 token 使用信息
            
            # 使用 runner.run_async 并获取完整响应
            logger.info("Starting ADK runner...")
            
            async for event in runner.run_async(
                new_message=content,
                user_id=context.user_id,
                session_id=context.current_session_id
            ):
                all_events.append(event)
                logger.info(f"Received event: {type(event).__name__}")
                
                # 检查事件是否包含 usage_metadata
                if hasattr(event, 'usage_metadata') and event.usage_metadata:
                    logger.info(f"Found usage_metadata in event: {event.usage_metadata}")
                    try:
                        # Google ADK 的 usage_metadata 通常包含这些字段
                        usage_metadata = {
                            'prompt_tokens': getattr(event.usage_metadata, 'prompt_token_count', 0),
                            'candidates_tokens': getattr(event.usage_metadata, 'candidates_token_count', 0),
                            'total_tokens': getattr(event.usage_metadata, 'total_token_count', 0)
                        }
                        logger.info(f"Extracted usage_metadata: {usage_metadata}")
                    except Exception as e:
                        logger.error(f"Error extracting usage_metadata: {e}")
                        # 尝试其他可能的字段名
                        try:
                            usage_metadata = {
                                'prompt_tokens': getattr(event.usage_metadata, 'prompt_tokens', 0),
                                'candidates_tokens': getattr(event.usage_metadata, 'candidates_tokens', 0),
                                'total_tokens': getattr(event.usage_metadata, 'total_tokens', 0)
                            }
                            logger.info(f"Extracted usage_metadata (fallback): {usage_metadata}")
                        except Exception as e2:
                            logger.error(f"Fallback extraction failed: {e2}")
                            logger.info(f"usage_metadata attributes: {dir(event.usage_metadata)}")
                            logger.info(f"usage_metadata content: {event.usage_metadata}")
                
                # 检查是否有 response 对象包含 usage_metadata
                if hasattr(event, 'response') and event.response:
                    if hasattr(event.response, 'usage_metadata') and event.response.usage_metadata:
                        logger.info(f"Found usage_metadata in response: {event.response.usage_metadata}")
                        try:
                            usage_metadata = {
                                'prompt_tokens': getattr(event.response.usage_metadata, 'prompt_token_count', 0),
                                'candidates_tokens': getattr(event.response.usage_metadata, 'candidates_token_count', 0),
                                'total_tokens': getattr(event.response.usage_metadata, 'total_token_count', 0)
                            }
                            logger.info(f"Extracted usage_metadata from response: {usage_metadata}")
                        except Exception as e:
                            logger.error(f"Error extracting usage_metadata from response: {e}")
                
                # 检查事件中的工具调用（按照官方示例）
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        # 检查是否是函数调用
                        if hasattr(part, 'function_call') and part.function_call:
                            function_call = part.function_call
                            tool_name = getattr(function_call, 'name', 'unknown')
                            tool_id = getattr(function_call, 'id', tool_name)
                            
                            # 避免重复发送相同的工具调用
                            if tool_id in seen_tool_calls:
                                continue
                            seen_tool_calls.add(tool_id)
                            
                            # 检查是否是长时间运行的工具
                            is_long_running = False
                            if (hasattr(event, 'long_running_tool_ids') and 
                                event.long_running_tool_ids and 
                                hasattr(function_call, 'id')):
                                is_long_running = function_call.id in event.long_running_tool_ids
                            
                            await self.send_to_connection(context, {
                                "type": "tool",
                                "tool_name": tool_name,
                                "status": "executing",
                                "is_long_running": is_long_running,
                                "timestamp": datetime.now().isoformat()
                            })
                            logger.info(f"Tool call detected: {tool_name} (long_running: {is_long_running})")
                        
                        # 检查是否是函数响应（工具完成）
                        elif hasattr(part, 'function_response') and part.function_response:
                            function_response = part.function_response
                            # 从响应中获取更多信息
                            tool_name = "unknown"
                            tool_result = None
                            
                            if hasattr(function_response, 'name'):
                                tool_name = function_response.name
                            
                            # 创建唯一标识符
                            response_id = f"{tool_name}_response"
                            if hasattr(function_response, 'id'):
                                response_id = function_response.id
                            
                            # 避免重复发送相同的工具响应
                            if response_id in seen_tool_responses:
                                continue
                            seen_tool_responses.add(response_id)
                            
                            if hasattr(function_response, 'response'):
                                response_data = function_response.response
                                
                                # 智能格式化不同类型的响应
                                if isinstance(response_data, dict):
                                    # 如果是字典，尝试美化JSON格式
                                    try:
                                        result_str = json.dumps(response_data, indent=2, ensure_ascii=False)
                                    except:
                                        result_str = str(response_data)
                                elif isinstance(response_data, (list, tuple)):
                                    # 如果是列表或元组，也尝试JSON格式化
                                    try:
                                        result_str = json.dumps(response_data, indent=2, ensure_ascii=False)
                                    except:
                                        result_str = str(response_data)
                                elif isinstance(response_data, str):
                                    # 字符串直接使用，保留原始格式
                                    result_str = response_data
                                else:
                                    # 其他类型转换为字符串
                                    result_str = str(response_data)
                                
                                await self.send_to_connection(context, {
                                    "type": "tool",
                                    "tool_name": tool_name,
                                    "status": "completed",
                                    "result": result_str,
                                    "timestamp": datetime.now().isoformat()
                                })
                            else:
                                # 没有结果的情况
                                await self.send_to_connection(context, {
                                    "type": "tool",
                                    "tool_name": tool_name,
                                    "status": "completed",
                                    "timestamp": datetime.now().isoformat()
                                })
                            
                            logger.info(f"Tool response received: {tool_name}")
            
            # 处理所有事件，只获取最后一个有效响应
            logger.info(f"Total events: {len(all_events)}")
            
            final_response = None
            # 从后往前查找最后一个有效的响应
            for event in reversed(all_events):
                if hasattr(event, 'content') and event.content:
                    content = event.content
                    # 处理 Google ADK 的 Content 对象
                    if hasattr(content, 'parts') and content.parts:
                        # 提取所有文本部分
                        text_parts = []
                        for part in content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_parts.append(part.text)
                        if text_parts:
                            final_response = '\n'.join(text_parts)
                            break
                    elif hasattr(content, 'text') and content.text:
                        final_response = content.text
                        break
                elif hasattr(event, 'text') and event.text:
                    final_response = event.text
                    break
                elif hasattr(event, 'output') and event.output:
                    final_response = event.output
                    break
                elif hasattr(event, 'message') and event.message:
                    final_response = event.message
                    break
            
            # 只发送最后一个响应内容
            if final_response:
                logger.info(f"Sending final response: {final_response[:200]}")
                # 保存助手回复到会话历史
                session.add_message("assistant", final_response)
                
                # 构建响应消息，包含 usage_metadata
                response_message = {
                    "type": "assistant",
                    "content": final_response,
                    "session_id": context.current_session_id
                }
                
                # 如果有 token 使用信息，添加到响应中
                if usage_metadata:
                    response_message["usage_metadata"] = usage_metadata
                    
                    # 执行光子收费（如果启用）
                    if CHARGING_ENABLED:
                        photon_service = get_photon_service()
                        if photon_service:
                            try:
                                # 获取输入输出token数量
                                input_tokens = usage_metadata.get('prompt_tokens', 0)
                                output_tokens = usage_metadata.get('candidates_tokens', 0)
                                
                                # 计算工具调用次数（从消息历史中统计）
                                tool_calls = 0
                                if hasattr(context, 'current_session') and context.current_session:
                                    # 统计当前会话中最后一次用户消息后的工具调用次数
                                    for msg in reversed(context.current_session.messages):
                                        if msg.role == 'user':
                                            break
                                        if msg.role == 'tool':
                                            tool_calls += 1
                                
                                if input_tokens > 0 or output_tokens > 0 or tool_calls > 0:
                                    logger.info(f"Processing photon charge - Input tokens: {input_tokens}, Output tokens: {output_tokens}, Tool calls: {tool_calls}")
                                    
                                    # 执行收费
                                    charge_result = await photon_service.charge_photon(
                                        input_tokens=input_tokens,
                                        output_tokens=output_tokens,
                                        tool_calls=tool_calls,
                                        request=None,  # WebSocket 连接中无法直接获取 Request 对象
                                        context=context  # 传递 WebSocket 连接上下文
                                    )
                                    
                                    # 将收费结果添加到响应中
                                    response_message["charge_result"] = {
                                        "success": charge_result.success,
                                        "code": charge_result.code,
                                        "message": charge_result.message,
                                        "biz_no": charge_result.biz_no,
                                        "photon_amount": charge_result.photon_amount,
                                        "rmb_amount": charge_result.rmb_amount
                                    }
                                    
                                    if charge_result.success:
                                        logger.info(f"Photon charge successful: {charge_result.message}")
                                    else:
                                        logger.warning(f"Photon charge failed: {charge_result.message}")
                                else:
                                    logger.info("No tokens or tool calls to charge")
                            except Exception as e:
                                logger.error(f"Error during photon charging: {e}")
                                response_message["charge_result"] = {
                                    "success": False,
                                    "code": -1,
                                    "message": f"收费过程中发生错误: {str(e)}",
                                    "biz_no": None,
                                    "photon_amount": 0,
                                    "rmb_amount": 0.0
                                }
                
                await self.send_to_connection(context, response_message)
            else:
                logger.warning("No response content found in events")
            
            # 发送一个空的完成标记，前端会识别这个来停止loading
            await self.send_to_connection(context, {
                "type": "complete",
                "content": ""
            })
                    
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"处理消息时出错: {e}\n{error_details}")
            
            # 如果是 ExceptionGroup，尝试提取更多信息
            if hasattr(e, '__cause__') and e.__cause__:
                logger.error(f"根本原因: {e.__cause__}")
            if hasattr(e, 'exceptions'):
                logger.error(f"子异常数量: {len(e.exceptions)}")
                for i, sub_exc in enumerate(e.exceptions):
                    logger.error(f"子异常 {i}: {sub_exc}", exc_info=(type(sub_exc), sub_exc, sub_exc.__traceback__))
            
            await context.websocket.send_json({
                "type": "error",
                "content": f"处理消息失败: {str(e)}"
            })

# 创建全局管理器
manager = SessionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点"""
    await manager.connect_client(websocket)
    
    # 获取该连接的上下文
    context = manager.active_connections.get(websocket)
    if not context:
        logger.error("无法获取连接上下文")
        await websocket.close()
        return
        
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "message":
                content = data.get("content", "").strip()
                if content:
                    await manager.process_message(context, content)
                    
            elif message_type == "create_session":
                # 创建新会话
                session = await manager.create_session(context)
                await manager.switch_session(context, session.id)
                await manager.send_sessions_list(context)
                await manager.send_session_messages(context, session.id)
                
            elif message_type == "switch_session":
                # 切换会话
                session_id = data.get("session_id")
                if session_id and await manager.switch_session(context, session_id):
                    await manager.send_session_messages(context, session_id)
                else:
                    await websocket.send_json({
                        "type": "error",
                        "content": "会话不存在"
                    })
                    
            elif message_type == "get_sessions":
                # 获取会话列表
                await manager.send_sessions_list(context)
                
            elif message_type == "delete_session":
                # 删除会话
                session_id = data.get("session_id")
                if session_id and manager.delete_session(context, session_id):
                    # 如果删除的是当前会话，切换到其他会话或创建新会话
                    if session_id == context.current_session_id:
                        if context.sessions:
                            # 切换到第一个可用会话
                            first_session_id = list(context.sessions.keys())[0]
                            await manager.switch_session(context, first_session_id)
                        else:
                            # 创建新会话
                            session = await manager.create_session(context)
                            await manager.switch_session(context, session.id)
                    await manager.send_sessions_list(context)
                else:
                    await websocket.send_json({
                        "type": "error",
                        "content": "删除会话失败"
                    })
                    
            elif message_type == "authenticate":
                # 处理用户认证信息
                app_access_key = data.get("appAccessKey", "").strip()
                client_name = data.get("clientName", "").strip()
                
                if app_access_key:
                    context.app_access_key = app_access_key
                    context.client_name = client_name or "WebClient"
                    context.is_authenticated = True
                    logger.info(f"用户 {context.user_id} 认证成功，AccessKey: {app_access_key[:8]}...")
                    
                    await websocket.send_json({
                        "type": "auth_success",
                        "content": "认证成功"
                    })
                else:
                    logger.warning(f"用户 {context.user_id} 认证失败：缺少AccessKey")
                    await websocket.send_json({
                        "type": "auth_error",
                        "content": "认证失败：缺少AccessKey"
                    })
                    
            elif message_type == "shell_command":
                command = data.get("command", "").strip()
                if command:
                    await execute_shell_command(command, context)
                
    except WebSocketDisconnect:
        manager.disconnect_client(websocket)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}", exc_info=True)
        manager.disconnect_client(websocket)

@app.get("/api/files/tree")
async def get_file_tree(path: str = None):
    """获取文件树结构"""
    try:
        # Use configured output directory if no path specified
        if path is None:
            path = agentconfig.get_files_config().get("outputDirectory", "output")
        
        base_path = Path(path)
        if not base_path.exists():
            base_path.mkdir(parents=True, exist_ok=True)
            
        def build_tree(directory: Path):
            items = []
            try:
                for item in sorted(directory.iterdir()):
                    if item.name.startswith('.'):
                        continue
                        
                    node = {
                        "name": item.name,
                        "path": str(item.relative_to(".")),
                        "type": "directory" if item.is_dir() else "file"
                    }
                    
                    if item.is_dir():
                        node["children"] = build_tree(item)
                    else:
                        node["size"] = item.stat().st_size
                        
                    items.append(node)
            except PermissionError:
                pass
            return items
        
        return JSONResponse(content=build_tree(base_path))
        
    except Exception as e:
        logger.error(f"获取文件树错误: {e}")
        return JSONResponse(content=[], status_code=500)

@app.get("/api/files/{file_path:path}")
async def get_file_content(file_path: str):
    """获取文件内容"""
    try:
        file = Path(file_path)
        if not file.exists() or not file.is_file():
            return JSONResponse(
                content={"error": "文件未找到"},
                status_code=404
            )
        
        # 判断文件类型
        suffix = file.suffix.lower()
        
        # 文本文件
        if suffix in ['.json', '.md', '.txt', '.csv', '.py', '.js', '.ts', '.log', '.xml', '.yaml', '.yml']:
            try:
                content = file.read_text(encoding='utf-8')
                return PlainTextResponse(content)
            except UnicodeDecodeError:
                return JSONResponse(
                    content={"error": "无法解码文件内容"},
                    status_code=400
                )
        else:
            # 二进制文件
            return FileResponse(file)
            
    except Exception as e:
        logger.error(f"读取文件错误: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"{agentconfig.config.get('agent', {}).get('name', 'Agent')} WebSocket 服务器正在运行",
        "mode": "session",
        "endpoints": {
            "websocket": "/ws",
            "files": "/api/files",
            "file_tree": "/api/files/tree",
            "config": "/api/config",
            "upload": "/api/upload",
            "upload_status": "/api/upload/status"
        }
    }

@app.get("/api/config")
async def get_config():
    """获取前端配置信息"""
    return JSONResponse(content={
        "agent": agentconfig.config.get("agent", {}),
        "ui": agentconfig.get_ui_config(),
        "files": agentconfig.get_files_config(),
        "websocket": agentconfig.get_websocket_config()
    })

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """文件上传API端点"""
    try:
        # 验证文件类型
        allowed_extensions = {'.xyz', '.mol', '.sdf', '.pdb', '.txt', '.json', '.csv'}
        file_extension = '.' + file.filename.split('.')[-1].lower() if file.filename and '.' in file.filename else ''
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型。支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 验证文件大小 (10MB限制)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="文件大小超过10MB限制"
            )
        
        # 重置文件指针
        await file.seek(0)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # 使用HTTP存储服务上传到bohr
            from dp.agent.server.storage.http_storage import HTTPStorage
            
            # 初始化HTTP存储
            storage = HTTPStorage()
            
            # 生成唯一的文件键
            import uuid
            file_key = f"uploads/{uuid.uuid4()}/{file.filename}"
            
            # 上传文件
            upload_result = storage._upload(file_key, temp_file_path)
            
            # 构建完整的URL
            if upload_result:
                # 如果返回的是相对路径，构建完整URL
                if not upload_result.startswith('http'):
                    upload_url = f"https://{upload_result}"
                else:
                    upload_url = upload_result
                
                logger.info(f"文件上传成功: {file.filename} -> {upload_url}")
                
                return JSONResponse(content={
                    "success": True,
                    "filename": file.filename,
                    "url": upload_url,
                    "key": file_key,
                    "size": len(file_content),
                    "type": file_extension
                })
            else:
                raise HTTPException(status_code=500, detail="上传到存储服务失败")
                
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传错误: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.get("/api/upload/status")
async def get_upload_status():
    """获取上传服务状态"""
    try:
        from dp.agent.server.storage.http_storage import HTTPStorage
        storage = HTTPStorage()
        
        # 检查存储服务是否可用
        if storage.plugin is not None:
            return JSONResponse(content={
                "available": True,
                "plugin_type": storage.plugin.__class__.__name__,
                "message": "文件上传服务可用"
            })
        else:
            return JSONResponse(content={
                "available": False,
                "message": "HTTP存储插件未配置"
            })
    except Exception as e:
        return JSONResponse(content={
            "available": False,
            "error": str(e),
            "message": "文件上传服务不可用"
        })

# 安全的命令白名单
SAFE_COMMANDS = {
    'ls', 'pwd', 'cd', 'cat', 'echo', 'grep', 'find', 'head', 'tail', 
    'wc', 'sort', 'uniq', 'diff', 'cp', 'mv', 'mkdir', 'touch', 'date',
    'whoami', 'hostname', 'uname', 'df', 'du', 'ps', 'top', 'which',
    'git', 'npm', 'python', 'pip', 'node', 'yarn', 'curl', 'wget',
    'tree', 'clear', 'history'
}

# 危险命令黑名单
DANGEROUS_COMMANDS = {
    'rm', 'rmdir', 'kill', 'killall', 'shutdown', 'reboot', 'sudo',
    'su', 'chmod', 'chown', 'dd', 'format', 'mkfs', 'fdisk', 'apt',
    'yum', 'brew', 'systemctl', 'service', 'docker', 'kubectl'
}

async def execute_shell_command(command: str, context: ConnectionContext):
    """安全地执行 shell 命令（保持状态）"""
    try:
        # 使用连接上下文中的shell状态
        shell_state = context.shell_state
        websocket = context.websocket
        
        # 解析命令
        try:
            cmd_parts = shlex.split(command)
        except ValueError as e:
            await websocket.send_json({
                "type": "shell_error",
                "error": f"命令解析错误: {str(e)}"
            })
            return
            
        if not cmd_parts:
            return
            
        # 获取基础命令
        base_cmd = cmd_parts[0]
        
        # 检查是否是危险命令
        if base_cmd in DANGEROUS_COMMANDS:
            await websocket.send_json({
                "type": "shell_error",
                "error": f"安全限制: 命令 '{base_cmd}' 已被禁用"
            })
            return
            
        # 对于不在白名单中的命令，给出警告但仍然执行
        if base_cmd not in SAFE_COMMANDS:
            logger.warning(f"执行非白名单命令: {base_cmd}")
        
        # 处理cd命令
        if base_cmd == "cd":
            try:
                if len(cmd_parts) == 1:
                    # cd without args goes to home
                    new_dir = os.path.expanduser("~")
                else:
                    new_dir = os.path.expanduser(cmd_parts[1])
                
                # 处理相对路径
                if not os.path.isabs(new_dir):
                    new_dir = os.path.join(shell_state["cwd"], new_dir)
                
                new_dir = os.path.normpath(new_dir)
                
                if os.path.isdir(new_dir):
                    shell_state["cwd"] = new_dir
                    await websocket.send_json({
                        "type": "shell_output",
                        "output": f"Changed directory to: {new_dir}\n"
                    })
                else:
                    await websocket.send_json({
                        "type": "shell_error",
                        "error": f"cd: no such file or directory: {cmd_parts[1]}\n"
                    })
            except Exception as e:
                await websocket.send_json({
                    "type": "shell_error",
                    "error": f"cd: {str(e)}\n"
                })
            return
        
        # 处理pwd命令
        if base_cmd == "pwd":
            await websocket.send_json({
                "type": "shell_output",
                "output": f"{shell_state['cwd']}\n"
            })
            return
        
        # 创建进程（使用保存的工作目录）
        logger.info(f"执行命令: {command} 在目录: {shell_state['cwd']}")
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=shell_state["cwd"],
            env=shell_state["env"]
        )
        
        # 设置超时时间（30秒）
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0
            )
            
            # 发送标准输出
            if stdout:
                output = stdout.decode('utf-8', errors='replace')
                logger.info(f"命令输出: {len(output)} 字符")
                await websocket.send_json({
                    "type": "shell_output",
                    "output": output
                })
            
            # 发送错误输出
            if stderr:
                error = stderr.decode('utf-8', errors='replace')
                logger.warning(f"命令错误: {error}")
                await websocket.send_json({
                    "type": "shell_error",
                    "error": error
                })
                
            # 如果没有输出
            if not stdout and not stderr:
                logger.info("命令执行完成，无输出")
                await websocket.send_json({
                    "type": "shell_output",
                    "output": "命令执行完成（无输出）\n"
                })
                
        except asyncio.TimeoutError:
            # 超时，终止进程
            process.terminate()
            await process.wait()
            await websocket.send_json({
                "type": "shell_error",
                "error": "命令执行超时（30秒）"
            })
            
    except Exception as e:
        logger.error(f"执行命令时出错: {e}")
        await websocket.send_json({
            "type": "shell_error",
            "error": f"执行命令失败: {str(e)}"
        })

if __name__ == "__main__":
    print("🚀 启动 Agent WebSocket 服务器...")
    print("📡 使用 Session 模式运行 rootagent")
    print("🌐 WebSocket 端点: ws://localhost:8000/ws")
    uvicorn.run(app, host="0.0.0.0", port=8000)