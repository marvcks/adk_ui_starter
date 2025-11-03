#!/usr/bin/env python3
"""
重构后的 Agent WebSocket 服务器
使用模块化架构，分离业务逻辑和通信逻辑
"""

import os
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass, field
import uuid
import subprocess
import shlex

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import tempfile

from google.adk import Runner
from google.adk.sessions import InMemorySessionService

# Import configuration
from config.agent_config import agentconfig

# Import photon charging service
from services.photon_service import PhotonService, init_photon_service, get_photon_service
from config.photon_config import PHOTON_CONFIG, CHARGING_ENABLED, FREE_TOKEN_QUOTA

# Import new modules - use absolute imports
from core.message_types import MessageType, WebSocketMessage
from core.state_machine import SessionState, StateMachine, SessionStateManager
from core.event_handlers import EventProcessor
from services.message_service import MessageService

# from bohrium_open_sdk import OpenSDK

# Get agent from configuration
rootagent = agentconfig.get_agent()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("google_adk.google.adk.tools.base_authenticated_tool").setLevel(logging.ERROR)


# 初始化光子收费服务
if CHARGING_ENABLED:
    init_photon_service(PHOTON_CONFIG)
    logger.info("光子收费服务已启用")
else:
    logger.info("光子收费服务已禁用")


@dataclass
class Session:
    """Session model"""
    id: str
    title: str = "新对话"
    created_at: datetime = field(default_factory=datetime.now)
    last_message_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    
    def update_title(self, content: str):
        """Update session title based on content"""
        if self.title == "新对话" and len(content) > 0:
            self.title = content[:30] + "..." if len(content) > 30 else content
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "last_message_at": self.last_message_at.isoformat(),
            "message_count": self.message_count
        }


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
        # 状态机管理器
        self.state_manager = SessionStateManager()
        # 事件处理器
        self.event_processor = EventProcessor()
        # 消息服务 - 传递WebSocket引用
        self.message_service = MessageService(self.event_processor, websocket)


class SessionManager:
    """会话管理器"""
    def __init__(self):
        self.active_connections: Dict[WebSocket, ConnectionContext] = {}
        self.app_name = agentconfig.config.get("agent", {}).get("name", "Agent")
        
    async def create_session(self, context: ConnectionContext) -> Session:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        session = Session(id=session_id)
        
        # 先将会话添加到连接的会话列表
        context.sessions[session_id] = session
        
        # 创建状态机
        state_machine = context.state_manager.create_session(session_id)
        
        # 异步创建 session service 和 runner
        task = asyncio.create_task(self._init_session_runner(context, session_id))
        
        # 添加错误处理回调
        def handle_init_error(future):
            try:
                future.result()
            except Exception as e:
                logger.error(f"初始化会话Runner时发生未处理的错误: {e}", exc_info=True)
        
        task.add_done_callback(handle_init_error)
        
        logger.info(f"为用户 {context.user_id} 创建新会话: {session_id}")
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
            
            # 更新状态机状态
            state_machine = context.state_manager.get_session(session_id)
            if state_machine:
                state_machine.transition_to(SessionState.READY, reason="Runner initialized")
            
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
            
            # 更新状态机状态
            state_machine = context.state_manager.get_session(session_id)
            if state_machine:
                state_machine.transition_to(SessionState.ERROR, reason=f"Runner initialization failed: {e}")
    
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
            
            # 清理状态机
            context.state_manager.remove_session(session_id)
            
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
    
    async def connect_client(self, websocket: WebSocket, app_access_key: Optional[str] = None, client_name: Optional[str] = None):
        """连接新客户端"""
        await websocket.accept()
        
        # 为新连接创建独立的上下文
        context = ConnectionContext(websocket)
        
        # 如果提供了认证信息，立即设置
        if app_access_key:
            context.app_access_key = app_access_key
            context.client_name = client_name or "WebClient"
            context.is_authenticated = True
            logger.info(f"用户 {context.user_id} 通过查询参数认证成功，AccessKey: {app_access_key}")
        
        self.active_connections[websocket] = context
        
        logger.info(f"新用户连接: {context.user_id}")
        
        # 创建默认会话
        session = await self.create_session(context)
        context.current_session_id = session.id
            
        # 发送初始会话信息
        await self.send_sessions_list(context)
        await self.send_session_messages(context, session.id)
        
        # 如果通过查询参数认证成功，发送认证成功消息
        if app_access_key:
            await websocket.send_json({
                "type": "auth_success",
                "content": "认证成功"
            })
        
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
            sessions_data.append(session.to_dict())
        
        # 使用简单格式发送消息
        await context.websocket.send_json({
            "type": "sessions_list",
            "sessions": sessions_data,
            "current_session_id": context.current_session_id
        })
    
    async def send_session_messages(self, context: ConnectionContext, session_id: str):
        """发送会话的历史消息"""
        session = self.get_session(context, session_id)
        if not session:
            logger.warning(f"会话 {session_id} 不存在，无法发送消息历史")
            return
            
        logger.info(f"准备发送会话 {session_id} 的消息历史")
        messages_data = context.message_service.get_message_history(session_id)
        logger.info(f"会话 {session_id} 获取到 {len(messages_data)} 条消息")
        
        # 使用简单格式发送消息
        await context.websocket.send_json({
            "type": "session_messages",
            "session_id": session_id,
            "messages": messages_data
        })
        logger.info(f"会话 {session_id} 的消息历史已发送到前端")
    
    async def send_to_connection(self, context: ConnectionContext, message: WebSocketMessage):
        """发送消息到特定连接"""
        try:
            # 直接发送消息数据，而不是WebSocketMessage包装
            await context.websocket.send_json(message.to_dict())
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            self.disconnect_client(context.websocket)
    
    async def process_message(self, context: ConnectionContext, message: str):
        """处理用户消息 - 重构后的版本"""
        if not context.current_session_id:
            # 发送错误消息 - 使用简单格式
            await context.websocket.send_json({
                "type": "error",
                "content": "没有活动的会话"
            })
            return
            
        # 等待runner初始化完成
        retry_count = 0
        while context.current_session_id not in context.runners and retry_count < 50:
            await asyncio.sleep(0.1)
            retry_count += 1
            
        if context.current_session_id not in context.runners:
            # 发送错误消息 - 使用简单格式
            await context.websocket.send_json({
                "type": "error",
                "content": "会话初始化失败，请重试"
            })
            return
            
        session = context.sessions[context.current_session_id]
        runner = context.runners[context.current_session_id]
        
        # 更新会话标题
        session.update_title(message)
        
        # 使用消息服务处理消息
        try:
            # 更新状态机状态
            state_machine = context.state_manager.get_session(context.current_session_id)
            if state_machine:
                state_machine.transition_to(SessionState.PROCESSING, reason="Processing user message")
            
            # 处理消息
            result = await context.message_service.process_user_message(
                context.current_session_id,
                context.user_id,
                message,
                runner,
                context  # 传递 ConnectionContext
            )
            
            if result['success']:
                # 构建响应消息，包含完整信息
                response_message = {
                    "type": "assistant",
                    "content": result['response']['content'],
                    "session_id": context.current_session_id
                }
                
                # 添加token使用信息
                if 'usage_metadata' in result['response']:
                    response_message["usage_metadata"] = result['response']['usage_metadata']
                
                # 添加收费结果信息
                if 'charge_result' in result:
                    response_message["charge_result"] = result['charge_result']
                    # logger.info(f"收费结果: {response_message['charge_result']}")

                    if CHARGING_ENABLED:
                        if not response_message["charge_result"]['success']:
                            await context.websocket.send_json({
                                    "type": "charge_failed",
                                    "content": f"收费失败: {result['charge_result'].get('message', '未知错误')}，连接将断开",
                                })
                            
                            # wait 5 seconds to let the client receive the message
                            await asyncio.sleep(5)
                                
                            # 断开连接
                            await context.websocket.close(code=4001, reason="Charge failed")
                            self.disconnect_client(context.websocket)
                            return
                
                
                # 发送助手回复
                await context.websocket.send_json(response_message)
                
                # 更新会话信息
                session.message_count = context.message_service.get_message_count(context.current_session_id)
                session.last_message_at = datetime.now()
                
                # 更新状态机状态
                if state_machine:
                    state_machine.transition_to(SessionState.READY, reason="Message processing completed")
            else:
                # 发送错误消息 - 使用简单格式
                await context.websocket.send_json({
                    "type": "error",
                    "content": f"处理消息失败: {result['error']}"
                })
                
                # 更新状态机状态
                if state_machine:
                    state_machine.transition_to(SessionState.ERROR, reason=f"Message processing failed: {result['error']}")
            
            # 发送完成标记 - 使用简单格式
            await context.websocket.send_json({
                "type": "complete",
                "content": ""
            })
                    
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"处理消息时出错: {e}\n{error_details}")
            
            # 发送错误消息 - 使用简单格式
            await context.websocket.send_json({
                "type": "error",
                "content": f"处理消息失败: {str(e)}"
            })
            
            # 更新状态机状态
            state_machine = context.state_manager.get_session(context.current_session_id)
            if state_machine:
                state_machine.transition_to(SessionState.ERROR, reason=f"Exception occurred: {str(e)}")


# 创建全局管理器
manager = SessionManager()

# FastAPI 应用
app = FastAPI(title="Refactored Agent WebSocket Server")

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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点"""
    # 在连接时尝试从查询参数获取认证信息
    query_params = websocket.query_params
    app_access_key = query_params.get("appAccessKey")
    client_name = query_params.get("clientName")

    logger.info(f"app_access_key: {app_access_key}")
    logger.info(f"client_name: {client_name}")

    # client = OpenSDK(access_key=access_key, app_key=app_key)

    
    await manager.connect_client(websocket, app_access_key, client_name)
    
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
                    # 使用简单格式发送错误消息
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
                    # 使用简单格式发送错误消息
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


# 文件相关API
@app.get("/api/files/tree")
async def get_file_tree(path: str = None):
    """获取文件树结构"""
    try:
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
        if suffix in ['.json', '.txt', '.csv', '.py', '.js', '.ts', '.log', '.xml', '.yaml', '.yml']:
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
        "message": f"{agentconfig.config.get('agent', {}).get('name', 'Agent')} 重构后的 WebSocket 服务器正在运行",
        "mode": "session",
        "architecture": "modular",
        "endpoints": {
            "websocket": "/ws",
            "files": "/api/files",
            "file_tree": "/api/files/tree",
            "config": "/api/config"
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
        
        return JSONResponse(content={
            "success": True,
            "status": "available",
            "message": "上传服务正常运行"
        })
    except Exception as e:
        logger.error(f"检查上传状态错误: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "status": "error",
                "message": f"上传服务不可用: {str(e)}"
            }
        )


# Shell 命令执行相关代码保持不变
SAFE_COMMANDS = {
    'ls', 'pwd', 'cd', 'cat', 'echo', 'grep', 'find', 'head', 'tail', 
    'wc', 'sort', 'uniq', 'diff', 'cp', 'mv', 'mkdir', 'touch', 'date',
    'whoami', 'hostname', 'uname', 'df', 'du', 'ps', 'top', 'which',
    'git', 'npm', 'python', 'pip', 'node', 'yarn', 'curl', 'wget',
    'tree', 'clear', 'history'
}

DANGEROUS_COMMANDS = {
    'rm', 'rmdir', 'kill', 'killall', 'shutdown', 'reboot', 'sudo',
    'su', 'chmod', 'chown', 'dd', 'format', 'mkfs', 'fdisk', 'apt',
    'yum', 'brew', 'systemctl', 'service', 'docker', 'kubectl'
}

async def execute_shell_command(command: str, context: ConnectionContext):
    """安全地执行 shell 命令（保持状态）"""
    try:
        shell_state = context.shell_state
        websocket = context.websocket
        
        try:
            cmd_parts = shlex.split(command)
        except ValueError as e:
            # 使用简单格式发送错误消息
            await websocket.send_json({
                "type": "shell_error",
                "error": f"命令解析错误: {str(e)}"
            })
            return
            
        if not cmd_parts:
            return
            
        base_cmd = cmd_parts[0]
        
        if base_cmd in DANGEROUS_COMMANDS:
            # 使用简单格式发送错误消息
            await websocket.send_json({
                "type": "shell_error",
                "error": f"安全限制: 命令 '{base_cmd}' 已被禁用"
            })
            return
            
        if base_cmd not in SAFE_COMMANDS:
            logger.warning(f"执行非白名单命令: {base_cmd}")
        
        # 处理cd命令
        if base_cmd == "cd":
            try:
                if len(cmd_parts) == 1:
                    new_dir = os.path.expanduser("~")
                else:
                    new_dir = os.path.expanduser(cmd_parts[1])
                
                if not os.path.isabs(new_dir):
                    new_dir = os.path.join(shell_state["cwd"], new_dir)
                
                new_dir = os.path.normpath(new_dir)
                
                if os.path.isdir(new_dir):
                    shell_state["cwd"] = new_dir
                    # 使用简单格式发送输出消息
                    await websocket.send_json({
                        "type": "shell_output",
                        "output": f"Changed directory to: {new_dir}\n"
                    })
                else:
                    # 使用简单格式发送错误消息
                    await websocket.send_json({
                        "type": "shell_error",
                        "error": f"cd: no such file or directory: {cmd_parts[1]}\n"
                    })
            except Exception as e:
                # 使用简单格式发送错误消息
                await websocket.send_json({
                    "type": "shell_error",
                    "error": f"cd: {str(e)}\n"
                })
            return
        
        # 处理pwd命令
        if base_cmd == "pwd":
            # 使用简单格式发送输出消息
            await websocket.send_json({
                "type": "shell_output",
                "output": f"{shell_state['cwd']}\n"
            })
            return
        
        # 创建进程
        logger.info(f"执行命令: {command} 在目录: {shell_state['cwd']}")
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=shell_state["cwd"],
            env=shell_state["env"]
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0
            )
            
            if stdout:
                output = stdout.decode('utf-8', errors='replace')
                # 使用简单格式发送输出消息
                await websocket.send_json({
                    "type": "shell_output",
                    "output": output
                })
            
            if stderr:
                error = stderr.decode('utf-8', errors='replace')
                # 使用简单格式发送错误消息
                await websocket.send_json({
                    "type": "shell_error",
                    "error": error
                })
                
            if not stdout and not stderr:
                # 使用简单格式发送输出消息
                await websocket.send_json({
                    "type": "shell_output",
                    "output": "命令执行完成（无输出）\n"
                })
                
        except asyncio.TimeoutError:
            process.terminate()
            await process.wait()
            # 使用简单格式发送错误消息
            await websocket.send_json({
                "type": "shell_error",
                "error": "命令执行超时（30秒）"
            })
            
    except Exception as e:
        logger.error(f"执行命令时出错: {e}")
        # 使用简单格式发送错误消息
        await websocket.send_json({
            "type": "shell_error",
            "error": f"执行命令失败: {str(e)}"
        })


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)